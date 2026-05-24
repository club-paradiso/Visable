# 2026-05-21 Source File Intake Report

Branch: `data/source-update-2026-05-21-manuals-and-notice-monitoring`
Intake date: 2026-05-24
Companion JSON: `docs/data/2026_05_21_source_file_intake_report.json`

> **This is an internal audit artifact. It is not legal advice and not an official immigration decision. Paradiso users must verify with 출입국·외국인청 / HiKorea / 1345 before acting.**

---

## 1. Scope

This report documents the intake of user-attached `260521` source files for the 2026-05-21 immigration manual update, the file-level identity evidence gathered, and the extraction status that gates subsequent audit work.

Two HWP (Hancom Hangul) files were attached by the user via the Claude Code on the Web upload channel. **No PDF files were attached in this run.** The repo's existing PDFs at `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` and `…/stay_manual_2026_05.pdf` are unchanged in this run.

---

## 2. Files Found

### 2.1 Incoming user-attached files

| Upload filename | Mapped role | Bytes | SHA-256 |
|---|---|---:|---|
| `9334fbf0-260521___________________________________.hwp` | 사증발급 안내매뉴얼 (visa issuance manual) | 2,170,880 | `635b8ede13218bb31a46d2993e8ab5efad211122bcfa6928a951d0fe5bae2ac4` |
| `8c28c425-260521________________________________________________________________________________.hwp` | 외국인체류 안내매뉴얼 (foreigner stay/residence manual) | 3,175,424 | `b9c7402807e007563c589235e63a0791dfcb864c6d1e6964dcd1d492caf77ce3` |

The `260521` substring in both filenames is treated as **filename-level evidence** of the 2026-05-21 issuance date. Filename evidence alone is not page-level evidence and does not by itself promote `source_date` in `source_manifest.json` to `2026-05-21` for the PDF entries.

### 2.2 Expected files not received

| Expected filename | Status |
|---|---|
| `사증발급 안내매뉴얼_260521_compressed.pdf` | NOT RECEIVED |
| `체류민원 안내매뉴얼_260521_compressed.pdf` | NOT RECEIVED |
| `사증발급 안내매뉴얼_260521.hwpx` | NOT RECEIVED |
| `체류민원 안내매뉴얼_260521.hwpx` | NOT RECEIVED |

No 260521 PDFs were attached. The repo therefore cannot byte-compare a 2026-05-21 PDF against the currently committed `2026-05/*.pdf` repo files.

### 2.3 Installation in repo

The two HWP files were copied into the source-manuals directory under stable, dated names:

| Repo path | Source filename | Bytes | SHA-256 |
|---|---|---:|---|
| `docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp` | `9334fbf0-260521___________________________________.hwp` | 2,170,880 | `635b8ede13218bb31a46d2993e8ab5efad211122bcfa6928a951d0fe5bae2ac4` |
| `docs/source-manuals/2026-05/stay_manual_2026_05_21.hwp` | `8c28c425-260521________________________________________________________________________________.hwp` | 3,175,424 | `b9c7402807e007563c589235e63a0791dfcb864c6d1e6964dcd1d492caf77ce3` |

Naming convention: `<role>_manual_2026_05_21.hwp` aligns with the existing `<role>_manual_2026_05.pdf` files but encodes the filename-level day evidence (`05_21`) explicitly so HWP and PDF artifacts are distinguishable.

---

## 3. HWP File-Level Identity Evidence

Both HWP files were parsed with `olefile` (Python). They are HWP 5.0 OLE compound documents.

