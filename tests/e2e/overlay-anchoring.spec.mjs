// Real-browser regression for header overlay anchoring (assets/js/anchored-overlay.js).
//
// Defect (2026-10-28): the KO language panel opened at the left edge of the screen.
// The modal <dialog> carries the UA rule `inset-inline-start: 0`; the old code set
// only `top` + `right` with a fixed width, so the box was over-constrained and the
// browser dropped `right`. These tests pin the trigger ↔ panel geometry:
//
//   * desktop/tablet (>680px): the panel opens under the trigger, end-aligned
//     (right edges in LTR, left edges in RTL), fully inside the viewport;
//   * ≤680px: a full-width bottom sheet;
//   * still attached after page scroll, window resize and theme switches;
//   * backdrop click / Escape close it, focus returns to the trigger, also after
//     a language pick re-renders the header buttons;
//   * ↑/↓/Home/End move through the languages;
//   * the theme picker shares the same anchoring.
//
// Visual baselines: set PARADISO_VISUAL=1 to also compare screenshots
// (`npx playwright test overlay-anchoring --update-snapshots` writes them).
import { test, expect } from '@playwright/test';

const POPOVER_MIN = 681;

async function boot(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('[data-cs-lang-open]') && !!window.VisableOverlay; } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}

async function viewport(page) {
  return page.evaluate(() => ({ w: document.documentElement.clientWidth, h: document.documentElement.clientHeight, rtl: document.documentElement.dir === 'rtl' }));
}

async function openLang(page) {
  const opener = page.locator('[data-cs-lang-open]:visible').first();
  await opener.click();
  const panel = page.locator('#csLangDialog[open]');
  await expect(panel).toBeVisible();
  await expect(opener).toHaveAttribute('aria-expanded', 'true');
  return { opener, panel };
}

// The geometric contract shared by every anchored overlay.
async function expectAnchored(page, opener, panel, label) {
  const vp = await viewport(page);
  const o = await opener.boundingBox();
  const p = await panel.boundingBox();
  expect(o, `${label}: trigger box`).not.toBeNull();
  expect(p, `${label}: panel box`).not.toBeNull();
  // fully inside the viewport
  expect(p.x, `${label}: panel left ${p.x}`).toBeGreaterThanOrEqual(0);
  expect(p.y, `${label}: panel top ${p.y}`).toBeGreaterThanOrEqual(0);
  expect(p.x + p.width, `${label}: panel right ${p.x + p.width} > ${vp.w}`).toBeLessThanOrEqual(vp.w + 1);
  expect(p.y + p.height, `${label}: panel bottom ${p.y + p.height} > ${vp.h}`).toBeLessThanOrEqual(vp.h + 1);
  if (vp.w >= POPOVER_MIN) {
    // below the trigger (or above it when there is no room below), with a gap
    const below = p.y >= o.y + o.height + 2 && p.y - (o.y + o.height) <= 16;
    const above = p.y + p.height <= o.y - 2 && o.y - (p.y + p.height) <= 16;
    expect(below || above, `${label}: panel y ${p.y} not adjacent to trigger ${o.y}-${o.y + o.height}`).toBe(true);
    // end-aligned with the trigger, unless clamped by the viewport margin
    const edgeGap = vp.rtl ? Math.abs(p.x - o.x) : Math.abs(p.x + p.width - (o.x + o.width));
    const clamped = vp.rtl ? p.x + p.width >= vp.w - 13 : p.x <= 13;
    expect(edgeGap <= 1.5 || clamped, `${label}: panel ${vp.rtl ? 'left' : 'right'} edge off the trigger by ${edgeGap}px`).toBe(true);
    // horizontally overlaps the trigger column (never stranded on the far side)
    expect(p.x < o.x + o.width && p.x + p.width > o.x, `${label}: panel does not overlap the trigger column`).toBe(true);
  } else {
    expect(p.width, `${label}: sheet width`).toBeGreaterThanOrEqual(vp.w - 2);
    expect(p.y + p.height, `${label}: sheet bottom`).toBeGreaterThanOrEqual(vp.h - 2);
  }
}

test('KO opens the language panel anchored to the button and inside the viewport', async ({ page }, info) => {
  await boot(page);
  const { opener, panel } = await openLang(page);
  await expectAnchored(page, opener, panel, 'home');
  await info.attach('language-panel-home', { body: await page.screenshot(), contentType: 'image/png' });
  if (process.env.PARADISO_VISUAL) await expect(page).toHaveScreenshot('language-panel-home.png', { maxDiffPixelRatio: 0.02, animations: 'disabled' });
});

