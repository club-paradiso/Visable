// Golden: registered immigration-agent finder and designated-hospital finder. Both load an
// official registry snapshot (data/agent_registry_2026-04-30.json,
// data/designated_medical_institutions_2026_11_02.json); expected names come from those files.
import { test, expect } from '@playwright/test';
import { pack, readJson } from '../helpers/data.mjs';
import { boot, normalize } from '../helpers/page.mjs';

const c = pack('ko').civic;
const AGENTS = readJson('data/agent_registry_2026-04-30.json');
const MEDS = readJson('data/designated_medical_institutions_2026_11_02.json');

async function openTool(page, label) {
  // The tool directory is a <details> whose <summary> reads "전체 도구 보기"; its tiles are buttons.
  const summary = page.locator('#csTools summary');
  if (!(await page.locator('#csTools[open]').count())) await summary.click();
  await page.getByRole('button', { name: new RegExp(normalize(label)) }).first().click();
}

test('agent finder lists the official registry by region', async ({ page }) => {
  const errors = await boot(page);
  await openTool(page, c.agencies);
  const region = AGENTS.regions[0];
  const first = AGENTS.agencies.find((a) => a.region1 === region);
  const select = page.locator('#agentFinderRegion');
  await expect(select).toBeVisible({ timeout: 30_000 });
  await expect(select.locator('option')).toHaveCount(AGENTS.regions.length + 1); // placeholder + 17 regions
  await select.selectOption({ label: region });
  await expect(page.getByText(first.name, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(first.address, { exact: false }).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('hospital finder lists the designated institutions for a region', async ({ page }) => {
  const errors = await boot(page);
  await openTool(page, c.hospitals);
  // Quick-pick chips are a fixed set (제주 first, the office this tool was built for).
  const region = '제주';
  expect(MEDS.regions).toContain(region);
  const first = MEDS.institutions.find((m) => m.region === region);
  const chips = page.locator('#medFinderChips');
  await expect(chips).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(String(MEDS.institutions.length), { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  await chips.getByRole('button', { name: region, exact: true }).click();
  await expect(page.getByText(first.institution_name, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  expect(errors).toEqual([]);
});
