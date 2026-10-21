# VISABLE R3.1: End-to-End Release & Verification Report
## Test Execution Records, Data Invariants & Multi-Viewport Browser Verification

- **Milestone**: VISABLE R3.1 (Production Publishing Recovery, Data Integrity & Operational Readiness)
- **Branch**: `feat/visable-r3-1-publishing-recovery`
- **Date**: 2026-10-20
- **QA Lead**: Automated QA & Reliability Engineering Team
- **Status**: 100% Passed (All Verification Suites Green)

---

## 1. Verification Summary

| Suite / Check | Command | Target / Scope | Result | Execution Time |
|---|---|---|---|---|
| **Checklist Data Invariant** | `node scripts/check_immigration_checklists.mjs` | 647 scenarios / 26 offices | **PASSED** (647/26) | 0.8s |
| **Backend Unit & Contract** | `python3 -m unittest backend.tests.test_checklist_operations backend.tests.test_knowledge_platform` | 75 unit & integration tests | **PASSED** (75/75, 0 errors, 0 failures) | 18.7s |
| **Playwright Browser E2E** | `npx playwright test tests/e2e/content-studio.spec.mjs tests/e2e/immigration-checklists.spec.mjs` | 138 tests across 6 viewports (1280, 768, 430, 390, 360, 320) | **PASSED** (138/138) | 3.1m |

---

## 2. Invariant Check Verification

```bash
$ export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH" && node scripts/check_immigration_checklists.mjs
Immigration checklist validation passed: 647 cases / 26 offices
```

- Total baseline cases: 647
  - `extension-202609.json`: 224 cases
  - `change-202609.json`: 251 cases
  - `registration-202609.json`: 172 cases
- Total immigration offices: 26 offices
- Canonical identifier check: 100% match `^e-`, `^c-`, `^r-` prefixes.
- Zero orphaned references or corrupted records.

---

## 3. Backend Unit & Integration Test Suite

```bash
$ export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH" && python3 -m unittest backend.tests.test_checklist_operations backend.tests.test_knowledge_platform
----------------------------------------------------------------------
Ran 75 tests in 18.680s

OK
```

Key test coverage includes:
1. `test_publish_release_endpoint_p0_contract_fix`: Validates that `publish_release_endpoint` passes `release_in=body` cleanly without TypeError.
2. `test_prepublish_validation_report_has_required_fields`: Confirms `passed`, `total_items`, `procedure_counts`, `durable_storage`, `dataset_checksum`, and `checks` fields.
3. `test_canonical_identifier_formats_enforced`: Validates rejection of non-canonical scenario IDs.
4. `test_four_eyes_self_approval_prevented`: Verifies `HTTP 409 Conflict` when draft author attempts self-approval.
5. `test_least_privilege_viewer_fallback`: Verifies fallback to `OperatorRole.VIEWER` on untrusted tokens.
6. `test_rollback_release_restores_snapshot_and_audit`: Verifies baseline snapshot reversion and audit event generation.
7. `test_public_preview_endpoints_functional`: Validates anonymous access to `/api/checklists/published` and candidate release preview on `/api/checklists/preview?release_id=...`.

---

## 4. Playwright End-to-End Browser Test Suite

```bash
$ export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH" && export PARADISO_PW_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" && npx playwright test tests/e2e/content-studio.spec.mjs tests/e2e/immigration-checklists.spec.mjs
  138 passed (3.1m)
```

Tested Viewports:
- `desktop-1280` (1280 x 800)
- `tablet-768` (768 x 1024)
- `mobile-430` (430 x 932)
- `mobile-390` (390 x 844)
- `mobile-360` (360 x 800)
- `mobile-320` (320 x 568)

Key Scenarios Verified:
- **Authentication & RBAC**: Closed state without tokens, rejection of invalid tokens, view-only adaptation for viewers, approval locks for editors.
- **Review Queue & Diff Viewer**: Live KPI calculation, visual diff inspection, HTTPS evidence requirement, Four-Eyes validation.
- **Publish Pipeline**: Pre-publish validation gate verifying 647 items, SHA-256 checksum rendering, candidate preview URL generation, rollback dialog execution.
- **Candidate Release Preview**: Top preview banner rendering on `/immigration-checklists.html?preview_release=rel-20261020-01` with exit preview navigation.
- **Mobile Usability**: Zero horizontal scrollbar/overflow across all 6 viewports, full WCAG AA color contrast, touch target compliance.

---

## 5. Pilot Scenarios & Vertical Slice Verification

| Scenario ID | Procedure | Visa Status | Category | Verified Functionality |
|---|---|---|---|---|
| `e-D2-01` | Extension | D-2 (유학) | Student general extension | Core required documents, conditional GPA requirements, draft diffing |
| `c-E71-01` | Change | E-7-1 (전문인력) | Professional employment change | Employment contract, employer tax filings, wage threshold check |
| `r-F4-01` | Registration | F-4 (재외동포) | Overseas Korean residence reporting | Basic nationality records, FBI background check, apostille/consular confirmation |
| `OFFICE-JEJU` | Override | D-2 (유학) | Jeju Immigration Office local rule | Regional financial solvency criteria override maintained without polluting national baseline |

All verification criteria for VISABLE R3.1 are completely satisfied.
