# Restore Trust — task board (2026-10-28)

Branch `claude/gracious-rubin-37fmu4`, base `06390bc`. A task moves to VERIFIED only when
the test named in its row passes. To resume, check `git status` and `git log`, then re-run the
commands in `test-results.md` before trusting this table.

| Group | Task | Status | Evidence |
|---|---|---|---|
| TG-A | Recon: README, CLAUDE.md, package.json, tests/CI, status-guidance resolver, manual corpus search, civic header overlays | DONE | `remediation-log.md` §1 |
| TG-B | Inventory of every status × procedure cell (263 codes × 16 procedures = 2,456 cells) through the real resolver | DONE | `inventory.csv`, `scripts/audit_status_procedure_grid.mjs` |
| TG-B | Trust-defect detection: chip/outcome mismatch, contradictory badges, wrong cited page, evidence volume and scope | DONE | `findings.csv` RT-01…RT-15 |
| TG-C | Legal integrity: no requirement, state, fee or document added or changed. Page references re-pointed only where the page text was read. Verification stages kept separate | VERIFIED | `legal-verification.csv`; data diff = 6 page numbers |
| TG-D | Evidence search: shared-chapter pages that name only other statuses are excluded; procedure evidence is kept to its own manual | VERIFIED | `audit_evidence_volume.mjs --check` (fails on the old code) |
| TG-E | Badge reflects the outcome (RT-01/02), badge legend (RT-03), verbatim source preview (RT-05), cited page (RT-04) | VERIFIED | `restore-trust.spec.mjs` (6 viewports × 4 tests), browser matrix |
| TG-E1 (P1) | Language selector anchoring and the shared overlay layer (RT-08…11) | VERIFIED | `RT-UI-overlay-anchoring.md`, `overlay-anchoring.spec.mjs` |
| TG-F | Pipeline: confirmed pages flow from `build_status_coverage_manifest.py`. Rebuilt bundle, suggest index and backend deploy copy | VERIFIED | manifest `--check`, `check_repo.sh` [11/14] |
| TG-G | Exhaustive browser pass: 258 status/substatus codes in batches of 10 at 390px | VERIFIED | `test-matrix.csv`, `scripts/browser_status_matrix.mjs` |
| TG-G | Regression suites: check_repo.sh, npm test groups, full Playwright run (3 projects) | see `test-results.md` | |
| TG-H | Security and performance: XSS probe, escaping review, resolver cost measured | VERIFIED | `test-results.md` §Security/Performance |
| TG-I | Final report and draft PR | DONE | `FINAL_REPORT.md` |

Open items (not VERIFIED): RT-13, RT-14 and RT-15. See `unresolved-risks.md`.
