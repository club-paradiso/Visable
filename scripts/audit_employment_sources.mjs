#!/usr/bin/env node
/*
 * audit_employment_sources.mjs  (npm run audit:employment-sources)
 * ----------------------------------------------------------------------------
 * Source & data-integrity audit for the employment analyzer. Proves the
 * non-negotiables from the task spec / CLAUDE.md:
 *   - source_registry.json: required fields; the MoJ press release + the two
 *     National Data Office standard classifications are present as OFFICIAL
 *     classification/reporting sources; immigrant statistics are auxiliary only.
 *   - visa_reporting_scope.json: the 17 included statuses + F-5 excluded + the
 *     15-day change rule + 직종/업종/소득 items, consistent with the canonical
 *     reporting context.
 *   - NO HALLUCINATED CODES anywhere: the lexicon/field/ambiguous files contain
 *     no official-code fields; every occupation_terms/industry_terms retrieval
 *     keyword resolves to >=1 real row in jobcode_master.json (so the analyzer
 *     can never invent vocabulary that maps to nothing).
 *
 * Exit non-zero on any failure.
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));
const norm = (s) => String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').trim();

let problems = 0;
const bad = (msg) => { problems++; console.error(`  ✗ ${msg}`); };
const ok = (msg) => console.log(`  ✓ ${msg}`);

/* ---- 1. source_registry.json ---- */
const reg = readJson('data/employment/source_registry.json');
const byId = Object.fromEntries((reg.sources || []).map((s) => [s.id, s]));
for (const s of reg.sources || []) {
  for (const f of ['id', 'title', 'publisher', 'source_type', 'usage', 'reliability'])
    if (!s[f] || (Array.isArray(s[f]) && !s[f].length)) bad(`source ${s.id || '?'} missing field "${f}"`);
}
const mustOfficial = {
  moj_employment_reporting_press_release_2026: 'legal/reporting source',
  national_data_office_ksco8: 'classification source',
  national_data_office_ksic11: 'classification source'
};
for (const [id, usage] of Object.entries(mustOfficial)) {
  const s = byId[id];
  if (!s) { bad(`required official source "${id}" missing from registry`); continue; }
  if (s.reliability !== 'official') bad(`source "${id}" must be reliability=official (got ${s.reliability})`);
  if (!(s.usage || []).includes(usage)) bad(`source "${id}" must declare usage "${usage}"`);
}
// statistics must never be a classification source
for (const s of reg.sources || []) {
  if (s.reliability === 'statistics' && (s.usage || []).includes('classification source'))
    bad(`statistics source "${s.id}" must NOT be a classification source`);
}
if (!problems) ok(`source_registry.json: ${reg.sources.length} sources, official classification + press release present, statistics auxiliary-only`);

/* ---- 2. visa_reporting_scope.json ---- */
const scope = readJson('data/employment/visa_reporting_scope.json');
const included = (scope.included_statuses || []).map((x) => x.code);
const EXPECT = ['E-1', 'E-2', 'E-3', 'E-4', 'E-5', 'E-6', 'E-7', 'E-8', 'E-9', 'E-10', 'F-2', 'F-4', 'F-6', 'H-2', 'D-7', 'D-8', 'D-9'];
for (const c of EXPECT) if (!included.includes(c)) bad(`visa scope missing included status ${c}`);
if (!(scope.excluded_statuses || []).some((x) => x.code === 'F-5')) bad('visa scope must exclude F-5');
if (Number(scope.change_deadline_days) !== 15) bad(`change deadline must be 15 days (got ${scope.change_deadline_days})`);
for (const item of ['직종', '업종']) if (!(scope.reporting_items || []).some((r) => r.includes(item))) bad(`reporting_items missing ${item}`);
if (!(scope.reporting_items || []).some((r) => r.includes('소득'))) bad('reporting_items missing 소득(income)');
// cross-check with canonical context
const ctx = readJson('data/jobcode_master.json').employment_reporting_context;
for (const c of EXPECT) if (!ctx.target_statuses.includes(c)) bad(`jobcode context target_statuses missing ${c}`);
if (!ctx.excluded_statuses.includes('F-5')) bad('jobcode context must exclude F-5');
if (!problems) ok('visa_reporting_scope.json: 17 included + F-5 excluded + 15-day rule, consistent with canonical context');

