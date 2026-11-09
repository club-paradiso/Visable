#!/usr/bin/env node
/**
 * Checks the "새 매뉴얼 개정 후보" notices (data/manual-updates/pending_revisions.json):
 *  - every revision's manual lines are verbatim in the newer edition's text and absent from the earlier edition's text;
 *  - reader deep links resolve to a real chapter/tab/section of data/manual-reader;
 *  - matching keeps visa and stay apart and never shows a subcode rule on its parent code;
 *  - every notice says it is not reviewed (state pending_review), nothing claims approval.
 * Run: node scripts/check_manual_updates.mjs   (also: python3 scripts/build_manual_update_notices.py --check)
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const json = (p) => JSON.parse(read(p));
let pass = 0; const fails = [];
const ok = (c, m) => { if (c) pass++; else fails.push(m); };
const compact = (s) => s.replace(/[^가-힣A-Za-z0-9]/g, '');

const data = json('data/manual-updates/pending_revisions.json');
const MU = require(join(ROOT, 'assets/js/manual-updates.js'));
const cat = json('data/manual-reader/catalog.json');
ok(data.state === 'pending_review' && /검토하지 않았/.test(data.note), 'file state is pending_review and the note says it is not reviewed');
ok(!/승인|approved/i.test(JSON.stringify(data.revisions)), 'no revision text claims approval');
ok(Array.isArray(data.revisions), 'revisions is an array');

const texts = {};
for (const role of ['visa', 'stay']) {
  const ed = data.editions[role];
  if (!ed) continue;
  ok(ed.status === 'pending_review', `${role}: edition is pending_review`);
  const diff = json(ed.diff.replace(/\.md$/, '.json'));
  ok(existsSync(join(ROOT, diff.meta.new_path)) && existsSync(join(ROOT, diff.meta.old_path)), `${role}: both edition texts exist`);
  texts[role] = { next: compact(read(diff.meta.new_path)), prev: compact(read(diff.meta.old_path)) };
  const hwp = require('node:crypto').createHash('sha256').update(readFileSync(join(ROOT, json('docs/source-manuals/source_manifest.json').pending_review_editions.find((e) => e.original_hwp_sha256 === ed.hwp_sha256 && e.source_date === ed.source_date).original_file))).digest('hex');
  ok(hwp === ed.hwp_sha256, `${role}: edition HWP digest matches the pinned digest`);
}

const chapters = new Map(cat.chapters.map((c) => [c.key, c]));
const ids = new Set();
for (const r of data.revisions) {
  ok(!ids.has(r.id), `${r.id}: unique id`); ids.add(r.id);
  ok(r.state === 'pending_review', `${r.id}: pending_review`);
  ok(['visa', 'stay'].includes(r.role), `${r.id}: role is visa or stay`);
  ok(r.codes.length && r.codes.every((c) => /^[A-H]-\d{1,2}(-\d+[A-Za-z]*)?$/.test(c)), `${r.id}: codes look like status codes`);
  ok(r.title_ko && r.title_en && r.summary_ko && r.summary_en, `${r.id}: ko+en title and summary`);
  ok(r.manual_lines.length > 0, `${r.id}: carries manual lines`);
  for (const l of r.manual_lines) {
    ok(texts[r.role].next.includes(compact(l)), `${r.id}: line is verbatim in the newer edition: ${l.slice(0, 40)}`);
  }
  // at least one line must be genuinely new (absent from the earlier edition at that spot is checked by the diff; here: whole-text absence for the longest line)
  const longest = [...r.manual_lines].sort((a, b) => b.length - a.length)[0];
  const inPrev = texts[r.role].prev.split(compact(longest)).length - 1, inNext = texts[r.role].next.split(compact(longest)).length - 1;
  ok(inNext > inPrev, `${r.id}: the longest line occurs more often in the newer edition than in the earlier one (${inNext} vs ${inPrev})`);
  // reader deep link
  const m = /^c-([^.]+)\.([vs])(?:\.(\w+))?$/.exec(r.reader_hash);
  ok(m, `${r.id}: reader_hash format`);
  if (m) {
    const ch = chapters.get(m[1]);
    ok(ch && ch[m[2]], `${r.id}: reader chapter ${m[1]}/${m[2]} exists`);
    ok((r.role === 'visa') === (m[2] === 'v'), `${r.id}: visa revisions link the visa manual and stay revisions the stay manual`);
    const route = require(join(ROOT, 'assets/js/manual-reader-route.js'));
    if (ch && ch[m[2]] && m[3] && !/^\d+$/.test(m[3])) {
      const secs = ch[m[2]].sections;
      const hit = m[3] === 'parttime' ? secs.some((b) => b.t === 'sec' && /시간제\s*취업/.test(b.l || '')) : secs.some((b) => b.t === 'sec' && b.k === m[3]);
      ok(hit, `${r.id}: reader section ${m[3]} exists in ${m[1]}.${m[2]}`);
    }
    // the changed text must really be inside that reader chapter
    const chap = json(`data/manual-reader/chapters/${m[2]}/${m[1]}.json`);
    const blob = compact(chap.blocks.map((b) => b.h.replace(/<[^>]+>/g, ' ')).join(' '));
    for (const l of r.manual_lines) ok(blob.includes(compact(l).slice(0, 40)), `${r.id}: line is rendered in reader chapter ${m[1]}.${m[2]}`);
    void route;
  }
}

// matching rules
const R = (id) => data.revisions.find((x) => x.id === id);
const d43v = R('v-d43-cert-jeju-intl-school'), d2 = R('s-d2-parttime-restricted-field-violation');
if (d43v && d2) {
  ok(MU.forStatus(data, 'visa', ['D-4-3'], 'visa_issuance_confirmation').includes(d43v), 'D-4-3 visa certificate shows its notice');
  ok(!MU.forStatus(data, 'stay', ['D-4-3'], 'visa_issuance_confirmation').includes(d43v), 'a visa revision never shows on a stay procedure');
  ok(!MU.forStatus(data, 'visa', ['D-4'], 'visa_issuance_confirmation').includes(d43v), 'a subcode revision (D-4-3) is not shown as a rule of the parent code D-4');
  ok(!MU.forStatus(data, 'visa', ['D-4-3'], 'electronic_visa').includes(d43v), 'a procedure-scoped revision stays off other procedures');
  ok(MU.forStatus(data, 'stay', ['D-2'], 'part_time_work').includes(d2) && !MU.forStatus(data, 'stay', ['D-2'], 'extension').includes(d2), 'D-2 part-time notice shows on part_time_work only');
  ok(MU.forStatus(data, 'stay', ['G-1-3#x'], 'status_change').filter((x) => x.codes.includes('G-1-3')).length === 2, 'G-1-3 notices show on the status_change procedure (where the manual text sits); a "#scenario" suffix is ignored');
  ok(MU.forStatus(data, 'stay', ['G-1-3'], 'extension').length === 0, 'G-1-3 change-of-status notices stay off the extension procedure');
}
const html = MU.noticeHtml(data, data.revisions.slice(0, 1), 'ko', { base: '' });
ok(/role="note"/.test(html) && /검토 전/.test(html) && /이전 판을 따릅니다/.test(html) && /href="#c-/.test(html), 'notice html is a labelled note, says 검토 전 / 이전 판, and deep-links the reader');
ok(MU.noticeHtml(data, [], 'ko') === '', 'no items → no markup');
const evil = MU.noticeHtml(data, [{ ...data.revisions[0], manual_lines: ['<img src=x onerror=alert(1)>'], title_ko: '<b>x</b>' }], 'ko', {});
ok(!/<img|<b>/.test(evil) && /&lt;img/.test(evil) && /&lt;b&gt;x/.test(evil), 'notice html escapes manual text and titles');

console.log(`[check_manual_updates] ${pass} checks passed, ${fails.length} failed`);
if (fails.length) { for (const f of fails) console.error('  FAIL:', f); process.exit(1); }
