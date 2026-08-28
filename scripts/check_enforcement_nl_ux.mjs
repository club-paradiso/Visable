import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'enforcement.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'scripts/enforcement-ui.mjs'), 'utf8');

assert.ok(html.includes('id="assessment-date"'), 'assessment date input must remain present');
assert.ok(js.includes('function localTodayIso()'), 'local today helper must exist');
assert.ok(js.includes('setAssessmentDateToday();'), 'assessment date must initialize to today');
assert.ok(js.includes("setAssessmentDateToday({ force: true })"), 'restart must restore today');
assert.ok(js.includes('function resolveAssessmentDate()'), 'assessment date resolver must exist');
assert.ok(
  !js.includes("$('#assessment-date').value ||"),
  'assessment date must go through the validated resolver, not a raw field read',
);
assert.equal(
  js.split('assessmentDate: resolveAssessmentDate()').length - 1,
  2,
  'both extract and analyze requests must carry a validated assessment date',
);
assert.ok(js.includes('input.max = localTodayIso();'), 'assessment date must be bounded to today');
assert.ok(html.includes('id="assessment-date-today"'), 'a reset-to-today control must exist');
assert.ok(html.includes('오늘 날짜가 기본값으로 채워집니다'), 'the today default must be explained to the user');
assert.ok(js.includes('분석 기준일:'), 'the applied assessment date must be visible in the result');
assert.ok(html.includes('data-example='), 'quick-fill examples must exist for natural-language input');
assert.ok(js.includes("$$('[data-example]')"), 'quick-fill examples must be wired');
assert.ok(js.includes('extractionWarnings'), 'fallback extraction warnings must be visible in confirmation UI');
assert.ok(js.includes('구조화 확인 메모'), 'confirmation UI must explain extraction fallbacks');
assert.ok(js.includes("'case text is required': '사례 설명을 입력해 주세요.'"), 'backend validation errors must be localized');

console.log('Enforcement natural-language/date UX contract passed.');
