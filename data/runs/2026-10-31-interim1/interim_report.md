# Interim submission — fully verified, complete companies

**Accepted: 7,145 unique companies**, every one with all seven required fields populated from verified sources (`companies_verified.csv`).

Only records that passed every check below are included. Records still being validated, uncertain, or missing any field are excluded and will be handled in the second submission.

## By ATS

| ATS | Companies |
|---|---|
| ashby | 3,094 |
| greenhouse | 1,791 |
| lever | 1,547 |
| breezy | 693 |
| smartrecruiters | 6 |
| bamboohr | 4 |
| workable | 4 |
| rippling | 2 |
| recruitee | 2 |
| pinpoint | 1 |
| teamtailor | 1 |

## Verification (all on 2026-10-31)

1. **ATS code → correct company:** the code was requested fresh from the provider endpoint after export; the response had the provider's expected structure; and there was positive identity evidence — the provider's stated company name matches the row (Greenhouse, SmartRecruiters, Breezy, Workable, BambooHR, Recruitee, Teamtailor) or the live careersite page names the company (Lever, Ashby, others).
2. **Careersite URL opens and belongs to the company:** fetched fresh; it landed on the same board (or the company's own verified website). Greenhouse hosted pages were fetched directly in a slow second pass. Redirects to another ATS board or to a vendor homepage were rejected.
3. **Website:** fetched fresh; kept only when the homepage identifies the company, or the ATS vendor publishes it and it loads.
4. **LinkedIn:** kept only when the verified homepage links to it or the reference record matches the verified website's domain (LinkedIn itself can't be opened without login). Never constructed.
5. **Description:** only from the verified homepage's meta description or the ATS vendor; HTML stripped.
6. **Not test/demo/sandbox/internal**, and **deduplicated** across all sources and ATS platforms (shared website, shared LinkedIn with matching name, or identical specific name on different ATS).

Selection funnel from the QA'd rows: QA-passed rows with all seven fields 7,468, no positive identity evidence (excluded) 111, careersite not on board or company site (excluded) 195, website not homepage-verified (excluded) 1, selected 7,161; Greenhouse direct page check: greenhouse_hosted_page_http_405_elsewhere 1, greenhouse_hosted_page_error_elsewhere 4, greenhouse_hosted_page_http_403_elsewhere 2, greenhouse_hosted_page_http_404_elsewhere 7, greenhouse_hosted_page_http_307_elsewhere 1, greenhouse_hosted_page_ok_elsewhere 1.

## Final QA on the exported CSV

- CSV re-read after writing: consistent columns and row count: True
- Field problems (missing required field, malformed URL, non-company LinkedIn URL, formula prefix, encoding artifact, embedded newline, HTML): 0 
- Duplicates: ATS boards 0, website hosts 0, LinkedIn URLs 2, normalized names 61
- **Consumer test** on this file: 200 rows (20 per ATS where available + suspicious rows), provider API URL and careersite URL built from `ats_system` + `ats_code` only, requested fresh: **200/200 passed**.

## Job list (`jobs.csv`)

149,956 open jobs for 5,875 companies, taken from the providers' public job APIs on 2026-10-31 (company, ATS, code, job title, job URL, location). By ATS: ashby 50,213, greenhouse 63,174, lever 36,000, bamboohr 32, smartrecruiters 374, pinpoint 7, rippling 13, recruitee 10, teamtailor 94, workable 39.
Not yet extracted: Breezy HR jobs (its API is rate-limited and still in use by the running validation) — to be added in the second submission.

## Industry classification (`industry_classification.csv`)

- Static / rule-based: **5,145** — BigPicture company dataset `industry`, joined on the company's verified website domain, assigned only when the reference has exactly one industry for that domain.
- LLM classification: **0** — no LLM classification has been run (not started, per instructions).
- Unclassified: 1,303 (no reference match) + 697 (reference lists conflicting industries) — left blank rather than guessed.
- The method is recorded per company in `classification_method` and `classification_basis`.

## Not in this submission

- Records still being validated (running until ~21:30–22:00), uncertain records, and verified-but-incomplete records (missing a verified website, LinkedIn or description).
