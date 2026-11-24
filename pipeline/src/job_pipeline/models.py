"""Data models for discovered boards, companies, and normalized job postings."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class DiscoveredBoard:
    ats: str
    code: str
    source: str
    region: str | None = None
    company_name: str | None = None

    @property
    def code_key(self) -> str:
        return self.code.casefold()


@dataclass
class BoardRow:
    id: int
    ats: str
    code_key: str
    code: str
    region: str | None = None
    company_name: str | None = None
    status: str = "active"
    consecutive_failures: int = 0
    jobs_count: int = 0
    last_synced_at: str | None = None


@dataclass
class CompanyRecord:
    slug: str
    name: str
    website_url: str | None = None
    logo_url: str | None = None
    description: str | None = None
    ats: str | None = None
    ats_code: str | None = None


@dataclass
class JobRecord:
    source_type: str  # "ats" | "feed"
    source: str  # e.g. "greenhouse", "remoteok"
    external_id: str
    company_name: str
    title: str
    apply_url: str
    source_url: str | None = None
    description_html: str | None = None
    description_text: str = ""
    location: str = ""
    country: str | None = None
    remote_type: str = "unknown"  # remote | hybrid | onsite | unknown
    employment_type: str = "unknown"  # full_time | part_time | contract | internship | freelance | unknown
    department: str | None = None
    seniority: str | None = None
    tags: list[str] = field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: str | None = None  # year | month | hour
    company_logo: str | None = None
    company_website: str | None = None
    posted_at: str | None = None
    board_id: int | None = None


@dataclass
class BoardFetchResult:
    board: BoardRow
    status: str  # "ok" | "not_found" | "error"
    jobs: list[JobRecord] = field(default_factory=list)
    company: CompanyRecord | None = None
    region_answered: str | None = None
    error: str | None = None
