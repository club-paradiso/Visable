/*
 * audit_evidence_volume.mjs — Restore Trust audit (2026-10-28).
 * Counts the "관련 원문" evidence list the result page builds for a status
 * (assets/js/manual-corpus-search.js, intent branch) and how many of those
 * pages never name the status at all.
 *
 *   node scripts/audit_evidence_volume.mjs [F-4 H-2 ...]   # table
 *   node scripts/audit_evidence_volume.mjs --check         # regression gate
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/manual-corpus-search.js'), 'utf8'))();
const MS = globalThis.VisableManualSearch;
const catalog = read('data/manual-corpus/catalog.json');
const pages = [].concat(...catalog.sources.map((s) => read(s.sections)));
const index = MS.prepare(catalog.sources, pages);
const bundle = read('data/status-guidance-202609.json');
const argCodes = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const codes = process.argv.includes('--check') ? [] : argCodes.length ? argCodes : ['F-4', 'H-2', 'F-5', 'E-7', 'D-2', 'F-6', 'G-1', 'F-2', 'E-9', 'D-10'];
const parentOf = (c) => c.split('-').slice(0, 2).join('-');
function intentFor(code, procedure) {
  const chapters = {};
  Object.keys(bundle.chapters || {}).forEach((mid) => { const c = bundle.chapters[mid][parentOf(code)]; const src = bundle.sources[mid]; if (c && src && src.corpus_source_id) chapters[src.corpus_source_id] = [c.pdf_start, c.pdf_end]; });
  const proc = procedure ? bundle.procedures.find((p) => p.id === procedure) : null;
  return { status: code, procedure: procedure || null, chapters, anchors: [], domain: proc ? (proc.domain === 'visa' ? 'visa_issuance' : 'stay') : null };
}
const nameOf = (code) => (bundle.codes[code] || {}).name_ko || '';
if (!process.argv.includes("--check")) console.log('query                      results  no-status-mention  cross-domain');
for (const code of codes) {
  for (const proc of [null, 'visa_issuance', 'extension']) {
    const intent = intentFor(code, proc);
    const hits = MS.search(index, code + ' ' + nameOf(code), { intent });
    const name = nameOf(code);
    const off = hits.filter((h) => { const t = MS.normalize(h.page.text); return !t.includes(MS.normalize(code)) && !(name && t.includes(name)); }).length;
    const cross = intent.domain ? hits.filter((h) => h.source.domain !== intent.domain).length : 0;
    console.log(`${(code + ' ' + (proc || '(status only)')).padEnd(26)} ${String(hits.length).padStart(7)}  ${String(off).padStart(17)}  ${String(cross).padStart(12)}`);
  }
}

// --check: procedure-scoped evidence never crosses manuals, and a shared chapter never
// admits a page that names only other statuses (the 동포 handbook case).
if (process.argv.includes('--check')) {
  const fails = [];
  for (const code of ['F-4', 'H-2', 'F-5', 'E-7', 'D-2', 'F-6', 'G-1', 'F-2', 'E-9', 'D-10']) {
    for (const proc of ['visa_issuance', 'extension', 'status_change']) {
      const intent = intentFor(code, proc);
      const cross = MS.search(index, code, { intent }).filter((h) => h.source.domain !== intent.domain);
      if (cross.length) fails.push(`${code} ${proc}: ${cross.length} page(s) from the other manual`);
    }
    const intent = intentFor(code, null);
    const parent = parentOf(code).toLowerCase();
    const foreign = MS.search(index, code, { intent }).filter((h) => { const row = index.rows.find((r) => r.page === h.page); return row && row.codes.length && !row.codes.some((c) => c === parent || c.startsWith(parent + '-')); });
    if (foreign.length) fails.push(`${code}: ${foreign.length} page(s) naming only other statuses`);
  }
  if (fails.length) { console.error('[audit_evidence_volume] FAIL\n  ' + fails.join('\n  ')); process.exit(1); }
  console.log('[audit_evidence_volume] OK — procedure evidence stays in its manual; no other-status-only pages');
}