| Field | visa HWP | stay HWP |
|---|---|---|
| HWP format version (FileHeader bytes 32-35, LE) | `5.1.0.1` | `5.1.0.1` |
| FileHeader flags (bytes 36-39, LE) | `0x5` | `0x5` |
| compressed flag (bit 0) | true | true |
| distribution_mode flag (bit 2) | **true** | **true** |
| encrypted flag (bit 1) | false | false |
| script_protected flag (bit 3) | false | false |
| `BodyText/Section*` streams | 1 (size ~326 bytes; effectively empty) | 1 (size ~314 bytes; effectively empty) |
| `ViewText/Section*` streams | 13 | 23 |
| `BinData/*` streams | 10 | 16 |
| `HwpSummaryInformation` populated fields | none usable (empty title/author/dates) | none usable |
| `PrvText` (preview) length | 2046 bytes UTF-16-LE | 2046 bytes UTF-16-LE |

### 3.1 PrvText (preview-of-document) extracted contents

`PrvText` is a short, unencrypted UTF-16-LE preview written by the HWP writer. It is not a substitute for the document body, but it is reliable identity evidence.

**Visa HWP `PrvText` first ~300 characters (verbatim):**

```
<사증발급 안내매뉴얼 (체류자격별 대상 첨부서류 등) >

   


2026. 5.

<법       무       부>
<출입국․외국인정책본부>
<目   次>
<>
<1. 외교(A-1)><13. 취재(D-5)><25. 특정활동(E-7)>
<2. 공무(A-2)><14. 종교(D-6)><26. 계절근로(E-8)>
<3. 협정(A-3)><15. 주재(D-7)><27. 비전문취업(E-9)>
<4. 사증면제(B-1)  ‣사증면제협정 체결국가 일람표><16. 기업투자(D-8) ><28. 선원취업(E-10)>
…
```

**Stay HWP `PrvText` first ~300 characters (verbatim):**

```
<외국인체류 안내매뉴얼>


  
2026. 5.


<법       무       부>
<출입국․외국인정책본부>
<目   次>
<>
<‣ 각종 체류허가 신청 시 유의사항><‣ 공통사항 (체류 일반)>
<체류자격별 대상 및 제출서류 등 안내메뉴얼>
<1. 외교(A-1)><20. 회화지도(E-2)>
<2. 공무(A-2)><21. 연구(E-3)>
…
```

### 3.2 Cross-check against repo PDF cover pages

The repo PDFs were extracted with `pdftotext -layout -f 1 -l 6` (poppler-utils 24.02.0). The resulting cover text matches the HWP `PrvText` on every structural marker:

| Marker | Visa HWP PrvText | Visa PDF cover | Stay HWP PrvText | Stay PDF cover |
|---|---|---|---|---|
| Document title | `사증발급 안내매뉴얼 (체류자격별 대상 첨부서류 등)` | identical | `외국인체류 안내매뉴얼` | identical |
| Cover date label | `2026. 5.` | identical | `2026. 5.` | identical |
| Authoring authority | `법무부 / 출입국·외국인정책본부` | identical | `법무부 / 출입국·외국인정책본부` | identical |
| Item count in TOC | 40 items (1–40) | 40 items | 41 items (1–41) | 41 items |
| Item 40 (visa) / Item 41 (stay) | `K-STAR 비자트랙 제도` | identical | `K-STAR 비자트랙 제도` | identical |

**Conclusion of cross-check**: The HWP files are structurally consistent with the repo PDFs (same product, same edition family, same TOC layout). This is necessary but not sufficient to prove byte-identical or content-identical equivalence. We cannot rule out content-level revisions between the PDF export (CreationDate 2026-05-07) and the HWP filename date (2026-05-21).

---

## 4. Extraction Status

