# Visa Issuance Enrichment Schema

This POC keeps visa issuance guidance outside `visa_data.json` so the main
status records do not absorb long manual text. The layer has three small files:

- `data/visa_issuance_records.json`: user-facing issuance summaries, scenario
  cards, document groups, warnings, and manual page pointers for priority codes.
- `data/procedure_evidence_bindings.json`: field-level source-lens state for
  `visa_issuance` records across canonical parent status codes.
- `data/official_web_overlays.json`: manifest-driven official web overlay
  framework for country/post differences. Confirmed overlay records must come
  only from `visa.go.kr`, `hikorea.go.kr`, `mofa.go.kr`,
  `overseas.mofa.go.kr`, or `law.go.kr`.

## Evidence Levels

- `source_confirmed`: manual page refs or official URLs support applicability
  and the relevant user-facing fields.
- `contextual`: official source context exists, but the field is not yet a
  complete requirement checklist.
- `limited`: official source location exists or context is plausible, but a
  confirmed user checklist would overstate the evidence.
- `unavailable`: no official source binding is available yet.
- `not_applicable`: the procedure should not be shown as an application route.

## Rules

- Official web overlays never overwrite national manual records.
- Timing, fees, reservations, and channel details stay limited unless a specific
  official source binding supports them.
- Every limited or unavailable binding must include a Korean user-facing
  explanation.
- Placeholder labels such as `TBD`, `N/A`, replacement characters, or internal
  enum names must not be visible in the UI.
