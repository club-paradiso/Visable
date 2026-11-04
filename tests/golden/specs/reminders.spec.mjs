// Golden: deadline reminders (localStorage-backed, exported to the user's own calendar).
// Expected labels come from data/i18n/ko.json; the seeded reminder is the test's own data.
// Storage key contract: paradisoReminders (phase0-inventory.md §B) — returning users keep them.
import { test, expect } from '@playwright/test';
import { pack } from '../helpers/data.mjs';
import { boot, bodyText, normalize } from '../helpers/page.mjs';

const ko = pack('ko');
const isoInDays = (n) => { const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const MEMO = '골든 테스트 메모';

test('a saved reminder within 30 days shows the banner and is listed in the reminders dialog with its type, memo and D-day', async ({ page }) => {
  const date = isoInDays(10);
  await page.addInitScript(([key, item]) => { try { localStorage.setItem(key, JSON.stringify([item])); } catch (e) {} },
    ['paradisoReminders', { id: 'r_golden', type: 'visa', date, memo: MEMO }]);
  const errors = await boot(page);
  // Banner: "<type label> (<memo>) — <days>일 남았어요."
  const bannerText = `${ko.reminderTypeLabels[0]} (${MEMO}) — ${ko.reminderBannerDaysLeft.replace('{days}', '10')}.`;
  await expect(page.getByText(bannerText, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  // Open the reminders tool from the home.
  await page.getByRole('button', { name: normalize(ko.civic.reminders) }).first().click();
  const dialog = page.getByRole('dialog').filter({ hasText: MEMO }).first();
  await expect(dialog).toBeVisible({ timeout: 30_000 });
  const text = normalize(await dialog.innerText());
  expect(text).toContain(ko.reminderTypeLabels[0]);
  expect(text).toContain(MEMO);
  expect(text).toContain('D-10');
  expect(text).toContain(ko.reminderIcsBtn);
  expect(text).toContain(ko.reminderGcalBtn);
  expect(text).toContain(ko.reminderDeleteBtn);
  expect(errors).toEqual([]);
});

test('saving a new reminder stores it under the legacy key and renders it', async ({ page }) => {
  await boot(page);
  await page.getByRole('button', { name: normalize(ko.civic.reminders) }).first().click();
  const dialog = page.locator('#reminderDialog');
  await expect(dialog).toBeVisible({ timeout: 30_000 });
  await dialog.locator('#reminderType').selectOption('arc');
  await dialog.locator('#reminderDate').fill(isoInDays(45));
  await dialog.locator('#reminderMemo').fill('새 리마인더');
  await dialog.getByRole('button', { name: ko.reminderSubmit }).click();
  await expect(dialog.getByText('새 리마인더', { exact: false }).first()).toBeVisible();
  const text = normalize(await dialog.innerText());
  expect(text).toContain(ko.reminderTypeLabels[1]);
  expect(text).toContain('D-45');
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('paradisoReminders') || '[]'));
  expect(stored).toHaveLength(1);
  expect(stored[0]).toMatchObject({ type: 'arc', memo: '새 리마인더' });
});
