# doc_master ID Migration with UI Compatibility (PR D batch 2)

Branch: `data/migrate-doc-master-ids-with-ui-compat`
Audit date: 2026-05-25
PR: **D batch 2** (after PR #160)

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

This is **PR D batch 2**. **PR #160** fixed only the G-1 stale page anchor and **deferred** the doc_master ID migration because the 12 corrupted Korean-string IDs are tied to `index.html` `DOC_DICT`/UI rendering. This PR performs the **coordinated migration** of those IDs to stable machine-readable IDs **with `index.html` rendering compatibility**, so user-facing Korean labels are byte-identical.

---

## Compressed archive verification

**Result: `compressed archive not provided`.**

The execution environment was scanned for `*.zip` / `*.tar` / `*.tar.gz` / `*.tgz` / `*.7z` manual-source archives and for `*260521*` / `*manual*source*` files. The only archive present was an unrelated chromedriver zip; no 2026-05-21 manual-source archive existed. Migration proceeded using committed repo files only. The canonical PDFs and `source_manifest.json` were **not** touched (PR #155 scope, closed).

| Field | Value |
|---|---|
| Temporary extraction path | _n/a (no archive)_ |
| Archive file list | _n/a_ |
| SHA-256 comparison | _n/a_ |
| Final decision | Proceed with committed repo files only |

---

## ID migration table (12 IDs)

| Old ID (corrupted Korean string) | New stable ID | Korean label (preserved) |
|---|---|---|
| 개별 사안별 증빙서류(매뉴얼 해당 항목 및 관할기관 안내 기준) | `doc_case_specific_evidence` | unchanged |
| 변경 사유 입증서류(활동계획서·초청서·고용계약서 등 해당 자격별) | `doc_change_reason_evidence` | unchanged |
| 사증발급신청서(별지 제17호 서식) | `doc_visa_application_form` | unchanged |
| 사진 1매(해당 시) | `doc_photo_one_optional` | unchanged |
| 수수료 | `doc_fee_generic` | unchanged |
| 여권 | `doc_passport_generic` | unchanged |
| 여권 및 외국인등록증 | `doc_passport_and_arc` | unchanged |
| 체류자격별 개별 첨부서류(매뉴얼 해당 자격 항목 참조) | `doc_status_specific_attachments` | unchanged |
| 체류지 입증서류 | `doc_residence_proof_generic` | unchanged |
| 통합신청서 | `doc_unified_application_form` | unchanged |
| 통합신청서(체류자격변경허가 신청 포함) | `doc_unified_application_form_change` | unchanged |
| 표준규격사진 1매 | `doc_standard_photo_one` | unchanged |

No collisions with existing IDs; no duplicate new IDs. Each corrupted entry was renamed to its **own** new ID — **not merged** into a similar existing `doc_*` entry (e.g. `여권` was *not* merged into `doc_passport`), because the existing entries' display labels differ and merging would change the rendered text.

---

## Changed files

| File | Change |
|---|---|
| `doc_master.json` | 12 `id` renames; `ko_name` / `en_name` / `description` preserved verbatim |
| `visa_data.json` | 39 ID-reference array entries repointed old → new |
| `backend/data/visas.json` | regenerated via `scripts/sync_visa_data.py` **only** |
| `index.html` | added 12 `DOC_DICT` keys → verbatim prior Korean labels; one trailing comma added to the previous last entry (`doc_cvi`) |
| `scripts/check_doc_master_id_migration.py` | new read-only validator (no dependencies) |
| `docs/data/2026_05_21_DOC_MASTER_ID_MIGRATION_REPORT.md` | this report |
| `docs/data/2026_05_21_doc_master_id_migration_report.json` | machine-readable report |

`docs/source-manuals/source_manifest.json` and the canonical PDFs were **not** changed.

---

## visa_data.json records updated (39 references across 15 records)

| Code | Refs | Fields |
|---|---:|---|
| COM-1 | 4 | initialReqDocs ×4 |
| D-10 | 1 | requiredDocs |
| D-2 | 1 | requiredDocs |
| D-4 | 1 | requiredDocs |
| D-4-2K | 2 | requiredDocs ×2 — **ID-reference rename only; not a duplicate/sub-code resolution (PR D-3)** |
| E-8 | 1 | requiredDocs |
| FAQ-1 | 5 | initialReqDocs ×5 |
| FAQ-2 | 5 | changeReqDocs ×5 |
| FAQ-4 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |
| K-STAR | 1 | requiredDocs — **ID-reference rename only; not a K-STAR content patch (PR D-3)** |
| NHIS-1 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |
| SCN-1 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |
| SCN-3 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |
| SCN-6 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |
| VW-1 | 3 | initialReqDocs, extensionReqDocs, changeReqDocs |

Only the **ID-reference arrays** were repointed. The **89** `documents_*[].name` display-label objects (per file) and free-text `summary`/`name` prose containing the same Korean substrings were left untouched — they are user-facing labels rendered directly, not doc_master ID references.

---

## index.html DOC_DICT compatibility

12 `DOC_DICT` keys were added, each mapping the new ID to the **verbatim prior Korean label** (the exact string the renderer's raw-string fallback showed before migration). The resolver at `index.html:11537` (`DOC_DICT[key] || (key.startsWith('doc_') ? '문서요건(...)' : key)`) now returns the same Korean text for the new `doc_*` IDs that it previously returned for the raw Korean-string IDs, so on-screen output is **byte-identical**.

No changes to layout, styling, UX, copy, search behavior, Paradiso AI behavior, or unrelated constants.

---

## Residual old-string occurrences (all are labels, by design)

| Location | Count | Nature |
|---|---:|---|
| visa_data.json / backend — **bare ID-array reference** | **0** | migration complete |
| doc_master.json `ko_name` | 12 | preserved Korean labels |
| index.html `DOC_DICT` values | 12 | preserved Korean labels |
| visa_data.json / backend `documents_*[].name` + `summary` prose | preserved | user-facing display text |

**Zero** corrupted IDs remain as active doc-reference array elements (verified in both `visa_data.json` and `backend/data/visas.json`). All remaining occurrences are label/display text that **must** be preserved.

---

## Confirmations

- ✅ Korean user-facing labels preserved (rendering byte-identical).
- ✅ No required-document meaning changed.
- ✅ No requiredDocuments added or removed.
- ✅ No eligibility, fees, income thresholds, stay periods, procedures, or legal/admin guidance text rewritten.
- ✅ No `verified=true` promotions.
- ✅ No `needsManualReview` removals.
- ✅ No records deleted.
- ✅ No visual/layout/UX/search/AI changes (DOC_DICT key additions only).
- ✅ `backend/data/visas.json` updated only through `scripts/sync_visa_data.py`.
- ✅ `source_manifest.json` and canonical PDFs unchanged.

---

## Validation results

| Check | Result |
|---|---|
| `python3 -m json.tool` (visa_data, backend visas, doc_master, this report, 3 PR #157 JSON artifacts) | ✅ valid |
| `scripts/sync_visa_data.py --check` | ✅ OK |
| `scripts/check_source_manuals.py` | ✅ OK |
| `scripts/check_source_updates.py --local-only` | ✅ OK |
| `scripts/check_visa_data_text_integrity.py` | ✅ PASS |
| `scripts/check_required_documents_coverage.py` | ✅ no regressions |
| `scripts/validate_coverage_matrix.py` | ✅ OK |
| `scripts/validate_manual_grounding_candidate.py` | ✅ OK |
| `scripts/check_doc_master_id_migration.py` (new) | ✅ OK (79 ids; all ID-array refs resolve + have DOC_DICT labels; no Korean-string ids remain) |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ pass (194 backend tests; git diff clean) |
| repo-search for old IDs as active refs | 0 |

---

## PR D-3 queue (substantive content, page-cited)

1. **F-6** income note / content (stay §33 pp.474–497, visa §34 pp.324–335).
2. **D-4-2K** duplicate/sub-code resolution (array indices 24 + 55).
3. **F-4 / H-2** 외국국적동포 Feb-2026 sub-manual content (stay §36 pp.518–584).
4. **K-STAR** substantive content (visa §40 pp.456–484 / stay §41 pp.749–777).
5. **REGION-S / 지역특화형** (stay §37 pp.585–654) / **광역형** (stay §40 pp.686–748).
6. **F-2 / F-3 / F-5 / H-1** page sub-range anchors (idiosyncratic; need page-cited re-derivation).
7. Optional: near-duplicate dedupe of migrated IDs vs existing `doc_*` entries; add `DOC_DICT` labels for pre-existing label-less IDs (`doc_top_tier_degree`, `doc_local_recommendation`).

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
