"""Compare two store exports of the same run, board by board, and attribute every change.

    python -m company_dataset.export_diff --old data/exports/pilot3 --new data/exports/pilot3_phase1c --out data/exports/pilot3_phase1c_diff

Causes: 'website_rule' (the board is in either export's website_rule_changes.csv; 'restored:'
when only the old export dropped its website) and
'merge' (the board's company grouping changed). Any other changed board is 'unexplained'.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

GROUPING = ("company_id", "other_boards")


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _groups(export: Path) -> dict[str, frozenset[str]]:
    by_company: dict[str, set[str]] = {}
    for r in _read(export / "company_boards.csv"):
        by_company.setdefault(r["company_id"], set()).add(r["board_id"])
    return {b: frozenset(m) for m in by_company.values() for b in m}


def _rule_changes(export: Path) -> dict[str, str]:
    p = export / "website_rule_changes.csv"
    return {r["board_id"]: r["reason"] for r in _read(p)} if p.exists() else {}


def diff(old: Path, new: Path) -> tuple[list[dict], dict]:
    old_rows = {r["board_id"]: r for r in _read(old / "boards.csv")}
    new_rows = {r["board_id"]: r for r in _read(new / "boards.csv")}
    # A board dropped by the website rules in either export: a newer rule can also restore a website.
    rule = {b: "restored:" + r for b, r in _rule_changes(old).items()}
    rule.update(_rule_changes(new))
    og, ng = _groups(old), _groups(new)
    old_complete = {r["board_id"] for r in _read(old / "companies_complete.csv")}
    new_complete = {r["board_id"] for r in _read(new / "companies_complete.csv")}
    changes = []
    for bid in sorted(set(old_rows) | set(new_rows), key=int):
        o, n = old_rows.get(bid, {}), new_rows.get(bid, {})
        fields = [c for c in sorted(set(o) | set(n)) if c not in GROUPING and o.get(c) != n.get(c)]
        regrouped = og.get(bid) != ng.get(bid)
        if not (fields or regrouped or (bid in old_complete) != (bid in new_complete)):
            continue
        causes = (["website_rule"] if bid in rule else []) + (["merge"] if regrouped else [])
        changes.append({
            "board_id": bid, "ats_system": n.get("ats_system") or o.get("ats_system"), "ats_code": n.get("ats_code") or o.get("ats_code"),
            "company_name": n.get("company_name") or o.get("company_name"), "cause": "+".join(causes) or "unexplained",
            "reason": rule.get(bid, ""), "fields_changed": ";".join(fields),
            "old_website": o.get("website_url", ""), "new_website": n.get("website_url", ""),
            "complete": {(True, True): "stays_complete", (True, False): "no_longer_complete", (False, True): "newly_complete",
                         (False, False): "not_complete"}[(bid in old_complete, bid in new_complete)],
            "old_company_boards": len(og.get(bid, ())), "new_company_boards": len(ng.get(bid, ())),
        })
    summary = {
        "boards_compared": len(set(old_rows) | set(new_rows)),
        "boards_changed": len(changes),
        "by_cause": dict(sorted(Counter(c["cause"] for c in changes).items())),
        "by_reason": dict(sorted(Counter(c["reason"] for c in changes if c["reason"]).items())),
        "by_completeness": dict(sorted(Counter(c["complete"] for c in changes).items())),
        "fields_changed": dict(sorted(Counter(f for c in changes for f in c["fields_changed"].split(";") if f).items())),
        "unexplained": sum(1 for c in changes if c["cause"] == "unexplained"),
        "counts_old": json.loads((old / "counts.json").read_text()),
        "counts_new": json.loads((new / "counts.json").read_text()),
    }
    return changes, summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="company_dataset.export_diff")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    changes, summary = diff(Path(a.old), Path(a.new))
    out.mkdir(parents=True)
    with open(out / "changed_boards.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(changes[0]) if changes else ["board_id"], lineterminator="\n")
        w.writeheader()
        w.writerows(changes)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith("counts")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
