import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { extractStructuredCaseV2 } = require('../lib/enforcement-grounded-ai.js');

const ASSESSMENT_DATE = '2026-08-28';
const AMBIGUOUS_WORK_CODES = [
  'UNAUTHORIZED_STAY_OR_WORK_ART18_1',
  'STATUS_OUTSIDE_ACTIVITY_ART20',
  'UNAUTHORIZED_EMPLOYMENT_ART18_2',
  'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
];

// Colloquial Korean phrasings that the same-origin JS fallback must handle the
// same way the Python service does. Each expectation asserts only facts the
// text itself establishes; anything ambiguous must stay unresolved.
const cases = [
  {
    name: 'two-digit status code is recognised and normalised',
    text: 'E-10 선원인데 허가 없이 다른 공장에서 일했어요',
    expect: { statusOfStay: 'E-10', violationCode: null, violationCandidates: AMBIGUOUS_WORK_CODES },
  },
  {
    name: 'subcode status, composite duration and workplace change',
    text: 'E-7-4 비자인데 근무처 변경 허가를 안 받고 2개월 3일 동안 다른 회사에서 일했습니다',
    expect: {
      statusOfStay: 'E-7-4',
      violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
      durationDays: 63,
      workplaceChangeAuthorized: false,
    },
  },
  {
    name: 'expiry wording, word-count duration, first offence and voluntary visit',
    text: 'D-10 구직비자인데 체류기간 만료 후 엿새 지났어요. 이번이 처음이고 스스로 출입국관서에 자진 방문했습니다',
    expect: {
      statusOfStay: 'D-10',
      violationCode: 'OVERSTAY_ART25',
      durationDays: 6,
      priorViolations: 0,
      voluntaryDisclosure: true,
    },
  },
  {
    name: 'explicit date range wins over stray duration tokens',
    text: '2026년 3월 1일부터 4월 10일까지 허가 없이 아르바이트를 했습니다. D-2 학생입니다',
    expect: {
      statusOfStay: 'D-2',
      violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
      violationStartDate: '2026-03-01',
      violationEndDate: '2026-04-10',
      durationDays: 41,
    },
  },
  {
    name: 'word duration and first-violation wording',
    text: 'D-2인데 한 달 동안 음식점에서 불법 취업했어요. 첫 위반입니다',
    expect: {
      statusOfStay: 'D-2',
      violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
      durationDays: 30,
      priorViolations: 0,
    },
  },
  {
    name: 'relative dates resolve against the assessment date',
    text: 'F-2 인데 어제부터 오늘까지 오버스테이 상태입니다',
    expect: {
      statusOfStay: 'F-2',
      violationCode: 'OVERSTAY_ART25',
      violationStartDate: '2026-08-27',
      violationEndDate: '2026-08-28',
      durationDays: 2,
    },
  },
];

for (const { name, text, expect } of cases) {
  const result = extractStructuredCaseV2(text, ASSESSMENT_DATE);
  for (const [key, value] of Object.entries(expect)) {
    assert.deepEqual(result[key] ?? null, value, `${name}: ${key}`);
  }
  assert.equal(result.assessmentDate, ASSESSMENT_DATE, `${name}: assessment date is preserved`);
}

// A four-digit year must never be read as a duration in years.
const dated = extractStructuredCaseV2('2026년 3월 1일부터 허가 없이 일했습니다', ASSESSMENT_DATE);
assert.ok(
  dated.durationDays == null || dated.durationDays < 3650,
  'calendar years must not be parsed as a violation duration',
);

// Unresolved facts must stay visible rather than being guessed.
const sparse = extractStructuredCaseV2('허가 없이 일했어요', ASSESSMENT_DATE);
assert.equal(sparse.violationCode ?? null, null, 'ambiguous text must not resolve to a provision');
assert.ok(sparse.unknownFacts.includes('체류자격'), 'missing status must be reported as unknown');
assert.ok(sparse.unknownFacts.includes('위반기간'), 'missing duration must be reported as unknown');

console.log(`Enforcement extraction quality passed (${cases.length} colloquial cases).`);
