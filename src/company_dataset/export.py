"""Export: deliverable files from the store. Deterministic: same store + same runs -> byte-identical files.

    python -m company_dataset.export --db data/store.db --runs fullrun,disc1 --out data/exports/final_YYYY-MM-DD
    python -m company_dataset.export --db data/store.db --run pilot1 --out data/exports/pilot1

--run exports one run; --runs merges several, where a board decided in more than one keeps its
newest run's decision and evidence. Counts are kept apart: candidate boards, live boards,
identity-confirmed boards, unique companies (clusters), complete companies. Companies are clustered
with cluster_companies (strong shared keys + matching names), never on a name alone.

Stored websites are re-checked with the current website rules using stored pages only (no
fetches); a website that fails is dropped with the fields found through it. The rules can only
remove a verification, never add one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from company_dataset import store
from company_dataset.enrich import website_supported
from company_dataset.identity import CONFIRMED, careers_branded_domain, cluster_companies
from company_dataset.normalize import canonical_board_url, clean_website, host_of
from company_dataset.verification import LIVE

REQUIRED = ["company_name", "description", "linkedin_url", "website_url", "careersite_url", "ats_system", "ats_code"]
RUN_EXTRA = ["country", "verification_status", "verification_date", "verification_endpoint", "jobs_count", "identity_status", "identity_basis",
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
    cols = REQUIRED + RUN_EXTRA
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


EXTRA = ["country", "verification_status", "verification_date", "verification_endpoint", "jobs_count",
         "identity_status", "identity_basis", "identity_conflicts", "run"]
BOARD_COLS = ["board_id", "ats_system", "ats_code", "region", "sources", "run", "identity_status", "identity_basis", "identity_conflicts",
              "verification_status", "verification_date", "verification_endpoint", "jobs_count", "company_name",
              "description", "linkedin_url", "website_url", "careersite_url", "careersite_evidence", "country"]


def _latest_identity_per_board(conn, runs: list[str]) -> dict[int, dict]:
    """Return identity row (newest run) per board across the given runs, joined with boards for ats/code."""
    qmarks = ",".join("?" * len(runs))
    q = (f"SELECT i.*, b.ats, b.code FROM identities i JOIN boards b ON b.id=i.board_id JOIN"
         f" (SELECT board_id, MAX(decided_at || '|' || run) AS pick FROM identities WHERE run IN ({qmarks}) GROUP BY board_id) t"
         f" ON i.board_id=t.board_id AND (i.decided_at || '|' || i.run)=t.pick")
    id_rows = {r["board_id"]: r for r in conn.execute(q, runs)}
    return id_rows


def _latest_field_evidence_per_board_field(conn, runs: list[str]) -> dict[tuple[int, str], dict]:
    """Return newest verified field_evidence per (board, field) across runs."""
    qmarks = ",".join("?" * len(runs))
    q = (f"SELECT e.* FROM field_evidence e JOIN"
         f" (SELECT board_id, field, MAX(observed_at || '|' || id) AS pick FROM field_evidence WHERE run IN ({qmarks}) AND status='verified' GROUP BY board_id, field) t"
         f" ON e.board_id=t.board_id AND e.field=t.field AND (e.observed_at || '|' || e.id)=t.pick")
    ev_rows = {}
    for r in conn.execute(q, runs):
        ev_rows[(r["board_id"], r["field"])] = r
    return ev_rows


def decided_rows(conn, runs: list[str]) -> list[dict]:
    """One merged row per board: newest identity run + per-field newest verified evidence across all runs."""
    # Get newest identity per board (includes board_id, status, name, basis, ats, code, etc.)
    id_map = _latest_identity_per_board(conn, runs)
    regions = {r[0]: r[1] for r in conn.execute("SELECT id, region FROM boards")}
    # Get newest verified evidence per (board, field) across all runs
    ev_map = _latest_field_evidence_per_board_field(conn, runs)
    # Sources per board
    srcs = defaultdict(list)
    for r in conn.execute("SELECT DISTINCT sr.board_id, s.name FROM source_rows sr JOIN sources s ON s.id=sr.source_id WHERE sr.board_id IS NOT NULL ORDER BY sr.board_id, s.name"):
        srcs[r[0]].append(r[1])
    
    out = []
    for bid in sorted(id_map):
        ident = id_map[bid]
        run = ident["run"]
        row = {"board_id": bid, "identity_status": ident["status"], "identity_basis": ident["basis"] or "",
               "identity_conflicts": ident["conflicts"] or "", "run": run, "region": regions.get(bid) or "",
               "ats_system": ident["ats"], "ats_code": ident["code"],
               "company_name": "", "description": "", "linkedin_url": "", "website_url": "",
               "careersite_url": "", "careersite_evidence": "", "country": "",
               "website_method": "", "linkedin_method": "", "description_method": "",
               "verification_status": "", "verification_date": "", "verification_endpoint": "", "jobs_count": "",
               "sources": ";".join(srcs.get(bid, []))}
        
        # Newest verification per board across runs (verification origin = run)
        qmarks = ",".join("?" * len(runs))
        v = conn.execute(
            f"SELECT v.* FROM verifications v JOIN"
            f" (SELECT board_id, MAX(checked_at) AS at_ FROM verifications WHERE origin IN ({qmarks}) GROUP BY board_id) t"
            f" ON v.board_id=t.board_id AND v.checked_at=t.at_ WHERE v.board_id=?", runs + [bid]
        ).fetchone()
        if v:
            row["verification_status"] = v["outcome"]
            row["verification_date"] = v["checked_at"]
            row["verification_endpoint"] = v["endpoint"] or ""
            row["jobs_count"] = "" if v["jobs_count"] is None else v["jobs_count"]
        
        # Fields from evidence (only if identity confirmed and status verified)
        FIELD_FOR = {"name": "company_name", "description": "description", "linkedin_url": "linkedin_url",
                     "website_url": "website_url", "careersite_url": "careersite_url",
                     "ats_system": "ats_system", "ats_code": "ats_code", "country": "country"}
        if row["identity_status"] == CONFIRMED:
            for field, col in FIELD_FOR.items():
                key = (bid, field)
                if key in ev_map:
                    ev = ev_map[key]
                    row[col] = ev["value"]
                    if field in ("website_url", "linkedin_url", "description"):
                        row[field.split("_")[0] + "_method"] = ev["method"]
                    if field == "careersite_url":
                        row["careersite_evidence"] = f"{ev['status']}:{ev['method']}"
                        row["_careersite_landed"] = ev["evidence_url"] or ""
                    if field == "country":
                        row["_country_method"] = ev["method"]
                    if field == "website_url":
                        row["_website_evidence"] = {"method": ev["method"], "url": ev["evidence_url"] or "",
                                                    "evidence_text": ev["evidence_text"] or "",
                                                    "status": ev["status"]}
        
        # Website rule re-check on merged website evidence (if present)
        if row.get("_website_evidence"):
            w = row["_website_evidence"]
            # Build verification-style dict for website_rule_failure: value = verified website URL
            w_legacy = {"value": row["website_url"], "method": w["method"], "evidence_url": w["url"], "evidence_text": w["evidence_text"] or ""}
            # Use identity name from the identity row
            ident_name = ident["name"] if ident["name"] else None
            rule = website_rule_failure(conn, w_legacy, ident_name)
            if rule:
                drop_website(row)
        
        # If identity not confirmed, wipe company name (per legacy behavior)
        if row["identity_status"] != CONFIRMED:
            row["company_name"] = ""
        
        row.pop("_website_evidence", None)  # internal, not exported
        out.append(row)
    return out


def build_export(conn, runs: list[str], out_dir: Path) -> dict:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = decided_rows(conn, runs)
    confirmed = [r for r in rows if r["identity_status"] == CONFIRMED and r["verification_status"] in LIVE]
    clusters = cluster_companies([{"name": r["company_name"], "website_url": r["website_url"], "website_verified": bool(r["website_url"]),
                                   "linkedin_url": r["linkedin_url"], "ats_system": r["ats_system"], "ats_code": r["ats_code"]}
                                  for r in confirmed])
    companies, links, merges = [], [], []
    for g in clusters:
        members = sorted((confirmed[i] for i in g), key=lambda r: (not is_complete(r), -sum(bool(r[c]) for c in REQUIRED),
                                                                   -(int(r["jobs_count"] or 0)), r["ats_system"], r["ats_code"].casefold()))
        primary = dict(members[0])
        cid = f"c{primary['board_id']}"
        primary["company_id"] = cid
        primary["other_boards"] = ";".join(f"{m['ats_system']}:{m['ats_code']}" for m in members[1:])
        companies.append(primary)
        if len(members) > 1:
            merges.append({"company_id": cid, "name": primary["company_name"],
                           "primary_board": f"{primary['ats_system']}:{primary['ats_code']}",
                           "merged_boards": ";".join(f"{m['ats_system']}:{m['ats_code']}" for m in members[1:]),
                           "primary_website": primary["website_url"], "primary_linkedin": primary["linkedin_url"],
                           "shared_website": len({m["website_url"] for m in members if m["website_url"]}) == 1 and bool(members[-1]["website_url"]),
                           "shared_linkedin": len({m["linkedin_url"] for m in members if m["linkedin_url"]}) == 1 and bool(members[-1]["linkedin_url"]),
                           "boards_count": len(members)})
    companies.sort(key=lambda r: (r["company_name"].casefold(), r["ats_system"], r["ats_code"].casefold()))
    merges.sort(key=lambda r: r["company_id"])
    complete = [r for r in companies if is_complete(r)]
    incomplete = [r for r in companies if not is_complete(r)]
    unresolved = [r for r in rows if r["identity_status"] in ("identity_unresolved", "identity_mismatch") and r["verification_status"] in LIVE]

    # possible duplicates: same company name, different company records
    seen_names: dict[str, list[str]] = defaultdict(list)
    for r in companies:
        seen_names[r["company_name"].casefold()].append(f"{r['ats_system']}:{r['ats_code']}:{r['company_id']}")
    possible = [{"name_form": name, "instances": ";".join(sorted(instances)), "count": len(instances)}
                for name, instances in sorted(seen_names.items()) if len(instances) > 1]

    # verification evidence trail: every field_evidence row for boards decided in the runs
    qmarks = ",".join("?" * len(runs))
    evidence_q = ("SELECT e.board_id, e.field, e.value, e.method, e.evidence_url, e.evidence_text, e.status,"
                  " e.observed_at, e.run, b.ats, b.code FROM field_evidence e JOIN boards b ON b.id=e.board_id"
                  f" WHERE e.run IN ({qmarks}) ORDER BY e.board_id, e.field, e.observed_at, e.run")
    evidence = [{"board_id": r[0], "field": r[1], "value": r[2], "method": r[3], "evidence_url": r[4],
                 "evidence_text": r[5], "status": r[6], "observed_at": r[7], "run": r[8],
                 "ats_system": r[9], "ats_code": r[10]} for r in conn.execute(evidence_q, runs)]

    # rejected records: every source row the adapters refused (global, not run-specific)
    rejects_q = ("SELECT s.name AS source_name, sr.row_ref, sr.ats, sr.code, sr.region, sr.name, sr.reject_reason, sr.reject_detail"
                 " FROM source_rows sr JOIN sources s ON s.id=sr.source_id WHERE sr.board_id IS NULL ORDER BY s.name, sr.row_ref")
    rejects = [{"source_name": r[0], "row_ref": r[1], "ats_system": r[2], "ats_code": r[3], "region": r[4] or "",
                "name_from_source": r[5] or "", "reject_reason": r[6] or "", "reject_detail": r[7] or ""}
               for r in conn.execute(rejects_q)]

    # unresolved: candidate boards the ATS serves as live but whose company identity stays unconfirmed
    unresolved_rows = []
    for r in unresolved:
        unresolved_rows.append({
            "board_id": r["board_id"], "ats_system": r["ats_system"], "ats_code": r["ats_code"], "region": r["region"],
            "sources": r["sources"], "run": r["run"], "identity_status": r["identity_status"], "identity_basis": r["identity_basis"],
            "verification_status": r["verification_status"], "verification_date": r["verification_date"],
            "endpoint_public_jobs": canonical_board_url(r["ats_system"], r["ats_code"], r["region"]),
            "careersite_url": r["careersite_url"], "website_url": r["website_url"]})

    # source breakdown across the whole store
    breakdown = []
    for s in conn.execute("SELECT id, name, url, rows_read, imported_at FROM sources ORDER BY name").fetchall():
        sid, name = s["id"], s["name"]
        pairs_q = ("SELECT COUNT(DISTINCT COALESCE(board_id, ats||'|'||code)) FROM source_rows WHERE source_id=?")
        boards_q = ("SELECT COUNT(DISTINCT sr.board_id) FROM source_rows sr WHERE sr.source_id=? AND sr.board_id IN"
                    f" (SELECT board_id FROM identities i WHERE i.run IN ({qmarks}))")
        records = conn.execute("SELECT COUNT(*) FROM source_rows WHERE source_id=?", (sid,)).fetchone()[0]
        boards_total = conn.execute(pairs_q, (sid,)).fetchone()[0]
        decided = conn.execute(boards_q, (sid, *runs)).fetchone()[0]
        live_qmarks = ",".join("?" * len(LIVE))
        live = conn.execute("SELECT COUNT(DISTINCT sr.board_id) FROM source_rows sr JOIN verifications v ON v.board_id=sr.board_id"
                            f" WHERE sr.source_id=? AND v.outcome IN ({live_qmarks}) AND v.origin IN ({qmarks})",
                            (sid, *LIVE, *runs)).fetchone()[0]
        breakdown.append({"source": name, "url": s["url"] or "", "rows_read": s["rows_read"], "records": records,
                          "rejects": records - conn.execute("SELECT COUNT(*) FROM source_rows WHERE source_id=? AND board_id IS NOT NULL", (sid,)).fetchone()[0],
                          "boards_contributed": boards_total, "boards_decided": decided, "live_boards": live,
                          "imported_at": s["imported_at"]})

    # spot check: deterministic 1-in-N sample of complete companies, review-ready
    n = max(1, len(complete) // 30) if complete else 0
    spots = []
    for r in complete[:: n or 1]:
        spots.append({"company_name": r["company_name"], "description": r["description"], "linkedin_url": r["linkedin_url"],
                      "website_url": r["website_url"], "careersite_url": r["careersite_url"],
                      "ats_board": f"{r['ats_system']}:{r['ats_code']}", "website_method": r["website_method"],
                      "linkedin_method": r["linkedin_method"], "careersite_evidence": r["careersite_evidence"],
                      "country": r["country"], "jobs_count": r["jobs_count"]})
    spot = {"sample_n": len(spots), "method": "every Nth complete company after sort (N=%d)" % n}

    cols = REQUIRED + EXTRA
    _write(out_dir / "companies_verified.csv", REQUIRED, complete)
    _write(out_dir / "companies_all_confirmed.csv", cols + ["missing_fields", "other_boards"],
           [{**r, "missing_fields": ";".join(c for c in REQUIRED if not r[c]) or ("careersite_unverified" if not is_complete(r) else "")} for r in companies])
    _write(out_dir / "companies_incomplete.csv", cols + ["missing_fields", "other_boards"],
           [{**r, "missing_fields": ";".join(c for c in REQUIRED if not r[c]) or ("careersite_unverified" if not is_complete(r) else "")} for r in incomplete])
    _write(out_dir / "boards_all.csv", BOARD_COLS, rows)
    _write(out_dir / "duplicates_and_merges.csv", ["company_id", "name", "primary_board", "merged_boards", "primary_website",
                                                   "primary_linkedin", "shared_website", "shared_linkedin", "boards_count"], merges)
    _write(out_dir / "possible_duplicates.csv", ["name_form", "instances", "count"], possible)
    _write(out_dir / "verification_evidence.csv",
           ["board_id", "ats_system", "ats_code", "field", "status", "value", "method", "evidence_url", "evidence_text", "observed_at", "run"],
           evidence)
    _write(out_dir / "rejected_records.csv",
           ["source_name", "row_ref", "ats_system", "ats_code", "region", "name_from_source", "reject_reason", "reject_detail"], rejects)
    _write(out_dir / "unresolved_records.csv",
           ["board_id", "ats_system", "ats_code", "region", "sources", "run", "identity_status", "identity_basis",
            "verification_status", "verification_date", "endpoint_public_jobs", "careersite_url", "website_url"], unresolved_rows)
    _write(out_dir / "source_breakdown.csv",
           ["source", "url", "rows_read", "records", "rejects", "boards_contributed", "boards_decided", "live_boards", "imported_at"], breakdown)
    _write(out_dir / "spot_check.csv", ["company_name", "description", "linkedin_url", "website_url", "careersite_url",
                                        "ats_board", "website_method", "linkedin_method", "careersite_evidence", "country", "jobs_count"], spots)

    counts = {
        "runs": runs,
        "boards_decided": len(rows),
        "live_boards": sum(1 for r in rows if r["verification_status"] in LIVE),
        "boards_not_live": len(rows) - sum(1 for r in rows if r["verification_status"] in LIVE),
        "identity_confirmed_live_boards": len(confirmed),
        "unique_companies": len(companies),
        "complete_companies": len(complete),
        "incomplete_companies": len(incomplete),
        "unresolved_live_boards": len(unresolved),
        "merged_companies": len(merges),
        "evidence_rows": len(evidence),
        "rejected_records": len(rejects),
        "source_breakdown": len(breakdown),
        "spot_check": spot,
        "boards_by_ats": {},
        "companies_by_ats": {},
        "boards_by_outcome": dict(sorted(Counter(r["verification_status"] for r in rows).items())),
        "identity_by_status": dict(sorted(Counter(r["identity_status"] for r in rows).items())),
        "sources": sorted({s for r in rows for s in (r["sources"] or "").split(";") if s}),
    }
    for ats in sorted({r["ats_system"] for r in rows}):
        g = [r for r in rows if r["ats_system"] == ats]
        cs = [r for r in companies if r["ats_system"] == ats]
        counts["boards_by_ats"][ats] = {
            "boards": len(g),
            "live": sum(1 for r in g if r["verification_status"] in LIVE),
            "not_live": sum(1 for r in g if r["verification_status"] not in LIVE),
            "identity_confirmed_live": sum(1 for r in g if r["identity_status"] == CONFIRMED and r["verification_status"] in LIVE),
            "unique_companies": len(cs),
            "complete_companies": sum(1 for r in cs if is_complete(r)),
        }
        counts["companies_by_ats"][ats] = {
            "unique_companies": len(cs),
            "complete_companies": sum(1 for r in cs if is_complete(r)),
            "incomplete_companies": sum(1 for r in cs if not is_complete(r)),
            "merged_companies": sum(1 for m in merges if m["primary_board"].startswith(f"{ats}:")),
        }
    (out_dir / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out_dir.iterdir())}
    (out_dir / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in digests.items()))
    return counts


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.export")
    p.add_argument("--db", required=True)
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--run", help="export one run")
    which.add_argument("--runs", help="comma-separated run labels to merge")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    conn = store.connect(a.db)
    counts = run_export(conn, a.run, Path(a.out)) if a.run else build_export(conn, [r for r in a.runs.split(",") if r], Path(a.out))
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
