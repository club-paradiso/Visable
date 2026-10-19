#!/usr/bin/env node
/*
 * check_manual_reader.mjs — contract for manual.html (매뉴얼 원문 읽기).
 *
 *  1. data/manual-reader is complete: every catalog chapter has its chapter file, every
 *     referenced image exists, and source digests match the committed Markdown.
 *  2. Text preservation recorded by scripts/build_manual_reader.py stays within the
 *     page-break-noise budget (nothing added, < 0.5% removed overall), and the Markdown
 *     still matches the independently extracted PDF text of the same edition (≥ 97%).
 *  3. Chapter HTML is inert (it is inserted with innerHTML): no scripts, iframes,
 *     inline event handlers or javascript: URLs.
 *  4. The editorial layer only points at chapters/sections that exist.
 *  5. assets/js/manual-reader-route.js maps every status code and procedure the
 *     status guidance knows to an existing reader chapter, never mixing 사증/체류.
 */
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const json = (p) => JSON.parse(read(p));
let pass = 0; const fails = [];
function ok(cond, msg) { if (cond) pass++; else fails.push(msg); }

const BASE = 'data/manual-reader/';
const cat = json(BASE + 'catalog.json');
const ed = json(BASE + 'editorial.json');
const route = require(join(ROOT, 'assets/js/manual-reader-route.js'));
const SECTION_KEYS = new Set(['scope', 'who', 'period', 'consul', 'cert', 'evisa', 'note', 'extra', 'work', 'grant', 'change', 'extend', 'reentry', 'reg', 'other']);

// 1. sources + files
for (const [tag, s] of Object.entries(cat.sources)) {
  ok(['v', 's'].includes(tag), `source tag ${tag} is v or s`);
  const md = readFileSync(join(ROOT, s.markdown));
  ok(createHash('sha256').update(md).digest('hex') === s.sha256, `${s.markdown}: sha256 matches catalog (rebuild with python3 scripts/build_manual_reader.py)`);
  ok(existsSync(join(ROOT, s.pdf)), `${tag}: official PDF ${s.pdf} exists`);
  ok(s.approval_state === 'needs_review', `${tag}: approval_state stays needs_review until a human content review`);
  ok(s.pdf_crosscheck && s.pdf_crosscheck.ratio >= 0.97, `${tag}: Markdown matches ≥97% of PDF text probes (got ${s.pdf_crosscheck && s.pdf_crosscheck.ratio})`);
}
const keys = new Set(cat.chapters.map((c) => c.key));
let blocksSeen = 0;
const unsafe = /<script\b|<iframe\b|<object\b|<embed\b|\son[a-z]+\s*=|javascript:/i;
for (const c of cat.chapters) {
  for (const tag of ['v', 's']) {
    if (!c[tag]) continue;
    const file = `${BASE}chapters/${tag}/${c.key}.json`;
    ok(existsSync(join(ROOT, file)), `${file} exists`);
    if (!existsSync(join(ROOT, file))) continue;
    const ch = json(file);
    ok(ch.blocks.length === c[tag].sections.length, `${file}: catalog section count matches`);
    ch.blocks.forEach((b, i) => {
      blocksSeen++;
      ok(b.t === 'sec' || b.t === 'html', `${file}#${i}: block type`);
      if (b.t === 'sec') ok(SECTION_KEYS.has(b.k), `${file}#${i}: known section key ${b.k}`);
      ok(!unsafe.test(b.h), `${file}#${i}: chapter HTML is inert`);
      for (const m of b.h.matchAll(/data-img="([\w-]+)"/g)) ok(existsSync(join(ROOT, `assets/manual-reader/img/${m[1]}.webp`)), `${file}#${i}: image ${m[1]}.webp exists`);
    });
  }
}
ok(blocksSeen > 400, `chapters carry the manual body (${blocksSeen} blocks)`);
const search = json(BASE + 'search.json');
ok(search.length === blocksSeen, 'search index has one row per block');

