# Full Manual → JSON Audit Report — 2026-05-21 Manual Update

Branch: `data/audit-2026-05-21-manual-update-json`
Audit date: 2026-05-24
Auditor: Claude Code (automated, human-reviewed PR required before merge)

> **This document is an internal audit report. It is not legal advice and is not an official immigration decision.**

---

## Executive Summary

This PR audited the Paradiso repository against the user-provided 2026-05-21 Korean immigration manual update (사증발급 안내매뉴얼 + 외국인체류 안내매뉴얼). The audit followed a strict 12-step protocol. No substantive changes were made to `visa_data.json`, `backend/data/visas.json`, or `doc_master.json`.

**Key finding**: The user-attached 2026-05-21 PDF source files (`사증발급 안내매뉴얼_260521.pdf`, `체류민원 안내매뉴얼_260521.pdf`) were referenced at local macOS paths (`/Users/seonjaekim/Downloads/`) that are not accessible from this remote Linux execution environment. A byte-level comparison between the user's 2026-05-21 files and the repo's committed PDFs could not be performed. All immigration data files remain classified as `generic-2026.5-unverified`.

**No file was promoted to `2026-05-21-confirmed`.**

---

## Step-by-Step Protocol Execution

### Step 1 — Environment Readiness

| Tool | Status |
|---|---|
| `pdftotext` (poppler-utils 24.02.0) | ✅ available |
| `pdfinfo` | ✅ available |
| `python3 pypdf 6.12.1` | ✅ available |
| `pdfminer.six 20260107` | ✅ available |
| `python3 -m json.tool` | ✅ available |
| All `scripts/check_*.py` | ✅ run and passed |

### Step 2 — PDF Extraction

Both repo PDFs were fully extracted using `pdftotext -layout` with form-feed page splitting:

| Manual | File | Pages | Lines extracted |
|---|---|---|---|
| Visa | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | 484 | ~20,909 |
| Stay | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | 774 | ~33,246 |

Per-page text files were written to `tmp/manual-2026-05-21/` (`.gitignore`d, not committed). Extraction completed without errors.

**Source-identity check results:**

| Field | Visa manual | Stay manual |
|---|---|---|
| Cover label | `2026. 5.` (month-level only) | `2026. 5.` (month-level only) |
| PDF internal CreationDate | `2026-05-07T00:54:33Z` | `2026-05-07T00:53:43Z` |
| Latest body date marker | `2026.2.12.` | `2026.2.12.` |
| Pilot project end date in body | — | `2026년 5월 19일` |
| SHA-256 | `5a191aed…84063` | `0492683…b3ba` |
| User-attached comparison | **BLOCKED** (local macOS path not reachable) | **BLOCKED** |

These facts are consistent with the repo PDFs being a pre-2026-05-21 (likely 2026-05-04 / created-2026-05-07) version of the "2026.5" manuals, but this is not proven. `source_date` is set to `"unresolved"` in `docs/source-manuals/source_manifest.json`.

### Step 3 — TOC Maps

Artifacts: `docs/data/2026_05_21_MANUAL_TOC_MAP.md` and `docs/data/2026_05_21_manual_toc_map.json`

Section-title anchors (spaced Korean name + code in parentheses at page start) were detected by regex across all per-page text files.

| Manual | TOC sections | High-confidence anchors | Low-confidence / no-header | Pointer-only sections |
|---|---|---|---|---|
| Visa (484 pp) | 40 | 35 | 2 (E-5, E-6) | 3 (F-4, H-2 → §38; partially F-5) |
| Stay (774 pp) | 41 | 38 | 1 (E-2) | 0 |

**Key structural anomalies documented:**
1. Stay manual D-8/D-9 body-order swap: D-9 (p112–114) prints before D-8 (p115+) despite TOC numbering.
2. Visa manual F-4/H-2 are TOC pointers to §38 外国국적동포 sub-manual.
3. §38 (visa) / §36 (stay): "알기쉬운 외국국적동포 업무 매뉴얼" — a separate Feb 2026 sub-manual bundled inside the May 2026 outer manual.
4. Visa manual E-5 and E-6 lack dedicated section-title header lines.
5. Stay manual E-2 lacks a dedicated section-title header line.

### Step 4 — Repo JSON Inventory

Artifacts: `docs/data/2026_05_21_REPO_JSON_INVENTORY.md` and `docs/data/2026_05_21_repo_json_inventory.json`

