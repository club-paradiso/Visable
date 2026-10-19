import { test, expect } from '@playwright/test';

// manual.html — 매뉴얼 원문 읽기. Deep links, checklist, search, and the entry from the landing.

test('status + procedure deep link opens the matching manual section', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('/manual.html#c-F-6.s.extend');
  const section = page.locator('#secs > section.sec.hit, #secs > section.sec').filter({ has: page.locator('.orig', { hasText: '체류기간 연장허가' }) }).first();
  await expect(section).toBeVisible();
  await expect(section.locator('h2')).toHaveText('체류기간 늘리기');
  await expect(page.locator('.tab[aria-selected="true"] b')).toHaveText('연장·변경·등록 등');
  await expect(page.locator('.disc .state')).toHaveText('원문 발췌 · 검토 전');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  expect(errors).toEqual([]);
});

test('visa tab keeps 사증 sections apart from 체류 sections', async ({ page }) => {
  await page.goto('/manual.html#c-D-2.v');
  await expect(page.locator('.tab[aria-selected="true"] b')).toHaveText('비자(사증) 받기');
  const origs = await page.locator('#secs .orig').allTextContents();
  expect(origs.some((t) => /사증발급인정서/.test(t))).toBe(true);
  expect(origs.some((t) => /체류기간 연장허가|외국인등록/.test(t))).toBe(false);
});

test('document checklist toggles and counts per viewer', async ({ page }) => {
  await page.goto('/manual.html#c-A-1.v.consul');
  const list = page.locator('ul.docs').first();
  await expect(list).toBeVisible();
  const count = page.locator('.dtools .cnt').first();
  const before = await count.textContent();
  await list.locator('li.doc .ck').first().click();
  await expect(list.locator('li.doc').first()).toHaveAttribute('aria-checked', 'true');
  await expect(count).not.toHaveText(before || '');
  await page.reload();
  await expect(page.locator('ul.docs li.doc').first()).toHaveAttribute('aria-checked', 'true');
});

test('search finds manual text and opens the section with the term marked', async ({ page }) => {
  await page.goto('/manual.html');
  await page.fill('#mr-q', '시간제취업');
  const first = page.locator('a.res').first();
  await expect(first).toBeVisible({ timeout: 15_000 });
  await first.click();
  await expect(page.locator('#secs mark').first()).toBeVisible();
});

test('landing offers the reader as a supporting tool', async ({ page }) => {
  await page.goto('/index.html');
  const link = page.locator('.cs-tools-support a.cs-tool[href="manual.html"]');
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/manual\.html/);
  await expect(page.locator('.intro h1')).toContainText('매뉴얼 원문을');
});
