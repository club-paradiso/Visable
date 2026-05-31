# Legacy JSON Safe-Patch Report — 2026-05

## Scope

Records inspected: **58** (all of `visa_data.json`; 41 real visa/status records + 17
synthetic/helper records). This report documents exactly what was changed in the
production JSON and what was deliberately left unchanged.

## Safety preflight

- **Backend serve path:** `backend/paradiso_backend.py` → `_load_visas()` returns
  records verbatim under `/api/visas` (`data`/`visas`); no field whitelist on output,
  so an additive optional field is passed through unchanged.
- **Schema guard:** `scripts/check_repo.sh` step 3 is a positive-presence check (no
  `additionalProperties: false`) → an extra optional field is not rejected.
- **AI prompt path:** verified by `backend/tests/test_paradiso_backend.py`
  (`test_migration_meta_not_in_ai_context_block`, `..._prompt_text`) that the AI
  context block uses a curated whitelist; the new field does **not** leak into AI
  prompts. All 205 backend tests + 4 law-grounding tests pass with the change.
- **Formatting fidelity:** `json.dumps(data, ensure_ascii=False, indent=2) + "\n"`
  reproduces `visa_data.json` byte-for-byte, so the scripted field-add produces a
  clean, additions-only diff (+291 / −0) with no reordering or reformatting.

Conclusion: adding an additive reference field is safe. It was therefore preferred
over an external-only mapping, and an external index was **also** added for decoupled
consumers.

## Legacy JSON fields changed

| Field | Change | Records | Notes |
|---|---|---|---|
| `structuredRequirementsRef` | **added** (new optional object) | 41 | 37 direct status matches + `D-4-2K`×2 + `REGION-S` + `F-4` |

Added object shape:

```json
"structuredRequirementsRef": {
  "source": "backend/data/manual_grounding/structured_requirements_2026_05.json",
  "statusCode": "D-4",
  "available": true,
  "entryCount": 15,
  "requiresHumanReview": true
}
```

Indirect mappings carry an explicit `mappingNote` (`D-4-2K`→`D-4`, `REGION-S`→
`REGIONAL`, `F-4`→`FORDIASP` embedded 외국국적동포 매뉴얼).

Synthetic/helper records (K-ETA, TB-1, SCN-*, OVS-1, NHIS-1, FAQ-*, VW-1, COM-1,
RF-1) received **no** ref — they have no manual evidence.

## Legacy JSON fields NOT changed

- No document arrays (`newReqDocs`, `extReqDocs`, `addReqDocs`, `documents_*`,
  `procedures.*.requiredDocs`) were edited — sub-code/scenario/conditional evidence
  was **not** flattened into parent fields.
- No `manualRefs` page ranges changed — PR #227 PDF-verified the existing citations
  are defensible procedure-section ranges, not errors (e.g. D-2 `pp. 42-44` correctly
  bounds the extension section that begins on p.42).
- No `needsManualReview` removed; no `verified=true` set.
- No `manualRequiredDocAudit`, `sourceManualStatus`, `migrationMeta` touched.
- No `doc_master.json` change.

## Structured refs / external index added

- In-record pointer: `structuredRequirementsRef` (41 records, above).
- External join table: `backend/data/manual_grounding/structured_requirements_index_2026_05.json`
  (42 structured statuses → entryCount, documentItemCount, readyCount,
  hasSubCodeEvidence, hasScenarioEvidence, requiresHumanReview, boundary/procedure/
  confidence breakdowns, mapped production codes).

## Exact source support for every production change

The only production change is the `structuredRequirementsRef` pointer. Its
`statusCode`/`entryCount` are derived directly from
`backend/data/manual_grounding/structured_requirements_2026_05.json`, which is itself
derived from `docs/data/claude_opus_manual_extraction_2026_05/` (part3/part4) and the
locally-verified `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`.
No document content was written into production; the pointer only advertises that
structured evidence exists and **requires human review**.

## Sync / parity result

```
python3 scripts/sync_visa_data.py --check   # OK: backend/data/visas.json matches visa_data.json (byte-identical)
```

## Validation result

```
python3 -m json.tool backend/data/manual_grounding/structured_requirements_2026_05.json        # PASS
python3 scripts/validate_structured_requirements.py <structured>                                # PASS (337 entries, 2546 doc items, 42 statuses)
python3 -m json.tool visa_data.json                                                             # PASS
python3 -m json.tool backend/data/visas.json                                                    # PASS
python3 -m json.tool doc_master.json                                                            # PASS (unchanged)
python3 scripts/sync_visa_data.py --check                                                       # OK
python3 scripts/check_required_documents_coverage.py                                            # PASS (rc=0)
bash scripts/check_repo.sh                                                                       # rc=0
python3 -m pytest backend/tests/                                                                 # 209 passed
```

## Script change (strictly necessary)

`scripts/check_required_documents_coverage.py` gained a small
`NON_DOCUMENT_METADATA_FIELDS` allowlist so the new `structuredRequirementsRef`
reference pointer (whose name contains a "req" token) is not misclassified as an
unrendered document field. This is the minimal change needed to keep the suggested
field name while keeping the coverage guard green; no document-coverage logic was
weakened for actual document fields.
