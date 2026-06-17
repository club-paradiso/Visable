# Unified Visa/Status Route-Guidance Layer — Implementation Report (2026-06)

Turns Paradiso's search → result-card experience into a **guided procedure
navigator** that works the same way for every 체류자격:

```
search → (세부코드 / 상황 선택) → (절차 선택) → result drawer opens with the
chosen subcode + procedure already active, summarised at the top.
```

This is a reusable route-guidance layer, not an F-6-only patch. All visa/status
records flow through one adapter + one set of components.

---

## 1. Files changed

| File | Change |
| --- | --- |
| `assets/js/visa-route-guide.js` | **New.** Self-contained route-guidance module (`window.ParadisoRoute`): normalized adapter, subcode selector, procedure selector, one-question route finder, procedure summary card, URL state machine, in-card CTA. ~Pure helpers are also `module.exports`-ed for Node tests. |
| `index.html` | **3 surgical edits** for the route layer + document-taxonomy fallback labels (see §7). (a) `<script defer src="assets/js/visa-route-guide.js">`; (b) `show-detail` action delegates to `ParadisoRoute.start()` with graceful fallback to `openVisaDrawer`; (c) `'routeGuideOverlay'` added to the global Escape-to-close list. No existing render/search/i18n/theme code was rewritten. |
| `data/i18n/{ko,en,zh-CN}.json` | Document-taxonomy relabel (display-only): `docUxGroupLabels` + `issuanceUiLabels` mapped to the spec's friendly taxonomy (§7). No keys added/removed (parity preserved). |
| `scripts/check_visa_route_guide.mjs` | **New.** Offline validation: loads the real pure functions and exercises the adapter, URL state machine, and route finder against every record + asserts index.html wiring, i18n fallbacks, and no-dummy-text. 127 checks. |
| `scripts/check_repo.sh` | Wired the new check in as step `[9d-2/14]`. |
| `audits/visa-route-guidance-unified-flow-2026-06.md` | This report. |

Protected data files (`visa_data.json`, `backend/data/visas.json`,
`doc_master.json`) were **not modified**. The layer is renderer/resolver-only.

---

## 2. Architecture summary

The repo's established extension pattern (see `assets/js/f4-route-guide.js`) is a
self-contained IIFE loaded with `<script defer>`, exposing a `window.Paradiso*`
namespace, fetching/reading its own data, and integrating through the existing
`paradiso:results-rendered` / `paradiso:landing-reset` events and the
`.external-guide-slot` injected into every result card. The route-guidance layer
follows exactly this pattern, so it is decoupled, testable, and degrades
gracefully if it fails to load (clicks fall back to the plain `openVisaDrawer`).

It reuses — never duplicates — the page's own machinery:

- **Availability** in the procedure selector is read from the page's **own
  rendered `.procedure-tab` buttons** (the single source of truth that
  `getProcedure()` produces), so it can never drift from what the card shows.
  The pure adapter mirrors `getProcedure()` availability for Node validation and
  as a fallback.
- **Result rendering** reuses `openVisaDrawer()` (the existing detail drawer);
  the summary card is injected at the top of the cloned card and the matching
  procedure tab/panel is activated with the same `.active` contract the
  `select-procedure` handler uses.
- **Official procedure labels** come from the page's `txAt('procedureLabels', …)`
  so they read identically to the tabs.
- **Modals** use the app's `openModal`/`closeModal` for focus-trap + Escape.

### Components (Step 4 mapping)

| Spec component | Implementation |
| --- | --- |
| `VisaRouteModal` | `#routeGuideOverlay` single wizard overlay (centered modal desktop / bottom sheet mobile) |
| `SubcodeSelector` | `renderSubcodeSelector()` |
| `ProcedureSelector` | `renderProcedureSelector()` (live-tab availability + adapter labels) |
| `ProcedureSummaryCard` | `injectSummaryCard()` (top of result drawer) |
| `ProcedureTabs` | reuses the existing in-card `.procedure-tab` / `.procedure-panel` |
| `RouteFinderQuestionStep` | `renderRouteFinder()` + `routeFinderNext()` engine |
| Mobile bottom sheet | CSS `@media (max-width:640px)` → overlay `align-items:flex-end` |

---

## 3. Data normalization (adapter)

`buildGuidanceModel(record)` produces a DOM-free normalized model:

