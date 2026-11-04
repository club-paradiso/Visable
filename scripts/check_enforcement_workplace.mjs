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

console.log(`Enforcement workplace parity passed (${fixtures.cases.length} shared fixtures + narrative checks).`);
