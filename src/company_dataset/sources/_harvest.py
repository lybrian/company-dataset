"""What the discovery harvests share: one tokens.csv format, and which identifiers are worth checking."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from company_dataset.models import Reject, SourceRecord
from company_dataset.normalize import CORE_ATS, clean_code, parse_board_url

# Stricter than clean_code, which lets template leftovers from crawled pages through ("$company").
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
COLUMNS = ["ats", "code", "region", "evidence"]


def board_from_url(url: str) -> tuple[str, str, str] | None:
    """(ats, code, region) when a URL is a target-ATS board with a plausible identifier."""
    parsed = parse_board_url(url)
    if not parsed or parsed.ats not in CORE_ATS:
        return None
    code = clean_code(parsed.ats, parsed.code)
    if not code or not _SLUG_RE.match(code):
        return None
    return parsed.ats, code, parsed.region or ""


def write_tokens(path: Path, tokens: dict[tuple[str, str], tuple[str, str, str]]) -> int:
    """tokens: (ats, casefolded code) -> (spelling, region, evidence). Replaces the file only once complete."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(COLUMNS)
        for (ats, _), (code, region, evidence) in sorted(tokens.items()):
            writer.writerow([ats, code, region, evidence])
    tmp.replace(path)
    return len(tokens)


def parse_tokens(path: Path, source: str) -> tuple[list[SourceRecord], list[Reject]]:
    records: list[SourceRecord] = []
    rejects: list[Reject] = []
    if not Path(path).exists():
        return records, rejects
    with open(path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            ref = f"line {i}"
            ats, raw = (row.get("ats") or "").strip(), (row.get("code") or "").strip()
            if ats not in CORE_ATS:
                rejects.append(Reject(source=source, reason="unsupported_ats", detail=ats, row_ref=ref))
                continue
            code = clean_code(ats, raw)
            if not code or not _SLUG_RE.match(code):
                rejects.append(Reject(source=source, reason="invalid_slug", detail=raw, row_ref=ref, ats=ats))
                continue
            # No name: a discovered identifier says nothing about which company runs the board.
            records.append(SourceRecord(source=source, ats=ats, code=code, region=(row.get("region") or "").strip() or None, row_ref=ref))
    return records, rejects
