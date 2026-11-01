# Enrichment pilot 1: measured results

Sample: 45 boards, up to 300 per ATS, stratified by prior verification state × first source (seed 20261031). Every board was re-checked live.
Wall time 4 min; requests: board_page_fetches 31, gh_content_fetches 1, homepage_fetches 34, validation_calls 45, wikidata_queries 1.

## Funnel per ATS (sample counts)

| ATS | pool boards | sampled | live now | identity confirmed | name | website | LinkedIn | description | careersite verified | complete | complete 95% CI | projected complete in pool (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ashby | 6,246 | 3 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | **1** | 6.1%–79.2% | 2,082 (384–4,949) |
| bamboohr | 16,304 | 3 | 2 | 1 | 1 | 2 | 2 | 2 | 2 | **1** | 6.1%–79.2% | 5,435 (1,003–12,918) |
| breezy | 6,397 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | **2** | 20.8%–93.9% | 4,265 (1,328–6,004) |
| greenhouse | 16,495 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | **1** | 6.1%–79.2% | 5,498 (1,014–13,070) |
| icims | 7,949 | 3 | 2 | 1 | 1 | 1 | 1 | 1 | 2 | **1** | 6.1%–79.2% | 2,650 (489–6,298) |
| join | 26,065 | 3 | 3 | 3 | 3 | 3 | 2 | 0 | 3 | **0** | 0.0%–56.2% | 0 (0–14,636) |
| lever | 9,112 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | **1** | 6.1%–79.2% | 3,037 (560–7,220) |
| personio | 3,219 | 3 | 2 | 1 | 1 | 1 | 0 | 0 | 2 | **0** | 0.0%–56.2% | 0 (0–1,807) |
| pinpoint | 1,234 | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | **2** | 20.8%–93.9% | 823 (256–1,158) |
| recruitee | 4,172 | 3 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | **0** | 0.0%–56.2% | 0 (0–2,343) |
| rippling | 2,483 | 3 | 2 | 1 | 1 | 2 | 2 | 2 | 2 | **1** | 6.1%–79.2% | 828 (153–1,967) |
| smartrecruiters | 4,027 | 3 | 2 | 2 | 2 | 1 | 1 | 1 | 2 | **1** | 6.1%–79.2% | 1,342 (248–3,191) |
| teamtailor | 4,084 | 3 | 2 | 2 | 2 | 2 | 1 | 1 | 2 | **1** | 6.1%–79.2% | 1,361 (251–3,236) |
| workable | 12,794 | 3 | 3 | 2 | 2 | 1 | 1 | 1 | 3 | **1** | 6.1%–79.2% | 4,265 (787–10,137) |
| workday | 9,872 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | **0** | 0.0%–56.2% | 0 (0–5,543) |

**Projected complete boards across all 130,453 candidate boards: ≈31,585** (sum of per-ATS 95% bounds 6,473–94,477). These are boards, before cross-ATS deduplication, and are an estimate from the sample, not verified records.

## Geography of complete boards (sample)

| ATS | US | UK | CA | other | unknown |
|---|---|---|---|---|---|
| ashby | 0 | 1 | 0 | 0 | 0 |
| bamboohr | 0 | 0 | 1 | 0 | 0 |
| breezy | 1 | 1 | 0 | 0 | 0 |
| greenhouse | 1 | 0 | 0 | 0 | 0 |
| icims | 1 | 0 | 0 | 0 | 0 |
| join | 0 | 0 | 0 | 0 | 0 |
| lever | 1 | 0 | 0 | 0 | 0 |
| personio | 0 | 0 | 0 | 0 | 0 |
| pinpoint | 1 | 0 | 0 | 0 | 1 |
| recruitee | 0 | 0 | 0 | 0 | 0 |
| rippling | 1 | 0 | 0 | 0 | 0 |
| smartrecruiters | 0 | 0 | 0 | 1 | 0 |
| teamtailor | 0 | 0 | 0 | 1 | 0 |
| workable | 1 | 0 | 0 | 0 | 0 |
| workday | 0 | 0 | 0 | 0 | 0 |

Projected complete boards in the US/UK/CA across the pool: ≈28,470. Country comes from BigPicture or Wikidata by verified domain, or from job locations; 'unknown' complete rows are not counted toward US/UK/CA.

## Zero-job boards

| ATS | live with jobs | live, zero jobs | complete with jobs | complete, zero jobs |
|---|---|---|---|---|
| ashby | 2 | 0 | 1 | 0 |
| bamboohr | 1 | 1 | 1 | 0 |
| breezy | 1 | 1 | 1 | 1 |
| greenhouse | 1 | 0 | 1 | 0 |
| icims | 2 | 0 | 1 | 0 |
| join | 1 | 2 | 0 | 0 |
| lever | 1 | 0 | 1 | 0 |
| personio | 2 | 0 | 0 | 0 |
| pinpoint | 3 | 0 | 2 | 0 |
| recruitee | 2 | 0 | 0 | 0 |
| rippling | 2 | 0 | 1 | 0 |
| smartrecruiters | 2 | 0 | 1 | 0 |
| teamtailor | 2 | 0 | 1 | 0 |
| workable | 2 | 1 | 1 | 0 |
| workday | 2 | 0 | 0 | 0 |

## Identity outcomes among live boards (sample)

- ashby: confirmed 2
- bamboohr: confirmed 1, unresolved 1
- breezy: confirmed 2
- greenhouse: confirmed 1
- icims: confirmed 1, unresolved 1
- join: confirmed 3
- lever: confirmed 1
- personio: confirmed 1, mismatch 1
- pinpoint: confirmed 3
- recruitee: confirmed 2
- rippling: confirmed 1, unresolved 1
- smartrecruiters: confirmed 2
- teamtailor: confirmed 2
- workable: confirmed 2, unresolved 1
- workday: unresolved 2

## How values were obtained (live boards, sample)

- website: reference_name_slug_domain 8, board_link 6, board_link_home_text 4, ashby_public_website 2, lever_home_page_link 1
- linkedin: homepage_link+reference_agrees 10, homepage_link+slug_matches_name_or_domain 4, bigpicture_by_verified_domain 3, bigpicture_and_wikidata_by_domain 1
- description: homepage_meta 15

## Possible incorrect matches

Automatic cross-checks on all sampled boards: homepage_description_not_english 5, linkedin_reference_differs 1.
Consistency checks on the 13 complete companies: domain_label_unlike_name 1. A flag means the domain or LinkedIn slug doesn't resemble the name (often legitimate, e.g. acronyms or rebrands); `review_sample.csv` lists these plus a random sample for manual review.

## Export from the store (this pilot run)

- candidate boards in run: 45
- live boards: 31
- identity confirmed live boards: 24
- unique companies: 24
- complete companies: 13
