# Record Store Runtime Wiring — E-4A Report

**Date:** 2026-05-25
**PR:** data: wire record store union runtime e4a
**Preceded by:** PR #174 (data: alias-deprecate scenario help records e3)
**Branch:** data/wire-record-store-union-runtime-e4a

---

## Summary

This is PR E-4A: runtime union resolver wiring and parity proof.

- No records were deleted from visa_data.json.
- No legal or admin content was changed.
- No UI changes were made.
- `removalFromVisaDataAllowed` remains false for all 17 alias-deprecated records.
- Runtime behavior is preserved: `/api/visas` returns the same 58 records.
- Simulated E-4B deletion parity: GREEN.

---

## Changed Files

| File | Change type |
|------|-------------|
| `backend/record_store_union.py` | **NEW** — importable union resolver adapter for backend |
| `backend/paradiso_backend.py` | **MODIFIED** — `_load_visas()` wired to union resolver (E-4A) |
| `backend/tests/test_paradiso_backend.py` | **MODIFIED** — 11 new E-4A parity tests added |
| `scripts/resolve_record_store.py` | **MODIFIED** — added simulate-e4-removal mode, updated docstring |
| `scripts/check_record_store_union_parity.py` | **MODIFIED** — added `--simulate-e4-removal` check |
| `docs/data/2026_05_21_RECORD_STORE_RUNTIME_WIRING_E4A_REPORT.md` | **NEW** — this file |
| `docs/data/2026_05_21_record_store_runtime_wiring_e4a_report.json` | **NEW** — machine-readable report |

---

## Backend Runtime Status

**Status: WIRED to union resolver**

- `backend/record_store_union.py` wraps `scripts/resolve_record_store.py` via sys.path injection.
- `_load_visas()` in `paradiso_backend.py` now tries `record_store_union.load_union_view()` first.
- Falls back to path-based loading gracefully if the resolver module is unavailable.
- `source_type` in `/api/visas` response is now `"union-resolver"` when the union path is used.
- `/api/visas` compatibility: **PRESERVED** — same 58 records, same shape, no warning field added.
- Data path: `visa_data.json` (via `scripts/resolve_record_store.py` → `union_view()`) + `data/scenario_help_records.json` (shadow; de-duplicated).

---

## Frontend Runtime Status

**Status: BEHAVIOR-COMPATIBLE via API (frontend wiring deferred — E-4A.2)**

- `index.html` was not modified.
- Frontend loads from `${API_BASE}/api/visas` (primary) or `./visa_data.json` (static fallback).
- Since the backend `/api/visas` is now union-resolver-backed and returns the same 58 records, the frontend behavior is automatically behavior-compatible.
- Direct static fallback (`./visa_data.json`) is unchanged and unaffected by this PR.
- Reason for deferral of explicit frontend wiring: the union output equals visa_data.json today; no frontend code change is needed to preserve behavior. E-4A.2 would add an explicit data-loading abstraction in index.html if needed post-E-4B.

---

## AI Context Status

**Status: BEHAVIOR-COMPATIBLE — migrationMeta does not leak**

- `_build_visa_data_context_block()` extracts only specific fields from visa_data records.
- `migrationMeta` is never included in the context block (field not in the extraction list).
- Tests added proving migrationMeta and its sub-fields are absent from AI context blocks and ungrounded prompts.
- AI path reads records from the union resolver (same content, same user-facing fields).
- No policy-sensitive wording was changed.

---

## Record Counts

| Metric | Count |
|--------|-------|
| visa_data.json records | 58 |
| scenario_help_records.json (shadow) | 17 |
| Union count | 58 |
| Simulated E-4B removal union count | 58 |
| Alias-deprecated (E-3 markers) | 17 |

---

## Duplicate Handling

| Code | Type | Status |
|------|------|--------|
| D-4-2K | Pre-existing duplicate in visa_data.json (indices 24 & 55) | **Preserved unchanged** — not alias-deprecated; deferred to D-content track |
| 17 shadow codes | Alias-deprecated in visa_data.json; shadow copies in scenario_help_records.json | **De-duplicated by union resolver** — visa_data copy is canonical during E-4A |

The union resolver uses `(array_index, code)` keying; D-4-2K duplicate is preserved exactly.

---

## Overstay Parity

| Code | Description | Status |
|------|-------------|--------|
| SCN-6 | Overstay scenario | Present exactly once in union |
| OVS-1 | Overstay risk country | Present exactly once in union |
| FAQ-4 | Overstay FAQ | Present exactly once in union |

Golden question stability: not degraded. Overstay records remain queryable. Backend tests assert each overstay code appears exactly once.

---

## Direct Search / Keyword Search Status

- Search operates on the records returned by `/api/visas` or the static `visa_data.json`.
- Since union == visa_data.json, search behavior is unchanged.
- Keyword chip and result card copy unchanged.
- No search ranking changes.

---

## migrationMeta Visibility

| Surface | Visible? | Notes |
|---------|----------|-------|
| `/api/visas` API response | YES — present in raw records | migrationMeta is in visa_data.json records; returned as-is. Not user-facing in the UI. |
| AI context block (`_build_visa_data_context_block`) | NO | Field extraction list does not include migrationMeta. Tests added. |
| AI ungrounded prompt | NO | Prompt builder does not read migrationMeta. Tests added. |
| Frontend-visible fields | NO | Frontend renders nameKo, nameEn, summary, etc. Not migrationMeta. |

---

## No Records Deleted

**CONFIRMED: No records were deleted from visa_data.json.**

