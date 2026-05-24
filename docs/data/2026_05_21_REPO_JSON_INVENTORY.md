# Paradiso JSON / Data Inventory — 2026-05-21 Manual Update Audit

Branch: `data/audit-2026-05-21-manual-update-json`
Audit date: 2026-05-24
Scope: Inventory every Paradiso JSON / data file that could be affected by the user-provided 2026-05-21 immigration manual update, and classify each by its current state of source-date alignment.

> **This document is an internal data inventory. It is not legal advice and is not an official immigration decision.** End-users must confirm any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.

---

## Critical Source-Identity Caveat

The user-attached PDFs `사증발급 안내매뉴얼_260521.pdf` and `체류민원 안내매뉴얼_260521.pdf` were referenced at local macOS paths (`/Users/seonjaekim/Downloads/...`). Those paths do not exist inside this remote Linux execution environment, so a byte-level comparison between the user's 2026-05-21 source files and the repo PDFs at `docs/source-manuals/2026-05/*.pdf` could not be performed.

Independent in-environment checks of the repo PDFs found:

- Cover page label: generic **"2026. 5."** with no day-level revision date.
- PDF internal `CreationDate`: **2026-05-07** for both files.
- Body text contains no date marker later than **2026.2.12.**, and references a pilot project ending **2026년 5월 19일** that one would expect to have been refreshed if the manual were dated 2026-05-21.
- File SHA-256 hashes match the existing `data/source_registry.json` `last_known_hash` values — the repo PDFs have not changed since they were committed.

These facts are **consistent with** the repo PDFs being the older (likely 2026-05-04 source export-on-2026-05-07) version of the "2026.5" manuals, **but this is not proven**. Where this inventory uses the label "generic-2026.5-unverified", that is the deliberate classification: the JSON file marks itself with the generic version "2026.5" but no date-level evidence is available in this run to advance the marker to "2026-05-21".

---

## Classification Scheme

For each file:

- **Source-sensitivity**: whether the file's content depends on the substantive content of an immigration manual or notice (vs. infrastructure / coverage tracking / source-monitoring).
- **Date alignment**:
  - `2026-05-21-confirmed` — file content has been verified to reflect the 2026-05-21 manual via either byte-level comparison or page-level evidence.
  - `generic-2026.5-unverified` — file content claims "2026.5" but no day-level verification is available.
  - `pre-2026-05-stale` — file content explicitly cites an older manual (`2026.3`, `2026.4`, `0504`, `2026-05-04`).
  - `mixed` — file mixes confirmed and unverified provenance.
  - `not-manual-dependent` — file content does not depend on the immigration manual.
  - `infrastructure` — file is a registry, manifest, or coverage tracker.
- **Inspection depth**: `deep` (full record-level inspection) or `shallow` (sampling / metadata only).
- **Changes-needed-in-this-PR**: `yes` / `no` / `documented-for-follow-up`.

No file in this PR was confirmed `2026-05-21-confirmed`.

---

## File-by-file Inventory

### Canonical immigration data

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `visa_data.json` | Canonical 58-record status/helper display data | Yes | Deep | `generic-2026.5-unverified` | Documented-for-follow-up | All visa records have `sourceManualStatus.visaManualVersion = "2026.5"` and `sourceManualStatus.stayManualVersion = "2026.5"`. All visa records have `verified = false` and `needsManualReview = true`. F-4 and H-2 dataDate is `2026-02-12`. K-Trainee D-4-2K dataDate is `2025-10-29`. F-6-1 income note still labeled `2026.3` per prior PR #145. No record claims 2026-05-21. See `2026_05_21_VISA_DATA_FULL_AUDIT.md` for the record-by-record audit. |
| `backend/data/visas.json` | Backend mirror of `visa_data.json` produced by `scripts/sync_visa_data.py` | Yes | Deep | mirrors source | No (no edit, no sync needed if root unchanged) | Same shape (58 records). Line count identical to root (9443 lines). |
| `doc_master.json` | Document-ID display-label master used by visa_data + UI | Yes | Deep | `generic-2026.5-unverified` (no explicit version) | Documented-for-follow-up | 79 entries; 66 are referenced by `visa_data.json`; 13 are unused, of which 12 are corrupted entries with literal Korean phrases as `id` (e.g. `"수수료"`, `"여권"`, `"표준규격사진 1매"`). 1 entry (`doc_arc_fee`) is a normal `doc_*`-prefixed ID that is currently unused. See `2026_05_21_MANUAL_JSON_CROSSWALK.md` for cleanup queue. |

