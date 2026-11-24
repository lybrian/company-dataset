"""RemoteOK public JSON job feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type

URL = "https://remoteok.com/api"


async def fetch_remoteok(client: HttpClient) -> list[JobRecord]:
    resp = await client.get(URL, bucket="feed_remoteok")
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    if not isinstance(data, list) or len(data) < 2:
        return []

    jobs: list[JobRecord] = []
    for item in data[1:]:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or item.get("slug") or "")
        title = (item.get("position") or "").strip()
        company = (item.get("company") or "").strip()
        apply_url = (item.get("apply_url") or item.get("url") or "").strip()
        if not ext_id or not title or not company or not apply_url:
            continue
        sal_min = int(item["salary_min"]) if isinstance(item.get("salary_min"), (int, float)) and item["salary_min"] > 0 else None
        sal_max = int(item["salary_max"]) if isinstance(item.get("salary_max"), (int, float)) and item["salary_max"] > 0 else None
        jobs.append(
            JobRecord(
                source_type="feed",
                source="remoteok",
                external_id=ext_id,
                company_name=company,
                company_logo=(item.get("company_logo") or item.get("logo") or "").strip() or None,
                title=title,
                description_html=item.get("description") or "",
                apply_url=apply_url,
                source_url=(item.get("url") or apply_url).strip(),
                location=(item.get("location") or "Remote").strip(),
                remote_type="remote",
                employment_type=infer_employment_type(item.get("employment_type") or "full_time"),
                tags=[str(t) for t in (item.get("tags") or []) if isinstance(t, str)],
                salary_min=sal_min,
                salary_max=sal_max,
                salary_currency="USD" if (sal_min or sal_max) else None,
                salary_period="year" if (sal_min or sal_max) else None,
                posted_at=item.get("date") or item.get("epoch"),
            )
        )
    return jobs
