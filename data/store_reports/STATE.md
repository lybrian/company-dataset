# Phase 1–2 state (2026-10-31 23:25 +0545)

Approved: storage, import, gates, export/dedup fixes, regression tests, pilot. NOT approved: deletions, full-scale runs, commits.

## Done
- Scratch archived + verified: `~/company-dataset-scratch-archive-2026-10-31` (351/351 sha256 OK, `MANIFEST.sha256`).
- Draft runs archived + verified: `~/company-dataset-archives/draft-runs-2026-10-31.tar.gz` (130/130). Deletion list: `~/company-dataset-archives/CLEANUP_PROPOSAL.md` (awaiting approval).
- `data/raw_2026-10-31/`: the raw dir the store was imported from (feashliaa/kalil/joa copied; others symlinked to data/raw).
- `data/store.db` (SQLite, WAL, FKs, append-only verifications): imported via `data/store_reports/run_import.sh` → import_1.json; re-run import_2.json added 0 rows (idempotent).
  295,590 source rows = 295,590 stored; 130,453 boards (= legacy candidate set exactly); 6,173 cache entries without a source row, all `invalid` (malformed Workday codes / codes no longer listed).
- Backup before pilot: `data/store_backups/store_pre_pilot1_2026-10-31.db`.
- New modules: store.py, store_import.py, verification.py, identity.py, careersite.py, wikidata.py, pilot.py, pilot_report.py, store_export.py; validate_extra.vendor_identity (Workday/iCIMS).
- Legacy export fixes: untiered zero-job rows → identity_not_established; collapse_companies → strong key + name match (no name-only merges, no shared-domain-different-name merges).
- Tests: 291 pass.

## Running
- pilot1: `python -m company_dataset.pilot --db data/store.db --raw data/raw_2026-10-31 --run pilot1 --out data/pilots/pilot1 --per-ats 300 --seed 20261031 --workers 24`
  (log: data/pilots/pilot1/log.jsonl). Started 17:33Z.

## After pilot1 finishes
1. `python -c "from pathlib import Path; from company_dataset import store, pilot; c=store.connect('data/store.db'); print(pilot.backfill_identities(c,'pilot1',Path('data/pilots/pilot1/results.csv')))"`
   (pilot1 started before the identities table existed).
2. `python -m company_dataset.store_export --db data/store.db --run pilot1 --out data/exports/pilot1` and again to `data/exports/pilot1_repro`; compare SHA256SUMS.
3. `python -m company_dataset.pilot_report --db data/store.db --pilot data/pilots/pilot1 --export data/exports/pilot1`
4. Manual review of `data/pilots/pilot1/review_sample.csv`; report to user.

## 2026-11-01: pilot1 finished
- 61 min. Wikidata stage failed (503); a separate retry is in data/pilots/pilot1/wikidata_retry.json.
- Identities backfilled (4,500). Exports data/exports/pilot1 and pilot1_repro are byte-identical (SHA256SUMS).
- Findings: data/pilots/pilot1/PILOT1_FINDINGS.md. Review sample: review_sample.csv.
- Next, awaiting approval: defect fixes and pilot2 (fresh seed); full run on the existing pool; CC CDX discovery pilot.

## 2026-11-01: Phase 1 (defect fixes + pilot2)
- Fixes: strict homepage self-naming (brand segments + names_compatible), provisional identity picks the homepage,
  parked domains, careers/investor/app hosts → main site, careersite-redirect domain as a board-attested candidate,
  strict LinkedIn slug rule, junk vendor names, "(old)" boards, test boards gated in the pilot, URL/news/domain-sale
  descriptions, Finnish false-English, Rippling __NEXT_DATA__ names and links, Wikidata batches of 10.
- Tests: 352 pass (tests/test_pilot1_regressions.py).
- Backup: data/store_backups/store_pre_pilot2_2026-11-01.db
- Running: pilot2 (seed 20261101, --exclude-run pilot1), out data/pilots/pilot2, methodology.json written.
- After: backfill not needed (identities written live); exports pilot2 and pilot2_repro; pilot_report; pilot_compare; manual review.
- Phase 2 (Common Crawl) awaits approval after the Phase 1 report.

## 2026-11-01: Phase 1b (precision-safe fixes + pilot3)
- Fixes:
  - homepage segments and Wikidata labels can support a match but never contradict one;
  - board ownership (two-way link, page linking ≤3 boards) corroborates the vendor name;
  - Workday entity codes are stripped, with the raw value kept and both spellings compared;
  - more junk names, plus the "- LinkedIn" suffix and QID labels;
  - the referral rule is narrowed;
  - a root that redirects to its careers host is kept as the website, with no careers-page description;
  - LinkedIn: affix-stripped handle equality, name-only acronyms, accent/%-folding, and a vendor/template blocklist.
- Fixture: tests/fixtures/linkedin_rejected_pilot2_labelled.csv (manual labels). Tests: 408 pass.
- Backup: data/store_backups/store_pre_pilot3_2026-11-01.db
- Running: pilot3 (seed 20261102, excluding pilot1+pilot2), out data/pilots/pilot3.
- After: exports pilot3 and pilot3_repro (checksums); pilot_report; pilot_compare --runs p1 p2 p3; manual review; report; STOP (Common Crawl needs approval).

## 2026-11-01: Phase 1c (two precision fixes, offline re-export only)
- Fixes:
  - geo-qualified names don't merge on a shared domain or LinkedIn (identity.geo_qualifiers / cluster_companies);
  - board-link websites must name the company by domain or page (pilot.website_supported, identity.domain_compatible);
  - careers-branded domains and careers platforms are not websites.
- store_export re-checks stored websites with the current rules: drop-only, no fetches; new file website_rule_changes.csv.
- Tests: 458 pass (tests/test_pilot3_regressions.py). The store was not modified (sha256 unchanged).
- Exports: data/exports/pilot3_phase1c = pilot3_phase1c_repro. Diff in data/exports/pilot3_phase1c_diff/: 38 changed, 0 unexplained.
- Report: data/pilots/pilot3/PHASE1C_REPORT.md. Common Crawl awaits approval.

## 2026-11-01: Phase 1d + freeze + Common Crawl discovery pilot (ccx1)
- Phase 1d:
  - vendor-declared Ashby/Lever websites;
  - four evaluated domain rules;
  - country second-level domains.
- Re-export pilot3_frozen = pilot3_frozen_repro: complete companies 1,071 → 1,073, 7 websites restored, 0 other changes.
- Frozen: data/methodology_freeze/FROZEN_2026-11-01.json (481 tests). Later runs use --require-frozen.
- Common Crawl harvest:
  - 6 crawls, 10 extra ATS: 49,535 boards → 12,413 new;
  - imported as source commoncrawl_extra;
  - backup data/store_backups/store_pre_ccextra_2026-11-01.db.
- Pilot ccx1:
  - 2,764 new boards: 1,583 live, 753 identity, 376 complete companies;
  - exports ccx1 = ccx1_repro.
- Report: data/pilots/ccx1/DISCOVERY_PILOT_REPORT.md; numbers in discovery_report.json.
- Pending approval:
  - full run;
  - the remaining 35 crawls;
  - CDX sizing of new ATS platforms.
