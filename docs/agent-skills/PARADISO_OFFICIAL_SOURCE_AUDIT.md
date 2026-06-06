# Paradiso Official Source Audit Protocol

## Purpose

Use this protocol when auditing Paradiso visa, stay-status, procedure, document, fee, deadline, office, or AI-grounding content for official source support.

The goal is to identify which claims are supported by official evidence, which are only partially supported, and which must remain marked for manual review. The audit must not create legal certainty by inference.

## Allowed actions

- Read committed Paradiso data, docs, fixtures, manuals, and source manifests.
- Compare records against official sources already committed to the repository.
- Record missing, partial, stale, conflicting, or unclear support.
- Propose follow-up patches with exact source locators and quotes.
- Classify evidence with the status taxonomy in `docs/verification/source-status-taxonomy.md`.
- Run read-only scripts that inspect data and print warnings.

## Forbidden actions

- Do not edit production data during an audit-only task.
- Do not set `verified=true`.
- Do not remove `needsManualReview`.
- Do not delete scenario, helper, FAQ, overstay, sub-code, or exception records.
- Do not rewrite user-facing legal guidance from memory or AI inference.
- Do not cite unofficial blogs, law-firm summaries, immigration-agent pages, random PDFs, SEO pages, forum answers, or AI summaries as legal authority.
- Do not introduce OpenAlex as an official immigration source.
- Do not treat internal Paradiso normalized data as the final authority unless it points to an official locator.
- Do not invent page numbers, manual versions, quotes, URLs, section names, or office jurisdiction details.

## Official source hierarchy

Use the highest applicable source. A lower tier can add context but cannot override a higher tier.

1. Korean statutes, enforcement decrees, enforcement rules, and official legal texts from official law sources.
2. Ministry of Justice or Korea Immigration Service manuals, forms, public notices, and official PDFs/HWPs with version/date evidence.
3. HiKorea, Korea Immigration Service, Visa Portal, government office, or 1345 official pages for procedures, offices, reservations, forms, and service routing.
4. Other Korean government sources only when the claim belongs to that agency's authority, such as Socinet for KIIP or official local-government pages for local office details.
5. Paradiso internal normalized data only as a pointer to the official evidence above, not as independent legal authority.

If sources conflict, report the conflict and keep the affected claim unverified until a reviewer resolves it.

## Read-only audit mode

Read-only audit mode is the default for this protocol.

- The auditor may inspect files and run audit scripts.
- The auditor may create docs, reports, schemas, or non-blocking tooling.
- The auditor must not modify production JSON records.
- The auditor must not change runtime AI answer generation.
- The auditor must not change frontend UI or backend routes.
- The auditor must not make CI fail unless a strict mode is explicitly requested.

## Required output format

Every audit output must include:

| Field | Required content |
|---|---|
| `recordPath` | File path and JSON path or stable record identifier. |
| `claimText` | Exact claim text or concise description of the record assertion. |
| `claimCategory` | One of the categories in `PARADISO_CLAIM_VERIFICATION.md`. |
| `currentFlags` | Current `verified`, `needsManualReview`, and `sourceStatus` values if present. |
| `sourceType` | Official source type, internal normalized source, or unavailable. |
| `sourceLocator` | URL, manual file, version date, page, section, article, notice id, or form id. |
| `supportLevel` | `direct`, `partial`, `contextual`, or `unavailable`. |
| `finding` | `ok`, `warning`, `error`, or `needs_manual_review`. |
| `recommendedAction` | Preserve, add locator, add quote, split scenario, reviewer check, or do not verify. |

## Failure handling

- Missing official support must be reported, not invented.
- If an official source cannot be opened, state that retrieval failed and keep support level `unavailable`.
- If a source supports only a parent status but not a sub-code or exception, classify as `partial` or `contextual`.
- If a source supports the procedure but not the fee, document, deadline, or eligibility condition, verify only the supported claim and report the rest.
- If exact text is ambiguous, require manual review and keep `verified=false`.
- If a patch would need production-data changes, stop and create a separate data patch plan.
