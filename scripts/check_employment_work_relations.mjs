#!/usr/bin/env node
// Cross-occupation relation tests. No model needed; both local and AI-backed
// searches must respect the subject/object distinction in the original text.
import assert from 'node:assert/strict';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';
import { inferEmploymentRelation } from './employment_work_relations.mjs';

const deps = loadEmploymentAnalyzerDeps();
const az = createEmploymentAnalyzer(deps);
const lex = Object.values(deps.lexicon).flatMap((v) => v.concepts || []);
const names = lex.filter((c) => c.type === 'role').flatMap((c) => c.surface || []);
const tests = [
  { q: '제주특별자치도 교육청에서 영어 보조교사를 관리하는 일을 하고있어요',
    kind: 'managed_staff', target: '보조교사', job: '인사 및 노무 사무원', industry: '교육 행정', no: '보육교사', question: true },
  { q: '교육지원청에서 원어민 교사 인사 채용 배치를 담당합니다',
    kind: 'managed_staff', target: '교사', job: '인사 및 노무 사무원', no: '보육교사' },
  { q: '병원에서 간호사들을 채용하고 인사 업무를 해요',
    kind: 'managed_staff', target: '간호사', job: '인사 및 노무 사무원', no: '간호사' },
  { q: 'IT 회사에서 개발자들 근태를 관리합니다',
    kind: 'managed_staff', target: '개발자', job: '인사 및 노무 사무원', no: '개발자' },
  { q: '음식점에서 요리사들의 스케줄을 관리해요',
    kind: 'managed_staff', target: '요리사', job: '총무 사무원 및 대학 행정조교', no: '요리사' },
  { q: '호텔에서 청소원 인력 채용을 맡고 있습니다',
    kind: 'managed_staff', target: '청소원', job: '인사 및 노무 사무원', no: '청소원' },
  { q: 'I recruit nurses at a hospital',
    kind: 'managed_staff', target: 'nurse', job: '인사 및 노무 사무원', no: '간호사' },
  { q: 'I manage teachers in a school',
    kind: 'managed_staff', target: 'teacher', job: '인사 및 노무 사무원', no: '교사' },
  { q: '저는 간호사로 근무하면서 간호사들을 교육해요', kind: 'mixed' },
  { q: 'I am a nurse and I train nurses', kind: 'mixed' },
  { q: '어린이집에서 보육교사로 일해요', kind: null },
  { q: '학교에서 보조교사로 근무해요', kind: null },
  { q: 'I work as an English teacher at school', kind: null },
  { q: '자동차를 관리하는 정비사입니다', kind: null },
  { q: '컴퓨터 서버와 전산 시스템을 관리해요', kind: null },
  { q: '병원에서 간호사는 아니고 전산 일을 해요', kind: null }
];

let passed = 0;
for (const t of tests) {
  const relation = inferEmploymentRelation(t.q, names);
  assert.equal(relation?.kind || null, t.kind, `relation: ${t.q}`);
  if (t.target) assert.ok(relation.target.includes(t.target), `target: ${t.q} → ${relation.target}`);
  const a = az.analyze({ text: t.q, locale: /[가-힣]/.test(t.q) ? 'ko' : 'en' });
  assert.equal(a.managedStaff, t.kind === 'managed_staff', `managed flag: ${t.q}`);
  if (t.kind === 'managed_staff') {
    assert.ok(a.occupationCandidates.some((c) => c.officialName === t.job),
      `expected ${t.job}, got ${a.occupationCandidates.map((c) => c.officialName).join(', ')}`);
    if (t.no) assert.ok(a.occupationCandidates.every((c) => c.officialName !== t.no),
      `task target leaked into occupation: ${t.q}`);
    assert.ok(a.occupationCandidates.every((c) => c.confidence !== 'high'),
      `uncertain staffing role must not display high confidence: ${t.q}`);
    if (t.industry) assert.ok(a.industryCandidates.some((c) => c.officialName === t.industry),
      `expected industry ${t.industry}, got ${a.industryCandidates.map((c) => c.officialName).join(', ')}`);
    if (t.question) assert.ok(a.ambiguityQuestions.some((q) => q.flag === 'managed_staff_duties'));
  }
  passed++;
}
// A profession alone is NOT evidence of the employer's business when the job
// is coordinating staff. Avoid reporting "hospital" for a recruiter at an agency.
const unknown = az.analyze('간호사들을 채용합니다');
assert.equal(unknown.managedStaff, true);
assert.equal(unknown.industryCandidates.length, 0);
assert.ok(unknown.ambiguityQuestions.some((q) => q.flag === 'unknown_employer_industry'));

// Externally provided AI facts must not turn the object (nurses) into our job.
const polluted = az.analyze({ text: '병원에서 간호사들을 채용해요',
  facts: { role: '간호사', tasks: ['간호 업무', '간호사 채용'], employerMainBusiness: '병원' } });
assert.equal(polluted.managedStaff, true);
assert.ok(polluted.occupationCandidates.every((c) => c.officialName !== '간호사'));

console.log(`Employment role/target separation: ${passed + 2} cases passed.`);