25 files inventoried. Classification results:

| Date alignment | Count |
|---|---:|
| `generic-2026.5-unverified` | 9 |
| `mirrors source` / `inherits` | 4 |
| `not-manual-dependent` | 5 |
| `infrastructure` | 4 |
| `n/a (audit-only)` | 3 |

**No file classified as `2026-05-21-confirmed`.**

### Step 5 — Manual → JSON Crosswalk

Artifacts: `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.md` and `docs/data/2026_05_21_manual_json_crosswalk.json`

Every `visa_data.json` record (58 total) was mapped to its manual section(s). Summary:

| Action | Records |
|---|---:|
| `no-change` (helper records) | 17 |
| `needs-page-review` (manual-dependent, locatable) | 34 |
| `needs-followup-pr` (high-risk gap or duplicate code) | 7 |

`needs-followup-pr` records: D-4-2K×2 (duplicate code), F-4, H-2, F-6, K-STAR, REGION-S.

### Step 6 — Full `visa_data.json` Audit

Artifacts: `docs/data/2026_05_21_VISA_DATA_FULL_AUDIT.md` and `docs/data/2026_05_21_visa_data_full_audit.json`

All 58 records audited individually:

| Metric | Count |
|---|---:|
| `verified=false` in all manual-dependent records | 41 of 41 |
| `needsManualReview=true` in all manual-dependent records | 41 of 41 |
| Records with stale `2026.3` date marker | 1 (F-6 income note, 3 occurrences) |
| Records with `2026.4` marker | 0 |
| Records claiming `2026-05-21` | 0 |
| `D-4-2K` duplicate count | 2 (indices 24 and 55) |

### Step 7 — Patch Policy (Patch Decision)

Per the hard rules, no substantive patch was applied to `visa_data.json`:
- No stale date marker was corrected (requires exact page evidence).
- No eligibility, income, fee, stay-period, or procedure claim was updated.
- No `verified` flag was advanced.
- No `needsManualReview` flag was removed.
- No doc list was rewritten.

The only substantive file change in this PR is `docs/source-manuals/source_manifest.json`, which adds date-level metadata fields (including `source_date: "unresolved"`) without changing any immigration-data values.

### Step 8 — `doc_master.json` Cleanup Queue

`doc_master.json` has:
- 79 total entries
- 66 referenced by `visa_data.json`
- 12 corrupted entries with literal Korean phrases as `id` (e.g. `"수수료"`, `"여권"`, `"표준규격사진 1매"`)
- 1 unused normal entry (`doc_arc_fee`)

No change made in this PR. Cleanup deferred to a follow-up PR.

### Step 9 — Validation Suite

