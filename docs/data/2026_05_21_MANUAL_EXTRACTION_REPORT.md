# 2026-05-21 Manual Extraction Report

Branch: `data/source-update-2026-05-21-manuals-and-notice-monitoring`
Extraction date: 2026-05-24
Companion JSON: `docs/data/2026_05_21_manual_extraction_report.json`

> **This is an internal audit artifact. It is not legal advice and not an official immigration decision.**

---

## 1. Scope

Records the tooling chosen, the per-file extraction outcome, and the chosen primary extraction source for the 2026-05-21 audit work. Inputs are:

- Two **repo PDFs** unchanged from PR #148 (`docs/source-manuals/2026-05/*.pdf`).
- Two **user-attached HWP files** newly installed in PR A (`docs/source-manuals/2026-05/*_2026_05_21.hwp`).

Scratch extraction outputs live under `tmp/` (gitignored).

---

## 2. Tooling installed in this run

| Tool | Version | Purpose | Install method |
|---|---|---|---|
| `poppler-utils` (provides `pdftotext`, `pdfinfo`) | 24.02.0 | PDF text + metadata | `apt-get install poppler-utils` |
| `python3 olefile` | 0.47 | HWP OLE compound stream reader (PrvText, FileHeader, stream inventory) | `pip3 install olefile` |
| `libreoffice` + `libreoffice-h2orestart` | 24.2.7.2 + 0.6.1 | HWP→PDF/HTML/TXT conversion attempt | `apt-get install libreoffice-h2orestart default-jre`, then `unopkg add --shared` |
| `default-jre` (OpenJDK 21) | 21.0.10 | Required by `H2Orestart.jar` | `apt-get install default-jre` |

None of these tools are added to the runtime project dependency files (`requirements.txt`, `package.json`, etc.). They are local extraction tooling only.

---

## 3. Per-file extraction outcome

### 3.1 `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` (repo)

| Field | Value |
|---|---|
| SHA-256 | `5a191aedd7d896b2f60a4065b7646a3ccda3e46abeacf9d34dc3802a19184063` |
| Pages | 484 |
| Primary extraction tool | `pdftotext -layout -enc UTF-8` |
| Plain-text output | `tmp/manual-2026-05-21/visa_manual_2026_05.txt` |
| Plain-text size | 1,190,538 bytes |
| Status | **OK** |

### 3.2 `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (repo)

| Field | Value |
|---|---|
| SHA-256 | `0492683698fdb2ba614b3c3aa791c462d03a68437e730093943e96ea15f7b3ba` |
| Pages | 774 |
| Primary extraction tool | `pdftotext -layout -enc UTF-8` |
| Plain-text output | `tmp/manual-2026-05-21/stay_manual_2026_05.txt` |
| Plain-text size | 1,793,714 bytes |
| Status | **OK** |

### 3.3 `docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp`

| Field | Value |
|---|---|
| SHA-256 | `635b8ede13218bb31a46d2993e8ab5efad211122bcfa6928a951d0fe5bae2ac4` |
| HWP version | 5.1.0.1 |
| FileHeader flags | 0x5 (compressed=1, distribution_mode=1) |
| `BodyText/Section*` body extraction | **FAIL** — sections are empty placeholders (~314–326 bytes each) in distribution mode, as expected. |
| `ViewText/Section*` body extraction | **BLOCKED** — first record header parses (tag=0x1c HWPTAG_DISTRIBUTE_DOC_DATA, payload 256 bytes), but the remainder fails raw-deflate (`zlib.error: invalid block type`), consistent with the spec-defined per-session encryption of the post-header payload. |
| `PrvText` (UTF-16-LE preview) extraction | **OK** — 2,046 bytes confirm cover, date label `2026. 5.`, authority, and TOC head. |
| LibreOffice 24.2.7 + h2orestart 0.6.1 conversion | **FAIL** — `source file could not be loaded` (h2orestart 0.6.1 does not decrypt distribution-mode files). |
| `pyhwp` Python 3.11 install attempt | **FAIL** — current `pyhwp` releases require Python 2.7. |
| Status | **BLOCKED** (preview-only) |

### 3.4 `docs/source-manuals/2026-05/stay_manual_2026_05_21.hwp`

| Field | Value |
|---|---|
| SHA-256 | `b9c7402807e007563c589235e63a0791dfcb864c6d1e6964dcd1d492caf77ce3` |
| HWP version | 5.1.0.1 |
| FileHeader flags | 0x5 (compressed=1, distribution_mode=1) |
| Body extraction status | Same blocker as 3.3 above. |
| `PrvText` extraction | **OK** — confirms cover, date label, authority, TOC head. |
| Status | **BLOCKED** (preview-only) |

---

