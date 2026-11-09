# Golden suite (tests/golden)

The behaviour contract for the frontend rebuild (docs/rebuild/). It covers every
feature tagged Critical in docs/rebuild/phase0-inventory.md, every shipped UI
language (14 packs + zh-TW), desktop (1280×900) and phone (390×844), the
fail-closed paths, and visual baselines for key screens.

Rules
- Assertions are on user-observable outcomes only: rendered text, roles and
  labels, URL/hash state, which notices appear. Never on DOM structure a refactor
  may change. Interaction locators may use the public control ids (`#civicQuery`,
  `#q`) and `data-*` hooks that already exist.
- Every expected value comes from a committed data file (`data/i18n/*.json`,
  `visa_data.json`, `data/status-guidance-202609.json`, `data/form_definitions.json`,
  `data/manual-reader/catalog.json`, …) or from `fixtures/guidance-strings.mjs`,
  which records the strings the site renders today with their source lines.
  Nothing is invented.
- Features that need live keys or a backend (Waymaker `/api/ask`, enforcement
  analysis, operator studios, live JUSO search) are marked **BLOCKED** with
  `test.fixme`; only their offline fail-closed behaviour is asserted.
- `/api/**` is aborted by default so the suite proves the site stays grounded on
  its static data.

Run
```bash
npm install --ignore-scripts --package-lock=false
npm run test:golden                       # local static server over the repo root
GOLDEN_SERVE_DIR=dist npm run test:golden # later phases: the build output
GOLDEN_BASE_URL=https://<preview>.vercel.app npm run test:golden   # a deployment
# sandbox without a downloadable browser:
PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium npm run test:golden
# visual baselines (generated/compared on the CI runner, ADR-005):
npm run test:golden -- --project=visual-desktop --project=visual-mobile
```

Vercel previews are behind SSO. Set `VERCEL_AUTOMATION_BYPASS_SECRET` (Protection
Bypass for Automation) to run against them; the config sends it as
`x-vercel-protection-bypass`.

Layout
- `playwright.golden.config.mjs` (repo root) — projects desktop-1280, mobile-390, visual-desktop, visual-mobile
- `helpers/data.mjs` — Node-side loaders for expected values
- `helpers/page.mjs` — boot/search/text helpers
- `fixtures/guidance-strings.mjs` — recorded guidance copy (ko/en) with provenance
- `specs/home.spec.mjs` — home in all 15 languages, language dialog, tool entries
- `specs/search.spec.mjs` — status search, subcodes, unknown codes, `?q=`, guidance language
- `specs/procedure.spec.mjs` — documents, fees, conditions, uncertainty notices
- `specs/fail-closed.spec.mjs` — missing data/scripts/AI, hallucination rejection
- `specs/pages.spec.mjs` — manual, form helper, checklists, new-home, preview, ai, enforcement, studios
- `specs/tools.spec.mjs` — employment code finder (canonical dataset, occupation lookup)
- `specs/reminders.spec.mjs` — deadline reminders (seeded storage, banner, dialog, save)
- `specs/finders.spec.mjs` — registered-agent and designated-hospital finders
- `specs/jurisdiction.spec.mjs` — 관할 출입국 finder (시·도 → 시·군·구 → office)
- `specs/legacy-card.spec.mjs` — the legacy per-status result card behind "기존 체류자격 카드 보기": header, subcodes, procedure tabs, extension documents (ko); English keyword query → empty state
- `specs/visual.spec.mjs` — 14 screenshots (visual-* projects only): home ko/en/dark/archive theme, settings overlay, D-2 guidance, D-2 legacy card (extension tab), job-code modal, manual, form helper, checklists, new-home, ai shell. CI generates baselines on its runner (ADR-005); Phase 4 compares locally against baselines generated right before each CSS step (ADR-011).

CI: `.github/workflows/golden.yml` runs the suite on every pull request against a
local static server, against the Vercel preview when a deployment becomes ready
(needs the bypass secret), and on demand against any URL.

## Readiness
`boot()` waits for the search field, for `#civicLanding[data-cs-hydrated]` to leave `static`, and for the first `paradiso-language-applied` event (the bootstrap fires it after the i18n packs load; civic-search re-renders the landing in its handler). Typing before that event can hit the element being replaced — this was the only flake the suite has shown.

`boot()` also pins `Math.random` to a seeded generator (mulberry32) before any page script runs. The home's example chips are four random picks from a pool (`selectExamples` in `assets/js/civic-search.js`); different picks wrap onto a different number of rows in some themes and shifted the full-page visual baselines. Element and viewport shots did not need this; it is applied uniformly so every run renders the same chips.

## Baseline sets (ci / local)

`snapshotPathTemplate` puts screenshots under `tests/golden/__screenshots__/<set>/…` where `<set>` is `ci` when `CI` is set and `local` otherwise (`GOLDEN_SNAPSHOT_SET` overrides). The `ci` set is generated on the GitHub runner's Chromium the first time the `golden-visual` job runs on a branch of this repository and is committed back to the PR branch by that job; from then on it is compared, never regenerated. The `local` set belongs to the machine that made it (a different Chromium renders text a few pixels apart) and is git-ignored. Local workflow for a CSS step: generate the `local` set from a pristine worktree of the base commit, apply the change, compare.

