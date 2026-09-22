import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
async function boot(page) {
  await page.route('**/api/**', (r) => r.abort());
  await page.goto('http://127.0.0.1:4173/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30000 });
}
async function search(page, q) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const sel = searched ? '#q' : '#civicQuery';
  await page.fill(sel, q); await page.press(sel, 'Enter');
  await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
  await page.waitForTimeout(600);
}
const shots = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900 }, { n: 'mobile-390', w: 390, h: 844 }, { n: 'mobile-320', w: 320, h: 568 }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await boot(page);
  await page.screenshot({ path: `${OUT}/${vp.n}-home.png`, fullPage: vp.n !== 'desktop-1280' });
  await search(page, '외국인등록증 재발급');
  const kind = await page.getAttribute('#statusGuidance', 'data-sg-kind');
  const text = await page.locator('#statusGuidance').innerText();
  shots.push({ vp: vp.n, q: '외국인등록증 재발급', kind, firstLine: text.split('\n').slice(0, 6) });
  await page.screenshot({ path: `${OUT}/${vp.n}-card-reissue.png`, fullPage: false });
  await page.screenshot({ path: `${OUT}/${vp.n}-card-reissue-full.png`, fullPage: true });
  await search(page, 'F-6 연장');
  await page.screenshot({ path: `${OUT}/${vp.n}-f6-extension.png`, fullPage: false });
  // answer F-6 subtype spouse → normal to reach a resolved checklist
  for (const pick of ['spouse', 'normal']) { const b = page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${pick}"]`).first(); if (await b.count()) { await b.click(); await page.waitForTimeout(200); } }
  await page.screenshot({ path: `${OUT}/${vp.n}-f6-1-resolved-full.png`, fullPage: true });
  shots.push({ vp: vp.n, q: 'F-6 연장 resolved', kind: await page.getAttribute('#statusGuidance', 'data-sg-kind'), docs: await page.locator('#statusGuidance .sg-doc-name').allInnerTexts() });
  if (vp.n === 'desktop-1280') { await page.click('#languageBtn').catch(() => {}); await page.waitForTimeout(200); await page.screenshot({ path: `${OUT}/${vp.n}-language-menu.png` }); }
  await ctx.close();
}
console.log(JSON.stringify(shots, null, 1));
await browser.close();
