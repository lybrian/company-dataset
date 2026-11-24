"""Normalization utilities for ATS URLs/slugs and unified job postings."""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote, urlsplit

from job_pipeline.models import JobRecord, utc_now

# Core 5 ATS
GREENHOUSE = "greenhouse"
LEVER = "lever"
ASHBY = "ashby"
SMARTRECRUITERS = "smartrecruiters"
BREEZY = "breezy"

# 10 Extra ATS from original codebase
WORKABLE = "workable"
WORKDAY = "workday"
BAMBOOHR = "bamboohr"
RECRUITEE = "recruitee"
TEAMTAILOR = "teamtailor"
PERSONIO = "personio"
RIPPLING = "rippling"
ICIMS = "icims"
PINPOINT = "pinpoint"
JOIN = "join"

# Additional ATS platforms
DOVER = "dover"
GEM = "gem"

CORE_ATS = (GREENHOUSE, LEVER, ASHBY, SMARTRECRUITERS, BREEZY)
EXTRA_ATS = (WORKABLE, WORKDAY, BAMBOOHR, RECRUITEE, TEAMTAILOR, PERSONIO, RIPPLING, ICIMS, PINPOINT, JOIN)
ADDITIONAL_ATS = (DOVER, GEM)
SUPPORTED_ATS = tuple(sorted(CORE_ATS + EXTRA_ATS + ADDITIONAL_ATS))

_HOSTS = {
    "job-boards.greenhouse.io": GREENHOUSE,
    "boards.greenhouse.io": GREENHOUSE,
    "boards-api.greenhouse.io": GREENHOUSE,
    "job-boards.eu.greenhouse.io": GREENHOUSE,
    "boards.eu.greenhouse.io": GREENHOUSE,
    "jobs.lever.co": LEVER,
    "jobs.eu.lever.co": LEVER,
    "api.lever.co": LEVER,
    "api.eu.lever.co": LEVER,
    "jobs.ashbyhq.com": ASHBY,
    "api.ashbyhq.com": ASHBY,
    "careers.smartrecruiters.com": SMARTRECRUITERS,
    "jobs.smartrecruiters.com": SMARTRECRUITERS,
    "api.smartrecruiters.com": SMARTRECRUITERS,
}

_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_SUBDOMAIN_HOSTS = {
    BREEZY: re.compile(rf"^({_LABEL})\.breezy\.hr$"),
    BAMBOOHR: re.compile(rf"^({_LABEL})\.bamboohr\.com$"),
    RECRUITEE: re.compile(rf"^({_LABEL})\.recruitee\.com$"),
    TEAMTAILOR: re.compile(rf"^({_LABEL})\.teamtailor\.com$"),
    PINPOINT: re.compile(rf"^({_LABEL})\.pinpointhq\.com$"),
    ICIMS: re.compile(rf"^({_LABEL})\.icims\.com$"),
}
_PERSONIO_HOST = re.compile(rf"^({_LABEL})\.jobs\.personio\.(de|com)$")
_WORKABLE_LEGACY_HOST = re.compile(rf"^({_LABEL})\.workable\.com$")
_WORKDAY_HOST = re.compile(rf"^({_LABEL})\.(wd\d{{1,3}})\.myworkdayjobs\.com$")
_WORKDAY_SITE_HOST = re.compile(r"^(wd\d{1,3})\.myworkdaysite\.com$")
_WORKDAY_SITE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_LOCALE = re.compile(r"^[a-z]{2}-[A-Za-z]{2}$")
_PATH_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_RESERVED = frozenset({
    "www", "api", "app", "help", "support", "status", "blog", "careers", "jobs",
    "apply", "static", "cdn", "assets", "info", "mail", "login", "admin",
    "developers", "developer", "docs", "community", "care",
})


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
    if not code or len(code) > 128 or code.startswith(".") or "/" in code:
        return False
    if not all(32 < ord(ch) < 127 for ch in code):
        return False
    if code.endswith(";") or code.endswith("\\"):
        return False
    return any(ch.isascii() and ch.isalnum() for ch in code)


def clean_code(ats: str, code: object) -> str | None:
    if not isinstance(code, str):
        return None
    code = code.split("\\", 1)[0].strip().rstrip(";").strip()
    if not code:
        return None
    if ats == WORKDAY:
        m = re.fullmatch(r"([A-Za-z0-9-]+)\.(wd\d{1,3})/([A-Za-z0-9_-]{1,100})", code, re.I)
        if not m or not re.fullmatch(_LABEL, m.group(1).lower()):
            return None
        return f"{m.group(1).lower()}.{m.group(2).lower()}/{m.group(3)}"
    if ats in (WORKABLE, RIPPLING, JOIN, DOVER, GEM):
        return code if _PATH_SLUG.match(code) else None
    if ats in (BREEZY, BAMBOOHR, RECRUITEE, TEAMTAILOR, PINPOINT, ICIMS, PERSONIO):
        low = code.lower()
        if low in _RESERVED:
            return None
        return low if re.fullmatch(_LABEL, low) else None
    if ats == ASHBY and " " in code:
        if not re.fullmatch(r"[^\s]+( [^\s]+)*", code) or not is_valid_slug(code.replace(" ", "-")):
            return None
        return code
    return code if is_valid_slug(code) else None


