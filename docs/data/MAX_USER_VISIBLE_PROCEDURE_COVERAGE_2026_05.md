# Maximize User-Visible Procedure Coverage — 2026-05

## Goal

Reduce the user-visible "structured document checklist … not verified yet"
fallback (`docReviewFallback` / `DOCUMENT_DATA_MISSING_NOTICE` in index.html) by
populating real, official-manual-backed procedure document lists in the
**canonical user-facing data file** `visa_data.json` (mirrored to
`backend/data/visas.json`).

This is a data-population PR, not an audit. It adds concrete required-document
content that the `renderProcedures` document tabs render directly.

## How the user-visible path works (confirmed)

`index.html` → `renderProcedures(v)` builds one tab per procedure in
`PROCEDURE_CONFIG` (visaIssuance, statusChange, extension, statusGrant,
registration, activitiesOutsideStatus, workplaceChange, **reentry**). A tab is
shown when `procedures[key].available !== false`; if its `requiredDocs` groups
are empty, the tab renders the fallback notice. So the way to remove a fallback
is to populate `procedures[key].requiredDocs`.

A coverage scan of the 39 A–H status records showed registration and extension
are already populated for essentially every applicable status. The empty
("available-but-empty" or "missing") procedure cells were concentrated in
**reentry, statusChange, activitiesOutsideStatus, workplaceChange, statusGrant**.

## What this PR populates: re-entry permit (재입국허가)

The stay manual repeats a uniform, **parent-level** 재입국허가 block in each
long-stay status section:

```
재입국허가
1. 재입국허가 면제 제도 … 등록 외국인이 출국일부터 1년 이내 재입국 시 면제 …
2. 복수재입국허가 (사우디·이란·리비아 제한, 단 F-6/D-2/D-4 국민은 가능)
   - 출국 후 1년 초과 2년 이내 재입국 시
   - 신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료
```

`scripts/populate_reentry_procedure_docs_2026_05.py` reads each status's own
re-entry sub-block (from `재입국허가` up to the next `외국인등록` heading, so the
following registration list is never merged in), takes the **verbatim**
`신청서류 :` / `제출서류 :` document line, re-verifies the printed page footer,
and writes a structured `procedures.reentry` record. Conditions are preserved:
the exemption rule and the multiple-reentry trigger go in `notes`, the
nationality restriction in `conditionalDocs` — never flattened into the required
list.

### Summary counts

| Metric | Value |
|---|---|
| Procedure records **added** (reentry) | **13** |
| Status records updated | 13 (re-entry procedure newly populated) |
| New document items | 52 (4 docs × 13) + conditions |
| Populated procedure cells (A–H) | 81 → **94** |
| reentry fallback cells removed | 13 |
| Records overwritten | 0 (only empty/missing reentry cells were filled) |

### Records added

All from `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (manualName
"체류민원", v2026.5), scope = parent status, JSON path
`<code>.procedures.reentry`.

| status | page | doc list (verbatim) | conditions preserved |
|---|---|---|---|
| D-1 | p.34 | 신청서(별지 34호서식) · 여권 원본 · 외국인등록증 · 수수료 | 면제 제도(notes); 국적 제한(conditional) |
| D-4 | p.93 | 〃 | 〃 |
| D-6 | p.107 | 〃 | 〃 |
| D-7 | p.113 | 〃 | 〃 |
| D-8 | p.126 | 〃 | 〃 |
| D-9 | p.136 | 〃 | 〃 |
| E-2 | p.173 | 〃 | 〃 |
| E-3 | p.194 | 〃 | 〃 |
| E-4 | p.199 | 〃 | 〃 |
| E-5 | p.203 | 〃 | 〃 |
| E-6 | p.211 | 〃 | 〃 |
| F-3 | p.425 | 〃 | 〃 |
| H-1 | p.517 | 신청서(별지 34호 서식) · 여권 · 외국인등록증 · 수수료 | 면제 제도(notes) |

Every record keeps `manualRefs[0].needsManualReview = true` and
`confidence = "manual_extracted_needs_review"` (auto-extracted from the PDF,
not hand-certified) — consistent with existing visa_data conventions.

## Remaining unfilled cases (left empty on purpose)

| status / procedure | reason |
|---|---|
| D-2, D-5, D-10, E-7, E-9, E-10, F-1, F-5, G-1 — reentry | The status's re-entry sub-block on its located page is **exemption-only** (no 복수재입국 document line within the re-entry block). D-2 is the 유학생-specific narrative. Not fabricated. |
| A-1 / A-2 / A-3 — reentry | Diplomatic/official/agreement statuses; no standard 복수재입국 document list in the re-entry sub-block. |
| statusChange (체류자격 변경) — most statuses | Manual 변경허가 sections are sub-code / scenario specific; `visa_data.json` procedures are parent-level only, so a safe parent record cannot represent the sub-code splits. `dataModelMismatch` / `subCodeSplit`. |
| activitiesOutsideStatus, workplaceChange, statusGrant — most statuses | Sub-code / applicant-type / employment-type specific in the manual; not safely parent-level. `subCodeSplit` / `scenarioSplit`. |

These are intentionally left as fallback rather than flattened — fidelity over
coverage.

## Runtime exposure (verified)

- `GET /api/visas` serves each updated record's `procedures.reentry` with the
  document list and conditions (confirmed for D-7, H-1; D-2 stays empty).
- The static site reads `visa_data.json` directly; `backend/data/visas.json` is
  the synced deploy mirror (`scripts/sync_visa_data.py --check` OK).
- `renderProcedures` now renders a populated 재입국 tab for the 13 statuses
  instead of the fallback notice.
- AI grounding: unchanged (the structured-requirements grounding layer from
  PR #229–#231 is separate and was not modified).

## Validation results

```
python3 scripts/populate_reentry_procedure_docs_2026_05.py   # +13 (idempotent: re-run +0)
python3 -m json.tool visa_data.json / backend/data/visas.json / doc_master.json   # OK
python3 scripts/sync_visa_data.py --check                    # OK (byte-identical mirror)
python3 scripts/check_required_documents_coverage.py         # PASS (rc=0)
python3 -m pytest backend/tests/test_reentry_procedure_coverage.py   # 4 passed
python3 -m pytest backend/tests/test_structured_requirements.py      # 26 passed (PR#231 layer unaffected)
python3 backend/tests/test_paradiso_backend.py               # 205 passed
bash scripts/check_repo.sh                                   # PASS (golden eval: all regression checks passed)
```

## Safety note

No unofficial sources were used. No scenario-specific requirements were
flattened into parent-level records. Ambiguous targets were left unfilled
instead of promoted.

- Only empty/missing reentry cells were filled; no richer record was
  overwritten. No `verified=true` set; `needsManualReview` retained. No UI
  redesign, no AI-pipeline change, no crawler. Document lists are verbatim from
  each status's own manual page (footer re-verified).
