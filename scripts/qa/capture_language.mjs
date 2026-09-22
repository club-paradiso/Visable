// Language UX + RTL screenshots (Chromium). Usage: node scripts/qa/capture_language.mjs <outdir>
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
const log = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
  const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await boot(page);
  const btn = page.locator('#civicLanding .cs-lang').first();
  log.push({ vp: vp.n, homeLangButton: await btn.count(), label: await btn.innerText().catch(() => '') });
  await btn.click(); await page.waitForTimeout(250);
  const dlg = page.locator('#csLangDialog[open]');
  log.push({ vp: vp.n, dialogOpen: await dlg.count(), options: await page.locator('#csLangDialog .cs-lang-option').count(), focusInDialog: await page.evaluate(() => !!document.activeElement && !!document.activeElement.closest('#csLangDialog')) });
  await page.screenshot({ path: `${OUT}/${vp.n}-language-${vp.mobile ? 'sheet' : 'popover'}.png` });
  await page.fill('#csLangDialog [data-cs-lang-filter]', 'esp'); await page.waitForTimeout(100);
  log.push({ vp: vp.n, filtered: await page.locator('#csLangDialog .cs-lang-option').allInnerTexts() });
  await page.keyboard.press('Escape'); await page.waitForTimeout(150);
  log.push({ vp: vp.n, closedAfterEscape: (await dlg.count()) === 0, focusBack: await page.evaluate(() => document.activeElement && document.activeElement.classList.contains('cs-lang')) });
  // choose English via the control
  await btn.click(); await page.waitForTimeout(150);
  await page.locator('#csLangDialog .cs-lang-option[data-lang="en"]').click(); await page.waitForTimeout(400);
  log.push({ vp: vp.n, htmlLang: await page.evaluate(() => document.documentElement.lang), stored: await page.evaluate(() => localStorage.getItem('paradiso:language')), dialogClosed: (await dlg.count()) === 0, buttonLabel: await page.locator('#civicLanding .cs-lang').first().innerText() });
  await page.screenshot({ path: `${OUT}/${vp.n}-home-en.png`, fullPage: vp.mobile });
  // Arabic RTL
  await page.locator('#civicLanding .cs-lang').first().click(); await page.waitForTimeout(150);
  await page.locator('#csLangDialog .cs-lang-option[data-lang="ar"]').click(); await page.waitForTimeout(500);
  log.push({ vp: vp.n, dir: await page.evaluate(() => document.documentElement.dir), lang: await page.evaluate(() => document.documentElement.lang) });
  await page.screenshot({ path: `${OUT}/${vp.n}-home-ar.png`, fullPage: vp.mobile });
  // searched state in Arabic: language button present, guidance renders (ko/en copy only for the layer), no horizontal overflow
  await page.fill('#civicQuery', '외국인등록증 재발급'); await page.press('#civicQuery', 'Enter');
  await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 }); await page.waitForTimeout(400);
  log.push({ vp: vp.n, searchedLangBtn: await page.locator('#hero .cs-lang-searched').count(), overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), kind: await page.getAttribute('#statusGuidance', 'data-sg-kind') });
  await page.screenshot({ path: `${OUT}/${vp.n}-searched-ar.png` });
  // back to Korean through the searched header control
  await page.locator('#hero .cs-lang-searched').click(); await page.waitForTimeout(150);
  await page.locator('#csLangDialog .cs-lang-option[data-lang="ko"]').click(); await page.waitForTimeout(400);
  log.push({ vp: vp.n, backToKo: await page.evaluate(() => document.documentElement.lang + '/' + document.documentElement.dir), stillSearched: await page.evaluate(() => document.body.classList.contains('searched')), query: await page.inputValue('#q'), kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), errors });
  await page.screenshot({ path: `${OUT}/${vp.n}-searched-ko-langbtn.png` });
  await ctx.close();
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
