# 2026-05-21 Anchor & Reference Stability Patch (PR D batch 3)

Branch: `data/patch-2026-05-21-anchor-and-ref-stability`
Audit date: 2026-05-25
PR: **D batch 3** (after PR #162)

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

This is **PR D batch 3**. **PR #162** completed the doc_master ID migration with UI compatibility. This PR runs a **post-D2 regression audit** and corrects **exact, PDF-proven page/reference anchor drift** only — no substantive immigration/legal content.

---

## Post-D2 regression audit (PR #162) — no regression found

| Check | Result |
|---|---|
| doc_master reference resolution (`check_doc_master_id_migration.py`) | ✅ OK (79 ids; all ID-array refs resolve; no Korean-string ids remain) |
| Old corrupted Korean-string IDs as active refs | ✅ 0 in `visa_data.json` and `backend/data/visas.json` |
| Backend sync (`sync_visa_data.py --check`) | ✅ OK before edits |
| DOC_DICT label coverage for `doc_` refs in id-arrays | ⚠️ 2 missing: `doc_local_recommendation`, `doc_top_tier_degree` — **pre-existing**, not a PR #162 regression |

**PR #162 left no regression**: no broken doc_master references, no DOC_DICT gaps for the migrated ids, no backend sync drift, and no stale active old-ID references. No regression fix was required. The 2 label-less `doc_` ids predate PR #162 (render via the `문서요건(...)` fallback); per the UI rule (`index.html` may change only for a real PR #162 regression) they are **not** touched here and are routed to PR D-4.

---

## Page/reference anchor corrections (PDF-proven)

All corrections are in the stay manual (`체류민원`, 777-page canonical PDF). Only the page-range token changed in each string; surrounding audit-note text is byte-identical. Every affected record's `requiredDocs` is the `["매뉴얼 확인 필요"]` placeholder, so no document requirement exists to change.

| Code | Old → New | Fields changed | PDF evidence |
|---|---|---|---|
| F-2 거주 | `pp. 358-424` → `pp. 360-420` | sectionPageRange, registration.manualRef.pageRange, registration.summary | p360 `거 주(F-2)`; p421 `동반(F-3)` |
| F-3 동반 | `pp. 425-428` → `pp. 421-425` | sectionPageRange, extension+registration manualRef.pageRange, extReq, extension+registration summary | p421 `동반(F-3)`; p426 `영 주(F-5)` |
| F-5 영주 | `pp. 429-477` → `pp. 426-473` | sectionPageRange, registration.manualRef.pageRange, registration.summary | p426 `영 주(F-5)`; p474 `결혼이민(F-6)` |
| H-1 관광취업 | `pp. 518-525` → `pp. 514-517` | sectionPageRange, registration.manualRef.pageRange, registration.summary | p514 `관광취업(H-1)`; p518 §36 sub-manual |
| H-1 관광취업 (ext) | `p. 521` → `p. 517` | extension.manualRef.pageRange | old p.521 fell in §36 (518-584); the H-1 `체류기간 연장허가` extension heading is on p517 |

**TOC evidence:** `docs/data/2026_05_21_manual_toc_map.json` stay sections — §30 F-2 360-420, §31 F-3 421-425, §32 F-5 426-473, §35 H-1 514-517.

### Anchors intentionally left unchanged

| Code | Field | Value | Reason |
|---|---|---|---|
| F-2 | extension.manualRef.pageRange | `p. 394` | Within re-derived section 360-420 (section start unchanged at 360); single-page citation not proven wrong. |
| F-5 | extension.manualRef.pageRange | `p. 429` | Within re-derived section 426-473; single-page citation not proven wrong. |

---

## Page-bounds audit (required search)

Method: parsed every `체류민원` `sectionPageRange` + `procedures.*.manualRefs[].pageRange` for standard-code records and compared against the PR #157 TOC map stay section bounds.

- **In-bounds after patch: 100**
- **Out-of-bounds after patch: 2 — both F-6** (explicitly excluded from this PR):
  - F-6 `manualRequiredDocAudit.sectionPageRange` = `pp. 478-501` (section 474-497) → PR D-4
  - F-6 `procedures.extension.manualRefs[0].pageRange` = `pp. 494-499` (section 474-497) → PR D-4

F-6 is the income-note record reserved for PR D-4; its anchors are left untouched here.

### Required-search results

| Search | Result |
|---|---|
| Old corrupted Korean-string doc IDs in active refs | 0 (visa_data + backend) |
| manualRef/pageRange outside PR #157 section bounds | 2 (both F-6, deferred); all F-2/F-3/F-5/H-1 now in-bounds |
| requiredDocuments IDs missing from doc_master.json | 0 |
| requiredDocuments IDs missing DOC_DICT label | 2 pre-existing (`doc_local_recommendation`, `doc_top_tier_degree`), deferred |

---

## Changed files

| File | Change |
|---|---|
| `visa_data.json` | 16 page-citation strings corrected across F-2/F-3/F-5/H-1 (page numbers only) |
| `backend/data/visas.json` | regenerated via `scripts/sync_visa_data.py` only |
| `docs/data/2026_05_21_ANCHOR_REF_STABILITY_PATCH_REPORT.md` | this report |
| `docs/data/2026_05_21_anchor_ref_stability_patch_report.json` | machine-readable report |

`index.html`, `doc_master.json`, and `source_manifest.json` were **not** changed.

---

## Confirmations

- ✅ Korean user-facing labels preserved.
- ✅ No required-document meaning changed.
- ✅ No requiredDocuments added or removed.
- ✅ No eligibility, fees, income thresholds, stay periods, procedures, or legal/admin guidance text rewritten (only page-range tokens changed).
- ✅ No `verified=true` promotions.
- ✅ No `needsManualReview` removals.
- ✅ No records deleted; no UI change (`index.html` untouched).
- ✅ `backend/data/visas.json` updated only through `scripts/sync_visa_data.py`.

---

## Validation results

| Check | Result |
|---|---|
| `python3 -m json.tool` (visa_data, backend visas, doc_master, this report, 3 PR #157 JSON artifacts) | ✅ valid |
| `scripts/check_doc_master_id_migration.py` | ✅ OK |
| `scripts/check_source_manuals.py` | ✅ OK |
| `scripts/check_source_updates.py --local-only` | ✅ OK |
| `scripts/sync_visa_data.py --check` | ✅ OK |
| `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| `scripts/check_required_documents_coverage.py` | ✅ no regressions |
| `scripts/validate_coverage_matrix.py` | ✅ OK |
| `scripts/validate_manual_grounding_candidate.py` | ✅ OK |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ pass (194 backend tests; git diff clean) |

---

## PR D-4 queue (substantive content, page-cited)

1. **F-6** income note/content **and F-6 page anchors** (`sectionPageRange` `478-501`→`474-497`; extension `494-499`) — stay §33 pp.474–497, visa §34 pp.324–335.
2. **D-4-2K** duplicate/sub-code resolution (array indices 24 + 55).
3. **F-4 / H-2** 외국국적동포 Feb-2026 sub-manual content (stay §36 pp.518–584).
4. **K-STAR** substantive content (visa §40 pp.456–484 / stay §41 pp.749–777).
5. **REGION-S / 지역특화형** (stay §37 pp.585–654) / **광역형** (stay §40 pp.686–748).
6. **DOC_DICT labels** for pre-existing label-less ids (`doc_local_recommendation`, `doc_top_tier_degree`).
7. Optional near-duplicate doc_master dedupe (migrated `*_generic` ids vs `doc_passport`/`doc_address`/`doc_app_form`).
8. Optional: add a read-only page-bounds validator once F-6 anchors are corrected (so it can hard-fail without a deferred-record carve-out).

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
