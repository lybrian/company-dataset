"""Himalayas.app public remote jobs API feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type

URL = "https://himalayas.app/jobs/api"


async def fetch_himalayas(client: HttpClient, *, max_pages: int = 3) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    limit = 100
    for page in range(max_pages):
        resp = await client.get(
            URL,
            bucket="feed_himalayas",
            params={"limit": limit, "offset": page * limit},
        )
        if resp.status_code != 200:
            break
        try:
            payload = resp.json()
        except ValueError:
            break
        items = payload.get("jobs") or []
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("guid") or item.get("applicationLink") or "")
            title = (item.get("title") or "").strip()
            company = (item.get("companyName") or "").strip()
            apply_url = (item.get("applicationLink") or item.get("guid") or "").strip()
            if not ext_id or not title or not company or not apply_url:
                continue
            locs = [str(x) for x in (item.get("locationRestrictions") or []) if isinstance(x, str)]
            location = ", ".join(locs) if locs else "Remote (Worldwide)"
            cats = [str(c) for c in (item.get("categories") or []) if isinstance(c, str)]
            sen = item.get("seniority") or []
            seniority = str(sen[0]) if isinstance(sen, list) and sen else (str(sen) if sen else None)
            sal_min = int(item["minSalary"]) if isinstance(item.get("minSalary"), (int, float)) and item["minSalary"] > 0 else None
            sal_max = int(item["maxSalary"]) if isinstance(item.get("maxSalary"), (int, float)) and item["maxSalary"] > 0 else None
            sal_cur = (item.get("currency") or "").strip().upper() or None
            jobs.append(
                JobRecord(
                    source_type="feed",
                    source="himalayas",
                    external_id=ext_id,
                    company_name=company,
                    company_logo=(item.get("companyLogo") or "").strip() or None,
                    title=title,
                    description_html=item.get("description") or item.get("excerpt") or "",
                    apply_url=apply_url,
                    source_url=(item.get("guid") or apply_url).strip(),
                    location=location,
                    remote_type="remote",
                    employment_type=infer_employment_type(item.get("employmentType")),
                    department=cats[0] if cats else None,
                    seniority=seniority,
                    tags=cats,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_cur if (sal_min or sal_max) else None,
                    salary_period="year" if (sal_min or sal_max) else None,
                    posted_at=item.get("pubDate"),
                )
            )
    return jobs
