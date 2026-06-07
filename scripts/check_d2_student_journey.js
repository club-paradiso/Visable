#!/usr/bin/env node
/*
 * Static checks for the D-2 student-journey golden path.
 *
 * These assert that the cleaned D-2 record exposes clear, non-duplicated,
 * non-placeholder procedure sections for the four journeys a real
 * international student walks through:
 *   1. 사증발급        (visaIssuance)        — pre-entry / overseas
 *   2. 외국인등록      (registration)         — post-entry / domestic
 *   3. 체류기간 연장   (extension)            — post-entry / domestic
 *   4. 자격외활동/시간제취업 (activitiesOutsideStatus) — part-time work permission
 *
 * Failures here are real invariant breaks (non-zero exit), unlike the
 * all-status audit which only warns.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const VISA_DATA = path.join(ROOT, 'visa_data.json');

const failures = [];
const passed = [];
function check(name, condition, detail) {
  if (condition) passed.push(name);
  else failures.push(name + (detail ? ' — ' + detail : ''));
}

const visas = JSON.parse(fs.readFileSync(VISA_DATA, 'utf8'));
const d2 = visas.find((r) => r && r.code === 'D-2');

const PLACEHOLDERS = ['문서명 미상', '비고 정보 없음', 'DATA_MISSING'];
const DIAGNOSTICS = [
  'bad_response', 'unsupported', 'not_attempted',
  'source_family_statuses', 'law_grounding_warnings', 'grounding_used',
];
const TARGET_KEYS = ['visaIssuance', 'registration', 'extension', 'activitiesOutsideStatus'];

function flattenGroups(rd) {
  if (!rd) return [];
  if (Array.isArray(rd)) return rd.slice();
  return []
    .concat(rd.commonDocs || [])
    .concat(rd.requiredDocs || [])
    .concat(rd.additionalDocs || [])
    .concat(rd.conditionalDocs || []);
}

function sectionText(proc) {
  return JSON.stringify(proc || {});
}

if (!d2) {
  console.error('[check_d2_student_journey] D-2 record not found in visa_data.json');
  process.exit(1);
}
const procs = d2.procedures || {};

/* 1. D-2 has structured procedure sections for all four journeys */
check('1. D-2 has all four procedure sections present and available',
  TARGET_KEYS.every((k) => {
    const p = procs[k];
    if (!p || p.available !== true) return false;
    const hasContent = (typeof p.summary === 'string' && p.summary.trim())
      || flattenGroups(p.requiredDocs).length > 0
      || (Array.isArray(p.eligibility) && p.eligibility.length > 0)
      || (Array.isArray(p.notes) && p.notes.length > 0);
    return hasContent;
  }),
  'each of visaIssuance/registration/extension/activitiesOutsideStatus must be available with content');

/* 2. visa issuance labeled pre-entry / overseas */
{
  const s = String(procs.visaIssuance && procs.visaIssuance.summary || '');
  check('2. D-2 visa issuance labeled pre-entry / overseas',
    s.includes('입국 전') && s.includes('재외공관'),
    'visaIssuance summary must mark pre-entry/overseas (입국 전 · 재외공관)');
}

/* 3. registration labeled post-entry / domestic */
{
  const s = String(procs.registration && procs.registration.summary || '');
  check('3. D-2 registration labeled post-entry / domestic stay',
    s.includes('입국 후') && s.includes('외국인등록'),
    'registration summary must mark post-entry/domestic (입국 후 · 외국인등록)');
}

/* 4. registration does not duplicate the same document or fee block */
{
  const docs = flattenGroups(procs.registration && procs.registration.requiredDocs)
    .map((d) => String(d).trim()).filter(Boolean);
  const uniqueDocs = new Set(docs);
  const docsUnique = uniqueDocs.size === docs.length;

  // fee blocks: registration maps to feeInfo.*.procedures.foreignRegistration
  const feeDisplays = [];
  const feeBlocks = d2.feeInfo || {};
  for (const block of Object.values(feeBlocks)) {
    const entry = block && block.procedures && block.procedures.foreignRegistration;
    if (entry && Array.isArray(entry.items)) {
      for (const it of entry.items) if (it && it.display) feeDisplays.push(String(it.display).trim());
    }
  }
  const feeUnique = new Set(feeDisplays).size === feeDisplays.length;
  check('4. D-2 registration has no duplicate document or fee blocks',
    docsUnique && feeUnique,
    `docsUnique=${docsUnique} feeUnique=${feeUnique}`);
}

/* 5. extension separates common and conditional documents */
{
  const rd = (procs.extension && procs.extension.requiredDocs) || {};
  check('5. D-2 extension separates common and conditional documents',
    Array.isArray(rd.commonDocs) && rd.commonDocs.length > 0
      && Array.isArray(rd.conditionalDocs) && rd.conditionalDocs.length > 0,
    'extension must populate both commonDocs and conditionalDocs');
}

/* 6. part-time work section is not confused with registration/extension */
{
  const p = procs.activitiesOutsideStatus || {};
  const s = String(p.summary || '');
  const mentionsPartTime = s.includes('자격외활동') || s.includes('시간제취업');
  // Must not be framed as the registration/extension procedure.
  const notRegistrationFramed = !s.includes('외국인등록') && !s.includes('체류기간 연장');
  check('6. D-2 part-time work section is distinct from registration/extension',
    mentionsPartTime && notRegistrationFramed,
    `mentionsPartTime=${mentionsPartTime} notRegistrationFramed=${notRegistrationFramed}`);
}

/* 7. 통합신청서 / 별지 제34호 preserved in registration */
{
  const docs = flattenGroups(procs.registration && procs.registration.requiredDocs).map(String);
  const hasUnified = docs.some((d) => d.includes('통합신청서') && d.includes('별지 제34호'));
  check('7. 통합신청서(별지 제34호 서식) preserved in D-2 registration',
    hasUnified,
    'registration must keep the official unified application form line');
}

/* 8. no user-facing placeholders in the four D-2 procedure sections */
{
  const text = TARGET_KEYS.map((k) => sectionText(procs[k])).join('\n');
  const hit = PLACEHOLDERS.filter((t) => text.includes(t));
  check('8. D-2 procedures contain no placeholder rows',
    hit.length === 0,
    'found placeholders: ' + hit.join(', '));
}

/* 9. no raw diagnostics in the four D-2 procedure sections */
{
  const text = TARGET_KEYS.map((k) => sectionText(procs[k])).join('\n');
  const hit = DIAGNOSTICS.filter((t) => text.includes(t));
  check('9. D-2 procedures contain no raw diagnostics',
    hit.length === 0,
    'found diagnostics: ' + hit.join(', '));
}

/* 10. existing all-status audit still runs and surfaces D-2 */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const result = audit.runAudit();
    ok = Array.isArray(result.records) && result.records.some((r) => r.statusCode === 'D-2');
  } catch (e) {
    ok = false;
  }
  check('10. all-status audit still runs and includes D-2', ok);
}

/* 11. existing static visa result card checks still pass */
{
  let ok = false;
  try {
    execFileSync('node', [path.join(ROOT, 'scripts', 'check_static_visa_result_cards.js')],
      { stdio: 'ignore' });
    ok = true;
  } catch (e) {
    ok = false;
  }
  check('11. static visa result card checks still pass', ok,
    'scripts/check_static_visa_result_cards.js exited non-zero');
}

/* ---- report ---- */
console.log('D-2 student-journey checks:');
for (const n of passed) console.log('  PASS ' + n);
for (const n of failures) console.log('  FAIL ' + n);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
