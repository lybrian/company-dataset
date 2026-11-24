"""Shared helpers for ATS job fetchers."""
from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

from job_pipeline.models import BoardFetchResult, BoardRow


def fallback_company_name(board: BoardRow) -> str:
    if board.company_name and board.company_name.strip():
        return board.company_name.strip()
    raw = board.code.split("/", 1)[0].split(".", 1)[0]
    raw = re.sub(r"^(careers|jobs)-", "", raw, flags=re.I)
    return raw.replace("-", " ").replace("_", " ").strip().title() or board.code


def same_host(url: str, expected_host: str) -> bool:
    try:
        return (urlsplit(url).hostname or "").lower() == expected_host.lower()
    except ValueError:
        return False


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_OG_TITLE_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I)


def extract_page_title(text: str) -> str | None:
    for rx in (_OG_TITLE_RE, _TITLE_RE):
        m = rx.search(text or "")
        if m:
            t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
            if t:
                return t
    return None


def not_found_result(board: BoardRow, error: str = "board_not_found") -> BoardFetchResult:
    return BoardFetchResult(board=board, status="not_found", error=error)


def error_result(board: BoardRow, error: str) -> BoardFetchResult:
    return BoardFetchResult(board=board, status="error", error=error)
