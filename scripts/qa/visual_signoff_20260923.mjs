// Release visual sign-off captures (2026-09-23): every mobile width × landing states and
// Form Helper screens, light + dark, seven languages. Each capture also records measured
// facts (horizontal overflow, whether the key controls are inside the viewport, the WCAG
// contrast of the primary action) so the visual review is cross-checked by numbers.
//   node scripts/qa/visual_signoff_20260923.mjs [outDir]   (static server on :4173)
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'artifacts/visual-signoff-20260923';
fs.mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE || 'http://127.0.0.1:4173';
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const VIEWPORTS = [[320, 568], [360, 800], [375, 812], [390, 844], [393, 852], [414, 896], [430, 932], [768, 1024], [1280, 900]];
const facts = [];
const settle = (page) => page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => null))));
async function measure(page, name, extra = {}) {
  const m = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const inView = (sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect(); return r.width > 0 && r.left >= -1 && r.right <= vw + 1; };
    const lum = (c) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
    const contrast = (sel) => { const e = [...document.querySelectorAll(sel)].find((x) => x.getClientRects().length); if (!e) return null; const cs = getComputedStyle(e); const p = (v) => v.match(/[\d.]+/g).slice(0, 3).map(Number); const a = lum(p(cs.color)), b = lum(p(cs.backgroundColor)); return Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 10) / 10; };
    // content inside a horizontal scroll / clip container (step rail, zoomable preview) may extend past the edge
    const inScroller = (e) => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) { const o = getComputedStyle(a).overflowX; if (o !== 'visible') return true; } return false; };
    // any visible element whose box sticks out of the viewport horizontally
    const escapes = [...document.querySelectorAll('body *')].filter((e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.position !== 'fixed' && (r.right > vw + 1 || r.left < -1) && !e.closest('[hidden],.cs-sr,.fh-skip,.sr-only,.visually-hidden') && !inScroller(e); }).slice(0, 3).map((e) => (e.id ? '#' + e.id : e.className && String(e.className).split(' ')[0] ? '.' + String(e.className).split(' ')[0] : e.tagName));
    return { overflow: document.documentElement.scrollWidth - vw, escapes, dir: document.documentElement.dir || 'ltr', theme: document.body.getAttribute('data-theme') || document.documentElement.getAttribute('data-theme'),
      primaryContrast: contrast('.fh-btn-primary'), fhNextInView: inView('#fhNext') ?? inView('#fhMobileBar .fh-btn-primary') };
  });
  facts.push({ name, ...m, ...extra });
}
async function shot(page, name, extra) { await settle(page); await page.screenshot({ path: `${OUT}/${name}.png` }); await measure(page, name, extra); }

