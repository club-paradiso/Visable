# Test results — Restore Trust (2026-10-28)

**Environment.** Linux container, Node 22, Python 3.13, Chromium 1243 (pre-installed) driven by @playwright/test 1.64.1. The site was served locally with `python3 -m http.server` over the repo root, with `/api/**` aborted so the offline fallbacks are exercised. Production was not driven directly (U-8).

## Repo gate

| Command | Result |
|---|---|
| `bash scripts/check_repo.sh` | **exit 0**. Backend 99/99 modules, NEW 0. The first run in a bare container needs `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`. The `[11/14]` deploy-copy check caught the rebuilt bundle; it passed after `python3 scripts/sync_visa_data.py` |

## Node suites

| Command | Result |
|---|---|
| `npm run test:status-guidance` | all OK: manifest 501, documents 1126, resolver 63, **grid audit 0 mismatches** (old resolver: 172 understated / 16 overstated), **evidence audit OK** (old search: cross-manual pages in every procedure case), router 32, suggest 1251, physical form 748, fees 33, local practice 11, quick answer 24, unification 38, **result hierarchy 11/11** (5/11 on main before the fixture port) |
| `npm run test:search-tools` | passed |
| `npm run test:legal-search` | 313/313, 68/68 |
| `npm run test:unified-search` | 81 |
| `npm run test:current-manuals` | OK |
| `npm run test:manual-reader` | 2174 checks, 0 failed. The `--check` step needs `markdown-it-py` and `html5lib`; those were not installed here, so that step was not run |

## Browser (Playwright)

| Command | Result |
|---|---|
| `npx playwright test overlay-anchoring language-control` (6 projects) | 78/78 |
| `npx playwright test overlay-anchoring --project=desktop-1280` on the **pre-fix** JS | 6/7 failed, as expected |
| `npx playwright test result-hierarchy restore-trust` (6 projects) | 84/84 |
| `npx playwright test --project=desktop-1280 --project=tablet-768 --project=mobile-390 --workers=4` (final code) | **727 passed, 0 failed, 104 skipped** (conditional `test.skip` in existing specs), 14.5 min |
| Same, `--workers=6`, mid-change | `waymaker-quick-answer.spec.mjs:131` failed under load in 2 of 2 runs. It passes 32/32 isolated (`--repeat-each=2`) on both base and fix (U-7) |
| `node scripts/browser_status_matrix.mjs` (all codes, batches of 10, 390×844) | 258 codes, 26 batches; 2,096 chips, 1,444 `원문 확인` badges, legend missing 0; 254 source-only answers opened, 230 cited a page and all 230 showed the preview, **verbatim mismatches 0**; **overflow 0**; **page errors 0**; `test-matrix.csv` |

Not run:

- the mobile-430/360/320 projects for the full suite (the new specs ran on all 6);
- WebKit (`playwright.immigration-webkit.config.mjs`);
- the pixel-baseline comparison (opt-in, `PARADISO_VISUAL=1`).

## Accessibility checks

- **Contrast.** Excerpt text and its title are at or above 4.5:1 in default, stamp, chrome and neon, on all 6 viewports (`restore-trust.spec.mjs`).
- **Language listbox keyboard.** Enter, ↑/↓, Home/End, Escape; focus returns to the trigger, including after the header re-renders.
- **ARIA.** `aria-expanded` follows the open state.
- **Touch targets** (≥44px) are unchanged; covered by `result-hierarchy.spec.mjs`.

## Security

- **XSS probe.** `?q=<img src=x onerror=…>"><svg onload=…> F-4`: the handler did not fire and no nodes were injected.
- **Escaping.** Every new string written to `innerHTML` (preview lines, title, note, `cite`) goes through `esc()`. Preview text comes from the committed corpus only; it doesn't come from user input or any network source.
- **No new endpoints, storage or prompts.**

## Performance (measured)

- **Chooser step** (Node, all 269 codes × 3): base 0.080 ms → fix 0.264 ms per step.
- **No extra requests.** The preview reuses the corpus that the related-source search already loads, through the same `load()` promise.