// 2. preservation
const total = cat.preservation.reduce((a, r) => a + r.chars, 0);
const lost = cat.preservation.reduce((a, r) => a + r.missing, 0);
ok(cat.preservation.every((r) => r.added === 0), 'no chapter gained letters the manual does not have');
ok(lost / total < 0.005, `removed page-break noise stays under 0.5% (${(lost / total * 100).toFixed(3)}%)`);
ok(total > 700000, `both manuals present (${total} letters)`);

// 4. editorial layer
for (const s of ed.statuses) ok(keys.has(s.key), `editorial status ${s.code} → chapter ${s.key} exists`);
for (const k of Object.keys(ed.extra_chapters)) ok(keys.has(k), `editorial extra chapter ${k} exists`);
for (const k of Object.keys(ed.section_titles)) ok(SECTION_KEYS.has(k), `section title ${k} is a known key`);
for (const t of ed.tasks) ok(t.keys.every((k) => SECTION_KEYS.has(k)) && ['v', 's'].includes(t.src), `task ${t.id} uses known keys and one manual`);
for (const t of ed.tasks) ok(t.keys.every((k) => (['consul', 'cert', 'evisa'].includes(k)) === (t.src === 'v')), `task ${t.id} never mixes 사증 and 체류 sections`);
for (const q of ed.quick) {
  const c = cat.chapters.find((x) => x.key === q.key);
  const secs = c && c[q.src] ? c[q.src].sections : null;
  ok(!!secs, `quick link ${q.t} → ${q.key}/${q.src} exists`);
  if (secs && (q.sec || q.lab)) ok(secs.some((b) => b.t === 'sec' && (q.lab ? (b.l || '').includes(q.lab) : b.k === q.sec)), `quick link ${q.t} resolves to a section`);
}
ok(ed.editorial === true && /법적 요건이 아닙니다/.test(ed.note), 'editorial layer declares it is not a legal requirement');

// 5. route coverage against the status guidance vocabulary
const sg = json('data/status-guidance-202609.json');
let mapped = 0;
for (const code of Object.keys(sg.codes)) {
  const ch = route.chapterFor(code);
  if (/^[A-H]-\d/.test(code) || code.startsWith('PROGRAM:')) {
    ok(ch && keys.has(ch), `status ${code} → reader chapter (${ch})`);
    if (ch) mapped++;
  }
}
for (const p of sg.procedures) {
  const sec = route.PROCEDURE_SECTION[p.id];
  if (sec) ok((sec[0] === 'v') === (p.domain === 'visa'), `procedure ${p.id} stays in its own manual (${sec[0]} vs ${p.domain})`);
}
ok(route.href('F-6-1', 'extension') === 'manual.html#c-F-6.s.extend', 'F-6-1 extension deep link');
ok(route.href('D-2', 'part_time_work') === 'manual.html#c-D-2.s.parttime', 'D-2 part-time deep link');
ok(route.href('F-4', 'visa_issuance') === 'manual.html#c-dongpo.v.consul', 'F-4 routes to the 외국국적동포 chapter');
ok(route.href('', null) === null, 'no code → no deep link');

// page wiring
const page = read('manual.html');
ok(/assets\/js\/manual-reader-route\.js/.test(page) && /assets\/js\/manual-reader\.js/.test(page), 'manual.html loads route + reader scripts');
ok(/visa_manual_260901\.pdf/.test(page) && /stay_manual_260918\.pdf/.test(page), 'manual.html keeps official PDF fallbacks (noscript)');
const reader = read('assets/js/manual-reader.js');
ok(/원문 발췌 · 검토 전/.test(reader), 'reader shows the needs-review state');
ok(/법적 요건이 아니며|법적 요건이 아닙니다/.test(reader), 'reader footer separates Visable editorial text from requirements');
const index = read('index.html');
ok(/<script defer src="assets\/js\/manual-reader-route\.js"><\/script>/.test(index), 'index.html loads the reader route before civic search');
ok(/href="manual\.html"/.test(index), 'landing links to manual.html');

if (fails.length) { console.error(fails.map((f) => '  FAIL  ' + f).join('\n')); }
console.log(`[check_manual_reader] ${pass} checks passed, ${fails.length} failed (${mapped} status codes routed)`);
process.exit(fails.length ? 1 : 0);
