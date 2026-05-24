# 2026-05-21 Manual Source Files

This directory is a staging location for the four user-provided Korean immigration manual source files.

Recommended next step:
- Compare these incoming files against the current repo PDFs.
- Install the verified PDFs into `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` and `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` only after hash/page comparison.
- Update `docs/source-manuals/source_manifest.json`.
- Do not patch `visa_data.json`, `backend/data/visas.json`, or `doc_master.json` in PR A.

Expected files:
- `visa_manual_2026_05_21_source.pdf`
- `stay_manual_2026_05_21_source.pdf`
- `visa_manual_2026_05_21_source.hwp`
- `stay_manual_2026_05_21_source.hwp`

Notes:
- The HWP files may be Hancom distribution-mode files. If extraction fails, document the blocker and use PDF extraction as the primary source.
- The stay PDF should be treated as important because it has 777 pages in the uploaded source.
