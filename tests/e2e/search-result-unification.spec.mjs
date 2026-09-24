// Search result unification (2026-09-23): one result system, reliable wording,
// relevant evidence, and no legacy frame on the way there.
//
//   * D-2: exact interpretation, no "가장 가까워 보여요", no legacy interpretation
//     ("이렇게 이해했어요"), no internal source ids, no 2026-05 / 2026.6 labels,
//     no repeated preparation paragraphs, raw passages collapsed, no expanded
//     unrelated procedure, one design system (only the guidance renders);
//   * D-2 → 체류기간 연장: one fee note; evidence ranks D-2 extension pages first,
//     never D-2 → E-1 (p.173) / D-2 → D-10 (p.210);
//   * the searched state never paints the legacy card, the legacy caution band or
//     the backend layer — sampled every frame from submit to ready, throttled;
//   * a result URL (?q=) never paints the landing or the legacy list;
//   * 390×844: interpretation, answer and one action inside the first screen;
//   * Arabic: the page stays RTL, the guidance block is English LTR, no overflow.
import { test, expect } from '@playwright/test';

async function boot(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery') && !!window.VisableCivicSearch; } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}
async function search(page, query) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const sel = searched ? '#q' : '#civicQuery';
  await page.fill(sel, query);
  await page.press(sel, 'Enter');
  const sg = page.locator('#statusGuidance[data-sg-kind]');
  await expect(sg).toBeVisible({ timeout: 20_000 });
  return sg;
}
const visibleText = (page) => page.evaluate(() => document.getElementById('mainContent').innerText);

// Frame sampler: one entry per painted frame (rAF), from before the action until told to stop.
const FRAME_LOG = () => {
  window.__frames = [];
  const vis = (el) => { if (!el) return false; const cs = getComputedStyle(el); const r = el.getBoundingClientRect(); return cs.display !== 'none' && cs.visibility !== 'hidden' && r.height > 0; };
  const tick = () => {
    const b = document.body;
    if (b) {
      window.__frames.push({
        t: Math.round(performance.now()),
        searched: b.classList.contains('searched'),
        landingVisible: vis(document.getElementById('civicLanding')),
        rlist: vis(document.getElementById('rlist')) && !!document.querySelector('#rlist article.vc'),
        band: vis(document.querySelector('#hero .reference-disclaimer')),
        usLayer: vis(document.getElementById('unifiedSearchLayer')),
        guidance: !!document.querySelector('#statusGuidance[data-sg-kind]'),
      });
    }
    if (!window.__stopFrames && window.__frames.length < 6000) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
};

test.describe('D-2 regression (from the D-2 bug report)', () => {
  test('exact interpretation, one result system, no legacy or internal strings', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2');
    await expect(sg.locator('.sg-interp')).toHaveAttribute('data-sg-match', 'EXACT_CODE');
    await expect(sg.locator('.sg-interp-code')).toHaveText('D-2');
    await expect(sg.locator('.sg-interp-name')).toContainText('유학');
    const text = await visibleText(page);
    expect(text).not.toContain('가장 가까워 보여요');
    expect(text).not.toContain('이렇게 이해했어요');
    expect(text).not.toMatch(/_pdf\b|stay_manual_20|visa_manual_20/);
    expect(text).not.toMatch(/2026-05|2026\.6 매뉴얼|체류민원 안내매뉴얼 기준/);
    // only the guidance (and the collapsed evidence disclosure) render in the result area
    const children = await page.evaluate(() => [...document.getElementById('mainContent').children].filter((c) => { const cs = getComputedStyle(c); return cs.display !== 'none' && c.getBoundingClientRect().height > 0; }).map((c) => c.id));
    expect(children.filter((id) => !['statusGuidance', 'civicRawSources'].includes(id))).toEqual([]);
    await expect(page.locator('#civicRawSources')).not.toHaveAttribute('open', /.*/);
    await expect(page.locator('#rlist')).toBeHidden();
    await expect(page.locator('#unifiedSearchLayer')).toBeHidden();
    // the procedure picker is compact, and no other procedure is expanded
    await expect(sg.locator('.sg-options-grid')).toBeVisible();
    await expect(page.locator('.vc.open:visible')).toHaveCount(0);
  });

  test('D-2 → 체류기간 연장: definitive answer, one fee note, one preparation note', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2');
    await sg.locator('[data-sg-action="answer"][data-sg-value="extension"]').click();
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('.sg-lead')).toHaveText('D-2 기준으로 안내해요.');
    const fee = await sg.locator('.sg-fee').innerText();
    expect(fee.split('반환되지 않').length - 1).toBe(1);
    await expect(sg.locator('.sg-doc-prep-note')).toHaveCount(1);
    const docs = await sg.locator('.sg-docs').innerText();
    expect(docs).not.toContain('공식 안내에 제출 형태가 따로 적혀 있지 않아요');
    // groups use the requirement vocabulary
    await expect(sg.locator('.sg-doc-group-required h4')).toContainText('필수');
    // common rules: triggered ones visible, the rest behind one disclosure
    await expect(sg.locator('.sg-rules-more')).toHaveCount(1);
    await expect(sg.locator('.sg-rules-more')).not.toHaveAttribute('open', /.*/);
    // no unrelated procedure is expanded below the extension answer
    const text = await visibleText(page);
    expect(text).not.toContain('사증발급 안내');
  });
});

