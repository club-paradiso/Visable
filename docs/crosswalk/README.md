# Manual/Law/HiKorea Crosswalk

This directory contains the scaffold for Paradiso's 2026.5 manual/law/HiKorea crosswalk.

The crosswalk exists to connect each Paradiso status, procedure, and user-facing guidance field to the exact official source that supports it.

## Scope

This is a documentation and schema scaffold only.

It must not be used to change production data until field-level source evidence has been filled and reviewed.

## Source hierarchy

1. Validated 2026.5 visa/stay manuals.
2. law.go.kr statutes, enforcement decrees, and enforcement rules.
3. Official HiKorea and MOJ administrative guide pages.
4. Paradiso JSON files as implementation targets only.

## Files

- `MANUAL_LAW_HIKOREA_CROSSWALK_PLAN_2026_05.md` - staged plan and priorities.
- `crosswalk_schema_2026_05.json` - machine-readable schema for future crosswalk records.
- `stay_status_crosswalk_template_2026_05.json` - template for status-level crosswalk entries.
- `procedure_crosswalk_template_2026_05.json` - template for procedure/service-level crosswalk entries.
- `CROSSWALK_DATA_PATCH_RULES_2026_05.md` - rules that must be satisfied before any data patch.

## Non-goals

- No production JSON patch.
- No verification metadata promotion.
- No AI grounding activation.
- No frontend redesign.
