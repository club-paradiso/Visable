// AFTER screenshots for Form Helper 2.0 (landing, search + hand-off, explain, editing + live preview, review with errors, preview/export, Arabic RTL, phone flow + preview sheet).
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'docs/design/screenshots/landing-form-helper-20260923/after';
fs.mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE || 'http://127.0.0.1:4173';
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
async function ctxFor(vp, lang) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined, locale: lang === 'ar' ? 'ar' : 'ko-KR' });
  const page = await ctx.newPage();
  await page.goto(BASE + '/form-helper.html' + (lang ? '?lang=' + lang : ''), { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('body.fh-ready', { timeout: 20000 }); await page.waitForTimeout(500);
  return { ctx, page };
}
const next = (page, mobile) => page.click(mobile ? '#fhMobileBar .fh-btn-primary' : '#fhNext');
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }, { n: 'mobile-320', w: 320, h: 568, mobile: true }]) {
  const { ctx, page } = await ctxFor(vp);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-landing.png` });
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-landing-full.png`, fullPage: true });
  await page.fill('#fhSearch', '난민'); await page.waitForSelector('#fhResults .fh-result-static'); await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-search-excluded-handoff.png` });
  await page.fill('#fhSearch', '주소 변경'); await page.waitForSelector('#fhResults .fh-result[data-form="F08"]');
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-search.png` });
  await page.click('#fhResults .fh-result[data-form="F08"]'); await page.waitForSelector('#fhStart');
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-explain.png`, fullPage: true });
  await page.click('#fhStart'); await page.waitForSelector('#f_name');
  await page.fill('#f_name', 'nguyen van anh'); await page.click('label[for="f_sex_1"]'); await page.fill('#f_nationality', 'VIETNAM'); await page.fill('#f_arc_no', '9801231234567');
  await page.focus('#f_arc_no'); await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-editing.png` });
  if (vp.mobile) { await page.click('#fhOpenSheet'); await page.waitForSelector('#fhSheet canvas'); await page.waitForTimeout(500); await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-preview-sheet.png` }); await page.click('#fhSheetClose'); }
  await next(page, vp.mobile); await page.waitForSelector('#f_new_address');
  await page.fill('#f_new_address', '경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호 (이의동) 이 주소는 일부러 아주 길게 적어서 세 줄을 넘기는 경우를 보여주는 예시입니다 계속 길게 길게 길게 더 길게 더 길게 끝');
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-error-overflow.png` });
  await page.fill('#f_new_address', '경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호');
  await page.click('label[for="f_res_type_1"]');
  await next(page, vp.mobile); await page.waitForSelector('#f_reporter_name');
  await next(page, vp.mobile); await page.waitForSelector('#fhToPreview');
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-review.png`, fullPage: true });
  await page.click('#fhToPreview'); await page.waitForSelector('#fhExport'); await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-preview-export.png`, fullPage: true });
  await ctx.close();
}
// review screen with missing required fields (error state) — desktop
{
  const { ctx, page } = await ctxFor({ w: 1280, h: 900, mobile: false });
  await page.goto(BASE + '/form-helper.html?form=F01&type=status_change'); await page.waitForSelector('body.fh-ready');
  await page.click('#fhStart'); await page.evaluate(() => VisableFormHelper.go('review'));
  await page.waitForSelector('#fhReview .fh-issues-error'); await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/desktop-1280-form-helper-error-missing.png`, fullPage: true });
  await ctx.close();
}
// Arabic RTL — desktop + phone
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  const { ctx, page } = await ctxFor(vp, 'ar');
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-ar-rtl-landing.png` });
  await page.click('.fh-card[data-form="F08"]'); await page.waitForSelector('#fhStart'); await page.click('#fhStart'); await page.waitForSelector('#f_name'); await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/${vp.n}-form-helper-ar-rtl-editing.png` });
  await ctx.close();
}
// English — desktop landing + explain
{
  const { ctx, page } = await ctxFor({ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, 'en');
  await page.screenshot({ path: `${OUT}/desktop-1280-form-helper-en-landing.png` });
  await page.click('.fh-card[data-form="F10"]'); await page.waitForSelector('#fhStart'); await page.screenshot({ path: `${OUT}/desktop-1280-form-helper-en-explain-f10.png`, fullPage: true });
  await ctx.close();
}
await browser.close();
console.log('form helper screenshots written to', OUT);
