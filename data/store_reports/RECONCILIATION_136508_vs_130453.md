# Reconciliation: 136,508 legacy candidates vs 130,453 store boards

- The legacy number came from `work3/intermediate/candidates.csv` (archived at `~/company-dataset-scratch-archive-2026-10-31/work3`). That build ran **before** the Feashliaa adapter started rejecting malformed Workday rows.
- The store holds 130,453 boards, built from the same 10 source files.
  - Every store board is among the 136,508.
  - 6,055 legacy candidates are not store boards. **All 6,055 are Workday, and all come from Feashliaa alone.** The list is in `reconcile_missing_6055.csv`.

## What they are

**Invalid identifiers.** The Feashliaa row's tenant field contains the Workday instance (`wd1`, `wd5`, `wd3`, `wd12`, …) instead of the company tenant. The old build therefore produced codes like `wd1.wd1/160over90us`, which address no real board.

## Not lost

- Each of the 6,055 is stored as a `source_rows` row with `reject_reason = invalid_slug` and the raw `tenant|wd|site` value in `reject_detail`.
  - Mapping: 6,055 rejected rows map one-to-one to the 6,055 missing candidates (0 duplicates, 0 unmatched).
- Source rows reconcile: 295,590 read = 295,590 stored (275,679 accepted + 19,911 rejected).

## Evidence they were never valid boards

The legacy validation caches had checked 5,892 of them:

| Legacy status | Count |
|---|---|
| invalid (provider 404/422) | 5,891 |
| unresolved | 1 |
| never checked | 163 |

None was valid.

## Coverage (corrected 2026-11-01)

My first version said 5,737 of these were "covered through correct codes". That overstated the evidence.

- What the store shows: 5,737 of the 6,055 site names also occur under a real tenant.
  - Those site names match **7,149** correct-tenant boards.
  - **433** of the site names appear under more than one tenant (e.g. `9dot_careers` under `9dot` and `emspmg`).
- A matching site name therefore does not show which board a malformed row meant, and it is not treated as proof of anything.
- The 7,149 correct-tenant boards stand only on their own evidence (`reconcile_correct_tenant_boards.csv`):

  | Latest own outcome | Boards |
  |---|---|
  | verified_live | 416 |
  | verified_live_zero_jobs | 42 |
  | dead_removed | 73 |
  | blocked_by_security | 30 |
  | temporarily_unavailable | 4 |
  | never checked | 6,584 |

- None has vendor-stated identity evidence outside the pilot. Workday identity comes only from the pilot's job-detail `hiringOrganization` lookup.
- The 6,055 malformed rows, including the 318 with no counterpart, stay rejected (`invalid_slug`) with their raw value in `source_rows`.

## Not duplicates or normalization collisions

- **Not duplicates:** the board keys are distinct.
- **Not normalization collisions:** no two different raw codes collapse into one store board here. Case-folding is the same in both builds.