def parse_board_url(raw: object) -> ParsedBoard | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    try:
        parts = urlsplit(text)
        raw_host = (parts.hostname or "").lower()
    except ValueError:
        return None
    host = raw_host[4:] if raw_host.startswith("www.") else raw_host
    segs = [unquote(seg) for seg in parts.path.split("/") if seg]

    # Core hosts
    ats = _HOSTS.get(host)
    if ats is not None:
        code = None
        region = None
        if ats == GREENHOUSE:
            region = "eu" if host in ("job-boards.eu.greenhouse.io", "boards.eu.greenhouse.io") else None
            if segs and segs[0] == "embed":
                code = _query_param(parts.query, "for")
            elif len(segs) >= 3 and segs[0] == "v1" and segs[1] == "boards":
                code = segs[2]
            elif segs:
                code = segs[0]
        elif ats == LEVER:
            region = "eu" if host in ("api.eu.lever.co", "jobs.eu.lever.co") else None
            if host in ("api.lever.co", "api.eu.lever.co"):
                if len(segs) >= 3 and segs[0] == "v0" and segs[1] == "postings":
                    code = segs[2]
            elif segs:
                code = segs[0]
        elif ats == ASHBY:
            if host == "api.ashbyhq.com":
                if len(segs) >= 3 and segs[0] == "posting-api" and segs[1] == "job-board":
                    code = segs[2]
            elif segs:
                code = segs[0]
        elif ats == SMARTRECRUITERS:
            if host == "api.smartrecruiters.com":
                if len(segs) >= 3 and segs[0] == "v1" and segs[1] == "companies":
                    code = segs[2]
            elif segs:
                code = segs[0]
        cleaned = clean_code(ats, code)
        return ParsedBoard(ats=ats, code=cleaned, region=region) if cleaned else None

    # Workable
    if host == "apply.workable.com":
        if segs and segs[0] not in ("api", "j") and _PATH_SLUG.match(segs[0]):
            return ParsedBoard(ats=WORKABLE, code=segs[0].lower())
        return None
    m = _WORKABLE_LEGACY_HOST.match(host)
    if m and m.group(1) not in _RESERVED:
        return ParsedBoard(ats=WORKABLE, code=m.group(1))

    # Workday
    m = _WORKDAY_HOST.match(host)
    if m:
        site = segs[1] if segs and _LOCALE.match(segs[0]) and len(segs) > 1 else (segs[0] if segs else None)
        if site and site != "wday" and _WORKDAY_SITE.match(site):
            cleaned = clean_code(WORKDAY, f"{m.group(1)}.{m.group(2)}/{site}")
            return ParsedBoard(ats=WORKDAY, code=cleaned) if cleaned else None
        return None
    m = _WORKDAY_SITE_HOST.match(host)
    if m and len(segs) >= 3 and segs[0] == "recruiting" and re.fullmatch(_LABEL, segs[1]) and _WORKDAY_SITE.match(segs[2]):
        cleaned = clean_code(WORKDAY, f"{segs[1]}.{m.group(1)}/{segs[2]}")
        return ParsedBoard(ats=WORKDAY, code=cleaned) if cleaned else None

    # Personio
    m = _PERSONIO_HOST.match(host)
    if m and m.group(1) not in _RESERVED:
        return ParsedBoard(ats=PERSONIO, code=m.group(1), region=("com" if m.group(2) == "com" else None))

    # Rippling
    if host == "ats.rippling.com":
        rest = segs[1:] if segs and _LOCALE.match(segs[0]) else segs
        if rest and rest[0] not in ("api", "static") and _PATH_SLUG.match(rest[0]):
            return ParsedBoard(ats=RIPPLING, code=rest[0])
        return None

    # JOIN
    if host == "join.com":
        if len(segs) >= 2 and segs[0] == "companies" and _PATH_SLUG.match(segs[1]):
            return ParsedBoard(ats=JOIN, code=segs[1])
        return None

    # Dover
    if host == "app.dover.com":
        if len(segs) >= 2 and segs[0] == "jobs" and _PATH_SLUG.match(segs[1]):
            return ParsedBoard(ats=DOVER, code=segs[1])
        return None

    # Gem
    if host == "jobs.gem.com":
        if segs and _PATH_SLUG.match(segs[0]):
            return ParsedBoard(ats=GEM, code=segs[0])
        return None

    # Subdomain-hosted ATS
    for sub_ats, rx in _SUBDOMAIN_HOSTS.items():
        m = rx.match(raw_host)
        if m:
            label = m.group(1)
            if label in _RESERVED:
                return None
            return ParsedBoard(ats=sub_ats, code=label)

    return None


