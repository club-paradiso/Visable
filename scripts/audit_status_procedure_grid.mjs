/*
 * audit_status_procedure_grid.mjs
 * ----------------------------------------------------------------------------
 * Restore Trust audit (2026-10-28): walks every status code × procedure cell of
 * data/status-guidance-202609.json through the real resolver
 * (assets/js/status-guidance.js, pure functions) and compares
 *
 *   stored state codes[code].procedures[proc].s
 *   chip state   the badge the procedure chooser renders next to the procedure
 *                name (e.g. 원문 확인 = SOURCE_ONLY), read from the resolver itself
 *   outcome      what picking that chip actually renders (resolved guidance,
 *                a follow-up question, an unresolved list, or the source-only page)
 *
 * and flags cells where the two disagree. Questions are answered with each
 * offered option in turn (depth-first, capped) so a cell counts as "guidance"
 * when at least one reachable answer path ends in structured guidance.
 *
 *   node scripts/audit_status_procedure_grid.mjs            # summary
 *   node scripts/audit_status_procedure_grid.mjs --csv out  # also write out/inventory.csv
 *   node scripts/audit_status_procedure_grid.mjs --check    # exit 1 on a chip/outcome mismatch
 * ----------------------------------------------------------------------------
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundleArg = process.argv.indexOf('--bundle');
const bundle = JSON.parse(readFileSync(bundleArg > 0 ? process.argv[bundleArg + 1] : join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;

const args = process.argv.slice(2);
const csvDir = args.includes('--csv') ? args[args.indexOf('--csv') + 1] : null;
const strict = args.includes('--check');

// Explore answer paths; return the set of terminal kinds reachable (capped).
function outcomes(code, proc) {
  const seen = new Set();
  let budget = 40;
  function go(answers, depth) {
    if (budget-- <= 0 || depth > 6) { seen.add('capped'); return; }
    const state = { interp: SG.interpret(code, bundle), answers: { ...answers }, procedure: proc, status: code, history: [], lang: 'ko' };
    let step;
    try { step = SG.nextStep(state, bundle); } catch (e) { seen.add('error:' + e.message.slice(0, 60)); return; }
    if (step.kind !== 'question') {
      // A reached rule still counts as source-only when its own completeness says so (a summary, no structured list).
      const e = step.entries && step.entries[0];
      if (step.kind === 'source-only') seen.add('source-only:' + (step.state || 'UNVERIFIED'));
      else if (e && e.completeness === 'SOURCE_ONLY') seen.add(step.kind + ':summary-only');
      else seen.add(step.kind + (e && e.completeness ? ':' + e.completeness : ''));
      return;
    }
    for (const o of step.options || []) go({ ...answers, [step.dimension]: o.id }, depth + 1);
  }
  go({}, 0);
  return [...seen];
}

// The badge the procedure chooser actually shows for each procedure of a code.
function shownChips(code) {
  const step = SG.nextStep({ interp: SG.interpret(code, bundle), answers: {}, procedure: null, status: code, history: [], lang: 'ko' }, bundle);
  const out = {};
  if (step.kind === 'question' && step.dimension === '__procedure') step.options.forEach((o) => { out[o.id] = o.state; });
  return out;
}

const rows = [];
for (const [code, info] of Object.entries(bundle.codes)) {
  if (!info.procedures) continue;
  const shown = shownChips(code);
  for (const [proc, raw] of Object.entries(info.procedures || {})) {
    const outs = outcomes(code, proc);
    // cell.s is the stored state; chip is what the chooser renders (absent when the procedure is not offered).
    const cell = { ...raw, s: proc in shown ? shown[proc] : raw.s };
    const guidance = outs.some((k) => /^(resolved|procedure)(:(?!summary-only)|$)/.test(k));
    const sourceOnly = outs.filter((k) => k.startsWith('source-only'));
    let verdict = 'consistent';
    if (cell.s === 'SOURCE_ONLY' && guidance) verdict = 'chip-understates';      // chip says 원문 확인, guidance is reachable
    if (cell.s === 'SUPPORTED' && !guidance && sourceOnly.length) verdict = 'chip-overstates'; // chip silent, no guidance
    rows.push({ id: `${code}::${proc}`, code, parent: info.parent || '', proc, stored: raw.s, offered: proc in shown, chip: cell.s, docs: cell.d || '', manual: cell.m || '', page: cell.p ?? '', outcomes: outs.join('|'), guidance, verdict });
  }
}

const count = (f) => rows.filter(f).length;
const byState = {};
rows.forEach((r) => { byState[r.chip] = (byState[r.chip] || 0) + 1; });
console.log(`cells: ${rows.length} (status codes: ${new Set(rows.map((r) => r.code)).size}, procedures: ${new Set(rows.map((r) => r.proc)).size})`);
console.log('chip states:', JSON.stringify(byState));
console.log(`guidance reachable: ${count((r) => r.guidance)} / ${rows.length}`);
console.log(`chip-understates (원문 확인 shown, guidance reachable): ${count((r) => r.verdict === 'chip-understates')}`);
console.log(`chip-overstates (no badge, no guidance): ${count((r) => r.verdict === 'chip-overstates')}`);
const errs = rows.filter((r) => /error|capped/.test(r.outcomes));
console.log(`resolver errors/capped: ${errs.length}`);
for (const r of rows.filter((r) => r.verdict !== 'consistent').slice(0, 40)) console.log(`  ${r.verdict}  ${r.id}  chip=${r.chip}  → ${r.outcomes}`);
for (const r of errs.slice(0, 10)) console.log(`  error  ${r.id} → ${r.outcomes}`);

if (csvDir) {
  mkdirSync(csvDir, { recursive: true });
  const cols = ['id', 'code', 'parent', 'proc', 'stored', 'offered', 'chip', 'docs', 'manual', 'page', 'outcomes', 'guidance', 'verdict'];
  const q = (v) => { const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  writeFileSync(join(csvDir, 'inventory.csv'), [cols.join(','), ...rows.map((r) => cols.map((c) => q(r[c])).join(','))].join('\n') + '\n');
  console.log(`wrote ${join(csvDir, 'inventory.csv')}`);
}
// A parent code must never be answered with one subcode's rule (CLAUDE.md "do not flatten subcodes").
const leaks = [];
for (const [code, info] of Object.entries(bundle.codes)) {
  if (info.kind !== 'status' || !info.procedures) continue;
  for (const proc of Object.keys(info.procedures)) {
    const step = SG.nextStep({ interp: SG.interpret(code, bundle), answers: {}, procedure: proc, status: code, history: [], lang: 'ko' }, bundle);
    if (step.kind === 'resolved' && step.entries[0].target.split('~')[0] !== code && !(step.entries[0].covers || []).includes(code)) leaks.push(`${code}::${proc} -> ${step.entries[0].target}`);
  }
}
console.log(`parent cells answered by a subcode-only rule: ${leaks.length}`);
leaks.slice(0, 20).forEach((l) => console.log('  ' + l));
if (strict && (leaks.length || rows.some((r) => r.verdict !== 'consistent' || /error/.test(r.outcomes)))) process.exit(1);
