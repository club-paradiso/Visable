// Intermittent "search does nothing" regressions:
//   1. a hung /api/visas (cold backend) must not keep search locked — the app falls back to the
//      committed visa_data.json after a short timeout;
//   2. an IME composition that never sends compositionend must not swallow every later Enter.
import { test, expect } from '@playwright/test';

test('a hanging backend does not lock search: static data takes over within the timeout', async ({ page }) => {
  await page.addInitScript(() => { window.PARADISO_BACKEND_URL = location.origin; });
  await page.route('**/api/visas', () => { /* never answers: simulates a cold or hung backend */ });
  await page.route(/\/api\/(?!visas)/, (route) => route.abort());
  await page.goto('/index.html');
  await page.waitForFunction(() => { try { return dataReady === true && !document.getElementById('q').disabled; } catch (e) { return false; } }, null, { timeout: 12_000 });
  await page.fill('#civicQuery', 'D-2');
  await page.press('#civicQuery', 'Enter');
  await expect(page.locator('#rlist .vc[data-code="D-2"]').first()).toBeAttached({ timeout: 15_000 });
});

test('a stuck composition flag (no compositionend) does not swallow Enter', async ({ page }) => {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto('/index.html');
  await page.waitForFunction(() => { try { return dataReady === true && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30_000 });
  const input = page.locator('#civicQuery');
  await input.click();
  await input.fill('F-4');
  // compositionstart with no matching compositionend, then the IME goes quiet.
  await input.evaluate((el) => el.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true })));
  await page.waitForTimeout(1800);
  await page.press('#civicQuery', 'Enter');
  await expect(page.locator('#rlist .vc[data-code="F-4"]').first()).toBeAttached({ timeout: 15_000 });
});
