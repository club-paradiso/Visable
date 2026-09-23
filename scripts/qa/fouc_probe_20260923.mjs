// FOUC probe: sample the landing during load under throttled network and record whether the legacy hero is visible.
import { chromium } from '@playwright/test';
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const results = [];
for (const profile of [{ name: 'fast', latency: 5, down: 50e6 }, { name: 'slow3g', latency: 400, down: 500e3 }, { name: 'mobile-390-slow', latency: 200, down: 1.6e6, viewport: { width: 390, height: 844 } }]) {
  const ctx = await browser.newContext({ viewport: profile.viewport || { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: profile.latency, downloadThroughput: profile.down / 8, uploadThroughput: 1e6 });
  const samples = [];
  const t0 = Date.now();
  const nav = page.goto('http://127.0.0.1:4173/index.html', { waitUntil: 'commit' });
  await nav;
  // sample until civic landing appears or 20s
  for (let i = 0; i < 400; i++) {
    let s = null;
    try {
      s = await page.evaluate(() => {
        const vis = (el) => { if (!el) return false; const cs = getComputedStyle(el); const r = el.getBoundingClientRect(); return cs.display !== 'none' && cs.visibility !== 'hidden' && r.height > 0; };
        return { t: performance.now(), ready: document.readyState, hero: vis(document.getElementById('hero')), civic: vis(document.getElementById('civicLanding')), bodyClass: document.body ? document.body.className : '', gw: vis(document.querySelector('.p-gateway')), wordmark: vis(document.querySelector('.brand-wordmark-img')) };
      });
    } catch (e) { s = { t: Date.now() - t0, err: String(e.message).slice(0, 60) }; }
    samples.push(s);
    if (s && s.civic) break;
    await page.waitForTimeout(50);
  }
  const heroFrames = samples.filter((s) => s && s.hero && !s.civic);
  const first = samples.find((s) => s && (s.hero || s.civic));
  results.push({ profile: profile.name, samples: samples.length, legacyHeroVisibleFrames: heroFrames.length, legacyVisibleMs: heroFrames.length ? Math.round(heroFrames[heroFrames.length - 1].t - heroFrames[0].t) : 0, firstPaintedState: first ? (first.hero ? 'LEGACY_HERO' : 'CIVIC') : 'none', civicAtMs: samples.find((s) => s && s.civic)?.t | 0 });
  await ctx.close();
}
console.log(JSON.stringify(results, null, 1));
await browser.close();
