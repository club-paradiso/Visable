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

/**
 * Guided-flow state machine for the employment finder. Drives PROGRESSIVE
 * disclosure so only one major action shows at a time: after a search the user
 * sees the interpretation first; when a fork question is pending AND there are
 * candidates to gate, the candidate list is held behind the question until the
 * user answers, picks "잘 모르겠어요", or explicitly reveals it. Weak inputs (no
 * candidates) are never gated — their guided examples are the action.
 *
 * Returns: 'idle' | 'analyzing' | 'needs_clarification' | 'showing_candidates'.
 */
export function employmentFlowState(opts = {}) {
  if (opts.analyzing) return 'analyzing';
  const r = opts.analyzerResult;
  if (!r) return 'idle';
  const needsClar = !!r.clarificationRequired && !opts.clarificationAnswered;
  if (needsClar && opts.hasCandidates && !opts.candidatesRevealed) return 'needs_clarification';
  return 'showing_candidates';
}

// Status vocabulary. `text` is shown next to the icon so status is never
// conveyed by colour alone (accessibility).
export const STATUS = {
  pending: { ko: '아직 필요해요', en: 'Not yet', 'zh-CN': '还需要', icon: '⬜' },
  ready: { ko: '후보를 찾았어요', en: 'Candidate found', 'zh-CN': '已找到候选', icon: '🔵' },
  needs_confirmation: { ko: '확인이 필요해요', en: 'Quick check needed', 'zh-CN': '需要确认', icon: '⚠️' },
  complete: { ko: '선택했어요', en: 'Selected', 'zh-CN': '已选择', icon: '✅' },
  blocked: { ko: '조금 더 알려주세요', en: 'Add a detail', 'zh-CN': '请再补充一点', icon: '✏️' }
};

