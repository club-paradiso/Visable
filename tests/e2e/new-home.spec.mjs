import { test, expect } from '@playwright/test';

async function expectNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'no horizontal overflow').toBeLessThanOrEqual(1);
}

test('New Home exposes a useful entry point and an accessible readiness dialog', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.goto('/new-home.html');
  await expect(page.locator('.nh-section-nav')).toBeVisible();
  await expect(page.locator('.nh-hero-guide')).toBeVisible();
  await expect(page.locator('.nh-card-icon').first()).toHaveText('01');
  await expectNoHorizontalOverflow(page);

  const trigger = page.locator('[data-action="open-readiness"]').first();
  await trigger.click();
  const modal = page.locator('#readinessModal');
  await expect(modal).toHaveClass(/active/);
  const progress = modal.getByRole('progressbar');
  await expect(progress).toHaveAttribute('aria-valuenow', '1');
  await expect(progress).toHaveAttribute('aria-valuemax', '8');
  await expect(modal.locator('legend')).toBeFocused();

  const next = modal.locator('.nh-modal-foot button.primary');
  await expect(next).toBeDisabled();
  await modal.locator('input[type="radio"]').first().check();
  await expect(next).toBeEnabled();

  await page.keyboard.press('Escape');
  await expect(modal).not.toHaveClass(/active/);
  await expect(trigger).toBeFocused();
  await expectNoHorizontalOverflow(page);
  expect(consoleErrors).toEqual([]);
});

test('homepage visa search settles without reopening blocking menus', async ({ page }) => {
  test.skip(page.viewportSize().width < 1000, 'The gateway search transition is a desktop homepage flow.');
  await page.goto('/index.html');
  await expect(page.locator('#searchToggleBtn')).toBeVisible();
  await page.locator('#searchToggleBtn').click();
  const input = page.locator('#q');
  await expect(input).toBeEnabled({ timeout: 20_000 });
  await input.fill('D-2');
  await page.getByTestId('visa-search-submit').click();
  await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 10_000 });
  await expect(page.locator('body')).not.toHaveClass(/launching/);
  await expect(page.locator('#cityMenu')).toBeHidden();
  await expect(page.locator('.vc[data-code="D-2"]')).toBeVisible();
  await expectNoHorizontalOverflow(page);
});
