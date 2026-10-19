# VISABLE R3: Risk & Security Register
## Content Operations Studio, Regulatory Data Governance & System Integrity

- **Milestone**: PR #662 (VISABLE R3 — Content Operations Studio)
- **Date**: 2026-10-19
- **Security Lead**: VISABLE Reliability & Regulatory Quality Engineering Team
- **Status**: Production Audit Ready

---

## 1. Threat Model & Security Posture

The Content Operations Studio (`/content-studio.html` and `/api/knowledge/studio/checklists/*`) governs authoritative immigration document requirements that directly affect real foreign residents' legal status, visa applications, and administrative outcomes in South Korea.

A compromised or improperly validated update could lead to:
1. Rejection of foreign residents' visa applications due to incorrect document guidance.
2. Inadvertent omission of required statutory documents.
3. Leaks of internal operator credentials.
4. Cross-site scripting (XSS) via maliciously crafted document titles or notes.

To counter these threats, the system implements defense-in-depth across authentication, authorization, data validation, and client rendering.

---

## 2. Prioritized Risk Register (P0 / P1 / P2)

| ID | Severity | Category | Risk Description | Probability | Impact | Mitigation Status & Technical Countermeasures |
|---|---|---|---|---|---|---|
| **R3-01** | **P0** | **Data Integrity** | Baseline scenario count reduction or silent data loss (dropping below 647 items). | Low | Critical | **RESOLVED**: Automated pre-publish validation gate (`run_prepublish_validation`) checks that total count == 647 (224 ext, 251 chg, 172 reg). Releases are rejected if any scenario is missing. |
| **R3-02** | **P0** | **Legal Authenticity** | Fabricated or uncorroborated requirements published without official statutory basis. | Medium | Critical | **RESOLVED**: Strict Evidence Gate in `act_on_draft(..., action='approve')`. Approval is blocked with `REVIEW_REQUIRED` (422/409) unless `evidence_url` begins with `https://`. |
| **R3-03** | **P0** | **Access Control** | Privilege escalation: Unauthorized user modifying, approving, or releasing data. | Low | High | **RESOLVED**: Server-side RBAC (`OperatorRole`: `viewer`, `editor`, `reviewer`, `publisher`). Tokens compared in constant time with HMAC (`hmac.compare_digest`). System is closed by default (503) if tokens are unset. |
| **R3-04** | **P1** | **Client Security** | Stored XSS injection through operator-provided text (titles, notes, reasons). | Medium | High | **RESOLVED**: `content-studio.js` exclusively uses `textContent` and DOM creation (`doc.createElement`). Zero `innerHTML` is used for dynamic strings. |
| **R3-05** | **P1** | **Credential Leakage** | Operator bearer token persisted in `localStorage` or leaked across browser tabs. | Medium | Medium | **RESOLVED**: Token is held in memory and `sessionStorage` only. Cleared on tab close or sign out. Page includes `<meta name="referrer" content="no-referrer">` and `noindex, nofollow`. |
| **R3-06** | **P1** | **Office Practice Contamination** | Local immigration office exceptions overwriting national statutory baselines. | Medium | Medium | **RESOLVED**: Separate `checklist_office_overrides` table. Local requirements (e.g. Jeju student financial thresholds) are stored as discrete overrides linked to office codes and never mutate national baseline items. |
| **R3-07** | **P2** | **Auditability** | Inability to determine who proposed, approved, or published a specific regulation. | Low | Medium | **RESOLVED**: Immutable audit log in SQLite. Every draft, action, and release records `actor`, `actor_role`, timestamp, and rationale. |
| **R3-08** | **P2** | **Mobile Accessibility** | Operator UI horizontal overflow or inaccessible forms on mobile/tablet viewports. | Medium | Low | **RESOLVED**: CSS responsive layout tested with Playwright across 6 viewports (desktop 1280 to mobile 320) with 0 horizontal overflow and full WCAG AA contrast. |

---

## 3. Defense Verification & Automated Testing Matrix

Every mitigation described above is backed by automated regression tests in the repository:

1. **Python Unit & Contract Tests (`backend/tests/test_checklist_operations.py`)**:
   - `test_bootstrap_seeds_exactly_647_items`: Asserts 647 items, 224 ext, 251 chg, 172 reg.
   - `test_role_permissions_rbac`: Verifies `viewer` cannot edit, `editor` cannot approve, `reviewer` cannot publish.
   - `test_evidence_gate_blocks_approval_without_https`: Validates HTTP 422 when approving draft without HTTPS link.
   - `test_prepublish_validation_gate_fails_if_baseline_corrupted`: Validates that deleting an item causes validation failure.
   - `test_publish_release_pipeline_applies_approved_drafts`: Validates end-to-end publish release.
   - `test_vertical_slice_pilot_d2_e7_f4_and_jeju`: Validates D-2, E-7-1, F-4 and Jeju office override.

2. **Browser E2E Tests (`tests/e2e/content-studio.spec.mjs`)**:
   - Closed state without configured token (503).
   - Rejection of invalid token without localStorage contamination (401).
   - Role presentation and RBAC adaptation in UI.
   - Live KPI calculation (647 items).
   - Strict HTTPS evidence requirement in Review Queue.
   - Visual Diff rendering with legal impact warning.
   - Pre-publish validation gate with 647 item checklist.
   - Zero horizontal overflow across viewports (1280, 768, 430, 390, 360, 320).
