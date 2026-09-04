import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'enforcement.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'scripts/enforcement-ui.mjs'), 'utf8');
const confirm = fs.readFileSync(path.join(root, 'api/enforcement/confirm.js'), 'utf8');

assert.ok(html.includes('id="assessment-date"'), 'assessment date input must remain present');
assert.ok(js.includes('function localTodayIso()'), 'local today helper must exist');
assert.ok(js.includes('setAssessmentDateToday();'), 'assessment date must initialize to today');
assert.ok(js.includes("setAssessmentDateToday({ force: true })"), 'restart must restore today');
assert.ok(js.includes('function resolveAssessmentDate()'), 'assessment date resolver must exist');
assert.ok(
  !js.includes("$('#assessment-date').value ||"),
  'assessment date must go through the validated resolver, not a raw field read',
);
assert.ok(
  js.includes('assessmentDate: resolveAssessmentDate()') && js.includes('assessmentDate: resolveAssessmentDate() }'),
  'extract and analyze paths must both normalize the assessment date',
);
assert.ok(js.includes('input.max = localTodayIso();'), 'assessment date must be bounded to today');
assert.ok(html.includes('id="assessment-date-today"'), 'a reset-to-today control must exist');
assert.ok(
  html.includes('기본값은 오늘') || html.includes('오늘 날짜가 기본값으로 채워집니다'),
  'the today default must be explained to the user',
);
assert.ok(js.includes('분석 기준일:'), 'the applied assessment date must be visible in the result');
assert.ok(html.includes('data-example='), 'quick-fill examples must exist for natural-language input');
assert.ok(js.includes("$$('[data-example]')"), 'quick-fill examples must be wired');
assert.ok(js.includes('extractionWarnings'), 'fallback extraction warnings must remain visible');
assert.ok(js.includes('확인이 필요한 해석'), 'confirmation details must explain extraction fallbacks');
assert.ok(js.includes("'case text is required': '사례 설명을 입력해 주세요.'"), 'backend validation errors must be localized');

assert.ok(html.includes('제가 이해한 내용이 맞나요?'), 'confirmation must ask a plain-language question');
assert.ok(html.includes('일부 내용이 달라요'), 'users must have an obvious way to correct the interpretation');
assert.ok(html.includes('네, 맞아요 · 분석하기'), 'users must explicitly confirm before analysis');
assert.ok(!html.includes('name="violationCode"'), 'internal violation code must not be exposed as an edit field');
assert.ok(!html.includes('name="authorizationObtained"'), 'internal boolean fields must not be exposed as bureaucratic controls');
assert.ok(js.includes('function deterministicSummary('), 'a zero-latency deterministic confirmation fallback must exist');
assert.ok(js.includes('function clarificationFor('), 'material missing facts must be asked conversationally');
assert.ok(js.includes('primary.disabled = Boolean(question)'), 'analysis must wait for a material clarification or explicit skip');
assert.ok(js.includes('잘 모르겠어요'), 'users must be allowed to keep genuinely unknown facts unknown');
assert.ok(js.includes('detectLocale(text)'), 'confirmation humanizer must receive a user-language hint');
assert.ok(js.includes('void humanizeConfirmation(structuredCase)'), 'Gemma polishing must never block the confirmation screen');
assert.ok(confirm.includes('Do not invent or infer missing facts'), 'humanizer must not add facts');
assert.ok(confirm.includes('Do not give legal advice'), 'humanizer must not perform legal analysis');
assert.ok(confirm.includes('payload.caseData') && !confirm.includes('payload.text'), 'humanizer must receive structured facts rather than raw narrative');

console.log('Enforcement natural-language/date UX contract passed.');
