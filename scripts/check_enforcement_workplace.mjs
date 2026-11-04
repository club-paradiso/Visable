import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const root = path.resolve(import.meta.dirname, '..');
const require = createRequire(import.meta.url);
const { calculateLegalBaseline, extractStructuredCase } = require('../lib/enforcement-fallback.js');
const { determineWorkplaceRegime } = require('../lib/enforcement-workplace.js');

const fixtures = JSON.parse(
  fs.readFileSync(path.join(root, 'backend/tests/fixtures/workplace_regime_cases.json'), 'utf8'),
);

// Brief case 17: the JS fallback must produce the same regime, baseline
// status and amount as the Python engine for every shared fixture.
for (const entry of fixtures.cases) {
  const det = determineWorkplaceRegime(entry.case);
  assert.equal(det.regime, entry.regime, `${entry.id}: regime`);
  if (entry.dutyBreach) assert.equal(det.dutyBreach, entry.dutyBreach, `${entry.id}: dutyBreach`);
  if (entry.reportTimeliness) {
    assert.equal(det.reportTimeliness, entry.reportTimeliness, `${entry.id}: reportTimeliness`);
  }
  const baseline = calculateLegalBaseline(entry.case);
  assert.equal(baseline.status, entry.baselineStatus, `${entry.id}: baseline status`);
  assert.equal(baseline.baselineAmountKrw ?? null, entry.baselineAmountKrw, `${entry.id}: amount`);
}

// Mission example through the JS extractor: no amount may be guessed.
const mission = extractStructuredCase(
  'E-7-4 비자로 근무하던 외국인이 기존 회사를 그만두고 다른 회사에 취업했습니다. '
  + '출입국에는 별도로 신고하지 않았고 새 회사에서 두 달 동안 일했습니다. 범칙금이 얼마나 나올까요?',
  '2026-11-04',
);
assert.equal(mission.statusOfStay, 'E-7-4');
const missionBaseline = calculateLegalBaseline(mission);
assert.equal(missionBaseline.baselineAmountKrw ?? null, null);
assert.equal(missionBaseline.workplaceDetermination.regime, 'UNRESOLVED');

// Brief case 22 (JS side): identifiers followed by Korean particles are PII.
const pii = extractStructuredCase(
  'E-2인데 근무처 변경 신고 없이 다른 학원에서 30일 일했습니다. 연락처는 010-1234-5678이고 여권번호는 M12345678입니다.',
  '2026-11-04',
);
assert.ok(pii.extractionWarnings.some((item) => item.includes('개인식별정보')));

// '신고했어요' (no object particle) must extract the same procedure fact.
const reported = extractStructuredCase('E-2인데 근무처를 옮기고 10일 안에 출입국에 신고했어요.', '2026-11-04');
assert.equal(reported.procedureStatus, 'REPORT_FILED');

// No-distrust-grounds rule: fields the determination card renders to end
// users (verifiedFacts, missingFacts, exceptionsChecked, warnings,
// nextQuestions, applicableRules, effectiveLawVersion) must never contain
// internal review/engine/ops terminology. The internal humanReviewReason
// metadata field is deliberately excluded — it is never rendered.
const BANNED_USER_TERMS = ['사람의 검토', '사람 검토', '결정론적', '운영자', 'API 키', '스냅샷', '엔진'];
function assertUserFieldsClean(det, label) {
  const rendered = [
    ...(det.verifiedFacts || []), ...(det.missingFacts || []),
    ...(det.exceptionsChecked || []), ...(det.warnings || []),
    ...(det.nextQuestions || []), ...(det.applicableRules || []),
    det.effectiveLawVersion || '',
  ].join('\n');
  for (const term of BANNED_USER_TERMS) {
    assert.ok(!rendered.includes(term), `${label}: user-facing determination fields must not contain "${term}"`);
  }
}
// UNRESOLVED (brief case 15: everything unknown).
assertUserFieldsClean(determineWorkplaceRegime({ violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1', assessmentDate: '2026-11-04' }), 'all-unknown');
// UNRESOLVED via unresolved notice requirements.
assertUserFieldsClean(determineWorkplaceRegime(fixtures.cases.find((entry) => entry.id === 'e7-occupation-unknown').case), 'occupation-unknown');
// Out-of-scope status: guidance must arrive as a missing fact + check method,
// not as an internal review reason.
const outOfScope = determineWorkplaceRegime({
  statusOfStay: 'F-5', violationCode: 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
  workplaceChangeType: 'CHANGE', assessmentDate: '2026-11-04',
});
assert.equal(outOfScope.regime, 'UNRESOLVED');
assert.ok(outOfScope.missingFacts.some((fact) => fact.includes('E-1~E-7') && fact.includes('근무처 변경·추가 절차')),
  'out-of-scope status must add a user-facing missing fact');
assert.ok(outOfScope.nextQuestions.some((q) => q.includes('1345')),
  'out-of-scope guidance must say where to check (관할 출입국·외국인관서 ☎1345)');
assertUserFieldsClean(outOfScope, 'out-of-scope status');
// Conflict: user-confirmed regime vs notice-based determination. The card
// must explain in plain language that the notice-based result was applied.
const conflictCase = {
  ...fixtures.cases.find((entry) => entry.id === 'e7-permit-excluded-occupation').case,
  workplaceRegime: 'REPORT', workplaceRegimeSource: 'USER_CONFIRMED',
};
const conflict = determineWorkplaceRegime(conflictCase);
assert.equal(conflict.regime, 'PERMIT');
assert.ok(conflict.warnings.some((w) => w.includes('고시 규칙 판별을 우선 표시')),
  'conflict case must carry the plain-language notice-priority warning');
assertUserFieldsClean(conflict, 'user-confirmation conflict');
// Before-notice-effective-date case stays clean as well.
assertUserFieldsClean(determineWorkplaceRegime(fixtures.cases.find((entry) => entry.id === 'before-notice-effective').case), 'before-notice-effective');

console.log(`Enforcement workplace parity passed (${fixtures.cases.length} shared fixtures + narrative checks).`);
