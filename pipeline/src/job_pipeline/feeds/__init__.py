"""Direct public job feed registry."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from job_pipeline.feeds.arbeitnow import fetch_arbeitnow
from job_pipeline.feeds.himalayas import fetch_himalayas
from job_pipeline.feeds.hn_hiring import fetch_hn_hiring
from job_pipeline.feeds.jobicy import fetch_jobicy
from job_pipeline.feeds.landingjobs import fetch_landingjobs
from job_pipeline.feeds.remoteok import fetch_remoteok
from job_pipeline.feeds.remotive import fetch_remotive
from job_pipeline.feeds.themuse import fetch_themuse
from job_pipeline.feeds.usajobs import fetch_usajobs
from job_pipeline.feeds.workingnomads import fetch_workingnomads
from job_pipeline.feeds.wwr import fetch_wwr
from job_pipeline.http_client import HttpClient
from job_pipeline.models import JobRecord

FeedFetcher = Callable[[HttpClient], Awaitable[list[JobRecord]]]

FEED_FETCHERS: dict[str, FeedFetcher] = {
    "remoteok": fetch_remoteok,
    "weworkremotely": fetch_wwr,
    "arbeitnow": fetch_arbeitnow,
    "remotive": fetch_remotive,
    "jobicy": fetch_jobicy,
    "himalayas": fetch_himalayas,
    "themuse": fetch_themuse,
    "workingnomads": fetch_workingnomads,
    "hn_hiring": fetch_hn_hiring,
    "landingjobs": fetch_landingjobs,
    "usajobs": fetch_usajobs,
}
