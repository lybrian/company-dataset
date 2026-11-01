# Verified ATS companies — 15 ATS platforms

Generated 2026-10-31. See `final_report.md` for counts, verification method, checks and limitations.

## Files
- `output/companies_total.csv` — every verified unique company (28,459 rows), with-jobs and zero-jobs. Filter `verification_tier` (A/C/blank) as needed.
- `output/companies_complete.csv` — rows with all seven required fields (9,405).
- `output/companies_incomplete.csv` — the rest, with `missing_fields`.
- `output/source_manifest.csv` — every source, license, checksum and contribution.
- `review/uncertain_companies.csv` — unresolved or not validated (not counted).
- `review/dead_companies.csv` — boards the vendor reports as not existing, or whose hosted page is gone.
- `review/rejected_records.csv`, `review/possible_duplicates.csv`, `review/companies_detailed.csv` — provenance and audit trail.
- `SOURCES.md`, `final_report.md`, `consumer_check.json`.

## Columns
name, description, linkedin_url, website_url, careersite_url, ats_system, ats_code (required) plus complete, missing_fields, http_status, checked_at, jobs_count, endpoint, verification_tier.
Blank means unknown; no value is invented.

## Reproduce a check
Build the URL from `ats_system` + `ats_code` (see the endpoint table in final_report.md) or use the `endpoint` column, and request it; a live board answers 200.
