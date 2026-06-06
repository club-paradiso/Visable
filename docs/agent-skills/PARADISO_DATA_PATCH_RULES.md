# Paradiso Visa and Status Data Patch Rules

## Purpose

Use these rules for future PRs that modify visa/status data, document mappings, scenario helpers, manual grounding, or source evidence metadata. They protect Paradiso from turning partial source matches into broad official claims.

These rules do not authorize production data changes by themselves. A data patch PR must state its scope and list every production file it edits.

## `verified=true` promotion criteria

A production record or scoped subrecord may be promoted to `verified=true` only when all criteria are met:

- An official source directly supports the exact claim and exact scope.
- The source hierarchy in `PARADISO_OFFICIAL_SOURCE_AUDIT.md` is satisfied.
- The record carries a manual, legal, or HiKorea locator.
- The locator includes manual version/date or page, law article, notice id, official URL, form id, or section heading as applicable.
- An exact quote or precise section reference is present.
- The procedure scope is clear: initial issuance, extension, change of status, registration, re-entry, reporting duty, reservation, or office routing.
- Status code and sub-code scope are clear.
- Scenario, exception, nationality, employer, family, school, helper, FAQ, and overstay scope is not flattened into a parent record.
- No AI inference is required to bridge from source to claim.
- Reviewer notes explain what was verified and what was left unverified.
- `lastChecked` is present in `YYYY-MM-DD` format.
- `needsManualReview` is removed only when the same reviewer explicitly confirms it is no longer needed for that exact scope.

## `needsManualReview` preservation rules

Preserve `needsManualReview=true` when:

- Any required document, eligibility rule, fee, deadline, or procedure step lacks direct official support.
- Source evidence covers only a parent status while sub-code or scenario records remain uncertain.
- A field was generated from a manual crosswalk, matrix, helper script, or candidate record but not human-reviewed.
- The official locator is a broad section range and not an exact page, section, article, or row.
- Source text conflicts or appears stale.
- The patch updates source metadata only.

Do not remove `needsManualReview` as a cleanup convenience. Removal is a separate reviewer decision.

## No broad inference

Do not infer:

- Requirements for one status from a similar status.
- Extension requirements from initial issuance requirements.
- Registration requirements from extension requirements.
- Sub-code requirements from parent status sections.
- Legal duties from UI workflow labels.
- Fees from old tables, cached pages, or examples unless the current official source states them.

If the source is close but not exact, mark it `source_partial` or `source_contextual`.

## No scenario flattening

Scenario-specific material must stay scoped. Do not flatten into parent fields when the claim belongs to:

- A sub-code.
- A helper flow.
- A family, employer, school, nationality, income, residence, or program scenario.
- A re-entry, overstay, reporting, cancellation, invitation, or exception pathway.
- A FAQ answer whose conditions are narrower than the parent status.

When the source covers only one scenario, either patch the scenario record or leave the parent unverified.

## No deletion without explicit instruction

Do not delete scenario, helper, FAQ, overstay, review, migration, or source-grounding records unless the user explicitly instructs deletion and the PR explains:

- The exact records removed.
- The replacement source or reason.
- Why no user-facing guidance was silently lost.
- Which exact-code searches were run to confirm no orphan references remain.

## Manual version and page locator requirements

Manual-backed claims must include:

- Manual title.
- Manual version or source date.
- Repository file path or official URL.
- Printed page, PDF page, table row, section heading, or article/appendix locator.
- Whether the locator applies to initial issuance, extension, change, registration, or another procedure.

Broad locators like "2026 manual" or "HiKorea" are not enough for `verified=true`.

## Source quote requirements

High-impact claims require either an exact quote or a precise section reference:

- Legal duty.
- Eligibility.
- Required document.
- Deadline.
- Fee.
- Status-specific exception.

If quote extraction is not possible, provide a precise section locator and reviewer note explaining why it is sufficient. If neither quote nor precise locator is available, keep `verified=false`.
