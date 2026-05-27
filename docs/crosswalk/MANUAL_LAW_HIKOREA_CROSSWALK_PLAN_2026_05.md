# Manual/Law/HiKorea Crosswalk Plan - 2026.5

## Purpose

This plan defines the next gated step after the official source-set/readiness audit.

The goal is to create a field-level crosswalk before any production data correction. The crosswalk should prove which official source supports each Paradiso data field, procedure label, document list, and user-facing guide.

## Why this step exists

Paradiso currently has source inventory documents and validated manuals. That is not enough to patch data safely.

Before touching production JSON, the project needs a mapping layer that answers:

- Which manual page or HiKorea guide supports this procedure?
- Which law article supports this legal basis or reporting duty?
- Which field in `visa_data.json` or `backend/data/visas.json` would be affected?
- Is the requirement universal, conditional, or sub-code-specific?
- Is there a law/manual conflict requiring human review?

## Primary outputs

The eventual completed crosswalk should include:

- status-level entries for A-1 through H-2 and special tracks,
- procedure-level entries for registration, extension, change of status, workplace change, passport change, address change, electronic petition, reservation, certificate issuance, and forms,
- source references with title, date, official URL or local path, page or article,
- target data field references,
- readiness labels for future patching.

## Work phases

### Phase 1 - Procedure crosswalk first

Prioritize common civil-petition procedures because they affect many statuses.

Initial procedure set:

1. foreigner registration,
2. extension of stay,
3. change of status,
4. workplace change/addition,
5. passport or registration-information change,
6. residence/address change,
7. electronic civil petition,
8. visit reservation,
9. certificate issuance,
10. official forms.

### Phase 2 - High-risk status crosswalk

Prioritize statuses with high user risk, sub-code complexity, or weak existing structured data.

Initial status set:

- C-3,
- D-2,
- D-4,
- D-10,
- E-7,
- E-8,
- E-9,
- E-10,
- F-series,
- G-1,
- H-1,
- H-2,
- regional visa,
- broad-area pilot visa,
- Top-Tier,
- K-STAR.

### Phase 3 - Full all-status crosswalk

After high-risk categories are stable, extend the crosswalk to every status from A-1 through H-2.

### Phase 4 - Patch planning

Only after the crosswalk is complete should the project prepare scoped data correction PRs.

## Readiness labels

Use these labels in crosswalk records:

- `READY_FOR_FIELD_PATCH`
- `NEEDS_PAGE_CITATION`
- `NEEDS_ARTICLE_CITATION`
- `NEEDS_ATTACHMENT_ARCHIVE`
- `LAW_MANUAL_CONFLICT_REVIEW`
- `SUBCODE_AMBIGUITY_REVIEW`
- `SCHEMA_GAP`
- `DO_NOT_PATCH`

## Non-goals

This scaffold does not:

- patch `visa_data.json`,
- patch `backend/data/visas.json`,
- remove `needsManualReview`,
- promote `verified=true`,
- activate AI grounding,
- change frontend behavior.

## Recommended next PR after this scaffold

`docs: build 2026.5 procedure crosswalk`

That PR should fill the procedure crosswalk first using the validated source set.
