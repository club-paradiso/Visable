# Foreign Registration Full Coverage Audit — 2026.05

> Internal data audit for Paradiso. This document is reference material for
> structured-data development; it is **not** legal advice, an official immigration
> determination, or a Ministry of Justice publication.

---

## Purpose

PR #173 fixed the renderer so the 외국인등록 document tab can fall back from
`documents_registration` to `procedures.registration.requiredDocs`. Despite that fix,
most status records still reach the structured-data-missing empty state at runtime.

This audit classifies **every top-level record in `visa_data.json`** by whether its
외국인등록 document data is:

- **(A) displayable** — already structured and renderable,
- **(B) source-grounded but not yet structured** — manual page reference exists; docs need to be extracted and placed into schema,
- **(B') placeholder_extracted** — `available=true` with raw extracted text in `summary`, but `requiredDocs` still holds only placeholder values,
- **(C) conditionally applicable** — registration may or may not apply depending on scenario or sub-code,
- **(D) not a visa/status record** — helper, FAQ, or scenario guide; registration tab should not appear.

This PR does **not** patch `visa_data.json` registration content. Its purpose is to
produce the full classification table and the machine-readable JSON report that
inform safe follow-up patch batches.

---

## Scope

- **Primary source:** `visa_data.json` (58 top-level records)
- **Secondary source:** `backend/data/visas.json` (synced mirror, validated for parity)
- **Manual sources:** 2026.5 canonical PDFs in `docs/source-manuals/2026-05/`
  - `stay_manual_2026_05.pdf` — **777 pages** (updated from 774 in PR #155)
  - `visa_manual_2026_05.pdf` — **484 pages**
- **TOC evidence:** `docs/data/2026_05_21_manual_toc_map.json` (re-derived from canonical PDFs in PR #155)
- **Prior audit:** `docs/data/FOREIGN_REGISTRATION_PROCEDURE_AUDIT_2026_05.md` (PR #173)
- **Audit script output:** `docs/data/foreign_registration_full_coverage_2026_05.json`

Sub-codes nested inside `subCodes` arrays are **not** classified individually here;
top-level records serve as the proxy for their sub-code variants.

---

## Source Hierarchy

1. Canonical 2026.5 Ministry of Justice manuals committed at `docs/source-manuals/2026-05/`
   — primary ground truth for all page references and document requirements.
2. Extracted TOC map `docs/data/2026_05_21_manual_toc_map.json`
   — section anchor pages re-derived from canonical PDFs (PR #155).
3. Existing extracted audit reports in `docs/data/`
   — secondary evidence; used where direct PDF text is not re-extracted in this session.
4. `visa_data.json` and `backend/data/visas.json`
   — derived structured data; reflects prior extraction cycles.

`pdftotext` is **not available** in the current execution environment. Section page
ranges come from the committed TOC map, not from a live extraction in this session.
See _Known Limitations_ below.

---

## Method

1. Load all 58 top-level records from `visa_data.json`.
2. For each record, evaluate in priority order:
   - Is this a helper/FAQ/scenario record (non-visa)?
   - Does `procedures.registration.requiredDocs` contain at least one non-placeholder string?
   - Is the record a short-stay code where registration rarely applies?
   - Is `available=true` but every doc string is a placeholder?
   - Does a `manualRefs` page reference exist (source-grounded, not yet structured)?
   - No signal at all.
3. Apply secondary flags: `needs_manual_page_review`, `source_range_missing_or_out_of_bounds`,
   `frontend_backend_sync_mismatch`, `duplicate_code`.
4. Cross-reference the TOC map to verify that a stay-manual section exists for the code
   and note the detected page range and confidence level.
5. Write machine-readable output to `docs/data/foreign_registration_full_coverage_2026_05.json`.

Script: `python3 scripts/audit_foreign_registration_full_coverage.py`

---

## Classification Definitions

| Symbol | Primary category | Meaning |
|--------|-----------------|---------|
| **A** | `displayable_registration_docs` | `procedures.registration.requiredDocs` (or `documents_registration`) contains ≥1 concrete string that is not a known placeholder. UI can render this data today. All current A records retain `needsManualReview: true` and should not be presented as officially verified. |
| **B** | `procedure_only_registration_docs` | `manualRefs` with a valid page range exists and `available: false`. Docs are all placeholder. Source-grounded but not yet structured. Needs manual page review and a structuring patch. |
| **B'** | `placeholder_registration_docs` | `available: true` but `requiredDocs` contains only placeholder values. Raw extracted text in `summary` field provides a starting point for structuring. High priority. |
| **C** | `conditionally_applicable_registration` | Short-stay status code (B-1, B-2, C-1, C-4) where foreign registration is generally **not** required for the typical entry (stays under 90 days). Manual section may exist but is likely to cover extension only, or to note registration inapplicability. Needs page-level review before any doc is added. |
| **D** | `non_visa_helper_record` | FAQ, scenario, guide, or administrative helper record. This is not a visa/status entry. Should not show 외국인등록 document tabs. |

Secondary flags are non-exclusive additions that can co-exist with any primary category.

---

## Summary Counts

| Category | Count | Codes |
|----------|-------|-------|
| **A** displayable_registration_docs | 6 | C-3, D-2, F-6, A-1, A-2, A-3 |
| **B'** placeholder_registration_docs | 1 | D-9 |
| **B** procedure_only_registration_docs | 30 | D-1, D-3, D-4, D-4-2K ×2, D-5, D-6, D-7, D-8, D-10, E-1–E-10, F-1–F-5, G-1, H-1, H-2, K-STAR, REGION-S |
| **C** conditionally_applicable_registration | 4 | B-1, B-2, C-1, C-4 |
| **D** non_visa_helper_record | 17 | K-ETA, TB-1, SCN-1–6, OVS-1, NHIS-1, FAQ-1–4, VW-1, COM-1, RF-1 |
| **Total** | **58** | |

| Secondary flag | Count | Notes |
|---------------|-------|-------|
| `needs_manual_page_review` | 41 | All records with `needsManualReview: true` in any `manualRefs` entry. |
| `duplicate_code` | 2 | D-4-2K appears twice (한국어연수/K-연수생 and 기업맞춤형인턴십/K-Trainee). |
| `source_range_missing_or_out_of_bounds` | 0 | No page references exceed the 777 / 484 canonical limits. |
| `frontend_backend_sync_mismatch` | 0 | `visa_data.json` and `backend/data/visas.json` are in sync. |

---

## Full Coverage Table

> `conf` = TOC-map detection confidence for the stay-manual section anchor.
> All manualRefs page numbers are within the canonical page limits (stay: 777, visa: 484).

| Code | Name | Cat | Primary category | Registration status | Current data path | Stay-manual evidence | Recommended action |
|------|------|-----|-----------------|-------------------|-------------------|---------------------|-------------------|
| K-ETA | 전자여행허가 종합 가이드 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| TB-1 | 결핵 고위험국가 진단서 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-1 | 글로벌 의사결정 매트릭스 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-2 | 실무 변수 체크리스트 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-3 | C-3 자격변경 시나리오 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-4 | F-1-6 혼인단절 시나리오 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-5 | F-4/H-2 동포 제약 시나리오 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| SCN-6 | 오버스테이 시나리오 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| OVS-1 | 불법체류다발국가 목록 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| NHIS-1 | 건강보험 면제·감면 | nhis | **D** non_visa_helper | n/a | none | — | Suppress tab |
| FAQ-1 | 외국인등록 및 체류지 변경 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| FAQ-2 | 체류기간 연장·자격 변경 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| FAQ-3 | 재입국허가 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| FAQ-4 | 전자팩스·오버스테이·국적 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| VW-1 | 무사증·사증면제 구분 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| COM-1 | 비자 공통 구비서류·팁 | faq | **D** non_visa_helper | n/a | none | — | Suppress tab |
| RF-1 | 난민인정신청 제출서류 안내 | scn | **D** non_visa_helper | n/a | none | — | Suppress tab |
| B-1 | 사증면제협정 | short | **C** conditionally_applicable | Short-stay; reg. rarely applies | manualRefs page ref only | pp.24-24 conf=high | Manual page review first |
| B-2 | 관광통과·무사증 | short | **C** conditionally_applicable | Short-stay; reg. rarely applies | manualRefs page ref only | pp.25-25 conf=high | Manual page review first |
| C-1 | 일시취재 | other | **C** conditionally_applicable | Short-stay; reg. rarely applies | manualRefs page ref only | pp.26-26 conf=high | Manual page review first |
| C-3 | 단기방문 | short | **A** displayable | Displayable (Chile C-3-4 case) | procedures.registration.requiredDocs | pp.27-28 conf=high | Retain; verify sub-code scope |
| C-4 | 단기취업 | short | **C** conditionally_applicable | Short-stay; reg. rarely applies | manualRefs page ref only | pp.29-31 conf=high | Manual page review first |
| D-1 | 문화예술 | study | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.32-34 conf=high | Batch 2 patch |
| D-2 | 유학 | study | **A** displayable | Displayable | procedures.registration.requiredDocs | pp.35-55 conf=high | Retain; verify docs |
| D-3 | 기술연수 | study | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.56-82 conf=high | Batch 2 patch |
| D-4 | 일반연수 | study | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.83-101 conf=high | Batch 2 patch |
| D-4-2K | 한국어연수(K-연수생) | study | **B** procedure_only ⚠️duplicate | Source-grounded, not structured | manualRefs (page ref) | pp.83-101 (extraction) | Resolve duplicate; Batch 2 |
| D-5 | 취재 | other | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.102-104 conf=high | Batch 5 patch |
| D-6 | 종교 | other | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.105-107 conf=high | Batch 5 patch |
| D-7 | 주재 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.108-114 conf=high | Batch 3 patch |
| D-8 | 기업투자 | invest | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.115-129 conf=high | Batch 3 patch |
| D-9 | 무역경영 | work | **B'** placeholder_extracted | available=True, docs placeholder | requiredDocs (placeholder) | pp.130-141 conf=high | **Batch 1** (high priority) |
| D-10 | 구직 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.142-165 conf=high | Batch 3 patch |
| E-1 | 교수 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.166-175 conf=high | Batch 3 patch |
| E-2 | 회화지도 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.~176-184 conf=low | Batch 3 patch (low-conf section) |
| E-3 | 연구 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.185-194 conf=high | Batch 3 patch |
| E-4 | 기술지도 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.195-199 conf=high | Batch 3 patch |
| E-5 | 전문직업 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.200-204 conf=high | Batch 3 patch |
| E-6 | 예술흥행 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.205-211 conf=high | Batch 3 patch |
| E-7 | 특정활동 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.212-323 conf=high | Batch 3 patch (large section) |
| E-8 | 계절근로 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.324-325 conf=high | Batch 3 patch |
| E-9 | 비전문취업 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.326-335 conf=high | Batch 3 patch |
| E-10 | 선원취업 | work | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.336-340 conf=high | Batch 3 patch |
| F-1 | 방문동거 | family | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.341-359 conf=high | Batch 4 patch |
| F-2 | 거주 | family | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.360-420 conf=high | Batch 4 patch |
| F-3 | 동반 | family | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.421-425 conf=high | Batch 4 patch |
| F-4 | 재외동포 | family | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | §38 special section (동포 sub-manual) | Batch 4 patch |
| F-5 | 영주 | family | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.426-473 conf=high | Batch 4 patch |
| F-6 | 결혼이민 | family | **A** displayable | Displayable | procedures.registration.requiredDocs | pp.474-497 conf=high | Retain; verify docs |
| G-1 | 기타(난민등) | other | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.498-513 conf=high | Batch 5 patch |
| H-1 | 관광취업 | other | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.514-517 conf=high | Batch 5 patch |
| H-2 | 방문취업 | other | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | §38 special section (동포 sub-manual) | Batch 5 patch |
| A-1 | 외교 | diplo | **A** displayable | Displayable (voluntary) | procedures.registration.requiredDocs | pp.14-17 conf=high | Retain; note voluntary nature |
| A-2 | 공무 | diplo | **A** displayable | Displayable (voluntary) | procedures.registration.requiredDocs | pp.18-20 conf=high | Retain; note voluntary nature |
| A-3 | 협정 | diplo | **A** displayable | Displayable (voluntary) | procedures.registration.requiredDocs | pp.21-23 conf=high | Retain; note voluntary nature |
| D-4-2K | 기업맞춤형인턴십(K-Trainee) | study | **B** procedure_only ⚠️duplicate | Source-grounded, not structured | manualRefs (page ref) | pp.83-101 (extraction) | Resolve duplicate; Batch 2 |
| K-STAR | K-STAR 비자트랙 | etc | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.746-757 (extraction)¹ | Batch 5 patch |
| REGION-S | 지역특화·광역형 비자 시범사업 | etc | **B** procedure_only | Source-grounded, not structured | manualRefs (page ref) | pp.696-745 (extraction) | Batch 5 patch |

> ¹ K-STAR `manualRefs` cites pp.746-757; TOC map places the K-STAR special section at pp.749-777. Pages 746-748 may belong to the preceding section. Minor discrepancy; manual page review required.

---

## Records with Displayable Registration Documents (Category A)

These six records are currently rendered by the UI fallback introduced in PR #173.
All retain `needsManualReview: true` and should not be presented as officially verified.

| Code | Name | Concrete docs | Manual page | Notes |
|------|------|--------------|-------------|-------|
| C-3 | 단기방문 | 3 items | 체류민원 p.28 | Specific to Chilean C-3-4 nationals staying ≥91 days. Scope note should be displayed with docs. |
| D-2 | 유학 | 7 items | 체류민원 p.44 | Auto-extracted. Confidence=auto_extracted_needs_review. |
| F-6 | 결혼이민 | 5 items | 체류민원 p.494 | Representative docs from F-6-1 (90-day entry) case. |
| A-1 | 외교 | 1 item | 체류민원 p.17 | Registration is exempt for A-1 holders but voluntarily available. |
| A-2 | 공무 | 1 item | 체류민원 p.20 | Same as A-1; voluntary registration. |
| A-3 | 협정 | 2 items | 체류민원 p.23 | Auto-extracted. |

**Do not patch these records' registration docs in this PR.**
Existing `verified=false` / `needsManualReview=true` markers must be preserved until
manual page review confirms the structured content.

---

## Records That Should Be Patched in Later Batches (Categories B and B')

### D-9 (무역경영) — Top Priority (Category B')

D-9 has `available: true` and a rich raw `summary` field that already contains the
registration document list extracted from 체류민원 p.136. However, the
`requiredDocs.requiredDocs` field still contains only `"매뉴얼 확인 필요"`. The raw
text must be parsed and placed into the structured `requiredDocs` schema.

**Action:** Manual page review of 체류민원 pp.130-141; structure `requiredDocs` from
raw `summary` text + manual confirmation. Part of Batch 1.

### E-2 (회화지도) — Low-confidence TOC anchor

E-2's section is not detected by the spaced-Korean-header regex; the TOC map flags its
anchor as `conf=low` and estimates its range as pp.~176-184 (embedded after E-1 at
p.175 and before E-3 at p.185). When pdftotext becomes available, verify the exact
page range before structuring docs.

---

## Records Where No Registration Tab Should Appear (Category D)

The following 17 records are FAQ, scenario, or guide records. They are not visa status
entries and should not display a 외국인등록 document tab.

> K-ETA, TB-1, SCN-1, SCN-2, SCN-3, SCN-4, SCN-5, SCN-6, OVS-1, NHIS-1,
> FAQ-1, FAQ-2, FAQ-3, FAQ-4, VW-1, COM-1, RF-1

**Recommended action (Batch 5 / UI cleanup):** Suppress the 외국인등록 tab in the
renderer for records whose `cat` is `scn`, `faq`, or `nhis`, or whose code is in
the explicit helper-code list. This is a UI-only change; no `visa_data.json` edits required.

---

## Short-Stay Records with Conditional Applicability (Category C)

| Code | Name | Stay-manual section | Rationale |
|------|------|---------------------|-----------|
| B-1 | 사증면제협정 | pp.24-24 (1 page) | Visa-exempt; stays typically 30-90 days. Registration not required in normal case. Edge: some treaty nationals can stay >90 days, at which point registration applies. Needs manual page review to determine if registration docs are listed. |
| B-2 | 관광통과·무사증 | pp.25-25 (1 page) | Transit/no-visa; very short stays. Registration essentially not applicable except in status-change edge cases. |
| C-1 | 일시취재 | pp.26-26 (1 page) | Temporary press coverage; stays typically ≤90 days. Registration not standard. |
| C-4 | 단기취업 | pp.29-31 (3 pages) | Short-term employment; stays typically ≤90 days. Registration not required in normal case. |

The one-page stay-manual sections for B-1, B-2, and C-1 are unlikely to contain
foreign registration document lists. They may simply note extension conditions or
note inapplicability. Until pdftotext review confirms, do not add registration
documents for these codes.

---

## Records Requiring Manual Source Review

All 41 records with `needs_manual_page_review: true` in their `manualRefs` require
human review of the canonical stay manual before their registration docs can be
structured. This flag is present on all Category B and B' records, and also on all
six Category A records (retained intentionally).

Priority order for manual review:
1. D-9 — raw summary text already extracted; just needs structuring.
2. D-2, F-6, C-3, A-1, A-2, A-3 — already displayable but should be spot-checked.
3. D-1, D-3, D-4, D-7, D-8, D-10 — high-traffic study/work statuses.
4. E-series (E-1 through E-10) — large employment block.
5. F-series (F-1 through F-5) — family and residence statuses.
6. G-1, H-1, H-2, K-STAR, REGION-S, D-5, D-6 — miscellaneous.
7. B-1, B-2, C-1, C-4 — conditionally applicable; review to confirm no registration section.

---

## Data Integrity Finding: Duplicate D-4-2K Code

Two separate top-level records share the code `D-4-2K`:
- `name: 한국어연수(K-연수생)` — Korean language training (K-Trainee scheme)
- `name: 기업맞춤형인턴십(K-Trainee)` — Corporate-customized internship (K-Trainee scheme)

Both reference the same stay-manual page range (pp.83-101) and carry the same
`needs_manual_page_review` flag. This is a **code-collision bug** that should be
resolved in a separate data-integrity patch before either record is given structured
registration docs. A distinct code (e.g. `D-4-KT`) should be assigned to one of the
two.

**Action:** Flag for resolution in a separate data-integrity PR before Batch 2.

---

## Page-Limit Discrepancy (Informational)

The prior audit script `scripts/audit_registration_procedure_coverage.py` uses a
stay-manual page limit of **774**. The canonical 2026-05-21 PDF (installed in PR #155
and re-anchored in the TOC map) is **777 pages**. The updated script
`scripts/audit_foreign_registration_full_coverage.py` uses the correct limit of 777.

No existing `manualRefs` page number exceeds 774, so there are currently **no
out-of-bounds violations** under either limit. The discrepancy is informational only.
`audit_registration_procedure_coverage.py` should be updated to 777 in a follow-up patch.

---

## Known Limitations

1. **No live pdftotext.** This environment does not have `pdftotext` available. All
   page range evidence comes from the committed TOC map
   (`docs/data/2026_05_21_manual_toc_map.json`), which was derived from a prior
   extraction session. The TOC map provides section-level page anchors but does not
   confirm which sub-sections within a status chapter contain registration-specific
   document lists.

2. **Section vs. sub-section scope.** The TOC map anchor for a given status code
   (e.g. D-7 at pp.108-114) covers the entire status chapter in the stay manual.
   That chapter typically contains both 외국인등록 and 체류기간 연장 sub-sections,
   but the audit cannot confirm which pages cover registration without live extraction.
   This is why all `manualRefs` entries retain `needsManualReview: true`.

3. **Sub-codes not classified individually.** Nested `subCodes` arrays are not
   classified. Some sub-codes (e.g. D-2-1 through D-2-8, F-6-1/2/3) may have
   different registration document requirements than the parent record.

4. **No law API.** No live Korean law or HiKorea API was used. All evidence is
   manual-derived from committed source PDFs and extracted text.

5. **All existing records remain `verified=false` / `needsManualReview=true`.** This
   audit does not verify or promote any existing record. That remains the responsibility
   of a human reviewer with access to the canonical PDF.

---

## Recommended Patch Batches

The audit PR itself does **not** patch `visa_data.json`. The following batches are
recommended for subsequent PRs, in dependency order.

### Pre-condition (before any batch)
- Resolve the D-4-2K code collision (separate data-integrity PR).
- Confirm `pdftotext` is available in the execution environment so that registration
  sub-section pages can be verified against the canonical stay PDF.

### Batch 1 — High-confidence common statuses
**Scope:** D-9 (무역경영)

D-9 has `available: true` and raw extracted text in `summary`. Structure
`requiredDocs` from the raw text at 체류민원 pp.130-141 (confirmed p.136 reference).
This is the only Category B' record and is the highest-confidence candidate for
immediate structuring without a full manual re-extraction.

### Batch 2 — D-series study/training
**Scope:** D-1, D-3, D-4, D-4-2K (after code-collision resolution)

Study and training statuses. Registration is required after 90 days. Stay-manual
sections: pp.32-34, pp.56-82, pp.83-101. All have high-confidence TOC anchors.

### Batch 3 — E-series employment
**Scope:** E-1 through E-10 (plus D-7, D-8, D-10 as employment-adjacent)

Employment statuses where registration is required. E-2 has a low-confidence TOC
anchor; treat it as lower priority within this batch and add a `needs_manual_review`
caveat to the structured data.

### Batch 4 — F-series family/residence
**Scope:** F-1, F-2, F-3, F-4, F-5

Family and residence statuses. F-4 and F-5 reference the 동포 special sub-manual
section; extra care needed to distinguish F-series registration from H-2/F-4 overlap
in that sub-manual.

### Batch 5 — Miscellaneous and UI cleanup
**Scope:**
- G-1, H-1, H-2, D-5, D-6, K-STAR, REGION-S — structure registration docs from
  manual.
- B-1, B-2, C-1, C-4 — after pdftotext review, either confirm inapplicability (and
  set `available: false` with a note) or add conditional docs.
- UI: suppress the 외국인등록 tab for all `non_visa_helper_record` codes (D category).

---

## Validation Results (This Audit PR)

| Check | Result |
|-------|--------|
| `python3 -m json.tool visa_data.json` | PASS |
| `python3 -m json.tool backend/data/visas.json` | PASS |
| `python3 scripts/sync_visa_data.py --check` | PASS |
| `python3 scripts/audit_registration_procedure_coverage.py` | PASS |
| `python3 scripts/audit_foreign_registration_full_coverage.py` | PASS (0 sync mismatches, 0 OOB) |
| `bash scripts/check_repo.sh` | PASS |

---

## Whether This Audit PR Is Safe to Merge

**Yes.** This PR introduces:
- A new audit script (`scripts/audit_foreign_registration_full_coverage.py`) that is
  read-only with respect to `visa_data.json` and `backend/data/visas.json`.
- A new machine-readable JSON report (`docs/data/foreign_registration_full_coverage_2026_05.json`).
- This markdown report (`docs/data/FOREIGN_REGISTRATION_FULL_COVERAGE_AUDIT_2026_05.md`).

No visa/status data was patched. No source PDFs were changed. No UI changes were made.
All JSON files validate. Frontend/backend are in sync. All existing golden eval and
regression checks pass.
