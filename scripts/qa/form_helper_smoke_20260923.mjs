// Form Helper 2.0 smoke: boot, search, explain, edit, preview, review, export (download) on desktop + mobile.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'artifacts/form-helper-qa';
fs.mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE || 'http://127.0.0.1:4173';
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined, acceptDownloads: true });
  const page = await ctx.newPage();
  const errors = []; const requests = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('request', r => requests.push(r.url()));
  await page.goto(BASE + '/form-helper.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('body.fh-ready', { timeout: 20000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${vp.n}-01-home.png` });
  await page.fill('#fhSearch', '주소 변경');
  await page.waitForSelector('#fhResults .fh-result');
  const firstResult = await page.locator('#fhResults .fh-result').first().getAttribute('data-form');
  await page.screenshot({ path: `${OUT}/${vp.n}-02-search.png` });
  await page.click('#fhResults .fh-result[data-form="F08"]');
  await page.waitForSelector('#fhStart');
  await page.screenshot({ path: `${OUT}/${vp.n}-03-explain.png`, fullPage: true });
  await page.click('#fhStart');
  await page.waitForSelector('#fhFields');
  await page.fill('#f_name', 'nguyen van anh');
  await page.click('label[for="f_sex_1"]');
  await page.fill('#f_nationality', 'VIETNAM');
  await page.fill('#f_phone', '010-2345-6789');
  await page.fill('#f_arc_no', '9801231234567');
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/${vp.n}-04-edit-step1.png` });
  const arcVal = await page.inputValue('#f_arc_no');
  const nameVal = await page.inputValue('#f_name');
  await page.click(vp.mobile ? '#fhMobileBar .fh-btn-primary' : '#fhNext');
  await page.waitForSelector('#f_new_address');
  await page.fill('#f_new_address', '경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호 (이의동)');
  await page.click('label[for="f_res_type_1"]');
  await page.waitForTimeout(150);
  if (vp.mobile) { await page.click('#fhOpenSheet'); await page.waitForSelector('#fhSheet canvas'); await page.waitForTimeout(400); await page.screenshot({ path: `${OUT}/${vp.n}-05-sheet.png` }); await page.click('#fhSheetClose'); }
  else { await page.focus('#f_new_address'); await page.waitForTimeout(300); await page.screenshot({ path: `${OUT}/${vp.n}-05-edit-preview.png` }); }
  // back navigation keeps data
  await page.goBack(); await page.waitForSelector('#f_name');
  const keptName = await page.inputValue('#f_name');
  await page.goForward(); await page.waitForSelector('#f_new_address');
  const keptAddr = await page.inputValue('#f_new_address');
  await page.click(vp.mobile ? '#fhMobileBar .fh-btn-primary' : '#fhNext'); // sign step
  await page.waitForSelector('#f_reporter_name');
  await page.click(vp.mobile ? '#fhMobileBar .fh-btn-primary' : '#fhNext'); // review
  await page.waitForSelector('#fhToPreview');
  await page.screenshot({ path: `${OUT}/${vp.n}-06-review.png`, fullPage: true });
  await page.click('#fhToPreview');
  await page.waitForSelector('#fhExport');
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${vp.n}-07-preview.png`, fullPage: true });
  const [download] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#fhExport')]);
  const file = `${OUT}/${vp.n}-F08-export.pdf`; await download.saveAs(file);
  fs.writeFileSync(`${OUT}/${vp.n}-F08-ops.json`, JSON.stringify({ form: 'F08', edition: await page.evaluate(() => VisableFormHelper.engine.editionOf(VisableFormHelper.data.defs.forms[VisableFormHelper.state.formId], VisableFormHelper.state.values[VisableFormHelper.state.formId])), ops: await page.evaluate(() => VisableFormHelper.state.ops) }));
  const status = await page.locator('#fhExportStatus').textContent();
  const state = await page.evaluate(() => ({ ops: VisableFormHelper.state.ops.length, issues: VisableFormHelper.state.issues, font: VisableFormHelper.state.fontReady, last: VisableFormHelper.lastExport }));
  const external = requests.filter(u => !u.startsWith(BASE)).map(u => u.split('?')[0]);
  console.log(JSON.stringify({ vp: vp.n, firstResult, arcVal, nameVal, keptName, keptAddr, status, state, errors, external: [...new Set(external)], pdfBytes: fs.statSync(file).size }, null, 1));
  await ctx.close();
}
await browser.close();
