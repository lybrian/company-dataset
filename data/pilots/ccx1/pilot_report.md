# Enrichment ccx1: measured results

Sample: 2,764 boards, up to 300 per ATS, stratified by prior verification state × first source (seed 20261103). Every board was re-checked live.
Wall time 19 min; requests: board_page_fetches 1,583, english_variant_fetches 1,540, homepage_fetches 1,539, validation_calls 2,764, vendor_identity_fetches 360, wikidata_queries 76.

## Funnel per ATS (sample counts)

| ATS | pool boards | sampled | live now | identity confirmed | name | website | LinkedIn | description | careersite verified | complete | complete 95% CI | projected complete in pool (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bamboohr | 17,256 | 300 | 144 | 46 | 46 | 47 | 46 | 38 | 144 | **36** | 8.8%–16.2% | 2,071 (1,518–2,790) |
| icims | 9,932 | 300 | 148 | 44 | 44 | 44 | 38 | 30 | 148 | **27** | 6.3%–12.8% | 894 (622–1,269) |
| join | 30,201 | 300 | 242 | 156 | 156 | 160 | 126 | 50 | 242 | **40** | 9.9%–17.6% | 4,027 (3,004–5,330) |
| personio | 5,121 | 300 | 154 | 91 | 91 | 96 | 80 | 43 | 152 | **32** | 7.7%–14.7% | 546 (392–751) |
| pinpoint | 1,300 | 66 | 60 | 46 | 46 | 46 | 42 | 39 | 56 | **34** | 39.7%–63.2% | 670 (516–821) |
| recruitee | 4,543 | 300 | 125 | 72 | 72 | 71 | 59 | 41 | 77 | **31** | 7.4%–14.3% | 469 (335–649) |
| rippling | 2,810 | 300 | 217 | 69 | 69 | 69 | 64 | 55 | 217 | **52** | 13.5%–22.0% | 487 (379–619) |
| teamtailor | 4,382 | 298 | 230 | 176 | 176 | 173 | 160 | 100 | 184 | **83** | 23.1%–33.2% | 1,220 (1,011–1,455) |
| workable | 14,247 | 300 | 117 | 38 | 38 | 38 | 37 | 93 | 115 | **37** | 9.1%–16.5% | 1,757 (1,294–2,356) |
| workday | 10,797 | 300 | 146 | 15 | 15 | 15 | 13 | 11 | 146 | **9** | 1.6%–5.6% | 324 (171–605) |

**Projected complete boards across all 142,866 candidate boards: ≈12,465** (95% CI 10,951–13,980, stratified estimator). These are boards before cross-ATS deduplication, and an estimate from the sample, not verified records.

## Geography of complete boards (sample)

| ATS | US | UK | CA | other | unknown |
|---|---|---|---|---|---|
| bamboohr | 23 | 4 | 3 | 2 | 4 |
| icims | 18 | 2 | 0 | 0 | 7 |
| join | 1 | 3 | 0 | 27 | 9 |
| personio | 0 | 0 | 0 | 25 | 7 |
| pinpoint | 16 | 3 | 0 | 2 | 13 |
| recruitee | 4 | 0 | 0 | 19 | 8 |
| rippling | 42 | 4 | 0 | 1 | 5 |
| teamtailor | 1 | 14 | 0 | 40 | 28 |
| workable | 14 | 7 | 0 | 10 | 6 |
| workday | 5 | 1 | 0 | 1 | 2 |

Projected complete boards in the US/UK/CA across the pool: ≈5,090. Country comes from BigPicture or Wikidata by verified domain, or from job locations; 'unknown' complete rows are not counted toward US/UK/CA.

## Zero-job boards

| ATS | live with jobs | live, zero jobs | complete with jobs | complete, zero jobs |
|---|---|---|---|---|
| bamboohr | 102 | 42 | 23 | 13 |
| icims | 63 | 85 | 14 | 13 |
| join | 30 | 212 | 6 | 34 |
| personio | 130 | 24 | 28 | 4 |
| pinpoint | 18 | 42 | 9 | 25 |
| recruitee | 101 | 24 | 28 | 3 |
| rippling | 140 | 77 | 35 | 17 |
| teamtailor | 193 | 37 | 70 | 13 |
| workable | 23 | 94 | 7 | 30 |
| workday | 117 | 29 | 9 | 0 |

## Identity outcomes among live boards (sample)

- bamboohr: confirmed 46, unresolved 98
- icims: confirmed 44, unresolved 104
- join: confirmed 156, unresolved 86
- personio: confirmed 91, unresolved 63
- pinpoint: confirmed 46, unresolved 14
- recruitee: confirmed 72, unresolved 53
- rippling: confirmed 69, unresolved 148
- teamtailor: confirmed 176, unresolved 49, not_a_company_board 5
- workable: confirmed 38, unresolved 79
- workday: confirmed 15, unresolved 131

## How values were obtained (live boards, sample)

- website: board_link 268, reference_name_slug_domain 182, board_link_home_text 167, careersite_redirect_domain 125, board_job_ad_link 13, jsonld_organization_url 4
- linkedin: homepage_link+reference_agrees 315, homepage_link 145, bigpicture_by_verified_domain 119, careersite_link+reference_agrees 44, careersite_link 35, homepage_only_company_link_numeric 4, bigpicture_and_wikidata_by_domain 2, wikidata_by_verified_domain 1
- description: homepage_meta 372, homepage_meta_english_page 68, workable_vendor_description 60

## Possible incorrect matches

Automatic cross-checks on all sampled boards: homepage_description_not_english 197, careersite_redirect 96, linkedin_reference_differs 39, reference_name_differs 32, wikidata_label_differs 25, root_redirects_to_careers_host 1.
Consistency checks on the 376 complete companies: domain_label_unlike_name 20, linkedin_slug_unlike_name_and_domain 1. A flag means the domain or LinkedIn slug doesn't resemble the name (often legitimate, e.g. acronyms or rebrands); `review_sample.csv` lists these plus a random sample for manual review.

## Export from the store (this pilot run)

- candidate boards in run: 2,764
- live boards: 1,583
- identity confirmed live boards: 753
- unique companies: 746
- complete companies: 376
