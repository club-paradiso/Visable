# Alias-Deprecate Scenario/Help Records — E-3

Branch: `data/alias-deprecate-scenario-help-records-e3`
Audit date: 2026-05-25
PR: **E-3** (after PR #172)

> **Internal migration artifact. Not legal advice. No records deleted; no legal/admin content rewritten; metadata-only change to 17 records; current runtime behavior preserved.**

## What this PR does

Adds explicit **alias/deprecation metadata** (`migrationMeta`) to the 17 scenario/help records still present in `visa_data.json`, and promotes the union resolver + parity checks as the authoritative migration-safety path. **No records are removed.**

## Alias-deprecated records (17; overstay-related: 3)

`K-ETA`, `TB-1`, `SCN-1`, `SCN-2`, `SCN-3`, `SCN-4`, `SCN-5`, **`SCN-6`**, **`OVS-1`**, `NHIS-1`, `FAQ-1`, `FAQ-2`, `FAQ-3`, **`FAQ-4`**, `VW-1`, `COM-1`, `RF-1`.

Each has a `scenario_help` shadow copy (PR E-1) and is now flagged alias-deprecated. Overstay-related: **SCN-6, OVS-1, FAQ-4**.

## Metadata added

A single namespaced object `migrationMeta` on each of the 17 records:

```json
"migrationMeta": {
  "migrationTrack": "E",
  "migrationStatus": "alias_deprecated_in_visa_data",
  "plannedCanonicalStore": "scenario_help",
  "canonicalShadowStore": "data/scenario_help_records.json",
  "scenarioHelpStoreCode": "<code>",
  "removalFromVisaDataAllowed": false,
  "requiresParityBeforeRemoval": true,
  "aliasDeprecatedAt": "2026-05-21-source-audit",
  "aliasDeprecationReason": "duplicated into scenario/help store; retained for runtime compatibility until E-4"
}
```

**Shape rationale:** a namespaced object guarantees zero collision with consumer field allowlists — `index.html` search/render and the AI payload (`code/name/cat/period/newReq/extReq/faq`), and the backend `_build_visa_data_context_block` (`code/nameKo/name/nameEn/category/cat/summary/period/manualDomains/sourceManualStatus`), all read **specific** fields, never `Object.keys(record)`. So `migrationMeta` cannot leak into UI/search/AI, and it is trivially strippable for parity comparison. No `code`/`name`/`cat`/`title`/legal/`requiredDocuments` value changed; `removalFromVisaDataAllowed` is `false`; `requiresParityBeforeRemoval` is `true`; no `verified=true`; no `needsManualReview` removed.

**Content-drift check:** a HEAD-vs-working diff confirms the 17 records changed **only** by adding `migrationMeta` (0 records with any other drift); the other 41 records are unchanged.

## Union resolver behavior

| Metric | Value |
|---|---|
| visa_data records | 58 |
| scenario_help shadow records | 17 |
| union records | 58 |
| union output behavior-compatible (== visa_data.json) | **true** |
| alias-deprecated records in visa_data | 17 |
| duplicate codes | `['D-4-2K']` (pre-existing, indices 24 & 55) |

**Duplicate handling:** union keyed by `(array_index, code)`; `visa_data` canonical; shadow de-duplicated (not re-added). No new duplicates; **`D-4-2K` is untouched** (separate D-content PR).

## Runtime status

- **Backend runtime: deferred (unwired).** Adding `migrationMeta` is backward-compatible (`/api/visas` consumers read specific fields; K-ETA name + `cat` unchanged). `/api/visas` now returns the 17 records with one extra metadata field — additive and read by no consumer. Resolver-authoritative wiring is gated to E-4.
- **Frontend runtime: deferred (unwired).** `index.html` untouched; no UI/copy/layout/search change.

## Compatibility / parity

- **Overstay golden questions:** stable. SCN-6/OVS-1/FAQ-4 remain in `visa_data.json` (content unchanged), queryable, each once in the union; golden questions unaffected; `check_repo.sh` passes.
- **Direct/keyword search:** unchanged (reads specific fields; `migrationMeta` not among them).
- **AI grounding:** unchanged (payload + context block read specific fields).

## Key statements

- **All 58 records remain in `visa_data.json`**; the 17 are alias-deprecated via metadata only, not removed.
- **Deletion remains unsafe and gated until E-4** (`removalFromVisaDataAllowed=false` on all 17).

## E-4 prerequisites

1. Backend union parity — backend reads the union (or `/api/visas` proven byte/semantically equivalent) with tests.
2. Frontend/search parity — `index.html` reads the union; direct/keyword search identical.
3. AI golden-eval parity — full golden run (incl. overstay) shows no regression.
4. Overstay golden questions stable.
5. `/api/visas` compatibility decision documented (keep union output-equivalent, or version the endpoint).

## Separate D-content queue

D-4-2K duplicate/sub-code · F-4/H-2 sub-manual · K-STAR · REGION-S / 지역특화형 / 광역형 · DOC_DICT labels for `doc_local_recommendation` and `doc_top_tier_degree`.

## Changed files

| File | Change |
|---|---|
| `visa_data.json` | `migrationMeta` added to 17 records (no other change) |
| `backend/data/visas.json` | synced via `scripts/sync_visa_data.py` |
| `data/scenario_help_records.json` | envelope metadata only (`e3_status` + per-record `visaDataAliasDeprecated`); nested `record` copies untouched |
| `scripts/check_scenario_help_records.py` | ignore approved `migrationMeta` in byte-for-byte compare; assert alias metadata + removal gated |
| `scripts/check_record_store_union_parity.py` | assert all 17 codes alias-deprecated with removal gated |
| `scripts/resolve_record_store.py` | report alias-deprecated count in output / `--check` |
| `docs/data/2026_05_21_ALIAS_DEPRECATE_SCENARIO_HELP_E3_REPORT.md` | this report |
| `docs/data/2026_05_21_alias_deprecate_scenario_help_e3_report.json` | machine-readable report |

`doc_master.json`, `index.html`, `source_manifest.json` untouched.

## Search results (required)

- `rg "alias_deprecated_in_visa_data|removalFromVisaDataAllowed|requiresParityBeforeRemoval|plannedCanonicalStore"`: the 17 `migrationMeta` blocks in `visa_data.json`/`backend/data/visas.json`, the shadow store, the validators, and these reports. `removalFromVisaDataAllowed` is `false` everywhere.
- `rg "SCN-6|OVS-1|FAQ-4|overstay"`: the 3 overstay records present (once each) in `visa_data.json` + shadow store; backend tests + golden questions reference overstay (unchanged).
- `rg "D-4-2K"`: present twice in `visa_data.json` (indices 24 & 55) — untouched; not in the scenario/help store.

## Validation results

| Check | Result |
|---|---|
| `python3 -m json.tool` (visa_data, backend visas, scenario_help, classification, report) | ✅ valid |
| `scripts/resolve_record_store.py --check` | ✅ OK (union==58==visa_data; alias-deprecated=17; pre-existing dup `[D-4-2K]`) |
| `scripts/check_record_store_union_parity.py` | ✅ OK (17 shadow de-duplicated 1:1 + alias-deprecated; overstay each once; zero behavior change) |
| `scripts/check_scenario_help_records.py` | ✅ OK (byte-for-byte match ignoring `migrationMeta`; alias metadata asserted; removal gated) |
| `check_visa_data_domain_classification` · `check_doc_master_id_migration` · `check_source_manuals` · `check_source_updates --local-only` · `sync_visa_data --check` · `check_visa_data_text_integrity` · `check_required_documents_coverage` · `validate_coverage_matrix` · `validate_manual_grounding_candidate` | ✅ pass |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ pass (194 backend tests; git diff clean) |

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
