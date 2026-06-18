/*
 * employment_checklist.mjs
 * ----------------------------------------------------------------------------
 * Builds the guided checklist state for the 취업정보 신고용 직종·업종 찾기 feature
 * from a (PR #442) analyzer result + the user's current selections. Pure ES
 * module: runs in Node (tests) and in the browser (bridged onto
 * window.EmploymentChecklist by index.html). It performs NO I/O.
 *
 * Why this exists: the old UI showed a STATIC 3-item legend that never reflected
 * the analyzer result, selections, clarifications, or the "공식 코드 확인 필요"
 * state — so it could imply progress that wasn't real. This module is the single
 * source of truth for checklist state, with explicit, testable status rules.
 *
 * Hard rules (do not weaken):
 *   - "candidate found" is NOT "confirmed".
 *   - "공식 코드 확인 필요" (needs_confirmation) is NOT complete.
 *   - a pending clarification keeps 직종/업종 out of complete.
 *   - income stays pending until a user-selected bracket exists.
 *   - the HiKorea final check is NEVER complete inside Paradiso.
 *   - this feature never asserts a visa permits the work (no eligibility step).
 * ----------------------------------------------------------------------------
 */

export const CHECKLIST_SCHEMA = '2026-06-employment-checklist';

// Status vocabulary. `text` is shown next to the icon so status is never
// conveyed by colour alone (accessibility).
export const STATUS = {
  pending: { ko: '아직 필요해요', en: 'Not yet', icon: '⬜' },
  ready: { ko: '후보를 찾았어요', en: 'Candidate found', icon: '🔵' },
  needs_confirmation: { ko: '확인이 필요해요', en: 'Quick check needed', icon: '⚠️' },
  complete: { ko: '선택했어요', en: 'Selected', icon: '✅' },
  blocked: { ko: '조금 더 알려주세요', en: 'Add a detail', icon: '✏️' }
};

