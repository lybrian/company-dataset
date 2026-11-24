"""ATS fetcher registry covering all 17 supported ATS platforms."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from job_pipeline.ats.additional import fetch_dover, fetch_gem
from job_pipeline.ats.base import error_result
from job_pipeline.ats.core import (
    fetch_ashby,
    fetch_breezy,
    fetch_greenhouse,
    fetch_lever,
    fetch_smartrecruiters,
)
from job_pipeline.ats.extra import (
    fetch_bamboohr,
    fetch_icims,
    fetch_join,
    fetch_personio,
    fetch_pinpoint,
    fetch_recruitee,
    fetch_rippling,
    fetch_teamtailor,
    fetch_workable,
    fetch_workday,
)
from job_pipeline.http_client import HttpClient
from job_pipeline.models import BoardFetchResult, BoardRow
from job_pipeline.normalize import (
    ASHBY,
    BAMBOOHR,
    BREEZY,
    DOVER,
    GEM,
    GREENHOUSE,
    ICIMS,
    JOIN,
    LEVER,
    PERSONIO,
    PINPOINT,
    RECRUITEE,
    RIPPLING,
    SMARTRECRUITERS,
    TEAMTAILOR,
    WORKABLE,
    WORKDAY,
)

AtsFetcher = Callable[[HttpClient, BoardRow], Awaitable[BoardFetchResult]]

ATS_FETCHERS: dict[str, AtsFetcher] = {
    GREENHOUSE: fetch_greenhouse,
    LEVER: fetch_lever,
    ASHBY: fetch_ashby,
    SMARTRECRUITERS: fetch_smartrecruiters,
    BREEZY: fetch_breezy,
    WORKABLE: fetch_workable,
    WORKDAY: fetch_workday,
    BAMBOOHR: fetch_bamboohr,
    RECRUITEE: fetch_recruitee,
    TEAMTAILOR: fetch_teamtailor,
    PERSONIO: fetch_personio,
    RIPPLING: fetch_rippling,
    ICIMS: fetch_icims,
    PINPOINT: fetch_pinpoint,
    JOIN: fetch_join,
    DOVER: fetch_dover,
    GEM: fetch_gem,
}


async def fetch_board_jobs(client: HttpClient, board: BoardRow) -> BoardFetchResult:
    fetcher = ATS_FETCHERS.get(board.ats)
    if fetcher is None:
        return error_result(board, f"unsupported_ats:{board.ats}")
    return await fetcher(client, board)
