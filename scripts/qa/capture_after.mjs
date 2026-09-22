// AFTER screenshots for the procedure-first / Quick Answer sprint (Chromium; Safari UA on mobile).
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'docs/design/screenshots/search-waymaker-20260922/after';
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
async function boot(page, lang) {
  await page.route('**/api/**', (r) => r.abort());
  await page.goto('http://127.0.0.1:4173/index.html' + (lang ? '?lang=' + lang : ''), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30000 });
}
async function search(page, q) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const sel = searched ? '#q' : '#civicQuery';
  await page.fill(sel, q); await page.press(sel, 'Enter');
  await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
  await page.waitForTimeout(500);
}
const log = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }, { n: 'mobile-320', w: 320, h: 568, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await boot(page);
  await page.screenshot({ path: `${OUT}/${vp.n}-home.png`, fullPage: vp.mobile });
  await search(page, '외국인등록증 재발급');
  log.push({ vp: vp.n, q: '외국인등록증 재발급', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), dead: (await page.locator('#statusGuidance').innerText()).includes('체류자격을 찾지 못했어요') });
  await page.screenshot({ path: `${OUT}/${vp.n}-card-reissue.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-card-reissue-full.png`, fullPage: true });
  await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
  log.push({ vp: vp.n, q: 'QA card reissue', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), quick: await page.getAttribute('#statusGuidance', 'data-sg-quick') });
  await page.screenshot({ path: `${OUT}/${vp.n}-quick-answer-card-reissue.png` });
  await search(page, 'F-6 연장');
  for (const pick of ['spouse', 'normal']) { const b = page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${pick}"]`).first(); if (await b.count()) { await b.click(); await page.waitForTimeout(200); } }
  await page.screenshot({ path: `${OUT}/${vp.n}-f6-1-resolved.png` });
  // expand the first document + fee details
  const firstDoc = page.locator('#statusGuidance .sg-doc-details summary').first(); if (await firstDoc.count()) await firstDoc.click();
  const fee = page.locator('#statusGuidance .sg-fee'); if (await fee.count()) { await fee.scrollIntoViewIfNeeded(); await page.screenshot({ path: `${OUT}/${vp.n}-f6-1-fee.png` }); }
  await page.screenshot({ path: `${OUT}/${vp.n}-f6-1-resolved-full.png`, fullPage: true });
  log.push({ vp: vp.n, q: 'F-6 연장 resolved', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), docs: await page.locator('#statusGuidance .sg-doc-name').allInnerTexts(), fee: await page.locator('#statusGuidance .sg-fee-amount').allInnerTexts(), errors });
  await ctx.close();
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
