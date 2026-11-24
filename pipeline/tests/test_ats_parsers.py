"""Tests for all 17 ATS job fetchers using mocked vendor API responses."""
from __future__ import annotations

import httpx
import respx

from job_pipeline.ats import ATS_FETCHERS, fetch_board_jobs
from job_pipeline.http_client import AsyncRateLimiter, HttpClient
from job_pipeline.models import BoardRow


def _board(ats: str, code: str, region: str | None = None) -> BoardRow:
    return BoardRow(id=1, ats=ats, code_key=code.casefold(), code=code, region=region, company_name="Acme")


def test_all_17_ats_registered():
    assert len(ATS_FETCHERS) == 17


@respx.mock
async def test_core_ats_fetchers():
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true").mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 101,
                        "title": "Backend Engineer",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
                        "location": {"name": "Remote - US"},
                        "departments": [{"name": "Engineering"}],
                        "content": "<p>Build APIs</p>",
                        "updated_at": "2026-10-01T10:00:00Z",
                    }
                ]
            },
        )
    )
    respx.get("https://api.lever.co/v0/postings/acme?mode=json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "lev-1",
                    "text": "Frontend Engineer",
                    "hostedUrl": "https://jobs.lever.co/acme/lev-1",
                    "categories": {"location": "New York, NY", "department": "Product", "commitment": "Full-time"},
                    "workplaceType": "hybrid",
                    "salaryRange": {"min": 150000, "max": 190000, "currency": "USD", "interval": "per-year-salary"},
                    "createdAt": 1700000000000,
                }
            ],
        )
    )
    respx.get("https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true").mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "ash-1",
                        "title": "ML Engineer",
                        "jobUrl": "https://jobs.ashbyhq.com/acme/ash-1",
                        "location": "San Francisco, CA",
                        "isRemote": True,
                        "employmentType": "FullTime",
                        "department": "AI",
                        "compensation": {"summaryComponents": [{"minValue": 200000, "maxValue": 250000, "currencyCode": "USD", "interval": "1 year"}]},
                    }
                ]
            },
        )
    )
    respx.get("https://api.smartrecruiters.com/v1/companies/acme/postings?limit=100&offset=0").mock(
        return_value=httpx.Response(
            200,
            json={
                "totalFound": 1,
                "content": [
                    {
                        "id": "sr-1",
                        "name": "Data Engineer",
                        "company": {"name": "Acme Inc"},
                        "location": {"city": "Berlin", "country": "de", "remote": False},
                        "department": {"label": "Data"},
                        "typeOfEmployment": {"label": "Full-time"},
                    }
                ],
            },
        )
    )
    respx.get("https://acme.breezy.hr/json").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "br-1",
                    "name": "DevOps Engineer",
                    "url": "https://acme.breezy.hr/p/br-1",
                    "location": {"name": "Austin, TX", "is_remote": True, "country": {"id": "US"}},
                    "type": {"name": "Full-Time"},
                }
            ],
        )
    )

    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        for ats in ("greenhouse", "lever", "ashby", "smartrecruiters", "breezy"):
            res = await fetch_board_jobs(client, _board(ats, "acme"))
            assert res.status == "ok", f"{ats} failed: {res.error}"
            assert len(res.jobs) == 1


@respx.mock
async def test_extra_and_additional_ats_fetchers():
    respx.get("https://apply.workable.com/api/v1/widget/accounts/acme?details=true").mock(
        return_value=httpx.Response(200, json={"name": "Acme", "jobs": [{"shortcode": "W1", "title": "QA", "url": "https://apply.workable.com/acme/j/W1/", "telecommuting": True}]})
    )
    respx.post("https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs").mock(
        return_value=httpx.Response(200, json={"total": 1, "jobPostings": [{"title": "PM", "externalPath": "/job/PM_1", "locationsText": "Seattle, WA", "bulletFields": ["R-1"]}]})
    )
    respx.get("https://acme.bamboohr.com/careers/list").mock(
        return_value=httpx.Response(200, json={"result": [{"id": "5", "jobOpeningName": "Designer", "location": {"city": "Denver", "state": "CO"}}]})
    )
    respx.get("https://acme.recruitee.com/api/offers/").mock(
        return_value=httpx.Response(200, json={"offers": [{"id": 9, "title": "SRE", "careers_url": "https://acme.recruitee.com/o/sre", "company_name": "Acme", "remote": True}]})
    )
    respx.get("https://acme.teamtailor.com/jobs.json").mock(
        return_value=httpx.Response(200, json={"title": "Acme", "items": [{"id": "t1", "title": "iOS Dev", "url": "https://acme.teamtailor.com/jobs/t1"}]})
    )
    respx.get("https://acme.jobs.personio.de/xml").mock(
        return_value=httpx.Response(200, text="<workzag-jobs><position><id>77</id><name>Security Eng</name><office>Munich</office></position></workzag-jobs>")
    )
    respx.get("https://api.rippling.com/platform/api/ats/v1/board/acme/jobs").mock(
        return_value=httpx.Response(200, json=[{"uuid": "r1", "name": "Fullstack", "url": "https://ats.rippling.com/acme/jobs/r1"}])
    )
    respx.get("https://careers-acme.icims.com/jobs/search?ss=1&in_iframe=1").mock(
        return_value=httpx.Response(200, text='<a href="https://careers-acme.icims.com/jobs/42/analyst/job">Analyst</a>')
    )
    respx.get("https://acme.pinpointhq.com/postings.json").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "p1", "title": "Writer", "url": "https://acme.pinpointhq.com/postings/p1"}]})
    )
    respx.get("https://join.com/companies/acme").mock(
        return_value=httpx.Response(200, text='<title>Jobs at Acme | JOIN</title><a href="/companies/acme/99-python-engineer">Python</a>')
    )
    respx.get("https://app.dover.com/api/v1/careers-page/acme/jobs").mock(
        return_value=httpx.Response(200, json={"results": [{"id": "d1", "title": "Founding Engineer", "locations": [{"name": "SF"}]}]})
    )
    respx.get("https://api.gem.com/job_board/v0/acme/job_posts/").mock(
        return_value=httpx.Response(200, json=[{"id": "g1", "title": "Research Scientist", "absolute_url": "https://jobs.gem.com/acme/g1"}])
    )

    cases = [
        ("workable", "acme"),
        ("workday", "acme.wd5/Careers"),
        ("bamboohr", "acme"),
        ("recruitee", "acme"),
        ("teamtailor", "acme"),
        ("personio", "acme"),
        ("rippling", "acme"),
        ("icims", "careers-acme"),
        ("pinpoint", "acme"),
        ("join", "acme"),
        ("dover", "acme"),
        ("gem", "acme"),
    ]
    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        for ats, code in cases:
            res = await fetch_board_jobs(client, _board(ats, code))
            assert res.status == "ok", f"{ats} failed: {res.error}"
            assert len(res.jobs) == 1


@respx.mock
async def test_board_404_returns_not_found():
    respx.get("https://boards-api.greenhouse.io/v1/boards/missing/jobs?content=true").mock(
        return_value=httpx.Response(404)
    )
    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        res = await fetch_board_jobs(client, _board("greenhouse", "missing"))
    assert res.status == "not_found"
