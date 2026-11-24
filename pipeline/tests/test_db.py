"""Tests for SQL migrations, FTS5 triggers, sharded selection, and content-hash upserts."""
from __future__ import annotations

from pathlib import Path

from job_pipeline.db import Database, split_sql_statements
from job_pipeline.models import DiscoveredBoard, JobRecord

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def test_split_sql_statements_preserves_triggers():
    sql = (MIGRATIONS_DIR / "0001_initial.sql").read_text(encoding="utf-8")
    stmts = split_sql_statements(sql)
    triggers = [s for s in stmts if s.upper().startswith("CREATE TRIGGER")]
    assert len(triggers) == 3
    for t in triggers:
        assert t.upper().endswith("END;")


async def test_migrate_and_fts_search(tmp_path):
    db_file = tmp_path / "test.db"
    async with Database(f"file:{db_file}") as db:
        applied = await db.migrate(MIGRATIONS_DIR)
        assert applied == ["0001_initial"]
        # Re-running migrate is idempotent
        assert await db.migrate(MIGRATIONS_DIR) == []

        count = await db.upsert_boards(
            [
                DiscoveredBoard(ats="greenhouse", code="stripe", source="lastround", company_name="Stripe"),
                DiscoveredBoard(ats="ashby", code="linear", source="kaleb", company_name="Linear"),
            ]
        )
        assert count == 2

        boards = await db.select_boards_for_shard(shard=0, total_shards=1, max_boards=10)
        assert len(boards) == 2

        job = JobRecord(
            source_type="ats",
            source="greenhouse",
            external_id="stripe:1",
            company_name="Stripe",
            title="Staff Distributed Systems Engineer",
            apply_url="https://boards.greenhouse.io/stripe/jobs/1",
            description_html="<p>Work on Rust and Go distributed consensus systems.</p>",
            location="Remote - US",
            tags=["rust", "distributed-systems"],
            board_id=boards[0].id,
        )
        upserted, skipped, expired = await db.upsert_jobs([job], board_id=boards[0].id, expire_missing_for_board=True)
        assert (upserted, skipped, expired) == (1, 0, 0)

        # Second identical upsert should skip full write via content_hash
        upserted2, skipped2, expired2 = await db.upsert_jobs([job], board_id=boards[0].id, expire_missing_for_board=True)
        assert (upserted2, skipped2, expired2) == (0, 1, 0)

        # Verify FTS5 index matches
        fts_res = await db.execute(
            "SELECT jobs.title FROM jobs JOIN jobs_fts ON jobs_fts.rowid = jobs.rowid WHERE jobs_fts MATCH 'consensus'"
        )
        assert len(fts_res.rows) == 1
        assert fts_res.rows[0]["title"] == "Staff Distributed Systems Engineer"

        # Empty board sync expires the missing job
        _, _, expired3 = await db.upsert_jobs([], board_id=boards[0].id, expire_missing_for_board=True)
        assert expired3 == 1
        active = await db.execute("SELECT COUNT(*) AS c FROM jobs WHERE is_active = 1")
        assert active.rows[0]["c"] == 0
