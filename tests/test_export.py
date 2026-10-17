import csv
import json

from company_dataset.export import (
    collapse_companies,
    drop_conflicting_linkedin,
    drop_shared_descriptions,
    run_export,
)
from company_dataset.models import REQUIRED_FIELDS
from company_dataset.reference import Reference


def _dirs(tmp_path):
    dirs = {
        "data": tmp_path,
        "raw": tmp_path / "raw",
        "cache": tmp_path / "cache",
        "intermediate": tmp_path / "intermediate",
        "output": tmp_path / "output",
        "review": tmp_path / "review",
        "reports": tmp_path / "reports",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _write_candidates(dirs, rows):
    path = dirs["intermediate"] / "candidates.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ats", "code", "alt_codes", "region", "name", "name_source", "careersite_urls", "sources"])
        for row in rows:
            writer.writerow(row)


def _valid(ats, code, **kw):
    base = {
        "ats": ats, "code": code, "status": "valid", "http_status": 200, "jobs_count": 5,
        "company_name": None, "description": None, "website_url": None, "country": None,
        "country_basis": None, "region_answered": None, "code_validated": code, "error": None,
        "checked_at": "2026-10-17T00:00:00Z",
    }
    base.update(kw)
    return base


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


HOME = {
    "status": "ok", "final_url": "https://acme.com/", "site_name": "Acme", "title": "Acme",
    "description": "Acme makes anvils for the construction industry.",
    "linkedin_slugs": ["acme"], "board_refs": [],
}


def test_required_fields_is_the_real_seven_business_fields():
    assert tuple(REQUIRED_FIELDS) == (
        "name", "description", "linkedin_url", "website_url", "careersite_url", "ats_system", "ats_code",
    )


def test_complete_rows_in_companies_csv_incomplete_separate(tmp_path):
    dirs = _dirs(tmp_path)
    _write_candidates(dirs, [
        ["greenhouse", "acme", "", "", "Acme Inc", "lastroundai", "", "latmay"],
        ["greenhouse", "bare", "", "", "", "", "", "latmay"],
    ])
    cache = {
        "greenhouse:acme": _valid("greenhouse", "acme", company_name="Acme", website_url="https://acme.com"),
        "greenhouse:bare": _valid("greenhouse", "bare", company_name="Bare Co"),
    }
    (dirs["cache"] / "validation.json").write_text(json.dumps(cache))
    (dirs["cache"] / "pages.json").write_text(json.dumps({"https://acme.com": HOME}))

    stats = run_export(dirs, ref=Reference())

    complete = _read(dirs["output"] / "companies_complete.csv")
    assert list(complete[0]) == list(REQUIRED_FIELDS)
    assert [r["ats_code"] for r in complete] == ["acme"]
    row = complete[0]
    assert all(row[f] for f in REQUIRED_FIELDS)
    assert row["linkedin_url"] == "https://www.linkedin.com/company/acme"
    assert row["careersite_url"] == "https://job-boards.greenhouse.io/acme"
    incomplete = _read(dirs["output"] / "companies_incomplete.csv")
    assert list(incomplete[0]) == list(REQUIRED_FIELDS) + ["missing_fields"]
    assert incomplete[0]["ats_code"] == "bare"
    assert incomplete[0]["missing_fields"] == "description;linkedin_url;website_url"
    assert stats["complete_companies"] == 1
    detailed = _read(dirs["review"] / "companies_detailed.csv")
    assert [(r["ats_code"], r["complete"]) for r in detailed] == [("acme", "yes"), ("bare", "no")]
    assert detailed[0]["website_source"] == "greenhouse_job_url_origin"
    total = _read(dirs["output"] / "companies_total.csv")
    assert list(total[0]) == list(REQUIRED_FIELDS) + ["complete", "missing_fields"]
    assert [(r["ats_code"], r["complete"], r["missing_fields"]) for r in total] == [("acme", "yes", ""), ("bare", "no", "description;linkedin_url;website_url")]
    assert sorted(f.name for f in dirs["output"].iterdir()) == ["companies_complete.csv", "companies_incomplete.csv", "companies_total.csv", "source_manifest.csv"]


