/*
 * browser_status_matrix.mjs — Restore Trust audit (2026-10-28), real-browser pass.
 *
 * Searches every status code in data/status-guidance-202609.json on index.html,
 * in batches of 10, at a phone width (390×844) and records per code:
 *   kind        what the result page rendered (question / resolved / source-only …)
 *   chips       procedure chips offered, and how many carry 원문 확인
 *   legend      whether the chooser explains the 원문 확인 mark
 *   source      for the first source-only procedure: the cited page, whether the
 *               verbatim preview rendered, and whether every preview line is on
 *               that corpus page
 *   overflow    horizontal scroll at 390px
 *   errors      uncaught page errors
 * Ends with an XSS probe of the search field. Writes CSV to --out (default stdout summary only).
 *
 *   python3 -m http.server 4173 &   # repo root
 *   node scripts/browser_status_matrix.mjs --base http://127.0.0.1:4173 --out docs/audits/restore-trust-2026-10-28/test-matrix.csv
 *
 * Needs Playwright (npm install). PARADISO_PW_EXECUTABLE points at a pre-installed Chromium.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { chromium } from 'playwright';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const BASE = arg('--base', 'http://127.0.0.1:4173');
const OUT = arg('--out', null);
const LIMIT = Number(arg('--limit', '0'));
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
// The preview drops PDF bullet glyphs (private-use characters); compare with them removed on both sides.
const flat = (t) => String(t).replace(/[\uE000-\uF8FF\u{F0000}-\u{FFFFD}]/gu, '').replace(/\s+/g, ' ').trim();
const corpus = {};
for (const s of JSON.parse(readFileSync(join(ROOT, 'data/manual-corpus/catalog.json'), 'utf8')).sources) corpus[s.id] = new Map(JSON.parse(readFileSync(join(ROOT, s.sections), 'utf8')).map((r) => [r.page, flat(r.text)]));

let codes = Object.entries(bundle.codes).filter(([, v]) => v.procedures && (v.kind === 'status' || v.kind === 'substatus')).map(([k]) => k);
if (LIMIT) codes = codes.slice(0, LIMIT);

const browser = await chromium.launch(process.env.PARADISO_PW_EXECUTABLE ? { executablePath: process.env.PARADISO_PW_EXECUTABLE } : {});
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
await ctx.route('**/api/**', (r) => r.abort());

async function one(code) {
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message.slice(0, 80)));
  const row = { code, kind: '', chips: 0, badges: 0, legend: false, src_proc: '', src_page: '', preview: '', verbatim: '', overflow: false, errors: '' };
  try {
    await page.goto(`${BASE}/index.html?q=${encodeURIComponent(code)}`);
    await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 25_000 });
    await page.waitForTimeout(300);
    row.kind = await page.locator('#statusGuidance').getAttribute('data-sg-kind');
    if (row.kind === 'question') {
      row.chips = await page.locator('#statusGuidance .sg-option[data-sg-dim="__procedure"]').count();
      row.badges = await page.locator('#statusGuidance .sg-option[data-sg-dim="__procedure"] .sg-state-source_only').count();
      row.legend = (await page.locator('.sg-chip-legend').count()) > 0;
      const so = page.locator('#statusGuidance .sg-option[data-sg-dim="__procedure"]:has(.sg-state-source_only)').first();
      if (await so.count()) {
        row.src_proc = await so.getAttribute('data-sg-value');
        await so.click();
        await page.waitForSelector('#statusGuidance[data-sg-kind]:not([data-sg-kind="question"])', { timeout: 15_000 }).catch(() => {});
        const btn = page.locator('#statusGuidance .sg-btn-source').first();
        if (await btn.count()) {
          row.src_page = await btn.getAttribute('data-sg-page');
          const sid = await btn.getAttribute('data-sg-source');
          const prev = page.locator('#statusGuidance .sg-source-preview');
          if (await prev.count()) {
            await prev.locator('.sg-source-excerpt').waitFor({ timeout: 10_000 }).catch(() => {});
            const lines = (await prev.locator('.sg-source-excerpt p').allInnerTexts()).filter((l) => l !== '…');
            row.preview = lines.length ? 'shown' : 'empty';
            const text = corpus[sid] && corpus[sid].get(Number(row.src_page));
            row.verbatim = lines.length ? String(!!text && lines.every((l) => text.includes(flat(l)))) : '';
          } else row.preview = 'none';
        }
      }
    }
    row.overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  } catch (e) { errors.push('harness: ' + e.message.split('\n')[0].slice(0, 80)); }
  row.errors = errors.join(' | ');
  await page.close();
  return row;
}

const rows = [];
for (let i = 0; i < codes.length; i += 10) {
  const batch = codes.slice(i, i + 10);
  const res = [];
  for (let j = 0; j < batch.length; j += 5) res.push(...await Promise.all(batch.slice(j, j + 5).map(one)));
  rows.push(...res);
  const bad = res.filter((r) => r.errors || r.overflow || r.verbatim === 'false').length;
  console.log(`batch ${i / 10 + 1}/${Math.ceil(codes.length / 10)}: ${batch[0]}…${batch[batch.length - 1]}  issues=${bad}`);
}

// XSS probe: the query is echoed on the result page; nothing it carries may execute.
const probe = await ctx.newPage();
let fired = false;
await probe.exposeFunction('__xss', () => { fired = true; });
await probe.goto(`${BASE}/index.html?q=${encodeURIComponent('<img src=x onerror=__xss()>"><svg onload=__xss()> F-4')}`);
await probe.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 25_000 }).catch(() => {});
await probe.waitForTimeout(1500);
const injected = await probe.evaluate(() => document.querySelectorAll('#statusGuidance img[src="x"], #statusGuidance svg[onload], #mainContent img[src="x"]').length);
await browser.close();

const sum = (f) => rows.filter(f).length;
console.log(`codes: ${rows.length}`);
console.log(`kinds: ${JSON.stringify(rows.reduce((a, r) => { a[r.kind || 'none'] = (a[r.kind || 'none'] || 0) + 1; return a; }, {}))}`);
console.log(`choosers: ${sum((r) => r.kind === 'question')}, chips: ${rows.reduce((a, r) => a + r.chips, 0)}, 원문 확인 badges: ${rows.reduce((a, r) => a + r.badges, 0)}, legend missing where badges shown: ${sum((r) => r.badges && !r.legend)}`);
console.log(`source-only answers opened: ${sum((r) => r.src_proc)}, preview shown: ${sum((r) => r.preview === 'shown')}, verbatim mismatches: ${sum((r) => r.verbatim === 'false')}`);
console.log(`overflow@390: ${sum((r) => r.overflow)}, page errors: ${sum((r) => r.errors)}`);
console.log(`xss: handler fired=${fired}, injected nodes=${injected}`);
if (OUT) {
  const cols = Object.keys(rows[0]);
  const q = (v) => { const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  writeFileSync(OUT, [cols.join(','), ...rows.map((r) => cols.map((c) => q(r[c])).join(','))].join('\n') + '\n');
  console.log(`wrote ${OUT}`);
}
if (fired || injected || rows.some((r) => r.errors || r.verbatim === 'false')) process.exitCode = 1;
