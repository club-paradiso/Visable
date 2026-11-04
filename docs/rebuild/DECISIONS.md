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

### ADR-009 correction (2026-11-03, from docs/rebuild/phase3-structure-map.md §2)
- The claim "every data load, storage read and render happens in DOMContentLoaded/event handlers"
  is **wrong** for: `initCity` (reads/writes `paradiso_city` at parse time), `globalEasyMode`
  (reads `paradiso:easyMode`), `I18N_DEV_WARNINGS` (reads `paradiso:i18n-debug`), the agent and
  medical finder IIFEs (fetch at parse time), the reminders IIFE (reads storage, renders), the
  scroll-reveal and anagram IIFEs, and the global-settings shim. The module entry runs after the
  whole document is parsed, so **parse-time code cannot call `window.Visable`**. Rule: parse-time
  code stays inline until a step deliberately defers it with a visual-golden check. The two finder
  fetch sites that were delegated in the first D2 pass were reverted to raw `fetch` for this reason.

### ADR-009 addendum (2026-11-03, job-code finder move)
- **Legacy checks that slice index.html by source markers are rewritten to slice the module file**
  (`// --- Job Code Modal · HiKorea` → `\nexport {`) rather than kept alive with a copy of the code in
  index.html. A module that is plain script apart from its trailing `export {…}` block evaluates in the
  `vm` sandbox exactly as the inline slice did, so the checks still exercise the real functions. The
  marker string is deliberately **not** repeated in index.html, so any other slicer finds nothing and
  fails loudly instead of silently testing an empty region.
- **Dynamic `import()` inside moved code is resolved against the document.** Inside the inline classic
  script `import('./scripts/x.mjs')` resolved against `/index.html`; inside `src/features/*.js` it would
  resolve against the module and Vite would bundle it. Moved code uses
  `import(/* @vite-ignore */ new URL('scripts/x.mjs', document.baseURI).href)`, which keeps the request
  URL and the lazy timing identical (checked in the built bundle). This is the one non-verbatim edit
  allowed in a "verbatim move", and it is called out in the module header.
- **DOMContentLoaded wiring that assigns a cluster's state moves with the cluster** as an exported
  `wire*()` function that the inline handler calls at the same position, so the state stays
  module-private and no new global is introduced.

### ADR-009 addendum 2 (2026-11-03, normalisation clusters)
- **Stub shape:** inline delegating stubs are `function name(...args) { return Visable.docs.name(...args); }` —
  one line each, generated from the list of moved functions that are still referenced outside the moved
  range (computed by word-boundary search over the rest of index.html plus the runtime `typeof` guards in
  assets/js and tests/e2e). Functions referenced only inside the moved range get no stub.
- **Legacy slicers that brace-match a function by name read a corpus with the module FIRST**
  (`read(module) + '\n' + read('index.html')`), because the stub in index.html has the same
  `function name(` signature and a slicer that scans index.html first would silently test the
  one-line stub. Slicers that look for a single literal read the module alone.
- **One module per cluster group, not the four-file split** suggested in the structure map (same as the
  job-code decision): cross-references inside the group are by bare name, which only one module scope can
  keep verbatim. Splitting is a follow-up refactor once the stubs are gone.

### ADR-009 addendum 3 (2026-11-03, cross-module bare names)
- Moved code resolves the names it calls through the global object (window functions / global lexical
  scope). A function that moved to module B is **not** visible to module A by bare name, even though it was
  when both were inline. Therefore the inline stub set for a move must include every moved function that
  any *other extracted module* references, not only those index.html references. The mover scans
  `src/**/*.js` for this; the golden suite is the safety net (it caught the first miss before commit).
- Once the stubs are gone (end of Phase 3), these cross-module references become explicit `import`s; until
  then the stubs are the documented seam.

### ADR-009 addendum 4 (2026-11-03, DOMContentLoaded registration stays inline)
- The three inline shims (`DETAIL_CODE_RESOLVER_SHIM_2026_05`, `DOC_SECTION_UNIFICATION_SHIM_2026_05`,
  `DOC_TERM_FEE_UI_SHIM_2026_05`) and the global-settings block register their own `DOMContentLoaded`
  handlers while the document is parsed. The main bootstrap handler used to be registered earlier in
  the same parse, so it ran first. A module registers only after parsing, i.e. after the shims, which
  would reverse that order. Decision: the handler body moves to `src/boot.js` as the exported
  `onDomReady()`, and index.html keeps a one-line parse-time registration that calls it. Listener
  order is unchanged; the body is verbatim. This is the one inline statement Phase 3 adds on purpose.

### ADR-009 addendum 5 (2026-11-03, module-evaluation time vs. the bridge)
- `src/main.js` builds `window.Visable` *after* its static imports have evaluated. Feature modules that run
  code at import time (reminders, finders, landing animation — the former parse-time IIFEs) therefore
  execute before the bridge exists. Any inline stub they call at that moment throws `ReferenceError:
  Visable is not defined`. Today this is safe by construction: the finders call nothing until their
  fetch resolves; the reminders IIFE wraps `tx()` in try/catch and falls back to its own labels, which
  is also what happened before the move (at parse time `tx()` returned the key). Rule: a module that
  runs at import time must not depend on a stub, and the test for it is the golden suite's page-error
  assertion plus the reminders spec. The clean fix (bridge before side-effect imports) is a Phase 7 item.