_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def extract_boards_from_text(text: str) -> list[ParsedBoard]:
    """Scan arbitrary text/HTML for ATS board URLs and return deduplicated ParsedBoards."""
    found: dict[tuple[str, str], ParsedBoard] = {}
    if not text:
        return []
    cleaned = text.replace("\\/", "/").replace("\\u002F", "/")
    for match in _URL_RE.findall(cleaned):
        url = match.rstrip(".,;:!?)")
        parsed = parse_board_url(url)
        if parsed is not None:
            found.setdefault((parsed.ats, parsed.code.casefold()), parsed)
    return list(found.values())


def canonical_board_url(ats: str, code: str, region: str | None = None) -> str:
    q = quote(code, safe="")
    if ats == GREENHOUSE:
        host = "job-boards.eu.greenhouse.io" if region == "eu" else "job-boards.greenhouse.io"
        return f"https://{host}/{q}"
    if ats == LEVER:
        host = "jobs.eu.lever.co" if region == "eu" else "jobs.lever.co"
        return f"https://{host}/{q}"
    if ats == ASHBY:
        return f"https://jobs.ashbyhq.com/{q}"
    if ats == SMARTRECRUITERS:
        return f"https://careers.smartrecruiters.com/{q}"
    if ats == BREEZY:
        return f"https://{code}.breezy.hr"
    if ats == WORKABLE:
        return f"https://apply.workable.com/{q}/"
    if ats == WORKDAY:
        host, site = code.split("/", 1)
        return f"https://{host}.myworkdayjobs.com/{quote(site, safe='')}"
    if ats == BAMBOOHR:
        return f"https://{code}.bamboohr.com/careers"
    if ats == RECRUITEE:
        return f"https://{code}.recruitee.com/"
    if ats == TEAMTAILOR:
        return f"https://{code}.teamtailor.com/jobs"
    if ats == PERSONIO:
        return f"https://{code}.jobs.personio.{'com' if region == 'com' else 'de'}/"
    if ats == RIPPLING:
        return f"https://ats.rippling.com/{q}/jobs"
    if ats == ICIMS:
        return f"https://{code}.icims.com/jobs/search"
    if ats == PINPOINT:
        return f"https://{code}.pinpointhq.com/"
    if ats == JOIN:
        return f"https://join.com/companies/{q}"
    if ats == DOVER:
        return f"https://app.dover.com/jobs/{q}"
    if ats == GEM:
        return f"https://jobs.gem.com/{q}"
    raise ValueError(f"Unsupported ATS: {ats}")


# ---------------------------------------------------------------------------
# Job posting normalizers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(raw: str | None, max_len: int = 12000) -> str:
    if not raw:
        return ""
    # Unescape twice in case of double-encoded Greenhouse/XML descriptions
    text = html.unescape(html.unescape(raw))
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text


