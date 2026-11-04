// Golden: landing tools that load their own data. Expected values come from
// data/jobcode_master.json (the canonical job-code dataset, phase0-data-canon.md).
import { test, expect } from '@playwright/test';
import { readJson, pack, stripTags } from '../helpers/data.mjs';
import { boot, bodyText, normalize } from '../helpers/page.mjs';

const JOBCODES = readJson('data/jobcode_master.json');
// A unit-level occupation row with a distinctive Korean name.
const chef = JOBCODES.data.find((r) => r.type === 'occupation' && r.code === '2970');

test('employment code finder loads the canonical dataset and finds an occupation by its name', async ({ page }) => {
  const c = pack('ko').civic;
  const dataResponses = [];
  page.on('response', (r) => { if (/jobcode_master\.json|output\.json/.test(r.url())) dataResponses.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ''), status: r.status() }); });
  await boot(page);
  await page.getByRole('button', { name: normalize(c.jobs) }).first().click();
  const field = page.locator('#jcSearchInput');
  await expect(field).toBeVisible({ timeout: 30_000 });
  await field.fill(chef.name_ko);
  await field.press('Enter');
  // The echo of the query appears first; wait for the candidate list (the code) itself.
  await expect(page.getByText(chef.code, { exact: true }).first()).toBeVisible({ timeout: 30_000 });
  const text = normalize(await bodyText(page));
  expect(text).toContain(chef.name_ko);
  expect(text).toContain(chef.code);
  // The finder's own caution stays with the result.
  expect(text).toContain(normalize(stripTags(pack('ko').jobCodeScopeWarning)));
  // Only the canonical file is requested, and it loads.
  expect(dataResponses.map((r) => r.url)).toEqual(['/data/jobcode_master.json']);
  expect(dataResponses[0].status).toBe(200);
});
