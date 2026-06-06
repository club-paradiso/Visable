# `verified=true` Gate

`verified=true` is a strict evidence gate. It means Paradiso has reviewed official source evidence for the exact record scope. It does not mean "looks plausible" or "came from a previous data file."

## Required criteria

A record or scoped subrecord may be `verified=true` only when every item below is satisfied.

| Criterion | Requirement |
|---|---|
| Official source exists | The evidence comes from a competent official source, not an unofficial summary. |
| Source hierarchy satisfied | The highest applicable source in `docs/agent-skills/PARADISO_OFFICIAL_SOURCE_AUDIT.md` was used or an explicit reason is recorded. |
| Manual/legal/HiKorea locator exists | The record includes an official URL, law article, notice id, form id, manual file path, manual version, page, section, or table row. |
| Exact quote or precise section exists | A `sourceQuoteKo` value or precise section reference is present for each high-impact claim. |
| Procedure scope is clear | Initial issuance, extension, change, registration, re-entry, reporting, reservation, or office routing is named. |
| Status code and sub-code scope is clear | The evidence states whether it covers parent code, sub-code, scenario, exception, or helper flow. |
| No AI inference | The reviewer did not use AI reasoning to bridge an evidence gap. |
| Reviewer notes present | Notes explain what was verified, what remains out of scope, and any caveats. |
| Last checked date present | `lastChecked` is present in `YYYY-MM-DD` format. |

## Required metadata

Use the schema in `docs/verification/source-evidence.schema.json`. For a `verified=true` record, these fields should be present either on the record or the scoped source-evidence object:

- `sourceStatus: "source_confirmed"`
- `sourceType`
- `sourceName`
- `sourceVersionDate`
- `sourceUrl` or repository source path
- `sourceLocator`
- `sourcePage` or `sourceSection` when applicable
- `sourceQuoteKo` or precise section reference
- `supportLevel: "direct"`
- `reviewerNotes`
- `lastChecked`

## Disqualifiers

Do not set or keep `verified=true` if:

- `needsManualReview=true` is still present for the same scope.
- The best evidence is `source_partial`, `source_contextual`, `official_unavailable`, or `needs_manual_review`.
- The source is an unofficial blog, law-firm summary, agency page, forum, random PDF, AI answer, or OpenAlex record.
- The locator is broad, such as only "HiKorea" or "2026 manual".
- The record merges multiple scenarios and only one scenario is supported.
- The source confirms a related procedure but not the claimed procedure.
- The exact quote or precise section reference cannot be provided for a high-impact claim.

## Review result

When a record fails the gate, the correct result is not a best guess. Keep or set:

- `verified=false`
- `needsManualReview=true` when manual review is needed
- `sourceStatus` matching the actual evidence state
- reviewer notes that name the missing locator, quote, scope, or source
