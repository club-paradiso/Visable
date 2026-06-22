# Unified Complex-Status Guide — F-4 reference implementation (2026-06)

Turns the fragmented "complex status" guidance (several competing CTAs → small
central modal → disconnected procedure/subcode/document cards) into one unified
pattern, with **F-4 (재외동포) as the complete reference implementation**:

```
status search/detail
  → ONE dominant primary CTA ("내 F-4 준비경로 확인하기")
    → full-screen / wide guided flow (one main question per step)
      → personalized, checklist-first result
        → official source / evidence panel
```

This is a **reusable** layer (`window.ParadisoComplexGuide.register/open`), not an
F-4-only patch. Protected data files (`visa_data.json`,
`backend/data/visas.json`, `doc_master.json`) were **not** modified. No
immigration content was invented — every document/step/source is reused from the
existing source-grounded `data/f4/*.json`; anything not source-backed is shown as
**"공식근거 확인 필요"**.

---

## 1. Summary

F-4 previously exposed **four** competing guide entry points that confused users:

1. `#f4RouteGuide` entry-panel CTA *"F-4 절차 확인하기"* (f4-route-guide.js)
2. In-card *"🧭 F-4 절차 확인하기"* (f4-route-guide.js `injectCardCta`)
3. Generic *"상황·절차별로 안내받기"* (visa-route-guide.js `injectCardCtas`)
4. In-card `.f4-route-wizard` route picker (index.html `renderF4RouteChooser`)

Guidance then continued inside a **640px central modal** with a single long
scroll. This PR collapses all of that into **one dominant primary CTA** that
opens a **full-screen / wide** guided preparation flow with **one question per
step** and a **checklist-first** result connected to the official sources.

## 2. Complex-status audit (Level A/B/C)

| Status | Current guidance | Level (this PR) |
| --- | --- | --- |
| **F-4** | Dedicated diaspora hub + 3 duplicate CTAs + 640px modal | **A — complete** reference implementation (full-screen flow, checklist result, single CTA) |
| F-6 | `ROUTE_WIZARD_CONFIG` route picker **+** generic CTA **+** seeded one-question route-finder | **C** (best next candidate → B/A; route-finder data already exists) |
| G-1 | `ROUTE_WIZARD_CONFIG` route picker + generic CTA (G-1-5 is a subcode, never top-level) | **C** |
| E-7 | `ROUTE_WIZARD_CONFIG` route picker + generic CTA + employment-code helper | **C** |
| F-2 / D-10 / H-2 / D-4 / F-1 | `ROUTE_WIZARD_CONFIG` route picker + generic CTA | **C** |
| F-5 (영주) | Subcodes + generic CTA; 사증발급 correctly suppressed (not_applicable) | **C** (simpler flow; no bespoke wizard today) |
| D-2 / C-3 / D-8 / E-2 / E-9 | Subcodes + generic CTA (+ D-2 student journey) | **C** |

F-4 is the only status whose preparation content (`data/f4/*.json`) is fully
source-graded and country-aware, which is why it is the safe Level-A target. The
others keep their existing systems unchanged in this PR and are *register-ready*
for the new engine (see §7).

## 3. Files changed

| File | Change |
| --- | --- |
| `assets/js/f4-route-guide.js` | **Rewritten** into a config-driven `ParadisoComplexGuide` engine (full-screen overlay, one-question-per-step, checklist-first result, focus trap/ESC/restore, progress, trilingual-safe chrome) **+ F-4 reference config**. Reuses the existing `data/f4` content and the hub/country/FAQ renderers (now used as "reference" views). `computeRoute` kept verbatim (back-compat). New `computeF4Path` maps the new flow answers → a route. Removed the duplicate in-card `injectCardCta`. |
| `assets/js/visa-route-guide.js` | Suppress the generic *"상황·절차별로 안내받기"* in-card CTA for **F-4** only (its dedicated guide owns that journey). All other statuses unaffected. |
| `index.html` | `renderF4RouteChooser` now returns `''` for **F-4** only, removing the in-card route-wizard for F-4 (config + i18n keys kept intact for the other statuses). |
| `scripts/check_f4_route_guide.mjs` | Updated the UI-contract assertions to the new unified design; **all legal/safety assertions preserved** (거소증 separation, 90-day deadline, military/nationality cautions, US-terms confinement, source-ref resolution, no-guarantee wording). Added assertions + `computeF4Path` routing cases. |
| `scripts/check_f4_guide_flow.mjs` | **New.** Offline end-to-end harness: drives the real step renderer + result-model builder against `data/f4/*.json` so every flow path is checklist-first, source-grounded, and never invents documents (81 checks). |
| `scripts/check_repo.sh` | Wired the new flow check into step `[9c/14]`. |

