// Golden suite config (docs/rebuild/phase0-inventory.md, tests/golden/README.md).
//
// The golden suite is the behaviour contract for the frontend rebuild: every
// Critical feature, every shipped UI language, desktop and mobile, with
// assertions on user-observable outcomes only (text, roles, labels, URL state,
// which notices appear). It runs against:
//   * a local static server over GOLDEN_SERVE_DIR (default: repo root; later
//     phases point it at the build output), or
//   * GOLDEN_BASE_URL (a Vercel preview or production URL) when set.
//
// Local sandbox: PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium when the
// Playwright-managed browser cannot be downloaded (see DECISIONS.md ADR-002).
import { defineConfig } from '@playwright/test';

const PORT = Number(process.env.GOLDEN_PORT || 4310);
const SERVE_DIR = process.env.GOLDEN_SERVE_DIR || '.';
const REMOTE = !!process.env.GOLDEN_BASE_URL;
const BASE_URL = (process.env.GOLDEN_BASE_URL || `http://127.0.0.1:${PORT}`).replace(/\/$/, '');

const UTF8_LOCALE = /utf-?8/i.test(process.env.LC_ALL || process.env.LC_CTYPE || process.env.LANG || '');
const BROWSER_ENV = UTF8_LOCALE ? process.env : { ...process.env, LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' };

// Vercel deployment protection: previews are behind SSO (project setting
// ssoProtection=all_except_custom_domains). A Protection Bypass for Automation
// secret, when the owner provides one, is sent on every request.
const BYPASS = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
const extraHTTPHeaders = BYPASS ? { 'x-vercel-protection-bypass': BYPASS, 'x-vercel-set-bypass-cookie': 'true' } : undefined;

const desktop = { viewport: { width: 1280, height: 900 } };
const mobile = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 };

export default defineConfig({
  testDir: './tests/golden/specs',
  timeout: 90_000,
  expect: { timeout: 15_000, toHaveScreenshot: { maxDiffPixelRatio: 0.02, animations: 'disabled', caret: 'hide' } },
  fullyParallel: true,
  retries: 0,
  workers: process.env.CI ? 2 : 4,
  reporter: process.env.CI ? [['list'], ['junit', { outputFile: 'test-results/golden-junit.xml' }]] : [['list']],
  outputDir: 'test-results/golden',
  snapshotPathTemplate: 'tests/golden/__screenshots__/{projectName}/{testFileName}/{arg}{ext}',
  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    extraHTTPHeaders,
    launchOptions: {
      ...(process.env.PARADISO_PW_EXECUTABLE ? { executablePath: process.env.PARADISO_PW_EXECUTABLE } : {}),
      env: BROWSER_ENV
    }
  },
  webServer: REMOTE ? undefined : {
    command: `python3 -m http.server ${PORT} --bind 127.0.0.1 --directory ${SERVE_DIR}`,
    url: `${BASE_URL}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  },
  projects: [
    { name: 'desktop-1280', use: desktop, testIgnore: /visual\.spec\.mjs/ },
    { name: 'mobile-390', use: mobile, testIgnore: /visual\.spec\.mjs/ },
    // Visual baselines live in tests/golden/__screenshots__/<project>/ and are
    // generated on the CI runner (fonts differ between machines; ADR-005).
    { name: 'visual-desktop', use: desktop, testMatch: /visual\.spec\.mjs/ },
    { name: 'visual-mobile', use: mobile, testMatch: /visual\.spec\.mjs/ }
  ]
});
