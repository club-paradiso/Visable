'use strict';

const rulesDb = require('../backend/data/enforcement/legal_rules.json');

const MAX_CASE_TEXT = 3000;
const COMMON_DISPOSITIONS = ['STAY_PERMISSION_DISADVANTAGE', 'DEPARTURE_ORDER', 'DEPORTATION'];
const CRIMINAL_CODES = new Set([
  'UNAUTHORIZED_STAY_OR_WORK_ART18_1',
  'UNAUTHORIZED_EMPLOYMENT_ART18_2',
  'STATUS_OUTSIDE_ACTIVITY_ART20',
  'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
]);

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function parseIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ''))) return null;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function iso(date) {
  return date.toISOString().slice(0, 10);
}

function daysInclusive(start, end) {
  return Math.floor((end.getTime() - start.getTime()) / 86400000) + 1;
}

function addMonthsUtc(value, months) {
  const year = value.getUTCFullYear();
  const monthIndex = value.getUTCMonth() + months;
  const targetYear = year + Math.floor(monthIndex / 12);
  const targetMonth = ((monthIndex % 12) + 12) % 12;
  const lastDay = new Date(Date.UTC(targetYear, targetMonth + 1, 0)).getUTCDate();
  const day = Math.min(value.getUTCDate(), lastDay);
  return new Date(Date.UTC(targetYear, targetMonth, day));
}

function omitNullish(object) {
  const output = {};
  for (const [key, value] of Object.entries(object)) {
    if (value !== null && value !== undefined) output[key] = value;
  }
  return output;
}

function containsSensitiveIdentifier(text) {
  return [
    /\b[A-Z]\d{8}\b/i,
    /\b\d{6}[- ]?[1-8]\d{6}\b/,
    /\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b/,
    /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/,
  ].some((pattern) => pattern.test(text || ''));
}

function extractDates(text) {
  const values = [];
  const pattern = /(\d{4})\s*(?:년|[./-])\s*(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*일?/g;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    const value = `${match[1]}-${String(match[2]).padStart(2, '0')}-${String(match[3]).padStart(2, '0')}`;
    if (parseIsoDate(value)) values.push(value);
  }
  return values;
}

function extractStructuredCase(text, assessmentDate) {
  const clean = String(text || '').trim().slice(0, MAX_CASE_TEXT).replace(/\s+/g, ' ');
  if (!clean) throw new Error('case text is required');

  const warnings = [];
  if (containsSensitiveIdentifier(clean)) {
    warnings.push('분석에 불필요한 개인식별정보가 감지되어 구조화 결과에 포함하지 않았습니다.');
  }

  const statusMatch = clean.match(/(?:^|[^A-Z0-9])([A-HM]-?\d(?:-\d+)?)(?![A-Z0-9-])/i);
  const statusOfStay = statusMatch ? statusMatch[1].toUpperCase() : null;

  let durationDays = null;
  const durationMatch = clean.match(/(?:약\s*)?(\d+)\s*(일|주|개월|달|년)/);
  if (durationMatch) {
    const multiplier = { '일': 1, '주': 7, '개월': 30, '달': 30, '년': 365 }[durationMatch[2]];
    durationDays = Number(durationMatch[1]) * multiplier;
  }

  const dates = extractDates(clean);
  const violationStartDate = dates[0] || null;
  const violationEndDate = dates[1] || null;
  if (violationStartDate && violationEndDate) {
    const start = parseIsoDate(violationStartDate);
    const end = parseIsoDate(violationEndDate);
    if (end >= start) durationDays = daysInclusive(start, end);
  }

  const unauthorized = /허가\s*(?:를\s*)?(?:받지\s*않|없이|없)|무허가|불법\s*취업/.test(clean);
  const work = /일했|일함|근무|아르바이트|알바|취업|고용|음식점|공장|건설/.test(clean);
  const overstay = /체류기간.*(?:넘|초과)|오버스테이|불법체류/.test(clean);
  const workplaceChange = /근무처.*(?:변경|추가)|사업장.*(?:변경|추가)/.test(clean);

  let violationCode = null;
  if (overstay) violationCode = 'OVERSTAY_ART25';
  else if (workplaceChange && unauthorized) violationCode = 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1';
  else if (work && unauthorized && statusOfStay && /^(D-2|D-4)/.test(statusOfStay)) violationCode = 'STATUS_OUTSIDE_ACTIVITY_ART20';
  else if (work && unauthorized) violationCode = 'UNAUTHORIZED_EMPLOYMENT_ART18_2';

  let priorViolations = null;
  if (/처음|초범|전력\s*(?:없|0)|걸린\s*적(?:은|이)?\s*없/.test(clean)) priorViolations = 0;
  else {
    const priorMatch = clean.match(/(?:과거|이전|전력).*?(\d+)\s*회/);
    if (priorMatch) priorViolations = Number(priorMatch[1]);
  }

  const voluntaryDisclosure = /자진\s*(?:신고|출석|출국)/.test(clean) ? true : null;
  const investigationStarted = /(?:사범)?조사.*(?:시작|중)|적발|단속/.test(clean) ? true : null;
  const falseRepresentation = /허위|위조|거짓/.test(clean) ? true : null;

  const unknownFacts = [];
  if (!statusOfStay) unknownFacts.push('체류자격');
  if (!violationCode) unknownFacts.push('구체적인 위반 유형');
  if (durationDays === null) unknownFacts.push('위반기간');
  if (!violationStartDate) unknownFacts.push('위반 시작일');
  if (priorViolations === null) unknownFacts.push('과거 위반 전력');
  if (voluntaryDisclosure === null) unknownFacts.push('자진신고 여부');
  if (investigationStarted === null) unknownFacts.push('사범조사 시작 여부');

  return omitNullish({
    schemaVersion: '1',
    statusOfStay,
    violationCode,
    violationCandidates: violationCode ? [violationCode] : [],
    activity: work ? '취업활동' : null,
    workplaceType: clean.includes('음식점') ? '음식점' : null,
    authorizationObtained: unauthorized ? false : null,
    durationDays,
    violationStartDate,
    violationEndDate,
    assessmentDate: assessmentDate || todayIso(),
    priorViolations,
    voluntaryDisclosure,
    investigationStarted,
    falseRepresentation,
    unknownFacts,
    extractionWarnings: warnings,
  });
}

