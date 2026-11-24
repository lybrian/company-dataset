"""Working Nomads public remote jobs JSON feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord

URL = "https://www.workingnomads.com/api/exposed_jobs/"


async def fetch_workingnomads(client: HttpClient) -> list[JobRecord]:
    resp = await client.get(URL, bucket="feed_workingnomads")
    if resp.status_code != 200:
        return []
    try:
        items = resp.json()
    except ValueError:
        return []
    if not isinstance(items, list):
        return []

    jobs: list[JobRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        company = (item.get("company_name") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not title or not company or not apply_url:
            continue
        raw_tags = item.get("tags") or ""
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if isinstance(raw_tags, str) else []
        cat = (item.get("category_name") or "").strip() or None
        if cat:
            tags.append(cat)
        jobs.append(
            JobRecord(
                source_type="feed",
                source="workingnomads",
                external_id=apply_url,
                company_name=company,
                title=title,
                description_html=item.get("description") or "",
                apply_url=apply_url,
                source_url=apply_url,
                location=(item.get("location") or "Remote").strip(),
                remote_type="remote",
                department=cat,
                tags=tags,
                posted_at=item.get("pub_date"),
            )
        )
    return jobs
