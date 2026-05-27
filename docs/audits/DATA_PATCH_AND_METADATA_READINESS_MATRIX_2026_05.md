# DATA PATCH AND METADATA READINESS MATRIX - 2026.5

## Executive status

The source-set documentation PR is ready now, but production data correction is not ready.

The remaining blockers are not broad source-discovery blockers. They are narrower implementation gates:

- DATE_VERIFICATION_GAP
- ATTACHMENT_DOWNLOAD_GAP
- FIELD_CROSSWALK_GAP
- SCHEMA_GAP

## Readiness labels

| Label | Meaning |
| --- | --- |
| READY_NOW | Can be done in the current documentation-only source-set PR. |
| READY_AFTER_SOURCESET_PR | Can start after the source-set PR is merged. |
| READY_AFTER_FULL_CROSSWALK | Requires field-level source mapping first. |
| READY_AFTER_DATA_PATCH | Requires source-confirmed data correction first. |
| READY_AFTER_METADATA_GATE | Requires metadata promotion rules and tests first. |
| BLOCKED_BY_SOURCE_GAP | Official source is not found or cannot be reached. |
| BLOCKED_BY_SCHEMA_GAP | Current schema cannot safely represent the data. |
| BLOCKED_BY_FRONTEND_AUDIT_GAP | UI cannot safely present source/verification state yet. |

## Goal matrix

| Goal | Current status | Next PR | Readiness |
| --- | --- | --- | --- |
| Source inventory PR | Official source routes, HiKorea pages, manual validations, and JSON inventory are ready | Commit documentation/source inventory only | READY_NOW |
| Official attachment archive PR | HiKorea notices confirm HWP/manual attachments, but direct binaries and checksums need archiving | Download/archive official attachments and update manifest | READY_AFTER_SOURCESET_PR |
| Full manual/law/HiKorea crosswalk | Not yet built | Create machine-readable crosswalk by status, procedure, field, URL, page, and article | READY_AFTER_SOURCESET_PR |
| All-status data correction | Not ready | Patch data only after full crosswalk | READY_AFTER_FULL_CROSSWALK |
| F/G/H data correction | Not ready | Category-specific crosswalk and patch PR | READY_AFTER_FULL_CROSSWALK |
| H-2/C-3/D/E/Jeju/scenario-helper correction | Not ready | Scenario-specific crosswalk and patch PR | READY_AFTER_FULL_CROSSWALK |
| verified=true promotion | Not ready | Metadata-gate PR after full source coverage | READY_AFTER_METADATA_GATE |
| needsManualReview removal | Not ready | Metadata-gate PR after ambiguity is resolved | READY_AFTER_METADATA_GATE |
| law-grounding debug/audit mode | Not ready | Implement only after crosswalk exists | READY_AFTER_FULL_CROSSWALK |
| law-grounding production activation | Not ready | Activate only after data patch and metadata gate | READY_AFTER_METADATA_GATE |
| Paradiso AI manual/law grounded answer generation | Not ready | Roll out after grounding/debug/regression pass | READY_AFTER_METADATA_GATE |

## Future data patch gate

Production data patching is allowed only when:

1. the relevant official source is recorded,
2. source title/date/URL/page-or-article is recorded,
3. the source directly supports the field,
4. the target JSON field is identified,
5. `visa_data.json` and `backend/data/visas.json` parity is preserved,
6. conditional requirements are not universalized,
7. sub-code-specific requirements are not merged into top-level records unless labelled,
8. `needsManualReview` is not removed before metadata gate approval,
9. `verified=true` is not set before metadata gate approval.

## Metadata gate

Metadata promotion requires complete field-level source coverage, resolved sub-code ambiguity, schema support, tests, and reviewer approval.