// All user-facing copy, keyed so tests can assert ko+en presence and so the
// renderer never hardcodes strings inline. (Dynamic analyzer copy in this feature
// follows the ko/en convention established in PR #442; zh-CN falls back to ko.)
export const CHECKLIST_COPY = {
  'step.occupation.label': { ko: '1단계 · 내가 하는 일 (직종)', en: 'Step 1 · Your work (occupation)' },
  'step.occupation.plain': { ko: '내가 실제로 하는 일', en: 'What you actually do' },
  'step.industry.label': { ko: '2단계 · 회사/사업장이 하는 일 (업종)', en: 'Step 2 · Employer / business activity (industry)' },
  'step.industry.plain': { ko: '회사·사업장이 하는 일', en: 'What your employer/business does' },
  'step.income.label': { ko: '3단계 · 연간소득 구간', en: 'Step 3 · Annual income bracket' },
  'step.income.plain': { ko: '하이코리아에서 선택할 소득 구간', en: 'Income bracket to pick on HiKorea' },
  'step.hikorea.label': { ko: '4단계 · 하이코리아 최종 확인', en: 'Step 4 · Final HiKorea check' },
  'step.hikorea.plain': { ko: '최종 신고 전 확인할 것', en: 'Confirm before final submission' },

  'reason.occupation.pending': { ko: '검색하면 ‘내가 하는 일’에 가까운 직종 후보를 찾아드려요.', en: 'Search and we\'ll find occupation candidates close to your work.' },
  'reason.occupation.ready': { ko: '직종 후보를 찾았어요. 내가 하는 일에 가까운 항목을 선택하세요.', en: 'Found occupation candidates — pick the one closest to your work.' },
  'reason.occupation.needs_confirmation': { ko: '한 가지만 더 확인하면 직종이 정확해져요. 아래 질문에 답해 주세요.', en: 'One more detail will pin down the occupation — answer the question below.' },
  'reason.occupation.needs_code': { ko: '입력은 이해했지만 공식 직종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official occupation code needs confirmation.' },
  'reason.occupation.complete': { ko: '직종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Occupation selected — confirm the final value on HiKorea.' },
  'reason.occupation.blocked': { ko: '조금 더 구체적으로 입력하면 직종 후보를 찾을 수 있어요 (하는 일/장소).', en: 'Add a bit more detail (task / place) to find occupation candidates.' },

  'reason.industry.pending': { ko: '검색하면 회사·사업장이 하는 일에 가까운 업종 후보를 찾아드려요.', en: 'Search and we\'ll find industry candidates close to your employer\'s business.' },
  'reason.industry.ready': { ko: '업종 후보를 찾았어요. 회사/사업장이 하는 일에 가까운 항목을 선택하세요.', en: 'Found industry candidates — pick the one closest to your employer\'s business.' },
  'reason.industry.needs_confirmation': { ko: '고용 형태(직접 고용/파견 등)에 따라 업종이 달라져요. 아래 질문에 답해 주세요.', en: 'Industry depends on the employment relationship — answer the question below.' },
  'reason.industry.needs_code': { ko: '입력은 이해했지만 공식 업종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official industry code needs confirmation.' },
  'reason.industry.complete': { ko: '업종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Industry selected — confirm the final value on HiKorea.' },
  'reason.industry.blocked': { ko: '회사/사업장이 무슨 일을 하는지 적으면 업종 후보를 찾을 수 있어요.', en: 'Tell us what your employer/business does to find industry candidates.' },

  'reason.income.pending': { ko: '하이코리아에서 실제 연간소득 구간을 선택해야 합니다 (과세 전 기준).', en: 'Select your actual annual income bracket on HiKorea (pre-tax).' },
  'reason.income.complete': { ko: '소득 구간을 임시로 골랐어요. 최종 선택은 하이코리아에서 확인하세요.', en: 'Income bracket drafted — confirm the final choice on HiKorea.' },

  'reason.hikorea.pending': { ko: '검색을 마치면 하이코리아에서 최종 확인할 항목을 정리해 드려요.', en: 'After searching, we\'ll list what to confirm on HiKorea.' },
  'reason.hikorea.needs_confirmation': { ko: '최종 신고는 하이코리아 화면에서 직접 확인·선택해야 합니다. Paradiso는 후보만 찾아드려요.', en: 'Final reporting is done on HiKorea itself — Paradiso only finds candidates.' },

  'section.occupation': { ko: '직종 후보: 내가 하는 일에 가까운 항목', en: 'Occupation candidates: closest to what you do' },
  'section.industry': { ko: '업종 후보: 회사/사업장이 하는 일에 가까운 항목', en: 'Industry candidates: closest to your employer\'s business' },
  'caution.main': { ko: 'Paradiso는 신고용 직종·업종 후보를 찾는 도구예요. 실제 신고 시에는 하이코리아 화면에서 최종 선택값을 확인하세요. (해당 체류자격에서 취업이 가능한지는 판단하지 않아요.)', en: 'Paradiso finds occupation/industry candidates for reporting. Always confirm the final values on HiKorea. (It does not decide whether your visa permits the work.)' },
  'weak.title': { ko: '입력하신 내용만으로는 직종과 업종을 나누기 어려워요.', en: 'This input alone is hard to split into occupation and industry.' },
  'weak.hint': { ko: '아래처럼 입력하면 더 정확해져요.', en: 'Try inputs like these for a better match.' },
  'weak.detail.place': { ko: '일하는 장소', en: 'Where you work' },
  'weak.detail.task': { ko: '하는 일', en: 'What you do' },
  'weak.detail.business': { ko: '회사/사업장이 하는 일', en: 'What the employer/business does' },
  'clarify.lead': { ko: '정확도를 높이려면 이것만 확인해 주세요.', en: 'One more detail will improve the match.' },
  'card.fit': { ko: '이 항목이 맞을 수 있는 경우', en: 'This may fit when' },
  'card.other': { ko: '다른 항목이 맞을 수 있는 경우', en: 'Another may fit when' },
  'card.needsCode': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation' },
  // HiKorea final step shows an action label, never a "complete" one.
  'status.hikorea': { ko: '하이코리아에서 확인해 주세요', en: 'Confirm in HiKorea' },

  // Toss-inspired guided UI copy (keyed ko/en; rendered by index.html).
  'interpret.title': { ko: '이렇게 이해했어요', en: 'Here’s how Paradiso understood your input' },
  'interpret.place': { ko: '일하는 곳', en: 'Where you work' },
  'interpret.object': { ko: '대상', en: 'What you handle' },
  'interpret.action': { ko: '하는 일', en: 'What you do' },
  'interpret.check': { ko: '더 확인할 점', en: 'Still to confirm' },
  'clarify.dunno': { ko: '잘 모르겠어요', en: 'Not sure' },
  'conf.high': { ko: '가장 가까움', en: 'Closest' },
  'conf.mid': { ko: '비슷함', en: 'Similar' },
  'conf.low': { ko: '가능성 있음', en: 'Possible' },
  'group.top': { ko: '가장 가까운 후보', en: 'Closest candidate' },
  'group.others': { ko: '다른 가능성', en: 'Other possibilities' },
  'group.several': { ko: '몇 가지 가능성이 있어요', en: 'A few possibilities' },
  'card.source': { ko: '공식 분류 코드', en: 'Official classification code' },
  'card.detail': { ko: '자세히 보기', en: 'See details' },
  'more.show': { ko: '더 보기', en: 'Show more' },
  'more.hide': { ko: '접기', en: 'Show less' },
  'needcode.title': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation' },
  'needcode.body': { ko: '입력하신 업무는 해석할 수 있지만, 하이코리아에서 실제 선택할 공식 코드까지는 최종 확인이 필요해요.', en: 'Paradiso can read your work, but the exact official code to pick in HiKorea still needs a final check.' },
  'needcode.research': { ko: '다른 표현으로 다시 검색', en: 'Search with different words' },
  'needcode.portal': { ko: '통계분류포털에서 확인', en: 'Check the classification portal' }
};

