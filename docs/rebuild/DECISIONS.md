# Visable frontend rebuild — DECISIONS (ADR log)

Short ADR-style entries. Every decision taken without the owner goes here with
the options considered, the evidence, and the reason.

## ADR-001 — Single harness branch instead of one branch per phase
- Date: 2026-11-03
- Context: the rebuild brief asks for `rebuild/phase-N-<slug>` branches and one PR per
  phase. The execution harness for this session designates
  `claude/visable-frontend-rebuild-0289z4` and forbids pushing to any other branch
  without explicit permission.
- Options: (a) create phase branches anyway; (b) do all phases on the designated
  branch, one PR, with phase boundaries as squash-mergeable commit groups and
  STATUS.md checkpoints; (c) stop and ask.
- Decision: (b). The harness rule is the stricter, explicit constraint. Phase
  boundaries are still recorded (tags in STATUS.md, commit message prefixes
  `phase0:`, `phase1:` …) so the owner can cherry-pick or split later.
- Consequence: "merge a phase PR into main yourself" is not possible until the owner
  grants branch permission; the PR stays open with full evidence (brief: "If you
  cannot … do not merge"). Listed under Owner decisions in STATUS.md.

## ADR-002 — Run Playwright with the pre-installed Chromium 1243
- Date: 2026-11-03
- Context: `npm install` resolves `@playwright/test@^1.61.0` to 1.64.1, which expects
  Chromium 1248; the sandbox has 1243 and cannot download browsers.
- Options: pin @playwright/test to a 1243-compatible version in package.json (a
  product/tooling change to make the sandbox happy), or use the existing
  `PARADISO_PW_EXECUTABLE` escape hatch in playwright.config.mjs.
- Decision: use `PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium` locally; CI keeps
  downloading its own browser. No package.json change.
- Evidence: landing-boot.spec.mjs desktop-1280 → 14 passed with the env var, 14 failed
  without it (browserType.launch: Executable doesn't exist …1248…).

## ADR-003 — Duplicate-JSON canon is already `data/jobcode_master.json`
- Date: 2026-11-03
- Context: the brief lists `jobcode_master.json` vs `data/jobcode_master.json` and
  `output.json` vs `data/output.json` as differing duplicates.
- Evidence: only `data/jobcode_master.json` exists in the checkout (md5
  5b0138f0e6e2dec5d5f90186e2494a1e). The other three paths do not exist; the shallow
  clone (161 commits) has no deletion record. `index.html:16931` keeps a four-path
  fallback chain `['./data/jobcode_master.json', './data/output.json', './jobcode_master.json', './output.json']`.
- Decision: canonical file = `data/jobcode_master.json`. No data merge is needed, so
  hard stop 3 is not triggered. Phase 1 trims the fallback chain to the canonical
  path only after a golden test proves the employment helper loads from it. Details
  in phase0-data-canon.md.

## ADR-004 — Preview-deployment verification runs in GitHub Actions, not in the sandbox
- Date: 2026-11-03
- Context: the brief requires the golden suite to pass 3× against the Vercel preview of each
  PR before a merge. `curl https://visable-mu.vercel.app/index.html` and the latest preview
  URL both return HTTP 000 from this sandbox (egress policy). The Vercel MCP exposes deployment
  metadata (project `visable`, team `team_YA4bUgBlPWrfBJGi6nea1W8W`) but cannot run a browser.
- Options: (a) skip preview verification; (b) a golden CI job that targets the PR's preview URL
  via `GOLDEN_BASE_URL` on `deployment_status` success events; (c) only local-static CI.
- Decision: (b) + (c). `.github/workflows/golden.yml` runs the suite against a local static
  server on every PR (blocking) and against the Vercel preview URL when Vercel reports the
  deployment ready (evidence for the 3× rule, read back through the GitHub MCP). Production
  runs are a `workflow_dispatch` input. Visual baselines are generated on the CI runner (fonts
  differ from this sandbox) — see ADR-005.

## ADR-005 — Visual baselines are produced on the CI runner, not in the sandbox
- Date: 2026-11-03
- Context: pixel baselines depend on installed fonts. The sandbox has IPA Gothic / WenQuanYi;
  `playwright install --with-deps` on ubuntu-latest installs a different set. Baselines
  captured here would fail in CI for font reasons alone, and external font CDNs are blocked here.
- Decision: `visual.spec.mjs` runs only in the `visual-*` projects. The `golden-visual` CI job
  compares against `tests/golden/__screenshots__/` when present, otherwise generates the
  baselines with `--update-snapshots` and uploads them as an artifact for review and commit.
  Tolerance `maxDiffPixelRatio: 0.02`, animations disabled, caret hidden, font CDNs aborted.
- Consequence: the first CI run on the PR produces the baselines; they are committed in a
  follow-up commit after inspection, and only then does the job start to compare.

## ADR-006 — `.vercelignore` with explicit paths instead of `docs/**` + negations
- Date: 2026-11-03 (Phase 1)
- Context: Vercel git deployments upload every tracked file (3,230 files / 647.1 MB measured
  with `node scripts/measure_deploy_set.mjs --no-ignore`). Only a small set is needed at runtime:
  `data/**`, `assets/**`, the HTML pages, `scripts/*.mjs` loaded by pages, `lib/**`, `api/**`,
  the two current manual PDFs, `docs/forms_official/`, and `backend/data/enforcement/legal_rules.json`
  (required by `lib/enforcement-fallback.js`, which the enforcement functions bundle).
- Options: (a) `docs/**` + `!docs/source-manuals/…pdf` — gitignore semantics cannot re-include a
  file under an excluded directory, so the PDFs would vanish; (b) explicit directory list; (c) move
  archives to another repository (hard stop 2 territory for anything not regenerable).
- Decision: (b). Explicit directories and file patterns; superseded manual editions, HWP sources and
  conversion by-products excluded; `backend/` excluded piecewise so `backend/data/enforcement/` stays.
  Result: **783 files / 117.9 MB**. Verified with the matcher in `scripts/measure_deploy_set.mjs`
  that every runtime path above is still included and `docs/source-manuals/2026-10-19/stay_manual_261019.pdf`
  (superseded, unlinked) is excluded.
- Not done: nothing is deleted from the repository (hard stop 2); `backend/data/manual_search_index.sqlite3`
  stays committed (Railway reads it; moving it to build time needs an owner-run deploy, hard stop 6).
- Verification plan: golden suite green locally; after push, the Vercel preview build log shows the
  smaller upload and `golden-deployment` runs when the bypass secret exists.


## ADR-007 — Generated data files stay committed; CI proves they are current
- Date: 2026-11-03 (Phase 1)
- Context: several deploy-path files are script outputs: `data/search-suggest-index.json`
  (`npm run build:search-suggest`), `data/status-guidance-202609.json` and
  `data/status-coverage-202609.json` (`npm run build:status-guidance`, Python),
  `data/manual-reader/**` (`npm run build:manual-reader`, Python with pinned parsers),
  `data/manual-corpus/*.json` and `backend/data/manual_search_index.sqlite3`
  (`npm run build:current-manuals`). The brief allows generating them at build time only
  when the output is provably identical.
- Evidence: `scripts/check_repo.sh` already runs every builder in `--check` mode
  (`build_status_coverage_manifest.py --check`, `author_rules.py --check`,
  `build_manual_reader.py --check`, `check_search_suggest.mjs` "index is current"), so a
  committed file that drifts from its generator fails CI today.
- Options: (a) generate in the Vercel build (needs Python + pinned deps on the builder, and
  turns legal-content generation into a deploy-time step that could change what users see
  without a reviewed commit); (b) keep committed, keep the `--check` gates.
- Decision: (b). Generated **content** stays reviewable in git; the deploy-time build (Phase 2)
  only bundles code. Exception candidates (the SQLite index) are owner decisions (STATUS.md #4).
