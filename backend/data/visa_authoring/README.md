# `visa_authoring/` — human-editable visa/status source

This directory is the **human-editable source of truth** for Korean
체류자격 (status-of-stay) data. The runtime file `visa_data.json` (repo root) and
its mirror `backend/data/visas.json` are **generated** from here.

Full guide: [`docs/visa-data-authoring-pipeline.md`](../../../docs/visa-data-authoring-pipeline.md).

## Layout

```text
visa_authoring/
  statuses/<CODE>.json     # one human-editable file per status (B-1, D-2, E-7, ...)
  common/
    doc_catalog.json         # index into doc_master.json (the active doc dictionary)
    fees_2026_05.json        # shared paradisoDefault fee block
    common_warnings_2026_05.json  # shared warnings block
    procedure_labels.json    # UI labels for procedure keys (NOT summaries, NOT legal content)
  audit/
    source_manual_status.json        # consolidated read-only view (generated)
    manual_required_doc_audit.json   # relocated audit field, re-injected by build (generated)
    search_alias_audit.json          # relocated _searchAliasAudit (generated)
    structured_requirements_refs.json# relocated structuredRequirementsRef (generated)
    source_notes.json                # relocated _source_notes (generated)
    migration_meta.json              # relocated migrationMeta (generated; empty on this branch)
    summary_cleanup_audit.json       # per-summary classification report (generated)
```

## Edit rules (short version)

- ✅ Edit top-level fields in `statuses/<CODE>.json` and the editable
  `common/` files (`fees_*`, `common_warnings_*`, `procedure_labels`).
- ❌ Do **not** edit `_generated` or `_authoring` blocks inside status files.
- ❌ Do **not** edit anything in `audit/` (generated views) or `doc_catalog.json`.
- ❌ Do **not** hand-edit `visa_data.json` / `backend/data/visas.json`.
- Keep official Korean document names intact; never invent legal content.
- After editing: `validate` → `build` → `diff` (see the guide).

## Regenerate this directory

```bash
python3 scripts/visa/extract_authoring_from_visa_data.py --force
```

(`--force` is required to overwrite existing files. Extraction self-checks that
the authoring layer rebuilds `visa_data.json` byte-for-byte before writing.)
