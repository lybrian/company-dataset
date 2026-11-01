# Common Crawl discovery pilot (ccx1), 2026-11-01

## Method

### Before the pilot (Phase 1d, then the freeze)

- **Websites from the company's own ATS settings:** trusted only when all of these hold:
  - the company set the website itself in its Ashby or Lever settings;
  - the URL passes the website checks;
  - the page links back to the board;
  - the declared and landed domains match.

  Evidence is recorded as `vendor_declared_website:<field>=<url>`.
- **Four domain rules,** each evaluated on its own (`domain_compatible`):
  - domain written in the name;
  - group word around the name;
  - set-off acronym;
  - leading name words joined.

  None accepted a known false match, and none accepted any of 301,683 random name/domain pairs. They apply only to sites that already link to the board.
- **Bug fix:** country second-level domains (`utec.edu.pe` was read as `edu.pe`).
- **Offline check:** Pilot 3 re-exported, `data/exports/pilot3_frozen` = `pilot3_frozen_repro`. Diff against Phase 1c: 7 websites restored, 0 other changes; complete companies 1,071 → 1,073.
- **Freeze:** `data/methodology_freeze/FROZEN_2026-11-01.json`, with module sha256 and tests (481 passed). The pilot ran with `--require-frozen`, which refuses to run on any code difference.

### The pilot itself

- **Discovery:** CDX index of 6 crawls (2026-39, 2026-21, 2025-51, 2025-26, 2024-42, 2023-40). Hosts of the 10 additional ATS only; URLs only.
  - Provenance per board: first/last capture (crawl, timestamp, URL), crawls seen, captures, any HTTP 200.
  - Files: `data/raw_cc_extra_2026-11-01/commoncrawl_extra/` (`tokens.csv` sha256 cf2b930c…, `harvest_cache.json.gz` with every index block read).
- **Import:** source `commoncrawl_extra`, deduplicated against the whole store (130,453 boards). Backup taken first: `data/store_backups/store_pre_ccextra_2026-11-01.db`.
- **Verification:** random sample of boards that **no other source lists**, 300 per ATS (all 66 Pinpoint, 298 Teamtailor).
  - Every board was checked with its provider.
  - Identity, website, LinkedIn, description and careersite were each verified separately, under the frozen rules.
- **Exports:** `data/exports/ccx1` = `data/exports/ccx1_repro` (byte-identical).

## Funnel

| Stage | Count |
|---|---|
| Discovered boards (6 crawls) | 49,535 |
| Already in the store | 37,122 (75%) |
| **New unique boards** | **12,413** |
| Sampled and checked with the provider | 2,764 |
| Provider-live | 1,583 (57%) |
| Identity confirmed | 753 |
| Unique companies | 746 |
| **Complete (all 7 fields verified)** | **376 companies** |
| Complete and not already known* | 361 |

\*Not already known = the website domain and LinkedIn URL appear neither in the Pilot 1–3 exports nor in the legacy final4 output. Legacy final4 is used only for this overlap flag, not as a source of truth.

## By ATS

| ATS | New boards | Sampled | Live | Identity | Complete new | Rate | Projected complete new (95% CI) | Projected US/UK/CA |
|---|---|---|---|---|---|---|---|---|
| bamboohr | 952 | 300 | 144 | 46 | 36 | 12.0% | 114 (84–154) | 95 |
| icims | 1,983 | 300 | 148 | 44 | 20 | 6.7% | 132 (86–200) | 106 |
| join | 4,136 | 300 | 242 | 156 | 40 | 13.3% | 551 (411–730) | 55 |
| personio | 2,030 | 300 | 154 | 91 | 32 | 10.7% | 217 (155–298) | 0 |
| pinpoint | 66 | 66 | 60 | 46 | 30 | 45.5% | 30 (22–38) | 17 |
| recruitee | 371 | 300 | 125 | 72 | 31 | 10.3% | 38 (27–53) | 5 |
| rippling | 327 | 300 | 217 | 69 | 52 | 17.3% | 57 (44–72) | 50 |
| teamtailor | 298 | 298 | 230 | 176 | 80 | 26.8% | 80 (66–96) | 15 |
| workable | 1,453 | 300 | 117 | 38 | 33 | 11.0% | 160 (115–219)† | 82 |
| workday | 937 | 300 | 146 | 15 | 7 | 2.3% | 22 (11–44) | 12 |
| **Total** | **12,413** | 2,764 | 1,583 | 753 | 361 | | **≈1,400 (1,020–1,900)** | **≈440 (270–750)** |

These are projections, not verified companies.

†138 of the 300 Workable checks were rate-limited, so the rate is a lower bound. Over conclusive checks only, the Workable projection is about 300.

## Geography

**Complete companies by country:**

| US | UK | CA | Other | Unknown |
|---|---|---|---|---|
| 122 | 38 | 3 | 126 | 87 |

- Mostly US/UK/CA: BambooHR, iCIMS, Rippling, Pinpoint and Workable.
- Mostly continental Europe: JOIN, Personio, Recruitee and Teamtailor.

## Age of discoveries

| Last seen | Live | Complete |
|---|---|---|
| 2026 | 73% | 17.9% |
| 2025 | 57% | 10.5% |
| 2024 | 44% | 10.5% |
| 2023 | 34% | 9.1% |

Each added crawl brought 3,500–5,300 more discovered boards, of which about a quarter are new to the store.

**The 35 crawls not harvested** (estimate):
- about 6,000–15,000 more new boards;
- at about 8% complete, about 500–1,200 more complete companies.

## Quality spot check (25 random complete rows)

- 23 correct.
- 1 related entity: MANN+HUMMEL Jackfilter got the parent's website and LinkedIn.
- 1 weak description: The Public Interest Network got a campaign blurb.

This is in line with Pilots 1–3 (about 3–7% of complete rows have a problem).

## Is 40,000 achievable?

**Not with the current platforms and sources.** Estimates of complete unique companies:

| Source | Complete unique companies |
|---|---|
| Existing pool, 130,453 boards (Pilots 1–3) | ≈24,000–26,000 |
| Common Crawl, 10 extra ATS, 6 crawls (this pilot) | +1,000–1,900 |
| Common Crawl, 10 extra ATS, other 35 crawls (rough) | +500–1,200 |
| Workable re-check after rate limits | +100–150 |
| **Total** | **≈26,000–29,000** |

The core 5 ATS were already harvested from all 41 crawls (source `commoncrawl`).

- **The gap:** about 11,000–14,000 complete companies. At an observed 11–14% complete per new board, that needs about 80,000–120,000 genuinely new boards.
- **The only lever of that size:** ATS platforms not yet covered, preferably US/UK-heavy ones. Candidates: JazzHR (applytojob.com), Paylocity, UKG/UltiPro, ADP Workforce Now, Paycom, Jobvite, Taleo, SuccessFactors, Dayforce, iSolved.
- **What each would need:**
  - an identifier parser;
  - a provider verification adapter;
  - a CDX prefix.

  This is new verification code, not new matching rules.
- **Cheap first step:** measure the board counts of those hosts in the CDX index (about 1–2 hours, no provider checks) before building any adapter.
