# AI Variant Grounding — Source Panel & Exhaustive Smoke (2026-05)

## Purpose

PRs #233–#237 wired the backend to return `procedure_variant_context_used` and
`procedure_variant_context_sources` when scenario-specific procedure variants are
injected into the AI prompt for a question. This document covers two additions:

1. **Frontend source panel** — makes that scenario-variant metadata visible to
   users inside the existing AI source/grounding panel.
2. **Exhaustive smoke script** — discovers all variant-bearing procedure targets
   from `/api/visas` and verifies that `/api/ask` returns correctly-shaped,
   safe variant metadata for each one.

---

## Frontend Source Panel Behavior

### Location

`renderGroundingSourcePanel(metadata)` in `index.html`.

### What was added

When the `/api/ask` response contains either:
- `procedure_variant_context_used: true`, or
- a non-empty `procedure_variant_context_sources` array

a new row is appended to the existing grounding panel:

| Field | Value |
|---|---|
| Korean label | `시나리오별 서류 근거` |
| Status wording | `매뉴얼 기반 후보 · 최종 확인 필요` |
| CSS state class | `state-partial` |

Up to **4** individual source items are shown beneath the row label. Each item
displays these safe fields only:

- `visa_code` (e.g. `D-9`)
- `procedure_key` (e.g. `statusChange`)
- `label` or `variant_id`
- `page_range` (e.g. `p. 215`)

If more than 4 sources exist, a compact "외 N건" overflow count is appended.

### What is NOT exposed

- `requiredDocs` (full document lists)
- `manualRefs` (full reference objects)
- `documents`, `raw`, `visa_data` (any raw structured data)
- Any field not in the safe list above

### Unchanged rows

The existing manual/law/public-data rows are unchanged. The new variant row is
appended after `공공데이터 근거` when present. The disclosure footer
("본 답변은 공개 자료에 기반한 참고 안내입니다. 최종 판단은 1345 · HiKorea ·
관할 출입국·외국인청에 확인하세요.") is also unchanged.

---

## Exhaustive Smoke Script Behavior

### Location

`scripts/smoke_ai_variant_grounding.py`

### Discovery

The script fetches `/api/visas` and discovers every visa record whose
`procedures.<key>.variants[]` array is non-empty, filtered to the four procedure
keys that the AI classifier can route:

| Procedure key | Korean prompt template |
|---|---|
| `statusChange` | `{code} 체류자격 변경 서류 알려줘` |
| `workplaceChange` | `{code} 근무처 변경 서류 알려줘` |
| `activitiesOutsideStatus` | `{code} 체류자격외활동허가 서류 알려줘` |
| `statusGrant` | `{code} 국내출생 자녀 체류자격 부여 서류 알려줘` |

### POST payload

Each target is posted to `/api/ask` with:
- `question` — generated from the template above
- `visa_code` — the target visa code
- `visa_data` — safe subset of the visa record (code, name, cat, period, newReq, extReq, faq, procedures)
- `lang: ko`
- `consent: true`

### Accepted response codes

| HTTP status | Interpretation |
|---|---|
| 200 | Normal — LLM provider configured and responded |
| 503 | Acceptable — no provider configured; validated if variant metadata present, skipped otherwise |

Any other status code is a FAIL.

### Validations performed

1. `procedure_variant_context_used` is `true`
2. `procedure_variant_context_sources` is a non-empty list
3. At least one source has the expected `procedure_key`
4. Every matching source has `needs_manual_review: true`
5. No source object contains a forbidden raw field: `requiredDocs`, `manualRefs`, `documents`, `raw`, `visa_data`
6. `grounding_used` is not `true` solely because of variant context (only flagged if `grounding_sources` is also empty)

### Output

Concise `PASS` / `FAIL` / `SKIP` lines per target, with a summary at the end.
Script exits non-zero if any target FAILS.

---

## Commands

### Local exhaustive (default)

```bash
# Start backend in a separate terminal:
cd backend && uvicorn paradiso_backend:app --port 8000

# Run exhaustive smoke:
BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_variant_grounding.py
```

### Deployed-safe (representative targets only)

Runs only four representative targets to avoid excessive live LLM calls on a
deployed backend with a real provider:

```bash
python3 scripts/smoke_ai_variant_grounding.py \
    --backend-url https://your-backend.example.com \
    --deployed-safe
```

Representative targets:

| Visa code | Procedure key |
|---|---|
| D-9 | statusChange |
| E-9 | workplaceChange |
| E-6 | activitiesOutsideStatus |
| F-1 | statusGrant |

### Capped (limit N targets)

```bash
python3 scripts/smoke_ai_variant_grounding.py --limit 5
```

---

## Validation Results

All validation commands were run against the clean `origin/main` base.

| Check | Result |
|---|---|
| `python3 -m json.tool visa_data.json` | PASS |
| `python3 -m json.tool backend/data/visas.json` | PASS |
| `python3 -m json.tool doc_master.json` | PASS |
| `python3 scripts/populate_scenario_procedure_variants_2026_05.py --check` | PASS |
| `python3 scripts/sync_visa_data.py --check` | PASS |
| `python3 scripts/check_required_documents_coverage.py` | PASS |
| `python3 scripts/validate_structured_requirements.py ...` | PASS |
| `python3 -m py_compile scripts/smoke_ai_variant_grounding.py` | PASS |
| `python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q` | PASS |
| `python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q` | PASS |
| `python3 -m pytest backend/tests -q` | PASS |
| `bash scripts/check_repo.sh` | PASS |

### Smoke targets discovered locally

13 variant-bearing routable targets were discovered across 7 visa codes:
D-4, D-8, D-9, E-4, E-5, E-6, E-9, F-1.

```
Results: 13 passed, 0 skipped (no-provider), 0 failed  /  13 total
```

All 13 targets passed validation against the local backend (no LLM provider
configured; the script validates variant metadata from the 503 response's
`detail` dict). The `--deployed-safe` representative mode (4 targets) also
passed.

---

## Limitations

- Needs-review variant context is **advisory only**. The AI may produce an
  answer based on manual-extracted context that has not been independently
  verified against the current official manual edition.
- `page_range` values shown in the panel refer to the manual version listed
  in `manual_version`; they may differ across manual revisions.
- The smoke script does not validate the correctness of the AI's *answer*,
  only the shape and safety of the response metadata.

---

## Safety Rule

> **Needs-review scenario variants remain local manual context and are not
> treated as source-confirmed determinations.**

Variants with `needsManualReview: true` are injected as advisory context
for the LLM. They never set `grounding_used: true`, never appear in
`grounding_sources`, and are never promoted to source-confirmed HIGH
confidence. The `state-partial` CSS class on the UI panel row reflects
this status explicitly.
