# PARADISO OFFICIAL LAW/MANUAL SOURCESET AND READINESS AUDIT - 2026.5

## 1. Executive verdict

Final verdict: **READY_FOR_SOURCESET_PR**.

The 2026.5 source-set documentation PR is ready because the user-provided 260521 visa/stay manuals were validated, HWP-derived PDFs were checked as usable extraction baselines, and HiKorea official pages now provide official retrieval paths for the core Korean immigration/residence law set, the latest stay-status manuals, address-change/fact-certificate manual, procedure guide pages, electronic civil petition services, reservation guide, and official forms directory.

This verdict does **not** mean production data can be patched. It only means the source inventory and readiness documents are ready to be committed as a documentation-only PR. Full data correction still requires a manual/law/HiKorea crosswalk, field-level source references, parity checks for `visa_data.json` and `backend/data/visas.json`, and a separate metadata gate before `verified=true` or `needsManualReview` changes.

## 2. Uploaded manual second-validation result

### Visa issuance manual

- Source file: `사증발급 안내매뉴얼_260521.pdf`.
- Title: `사증발급 안내매뉴얼`.
- Publication month: `2026. 5.`.
- Publisher: 법무부 출입국·외국인정책본부.
- Page count: 484 pages.
- Coverage: A-1 through H-2, Top-Tier visa, K-STAR visa track.
- Extraction status: PDF text extraction usable for crosswalk.

### Stay/residence manual

- Source file: `체류민원 안내매뉴얼_260521.pdf`.
- Title: `외국인체류 안내매뉴얼` / `체류민원 안내매뉴얼`.
- Publication month: `2026. 5.`.
- Publisher: 법무부 출입국·외국인정책본부.
- Page count: 777 pages.
- Coverage: common stay matters, stay-status-specific documents, foreigner registration, extension, change of status, workplace/address/passport reporting, regional visa programs, Top-Tier, and K-STAR.
- Extraction status: PDF text extraction usable for crosswalk.

## 3. Test/source environment

Sources reviewed for this documentation PR:

- User-provided 260521 visa/stay PDFs.
- User-provided HWP originals and HWP-derived PDFs.
- Repository source-manual path expectations under `docs/source-manuals/2026-05/`.
- 국가법령정보센터 / law.go.kr law-name routes.
- HiKorea official law/guideline directory and administrative guide pages.
- HiKorea official forms directory and reservation/electronic petition pages.

## 4. Official source hierarchy

1. User-provided 2026.5 manuals validated in this audit.
2. Repository canonical manuals under `docs/source-manuals/2026-05/`, once matching is confirmed.
3. 국가법령정보센터 / law.go.kr statutes, enforcement decrees, and enforcement rules.
4. Official HiKorea and MOJ/Korea Immigration Service administrative guide pages.
5. Paradiso JSON files as implementation targets, not source authority.

## 5. Law source inventory

The core legal source set is recorded in `docs/source-laws/law_sources_2026_05.json` and summarized in `docs/source-laws/LAW_SOURCESET_INVENTORY_2026_05.md`.

Core law sets:

- 출입국관리법 / 시행령 / 시행규칙.
- 국적법 / 시행령 / 시행규칙.
- 난민법 / 시행령 / 시행규칙.
- 재외동포의 출입국과 법적 지위에 관한 법률 / 시행령 / 시행규칙.
- 재한외국인 처우 기본법 / 시행령.

The law.go.kr law-name routes are official retrieval paths. Some routes still require final effective-date parsing before metadata promotion.

## 6. Manual/source guide inventory

The source inventory includes:

- HiKorea `체류자격별 통합 안내 매뉴얼(최신)` notice.
- 사증발급 안내매뉴얼.
- 외국인체류 안내매뉴얼 / 체류민원 안내매뉴얼.
- Public manual revision-history HWP.
- HiKorea `출입국관련 법령지침정보`.
- HiKorea `출입국/체류안내` directory.
- Foreign registration, extension, change of status, workplace change/addition, registration-information/passport change, residence change, electronic civil petition, visit reservation, certificate issuance, and forms pages.

## 7. Address-change/fact-certificate source inventory

HiKorea `출입국관련 법령지침정보` identifies the address-change/fact-certificate manual route. The direct attachment should be archived in a later official attachment archive PR. Do not use this source to patch production data until the exact attachment, checksum, and field-level mappings are recorded.

## 8. Law/manual role separation

Manuals and HiKorea procedure pages are operational/procedure sources for required documents, procedure tabs, application labels, and user-facing civil-petition guidance.

Laws and regulations are legal authority for stay-status basis, reporting duties, fees, penalties, broad eligibility/status structure, statutory limits, and administrative authority.

If law and manual appear to conflict, classify the issue as `LAW_MANUAL_CONFLICT_REVIEW`, cite both sources, and do not patch production data automatically.

## 9. Staged readiness matrix

The readiness matrix is recorded in `docs/audits/readiness_matrix_2026_05.json` and `docs/audits/DATA_PATCH_AND_METADATA_READINESS_MATRIX_2026_05.md`.

Top-level result:

- Source inventory PR: READY_NOW.
- Official attachment archive PR: READY_AFTER_SOURCESET_PR.
- Full manual/law/HiKorea crosswalk: READY_AFTER_SOURCESET_PR.
- Data correction: READY_AFTER_FULL_CROSSWALK.
- `verified=true` and `needsManualReview` changes: READY_AFTER_METADATA_GATE.

## 10. Future data patch gate

A production data patch is allowed only if:

1. The relevant manual or law source is official.
2. Source title/date/URL/page-or-article is recorded.
3. The source directly supports the field being patched.
4. The target JSON field is clearly located.
5. `visa_data.json` and `backend/data/visas.json` parity can be preserved.
6. Conditional requirements are not turned into universal requirements.
7. Sub-code-specific requirements are not merged into top-level records unless clearly labelled.
8. The patch does not remove `needsManualReview` unless the metadata gate is satisfied.
9. The patch does not set `verified=true` unless a dedicated metadata-gate PR proves full source coverage.

## 11. Metadata promotion gate

`verified=true` promotion and `needsManualReview` removal require:

- all relevant procedure/document fields source-confirmed,
- exact source references recorded,
- sub-code ambiguity resolved,
- schema support for verification metadata,
- regression tests passing,
- dedicated metadata-gate PR reviewed.

## 12. Remaining source gaps

Remaining gaps are more precise than broad source gaps:

- `DATE_VERIFICATION_GAP`: law route exists, but final current effective/amended date parse may be pending.
- `ATTACHMENT_DOWNLOAD_GAP`: HiKorea notice confirms attachment, but local archived copy and checksum may be pending.
- `FIELD_CROSSWALK_GAP`: official sources exist, but individual JSON fields are not yet mapped.
- `SCHEMA_GAP`: current JSON may not express conditional or sub-code-specific requirements safely.

## 13. Recommended PR sequence

1. Source-set and readiness documentation PR.
2. Official attachment archive PR.
3. Manual/law/HiKorea full crosswalk PR.
4. Scoped high-risk status crosswalk PRs.
5. Source-confirmed data correction PRs.
6. Metadata gate PR.
7. AI/law-grounding debug mode PR.
8. AI/law-grounding production activation PR.

## 14. Machine-readable source inventory JSON

See `docs/source-laws/law_sources_2026_05.json`.

## 15. Machine-readable readiness matrix JSON

See `docs/audits/readiness_matrix_2026_05.json`.
