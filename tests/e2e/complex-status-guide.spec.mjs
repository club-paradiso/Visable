// Real-browser QA for the complex status guide (F-4 + F-6/G-1/E-7/F-5/D-2/D-4).
//
// Covers what the offline harness (scripts/check_complex_status_guide_qa.mjs)
// cannot: actual rendering, viewport overflow/clipping, overlay sizing, focus,
// keyboard, and theme rendering. Run locally per playwright.config.mjs.
//
// NOTE: This suite was authored from the verified rendered strings/selectors but
// could not be executed in the build sandbox (the Playwright browser CDN is
// blocked by network egress). Treat the first local run as the verification step;
// selectors are grounded in assets/js/{f4-route-guide,complex-status-guide}.js.
import { test, expect } from '@playwright/test';

const SIX = ['F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];
const ALL = ['F-4', ...SIX];

// Overlay + CTA selectors differ between the F-4 module and the shared CSG module.
function sel(code) {
  return code === 'F-4'
    ? { overlay: '#f4HubModalOverlay', startAttr: '[data-f4g-start]', closeAttr: '[data-f4h-close]', opt: '[data-f4g-opt]', foot: '[data-f4g-foot]' }
    : { overlay: '#csgOverlay', startAttr: '[data-csg-start]', closeAttr: '[data-csg-close]', opt: '[data-csg-opt]', foot: '[data-csg-foot]' };
}
const ctaKo = (code) => `내 상황에 맞는 ${code} 준비서류 찾기`;

async function searchStatus(page, code) {
  await page.goto('/index.html');
  // Wait for the app's data to be ready (backend API absent → static fallback).
  await page.waitForFunction(() => typeof window.VISA_DATA !== 'undefined' || (typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 0), null, { timeout: 30_000 })
    .catch(() => {});
  await page.waitForFunction(() => (typeof dataReady !== 'undefined' && dataReady) === true, null, { timeout: 30_000 });
  // Drive the real search path (the search form starts hidden / input disabled).
  await page.evaluate((c) => {
    const form = document.getElementById('searchForm'); if (form) form.style.display = '';
    const q = document.getElementById('q'); if (q) { q.disabled = false; q.value = c; }
    if (typeof executeSearch === 'function') executeSearch();
    else if (typeof renderResults === 'function') renderResults(c);
  }, code);
  // Ensure the status card rendered and is expanded so its slot is visible.
  const card = page.locator(`#rlist .vc[data-code="${code}"]`);
  await card.first().waitFor({ timeout: 15_000 });
  await page.evaluate((c) => {
    const card = document.querySelector(`#rlist .vc[data-code="${c}"]`);
    if (card && !card.classList.contains('open')) {
      const h = card.querySelector('.vc-h, [data-action="toggle-detail"]');
      if (h) h.click();
    }
  }, code);
}

test.describe('recommended-start block + no horizontal overflow (all statuses)', () => {
  for (const code of ALL) {
    test(`${code}: block + primary CTA visible, no overflow`, async ({ page }) => {
      await searchStatus(page, code);
      // No horizontal overflow at any viewport.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      // Recommended-start CTA present and visible.
      const cta = page.getByRole('button', { name: ctaKo(code) });
      await expect(cta.first()).toBeVisible();
      // Touch target tall enough.
      const box = await cta.first().boundingBox();
      expect(box && box.height).toBeGreaterThanOrEqual(44);
    });
  }
});

test.describe('guided flow opens wide, one question per step, checklist result', () => {
  for (const code of ['F-4', 'F-6']) { // full deep flow for the two strongest
    test(`${code}: open → steps → checklist result → close + focus restore`, async ({ page }, testInfo) => {
      await searchStatus(page, code);
      const s = sel(code);
      const cta = page.getByRole('button', { name: ctaKo(code) }).first();
      await cta.focus();
      await page.keyboard.press('Enter'); // keyboard-activatable
      const overlay = page.locator(s.overlay);
      await expect(overlay).toBeVisible();
      // Wide / full-screen, not a tiny modal: box >= 60% of viewport width.
      const box = await overlay.locator('.csg-box, .f4h-box').boundingBox();
      const vw = page.viewportSize().width;
      expect(box.width).toBeGreaterThanOrEqual(Math.min(vw, 0.6 * vw));
      // One question visible with options.
      await expect(overlay.locator(s.opt).first()).toBeVisible();
      // Walk the flow: pick the first option each step, then advance, until result.
      for (let i = 0; i < 6; i++) {
        const opts = overlay.locator(s.opt);
        if (await opts.count()) await opts.first().click();
        const next = overlay.locator(`${s.foot} button`).last();
        if (await next.isEnabled()) await next.click();
        if (await overlay.locator('text=먼저 해야 할 일').count()) break;
      }
      // Checklist-first result: the spec sections appear.
      await expect(overlay.getByText('먼저 해야 할 일')).toBeVisible();
      await expect(overlay.getByText('기본 준비서류')).toBeVisible();
      await expect(overlay.getByText('신청 절차')).toBeVisible();
      // Use .first(): the result's section title is "공식 근거", but an explanatory
      // note also contains the substring "공식 근거(매뉴얼·출처)…", so a bare
      // getByText matches 2 elements and trips strict mode. .first() (the title,
      // which renders before the note) is template-agnostic across the CSG and
      // F-4 hub result layouts.
      await expect(overlay.getByText('공식 근거').first()).toBeVisible();
      // ESC closes + focus returns to the trigger CTA.
      await page.keyboard.press('Escape');
      await expect(overlay).toBeHidden();
      const focused = await page.evaluate(() => document.activeElement && document.activeElement.textContent || '');
      expect(focused).toContain('준비서류 찾기');
      await testInfo.attach(`${code}-result`, { body: await page.screenshot(), contentType: 'image/png' });
    });
  }
});

test.describe('themes render (civic_editorial + archive_diary)', () => {
  for (const theme of ['civic_editorial', 'archive_diary']) {
    test(`${theme}: F-6 guide opens and result renders`, async ({ page }) => {
      await page.addInitScript((t) => { try { localStorage.setItem('paradiso-theme', t); } catch (e) {} }, theme);
      await searchStatus(page, 'F-6');
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
      const cta = page.getByRole('button', { name: ctaKo('F-6') }).first();
      await cta.click();
      const overlay = page.locator('#csgOverlay');
      await expect(overlay).toBeVisible();
      // Surfaces must have a real (theme-token) background, not transparent.
      const bg = await overlay.locator('.csg-box').evaluate((el) => getComputedStyle(el).backgroundColor);
      expect(bg).not.toBe('rgba(0, 0, 0, 0)');
    });
  }
});