## 4. F-4 CTA consolidation

- **Removed:** in-card *"🧭 F-4 절차 확인하기"* panel (`injectCardCta` deleted).
- **Suppressed for F-4:** the generic *"상황·절차별로 안내받기"* in-card CTA and the
  `.f4-route-wizard` in-card route picker.
- **Kept as the single dominant entry:** the `#f4RouteGuide` hero, now showing the
  header *"F-4 재외동포 체류자격 안내"*, the spec description, **one** filled primary
  CTA *"내 F-4 준비경로 확인하기 / Check My F-4 Preparation Path"*, and four
  visually-weaker secondary actions (전체 세부자격 / 공통서류 / 신청 절차 / 공식 근거).

## 5. New F-4 guided flow (one question per step)

Full-screen (mobile) / wide sheet (desktop) overlay with title, **step counter**,
**progress bar**, **Back / Next**, **Close**, focus trap, ESC, and focus restore.

1. *현재 어떤 상황에 가까우신가요?* (apply abroad / change in Korea / already F-4
   extension / residence registration / **잘 모르겠어요**)
2. *본인 또는 가족의 대한민국 국적 이력이 있나요?* (self previously held /
   parent–grandparent / **잘 모르겠어요** / 해당 없음)
3. *현재 어디에 있나요?* (in Korea / outside Korea / **잘 모르겠어요**)
4. *지금 필요한 절차는 무엇인가요?* (사증발급 / 체류자격변경 / 기간연장 / 거소신고 /
   **잘 모르겠어요**)
5. *추가 확인이 필요할 수 있는 항목* — optional multi-select (nationality loss,
   family proof, criminal record, military, apostille, translation), cautious
   wording *"추가 확인이 필요할 수 있습니다"*.

## 6. F-4 result screen (checklist-first)

Top title *"당신에게 가까운 F-4 준비경로"* + a cautious route chip
(*해외 F-4 사증 신청 검토 경로* / *한국 내 F-4 체류자격변경 검토 경로* /
*F-4 기간연장/변경 준비 경로* / *거소신고 준비 경로* / official-confirmation path).
Sections, all from existing data:

1. **먼저 해야 할 일** — route `checkFirst` chips + source-backed warnings.
2. **기본 준비서류** — a real **checkbox checklist** from `base.hub.*` docs;
   routes with no source-backed list (extension / official-check) show a
   *"공식근거 확인 필요"* note instead of invented docs.
3. **내 상황에서 추가될 수 있는 서류** — the Step-5 selections, each mapped to the
   matching source-backed note (criminal record / military / nationality /
   apostille / translation) or flagged *"공식근거 확인 필요"* (family proof).
4. **신청 절차** — source-backed steps where present, otherwise the generic
   process list (prepare → reserve → submit → review → result → follow-up).
5. **공식 근거** — resolved from `data/f4/sources.json` with dates + links (never
   a fake citation).
6. **다음 행동** — Copy checklist, View document details, HiKorea reservation,
   Check jurisdiction office, Restart.

Plus the Korean-national caution (when nationality is self-held / unsure), the
official-check warning, and the safety note *"개별 사안, 관할 출입국기관 또는
재외공관 판단에 따라 추가서류가 요구될 수 있습니다."*

## 7. Component architecture

A reusable engine — `window.ParadisoComplexGuide` — was created:

```js
ParadisoComplexGuide.register(code, {
  code, ensureData(), title(), steps:[{ id, type, qKey, options:[{id,key,unsure?}] }],
  computeResult(answers), refViews:[...]
});
ParadisoComplexGuide.open(code, { ref });   // flow, or jump to a reference view
```

