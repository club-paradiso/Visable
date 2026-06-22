/* ============================================================================
 * Paradiso — Complex-Status Guide engine + F-4 (재외동포) reference config
 * ----------------------------------------------------------------------------
 * A reusable, full-screen guided-preparation experience for "complex" statuses
 * — statuses whose required documents and procedures vary by sub-category,
 * situation, nationality history, or procedure. F-4 is the first, complete
 * reference implementation (Level A). Other statuses register a config object
 * with the same shape (see `ParadisoComplexGuide.register`).
 *
 * Replaces the previous pattern (several competing CTAs → small central modal →
 * disconnected procedure/subcode/document cards) with one unified pattern:
 *
 *   status search/detail
 *     → ONE dominant primary CTA
 *       → full-screen / wide guided flow (one main question per step)
 *         → personalized, checklist-first result
 *           → official source / evidence panel
 *
 * Engine (window.ParadisoComplexGuide):
 *   register(code, config) — add a status config:
 *     { code, ensureData(), title(), steps:[{ id, type:'single'|'multi',
 *       question(), help(), options:[{ id, label(), unsure? }] }],
 *       computeResult(answers), renderResult(model), refViews:{ id:{label,render} } }
 *   open(code, { ref })     — open the guide (flow, or jump straight to a ref view)
 *   close()                 — close + restore focus
 *   isOpen()                — overlay open?
 *
 * F-4 data (kept OUT of index.html, fetched lazily from data/f4/):
 *   base.json · diagnostic.json · faq.json · countries.json ·
 *   country_overlays.json · sources.json
 *
 * Safety contract (do not weaken):
 *  - F-4 is for FOREIGN-NATIONAL overseas Koreans. Current Korean nationals are
 *    routed to "국적/병역/자격 확인 필요", never into ordinary applicant guidance.
 *  - F-4 visa issuance and 국내거소신고/거소증 are SEPARATE procedures.
 *  - Overseas missions NEVER issue a 거소증.
 *  - The 90-day domestic residence-report deadline is never hidden.
 *  - Country-specific rules live in the country overlay only — never universalized.
 *  - Eligibility/approval is never guaranteed; nothing is invented. Items that
 *    are not source-backed are shown as "공식근거 확인 필요", never as certain.
 * ========================================================================== */
