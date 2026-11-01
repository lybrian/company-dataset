# Phase 1c report: two precision fixes, offline re-export of pilot 3 (2026-11-01)

No provider checks, fetches, Common Crawl or full run. The store was only read: its sha256 is
24c3c2a0…2a93, the same before and after. All previous pilots, exports and archives are untouched.

## Outputs

| Item | Path |
|---|---|
| Corrected export | `data/exports/pilot3_phase1c/` |
| Reproduction | `data/exports/pilot3_phase1c_repro/` (SHA256SUMS identical) |
| Old vs new comparison | `data/exports/pilot3_phase1c_diff/changed_boards.csv`, `summary.json` |
| Websites dropped, with reason | `data/exports/pilot3_phase1c/website_rule_changes.csv` |
| Tests | `data/store_reports/tests_phase1c.txt`: 458 passed. Of these, 50 are new, in `tests/test_pilot3_regressions.py` |
| Unchanged baseline | `data/exports/pilot3/`, `data/exports/pilot3_repro/` |

## Fixes

1. **Geo-qualified names.** In `identity.cluster_companies`, two boards that share a domain or LinkedIn key no longer merge when their names carry different country or region qualifiers. "KPMG Australia" ≠ "KPMG", "Deloitte UK" ≠ "Deloitte US". Only the same provider account counts as explicit evidence across qualifiers. "International", "Global" and compass words are not treated as qualifiers.
2. **Ownership websites.** A site accepted because it links to the board must also have a domain that names the company (`identity.domain_compatible`), or a page that names itself as the company.
   - Careers-branded domains (`careers_branded_domain`) and careers platforms (jibeapply.com and 13 others, in `normalize`) are never websites.
   - Board ownership still confirms identity when the site is rejected.
   - A root that redirects to its own careers host is kept, as before.
   - Live runs apply this in `pilot.py` and can move on to the next candidate site.
   - Offline, `store_export` re-checks the stored evidence and stored pages. A failing website is dropped together with what came from it: LinkedIn, homepage description, domain-based country, and careersite verification that relied on a redirect to that domain.

## What changed (4,500 boards compared)

38 boards changed: 36 from the website rule and 2 from the merge fix. **No unexplained changes.**

| | Old | New |
|---|---|---|
| Unique companies | 1,933 | 1,934 |
| Complete companies | 1,075 | 1,071 |
| Websites dropped | – | 36 (25 board-link only, 10 careers-branded, 1 careers platform) |

- **Merge:** KPMG Australia and pinpoint `kpmg` are now separate companies. pinpoint `kpmg` was already a complete board, so it now appears as its own complete company (+1).
- **No longer complete (5):**
  - pladis France (bn-biscuits.com): correctly removed.
  - The Sia Foundation (sia.tech), fomo Labs (fomo.family), Martin Mathys (mathyspaints.eu) and Isabella Glutenfreie Pâtisserie (isabella-patisserie.de): these look like the companies' own sites, so they are **false drops**.

### Manual verdicts on the 36 dropped websites

- **Correct, 14:**
  - parent's domains: fcs.wfs.aero, dunigroup.com;
  - a brand site: bn-biscuits.com;
  - a city's campaign site: schluesselposition.de;
  - careers domains: vistrycareers.co.uk, wellpathcareers.com, jobsatpeligoni.com, werkenbijedco.nl, jobs-vandervalk.de, europizzaproductsjobs.com, invitejobs.nl, zahnarzt-simo-karriere.de, ca-recrute.fr;
  - a careers platform: moncler.jibeapply.com.
- **Probably correct, 4:** oldcreeklodgegatlinburg.com (Oaktenn), fabianbuenker.de (Golf in Leicht), americansafetycouncil.com (Certus), sverigesskonhetscenter.se (Skönhetsgruppen).
- **False drops, 12:** sia.tech, fomo.family, mathyspaints.eu, isabella-patisserie.de, blacknova.vc, montessori-lauf.de, utec.edu.pe, sms-ing.de, expertisebureaurisicobeheer.nl, steuerberater-aschaffenburg.eu, beledad.com, my-headhunter.at. Only the first four were complete.
- **No effect on confirmed output, 6:** 5 unresolved or mismatched boards (halfmoon, saputo, heidrick, robbinsrecruiting, pineapple-recruiting) and one unclear case (autonomous-teaming.ai, "ATS").

Correction to the Phase 1b review: montessori-lauf.de is most likely the association's own school site ("Montessori Campus Lauf und Altdorf"), not a different school's. It is listed above as a false drop.

## Limits of the offline re-export

- It cannot try the next-ranked website. In a live run, some boards would go on to verify their real site (for example the main Vistry domain).
- Boards with no confirmed name have no name to check a board-link website against, so their board-link websites are dropped. This affects unresolved rows only.
- The live candidate loop in `pilot.main` has no unit test of its own. Its parts (`website_supported`, `careers_branded_domain`, `domain_compatible`, `board_ownership`) are tested.
