from company_dataset.sources import (
    africa_ats, builder_jobs, commoncrawl, commoncrawl_gapfill, commoncrawl_indexer, feashliaa, headcountlabs, joa, jobanalytics, kaleb, kalil,
    lastround, latmay, legacy_subdomains, moonie, openatsfeed, slug_prober, wayback_cdx,
)

SOURCES = [latmay, lastround, kaleb, moonie, feashliaa, commoncrawl, headcountlabs, openatsfeed, kalil, joa,
           africa_ats, builder_jobs, commoncrawl_gapfill, jobanalytics, legacy_subdomains, wayback_cdx, commoncrawl_indexer, slug_prober]

__all__ = ["SOURCES", "africa_ats", "builder_jobs", "commoncrawl", "commoncrawl_gapfill", "feashliaa", "headcountlabs", "joa", "jobanalytics",
           "kaleb", "kalil", "lastround", "latmay", "legacy_subdomains", "moonie", "openatsfeed", "commoncrawl_indexer", "slug_prober", "wayback_cdx"]
