"""Discover ATS boards from the Y Combinator company directory (yc-oss mirror)."""
from __future__ import annotations

import re

from job_pipeline.http_client import HttpClient
from job_pipeline.models import DiscoveredBoard
from job_pipeline.normalize import ASHBY, GREENHOUSE, LEVER, clean_code, extract_boards_from_text

YC_DIRECTORY_URL = "https://yc-oss.github.io/api/companies/all.json"


async def discover_yc(client: HttpClient, *, max_companies: int = 5000) -> list[DiscoveredBoard]:
    resp = await client.get(YC_DIRECTORY_URL, bucket="yc")
    if resp.status_code != 200:
        return []
    try:
        companies = resp.json()
    except ValueError:
        return []
    if not isinstance(companies, list):
        return []

    out: list[DiscoveredBoard] = []
    seen: set[tuple[str, str]] = set()
    for comp in companies[:max_companies]:
        if not isinstance(comp, dict):
            continue
        name = (comp.get("name") or "").strip() or None
        # Check explicit ATS links in descriptions/URLs first
        blob = " ".join(
            str(comp.get(k) or "")
            for k in ("website", "one_liner", "long_description", "url")
        )
        for parsed in extract_boards_from_text(blob):
            key = (parsed.ats, parsed.code.casefold())
            if key not in seen:
                seen.add(key)
                out.append(
                    DiscoveredBoard(
                        ats=parsed.ats,
                        code=parsed.code,
                        region=parsed.region,
                        source="yc_directory",
                        company_name=name,
                    )
                )
        # Also include YC hiring companies' slug as a candidate on Ashby/Greenhouse/Lever if active
        if comp.get("isHiring") and comp.get("slug"):
            slug = re.sub(r"[^a-z0-9-]", "", str(comp["slug"]).lower())
            if len(slug) >= 2:
                for ats in (ASHBY, GREENHOUSE, LEVER):
                    code = clean_code(ats, slug)
                    if code and (ats, code.casefold()) not in seen:
                        seen.add((ats, code.casefold()))
                        out.append(
                            DiscoveredBoard(
                                ats=ats,
                                code=code,
                                source="yc_hiring",
                                company_name=name,
                            )
                        )
    return out
