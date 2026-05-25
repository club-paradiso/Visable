# 2026-05-21 PDF Source Install Report

**Branch:** `data/install-2026-05-21-pdf-sources`  
**Date:** 2026-05-25  
**Follow-up to:** PR #150 (HWP companion files only), PR #153 (staged incoming PDF/HWP source files)

---

## Summary

This PR installs the 2026-05-21 PDF source files committed under
`docs/source-manuals/2026-05/incoming/` into the canonical manual paths.
Both PDFs have been replaced. The stay manual page count changed from 774 → 777.

| Manual | Prior pages | New pages | SHA changed | Size changed | Installed |
|--------|-------------|-----------|-------------|--------------|-----------|
| Visa Issuance (visa_manual_2026_05.pdf) | 484 | 484 | ✅ yes | ✅ yes | ✅ yes |
| Stay/Residence (stay_manual_2026_05.pdf) | 774 | **777** | ✅ yes | ✅ yes | ✅ yes |

---

## Incoming File Verification (vs. source_files_manifest_2026_05_21.json)

All six incoming files verified against the staged manifest:

| File | Manifest SHA-256 | Actual SHA-256 | Match | Pages |
|------|-----------------|----------------|-------|-------|
| `visa_manual_2026_05_21_source.pdf` | `7fd79509…` | `7fd79509…` | ✅ | 484 |
| `stay_manual_2026_05_21_source.pdf` | `dd0d2f10…` | `dd0d2f10…` | ✅ | 777 |
| `visa_manual_2026_05_21_source.hwp` | `635b8ede…` | `635b8ede…` | ✅ | — |
| `stay_manual_2026_05_21_source.hwp` | `b9c74028…` | `b9c74028…` | ✅ | — |

---

## Comparison: Incoming vs. Prior Canonical

### Visa Issuance Manual

| Field | Prior canonical | Incoming (2026-05-21 source) |
|-------|----------------|------------------------------|
| SHA-256 | `5a191aed…` | `7fd79509…` |
| Size (bytes) | 13,189,369 | 13,194,599 |
| Pages | 484 | 484 |
| PDF CreationDate | 2026-05-07T00:54:33Z | 2026-05-24T11:54:54Z |
| PDF version | 1.3 | 1.3 |
| Cover text (p1) | identical | identical |
| TOC text (p2-10) | identical | identical |

**Decision:** REPLACE — SHA-256, byte size, and PDF internal CreationDate differ.
Page count and cover/TOC text are unchanged, indicating a revised export of the same manual revision.

### Stay/Residence Manual

| Field | Prior canonical | Incoming (2026-05-21 source) |
|-------|----------------|------------------------------|
| SHA-256 | `04926836…` | `dd0d2f10…` |
| Size (bytes) | 14,818,347 | 14,884,075 |
| Pages | **774** | **777** (+3) |
| PDF CreationDate | 2026-05-07T00:53:43Z | 2026-05-24T11:56:30Z |
| PDF version | 1.4 | 1.4 |
| Cover text (p1) | identical | identical |
| TOC text (p2-12) | identical | identical |

**Decision:** REPLACE — SHA-256, byte size, page count, and PDF internal CreationDate all differ.
The 3 added pages are back-matter appendices (붙임 section):

- **붙임 8** — 인구감소지역 지정 변경 고시 (행정안전부 고시 제2024-15호, 2024. 2. 27., 개정)
- **붙임 9** — 우수인재 특별귀화 평가기준 (extended table)
- **붙임 10** — 우수인재 국적신청 상세기술서 (form template)

Cover page and TOC (pages 1-12) are byte-identical to the prior canonical PDF.

---

## pdfinfo — Installed Canonical PDFs

### visa_manual_2026_05.pdf

```
Title:        무제
Author:       lulu
Creator:      한컴오피스 한글 Viewer
Producer:     macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext
CreationDate: Sun May 24 11:54:54 2026 UTC
ModDate:      Sun May 24 11:54:54 2026 UTC
Pages:        484
File size:    13194599 bytes
PDF version:  1.3
```

### stay_manual_2026_05.pdf

```
Title:        무제
Author:       lulu
Creator:      한컴오피스 한글 Viewer
Producer:     macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext
CreationDate: Sun May 24 11:56:30 2026 UTC
ModDate:      Sun May 24 11:56:30 2026 UTC
Pages:        777
File size:    14884075 bytes
PDF version:  1.4
```

---

## Source Date Analysis

- **source_date assigned:** `2026-05-21`
- **Evidence basis:** incoming source-file filenames (`*_260521.*`) and the staged manifest `source_files_manifest_2026_05_21.json` (PR #153)
- **PDF internal CreationDate:** `2026-05-24` — this is the macOS Quartz PDFContext export timestamp, **not** the source-file revision date. The two values are different facts and must not be conflated.
- **Cover page label:** `2026. 5.` — month-level only, no day-level date on either cover page.

---

## HWP Companion Files

Both HWP companion files are in HWP 배포용 (distribution-mode). Body text extraction is blocked:

| HWP | Path | Mode | Extraction |
|-----|------|------|------------|
| Visa | `docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp` | distribution | blocked |
| Stay | `docs/source-manuals/2026-05/stay_manual_2026_05_21.hwp` | distribution | blocked |

Tools attempted: LibreOffice 24.2.7 (fails to load), pyhwp (Python 2.7 only).
`source_file_format_available: ["pdf", "hwp"]` is recorded in source_manifest.json.

---

## Files Modified

| File | Change |
|------|--------|
| `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | Replaced with 2026-05-21 source |
| `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | Replaced with 2026-05-21 source (774 → 777 pages) |
| `docs/source-manuals/source_manifest.json` | Updated SHA-256, size, pages, source_date, pdf_internal_creation_date, verification_status, audit_history |
| `scripts/check_source_manuals.py` | Updated `REQUIRED_ROLES` stay page count 774 → 777 |
| `data/source_registry.json` | Updated `last_known_hash` for both PDFs to reflect installed versions |
| `docs/data/2026_05_21_PDF_SOURCE_INSTALL_REPORT.md` | Created (this file) |
| `docs/data/2026_05_21_pdf_source_install_report.json` | Created |

## Files NOT Modified

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- No legal/manual content patched.

---

## Validation Results

| Command | Result | Notes |
|---------|--------|-------|
| `python3 -m json.tool docs/source-manuals/source_manifest.json` | ✅ PASS | Valid JSON |
| `python3 -m json.tool docs/data/2026_05_21_pdf_source_install_report.json` | ✅ PASS | Valid JSON |
| `python3 scripts/check_source_manuals.py` | ✅ PASS | `[check_source_manuals] OK - current 2026.5 source manuals are registered.` |
| `python3 scripts/check_source_updates.py --local-only` | ✅ PASS | Both PDFs report `unchanged` against updated registry hashes |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ PASS | All 14 steps passed; 194 backend tests OK; golden eval skipped (restricted env) |

---

## Downstream Impact

**PR B must rebuild TOC/crosswalk/audit** because the canonical stay PDF changed from 774 to 777 pages.
All downstream artifacts derived from page numbers in the stay manual are potentially stale:

- `docs/data/2026_05_21_MANUAL_TOC_MAP.md` / `2026_05_21_manual_toc_map.json`
- `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.md` / `2026_05_21_manual_json_crosswalk.json`
- `docs/data/2026_05_21_FULL_MANUAL_JSON_AUDIT_REPORT.md`

PR C/D (legal/manual content patching) should follow PR B.
