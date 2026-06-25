# 260623 Stay Manual HWPX Readability Report

## Source
- Official URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Notice title confirmed on page: `체류자격별 통합 안내 매뉴얼(최신)`
- Original filename: `260623 체류민원 자격별 안내 매뉴얼.hwpx`
- Normalized filename: `backend/data/sources/manuals/260623_stay_manual.hwpx`
- File size: 3,649,486 bytes
- SHA-256: `37b26a44bb075b02fb73d2b15825b5091da01039a9fd77f5887144edd8f9dad5`
- File type: ZIP/HWPX package with `application/hwp+zip` mimetype

## Acquisition
- Local file found: yes, in `~/Downloads`
- Browser/page route attempted: yes
- Direct attachment download attempted: yes, through the normal HiKorea attachment endpoint after confirming the notice page
- Download result: success; the downloaded `APND_SEQ=482` attachment hash-matched the local file exactly
- Downloaded error page: no

## Package inspection
- ZIP/HWPX valid: yes
- Entry count: 48
- Key entries: `mimetype`, `version.xml`, `Contents/content.hpf`, `Contents/header.xml`, `Contents/section0.xml` through `Contents/section22.xml`, `Preview/PrvText.txt`, `META-INF/manifest.xml`
- Metadata found: HWPX mimetype and manifest
- Encrypted entries: 42 manifest entries, including `Contents/header.xml`, all `Contents/section*.xml`, `Preview/PrvText.txt`, and several embedded assets
- Body payload: section files start with non-XML encrypted bytes

## Extraction methods tried
- Direct HWPX XML: blocked; all 23 section body files are manifest-marked encrypted
- Existing HWPX extractor diagnostics: created `260623_stay_manual_extracted.txt`, `260623_stay_manual_extracted.md`, and `260623_stay_manual_sections.json`
- LibreOffice DOCX/PDF/TXT: unavailable in this desktop environment (`soffice` and `libreoffice` not found)
- HWP/PyHWP tools: unavailable (`hwp5txt` and `hwp2md` not found)
- PDF route: no 260623 stay PDF export was found
- TXT/DOCX route: no 260623 stay TXT or DOCX export was found

## Extraction result
- Result: failed for readable text; diagnostic extraction only
- Output TXT: `backend/data/sources/manuals/260623_stay_manual_extracted.txt`
- Output MD: `backend/data/sources/manuals/260623_stay_manual_extracted.md`
- Output JSON: `backend/data/sources/manuals/260623_stay_manual_sections.json`
- Character count: 2,325 bytes of diagnostics, not manual text
- Hangul ratio: not meaningful; body text is unreadable
- Detected status codes: none
- Sections recorded: 23
- Parse errors recorded: 23

## Quality assessment
- Human-readable: no
- Tables preserved: no
- Section/source traceability: yes, section filenames and parse errors are preserved
- Suitable for follow-up data migration: no

## Blockers
- The official 260623 stay manual is a valid distribution/protected HWPX package.
- All body sections needed for source-grounded text extraction are encrypted/non-XML in the package.
- The companion 260623 change log is also unreadable, so the delta from the readable 260617 stay text cannot be verified.

## Next step
- Obtain a Hancom-exported DOCX/TXT/PDF of the 260623 stay manual or a readable official equivalent.
- Read the 260623 change log before applying any 260623 stay/residence guidance.
- Keep the existing verified baseline until a readable 260623 source is reviewed.
