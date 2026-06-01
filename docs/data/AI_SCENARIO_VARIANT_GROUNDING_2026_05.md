# AI Scenario Procedure Variant Context — 2026-05

## Why This PR Exists

PR #233 added backward-compatible `procedures.<key>.variants[]` support. PR #234
populated 24 official-manual-backed scenario and sub-code records. The UI and
`/api/visas` could expose those records, but `/api/ask` still injected only a
small local catalog summary. The AI prompt did not receive the labeled variant
scenarios or their document groups.

This PR adds a compact, task-filtered needs-review context block so AI answers
can use those local manual-backed records without presenting them as final
official determinations.

## Trust Boundary

Scenario procedure variants remain a separate advisory layer:

| Layer | Trust level | Effect on `grounding_used` |
|---|---|---|
| Deterministic stay-manual grounding fixture | Existing verified fixture path | May set `grounding_used=true` |
| HIGH / `STRUCTURED_EVIDENCE_READY` structured requirements | Source-confirmed additive block | Does not change existing grounding selection |
| Scenario procedure variants | Manual-backed local catalog context with `needsManualReview: true` | Never sets `grounding_used=true` |

The new block is labeled:

`[Manual-backed local procedure variant context — needs review]`

It explicitly instructs the model:

- Scenario checklists apply only when the labeled scenario matches the user's
  facts.
- Do not generalize a variant to every user under the parent visa.
- If facts do not match, say that the checklist may not apply.
- Do not invent missing documents, deadlines, fees, or legal citations.
- Verify the applicable checklist with HiKorea, 1345, or the competent
  immigration office.

## Backend Helpers

`backend/paradiso_backend.py` adds:

- `_procedure_variant_key_for_task()`
- `_select_procedure_variants()`
- `_build_procedure_variant_context_block()`
- `_procedure_variant_context_sources()`

Selection behavior:

- Read only `visa_data.procedures`.
- Select variants only from the procedure matching the detected task.
- Prefer an exact `statusCode` match when a payload sub-code is present.
- Otherwise include at most three visibly labeled scenario options.
- Ignore empty or explicitly unavailable variants.
- Cap rendered document items and field lengths to prevent prompt bloat.

The frontend `detected_code` payload hint is considered before the parent
`visa_data.code`, allowing an `ai.html` sub-code match to narrow the variant
selection.

## Task Mapping

| Detected task type | Procedure key |
|---|---|
| `status_change` | `statusChange` |
| `workplace_change` | `workplaceChange` |
| `activities_outside_status` if detected by a future classifier expansion | `activitiesOutsideStatus` |
| `family_status_change` with explicit birth or status-grant wording | `statusGrant` |

A vague family-status question does not pull child-specific `statusGrant`
variants into the prompt.

Registration remains on its existing parent-level path and does not select
scenario variants. This PR intentionally leaves the existing task detector
surface unchanged for registration and outside-status questions; the
`activitiesOutsideStatus` mapping is ready for a later classifier expansion.

## Prompt Assembly

`/api/ask` appends the needs-review variant block after the existing local
catalog context and before the source-confirmed structured-requirements block.

- Deterministic manual grounding remains primary when present.
- HIGH / `STRUCTURED_EVIDENCE_READY` semantics remain unchanged.
- No matching variant means no new block and no behavior change.

`ai.html` already sends `procedures` in its compact local record. The embedded
AI modal in `index.html` now forwards `visa.procedures` as one additive payload
field so the existing change/workplace AI route can benefit too.

## Response Metadata

`AskResponse` adds optional backward-compatible fields:

- `procedure_variant_context_used: bool`
- `procedure_variant_context_sources: List[Dict[str, Any]]`

Each source summary contains safe metadata only:

- `visa_code`
- `procedure_key`
- `variant_id`
- `label`
- `status_code`
- `page_range`
- `manual_name`
- `manual_version`
- `needs_manual_review`

Full document lists and notes are not duplicated into response metadata. They
remain public through the existing `/api/visas` catalog.

## Tests

Focused regression coverage verifies:

- D-9 status-change context.
- E-9 workplace-change context.
- Exact D-8-4 sub-code preference.
- E-6 outside-status mapping readiness without changing existing detector
  semantics.
- Conservative F-1 status-grant selection.
- No context for unrelated questions.
- Existing D-2 deterministic extension grounding remains independent.
- `grounding_used` stays false for needs-review-only context.
- Safe metadata shape on the no-provider 503 response.
- Actual prompt appending through a patched provider call.
- Existing parent-level D-2 registration, PR #232 re-entry data, variant
  rendering, population replay, and sync checks remain covered.

## Validation

Run:

```text
python3 -m json.tool visa_data.json
python3 -m json.tool backend/data/visas.json
python3 -m json.tool doc_master.json
python3 scripts/populate_scenario_procedure_variants_2026_05.py --check
python3 scripts/sync_visa_data.py --check
python3 scripts/check_required_documents_coverage.py
python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_05.json
python3 -m pytest backend/tests -q
bash scripts/check_repo.sh
```

Results:

- JSON validation passed for `visa_data.json`, `backend/data/visas.json`, and
  `doc_master.json`.
- Curated population replay, canonical/deploy sync, required-document coverage,
  structured-requirement validation, and record-store parity checks passed.
- Focused scenario-variant tests passed: `24 passed`.
- Full backend tests passed: `263 passed`.
- Golden evaluation passed: `45 passed, 0 failed`.
- `bash scripts/check_repo.sh` passed, including its bundled backend regression
  run and golden evaluation.
- `bash scripts/smoke_frontend_accessibility.sh` was attempted but could not
  fetch the deployed GitHub Pages site because sandbox DNS resolution is
  blocked. The required network escalation was also rejected by the environment
  approval quota. The deterministic frontend payload assertion passed.

## Known Limitations

- Variant context depends on the frontend sending the matching local catalog
  record. Requests without `visa_data.procedures` remain unchanged.
- Free-text visa sub-codes are not treated as binding declarations. Exact
  sub-code preference uses explicit payload metadata.
- The helper includes only a small scenario option set to limit prompt size.
  The model must ask for clarifying facts when the shown options do not settle
  applicability.
- Variants retain `needsManualReview: true`; this PR does not promote them into
  deterministic manual grounding or source-confirmed structured requirements.

## Safety Note

Scenario procedure variants are injected as needs-review local manual context,
not as final source-confirmed determinations.
