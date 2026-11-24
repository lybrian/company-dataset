"""Jobicy public remote jobs API v2 feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type

URL = "https://jobicy.com/api/v2/remote-jobs"


async def fetch_jobicy(client: HttpClient) -> list[JobRecord]:
    resp = await client.get(URL, bucket="feed_jobicy", params={"count": 50})
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
        title = (item.get("jobTitle") or "").strip()
        company = (item.get("companyName") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not company or not apply_url:
            continue
        job_types = item.get("jobType") or []
        emp_raw = job_types[0] if isinstance(job_types, list) and job_types else (str(job_types) if job_types else None)
        industries = [str(i) for i in (item.get("jobIndustry") or []) if isinstance(i, str)]
        sal_min = int(item["annualSalaryMin"]) if str(item.get("annualSalaryMin") or "").isdigit() else None
        sal_max = int(item["annualSalaryMax"]) if str(item.get("annualSalaryMax") or "").isdigit() else None
        sal_cur = (item.get("salaryCurrency") or "").strip().upper() or None
        jobs.append(
            JobRecord(
                source_type="feed",
                source="jobicy",
                external_id=ext_id,
                company_name=company,
                company_logo=(item.get("companyLogo") or "").strip() or None,
                title=title,
                description_html=item.get("jobDescription") or item.get("jobExcerpt") or "",
                apply_url=apply_url,
                source_url=apply_url,
                location=(item.get("jobGeo") or "Remote").strip(),
                remote_type="remote",
                employment_type=infer_employment_type(emp_raw),
                department=industries[0] if industries else None,
                seniority=(item.get("jobLevel") or "").strip() or None,
                tags=industries,
                salary_min=sal_min,
                salary_max=sal_max,
                salary_currency=sal_cur if (sal_min or sal_max) else None,
                salary_period="year" if (sal_min or sal_max) else None,
                posted_at=item.get("pubDate"),
            )
        )
    return jobs
