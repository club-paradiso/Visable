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

// E-1~E-7: an ambiguous permit-vs-report regime must never produce a fine.
const { calculateLegalBaseline } = require('../lib/enforcement-fallback.js');
const fallbackModule = require('../lib/enforcement-fallback.js');
const pyNotes = JSON.parse(execFileSync('python3', ['-c',
  'import json, sys; sys.path.insert(0, "backend"); '
  + 'from services.enforcement_rules import REPORT_PROVISO_NOTE, SHARED_TIER_NOTE, PERMIT_CONFIRMATION_NOTE; '
  + 'print(json.dumps([REPORT_PROVISO_NOTE, SHARED_TIER_NOTE, PERMIT_CONFIRMATION_NOTE]))'], { cwd: root, encoding: 'utf8' }));
assert.equal(fallbackModule.REPORT_PROVISO_NOTE, pyNotes[0], 'report note parity');
assert.equal(fallbackModule.SHARED_TIER_NOTE, pyNotes[1], 'shared tier parity');
assert.equal(fallbackModule.PERMIT_CONFIRMATION_NOTE, pyNotes[2], 'conditional permit note parity');
const overlap = extractStructuredCaseV2('E-7인데 지정된 근무처가 아닌 다른 회사로 옮겨서 변경허가 없이 30일 일했습니다.', assessmentDate);
const overlapBaseline = calculateLegalBaseline(overlap);
assert.equal(overlapBaseline.status, 'MISSING_FACTS', 'E-7 overlap must not be priced');
assert.equal(overlapBaseline.baselineAmountKrw ?? null, null, 'no presumed permit fine');
const e2 = extractStructuredCaseV2('E-2 체류자격으로 필요한 허가 없이 63일 동안 일한 상황이에요. 이번이 첫 위반이에요. 본인이 먼저 신고하거나 출입국관서에 자진 방문했어요.', assessmentDate);
assert.equal(e2.statusOfStay, 'E-2');
assert.equal(e2.durationDays, 63);
const e2Unknown = { ...e2, violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', violationCandidates: ['UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1'] };
assert.equal(calculateLegalBaseline(e2Unknown).status, 'MISSING_FACTS');
assert.equal(calculateLegalBaseline({ ...e2Unknown, workplaceRegime: 'REPORT' }).status, 'UNSUPPORTED');
const e2Permit = calculateLegalBaseline({ ...e2Unknown, workplaceRegime: 'PERMIT' });
assert.equal(e2Permit.status, 'AVAILABLE');
assert.equal(e2Permit.baselineAmountKrw, 1000000);
assert.ok(e2Permit.assumptions.includes(pyNotes[2]), 'conditional permit note');
const e9 = calculateLegalBaseline(extractStructuredCaseV2('E-9인데 사업장 변경 허가 없이 다른 공장에서 40일 일했습니다.', assessmentDate));
assert.equal(e9.status, 'AVAILABLE', 'E-9 fine still calculated');
const f2 = calculateLegalBaseline(extractStructuredCaseV2('F-2인데 다른 곳에서 허가 없이 10일 일했습니다.', assessmentDate));
assert.equal(f2.status, 'MISSING_FACTS', 'candidates with different tables stay missing facts');

console.log(`Enforcement extraction quality passed (${cases.length} shared parity cases).`);
