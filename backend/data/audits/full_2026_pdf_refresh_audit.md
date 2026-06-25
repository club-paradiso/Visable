# Full 2026 PDF Manual Refresh Audit

## Scope
- Task: refresh Paradiso source grounding from readable 2026 HiKorea PDF manuals.
- Branch: `data/refresh-all-statuses-from-2026-pdf-manuals`
- Official notice: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Source domains kept separate:
  - `260617` 사증민원 manual: 입국 전 사증발급.
  - `260623` 체류민원 manual: 입국 후 체류민원.

## Sources Installed
- `backend/data/sources/manuals/260617_visa_manual_exported.pdf`
- `backend/data/sources/manuals/260617_visa_manual_readable.txt`
- `backend/data/sources/manuals/260617_visa_manual_sections.json`
- `backend/data/sources/manuals/260623_stay_manual_exported.pdf`
- `backend/data/sources/manuals/260623_stay_manual_readable.txt`
- `backend/data/sources/manuals/260623_stay_manual_sections.json`

## Extraction
- Extraction script: `scripts/visa/extract_2026_pdf_manuals.py`
- Method used: `pypdf` page-level extraction.
- Visa result: 487 pages, 432,692 section characters, 148 distinct detected code tokens.
- Stay result: 780 pages, 673,997 section characters, 182 distinct detected code tokens.
- Page traceability: preserved in `*_sections.json` with `source_id`, `source_file`, `page`, `heading`, text, status codes, and subcodes.

## Status Inventory
- Inventory artifacts:
  - `backend/data/audits/manual_status_inventory_2026.json`
  - `backend/data/audits/manual_status_inventory_2026.md`
  - `backend/data/audits/status_matrix_2026_pdf_refresh.json`
- Status matrix rows: 43
- Canonical Paradiso statuses audited: 42
- Scenario/helper row: `C-2`
- Manual-present codes: 41
- Manual subcodes discovered: 215
- Source occurrences: stay manual 2,023; visa manual 855

## Data Changes
- Active source registry entries now point to:
  - `visa_manual_2026_06_17_pdf`
  - `stay_manual_2026_06_23_pdf`
- Superseded source entries are marked deprecated rather than deleted.
- `docs/source-manuals/source_manifest.json` now records current 2026.6 readable PDF sources, hashes, page counts, extracted text paths, and archived previous-current metadata.
- All 42 canonical authoring status files received refreshed PDF source metadata under `sourceManualStatus.manualRefresh2026Pdf`.
- Generated data regenerated/synced:
  - `visa_data.json`
  - `backend/data/visas.json`
- No invalid pseudo-code such as `D-2-R` was introduced.
- No duplicate `D-2` top-level record was introduced.

## Substantive Guidance Policy
- This PR promotes readable source availability, source metadata, page-level inventories, and source references.
- It does not claim that every eligibility, document, fee, period, applicant-condition, or scenario field was newly line-by-line certified from the 2026 PDFs.
- Existing structured legal guidance remains `needsManualReview: true` where field-level certification is incomplete.
- `manualRefs` and source panels now point to readable 2026.6 PDF-derived text rather than stale 2026.5 source labels.
- The older structured requirements layer remains separately gated and is not mechanically relabeled as 260623-certified.

## UI And Waymaker
- UI source labels were updated from generic 2026.5 copy to readable 2026.6 PDF source labels where the current source panel/fallback copy is shown.
- i18n review labels were updated in `data/i18n/en.json`, `data/i18n/ko.json`, and `data/i18n/zh-CN.json`.
- Waymaker stay grounding fixture now points to the 260623 stay PDF and source date `2026-06-23`.
- E-7 stay-extension grounding moved from page 226 to page 227 based on the 260623 stay PDF extraction.
- D-2 and D-4 stay-extension page ranges were rechecked and preserved.

## Preserved Or Blocked Items
- Change-log readable PDF was not available; no change-log extraction was used.
- Official mission/embassy supplementation was not attempted in this pass to avoid delaying the core national-manual refresh.
- Broad field-level structured requirement regeneration from the new PDFs is a follow-up task.
- Mission-specific guidance remains separate from national manual guidance.

## Recommended Follow-Up
- Perform line-by-line certification for high-risk fields in the extracted PDF sections, starting with F-5, F-6, G-1, E-7, F-2, F-4, C-3, B-1, and B-2.
- Add a readable change-log PDF if available and rerun the inventory.
- Add official mission-specific overlays only in separate source-labeled PRs.

