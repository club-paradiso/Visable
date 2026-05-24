# Source Identity Report — 2026-05-21 Manual Update

Branch: `data/audit-2026-05-21-manual-update-json`
Report date: 2026-05-24

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

---

## Status: BLOCKED — Incoming PDFs Not Found

The expected incoming PDF files were not present at the specified paths:

| Expected path | Status |
|---|---|
| `tmp/incoming/사증발급 안내매뉴얼_260521.pdf` | **NOT FOUND** |
| `tmp/incoming/체류민원 안내매뉴얼_260521.pdf` | **NOT FOUND** |

A full filesystem search (up to depth 6) found no files matching `*260521*`, `*사증발급*`, or `*체류민원*` anywhere in the container. The `tmp/incoming/` directory does not exist.

**No repo PDFs were replaced. No immigration data was changed. No `verified` flags were advanced.**

---

## Repo PDF Baseline (unchanged)

These are the currently-committed repo PDFs that the prior audit run extracted from.

### 사증발급 안내매뉴얼 (Visa Issuance Manual)

| Field | Value |
|---|---|
| Repo path | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` |
| File size | 13,189,369 bytes (12.6 MB) |
| SHA-256 | `5a191aedd7d896b2f60a4065b7646a3ccda3e46abeacf9d34dc3802a19184063` |
| PDF internal CreationDate | `2026-05-07T00:54:33Z` |
| PDF title | `무제` |
| Pages | 484 |
| Cover label | `2026. 5.` (month-level only; no day) |
| Latest body date marker | `2026.2.12.` |

### 외국인체류 안내매뉴얼 (Stay Residence Manual)

| Field | Value |
|---|---|
| Repo path | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` |
| File size | 14,818,347 bytes (14.1 MB) |
| SHA-256 | `0492683698fdb2ba614b3c3aa791c462d03a68437e730093943e96ea15f7b3ba` |
| PDF internal CreationDate | `2026-05-07T00:53:43Z` |
| PDF title | `무제` |
| Pages | 774 |
| Cover label | `2026. 5.` (month-level only; no day) |
| Latest body date marker | `2026.2.12.` |
| Pilot project end date in body | `2026년 5월 19일` |

**Source date classification**: `unresolved`. The repo PDFs carry the generic "2026. 5." label and were created 2026-05-07 internally. They could be the 2026-05-04 or 2026-05-21 edition — this cannot be determined without the incoming files.

---

## Prior Extraction (still intact in tmp/)

The previous audit run successfully extracted both repo PDFs and the output files are still present in `tmp/manual-2026-05-21/` (`.gitignore`d, not committed):

| Path | Files |
|---|---|
| `tmp/manual-2026-05-21/visa_manual_2026_05_21.txt` | 20,908 lines (full-text, layout mode) |
| `tmp/manual-2026-05-21/stay_manual_2026_05_21.txt` | 33,245 lines (full-text, layout mode) |
| `tmp/manual-2026-05-21/visa_pages/v_p0001.txt … v_p0484.txt` | 484 page files |
| `tmp/manual-2026-05-21/stay_pages/s_p0001.txt … s_p0774.txt` | 774 page files |
| `tmp/manual-2026-05-21/section_anchors.json` | TOC anchor map |
| `tmp/manual-2026-05-21/visa_record_snapshot.json` | Structural snapshot |

These files are from the **currently-committed repo PDFs** (SHA-256 as above). If the repo PDFs are replaced by the actual 2026-05-21 files, all extraction output must be regenerated.

---

## Existing Audit Artifacts (committed in prior PR #147)

The following files were already committed to this branch and merged to `main` in PR #147:

| File | Status |
|---|---|
| `docs/source-manuals/source_manifest.json` | Updated — `source_date: "unresolved"`, PDF creation date, SHA-256, audit_history |
| `docs/data/2026_05_21_REPO_JSON_INVENTORY.md` + `.json` | Committed |
| `docs/data/2026_05_21_MANUAL_TOC_MAP.md` + `.json` | Committed |
| `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.md` + `.json` | Committed |
| `docs/data/2026_05_21_VISA_DATA_FULL_AUDIT.md` + `.json` | Committed |
| `docs/data/2026_05_21_FULL_MANUAL_JSON_AUDIT_REPORT.md` | Committed |

All these artifacts describe the **repo's current "2026.5" PDFs** and are classified `generic-2026.5-unverified`. They remain valid regardless of whether the incoming 2026-05-21 PDFs arrive.

---

## Validation Results (this run)

| Check | Result |
|---|---|
| `python3 -m json.tool source_manifest.json` | ✅ OK |
| `python3 -m json.tool visa_data.json` | ✅ OK |
| `python3 -m json.tool backend/data/visas.json` | ✅ OK |
| `python3 -m json.tool doc_master.json` | ✅ OK |
| `scripts/sync_visa_data.py --check` | ✅ OK (backend mirrors root) |
| `scripts/check_source_manuals.py` | ✅ OK |
| `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| `scripts/check_required_documents_coverage.py` | ✅ PASS (no regressions) |

---

## What Must Happen Before Full Audit Can Continue

1. **Place the incoming PDFs** at:
   - `tmp/incoming/사증발급 안내매뉴얼_260521.pdf`
   - `tmp/incoming/체류민원 안내매뉴얼_260521.pdf`
   
   (or at any accessible path — update the audit command accordingly)

2. **Compare SHA-256** of incoming files against the repo baseline above.

3. **If SHA-256 differs** (incoming ≠ repo):
   - Copy incoming → `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` and `…/stay_manual_2026_05.pdf`
   - Update `source_manifest.json`: `source_date: "2026-05-21"`, `verification_status: "source_file_compared"`, new SHA-256, new page counts
   - Re-run `pdftotext -layout` to regenerate `tmp/manual-2026-05-21/` extraction
   - Regenerate `2026_05_21_MANUAL_TOC_MAP.*` with new page anchors
   - Flag all `visa_data.json` records' procedure `manualRefs` as potentially stale (page numbers may shift)

4. **If SHA-256 matches** (incoming = repo):
   - Update `source_manifest.json`: `source_date: "2026-05-21"`, `verification_status: "source_file_compared"` (identity confirmed)
   - Prior extraction output and TOC map remain valid
   - All prior audit artifacts remain valid

5. **Then proceed** to the full manual-to-JSON crosswalk (Opus recommended for that stage).

---

## What Is Safe for Opus to Continue Now

Despite the source-identity blocker, the following are **safe to proceed with** against the current repo PDFs (they are unblocked because they don't depend on confirming the 2026-05-21 identity):

- Extracting content from specific manual sections to patch **confirmed** gaps (e.g., D-2 extension docs from stay pp.43–44, where active grounding already exists)
- Adding grounding entries to `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` for sections with high-confidence page anchors
- Cleaning up `doc_master.json` corrupted entries (12 Korean-text IDs)
- Resolving the D-4-2K duplicate code

These should **not** be done until source identity is resolved for records with high-risk content (F-6 income, F-4/H-2, K-STAR, REGION-S), since those section's page numbers may shift if the PDFs are replaced.

---

## Legal Disclaimer

Nothing in this report constitutes legal advice or an official immigration decision. All records remain `needsManualReview=true`. Users must verify with 출입국·외국인청, HiKorea, or 1345.
