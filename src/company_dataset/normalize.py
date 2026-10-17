from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

GREENHOUSE = "greenhouse"
LEVER = "lever"
ASHBY = "ashby"
SUPPORTED_ATS = (ASHBY, GREENHOUSE, LEVER)

_HOSTS = {
    "job-boards.greenhouse.io": GREENHOUSE,
    "boards.greenhouse.io": GREENHOUSE,
    "boards-api.greenhouse.io": GREENHOUSE,
    "jobs.lever.co": LEVER,
    "jobs.eu.lever.co": LEVER,
    "api.lever.co": LEVER,
    "api.eu.lever.co": LEVER,
    "jobs.ashbyhq.com": ASHBY,
    "api.ashbyhq.com": ASHBY,
}


@dataclass(frozen=True)
class ParsedBoard:
    ats: str
    code: str
    region: str | None = None


def _query_param(query: str, name: str) -> str | None:
    for part in query.split("&"):
        if not part:
            continue
        key, _, value = part.partition("=")
        if unquote(key) == name:
            return unquote(value)
    return None


def is_valid_slug(code: str) -> bool:
    if not code or len(code) > 128:
        return False
    if code.startswith("."):
        return False
    if "/" in code:
        return False
    if not all(32 < ord(ch) < 127 for ch in code):
        return False
    # A trailing ";" or "\" never occurs in a real board slug; it is the signature
    # of a scraped CSS/JS fragment leaking into a source dataset's URL column
    # (e.g. "100vw;", "Abridge\\") rather than a company-chosen identifier.
    if code.endswith(";") or code.endswith("\\"):
        return False
    return any(ch.isascii() and ch.isalnum() for ch in code)


def parse_board_url(raw) -> ParsedBoard | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    try:
        parts = urlsplit(text)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    if host.startswith("www."):
        host = host[4:]
    ats = _HOSTS.get(host)
    if ats is None:
        return None
    segs = [unquote(seg) for seg in parts.path.split("/") if seg != ""]
    code = None
    region = None
    if ats == GREENHOUSE:
        if segs and segs[0] == "embed":
            code = _query_param(parts.query, "for")
        elif len(segs) >= 3 and segs[0] == "v1" and segs[1] == "boards":
            code = segs[2]
        elif segs:
            code = segs[0]
    elif ats == LEVER:
        if host in ("api.lever.co", "api.eu.lever.co"):
            region = "eu" if host == "api.eu.lever.co" else None
            if len(segs) >= 3 and segs[0] == "v0" and segs[1] == "postings":
                code = segs[2]
        else:
            region = "eu" if host == "jobs.eu.lever.co" else None
            if segs:
                code = segs[0]
    else:
        if host == "api.ashbyhq.com":
            if len(segs) >= 3 and segs[0] == "posting-api" and segs[1] == "job-board":
                code = segs[2]
        elif segs:
            code = segs[0]
    if code is None:
        return None
    code = clean_code(ats, code)
    if code is None:
        return None
    return ParsedBoard(ats=ats, code=code, region=region)


def clean_code(ats: str, code) -> str | None:
    """A board slug as the vendor would accept it, or None.

    Scraped columns often carry the tail of a JS string ("abridge\\", "camber.\\r\\n…",
    "block;"); the slug is what comes before it. Ashby organization slugs may contain
    single spaces ("Applied Compute"). Validation decides whether the board is real.
    """
    if not isinstance(code, str):
        return None
    code = code.split("\\", 1)[0].strip().rstrip(";").strip()
    if ats == ASHBY and " " in code:
        if not re.fullmatch(r"[^\s]+( [^\s]+)*", code) or not is_valid_slug(code.replace(" ", "-")):
            return None
        return code
    return code if is_valid_slug(code) else None


def canonical_board_url(ats: str, code: str, region: str | None = None) -> str:
    q = quote(code, safe="")
    if ats == GREENHOUSE:
        return f"https://job-boards.greenhouse.io/{q}"
    if ats == LEVER:
        host = "jobs.eu.lever.co" if region == "eu" else "jobs.lever.co"
        return f"https://{host}/{q}"
    if ats == ASHBY:
        return f"https://jobs.ashbyhq.com/{q}"
    raise ValueError(f"unsupported ats: {ats}")


def canonical_api_url(ats: str, code: str, region: str | None = None) -> str:
    q = quote(code, safe="")
    if ats == GREENHOUSE:
        return f"https://boards-api.greenhouse.io/v1/boards/{q}/jobs"
    if ats == LEVER:
        host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
        return f"https://{host}/v0/postings/{q}?mode=json"
    if ats == ASHBY:
        return f"https://api.ashbyhq.com/posting-api/job-board/{q}"
    raise ValueError(f"unsupported ats: {ats}")


def greenhouse_board_info_url(code: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{quote(code, safe='')}"


# Hosts that are never a company's own website: ATS / recruiting platforms, link
# shorteners, site builders' marketing domains, and big platforms whose links show up
# in page chrome. A website on one of these says nothing about the company itself.
_NON_COMPANY_HOSTS = (
    "greenhouse.io", "greenhouse.com", "lever.co", "ashbyhq.com", "ashbyprd.com",
    "careerpuck.com", "myworkdayjobs.com", "workday.com", "icims.com", "adp.com",
    "ultipro.com", "ukg.com", "applytojob.com", "jazzhr.com", "bamboohr.com",
    "smartrecruiters.com", "jobvite.com", "workable.com", "recruitee.com",
    "breezy.hr", "teamtailor.com", "pinpointhq.com", "rippling.com", "paylocity.com",
    "taleo.net", "successfactors.com", "dayforcehcm.com", "paycomonline.net",
    "indeed.com", "glassdoor.com", "linkedin.com", "lnkd.in", "bit.ly", "linktr.ee",
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com", "tiktok.com",
    "google.com", "goo.gl", "squarespace.com", "wix.com", "webflow.io", "github.io",
    "notion.site", "medium.com", "outlook.com", "safelinks.protection.outlook.com",
    "typeform.com", "hubspot.com", "calendly.com", "cloudflare.com", "gstatic.com",
    "googleapis.com", "w3.org", "schema.org", "apple.com",
)
_HOST_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
CAREER_SUBDOMAINS = ("careers", "career", "jobs", "job", "join", "work", "talent", "apply", "recruiting", "hiring")


def host_of(url) -> str:
    """Lower-cased hostname without a leading www., or "" when unparseable."""
    if not isinstance(url, str) or not url.strip():
        return ""
    text = url.strip()
    if "://" not in text:
        text = "https://" + text
    try:
        host = (urlsplit(text).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def is_non_company_host(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in _NON_COMPANY_HOSTS)


def clean_website(url) -> str | None:
    """Normalize a website to scheme://host, or None if it cannot be a company site.

    Rejects malformed values seen in sources ("https://https:", "javascript:void(0)",
    "http://Beaver Process Equipment") and hosts that belong to platforms rather than
    the company.
    """
    if not isinstance(url, str):
        return None
    text = url.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    try:
        parts = urlsplit(text)
        raw_host = parts.hostname or ""
    except ValueError:
        return None
    if parts.scheme not in ("http", "https"):
        return None
    host = raw_host.lower().rstrip(".")
    if not _HOST_RE.match(host) or is_non_company_host(host.removeprefix("www.")):
        return None
    return f"{parts.scheme}://{host}"


def career_subdomain_parent(host: str) -> str | None:
    """careers.acme.com -> acme.com; None when the host has no career-style first label."""
    labels = host.split(".")
    if len(labels) >= 3 and labels[0] in CAREER_SUBDOMAINS:
        return ".".join(labels[1:])
    return None
