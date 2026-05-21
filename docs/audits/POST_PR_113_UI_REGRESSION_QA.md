# Post-merge Regression QA — PR #113

Date: 2026-05-21 (UTC)
Branch: `audit/post-pr-113-ui-regression-qa`
Target PR (already merged): #113 — `feat(ui): restructure result and Paradiso.ai answer cards`

## Environment / fetch status
- Attempted to update local main with `git pull --ff-only origin main`.
- **BLOCKED_BY_ENVIRONMENT**: remote `origin` is not configured in this container (`fatal: 'origin' does not appear to be a git repository`).
- QA scope below is based on the locally available repository state only.

## Files inspected
- `index.html`
- `ai.html`
- `docs/design/PARADISO_UX_DIRECTION_LOCK.md`
- `docs/design/RESULT_AND_AI_CARD_STRUCTURAL_REWRITE_V2_NOTES.md`
- `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md`
- `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`
- `docs/ai/ANSWER_QUALITY_CONTRACT.md`

## Commands run
1. `git status --short`
2. `python3 -m json.tool visa_data.json > /dev/null`
3. `bash scripts/check_repo.sh`
4. `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`
5. `rg -n "open-hikorea-guide|hikoreaGuideOverlay|updateCategoryCounts|renderGroundingSourcePanel|pa-answer-card-shell|appendAiAnswer|data-action" index.html ai.html`
6. `rg -n -i "legally verified|official decision|guaranteed|production-ready law grounding|legally binding" index.html ai.html docs`

## Regression checklist summary

### Automated/static checks
- ✅ PR #104-preserved selectors and hooks (`data-action`, `open-hikorea-guide`, `hikoreaGuideOverlay`, `updateCategoryCounts`, `appendAiAnswer`, `pa-answer-card-shell`, `renderGroundingSourcePanel`) are present in `index.html`/`ai.html`.
- ✅ `visa_data.json` parses cleanly.
- ✅ Repository policy checks pass in skip mode (`ALLOW_BACKEND_TEST_SKIP=1`) with backend dependency bootstrap blocked by proxy (403 tunnel failures).
- ✅ No new assertive overclaim phrases were found in `index.html`/`ai.html`; existing conservative disclaimer language remains present.
- ✅ Required-documents coverage check reports no rendering-coverage regression and no fallback gaps in current data snapshot.

### Runtime/manual items still requiring browser verification
The following items cannot be conclusively proven by static CLI-only checks and should be manually smoke-tested in a browser session:
- body state machine transitions (`landing/searching/searched`)
- language toggle interaction
- theme toggle interaction
- direct visa search flow (D-2, E-7, F-1, F-6)
- keyword search flow (address/passport information change)
- unknown visa fallback rendering
- HiKorea CTA + overlay open/close + flow steps
- reminder feature behavior
- agent finder + medical institution finder behavior
- mobile 390px overflow / duplicate wordmark visual checks
- inert shell behavior at runtime (`pa-answer-card-shell` not breaking legacy `appendAiAnswer()` rendering)

## Pass/fail disposition
- **Code patch required:** No.
- **Code patch applied:** No.
- **QA audit artifact added:** Yes (`docs/audits/POST_PR_113_UI_REGRESSION_QA.md`).

## Blocked commands / environment limitations
- `git pull --ff-only origin main` blocked due missing/inaccessible remote.
- `bash scripts/check_repo.sh` full backend test path blocked by dependency bootstrap failures under proxy restrictions (`CONNECT tunnel 403`).
- Used fallback command as instructed: `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`.
