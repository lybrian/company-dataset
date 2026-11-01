"""Discovery-yield report for a discovery source: how many discoveries survive each stage.

    python -m company_dataset.discovery_report --db data/store.db --source commoncrawl_extra \
        --cache data/raw_cc_extra_2026-11-01/commoncrawl_extra/harvest_cache.json.gz \
        --run ccx1 --export data/exports/ccx1 --known data/exports/pilot1 ... --legacy data/runs/2026-10-31-final4/output/companies_total.csv \
        --out data/pilots/ccx1/discovery_report.json

discovered -> unique board new to the store -> provider-live -> identity-confirmed -> complete
-> complete company not already known. The last stages are measured on the pilot sample and
projected per ATS onto all new boards (estimates, not verified companies).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from company_dataset import store
from company_dataset.identity import registrable_domain
from company_dataset.pilot_report import wilson
from company_dataset.verification import LIVE

GEO = {"US": "US", "GB": "UK", "UK": "UK", "CA": "CA"}


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def crawl_curve(cache_path: Path) -> list[dict]:
    """Cumulative unique boards as crawls are added, newest first: how much each crawl adds."""
    cache = json.loads(gzip.decompress(cache_path.read_bytes()))
    by_crawl = defaultdict(set)
    for key, v in cache.items():
        crawl = key.split("|", 1)[0]
        for o in v["observations"]:
            by_crawl[crawl].add((o[0], o[1].casefold()))
    seen, out = set(), []
    for crawl in sorted(by_crawl, reverse=True):
        new = by_crawl[crawl] - seen
        seen |= by_crawl[crawl]
        out.append({"crawl": crawl, "boards_in_crawl": len(by_crawl[crawl]), "new_vs_newer_crawls": len(new), "cumulative": len(seen)})
    return out


def store_overlap(conn, source: str) -> dict:
    """Per ATS: discovered boards, how many other sources already listed, how many are new."""
    rows = conn.execute(
        "SELECT b.ats, sr.board_id, (SELECT COUNT(DISTINCT s2.source_id) FROM source_rows s2 WHERE s2.board_id=sr.board_id AND s2.source_id<>sr.source_id) AS others"
        " FROM source_rows sr JOIN sources s ON s.id=sr.source_id JOIN boards b ON b.id=sr.board_id WHERE s.name=?", (source,)).fetchall()
    out = defaultdict(lambda: {"discovered": 0, "already_in_store": 0, "new_boards": 0})
    for r in rows:
        o = out[r["ats"]]
        o["discovered"] += 1
        o["already_in_store" if r["others"] else "new_boards"] += 1
    return dict(sorted(out.items()))


def known_keys(exports: list[Path], legacy: Path | None) -> tuple[set, set]:
    domains, linkedins = set(), set()
    files = [e / "companies_all_confirmed.csv" for e in exports] + ([legacy] if legacy else [])
    for f in files:
        for r in _read(f):
            if r.get("website_url"):
                domains.add(registrable_domain(r["website_url"]))
            if r.get("linkedin_url"):
                linkedins.add(r["linkedin_url"].rstrip("/").lower())
    return domains, linkedins


def funnel(export: Path, domains: set, linkedins: set) -> dict:
    boards = _read(export / "boards.csv")
    complete = _read(export / "companies_complete.csv")
    confirmed = _read(export / "companies_all_confirmed.csv")
    per = defaultdict(Counter)
    for r in boards:
        c = per[r["ats_system"]]
        c["sampled"] += 1
        c["provider_live"] += r["verification_status"] in LIVE
        c["identity_confirmed"] += r["verification_status"] in LIVE and r["identity_status"] == "identity_confirmed"
    for r in confirmed:
        per[r["ats_system"]]["unique_companies"] += 1
    geo = Counter()
    for r in complete:
        c = per[r["ats_system"]]
        c["complete_companies"] += 1
        known = registrable_domain(r["website_url"]) in domains or r["linkedin_url"].rstrip("/").lower() in linkedins
        c["complete_already_known"] += known
        c["complete_new_companies"] += not known
        g = GEO.get((r.get("country") or "").upper(), "other" if r.get("country") else "unknown")
        geo[(r["ats_system"], g)] += 1
        geo[("all", g)] += 1
        if not known and g in ("US", "UK", "CA"):
            c["complete_new_us_uk_ca"] += 1
    return {"per_ats": {k: dict(v) for k, v in sorted(per.items())},
            "complete_by_geo": {f"{a}|{g}": n for (a, g), n in sorted(geo.items())}}


def project(overlap: dict, f: dict) -> dict:
    """Per ATS: new boards x the sample's rate of complete, not-already-known companies (Wilson 95%)."""
    out, tot = {}, Counter()
    for ats, o in overlap.items():
        s = f["per_ats"].get(ats)
        if not s or not s.get("sampled"):
            continue
        n = s["sampled"]
        for key in ("complete_new_companies", "complete_new_us_uk_ca"):
            k = s.get(key, 0)
            lo, hi = wilson(k, n)
            est = {"rate": round(k / n, 4), "estimate": round(o["new_boards"] * k / n), "low": round(o["new_boards"] * lo), "high": round(o["new_boards"] * hi)}
            out.setdefault(ats, {"new_boards": o["new_boards"], "sampled": n})[key] = est
            for x in ("estimate", "low", "high"):
                tot[f"{key}_{x}"] += est[x]
    out["total"] = dict(tot)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.discovery_report")
    p.add_argument("--db", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--export", required=True)
    p.add_argument("--known", action="append", default=[], help="verified exports whose companies count as already known")
    p.add_argument("--legacy", help="legacy output used only to flag likely-known companies")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if Path(a.out).exists():
        raise SystemExit(f"refusing to overwrite {a.out}")
    conn = store.connect(a.db)
    overlap = store_overlap(conn, a.source)
    domains, linkedins = known_keys([Path(x) for x in a.known], Path(a.legacy) if a.legacy else None)
    f = funnel(Path(a.export), domains, linkedins)
    report = {"crawl_curve": crawl_curve(Path(a.cache)), "store_overlap": overlap, "funnel": f, "projection": project(overlap, f)}
    Path(a.out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["projection"]["total"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
