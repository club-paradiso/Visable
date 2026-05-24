# 2026.5 High-Risk Gap Patch Audit

Branch: `data/verify-and-patch-2026-05-high-risk-gaps`

Audit date: 2026-05-24

Repository: `lucanomics/Paradiso`

> This audit is not legal advice and is not an official immigration decision. Users and reviewers must confirm any case-specific result with the competent immigration office, HiKorea, 1345, or a qualified Korean immigration professional.

## Executive Summary

This follow-up audit was opened to verify and patch the highest-risk 2026.5 manual gaps identified by the prior JSON/manual/law audit. The local environment does not have a page-level PDF extraction path available: `pdftotext`, `pdfinfo`, `pypdf`, `PyPDF2`, `fitz`, `pdfminer`, `mutool`, `qpdf`, `pdfgrep`, `exiftool`, and `gs` were unavailable. `/usr/bin/strings` exists, but it does not provide reliable PDF page-level extraction or page-bound citations for this work.

Because page-level PDF review could not be performed, this PR is audit-only. No substantive immigration/legal data was changed, no required-document lists were rewritten, and no record was marked `verified = true`. The high-risk targets remain `needsManualReview = true` / unresolved until a reviewer can extract and inspect the exact source pages in the committed 2026.5 manuals.

Files added in this PR:

- `docs/data/2026_05_HIGH_RISK_GAP_PATCH_AUDIT.md`
- `docs/data/2026_05_high_risk_gap_patch_matrix.json`

Files intentionally not changed:

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- `index.html`
- `ai.html`
- backend behavior and UI behavior

## Scope And Non-Goals

Scope:

- Inspect current repo state for the five high-risk targets.
- Check whether local PDF extraction tooling exists.
- Preserve the 2026.5 manual source layer as the controlling manual source.
- Produce explicit audit artifacts documenting the blocker, current data state, and remaining review work.

Non-goals:

- No UI redesign.
- No backend behavior change.
- No live law.go.kr, HiKorea, or Ministry of Justice claims.
- No invented eligibility, region, income, or document requirements.
- No source-page verification without actual page extraction.
- No advancement of any high-risk record to `verified = true`.

## Source Files Used

Primary manual source files present in the repository:

| Source | Path | Manifest metadata |
|---|---|---|
| Visa issuance manual | `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `사증발급 안내매뉴얼`, 2026.5, 484 pages |
| Stay/residence manual | `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | `외국인체류 안내매뉴얼`, 2026.5, 774 pages |
| Source manifest | `docs/source-manuals/source_manifest.json` | current source registration |

Local file checks:

| File | Git blob SHA | Local SHA-256 |
|---|---|---|
| `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | `26559cadc83044e85d1cd2d5f4eca7d0cf65d68c` | `5a191aedd7d896b2f60a4065b7646a3ccda3e46abeacf9d34dc3802a19184063` |
| `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | `fcc0b8916d66b2d1d8b78eb305abf07e76f11f83` | `0492683698fdb2ba614b3c3aa791c462d03a68437e730093943e96ea15f7b3ba` |

Repo audit/data files inspected:

- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`
- `data/source_registry.json`
- `backend/data/eval/paradiso_coverage_matrix.json`
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
- `backend/data/manual_grounding/candidates/*`
- `docs/data/JSON_MANUAL_LAW_AUDIT_2026_05.md`
- `docs/data/json_manual_law_audit_2026_05_matrix.json`
- listed validation scripts
- `index.html` and `ai.html` for no-UI-impact confirmation

## Extraction Tools

Tool availability checked in this environment:

| Tool | Available | Result |
|---|---:|---|
| `pdftotext` | No | `command -v pdftotext` returned no path |
| `pdfinfo` | No | `command -v pdfinfo` returned no path |
| Python `pypdf` | No | `importlib.util.find_spec("pypdf")` false |
| Python `PyPDF2` | No | `importlib.util.find_spec("PyPDF2")` false |
| Python `fitz` | No | `importlib.util.find_spec("fitz")` false |
| Python `pdfminer` | No | `importlib.util.find_spec("pdfminer")` false |
| `mutool` | No | no path |
| `qpdf` | No | no path |
| `pdfgrep` | No | no path |
| `exiftool` | No | no path |
| `gs` | No | no path |
| `strings` | Yes | `/usr/bin/strings`, not suitable for page-level PDF verification |

Decision from tooling check: source-page review is blocked. Under the requested hard rules, substantive data patching was stopped.

## Exact Manual Sections / Pages Inspected

No exact manual pages were independently inspected in this PR because no reliable local PDF text/page extraction tool was available.

Existing repo metadata and prior audit artifacts mention approximate sections and prior page references, but this PR does not treat those as newly revalidated page-level evidence. The only safe statement from this run is that the committed PDFs and manifest exist locally and that exact page review remains required.

## Target Findings

### 1. D-4-2K

Current repo state:

- `visa_data.json` contains a `D-4` parent record with a `D-4-2K` subcode named `한국어연수(K-연수생)`.
- `visa_data.json` also contains a top-level `D-4-2K` record named `한국어연수(K-연수생)`.
- `visa_data.json` also contains a top-level `D-4-2K` record named `기업맞춤형인턴십(K-Trainee)`.
- `backend/data/visas.json` mirrors the same state.
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` explicitly says the active D-4 grounding covers `D-4-1` and `D-4-7` only and does not cover `D-4-2K`.

2026.5 manual finding:

- Not independently verified in this PR. Exact D-4 section pages could not be extracted or inspected.

Decision:

- `unresolved`.
- No code/subcode rename, merge, deletion, or document-list patch was made.

Files changed:

- Audit artifacts only.

Remaining risk:

- The repo may contain a real duplicate bug, two distinct tracks with insufficient code/subcode modeling, a renamed/obsolete entry, or a partially modeled policy addition. A reviewer must inspect the 2026.5 stay manual D-4 pages before changing the records.

### 2. Top-Tier Visa Gap

Current repo state:

- `visa_data.json` has `D-10-T` as a subcode under `D-10`.
- `visa_data.json` has `E-7-T` as a subcode under `E-7`.
- `visa_data.json` has `F-2-T` as a subcode under `F-2`.
- `visa_data.json` has `F-5-T` as a subcode under `F-5`.
- `docs/data/json_manual_law_audit_2026_05_matrix.json` still has a `TOP-TIER` row marked `modeled_in_visa_data=false`, which does not fully reflect the current subcode-level data state.
- These subcode entries remain under parent records whose `sourceManualStatus.verified` is `false` and `sourceManualStatus.needsManualReview` is `true`.

2026.5 manual finding:

- Not independently verified in this PR. Exact Top-Tier manual sections/pages could not be extracted or inspected.

Decision:

- `deferred`.
- No umbrella record, separate records, alias-only patch, or source-manual status change was made.
- The current matrix mismatch is documented in the new follow-up matrix instead of patching the prior matrix without source-page review.

Files changed:

- Audit artifacts only.

Remaining risk:

- It is unclear whether the product should represent Top-Tier as one umbrella record, separate records, subcodes only, aliases/search keywords, or another structure. Exact manual page review is required before changing data shape or user-facing text.

### 3. 광역형 비자 시범사업

Current repo state:

- `visa_data.json` contains top-level `REGION-S` named `지역특화·광역형 비자 시범사업`.
- `docs/data/json_manual_law_audit_2026_05_matrix.json` has both a `REGION-S` modeled row and a separate `광역형` row marked `modeled_in_visa_data=false`.
- `REGION-S` remains `verified=false` / `needsManualReview=true`.

2026.5 manual finding:

- Not independently verified in this PR. Exact 광역형 pages/section could not be extracted or inspected.

Decision:

- `unresolved`.
- No new dedicated record, alias patch, eligibility patch, region patch, or document-list patch was made.

Files changed:

- Audit artifacts only.

Remaining risk:

- The current `REGION-S` record may or may not cover the 광역형 시범사업 sufficiently. A reviewer must inspect the exact 2026.5 stay manual section before deciding whether to add a separate record or conservative aliases.

### 4. 국내 성장 기반 외국인 청소년 취업·정주 체류제도

Current repo state:

- `visa_data.json` contains this phrase inside D-10 text/procedure-derived content.
- No dedicated top-level record or clear helper entry was found for `국내 성장 기반 외국인 청소년 취업·정주 체류제도`.
- `docs/data/json_manual_law_audit_2026_05_matrix.json` has `청소년취업정주` marked `modeled_in_visa_data=false`.

2026.5 manual finding:

- Not independently verified in this PR. Exact pages/section could not be extracted or inspected.

Decision:

- `deferred`.
- No record, alias, helper entry, eligibility text, or document-list patch was made.

Files changed:

- Audit artifacts only.

Remaining risk:

- The current D-10 text may mention the program without giving users a safe, discoverable model. A source-page reviewer must decide whether this belongs as a D-10 sub-scenario, alias, helper entry, or deferred manual-review-only note.

### 5. F-6 Income Figures

Current repo state:

- `visa_data.json` and `backend/data/visas.json` still contain F-6-1 income note text labeled `체류민원 안내매뉴얼 2026.3 발췌 — 2026.5 매뉴얼 대비 갱신 여부 수동 검토 필요`.
- The figures were not changed.
- Existing F-6 candidate grounding under `backend/data/manual_grounding/candidates/f6_divorce_status_change/` is draft-only and does not verify F-6 income figures.

2026.5 manual finding:

- Not independently verified in this PR. Exact F-6 income pages could not be extracted or inspected.

Decision:

- `unresolved`.
- No provenance wording or income figures were changed.

Files changed:

- Audit artifacts only.

Remaining risk:

- The 2026.3 provenance warning remains visible. A reviewer must locate the exact 2026.5 F-6 income requirement pages and compare the figures before changing provenance wording or numbers.

## Validation Commands And Results

Validation was run after adding the audit artifacts. See the PR body for the concise command summary.

| Command | Result |
|---|---|
| `python3 -m json.tool visa_data.json > /tmp/visa_data_check.json` | OK |
| `python3 -m json.tool backend/data/visas.json > /tmp/backend_visas_check.json` | OK |
| `python3 -m json.tool doc_master.json > /tmp/doc_master_check.json` | OK |
| `python3 -m json.tool docs/data/json_manual_law_audit_2026_05_matrix.json > /tmp/audit_matrix_check.json` | OK |
| `python3 -m json.tool docs/data/2026_05_high_risk_gap_patch_matrix.json > /tmp/high_risk_gap_patch_matrix_check.json` | OK |
| `python3 scripts/sync_visa_data.py --check` | OK |
| `python3 scripts/check_visa_data_text_integrity.py` | OK |
| `python3 scripts/check_required_documents_coverage.py` | OK |
| `python3 scripts/check_source_manuals.py` | OK, with `pdfinfo` warning/skipped page-count verification |
| `python3 scripts/check_source_updates.py --local-only` | OK |
| `python3 scripts/validate_coverage_matrix.py` | OK |
| `python3 scripts/validate_manual_grounding_candidate.py` | OK |
| `bash scripts/check_repo.sh` | OK, including backend tests and non-strict golden eval |

Search checks were run for duplicated `D-4-2K`, `2026.3`, `체류민원_0504.pdf`, `pdftotext -layout`, and exact true/false verification flag patterns. The first four checks have existing repo hits and are documented as remaining review risks, not new claims from this PR. The exact verification-flag checks returned no hits.

## Final Statement

This PR is an audit-only blocker report. It does not change immigration eligibility, required documents, procedures, UI, backend behavior, or source PDFs. It does not provide legal advice or an official immigration decision.
