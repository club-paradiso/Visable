// WebKit (Safari engine) run of the real-browser suites, for CI (repo-validation.yml → webkit-e2e).
// The pre-installed Chromium executable override does not apply to WebKit, so launchOptions is reset.
//   npx playwright install --with-deps webkit
//   npx playwright test -c playwright.webkit.config.mjs
import { defineConfig } from '@playwright/test';
import base from './playwright.config.mjs';

export default defineConfig({
  ...base,
  use: { ...base.use, launchOptions: { env: base.use.launchOptions && base.use.launchOptions.env } },
  projects: [
    // the whole suite at iPhone width, touch and mobile viewport like Safari on iOS
    { name: 'webkit-iphone-390', use: { browserName: 'webkit', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    // desktop Safari for the layout-sensitive specs
    { name: 'webkit-desktop-1280', use: { browserName: 'webkit', viewport: { width: 1280, height: 900 } },
      testMatch: ['**/overlay-anchoring.spec.mjs', '**/restore-trust.spec.mjs', '**/language-control.spec.mjs', '**/result-hierarchy.spec.mjs', '**/landing-boot.spec.mjs', '**/search-first-home.spec.mjs'] },
  ],
});
