#!/usr/bin/env node
/*
 * Static checks for the remaining standard status-journey cleanup (batch 2).
 *
 * Asserts the cleaned remaining target statuses expose clear, non-placeholder,
 * non-diagnostic procedure sections; that short-stay/exemption statuses are not
 * presented as ordinary long-term registration statuses; and that each status
 * keeps its distinct purpose (no collapsing of D-series or E-series into generic
 * guidance). The already-merged D-2, expanded-priority, and exact-code-search
 * checks are run as regression baselines.
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
  'B-1', 'B-2', 'C-1', 'C-4',
  'D-1', 'D-3', 'D-5', 'D-6', 'D-7', 'D-8', 'D-9',
  'E-3', 'E-4', 'E-5', 'E-10',
];
const SHORTSTAY = ['B-1', 'B-2', 'C-1', 'C-4'];
const LONGSTAY_D = ['D-1', 'D-3', 'D-5', 'D-6', 'D-7', 'D-8', 'D-9'];
const PLACEHOLDERS = ['문서명 미상', '비고 정보 없음', 'DATA_MISSING', '매뉴얼 확인 필요', '페이지 확인 필요'];
const DIAGNOSTICS = [
  'bad_response', 'unsupported', 'not_attempted',
  'source_family_statuses', 'law_grounding_warnings', 'grounding_used',
];
const DEV_NOTES = ['자동 추출', '자동 확정', 'PDF 텍스트', '수동 검토', '수동 대조', '구조화해야'];
// Employment doc IDs/terms that must NOT be invented onto short-stay statuses.
const EMPLOYMENT_DOC_IDS = ['doc_emp_contract', 'doc_eps', 'doc_enroll'];

const failures = [];
const passed = [];
function check(name, cond, detail) {
  if (cond) passed.push(name);
  else failures.push(name + (detail ? ' — ' + detail : ''));
}

function allProcText(rec) {
  return JSON.stringify((rec && rec.procedures) || {});
}
function name(code) {
  const r = byCode.get(code);
  return r ? (r.nameKo || r.name || '') : '';
}
function regSummary(code) {
  const r = byCode.get(code);
  return String(((r && r.procedures && r.procedures.registration) || {}).summary || '');
}

/* 1. Remaining target statuses appear in the audit matrix */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const seen = new Set(audit.runAudit().records.map((r) => r.statusCode));
    ok = TARGETS.every((c) => seen.has(c));
  } catch (e) { ok = false; }
  check('1. all remaining target statuses appear in the audit matrix', ok);
}