(function () {
  'use strict';

  var DATA_BASE = 'data/f4/';
  var FILES = {
    base: 'base.json',
    diagnostic: 'diagnostic.json',
    faq: 'faq.json',
    countries: 'countries.json',
    overlays: 'country_overlays.json',
    sources: 'sources.json'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  /* ---- UI chrome strings (Korean canonical; English active) --------------
   * Korean stays the source of truth. data/f4/*.json content (FAQ, country
   * overlays, diagnostic Q&A, steps) is legal/source data and remains Korean
   * per the project i18n policy (manifest.json). Only chrome resolves to the
   * active UI language. STR/TAB_LABEL stay accessed as STR.key / TAB_LABEL[k];
   * a Proxy resolves the active language at access time so reopening the guide
   * after switching language shows the right text.
   *
   * Simplified Chinese (zh-CN) chrome is intentionally NOT hardcoded here: the
   * platform marks Chinese as "preparing", and per the repo fallback policy a
   * non-en locale resolves to Korean canonical chrome rather than low-quality
   * machine text (see f4Lang). */
  function f4Lang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return l === 'en' ? 'en' : 'ko';
  }
  var STR_KO = {
    loading: 'F-4 안내 데이터를 불러오는 중입니다…',
    fetchFail: 'F-4 안내 데이터를 불러오지 못했습니다. 이 안내 없이 진행하지 마시고, 관할 재외공관·하이코리아·1345에서 직접 확인해 주세요.',
    entryEyebrow: '재외동포 F-4 · 공식 출처 기반 안내',
    startCtaFallback: 'F-4 절차 확인하기',
    modalAria: 'F-4 재외동포 안내',
    close: '닫기',
    back: '← 이전',
    restart: '처음부터 다시',
    seeResult: '결과 보기',
    recommended: '추천 경로',
    why: '왜 이 경로인가요?',
    checkFirst: '먼저 확인할 것',
    nextStep: '다음 단계',
    cautions: '주의',
    officialWarn: '공식 확인 안내',
    countryGuide: '국가별 확인',
    openHub: 'F-4 절차 자세히 보기',
    backToDiagnostic: '← 진단으로 돌아가기',
    hubTitle: 'F-4 절차 안내 허브',
    selectCountryLabel: '신청 국가 또는 거주 국가를 선택하세요',
    selectCountryHint: '국가별 공관 절차, 범죄경력증명서, 인증 방식, 예약, 수수료, 처리기간은 다를 수 있습니다. 검증되지 않은 국가는 공통 F-4 기준만 안내합니다.',
    selectCountryPlaceholder: '— 국가 선택 (선택 사항) —',
    noCountrySelected: '아직 국가를 선택하지 않았습니다. 공통 F-4 기준만 표시됩니다. 국가를 선택하면 해당 국가의 공관 안내(검증된 경우)가 함께 표시됩니다.',
    commonRulesHeading: '공통 F-4 기준 (모든 국가 공통)',
    countryRulesHeading: '국가별 안내',
    docsHeading: '공통 제출서류',
    stepsHeading: '단계',
    sourcesHeading: '출처',
    notGuaranteeFootnote: '이 안내는 자격이나 허가를 보장하지 않습니다. 실제 적용 여부는 관할 재외공관·출입국·외국인관서·하이코리아(1345)에서 확인하세요.',
    badgeVerified: '공식 기준 확인됨',
    badgePartial: '일부 공식 자료',
    badgeRefresh: '공식 최신성 확인 필요',
    badgeOfficialCheck: '공식 확인 필요',
    badgeUnclear: '확인 자료 없음',
    sourceDatePrefix: '기준일',
    linkMissionPage: '공관 안내 페이지',
    linkMissionFinder: '관할 재외공관 찾기',
    linkVisaPortal: '비자포털 확인하기',
    linkHikorea: 'HiKorea 확인하기',
    link1345: '1345 확인 권장',
    tagCountryVaries: '국가별 상이',
    tagOfficialCheck: '공식 확인',
    answerPrompt: '위 질문에 답하면 추천 경로가 나타납니다.',
    ctaHelperFallback: '재외공관 신청, 국내거소신고, 자격변경 중 내 상황에 맞는 흐름을 확인합니다.',
    conditionsHeading: '조건',
    fieldCriminalRecord: '범죄경력증명서',
    fieldAuthentication: '문서 인증(아포스티유/영사확인)',
    fieldBooking: '예약',
    fieldFee: '수수료(사증 수수료)',
    fieldProcessingTime: '처리기간',
    fieldMissionPractice: '공관 실무',
    /* ---- unified guide chrome (new) ---- */
    guideHeader: 'F-4 재외동포 체류자격 안내',
    guideIntro: '재외동포 유형, 국적 이력, 신청 절차에 따라 준비서류와 진행 방식이 달라질 수 있습니다. 몇 가지 질문에 답하면 내 상황에 가까운 준비경로를 확인할 수 있습니다.',
    primaryCta: '내 상황에 맞는 F-4 준비서류 찾기',
    recStartTitle: '추천 시작점',
    recStartBody: 'F-4는 국적 이력, 신청 위치, 거소신고 여부에 따라 준비서류가 달라질 수 있습니다. 세부코드를 몰라도 몇 가지 질문에 답하면 내 상황에 가까운 준비서류와 절차를 확인할 수 있습니다.',
    ctaMicrocopy: '약 1분 · 4~5개 질문 · 세부코드를 몰라도 시작 가능',
    stickyCta: 'F-4 준비서류 찾기 시작',
    secondaryActionsLabel: '다른 방식으로 보기',
    secViewSubcategories: '전체 세부자격 보기',
    secViewCommonDocs: '공통서류 보기',
    secViewProcedure: '신청 절차 보기',
    secViewSources: '공식 근거 보기',
    stepWord: '단계',
    next: '다음',
    restartShort: '다시 시작',
    backToGuide: '← 안내로 돌아가기',
    startGuideShort: '안내 시작하기',
    progressAria: '진행 상황',
    stepSituationQ: '현재 어떤 상황에 가까우신가요?',
    stepNationalityQ: '본인 또는 가족의 대한민국 국적 이력이 있나요?',
    stepLocationQ: '현재 어디에 있나요?',
    stepProcedureQ: '지금 필요한 절차는 무엇인가요?',
    stepConfirmQ: '추가 확인이 필요할 수 있는 항목',
    stepConfirmHelp: '아래 항목은 개별 상황에 따라 추가 확인이 필요할 수 있습니다. 해당하는 항목을 선택하면 결과에 함께 안내합니다. 선택은 선택 사항입니다.',
    optUnsure: '잘 모르겠어요',
    optSitApplyAbroad: '해외에서 F-4 비자를 신청하려고 해요',
    optSitChangeInKorea: '한국에서 F-4로 체류자격을 변경하려고 해요',
    optSitExtension: '이미 F-4이고 기간연장/변경이 필요해요',
    optSitResidence: '거소신고가 필요해요',
    optNatSelfHeld: '과거 대한민국 국적을 보유했던 적이 있어요',
    optNatAncestor: '부모 또는 조부모가 대한민국 국적을 보유했던 적이 있어요',
    optNatNone: '해당 없음',
    optLocInKorea: '한국 내 체류 중',
    optLocOverseas: '해외 체류 중',
    optProcVisa: '사증발급',
    optProcChange: '체류자격변경',
    optProcExtension: '기간연장',
    optProcResidence: '거소신고',
    confNationalityLoss: '국적 상실·이탈 관련 사안',
    confFamilyProof: '가족관계 입증',
    confCriminalRecord: '범죄경력증명서',
    confMilitary: '병역 관련 사안',
    confApostille: '아포스티유·영사확인',
    confTranslation: '번역·공증',
    mayRequireConfirm: '추가 확인이 필요할 수 있습니다',
    officialSourceNeedsConfirm: '공식근거 확인 필요',
    resultTitle: '당신에게 가까운 F-4 준비경로',
    resWhy: '왜 이 경로인가요?',
    resFirstSteps: '먼저 해야 할 일',
    resBasicDocs: '기본 준비서류',
    resAdditionalDocs: '내 상황에서 추가될 수 있는 서류',
    resProcedure: '신청 절차',
    resSources: '공식 근거',
    resNextActions: '다음 행동',
    checklistIntro: '아래 준비서류는 공식 매뉴얼을 정리한 참고용 체크리스트입니다. 항목을 눌러 직접 확인하며 준비하세요.',
    copyChecklist: '체크리스트 복사',
    copied: '복사되었습니다',
    copyFail: '복사하지 못했습니다',
    viewDocDetails: '서류 자세히 보기',
    viewHikoreaGuide: 'HiKorea 예약 안내',
    checkJurisdiction: '관할 기관 확인',
    safetyNote: '개별 사안, 관할 출입국기관 또는 재외공관 판단에 따라 추가서류가 요구될 수 있습니다.',
    routeLabelOverseas: '해외 F-4 사증 신청 검토 경로',
    routeLabelStatusChange: '한국 내 F-4 체류자격변경 검토 경로',
    routeLabelExtension: 'F-4 기간연장/변경 준비 경로',
    routeLabelResidence: '거소신고 준비 경로',
    routeLabelOfficialCheck: '공식 확인이 필요한 경로',
    procStepPrepare: '서류 준비',
    procStepReserve: '필요 시 방문 예약',
    procStepSubmit: '신청서 제출',
    procStepReview: '심사',
    procStepResult: '결과 확인',
    procStepFollowup: '필요 시 후속 등록·증 발급',
    noAdditionalDocsNote: '선택한 추가 항목이 없습니다. 개별 상황에 따라 추가서류가 요구될 수 있으니 관할 기관에서 확인하세요.',
    extensionDocsNote: '기간연장의 구체적 제출서류는 개인 상황과 관할 기관에 따라 다릅니다. 아래 안내와 함께 관할 출입국·외국인관서 또는 하이코리아(1345)에서 확인하세요.',
    officialCheckDocsNote: '먼저 자격·국적 사안을 정리해야 하므로 일반 준비서류 목록을 단정해 안내하지 않습니다. 관할 공관·법무부(하이코리아·1345)에서 확인하세요.',
    subcatHeading: 'F-4 세부 유형'
  };
  var STR_EN = {
    loading: 'Loading F-4 guidance data…',
    fetchFail: 'Could not load F-4 guidance data. Do not proceed without it — please verify directly with your competent Korean mission, HiKorea, or 1345.',
    entryEyebrow: 'Overseas Korean F-4 · Guidance based on official sources',
    startCtaFallback: 'Check F-4 procedures',
    modalAria: 'F-4 overseas Korean guidance',
    close: 'Close',
    back: '← Back',
    restart: 'Start over',
    seeResult: 'See result',
    recommended: 'Recommended path',
    why: 'Why this path?',
    checkFirst: 'Check first',
    nextStep: 'Next step',
    cautions: 'Cautions',
    officialWarn: 'Official verification notice',
    countryGuide: 'Country-specific check',
    openHub: 'View F-4 procedures in detail',
    backToDiagnostic: '← Back to diagnostic',
    hubTitle: 'F-4 procedure guide hub',
    selectCountryLabel: 'Select your country of application or residence',
    selectCountryHint: 'Consular procedures, criminal record certificates, authentication methods, booking, fees, and processing times can vary by country. For unverified countries, only the common F-4 standards are shown.',
    selectCountryPlaceholder: '— Select a country (optional) —',
    noCountrySelected: 'No country selected yet. Only the common F-4 standards are shown. Select a country to also see that country’s consular guidance (where verified).',
    commonRulesHeading: 'Common F-4 standards (all countries)',
    countryRulesHeading: 'Country-specific guidance',
    docsHeading: 'Common required documents',
    stepsHeading: 'Steps',
    sourcesHeading: 'Sources',
    notGuaranteeFootnote: 'This guidance does not guarantee eligibility or approval. Confirm actual application with your competent Korean mission, the immigration office, or HiKorea (1345).',
    badgeVerified: 'Official standard verified',
    badgePartial: 'Partial official sources',
    badgeRefresh: 'Verify official currency',
    badgeOfficialCheck: 'Official check needed',
    badgeUnclear: 'No verification sources',
    sourceDatePrefix: 'As of',
    linkMissionPage: 'Mission information page',
    linkMissionFinder: 'Find your Korean mission',
    linkVisaPortal: 'Check the Visa Portal',
    linkHikorea: 'Check on HiKorea',
    link1345: 'Verify via 1345',
    tagCountryVaries: 'Varies by country',
    tagOfficialCheck: 'Official check',
    answerPrompt: 'Answer the questions above to see your recommended path.',
    ctaHelperFallback: 'Find the flow that fits you among consular application, domestic residence report, and status change.',
    conditionsHeading: 'Conditions',
    fieldCriminalRecord: 'Criminal record certificate',
    fieldAuthentication: 'Document authentication (apostille / consular)',
    fieldBooking: 'Booking',
    fieldFee: 'Fees (visa fee)',
    fieldProcessingTime: 'Processing time',
    fieldMissionPractice: 'Mission practice',
    /* ---- unified guide chrome (new) ---- */
    guideHeader: 'F-4 Overseas Korean Status Guide',
    guideIntro: 'Required documents and procedures may vary depending on your overseas Korean category, nationality history, and application path. Answer a few questions to find the preparation path closest to your situation.',
    primaryCta: 'Find My F-4 Document Checklist',
    recStartTitle: 'Recommended starting point',
    recStartBody: 'F-4 documents and procedures may vary depending on nationality history, application location, and residence registration needs. Even if you do not know your subcategory, answer a few questions to find the document checklist and procedure closest to your situation.',
    ctaMicrocopy: 'About 1 minute · 4–5 questions · No subcategory knowledge needed',
    stickyCta: 'Start F-4 Checklist',
    secondaryActionsLabel: 'Other ways to view this status',
    secViewSubcategories: 'View All Subcategories',
    secViewCommonDocs: 'View Common Documents',
    secViewProcedure: 'View Application Procedure',
    secViewSources: 'View Official Sources',
    stepWord: 'Step',
    next: 'Next',
    restartShort: 'Restart',
    backToGuide: '← Back to guide',
    startGuideShort: 'Start the guide',
    progressAria: 'Progress',
    stepSituationQ: 'Which situation is closest to yours?',
    stepNationalityQ: 'Do you or your family have Korean nationality history?',
    stepLocationQ: 'Where are you currently located?',
    stepProcedureQ: 'Which procedure do you need now?',
    stepConfirmQ: 'Items that may require additional confirmation',
    stepConfirmHelp: 'The items below may require additional confirmation depending on your individual case. Select any that apply and they will appear in your result. This step is optional.',
    optUnsure: 'I am not sure',
    optSitApplyAbroad: 'I want to apply for an F-4 visa from outside Korea',
    optSitChangeInKorea: 'I want to change my status to F-4 inside Korea',
    optSitExtension: 'I already have F-4 and need extension/change guidance',
    optSitResidence: 'I need domestic residence registration guidance',
    optNatSelfHeld: 'I previously held Korean nationality',
    optNatAncestor: 'My parent or grandparent previously held Korean nationality',
    optNatNone: 'Not applicable',
    optLocInKorea: 'I am currently in Korea',
    optLocOverseas: 'I am currently outside Korea',
    optProcVisa: 'Visa issuance',
    optProcChange: 'Change of status',
    optProcExtension: 'Extension of stay',
    optProcResidence: 'Domestic residence registration',
    confNationalityLoss: 'Nationality loss / renunciation',
    confFamilyProof: 'Family relationship proof',
    confCriminalRecord: 'Criminal background certificate',
    confMilitary: 'Military service-related issue',
    confApostille: 'Apostille / consular confirmation',
    confTranslation: 'Translation / notarization',
    mayRequireConfirm: 'May require additional confirmation',
    officialSourceNeedsConfirm: 'Official source needs confirmation',
    resultTitle: 'Your likely F-4 preparation path',
    resWhy: 'Why this path?',
    resFirstSteps: 'First steps',
    resBasicDocs: 'Basic required documents',
    resAdditionalDocs: 'Documents that may be added for your situation',
    resProcedure: 'Procedure',
    resSources: 'Official sources',
    resNextActions: 'Next actions',
    checklistIntro: 'The documents below are a reference checklist compiled from the official manuals. Tap each item to track it as you prepare.',
    copyChecklist: 'Copy checklist',
    copied: 'Copied',
    copyFail: 'Could not copy',
    viewDocDetails: 'View document details',
    viewHikoreaGuide: 'View HiKorea reservation guide',
    checkJurisdiction: 'Check jurisdiction office',
    safetyNote: 'Additional documents may be requested depending on your individual case and the decision of the competent immigration office or Korean consulate.',
    routeLabelOverseas: 'F-4 visa application review path',
    routeLabelStatusChange: 'F-4 change-of-status review path',
    routeLabelExtension: 'F-4 extension/change preparation path',
    routeLabelResidence: 'Domestic residence registration preparation path',
    routeLabelOfficialCheck: 'A path that needs official confirmation',
    procStepPrepare: 'Prepare documents',
    procStepReserve: 'Make a reservation if applicable',
    procStepSubmit: 'Submit application',
    procStepReview: 'Review / screening',
    procStepResult: 'Check result',
    procStepFollowup: 'Complete follow-up registration or card issuance if applicable',
    noAdditionalDocsNote: 'You did not select any additional items. Extra documents may still be requested depending on your individual case — confirm with the competent office.',
    extensionDocsNote: 'The specific documents for an extension depend on your individual case and the competent office. Confirm with the competent immigration office or HiKorea (1345) together with the guidance below.',
    officialCheckDocsNote: 'Because your eligibility/nationality should be resolved first, we do not state a definite document list here. Confirm with your competent mission or the Ministry of Justice (HiKorea / 1345).',
    subcatHeading: 'F-4 sub-categories'
  };
  var STR_PACKS = { ko: STR_KO, en: STR_EN };
  var STR = (typeof Proxy === 'function')
    ? new Proxy({}, { get: function (_t, k) { var p = STR_PACKS[f4Lang()] || STR_KO; return (p[k] != null) ? p[k] : STR_KO[k]; } })
    : STR_KO;

  // Country/overlay display label in the active language (data has labelKo/labelEn).
  function clabel(c) {
    if (!c) return '';
    return (f4Lang() === 'en' && c.labelEn) ? c.labelEn : (c.labelKo || c.labelEn || '');
  }

  var TAB_LABEL_KO = {
    overview: 'F-4 한눈에 보기',
    overseasApplication: '재외공관 신청',
    residenceReport: '국내거소신고/거소증',
    statusChange: '국내 자격변경',
    country: '국가별 확인',
    faq: 'F-4 자주 묻는 질문'
  };
  var TAB_LABEL_EN = {
    overview: 'F-4 at a glance',
    overseasApplication: 'Apply at a mission',
    residenceReport: 'Domestic residence report / card',
    statusChange: 'Status change in Korea',
    country: 'Country-specific',
    faq: 'F-4 FAQ'
  };
  var TAB_LABEL_PACKS = { ko: TAB_LABEL_KO, en: TAB_LABEL_EN };
  var TAB_LABEL = (typeof Proxy === 'function')
    ? new Proxy({}, { get: function (_t, k) { var p = TAB_LABEL_PACKS[f4Lang()] || TAB_LABEL_KO; return (p[k] != null) ? p[k] : TAB_LABEL_KO[k]; } })
    : TAB_LABEL_KO;
  var HUB_TABS = ['overview', 'overseasApplication', 'residenceReport', 'statusChange', 'country', 'faq'];

  function stateBadge(status) {
    var map = {
      verified_official: ['ok', STR.badgeVerified],
      partial_official: ['partial', STR.badgePartial],
      needs_refresh: ['refresh', STR.badgeRefresh],
      official_check_required: ['check', STR.badgeOfficialCheck],
      not_available_or_unclear: ['check', STR.badgeUnclear]
    };
    var m = map[status] || ['check', STR.badgeOfficialCheck];
    return '<span class="f4h-badge f4h-badge-' + m[0] + '">' + esc(m[1]) + '</span>';
  }

  /* ----------------------------------------------------------- module state */
  var state = {
    data: null,
    loadPromise: null,
    // legacy diagnostic answers kept for computeRoute back-compat helpers
    answers: {},
    revealed: 1,
    selectedCountry: '',
    // unified guide state
    config: null,        // active complex-status config (F-4 here)
    view: 'flow',        // 'flow' | 'result' | 'ref' | 'hub'
    stepIndex: 0,
    flowAnswers: {},     // { situation, nationality, location, procedure, confirmations:[] }
    result: null,        // computed result model
    refId: null,         // active reference view id
    hubTab: 'overview',
    modal: null,
    lastFocus: null,
    keyHandler: null
  };

  function loadAll() {
    if (state.data) return Promise.resolve(state.data);
    if (state.loadPromise) return state.loadPromise;
    var fetchJson = function (name) {
      return fetch(DATA_BASE + FILES[name], { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + name);
        return r.json();
      });
    };
    state.loadPromise = Promise.all(['base', 'diagnostic', 'faq', 'countries', 'overlays', 'sources'].map(fetchJson))
      .then(function (arr) {
        var data = { base: arr[0], diagnostic: arr[1], faq: arr[2], countries: arr[3], overlays: arr[4], sources: arr[5] };
        if (!data.base || !data.diagnostic || !data.diagnostic.questions) throw new Error('unexpected F-4 schema');
        state.data = data;
        return data;
      })
      .catch(function (e) { state.loadPromise = null; throw e; });
    return state.loadPromise;
  }

  /* ----------------------------------------------------- diagnostic routing */
  // Computes the recommended route id + optional context note from the LEGACY
  // diagnostic answers. Pure function (exposed for tests). Never promises
  // eligibility. Kept for back-compat with offline validation harnesses.
  function computeRoute(a) {
    a = a || {};
    var nat = a.nationality;
    // Nationality is a routing/caution check ONLY — never an eligibility gate.
    if (nat === 'korean') return { routeId: 'nationality_check', contextNote: 'nationalityKorean' };
    if (nat === 'unsure') return { routeId: 'nationality_check', contextNote: 'nationalityUnsure' };

    var loc = a.location, vs = a.visa_status, rr = a.residence_report, et = a.entry_timing;

    if (vs === 'yes_entered') {
      var noReport = (rr === 'not_yet' || rr === 'unsure' || rr == null);
      if (noReport && et === 'over90') return { routeId: 'official_check', contextNote: 'enteredNoReportOver90' };
      if (noReport) return { routeId: 'residence_report', contextNote: 'enteredNoReportUnder90' };
      return { routeId: 'residence_report' };
    }
    if (vs === 'yes_not_entered') return { routeId: 'overseas_application', contextNote: 'visaIssuedNotEntered' };

    if (loc === 'overseas_apply') return { routeId: 'overseas_application' };
    if (loc === 'need_residence_report') return { routeId: 'residence_report' };
    if (loc === 'domestic_change') return { routeId: 'status_change' };

    if (vs === 'no') return { routeId: 'overseas_application' };
    return { routeId: 'official_check' };
  }

  // Maps the NEW unified one-question-per-step answers to a result route id.
  // Procedure is the strongest signal; situation is the fallback. Pure.
  function computeF4Path(a) {
    a = a || {};
    var proc = a.procedure;
    if (proc === 'visa_issuance') return 'overseas_application';
    if (proc === 'change_of_status') return 'status_change';
    if (proc === 'extension') return 'extension';
    if (proc === 'residence_registration') return 'residence_report';
    var s = a.situation;
    if (s === 'apply_abroad') return 'overseas_application';
    if (s === 'change_in_korea') return 'status_change';
    if (s === 'already_f4_extension') return 'extension';
    if (s === 'residence_registration') return 'residence_report';
    return 'official_check';
  }

  /* ------------------------------------------------------ F-4 flow config */
  // One main question per step. Every question offers a "잘 모르겠어요" path.
  // Step 5 is an optional multi-select of items that may require confirmation.
  var F4_STEPS = [
    { id: 'situation', type: 'single', qKey: 'stepSituationQ', options: [
      { id: 'apply_abroad', key: 'optSitApplyAbroad' },
      { id: 'change_in_korea', key: 'optSitChangeInKorea' },
      { id: 'already_f4_extension', key: 'optSitExtension' },
      { id: 'residence_registration', key: 'optSitResidence' },
      { id: 'not_sure', key: 'optUnsure', unsure: true }
    ] },
    { id: 'nationality', type: 'single', qKey: 'stepNationalityQ', options: [
      { id: 'self_held', key: 'optNatSelfHeld' },
      { id: 'ancestor_held', key: 'optNatAncestor' },
      { id: 'not_sure', key: 'optUnsure', unsure: true },
      { id: 'not_applicable', key: 'optNatNone' }
    ] },
    { id: 'location', type: 'single', qKey: 'stepLocationQ', options: [
      { id: 'in_korea', key: 'optLocInKorea' },
      { id: 'outside_korea', key: 'optLocOverseas' },
      { id: 'not_sure', key: 'optUnsure', unsure: true }
    ] },
    { id: 'procedure', type: 'single', qKey: 'stepProcedureQ', options: [
      { id: 'visa_issuance', key: 'optProcVisa' },
      { id: 'change_of_status', key: 'optProcChange' },
      { id: 'extension', key: 'optProcExtension' },
      { id: 'residence_registration', key: 'optProcResidence' },
      { id: 'not_sure', key: 'optUnsure', unsure: true }
    ] },
    { id: 'confirmations', type: 'multi', qKey: 'stepConfirmQ', helpKey: 'stepConfirmHelp', optional: true, options: [
      { id: 'nationality_loss', key: 'confNationalityLoss' },
      { id: 'family_proof', key: 'confFamilyProof' },
      { id: 'criminal_record', key: 'confCriminalRecord' },
      { id: 'military', key: 'confMilitary' },
      { id: 'apostille', key: 'confApostille' },
      { id: 'translation', key: 'confTranslation' }
    ] }
  ];

  // Result-route → hub section used to source documents/steps/sources. Honest:
  // 'extension' & 'official_check' have no source-backed doc list and say so.
  var ROUTE_HUBTAB = {
    overseas_application: 'overseasApplication',
    residence_report: 'residenceReport',
    status_change: 'statusChange',
    nationality_check: 'overview',
    official_check: 'overview'
  };
  var ROUTE_LABEL_KEY = {
    overseas_application: 'routeLabelOverseas',
    status_change: 'routeLabelStatusChange',
    extension: 'routeLabelExtension',
    residence_report: 'routeLabelResidence',
    nationality_check: 'routeLabelOfficialCheck',
    official_check: 'routeLabelOfficialCheck'
  };

  /* --------------------------------------------------------------- styling */
  function injectStyles() {
    if (document.getElementById('f4HubStyles')) return;
    var css = '' +
'.f4-route-guide{margin:1.1rem 0;}' +
'.f4h-entry,.f4g-hero{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1.15rem 1.2rem;}' +
'.f4h-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.f4h-h2,.f4g-hero-title{font-size:1.2rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .35rem;word-break:keep-all;line-height:1.35;}' +
'.f4h-sub,.f4g-hero-sub{font-size:.9rem;line-height:1.65;color:var(--t2,#4f5552);margin:0 0 .8rem;word-break:keep-all;}' +
'.f4h-badges{display:flex;flex-wrap:wrap;gap:.35rem;margin:.1rem 0 .85rem;}' +
'.f4h-badge{display:inline-block;font-size:.72rem;font-weight:700;padding:.16rem .5rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t2,#4f5552);background:var(--bg2,#f1ece2);}' +
'.f4h-badge-ok{border-color:var(--cSt,#0EA37B);color:var(--cSt,#0a7a5c);background:transparent;}' +
'.f4h-badge-partial{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4h-badge-refresh{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4h-badge-check{border-color:var(--cy,#FF6B5B);color:var(--hlT,#8A3426);background:transparent;}' +
/* primary CTA — the single dominant action */
'.f4g-primary-cta{font:inherit;font-weight:800;font-size:1rem;border-radius:13px;padding:.85rem 1.3rem;cursor:pointer;min-height:52px;border:1px solid var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;display:inline-flex;align-items:center;gap:.5rem;width:100%;justify-content:center;box-shadow:0 2px 10px rgba(47,94,103,.18);}' +
'.f4g-primary-cta:hover{filter:brightness(1.06);}' +
'.f4g-primary-cta:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:2px;}' +
'.f4g-primary-cta .f4g-cta-go{font-size:1.15rem;}' +
'.f4g-hero-preflight{font-size:.76rem;color:var(--t3,#757a76);margin:.55rem 0 0;word-break:keep-all;}' +
/* secondary actions — visually weaker than the primary CTA */
'.f4g-secondary{margin-top:.95rem;padding-top:.8rem;border-top:1px dashed var(--bd2,#ddd3c3);}' +
'.f4g-secondary-label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.04em;color:var(--t3,#757a76);margin:0 0 .45rem;}' +
'.f4g-secondary-row{display:flex;flex-wrap:wrap;gap:.4rem;}' +
'.f4g-secondary-btn{font:inherit;font-size:.8rem;font-weight:600;border-radius:999px;padding:.4rem .8rem;min-height:38px;cursor:pointer;border:1px solid var(--bd,#d1c6b4);background:transparent;color:var(--t2,#4f5552);}' +
'.f4g-secondary-btn:hover{border-color:var(--ac,#2f5e67);color:var(--ac,#2f5e67);}' +
'.f4g-secondary-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
/* full-screen / wide overlay */
'.f4h-overlay{position:fixed;inset:0;z-index:9000;display:none;align-items:center;justify-content:center;padding:1.25rem;background:rgba(20,20,18,.55);}' +
'.f4h-overlay.open{display:flex;}' +
'.f4h-box{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:18px;box-shadow:0 18px 60px rgba(0,0,0,.3);width:min(960px,100%);height:min(760px,94vh);max-height:94vh;display:flex;flex-direction:column;overflow:hidden;}' +
'.f4h-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem;padding:1rem 1.3rem .7rem;border-bottom:1px solid var(--bd2,#e5dccb);flex:0 0 auto;}' +
'.f4h-head-main{min-width:0;}' +
'.f4h-head h2{font-size:1.12rem;font-weight:800;color:var(--t1,#202221);margin:.05rem 0 0;word-break:keep-all;}' +
'.f4g-step-count{font-size:.74rem;font-weight:700;color:var(--ac,#2f5e67);margin:.25rem 0 0;letter-spacing:.04em;}' +
'.f4h-close{font:inherit;font-size:1.2rem;line-height:1;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);border-radius:10px;min-width:42px;min-height:42px;cursor:pointer;flex:0 0 auto;}' +
'.f4h-close:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4g-progress{height:6px;background:var(--bg2,#f1ece2);flex:0 0 auto;}' +
'.f4g-progress-bar{height:100%;background:var(--ac,#2f5e67);border-radius:0 3px 3px 0;transition:width .25s ease;}' +
'.f4h-body{padding:1.1rem 1.3rem 1.2rem;overflow-y:auto;flex:1 1 auto;-webkit-overflow-scrolling:touch;}' +
'.f4g-foot{display:flex;align-items:center;justify-content:space-between;gap:.6rem;padding:.8rem 1.3rem;border-top:1px solid var(--bd2,#e5dccb);background:var(--bg1,#fff);flex:0 0 auto;}' +
'.f4g-foot-btn{font:inherit;font-weight:700;font-size:.9rem;border-radius:11px;padding:.7rem 1.15rem;cursor:pointer;min-height:48px;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);}' +
'.f4g-foot-btn.primary{border-color:var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;}' +
'.f4g-foot-btn:disabled{opacity:.45;cursor:not-allowed;}' +
'.f4g-foot-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
/* steps */
'.f4g-q-title{font-size:1.12rem;font-weight:800;color:var(--t1,#202221);margin:.2rem 0 .3rem;word-break:keep-all;line-height:1.4;}' +
'.f4g-q-help{font-size:.84rem;line-height:1.6;color:var(--t3,#757a76);margin:0 0 .9rem;word-break:keep-all;}' +
'.f4g-opts{display:grid;gap:.55rem;max-width:620px;}' +
'.f4g-opt{font:inherit;text-align:left;background:var(--bgI,#fff);border:1.5px solid var(--bd,#d1c6b4);border-radius:12px;padding:.85rem 1rem;cursor:pointer;min-height:56px;color:var(--t1,#202221);font-size:.95rem;word-break:keep-all;display:flex;align-items:center;gap:.6rem;line-height:1.45;}' +
'.f4g-opt:hover{border-color:var(--ac,#2f5e67);}' +
'.f4g-opt:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4g-opt[aria-pressed="true"]{border-color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));box-shadow:inset 0 0 0 1px var(--ac,#2f5e67);font-weight:700;}' +
'.f4g-opt-mark{flex:0 0 auto;width:22px;height:22px;border-radius:50%;border:2px solid var(--bd,#9b9384);display:inline-flex;align-items:center;justify-content:center;font-size:.8rem;color:#fff;}' +
'.f4g-opt[aria-pressed="true"] .f4g-opt-mark{background:var(--ac,#2f5e67);border-color:var(--ac,#2f5e67);}' +
'.f4g-opt-multi .f4g-opt-mark{border-radius:6px;}' +
'.f4g-opt-unsure{color:var(--t2,#4f5552);font-style:italic;}' +
/* result */
'.f4g-result-title{font-size:.82rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--t3,#757a76);margin:0 0 .35rem;}' +
'.f4g-route-chip{display:inline-block;font-size:1.02rem;font-weight:800;color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));border:1px solid var(--ac,#2f5e67);border-radius:12px;padding:.5rem .85rem;margin:0 0 .9rem;word-break:keep-all;}' +
'.f4g-section{border:1px solid var(--bd2,#e5dccb);border-radius:14px;padding:.85rem 1rem;margin:0 0 .8rem;background:var(--bg1,#fff);}' +
'.f4g-section-title{font-size:.96rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .55rem;word-break:keep-all;display:flex;align-items:center;gap:.4rem;}' +
'.f4g-section-title .f4g-num{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--ac,#2f5e67);color:#fff;font-size:.78rem;font-weight:800;flex:0 0 auto;}' +
'.f4g-checklist{display:grid;gap:.4rem;}' +
'.f4g-chk{display:flex;align-items:flex-start;gap:.6rem;padding:.55rem .7rem;border:1px solid var(--bd,#d1c6b4);border-radius:10px;background:var(--bgI,#fff);cursor:pointer;font-size:.88rem;line-height:1.55;color:var(--t1,#202221);word-break:keep-all;}' +
'.f4g-chk input{margin-top:.18rem;width:18px;height:18px;flex:0 0 auto;accent-color:var(--ac,#2f5e67);}' +
'.f4g-chk:focus-within{outline:2px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4g-intro-line{font-size:.8rem;color:var(--t3,#757a76);margin:0 0 .5rem;word-break:keep-all;}' +
'.f4g-chips{display:flex;flex-wrap:wrap;gap:.35rem;}' +
'.f4g-chip{display:inline-block;font-size:.78rem;font-weight:700;padding:.3rem .6rem;border-radius:999px;border:1.5px solid var(--ac,#2f5e67);color:var(--ac,#2f5e67);background:transparent;}' +
'.f4g-add-item{padding:.55rem .7rem;border:1px dashed var(--cWk,#E68A3A);border-radius:10px;background:var(--bg2,#f7f3ea);margin:.35rem 0;}' +
'.f4g-add-item .f4g-add-tag{display:inline-block;font-size:.68rem;font-weight:800;color:var(--cWk,#a85f1c);border:1px solid var(--cWk,#E68A3A);border-radius:999px;padding:.05rem .45rem;margin-left:.35rem;}' +
'.f4g-add-item .f4g-add-name{font-size:.9rem;font-weight:700;color:var(--t1,#202221);}' +
'.f4g-add-item .f4g-add-note{font-size:.82rem;line-height:1.55;color:var(--t2,#4f5552);margin:.25rem 0 0;word-break:keep-all;}' +
'.f4g-actions{display:flex;flex-wrap:wrap;gap:.45rem;margin:.3rem 0;}' +
'.f4g-act-btn{display:inline-flex;align-items:center;min-height:44px;padding:.45rem .9rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.84rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.f4g-act-btn.primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.f4g-act-btn:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.f4g-act-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
/* shared result/hub copy blocks */
'.f4h-h4{font-size:.82rem;font-weight:800;color:var(--t2,#4f5552);margin:.85rem 0 .3rem;text-transform:none;}' +
'.f4h-p{font-size:.87rem;line-height:1.65;color:var(--t1,#202221);margin:.2rem 0;word-break:keep-all;}' +
'.f4h-ul{margin:.2rem 0;padding-left:1.15rem;}' +
'.f4h-ul li{font-size:.85rem;line-height:1.6;color:var(--t1,#202221);margin:.15rem 0;word-break:keep-all;}' +
'.f4h-chips{display:flex;flex-wrap:wrap;gap:.35rem;}' +
'.f4h-chip{display:inline-block;font-size:.76rem;font-weight:800;padding:.26rem .58rem;border-radius:999px;border:1.5px solid var(--ac,#2f5e67);color:var(--ac,#2f5e67);background:transparent;}' +
'.f4h-warn{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.6rem .75rem;margin:.5rem 0;}' +
'.f4h-warn .f4h-h4{color:var(--hlT,#8A3426);margin-top:0;}' +
'.f4h-warn li,.f4h-warn .f4h-p{color:var(--hlT,#8A3426);}' +
'.f4h-note{background:var(--bg2,#f1ece2);border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.6rem .75rem;margin:.5rem 0;font-size:.84rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;}' +
'.f4h-safety{background:var(--bg2,#f7f3ea);border:1px solid var(--bd,#d1c6b4);border-left:4px solid var(--cWk,#E68A3A);border-radius:10px;padding:.7rem .8rem;margin:.6rem 0 .2rem;font-size:.82rem;line-height:1.6;color:var(--t2,#4f5552);word-break:keep-all;}' +
'.f4h-links{display:flex;flex-wrap:wrap;gap:.45rem;margin:.6rem 0 .2rem;}' +
'.f4h-links a,.f4h-links button{display:inline-flex;align-items:center;min-height:42px;padding:.4rem .85rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.82rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.f4h-links a.primary,.f4h-links button.primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.f4h-links a:hover,.f4h-links button:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.f4h-links a:focus-visible,.f4h-links button:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-q{border:1px solid var(--bd,#d1c6b4);border-radius:12px;padding:.7rem .8rem;margin:0 0 .7rem;background:var(--bgI,#fff);}' +
'.f4h-q-help{font-size:.76rem;color:var(--t3,#757a76);margin:0 0 .5rem;word-break:keep-all;}' +
'.f4h-select{font:inherit;font-size:.9rem;width:100%;min-height:46px;padding:.5rem .6rem;border:1.5px solid var(--bd,#d1c6b4);border-radius:10px;background:var(--bgI,#fff);color:var(--t1,#202221);}' +
'.f4h-tabs{display:flex;flex-wrap:wrap;gap:.3rem;border-bottom:1px solid var(--bd2,#e5dccb);margin-bottom:.7rem;}' +
'.f4h-tab{font:inherit;font-size:.82rem;font-weight:700;border:none;border-bottom:2.5px solid transparent;background:transparent;color:var(--t2,#4f5552);padding:.5rem .55rem;cursor:pointer;min-height:40px;}' +
'.f4h-tab[aria-selected="true"]{color:var(--ac,#2f5e67);border-bottom-color:var(--ac,#2f5e67);}' +
'.f4h-tab:focus-visible{outline:2px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-foot{font-size:.74rem;color:var(--t3,#757a76);margin-top:.8rem;padding-top:.6rem;border-top:1px dashed var(--bd2,#ddd3c3);word-break:keep-all;}' +
'.f4h-faq details{border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.45rem .7rem;margin:.4rem 0;background:var(--bgI,#fff);}' +
'.f4h-faq summary{cursor:pointer;font-size:.86rem;font-weight:800;color:var(--t1,#202221);min-height:34px;display:flex;align-items:center;word-break:keep-all;}' +
'.f4h-faq-group-title{font-size:.92rem;font-weight:800;color:var(--ac,#2f5e67);margin:.9rem 0 .2rem;}' +
'.f4h-tag{display:inline-block;font-size:.68rem;font-weight:700;padding:.1rem .45rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t3,#757a76);margin-left:.35rem;}' +
'.f4h-error{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.8rem;font-size:.88rem;color:var(--hlT,#8A3426);word-break:keep-all;}' +
'body.f4h-modal-open{overflow:hidden;}' +
/* recommended-start block (entry hero) */
'.f4g-recstart{position:relative;}' +
'.f4g-rec-title{font-size:1.18rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 .4rem;display:flex;align-items:center;gap:.45rem;word-break:keep-all;line-height:1.35;}' +
'.f4g-rec-title::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--ac,#2f5e67);display:inline-block;flex:0 0 auto;}' +
'.f4g-rec-body{font-size:.9rem;line-height:1.65;color:var(--t2,#4f5552);margin:0 0 .9rem;word-break:keep-all;}' +
'.f4g-rec-microcopy{font-size:.78rem;color:var(--t3,#757a76);margin:.5rem 0 0;text-align:center;word-break:keep-all;}' +
/* in-card placement: visually distinct, theme-token accent */
'.f4g-hero.f4g-hero-incard{margin:.5rem 0 .2rem;border-color:var(--ac,#2f5e67);border-left-width:4px;background:var(--bg2,#f7f3ea);}' +
/* mobile-only sticky bottom CTA (reinforces the same primary action) */
'.f4g-sticky{position:fixed;left:0;right:0;bottom:0;z-index:8000;padding:.6rem .8rem;padding-bottom:calc(.6rem + env(safe-area-inset-bottom,0px));background:var(--bg1,#fff);border-top:1px solid var(--bd,#d1c6b4);box-shadow:0 -4px 16px rgba(0,0,0,.12);}' +
'.f4g-sticky[hidden]{display:none;}' +
'.f4g-sticky-btn{display:block;width:100%;min-height:50px;font:inherit;font-weight:800;font-size:.95rem;border-radius:12px;border:1px solid var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;cursor:pointer;}' +
'.f4g-sticky-btn:hover{filter:brightness(1.05);}' +
'.f4g-sticky-btn:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:2px;}' +
'@media (min-width:641px){.f4g-sticky{display:none !important;}}' +
'body.f4h-modal-open .f4g-sticky{display:none !important;}' +
'@media (max-width:640px){.f4h-overlay{padding:0;align-items:stretch;}.f4h-box{width:100%;height:100%;max-height:100%;border-radius:0;}.f4g-opts{max-width:none;}.f4g-foot-btn{flex:1 1 auto;text-align:center;}}';
    var style = document.createElement('style');
    style.id = 'f4HubStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------------- entry panel UI */
  // "Recommended starting point" block — the single, dominant F-4 entry. Built
  // as a self-contained block so it can be injected either at the TOP of the
  // F-4 result card (immediately after the title + short summary, before the
  // long subcode/procedure sections) or, as a fallback, into the #f4RouteGuide
  // section. The primary CTA is the obvious recommended next step; the secondary
  // "other ways to view" actions are visually weaker.
  function recStartBlockHtml(data) {
    var d = data.diagnostic;
    var b = data.base;
    // d.title is the cautious pre-flight note kept from the data layer.
    var preflight = (d && d.title) ? '<p class="f4g-hero-preflight">' + esc(d.title) + '</p>' : '';
    var secBtn = function (ref, key) {
      return '<button type="button" class="f4g-secondary-btn" data-f4g-ref="' + ref + '">' + esc(STR[key]) + '</button>';
    };
    return '<div class="f4g-recstart">' +
      '<p class="f4h-eyebrow">' + esc(STR.entryEyebrow) + '</p>' +
      '<h2 class="f4g-rec-title" id="f4RouteGuideTitle">' + esc(STR.recStartTitle) + '</h2>' +
      '<div class="f4h-badges">' + stateBadge(b.sourceStatus) + '<span class="f4h-badge">' + esc(STR.sourceDatePrefix + ': ' + b.lastUpdated) + '</span></div>' +
      '<p class="f4g-rec-body">' + esc(STR.recStartBody) + '</p>' +
      '<button type="button" class="f4g-primary-cta" data-f4g-start>' + esc(STR.primaryCta) + '<span class="f4g-cta-go" aria-hidden="true">→</span></button>' +
      '<p class="f4g-rec-microcopy">' + esc(STR.ctaMicrocopy) + '</p>' +
      '<div class="f4g-secondary">' +
        '<span class="f4g-secondary-label">' + esc(STR.secondaryActionsLabel) + '</span>' +
        '<div class="f4g-secondary-row">' +
          secBtn('subcategories', 'secViewSubcategories') +
          secBtn('commonDocs', 'secViewCommonDocs') +
          secBtn('procedure', 'secViewProcedure') +
          secBtn('sources', 'secViewSources') +
        '</div>' +
      '</div>' +
      preflight +
    '</div>';
  }

  // Section-fallback wrapper (kept for the #f4RouteGuide mount + tests).
  function entryPanelHtml(data) {
    return '<div class="f4g-hero">' + recStartBlockHtml(data) + '</div>';
  }

  function wireEntry(container) {
    var startBtn = container.querySelector('[data-f4g-start]');
    if (startBtn) startBtn.addEventListener('click', function () { openGuide({ view: 'flow' }); });
    container.querySelectorAll('[data-f4g-ref]').forEach(function (btn) {
      btn.addEventListener('click', function () { openGuide({ view: 'ref', refId: btn.getAttribute('data-f4g-ref') }); });
    });
  }

  function mountEntryPanel(section, data, preselectCountry) {
    injectStyles();
    section.innerHTML = entryPanelHtml(data);
    section.hidden = false;
    if (preselectCountry) state.selectedCountry = preselectCountry;
    wireEntry(section);
  }

  // True only when the F-4 card hosting the slot is actually expanded. A
  // collapsed card (.vc without .open) keeps its body — including the slot — in
  // the DOM but visually collapsed (grid-template-rows:0fr), so the slot exists
  // yet the promoted CTA would be invisible. In that case we must NOT claim the
  // in-card injection succeeded, or the standalone fallback gets hidden and the
  // CTA disappears for keyword searches like "국내거소" where F-4 stays collapsed.
  function isCardOpen(slot) {
    var card = (slot && slot.closest) ? slot.closest('.vc') : null;
    // No .vc wrapper (unexpected markup) → treat as visible rather than hide.
    if (!card) return true;
    return card.classList.contains('open');
  }

  // Promote the recommended-start block to the TOP of the F-4 result card via
  // the card's .external-guide-slot (rendered right after the card summary), so
  // the primary CTA is above the fold — never tucked at the bottom or in a
  // corner. Returns true only when the slot exists AND its card is expanded;
  // otherwise the caller keeps the standalone #f4RouteGuide section visible.
  function injectRecStart(data, preselectCountry) {
    injectStyles();
    var slot = document.querySelector('.external-guide-slot[data-guide-slot="F-4"]');
    if (!slot || !isCardOpen(slot)) return false;
    if (preselectCountry) state.selectedCountry = preselectCountry;
    slot.innerHTML = '<div class="f4g-hero f4g-hero-incard">' + recStartBlockHtml(data) + '</div>';
    wireEntry(slot);
    return true;
  }

  /* --------------------------------------------- mobile-only sticky CTA */
  // Reinforces the SAME primary action so the guide stays reachable on small
  // screens without scrolling back up. Mobile-only (CSS) and hidden whenever the
  // guide overlay itself is open, so it never creates a competing path.
  var stickyEl = null;
  function ensureSticky() {
    if (stickyEl) return stickyEl;
    injectStyles();
    stickyEl = document.createElement('div');
    stickyEl.className = 'f4g-sticky';
    stickyEl.id = 'f4gStickyCta';
    stickyEl.hidden = true;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'f4g-sticky-btn';
    btn.textContent = STR.stickyCta;
    btn.addEventListener('click', function () { openGuide({ view: 'flow' }); });
    stickyEl.appendChild(btn);
    document.body.appendChild(stickyEl);
    return stickyEl;
  }
  function showStickyCta() {
    ensureSticky();
    var btn = stickyEl.querySelector('.f4g-sticky-btn');
    if (btn) btn.textContent = STR.stickyCta;
    stickyEl.hidden = false;
  }
  function hideStickyCta() { if (stickyEl) stickyEl.hidden = true; }

  /* --------------------------------------------------------------- overlay */
  function buildOverlay() {
    if (state.modal) return state.modal;
    injectStyles();
    var overlay = document.createElement('div');
    overlay.className = 'f4h-overlay';
    overlay.id = 'f4HubModalOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'f4HubModalTitle');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML =
      '<div class="f4h-box" role="document">' +
        '<div class="f4h-head">' +
          '<div class="f4h-head-main">' +
            '<h2 id="f4HubModalTitle"></h2>' +
            '<p class="f4g-step-count" data-f4g-stepcount aria-live="polite"></p>' +
          '</div>' +
          '<button type="button" class="f4h-close" data-f4h-close aria-label="' + esc(STR.close) + '">✕</button>' +
        '</div>' +
        '<div class="f4g-progress" role="progressbar" aria-label="' + esc(STR.progressAria) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" data-f4g-progress>' +
          '<div class="f4g-progress-bar" data-f4g-progressbar style="width:0%"></div>' +
        '</div>' +
        '<div class="f4h-body" id="f4HubModalBody"></div>' +
        '<div class="f4g-foot" data-f4g-foot></div>' +
      '</div>';
    document.body.appendChild(overlay);
    // Backdrop click closes (informational dialog, safe to dismiss).
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeGuide(); });
    overlay.querySelector('[data-f4h-close]').addEventListener('click', closeGuide);
    state.modal = overlay;
    return overlay;
  }

  function focusables(container) {
    return Array.prototype.slice.call(container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) { return !el.disabled && (el.offsetParent !== null || el === document.activeElement); });
  }

  function onKeydown(e) {
    if (!state.modal || !state.modal.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeGuide(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables(state.modal);
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function openGuide(opts) {
    opts = opts || {};
    return loadAll().then(function () {
      buildOverlay();
      state.lastFocus = document.activeElement;
      state.config = F4_CONFIG;
      if (opts.view === 'ref') { state.view = 'ref'; state.refId = opts.refId || 'subcategories'; state.hubTab = refToHubTab(state.refId); }
      else { state.view = 'flow'; state.stepIndex = 0; state.flowAnswers = { confirmations: [] }; state.result = null; }
      renderGuide();
      state.modal.classList.add('open');
      state.modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('f4h-modal-open');
      if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
      focusFirst();
    }).catch(function () {
      buildOverlay();
      var body = state.modal.querySelector('#f4HubModalBody');
      state.modal.querySelector('#f4HubModalTitle').textContent = STR.modalAria;
      setStepCount('');
      setProgress(0);
      body.innerHTML = '<div class="f4h-error">' + esc(STR.fetchFail) + '</div>';
      renderFooter([
        { label: STR.close, action: 'close', primary: true }
      ]);
      state.modal.classList.add('open');
      state.modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('f4h-modal-open');
      if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
      state.modal.querySelector('[data-f4h-close]').focus();
    });
  }

  function closeGuide() {
    if (!state.modal) return;
    state.modal.classList.remove('open');
    state.modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('f4h-modal-open');
    if (state.keyHandler) { document.removeEventListener('keydown', state.keyHandler, true); state.keyHandler = null; }
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') {
      try { state.lastFocus.focus(); } catch (e) {}
    }
    state.lastFocus = null;
  }

  function focusFirst() {
    if (!state.modal) return;
    var body = state.modal.querySelector('#f4HubModalBody');
    var target = body && body.querySelector('button, a, input, select');
    if (!target) target = state.modal.querySelector('[data-f4h-close]');
    if (target) { try { target.focus(); } catch (e) {} }
  }

  /* ------------------------------------------------------------- rendering */
  function setStepCount(text) {
    var el = state.modal && state.modal.querySelector('[data-f4g-stepcount]');
    if (el) el.textContent = text || '';
  }
  function setProgress(pct) {
    if (!state.modal) return;
    var wrap = state.modal.querySelector('[data-f4g-progress]');
    var bar = state.modal.querySelector('[data-f4g-progressbar]');
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    if (bar) bar.style.width = pct + '%';
    if (wrap) wrap.setAttribute('aria-valuenow', String(pct));
  }
  function renderFooter(buttons) {
    var foot = state.modal && state.modal.querySelector('[data-f4g-foot]');
    if (!foot) return;
    foot.innerHTML = (buttons || []).map(function (b) {
      var attrs = 'type="button" class="f4g-foot-btn' + (b.primary ? ' primary' : '') + '" data-f4g-act="' + b.action + '"' + (b.disabled ? ' disabled' : '');
      return '<button ' + attrs + '>' + esc(b.label) + '</button>';
    }).join('');
    foot.querySelectorAll('[data-f4g-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-f4g-act')); });
    });
  }
  function footAction(action) {
    if (action === 'close') return closeGuide();
    if (action === 'back') return goBack();
    if (action === 'next') return goNext();
    if (action === 'restart') { state.view = 'flow'; state.stepIndex = 0; state.flowAnswers = { confirmations: [] }; state.result = null; renderGuide(); focusFirst(); return; }
    if (action === 'startflow') { state.view = 'flow'; state.stepIndex = 0; state.flowAnswers = { confirmations: [] }; state.result = null; renderGuide(); focusFirst(); return; }
  }

  function renderGuide() {
    if (!state.modal) return;
    if (state.view === 'flow') return renderFlow();
    if (state.view === 'result') return renderResultView();
    if (state.view === 'ref') return renderRefView();
  }

  // -------- guided flow (one question per step)
  function renderFlow() {
    var titleEl = state.modal.querySelector('#f4HubModalTitle');
    var body = state.modal.querySelector('#f4HubModalBody');
    var steps = F4_STEPS;
    var step = steps[state.stepIndex];
    titleEl.textContent = STR.guideHeader;
    var n = state.stepIndex + 1, total = steps.length;
    setStepCount(f4Lang() === 'en' ? (STR.stepWord + ' ' + n + ' / ' + total) : (n + ' / ' + total + ' ' + STR.stepWord));
    setProgress((n / total) * 100);
    body.innerHTML = renderStepHtml(step);
    body.scrollTop = 0;
    wireStep(step, body);
    var answered = stepAnswered(step);
    var isLast = state.stepIndex === steps.length - 1;
    renderFooter([
      { label: STR.back, action: 'back', disabled: state.stepIndex === 0 },
      { label: isLast ? STR.seeResult : STR.next, action: 'next', primary: true, disabled: !answered }
    ]);
  }

  function renderStepHtml(step) {
    var html = '<div class="f4g-step">';
    html += '<h3 class="f4g-q-title">' + esc(STR[step.qKey]) + '</h3>';
    if (step.helpKey) html += '<p class="f4g-q-help">' + esc(STR[step.helpKey]) + '</p>';
    var multi = step.type === 'multi';
    var sel = multi ? (state.flowAnswers.confirmations || []) : state.flowAnswers[step.id];
    html += '<div class="f4g-opts" role="' + (multi ? 'group' : 'radiogroup') + '" aria-label="' + esc(STR[step.qKey]) + '">';
    html += step.options.map(function (o) {
      var pressed = multi ? (sel.indexOf(o.id) !== -1) : (sel === o.id);
      var cls = 'f4g-opt' + (multi ? ' f4g-opt-multi' : '') + (o.unsure ? ' f4g-opt-unsure' : '');
      var mark = '<span class="f4g-opt-mark" aria-hidden="true">' + (pressed ? (multi ? '✓' : '●') : '') + '</span>';
      return '<button type="button" class="' + cls + '" role="' + (multi ? 'checkbox' : 'radio') + '" aria-pressed="' + (pressed ? 'true' : 'false') + '" aria-checked="' + (pressed ? 'true' : 'false') + '" data-f4g-opt="' + esc(o.id) + '">' + mark + '<span>' + esc(STR[o.key]) + '</span></button>';
    }).join('');
    html += '</div>';
    html += '<p class="f4h-foot">' + esc(STR.notGuaranteeFootnote) + '</p>';
    return html + '</div>';
  }

  function stepAnswered(step) {
    if (step.optional) return true;
    if (step.type === 'multi') return true;
    return !!state.flowAnswers[step.id];
  }

  function wireStep(step, body) {
    var multi = step.type === 'multi';
    body.querySelectorAll('[data-f4g-opt]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-f4g-opt');
        if (multi) {
          var arr = state.flowAnswers.confirmations || (state.flowAnswers.confirmations = []);
          var i = arr.indexOf(id);
          if (i === -1) arr.push(id); else arr.splice(i, 1);
        } else {
          state.flowAnswers[step.id] = id;
        }
        renderFlow();
      });
    });
  }

  function goNext() {
    var steps = F4_STEPS;
    var step = steps[state.stepIndex];
    if (!stepAnswered(step)) return;
    if (state.stepIndex < steps.length - 1) { state.stepIndex++; renderFlow(); focusFirst(); return; }
    // Last step → compute + show result.
    state.result = buildResultModel(state.flowAnswers);
    state.view = 'result';
    renderGuide();
    focusFirst();
  }
  function goBack() {
    if (state.view === 'result') { state.view = 'flow'; renderGuide(); focusFirst(); return; }
    if (state.stepIndex > 0) { state.stepIndex--; renderFlow(); focusFirst(); }
  }

  /* ------------------------------------------------------------- result */
  function localizedList(arr) {
    // data arrays are Korean-canonical legal/source content (per i18n policy)
    return (arr || []).slice();
  }

  function buildResultModel(a) {
    var routeId = computeF4Path(a);
    var b = state.data.base;
    var diag = state.data.diagnostic;
    var hubTab = ROUTE_HUBTAB[routeId];
    var route = diag.routes[routeId] || null;
    var hub = hubTab ? b.hub[hubTab] : null;

    var firstSteps = route && route.checkFirst ? localizedList(route.checkFirst) : [];
    var warnings = route && route.warnings ? localizedList(route.warnings) : [];

    // Basic documents (source-backed only).
    var basicDocs = [];
    var basicNote = '';
    if (routeId === 'overseas_application' && hub) basicDocs = localizedList(hub.commonDocs);
    else if (routeId === 'residence_report' && hub) basicDocs = localizedList(hub.docs);
    else if (routeId === 'status_change' && hub) basicDocs = localizedList(hub.docs);
    else if (routeId === 'extension') { basicNote = STR.extensionDocsNote; if (b.common.stayLimitNote) warnings = warnings.concat([b.common.stayLimitNote]); }
    else { basicNote = STR.officialCheckDocsNote; }

    // Procedure steps: prefer source-backed; otherwise the generic process list.
    var procSteps;
    if (hub && Array.isArray(hub.steps) && hub.steps.length) procSteps = localizedList(hub.steps);
    else procSteps = [STR.procStepPrepare, STR.procStepReserve, STR.procStepSubmit, STR.procStepReview, STR.procStepResult, STR.procStepFollowup];

    // Sources: from the relevant hub section (resolvable in sources.json).
    var sourceRefs = (hub && hub.sourceRefs) ? hub.sourceRefs.slice() : (b.hub.overview.sourceRefs || []).slice();

    // Additional docs from Step-5 confirmations (source-backed notes reused).
    var addItems = buildAdditionalItems(a.confirmations || [], b);

    // Always surface the current-Korean-national caution when nationality is
    // unclear / self-held — F-4 is for FOREIGN nationals only.
    var natCaution = '';
    if (a.nationality === 'not_sure' || a.nationality === 'self_held' || routeId === 'nationality_check') {
      natCaution = b.common.nationalityCaution;
    }

    return {
      routeId: routeId,
      labelKey: ROUTE_LABEL_KEY[routeId] || 'routeLabelOfficialCheck',
      why: route ? route.why : '',
      recommended: route ? route.recommended : '',
      firstSteps: firstSteps,
      warnings: warnings,
      basicDocs: basicDocs,
      basicNote: basicNote,
      addItems: addItems,
      procSteps: procSteps,
      sourceRefs: sourceRefs,
      ctas: route && route.ctas ? route.ctas.slice() : ['hikorea', 'call1345', 'missionFinder'],
      natCaution: natCaution
    };
  }

  // Maps a confirmation id → { name, note, sourceBacked } using EXISTING data.
  function buildAdditionalItems(ids, b) {
    var c = b.common;
    var map = {
      criminal_record: { nameKey: 'confCriminalRecord', note: c.criminalRecordCommon, sourceBacked: true },
      apostille: { nameKey: 'confApostille', note: c.criminalRecordCommon, sourceBacked: true },
      translation: { nameKey: 'confTranslation', note: c.criminalRecordCommon, sourceBacked: true },
      military: { nameKey: 'confMilitary', note: c.militaryCaution, sourceBacked: true },
      nationality_loss: { nameKey: 'confNationalityLoss', note: c.nationalityCaution, sourceBacked: true },
      family_proof: { nameKey: 'confFamilyProof', note: '', sourceBacked: false }
    };
    return (ids || []).map(function (id) {
      var m = map[id];
      if (!m) return null;
      return { name: STR[m.nameKey], note: m.note || '', sourceBacked: m.sourceBacked };
    }).filter(Boolean);
  }

  function srcLine(refs) {
    if (!refs || !refs.length) return '';
    var byId = {};
    (state.data.sources.sources || []).forEach(function (s) { byId[s.id] = s; });
    var titles = refs.map(function (id) {
      var s = byId[id];
      return s ? esc(s.title) + (s.sourceDate ? ' (' + esc(s.sourceDate) + ')' : '') : esc(id);
    });
    return '<p class="f4h-foot">' + esc(STR.sourcesHeading) + ': ' + titles.join(' · ') + '</p>';
  }

  function sourceListHtml(refs) {
    if (!refs || !refs.length) return '<p class="f4h-p">' + esc(STR.officialSourceNeedsConfirm) + '</p>';
    var byId = {};
    (state.data.sources.sources || []).forEach(function (s) { byId[s.id] = s; });
    var items = refs.map(function (id) {
      var s = byId[id];
      if (!s) return '<li>' + esc(id) + '</li>';
      var label = esc(s.title) + (s.sourceDate ? ' <span style="color:var(--t3,#757a76);">(' + esc(STR.sourceDatePrefix) + ': ' + esc(s.sourceDate) + ')</span>' : '');
      if (s.url) return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + label + '</a></li>';
      return '<li>' + label + '</li>';
    }).join('');
    return '<ul class="f4h-ul">' + items + '</ul>';
  }

  function numSection(n, titleStr, inner) {
    return '<div class="f4g-section"><p class="f4g-section-title"><span class="f4g-num" aria-hidden="true">' + n + '</span>' + esc(titleStr) + '</p>' + inner + '</div>';
  }

  function renderResultView() {
    var titleEl = state.modal.querySelector('#f4HubModalTitle');
    var body = state.modal.querySelector('#f4HubModalBody');
    var m = state.result;
    titleEl.textContent = STR.guideHeader;
    setStepCount('');
    setProgress(100);

    var html = '<div class="f4g-result" role="status" aria-live="polite">';
    html += '<p class="f4g-result-title">' + esc(STR.resultTitle) + '</p>';
    html += '<div class="f4g-route-chip">' + esc(STR[m.labelKey]) + '</div>';

    // Why this path (cautious; from source data when available).
    if (m.recommended || m.why) {
      var whyInner = (m.recommended ? '<p class="f4h-p">' + esc(m.recommended) + '</p>' : '') +
        (m.why ? '<p class="f4h-p">' + esc(m.why) + '</p>' : '');
      html += '<div class="f4g-section"><p class="f4g-section-title">' + esc(STR.resWhy) + '</p>' + whyInner + '</div>';
    }

    // 1. First steps
    var firstInner = '';
    if (m.firstSteps.length) firstInner += '<div class="f4g-chips">' + m.firstSteps.map(function (s) { return '<span class="f4g-chip">' + esc(s) + '</span>'; }).join('') + '</div>';
    if (m.warnings.length) firstInner += '<div class="f4h-warn"><ul class="f4h-ul">' + m.warnings.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('') + '</ul></div>';
    if (!firstInner) firstInner = '<p class="f4h-p">' + esc(STR.safetyNote) + '</p>';
    html += numSection('1', STR.resFirstSteps, firstInner);

    // 2. Basic required documents (checklist-first)
    var basicInner = '';
    if (m.basicDocs.length) {
      basicInner += '<p class="f4g-intro-line">' + esc(STR.checklistIntro) + '</p>';
      basicInner += '<div class="f4g-checklist">' + m.basicDocs.map(function (doc, i) {
        return '<label class="f4g-chk"><input type="checkbox" data-f4g-doc="' + i + '"><span>' + esc(doc) + '</span></label>';
      }).join('') + '</div>';
    } else {
      basicInner += '<div class="f4h-note">' + stateBadge('official_check_required') + '<br>' + esc(m.basicNote || STR.officialSourceNeedsConfirm) + '</div>';
    }
    html += numSection('2', STR.resBasicDocs, basicInner);

    // 3. Documents that may be added for your situation
    var addInner = '';
    if (m.addItems.length) {
      addInner += m.addItems.map(function (it) {
        var tag = it.sourceBacked ? STR.mayRequireConfirm : STR.officialSourceNeedsConfirm;
        return '<div class="f4g-add-item"><span class="f4g-add-name">' + esc(it.name) + '</span><span class="f4g-add-tag">' + esc(tag) + '</span>' +
          (it.note ? '<p class="f4g-add-note">' + esc(it.note) + '</p>' : '') + '</div>';
      }).join('');
    } else {
      addInner = '<p class="f4h-p">' + esc(STR.noAdditionalDocsNote) + '</p>';
    }
    html += numSection('3', STR.resAdditionalDocs, addInner);

    // 4. Procedure
    html += numSection('4', STR.resProcedure, '<ol class="f4h-ul">' + m.procSteps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>');

    // 5. Official sources
    html += numSection('5', STR.resSources, sourceListHtml(m.sourceRefs));

    // 6. Next actions
    html += numSection('6', STR.resNextActions, renderNextActions(m));

    // Nationality caution (when relevant) + safety note.
    if (m.natCaution) html += '<div class="f4h-warn"><p class="f4h-p">' + esc(m.natCaution) + '</p></div>';
    html += '<div class="f4h-note">' + esc(state.data.base.common.officialCheckWarning) + '</div>';
    html += '<div class="f4h-safety">' + esc(STR.safetyNote) + '</div>';
    html += '</div>';

    body.innerHTML = html;
    body.scrollTop = 0;
    wireResult(body, m);

    renderFooter([
      { label: STR.restartShort, action: 'restart' },
      { label: STR.close, action: 'close', primary: true }
    ]);
  }

  function renderNextActions(m) {
    var b = state.data.base;
    var links = '<button type="button" class="f4g-act-btn primary" data-f4g-copy>' + esc(STR.copyChecklist) + '</button>';
    links += '<button type="button" class="f4g-act-btn" data-f4g-ref="commonDocs">' + esc(STR.viewDocDetails) + '</button>';
    links += '<a class="f4g-act-btn" href="' + esc(b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.viewHikoreaGuide) + '</a>';
    links += '<a class="f4g-act-btn" href="' + esc(b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.checkJurisdiction) + '</a>';
    links += '<button type="button" class="f4g-act-btn" data-f4g-act="restart">' + esc(STR.restartShort) + '</button>';
    return '<div class="f4g-actions">' + links + '</div>';
  }

  function buildChecklistText(m) {
    var lines = [];
    lines.push(STR.resultTitle + ': ' + STR[m.labelKey]);
    if (m.firstSteps.length) { lines.push(''); lines.push('[' + STR.resFirstSteps + ']'); m.firstSteps.forEach(function (s) { lines.push('- ' + s); }); }
    lines.push(''); lines.push('[' + STR.resBasicDocs + ']');
    if (m.basicDocs.length) m.basicDocs.forEach(function (d) { lines.push('[ ] ' + d); });
    else lines.push('- ' + (m.basicNote || STR.officialSourceNeedsConfirm));
    if (m.addItems.length) { lines.push(''); lines.push('[' + STR.resAdditionalDocs + ']'); m.addItems.forEach(function (it) { lines.push('- ' + it.name + ' (' + (it.sourceBacked ? STR.mayRequireConfirm : STR.officialSourceNeedsConfirm) + ')'); }); }
    lines.push(''); lines.push('[' + STR.resProcedure + ']');
    m.procSteps.forEach(function (s, i) { lines.push((i + 1) + '. ' + s); });
    lines.push(''); lines.push(STR.safetyNote);
    return lines.join('\n');
  }

  function wireResult(body, m) {
    var copyBtn = body.querySelector('[data-f4g-copy]');
    if (copyBtn) copyBtn.addEventListener('click', function () {
      var text = buildChecklistText(m);
      var done = function (okState) { copyBtn.textContent = okState ? STR.copied : STR.copyFail; setTimeout(function () { copyBtn.textContent = STR.copyChecklist; }, 1800); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      } else {
        try {
          var ta = document.createElement('textarea');
          ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
          document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
          done(true);
        } catch (e) { done(false); }
      }
    });
    body.querySelectorAll('[data-f4g-ref]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.view = 'ref'; state.refId = btn.getAttribute('data-f4g-ref'); state.hubTab = refToHubTab(state.refId); renderGuide(); focusFirst(); });
    });
    // In-body action buttons (e.g. the "다시 시작" next-action) reuse footAction.
    body.querySelectorAll('[data-f4g-act]').forEach(function (btn) {
      btn.addEventListener('click', function () { footAction(btn.getAttribute('data-f4g-act')); });
    });
  }

  /* ------------------------------------------------------------- ref views */
  // Secondary "jump to reference" views reuse the source-grounded hub content.
  function refToHubTab(refId) {
    if (refId === 'subcategories') return 'overview';
    if (refId === 'commonDocs') return 'overseasApplication';
    if (refId === 'procedure') return 'overseasApplication';
    if (refId === 'sources') return 'overview';
    return 'overview';
  }

  function renderRefView() {
    var titleEl = state.modal.querySelector('#f4HubModalTitle');
    var body = state.modal.querySelector('#f4HubModalBody');
    setStepCount('');
    setProgress(0);
    var refId = state.refId;
    var html = '';
    if (refId === 'sources') {
      titleEl.textContent = STR.secViewSources;
      html = renderSourcesRef();
    } else if (refId === 'commonDocs') {
      titleEl.textContent = STR.secViewCommonDocs;
      html = renderCommonDocsRef();
    } else if (refId === 'subcategories') {
      titleEl.textContent = STR.secViewSubcategories;
      html = renderSubcategoriesRef();
    } else { // procedure → tabbed hub
      titleEl.textContent = STR.secViewProcedure;
      html = renderHub();
    }
    body.innerHTML = html;
    body.scrollTop = 0;
    wireHub(body);
    renderFooter([
      { label: STR.startGuideShort, action: 'startflow' },
      { label: STR.close, action: 'close', primary: true }
    ]);
  }

  function listHtml(arr) {
    return '<ul class="f4h-ul">' + (arr || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
  }

  function commonRulesHtml() {
    var c = state.data.base.common;
    return '<div class="f4h-warn"><p class="f4h-h4">' + esc(STR.commonRulesHeading) + '</p>' +
      '<ul class="f4h-ul">' +
        '<li>' + esc(c.separationWarning) + '</li>' +
        '<li>' + esc(c.deadline90) + '</li>' +
        '<li>' + esc(c.militaryCaution) + '</li>' +
      '</ul></div>';
  }

  function renderSubcategoriesRef() {
    var b = state.data.base;
    var ov = b.hub.overview;
    return '<h3 style="margin:.1rem 0 .35rem;color:var(--ac,#2f5e67);">' + esc(STR.subcatHeading) + '</h3>' +
      '<p class="f4h-p">' + esc(ov.summary) + '</p>' +
      '<p class="f4h-h4">' + esc(b.common.whoTitle) + '</p>' + listHtml(b.common.who) +
      '<p class="f4h-h4">' + esc(b.common.notForTitle) + '</p>' + listHtml(b.common.notFor) +
      commonRulesHtml() + srcLine(ov.sourceRefs);
  }

  function renderCommonDocsRef() {
    var b = state.data.base;
    var s = b.hub.overseasApplication;
    return '<h3 style="margin:.1rem 0 .35rem;color:var(--ac,#2f5e67);">' + esc(STR.docsHeading) + '</h3>' +
      '<p class="f4h-p">' + esc(s.intro) + '</p>' +
      listHtml(s.commonDocs) +
      '<div class="f4h-note">' + esc(b.common.criminalRecordCommon) + '</div>' +
      '<div class="f4h-note">' + esc(b.common.koreanAbilityCommon) + '</div>' +
      '<div class="f4h-safety">' + esc(STR.safetyNote) + '</div>' +
      srcLine(s.sourceRefs);
  }

  function renderSourcesRef() {
    var sources = state.data.sources.sources || [];
    var items = sources.map(function (s) {
      var label = esc(s.title) + (s.sourceDate ? ' <span style="color:var(--t3,#757a76);">(' + esc(STR.sourceDatePrefix) + ': ' + esc(s.sourceDate) + ')</span>' : '');
      if (s.url) return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + label + '</a></li>';
      return '<li>' + label + '</li>';
    }).join('');
    return '<h3 style="margin:.1rem 0 .35rem;color:var(--ac,#2f5e67);">' + esc(STR.resSources) + '</h3>' +
      '<div class="f4h-badges">' + stateBadge(state.data.base.sourceStatus) + '</div>' +
      '<ul class="f4h-ul">' + items + '</ul>' +
      '<div class="f4h-note">' + esc(state.data.base.disclaimer) + '</div>';
  }

  /* ----------------------------------------------------------- hub (ref) */
  function countrySelectHtml() {
    var byRegion = {};
    state.data.countries.countries.forEach(function (c) {
      (byRegion[c.region] = byRegion[c.region] || []).push(c);
    });
    var groups = Object.keys(byRegion).map(function (region) {
      var opts = byRegion[region].map(function (c) {
        var sel = c.countryCode === state.selectedCountry ? ' selected' : '';
        return '<option value="' + esc(c.countryCode) + '"' + sel + '>' + esc(c.labelKo) + ' (' + esc(c.labelEn) + ')</option>';
      }).join('');
      return '<optgroup label="' + esc(region) + '">' + opts + '</optgroup>';
    }).join('');
    return '<label class="f4h-h4" for="f4hCountrySelect">' + esc(STR.selectCountryLabel) + '</label>' +
      '<p class="f4h-q-help">' + esc(STR.selectCountryHint) + '</p>' +
      '<select class="f4h-select" id="f4hCountrySelect" data-f4h-country>' +
        '<option value="">' + esc(STR.selectCountryPlaceholder) + '</option>' + groups +
      '</select>';
  }

  function getOverlay(code) {
    var ov = state.data.overlays && state.data.overlays.overlays;
    return (ov && ov[code]) || null;
  }
  function getCountry(code) {
    var found = null;
    state.data.countries.countries.forEach(function (c) { if (c.countryCode === code) found = c; });
    return found;
  }

  function renderHub() {
    var tabs = HUB_TABS.map(function (t) {
      var sel = t === state.hubTab ? 'true' : 'false';
      return '<button type="button" class="f4h-tab" role="tab" aria-selected="' + sel + '" data-f4h-tab="' + t + '">' + esc(TAB_LABEL[t]) + '</button>';
    }).join('');
    var html = '<div class="f4h-tabs" role="tablist" aria-label="' + esc(STR.hubTitle) + '">' + tabs + '</div>' +
      '<div role="tabpanel">' + renderHubTab(state.hubTab) + '</div>';
    return html;
  }

  function renderHubTab(tab) {
    var b = state.data.base;
    if (tab === 'overview') {
      var ov = b.hub.overview;
      return '<h3 class="f4h-result" style="border:none;margin:0;padding:0;color:var(--ac,#2f5e67);">' + esc(ov.title) + '</h3>' +
        '<p class="f4h-p">' + esc(ov.summary) + '</p>' + listHtml(ov.points) +
        '<p class="f4h-h4">' + esc(b.common.whoTitle) + '</p>' + listHtml(b.common.who) +
        '<p class="f4h-h4">' + esc(b.common.notForTitle) + '</p>' + listHtml(b.common.notFor) +
        commonRulesHtml() + srcLine(ov.sourceRefs);
    }
    if (tab === 'overseasApplication') {
      var s = b.hub.overseasApplication;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(s.title) + '</h3>' +
        '<p class="f4h-p">' + esc(s.intro) + '</p>' +
        '<p class="f4h-h4">' + esc(STR.stepsHeading) + '</p>' + listHtml(s.steps) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(s.commonDocs) +
        '<div class="f4h-note">' + esc(s.note) + '</div>' +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkMissionFinder) + '</a>' +
        '<a href="' + esc(b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkVisaPortal) + '</a></div>' +
        srcLine(s.sourceRefs);
    }
    if (tab === 'residenceReport') {
      var rr = b.hub.residenceReport;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(rr.title) + '</h3>' +
        '<p class="f4h-p">' + esc(rr.intro) + '</p>' +
        '<div class="f4h-warn"><p class="f4h-p">' + esc(rr.warning) + '</p></div>' +
        '<p class="f4h-h4">' + esc(STR.stepsHeading) + '</p>' + listHtml(rr.steps) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(rr.docs) +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkHikorea) + '</a>' +
        '<a href="tel:1345">' + esc(STR.link1345) + '</a></div>' +
        srcLine(rr.sourceRefs);
    }
    if (tab === 'statusChange') {
      var sc = b.hub.statusChange;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(sc.title) + '</h3>' +
        '<p class="f4h-p">' + esc(sc.intro) + '</p>' +
        '<p class="f4h-h4">' + esc(STR.conditionsHeading) + '</p>' + listHtml(sc.conditions) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(sc.docs) +
        '<div class="f4h-note">' + esc(sc.h2Note) + '</div>' +
        '<div class="f4h-note">' + esc(sc.note) + '</div>' +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkHikorea) + '</a>' +
        '<a href="tel:1345">' + esc(STR.link1345) + '</a></div>' +
        srcLine(sc.sourceRefs);
    }
    if (tab === 'country') return renderCountryTab();
    if (tab === 'faq') return renderFaqTab();
    return '';
  }

  function sectionFieldHtml(label, field) {
    if (!field) return '';
    var html = '<p class="f4h-h4">' + esc(label) + ' ' + stateBadge(field.status) + '</p>';
    if (field.summaryKo) html += '<p class="f4h-p">' + esc(field.summaryKo) + '</p>';
    if (field.detailKo && field.detailKo.length) html += listHtml(field.detailKo);
    return html;
  }

  function renderCountryTab() {
    var b = state.data.base;
    var html = '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(STR.countryGuide) + '</h3>' +
      '<div class="f4h-q">' + countrySelectHtml() + '</div>';
    // Common rules ALWAYS stay visibly separate from country specifics.
    html += commonRulesHtml();
    if (!state.selectedCountry) {
      html += '<div class="f4h-note">' + esc(STR.noCountrySelected) + '</div>';
      return html;
    }
    var c = getCountry(state.selectedCountry);
    var ov = getOverlay(state.selectedCountry);
    html += '<p class="f4h-h4">' + esc(STR.countryRulesHeading) + ' · ' + esc(c ? clabel(c) : state.selectedCountry) + '</p>';
    if (!ov) {
      html += '<div class="f4h-note">' + stateBadge('official_check_required') + '<br>' + esc(b.fallbackUnverifiedCountry) + '</div>';
      html += '<div class="f4h-links"><a href="' + esc(b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkMissionFinder) + '</a>' +
        '<a href="' + esc(b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkVisaPortal) + '</a>' +
        '<a href="tel:1345">' + esc(STR.link1345) + '</a></div>';
      return html;
    }
    html += '<div class="f4h-note">' + stateBadge(ov.sourceStatus) + ' ' + esc(ov.sourceStatusReason || '') + '</div>';
    html += sectionFieldHtml(STR.fieldCriminalRecord, ov.criminalRecord);
    html += sectionFieldHtml(STR.fieldAuthentication, ov.authentication);
    html += sectionFieldHtml(STR.fieldBooking, ov.booking);
    html += sectionFieldHtml(STR.fieldFee, ov.fee);
    html += sectionFieldHtml(STR.fieldProcessingTime, ov.processingTime);
    html += sectionFieldHtml(STR.fieldMissionPractice, ov.missionPractice);
    if (ov.warnings && ov.warnings.length) {
      html += '<div class="f4h-warn"><p class="f4h-h4">' + esc(STR.cautions) + '</p>' + listHtml(ov.warnings) + '</div>';
    }
    var links = '<div class="f4h-links">';
    if (ov.missionUrl) links += '<a href="' + esc(ov.missionUrl) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkMissionPage) + '</a>';
    links += '<a href="' + esc(ov.missionFinderUrl || b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkMissionFinder) + '</a>' +
      '<a href="' + esc(ov.visaPortalUrl || b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkVisaPortal) + '</a>' +
      '<a href="' + esc(ov.hikoreaUrl || b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">' + esc(STR.linkHikorea) + '</a>' +
      '<a href="tel:1345">' + esc(STR.link1345) + '</a></div>';
    html += links;
    html += srcLine(ov.sourceRefs);
    return html;
  }

  function renderFaqTab() {
    var faq = state.data.faq;
    var html = '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(faq.title) + '</h3>';
    faq.groups.forEach(function (g) {
      html += '<p class="f4h-faq-group-title">' + esc(g.title) + '</p><div class="f4h-faq">';
      g.items.forEach(function (it) {
        var tags = '';
        if (it.countryVaries) tags += '<span class="f4h-tag">' + esc(STR.tagCountryVaries) + '</span>';
        if (it.officialCheck) tags += '<span class="f4h-tag">' + esc(STR.tagOfficialCheck) + '</span>';
        html += '<details><summary>' + esc(it.q) + tags + '</summary>' +
          '<p class="f4h-p">' + esc(it.a) + '</p>' + srcLine(it.sourceRefs) + '</details>';
      });
      html += '</div>';
    });
    return html;
  }

  function wireHub(body) {
    body.querySelectorAll('[data-f4h-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.hubTab = btn.dataset.f4hTab; renderRefView(); });
    });
    var sel = body.querySelector('[data-f4h-country]');
    if (sel) sel.addEventListener('change', function () { state.selectedCountry = sel.value; renderRefView(); });
  }

  /* ----------------------------------------- F-4 config + reusable engine */
  // F-4 reference config. Other statuses register a config of the same shape.
  var F4_CONFIG = {
    code: 'F-4',
    ensureData: loadAll,
    title: function () { return STR.guideHeader; },
    steps: F4_STEPS,
    computeResult: buildResultModel,
    refViews: ['subcategories', 'commonDocs', 'procedure', 'sources']
  };

  var REGISTRY = { 'F-4': F4_CONFIG };
  var ParadisoComplexGuide = {
    register: function (code, config) { if (code && config) REGISTRY[code] = config; return this; },
    has: function (code) { return !!REGISTRY[code]; },
    open: function (code, opts) {
      opts = opts || {};
      if (code && code !== 'F-4') return false; // only F-4 wired for now
      return openGuide(opts.ref ? { view: 'ref', refId: opts.ref } : { view: 'flow' });
    },
    close: closeGuide,
    isOpen: function () { return !!(state.modal && state.modal.classList.contains('open')); },
    _registry: REGISTRY
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoComplexGuide = ParadisoComplexGuide;

  /* ----------------------------------------------------- public API (tests) */
  var api = {
    STR: STR,
    loadAll: loadAll,
    computeRoute: computeRoute,
    computeF4Path: computeF4Path,
    openGuide: openGuide,
    closeGuide: closeGuide,
    stateBadge: stateBadge,
    // Pure helpers (also used by the offline flow-verification harness):
    F4_STEPS: F4_STEPS,
    buildResultModel: buildResultModel,
    buildChecklistText: buildChecklistText,
    renderStepHtml: renderStepHtml,
    recStartBlockHtml: recStartBlockHtml,
    entryPanelHtml: entryPanelHtml,
    _state: state
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoF4Guide = api;

  if (typeof document === 'undefined') return;

  /* ----------------------------------------------- search-result integration */
  var F4_QUERY = /f-?4|재외동포|동포\s*비자/i;
  var EXTRA_TRIGGERS = ['거소증', '국내거소', '거소신고', 'fbi', '범죄경력', '아포스티유', '영사확인',
    '국적상실', '복수국적', '병역', '이중국적', '자격변경', '재외공관', '국내거소신고'];

  function isF4Relevant(detail) {
    var q = String((detail && detail.query) || '');
    if (F4_QUERY.test(q)) return true;
    var lower = q.toLowerCase();
    for (var i = 0; i < EXTRA_TRIGGERS.length; i++) {
      if (lower.indexOf(EXTRA_TRIGGERS[i]) !== -1) return true;
    }
    var codes = (detail && detail.codes) || [];
    return codes[0] === 'F-4' || (detail && detail.primaryCode === 'F-4');
  }

  // Detect a country mentioned in the query (e.g., "미국 F-4") to preselect.
  function detectCountry(query) {
    if (!state.data) return '';
    var q = String(query || '').toLowerCase();
    var hit = '';
    state.data.countries.countries.forEach(function (c) {
      if (hit) return;
      if (q.indexOf(c.labelKo) !== -1 || (c.labelEn && q.indexOf(c.labelEn.toLowerCase()) !== -1)) hit = c.countryCode;
    });
    return hit;
  }

  document.addEventListener('paradiso:results-rendered', function (e) {
    var section = document.getElementById('f4RouteGuide');
    var detail = e.detail || {};
    if (!isF4Relevant(detail)) {
      if (section) { section.hidden = true; section.innerHTML = ''; }
      hideStickyCta();
      return;
    }
    loadAll().then(function (data) {
      var preselect = detectCountry(detail.query);
      // Prefer promoting the block to the TOP of the F-4 card; only fall back to
      // the standalone section when no F-4 card is present in the results.
      var injected = injectRecStart(data, preselect);
      if (injected) { if (section) { section.hidden = true; section.innerHTML = ''; } }
      else if (section) { mountEntryPanel(section, data, preselect); }
      showStickyCta();
    }).catch(function () {
      hideStickyCta();
      if (!section) return;
      injectStyles();
      section.hidden = false;
      section.innerHTML = '<div class="f4g-hero"><div class="f4h-error">' + esc(STR.fetchFail) + '</div>' +
        '<div class="f4h-links" style="margin-top:.5rem;">' +
          '<a href="https://overseas.mofa.go.kr" target="_blank" rel="noopener noreferrer">' + esc(STR.linkMissionFinder) + '</a>' +
          '<a href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">' + esc(STR.linkHikorea) + '</a>' +
          '<a href="tel:1345">' + esc(STR.link1345) + '</a>' +
        '</div></div>';
    });
  });

  document.addEventListener('paradiso:landing-reset', function () {
    var section = document.getElementById('f4RouteGuide');
    if (section) { section.hidden = true; section.innerHTML = ''; }
    hideStickyCta();
    if (state.modal && state.modal.classList.contains('open')) closeGuide();
  });

  // Live language switch: re-render the open guide and whichever entry surface is
  // active (in-card block or fallback section) so chrome follows the active
  // language without needing to reopen (the Proxy already keeps reopened popups
  // correct).
  window.addEventListener('paradiso-language-applied', function () {
    if (state.modal && state.modal.classList.contains('open') && state.data) {
      try { renderGuide(); } catch (e) { /* noop */ }
    }
    if (!state.data) return;
    try {
      var inCard = document.querySelector('.external-guide-slot[data-guide-slot="F-4"] .f4g-hero-incard');
      var section = document.getElementById('f4RouteGuide');
      if (inCard) { injectRecStart(state.data, state.selectedCountry); if (section) { section.hidden = true; section.innerHTML = ''; } }
      else if (section && !section.hidden) { mountEntryPanel(section, state.data, state.selectedCountry); }
      if (stickyEl && !stickyEl.hidden) { var sb = stickyEl.querySelector('.f4g-sticky-btn'); if (sb) sb.textContent = STR.stickyCta; }
    } catch (e) { /* noop */ }
  });
})();