/** Resolve a copy key to a language (ko default; zh-CN falls back to ko). */
export function checklistCopy(key, lang) {
  const e = CHECKLIST_COPY[key];
  if (!e) return key;
  return (lang === 'en' ? e.en : e.ko) || e.ko;
}
function statusLabel(status, lang) {
  const s = STATUS[status] || STATUS.pending;
  return (lang === 'en' ? s.en : s.ko) || s.ko;
}

// Which track(s) the TOP clarification question actually forks. Keeps the two
// checklist tracks independent: "software developer" clarifies the employer
// (industry) while the occupation is already clear; "골프장 청소" clarifies the
// employer (industry) while "cleaner" is clear; a vessel/factory fork changes both.
const CLARIFY_TRACKS_BY_TOPIC = {
  direct_employer_vs_contractor: ['industry'],
  restaurant_employee_vs_outsourced: ['industry'],
  employer_product_unknown: ['industry'],
  hospitality_role_unknown: ['occupation'],
  construction_labor_vs_technical_install: ['occupation'],
  vessel_crew_vs_land_processing: ['occupation', 'industry'],
  aquaculture_vs_processing: ['occupation', 'industry'],
  farm_harvest_vs_food_factory: ['occupation', 'industry'],
  manufacturing_vs_logistics: ['occupation', 'industry']
};
const CLARIFY_TRACKS_BY_FLAG = {
  workplace: ['industry'],
  role: ['occupation'],
  freelancer: ['occupation', 'industry'],
  owner: ['occupation', 'industry'],
  underspecified: ['occupation', 'industry']
};
function clarificationTracks(result) {
  const q = result && Array.isArray(result.ambiguityQuestions) ? result.ambiguityQuestions[0] : null;
  if (!q) return { occupation: false, industry: false };
  const list = (q.topic && CLARIFY_TRACKS_BY_TOPIC[q.topic]) || (q.flag && CLARIFY_TRACKS_BY_FLAG[q.flag]) || ['occupation', 'industry'];
  return { occupation: list.includes('occupation'), industry: list.includes('industry') };
}

/** True when the analyzer understood the input (signals/concepts/interpretation). */
function hasUnderstanding(r) {
  if (!r) return false;
  const ps = r.parsedSignals || {};
  const sig = (ps.places || []).length + (ps.objects || []).length + (ps.actions || []).length + (ps.tools || []).length;
  return sig > 0 || (r.matchedConcepts || []).length > 0 || !!r.parsedInterpretation ||
    !!(r.extracted && (r.extracted.jobRole || r.extracted.workplaceType || r.extracted.businessActivity));
}

/**
 * buildEmploymentChecklistState(opts) → { schema, lang, concepts, steps }.
 *
 * opts:
 *   analyzerResult           PR #442 analyze() output, or null (initial state)
 *   selectedOccupation       { code, name } | null  (user confirmed)
 *   selectedIndustry         { code, name } | null
 *   clarificationState       { answered:boolean } | null   (override)
 *   incomeState              { selected:boolean, value? } | null
 *   sourceStatus             override string (else analyzerResult.sourceStatus)
 *   occupationResultCount    number of occupation cards actually shown (UI truth)
 *   industryResultCount      number of industry cards actually shown
 *   lang                     'ko' | 'en'  (default 'ko')
 */
