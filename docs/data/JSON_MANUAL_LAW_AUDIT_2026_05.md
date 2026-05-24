# JSON × Manual / Law Audit — 2026.5

Branch: `data/manual-law-json-audit-2026-05`
Audit date: 2026-05-24
Scope: Paradiso JSON/data audit against the **2026.5 법무부 출입국·외국인정책본부** immigration manuals.

> **This document is an internal data audit. It is not legal advice and is not an official immigration decision.** End-users must confirm any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified professional.

---

## Executive Summary

This PR is a conservative JSON/data-layer audit and cleanup PR. It does **not** complete full legal/manual verification, does **not** verify required-document lists page by page, and does **not** provide official immigration guidance.

The deterministic changes in this PR are limited to:

1. `doc_master.json` placeholder display labels: 43 generic labels were replaced with clearer Korean/English document names and descriptions where the document ID made the intended meaning unambiguous.
2. `visa_data.json` duplicate common notice cleanup: mechanically repeated legacy `[공통 유의사항]` blocks were removed when an equivalent `[2026-05 공통 유의사항]` block was already present.
3. Legacy source-label cleanup: pure `2026.3` version-stamp notes were reworded to indicate 2026.5 manual alignment **with manual review still required**.
4. F-6 income notes: won figures were **not** changed. Their provenance remains marked as requiring manual review against the 2026.5 stay manual.
5. `backend/data/visas.json` was re-synced from `visa_data.json`.

No required-document list, eligibility rule, procedure block, UI behavior, backend behavior, law-grounding behavior, or source PDF file was changed.

---

## Source Hierarchy

1. **Manual layer (primary for data shape and required-document lists):**
   - `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` — 사증발급 안내매뉴얼, 2026.5, 법무부 출입국·외국인정책본부.
   - `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` — 외국인체류 안내매뉴얼, 2026.5, 법무부 출입국·외국인정책본부.
2. **Law layer (not fetched in this PR):**
   - 국가법령정보센터 (`law.go.kr`)
   - 출입국관리법 / 시행령 / 시행규칙
   - 국적법 / 난민법 / 재외동포법 and related subordinate rules.
3. **Operational notices (not fetched in this PR):**
   - HiKorea notices
   - Ministry of Justice immigration notices and press releases.

`visa_data.json` remains implementation/display data, not source of truth.

---

## Source Manual PDF Verification

The two 2026.5 source PDF files were already present in the repository before this PR branch and were **not changed** by this PR.

GitHub blob verification:

| File | Git blob SHA on base/head | Changed by this PR? | Page count source |
|---|---|---:|---|
| `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `26559cadc83044e85d1cd2d5f4eca7d0cf65d68c` | No | `docs/source-manuals/source_manifest.json` declares 484 pages. |
| `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | `fcc0b8916d66b2d1d8b78eb305abf07e76f11f83` | No | `docs/source-manuals/source_manifest.json` declares 774 pages. |

Important verification limits:

- `pdftotext` was reported unavailable in the follow-up environment. This audit file therefore does **not** claim that `pdftotext -layout` extraction succeeded.
- `pdfinfo`, `pypdf`, `PyPDF2`, and `fitz` page-count checks were reported unavailable in the follow-up environment.
- Page counts in this PR are therefore based on the existing `docs/source-manuals/source_manifest.json`, not on an independent recomputation performed in the follow-up.
- Exact byte sizes and SHA-256 hashes were not independently recomputed through the GitHub connector used for this correction. The available remote verification is the Git blob SHA comparison above.
- No live law.go.kr, HiKorea, or MOJ notice verification was performed in this PR.

This correction intentionally removes the earlier inaccurate implication that both PDF TOCs were extracted with `pdftotext -layout` in this PR.

---

## JSON Inventory

Primary files inspected or affected:

| Path | Kind | Changed |
|---|---|---:|
| `visa_data.json` | canonical visa/status display data | Yes |
| `backend/data/visas.json` | backend mirror of `visa_data.json` | Yes, synced |
| `doc_master.json` | document ID to display-label master | Yes |
| `docs/data/json_manual_law_audit_2026_05_matrix.json` | machine-readable audit matrix | Added |
| `docs/source-manuals/source_manifest.json` | source manual manifest | No |
| `data/source_registry.json` | source allow-list | No |
| `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` | active manual-grounding fixture | No |
| `backend/data/eval/paradiso_coverage_matrix.json` | coverage/eval control data | No |

