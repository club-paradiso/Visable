// Golden visual baselines for key screens. Runs only in the visual-* projects.
// Baselines are generated and compared on the CI runner (ADR-005); external
// fonts are blocked so rendering does not depend on CDN availability. Phase 4
// (CSS) compares every step against baselines generated locally on the same
// Chromium before the step (see docs/rebuild/STATUS.md).
import { test, expect } from '@playwright/test';
import { boot, search, guidanceHeading } from '../helpers/page.mjs';

const FONT_CDNS = ['**/fonts.googleapis.com/**', '**/fonts.gstatic.com/**', '**/cdn.jsdelivr.net/**'];
const blockFonts = FONT_CDNS.map((p) => [p, (route) => route.abort()]);
const shot = (name, opts = {}) => ({ fullPage: true, ...opts });
// Per-viewer settings are stored before navigation (same keys the site uses).
const withStorage = (page, entries) => page.addInitScript((e) => { for (const [k, v] of e) { try { localStorage.setItem(k, v); } catch (_) {} } }, entries);

test('home (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('home-ko.png', { fullPage: false });
  await expect(page).toHaveScreenshot('home-ko-full.png', shot());
});

test('home (en)', async ({ page }) => {
  await boot(page, { query: { lang: 'en' }, routes: blockFonts });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('home-en-full.png', shot());
});

test('home, dark brightness (ko)', async ({ page }) => {
  await withStorage(page, [['paradiso:brightness', 'dark']]);
  await boot(page, { routes: blockFonts });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('home-ko-dark-full.png', shot());
});

test('home, archive_diary theme (ko)', async ({ page }) => {
  await withStorage(page, [['paradiso:editorial-theme', 'archive_diary']]);
  await boot(page, { routes: blockFonts });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('home-ko-archive-full.png', shot());
});

// The three optional skins (assets/js/visable-theme.js THEMES, stored under `visable:theme`, applied as
// html[data-vt]); the default skin is every other state. Added for the design-led CSS pass (owner decision 6).
for (const skin of ['stamp', 'chrome', 'neon']) {
  test(`home, ${skin} skin (ko)`, async ({ page }) => {
    await withStorage(page, [['visable:theme', skin]]);
    await boot(page, { routes: blockFonts });
    await expect(page.locator('html')).toHaveAttribute('data-vt', skin);
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot(`home-ko-${skin}-full.png`, shot());
  });

  // The bare query "D-2" lands on the procedure chooser (what to do with D-2), i.e. the searched layout under the skin.
  test(`D-2 searched state (procedure chooser), ${skin} skin (ko)`, async ({ page }) => {
    await withStorage(page, [['visable:theme', skin]]);
    await boot(page, { routes: blockFonts });
    await search(page, 'D-2');
    await expect(guidanceHeading(page, 'D-2')).toBeVisible();
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot(`d2-extension-ko-${skin}-full.png`, shot());
  });
}

// Home sections the service directory reveals (tests/e2e/landing-utilities.spec.mjs covers the behaviour).
// Added 2026-11-09 after the !important pass stripped the rule that keeps #visaManualSection visible inside
// the civic browse panel: the oracle had no revealed-section state, so the pass could not see the break.
async function openDirectoryEntry(page, target) {
  const entry = page.locator(`.cs-directory [data-action="reveal-home-section"][data-target="${target}"]`);
  if (!(await entry.isVisible().catch(() => false))) await page.locator('#csTools summary').click();
  await entry.click();
}

test('home, browse panel revealed (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await openDirectoryEntry(page, 'visaManualSection');
  await expect(page.locator('#visaManualSection')).toBeVisible();
  await page.waitForTimeout(1200); // the panel smooth-scrolls into view and renders the pre-entry track
  await expect(page).toHaveScreenshot('home-ko-browse-revealed-full.png', shot());
});

test('home, pathways revealed (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await openDirectoryEntry(page, 'pathwaySection');
  await expect(page.locator('#pathwaySection')).toBeVisible();
  await page.waitForTimeout(1200);
  await expect(page).toHaveScreenshot('home-ko-pathways-revealed-full.png', shot());
});

test('home, reminder dialog open (ko)', async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-09T09:00:00+09:00')); // the dialog counts days from today
  await boot(page, { routes: blockFonts });
  await openDirectoryEntry(page, 'reminderSection');
  const dialog = page.locator('#reminderDialog');
  await expect(dialog).toBeVisible();
  await page.waitForTimeout(800);
  await expect(dialog).toHaveScreenshot('reminder-dialog-ko.png');
});

test('global settings overlay open after a search (ko)', async ({ page }) => {
  // Opened through the public window.openGlobalSettings() the data-action dispatcher calls (the trigger
  // button is not rendered visible in this viewport state); the overlay's own styling is what is baselined.
  await boot(page, { routes: blockFonts });
  await search(page, 'D-2');
  await page.evaluate(() => window.openGlobalSettings());
  await expect(page.locator('#globalSettingsOverlay')).toBeVisible();
  await page.waitForTimeout(300);
  await expect(page).toHaveScreenshot('settings-overlay-ko.png', { fullPage: false });
});

