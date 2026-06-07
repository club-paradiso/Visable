#!/usr/bin/env node
/*
 * Static test harness for the all-status procedure journey audit.
 *
 * Unlike the audit itself (which only warns about existing data-quality
 * issues), this harness asserts invariants about the audit *machinery* and
 * fails CI (non-zero exit) when one of those expectations breaks. It does not
 * fail on the data warnings the audit surfaces.
 *
 * Usage: node scripts/check_procedure_journey_audit.js
 */
'use strict';

const audit = require('./audit_procedure_journeys.js');

const failures = [];
const passed = [];

function check(name, condition, detail) {
  if (condition) {
    passed.push(name);
  } else {
    failures.push(name + (detail ? ' — ' + detail : ''));
  }
}

// Run the audit in-memory (no file writes) once, reuse for all assertions.
const result = audit.runAudit();
const byCode = new Map(result.records.map((r) => [r.statusCode, r]));
const findProc = (code, key) => {
  const rec = byCode.get(code);
  if (!rec) return null;
  return rec.procedures.find((p) => p.procedureKey === key) || null;
};

/* 1. audit script runs successfully */
check('1. audit runs and returns a structured result',
  result && result.summary && Array.isArray(result.records) && result.records.length > 0,
  'runAudit() did not return a populated result');

/* 2. D-2 appears in audit */
check('2. D-2 appears in audit', byCode.has('D-2'));

/* 3. C-3 appears in audit */
check('3. C-3 appears in audit', byCode.has('C-3'));

/* 4. H-2 appears in audit if present in data */
{
  const visaData = require('../visa_data.json');
  const h2InData = visaData.some((r) => r && r.code === 'H-2');
  if (h2InData) {
    check('4. H-2 present in data is surfaced in audit', byCode.has('H-2'),
      'H-2 exists in visa_data.json but is missing from audit output');
  } else {
    check('4. H-2 absence is consistent', !byCode.has('H-2'),
      'H-2 not in data but appeared in audit');
  }
}

/* 5. G-1/G-1-5 handling is reported */
{
  const g1Finding = result.priorityFindings.find((p) => p.statusCode === 'G-1');
  const g15Finding = result.priorityFindings.find((p) => p.statusCode === 'G-1-5');
  check('5. G-1 and G-1-5 handling is reported in priority findings',
    Boolean(g1Finding) && Boolean(g15Finding),
    'priority findings must include both G-1 and G-1-5 entries');
}

/* 6. duplicate document detection works */
{
  const dups = audit.findDuplicates(['a', 'b', 'a', 'c', 'b']);
  check('6. duplicate document detection works',
    dups.includes('a') && dups.includes('b') && !dups.includes('c') && dups.length === 2,
    'findDuplicates returned: ' + JSON.stringify(dups));
}

/* 7. placeholder detection works */
{
  const fakeRecord = {
    code: 'F-9',
    procedures: {
      registration: {
        available: true,
        requiredDocs: { requiredDocs: ['DATA_MISSING', '문서명 미상', '신청서'] },
        manualRefs: [{ pageRange: 'p. 1' }],
      },
    },
  };
  const probe = audit.runAudit({ visaData: [fakeRecord], html: '' });
  const proc = probe.records[0].procedures.find((p) => p.procedureKey === 'registration');
  const hasPlaceholderFlag = proc.riskFlags.some((f) => f.id === 'PLACEHOLDER_TEXT');
  check('7. placeholder detection works', hasPlaceholderFlag && proc.placeholderRowCount >= 2,
    'placeholder flag not raised for synthetic DATA_MISSING/문서명 미상 rows');
}

/* 8. raw diagnostic detection works */
{
  const fakeRecord = {
    code: 'G-9',
    procedures: {
      extension: {
        available: true,
        summary: 'ok',
        requiredDocs: { requiredDocs: ['신청서'] },
        notes: ['bad_response'],
        diagnostics: ['not_attempted'],
        manualRefs: [{ pageRange: 'p. 2' }],
      },
    },
  };
  const probe = audit.runAudit({ visaData: [fakeRecord], html: '' });
  const proc = probe.records[0].procedures.find((p) => p.procedureKey === 'extension');
  const hasDiag = proc.riskFlags.some((f) => f.id === 'RAW_DIAGNOSTIC');
  check('8. raw diagnostic detection works', hasDiag && proc.diagnosticCount >= 1,
    'raw diagnostic flag not raised for synthetic bad_response/not_attempted');
}

/* 9. procedure keys are recognized consistently */
{
  const expected = [
    'visaIssuance', 'registration', 'extension', 'statusChange',
    'activitiesOutsideStatus', 'workplaceChange', 'statusGrant', 'reentry',
  ];
  const same = audit.PROCEDURE_KEYS.length === expected.length
    && expected.every((k, i) => audit.PROCEDURE_KEYS[i] === k);
  // Every audited record must report exactly these procedure keys, in order.
  const everyRecordConsistent = result.records.every((rec) =>
    rec.procedures.length === expected.length
    && rec.procedures.every((p, i) => p.procedureKey === expected[i]));
  check('9. procedure keys are recognized consistently', same && everyRecordConsistent,
    'PROCEDURE_KEYS or per-record procedure ordering drifted from the canonical list');
}

/* 10. audit output is deterministic */
{
  const a = JSON.stringify(audit.runAudit({ html: '' }));
  const b = JSON.stringify(audit.runAudit({ html: '' }));
  check('10. audit output is deterministic', a === b,
    'two runAudit() runs produced different output');
}

/* Extra sanity: priority statuses all surfaced (present flag computed). */
check('extra. all priority statuses evaluated',
  result.priorityFindings.length === audit.PRIORITY_STATUSES.length,
  'priority findings count mismatch');

/* ---- report ---- */
console.log('Procedure journey audit checks:');
for (const name of passed) console.log('  PASS ' + name);
for (const name of failures) console.log('  FAIL ' + name);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);

if (failures.length > 0) {
  process.exit(1);
}
process.exit(0);
