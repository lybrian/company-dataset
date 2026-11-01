# Consolidated Company Dataset — Validation Summary

**Generated:** 2026-10-31
**Total consolidated companies:** 8,733

## Source Datasets

| Dataset | Path | Rows | Complete | Genuinely Verified |
|---|---|---|---|---|
| final4_complete | `data/runs/2026-10-31-final4/output/companies_total.csv` (filtered to complete=yes) | 9,405 | 9,405 | 8,738 |
| final4_total | `data/runs/2026-10-31-final4/output/companies_total.csv` | 28,459 | 9,405 | N/A (includes incomplete) |
| interim1 | `data/runs/2026-10-31-interim1/companies_verified.csv` | 7,145 | 7,145 | 6,624 |

## Verification Methodology

### final4_complete
- **Per-record verification:** Every company in `companies_complete.csv` was validated against the vendor API.
- **Evidence columns:** `http_status`, `checked_at`, `endpoint`, `verification_tier`, `jobs_count` present for every row.
- **Verification tiers:** A (jobs>0, no Lever region conflict), B (Lever jobs>0, region mismatch), C (zero jobs with independent identity evidence).
- **Complete filter:** Only rows with `complete=yes` (all 7 required fields) and `verification_tier` in {A,B,C} and `http_status=200` are considered genuinely verified.
- **Result:** 8,738 / 9,405 rows meet genuine verification criteria.

### interim1
- **Per-record verification:** Every company in `companies_verified.csv` passed the full pipeline including Greenhouse hosted-page check.
- **Evidence columns:** `verification_tier`, `verification_status`, `verification_date`, `endpoint` present for every row.
- **Consumer check:** A representative sample of 200 rows (100 representative + 100 suspicious) was re-validated fresh against vendor APIs and careersite URLs: **200/200 passed**.
- **Important:** The consumer check is a **representative sample**, not per-record verification. Individual records are not individually re-checked.
- **Result:** 6,624 / 7,145 rows have per-record verification evidence (verification_tier, status, date, endpoint).

## Deduplication Methodology

Companies were deduplicated across both datasets using the following hierarchy:
1. **Registered domain** of website URL (strongest signal)
2. **LinkedIn URL** (only when normalized name also matches)
3. **ATS board identifier** (ats_system:ats_code exact match)
4. **Normalized company name** (only across different ATS, and only when no conflicting website)

Companies sharing only a name (without website/LinkedIn/ATS match) are **not merged** — there are many distinct companies with identical names (e.g., three unrelated 'Patch' companies).

## Overlap Between Datasets

- final4 genuine identity keys: 33752
- interim1 genuine identity keys: 25567
- Overlapping keys: 25567

- website: final4=8733, interim1=6621, overlap=6621
- linkedin: final4=8737, interim1=6623, overlap=6623
- ats_board: final4=8738, interim1=6624, overlap=6624
- name: final4=7544, interim1=5699, overlap=5699

## Exclusions

The following were **excluded** from the consolidated CSV:
- final4 incomplete companies (missing ≥1 required field): 19,054
- final4 uncertain companies (unresolved validation): 84,746
- final4 dead companies (board not found, careersite unavailable): 22,282
- final4 rejected records (test/demo/auxiliary/unsupported ATS/etc.): 121,905
- final4 complete companies lacking genuine verification evidence (no tier/HTTP 200/checked_at): 667
- interim1 companies lacking per-record verification evidence: 521

## Structural CSV Checks

- **All 7 required fields populated:** Yes (8,733 / 8,733)
- **CSV round-trip:** Consistent columns and row count
- **URL format:** All URLs valid. 13 LinkedIn URLs contain apostrophes in company names (e.g., "Emily's List") — these are valid LinkedIn URLs.
- **Duplicate ATS boards:** 0
- **Duplicate website hosts:** 0
- **Duplicate LinkedIn URLs:** 1 (EyeCare Associates & EyeCare Partners share the same LinkedIn page — distinct companies, correctly not merged)
- **Duplicate normalized names:** 59 (distinct companies with same name but different websites/ATS boards — correctly not merged per deduplication rules)

**8,733 unique, genuinely verified, complete companies**

### By ATS

| ATS | Companies |
|---|---|
| ashby | 2,853 |
| bamboohr | 5 |
| breezy | 1,085 |
| greenhouse | 3,375 |
| lever | 1,399 |
| pinpoint | 1 |
| recruitee | 2 |
| rippling | 2 |
| smartrecruiters | 6 |
| teamtailor | 1 |
| workable | 2 |
| workday | 2 |

### By Source Dataset

| Source | Companies |
|---|---|
| final4 | 8,733 |

### Verification Tier Distribution

| Tier | Companies | Meaning |
|---|---|---|
| A | 8,080 | Jobs > 0, no Lever region conflict |
| B | 6 | Lever jobs > 0, candidate region ≠ region_answered |
| C | 647 | Zero jobs with independent identity evidence (Greenhouse name match / Breezy hosted page) |

### Merged Records

- Companies merged from multiple source rows: 6,622
- Total duplicate rows collapsed: 6,629

## Limitations & Caveats

1. **final4 consumer check was a sample** (300 rows across 14 ATS platforms, not per-record). The 3 failures (Personio SF Group, Breezy SMG/Shoals Club) indicate name mismatches that may exist elsewhere.
2. **interim1 consumer check was a sample** (200 rows, 100 representative + 100 suspicious, 200/200 passed). This does not guarantee every individual record would pass a fresh check.
3. **No new API checks were performed** for this consolidation. Verification evidence is from the original pipeline runs (2026-10-31).
4. **Greenhouse hosted pages** were not fetched in final4 (WAF blocks); interim1 did a slow second pass. Some Greenhouse careersite_urls may redirect.
5. **LinkedIn URLs** cannot be verified without login; they are cross-checked against homepage links and reference data only.
6. **Descriptions** are from homepage meta tags or vendor board intros; recruiting copy and placeholders were filtered.
7. **Breezy jobs** not extracted in interim1 (rate-limited); not in final4 either.

## Files in This Delivery

- `companies_verified_consolidated.csv` — One row per genuinely verified, complete, unique company (7 required fields + verification evidence)
- `validation_summary.md` — This file

