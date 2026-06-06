# Paradiso PR Review Gate

## Scope

Apply this checklist before merging PRs that affect:

- Visa/status data.
- Document requirements.
- AI answers, answer grounding, citations, or source panels.
- Legal, stay-status, procedure, deadline, fee, office, or reservation guidance.
- Source manuals, source catalogs, grounding fixtures, or audit tooling.

## Source locator coverage

- Every new or expanded official claim has a source locator.
- Locator includes official source type, title/name, version/date, URL or repo path, page/section/article/row when applicable.
- `sourceStatus` values use `docs/verification/source-status-taxonomy.md`.
- `verified=true` changes satisfy `docs/verification/verified-true-gate.md`.
- Claims with partial, contextual, stale, conflicting, or missing evidence are not presented as source confirmed.

## Regression checks

- Run the smallest relevant existing tests or scripts for the touched area.
- For data changes, run record-store parity, text-integrity, and source-evidence checks when available.
- For AI answer changes, run answer contract, grounding, and safeguard tests when available.
- For manual/source changes, run source monitor or manual-grounding validators when available.
- If a check cannot run, the PR description must say why and what risk remains.

## Exact-code search checks

For every touched status code, sub-code, document id, helper id, or source id:

- Search exact identifiers across production data, backend fixtures, scripts, and docs.
- Confirm no orphan references, duplicate records, stale aliases, or mismatched code/sub-code assumptions.
- For deletions or renames, include the exact search terms and result summary in the PR.
- For broad patches, sample at least one parent status, one sub-code, and one helper/scenario record.

## UI duplicate-section checks

If the PR touches any UI-facing field, renderer, or answer payload:

- Check that required documents do not render in duplicate sections.
- Check that source panels do not duplicate official and internal versions of the same source as separate authorities.
- Check that fallback or uncertainty sections do not repeat the same warning in multiple places.
- Check mobile and desktop layouts if UI code changes.

If the PR is docs/tooling only, explicitly state that no frontend UI was modified.

## Disclaimer checks

- AI answers that include legal, eligibility, deadline, fee, or status-specific exception claims must carry an appropriate non-advice disclaimer or uncertainty signal.
- Missing official support must be visible to the user or reviewer, not hidden in logs.
- High-risk cases must direct users to official confirmation, 1345, immigration office, or qualified professional review as appropriate.
- Disclaimers must not be used to justify unsupported confident claims.

## No unofficial-source contamination

- Unofficial blogs, law firms, agencies, forums, AI answers, random PDFs, and SEO pages cannot serve as legal authority.
- OpenAlex cannot be introduced as an official source for immigration claims.
- Internal Paradiso data cannot be cited as an official source unless it links to official evidence.
- If an unofficial source was used for discovery, the PR must replace it with official evidence before making a claim.

## No unsupported claim expansion

- Do not broaden a sourced claim from one status to another.
- Do not broaden a sourced claim from one procedure to all procedures.
- Do not broaden a sourced claim from a parent code to sub-codes or exceptions.
- Do not turn contextual source material into direct support.
- Do not convert manual location evidence into substantive verification unless the source text was reviewed.

## Required PR description items

Every in-scope PR must include:

- Files changed.
- Whether production data changed.
- Whether frontend UI changed.
- Whether backend runtime or AI generation changed.
- Source evidence summary.
- Checks run.
- Known source gaps or manual-review items.
