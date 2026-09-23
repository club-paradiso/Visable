// Real-browser tests for the global language control
// (assets/js/civic-search.js `langButton` / `openLangDialog`).
//
//   * one control on the home nav and in the searched header, 15 languages in
//     native names, searchable, popover on desktop / bottom sheet on mobile;
//   * Escape closes and returns focus; aria-expanded tracks the state;
//   * picking a language goes through the existing apply-language path:
//     document lang/dir, `paradiso:language` storage, `?lang=` bootstrap;
//   * Arabic flips the document to RTL without horizontal overflow;
//   * the choice survives a search and the guidance renders in that language.
import { test, expect } from '@playwright/test';

async function boot(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery') && !!document.querySelector('[data-cs-lang-open]'); } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}

async function openDialog(page) {
  const opener = page.locator('[data-cs-lang-open]:visible').first();
  await expect(opener).toBeVisible();
  await opener.click();
  const dialog = page.locator('#csLangDialog[open]');
  await expect(dialog).toBeVisible();
  await expect(opener).toHaveAttribute('aria-expanded', 'true');
  return { opener, dialog };
}

async function noHorizontalScroll(page) {
  const o = await page.evaluate(() => ({ doc: document.documentElement.scrollWidth, body: document.body.scrollWidth, inner: innerWidth }));
  expect(o.doc, `document scrollWidth ${o.doc} > ${o.inner}`).toBeLessThanOrEqual(o.inner + 1);
  expect(o.body, `body scrollWidth ${o.body} > ${o.inner}`).toBeLessThanOrEqual(o.inner + 1);
}

test('the control lists 15 languages in their native names, filters, closes on Escape and returns focus', async ({ page }) => {
  await boot(page);
  const { opener, dialog } = await openDialog(page);
  await expect(dialog.locator('.cs-lang-option')).toHaveCount(15);
  await expect(dialog.locator('.cs-lang-option[aria-selected="true"]')).toHaveCount(1);
  for (const [code, name] of [['ko', '한국어'], ['en', 'English'], ['ar', 'العربية'], ['zh-TW', '繁體中文'], ['vi', 'Tiếng Việt']]) {
    await expect(dialog.locator(`.cs-lang-option[data-lang="${code}"] .cs-lang-native`)).toHaveText(name);
  }
  await dialog.locator('[data-cs-lang-filter]').fill('espa');
  await expect(dialog.locator('.cs-lang-option')).toHaveCount(1);
  await expect(dialog.locator('.cs-lang-option').first()).toContainText('Español');
  await dialog.locator('[data-cs-lang-filter]').fill('');
  await expect(dialog.locator('.cs-lang-option')).toHaveCount(15);
  await page.keyboard.press('Escape');
  await expect(page.locator('#csLangDialog[open]')).toHaveCount(0);
  await expect(opener).toHaveAttribute('aria-expanded', 'false');
  const focused = await page.evaluate(() => document.activeElement && document.activeElement.hasAttribute('data-cs-lang-open'));
  expect(focused).toBe(true);
  await noHorizontalScroll(page);
});

test('desktop shows a popover under the button; mobile shows a bottom sheet', async ({ page }) => {
  await boot(page);
  const { opener, dialog } = await openDialog(page);
  const vw = await page.evaluate(() => innerWidth);
  const vh = await page.evaluate(() => innerHeight);
  const box = await dialog.boundingBox();
  const ob = await opener.boundingBox();
  expect(box).not.toBeNull();
  if (vw > 680) {
    expect(box.width).toBeLessThan(480);
    expect(box.y).toBeGreaterThanOrEqual(ob.y + ob.height - 1);
  } else {
    expect(box.width).toBeGreaterThanOrEqual(vw - 2);
    expect(box.y + box.height).toBeGreaterThanOrEqual(vh - 2);
  }
  await noHorizontalScroll(page);
});

test('picking English updates the document, storage and button, and the search answers in English', async ({ page }) => {
  await boot(page);
  const { dialog } = await openDialog(page);
  await dialog.locator('.cs-lang-option[data-lang="en"]').click();
  await expect(page.locator('#csLangDialog[open]')).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');
  const stored = await page.evaluate(() => localStorage.getItem('paradiso:language'));
  expect(String(stored)).toContain('en');
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('EN');
  await page.fill('#civicQuery', 'residence card reissue');
  await page.press('#civicQuery', 'Enter');
  const sg = page.locator('#statusGuidance[data-sg-kind]');
  await expect(sg).toBeVisible({ timeout: 20_000 });
  await expect(sg.locator('#sgAnswerTitle')).toContainText('Residence card reissue');
  // the control is still reachable from the searched header
  await expect(page.locator('[data-cs-lang-open]:visible').first()).toBeVisible();
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('EN');
});

test('Arabic flips the page to RTL with no horizontal overflow, before and after a search', async ({ page }) => {
  await boot(page);
  const { dialog } = await openDialog(page);
  await dialog.locator('.cs-lang-option[data-lang="ar"]').click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe('rtl');
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('ع');
  await noHorizontalScroll(page);
  await page.fill('#civicQuery', '외국인등록증 재발급');
  await page.press('#civicQuery', 'Enter');
  await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  expect(await page.evaluate(() => document.documentElement.dir)).toBe('rtl');
  await expect(page.locator('[data-cs-lang-open]:visible').first()).toBeVisible();
  await noHorizontalScroll(page);
});

test('?lang=en bootstraps the control and the stored choice survives a reload', async ({ page }) => {
  await boot(page, '/index.html?lang=en');
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('EN');
  expect(await page.evaluate(() => document.documentElement.lang)).toBe('en');
  await page.goto('/index.html');
  await page.waitForFunction(() => !!document.querySelector('[data-cs-lang-open]'), null, { timeout: 30_000 });
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('EN');
});

test('the New Home language selector is untouched by the civic control', async ({ page }) => {
  await boot(page);
  const civic = await page.locator('[data-cs-lang-open]').count();
  expect(civic).toBeGreaterThan(0);
  // the civic dialog is created lazily and never replaces the global LANGUAGE_OPTIONS delegation
  // LANGUAGE_OPTIONS / isLanguageSelectable are script-scope globals in index.html (const/function), not window properties
  const usesGlobal = await page.evaluate(() => { try { return Array.isArray(LANGUAGE_OPTIONS) && LANGUAGE_OPTIONS.length === 15 && typeof isLanguageSelectable === 'function'; } catch (e) { return false; } });
  expect(usesGlobal).toBe(true);
});
