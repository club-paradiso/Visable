# Scenario/Help/AI-Grounding Store — E-1 (additive duplication only)

Branch: `data/add-scenario-help-data-store-e1`
Audit date: 2026-05-25
PR: **E-1** (after PR #169)

> **This document is an internal migration-preparation artifact. It is not legal advice. This PR does NOT delete, migrate, or rewrite any record in `visa_data.json`. Current runtime behavior is unchanged.**

## What this PR does

Introduces `data/scenario_help_records.json` containing **duplicated copies** of the **17** scenario/help/AI-grounding candidate records identified in PR #169. Each original record is preserved **byte-for-byte** under a `record` key, with migration metadata as siblings. The file is **not consumed at runtime**; `visa_data.json` remains the live source and is untouched.

**Path choice:** `data/` (alongside `agent_registry`, `designated_medical_institutions`, `jobcode_master`, `source_registry`). Nesting the original under `record` (rather than adding keys into the record) guarantees byte-for-byte preservation and makes parity machine-verifiable.

## Duplicated records (17; overstay-related: 3)

| Code | idx | primary_type | source_grounding | Overstay | Why a scenario/help candidate | UI dep |
|---|---:|---|---|:--:|---|---|
| K-ETA | 0 | faq | non_manual_operational | – | Electronic travel-authorization guide (not a 체류자격 code) | faq-card |
| TB-1 | 1 | procedure_helper | non_manual_operational | – | Tuberculosis document-criteria card | scn-card |
| SCN-1 | 2 | scenario | scenario_policy_sensitive | – | Global decision matrix scenario | scn-card |
| SCN-2 | 3 | scenario | scenario_policy_sensitive | – | Practical variable checklist | scn-card |
| SCN-3 | 4 | scenario | scenario_policy_sensitive | – | C-3 status-change scenario | scn-card |
| SCN-4 | 5 | scenario | scenario_policy_sensitive | – | F-1-6 marriage-dissolution timing | scn-card |
| SCN-5 | 6 | scenario | scenario_policy_sensitive | – | F-4/H-2 동포 restriction scenario | scn-card |
| SCN-6 | 7 | risk_warning | scenario_policy_sensitive | **Yes** | Overstay (illegal-stay) risk scenario | scn-card |
| OVS-1 | 8 | risk_warning | scenario_policy_sensitive | **Yes** | Overstay frequent-country list | scn-card |
| NHIS-1 | 9 | insurance_or_utility | non_manual_operational | – | NHIS exemption/reduction utility | nhis-card |
| FAQ-1 | 10 | faq | non_manual_operational | – | FAQ: 외국인등록·체류지 변경 | faq-card |
| FAQ-2 | 11 | faq | non_manual_operational | – | FAQ: 체류기간 연장·자격 변경 | faq-card |
| FAQ-3 | 12 | faq | non_manual_operational | – | FAQ: 재입국허가 | faq-card |
| FAQ-4 | 13 | faq | non_manual_operational | **Yes** | FAQ: 전자팩스·오버스테이·국적 | faq-card |
| VW-1 | 14 | faq | non_manual_operational | – | 무사증·사증면제 explainer | faq-card |
| COM-1 | 15 | procedure_helper | non_manual_operational | – | Common-document tips | faq-card |
| RF-1 | 46 | procedure_helper | non_manual_operational | – | Refugee-application doc helper (G-1 adjacent) | scn-card |

Every record is used by: `index.html` `cat`-based card rendering + in-app search + AI context payload (the 3 overstay records additionally ground the AI golden eval).

## Key statements

- **All 17 records remain in `visa_data.json` unchanged.** This PR only ADDS duplicated copies.
- **Immediate deletion remains unsafe** (per PR #169): `index.html` renders these via `['faq','scn','nhis'].includes(visa.cat)` (+ `CC`/`CL` maps + search + AI payload); `backend/tests/test_paradiso_backend.py` asserts **K-ETA** present + the **`cat`** field via `/api/visas`; **8 overstay** golden questions are grounded by `SCN-6`/`OVS-1`/`FAQ-4`. Deletion is gated behind **E-4** parity tests.

## Runtime impact

**None.** The new file is additive and not loaded by `index.html` or the backend. The read-only resolver (`scripts/resolve_record_store.py`) confirms the union of `visa_data.json` + the new store **equals `visa_data.json`** today (zero behavior change). `/api/visas`, direct/keyword search, and golden questions are unaffected.

## Future migration

- **E-2:** runtime union resolver so AI/search read **both** files; prove AI golden-eval parity (overstay).
- **E-3:** alias-deprecate the 17 records in `visa_data.json` (not deletion); resolver prefers the new store; backend tests read the union.
- **E-4:** remove from `visa_data.json` **only after** E-1…E-3 prove zero UI/search/AI/backend regressions.

## D-content queue (separate, source-grounded)

D-4-2K duplicate/sub-code · F-4/H-2 sub-manual content · K-STAR records · REGION-S / 지역특화형 / 광역형 records.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Duplicate code collision | Validator forbids duplicate codes in the store; each must exist once in `visa_data.json` |
| Stale duplicated content | Validator asserts each nested record deep-equals `visa_data.json` byte-for-byte (re-sync needed if visa_data changes before E-4) |
| UI category rendering dependency | `index.html` still renders from `visa_data.json` (`cat` faq/scn/nhis); unchanged |
| Backend `/api/visas` dependency | Still returns `visa_data.json`-derived records; resolver not wired in |
| Golden AI eval dependency | Overstay questions still grounded by in-`visa_data` records; unchanged |

## Changed files

| File | Change |
|---|---|
| `data/scenario_help_records.json` | new — 17 duplicated records (originals nested byte-for-byte + migration metadata) |
| `scripts/check_scenario_help_records.py` | new — read-only validator |
| `scripts/resolve_record_store.py` | new — read-only union resolver (E-2 preview; not wired into runtime) |
| `docs/data/2026_05_21_SCENARIO_HELP_STORE_E1_REPORT.md` | this report |
| `docs/data/2026_05_21_scenario_help_store_e1_report.json` | machine-readable report |

**No production data changed.** `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, `index.html`, `source_manifest.json` untouched. No records deleted; no legal/admin content rewritten; no `verified=true`; no `needsManualReview` removals.

## Search results (required)

- `rg "overstay|불법체류|SCN|FAQ|NHIS|VW|COM|OVS"`: the 3 overstay records (SCN-6, OVS-1, FAQ-4) plus the helper codes are present in both `visa_data.json` and the new store; backend tests + golden questions reference overstay (unchanged).
- `rg "scenario_help_records|check_scenario_help_records|migrationStatus|duplicated_from_visa_data"`: matches only the new file, its validator, this report, and the resolver — no runtime wiring.

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
