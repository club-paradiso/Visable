// Real-browser tests for the civic landing boot, the purpose-browse panel and
// the Waymaker / New Home entries.
//
//   * first paint: the legacy hero is never displayed in any painted frame,
//     under a fast and a throttled connection, desktop and iPhone-sized;
//   * the static shell is reused by civic-search.js (no re-render, no shift);
//   * the home is search-first: the pre-entry / post-entry journey cards are
//     gone; the purpose pickers they opened (index.html startPreEntryTrack() /
//     startInKoreaTrack()) stay reachable from the directory in a browse panel:
//     CLOSED → PRE → POST (tabs) → CLOSED, keyboard, ARIA state, focus return;
//   * the directory entry and the legacy reveal action route through the same
//     state machine;
//   * Waymaker and New Home entries are visible on the home, navigate to the
//     right pages, and the browser Back restores the landing;
//   * a failed civic script load shows the reload row instead of a dead page.
import { test, expect } from '@playwright/test';

async function bootHome(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery') && !!window.VisableCivicSearch; } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}

// Records, from the very first frame the page can execute script in, whether
// the legacy hero was ever displayed. rAF fires once per painted frame.
const PAINT_LOG = () => {
  window.__paintLog = [];
  const vis = (el) => { if (!el) return false; const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden'; };
  const tick = () => {
    const body = document.body;
    window.__paintLog.push({
      t: Math.round(performance.now()),
      body: !!body,
      civicClass: !!(body && body.classList.contains('civic-refresh')),
      heroVisible: vis(document.getElementById('hero')),
      topCtrlsVisible: vis(document.getElementById('topCtrls')),
      civicPresent: !!document.getElementById('civicLanding'),
      civicVisible: vis(document.getElementById('civicLanding')),
    });
    if (window.__paintLog.length < 4000) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  try {
    window.__cls = 0;
    new PerformanceObserver((list) => { for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) { window.__cls = -1; }
};

for (const profile of [
  { name: 'fast', latency: 5, download: 50e6 },
  // A 1.4 MB document over a slow-ish mobile link: the shell must still be the first painted state.
  { name: 'slow (300 ms RTT, 2 Mbps)', latency: 300, download: 2e6 },
]) {
  test(`first paint never shows the legacy hero — ${profile.name}`, async ({ page, context, browserName }) => {
    test.setTimeout(180_000);
    await page.addInitScript(PAINT_LOG);
    if (browserName === 'chromium') {
      const cdp = await context.newCDPSession(page);
      await cdp.send('Network.enable');
      await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: profile.latency, downloadThroughput: profile.download / 8, uploadThroughput: 1e6 });
    }
    await page.route('**/api/**', (route) => route.abort());
    await page.goto('/index.html', { waitUntil: 'commit' });
    await page.waitForFunction(() => document.getElementById('civicLanding') && document.getElementById('civicLanding').getAttribute('data-cs-hydrated') === 'reused', null, { timeout: 90_000 });
    await page.waitForTimeout(300);
    const log = await page.evaluate(() => window.__paintLog);
    const framesWithBody = log.filter((f) => f.body);
    expect(framesWithBody.length, 'frames were sampled after <body> existed').toBeGreaterThan(0);
    const legacyFrames = framesWithBody.filter((f) => f.heroVisible || f.topCtrlsVisible);
    expect(legacyFrames, `legacy hero/top controls painted in ${legacyFrames.length} frame(s)`).toEqual([]);
    expect(framesWithBody.every((f) => f.civicClass), 'body carries civic-refresh from its first frame').toBe(true);
    // once the shell has been parsed it is displayed, and never hidden again while landing
    const afterShell = framesWithBody.filter((f) => f.civicPresent);
    expect(afterShell.length).toBeGreaterThan(0);
    expect(afterShell.every((f) => f.civicVisible), 'the civic shell stays visible once parsed').toBe(true);
    const cls = await page.evaluate(() => window.__cls);
    if (cls >= 0) expect(cls, `cumulative layout shift ${cls}`).toBeLessThan(0.25);
  });
}

test('the static shell is reused, not re-rendered, and the legacy hero stays hidden after hydration', async ({ page }) => {
  await bootHome(page);
  await expect(page.locator('#civicLanding')).toHaveAttribute('data-cs-hydrated', 'reused');
  await expect(page.locator('#hero')).toBeHidden();
  await expect(page.locator('#topCtrls')).toBeHidden();
  await expect(page.locator('#civicLanding')).toHaveCount(1);
  await expect(page.locator('.cs-brand img')).toHaveCount(1);
  await expect(page.locator('#civicQuery')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test('a failed civic script load leaves a usable page with a reload row, not a blank or legacy page', async ({ page }) => {
  await page.route('**/assets/js/civic-search.js', (route) => route.abort());
  await page.route('**/api/**', (route) => route.abort());
  await page.goto('/index.html');
  await expect(page.locator('body')).toHaveClass(/civic-boot-failed/);
  await expect(page.locator('.cs-boot-failed')).toBeVisible();
  await expect(page.locator('.cs-boot-failed .cs-boot-reload')).toBeVisible();
  await expect(page.locator('#hero')).toBeHidden();
  // the static shell still offers the search field and the tools, never the old journey cards
  await expect(page.locator('#civicLanding #civicQuery')).toBeVisible();
  await expect(page.locator('#civicLanding .cs-route')).toHaveCount(0);
  await expect(page.locator('#civicLanding .cs-tool')).toHaveCount(6);
});

test.describe('purpose browse panel (the former journey content, reached from the directory)', () => {
  const entry = (page) => page.locator('.cs-directory [data-action="reveal-home-section"][data-target="visaManualSection"]');
  const state = (page) => page.evaluate(() => window.VisableCivicSearch.journey.state());

  test('the home has no pre/post journey cards; the pickers open from the directory and switch with tabs', async ({ page }) => {
    await bootHome(page);
    await expect(page.locator('.cs-route, .cs-journey, #civicJourneyPanel')).toHaveCount(0);
    await expect(page.locator('#civicLanding')).not.toContainText('한국 입국 전');
    const panel = page.locator('#civicBrowsePanel');
    const pre = panel.locator('[data-cs-journey="pre"]');
    const post = panel.locator('[data-cs-journey="post"]');
    await expect(panel).toBeHidden();
    expect(await state(page)).toBe('CLOSED');

    await page.locator('.cs-directory summary').click();
    await expect(entry(page)).toHaveAttribute('aria-controls', 'civicBrowsePanel');
    await expect(entry(page)).toHaveAttribute('aria-expanded', 'false');
    await entry(page).click();
    expect(await state(page)).toBe('PRE_ENTRY_OPEN');
    await expect(entry(page)).toHaveAttribute('aria-expanded', 'true');
    await expect(panel).toBeVisible();
    await expect(pre).toHaveAttribute('aria-pressed', 'true');
    await expect(post).toHaveAttribute('aria-pressed', 'false');
    await expect(panel.locator('#visaManualSection')).toBeVisible();
    await expect(panel.locator('#visaManualDynamic .visa-purpose-card').first()).toBeVisible();
    await expect(panel.locator('.visa-track-selector')).toBeHidden();
    await expect(panel.locator('#visaManualDynamic')).toContainText(/유학·연수|Study/);
    // the panel sits after the directory and before the about disclosure, below search and tools
    const order = await page.evaluate(() => {
      const after = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      const p = document.getElementById('civicBrowsePanel');
      return { afterSearch: after(document.getElementById('civicSearchForm'), p), afterTools: after(document.querySelector('.cs-tools'), p), afterDirectory: after(document.querySelector('.cs-directory'), p), beforeAbout: after(p, document.getElementById('civic-about')) };
    });
    expect(order).toEqual({ afterSearch: true, afterTools: true, afterDirectory: true, beforeAbout: true });

    await post.click(); // switch
    expect(await state(page)).toBe('POST_ENTRY_OPEN');
    await expect(post).toHaveAttribute('aria-pressed', 'true');
    await expect(pre).toHaveAttribute('aria-pressed', 'false');
    await expect(panel.locator('#visaManualDynamic')).toContainText(/체류기간 연장|Extension of stay/);
    await post.click(); // the open tab keeps the panel open
    expect(await state(page)).toBe('POST_ENTRY_OPEN');

    // close returns focus to the control that opened the panel
    await panel.locator('.cs-journey-close').click();
    expect(await state(page)).toBe('CLOSED');
    await expect(panel).toBeHidden();
    await expect(entry(page)).toBeFocused();
    await expect(entry(page)).toHaveAttribute('aria-expanded', 'false');
  });

  test('keyboard: Enter opens from the directory, Escape inside the panel closes it and returns focus', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-directory summary').click();
    await entry(page).focus();
    await page.keyboard.press('Enter');
    expect(await state(page)).toBe('PRE_ENTRY_OPEN');
    await page.locator('#civicBrowsePanel [data-cs-journey="post"]').focus();
    await page.keyboard.press('Space');
    expect(await state(page)).toBe('POST_ENTRY_OPEN');
    await page.locator('#civicBrowsePanel .cs-journey-close').focus();
    await page.keyboard.press('Escape');
    expect(await state(page)).toBe('CLOSED');
    await expect(entry(page)).toBeFocused();
  });

  test('a search leaves the landing; coming back resets the panel to CLOSED', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-directory summary').click();
    await entry(page).click();
    expect(await state(page)).toBe('PRE_ENTRY_OPEN');
    await expect(page.locator('#visaManualSection')).toBeVisible();
    await page.fill('#civicQuery', 'F-6 연장');
    await page.press('#civicQuery', 'Enter');
    await expect(page.locator('body')).toHaveClass(/searched/);
    await expect(page.locator('#civicLanding')).toBeHidden();
    await page.locator('#hero .logo-area').click();
    await expect(page.locator('body')).not.toHaveClass(/searched/);
    expect(await state(page)).toBe('CLOSED');
    await expect(page.locator('#civicBrowsePanel')).toBeHidden();
  });

  test('a language change keeps an open panel open and re-renders its copy', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-directory summary').click();
    await entry(page).click();
    await page.locator('#civicBrowsePanel [data-cs-journey="post"]').click();
    await page.locator('[data-cs-lang-open]:visible').first().click();
    await page.locator('#csLangDialog .cs-lang-option[data-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('#civicBrowsePanel [data-cs-journey="post"]')).toHaveText('After entry · Managing your stay');
    await expect(page.locator('#civicBrowsePanel [data-cs-journey="post"]')).toHaveAttribute('aria-pressed', 'true');
    expect(await state(page)).toBe('POST_ENTRY_OPEN');
    await expect(page.locator('#civicBrowsePanel')).toBeVisible();
    await expect(page.locator('#visaManualDynamic')).toContainText('Extension of stay');
  });
});

test.describe('Waymaker and New Home entries', () => {
  test('both are visible core tools on the home and are not only inside the collapsed directory', async ({ page }) => {
    await bootHome(page);
    const waymaker = page.locator('.cs-tools-core .cs-tool[data-cs-tool="waymaker"]');
    const newHome = page.locator('.cs-tools-core .cs-tool[data-cs-tool="newhome"]');
    const forms = page.locator('.cs-tools-core .cs-tool[data-cs-tool="forms"]');
    for (const el of [waymaker, newHome, forms]) {
      await el.scrollIntoViewIfNeeded();
      await expect(el).toBeVisible();
      const box = await el.boundingBox();
      expect(box.height).toBeGreaterThanOrEqual(44);
    }
    await expect(waymaker).toContainText('Waymaker');
    await expect(waymaker.locator('small')).not.toHaveText('');
    await expect(newHome).toContainText('New Home');
    await expect(newHome.locator('small')).toContainText(/국적|Nationality/);
    await expect(waymaker).toHaveAttribute('href', 'ai.html');
    await expect(newHome).toHaveAttribute('href', 'new-home.html');
    // search stays the primary control: it is in the first screen, above every tool, and its headline is larger
    const sizes = await page.evaluate(() => {
      const bar = document.querySelector('.cs-searchbar').getBoundingClientRect();
      const tools = [...document.querySelectorAll('.cs-tools .cs-tool')].map((t) => t.getBoundingClientRect());
      return { search: parseFloat(getComputedStyle(document.querySelector('.cs-hero h1')).fontSize), tool: parseFloat(getComputedStyle(document.querySelector('.cs-tools-core .cs-tool strong')).fontSize), barAbove: tools.every((t) => bar.bottom <= t.top), barInFirstScreen: bar.bottom <= innerHeight };
    });
    expect(sizes.search).toBeGreaterThan(sizes.tool);
    expect(sizes.barAbove).toBe(true);
    expect(sizes.barInFirstScreen).toBe(true);
  });

  test('Waymaker opens the Waymaker workspace and Back restores the landing', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-tools-core .cs-tool[data-cs-tool="waymaker"]').click();
    await expect(page).toHaveURL(/ai\.html$/);
    await expect(page.locator('body')).toHaveClass(/product-waymaker/);
    await expect(page.locator('.vf-product-wordmark.product-wordmark-light')).toBeVisible();
    await expect(page.locator('.wm-brand-wordmark .product-wordmark-light')).toBeVisible();
    await expect(page.locator('.vf-product-wordmark.product-wordmark-light')).toHaveAttribute('src', /waymaker-wordmark\.svg$/);
    expect(await page.locator('.wm-brand-wordmark .product-wordmark-light').evaluate((img) => img.complete && img.naturalWidth > 0)).toBe(true);
    await page.goBack();
    await expect(page).toHaveURL(/index\.html/);
    await expect(page.locator('#civicQuery')).toBeVisible();
    await expect(page.locator('#hero')).toBeHidden();
  });

  test('New Home opens the nationality hub and Back restores the landing', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-tools-core .cs-tool[data-cs-tool="newhome"]').click();
    await expect(page).toHaveURL(/new-home\.html$/);
    await expect(page.locator('body')).toHaveClass(/product-new-home/);
    await expect(page.locator('.vf-product-wordmark.product-wordmark-light')).toBeVisible();
    await expect(page.locator('.nh-brand-wordmark .product-wordmark-light')).toBeVisible();
    await expect(page.locator('.vf-product-wordmark.product-wordmark-light')).toHaveAttribute('src', /new-home-wordmark\.svg$/);
    expect(await page.locator('.nh-brand-wordmark .product-wordmark-light').evaluate((img) => img.complete && img.naturalWidth > 0)).toBe(true);
    await page.goBack();
    await expect(page).toHaveURL(/index\.html/);
    await expect(page.locator('#civicQuery')).toBeVisible();
  });
});

test.describe('localized layout', () => {
  test('the mounted purpose pickers are fully translated (no Korean left in de / ja / ar)', async ({ page }) => {
    for (const lang of ['de', 'ja', 'ar']) {
      await bootHome(page, '/index.html?lang=' + lang);
      await page.locator('.cs-directory summary').click();
      await page.locator('.cs-directory [data-target="visaManualSection"]').click();
      for (const track of ['pre', 'post']) {
        await page.click(`#civicBrowsePanel [data-cs-journey="${track}"]`);
        await expect(page.locator('#civicBrowsePanel')).toBeVisible();
        const korean = await page.evaluate(() => [...document.querySelectorAll('.cs-journey-slot *')]
          .filter((e) => e.children.length === 0 && e.offsetParent && /[가-힣]/.test(e.textContent)).map((e) => e.textContent.trim()));
        expect(korean, `${lang} ${track}`).toEqual([]);
      }
    }
  });

  // keep-all keeps Korean words whole but removes every break point from Japanese / Chinese
  for (const lang of ['ja', 'zh-CN']) {
    test(`the ${lang} headline, search copy, examples and tool text wrap inside the viewport`, async ({ page }) => {
      await bootHome(page, '/index.html?lang=' + lang);
      await expect(page.locator('html')).toHaveAttribute('lang', lang);
      const clipped = await page.evaluate(() => {
        const vw = document.documentElement.clientWidth;
        return [...document.querySelectorAll('.cs-hero h1, .cs-hero > p, .cs-examples button, .cs-example-link, .cs-tool strong, .cs-tool small')]
          .filter((e) => { const r = e.getBoundingClientRect(); return r.width && (e.scrollWidth - e.clientWidth > 1 || r.right > vw + 1); })
          .map((e) => e.textContent.trim().slice(0, 20));
      });
      expect(clipped).toEqual([]);
    });
  }
});
