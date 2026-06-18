# Visa Data Authoring Pipeline

> **Status:** introduced in the `refactor/visa-data-authoring-pipeline` work
> (branch `claude/intelligent-hamilton-b1bszg`). This is a **data-architecture
> and editing-workflow** change. It does **not** change any legal content,
> eligibility rule, document requirement, deadline, fee, source reference, or
> visa guidance wording. Runtime output is byte-for-byte identical.

## TL;DR

- **`visa_data.json` (repo root) is now a _generated compatibility artifact_.**
  Do **not** hand-edit it.
- **Humans edit the authoring layer:** `backend/data/visa_authoring/`.
- Run `python3 scripts/visa/build_visa_data.py` to regenerate `visa_data.json`
  and re-sync the backend mirror.
- The build is **provably lossless**: a fresh `extract` → `build` reproduces the
  committed `visa_data.json` byte-for-byte (verified: 980,051 bytes, 2-space
  indent, raw UTF-8, trailing newline).

## Why

`visa_data.json` is a ~980 KB flat JSON array that mixed canonical status data
with legacy compatibility fields, duplicated document data, long FAQ/summary
prose, repeated fee defaults, and audit/migration metadata. Editing it by hand
was error-prone. This pipeline puts a maintainable authoring layer in front of
it while keeping the generated file exactly as the live frontend/backend expect.

## Which files are generated vs human-editable

| File / dir | Role | Edit by hand? |
| --- | --- | --- |
| `visa_data.json` (repo root) | **Generated** compatibility artifact (frontend `fetch`, backend loader) | ❌ No — run the build |
| `backend/data/visas.json` | **Generated** byte mirror of `visa_data.json` (Railway deploy context) | ❌ No — synced by build |
| `backend/data/visa_authoring/statuses/<CODE>.json` | **Human-editable** per-status authoring file | ✅ Yes |
| `backend/data/visa_authoring/common/*.json` | **Human-editable** shared fees / warnings / labels / doc index | ✅ Yes (fees/warnings/labels) |
| `backend/data/visa_authoring/audit/*.json` | **Generated** relocated audit/migration fields + summary cleanup report | ❌ No — generated views |
| `doc_master.json` | Document dictionary (the active doc-ID source of truth) | ⚠️ Out of scope here |

Inside each `statuses/<CODE>.json`:

- **Top-level fields** (`code`, `nameKo`, `nameEn`, `name`, `cat`, `period`,
  `stayPeriodCap`, `activityScope`, `manualDomains`, `aliases`, `searchAliases`,
  `subcodes`, `procedures`, `manualRefs`, `sourceManualStatus`, `reviewStatus`,
  `editorNotes`) are **human-editable**.
- **`_generated`** holds compatibility/legacy fields (`newReq`, `documents_*`,
  `faq`, the verbatim camelCase `subCodes`, removed summaries, etc.). **Do not
  hand-edit.** These are regenerated.
- **`_authoring`** holds the lossless reconstruction metadata (`keyOrder`,
  `keySource`, `procOrder`, `procKeyOrder`, `recordIndex`). **Do not hand-edit.**

## How the round-trip stays lossless

Every status file records the exact original top-level key order
(`_authoring.keyOrder`) and, for each original key, exactly one **source**
(`_authoring.keySource`): `identity`, `subcodes`, `procedures`, `feeRef`,
`warnRef`, `compat`, or `audit:<file>`. `build` walks `keyOrder` and pulls each
key's value from its declared source, then serializes with the exact
`json.dumps(..., ensure_ascii=False, indent=2) + "\n"` formatting. The extract
script **self-checks** this before writing and refuses to write if the
reconstruction is not byte-identical.

## Legacy / compatibility fields

`newReq`, `newReqDocs`, `extReq`, `extReqDocs`, `changeReq`, `changeReqDocs`,
`initialReqDocs`, `extensionReqDocs`, `documents_initial`,
`documents_registration`, `documents_extension`, `faq`, the camelCase
`subCodes`, and per-status `feeInfo` are **compatibility fields** still read by
the live frontend. They are preserved verbatim in `_generated` and regenerated
on build. They will be migrated/derived in later PRs (see "Migration path").

## Audit / migration fields

`_source_notes`, `_searchAliasAudit`, `structuredRequirementsRef`,
`manualRequiredDocAudit`, and `migrationMeta` are **script-only** (no runtime
frontend consumer). They are relocated to `audit/*.json` keyed by code and
re-injected verbatim on build. **Do not manually edit audit files** — they are
generated. `sourceManualStatus` stays editable in the status file;
`audit/source_manual_status.json` is a read-only consolidated view.

## Source-backed claims

Any source-backed procedure / document / fee claim must carry an exact
reference in metadata: `manualRefs` on the procedure and/or
`sourceManualStatus` on the status. **Source references live in metadata, never
buried inside summary prose.** Do not invent legal/immigration content and do
not add document requirements that are not already in the local data/source
files. Do not translate official Korean document names in checklist data.

## How to … (common edits)

### Edit a status
1. Open `backend/data/visa_authoring/statuses/<CODE>.json`.
2. Edit the human-editable top-level fields (e.g. `period`, `searchAliases`,
   `procedures`, `subcodes`, `sourceManualStatus`). Leave `_generated` /
   `_authoring` alone.