test.describe('D-2 연장 evidence relevance', () => {
  test('evidence collapsed by default; expanded, D-2 extension pages lead and transition pages stay out of the top', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    await expect(sg.locator('.sg-interp')).toHaveAttribute('data-sg-match', 'EXACT_CODE');
    await expect(sg.locator('.sg-interp-proc')).toHaveText('체류기간 연장');
    const ev = sg.locator('#sgEvidence');
    await expect(ev).not.toHaveAttribute('open', /.*/);
    await expect(ev.locator(':scope > summary')).toContainText('공식 근거');
    await ev.locator(':scope > summary').click();
    await expect(ev.locator('.sg-evidence-list li').first()).toBeVisible();
    await expect(ev.locator('.sg-ev-review')).toHaveCount(1);
    const raw = page.locator('#civicRawSources');
    await expect(ev.locator('#civicRawSources')).toHaveCount(1);
    await raw.locator(':scope > summary').click();
    const metas = raw.locator('.cs-result-meta');
    await expect(metas.first()).toContainText('43 쪽');
    const top = await metas.allInnerTexts();
    for (const m of top.slice(0, 3)) {
      expect(m).not.toMatch(/ 173 쪽| 210 쪽/);
      expect(m).toContain('외국인체류 안내매뉴얼');
    }
  });
});

test.describe('no legacy frame', () => {
  test('from submit to ready, no painted frame shows the legacy card, the legacy band or the backend layer (throttled)', async ({ page, context, browserName }) => {
    test.setTimeout(120_000);
    await boot(page);
    if (browserName === 'chromium') {
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
      await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 250, downloadThroughput: 2e6 / 8, uploadThroughput: 1e6 });
    }
    await page.evaluate(FRAME_LOG);
    await page.fill('#civicQuery', 'D-2 연장');
    await page.press('#civicQuery', 'Enter');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 60_000 });
    await page.waitForTimeout(500);
    const frames = await page.evaluate(() => { window.__stopFrames = true; return window.__frames; });
    const searched = frames.filter((f) => f.searched);
    expect(searched.length).toBeGreaterThan(0);
    const bad = searched.filter((f) => f.rlist || f.band || f.usLayer);
    expect(bad, `legacy UI painted in ${bad.length} frame(s)`).toEqual([]);
  });

  test('a result URL (?q=D-2) starts in the searched state: no landing frame, no legacy frame', async ({ page, context, browserName }) => {
    test.setTimeout(120_000);
    await page.addInitScript(FRAME_LOG);
    if (browserName === 'chromium') {
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 200, downloadThroughput: 4e6 / 8, uploadThroughput: 1e6 });
    }
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/index.html?q=D-2', { waitUntil: 'commit' });
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 90_000 });
    await page.waitForTimeout(500);
    const frames = await page.evaluate(() => { window.__stopFrames = true; return window.__frames; });
    expect(frames.length).toBeGreaterThan(0);
    expect(frames.filter((f) => f.landingVisible), 'landing painted on a result URL').toEqual([]);
    expect(frames.filter((f) => f.rlist || f.band || f.usLayer), 'legacy painted on a result URL').toEqual([]);
    await expect(page.locator('#q')).toHaveValue('D-2');
  });
});

test.describe('density and locales', () => {
  test('390×844: interpretation, answer and one action are in the first screen', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    for (const sel of ['.sg-interp', '#sgAnswerTitle', '.sg-answer-actions .sg-btn']) {
      const box = await sg.locator(sel).first().boundingBox();
      expect(box, sel).not.toBeNull();
      expect(box.y + Math.min(box.height, 44), `${sel} below the first screen`).toBeLessThanOrEqual(844);
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('Arabic: page RTL, guidance English LTR, no Korean prose in the answer, no overflow', async ({ page }) => {
    await boot(page, '/index.html?lang=ar');
    await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe('rtl');
    const sg = await search(page, 'D-2 연장');
    await expect(sg).toHaveAttribute('lang', 'en');
    await expect(sg).toHaveAttribute('dir', 'ltr');
    const answer = await sg.locator('.sg-answer').innerText();
    expect(answer).not.toMatch(/[가-힣]{2,}/);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('disclosures are keyboard operable and announce their state', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toHaveAttribute('data-sg-state', 'ready');
    const summary = sg.locator('#sgEvidence > summary');
    await summary.focus();
    await page.keyboard.press('Enter');
    await expect(sg.locator('#sgEvidence')).toHaveAttribute('open', /.*/);
    const edit = sg.locator('.sg-interp [data-sg-action="edit"]');
    await expect(edit).toHaveAttribute('aria-expanded', 'false');
    await edit.click();
    await expect(sg.locator('.sg-interp [data-sg-action="edit"]')).toHaveAttribute('aria-expanded', 'true');
  });
});
