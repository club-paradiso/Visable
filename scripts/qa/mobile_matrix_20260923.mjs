// Mobile matrix (320/360/375/390/393/414/430/768) for the civic landing and the Form Helper:
// no horizontal overflow, core controls visible with ≥44px targets, journey toggle works,
// Form Helper edit screen + preview sheet usable; long-text locales (ja/vi/ru/de/ar) on the
// Form Helper chrome at 320px. Writes a JSON + Markdown report and a few screenshots.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'artifacts/mobile-matrix-20260923';
fs.mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE || 'http://127.0.0.1:4173';
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const WIDTHS = [320, 360, 375, 390, 393, 414, 430, 768];
const rows = [];
const overflowOf = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
const targetOk = async (loc) => { const b = await loc.boundingBox(); return !!b && b.height >= 44 && b.width >= 44; };
for (const w of WIDTHS) {
  const mobile = w < 768;
  const ctx = await browser.newContext({ viewport: { width: w, height: 844 }, isMobile: mobile, hasTouch: mobile, userAgent: mobile ? UA : undefined });
  const page = await ctx.newPage();
  await page.route('**/api/**', (r) => r.abort());
  // landing
  await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#civicLanding [data-cs-journey="pre"]', { timeout: 20000 }); await page.waitForTimeout(500);
  const r1 = { width: w, page: 'index', overflow: await overflowOf(page) };
  r1.searchVisible = await page.locator('#civicQuery').isVisible();
  r1.journeyTarget = await targetOk(page.locator('[data-cs-journey="pre"]'));
  await page.click('[data-cs-journey="pre"]'); await page.waitForTimeout(300);
  r1.journeyOpen = await page.getAttribute('[data-cs-journey="pre"]', 'aria-expanded');
  r1.overflowJourneyOpen = await overflowOf(page);
  await page.click('[data-cs-journey="pre"]'); await page.waitForTimeout(200);
  r1.journeyClosed = await page.getAttribute('[data-cs-journey="pre"]', 'aria-expanded');
  r1.waymaker = await targetOk(page.locator('a.cs-tool[href="ai.html"]'));
  r1.newHome = await targetOk(page.locator('a.cs-tool[href="new-home.html"]'));
  if ([320, 375, 414, 768].includes(w)) await page.screenshot({ path: `${OUT}/index-${w}.png` });
  rows.push(r1);
  // form helper
  await page.goto(BASE + '/form-helper.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('body.fh-ready', { timeout: 20000 }); await page.waitForTimeout(300);
  const r2 = { width: w, page: 'form-helper', overflow: await overflowOf(page) };
  r2.cardTarget = await targetOk(page.locator('.fh-card[data-form="F08"]').first());
  await page.click('.fh-card[data-form="F08"]'); await page.waitForSelector('#fhStart'); await page.click('#fhStart'); await page.waitForSelector('#f_name');
  await page.fill('#f_name', 'NGUYEN VAN ANH'); await page.waitForTimeout(200);
  r2.overflowEdit = await overflowOf(page);
  r2.inputTarget = await targetOk(page.locator('#f_name'));
  const barVisible = await page.locator('#fhMobileBar').isVisible();
  r2.mobileBar = barVisible;
  if (barVisible) {
    r2.nextTarget = await targetOk(page.locator('#fhMobileBar .fh-btn-primary'));
    await page.click('#fhOpenSheet'); await page.waitForSelector('#fhSheet canvas'); await page.waitForTimeout(300);
    r2.sheetCanvasWidth = await page.locator('#fhSheet canvas').evaluate((c) => c.getBoundingClientRect().width);
    r2.overflowSheet = await overflowOf(page);
    if ([320, 375, 414].includes(w)) await page.screenshot({ path: `${OUT}/form-helper-sheet-${w}.png` });
    await page.click('#fhSheetClose');
  } else {
    r2.nextTarget = await targetOk(page.locator('#fhNext'));
    r2.asideVisible = await page.locator('.fh-aside').isVisible();
  }
  if ([320, 375, 414, 768].includes(w)) await page.screenshot({ path: `${OUT}/form-helper-edit-${w}.png` });
  rows.push(r2);
  await ctx.close();
}
// long-text locales at 320px on the Form Helper chrome
const langRows = [];
for (const lang of ['ja', 'vi', 'ru', 'de', 'ar', 'en']) {
  const ctx = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true, userAgent: UA });
  const page = await ctx.newPage();
  await page.goto(BASE + '/form-helper.html?lang=' + lang, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('body.fh-ready', { timeout: 20000 }); await page.waitForTimeout(300);
  const r = { lang, overflowHome: await overflowOf(page), dir: await page.getAttribute('html', 'dir') };
  await page.click('.fh-card[data-form="F08"]'); await page.waitForSelector('#fhStart'); await page.click('#fhStart'); await page.waitForSelector('#f_name'); await page.waitForTimeout(200);
  r.overflowEdit = await overflowOf(page);
  r.barButtonsClipped = await page.evaluate(() => [...document.querySelectorAll('#fhMobileBar .fh-btn')].some((b) => b.scrollWidth > b.clientWidth + 1));
  r.stepTitle = await page.locator('#fhStepTitle').textContent();
  await page.screenshot({ path: `${OUT}/form-helper-320-${lang}.png` });
  langRows.push(r);
  await ctx.close();
}
await browser.close();
const bad = rows.filter((r) => r.overflow > 1 || r.overflowEdit > 1 || r.overflowJourneyOpen > 1 || r.overflowSheet > 1 || r.journeyTarget === false || r.cardTarget === false || r.nextTarget === false || r.inputTarget === false || r.journeyOpen !== 'true' && r.page === 'index' || r.journeyClosed !== 'false' && r.page === 'index');
const badLang = langRows.filter((r) => r.overflowHome > 1 || r.overflowEdit > 1 || r.barButtonsClipped);
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ rows, langRows, bad, badLang }, null, 1));
let md = '# Mobile matrix — 2026-09-23\n\n| width | page | overflow | overflow (edit/journey) | overflow (sheet) | targets ≥44px | journey open/close | notes |\n| --- | --- | ---: | ---: | ---: | --- | --- | --- |\n';
for (const r of rows) md += `| ${r.width} | ${r.page} | ${r.overflow} | ${r.overflowEdit ?? r.overflowJourneyOpen ?? ''} | ${r.overflowSheet ?? '—'} | ${[r.journeyTarget, r.waymaker, r.newHome, r.cardTarget, r.inputTarget, r.nextTarget].filter((x) => x !== undefined).every(Boolean) ? 'ok' : 'FAIL'} | ${r.page === 'index' ? r.journeyOpen + '/' + r.journeyClosed : (r.mobileBar ? 'bottom bar + sheet ' + Math.round(r.sheetCanvasWidth || 0) + 'px' : 'side preview')} | |\n`;
md += '\n## Form Helper chrome at 320px, long-text locales\n\n| lang | dir | overflow home | overflow edit | bar buttons clipped | step title |\n| --- | --- | ---: | ---: | --- | --- |\n';
for (const r of langRows) md += `| ${r.lang} | ${r.dir} | ${r.overflowHome} | ${r.overflowEdit} | ${r.barButtonsClipped ? 'YES' : 'no'} | ${r.stepTitle} |\n`;
md += `\nResult: ${bad.length + badLang.length ? 'FAIL (' + (bad.length + badLang.length) + ' rows)' : 'PASS'} — Chromium only; WebKit runs in CI (mobile-webkit-qa).\n`;
fs.writeFileSync(`${OUT}/report.md`, md);
console.log(md);
