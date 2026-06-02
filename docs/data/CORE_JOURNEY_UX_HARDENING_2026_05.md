# Core Journey UX Hardening (2026-05)

## 1. Purpose

PRs #233–#247 expanded Paradiso with procedure variants, a guided scenario
selector, a selected-scenario checklist, copy/print, a deadline/calendar tool,
route-aware F-4 guidance, an AI source/law-grounding panel, and partial-language
fallback transparency. The product gained many new UI surfaces quickly. This
pass **hardens and polishes the core user journeys** after that expansion: it
makes the surfaces feel coherent, readable, localized, and mobile-usable, and it
locks the behavior in with deterministic tests.

It deliberately does **not** expand the route wizard to F-6/G-1 — that is a later
PR. No grounding semantics, manual sources, scenario data, disclaimers, or
verification flags were changed.

## 2. Core journeys inspected

1. Search **F-4** → choose route → relevant procedures/docs → checklist →
   deadline/calendar → HiKorea/1345 guidance → AI question.
2. Search **H-1** → ask activity-scope/study question → cautious law-grounding /
   source status → no unsupported claims.
3. Search **D-2 / E-7** → procedure descriptions → selected scenario → checklist
   → calendar/reminder.
4. Switch to **English / Simplified Chinese / Traditional Chinese** → repeat one
   complex flow without Korean-only UI chrome (official Korean document names
   excepted).
5. Select a **partial language** → fallback notice instead of silent Korean.
6. **Mobile width** → cards, panels, buttons, and source/status blocks remain
   readable.

## 3. Actual implementation changes made

All changes are in `index.html` (frontend UI/CSS/JS) plus one new test file and
this document. No backend or data files were modified.

### Frontend (`index.html`)

* **Next-action panel localization** — `renderNextActionArea()` previously
  hardcoded Korean strings ("지금 할 수 있는 일", "HiKorea 예약 도우미",
  "구비서류 확인", and three `<small>` descriptions). In English / Chinese modes
  this rendered Korean-only chrome at the top of *every* visa result card. All of
  it is now routed through `tx()` with new keys (`nextActionTitle`,
  `nextActionHikoreaKicker/Title/Desc`, `nextActionDocsKicker/Title/Desc`,
  `nextActionAiKicker/Desc`) translated for ko / en / zh / zh-Hant.
* **F-4 selected-route banner** — `selectF4Route()` now renders a labelled
  `f4-route-selected` banner ("Selected route: <route label>") above the cautious
  route detail, reusing the previously-unused `f4RouteSelectedPrefix` key. The
  selected route is now obvious in *text*, not color alone. Show-all/reset,
  procedure highlighting, and the cautious source notes are unchanged.
* **Source / law-grounding panel readability** — `renderGroundingSourcePanel()`
  gained a plain-language lead line (`gp-lead`, `aiSourcePanelLead`) directly
  under the title, and a reassurance sub-note (`gp-subnote`,
  `lawGroundingReassure`) that attaches *only* to `unavailable` / `disabled` law
  grounding so those states no longer read as a failure of the whole answer.
* **AI modal selected-context banner** — a new `#aiModalContext` note in the AI
  modal. `openAiModal()` fills it with safe labels only (`visa code · procedure
  label · scenario label`) plus a note that only identifiers are sent; it is
  hidden again when no scenario is selected. The `/api/ask` payload is unchanged
  and still sends only `selected_procedure_key` / `selected_procedure_variant_id`
  — never checklist or reminder state.
* **Mobile / accessibility CSS** — new component styles for the elements above,
  plus a consolidated `@media (max-width: 480px)` block that stacks the
  next-action grid, full-widths route chips and scenario choices, single-columns
  the deadline inputs, and gives checklist/calendar action buttons 44px tap
  targets with clean wrapping and no horizontal overflow.

### Tests

* New `backend/tests/test_core_journey_ux_hardening.py` (19 deterministic
  static checks against `index.html`).

