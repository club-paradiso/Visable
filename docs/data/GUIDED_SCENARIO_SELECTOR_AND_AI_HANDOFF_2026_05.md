# Guided Scenario Selector & AI Handoff (2026-05)

## 1. Purpose

Procedure variants were already stored under `procedures.<key>.variants[]`,
exposed by `/api/visas`, and available to `/api/ask` through task-worded
routing. This change makes those scenario-specific checklists discoverable in
the visa detail UI and lets a user explicitly narrow Paradiso AI context to the
scenario they selected.

This is a product-flow improvement only. It does not add scenario data, promote
candidate evidence, or change deterministic manual grounding semantics.

## 2. UI behavior

When a procedure has non-empty `variants[]`, `index.html` now renders:

- the guided section label `내 상황에 맞는 시나리오 선택`;
- the explanation `세부 자격·사유에 따라 제출서류가 달라질 수 있습니다. 아래에서 가장 가까운 상황을 선택해 확인하세요.`;
- a keyboard-accessible `<button>` option for each variant, including
  `labelKo`, `statusCode` when present, and a short `scenarioKo` preview;
- an `전체 보기` reset for multi-variant procedures;
- the existing required-document cards for every scenario.

Selecting a scenario visibly marks its button and card, keeps the other cards
visible with reduced emphasis, and shows the selected card's checklist,
cautious note, and AI CTA. A one-variant procedure shows its card as selected
without adding unnecessary selector controls.

The legacy duplicate-document unifier now skips headings already inside
structured procedure grids. This keeps variant-bearing procedure sections
visible while preserving duplicate-summary cleanup for ordinary sections.

The cautious note is:

`선택한 시나리오는 참고용입니다. 실제 적용 여부는 HiKorea, 1345 또는 관할 출입국·외국인관서에서 확인하세요.`

## 3. AI handoff payload fields

The existing embedded AI modal is reused. The selected card CTA
`이 시나리오로 AI에게 질문하기` prefills a question such as:

`{visa_code} {selected variant labelKo} 기준으로 필요한 서류와 주의사항 알려줘`

When the modal is opened from a selected scenario, its existing `/api/ask`
request adds:

- `selected_procedure_key`
- `selected_procedure_variant_id`

The request still includes `visa_data` as before. No raw document list is sent
separately.

## 4. Backend selected-variant narrowing behavior

`backend/paradiso_backend.py` accepts both optional selected-scenario fields.
The procedure variant selector now applies these rules:

- a provided `selected_procedure_key` takes priority over task-detected routing;
- a provided matching `selected_procedure_variant_id` narrows context to that
  one variant;
- a missing or invalid selected variant id produces no scenario context and
  does not crash or broaden to unrelated variants;
- with no selected fields, existing task and sub-code routing is unchanged.

Selected variants remain a compact needs-review prompt block. They never flip
`grounding_used=true`.

## 5. Source panel wording

The embedded AI source panel still uses the needs-review row
`시나리오별 서류 근거` for routed scenario candidates.

When the returned safe metadata contains the variant explicitly handed off
from the selector, the row label becomes `선택한 시나리오 기준` and retains the
cautious wording `매뉴얼 기반 후보 · 최종 확인 필요`.

## 6. Tests added

Deterministic regression coverage now checks:

- selected F-6, G-1, and F-2 variants narrow to only the selected variant;
- invalid selected ids do not crash or leak raw metadata;
- selected variant context does not set `grounding_used=true`;
- generic family, work, and status questions still do not force variants;
- no-selection routing still works;
- selected procedure key-only preference works;
- the frontend contains the selector label, CTA, payload fields, and existing
  source-panel wording.

Existing coverage continues to assert D-2 registration, reentry, batch-1,
batch-2, and hard-case variant exposure.

## 7. Smoke script changes

`scripts/smoke_ai_variant_grounding.py` adds
`--selected-variant-smoke`. In that mode it selects the first variant id under
each discovered routable procedure target, POSTs both handoff fields, and
asserts that returned safe sources contain only that variant id under the
selected procedure key.

Default smoke behavior remains unchanged.

## 8. Validation results

Validation run during implementation:

- `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`, and
  `doc_master.json` -> passed.
- `populate_scenario_procedure_variants_2026_05.py --check` -> passed (24).
- `populate_scenario_procedure_variants_batch2_2026_05.py --check` -> passed (15).
- `populate_hard_case_scenario_procedure_variants_2026_05.py --check` -> passed (12).
- `sync_visa_data.py --check` -> passed.
- `check_required_documents_coverage.py` -> passed.
- `validate_structured_requirements.py ... structured_requirements_2026_05.json` -> passed.
- `py_compile` and `--help` for both AI smoke scripts -> passed.
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q` -> passed (`65 passed, 39 subtests passed`).
- `python3 -m unittest backend.tests.test_scenario_procedure_variants` -> passed
  (`65 tests`).
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q` -> passed (`17 passed`).
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests -q` -> passed (`304 passed, 39 subtests passed`).
- `python3 scripts/smoke_ai_all_status_safeguards.py` -> passed (`58 / 58`).
- Local no-provider HTTP smoke: default variant mode -> passed (`25 / 25`);
  selected-variant mode -> passed (`25 / 25`); all-status safeguard mode ->
  passed (`58 / 58`).
- `bash scripts/check_repo.sh` -> passed (205 unittest checks; golden eval
  `50 / 50`). `pdfinfo` was not installed, so that script reported its existing
  page-count-verification skip warning while still validating the registered
  manual files.
- In-app browser verification -> passed for F-6 detail discovery, visible
  selector/reset state, selected F-6-3 emphasis, F-6-2 de-emphasis, and
  selected-scenario AI modal prefill.

## 9. Known limitations

- Scenario selection is an explicit reference aid, not an eligibility
  determination.
- The selector does not attempt to decide which scenario applies to a user.
- AI narrowing depends on the user selecting the closest card and asking from
  its CTA.
- Scenario document strings remain local catalog transcriptions of committed
  official-manual pages and still require final confirmation.

## 10. Safety note

> Selected scenario variants remain needs-review local manual context and are
> not treated as source-confirmed determinations.
