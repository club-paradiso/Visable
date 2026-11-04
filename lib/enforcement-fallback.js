'use strict';

const rulesDb = require('../backend/data/enforcement/legal_rules.json');
const { factualText, eventValue, relevantDurationText } = require('./enforcement-language');
const { determineWorkplaceRegime, WORKPLACE_VIOLATION_CODES } = require('./enforcement-workplace');

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
  // Korean particles attach directly to identifiers ("M12345678입니다"), where
  // \b never fires; use lookarounds instead. Mirrors enforcement_service.py.
  return [
    /(?<![A-Z0-9])[A-Z]\d{8}(?!\d)/i,
    /(?<!\d)\d{6}[- ]?[1-8]\d{6}(?!\d)/,
    /(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)/,
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
const WORKPLACE_OVERLAP_CODES = [
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
  + '|(?:신고|등록)(?:를|도)?\\s*(?:안\\s*했|하지\\s*않았|못\\s*했)'
  + '|(?:변경|추가)\\s*신고\\s*없이'
  + '|취업\\s*(?:불가|금지)',
  'i',
);
const WORK_RE = new RegExp(
  '일했|일함|일한|일하고|일하다|근무|아르바이트|알바|취업|고용|돈\\s*벌'
  + '|사업장|근무처|음식점|공장|건설|회사|업체',
  'i',
);
const OVERSTAY_RE = new RegExp(
  '체류기간.*(?:넘|초과|만료|지났)'
  + '|기간\\s*만료.*(?:후|지났|넘)'
  + '|만료(?:일)?\\s*(?:후|지났|넘)'
  + '|(?:비자|체류|체류기간|기간)\\s*(?:이|가)?\\s*만료\\s*(?:되고|됐는데|되었는데|된\\s*(?:뒤|후|지|채))'
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
// 취업활동 체류자격자가 "다른 사업장/회사"에서 일했다는 서술: 지정 근무처 밖 근무
// (제18조제2항)의 표지다. 변경·추가 신호가 함께 있으면 제21조제1항이 우선한다.
// backend/services/enforcement_service.py의 _OTHER_WORKPLACE_RE와 같아야 한다.
const OTHER_WORKPLACE_RE = /다른\s*(?:근무처|사업장|회사|업체)/i;
const EXPLICIT_NO_WORK_STATUS_RE = new RegExp(
  '취업활동을?\\s*(?:할\\s*수\\s*)?없는\\s*체류자격'
  + '|취업\\s*(?:불가|금지)\\s*체류자격'
  + '|취업자격\\s*(?:이\\s*)?없',
  'i',
);
const FIRST_OFFENSE_RE = new RegExp(
  '처음(?:이고|입니다|이에요|이예요)|이번이\\s*처음|초범|첫\\s*(?:위반|적발)|전력\\s*(?:없|0)|위반\\s*이력\\s*없'
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
  const statuses = [...clean.matchAll(new RegExp(STATUS_RE.source, 'gi'))];
  if (new Set(statuses.map((m) => `${m[1].toUpperCase()}-${Number(m[2])}${m[3] ? `-${Number(m[3])}` : ''}`)).size > 1) return null;
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
  const scrubbed = relevantDurationText(clean.replace(FULL_DATE_RE, ' '));
  if ((scrubbed.match(/(?:\d+\s*(?:개월|일|주|달|년)\s*)+/g) || []).length > 1) return null;

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

function classifyViolation(clean, status, includeOverstay = true) {
  clean = factualText(clean);
  const unauthorized = UNAUTHORIZED_RE.test(clean);
  const work = WORK_RE.test(clean);
  const overstay = OVERSTAY_RE.test(clean);
  const workplaceChange = WORKPLACE_CHANGE_RE.test(clean);
  const explicitDesignatedWorkplace = OUTSIDE_DESIGNATED_WORKPLACE_RE.test(clean);
  const outsideDesignatedWorkplace = explicitDesignatedWorkplace || OTHER_WORKPLACE_RE.test(clean);
  const explicitNoWorkStatus = EXPLICIT_NO_WORK_STATUS_RE.test(clean);
  const normalizedStatus = String(status || '').toUpperCase();

  if (overstay && includeOverstay && work && unauthorized) {
    const workResult = classifyViolation(clean, status, false);
    return { violationCode: null, violationCandidates: [...new Set(['OVERSTAY_ART25', ...workResult.violationCandidates])], unauthorized, work, workplaceChange };
  }
  if (overstay && includeOverstay) {
    return { violationCode: 'OVERSTAY_ART25', violationCandidates: ['OVERSTAY_ART25'], unauthorized, work, workplaceChange };
  }
  if (!(work && unauthorized)) {
    return { violationCode: null, violationCandidates: [], unauthorized, work, workplaceChange };
  }

  // 명시적인 조문 표지가 있을 때만 조문을 확정한다. 분기 순서는
  // backend/services/enforcement_service.py의 _classify_violation과 동일해야 한다.
  // 제18조제2항 표지와 제21조제1항 표지가 함께 서술되면 승자를 정하지 않고 두 후보만
  // 남긴다: 제21조제3항에 따라 같은 조 제1항 단서(신고 대상자)에 해당하는지가 결정적
  // 사실이고, 그 사실은 문장만으로 알 수 없다(이슈 #587).
  if (!STUDY_STATUS_RE.test(normalizedStatus) && workplaceChange && explicitDesignatedWorkplace) {
    return {
      violationCode: null,
      violationCandidates: [...WORKPLACE_OVERLAP_CODES],
      unauthorized,
      work,
      workplaceChange,
    };
  }
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

// Conservative narrative extraction of workplace-change facts; mirrors
// _extract_workplace_facts in backend/services/enforcement_service.py.
// Ambiguous statements stay null so the UI can ask instead of guessing.
function extractWorkplaceFacts(clean, work) {
  const facts = {};
  let occupation = null;
  const codeMatch = clean.match(/직종\s*코드?\s*[:：]?\s*\(?\s*(S?\d{3,5})\s*\)?/i);
  if (codeMatch) occupation = codeMatch[1].toUpperCase();
  else {
    for (const [pattern, code] of [
      [/주방장|조리사/, '441'],
      [/조선\s*용접|용접공/, '7430'],
      [/기계공학\s*기술자/, '2351'],
      [/제도사/, '2395'],
      [/의료\s*코디네이터/, 'S3922'],
      [/호텔\s*접수\s*사무원/, '3922'],
      [/고객\s*상담\s*사무원/, '3991'],
      [/판매\s*사무원/, '31215'],
      [/양식\s*기술자/, '6301'],
    ]) {
      if (pattern.test(clean)) { occupation = code; break; }
    }
  }
  facts.occupationCode = occupation;

  if (/(?:같은|동일한)\s*(?:회사|고용주|업체).{0,12}(?:장소|지점|사업장)만/.test(clean)) facts.workplaceChangeType = 'SAME_EMPLOYER_SITE_ONLY';
  else if (/(?:근무처|사업장|회사|업체)(?:를|을)?\s*추가|추가로\s*(?:일|근무)|겸업|투잡/.test(clean)) facts.workplaceChangeType = 'ADDITION';
  else if (/옮겼|옮긴|이직|그만두고.{0,10}(?:다른|새)/.test(clean)) facts.workplaceChangeType = 'CHANGE';
  else facts.workplaceChangeType = null;

  let endReason = null;
  if (/계약\s*(?:이|기간)?\s*(?:만료|끝나|종료돼|종료되)/.test(clean)) endReason = 'CONTRACT_EXPIRED';
  else if (/폐업|회사가\s*문을\s*닫|사업장\s*폐쇄/.test(clean)) endReason = 'EMPLOYER_CLOSED';
  else if (/(?:본인|자신)\s*(?:잘못|귀책)|징계\s*해고|귀책\s*사유/.test(clean)) endReason = 'DISMISSED_OWN_FAULT';
  else if (/회사\s*사정으로\s*(?:해고|그만)|회사\s*사정으로\s*나오|권고사직/.test(clean)) endReason = 'DISMISSED_NO_OWN_FAULT';
  else if (/본인이\s*(?:그만|사직|퇴사)|스스로\s*(?:그만|사직|퇴사)|중도에\s*(?:그만|퇴사)/.test(clean)) endReason = 'RESIGNED_MID_CONTRACT';
  else if (facts.workplaceChangeType === 'ADDITION') endReason = 'NOT_ENDED';
  facts.previousEmploymentEndReason = endReason;

  if (/(?:이적|옮기[는니])\s*(?:것)?(?:에)?\s*동의(?:를|도)?\s*(?:받았|받음|했|해\s*줬)/.test(clean)) facts.employerConsent = true;
  else if (/동의(?:를|도)?\s*(?:안\s*받|못\s*받|받지\s*못|없(?:이|었))/.test(clean)) facts.employerConsent = false;
  else facts.employerConsent = null;

  if (/외국인\s*등록(?:을|도)?\s*(?:했|하고|한\s*상태)|등록증(?:이|을)\s*(?:있|발급받)/.test(clean)) facts.alienRegistered = true;
  else if (/외국인\s*등록(?:을|도)?\s*(?:안\s*했|못\s*했|하지\s*않)|등록\s*전(?:이|에)/.test(clean)) facts.alienRegistered = false;
  else facts.alienRegistered = null;

  if (/자격\s*요건(?:을|도)?\s*(?:갖추|충족)/.test(clean)) facts.meetsNewWorkplaceQualifications = true;
  else if (/자격\s*요건(?:에)?\s*(?:미달|안\s*돼|못\s*미치)/.test(clean)) facts.meetsNewWorkplaceQualifications = false;
  else facts.meetsNewWorkplaceQualifications = null;

  if (/(?:아직|아닌)\s*(?:일|근무)(?:을|를)?\s*시작하지\s*않|근무\s*시작\s*전(?:이|이라)/.test(clean)) facts.actuallyStartedWork = false;
  else if (work && /일했|근무했|일하기\s*시작|근무를\s*시작|근무\s*중/.test(clean)) facts.actuallyStartedWork = true;
  else facts.actuallyStartedWork = null;

  if (/(?:변경|추가)\s*허가(?:를|도)?\s*(?:받았|받음|취득)/.test(clean)) facts.procedureStatus = 'PERMIT_GRANTED';
  else if (/(?:변경|추가)?\s*신고(?:를|도)?\s*(?:했|완료|마쳤)/.test(clean)) facts.procedureStatus = 'REPORT_FILED';
  else if (/(?:허가|신고)\s*신청(?:을|도)?\s*(?:했|넣었).{0,12}(?:대기|처리\s*중|심사\s*중)|심사\s*중/.test(clean)) facts.procedureStatus = 'APPLIED_PENDING';
  else if (/(?:허가|신고)(?:를|도)?\s*(?:안\s*했|하지\s*않았|못\s*했)|아무것도\s*안\s*했|신고도\s*안\s*했/.test(clean)) facts.procedureStatus = 'NONE';
  else facts.procedureStatus = null;

  return facts;
}

function extractStructuredCase(text, assessmentDate) {
  const clean = String(text || '').trim().slice(0, MAX_CASE_TEXT).replace(/\s+/g, ' ');
  if (!clean) throw new Error('case text is required');

  const warnings = [];
  if (containsSensitiveIdentifier(clean)) {
    warnings.push('분석에 불필요한 개인식별정보가 감지되어 구조화 결과에 포함하지 않았습니다.');
  }

  const facts = factualText(clean);
  const statusOfStay = extractStatus(facts);
  let durationDays = extractDurationDays(facts);
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

  const voluntaryDisclosure = eventValue(clean, VOLUNTARY_RE);
  const investigationStarted = eventValue(clean, /(?:사범)?조사|적발|단속|걸렸|출입국.{0,12}(?:연락|통보)/i);
  const falseRepresentation = eventValue(clean, FALSE_REPRESENTATION_RE);

  let authorizationObtained = null;
  if (unauthorized) authorizationObtained = false;
  else if (EXPLICIT_AUTHORIZED_RE.test(clean)) authorizationObtained = true;

  let workplaceChangeAuthorized = null;
  if (workplaceChange) {
    if (/(?:변경|추가)\s*(?:허가|신고).*(?:안\s*했|안\s*받|없이|미허가|미신고)/i.test(clean)) workplaceChangeAuthorized = false;
    else if (/(?:변경|추가)\s*(?:허가|신고).*(?:받았|했음|완료)/i.test(clean)) workplaceChangeAuthorized = true;
    else if (unauthorized) workplaceChangeAuthorized = false;
  }

  if (violationCandidates.length > 1 && violationCandidates.includes('OVERSTAY_ART25')) warnings.push('초과체류와 취업 관련 사실이 함께 있어 위반별 기간과 적용 관계를 각각 확인해야 합니다.');
  if ((facts.match(new RegExp(STATUS_RE.source, 'gi')) || []).length > 1 && !statusOfStay) warnings.push('여러 체류자격이 언급되어 위반 당시의 체류자격을 확인해야 합니다.');
  const workplaceFacts = extractWorkplaceFacts(clean, work);
  const caseData = {
    schemaVersion: '1',
    statusOfStay,
    violationCode,
    violationCandidates,
    activity: work ? '취업활동' : null,
    workplaceType: clean.includes('음식점') ? '음식점' : null,
    authorizationObtained,
    workplaceChangeAuthorized,
    occupationCode: workplaceFacts.occupationCode,
    workplaceChangeType: workplaceFacts.workplaceChangeType,
    previousEmploymentEndReason: workplaceFacts.previousEmploymentEndReason,
    employerConsent: workplaceFacts.employerConsent,
    alienRegistered: workplaceFacts.alienRegistered,
    meetsNewWorkplaceQualifications: workplaceFacts.meetsNewWorkplaceQualifications,
    actuallyStartedWork: workplaceFacts.actuallyStartedWork,
    procedureStatus: workplaceFacts.procedureStatus,
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

// A day-count alone cannot always determine a calendar-month tier.
// Find the exact inclusive-day threshold range over a full leap-year cycle.
// If different start dates would select different tiers, require actual dates.
// Do not silently treat 30 days as one legal calendar month.
function ambiguousCalendarBoundary(tiers, durationDays) {
  const thresholds = [...new Set(tiers.map((row) => Number(row.minimumMonths)))]
    .filter((months) => Number.isInteger(months) && months > 0 && months <= 120);
  for (const months of thresholds) {
    let shortest = Infinity;
    let longest = -Infinity;
    for (let year = 2024; year <= 2027; year++) {
      for (let month = 0; month < 12; month++) {
        const days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
        for (let day = 1; day <= days; day++) {
          const start = new Date(Date.UTC(year, month, day));
          const threshold = daysInclusive(start, addMonthsUtc(start, months));
          shortest = Math.min(shortest, threshold);
          longest = Math.max(longest, threshold);
        }
      }
    }
    if (durationDays >= shortest && durationDays < longest) return true;
  }
  return false;
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

// Mirrors backend/services/enforcement_rules.py (REPORT_PROVISO_NOTE, SHARED_TIER_NOTE,
// _shared_candidate_rule). 출입국관리법 제21조제1항 단서·제3항, 시행령 제26조의2.
const REPORT_PROVISO_STATUS_RE = /^E-[1-7](?:-|$)/i;
const WORKPLACE_CODES = new Set(['UNAUTHORIZED_EMPLOYMENT_ART18_2', 'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1']);
const REPORT_PROVISO_NOTE = "이 금액은 근무처 변경·추가 '허가' 대상자 기준입니다. E-1~E-7 중 법무부장관 고시 요건을 갖춘 "
  + "'신고' 대상자라면 제18조제2항은 적용되지 않고(출입국관리법 제21조제3항, 시행령 제26조의2), "
  + '신고의무 위반은 범칙금이 아니라 과태료(같은 법 제100조제1항제3호, 200만원 이하) 대상입니다.';
const PERMIT_CONFIRMATION_NOTE = '근무처 변경·추가가 사전허가 대상이라는 사용자의 확인을 전제로 한 조건부 계산입니다. '
  + '출입국관서의 최종 법적 분류를 의미하지 않습니다.';
const SHARED_TIER_NOTE = '제18조제2항과 제21조제1항 중 어느 조문이 적용되는지는 정해지지 않았지만, 두 조문의 범칙금 '
  + '양정기준(출입국관리법 시행규칙 별표 7 더목·저목)이 같아 기준 금액은 같습니다.';

function reportProvisoApplies(status, codes) {
  if (!codes.some((code) => WORKPLACE_CODES.has(code))) return false;
  return !status || REPORT_PROVISO_STATUS_RE.test(String(status));
}

function sharedCandidateRules(caseData, snapshot) {
  const candidates = [...new Set(caseData.violationCandidates || [])];
  if (candidates.length < 2) return null;
  const rules = candidates.map((code) => snapshot.rules.find((row) => row.violationCode === code));
  if (rules.some((rule) => !rule)) return null;
  const key = (rule) => JSON.stringify([rule.tiers, rule.statutoryMaximumKrw]);
  return rules.every((rule) => key(rule) === key(rules[0])) ? rules : null;
}

function calculateLegalBaseline(caseData) {
  // Workplace determination runs BEFORE the fine-snapshot resolution,
  // mirroring backend/services/enforcement_rules.py: its terminal outcomes
  // do not depend on the 범칙금 snapshot and must not be masked by
  // HISTORICAL_RULE_UNAVAILABLE for pre-snapshot incidents.
  const workplaceCodes = caseData.violationCode ? [caseData.violationCode] : (caseData.violationCandidates || []);
  const workplaceGate = workplaceCodes.some((code) => WORKPLACE_VIOLATION_CODES.has(code))
    && (Boolean(caseData.violationCode) || workplaceCodes.every((code) => WORKPLACE_VIOLATION_CODES.has(code)));
  let determination = workplaceGate ? determineWorkplaceRegime(caseData) : null;

  const snapshot = resolveSnapshot(caseData);
  const sources = snapshot ? sourceRefs(snapshot) : [];

  if (determination) {
    const inEngineScope = !caseData.statusOfStay || REPORT_PROVISO_STATUS_RE.test(String(caseData.statusOfStay));
    if (determination.regime === 'UNRESOLVED' && !inEngineScope) determination = null;
  }
  if (determination) {
    const common = {
      violationCode: caseData.violationCode || null,
      legalSnapshotId: snapshot ? snapshot.id : null,
      effectiveFrom: snapshot ? snapshot.effectiveFrom : null,
      sources: snapshot ? sources : determination.evidence,
      workplaceDetermination: determination,
    };
    if (determination.regime === 'NOT_APPLICABLE'
        || (['CONFIRMED', 'USER_CONFIRMED'].includes(determination.determinationStatus) && determination.dutyBreach === 'NOT_ESTABLISHED')) {
      return {
        ...common,
        status: 'NOT_APPLICABLE',
        missingFacts: [],
        assumptions: ['확인된 사실만으로는 근무처 변경·추가 의무 위반이 성립하지 않아 범칙금·과태료를 계산하지 않습니다.'],
        confidence: 'HIGH',
      };
    }
    if (determination.regime === 'REPORT' && ['CONFIRMED', 'USER_CONFIRMED'].includes(determination.determinationStatus)) {
      return {
        ...common,
        status: 'ADMINISTRATIVE_FINE_TRACK',
        statutoryMaximumKrw: determination.administrativeFineStatutoryMaximumKrw,
        appliedRules: [
          '출입국관리법 제21조제1항 단서(사후신고 의무)',
          '출입국관리법 시행령 제26조의2',
          '법무부고시 제2020-212호(신고 대상 요건)',
          '출입국관리법 제100조제1항제3호(과태료, 200만원 이하)',
        ],
        missingFacts: [...determination.missingFacts],
        assumptions: ['사후신고 의무 위반은 범칙금이 아니라 과태료 검토 대상입니다. 위 금액은 법정 상한이며, 검증된 과태료 양정기준이 없어 구체적인 산정액은 제시하지 않습니다.'],
        confidence: determination.dutyBreach === 'ESTABLISHED' ? 'HIGH' : 'INSUFFICIENT',
      };
    }
    if (determination.regime === 'UNRESOLVED' && !determination.missingFacts.includes('사건 당시 고시 버전')) {
      return {
        ...common,
        status: 'MISSING_FACTS',
        missingFacts: ['근무처 변경·추가가 사전허가 대상인지 사후신고 대상인지 확정할 수 없습니다.', ...determination.missingFacts],
        confidence: 'INSUFFICIENT',
      };
    }
    if (determination.regime === 'PERMIT' && determination.determinationStatus === 'CONFIRMED' && determination.dutyBreach === 'UNRESOLVED') {
      // Engine-confirmed permission duty + unproven breach: no amount.
      return {
        ...common,
        status: 'MISSING_FACTS',
        missingFacts: ['근무처 변경·추가 허가를 받았는지 확인되지 않았습니다.', ...determination.missingFacts],
        confidence: 'INSUFFICIENT',
      };
    }
    if (!caseData.violationCode && determination.determinationStatus === 'USER_CONFIRMED') {
      return {
        ...common,
        status: 'MISSING_FACTS',
        missingFacts: ['적용 조문이 확정되지 않아, 사용자 확인만으로는 조건부 계산을 하지 않습니다.', ...determination.missingFacts],
        confidence: 'INSUFFICIENT',
      };
    }
  }

  if (!snapshot) {
    return omitNullish({
      status: 'HISTORICAL_RULE_UNAVAILABLE',
      violationCode: caseData.violationCode || null,
      missingFacts: ['해당 위반기간 전체에 적용되는 검증된 법령 스냅샷'],
      confidence: 'INSUFFICIENT',
      workplaceDetermination: determination,
    });
  }
  const sharedRules = caseData.violationCode ? null : sharedCandidateRules(caseData, snapshot);
  if (!caseData.violationCode && !sharedRules) {
    return {
      status: 'MISSING_FACTS',
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      missingFacts: ['위반 유형'],
      sources,
      confidence: 'INSUFFICIENT',
      workplaceDetermination: determination,
    };
  }

  const rule = sharedRules ? sharedRules[0] : snapshot.rules.find((row) => row.violationCode === caseData.violationCode);
  if (!rule) {
    return {
      status: 'UNSUPPORTED',
      violationCode: caseData.violationCode,
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      sources,
      confidence: 'INSUFFICIENT',
      workplaceDetermination: determination,
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
      workplaceDetermination: determination,
    };
  }

  if (!(caseData.violationStartDate && caseData.violationEndDate)
      && ambiguousCalendarBoundary(rule.tiers, Number(durationDays))) {
    return {
      status: 'MISSING_FACTS',
      violationCode: caseData.violationCode || null,
      violationLabel: sharedRules ? sharedRules.map((row) => row.label).join(' 또는 ') : rule.label,
      legalSnapshotId: snapshot.id,
      effectiveFrom: snapshot.effectiveFrom,
      missingFacts: ['월 단위 범칙금 구간의 경계입니다. 정확한 위반 시작일과 종료일이 필요합니다.'],
      sources,
      confidence: 'INSUFFICIENT',
      workplaceDetermination: determination,
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
  const codes = sharedRules ? sharedRules.map((row) => row.violationCode) : [caseData.violationCode];
  if (sharedRules) assumptions.push(SHARED_TIER_NOTE);
  if (determination && determination.regime === 'PERMIT') {
    if (determination.determinationStatus === 'USER_CONFIRMED') assumptions.push(PERMIT_CONFIRMATION_NOTE);
    else if (determination.determinationStatus === 'CONFIRMED') assumptions.push('법무부고시 제2020-212호 요건·적용제외를 확인한 결과 사전허가 대상으로 판별되어 범칙금 기준으로 계산했습니다.');
  } else if (reportProvisoApplies(caseData.statusOfStay, codes)) {
    assumptions.push(PERMIT_CONFIRMATION_NOTE);
  }
  const appliedRules = (sharedRules ? sharedRules.map((row) => row.statuteArticle) : [rule.statuteArticle])
    .concat([rule.penaltyArticle, '출입국관리법 시행규칙 제86조(가중·감경 범위)']);

  return {
    status: 'AVAILABLE',
    violationCode: caseData.violationCode || null,
    violationLabel: sharedRules ? `${sharedRules.map((row) => row.label).join(' 또는 ')} (조문 미확정)` : rule.label,
    baselineAmountKrw,
    legallyAdjustableRange: { minimumKrw, maximumKrw, currency: 'KRW' },
    statutoryMaximumKrw,
    durationDays: Number(durationDays),
    legalSnapshotId: snapshot.id,
    effectiveFrom: snapshot.effectiveFrom,
    appliedRules,
    legallyAvailableDispositions: availableDispositions(codes[0]),
    assumptions,
    missingFacts: [],
    sources,
    confidence: assumptions.length ? 'HIGH' : 'VERY_HIGH',
    workplaceDetermination: determination,
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
    workplaceDetermination: baseline.workplaceDetermination || null,
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
  REPORT_PROVISO_NOTE,
  PERMIT_CONFIRMATION_NOTE,
  SHARED_TIER_NOTE,
};
