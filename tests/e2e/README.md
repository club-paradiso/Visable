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

## Procedure-first search, Waymaker Quick Answer, language control (2026-09)

Three specs cover the search sprint and run in CI (`landing-restoration-e2e`,
projects desktop-1280 / tablet-768 / mobile-390 / mobile-320):

- `procedure-first-search.spec.mjs` — `외국인등록증 재발급` (and its Korean/English
  phrasings) never dead-ends on "체류자격을 찾지 못했어요"; reason chips move only the
  existing-card item; fees render in the fee section, never as a document; the
  status question for `체류기간 연장`; collapsed evidence still opens the page;
  concise disclaimer; report dialog; Jeju office variation stays an unverified report.
- `waymaker-quick-answer.spec.mjs` — deterministic Quick Answer for question-form
  queries, collapsed full guidance, fee mode without a model call, AI rewrite
  accepted only when validated (hallucinated text rejected, honest note), 404 /
  NOT_CONFIGURED silent, follow-up handoff prefills `ai.html`.
- `language-control.spec.mjs` — 15 native-name languages, filter, Escape/focus,
  popover vs bottom sheet, English/Arabic (RTL) application, `?lang=` bootstrap,
  storage persistence, New Home selector untouched.

```bash
PARADISO_PW_EXECUTABLE=/path/to/chromium npx playwright test tests/e2e/procedure-first-search.spec.mjs tests/e2e/waymaker-quick-answer.spec.mjs tests/e2e/language-control.spec.mjs --project=desktop-1280 --project=mobile-320
```

## Landing boot, journey state machine, Waymaker / New Home entries (2026-09-23)

`landing-boot.spec.mjs` runs in CI (`landing-restoration-e2e`, desktop-1280 / mobile-390 / mobile-320):

- first paint: an init script samples every animation frame from the earliest
  moment the page can run script and asserts the legacy hero / top controls are
  never displayed (fast and throttled connection), `body.civic-refresh` is present
  from the first frame, the civic shell stays visible once parsed and cumulative
  layout shift stays low;
- the static shell in `index.html` is reused by `civic-search.js`
  (`data-cs-hydrated="reused"`), a failed civic script load shows the reload row;
- journey: CLOSED → PRE → CLOSED (second click) → POST → PRE, keyboard Enter/Space,
  Escape, `aria-expanded` / `aria-controls`, focus returns to the trigger, the panel
  sits under the triggers, the directory entry routes through the same state, a
  language change keeps the open track and re-renders it;
- Waymaker and New Home are visible core tools with ≥44 px targets, navigate to
  `ai.html` / `new-home.html`, and Back restores the landing.

```bash
PARADISO_PW_EXECUTABLE=/path/to/chromium npx playwright test tests/e2e/landing-boot.spec.mjs --project=desktop-1280 --project=mobile-390
```

## Form Helper 2.0 (2026-09-23)

`form-helper.spec.mjs` runs in CI (`landing-restoration-e2e`, desktop-1280 / mobile-390 / mobile-320):

- home search resolves the brief's examples (주소 변경 → 체류지변경신고서, 통합신청서, 숙소 제공,
  신원보증, F-4 거소신고); 난민 / 출국기한유예 forms only ever appear as catalog entries with
  the "이 서류는 Visable 자동작성 대상이 아니에요" hand-off, never as fillable forms;
- select → explain → fill → browser Back keeps the values → review → preview → export; the
  ops drawn on the preview canvas are the ops written into the PDF (`VisableFormHelper.lastExport`);
  no request leaves the origin apart from the font CDN;
- the downloaded file name is asserted exactly (`NGUYEN VAN ANH_체류지변경신고서.pdf`), both
  from the browser's download event and from `VisableFormHelper.lastExport.filename`;
- a too-long value is flagged in the field, on the review screen and again in the export
  dialog ("그래도 내려받기" / "고치기"); the reset `<dialog>` warns before clearing;
- Waymaker deep links (`?form=F01&type=sojourn_extension`) preselect the application type;
  edition switches (F01 ↔ F03 중문 병기) keep the data; EN chrome and Arabic RTL work with
  the Korean official field names still visible; the flow is keyboard reachable;
- primary actions and the current step number keep a WCAG contrast of at least 4.5 : 1 in the
  light and the dark theme, and screen transitions are off under `prefers-reduced-motion`.

The offline twin is `scripts/check_form_helper.mjs` (in `check_repo.sh`): inventory /
coverage freshness, exclusions, template sha256 / page / size drift, schema ↔ definition
consistency, engine unit tests, a Node export of every sample verified with PyMuPDF
(`scripts/forms/verify_export.py`) — the same vendor pdf-lib / fontkit files the browser uses —
and a static geometry audit of **every** overlay (`scripts/forms/audit_overlay_geometry.py`:
bounded width, no table rule / printed label inside the writable area, no run past the row end),
which is itself tested against planted defects.

**Browser locale.** Chromium on Linux converts a suggested download name to the process's
native multibyte charset; under the POSIX/C locale every non-ASCII name degrades to
`download`. `playwright.config.mjs` therefore launches the browser with `LANG` / `LC_ALL =
C.UTF-8` unless the environment already selects a UTF-8 locale — the filename assertion stays
strict instead of accepting the fallback.

```bash
PARADISO_PW_EXECUTABLE=/path/to/chromium npx playwright test tests/e2e/form-helper.spec.mjs --project=desktop-1280 --project=mobile-390 --project=mobile-320
node scripts/check_form_helper.mjs            # add --record-qa to write support.qa into data/form_schemas.json
```