def test_dead_careersite_and_invalid_boards_are_rejected(tmp_path):
    dirs = _dirs(tmp_path)
    _write_candidates(dirs, [
        ["lever", "siepe", "", "", "", "", "", "latmay"],
        ["lever", "deadco", "", "", "", "", "", "latmay"],
        ["ashby", "notyet", "", "", "", "", "", "latmay"],
    ])
    cache = {
        "lever:siepe": _valid("lever", "siepe", jobs_count=0),
        "lever:deadco": _valid("lever", "deadco", status="invalid", http_status=404, error="board_not_found"),
    }
    (dirs["cache"] / "validation.json").write_text(json.dumps(cache))
    (dirs["cache"] / "pages.json").write_text(json.dumps({"https://jobs.lever.co/siepe": {"status": "http_404"}}))

    stats = run_export(dirs, ref=Reference())

    assert stats["live_boards"] == 0
    reasons = sorted(r["reason"] for r in _read(dirs["review"] / "rejected_records.csv"))
    assert reasons == ["careersite_unavailable", "not_validated", "validation_failed"]


def _row(code, website, linkedin="", description="", ats="greenhouse", name=None, jobs=1):
    return {
        "name": name or code.title(), "description": description, "linkedin_url": linkedin,
        "website_url": website, "careersite_url": f"https://b/{code}", "ats_system": ats, "ats_code": code,
        "jobs_count": jobs, "linkedin_source": "x", "description_source": "x", "also_on_ats": "",
    }


def test_shared_linkedin_kept_only_where_it_matches():
    rows = [
        _row("charliehealth", "https://charliehealth.com", "https://www.linkedin.com/company/charlie-health"),
        _row("brighthire", "https://brighthire.com", "https://www.linkedin.com/company/charlie-health"),
    ]
    assert drop_conflicting_linkedin(rows) == 1
    assert rows[0]["linkedin_url"] and not rows[1]["linkedin_url"]


def test_template_description_shared_by_many_companies_dropped():
    text = "It takes a big heart to shape little minds and we love it."
    rows = [_row(f"school{i}", f"https://school{i}.com", description=text) for i in range(3)]
    assert drop_shared_descriptions(rows) == 3


def test_one_row_per_company_across_ats_and_boards():
    rows = [
        _row("robinhood", "https://robinhood.com", "https://www.linkedin.com/company/robinhood", "Robinhood is a brokerage app.", jobs=50),
        _row("robinhoodcontractors", "https://www.robinhood.com", jobs=3),
        _row("robinhood", "https://robinhood.com", ats="lever", jobs=1),
        _row("talkdesk2", "", "https://www.linkedin.com/company/talkdesk", name="Talkdesk"),
        _row("talkdesk", "https://talkdesk.com", "https://www.linkedin.com/company/talkdesk", ats="ashby", name="Talkdesk"),
        _row("acme-sub", "https://acmesub.com", "https://www.linkedin.com/company/acme", name="Zenith Sub"),
        _row("acme", "https://acme.com", "https://www.linkedin.com/company/acme", name="Acme"),
    ]
    kept, extras = collapse_companies(rows)
    assert sorted(r["ats_code"] for r in kept) == ["acme", "acme-sub", "robinhood", "talkdesk"]
    rh = next(r for r in kept if r["ats_code"] == "robinhood")
    assert rh["ats_system"] == "greenhouse"
    assert rh["also_on_ats"] == "lever"
    assert rh["other_boards"] == "greenhouse:robinhoodcontractors;lever:robinhood"
    assert next(r for r in kept if r["ats_code"] == "talkdesk")["other_boards"] == "greenhouse:talkdesk2"
