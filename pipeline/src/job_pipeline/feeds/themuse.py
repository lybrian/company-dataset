"""The Muse public jobs API feed."""
from __future__ import annotations

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_remote_type

URL = "https://www.themuse.com/api/public/jobs"


async def fetch_themuse(client: HttpClient, *, max_pages: int = 5) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    for page in range(1, max_pages + 1):
        resp = await client.get(URL, bucket="feed_themuse", params={"page": page})
        if resp.status_code != 200:
            break
        try:
            payload = resp.json()
        except ValueError:
            break
        items = payload.get("results") or []
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("id") or "")
            title = (item.get("name") or "").strip()
            comp = item.get("company") or {}
            company = (comp.get("name") or "").strip() if isinstance(comp, dict) else ""
            refs = item.get("refs") or {}
            apply_url = (refs.get("landing_page") or "").strip() if isinstance(refs, dict) else ""
            if not ext_id or not title or not company or not apply_url:
                continue
            locs = [
                (loc.get("name") or "").strip()
                for loc in (item.get("locations") or [])
                if isinstance(loc, dict) and loc.get("name")
            ]
            location = ", ".join(locs)
            cats = [
                (c.get("name") or "").strip()
                for c in (item.get("categories") or [])
                if isinstance(c, dict) and c.get("name")
            ]
            levels = [
                (lv.get("name") or "").strip()
                for lv in (item.get("levels") or [])
                if isinstance(lv, dict) and lv.get("name")
            ]
            jobs.append(
                JobRecord(
                    source_type="feed",
                    source="themuse",
                    external_id=ext_id,
                    company_name=company,
                    title=title,
                    description_html=item.get("contents") or "",
                    apply_url=apply_url,
                    source_url=apply_url,
                    location=location,
                    remote_type=infer_remote_type(title, location),
                    department=cats[0] if cats else None,
                    seniority=levels[0] if levels else None,
                    tags=cats + levels,
                    posted_at=item.get("publication_date"),
                )
            )
    return jobs
