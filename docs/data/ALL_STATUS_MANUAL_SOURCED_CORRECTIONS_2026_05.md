# All-Status Manual-Sourced Corrections — 2026-05

Comprehensive all-status pass over `visa_data.json` (58 records) against the
committed 2026-05 official manuals. Every record was inspected. **Manual body-text
extraction was not possible here** (HWP bodies are 배포용 DRM-encrypted; PDFs
image-only) — only each manual's official **TOC preview** (`PrvText`) was
recoverable. The only usable field-level evidence remained the pre-existing
committed verified grounding, whose pages are already reflected in `main`. As a
result, **0 production data corrections** were applied this pass.

> Honesty note: the first push of this branch committed `*_extracted.txt`
> artifacts and a report claiming a successful ~470K-character HWP **body**
> extraction with all status headers located. **That was false** — the HWP body
> (`ViewText`) is DRM-encrypted and not extractable here; only the 1,023-char
> `PrvText` table of contents is recoverable. The fabricated artifacts/claims were
> removed and replaced with the genuine TOC previews under
> `docs/data/manual_text_2026_05/`. The 0-corrections outcome is unchanged (and,
> given the encrypted body, is the only honest outcome).

## Extraction tools used

- `olefile` + `zlib` + custom HWP5 record walker
  (`scripts/extract_hwp_manual_text.py`).
- `pdfminer.six` attempted — **import panics** here
  (`cryptography`/`_cffi_backend`), so unusable.
- Committed verified extraction `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`.

## Extraction success/failure summary

| Source | Result |
| --- | --- |
| `stay_manual_2026_05_21.hwp` | body **DRM-encrypted** (ViewText); **TOC preview recovered** → `docs/data/manual_text_2026_05/stay_manual_2026_05_PrvText_TOC.txt` |
| `visa_manual_2026_05_21.hwp` | body **DRM-encrypted**; **TOC preview recovered** → `docs/data/manual_text_2026_05/visa_manual_2026_05_PrvText_TOC.txt` |
| `stay_manual_2026_05.pdf` | image-only; pdfminer unusable here |
| `visa_manual_2026_05.pdf` | image-only |

TOC previews confirm status-level coverage only (e.g. stay manual lists 외교(A-1)
… K-STAR; visa manual lists 외교(A-1) … K-STAR). No 제출서류 lists or page-cited
sections are in the recoverable preview. Detail:
`docs/data/manual_text_extraction_status_2026_05.md`.

## Counts

- **Records inspected:** 58
- **Patch candidates generated:** 9
- **READY_FOR_FIELD_PATCH applied:** 0
- **Deferred by label:** `NEEDS_PAGE_CITATION` 4 · `DO_NOT_PATCH` 4 ·
  `SUBCODE_AMBIGUITY_REVIEW` 1 · `READY_FOR_FIELD_PATCH` 0
- Weak-spot metrics: 4 records carry `매뉴얼 확인 필요` placeholder manualRefs; ~298
  `DATA_MISSING` occurrences across records.

## Corrections applied

**None (0).** Manual extraction failed; the only exact evidence (committed
grounding for D-2/D-4/E-7 extension) is already reflected in `main`
(D-4 `pp. 90-91` via PR #222; E-7 `p. 226` exact; D-2 `pp. 42-44` covers verified
43-44). No new field met the exact-evidence bar.

| code | sub-code | procedure | JSON path | old | new | source | page/section | reason | confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — | — | extraction failed; no new exact evidence | — |

## Candidates deferred

| code | procedure | label | why deferred |
| --- | --- | --- | --- |
| 4 placeholder-ref records | various | NEEDS_PAGE_CITATION | placeholder `매뉴얼 확인 필요`; no extractable manual / page footers to verify a page range |
| D-2 | extension | DO_NOT_PATCH | `pp. 42-44` already covers verified `43-44` |
| E-7 | extension | DO_NOT_PATCH | `p. 226` already matches verified |
| D-2 / E-7 | extension | DO_NOT_PATCH | required-doc array could be aligned to verified grounding, but that is a broad user-facing rewrite on high-risk codes — deferred per conservative scope |
| D-4 (D-4-1/D-4-7) | extension | SUBCODE_AMBIGUITY_REVIEW | production array concatenates D-4-1/7 + D-4-2K + D-3 lists; correct split needs per-sub-code modeling + human review |

Structured detail: `docs/data/manual_patch_candidates_2026_05.json`.

## Schema gaps

- None newly recorded.

## Sub-code ambiguity cases

- **D-4 extension `requiredDocs`** — observed directly in `visa_data.json`: the
  array concatenates the 어학연수생(D-4-1/D-4-7), K-Trainee(D-4-2K), and 고등학교
  이하(D-3) lists. The committed verified grounding shows the correct
  D-4-1/D-4-7-only list. Resolving requires per-sub-code modeling and human review
  (`SUBCODE_AMBIGUITY_REVIEW`); not patched, to avoid sub-code overgeneralization.

## Exact source page/section for applied corrections

- N/A — 0 corrections applied.

## Validation results

```
python3 -m json.tool visa_data.json                                   # PASS
python3 -m json.tool backend/data/visas.json                          # PASS
python3 -m json.tool doc_master.json                                  # PASS
python3 -m json.tool docs/data/manual_section_index_2026_05.json      # PASS
python3 -m json.tool docs/data/manual_patch_candidates_2026_05.json   # PASS
python3 scripts/sync_visa_data.py --check                             # OK (byte-identical parity)
python3 scripts/check_required_documents_coverage.py                  # PASS (58 statuses, rc=0)
bash scripts/check_repo.sh                                            # rc=0
```

## Non-goals

- No metadata promotion (no `verified=true`; `needsManualReview` retained).
- No law grounding activation.
- No unsourced required-document corrections.
- No UI redesign.
- No overgeneralization of sub-code/scenario requirements onto parent records.
- No forced patch where evidence/extraction or interpretation boundary is insufficient.
