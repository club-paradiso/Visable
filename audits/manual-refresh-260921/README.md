# September 2026 PDF search update

The supplied visa PDF (2026-09-01, 519 pages) and stay PDF (2026-09-18,
810 pages) are now indexed in full, with separate domains and links to the
original PDF page. The original files are SHA-256 pinned in
`data/manual-corpus/sources.json`.

These reports compare the September PDFs with the June PDF editions cited by
existing structured guides. They do **not** compare with or supersede the July
HWP human approval record. The existing July-to-September-1 HWP comparison is in
`audits/manual-refresh-260901/`. No new human approval has been recorded.

- `visa_pdf_comparison.md` / `.json`: June 17 PDF to September 1 PDF.
- `stay_pdf_comparison.md` / `.json`: June 23 PDF to September 18 PDF.
- Each side uses the same PyMuPDF 1.28.2 text extraction. Exact duplicate word
  paint operations at the same PDF coordinates are removed; repeated prose at
  different positions is retained. Source wording is not rewritten.
- The reports list candidate changed pages and affected codes. Pagination,
  layout and table changes can still appear as differences; these counts are
  not counts of changed legal requirements.
- Tables and images must be read in the source PDF. The plain-text excerpts do
  not preserve cell relationships and are labeled as unreviewed in the UI.
- The source registry uses `needs_manual_review`; the existing `active` approved
  editions and the approval index are preserved. The new searchable SQLite
  chunks all have `direct_evidence=0`.
- Existing structured visa/document guides are not relabeled as September
  guidance. Their dates remain visible, alongside the new original-text tab.

Reproduce with Python and `pip install -r scripts/requirements-manuals.txt`,
then `npm run build:current-manuals`. Verify with `npm run test:current-manuals`
and `npm run validate` (backend test dependencies required).
