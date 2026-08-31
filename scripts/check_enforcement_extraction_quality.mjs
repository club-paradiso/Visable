import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const root = path.resolve(import.meta.dirname, '..');
const require = createRequire(import.meta.url);
const { extractStructuredCaseV2 } = require('../lib/enforcement-grounded-ai.js');

// Shared with backend/tests/test_enforcement_extraction_quality.py. The Python
// service is the primary extractor and this JS module is the same-origin
// fallback; running one fixture set through both keeps them from drifting, so a
// user never gets a different provision depending on which path served them.
const fixture = JSON.parse(fs.readFileSync(
  path.join(root, 'backend/tests/fixtures/enforcement_extraction_parity.json'),
  'utf8',
));
const { assessmentDate, ambiguousWorkCodes, cases } = fixture;

for (const { name, text, expect } of cases) {
  const result = extractStructuredCaseV2(text, assessmentDate);
  for (const [key, expected] of Object.entries(expect)) {
    const value = expected === 'AMBIGUOUS' ? ambiguousWorkCodes : expected;
    assert.deepEqual(result[key] ?? null, value, `${name}: ${key}`);
  }
  assert.equal(result.assessmentDate, assessmentDate, `${name}: assessment date is preserved`);
}

// A four-digit year must never be read as a duration in years.
const dated = extractStructuredCaseV2('2026년 3월 1일부터 허가 없이 일했습니다', assessmentDate);
assert.ok(
  dated.durationDays == null || dated.durationDays < 3650,
  'calendar years must not be parsed as a violation duration',
);

// Unresolved facts must stay visible rather than being guessed.
const sparse = extractStructuredCaseV2('허가 없이 일했어요', assessmentDate);
assert.equal(sparse.violationCode ?? null, null, 'ambiguous text must not resolve to a provision');
assert.ok(sparse.unknownFacts.includes('체류자격'), 'missing status must be reported as unknown');
assert.ok(sparse.unknownFacts.includes('위반기간'), 'missing duration must be reported as unknown');

console.log(`Enforcement extraction quality passed (${cases.length} shared parity cases).`);