// All user-facing copy, keyed so tests can assert ko+en presence and so the
// renderer never hardcodes strings inline. (Dynamic analyzer copy in this feature
// follows the ko/en convention established in PR #442; zh-CN falls back to ko.)
export const CHECKLIST_COPY = {
  'step.occupation.label': { ko: '1단계 · 내가 하는 일 (직종)', en: 'Step 1 · Your work (occupation)', 'zh-CN': '第 1 步 · 我所做的工作（职业）' },
  'step.occupation.plain': { ko: '내가 실제로 하는 일', en: 'What you actually do', 'zh-CN': '我实际所做的工作' },
  'step.industry.label': { ko: '2단계 · 회사/사업장이 하는 일 (업종)', en: 'Step 2 · Employer / business activity (industry)', 'zh-CN': '第 2 步 · 公司/营业场所所做的业务（行业）' },
  'step.industry.plain': { ko: '회사·사업장이 하는 일', en: 'What your employer/business does', 'zh-CN': '公司·营业场所所做的业务' },
  'step.income.label': { ko: '3단계 · 연간소득 구간', en: 'Step 3 · Annual income bracket', 'zh-CN': '第 3 步 · 年收入区间' },
  'step.income.plain': { ko: '하이코리아에서 선택할 소득 구간', en: 'Income bracket to pick on HiKorea', 'zh-CN': '在 HiKorea 选择的收入区间' },
  'step.hikorea.label': { ko: '4단계 · 하이코리아 최종 확인', en: 'Step 4 · Final HiKorea check', 'zh-CN': '第 4 步 · HiKorea 最终确认' },
  'step.hikorea.plain': { ko: '최종 신고 전 확인할 것', en: 'Confirm before final submission', 'zh-CN': '最终申报前需确认的事项' },

  'reason.occupation.pending': { ko: '검색하면 ‘내가 하는 일’에 가까운 직종 후보를 찾아드려요.', en: 'Search and we\'ll find occupation candidates close to your work.', 'zh-CN': '搜索后，我们会为您找出与“我所做的工作”相近的职业候选。' },
  'reason.occupation.ready': { ko: '직종 후보를 찾았어요. 내가 하는 일에 가까운 항목을 선택하세요.', en: 'Found occupation candidates — pick the one closest to your work.', 'zh-CN': '已找到职业候选。请选择与您所做工作最接近的项目。' },
  'reason.occupation.needs_confirmation': { ko: '한 가지만 더 확인하면 직종이 정확해져요. 아래 질문에 답해 주세요.', en: 'One more detail will pin down the occupation — answer the question below.', 'zh-CN': '再确认一点，职业就能更准确。请回答下面的问题。' },
  'reason.occupation.needs_code': { ko: '입력은 이해했지만 공식 직종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official occupation code needs confirmation.', 'zh-CN': '已理解您的输入，但官方职业代码仍需确认（需确认官方代码）。' },
  'reason.occupation.complete': { ko: '직종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Occupation selected — confirm the final value on HiKorea.', 'zh-CN': '已选择职业候选。最终值请在 HiKorea 确认。' },
  'reason.occupation.blocked': { ko: '조금 더 구체적으로 입력하면 직종 후보를 찾을 수 있어요 (하는 일/장소).', en: 'Add a bit more detail (task / place) to find occupation candidates.', 'zh-CN': '再输入得具体一些（工作内容/地点），即可找到职业候选。' },

  'reason.industry.pending': { ko: '검색하면 회사·사업장이 하는 일에 가까운 업종 후보를 찾아드려요.', en: 'Search and we\'ll find industry candidates close to your employer\'s business.', 'zh-CN': '搜索后，我们会为您找出与公司·营业场所业务相近的行业候选。' },
  'reason.industry.ready': { ko: '업종 후보를 찾았어요. 회사/사업장이 하는 일에 가까운 항목을 선택하세요.', en: 'Found industry candidates — pick the one closest to your employer\'s business.', 'zh-CN': '已找到行业候选。请选择与公司/营业场所业务最接近的项目。' },
  'reason.industry.needs_confirmation': { ko: '고용 형태(직접 고용/파견 등)에 따라 업종이 달라져요. 아래 질문에 답해 주세요.', en: 'Industry depends on the employment relationship — answer the question below.', 'zh-CN': '行业会因雇佣形态（直接雇佣/派遣等）而不同。请回答下面的问题。' },
  'reason.industry.needs_code': { ko: '입력은 이해했지만 공식 업종 코드는 확인이 필요해요 (공식 코드 확인 필요).', en: 'Understood, but the official industry code needs confirmation.', 'zh-CN': '已理解您的输入，但官方行业代码仍需确认（需确认官方代码）。' },
  'reason.industry.complete': { ko: '업종 후보를 선택했어요. 최종값은 하이코리아에서 확인하세요.', en: 'Industry selected — confirm the final value on HiKorea.', 'zh-CN': '已选择行业候选。最终值请在 HiKorea 确认。' },
  'reason.industry.blocked': { ko: '회사/사업장이 무슨 일을 하는지 적으면 업종 후보를 찾을 수 있어요.', en: 'Tell us what your employer/business does to find industry candidates.', 'zh-CN': '写明公司/营业场所做什么业务，即可找到行业候选。' },

  'reason.income.pending': { ko: '하이코리아에서 실제 연간소득 구간을 선택해야 합니다 (과세 전 기준).', en: 'Select your actual annual income bracket on HiKorea (pre-tax).', 'zh-CN': '须在 HiKorea 选择实际年收入区间（以税前为准）。' },
  'reason.income.complete': { ko: '소득 구간을 임시로 골랐어요. 최종 선택은 하이코리아에서 확인하세요.', en: 'Income bracket drafted — confirm the final choice on HiKorea.', 'zh-CN': '已暂选收入区间。最终选择请在 HiKorea 确认。' },

  'reason.hikorea.pending': { ko: '검색을 마치면 하이코리아에서 최종 확인할 항목을 정리해 드려요.', en: 'After searching, we\'ll list what to confirm on HiKorea.', 'zh-CN': '搜索结束后，我们会为您整理出需在 HiKorea 最终确认的事项。' },
  'reason.hikorea.needs_confirmation': { ko: '최종 신고는 하이코리아 화면에서 직접 확인·선택해야 합니다. Paradiso는 후보만 찾아드려요.', en: 'Final reporting is done on HiKorea itself — Paradiso only finds candidates.', 'zh-CN': '最终申报须在 HiKorea 界面亲自确认·选择。Paradiso 仅为您查找候选。' },

  'section.occupation': { ko: '직종 후보: 내가 하는 일에 가까운 항목', en: 'Occupation candidates: closest to what you do', 'zh-CN': '职业候选：与您所做工作最接近的项目' },
  'section.industry': { ko: '업종 후보: 회사/사업장이 하는 일에 가까운 항목', en: 'Industry candidates: closest to your employer\'s business', 'zh-CN': '行业候选：与公司/营业场所业务最接近的项目' },
  'caution.main': { ko: 'Paradiso는 신고용 직종·업종 후보를 찾는 도구예요. 실제 신고 시에는 하이코리아 화면에서 최종 선택값을 확인하세요. (해당 체류자격에서 취업이 가능한지는 판단하지 않아요.)', en: 'Paradiso finds occupation/industry candidates for reporting. Always confirm the final values on HiKorea. (It does not decide whether your visa permits the work.)', 'zh-CN': 'Paradiso 是用于查找申报用职业·行业候选的工具。实际申报时，请在 HiKorea 界面确认最终选择值。（不判断该居留资格是否允许就业。）' },
  'weak.title': { ko: '입력하신 내용만으로는 직종과 업종을 나누기 어려워요.', en: 'This input alone is hard to split into occupation and industry.', 'zh-CN': '仅凭您输入的内容，难以区分职业和行业。' },
  'weak.hint': { ko: '아래처럼 입력하면 더 정확해져요.', en: 'Try inputs like these for a better match.', 'zh-CN': '像下面这样输入会更准确。' },
  'weak.detail.place': { ko: '일하는 장소', en: 'Where you work', 'zh-CN': '工作地点' },
  'weak.detail.task': { ko: '하는 일', en: 'What you do', 'zh-CN': '所做的工作' },
  'weak.detail.business': { ko: '회사/사업장이 하는 일', en: 'What the employer/business does', 'zh-CN': '公司/营业场所所做的业务' },
  'clarify.lead': { ko: '정확도를 높이려면 이것만 확인해 주세요.', en: 'One more detail will improve the match.', 'zh-CN': '为提高准确度，只需确认这一点。' },
  'card.fit': { ko: '이 항목이 맞을 수 있는 경우', en: 'This may fit when', 'zh-CN': '该项目可能合适的情况' },
  'card.other': { ko: '다른 항목이 맞을 수 있는 경우', en: 'Another may fit when', 'zh-CN': '其他项目可能更合适的情况' },
  'card.needsCode': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation', 'zh-CN': '需确认官方代码' },
  // HiKorea final step shows an action label, never a "complete" one.
  'status.hikorea': { ko: '하이코리아에서 확인해 주세요', en: 'Confirm in HiKorea', 'zh-CN': '请在 HiKorea 确认' },

  // Toss-inspired guided UI copy (keyed ko/en/zh-CN; rendered by index.html).
  'interpret.title': { ko: '이렇게 이해했어요', en: 'Here’s how Paradiso understood your input', 'zh-CN': 'Paradiso 是这样理解您输入的' },
  'interpret.place': { ko: '일하는 곳', en: 'Where you work', 'zh-CN': '工作地点' },
  'interpret.object': { ko: '대상', en: 'What you handle', 'zh-CN': '处理的对象' },
  'interpret.action': { ko: '하는 일', en: 'What you do', 'zh-CN': '所做的工作' },
  'interpret.check': { ko: '더 확인할 점', en: 'Still to confirm', 'zh-CN': '仍需确认的点' },
  'clarify.dunno': { ko: '잘 모르겠어요', en: 'Not sure', 'zh-CN': '不太清楚' },
  'conf.high': { ko: '가장 가까움', en: 'Closest', 'zh-CN': '最接近' },
  'conf.mid': { ko: '비슷함', en: 'Similar', 'zh-CN': '相似' },
  'conf.low': { ko: '가능성 있음', en: 'Possible', 'zh-CN': '有可能' },
  'group.top': { ko: '가장 가까운 후보', en: 'Closest candidate', 'zh-CN': '最接近的候选' },
  'group.others': { ko: '다른 가능성', en: 'Other possibilities', 'zh-CN': '其他可能' },
  'group.several': { ko: '몇 가지 가능성이 있어요', en: 'A few possibilities', 'zh-CN': '有几种可能' },
  'card.source': { ko: '공식 분류 코드', en: 'Official classification code', 'zh-CN': '官方分类代码' },
  'card.detail': { ko: '자세히 보기', en: 'See details', 'zh-CN': '查看详情' },
  'more.show': { ko: '더 보기', en: 'Show more', 'zh-CN': '查看更多' },
  'more.hide': { ko: '접기', en: 'Show less', 'zh-CN': '收起' },
  'needcode.title': { ko: '공식 코드 확인 필요', en: 'Official code needs confirmation', 'zh-CN': '需确认官方代码' },
  'needcode.body': { ko: '입력하신 업무는 해석할 수 있지만, 하이코리아에서 실제 선택할 공식 코드까지는 최종 확인이 필요해요.', en: 'Paradiso can read your work, but the exact official code to pick in HiKorea still needs a final check.', 'zh-CN': '您输入的工作可以被解读，但在 HiKorea 实际选择的官方代码仍需最终确认。' },
  'needcode.research': { ko: '다른 표현으로 다시 검색', en: 'Search with different words', 'zh-CN': '换种表述重新搜索' },
  'needcode.portal': { ko: '통계분류포털에서 확인', en: 'Check the classification portal', 'zh-CN': '在统计分类门户确认' },
  // Guided-flow gate (candidates held behind the clarification question)
  'flow.gateTitle': { ko: '후보는 잠시 후에 보여드릴게요', en: 'Candidates in just a moment', 'zh-CN': '候选稍后即可显示' },
  'flow.gateBody': { ko: '위 질문에 답하면 더 정확한 직종·업종 후보를 보여드려요.', en: 'Answer the question above and we’ll show more accurate occupation/industry candidates.', 'zh-CN': '回答上面的问题，即可显示更准确的职业·行业候选。' },
  'flow.reveal': { ko: '그냥 후보 보기', en: 'Show candidates anyway', 'zh-CN': '直接查看候选' }
};

/** Resolve a copy key to a language (ko default; zh-CN falls back to ko). */
export function checklistCopy(key, lang) {
  const e = CHECKLIST_COPY[key];
  if (!e) return key;
  if (lang === 'zh-CN') return e['zh-CN'] || e.ko;
  return (lang === 'en' ? e.en : e.ko) || e.ko;
}
function statusLabel(status, lang) {
  const s = STATUS[status] || STATUS.pending;
  if (lang === 'zh-CN') return s['zh-CN'] || s.ko;
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
  const lang = opts.lang === 'en' ? 'en' : opts.lang === 'zh-CN' ? 'zh-CN' : 'ko';
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

export default { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, checklistCopy, buildEmploymentChecklistState, employmentFlowState };

// Browser bridge for the inline UI in index.html (no build step).
if (typeof window !== 'undefined') {
  window.EmploymentChecklist = { CHECKLIST_SCHEMA, STATUS, CHECKLIST_COPY, checklistCopy, buildEmploymentChecklistState, employmentFlowState };
}
