# Phase 1b report: precision-safe fixes and validation pilot 3 (2026-11-01)

## Outputs

| Item | Path |
|---|---|
| Pilot 3 | `data/pilots/pilot3/` |
| Run files | `results.csv`, `report.json`, `pilot_report.md`, `comparison.md` (pilots 1–3), `review_sample_v2.csv`, `methodology.json` (args + module sha256), `log.jsonl` |
| Exports | `data/exports/pilot3/` = `data/exports/pilot3_repro/` (SHA256SUMS identical) |
| LinkedIn investigation | `data/pilots/pilot2/linkedin_rejected_108.csv`; labelled fixture `tests/fixtures/linkedin_rejected_pilot2_labelled.csv` |
| Backup taken before the run | `data/store_backups/store_pre_pilot3_2026-11-01.db` |
| Tests | 408 passed (`data/store_reports/tests_before_pilot3.txt`); new regression tests in `tests/test_pilot2_regressions.py` |

## Method

- Fresh sample: seed 20261102, 300 per ATS, excluding all 9,000 boards of pilots 1 and 2.
- Code frozen for the run.
- 28 min. Wikidata: 0 failed batches.

## Same metrics, three pilots

The pilots used different random samples, so part of each difference is sampling noise.

| Metric | Pilot 1 | Pilot 2 | Pilot 3 |
|---|---|---|---|
| Live boards | 3,179 | 3,154 | 3,170 |
| Identity confirmed | 57.5% | 60.4% | 61.5% |
| Identity unresolved | 38.7% | 36.5% | 37.0% |
| Identity mismatch | 3.8% | 2.8% | 1.3% |
| Not a company board | 0 | 7 | 8 |
| Website verified | 57.7% | 57.0% | 55.9% |
| LinkedIn verified | 51.8% | 48.3% | 48.8% |
| Description verified | 45.7% | 45.9% | 44.4% |
| Careersite verified | 96.0% | 96.9% | 97.3% |
| Complete boards | 1,065 | 1,079 | 1,089 |
| Complete US/UK/CA | 566 | 621 | 632 |
| Unique companies (export) | 1,823 | 1,900 | 1,933 |
| Complete companies (export) | 1,063 | 1,075 | 1,075 |
| Projected complete boards in the pool (estimate) | 27,084 | 26,082 | 25,930 (24,223–27,637) |
| Projected US/UK/CA complete boards (estimate) | 14,867 | 14,942 | 15,622 |

## Manual review of pilot 3

### False matches

**60 random complete rows:**
- 2 related-entity websites:
  - Ogilvy Health Canada → ogilvy.com and the parent's LinkedIn page;
  - pladis France → bn-biscuits.com, a brand site, confirmed through board ownership.
- 1 news-item description (IMPOWER).
- 1 name formatting issue ("PosadMaxwan | Generation.E").
- Comparable rates: pilot 1 had 2 entity errors + 2 quality issues; pilot 2 had 0 confirmed + 1 questionable + 2 quality issues.

**Paths changed by Phase 1b (checked for introduced false matches):**
- **Board ownership (30 of 34 sampled):**
  - The vendor names are correct.
  - About 5 websites are not the company's official site: a city's recruiting-campaign site, a different school's site, a parent group, a brand site, and a careers-branded domain.
  - Only 14 ownership-confirmed boards are complete. 13 of those 14 are correct; 1 is wrong (pladis).
- **LinkedIn values accepted only by the new rules (18):** 17 correct, 1 parent page (EER Poland → global).
- **Careers platform used as a website:** 1 (moncler.jibeapply.com), in an incomplete row.

### False rejections

1. **Mismatches: 40, down from 89.** All 40 are now list contradictions only.
   - About 12 of 25 sampled are still false rejections. The causes are noisy list names and entity codes:
     - "Pfizer (Internaljobs)", "Opportunities at Tutera…", "Jobübersicht bei AXA", "Build at Odyssey";
     - entity codes the new rule doesn't strip: "140 Pfizer Inc", "COH City Of Hialeah", "SCUSA Saputo Cheese USA Inc";
     - the accented "Félix", which the tokenizer splits;
     - junk vendor names: "Credit Union", "@one", "one".
   - About 13 are correct: subsidiaries, other facilities, and stale list names after an acquisition.
2. **Unresolved boards with a website (20 sampled):** about 10 look correct but are blocked. Mostly they're Personio boards with no vendor name.
3. **Not-a-company boards (8):** all correct. The "Referral Centre" fix holds.

### False merges

- 1 of 15: KPMG Australia + pinpoint `kpmg`, joined through kpmg.com. Member firms are separate companies.
- Pilot 2: 0 of 6. Pilot 1: 0 of 5.
