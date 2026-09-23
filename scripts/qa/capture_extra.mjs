// Extra AFTER screenshots: report dialog, office variation (Jeju), evidence opened,
// plain-language status prompt, address report, passport-change report (Chromium; Safari UA on mobile).
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
  await page.waitForTimeout(400);
}
const log = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }, { n: 'mobile-320', w: 320, h: 568, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage();
  const errors = []; page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await boot(page);
  // 1. plain-language status prompt
  await search(page, '체류기간 연장');
  await page.screenshot({ path: `${OUT}/${vp.n}-extension-status-prompt.png` });
  log.push({ vp: vp.n, q: '체류기간 연장', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind') });
  // 2. address report
  await search(page, '체류지 변경 신고');
  await page.screenshot({ path: `${OUT}/${vp.n}-address-report-full.png`, fullPage: true });
  log.push({ vp: vp.n, q: '체류지 변경 신고', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind') });
  // 3. passport-change report
  await search(page, '여권 재발급 후 신고');
  await page.screenshot({ path: `${OUT}/${vp.n}-passport-change-report.png` });
  log.push({ vp: vp.n, q: '여권 재발급 후 신고', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind') });
  // 4. evidence opened (card reissue)
  await search(page, '외국인등록증 재발급');
  await page.locator('#sgEvidence > summary').click(); await page.waitForTimeout(200);
  const ev = page.locator('#statusGuidance .sg-evidence'); await ev.scrollIntoViewIfNeeded();
  await ev.screenshot({ path: `${OUT}/${vp.n}-card-reissue-evidence-open.png` });
  // 5. report dialog
  await page.locator('#statusGuidance [data-sg-action="report"]').first().click();
  await page.waitForSelector('#sgReportDialog[open]', { timeout: 5000 }); await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/${vp.n}-report-dialog.png` });
  await page.keyboard.press('Escape'); await page.waitForTimeout(150);
  // 6. office variation (Jeju F-6-1)
  await search(page, 'F-6-1 연장');
  const normal = page.locator('#statusGuidance [data-sg-action="answer"][data-sg-value="normal"]').first(); if (await normal.count()) { await normal.click(); await page.waitForTimeout(250); }
  await page.selectOption('#sgOffice', 'jeju'); await page.waitForTimeout(300);
  const local = page.locator('#statusGuidance .sg-local'); await local.scrollIntoViewIfNeeded();
  await local.screenshot({ path: `${OUT}/${vp.n}-f6-1-jeju-local-practice.png` });
  log.push({ vp: vp.n, q: 'F-6-1 연장 + jeju', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), local: (await local.innerText()).slice(0, 160), errors });
  await ctx.close();
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
