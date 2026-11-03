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

## ADR-008 — Phase 2 build: Vite multi-page, staged (classic scripts stay classic until Phase 3)
- Date: 2026-11-03 (design; implementation starts after Phase 1 exit)
- Context: 12 HTML pages, all asset references relative (`assets/…`, `data/…`, `scripts/…`), no
  `<base>`, no absolute `/` paths (verified by grep). index.html loads 24 classic
  `<script src>` IIFEs that publish globals, 2 `type="module"` scripts, 8 CSS files with
  `?v=` cache busters, and 11 inline scripts. Legacy checks load `assets/js/*.js` with
  `new Function`/`vm` and therefore need them to stay IIFE sources (phase0-legacy-checks.md §D).
  Vite processes `<script type="module">` and `<link rel="stylesheet">` in HTML entries; it
  leaves classic `<script src>` and inline classic scripts untouched (and does not copy their
  files unless they are static assets).
- Options: (a) convert every classic script to an ES module in Phase 2 (big-bang; breaks the
  `new Function` checks and the implicit-global contracts the CI e2e specs rely on, §G);
  (b) Vite MPA now, with classic scripts and all `data/`, `scripts/*.mjs`-loaded-as-URL,
  `docs/source-manuals/<current>` PDFs, `assets/forms`, `assets/manual-reader` copied as static
  files to their public paths; CSS and the two module scripts become hashed bundles; classic
  scripts are converted one by one in Phase 3 and gain hashing as they move; (c) no bundler.
- Decision: (b). Static copies keep every public URL (data JSON, PDFs, `scripts/*.mjs` loaded by
  `import()` at runtime) byte-identical; `vercel.json` headers for `/assets/js/civic-search.js`
  and `/assets/css/civic-search.css` keep working because those files are still served at the
  same paths until Phase 3 hashes them (then the header rules are updated in the same commit).
  Golden suite runs against `dist/` via `GOLDEN_SERVE_DIR=dist` locally and in CI; the Vercel
  build command becomes `npm run build` with `outputDirectory: dist`.
- Measured constraint: npm registry reachable (vite 8.3.5, typescript 7.0.2 available).
- Risks to verify in Phase 2: Vite's handling of `href="assets/css/x.css?v=…"` (query on a
  local asset), Google Fonts `media="print" onload=` links (external, untouched), the static
  landing shell equality check (`check_landing_shell.mjs` must run against the built
  `dist/index.html` or the source — decide when wiring), and `.vercelignore` vs. build inputs
  (`tests/`, `.github/` are not build inputs; `scripts/` is).

### ADR-008 addendum (2026-11-03, after the first build)
- Observed: Vite merged index.html's 8 local stylesheets into 3 hashed chunks and reordered them
  (`visable-product-2026.css` moved from first to second), and minified the 6 inline `<style>` blocks
  (14,511 differing lines). The golden suite still passed (it asserts text, not style), which is exactly
  why this is not acceptable as a behaviour-preserving step.
- Decision: a `transformIndexHtml` pre-plugin marks every local stylesheet link `vite-ignore` so the CSS
  stays raw, separate and in order; `build.cssMinify: false` keeps inline CSS unminified; `assetsInlineLimit: 0`
  keeps images as files. Hashing is applied in Phase 2 only to the `type="module"` scripts and to image
  assets referenced from HTML/CSS (the raw copies under `assets/` also stay, so old URLs keep working).
  CSS hashing moves to Phase 4, where the visual baselines are the gate.

## ADR-009 — Phase 3 extraction mechanics: ES modules under src/, one `window.Visable` bridge
- Date: 2026-11-03
- Context: index.html's main inline block (lines 16104–26318) is a classic script that runs at
  parse time and shares ~487 functions and many `const` data tables through the global scope with
  24 classic `assets/js` scripts, 4 inline shims and the e2e specs (phase0-legacy-checks.md §G).
  ES modules are always deferred and have their own scope, so extracted code cannot simply be
  "moved" without an explicit hand-off.
- Options: (a) extract into classic scripts (keeps globals, defeats the goal); (b) ES modules plus
  dozens of ad-hoc `window.x = …` globals (violates "no new globals"); (c) ES modules under `src/`
  bundled by Vite, exposing exactly one bridge object `window.Visable` during the transition,
  with the inline code delegating to it function by function.
- Decision: (c). `src/main.js` is the single module entry for index.html; it imports the extracted
  modules and assigns `window.Visable = { data, state, render, … }` (one global, documented, removed
  or frozen in Phase 7). Inline functions are first turned into thin delegations
  (`function fetchJson(url) { return Visable.data.fetchJson(url); }`), the golden suite runs, then
  the inline function is deleted once nothing calls it. Timing is safe because every data load,
  storage read and render happens in `DOMContentLoaded`/event handlers (verified in the structure
  map), which fire after module scripts execute; anything found to run at parse time stays inline.
  The compatibility surface the e2e specs and `assets/js` scripts use (`VISA_DATA`, `renderResults`,
  `executeSearch`, `applyLanguage`, `openVisaDrawer`, `tx`, `escapeHtml`, `API_BASE`, …) stays on
  `window` until Phase 7, each removal recorded.
- Typing: TypeScript 7.0.2 with `tsconfig.json` scoped to `src/**` (`allowJs`, `checkJs`, `strict`);
  new modules are `.ts` where they have a stable contract (data layer, state layer), `.js` with JSDoc
  where they are moved legacy code. `npm run typecheck` gates CI alongside the golden suite.
- Order (brief): data loading → state/storage (with key migration = keep every existing key name
  unchanged; no renames) → rendering helpers (escaping) → features, lowest coupling first.

## ADR-010 — Phase 3 modules are plain ES modules with JSDoc types, not `.ts`
- Date: 2026-11-03
- Context: the brief prefers `.ts` for new modules. The first data-layer modules were written as
  `.ts`; the build and the golden suite against `dist/` passed. But the legacy CI jobs
  (repo-validation.yml `landing-restoration-e2e`, `webkit-e2e`, mobile QA; immigration-checklists
  workflow) and `playwright.config.mjs` serve the **source tree** with `python3 -m http.server`,
  with no build step. A `<script type="module" src="src/main.js">` that imports `.ts` files fails
  in a browser served that way, so every inline delegation to the bridge would break those jobs.
- Options: (a) rewrite every legacy CI job and config to build first (touches workflows the brief
  told Phase 0 to leave alone, and makes the repo un-runnable without a build); (b) `.ts` plus a
  committed compiled copy (two sources of truth); (c) `.js` ES modules with `// @ts-check` + JSDoc,
  type-checked by `tsc` (`checkJs`, `strict`) — runnable natively from the source tree and bundled
  by Vite in production.
- Decision: (c) for Phase 3–5. `npm run typecheck` runs in `golden-local` before the build. `.ts`
  can be adopted file by file once the legacy jobs serve `dist/` (Phase 7 decision).
- Evidence: with `.js` modules the golden suite passes both against the source tree (100 passed)
  and against `dist/` (100 passed); `window.Visable.data` is present when served from source.
