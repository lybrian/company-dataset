from company_dataset.sources import (
    africa_ats, builder_jobs, commoncrawl, commoncrawl_gapfill, feashliaa, headcountlabs, joa, jobanalytics, kaleb, kalil, lastround, latmay,
    legacy_subdomains, moonie, openatsfeed,
)

SOURCES = [latmay, lastround, kaleb, moonie, feashliaa, commoncrawl, headcountlabs, openatsfeed, kalil, joa,
           africa_ats, builder_jobs, commoncrawl_gapfill, jobanalytics, legacy_subdomains]

__all__ = ["SOURCES", "africa_ats", "builder_jobs", "commoncrawl", "commoncrawl_gapfill", "feashliaa", "headcountlabs", "joa", "jobanalytics",
           "kaleb", "kalil", "lastround", "latmay", "legacy_subdomains", "moonie", "openatsfeed"]
