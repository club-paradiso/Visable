#!/usr/bin/env node
/*
 * check_employment_code_analyzer.mjs
 * ----------------------------------------------------------------------------
 * Regression tests for the deterministic employment-code analyzer
 * (scripts/employment_code_analyzer.mjs).
 *
 * For each fixture in data/employment/analyzer_test_cases.json it asserts:
 *   - NO HALLUCINATED CODE: every returned candidate code exists in
 *     data/jobcode_master.json with the matching classification type.
 *   - source metadata is present (sourceNotes non-empty).
 *   - minimum occupation / industry candidate counts.
 *   - ambiguity follow-up questions appear when the input is underspecified.
 *   - requested substrings appear in the right track's candidates.
 *   - occupation and industry tracks never leak into each other.
 *
 * Run:  node scripts/check_employment_code_analyzer.mjs
 * Exits non-zero on any failure (CI-friendly).
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));

const master = readJson('data/jobcode_master.json');
const ko = readJson('data/employment/synonyms.ko.json');
const en = readJson('data/employment/synonyms.en.json');
const sources = readJson('data/employment/classification_sources.json');
const fixtures = readJson('data/employment/analyzer_test_cases.json');

// Canonical code sets per type — the hallucination guard.
const validCodes = { occupation: new Set(), industry: new Set() };
for (const r of master.data) validCodes[r.type] && validCodes[r.type].add(String(r.code));

const analyzer = createEmploymentAnalyzer({
  data: master,
  lexicon: { ko, en },
  sources,
  context: master.employment_reporting_context
});

let failures = 0;
let passed = 0;
const fail = (id, msg) => { failures++; console.error(`  ✗ [${id}] ${msg}`); };

function includesIn(candidates, needle) {
  return candidates.some((c) => (c.name && c.name.includes(needle)) || (c.path && c.path.includes(needle)));
}

for (const tc of fixtures.cases) {
  const res = analyzer.analyze({ text: tc.text, locale: tc.locale });
  const exp = tc.expect || {};
  let localFail = failures;

  // --- ALWAYS: no hallucinated codes ---
  for (const c of res.occupationCandidates) {
    if (c.classification !== 'occupation') fail(tc.id, `occupation candidate has wrong classification: ${c.classification}`);
    if (!validCodes.occupation.has(String(c.code))) fail(tc.id, `HALLUCINATED occupation code: ${c.code} (${c.name})`);
  }
  for (const c of res.industryCandidates) {
    if (c.classification !== 'industry') fail(tc.id, `industry candidate has wrong classification: ${c.classification}`);
    if (!validCodes.industry.has(String(c.code))) fail(tc.id, `HALLUCINATED industry code: ${c.code} (${c.name})`);
  }

  // --- ALWAYS: source metadata present ---
  if (!Array.isArray(res.sourceNotes) || res.sourceNotes.length === 0) fail(tc.id, 'sourceNotes missing/empty');
  // --- ALWAYS: base caveat present (never claims legality) ---
  if (!res.warnings.some((w) => w.includes('별도 확인'))) fail(tc.id, 'base legal caveat missing from warnings');

  // --- per-fixture expectations ---
  if (exp.minOccupation != null && res.occupationCandidates.length < exp.minOccupation)
    fail(tc.id, `expected >=${exp.minOccupation} occupation candidates, got ${res.occupationCandidates.length}`);
  if (exp.minIndustry != null && res.industryCandidates.length < exp.minIndustry)
    fail(tc.id, `expected >=${exp.minIndustry} industry candidates, got ${res.industryCandidates.length}`);
  if (exp.expectAmbiguity === true && res.ambiguityQuestions.length === 0)
    fail(tc.id, 'expected an ambiguity follow-up question, got none');
  for (const needle of exp.occupationIncludes || [])
    if (!includesIn(res.occupationCandidates, needle)) fail(tc.id, `occupation candidates missing expected text "${needle}"`);
  for (const needle of exp.industryIncludes || [])
    if (!includesIn(res.industryCandidates, needle)) fail(tc.id, `industry candidates missing expected text "${needle}"`);

  if (failures === localFail) passed++;
}

// --- Structural smoke test of the public API shape on one input ---
const sample = analyzer.analyze('카페에서 바리스타로 일해요');
for (const key of ['normalizedInput', 'extracted', 'occupationCandidates', 'industryCandidates', 'ambiguityQuestions', 'warnings', 'sourceNotes']) {
  if (!(key in sample)) fail('api-shape', `EmploymentCodeAnalysis missing field "${key}"`);
}
const sc = sample.occupationCandidates[0];
for (const key of ['code', 'name', 'classification', 'level', 'score', 'confidence', 'matchedTerms', 'reason', 'source']) {
  if (sc && !(key in sc)) fail('api-shape', `Candidate missing field "${key}"`);
}

console.log(`\nEmployment code analyzer: ${passed}/${fixtures.cases.length} fixtures passed, ${failures} assertion failure(s).`);
if (failures > 0) process.exit(1);
console.log('OK — no hallucinated codes, tracks separated, source metadata present.');
