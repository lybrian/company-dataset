# Enrichment pilot3: measured results

Sample: 4,500 boards, up to 300 per ATS, stratified by prior verification state × first source (seed 20261102, excluding boards of pilot1, pilot2). Every board was re-checked live.
Wall time 28 min; requests: board_page_fetches 3,170, english_variant_fetches 2,416, gh_content_fetches 111, homepage_fetches 3,254, validation_calls 4,500, vendor_identity_fetches 554, wikidata_queries 176.

## Funnel per ATS (sample counts)

| ATS | pool boards | sampled | live now | identity confirmed | name | website | LinkedIn | description | careersite verified | complete | complete 95% CI | projected complete in pool (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ashby | 6,246 | 300 | 215 | 185 | 185 | 181 | 156 | 168 | 213 | **145** | 42.7%–54.0% | 3,019 (2,669–3,371) |
| bamboohr | 16,304 | 300 | 238 | 82 | 82 | 84 | 79 | 74 | 238 | **68** | 18.3%–27.7% | 3,696 (2,982–4,522) |
| breezy | 6,397 | 300 | 196 | 139 | 139 | 135 | 127 | 103 | 196 | **97** | 27.3%–37.8% | 2,068 (1,746–2,419) |
| greenhouse | 16,495 | 300 | 156 | 107 | 107 | 94 | 84 | 111 | 150 | **77** | 21.1%–30.9% | 4,234 (3,473–5,096) |
| icims | 7,949 | 300 | 142 | 86 | 86 | 68 | 53 | 52 | 142 | **37** | 9.1%–16.5% | 980 (722–1,315) |
| join | 26,065 | 300 | 288 | 254 | 254 | 170 | 117 | 31 | 288 | **24** | 5.4%–11.6% | 2,085 (1,417–3,031) |
| lever | 9,112 | 300 | 95 | 66 | 66 | 64 | 54 | 56 | 78 | **43** | 10.8%–18.8% | 1,306 (986–1,709) |
| personio | 3,219 | 300 | 195 | 112 | 112 | 134 | 124 | 75 | 194 | **61** | 16.2%–25.2% | 655 (520–813) |
| pinpoint | 1,234 | 300 | 299 | 231 | 231 | 224 | 205 | 198 | 296 | **178** | 53.7%–64.7% | 732 (663–799) |
| recruitee | 4,172 | 300 | 225 | 145 | 145 | 127 | 111 | 62 | 196 | **51** | 13.2%–21.7% | 709 (550–904) |
| rippling | 2,483 | 300 | 267 | 110 | 110 | 87 | 77 | 76 | 261 | **65** | 17.4%–26.7% | 538 (432–662) |
| smartrecruiters | 4,027 | 300 | 156 | 100 | 100 | 97 | 88 | 74 | 151 | **66** | 17.7%–27.0% | 886 (712–1,088) |
| teamtailor | 4,084 | 300 | 230 | 186 | 186 | 182 | 163 | 94 | 214 | **82** | 22.6%–32.6% | 1,116 (923–1,333) |
| workable | 12,794 | 300 | 272 | 118 | 118 | 98 | 89 | 212 | 272 | **80** | 22.0%–31.9% | 3,412 (2,812–4,087) |
| workday | 9,872 | 300 | 196 | 28 | 28 | 26 | 20 | 22 | 196 | **15** | 3.1%–8.1% | 494 (301–798) |

**Projected complete boards across all 130,453 candidate boards: ≈25,930** (95% CI 24,223–27,637, stratified estimator). These are boards before cross-ATS deduplication, and an estimate from the sample, not verified records.

## Geography of complete boards (sample)

| ATS | US | UK | CA | other | unknown |
|---|---|---|---|---|---|
| ashby | 90 | 12 | 3 | 16 | 24 |
| bamboohr | 38 | 7 | 6 | 11 | 6 |
| breezy | 50 | 10 | 4 | 10 | 23 |
| greenhouse | 59 | 6 | 2 | 6 | 4 |
| icims | 20 | 2 | 2 | 3 | 10 |
| join | 0 | 1 | 0 | 17 | 6 |
| lever | 27 | 1 | 2 | 10 | 3 |
| personio | 0 | 1 | 0 | 46 | 14 |
| pinpoint | 65 | 49 | 7 | 19 | 38 |
| recruitee | 8 | 4 | 1 | 29 | 9 |
| rippling | 48 | 1 | 2 | 3 | 11 |
| smartrecruiters | 26 | 4 | 2 | 22 | 12 |
| teamtailor | 7 | 11 | 0 | 34 | 30 |
| workable | 29 | 14 | 0 | 22 | 15 |
| workday | 11 | 0 | 0 | 1 | 3 |

Projected complete boards in the US/UK/CA across the pool: ≈15,622. Country comes from BigPicture or Wikidata by verified domain, or from job locations; 'unknown' complete rows are not counted toward US/UK/CA.

## Zero-job boards

| ATS | live with jobs | live, zero jobs | complete with jobs | complete, zero jobs |
|---|---|---|---|---|
| ashby | 187 | 28 | 128 | 17 |
| bamboohr | 145 | 93 | 40 | 28 |
| breezy | 110 | 86 | 58 | 39 |
| greenhouse | 129 | 27 | 68 | 9 |
| icims | 102 | 40 | 31 | 6 |
| join | 137 | 151 | 7 | 17 |
| lever | 72 | 23 | 37 | 6 |
| personio | 172 | 23 | 55 | 6 |
| pinpoint | 225 | 74 | 136 | 42 |
| recruitee | 197 | 28 | 45 | 6 |
| rippling | 202 | 65 | 55 | 10 |
| smartrecruiters | 156 | 0 | 66 | 0 |
| teamtailor | 187 | 43 | 68 | 14 |
| workable | 85 | 187 | 25 | 55 |
| workday | 175 | 21 | 14 | 1 |

## Identity outcomes among live boards (sample)

- ashby: confirmed 185, unresolved 30
- bamboohr: confirmed 82, mismatch 1, unresolved 155
- breezy: confirmed 139, unresolved 57
- greenhouse: confirmed 107, unresolved 47, not_a_company_board 2
- icims: confirmed 86, mismatch 6, unresolved 50
- join: confirmed 254, mismatch 3, unresolved 31
- lever: confirmed 66, unresolved 29
- personio: confirmed 112, unresolved 83
- pinpoint: confirmed 231, mismatch 1, unresolved 63, not_a_company_board 4
- recruitee: confirmed 145, unresolved 79, not_a_company_board 1
- rippling: confirmed 110, mismatch 4, unresolved 152, not_a_company_board 1
- smartrecruiters: confirmed 100, unresolved 56
- teamtailor: confirmed 186, mismatch 1, unresolved 43
- workable: confirmed 118, unresolved 154
- workday: confirmed 28, mismatch 24, unresolved 144

## How values were obtained (live boards, sample)

- website: board_link 732, reference_name_slug_domain 392, board_link_home_text 260, ashby_public_website 178, careersite_redirect_domain 122, lever_home_page_link 55, greenhouse_job_ads 13, jsonld_organization_url 10, board_job_ad_link 9
- linkedin: homepage_link+reference_agrees 751, homepage_link 347, bigpicture_by_verified_domain 282, careersite_link+reference_agrees 74, careersite_link 71, homepage_only_company_link_numeric 11, bigpicture_and_wikidata_by_domain 7, wikidata_by_verified_domain 4
- description: homepage_meta 1163, workable_vendor_description 128, homepage_meta_english_page 86, greenhouse_vendor_description 31

## Possible incorrect matches

Automatic cross-checks on all sampled boards: homepage_description_not_english 291, linkedin_reference_differs 76, careersite_redirect 61, wikidata_label_differs 60, reference_name_differs 46, root_redirects_to_careers_host 2.
Consistency checks on the 1075 complete companies: domain_label_unlike_name 48, linkedin_slug_unlike_name_and_domain 7. A flag means the domain or LinkedIn slug doesn't resemble the name (often legitimate, e.g. acronyms or rebrands); `review_sample.csv` lists these plus a random sample for manual review.

## Export from the store (this pilot run)

- candidate boards in run: 4,500
- live boards: 3,170
- identity confirmed live boards: 1,949
- unique companies: 1,933
- complete companies: 1,075