### Manuals and source identity

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | 사증발급 안내매뉴얼 | Yes (is the source) | Deep | Unresolved between 2026-05-04 and 2026-05-21 | No (PDF not replaced) | 484 pages, 12.6 MB, SHA-256 `5a191aed…84063`. PDF internal CreationDate 2026-05-07. Cover label `2026. 5.` |
| `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | 외국인체류 안내매뉴얼 | Yes (is the source) | Deep | Unresolved between 2026-05-04 and 2026-05-21 | No (PDF not replaced) | 774 pages, 14.1 MB, SHA-256 `0492683…b3ba`. PDF internal CreationDate 2026-05-07. Cover label `2026. 5.` |
| `docs/source-manuals/source_manifest.json` | Manual manifest | Yes | Deep | `generic-2026.5-unverified` (now annotated) | Yes | Added date-level metadata fields (`source_date: "unresolved"`, `source_label`, `supersedes`, `file_sha256`, `file_size_bytes`, `pdf_internal_creation_date`, `verification_status: "user_attached_pdf_not_accessible_in_environment"`, `verification_note`) and an `audit_history` array. Existing `version: "2026.5"` preserved. `source_date` deliberately set to `"unresolved"` because byte-level comparison against the user-attached 2026-05-21 file could not be performed. |
| `docs/source-manuals/SOURCE_MANUALS.md` | Manual-directory README | Yes | Deep | `generic-2026.5-unverified` | No (no edit) | Already documents 2026.5 generically; no day-level claim. Not contradicted by this PR. |
| `data/source_registry.json` | Source allow-list for monitoring | Yes (registry) | Deep | `generic-2026.5-unverified` for the two PDF entries | No | Both PDF entries already carry version `"2026.5"` and correct SHA-256 hashes that match this run. Other entries are `status=not_configured` law/notice placeholders. |

### Manual grounding fixtures

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` | Active page-grounded extractions read by /api/ask | Yes | Deep | `generic-2026.5-unverified`; sub-entries verified at page-range level inside the same 2026.5 PDF | No | Schema 1.2. `source_date: "2026.5"`. Three groundings: `d2_extension_2026_05` (D-2 ext, pp.43-44, verified_locally, high confidence), `d4_extension_2026_05` (D-4 ext for D-4-1/D-4-7 only, pp.90-91), `e7_extension_2026_05` (E-7 ext general, p.226). Page references are absolute PDF pages inside the committed 2026.5 file; they remain valid as long as that file is the canonical source. |
| `backend/data/manual_grounding/candidates/README.md` | Candidate grounding directory README | Yes | Shallow | n/a | No | Documentation only. |
| `backend/data/manual_grounding/candidates/f6_divorce_status_change/*` | Draft F-6 divorce status change candidate | Yes | Shallow | draft | No | Draft-only, not promoted to active. Does not address F-6 income figures. |

### Audit / coverage / matrix artifacts

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `docs/data/JSON_MANUAL_LAW_AUDIT_2026_05.md` | Prior PR #140 audit report | Yes | Deep | `generic-2026.5-unverified` audit | No (not retroactively edited) | Documents the JSON cleanup + matrix construction work from the merged audit PR #140. Already correctly states 2026.5 generically. |
| `docs/data/json_manual_law_audit_2026_05_matrix.json` | Prior PR #140 audit matrix | Yes | Deep | `generic-2026.5-unverified` | No | 44 rows mapping codes to manual sections + approximate page ranges. Approximate page ranges were generated without page-level extraction in PR #140 and should be considered indicative, not authoritative. This PR's `2026_05_21_manual_json_crosswalk.json` carries fresh page anchors extracted with `pdftotext` in this run. |
| `docs/data/2026_05_HIGH_RISK_GAP_PATCH_AUDIT.md` | Prior PR #145 audit-only blocker report | Yes | Deep | n/a (audit-only) | No | Reports that PR #145 was blocked by lack of PDF extraction tooling. The same five high-risk targets (D-4-2K duplicates, Top-Tier, 광역형, 청소년취업정주, F-6 income) are still outstanding. |
| `docs/data/2026_05_high_risk_gap_patch_matrix.json` | Prior PR #145 audit matrix | Yes | Deep | n/a (audit-only) | No | Mirrors the audit-only blocker state. |
| `docs/data/MANUAL_BASED_DATA_MODEL.md` | Manual-to-data-model notes | Yes | Shallow | n/a | No | Reference notes; no data values. |
| `docs/data/MANUAL_REQUIRED_DOC_AUDIT_2026_05.md` | Manual required-doc audit notes | Yes | Shallow | `generic-2026.5-unverified` | No | Reference notes only. |
| `docs/data/MANUAL_SOURCE_AUDIT_QUEUE.md` | Audit queue | Yes | Shallow | n/a | No | Reference notes only. |
| `docs/data/HIKOREA_SOURCE_*` (4 files) | HiKorea source monitor schema / catalog notes from PR #144 | Yes (source-monitoring) | Shallow | not-manual-dependent | No | Infrastructure for future source monitoring. Not directly affected by manual revision dates. |
| `backend/data/eval/paradiso_coverage_matrix.json` | Coverage/eval control plane | Yes | Deep | `generic-2026.5-unverified` (references active grounding fixture) | No | Read-only metadata; does not call /api/ask. Pointer to `stay_manual_grounding_2026_05.json` remains correct. |
| `backend/data/eval/paradiso_ai_golden_questions.json` | AI golden eval questions | Yes (eval) | Shallow | mixed | No | Eval test cases; not user-facing. Not directly affected by manual revision dates. |

