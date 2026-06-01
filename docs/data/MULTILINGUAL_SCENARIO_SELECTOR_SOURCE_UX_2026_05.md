# Multilingual Scenario Selector and Source UX (2026-05)

## 1. Purpose

This change makes the guided scenario selector, document-group presentation,
selected-scenario AI handoff, and embedded AI source panel understandable in
Korean, English, Simplified Chinese, and Traditional Chinese modes.

It is a targeted UI localization change. It does not add scenario variants,
change manual grounding semantics, or translate official Korean document lists.

## 2. Localized UI strings

The existing `UI_TRANSLATIONS` dictionary in `index.html` now covers:

- scenario selector title, explanatory copy, selected state, and `Show all`
- selected-scenario reference disclosure and AI handoff CTA
- procedure-key labels and document-group labels in Chinese modes
- source panel title, source categories, verification states, advisory fallback,
  technical-details label, and final-confirmation disclosure
- source-panel badge labels such as `Source present`, `Needs review`, and
  `Reference`

Korean remains the source and fallback language. English and Chinese copy is
cautious and keeps the distinction between reference guidance and official
determination visible.

## 3. Official Korean terms

Scenario variants currently store official labels and document items in Korean.
The UI preserves those values without destructive translation.

Non-Korean modes show a short note:

- English: `Official document names are shown in Korean to match the immigration manual.`
- Simplified Chinese: `为与出入境手册一致，正式材料名称以韩文显示。`

Scenario cards also explain that official scenario labels remain in Korean.
Translated helper text is presented only as navigation assistance.

## 4. Selected-scenario AI handoff

The selected-scenario CTA continues to send:

- `selected_procedure_key`
- `selected_procedure_variant_id`
- `visa_data`
- current `lang`

It does not send raw `requiredDocs` separately. The prefilled user question now
uses the active UI language:

- Korean asks for documents and cautions based on the selected Korean label.
- English asks for required documents and key cautions and requests Korean
  official document names where relevant.
- Chinese asks for required materials and cautions and requests retention of
  Korean official material names where relevant.

## 5. Source panel localization and safety wording

The embedded source panel now localizes:

- administrative manual source
- scenario-specific document source
- selected-scenario basis
- manual-based candidate / final-confirmation-needed state
- general advisory fallback
- law and public-data source states
- 1345, HiKorea, and competent immigration-office disclosure

Needs-review scenario variants remain visually separate from deterministic
manual grounding. The source panel still exposes only safe metadata fields and
does not expose raw `requiredDocs`, `manualRefs`, or `visa_data`.

## 6. Tests added

`backend/tests/test_scenario_procedure_variants.py` now checks:

- Korean selector fallback remains present
- English and Chinese selector labels and AI CTAs are present
- English and Chinese Korean-document-name notes are present
- English and Chinese selected-scenario prompt templates are present
- selected-variant payload fields and current language remain wired
- Korean, English, and Chinese source-panel labels are present
- localized source badge CSS variables and localized procedure-key rendering
  remain wired

Existing backend tests continue to cover selected-variant narrowing,
no-selection behavior, needs-review grounding separation, and safe metadata
shape.

## 7. Validation results

Passed:

- JSON validation for `visa_data.json`, `backend/data/visas.json`, and
  `doc_master.json`
- batch-1, batch-2, hard-case, and remaining-complex-subtype population helpers
  with `--check`
- `scripts/sync_visa_data.py --check`
- `scripts/check_required_documents_coverage.py`
- structured-requirements validation
- smoke-script compilation and `--help`
- `node scripts/check_i18n.js` (`421` English keys and `421` Korean keys)
- `python -m pytest backend/tests/test_scenario_procedure_variants.py -q`
  (`72 passed, 66 subtests passed`)
- `python -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q`
  (`17 passed`)
- `python -m pytest backend/tests -q` (`311 passed, 66 subtests passed`)
- `bash scripts/check_repo.sh`
- local no-provider variant smoke (`28 passed, 0 failed`)
- local no-provider selected-variant smoke (`28 passed, 0 failed`)
- local HTTP all-status safeguard sweep (`58 OK, 0 warnings, 0 failures`)
- local browser sanity check for English and Simplified Chinese selector,
  document-group, Korean-term note, CTA, and selected-scenario prefill rendering

## 8. Known limitations

- Official scenario labels and document item text remain Korean because the
  committed data does not provide authoritative translated equivalents.
- Other supported UI languages continue to use the existing Korean fallback for
  the newly added helper strings until reviewed translations are added.
- `ai.html` remains a separate standalone chat entry point. The guided selector
  and selected-variant handoff continue to use the embedded AI modal in
  `index.html`; no second AI interface was introduced.

## 9. Safety note

Translated helper text is for usability only; official Korean manual terms remain authoritative.
