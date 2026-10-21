import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { assessTemporalLawEvidence, dateIso } = require('../lib/enforcement-law-validity.js');

assert.equal(dateIso('20260123'), '2026-01-23');
assert.equal(dateIso('2026-2-3'), '2026-02-03');
assert.equal(dateIso('2026-02-30'), null);
assert.equal(dateIso('bogus'), null);

const dateCase = { violationStartDate: '2026-02-01', violationEndDate: '2026-02-20' };
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '2026-01-23').verified, true);
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '2026-02-15').code, 'historical_version_required');
assert.equal(assessTemporalLawEvidence(dateCase, '2026-01-01', '').code, 'effective_dates_unavailable');
assert.equal(assessTemporalLawEvidence({ durationDays: 18, assessmentDate: '2026-10-21' },
  '2026-01-01', '2026-01-23').code, 'violation_dates_required');
assert.equal(assessTemporalLawEvidence({ violationStartDate: '2026-02-20', violationEndDate: '2026-02-01' },
  '2026-01-01', '2026-01-23').verified, false);

const source = require('../lib/enforcement-law-grounding.js');
assert.equal(typeof source.groundOfficialLaw, 'function');
console.log('Official law temporal evidence checks passed');
