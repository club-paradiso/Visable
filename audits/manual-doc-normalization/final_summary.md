# Final Summary — Manual Document Normalization

**Branch:** `claude/vigilant-ritchie-49oja3`
**Date:** 2026-06-10
**Scope:** Audit + scoped fix of document labels, duplicates, and embedded-manual
page strings across all 42 top-level records in `visa_data.json`.

## Coverage
- **Top-level codes audited:** 42 / 42 (every code has a recorded audit entry across batches B01–B07).
- Method: global mechanical scan (`scan_mechanical.py`) + targeted naming-near-miss
  scan (`scan_naming.py`), each candidate verified against the **correct** manual
  by procedure tab (visa manual for `visaIssuance`; stay manual for all 체류 tabs).

## Confirmed fixes applied: 5 (all Type E)
Removed the literal `(embedded manual pp. X-XX)` parenthetical from 5 source-citation
`pageRange` strings; the rest of each citation (`PDF pp. …`, sourceFile, confidence,
needsManualReview) was left intact.

| # | Code | Tab | Old → New |
|---|---|---|---|
| 1 | F-4 | extension       | `PDF pp. 530-531 (embedded manual pp. 10-11)` → `PDF pp. 530-531` |
| 2 | F-4 | registration    | `PDF p. 530 (embedded manual p. 10)` → `PDF p. 530` |
| 3 | F-4 | statusChange    | `PDF pp. 528-530 (embedded manual pp. 8-10)` → `PDF pp. 528-530` |
| 4 | H-2 | registration    | `PDF pp. 524-525 (embedded manual pp. 4-5)` → `PDF pp. 524-525` |
| 5 | H-2 | workplaceChange | `PDF pp. 525-526 (embedded manual pp. 5-6)` → `PDF pp. 525-526` |

- Type A (exact duplicate in array): **0 found.**
- Type B (commonDocs ∩ requiredDocs): **0 found.**
- Type C (semantic duplicate confirmed by manual): **0 confirmed.**
- Type D (naming corrected to official label): **0 confirmed** (see below).

## Ambiguous / skipped: 34 (no change made)
All 33 naming near-miss candidates + 1 normalized near-dup were reviewed against the
correct manual and **intentionally not changed**, by category:

| Category | Count | Why skipped |
|---|---|---|
| ALREADY_FAITHFUL | 22 | Data label already matches the manual modulo whitespace / dot-char (`·`/`․`) / a dropped `*` or paren annotation. Changing it would be pointless churn, not a correctness fix. |
| FLATTENED_ARTIFACT | 6 | Extraction concatenated a section heading or roman-numeral marker into the "document" string (e.g. `체류기간 연장허가,`, `통합신청서 ※ 지방자치단체 방문 시:`, D-10 `체류지 입증서류 ⅱ) …`). Table context unclear → ambiguous per the flattened-extraction rule. |
| LESS_SPECIFIC | 3 | Data uses a valid but less-specific label (F-4 `통합신청서(별지 제1호 서식)` vs manual `재외동포 통합신청서(별지 제1호서식)`; H-2 `외국인등록 신청서`). Not *wrong*; does not meet the non-interactive "extremely clear" bar. Flagged for human review. |
| MULTI_DOC_ELEMENT | 1 | D-8 `신청서, 여권, 표준규격사진, 체류지 입증서류` packs 4 docs in one array element; splitting = restructuring (out of scope). |
| FEE_NOTE | 1 | D-8 `수수료 면제` is a fee note, not a document name (fees are protected). |
| NEAR_DUP (D-10) | 1 | `구직활동계획서` vs `구직활동 계획서` in one flattened array map to different applicant sub-categories (점수제 적용 vs 점수제 면제 특례) in the manual; not a true duplicate. |

> The D-10 `extension.requiredDocs` array is the most extraction-damaged
> (headings-as-documents). It is flagged for a future structured re-extraction
> pass (follow-up work, NOT attempted here per the no-new-pipeline rule).

## Files changed
| File | Change |
|---|---|
| `visa_data.json` | 5 lines (Type E parenthetical removal) |
| `backend/data/visas.json` | 5 lines (regenerated via `scripts/sync_visa_data.py`, not hand-edited) |

Protected/untouched: legal disclaimers, fee amounts, source citations (other than the
literal embedded-manual parenthetical), subcode data, procedure logic, `index.html`
(0 embedded-manual strings present), `doc_master.json` (0 findings).

## Validation results
- `python3 -m json.tool visa_data.json` → VALID
- `python3 -m json.tool doc_master.json` → VALID
- `git diff --check` → clean
- `scripts/sync_visa_data.py --check` → in sync
- `scripts/check_repo.sh` → **PASS** (all regression checks; JSON valid; manual schema valid; source manuals registered; diff clean; no forbidden branding). Baseline before edits was also PASS — no regression introduced.

## Remaining risks / follow-ups (not in scope here)
1. Structured re-extraction of flattened tables (esp. D-10 `extension.requiredDocs`,
   E-7/E-8 heading fragments) to recover document-vs-heading boundaries.
2. Human decision on the 3 LESS_SPECIFIC labels (whether to prefix `재외동포` / use
   `통합신청서` form name).
3. These manuals are text extractions of HWP; verbatim-match rates (≈54% exact, ≈10%
   label-partial) reflect annotation/whitespace divergence, not data errors.

## Commit/PR status
**Not committed, no PR created** — per the instruction to hold commit/PR until
explicitly authorized. Working tree contains the 2-file, 10-line change ready to commit.
