"""Discover ATS boards from VC portfolio job sites (respecting robots.txt)."""
from __future__ import annotations

import re
from urllib.robotparser import RobotFileParser

from job_pipeline.config import DEFAULT_USER_AGENT
from job_pipeline.http_client import HttpClient
from job_pipeline.models import DiscoveredBoard
from job_pipeline.normalize import extract_boards_from_text

VC_SITES = [
    "jobs.a16z.com",
    "jobs.sequoiacap.com",
    "jobs.greylock.com",
    "jobs.accel.com",
    "jobs.lsvp.com",
    "jobs.kleinerperkins.com",
    "jobs.bvp.com",
    "jobs.generalcatalyst.com",
    "jobs.khoslaventures.com",
    "jobs.firstround.com",
    "jobs.8vc.com",
    "jobs.gv.com",
]

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


async def discover_vc_boards(
    client: HttpClient,
    *,
    sites: list[str] | None = None,
    max_pages_per_site: int = 40,
) -> list[DiscoveredBoard]:
    out: list[DiscoveredBoard] = []
    seen: set[tuple[str, str]] = set()
    for site in sites or VC_SITES:
        robots = RobotFileParser()
        try:
            r_resp = await client.get(f"https://{site}/robots.txt", bucket="vc_boards")
            if r_resp.status_code == 200:
                robots.parse(r_resp.text.splitlines())
        except Exception:
            pass

        pages = [f"https://{site}/jobs"]
        try:
            sm_url = f"https://{site}/sitemap.xml"
            if robots.can_fetch(DEFAULT_USER_AGENT, sm_url):
                sm_resp = await client.get(sm_url, bucket="vc_boards")
                if sm_resp.status_code == 200:
                    for loc in _LOC_RE.findall(sm_resp.text):
                        if "/company/" in loc:
                            pages.append(loc)
        except Exception:
            pass

        for url in pages[:max_pages_per_site]:
            if not robots.can_fetch(DEFAULT_USER_AGENT, url):
                continue
            try:
                resp = await client.get(url, bucket="vc_boards")
                if resp.status_code != 200:
                    continue
                for parsed in extract_boards_from_text(resp.text):
                    key = (parsed.ats, parsed.code.casefold())
                    if key not in seen:
                        seen.add(key)
                        out.append(
                            DiscoveredBoard(
                                ats=parsed.ats,
                                code=parsed.code,
                                region=parsed.region,
                                source=f"vc:{site}",
                            )
                        )
            except Exception:
                continue
    return out
