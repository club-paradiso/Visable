// Tools directory ("전체 도구 보기") and the searched-state header geometry.
//
//  - The full catalogue is a native <details> that starts CLOSED on a fresh visit.
//    The search field and the core tools own the first screen.
//  - Its summary toggles it (mouse, keyboard); the header link toggles it too and
//    mirrors the state through aria-expanded / aria-controls.
//  - A direct #csTools link (cross-page deep link) expands it so linked content
//    stays reachable; a language re-render keeps an intentional expansion.
//  - On a result page the language control keeps its intrinsic width at every
//    tablet width (681–820px used to stretch it across the header column) and the
//    page never scrolls horizontally.
import { test, expect } from '@playwright/test';

const hydrated = (page) => page.waitForSelector('#civicLanding[data-cs-hydrated="reused"], #civicLanding[data-cs-hydrated="rendered"]', { timeout: 30_000 });

test.describe('tools directory is collapsed by default', () => {
  test('fresh visit: closed; summary and header link toggle it; state is announced', async ({ page }) => {
    await page.goto('/');
    await hydrated(page);
    const dir = page.locator('#csTools');
    await expect(dir).toHaveCount(1);
    expect(await dir.evaluate((d) => d.tagName)).toBe('DETAILS');
    await expect(dir).toHaveJSProperty('open', false);
    // The first screen keeps the search form, the core tools and the summary reachable.
    await expect(page.locator('#civicQuery')).toBeVisible();
    await expect(page.locator('.cs-tools-core .cs-tool').first()).toBeVisible();
    await expect(dir.locator('summary')).toBeVisible();
    await expect(dir.locator('.cs-service').first()).toBeHidden();

    await dir.locator('summary').click();
    await expect(dir).toHaveJSProperty('open', true);
    await expect(dir.locator('.cs-service').first()).toBeVisible();
    await dir.locator('summary').click();
    await expect(dir).toHaveJSProperty('open', false);
    await expect(dir.locator('.cs-service').first()).toBeHidden();

    const link = page.locator('[data-cs-open-tools]');
    await expect(link).toHaveAttribute('aria-controls', 'csTools');
    await expect(link).toHaveAttribute('aria-expanded', 'false');
    if (await link.isVisible()) {
      await link.click();
      await expect(dir).toHaveJSProperty('open', true);
      await expect(link).toHaveAttribute('aria-expanded', 'true');
      await link.click();
      await expect(dir).toHaveJSProperty('open', false);
      await expect(link).toHaveAttribute('aria-expanded', 'false');
    }
  });

  test('keyboard: Enter and Space on the summary expand and collapse', async ({ page }) => {
    await page.goto('/');
    await hydrated(page);
    const dir = page.locator('#csTools');
    await dir.locator('summary').focus();
    await page.keyboard.press('Enter');
    await expect(dir).toHaveJSProperty('open', true);
    await expect(page.locator('[data-cs-open-tools]')).toHaveAttribute('aria-expanded', 'true');
    await page.keyboard.press('Space');
    await expect(dir).toHaveJSProperty('open', false);
    await expect(page.locator('[data-cs-open-tools]')).toHaveAttribute('aria-expanded', 'false');
  });

  test('direct #csTools navigation expands the directory', async ({ page }) => {
    await page.goto('/#csTools');
    await hydrated(page);
    const dir = page.locator('#csTools');
    await expect(dir).toHaveJSProperty('open', true);
    await expect(dir.locator('.cs-service').first()).toBeVisible();
    await expect(page.locator('[data-cs-open-tools]')).toHaveAttribute('aria-expanded', 'true');
  });

  test('an intentional expansion survives a language change', async ({ page }) => {
    await page.goto('/');
    await hydrated(page);
    const dir = page.locator('#csTools');
    await dir.locator('summary').click();
    await expect(dir).toHaveJSProperty('open', true);
    await page.locator('#civicLanding [data-cs-lang-open]').click();
    await page.locator('#csLangDialog [data-action="apply-language"][data-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('#csTools')).toHaveJSProperty('open', true);
    await expect(page.locator('[data-cs-open-tools]')).toHaveAttribute('aria-expanded', 'true');
    // and a fresh visit in that language still starts closed
    await page.goto('/');
    await hydrated(page);
    await expect(page.locator('#csTools')).toHaveJSProperty('open', false);
  });
});

test.describe('result page header geometry', () => {
  test('the language control stays compact and nothing overflows (phones, tablets, desktop)', async ({ page }) => {
    await page.goto('/?q=' + encodeURIComponent('F-4 체류기간 연장'));
    await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 30_000 });
    for (const [w, h] of [[320, 568], [360, 780], [390, 844], [430, 932], [680, 900], [681, 900], [768, 1024], [820, 1180], [1024, 768], [1180, 820], [1280, 900], [1440, 900]]) {
      await page.setViewportSize({ width: w, height: h });
      await page.waitForTimeout(80);
      const geo = await page.evaluate(() => {
        const b = document.querySelector('#hero .cs-lang-searched');
        const r = b.getBoundingClientRect();
        const header = document.querySelector('#hero .header-inner').getBoundingClientRect();
        return { w: r.width, h: r.height, right: r.right, headerRight: header.right, scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth };
      });
      expect(geo.w, `language control width at ${w}px`).toBeLessThanOrEqual(72);
      expect(geo.w, `touch target width at ${w}px`).toBeGreaterThanOrEqual(44);
      expect(geo.h, `touch target height at ${w}px`).toBeGreaterThanOrEqual(44);
      expect(geo.right, `language control inside the header at ${w}px`).toBeLessThanOrEqual(geo.headerRight + 1);
      expect(geo.scrollW, `no horizontal page overflow at ${w}px`).toBeLessThanOrEqual(geo.innerW);
    }
  });
});