test('the panel stays attached after a search, a page scroll and while scrolling with it open', async ({ page }, info) => {
  await boot(page);
  await page.fill('#civicQuery', 'F-6 체류기간 연장');
  await page.press('#civicQuery', 'Enter');
  await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(250);
  const { opener, panel } = await openLang(page);
  await expectAnchored(page, opener, panel, 'searched+scrolled');
  // scrolling the page under the open modal must not detach the panel
  await page.mouse.move(5, 5);
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(250);
  if (await opener.isVisible()) await expectAnchored(page, opener, panel, 'scrolled while open');
  await info.attach('language-panel-searched', { body: await page.screenshot(), contentType: 'image/png' });
});

test('resizing while open keeps the panel attached and switches popover ↔ sheet', async ({ page }) => {
  await boot(page);
  const { opener, panel } = await openLang(page);
  for (const [w, h] of [[1440, 900], [900, 800], [700, 800], [520, 800], [1200, 800]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(200);
    await expectAnchored(page, opener, panel, `resize ${w}`);
  }
});

test('Escape and a backdrop click close the panel and return focus; repeated opens are stable', async ({ page }) => {
  await boot(page);
  const boxes = [];
  for (let i = 0; i < 4; i++) {
    const { opener, panel } = await openLang(page);
    boxes.push(await panel.boundingBox());
    if (i % 2) {
      // a point on the backdrop: bottom-left beside the popover, top-left above the sheet
      const vp = await viewport(page);
      await page.mouse.click(4, vp.w >= POPOVER_MIN ? vp.h - 4 : 4);
    } else {
      await page.keyboard.press('Escape');
    }
    await expect(page.locator('#csLangDialog[open]')).toHaveCount(0);
    await expect(opener).toHaveAttribute('aria-expanded', 'false');
    expect(await page.evaluate(() => document.activeElement && document.activeElement.hasAttribute('data-cs-lang-open'))).toBe(true);
  }
  for (const b of boxes.slice(1)) {
    expect(Math.round(b.x)).toBe(Math.round(boxes[0].x));
    expect(Math.round(b.y)).toBe(Math.round(boxes[0].y));
  }
});

test('keyboard: Enter opens, arrows move, Enter picks, the panel closes and focus returns to the new button', async ({ page }) => {
  await boot(page);
  const opener = page.locator('[data-cs-lang-open]:visible').first();
  await opener.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#csLangDialog[open]')).toBeVisible();
  const active = () => page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-lang'));
  expect(await active()).toBe('ko');
  await page.keyboard.press('End');
  const last = await active();
  await page.keyboard.press('Home');
  expect(await active()).not.toBe(last);
  const first = await active();
  await page.keyboard.press('ArrowDown');
  expect(await active()).not.toBe(first);
  // pick English with the keyboard
  await page.locator('#csLangDialog .cs-lang-option[data-lang="en"]').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#csLangDialog[open]')).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');
  await expect.poll(() => page.evaluate(() => document.activeElement && document.activeElement.hasAttribute('data-cs-lang-open'))).toBe(true);
  await expect(page.locator('[data-cs-lang-open]:visible .cs-lang-code').first()).toHaveText('EN');
  expect(String(await page.evaluate(() => localStorage.getItem('paradiso:language')))).toContain('en');
});

test('Arabic (RTL): the panel aligns to the mirrored button', async ({ page }) => {
  await boot(page);
  let { panel } = await openLang(page);
  await panel.locator('.cs-lang-option[data-lang="ar"]').click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe('rtl');
  const again = await openLang(page);
  await expectAnchored(page, again.opener, again.panel, 'rtl');
});

test('the theme picker shares the anchoring, and the language panel stays anchored in every theme', async ({ page }) => {
  await boot(page);
  for (const skin of ['stamp', 'chrome', 'neon', 'default']) {
    const themeBtn = page.locator('[data-vt-open]:visible').first();
    await themeBtn.click();
    const pop = page.locator('#vtCivicPop:not([hidden])');
    await expect(pop).toBeVisible();
    const vp = await viewport(page);
    if (vp.w > 600) await expectAnchored(page, themeBtn, pop, `theme picker (${skin})`);
    await pop.locator(`.vt-opt[data-vt-value="${skin}"]`).click();
    await expect.poll(() => page.evaluate(() => document.documentElement.getAttribute("data-vt"))).toBe(skin);
    await page.keyboard.press('Escape');
    await expect(pop).toHaveCount(0);
    const { opener, panel } = await openLang(page);
    await expectAnchored(page, opener, panel, `language in ${skin}`);
    await page.keyboard.press('Escape');
  }
});
