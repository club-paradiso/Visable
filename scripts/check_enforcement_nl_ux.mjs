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
assert.ok(
  js.includes("assessmentDate: $('#assessment-date').value || localTodayIso()"),
  'extract requests must always carry a concrete assessment date',
);
assert.ok(js.includes('extractionWarnings'), 'fallback extraction warnings must be visible in confirmation UI');
assert.ok(js.includes('구조화 확인 메모'), 'confirmation UI must explain extraction fallbacks');
assert.ok(js.includes("'case text is required': '사례 설명을 입력해 주세요.'"), 'backend validation errors must be localized');

console.log('Enforcement natural-language/date UX contract passed.');