The engine owns the overlay chrome, step navigation, progress, focus management,
a11y, and the checklist-result primitives. **F-4 registers the first config**;
other statuses adopt the same shape (Level C → B/A) without touching the engine.

## 8. Other complex statuses

No behavior change in this PR (honest Level C): F-6, G-1, F-2, D-10, H-2, E-7,
D-4, F-1 keep the existing `ROUTE_WIZARD_CONFIG` picker; F-5/D-2/C-3/D-8/E-2/E-9
keep the subcode + generic CTA. They are *register-ready* for the new engine.
**F-6 is the recommended next migration** (it already has a curated one-question
route-finder in `visa-route-guide.js` plus F-6-1/2/3 descriptors), so its
full-screen flow can be built without inventing content.

## 9. i18n

All new chrome lives in the module's paired KO/EN `STR_KO`/`STR_EN` packs
(parity enforced by `check_popup_i18n.mjs`); no `data/i18n` keys were added or
removed (ko/en/zh-CN parity preserved — 1076 keys). Per the repo fallback policy
and the platform's "Chinese preparing" status, zh-CN chrome resolves to Korean
canonical rather than low-quality machine text. New keys include: `primaryCta`,
`guideHeader`, `guideIntro`, `secView*`, `step*Q`, `optUnsure`, `opt*`, `conf*`,
`mayRequireConfirm`, `officialSourceNeedsConfirm`, `resultTitle`, `resFirstSteps`,
`resBasicDocs`, `resAdditionalDocs`, `resProcedure`, `resSources`, `resNextActions`,
`copyChecklist`, `restartShort`, `safetyNote`, `routeLabel*`, `procStep*`.

## 10. Accessibility / responsive

`role="dialog"` + `aria-modal`, `aria-labelledby`, a `progressbar` with live
`aria-valuenow`, radio/checkbox roles with `aria-checked`/`aria-pressed`, a Tab
focus-trap (with `shiftKey`), ESC-to-close, focus moved into the flow on open and
**restored to the trigger on close**. Options are ≥56px tall; footer controls
≥48px. The overlay is a wide sheet on desktop (`min(960px, 100%)` × `min(760px,
94vh)`) and **full-screen** at ≤640px (no double-scroll, no horizontal overflow).
CSS uses the shared `--bg/--t/--ac/...` theme tokens, so **civic_editorial** and
**archive_diary** (and dark) are covered automatically.

## 11. Tests run

- `node scripts/check_f4_route_guide.mjs` → **116/116** (legal guardrails intact +
  new unified-guide contract + `computeF4Path` routing).
- `node scripts/check_f4_guide_flow.mjs` → **81/81** (real step renderer +
  result-model over `data/f4/*.json`; no undefined, source-grounded, nothing
  invented).
- `node scripts/smoke_f4_hub.mjs` → 59/59 · `check_popup_i18n.mjs` OK ·
  `check_i18n.js` OK (1076 keys) · `check_visa_route_guide.mjs` 127/127 ·
  `check_visa_issuance_ui.mjs` 2846/0 · `check_subcode_modal.mjs` OK ·
  `check_dummy_text.mjs` OK · `smoke_static_i18n.mjs` OK.
- `bash scripts/check_repo.sh` → **Success** (incl. 251 + 26 backend tests via the
  bootstrapped venv; golden eval requires network and is the only skipped step).

## 12. Remaining risks / honest gaps

- **Browser QA** could not run offline (no jsdom/Chromium); the new
  `check_f4_guide_flow.mjs` is the offline stand-in (it executes the real render +
  result logic). A real-browser pass at 360/390/430/768/1280px is recommended
  before release.
- **Extension route** has no source-backed F-4 document list; it intentionally
  shows the stay-limit note + *"공식근거 확인 필요"* rather than guessing.
- Other complex statuses still have route-wizard **+** generic-CTA duplication;
  this PR only consolidated F-4. Migrating them is follow-up work.

## 13. Recommended next PR

Migrate **F-6** to a Level-A/B `ParadisoComplexGuide` config (reuse the existing
F-6 one-question route-finder + F-6-1/2/3 descriptors + the subcode procedure
data), and suppress its duplicate route-wizard / generic CTA the same way F-4 was
consolidated. Then iterate to G-1, E-7, F-2 — each as a config, no engine change.
