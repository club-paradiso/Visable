# Complex status guide — QA & regression coverage (2026-06-22)

A QA/regression-coverage pass for the complex status guide system (F-4 +
F-6/G-1/E-7/F-5/D-2/D-4). **No app behavior, UI, or legal/immigration content was
changed** — this PR only adds test coverage so future changes cannot silently
break the guide UX.

## Test approach

Real-browser automation **cannot run in this environment or in CI**:
- CI runs only `bash scripts/check_repo.sh` on a runner with no browser binary;
  the repo is a deliberate no-build static site (no `npm ci` step).
- In the build sandbox, `@playwright/test` installs from npm, but the Playwright
  **browser download is blocked by network egress** (`cdn.playwright.dev` not
  allowlisted) and there is no system Chromium — so a real browser could not be
  launched here.

So coverage is delivered in two layers:

1. **CI regression guard (verified, offline)** —
   `scripts/check_complex_status_guide_qa.mjs`, wired into `check_repo.sh` as
   step `[9d-4/14]`. It loads the REAL guide modules and exercises their pure
   render/result functions across all seven statuses in **KO + EN**, asserting the
   full QA contract (176 checks). This is the repo's established offline-stand-in
   pattern (same as `check_f4_guide_flow` / `check_complex_status_guide`).
2. **Real-browser suite (provided; run locally)** — `tests/e2e/
   complex-status-guide.spec.mjs` + `playwright.config.mjs` + `npm run test:e2e`.
   Authored from the verified rendered selectors but **not executed in this
   sandbox** (see above); the first local run in a browser-capable env is the
   verification step. Covers what the offline guard can't: real rendering,
   viewport overflow/clipping, overlay sizing, focus, keyboard, theme rendering.

## Status coverage (offline guard, KO + EN)

For each of **F-4, F-6, G-1, E-7, F-5, D-2, D-4**:

