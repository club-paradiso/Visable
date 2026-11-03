// Prediction-quality guards that a prompt alone cannot guarantee.
// The model text below is a real gpt-oss-120b answer captured from the preview
// probe (?diagnose=raw, fixed synthetic case) on 2026-11-03.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { analyzeBaselineCase, validatePrediction, restatesViolation } = require('../lib/enforcement-grounded-ai.js');

const caseData = {
  schemaVersion: '1', statusOfStay: 'D-2', violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20',
  durationDays: 18, authorizationObtained: false, priorViolations: 0, assessmentDate: '2026-11-03',
  unknownFacts: ['자진신고 여부', '사범조사 시작 여부'],
};
const base = analyzeBaselineCase(caseData);
const baseline = base.legalBaseline;
const evidence = base.prediction.evidence;

const captured = JSON.stringify({
  status: 'LIMITED',
  monetaryPrediction: {
    predictedLikelyRange: { minimumKrw: 1500000, maximumKrw: 2500000 },
    pointEstimateKrw: 2000000,
    predictedDirection: 'BASELINE',
    confidence: { level: 'HIGH', reasons: ['사실관계가 명확히 제공됨'] },
    rationale: [
      { code: 'FIRST_OFFENSE', label: '첫 위반이므로 감경 요인입니다', direction: 'MITIGATING', basis: 'SUPPORTED', evidenceIds: [] },
      { code: 'SHORT_DURATION', label: '위반 기간이 18일로 짧아 감경 요인입니다', direction: 'MITIGATING', basis: 'SUPPORTED', evidenceIds: [] },
      { code: 'UNAUTHORIZED_ACTIVITY', label: '허가 없이 체류자격 외 활동을 하여 가중 요인입니다', direction: 'AGGRAVATING', basis: 'SUPPORTED', evidenceIds: [] },
    ],
  },
  primaryDisposition: {
    type: 'STAY_PERMISSION_DISADVANTAGE', likelihood: 'HIGH',
    confidence: { level: 'HIGH', reasons: ['가장 흔한 처분입니다'] },
    rationale: [{ code: 'VIOLATION_NATURE', label: '체류자격 외 활동 위반은 체류 허가에 불이익을 주는 처분이 일반적입니다', direction: 'NEUTRAL', basis: 'INFERRED', evidenceIds: [] }],
    supportingEvidence: [],
  },
  alternativeDispositions: [],
  stayImpact: ['체류자격 외 활동 위반은 향후 체류 연장 신청 시 불리하게 작용할 가능성이 있습니다'],
  aggravatingFactors: [
    { code: 'UNAUTHORIZED_ACTIVITY', label: '허가 없이 체류자격 외 활동을 하여 가중 요인입니다', direction: 'AGGRAVATING', basis: 'SUPPORTED', evidenceIds: [] },
  ],
  mitigatingFactors: [{ code: 'FIRST_OFFENSE', label: '첫 위반이므로 감경 요인입니다', direction: 'MITIGATING', basis: 'SUPPORTED', evidenceIds: [] }],
  unresolvedFactors: [],
  confidence: { level: 'HIGH', reasons: ['입력된 사실이 충분히 제공됨'] },
  limitations: ['추가 요인은 반영되지 않을 수 있습니다'],
});

const out = validatePrediction(captured, caseData, baseline, evidence, [], { status: 'UNAVAILABLE', limitations: [] }, 'groq/test');

// The violation restated as "aggravating" is removed everywhere it appeared.
assert.equal(out.aggravatingFactors.some((item) => /허가 없이 체류자격 외 활동/.test(item.label)), false);
assert.equal(out.monetaryPrediction.rationale.some((item) => item.direction === 'AGGRAVATING'), false);
assert.ok(out.validationNotes.includes('DROPPED_VIOLATION_RESTATED_AS_AGGRAVATING'));

// Everything legitimate survives: range, disposition, stay impact, mitigating reasons.
assert.deepEqual(out.monetaryPrediction.predictedLikelyRange, { minimumKrw: 1500000, maximumKrw: 2500000, currency: 'KRW' });
assert.equal(out.primaryDisposition.type, 'STAY_PERMISSION_DISADVANTAGE');
assert.equal(out.stayImpact.length, 1);
assert.equal(out.monetaryPrediction.rationale.length, 2);

// The server's own FIRST_OFFENSE factor wins over the model's restatement of it.
const firstOffense = out.mitigatingFactors.filter((item) => item.code === 'FIRST_OFFENSE');
assert.equal(firstOffense.length, 1);
assert.equal(firstOffense[0].label, '확인된 과거 동종 위반 전력이 없습니다.');

// Confidence never exceeds the server cap, whatever the model claims.
assert.notEqual(out.confidence.level, 'HIGH');

