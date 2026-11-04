// Regression coverage for the task-first HiKorea helper (desktop + mobile).
// Do not assume that a Visable guide creates a real government booking.
import { test, expect } from '@playwright/test';
import { boot } from '../helpers/page.mjs';

const BOOK = 'https://www.hikorea.go.kr/resv/ResvIntroR.pt';
const NON_MEMBER_LOOKUP = 'https://www.hikorea.go.kr/mypage/MypgNonRegResvPageR.pt';

async function openHelper(page) {
  const launcher = page.locator('[data-action="open-hikorea-guide"]:visible').first();
  await expect(launcher).toBeVisible();
  await launcher.click();
  await expect(page.locator('#hikoreaGuideOverlay')).toHaveClass(/active/);
  return page.locator('#hikoreaGuideBody');
}

test('HiKorea: task-first start, direct official booking and no empty screenshots', async ({ page }) => {
  const errors = await boot(page);
  const body = await openHelper(page);
  await expect(body.locator('[role="tablist"] [role="tab"]')).toHaveCount(4);
  await expect(body.locator('.prh-hero-title')).toBeVisible();
  await expect(body.locator('.prh-hero-actions a[href="' + BOOK + '"]')).toBeVisible();
  await expect(body.locator('.prh-flow-preview li')).toHaveCount(3);

  await body.locator('#prhtab-reservation').click();
  await expect(body.locator('.prh-steps .prh-step')).toHaveCount(5);
  await expect(body.locator('.prh-shot-ph')).toHaveCount(0);
  await expect(body.locator('.prh-finder a[href="' + BOOK + '"]')).toBeVisible();

  await body.locator('#prhtab-manage').click();
  await expect(body.locator('a[href="' + NON_MEMBER_LOOKUP + '"]')).toBeVisible();
  expect(errors).toEqual([]);
});

test('HiKorea: account preparation remains optional and open after password creation', async ({ page }) => {
  const errors = await boot(page);
  const body = await openHelper(page);
  await body.locator('[data-prh-action="go-tab"][data-prh-tab="signup"]').first().click();
  await expect(body.locator('.prh-account-disclosure')).toBeVisible();
  await expect(body.locator('.prh-account-prep')).toBeHidden();
  await body.locator('.prh-account-disclosure > summary').click();
  await expect(body.locator('.prh-account-prep')).toBeVisible();
  await body.locator('[data-prh-action="generate-password"]').click();
  await expect(body.locator('.prh-account-disclosure')).toHaveAttribute('open', '');
  await expect(body.locator('#prhGeneratedPassword')).toBeVisible();
  expect(errors).toEqual([]);
});

test('HiKorea: reservation finder prioritizes the next action and collapses long details', async ({ page }) => {
  const errors = await boot(page);
  const body = await openHelper(page);
  await body.locator('[data-prh-action="start-finder"]').first().click();
  await expect(body.locator('.prh-q')).toBeVisible();
  await body.locator('[data-prh-field="purpose"][data-prh-value="extension"]').click();
  await body.locator('[data-prh-field="card"][data-prh-value="yes"]').click();
  await body.locator('[data-prh-field="loc"][data-prh-value="in_korea"]').click();
  await body.locator('#prhCode').fill('D-2');
  await body.locator('[data-prh-action="next"]').click();
  await body.locator('[data-prh-field="expiry"][data-prh-value="__skip__"]').click();
  await body.locator('[data-prh-action="next"]').click();

  await expect(body.locator('.prh-result-card')).toBeVisible();
  await expect(body.locator('.prh-result-primary a[href="' + BOOK + '"]')).toBeVisible();
  const details = body.locator('.prh-result-details');
  await expect(details).toBeVisible();
  await expect(details.locator('.prh-sections')).toBeHidden();
  await details.locator('summary').click();
  await expect(details.locator('.prh-sections')).toBeVisible();
  expect(errors).toEqual([]);
});
