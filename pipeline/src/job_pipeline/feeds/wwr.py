"""WeWorkRemotely RSS job feed."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord
from job_pipeline.normalize import infer_employment_type

URL = "https://weworkremotely.com/remote-jobs.rss"


async def fetch_wwr(client: HttpClient) -> list[JobRecord]:
    resp = await client.get(URL, bucket="feed_wwr")
    if resp.status_code != 200:
        return []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []

    jobs: list[JobRecord] = []
    for item in root.findall(".//item"):
        raw_title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        if not raw_title or not link:
            continue
        if ":" in raw_title:
            company, title = [p.strip() for p in raw_title.split(":", 1)]
        else:
            company, title = "Unknown", raw_title
        region = (item.findtext("region") or "Remote").strip()
        category = (item.findtext("category") or "").strip() or None
        job_type = (item.findtext("type") or "").strip()
        jobs.append(
            JobRecord(
                source_type="feed",
                source="weworkremotely",
                external_id=guid,
                company_name=company or "Unknown",
                title=title or raw_title,
                description_html=item.findtext("description") or "",
                apply_url=link,
                source_url=link,
                location=region,
                remote_type="remote",
                employment_type=infer_employment_type(job_type),
                department=category,
                tags=[category] if category else [],
                posted_at=item.findtext("pubDate"),
            )
        )
    return jobs
