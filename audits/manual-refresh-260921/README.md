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

## 2026-09-18 stay manual — 배포용 HWP original (added 2026-09-22)

The ministry's own HWP of the September 18 stay edition is now committed and
pinned alongside the PDF, so the September stay text no longer depends solely on
a PDF text layer.

- `docs/source-manuals/2026-09/stay_manual_260918.hwp`, SHA-256
  `06abba5f7ca1b3029225114097b234391306f71e0fbeabbfea73a5b8824e5917`.
- Body text read from the 배포용 ViewText stream with
  `scripts/decrypt_hwp_distribution.py` into
  `docs/source-manuals/2026-09/extracted/full_text/stay_manual_260918.txt`:
  726,907 characters, 22,131 non-empty lines, all 38 parent status codes, zero
  U+FFFD. The same script reproduces the approved 2026-07-31 stay extraction
  byte-for-byte, which is what establishes that the METHOD is sound.
- Edition identity is established by comparison, not by the cover (which reads
  only `2026. 9.`): every line this file adds or changes against the 2026-09-01
  HWP appears verbatim in the pinned 2026-09-18 PDF extraction, and the two
  superseded 2026-09-01 lines do not.
- `stay_hwp_260901_to_260918.md` / `.json`: the HWP-to-HWP comparison, produced
  by `scripts/diff_manual_paragraph_editions.py`. Both sides come from the same
  extractor, so this is the apples-to-apples September comparison. It reports
  3 hunks — 0.02% of lines — touching D-8-4/F-5-1 (영주 신청 시 ‘매년’ 체류기간
  산정방법 예시 신설) and the F-5 ‘3년 이상 근무’ 해석 문구.
- Registered `needs_manual_review` / `needs_review` / `pending_review` in
  `data/source_registry.json`, `data/manual_approval_index.json` and
  `docs/source-manuals/source_manifest.json`. No human content approval has been
  recorded, so the approved and current stay edition remains 2026-07-31.
- The HWP is paragraph-anchored and is deliberately NOT added to the searchable
  corpus or the SQLite index; the page-anchored PDF of the same edition already
  carries that role. Locators, page numbers and counts are never merged across
  the two containers, nor across the 09-01 and 09-18 editions.
- The 2026-09-01 visa HWP supplied with it is byte-identical to the copy already
  committed at `docs/source-manuals/2026-09-01/visa_manual_260901.hwp` (SHA-256
  `6a806dbf6822bb8e4e5c6fd6b758da122dd254d0683533278bd7436d1e87925f`), so nothing
  changed on the visa side.