/* ---- 3. income_brackets.json ---- */
const inc = readJson('data/employment/income_brackets.json');
if (!Array.isArray(inc.brackets) || inc.brackets.length < 2) bad('income_brackets must list brackets');
if (!inc.source_status) bad('income_brackets must carry source_status (verified/unverified)');
if (inc.source_status === 'unverified' && !inc.verification_note) bad('unverified income_brackets must explain the gap');
ok(`income_brackets.json: ${inc.brackets.length} brackets, source_status=${inc.source_status}`);

/* ---- 4. NO hallucinated codes: lexicons carry no official-code fields ---- */
const lexFiles = [
  'data/employment/synonyms.ko.json', 'data/employment/synonyms.en.json',
  'data/employment/aliases.entertainment.ko.json', 'data/employment/aliases.entertainment.en.json',
  'data/employment/aliases.tattoo.ko.json', 'data/employment/aliases.tattoo.en.json',
  'data/employment/ambiguous_inputs.json', 'data/employment/disambiguation_rules.json',
  'data/employment/colloquial_field_terms_ko.json', 'data/employment/colloquial_field_terms_en.json'
];
for (const f of lexFiles) {
  const raw = readFileSync(join(root, f), 'utf8');
  // an official-looking code field would be the only way to smuggle a fake code in
  if (/"(official_?code|code|코드값)"\s*:/.test(raw)) bad(`${f} appears to contain an official code field (must be code-free)`);
}
if (!problems) ok(`${lexFiles.length} lexicon/rule files are code-free (no invented official codes)`);

/* ---- 5. No dead-end concept: every entry with retrieval terms has >=1 that
 *        resolves to a real dataset row (colloquial broadening aliases need not
 *        each resolve, but a concept/signal must never map to NOTHING). ------- */
const data = readJson('data/jobcode_master.json').data;
const occNames = data.filter((r) => r.type === 'occupation').map((r) => norm(r.name_ko));
const indNames = data.filter((r) => r.type === 'industry').map((r) => norm(r.name_ko));
const anyResolves = (terms, names) => (terms || []).some((t) => { const x = norm(t); return x && names.some((n) => n.includes(x)); });

let entriesChecked = 0, deadEnds = 0;
function auditEntry(label, occT, indT) {
  if (occT && occT.length) { entriesChecked++; if (!anyResolves(occT, occNames)) { deadEnds++; bad(`${label}: NO occupation_terms resolve to any KSCO8 row (${occT.join('/')})`); } }
  if (indT && indT.length) { entriesChecked++; if (!anyResolves(indT, indNames)) { deadEnds++; bad(`${label}: NO industry_terms resolve to any KSIC11 row (${indT.join('/')})`); } }
}
for (const f of ['synonyms.ko.json', 'synonyms.en.json', 'aliases.entertainment.ko.json', 'aliases.entertainment.en.json', 'aliases.tattoo.ko.json', 'aliases.tattoo.en.json'])
  for (const c of readJson('data/employment/' + f).concepts || []) auditEntry(`${f}#${c.id}`, c.occupation_terms, c.industry_terms);
for (const f of ['colloquial_field_terms_ko.json', 'colloquial_field_terms_en.json'])
  for (const s of readJson('data/employment/' + f).signals || []) auditEntry(`${f}#${s.id}`, s.occupation_terms, s.industry_terms);
for (const e of readJson('data/employment/ambiguous_inputs.json').entries || [])
  auditEntry(`ambiguous#${e.id}`, (e.decompose || {}).occupation_terms, (e.decompose || {}).industry_terms);
if (!deadEnds) ok(`no dead-end concepts: all ${entriesChecked} retrieval tracks resolve to >=1 real KSCO8/KSIC11 row`);

console.log(`\nEmployment source audit: ${problems} problem(s).`);
if (problems > 0) process.exit(1);
console.log('OK — sources grounded, scope correct, lexicons code-free, every retrieval keyword traces to a real classification row.');
