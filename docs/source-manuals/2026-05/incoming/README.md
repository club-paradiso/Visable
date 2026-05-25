# 2026-05-21 Manual Source Files

This directory is a staging location for the four user-provided Korean immigration manual source files.

Install status:
- The staged PDFs were compared against the prior canonical repo PDFs in the `data/install-2026-05-21-source-pdfs` follow-up.
- The verified PDFs were installed into `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` and `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`.
- `docs/source-manuals/source_manifest.json` was updated.
- `visa_data.json`, `backend/data/visas.json`, and `doc_master.json` were not patched in this source-install PR.

Expected files:
- `visa_manual_2026_05_21_source.pdf`
- `stay_manual_2026_05_21_source.pdf`
- `visa_manual_2026_05_21_source.hwp`
- `stay_manual_2026_05_21_source.hwp`

Notes:
- The HWP files may be Hancom distribution-mode files. If extraction fails, document the blocker and use PDF extraction as the primary source.
- The stay PDF should be treated as important because it has 777 pages in the uploaded source.