// Real aggravation is kept even when the sentence also mentions the violation.
assert.equal(restatesViolation({ direction: 'AGGRAVATING', label: '과거 위반 전력이 있는 상태에서 허가 없이 다시 일했습니다' }), false);
assert.equal(restatesViolation({ direction: 'AGGRAVATING', label: '단속으로 적발되었습니다' }), false);
assert.equal(restatesViolation({ direction: 'MITIGATING', label: '허가 없이 일한 기간이 짧습니다' }), false);
assert.equal(restatesViolation({ direction: 'AGGRAVATING', label: '근무처 변경 허가 없이 다른 회사에서 일했습니다' }), true);

console.log('Enforcement prediction quality guards passed (captured gpt-oss output).');

// ---- Shape slips are unwrapped, not thrown away ----------------------------------
const { unwrapPredictionPayload, analyzeGroundedCase } = require('../lib/enforcement-grounded-ai.js');
const inner = JSON.parse(captured);
assert.equal(unwrapPredictionPayload([inner]).primaryDisposition.type, 'STAY_PERMISSION_DISADVANTAGE');
assert.equal(unwrapPredictionPayload({ prediction: inner }).primaryDisposition.type, 'STAY_PERMISSION_DISADVANTAGE');
assert.equal(unwrapPredictionPayload(inner), inner, 'a correct payload is left alone');
const fromArray = validatePrediction(JSON.stringify([inner]), caseData, baseline, evidence, [], { status: 'UNAVAILABLE', limitations: [] }, 'groq/test');
assert.equal(fromArray.primaryDisposition.type, 'STAY_PERMISSION_DISADVANTAGE');

// ---- One retry on a different model when the first answer is unusable -----------
const saved = { ...process.env };
const realFetch = globalThis.fetch;
try {
  process.env.GROQ_API_KEY = 'synthetic-test-only';
  process.env.ENFORCEMENT_GROQ_MODELS = 'test/broken-model,test/good-model';
  delete process.env.OPENROUTER_API_KEY;
  for (const name of ['LAW_API_OC', 'LAW_OC', 'OPEN_LAW_ID', 'LAW_API_KEY']) delete process.env[name];
  const asked = [];
  globalThis.fetch = async (url, init) => {
    if (new URL(url).host !== 'api.groq.com') return { ok: false, status: 503, json: async () => ({}), text: async () => '' };
    const { model } = JSON.parse(init.body);
    asked.push(model);
    const content = model === 'test/broken-model' ? '"not an object"' : captured;
    return { ok: true, status: 200, json: async () => ({ model, choices: [{ message: { content } }] }) };
  };
  const result = await analyzeGroundedCase(caseData, { timeoutMs: 20000 });
  assert.deepEqual(asked, ['test/broken-model', 'test/good-model'], 'the second attempt must skip the model that failed');
  assert.equal(result.prediction.primaryDisposition?.type, 'STAY_PERMISSION_DISADVANTAGE');
  assert.equal(result.prediction.modelId, 'groq/test/good-model');
  assert.ok(result.prediction.validationNotes.some((note) => note.startsWith('RETRY_REJECTED:invalid_prediction_object')));
} finally {
  globalThis.fetch = realFetch;
  for (const key of Object.keys(process.env)) if (!(key in saved)) delete process.env[key];
  Object.assign(process.env, saved);
}

console.log('Enforcement prediction shape-unwrap and retry checks passed.');

// ---- No HIGH likelihood without outcome evidence, in either direction -------------
{
  const severe = JSON.parse(captured);
  severe.primaryDisposition = { ...severe.primaryDisposition, type: 'DEPORTATION', likelihood: 'HIGH' };
  severe.alternativeDispositions = [{ type: 'STAY_PERMISSION_DISADVANTAGE', likelihood: 'VERY_HIGH', rationale: [] }];
  const capped = validatePrediction(JSON.stringify(severe), caseData, baseline, evidence, [], { status: 'UNAVAILABLE', limitations: [] }, 'groq/test');
  assert.equal(capped.primaryDisposition.type, 'DEPORTATION');
  assert.equal(capped.primaryDisposition.likelihood, 'MODERATE');
  assert.equal(capped.primaryDisposition.likelihoodCappedFrom, 'HIGH');
  assert.equal(capped.alternativeDispositions[0].likelihood, 'MODERATE');
  assert.ok(capped.validationNotes.includes('LIKELIHOOD_CAPPED:DEPORTATION:HIGH'));
  const low = JSON.parse(captured);
  low.primaryDisposition = { ...low.primaryDisposition, likelihood: 'LOW' };
  const kept = validatePrediction(JSON.stringify(low), caseData, baseline, evidence, [], { status: 'UNAVAILABLE', limitations: [] }, 'groq/test');
  assert.equal(kept.primaryDisposition.likelihood, 'LOW');
  assert.equal(kept.primaryDisposition.likelihoodCappedFrom, undefined);
  console.log('Enforcement likelihood cap checks passed.');
}
