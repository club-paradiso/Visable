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
- `specs/visual.spec.mjs` — screenshots (visual-* projects only)

CI: `.github/workflows/golden.yml` runs the suite on every pull request against a
local static server, against the Vercel preview when a deployment becomes ready
(needs the bypass secret), and on demand against any URL.