function sourceRefs(snapshot) {
  return (snapshot.sources || []).map((source, index) => ({
    id: `${snapshot.id}:source:${index + 1}`,
    authority: source.authority,
    title: source.lawName,
    article: source.article,
    effectiveDate: snapshot.effectiveFrom,
    url: source.url,
    verifiedAt: snapshot.verifiedAt,
  }));
}

function resolveSnapshot(caseData) {
  const relevant = caseData.violationEndDate || caseData.violationStartDate || caseData.assessmentDate || todayIso();
  const snapshots = [...rulesDb.snapshots].sort((a, b) => b.effectiveFrom.localeCompare(a.effectiveFrom));
  for (const snapshot of snapshots) {
    if (relevant < snapshot.effectiveFrom) continue;
    if (snapshot.effectiveUntil && relevant > snapshot.effectiveUntil) continue;
    if (caseData.violationStartDate && caseData.violationStartDate < snapshot.effectiveFrom) return null;
    return snapshot;
  }
  return null;
}

function tierForDuration(tiers, caseData, durationDays) {
  let months;
  if (caseData.violationStartDate && caseData.violationEndDate) {
    const start = parseIsoDate(caseData.violationStartDate);
    const end = parseIsoDate(caseData.violationEndDate);
    months = 0;
    while (months < 1200 && end >= addMonthsUtc(start, months + 1)) months += 1;
  } else {
    months = durationDays / 30;
  }
  const tier = tiers.find((row) => months >= Number(row.minimumMonths)
    && (row.maximumMonths === null || row.maximumMonths === undefined || months < Number(row.maximumMonths)));
  if (!tier) throw new Error('no duration tier matched');
  return tier;
}

function availableDispositions(code) {
  if (CRIMINAL_CODES.has(code)) return [...COMMON_DISPOSITIONS, 'CRIMINAL_REFERRAL'];
  if (code === 'OVERSTAY_ART25') return [...COMMON_DISPOSITIONS];
  return [];
}

