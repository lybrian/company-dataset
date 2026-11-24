"""Remotive public remote jobs API feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type

URL = "https://remotive.com/api/remote-jobs"


async def fetch_remotive(client: HttpClient) -> list[JobRecord]:
    resp = await client.get(URL, bucket="feed_remotive")
    if resp.status_code != 200:
        return []
    try:
        payload = resp.json()
    except ValueError:
        return []

    jobs: list[JobRecord] = []
    for item in payload.get("jobs") or []:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        company = (item.get("company_name") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not company or not apply_url:
            continue
        cat = (item.get("category") or "").strip() or None
        tags = [str(t) for t in (item.get("tags") or []) if isinstance(t, str)]
        if cat:
            tags.append(cat)
        jobs.append(
            JobRecord(
                source_type="feed",
                source="remotive",
                external_id=ext_id,
                company_name=company,
                company_logo=(item.get("company_logo") or "").strip() or None,
                title=title,
                description_html=item.get("description") or "",
                apply_url=apply_url,
                source_url=apply_url,
                location=(item.get("candidate_required_location") or "Remote").strip(),
                remote_type="remote",
                employment_type=infer_employment_type(item.get("job_type")),
                department=cat,
                tags=tags,
                posted_at=item.get("publication_date"),
            )
        )
    return jobs
