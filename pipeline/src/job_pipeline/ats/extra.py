"""Job fetchers for the 10 additional ATS platforms ported from platforms.py."""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

from job_pipeline.ats.base import (
    error_result,
    extract_page_title,
    fallback_company_name,
    not_found_result,
    same_host,
)
from job_pipeline.http_client import HttpClient
from job_pipeline.models import BoardFetchResult, BoardRow, CompanyRecord, JobRecord
from job_pipeline.normalize import (
    BAMBOOHR,
    ICIMS,
    JOIN,
    PERSONIO,
    PINPOINT,
    RECRUITEE,
    RIPPLING,
    TEAMTAILOR,
    WORKABLE,
    WORKDAY,
    canonical_board_url,
    infer_employment_type,
    infer_remote_type,
    slugify_company,
    strip_html,
)


async def fetch_workable(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://apply.workable.com/api/v1/widget/accounts/{q}?details=true"
    try:
        resp = await client.get(url, bucket=WORKABLE)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = data.get("jobs")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = (data.get("name") or "").strip() or fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("shortcode") or item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("url") or item.get("shortlink") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        loc_parts = [p for p in [item.get("city"), item.get("state"), item.get("country")] if p]
        location = ", ".join(str(p) for p in loc_parts)
        is_remote = bool(item.get("telecommuting")) if "telecommuting" in item else None
        jobs.append(
            JobRecord(
                source_type="ats",
                source=WORKABLE,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(WORKABLE, board.code),
                description_html=item.get("description") or "",
                location=location,
                remote_type=infer_remote_type(title, location, is_remote=is_remote),
                employment_type=infer_employment_type(item.get("employment_type")),
                department=(item.get("department") or "").strip() or None,
                tags=[item["department"]] if item.get("department") else [],
                posted_at=item.get("published_on"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(
        slug=slugify_company(company_name),
        name=company_name,
        description=strip_html(data.get("description"), max_len=1500) or None,
        ats=WORKABLE,
        ats_code=board.code,
    )
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_workday(client: HttpClient, board: BoardRow, *, max_pages: int = 5) -> BoardFetchResult:
    try:
        host_part, site = board.code.split("/", 1)
        tenant, wd = host_part.split(".", 1)
    except ValueError:
        return not_found_result(board, "invalid_workday_code")

    base_host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    api_url = f"{base_host}/wday/cxs/{tenant}/{quote(site, safe='')}/jobs"
    raw_jobs: list[dict] = []
    limit = 20

    for page in range(max_pages):
        payload = {"appliedFacets": {}, "limit": limit, "offset": page * limit, "searchText": ""}
        try:
            resp = await client.post_json(api_url, payload, bucket=WORKDAY)
        except Exception as exc:
            if page == 0:
                return error_result(board, f"request_error: {exc}")
            break
        if resp.status_code in (404, 422):
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
        postings = data.get("jobPostings")
        if not isinstance(postings, list):
            if page == 0:
                return error_result(board, "unexpected_schema")
            break
        raw_jobs.extend(postings)
        total = int(data.get("total") or len(raw_jobs))
        if len(raw_jobs) >= total or not postings:
            break

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        ext_path = (item.get("externalPath") or "").strip()
        if not title or not ext_path:
            continue
        req_ids = item.get("bulletFields") or []
        ext_id = str(req_ids[0]) if req_ids else ext_path.strip("/")
        apply_url = f"{base_host}/{quote(site, safe='')}{ext_path}"
        location = (item.get("locationsText") or "").strip()
        jobs.append(
            JobRecord(
                source_type="ats",
                source=WORKDAY,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(WORKDAY, board.code),
                location=location,
                remote_type=infer_remote_type(title, location, raw_workplace=item.get("remoteType")),
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=WORKDAY, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_bamboohr(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.bamboohr.com/careers/list"
    try:
        resp = await client.get(url, bucket=BAMBOOHR)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if not same_host(str(resp.url), f"{board.code}.bamboohr.com") or resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = data.get("result")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("jobOpeningName") or "").strip()
        if not ext_id or not title:
            continue
        loc_obj = item.get("location") or {}
        loc_parts = [p for p in [loc_obj.get("city"), loc_obj.get("state")] if p] if isinstance(loc_obj, dict) else []
        location = ", ".join(str(p) for p in loc_parts)
        is_remote = bool(item.get("isRemote")) if "isRemote" in item else None
        jobs.append(
            JobRecord(
                source_type="ats",
                source=BAMBOOHR,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=f"https://{board.code}.bamboohr.com/careers/{ext_id}",
                source_url=canonical_board_url(BAMBOOHR, board.code),
                location=location,
                remote_type=infer_remote_type(title, location, is_remote=is_remote),
                employment_type=infer_employment_type(item.get("employmentStatusLabel")),
                department=(item.get("departmentLabel") or "").strip() or None,
                tags=[item["departmentLabel"]] if item.get("departmentLabel") else [],
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=BAMBOOHR, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_recruitee(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.recruitee.com/api/offers/"
    try:
        resp = await client.get(url, bucket=RECRUITEE)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = data.get("offers")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = board.company_name
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or item.get("slug") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("careers_url") or item.get("careers_apply_url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        if not company_name and item.get("company_name"):
            company_name = str(item["company_name"]).strip()
        c_name = company_name or fallback_company_name(board)
        location = (item.get("location") or "").strip()
        is_remote = bool(item.get("remote")) if "remote" in item else None
        is_hybrid = bool(item.get("hybrid")) if "hybrid" in item else False
        remote_type = "hybrid" if is_hybrid else infer_remote_type(title, location, is_remote=is_remote)
        jobs.append(
            JobRecord(
                source_type="ats",
                source=RECRUITEE,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=c_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(RECRUITEE, board.code),
                description_html=(item.get("description") or "") + "\n" + (item.get("requirements") or ""),
                location=location,
                country=(item.get("country_code") or "").upper() or None,
                remote_type=remote_type,
                employment_type=infer_employment_type(item.get("employment_type_code")),
                department=(item.get("department") or "").strip() or None,
                tags=[t for t in (item.get("tags") or []) if isinstance(t, str)],
                posted_at=item.get("published_at") or item.get("created_at"),
                board_id=board.id,
            )
        )
    final_name = company_name or fallback_company_name(board)
    company = CompanyRecord(slug=slugify_company(final_name), name=final_name, ats=RECRUITEE, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_teamtailor(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.teamtailor.com/jobs.json"
    try:
        resp = await client.get(url, bucket=TEAMTAILOR)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return error_result(board, "invalid_json")
    raw_jobs = data.get("items")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = (data.get("title") or "").strip() or fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        jobs.append(
            JobRecord(
                source_type="ats",
                source=TEAMTAILOR,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(TEAMTAILOR, board.code),
                description_html=item.get("content_html") or "",
                description_text=item.get("summary") or "",
                tags=[t for t in (item.get("tags") or []) if isinstance(t, str)],
                posted_at=item.get("date_published"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=TEAMTAILOR, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_personio(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    regions = ["com", None] if board.region == "com" else [None, "com"]
    xml_text = None
    answered_region = None
    for region in regions:
        tld = "com" if region == "com" else "de"
        url = f"https://{board.code}.jobs.personio.{tld}/xml"
        try:
            resp = await client.get(url, bucket=PERSONIO)
        except Exception as exc:
            return error_result(board, f"request_error: {exc}")
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            return error_result(board, f"http_{resp.status_code}")
        if "<workzag-jobs" not in resp.text:
            return error_result(board, "unexpected_schema")
        xml_text = resp.text
        answered_region = region
        break

    if xml_text is None:
        return not_found_result(board)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return error_result(board, "invalid_xml")

    tld = "com" if answered_region == "com" else "de"
    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for pos in root.findall(".//position"):
        ext_id = (pos.findtext("id") or "").strip()
        title = (pos.findtext("name") or "").strip()
        if not ext_id or not title:
            continue
        subcompany = (pos.findtext("subcompany") or "").strip()
        c_name = subcompany or company_name
        location = (pos.findtext("office") or "").strip()
        dept = (pos.findtext("department") or "").strip() or None
        schedule = (pos.findtext("schedule") or "").strip()
        emp = (pos.findtext("employmentType") or "").strip()
        seniority = (pos.findtext("seniority") or "").strip() or None
        desc_parts = [
            (d.findtext("value") or "")
            for d in pos.findall(".//jobDescription")
        ]
        desc_html = "\n".join(p for p in desc_parts if p)
        apply_url = f"https://{board.code}.jobs.personio.{tld}/job/{ext_id}"
        jobs.append(
            JobRecord(
                source_type="ats",
                source=PERSONIO,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=c_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(PERSONIO, board.code, answered_region),
                description_html=desc_html,
                location=location,
                employment_type=infer_employment_type(f"{emp} {schedule}"),
                department=dept,
                seniority=seniority,
                tags=[t for t in [dept, seniority] if t],
                posted_at=pos.findtext("createdAt"),
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=PERSONIO, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company, region_answered=answered_region)


async def fetch_rippling(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://api.rippling.com/platform/api/ats/v1/board/{q}/jobs"
    try:
        resp = await client.get(url, bucket=RIPPLING)
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

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("uuid") or item.get("id") or "")
        title = (item.get("name") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        loc = item.get("workLocation") or {}
        location = (loc.get("label") or "").strip() if isinstance(loc, dict) else ""
        dept_obj = item.get("department") or {}
        dept = (dept_obj.get("label") or "").strip() if isinstance(dept_obj, dict) else None
        jobs.append(
            JobRecord(
                source_type="ats",
                source=RIPPLING,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(RIPPLING, board.code),
                location=location,
                department=dept or None,
                tags=[dept] if dept else [],
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=RIPPLING, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


_ICIMS_LINK_RE = re.compile(
    r'href="(https://[^"/]+\.icims\.com/jobs/(\d+)/[^"?]+/job)[^"]*"[^>]*>(.*?)</a>',
    re.I | re.S,
)


async def fetch_icims(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.icims.com/jobs/search?ss=1&in_iframe=1"
    try:
        resp = await client.get(url, bucket=ICIMS)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200 or not same_host(str(resp.url), f"{board.code}.icims.com"):
        return error_result(board, f"http_{resp.status_code}")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    seen: set[str] = set()
    for match in _ICIMS_LINK_RE.finditer(resp.text):
        job_url, ext_id, raw_title = match.group(1), match.group(2), match.group(3)
        if ext_id in seen:
            continue
        seen.add(ext_id)
        title = strip_html(raw_title, max_len=250)
        if not title:
            continue
        jobs.append(
            JobRecord(
                source_type="ats",
                source=ICIMS,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=job_url,
                source_url=canonical_board_url(ICIMS, board.code),
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=ICIMS, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_pinpoint(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    url = f"https://{board.code}.pinpointhq.com/postings.json"
    try:
        resp = await client.get(url, bucket=PINPOINT)
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
    raw_jobs = payload.get("data")
    if not isinstance(raw_jobs, list):
        return error_result(board, "unexpected_schema")

    company_name = fallback_company_name(board)
    jobs: list[JobRecord] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        ext_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        apply_url = (item.get("url") or "").strip()
        if not ext_id or not title or not apply_url:
            continue
        loc_obj = item.get("location") or {}
        location = (loc_obj.get("name") or "").strip() if isinstance(loc_obj, dict) else ""
        job_obj = item.get("job") or {}
        dept = (job_obj.get("department") or {}).get("name") if isinstance(job_obj.get("department"), dict) else None
        jobs.append(
            JobRecord(
                source_type="ats",
                source=PINPOINT,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=title,
                apply_url=apply_url,
                source_url=canonical_board_url(PINPOINT, board.code),
                description_html=item.get("description") or "",
                location=location,
                remote_type=infer_remote_type(title, location, raw_workplace=item.get("workplace_type")),
                employment_type=infer_employment_type(item.get("employment_type_text")),
                department=dept,
                tags=[dept] if dept else [],
                salary_min=int(item["compensation_minimum"]) if isinstance(item.get("compensation_minimum"), (int, float)) else None,
                salary_max=int(item["compensation_maximum"]) if isinstance(item.get("compensation_maximum"), (int, float)) else None,
                salary_currency=(item.get("compensation_currency") or "").upper() or None,
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=PINPOINT, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)


async def fetch_join(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    q = quote(board.code, safe="")
    url = f"https://join.com/companies/{q}"
    try:
        resp = await client.get(url, bucket=JOIN)
    except Exception as exc:
        return error_result(board, f"request_error: {exc}")
    if resp.status_code == 404:
        return not_found_result(board)
    if resp.status_code != 200:
        return error_result(board, f"http_{resp.status_code}")

    title_str = extract_page_title(resp.text) or ""
    m_name = re.match(r"^Jobs at (.+?) \| JOIN$", title_str, re.I)
    company_name = m_name.group(1).strip() if m_name else fallback_company_name(board)

    link_re = re.compile(
        rf'href="(/companies/{re.escape(board.code)}/(\d+)-([^"?#]+))"',
        re.I,
    )
    jobs: list[JobRecord] = []
    seen: set[str] = set()
    for match in link_re.finditer(resp.text):
        path, ext_id, slug = match.group(1), match.group(2), match.group(3)
        if ext_id in seen:
            continue
        seen.add(ext_id)
        job_title = html.unescape(slug.replace("-", " ")).strip().title()
        jobs.append(
            JobRecord(
                source_type="ats",
                source=JOIN,
                external_id=f"{board.code_key}:{ext_id}",
                company_name=company_name,
                title=job_title,
                apply_url=f"https://join.com{path}",
                source_url=url,
                board_id=board.id,
            )
        )
    company = CompanyRecord(slug=slugify_company(company_name), name=company_name, ats=JOIN, ats_code=board.code)
    return BoardFetchResult(board=board, status="ok", jobs=jobs, company=company)
