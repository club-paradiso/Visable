// Golden: "관할 출입국 찾기" — the office responsible for an address. Expected office and address
// come from the jurisdiction tables (src/features/jurisdiction-data.js, moved verbatim from index.html).
import { test, expect } from '@playwright/test';
import { pack } from '../helpers/data.mjs';
import { boot, normalize } from '../helpers/page.mjs';
import { JUR_DB, OFFICE_INFO } from '../../../src/features/jurisdiction-data.js';

const c = pack('ko').civic;

test('choosing a 시·도 and 시·군·구 shows the responsible immigration office and its address', async ({ page }) => {
  const sido = '서울특별시';
  const sigungu = '종로구';
  const office = JUR_DB[sido][sigungu];
  const info = OFFICE_INFO[office];
  expect(info, 'office info exists for the chosen district').toBeTruthy();
  const errors = await boot(page);
  const summary = page.locator('#csTools summary');
  if (!(await page.locator('#csTools[open]').count())) await summary.click();
  await page.getByRole('button', { name: new RegExp(normalize(c.office)) }).first().click();
  const sidoSel = page.locator('#jurSido');
  await expect(sidoSel).toBeVisible({ timeout: 30_000 });
  await expect(sidoSel.locator('option')).toHaveCount(Object.keys(JUR_DB).length + 1);
  await sidoSel.selectOption(sido);
  const sigunguSel = page.locator('#jurSigungu');
  await expect(sigunguSel).toBeEnabled();
  await expect(sigunguSel.locator('option')).toHaveCount(Object.keys(JUR_DB[sido]).length + 1);
  await sigunguSel.selectOption(sigungu);
  await expect(page.getByText(office, { exact: true }).first()).toBeVisible();
  await expect(page.getByText(info.addr, { exact: true }).first()).toBeVisible();
  expect(errors).toEqual([]);
});
