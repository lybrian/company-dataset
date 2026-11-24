"""Arbeitnow public job board API feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type, infer_remote_type

URL = "https://www.arbeitnow.com/api/job-board-api"


async def fetch_arbeitnow(client: HttpClient, *, max_pages: int = 3) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    for page in range(1, max_pages + 1):
        resp = await client.get(URL, bucket="feed_arbeitnow", params={"page": page})
        if resp.status_code != 200:
            break
        try:
            payload = resp.json()
        except ValueError:
            break
        items = payload.get("data") or []
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("slug") or "")
            title = (item.get("title") or "").strip()
            company = (item.get("company_name") or "").strip()
            apply_url = (item.get("url") or "").strip()
            if not ext_id or not title or not company or not apply_url:
                continue
            location = (item.get("location") or "").strip()
            is_remote = bool(item.get("remote")) if "remote" in item else None
            job_types = item.get("job_types") or []
            emp_raw = job_types[0] if isinstance(job_types, list) and job_types else None
            jobs.append(
                JobRecord(
                    source_type="feed",
                    source="arbeitnow",
                    external_id=ext_id,
                    company_name=company,
                    title=title,
                    description_html=item.get("description") or "",
                    apply_url=apply_url,
                    source_url=apply_url,
                    location=location,
                    remote_type=infer_remote_type(title, location, is_remote=is_remote),
                    employment_type=infer_employment_type(emp_raw),
                    tags=[str(t) for t in (item.get("tags") or []) if isinstance(t, str)],
                    posted_at=item.get("created_at"),
                )
            )
    return jobs
