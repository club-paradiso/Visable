import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';
import { interpretEmploymentInput } from './employment_interpret_client.mjs';

const root = new URL('../', import.meta.url);
new Function(fs.readFileSync(new URL('assets/js/status-guidance.js', root), 'utf8'))();
new Function(fs.readFileSync(new URL('assets/js/search-router.js', root), 'utf8'))();
const bundle = JSON.parse(fs.readFileSync(new URL('data/status-guidance-202609.json', root)));
const SG = globalThis.VisableStatusGuidance;
for (const [query, status, procedure] of [
  ['D-2가 아니라 D-10인데 연장하려면?', 'D-10', 'extension'],
  ['Not D-2 but D-10, extension documents?', 'D-10', 'extension'],
  ['등록증 재발급 말고 체류기간 연장 서류', null, 'extension'],
  ['등록증을 처음 신청하고 싶어요', null, 'registration'],
  ['여권을 대사관에서 갱신하려면?', null, null],
]) {
  const result = SG.interpret(query, bundle);
  assert.equal(result.codes[0]?.code ?? null, status, query);
  assert.equal(result.procedure, procedure, query);
}
const unknown = SG.interpret('F-10 연장 서류', bundle);
assert.deepEqual(unknown.codes, []);
assert.deepEqual(unknown.unknownCodes, ['F-10']);
assert.equal(SG.normalizeCode('E74', bundle.codes), 'E-7-4');
const transition = SG.interpret('D-10으로 바꾸려는데 지금은 D-2예요', bundle);
assert.equal(transition.codes[0].code, 'D-10');
assert.equal(transition.transitionFrom, 'D-2');
const multi = SG.interpret('D-2 연장하고 주소 변경도 하려면?', bundle);
assert.deepEqual(multi.procedureCandidates, ['extension', 'residence_report']);
assert.equal(SG.nextStep({ interp: multi, answers: {}, lang: 'ko' }, bundle).dimension, '__procedure');

const analyzer = createEmploymentAnalyzer(loadEmploymentAnalyzerDeps());
for (const [text, expected, denied] of [
  ['병원에서 전산 시스템을 관리해요. 간호사는 아니에요', '정보 시스템 운영자', /간호/],
  ['I build websites for a hospital, not a doctor', '웹 개발자', /의사/],
  ['식당에서 회계만 해요. 조리사는 아니에요', '회계 사무원', /조리사|회계사|세무사/],
]) {
  const result = analyzer.analyze({ text });
  assert.equal(result.occupationCandidates[0].officialName, expected, text);
  assert.ok(!denied.test(result.occupationCandidates[0].officialName), text);
}
const dispatched = analyzer.analyze({ text: '호텔 소속은 아니고 인력회사에서 보내줘서 객실 청소해요' });
assert.ok(dispatched.clarificationQuestion.includes('고용한 회사'));
assert.ok(dispatched.industryCandidates.every((c) => c.confidence === 'low'));
const misleadingAI = analyzer.analyze({ text: '병원 전산 담당이고 간호사는 아니에요', facts: { role: '간호사', tasks: ['전산 시스템 관리'] } });
assert.equal(misleadingAI.occupationCandidates[0].officialName, '정보 시스템 운영자');
const translated = analyzer.analyze({ text: 'Tôi hái quýt ở trang trại', facts: { role: '귤 수확', tasks: ['귤 따요'], workplace: '농장' } });
assert.ok(translated.occupationCandidates.some((c) => /농업|과수|채소/.test(c.officialName)));
assert.ok(!analyzer.analyze({ text: 'Tôi hái quýt ở trang trại' }).clarificationQuestion.includes('너무 짧'));

let called = '';
const facts = await interpretEmploymentInput({ text: '병원 전산 담당', apiBase: 'https://backend.invalid', fetchImpl: async (url, options) => {
  called = url; assert.equal(JSON.parse(options.body).text, '병원 전산 담당');
  return { ok: true, json: async () => ({ status: 'ok', extraction: { role: '전산 담당', code: '12345', tasks: ['시스템 관리'] } }) };
} });
assert.ok(called.endsWith('/api/employment/interpret'));
assert.equal(facts.role, '전산 담당');
assert.equal(facts.code, undefined);
assert.equal(await interpretEmploymentInput({ text: 'test', apiBase: 'https://backend.invalid', fetchImpl: async () => ({ ok: true, json: async () => ({ status: 'unavailable', reason: 'rate_limited' }) }) }), null);
assert.equal(await interpretEmploymentInput({ text: 'test', apiBase: 'https://backend.invalid', timeoutMs: 10, fetchImpl: async () => new Promise(() => {}) }), null);
console.log('Question understanding: status/procedure relationships, job polarity, employer ambiguity and bounded AI fallback passed.');
