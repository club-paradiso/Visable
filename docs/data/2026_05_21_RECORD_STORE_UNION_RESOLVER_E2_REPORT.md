# Record-Store Union Resolver — E-2 (resolver + parity tests; runtime not wired)

Branch: `data/add-record-store-union-resolver-e2`
Audit date: 2026-05-25
PR: **E-2** (after PR #170)

> **Internal migration artifact. Not legal advice. No records deleted, migrated, or rewritten; no legal/admin content changed; current runtime behavior is preserved.**

## What this PR does

Introduces a **deterministic, importable, read-only union resolver** for `visa_data.json` + `data/scenario_help_records.json`, plus **parity tests** that gate any future runtime wiring. It does **not** change `/api/visas`, search, AI grounding, or the frontend.

## Backend / frontend wiring decision

- **Backend runtime wired: NO.**
- **Frontend runtime wired: NO.**

The 17 scenario/help records are byte-for-byte **shadow duplicates** of records still in `visa_data.json`, so the union **already equals `visa_data.json`**. Wiring `/api/visas` or `index.html` to the resolver would produce **zero functional change** while introducing behavior-uncertainty risk. Per the task's own guidance ("if wiring would create behavior uncertainty, do not wire it — add resolver/tests and document"), E-2 ships the resolver + parity tests and **defers runtime wiring to E-3** (after alias-deprecation metadata makes the shadow authoritative).

## Resolver design (`scripts/resolve_record_store.py`)

- `load_visa_data()` — canonical live records.
- `load_scenario_help_shadow()` — E-1 shadow envelopes.
- `union_view(prefer="visa_data")` — deterministic, de-duplicated union keyed by `(array_index, code)`. `visa_data` is canonical; shadow duplicates are **not re-added**, so the union is exactly `visa_data.json`. `prefer` is a seam for the future E-3/E-4 resolver.
- `shadow_index()` — shadow **metadata** only (no record content override).
- `parity_report()` / `--check` — asserts the E-2 invariants.

## Parity result

| Metric | Value |
|---|---|
| visa_data records | 58 |
| scenario_help shadow records | 17 |
| union records | 58 |
| union == visa_data.json | **true** |
| duplicate codes in union | `['D-4-2K']` |
| duplicate codes in visa_data.json | `['D-4-2K']` |
| union output == `/api/visas` behavior | **true** |

**Duplicate handling:** union keyed by `(array_index, code)`; `visa_data` canonical; shadow duplicates de-duplicated (not re-added). The **only** duplicate code is the **pre-existing `D-4-2K`** (`visa_data` indices 24 & 55), deferred to the D-content track — the union introduces **no new duplicates**. The 17 shadow codes (incl. overstay SCN-6/OVS-1/FAQ-4) each appear exactly once.

## Compatibility status

- **Overstay golden questions:** unchanged. SCN-6/OVS-1/FAQ-4 appear once in the union; questions still grounded by the in-`visa_data` records (`/api/visas` unchanged). `check_repo.sh` passes.
- **Direct / keyword search:** unchanged. `/api/visas` and `index.html` still read `visa_data.json`-derived records; resolver not wired into search. Direct code-lookup parity verified (every `visa_data` code resolves identically via the union).
- **AI grounding:** unchanged. AI context block/payload still use `visa_data.json` records; resolver is read-only and unused at runtime.

## Key statements

- **All 58 records remain in `visa_data.json` unchanged** (incl. the 17 shadowed ones).
- **Immediate deletion remains unsafe and gated** — requires E-3 (alias-deprecation) + E-4 parity across backend, frontend, search, and AI golden eval.

## Next steps

- **E-3:** add explicit deprecation/alias metadata to the 17 scenario/helper records in `visa_data.json` (no removal); make the union resolver authoritative for AI/search (wire backend/frontend behind parity); update backend tests to read the union while keeping `/api/visas` output-compatible.
- **E-4:** remove the 17 records from `visa_data.json` **only after** parity tests pass across backend, frontend, search, and AI golden eval.

## Separate D-content queue

D-4-2K duplicate/sub-code · F-4/H-2 sub-manual · K-STAR · REGION-S / 지역특화형 / 광역형 · DOC_DICT labels for `doc_local_recommendation` and `doc_top_tier_degree`.

## Changed files

| File | Change |
|---|---|
| `scripts/resolve_record_store.py` | strengthened — importable deterministic union API + `--check` |
| `scripts/check_record_store_union_parity.py` | new — read-only E-2 parity tests |
| `docs/data/2026_05_21_RECORD_STORE_UNION_RESOLVER_E2_REPORT.md` | this report |
| `docs/data/2026_05_21_record_store_union_resolver_e2_report.json` | machine-readable report |

**No production data changed** — `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, `index.html`, `data/scenario_help_records.json`, `source_manifest.json` untouched. No records deleted; no legal/admin content rewritten; no `verified=true`; no `needsManualReview` removals.

## Search results (required)

- `rg "scenario_help_records|resolve_record_store|removalFromVisaDataAllowed|duplicated_from_visa_data"`: matches the E-1 store, the resolver, the parity validator, and these reports — **no runtime wiring** in `backend/` or `index.html`.
- `rg "overstay|SCN-6|OVS-1|FAQ-4"`: the 3 overstay records present once each in both `visa_data.json` and the shadow store; backend tests + golden questions reference overstay (unchanged).
- `rg "/api/visas|visa_data.json"` in `backend`/`index.html`: backend `_load_visas()` and `index.html` `fetch('/api/visas')`→fallback `./visa_data.json` are **unchanged**.

## Validation results

| Check | Result |
|---|---|
| `python3 -m json.tool` (visa_data, backend visas, scenario_help, classification, report) | ✅ valid |
| `scripts/resolve_record_store.py --check` | ✅ OK (union==58==visa_data; no new dup codes; pre-existing dup=`[D-4-2K]`) |
| `scripts/check_record_store_union_parity.py` (new) | ✅ OK (17 shadow de-duplicated 1:1; overstay each once; direct-lookup parity; zero behavior change) |
| `check_scenario_help_records` · `check_visa_data_domain_classification` · `check_doc_master_id_migration` · `check_source_manuals` · `check_source_updates --local-only` · `sync_visa_data --check` · `check_visa_data_text_integrity` · `check_required_documents_coverage` · `validate_coverage_matrix` · `validate_manual_grounding_candidate` | ✅ pass |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | ✅ pass (194 backend tests; git diff clean) |

## Legal Disclaimer

Paradiso is reference software. Nothing in this report or the repository's data files constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
