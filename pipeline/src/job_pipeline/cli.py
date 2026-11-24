"""CLI entrypoint for the Turso job ingestion pipeline."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from job_pipeline.config import Settings
from job_pipeline.db import Database
from job_pipeline.http_client import HttpClient
from job_pipeline.sync import sync_ats_shard, sync_discovery, sync_feeds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-pipeline", description="Async job board ingestion pipeline for Turso")
    parser.add_argument("--db-url", default=None, help="Override TURSO_DATABASE_URL (e.g. file:local.db or libsql://...)")
    parser.add_argument("--auth-token", default=None, help="Override TURSO_AUTH_TOKEN")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Apply SQL migrations to the database")

    p_disc = sub.add_parser("discover", help="Discover ATS board slugs and upsert into boards table")
    p_disc.add_argument("--sources", default="all", help="Comma-separated groups: registries,yc,hn,vc or 'all'")

    p_ats = sub.add_parser("ingest-ats", help="Sync a shard of active ATS boards into Turso")
    p_ats.add_argument("--shard", type=int, default=0, help="0-indexed shard number")
    p_ats.add_argument("--total-shards", type=int, default=1, help="Total number of shards")
    p_ats.add_argument("--max-boards", type=int, default=300, help="Max boards to process in this shard")
    p_ats.add_argument("--ats", default="", help="Optional comma-separated ATS filter (e.g. greenhouse,lever,ashby)")
    p_ats.add_argument("--concurrency", type=int, default=20, help="Max concurrent board fetches")

    p_feeds = sub.add_parser("ingest-feeds", help="Fetch direct public job feeds into Turso")
    p_feeds.add_argument("--feeds", default="all", help="Comma-separated feed names or 'all'")

    return parser


async def _run(args: argparse.Namespace) -> dict:
    settings = Settings.from_env(database_url=args.db_url, auth_token=args.auth_token)
    async with Database(settings.database_url, settings.auth_token, batch_size=settings.batch_size) as db:
        if args.command == "migrate":
            applied = await db.migrate(settings.migrations_dir)
            return {"command": "migrate", "applied": applied}

        async with HttpClient(
            timeout=settings.http_timeout,
            max_retries=settings.max_retries,
            user_agent=settings.user_agent,
        ) as client:
            if args.command == "discover":
                groups = None if args.sources == "all" else [s.strip() for s in args.sources.split(",") if s.strip()]
                return await sync_discovery(db, client, groups=groups)

            if args.command == "ingest-ats":
                ats_filter = [a.strip().lower() for a in args.ats.split(",") if a.strip()] or None
                return await sync_ats_shard(
                    db,
                    client,
                    settings,
                    shard=args.shard,
                    total_shards=args.total_shards,
                    max_boards=args.max_boards,
                    ats_filter=ats_filter,
                    concurrency=args.concurrency,
                )

            if args.command == "ingest-feeds":
                feeds = None if args.feeds == "all" else [f.strip().lower() for f in args.feeds.split(",") if f.strip()]
                return await sync_feeds(db, client, settings, feeds=feeds)

    raise ValueError(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(_run(args))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
