# High-Confidence Data Update — 2026.5 Manuals

**Date:** 2026-06-07
**Applies to:** `visa_data.json` (canonical) + `backend/data/visas.json` (synced)
**Driver:** `scripts/apply_registration_docs_source_confirmed_2026_06.py`
**Audit basis:** `docs/data/DATA_COVERAGE_AUDIT_2026_05_MANUALS.md`

Only changes that satisfy **every** Phase-3 gate were applied: direct page-level
source evidence in the committed official manual; exact file/page/section
recorded; unambiguous procedure type; clear document list; clear sub-code
mapping with **no flattening**; real data gap; existing production schema;
verifiable by existing scripts.

---

## 1. Updated codes / procedures

Three previously **empty** foreigner-registration (외국인등록) document lists were
populated at the parent `procedures.registration` level. Each manual section
presents a **single** registration list for the status (not split per sub-code),
so reproducing it at parent level does **not** flatten scenario-specific data.

| Code | Procedure | Before | After (groups) |
|---|---|---|---|
| **E-10** 선원취업 | registration | empty (`준비 중`) | common 4 · required 5 |
| **D-8** 기업투자 | registration | empty (`준비 중`) | common 4 · required 2 · conditional 1 |
| **H-1** 관광취업 | registration | empty (`준비 중`) | common 4 · required 2 · conditional 1 |

### Exact content (verbatim from manual, common items via existing doc tokens)

**E-10 — stay manual pp. 338–339, "외국인등록 / 1. 외국인등록 신청서류"**
- commonDocs: 신청서(별지 제34호 서식) · 여권 원본 · `doc_standard_photo_one` · `doc_fee_generic`
- requiredDocs: 내항여객운송사업면허증 또는 내항화물운송등록증 · 건강검진서(밀봉된 상태로 제출, 개봉 불가) · 마약검사 확인서(밀봉된 상태로 제출, 개봉 불가) · 산업재해보상보험 또는 상해보험 가입증명원 · `doc_residence_proof_generic`

**D-8 — stay manual p. 126, "외국인등록 / 1. 외국인등록 신청서류"**
- commonDocs: 신청서(별지 제34호 서식) · 여권 원본 · `doc_standard_photo_one` · `doc_fee_generic`
- requiredDocs: 사업자등록증 · 체류지 입증서류(부동산 임대차계약서 등)
- conditionalDocs: 법인 등기사항전부증명서(법인기업인 경우)
- note: 재외공관에서 D-8을 직접 받아 입국한 경우 체류자격 변경신청 제출서류 준용 (`☞` from p. 126).

**H-1 — stay manual p. 517, "외국인등록 / 제출서류" (90일 초과 체류자 대상, 협정상 예외 없음)**
- commonDocs: 신청서(별지 제34호 서식) · `doc_passport_generic` · `doc_standard_photo_one` · `doc_fee_generic`
- requiredDocs: 여행일정 및 활동계획서 · 체류지 입증서류(월세계약서 등)
- conditionalDocs: 근무처의 사업자등록증 사본 및 계약서 등(취업 중인 경우)
- **Note:** this is the **H-1-specific** section (working-holiday wording), **not** a
  borrowed/fallback list — directly addressing the QA "borrowed list" concern for H-1.

### Metadata changes (per filled procedure)
- `manualRefs[0].pageRange` tightened to the exact page(s); `.section` added
  (e.g. `외국인등록 신청서류`); `.confidence` raised from `needs_manual_review`
  (vague wide range) to the existing **`manual_page_extract_needs_review`**.
- `needsManualReview` kept **true** at the ref and record level (conservative posture).
- `manualRequiredDocAudit` annotated: `registrationDocsPage`, `registrationDocsSection`,
  `registrationDocsMethod = pdf_text_manual_page_verified`, `registrationDocsUpdatedAt`.
- A source note appended to `procedures.registration.notes` (no existing caution
  note was removed or weakened).

---

## 2. Source evidence used

| Code | File | Page | Section header | Page-mapping check |
|---|---|---|---|---|
| E-10 | `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` | pp. 338–339 | 외국인등록 / 1. 외국인등록 신청서류 | footer `- 338 -` / `- 339 -` verified |
| D-8 | same | p. 126 | 외국인등록 / 1. 외국인등록 신청서류 | footer `- 126 -` verified |
| H-1 | same | p. 517 | 외국인등록 / 제출서류 | footer `- 517 -` verified |

---

## 3. Production data files changed

- `visa_data.json` (canonical)
- `backend/data/visas.json` (kept in sync via `scripts/sync_visa_data.py`)
- `scripts/apply_registration_docs_source_confirmed_2026_06.py` (new, reproducible
  applier — idempotent, asserts empty pre-state before writing)

No `index.html` change: the app fetches `./visa_data.json` at runtime.

---

## 4. What was intentionally NOT updated

- **D-10 registration** — no 외국인등록 list in the D-10 chapter (pp. 142–165).
- **F-2 / G-1 registration** — sub-code-specific; no parent-level list.
- **H-2** — `신규발급 중단` (policy-limited); appendix-only source.
- **B-1 registration** — exceptional; no status-specific list.
- **H-1 extension / reentry** — current values not re-verified (borrowed-list risk).
- **E-10 extension** — two distinct scenarios with different doc sets → flatten risk.
- **D-10 extension raw strings** — quality cleanup deferred (not a coverage gap).
- No AI grounding / logic changed; no UI redesign; no theme change; no disclaimer
  or source-warning weakened.

---

## 5. Remaining source-limited / source-missing cases

`source-missing`: D-10, F-2, G-1, B-1 registration.
`policy-limited`: H-2 (all procedures).
`data-present-needs-source-check`: H-1 extension/reentry, D-10 extension.
See `docs/data/DATA_COVERAGE_AUDIT_2026_05_MANUALS.md` §5–§7 for the full list and
recommended follow-up PRs.

---

## 6. Verification results

Commands run (all pass):

- `python3 -m json.tool visa_data.json` → OK
- check_repo.sh step [3] schema (representative + every status-code record:
  procedures.extension/registration present, manualRefs non-empty,
  requiredDocs.requiredDocs is a list, no unknown `doc_` tokens,
  manualRequiredDocAudit.manualVersion == 2026.5) → **NONE** (no errors)
- `scripts/check_visa_text_corruption.py` → OK
- `scripts/check_visa_data_text_integrity.py` → PASS
- `scripts/check_visa_data_domain_classification.py` → OK (58 records)
- `scripts/sync_visa_data.py --check` → in sync
- `scripts/check_required_documents_coverage.py` → PASS (no regressions)
- `node scripts/check_i18n.js` → OK
- `node scripts/check_procedure_journey_audit.js` → 11 passed / 0 failed
  (includes placeholder-detection, duplicate-doc, raw-diagnostic detection)
- `node scripts/check_static_visa_result_cards.js` → OK
- `git diff --check` → clean

Rendered-output spot check confirmed all `doc_` tokens resolve to Korean labels
and the filled lists match the manual pages verbatim.
