"""Database client supporting both Turso HTTP v2 Pipeline API and local SQLite."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from job_pipeline.models import BoardRow, CompanyRecord, DiscoveredBoard, JobRecord, utc_now
from job_pipeline.normalize import (
    compute_content_hash,
    compute_job_id,
    finalize_job,
    slugify_company,
)


def split_sql_statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements, preserving BEGIN ... END; trigger blocks."""
    statements: list[str] = []
    buf: list[str] = []
    in_trigger = False
    for raw_line in sql.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(raw_line)
        upper = stripped.upper()
        if upper.startswith("CREATE TRIGGER") or " BEGIN" in upper or upper.endswith("BEGIN"):
            in_trigger = True
        if in_trigger:
            if upper.endswith("END;"):
                statements.append("\n".join(buf).strip())
                buf = []
                in_trigger = False
        elif stripped.endswith(";"):
            statements.append("\n".join(buf).strip())
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _encode_turso_arg(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _decode_turso_cell(cell: dict[str, Any]) -> Any:
    ctype = cell.get("type")
    if ctype == "null":
        return None
    if ctype == "integer":
        return int(cell["value"])
    if ctype == "float":
        return float(cell["value"])
    return cell.get("value")


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    affected_rows: int = 0
    last_insert_rowid: int | None = None


class Database:
    """Unified async interface over Turso HTTP v2 Pipeline API or local SQLite."""

    def __init__(self, database_url: str, auth_token: str | None = None, batch_size: int = 50):
        self.database_url = database_url
        self.auth_token = auth_token
        self.batch_size = batch_size
        self._sqlite: sqlite3.Connection | None = None
        self._http: httpx.AsyncClient | None = None
        self._turso_url: str | None = None

        if database_url.startswith("file:"):
            path = database_url[5:]
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._sqlite = sqlite3.connect(path)
            self._sqlite.row_factory = sqlite3.Row
            self._sqlite.execute("PRAGMA foreign_keys = ON")
            if path != ":memory:":
                self._sqlite.execute("PRAGMA journal_mode = WAL")
        else:
            http_url = database_url.replace("libsql://", "https://").rstrip("/")
            self._turso_url = f"{http_url}/v2/pipeline"
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            self._http = httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(30.0))

    async def __aenter__(self) -> "Database":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def close(self) -> None:
        if self._sqlite is not None:
            self._sqlite.close()
            self._sqlite = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> QueryResult:
        results = await self.batch([(sql, params)])
        return results[0]

    async def batch(self, statements: list[tuple[str, tuple[Any, ...] | list[Any]]]) -> list[QueryResult]:
        if not statements:
            return []
        if self._sqlite is not None:
            return self._batch_sqlite(statements)
        return await self._batch_turso(statements)

    def _batch_sqlite(self, statements: list[tuple[str, tuple[Any, ...] | list[Any]]]) -> list[QueryResult]:
        assert self._sqlite is not None
        out: list[QueryResult] = []
        with self._sqlite:
            for sql, params in statements:
                cur = self._sqlite.execute(sql, tuple(params))
                if cur.description:
                    rows = [dict(r) for r in cur.fetchall()]
                else:
                    rows = []
                out.append(
                    QueryResult(
                        rows=rows,
                        affected_rows=cur.rowcount if cur.rowcount >= 0 else 0,
                        last_insert_rowid=cur.lastrowid,
                    )
                )
        return out

    async def _batch_turso(self, statements: list[tuple[str, tuple[Any, ...] | list[Any]]]) -> list[QueryResult]:
        assert self._http is not None and self._turso_url is not None
        all_results: list[QueryResult] = []
        for i in range(0, len(statements), self.batch_size):
            chunk = statements[i : i + self.batch_size]
            requests_payload = [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": [_encode_turso_arg(a) for a in params],
                    },
                }
                for sql, params in chunk
            ]
            requests_payload.append({"type": "close"})
            resp = await self._http.post(self._turso_url, json={"requests": requests_payload})
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", [])[:-1]:
                if item.get("type") == "error":
                    msg = item.get("error", {}).get("message", "Unknown Turso error")
                    raise RuntimeError(f"Turso SQL error: {msg}")
                res = item.get("response", {}).get("result", {})
                cols = [c["name"] for c in res.get("cols", [])]
                rows = [
                    {cols[idx]: _decode_turso_cell(cell) for idx, cell in enumerate(row)}
                    for row in res.get("rows", [])
                ]
                last_id_raw = res.get("last_insert_rowid")
                all_results.append(
                    QueryResult(
                        rows=rows,
                        affected_rows=int(res.get("affected_row_count") or 0),
                        last_insert_rowid=int(last_id_raw) if last_id_raw is not None else None,
                    )
                )
        return all_results

    # ------------------------------------------------------------------
    # Schema migrations
    # ------------------------------------------------------------------

    async def migrate(self, migrations_dir: Path) -> list[str]:
        await self.execute(
            "CREATE TABLE IF NOT EXISTS _migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        res = await self.execute("SELECT version FROM _migrations")
        applied = {r["version"] for r in res.rows}
        newly_applied: list[str] = []

        for path in sorted(Path(migrations_dir).glob("*.sql")):
            version = path.stem
            if version in applied:
                continue
            stmts = split_sql_statements(path.read_text(encoding="utf-8"))
            batch_items: list[tuple[str, tuple[Any, ...]]] = [(s, ()) for s in stmts]
            batch_items.append(
                ("INSERT OR IGNORE INTO _migrations (version, applied_at) VALUES (?, ?)", (version, utc_now()))
            )
            await self.batch(batch_items)
            newly_applied.append(version)
        return newly_applied

    # ------------------------------------------------------------------
    # Boards repository
    # ------------------------------------------------------------------

    async def upsert_boards(self, boards: list[DiscoveredBoard]) -> int:
        if not boards:
            return 0
        now = utc_now()
        deduped: dict[tuple[str, str], DiscoveredBoard] = {}
        for b in boards:
            key = (b.ats, b.code_key)
            if key not in deduped or (b.company_name and not deduped[key].company_name):
                deduped[key] = b

        stmts: list[tuple[str, tuple[Any, ...]]] = []
        for b in deduped.values():
            stmts.append(
                (
                    """
                    INSERT INTO boards (ats, code_key, code, region, company_name, source, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    ON CONFLICT(ats, code_key) DO UPDATE SET
                        region = COALESCE(excluded.region, boards.region),
                        company_name = COALESCE(excluded.company_name, boards.company_name),
                        updated_at = excluded.updated_at
                    """,
                    (b.ats, b.code_key, b.code, b.region, b.company_name, b.source, now, now),
                )
            )
        await self.batch(stmts)
        return len(stmts)

    async def select_boards_for_shard(
        self,
        shard: int,
        total_shards: int,
        max_boards: int = 300,
        ats_filter: list[str] | None = None,
    ) -> list[BoardRow]:
        where = ["status = 'active'", "(id % ?) = ?"]
        params: list[Any] = [total_shards, shard]
        if ats_filter:
            placeholders = ",".join("?" for _ in ats_filter)
            where.append(f"ats IN ({placeholders})")
            params.extend(ats_filter)
        params.append(max_boards)
        sql = f"""
            SELECT id, ats, code_key, code, region, company_name, status,
                   consecutive_failures, jobs_count, last_synced_at
            FROM boards
            WHERE {' AND '.join(where)}
            ORDER BY CASE WHEN last_synced_at IS NULL THEN 0 ELSE 1 END, last_synced_at ASC, id ASC
            LIMIT ?
        """
        res = await self.execute(sql, params)
        return [
            BoardRow(
                id=int(r["id"]),
                ats=str(r["ats"]),
                code_key=str(r["code_key"]),
                code=str(r["code"]),
                region=r["region"],
                company_name=r["company_name"],
                status=str(r["status"]),
                consecutive_failures=int(r["consecutive_failures"] or 0),
                jobs_count=int(r["jobs_count"] or 0),
                last_synced_at=r["last_synced_at"],
            )
            for r in res.rows
        ]

    async def mark_board_synced(
        self,
        board_id: int,
        jobs_count: int,
        company_name: str | None = None,
        region: str | None = None,
    ) -> None:
        now = utc_now()
        await self.execute(
            """
            UPDATE boards
            SET status = 'active',
                consecutive_failures = 0,
                jobs_count = ?,
                company_name = COALESCE(?, company_name),
                region = COALESCE(?, region),
                last_error = NULL,
                last_synced_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (jobs_count, company_name, region, now, now, board_id),
        )

    async def mark_board_failed(
        self,
        board_id: int,
        error: str,
        *,
        is_not_found: bool = False,
        max_consecutive_failures: int = 3,
    ) -> None:
        now = utc_now()
        if is_not_found:
            await self.execute(
                """
                UPDATE boards
                SET consecutive_failures = consecutive_failures + 1,
                    status = CASE WHEN consecutive_failures + 1 >= ? THEN 'dead' ELSE status END,
                    last_error = ?,
                    last_synced_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (max_consecutive_failures, error[:250], now, now, board_id),
            )
        else:
            await self.execute(
                """
                UPDATE boards
                SET last_error = ?,
                    last_synced_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (error[:250], now, now, board_id),
            )

    # ------------------------------------------------------------------
    # Companies & Jobs repository
    # ------------------------------------------------------------------

    async def upsert_company(self, company: CompanyRecord) -> int | None:
        now = utc_now()
        await self.execute(
            """
            INSERT INTO companies (slug, name, website_url, logo_url, description, ats, ats_code, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = COALESCE(NULLIF(excluded.name, ''), companies.name),
                website_url = COALESCE(excluded.website_url, companies.website_url),
                logo_url = COALESCE(excluded.logo_url, companies.logo_url),
                description = COALESCE(excluded.description, companies.description),
                ats = COALESCE(excluded.ats, companies.ats),
                ats_code = COALESCE(excluded.ats_code, companies.ats_code),
                updated_at = excluded.updated_at
            """,
            (
                company.slug,
                company.name,
                company.website_url,
                company.logo_url,
                company.description,
                company.ats,
                company.ats_code,
                now,
                now,
            ),
        )
        res = await self.execute("SELECT id FROM companies WHERE slug = ?", (company.slug,))
        return int(res.rows[0]["id"]) if res.rows else None

    async def upsert_jobs(
        self,
        jobs: list[JobRecord],
        *,
        board_id: int | None = None,
        expire_missing_for_board: bool = False,
    ) -> tuple[int, int, int]:
        """Upsert normalized jobs using content_hash diffing.

        Returns (upserted_count, skipped_count, expired_count).
        """
        now = utc_now()
        prepared: list[tuple[str, str, str, JobRecord]] = []
        seen_ids: set[str] = set()
        company_map: dict[str, CompanyRecord] = {}

        for raw_job in jobs:
            job = finalize_job(raw_job)
            if not job.title or not job.apply_url:
                continue
            job_id = compute_job_id(job.source, job.external_id)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            c_slug = slugify_company(job.company_name)
            c_hash = compute_content_hash(job)
            prepared.append((job_id, c_slug, c_hash, job))
            if c_slug not in company_map:
                company_map[c_slug] = CompanyRecord(
                    slug=c_slug,
                    name=job.company_name,
                    website_url=job.company_website,
                    logo_url=job.company_logo,
                    ats=job.source if job.source_type == "ats" else None,
                )

        # Upsert companies in batch
        if company_map:
            comp_stmts = [
                (
                    """
                    INSERT INTO companies (slug, name, website_url, logo_url, ats, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        website_url = COALESCE(excluded.website_url, companies.website_url),
                        logo_url = COALESCE(excluded.logo_url, companies.logo_url),
                        ats = COALESCE(excluded.ats, companies.ats),
                        updated_at = excluded.updated_at
                    """,
                    (c.slug, c.name, c.website_url, c.logo_url, c.ats, now, now),
                )
                for c in company_map.values()
            ]
            await self.batch(comp_stmts)

        # Fetch existing hashes to skip redundant full updates (saves Turso row writes)
        existing: dict[str, tuple[str, int]] = {}
        id_list = [p[0] for p in prepared]
        for i in range(0, len(id_list), 80):
            chunk = id_list[i : i + 80]
            placeholders = ",".join("?" for _ in chunk)
            res = await self.execute(
                f"SELECT id, content_hash, is_active FROM jobs WHERE id IN ({placeholders})",
                chunk,
            )
            for r in res.rows:
                existing[str(r["id"])] = (str(r["content_hash"]), int(r["is_active"]))

        stmts: list[tuple[str, tuple[Any, ...]]] = []
        upserted = 0
        skipped = 0

        for job_id, c_slug, c_hash, job in prepared:
            prev = existing.get(job_id)
            if prev is not None and prev[0] == c_hash and prev[1] == 1:
                # Unchanged active job: touch last_seen_at only for feeds (for staleness expiry)
                if job.source_type == "feed":
                    stmts.append(("UPDATE jobs SET last_seen_at = ? WHERE id = ?", (now, job_id)))
                skipped += 1
                continue

            tags_json = json.dumps(job.tags)
            tags_text = " ".join(job.tags)
            stmts.append(
                (
                    """
                    INSERT INTO jobs (
                        id, source_type, source, external_id, board_id,
                        company_id, company_name, company_slug, company_logo,
                        title, description_html, description_text,
                        apply_url, source_url, location, country,
                        remote_type, employment_type, department, seniority,
                        tags_json, tags_text,
                        salary_min, salary_max, salary_currency, salary_period,
                        content_hash, is_active, posted_at, first_seen_at, last_seen_at, expired_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        (SELECT id FROM companies WHERE slug = ?), ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, 1, ?, ?, ?, NULL
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        company_name = excluded.company_name,
                        company_slug = excluded.company_slug,
                        company_logo = COALESCE(excluded.company_logo, jobs.company_logo),
                        title = excluded.title,
                        description_html = excluded.description_html,
                        description_text = excluded.description_text,
                        apply_url = excluded.apply_url,
                        source_url = excluded.source_url,
                        location = excluded.location,
                        country = excluded.country,
                        remote_type = excluded.remote_type,
                        employment_type = excluded.employment_type,
                        department = excluded.department,
                        seniority = excluded.seniority,
                        tags_json = excluded.tags_json,
                        tags_text = excluded.tags_text,
                        salary_min = excluded.salary_min,
                        salary_max = excluded.salary_max,
                        salary_currency = excluded.salary_currency,
                        salary_period = excluded.salary_period,
                        content_hash = excluded.content_hash,
                        is_active = 1,
                        last_seen_at = excluded.last_seen_at,
                        expired_at = NULL
                    """,
                    (
                        job_id,
                        job.source_type,
                        job.source,
                        job.external_id,
                        board_id if board_id is not None else job.board_id,
                        c_slug,
                        job.company_name,
                        c_slug,
                        job.company_logo,
                        job.title,
                        job.description_html,
                        job.description_text,
                        job.apply_url,
                        job.source_url,
                        job.location,
                        job.country,
                        job.remote_type,
                        job.employment_type,
                        job.department,
                        job.seniority,
                        tags_json,
                        tags_text,
                        job.salary_min,
                        job.salary_max,
                        job.salary_currency,
                        job.salary_period,
                        c_hash,
                        job.posted_at or now,
                        now,
                        now,
                    ),
                )
            )
            upserted += 1

        if stmts:
            await self.batch(stmts)

        expired = 0
        if expire_missing_for_board and board_id is not None:
            if seen_ids:
                placeholders = ",".join("?" for _ in seen_ids)
                res = await self.execute(
                    f"""
                    UPDATE jobs
                    SET is_active = 0, expired_at = ?
                    WHERE board_id = ? AND is_active = 1 AND id NOT IN ({placeholders})
                    """,
                    [now, board_id, *seen_ids],
                )
                expired = res.affected_rows
            else:
                res = await self.execute(
                    "UPDATE jobs SET is_active = 0, expired_at = ? WHERE board_id = ? AND is_active = 1",
                    (now, board_id),
                )
                expired = res.affected_rows

        return upserted, skipped, expired

    async def expire_stale_feed_jobs(self, days: int = 14) -> int:
        now = utc_now()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = await self.execute(
            """
            UPDATE jobs
            SET is_active = 0, expired_at = ?
            WHERE source_type = 'feed' AND is_active = 1 AND last_seen_at < ?
            """,
            (now, cutoff),
        )
        return res.affected_rows

    # ------------------------------------------------------------------
    # Ingestion run telemetry
    # ------------------------------------------------------------------

    async def start_run(self, run_type: str, shard: str | None = None) -> int:
        res = await self.execute(
            "INSERT INTO ingestion_runs (run_type, shard, started_at, status) VALUES (?, ?, ?, 'running')",
            (run_type, shard, utc_now()),
        )
        return int(res.last_insert_rowid or 0)

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str = "completed",
        boards_processed: int = 0,
        jobs_upserted: int = 0,
        jobs_skipped: int = 0,
        jobs_expired: int = 0,
        errors_count: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.execute(
            """
            UPDATE ingestion_runs
            SET finished_at = ?,
                status = ?,
                boards_processed = ?,
                jobs_upserted = ?,
                jobs_skipped = ?,
                jobs_expired = ?,
                errors_count = ?,
                details_json = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                status,
                boards_processed,
                jobs_upserted,
                jobs_skipped,
                jobs_expired,
                errors_count,
                json.dumps(details) if details else None,
                run_id,
            ),
        )
