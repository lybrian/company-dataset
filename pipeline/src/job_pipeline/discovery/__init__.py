"""Board discovery orchestrator."""
from __future__ import annotations

from job_pipeline.discovery.hn import discover_hn_boards
from job_pipeline.discovery.registries import discover_all_registries
from job_pipeline.discovery.vc_boards import discover_vc_boards
from job_pipeline.discovery.yc import discover_yc
from job_pipeline.http_client import HttpClient
from job_pipeline.models import DiscoveredBoard

DISCOVERY_GROUPS = {
    "registries": discover_all_registries,
    "yc": discover_yc,
    "hn": discover_hn_boards,
    "vc": discover_vc_boards,
}


async def run_discovery(client: HttpClient, groups: list[str] | None = None) -> dict[str, list[DiscoveredBoard]]:
    selected = groups or list(DISCOVERY_GROUPS.keys())
    results: dict[str, list[DiscoveredBoard]] = {}
    for name in selected:
        fn = DISCOVERY_GROUPS.get(name)
        if fn is None:
            continue
        results[name] = await fn(client)
    return results
