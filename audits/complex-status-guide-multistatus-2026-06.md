# Multi-status ComplexStatusGuide migration — F-6/G-1/E-7/F-5/D-2/D-4 (2026-06)

Brings the F-4 "recommended starting point → one dominant CTA → full-screen
guided flow → checklist-first result → official source/evidence handoff" pattern
to six more complex statuses, **without touching the F-4 reference module** and
**without inventing any legal/document content**.

## 1. Summary

F-6, G-1, E-7, F-5, D-2, and D-4 each now expose a single **추천 시작점
/ Recommended starting point** block at the top of their result card, with one
dominant CTA *"내 상황에 맞는 {CODE} 준비서류 찾기 / Find My {CODE} Document
Checklist"*, demoted secondary actions under *"다른 방식으로 보기 / Other ways to
view this status"*, and a full-screen guided flow (subcategory → procedure) that
ends in a **checklist-first** result. The competing legacy CTAs (the generic
"상황·절차별로 안내받기" and the in-card route-wizard) are suppressed for these six.

The actual legal documents are **never re-derived here** — the guide narrows the
user to a source-backed subcode + procedure and hands off to the existing,
tested source-backed detail (`ParadisoRoute.goToResult` → the card drawer). Items
this flow cannot assert are marked **"공식근거 확인 필요"**.

## 2. Status-by-status result

All six are implemented at **Level B** (unified entry + full-screen guided flow +
checklist-first result + safe handoff). Depth is intentionally conservative
because the deep per-subcode document data is owned by the existing source-backed
renderer, not this flow.

| Status | Level | Flow steps (source-backed) | Result | Data/source notes |
| --- | --- | --- | --- | --- |
| **F-6** | B | subcategory (F-6-1 국민배우자 / F-6-2 자녀양육자 / F-6-3 혼인단절자) + "잘 모르겠어요"; procedure (7 available) | checklist-first + handoff | 3 active subcodes; richest. (Existing F-6 route-finder remains available via ParadisoRoute.) |
| **G-1** | B | subcategory (15 reason-based active subcodes: 산재/난민/치료/소송/임금체불/사망가족/아동/임신출산/기타…) + 잘 모르겠어요; procedure (4) | checklist-first + cautious note + handoff | All subcodes `needsReview` → cautious note; nothing asserted. |
| **E-7** | B | subcategory (11 active 직종 groups; manual-review codes excluded) + 잘 모르겠어요; procedure (4 incl. workplace_change) | checklist-first + occupation note + handoff | Does **not** duplicate the existing job/industry-code analyzer; notes that exact 직종 confirmation may be required. |
| **F-5** | B (conservative) | subcategory (8 active 영주 types; **22 manual-review placeholders excluded**) + 잘 모르겠어요; procedure (연장/외국인등록; **사증발급 excluded — not_applicable**) | checklist-first + cautious note + handoff | Most F-5 subcodes are manual-review placeholders in the data → excluded; permanent-residence note. |
| **D-2** | B | subcategory (8 study types: 전문학사~박사/연구/교환/일학습/방문) + 잘 모르겠어요; procedure (6) | checklist-first + handoff | Clean subcodes. Kept strictly separate from D-4. |
| **D-4** | B | subcategory (7 training types: 어학원/기타기관/K-Trainee/초중고/한식/사설/외국어) + 잘 모르겠어요; procedure (5) | checklist-first + handoff | Clean subcodes. Kept strictly separate from D-2. |

CTA change for all six: removed the competing generic CTA + route-wizard; added
one recommended-start block with a single dominant CTA + demoted secondary
actions.

## 3. Files changed

| File | Change |
| --- | --- |
| `assets/js/complex-status-guide.js` | **New.** Self-contained `window.ParadisoStatusGuide` engine: recommended-start block injection at the top of each target card, full-screen/wide overlay (role=dialog, focus trap, ESC, progress, Back/Next/Close/Restart), config-driven subcode→procedure flow sourced from the tested `ParadisoRoute.buildGuidanceModel` adapter, checklist-first result, and a safe handoff to the source-backed detail. Pure helpers exported for the offline test. |
| `index.html` | Loads the new module (after visa-route-guide.js); `renderF4RouteChooser` now suppresses the legacy route-wizard for F-4 **and** the six (`COMPLEX_GUIDE_MIGRATED`). |
| `assets/js/visa-route-guide.js` | Generic in-card CTA suppressed for the six as well as F-4 (`COMPLEX_GUIDE_OWNED`); this module still powers the six guides' "view full detail" handoff. |
| `scripts/check_complex_status_guide.mjs` | **New.** Offline contract test (139 checks): exercises the real engine against `visa_data.json` (source-backed options only; checklist-first; no invented docs; wiring; F-4 untouched). |
| `scripts/check_repo.sh` | Wires the new check in as `[9d-3/14]`. |
| `scripts/check_popup_i18n.mjs` | Adds the new module to the KO/EN popup-chrome parity targets. |

