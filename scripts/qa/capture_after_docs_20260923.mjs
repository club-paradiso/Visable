// AFTER screenshots for the document physical-form guidance (explicit / source-silent / contract / passport).
import { chromium } from '@playwright/test';
import fs from 'node:fs';
const OUT = process.argv[2] || 'docs/design/screenshots/landing-form-helper-20260923/after';
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium', headless: true, args: ['--no-sandbox'] });
const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const BASE = 'http://127.0.0.1:4173';
async function boot(page) {
  await page.route('**/api/**', (r) => r.abort());
  await page.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30000 });
}
async function search(page, q, picks) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const sel = searched ? '#q' : '#civicQuery';
  await page.fill(sel, q); await page.press(sel, 'Enter');
  await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
  for (const pick of picks || []) { const b = page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${pick}"]`).first(); if (await b.count()) { await b.click(); await page.waitForTimeout(250); } }
  await page.waitForTimeout(300);
}
const cases = [
  { n: 'docs-f6-1-passport-recommendation', q: 'F-6 연장', picks: ['spouse', 'normal'], open: 3 },
  { n: 'docs-d2-registration-explicit-original-copy', q: 'D-2 외국인등록', picks: [], open: 3 },
  { n: 'docs-e7-1-extension-contract-silent', q: 'E-7-1 연장', picks: [], open: 4 },
  { n: 'docs-e1-extension-contract-explicit-original-copy', q: 'E-1 연장', picks: [], open: 4 },
  { n: 'docs-e9-extension-contract-explicit-copy', q: 'E-9 연장', picks: [], open: 4 },
  { n: 'docs-address-report-original-shown', q: '주소 변경 신고', picks: [], open: 3 },
];
const log = [];
for (const vp of [{ n: 'desktop-1280', w: 1280, h: 900, mobile: false }, { n: 'mobile-390', w: 390, h: 844, mobile: true }]) {
  for (const c of cases) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, userAgent: vp.mobile ? UA : undefined });
    const page = await ctx.newPage(); await boot(page);
    await search(page, c.q, c.picks);
    const full = page.locator('#statusGuidance [data-sg-action="toggle-full"]'); if (await full.count()) { await full.first().click(); await page.waitForTimeout(200); }
    const summaries = page.locator('#statusGuidance .sg-doc-details summary');
    const n = await summaries.count();
    for (let i = 0; i < Math.min(n, c.open); i++) await summaries.nth(i).click();
    const docs = page.locator('#statusGuidance .sg-docs'); if (await docs.count()) await docs.scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
    await page.screenshot({ path: `${OUT}/${vp.n}-${c.n}.png` });
    log.push({ vp: vp.n, case: c.n, forms: await page.locator('#statusGuidance .sg-doc').evaluateAll(els => els.map(e => (e.querySelector('.sg-doc-name')?.textContent || '').slice(0, 26) + ' => ' + (e.querySelector('.sg-doc-form')?.textContent || '-') + ' [' + (e.querySelector('.sg-doc-form')?.getAttribute('data-sg-form-kind') || '') + ']')), note: (await page.locator('#statusGuidance .sg-doc-prep-note').allInnerTexts()).length });
    await ctx.close();
  }
}
console.log(JSON.stringify(log, null, 1));
await browser.close();
