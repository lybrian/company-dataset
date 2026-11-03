# company-dataset

A list of companies that hire through **Greenhouse, Lever, Ashby, SmartRecruiters or Breezy HR**, built from public datasets and the vendors' own public job-board APIs.

As of the last export (`data/exports/final_2026-11-03`, not stored in git):

- **19,059 verified companies** with a name, description, ATS and ATS code: `companies_verified.csv`
- **2,702 more** confirmed companies missing one of those: `companies_incomplete.csv`
- **8,815 live boards** with no confirmed identity: `unresolved_boards.csv`
- By ATS: Greenhouse 6,087, SmartRecruiters 4,146, Ashby 4,104, Breezy 2,859, Lever 1,863
- 3,733 verified companies had no open jobs at their last check

Rows were last checked between 1 and 3 November 2026; `qa_report.json` gives the counts, and this export did not run a fresh check of every board. Workable is kept apart in `workable_companies.csv`, which is empty for this export because Workable validation was not finished.

The sections below describe the older `data/output` files where they name them. Those files start with the same required columns: `name`, `description`, `linkedin_url`, `website_url`, `careersite_url`, `ats_system`, `ats_code`. To share the data, send `companies_complete.csv` (or `companies_total.csv`) together with `source_manifest.csv`, which carries the credit some source licenses require.

Every company on the list has a board that answered the vendor's API when we checked it. Nothing is made up. If we couldn't find a value from a real source, the field is empty and the company goes in the incomplete file.

## Where the values come from

- **careersite_url, ats_code**: the board itself, for the exact slug the vendor accepted.
- **name**: the vendor's own record (the Greenhouse board name, the Ashby organization, the Lever page title). We fall back to the source datasets, then BigPicture, then the homepage title. Labels like "Open Roles" or "Acme Careers" don't count as names.
- **website_url**: Ashby publishes each company's website, and Lever boards link to it. For Greenhouse we use the company domain its job links point to, or links in the company's own job ads. If none of those work, we look the company up in BigPicture by name, but only accept a domain that matches the board slug and whose homepage names the company.
- **linkedin_url**: the LinkedIn company page linked from the company's homepage, cross-checked against BigPicture; otherwise BigPicture's record for that domain. It is never built from a name.
- **description**: the description the company gives its own homepage (the meta description), or failing that its Greenhouse board intro. Descriptions may be in any language: a homepage's own meta description is accepted as written, and an English version is used when the site offers one. Recruiting copy ("Join our team…"), cookie banners and placeholders are filtered out, and long text is cut at a sentence boundary.

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
```

The pipeline works over `data/store.db`, in four stages: ingest, identity, enrich, export. Every value it delivers has a row in `field_evidence` saying how it was obtained, and corrections are appended under a new run label rather than rewriting history. An export names the runs it merges.

```bash
# Discovery: each harvest resumes after a stop and writes data/raw/<source>/tokens.csv
python -m company_dataset.sources.wayback_cdx --raw data/raw
python -m company_dataset.sources.commoncrawl_indexer --raw data/raw
python -m company_dataset.sources.slug_prober --raw data/raw --db data/store.db --limit-per-vendor 5000

company-dataset ingest --db data/store.db --raw data/raw --only wayback_cdx_2026_11_03
company-dataset enrich --db data/store.db --raw data/raw --run myrun --out data/runs/myrun --per-ats 100000 --only-undecided
company-dataset repair descriptions-cached --db data/store.db --run mydesc --from-runs myrun
company-dataset repair final-checks --db data/store.db --run myqa --from-runs myrun,mydesc
company-dataset export --db data/store.db --runs myrun,mydesc,myqa --fresh-origin myqa --out data/exports/final_YYYY-MM-DD
```

The export writes `companies_verified.csv`, `companies_incomplete.csv`, `unresolved_boards.csv`, `evidence.csv`, `sources.json`, `qa_report.json` and `SHA256SUMS`. A company is verified when its board is live, its identity is confirmed, and `company_name`, `description`, `ats_system` and `ats_code` are all present. `linkedin_url`, `website_url` and `careersite_url` are filled only where verified. If a quality gate fails, only a report is written, next to the output folder.

The first CSV-based line (`download`, `build`, `validate`, `enrich`, `export`, `report`) is deprecated. It still runs as `company-dataset-legacy`, and the sections below that mention `data/output` describe its files.

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
