# HiKorea Reservation Helper — Browser QA (2026-06)

/ 하이코리아 예약 도우미 real-browser QA pass

## 1. Summary

Post-merge QA of the **하이코리아 예약 도우미 / HiKorea Reservation Helper** (introduced
in PR #462, nearby-wording polish in PR #464). The helper itself is healthy: it
opens reliably from every entry point, carries visa/status context in from search
results, runs the one-question-per-step flow, and renders a cautious, sectioned
result card across both languages. All deterministic + i18n validation is green,
and a headless full-flow harness drove the **real** module through every entry
point and scenario (106/106).

**One concrete issue was found and fixed:** the nearby `관할 출입국관서 조회`
(jurisdiction lookup) modal on `main` still carried the old absolute/bureaucratic
reservation wording. PR #464 had softened it, but that change merged into the
feature branch rather than `main`, so it regressed on `main`. This PR re-applies
the softening so the modal's tone matches the helper.

**Real-browser limitation:** no browser binary is available in this environment
and Playwright browser download is network-blocked, so visual rendering was
verified at the headless-DOM + code-review level rather than with live
screenshots. Details below.

## 2. Scope

In scope:
- `하이코리아 예약 도우미 / HiKorea Reservation Helper` (`assets/js/hikorea-reservation-helper.js`)
- Entry points: main gateway card + visa-search result cards (D-2/F-4/E-7/F-5/G-1/F-6)
- The adjacent `관할 출입국관서 조회` modal (tone consistency only)

Explicitly out of scope (untouched): visa data/logic, legal/document-requirement
logic, Waymaker answer generation, homepage redesign, broad `index.html`
refactor, and unproven legacy CSS/i18n deletion.

## 3. Browser / local setup used

- Node `v22.x`. Static site, no build step.
- **Real browser: unavailable.** `npx playwright --version` → 1.56.1, but no
  browser binary is cached and `npx playwright install chromium` is network-blocked
  (no-op); no system Chrome/Chromium present. Live screenshots could not be captured.
- **Substitute harness:** the real module is loaded into a minimal DOM stub and
  driven through the actual `document` click/change → `render()` path (option
  picks auto-advance, Next/Back, status-code input, expiry input, result). This
  exercises the genuine render output and routing, not a re-implementation.
- Layout/contrast/overflow were assessed by reading the module's injected CSS
  (theme tokens + responsive rules) and the shared modal CSS in `index.html`.

## 4. QA matrix

Harness coverage = real module render, asserted programmatically. Visual columns
marked “code-review” were verified by inspecting CSS/markup, not a live browser.

| Language | Theme | Viewport | Entry point | Method | Result |
|---|---|---|---|---|---|
| KO | civic_editorial | desktop 1440 | main gateway card | harness + code-review | ✅ opens, title `하이코리아 예약 도우미`, `1 / 4`, q1, no suggestion panel |
| KO | civic_editorial | mobile 375 | D-2 search → helper | harness + code-review | ✅ code carried in, D-2 chips, large tap targets, sticky nav doesn’t cover result |
| KO | archive_diary | mobile 375 | F-4 search → helper | harness + code-review | ✅ F-4 chips incl. 국내거소신고; theme-token contrast |
| KO | civic_editorial | tablet 768 | E-7 search → helper | harness + code-review | ✅ E-7 chips incl. 근무처 변경/추가 |
| KO | civic_editorial | desktop 1440 | F-5 search → helper | harness + code-review | ✅ concrete F-5 chips (체류지 변경·등록증 재발급·등록사항 변경·체류자격 관련 상담) |
| KO | archive_diary | mobile 375 | G-1 search → helper | harness + code-review | ✅ G-1 chips |
| EN | civic_editorial | desktop 1440 | main + all 6 contexts | harness + code-review | ✅ title `HiKorea Reservation Helper`, sections/cautions localize, no leaked KO chrome |
| EN | archive_diary | mobile 375 | result card | harness + code-review | ✅ long EN labels wrap (no fixed width/nowrap → no overflow) |
| KO/EN | both | all | `관할 출입국관서 조회` modal | code-review | ✅ after fix, tone matches helper |

A11y / interaction (shared modal shell, verified by reading `index.html`):
- Escape closes the helper (`keydown` handler at index.html includes `hikoreaGuideOverlay`). ✅
- Focus trap on Tab (`trapModalFocus`). ✅
- Focus restored to the triggering element on close (`closeModal` → `lastFocusedElement`). ✅
- Modal scrolls when tall (`.hikorea-modal { max-height:88vh; overflow-y:auto }`, mobile `92vh`; `.modal-body { overflow-y:auto }`) → bottom CTAs reachable. ✅
- Close button (✕) wired to `close-hikorea-guide` → `closeModal`. ✅
- Options/Next/Back are real `<button>`s with `:focus-visible` rings; progress is `role="progressbar"` with `aria-valuenow`. ✅

## 5. Scenario results (A–F)

Driven through the real click/render path; recommendation + cautions asserted.

| # | Input | Expected | Result |
|---|---|---|---|
| A | D-2, purpose unsure/등록, card 없어요, in Korea | → 외국인등록, cautious, disclaimer + same-day caution | ✅ `외국인등록 / Alien registration`; not overconfident |
| B | D-2, purpose 연장, card 있어요, in Korea, expiry ~10d | → 체류기간 연장, expiry caution, “check window” | ✅ `체류기간 연장`; “만료일이 얼마 남지 않았…” + application-window note |
| C | F-4, purpose unsure/등록, card 없어요, in Korea | → 국내거소신고 (not generic 외국인등록) | ✅ `국내거소신고 / Domestic residence report` |
| D | E-7, purpose 근무처 변경/추가, card 있어요, in Korea | → 근무처 변경/추가, generic prep (nothing invented) | ✅ `근무처 변경/추가`; prep = generic “check required documents” |
| E | F-5 context | concrete chips only | ✅ 체류지 변경 · 등록증 재발급 · 등록사항 변경 · 체류자격 관련 상담 (no vague labels) |
| F | mostly 잘 모르겠어요 | low confidence + 1345 / 관할 출입국 fallback | ✅ confidence `낮음/low`, 1345 fallback, still gives practical steps |

Always-on cautions verified on a normal result: same-day caution
(`당일 예약은 되지 않을 수 있…`) and real-name caution
(`예약은 실제 방문하는 사람 이름…`) present.

## 6. Issues found

1. **(Fixed)** `관할 출입국관서 조회` modal on `main` used absolute/bureaucratic
   reservation wording inconsistent with the helper:
   `⚠️ 방문 예약 필수`, `예약 없이 방문 시 당일 처리 불가`, `예약 10분 전 도착, 지각 시 무효 처리`.
   (PR #464 had softened this, but on the feature branch — it never reached `main`.)
2. No other concrete defect found. Modal open/close/Escape/focus-restore/scroll,
   progress, status-context pass-through, F-5 concrete chips, KO/EN parity, and
   "no old pre-check UI" all verified good. No helper-caused console errors in the
   headless drive (no exceptions thrown across 106 flow assertions).

## 7. Fixes made

- `index.html` — softened the jurisdiction-lookup modal (KO-only static markup;
  no test/i18n/script dependency), keeping the guidance but matching the helper's
  cautious, practical tone:
  - `⚠️ 방문 예약 필수` → `📅 방문 전 예약 안내`
  - `…사전 예약 필수` → `…보통 사전 예약이 필요해요.`
  - `예약 없이 방문 시 당일 처리 불가` → `일부 업무는 예약 없이 방문하면 처리되지 않을 수 있어요. 방문 전에 하이코리아에서 예약 가능 여부를 확인하세요.`
  - `예약 10분 전 도착, 지각 시 무효 처리` → `예약 시간에 늦으면 접수가 어려울 수 있으니, 여유 있게 도착하세요.`

No changes to the helper module were needed — it passed all QA.

## 8. Screenshots

Not captured. No browser binary is available and Playwright's Chromium download
is network-blocked in this environment, so live rendering could not be
screenshotted. Visual checks were done via the headless render harness (real
module output) plus CSS/markup review. A real-device screenshot pass is listed as
follow-up.

## 9. Tests run

- `node scripts/check_hikorea_reservation_helper.mjs` → **80/80**
- `node scripts/check_popup_i18n.mjs` → OK (KO/EN chrome parity)
- `node scripts/check_i18n.js` → OK (coverage + hardcoded-text scan)
- `git diff --check` → clean
- `bash scripts/check_repo.sh` → PASS (see PR body for the exact tail)
- Headless full-flow harness (6 entry points × KO/EN + scenarios A–F + always-on
  cautions) → **106/106**

## 10. Remaining limitations

- No live-browser rendering verification (no binary / network-blocked install):
  pixel-level contrast, exact line-wrapping, and real-device tap behavior are
  inferred from theme tokens + responsive CSS, not observed.
- Legacy residue (dead `.step0a-*` / wizard-internal `.hikorea-*` CSS and orphaned
  `hk*`/`step0a*` i18n keys) remains. Not removed here — several `.hikorea-*`
  classes are still live and the i18n keys are pinned by
  `RouteAwareI18nCoverageTests` + KO/EN/zh-CN parity. Removing them is a separate,
  carefully-scoped cleanup, not "cleanup theater."

## 11. Recommended follow-up

1. A real-device / real-browser screenshot pass (KO/EN × civic_editorial/archive_diary
   × 1440/768/375), focusing on `archive_diary` contrast and EN label wrapping on
   375px.
2. A dedicated cleanup PR for dead `.hikorea-*`/`.step0a-*` CSS + orphaned
   `hk*`/`step0a*` i18n keys, updating `RouteAwareI18nCoverageTests` in lockstep.
3. Consider porting the jurisdiction-modal tone fix and any future helper polish
   to a single lineage so feature-branch vs. `main` wording can't diverge again.