function calculateLegalBaseline(caseData) {
  const snapshot = resolveSnapshot(caseData);
  if (!snapshot) {
    return omitNullish({
      status: 'HISTORICAL_RULE_UNAVAILABLE',
      violationCode: caseData.violationCode || null,
      missingFacts: ['해당 위반기간 전체에 적용되는 검증된 법령 스냅샷'],
      confidence: 'INSUFFICIENT',
    });
  }

  const sources = sourceRefs(snapshot);
  if (!caseData.violationCode) {
    return {
      status: 'MISSING_FACTS',
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      missingFacts: ['위반 유형'],
      sources,
      confidence: 'INSUFFICIENT',
    };
  }

  const rule = snapshot.rules.find((row) => row.violationCode === caseData.violationCode);
  if (!rule) {
    return {
      status: 'UNSUPPORTED',
      violationCode: caseData.violationCode,
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      sources,
      confidence: 'INSUFFICIENT',
    };
  }

  let durationDays = caseData.durationDays;
  if (caseData.violationStartDate && caseData.violationEndDate) {
    const start = parseIsoDate(caseData.violationStartDate);
    const end = parseIsoDate(caseData.violationEndDate);
    if (!start || !end || end < start) throw new Error('invalid violation date range');
    durationDays = daysInclusive(start, end);
  }

  if (durationDays === null || durationDays === undefined || Number.isNaN(Number(durationDays))) {
    return {
      status: 'MISSING_FACTS',
      violationCode: caseData.violationCode,
      violationLabel: rule.label,
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      missingFacts: ['위반기간'],
      sources,
      confidence: 'INSUFFICIENT',
    };
  }

  const tier = tierForDuration(rule.tiers, caseData, Number(durationDays));
  const baselineAmountKrw = Number(tier.amountKrw);
  const statutoryMaximumKrw = Number(rule.statutoryMaximumKrw);
  const minimumKrw = Math.max(0, Math.floor(baselineAmountKrw / 2));
  const maximumKrw = Math.min(statutoryMaximumKrw, baselineAmountKrw + Math.floor(baselineAmountKrw / 2));
  const assumptions = [];
  if (!(caseData.violationStartDate && caseData.violationEndDate)) {
    assumptions.push('정확한 시작·종료일이 없어 30일을 1개월로 환산했습니다.');
  }

  return {
    status: 'AVAILABLE',
    violationCode: caseData.violationCode,
    violationLabel: rule.label,
    baselineAmountKrw,
    legallyAdjustableRange: { minimumKrw, maximumKrw, currency: 'KRW' },
    statutoryMaximumKrw,
    durationDays: Number(durationDays),
    legalSnapshotId: snapshot.id,
    effectiveFrom: snapshot.effectiveFrom,
    appliedRules: [rule.statuteArticle, rule.penaltyArticle, '출입국관리법 시행규칙 제86조(가중·감경 범위)'],
    legallyAvailableDispositions: availableDispositions(caseData.violationCode),
    assumptions,
    missingFacts: [],
    sources,
    confidence: assumptions.length ? 'HIGH' : 'VERY_HIGH',
  };
}

function evidenceFromBaseline(baseline) {
  return (baseline.sources || []).map((source) => ({
    id: source.id,
    sourceType: source.title && source.title.includes('시행규칙') ? 'REGULATION' : 'STATUTE',
    title: source.title,
    authority: source.authority,
    sourceDate: source.effectiveDate,
    sourceUrl: source.url,
    excerpt: source.article || '',
    citationGrade: 'DIRECT',
    resultKind: 'LEGAL_RULE',
    applicable: true,
  }));
}

function analyzeCase(caseData) {
  if (!caseData || typeof caseData !== 'object' || Array.isArray(caseData)) {
    throw new Error('invalid structured enforcement case');
  }
  if (caseData.violationStartDate && !parseIsoDate(caseData.violationStartDate)) throw new Error('invalid structured enforcement case');
  if (caseData.violationEndDate && !parseIsoDate(caseData.violationEndDate)) throw new Error('invalid structured enforcement case');
  if (caseData.violationStartDate && caseData.violationEndDate && caseData.violationEndDate < caseData.violationStartDate) {
    throw new Error('invalid structured enforcement case');
  }

  const baseline = calculateLegalBaseline(caseData);
  const evidence = evidenceFromBaseline(baseline);
  const limitations = ['현재 확인 가능한 유사 공개사례가 충분하지 않습니다.'];
  if (baseline.status !== 'AVAILABLE') limitations.push('검증된 법령상 기준이 없어 AI 예측을 생성하지 않았습니다.');
  else limitations.push('현재 AI 예상 처분을 생성하지 못했습니다.');

  return {
    schemaVersion: '1',
    case: caseData,
    legalBaseline: baseline,
    prediction: {
      schemaVersion: '1',
      engineVersion: 'enforcement-prediction-v1',
      promptVersion: 'enforcement-prediction-prompt-v1',
      status: 'UNAVAILABLE',
      evidence,
      similarCases: [],
      aggravatingFactors: [],
      mitigatingFactors: [],
      unresolvedFactors: [],
      alternativeDispositions: [],
      stayImpact: [],
      confidence: {
        level: 'INSUFFICIENT',
        reasons: ['법령상 기준은 유지되지만 예측 모델의 유효한 구조화 결과가 없습니다.'],
      },
      limitations,
    },
    generatedAt: new Date().toISOString(),
    disclaimer: '이 결과는 공개 법령과 제한된 공개 근거에 기반한 정보 제공용 예상이며, 출입국 당국의 최종 처분이나 법률 자문이 아닙니다.',
    privacyNotice: '원문 사례 서술은 응답·저장·일반 로그에 남기지 않습니다.',
  };
}

module.exports = {
  extractStructuredCase,
  analyzeCase,
  calculateLegalBaseline,
};
