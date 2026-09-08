import { test, expect } from '@playwright/test';

const ACTIONS = [
  'open-short-stay',
  'open-jobcode-modal',
  'open-jurisdiction-modal',
  'open-agent-finder',
  'open-med-finder'
];

test('landing keeps all five historical utility entry points visible', async ({ page }) => {
  await page.goto('/index.html');

  const utilityRow = page.locator('.p-gw-utility');
  await expect(utilityRow).toBeVisible();
  await expect(utilityRow.locator('.p-gw-util')).toHaveCount(5);

  for (const action of ACTIONS) {
    await expect(page.locator(`.p-gw-util[data-action="${action}"]`)).toBeVisible();
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'restored utilities must not introduce horizontal overflow').toBeLessThanOrEqual(1);
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