test('D-2 extension guidance (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await search(page, 'D-2 체류기간 연장');
  await expect(guidanceHeading(page, 'D-2 체류기간 연장')).toBeAttached();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('d2-extension-ko.png', { fullPage: false });
  await expect(page).toHaveScreenshot('d2-extension-ko-full.png', shot());
});

test('D-2 legacy status card, extension tab (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await search(page, 'D-2 체류기간 연장');
  await page.locator('[data-sg-action="legacy-card"]').first().click();
  const card = page.locator('#rlist article.vc[data-code="D-2"]');
  await expect(card).toBeVisible();
  await card.locator('[data-action="select-procedure"][data-procedure="extension"]').first().click();
  await expect(card.locator('[data-procedure-panel="extension"]')).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('d2-legacy-card-ko-full.png', shot());
});

test('employment code finder open (ko)', async ({ page }) => {
  await boot(page, { routes: blockFonts });
  await page.getByRole('button', { name: /직종|업종|코드/ }).first().click().catch(() => {});
  const field = page.locator('#jcSearchInput');
  if (!(await field.isVisible().catch(() => false))) {
    await page.locator('[data-action="open-jobcode-modal"]:visible').first().click();
  }
  await expect(field).toBeVisible();
  await page.waitForTimeout(300);
  await expect(page).toHaveScreenshot('jobcode-modal-ko.png', { fullPage: false });
});

test('manual reader home', async ({ page }) => {
  await boot(page, { path: '/manual.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('manual-home-20261109.png', { fullPage: false });
});

test('form helper home', async ({ page }) => {
  await boot(page, { path: '/form-helper.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('form-helper-home-full.png', shot());
});

test('immigration checklists home', async ({ page }) => {
  await boot(page, { path: '/immigration-checklists.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('checklists-home-full.png', shot());
});

test('new home (nationality landing)', async ({ page }) => {
  await boot(page, { path: '/new-home.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('new-home-full.png', shot());
});

test('nationality interview hub', async ({ page }) => {
  await boot(page, { path: '/nationality-interview-hub.html', waitForSearch: false, routes: blockFonts });
  await expect(page.getByText('국적민원 알아보기', { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(500);
  await expect(page).toHaveScreenshot('nationality-hub-full.png', shot());
});

test('ai.html shell', async ({ page }) => {
  await boot(page, { path: '/ai.html', waitForSearch: false, routes: blockFonts });
  await page.waitForTimeout(800);
  await expect(page).toHaveScreenshot('ai-shell.png', { fullPage: false });
});

// Modals of the legacy card and the landing tools (their width/layout rules are the inline style attributes Phase 4 moves).
async function openLegacyCard(page) {
  await boot(page, { routes: blockFonts });
  await search(page, 'D-2 체류기간 연장');
  await page.locator('[data-sg-action="legacy-card"]').first().click();
  const card = page.locator('#rlist article.vc[data-code="D-2"]');
  await expect(card).toBeVisible();
  return card;
}
for (const [name, action, overlay] of [
  ['ai modal', 'open-ai-modal', '#aiModalOverlay'],
  ['document modal', 'open-doc-modal', '#docModalOverlay'],
  ['faq modal', 'open-faq-modal', '#faqModalOverlay'],
  // (the HiKorea guide overlay is not baselined: it did not render pixel-stable across two runs)
]) {
  test(`legacy card: ${name} (ko)`, async ({ page }) => {
    const card = await openLegacyCard(page);
    await card.locator(`[data-action="${action}"]`).first().click();
    await expect(page.locator(overlay)).toBeVisible();
    await page.waitForTimeout(1500); // modal bodies load their data (document help, registries) after opening
    // Element screenshot: the page behind the backdrop is still smooth-scrolling the legacy card into view,
    // which made full-viewport shots differ by 4–7% between runs; the modal box itself is what Phase 4 touches.
    await expect(page.locator(`${overlay} .modal-box`)).toHaveScreenshot(`modal-${action}.png`);
  });
}
for (const [name, action, overlay] of [
  ['agent finder', 'open-agent-finder', '#agentFinderModalOverlay'],
  ['hospital finder', 'open-med-finder', '#medFinderModalOverlay'],
  ['jurisdiction finder', 'open-jurisdiction-modal', '#jurisdictionModalOverlay'],
]) {
  test(`landing tool: ${name} (ko)`, async ({ page }) => {
    await boot(page, { routes: blockFonts });
    const btn = page.locator(`[data-action="${action}"]:visible`).first();
    if (!(await btn.isVisible().catch(() => false))) await page.locator('#csTools summary').click();
    await page.locator(`[data-action="${action}"]:visible`).first().click();
    await expect(page.locator(overlay)).toBeVisible();
    await page.waitForTimeout(1500); // modal bodies load their data (document help, registries) after opening
    // Element screenshot: the page behind the backdrop is still smooth-scrolling the legacy card into view,
    // which made full-viewport shots differ by 4–7% between runs; the modal box itself is what Phase 4 touches.
    await expect(page.locator(`${overlay} .modal-box`)).toHaveScreenshot(`modal-${action}.png`);
  });
}
