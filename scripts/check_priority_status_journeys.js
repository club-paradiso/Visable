#!/usr/bin/env node
/*
 * Static checks for the expanded priority-status journey cleanup (batch 1).
 *
 * Asserts the cleaned target statuses expose clear, non-placeholder,
 * non-diagnostic procedure sections, preserve subtype/family/exact-code
 * distinctions, and do not confuse statuses with one another. D-2 is used as
 * the regression baseline (its golden-path checks must still pass).
 *
 * Failures are real invariant breaks (non-zero exit).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const visas = JSON.parse(fs.readFileSync(path.join(ROOT, 'visa_data.json'), 'utf8'));
const byCode = new Map(visas.map((r) => [r && r.code, r]));

const TARGETS = [
  'A-1', 'A-2', 'A-3', 'C-3', 'D-2', 'D-4', 'D-10', 'E-1', 'E-2', 'E-6', 'E-7',
  'E-9', 'F-1', 'F-2', 'F-3', 'F-4', 'F-5', 'F-6', 'G-1', 'H-1', 'H-2',
];
const PLACEHOLDERS = ['문서명 미상', '비고 정보 없음', 'DATA_MISSING'];
const DIAGNOSTICS = [
  'bad_response', 'unsupported', 'not_attempted',
  'source_family_statuses', 'law_grounding_warnings', 'grounding_used',
];
const EMPLOYMENT_STUDY_DOC_IDS = ['doc_enroll', 'doc_emp_contract', 'doc_eps', 'doc_emp_recom'];

const failures = [];
const passed = [];
function check(name, cond, detail) {
  if (cond) passed.push(name);
  else failures.push(name + (detail ? ' — ' + detail : ''));
}

function flat(rd) {
  if (!rd) return [];
  if (Array.isArray(rd)) return rd.map(String);
  return []
    .concat(rd.commonDocs || [], rd.requiredDocs || [], rd.additionalDocs || [], rd.conditionalDocs || [])
    .map(String);
}
function procText(rec, key) {
  return JSON.stringify((rec && rec.procedures && rec.procedures[key]) || {});
}
function allProcText(rec) {
  return JSON.stringify((rec && rec.procedures) || {});
}
function name(code) {
  const r = byCode.get(code);
  return r ? (r.nameKo || r.name || '') : '';
}

/* 1. Target statuses appear in the audit matrix */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const result = audit.runAudit();
    const seen = new Set(result.records.map((r) => r.statusCode));
    // G-1-5 is represented as a G-1 sub-code, not a standalone record.
    const expected = TARGETS.filter((c) => c !== 'G-1-5');
    ok = expected.every((c) => seen.has(c));
  } catch (e) { ok = false; }
  check('1. all target statuses appear in the audit matrix', ok);
}

/* 2. No user-facing placeholders in target procedures */
{
  const bad = [];
  for (const c of TARGETS) {
    const t = allProcText(byCode.get(c));
    for (const p of PLACEHOLDERS) if (t.includes(p)) bad.push(`${c}:${p}`);
  }
  check('2. target procedures contain no placeholders', bad.length === 0, bad.join(', '));
}

/* 3. No raw diagnostics in target procedures */
{
  const bad = [];
  for (const c of TARGETS) {
    const t = allProcText(byCode.get(c));
    for (const d of DIAGNOSTICS) if (t.includes(d)) bad.push(`${c}:${d}`);
  }
  check('3. target procedures contain no raw diagnostics', bad.length === 0, bad.join(', '));
}

/* 4. A-1/A-2/A-3 do not receive invented worker/student checklists */
{
  const bad = [];
  for (const c of ['A-1', 'A-2', 'A-3']) {
    const rec = byCode.get(c);
    const t = allProcText(rec);
    for (const id of EMPLOYMENT_STUDY_DOC_IDS) if (t.includes(id)) bad.push(`${c}:${id}`);
    // must not be reframed with the long-stay registration surfacing template
    const regSum = String((rec.procedures.registration || {}).summary || '');
    if (regSum.includes('외국인등록(외국인등록증 발급)을 해야 합니다')) bad.push(`${c}:reframed-registration`);
  }
  check('4. A-series keep source-limited diplomatic data (no invented checklists)', bad.length === 0, bad.join(', '));
}

/* 5. C-3 does not imply generic long-term registration for all C-3 users */
{
  const c3 = byCode.get('C-3');
  const reg = c3.procedures.registration || {};
  const text = JSON.stringify(reg);
  const scoped = text.includes('대부분의 단기방문') || text.includes('91일') || text.includes('단기상용');
  // and C-3 registration must not use the universal long-stay surfacing template
  const notUniversal = !String(reg.summary || '').includes('자격으로 90일을 초과하여 체류하는 경우');
  check('5. C-3 registration stays scoped to short-stay special cases', scoped && notUniversal,
    `scoped=${scoped} notUniversal=${notUniversal}`);
}

