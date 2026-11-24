"""End-to-end orchestration test for ATS shard sync, dead-board pause, and feed sync."""
from __future__ import annotations

from pathlib import Path

import httpx
import respx

from job_pipeline.config import Settings
from job_pipeline.db import Database
from job_pipeline.http_client import AsyncRateLimiter, HttpClient
from job_pipeline.models import DiscoveredBoard
from job_pipeline.sync import sync_ats_shard, sync_feeds

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


@respx.mock
async def test_e2e_ats_and_feed_sync(tmp_path):
    db_path = tmp_path / "e2e.db"
    settings = Settings(
        database_url=f"file:{db_path}",
        auth_token=None,
        migrations_dir=MIGRATIONS_DIR,
        max_consecutive_failures=2,
    )

    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 1,
                        "title": "Staff Platform Engineer",
                        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/1",
                        "location": {"name": "Remote - US"},
                        "content": "<p>Build developer infrastructure</p>",
                    }
                ]
            },
        )
    )
    respx.get("https://boards-api.greenhouse.io/v1/boards/ghost/jobs?content=true").mock(
        return_value=httpx.Response(404)
    )
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"legal": "ok"},
                {
                    "id": "rok-9",
                    "position": "Principal Go Engineer",
                    "company": "Turso",
                    "apply_url": "https://turso.tech/jobs/9",
                    "salary_min": 180000,
                    "salary_max": 220000,
                    "tags": ["go", "sqlite"],
                },
            ],
        )
    )

    async with Database(settings.database_url) as db:
        await db.migrate(MIGRATIONS_DIR)
        await db.upsert_boards(
            [
                DiscoveredBoard(ats="greenhouse", code="stripe", source="lastround", company_name="Stripe"),
                DiscoveredBoard(ats="greenhouse", code="ghost", source="lastround", company_name="Ghost"),
            ]
        )

        async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
            # First ATS sync: stripe succeeds, ghost fails (1/2)
            r1 = await sync_ats_shard(db, client, settings, shard=0, total_shards=1, max_boards=10)
            assert r1["boards_ok"] == 1
            assert r1["boards_not_found"] == 1
            assert r1["jobs_upserted"] == 1

            # Second ATS sync: ghost hits 2/2 consecutive 404s -> marked dead
            r2 = await sync_ats_shard(db, client, settings, shard=0, total_shards=1, max_boards=10)
            assert r2["jobs_skipped"] == 1
            ghost_row = await db.execute("SELECT status, consecutive_failures FROM boards WHERE code = 'ghost'")
            assert ghost_row.rows[0]["status"] == "dead"
            assert ghost_row.rows[0]["consecutive_failures"] == 2

            # Feed sync
            rf = await sync_feeds(db, client, settings, feeds=["remoteok"])
            assert rf["jobs_upserted"] == 1

        runs = await db.execute("SELECT COUNT(*) AS c FROM ingestion_runs WHERE status = 'completed'")
        assert runs.rows[0]["c"] == 3
        total_jobs = await db.execute("SELECT COUNT(*) AS c FROM jobs WHERE is_active = 1")
        assert total_jobs.rows[0]["c"] == 2
