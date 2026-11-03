// Golden visual baselines for key screens. Runs only in the visual-* projects.
// Baselines are generated and compared on the CI runner (ADR-005); external
// fonts are blocked so rendering does not depend on CDN availability.
import { test, expect } from '@playwright/test';
import { boot, search, guidanceHeading } from '../helpers/page.mjs';

const FONT_CDNS = ['**/fonts.googleapis.com/**', '**/fonts.gstatic.com/**', '**/cdn.jsdelivr.net/**'];
const blockFonts = FONT_CDNS.map((p) => [p, (route) => route.abort()]);

test('home (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('home-ko.png', { fullPage: false });
});

test('D-2 extension guidance (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await search(page, 'D-2 체류기간 연장');
  await expect(guidanceHeading(page, 'D-2 체류기간 연장')).toBeAttached();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('d2-extension-ko.png', { fullPage: false });
});

test('manual reader home', async ({ page }) => {
  await boot(page, { path: '/manual.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('manual-home.png', { fullPage: false });
});
