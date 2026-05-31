# All-Status Source-Confirmed Correction Report — 2026-05

## Purpose

A comprehensive, all-status inspection of every record in `visa_data.json` (58
records, 41 real visa/status records) against the official 2026-05 manuals, using
the Claude Opus manual-extraction artifacts (`docs/data/claude_opus_manual_extraction_2026_05/`)
as candidate evidence and **independent PyMuPDF re-extraction of the committed
PDFs** as the verification gate. The goal was to apply every correction that is
source-confirmed, page/section-supported, parent/sub-code-bounded, and safely
representable in the current schema — without forcing any patch that lacks exact
evidence.

## Source artifacts used

- `docs/data/claude_opus_manual_extraction_2026_05/` — Parts 2–7 CSV/JSON, HWP
  verification report, full HWP text (visa + stay), MANIFEST.
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (777 pp.) and
  `visa_manual_2026_05.pdf` (484 pp.) — re-extracted page-by-page with **PyMuPDF
  1.27** (text layer intact; printed footer `- N -` == absolute PDF page, 1:1),
  enabling independent verification of page citations and section titles.
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` — 3
  locally-verified, HIGH-confidence groundings (D-2 pp.43-44, D-4-1/D-4-7 pp.90-91,
  E-7 p.226).
- `visa_data.json`, `backend/data/visas.json`, `doc_master.json`.

## Inspection scope and counts

- **Records inspected:** 58 (all) — 41 real visa/status records, 17 synthetic/helper records.
- **Evidence rows reviewed:** 441 field-evidence blocks (`part3`), cross-checked
  against 2,519 document-item rows (`part4`), 442 sub-code rows (`part5`), 275
  HWP/PDF cross-check rows, and 23 high-risk items (`part6`).
- **Candidates generated:** 44 (`ALL_STATUS_SOURCE_CONFIRMED_PATCH_CANDIDATES_2026_05.json`).
- **READY_FOR_FIELD_PATCH candidates:** **0**.
- **Corrections applied:** **0**.
- **Deferred candidates by label:** `SUBCODE_AMBIGUITY_REVIEW` 42 · `DO_NOT_PATCH` 1 · `NEEDS_REVIEW` 1.

For reference, the underlying extraction artifact labels across all 441 field-evidence
rows are: `NEEDS_PAGE_CITATION` 187 · `NEEDS_REVIEW` 144 · `SUBCODE_AMBIGUITY_REVIEW`
110 — and **0** were promoted to `READY` by the extraction itself.

## Applied corrections

| code | sub_code | procedure | JSON path | old | new | source | page/section | excerpt | reason | confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | No candidate met the exact-evidence + clear-current-error + parent-level + schema-representable bar. | — |

**None (0).** See "Why zero corrections" below.

## Why zero corrections were applied

This pass had **more capability than prior passes** (PyMuPDF gave working PDF text,
unlike PR #224 where extraction was blocked). That capability was used to *verify*,
and verification confirmed the conservative outcome:

1. **The only HIGH-confidence, exact-page, clear-boundary evidence — the 3 verified
   groundings (D-2, D-4-1/D-4-7, E-7) — is already reflected in `main`** (D-4 pp.90-91
   via PR #222; E-7 p.226 exact; D-2 extension covered). Re-reading PDF pp.90-91
   reproduced the D-4 grounding verbatim (`① 신청서 (별지 34호 서식)…`), confirming the
   data is correct.

2. **The auto-extracted page citations are defensible, not clearly wrong.** The most
   promising candidate — D-2 `procedures.extension.manualRefs` `"pp. 42-44"` —
   initially looked like an over-broad range (the verified grounding scopes the
   제출서류 to 43-44). But PDF reading shows the **체류기간 연장허가 procedure section
   begins on p.42** (`가. 기본원칙 / 학사일정을 고려한 체류기간 부여`). So "pp. 42-44"
   correctly bounds the extension *procedure section*; the grounding's "43-44" is the
   narrower 제출서류 sublist. Narrowing would drop the 가.기본원칙 page — a regression,
   not a fix. Labelled `DO_NOT_PATCH`.

3. **Document-list evidence cannot be attributed to parent vs sub-code mechanically.**
   Of 441 field-evidence rows, only 9 are `universal`-boundary — and every one is
   `NEEDS_PAGE_CITATION`, MEDIUM confidence, with `procedure_type` listing *all*
   procedures concatenated (procedure attribution also unresolved). The remaining 432
   are `sub_code_specific` (110), `scenario_specific` (181), or `unclear` (141).
   Confidence is MEDIUM (295) or LOW (146) — never HIGH. Patching any of these into
   parent records would over-generalize sub-code/scenario requirements (a hard
   constraint violation).

4. **The canonical `procedures.*` data is already manual-sourced.** Spot-checks (e.g.
   D-2 `procedures.registration`) show the per-procedure `requiredDocs` already mirror
   the manual page content (p.44 외국인등록 제출서류) with `needsManualReview` flags. The
   `documents_*` legacy fields and their `DATA_MISSING` notes are vestigial display
   structures superseded by `procedures.*`; filling them would duplicate data and risk
   flattening the conditional branches (대체서류 ①②, 인증대학/일반대학) present on the page.

## Deferred candidates

| code(s) | label | why deferred |
|---|---|---|
| D-2 (extension pageRange) | DO_NOT_PATCH | Current "pp. 42-44" is a defensible procedure-section citation (extension begins p.42); verified grounding 43-44 is a narrower sublist scope. |
| 42 status groups (C-3, C-4, D-2, D-4, D-8, D-10, E-1…F-6, G-1, H-1, H-2, A-1…D-6, K-STAR, REGION-S, etc.) | SUBCODE_AMBIGUITY_REVIEW | Field-evidence document blocks are sub_code_specific/scenario_specific and not machine-attributed to a sub-code; patching into parent/generic fields would over-generalize. Human per-sub-code segmentation required. |
| F-4 (extension pageRange) | NEEDS_REVIEW / SUBCODE_AMBIGUITY_REVIEW | F-4 procedures are cross-referenced inside the embedded 외국국적동포 업무 매뉴얼 (PDF p.518+); no clean standalone parent-level 체류기간 연장허가 제출서류 list; correct page cannot be fixed with exact evidence. |

Full structured detail: `docs/data/ALL_STATUS_SOURCE_CONFIRMED_PATCH_CANDIDATES_2026_05.json`.
Per-record gap detail: `docs/data/ALL_STATUS_DATA_GAP_INVENTORY_2026_05.json`.

## High-risk status notes

High-risk statuses (≥8 sub-codes or ≥8 sub-code evidence rows): **C-3, C-4, D-2, D-4,
D-8, D-10, E-7, E-8, E-9, F-1, F-2, F-3, F-4, F-5, F-6, G-1, H-2, K-STAR.** These
require human manual segmentation before any field patch (per `part6_high_risk_review.csv`):

- **E-7** (특정활동) spans stay pp.212-323 with dozens of occupation codes; document
  blocks span many sub-codes and cannot be auto-attributed.
- **F-5 / F-2 / F-1** carry the largest sub-code counts (35 / 28 / 20) with the most
  incomplete automated separation.
- **F-4** is documented via an embedded cross-referenced sub-manual.
- **D-4** parent `extension` requiredDocs concatenate D-4-1/D-4-7 + D-4-2K + D-3 lists;
  the verified grounding only covers the D-4-1/D-4-7 sub-track — must not be merged
  into the parent.

Recommended manual-review priority (from MANIFEST): **E-7 → F-5 → F-2 → F-1 → D-4 →
F-6 → H-2 → G-1 → C-3 → D-10.**

## Parent/sub-code boundary notes

- The manual presents most extension/registration document lists **per sub-code** in
  multi-column tables (left = sub-code/scenario label, right = circled documents). PDF
  text extraction concatenates the columns, so sub-code attribution is unverifiable
  without page inspection. Parent records must not absorb sub-code-specific lists.
- `D-4-2K` appears twice in `visa_data.json` by design (backend-test-protected) and was
  not altered.

## Schema gaps

- `documents_initial` / `documents_extension` / `documents_registration` legacy fields
  use a flat `{name, note}` shape that cannot represent the conditional branches
  (대체서류 alternatives, 인증대학/일반대학 splits) present in the manual without
  flattening. The canonical `procedures.*.requiredDocs` (`commonDocs / requiredDocs /
  additionalDocs / conditionalDocs`) is the appropriate target, and is already
  populated. No new schema was introduced in this PR.

## Validation results

```
python3 -m json.tool visa_data.json                                                       # PASS (unchanged)
python3 -m json.tool backend/data/visas.json                                              # PASS (unchanged)
python3 -m json.tool doc_master.json                                                      # PASS (unchanged)
python3 -m json.tool docs/data/ALL_STATUS_DATA_GAP_INVENTORY_2026_05.json                 # PASS
python3 -m json.tool docs/data/ALL_STATUS_SOURCE_CONFIRMED_PATCH_CANDIDATES_2026_05.json  # PASS
python3 scripts/sync_visa_data.py --check                                                 # OK (byte-identical parity)
python3 scripts/check_required_documents_coverage.py                                       # PASS (58 statuses, rc=0)
bash scripts/check_repo.sh                                                                 # rc=0
```

## Non-goals

- No metadata promotion (`verified=true` not set; `needsManualReview` retained).
- No law grounding activation.
- No UI redesign.
- No unsourced required-document corrections.
- No overgeneralization of parent/sub-code requirements (no sub-code/scenario list merged into a parent record).
- No merging of visa issuance and stay/residence procedure evidence (첨부서류 vs 제출서류 kept separate).
- No flattening of conditional requirements into universal requirements.
