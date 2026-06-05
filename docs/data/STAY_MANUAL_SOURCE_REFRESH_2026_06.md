# 2026-06-01 Stay/Residence Manual Source Refresh

## Purpose

Record the refresh of Paradiso's current stay/residence manual source artifacts to the user-provided 2026-06-01 set, and document the artifacts, status, validation, and follow-ups.

The binary install and metadata pointer updates were merged into `main` via PR #277 (`fix: generalize legal grounding and source-status handling`, commit `5cfb9b5`). This document is the standalone refresh memo requested by the refresh task brief; the SHA-256 hashes of the user-provided files under `incoming/manuals/2026-06-01/` match the canonical files installed under `docs/source-manuals/2026-06/` bit-for-bit, so no re-install was required on this branch.

## New source files

| Role | Format | Repo path | SHA-256 | Bytes |
| --- | --- | --- | --- | --- |
| Stay/residence manual (current) | PDF | `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` | `e25e97c3c2a05b5676ca3648a04226dcdc2433ab7c89a2f5105e6f8be49778b0` | 14,894,357 |
| Stay/residence manual (companion, stored-only) | HWP | `docs/source-manuals/2026-06/stay_manual_2026_06_01.hwp` | `9bba776083a1599a4fb7c6fc1c4452053652a1750ef6824de72e9e5bdffa297d` | 3,177,472 |

Original user-provided filenames preserved in the intake manifest at `docs/source-manuals/2026-06/incoming/source_files_manifest_2026_06_01.json`:

- `stay_manual_260601.pdf`
- `260601_체류민원_자격별_안내_매뉴얼(숙련기능인력 제도 개선사항 반영).hwp` (filename surfaced from the upload; may appear in decomposed Unicode form depending on the unzip environment)

## Source version / date

- Manual identifier: 외국인체류 안내매뉴얼 (Foreigner Stay/Residence Guide Manual)
- Manual version label: `2026.5`
- Source file revision date: `2026-06-01`
- Issuing body: 법무부 출입국·외국인정책본부 (Ministry of Justice, Korea Immigration Service)
- Pages: 777 (pypdf 6.10.0; matches `scripts/check_source_manuals.py` expectation)
- Cover label: `2026. 5.` (month-level; the day is not encoded in the cover, so `source_date: 2026-06-01` is evidenced via the upload filename and source files manifest, not cover text)

The June PDF supersedes the May 2026.5 stay manual (`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`, 774 pages). The May PDF is retained as an archived artifact for audit comparison only and is marked `deprecated` in `data/source_registry.json`.

## PDF parsed/indexed status

- Primary extraction format: `pdf`
- Extraction tooling: `pypdf 6.10.0` (page count, /Info metadata, sampled page-level text)
- Runtime grounding spot-check pages (43, 44, 90, 91, 226) were extracted from both the May and June PDFs and matched by text SHA-256, so the narrow stay-manual grounding fixture (`backend/data/manual_grounding/stay_manual_grounding_2026_05.json`) was repointed at the June PDF without per-entry content edits.
- Broader structured requirements were regenerated from the June PDF using `scripts/regenerate_2026_06_01_structured_stay_manual_indexes.py`, producing:
  - `backend/data/manual_grounding/structured_requirements_2026_06_01.json` (352 entries, 2,597 document items, 42 statuses)
  - `backend/data/manual_grounding/structured_requirements_index_2026_06_01.json`
  - `docs/data/2026_06_01_structured_stay_manual_refresh_audit.json`
- Runtime accessor (`backend/structured_requirements.py`) loads the `_2026_06_01.json` file by default.

## HWP parsed/indexed status

- Status: `stored_only` (NOT parsed, NOT indexed).
- HWP version flags: `0x5` — compressed, distribution-mode (배포용).
- Local inspection: `olefile 0.47` exposes 1 `BodyText` stream and 23 `ViewText` sections, but `BodyText` extraction returns only the distribution-mode placeholder text, not the manual body. `pyhwp` does not run on Python 3.11+ in the current environment; `libreoffice 24.2.7 + libreoffice-h2orestart 0.6.1` was unable to load the distribution-mode HWP on the related May 2026-05-21 HWPs.
- Decision: keep the HWP as an official source artifact (filename-level evidence of the 2026-06-01 revision), but do not treat it as parsed and do not emit any user-facing grounding citation that depends on HWP body extraction.

## Source catalog / manifest changes

The following pointers describe the post-refresh state on `main`:

- `docs/source-manuals/source_manifest.json`
  - `current.stay_residence_manual.source_date` → `2026-06-01`
  - `current.stay_residence_manual.file` → `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf`
  - `current.stay_residence_manual.pages` → `777`
  - `current.stay_residence_manual.file_sha256` → matches the PDF above
  - `alternate_source_files[]` includes the HWP companion with explicit `extraction_blocker: hwp_distribution_mode_body_text_placeholder`
  - `archived_previous_current` records the prior 2026-05 stay PDF for audit
  - `audit_history` includes the 2026-06-05 refresh entry
