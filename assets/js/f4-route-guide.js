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
  // Locales with a full in-module chrome pack. zh-TW is rendered via the zh-CN
  // pack (runtime Traditional conversion handles the displayed glyphs), matching
  // the platform i18n policy. Anything else falls back to Korean canonical.
  var F4_SUPPORTED_LANGS = { en: 1, 'zh-CN': 1, ja: 1, vi: 1, tl: 1, id: 1, ru: 1, fr: 1, es: 1, ar: 1, de: 1 };
  function f4Lang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    if (l === 'zh-TW') return 'zh-CN';
    return F4_SUPPORTED_LANGS[l] ? l : 'ko';
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
    recStartTitle: '상황에 맞는 절차 안내',
    recStartBody: 'F-4는 국적 이력, 신청 위치, 거소신고 여부에 따라 준비서류가 달라질 수 있습니다. 세부코드를 몰라도 몇 가지 질문에 답하면 내 상황에 가까운 준비서류와 절차를 확인할 수 있습니다.',
    ctaMicrocopy: '약 1분 · 4~5개 질문 · 세부코드를 몰라도 시작 가능',
    stickyCta: 'F-4 준비서류 찾기 시작',
    secondaryActionsLabel: '다른 방법으로 찾아보기',
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
    recStartTitle: 'Guided steps for your situation',
    recStartBody: 'F-4 documents and procedures may vary depending on nationality history, application location, and residence registration needs. Even if you do not know your subcategory, answer a few questions to find the document checklist and procedure closest to your situation.',
    ctaMicrocopy: 'About 1 minute · 4–5 questions · No subcategory knowledge needed',
    stickyCta: 'Start F-4 Checklist',
    secondaryActionsLabel: 'Other ways to explore',
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
  var STR_ZH = {
    loading: '正在加载 F-4 指引数据…',
    fetchFail: '无法加载 F-4 指引数据。请勿在没有此指引的情况下办理，请直接向管辖驻外公馆·HiKorea·1345 确认。',
    entryEyebrow: '在外同胞 F-4 · 基于官方依据的指引',
    startCtaFallback: '确认 F-4 手续',
    modalAria: 'F-4 在外同胞指引',
    close: '关闭',
    back: '← 上一步',
    restart: '从头开始',
    seeResult: '查看结果',
    recommended: '推荐路径',
    why: '为什么是这条路径？',
    checkFirst: '首先要确认的事',
    nextStep: '下一步',
    cautions: '注意',
    officialWarn: '官方确认提示',
    countryGuide: '按国家确认',
    openHub: '查看 F-4 手续详情',
    backToDiagnostic: '← 返回诊断',
    hubTitle: 'F-4 手续指引中心',
    selectCountryLabel: '请选择申请国家或居住国家',
    selectCountryHint: '各国公馆手续、犯罪记录证明、认证方式、预约、手续费、处理时间可能不同。未经核实的国家仅提供通用 F-4 标准。',
    selectCountryPlaceholder: '— 选择国家（选填）—',
    noCountrySelected: '尚未选择国家，仅显示通用 F-4 标准。选择国家后，将一并显示该国公馆指引（如已核实）。',
    commonRulesHeading: '通用 F-4 标准（所有国家通用）',
    countryRulesHeading: '按国家指引',
    docsHeading: '通用提交材料',
    stepsHeading: '步骤',
    sourcesHeading: '出处',
    notGuaranteeFootnote: '本指引不保证资格或许可。实际是否适用，请向管辖驻外公馆·出入境·外国人机关·HiKorea（1345）确认。',
    badgeVerified: '已确认官方标准',
    badgePartial: '部分官方资料',
    badgeRefresh: '需确认官方最新性',
    badgeOfficialCheck: '需官方确认',
    badgeUnclear: '无确认资料',
    sourceDatePrefix: '基准日',
    linkMissionPage: '公馆指引页面',
    linkMissionFinder: '查找管辖驻外公馆',
    linkVisaPortal: '确认签证门户',
    linkHikorea: '确认 HiKorea',
    link1345: '建议向 1345 确认',
    tagCountryVaries: '各国不同',
    tagOfficialCheck: '官方确认',
    answerPrompt: '回答上述问题后，将显示推荐路径。',
    ctaHelperFallback: '在驻外公馆申请、国内居所申报、资格变更中，确认符合我情况的流程。',
    conditionsHeading: '条件',
    fieldCriminalRecord: '犯罪记录证明',
    fieldAuthentication: '文件认证（海牙认证/领事认证）',
    fieldBooking: '预约',
    fieldFee: '手续费（签证手续费）',
    fieldProcessingTime: '处理时间',
    fieldMissionPractice: '公馆实务',
    guideHeader: 'F-4 在外同胞居留资格指引',
    guideIntro: '准备材料和办理方式会因在外同胞类型、国籍经历、申请手续而不同。回答几个问题，即可确认与您情况相近的准备路径。',
    primaryCta: '查找符合我情况的 F-4 准备材料',
    recStartTitle: '符合您情况的手续指引',
    recStartBody: 'F-4 的准备材料会因国籍经历、申请地点、是否居所申报而不同。即使不知道子代码，回答几个问题，即可确认与您情况相近的准备材料和手续。',
    ctaMicrocopy: '约 1 分钟 · 4~5 个问题 · 不知道子代码也能开始',
    stickyCta: '开始查找 F-4 准备材料',
    secondaryActionsLabel: '用其他方式查找',
    secViewSubcategories: '查看全部细分资格',
    secViewCommonDocs: '查看通用材料',
    secViewProcedure: '查看申请手续',
    secViewSources: '查看官方依据',
    stepWord: '步骤',
    next: '下一步',
    restartShort: '重新开始',
    backToGuide: '← 返回指引',
    startGuideShort: '开始指引',
    progressAria: '进度',
    stepSituationQ: '您目前更接近哪种情况？',
    stepNationalityQ: '您本人或家人是否有大韩民国国籍经历？',
    stepLocationQ: '您现在在哪里？',
    stepProcedureQ: '您现在需要办理哪项手续？',
    stepConfirmQ: '可能需要额外确认的项目',
    stepConfirmHelp: '以下项目可能依个别情况需要额外确认。选择相关项目后将一并在结果中说明。此选择为选填。',
    optUnsure: '不太清楚',
    optSitApplyAbroad: '我想在海外申请 F-4 签证',
    optSitChangeInKorea: '我想在韩国把居留资格变更为 F-4',
    optSitExtension: '我已是 F-4，需要延期/变更',
    optSitResidence: '我需要办理居所申报',
    optNatSelfHeld: '我曾经持有过大韩民国国籍',
    optNatAncestor: '我的父母或祖父母曾持有大韩民国国籍',
    optNatNone: '不适用',
    optLocInKorea: '在韩国停留中',
    optLocOverseas: '在海外停留中',
    optProcVisa: '签证签发',
    optProcChange: '居留资格变更',
    optProcExtension: '期限延长',
    optProcResidence: '居所申报',
    confNationalityLoss: '国籍丧失·脱离相关事项',
    confFamilyProof: '家庭关系证明',
    confCriminalRecord: '犯罪记录证明',
    confMilitary: '兵役相关事项',
    confApostille: '海牙认证·领事认证',
    confTranslation: '翻译·公证',
    mayRequireConfirm: '可能需要额外确认',
    officialSourceNeedsConfirm: '需确认官方依据',
    resultTitle: '与您情况相近的 F-4 准备路径',
    resWhy: '为什么是这条路径？',
    resFirstSteps: '首先要做的事',
    resBasicDocs: '基本准备材料',
    resAdditionalDocs: '依您情况可能追加的材料',
    resProcedure: '申请手续',
    resSources: '官方依据',
    resNextActions: '下一步行动',
    checklistIntro: '以下准备材料是整理官方手册而成的参考用清单。请点击各项目自行确认并准备。',
    copyChecklist: '复制清单',
    copied: '已复制',
    copyFail: '复制失败',
    viewDocDetails: '查看材料详情',
    viewHikoreaGuide: 'HiKorea 预约指引',
    checkJurisdiction: '确认管辖机关',
    safetyNote: '依个别情形及管辖出入境机关或驻外公馆的判断，可能要求追加材料。',
    routeLabelOverseas: '海外 F-4 签证申请审查路径',
    routeLabelStatusChange: '韩国境内 F-4 居留资格变更审查路径',
    routeLabelExtension: 'F-4 期限延长/变更准备路径',
    routeLabelResidence: '居所申报准备路径',
    routeLabelOfficialCheck: '需要官方确认的路径',
    procStepPrepare: '准备材料',
    procStepReserve: '如需则预约访问',
    procStepSubmit: '提交申请书',
    procStepReview: '审查',
    procStepResult: '确认结果',
    procStepFollowup: '如需则后续登录·发证',
    noAdditionalDocsNote: '未选择任何追加项目。依个别情况可能要求追加材料，请向管辖机关确认。',
    extensionDocsNote: '期限延长的具体提交材料因个人情况和管辖机关而异。请结合下方指引，向管辖出入境·外国人机关或 HiKorea（1345）确认。',
    officialCheckDocsNote: '由于须先理清资格·国籍事项，故不对一般准备材料清单作出断定式指引。请向管辖公馆·法务部（HiKorea·1345）确认。',
    subcatHeading: 'F-4 细分类型'
  };
  var STR_JA = {
    loading: 'F-4 案内データを読み込んでいます…',
    fetchFail: 'F-4 案内データを読み込めませんでした。この案内なしで手続きを進めず、管轄の在外公館・HiKorea・1345 で直接ご確認ください。',
    entryEyebrow: '在外同胞 F-4 · 公式出典に基づく案内',
    startCtaFallback: 'F-4 手続きを確認する',
    modalAria: 'F-4 在外同胞案内',
    close: '閉じる',
    back: '← 戻る',
    restart: '最初からやり直す',
    seeResult: '結果を見る',
    recommended: 'おすすめの経路',
    why: 'なぜこの経路ですか？',
    checkFirst: 'まず確認すること',
    nextStep: '次のステップ',
    cautions: '注意',
    officialWarn: '公式確認のお知らせ',
    countryGuide: '国別の確認',
    openHub: 'F-4 手続きの詳細を見る',
    backToDiagnostic: '← 診断に戻る',
    hubTitle: 'F-4 手続き案内ハブ',
    selectCountryLabel: '申請国または居住国を選択してください',
    selectCountryHint: '国によって公館の手続き、犯罪経歴証明書、認証方式、予約、手数料、処理期間が異なる場合があります。未検証の国については共通 F-4 基準のみを案内します。',
    selectCountryPlaceholder: '— 国を選択（任意）—',
    noCountrySelected: 'まだ国を選択していません。共通 F-4 基準のみが表示されます。国を選択すると、その国の公館案内（検証済みの場合）も併せて表示されます。',
    commonRulesHeading: '共通 F-4 基準（すべての国に共通）',
    countryRulesHeading: '国別の案内',
    docsHeading: '共通提出書類',
    stepsHeading: 'ステップ',
    sourcesHeading: '出典',
    notGuaranteeFootnote: 'この案内は資格や許可を保証するものではありません。実際の適用可否は、管轄の在外公館・出入国・外国人官署・HiKorea（1345）でご確認ください。',
    badgeVerified: '公式基準を確認済み',
    badgePartial: '一部公式資料',
    badgeRefresh: '公式の最新性の確認が必要',
    badgeOfficialCheck: '公式確認が必要',
    badgeUnclear: '確認資料なし',
    sourceDatePrefix: '基準日',
    linkMissionPage: '公館案内ページ',
    linkMissionFinder: '管轄の在外公館を探す',
    linkVisaPortal: 'ビザポータルで確認する',
    linkHikorea: 'HiKorea で確認する',
    link1345: '1345 での確認を推奨',
    tagCountryVaries: '国により異なる',
    tagOfficialCheck: '公式確認',
    answerPrompt: '上の質問に答えると、おすすめの経路が表示されます。',
    ctaHelperFallback: '在外公館での申請、国内居所申告、資格変更のうち、ご自身の状況に合う流れを確認します。',
    conditionsHeading: '条件',
    fieldCriminalRecord: '犯罪経歴証明書',
    fieldAuthentication: '文書認証（アポスティーユ／領事確認）',
    fieldBooking: '予約',
    fieldFee: '手数料（査証手数料）',
    fieldProcessingTime: '処理期間',
    fieldMissionPractice: '公館の実務',
    guideHeader: 'F-4 在外同胞 在留資格案内',
    guideIntro: '在外同胞の類型、国籍履歴、申請手続きによって、準備書類や進め方が異なる場合があります。いくつかの質問に答えると、ご自身の状況に近い準備経路を確認できます。',
    primaryCta: '私の状況に合う F-4 準備書類を探す',
    recStartTitle: '状況に合った手続き案内',
    recStartBody: 'F-4 は国籍履歴、申請場所、居所申告の有無によって準備書類が異なる場合があります。サブコードがわからなくても、いくつかの質問に答えれば、ご自身の状況に近い準備書類と手続きを確認できます。',
    ctaMicrocopy: '約1分 · 4〜5個の質問 · サブコードを知らなくても開始可能',
    stickyCta: 'F-4 準備書類探しを開始',
    secondaryActionsLabel: '別の方法で探す',
    secViewSubcategories: '全ての細分資格を見る',
    secViewCommonDocs: '共通書類を見る',
    secViewProcedure: '申請手続きを見る',
    secViewSources: '公式根拠を見る',
    stepWord: 'ステップ',
    next: '次へ',
    restartShort: 'やり直す',
    backToGuide: '← 案内に戻る',
    startGuideShort: '案内を開始する',
    progressAria: '進行状況',
    stepSituationQ: '現在、どの状況に近いですか？',
    stepNationalityQ: 'ご本人またはご家族に大韓民国の国籍履歴はありますか？',
    stepLocationQ: '現在どこにいますか？',
    stepProcedureQ: '今必要な手続きは何ですか？',
    stepConfirmQ: '追加の確認が必要となる可能性のある項目',
    stepConfirmHelp: '以下の項目は、個別の状況によって追加の確認が必要となる場合があります。該当する項目を選択すると、結果に併せて案内します。この選択は任意です。',
    optUnsure: 'よくわかりません',
    optSitApplyAbroad: '海外で F-4 ビザを申請しようとしています',
    optSitChangeInKorea: '韓国で在留資格を F-4 に変更しようとしています',
    optSitExtension: 'すでに F-4 で、期間延長／変更が必要です',
    optSitResidence: '居所申告が必要です',
    optNatSelfHeld: '過去に大韓民国の国籍を保有していたことがあります',
    optNatAncestor: '父母または祖父母が大韓民国の国籍を保有していたことがあります',
    optNatNone: '該当なし',
    optLocInKorea: '韓国に滞在中',
    optLocOverseas: '海外に滞在中',
    optProcVisa: '査証発給',
    optProcChange: '在留資格変更',
    optProcExtension: '期間延長',
    optProcResidence: '居所申告',
    confNationalityLoss: '国籍喪失・離脱に関する事項',
    confFamilyProof: '家族関係の立証',
    confCriminalRecord: '犯罪経歴証明書',
    confMilitary: '兵役に関する事項',
    confApostille: 'アポスティーユ・領事確認',
    confTranslation: '翻訳・公証',
    mayRequireConfirm: '追加の確認が必要となる場合があります',
    officialSourceNeedsConfirm: '公式根拠の確認が必要',
    resultTitle: 'あなたに近い F-4 準備経路',
    resWhy: 'なぜこの経路ですか？',
    resFirstSteps: 'まずすべきこと',
    resBasicDocs: '基本準備書類',
    resAdditionalDocs: 'あなたの状況で追加される可能性のある書類',
    resProcedure: '申請手続き',
    resSources: '公式根拠',
    resNextActions: '次の行動',
    checklistIntro: '以下の準備書類は、公式マニュアルを整理した参考用チェックリストです。各項目を押して、ご自身で確認しながら準備してください。',
    copyChecklist: 'チェックリストをコピー',
    copied: 'コピーしました',
    copyFail: 'コピーできませんでした',
    viewDocDetails: '書類の詳細を見る',
    viewHikoreaGuide: 'HiKorea 予約案内',
    checkJurisdiction: '管轄機関を確認',
    safetyNote: '個別の事案や、管轄の出入国機関または在外公館の判断によって、追加書類が求められる場合があります。',
    routeLabelOverseas: '海外 F-4 査証申請の検討経路',
    routeLabelStatusChange: '韓国内 F-4 在留資格変更の検討経路',
    routeLabelExtension: 'F-4 期間延長／変更の準備経路',
    routeLabelResidence: '居所申告の準備経路',
    routeLabelOfficialCheck: '公式確認が必要な経路',
    procStepPrepare: '書類の準備',
    procStepReserve: '必要に応じて訪問予約',
    procStepSubmit: '申請書の提出',
    procStepReview: '審査',
    procStepResult: '結果の確認',
    procStepFollowup: '必要に応じて後続の登録・証の発給',
    noAdditionalDocsNote: '追加項目が選択されていません。個別の状況によって追加書類が求められる場合がありますので、管轄機関でご確認ください。',
    extensionDocsNote: '期間延長の具体的な提出書類は、個人の状況や管轄機関によって異なります。以下の案内とあわせて、管轄の出入国・外国人官署または HiKorea（1345）でご確認ください。',
    officialCheckDocsNote: 'まず資格・国籍に関する事項を整理する必要があるため、一般的な準備書類リストを断定的には案内しません。管轄の公館・法務部（HiKorea・1345）でご確認ください。',
    subcatHeading: 'F-4 細分類型'
  };
  var STR_VI = {
    loading: 'Đang tải dữ liệu hướng dẫn F-4…',
    fetchFail: 'Không thể tải dữ liệu hướng dẫn F-4. Vui lòng không tiến hành khi chưa có hướng dẫn này; hãy xác nhận trực tiếp với cơ quan đại diện Hàn Quốc có thẩm quyền, HiKorea hoặc 1345.',
    entryEyebrow: 'Kiều bào F-4 · Hướng dẫn dựa trên nguồn chính thức',
    startCtaFallback: 'Kiểm tra thủ tục F-4',
    modalAria: 'Hướng dẫn kiều bào F-4',
    close: 'Đóng',
    back: '← Quay lại',
    restart: 'Bắt đầu lại',
    seeResult: 'Xem kết quả',
    recommended: 'Lộ trình đề xuất',
    why: 'Vì sao chọn lộ trình này?',
    checkFirst: 'Cần kiểm tra trước',
    nextStep: 'Bước tiếp theo',
    cautions: 'Lưu ý',
    officialWarn: 'Thông báo xác minh chính thức',
    countryGuide: 'Kiểm tra theo quốc gia',
    openHub: 'Xem chi tiết thủ tục F-4',
    backToDiagnostic: '← Quay lại chẩn đoán',
    hubTitle: 'Trung tâm hướng dẫn thủ tục F-4',
    selectCountryLabel: 'Chọn quốc gia nộp hồ sơ hoặc quốc gia cư trú',
    selectCountryHint: 'Thủ tục lãnh sự, giấy chứng nhận lý lịch tư pháp, phương thức chứng thực, đặt lịch, lệ phí và thời gian xử lý có thể khác nhau tùy quốc gia. Với những quốc gia chưa được xác minh, chỉ hiển thị tiêu chuẩn F-4 chung.',
    selectCountryPlaceholder: '— Chọn quốc gia (tùy chọn) —',
    noCountrySelected: 'Bạn chưa chọn quốc gia. Chỉ hiển thị tiêu chuẩn F-4 chung. Khi chọn quốc gia, hướng dẫn lãnh sự của quốc gia đó (nếu đã xác minh) cũng sẽ được hiển thị.',
    commonRulesHeading: 'Tiêu chuẩn F-4 chung (áp dụng cho mọi quốc gia)',
    countryRulesHeading: 'Hướng dẫn theo quốc gia',
    docsHeading: 'Giấy tờ nộp chung',
    stepsHeading: 'Các bước',
    sourcesHeading: 'Nguồn',
    notGuaranteeFootnote: 'Hướng dẫn này không bảo đảm tư cách hay sự chấp thuận. Về khả năng áp dụng thực tế, vui lòng xác nhận với cơ quan đại diện Hàn Quốc có thẩm quyền, cơ quan xuất nhập cảnh hoặc HiKorea (1345).',
    badgeVerified: 'Đã xác minh tiêu chuẩn chính thức',
    badgePartial: 'Một phần tài liệu chính thức',
    badgeRefresh: 'Cần xác minh tính cập nhật chính thức',
    badgeOfficialCheck: 'Cần xác minh chính thức',
    badgeUnclear: 'Không có tài liệu xác minh',
    sourceDatePrefix: 'Tính đến',
    linkMissionPage: 'Trang thông tin cơ quan đại diện',
    linkMissionFinder: 'Tìm cơ quan đại diện Hàn Quốc',
    linkVisaPortal: 'Kiểm tra Cổng thị thực',
    linkHikorea: 'Kiểm tra trên HiKorea',
    link1345: 'Nên xác minh qua 1345',
    tagCountryVaries: 'Khác nhau theo quốc gia',
    tagOfficialCheck: 'Xác minh chính thức',
    answerPrompt: 'Trả lời các câu hỏi ở trên để xem lộ trình đề xuất.',
    ctaHelperFallback: 'Tìm quy trình phù hợp với bạn trong số: nộp hồ sơ tại cơ quan lãnh sự, khai báo cư trú trong nước và thay đổi tư cách.',
    conditionsHeading: 'Điều kiện',
    fieldCriminalRecord: 'Giấy chứng nhận lý lịch tư pháp',
    fieldAuthentication: 'Chứng thực giấy tờ (apostille / lãnh sự)',
    fieldBooking: 'Đặt lịch',
    fieldFee: 'Lệ phí (lệ phí thị thực)',
    fieldProcessingTime: 'Thời gian xử lý',
    fieldMissionPractice: 'Thực tiễn của cơ quan đại diện',
    guideHeader: 'Hướng dẫn tư cách lưu trú kiều bào F-4',
    guideIntro: 'Giấy tờ chuẩn bị và cách tiến hành có thể khác nhau tùy theo loại kiều bào, lịch sử quốc tịch và thủ tục nộp hồ sơ. Trả lời vài câu hỏi để tìm lộ trình chuẩn bị gần với tình huống của bạn.',
    primaryCta: 'Tìm giấy tờ chuẩn bị F-4 phù hợp với tôi',
    recStartTitle: 'Hướng dẫn thủ tục theo tình huống của bạn',
    recStartBody: 'Giấy tờ chuẩn bị F-4 có thể khác nhau tùy theo lịch sử quốc tịch, nơi nộp hồ sơ và việc khai báo cư trú. Dù không biết mã phụ, chỉ cần trả lời vài câu hỏi là bạn có thể tìm được giấy tờ và thủ tục gần với tình huống của mình.',
    ctaMicrocopy: 'Khoảng 1 phút · 4–5 câu hỏi · Không cần biết mã phụ vẫn bắt đầu được',
    stickyCta: 'Bắt đầu tìm giấy tờ F-4',
    secondaryActionsLabel: 'Tìm bằng cách khác',
    secViewSubcategories: 'Xem tất cả tư cách chi tiết',
    secViewCommonDocs: 'Xem giấy tờ chung',
    secViewProcedure: 'Xem thủ tục nộp hồ sơ',
    secViewSources: 'Xem căn cứ chính thức',
    stepWord: 'Bước',
    next: 'Tiếp theo',
    restartShort: 'Bắt đầu lại',
    backToGuide: '← Quay lại hướng dẫn',
    startGuideShort: 'Bắt đầu hướng dẫn',
    progressAria: 'Tiến độ',
    stepSituationQ: 'Hiện tại bạn gần với tình huống nào nhất?',
    stepNationalityQ: 'Bạn hoặc gia đình có lịch sử quốc tịch Hàn Quốc không?',
    stepLocationQ: 'Hiện tại bạn đang ở đâu?',
    stepProcedureQ: 'Thủ tục bạn cần ngay bây giờ là gì?',
    stepConfirmQ: 'Các mục có thể cần xác nhận thêm',
    stepConfirmHelp: 'Các mục dưới đây có thể cần xác nhận thêm tùy theo trường hợp cá nhân. Chọn những mục phù hợp và chúng sẽ được hiển thị trong kết quả. Bước này là tùy chọn.',
    optUnsure: 'Tôi không chắc',
    optSitApplyAbroad: 'Tôi muốn xin thị thực F-4 từ bên ngoài Hàn Quốc',
    optSitChangeInKorea: 'Tôi muốn thay đổi tư cách lưu trú sang F-4 tại Hàn Quốc',
    optSitExtension: 'Tôi đã có F-4 và cần gia hạn/thay đổi',
    optSitResidence: 'Tôi cần khai báo cư trú',
    optNatSelfHeld: 'Trước đây tôi từng có quốc tịch Hàn Quốc',
    optNatAncestor: 'Cha mẹ hoặc ông bà tôi từng có quốc tịch Hàn Quốc',
    optNatNone: 'Không áp dụng',
    optLocInKorea: 'Đang ở Hàn Quốc',
    optLocOverseas: 'Đang ở nước ngoài',
    optProcVisa: 'Cấp thị thực',
    optProcChange: 'Thay đổi tư cách lưu trú',
    optProcExtension: 'Gia hạn thời gian lưu trú',
    optProcResidence: 'Khai báo cư trú',
    confNationalityLoss: 'Vấn đề liên quan đến mất/từ bỏ quốc tịch',
    confFamilyProof: 'Chứng minh quan hệ gia đình',
    confCriminalRecord: 'Giấy chứng nhận lý lịch tư pháp',
    confMilitary: 'Vấn đề liên quan đến nghĩa vụ quân sự',
    confApostille: 'Apostille · chứng thực lãnh sự',
    confTranslation: 'Dịch thuật · công chứng',
    mayRequireConfirm: 'Có thể cần xác nhận thêm',
    officialSourceNeedsConfirm: 'Cần xác nhận căn cứ chính thức',
    resultTitle: 'Lộ trình chuẩn bị F-4 gần với bạn',
    resWhy: 'Vì sao chọn lộ trình này?',
    resFirstSteps: 'Việc cần làm trước tiên',
    resBasicDocs: 'Giấy tờ chuẩn bị cơ bản',
    resAdditionalDocs: 'Giấy tờ có thể được bổ sung cho tình huống của bạn',
    resProcedure: 'Thủ tục nộp hồ sơ',
    resSources: 'Căn cứ chính thức',
    resNextActions: 'Hành động tiếp theo',
    checklistIntro: 'Các giấy tờ dưới đây là danh sách kiểm tra tham khảo được tổng hợp từ sổ tay hướng dẫn chính thức. Hãy nhấn vào từng mục để tự kiểm tra trong khi chuẩn bị.',
    copyChecklist: 'Sao chép danh sách',
    copied: 'Đã sao chép',
    copyFail: 'Không thể sao chép',
    viewDocDetails: 'Xem chi tiết giấy tờ',
    viewHikoreaGuide: 'Hướng dẫn đặt lịch HiKorea',
    checkJurisdiction: 'Kiểm tra cơ quan có thẩm quyền',
    safetyNote: 'Tùy theo trường hợp cá nhân và quyết định của cơ quan xuất nhập cảnh có thẩm quyền hoặc cơ quan đại diện Hàn Quốc, có thể yêu cầu giấy tờ bổ sung.',
    routeLabelOverseas: 'Lộ trình xem xét nộp hồ sơ thị thực F-4 ở nước ngoài',
    routeLabelStatusChange: 'Lộ trình xem xét thay đổi tư cách F-4 tại Hàn Quốc',
    routeLabelExtension: 'Lộ trình chuẩn bị gia hạn/thay đổi F-4',
    routeLabelResidence: 'Lộ trình chuẩn bị khai báo cư trú',
    routeLabelOfficialCheck: 'Lộ trình cần xác nhận chính thức',
    procStepPrepare: 'Chuẩn bị giấy tờ',
    procStepReserve: 'Đặt lịch nếu cần',
    procStepSubmit: 'Nộp đơn',
    procStepReview: 'Thẩm tra / xét duyệt',
    procStepResult: 'Kiểm tra kết quả',
    procStepFollowup: 'Hoàn tất đăng ký tiếp theo hoặc cấp thẻ nếu cần',
    noAdditionalDocsNote: 'Bạn chưa chọn mục bổ sung nào. Vẫn có thể được yêu cầu giấy tờ bổ sung tùy theo trường hợp cá nhân — hãy xác nhận với cơ quan có thẩm quyền.',
    extensionDocsNote: 'Giấy tờ cụ thể cho việc gia hạn phụ thuộc vào trường hợp cá nhân và cơ quan có thẩm quyền. Hãy xác nhận với cơ quan xuất nhập cảnh có thẩm quyền hoặc HiKorea (1345) cùng với hướng dẫn dưới đây.',
    officialCheckDocsNote: 'Vì cần làm rõ tư cách/quốc tịch trước, chúng tôi không nêu danh sách giấy tờ chắc chắn ở đây. Hãy xác nhận với cơ quan đại diện có thẩm quyền hoặc Bộ Tư pháp (HiKorea / 1345).',
    subcatHeading: 'Các loại chi tiết F-4'
  };
  var STR_TL = {
    loading: 'Naglo-load ng datos ng gabay sa F-4…',
    fetchFail: 'Hindi ma-load ang datos ng gabay sa F-4. Huwag magpatuloy nang wala ito — mangyaring direktang kumpirmahin sa may-kapangyarihang misyon ng Korea, sa HiKorea, o sa 1345.',
    entryEyebrow: 'Overseas Korean F-4 · Gabay batay sa opisyal na mga pinagmulan',
    startCtaFallback: 'Tingnan ang mga proseso ng F-4',
    modalAria: 'Gabay sa overseas Korean F-4',
    close: 'Isara',
    back: '← Bumalik',
    restart: 'Magsimula muli',
    seeResult: 'Tingnan ang resulta',
    recommended: 'Inirerekomendang landas',
    why: 'Bakit ang landas na ito?',
    checkFirst: 'Suriin muna',
    nextStep: 'Susunod na hakbang',
    cautions: 'Mga babala',
    officialWarn: 'Paunawa sa opisyal na pagpapatunay',
    countryGuide: 'Pagsuri ayon sa bansa',
    openHub: 'Tingnan nang detalyado ang mga proseso ng F-4',
    backToDiagnostic: '← Bumalik sa diagnostic',
    hubTitle: 'Hub ng gabay sa proseso ng F-4',
    selectCountryLabel: 'Piliin ang iyong bansa ng aplikasyon o paninirahan',
    selectCountryHint: 'Maaaring mag-iba ang mga prosesong konsular, sertipiko ng kriminal na rekord, paraan ng pagpapatunay, booking, bayarin, at oras ng pagproseso depende sa bansa. Para sa mga hindi pa naberipikang bansa, ang karaniwang pamantayan lamang ng F-4 ang ipinapakita.',
    selectCountryPlaceholder: '— Pumili ng bansa (opsyonal) —',
    noCountrySelected: 'Wala pang napiling bansa. Ang karaniwang pamantayan lamang ng F-4 ang ipinapakita. Pumili ng bansa upang makita rin ang konsular na gabay ng bansang iyon (kung naberipika).',
    commonRulesHeading: 'Karaniwang pamantayan ng F-4 (lahat ng bansa)',
    countryRulesHeading: 'Gabay ayon sa bansa',
    docsHeading: 'Karaniwang mga isinusumiteng dokumento',
    stepsHeading: 'Mga hakbang',
    sourcesHeading: 'Mga pinagmulan',
    notGuaranteeFootnote: 'Ang gabay na ito ay hindi gumagarantiya ng pagiging karapat-dapat o pag-apruba. Kumpirmahin ang aktwal na aplikasyon sa may-kapangyarihang misyon ng Korea, sa tanggapan ng imigrasyon, o sa HiKorea (1345).',
    badgeVerified: 'Naberipika ang opisyal na pamantayan',
    badgePartial: 'Bahagyang opisyal na mga pinagmulan',
    badgeRefresh: 'Kailangang patunayan ang opisyal na pagiging napapanahon',
    badgeOfficialCheck: 'Kailangan ng opisyal na pagsuri',
    badgeUnclear: 'Walang mapagkukunan ng pagpapatunay',
    sourceDatePrefix: 'Sa petsang',
    linkMissionPage: 'Pahina ng impormasyon ng misyon',
    linkMissionFinder: 'Hanapin ang iyong misyon ng Korea',
    linkVisaPortal: 'Tingnan ang Visa Portal',
    linkHikorea: 'Tingnan sa HiKorea',
    link1345: 'Patunayan sa pamamagitan ng 1345',
    tagCountryVaries: 'Nag-iiba ayon sa bansa',
    tagOfficialCheck: 'Opisyal na pagsuri',
    answerPrompt: 'Sagutin ang mga tanong sa itaas upang makita ang inirerekomendang landas.',
    ctaHelperFallback: 'Hanapin ang daloy na akma sa iyo mula sa konsular na aplikasyon, lokal na pag-uulat ng paninirahan, at pagbabago ng katayuan.',
    conditionsHeading: 'Mga kondisyon',
    fieldCriminalRecord: 'Sertipiko ng kriminal na rekord',
    fieldAuthentication: 'Pagpapatunay ng dokumento (apostille / konsular)',
    fieldBooking: 'Booking',
    fieldFee: 'Bayarin (bayad sa visa)',
    fieldProcessingTime: 'Oras ng pagproseso',
    fieldMissionPractice: 'Praktika ng misyon',
    guideHeader: 'Gabay sa katayuan ng paninirahan ng Overseas Korean F-4',
    guideIntro: 'Maaaring mag-iba ang mga kinakailangang dokumento at proseso depende sa iyong kategorya bilang overseas Korean, kasaysayan ng nasyonalidad, at landas ng aplikasyon. Sagutin ang ilang tanong upang mahanap ang landas ng paghahanda na pinakamalapit sa iyong sitwasyon.',
    primaryCta: 'Hanapin ang aking checklist ng dokumento sa F-4',
    recStartTitle: 'Ginabayang mga hakbang para sa iyong sitwasyon',
    recStartBody: 'Maaaring mag-iba ang mga dokumento at proseso ng F-4 depende sa kasaysayan ng nasyonalidad, lokasyon ng aplikasyon, at pangangailangan sa pagpaparehistro ng paninirahan. Kahit hindi mo alam ang iyong subkategorya, sagutin ang ilang tanong upang mahanap ang checklist ng dokumento at proseso na pinakamalapit sa iyong sitwasyon.',
    ctaMicrocopy: 'Mga 1 minuto · 4–5 tanong · Hindi kailangang malaman ang subkategorya',
    stickyCta: 'Simulan ang checklist ng F-4',
    secondaryActionsLabel: 'Iba pang paraan ng paghahanap',
    secViewSubcategories: 'Tingnan ang lahat ng subkategorya',
    secViewCommonDocs: 'Tingnan ang karaniwang mga dokumento',
    secViewProcedure: 'Tingnan ang proseso ng aplikasyon',
    secViewSources: 'Tingnan ang opisyal na mga pinagmulan',
    stepWord: 'Hakbang',
    next: 'Susunod',
    restartShort: 'Simulan muli',
    backToGuide: '← Bumalik sa gabay',
    startGuideShort: 'Simulan ang gabay',
    progressAria: 'Pag-usad',
    stepSituationQ: 'Aling sitwasyon ang pinakamalapit sa iyo?',
    stepNationalityQ: 'May kasaysayan ka ba o ang iyong pamilya ng nasyonalidad na Koreano?',
    stepLocationQ: 'Saan ka naroroon sa kasalukuyan?',
    stepProcedureQ: 'Anong proseso ang kailangan mo ngayon?',
    stepConfirmQ: 'Mga item na maaaring mangailangan ng karagdagang kumpirmasyon',
    stepConfirmHelp: 'Ang mga item sa ibaba ay maaaring mangailangan ng karagdagang kumpirmasyon depende sa iyong indibidwal na kaso. Piliin ang anumang naaangkop at lilitaw ang mga ito sa iyong resulta. Opsyonal ang hakbang na ito.',
    optUnsure: 'Hindi ako sigurado',
    optSitApplyAbroad: 'Gusto kong mag-apply ng F-4 visa mula sa labas ng Korea',
    optSitChangeInKorea: 'Gusto kong baguhin ang aking katayuan tungo sa F-4 sa loob ng Korea',
    optSitExtension: 'May F-4 na ako at kailangan ng extension/pagbabago',
    optSitResidence: 'Kailangan ko ng pag-uulat ng paninirahan',
    optNatSelfHeld: 'Dati akong may hawak na nasyonalidad na Koreano',
    optNatAncestor: 'Ang aking magulang o lolo/lola ay dating may nasyonalidad na Koreano',
    optNatNone: 'Hindi naaangkop',
    optLocInKorea: 'Nasa Korea ako sa kasalukuyan',
    optLocOverseas: 'Nasa labas ako ng Korea sa kasalukuyan',
    optProcVisa: 'Pagkakaloob ng visa',
    optProcChange: 'Pagbabago ng katayuan',
    optProcExtension: 'Extension ng paninirahan',
    optProcResidence: 'Pag-uulat ng paninirahan',
    confNationalityLoss: 'Pagkawala / pagtatakwil ng nasyonalidad',
    confFamilyProof: 'Patunay ng relasyong pampamilya',
    confCriminalRecord: 'Sertipiko ng kriminal na rekord',
    confMilitary: 'Isyu kaugnay ng serbisyo militar',
    confApostille: 'Apostille / kumpirmasyong konsular',
    confTranslation: 'Pagsasalin / notaryo',
    mayRequireConfirm: 'Maaaring mangailangan ng karagdagang kumpirmasyon',
    officialSourceNeedsConfirm: 'Kailangang kumpirmahin ang opisyal na pinagmulan',
    resultTitle: 'Ang iyong malapit na landas ng paghahanda sa F-4',
    resWhy: 'Bakit ang landas na ito?',
    resFirstSteps: 'Mga unang hakbang',
    resBasicDocs: 'Pangunahing mga kinakailangang dokumento',
    resAdditionalDocs: 'Mga dokumentong maaaring idagdag para sa iyong sitwasyon',
    resProcedure: 'Proseso',
    resSources: 'Opisyal na mga pinagmulan',
    resNextActions: 'Mga susunod na aksyon',
    checklistIntro: 'Ang mga dokumento sa ibaba ay isang sanggunian na checklist na binuo mula sa mga opisyal na manwal. I-tap ang bawat item upang subaybayan ito habang naghahanda.',
    copyChecklist: 'Kopyahin ang checklist',
    copied: 'Nakopya',
    copyFail: 'Hindi makopya',
    viewDocDetails: 'Tingnan ang detalye ng dokumento',
    viewHikoreaGuide: 'Tingnan ang gabay sa reserbasyon ng HiKorea',
    checkJurisdiction: 'Suriin ang tanggapang may hurisdiksyon',
    safetyNote: 'Maaaring humiling ng karagdagang dokumento depende sa iyong indibidwal na kaso at sa pasya ng may-kapangyarihang tanggapan ng imigrasyon o konsulado ng Korea.',
    routeLabelOverseas: 'Landas ng pagsusuri sa aplikasyon ng F-4 visa sa ibang bansa',
    routeLabelStatusChange: 'Landas ng pagsusuri sa pagbabago ng katayuang F-4 sa Korea',
    routeLabelExtension: 'Landas ng paghahanda sa extension/pagbabago ng F-4',
    routeLabelResidence: 'Landas ng paghahanda sa pag-uulat ng paninirahan',
    routeLabelOfficialCheck: 'Landas na nangangailangan ng opisyal na kumpirmasyon',
    procStepPrepare: 'Ihanda ang mga dokumento',
    procStepReserve: 'Gumawa ng reserbasyon kung naaangkop',
    procStepSubmit: 'Isumite ang aplikasyon',
    procStepReview: 'Pagsusuri / pagsasala',
    procStepResult: 'Tingnan ang resulta',
    procStepFollowup: 'Kumpletuhin ang kasunod na pagpaparehistro o pag-isyu ng kard kung naaangkop',
    noAdditionalDocsNote: 'Wala kang napiling karagdagang item. Maaari pa ring humiling ng dagdag na dokumento depende sa iyong indibidwal na kaso — kumpirmahin sa may-kapangyarihang tanggapan.',
    extensionDocsNote: 'Ang tiyak na mga dokumento para sa extension ay nakadepende sa iyong indibidwal na kaso at sa may-kapangyarihang tanggapan. Kumpirmahin sa may-kapangyarihang tanggapan ng imigrasyon o sa HiKorea (1345) kasama ng gabay sa ibaba.',
    officialCheckDocsNote: 'Dahil dapat munang ayusin ang iyong pagiging karapat-dapat/nasyonalidad, hindi kami nagsasaad ng tiyak na listahan ng dokumento dito. Kumpirmahin sa iyong may-kapangyarihang misyon o sa Ministri ng Hustisya (HiKorea / 1345).',
    subcatHeading: 'Mga subkategorya ng F-4'
  };
  var STR_ID = {
    loading: 'Memuat data panduan F-4…',
    fetchFail: 'Tidak dapat memuat data panduan F-4. Jangan melanjutkan tanpa panduan ini — silakan konfirmasi langsung ke perwakilan Korea yang berwenang, HiKorea, atau 1345.',
    entryEyebrow: 'Warga Korea Perantauan F-4 · Panduan berdasarkan sumber resmi',
    startCtaFallback: 'Periksa prosedur F-4',
    modalAria: 'Panduan warga Korea perantauan F-4',
    close: 'Tutup',
    back: '← Kembali',
    restart: 'Mulai dari awal',
    seeResult: 'Lihat hasil',
    recommended: 'Jalur yang disarankan',
    why: 'Mengapa jalur ini?',
    checkFirst: 'Periksa terlebih dahulu',
    nextStep: 'Langkah berikutnya',
    cautions: 'Perhatian',
    officialWarn: 'Pemberitahuan verifikasi resmi',
    countryGuide: 'Pemeriksaan menurut negara',
    openHub: 'Lihat prosedur F-4 secara rinci',
    backToDiagnostic: '← Kembali ke diagnosis',
    hubTitle: 'Pusat panduan prosedur F-4',
    selectCountryLabel: 'Pilih negara pengajuan atau negara tempat tinggal Anda',
    selectCountryHint: 'Prosedur konsuler, surat keterangan catatan kriminal, metode pengesahan, pemesanan, biaya, dan waktu pemrosesan dapat berbeda menurut negara. Untuk negara yang belum diverifikasi, hanya standar umum F-4 yang ditampilkan.',
    selectCountryPlaceholder: '— Pilih negara (opsional) —',
    noCountrySelected: 'Anda belum memilih negara. Hanya standar umum F-4 yang ditampilkan. Pilih negara untuk juga melihat panduan konsuler negara tersebut (bila telah diverifikasi).',
    commonRulesHeading: 'Standar umum F-4 (berlaku untuk semua negara)',
    countryRulesHeading: 'Panduan menurut negara',
    docsHeading: 'Dokumen yang diserahkan secara umum',
    stepsHeading: 'Langkah',
    sourcesHeading: 'Sumber',
    notGuaranteeFootnote: 'Panduan ini tidak menjamin kelayakan atau persetujuan. Konfirmasikan pengajuan sebenarnya ke perwakilan Korea yang berwenang, kantor imigrasi, atau HiKorea (1345).',
    badgeVerified: 'Standar resmi terverifikasi',
    badgePartial: 'Sebagian sumber resmi',
    badgeRefresh: 'Perlu verifikasi kemutakhiran resmi',
    badgeOfficialCheck: 'Perlu pemeriksaan resmi',
    badgeUnclear: 'Tidak ada sumber verifikasi',
    sourceDatePrefix: 'Per tanggal',
    linkMissionPage: 'Halaman informasi perwakilan',
    linkMissionFinder: 'Cari perwakilan Korea Anda',
    linkVisaPortal: 'Periksa Portal Visa',
    linkHikorea: 'Periksa di HiKorea',
    link1345: 'Verifikasi melalui 1345',
    tagCountryVaries: 'Berbeda menurut negara',
    tagOfficialCheck: 'Pemeriksaan resmi',
    answerPrompt: 'Jawab pertanyaan di atas untuk melihat jalur yang disarankan.',
    ctaHelperFallback: 'Temukan alur yang sesuai untuk Anda di antara pengajuan konsuler, pelaporan tempat tinggal di dalam negeri, dan perubahan status.',
    conditionsHeading: 'Persyaratan',
    fieldCriminalRecord: 'Surat keterangan catatan kriminal',
    fieldAuthentication: 'Pengesahan dokumen (apostille / konsuler)',
    fieldBooking: 'Pemesanan',
    fieldFee: 'Biaya (biaya visa)',
    fieldProcessingTime: 'Waktu pemrosesan',
    fieldMissionPractice: 'Praktik perwakilan',
    guideHeader: 'Panduan status tinggal Warga Korea Perantauan F-4',
    guideIntro: 'Dokumen dan prosedur yang diperlukan dapat berbeda tergantung kategori warga Korea perantauan Anda, riwayat kewarganegaraan, dan jalur pengajuan. Jawab beberapa pertanyaan untuk menemukan jalur persiapan yang paling sesuai dengan situasi Anda.',
    primaryCta: 'Temukan daftar dokumen F-4 saya',
    recStartTitle: 'Panduan langkah sesuai situasi Anda',
    recStartBody: 'Dokumen dan prosedur F-4 dapat berbeda tergantung riwayat kewarganegaraan, lokasi pengajuan, dan kebutuhan pelaporan tempat tinggal. Meskipun tidak mengetahui subkategori Anda, jawab beberapa pertanyaan untuk menemukan daftar dokumen dan prosedur yang paling sesuai dengan situasi Anda.',
    ctaMicrocopy: 'Sekitar 1 menit · 4–5 pertanyaan · Tidak perlu tahu subkategori',
    stickyCta: 'Mulai daftar dokumen F-4',
    secondaryActionsLabel: 'Cara lain untuk menelusuri',
    secViewSubcategories: 'Lihat semua subkategori',
    secViewCommonDocs: 'Lihat dokumen umum',
    secViewProcedure: 'Lihat prosedur pengajuan',
    secViewSources: 'Lihat dasar resmi',
    stepWord: 'Langkah',
    next: 'Berikutnya',
    restartShort: 'Mulai ulang',
    backToGuide: '← Kembali ke panduan',
    startGuideShort: 'Mulai panduan',
    progressAria: 'Kemajuan',
    stepSituationQ: 'Situasi mana yang paling mendekati Anda?',
    stepNationalityQ: 'Apakah Anda atau keluarga Anda memiliki riwayat kewarganegaraan Korea?',
    stepLocationQ: 'Di mana Anda berada saat ini?',
    stepProcedureQ: 'Prosedur apa yang Anda perlukan sekarang?',
    stepConfirmQ: 'Item yang mungkin memerlukan konfirmasi tambahan',
    stepConfirmHelp: 'Item di bawah ini mungkin memerlukan konfirmasi tambahan tergantung kasus pribadi Anda. Pilih item yang sesuai dan akan ditampilkan dalam hasil Anda. Langkah ini opsional.',
    optUnsure: 'Saya tidak yakin',
    optSitApplyAbroad: 'Saya ingin mengajukan visa F-4 dari luar Korea',
    optSitChangeInKorea: 'Saya ingin mengubah status saya menjadi F-4 di dalam Korea',
    optSitExtension: 'Saya sudah memiliki F-4 dan memerlukan perpanjangan/perubahan',
    optSitResidence: 'Saya memerlukan pelaporan tempat tinggal',
    optNatSelfHeld: 'Saya pernah memiliki kewarganegaraan Korea',
    optNatAncestor: 'Orang tua atau kakek-nenek saya pernah memiliki kewarganegaraan Korea',
    optNatNone: 'Tidak berlaku',
    optLocInKorea: 'Sedang berada di Korea',
    optLocOverseas: 'Sedang berada di luar Korea',
    optProcVisa: 'Penerbitan visa',
    optProcChange: 'Perubahan status',
    optProcExtension: 'Perpanjangan masa tinggal',
    optProcResidence: 'Pelaporan tempat tinggal',
    confNationalityLoss: 'Hal terkait kehilangan / pelepasan kewarganegaraan',
    confFamilyProof: 'Pembuktian hubungan keluarga',
    confCriminalRecord: 'Surat keterangan catatan kriminal',
    confMilitary: 'Hal terkait wajib militer',
    confApostille: 'Apostille · pengesahan konsuler',
    confTranslation: 'Penerjemahan · notaris',
    mayRequireConfirm: 'Mungkin memerlukan konfirmasi tambahan',
    officialSourceNeedsConfirm: 'Dasar resmi perlu dikonfirmasi',
    resultTitle: 'Jalur persiapan F-4 yang sesuai dengan Anda',
    resWhy: 'Mengapa jalur ini?',
    resFirstSteps: 'Yang harus dilakukan terlebih dahulu',
    resBasicDocs: 'Dokumen persiapan dasar',
    resAdditionalDocs: 'Dokumen yang mungkin ditambahkan untuk situasi Anda',
    resProcedure: 'Prosedur pengajuan',
    resSources: 'Dasar resmi',
    resNextActions: 'Tindakan berikutnya',
    checklistIntro: 'Dokumen di bawah ini adalah daftar periksa referensi yang disusun dari manual resmi. Ketuk setiap item untuk melacaknya saat Anda mempersiapkan.',
    copyChecklist: 'Salin daftar periksa',
    copied: 'Tersalin',
    copyFail: 'Tidak dapat menyalin',
    viewDocDetails: 'Lihat detail dokumen',
    viewHikoreaGuide: 'Lihat panduan reservasi HiKorea',
    checkJurisdiction: 'Periksa kantor yang berwenang',
    safetyNote: 'Dokumen tambahan dapat diminta tergantung kasus pribadi Anda dan keputusan kantor imigrasi yang berwenang atau konsulat Korea.',
    routeLabelOverseas: 'Jalur peninjauan pengajuan visa F-4 di luar negeri',
    routeLabelStatusChange: 'Jalur peninjauan perubahan status F-4 di Korea',
    routeLabelExtension: 'Jalur persiapan perpanjangan/perubahan F-4',
    routeLabelResidence: 'Jalur persiapan pelaporan tempat tinggal',
    routeLabelOfficialCheck: 'Jalur yang memerlukan konfirmasi resmi',
    procStepPrepare: 'Siapkan dokumen',
    procStepReserve: 'Buat reservasi jika berlaku',
    procStepSubmit: 'Ajukan permohonan',
    procStepReview: 'Peninjauan / penyaringan',
    procStepResult: 'Periksa hasil',
    procStepFollowup: 'Selesaikan pendaftaran lanjutan atau penerbitan kartu jika berlaku',
    noAdditionalDocsNote: 'Anda tidak memilih item tambahan apa pun. Dokumen tambahan tetap dapat diminta tergantung kasus pribadi Anda — konfirmasikan ke kantor yang berwenang.',
    extensionDocsNote: 'Dokumen spesifik untuk perpanjangan bergantung pada kasus pribadi Anda dan kantor yang berwenang. Konfirmasikan ke kantor imigrasi yang berwenang atau HiKorea (1345) bersama panduan di bawah ini.',
    officialCheckDocsNote: 'Karena kelayakan/kewarganegaraan Anda harus diselesaikan terlebih dahulu, kami tidak menyatakan daftar dokumen yang pasti di sini. Konfirmasikan ke perwakilan yang berwenang atau Kementerian Kehakiman (HiKorea / 1345).',
    subcatHeading: 'Subkategori F-4'
  };
  var STR_RU = {
    loading: 'Загрузка данных руководства F-4…',
    fetchFail: 'Не удалось загрузить данные руководства F-4. Не продолжайте без него — пожалуйста, уточните напрямую в компетентном представительстве Кореи, на HiKorea или по номеру 1345.',
    entryEyebrow: 'Зарубежные корейцы F-4 · Руководство на основе официальных источников',
    startCtaFallback: 'Проверить процедуры F-4',
    modalAria: 'Руководство для зарубежных корейцев F-4',
    close: 'Закрыть',
    back: '← Назад',
    restart: 'Начать заново',
    seeResult: 'Посмотреть результат',
    recommended: 'Рекомендуемый путь',
    why: 'Почему этот путь?',
    checkFirst: 'Сначала проверьте',
    nextStep: 'Следующий шаг',
    cautions: 'Внимание',
    officialWarn: 'Уведомление об официальной проверке',
    countryGuide: 'Проверка по стране',
    openHub: 'Подробнее о процедурах F-4',
    backToDiagnostic: '← Назад к диагностике',
    hubTitle: 'Центр руководства по процедурам F-4',
    selectCountryLabel: 'Выберите страну подачи заявления или проживания',
    selectCountryHint: 'Консульские процедуры, справки о судимости, способы заверения, запись, сборы и сроки обработки могут различаться в зависимости от страны. Для непроверенных стран показываются только общие стандарты F-4.',
    selectCountryPlaceholder: '— Выберите страну (необязательно) —',
    noCountrySelected: 'Страна ещё не выбрана. Показываются только общие стандарты F-4. Выберите страну, чтобы также увидеть консульское руководство этой страны (если оно проверено).',
    commonRulesHeading: 'Общие стандарты F-4 (для всех стран)',
    countryRulesHeading: 'Руководство по стране',
    docsHeading: 'Общие подаваемые документы',
    stepsHeading: 'Шаги',
    sourcesHeading: 'Источники',
    notGuaranteeFootnote: 'Это руководство не гарантирует право на получение статуса или одобрение. Уточните фактическую подачу заявления в компетентном представительстве Кореи, в иммиграционной службе или на HiKorea (1345).',
    badgeVerified: 'Официальный стандарт проверен',
    badgePartial: 'Частично официальные источники',
    badgeRefresh: 'Требуется проверка официальной актуальности',
    badgeOfficialCheck: 'Требуется официальная проверка',
    badgeUnclear: 'Нет источников для проверки',
    sourceDatePrefix: 'По состоянию на',
    linkMissionPage: 'Страница информации представительства',
    linkMissionFinder: 'Найти представительство Кореи',
    linkVisaPortal: 'Проверить на Визовом портале',
    linkHikorea: 'Проверить на HiKorea',
    link1345: 'Рекомендуется уточнить по 1345',
    tagCountryVaries: 'Различается по странам',
    tagOfficialCheck: 'Официальная проверка',
    answerPrompt: 'Ответьте на вопросы выше, чтобы увидеть рекомендуемый путь.',
    ctaHelperFallback: 'Найдите подходящий вам порядок действий среди консульской подачи, внутреннего уведомления о месте жительства и изменения статуса.',
    conditionsHeading: 'Условия',
    fieldCriminalRecord: 'Справка о судимости',
    fieldAuthentication: 'Заверение документов (апостиль / консульское)',
    fieldBooking: 'Запись',
    fieldFee: 'Сбор (визовый сбор)',
    fieldProcessingTime: 'Срок обработки',
    fieldMissionPractice: 'Практика представительства',
    guideHeader: 'Руководство по статусу пребывания зарубежных корейцев F-4',
    guideIntro: 'Необходимые документы и процедуры могут различаться в зависимости от вашей категории зарубежного корейца, истории гражданства и пути подачи заявления. Ответьте на несколько вопросов, чтобы найти путь подготовки, наиболее близкий к вашей ситуации.',
    primaryCta: 'Найти мой список документов F-4',
    recStartTitle: 'Пошаговое руководство для вашей ситуации',
    recStartBody: 'Документы и процедуры F-4 могут различаться в зависимости от истории гражданства, места подачи заявления и необходимости регистрации места жительства. Даже если вы не знаете свою подкатегорию, ответьте на несколько вопросов, чтобы найти список документов и процедуру, наиболее близкие к вашей ситуации.',
    ctaMicrocopy: 'Около 1 минуты · 4–5 вопросов · Знание подкатегории не требуется',
    stickyCta: 'Начать список документов F-4',
    secondaryActionsLabel: 'Другие способы поиска',
    secViewSubcategories: 'Посмотреть все подкатегории',
    secViewCommonDocs: 'Посмотреть общие документы',
    secViewProcedure: 'Посмотреть процедуру подачи',
    secViewSources: 'Посмотреть официальные основания',
    stepWord: 'Шаг',
    next: 'Далее',
    restartShort: 'Заново',
    backToGuide: '← Назад к руководству',
    startGuideShort: 'Начать руководство',
    progressAria: 'Прогресс',
    stepSituationQ: 'Какая ситуация наиболее близка к вашей?',
    stepNationalityQ: 'Есть ли у вас или вашей семьи история корейского гражданства?',
    stepLocationQ: 'Где вы сейчас находитесь?',
    stepProcedureQ: 'Какая процедура вам нужна сейчас?',
    stepConfirmQ: 'Пункты, которые могут потребовать дополнительного подтверждения',
    stepConfirmHelp: 'Приведённые ниже пункты могут потребовать дополнительного подтверждения в зависимости от вашего индивидуального случая. Выберите подходящие, и они появятся в вашем результате. Этот шаг необязателен.',
    optUnsure: 'Я не уверен(а)',
    optSitApplyAbroad: 'Я хочу подать заявление на визу F-4 из-за пределов Кореи',
    optSitChangeInKorea: 'Я хочу изменить свой статус на F-4 внутри Кореи',
    optSitExtension: 'У меня уже есть F-4, и мне нужно продление/изменение',
    optSitResidence: 'Мне нужно уведомление о месте жительства',
    optNatSelfHeld: 'Ранее у меня было корейское гражданство',
    optNatAncestor: 'Мои родители или бабушка/дедушка ранее имели корейское гражданство',
    optNatNone: 'Не применимо',
    optLocInKorea: 'Сейчас нахожусь в Корее',
    optLocOverseas: 'Сейчас нахожусь за пределами Кореи',
    optProcVisa: 'Выдача визы',
    optProcChange: 'Изменение статуса',
    optProcExtension: 'Продление срока пребывания',
    optProcResidence: 'Уведомление о месте жительства',
    confNationalityLoss: 'Вопросы утраты / отказа от гражданства',
    confFamilyProof: 'Подтверждение родственных отношений',
    confCriminalRecord: 'Справка о судимости',
    confMilitary: 'Вопросы, связанные с воинской службой',
    confApostille: 'Апостиль · консульское заверение',
    confTranslation: 'Перевод · нотариальное заверение',
    mayRequireConfirm: 'Может потребоваться дополнительное подтверждение',
    officialSourceNeedsConfirm: 'Требуется подтверждение официального основания',
    resultTitle: 'Близкий вам путь подготовки F-4',
    resWhy: 'Почему этот путь?',
    resFirstSteps: 'Что сделать в первую очередь',
    resBasicDocs: 'Основные документы для подготовки',
    resAdditionalDocs: 'Документы, которые могут добавиться в вашей ситуации',
    resProcedure: 'Процедура подачи',
    resSources: 'Официальные основания',
    resNextActions: 'Следующие действия',
    checklistIntro: 'Приведённые ниже документы — это справочный контрольный список, составленный на основе официальных руководств. Нажимайте на каждый пункт, чтобы отмечать его по мере подготовки.',
    copyChecklist: 'Копировать список',
    copied: 'Скопировано',
    copyFail: 'Не удалось скопировать',
    viewDocDetails: 'Подробнее о документах',
    viewHikoreaGuide: 'Руководство по записи на HiKorea',
    checkJurisdiction: 'Проверить компетентный орган',
    safetyNote: 'В зависимости от вашего индивидуального случая и решения компетентной иммиграционной службы или консульства Кореи могут потребоваться дополнительные документы.',
    routeLabelOverseas: 'Путь рассмотрения подачи на визу F-4 за рубежом',
    routeLabelStatusChange: 'Путь рассмотрения изменения статуса F-4 в Корее',
    routeLabelExtension: 'Путь подготовки к продлению/изменению F-4',
    routeLabelResidence: 'Путь подготовки к уведомлению о месте жительства',
    routeLabelOfficialCheck: 'Путь, требующий официального подтверждения',
    procStepPrepare: 'Подготовить документы',
    procStepReserve: 'Записаться на приём при необходимости',
    procStepSubmit: 'Подать заявление',
    procStepReview: 'Рассмотрение / проверка',
    procStepResult: 'Проверить результат',
    procStepFollowup: 'При необходимости завершить последующую регистрацию или выдачу карты',
    noAdditionalDocsNote: 'Вы не выбрали ни одного дополнительного пункта. Дополнительные документы всё же могут быть запрошены в зависимости от вашего индивидуального случая — уточните в компетентном органе.',
    extensionDocsNote: 'Конкретные документы для продления зависят от вашего индивидуального случая и компетентного органа. Уточните в компетентной иммиграционной службе или на HiKorea (1345) вместе с приведённым ниже руководством.',
    officialCheckDocsNote: 'Поскольку сначала следует урегулировать вопрос вашего права на статус/гражданства, мы не приводим здесь окончательный список документов. Уточните в компетентном представительстве или в Министерстве юстиции (HiKorea / 1345).',
    subcatHeading: 'Подкатегории F-4'
  };
  var STR_FR = {
    loading: 'Chargement des données du guide F-4…',
    fetchFail: 'Impossible de charger les données du guide F-4. Ne poursuivez pas sans ce guide — veuillez vérifier directement auprès de la mission coréenne compétente, de HiKorea ou du 1345.',
    entryEyebrow: 'Coréen·ne·s de l’étranger F-4 · Guide fondé sur des sources officielles',
    startCtaFallback: 'Vérifier les procédures F-4',
    modalAria: 'Guide F-4 pour les Coréens de l’étranger',
    close: 'Fermer',
    back: '← Retour',
    restart: 'Recommencer',
    seeResult: 'Voir le résultat',
    recommended: 'Parcours recommandé',
    why: 'Pourquoi ce parcours ?',
    checkFirst: 'À vérifier d’abord',
    nextStep: 'Étape suivante',
    cautions: 'Attention',
    officialWarn: 'Avis de vérification officielle',
    countryGuide: 'Vérification par pays',
    openHub: 'Voir les procédures F-4 en détail',
    backToDiagnostic: '← Retour au diagnostic',
    hubTitle: 'Centre de guide des procédures F-4',
    selectCountryLabel: 'Sélectionnez votre pays de dépôt ou de résidence',
    selectCountryHint: 'Les procédures consulaires, les certificats de casier judiciaire, les modes d’authentification, la prise de rendez-vous, les frais et les délais de traitement peuvent varier selon les pays. Pour les pays non vérifiés, seules les normes communes F-4 sont affichées.',
    selectCountryPlaceholder: '— Sélectionnez un pays (facultatif) —',
    noCountrySelected: 'Aucun pays sélectionné pour l’instant. Seules les normes communes F-4 sont affichées. Sélectionnez un pays pour voir aussi le guide consulaire de ce pays (lorsqu’il est vérifié).',
    commonRulesHeading: 'Normes communes F-4 (tous pays)',
    countryRulesHeading: 'Guide par pays',
    docsHeading: 'Documents communs à fournir',
    stepsHeading: 'Étapes',
    sourcesHeading: 'Sources',
    notGuaranteeFootnote: 'Ce guide ne garantit ni l’éligibilité ni l’approbation. Confirmez la demande réelle auprès de la mission coréenne compétente, du bureau de l’immigration ou de HiKorea (1345).',
    badgeVerified: 'Norme officielle vérifiée',
    badgePartial: 'Sources officielles partielles',
    badgeRefresh: 'Vérifier l’actualité officielle',
    badgeOfficialCheck: 'Vérification officielle requise',
    badgeUnclear: 'Aucune source de vérification',
    sourceDatePrefix: 'Au',
    linkMissionPage: 'Page d’information de la mission',
    linkMissionFinder: 'Trouver votre mission coréenne',
    linkVisaPortal: 'Vérifier sur le Portail des visas',
    linkHikorea: 'Vérifier sur HiKorea',
    link1345: 'Vérifier via le 1345',
    tagCountryVaries: 'Varie selon le pays',
    tagOfficialCheck: 'Vérification officielle',
    answerPrompt: 'Répondez aux questions ci-dessus pour voir votre parcours recommandé.',
    ctaHelperFallback: 'Trouvez le parcours qui vous convient parmi la demande consulaire, la déclaration de résidence sur le territoire et le changement de statut.',
    conditionsHeading: 'Conditions',
    fieldCriminalRecord: 'Certificat de casier judiciaire',
    fieldAuthentication: 'Authentification des documents (apostille / consulaire)',
    fieldBooking: 'Prise de rendez-vous',
    fieldFee: 'Frais (frais de visa)',
    fieldProcessingTime: 'Délai de traitement',
    fieldMissionPractice: 'Pratique de la mission',
    guideHeader: 'Guide du statut de séjour F-4 pour les Coréens de l’étranger',
    guideIntro: 'Les documents requis et les procédures peuvent varier selon votre catégorie de Coréen de l’étranger, votre historique de nationalité et votre parcours de demande. Répondez à quelques questions pour trouver le parcours de préparation le plus proche de votre situation.',
    primaryCta: 'Trouver ma liste de documents F-4',
    recStartTitle: 'Étapes guidées selon votre situation',
    recStartBody: 'Les documents et procédures F-4 peuvent varier selon l’historique de nationalité, le lieu de dépôt et les besoins de déclaration de résidence. Même si vous ne connaissez pas votre sous-catégorie, répondez à quelques questions pour trouver la liste de documents et la procédure les plus proches de votre situation.',
    ctaMicrocopy: 'Environ 1 minute · 4 à 5 questions · Aucune connaissance de la sous-catégorie requise',
    stickyCta: 'Démarrer la liste F-4',
    secondaryActionsLabel: 'Autres façons d’explorer',
    secViewSubcategories: 'Voir toutes les sous-catégories',
    secViewCommonDocs: 'Voir les documents communs',
    secViewProcedure: 'Voir la procédure de demande',
    secViewSources: 'Voir les fondements officiels',
    stepWord: 'Étape',
    next: 'Suivant',
    restartShort: 'Recommencer',
    backToGuide: '← Retour au guide',
    startGuideShort: 'Démarrer le guide',
    progressAria: 'Progression',
    stepSituationQ: 'Quelle situation correspond le mieux à la vôtre ?',
    stepNationalityQ: 'Vous ou votre famille avez-vous un historique de nationalité coréenne ?',
    stepLocationQ: 'Où vous trouvez-vous actuellement ?',
    stepProcedureQ: 'De quelle procédure avez-vous besoin maintenant ?',
    stepConfirmQ: 'Éléments pouvant nécessiter une confirmation supplémentaire',
    stepConfirmHelp: 'Les éléments ci-dessous peuvent nécessiter une confirmation supplémentaire selon votre cas individuel. Sélectionnez ceux qui s’appliquent et ils apparaîtront dans votre résultat. Cette étape est facultative.',
    optUnsure: 'Je ne suis pas sûr·e',
    optSitApplyAbroad: 'Je souhaite demander un visa F-4 depuis l’étranger',
    optSitChangeInKorea: 'Je souhaite changer mon statut vers F-4 en Corée',
    optSitExtension: 'J’ai déjà un F-4 et j’ai besoin d’une prolongation/modification',
    optSitResidence: 'J’ai besoin d’une déclaration de résidence',
    optNatSelfHeld: 'J’ai déjà détenu la nationalité coréenne',
    optNatAncestor: 'Mon parent ou grand-parent a déjà détenu la nationalité coréenne',
    optNatNone: 'Non applicable',
    optLocInKorea: 'Je suis actuellement en Corée',
    optLocOverseas: 'Je suis actuellement hors de Corée',
    optProcVisa: 'Délivrance du visa',
    optProcChange: 'Changement de statut',
    optProcExtension: 'Prolongation du séjour',
    optProcResidence: 'Déclaration de résidence',
    confNationalityLoss: 'Questions de perte / renonciation à la nationalité',
    confFamilyProof: 'Preuve du lien familial',
    confCriminalRecord: 'Certificat de casier judiciaire',
    confMilitary: 'Question liée au service militaire',
    confApostille: 'Apostille · confirmation consulaire',
    confTranslation: 'Traduction · notarisation',
    mayRequireConfirm: 'Peut nécessiter une confirmation supplémentaire',
    officialSourceNeedsConfirm: 'La source officielle doit être confirmée',
    resultTitle: 'Votre parcours de préparation F-4 probable',
    resWhy: 'Pourquoi ce parcours ?',
    resFirstSteps: 'Premières étapes',
    resBasicDocs: 'Documents de base à préparer',
    resAdditionalDocs: 'Documents pouvant s’ajouter selon votre situation',
    resProcedure: 'Procédure de demande',
    resSources: 'Fondements officiels',
    resNextActions: 'Actions suivantes',
    checklistIntro: 'Les documents ci-dessous constituent une liste de contrôle de référence compilée à partir des manuels officiels. Touchez chaque élément pour le suivre au fur et à mesure de votre préparation.',
    copyChecklist: 'Copier la liste',
    copied: 'Copié',
    copyFail: 'Impossible de copier',
    viewDocDetails: 'Voir les détails des documents',
    viewHikoreaGuide: 'Voir le guide de réservation HiKorea',
    checkJurisdiction: 'Vérifier le bureau compétent',
    safetyNote: 'Des documents supplémentaires peuvent être demandés selon votre cas individuel et la décision du bureau de l’immigration compétent ou du consulat de Corée.',
    routeLabelOverseas: 'Parcours d’examen de la demande de visa F-4 à l’étranger',
    routeLabelStatusChange: 'Parcours d’examen du changement de statut F-4 en Corée',
    routeLabelExtension: 'Parcours de préparation à la prolongation/modification du F-4',
    routeLabelResidence: 'Parcours de préparation à la déclaration de résidence',
    routeLabelOfficialCheck: 'Un parcours nécessitant une confirmation officielle',
    procStepPrepare: 'Préparer les documents',
    procStepReserve: 'Prendre rendez-vous le cas échéant',
    procStepSubmit: 'Déposer la demande',
    procStepReview: 'Examen / instruction',
    procStepResult: 'Vérifier le résultat',
    procStepFollowup: 'Effectuer l’enregistrement de suivi ou la délivrance de la carte le cas échéant',
    noAdditionalDocsNote: 'Vous n’avez sélectionné aucun élément supplémentaire. Des documents additionnels peuvent tout de même être demandés selon votre cas individuel — confirmez auprès du bureau compétent.',
    extensionDocsNote: 'Les documents précis pour une prolongation dépendent de votre cas individuel et du bureau compétent. Confirmez auprès du bureau de l’immigration compétent ou de HiKorea (1345) avec le guide ci-dessous.',
    officialCheckDocsNote: 'Comme votre éligibilité/nationalité doit d’abord être clarifiée, nous n’indiquons pas ici de liste de documents définitive. Confirmez auprès de votre mission compétente ou du ministère de la Justice (HiKorea / 1345).',
    subcatHeading: 'Sous-catégories F-4'
  };
  var STR_ES = {
    loading: 'Cargando los datos de la guía F-4…',
    fetchFail: 'No se pudieron cargar los datos de la guía F-4. No continúe sin ella: confirme directamente con la misión coreana competente, con HiKorea o con el 1345.',
    entryEyebrow: 'Coreanos en el extranjero F-4 · Guía basada en fuentes oficiales',
    startCtaFallback: 'Comprobar los trámites F-4',
    modalAria: 'Guía F-4 para coreanos en el extranjero',
    close: 'Cerrar',
    back: '← Atrás',
    restart: 'Empezar de nuevo',
    seeResult: 'Ver el resultado',
    recommended: 'Ruta recomendada',
    why: '¿Por qué esta ruta?',
    checkFirst: 'Comprobar primero',
    nextStep: 'Siguiente paso',
    cautions: 'Precaución',
    officialWarn: 'Aviso de verificación oficial',
    countryGuide: 'Comprobación por país',
    openHub: 'Ver los trámites F-4 en detalle',
    backToDiagnostic: '← Volver al diagnóstico',
    hubTitle: 'Centro de guía de trámites F-4',
    selectCountryLabel: 'Seleccione su país de solicitud o de residencia',
    selectCountryHint: 'Los trámites consulares, los certificados de antecedentes penales, los métodos de autenticación, la reserva de cita, las tasas y los plazos de tramitación pueden variar según el país. Para los países no verificados, solo se muestran los estándares comunes de F-4.',
    selectCountryPlaceholder: '— Seleccione un país (opcional) —',
    noCountrySelected: 'Aún no ha seleccionado ningún país. Solo se muestran los estándares comunes de F-4. Seleccione un país para ver también la guía consular de ese país (cuando esté verificada).',
    commonRulesHeading: 'Estándares comunes de F-4 (todos los países)',
    countryRulesHeading: 'Guía por país',
    docsHeading: 'Documentos comunes a presentar',
    stepsHeading: 'Pasos',
    sourcesHeading: 'Fuentes',
    notGuaranteeFootnote: 'Esta guía no garantiza la elegibilidad ni la aprobación. Confirme la solicitud real con la misión coreana competente, con la oficina de inmigración o con HiKorea (1345).',
    badgeVerified: 'Estándar oficial verificado',
    badgePartial: 'Fuentes oficiales parciales',
    badgeRefresh: 'Verificar la vigencia oficial',
    badgeOfficialCheck: 'Se requiere verificación oficial',
    badgeUnclear: 'Sin fuentes de verificación',
    sourceDatePrefix: 'A fecha de',
    linkMissionPage: 'Página de información de la misión',
    linkMissionFinder: 'Encuentre su misión coreana',
    linkVisaPortal: 'Consultar el Portal de visados',
    linkHikorea: 'Consultar en HiKorea',
    link1345: 'Verificar a través del 1345',
    tagCountryVaries: 'Varía según el país',
    tagOfficialCheck: 'Verificación oficial',
    answerPrompt: 'Responda las preguntas anteriores para ver su ruta recomendada.',
    ctaHelperFallback: 'Encuentre el flujo que se ajusta a usted entre la solicitud consular, la declaración de residencia nacional y el cambio de estatus.',
    conditionsHeading: 'Condiciones',
    fieldCriminalRecord: 'Certificado de antecedentes penales',
    fieldAuthentication: 'Autenticación de documentos (apostilla / consular)',
    fieldBooking: 'Reserva de cita',
    fieldFee: 'Tasas (tasa de visado)',
    fieldProcessingTime: 'Plazo de tramitación',
    fieldMissionPractice: 'Práctica de la misión',
    guideHeader: 'Guía del estatus de estancia F-4 para coreanos en el extranjero',
    guideIntro: 'Los documentos requeridos y los trámites pueden variar según su categoría de coreano en el extranjero, su historial de nacionalidad y su vía de solicitud. Responda algunas preguntas para encontrar la ruta de preparación más cercana a su situación.',
    primaryCta: 'Encontrar mi lista de documentos F-4',
    recStartTitle: 'Pasos guiados para su situación',
    recStartBody: 'Los documentos y trámites de F-4 pueden variar según el historial de nacionalidad, el lugar de solicitud y las necesidades de declaración de residencia. Aunque no conozca su subcategoría, responda algunas preguntas para encontrar la lista de documentos y el trámite más cercanos a su situación.',
    ctaMicrocopy: 'Aproximadamente 1 minuto · 4–5 preguntas · No es necesario conocer la subcategoría',
    stickyCta: 'Iniciar la lista F-4',
    secondaryActionsLabel: 'Otras formas de explorar',
    secViewSubcategories: 'Ver todas las subcategorías',
    secViewCommonDocs: 'Ver los documentos comunes',
    secViewProcedure: 'Ver el trámite de solicitud',
    secViewSources: 'Ver los fundamentos oficiales',
    stepWord: 'Paso',
    next: 'Siguiente',
    restartShort: 'Reiniciar',
    backToGuide: '← Volver a la guía',
    startGuideShort: 'Iniciar la guía',
    progressAria: 'Progreso',
    stepSituationQ: '¿Qué situación se acerca más a la suya?',
    stepNationalityQ: '¿Usted o su familia tienen un historial de nacionalidad coreana?',
    stepLocationQ: '¿Dónde se encuentra actualmente?',
    stepProcedureQ: '¿Qué trámite necesita ahora?',
    stepConfirmQ: 'Elementos que pueden requerir confirmación adicional',
    stepConfirmHelp: 'Los elementos siguientes pueden requerir confirmación adicional según su caso individual. Seleccione los que correspondan y aparecerán en su resultado. Este paso es opcional.',
    optUnsure: 'No estoy seguro/a',
    optSitApplyAbroad: 'Quiero solicitar un visado F-4 desde fuera de Corea',
    optSitChangeInKorea: 'Quiero cambiar mi estatus a F-4 dentro de Corea',
    optSitExtension: 'Ya tengo F-4 y necesito una prórroga/modificación',
    optSitResidence: 'Necesito una declaración de residencia',
    optNatSelfHeld: 'Anteriormente tuve la nacionalidad coreana',
    optNatAncestor: 'Mi padre/madre o abuelo/a tuvo anteriormente la nacionalidad coreana',
    optNatNone: 'No aplica',
    optLocInKorea: 'Actualmente estoy en Corea',
    optLocOverseas: 'Actualmente estoy fuera de Corea',
    optProcVisa: 'Expedición del visado',
    optProcChange: 'Cambio de estatus',
    optProcExtension: 'Prórroga de la estancia',
    optProcResidence: 'Declaración de residencia',
    confNationalityLoss: 'Asuntos de pérdida / renuncia a la nacionalidad',
    confFamilyProof: 'Prueba de relación familiar',
    confCriminalRecord: 'Certificado de antecedentes penales',
    confMilitary: 'Asunto relacionado con el servicio militar',
    confApostille: 'Apostilla · confirmación consular',
    confTranslation: 'Traducción · notarización',
    mayRequireConfirm: 'Puede requerir confirmación adicional',
    officialSourceNeedsConfirm: 'La fuente oficial debe confirmarse',
    resultTitle: 'Su probable ruta de preparación F-4',
    resWhy: '¿Por qué esta ruta?',
    resFirstSteps: 'Primeros pasos',
    resBasicDocs: 'Documentos básicos a preparar',
    resAdditionalDocs: 'Documentos que pueden añadirse según su situación',
    resProcedure: 'Trámite de solicitud',
    resSources: 'Fundamentos oficiales',
    resNextActions: 'Acciones siguientes',
    checklistIntro: 'Los documentos siguientes son una lista de verificación de referencia recopilada de los manuales oficiales. Toque cada elemento para hacer seguimiento mientras se prepara.',
    copyChecklist: 'Copiar la lista',
    copied: 'Copiado',
    copyFail: 'No se pudo copiar',
    viewDocDetails: 'Ver los detalles del documento',
    viewHikoreaGuide: 'Ver la guía de reserva de HiKorea',
    checkJurisdiction: 'Comprobar la oficina competente',
    safetyNote: 'Pueden solicitarse documentos adicionales según su caso individual y la decisión de la oficina de inmigración competente o del consulado de Corea.',
    routeLabelOverseas: 'Ruta de revisión de la solicitud de visado F-4 en el extranjero',
    routeLabelStatusChange: 'Ruta de revisión del cambio de estatus F-4 en Corea',
    routeLabelExtension: 'Ruta de preparación de la prórroga/modificación de F-4',
    routeLabelResidence: 'Ruta de preparación de la declaración de residencia',
    routeLabelOfficialCheck: 'Una ruta que necesita confirmación oficial',
    procStepPrepare: 'Preparar los documentos',
    procStepReserve: 'Reservar cita si corresponde',
    procStepSubmit: 'Presentar la solicitud',
    procStepReview: 'Revisión / examen',
    procStepResult: 'Comprobar el resultado',
    procStepFollowup: 'Completar el registro posterior o la expedición de la tarjeta si corresponde',
    noAdditionalDocsNote: 'No seleccionó ningún elemento adicional. Aun así pueden solicitarse documentos adicionales según su caso individual: confirme con la oficina competente.',
    extensionDocsNote: 'Los documentos concretos para una prórroga dependen de su caso individual y de la oficina competente. Confirme con la oficina de inmigración competente o con HiKorea (1345) junto con la guía siguiente.',
    officialCheckDocsNote: 'Dado que primero debe resolverse su elegibilidad/nacionalidad, no indicamos aquí una lista de documentos definitiva. Confirme con su misión competente o con el Ministerio de Justicia (HiKorea / 1345).',
    subcatHeading: 'Subcategorías de F-4'
  };
  var STR_AR = {
    loading: 'جارٍ تحميل بيانات دليل F-4…',
    fetchFail: 'تعذّر تحميل بيانات دليل F-4. لا تتابع من دون هذا الدليل — يرجى التحقق مباشرةً من البعثة الكورية المختصة أو HiKorea أو الرقم 1345.',
    entryEyebrow: 'الكوريون في الخارج F-4 · دليل مبني على مصادر رسمية',
    startCtaFallback: 'التحقق من إجراءات F-4',
    modalAria: 'دليل الكوريين في الخارج F-4',
    close: 'إغلاق',
    back: '→ رجوع',
    restart: 'البدء من جديد',
    seeResult: 'عرض النتيجة',
    recommended: 'المسار الموصى به',
    why: 'لماذا هذا المسار؟',
    checkFirst: 'تحقق أولاً',
    nextStep: 'الخطوة التالية',
    cautions: 'تنبيه',
    officialWarn: 'إشعار بالتحقق الرسمي',
    countryGuide: 'التحقق حسب الدولة',
    openHub: 'عرض إجراءات F-4 بالتفصيل',
    backToDiagnostic: '→ العودة إلى التشخيص',
    hubTitle: 'مركز دليل إجراءات F-4',
    selectCountryLabel: 'اختر دولة التقديم أو دولة الإقامة',
    selectCountryHint: 'قد تختلف الإجراءات القنصلية وشهادات السجل الجنائي وطرق التصديق والحجز والرسوم ومدة المعالجة حسب الدولة. بالنسبة إلى الدول غير المُتحقَّق منها، تُعرض معايير F-4 العامة فقط.',
    selectCountryPlaceholder: '— اختر دولة (اختياري) —',
    noCountrySelected: 'لم تختر دولة بعد. تُعرض معايير F-4 العامة فقط. اختر دولة لعرض الدليل القنصلي لتلك الدولة أيضاً (في حال التحقق منه).',
    commonRulesHeading: 'معايير F-4 العامة (لجميع الدول)',
    countryRulesHeading: 'الدليل حسب الدولة',
    docsHeading: 'المستندات المقدَّمة المشتركة',
    stepsHeading: 'الخطوات',
    sourcesHeading: 'المصادر',
    notGuaranteeFootnote: 'لا يضمن هذا الدليل الأهلية أو الموافقة. تحقق من التقديم الفعلي لدى البعثة الكورية المختصة أو مكتب الهجرة أو HiKorea (1345).',
    badgeVerified: 'تم التحقق من المعيار الرسمي',
    badgePartial: 'مصادر رسمية جزئية',
    badgeRefresh: 'يلزم التحقق من حداثة المصدر الرسمي',
    badgeOfficialCheck: 'يلزم التحقق الرسمي',
    badgeUnclear: 'لا توجد مصادر للتحقق',
    sourceDatePrefix: 'حتى تاريخ',
    linkMissionPage: 'صفحة معلومات البعثة',
    linkMissionFinder: 'ابحث عن البعثة الكورية المختصة',
    linkVisaPortal: 'التحقق من بوابة التأشيرات',
    linkHikorea: 'التحقق على HiKorea',
    link1345: 'يُنصح بالتحقق عبر 1345',
    tagCountryVaries: 'يختلف حسب الدولة',
    tagOfficialCheck: 'تحقق رسمي',
    answerPrompt: 'أجب عن الأسئلة أعلاه لعرض المسار الموصى به.',
    ctaHelperFallback: 'اعثر على المسار المناسب لك بين التقديم القنصلي والإبلاغ عن محل الإقامة داخل البلاد وتغيير وضع الإقامة.',
    conditionsHeading: 'الشروط',
    fieldCriminalRecord: 'شهادة السجل الجنائي',
    fieldAuthentication: 'تصديق المستندات (أبوستيل / تصديق قنصلي)',
    fieldBooking: 'الحجز',
    fieldFee: 'الرسوم (رسوم التأشيرة)',
    fieldProcessingTime: 'مدة المعالجة',
    fieldMissionPractice: 'الممارسة العملية للبعثة',
    guideHeader: 'دليل وضع الإقامة للكوريين في الخارج F-4',
    guideIntro: 'قد تختلف المستندات المطلوبة والإجراءات حسب فئة الكوري في الخارج وتاريخ الجنسية ومسار التقديم. أجب عن بضعة أسئلة للعثور على مسار التحضير الأقرب إلى حالتك.',
    primaryCta: 'العثور على قائمة مستندات F-4 الخاصة بي',
    recStartTitle: 'خطوات موجّهة حسب حالتك',
    recStartBody: 'قد تختلف مستندات وإجراءات F-4 حسب تاريخ الجنسية ومكان التقديم والحاجة إلى الإبلاغ عن محل الإقامة. حتى لو كنت لا تعرف الرمز الفرعي الخاص بك، أجب عن بضعة أسئلة للعثور على قائمة المستندات والإجراء الأقرب إلى حالتك.',
    ctaMicrocopy: 'نحو دقيقة واحدة · 4–5 أسئلة · لا حاجة لمعرفة الرمز الفرعي',
    stickyCta: 'بدء قائمة مستندات F-4',
    secondaryActionsLabel: 'طرق أخرى للاستكشاف',
    secViewSubcategories: 'عرض جميع الفئات الفرعية',
    secViewCommonDocs: 'عرض المستندات المشتركة',
    secViewProcedure: 'عرض إجراء التقديم',
    secViewSources: 'عرض الأسس الرسمية',
    stepWord: 'خطوة',
    next: 'التالي',
    restartShort: 'إعادة',
    backToGuide: '→ العودة إلى الدليل',
    startGuideShort: 'بدء الدليل',
    progressAria: 'التقدّم',
    stepSituationQ: 'أي حالة أقرب إلى وضعك؟',
    stepNationalityQ: 'هل لديك أو لدى عائلتك تاريخ جنسية كورية؟',
    stepLocationQ: 'أين تتواجد حالياً؟',
    stepProcedureQ: 'ما الإجراء الذي تحتاجه الآن؟',
    stepConfirmQ: 'عناصر قد تتطلب تأكيداً إضافياً',
    stepConfirmHelp: 'قد تتطلب العناصر أدناه تأكيداً إضافياً حسب حالتك الفردية. اختر ما ينطبق منها وستظهر في نتيجتك. هذه الخطوة اختيارية.',
    optUnsure: 'لست متأكداً',
    optSitApplyAbroad: 'أرغب في التقديم على تأشيرة F-4 من خارج كوريا',
    optSitChangeInKorea: 'أرغب في تغيير وضع إقامتي إلى F-4 داخل كوريا',
    optSitExtension: 'لديّ F-4 بالفعل وأحتاج إلى تمديد/تغيير',
    optSitResidence: 'أحتاج إلى الإبلاغ عن محل الإقامة',
    optNatSelfHeld: 'سبق أن حملت الجنسية الكورية',
    optNatAncestor: 'سبق لأحد والديّ أو أجدادي أن حمل الجنسية الكورية',
    optNatNone: 'لا ينطبق',
    optLocInKorea: 'موجود حالياً في كوريا',
    optLocOverseas: 'موجود حالياً خارج كوريا',
    optProcVisa: 'إصدار التأشيرة',
    optProcChange: 'تغيير وضع الإقامة',
    optProcExtension: 'تمديد مدة الإقامة',
    optProcResidence: 'الإبلاغ عن محل الإقامة',
    confNationalityLoss: 'مسائل فقدان / التخلي عن الجنسية',
    confFamilyProof: 'إثبات صلة القرابة',
    confCriminalRecord: 'شهادة السجل الجنائي',
    confMilitary: 'مسألة متعلقة بالخدمة العسكرية',
    confApostille: 'أبوستيل · تصديق قنصلي',
    confTranslation: 'ترجمة · توثيق',
    mayRequireConfirm: 'قد يتطلب تأكيداً إضافياً',
    officialSourceNeedsConfirm: 'يلزم تأكيد المصدر الرسمي',
    resultTitle: 'مسار تحضير F-4 الأقرب إليك',
    resWhy: 'لماذا هذا المسار؟',
    resFirstSteps: 'ما يجب فعله أولاً',
    resBasicDocs: 'المستندات الأساسية للتحضير',
    resAdditionalDocs: 'مستندات قد تُضاف حسب حالتك',
    resProcedure: 'إجراء التقديم',
    resSources: 'الأسس الرسمية',
    resNextActions: 'الإجراءات التالية',
    checklistIntro: 'المستندات أدناه قائمة تحقق مرجعية مُجمَّعة من الأدلة الرسمية. اضغط على كل عنصر لمتابعته أثناء التحضير.',
    copyChecklist: 'نسخ قائمة التحقق',
    copied: 'تم النسخ',
    copyFail: 'تعذّر النسخ',
    viewDocDetails: 'عرض تفاصيل المستند',
    viewHikoreaGuide: 'عرض دليل الحجز على HiKorea',
    checkJurisdiction: 'التحقق من الجهة المختصة',
    safetyNote: 'قد تُطلب مستندات إضافية حسب حالتك الفردية وقرار مكتب الهجرة المختص أو القنصلية الكورية.',
    routeLabelOverseas: 'مسار مراجعة طلب تأشيرة F-4 في الخارج',
    routeLabelStatusChange: 'مسار مراجعة تغيير وضع F-4 داخل كوريا',
    routeLabelExtension: 'مسار تحضير تمديد/تغيير F-4',
    routeLabelResidence: 'مسار تحضير الإبلاغ عن محل الإقامة',
    routeLabelOfficialCheck: 'مسار يتطلب تأكيداً رسمياً',
    procStepPrepare: 'تحضير المستندات',
    procStepReserve: 'الحجز عند الحاجة',
    procStepSubmit: 'تقديم الطلب',
    procStepReview: 'المراجعة / الفحص',
    procStepResult: 'التحقق من النتيجة',
    procStepFollowup: 'إتمام التسجيل اللاحق أو إصدار البطاقة عند الحاجة',
    noAdditionalDocsNote: 'لم تختر أي عنصر إضافي. قد تُطلب مستندات إضافية رغم ذلك حسب حالتك الفردية — تحقق من الجهة المختصة.',
    extensionDocsNote: 'تعتمد المستندات المحددة للتمديد على حالتك الفردية والجهة المختصة. تحقق من مكتب الهجرة المختص أو HiKorea (1345) مع الدليل أدناه.',
    officialCheckDocsNote: 'بما أنه يجب أولاً حسم مسألة أهليتك/جنسيتك، فإننا لا نذكر هنا قائمة مستندات قاطعة. تحقق من البعثة المختصة أو وزارة العدل (HiKorea / 1345).',
    subcatHeading: 'الفئات الفرعية لـ F-4'
  };
  var STR_DE = {
    loading: 'F-4-Leitfadendaten werden geladen…',
    fetchFail: 'Die F-4-Leitfadendaten konnten nicht geladen werden. Fahren Sie nicht ohne sie fort – bitte erkundigen Sie sich direkt bei der zuständigen koreanischen Auslandsvertretung, bei HiKorea oder unter 1345.',
    entryEyebrow: 'Auslandskoreaner F-4 · Leitfaden auf Basis offizieller Quellen',
    startCtaFallback: 'F-4-Verfahren prüfen',
    modalAria: 'F-4-Leitfaden für Auslandskoreaner',
    close: 'Schließen',
    back: '← Zurück',
    restart: 'Neu beginnen',
    seeResult: 'Ergebnis ansehen',
    recommended: 'Empfohlener Weg',
    why: 'Warum dieser Weg?',
    checkFirst: 'Zuerst prüfen',
    nextStep: 'Nächster Schritt',
    cautions: 'Achtung',
    officialWarn: 'Hinweis zur offiziellen Überprüfung',
    countryGuide: 'Länderspezifische Prüfung',
    openHub: 'F-4-Verfahren im Detail ansehen',
    backToDiagnostic: '← Zurück zur Diagnose',
    hubTitle: 'F-4-Verfahrensleitfaden-Hub',
    selectCountryLabel: 'Wählen Sie Ihr Antrags- oder Wohnsitzland',
    selectCountryHint: 'Konsularische Verfahren, Führungszeugnisse, Beglaubigungsarten, Terminvereinbarung, Gebühren und Bearbeitungszeiten können je nach Land unterschiedlich sein. Für nicht verifizierte Länder werden nur die gemeinsamen F-4-Standards angezeigt.',
    selectCountryPlaceholder: '— Land auswählen (optional) —',
    noCountrySelected: 'Noch kein Land ausgewählt. Es werden nur die gemeinsamen F-4-Standards angezeigt. Wählen Sie ein Land, um auch den konsularischen Leitfaden dieses Landes zu sehen (sofern verifiziert).',
    commonRulesHeading: 'Gemeinsame F-4-Standards (alle Länder)',
    countryRulesHeading: 'Länderspezifischer Leitfaden',
    docsHeading: 'Gemeinsam einzureichende Unterlagen',
    stepsHeading: 'Schritte',
    sourcesHeading: 'Quellen',
    notGuaranteeFootnote: 'Dieser Leitfaden garantiert weder die Berechtigung noch die Genehmigung. Bestätigen Sie den tatsächlichen Antrag bei der zuständigen koreanischen Auslandsvertretung, bei der Einwanderungsbehörde oder bei HiKorea (1345).',
    badgeVerified: 'Offizieller Standard verifiziert',
    badgePartial: 'Teilweise offizielle Quellen',
    badgeRefresh: 'Offizielle Aktualität prüfen',
    badgeOfficialCheck: 'Offizielle Prüfung erforderlich',
    badgeUnclear: 'Keine Überprüfungsquellen',
    sourceDatePrefix: 'Stand',
    linkMissionPage: 'Informationsseite der Auslandsvertretung',
    linkMissionFinder: 'Ihre koreanische Auslandsvertretung finden',
    linkVisaPortal: 'Im Visa-Portal prüfen',
    linkHikorea: 'Auf HiKorea prüfen',
    link1345: 'Über 1345 bestätigen',
    tagCountryVaries: 'Je nach Land unterschiedlich',
    tagOfficialCheck: 'Offizielle Prüfung',
    answerPrompt: 'Beantworten Sie die obigen Fragen, um Ihren empfohlenen Weg zu sehen.',
    ctaHelperFallback: 'Finden Sie den passenden Ablauf unter konsularischem Antrag, inländischer Wohnsitzmeldung und Statuswechsel.',
    conditionsHeading: 'Voraussetzungen',
    fieldCriminalRecord: 'Führungszeugnis',
    fieldAuthentication: 'Beglaubigung von Dokumenten (Apostille / konsularisch)',
    fieldBooking: 'Terminvereinbarung',
    fieldFee: 'Gebühren (Visagebühr)',
    fieldProcessingTime: 'Bearbeitungszeit',
    fieldMissionPractice: 'Praxis der Auslandsvertretung',
    guideHeader: 'Leitfaden zum Aufenthaltsstatus F-4 für Auslandskoreaner',
    guideIntro: 'Die erforderlichen Unterlagen und Verfahren können je nach Ihrer Auslandskoreaner-Kategorie, Ihrer Staatsangehörigkeitsgeschichte und Ihrem Antragsweg unterschiedlich sein. Beantworten Sie einige Fragen, um den Vorbereitungsweg zu finden, der Ihrer Situation am nächsten kommt.',
    primaryCta: 'Meine F-4-Unterlagenliste finden',
    recStartTitle: 'Geführte Schritte für Ihre Situation',
    recStartBody: 'Die F-4-Unterlagen und -Verfahren können je nach Staatsangehörigkeitsgeschichte, Antragsort und Bedarf an einer Wohnsitzmeldung unterschiedlich sein. Auch wenn Sie Ihre Unterkategorie nicht kennen, beantworten Sie einige Fragen, um die Unterlagenliste und das Verfahren zu finden, die Ihrer Situation am nächsten kommen.',
    ctaMicrocopy: 'Etwa 1 Minute · 4–5 Fragen · Keine Kenntnis der Unterkategorie nötig',
    stickyCta: 'F-4-Unterlagenliste starten',
    secondaryActionsLabel: 'Andere Wege zum Erkunden',
    secViewSubcategories: 'Alle Unterkategorien ansehen',
    secViewCommonDocs: 'Gemeinsame Unterlagen ansehen',
    secViewProcedure: 'Antragsverfahren ansehen',
    secViewSources: 'Offizielle Grundlagen ansehen',
    stepWord: 'Schritt',
    next: 'Weiter',
    restartShort: 'Neu starten',
    backToGuide: '← Zurück zum Leitfaden',
    startGuideShort: 'Leitfaden starten',
    progressAria: 'Fortschritt',
    stepSituationQ: 'Welche Situation trifft auf Sie am ehesten zu?',
    stepNationalityQ: 'Haben Sie oder Ihre Familie eine koreanische Staatsangehörigkeitsgeschichte?',
    stepLocationQ: 'Wo befinden Sie sich derzeit?',
    stepProcedureQ: 'Welches Verfahren benötigen Sie jetzt?',
    stepConfirmQ: 'Punkte, die eine zusätzliche Bestätigung erfordern können',
    stepConfirmHelp: 'Die folgenden Punkte können je nach Ihrem Einzelfall eine zusätzliche Bestätigung erfordern. Wählen Sie die zutreffenden aus, und sie erscheinen in Ihrem Ergebnis. Dieser Schritt ist optional.',
    optUnsure: 'Ich bin nicht sicher',
    optSitApplyAbroad: 'Ich möchte ein F-4-Visum von außerhalb Koreas beantragen',
    optSitChangeInKorea: 'Ich möchte meinen Status innerhalb Koreas auf F-4 ändern',
    optSitExtension: 'Ich habe bereits F-4 und benötige eine Verlängerung/Änderung',
    optSitResidence: 'Ich benötige eine Wohnsitzmeldung',
    optNatSelfHeld: 'Ich besaß früher die koreanische Staatsangehörigkeit',
    optNatAncestor: 'Mein Elternteil oder Großelternteil besaß früher die koreanische Staatsangehörigkeit',
    optNatNone: 'Nicht zutreffend',
    optLocInKorea: 'Ich bin derzeit in Korea',
    optLocOverseas: 'Ich bin derzeit außerhalb Koreas',
    optProcVisa: 'Visumerteilung',
    optProcChange: 'Statuswechsel',
    optProcExtension: 'Verlängerung des Aufenthalts',
    optProcResidence: 'Wohnsitzmeldung',
    confNationalityLoss: 'Angelegenheiten zum Verlust / zur Aufgabe der Staatsangehörigkeit',
    confFamilyProof: 'Nachweis des Familienverhältnisses',
    confCriminalRecord: 'Führungszeugnis',
    confMilitary: 'Angelegenheit im Zusammenhang mit dem Wehrdienst',
    confApostille: 'Apostille · konsularische Bestätigung',
    confTranslation: 'Übersetzung · notarielle Beglaubigung',
    mayRequireConfirm: 'Kann eine zusätzliche Bestätigung erfordern',
    officialSourceNeedsConfirm: 'Offizielle Grundlage muss bestätigt werden',
    resultTitle: 'Ihr wahrscheinlicher F-4-Vorbereitungsweg',
    resWhy: 'Warum dieser Weg?',
    resFirstSteps: 'Erste Schritte',
    resBasicDocs: 'Grundlegende vorzubereitende Unterlagen',
    resAdditionalDocs: 'Unterlagen, die je nach Ihrer Situation hinzukommen können',
    resProcedure: 'Antragsverfahren',
    resSources: 'Offizielle Grundlagen',
    resNextActions: 'Nächste Schritte',
    checklistIntro: 'Die folgenden Unterlagen sind eine Referenz-Checkliste, die aus den offiziellen Handbüchern zusammengestellt wurde. Tippen Sie auf jeden Punkt, um ihn während der Vorbereitung zu verfolgen.',
    copyChecklist: 'Checkliste kopieren',
    copied: 'Kopiert',
    copyFail: 'Kopieren nicht möglich',
    viewDocDetails: 'Unterlagendetails ansehen',
    viewHikoreaGuide: 'HiKorea-Reservierungsleitfaden ansehen',
    checkJurisdiction: 'Zuständige Behörde prüfen',
    safetyNote: 'Je nach Ihrem Einzelfall und der Entscheidung der zuständigen Einwanderungsbehörde oder des koreanischen Konsulats können zusätzliche Unterlagen verlangt werden.',
    routeLabelOverseas: 'Prüfweg für den F-4-Visumantrag im Ausland',
    routeLabelStatusChange: 'Prüfweg für den F-4-Statuswechsel in Korea',
    routeLabelExtension: 'Vorbereitungsweg für F-4-Verlängerung/-Änderung',
    routeLabelResidence: 'Vorbereitungsweg für die Wohnsitzmeldung',
    routeLabelOfficialCheck: 'Ein Weg, der eine offizielle Bestätigung erfordert',
    procStepPrepare: 'Unterlagen vorbereiten',
    procStepReserve: 'Bei Bedarf einen Termin vereinbaren',
    procStepSubmit: 'Antrag einreichen',
    procStepReview: 'Prüfung / Begutachtung',
    procStepResult: 'Ergebnis prüfen',
    procStepFollowup: 'Bei Bedarf die anschließende Registrierung oder Kartenausstellung abschließen',
    noAdditionalDocsNote: 'Sie haben keine zusätzlichen Punkte ausgewählt. Je nach Ihrem Einzelfall können dennoch zusätzliche Unterlagen verlangt werden – bestätigen Sie dies bei der zuständigen Behörde.',
    extensionDocsNote: 'Die konkreten Unterlagen für eine Verlängerung hängen von Ihrem Einzelfall und der zuständigen Behörde ab. Bestätigen Sie dies zusammen mit dem Leitfaden unten bei der zuständigen Einwanderungsbehörde oder bei HiKorea (1345).',
    officialCheckDocsNote: 'Da zunächst Ihre Berechtigung/Staatsangehörigkeit geklärt werden sollte, geben wir hier keine endgültige Unterlagenliste an. Bestätigen Sie dies bei Ihrer zuständigen Auslandsvertretung oder beim Justizministerium (HiKorea / 1345).',
    subcatHeading: 'F-4-Unterkategorien'
  };
  var STR_PACKS = { ko: STR_KO, en: STR_EN, 'zh-CN': STR_ZH, ja: STR_JA, vi: STR_VI, tl: STR_TL, id: STR_ID, ru: STR_RU, fr: STR_FR, es: STR_ES, ar: STR_AR, de: STR_DE };
  var STR = (typeof Proxy === 'function')
    ? new Proxy({}, { get: function (_t, k) { var p = STR_PACKS[f4Lang()] || STR_KO; return (p[k] != null) ? p[k] : STR_KO[k]; } })
    : STR_KO;

  // Country/overlay display label in the active language. The country data only
  // carries labelKo/labelEn/labelZh, so locales without a dedicated label fall
  // back: zh-CN → labelZh; ko → labelKo; every other active locale prefers the
  // English country name (more readable than Korean for those readers) before
  // dropping to the Korean canonical.
  function clabel(c) {
    if (!c) return '';
    var lg = f4Lang();
    if (lg === 'zh-CN') return c.labelZh || c.labelEn || c.labelKo || '';
    if (lg === 'ko') return c.labelKo || c.labelEn || '';
    return c.labelEn || c.labelKo || '';
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
  var TAB_LABEL_ZH = {
    overview: 'F-4 一览',
    overseasApplication: '在驻外公馆申请',
    residenceReport: '国内居所申报/居所证',
    statusChange: '在韩国变更资格',
    country: '按国家确认',
    faq: 'F-4 常见问题'
  };
  var TAB_LABEL_JA = {
    overview: 'F-4 ひと目で見る',
    overseasApplication: '在外公館で申請',
    residenceReport: '国内居所申告／居所証',
    statusChange: '韓国で資格変更',
    country: '国別の確認',
    faq: 'F-4 よくある質問'
  };
  var TAB_LABEL_VI = {
    overview: 'Tổng quan F-4',
    overseasApplication: 'Nộp tại cơ quan đại diện',
    residenceReport: 'Khai báo cư trú / thẻ cư trú',
    statusChange: 'Thay đổi tư cách tại Hàn Quốc',
    country: 'Theo quốc gia',
    faq: 'Câu hỏi thường gặp F-4'
  };
  var TAB_LABEL_TL = {
    overview: 'F-4 sa isang sulyap',
    overseasApplication: 'Mag-apply sa isang misyon',
    residenceReport: 'Pag-uulat ng paninirahan / kard',
    statusChange: 'Pagbabago ng katayuan sa Korea',
    country: 'Ayon sa bansa',
    faq: 'FAQ ng F-4'
  };
  var TAB_LABEL_ID = {
    overview: 'Sekilas F-4',
    overseasApplication: 'Mengajukan di perwakilan',
    residenceReport: 'Pelaporan tempat tinggal / kartu',
    statusChange: 'Perubahan status di Korea',
    country: 'Menurut negara',
    faq: 'FAQ F-4'
  };
  var TAB_LABEL_RU = {
    overview: 'F-4 кратко',
    overseasApplication: 'Подача в представительстве',
    residenceReport: 'Уведомление о месте жительства / карта',
    statusChange: 'Изменение статуса в Корее',
    country: 'По стране',
    faq: 'Частые вопросы по F-4'
  };
  var TAB_LABEL_FR = {
    overview: 'F-4 en un coup d’œil',
    overseasApplication: 'Déposer à une mission',
    residenceReport: 'Déclaration de résidence / carte',
    statusChange: 'Changement de statut en Corée',
    country: 'Par pays',
    faq: 'FAQ F-4'
  };
  var TAB_LABEL_ES = {
    overview: 'F-4 de un vistazo',
    overseasApplication: 'Solicitar en una misión',
    residenceReport: 'Declaración de residencia / tarjeta',
    statusChange: 'Cambio de estatus en Corea',
    country: 'Por país',
    faq: 'Preguntas frecuentes F-4'
  };
  var TAB_LABEL_AR = {
    overview: 'F-4 في لمحة',
    overseasApplication: 'التقديم لدى البعثة',
    residenceReport: 'الإبلاغ عن محل الإقامة / البطاقة',
    statusChange: 'تغيير الوضع داخل كوريا',
    country: 'حسب الدولة',
    faq: 'الأسئلة الشائعة عن F-4'
  };
  var TAB_LABEL_DE = {
    overview: 'F-4 auf einen Blick',
    overseasApplication: 'Bei einer Auslandsvertretung beantragen',
    residenceReport: 'Wohnsitzmeldung / Karte',
    statusChange: 'Statuswechsel in Korea',
    country: 'Nach Land',
    faq: 'F-4-FAQ'
  };
  var TAB_LABEL_PACKS = { ko: TAB_LABEL_KO, en: TAB_LABEL_EN, 'zh-CN': TAB_LABEL_ZH, ja: TAB_LABEL_JA, vi: TAB_LABEL_VI, tl: TAB_LABEL_TL, id: TAB_LABEL_ID, ru: TAB_LABEL_RU, fr: TAB_LABEL_FR, es: TAB_LABEL_ES, ar: TAB_LABEL_AR, de: TAB_LABEL_DE };
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
'.f4g-result{max-width:680px;}' +
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
  // "Guided steps for your situation" block — the single, dominant F-4 entry. Built
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
    // Korean reads "n / total 단계" (counter after); every other locale reads
    // "Step n / total" (word first).
    setStepCount((f4Lang() === 'ko') ? (n + ' / ' + total + ' ' + STR.stepWord) : (STR.stepWord + ' ' + n + ' / ' + total));
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