| Check | F-4 | F-6 | G-1 | E-7 | F-5 | D-2 | D-4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recommended-start block + 추천 시작점 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| document-checklist primary CTA (KO+EN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| secondary actions demoted under "다른 방식으로 보기" | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| primary CTA precedes secondary (hierarchy) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| one-question-per-step + "I am not sure" | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| checklist-first result section labels (KO+EN) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| source-safety (no overconfident wording) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Plus: extension results show source-backed **manual references**; F-6 visa
issuance renders a resolvable `doc_master` checklist; no prose leaks into any
rendered checklist; full-screen/wide overlay + a11y attributes; theme-token CSS;
F-4 regression (new CTA copy present, old "preparation path" copy gone); and the
index.html / visa-route-guide CTA-suppression wiring for all seven.

The real-browser suite then verifies, per status: search → block + CTA visible →
no horizontal overflow → ≥44px touch target; and for F-4 + F-6 the deep flow
(keyboard-open → wide overlay → one question per step → checklist result → ESC
close → focus restore).

## Viewport coverage (Playwright)

- **All 7 statuses × 5 viewports** — 1280 (desktop), 768 (tablet), 430 / 390 /
  360 (mobile): block + CTA visible, ≥44px target, no horizontal overflow.
- **Deep flow (F-4 + F-6) × 5 viewports**: open → steps → checklist result →
  close. Reduced matrix (deep flow only for the two strongest) keeps runtime
  reasonable, per the task's allowance; extend as the other statuses' data
  matures.

## Theme coverage

`civic_editorial` + `archive_diary` — F-6 guide opens and the overlay surface has
a real theme-token background (Playwright). The offline guard additionally
asserts both modules' CSS uses theme tokens (`--bg1/--ac/--t1/--bd`) so neither
hardcodes a non-theme surface.

## i18n coverage

- **KO + EN**: the offline guard runs the entire matrix in both languages
  (CTA copy, "잘 모르겠어요 / I am not sure", result section labels).
- **zh-CN**: falls back to Korean per the repo policy (unchanged); not broken.

## Accessibility coverage

Asserted (offline, in both modules) + exercised (Playwright for F-4/F-6):
`role=dialog` + `aria-modal`, Tab focus-trap (shiftKey) + focus restore
(`lastFocus`), ESC close, radio-group options with `aria-checked`, progressbar
with `aria-valuenow`, accessible button names, keyboard activation (Enter).

## Source-safety / data-safety checks

The guard scans all user-facing rendered strings (both languages, all statuses)
for overconfident wording and fails on any of: *you are eligible*, *you will be
approved*, *always required*, *guarantees/guaranteed approval*, *반드시 발급*,
*무조건 가능*, *승인됩니다*, *항상 필요*, *보장합니다*. It also confirms
"공식근거 확인 필요 / Official source needs confirmation" is available and that F-4
keeps its explicit "does not guarantee / 보장하지 않습니다" wording. (The only
"guaranteed" occurrences are safe negations — "never/cannot be guaranteed".)

## Bugs found and fixed

None. No behavioral bug was found during this QA pass; no app/logic file was
modified. (Two initial *test* assumptions were corrected before landing: the
first available procedure for some statuses is `visa_issuance` with no
`procedures` entry — the engine correctly shows "공식근거 확인 필요" there, so the
manual-reference assertion was moved to the `extension` procedure; and F-4 builds
its `role` attribute dynamically, so the a11y regex was widened. These were test
fixes, not engine changes.)

## Files changed

| File | Purpose |
| --- | --- |
| `scripts/check_complex_status_guide_qa.mjs` | **New.** Offline cross-status QA regression guard (176 checks, KO+EN). |
| `scripts/check_repo.sh` | Wires the QA guard in as `[9d-4/14]`. |
| `tests/e2e/complex-status-guide.spec.mjs` | **New.** Real-browser Playwright suite (run locally). |
| `playwright.config.mjs` | **New.** Static-server + 5-viewport projects for the e2e suite. |
| `tests/e2e/README.md` | **New.** How to run + the honesty note about CI/sandbox. |
| `package.json` | Adds `test:e2e` + `test:complex-guide-qa` scripts and the `@playwright/test` devDependency. |
| `audits/complex-status-real-browser-qa-2026-06-22.md` | This report. |

No changes to `index.html`, `assets/js/*` guide modules, or any data file.

## Tests run

- `node scripts/check_complex_status_guide_qa.mjs` → **176/176** ✅
- `node --check tests/e2e/complex-status-guide.spec.mjs` / `playwright.config.mjs` → syntax OK
- `bash scripts/check_repo.sh` (ALLOW_BACKEND_TEST_SKIP=1) → **Success** — incl.
  `check_f4_route_guide` / `smoke_f4_hub` / `check_f4_guide_flow` (F-4 not
  regressed), `check_complex_status_guide`, the new `[9d-4]` QA guard, and 251 +
  26 backend tests. Only the network-gated golden eval was skipped.
- `npm run test:e2e` → **not run here** (browser CDN egress blocked); run locally.

## Manual QA (exact steps, until the e2e suite is run in a browser env)

For each of F-4, F-6, G-1, E-7, F-5, D-2, D-4, at 360 / 390 / 430 / 768 / 1280px,
in KO and EN, and in civic_editorial + archive_diary:
1. Open the site, search the status code.
2. Confirm the "추천 시작점 / Recommended starting point" block appears near the top
   with the "내 상황에 맞는 {CODE} 준비서류 찾기 / Find My {CODE} Document Checklist" CTA,
   before subcode/procedure detail, with no horizontal overflow.
3. Confirm secondary actions sit under "다른 방식으로 보기 / Other ways to view this
   status" and look weaker than the primary CTA.
4. Click/Enter the CTA → confirm a full-screen (mobile) / wide (desktop) overlay,
   not a tiny modal; no double-scroll; Close/Back/Next visible.
5. Confirm one question per step and an "I am not sure" option; complete the flow.
6. Confirm a checklist-first result (먼저 해야 할 일 / 기본 준비서류 / 내 상황에서 추가될 수
   있는 서류 / 신청 절차 / 공식 근거 / 다음 행동), with source-backed manual references or
   "공식근거 확인 필요" — no empty cards, no fabricated sources.
7. ESC closes; focus returns to the CTA.

## Remaining limitations

- The Playwright suite is **provided but unverified in this sandbox** (browser
  egress blocked). It must be run once in a browser-capable env; treat that run
  as its verification. The offline guard is the CI safety net in the meantime.
- The offline guard asserts strings/structure/a11y attributes from the real
  modules, not pixel layout; visual/overflow regressions are only caught by the
  Playwright run.
- Deep-flow e2e currently covers F-4 + F-6; the other four get the block/overflow
  smoke only.

## Recommended next PR

Run the Playwright suite in a browser-capable environment (or add a separate,
opt-in browser CI workflow) to verify it and capture baseline screenshots; then
the previously-recommended **source-reviewed `doc_master` mapping** for the six
statuses' procedure documents (which would also let the deep-flow e2e assert real
in-overlay document checklists for D-2/D-4/E-7).
