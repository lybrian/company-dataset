"""Tests for all 11 direct public job feeds using mocked HTTP fixtures."""
from __future__ import annotations

import httpx
import respx

from job_pipeline.feeds import FEED_FETCHERS
from job_pipeline.feeds import (
    arbeitnow,
    himalayas,
    hn_hiring,
    jobicy,
    landingjobs,
    remoteok,
    remotive,
    themuse,
    usajobs,
    workingnomads,
    wwr,
)
from job_pipeline.http_client import AsyncRateLimiter, HttpClient


def test_all_11_feeds_registered():
    assert len(FEED_FETCHERS) == 11


@respx.mock
async def test_all_direct_feeds():
    respx.get(remoteok.URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"legal": "notice"},
                {
                    "id": "rok-1",
                    "position": "Rust Engineer",
                    "company": "Fly",
                    "apply_url": "https://remoteok.com/l/1",
                    "salary_min": 140000,
                    "salary_max": 180000,
                    "tags": ["rust", "linux"],
                },
            ],
        )
    )
    respx.get(wwr.URL).mock(
        return_value=httpx.Response(
            200,
            content=b"<rss><channel><item><title>Basecamp: Rails Engineer</title><link>https://weworkremotely.com/1</link><guid>wwr-1</guid><region>Anywhere</region><category>Programming</category></item></channel></rss>",
        )
    )
    respx.get(arbeitnow.URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={"data": [{"slug": "arb-1", "title": "Go Dev", "company_name": "N26", "url": "https://arbeitnow.com/1", "location": "Berlin", "remote": True}]},
            ),
            httpx.Response(200, json={"data": []}),
        ]
    )
    respx.get(remotive.URL).mock(
        return_value=httpx.Response(
            200,
            json={"jobs": [{"id": 42, "title": "Python Dev", "company_name": "Zapier", "url": "https://remotive.com/42", "category": "Software Development"}]},
        )
    )
    respx.get(jobicy.URL).mock(
        return_value=httpx.Response(
            200,
            json={"jobs": [{"id": 99, "jobTitle": "SRE", "companyName": "GitLab", "url": "https://jobicy.com/99", "annualSalaryMin": "130000", "annualSalaryMax": "170000", "salaryCurrency": "USD"}]},
        )
    )
    respx.get(himalayas.URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={"jobs": [{"guid": "him-1", "title": "TypeScript Engineer", "companyName": "Supabase", "applicationLink": "https://supabase.com/careers/1", "minSalary": 160000, "maxSalary": 210000, "currency": "USD"}]},
            ),
            httpx.Response(200, json={"jobs": []}),
        ]
    )
    respx.get(themuse.URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={"results": [{"id": 7, "name": "Product Manager", "company": {"name": "Datadog"}, "refs": {"landing_page": "https://themuse.com/7"}, "locations": [{"name": "New York, NY"}]}]},
            ),
            httpx.Response(200, json={"results": []}),
        ]
    )
    respx.get(workingnomads.URL).mock(
        return_value=httpx.Response(
            200,
            json=[{"title": "Data Scientist", "company_name": "Automattic", "url": "https://workingnomads.com/1", "tags": "python,ml"}],
        )
    )
    respx.get(hn_hiring.SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"hits": [{"objectID": "40000001"}]})
    )
    respx.get(hn_hiring.ITEM_URL.format(item_id="40000001")).mock(
        return_value=httpx.Response(
            200,
            json={
                "children": [
                    {
                        "id": 40000002,
                        "text": "Turso | Systems Engineer | Remote | Full-time<p>Apply at https://turso.tech/careers</p>",
                        "created_at_i": 1700000000,
                    }
                ]
            },
        )
    )
    respx.get(landingjobs.URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json=[{"id": 55, "title": "Backend Dev", "company_name": "Remote", "url": "https://landing.jobs/55", "city": "Lisbon", "country_code": "PT", "remote": True}],
            ),
            httpx.Response(200, json=[]),
        ]
    )
    respx.get(usajobs.URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "SearchResult": {
                    "SearchResultItems": [
                        {
                            "MatchedObjectId": "usa-1",
                            "MatchedObjectDescriptor": {
                                "PositionTitle": "IT Specialist",
                                "OrganizationName": "NASA",
                                "ApplyURI": ["https://usajobs.gov/1"],
                                "PositionLocationDisplay": "Washington, DC",
                            },
                        }
                    ]
                }
            },
        )
    )

    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        for name, fn in FEED_FETCHERS.items():
            if name == "usajobs":
                jobs = await usajobs.fetch_usajobs(client, api_key="k", user_agent="me@example.com")
            else:
                jobs = await fn(client)
            assert len(jobs) == 1, f"Feed {name} returned {len(jobs)} jobs"
            assert jobs[0].source_type == "feed"
