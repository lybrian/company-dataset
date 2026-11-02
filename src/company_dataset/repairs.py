"""One-off corrections to decisions already in the store, each recorded under its own run label.

Nothing is rewritten: new verification, identity and evidence rows are appended, and an export
picks a run up by naming it. Each step commits as one transaction.

    python -m company_dataset.repairs sr-existence --db data/store.db --run sr_existence_2026-11-03
    python -m company_dataset.repairs reresolve --db data/store.db --run identity_fix_2026-11-03 --from-runs fullrun,disc1,sr_fix_test
    python -m company_dataset.repairs reverify-recovery --db data/store.db --run recovery_reverify_2026-11-03 --from-run recovery1
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from company_dataset import store
from company_dataset.enrichment import (
    board_from_validation, clean_description, fetch_page, is_english, landing_site, linkedin_url,
)
from company_dataset.http import HttpClient
from company_dataset.enrich import board_ownership, official_landing, verify_homepage, website_supported
from company_dataset.identity import (
    CONFIRMED, careers_branded_domain, domain_compatible, linkedin_compatible, name_claims, registrable_domain, resolve_identity,
)
from company_dataset.ingest import load_boards
from company_dataset.models import Candidate, utc_now
from company_dataset.normalize import CORE_ATS, SMARTRECRUITERS, canonical_board_url, clean_website, normalize_linkedin
from company_dataset.validate import SR_NO_SUCH_COMPANY, smartrecruiters_generic_page
from company_dataset.verification import INVALID_IDENTIFIER, LIVE, VERIFIED_LIVE_ZERO_JOBS

# Identity bases whose stored name is the vendor's own: the hosted page it came from is not stored.
_VENDOR_BASES = ("vendor_only", "vendor_not_corroborated", "vendor")
_FINAL_PAGE_STATUSES = ("ok", "http_404", "http_410")


def backfill_smartrecruiters_existence(conn, run: str, now: str) -> dict:
    """Boards counted live on a totalFound=0 answer whose stored careers page fell back to generic search."""
    latest = store.latest_verifications(conn)
    invalidated = 0
    with conn:
        for r in conn.execute("SELECT id, code FROM boards WHERE ats=?", (SMARTRECRUITERS,)).fetchall():
            v = latest.get(r["id"])
            if not v or v["outcome"] != VERIFIED_LIVE_ZERO_JOBS:
                continue
            url = canonical_board_url(SMARTRECRUITERS, r["code"])
            page = store.page(conn, url)
            if not page or not smartrecruiters_generic_page(page.get("final_url") or ""):
                continue
            conn.execute("INSERT INTO verifications(board_id, checked_at, origin, endpoint, http_status, outcome, legacy_status, error, jobs_count)"
                         " VALUES (?,?,?,?,?,?,?,?,?)", (r["id"], now, run, url, 200, INVALID_IDENTIFIER, "invalid", SR_NO_SUCH_COMPANY, None))
            conn.execute("INSERT OR REPLACE INTO identities(board_id, run, status, name, basis, conflicts, decided_at) VALUES (?,?,?,?,?,?,?)",
                         (r["id"], run, "not_live", None, SR_NO_SUCH_COMPANY, "", now))
            invalidated += 1
    return {"invalidated": invalidated}


def _validation(v) -> dict:
    return {"status": v["legacy_status"], "http_status": v["http_status"], "error": v["error"], "jobs_count": v["jobs_count"],
            "code_validated": v["code_validated"], "region_answered": v["region_answered"], "company_name": v["provider_name"],
            "company_identifier": v["provider_identifier"], "website_url": v["provider_website"], "description": v["provider_description"],
            "country": v["provider_country"], "checked_at": v["checked_at"]}


def _result(conn, b: dict, v, stored_vendor_name: str | None) -> dict:
    """The shape name_claims reads, rebuilt from the store. Raw HTML is gone, so a hosted-page
    name survives only as the name its earlier decision recorded."""
    validation = _validation(v)
    board = board_from_validation(Candidate(ats=b["ats"], codes=b["codes"] or [b["code"]], region=b["region"]), validation)
    return {"board": b, "validation": validation, "careersite_url": board.careersite_url, "board_page": store.page(conn, board.careersite_url),
            "board_extract": {"names": [(stored_vendor_name, "stored_identity_name")]} if stored_vendor_name else None}


def _claims_text(claims) -> str:
    return "; ".join(f"{c.kind}:{c.origin}={c.name}" for c in claims)[:500]


def _record_identity(conn, run, board_id, ident, now):
    conn.execute("INSERT OR REPLACE INTO identities(board_id, run, status, name, basis, conflicts, decided_at) VALUES (?,?,?,?,?,?,?)",
                 (board_id, run, ident.status, ident.name, "+".join(ident.basis), " | ".join(ident.conflicts), now))


def _record_evidence(conn, run, board_id, field, value, method, url, text, now):
    conn.execute("INSERT OR IGNORE INTO field_evidence(board_id, field, value, method, evidence_url, evidence_text, status, observed_at, run)"
                 " VALUES (?,?,?,?,?,?,'verified',?,?)", (board_id, field, value, method, url, (text or "")[:500], now, run))


def reresolve_identities(conn, run: str, from_runs: list[str], now: str) -> dict:
    """Decide open boards again with the current rules. Only a move to confirmed is recorded, so
    confirmed boards and everything that stays open keep the decision they already have."""
    latest = store.latest_verifications(conn)
    marks = ",".join("?" * len(from_runs))
    open_boards = {r["board_id"]: r for r in conn.execute(
        f"SELECT i.* FROM identities i JOIN (SELECT board_id, MAX(decided_at || '|' || run) AS pick FROM identities WHERE run IN ({marks}) GROUP BY board_id) t"
        " ON i.board_id=t.board_id AND (i.decided_at || '|' || i.run)=t.pick WHERE i.status IN ('identity_unresolved', 'identity_mismatch')", from_runs)}
    stats = Counter()
    by_ats = Counter()
    with conn:
        for b in load_boards(conn):
            prior = open_boards.get(b["id"])
            v = latest.get(b["id"])
            if not prior or b["ats"] not in CORE_ATS or not v or v["outcome"] not in LIVE:
                continue
            stats["considered"] += 1
            res = _result(conn, b, v, prior["name"] if prior["basis"] in _VENDOR_BASES else None)
            claims = name_claims(res, homepage=None)
            ident = resolve_identity(claims, b["code"])
            if ident.status != CONFIRMED:
                continue
            _record_identity(conn, run, b["id"], ident, now)
            _record_evidence(conn, run, b["id"], "name", ident.name, "identity:" + "+".join(ident.basis), v["endpoint"], _claims_text(claims), now)
            stats["confirmed"] += 1
            by_ats[b["ats"]] += 1
    return {"considered": stats["considered"], "confirmed": stats["confirmed"], "by_ats": dict(sorted(by_ats.items()))}


def _slug_agrees(site: str, code: str) -> bool:
    label = re.sub(r"[^a-z0-9]", "", registrable_domain(site).split(".")[0])
    slug = re.sub(r"[^a-z0-9]", "", code.lower())
    return bool(label) and (label == slug or (len(label) >= 4 and slug.startswith(label)))


def _site_failure(site: str, page: dict | None, b: dict, names: list[str], method: str) -> tuple[str, str | None, str, bool]:
    """(reason it fails or '', landed site, evidence text, landed on a careers host)."""
    evidence = verify_homepage(page, b, names)
    if not evidence:
        return "homepage_does_not_name_company", None, "", False
    landed, on_careers = official_landing(site, landing_site(site, page))
    if not landed or careers_branded_domain(landed, names):
        return "careers_or_non_company_host", None, "", False
    if evidence.startswith("links_to_board"):
        support = website_supported(landed, page, names, method, site)
        if not support:
            return "board_link_only", None, "", False
        return "", landed, f"{evidence}; {support}", on_careers
    # A name join can land on a namesake: a site calling itself "Apollo" proves nothing about a
    # board named Apollo unless its domain or the board's slug also point at it.
    if method != "provider_website" and not any(domain_compatible(landed, n) for n in names) and not _slug_agrees(landed, b["code"]):
        return "possible_namesake", None, "", False
    return "", landed, evidence, on_careers


def reverify_recovery(conn, run: str, from_run: str, client: HttpClient, now: str, workers: int = 12, refetch: bool = False) -> dict:
    """Hold another run's reference-sourced websites to the homepage rules every other row meets.
    Boards that pass are recorded under `run`, with values re-derived from the fetched homepage.
    refetch: ignore stored pages, for when the summaries were written by an older parser."""
    rows = conn.execute(
        "SELECT i.board_id, i.name AS identity_name, e.value AS website, e.method FROM identities i JOIN field_evidence e"
        " ON e.board_id=i.board_id AND e.run=i.run AND e.field='website_url' AND e.status='verified'"
        " WHERE i.run=? AND i.status=? ORDER BY i.board_id", (from_run, CONFIRMED)).fetchall()
    sites = {r["board_id"]: clean_website(r["website"]) for r in rows}
    stale = sorted({s for s in sites.values() if s and (refetch or (store.page(conn, s) or {}).get("status") not in _FINAL_PAGE_STATUSES)})
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fetched = dict(zip(stale, ex.map(lambda u: fetch_page(client, u), stale)))
    boards = {b["id"]: b for b in load_boards(conn)}
    latest = store.latest_verifications(conn)
    stats = Counter()
    dropped = Counter()
    with conn:
        for url, summary in fetched.items():
            store.put_page(conn, url, summary)
        for r in rows:
            b, v, site = boards[r["board_id"]], latest.get(r["board_id"]), sites[r["board_id"]]
            if not v or v["outcome"] not in LIVE or not site:
                dropped["not_live_or_no_site"] += 1
                continue
            res = _result(conn, b, v, None)
            names = list(dict.fromkeys(n for n in (v["provider_name"], r["identity_name"]) if n))
            page = store.page(conn, site)
            reason, landed, evidence, on_careers = _site_failure(site, page, b, names, r["method"])
            if reason:
                dropped[reason] += 1
                continue
            owned = board_ownership(evidence, "board_link", page)
            claims = name_claims(res, page, homepage_independent=True)
            ident = resolve_identity(claims, b["code"], board_ownership=owned)
            if ident.status != CONFIRMED:
                dropped["identity_not_confirmed"] += 1
                continue
            _record_identity(conn, run, b["id"], ident, now)
            _record_evidence(conn, run, b["id"], "name", ident.name, "identity:" + "+".join(ident.basis), v["endpoint"], _claims_text(claims), now)
            _record_evidence(conn, run, b["id"], "website_url", landed, f"{r['method']}+homepage_names_company", site, evidence, now)
            _carry_description(conn, run, b["id"], page, on_careers, v, now, site)
            _carry_linkedin(conn, run, b["id"], from_run, ident.name, landed, page, now, site)
            stats["kept"] += 1
    return {"considered": len(rows), "fetched": len(fetched), "kept": stats["kept"], "dropped": dict(sorted(dropped.items()))}


def _carry_description(conn, run, board_id, page, on_careers, v, now, site):
    candidates = [] if on_careers else [(page.get("description"), "homepage_meta", site)]
    candidates.append((v["provider_description"], "provider_description", v["endpoint"]))
    for text, method, url in candidates:
        d = clean_description(text)
        if d and is_english(d):
            _record_evidence(conn, run, board_id, "description", d, method, url, d[:200], now)
            return


def _carry_linkedin(conn, run, board_id, from_run, name, website, page, now, site):
    earlier = [r["value"] for r in conn.execute("SELECT value FROM field_evidence WHERE board_id=? AND run=? AND field='linkedin_url' AND status='verified'", (board_id, from_run))]
    options = [(linkedin_url(s), "homepage_link") for s in page.get("linkedin_slugs") or []] + [(u, "earlier_run_reference") for u in earlier]
    for url, method in options:
        clean = normalize_linkedin(url)
        if clean and linkedin_compatible(clean.rsplit("/", 1)[-1], name, website):
            _record_evidence(conn, run, board_id, "linkedin_url", clean, method, site, "", now)
            return


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.repairs")
    p.add_argument("step", choices=["sr-existence", "reresolve", "reverify-recovery"])
    p.add_argument("--db", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--from-runs", default="", help="reresolve: comma-separated runs whose newest decision per board is the starting point")
    p.add_argument("--from-run", default="recovery1", help="reverify-recovery: the run whose websites are checked")
    p.add_argument("--refetch", action="store_true", help="reverify-recovery: fetch every site again instead of using stored pages")
    a = p.parse_args(argv)
    conn = store.connect(a.db)
    if a.step == "sr-existence":
        out = backfill_smartrecruiters_existence(conn, a.run, utc_now())
    elif a.step == "reresolve":
        out = reresolve_identities(conn, a.run, [r for r in a.from_runs.split(",") if r], utc_now())
    else:
        out = reverify_recovery(conn, a.run, a.from_run, HttpClient(timeout=20, per_host_interval=0.5, max_attempts=2), utc_now(), refetch=a.refetch)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