All 58 records remain. The 17 alias-deprecated records (carrying `migrationMeta`) remain in visa_data.json with `removalFromVisaDataAllowed: false`.

---

## removalFromVisaDataAllowed

**REMAINS FALSE for all 17 alias-deprecated records.**

No records have `removalFromVisaDataAllowed` set to true in this PR. Deletion is gated to E-4B after all E-4A parity gates are proven.

---

## Simulated E-4B Removal Result

Command: `python3 scripts/resolve_record_store.py --check --simulate-e4-removal`

Result:
```
[resolve_record_store] OK - simulated-E4-removal parity GREEN
(sim==58==visa_data; deprecated_removed=17; user-facing content parity: PASS;
no new dup codes; migrationMeta intentionally absent).
```

Command: `python3 scripts/check_record_store_union_parity.py --simulate-e4-removal`

Result:
```
[check_record_store_union_parity] simulate-e4-removal GREEN
- sim=58==visa_data=58; deprecated=17 removed+replaced; content parity: PASS;
D-4-2K dup preserved; E-4B deletion safe.
```

Note: migrationMeta is intentionally absent from shadow records (it is an E-3 alias-deprecation marker added only to visa_data.json; not user-facing content).

---

## Validation Results

All checks ran and passed:

```
python3 scripts/resolve_record_store.py --check
→ OK - E-4A invariants hold (union==58==visa_data; shadow=17; no new dup codes; pre-existing dup=['D-4-2K']).

python3 scripts/resolve_record_store.py --check --simulate-e4-removal
→ OK - simulated-E4-removal parity GREEN

python3 scripts/check_record_store_union_parity.py
→ OK - union=58 == visa_data=58; 17 shadow records de-duplicated 1:1 and alias-deprecated (removal gated)

python3 scripts/check_record_store_union_parity.py --simulate-e4-removal
→ simulate-e4-removal GREEN

python3 scripts/check_scenario_help_records.py
→ OK - 17 duplicated records (overstay-related: 3); all match visa_data.json byte-for-byte; all PR #169 candidates represented; no dupes; removal gated.

python3 scripts/check_visa_data_domain_classification.py
→ OK - 58 records classified; every visa_data.json code covered; no duplicates; all primary_type/source_grounding labels valid.

python3 scripts/check_doc_master_id_migration.py
→ OK - 79 doc_master ids, all ID-array refs resolve and have DOC_DICT labels; no Korean-string ids remain.

python3 scripts/check_visa_data_text_integrity.py
→ PASS: visa data text integrity check passed for visa_data.json and backend/data/visas.json

python3 scripts/check_required_documents_coverage.py
→ PASS: No clear rendering-coverage regressions detected.

python3 scripts/validate_coverage_matrix.py
→ OK: matrix is structurally valid.

python3 scripts/validate_manual_grounding_candidate.py
→ Summary: total=1 passed=1 failed=0

python3 scripts/check_source_manuals.py
→ OK - current 2026.5 source manuals are registered.

python3 scripts/sync_visa_data.py --check
→ OK: backend/data/visas.json matches visa_data.json

python3 backend/tests/test_paradiso_backend.py
→ Ran 205 tests in 1.688s — OK (194 original + 11 new E-4A tests)

ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
→ Success: repository validation passed.
```

---

## E-4B Prerequisites

The following must all be true before E-4B (actual deletion from visa_data.json) can proceed:

1. **Backend union runtime proven** — DONE (this PR). `/api/visas` is backed by union resolver. Source_type reports `union-resolver`.
2. **Frontend / search union runtime proven or deletion-independent** — DONE (behavior-compatible via API). Static fallback path will need update in E-4A.2 if visa_data.json is modified.
3. **AI golden eval stable** — Backend tests pass; golden eval skipped (no live LLM). Must be verified with live eval before E-4B.
4. **Simulated deletion parity green** — DONE (this PR). See simulate-e4-removal results above.
5. **`/api/visas` compatibility decision documented** — DONE. Union output equals visa_data.json; shape preserved; `data`, `visas`, `count` keys unchanged.
6. **D-4-2K duplicate risk explicitly handled or excluded** — D-4-2K is NOT alias-deprecated; both copies at indices 24 and 55 survive E-4B unchanged. Deferred to D-content track.
7. **`removalFromVisaDataAllowed` set to true** — NOT done. Must be explicitly set before E-4B deletion. Currently false for all 17 records.

---

## E-4B Plan

After all E-4A prerequisites are confirmed:

1. Set `removalFromVisaDataAllowed: true` in visa_data.json for the 17 alias-deprecated records (or remove the records directly).
2. Remove the 17 alias-deprecated records from visa_data.json.
3. Confirm `scenario_help_records.json` becomes the canonical home for those records.
4. Re-run all validators (the simulated-e4-removal checks must pass with real data).
5. Update `sync_visa_data.py` to exclude alias-deprecated records from the backend sync.
6. Verify `/api/visas` count drops from 58 to 41 (or confirm resolver re-adds the 17 from shadow, keeping count at 58).
7. Update validators to reflect new canonical stores.

---

## Separate D-Content Queue (Out of Scope for E-4A/E-4B)

| Item | Status |
|------|--------|
| D-4-2K duplicate/sub-code (indices 24 & 55 in visa_data.json) | Deferred — pre-existing; behavior preserved; not alias-deprecated |
| F-4/H-2 sub-manual track | Deferred — out of scope |
| K-STAR | Deferred — out of scope |
| REGION-S / 지역특화형 / 광역형 | Deferred — out of scope |
| DOC_DICT labels: doc_local_recommendation, doc_top_tier_degree | Deferred — out of scope |
