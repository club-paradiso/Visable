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

test('New Home explains nationality and KIIP routes with scoped official sources', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.goto('/new-home.html');
  const pathIds = await page.evaluate(() => fetch('/data/nationality_paths.json').then((response) => response.json()).then((data) => data.paths.map((item) => item.id)));
  expect(pathIds).toEqual(expect.arrayContaining(['general', 'marriage', 'family', 'special', 'restoration', 'determination', 'dual', 'loss', 'renunciation', 'after']));
  await expect(page.locator('.nh-hub-item[data-id="loss"]')).toBeVisible();
  await expect(page.locator('.nh-hub-item[data-id="renunciation"]')).toBeVisible();
  await expect(page.locator('#kiip')).toContainText(/자동으로 보장하지 않습니다|do not automatically establish eligibility/);
  await expect(page.locator('.nh-source-disclaimer')).toContainText(/제휴 또는 소속 관계가 없습니다|is not affiliated/);
  await expect(page.locator('.nh-source-card')).toHaveCount(16);
  await expect(page.locator('.nh-source-scope').first()).toBeVisible();
  await expect(page.locator('.nh-source-meta').first()).toContainText(/확인일|Accessed/);
  await expect(page.locator('.nh-source-link[href="https://mojminwon.moj.go.kr/minwon/2014/subview.do"]')).toBeVisible();
  await expect(page.getByText(/향후 시행 — 현재 기준 아님|Future effective date — not current law/)).toBeVisible();
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
  const missionSources = page.locator('.vc[data-code="D-2"] details.issuance-mission-sources').first();
  await expect(missionSources).toBeVisible();
  await missionSources.locator('summary').click();
  await expect(missionSources.locator('a.issuance-mission-link').first()).toHaveAttribute('href', /overseas\.mofa\.go\.kr/);
  await expect(missionSources).toContainText('해당 공관 범위만 적용');
  await expectNoHorizontalOverflow(page);
});
