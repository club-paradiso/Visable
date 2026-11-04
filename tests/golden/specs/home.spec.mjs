// Golden: the search-first home in every shipped UI language, desktop + mobile.
// Expected copy comes from data/i18n/<locale>.json (`civic` object, footer keys).
import { test, expect } from '@playwright/test';
import { LOCALES, RTL, pack, stripTags, localeLabel } from '../helpers/data.mjs';
import { boot, bodyText, normalize, noHorizontalScroll, storage } from '../helpers/page.mjs';

for (const locale of LOCALES) {
  test(`home renders in ${locale} from its i18n pack`, async ({ page }, testInfo) => {
    const p = pack(locale);
    const c = p.civic;
    const errors = await boot(page, { query: { lang: locale } });
    // zh-TW renders the zh-CN pack converted to Traditional characters; its copy
    // is not stored anywhere, so only language/structure is asserted for it.
    const textual = locale !== 'zh-TW';
    await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe(locale);
    expect(await page.evaluate(() => document.documentElement.dir || 'ltr')).toBe(RTL.has(locale) ? 'rtl' : 'ltr');
    const text = normalize(await bodyText(page));
    if (textual) {
      expect(text).toContain(normalize(stripTags(c.title)));
      expect(text).toContain(normalize(c.sub));
      expect(text).toContain(normalize(c.examples));
      expect(text).toContain(normalize(c.coreTools));
      // Checklist entry is intentionally not a primary home tool anymore.
      // Its label remains reachable through the full tools directory.
      expect(text).toContain(normalize(c.allTools));
      // The footer disclaimer must be on every home.
      expect(text).toContain(normalize(c.disclaimer));
    }
    await expect(page.locator('.cs-tools-core .cs-tool')).toHaveCount(5);
    await expect(page.locator('.cs-tools-core [data-cs-tool="checklists"]')).toHaveCount(0);
    await expect(page.locator('.cs-directory a[href="immigration-checklists.html"]')).toHaveCount(1);
    // The language control is present; on desktop it shows the current language by its native name
    // (the phone header shows the short code instead).
    const opener = page.locator('[data-cs-lang-open]:visible').first();
    await expect(opener).toBeVisible();
    await expect(opener).toHaveAttribute('aria-expanded', 'false');
    if (testInfo.project.name.startsWith('desktop')) expect(text).toContain(localeLabel(locale));
    // The search field is a labelled combobox the user can type into.
    await expect(page.getByRole('combobox').first()).toBeVisible();
    await noHorizontalScroll(page);
    expect(errors, 'no uncaught page errors').toEqual([]);
  });
}

test('the language dialog lists all 15 shipped languages and applying one persists it', async ({ page }) => {
  await boot(page);
  const opener = page.locator('[data-cs-lang-open]:visible').first();
  await opener.click();
  const dialog = page.getByRole('dialog').filter({ has: page.getByRole('listbox') }).first();
  await expect(dialog).toBeVisible();
  const options = dialog.getByRole('option');
  await expect(options).toHaveCount(LOCALES.length);
  for (const locale of LOCALES) await expect(options.filter({ hasText: localeLabel(locale) }).first()).toBeVisible();
  await options.filter({ hasText: localeLabel('en') }).first().click();
  const en = pack('en').civic;
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');
  await expect(page.getByText(normalize(stripTags(en.title)), { exact: false }).first()).toBeVisible();
  // The choice is the returning user's state (storage key contract, phase0-inventory B).
  expect(await storage(page, 'paradiso:language')).toBe('en');
  await page.reload();
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');
});

for (const locale of ['ko', 'en']) {
  test(`landing tools and entries are present and link to the right pages (${locale})`, async ({ page }) => {
    const c = pack(locale).civic;
    await boot(page, { query: { lang: locale } });
    await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe(locale);
    await expect(page.getByText(normalize(c.coreTools), { exact: false }).first()).toBeVisible();
    const text = normalize(await bodyText(page));
    // Five primary tools; the detailed checklist is preserved in the directory.
    for (const key of ['paperwork', 'manuals', 'allTools']) expect(text, key).toContain(normalize(c[key]));
    await expect(page.locator('.cs-tools-core .cs-tool')).toHaveCount(5);
    await expect(page.locator('.cs-directory a[href="immigration-checklists.html"]')).toHaveCount(1);
    // Manual reader and form helper are reachable from the home (the header "forms" link folds away on phones).
    await expect(page.locator('a[href^="manual.html"]:visible').first()).toBeVisible();
    await expect(page.locator('a[href^="form-helper.html"]').first()).toBeAttached();
    // Waymaker entry carries its name.
    expect(text).toContain('Waymaker');
  });
}
