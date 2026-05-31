# Claude Opus Manual Extraction — Ingestion Report (2026-05)

## Purpose

This report documents the ingestion of Claude Opus manual-extraction and HWP
cross-validation artifacts into the repository for the 2026-05 edition of the
official Korean immigration manuals. The artifacts provide structured, page-cited
field evidence extracted from:

- `visa_manual_2026_05.pdf` — 사증발급 안내 매뉴얼 (484 pages)
- `stay_manual_2026_05.pdf` — 외국인체류 안내 매뉴얼 (777 pages)
- `visa_manual_2026_05_21.hwp` — 배포용 HWP 5.1.0.1 (cross-validation)
- `stay_manual_2026_05_21.hwp` — 배포용 HWP 5.1.0.1 (cross-validation)

The artifacts are **candidate evidence only**. They are stored under
`docs/data/claude_opus_manual_extraction_2026_05/` for future human-reviewed
targeted patches. **No production data was modified by this commit.**

---

## File Inventory

All files reside under `docs/data/claude_opus_manual_extraction_2026_05/`.

| # | Filename | Purpose | Data rows |
|---|----------|---------|-----------|
| 1 | `MANIFEST.md` | Master manifest: key facts, usage constraints, review sequence | — |
| 2 | `PART1_PART8_SUMMARY.md` | Extraction summary + developer notes (Parts 1 & 8) | — |
| 3 | `part2_coverage_checklist.csv` | Per-status/sub-code extraction status for all 80 parent sections | 522 |
| 4 | `part3_field_evidence.csv` | One row per 제출/첨부서류 block; 17 columns incl. PDF page, boundary, excerpt, patch_readiness | 441 |
| 5 | `part4_document_items.csv` | One row per individual ①②③ required-document item; most granular output | 2,519 |
| 6 | `part5_subcode_coverage.csv` | Parent↔sub-code structure map across both manuals | 442 |
| 7 | `part6_high_risk_review.csv` | 23 statuses flagged for mandatory manual segmentation before any patch | 23 |
| 8 | `part7_patch_readiness_counts.json` | Patch-readiness label distribution (JSON) | — |
| 9 | `HWP_VERIFICATION_REPORT.md` | HWP decryption method, extraction approach, cross-validation results | — |
| 10 | `crosscheck_subcodes.csv` | PDF vs HWP per-sub-code agreement matrix | 275 |
| 11 | `visa_hwp_full.txt` | Full visa manual HWP body text (‖-delimited table cells, 13 ViewText sections) | — |
| 12 | `stay_hwp_full.txt` | Full stay manual HWP body text (‖-delimited, XML-parsed) | — |

---

## Extraction Summary

| Metric | Visa manual | Stay manual | Total |
|--------|-------------|-------------|-------|
| Parent status sections | 39 | 41 | **80** |
| 제출/첨부서류 blocks | 156 | 285 | **441** |
| Individual document item rows | — | — | **2,519** |
| Sub-code coverage rows | — | — | **442** |
| Source pages covered | 484 | 777 | — |

Document-marker convention:

- Visa manual (`visa_manual_2026_05.pdf`) uses **첨부서류**
- Stay/residence manual (`stay_manual_2026_05.pdf`) uses **제출서류**

**These two manuals cover distinct procedure types** (visa issuance vs. registration /
extension / change). Their procedure evidence must not be merged.

### Extraction limitations (recorded verbatim from PART1_PART8_SUMMARY.md)

1. Document blocks are located precisely by page, but **machine attribution to a
   specific sub-code is not definitively possible**: the source text splits into
   left-label / numbered-item columns that are concatenated in PDF text extraction.
2. Circled-item lists (①②③) extract correctly; multi-column conditional labels may
   interleave with item text in complex layouts.
3. **E-7** spans visa pp. 168–277 and stay pp. 212–323 (100+ pages, dozens of
   occupation codes) — automated sub-code separation is partial; manual segmentation
   recommended.
4. Some sections (e.g. E-2 stay) lack a standalone centered heading; start page is
   approximate; those rows carry `NEEDS_PAGE_CITATION`.
5. No external knowledge or web search was used; unprovable fields are left blank or
   flagged for review.

---

## HWP Cross-Validation Summary

The 배포용 (distribution) HWP files have their body text in an encrypted
`ViewText` stream (not the standard `BodyText` stream). Extraction required:

- **Stay**: `hwp5proc xml` → lxml reconstruction, preserving table-cell boundaries
  (‖-delimited), 754 KB output.
- **Visa**: pyhwp low-level `viewtext` accessor, 13 ViewText sections direct-decoded,
  458 KB output, avoiding a fatal `undefined Kind value: 2` crash.

**HWP has no page numbers** (reflowable format). PDF remains the sole page-citation
authority.

### Cross-validation results

| Check | Visa | Stay |
|-------|------|------|
| 첨부서류 markers (HWP / PDF) | 220 / 221 | 51 / 50 |
| 제출서류 markers (HWP / PDF) | 75 / 76 | 362 / 361 |
| Unique sub-codes (HWP / PDF) | 124 / 124 | 151 / 150 |
| **Sub-code cross-check agreement** | **274 / 275 (99.6%)** | |

