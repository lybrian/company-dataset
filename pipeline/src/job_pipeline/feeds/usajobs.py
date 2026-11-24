"""USAJobs federal jobs API feed (optional; enabled when USAJOBS_API_KEY is set)."""
from __future__ import annotations

import os

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type, infer_remote_type

URL = "https://data.usajobs.gov/api/search"


async def fetch_usajobs(
    client: HttpClient,
    *,
    api_key: str | None = None,
    user_agent: str | None = None,
) -> list[JobRecord]:
    key = api_key or os.environ.get("USAJOBS_API_KEY")
    ua = user_agent or os.environ.get("USAJOBS_USER_AGENT")
    if not key or not ua:
        return []

    resp = await client.get(
        URL,
        bucket="feed_usajobs",
        headers={
            "Authorization-Key": key,
            "User-Agent": ua,
            "Host": "data.usajobs.gov",
        },
        params={"ResultsPerPage": 100, "Page": 1},
    )
    if resp.status_code != 200:
        return []
    try:
        items = resp.json().get("SearchResult", {}).get("SearchResultItems", [])
    except ValueError:
        return []

    jobs: list[JobRecord] = []
    for entry in items:
        desc = entry.get("MatchedObjectDescriptor") or {}
        ext_id = str(entry.get("MatchedObjectId") or desc.get("PositionID") or "")
        title = (desc.get("PositionTitle") or "").strip()
        company = (desc.get("OrganizationName") or desc.get("DepartmentName") or "").strip()
        apply_uris = desc.get("ApplyURI") or []
        apply_url = (apply_uris[0] if apply_uris else desc.get("PositionURI") or "").strip()
        if not ext_id or not title or not company or not apply_url:
            continue
        location = (desc.get("PositionLocationDisplay") or "").strip()
        rem = (desc.get("PositionRemuneration") or [{}])[0]
        sal_min = int(float(rem["MinimumRange"])) if rem.get("MinimumRange") else None
        sal_max = int(float(rem["MaximumRange"])) if rem.get("MaximumRange") else None
        sched = (desc.get("PositionSchedule") or [{}])[0].get("Name")
        user_area = (desc.get("UserArea") or {}).get("Details") or {}
        telework = bool(user_area.get("TeleworkEligible"))
        jobs.append(
            JobRecord(
                source_type="feed",
                source="usajobs",
                external_id=ext_id,
                company_name=company,
                title=title,
                description_text=user_area.get("JobSummary") or desc.get("QualificationSummary") or "",
                apply_url=apply_url,
                source_url=(desc.get("PositionURI") or apply_url).strip(),
                location=location,
                country="US",
                remote_type=infer_remote_type(title, location, is_remote=True if telework and "remote" in location.lower() else None),
                employment_type=infer_employment_type(sched),
                department=(desc.get("DepartmentName") or "").strip() or None,
                tags=["government", "federal"],
                salary_min=sal_min,
                salary_max=sal_max,
                salary_currency="USD" if (sal_min or sal_max) else None,
                salary_period="year" if (sal_min or sal_max) else None,
                posted_at=desc.get("PublicationStartDate"),
            )
        )
    return jobs
