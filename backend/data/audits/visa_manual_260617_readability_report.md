# 260617 Visa Manual HWP Readability Report

## Source
- Official URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Notice title confirmed on page: `체류자격별 통합 안내 매뉴얼(최신)`
- Original filename: `260617 사증민원 자격별 안내 매뉴얼.hwp`
- Normalized filename: `backend/data/sources/manuals/260617_visa_manual.hwp`
- File size: 2,137,600 bytes
- SHA-256: `bf9fe9117f026a020eac7162336b5c8e46110e5c7d38558ac1e0e7924e1ffe35`
- File type: Hangul Word Processor 5.x

## Acquisition
- Local file found: yes, in `~/Downloads`
- Browser/page route attempted: yes
- Direct attachment download attempted: yes, through the normal HiKorea attachment endpoint after confirming the notice page
- Download result: success; the downloaded `APND_SEQ=479` attachment hash-matched the local file exactly
- Downloaded error page: no

## Readable exports found
- PDF export: `backend/data/sources/manuals/260617_visa_manual_exported.pdf`
- PDF SHA-256: `d3f12e1292eb350ac928cf696402b8a10850511e2220fb0bc05532bd19ba86c9`
- PDF metadata: 487 pages, unencrypted, created by `한컴오피스 한글 Viewer`
- Existing readable text copied for audit: `backend/data/sources/manuals/260617_visa_manual_readable.txt`
- Readable text SHA-256: `58a9d65a4625628e7487e869fd26cc866aed508d7ed524a2cb747a655f3df290`
- Section JSON: `backend/data/sources/manuals/260617_visa_manual_sections.json`

## Extraction methods tried
- Direct HWP body extraction: blocked; the HWP is distribution-mode in available tooling
- Existing readable text route: successful, using repository-held official text extracted from the 487-page 2026.6 visa manual
- PDF route: usable for identity/metadata and fallback review; `pdfinfo`, `pypdf`, and `pdfplumber` are available in the bundled desktop runtime
- LibreOffice DOCX/PDF/TXT: unavailable in this desktop environment (`soffice` and `libreoffice` not found)
- HWP/PyHWP tools: unavailable (`hwp5txt` and `hwp2md` not found)

## Extraction result
- Result: readable reference available, but not promoted
- Output TXT: `backend/data/sources/manuals/260617_visa_manual_readable.txt`
- Output JSON: `backend/data/sources/manuals/260617_visa_manual_sections.json`
- Character count: 484,234 characters
- Byte count: 1,050,917 bytes
- Line count: 22,171
- Hangul ratio: 0.5640
- Sections/pages recorded: 487
- Distinct status codes detected: 40
- Major status code hits: D-2 65, D-4 49, D-10 49, E-7 126, E-9 36, F-2 82, F-4 100, F-5 80, F-6 20, G-1 17, H-2 65, C-3 138, B-1 7, B-2 5

## Quality assessment
- Human-readable: yes
- Tables preserved: partially, as page/paragraph text
- Section/source traceability: page-level section records are preserved
- Suitable for automatic data migration: no, not by itself; a separate human-reviewed PR is required

## Blockers
- The official HWP original is not directly readable with available HWP tooling.
- The 260623 change log is unreadable, so any cross-domain change claims must wait for a readable change log.
- Visa issuance guidance must remain separate from stay/residence guidance.

## Next step
- Use the readable 260617 visa manual text only in a separate source-grounded review PR.
- Do not apply visa-issuance text to stay/residence fields.
