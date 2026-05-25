# 2026-05-21 PDF Source Install Report

Date: 2026-05-25  
Branch: `data/install-2026-05-21-source-pdfs`  
Decision: canonical replacement performed.

## Summary

The staged user-provided source PDFs were compared against the prior canonical repo PDFs using SHA-256, page count, PDF metadata, cover/TOC text extraction, and sampled page-level extraction. The comparison supports installing the incoming PDFs as the canonical 2026.5 source manuals.

No legal/manual content was patched. No downstream immigration data was patched. HWP body extraction was not used as proof.

## Files

| Role | Prior canonical PDF | Incoming PDF | Installed canonical PDF |
| --- | --- | --- | --- |
| Visa issuance | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `docs/source-manuals/2026-05/incoming/visa_manual_2026_05_21_source.pdf` | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` |
| Stay/residence | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | `docs/source-manuals/2026-05/incoming/stay_manual_2026_05_21_source.pdf` | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` |

## SHA-256 Comparison

| Role | Prior canonical SHA-256 | Incoming SHA-256 | Replacement performed |
| --- | --- | --- | --- |
| Visa issuance | `5a191aedd7d896b2f60a4065b7646a3ccda3e46abeacf9d34dc3802a19184063` | `7fd79509c8c92ccd5e3b026d83f6884d69d3e0dcbcdf8c2936daf886a92ae11c` | Yes |
| Stay/residence | `0492683698fdb2ba614b3c3aa791c462d03a68437e730093943e96ea15f7b3ba` | `dd0d2f101c893022f24233d746dd24fc6bd9432eef3ea135f173e54d25f9c3e1` | Yes |

## Page Count Comparison

| Role | Prior pages | Incoming pages | Result |
| --- | ---: | ---: | --- |
| Visa issuance | 484 | 484 | unchanged |
| Stay/residence | 774 | 777 | changed; incoming has 3 additional pages |

## PDF Metadata Comparison

| Role | Prior CreationDate | Incoming CreationDate | Prior producer | Incoming producer |
| --- | --- | --- | --- | --- |
| Visa issuance | `D:20260507005433Z00'00'` | `D:20260524115454Z00'00'` | `macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext` | `macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext` |
| Stay/residence | `D:20260507005343Z00'00'` | `D:20260524115630Z00'00'` | `macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext` | `macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext` |

## Cover And TOC Text

| Role | Cover/TOC result |
| --- | --- |
| Visa issuance | Cover identifies `사증발급 안내매뉴얼`, 2026.5. TOC sample matches the expected visa manual structure; sampled pages 1, 2, 3, 4, 5, 100, 250, and 484 matched prior canonical text hashes. |
| Stay/residence | Cover identifies `외국인체류 안내매뉴얼`, 2026.5. TOC sample matches the expected stay manual structure; sampled pages 1, 2, 3, 4, 5, and 100 matched prior canonical text hashes. Later sampled pages shifted as expected with the 777-page incoming PDF. |

## Basic Extraction Quality

`pypdf` extracted Korean text from each sampled incoming PDF page used in this report. The cover and TOC pages were readable for both PDFs, and mid/end samples returned text. A full all-page extraction was intentionally not used as the proof here because the local desktop runtime was slow; this report records bounded PDF page-level extraction evidence plus manifest and metadata checks.

## Source Manifest Changes

- `source_date` changed from `unresolved` to `2026-05-21` for both current PDF entries.
- `verification_status` changed to `source_file_compared` for both current PDF entries.
- `file_sha256`, `file_size_bytes`, `pages`, and PDF internal metadata fields were updated to match the installed incoming PDFs.
- Audit history was appended for this install.

## Unresolved Risks

- Cover pages still show only `2026. 5.` and do not visibly encode the day-level revision date.
- The day-level date evidence comes from user-provided PDF filenames/manifest plus PDF page-level identity, not from an external official fetch in this PR.
- HWP body extraction remains blocked by distribution mode and was not used as proof.
- The stay manual page count changed from 774 to 777, so downstream citations should be re-audited before data promotion.

## Next Recommended PR

Re-run source extraction/TOC mapping from the newly installed canonical PDFs and produce a citation-drift audit before updating any grounding records or visa data.
