// Search result hierarchy (pre-launch rescue 2026-10-24).
//
//  D-3 체류기간 연장 (source-only) must read, top to bottom: identity → the manual
//  page as the primary action → an "at a glance" overview (confirmed / depends on
//  the case / check in the source) → cost → the 동포 scheme as a COLLAPSED,
//  conditional block → labelled next-action rows → evidence with the procedure's
//  page first and fee law behind a disclosure. D-2 (structured) keeps documents
//  before cost with the evidence collapsed. Unknown codes are named. The result
//  never overflows horizontally, every action row is a 44px+ target, headings
//  nest (one h2, then h3s), and the English and dark faces render the same
//  structure. Browser back/forward restores the previous result.
import { test, expect } from '@playwright/test';

const q = (s) => '/?q=' + encodeURIComponent(s);
const ready = (page, kind) => page.waitForSelector(`#statusGuidance[data-sg-kind="${kind}"]`, { timeout: 30_000 });
async function noHorizontalScroll(page) {
  const o = await page.evaluate(() => ({ s: document.documentElement.scrollWidth, w: window.innerWidth }));
  expect(o.s, 'no horizontal overflow').toBeLessThanOrEqual(o.w);
}
const topOf = (loc) => loc.evaluate((el) => el.getBoundingClientRect().top + window.scrollY);

test.describe('F-4 extension result (structured from the compatriot handbook)', () => {
  test('lists the manual documents and cites the F-4 page, not the H-2 page', async ({ page }) => {
    await page.goto(q('F-4 체류기간 연장'));
    await ready(page, 'resolved');
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('F-4');
    await expect(sg).toContainText('한국어능력 입증서류');
    await expect(sg).toContainText('체류지 입증서류');
    await expect(sg).not.toContainText('정리된 안내가 아직 없어요');
    await expect(sg.locator('[data-sg-page="537"]')).toHaveCount(0);
    await expect(sg).not.toContainText('세부유형을 확인하면');
    await noHorizontalScroll(page);
  });
});

