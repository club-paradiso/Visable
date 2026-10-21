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

const savedFetch = globalThis.fetch;
const savedEnv = {
  LAW_API_OC: process.env.LAW_API_OC,
  LAW_GROUNDING_MODE: process.env.LAW_GROUNDING_MODE,
};
try {
  process.env.LAW_API_OC = 'SYNTHETIC_NON_SECRET_TEST';
  process.env.LAW_GROUNDING_MODE = 'enabled';
  globalThis.fetch = async (url) => {
    const u = new URL(url);
    const isSearch = u.pathname.includes('lawSearch');
    const isAct = isSearch ? u.searchParams.get('query') === '출입국관리법'
      : u.searchParams.get('MST') === 'TEST-ACT';
    const payload = isSearch
      ? { law: [{ 법령명한글: isAct ? '출입국관리법' : '출입국관리법 시행규칙',
                  법령일련번호: isAct ? 'TEST-ACT' : 'TEST-RULE',
                  시행일자: isAct ? '20260101' : '20260123' }] }
      : isAct
        ? { 조문: [{ 조문번호: '20', 조문제목: '체류자격 외 활동', 조문내용: '공식 원문 모의자료' }] }
        : { 조문: [{ 조문번호: '86', 조문제목: '범칙금', 조문내용: '공식 원문 모의자료' }],
            별표: [{ 별표번호: '7', 별표제목: '범칙금 양정기준', 별표내용: '범칙금 모의자료' }] };
    return { ok: true, text: async () => JSON.stringify(payload) };
  };
  const baseline = { status: 'AVAILABLE' };
  const current = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-02-01', violationEndDate: '2026-02-20',
  }, baseline);
  assert.equal(current.temporalVerification.status, 'CONFIRMED');
  assert.equal(current.status, 'VERIFIED');
  const historical = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
    violationStartDate: '2026-01-01', violationEndDate: '2026-01-20',
  }, baseline);
  assert.equal(historical.temporalVerification.code, 'historical_version_required');
  assert.equal(historical.status, 'LIMITED');
  const missingDates = await source.groundOfficialLaw({
    violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20', durationDays: 18,
  }, baseline);
  assert.equal(missingDates.temporalVerification.code, 'violation_dates_required');
  assert.equal(missingDates.status, 'LIMITED');
} finally {
  globalThis.fetch = savedFetch;
  for (const [key, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}
console.log('Official law temporal evidence checks passed');