| File | Tool | Status |
|---|---|---|
| `visa_manual_2026_05.pdf` (repo) | `pdftotext -layout -enc UTF-8` (poppler-utils 24.02.0) | **OK** — 1,190,538 bytes plain text extracted |
| `stay_manual_2026_05.pdf` (repo) | `pdftotext -layout -enc UTF-8` (poppler-utils 24.02.0) | **OK** — 1,793,714 bytes plain text extracted |
| `visa_manual_2026_05_21.hwp` | `olefile` PrvText | **OK (preview only, ~2 KB)** |
| `visa_manual_2026_05_21.hwp` | full text extraction via record-stream walk + raw deflate | **BLOCKED** — distribution_mode encrypted ViewText |
| `visa_manual_2026_05_21.hwp` | LibreOffice 24.2.7 + libreoffice-h2orestart 0.6.1 (`Hwp2002_Reader` filter) | **FAIL** — `source file could not be loaded` (h2orestart does not decrypt distribution-mode files) |
| `stay_manual_2026_05_21.hwp` | same as visa HWP | same result |

### 4.1 Why HWP body extraction is blocked

The HWP 5.x `distribution_mode` (배포용) flag (FileHeader bit 2) marks the file as a "distribution-only" copy that intentionally protects the document's editable body. In this mode:

- `BodyText/Section*` streams are emptied (we observed each to be ~314–326 bytes, with no parseable text records).
- `ViewText/Section*` streams hold the rendered text but are encrypted with a session key derived from a per-document key payload that is itself stored inside an `HWPTAG_DISTRIBUTE_DOC_DATA` (tag `0x1c`) record at the head of each section.
- The first record header parses correctly (tag=0x1c, size=256), but the data immediately after the 256-byte payload fails both raw-deflate (`zlib.error: invalid block type`) and any other naive decompression, which is consistent with the spec-defined behavior that the remainder of the stream is block-cipher encrypted (Korean civil HWP implementations historically use SEED or AES-128 in ECB mode for this layer).

Implementing distribution-mode decryption requires either (a) a reference implementation of the Hancom session-key derivation, which we are not permitted to copy from external repositories per the task's "no copy" rule, or (b) writing an original implementation from the public HWP 5.0 binary spec, which is out of scope for PR A. The blocker is recorded and revisitable.

### 4.2 What HWP gives us today

Because PrvText is unencrypted and zlib-free, we still gain three usable signals from the HWP files:

1. **Filename evidence** of 2026-05-21 issuance (the upload preserved the `260521` substring).
2. **Structural identity** with the repo PDFs (title, cover date label, authority, TOC item count, and TOC final-item text all match).
3. **Source-truth preservation** — committing the HWP binaries into the repo means a future run with proper distribution-mode tooling can perform full HWP-to-PDF content diffing without having to re-solicit the file from the user.

### 4.3 What HWP does NOT give us today

- No section-by-section body text.
- No table extraction (required-document tables, eligibility tables, fee tables).
- No page-level anchors.
- No proof that HWP content is identical to PDF content. Only consistency.

---

## 5. PDF Identity (unchanged from PR #148 baseline)

