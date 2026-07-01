# Review — E-7-M (K-CORE) 체류자격 변경 grounding candidate

> **Status: DRAFT candidate. NOT active grounding.** Nothing in this
> directory is read by `/api/ask`. Promotion into the active fixture
> (`backend/data/manual_grounding/stay_manual_grounding_2026_05.json`)
> requires a separate, human-authored, reviewed PR and
> `human_review.decision = "approved"`.

## Source

- **Manual:** 「육성형 전문기술인력 제도」 사증·체류관리 매뉴얼 (법무부 외국인정책과, 2026.6)
- **Effective:** 2026-03-05 · **Distributed:** 2026-06-29
- **Committed source (standard/non-distribution HWP):**
  `backend/data/sources/manuals/260629_kcore_manual.hwp`
  (SHA-256 `391bb05c5a848285e4ed6b8dba545c4c33dcacdb592cae3f147fb176af8a9f3e`, 130,560 bytes)
- **Readable extraction:** `backend/data/sources/manuals/260629_kcore_manual_readable.txt`
  (SHA-256 `156224395214d1fc99a0e798d21977a433cd523e2af06dd50a6eca5013bbadfd`)
- **Section index:** `backend/data/sources/manuals/260629_kcore_manual_sections.json` (logical section 5 = `(1) 체류자격 변경`)

Unlike the large HiKorea 사증/체류 안내 매뉴얼 (distribution-mode HWP whose
body cannot be extracted on Linux), this K-CORE program manual is a **standard
non-distribution HWP** (FileHeader flag `0x1`, no `0x4`). Its body was fully and
deterministically extracted with the builtin `olefile` HWPTAG_PARA_TEXT parser
(`scripts/extract_kcore_manual_260629.py`).

## What was verified locally

- [x] `required_documents` match the manual's `❍(제출서류)` list under `(1) 체류자격 변경` verbatim (외국인 준비서류 ①–④ + 업체 준비서류 ⑤–⑦).
- [x] Eligibility / 심사기준 (졸업요건, 한국어·사회통합 요건, 취업요건, 쿼터 완화) copied verbatim from logical section 5.
- [x] 체류기간 (고용계약기간 + 3개월, 최대 3년) confirmed in section 5.
- [x] New 세부약호 `E-7-M(K-CORE 비자)` and 직종코드 `9991(육성형 전문기술이민)` confirmed in section 6 (Ⅳ. 행정사항).
- [x] 체류자격 변경 제한 (육성형 전문기술학과 유학생 외 변경 불가) confirmed in section 5 `(4)`.

## What still requires domain-expert review before promotion

- [ ] Splitting per-procedure grounding: this candidate covers **체류자격 변경** only. 체류기간 연장 and 근무처 변경·추가 have their own 제출서류 lists (manual Ⅲ-2 (2),(3)) and need separate entries.
- [ ] "적정임금" interpretation and the 연봉 2,600만원 threshold's adjustment clause (숙련기능인력 E-7-4 수준, 변동 가능).
- [ ] Interaction with the general 「특정활동(E-7) …지침」 for matters not covered by this pilot manual.
- [ ] Whether/when to add E-7-M to the backend `_GROUNDED_VISA_CODES` selection for a `체류자격 변경` task type (currently the active fixture only grounds `체류기간 연장허가`; this candidate's `procedure_type` intentionally does not match it, so an accidental promotion cannot be selected at runtime).

## Safety properties

- `procedure_type = "체류자격 변경"` ≠ the active fixture's `체류기간 연장허가`, so `_select_grounding()` cannot select this even if promoted by mistake.
- File lives under `candidates/`, which the backend never loads.
- `human_review.decision = "pending"` → `scripts/promote_grounding_candidate.py` refuses to promote.

Reviewer: _(unassigned — pending domain-expert signoff)_
