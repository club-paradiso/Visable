import { test, expect } from '@playwright/test';

async function boot(page) {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto('/index.html');
  await expect(page.locator('#civicQuery')).toBeVisible();
}

test('main search respects a corrected status rather than the first code typed', async ({ page }) => {
  await boot(page);
  await page.locator('#civicQuery').fill('D-2가 아니라 D-10인데 연장하려면?');
  await page.locator('#civicQuery').press('Enter');
  const guidance = page.locator('#statusGuidance');
  await expect(guidance).toBeVisible();
  await expect(guidance.locator('.sg-interp')).toContainText('D-10');
  await expect(guidance.locator('.sg-interp')).not.toContainText('D-2');
});

test('main search respects a rejected procedure and asks for the missing status', async ({ page }) => {
  await boot(page);
  await page.locator('#civicQuery').fill('등록증 재발급 말고 체류기간 연장 서류');
  await page.locator('#civicQuery').press('Enter');
  await expect(page.locator('#statusGuidance')).toHaveAttribute('data-sg-kind', 'need-status');
  await expect(page.locator('#statusGuidance .sg-interp')).toContainText('연장');
});

async function openEmployment(page) {
  if (await page.locator('.cs-directory').getAttribute('open') === null) await page.locator('.cs-directory summary').click();
  await page.locator('.cs-directory [data-action="open-jobcode-modal"]').click();
  await expect(page.locator('#jcSearchInput')).toBeVisible();
}

test('a rate-limited interpreter keeps local job understanding and excludes a denied role', async ({ page }) => {
  await boot(page);
  await page.route('**/api/employment/interpret', (route) => route.fulfill({ json: { status: 'unavailable', reason: 'rate_limited' } }));
  await openEmployment(page);
  await page.locator('#jcSearchInput').fill('병원에서 전산 시스템을 관리해요. 간호사는 아니에요');
  await page.locator('#jcSearchInput').press('Enter');
  await expect(page.locator('#jcJobResults .jc2-card').first()).toContainText('정보 시스템 운영자');
  await expect(page.locator('#jcJobResults .jc2-card').first()).not.toContainText('간호사');
});

test('structured multilingual interpretation reaches official classification search', async ({ page }) => {
  await boot(page);
  let requested = false;
  await page.route('**/api/employment/interpret', (route) => {
    requested = true;
    return route.fulfill({ json: { status: 'ok', extraction: { role: '귤 수확', tasks: ['귤 따요'], workplace: '농장', employerMainBusiness: '과수 농업' } } });
  });
  await openEmployment(page);
  await page.locator('#jcSearchInput').fill('Tôi hái quýt ở trang trại');
  await page.locator('#jcSearchInput').press('Enter');
  await expect(page.locator('#jcJobResults')).toContainText(/과수|농업|채소/);
  expect(requested).toBe(true);
});
