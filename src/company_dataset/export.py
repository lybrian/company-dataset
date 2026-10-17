from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from company_dataset import reference as reference_mod
from company_dataset.build import load_candidates
from company_dataset.enrichment import board_from_validation, is_auxiliary_board, is_test_board, name_key
from company_dataset.models import REQUIRED_FIELDS, utc_now
from company_dataset.normalize import host_of
from company_dataset.resolve import resolve_board, slug_matches

COMPANY_COLUMNS = [
    "name",
    "description",
    "linkedin_url",
    "website_url",
    "careersite_url",
    "ats_system",
    "ats_code",
    "country",
    "jobs_count",
    "also_on_ats",
    "other_boards",
    "name_source",
    "description_source",
    "linkedin_source",
    "website_source",
    "country_source",
    "validated_at",
    "sources",
]

REJECT_COLUMNS = [
    "source",
    "reason",
    "detail",
    "row_ref",
    "ats_system",
    "ats_code",
    "name",
    "careersite_url",
    "raw_json",
]

# The same description on this many unrelated companies is template text, not theirs.
SHARED_DESCRIPTION_LIMIT = 3


def _read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return default


def _load_source_rejects(dirs: dict) -> list[list]:
    path = dirs["intermediate"] / "source_rejects.csv"
    rows: list[list] = []
    if not path.exists():
        return rows
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append([
                row["source"],
                row["reason"],
                row["detail"],
                row["row_ref"],
                row.get("ats") or "",
                row.get("code") or "",
                "",
                "",
                row.get("raw_json") or "",
            ])
    return rows


def missing_fields(row: dict) -> list[str]:
    return [f for f in REQUIRED_FIELDS if not str(row.get(f) or "").strip()]


def _filled(row: dict) -> int:
    return len(REQUIRED_FIELDS) - len(missing_fields(row))


def drop_conflicting_linkedin(rows: list[dict]) -> int:
    """A LinkedIn page shared by different websites belongs to at most the rows it names."""
    by_li: dict[str, set] = defaultdict(set)
    for row in rows:
        if row["linkedin_url"]:
            by_li[row["linkedin_url"].lower()].add(host_of(row["website_url"]))
    dropped = 0
    for row in rows:
        li = row["linkedin_url"]
        if li and len(by_li[li.lower()]) > 1:
            slug = li.rsplit("/", 1)[-1]
            if not slug_matches(slug, row["name"], row["website_url"]):
                row["linkedin_url"] = ""
                row["linkedin_source"] = ""
                dropped += 1
    return dropped


def drop_shared_descriptions(rows: list[dict]) -> int:
    by_desc: dict[str, set] = defaultdict(set)
    for row in rows:
        if row["description"]:
            by_desc[row["description"].casefold()].add(host_of(row["website_url"]) or row["ats_code"])
    dropped = 0
    for row in rows:
        d = row["description"]
        if d and len(by_desc[d.casefold()]) >= SHARED_DESCRIPTION_LIMIT:
            row["description"] = ""
            row["description_source"] = ""
            dropped += 1
    return dropped


def _jobs(row: dict) -> int:
    return int(row["jobs_count"]) if str(row["jobs_count"]).isdigit() else -1


