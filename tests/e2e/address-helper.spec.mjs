// Address Helper (address-helper.html) — JUSOYUNO folded into Visable as a tool.
//
// The static E2E server has no serverless runtime and no JUSO_API_KEY, so the
// API is intercepted: one spec proves the honest NOT_CONFIGURED fallback (the
// state the preview shows until the key is registered on this project), the
// other drives the full search → candidate → card flow on a stubbed official
// response. Nothing here calls the live JUSO API. Layout is asserted at phone
// widths in every shipped UI language of the tool, because its copy is longest
// in Vietnamese and Hindi.
import { test, expect } from '@playwright/test';

const RESULT = {
  roadAddr: '제주특별자치도 제주시 중앙로 1',
  roadAddrPart2: '',
  engAddr: '1, Jungang-ro, Jeju-si, Jeju-do, Republic of Korea',
  jibunAddr: '제주특별자치도 제주시 이도일동 1',
  zipNo: '63264',
  buildingName: ''
};

test.describe('address helper', () => {
  test('not configured: manual fallback, no fabricated results', async ({ page }) => {
    await page.route('**/api/address/search', (route) => route.fulfill({
      status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'NOT_CONFIGURED' })
    }));
    await page.goto('/address-helper.html');
    await expect(page.locator('#search')).toBeVisible();
    await page.locator('#keyword').fill('제주시 중앙로 1');
    await page.locator('#search').click();
    await expect(page.locator('#manualHelp')).toBeVisible();
    await expect(page.locator('#candidates .candidate')).toHaveCount(0);
    await expect(page.locator('#selected')).toBeHidden();
  });

  test('configured: search → candidate → Korean/English card', async ({ page }) => {
    await page.route('**/api/address/search', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ code: 'OK', totalCount: 1, source: 'MOIS_JUSO', verifiedBaseOnly: true, results: [RESULT] })
    }));
    await page.goto('/address-helper.html');
    await page.locator('#keyword').fill('제주시 중앙로 1');
    await page.locator('#search').click();
    const candidate = page.locator('#candidates .candidate');
    await expect(candidate).toHaveCount(1);
    await candidate.click();
    await expect(page.locator('#selected')).toBeVisible();
    await expect(page.locator('#krResult')).toHaveText(RESULT.roadAddr);
    await expect(page.locator('#enResult')).toHaveText(RESULT.engAddr);
    await expect(page.locator('#zipResult')).toContainText('63264');
  });

  test('no horizontal overflow at phone widths in any shipped language', async ({ page }) => {
    await page.route('**/api/address/search', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ code: 'OK', totalCount: 1, source: 'MOIS_JUSO', verifiedBaseOnly: true, results: [RESULT] })
    }));
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto('/address-helper.html');
      for (const lang of ['ko', 'en', 'zh', 'vi', 'id', 'hi']) {
        await page.locator('#language').selectOption(lang);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect(overflow, `overflow at ${width}px in ${lang}`).toBeLessThanOrEqual(1);
      }
      // The result card carries the longest unbroken strings (the addresses).
      await page.locator('#language').selectOption('ko');
      await page.locator('#keyword').fill('제주시 중앙로 1');
      await page.locator('#search').click();
      await page.locator('#candidates .candidate').click();
      await expect(page.locator('#selected')).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `overflow with result card at ${width}px`).toBeLessThanOrEqual(1);
    }
  });
});
