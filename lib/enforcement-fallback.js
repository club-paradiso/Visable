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

const WORK_STATUS_RE = /^(?:C-4|E-(?:1|2|3|4|5|6|7|8|9|10)|H-2)(?:-|$)/i;
const CLEAR_NON_WORK_STATUS_RE = /^(?:B-1|B-2|C-1|C-3)(?:-|$)/i;
const STUDY_STATUS_RE = /^(?:D-2|D-4)(?:-|$)/i;
const AMBIGUOUS_WORK_RELATION_FACT = '취업 가능 체류자격인지 및 지정 근무처·근무처 변경 관계';
const ALLOWED_VIOLATION_CODES = new Set([
  'UNAUTHORIZED_STAY_OR_WORK_ART18_1',
  'UNAUTHORIZED_EMPLOYMENT_ART18_2',
  'STATUS_OUTSIDE_ACTIVITY_ART20',
  'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
  'OVERSTAY_ART25',
]);
const AMBIGUOUS_WORK_CODES = [
  'UNAUTHORIZED_STAY_OR_WORK_ART18_1',
  'STATUS_OUTSIDE_ACTIVITY_ART20',
  'UNAUTHORIZED_EMPLOYMENT_ART18_2',
  'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
];
const CANONICAL_UNKNOWN_FACTS = new Set([
  '체류자격',
  '구체적인 위반 유형',
  AMBIGUOUS_WORK_RELATION_FACT,
  '위반기간',
  '위반 시작일',
  '과거 위반 전력',
  '자진신고 여부',
  '사범조사 시작 여부',
]);