for (const [w, h] of VIEWPORTS) {
  const mobile = w < 768;
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, userAgent: mobile ? UA : undefined, reducedMotion: 'reduce', locale: 'ko-KR' });
  const page = await ctx.newPage();
  await page.route('**/api/**', (r) => r.abort());
  await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#civicLanding [data-cs-journey="pre"]', { timeout: 20000 }); await page.waitForTimeout(400);
  await shot(page, `${w}-home`);
  const pre = page.locator('[data-cs-journey="pre"]'), post = page.locator('[data-cs-journey="post"]');
  await pre.scrollIntoViewIfNeeded(); await pre.click(); await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('.cs-journey').scrollIntoView({ block: 'start' }));
  await shot(page, `${w}-journey-pre-open`, { expanded: await pre.getAttribute('aria-expanded') });
  await post.click(); await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('.cs-journey').scrollIntoView({ block: 'start' }));
  await shot(page, `${w}-journey-post-open`, { expanded: await post.getAttribute('aria-expanded'), preExpanded: await pre.getAttribute('aria-expanded') });
  await post.click(); await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('.cs-journey').scrollIntoView({ block: 'start' }));
  await shot(page, `${w}-journey-closed-again`, { expanded: await post.getAttribute('aria-expanded'), panelHidden: await page.locator('#civicJourneyPanel').isHidden() });
  await page.evaluate(() => document.querySelector('.cs-tools-core').scrollIntoView({ block: 'center' }));
  await shot(page, `${w}-core-tools`, { waymaker: await page.locator('a.cs-tool[href="ai.html"]').isVisible(), newHome: await page.locator('a.cs-tool[href="new-home.html"]').isVisible() });
  // Form Helper
  await page.goto(BASE + '/form-helper.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('body.fh-ready', { timeout: 20000 });
  await shot(page, `${w}-fh-home`);
  await page.click('.fh-card[data-form="F01"]'); await page.waitForSelector('#fhStart');
  await shot(page, `${w}-fh-explain`);
  await page.click('#fhStart');
  await page.click('label[for="f_app_type_2"]').catch(() => {});
  await shot(page, `${w}-fh-edit`);
  if (mobile) { await page.click('#fhOpenSheet'); await page.waitForSelector('#fhSheet canvas'); await page.waitForTimeout(400); await shot(page, `${w}-fh-sheet`); await page.click('#fhSheetClose'); }
  await ctx.close();
}
// dark theme + review / preview / export dialog on 390 and 1280
for (const [w, h] of [[390, 844], [1280, 900]]) {
  const mobile = w < 768;
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, userAgent: mobile ? UA : undefined, reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  for (const theme of ['light', 'dark']) {
    await page.goto(BASE + '/form-helper.html?form=F08', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('body.fh-ready'); await page.waitForSelector('#fhStart');
    if (theme === 'dark' && (await page.getAttribute('body', 'data-theme')) !== 'dark') await page.click('#fhTheme');
    await shot(page, `${w}-${theme}-fh-explain`);
    await page.click('#fhStart');
    await page.fill('#f_name', 'nguyen van anh'); await page.click('label[for="f_sex_1"]'); await page.fill('#f_nationality', 'SOCIALIST REPUBLIC OF VIETNAM AND MORE'); await page.fill('#f_arc_no', '9801231234567');
    await page.waitForTimeout(300);
    await shot(page, `${w}-${theme}-fh-edit-overflow-warning`);
    const next = () => page.click(mobile ? '#fhMobileBar .fh-btn-primary' : '#fhNext');
    await next(); await page.waitForSelector('#f_new_address');
    await page.fill('#f_new_address', '경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호');
    await shot(page, `${w}-${theme}-fh-edit-step2`);
    await page.click('label[for="f_res_type_1"]');
    await next(); await next(); await page.waitForSelector('#fhToPreview');
    await shot(page, `${w}-${theme}-fh-review`);
    await page.click('#fhToPreview'); await page.waitForSelector('#fhFullPreview canvas'); await page.waitForTimeout(400);
    await shot(page, `${w}-${theme}-fh-preview`);
    await page.click('#fhExport'); await page.waitForSelector('#fhExportDialog', { state: 'visible' });
    await shot(page, `${w}-${theme}-fh-export-warning`);
    await page.click('#fhExportDialog button[value="fix"]');
  }
  await ctx.close();
}
// seven languages at 390 (landing + Form Helper editor) and Arabic sheet/dialog
for (const lang of ['ko', 'en', 'de', 'ru', 'vi', 'ja', 'ar']) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, userAgent: UA, reducedMotion: 'reduce' });
  const page = await ctx.newPage(); await page.route('**/api/**', (r) => r.abort());
  await page.goto(BASE + '/index.html?lang=' + lang, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#civicLanding [data-cs-journey="pre"]', { timeout: 20000 }); await page.waitForTimeout(500);
  await shot(page, `i18n-${lang}-home`);
  await page.click('[data-cs-journey="post"]'); await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('.cs-journey').scrollIntoView({ block: 'start' }));
  await shot(page, `i18n-${lang}-journey-post`);
  await page.goto(BASE + '/form-helper.html?form=F08&lang=' + lang, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#fhStart'); await page.click('#fhStart');
  await shot(page, `i18n-${lang}-fh-edit`);
  if (lang === 'ar') { await page.click('#fhOpenSheet'); await page.waitForSelector('#fhSheet canvas'); await page.waitForTimeout(400); await shot(page, 'i18n-ar-fh-sheet'); await page.click('#fhSheetClose');
    await page.click('#fhMobileBar .fh-btn-ghost, #fhMobileBar button:first-child').catch(() => {}); }
  await ctx.close();
}
fs.writeFileSync(`${OUT}/facts.json`, JSON.stringify(facts, null, 1));
const bad = facts.filter((f) => f.overflow > 1 || f.escapes.length || (f.primaryContrast !== null && f.primaryContrast < 4.5));
console.log(`[visual_signoff] ${facts.length} captures, ${bad.length} with overflow / escaping elements / low contrast`);
for (const b of bad) console.log('  ', JSON.stringify(b));
await browser.close();
