#!/usr/bin/env node
/*
 * employment_failure_report.mjs  (dev-only)
 * ----------------------------------------------------------------------------
 * Summarizes employment-analyzer query logs (the records produced by
 * employment_failure_log.mjs) into an actionable coverage report:
 *   - top failed (no-result) queries
 *   - top low-confidence queries
 *   - queries that triggered a clarification
 *   - queries where the user picked "none of these"
 *   - candidate aliases that should be added (signals seen on failing queries)
 *
 * Usage:
 *   node scripts/employment_failure_report.mjs [path/to/log.jsonl]
 *
 * Default log path: data/ops/employment_query_log.jsonl  (JSON Lines, one
 * record per line). The app is static; until a backend persists records there,
 * this prints how to wire logging (see employment_failure_log.mjs `persist`).
 * ----------------------------------------------------------------------------
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const logPath = process.argv[2] || join(root, 'data/ops/employment_query_log.jsonl');

if (!existsSync(logPath)) {
  console.log(`No log file at ${logPath}.`);
  console.log('\nParadiso is a static site, so analyzer query logs are not persisted by default.');
  console.log('To collect them, attach a logger in the UI and forward records to a backend:');
  console.log('  const logger = window.EmploymentFailureLog.createFailureLogger({');
  console.log("    persist: (rec) => navigator.sendBeacon('/api/employment-log', JSON.stringify(rec))");
  console.log('  });');
  console.log('  logger.log(analysis, { userSelected });  // after each search / selection');
  console.log('\nThe backend appends each record as one JSON line to this path, then re-run this report.');
  process.exit(0);
}

const lines = readFileSync(logPath, 'utf8').split('\n').map((l) => l.trim()).filter(Boolean);
const records = [];
for (const l of lines) { try { records.push(JSON.parse(l)); } catch { /* skip malformed */ } }

const tally = (pred, keyFn) => {
  const m = new Map();
  for (const r of records) if (pred(r)) { const k = keyFn(r); m.set(k, (m.get(k) || 0) + 1); }
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
};
const show = (title, rows, n = 20) => {
  console.log(`\n## ${title} (${rows.length})`);
  rows.slice(0, n).forEach(([k, c]) => console.log(`  ${String(c).padStart(4)}  ${k}`));
  if (!rows.length) console.log('  (none)');
};

console.log(`Employment analyzer query report — ${records.length} record(s) from ${logPath}`);
show('Top failed (no-result) queries', tally((r) => r.noResultFlag, (r) => r.query));
show('Top low-confidence queries', tally((r) => r.lowConfidenceFlag && !r.noResultFlag, (r) => r.query));
show('Queries that triggered a clarification', tally((r) => r.clarificationFlag, (r) => r.query));
show('Queries where user selected "none of these"', tally((r) => r.userSelected === 'none', (r) => r.query));

// Alias candidates: signals detected on failing queries are concrete terms that
// should map to a code — surface them grouped so they can be added to the lexicon.
const sig = new Map();
for (const r of records) {
  if (!(r.noResultFlag || r.lowConfidenceFlag)) continue;
  const s = r.parsedSignals || {};
  [...(s.places || []), ...(s.objects || []), ...(s.actions || [])].forEach((t) => sig.set(t, (sig.get(t) || 0) + 1));
}
show('Candidate aliases to add (signals on failing queries)', [...sig.entries()].sort((a, b) => b[1] - a[1]));

// language / mode distribution of failures
show('Failures by detected language', tally((r) => r.noResultFlag || r.lowConfidenceFlag, (r) => r.detectedLanguage));
show('Failures by mode', tally((r) => r.noResultFlag || r.lowConfidenceFlag, (r) => r.mode));
console.log('');