/* 6. D-4 remains distinct from D-2 */
{
  const d4 = byCode.get('D-4');
  const distinctName = name('D-4') && name('D-2') && name('D-4') !== name('D-2');
  const regSum = String((d4.procedures.registration || {}).summary || '');
  const d4Specific = regSum.includes('D-4') || regSum.includes(name('D-4'));
  check('6. D-4 is distinct from D-2', distinctName && d4Specific,
    `name(D-4)=${name('D-4')} name(D-2)=${name('D-2')}`);
}

/* 7. D-10 does not duplicate destination E-series requirements */
{
  const d10 = byCode.get('D-10');
  const reg = d10.procedures.registration || {};
  // surfaced registration must be source-limited (no fabricated E-series docs)
  const docless = flat(reg.requiredDocs).length === 0;
  const t = allProcText(d10);
  const noEseriesDocs = !t.includes('doc_emp_contract') && !t.includes('doc_eps');
  check('7. D-10 registration is source-limited and not E-series duplicated', docless && noEseriesDocs,
    `docless=${docless} noEseriesDocs=${noEseriesDocs}`);
}

/* 8. E-series statuses preserve distinct procedure logic */
{
  const eNames = ['E-1', 'E-2', 'E-6', 'E-7', 'E-9'].map(name);
  const distinct = new Set(eNames).size === eNames.length && eNames.every(Boolean);
  check('8. E-series statuses have distinct names/logic', distinct, eNames.join(' / '));
}

/* 9. E-7 is not confused with E-9 */
{
  const e7 = name('E-7'); const e9 = name('E-9');
  const ok = e7 && e9 && e7 !== e9
    && e7.includes('특정활동') && e9.includes('비전문');
  check('9. E-7 (특정활동) is not confused with E-9 (비전문취업)', ok, `${e7} vs ${e9}`);
}

/* 10. F-series preserve subtype/family/residence distinctions */
{
  const fNames = ['F-1', 'F-2', 'F-3', 'F-4', 'F-5', 'F-6'].map(name);
  const distinct = new Set(fNames).size === fNames.length && fNames.every(Boolean);
  check('10. F-series statuses have distinct subtype/family names', distinct, fNames.join(' / '));
}

/* 11. F-4 is not confused with H-2 */
{
  const f4 = name('F-4'); const h2 = name('H-2');
  const ok = f4 && h2 && f4 !== h2 && f4.includes('재외동포') && h2.includes('방문취업');
  check('11. F-4 (재외동포) is not confused with H-2 (방문취업)', ok, `${f4} vs ${h2}`);
}

/* 12. F-6 preserves conditional spouse/family-document logic */
{
  const f6 = byCode.get('F-6');
  const docs = flat((f6.procedures.extension || {}).requiredDocs);
  const hasMarriageDoc = docs.some((d) => d.includes('혼인관계증명서'));
  const hasConditional = docs.some((d) => d.includes('혼인단절') || d.includes('이혼') || d.includes('별거'));
  check('12. F-6 extension keeps conditional spouse/family-document logic', hasMarriageDoc && hasConditional,
    `marriageDoc=${hasMarriageDoc} conditional=${hasConditional}`);
}

/* 13. G-1 / G-1-5 preserves exact G-1-5 context */
{
  const g1 = byCode.get('G-1') || {};
  const subs = JSON.stringify(g1.subCodes || g1.subcodes || g1.subTypes || []);
  check('13. G-1-5 sub-code context is preserved', subs.includes('G-1-5'),
    'G-1-5 must remain present in G-1 sub-codes');
}

/* 14. H-1 separates registration from work/scope cautions */
{
  const h1 = byCode.get('H-1');
  const reg = JSON.stringify(h1.procedures.registration || {});
  check('14. H-1 registration is separated from work-scope guidance', reg.includes('취업 범위') && reg.includes('별개'),
    'H-1 registration must note it is separate from work-scope guidance');
}

/* 15. H-2 is not confused with F-4 or E-9 */
{
  const h2 = name('H-2');
  const ok = h2 && h2 !== name('F-4') && h2 !== name('E-9') && h2.includes('방문취업');
  check('15. H-2 (방문취업) is not confused with F-4 or E-9', ok,
    `H-2=${h2} F-4=${name('F-4')} E-9=${name('E-9')}`);
}

/* 16. Existing D-2 golden path checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_d2_student_journey.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('16. D-2 golden path checks still pass', ok);
}

/* 17. Existing all-status audit still runs */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const r = audit.runAudit();
    ok = r.records.some((x) => x.statusCode === 'D-2') && r.records.some((x) => x.statusCode === 'E-7');
  } catch (e) { ok = false; }
  check('17. all-status audit still runs', ok);
}

/* 18. Existing static visa result card checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_static_visa_result_cards.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('18. static visa result card checks still pass', ok);
}

/* ---- report ---- */
console.log('Priority-status journey checks:');
for (const n of passed) console.log('  PASS ' + n);
for (const n of failures) console.log('  FAIL ' + n);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
