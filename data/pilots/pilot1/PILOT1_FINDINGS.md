# Pilot 1: findings, manual review, and yield estimate (2026-11-01)

**Inputs:**
- `report.json`, `results.csv` and `pilot_report.md` in this folder
- `data/exports/pilot1` (byte-identical to `data/exports/pilot1_repro`)
- `wikidata_retry.json`

**Method:** unchanged during the run.

**Wikidata stage failed (HTTP 503).** Pilot 1 numbers therefore include no Wikidata evidence. A separate read-only retry is reported separately below.

## Counts in the sample

| Stage | Boards |
|---|---|
| Candidate boards sampled | 4,500 |
| Live boards | 3,179 (2,289 with jobs, 890 with zero jobs) |
| Identity-confirmed live boards | 1,828 |
| Unique companies | 1,823 (5 merges, all checked correct) |
| Complete companies | 1,063 |

## Manual review

**60 random complete rows:**
- 55 fully correct.
- Wrong entity: 2 rows.
  - `smartthings` → website samsung.com (the parent's domain).
  - `beitzelcareers` → Pillar Innovations' website, LinkedIn and description (the parent's).
- Quality issues: 2 rows.
  - `sospro`: a Finnish description passed the English check.
  - `fortus`: the name carries a "(old)" suffix.

**69 flagged complete rows.** Most are legitimate acronyms or rebrands, for example ada.org, btlaw.com and imux.com. Defects found:

| Defect | Rows |
|---|---|
| Parked-domain website and description (`workandtravelguide` → hugedomains.com) | 1 |
| Careers or investor subdomain used as the official website (career.knauf.com, careers.actalentservices.com, investor.lennox.com) | 3 |
| Description is a URL | 2 |
| Description is a news snippet (caimmigrant, filminstitutet, focalpoint) | 3 |
| Parent-company LinkedIn (eyecare-partners.com) | 1 |
| Subsidiary named but parent's site (Etraveli Group → tripstack.com) | 1 |

**25 sampled identity mismatches:**
- About 8 are false rejections caused by name variants: XXL Norge / XXL, deister UK / deister electronic UK, Pearl Abyss Europe / Pearl Abyss, word order, BQ / BQ Redovisning, SEI / SEIC, Ferguson.
- About 17 are correct rejections:
  - a staging board;
  - junk vendor names ("UNAVAILABLE" ×6 in iCIMS, a hosting hostname);
  - legal entities and subsidiaries (DU-HAR MAT AS / NorgesGruppen, Evergreen Roadworks / Heritage);
  - product names (Maincode / Matilda);
  - a franchise (IKEA – Al Homaizi);
  - a rename (Refraction Point / LimaCharlie).

  The junk-name cases should drop the vendor name and re-decide identity, not stay mismatches.

**15 unresolved boards with a verified website:**
- Mostly Rippling and Personio, where every name signal comes from the slug: a list name that echoes the code, plus a website found by slug.
- Correctly not confirmed under the rules. Likely right, but not provable without vendor or page evidence.
- Rippling needs a page or API name source.

**Merges:** 5 of 5 correct (aerovect, emnify, Franke, Goldbelt, ELAN/GTN). No false merges seen; the sample is small.

## Wikidata retry (separate, not part of pilot 1)

- 1,821 verified domains; 394 matched (363 to a single item).
- Would add a country to 63 of the 265 complete rows that have none.
- Would complete only 4 rows that were missing just LinkedIn.

## Yield estimate from existing candidates (estimate, not verified records)

1. **Complete boards in the pool of 130,453:** ≈27,100 (95% CI 25,300–28,900), stratified by ATS.
2. **Boards per company:** in the sample, 76 of 1,065 complete boards have a known second board of the same company. That gives a mean 1/k of 0.963. It's a lower bound on duplication, because only boards with known websites count.
3. **Unique complete companies:** ≈26,000 (range ≈23,500–27,900).
   - Before removing the ≈3–7% wrong-entity or low-quality rows seen in review: realistic **≈24,000–26,000**.
4. **US/UK/CA:** ≈14,900 complete boards with a known country (pilot country only). The Wikidata country would raise this somewhat. Rows with unknown country are not counted.
