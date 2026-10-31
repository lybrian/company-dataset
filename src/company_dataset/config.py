from __future__ import annotations

import os
from pathlib import Path

RAW_DIR_NAME = "raw"
CACHE_DIR_NAME = "cache"
INTERMEDIATE_DIR_NAME = "intermediate"
OUTPUT_DIR_NAME = "output"
REVIEW_DIR_NAME = "review"
REPORTS_DIR_NAME = "reports"

DEFAULT_DATA_DIR = "data"

ATS_RATE_LIMITS = {
    "smartrecruiters": {"max_concurrent": 2, "delay_seconds": 0.5},
    "breezy": {"max_concurrent": 2, "delay_seconds": 0.5},
}

RATE_LIMIT_ENV_VARS = {
    "smartrecruiters": {
        "max_concurrent": "COMPANY_DATASET_SMARTRECRUITERS_MAX_CONCURRENT",
        "delay_seconds": "COMPANY_DATASET_SMARTRECRUITERS_DELAY_SECONDS",
    },
    "breezy": {
        "max_concurrent": "COMPANY_DATASET_BREEZY_MAX_CONCURRENT",
        "delay_seconds": "COMPANY_DATASET_BREEZY_DELAY_SECONDS",
    },
}


def _parse_rate_limit_value(field: str, raw: str, var: str):
    try:
        value = int(raw) if field == "max_concurrent" else float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {var}: {raw!r}") from exc
    if field == "max_concurrent" and value < 1:
        raise ValueError(f"invalid {var}: must be >= 1")
    if field == "delay_seconds" and value < 0:
        raise ValueError(f"invalid {var}: must be >= 0")
    return value


def resolve_rate_limits(
    overrides: dict[str, dict] | None = None,
    env=None,
) -> dict[str, dict]:
    env = os.environ if env is None else env
    limits = {ats: dict(cfg) for ats, cfg in ATS_RATE_LIMITS.items()}
    for ats, fields in RATE_LIMIT_ENV_VARS.items():
        for field, var in fields.items():
            raw = env.get(var)
            if raw is None or str(raw).strip() == "":
                continue
            limits[ats][field] = _parse_rate_limit_value(field, str(raw).strip(), var)
    for ats, fields in (overrides or {}).items():
        for field, value in fields.items():
            if value is not None:
                limits[ats][field] = value
    return limits


def resolve_dirs(data_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, Path]:
    base = Path(data_dir)
    dirs = {
        "data": base,
        "raw": base / RAW_DIR_NAME,
        "cache": base / CACHE_DIR_NAME,
        "intermediate": base / INTERMEDIATE_DIR_NAME,
        "output": base / OUTPUT_DIR_NAME,
        "review": base / REVIEW_DIR_NAME,
        "reports": Path(REPORTS_DIR_NAME),
    }
    for key, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
    return dirs
