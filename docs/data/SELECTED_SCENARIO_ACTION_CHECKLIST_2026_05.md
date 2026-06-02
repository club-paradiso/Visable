# Selected Scenario Action Checklist (2026-05)

## 1. Purpose

The guided scenario selector (PR #242) and its localization (PR #244) let a
user pick the procedure variant closest to their situation and hand that
selection to Paradiso AI. This change turns the **selected** scenario variant
into an actionable preparation checklist directly inside the visa detail card.

When a user selects a scenario variant, Paradiso now shows a clearly visible
checklist panel that helps them:

- prepare the documents required for that specific scenario,
- track completed items locally in their own browser,
- copy or print the checklist, and
- move toward the official confirmation / reservation step.

This is a product-flow / UI improvement only. It adds **no** scenario data,
makes **no** backend changes, and does **not** change deterministic manual
grounding semantics. Checked items never imply official approval.

## 2. Checklist behavior

The checklist is rendered inside each variant card's
`.scenario-selected-actions` block (`renderScenarioChecklist()` in
`index.html`), which is only visible when that card is selected. Behavior:

- Items are grouped from the selected variant's normalized `requiredDocs`
  using the four existing document groups: `commonDocs`, `requiredDocs`,
  `additionalDocs`, `conditionalDocs`.
- Group headings reuse the already-localized `docGroupLabels` from PR #244
  (`txAt('docGroupLabels', …)`).
- Each item is a checkbox inside a `<label>` (so the whole label is clickable
  and screen-reader friendly). Empty groups are skipped.
- Official Korean document item text is preserved exactly; it is never
  translated.
- In non-Korean modes the existing procedure-panel note
  (`officialDocumentNamesKoNote`) explains that official document names are
  shown in Korean. This note is unchanged and still rendered above the
  selector/checklist.
- If there is only one variant, its card is selected by default, so the
  checklist is shown immediately. If no variant is selected, the checklist is
  not shown (the whole `.scenario-selected-actions` block is hidden by CSS).
- The checklist degrades gracefully when `requiredDocs` is missing, a group is
  empty, or the variant has no `manualRefs`.

## 3. LocalStorage scope and privacy note

Checkbox state is stored only in the visitor's browser via `localStorage`.

- Storage key prefix: `paradiso:scenario-checklist:`.
- Each item's key is scoped by **visa/status code**, **procedure key**,
  **variant id**, **document group**, and a **stable hash of the item text**:
  `paradiso:scenario-checklist:<visa>:<procedureKey>:<variantId>:<group>:<hash>`.
  Visa/procedure/variant segments are `encodeURIComponent`-escaped.
- Because the key is scoped per variant, switching the selected variant shows
  the correct saved state for that variant only.
- The stored value is just `'1'` for a checked item; unchecked items are
  removed. No document text, personal data, or PII is ever stored — only the
  hashed item key and a checked flag.
- All `localStorage` access is wrapped in `try/catch`; if storage is
  unavailable the checkboxes still toggle in-session, they simply are not
  persisted.
- **Checkbox state is never sent to the backend or AI.** There is no login and
  no server-side state.

## 4. Copy / print behavior

Lightweight actions sit directly under the checklist.

**Copy checklist** (`copyScenarioChecklist()`):

- Builds a plain-text checklist via `buildScenarioChecklistText()` containing
  the visa/status code, localized procedure label, selected scenario Korean
  label, the grouped document list (with `[x]` / `[ ]` markers reflecting the
  current checked state), the source page range when available, the safety
  note, and the confirmation guidance.
- Korean document names are preserved. No raw JSON or internal metadata is
  included.
- Uses the async Clipboard API with a legacy `document.execCommand('copy')`
  fallback. If both are unavailable it shows a localized failure/fallback
  message (`scenarioChecklistCopyFailed`) and never throws.
- Success / failure feedback is announced via an `aria-live="polite"` status
  region.

**Print view** (`printScenarioChecklist()`):

- Renders a print-friendly document into a dedicated `#scenarioChecklistPrintHost`
  container, toggles `body.printing-scenario-checklist`, and calls
  `window.print()`. A small `@media print` rule hides everything except the
  print host so the selected checklist is readable on paper.
- Checked state is shown with `☑` / `☐` glyphs (not colour alone).
- No new dependency is added; cleanup runs on `afterprint` and via a defensive
  timeout for browsers that do not fire it.

## 5. Confirmation / reservation guidance behavior

Below the checklist a small guidance panel reminds the user to confirm before
submitting:

> 제출 전 HiKorea, 1345 또는 관할 출입국·외국인관서에서 실제 적용 여부와 추가서류를 확인하세요.

The selected card also keeps its existing reference note pointing to HiKorea /
1345 / the competent immigration office (PR #242). No new official URLs are
invented and no reservation/filing integration is created — Paradiso cannot
file applications. The guidance reuses the existing HiKorea / 1345 /
immigration-office wording already present in the app.

## 6. AI handoff behavior

The existing selected-scenario AI handoff (PR #242/#244) is unchanged. A new
**secondary** action is added inside the checklist:

> 체크리스트 기준으로 누락 가능성 물어보기 — *Ask AI what might be missing from this checklist*

It reuses `openAiModal()` with a new optional `promptKey` argument
(`scenarioChecklistMissingPrompt`). The request path is identical to the
existing handoff and still sends:

- `selected_procedure_key`
- `selected_procedure_variant_id`
- `visa_data`
- current `lang`

It does **not** send checkbox completion state, personal data, or a separate
raw `requiredDocs` list (those already live inside `visa_data`). The prompt is
deliberately cautious: it asks for *possible* omissions and common mistakes and
explicitly tells the model not to assert final sufficiency or approval.

## 7. Localization coverage

All new UI strings use the existing `UI_TRANSLATIONS` / `tx()` architecture.
Eleven new keys were added to Korean (`ko`), English (`en`), Simplified Chinese
(`zh`), and Traditional Chinese (`zhHant`):

`scenarioChecklistTitle`, `scenarioChecklistCopy`, `scenarioChecklistPrint`,
`scenarioChecklistReset`, `scenarioChecklistConfirmGuidance`,
`scenarioChecklistMissingAsk`, `scenarioChecklistMissingPrompt`,
`scenarioChecklistSafetyNote`, `scenarioChecklistCopied`,
`scenarioChecklistCopyFailed`, `scenarioChecklistSourceLabel`.

English values contain no Hangul (enforced by `scripts/check_i18n.js`). Other
supported languages fall back to Korean via the existing `tx()` fallback until
reviewed translations are added. Official Korean document item text is never
mass-translated.

## 8. Tests added

`backend/tests/test_scenario_procedure_variants.py` gains
`SelectedScenarioActionChecklistFrontendTests` (deterministic HTML-string
checks):

- Korean / English / Simplified / Traditional checklist section labels present.
- Copy, print, and reset labels present in all four languages.
- Confirmation guidance copy present in all four languages.
- Safety note present (and does not imply approval).
- Secondary AI checklist prompt button + template present in all four languages
  and wired through `openAiModal(..., 'scenarioChecklistMissingPrompt')`.
- `localStorage` usage is scoped by visa/procedure/variant/group/item and
  persisted on change (not posted).
- The `/api/ask` request body contains no checklist/checkbox state.
- The selected-scenario payload still includes `selected_procedure_key`,
  `selected_procedure_variant_id`, `visa_data`, and `lang`.
- Source panel scenario wording is unchanged.
- The non-Korean official-document-name note remains present.
- Grouped rendering, accessible labels, non-colour checked state, and the
  clipboard/print resilience paths are present.

Existing backend selected-variant narrowing, no-selection, needs-review
separation, and safe-metadata tests are unchanged and still pass. No change
makes needs-review variants set `grounding_used=true` and no raw fields appear
in metadata (the backend was not modified).

## 9. Validation results

All passed:

- `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json`.
- `populate_scenario_procedure_variants_2026_05.py --check` (24),
  `populate_scenario_procedure_variants_batch2_2026_05.py --check` (15),
  `populate_hard_case_scenario_procedure_variants_2026_05.py --check` (12),
  `populate_remaining_complex_subtype_scenario_variants_2026_05.py --check`.
- `scripts/sync_visa_data.py --check` (canonical / deploy mirror match).
- `scripts/check_required_documents_coverage.py` (no regressions).
- `scripts/validate_structured_requirements.py … structured_requirements_2026_05.json`
  (STRUCTURED_EVIDENCE_READY still 18 — grounding semantics unchanged).
- `py_compile` and `--help` for both AI smoke scripts.
- `node scripts/check_i18n.js` — 432 keys in en, 432 in ko (was 421/421; +11).
- `python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q` —
  86 passed, 66 subtests passed.
- `python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q`
  — 17 passed.
- `python3 -m pytest backend/tests -q` — 325 passed, 66 subtests passed.
- `bash scripts/check_repo.sh` — all regression checks passed.
- Local no-provider HTTP smoke: variant mode 28/28, selected-variant mode
  28/28, all-status safeguard sweep 58 OK / 0 warnings / 0 failures.

A JS syntax compile-check of every inline `<script>` block in `index.html`
reported 0 errors, and a sandbox exercise of `renderScenarioChecklist()` /
copy / print / storage-key logic passed 24/24 assertions.

## 10. Known limitations

- The checklist is a personal reference aid, not an eligibility determination,
  and does not decide which scenario applies to a user.
- Checkbox state is per-browser only (no sync across devices) and is cleared if
  the user clears site storage.
- Official scenario labels and document item text remain Korean because the
  committed data does not provide authoritative translated equivalents; only
  navigation/helper copy is localized.
- Print isolation uses an `@media print` rule plus a print host; very long
  checklists rely on the browser's normal pagination.
- Other supported UI languages reuse the Korean fallback for the new strings
  until reviewed translations are added.

## 11. Safety note

> The checklist is a preparation aid only and does not guarantee acceptance or
> approval.
