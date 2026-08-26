'use strict';

const OUTCOME_POLICY_VERSION = 'enforcement-outcome-policy-2026-08-26-v1';
const NO_IMMEDIATE_DEPARTURE_MEASURE = 'NO_IMMEDIATE_DEPARTURE_MEASURE';
const DEPARTURE_RECOMMENDATION = 'DEPARTURE_RECOMMENDATION';
const HIGH_IMPACT_DEPARTURE_TYPES = new Set(['DEPARTURE_ORDER', 'DEPORTATION']);

function unique(items) {
  return [...new Set((items || []).filter(Boolean))];
}

function directCaseEvidenceIds(prediction) {
  return new Set((prediction && prediction.evidence || [])
    .filter((item) => item && item.resultKind === 'BODY_RESULT' && item.citationGrade === 'DIRECT')
    .map((item) => item.id)
    .filter(Boolean));
}

function hasDirectDispositionSupport(disposition, directIds) {
  if (!disposition || !Array.isArray(disposition.supportingEvidence)) return false;
  return disposition.supportingEvidence.some((id) => directIds.has(id));
}

function lowConfidence(existing, reason) {
  const reasons = unique([...(existing && existing.reasons || []), reason]).slice(0, 8);
  return { level: 'LOW', reasons };
}

function conservativeNeutralOutcome(reason) {
  return {
    type: NO_IMMEDIATE_DEPARTURE_MEASURE,
    likelihood: 'UNKNOWN',
    rank: 1,
    confidence: {
      level: 'LOW',
      reasons: [reason],
    },
    rationale: [],
    supportingEvidence: [],
  };
}

function sanitizeF5Dispositions(analysis) {
  const caseData = analysis && analysis.case || {};
  const baseline = analysis && analysis.legalBaseline || {};
  const prediction = analysis && analysis.prediction || {};
  const status = String(caseData.statusOfStay || '').toUpperCase();
  if (!/^F-5(?:-|$)/.test(status)) return;

  // Immigration Act Article 46(2) generally protects permanent residents from
  // deportation except limited serious exceptions. The public case schema does
  // not capture all exception facts, so fail closed instead of predicting it.
  baseline.legallyAvailableDispositions = (baseline.legallyAvailableDispositions || [])
    .filter((type) => type !== 'DEPORTATION');
  if (prediction.primaryDisposition && prediction.primaryDisposition.type === 'DEPORTATION') {
    prediction.primaryDisposition = null;
  }
  prediction.alternativeDispositions = (prediction.alternativeDispositions || [])
    .filter((item) => item && item.type !== 'DEPORTATION');
  prediction.limitations = unique([
    ...(prediction.limitations || []),
    'F-5 영주자에 대한 강제퇴거는 출입국관리법 제46조제2항의 제한과 예외사유를 별도로 확인해야 하므로 일반 예측에서 제외했습니다.',
  ]);
}

function applyOutcomePolicy(analysis) {
  if (!analysis || typeof analysis !== 'object') return analysis;
  const baseline = analysis.legalBaseline || {};
  const prediction = analysis.prediction || {};
  const directIds = directCaseEvidenceIds(prediction);

  if (baseline.status === 'AVAILABLE') {
    baseline.legallyAvailableDispositions = unique([
      NO_IMMEDIATE_DEPARTURE_MEASURE,
      DEPARTURE_RECOMMENDATION,
      ...(baseline.legallyAvailableDispositions || []),
    ]);
  }

  sanitizeF5Dispositions(analysis);

  const directReason = '직접 인용 가능한 유사사례 본문이 해당 출국조치를 뒷받침하지 않아 가장 유력한 처분으로 단정하지 않았습니다.';
  let demotedPrimary = null;
  if (prediction.primaryDisposition
      && HIGH_IMPACT_DEPARTURE_TYPES.has(prediction.primaryDisposition.type)
      && !hasDirectDispositionSupport(prediction.primaryDisposition, directIds)) {
    demotedPrimary = {
      ...prediction.primaryDisposition,
      likelihood: 'UNKNOWN',
      confidence: lowConfidence(prediction.primaryDisposition.confidence, directReason),
      rank: 2,
    };
    prediction.primaryDisposition = null;
  }

  const alternatives = [...(prediction.alternativeDispositions || [])];
  if (demotedPrimary) alternatives.unshift(demotedPrimary);
  if (baseline.status === 'AVAILABLE'
      && !alternatives.some((item) => item && item.type === NO_IMMEDIATE_DEPARTURE_MEASURE)
      && (!prediction.primaryDisposition || prediction.primaryDisposition.type !== NO_IMMEDIATE_DEPARTURE_MEASURE)) {
    alternatives.unshift(conservativeNeutralOutcome(
      '출입국관리법 제68조상 출국명령은 통고처분 후 자동으로 발생하는 효과가 아니라 별도 판단이 필요한 조치이므로, 즉시 출국조치가 없는 결과도 배제하지 않습니다.'
    ));
  }

  prediction.alternativeDispositions = alternatives
    .filter((item, index, list) => item && list.findIndex((other) => other && other.type === item.type) === index)
    .map((item, index) => ({ ...item, rank: prediction.primaryDisposition ? index + 2 : index + 1 }))
    .slice(0, 4);

  prediction.limitations = unique([
    ...(prediction.limitations || []),
    '출국명령·강제퇴거는 범칙금 산정과 별개의 재량·요건 판단이 필요한 조치이며 자동 결과로 해석하면 안 됩니다.',
    '표시되는 ±50% 금액 범위는 출입국관리법 시행규칙 제86조제2항의 통상 가중·감경 범위입니다. 제86조제3항의 법무부장관 승인 예외는 자동 예측하지 않습니다.',
  ]).slice(0, 12);

  analysis.outcomePolicy = {
    version: OUTCOME_POLICY_VERSION,
    departureOrderIsAutomatic: false,
    ordinaryAdjustmentBasis: '출입국관리법 시행규칙 제86조제2항',
    exceptionalAdjustmentExcluded: true,
    directCaseEvidenceCount: directIds.size,
  };
  return analysis;
}

module.exports = {
  DEPARTURE_RECOMMENDATION,
  NO_IMMEDIATE_DEPARTURE_MEASURE,
  OUTCOME_POLICY_VERSION,
  applyOutcomePolicy,
};
