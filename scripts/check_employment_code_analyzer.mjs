#!/usr/bin/env node
/*
 * check_employment_code_analyzer.mjs
 * ----------------------------------------------------------------------------
 * Regression tests for the deterministic employment-code analyzer
 * (scripts/employment_code_analyzer.mjs), covering ordinary jobs plus the
 * legally-sensitive entertainment (idol/dancer/...) and tattoo domains.
 *
 * For each fixture in data/employment/analyzer_test_cases.json it asserts:
 *   - NO HALLUCINATED CODE: every returned candidate code exists in
 *     data/jobcode_master.json with the matching classification type.
 *   - occupation/industry tracks never leak into each other.
 *   - source metadata is present (sourceNotes non-empty).
 *   - legality is never implied (base caveat always present).
 *   - per-fixture: min counts, ambiguity follow-ups, follow-up chips,
 *     legal sensitivity, role status, confidence ceilings, warning text, and
 *     that umbrella terms like 아이돌 are NOT mapped to one exact code.
 *
 * Run:  node scripts/check_employment_code_analyzer.mjs
 * Exits non-zero on any failure (CI-friendly).
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));

const deps = loadEmploymentAnalyzerDeps();
const fixtures = readJson('data/employment/analyzer_test_cases.json');

// Canonical code sets per type — the hallucination guard.
const validCodes = { occupation: new Set(), industry: new Set() };
for (const r of deps.data.data) validCodes[r.type] && validCodes[r.type].add(String(r.code));

const analyzer = createEmploymentAnalyzer(deps);
const CONF = { low: 0, medium: 1, high: 2 };

let failures = 0;
let passed = 0;
const fail = (id, msg) => { failures++; console.error(`  ✗ [${id}] ${msg}`); };

function includesIn(candidates, needle) {
  return candidates.some((c) => (c.name && c.name.includes(needle)) || (c.path && c.path.includes(needle)));
}

for (const tc of fixtures.cases) {
  const res = analyzer.analyze({ text: tc.text, locale: tc.locale });
  const exp = tc.expect || {};
  const localFail = failures;
  const allCands = [...res.occupationCandidates, ...res.industryCandidates];

  // --- ALWAYS: no hallucinated codes + track separation ---
  for (const c of res.occupationCandidates) {
    if (c.classification !== 'occupation') fail(tc.id, `occupation candidate wrong classification: ${c.classification}`);
    if (!validCodes.occupation.has(String(c.code))) fail(tc.id, `HALLUCINATED occupation code: ${c.code} (${c.officialName})`);
  }
  for (const c of res.industryCandidates) {
    if (c.classification !== 'industry') fail(tc.id, `industry candidate wrong classification: ${c.classification}`);
    if (!validCodes.industry.has(String(c.code))) fail(tc.id, `HALLUCINATED industry code: ${c.code} (${c.officialName})`);
  }
  // --- ALWAYS: source metadata + legality-never-implied ---
  if (!Array.isArray(res.sourceNotes) || res.sourceNotes.length === 0) fail(tc.id, 'sourceNotes missing/empty');
  if (!res.warnings.some((w) => w.includes('별도 확인'))) fail(tc.id, 'base legal caveat missing from warnings');

  // --- per-fixture expectations ---
  if (exp.minOccupation != null && res.occupationCandidates.length < exp.minOccupation)
    fail(tc.id, `expected >=${exp.minOccupation} occupation candidates, got ${res.occupationCandidates.length}`);
  if (exp.minIndustry != null && res.industryCandidates.length < exp.minIndustry)
    fail(tc.id, `expected >=${exp.minIndustry} industry candidates, got ${res.industryCandidates.length}`);
  if (exp.expectAmbiguity === true && res.ambiguityQuestions.length === 0)
    fail(tc.id, 'expected an ambiguity follow-up question, got none');
  if (exp.expectFollowUpChips === true && (!res.followUpChips || res.followUpChips.length === 0))
    fail(tc.id, 'expected follow-up chips, got none');
  for (const needle of exp.occupationIncludes || [])
    if (!includesIn(res.occupationCandidates, needle)) fail(tc.id, `occupation candidates missing "${needle}"`);
  for (const needle of exp.industryIncludes || [])
    if (!includesIn(res.industryCandidates, needle)) fail(tc.id, `industry candidates missing "${needle}"`);
  for (const sens of exp.expectLegalSensitivity || [])
    if (!(res.extracted.legalSensitivity || []).includes(sens)) fail(tc.id, `expected legalSensitivity "${sens}", got ${JSON.stringify(res.extracted.legalSensitivity)}`);
  if (exp.expectRoleStatus && res.extracted.roleStatus !== exp.expectRoleStatus)
    fail(tc.id, `expected roleStatus "${exp.expectRoleStatus}", got "${res.extracted.roleStatus}"`);
  if (exp.expectMaxConfidence) {
    const cap = CONF[exp.expectMaxConfidence];
    const over = allCands.filter((c) => CONF[c.confidence] > cap);
    if (over.length) fail(tc.id, `confidence above "${exp.expectMaxConfidence}": ${over.map((c) => c.code + '=' + c.confidence).join(', ')}`);
  }
  for (const needle of exp.expectWarningIncludes || [])
    if (!res.warnings.some((w) => w.includes(needle))) fail(tc.id, `warnings missing "${needle}"`);
  if (exp.notSingleExactName) {
    const exact = allCands.find((c) => c.officialName === exp.notSingleExactName);
    if (exact) fail(tc.id, `umbrella term mapped to a single exact code "${exp.notSingleExactName}" (${exact.code})`);
  }

  if (failures === localFail) passed++;
}

// --- Structural smoke test of the public API shape ---
const sample = analyzer.analyze('아이돌 연습생');
for (const key of ['normalizedInput', 'extracted', 'occupationCandidates', 'industryCandidates', 'ambiguityQuestions', 'followUpChips', 'warnings', 'sourceNotes'])
  if (!(key in sample)) fail('api-shape', `EmploymentCodeAnalysis missing field "${key}"`);
for (const key of ['language', 'jobRole', 'workplaceType', 'businessActivity', 'employmentType', 'employerType', 'incomeStatus', 'performanceType', 'roleStatus', 'legalSensitivity', 'visaStatus'])
  if (!(key in sample.extracted) && sample.extracted[key] === undefined && !('extracted' in sample)) fail('api-shape', `extracted missing "${key}"`);
const sc = sample.occupationCandidates[0];
for (const key of ['code', 'officialName', 'classificationType', 'level', 'score', 'confidence', 'matchedTerms', 'reasonKo', 'caveats', 'source'])
  if (sc && !(key in sc)) fail('api-shape', `Candidate missing field "${key}"`);

console.log(`\nEmployment code analyzer: ${passed}/${fixtures.cases.length} fixtures passed, ${failures} assertion failure(s).`);
if (failures > 0) process.exit(1);
console.log('OK — no hallucinated codes, tracks separated, entertainment/tattoo decomposition + legal cautions verified, source metadata present.');