```js
{ code, titleKo, titleEn, hasSubcodes,
  subcodes: [{ code, titleKo, titleEn, userLabelKo, status, needsReview }],
  procedures: [{ key, camelKey, officialLabel, userLabel, explanation, status }],
  hasRouteFinder }
```

- **Procedure enum** is the approved snake_case set; `CAMEL_OF` maps each to the
  legacy in-page tab key. `procedureStatusForRecord()` returns
  `available | conditional | not_applicable | source_limited` and faithfully
  mirrors `getProcedure()` (explicit `available` flag → legacy `*ReqDocs`/`*Req`
  fields → suppression of 사증발급 for 영주 F-5).
- **No invented content.** Sub-code titles come from the data; the only curated
  plain-language descriptors are F-6-1/2/3 (verbatim from the spec). Every other
  sub-code falls back to its official Korean name. Procedures with no
  source-backed data are shown as `source_limited` ("공식 출처 확인 필요"), never
  faked. Procedures the page does not render are simply not offered.
- **i18n:** the new surface is trilingual (ko / en / zh-CN) in-module, so it does
  not touch the central packs (no parity-check risk) and does not regress KO/EN.
  Titles use the localized visa name; the module re-renders on
  `paradiso-language-applied`.

---

## 4. UI flow summary

- **Entry:** every guidable result card gets a prominent in-card CTA
  ("상황·절차별로 안내받기"), reusing the already-wired `data-action="show-detail"`.
  Compact search cards route through the same delegated action.
- **Parent with subcodes →** centered modal / bottom sheet:
  *"{code} {name} 중 어떤 상황에 가까우신가요?"* with sub-code cards (세부코드 badge,
  KO/EN title, plain-language descriptor) + **"잘 모르겠어요"** + "먼저 전체 안내 보기".
- **Parent without subcodes / direct sub-code →** skips straight to the procedure
  selector (user label + official label + explanation + availability badge;
  not-applicable shown disabled, never hidden; 방문예약 always offered → HiKorea).