| Check | Command | Result |
|---|---|---|
| All new JSON artifacts | `python3 -m json.tool` | ✅ All valid |
| Source manuals | `scripts/check_source_manuals.py` | ✅ OK |
| Visa data sync | `scripts/sync_visa_data.py --check` | ✅ OK (no edit needed) |
| Source updates | `scripts/check_source_updates.py --local-only` | ✅ Both PDFs unchanged |
| Text integrity | `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| Doc coverage | `scripts/check_required_documents_coverage.py` | ✅ No regressions |
| Coverage matrix | `scripts/validate_coverage_matrix.py` | ✅ OK (20 rows, 3 active fixtures) |

### Step 10 — Search Checks

| Pattern | Count in `visa_data.json` | Notes |
|---|---|---|
| `"2026.3"` | 3 | F-6 income note (documented, not patched) |
| `"2026.4"` | 0 | None |
| `"2026-05-21"` | 0 | None claimed |
| `"verified":false` | 41 | All manual-dependent records |
| `"needsManualReview":true` | 41 | All manual-dependent records |
| Code `"K-STAR"` | 1 | Dedicated record present |
| Code `"REGION-S"` | 1 | Dedicated record present |
| Code `"D-4-2K"` | 2 | Duplicate (documented) |

### Step 11 — This Report

### Step 12 — Commit and PR

Changes in this PR:

| File | Change |
|---|---|
| `docs/source-manuals/source_manifest.json` | Added date-level metadata fields (`source_date: "unresolved"`, `pdf_internal_creation_date`, `file_sha256`, `file_size_bytes`, `verification_status`, `audit_history`). No immigration-data values changed. |
| `docs/data/2026_05_21_REPO_JSON_INVENTORY.md` | New audit artifact |
| `docs/data/2026_05_21_repo_json_inventory.json` | New audit artifact |
| `docs/data/2026_05_21_MANUAL_TOC_MAP.md` | New audit artifact |
| `docs/data/2026_05_21_manual_toc_map.json` | New audit artifact |
| `docs/data/2026_05_21_MANUAL_JSON_CROSSWALK.md` | New audit artifact |
| `docs/data/2026_05_21_manual_json_crosswalk.json` | New audit artifact |
| `docs/data/2026_05_21_VISA_DATA_FULL_AUDIT.md` | New audit artifact |
| `docs/data/2026_05_21_visa_data_full_audit.json` | New audit artifact |
| `docs/data/2026_05_21_FULL_MANUAL_JSON_AUDIT_REPORT.md` | This report |

**No changes to `visa_data.json`, `backend/data/visas.json`, or `doc_master.json`.**

---

## Outstanding Issues for Follow-up PRs

### Priority 1 — F-6 Income Note (stale 2026.3 marker)

The F-6 income note contains three occurrences of `"체류민원 안내매뉴얼 2026.3 발췌"`. This note must be updated or removed after a reviewer extracts the income eligibility table from stay manual §33 pp.478–501 (specifically F-6-1 소득요건). This was the blocker for prior PR #145 and remains unresolved.

**Target pages**: Stay §33 pp.478–501 (visa §34 pp.324–335 for visa issuance side).

### Priority 2 — D-4-2K Duplicate Code

Two `visa_data.json` records share code `D-4-2K`:
- Index 24: `한국어연수(K-연수생)` — D-4-2K in the D-4 sub-code sense
- Index 55: `기업맞춤형인턴십(K-Trainee)` — 2025-10-29 신설 시범사업

A follow-up PR must assign a unique code to one of them (e.g., `D-4-2T` for K-Trainee or use a `subCode` structure) with page-level evidence from Visa §12 pp.73–87 / Stay §12 pp.83–101.

### Priority 3 — F-4 and H-2 (Feb 2026 sub-manual)

Both F-4 and H-2 content is sourced from the "알기쉬운 외국국적동포 업무 매뉴얼" — a Feb 2026 sub-manual bundled inside the May 2026 outer manual. The `dataDate` is `2026-02-12`. The actual May 2026 outer manual's visa/stay sections for these codes are pointer-only. A dedicated PR should:
- Extract F-4 and H-2 content from Stay §36 pp.522–588.
- Confirm whether the Feb 2026 sub-manual content changed in the May 2026 reprint.
- Document H-2 신규발급 중단 status.

### Priority 4 — K-STAR Sub-manual

K-STAR has dedicated sub-manuals in both the visa (§40 pp.456–484, 29 pp) and stay (§41 pp.746–774, 29 pp) manuals. The existing `K-STAR` record in `visa_data.json` has all fields `needsManualReview=true`. A dedicated PR should extract eligibility, required documents, and procedures from both sub-manual sections.

### Priority 5 — REGION-S (지역특화형 + 광역형)

Stay §37 (지역특화형비자, pp.589–651, 63 pp) and Stay §40 (광역형 비자 시범사업, pp.683–745, 63 pp) are the two largest special sections in the stay manual. The existing `REGION-S` record models both programs but all fields are `needsManualReview=true`. A dedicated PR should extract both sections independently.

---

## Source-Date Caveat (preserved verbatim from source_manifest.json)

> "Per the data/audit-2026-05-21-manual-update-json task, the user-attached PDF files at local macOS paths (/Users/seonjaekim/Downloads/) were not accessible from this remote Linux execution environment, so a byte-level comparison against the user's 2026-05-21 files could not be performed. The repo PDFs' cover pages carry the generic 'YYYY. 5.' month-level label with no day. The PDF internal CreationDate is 2026-05-07. No internal date marker later than 2026.2.12. was found in the manual body. These facts are consistent with the repo PDFs being a pre-2026-05-21 (likely 2026-05-04 export-on-2026-05-07) version, but this is not proven. The 'source_date' field is therefore set to 'unresolved'. Do not promote 'source_date' to '2026-05-21' without page-level evidence."

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this report, the audited JSON files, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea (`hikorea.go.kr`), 1345 종합민원안내, or a qualified Korean immigration professional. Where this audit could not verify a specific page, statute, or source-date claim, the underlying record is left flagged with `needsManualReview = true` and must be treated as unverified until a human reviewer confirms the source.
