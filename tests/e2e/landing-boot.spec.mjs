// Real-browser tests for the civic landing boot, the pre-entry / post-entry
// journey state machine and the Waymaker / New Home entries.
//
//   * first paint: the legacy hero is never displayed in any painted frame,
//     under a fast and a throttled connection, desktop and iPhone-sized;
//   * the static shell is reused by civic-search.js (no re-render, no shift);
//   * journey: CLOSED → PRE → CLOSED (second click) → POST → PRE (switch),
//     keyboard Enter/Space, ARIA state, focus after collapse;
//   * the directory entry that targets the journey section routes through the
//     same state machine;
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
  await expect(page.locator('#civicLanding .cs-route')).toHaveCount(2);
});

test.describe('journey state machine', () => {
  test('second click collapses; PRE↔POST switching is deterministic; ARIA matches; focus stays sensible', async ({ page }) => {
    await bootHome(page);
    const pre = page.locator('.cs-route[data-cs-journey="pre"]');
    const post = page.locator('.cs-route[data-cs-journey="post"]');
    const panel = page.locator('#civicJourneyPanel');
    const state = () => page.evaluate(() => window.VisableCivicSearch.journey.state());
    await expect(pre).toHaveAttribute('aria-expanded', 'false');
    await expect(pre).toHaveAttribute('aria-controls', 'civicJourneyPanel');
    await expect(panel).toBeHidden();
    expect(await state()).toBe('CLOSED');

    await pre.click();
    expect(await state()).toBe('PRE_ENTRY_OPEN');
    await expect(pre).toHaveAttribute('aria-expanded', 'true');
    await expect(post).toHaveAttribute('aria-expanded', 'false');
    await expect(panel).toBeVisible();
    await expect(panel.locator('#visaManualSection')).toBeVisible();
    await expect(panel.locator('#visaManualDynamic .visa-purpose-card').first()).toBeVisible();
    await expect(panel.locator('.visa-track-selector')).toBeHidden();
    // the panel sits directly under the triggers, not below the footer
    const order = await page.evaluate(() => {
      const routes = document.querySelector('.cs-routes'), panel = document.getElementById('civicJourneyPanel'), footer = document.querySelector('.cs-footer');
      return { panelAfterRoutes: !!(routes.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING), panelBeforeFooter: !!(panel.compareDocumentPosition(footer) & Node.DOCUMENT_POSITION_FOLLOWING) };
    });
    expect(order).toEqual({ panelAfterRoutes: true, panelBeforeFooter: true });

    await pre.click(); // second click collapses
    expect(await state()).toBe('CLOSED');
    await expect(pre).toHaveAttribute('aria-expanded', 'false');
    await expect(panel).toBeHidden();
    await expect(pre).toBeFocused();

    await post.click();
    expect(await state()).toBe('POST_ENTRY_OPEN');
    await expect(post).toHaveAttribute('aria-expanded', 'true');
    await expect(pre).toHaveAttribute('aria-expanded', 'false');
    await expect(panel.locator('#visaManualDynamic')).toContainText(/체류기간 연장|Extension of stay/);

    await pre.click(); // switch
    expect(await state()).toBe('PRE_ENTRY_OPEN');
    await expect(pre).toHaveAttribute('aria-expanded', 'true');
    await expect(post).toHaveAttribute('aria-expanded', 'false');
    await expect(panel.locator('#visaManualDynamic')).toContainText(/유학·연수|Study/);

    // close button returns focus to the open trigger
    await panel.locator('.cs-journey-close').click();
    expect(await state()).toBe('CLOSED');
    await expect(pre).toBeFocused();
    await expect(panel).toBeHidden();
  });

  test('keyboard Enter and Space behave like click', async ({ page }) => {
    await bootHome(page);
    const pre = page.locator('.cs-route[data-cs-journey="pre"]');
    const post = page.locator('.cs-route[data-cs-journey="post"]');
    const state = () => page.evaluate(() => window.VisableCivicSearch.journey.state());
    await pre.focus();
    await page.keyboard.press('Enter');
    expect(await state()).toBe('PRE_ENTRY_OPEN');
    await page.keyboard.press('Enter');
    expect(await state()).toBe('CLOSED');
    await post.focus();
    await page.keyboard.press('Space');
    expect(await state()).toBe('POST_ENTRY_OPEN');
    await expect(post).toHaveAttribute('aria-expanded', 'true');
    // Escape inside the panel closes it and returns focus to the trigger
    await page.locator('#civicJourneyPanel .visa-purpose-card').first().focus().catch(() => {});
    await page.locator('#civicJourneyPanel .cs-journey-close').focus();
    await page.keyboard.press('Escape');
    expect(await state()).toBe('CLOSED');
    await expect(post).toBeFocused();
  });

  test('the directory entry and the legacy reveal action route through the same state machine', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-directory summary').click();
    const entry = page.locator('.cs-directory [data-action="reveal-home-section"][data-target="visaManualSection"]');
    await entry.click();
    expect(await page.evaluate(() => window.VisableCivicSearch.journey.state())).toBe('PRE_ENTRY_OPEN');
    await expect(page.locator('#visaManualSection')).toBeVisible();
    await expect(page.locator('.cs-route[data-cs-journey="pre"]')).toHaveAttribute('aria-expanded', 'true');
    // a search leaves the landing; coming back resets the journey to CLOSED
    await page.fill('#civicQuery', 'F-6 연장');
    await page.press('#civicQuery', 'Enter');
    await expect(page.locator('body')).toHaveClass(/searched/);
    await expect(page.locator('#civicLanding')).toBeHidden();
    await page.locator('#hero .logo-area').click();
    await expect(page.locator('body')).not.toHaveClass(/searched/);
    expect(await page.evaluate(() => window.VisableCivicSearch.journey.state())).toBe('CLOSED');
    await expect(page.locator('.cs-route[data-cs-journey="pre"]')).toHaveAttribute('aria-expanded', 'false');
  });

  test('a language change keeps an open journey open and re-renders its copy', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-route[data-cs-journey="post"]').click();
    await page.locator('[data-cs-lang-open]:visible').first().click();
    await page.locator('#csLangDialog .cs-lang-option[data-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('.cs-route[data-cs-journey="post"] .cs-route-title')).toHaveText('Managing your stay');
    expect(await page.evaluate(() => window.VisableCivicSearch.journey.state())).toBe('POST_ENTRY_OPEN');
    await expect(page.locator('#civicJourneyPanel')).toBeVisible();
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
    // search stays the primary control: it is above the tools and larger than any tool title
    const sizes = await page.evaluate(() => ({ search: parseFloat(getComputedStyle(document.querySelector('.cs-hero h1')).fontSize), tool: parseFloat(getComputedStyle(document.querySelector('.cs-tools-core .cs-tool strong')).fontSize) }));
    expect(sizes.search).toBeGreaterThan(sizes.tool);
  });

  test('Waymaker opens the Waymaker workspace and Back restores the landing', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-tools-core .cs-tool[data-cs-tool="waymaker"]').click();
    await expect(page).toHaveURL(/ai\.html$/);
    await expect(page.locator('body')).toHaveClass(/product-waymaker/);
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
    await page.goBack();
    await expect(page).toHaveURL(/index\.html/);
    await expect(page.locator('#civicQuery')).toBeVisible();
  });
});
