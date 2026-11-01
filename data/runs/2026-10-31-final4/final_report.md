# Final report: verified companies on 15 ATS platforms

Run directory: `/Users/danuzz/company-dataset/data/runs/2026-10-31-final4`. Every number below is computed from the files in this directory and the validation cache it was exported from.

## Headline

- **Verified unique companies (companies_total.csv): 28,459**
- With at least one open job: 22,285; zero open jobs (board live, no postings today): 6,174
- All seven required fields filled (companies_complete.csv): 9,405 (33.0%)
- Raw discovery pool: 136,508 unique candidates across 15 platforms
- Target was 40,000. **Not reached: short by 11,541.** See Limitations.

## Reconciliation by ATS

Candidates = valid + invalid (dead) + unresolved (uncertain) + not validated. Accepted = valid minus post-validation rejects (test/demo, internal/auxiliary, hosted page gone, duplicate of another kept board).

| ATS | Discovered | Valid | Dead | Uncertain | Not validated (deadline) | Test/demo | Internal | Page gone | No identity | Duplicate | Accepted | With jobs | Zero jobs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Greenhouse | 16,495 | 8,571 | 7,920 | 0 | 4 | 40 | 83 | 0 | 203 | 265 | 7,980 | 6,606 | 1,374 |
| Lever | 9,112 | 2,902 | 6,208 | 0 | 2 | 10 | 0 | 472 | 15 | 88 | 2,317 | 1,981 | 336 |
| Ashby | 6,246 | 4,457 | 1,785 | 0 | 4 | 7 | 0 | 43 | 7 | 70 | 4,330 | 3,812 | 518 |
| SmartRecruiters | 4,027 | 1,568 | 0 | 828 | 1,631 | 2 | 1 | 0 | 28 | 29 | 1,508 | 1,508 | 0 |
| Breezy HR | 6,397 | 3,977 | 1,764 | 421 | 235 | 2 | 0 | 1 | 41 | 158 | 3,775 | 2,140 | 1,635 |
| Workable | 12,794 | 712 | 70 | 0 | 12,012 | 0 | 0 | 0 | 9 | 31 | 672 | 264 | 408 |
| Workday | 15,927 | 311 | 1,830 | 29 | 13,757 | 0 | 0 | 0 | 124 | 2 | 185 | 178 | 7 |
| BambooHR | 16,304 | 1,699 | 395 | 57 | 14,153 | 2 | 0 | 0 | 2 | 99 | 1,596 | 1,095 | 501 |
| Recruitee | 4,172 | 1,067 | 349 | 2 | 2,754 | 1 | 1 | 0 | 123 | 14 | 928 | 887 | 41 |
| Teamtailor | 4,084 | 1,066 | 347 | 5 | 2,666 | 11 | 0 | 0 | 11 | 11 | 1,033 | 839 | 194 |
| Personio | 3,219 | 923 | 496 | 0 | 1,800 | 0 | 0 | 0 | 23 | 11 | 889 | 765 | 124 |
| Rippling | 2,483 | 1,273 | 145 | 0 | 1,065 | 0 | 0 | 0 | 439 | 48 | 786 | 595 | 191 |
| iCIMS | 7,949 | 940 | 440 | 38 | 6,531 | 0 | 0 | 0 | 236 | 6 | 698 | 638 | 60 |
| Pinpoint | 1,234 | 1,233 | 1 | 0 | 0 | 3 | 0 | 0 | 835 | 12 | 383 | 316 | 67 |
| JOIN | 26,065 | 1,400 | 16 | 3 | 24,646 | 0 | 0 | 0 | 7 | 14 | 1,379 | 661 | 718 |
| **Total** | 136,508 | 32,099 | 21,766 | 1,383 | 81,260 | 78 | 85 | 516 | 2,103 | 858 | 28,459 | 22,285 | 6,174 |

Note: valid - rejects can exceed accepted slightly because a duplicate is counted against the ATS of the board that was dropped.

## How each board was verified

Every accepted row has `http_status` 200 and a `checked_at` timestamp from a live request made on 2026-10-31 to the vendor endpoint in `endpoint`. A board counts as dead only when the vendor's own not-found answer came back for every candidate code; 403/429/5xx/timeouts are uncertain, never dead.

