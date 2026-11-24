"""Hacker News 'Ask HN: Who is hiring?' direct job feed via Algolia API."""
from __future__ import annotations

import html
import re

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type, infer_remote_type, strip_html

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{item_id}"
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def parse_hn_comment_to_job(comment: dict) -> JobRecord | None:
    comment_id = str(comment.get("id") or comment.get("objectID") or "")
    raw_html = comment.get("text") or comment.get("comment_text") or ""
    if not comment_id or not raw_html:
        return None
    # First line usually follows: Company | Role | Location | Remote | URL
    first_para = raw_html.split("<p>", 1)[0]
    header = strip_html(first_para, max_len=300)
    parts = [p.strip() for p in header.split("|") if p.strip()]
    if len(parts) < 2:
        return None
    company = parts[0][:100]
    title = parts[1][:140]
    location = parts[2][:120] if len(parts) >= 3 else ""
    rest_header = " ".join(parts[2:])

    urls = _URL_RE.findall(html.unescape(raw_html))
    hn_link = f"https://news.ycombinator.com/item?id={comment_id}"
    apply_url = urls[0].rstrip(".,;:!?)") if urls else hn_link
    desc_text = strip_html(raw_html)
    return JobRecord(
        source_type="feed",
        source="hn_hiring",
        external_id=comment_id,
        company_name=company,
        title=title,
        description_html=raw_html,
        description_text=desc_text,
        apply_url=apply_url,
        source_url=hn_link,
        location=location,
        remote_type=infer_remote_type(title, rest_header, desc_text),
        employment_type=infer_employment_type(rest_header),
        tags=["hackernews"],
        posted_at=comment.get("created_at") or comment.get("created_at_i"),
    )


async def fetch_hn_hiring(client: HttpClient, *, max_comments: int = 200) -> list[JobRecord]:
    resp = await client.get(
        SEARCH_URL,
        bucket="feed_hn",
        params={
            "tags": "story,author_whoishiring",
            "query": "Who is hiring",
            "hitsPerPage": 1,
        },
    )
    if resp.status_code != 200:
        return []
    try:
        hits = resp.json().get("hits") or []
    except ValueError:
        return []
    if not hits:
        return []
    story_id = hits[0].get("objectID")
    if not story_id:
        return []

    item_resp = await client.get(ITEM_URL.format(item_id=story_id), bucket="feed_hn")
    if item_resp.status_code != 200:
        return []
    try:
        story = item_resp.json()
    except ValueError:
        return []

    jobs: list[JobRecord] = []
    for child in (story.get("children") or [])[:max_comments]:
        if not isinstance(child, dict):
            continue
        job = parse_hn_comment_to_job(child)
        if job is not None:
            jobs.append(job)
    return jobs
