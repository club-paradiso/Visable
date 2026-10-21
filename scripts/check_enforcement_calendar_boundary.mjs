import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { calculateLegalBaseline } = require('../lib/enforcement-fallback.js');

const sample = (updates = {}) => ({
  statusOfStay: 'D-2',
  violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
  violationCandidates: ['STATUS_OUTSIDE_ACTIVITY_ART20'],
  durationDays: 18,
  authorizationObtained: false,
  assessmentDate: '2026-10-21',
  priorViolations: 0,
  ...updates,
});

const short = calculateLegalBaseline(sample());
assert.equal(short.status, 'AVAILABLE');
assert.equal(short.baselineAmountKrw, 2_000_000);

const uncertain = calculateLegalBaseline(sample({ durationDays: 30 }));
assert.equal(uncertain.status, 'MISSING_FACTS');
assert.equal(uncertain.baselineAmountKrw, undefined);
assert.ok(uncertain.missingFacts.some((fact) => fact.includes('시작일')));

// Same inclusive duration, different calendar-month tier: exact dates matter.
const before = calculateLegalBaseline(sample({
  durationDays: 30, violationStartDate: '2026-01-01', violationEndDate: '2026-01-30',
}));
const after = calculateLegalBaseline(sample({
  durationDays: 30, violationStartDate: '2026-02-01', violationEndDate: '2026-03-02',
}));
assert.equal(before.status, 'AVAILABLE');
assert.equal(after.status, 'AVAILABLE');
assert.equal(before.baselineAmountKrw, 2_000_000);
assert.equal(after.baselineAmountKrw, 3_000_000);

// Non-boundary duration remains usable, including unrelated 3-month tiers.
const certain = calculateLegalBaseline(sample({ durationDays: 33 }));
assert.equal(certain.status, 'AVAILABLE');
assert.equal(certain.baselineAmountKrw, 3_000_000);
const workplace = calculateLegalBaseline(sample({
  violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', durationDays: 30,
}));
assert.equal(workplace.status, 'AVAILABLE');
assert.equal(workplace.baselineAmountKrw, 1_000_000);
console.log('enforcement calendar boundary checks passed');