| ATS | Endpoint | Not-found signal | Company identity evidence |
|---|---|---|---|
| Workable | `apply.workable.com/api/v1/widget/accounts/{code}` | 404 | Workable returns the account's company name and description |
| BambooHR | `{code}.bamboohr.com/careers/list` (+ `/careers/company-info`) | redirect off the company subdomain | BambooHR returns the company name |
| Workday | POST `{tenant}.{wdN}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` | 422/404 | **None from Workday**; identity = tenant + site path from the source URL |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{code}/postings` | 404; `totalFound=0` is uncertain | `company.identifier` must equal the code |
| Breezy HR | `{code}.breezy.hr/json` (+ hosted page when empty) | 404 with 'Career portal not found' | `company.friendly_id` must equal the code; empty boards need the hosted page to name the company |

Tiers: A = open jobs today; C = zero jobs but the vendor names a company that matches the source's name (or Breezy hosted-page identity); blank = live board, zero jobs, no independent name evidence.

| ATS | A | C | blank |
|---|---|---|---|
| Greenhouse | 6,606 | 636 | 738 |
| Lever | 1,974 | 0 | 336 |
| Ashby | 3,812 | 0 | 518 |
| SmartRecruiters | 1,508 | 0 | 0 |
| Breezy HR | 2,140 | 1,635 | 0 |
| Workable | 264 | 155 | 253 |
| Workday | 178 | 0 | 7 |
| BambooHR | 1,095 | 192 | 309 |
| Recruitee | 887 | 0 | 41 |
| Teamtailor | 839 | 50 | 144 |
| Personio | 765 | 69 | 55 |
| Rippling | 595 | 0 | 191 |
| iCIMS | 638 | 1 | 59 |
| Pinpoint | 316 | 0 | 67 |
| JOIN | 661 | 698 | 20 |

## Check dates

| ATS | Earliest checked_at | Latest checked_at |
|---|---|---|
| Greenhouse | 2026-10-31T13:39:58Z | 2026-10-31T14:09:40Z |
| Lever | 2026-10-31T14:09:40Z | 2026-10-31T14:17:16Z |
| Ashby | 2026-10-31T13:30:47Z | 2026-10-31T13:39:58Z |
| SmartRecruiters | 2026-10-31T07:35:18Z | 2026-10-31T14:25:24Z |
| Breezy HR | 2026-10-31T07:36:51Z | 2026-10-31T14:25:31Z |
| Workable | 2026-10-31T14:05:34Z | 2026-10-31T14:23:10Z |
| Workday | 2026-10-31T14:06:28Z | 2026-10-31T14:11:40Z |
| BambooHR | 2026-10-31T13:55:50Z | 2026-10-31T14:27:22Z |
| Recruitee | 2026-10-31T14:02:45Z | 2026-10-31T14:19:57Z |
| Teamtailor | 2026-10-31T14:04:40Z | 2026-10-31T14:19:57Z |
| Personio | 2026-10-31T14:00:19Z | 2026-10-31T14:19:58Z |
| Rippling | 2026-10-31T14:03:28Z | 2026-10-31T14:19:57Z |
| iCIMS | 2026-10-31T13:57:26Z | 2026-10-31T14:19:57Z |
| Pinpoint | 2026-10-31T14:01:31Z | 2026-10-31T14:18:20Z |
| JOIN | 2026-10-31T13:58:33Z | 2026-10-31T14:19:57Z |

## Validation runs


## Consumer-style check

300 rows sampled with a fixed seed; each request built only from `ats_system` + `ats_code`, sent fresh (655 requests).

| ATS | Checked | HTTP 200 | Vendor name available | Matches row name | Differs |
|---|---|---|---|---|---|
| Greenhouse | 32 | 32 | 32 | 32 | 0 |
| Lever | 18 | 18 | 0 | 0 | 0 |
| Ashby | 19 | 19 | 0 | 0 | 0 |
| SmartRecruiters | 55 | 55 | 55 | 55 | 0 |
| Breezy HR | 63 | 63 | 63 | 61 | 2 |
| Workable | 10 | 10 | 10 | 10 | 0 |
| Workday | 10 | 10 | 0 | 0 | 0 |
| BambooHR | 11 | 11 | 11 | 11 | 0 |
| Recruitee | 12 | 12 | 12 | 12 | 0 |
| Teamtailor | 10 | 10 | 10 | 10 | 0 |
| Personio | 11 | 11 | 9 | 8 | 1 |
| Rippling | 13 | 13 | 0 | 0 | 0 |
| iCIMS | 11 | 11 | 0 | 0 | 0 |
| Pinpoint | 11 | 11 | 0 | 0 | 0 |
| JOIN | 14 | 14 | 14 | 14 | 0 |

Failures and name differences (3), every one listed:

- personio:sfgroup status=200 row_name='SF Group' vendor_name='SF Group'
- breezy:smg status=200 row_name='SMG Security' vendor_name='Zeus Fire and Security'
- breezy:shoals-club status=200 row_name='Bald Head Island Club' vendor_name='Shoals Club'

## Field completeness

| ATS | rows | name | description | linkedin_url | website_url | careersite_url | ats_system | ats_code | all seven |
|---|---|---|---|---|---|---|---|---|---|
| Greenhouse | 7,980 | 100.0% | 64.7% | 48.6% | 53.0% | 100.0% | 100.0% | 100.0% | 43.8% |
| Lever | 2,317 | 100.0% | 75.1% | 83.9% | 92.0% | 100.0% | 100.0% | 100.0% | 69.9% |
| Ashby | 4,330 | 100.0% | 86.5% | 81.4% | 98.1% | 100.0% | 100.0% | 100.0% | 73.4% |
| SmartRecruiters | 1,508 | 100.0% | 0.4% | 0.5% | 0.5% | 100.0% | 100.0% | 100.0% | 0.4% |
| Breezy HR | 3,775 | 100.0% | 29.7% | 35.6% | 36.8% | 100.0% | 100.0% | 100.0% | 28.8% |
| Workable | 672 | 100.0% | 73.1% | 0.6% | 0.6% | 100.0% | 100.0% | 100.0% | 0.6% |
| Workday | 185 | 100.0% | 1.1% | 1.1% | 1.1% | 100.0% | 100.0% | 100.0% | 1.1% |
| BambooHR | 1,596 | 100.0% | 0.3% | 0.3% | 0.3% | 100.0% | 100.0% | 100.0% | 0.3% |
| Recruitee | 928 | 100.0% | 0.2% | 0.2% | 0.2% | 100.0% | 100.0% | 100.0% | 0.2% |
| Teamtailor | 1,033 | 100.0% | 0.1% | 0.3% | 0.3% | 100.0% | 100.0% | 100.0% | 0.1% |
| Personio | 889 | 100.0% | 0.1% | 0.0% | 0.1% | 100.0% | 100.0% | 100.0% | 0.0% |
| Rippling | 786 | 100.0% | 0.4% | 0.3% | 0.4% | 100.0% | 100.0% | 100.0% | 0.3% |
| iCIMS | 698 | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Pinpoint | 383 | 100.0% | 0.3% | 0.3% | 0.3% | 100.0% | 100.0% | 100.0% | 0.3% |
| JOIN | 1,379 | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| All | 28,459 | 100.0% | 43.2% | 37.7% | 42.3% | 100.0% | 100.0% | 100.0% | 33.0% |

Website provenance: ashby_public_website 4,219, reference_name_match_homepage_verified 3,180, lever_home_page_link 1,989, greenhouse_job_ads_homepage_verified 1,491, greenhouse_job_url_origin 927, greenhouse_job_ads_slug_match 159, greenhouse_job_url_origin_parent 49, lever_home_page_link_parent 11, ashby_public_website_parent 6. Values are only taken from vendor data, the BigPicture reference join, or a homepage that confirms the name; nothing is guessed, and blanks stay blank.

## Country / region (where known)

9,827 of 28,459 rows have a country. Top: US 7,425, GB 548, CA 386, DE 253, AU 145, FR 126, NL 88, CH 62, IN 49, BR 43, SG 39, BE 32.

## Per-source yield

| Source | Candidates contributed (5 ATS) | In accepted rows | License |
|---|---|---|---|
| latmay | 55,860 | 16,783 | CC-BY-4.0 |
| lastroundai | 895 | 8,503 | CC-BY-4.0 |
| kaleb | 3,306 | 6,935 | CC0-1.0 |
| moonie | 196 | 1,083 | CC0-1.0 |
| feashliaa | 26,256 | 10,325 | MIT |
| commoncrawl | 5,644 | 15,270 | Common Crawl Terms of Use |
| headcountlabs | 521 | 9,979 | CC-BY-4.0 |
| openatsfeed | 9,315 | 15,912 | MIT |
| kalil | 34,133 | 17,747 | MIT |
| joa | 382 | 3,378 | CC-BY-4.0 |

## Limitations

- **Deadline:** this delivery was exported mid-validation to meet the deadline. 81,260 candidates were never validated; they are listed in `review/uncertain_companies.csv` with reason `not_validated` and are not counted.
- **Workday identity:** Workday's public endpoint returns no company name, so a Workday row proves the tenant/site board exists, not which legal entity owns it. Names come from the source lists.
- **Zero-job boards:** many live Workable/BambooHR accounts have no open postings today (tier C or blank). Filter on `verification_tier` = A for currently-hiring companies.
- **Enrichment:** homepage fetching for website/LinkedIn was not run for newly added boards in this delivery (time). Their website/LinkedIn fields are filled only where reference data already confirmed them; completeness is reported as is.
- **Cross-platform dedupe:** boards merge on a shared website, a shared LinkedIn page with matching names, or an identical specific company name (>= 6 normalized characters) on different ATS without conflicting websites. Same-name rows that were not merged are in `review/possible_duplicates.csv`.
- **Recheck:** SmartRecruiters/Breezy boards verified earlier today were re-requested in the same deadline-bounded run after new candidates; boards not reached keep their earlier same-day check, visible in `checked_at`.
- **Platforms with no vendor company name** (Lever, Ashby, Rippling, Pinpoint, Workday): a row is kept only when a source names the company; boards without any name are in uncertain_companies.csv as identity_not_established.
- Paycom and JazzHR were discovered but not added (no reliable not-found signal).
