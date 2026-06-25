# Manual QA - 2026 PDF Refresh

## Extraction Quality
- Visa readable text: 458,881 characters, Hangul ratio 0.5952.
- Stay readable text: 716,788 characters, Hangul ratio 0.5823.
- Both PDFs are unencrypted and produce readable Korean text.
- Cover pages were rendered to PNG under `/tmp/paradiso_pdf_verify/` for local visual confirmation.

## Major Status-Code Hits
| Code | Visa TXT Count | Stay TXT Count |
| --- | ---: | ---: |
| D-2 | 65 | 131 |
| D-4 | 49 | 65 |
| D-10 | 49 | 129 |
| E-7 | 126 | 348 |
| E-9 | 36 | 79 |
| F-2 | 82 | 318 |
| F-4 | 100 | 139 |
| F-5 | 80 | 352 |
| F-6 | 20 | 109 |
| G-1 | 17 | 85 |
| G-1-2 | 0 | 1 |
| G-1-5 | 0 | 18 |
| H-2 | 65 | 88 |
| C-3 | 138 | 62 |
| B-1 | 7 | 31 |
| B-2 | 5 | 15 |

## Page Spot Checks
- Visa page 1: cover extracts `사증발급 안내매뉴얼 ... 2026. 6.`
- Stay page 1: cover extracts `외국인체류 안내매뉴얼 2026. 6.`
- Stay page 43-44: D-2 extension/registration evidence remains readable.
- Stay page 90-91: D-4 evidence remains readable.
- Stay page 227: E-7 extension evidence is readable and contains 제출서류 markers.

## Safety Assessment
- The extracted text is suitable for human review and follow-up data migration.
- The page-level JSON preserves source traceability.
- The extraction is not an OCR dump and does not depend on protected HWP/HWPX body bytes.
- The output should not be dumped wholesale into production UI.

## Manual Review Gate
- All canonical authoring statuses remain `needsManualReview: true` after the PDF metadata refresh.
- This is intentional: full text extraction and status inventory are not the same as line-by-line legal field certification.