export function buildEmploymentChecklistState(opts = {}) {
  const r = opts.analyzerResult || null;
  const lang = opts.lang === 'en' ? 'en' : 'ko';
  const hasResult = !!r;

  const occCount = opts.occupationResultCount != null
    ? opts.occupationResultCount : (r && r.occupationCandidates ? r.occupationCandidates.length : 0);
  const indCount = opts.industryResultCount != null
    ? opts.industryResultCount : (r && r.industryCandidates ? r.industryCandidates.length : 0);

  const understood = hasUnderstanding(r);
  const answered = !!(opts.clarificationState && opts.clarificationState.answered);
  const clarificationPending = !!(r && r.clarificationRequired) && !answered;
  // Per-track: only the track(s) the top question actually forks are held back.
  const forks = clarificationPending ? clarificationTracks(r) : { occupation: false, industry: false };
  const noOfficialCodeFound = !!(r && r.noOfficialCodeFound);
  const needsCode = hasResult && (opts.sourceStatus === 'needs_confirmation' || r.sourceStatus === 'needs_confirmation' ||
    (noOfficialCodeFound && understood));

  const occupationConfirmed = !!opts.selectedOccupation;
  const industryConfirmed = !!opts.selectedIndustry;
  const occupationCandidateFound = occCount > 0;
  const industryCandidateFound = indCount > 0;
  const incomeSelected = !!(opts.incomeState && opts.incomeState.selected);

  // Per-track status: confirmed > (this track's) clarification > candidate >
  // needs-code > weak. Clarification only blocks the track it actually forks.
  function trackStatus(confirmed, candidateFound, forked) {
    if (!hasResult) return 'pending';
    if (confirmed) return 'complete';
    if (forked) return 'needs_confirmation';
    if (candidateFound) return 'ready';
    if (needsCode) return 'needs_confirmation';
    if (understood) return 'needs_confirmation'; // understood but no card → confirm officially
    return 'blocked';                            // weak input → ask for more detail
  }
  const occStatus = trackStatus(occupationConfirmed, occupationCandidateFound, forks.occupation);
  const indStatus = trackStatus(industryConfirmed, industryCandidateFound, forks.industry);

  function reasonKey(track, status, forked) {
    if (status === 'complete') return `reason.${track}.complete`;
    if (status === 'blocked') return `reason.${track}.blocked`;
    if (status === 'ready') return `reason.${track}.ready`;
    if (status === 'pending') return `reason.${track}.pending`;
    // needs_confirmation: this track's clarification first, else official-code.
    if (forked) return `reason.${track}.needs_confirmation`;
    return `reason.${track}.needs_code`;
  }

  const mkStep = (id, labelKey, plainKey, status, reasonKeyStr, extra = {}) => ({
    id,
    label: checklistCopy(labelKey, lang),
    labelKey,
    plainLanguageLabel: checklistCopy(plainKey, lang),
    status,
    // statusLabelKey lets a step show an action-style label (e.g. the HiKorea
    // step always says "하이코리아에서 확인해 주세요", never a "complete" label).
    statusLabel: extra.statusLabelKey ? checklistCopy(extra.statusLabelKey, lang) : statusLabel(status, lang),
    reason: checklistCopy(reasonKeyStr, lang),
    reasonKey: reasonKeyStr,
    i18nKey: labelKey,
    sourceStatus: extra.sourceStatus || (status === 'needs_confirmation' && extra.code ? 'needs_confirmation' : (status === 'ready' || status === 'complete' ? 'official_list' : 'pending')),
    ...(extra.actionLabel ? { actionLabel: extra.actionLabel } : {})
  });

  const incomeStatus = !hasResult ? 'pending' : (incomeSelected ? 'complete' : 'pending');
  const incomeReasonKey = incomeStatus === 'complete' ? 'reason.income.complete' : 'reason.income.pending';
  // HiKorea final check is NEVER complete inside Paradiso.
  const hikoreaStatus = hasResult ? 'needs_confirmation' : 'pending';
  const hikoreaReasonKey = hasResult ? 'reason.hikorea.needs_confirmation' : 'reason.hikorea.pending';

  const steps = [
    mkStep('occupation', 'step.occupation.label', 'step.occupation.plain', occStatus,
      reasonKey('occupation', occStatus, forks.occupation), { code: true }),
    mkStep('industry', 'step.industry.label', 'step.industry.plain', indStatus,
      reasonKey('industry', indStatus, forks.industry), { code: true }),
    mkStep('income', 'step.income.label', 'step.income.plain', incomeStatus, incomeReasonKey),
    mkStep('hikorea', 'step.hikorea.label', 'step.hikorea.plain', hikoreaStatus, hikoreaReasonKey,
      { sourceStatus: 'needs_confirmation', statusLabelKey: 'status.hikorea' })
  ];

  return {
    schema: CHECKLIST_SCHEMA,
    lang,
    concepts: {
      occupationCandidateFound,
      occupationConfirmed,
      industryCandidateFound,
      industryConfirmed,
      incomeReminderShown: hasResult,
      incomeSelected,
      officialCodeVerified: (occupationCandidateFound || industryCandidateFound) && !noOfficialCodeFound,
      officialCodeNeedsConfirmation: needsCode,
      clarificationPending,
      hikoreaFinalCheckRequired: true
    },
    steps
  };
}

export default { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, checklistCopy, buildEmploymentChecklistState };

// Browser bridge for the inline UI in index.html (no build step).
if (typeof window !== 'undefined') {
  window.EmploymentChecklist = { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, checklistCopy, buildEmploymentChecklistState };
}
