"""Orchestration routines for board discovery, sharded ATS ingestion, and feed ingestion."""
from __future__ import annotations

import asyncio
from typing import Any

from job_pipeline.ats import fetch_board_jobs
from job_pipeline.config import Settings
from job_pipeline.db import Database
from job_pipeline.discovery import run_discovery
from job_pipeline.feeds import FEED_FETCHERS
from job_pipeline.http_client import HttpClient


async def sync_discovery(
    db: Database,
    client: HttpClient,
    *,
    groups: list[str] | None = None,
) -> dict[str, Any]:
    run_id = await db.start_run("discover")
    per_group: dict[str, int] = {}
    errors = 0
    total_upserted = 0
    try:
        discovered = await run_discovery(client, groups=groups)
        for group_name, boards in discovered.items():
            count = await db.upsert_boards(boards)
            per_group[group_name] = count
            total_upserted += count
        await db.finish_run(
            run_id,
            status="completed",
            boards_processed=total_upserted,
            errors_count=errors,
            details={"groups": per_group},
        )
        return {"run_id": run_id, "boards_upserted": total_upserted, "groups": per_group}
    except Exception as exc:
        await db.finish_run(run_id, status="failed", errors_count=errors + 1, details={"error": str(exc)})
        raise


async def sync_ats_shard(
    db: Database,
    client: HttpClient,
    settings: Settings,
    *,
    shard: int = 0,
    total_shards: int = 1,
    max_boards: int = 300,
    ats_filter: list[str] | None = None,
    concurrency: int = 20,
) -> dict[str, Any]:
    shard_label = f"{shard}/{total_shards}"
    run_id = await db.start_run("ats", shard=shard_label)
    boards = await db.select_boards_for_shard(
        shard=shard,
        total_shards=total_shards,
        max_boards=max_boards,
        ats_filter=ats_filter,
    )

    sem = asyncio.Semaphore(max(1, concurrency))
    totals = {
        "boards_processed": 0,
        "boards_ok": 0,
        "boards_not_found": 0,
        "boards_error": 0,
        "jobs_upserted": 0,
        "jobs_skipped": 0,
        "jobs_expired": 0,
    }

    async def _fetch(board):
        async with sem:
            return await fetch_board_jobs(client, board)

    try:
        results = await asyncio.gather(*(_fetch(b) for b in boards), return_exceptions=True)
        for board, res in zip(boards, results):
            totals["boards_processed"] += 1
            if isinstance(res, Exception):
                totals["boards_error"] += 1
                await db.mark_board_failed(board.id, str(res), is_not_found=False)
                continue
            if res.status == "ok":
                totals["boards_ok"] += 1
                if res.company is not None:
                    await db.upsert_company(res.company)
                upserted, skipped, expired = await db.upsert_jobs(
                    res.jobs,
                    board_id=board.id,
                    expire_missing_for_board=True,
                )
                totals["jobs_upserted"] += upserted
                totals["jobs_skipped"] += skipped
                totals["jobs_expired"] += expired
                await db.mark_board_synced(
                    board.id,
                    jobs_count=len(res.jobs),
                    company_name=res.company.name if res.company else None,
                    region=res.region_answered,
                )
            elif res.status == "not_found":
                totals["boards_not_found"] += 1
                await db.mark_board_failed(
                    board.id,
                    res.error or "not_found",
                    is_not_found=True,
                    max_consecutive_failures=settings.max_consecutive_failures,
                )
            else:
                totals["boards_error"] += 1
                await db.mark_board_failed(board.id, res.error or "error", is_not_found=False)

        await db.finish_run(
            run_id,
            status="completed",
            boards_processed=totals["boards_processed"],
            jobs_upserted=totals["jobs_upserted"],
            jobs_skipped=totals["jobs_skipped"],
            jobs_expired=totals["jobs_expired"],
            errors_count=totals["boards_error"],
            details=totals,
        )
        return {"run_id": run_id, "shard": shard_label, **totals}
    except Exception as exc:
        await db.finish_run(run_id, status="failed", errors_count=totals["boards_error"] + 1, details={"error": str(exc)})
        raise


async def sync_feeds(
    db: Database,
    client: HttpClient,
    settings: Settings,
    *,
    feeds: list[str] | None = None,
) -> dict[str, Any]:
    run_id = await db.start_run("feed")
    selected = feeds or list(FEED_FETCHERS.keys())
    per_feed: dict[str, dict[str, int | str]] = {}
    total_upserted = 0
    total_skipped = 0
    errors = 0

    try:
        for name in selected:
            fetcher = FEED_FETCHERS.get(name)
            if fetcher is None:
                continue
            try:
                jobs = await fetcher(client)
                upserted, skipped, _ = await db.upsert_jobs(jobs)
                total_upserted += upserted
                total_skipped += skipped
                per_feed[name] = {"fetched": len(jobs), "upserted": upserted, "skipped": skipped}
            except Exception as exc:
                errors += 1
                per_feed[name] = {"error": str(exc)}

        expired = await db.expire_stale_feed_jobs(days=settings.feed_expiry_days)
        await db.finish_run(
            run_id,
            status="completed",
            boards_processed=len(per_feed),
            jobs_upserted=total_upserted,
            jobs_skipped=total_skipped,
            jobs_expired=expired,
            errors_count=errors,
            details={"feeds": per_feed},
        )
        return {
            "run_id": run_id,
            "jobs_upserted": total_upserted,
            "jobs_skipped": total_skipped,
            "jobs_expired": expired,
            "errors": errors,
            "feeds": per_feed,
        }
    except Exception as exc:
        await db.finish_run(run_id, status="failed", errors_count=errors + 1, details={"error": str(exc)})
        raise
