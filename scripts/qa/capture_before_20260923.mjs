// BEFORE screenshots for the landing / form-helper / document-guidance sprint (2026-09-23).
// Chromium only (WebKit is not installable in the build sandbox); Safari UA on mobile.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'docs/design/screenshots/landing-form-helper-20260923/before';
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
  await bootHome(page);
  await page.screenshot({ path: `${OUT}/${vp.n}-home.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-home-full.png`, fullPage: true });
  // journey: open PRE, then click PRE again (does it collapse?)
  const pre = page.locator('.cs-routes button[data-journey-track="pre"]');
  await pre.click(); await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-pre-open-full.png`, fullPage: true });
  const preOpenVisible = await page.locator('#visaManualSection').isVisible();
  const preExpanded = await pre.getAttribute('aria-expanded');
  await pre.click(); await page.waitForTimeout(400);
  const afterSecondClickVisible = await page.locator('#visaManualSection').isVisible();
  const afterSecondExpanded = await pre.getAttribute('aria-expanded');
  await page.locator('.cs-routes button[data-journey-track="in"]').click(); await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${vp.n}-journey-post-open-full.png`, fullPage: true });
  const preAfterPost = await pre.getAttribute('aria-expanded');
  log.push({ vp: vp.n, preOpenVisible, preExpanded, afterSecondClickVisible, afterSecondExpanded, preAriaAfterPostClick: preAfterPost, errors });
  // directory (all tools) with Waymaker / New Home buried
  await page.locator('.cs-directory summary').click(); await page.waitForTimeout(200);
  await page.locator('.cs-directory').scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/${vp.n}-directory-open.png` });
  await ctx.close();
}
// Arabic RTL home
{
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, userAgent: UA });
  const page = await ctx.newPage(); await bootHome(page, 'ar'); await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/mobile-390-home-ar-full.png`, fullPage: true });
  await ctx.close();
}
// document guidance: F-6-1 extension (passport row = source unspecified) + address report (contract-like lease)
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage(); await bootHome(page);
  await page.fill('#civicQuery', 'F-6 연장'); await page.press('#civicQuery', 'Enter');
  await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
  for (const pick of ['spouse', 'normal']) { const b = page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${pick}"]`).first(); if (await b.count()) { await b.click(); await page.waitForTimeout(200); } }
  const summaries = page.locator('#statusGuidance .sg-doc-details summary');
  const n = await summaries.count();
  for (let i = 0; i < Math.min(n, 3); i++) await summaries.nth(i).click();
  const docs = page.locator('#statusGuidance .sg-docs'); await docs.scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}/${vp.n}-docs-f6-1-source-unspecified.png` });
  log.push({ vp: vp.n, q: 'F-6-1 docs', names: await page.locator('#statusGuidance .sg-doc-name').allInnerTexts(), meta: (await page.locator('#statusGuidance .sg-doc-meta').allInnerTexts()).slice(0, 3) });
  await ctx.close();
}
// form helper before
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await page.goto(BASE + '/form-helper.html', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-landing.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-landing-full.png`, fullPage: true });
  await page.locator('.fh-doc-card[data-doc="integrated"]').click(); await page.waitForTimeout(300);
  await page.locator('.fh-branch-btn[data-form="F01"]').click(); await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-step1.png` });
  await page.locator('.fh-type-card[data-type="sojourn_extension"]').click(); await page.waitForTimeout(200);
  await page.locator('#fhNextBtn').click(); await page.waitForTimeout(300);
  await page.fill('#surname', 'NGUYEN'); await page.fill('#givenName', 'THI HOANG ANH MARIA-CATHERINE');
  await page.fill('#koreanAddress', '서울특별시 강남구 테헤란로 152 강남파이낸스센터 27층 2701호 (역삼동)');
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-fields.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-fields-full.png`, fullPage: true });
  log.push({ vp: vp.n, formHelperErrors: errors });
  await ctx.close();
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
