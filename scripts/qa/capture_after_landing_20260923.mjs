// AFTER screenshots for the landing part of the sprint (Chromium; Safari UA on mobile).
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'docs/design/screenshots/landing-form-helper-20260923/after';
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const BASE = 'http://127.0.0.1:4173';
async function bootHome(page, lang) {
  await page.route('**/api/**', (r) => r.abort());
  await page.goto(BASE + '/index.html' + (lang ? '?lang=' + lang : ''), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30000 });
  await page.waitForTimeout(300);
}
const log = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }, { n: 'mobile-320', w: 320, h: 568, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', (e) => errors.push(String(e.message || e)));
  // first paint evidence: screenshot at commit (before scripts)
  await page.route('**/api/**', (r) => r.abort());
  await page.goto(BASE + '/index.html', { waitUntil: 'commit' });
  await page.screenshot({ path: `${OUT}/${vp.n}-first-paint.png` });
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30000 });
  await page.waitForTimeout(300);
  const hydrated = await page.getAttribute('#civicLanding', 'data-cs-hydrated');
  await page.screenshot({ path: `${OUT}/${vp.n}-home.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-home-full.png`, fullPage: true });
  const pre = page.locator('.cs-route[data-cs-journey="pre"]'); const post = page.locator('.cs-route[data-cs-journey="post"]');
  await pre.click(); await page.waitForTimeout(700);
  const s1 = { preExpanded: await pre.getAttribute('aria-expanded'), postExpanded: await post.getAttribute('aria-expanded'), panelVisible: await page.locator('#civicJourneyPanel').isVisible(), state: await page.evaluate(() => VisableCivicSearch.journey.state()) };
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-pre-open.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-pre-open-full.png`, fullPage: true });
  await pre.click(); await page.waitForTimeout(400);
  const s2 = { preExpanded: await pre.getAttribute('aria-expanded'), panelVisible: await page.locator('#civicJourneyPanel').isVisible(), state: await page.evaluate(() => VisableCivicSearch.journey.state()) };
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-closed-again.png` });
  await post.click(); await page.waitForTimeout(700);
  const s3 = { preExpanded: await pre.getAttribute('aria-expanded'), postExpanded: await post.getAttribute('aria-expanded'), state: await page.evaluate(() => VisableCivicSearch.journey.state()) };
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-post-open-full.png`, fullPage: true });
  await pre.click(); await page.waitForTimeout(500);
  const s4 = { preExpanded: await pre.getAttribute('aria-expanded'), postExpanded: await post.getAttribute('aria-expanded'), state: await page.evaluate(() => VisableCivicSearch.journey.state()) };
  // keyboard: focus post and press Space → switches; Enter again → closes
  await post.focus(); await page.keyboard.press('Space'); await page.waitForTimeout(300);
  const s5 = { state: await page.evaluate(() => VisableCivicSearch.journey.state()), postExpanded: await post.getAttribute('aria-expanded') };
  await page.keyboard.press('Enter'); await page.waitForTimeout(300);
  const s6 = { state: await page.evaluate(() => VisableCivicSearch.journey.state()), focusOnPost: await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-cs-journey')) };
  // tools
  const tools = page.locator('.cs-tools-core'); await tools.scrollIntoViewIfNeeded(); await page.screenshot({ path: `${OUT}/${vp.n}-core-tools.png` });
  log.push({ vp: vp.n, hydrated, s1, s2, s3, s4, s5, s6, errors });
  await ctx.close();
}
for (const lang of ['ar', 'de', 'ru', 'vi', 'ja', 'en']) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, userAgent: UA });
  const page = await ctx.newPage(); await bootHome(page, lang); await page.waitForTimeout(500);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  await page.locator('.cs-route[data-cs-journey="pre"]').click(); await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/mobile-390-home-${lang}-full.png`, fullPage: true });
  log.push({ lang, overflow, dir: await page.getAttribute('html', 'dir'), routeTitle: await page.locator('.cs-route-title').first().innerText() });
  await ctx.close();
  if (lang === 'de' || lang === 'ar') { const c2 = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const p2 = await c2.newPage(); await bootHome(p2, lang); await p2.waitForTimeout(400); await p2.screenshot({ path: `${OUT}/desktop-1280-home-${lang}.png`, fullPage: true }); await c2.close(); }
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