### Adjacent reference data (not manual-controlled)

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `data/jobcode_master.json` | KSIC/SOC-style job code master, referenced by E-7 etc. | Manual-adjacent | Shallow | not-manual-dependent | No | Sourced from a separate notice. Sample search for "0504" returns false positives (phone numbers). |
| `data/agent_registry_2026-04-30.json` | 민원대행 등록기관 registry, dated 2026-04-30 | Independent | Shallow | not-manual-dependent | No | Standalone registry dated by file name. Sample search for "0504" returns false positives (phone numbers and internal `agent-0504` IDs). |
| `data/designated_medical_institutions_2026_04_30.json` | Designated medical institutions, dated 2026-04-30 | Independent | Shallow | not-manual-dependent | No | Standalone registry. Sample search for "0504" returns false positives (`med-0504` internal IDs). |
| `data/sources/hikorea_source_catalog.json` | HiKorea source catalog from PR #144 | Manual-adjacent | Shallow | not-manual-dependent | No | Source registry, not visa data. |
| `data/sources/immigration_notice_sources.json` | Immigration notice source registry | Manual-adjacent | Shallow | not-manual-dependent | No | Source registry, not visa data. |
| `data/sources/medical-institutions/` | Medical institution sub-sources | Independent | Shallow | not-manual-dependent | No | Reference data. |
| `data/sources/민원대행_등록기관_2026-04-30.pdf` and `.xlsx` | 민원대행 source files | Independent | Shallow | not-manual-dependent | No | Source files for the agent registry above. Internal date 2026-04-30. |

### UI

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `index.html` | Main UI | Renders visa_data.json | Shallow | inherits visa_data.json | No | Localized `landingHints` for 18 languages mention `K-Trainee(D-4-2K)`, `K-ETA`, `E-7-4`, `F-6`, `F-3`, `TB-1`, `RF-1`, `SCN-6`, `D-10`, etc. None of these landing-hint string changes are required by this PR. |
| `ai.html` | AI page | Includes K-STAR explicit local-record routing | Shallow | inherits visa_data.json | No | Routes K-STAR explicitly because it is a local structured record. No structural change required by this PR. |
| `prototype/index.html`, `prototype/ai.html` | Prototype copies | Same shape | Shallow | inherits prototype | No | Not the production UI. |

### Backend code (not data)

| Path | Purpose | Source-sensitive | Inspection depth | Date alignment | Changes in this PR | Notes |
|---|---|---:|---|---|---|---|
| `scripts/sync_visa_data.py` | Sync canonical `visa_data.json` → `backend/data/visas.json` | Infrastructure | Shallow | infrastructure | No | Will be re-run if `visa_data.json` is edited. This PR makes no substantive `visa_data.json` edits, so no sync is required. |
| `scripts/check_source_manuals.py` | Validates source manuals registration | Infrastructure | Shallow | infrastructure | No | Passes against the updated manifest. |
| `scripts/check_source_updates.py` | Local source-monitor report | Infrastructure | Shallow | infrastructure | No | Reports both PDFs unchanged. |
| `scripts/check_visa_data_text_integrity.py` | Visa data text integrity | Infrastructure | Shallow | infrastructure | No | n/a unless visa_data.json edited. |
| `scripts/check_required_documents_coverage.py` | Required docs coverage check | Infrastructure | Shallow | infrastructure | No | n/a unless visa_data.json edited. |
| `scripts/validate_coverage_matrix.py` | Coverage matrix validator | Infrastructure | Shallow | infrastructure | No | n/a unless eval data edited. |
| `scripts/validate_manual_grounding_candidate.py` | Candidate validator | Infrastructure | Shallow | infrastructure | No | n/a unless candidate edited. |
| `scripts/check_repo.sh` | Repo bootstrap and check | Infrastructure | Shallow | infrastructure | No | Aggregator. |
| Other backend code | Service code | Infrastructure | Shallow | infrastructure | No | Not changed by data audit. |

---

## Inventory Summary

- Files inspected deeply: 12.
- Files inspected shallowly: 16.
- Files changed by this PR: 1 substantive (`docs/source-manuals/source_manifest.json`), plus this audit's documentation artifacts under `docs/data/`.
- Files needing follow-up: see `2026_05_21_MANUAL_JSON_CROSSWALK.md` and `2026_05_21_VISA_DATA_FULL_AUDIT.md`.
- No file in this PR is classifiable as `2026-05-21-confirmed`. All immigration-data files remain `generic-2026.5-unverified` until a reviewer can directly compare against the user's `_260521.pdf` source files or extract a dated revision marker from inside the manual body.

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this inventory, the audited JSON files, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea (`hikorea.go.kr`), 1345 종합민원안내, or a qualified Korean immigration professional. Where this audit could not verify a specific page, statute, or source-date claim, the underlying record is left flagged with `needsManualReview = true` and must be treated as unverified until a human reviewer confirms the source.