test.describe('D-3 extension result (source-only)', () => {
  test('hierarchy: identity, source action, overview, fee, collapsed scheme, actions, grouped evidence', async ({ page }) => {
    await page.goto(q('D-3 체류기간 연장'));
    await ready(page, 'source-only');
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('D-3');
    await expect(sg.locator('.sg-source-only .sg-lead')).toContainText('정리된 안내가 아직 없어요');
    const srcBtn = sg.locator('.sg-answer .sg-btn-source');
    await expect(srcBtn).toBeVisible();
    await expect(srcBtn).toContainText('공식 원문 56쪽 보기');

    const overview = sg.locator('.sg-overview');
    await expect(overview).toBeVisible();
    await expect(overview.locator('.sg-ov-confirmed')).toContainText('수수료 ₩60,000');
    await expect(overview.locator('.sg-ov-source')).toContainText('56쪽');
    await expect(overview).toContainText('2026년 10월판');
    await expect(sg).not.toContainText('9월판');

    // order on the page
    const order = [sg.locator('.sg-answer'), overview, sg.locator('.sg-fee'), sg.locator('.sg-next'), sg.locator('.sg-evidence')];
    let last = -1;
    for (const loc of order) { const t = await topOf(loc); expect(t).toBeGreaterThan(last); last = t; }

    // D-3 belongs to no special scheme
    await expect(sg.locator('.sg-program-details')).toHaveCount(0);

    // no inapplicable fee exemptions for D-3
    await expect(sg.locator('.sg-fee')).not.toContainText('면제·감경 조건');

    // evidence: open, procedure page first, fee law behind a disclosure
    const ev = sg.locator('#sgEvidence');
    await expect(ev).toHaveAttribute('open', /.*/);
    await expect(ev.locator('.sg-ev-group')).toContainText('이 절차의 공식 안내');
    await expect(ev.locator('.sg-ev-primary')).toContainText('56쪽');
    const more = ev.locator('.sg-ev-more');
    await expect(more).toHaveJSProperty('open', false);
    await expect(more.locator('> summary')).toContainText(/수수료·법령 근거 \d+건/);
    await more.locator('> summary').click();
    await expect(more.locator('.sg-ev-law').first()).toBeVisible();
    await noHorizontalScroll(page);
  });

  test('the primary source action opens the manual page; action rows are 44px+ targets', async ({ page }) => {
    await page.goto(q('D-3 체류기간 연장'));
    await ready(page, 'source-only');
    const sg = page.locator('#statusGuidance');
    const rows = sg.locator('.sg-next .sg-actions li > .sg-action');
    await expect(rows).toHaveCount(4);
    // one call to action each: the page lives in the answer head, Waymaker in its own block
    await expect(sg.locator('[data-sg-action="open-page"][data-sg-page="56"]')).toHaveCount(2);
    await expect(sg.locator('[data-sg-action="followup"]')).toHaveCount(1);
    await expect(rows.first()).toContainText('방문예약 안내');
    await page.waitForSelector('#statusGuidance[data-sg-state="ready"], body[data-sg-state="ready"]');
    await page.waitForTimeout(300);
    const rects = await page.evaluate(() => [...document.querySelectorAll('#statusGuidance .sg-next .sg-actions li > .sg-action')].map((e) => { const r = e.getBoundingClientRect(); return { w: r.width, h: r.height }; }));
    expect(rects.length).toBe(4);
    for (const r of rects) { expect(r.h).toBeGreaterThanOrEqual(44); expect(r.w).toBeGreaterThanOrEqual(44); }
    // the phone-only F-4 band does not sit over the structured answer
    const band = page.locator('#f4gStickyCta');
    if (await band.count()) await expect(band).toBeHidden();
    await sg.locator('.sg-answer .sg-btn-source').click();
    const dialog = page.locator('#civicPageDialog[open]');
    await expect(dialog).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('#civicPageTitle')).not.toHaveText('');
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    // focus returns to the opener
    await expect(sg.locator('.sg-answer .sg-btn-source')).toBeFocused();
  });

  test('heading structure nests: one h2 answer title, then h3 sections', async ({ page }) => {
    await page.goto(q('D-3 체류기간 연장'));
    await ready(page, 'source-only');
    const levels = await page.locator('#statusGuidance h2, #statusGuidance h3').evaluateAll((els) => els.filter((e) => !e.classList.contains('sg-sr')).map((e) => e.tagName));
    expect(levels[0]).toBe('H2');
    expect(levels.filter((l) => l === 'H2').length).toBe(1);
    expect(levels.length).toBeGreaterThan(4);
  });

  test('English copy mirrors the structure and names the edition from the bundle', async ({ page }) => {
    await page.goto(q('D-3 체류기간 연장'));
    await ready(page, 'source-only');
    await page.locator('#hero .cs-lang-searched').click();
    await page.locator('#csLangDialog [data-action="apply-language"][data-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('.sg-overview h3')).toHaveText('At a glance', { timeout: 10_000 });
    await expect(sg.locator('.sg-overview')).toContainText('October 2026');
    await expect(sg.locator('.sg-answer .sg-btn-source')).toContainText('Open the source, p.56');
    await expect(sg.locator('.sg-next .sg-action').first()).toContainText('Visit reservation guide');
    await expect(sg).not.toContainText('September');
    await noHorizontalScroll(page);
  });

  test('dark face keeps the overview and action rows visible', async ({ page }) => {
    await page.goto(q('D-3 체류기간 연장'));
    await ready(page, 'source-only');
    await page.evaluate(() => { document.documentElement.setAttribute('data-theme', 'dark'); document.body.setAttribute('data-theme', 'dark'); });
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('.sg-overview')).toBeVisible();
    await expect(sg.locator('.sg-next .sg-action').first()).toBeVisible();
    // Contrast of overview text on its panel (WCAG AA body text ≥ 4.5:1). Query fresh inside
    // the page: the result re-renders once more when the legacy list loads, so a locator
    // handle taken earlier can point at a detached node.
    await page.waitForSelector('body[data-sg-state="ready"]');
    await page.waitForTimeout(300);
    const ratio = await page.evaluate(() => {
      const li = document.querySelector('#statusGuidance .sg-ov-group li');
      const rgb = (s) => { const m = s.match(/[\d.]+/g) || []; return m.length >= 3 ? m.slice(0, 3).map(Number) : null; };
      const lum = ([r, g, b]) => { const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
      let el = li, bg = null;
      while (el && !bg) { const c = getComputedStyle(el).backgroundColor; const p = rgb(c); if (p && !/rgba\(.*, 0\)$/.test(c)) bg = p; el = el.parentElement; }
      const fg = rgb(getComputedStyle(li).color);
      if (!fg || !bg) return null;
      const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
      return (a + 0.05) / (b + 0.05);
    });
    expect(ratio).not.toBeNull();
    expect(ratio).toBeGreaterThanOrEqual(4.5);
    await noHorizontalScroll(page);
  });
});

