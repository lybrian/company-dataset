# Enrichment pilot 1: measured results

Sample: 4,500 boards, up to 300 per ATS, stratified by prior verification state × first source (seed 20261031). Every board was re-checked live.
Wall time 61 min; requests: board_page_fetches 3,179, english_variant_fetches 2,528, gh_content_fetches 100, homepage_fetches 3,259, validation_calls 4,500, vendor_identity_fetches 538.

## Funnel per ATS (sample counts)

| ATS | pool boards | sampled | live now | identity confirmed | name | website | LinkedIn | description | careersite verified | complete | complete 95% CI | projected complete in pool (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ashby | 6,246 | 300 | 215 | 191 | 191 | 194 | 160 | 178 | 213 | **146** | 43.1%–54.3% | 3,040 (2,690–3,392) |
| bamboohr | 16,304 | 300 | 237 | 84 | 84 | 89 | 82 | 72 | 237 | **63** | 16.8%–26.0% | 3,424 (2,735–4,233) |
| breezy | 6,397 | 300 | 196 | 115 | 115 | 120 | 112 | 94 | 196 | **83** | 22.9%–33.0% | 1,770 (1,466–2,110) |
| greenhouse | 16,495 | 300 | 156 | 115 | 115 | 106 | 94 | 111 | 148 | **80** | 22.0%–31.9% | 4,399 (3,626–5,269) |
| icims | 7,949 | 300 | 135 | 68 | 68 | 73 | 62 | 47 | 135 | **30** | 7.1%–13.9% | 795 (564–1,106) |
| join | 26,065 | 300 | 283 | 264 | 264 | 170 | 138 | 46 | 283 | **43** | 10.8%–18.8% | 3,736 (2,820–4,887) |
| lever | 9,112 | 300 | 95 | 69 | 69 | 70 | 67 | 63 | 83 | **56** | 14.7%–23.5% | 1,701 (1,336–2,138) |
| personio | 3,219 | 300 | 195 | 103 | 103 | 139 | 128 | 76 | 194 | **54** | 14.1%–22.7% | 579 (453–732) |
| pinpoint | 1,234 | 300 | 300 | 239 | 239 | 233 | 218 | 205 | 297 | **187** | 56.7%–67.6% | 769 (700–835) |
| recruitee | 4,172 | 300 | 237 | 134 | 134 | 140 | 127 | 78 | 180 | **60** | 15.9%–24.9% | 834 (662–1,039) |
| rippling | 2,483 | 300 | 272 | 37 | 37 | 82 | 80 | 76 | 265 | **23** | 5.2%–11.2% | 190 (128–279) |
| smartrecruiters | 4,027 | 300 | 155 | 106 | 106 | 106 | 95 | 81 | 147 | **70** | 18.9%–28.4% | 940 (761–1,145) |
| teamtailor | 4,084 | 300 | 230 | 166 | 166 | 173 | 160 | 87 | 203 | **75** | 20.4%–30.2% | 1,021 (835–1,233) |
| workable | 12,794 | 300 | 274 | 99 | 99 | 95 | 89 | 208 | 273 | **78** | 21.4%–31.2% | 3,326 (2,733–3,997) |
| workday | 9,872 | 300 | 199 | 38 | 38 | 44 | 34 | 32 | 199 | **17** | 3.6%–8.9% | 559 (352–877) |

**Projected complete boards across all 130,453 candidate boards: ≈27,084** (95% CI 25,260–28,907, stratified estimator). These are boards before cross-ATS deduplication, and an estimate from the sample, not verified records.

## Geography of complete boards (sample)

| ATS | US | UK | CA | other | unknown |
|---|---|---|---|---|---|
| ashby | 92 | 6 | 7 | 15 | 26 |
| bamboohr | 41 | 4 | 4 | 6 | 8 |
| breezy | 41 | 7 | 5 | 11 | 19 |
| greenhouse | 55 | 3 | 2 | 4 | 16 |
| icims | 15 | 1 | 0 | 1 | 13 |
| join | 0 | 0 | 0 | 27 | 16 |
| lever | 31 | 1 | 8 | 9 | 7 |
| personio | 2 | 6 | 0 | 38 | 8 |
| pinpoint | 54 | 40 | 6 | 16 | 71 |
| recruitee | 10 | 2 | 0 | 31 | 17 |
| rippling | 15 | 1 | 2 | 2 | 3 |
| smartrecruiters | 20 | 4 | 3 | 20 | 23 |
| teamtailor | 2 | 12 | 2 | 35 | 24 |
| workable | 42 | 8 | 3 | 18 | 7 |
| workday | 7 | 1 | 1 | 1 | 7 |

Projected complete boards in the US/UK/CA across the pool: ≈14,867. Country comes from BigPicture or Wikidata by verified domain, or from job locations; 'unknown' complete rows are not counted toward US/UK/CA.

## Zero-job boards

| ATS | live with jobs | live, zero jobs | complete with jobs | complete, zero jobs |
|---|---|---|---|---|
| ashby | 188 | 27 | 134 | 12 |
| bamboohr | 155 | 82 | 44 | 19 |
| breezy | 110 | 86 | 43 | 40 |
| greenhouse | 128 | 28 | 71 | 9 |
| icims | 95 | 40 | 25 | 5 |
| join | 131 | 152 | 22 | 21 |
| lever | 72 | 23 | 45 | 11 |
| personio | 172 | 23 | 47 | 7 |
| pinpoint | 226 | 74 | 147 | 40 |
| recruitee | 194 | 43 | 53 | 7 |
| rippling | 213 | 59 | 19 | 4 |
| smartrecruiters | 155 | 0 | 70 | 0 |
| teamtailor | 187 | 43 | 58 | 17 |
| workable | 89 | 185 | 35 | 43 |
| workday | 174 | 25 | 17 | 0 |

## Identity outcomes among live boards (sample)

- ashby: confirmed 191, mismatch 3, unresolved 21
- bamboohr: confirmed 84, mismatch 7, unresolved 146
- breezy: confirmed 115, mismatch 5, unresolved 76
- greenhouse: confirmed 115, mismatch 3, unresolved 38
- icims: confirmed 68, mismatch 25, unresolved 42
- join: confirmed 264, unresolved 19
- lever: confirmed 69, mismatch 2, unresolved 24
- personio: confirmed 103, mismatch 13, unresolved 79
- pinpoint: confirmed 239, mismatch 3, unresolved 58
- recruitee: confirmed 134, mismatch 11, unresolved 92
- rippling: confirmed 37, mismatch 1, unresolved 234
- smartrecruiters: confirmed 106, mismatch 2, unresolved 47
- teamtailor: confirmed 166, mismatch 16, unresolved 48
- workable: confirmed 99, mismatch 3, unresolved 172
- workday: confirmed 38, mismatch 28, unresolved 133

## How values were obtained (live boards, sample)

- website: board_link 815, reference_name_slug_domain 437, board_link_home_text 274, ashby_public_website 192, lever_home_page_link 63, greenhouse_job_url_origin 26, greenhouse_job_ads 16, jsonld_organization_url 11
- linkedin: homepage_link+reference_agrees 799, homepage_link+slug_matches_name_or_domain 381, bigpicture_by_verified_domain 275, careersite_link+reference_agrees 84, careersite_link+slug_matches_name_or_domain 63, homepage_only_company_link_numeric 44
- description: homepage_meta 1197, workable_vendor_description 131, homepage_meta_english_page 108, greenhouse_vendor_description 18

## Possible incorrect matches

Automatic cross-checks on all sampled boards: homepage_description_not_english 255, careersite_redirect 105, linkedin_reference_differs 104, reference_name_differs 65.
Consistency checks on the 1063 complete companies: domain_label_unlike_name 58, linkedin_slug_unlike_name_and_domain 11. A flag means the domain or LinkedIn slug doesn't resemble the name (often legitimate, e.g. acronyms or rebrands); `review_sample.csv` lists these plus a random sample for manual review.

## Export from the store (this pilot run)

- candidate boards in run: 4,500
- live boards: 3,179
- identity confirmed live boards: 1,828
- unique companies: 1,823
- complete companies: 1,063
