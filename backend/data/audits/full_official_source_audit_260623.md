# Full Official Source Audit - 260623

## Summary
- Retried official-source acquisition from desktop Codex for the HiKorea latest manual notice.
- Confirmed the notice title `체류자격별 통합 안내 매뉴얼(최신)` and downloaded all three expected attachments through the normal public attachment endpoint.
- Preserved official originals and diagnostics under `backend/data/sources/manuals/`.
- Confirmed the 260623 stay manual and 260623 change log are valid HWPX packages but unreadable for body text because their section entries are encrypted.
- Confirmed readable 260617 reference text exists for the visa manual and the June 17 stay baseline, but did not use either as a substitute for unreadable 260623 stay/change-log text.
- Made no substantive immigration guidance changes.

## Official notice
- URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Notice title: `체류자격별 통합 안내 매뉴얼(최신)`
- Attachments confirmed:
  - `260623 체류민원 자격별 안내 매뉴얼.hwpx`
  - `260617 사증민원 자격별 안내 매뉴얼.hwp`
  - `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`

## Sources acquired
- `backend/data/sources/manuals/260623_stay_manual.hwpx`
  - Original: `260623 체류민원 자격별 안내 매뉴얼.hwpx`
  - Size: 3,649,486 bytes
  - SHA-256: `37b26a44bb075b02fb73d2b15825b5091da01039a9fd77f5887144edd8f9dad5`
  - Acquisition: local Downloads plus browser-confirmed direct attachment download; downloaded file hash-matched local copy
  - Domain: post-entry stay/residence civil affairs
- `backend/data/sources/manuals/260617_visa_manual.hwp`
  - Original: `260617 사증민원 자격별 안내 매뉴얼.hwp`
  - Size: 2,137,600 bytes
  - SHA-256: `bf9fe9117f026a020eac7162336b5c8e46110e5c7d38558ac1e0e7924e1ffe35`
  - Acquisition: local Downloads plus browser-confirmed direct attachment download; downloaded file hash-matched local copy
  - Domain: pre-entry visa issuance
- `backend/data/sources/manuals/260623_visa_stay_change_log.hwpx`
  - Original: `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`
  - Size: 25,366 bytes
  - SHA-256: `c96203122ef2d1d4d4031e18531a863a2b48ebcd9dab005647a06a35d55bc6cc`
  - Acquisition: browser-confirmed direct attachment download
  - Domain: visa/stay change log

## Readable references preserved
- `backend/data/sources/manuals/260617_visa_manual_exported.pdf`
  - SHA-256: `d3f12e1292eb350ac928cf696402b8a10850511e2220fb0bc05532bd19ba86c9`
  - PDF metadata: 487 pages, unencrypted, created by `한컴오피스 한글 Viewer`
- `backend/data/sources/manuals/260617_visa_manual_readable.txt`
  - SHA-256: `58a9d65a4625628e7487e869fd26cc866aed508d7ed524a2cb747a655f3df290`
  - Quality: 484,234 characters, Hangul ratio 0.5640, 40 distinct status codes
- `backend/data/sources/manuals/260617_visa_manual_sections.json`
  - Sections/pages: 487
- `backend/data/sources/manuals/260617_stay_manual_readable.txt`
  - Source: existing repository-readable June 17 stay baseline copied for audit evidence
  - SHA-256: `0f8c90b31a8255ceae2369a804bec20d7af51a751f94e4c69c834c7053772631`
  - Quality: 760,911 characters, Hangul ratio 0.5467, 51 distinct status codes
  - Use restriction: not a substitute for unreadable 260623 stay manual or unreadable 260623 change log
- `backend/data/sources/manuals/260617_stay_manual_sections.json`
  - Sections/pages: 778

## Extraction and readability
- 260623 stay HWPX:
  - ZIP/HWPX valid: yes
  - Entry count: 48
  - Sections: 23
  - Parse errors: 23
  - Result: unreadable; all body section files are encrypted/non-XML
  - Diagnostics: `260623_stay_manual_extracted.txt`, `260623_stay_manual_extracted.md`, `260623_stay_manual_sections.json`
- 260623 change log HWPX:
  - ZIP/HWPX valid: yes
  - Entry count: 10
  - Sections: 1
  - Parse errors: 1
  - Result: unreadable; body section is encrypted/non-XML
  - Diagnostics: `260623_change_log_extracted.txt`, `260623_change_log_extracted.md`, `260623_change_log_sections.json`
- 260617 visa HWP:
  - Official original acquired and hash-matched
  - Direct HWP body extraction remains blocked by distribution-mode packaging in available tooling
  - Readable PDF/text exports are available for human review

