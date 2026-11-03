#!/usr/bin/env node
/*
 * check_employment_benchmark.mjs
 * ----------------------------------------------------------------------------
 * End-to-end accuracy + friction benchmark for the 직종·업종 finder, scored on
 * data/employment/realistic_benchmark.json (inputs written the way people
 * actually type). Reports, per track:
 *   top-1  – the first card shown is an acceptable code
 *   top-3  – an acceptable code is among the first three cards
 *   miss   – no acceptable code in the five the analyzer returns
 * and for the flow:
 *   gated  – a clarification question hides the candidates until answered
 *   empty  – no candidate at all on a scored track
 *
 *   node scripts/check_employment_benchmark.mjs            # summary + gates
 *   node scripts/check_employment_benchmark.mjs --verbose  # every case
 *   node scripts/check_employment_benchmark.mjs --json     # machine-readable
 *
 * Exits non-zero when a gate in GATES is not met, so a regression shows up in
 * CI. The gates were set from a measured run, not guessed (see the PR).
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const fileArg = process.argv.indexOf('--file');
const benchPath = fileArg > 0 ? process.argv[fileArg + 1] : 'data/employment/realistic_benchmark.json';
const bench = JSON.parse(readFileSync(join(root, benchPath), 'utf8'));
// Held-out sets report numbers only; the gates apply to the main set.
const reportOnly = process.argv.includes('--report-only');

const verbose = process.argv.includes('--verbose');
const asJson = process.argv.includes('--json');

// Minimum shares (0–1). Raised as the analyzer improves; never lowered to pass.
export const GATES = {
  occupation: { top1: 0.85, top3: 0.95 },
  industry: { top1: 0.8, top3: 0.9 },
  maxGated: 0.15
};

// The UI (renderJobcodeList, guided mode) lists reportable leaf codes before
// broad parent codes, keeping the analyzer's order inside each group. Score that
// order, because it is what the person sees.
const deps = loadEmploymentAnalyzerDeps();
const parents = { occupation: new Set(), industry: new Set() };
for (const r of deps.data.data) if (r.parent_code && parents[r.type]) parents[r.type].add(String(r.parent_code));
const asShown = (list, track) => {
  const leaf = (c) => !parents[track].has(String(c.code));
  return [...(list || []).filter(leaf), ...(list || []).filter((c) => !leaf(c))];
};
const analyzer = createEmploymentAnalyzer(deps);
const accepts = (pattern, code) => (pattern.endsWith('*') ? String(code).startsWith(pattern.slice(0, -1)) : String(code) === pattern);
const rankOf = (list, patterns) => {
  const i = (list || []).findIndex((c) => patterns.some((p) => accepts(p, c.code)));
  return i < 0 ? null : i + 1;
};

const stats = { occupation: { n: 0, top1: 0, top3: 0, empty: 0 }, industry: { n: 0, top1: 0, top3: 0, empty: 0 }, gated: 0, cases: bench.cases.length };
const rows = [];
for (const c of bench.cases) {
  const r = analyzer.analyze({ text: c.text, locale: 'ko' });
  // Gated = candidates hidden behind a question. Uses the analyzer's blocking
  // flag when it reports one, else the older "any question gates" behaviour.
  const blocking = typeof r.clarificationBlocking === 'boolean' ? r.clarificationBlocking : !!r.clarificationRequired;
  const row = { id: c.id, text: c.text, gated: blocking, question: r.clarificationQuestion || null };
  if (row.gated) stats.gated++;
  for (const [track, key, list] of [['occupation', 'occ', asShown(r.occupationCandidates, 'occupation')], ['industry', 'ind', asShown(r.industryCandidates, 'industry')]]) {
    const want = c[key];
    if (!Array.isArray(want) || !want.length) continue;
    const s = stats[track];
    s.n++;
    const rank = rankOf(list, want);
    if (!list || !list.length) s.empty++;
    if (rank === 1) s.top1++;
    if (rank && rank <= 3) s.top3++;
    row[track] = { want, rank, got: (list || []).slice(0, 3).map((x) => `${x.code} ${x.officialName || x.name_ko || ''}`.trim()) };
  }
  rows.push(row);
}

const pct = (a, b) => (b ? a / b : 1);
const summary = {
  occupation: { cases: stats.occupation.n, top1: pct(stats.occupation.top1, stats.occupation.n), top3: pct(stats.occupation.top3, stats.occupation.n), empty: stats.occupation.empty },
  industry: { cases: stats.industry.n, top1: pct(stats.industry.top1, stats.industry.n), top3: pct(stats.industry.top3, stats.industry.n), empty: stats.industry.empty },
  gated: pct(stats.gated, stats.cases),
  cases: stats.cases
};

if (asJson) {
  console.log(JSON.stringify({ summary, rows }, null, 2));
} else {
  const f = (x) => `${(x * 100).toFixed(1)}%`;
  if (verbose) {
    for (const row of rows) {
      const parts = ['occupation', 'industry'].filter((t) => row[t]).map((t) => `${t[0]}:${row[t].rank || '✗'} [${row[t].got.join(' | ')}]`);
      console.log(`${row.gated ? 'G' : ' '} ${row.id.padEnd(14)} ${row.text}\n      ${parts.join('\n      ')}${row.gated ? `\n      Q: ${row.question}` : ''}`);
    }
  }
  console.log(`\nEmployment benchmark: ${benchPath} (${summary.cases} realistic inputs)`);
  console.log(`  occupation  top-1 ${f(summary.occupation.top1)}  top-3 ${f(summary.occupation.top3)}  empty ${summary.occupation.empty}/${summary.occupation.cases}`);
  console.log(`  industry    top-1 ${f(summary.industry.top1)}  top-3 ${f(summary.industry.top3)}  empty ${summary.industry.empty}/${summary.industry.cases}`);
  console.log(`  gated by a question before candidates: ${f(summary.gated)}`);
}

const failed = [];
for (const t of ['occupation', 'industry']) {
  if (summary[t].top1 < GATES[t].top1) failed.push(`${t} top-1 ${(summary[t].top1 * 100).toFixed(1)}% < ${GATES[t].top1 * 100}%`);
  if (summary[t].top3 < GATES[t].top3) failed.push(`${t} top-3 ${(summary[t].top3 * 100).toFixed(1)}% < ${GATES[t].top3 * 100}%`);
}
if (summary.gated > GATES.maxGated) failed.push(`gated ${(summary.gated * 100).toFixed(1)}% > ${GATES.maxGated * 100}%`);
if (!asJson) {
  if (reportOnly) console.log(`REPORT (held-out, not gated)${failed.length ? ` — below main-set gates: ${failed.join('; ')}` : ' — meets main-set gates'}`);
  else console.log(failed.length ? `FAIL — ${failed.join('; ')}` : 'OK — accuracy and friction gates met.');
}
process.exit(failed.length && !reportOnly ? 1 : 0);
