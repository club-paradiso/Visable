import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

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
const { assessmentDate, ambiguousWorkCodes, workplaceOverlapCodes, cases } = fixture;

for (const { name, text, expect } of cases) {
  const result = extractStructuredCaseV2(text, assessmentDate);
  for (const [key, expected] of Object.entries(expect)) {
    const value = expected === 'AMBIGUOUS'
      ? ambiguousWorkCodes
      : expected === 'WORKPLACE_OVERLAP' ? workplaceOverlapCodes : expected;
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

// Issue #587: unresolved 18(2)/21(1) overlap still yields the shared 별표 7 baseline,
// with the same disclosures as the Python service (texts must not drift).
const { calculateLegalBaseline } = require('../lib/enforcement-fallback.js');
const fallbackModule = require('../lib/enforcement-fallback.js');
const pyNotes = JSON.parse(execFileSync('python3', ['-c',
  'import json, sys; sys.path.insert(0, "backend"); '
  + 'from services.enforcement_rules import REPORT_PROVISO_NOTE, SHARED_TIER_NOTE; '
  + 'print(json.dumps([REPORT_PROVISO_NOTE, SHARED_TIER_NOTE]))'], { cwd: root, encoding: 'utf8' }));
assert.equal(fallbackModule.REPORT_PROVISO_NOTE, pyNotes[0], 'REPORT_PROVISO_NOTE is identical in Python and JS');
assert.equal(fallbackModule.SHARED_TIER_NOTE, pyNotes[1], 'SHARED_TIER_NOTE is identical in Python and JS');
const overlap = extractStructuredCaseV2('E-7인데 지정된 근무처가 아닌 다른 회사로 옮겨서 변경허가 없이 30일 일했습니다.', assessmentDate);
const overlapBaseline = calculateLegalBaseline(overlap);
assert.equal(overlapBaseline.status, 'AVAILABLE', 'overlap baseline is available');
assert.equal(overlapBaseline.baselineAmountKrw, 1000000, 'overlap baseline uses the shared 별표 7 tier');
assert.equal(overlapBaseline.violationCode, null, 'overlap keeps the provision unresolved');
assert.ok(overlapBaseline.assumptions.some((a) => a.includes('별표 7 더목·저목')), 'shared-tier note');
assert.ok(overlapBaseline.assumptions.some((a) => a.includes('제100조제1항제3호')), 'E-7 proviso note');
const e9 = calculateLegalBaseline(extractStructuredCaseV2('E-9인데 사업장 변경 허가 없이 다른 공장에서 40일 일했습니다.', assessmentDate));
assert.ok(!e9.assumptions.some((a) => a.includes('제100조제1항제3호')), 'no proviso note for E-9');
const f2 = calculateLegalBaseline(extractStructuredCaseV2('F-2인데 다른 곳에서 허가 없이 10일 일했습니다.', assessmentDate));
assert.equal(f2.status, 'MISSING_FACTS', 'candidates with different tables stay missing facts');

console.log(`Enforcement extraction quality passed (${cases.length} shared parity cases).`);
