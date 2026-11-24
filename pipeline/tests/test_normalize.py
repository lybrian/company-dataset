"""Tests for ATS URL parsing, slug cleaning, and job field normalization."""
from __future__ import annotations

import pytest

from job_pipeline.models import JobRecord
from job_pipeline.normalize import (
    ASHBY,
    BAMBOOHR,
    BREEZY,
    DOVER,
    GEM,
    GREENHOUSE,
    ICIMS,
    JOIN,
    LEVER,
    PERSONIO,
    PINPOINT,
    RECRUITEE,
    RIPPLING,
    SMARTRECRUITERS,
    TEAMTAILOR,
    WORKABLE,
    WORKDAY,
    compute_content_hash,
    compute_job_id,
    extract_boards_from_text,
    extract_country,
    finalize_job,
    infer_employment_type,
    infer_remote_type,
    normalize_timestamp,
    parse_board_url,
    slugify_company,
    strip_html,
)


@pytest.mark.parametrize(
    "url,expected_ats,expected_code,expected_region",
    [
        ("https://boards.greenhouse.io/stripe", GREENHOUSE, "stripe", None),
        ("https://job-boards.eu.greenhouse.io/klarna", GREENHOUSE, "klarna", "eu"),
        ("https://boards.greenhouse.io/embed/job_board?for=figma", GREENHOUSE, "figma", None),
        ("https://jobs.lever.co/netflix", LEVER, "netflix", None),
        ("https://jobs.eu.lever.co/n26", LEVER, "n26", "eu"),
        ("https://jobs.ashbyhq.com/openai", ASHBY, "openai", None),
        ("https://careers.smartrecruiters.com/BoschGroup", SMARTRECRUITERS, "BoschGroup", None),
        ("https://acme.breezy.hr", BREEZY, "acme", None),
        ("https://apply.workable.com/vercel/", WORKABLE, "vercel", None),
        ("https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite", WORKDAY, "nvidia.wd5/NVIDIAExternalCareerSite", None),
        ("https://acme.bamboohr.com/careers", BAMBOOHR, "acme", None),
        ("https://acme.recruitee.com/", RECRUITEE, "acme", None),
        ("https://acme.teamtailor.com/jobs", TEAMTAILOR, "acme", None),
        ("https://acme.jobs.personio.de/", PERSONIO, "acme", None),
        ("https://acme.jobs.personio.com/", PERSONIO, "acme", "com"),
        ("https://ats.rippling.com/en-US/acme-inc/jobs", RIPPLING, "acme-inc", None),
        ("https://careers-acme.icims.com/jobs/search", ICIMS, "careers-acme", None),
        ("https://acme.pinpointhq.com/", PINPOINT, "acme", None),
        ("https://join.com/companies/acme", JOIN, "acme", None),
        ("https://app.dover.com/jobs/acme", DOVER, "acme", None),
        ("https://jobs.gem.com/acme", GEM, "acme", None),
    ],
)
def test_parse_board_url_all_17_ats(url, expected_ats, expected_code, expected_region):
    parsed = parse_board_url(url)
    assert parsed is not None
    assert parsed.ats == expected_ats
    assert parsed.code == expected_code
    assert parsed.region == expected_region


def test_extract_boards_from_text():
    text = (
        'We are hiring! Apply at https://jobs.ashbyhq.com/linear or '
        'https://boards.greenhouse.io/stripe/jobs/12345 and https://app.dover.com/jobs/acme.'
    )
    boards = extract_boards_from_text(text)
    keys = {(b.ats, b.code) for b in boards}
    assert (ASHBY, "linear") in keys
    assert (GREENHOUSE, "stripe") in keys
    assert (DOVER, "acme") in keys


def test_job_normalizers():
    assert strip_html("<p>Hello &amp; <b>world</b></p>") == "Hello & world"
    assert slugify_company("Acme Corp., Inc.") == "acme-corp-inc"
    assert infer_remote_type("Staff Engineer", "Remote - US") == "remote"
    assert infer_remote_type("Staff Engineer", "Hybrid - New York, NY") == "hybrid"
    assert infer_remote_type("Staff Engineer", "On-site London") == "onsite"
    assert infer_employment_type("Full-Time") == "full_time"
    assert infer_employment_type("Summer Internship") == "internship"
    assert infer_employment_type("Contract / Freelance") == "freelance"
    assert extract_country("San Francisco, CA") == "US"
    assert extract_country("Berlin, Germany") == "DE"
    assert extract_country("London, UK") == "GB"
    assert normalize_timestamp(1700000000000) == "2023-11-14T22:13:20Z"
    assert normalize_timestamp("2026-10-01T12:00:00+00:00") == "2026-10-01T12:00:00Z"


def test_deterministic_id_and_content_hash():
    j1 = finalize_job(
        JobRecord(
            source_type="ats",
            source="greenhouse",
            external_id="stripe:123",
            company_name="Stripe",
            title="Senior Backend Engineer",
            apply_url="https://boards.greenhouse.io/stripe/jobs/123",
            description_html="<p>Build payments infrastructure</p>",
            location="San Francisco, CA (Remote)",
        )
    )
    assert j1.remote_type == "remote"
    assert j1.country == "US"
    assert compute_job_id("greenhouse", "stripe:123") == compute_job_id("greenhouse", "stripe:123")
    h1 = compute_content_hash(j1)
    j1.title = "Staff Backend Engineer"
    assert compute_content_hash(j1) != h1
