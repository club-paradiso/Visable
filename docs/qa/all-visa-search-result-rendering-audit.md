# All-Visa Search and Result Rendering Audit

## Summary

This documentation-only audit records the current static search/result-rendering baseline for all visa/status code entries after PR #133 (`fix(ui): apply Figma landing direction while preserving search flows`).

The audit exists to provide a controlled baseline before fixing search-ranking and result-card quality issues across the full visa catalog.

## Scope

This PR is documentation-only.

No code or data files were modified:

- `index.html` untouched
- `ai.html` untouched
- backend untouched
- `visa_data.json` untouched
- `doc_master.json` untouched

## Post-PR #133 rebase note

The audit branch was based on the latest main after PR #133 was merged.

Latest relevant main history includes:

```text
c4d318f Merge pull request #133
```

PR #133 changed the landing UX only and reported preservation of search flows, including command palette opening, D-2/E-7 search, compact results, visa drawer, document modal, HiKorea guide, Paradiso.ai link, language toggle, and theme toggle.

This audit should therefore be read as the post-PR #133 static baseline.

## Method

The audit extracted visa/status code entries from the current repository data and checked static search/result-rendering assumptions against the frontend structure.

Browser automation was attempted in the previous Codex workspace but was unavailable/blocked for the local `127.0.0.1:8765` URL. Browser-dependent checks are therefore intentionally marked as `NOT EXECUTED`, not `PASS`.

## Extracted code coverage

- Total extracted code entries: `197`
- Top-level records: `58`
- Subcodes: `139`

## Static audit result

| Category | Count |
|---|---:|
| PASS | 193 |
| FAIL | 4 |
| NOT EXECUTED | 0 |

Static counts were unchanged after rebasing onto the post-PR #133 main baseline.

## Browser audit result

| Environment | PASS | FAIL | NOT EXECUTED |
|---|---:|---:|---:|
| Desktop browser | 0 | 0 | 197 |
| Mobile 390px browser | 0 | 0 | 197 |

Browser checks remain `NOT EXECUTED` because browser automation was unavailable/blocked in the audit environment. No browser PASS status is claimed.

## Priority spot-check result

Priority spot-check codes did not show no-result, compact-card, or drawer-target failures in the static audit:

- D-2
- D-4
- E-7
- F-1
- F-2
- F-5
- F-6
- G-1
- H-1
- H-2
- C-3
- D-10

These still require real browser/mobile visual QA before being called fully verified.

## Known failures and weak-match findings

The static audit identified exact-code ranking issues that should be handled in a separate search-ranking PR.

### P1: Exact-code ranking issues

- Query `D-1` ranks `D-10` ahead of the exact `D-1` match.
- Query `E-1` ranks `E-10` ahead of the exact `E-1` match.
- Duplicated `D-4-2K` appears to rank behind broader `D-4` matches.

These were intentionally not fixed in this documentation-only audit.

Recommended follow-up PR:

```text
fix(search): prioritize exact visa-code matches
```

Expected ranking rule:

```text
exact code match > prefix match > substring match > fuzzy/keyword match
```

## Browser-dependent checks still needed

A later browser QA pass should test at least:

- Every code search opens at least one result or a clear empty state.
- Compact result cards render without console errors.
- `자세히 보기` opens the correct visa drawer.
- Drawer content does not overflow on mobile.
- Document/checklist section does not crash.
- Source/manual panel does not disappear.
- `DATA_MISSING` is shown honestly where data is incomplete.
- No forbidden official/legal guarantee wording appears.

## Validation rerun

The following validation checks were reported as passing after the post-PR #133 rebase:

- `node scripts/check_i18n.js` PASS
- `python3 -m json.tool visa_data.json > /dev/null` PASS
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` PASS
- `git diff --check` PASS
- Forbidden phrase scan PASS, no matches

Smart quote scan:

- `rg -n "[‘’“”]" index.html ai.html` found 8 existing `index.html` i18n/landing-copy lines.
- No patch was made because those lines were pre-existing content and not introduced by this audit.

## Forbidden phrase scan

The forbidden phrase scan returned no matches for:

```text
Paradiso 39|v39|v38|legally verified|official decision|guaranteed|approved|government-certified|production-ready law grounding|verified official decision|검증 완료|공식 결정|승인 보장
```

## Issue categories for future audits

Future browser and data-quality audits should classify failures under:

- no search result
- weak search match
- compact card missing
- drawer target missing
- drawer opens but content poor
- document section empty or misleading
- source panel missing
- `DATA_MISSING` excessive
- mobile overflow
- JS console error
- forbidden legal/official copy
- needs manual review

## Recommended next PRs

1. `fix(search): prioritize exact visa-code matches`
   - Fix D-1/D-10, E-1/E-10, and D-4-2K ranking behavior.
   - Keep scope narrow to search scoring.

2. `fix(ui): improve D-2 result readability and document accuracy`
   - Focus on D-2 as the primary demo/use case.
   - Improve information hierarchy, document grouping, source panel visibility, and drawer readability.

3. `audit(ui): run browser visual QA for priority visa codes`
   - Use real browser/manual or Agent Mode inspection for D-2, D-4, E-7, F-1, F-6, C-3, D-10.
   - Include mobile 390px screenshots/notes.

4. `docs(qa): plan staged all-visa quality remediation`
   - Create a staged plan by visa family: D-series, E-series, F-series, C/G/H-series, and other/special categories.
   - Do not attempt to fix every visa code in one PR.

## PR body draft

```text
## Summary

Adds a documentation-only all-visa-code search/result rendering audit after PR #133.

## Scope

Documentation-only. No code/data files modified.

## Results

- Static audit covered 197 extracted code entries: 58 top-level records + 139 subcodes.
- Static counts after rebase: 193 PASS / 4 FAIL / 0 NOT EXECUTED.
- Browser checks remain NOT EXECUTED because browser automation was unavailable/blocked.
- Known exact-code ranking findings:
  - D-1 ranks behind D-10
  - E-1 ranks behind E-10
  - D-4-2K ranking/duplication issue

## Validation

- node scripts/check_i18n.js PASS
- python3 -m json.tool visa_data.json > /dev/null PASS
- ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh PASS
- git diff --check PASS
- Forbidden phrase scan PASS

## Next recommended PR

fix(search): prioritize exact visa-code matches
```
