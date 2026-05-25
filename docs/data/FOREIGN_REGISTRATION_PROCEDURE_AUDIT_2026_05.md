# Foreign Registration Procedure Audit - 2026.05

> Internal source/data audit for Paradiso. This is reference documentation, not legal advice or an official immigration determination.

## Problem Summary

The search-result required-document section showed a registration tab labeled `외국인등록증 신청`. That label was narrower than the administrative procedure represented in the 2026.5 stay manual and in the structured data, which uses `외국인등록`.

The functional issue was a renderer/data-path mismatch. The three required-document tabs read only:

- `documents_initial`
- `documents_registration`
- `documents_extension`

But current structured registration data is mostly stored under `procedures.registration.requiredDocs` with `procedures.registration.manualRefs`. Because every `documents_registration` field is currently `DATA_MISSING`, concrete registration documents already present in `procedures.registration` were unreachable from the registration tab.

## Files Inspected

- `index.html`
- `ai.html`
- `visa_data.json`
- `backend/data/visas.json`
- `backend/paradiso_backend.py`
- `backend/services/korean_law_client.py`
- `scripts/sync_visa_data.py`
- `scripts/check_required_documents_coverage.py`
- `scripts/check_repo.sh`
- `scripts/smoke_law_grounding.sh`
- `docs/source-manuals/SOURCE_MANUALS.md`
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
- `docs/data/2026_05_21_MANUAL_EXTRACTION_REPORT.md`
- `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md`
- `docs/integrations/LAW_GROUNDING_LIVE_SMOKE_RESULTS.md`

## Root Cause

- **Label issue:** user-facing tab label used `외국인등록증 신청`; changed to `외국인등록`.
- **Rendering/key mismatch:** registration tab consumed `documents_registration`; structured registration content exists under `procedures.registration`.
- **Missing structured data:** many records contain only placeholder/manual-review registration procedure data and should continue to show a source-conscious empty state.
- **Source/manual caution:** records with placeholder registration data were intentionally left unchanged because the current data does not contain concrete, status-specific registration documents verified enough for display.

## Fix Summary

- Kept the internal `registration` key stable.
- Preserved valid `documents_registration` data when it exists.
- Added a fallback from empty/placeholder `documents_registration` to concrete documents in `procedures.registration.requiredDocs`.
- Ignored placeholder document values such as `매뉴얼 확인 필요` so they do not render as real checklist items.
- Added a neutral registration-specific empty state:
  - `이 체류자격의 외국인등록 구비서류는 현재 구조화 데이터에 충분히 정리되어 있지 않습니다. 최신 체류민원 안내매뉴얼 또는 관할 출입국·외국인관서를 확인하세요.`
- Added `scripts/audit_registration_procedure_coverage.py` to report the exact data-path split and frontend/backend sync consistency.

## Affected Records Audited

`python3 scripts/audit_registration_procedure_coverage.py` reports:

- Total records: 58
- Records where document tabs are visible: 58
- Records with concrete direct `documents_registration`: 0
- Records with concrete `procedures.registration` documents: 6
- Records with concrete procedure-only registration documents now reachable by the UI fallback: `C-3`, `D-2`, `F-6`, `A-1`, `A-2`, `A-3`
- Records with registration procedure metadata that remains placeholder/summary-only: 35
- Records with no registration signal: 17, mostly FAQ/scenario/helper records such as `SCN-*`, `FAQ-*`, `NHIS-1`, `K-ETA`, `TB-1`

No visa/status records were patched. This PR does not add, remove, or rewrite manual-derived document content.

## Source/Manual Caution

Canonical source files are documented in `docs/source-manuals/SOURCE_MANUALS.md` as the current 2026.5 source-of-truth PDFs:

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`

Existing registration manual references remain unchanged and retain their `needsManualReview` / confidence markers. The new audit script checks registration manual-reference page ranges against committed manual page limits from the existing extraction report: stay manual 774 pages, visa manual 484 pages.

The 35 placeholder/summary-only records remain unchanged. Examples include `E-7`, `F-2`, `F-5`, `K-STAR`, and `REGION-S`. This avoids copying extension documents into registration, broad-normalizing the data model, or inventing missing registration checklists.

Existing law-grounding code is conservative and opt-in:

- `backend/services/korean_law_client.py` returns `LAW_API_KEY_MISSING`, `LAW_GROUNDING_DISABLED`, or source-unavailable warnings unless explicitly configured.
- `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md` documents external law/public-data grounding as inactive for current runtime behavior.
- `docs/integrations/LAW_GROUNDING_LIVE_SMOKE_RESULTS.md` records prior live smoke blockers.

No live law API key was available or used for this patch, so this PR does not add or assert legal citations beyond existing manual references in the repo.

## Validation Results

Run in this PR:

- `python3 -m json.tool visa_data.json` - PASS
- `python3 -m json.tool backend/data/visas.json` - PASS
- `python3 scripts/sync_visa_data.py --check` - PASS
- `python3 scripts/audit_registration_procedure_coverage.py` - PASS
- `rg "외국인등록증 신청|Alien Registration Card Application" index.html ai.html visa_data.json backend/data/visas.json` - PASS, no matches
- `bash scripts/check_repo.sh` - PASS

## Browser-Smoke Limitation

No browser-only evidence is claimed in this report. If a local browser/server is unavailable in a restricted execution environment, the functional assertion is covered by deterministic rendering-path inspection plus the new audit script.

## Remaining Deferred Issues

- `documents_registration` remains unpopulated across `visa_data.json`; the UI fallback repairs rendering but does not migrate schema.
- The 35 placeholder/summary-only registration records need future manual-page review before content expansion.
- F-6 remains a scenario-sensitive family-status area. Existing `verified=false` / `needsManualReview=true` markers are intentionally preserved.
- Live legal API verification remains unavailable without an operator-provided safe environment and key.