const STATUS_RE = /(?<![A-Z0-9])([A-HM])\s*-?\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?(?!\d)/i;
const FULL_DATE_RE = /(\d{4})\s*(?:년|[./-])\s*(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*일?/g;
const SHORT_DATE_RE = /(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*일?/;
const DURATION_TOKEN_RE = /(\d+)\s*(년|개월|달|주|일)/g;
const DURATION_MULTIPLIERS = { '일': 1, '주': 7, '개월': 30, '달': 30, '년': 365 };
const WORD_DURATIONS = [
  [/(?<![가-힣])하루(?![가-힣])/, 1],
  [/(?<![가-힣])이틀(?![가-힣])/, 2],
  [/(?<![가-힣])사흘(?![가-힣])/, 3],
  [/(?<![가-힣])나흘(?![가-힣])/, 4],
  [/(?<![가-힣])닷새(?![가-힣])/, 5],
  [/(?<![가-힣])엿새(?![가-힣])/, 6],
  [/(?<![가-힣])이레(?![가-힣])/, 7],
  [/(?<![가-힣])여드레(?![가-힣])/, 8],
  [/(?<![가-힣])아흐레(?![가-힣])/, 9],
  [/(?<![가-힣])열흘(?![가-힣])/, 10],
  [/일주일/, 7],
  [/보름/, 15],
  [/한\s*달/, 30],
  [/두\s*달/, 60],
  [/(?:세|석)\s*달/, 90],
];

const UNAUTHORIZED_RE = new RegExp(
  '허가(?:를)?\\s*(?:안\\s*받|받지\\s*않|없이|없|미취득|미허가)'
  + '|무허가|불법\\s*(?:취업|근무|알바)'
  + '|시간제\\s*취업(?:허가)?\\s*(?:안\\s*받|미허가|없이)'
  + '|취업\\s*(?:불가|금지)',
  'i',
);
const WORK_RE = new RegExp(
  '일했|일함|일하고|일하다|근무|아르바이트|알바|취업|고용|돈\\s*벌'
  + '|사업장|근무처|음식점|공장|건설|회사|업체',
  'i',
);
const OVERSTAY_RE = new RegExp(
  '체류기간.*(?:넘|초과|만료|지났)'
  + '|기간\\s*만료.*(?:후|지났|넘)'
  + '|만료(?:일)?\\s*(?:후|지났|넘)'
  + '|오버스테이|불법체류|초과\\s*체류'
  + '|(?:\\d+\\s*일|하루|이틀|사흘|나흘|닷새|엿새|일주일).*(?:오버스테이|초과)',
  'i',
);
// 제21조제1항(근무처 변경·추가 허가)을 가리키는 명시적 표현만 잡는다.
// "다른 회사에서 일했다" 같은 서술은 제18조제2항과 구별되지 않으므로 제외한다.
const WORKPLACE_CHANGE_RE = new RegExp(
  '(?:근무처|사업장|회사|업체)\\s*(?:를|로|으로)?\\s*(?:변경|추가)'
  + '|(?:변경|추가)\\s*(?:허가|신고)'
  + '|(?:근무처|사업장|회사|업체).*?(?:옮겼|옮긴|옮기|이직)'
  + '|(?:옮겼|옮긴|이직).*?(?:허가|신고)',
  'i',
);
// 제18조제2항(지정된 근무처가 아닌 곳에서 근무)을 가리키는 명시적 표현.
const OUTSIDE_DESIGNATED_WORKPLACE_RE = new RegExp(
  '지정(?:된)?\\s*(?:근무처|사업장).*(?:아닌|외)'
  + '|허가(?:된)?\\s*(?:근무처|사업장).*(?:외|아닌)',
  'i',
);
const EXPLICIT_NO_WORK_STATUS_RE = new RegExp(
  '취업활동을?\\s*(?:할\\s*수\\s*)?없는\\s*체류자격'
  + '|취업\\s*(?:불가|금지)\\s*체류자격'
  + '|취업자격\\s*(?:이\\s*)?없',
  'i',
);
const FIRST_OFFENSE_RE = new RegExp(
  '처음|초범|첫\\s*(?:위반|적발)|전력\\s*(?:없|0)|위반\\s*이력\\s*없'
  + '|걸린\\s*적(?:은|이)?\\s*없|처벌\\s*받은\\s*적\\s*없',
  'i',
);
const PRIOR_COUNT_RE = /(?:과거|이전|전력|위반\s*이력).*?(\d+)\s*회/i;
const VOLUNTARY_RE = new RegExp(
  '자진\\s*(?:신고|출석|출국|방문)|스스로\\s*(?:신고|출석|방문)'
  + '|(?:바로|즉시)\\s*(?:출입국|관서).*(?:방문|찾아)',
  'i',
);
const INVESTIGATION_RE = /(?:사범)?조사.*(?:시작|중)|적발|단속|걸렸|출입국.*(?:연락|통보)/i;
const FALSE_REPRESENTATION_RE = /허위|위조|거짓/i;
const EXPLICIT_AUTHORIZED_RE = /(?:취업|활동|시간제\s*취업)?\s*허가(?:를)?\s*(?:받았|받음|취득|있음)/i;

function extractStatus(clean) {
  const match = clean.match(STATUS_RE);
  if (!match) return null;
  let status = `${match[1].toUpperCase()}-${Number(match[2])}`;
  if (match[3]) status += `-${Number(match[3])}`;
  return status;
}

function extractDates(clean, assessmentDate) {
  const found = [];
  FULL_DATE_RE.lastIndex = 0;
  let match;
  while ((match = FULL_DATE_RE.exec(clean)) !== null) {
    const value = `${match[1]}-${String(match[2]).padStart(2, '0')}-${String(match[3]).padStart(2, '0')}`;
    const parsed = parseIsoDate(value);
    if (parsed && parsed.getUTCMonth() + 1 === Number(match[2]) && parsed.getUTCDate() === Number(match[3])) {
      found.push({ end: match.index + match[0].length, value, year: Number(match[1]) });
    }
  }

  const dates = found.map((item) => item.value);
  if (found.length === 1) {
    const short = clean.slice(found[0].end).match(SHORT_DATE_RE);
    if (short) {
      const value = `${found[0].year}-${String(short[1]).padStart(2, '0')}-${String(short[2]).padStart(2, '0')}`;
      const parsed = parseIsoDate(value);
      if (parsed && parsed.getUTCMonth() + 1 === Number(short[1]) && parsed.getUTCDate() === Number(short[2])) {
        dates.push(value);
      }
    }
  }

  const reference = assessmentDate && parseIsoDate(assessmentDate) ? assessmentDate : todayIso();
  if (dates.length === 1 && /오늘\s*(?:까지|현재|기준|방문|자진)/.test(clean) && reference >= dates[0]) {
    dates.push(reference);
  }
  if (!dates.length && /어제\s*(?:부터|시작)/.test(clean)) {
    const referenceDate = parseIsoDate(reference);
    dates.push(iso(new Date(referenceDate.getTime() - 86400000)));
    if (/오늘\s*(?:까지|현재|기준)/.test(clean)) dates.push(reference);
  }

  return { violationStartDate: dates[0] || null, violationEndDate: dates[1] || null };
}

function extractDurationDays(clean) {
  const scrubbed = clean.replace(FULL_DATE_RE, ' ');

  let total = 0;
  let matched = false;
  DURATION_TOKEN_RE.lastIndex = 0;
  let match;
  while ((match = DURATION_TOKEN_RE.exec(scrubbed)) !== null) {
    const amount = Number(match[1]);
    const unit = match[2];
    if (unit === '년' && amount > 100) continue;
    total += amount * DURATION_MULTIPLIERS[unit];
    matched = true;
  }
  if (matched) return total;

  for (const [pattern, days] of WORD_DURATIONS) {
    if (pattern.test(scrubbed)) return days;
  }
  return null;
}

function classifyViolation(clean, status) {
  const unauthorized = UNAUTHORIZED_RE.test(clean);
  const work = WORK_RE.test(clean);
  const overstay = OVERSTAY_RE.test(clean);
  const workplaceChange = WORKPLACE_CHANGE_RE.test(clean);
  const outsideDesignatedWorkplace = OUTSIDE_DESIGNATED_WORKPLACE_RE.test(clean);
  const explicitNoWorkStatus = EXPLICIT_NO_WORK_STATUS_RE.test(clean);
  const normalizedStatus = String(status || '').toUpperCase();

  if (overstay) {
    return { violationCode: 'OVERSTAY_ART25', violationCandidates: ['OVERSTAY_ART25'], unauthorized, work, workplaceChange };
  }
  if (!(work && unauthorized)) {
    return { violationCode: null, violationCandidates: [], unauthorized, work, workplaceChange };
  }

  // 명시적인 조문 표지가 있을 때만 조문을 확정한다. 분기 순서는
  // backend/services/enforcement_service.py의 _classify_violation과 동일해야 한다:
  // 변경·추가·이직처럼 제21조제1항을 직접 가리키는 더 구체적인 신호를 먼저 적용해야
  // "지정된 근무처가 아닌 다른 회사로 옮겨서" 같은 복합 문장을 오분류하지 않는다.
  let code = null;
  if (STUDY_STATUS_RE.test(normalizedStatus)) code = 'STATUS_OUTSIDE_ACTIVITY_ART20';
  else if (workplaceChange) code = 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1';
  else if (outsideDesignatedWorkplace && WORK_STATUS_RE.test(normalizedStatus)) code = 'UNAUTHORIZED_EMPLOYMENT_ART18_2';
  else if (explicitNoWorkStatus || CLEAR_NON_WORK_STATUS_RE.test(normalizedStatus)) code = 'UNAUTHORIZED_STAY_OR_WORK_ART18_1';

  return {
    violationCode: code,
    violationCandidates: code ? [code] : [...AMBIGUOUS_WORK_CODES],
    unauthorized,
    work,
    workplaceChange,
  };
}

function unknownFactsFor(caseData) {
  const unknown = (caseData.unknownFacts || []).filter((item) => item && !CANONICAL_UNKNOWN_FACTS.has(item));
  if (!caseData.statusOfStay) unknown.push('체류자격');
  if (!caseData.violationCode) {
    if ((caseData.violationCandidates || []).length) unknown.push(AMBIGUOUS_WORK_RELATION_FACT);
    else unknown.push('구체적인 위반 유형');
  }
  if (caseData.durationDays === null || caseData.durationDays === undefined) {
    unknown.push('위반기간');
    if (!caseData.violationStartDate) unknown.push('위반 시작일');
  }
  if (caseData.priorViolations === null || caseData.priorViolations === undefined) unknown.push('과거 위반 전력');
  if (caseData.voluntaryDisclosure === null || caseData.voluntaryDisclosure === undefined) unknown.push('자진신고 여부');
  if (caseData.investigationStarted === null || caseData.investigationStarted === undefined) unknown.push('사범조사 시작 여부');
  return [...new Set(unknown)];
}

function extractStructuredCase(text, assessmentDate) {
  const clean = String(text || '').trim().slice(0, MAX_CASE_TEXT).replace(/\s+/g, ' ');
  if (!clean) throw new Error('case text is required');

  const warnings = [];
  if (containsSensitiveIdentifier(clean)) {
    warnings.push('분석에 불필요한 개인식별정보가 감지되어 구조화 결과에 포함하지 않았습니다.');
  }

  const statusOfStay = extractStatus(clean);
  let durationDays = extractDurationDays(clean);
  const { violationStartDate, violationEndDate } = extractDates(clean, assessmentDate);
  if (violationStartDate && violationEndDate) {
    const start = parseIsoDate(violationStartDate);
    const end = parseIsoDate(violationEndDate);
    if (start && end && end >= start) durationDays = daysInclusive(start, end);
  }

  const { violationCode, violationCandidates, unauthorized, work, workplaceChange } = classifyViolation(clean, statusOfStay);

  let priorViolations = null;
  if (FIRST_OFFENSE_RE.test(clean)) priorViolations = 0;
  else {
    const priorMatch = clean.match(PRIOR_COUNT_RE);
    if (priorMatch) priorViolations = Number(priorMatch[1]);
  }

  const voluntaryDisclosure = VOLUNTARY_RE.test(clean) ? true : null;
  const investigationStarted = INVESTIGATION_RE.test(clean) ? true : null;
  const falseRepresentation = FALSE_REPRESENTATION_RE.test(clean) ? true : null;

  let authorizationObtained = null;
  if (unauthorized) authorizationObtained = false;
  else if (EXPLICIT_AUTHORIZED_RE.test(clean)) authorizationObtained = true;

  let workplaceChangeAuthorized = null;
  if (workplaceChange) {
    if (/(?:변경|추가)\s*(?:허가|신고).*(?:안\s*했|안\s*받|없이|미허가|미신고)/i.test(clean)) workplaceChangeAuthorized = false;
    else if (/(?:변경|추가)\s*(?:허가|신고).*(?:받았|했음|완료)/i.test(clean)) workplaceChangeAuthorized = true;
    else if (unauthorized) workplaceChangeAuthorized = false;
  }

  const caseData = {
    schemaVersion: '1',
    statusOfStay,
    violationCode,
    violationCandidates,
    activity: work ? '취업활동' : null,
    workplaceType: clean.includes('음식점') ? '음식점' : null,
    authorizationObtained,
    workplaceChangeAuthorized,
    durationDays,
    violationStartDate,
    violationEndDate,
    assessmentDate: assessmentDate || todayIso(),
    priorViolations,
    voluntaryDisclosure,
    investigationStarted,
    falseRepresentation,
    extractionWarnings: warnings,
  };
  caseData.unknownFacts = unknownFactsFor(caseData);

  return omitNullish(caseData);
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
  classifyViolation,
  unknownFactsFor,
  AMBIGUOUS_WORK_RELATION_FACT,
  ALLOWED_VIOLATION_CODES,
};