## Tooling tried
- Added deterministic HWPX diagnostic extractor: `scripts/extract_hwpx_text.py`
- Added smoke test fixture: `scripts/tests/test_extract_hwpx_text.py`
- Available: bundled `pdfinfo`, `pypdf`, `pdfplumber`, and `python-docx`
- Unavailable: `soffice`, `libreoffice`, `hwp5txt`, `hwp2md`, `pandoc`, system `pdftotext`
- HWP converter benchmark classified the 260617 HWP originals as distribution-mode and not directly extractable with available local tooling.

## Data and guidance impact
- Statuses audited: 257 matrix rows
- Canonical authoring statuses audited: 42
- Scenario/help/alias rows audited: 214
- Invalid legacy pseudo-code rows audited: 1 (`D-2-R`, found only in legacy docs/audits)
- Statuses updated: 0
- Statuses preserved: 42 canonical records
- Statuses blocked for 260623 promotion: 42 canonical records plus related helper rows
- Substantive data files changed: none
- Generated runtime data regenerated: no
- Source registry metadata changed: yes, to reflect that desktop acquisition succeeded while readable 260623 extraction remains blocked
- Source manifest metadata changed: yes, active local PDF hash pins were aligned with the files currently present in the repository

## Existing repository baseline
- `backend/data/visa_authoring/statuses/*.json`: 42 files currently reference `sourceManualStatus.sourceDate = 2026-06-17`, with `verified = false` and `needsManualReview = true`.
- `data/source_registry.json`: active runtime manual invariants remain unchanged; 2026.6 text entries remain `not_configured` reference-only.
- No 260623 stay/residence guidance was applied because the 260623 stay manual and change log were not readable.

## Status matrix
- Output: `backend/data/audits/status_matrix_260623.json`
- Shape: one row per audited code after folding duplicate helper appearances into row evidence
- Required fields preserved: code, official Korean name, record path, canonical status, manual presence flags, source dates, subcodes, change flags, UI/Waymaker impact, recommendation, and evidence
- Recommendation distribution:
  - `blocked`: 256
  - `preserve`: 1

## UI and Waymaker
- UI fixes: none
- Waymaker fixes: none
- Reason: no source-supported data change was made, and no new UI or grounding issue was discovered that could be fixed without changing legal guidance.
- Guardrail kept: unreadable 260623 HWPX diagnostics are not treated as parsed source evidence.

## Mission sources
- Mission/embassy enrichment was not attempted beyond the HiKorea official notice and attachments.
- No global mission coverage is claimed.
- Details: `backend/data/audits/mission_visa_sources_audit.md`

## Quality assessment
- Human-readable 260623 stay manual: no
- Human-readable 260623 change log: no
- Human-readable 260617 visa reference: yes
- Tables preserved: partially for readable page-text references; not available for encrypted HWPX bodies
- Source traceability: yes
- Suitable for a 260623 stay/residence migration: no
- Suitable for later human review of 260617 visa text: yes, in a separate PR

## Validation
- `python3 scripts/check_source_grounding_metadata.py`: passed with 6 non-blocking freshness warnings on active manual metadata fields
- `python3 scripts/check_source_updates.py --local-only`: passed; active/local source hashes unchanged after registry and manifest alignment
- `python3 scripts/visa/validate_visa_authoring.py`: passed
- `python3 scripts/visa/build_visa_data.py --check`: passed
- `python3 scripts/check_visa_data_domain_classification.py`: passed
- `python3 -m pytest scripts/tests/test_extract_hwpx_text.py -q || true`: local pytest is not installed, so the pytest invocation could not run
- Direct synthetic HWPX smoke for `scripts/extract_hwpx_text.py`: passed
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`: passed; golden eval skipped because backend dependency bootstrap was allowed to skip

## Blockers
- The 260623 stay manual is a distribution/protected HWPX with encrypted body sections.
- The 260623 change log is also a distribution/protected HWPX with encrypted body sections.
- Without a readable change log, the June 17 stay baseline cannot be safely promoted to the June 23 latest stay guidance.
- Available local tooling does not include Hancom, LibreOffice, HWP text tools, or system `pdftotext`.

## Recommended follow-up
- Obtain official Hancom-exported DOCX/TXT/PDF versions of:
  - `260623 체류민원 자격별 안내 매뉴얼.hwpx`
  - `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`
- Re-run extraction and compare against the June 17 readable baseline.
- Open a separate source-grounded data PR only after readable evidence supports each change.
