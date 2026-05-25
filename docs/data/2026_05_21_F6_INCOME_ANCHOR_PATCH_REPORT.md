# 2026-05-21 F-6 Income & Anchor Patch (PR D batch 4)

Branch: `data/patch-2026-05-21-f6-income-and-anchors`
Audit date: 2026-05-25
PR: **D batch 4** (after PR #165) — **F-6 (결혼이민) ONLY**

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

This is **PR D batch 4**. **PR #165** left exactly two out-of-bounds F-6 anchors (`478-501`, `494-499`) deferred to PR D-4. This PR fixes the F-6 page/reference anchors and, with exact page-cited evidence, the stale F-6 income **source-date label**. F-6 is high-sensitivity; nothing was inferred.

---

## F-6 section bounds confirmed

- **Stay manual §33 결혼이민(F-6) = pp.474-497** — PDF: p474 header `결혼이민(F-6)`, p498 header `기 타(G-1)`.
- TOC artifact: `docs/data/2026_05_21_manual_toc_map.json` stay §33 = 474-497.

---

## Page/reference anchor changes (PDF-proven)

| Field | Old → New | Evidence |
|---|---|---|
| `manualRequiredDocAudit.sectionPageRange` | `pp. 478-501` → `pp. 474-497` | PR #157 TOC + p474 `결혼이민(F-6)` / p498 `기 타(G-1)`; old range started 4pp into the section and overran into G-1 |
| `procedures.extension.manualRefs[0].pageRange` | `pp. 494-499` → `pp. 494-497` | F-6 ends p497; p498-499 = G-1. p494-497 are F-6 외국인등록/체류기간 연장 pages. Upper bound clamped to the section end; start unchanged |

**Left unchanged:** `procedures.registration.manualRefs[0].pageRange` = `p. 494` (within 474-497; confirmed F-6 외국인등록/체류기간 연장 page; not proven wrong). The six placeholder `매뉴얼 확인 필요` manualRefs (visaIssuance/statusChange/statusGrant/activitiesOutsideStatus/workplaceChange/reentry) assert no page and were left.

---

## Income source-date label change (figures kept verbatim)

PR #157 classified F-6 as `stale` due to a `2026.3` income/source note. Direct extraction proves the **income figures are current** — identical to the canonical 2026-05-21 manual — so this is a **source-date-label fix only**, not an income-value change.

**Changed in 3 identical fields** (`subCodes[0].note`, `subcodes[0].note`, `subcodes[0].summary`):

- **Old prefix:** `(체류민원 안내매뉴얼 2026.3 발췌 — 2026.5 매뉴얼 대비 갱신 여부 수동 검토 필요)`
- **New prefix:** `(소득요건 수치는 체류민원 안내매뉴얼 2026.5(2026-05-21) p.478 '2026년 기준 소득요건' 표와 일치 확인)`
- **Income figures (unchanged, verbatim):** `소득요건: 2026년 기준 2인 25,195,752원, 3인 32,154,216원, 4인 38,968,428원, 5인 45,340,314원, 6인 51,335,712원, 7인 57,090,900원, 8인 이상은 1인 증가당 5,755,188원 추가.`

### Evidence (stay manual p.478)

```
* (참고) 2026년 기준 소득요건 : 초청인의 과거 1년간 연간소득(세전)이 아래 표에 해당되는 금액 이상이어야 함
   구 분        2인 가구    3인 가구    4인 가구    5인 가구    6인 가구    7인 가구
   소득기준   25,195,752  32,154,216  38,968,428  45,340,314  51,335,712  57,090,900
* 8인 가구 이상의 소득기준 : 가구원 추가 1인당 5,755,188원씩 증가
```

- **Why the old value was stale:** it attributed the figures to a `2026.3 발췌` (2026.3 manual excerpt) and flagged `2026.5 매뉴얼 대비 갱신 여부 수동 검토 필요` (needs review of whether updated vs the 2026.5 manual).
- **Why the new value is source-grounded:** the figures are byte-for-byte identical to the `2026년 기준 소득요건` table on **p.478** of the canonical 2026-05-21 stay manual. The numeric requirement is current and unchanged; only the source-date label was stale.
- **Caution preserved:** the conditional `8인 이상은 1인 증가당 5,755,188원 추가` is verbatim. The manual's 2024 (p482, 법무부고시 제2023-648호) and 2025 (p486) reference tables were **not** substituted; the note keeps the latest `2026년 기준` table as before. No simplification or paraphrase.

---

## Required searches

| Search | Result |
|---|---|
| Stale F-6 ranges `478-501` / `494-499` | 0 remaining (visa_data + backend) |
| Stale F-6 income/source strings (`2026.3 발췌`, `갱신 여부 수동 검토 필요`) | 0 remaining |
| Non-F-6 records changed | 0 (record-level diff: only F-6; 58/58 records) |
| Stay page ranges outside PR #157 section bounds after patch | **0** |

---

## Changed files

| File | Change |
|---|---|
| `visa_data.json` | F-6 only: 2 page anchors + 3 income-note source-label prefixes (income figures verbatim) |
| `backend/data/visas.json` | regenerated via `scripts/sync_visa_data.py` only |
| `docs/data/2026_05_21_F6_INCOME_ANCHOR_PATCH_REPORT.md` | this report |
| `docs/data/2026_05_21_f6_income_anchor_patch_report.json` | machine-readable report |

`index.html`, `doc_master.json`, `source_manifest.json` **unchanged**.

---

## Confirmations

- ✅ Only the F-6 record was changed.
- ✅ No required-document meaning changed; no requiredDocuments added or removed.
- ✅ No fees, stay periods, unrelated procedures, or unrelated eligibility changed.
- ✅ **Income values unchanged**; only the income **source-date label** was corrected (page-cited to p.478).
- ✅ No `verified=true` promotions (F-6 `verified=false`).
- ✅ No `needsManualReview` removals (F-6 `needsManualReview=true`).
- ✅ No records deleted; no UI change.
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
| post-patch stay page-bounds audit | ✅ 0 out-of-bounds |

---

## PR D-5 queue

1. **D-4-2K** duplicate/sub-code resolution (array indices 24 + 55).
2. **F-4 / H-2** 외국국적동포 Feb-2026 sub-manual content (stay §36 pp.518-584).
3. **K-STAR** substantive content (visa §40 pp.456-484 / stay §41 pp.749-777).
4. **REGION-S / 지역특화형** (stay §37 pp.585-654) / **광역형** (stay §40 pp.686-748).
5. **DOC_DICT labels** for `doc_local_recommendation` and `doc_top_tier_degree`.
6. Optional near-duplicate doc_master dedupe.
7. Optional read-only page-bounds validator (now feasible — 0 out-of-bounds stay anchors after this PR).

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