Protected data files (`visa_data.json`, `backend/data/visas.json`,
`doc_master.json`) and the F-4 module were **not modified**.

## 4. Shared architecture

The F-4 engine (`ParadisoComplexGuide`) is data/f4-coupled and must not regress,
so it was **not forked into**. The new engine reuses the same UX, CSS tokens,
copy, a11y, and checklist-first pattern, but sources its options from
`ParadisoRoute` (visa_data) and delegates real documents to the existing
source-backed detail. This keeps all six consistent with F-4 while keeping new
code entirely out of protected legal-data rendering. (A future PR could unify F-4
onto a single generic engine once both are stable — see §11.)

## 5. CTA & discoverability

Each target card now leads with the recommended-start block (top of the card,
before subcode/procedure detail) and one dominant filled CTA, with the four
secondary "browse manually" actions demoted to small pills under a weaker label.
The previously competing generic CTA and route-wizard are suppressed for these
six, so there is exactly one recommended primary action per status.

## 6. i18n

All new chrome lives in the module's paired `STR_KO`/`STR_EN` packs (parity
enforced by `check_popup_i18n.mjs`); the CTA/sticky copy is built by interpolating
the status code into a template. No `data/i18n` keys were added/removed. Per the
repo policy and the platform's "Chinese preparing" status, zh-CN chrome resolves
to Korean canonical rather than low-quality machine text. Subcode/procedure
option labels come from `visa_data.json` (verbatim) via the adapter — never
invented strings.

## 7. Accessibility & responsive

`role="dialog"` + `aria-modal` + `aria-labelledby`; a `progressbar` with live
`aria-valuenow`; radio-group options with `aria-checked`; Tab focus-trap (with
shift), ESC-to-close, focus moved into the flow on open and restored to the CTA
on close. Options ≥52px, footer controls ≥48px. Overlay is a wide sheet on
desktop (`min(900px, 100%)` × `min(720px, 94vh)`) and **full-screen** ≤640px (no
double-scroll, no horizontal overflow). CSS uses the shared `--bg/--t/--ac/...`
tokens → civic_editorial + archive_diary (and dark) covered automatically.

## 8. Tests run

- `node scripts/check_complex_status_guide.mjs` → **139/139** (engine API,
  source-safe options, checklist-first, no invented docs, wiring, F-4 untouched).
- `node scripts/check_f4_route_guide.mjs` / `smoke_f4_hub.mjs` /
  `check_f4_guide_flow.mjs` → **ALL PASS** (F-4 not regressed).
- `node scripts/check_visa_route_guide.mjs` → 127/127 · `check_popup_i18n` OK ·
  `check_i18n` OK · `check_visa_issuance_ui` 2846/0 · `check_subcode_modal` OK ·
  `check_dummy_text` OK.
- `bash scripts/check_repo.sh` → **Success** (incl. 251 + 26 backend tests; only
  the network-gated golden eval skipped).

## 9. F-4 regression check

F-4 module + tests untouched; `check_f4_route_guide` / `smoke_f4_hub` /
`check_f4_guide_flow` all pass. F-4 remains in both suppression sets
(`COMPLEX_GUIDE_MIGRATED` / `COMPLEX_GUIDE_OWNED`), so its single CTA is intact.

## 10. Remaining risks

- **Conservative results.** "Basic required documents" hands off to the existing
  source-backed detail rather than rendering a per-subcode checklist inline (to
  avoid touching protected data / duplicate-render audits). Surfacing
  source-backed docs directly inside the guide is a future data-readiness pass.
- **No offline browser** (jsdom/Chromium); `check_complex_status_guide.mjs` is the
  offline stand-in. A real-browser pass at 360/390/430/768/1280px and both themes
  is recommended.
- **Two engines** (F-4 + the six) share the pattern but not the code; intentional
  for safety. Unification is a follow-up.
- G-1/E-7/F-5 carry cautious notes because their data is largely review-gated;
  outcomes are never asserted.

## 11. Recommended next PR

A real-browser QA pass (widths + themes + keyboard/ESC/focus) across all seven
statuses, then either (a) unify F-4 + the six onto one generic engine, or (b) a
data-readiness pass to surface source-backed per-subcode documents directly in
the result for the cleanest statuses (D-2/D-4/F-6) — source-reviewed, not guessed.
