"""Landing.jobs public European tech jobs API feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type, infer_remote_type

URL = "https://landing.jobs/api/v1/jobs"


async def fetch_landingjobs(client: HttpClient, *, max_pages: int = 3) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    limit = 50
    for page in range(max_pages):
        resp = await client.get(
            URL,
            bucket="feed_landingjobs",
            params={"limit": limit, "offset": page * limit},
        )
        if resp.status_code != 200:
            break
        try:
            items = resp.json()
        except ValueError:
            break
        if not isinstance(items, list) or not items:
            break
        for item in items:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("id") or "")
            title = (item.get("title") or "").strip()
            apply_url = (item.get("url") or "").strip()
            if not ext_id or not title or not apply_url:
                continue
            company = (item.get("company_name") or f"Company #{item.get('company_id', 'unknown')}").strip()
            loc_parts = [p for p in [item.get("city"), item.get("country_name")] if p]
            location = ", ".join(str(p) for p in loc_parts)
            is_remote = bool(item.get("remote")) if "remote" in item else None
            sal_min = int(item["gross_salary_low"]) if isinstance(item.get("gross_salary_low"), (int, float)) and item["gross_salary_low"] > 0 else None
            sal_max = int(item["gross_salary_high"]) if isinstance(item.get("gross_salary_high"), (int, float)) and item["gross_salary_high"] > 0 else None
            jobs.append(
                JobRecord(
                    source_type="feed",
                    source="landingjobs",
                    external_id=ext_id,
                    company_name=company,
                    title=title,
                    description_html=(item.get("role_description") or "") + "\n" + (item.get("main_requirements") or ""),
                    apply_url=apply_url,
                    source_url=apply_url,
                    location=location,
                    country=(item.get("country_code") or "").upper() or None,
                    remote_type=infer_remote_type(title, location, is_remote=is_remote),
                    employment_type=infer_employment_type(item.get("type")),
                    tags=[str(t) for t in (item.get("tags") or []) if isinstance(t, str)],
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=(item.get("currency_code") or "EUR").upper() if (sal_min or sal_max) else None,
                    salary_period="year" if (sal_min or sal_max) else None,
                    posted_at=item.get("published_at"),
                )
            )
    return jobs
