"""Job fetchers for the 5 core ATS platforms: Greenhouse, Lever, Ashby, SmartRecruiters, Breezy."""
from __future__ import annotations

from urllib.parse import quote

from job_pipeline.ats.base import error_result, fallback_company_name, not_found_result
from job_pipeline.http_client import HttpClient
from job_pipeline.models import BoardFetchResult, BoardRow, CompanyRecord, JobRecord
from job_pipeline.normalize import (
    ASHBY,
    BREEZY,
    GREENHOUSE,
    LEVER,
    SMARTRECRUITERS,
    canonical_board_url,
    infer_employment_type,
    infer_remote_type,
    slugify_company,
    strip_html,
)


async def fetch_greenhouse(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://boards-api.greenhouse.io/v1/boards/{q}/jobs?content=true"
    try:
        resp = await client.get(url, bucket=GREENHOUSE)
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
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = board.company_name
    company_desc = None
    # Fetch lightweight board metadata if company_name is not yet known
    if not company_name:
        try:
            info_resp = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{q}", bucket=GREENHOUSE
            )
            if info_resp.status_code == 200:
                info = info_resp.json()
                company_name = (info.get("name") or "").strip() or None
                company_desc = strip_html(info.get("content") or "", max_len=1500) or None
        except Exception:
            pass
    company_name = company_name or fallback_company_name(board)

    jobs: list[JobRecord] = []
    region = board.region
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("absolute_url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        if ".eu.greenhouse.io/" in apply_url:
            region = "eu"
        loc_obj = item.get("location")
        location = (loc_obj.get("name") or "").strip() if isinstance(loc_obj, dict) else ""
        depts = [
            (d.get("name") or "").strip()
            for d in (item.get("departments") or [])
            if isinstance(d, dict) and d.get("name")
        ]
        dept = depts[0] if depts else None
        desc_html = item.get("content") or ""
        jobs.append(
            JobRecord(
                source_type="ats",
                source=GREENHOUSE,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(GREENHOUSE, board.code, region),
                description_html=desc_html,
                location=location,
                department=dept,
                tags=depts,
                posted_at=item.get("updated_at") or item.get("first_published"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(
        slug=slugify_company(company_name),
        name=company_name,
        description=company_desc,
        ats=GREENHOUSE,
        ats_code=board.code,
    )
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company, region_answered=region)


async def fetch_lever(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    regions = ["eu", None] if board.region == "eu" else [None, "eu"]
    payload = None
    answered_region = None
    for region in regions:
        host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
        url = f"https://{host}/v0/postings/{q}?mode=json"
        try:
            resp = await client.get(url, bucket=LEVER)
        except Exception as exc:
            return error_result(board, f"request_error: {exc}")
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            return error_result(board, f"http_{resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            return error_result(board, "invalid_json")
        if not isinstance(data, list):
            return error_result(board, "unexpected_schema")
        payload = data
        answered_region = region
        break

    if payload is None:
        return not_found_result(board)

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("text") or "").strip()
        apply_url = (item.get("hostedUrl") or item.get("applyUrl") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        cats = item.get("categories") or {}
        location = (cats.get("location") or "").strip()
        dept = (cats.get("department") or cats.get("team") or "").strip() or None
        commitment = cats.get("commitment")
        workplace = item.get("workplaceType")
        salary = item.get("salaryRange") or {}
        sal_min = int(salary["min"]) if isinstance(salary.get("min"), (int, float)) else None
        sal_max = int(salary["max"]) if isinstance(salary.get("max"), (int, float)) else None
        sal_cur = (salary.get("currency") or "").strip().upper() or None
        sal_per = (salary.get("interval") or "").strip().lower() or None
        if sal_per in ("per-year-salary", "yearly", "annual", "year"):
            sal_per = "year"
        elif sal_per in ("per-month-salary", "monthly", "month"):
            sal_per = "month"
        elif sal_per in ("per-hour-wage", "hourly", "hour"):
            sal_per = "hour"
        else:
            sal_per = None
        tags = [t for t in [cats.get("team"), cats.get("department"), cats.get("commitment")] if isinstance(t, str) and t.strip()]
        desc_html = item.get("description") or ""
        desc_plain = item.get("descriptionPlain") or ""
        jobs.append(
            JobRecord(
                source_type="ats",
                source=LEVER,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(LEVER, board.code, answered_region),
                description_html=desc_html,
                description_text=desc_plain,
                location=location,
                country=(item.get("country") or "").strip().upper() or None,
                remote_type=infer_remote_type(title, location, desc_plain, raw_workplace=workplace),
                employment_type=infer_employment_type(commitment),
                department=dept,
                tags=tags,
                salary_min=sal_min,
                salary_max=sal_max,
                salary_currency=sal_cur,
                salary_period=sal_per,
                posted_at=item.get("createdAt"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(
        slug=slugify_company(company_name),
        name=company_name,
        ats=LEVER,
        ats_code=board.code,
    )
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company, region_answered=answered_region)


async def fetch_ashby(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://api.ashbyhq.com/posting-api/job-board/{q}?includeCompensation=true"
    try:
        resp = await client.get(url, bucket=ASHBY)
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
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        if item.get("isListed") is False:
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("jobUrl") or item.get("applyUrl") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        location = (item.get("location") or "").strip()
        dept = (item.get("department") or item.get("team") or "").strip() or None
        is_remote = item.get("isRemote")
        workplace = item.get("workplaceType")
        comp = item.get("compensation") or {}
        sal_min = sal_max = sal_cur = sal_per = None
        for tier in comp.get("summaryComponents") or comp.get("compensationTiers") or []:
            if not isinstance(tier, dict):
                continue
            if tier.get("minValue") is not None:
                sal_min = int(tier["minValue"])
            if tier.get("maxValue") is not None:
                sal_max = int(tier["maxValue"])
            if tier.get("currencyCode"):
                sal_cur = str(tier["currencyCode"]).upper()
            if tier.get("interval"):
                iv = str(tier["interval"]).lower()
                sal_per = "year" if "year" in iv else ("month" if "month" in iv else ("hour" if "hour" in iv else None))
            if sal_min or sal_max:
                break
        tags = [t for t in [item.get("department"), item.get("team")] if isinstance(t, str) and t.strip()]
        jobs.append(
            JobRecord(
                source_type="ats",
                source=ASHBY,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(ASHBY, board.code),
                description_html=item.get("descriptionHtml") or "",
                description_text=item.get("descriptionPlain") or "",
                location=location,
                remote_type=infer_remote_type(title, location, is_remote=is_remote if isinstance(is_remote, bool) else None, raw_workplace=workplace),
                employment_type=infer_employment_type(item.get("employmentType")),
                department=dept,
                tags=tags,
                salary_min=sal_min,
                salary_max=sal_max,
                salary_currency=sal_cur,
                salary_period=sal_per,
                posted_at=item.get("publishedAt"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(
        slug=slugify_company(company_name),
        name=company_name,
        ats=ASHBY,
        ats_code=board.code,
    )
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_smartrecruiters(client: HttpClient, board: BoardRow, *, max_pages: int = 5) -> BoardFetchResult:
    q = quote(board.code, safe="")
    raw_jobs: list[dict] = []
    company_name = board.company_name

    for page in range(max_pages):
        offset = page * 100
        url = f"https://api.smartrecruiters.com/v1/companies/{q}/postings?limit=100&offset={offset}"
        try:
            resp = await client.get(url, bucket=SMARTRECRUITERS)
        except Exception as exc:
            if page == 0:
                return error_result(board, f"request_error: {exc}")
            break
        if resp.status_code == 404:
            return not_found_result(board) if page == 0 else BoardFetchResult(board=board, status="ok", jobs=[])
        if resp.status_code != 200:
            if page == 0:
                return error_result(board, f"http_{resp.status_code}")
            break
        try:
            data = resp.json()
        except ValueError:
            if page == 0:
                return error_result(board, "invalid_json")
            break
        content = data.get("content")
        if not isinstance(content, list):
            if page == 0:
                return error_result(board, "unexpected_schema")
            break
        raw_jobs.extend(content)
        total = int(data.get("totalFound") or len(raw_jobs))
        if len(raw_jobs) >= total or not content:
            break

    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("name") or "").strip()
        if not ext_id or not title:
            continue
        comp_obj = item.get("company") or {}
        if not company_name and isinstance(comp_obj, dict) and comp_obj.get("name"):
            company_name = str(comp_obj["name"]).strip()
        c_name = company_name or fallback_company_name(board)
        loc = item.get("location") or {}
        loc_parts = [p for p in [loc.get("city"), loc.get("region"), loc.get("country")] if p]
        location = ", ".join(str(p) for p in loc_parts)
        country = str(loc.get("country")).upper() if loc.get("country") and len(str(loc.get("country"))) == 2 else None
        is_remote = bool(loc.get("remote")) if "remote" in loc else None
        dept = (item.get("department") or {}).get("label") if isinstance(item.get("department"), dict) else None
        emp = (item.get("typeOfEmployment") or {}).get("label") if isinstance(item.get("typeOfEmployment"), dict) else None
        exp = (item.get("experienceLevel") or {}).get("label") if isinstance(item.get("experienceLevel"), dict) else None
        apply_url = f"https://jobs.smartrecruiters.com/{q}/{ext_id}"
        jobs.append(
            JobRecord(
                source_type="ats",
                source=SMARTRECRUITERS,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=c_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(SMARTRECRUITERS, board.code),
                location=location,
                country=country,
                remote_type=infer_remote_type(title, location, is_remote=is_remote),
                employment_type=infer_employment_type(emp),
                department=dept,
                seniority=exp,
                tags=[t for t in [dept, exp] if t],
                posted_at=item.get("releasedDate"),
                board_id=board.id,
            )
        )
    final_name = company_name or fallback_company_name(board)
    company = CompanyRecord(slug=slugify_company(final_name), name=final_name, ats=SMARTRECRUITERS, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_breezy(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.breezy.hr/json"
    try:
        resp = await client.get(url, bucket=BREEZY)
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
    if not isinstance(payload, list):
        return error_result(board, "unexpected_schema")

    company_name = board.company_name
    jobs: list[JobRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or item.get("friendly_id") or "")
        title = (item.get("name") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        comp_obj = item.get("company")
        if not company_name and isinstance(comp_obj, dict) and comp_obj.get("name"):
            company_name = str(comp_obj["name"]).strip()
        c_name = company_name or fallback_company_name(board)
        loc = item.get("location") or {}
        location = (loc.get("name") or "").strip() if isinstance(loc, dict) else ""
        is_remote = bool(loc.get("is_remote")) if isinstance(loc, dict) and "is_remote" in loc else None
        country_obj = loc.get("country") if isinstance(loc, dict) else None
        country = (country_obj.get("id") or "").upper() if isinstance(country_obj, dict) and len(str(country_obj.get("id") or "")) == 2 else None
        emp_obj = item.get("type")
        emp = emp_obj.get("name") if isinstance(emp_obj, dict) else None
        dept = (item.get("department") or "").strip() or None
        jobs.append(
            JobRecord(
                source_type="ats",
                source=BREEZY,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=c_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(BREEZY, board.code),
                location=location,
                country=country,
                remote_type=infer_remote_type(title, location, is_remote=is_remote),
                employment_type=infer_employment_type(emp),
                department=dept,
                tags=[dept] if dept else [],
                posted_at=item.get("published_date"),
                board_id=board.id,
            )
        )
    final_name = company_name or fallback_company_name(board)
    company = CompanyRecord(slug=slugify_company(final_name), name=final_name, ats=BREEZY, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)
