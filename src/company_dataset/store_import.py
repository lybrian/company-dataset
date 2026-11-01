"""Idempotent import of source files, legacy validation caches, page caches and QA re-checks."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from company_dataset import store
from company_dataset.export import _validation_endpoint
from company_dataset.sources import SOURCES
from company_dataset.verification import classify


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def import_sources(conn: sqlite3.Connection, raw_dir: Path, now: str, modules=SOURCES) -> dict:
    """Every adapter output row (records and rejects) becomes one source_rows row, in order.

    A source already imported from the same file checksum is skipped; a different checksum
    for an already-imported source is refused, so history is never silently replaced.
    """
    report = {}
    for mod in modules:
        meta = mod.META
        path = Path(raw_dir) / meta.name / meta.filename
        if not path.exists():
            report[meta.name] = {"status": "file_missing", "path": str(path)}
            continue
        digest = _sha256(path)
        existing = conn.execute("SELECT id, file_sha256, rows_read FROM sources WHERE name=?", (meta.name,)).fetchone()
        if existing and existing["file_sha256"] == digest:
            report[meta.name] = {"status": "already_imported", "rows_read": existing["rows_read"]}
            continue
        if existing:
            raise RuntimeError(f"{meta.name}: already imported from a different file ({existing['file_sha256'][:12]} != {digest[:12]})")
        records, rejects = mod.parse(path)
        with conn:
            cur = conn.execute(
                "INSERT INTO sources(name, url, license, file_path, file_sha256, rows_read, imported_at) VALUES (?,?,?,?,?,?,?)",
                (meta.name, meta.download_url, meta.license, str(path), digest, len(records) + len(rejects), now),
            )
            sid = cur.lastrowid
            seq = 0
            for rec in records:
                bid = store.board_id(conn, rec.ats, rec.code, rec.region)
                if rec.region == "eu":
                    conn.execute("UPDATE boards SET region='eu' WHERE id=? AND region IS NULL", (bid,))
                conn.execute(
                    "INSERT INTO source_rows(source_id, seq, row_ref, board_id, ats, code, region, name, careersite_url) VALUES (?,?,?,?,?,?,?,?,?)",
                    (sid, seq, rec.row_ref, bid, rec.ats, rec.code, rec.region, rec.name, rec.careersite_url),
                )
                seq += 1
            for rej in rejects:
                conn.execute(
                    "INSERT INTO source_rows(source_id, seq, row_ref, ats, code, reject_reason, reject_detail) VALUES (?,?,?,?,?,?,?)",
                    (sid, seq, rej.row_ref, rej.ats or None, rej.code or None, rej.reason, rej.detail),
                )
                seq += 1
        report[meta.name] = {"status": "imported", "records": len(records), "rejects": len(rejects), "sha256": digest}
    return report


def _insert_check(conn, bid: int, ats: str, code: str, rec: dict, origin: str) -> bool:
    cur = conn.execute(
        "INSERT OR IGNORE INTO verifications(board_id, checked_at, origin, endpoint, http_status, outcome, legacy_status, error,"
        " jobs_count, code_validated, region_answered, provider_name, provider_identifier, provider_website,"
        " provider_description, provider_country) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            bid, rec["checked_at"], origin, _validation_endpoint(ats, code, rec), rec.get("http_status"),
            classify(rec.get("status"), rec.get("http_status"), rec.get("error"), rec.get("jobs_count")),
            rec.get("status"), rec.get("error"), rec.get("jobs_count"), rec.get("code_validated"), rec.get("region_answered"),
            rec.get("company_name"), rec.get("company_identifier"), rec.get("website_url"), rec.get("description"), rec.get("country"),
        ),
    )
    return cur.rowcount == 1


def import_validation_cache(conn: sqlite3.Connection, path: Path, origin: str) -> dict:
    """Legacy validation.json → verifications. Entries for boards no source lists are counted, not invented."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = {(r["ats"], r["code_key"]): r["id"] for r in conn.execute("SELECT id, ats, code_key FROM boards")}
    stats = Counter(entries=len(data))
    with conn:
        for key, rec in data.items():
            ats, _, code_key = key.partition(":")
            bid = keys.get((ats, code_key))
            if bid is None:
                stats["no_source_row"] += 1
                continue
            if not rec.get("checked_at"):
                stats["no_checked_at"] += 1
                continue
            if _insert_check(conn, bid, ats, rec.get("code") or code_key, rec, origin):
                stats["inserted"] += 1
            else:
                stats["already_present"] += 1
    return dict(stats)


def import_qa_rechecks(conn: sqlite3.Connection, path: Path, origin: str) -> dict:
    """qa.py jsonl: the fresh provider re-check of each delivered row."""
    keys = {(r["ats"], r["code_key"]): r["id"] for r in conn.execute("SELECT id, ats, code_key FROM boards")}
    stats = Counter()
    with conn:
        for line in open(path, encoding="utf-8"):
            j = json.loads(line)
            stats["entries"] += 1
            bid = keys.get((j["ats"], j["code"].casefold()))
            if bid is None:
                stats["no_source_row"] += 1
                continue
            rec = {
                "status": j.get("api_status"), "http_status": j.get("api_http"), "error": j.get("api_error"),
                "jobs_count": j.get("api_jobs"), "company_name": j.get("api_name"), "checked_at": j["checked_at"],
            }
            if _insert_check(conn, bid, j["ats"], j["code"], rec, origin):
                stats["inserted"] += 1
            else:
                stats["already_present"] += 1
    return dict(stats)


def import_pages(conn: sqlite3.Connection, path: Path) -> dict:
    """Page summaries; when caches disagree the most recently fetched copy wins."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    stats = Counter(entries=len(data))
    with conn:
        for url, summary in data.items():
            row = conn.execute("SELECT fetched_at FROM pages WHERE url=?", (url,)).fetchone()
            if row and (row[0] or "") >= (summary.get("fetched_at") or ""):
                stats["kept_existing"] += 1
                continue
            store.put_page(conn, url, summary)
            stats["written"] += 1
    return dict(stats)


def main(argv=None) -> int:
    """python -m company_dataset.store_import --db data/store.db --raw data/raw_2026-10-31
       --cache ORIGIN=path/validation.json ... --pages path/pages.json ... --qa ORIGIN=path.jsonl ..."""
    import argparse

    from company_dataset.models import utc_now

    p = argparse.ArgumentParser(prog="company_dataset.store_import")
    p.add_argument("--db", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--cache", action="append", default=[], help="ORIGIN=path to a legacy validation.json")
    p.add_argument("--pages", action="append", default=[])
    p.add_argument("--qa", action="append", default=[], help="ORIGIN=path to a qa.py jsonl")
    p.add_argument("--report", help="write the import report JSON here")
    a = p.parse_args(argv)
    conn = store.connect(a.db)
    report = {"started_at": utc_now(), "sources": import_sources(conn, Path(a.raw), utc_now())}
    report["caches"] = {}
    for spec in a.cache:
        origin, _, path = spec.partition("=")
        report["caches"][origin] = import_validation_cache(conn, Path(path), origin)
        print(origin, report["caches"][origin], flush=True)
    report["qa"] = {}
    for spec in a.qa:
        origin, _, path = spec.partition("=")
        report["qa"][origin] = import_qa_rechecks(conn, Path(path), origin)
    report["pages"] = {p_: import_pages(conn, Path(p_)) for p_ in a.pages}
    report["finished_at"] = utc_now()
    out = json.dumps(report, indent=1)
    if a.report:
        Path(a.report).write_text(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
