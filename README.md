# company-dataset

A list of companies that hire through **Greenhouse, Lever, Ashby, SmartRecruiters or Breezy HR**, built from public datasets and the vendors' own public job-board APIs.

As of the last run (October 2026):

- **8,373 companies** with all seven required fields: `data/output/companies_complete.csv`
- **6,715 more** live companies missing at least one field: `data/output/companies_incomplete.csv`, which names the missing fields
- **All 15,088** in one file for merging: `data/output/companies_total.csv`, with `complete` and `missing_fields` columns
- 72% of the complete companies are headquartered in the US, UK or Canada

All three start with the same required columns: `name`, `description`, `linkedin_url`, `website_url`, `careersite_url`, `ats_system`, `ats_code`. To share the data, send `companies_complete.csv` (or `companies_total.csv`) together with `source_manifest.csv`, which carries the credit some source licenses require.

Every company on the list has a board that answered the vendor's API when we checked it. Nothing is made up. If we couldn't find a value from a real source, the field is empty and the company goes in the incomplete file.

## Where the values come from

- **careersite_url, ats_code**: the board itself, for the exact slug the vendor accepted.
- **name**: the vendor's own record (the Greenhouse board name, the Ashby organization, the Lever page title). We fall back to the source datasets, then BigPicture, then the homepage title. Labels like "Open Roles" or "Acme Careers" don't count as names.
- **website_url**: Ashby publishes each company's website, and Lever boards link to it. For Greenhouse we use the company domain its job links point to, or links in the company's own job ads. If none of those work, we look the company up in BigPicture by name, but only accept a domain that matches the board slug and whose homepage names the company.
- **linkedin_url**: the LinkedIn company page linked from the company's homepage, cross-checked against BigPicture; otherwise BigPicture's record for that domain. It is never built from a name.
- **description**: the description the company gives its own homepage (the meta description), or failing that its Greenhouse board intro. Descriptions must be in English: if a homepage is in another language we ask for its English version (and try `/en`, `/en-us`, `/en-gb`, `/us`); if there isn't one, the description is left empty. Recruiting copy ("Join our team…"), cookie banners and placeholders are filtered out, and long text is cut at a sentence boundary.

Vendor demo and sandbox boards ("Lever Demo 2", "UiPath Workday Sandbox") and companies' internal, referral and talent-pool boards are left out, since they aren't separate companies.

A spot check of 80 random rows against the live web found every board still live, every website the right company, and every LinkedIn link consistent with the company.

## Duplicates

Companies often have more than one board: one for contractors, one for interns, an old one left behind after switching ATS. We count boards as one company when they share a website, or when they share a LinkedIn page and also have matching names. The company appears once.

Companies that only share a name are left alone, because many different companies have the same name (there are three unrelated companies called Patch on the list). They're listed in `data/review/possible_duplicates.csv` in case you want to check them by hand.

## Files

| File | What it holds |
|---|---|
| `data/output/companies_complete.csv` | The list: complete companies, seven columns |
| `data/output/companies_total.csv` | Every live company, seven columns plus `complete`, `missing_fields`, `http_status`, `checked_at`, `jobs_count`, `endpoint`, `verification_tier` |
| `data/output/companies_incomplete.csv` | Live companies with gaps, plus a `missing_fields` column |
| `data/output/source_manifest.csv` | Every source, with its license, attribution, download date and checksum |
| `reports/quality_report.md` | Counts, field coverage, sources, locations and rejections |
| `data/review/companies_detailed.csv` | Every live company with extra columns: country, open jobs, the company's other boards, and where each value came from, plus evidence columns |
| `data/review/rejected_records.csv` | Everything that was dropped and why |
| `data/review/possible_duplicates.csv` | Companies that share a name with another row |
| `data/review/uncertain_companies.csv` | Boards with unresolved validation (total_found_zero, company_identifier_mismatch, etc.) |
| `data/review/dead_companies.csv` | Boards that are gone (board_not_found, careersite_unavailable) |

`data/output/` and `reports/` are in git. Everything else under `data/` is rebuilt by the pipeline and isn't committed.

## Sources

Board slugs:

