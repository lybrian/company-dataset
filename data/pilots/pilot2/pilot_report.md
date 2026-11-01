# Enrichment pilot2: measured results

Sample: 4,500 boards, up to 300 per ATS, stratified by prior verification state × first source (seed 20261101, excluding boards of pilot1). Every board was re-checked live.
Wall time 27 min; requests: board_page_fetches 3,154, english_variant_fetches 2,368, gh_content_fetches 110, homepage_fetches 3,214, validation_calls 4,500, vendor_identity_fetches 540, wikidata_queries 180.

## Funnel per ATS (sample counts)

| ATS | pool boards | sampled | live now | identity confirmed | name | website | LinkedIn | description | careersite verified | complete | complete 95% CI | projected complete in pool (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ashby | 6,246 | 300 | 215 | 195 | 195 | 192 | 153 | 174 | 214 | **135** | 39.5%–50.7% | 2,811 (2,465–3,164) |
| bamboohr | 16,304 | 300 | 235 | 86 | 86 | 87 | 78 | 74 | 235 | **65** | 17.4%–26.7% | 3,533 (2,833–4,348) |
| breezy | 6,397 | 300 | 196 | 122 | 122 | 127 | 108 | 110 | 196 | **92** | 25.7%–36.1% | 1,962 (1,645–2,309) |
| greenhouse | 16,495 | 300 | 156 | 100 | 100 | 89 | 75 | 109 | 149 | **65** | 17.4%–26.7% | 3,574 (2,867–4,399) |
| icims | 7,949 | 300 | 127 | 67 | 67 | 47 | 39 | 41 | 127 | **34** | 8.2%–15.4% | 901 (654–1,226) |
| join | 26,065 | 300 | 290 | 259 | 259 | 185 | 129 | 44 | 290 | **35** | 8.5%–15.8% | 3,041 (2,218–4,117) |
| lever | 9,112 | 300 | 95 | 63 | 63 | 64 | 59 | 59 | 75 | **50** | 12.9%–21.3% | 1,519 (1,173–1,941) |
| personio | 3,219 | 300 | 195 | 119 | 119 | 137 | 117 | 76 | 195 | **57** | 15.0%–23.8% | 612 (482–767) |
| pinpoint | 1,234 | 300 | 300 | 229 | 229 | 228 | 198 | 209 | 298 | **177** | 53.4%–64.4% | 728 (658–795) |
| recruitee | 4,172 | 300 | 231 | 145 | 145 | 136 | 118 | 78 | 180 | **62** | 16.5%–25.6% | 862 (687–1,068) |
| rippling | 2,483 | 300 | 256 | 113 | 113 | 105 | 100 | 91 | 255 | **83** | 22.9%–33.0% | 687 (569–819) |
| smartrecruiters | 4,027 | 300 | 159 | 96 | 96 | 96 | 81 | 70 | 156 | **57** | 15.0%–23.8% | 765 (603–959) |
| teamtailor | 4,084 | 300 | 230 | 174 | 174 | 183 | 159 | 83 | 216 | **66** | 17.7%–27.0% | 898 (722–1,104) |
| workable | 12,794 | 300 | 275 | 111 | 111 | 99 | 92 | 211 | 275 | **89** | 24.8%–35.1% | 3,796 (3,170–4,486) |
| workday | 9,872 | 300 | 194 | 27 | 27 | 22 | 17 | 19 | 194 | **12** | 2.3%–6.9% | 395 (227–677) |

**Projected complete boards across all 130,453 candidate boards: ≈26,082** (95% CI 24,323–27,842, stratified estimator). These are boards before cross-ATS deduplication, and an estimate from the sample, not verified records.

## Geography of complete boards (sample)

| ATS | US | UK | CA | other | unknown |
|---|---|---|---|---|---|
| ashby | 87 | 4 | 2 | 22 | 20 |
| bamboohr | 32 | 6 | 9 | 8 | 10 |
| breezy | 50 | 3 | 6 | 16 | 17 |
| greenhouse | 49 | 2 | 0 | 5 | 9 |
| icims | 18 | 0 | 0 | 4 | 12 |
| join | 1 | 0 | 0 | 26 | 8 |
| lever | 38 | 1 | 4 | 2 | 5 |
| personio | 2 | 7 | 0 | 35 | 13 |
| pinpoint | 70 | 36 | 7 | 20 | 44 |
| recruitee | 11 | 4 | 0 | 32 | 15 |
| rippling | 61 | 1 | 5 | 7 | 9 |
| smartrecruiters | 21 | 4 | 1 | 21 | 10 |
| teamtailor | 7 | 9 | 0 | 34 | 16 |
| workable | 47 | 6 | 4 | 19 | 13 |
| workday | 6 | 0 | 0 | 3 | 3 |

Projected complete boards in the US/UK/CA across the pool: ≈14,942. Country comes from BigPicture or Wikidata by verified domain, or from job locations; 'unknown' complete rows are not counted toward US/UK/CA.

## Zero-job boards

| ATS | live with jobs | live, zero jobs | complete with jobs | complete, zero jobs |
|---|---|---|---|---|
| ashby | 188 | 27 | 120 | 15 |
| bamboohr | 147 | 88 | 37 | 28 |
| breezy | 110 | 86 | 55 | 37 |
| greenhouse | 128 | 28 | 58 | 7 |
| icims | 94 | 33 | 29 | 5 |
| join | 139 | 151 | 16 | 19 |
| lever | 72 | 23 | 44 | 6 |
| personio | 172 | 23 | 51 | 6 |
| pinpoint | 226 | 74 | 135 | 42 |
| recruitee | 199 | 32 | 54 | 8 |
| rippling | 196 | 60 | 61 | 22 |
| smartrecruiters | 159 | 0 | 57 | 0 |
| teamtailor | 186 | 44 | 57 | 9 |
| workable | 96 | 179 | 36 | 53 |
| workday | 176 | 18 | 12 | 0 |

## Identity outcomes among live boards (sample)

- ashby: confirmed 195, unresolved 19, not_a_company_board 1
- bamboohr: confirmed 86, mismatch 2, unresolved 147
- breezy: confirmed 122, mismatch 7, unresolved 67
- greenhouse: confirmed 100, mismatch 4, unresolved 49, not_a_company_board 3
- icims: confirmed 67, mismatch 10, unresolved 50
- join: confirmed 259, mismatch 7, unresolved 24
- lever: confirmed 63, mismatch 1, unresolved 31
- personio: confirmed 119, mismatch 5, unresolved 71
- pinpoint: confirmed 229, mismatch 4, unresolved 66, not_a_company_board 1
- recruitee: confirmed 145, mismatch 3, unresolved 83
- rippling: confirmed 113, mismatch 6, unresolved 136, not_a_company_board 1
- smartrecruiters: confirmed 96, mismatch 1, unresolved 61, not_a_company_board 1
- teamtailor: confirmed 174, mismatch 14, unresolved 42
- workable: confirmed 111, mismatch 1, unresolved 163
- workday: confirmed 27, mismatch 24, unresolved 143

## How values were obtained (live boards, sample)

- website: board_link 716, reference_name_slug_domain 433, board_link_home_text 281, ashby_public_website 188, careersite_redirect_domain 87, lever_home_page_link 58, greenhouse_job_ads 16, board_job_ad_link 14, jsonld_organization_url 4
- linkedin: homepage_link+reference_agrees 754, homepage_link 342, bigpicture_by_verified_domain 286, careersite_link+reference_agrees 71, careersite_link 51, wikidata_by_verified_domain 7, bigpicture_and_wikidata_by_domain 7, homepage_only_company_link_numeric 5
- description: homepage_meta 1203, workable_vendor_description 124, homepage_meta_english_page 90, greenhouse_vendor_description 31

## Possible incorrect matches

Automatic cross-checks on all sampled boards: homepage_description_not_english 276, careersite_redirect 74, linkedin_reference_differs 70, reference_name_differs 56, wikidata_label_differs 54.
Consistency checks on the 1075 complete companies: domain_label_unlike_name 47, linkedin_slug_unlike_name_and_domain 1. A flag means the domain or LinkedIn slug doesn't resemble the name (often legitimate, e.g. acronyms or rebrands); `review_sample.csv` lists these plus a random sample for manual review.

## Export from the store (this pilot run)

- candidate boards in run: 4,500
- live boards: 3,154
- identity confirmed live boards: 1,906
- unique companies: 1,900
- complete companies: 1,075
