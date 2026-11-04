'use strict';

// Deterministic workplace change/addition regime determination.
// Mirrors backend/services/enforcement_workplace.py exactly; parity is
// verified against backend/tests/fixtures/workplace_regime_cases.json by
// scripts/check_enforcement_workplace.mjs. Rules come from the verified
// rule store backend/data/enforcement/workplace_regime_rules.json
// (MOJ Notice 2020-212, Immigration Act Art.21/100, Decree Art.26-2).
// See the Python module for the legal reasoning and hard rules.

const rules = require('../backend/data/enforcement/workplace_regime_rules.json');

const WORKPLACE_VIOLATION_CODES = new Set([
  'UNAUTHORIZED_EMPLOYMENT_ART18_2',
  'UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1',
]);
const ELIGIBLE_STATUS_RE = /^E-[1-7](?:-|$)/i;
const OWN_FAULT_REASONS = new Set(['DISMISSED_OWN_FAULT', 'RESIGNED_MID_CONTRACT']);
const CLEAR_NON_OWN_FAULT_REASONS = new Set([
  'CONTRACT_EXPIRED', 'DISMISSED_NO_OWN_FAULT', 'EMPLOYER_CLOSED', 'NOT_ENDED',
]);

const NEXT_QUESTIONS = {
  '체류자격': '변경 당시 어떤 비자(체류자격)로 체류했나요?',
  '실제 직종(직종코드)': '새 근무처에서 실제로 어떤 일을 하나요? 직종코드(예: 441)를 알면 알려 주세요.',
  'E-6 세부 유형': 'E-6 중 호텔·유흥시설 공연(E-6-2)에 해당하나요?',
  '해외 온라인상품판매원 해당 여부': '해외 온라인상품 판매 업무를 하나요?',
  '외국인등록 여부': '당시 외국인등록을 하고 체류 중이었나요?',
  '외국인등록 전 신고 예외(1회) 사용 여부': '외국인등록 전에 신고할 수 있는 예외(1회)를 이전에 사용한 적이 있나요?',
  '새 근무처 자격요건 충족 여부': '새 근무처에서 일하는 데 필요한 자격요건(학위·자격 등)을 갖추었나요?',
  '이전 고용 종료 사유': '이전 회사는 왜 그만두게 됐나요? (계약 만료, 본인이 중도에 그만둠, 해고, 회사 폐업 등)',
  '원 고용주 이적 동의 여부': '이전 회사에서 다른 회사로 옮기는 것에 동의받았나요?',
  '근무처 변경일': '새 근무처로 옮기거나 추가한 날짜가 언제인가요?',
  '신고일': '출입국관서에 신고한 날짜가 언제인가요?',
  '허가 취득 여부': '근무를 시작하기 전에 출입국관서에서 근무처 변경·추가 허가를 받았나요?',
  '행정 절차 진행 여부': '출입국관서에 허가 신청이나 신고를 한 적이 있나요?',
  '사건 당시 고시 버전': '사건 날짜를 기준으로 당시 시행 고시를 확인해야 합니다. 변경 날짜를 알려 주세요.',
};

function evidenceRefs() {
  return rules.sources.map((source) => ({
    id: `workplace-regime:${source.id}`,
    authority: source.authority,
    title: source.lawName,
    article: source.article || null,
    effectiveDate: source.effectiveFrom,
    url: source.url,
    verifiedAt: rules.verifiedAt,
  }));
}