3. `python3 scripts/visa/validate_visa_authoring.py`
4. `python3 scripts/visa/build_visa_data.py`
5. `python3 scripts/visa/diff_visa_data.py --git` and review the diff.

### Add a status
1. Create `statuses/<CODE>.json` modeled on an existing file. Provide identity
   fields, `procedures`, `reviewStatus` (default `needs_review`), and an
   `_authoring` block with `recordIndex` (the desired array position),
   `keyOrder`, and a `keySource` mapping every key. Put compatibility fields
   under `_generated.compat`.
2. Validate, build, diff. The diff will report the new code — confirm it is
   intended.

> Tip: the safest way to bootstrap is to add the record to the data once,
> re-run `extract --force`, and let extraction generate the correct
> `_authoring` metadata. Until tooling for greenfield authoring exists, prefer
> editing existing statuses.

### Update subcodes
- Edit the human-editable `subcodes` array (normalized from the legacy
  camelCase `subCodes`). Build re-emits the runtime `subCodes` field from it, so
  **exact-code search for parent codes and subcodes is preserved**. Do not
  flatten subcodes into the parent.

### Update procedure document groups
- Edit `procedures.<key>.requiredDocs`, which is a group object with
  `commonDocs` / `requiredDocs` / `additionalDocs` / `conditionalDocs`. Keep
  official Korean document names intact. Keep the visa-manual vs stay-manual
  procedure scopes strictly separate (사증발급 vs 체류 procedures).

### Update shared fees / warnings
- Edit `common/fees_2026_05.json` (the shared `paradisoDefault` fee block) or
  `common/common_warnings_2026_05.json`. Statuses whose value matched the shared
  default are emitted by reference, so one edit updates all of them. A status
  with a custom value keeps it verbatim under `_generated`.

### Handle `summary` fields
- `summary` is **optional, not mandatory**. A procedure **label is not a
  summary** (use `common/procedure_labels.json` for labels).
- Keep only concise, source-backed, status-specific summaries (these stay in the
  status file with `summaryQuality: source_backed`).
- Do **not** put OCR/manual chunks, generic `[입국 후 …]` / `[입국 전 …]`
  boilerplate, `DATA_MISSING`, or duplicated requirement text in a summary.
- Generated-compatibility summaries may exist temporarily in `_generated`
  (re-injected so the current UI does not blank out). Do not hand-edit them.
- For every `summary` kept in authoring, set `summaryQuality` (one of
  `human_curated`, `source_backed`, `generated_legacy`, `ocr_blob`,
  `template_placeholder`, `none`).

## Validation / build / diff

| Command | Purpose |
| --- | --- |
| `python3 scripts/visa/extract_authoring_from_visa_data.py [--force]` | Regenerate the authoring layer from `visa_data.json` (self-checks losslessness; refuses to clobber without `--force`). |
| `python3 scripts/visa/validate_visa_authoring.py` | Validate the authoring layer (codes, identity, subcodes, banned fields, doc IDs, summary rules, freshness, mirror). |
| `python3 scripts/visa/build_visa_data.py` | Build `visa_data.json` and sync `backend/data/visas.json`. |
| `python3 scripts/visa/build_visa_data.py --check` | Fail if generated output is out of date (CI). |
| `python3 scripts/visa/diff_visa_data.py [--git]` | Conservative diff of regenerated output vs baseline + authoring cleanup report. |

There is no root `package.json`, so these are invoked directly with `python3`
(the repo convention for data scripts). The pipeline is implemented in Python
because Python's serializer is the one verified to reproduce `visa_data.json`
byte-for-byte.

Recommended pre-commit sequence (the equivalent of a `visa:check` script):

```bash
python3 scripts/visa/validate_visa_authoring.py \
  && python3 scripts/visa/build_visa_data.py \
  && python3 scripts/visa/diff_visa_data.py --git
```

## Migration path (future PRs)

1. Make the frontend consume normalized `subcodes` (then drop camelCase
   `subCodes` from generated output).
2. Move FAQ/help copy out of status records into dedicated help data.
3. Derive `documents_*` / `newReq*` legacy fields from `procedures` instead of
   storing them, then remove them from `_generated`.
4. Update renderers to hide low-value generated summaries
   (`summaryHiddenInUi: true`) and show `summary` only when `summaryQuality` is
   `source_backed` or `human_curated`. **Deferred here** to keep runtime output
   byte-identical and avoid blank cards.

## Note on record counts

This branch's live `visa_data.json` has **42 canonical status records**. The 17
scenario/help/FAQ records described in older audits were already migrated out of
the master on 2026-06-08 (see
`data/removed_from_visa_data_scenario_records_20260608.json`). The
`docs/data/2026_05_21_visa_data_domain_classification.json` snapshot and the
`scenario_help_records.json` shadow store predate that migration, so
`check_visa_data_domain_classification.py`, `check_scenario_help_records.py`, and
`check_record_store_union_parity.py` are **pre-existing red** against the current
data. Reconciling those stale snapshots is out of scope for this
data-architecture PR.