def slugify_company(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug[:80] or "unknown"


def compute_job_id(source: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{source}:{external_id}".encode("utf-8")).hexdigest()
    return digest[:24]


def compute_content_hash(job: JobRecord) -> str:
    payload = json.dumps(
        {
            "title": job.title,
            "company_name": job.company_name,
            "apply_url": job.apply_url,
            "location": job.location,
            "country": job.country,
            "remote_type": job.remote_type,
            "employment_type": job.employment_type,
            "department": job.department,
            "seniority": job.seniority,
            "tags": sorted(set(job.tags)),
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "salary_period": job.salary_period,
            "description_text": job.description_text[:4000],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def infer_remote_type(
    title: str = "",
    location: str = "",
    description: str = "",
    is_remote: bool | None = None,
    raw_workplace: str | None = None,
) -> str:
    if raw_workplace:
        rw = raw_workplace.strip().lower()
        if "hybrid" in rw:
            return "hybrid"
        if "remote" in rw or "telecommute" in rw:
            return "remote"
        if "onsite" in rw or "on-site" in rw or "office" in rw or "in-person" in rw:
            return "onsite"
    if is_remote is True:
        return "remote"
    combined = f"{title} {location}".lower()
    if re.search(r"\bhybrid\b", combined):
        return "hybrid"
    if re.search(r"\b(remote|work from home|wfh|anywhere|distributed)\b", combined):
        return "remote"
    if re.search(r"\b(on-?site|in-?office|in-?person)\b", combined):
        return "onsite"
    if is_remote is False:
        return "onsite"
    if description:
        head = description[:600].lower()
        if re.search(r"\bhybrid\b", head):
            return "hybrid"
        if re.search(r"\b(fully remote|100% remote|remote-first|remote only)\b", head):
            return "remote"
    return "unknown"


def infer_employment_type(raw: str | None) -> str:
    if not raw:
        return "unknown"
    t = raw.strip().lower().replace("_", " ").replace("-", " ")
    if "intern" in t or "co op" in t or "coop" in t:
        return "internship"
    if "part time" in t or "parttime" in t:
        return "part_time"
    if "freelance" in t:
        return "freelance"
    if "contract" in t or "temp" in t or "consultant" in t:
        return "contract"
    if "full time" in t or "fulltime" in t or "permanent" in t or "regular" in t or "salaried" in t:
        return "full_time"
    return "unknown"


_COUNTRY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(united states|u\.?s\.?a\.?|usa)\b", re.I), "US"),
    (re.compile(r"\bUS\b"), "US"),
    (re.compile(r",\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b"), "US"),
    (re.compile(r"\b(san francisco|new york|nyc|seattle|austin|boston|chicago|los angeles|denver|atlanta|miami)\b", re.I), "US"),
    (re.compile(r"\b(united kingdom|u\.?k\.?|england|scotland|wales|london|manchester|edinburgh)\b", re.I), "GB"),
    (re.compile(r"\bUK\b"), "GB"),
    (re.compile(r"\b(canada|toronto|vancouver|montreal|ottawa|calgary)\b", re.I), "CA"),
    (re.compile(r"\b(germany|deutschland|berlin|munich|münchen|hamburg|frankfurt)\b", re.I), "DE"),
    (re.compile(r"\b(france|paris|lyon|marseille)\b", re.I), "FR"),
    (re.compile(r"\b(netherlands|amsterdam|rotterdam|utrecht)\b", re.I), "NL"),
    (re.compile(r"\b(spain|españa|madrid|barcelona)\b", re.I), "ES"),
    (re.compile(r"\b(italy|italia|milan|rome)\b", re.I), "IT"),
    (re.compile(r"\b(ireland|dublin)\b", re.I), "IE"),
    (re.compile(r"\b(sweden|stockholm|gothenburg)\b", re.I), "SE"),
    (re.compile(r"\b(switzerland|zurich|zürich|geneva)\b", re.I), "CH"),
    (re.compile(r"\b(poland|warsaw|krakow|kraków|wroclaw)\b", re.I), "PL"),
    (re.compile(r"\b(portugal|lisbon|porto)\b", re.I), "PT"),
    (re.compile(r"\b(australia|sydney|melbourne|brisbane)\b", re.I), "AU"),
    (re.compile(r"\b(india|bangalore|bengaluru|mumbai|hyderabad|delhi|pune)\b", re.I), "IN"),
    (re.compile(r"\b(singapore)\b", re.I), "SG"),
    (re.compile(r"\b(japan|tokyo|osaka)\b", re.I), "JP"),
    (re.compile(r"\b(brazil|brasil|são paulo|sao paulo)\b", re.I), "BR"),
    (re.compile(r"\b(mexico|méxico|mexico city)\b", re.I), "MX"),
    (re.compile(r"\b(israel|tel aviv)\b", re.I), "IL"),
]


def extract_country(location: str | None) -> str | None:
    if not location:
        return None
    loc = location.strip()
    if len(loc) == 2 and loc.isalpha() and loc.isupper():
        return loc
    for rx, code in _COUNTRY_PATTERNS:
        if rx.search(loc):
            return code
    return None


def normalize_timestamp(value: object) -> str:
    """Parse ISO-8601, RFC-2822, or epoch (s / ms) into UTC ISO-8601 string."""
    if value is None or value == "":
        return utc_now()
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OSError, OverflowError):
            return utc_now()
    text = str(value).strip()
    if not text:
        return utc_now()
    if text.isdigit():
        return normalize_timestamp(int(text))
    # ISO-8601
    try:
        iso = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    # RFC-2822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        pass
    return utc_now()


def normalize_tags(tags: list[str] | None, max_tags: int = 12) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tags or []:
        if not isinstance(raw, str):
            continue
        t = re.sub(r"\s+", " ", raw).strip().lower()
        if not t or len(t) > 40 or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_tags:
            break
    return out


def finalize_job(job: JobRecord) -> JobRecord:
    """Fill in derived fields (description_text, remote_type, country, posted_at, tags)."""
    if not job.description_text and job.description_html:
        job.description_text = strip_html(job.description_html)
    else:
        job.description_text = strip_html(job.description_text)
    if job.remote_type == "unknown":
        job.remote_type = infer_remote_type(job.title, job.location, job.description_text)
    if job.country is None and job.location:
        job.country = extract_country(job.location)
    job.tags = normalize_tags(job.tags)
    job.posted_at = normalize_timestamp(job.posted_at)
    return job