function addDaysIso(iso, days) {
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return null;
  // Reject overflow-normalized dates ("2026-13-40" parses to a valid but
  // different day in some engines) by round-tripping the components.
  const roundTrip = date.toISOString().slice(0, 10);
  if (roundTrip !== iso) return null;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function finish(det) {
  det.missingFacts = [...new Set(det.missingFacts)];
  det.nextQuestions = det.missingFacts.map((fact) => NEXT_QUESTIONS[fact]).filter(Boolean);
  return det;
}

function baseDetermination() {
  const notice = rules.sources[0];
  return {
    regime: 'UNRESOLVED',
    determinationStatus: 'UNRESOLVED',
    determinationSource: 'ENGINE',
    verifiedFacts: [],
    missingFacts: [],
    applicableRules: [
      '출입국관리법 제21조제1항(본문: 사전허가 / 단서: 대통령령으로 정하는 사람의 15일 이내 사후신고)',
      '출입국관리법 시행령 제26조의2제1항(신고 대상: E-1~E-7 중 법무부장관 고시 요건 충족자)',
      '법무부고시 제2020-212호(신고만으로 근무처 변경·추가를 할 수 있는 외국인의 요건)',
    ],
    exceptionsChecked: [],
    effectiveLawVersion: `${notice.lawName} (${notice.noticeNo}, 시행 ${notice.effectiveFrom})`,
    evidence: evidenceRefs(),
    warnings: [],
    nextQuestions: [],
    humanReviewReason: null,
    penaltyTrack: 'UNRESOLVED',
    dutyBreach: 'UNRESOLVED',
    reportDeadlineDate: null,
    reportTimeliness: null,
    administrativeFineStatutoryMaximumKrw: null,
  };
}

function assessBreach(caseData, regime, det) {
  const procedure = caseData.procedureStatus || null;
  if (regime === 'PERMIT') {
    det.penaltyTrack = 'CRIMINAL_FINE';
    // An explicitly stated procedure always outranks the legacy authorized
    // flag; a report filing is not a permit and never satisfies this duty.
    if (procedure === 'PERMIT_GRANTED') {
      det.dutyBreach = 'NOT_ESTABLISHED';
    } else if (procedure === 'APPLIED_PENDING') {
      det.dutyBreach = 'UNRESOLVED';
      det.warnings.push('허가 신청만으로는 허가를 받은 것이 아닙니다. 처리 결과가 확인되어야 합니다.');
    } else if (procedure === 'REPORT_FILED' || procedure === 'NONE') {
      det.dutyBreach = 'ESTABLISHED';
    } else if (caseData.workplaceChangeAuthorized === true) {
      det.dutyBreach = 'NOT_ESTABLISHED';
    } else if (caseData.workplaceChangeAuthorized === false) {
      det.dutyBreach = 'ESTABLISHED';
    } else {
      det.dutyBreach = 'UNRESOLVED';
      if (!det.missingFacts.includes('허가 취득 여부')) det.missingFacts.push('허가 취득 여부');
    }
    return;
  }
  if (regime === 'REPORT') {
    det.penaltyTrack = 'ADMINISTRATIVE_FINE';
    det.administrativeFineStatutoryMaximumKrw = Number(rules.reportDuty.statutoryMaximumKrw);
    let changeDate = caseData.workplaceChangeDate || caseData.newWorkplaceStartDate || caseData.violationStartDate || null;
    if (changeDate) {
      const deadline = addDaysIso(changeDate, Number(rules.reportDuty.deadlineDays));
      if (deadline === null) {
        // Unparseable date: treat as missing rather than crashing or
        // comparing against a fabricated deadline.
        changeDate = null;
        if (!det.missingFacts.includes('근무처 변경일')) det.missingFacts.push('근무처 변경일');
      } else {
        det.reportDeadlineDate = deadline;
      }
    }
    if (procedure === 'REPORT_FILED') {
      const reportDate = caseData.applicationOrReportDate || null;
      if (reportDate && changeDate) {
        if (reportDate <= det.reportDeadlineDate) {
          det.reportTimeliness = 'WITHIN_DEADLINE';
          det.dutyBreach = 'NOT_ESTABLISHED';
        } else {
          det.reportTimeliness = 'LATE';
          det.dutyBreach = 'ESTABLISHED';
        }
      } else {
        det.reportTimeliness = 'UNKNOWN';
        det.dutyBreach = 'UNRESOLVED';
        if (!changeDate) det.missingFacts.push('근무처 변경일');
        if (!reportDate) det.missingFacts.push('신고일');
      }
    } else if (procedure === 'NONE') {
      const reference = caseData.assessmentDate || new Date().toISOString().slice(0, 10);
      if (changeDate && reference > det.reportDeadlineDate) {
        det.reportTimeliness = 'NOT_REPORTED_DEADLINE_PASSED';
        det.dutyBreach = 'ESTABLISHED';
      } else {
        det.reportTimeliness = 'UNKNOWN';
        det.dutyBreach = 'UNRESOLVED';
        if (!changeDate) det.missingFacts.push('근무처 변경일');
        else det.warnings.push('아직 신고기한(변경일부터 15일)이 지나지 않았을 수 있어 위반으로 확정하지 않습니다.');
      }
    } else if (procedure === 'PERMIT_GRANTED') {
      det.dutyBreach = 'NOT_ESTABLISHED';
      det.warnings.push('사전허가를 받았다면 신고의무 위반 쟁점은 별도로 발생하지 않습니다.');
    } else {
      det.reportTimeliness = 'UNKNOWN';
      det.dutyBreach = 'UNRESOLVED';
      if (!det.missingFacts.includes('행정 절차 진행 여부')) det.missingFacts.push('행정 절차 진행 여부');
    }
  }
}

function normalizeOccupation(value) {
  if (!value) return null;
  return String(value).replace(/[\s.\-]+/g, '').toUpperCase() || null;
}

function engineDetermine(caseData) {
  const eligibility = rules.reportEligibility;
  const det = baseDetermination();

  if (caseData.workplaceChangeType === 'SAME_EMPLOYER_SITE_ONLY') {
    det.warnings.push('같은 고용주 안에서 근무 장소만 바뀐 경우도 근무처 변경에 해당할 수 있어, 비대상이라고 단정하지 않습니다.');
  }

  const status = String(caseData.statusOfStay || '').toUpperCase();
  if (!status) {
    det.missingFacts.push('체류자격');
    return finish(det);
  }
  det.verifiedFacts.push(`체류자격 ${status}`);

  const changeDate = caseData.workplaceChangeDate || caseData.newWorkplaceStartDate || caseData.violationStartDate || null;
  const noticeSource = rules.sources.find((source) => source.id === 'moj-notice-2020-212');
  if (changeDate && changeDate < noticeSource.effectiveFrom) {
    det.missingFacts.push('사건 당시 고시 버전');
    det.humanReviewReason = '근무처 변경일이 고시 제2020-212호 시행일(2020-06-22)보다 빨라, 사건 당시 고시 버전을 검증된 스냅샷으로 확인할 수 없습니다.';
    return finish(det);
  }

  if (eligibility.excludedStatuses.includes(status)) {
    det.regime = 'PERMIT';
    det.determinationStatus = 'CONFIRMED';
    det.exceptionsChecked.push('고시 적용제외: 예술흥행(E-6) 중 호텔업시설·유흥업소 등 공연 종사자(E-6-2)는 신고 대상에서 제외');
    det.verifiedFacts.push('E-6-2는 고시상 신고 적용제외 대상');
    assessBreach(caseData, 'PERMIT', det);
    return finish(det);
  }

  if (!ELIGIBLE_STATUS_RE.test(status)) {
    det.humanReviewReason = '검증된 고시 규칙은 E-1~E-7 체류자격의 신고 대상 판별만 다룹니다. 그 밖의 체류자격은 이 엔진으로 사전허가/사후신고를 확정하지 않습니다.';
    return finish(det);
  }

  let unresolved = false;
  const endReason = caseData.previousEmploymentEndReason || null;

  if (status.startsWith('E-7')) {
    const occupation = normalizeOccupation(caseData.occupationCode);
    if (!occupation) {
      det.missingFacts.push('실제 직종(직종코드)');
      unresolved = true;
    } else if (Object.hasOwn(eligibility.conditionalOccupationCodesE7, occupation)) {
      if (caseData.overseasOnlineSeller === true) {
        det.regime = 'PERMIT';
        det.determinationStatus = 'CONFIRMED';
        det.exceptionsChecked.push('고시 적용제외: E-7 직종코드 2742 중 해외 온라인상품판매원은 신고 대상에서 제외');
        det.verifiedFacts.push('직종코드 2742 · 해외 온라인상품판매원');
        assessBreach(caseData, 'PERMIT', det);
        return finish(det);
      } else if (caseData.overseasOnlineSeller === false) {
        det.exceptionsChecked.push('직종코드 2742이나 해외 온라인상품판매원이 아니어서 조건부 적용제외에 해당하지 않음');
        det.verifiedFacts.push(`직종코드 ${occupation}`);
      } else {
        det.missingFacts.push('해외 온라인상품판매원 해당 여부');
        unresolved = true;
      }
    } else if (eligibility.excludedOccupationCodesE7.includes(occupation)) {
      det.regime = 'PERMIT';
      det.determinationStatus = 'CONFIRMED';
      det.exceptionsChecked.push(`고시 적용제외: E-7 직종코드 ${occupation}는 사전관리가 필요한 직종으로 신고 대상에서 제외`);
      det.verifiedFacts.push(`직종코드 ${occupation}`);
      assessBreach(caseData, 'PERMIT', det);
      return finish(det);
    } else {
      det.exceptionsChecked.push(`E-7 직종코드 ${occupation}는 고시 적용제외 목록에 없음`);
      det.verifiedFacts.push(`직종코드 ${occupation}`);
    }
  } else if (status.startsWith('E-6')) {
    if (status === 'E-6' || !['E-6-1', 'E-6-3'].includes(status)) {
      det.missingFacts.push('E-6 세부 유형');
      unresolved = true;
    } else {
      det.exceptionsChecked.push('E-6-2가 아닌 E-6 세부 유형은 고시 적용제외에 해당하지 않음');
    }
  }

  if (caseData.alienRegistered === null || caseData.alienRegistered === undefined) {
    det.missingFacts.push('외국인등록 여부');
    unresolved = true;
  } else if (caseData.alienRegistered === false) {
    if (['DISMISSED_NO_OWN_FAULT', 'EMPLOYER_CLOSED', 'CONTRACT_EXPIRED'].includes(endReason)) {
      if (caseData.registrationExceptionUsed === true) {
        det.regime = 'PERMIT';
        det.determinationStatus = 'CONFIRMED';
        det.exceptionsChecked.push('고시 단서: 외국인등록 전 신고 허용(1회)을 이미 사용해, 등록 전 신고 대상에 해당하지 않음');
        assessBreach(caseData, 'PERMIT', det);
        return finish(det);
      } else if (caseData.registrationExceptionUsed === false) {
        det.exceptionsChecked.push('고시 단서: 본인 귀책사유 없이 고용계약이 종료된 경우 외국인등록 전이라도 1회에 한해 신고 허용');
        det.verifiedFacts.push('외국인등록 전 신고 예외(1회) 미사용');
      } else {
        det.missingFacts.push('외국인등록 전 신고 예외(1회) 사용 여부');
        unresolved = true;
      }
    } else if (['DISMISSED_OWN_FAULT', 'RESIGNED_MID_CONTRACT'].includes(endReason)) {
      det.regime = 'PERMIT';
      det.determinationStatus = 'CONFIRMED';
      det.exceptionsChecked.push('고시 자격요건: 외국인등록을 하고 체류 중이어야 한다는 요건 미충족');
      assessBreach(caseData, 'PERMIT', det);
      return finish(det);
    } else {
      det.missingFacts.push('이전 고용 종료 사유');
      unresolved = true;
    }
  } else {
    det.verifiedFacts.push('외국인등록 후 체류 중');
  }

  if (caseData.meetsNewWorkplaceQualifications === null || caseData.meetsNewWorkplaceQualifications === undefined) {
    det.missingFacts.push('새 근무처 자격요건 충족 여부');
    unresolved = true;
  } else if (caseData.meetsNewWorkplaceQualifications === false) {
    det.regime = 'PERMIT';
    det.determinationStatus = 'CONFIRMED';
    det.exceptionsChecked.push('고시 자격요건: 변경·추가되는 근무처 활동에 필요한 자격요건을 갖추어야 함');
    det.warnings.push('새 근무처 자격요건 미충족 자체는 체류자격 범위 문제로 별도 검토가 필요할 수 있습니다.');
    assessBreach(caseData, 'PERMIT', det);
    return finish(det);
  } else {
    det.verifiedFacts.push('새 근무처 자격요건 충족');
  }

  if (caseData.workplaceChangeType === 'ADDITION' || endReason === 'NOT_ENDED') {
    det.exceptionsChecked.push('기존 고용이 유지되는 근무처 추가는 \'해고·중도퇴직\' 적용제외와 무관');
  } else if (OWN_FAULT_REASONS.has(endReason)) {
    if (caseData.employerConsent === true) {
      det.exceptionsChecked.push('본인 귀책 해고·중도퇴직이나 원 고용주 이적 동의를 받아 적용제외에 해당하지 않음');
      det.verifiedFacts.push('원 고용주 이적 동의 있음');
    } else if (caseData.employerConsent === false) {
      det.regime = 'PERMIT';
      det.determinationStatus = 'CONFIRMED';
      det.exceptionsChecked.push('고시 적용제외: 본인 귀책사유로 해고 또는 중도 퇴직하고 원 고용주의 이적 동의를 받지 못한 자');
      assessBreach(caseData, 'PERMIT', det);
      return finish(det);
    } else {
      det.missingFacts.push('원 고용주 이적 동의 여부');
      unresolved = true;
    }
  } else if (CLEAR_NON_OWN_FAULT_REASONS.has(endReason)) {
    det.exceptionsChecked.push('계약만료·본인 귀책 없는 해고·폐업 등은 고시의 본인귀책 적용제외에 해당하지 않음');
  } else {
    det.missingFacts.push('이전 고용 종료 사유');
    unresolved = true;
  }

  if (unresolved) {
    det.humanReviewReason = '고시 요건 중 확인되지 않은 항목이 있어 사전허가/사후신고를 확정할 수 없습니다. 확인되지 않은 요건을 충족한 것으로 가정하지 않습니다.';
    return finish(det);
  }

  det.regime = 'REPORT';
  det.determinationStatus = 'CONFIRMED';
  det.verifiedFacts.push('법무부고시 제2020-212호의 신고 대상 요건을 모두 충족하고 적용제외에 해당하지 않음');
  assessBreach(caseData, 'REPORT', det);
  return finish(det);
}

function determineWorkplaceRegime(caseData) {
  if (caseData.actuallyStartedWork === false) {
    const det = baseDetermination();
    det.regime = 'NOT_APPLICABLE';
    det.determinationStatus = 'NOT_APPLICABLE';
    det.verifiedFacts = ['새 근무처에서 실제로 근무를 시작하지 않음'];
    det.applicableRules = ['출입국관리법 제21조(근무처 변경·추가) — 실제 근무 사실이 전제'];
    det.penaltyTrack = 'NONE';
    det.dutyBreach = 'NOT_ESTABLISHED';
    det.warnings = ['실제로 근무하지 않았다면 근무를 전제로 한 범칙금·과태료 계산은 하지 않습니다.'];
    return finish(det);
  }

  const engine = engineDetermine(caseData);
  const userRegime = ['PERMIT', 'REPORT'].includes(caseData.workplaceRegime) ? caseData.workplaceRegime : null;
  // Raw-JSON callers get no schema validation (unlike the Python model's
  // Literal), so provenance is checked explicitly: only an absent source
  // (legacy payloads) or an explicit USER_CONFIRMED may act as a user
  // confirmation. Any other value (e.g. an AI-supplied tag) is ignored.
  const source = caseData.workplaceRegimeSource || null;
  const userConfirmed = userRegime && (source === null || source === 'USER_CONFIRMED');
  if (userConfirmed) {
    if (engine.determinationStatus === 'CONFIRMED' && engine.regime !== userRegime) {
      engine.warnings.push('관할관서에서 확인받았다는 내용과 검증된 고시 규칙의 판별이 다릅니다. 고시 규칙 판별을 우선 표시하니, 관할 출입국·외국인관서에서 최종 확인해 주세요.');
      engine.humanReviewReason = '사용자 확인과 결정론적 판별이 충돌합니다.';
      return finish(engine);
    }
    if (engine.determinationStatus !== 'CONFIRMED') {
      const det = baseDetermination();
      det.regime = userRegime;
      det.determinationStatus = 'USER_CONFIRMED';
      det.determinationSource = 'USER_CONFIRMED';
      det.verifiedFacts = [...engine.verifiedFacts];
      det.missingFacts = [...engine.missingFacts];
      det.exceptionsChecked = [...engine.exceptionsChecked];
      det.humanReviewReason = engine.humanReviewReason;
      det.warnings = ['사용자가 관할관서에서 확인한 구분을 전제로 합니다. Visable이 법적으로 확정한 분류가 아닙니다.'];
      assessBreach(caseData, userRegime, det);
      return finish(det);
    }
  }
  return finish(engine);
}

function isWorkplaceCase(caseData) {
  const codes = caseData.violationCode ? [caseData.violationCode] : (caseData.violationCandidates || []);
  if (codes.some((code) => WORKPLACE_VIOLATION_CODES.has(code))) return true;
  return Boolean(caseData.workplaceChangeType || caseData.workplaceChangeDate || caseData.occupationCode || caseData.procedureStatus);
}

module.exports = {
  determineWorkplaceRegime,
  isWorkplaceCase,
  WORKPLACE_VIOLATION_CODES,
  workplaceRules: rules,
};
