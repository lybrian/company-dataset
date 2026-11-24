"""Discover ATS board links from recent Hacker News comments via Algolia API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape

from job_pipeline.http_client import HttpClient
from job_pipeline.models import DiscoveredBoard
from job_pipeline.normalize import extract_boards_from_text

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ATS_QUERY_HOSTS = [
    "jobs.ashbyhq.com",
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
    "jobs.lever.co",
    "apply.workable.com",
    "ats.rippling.com",
    "app.dover.com/jobs",
    "jobs.gem.com",
]


async def discover_hn_boards(
    client: HttpClient,
    *,
    lookback_days: int = 120,
    max_pages_per_host: int = 3,
) -> list[DiscoveredBoard]:
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp())
    out: list[DiscoveredBoard] = []
    seen: set[tuple[str, str]] = set()

    for host in ATS_QUERY_HOSTS:
        for page in range(max_pages_per_host):
            try:
                resp = await client.get(
                    HN_SEARCH_URL,
                    bucket="hn",
                    params={
                        "tags": "comment",
                        "query": host,
                        "hitsPerPage": 100,
                        "page": page,
                        "numericFilters": f"created_at_i>={cutoff}",
                    },
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
            except Exception:
                break
            hits = data.get("hits") or []
            if not hits:
                break
            for hit in hits:
                text = unescape(hit.get("comment_text") or "")
                for parsed in extract_boards_from_text(text):
                    key = (parsed.ats, parsed.code.casefold())
                    if key not in seen:
                        seen.add(key)
                        out.append(
                            DiscoveredBoard(
                                ats=parsed.ats,
                                code=parsed.code,
                                region=parsed.region,
                                source="hn_comments",
                            )
                        )
            if page + 1 >= int(data.get("nbPages") or 0):
                break
    return out