/* 2. No user-facing placeholders / fake doc rows in target procedures */
{
  const bad = [];
  for (const c of TARGETS) {
    const t = allProcText(byCode.get(c));
    for (const p of PLACEHOLDERS) if (t.includes(p)) bad.push(`${c}:${p}`);
  }
  check('2. target procedures contain no placeholders/fake doc rows', bad.length === 0, bad.join(', '));
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

/* 4. No developer-facing extraction notes leak to users */
{
  const bad = [];
  for (const c of TARGETS) {
    const t = allProcText(byCode.get(c));
    for (const d of DEV_NOTES) if (t.includes(d)) bad.push(`${c}:${d}`);
  }
  check('4. target procedures contain no developer-facing extraction notes', bad.length === 0, bad.join(', '));
}

/* 5. B-1/B-2 are not presented as ordinary long-term ARC/extension statuses */
{
  const bad = [];
  for (const c of ['B-1', 'B-2']) {
    const sum = regSummary(c);
    // must be the scoped short-stay notice, not the long-stay surfacing template
    if (sum.includes('90일을 초과해 체류하는 경우, 입국일로부터 90일 이내')) bad.push(`${c}:long-stay-template`);
    if (!sum.includes('원칙적으로 외국인등록 대상이 아닙니다')) bad.push(`${c}:missing-scoped-notice`);
    // must not invent employment/ARC checklists
    const t = allProcText(byCode.get(c));
    for (const id of EMPLOYMENT_DOC_IDS) if (t.includes(id)) bad.push(`${c}:${id}`);
  }
  check('5. B-1/B-2 stay scoped (not ordinary long-term registration)', bad.length === 0, bad.join(', '));
}

/* 6. C-1/C-4 are not confused with C-3 or E-series employment statuses */
{
  const bad = [];
  // distinct names from C-3 and from each other
  const names = { 'C-1': name('C-1'), 'C-3': name('C-3'), 'C-4': name('C-4') };
  if (!names['C-1'] || !names['C-4']) bad.push('missing-name');
  if (names['C-1'] === names['C-3'] || names['C-4'] === names['C-3'] || names['C-1'] === names['C-4']) bad.push('name-collision');
  // C-4 (단기취업) must stay short-term scoped — not surfaced as E-series long-term registration
  const c4reg = regSummary('C-4');
  if (!c4reg.includes('원칙적으로 외국인등록 대상이 아닙니다')) bad.push('C-4:not-scoped');
  // C-4 must not be reframed as E-series employment registration
  if (c4reg.includes('90일을 초과해 체류하는 경우, 입국일로부터 90일 이내')) bad.push('C-4:long-stay-template');
  check('6. C-1/C-4 are distinct from C-3 and not E-series employment', bad.length === 0,
    `${JSON.stringify(names)} ${bad.join(', ')}`);
}

/* 7. D-series remaining statuses preserve distinct purpose labels */
{
  const dNames = LONGSTAY_D.map(name);
  const distinct = new Set(dNames).size === dNames.length && dNames.every(Boolean);
  // sanity: known purposes present
  const purposes = name('D-1').includes('문화') && name('D-3').includes('연수')
    && name('D-5').includes('취재') && name('D-6').includes('종교')
    && name('D-7').includes('주재') && name('D-8').includes('투자') && name('D-9').includes('무역');
  check('7. D-series remaining statuses keep distinct purpose names', distinct && purposes,
    dNames.join(' / '));
}

/* 8. D-7/D-8/D-9 are not collapsed into one generic business/investment notice */
{
  const bad = [];
  // each registration summary must name its own status/code (distinct surfacing)
  for (const c of ['D-7', 'D-8']) {
    if (!regSummary(c).includes(`(${c})`)) bad.push(`${c}:reg-not-self-labelled`);
  }
  // D-9 keeps its own real source-backed registration summary (embedded docs)
  const d9reg = regSummary('D-9');
  const d9HasOwn = d9reg.includes('외국인등록') && d9reg.includes('제출서류');
  if (!d9HasOwn) bad.push('D-9:lost-own-summary');
  // the three must not share an identical registration summary
  const sums = new Set(['D-7', 'D-8', 'D-9'].map(regSummary));
  if (sums.size !== 3) bad.push('D-7/D-8/D-9:identical-reg-summary');
  check('8. D-7/D-8/D-9 are not collapsed into generic guidance', bad.length === 0, bad.join(', '));
}

/* 9. E-3/E-4/E-5/E-10 preserve distinct employment/professional/vessel context */
{
  const eNames = ['E-3', 'E-4', 'E-5', 'E-10'].map(name);
  const distinct = new Set(eNames).size === eNames.length && eNames.every(Boolean);
  const purposes = name('E-3').includes('연구') && name('E-4').includes('기술')
    && name('E-5').includes('전문') && name('E-10').includes('선원');
  check('9. E-3/E-4/E-5/E-10 keep distinct employment/professional/vessel names',
    distinct && purposes, eNames.join(' / '));
}

/* 10. E-10 is not confused with E-7 or E-9 */
{
  const e10 = name('E-10');
  const ok = e10 && e10 !== name('E-7') && e10 !== name('E-9') && e10.includes('선원');
  check('10. E-10 (선원취업) is not confused with E-7 or E-9', ok,
    `E-10=${e10} E-7=${name('E-7')} E-9=${name('E-9')}`);
}

/* 11. Long-stay registration tabs are surfaced (available) and source-limited */
{
  const bad = [];
  for (const c of ['D-1', 'D-3', 'D-5', 'D-6', 'D-7', 'D-8', 'E-3', 'E-4', 'E-5', 'E-10']) {
    const reg = (byCode.get(c).procedures || {}).registration || {};
    if (reg.available !== true) bad.push(`${c}:not-available`);
    if (!String(reg.summary || '').includes('외국인등록')) bad.push(`${c}:no-registration-notice`);
  }
  check('11. long-stay registration tabs are surfaced and source-limited', bad.length === 0, bad.join(', '));
}

/* 12. Short-stay registration tabs do not list invented documents */
{
  const bad = [];
  for (const c of SHORTSTAY) {
    const reg = (byCode.get(c).procedures || {}).registration || {};
    const rd = reg.requiredDocs || {};
    const total = []
      .concat(rd.commonDocs || [], rd.requiredDocs || [], rd.additionalDocs || [], rd.conditionalDocs || []);
    if (total.length > 0) bad.push(`${c}:${total.length}-invented-docs`);
  }
  check('12. short-stay registration tabs list no invented documents', bad.length === 0, bad.join(', '));
}

/* 13. Extension tabs carry a next-action hint */
{
  const bad = [];
  for (const c of TARGETS) {
    const ext = (byCode.get(c).procedures || {}).extension;
    if (!ext) continue;
    const notes = Array.isArray(ext.notes) ? ext.notes.join('\n') : '';
    if (!notes.includes('다음 단계')) bad.push(c);
  }
  check('13. extension tabs carry a next-action hint', bad.length === 0, bad.join(', '));
}

/* 14. Source-backed extension documents were preserved (not flattened away) */
{
  // D-7/D-8/E-3 had real source-backed extension doc lists; they must survive.
  const bad = [];
  for (const c of ['D-7', 'D-8', 'E-3']) {
    const rd = ((byCode.get(c).procedures || {}).extension || {}).requiredDocs || {};
    const total = []
      .concat(rd.commonDocs || [], rd.requiredDocs || [], rd.additionalDocs || [], rd.conditionalDocs || []);
    if (total.length < 3) bad.push(`${c}:${total.length}`);
    // the official application form must remain
    if (!JSON.stringify(rd).includes('통합신청서') && !JSON.stringify(rd).includes('신청서')) {
      bad.push(`${c}:no-form`);
    }
  }
  check('14. source-backed extension documents preserved', bad.length === 0, bad.join(', '));
}

/* 15. Existing D-2 golden path checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_d2_student_journey.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('15. D-2 golden path checks still pass', ok);
}

/* 16. Existing expanded priority status checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_priority_status_journeys.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('16. expanded priority status checks still pass', ok);
}

/* 17. Existing exact-code search QA checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_exact_code_search.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('17. exact-code search QA checks still pass', ok);
}

/* 18. Existing all-status audit still runs and includes targets */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const r = audit.runAudit();
    const seen = new Set(r.records.map((x) => x.statusCode));
    ok = seen.has('D-2') && seen.has('E-3') && seen.has('B-1');
  } catch (e) { ok = false; }
  check('18. all-status audit still runs and includes targets', ok);
}

/* 19. Existing static visa result card checks still pass */
{
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', 'check_static_visa_result_cards.js')], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check('19. static visa result card checks still pass', ok);
}

/* ---- report ---- */
console.log('Remaining status-journey checks:');
for (const n of passed) console.log('  PASS ' + n);
for (const n of failures) console.log('  FAIL ' + n);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