The currently committed repo PDFs are unchanged in this PR. Their internal metadata, hashes, and prior identity analysis from `docs/data/2026_05_21_SOURCE_IDENTITY_REPORT.md` (PR #148) remain valid.

| Field | Visa PDF | Stay PDF |
|---|---|---|
| Repo path | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` |
| File size | 13,189,369 bytes | 14,818,347 bytes |
| SHA-256 | `5a191aedd7d896b2f60a4065b7646a3ccda3e46abeacf9d34dc3802a19184063` | `0492683698fdb2ba614b3c3aa791c462d03a68437e730093943e96ea15f7b3ba` |
| PDF internal CreationDate | `2026-05-07T00:54:33Z` | `2026-05-07T00:53:43Z` |
| PDF internal Producer | `한컴오피스 한글 Viewer` (then printed via macOS Quartz PDFContext) | same |
| PDF internal Title | `무제` (Untitled) | `무제` |
| PDF internal Author | `lulu` | `lulu` |
| Pages | 484 | 774 |
| Cover label | `2026. 5.` (month-level only, no day) | `2026. 5.` |

**The PDF source_date remains `unresolved`** because:
- No 260521 PDF was attached for byte-level comparison.
- The repo PDF carries an internal CreationDate of 2026-05-07 — **earlier** than the HWP filename's `260521` date — so the repo PDF could be an earlier export of the same monthly manual and may diverge from the 2026-05-21 HWP content at the body level.
- Structural identity (title, TOC, cover label) is consistent but not page-level.

---

## 6. Decisions Made in This PR (PR A scope)

- **Installed** both HWP files into `docs/source-manuals/2026-05/` under dated names.
- **Did NOT replace** the repo PDFs (no incoming PDF to compare).
- **Did NOT advance** `source_manifest.json[*].source_date` from `"unresolved"` for the PDF entries.
- **Added** an `alternate_source_files` array per role inside `source_manifest.json` describing the HWP files, with their own `source_date: "2026-05-21"` tagged as filename-level evidence and a `verification_status` that explicitly flags the distribution-mode extraction blocker.
- **Did NOT change** any `visa_data.json`, `backend/data/visas.json`, or `doc_master.json` record.
- **Did NOT change** any `verified` flag.
- **Did NOT remove** any `needsManualReview` warning.

This PR is **PR A** in the recommended split (see `docs/data/2026_05_21_MANUAL_EXTRACTION_REPORT.md` "Recommended next PRs" section). Subsequent crosswalk, JSON audit, and patch work is gated on either (a) HWP distribution-mode extraction becoming available or (b) the user attaching a 2026-05-21 PDF for byte-level comparison.

---

## 7. Validation

Ran on this PR:

| Check | Result |
|---|---|
| `python3 -m json.tool docs/source-manuals/source_manifest.json` | OK (after this PR's edit) |
| `python3 -m json.tool visa_data.json` | OK |
| `python3 -m json.tool backend/data/visas.json` | OK |
| `python3 -m json.tool doc_master.json` | OK |
| `python3 -m json.tool docs/data/2026_05_21_source_file_intake_report.json` | OK |
| `python3 -m json.tool docs/data/2026_05_21_manual_extraction_report.json` | OK |
| `python3 scripts/sync_visa_data.py --check` | OK |
| `python3 scripts/check_source_manuals.py` | OK (after manifest schema accepts `alternate_source_files`) |

No data records were changed; coverage/integrity checks are not affected by this PR.

---

## 8. Remaining Risks

- The repo PDFs may not be the 2026-05-21 edition. If they are not, any patches downstream using these PDFs as evidence would propagate stale content into `visa_data.json`. PR B (crosswalk rebuild) must therefore **either** wait for HWP extraction **or** treat all evidence from the repo PDFs as `unresolved-edition` until the user supplies a 2026-05-21 PDF.
- HWP `PrvText` only covers ~2 KB of the cover/TOC. It cannot detect body-level revisions.
- HwpSummaryInformation is empty, so we have no in-file author/created/modified timestamps to corroborate the filename date.

---

## 9. Recommended next steps

1. **Unblock HWP distribution-mode extraction.** Options:
   - Operator runs `hwp5proc` from `pyhwp` on a machine with Python 2 toolchain (the version we tried in this environment requires Python 2.7 only and fails to install on Python 3.11).
   - Operator opens the HWP files in Hancom Office on a desktop machine and re-exports as PDF or HWPX, then re-attaches the export.
   - Future PR can implement an original distribution-mode decryptor against the public HWP 5.0 binary spec (no copying external implementations).
2. **OR**: User attaches `사증발급 안내매뉴얼_260521.pdf` and `체류민원 안내매뉴얼_260521.pdf` for byte-level comparison against the repo PDFs.
3. Once either path delivers usable 2026-05-21 body text, proceed to PR B (crosswalk rebuild) per the PR splitting plan in the task description.

---

## 10. Legal Disclaimer

Nothing in this report is legal advice or an official immigration decision. Paradiso is an AI-powered reference tool; users must verify with 출입국·외국인청, HiKorea, 1345, or a qualified immigration professional before acting. All `verified` flags in repo data files remain unchanged by this PR.
