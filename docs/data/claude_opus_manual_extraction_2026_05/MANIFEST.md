# MANIFEST — claude_opus_manual_extraction_2026_05

**Generated:** 2026-05-31  
**Extraction model:** Claude Sonnet 4.6 (Opus-class extraction pass)  
**Status:** Candidate evidence artifacts — NOT production data patches  
**READY_FOR_FIELD_PATCH:** 0 (intentional — see note below)

---

## Source Manuals

| File | Type | Pages |
|------|------|-------|
| `visa_manual_2026_05.pdf` | 사증발급 안내 매뉴얼 | 484 |
| `stay_manual_2026_05.pdf` | 외국인체류 안내 매뉴얼 | 777 |
| `visa_manual_2026_05_21.hwp` | 배포용 HWP 5.1.0.1 (cross-validation) | — |
| `stay_manual_2026_05_21.hwp` | 배포용 HWP 5.1.0.1 (cross-validation) | — |

---

## Key Facts

- **Parent status sections:** visa 39 + stay 41 = **80**
- **Field-evidence / document blocks:** **441**
- **Individual document item rows:** **2,519**
- **Sub-code coverage rows:** **442**
- **Cross-check sub-code rows:** **275** (unique sub-codes across both manuals)
- **High-risk review items:** **23**
- **HWP/PDF sub-code agreement:** 274 of 275 (99.6%)
- **F-5-27 discrepancy:** comparison-method artifact only — F-5-27 is present in the PDF at line 18,664. Not a real missing source.
- **Page-citation authority:** PDF (HWP files are reflowable, no page numbers)
- **HWP text value:** cleaner table-cell boundaries (‖-delimited) for document-list verification
- **Visa manual document marker:** 첨부서류
- **Stay/residence manual document marker:** 제출서류 — do not merge with visa evidence

---

## Why READY_FOR_FIELD_PATCH = 0

The source manuals use multi-column table layouts where a label/scenario column (left) identifies the applicable sub-code and a circled-item column (right) lists the required documents. PDF text-layer extraction concatenates these columns, making machine attribution of document blocks to specific sub-codes unverifiable without human page inspection. No row was promoted to READY_FOR_FIELD_PATCH. This is intentional, not an extraction failure. Per-row page verification by a human reviewer is required before any field patch.

---

## File Inventory

| # | Filename | Purpose | Rows (excl. header) | Size |
|---|----------|---------|---------------------|------|
| 1 | `PART1_PART8_SUMMARY.md` | Extraction summary + developer notes (Parts 1 & 8 of original spec) | — | 3.9 KB |
| 2 | `part2_coverage_checklist.csv` | Per-status/sub-code extraction status for all 80 parent sections + sub-code rows | 522 | 129 KB |
| 3 | `part3_field_evidence.csv` | 17-column field-level evidence; one row per 제출/첨부서류 block; includes PDF page, boundary, excerpt, confidence, patch_readiness | 441 | 602 KB |
| 4 | `part4_document_items.csv` | One row per individual ①②③ required-document item; most granular extraction output | 2,519 | 2.0 MB |
| 5 | `part5_subcode_coverage.csv` | Parent↔sub-code structure map; covers all 275 unique sub-codes across both manuals | 442 | 44 KB |
| 6 | `part6_high_risk_review.csv` | 23 high-risk statuses flagged for mandatory manual segmentation before any patch | 23 | 5.5 KB |
| 7 | `part7_patch_readiness_counts.json` | Patch-readiness label distribution: `{"NEEDS_PAGE_CITATION":187,"NEEDS_REVIEW":144,"SUBCODE_AMBIGUITY_REVIEW":110}` | — | 90 B |
| 8 | `HWP_VERIFICATION_REPORT.md` | Documents HWP decryption method, extraction approach, and cross-validation results | — | 2.2 KB |
| 9 | `crosscheck_subcodes.csv` | PDF vs HWP per-sub-code agreement matrix; 274/275 agree | 275 | 5.9 KB |
| 10 | `visa_hwp_full.txt` | Full visa manual HWP body text; table cells ‖-delimited; 13 ViewText sections | — | 988 KB |
| 11 | `stay_hwp_full.txt` | Full stay manual HWP body text; table cells ‖-delimited; XML-parsed | — | 1.5 MB |
| 12 | `MANIFEST.md` | This file | — | — |

---

## Important Usage Constraints

1. **Do not merge visa and stay evidence.** Different procedure types, different document conventions (첨부서류 vs 제출서류).
2. **Do not treat `sub_code` as empty** when `sub_code_type=unclear` — attribution is pending, not absent.
3. **Do not batch-promote** `patch_readiness` without per-row page verification.
4. **`notes` column in part3** includes `"subcode attribution unverified"` on every row — this is correct and must not be removed.
5. **HWP text files have no page numbers** — use PDF for all page citations.

---

## Recommended Review Sequence (Priority Order)

E-7 → F-5 → F-2 → F-1 → D-4 → F-6 → H-2 → G-1 → C-3 → D-10

See `part6_high_risk_review.csv` for per-status issue details and page ranges.