- `docs/source-manuals/SOURCE_MANUALS.md` — current/archived sections updated; refresh-status section appended
- `data/source_registry.json`
  - New entry `stay_manual_2026_06_01_pdf` with `status: active`
  - `stay_manual_2026_05_pdf` flipped to `status: deprecated`, `superseded_by: stay_manual_2026_06_01_pdf`
- `data/sources/hikorea_source_catalog.json` — `moj_stay_manual_2026_06_01` references the new repo path
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` — `source_file` repointed to the June PDF; entries retain their `_2026_05` grounding IDs (the suffix is the grounding-fixture revision, not the source date) and `verification_note` records the runtime-page spot-check
- `backend/data/manual_grounding/structured_requirements_2026_06_01.json` and `structured_requirements_index_2026_06_01.json` — regenerated from the June PDF
- `backend/structured_requirements.py` — `_STRUCTURED_FILE` points at `structured_requirements_2026_06_01.json`

## Tests / validation

Existing tests on `main` already enforce the refresh; they were re-run on this branch and all pass:

- `backend/tests/test_source_grounding_pipeline.py::test_*` — asserts `source_manifest.json::current.stay_residence_manual.file == docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` and `source_date == 2026-06-01`
- `backend/tests/test_paradiso_backend.py` — asserts the runtime grounding bundle's `source_file` and `source_revision_date` are the June PDF / `2026-06-01`
- `backend/tests/test_generalized_source_grounding_regression.py` — asserts prompt-builder output includes `version/date: 2026-06-01`
- `backend/tests/test_structured_requirements.py` — exercises the structured-requirements accessor against the June index

Validation commands executed locally on this branch:

```
python3 -m json.tool visa_data.json
python3 -m json.tool backend/data/visas.json
python3 -m json.tool doc_master.json
python3 -m json.tool docs/source-manuals/source_manifest.json
python3 -m json.tool data/source_registry.json
python3 -m json.tool data/sources/hikorea_source_catalog.json
python3 -m json.tool backend/data/manual_grounding/structured_requirements_2026_06_01.json
python3 -m json.tool backend/data/manual_grounding/structured_requirements_index_2026_06_01.json
python3 -m json.tool backend/data/manual_grounding/stay_manual_grounding_2026_05.json
python3 scripts/check_source_manuals.py
python3 scripts/sync_visa_data.py --check
python3 scripts/check_required_documents_coverage.py
python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_06_01.json
python3 -m pytest backend/tests/test_paradiso_backend.py backend/tests/test_structured_requirements.py backend/tests/test_source_grounding_pipeline.py -q
```

Result: every command above returned a clean pass on this branch. `scripts/check_source_manuals.py` emits a `pdfinfo not found` warning in this environment but still validates the manifest schema and required-fields contract; the 777-page assertion is enforced by the script's `REQUIRED_ROLES` map and matches the installed PDF.

## Known limitations

- `visa_data.json` `sourceBasis` strings remain at the month-level label `2026.5 체류민원/사증 매뉴얼…`. The refresh did not rewrite per-entry copy because this PR is explicitly scoped not to broadly rewrite `visa_data.json`.
- The grounding fixture filename `stay_manual_grounding_2026_05.json` is unchanged on disk to avoid a backend constant rename (`_STAY_MANUAL_GROUNDING_FILE` in `backend/paradiso_backend.py`). Its contents already point at the June PDF; only the filename suffix lags.
- HWP body text remains unavailable; any claim that depends on HWP body content would be unverified.
- The structured requirements fixture is large (~1.9 MB). Per-entry confidence/readiness distribution did not materially change between the May and June regenerations; document-level deltas come from the seven pages that changed between the two PDFs (see `docs/data/2026_06_01_structured_stay_manual_refresh_audit.json::pageAudit.changedPages`).

## Follow-up tasks

- Optionally rename `stay_manual_grounding_2026_05.json` to `stay_manual_grounding_2026_06_01.json` along with the backend constant in a separate small PR.
- Refresh the per-entry `sourceBasis` strings in `visa_data.json` from "2026.5 …" to a phrasing that distinguishes the 2026-06-01 stay manual from the 2026-05-21 visa-issuance manual when a deliberate `visa_data.json` rewrite is approved.
- If/when a distribution-mode HWP extractor becomes available, re-evaluate whether the HWP should be promoted from `stored_only` to `parsed`.
- The seven pages that changed between the May and June PDFs (audit IDs `299`, `619`, `620`, `621`, `623`, plus 2 more recorded in the audit file) are concentrated in the 숙련기능인력 (skilled labor) section — a follow-up review of any visa entries that cite those pages is recommended.

## Safety note

This refresh installs and registers official source artifacts and points the runtime at the new PDF. It does not certify that every visa/status document list in `visa_data.json` has been independently revalidated against the June manual. Final agency determination still rests with the relevant 출입국·외국인청/사무소/출장소; Paradiso provides reference information only and does not provide legal advice or filing services.
