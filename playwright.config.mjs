// Playwright config for the complex-status-guide real-browser QA suite.
//
// This is intentionally NOT part of `bash scripts/check_repo.sh` / CI: CI has no
// browser binary and the repo is a no-build static site. Run it locally in a
// browser-capable environment:
//
//   npm install                      # installs @playwright/test (devDependency)
//   npx playwright install chromium  # one-time browser download
//   npm run test:e2e
//
// The webServer below serves the repo root statically; index.html falls back to
// the committed visa_data.json / doc_master.json when the backend API is absent,
// so the guide is fully functional offline.
import { defineConfig } from '@playwright/test';

const PORT = Number(process.env.PARADISO_E2E_PORT || 4173);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    headless: true,
    screenshot: 'only-on-failure',
    // In environments that ship a pre-installed Chromium whose build differs from
    // the @playwright/test pin, point at it via PARADISO_PW_EXECUTABLE instead of
    // downloading (e.g. /opt/pw-browsers/chromium-XXXX/chrome-linux/chrome). When
    // the env var is unset, Playwright uses its own managed browser as usual.
    launchOptions: process.env.PARADISO_PW_EXECUTABLE
      ? { executablePath: process.env.PARADISO_PW_EXECUTABLE }
      : {}
  },
  webServer: {
    command: `python3 -m http.server ${PORT}`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  },
  // Viewport matrix: full set for the deep flow on F-4/F-6; the per-status block
  // smoke runs on every project too (cost is acceptable for a local/manual run).
  projects: [
    { name: 'desktop-1280', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'tablet-768', use: { viewport: { width: 768, height: 1024 } } },
    { name: 'mobile-430', use: { viewport: { width: 430, height: 932 } } },
    { name: 'mobile-390', use: { viewport: { width: 390, height: 844 } } },
    { name: 'mobile-360', use: { viewport: { width: 360, height: 780 } } }
  ]
});