### ADR-009 addendum 6 (2026-11-04, shims and the end of Phase 3)
- The three DOM-patching shims keep a parse-time `DOMContentLoaded` registration in index.html (same
  mechanism as the main bootstrap, addendum 4); their bodies are modules exporting the install function.
  The global-settings block has no first-paint effect and runs at module evaluation instead of parse time.
- What stays inline, and why it is not "logic": the state owners and data tables that assets/js, the e2e
  specs and legacy scripts read by bare name or regex-parse from index.html; the four first-paint scripts;
  the parse-time initialisers; and 193 one-line stubs. Retiring the stubs means every caller imports the
  module (and the e2e/assets/js callers get a stable surface); moving the state owners means a data-flow
  redesign. Both are behaviour-affecting and belong to a later phase, not to this behaviour-preserving one.

## ADR-011 — Phase 4 CSS: verbatim extraction first, local visual baselines per step
- Each inline `<style>` block becomes a stylesheet linked at the same position, so the cascade is
  unchanged; relative `url()`s are rewritten for the new directory; the critical first-paint block
  stays inline. Only after that do tokens, dead rules and `!important` get touched, one step each.
- CI generates visual baselines on its own runner (ADR-005) and cannot compare across commits until
  the owner commits baselines (owner decision 3). Phase 4 therefore compares each step locally against
  baselines generated on the same Chromium immediately before the step, fonts blocked, 14 states × 2
  viewports. Those files are excluded via `.git/info/exclude`, never committed by this session.
- Legacy checks that regex CSS from index.html read the shared source list
  (`scripts/frontend_modules.json`, key renamed to `sources`, now modules + stylesheets, then
  index.html). Checks about document order (tab order, skip link) keep reading the raw document.

### ADR-011 addendum 1 — inline style attributes and deterministic visual runs
- Static `style="…"` attributes become id-scoped rules in one stylesheet linked last; the selector
  specificity is lower than the attribute's, but nothing else targets those ids with the same
  properties (checked by grep before the move), and the visual comparison is the proof. Attributes a
  script toggles through `element.style` stay inline: moving them would change what the script's
  first toggle does (an inline `display:none` removed by `style.display=''` reveals the element; a
  stylesheet rule would not), which is behaviour.
- The golden harness pins `Math.random` to a seeded generator. The alternative — waiting for the chips —
  does not help because the content itself is random; pinning it keeps the product code untouched and
  makes every golden run render the same chips. Documented in tests/golden/README.md.

### ADR-011 addendum 2 — tokens.css is a verbatim move, not a DESIGN.md re-derivation
- The brief asks for design tokens from DESIGN.md. DESIGN.md itself states that its colour values are a
  transcription of the civic token layer in the shipped CSS and that the CSS wins on any difference. So
  the tokens file is that layer moved verbatim, with the DESIGN.md name → CSS variable mapping written in
  the file header; no value changes, and the WCAG floor check (`check_civic_tokens.mjs`) keeps reading the
  same declarations through the shared source list.
- Blocks that mix custom properties with ordinary declarations stay in index-base.css rather than being
  split, because splitting a block is not a verbatim move and the visual baseline cannot prove the two halves
  equivalent under every theme/skin combination.

### ADR-011 addendum 3 — `!important` reduction is limited to removals that are sound without a full-site visual oracle
- Dropping an `!important` changes the winner wherever another rule sets the same property on the same
  element with higher specificity or later order. Which elements carry which classes is partly decided at
  runtime (civic-search, the renderers, skins), so no static analysis can prove a removal harmless, and the
  38-state visual baseline covers the default skin only. A broad `!important` sweep would therefore be a
  behaviour change verified by sampling, which this phase does not do.
- What is sound: removing the earlier copy of an exact duplicate rule (same at-rule context, selector text,
  declarations). The later copy wins in every situation the earlier one did, so the cascade is unchanged
  for every element, theme and skin. That is the reduction applied (27 `!important`); the rest is counted
  and left for a later, design-led pass with per-skin baselines (listed under Owner decisions needed).

## ADR-012 — Phase 5: other pages move inline scripts to external classic scripts, not modules
- The brief prefers ES modules, and index.html got them (ADR-009) because its bootstrap already ran on
  DOMContentLoaded and the parse-time pieces could stay inline. The other pages are different: ai.html's
  2,714-line block runs synchronously at parse time, computes constants from globals that later classic
  scripts define (`API_BASE` reads `window.VisableBackend`, loaded 2,700 lines later), and precedes
  deferred scripts (ui-pictograms, legal-source-search) that post-process what it renders; new-home.html's
  IIFE runs at the end of the body before its deferred scripts. A module script is deferred, so moving
  either block into one reorders execution relative to those scripts and changes the values of
  parse-time constants. That is behaviour, not structure.
- An external classic `<script src>` at the same position executes synchronously at parse time in the
  same order, with the same global scope semantics (top-level `const`/`function` of a classic script are
  global either way). So Phase 5 moves each block verbatim to `assets/js/pages/<page>-<part>.js`, keeps
  the first-paint restores inline (same rule as index.html), and leaves module conversion for a phase
  that may change boot order under its own tests. Legacy checks that slice a page's source read a page
  corpus (`scripts/frontend_modules.json` → `pages`), modules first, like the index.html corpus.

