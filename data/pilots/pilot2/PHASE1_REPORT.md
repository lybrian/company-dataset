# Phase 1 report: defect fixes and pilot 2 (2026-11-01)

## Outputs

| Item | Path |
|---|---|
| Pilot 2 run | `data/pilots/pilot2/` |
| Run files | `sample.csv`, `results.csv`, `report.json`, `pilot_report.md`, `comparison.md`, `review_sample_v2.csv`, `methodology.json` (args + sha256 of the 13 modules used), `log.jsonl` |
| Exports | `data/exports/pilot2/` and `data/exports/pilot2_repro/`, byte-identical (SHA256SUMS match) |
| Store backup taken before the run | `data/store_backups/store_pre_pilot2_2026-11-01.db` |
| Pilot 1 | `data/pilots/pilot1/`, `data/exports/pilot1/`: unchanged |
| Tests | 352 passed (`data/store_reports/tests_before_pilot2.txt`); regressions in `tests/test_pilot1_regressions.py` |

## Method

- Fresh random sample: seed 20261101, 300 per ATS, same stratification. All 4,500 pilot 1 boards were excluded.
- The code was frozen for the run.
- Wall time 27 min, against 61 min for pilot 1, because the queue now interleaves ATS.
- Wikidata: 180 queries, 0 failed batches. In pilot 1 the stage failed entirely.

## Pilot 1 vs pilot 2 (different random samples, so part of each difference is sampling noise)

| Metric | Pilot 1 | Pilot 2 |
|---|---|---|
| Live boards | 3,179 | 3,154 |
| Identity confirmed | 1,828 (57.5%) | 1,906 (60.4%) |
| Identity unresolved | 1,229 (38.7%) | 1,152 (36.5%) |
| Identity mismatch | 122 (3.8%) | 89 (2.8%) |
| Not a company board (test/old/aux) | 0 | 7 |
| Website verified | 1,834 (57.7%) | 1,797 (57.0%) |
| LinkedIn verified | 1,646 (51.8%) | 1,523 (48.3%) |
| Description verified | 1,454 (45.7%) | 1,448 (45.9%) |
| Careersite verified | 3,053 | 3,055 |
| Complete boards | 1,065 | 1,079 |
| Complete with country US/UK/CA | 566 | 621 |
| Unique companies (export) | 1,823 | 1,900 |
| Complete companies (export) | 1,063 | 1,075 |
| Projected complete boards in the pool (estimate) | 27,084 (25,260–28,907) | 26,082 (24,323–27,842) |

## Manual review of pilot 2 (`review_sample_v2.csv`)

### Incorrect matches

**60 random complete rows:**
- No confirmed wrong-entity rows. Pilot 1 had 2.
- 1 questionable: `bfgroup` → rainbowforest.org, possibly a rename.
- 1 non-English description passed (`callista`, German).
- 1 vendor name with a junk suffix ("VerSprite - LinkedIn").

**All 1,079 complete rows, automated scan:**

| Defect | Rows |
|---|---|
| Parked or for-sale site | 0 |
| URL description | 0 |
| Careers host as website (`silverspin`: the root redirects to careers.silverspin.com) | 1 |
| Junk name suffix | 1 |

### False rejections

1. **Identity mismatches.**
   - 42 of 89 are contradicted only by homepage title segments or a Wikidata label. Many of those segments are taglines ("New and Used Car Dealer", "Exceptional Veterinary Care", "Homepage").
   - In the 25-row sample, about 15 are false rejections. Several have a homepage that links straight to the board, which is strong ownership evidence, but the taglines still created a "conflict".
   - 3 are Workday entity-code prefixes ("B8115 Bob's Discount Furniture", "LE0002 U.S. Urology Partners").
   - About 10 are correct: Hebrew Theological College vs Touro, ALS Customs vs Rhe (1989), TAKRAF USA vs TAKRAF Group, and similar.
2. **Unresolved boards with a website (20 sampled).** About 12 are probably the right company but are blocked:
   - Personio boards with no vendor name and only code-like list names;
   - junk vendor names: "Employer", "en", "Audio intelligence".

   `personio:amazon` → amazon.com was correctly withheld.
3. **Not-a-company boards (7).** 6 correct (sandboxes, internal, "(old)"). 1 false: `paarc-employment`, "Peel Addiction Assessment And Referral Centre", caught by the "referral" rule.
4. **LinkedIn rule cost.** The stricter slug rule rejected candidates on 168 boards; 108 of them got no LinkedIn as a result.
   - Some rejections are legitimate cases lost: beleadingedge / Leading Edge Aviation, cfc-underwriting-ltd / CFC.
   - Some are related entities that should stay rejected: queen-alexandra-college / Queen Alexandra Charity.
   - This is the main reason LinkedIn coverage fell from 51.8% to 48.3%.

### False merges

0 of 6. The merges were adamsmith, eraneos (+ iberia), mintos, nexthink, parte, placemakr. Pilot 1 also had 0 of 5.

## Per-ATS notes (complete boards, pilot 1 → pilot 2)

| ATS | Pilot 1 | Pilot 2 | Note |
|---|---|---|---|
| Rippling | 23 | 83 | Fix: names from embedded page data |
| Workable | 78 | 89 | |
| Breezy | 83 | 92 | |
| iCIMS | 30 | 34 | |
| Greenhouse | 80 | 65 | Stricter homepage rule plus sampling |
| Ashby | 146 | 135 | Stricter homepage rule plus sampling |
| Join | 43 | 35 | Stricter homepage rule plus sampling |
| Workday | 17 | 12 | |