---

## Files Changed

| File | Change | Reason |
|---|---|---|
| `doc_master.json` | Replaced obvious placeholder labels such as `Tb`, `Bank Bal`, `Mar Rel`, `Id`, and `Cvi` with clearer document names. | Rendering quality fix for document labels where ID/usage made meaning unambiguous. |
| `visa_data.json` | Removed mechanically duplicated common notice blocks and reworded stale pure version labels while preserving `needsManualReview`. | Mechanical cleanup, not substantive legal rewrite. |
| `backend/data/visas.json` | Re-synced from root `visa_data.json`. | Keep backend mirror aligned. |
| `.gitignore` | Added `tmp/` for audit scratch files. | Prevent extraction scratch files from being committed. |
| `docs/data/JSON_MANUAL_LAW_AUDIT_2026_05.md` | Added/updated this audit report. | Review and traceability. |
| `docs/data/json_manual_law_audit_2026_05_matrix.json` | Added machine-readable audit matrix. | Follow-up planning and coverage tracking. |

No source PDF file was changed.

---

## Manual Coverage Summary

The matrix in `docs/data/json_manual_law_audit_2026_05_matrix.json` tracks modeled and unmodeled items. The highest-risk unresolved gaps are:

1. Duplicate `D-4-2K` records in `visa_data.json`.
2. Top-Tier visa tracks: `D-10-T`, `E-7-T`, `F-2-T`, `F-5-T`.
3. 광역형 비자 시범사업.
4. 국내 성장 기반 외국인 청소년 취업·정주 체류제도.
5. F-6 income figures, still tagged as 2026.3 provenance pending 2026.5 manual review.
6. Live law.go.kr verification, not performed.

All status records remain unverified for legal/product purposes unless separately grounded with explicit page references.

---

## Intentionally Not Changed

- No required-document list was rewritten.
- No eligibility rule was rewritten.
- No `procedures.*` block was rewritten.
- No UI or backend behavior was changed.
- No source PDF was replaced.
- No record was advanced to `verified = true`.
- No live law.go.kr / HiKorea / MOJ verification was performed.

---

## Validation Commands Reported

The following checks were reported as passing in the audit run:

| Command | Result |
|---|---|
| `python3 -m json.tool visa_data.json > /tmp/visa_data_check.json` | OK |
| `python3 -m json.tool doc_master.json > /tmp/doc_master_check.json` | OK |
| `python3 scripts/sync_visa_data.py --check` | OK |
| `python3 scripts/check_visa_data_text_integrity.py` | PASS |
| `python3 scripts/check_visa_text_corruption.py` | OK |
| `python3 scripts/check_required_documents_coverage.py` | PASS |
| `python3 scripts/check_source_manuals.py` | OK |
| `python3 scripts/check_source_updates.py --local-only` | OK |
| `python3 scripts/validate_coverage_matrix.py` | OK |
| `python3 scripts/validate_manual_grounding_candidate.py` | 1/1 passed |

The following were not independently completed in the follow-up environment:

- `pdftotext -layout` extraction: unavailable.
- `pdfinfo` page counting: unavailable.
- Python PDF library page counting with `pypdf`, `PyPDF2`, or `fitz`: unavailable.
- Live law.go.kr / HiKorea / MOJ checks: not performed.

---

## Merge Guidance

This PR may be reviewed as a **conservative audit and mechanical cleanup PR**, not as a complete 2026.5 immigration-content update.

Before any future PR marks records as verified or rewrites required-document content, reviewers must confirm exact manual pages and relevant legal/statutory references.

---

## Legal Disclaimer

Paradiso is reference software. This audit, the patched JSON files, and any rendered output do **not** constitute legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea (`hikorea.go.kr`), 1345 종합민원안내, or a qualified Korean immigration professional. Where this audit could not verify a specific page or statute reference, the underlying record is left flagged with `needsManualReview = true` and must be treated as unverified until a human reviewer confirms the source.
