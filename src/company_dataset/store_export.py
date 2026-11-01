"""Export one run's companies from the store. Deterministic: same store + run -> byte-identical files.

    python -m company_dataset.store_export --db data/store.db --run pilot1 --out data/exports/pilot1

Counts are kept apart: candidate boards (in the run), live boards, identity-confirmed boards,
unique companies (clusters), complete companies.

Stored websites are re-checked with the current website rules using stored pages only (no
fetches); a website that fails is dropped with the fields found through it, and listed in
website_rule_changes.csv. The rules can only remove a verification, never add one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from company_dataset import store
from company_dataset.identity import CONFIRMED, careers_branded_domain, cluster_companies
from company_dataset.normalize import clean_website, host_of
from company_dataset.verification import LIVE

REQUIRED = ["company_name", "description", "linkedin_url", "website_url", "careersite_url", "ats_system", "ats_code"]
EXTRA = ["country", "verification_status", "verification_date", "verification_endpoint", "jobs_count", "identity_status", "identity_basis",
         "careersite_evidence", "website_method", "linkedin_method", "description_method", "sources", "company_id", "other_boards", "board_id"]
FIELD_FOR = {"name": "company_name", "description": "description", "linkedin_url": "linkedin_url", "website_url": "website_url",
             "careersite_url": "careersite_url", "ats_system": "ats_system", "ats_code": "ats_code", "country": "country"}


def board_rows(conn, run: str) -> list[dict]:
    """One row per board decided in this run, built only from stored evidence."""
    rows, websites = {}, {}
    q = ("SELECT i.board_id, i.status, i.name, i.basis, b.ats, b.code FROM identities i JOIN boards b ON b.id=i.board_id"
         " WHERE i.run=? ORDER BY i.board_id")
    for r in conn.execute(q, (run,)):
        rows[r["board_id"]] = {"board_id": r["board_id"], "identity_status": r["status"], "identity_basis": r["basis"] or "",
                               "ats_system": r["ats"], "ats_code": r["code"], **{c: "" for c in REQUIRED[:5]},
                               "country": "", "careersite_evidence": "", "website_method": "", "linkedin_method": "", "description_method": ""}
    # Newest evidence per (board, field); a 'candidate' careersite (page blocked) is reported, not counted as verified.
    for r in conn.execute("SELECT board_id, field, value, method, evidence_url, evidence_text, status FROM field_evidence WHERE run=? ORDER BY board_id, field, observed_at, id", (run,)):
        row = rows.get(r["board_id"])
        if row is None:
            continue
        col = FIELD_FOR.get(r["field"])
        if r["field"] == "careersite_url":
            row["careersite_evidence"] = r["status"] + ":" + r["method"]
            row["careersite_url"] = r["value"]
            row["_careersite_landed"] = r["evidence_url"] or ""
        elif col and r["status"] == "verified":
            row[col] = r["value"]
            if r["field"] in ("website_url", "linkedin_url", "description"):
                row[r["field"].split("_")[0] + "_method"] = r["method"]
            if r["field"] == "website_url":
                websites[r["board_id"]] = r
            if r["field"] == "country":
                row["_country_method"] = r["method"]
    latest = {}
    for r in conn.execute("SELECT * FROM verifications WHERE origin=? ORDER BY board_id, checked_at", (run,)):
        latest[r["board_id"]] = r
    for bid, row in rows.items():
        v = latest.get(bid)
        row["verification_status"] = v["outcome"] if v else ""
        row["verification_date"] = v["checked_at"] if v else ""
        row["verification_endpoint"] = v["endpoint"] if v else ""
        row["jobs_count"] = "" if not v or v["jobs_count"] is None else v["jobs_count"]
        if row["identity_status"] != CONFIRMED:
            row["company_name"] = ""
    srcs: dict[int, list[str]] = {}
    for r in conn.execute("SELECT DISTINCT sr.board_id, s.name FROM source_rows sr JOIN sources s ON s.id=sr.source_id WHERE sr.board_id IS NOT NULL ORDER BY sr.board_id, s.name"):
        if r[0] in rows:
            srcs.setdefault(r[0], []).append(r[1])
    names = {r["board_id"]: r["name"] for r in conn.execute("SELECT board_id, name FROM identities WHERE run=?", (run,))}
    for bid, row in rows.items():
        row["sources"] = ";".join(srcs.get(bid, []))
        if bid in websites:
            row["_website_rule"] = website_rule_failure(conn, websites[bid], names.get(bid))
            if row["_website_rule"]:
                drop_website(row)
    return [rows[k] for k in sorted(rows)]


def website_rule_failure(conn, w, name: str | None) -> str:
    """Why a stored website fails the current rules ('' if it passes)."""
    from company_dataset.pilot import website_supported

    names = [name] if name else []
    if not clean_website(w["value"]):
        return "careers_platform_or_non_company_host"
    if careers_branded_domain(w["value"], names):
        return "careers_branded_domain"
    basis = w["method"].split("+")[0]
    if (w["evidence_text"] or "").startswith("links_to_board") and not website_supported(
            w["value"], store.page(conn, w["evidence_url"]), names, basis, w["evidence_url"]):
        return "board_link_only:domain_and_homepage_do_not_name_company"
    return ""


def drop_website(row: dict) -> None:
    """LinkedIn is only looked for on a verified website, homepage descriptions and domain-based
    countries come from it: all go with it. Vendor descriptions and job-location countries stay."""
    row["_dropped_website"] = row["website_url"]
    row["website_url"] = row["website_method"] = ""
    row["linkedin_url"] = row["linkedin_method"] = ""
    if row["description_method"].startswith("homepage_meta"):
        row["description"] = row["description_method"] = ""
    if row.get("_country_method", "").endswith("by_verified_domain"):
        row["country"] = ""
    # A careersite counted as verified because the board redirected to the dropped site's domain.
    landed = host_of(row.get("_careersite_landed", ""))
    if row["careersite_evidence"].startswith("verified") and landed and landed != host_of(row["careersite_url"]):
        row["careersite_evidence"] = "unverified:redirected_to_dropped_website"


def is_complete(row: dict) -> bool:
    return (row["identity_status"] == CONFIRMED and row["verification_status"] in LIVE
            and row["careersite_evidence"].startswith("verified") and all(row[c] for c in REQUIRED))


def run_export(conn, run: str, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    rows = board_rows(conn, run)
    confirmed = [r for r in rows if r["identity_status"] == CONFIRMED and r["verification_status"] in LIVE]
    clusters = cluster_companies([{"name": r["company_name"], "website_url": r["website_url"], "website_verified": bool(r["website_url"]),
                                   "linkedin_url": r["linkedin_url"], "ats_system": r["ats_system"], "ats_code": r["ats_code"]} for r in confirmed])
    companies, links = [], []
    for g in clusters:
        members = sorted((confirmed[i] for i in g), key=lambda r: (not is_complete(r), -sum(bool(r[c]) for c in REQUIRED),
                                                                    -(int(r["jobs_count"] or 0)), r["ats_system"], r["ats_code"].casefold()))
        primary = dict(members[0])
        cid = f"c{primary['board_id']}"
        primary["company_id"] = cid
        primary["other_boards"] = ";".join(f"{m['ats_system']}:{m['ats_code']}" for m in members[1:])
        companies.append(primary)
        for m in members:
            links.append({"company_id": cid, "board_id": m["board_id"], "ats_system": m["ats_system"], "ats_code": m["ats_code"],
                          "role": "primary" if m is members[0] else "same_company"})
    companies.sort(key=lambda r: (r["company_name"].casefold(), r["ats_system"], r["ats_code"].casefold()))
    complete = [r for r in companies if is_complete(r)]
    unresolved = [r for r in rows if not (r["identity_status"] == CONFIRMED and r["verification_status"] in LIVE)]
    rule_changes = [{"board_id": r["board_id"], "ats_system": r["ats_system"], "ats_code": r["ats_code"], "identity_status": r["identity_status"],
                     "company_name": r["company_name"], "website_url": r["_dropped_website"], "reason": r["_website_rule"]}
                    for r in rows if r.get("_website_rule")]

    out.mkdir(parents=True)
    cols = REQUIRED + EXTRA
    _write(out / "companies_complete.csv", cols, complete)
    _write(out / "companies_all_confirmed.csv", cols + ["missing_fields"], [{**r, "missing_fields": ";".join(c for c in REQUIRED if not r[c]) or ("careersite_unverified" if not is_complete(r) else "")} for r in companies])
    _write(out / "boards.csv", cols, rows)
    _write(out / "company_boards.csv", ["company_id", "board_id", "ats_system", "ats_code", "role"], links)
    _write(out / "unresolved_boards.csv", cols, unresolved)
    _write(out / "website_rule_changes.csv", ["board_id", "ats_system", "ats_code", "identity_status", "company_name", "website_url", "reason"], rule_changes)
    counts = {
        "run": run,
        "candidate_boards_in_run": len(rows),
        "live_boards": sum(1 for r in rows if r["verification_status"] in LIVE),
        "identity_confirmed_live_boards": len(confirmed),
        "unique_companies": len(companies),
        "complete_companies": len(complete),
        "boards_by_outcome": dict(sorted(Counter(r["verification_status"] for r in rows).items())),
        "identity_by_status": dict(sorted(Counter(r["identity_status"] for r in rows).items())),
        "websites_dropped_by_current_rules": dict(sorted(Counter(r["reason"] for r in rule_changes).items())),
    }
    (out / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}
    (out / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in digests.items()))
    return counts


def _write(path: Path, cols: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.store_export")
    p.add_argument("--db", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    print(json.dumps(run_export(store.connect(a.db), a.run, Path(a.out)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