| Source | License |
|---|---|
| [latmay/ats-career-page-urls](https://huggingface.co/datasets/latmay/ats-career-page-urls) | CC BY 4.0 |
| [LastRound AI ATS directory](https://github.com/fyrosofttech/lastroundai-hiring-data) | CC BY 4.0 (credit LastRound AI and link their [study](https://lastroundai.com/blog/salary-transparency-study-2026)) |
| [Headcount Labs job postings](https://huggingface.co/datasets/HeadcountLabs/job-postings) | CC BY 4.0 |
| [kalebconfer job-board-directory](https://kalebconfer-sys.github.io/job-board-directory/) | CC0 (declared on the site; the repo has no LICENSE file) |
| [moonie0201/ats-directory](https://github.com/moonie0201/ats-directory) | CC0 |
| [Feashliaa/job-board-aggregator](https://github.com/Feashliaa/job-board-aggregator) | MIT |
| [veresk06/open-ats-feed](https://github.com/veresk06/open-ats-feed) | MIT |
| [Common Crawl](https://commoncrawl.org/terms-of-use/) index, 41 crawls from 2020 to 2026 | Common Crawl terms of use (we only use URL paths) |

Company details:

| Source | License | Used for |
|---|---|---|
| [BigPicture free company dataset (2023 Q4)](https://huggingface.co/datasets/bigpictureio/companies-2023-q4-sm) | ODC-By 1.0 | LinkedIn handle, headquarters country, website lookup by name |

## Why it's 15,000 and not 20,000–30,000

Merging every public dataset gives about 31,800 distinct boards, which is where a 20–30k estimate comes from. But about half of them no longer exist when you ask the vendor: the company moved to another ATS, shut down, or the slug in the dataset was never right. Including them would put companies on the list that don't use these systems.

We tried to find more: Common Crawl back to 2020, a 5.7-million-posting dataset, GitHub lists, and guessing slugs from the domains of US, UK and Canadian companies. Each added a few hundred companies at most, because the sources mostly list the same companies (over 80% of live boards appear in two or more of them). The rest of the gap would need paid company data or brute-force slug guessing against the vendors' APIs.

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
company-dataset all
```

You can also run one stage at a time: `download`, `build`, `validate`, `enrich`, `export`, `report`. A full run from scratch downloads about 4 GB (the Headcount Labs parquet files can be deleted once `boards.csv` has been extracted from them) and makes tens of thousands of polite, rate-limited requests, so it takes a few hours. After that, everything is cached and reruns only fetch what's new or what failed last time.

Useful options:

- `--refresh` re-downloads the sources
- `--max-age-days N` rechecks boards last validated more than N days ago
- `--workers` and `--per-host-delay` control request concurrency and pacing
- `--ats ATS1,ATS2` limits validation to specific ATSes (greenhouse, lever, ashby, smartrecruiters, breezy)
- `--run-dir PATH` writes outputs to a fresh directory (fails if it exists)
- `--smartrecruiters-max-concurrent N` and `--smartrecruiters-delay-seconds S` override rate limits
- `--breezy-max-concurrent N` and `--breezy-delay-seconds S` override rate limits

## Verification tiers

Each live board gets a `verification_tier` in the output:
- **A** — boards with open jobs (no Lever region conflict)
- **B** — Lever boards with jobs > 0 where the candidate's source region (EU/US) differs from the region that answered (region_answered)
- **C** — boards with zero jobs but independent association evidence:
  - Breezy: only when the hosted page confirms the company identity
  - Greenhouse: only when the board-info name matches the candidate/source name via `names_match`; blank if no candidate name
  - Lever/Ashby/SmartRecruiters zero-job: no tier

## Evidence columns

`companies_total.csv` and `data/review/companies_detailed.csv` include:
- `http_status` — the vendor API response code
- `checked_at` — when the board was last validated
- `jobs_count` — number of open jobs at validation time
- `endpoint` — the exact vendor API URL that was queried
- `verification_tier` — the tier assigned to the board

## Review files

Two new review files help audit the validation:
- `data/review/uncertain_companies.csv` — boards with unresolved validation (e.g., total_found_zero, company_identifier_mismatch, exists_no_identity, http_404_unrecognized)
- `data/review/dead_companies.csv` — boards that are gone (board_not_found, careersite_unavailable)

## Requirements

Python 3.11+, `requests` and `duckdb` (used to read the Headcount Labs parquet files).
