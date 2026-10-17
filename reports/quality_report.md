# Data quality report

_Generated 2026-10-17T21:31:14Z_

## The short version

`companies.csv` has **8,456 companies**, each with all seven required fields filled in. Another 6,632 live companies are missing at least one field; they are in `companies_incomplete.csv` with the gaps named. That makes 15,088 live companies in total, one row per company.

That is 11,544 short of the 20,000 we were aiming for. The section on coverage below explains why we couldn't find more.

| | Count |
|---|---|
| Board slugs collected from all sources | 31,843 |
| Still live when checked against the vendor's API | 16,084 |
| Gone (404 from the vendor) | 15,759 |
| API answers but the public careers page is gone | 534 |
| Vendor demo, sandbox or test boards ("Lever Demo 2", "Merge API Integration Sandbox") | 57 |
| A company's secondary board: internal, referrals, talent pool | 84 |
| Extra boards folded into a company already listed | 321 |
| **Live companies** | **15,088** |
| **Complete companies (`companies.csv`)** | **8,456** |

## How complete the live list is

| Field | Filled | Of | |
|---|---|---|---|
| `name` | 14,861 | 15,088 | 98.5% |
| `description` | 11,063 | 15,088 | 73.32% |
| `linkedin_url` | 9,429 | 15,088 | 62.49% |
| `website_url` | 10,726 | 15,088 | 71.09% |
| `careersite_url` | 15,088 | 15,088 | 100.0% |
| `ats_system` | 15,088 | 15,088 | 100.0% |
| `ats_code` | 15,088 | 15,088 | 100.0% |

Among the incomplete rows, the missing fields are `linkedin_url` (5,659), `website_url` (4,362), `description` (4,025), `name` (227). LinkedIn is the hardest: if a company's homepage doesn't link to its LinkedIn page and it isn't in the reference data, we leave it blank rather than guess.

By ATS:

| ATS | Live | Complete |
|---|---|---|
| Greenhouse | 8,329 | 3,579 |
| Lever | 2,357 | 1,644 |
| Ashby | 4,402 | 3,233 |

## Duplicates

A company often has more than one board: a second board for contractors or interns, an old board left behind after a move from Lever to Ashby, and so on. We treat boards as the same company when they share a website, or when they share a LinkedIn page *and* have matching names. Each company appears once; its other boards are listed in `other_boards` in `review/companies_detailed.csv`, and in `review/rejected_records.csv` as `duplicate_company_board`.

- Boards folded into another company's row: 321
- Companies that share a name with another row but couldn't be confirmed as the same company: 582 (288 of them in `companies.csv`). These are left separate and listed in `review/possible_duplicates.csv` for a person to check. Names alone aren't enough to merge on; there are a lot of companies called Atlas.

Job postings themselves aren't part of this dataset, so the same job appearing on two boards doesn't produce two rows.

## Where the values come from

- **Name:** vendor 8,422, reference 13, homepage 12, lastroundai 9
- **Website:** ashby public website 3,207, reference name match homepage verified 1,580, lever home page link 1,532, greenhouse job ads homepage verified 1,245, greenhouse job url origin 757, greenhouse job ads slug match 83, greenhouse job url origin parent 39, lever home page link parent 9, ashby public website parent 4
- **LinkedIn:** homepage and reference 4,402, homepage link 2,293, reference domain match 1,699, homepage link numeric id 62
- **Description:** homepage meta 8,259, greenhouse board intro 197
- **Country:** reference hq 6,068, none 1,379, ashby postings unanimous 832, lever postings unanimous 177

`review/companies_detailed.csv` has the same information per row in its `*_source` columns, so any single value can be traced back.

## Location

- In `companies.csv`: 5,392 US, 426 UK, 267 Canada (72.0% of rows), 992 elsewhere, 1,379 unknown.
- Across all live companies: 6,686 US, 483 UK, 316 Canada (49.6% of rows), 1,205 elsewhere, 6,398 unknown.

Country means headquarters country from BigPicture, matched on the company's website. If that's missing we use the country of the company's job postings, but only when every posting on the board is in the same country.

## Sources

| Source | Used for | License | Live boards it lists | Only source for |
|---|---|---|---|---|
| latmay | board slugs | CC-BY-4.0 | 13,286 | 653 |
| lastroundai | board slugs | CC-BY-4.0 | 8,901 | 466 |
| kaleb | board slugs | CC0-1.0 | 6,046 | 10 |
| moonie | board slugs | CC0-1.0 | 1,061 | 7 |
| feashliaa | board slugs | MIT | 9,268 | 1 |
| commoncrawl | board slugs | Common Crawl Terms of Use | 11,382 | 51 |
| headcountlabs | board slugs | CC-BY-4.0 | 10,351 | 481 |
| openatsfeed | board slugs | MIT | 11,491 | 115 |
| bigpicture | company details | ODC-By-1.0 | - | - |

## Why there aren't 20,000

The sources overlap heavily. 88.4% of live boards turn up in two or more of them, and each new source we added contributed only a few hundred boards nobody else had. Things we tried beyond the original sources:

- Common Crawl's index for the Greenhouse, Lever and Ashby board hosts, across 41 crawls from 2020 to 2026. (We also tried the vendors' API hosts; they added nothing.)
- The Headcount Labs postings dataset (5.7 million postings), including Greenhouse boards that only appear as postings on a company's own site, which we resolved by reading the board embedded in those pages.
- MIT-licensed board lists on GitHub (open-ats-feed and smaller ones).
- Guessing slugs from company domains for a random sample of US, UK and Canadian companies. About 1.7% of large companies had a board, and most of those were already on our list.

So the number of companies with public boards on these three ATSes that can be found in open data is about 15,000, not 20,000 to 30,000. Getting closer would take either paid company data or mass slug-guessing against the vendors' APIs.

## Rejected rows

| Reason | Rows |
|---|---|
| `validation_failed` | 15,759 |
| `careersite_unavailable` | 534 |
| `duplicate_company_board` | 321 |
| `auxiliary_board` | 84 |
| `test_or_demo_board` | 57 |

We also removed 8 LinkedIn links that pointed at another company's page, and 73 descriptions that were template text shared by three or more companies.
