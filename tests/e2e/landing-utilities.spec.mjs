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

test('landing keeps all eight public utilities and restored journey surfaces visible', async ({ page }) => {
  await page.goto('/index.html');

  const utilityRow = page.locator('.p-gw-utility');
  await expect(utilityRow).toBeVisible();
  await expect(utilityRow.locator('.p-gw-util')).toHaveCount(DIRECT_ACTIONS.length + JOURNEY_TARGETS.length);

  for (const action of DIRECT_ACTIONS) {
    await expect(utilityRow.locator(`.p-gw-util[data-action="${action}"]`)).toBeVisible();
  }

  for (const target of JOURNEY_TARGETS) {
    const entry = utilityRow.locator(`.p-gw-util[data-action="reveal-home-section"][data-target="${target}"]`);
    await expect(entry).toBeVisible();
    await expect(page.locator(`#${target}`)).toBeVisible();
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'restored landing services must not introduce horizontal overflow').toBeLessThanOrEqual(1);
});

test('restored short-stay entry opens the existing checker instead of a dead shell', async ({ page }) => {
  await page.goto('/index.html');

  await page.locator('.p-gw-util[data-action="open-short-stay"]').click();
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
  const entry = page.locator('.p-gw-util[data-action="open-short-stay"]');
  await expect(entry).toBeVisible();
  await entry.click();

  const modal = page.locator('#shortStayModalOverlay');
  await expect(modal).toHaveClass(/active/, { timeout: 10_000 });
  await expect(modal).toHaveAttribute('aria-hidden', 'false');
  await expect(modal.locator('#shortStayChecker')).toBeVisible();
});
