# 2026-05-21 Data-Reference Patch — Batch 1 (PR D batch 1)

Branch: `data/patch-2026-05-21-data-reference-batch-1`
Audit date: 2026-05-25
PR: **D batch 1** (after PR #159)

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

This is **PR D batch 1**, the coordinated data-reference follow-up to:
- **PR #157** (merged) — regenerated the TOC map / crosswalk / audit artifacts against the canonical **484-page visa** and **777-page stay** PDFs installed by PR #155.
- **PR #159** (merged) — completed PR C safe metadata/doc-ref hygiene and deferred coordinated production-data edits.

**Scope statement:** This batch performs coordinated, page-cited data-reference patches that require editing production data files, **without** rewriting any substantive immigration/legal guidance text. **No eligibility, fees, income thresholds, stay periods, procedures, or required-document meanings were changed. No `verified=true` promotions. No `needsManualReview` removals. No records deleted. No UI changes.**

---

## Changed files

| File | Change |
|---|---|
| `visa_data.json` | G-1 record: 3 stale stay-section page references `pp. 502-517` → `pp. 498-513` |
| `backend/data/visas.json` | Mirrored via `scripts/sync_visa_data.py` (sync only) |
| `docs/data/2026_05_21_DATA_REFERENCE_PATCH_BATCH_1.md` | New report (this file) |
| `docs/data/2026_05_21_data_reference_patch_batch_1.json` | New machine-readable report |

---

## Page-reference anchor correction (the one change applied)

### G-1 (기타(난민등), array index 45) — stay section `pp. 502-517` → `pp. 498-513`

Three occurrences in the G-1 record, all the same stale stay-section pointer, were corrected:

| Field | Old | New |
|---|---|---|
| `procedures.registration.summary` (page citation inside the audit note text) | `…매뉴얼 pp. 502-517에서…` | `…매뉴얼 pp. 498-513에서…` |
| `procedures.registration.manualRefs[0].pageRange` | `pp. 502-517` | `pp. 498-513` |
| `manualRequiredDocAudit.sectionPageRange` | `pp. 502-517` | `pp. 498-513` |

**Evidence:**
- **Audit artifact:** `docs/data/2026_05_21_manual_toc_map.json` / `…_MANUAL_TOC_MAP.md` — stay §34 `기 타(G-1)` re-derived to **pp.498-513** (was `pp.502-517` in the pre-#155 774-page map).
- **Crosswalk:** `docs/data/2026_05_21_manual_json_crosswalk.json` — G-1 `stay_pages` = `498-513`.
- **Direct PDF extraction** (`pdftotext -layout -f N -l N` on `stay_manual_2026_05.pdf`): p498 = `기 타(G-1)` section header; p513 = still G-1 content (`나. 체류허가기간`); p514 = `관광취업(H-1)` header. Confirms G-1 = **pp.498-513**.
- **Staleness:** the old `pp.502-517` starts 4 pages after the re-derived G-1 header (p498) and over-runs into the re-derived **H-1** section (pp.514-517) — i.e., it pointed partially outside the re-derived G-1 section.

**Why this is safe:** the G-1 `registration` procedure's `requiredDocs` is the placeholder `["매뉴얼 확인 필요"]` with `needsManualReview=true`; no substantive document is asserted. Correcting the reviewer page pointer changes no document requirement, eligibility, fee, income, stay period, or procedure. The current value exactly equaled the pre-#155 full G-1 section range (502-517), proving the field held the section anchor; PR #157 + direct PDF extraction give the exact re-derived range (498-513). `verified` remains `false`; `needsManualReview` remains `true`.

---

## doc_master ID migration — DEFERRED to PR D-2 (blocker documented)

**The coordinated doc_master ID migration was not performed in this batch**, because it cannot be done safely under the hard constraints *"Do not make UI changes"* and *"preserve user-facing document meaning."*

**Finding:** the frontend `index.html` resolves document tokens via its own `DOC_DICT` map (`index.html:10104`), **not** via `doc_master.json`. The resolution at `index.html:11537` is:

```js
let officialName = DOC_DICT[key] || (typeof key === 'string' && key.startsWith('doc_') ? `문서요건(${key.replace('doc_','').replace(/_/g,' ')})` : key);
```

- The 12 corrupted Korean-string IDs are **not** keys in `DOC_DICT` (count = 0 in `index.html`), so they currently render via the **raw-string fallback** as their own readable Korean document names.
- If they were renamed to machine IDs (`doc_*`) in `visa_data.json` **without** adding matching `DOC_DICT` entries, the renderer would display a generic placeholder `문서요건(...)` instead of the Korean document name — **destroying** user-facing document meaning.
- Adding `DOC_DICT` entries is a **UI change**, which is out of scope for this batch.

Therefore the full migration (doc_master rename + `visa_data.json` reference updates + `index.html` `DOC_DICT` additions, in lockstep) is deferred to **PR D-2**.

The 12 IDs pending migration:

`개별 사안별 증빙서류(매뉴얼 해당 항목 및 관할기관 안내 기준)`, `변경 사유 입증서류(활동계획서·초청서·고용계약서 등 해당 자격별)`, `사증발급신청서(별지 제17호 서식)`, `사진 1매(해당 시)`, `수수료`, `여권`, `여권 및 외국인등록증`, `체류자격별 개별 첨부서류(매뉴얼 해당 자격 항목 참조)`, `체류지 입증서류`, `통합신청서`, `통합신청서(체류자격변경허가 신청 포함)`, `표준규격사진 1매`.

> **Near-duplicate note:** some of these exactly match existing `doc_*` `ko_name`s (`여권`=`doc_passport`, `체류지 입증서류`=`doc_address`, `통합신청서`=`doc_app_form`). A future migration could repoint + dedupe, but the entries' `en_name`/`description` differ, so display/usage identity must be confirmed before collapsing. PR D-2.

---

## Page anchors deliberately deferred to PR D-2 (cannot prove exact value)

| Record | Current value | Reason for deferral |
|---|---|---|
| F-2 | `pp. 358-424` | Idiosyncratic (starts at 358; matches neither pre-#155 `360-424` nor re-derived `360-420`). Exact intended sub-range unprovable from PR #157 alone. |
| F-3 | `pp. 425-428` | Sub-range, not the pre-#155 full section (`425-441`). Re-derived F-3 = `421-425`; exact doc-list sub-range needs page-cited re-derivation. |
| F-5 | `pp. 429-477` | Idiosyncratic (starts at 429; pre-#155 section `442-477`). Re-derived F-5 = `426-473`; also a `partial` (split §32/§36) record. |
| H-1 | `pp. 518-525` | Not the pre-#155 full section (`518-521`); over-runs to 525. Re-derived H-1 = `514-517`. |

Per-procedure **fine citations** (e.g. G-1 extension `p. 513`, F-2 `p. 394`, D-9 `p. 133/136`, D-7 `p. 112`) were left unchanged: the stay sections shifted, so the precise page of a specific cited paragraph must be re-derived by page extraction before changing a single-page citation — a TODO is preferred over guessing.

`D-7` (`pp. 108-114`) and `D-9` (`pp. 130-141`) section anchors already match the re-derived ranges; no change needed.

---

## PR D-2 queue

1. **doc_master ID migration** of the 12 corrupted Korean-string IDs, in lockstep with `index.html` `DOC_DICT` additions (and near-duplicate dedupe vs `doc_passport`/`doc_address`/`doc_app_form` after confirming display identity).
2. **F-6** income note / content (stay §33 pp.474-497, visa §34 pp.324-335) — page-cited.
3. **D-4-2K** duplicate/sub-code resolution (array indices 24 + 55).
4. **F-4 / H-2** 외국국적동포 Feb-2026 sub-manual content (stay §36 pp.518-584).
5. **K-STAR** records (visa §40 pp.456-484 / stay §41 pp.749-777).
6. **REGION-S / 지역특화형** (stay §37 pp.585-654) / **광역형** (stay §40 pp.686-748) records.
7. **Page-anchor sub-range corrections** for F-2, F-3, F-5, H-1 and per-procedure fine citations, with exact PDF page extraction.
8. Any **requiredDocuments** additions/removals requiring exact page evidence.

---

## Validation results

| Check | Result |
|---|---|
| `python3 -m json.tool` (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`, this report JSON, 3 PR #157 JSON artifacts) | ✅ all valid |
| `scripts/sync_visa_data.py --check` | ✅ OK (backend matches visa_data.json) |
| `scripts/check_source_manuals.py` | ✅ OK (484 / 777) |
| `scripts/check_source_updates.py --local-only` | ✅ OK |
| `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| `scripts/check_required_documents_coverage.py` | ✅ no regressions |
| `scripts/validate_coverage_matrix.py` | ✅ OK |
| `scripts/validate_manual_grounding_candidate.py` | ✅ OK |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ pass (194 backend tests OK; git diff clean) |

---

## Statements

- **No substantive legal/admin guidance text was rewritten.** No eligibility, fees, income thresholds, stay periods, procedures, or required-document meanings were changed.
- **`verified` remains `false`** for all records (unchanged).
- **`needsManualReview` was not removed** from any record (unchanged).
- **`backend/data/visas.json` was updated only through `scripts/sync_visa_data.py`.**
- The only production-data change is the G-1 stay-section page-anchor correction (`pp. 502-517` → `pp. 498-513`), grounded in PR #157 artifacts and direct PDF extraction.

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
