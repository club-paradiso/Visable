# Structured Requirements Promotion Report — 2026-05

## Purpose

This PR follows PR #229 (which exposed only HIGH + STRUCTURED_EVIDENCE_READY
structured entries to the backend/API/AI/UI). Its goal is to **increase the number
of source-confirmed structured requirements** by independently verifying candidate
entries against the committed 2026-05 official PDFs and promoting those that pass the
strict 9-point promotion rule.

This is a concrete data change, not a docs-only audit: one new entry was verified and
promoted, raising the runtime-exposed source-confirmed count from **3 to 4**.

## Source files used

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (PyMuPDF text extraction; printed footer `- N -` == absolute PDF page, 1:1)
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
- `docs/data/claude_opus_manual_extraction_2026_05/` (part3/part4/part5/part6 — candidate spine)
- `docs/data/claude_opus_manual_extraction_2026_05/stay_hwp_full.txt`, `visa_hwp_full.txt` (table-cell/boundary cross-check; HWP has no page numbers and cannot replace PDF citation)
- `backend/data/manual_grounding/structured_requirements_2026_05.json` (target)

## Counts

- **Initial HIGH / STRUCTURED_EVIDENCE_READY:** 3 (D-2 extension, D-4-1/D-4-7 extension, E-7 extension)
- **Final HIGH / STRUCTURED_EVIDENCE_READY:** 4
- **Entries promoted this PR:** 1 (D-2 registration)
- **Total structured entries:** 337 → 338
- **Total document items:** 2,546 → 2,550

## Entries promoted

| statusCode | subCode | procedureType | boundaryType | source file | page range | section title | source excerpt (head) | docs | old conf/review/readiness | new conf/review/readiness | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-2 | — | registration | parent_code_level | stay_manual_2026_05.pdf | 44-44 | 유학(D-2) — 외국인등록 / 1. 제출서류 | `외국인등록 / 1. 제출서류 / ❍ 신청서, 여권 및 사본 1부, 표준규격사진 1매 …` | 4 | (auto block, garbled) / needs_human_review / NEEDS_SCENARIO_REVIEW | HIGH / source_confirmed / STRUCTURED_EVIDENCE_READY | PDF p.44 verified: single procedure (외국인등록), parent-level for 유학(D-2), no sub-code split; 대체서류/수수료 conditions captured as document-level `conditionKo` (not flattened). |

The four parent-level documents: ① 신청서, 여권 및 사본 1부, 표준규격사진 1매 · ② 수수료
(연장 동시신청 시 면제 / 면제대상자도 등록증 발급·재발급 수수료 납부) · ③ 재학(연구생)증명서
(대체서류: 인증대학 이상 등록금납입증명서 / 일반대학 이하 협조요청서·등록금납입증명서) ·
④ 체류지 입증서류 (재정능력 입증서류 제출 불요).

## Entries not promoted (priority targets) — blockers by category

| statusCode | procedure | blocker category | detail |
|---|---|---|---|
| D-4 | registration / other | sub_code_split | pp.83-101 split across D-4-1/7, D-4-2K, D-3; no parent-level list (extension D-4-1/7 already promoted). |
| C-3 | various | sub_code_split + scenario_split | 12 entries all sub_code/scenario specific (C-3-1..C-3-11); short-term status; no parent-level single-procedure list. |
| F-6 | extension | sub_code_split + conditional | pp.491-495 handle 체류기간 연장허가 separately for F-6-1/F-6-2/F-6-3 with distinct income/document conditions. |
| G-1 | various | scenario_split | 기타(G-1) is intrinsically heterogeneous (humanitarian/refugee/medical); scenario-specific blocks only. |
| H-2 | other | procedure_not_isolable | multi-procedure "other" bundles; page citation unverified; production marks 신규발급 중단. |
| D-10 | other | sub_code_split + procedure_not_isolable | references D-10-1/2/3 (p.159) with mixed procedures; "other" bundles. |
| E-7 | registration / other (37 entries) | sub_code_split + procedure_not_isolable | pp.212-323, dozens of occupation codes; no additional clean parent-level list beyond the already-promoted extension. |

**Blocker categories summary:** `sub_code_split` (D-4, C-3, F-6, D-10, E-7),
`scenario_split` (C-3, G-1), `procedure_not_isolable` / multi-procedure "other"
(H-2, D-10, E-7), `conditional` (F-6). The dominant structural blocker remains that
auto-extracted entries bundle multiple procedures (`procedureType: "other"`, 315/338)
and most document blocks are sub-code/scenario-scoped — exactly what PR #227 found.
Promotion requires a clean single-procedure, parent-level list, which among the
priority targets exists (and was not already promoted) only for D-2 registration.

## Legacy JSON changes

**None.** The D-2 production record's `procedures.registration.manualRefs` is already
`p. 44` — now independently PDF-verified as correct, so no change was needed. No
sub-code/scenario/conditional evidence was pushed into flat parent fields. `verified`
was not set; `needsManualReview` was not removed. `visa_data.json` /
`backend/data/visas.json` are unchanged and remain byte-identical.

## Runtime exposure changes

- `/api/visas`: the D-2 record's additive `sourceConfirmedStructuredRequirements` now
  carries **2** entries (extension + registration) instead of 1.
- `GET /api/visas/D-2/structured-requirements`: `sourceConfirmedCount` 1 → 2.
- AI grounding: the "Source-confirmed structured requirements from 2026-05 official
  manuals" block for D-2 now includes the 외국인등록 (registration) list.
- D-4, E-7 unchanged; all needs-review/high-risk statuses (C-3, F-6, G-1, H-2, D-10,
  E-7 candidate rows, …) remain hidden — verified by tests.

## Tests added / updated

`backend/tests/test_structured_requirements.py` — new `StructuredRequirementsPromotionTests`:
total source-confirmed count == 4; D-2 exposes both extension + registration; D-2
registration is parent_code_level / p.44 / 4 parent-level docs; `/api/visas` D-2 and
the dedicated endpoint expose registration; AI block for D-2 includes 외국인등록;
high-risk statuses still hidden after promotion. (230 backend tests pass total.)

## Validation results

```
python3 scripts/validate_structured_requirements.py <structured>   # PASS (338 entries, 2550 docs, 4 HIGH/READY)
python3 -m json.tool <structured> / <mirror> / <index> / <candidates>   # PASS
python3 -m json.tool visa_data.json / backend/data/visas.json / doc_master.json   # PASS (unchanged)
python3 scripts/sync_visa_data.py --check                          # OK (byte-identical)
python3 scripts/check_required_documents_coverage.py               # PASS (rc=0)
bash scripts/check_repo.sh                                         # rc=0
python3 -m pytest backend/tests/                                   # 230 passed
```

## Explicit non-goals

- No exposure of unreviewed candidate evidence (the 334 needs-review entries stay hidden; verified by tests).
- No metadata promotion on production records (`verified=true` not set; `needsManualReview` retained).
- No law grounding activation.
- No broad UI redesign (the existing PR #229 conditional panel simply gains the D-2 registration row).
- No unsourced required-document corrections (the one promotion is verbatim from PDF p.44).
- No flattening of sub-code/scenario/conditional requirements into parent records (D-2 conditions kept as document-level `conditionKo`; all non-parent targets deferred).
- No merging of visa issuance and stay/residence evidence.
- No modification to employment helper data / `data/jobcode_master.json`.
