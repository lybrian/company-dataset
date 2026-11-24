"""Configuration and rate limits for the job ingestion pipeline."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_USER_AGENT = "OpenJobBoardPipeline/1.0 (+https://github.com/lybrian/company-dataset; polite crawler)"

# Per-ATS concurrency and minimum delay between requests (seconds).
ATS_RATE_LIMITS: dict[str, tuple[int, float]] = {
    "greenhouse": (8, 0.1),
    "lever": (6, 0.15),
    "ashby": (6, 0.15),
    "smartrecruiters": (6, 0.15),
    "breezy": (5, 0.2),
    "workable": (5, 0.2),
    "workday": (4, 0.25),
    "bamboohr": (5, 0.2),
    "recruitee": (6, 0.15),
    "teamtailor": (5, 0.2),
    "personio": (4, 0.25),
    "rippling": (6, 0.15),
    "icims": (3, 0.35),
    "pinpoint": (6, 0.15),
    "join": (4, 0.3),
    "dover": (6, 0.15),
    "gem": (6, 0.15),
}

DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
DEFAULT_FEED_EXPIRY_DAYS = 14


@dataclass(frozen=True)
class Settings:
    database_url: str
    auth_token: str | None
    migrations_dir: Path
    user_agent: str = DEFAULT_USER_AGENT
    http_timeout: float = 25.0
    max_retries: int = 2
    batch_size: int = 50
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES
    feed_expiry_days: int = DEFAULT_FEED_EXPIRY_DAYS
    usajobs_api_key: str | None = None
    usajobs_user_agent: str | None = None

    @classmethod
    def from_env(cls, database_url: str | None = None, auth_token: str | None = None) -> "Settings":
        db_url = database_url or os.environ.get("TURSO_DATABASE_URL", "file:local.db")
        token = auth_token if auth_token is not None else os.environ.get("TURSO_AUTH_TOKEN")
        # Resolve repo-root db/migrations relative to this file or cwd.
        repo_root = Path(__file__).resolve().parents[3]
        migrations = repo_root / "db" / "migrations"
        if not migrations.exists():
            migrations = Path.cwd() / "db" / "migrations"
        return cls(
            database_url=db_url,
            auth_token=token,
            migrations_dir=migrations,
            usajobs_api_key=os.environ.get("USAJOBS_API_KEY") or None,
            usajobs_user_agent=os.environ.get("USAJOBS_USER_AGENT") or None,
        )
