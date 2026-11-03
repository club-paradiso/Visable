# Visable frontend rebuild — STATUS

This file is the resume point. A fresh session must read it first, verify the
"Last verified state" against the real repo (branch, open PRs, CI), and continue
from the first unfinished step. Never redo a phase recorded as done and verified.

## Last verified state
- Date: 2026-11-03
- Working branch: `claude/visable-frontend-rebuild-0289z4` (harness-designated; see DECISIONS.md ADR-001)
- Base: `origin/main` @ 5082d9d (Merge PR #757, address helper tool)
- Open PRs by this effort: **#758** https://github.com/club-paradiso/Visable/pull/758 (draft; Phase 0)
- Current phase: **Phase 2 — Build tooling (Vite)** (in progress; Phases 0–1 done)

## Environment facts (verified this session)
- Node v22.23.4, npm 10.9.9, Python 3.13.18
- `npm install --ignore-scripts --package-lock=false` installs @playwright/test 1.64.1 (package.json pins ^1.61.0)
- Pre-installed Chromium is build 1243 at `/opt/pw-browsers/chromium`; Playwright 1.64.1 wants 1248 and
  cannot download. Run every Playwright suite with
  `PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium` (playwright.config.mjs already honours it).
  Verified: `PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium npx playwright test tests/e2e/landing-boot.spec.mjs --project=desktop-1280` → 14 passed (25.6s).
- Git clone is shallow (161 commits); history-based checks are limited.

## Baseline measurements (verified 2026-11-03, commands in phase0 report)
| Metric | Prompt claim | Measured | Command |
|---|---|---|---|
| index.html lines | 26,908 | 26,908 | `wc -l index.html` |
| inline `<script>` blocks (logic) | 11 | 11 (8 bare `<script>` + 3 `<script id=...SHIM...>` / settings) | `grep -o '<script[^>]*>' index.html \| sort \| uniq -c` |
| external scripts | 25 | 26 (24 classic + 2 `type=module`) | same |
| inline `<style>` blocks | 6 | 6 | `grep -c '<style' index.html` |
| `!important` in index.html | — | 1,406 | `grep -o '!important' index.html \| wc -l` |
| `!important` index.html + assets/css | 3,307 | 3,307 | `cat index.html assets/css/*.css \| grep -o '!important' \| wc -l` |
| function declarations in index.html | ~487 | 487 | `grep -cE '^\s*(async\s+)?function\s+\w+' index.html` |
| `innerHTML` uses | 112 | 112 | `grep -o innerHTML index.html \| wc -l` |
| `localStorage` uses | 41 | 41 | `grep -o localStorage index.html \| wc -l` |
| `fetch(` calls | 12 | 12 | `grep -o 'fetch(' index.html \| wc -l` |
| linked CSS files | 9 | 8 local + 3 font CDN | `grep -o '<link[^>]*stylesheet[^>]*>' index.html` |
| assets/js modules | 36 / ~31,600 | 36 / 31,642 | `ls assets/js \| wc -l; wc -l assets/js/*.js` |
| other HTML pages | 10 | 10 | `ls *.html` |
| scripts/tests files referencing index.html | 64 | 84 files (incl. e2e specs + README) | `grep -l index.html scripts/* tests/e2e/* \| wc -l` |
| docs/ | ~404 MB | 404M | `du -sh docs` |
| backend/data/ | ~120 MB | 120M (manual_search_index.sqlite3 = 43,618,304 B) | `du -sh backend/data; ls -la backend/data/manual_search_index.sqlite3` |
| data/ | ~56 MB | 56M | `du -sh data` |
| experiments/ | ~22 MB | 22M | `du -sh experiments` |
| .git | ~287 MB | 287M (shallow clone) | `du -sh .git` |
| backend/paradiso_backend.py | ~9,196 | 9,196 | `wc -l` |
| duplicate JSON pairs | jobcode_master.json vs data/, output.json vs data/ | **Only `data/jobcode_master.json` exists.** `jobcode_master.json`, `output.json`, `data/output.json` do not exist. index.html:16931 still lists all four as a fallback chain. | `ls -la jobcode_master.json data/jobcode_master.json output.json data/output.json` |

## Phase 0 — Safety net (in progress)
- [x] Baseline measurements (above)
- [x] Playwright runs in this sandbox (see Environment facts)
- [x] Existing e2e baseline: `PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium npx playwright test --project=desktop-1280 --project=mobile-390 --workers=4` → **563 passed, 69 skipped, 0 failed (8.3m)**
- [x] Production/preview `*.vercel.app` URLs are NOT reachable from this sandbox (curl → 000). Preview verification must run in GitHub Actions (ADR-004).
- [x] docs/rebuild/phase0-inventory.md (46 index features: C20/I18/P8; 11 other pages inventoried; address-helper.html added by PR #757 noted)
- [x] docs/rebuild/phase0-legacy-checks.md (38 index-reading checks classified; retire mapping started)
- [x] docs/rebuild/phase0-data-canon.md (no duplicate pair exists; canon = data/jobcode_master.json)
- [ ] tests/golden/ Playwright suite (every Critical feature, all shipped UI languages, desktop + mobile, fail-closed cases, visual baselines)
- [x] `.github/workflows/golden.yml` (golden-local on PRs, golden-visual baseline generation, golden-deployment on Vercel deployment_status / dispatch). Not yet observed running (push pending).
- [x] **Exit met (2026-11-03):** golden suite green 3× in a row against the unmodified site, served from a detached worktree at 2b22766 (pre-Phase-1 code) with the final specs:
  `GOLDEN_SERVE_DIR=<worktree> GOLDEN_PORT=4330 PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium npx playwright test -c playwright.golden.config.mjs --project=desktop-1280 --project=mobile-390` → run 1: 100 passed / 6 skipped; run 2: 100 passed / 6 skipped; run 3: 100 passed / 6 skipped (2.1 min each). The 6 skipped are the BLOCKED `test.fixme` markers (live keys / operator token).
  CI: Golden Suite run 41701563795 at f3bb0d7 → `golden-local` success (desktop + phone, 2.0 min), `golden-visual` success (baselines generated on the runner, artifact `golden-visual-41701563795-1`), `golden-deployment` skipped by the GOLDEN_PREVIEW_ENABLED gate.
  Earlier flakes and their root causes (all test-side, none product-side): new-home locale set after load (fixed with addInitScript), new-home notice read before render (fixed with a text poll; a substring locator matched a hidden duplicate span), finder test read the body before candidates rendered (fixed by waiting for the code).
- Phase 0 status: **done and verified.**

## Phase 1 — Repo diet and data canon (in progress)
Done (verified 2026-11-03):
- `.vercelignore` committed (6e782a8, ADR-006). Vercel build log for deployment dpl_5pz3NhN6nmDccvF1ByK38kLJEdss (commit 6e782a8): "Found .vercelignore" → "Removed 2447 ignored files defined in .vercelignore" (3,230 − 2,447 = 783 files, matching `node scripts/measure_deploy_set.mjs` → 783 files / 117.9 MB). Clone step on Vercel still takes 3:31 (git history size; see history-rewrite-plan.md).
- Preview spot checks on that deployment via the Vercel MCP fetch (SSO-protected URL, share link): `/manual.html` 200 with the two PDF links, `/docs/forms_official/FORM_HELPER_COVERAGE_20260923.md` 200, `/data/i18n/manifest.json` 200, `/api/enforcement/law-probe` 200 JSON (function bundles `backend/data/enforcement/legal_rules.json` correctly).
- `JOBCODE_JSON_PATHS` trimmed to `./data/jobcode_master.json` (f3bb0d7) with a new golden test `tests/golden/specs/tools.spec.mjs` (finder loads the canonical file only; occupation 2970 found). Verified locally 5/5 runs on desktop-1280 + mobile-390.
- history-rewrite-plan.md written (not executed).
- **Exit met (2026-11-03):** golden suite against the modified working tree (5f325b8 / b9cfad5, repo root served) 3× in a row: 100 passed / 6 skipped each (2.1–2.2 min). Deploy size before/after: 3,230 files / 647.1 MB → 783 files / 117.9 MB (Vercel: "Removed 2447 ignored files"). Checkout size unchanged (nothing deleted from git; history rewrite is the owner's call, history-rewrite-plan.md).
- Phase 1 status: **done and verified.** Left open by design: `backend/data/manual_search_index.sqlite3` stays committed (owner decision 4).

Pre-measurements (verified 2026-11-03):
Pre-measurements (verified 2026-11-03):
- Tracked files: 3,218 / 647.0 MB (`git ls-files` sizes). Vercel git deployments upload all of it today (no `.vercelignore`).
- Planned `.vercelignore` (archive docs, superseded manual editions, experiments, tests, audits, reports, backend except `backend/data/enforcement/` which `lib/enforcement-fallback.js` requires) → **871 files / 133.5 MB** (data 54.6, docs 44.4, assets 25.5, scripts 4.6, root 4.0).
- Runtime paths that MUST stay deployed (grep of shipped HTML/JS/api): `docs/source-manuals/2026-10-19/visa_manual_261019.pdf`, `docs/source-manuals/2026-11-02/stay_manual_261102.pdf`, `docs/forms_official/FORM_HELPER_COVERAGE_20260923.md`, `scripts/employment_*.mjs`, `scripts/enforcement-ui.mjs`, `lib/**`, `backend/data/enforcement/legal_rules.json`, `data/**`, `assets/**`, `agency-directory/` (unlinked but harmless, 0.4 MB).
- Steps: (1) trim `JOBCODE_JSON_PATHS` to the canonical path (behaviour-preserving; golden procedure/search tests + check_employment_* guard it); (2) add `.vercelignore` + a measurement script; (3) history-rewrite-plan.md written (done, not executed); (4) generated-artefact decision for `backend/data/manual_search_index.sqlite3` → Railway deploy dependency, owner decision.

## CI notes (PR #758)
- `webkit-e2e` (Repo Validation) is red on this PR at fe338a3 and 1acc5d6 with exactly one failure:
  `tests/e2e/search-first-home.spec.mjs:226 › dialog tools open the existing dialogs from the keyboard` on
  `webkit-desktop-1280` (365 passed, 38 skipped). The same test is the known pre-existing WebKit failure that
  main's merge commits for #745, #746 and #755 record ("webkit-e2e is red only on search-first-home dialog
  tools, which fails the same way on unrelated PRs"). fe338a3 contains no product change, so it is not this PR's.
  No fix exists yet; it is outside this PR's scope (a WebKit keyboard/dialog issue in the existing e2e spec), noted
  once on the PR.
- `golden-deployment` was red by design before the GOLDEN_PREVIEW_ENABLED gate (d8ed3cb); skipped since.

## Owner decisions needed
1. **Vercel preview access for CI** — the project has `ssoProtection: all_except_custom_domains`, so preview URLs return 401/SSO to GitHub Actions. To satisfy the "golden suite 3× against the preview" merge rule the owner must create a *Protection Bypass for Automation* secret in Vercel (Project → Settings → Deployment Protection) and add it as the repository secret `VERCEL_AUTOMATION_BYPASS_SECRET`, then set the repository variable `GOLDEN_PREVIEW_ENABLED=true` (the `golden-deployment` job is skipped until then so it does not stay red by design; verified red on the first run: HTTP 302 SSO redirect). Hard stop 6 (Vercel settings / secrets) — not done by this session. Recommendation: do it; it is read-only for the site and scoped to automation.
2. **Branching** — this session may only push to `claude/visable-frontend-rebuild-0289z4` (ADR-001). The brief's one-branch-per-phase + self-merge rule cannot be followed without permission. Recommendation: review/merge the Phase 0 PR, then grant `rebuild/phase-N-*` branches or keep one long-lived PR per phase re-targeted from this branch.
4. **Generated search index on Railway** — `backend/data/manual_search_index.sqlite3` (41.6 MB, the largest blob in history) is generated by `npm run build:manual-index`. Moving it out of git needs a Railway build step (hard stop 6) and a byte-identical rebuild proof. Recommendation: owner adds `python3 scripts/build_manual_search_index.py --out backend/data/manual_search_index.sqlite3` to the Railway build command, then this file can be dropped from the repo in a later phase; until then it stays.
3. **Visual baselines** — generated on the CI runner (ADR-005) and uploaded as an artifact; someone must download and commit `tests/golden/__screenshots__/` (this sandbox cannot download Actions artifacts). Recommendation: owner commits them after a glance, or grants a CI commit-back step (contents: write).

## Next step
Finish the three Phase 0 documents from subagent output, then author tests/golden/.
