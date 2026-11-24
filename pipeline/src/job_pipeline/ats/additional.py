"""Job fetchers for additional public ATS platforms: Dover and Gem."""
from __future__ import annotations

from urllib.parse import quote

from job_pipeline.ats.base import error_result, fallback_company_name, not_found_result
from job_pipeline.http_client import HttpClient
from job_pipeline.models import BoardFetchResult, BoardRow, CompanyRecord, JobRecord
from job_pipeline.normalize import (
    DOVER,
    GEM,
    canonical_board_url,
    infer_employment_type,
    infer_remote_type,
    slugify_company,
)


async def fetch_dover(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://app.dover.com/api/v1/careers-page/{q}/jobs"
    try:
        resp = await client.get(url, bucket=DOVER)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        payload = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        if not ext_id or not title:
            continue
        locs = item.get("locations") or []
        location = ", ".join(
            (loc.get("name") or "").strip()
            for loc in locs
            if isinstance(loc, dict) and loc.get("name")
        )
        apply_url = f"https://app.dover.com/apply/{q}/{ext_id}"
        jobs.append(
            JobRecord(
                source_type="ats",
                source=DOVER,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(DOVER, board.code),
                description_html=item.get("description") or "",
                location=location,
                remote_type=infer_remote_type(title, location),
                employment_type=infer_employment_type(item.get("employment_type")),
                department=(item.get("department") or "").strip() or None,
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=DOVER, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_gem(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://api.gem.com/job_board/v0/{q}/job_posts/"
    try:
        resp = await client.get(url, bucket=GEM)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        payload = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = payload if isinstance(payload, list) else payload.get("job_posts")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("absolute_url") or f"https://jobs.gem.com/{q}/{ext_id}").strip()
        if not ext_id or not title:
            continue
        loc = item.get("location") or {}
        location = (loc.get("name") or "").strip() if isinstance(loc, dict) else str(loc or "")
        depts = [
            (d.get("name") or "").strip()
            for d in (item.get("departments") or [])
            if isinstance(d, dict) and d.get("name")
        ]
        jobs.append(
            JobRecord(
                source_type="ats",
                source=GEM,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(GEM, board.code),
                description_html=item.get("content") or "",
                location=location,
                remote_type=infer_remote_type(title, location, raw_workplace=item.get("location_type")),
                employment_type=infer_employment_type(item.get("employment_type")),
                department=depts[0] if depts else None,
                tags=depts,
                posted_at=item.get("first_published_at") or item.get("updated_at"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=GEM, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)
