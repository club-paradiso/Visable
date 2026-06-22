# Complex status guide — real-browser QA (Playwright)

Real-browser regression suite for the complex status guide (F-4 + F-6/G-1/E-7/
F-5/D-2/D-4). It complements the **offline** CI guard
`scripts/check_complex_status_guide_qa.mjs` (run in `bash scripts/check_repo.sh`)
by covering what only a browser can: actual rendering, viewport
overflow/clipping, overlay sizing, focus, keyboard, and theme rendering.

## Why this is not in CI

CI runs only `bash scripts/check_repo.sh` on a runner with **no browser binary**,
and this repo is a deliberate no-build static site. Adding a Chromium download +
browser run to every PR would be heavy and network-dependent. So the **offline
harness is the CI regression guard**; this Playwright suite is for local / manual
real-browser QA (or a separate browser-capable workflow if the team adds one).

> Honesty note: this suite was authored from the verified rendered
> strings/selectors but **could not be executed in the build sandbox** — the
> Playwright browser CDN (`cdn.playwright.dev`) is blocked by network egress and
> there is no system browser. Treat the first local run as the verification step.

## Run it

```bash
npm install                      # installs @playwright/test (devDependency)
npx playwright install chromium  # one-time browser download
npm run test:e2e                 # all viewport projects
# or a single viewport:
npx playwright test --project=mobile-390
```

The config (`playwright.config.mjs`) starts a static server (`python3 -m
http.server`) over the repo root; `index.html` falls back to the committed
`visa_data.json` / `doc_master.json` when the backend API is absent, so the guide
is fully functional offline.

## Coverage

- **All 7 statuses × 5 viewports** (1280 / 768 / 430 / 390 / 360): recommended-
  start block + document-checklist CTA visible, ≥44px touch target, no horizontal
  overflow.
- **F-4 + F-6 deep flow × 5 viewports**: keyboard-open the guide, assert a
  wide/full-screen overlay (not a tiny modal), one question per step, walk to the
  checklist-first result (먼저 해야 할 일 / 기본 준비서류 / 신청 절차 / 공식 근거), ESC close +
  focus restore to the CTA.
- **Themes**: civic_editorial + archive_diary render the F-6 guide with a real
  (theme-token) surface background.

## Reduced matrix / cost

Per-status block smoke runs on every viewport; the deep flow runs only for F-4 +
F-6 (the strongest implementations) to keep runtime reasonable. Extend the deep
flow to G-1/E-7/F-5/D-2/D-4 as their data matures.