The single mismatch (`F-5-27`, stay) is a **comparison-method artifact**: `F-5-27`
is present in the PDF at line 18,664 as a ※ exclusion note
(`"※ F-5-2/3, F-5-6, F-5-7, F-5-14, F-5-27은 별도 지침"`). The regex-set
comparison method counted it only in one pass. There is no real missing source.

Document-item text spot-checks (F-6, A-3 별지 제34호 region) confirm item-level
agreement between HWP and PDF (출생증명서 사본, 대사관 협조공한, etc.); only
multi-column adjacency ordering differs.

**Conclusion: existing PDF-based extraction is content-equivalent to the HWP
originals. HWP text is a cleaner supplementary source for table-cell boundary
verification and document-list segmentation (especially E-7 large sections).**

---

## Patch Readiness Summary

```
NEEDS_PAGE_CITATION:     187
NEEDS_REVIEW:            144
SUBCODE_AMBIGUITY_REVIEW: 110
READY_FOR_FIELD_PATCH:     0  (intentional)
```

### Why READY_FOR_FIELD_PATCH = 0

The manual source tables use multi-column layouts in which a left-column label
identifies the applicable sub-code (or scenario) and a right column lists required
documents with circled items. PDF text-layer extraction concatenates these columns,
making machine attribution of a document block to a specific sub-code unverifiable
without human page inspection.

No row was promoted to `READY_FOR_FIELD_PATCH`. This is **intentional and
conservative**, not an extraction failure. Per-row page verification by a human
reviewer is required before any field patch.

This is consistent with the 0-correction outcome of the prior all-status manual pass
(PR #224, `data/all-status-manual-sourced-corrections-2026-05`), where the same HWP
encryption and PDF image-only constraints prevented extraction; in contrast, these
artifacts represent a successful full PDF extraction pass, but the sub-code
attribution barrier still prevents automatic patching.

---

## Why Production JSON Was Not Modified

- `visa_data.json`, `backend/data/visas.json`, `doc_master.json`: **unchanged**.
- No extracted row reached `READY_FOR_FIELD_PATCH`. The extraction artifacts are
  candidate evidence awaiting human page-level review.
- The one verified production correction from the 2026-05 cycle (D-4 extension
  `pp. 90-91` pageRange) was already applied in PR #222 from committed grounding.
- Extracting more text does not lower the evidence bar: a field patch requires
  exact page-cited evidence plus confident sub-code attribution, neither of which
  is machine-verifiable from this extraction alone.

---

## Validation Results

```
python3 -m json.tool docs/data/claude_opus_manual_extraction_2026_05/part7_patch_readiness_counts.json  # PASS
python3 -m json.tool visa_data.json                                                                      # PASS
python3 -m json.tool backend/data/visas.json                                                             # PASS
python3 -m json.tool doc_master.json                                                                     # PASS
python3 scripts/sync_visa_data.py --check                                                                # OK (byte-identical parity)
python3 scripts/check_required_documents_coverage.py                                                     # PASS (58 statuses, rc=0)
bash scripts/check_repo.sh                                                                               # rc=0
```

---

## How Future Developers Should Use These Files

1. **Start with `MANIFEST.md`** — key facts, usage constraints, and recommended
   review sequence.
2. **`part3_field_evidence.csv`** is the primary lookup: filter by `status_code`,
   `procedure`, and `sub_code` to find candidate document blocks for a given visa
   status. Check `patch_readiness` and `page_ref` columns.
3. **`part4_document_items.csv`** provides the individual required-document strings
   with their parent block FK. Use to verify specific document names against
   production `requiredDocs` arrays.
4. **`crosscheck_subcodes.csv`** and **`HWP_VERIFICATION_REPORT.md`** establish
   confidence that PDF extraction is content-equivalent to HWP. Use
   `visa_hwp_full.txt` / `stay_hwp_full.txt` for table-cell boundary verification
   (‖-delimited) when resolving multi-column ambiguities.
5. **Do not merge rows** from visa and stay extractions — different procedure types
   and document conventions (첨부서류 vs 제출서류).
6. **Do not batch-promote** `patch_readiness` without per-row PDF page verification.
   The `notes` column of `part3_field_evidence.csv` contains
   `"subcode attribution unverified"` on every row — this is correct and must not
   be removed.
7. **HWP text has no page numbers** — always use PDF for page citations.

---

## Recommended Next Targeted Manual-Review Sequence

Priority order from `part6_high_risk_review.csv`:

```
E-7 → F-5 → F-2 → F-1 → D-4 → F-6 → H-2 → G-1 → C-3 → D-10
```

These statuses have the most sub-codes, largest page ranges, or most complex
multi-column table layouts. Automated sub-code attribution is most incomplete here.
Focused human review of one status at a time against the PDF source pages will
unlock the highest-confidence targeted patches.

---

## Non-Goals

- No production JSON patch (`visa_data.json` / `backend/data/visas.json` /
  `doc_master.json` unchanged).
- No metadata promotion (`verified=true` not set; `needsManualReview` retained
  where present).
- No law grounding activation.
- No UI redesign.
- No unsourced required-document corrections.
- No overgeneralization of sub-code-specific requirements onto parent status records.
- No merging of visa issuance and stay/residence procedure evidence.
