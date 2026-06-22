# Complex-status Level-A refinement — F-6/G-1/E-7/F-5/D-2/D-4 (2026-06-22)

Refines the six unified ComplexStatusGuide flows toward Level A **only where
source-backed repo data supports it**. F-4 is untouched (reference impl). No
eligibility rules, document requirements, subcode meanings, or citations were
invented.

## What this PR changed (over the #459 entry migration)

The guided-flow **result** now surfaces source-backed data instead of a flat
"공식근거 확인 필요" handoff:

1. **Official sources section** now shows the procedure's real **manual
   references** (`manualName · version · pageRange`, e.g. *사증민원 2026.6 ·
   pp. 326-337*) from `visa_data.json` `procedures.<key>.manualRefs` — every one
   of the six has these for its documented procedures. (criterion 7 ✓)
2. **Basic-document checklist** is rendered **only from resolvable `doc_master`
   IDs** (short, clean, audit-safe names). Prose document text (most of the data)
   is **never** re-rendered as tiles — it stays with the existing audit-guarded
   card renderer via the "전체 준비서류·절차 보기" handoff. (criteria 6, 11, 12 ✓)
3. **기본 준비서류 / 내 상황에서 추가될 수 있는 서류** are separated sections; copy-checklist
   includes resolved doc names + source refs.

Data reality (audited): document data for these statuses is **predominantly
prose**, not `doc_master` IDs. Only **F-6 visa issuance** is fully ID-based, so it
is the one path that gets a genuine in-overlay document checklist today. This is
why most statuses remain **Level B** — honestly, not cosmetically.

## Status-by-status level (after this PR)

| Status | Level | Why |
| --- | --- | --- |
| **F-6** | **A (visa issuance) / B (other procedures)** | visa issuance renders a real 9-item source-backed `doc_master` checklist (기본증명서, 가족관계증명서, 혼인관계증명서, 소득 입증서류…) + manual ref; extension/registration are prose → manual ref + handoff. 3 clean subcodes. |
| **D-2** | **B (strong)** | 8 clean subcodes; **every** procedure has source-backed prose docs + manual refs, but prose isn't `doc_master`-mapped → no in-overlay checklist yet. Kept distinct from D-4. |
| **D-4** | **B** | 7 clean subcodes; extension/reentry are MIXED (1 resolvable `doc_master` ID renders, rest prose → handoff) + manual refs. Kept distinct from D-2. |
| **E-7** | **B** | 11 occupation subcodes; only extension has (prose) docs + manual ref. Occupation note; deliberately does NOT duplicate the job/industry-code analyzer. |
| **F-5** | **B/C** | 8 active 영주 subcodes (22 manual-review placeholders excluded); 사증발급 not_applicable; only extension has sparse prose docs. Cautious permanent-residence note. |
| **G-1** | **B/C** | 16 reason-based subcodes, all `needsReview`; only extension has docs (1 prose item). Cautious reason-based note. |

## Source/data safety

- Checklist items are rendered **only** for `doc_master`-resolvable IDs; prose
  (incl. bundled strings like "통합신청서…, 여권, 외국인등록증, 수수료") is counted and
  routed to the audit-safe handoff, never rendered as a tile. Verified by
  `check_complex_status_guide.mjs` (no prose leaks into any of the six statuses'
  checklists).
- Manual references are displayed verbatim from the data (no fabricated
  citations). Procedures without docs/refs show "공식근거 확인 필요".
- Subcodes carry no own documents in the data, so the result shows the **parent
  procedure's** documents — no subcode-specific requirements are invented.
- No eligibility/approval claims; cautious wording throughout; standard safety
  note retained.

## Gaps preventing fuller Level A (recommended follow-up data tasks)

1. **Map procedure documents to `doc_master` IDs.** The biggest gap: D-2/D-4/E-7/
   F-5/G-1 store documents as prose. A source-reviewed pass mapping those prose
   names to `doc_master` IDs (and splitting bundled comma-lists) would let the
   in-overlay checklist light up for these statuses — turning D-2 (and others)
   into genuine Level A. This must be source-reviewed, not guessed.
2. **`procedure_evidence_bindings.json` join.** Its records key procedures by
   snake_case `procedureType` while `visa_data` uses camelCase; wiring evidence
   levels (`evidenceLevel`, `sourceBackedFields`) into the result would add a
   confidence signal. Low risk, data-only.
3. **G-1 / F-5 remain review-gated** (humanitarian / permanent-residence); keep
   conservative until per-reason / per-type documents are source-confirmed.

## Engine / safety notes

- All changes are isolated to `assets/js/complex-status-guide.js` (+ its test).
  The F-4 module and engine are untouched; `check_f4_route_guide` /
  `smoke_f4_hub` / `check_f4_guide_flow` all pass.
- `doc_master.json` is fetched lazily with graceful fallback (handoff) if the
  fetch fails — no hard dependency, no regression risk.

## Recommended next PR

A **source-reviewed data pass** mapping the six statuses' procedure documents to
`doc_master` IDs (item 1 above) — this is what unlocks real Level A for D-2/D-4/
F-6-extension/E-7. Pair it with a real-browser QA pass (widths + themes +
keyboard) across all seven statuses.