def collapse_companies(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """One row per company, across all three ATSes.

    Boards are the same company when they share a website, or share a LinkedIn page
    and also have matching names (a parent's LinkedIn on a subsidiary's site alone is
    not enough). The most complete board is kept, then the one with the most jobs; the
    rest are listed in `other_boards` and returned as extras.
    """
    from company_dataset.enrichment import names_match

    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    by_host: dict[str, int] = {}
    by_li: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        host = host_of(row["website_url"])
        if host:
            if host in by_host:
                union(i, by_host[host])
            else:
                by_host[host] = i
        if row["linkedin_url"]:
            by_li[row["linkedin_url"].lower()].append(i)
    for members in by_li.values():
        for a in members:
            for b in members:
                if a < b and names_match(rows[a]["name"], rows[b]["name"]):
                    union(a, b)

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    keep: list[dict] = []
    extras: list[dict] = []
    for group in groups.values():
        group.sort(key=lambda r: (-_filled(r), -_jobs(r), r["ats_system"], r["ats_code"].casefold()))
        primary = group[0]
        others = group[1:]
        primary["also_on_ats"] = ";".join(sorted({r["ats_system"] for r in others} - {primary["ats_system"]}))
        primary["other_boards"] = ";".join(f"{r['ats_system']}:{r['ats_code']}" for r in others)
        keep.append(primary)
        extras.extend(others)
    return keep, extras


DETAILED_COLUMNS = COMPANY_COLUMNS + ["complete", "missing_fields"]


def _by_name(row: dict):
    return ((row["name"] or "~").casefold(), row["ats_system"], row["ats_code"].casefold())


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_export(dirs: dict, ref=None) -> dict:
    candidates = load_candidates(dirs)
    cache = _read_json(dirs["cache"] / "validation.json", {}) or {}
    pages = _read_json(dirs["cache"] / "pages.json", {}) or {}
    ref = ref if ref is not None else reference_mod.load_saved(dirs)
    build_stats = _read_json(dirs["intermediate"] / "build_stats.json", {}) or {}
    manifest = _read_json(dirs["intermediate"] / "manifest.json", []) or []

    live: list[dict] = []
    validation_rejects: list[list] = []
    for cand in candidates:
        ats, code = cand.ats, cand.code
        sources = "; ".join(cand.sources)
        careersites = "; ".join(cand.careersite_urls)
        outcome = cache.get(cand.key)
        if outcome is None:
            validation_rejects.append([sources, "not_validated", "no validation result; run validate stage", "", ats, code, cand.name or "", careersites, ""])
            continue
        if outcome.get("status") != "valid":
            reason = "validation_failed" if outcome.get("status") == "invalid" else "validation_unresolved"
            detail = f'http={outcome.get("http_status")} error={outcome.get("error") or ""}'
            validation_rejects.append([sources, reason, detail, "", ats, code, cand.name or "", careersites, ""])
            continue
        board = board_from_validation(cand, outcome)
        res = resolve_board(board, outcome, pages, ref, source_name=cand.name or "", source_name_origin=cand.name_source)
        if any(is_test_board(n, board.code) for n in (res.name, outcome.get("company_name"), cand.name)):
            validation_rejects.append([sources, "test_or_demo_board", "vendor sandbox / demo / test board, not a company", "", ats, board.code, res.name or outcome.get("company_name") or "", board.careersite_url, ""])
            continue
        if any(is_auxiliary_board(n) for n in (res.name, outcome.get("company_name"))):
            validation_rejects.append([sources, "auxiliary_board", "internal / referral / talent-pool board, not the company's main board", "", ats, board.code, res.name or outcome.get("company_name") or "", board.careersite_url, ""])
            continue
        if res.careersite_status == "dead":
            validation_rejects.append([sources, "careersite_unavailable", "vendor API answers but the hosted board page is gone", "", ats, board.code, res.name, board.careersite_url, ""])
            continue
        live.append({
            "name": res.name,
            "description": res.description,
            "linkedin_url": res.linkedin_url,
            "website_url": res.website_url,
            "careersite_url": board.careersite_url,
            "ats_system": ats,
            "ats_code": board.code,
            "country": res.country,
            "jobs_count": outcome.get("jobs_count") if outcome.get("jobs_count") is not None else "",
            "also_on_ats": "",
            "other_boards": "",
            **res.sources,
            "validated_at": outcome.get("checked_at") or "",
            "sources": sources,
        })

    linkedin_conflicts = drop_conflicting_linkedin(live)
    shared_descriptions = drop_shared_descriptions(live)
    kept, extra_boards = collapse_companies(live)
    for row in extra_boards:
        validation_rejects.append([row["sources"], "duplicate_company_board", f"same company as a kept board ({host_of(row['website_url']) or row['linkedin_url']})", "", row["ats_system"], row["ats_code"], row["name"], row["careersite_url"], ""])

    for row in kept:
        row["missing_fields"] = ";".join(missing_fields(row))
        row["complete"] = "no" if row["missing_fields"] else "yes"
    kept.sort(key=_by_name)
    complete = [r for r in kept if r["complete"] == "yes"]
    incomplete = [r for r in kept if r["complete"] == "no"]

    # Hand-off files: exactly the required fields.
    write_csv(dirs["output"] / "companies.csv", list(REQUIRED_FIELDS), complete)
    write_csv(dirs["output"] / "companies_incomplete.csv", list(REQUIRED_FIELDS) + ["missing_fields"], incomplete)

    # Review files: provenance, rejects and possible duplicates, for checking the work.
    review = Path(dirs.get("review") or Path(dirs["data"]) / "review")
    write_csv(review / "companies_detailed.csv", DETAILED_COLUMNS, complete + incomplete)
    rejects = _load_source_rejects(dirs) + validation_rejects
    review.mkdir(parents=True, exist_ok=True)
    with open(review / "rejected_records.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(REJECT_COLUMNS)
        writer.writerows(rejects)

    per_source = build_stats.get("per_source", {})
    contributed = Counter(s for cand in candidates for s in cand.sources)
    source_rows: list[dict] = []
    for entry in manifest:
        name = entry.get("source", "")
        src_stats = per_source.get(name, {})
        source_rows.append({
            "source": name,
            "role": entry.get("role", "boards"),
            "description": entry.get("description", ""),
            "download_url": entry.get("download_url", ""),
            "license": entry.get("license", ""),
            "license_url": entry.get("license_url", ""),
            "license_note": entry.get("license_note", ""),
            "attribution": entry.get("attribution", ""),
            "downloaded_at": entry.get("downloaded_at") or "",
            "sha256": entry.get("sha256", ""),
            "size_bytes": entry.get("size_bytes", ""),
            "rows_read": src_stats.get("rows_read", ""),
            "in_scope_records": src_stats.get("records", ""),
            "rejected_rows": src_stats.get("rejects", ""),
            "contributed_candidates": contributed.get(name, ""),
        })
    with open(dirs["output"] / "source_manifest.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(source_rows[0].keys()) if source_rows else ["source"])
        writer.writeheader()
        writer.writerows(source_rows)

    def completeness(rows):
        total = len(rows)
        return {f: {"non_null": sum(1 for r in rows if r[f]), "total": total, "pct": round(100 * sum(1 for r in rows if r[f]) / total, 2) if total else 0.0} for f in REQUIRED_FIELDS}

    def countries(rows):
        c = Counter(r["country"] for r in rows if r["country"])
        focus = sum(c[k] for k in ("US", "GB", "CA"))
        return {
            "rows_with_country": sum(c.values()),
            "us_uk_ca": focus,
            "us_uk_ca_pct": round(100 * focus / len(rows), 2) if rows else 0.0,
            "breakdown": dict(c.most_common()),
        }

    names = Counter(name_key(r["name"]) for r in kept if len(name_key(r["name"])) >= 3)
    same_name = [r for r in kept if names[name_key(r["name"])] > 1]
    write_csv(
        review / "possible_duplicates.csv",
        ["name", "ats_system", "ats_code", "website_url", "linkedin_url", "careersite_url"],
        sorted(same_name, key=lambda r: (name_key(r["name"]), r["ats_system"], r["ats_code"])),
    )
    reject_reasons = Counter(r[1] for r in validation_rejects)
    live_sources = [[s for s in r["sources"].split("; ") if s] for r in live]
    source_overlap = {
        "by_source_count": dict(sorted(Counter(len(s) for s in live_sources).items())),
        "in_live_boards": dict(Counter(x for s in live_sources for x in s)),
        "sole_source_for": dict(Counter(s[0] for s in live_sources if len(s) == 1)),
    }
    export_stats = {
        "generated_at": utc_now(),
        "live_boards": len(live),
        "live_companies_after_collapse": len(kept),
        "complete_companies": len(complete),
        "complete_unique_websites": len({host_of(r["website_url"]) for r in complete}),
        "incomplete_companies": len(incomplete),
        "complete_by_ats": dict(Counter(r["ats_system"] for r in complete)),
        "live_by_ats": dict(Counter(r["ats_system"] for r in kept)),
        "completeness_live": completeness(kept),
        "missing_field_counts": dict(Counter(f for r in incomplete for f in r["missing_fields"].split(";") if f)),
        "country_complete": countries(complete),
        "country_live": countries(kept),
        "sources_complete": {k: dict(Counter(r[k] for r in complete)) for k in ("name_source", "website_source", "linkedin_source", "description_source", "country_source")},
        "linkedin_conflicts_dropped": linkedin_conflicts,
        "shared_descriptions_dropped": shared_descriptions,
        "boards_merged_into_companies": len(extra_boards),
        "same_name_not_merged": len(same_name),
        "same_name_not_merged_in_deliverable": sum(1 for r in same_name if not missing_fields(r)),
        "post_validation_rejects": dict(reject_reasons),
        "source_overlap": source_overlap,
        "rejected_rows_total": len(rejects),
    }
    (dirs["intermediate"] / "export_stats.json").write_text(json.dumps(export_stats, indent=2))
    print(
        f"[export] live boards={len(live)} companies={len(kept)} complete={len(complete)} "
        f"incomplete={len(incomplete)} rejects={dict(reject_reasons)}"
    )
    return export_stats
