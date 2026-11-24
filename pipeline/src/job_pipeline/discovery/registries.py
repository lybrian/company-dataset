"""Board discovery from curated public GitHub / web ATS registries."""
from __future__ import annotations

import csv
import io
import json
import re

from job_pipeline.http_client import HttpClient
from job_pipeline.models import DiscoveredBoard
from job_pipeline.normalize import (
    ASHBY,
    GREENHOUSE,
    LEVER,
    PERSONIO,
    RECRUITEE,
    RIPPLING,
    SUPPORTED_ATS,
    WORKABLE,
    WORKDAY,
    clean_code,
    parse_board_url,
)

LASTROUND_URL = "https://raw.githubusercontent.com/fyrosofttech/lastroundai-hiring-data/main/ats-directory/lastroundai-ats-company-directory-2026-08.csv"
KALEB_URL = "https://kalebconfer-sys.github.io/job-board-directory/job-board-directory.csv"
MOONIE_URL = "https://raw.githubusercontent.com/moonie0201/ats-directory/main/companies.jsonl"
FEASHLIAA_BASE = "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/"
FEASHLIAA_FILES = {
    "greenhouse": "greenhouse_companies.json",
    "lever": "lever_companies.json",
    "ashby": "ashby_companies.json",
    "workday": "workday_companies.json",
    "bamboohr": "bamboohr_companies.json",
    "icims": "icims_companies.json",
}
OPENATSFEED_URL = "https://raw.githubusercontent.com/veresk06/open-ats-feed/main/data/tokens.json"
OPEN_JOBS_URL = "https://raw.githubusercontent.com/elliottdehn/open-jobs/main/slugs.json"


async def discover_lastround(client: HttpClient) -> list[DiscoveredBoard]:
    resp = await client.get(LASTROUND_URL, bucket="github")
    if resp.status_code != 200:
        return []
    vendor_map = {"greenhouse": GREENHOUSE, "lever": LEVER, "ashby": ASHBY}
    out: list[DiscoveredBoard] = []
    reader = csv.DictReader(io.StringIO(resp.text.lstrip("\ufeff")))
    for row in reader:
        ats = vendor_map.get((row.get("ats_vendor") or "").strip().lower())
        if not ats:
            continue
        code = clean_code(ats, (row.get("board_slug") or "").strip())
        if code:
            name = (row.get("company_name") or "").strip() or None
            out.append(DiscoveredBoard(ats=ats, code=code, source="lastround", company_name=name))
    return out


async def discover_kaleb(client: HttpClient) -> list[DiscoveredBoard]:
    resp = await client.get(KALEB_URL, bucket="github")
    if resp.status_code != 200:
        return []
    platform_map = {
        "greenhouse": GREENHOUSE,
        "lever": LEVER,
        "ashby": ASHBY,
        "workable": WORKABLE,
        "workday": WORKDAY,
        "recruitee": RECRUITEE,
        "personio": PERSONIO,
        "rippling": RIPPLING,
    }
    out: list[DiscoveredBoard] = []
    reader = csv.DictReader(io.StringIO(resp.text.lstrip("\ufeff")))
    for row in reader:
        ats = platform_map.get((row.get("platform") or "").strip().lower())
        if not ats:
            continue
        name = (row.get("company") or "").strip() or None
        board_url = (row.get("board_url") or "").strip()
        parsed = parse_board_url(board_url) if board_url else None
        if parsed and parsed.ats == ats:
            out.append(
                DiscoveredBoard(
                    ats=ats,
                    code=parsed.code,
                    region=parsed.region,
                    source="kaleb",
                    company_name=name,
                )
            )
            continue
        code = clean_code(ats, (row.get("token") or "").strip())
        if code:
            out.append(DiscoveredBoard(ats=ats, code=code, source="kaleb", company_name=name))
    return out


async def discover_moonie(client: HttpClient) -> list[DiscoveredBoard]:
    resp = await client.get(MOONIE_URL, bucket="github")
    if resp.status_code != 200:
        return []
    out: list[DiscoveredBoard] = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if (row.get("status") or "").strip().lower() == "dead":
            continue
        ats = (row.get("provider") or "").strip().lower()
        if ats not in SUPPORTED_ATS:
            continue
        code = clean_code(ats, (row.get("slug") or "").strip())
        if not code:
            continue
        region = "eu" if (row.get("region") or "").strip().lower() == "eu" else None
        name = (row.get("name") or "").strip() or None
        out.append(DiscoveredBoard(ats=ats, code=code, region=region, source="moonie", company_name=name))
    return out


def _feashliaa_code(ats: str, slug: str) -> str | None:
    if ats == "workday":
        parts = slug.split("|")
        if len(parts) != 3 or re.fullmatch(r"wd\d{1,3}", parts[0], re.I):
            return None
        return clean_code(ats, f"{parts[0]}.{parts[1]}/{parts[2]}")
    if ats == "icims":
        label = slug.strip("-").lower()
        return clean_code(ats, label if label.startswith(("careers-", "jobs-")) else f"careers-{label}")
    return clean_code(ats, slug)


async def discover_feashliaa(client: HttpClient) -> list[DiscoveredBoard]:
    out: list[DiscoveredBoard] = []
    for ats, filename in FEASHLIAA_FILES.items():
        resp = await client.get(FEASHLIAA_BASE + filename, bucket="github")
        if resp.status_code != 200:
            continue
        try:
            slugs = resp.json()
        except ValueError:
            continue
        if not isinstance(slugs, list):
            continue
        for raw in slugs:
            if not isinstance(raw, str):
                continue
            code = _feashliaa_code(ats, raw.strip())
            if code:
                out.append(DiscoveredBoard(ats=ats, code=code, source="feashliaa"))
    return out


async def discover_openatsfeed(client: HttpClient) -> list[DiscoveredBoard]:
    resp = await client.get(OPENATSFEED_URL, bucket="github")
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    out: list[DiscoveredBoard] = []
    if not isinstance(data, dict):
        return out
    for provider, tokens in data.items():
        ats = provider.strip().lower()
        if ats not in SUPPORTED_ATS or not isinstance(tokens, list):
            continue
        for tok in tokens:
            if not isinstance(tok, str):
                continue
            code = clean_code(ats, tok.strip())
            if code:
                out.append(DiscoveredBoard(ats=ats, code=code, source="openatsfeed"))
    return out


async def discover_open_jobs(client: HttpClient) -> list[DiscoveredBoard]:
    resp = await client.get(OPEN_JOBS_URL, bucket="github")
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    out: list[DiscoveredBoard] = []
    ats_map = (data.get("ats") or {}) if isinstance(data, dict) else {}
    for ats, slugs in ats_map.items():
        ats_low = ats.strip().lower()
        if ats_low not in SUPPORTED_ATS or not isinstance(slugs, list):
            continue
        for raw in slugs:
            if not isinstance(raw, str):
                continue
            code = clean_code(ats_low, raw.strip())
            if code:
                out.append(DiscoveredBoard(ats=ats_low, code=code, source="open_jobs"))
    return out


async def discover_all_registries(client: HttpClient) -> list[DiscoveredBoard]:
    boards: list[DiscoveredBoard] = []
    for fn in (
        discover_lastround,
        discover_kaleb,
        discover_moonie,
        discover_feashliaa,
        discover_openatsfeed,
        discover_open_jobs,
    ):
        try:
            boards.extend(await fn(client))
        except Exception:
            continue
    return boards
