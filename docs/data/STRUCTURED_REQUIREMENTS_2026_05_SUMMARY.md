# Structured Requirements Layer — 2026-05 Summary

## Why this PR exists (after PR #227)

PR #227 inspected all 58 records and found **0 production corrections** were safely
applicable, because the overwhelming majority of 2026-05 manual evidence is
**sub-code-specific, scenario-specific, conditional, or multi-procedure** — and the
legacy flat fields (`newReqDocs`, `extReqDocs`, flat `requiredDocs` arrays) cannot
absorb that evidence without over-generalizing it onto parent records.

This PR resolves that structural gap by introducing a **structured evidence layer**
that can faithfully represent the evidence at the correct granularity (status →
sub-code → scenario → condition → procedure → document item → source page), and by
**bridging** the existing production records to that layer without distorting their
shape.

## What was created

| File | Role |
|------|------|
| `backend/data/manual_grounding/structured_requirements_2026_05.json` | The structured evidence layer (canonical). |
| `docs/data/structured_requirements_2026_05.json` | Docs mirror (identical copy). |
| `backend/data/manual_grounding/structured_requirements_index_2026_05.json` | Join table: structured statusCode → metrics + mapped production codes. |
| `scripts/validate_structured_requirements.py` | Structural + boundary-safety validator. |

## Counts

- **Statuses represented:** 42
- **Structured entries:** 337 (334 auto-extracted blocks + 3 verified groundings)
- **Document items:** 2,546 (2,519 from `part4_document_items.csv` + 27 from verified groundings)

### By procedure type
`other` (multi-procedure / unresolved) 315 · `visa_issuance` 18 · `extension` 4

`other` dominates because most manual document blocks in the source PDFs are
presented under a section that spans several procedures at once; the extraction
could not attribute a single procedure mechanically. The raw detected procedures are
preserved per entry in `procedureTypesDetected`.

### By boundary type
`scenario_specific` 142 · `unclear` 94 · `sub_code_specific` 92 · `universal` 7 · `parent_code_level` 2

Only **9 of 337** entries are parent-level/universal — confirming PR #227's finding
that almost all evidence is below the parent grain.

### By confidence
`MEDIUM` 201 · `LOW` 133 · `HIGH` 3

`HIGH` is reserved for the 3 locally-verified groundings. No auto-extracted row is
HIGH (by design — machine attribution is unverified).

### By readiness label
`NEEDS_SCENARIO_REVIEW` 142 · `NEEDS_PAGE_CITATION` 101 · `NEEDS_SUBCODE_REVIEW` 91 · `STRUCTURED_EVIDENCE_READY` 3

## High-risk statuses

C-3, C-4, D-2, D-4, D-8, D-10, E-7, E-8, E-9, F-1, F-2, F-3, F-4, F-5, F-6, G-1, H-2,
K-STAR. These carry the most sub-codes / largest page ranges / most complex
multi-column tables (E-7 alone has 38 entries spanning stay pp.212-323). They require
human per-sub-code segmentation before any promotion to user-facing data.

## How this differs from the legacy flat fields

| Legacy flat fields | Structured layer |
|---|---|
| One array per procedure per record | One entry per (status, sub-code, scenario, procedure, page) block |
| No place for sub-code/scenario/condition | Explicit `subCode`, `scenarioId`, per-document `conditionKo`, `boundary` |
| No machine-checkable provenance | `manualSource` with file, pages, section title, excerpt |
| No readiness/confidence semantics | `confidence`, `reviewStatus`, `readinessLabel`, `doNotFlatten` |
| Risk of over-generalization | Boundary-safety enforced by validator |

## What changed in `visa_data.json`

Only an **additive** `structuredRequirementsRef` pointer was added to 41 records (37
direct matches + D-4-2K×2 + REGION-S→REGIONAL + F-4→FORDIASP). No existing field was
modified, removed, reordered, or reformatted. `backend/data/visas.json` is kept
byte-identical via the sync copy. See `LEGACY_JSON_SAFE_PATCH_REPORT_2026_05.md`.

## What was intentionally NOT changed

- No legacy document array was edited (no flattening of sub-code/scenario/conditional
  evidence into parent arrays).
- No `manualRefs` page range was changed — PR #227 verified the existing citations are
  defensible procedure-section approximations, not errors.
- No `verified=true` promotion; no `needsManualReview` removed.
- No `doc_master.json` entries added (structured `docMasterId` left `null` pending
  human review; no exact reusable definition was unambiguously supported).
- No runtime wiring of structured *content* into AI/answer paths (see below).

## How future PRs should promote structured rows into production

1. Pick a status from the high-risk priority order (E-7 → F-5 → F-2 → F-1 → D-4 →
   F-6 → H-2 → G-1 → C-3 → D-10).
2. For each structured entry, open the cited `manualSource` page in the PDF and
   confirm the sub-code/scenario boundary by hand.
3. Promote the entry to `readinessLabel: STRUCTURED_EVIDENCE_READY` only when the
   boundary, procedure, and document list are confirmed and the production schema can
   represent them without flattening (use `procedures.*.requiredDocs` groups, or a
   sub-code-scoped structure — never a flat parent array for sub-code evidence).
4. Resolve each document's `docMasterId` against `doc_master.json`; add a reusable
   doc definition only when no existing ID fits and the document is not
   scenario/sub-code-specific in a misleading way.
5. Keep `needsManualReview` until a human signs off; never set `verified=true`
   automatically.