- **Procedure chosen →** URL is pushed (`?code&subcode&procedure`), the result
  drawer opens, a **summary card** is injected at the top (parent + subcode,
  KO/EN title, *현재 선택한 절차*, *이 절차는 누구에게 해당하나요?*, and buttons
  **세부코드 바꾸기 / 절차 바꾸기 / 공식근거 보기 / Waymaker로 질문하기**), and the matching
  procedure tab is activated. Landing is the calm summary (not a wall of docs —
  per the spec's "Do not"), with a one-tap jump to the procedure detail.
- **Route finder ("잘 모르겠어요"):** one question at a time, 뒤로 always available,
  "결과 보기" only when confident, low-confidence → "공식기관 확인 필요" + closest
  sub-codes. Config-driven (`ROUTE_FINDER`), seeded with F-6 from the spec.
- **URL state:** refresh, back/forward, and shared links all reopen the same
  guidance; invalid sub-code/procedure are dropped and the URL is scrubbed back
  to the parent with a non-blocking toast.

---

## 5. Test results

- `node scripts/check_visa_route_guide.mjs` → **127/127 pass** (adapter, URL
  round-trip + graceful validation, route finder, i18n fallbacks, no-dummy-text,
  code-hierarchy invariants incl. G-1-5).
- `bash scripts/check_repo.sh` (offline) → **Success** — JSON valid, manual
  schema valid, i18n parity, subcode-modal, dummy-text, F-4 hub, visa-issuance
  UI, duplicate-render audit, required-docs coverage, **251 backend tests**, etc.
- **Real-browser (Playwright/Chromium) smoke → 36/36 pass:** full F-6 flow,
  deep-link reload, graceful fallback, no-subcode skip (E-1), direct-subcode skip
  (F-6-1), route finder, real CTA click delegation, back/forward, **mobile bottom
  sheet**, and **light + dark** rendering. Zero page errors from the layer.
- **Breadth (all 17 priority statuses) → all pass** end-to-end: each opens the
  correct selector, lands on the drawer with a summary card, activates a valid
  procedure tab, and writes URL state. (F-5 correctly skips suppressed 사증발급 and
  lands on 체류자격 변경; H-1 — no subcodes — goes straight to the procedure
  selector; G-1-5 resolves to parent G-1.)

The only "failures" encountered during development were over-strict *test*
invariants that surfaced real data patterns (some codes like `D-4-1` are both
standalone records and sub-codes; some sub-codes like `F-2-7S`/`E-7-4R` are
shared by a real status and a special program such as K-STAR/REGION-S). The
resolver handles these correctly (prefer the standalone record, then the first
valid parent); the validation was corrected to assert *reachability*.

---

## 6. Status classification (Step 9 audit, all 42 records)

- **Has meaningful sub-codes:** 29 records. **No sub-codes:** 13 (skip the
  sub-code step). **Has scenario/route wizard:** 9 (F-4, F-6, G-1, F-2, D-10,
  H-2, E-7, D-4, F-1). **Has a one-question route finder:** F-6 (seeded; config
  extensible to others).
- **Procedure data:** every status-like record exposes **≥1 available
  procedure** (no broken/empty result UI anywhere). Procedures present-but-empty
  render as honest `source_limited`.

---

## 7. Document taxonomy relabel (spec item 9) — done

The shared procedure/issuance document groups now use the spec's friendlier,
honest taxonomy instead of bare 공통서류/필수서류 — **display-only, all three
locales, no document re-bucketing, all source references preserved:**

| Internal bucket(s) (data model, unchanged) | Old label | New user-facing label |
| --- | --- | --- |
| `commonDocs` + `requiredDocs` | 기본 준비서류 / 공통서류 | **항상 확인할 서류** (Always-needed documents) |
| `additionalDocs` (+ `conditionalDocs`) | 상황별 추가서류 / 추가서류 | **상황별 추가 서류** (Situation-specific documents) |
| conditional (issuance only) | 해당 시 서류 | 해당 시 서류 (kept — distinct sub-type) |
| discretionary catch-all note | 심사 중 추가 요청 가능 | **기관 확인 필요 서류** (Confirm with the office) |
| fees | (already separated) | rendered in the dedicated fee box (수수료) |

- Changed `docUxGroupLabels` and `issuanceUiLabels` in
  `data/i18n/{ko,en,zh-CN}.json` plus the matching `txAt(...)` fallbacks in
  `index.html`. The four internal buckets (`commonDocs`/`requiredDocs`/
  `additionalDocs`/`conditionalDocs`) are untouched, so
  `audit_duplicate_render_content.py` and `check_required_documents_coverage.py`
  (which operate on the raw data buckets) still pass.
- The existing `docGroupingNote` disclaimer ("화면의 묶음은 이해를 돕기 위한 Paradiso
  분류이며, 원문 매뉴얼의 표현은 자격·절차별로 다를 수 있습니다.") keeps the friendly labels
  honest — they are explicitly Paradiso's reader-facing classification, not a
  claim about official manual headings.

**Still deferred (needs document-level source classification, not a label swap):**
the purely type-based buckets 번역·공증·아포스티유 확인 and 온라인·방문 제출 관련. Fees
(수수료) are already pulled into their own box; 사진/신청서 remain inside 항상 확인할
서류. Splitting translation/submission docs into their own groups would require
re-classifying individual document IDs and is left as a follow-up data pass so it
can be source-reviewed rather than guessed.

## 7b. Earlier deferred items (still open)
- **Route finder coverage.** Only F-6 has a curated question set today (verbatim
  from the spec). The engine is generic — additional statuses are added by
  config only, with no code changes — but new question text must be
  source-reviewed before adding, so other statuses currently use the sub-code
  selector + "공식기관 확인 필요" low-confidence path.
- **`residence_report` / `part_time_work`.** Kept in the approved enum but only
  surfaced where the page actually renders a tab; otherwise they are not shown as
  active choices (no fake content). F-4 거소신고 continues to be served by the
  richer existing F-4 hub, which coexists with the unified CTA.
- **`zh-CN`** strings for the new surface are provided but the platform marks
  Chinese as "preparing"; they will display once the locale is enabled.

---

## 8. Manual QA notes (screenshots captured)

Captured via headless Chromium against a local server:

1. F-6 sub-code selector (desktop, light) — title *"F-6 결혼이민 중 어떤 상황에
   가까우신가요?"*, F-6-1/2/3 with 세부코드 badges + descriptors + "잘 모르겠어요".
2. F-6-1 procedure selector — user labels + official labels + availability
   badges (안내 있음 / 해당 없음 disabled).
3. Result drawer with summary card — F-6-1 · 국민배우자, *현재 선택한 절차: 사증발급*,
   누구에게 해당, and the four action buttons.
4. Route finder (one question at a time).
5. Dark mode sub-code selector (readable).
6. Mobile bottom sheet (procedure selector docked to the bottom).
7. F-4 result card — unified CTA coexisting cleanly with the existing F-4 hub.
