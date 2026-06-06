# All-Status Procedure Tabs and Registration Deadline Fix (2026-06)

## Scope

This is a focused hotfix for two regressions:

- Procedure-tab rendering drift, where structured/manual requirements could appear both inside procedure tabs and again as a separate source-confirmed block.
- AI registration-deadline routing, where 외국인등록 / ARC / 입국일 / 90일 이내 questions could fall through to work/activity templates.

D-2 is used only as the observed regression fixture. The implementation is procedure-key driven and status-agnostic.

## Diagnosis Summary

- `renderResults()` mounted `renderProcedures(v, kw)` and then separately mounted `renderSourceConfirmedRequirements(v)`, creating duplicate source-confirmed manual requirements when the selected tab already had documents.
- `getProcedure()` consumed raw procedure docs and legacy fields, but did not consume `sourceConfirmedStructuredRequirements` as the canonical first source.
- A legacy DOM shim injected repeated fee notices after tabs, even though `renderProcedureFeeBox()` already rendered fee information inside each procedure panel.
- The global deadline calculator was mounted for every visa-result card, producing empty or irrelevant deadline blocks.
- AI issue detection treated spaced Korean `외국인 등록` and entry-date wording too weakly; date suffixes like `27일` could contribute to work/activity fallback contamination.

## Rendering Contract

Each status now follows one procedure-tab contract:

- Resolve source-confirmed structured entries by `procedureType -> procedureKey`.
- Merge documents in priority order: source-confirmed structured requirements, committed raw procedure docs, legacy fallback fields.
- Render grouped documents inside the selected procedure tab as common/basic, required, additional/review, and conditional.
- Do not mount a second source-confirmed block after procedure tabs.
- Do not render placeholder document rows such as `문서명 미상` or `비고 정보 없음`.
- Preserve exact sub-code metadata in source references when present.
- Keep visa issuance (`visa_issuance`) separate from domestic stay/residence procedures (`registration`, `extension`, `statusChange`, etc.).

## Attachment Handling

Screenshots were used as visual regression evidence only. Attached HWP/PDF manuals were treated as official-source cross-check material only; implementation authority remained the committed repo data and existing source-manual/structured-requirement files. No screenshots, duplicate manuals, secrets, `.env` files, or temporary files are part of this hotfix.

## Official Documents

Domestic stay/residence procedure application-form lines preserve the official integrated application form label when source-backed:

- `통합신청서(별지 제34호 서식)`

Visa-issuance forms remain separate and are not rewritten into domestic stay forms.

## Fee, Deadline, and Source Lenses

- Generic fee information is labeled as `공통 수수료 참고` / `Common fee reference`.
- Status-specific fee overrides remain available where already committed.
- The legacy fee notice injector is disabled to prevent noisy duplicate fee blocks.
- The automatic global deadline calculator is no longer mounted in every result card.
- Source-confirmed status is shown in the selected procedure panel header instead of as a post-tab duplicate block.
- Raw diagnostics such as `bad_response`, `not_attempted`, `manual: attempted`, and `planned_not_wired` are not rendered by the result-card template.

## Registration Deadline AI

Registration-deadline routing is now signal-based and status-agnostic:

- 외국인등록 / 외국인 등록
- ARC / alien registration / foreigner registration
- 등록 기한 / 등록 언제까지
- 입국일 / date of entry / entered Korea
- 90일 이내 / within 90 days

Business-registration wording remains excluded unless foreigner/ARC registration is also named.

Supported entry-date formats:

- `2026년 2월 27일`
- `2026-02-27`
- `2026.2.27`
- `2026/02/27`

Calculation rule: entry date + 90 calendar days.

Regression fixture:

- Question: `d-2 비자로 들어온 학생은 외국인 등록을 언제까지 해야해? 2026년 2월 27일에 입국했어.`
- Status: `D-2`
- Entry date: `2026-02-27`
- Deadline: `2026-05-28`
- Answer-shape gate rejects work/activity contamination in registration-deadline answers.

Representative statuses covered in tests: D-2, H-1, E-7, F-6, G-1/G-1-5, F-4, H-2, C-3.

## Tests and Validation

Added/updated:

- `scripts/check_static_visa_result_cards.js`
- `backend/tests/test_evidence_backed_answer_gates.py`
- `backend/tests/test_scenario_procedure_variants.py`

Validation run:

- `python3 -m json.tool visa_data.json` passed
- `python3 -m json.tool backend/data/visas.json` passed
- `python3 -m json.tool doc_master.json` passed
- `python3 scripts/sync_visa_data.py --check` passed
- `python3 scripts/check_required_documents_coverage.py` passed
- `python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_06_01.json` passed
- `node scripts/check_i18n.js` passed
- `node scripts/check_ai_shell_semantics.js` passed
- `node scripts/check_static_visa_result_cards.js` passed
- `node scripts/check_deadline_helpers.js` passed
- `python3 -m unittest backend.tests.test_evidence_backed_answer_gates -v` passed
- `python3 -m unittest backend.tests.test_scenario_procedure_variants.ScenarioProcedureVariantAiContextTests.test_unrelated_question_and_parent_registration_do_not_use_variant_context -v` passed
- `python3 scripts/evaluate_paradiso_ai_golden_questions.py` passed
- `bash scripts/check_repo.sh` passed

Pytest validation commands could not run in this local environment because `python3 -m pytest --version` fails with `No module named pytest`. The focused edited test file is `unittest`-based and was executed directly.

`bash scripts/check_repo.sh` required hydrating only tracked source-manual files from Git in the sparse checkout. It warned that `pdfinfo` is unavailable, so page-count verification was skipped inside that script.

## Risks

- The UI now depends on `sourceConfirmedStructuredRequirements` being present on API-enriched records for source-confirmed tab population. Static `visa_data.json` still renders committed raw/legacy procedure data.
- Some source-confirmed public summaries do not expose document-level `conditionKo`; conditional details remain limited to committed data unless the API projection is expanded later.
- `pdfinfo` is not available in this environment, so repo-check page-count verification could not run even after tracked PDFs were hydrated.

## Follow-Ups

- Install/declare pytest in the local validation environment or add a documented unittest fallback for test files that already use unittest.
- Consider projecting source-confirmed document conditions into the public structured-requirements API once product copy is ready to display them cleanly.
- Revisit the legacy document-term shim and move any still-useful official-term normalization into pure render-time helpers.