## 4. Primary extraction source for downstream audit work

Because HWP body extraction is blocked, the primary extraction source for downstream Korean text content in this audit cycle is **the repo PDFs** (`visa_manual_2026_05.pdf` and `stay_manual_2026_05.pdf`), via `pdftotext -layout -enc UTF-8`.

The HWP files are installed in the repo as authoritative **source-truth binaries** carrying filename-level 2026-05-21 evidence, retrievable for re-extraction by a future toolchain. They are not used for content extraction in this audit cycle.

| Manual | Primary text extraction format | Reason |
|---|---|---|
| `visa_issuance_manual` | PDF | HWP distribution-mode extraction blocked |
| `stay_residence_manual` | PDF | HWP distribution-mode extraction blocked |

This is consistent with the task rule: *"If HWP extraction fails but PDF extraction works, continue with PDF and document HWP blocker."*

---

## 5. Page/section mapping confidence

For the repo PDFs:

| Field | Value |
|---|---|
| `pdftotext -layout` page boundaries | preserved via form-feed (`\x0c`) — page count cross-checked against `pdfinfo` (484 / 774) ✅ |
| Korean glyph fidelity | high — extracted text matches expected `사증발급 안내매뉴얼 (체류자격별 대상 첨부서류 등)` cover and TOC entries verbatim. |
| Table extraction | partial — `pdftotext -layout` preserves column alignment via whitespace, but multi-line cells in required-document tables sometimes wrap; downstream crosswalk work must use per-page text + visual reference for verification. |
| OCR required? | no — text layer is present and selectable. |

For the HWP files:

| Field | Value |
|---|---|
| Page/section mapping | not applicable until distribution-mode body is unblocked. |
| PrvText confidence | high for cover / TOC head / authority — these are the only items inside PrvText. |

---

## 6. Known extraction failures and their handling

| Failure | Affects | Handling in PR A |
|---|---|---|
| HWP distribution-mode body extraction blocked | `visa_manual_2026_05_21.hwp`, `stay_manual_2026_05_21.hwp` | Documented here; no downstream data patched on HWP evidence in this PR. |
| 2026-05-21 PDF not received | byte-level comparison against repo PDF | Documented in source intake report; `source_date` remains `unresolved` for PDF entries. |
| `HwpSummaryInformation` empty | corroborating in-file timestamps | Documented; rely on filename + PrvText for HWP identity. |

---

## 7. Scratch outputs

All extracted scratch files live under `tmp/` and are `.gitignore`d.

```
tmp/
├── file_hashes.json
├── incoming/
│   ├── 9334fbf0-260521___________________________________.hwp
│   └── 8c28c425-260521________________________________________________________________________________.hwp
└── manual-2026-05-21/
    ├── visa_manual_2026_05.txt          (1,190,538 bytes; from repo PDF)
    ├── stay_manual_2026_05.txt          (1,793,714 bytes; from repo PDF)
    ├── visa_pdf_p1_6.txt                (cover/TOC for cross-check)
    ├── stay_pdf_p1_6.txt                (cover/TOC for cross-check)
    └── hwp_extract/
        ├── extract_summary.json         (per-section attempt log)
        ├── visa/full.txt                (0 bytes — extraction blocked)
        └── stay/full.txt                (0 bytes — extraction blocked)
```

These are intentionally not committed. A future PR that successfully extracts the HWP body will regenerate this tree.

---

## 8. Validation

| Check | Result |
|---|---|
| `python3 -m json.tool docs/data/2026_05_21_manual_extraction_report.json` | OK |
| `python3 -m json.tool docs/source-manuals/source_manifest.json` (post-PR-A edit) | OK |
| `python3 scripts/check_source_manuals.py` (after manifest schema accepts `alternate_source_files`) | OK |

No data records were changed; coverage/integrity scripts are not affected by this PR.

---

## 9. Recommended next PRs

1. **Unblock HWP** — either via Hancom-Office-side re-export by operator (HWPX or non-distribution HWP), or by user attaching a 2026-05-21 PDF for byte-level comparison.
2. **PR B**: rebuild `docs/data/2026_05_21_MANUAL_TOC_MAP.*`, `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.*`, `docs/data/2026_05_21_VISA_DATA_FULL_AUDIT.*` against 2026-05-21-confirmed source.
3. **PR C**: safe source-grounded metadata patches.
4. **PR D**: per-status required-document patches.

See the task's PR splitting plan (Phase 10) for the full sequence.

---

## 10. Legal Disclaimer

Nothing in this report is legal advice or an official immigration decision. Paradiso is an AI-powered reference tool; users must verify with 출입국·외국인청, HiKorea, 1345, or a qualified professional. No `verified` flag in any repo data file was changed by this PR.
