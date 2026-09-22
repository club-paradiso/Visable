import { test, expect } from '@playwright/test';

const DIRECT_ACTIONS = [
  'open-short-stay',
  'open-jobcode-modal',
  'open-jurisdiction-modal',
  'open-agent-finder',
  'open-med-finder'
];

const JOURNEY_TARGETS = [
  'visaManualSection',
  'pathwaySection',
  'reminderSection'
];

test('all eight utilities remain reachable through the selected design service directory', async ({ page }) => {
  await page.goto('/index.html');

  await page.locator('.cs-directory summary').click();
  const utilityRow = page.locator('.cs-directory');
  await expect(utilityRow).toBeVisible();
  await expect(utilityRow.locator('button[data-action^="open-"], button[data-action="reveal-home-section"]')).toHaveCount(DIRECT_ACTIONS.length + JOURNEY_TARGETS.length);

  for (const action of DIRECT_ACTIONS) {
    await expect(utilityRow.locator(`button[data-action="${action}"]`)).toBeVisible();
  }

  for (const target of JOURNEY_TARGETS) {
    const entry = utilityRow.locator(`button[data-action="reveal-home-section"][data-target="${target}"]`);
    await expect(entry).toBeVisible();
    await entry.click();
    await expect(page.locator(`#${target}`)).toBeVisible();
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'restored landing services must not introduce horizontal overflow').toBeLessThanOrEqual(1);
});

test('restored short-stay entry opens the existing checker instead of a dead shell', async ({ page }) => {
  await page.goto('/index.html');

  await page.locator('.cs-directory summary').click();
  await page.locator('.cs-directory [data-action="open-short-stay"]').click();
  const modal = page.locator('#shortStayModalOverlay');
  await expect(modal).toHaveClass(/active/);
  await expect(modal).toHaveAttribute('aria-hidden', 'false');
  await expect(modal.locator('#shortStayChecker')).toBeVisible();
  await expect(modal).toContainText(/국적별 단기입국 경로 확인|Short-stay entry/);
});

test('an early short-stay tap is replayed after the deferred checker becomes ready', async ({ page }) => {
  await page.route('**/assets/js/short-stay-checker.js', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });

  await page.goto('/index.html', { waitUntil: 'commit' });
  await page.locator('.cs-directory summary').click();
  const entry = page.locator('.cs-directory [data-action="open-short-stay"]');
  await expect(entry).toBeVisible();
  await entry.click();

  const modal = page.locator('#shortStayModalOverlay');
  await expect(modal).toHaveClass(/active/, { timeout: 10_000 });
  await expect(modal).toHaveAttribute('aria-hidden', 'false');
  await expect(modal.locator('#shortStayChecker')).toBeVisible();
});

test('a utility tap before the action delegation is installed is replayed, not dropped', async ({ page }) => {
  // The delegated listener that owns every [data-action] is installed inside
  // index.html's DOMContentLoaded callback, after `await loadI18nTranslations()`.
  // Deferred scripts render the interactive directory inside that window, so
  // delaying i18n reproduces the state a slow connection puts a real user in:
  // the control is on screen and clickable, and its owner does not exist yet.
  await page.route('**/data/i18n/**', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    await route.continue();
  });

  await page.goto('/index.html', { waitUntil: 'commit' });
  await page.locator('.cs-directory summary').click();
  const entry = page.locator('.cs-directory [data-action="reveal-home-section"][data-target="visaManualSection"]');
  await expect(entry).toBeVisible();
  await entry.click();

  // Nothing can have handled it yet — that is the whole point of the fixture.
  await expect(page.locator('#visaManualSection')).toBeHidden();
  // Once the delegation is installed the recorded tap must be replayed.
  await expect(page.locator('#visaManualSection')).toBeVisible({ timeout: 15_000 });
});

test('an early short-stay tap opens the checker exactly once', async ({ page }) => {
  // Both readiness bridges are armed here: the delegation is held back by the
  // i18n await and the checker module is held back by its own delay. They must
  // stay disjoint, so the modal opens once and stays open rather than being
  // opened twice or toggled shut by a duplicate replay.
  await page.route('**/data/i18n/**', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.route('**/assets/js/short-stay-checker.js', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });

  await page.goto('/index.html', { waitUntil: 'commit' });
  await page.locator('.cs-directory summary').click();
  await page.locator('.cs-directory [data-action="open-short-stay"]').click();

  const modal = page.locator('#shortStayModalOverlay');
  await expect(modal).toHaveClass(/active/, { timeout: 15_000 });
  await expect(modal).toHaveAttribute('aria-hidden', 'false');
  await expect(modal.locator('#shortStayChecker')).toBeVisible();
  // Give any second replay time to land, then confirm it did not close or
  // re-toggle the modal.
  await page.waitForTimeout(1000);
  await expect(modal).toHaveClass(/active/);
  await expect(page.locator('#shortStayModalOverlay')).toHaveCount(1);
});

test('September original search preserves source scope, page links and exact code aliases', async ({ page }) => {
  await page.goto('/index.html');
  await page.locator('#civicQuery').fill('E74');
  await page.locator('#civicSearchForm button[type="submit"]').click();
  const results = page.locator('#civicManualResults');
  await expect(results).toContainText('2026.09.18');
  // The raw excerpt list opens with 3 hits (the structured status guidance now sits above it); 결과 더 보기 loads more.
  await expect(results.locator('.cs-manual-list li')).toHaveCount(3);
  await expect(results.locator('.cs-more')).toHaveCount(1);
  await expect(results.locator('.cs-result-title').first()).toContainText('E-7-4');
  await results.locator('#civicDomain').selectOption('visa_issuance');
  await expect(results.locator('.cs-result-meta').first()).toContainText('2026-09-01');
  const link = results.locator('.cs-result-actions a').first();
  await expect(link).toHaveAttribute('href', /visa_manual_260901\.pdf#page=\d+/);
  await results.locator('.cs-result-title').first().click();
  await expect(page.locator('#civicPageDialog')).toBeVisible();
  await expect(page.locator('#civicPageDialog pre')).toContainText('E-7-4');
  await page.keyboard.press('Escape');
  await expect(page.locator('#civicPageDialog')).not.toBeVisible();
});
