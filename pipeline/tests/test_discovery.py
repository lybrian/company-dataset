"""Tests for board discovery harvesters with mocked HTTP responses."""
from __future__ import annotations

import httpx
import respx

from job_pipeline.discovery.hn import HN_SEARCH_URL, discover_hn_boards
from job_pipeline.discovery.registries import (
    FEASHLIAA_BASE,
    KALEB_URL,
    LASTROUND_URL,
    MOONIE_URL,
    OPEN_JOBS_URL,
    OPENATSFEED_URL,
    discover_all_registries,
)
from job_pipeline.discovery.yc import YC_DIRECTORY_URL, discover_yc
from job_pipeline.http_client import AsyncRateLimiter, HttpClient


@respx.mock
async def test_discover_all_registries():
    respx.get(LASTROUND_URL).mock(
        return_value=httpx.Response(
            200,
            text="company_name,ats_vendor,board_slug\nStripe,greenhouse,stripe\nLinear,ashby,linear\n",
        )
    )
    respx.get(KALEB_URL).mock(
        return_value=httpx.Response(
            200,
            text="company,platform,token,board_url\nVercel,workable,vercel,https://apply.workable.com/vercel/\n",
        )
    )
    respx.get(MOONIE_URL).mock(
        return_value=httpx.Response(
            200,
            text='{"provider":"lever","slug":"n26","region":"eu","name":"N26","status":"live"}\n{"provider":"lever","slug":"deadco","status":"dead"}\n',
        )
    )
    respx.get(FEASHLIAA_BASE + "greenhouse_companies.json").mock(return_value=httpx.Response(200, json=["figma"]))
    respx.get(FEASHLIAA_BASE + "lever_companies.json").mock(return_value=httpx.Response(200, json=[]))
    respx.get(FEASHLIAA_BASE + "ashby_companies.json").mock(return_value=httpx.Response(200, json=[]))
    respx.get(FEASHLIAA_BASE + "workday_companies.json").mock(return_value=httpx.Response(200, json=["nvidia|wd5|NVIDIAExternalCareerSite"]))
    respx.get(FEASHLIAA_BASE + "bamboohr_companies.json").mock(return_value=httpx.Response(200, json=[]))
    respx.get(FEASHLIAA_BASE + "icims_companies.json").mock(return_value=httpx.Response(200, json=["acme"]))
    respx.get(OPENATSFEED_URL).mock(return_value=httpx.Response(200, json={"rippling": ["rippling-co"]}))
    respx.get(OPEN_JOBS_URL).mock(return_value=httpx.Response(200, json={"ats": {"breezy": ["breezyco"]}}))

    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        boards = await discover_all_registries(client)

    keys = {(b.ats, b.code) for b in boards}
    assert ("greenhouse", "stripe") in keys
    assert ("ashby", "linear") in keys
    assert ("workable", "vercel") in keys
    assert ("lever", "n26") in keys
    assert ("lever", "deadco") not in keys
    assert ("workday", "nvidia.wd5/NVIDIAExternalCareerSite") in keys
    assert ("icims", "careers-acme") in keys
    assert ("rippling", "rippling-co") in keys
    assert ("breezy", "breezyco") in keys


@respx.mock
async def test_discover_yc_and_hn():
    respx.get(YC_DIRECTORY_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"name": "PostHog", "slug": "posthog", "isHiring": True, "website": "https://posthog.com"},
            ],
        )
    )
    respx.get(HN_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "nbPages": 1,
                "hits": [{"comment_text": "Apply at https://jobs.gem.com/anthropic"}],
            },
        )
    )
    async with HttpClient(rate_limiter=AsyncRateLimiter({})) as client:
        yc_boards = await discover_yc(client)
        hn_boards = await discover_hn_boards(client, max_pages_per_host=1)

    assert any(b.ats == "ashby" and b.code == "posthog" for b in yc_boards)
    assert any(b.ats == "gem" and b.code == "anthropic" for b in hn_boards)