test.describe('structured and unknown results', () => {
  test('D-2 extension: overview between answer and documents, evidence collapsed, no scheme block', async ({ page }) => {
    await page.goto(q('D-2 체류기간 연장'));
    await ready(page, 'resolved');
    // measure only after the guide has settled (a late re-render detaches the nodes)
    await page.waitForSelector('#statusGuidance[data-sg-state="ready"], body[data-sg-state="ready"]');
    await page.waitForLoadState('networkidle');
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('.sg-overview .sg-ov-confirmed')).toContainText('필수 서류 6개');
    await expect(sg.locator('.sg-overview .sg-ov-conditional')).toContainText('조건에 따라 내는 서류 1개');
    const order = [sg.locator('.sg-answer'), sg.locator('.sg-overview'), sg.locator('.sg-docs'), sg.locator('.sg-fee'), sg.locator('.sg-cond-section'), sg.locator('.sg-next'), sg.locator('.sg-evidence')];
    let last = -1;
    for (const loc of order) { const t = await topOf(loc); expect(t).toBeGreaterThan(last); last = t; }
    await expect(sg.locator('.sg-program')).toHaveCount(0);
    await expect(sg.locator('#sgEvidence')).not.toHaveAttribute('open', /.*/);
    await expect(sg.locator('.sg-fee')).toContainText('면제·감경 조건 · 2');
    await expect(sg.locator('.sg-next .sg-action').first()).toContainText('방문예약 안내');
    await noHorizontalScroll(page);
  });

  test('an unknown code is named instead of silently dropped', async ({ page }) => {
    await page.goto(q('Z-9 연장'));
    await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 30_000 });
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('.sg-warn').first()).toContainText('Z-9');
    await expect(sg.locator('.sg-warn').first()).toContainText('확인되지 않는 코드');
    await expect(sg).not.toContainText('9월 기준');
  });

  test('"D-2에서 D-10 변경" answers for the target status D-10 as a status change', async ({ page }) => {
    await page.goto(q('D-2에서 D-10 변경'));
    await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 30_000 });
    const sg = page.locator('#statusGuidance');
    await expect(sg.locator('.sg-interp-code')).toHaveText('D-10');
    await expect(sg.locator('.sg-interp-proc')).toContainText('체류자격 변경');
  });

  test('browser back and forward restore the previous result', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#civicLanding[data-cs-hydrated]');
    await page.locator('#civicQuery').fill('D-2 체류기간 연장');
    await page.locator('#civicSearchForm').evaluate((f) => f.requestSubmit());
    await ready(page, 'resolved');
    await page.locator('#q').fill('F-4 체류기간 연장');
    await page.locator('#q').press('Enter');
    await ready(page, 'resolved');
    await expect(page.locator('#statusGuidance #sgAnswerTitle')).toContainText('F-4', { timeout: 15_000 });
    await page.goBack();
    await expect(page.locator('#statusGuidance #sgAnswerTitle')).toContainText('D-2', { timeout: 15_000 });
    await page.goForward();
    await expect(page.locator('#statusGuidance #sgAnswerTitle')).toContainText('F-4', { timeout: 15_000 });
  });
});
