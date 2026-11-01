"""Side-by-side metrics of two pilot runs, and a review sample covering successes and failures.

    python -m company_dataset.pilot_compare --runs data/pilots/pilot1 data/pilots/pilot2 data/pilots/pilot3 --export-last data/exports/pilot3
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

LIVE = ("verified_live", "verified_live_zero_jobs")
GEO = {"US": "US", "GB": "UK", "CA": "CA"}


def _old_linkedin_rule(url: str, name: str, website: str) -> bool:
    """The pilot 2 slug rule, to find LinkedIn values only the phase 1b rules accept."""
    import re

    from company_dataset.enrichment import name_key
    from company_dataset.identity import names_compatible, registrable_domain

    words = re.sub(r"[-_.]+", " ", url.rstrip("/").rsplit("/", 1)[-1])
    sk = re.sub(r"[^a-z0-9]", "", words.lower())
    if sk.isdigit():
        return True
    keys = [name_key(name)] + ([re.sub(r"[^a-z0-9]", "", registrable_domain(website).split(".")[0])] if website else [])
    for k in keys:
        if len(k) >= 3 and (sk == k or (len(k) >= 4 and k in sk and sk.startswith(k)) or (len(sk) >= 4 and sk in k and k.startswith(sk))):
            return True
    return names_compatible(words, name)


def metrics(rows: list[dict]) -> dict:
    live = [r for r in rows if r["outcome"] in LIVE]
    n = len(live) or 1

    def pct(k):
        return f"{k} ({k / n:.1%})"

    return {
        "sampled": len(rows), "live": len(live),
        "identity confirmed": pct(sum(r["identity_status"] == "identity_confirmed" for r in live)),
        "identity unresolved": pct(sum(r["identity_status"] == "identity_unresolved" for r in live)),
        "identity mismatch": pct(sum(r["identity_status"] == "identity_mismatch" for r in live)),
        "not a company board (test/old/aux)": pct(sum(r["identity_status"] == "not_a_company_board" for r in live)),
        "website verified": pct(sum(bool(r["website_url"]) for r in live)),
        "LinkedIn verified": pct(sum(bool(r["linkedin_url"]) for r in live)),
        "description verified": pct(sum(bool(r["description"]) for r in live)),
        "careersite verified": pct(sum(r.get("careersite_status") == "verified" for r in live)),
        "complete": sum(r["complete_strict"] == "True" for r in rows),
        "complete US/UK/CA": sum(r["complete_strict"] == "True" and r["country"] in GEO for r in rows),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--export-last", required=True)
    a = p.parse_args(argv)
    runs = [Path(r) for r in a.runs]
    results = [list(csv.DictReader(open(r / "results.csv", newline="", encoding="utf-8"))) for r in runs]
    ms = [metrics(r) for r in results]
    L = ["| metric | " + " | ".join(r.name for r in runs) + " |", "|---" * (len(runs) + 1) + "|"]
    L += [f"| {k} | " + " | ".join(str(m[k]) for m in ms) + " |" for k in ms[0]]
    out = "\n".join(L)
    print(out)
    last = runs[-1]
    (last / "comparison.md").write_text(out + "\n")
    rb = results[-1]
    a.b, a.export_b = str(last), a.export_last

    rnd = random.Random(20261101)
    live = [r for r in rb if r["outcome"] in LIVE]
    groups = {
        "complete_random": [r for r in rb if r["complete_strict"] == "True"],
        "mismatch_random": [r for r in live if r["identity_status"] == "identity_mismatch"],
        "unresolved_with_website": [r for r in live if r["identity_status"] == "identity_unresolved" and r["website_url"]],
        "unresolved_no_website": [r for r in live if r["identity_status"] == "identity_unresolved" and not r["website_url"]],
        "confirmed_incomplete": [r for r in live if r["identity_status"] == "identity_confirmed" and r["complete_strict"] != "True"],
        "not_a_company_board": [r for r in live if r["identity_status"] == "not_a_company_board"],
        "confirmed_by_board_ownership": [r for r in live if "board_ownership" in r.get("identity_basis", "")],
        "linkedin_new_rules": [r for r in live if r["linkedin_url"] and r["complete_strict"] == "True"
                               and not _old_linkedin_rule(r["linkedin_url"], r["name"], r["website_url"])],
    }
    sizes = {"complete_random": 60, "mismatch_random": 25, "unresolved_with_website": 20, "unresolved_no_website": 15,
             "confirmed_incomplete": 20, "not_a_company_board": 15, "confirmed_by_board_ownership": 30, "linkedin_new_rules": 30}
    merges = [r for r in csv.DictReader(open(Path(a.export_b) / "companies_all_confirmed.csv", newline="", encoding="utf-8")) if r["other_boards"]]
    cols = ["group", "ats_system", "ats_code", "identity_status", "identity_basis", "identity_conflicts", "name", "website_url", "website_method",
            "linkedin_url", "linkedin_method", "description", "careersite_status", "country", "flags", "other_boards"]
    with open(Path(a.b) / "review_sample_v2.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for g, members in groups.items():
            for r in rnd.sample(members, min(sizes[g], len(members))):
                w.writerow({**r, "group": g})
        for r in merges:
            w.writerow({"group": "merge", "ats_system": r["ats_system"], "ats_code": r["ats_code"], "name": r["company_name"],
                        "website_url": r["website_url"], "linkedin_url": r["linkedin_url"], "other_boards": r["other_boards"]})
    print({g: min(sizes[g], len(m)) for g, m in groups.items()}, "merges", len(merges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