### Backend / scripts

* None changed. No backend bug was found during the audit.

## 4. F-4 route UX hardening (Part B)

* Route chooser already renders near the top of the F-4 detail flow (before the
  procedure tabs); unchanged.
* **Selected route is now visually obvious** via the new text banner *and* the
  existing chip `aria-pressed="true"` highlight (not color-only).
* Selecting a route still brings the matching procedure tab/panel forward and
  de-emphasizes (never hides) the others; "Show all F-4 routes" resets.
* Domestic residence report (route 4) wording stays distinct from generic
  foreigner registration ("a domestic residence report, which is distinct from a
  general foreigner registration").
* H-2 → F-4 and B-2/C-3 → F-4 wording still avoids implying automatic approval or
  blanket eligibility ("Selecting a route does not imply eligibility or
  approval"; "another eligible status").
* Works in ko / en / zh / zh-Hant; no raw `manualRefs` / `requiredDocs` exposed.

## 5. Checklist / deadline / action-panel consolidation (Part C)

The action area order on the card is: next-action panel → procedures (with
scenario selector + checklist) → deadline calculator → document tabs → caution →
source-confirmed requirements → source-evidence panel → manual actions.

* The deadline calculator already labels each computed date with an honest
  source-status badge — `deadlineSourceCommonRule` ("Common-rule preparation
  date"), `deadlineSourceCustom` ("Custom reminder") — and the 90-day figure is
  explicitly a *common-rule preparation aid*, never an official per-status
  deadline. Verified and left intact.
* Calendar (ICS + Google) exports already carry cautious DESCRIPTION text
  (`deadlineCalendarCaution`: "Not an official deadline…"). Verified.
* Checklist / reminder state remains **browser-local only**; nothing is sent to
  the backend or AI. Verified by test.
* The new mobile block consolidates the checklist-action and calendar-action
  button rows so they wrap cleanly into comfortable tap targets on phones.

## 6. Source panel readability changes (Part D)

* Plain-language lead summarizing what the answer is based on; "It is not a final
  confirmation."
* `unavailable` / `disabled` law grounding now shows a reassurance sub-note and
  keeps its cautious `state-partial` / `state-disabled` styling — it no longer
  looks like the answer failed.
* `used` law grounding still does **not** imply a final official legal decision
  (the disclosure line is retained).
* Needs-review scenario context stays in its own `state-needs-review` row,
  separate from source-confirmed grounding.
* The panel renders only the safe metadata fields (`visa_code`, `procedure_key`,
  `label`/`variant_id`, `page_range`); raw `requiredDocs` / `manualRefs` / full
  `visa_data` are never surfaced.

## 7. Mobile / accessibility improvements (Part E)

* `@media (max-width: 480px)`: next-action grid → 1 column; route chips and
  scenario choices → full width, 44px min-height; deadline inputs → 1 column;
  checklist/calendar action buttons wrap with 44px tap targets; calendar buttons
  stretch and center.
* Focus-visible rings already exist for route chips, scenario choices, checklist
  buttons, deadline inputs/buttons, and next-action buttons (confirmed by test).
* Route / scenario / checklist selected states use `aria-pressed` /
  `is-selected` classes plus text, not color alone.

## 8. Language fallback / i18n cleanup (Part F)

* All newly introduced strings go through `tx()`; the formerly Korean-only
  next-action chrome is now fully localized.
* New keys added to ko **and** en (required by `scripts/check_i18n.js`) and to zh
  / zh-Hant for the four main languages. `node scripts/check_i18n.js` passes
  (497 keys in en, 497 in ko).
* Partial languages fall back to Korean for the new keys and continue to show the
  existing `partialLanguageNotice` — no silent fallback for full languages.
* Official Korean document names remain Korean (unchanged).

## 9. HiKorea / 1345 action behavior (Part G)

* Confirmed there is **no blocking acknowledgement checkbox** before opening the
  HiKorea guide — `openHikoreaGuide()` opens the modal directly.
* The HiKorea reservation-helper next-action button is now localized, so the
  official-confirmation entry point is visible (but cautious) in all four
  languages.
* External links (Google Calendar, jurisdiction maps, official links) use
  `target="_blank"` with `rel="noopener"` / `rel="noopener noreferrer"`.
* No reservation/application filing is created; Paradiso does not reserve, file,
  approve, or determine jurisdiction.

## 10. AI modal selected-context behavior (Part H)

* The AI modal now shows the selected scenario context as safe labels when a
  scenario was chosen, and hides the banner otherwise.
* Only `selected_procedure_key` / `selected_procedure_variant_id` are sent; local
  checklist completion and reminder state are never included in the payload.
* H-1 / activity-scope questions still trigger law-grounding intent — verified
  live (`sample_would_trigger=True`, `law_grounding_status=disabled`).

## 11. Tests added

`backend/tests/test_core_journey_ux_hardening.py` — 19 static checks:

* next-action panel routed through `tx()`; no inline Korean chrome; labels in
  four languages; HiKorea action title localized.
* F-4 selected-route banner + prefix + label echo; show-all/reset; route titles
  in four languages; domestic-residence wording distinct; no approval implied;
  route→procedure mapping present.
* source panel plain-language lead (four languages); reassurance note bound to
  unavailable/disabled only; scenario/source labels retained; only safe variant
  fields read.
* AI modal `#aiModalContext` present exactly once; populated with safe labels;
  hidden when none; payload sends only identifiers, never checklist/reminder.
* mobile `@media (max-width: 480px)` rules present; focus-visible styles present.
* HiKorea action not gated by a blocking checkbox; calendar links safe.

## 12. Validation results

* `node scripts/check_i18n.js` → OK (497 keys in en, 497 in ko).
* `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` → all valid.
* `python3 scripts/sync_visa_data.py --check` → backend visas match.
* `python3 scripts/check_required_documents_coverage.py` → PASS.
* `python3 scripts/validate_structured_requirements.py …structured_requirements_2026_05.json`
  → valid.
* `py_compile` + `--help` for `smoke_ai_variant_grounding.py`,
  `smoke_ai_all_status_safeguards.py`; `smoke_law_grounding.sh --help` → OK.
* `python3 -m unittest backend.tests.test_core_journey_ux_hardening` → 19 OK.
* `python3 -m unittest discover -s backend/tests` → 438 OK.
* `bash scripts/check_repo.sh` → all regression checks + golden eval passed.
* Local no-provider backend smoke (uvicorn on 127.0.0.1:8000):
  * `smoke_ai_variant_grounding.py` → 28 passed / 0 failed.
  * `smoke_ai_variant_grounding.py --selected-variant-smoke` → 28 passed / 0 failed.
  * `smoke_ai_all_status_safeguards.py` → 58 OK / 0 warnings / 0 failures.
  * `smoke_law_grounding.sh` → disabled/audit-safe mode; H-1 sample triggers
    intent with `attempted=False`; `/api/ask` returns 503 (no provider) with
    `law_grounding_status=disabled`. No secrets printed.

## 13. Known limitations

* The deeper AI modal action-button labels (e.g. "종합 상황 분석 요청") and the
  document-tab stage labels remain Korean-only; they were out of scope for this
  pass and are tracked for a future i18n sweep.
* The route wizard is still F-4-only by design; F-6 / G-1 route-wizard expansion
  is intentionally deferred to a later PR.
* Live AI-answer quality could not be exercised because no LLM provider key is
  configured in this environment (no-provider 503 mode); structural/safeguard
  smokes were run instead.

## 14. Safety note

Route explanations, law grounding, deadline calculations, and checklists are
preparation aids only and do not replace official confirmation by HiKorea, 1345,
or the competent immigration office.
