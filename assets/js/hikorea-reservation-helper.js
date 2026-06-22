/* ============================================================================
 * Paradiso — 하이코리아 예약 도우미 / HiKorea Reservation Helper
 * ----------------------------------------------------------------------------
 * A friendly, mobile-first, step-by-step helper that answers the question a
 * user actually has before going to immigration:
 *
 *   "그래서 무슨 버튼을 어떻게 눌러야 하는데?"
 *   ("So which button do I actually press, and how?")
 *
 * It replaces the previous static, government-PDF-style modal guide with a
 * one-question-at-a-time flow:
 *
 *   purpose → registration-card status → location → status code →
 *   (expiry, only when relevant) → a single result card with four compact
 *   sections (what to click · what to prepare · what to check · if it fails).
 *
 * Design contract (do not weaken):
 *  - Deterministic + testable: computeReservationPath() is a pure function with
 *    no DOM/network/model dependency. The visible flow is fully rule-based — it
 *    never calls any language model. (scripts/check_hikorea_reservation_helper.mjs)
 *  - Cautious wording only. Recommendations are framed as "likely", never as
 *    official rules. The result and footer always carry the official-source
 *    disclaimer (HiKorea / 1345 / 관할 출입국).
 *  - No invented immigration-law claims; no document requirements beyond the
 *    generic preparation reminders below.
 *  - Korean is canonical; English chrome is paired 1:1 (STR_KO/STR_EN — checked
 *    by scripts/check_popup_i18n.mjs). Per the repo i18n fallback policy, locales
 *    other than en resolve to Korean canonical chrome rather than machine text.
 *
 * The module renders into the existing #hikoreaGuideBody inside the
 * #hikoreaGuideOverlay modal shell so it reuses the page's proven modal focus
 * trap / Escape / focus-restore (openModal/closeModal in index.html). index.html
 * owns the modal shell; this module owns the content + logic.
 * ========================================================================== */
(function () {
  'use strict';

  /* --------------------------------------------------------------- escaping */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  /* ------------------------------------------------------------------------ *
   * Deterministic core. Pure: same input → same output, no DOM/network/LLM.
   * Returns structured IDs/keys only; the UI layer maps them to localized copy.
   *
   * input:  { reservationPurpose, hasRegistrationCard, currentLocation,
   *           statusCode, expiryDate }
   * output: { recommendedPurpose, confidence, expiryStatus, warnings,
   *           beforeBookingChecklist, afterBookingChecklist, hikoreaClickSteps,
   *           blockedCaseTips }
   *
   * Kept self-contained (no references to module-scope tables) so it can be
   * extracted and exercised in isolation by the test harness.
   * ------------------------------------------------------------------------ */
  function computeReservationPath(input) {
    var inp = input || {};
    var purpose = inp.reservationPurpose || '';
    var card = inp.hasRegistrationCard || '';
    var loc = inp.currentLocation || '';
    var code = String(inp.statusCode || '').toUpperCase().replace(/\s+/g, '');
    var expiry = inp.expiryDate || '';

    var warnings = [];
    warnings.push('sameDay');
    warnings.push('realName');

    if (loc === 'overseas') warnings.push('overseasNotice');

    var isUnsure = (purpose === '' || purpose === 'unsure');
    var isF4 = code === 'F-4' || code.indexOf('F-4') === 0;

    var recommended = purpose;
    var confidence = 'medium';

    if (isUnsure) {
      if (card === 'no' && loc !== 'overseas') {
        recommended = isF4 ? 'residence_report' : 'registration';
        confidence = 'medium';
      } else if (card === 'yes') {
        recommended = 'extension';
        confidence = 'low';
        warnings.push('unsureGuidance');
      } else {
        recommended = 'unsure';
        confidence = 'low';
        warnings.push('unsureGuidance');
      }
    } else {
      recommended = purpose;
      confidence = 'high';
      if (purpose === 'registration') {
        if (isF4) {
          recommended = 'residence_report';
          warnings.push('f4ResidenceReport');
        }
        if (card === 'yes') {
          warnings.push('alreadyRegistered');
          confidence = 'medium';
        }
      }
      if (purpose === 'extension') {
        warnings.push('extensionWindow');
        if (card === 'no') {
          warnings.push('registerFirst');
          confidence = 'medium';
        }
      }
      if ((purpose === 'change_status' || purpose === 'workplace' || purpose === 'activity') && card === 'no') {
        warnings.push('registerFirst');
        confidence = 'medium';
      }
    }

    var expiryStatus = 'none';
    if (expiry) {
      var d = new Date(expiry + 'T00:00:00');
      if (!isNaN(d.getTime())) {
        var today = new Date();
        today.setHours(0, 0, 0, 0);
        var diff = Math.floor((d.getTime() - today.getTime()) / 86400000);
        if (diff < 0) {
          expiryStatus = 'expired';
          warnings.push('expired');
        } else if (diff <= 14) {
          expiryStatus = 'imminent';
          warnings.push('imminent');
        } else {
          expiryStatus = 'ok';
        }
      }
    }

    var before = ['identity', 'realNameAcct'];
    if (recommended === 'extension' || recommended === 'change_status' || recommended === 'workplace' || recommended === 'activity') {
      before.push('docsReady');
    }
    if (recommended === 'registration' || recommended === 'residence_report' || recommended === 'address') {
      before.push('addressKnown');
    }
    before.push('officeKnown');

    var after = ['saveConfirm', 'checkDateOffice', 'visitorName', 'sameDayReminder'];

    var clickSteps = ['open', 'civil', 'visit', 'start', 'login', 'office', 'purpose', 'datetime', 'save'];

    var blockedTips = ['noDates', 'today', 'office', 'login', 'purpose'];

    return {
      recommendedPurpose: recommended,
      confidence: confidence,
      expiryStatus: expiryStatus,
      warnings: warnings,
      beforeBookingChecklist: before,
      afterBookingChecklist: after,
      hikoreaClickSteps: clickSteps,
      blockedCaseTips: blockedTips
    };
  }

  /* ------------------------------------------------------------------ i18n */
  function prhLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return l === 'en' ? 'en' : 'ko';
  }

  var STR_KO = {
    modalAria: '하이코리아 예약 도우미',
    headerTitle: '하이코리아 예약 도우미',
    headerSub: '출입국에 가기 전에, 내 상황에 맞는 예약 목적과 준비물을 확인하세요.',
    notOfficialChip: '공식 서비스 아님',
    progressAria: '진행 단계',
    next: '다음',
    back: '이전',
    findPath: '예약 경로 찾기',
    restart: '처음부터 다시',
    close: '닫기',
    goHikorea: '하이코리아 바로가기',
    viewDocs: '구비서류 체크리스트 보기',
    saveResult: '결과 저장',
    saved: '복사됨',
    saveFail: '복사하지 못했어요. 직접 화면을 저장하세요.',
    hotline: '예약이나 절차가 헷갈리면 외국인종합안내센터 1345로 문의하세요.',
    call1345: '1345 전화',

    q1: '무엇 때문에 출입국에 가시나요?',
    q1Help: '정확한 이름을 몰라도 괜찮아요. 가장 가까운 상황을 골라주세요.',
    q2: '외국인등록증이나 거소증이 있나요?',
    q2Help: '등록증이 있는지에 따라 예약 목적이 달라질 수 있어요.',
    q3: '지금 한국에 있나요?',
    q3Help: '하이코리아 방문예약은 보통 한국 안에서 출입국에 방문할 때 필요합니다.',
    q4: '현재 체류자격을 알고 있나요?',
    q4Help: '예: D-2, F-4, E-7처럼 여권 사증면이나 등록증에 적힌 코드를 입력할 수 있어요.',
    q4Placeholder: '예: D-2, F-4, E-7',
    q4Skip: '잘 모르겠어요',
    q5: '체류기간 만료일이 언제인가요?',
    q5Help: '연장 신청은 만료일 전에 해야 합니다. 정확한 가능 기간은 방문 전에 다시 확인하세요.',
    q5Skip: '잘 모르겠어요',

    optYes: '있어요',
    optNo: '없어요',
    optNotSure: '잘 모르겠어요',
    optInKorea: '한국에 있어요',
    optOverseas: '아직 해외에 있어요',

    pRegistration: '외국인등록',
    pExtension: '체류기간 연장',
    pChange: '체류자격 변경',
    pActivity: '체류자격외 활동허가',
    pWorkplace: '근무처 변경/추가',
    pAddress: '체류지 변경',
    pReissue: '등록증 재발급',
    pUnsure: '잘 모르겠어요',
    pResidenceReport: '국내거소신고',
    pResidenceReissue: '거소증 재발급',
    pRegChange: '등록사항 변경',
    pConsult: '기타 체류 관련 상담',
    pConsultF5: '체류자격 관련 상담',

    resultLabel: '추천 예약 목적',
    resultLead: '입력한 내용을 기준으로 보면, 하이코리아에서 이 업무로 예약할 가능성이 높습니다.',
    resultLeadLow: '아직 추천을 확정하기 어려워요. 아래 안내를 참고하고, 1345나 관할 출입국에 정확한 예약 목적을 확인하세요.',
    confLabel: '추천 신뢰도',
    confHigh: '높음',
    confMedium: '보통',
    confLow: '낮음',

    secClick: '하이코리아에서 누를 것',
    secBefore: '예약 전에 준비할 것',
    secAfter: '예약 후 확인할 것',
    secBlocked: '예약이 안 될 때',
    cautionsTitle: '꼭 기억할 점',

    click1: '하이코리아 접속',
    click2: '민원신청 선택',
    click3: '방문예약 선택',
    click4: '방문예약 신청 선택',
    click5: '회원 로그인 또는 비회원 인증',
    click6: '관할 출입국관서 선택',
    click7: '방문 목적 선택',
    click8: '날짜와 시간 선택',
    click9: '예약 완료 후 접수증 저장',

    bIdentity: '여권 또는 신분증',
    bRealNameAcct: '실제 방문하는 사람 본인 명의 정보',
    bDocsReady: '신청에 필요한 서류를 미리 확인',
    bAddressKnown: '현재 거주지 주소 확인',
    bOfficeKnown: '방문할 관할 출입국 확인',

    aSaveConfirm: '예약 접수증(확인증)을 저장하거나 캡처하세요.',
    aCheckDateOffice: '예약한 날짜와 방문할 출입국 사무소를 다시 확인하세요.',
    aVisitorName: '예약이 실제 방문하는 사람 이름으로 됐는지 확인하세요.',
    aSameDayReminder: '당일 예약은 되지 않을 수 있으니 미리 예약 날짜를 확인하세요.',

    wSameDay: '당일 예약은 되지 않을 수 있어요. 방문예약은 보통 다음 날부터 가능합니다.',
    wRealName: '예약은 실제 방문하는 사람 이름으로 해야 합니다.',
    wOverseasNotice: '하이코리아 방문예약은 보통 한국 안에서 출입국에 방문할 때 필요합니다. 아직 해외에 있다면 입국 후 다시 확인하세요.',
    wUnsureGuidance: '어떤 업무를 골라야 할지 모르겠다면 1345나 관할 출입국에 확인하세요.',
    wExtensionWindow: '비자 만료 전에 연장 신청을 해야 합니다. 정확한 신청 가능 기간은 방문 전에 다시 확인하세요.',
    wExpired: '입력한 만료일이 이미 지났어요. 늦으면 불이익이 있을 수 있으니 1345나 관할 출입국에 바로 확인하세요.',
    wImminent: '만료일이 얼마 남지 않았어요. 가능한 빨리 예약하고 신청을 준비하세요.',
    wRegisterFirst: '먼저 외국인등록이 필요할 수 있어요. 등록증이 없다면 등록 절차부터 확인하세요.',
    wAlreadyRegistered: '이미 등록증이 있다면 외국인등록을 다시 할 필요는 없을 수 있어요. 필요한 업무를 다시 확인하세요.',
    wF4ResidenceReport: 'F-4는 외국인등록 대신 국내거소신고를 하는 경우가 많아요.',

    blkNoDatesT: '날짜가 안 보여요',
    blkNoDatesB: '예약 가능한 시간이 이미 마감됐을 수 있어요. 다른 날짜를 확인하거나, 관할 출입국 또는 1345에 문의하세요.',
    blkTodayT: '오늘 방문하고 싶어요',
    blkTodayB: '하이코리아 방문예약은 당일 예약이 어려울 수 있어요. 가능한 날짜를 먼저 확인하세요.',
    blkOfficeT: '어느 출입국을 골라야 할지 모르겠어요',
    blkOfficeB: '보통 현재 주소지를 기준으로 관할 출입국을 확인합니다. 주소가 애매하면 1345나 관할 출입국에 문의하세요.',
    blkLoginT: '로그인이나 인증이 안 돼요',
    blkLoginB: '회원 로그인이 어렵다면 비회원 인증이 가능한지 확인하세요. 그래도 안 되면 하이코리아 안내나 1345를 이용하세요.',
    blkPurposeT: '어떤 업무를 골라야 할지 모르겠어요',
    blkPurposeB: 'Paradiso의 추천 결과를 저장해 두고, 1345나 관할 출입국에 정확한 예약 목적을 확인하세요.',

    statusSuggTitle: '이 체류자격에서 많이 찾는 예약 목적',
    statusSuggCaution: '아래 항목은 이 체류자격에서 자주 이어지는 예약 목적입니다. 실제로 어떤 업무를 선택해야 하는지는 본인 상황에 따라 달라질 수 있어요.',

    disclaimer: '이 도우미는 예약 전에 필요한 정보를 정리해 주는 안내입니다. 실제 신청 가능 여부와 처리 기준은 하이코리아, 1345, 또는 관할 출입국에서 최종 확인하세요.'
  };

  var STR_EN = {
    modalAria: 'HiKorea Reservation Helper',
    headerTitle: 'HiKorea Reservation Helper',
    headerSub: 'Find the right visit reservation path before going to immigration.',
    notOfficialChip: 'Not an official service',
    progressAria: 'Progress',
    next: 'Next',
    back: 'Back',
    findPath: 'Find my reservation path',
    restart: 'Start over',
    close: 'Close',
    goHikorea: 'Go to HiKorea',
    viewDocs: 'View document checklist',
    saveResult: 'Save result',
    saved: 'Copied',
    saveFail: 'Could not copy. Please save the screen yourself.',
    hotline: 'If reservations or procedures are confusing, call the Immigration Contact Center at 1345.',
    call1345: 'Call 1345',

    q1: 'Why are you visiting immigration?',
    q1Help: 'You do not need to know the exact official term. Choose the closest situation.',
    q2: 'Do you have an Alien Registration Card or residence card?',
    q2Help: 'Your reservation path may differ depending on whether you already have a card.',
    q3: 'Are you currently in Korea?',
    q3Help: 'HiKorea visit reservations are usually for visiting an immigration office in Korea.',
    q4: 'Do you know your current visa/status type?',
    q4Help: 'For example, you can enter a code like D-2, F-4, or E-7 if you know it.',
    q4Placeholder: 'e.g., D-2, F-4, E-7',
    q4Skip: 'I am not sure',
    q5: 'When does your current stay expire?',
    q5Help: 'Extension should be requested before your stay expires. Check the exact application window before visiting.',
    q5Skip: 'I am not sure',

    optYes: 'Yes',
    optNo: 'No',
    optNotSure: 'Not sure',
    optInKorea: 'I am in Korea',
    optOverseas: 'I am outside Korea',

    pRegistration: 'Alien registration',
    pExtension: 'Extension of stay',
    pChange: 'Change of status',
    pActivity: 'Permission for activities outside current status',
    pWorkplace: 'Change or addition of workplace',
    pAddress: 'Change of address',
    pReissue: 'Reissue of registration card',
    pUnsure: 'I am not sure',
    pResidenceReport: 'Domestic residence report',
    pResidenceReissue: 'Reissue of residence card',
    pRegChange: 'Change of registration details',
    pConsult: 'Other residence-related consultation',
    pConsultF5: 'Status-related consultation',

    resultLabel: 'Recommended reservation purpose',
    resultLead: 'Based on your answers, this is likely the reservation purpose you need on HiKorea.',
    resultLeadLow: 'We could not confirm a recommendation yet. Use the guidance below and confirm the exact reservation purpose with 1345 or your immigration office.',
    confLabel: 'Confidence',
    confHigh: 'high',
    confMedium: 'medium',
    confLow: 'low',

    secClick: 'What to click on HiKorea',
    secBefore: 'What to prepare before booking',
    secAfter: 'What to check after booking',
    secBlocked: 'If booking does not work',
    cautionsTitle: 'Please keep in mind',

    click1: 'Open HiKorea',
    click2: 'Choose Civil Petitions',
    click3: 'Choose Visit Reservation',
    click4: 'Start visit reservation',
    click5: 'Log in or use non-member verification',
    click6: 'Choose the immigration office',
    click7: 'Choose the visit purpose',
    click8: 'Select date and time',
    click9: 'Save the reservation confirmation',

    bIdentity: 'Passport or photo ID',
    bRealNameAcct: 'Details under the name of the actual visitor',
    bDocsReady: 'Check the documents needed for your application in advance',
    bAddressKnown: 'Know your current address',
    bOfficeKnown: 'Know which immigration office to visit',

    aSaveConfirm: 'Save or screenshot the reservation confirmation.',
    aCheckDateOffice: 'Double-check the reserved date and the immigration office you will visit.',
    aVisitorName: 'Confirm the reservation is under the name of the person who will visit.',
    aSameDayReminder: 'Same-day reservations may not be available, so check available dates in advance.',

    wSameDay: 'Same-day reservations may not be available. Visit reservations are usually available from the next day onward.',
    wRealName: 'The reservation should be made under the name of the person who will visit.',
    wOverseasNotice: 'HiKorea visit reservations are usually for visiting an immigration office in Korea. If you are still abroad, check again after you arrive.',
    wUnsureGuidance: 'If you are not sure which purpose to choose, contact 1345 or your immigration office.',
    wExtensionWindow: 'You should apply for an extension before your visa expires. Check the exact application window before visiting.',
    wExpired: 'The expiry date you entered has already passed. Delays can cause problems — contact 1345 or your immigration office right away.',
    wImminent: 'Your expiry date is close. Book as soon as possible and prepare your application.',
    wRegisterFirst: 'You may need to complete alien registration first. If you do not have a card yet, check the registration step first.',
    wAlreadyRegistered: 'If you already have a card, you may not need to register again. Re-check which task you actually need.',
    wF4ResidenceReport: 'F-4 holders often file a domestic residence report instead of alien registration.',

    blkNoDatesT: 'No dates are available',
    blkNoDatesB: 'Available slots may already be full. Try another date, or contact 1345 or your immigration office.',
    blkTodayT: 'I want to visit today',
    blkTodayB: 'Same-day visit reservations may not be available. Check available dates before going.',
    blkOfficeT: 'I do not know which office to choose',
    blkOfficeB: 'The office is usually based on your current address. If unsure, contact 1345 or your immigration office.',
    blkLoginT: 'Login or verification does not work',
    blkLoginB: 'If member login does not work, check whether non-member verification is available. If it still fails, use HiKorea support or call 1345.',
    blkPurposeT: 'I do not know which purpose to choose',
    blkPurposeB: 'Save your Paradiso result and confirm the exact reservation purpose with 1345 or your immigration office.',

    statusSuggTitle: 'Common reservation purposes for this status',
    statusSuggCaution: 'These are common reservation purposes for this status. The exact purpose may differ depending on your situation.',

    disclaimer: 'This helper organizes information before booking. Final availability and processing standards should be confirmed with HiKorea, 1345, or your immigration office.'
  };

  var STR_PACKS = { ko: STR_KO, en: STR_EN };
  var STR = (typeof Proxy === 'function')
    ? new Proxy({}, { get: function (_t, k) { var p = STR_PACKS[prhLang()] || STR_KO; return (p[k] != null) ? p[k] : STR_KO[k]; } })
    : STR_KO;

  /* ----------------------------------------------- purpose / status tables */
  // Purpose id → STR label key. Includes the 8 step-1 options plus the extra
  // status-specific purposes (F-4 거소 / F-5 등록사항 변경 / G-1 상담).
  var PURPOSE_LABEL_KEY = {
    registration: 'pRegistration',
    extension: 'pExtension',
    change_status: 'pChange',
    activity: 'pActivity',
    workplace: 'pWorkplace',
    address: 'pAddress',
    reissue: 'pReissue',
    unsure: 'pUnsure',
    residence_report: 'pResidenceReport',
    residence_reissue: 'pResidenceReissue',
    reg_change: 'pRegChange',
    consult: 'pConsult',
    consult_f5: 'pConsultF5'
  };

  // The eight step-1 purpose cards, in order.
  var PURPOSE_OPTIONS = ['registration', 'extension', 'change_status', 'activity', 'workplace', 'address', 'reissue', 'unsure'];

  // Common reservation purposes per status. Framed as suggestions, never as
  // guaranteed instructions. F-5 deliberately uses concrete user-facing tasks
  // (change of address · reissue of card · change of registration details ·
  // status-related consultation) at the SAME specificity as the other statuses
  // — never vague permanent-residence catch-all wording.
  var STATUS_SUGGESTIONS = {
    'D-2': ['registration', 'extension', 'address', 'activity'],
    'F-4': ['residence_report', 'extension', 'residence_reissue', 'address'],
    'E-7': ['registration', 'change_status', 'workplace', 'extension'],
    'F-6': ['registration', 'extension', 'address', 'reissue'],
    'F-5': ['address', 'reissue', 'reg_change', 'consult_f5'],
    'G-1': ['registration', 'extension', 'address', 'consult']
  };

  function normalizeCode(code) {
    var c = String(code || '').toUpperCase().replace(/\s+/g, '');
    if (!c) return '';
    // Map a subcode (D-2-1 → D-2) to its parent family for suggestion lookup.
    var m = c.match(/^([A-H]-\d{1,2})/);
    return m ? m[1] : c;
  }

  function suggestionsFor(code) {
    var key = normalizeCode(code);
    return STATUS_SUGGESTIONS[key] || null;
  }

  function purposeLabel(id) {
    var k = PURPOSE_LABEL_KEY[id];
    return k ? STR[k] : id;
  }

  /* --------------------------------------------------------------- styles */
  var STYLE_ID = 'prh-styles';
  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      '#hikoreaGuideBody .prh-root{display:flex;flex-direction:column;gap:1rem;color:var(--t1);font-family:var(--ff,inherit);}',
      '#hikoreaGuideBody .prh-progress{display:flex;align-items:center;gap:.6rem;}',
      '#hikoreaGuideBody .prh-progress-track{flex:1;height:8px;border-radius:999px;background:var(--bg2);overflow:hidden;}',
      '#hikoreaGuideBody .prh-progress-fill{height:100%;background:var(--ac);border-radius:999px;transition:width .25s ease;}',
      '#hikoreaGuideBody .prh-progress-label{font-size:.8rem;font-weight:800;color:var(--t2);white-space:nowrap;}',
      '#hikoreaGuideBody .prh-q{font-size:1.18rem;font-weight:800;line-height:1.4;margin:.2rem 0 0;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-help{font-size:.9rem;line-height:1.55;color:var(--t2);margin:0;}',
      '#hikoreaGuideBody .prh-options{display:grid;gap:.6rem;grid-template-columns:1fr;}',
      '@media (min-width:560px){#hikoreaGuideBody .prh-options.prh-grid-2{grid-template-columns:1fr 1fr;}}',
      '#hikoreaGuideBody .prh-opt{display:flex;align-items:center;gap:.6rem;width:100%;min-height:52px;text-align:left;padding:.85rem 1rem;border:1.5px solid var(--bd);border-radius:var(--radius-md,10px);background:var(--bg1);color:var(--t1);font-size:1rem;font-weight:700;font-family:inherit;cursor:pointer;transition:border-color .15s,background .15s,box-shadow .15s;}',
      '#hikoreaGuideBody .prh-opt:hover{border-color:var(--ac);background:color-mix(in srgb,var(--ac) 6%,var(--bg1));}',
      '#hikoreaGuideBody .prh-opt:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-opt.is-selected{border-color:var(--ac);background:color-mix(in srgb,var(--ac) 12%,var(--bg1));box-shadow:inset 0 0 0 1px var(--ac);}',
      '#hikoreaGuideBody .prh-opt .prh-opt-check{margin-left:auto;color:var(--ac);font-weight:900;opacity:0;}',
      '#hikoreaGuideBody .prh-opt.is-selected .prh-opt-check{opacity:1;}',
      '#hikoreaGuideBody .prh-field{display:flex;flex-direction:column;gap:.5rem;}',
      '#hikoreaGuideBody .prh-input{width:100%;padding:.8rem .9rem;border:1.5px solid var(--bd);border-radius:var(--radius-md,10px);background:var(--bgI,var(--bg1));color:var(--t1);font-size:1rem;font-family:inherit;}',
      '#hikoreaGuideBody .prh-input:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:1px;border-color:var(--ac);}',
      '#hikoreaGuideBody .prh-sugg{border:1px dashed var(--bd3);border-radius:var(--radius-md,10px);padding:.8rem .9rem;background:var(--bg2);display:flex;flex-direction:column;gap:.55rem;}',
      '#hikoreaGuideBody .prh-sugg-title{font-size:.84rem;font-weight:800;color:var(--t1);margin:0;}',
      '#hikoreaGuideBody .prh-sugg-caution{font-size:.78rem;line-height:1.5;color:var(--t3);margin:0;}',
      '#hikoreaGuideBody .prh-chips{display:flex;flex-wrap:wrap;gap:.4rem;}',
      '#hikoreaGuideBody .prh-chip{border:1px solid var(--ac);background:transparent;color:var(--ac2,var(--ac));font-size:.82rem;font-weight:700;font-family:inherit;padding:.36rem .7rem;border-radius:999px;cursor:pointer;}',
      '#hikoreaGuideBody .prh-chip:hover{background:color-mix(in srgb,var(--ac) 10%,transparent);}',
      '#hikoreaGuideBody .prh-chip:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-nav{display:flex;gap:.6rem;align-items:center;margin-top:.3rem;}',
      '#hikoreaGuideBody .prh-btn{appearance:none;border-radius:var(--radius-md,10px);font-family:inherit;font-weight:800;font-size:.95rem;padding:.8rem 1.1rem;cursor:pointer;min-height:48px;border:1.5px solid var(--bd);background:var(--bg1);color:var(--t1);}',
      '#hikoreaGuideBody .prh-btn:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-btn.prh-primary{background:var(--ac);border-color:var(--ac);color:#fff;margin-left:auto;}',
      '#hikoreaGuideBody .prh-btn.prh-primary:hover{background:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-btn[disabled]{opacity:.45;cursor:not-allowed;}',
      '#hikoreaGuideBody .prh-strip{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;font-size:.84rem;line-height:1.5;color:var(--t2);background:var(--bg2);border:1px solid var(--bd2);border-radius:var(--radius-md,10px);padding:.55rem .8rem;}',
      '#hikoreaGuideBody .prh-strip a{color:var(--ac);font-weight:800;}',
      '#hikoreaGuideBody .prh-result-card{border:1.5px solid var(--ac);border-radius:var(--radius-lg,14px);background:color-mix(in srgb,var(--ac) 7%,var(--bg1));padding:1rem 1.05rem;display:flex;flex-direction:column;gap:.4rem;}',
      '#hikoreaGuideBody .prh-result-kicker{font-size:.78rem;font-weight:800;letter-spacing:.02em;color:var(--ac2,var(--ac));text-transform:uppercase;}',
      '#hikoreaGuideBody .prh-result-purpose{font-size:1.5rem;font-weight:900;line-height:1.25;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-result-lead{font-size:.9rem;line-height:1.55;color:var(--t2);margin:0;}',
      '#hikoreaGuideBody .prh-conf{align-self:flex-start;font-size:.74rem;font-weight:800;padding:.2rem .55rem;border-radius:999px;border:1px solid var(--bd);background:var(--bg1);color:var(--t2);}',
      '#hikoreaGuideBody .prh-conf.is-high{border-color:var(--ac);color:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-conf.is-low{border-color:var(--color-warning,#b88600);color:var(--color-warning,#b88600);}',
      '#hikoreaGuideBody .prh-cautions{border:1px solid color-mix(in srgb,var(--color-warning,#b88600) 35%,transparent);background:color-mix(in srgb,var(--color-warning,#b88600) 10%,var(--bg1));border-radius:var(--radius-md,10px);padding:.7rem .9rem;}',
      '#hikoreaGuideBody .prh-cautions h4{margin:0 0 .4rem;font-size:.82rem;font-weight:800;}',
      '#hikoreaGuideBody .prh-cautions ul{margin:0;padding-left:1.1rem;display:flex;flex-direction:column;gap:.3rem;}',
      '#hikoreaGuideBody .prh-cautions li{font-size:.85rem;line-height:1.5;}',
      '#hikoreaGuideBody .prh-sections{display:grid;gap:.7rem;grid-template-columns:1fr;}',
      '@media (min-width:620px){#hikoreaGuideBody .prh-sections{grid-template-columns:1fr 1fr;}}',
      '#hikoreaGuideBody .prh-section{border:1px solid var(--bd2);border-radius:var(--radius-md,10px);background:var(--bg1);padding:.8rem .9rem;}',
      '#hikoreaGuideBody .prh-section h4{margin:0 0 .5rem;font-size:.92rem;font-weight:800;display:flex;align-items:center;gap:.4rem;}',
      '#hikoreaGuideBody .prh-section ol,#hikoreaGuideBody .prh-section ul{margin:0;padding-left:1.15rem;display:flex;flex-direction:column;gap:.32rem;}',
      '#hikoreaGuideBody .prh-section li{font-size:.86rem;line-height:1.5;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-blocked details{border:1px solid var(--bd2);border-radius:var(--radius-md,10px);background:var(--bg1);padding:.1rem .2rem;margin-bottom:.4rem;}',
      '#hikoreaGuideBody .prh-blocked summary{cursor:pointer;font-size:.88rem;font-weight:700;padding:.6rem .7rem;list-style:none;}',
      '#hikoreaGuideBody .prh-blocked summary::-webkit-details-marker{display:none;}',
      '#hikoreaGuideBody .prh-blocked summary::after{content:"+";float:right;font-weight:900;color:var(--t3);}',
      '#hikoreaGuideBody .prh-blocked details[open] summary::after{content:"–";}',
      '#hikoreaGuideBody .prh-blocked .prh-blocked-body{font-size:.85rem;line-height:1.55;color:var(--t2);padding:0 .7rem .7rem;margin:0;}',
      '#hikoreaGuideBody .prh-ctas{display:flex;flex-wrap:wrap;gap:.55rem;}',
      '#hikoreaGuideBody .prh-cta{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;min-height:48px;padding:.75rem 1rem;border-radius:var(--radius-md,10px);font-weight:800;font-size:.92rem;font-family:inherit;cursor:pointer;text-decoration:none;border:1.5px solid var(--bd);background:var(--bg1);color:var(--t1);}',
      '#hikoreaGuideBody .prh-cta:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-cta.prh-cta-secondary{flex:1;min-width:160px;background:var(--ac);border-color:var(--ac);color:#fff;}',
      '#hikoreaGuideBody .prh-disclaimer{font-size:.78rem;line-height:1.55;color:var(--t3);border-top:1px dashed var(--bd2);padding-top:.7rem;margin:0;}',
      '#hikoreaGuideBody .prh-section-full{grid-column:1/-1;}',
      // Mobile sticky action bar keeps the primary control reachable.
      '@media (max-width:560px){#hikoreaGuideBody .prh-nav{position:sticky;bottom:0;background:var(--bg0);padding:.6rem 0 .2rem;border-top:1px solid var(--bd2);z-index:2;}#hikoreaGuideBody .prh-ctas .prh-cta{flex:1 1 100%;}}'
    ].join('\n');
    var el = document.createElement('style');
    el.id = STYLE_ID;
    el.textContent = css;
    document.head.appendChild(el);
  }

  /* ----------------------------------------------------------------- state */
  var state = {
    visaCode: '',
    purpose: '',
    card: '',
    loc: '',
    code: '',
    expiry: '',
    step: 1,
    view: 'wizard'
  };

  function needsExpiry() { return state.purpose === 'extension'; }
  function totalSteps() { return needsExpiry() ? 5 : 4; }

  function getBody() { return document.getElementById('hikoreaGuideBody'); }

  /* ------------------------------------------------------------ rendering */
  function header() {
    var titleEl = document.getElementById('hikoreaGuideTitle');
    var subEl = document.getElementById('hikoreaGuideSub');
    var chipEl = document.getElementById('hikoreaGuideChip');
    if (titleEl) titleEl.textContent = STR.headerTitle;
    if (subEl) subEl.textContent = STR.headerSub;
    if (chipEl) chipEl.textContent = STR.notOfficialChip;
  }

  function progressHtml() {
    var total = totalSteps();
    var pct = Math.round((state.step / total) * 100);
    return '<div class="prh-progress" role="progressbar" aria-label="' + esc(STR.progressAria) +
      '" aria-valuemin="1" aria-valuemax="' + total + '" aria-valuenow="' + state.step + '">' +
      '<div class="prh-progress-track"><div class="prh-progress-fill" style="width:' + pct + '%"></div></div>' +
      '<span class="prh-progress-label">' + state.step + ' / ' + total + '</span></div>';
  }

  function optBtn(field, value, label, selected) {
    return '<button type="button" class="prh-opt' + (selected ? ' is-selected' : '') + '" data-prh-action="pick" data-prh-field="' + esc(field) + '" data-prh-value="' + esc(value) + '">' +
      '<span>' + esc(label) + '</span><span class="prh-opt-check" aria-hidden="true">✓</span></button>';
  }

  function navHtml(opts) {
    opts = opts || {};
    var back = state.step > 1
      ? '<button type="button" class="prh-btn" data-prh-action="back">' + esc(STR.back) + '</button>'
      : '';
    var nextLabel = opts.last ? STR.findPath : STR.next;
    var nextDisabled = opts.nextDisabled ? ' disabled' : '';
    var next = '<button type="button" class="prh-btn prh-primary" data-prh-action="next"' + nextDisabled + '>' + esc(nextLabel) + '</button>';
    return '<div class="prh-nav">' + back + next + '</div>';
  }

  function hotlineHtml() {
    return '<div class="prh-strip">' + esc(STR.hotline) + ' <a href="tel:1345">' + esc(STR.call1345) + '</a></div>';
  }

  function suggestionPanelHtml() {
    var sugg = suggestionsFor(state.code || state.visaCode);
    if (!sugg) return '';
    var chips = sugg.map(function (id) {
      return '<button type="button" class="prh-chip" data-prh-action="pick-suggestion" data-prh-value="' + esc(id) + '">' + esc(purposeLabel(id)) + '</button>';
    }).join('');
    return '<div class="prh-sugg"><p class="prh-sugg-title">' + esc(STR.statusSuggTitle) + ' · ' + esc(normalizeCode(state.code || state.visaCode)) + '</p>' +
      '<div class="prh-chips">' + chips + '</div>' +
      '<p class="prh-sugg-caution">' + esc(STR.statusSuggCaution) + '</p></div>';
  }

  function renderStep() {
    var body = getBody();
    if (!body) return;
    var html = progressHtml();

    if (state.step === 1) {
      html += '<h3 class="prh-q">' + esc(STR.q1) + '</h3><p class="prh-help">' + esc(STR.q1Help) + '</p>';
      html += suggestionPanelHtml();
      html += '<div class="prh-options prh-grid-2">' + PURPOSE_OPTIONS.map(function (id) {
        return optBtn('purpose', id, purposeLabel(id), state.purpose === id);
      }).join('') + '</div>';
      html += navHtml({ nextDisabled: !state.purpose });
    } else if (state.step === 2) {
      html += '<h3 class="prh-q">' + esc(STR.q2) + '</h3><p class="prh-help">' + esc(STR.q2Help) + '</p>';
      html += '<div class="prh-options">' +
        optBtn('card', 'yes', STR.optYes, state.card === 'yes') +
        optBtn('card', 'no', STR.optNo, state.card === 'no') +
        optBtn('card', 'unsure', STR.optNotSure, state.card === 'unsure') + '</div>';
      html += navHtml({ nextDisabled: !state.card });
    } else if (state.step === 3) {
      html += '<h3 class="prh-q">' + esc(STR.q3) + '</h3><p class="prh-help">' + esc(STR.q3Help) + '</p>';
      html += '<div class="prh-options">' +
        optBtn('loc', 'in_korea', STR.optInKorea, state.loc === 'in_korea') +
        optBtn('loc', 'overseas', STR.optOverseas, state.loc === 'overseas') + '</div>';
      html += navHtml({ nextDisabled: !state.loc });
    } else if (state.step === 4) {
      var lastOnFour = !needsExpiry();
      html += '<h3 class="prh-q">' + esc(STR.q4) + '</h3><p class="prh-help">' + esc(STR.q4Help) + '</p>';
      html += '<div class="prh-field"><input type="text" class="prh-input" id="prhCode" inputmode="text" autocomplete="off" spellcheck="false" placeholder="' + esc(STR.q4Placeholder) + '" aria-label="' + esc(STR.q4) + '" value="' + esc(state.code) + '" data-prh-field="code">';
      html += '<div class="prh-options">' + optBtn('code', '__skip__', STR.q4Skip, state.code === '__skip__') + '</div></div>';
      html += navHtml({ last: lastOnFour });
    } else if (state.step === 5) {
      html += '<h3 class="prh-q">' + esc(STR.q5) + '</h3><p class="prh-help">' + esc(STR.q5Help) + '</p>';
      html += '<div class="prh-field"><input type="date" class="prh-input" id="prhExpiry" aria-label="' + esc(STR.q5) + '" value="' + esc(state.expiry === '__skip__' ? '' : state.expiry) + '" data-prh-field="expiry">';
      html += '<div class="prh-options">' + optBtn('expiry', '__skip__', STR.q5Skip, state.expiry === '__skip__') + '</div></div>';
      html += navHtml({ last: true });
    }

    html += hotlineHtml();
    html += '<p class="prh-disclaimer">' + esc(STR.disclaimer) + '</p>';
    body.innerHTML = '<div class="prh-root" data-prh-root>' + html + '</div>';
  }

  function warningText(key) {
    var map = {
      sameDay: 'wSameDay', realName: 'wRealName', overseasNotice: 'wOverseasNotice',
      unsureGuidance: 'wUnsureGuidance', extensionWindow: 'wExtensionWindow',
      expired: 'wExpired', imminent: 'wImminent', registerFirst: 'wRegisterFirst',
      alreadyRegistered: 'wAlreadyRegistered', f4ResidenceReport: 'wF4ResidenceReport'
    };
    return map[key] ? STR[map[key]] : '';
  }

  function renderResult() {
    var body = getBody();
    if (!body) return;
    var model = computeReservationPath({
      reservationPurpose: state.purpose,
      hasRegistrationCard: state.card,
      currentLocation: state.loc,
      statusCode: (state.code && state.code !== '__skip__') ? state.code : (state.visaCode || ''),
      expiryDate: (state.expiry && state.expiry !== '__skip__') ? state.expiry : ''
    });
    state.lastModel = model;

    var isLow = model.confidence === 'low' || model.recommendedPurpose === 'unsure';
    var confKey = model.confidence === 'high' ? 'confHigh' : (model.confidence === 'low' ? 'confLow' : 'confMedium');
    var confCls = model.confidence === 'high' ? ' is-high' : (model.confidence === 'low' ? ' is-low' : '');

    var html = '';

    // Result card
    html += '<div class="prh-result-card">';
    html += '<span class="prh-result-kicker">' + esc(STR.resultLabel) + '</span>';
    if (!isLow) html += '<div class="prh-result-purpose">' + esc(purposeLabel(model.recommendedPurpose)) + '</div>';
    html += '<p class="prh-result-lead">' + esc(isLow ? STR.resultLeadLow : STR.resultLead) + '</p>';
    html += '<span class="prh-conf' + confCls + '">' + esc(STR.confLabel) + ': ' + esc(STR[confKey]) + '</span>';
    html += '</div>';

    // Cautions (always carry same-day + real-name)
    var cautionLis = model.warnings.map(function (w) {
      var t = warningText(w);
      return t ? '<li>' + esc(t) + '</li>' : '';
    }).join('');
    if (cautionLis) {
      html += '<div class="prh-cautions"><h4>' + esc(STR.cautionsTitle) + '</h4><ul>' + cautionLis + '</ul></div>';
    }

    // Four compact sections
    html += '<div class="prh-sections">';

    // 1. What to click
    var clickLis = model.hikoreaClickSteps.map(function (id, i) {
      return '<li>' + esc(STR['click' + (i + 1)]) + '</li>';
    }).join('');
    html += '<div class="prh-section prh-section-full"><h4>🖱️ ' + esc(STR.secClick) + '</h4><ol>' + clickLis + '</ol></div>';

    // 2. Before booking
    var beforeLis = model.beforeBookingChecklist.map(function (id) {
      var k = { identity: 'bIdentity', realNameAcct: 'bRealNameAcct', docsReady: 'bDocsReady', addressKnown: 'bAddressKnown', officeKnown: 'bOfficeKnown' }[id];
      return k ? '<li>' + esc(STR[k]) + '</li>' : '';
    }).join('');
    html += '<div class="prh-section"><h4>🎒 ' + esc(STR.secBefore) + '</h4><ul>' + beforeLis + '</ul></div>';

    // 3. After booking
    var afterLis = model.afterBookingChecklist.map(function (id) {
      var k = { saveConfirm: 'aSaveConfirm', checkDateOffice: 'aCheckDateOffice', visitorName: 'aVisitorName', sameDayReminder: 'aSameDayReminder' }[id];
      return k ? '<li>' + esc(STR[k]) + '</li>' : '';
    }).join('');
    html += '<div class="prh-section"><h4>✅ ' + esc(STR.secAfter) + '</h4><ul>' + afterLis + '</ul></div>';

    html += '</div>'; // .prh-sections

    // 4. Blocked-case guidance
    var blkMap = {
      noDates: ['blkNoDatesT', 'blkNoDatesB'], today: ['blkTodayT', 'blkTodayB'],
      office: ['blkOfficeT', 'blkOfficeB'], login: ['blkLoginT', 'blkLoginB'],
      purpose: ['blkPurposeT', 'blkPurposeB']
    };
    var blkHtml = model.blockedCaseTips.map(function (id) {
      var pair = blkMap[id];
      if (!pair) return '';
      return '<details><summary>' + esc(STR[pair[0]]) + '</summary><p class="prh-blocked-body">' + esc(STR[pair[1]]) + '</p></details>';
    }).join('');
    html += '<div class="prh-section prh-blocked prh-section-full"><h4>🛟 ' + esc(STR.secBlocked) + '</h4>' + blkHtml + '</div>';

    // CTAs (hierarchy: Go to HiKorea · View docs (if code) · Save result · Start over)
    html += '<div class="prh-ctas">';
    html += '<a class="prh-cta prh-cta-secondary" href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">' + esc(STR.goHikorea) + '</a>';
    var docCode = (state.code && state.code !== '__skip__') ? state.code : (state.visaCode || '');
    if (docCode) {
      var docType = (model.recommendedPurpose === 'extension') ? 'ext' : ((model.recommendedPurpose === 'change_status') ? 'change' : 'new');
      html += '<button type="button" class="prh-cta" data-action="open-doc-modal" data-vcode="' + esc(docCode) + '" data-type="' + docType + '">' + esc(STR.viewDocs) + '</button>';
    }
    html += '<button type="button" class="prh-cta" data-prh-action="save-result">' + esc(STR.saveResult) + '</button>';
    html += '<button type="button" class="prh-cta" data-prh-action="restart">' + esc(STR.restart) + '</button>';
    html += '</div>';

    html += hotlineHtml();
    html += '<p class="prh-disclaimer">' + esc(STR.disclaimer) + '</p>';

    body.innerHTML = '<div class="prh-root" data-prh-root>' + html + '</div>';
  }

  function render() {
    ensureStyles();
    header();
    if (state.view === 'result') renderResult();
    else renderStep();
  }

  /* ---------------------------------------------------------- transitions */
  function captureInputs() {
    var codeInput = document.getElementById('prhCode');
    if (codeInput && state.step === 4) {
      var v = codeInput.value.trim();
      if (v) state.code = v;
    }
    var expInput = document.getElementById('prhExpiry');
    if (expInput && state.step === 5 && expInput.value) state.expiry = expInput.value;
  }

  function goNext() {
    captureInputs();
    if (state.step === 1 && !state.purpose) return;
    if (state.step === 2 && !state.card) return;
    if (state.step === 3 && !state.loc) return;
    var total = totalSteps();
    if (state.step >= total) {
      state.view = 'result';
      render();
      return;
    }
    state.step += 1;
    render();
  }

  function goBack() {
    captureInputs();
    if (state.view === 'result') {
      state.view = 'wizard';
      state.step = totalSteps();
      render();
      return;
    }
    if (state.step > 1) state.step -= 1;
    render();
  }

  function buildResultText() {
    var m = state.lastModel || {};
    var lines = [];
    lines.push(STR.headerTitle);
    lines.push(STR.resultLabel + ': ' + purposeLabel(m.recommendedPurpose));
    lines.push('');
    lines.push(STR.secClick + ':');
    (m.hikoreaClickSteps || []).forEach(function (id, i) { lines.push((i + 1) + '. ' + STR['click' + (i + 1)]); });
    lines.push('');
    lines.push(STR.secBefore + ':');
    (m.beforeBookingChecklist || []).forEach(function (id) {
      var k = { identity: 'bIdentity', realNameAcct: 'bRealNameAcct', docsReady: 'bDocsReady', addressKnown: 'bAddressKnown', officeKnown: 'bOfficeKnown' }[id];
      if (k) lines.push('- ' + STR[k]);
    });
    lines.push('');
    lines.push(STR.disclaimer);
    return lines.join('\n');
  }

  function saveResult(btn) {
    var text = buildResultText();
    function done() { if (btn) { var o = btn.textContent; btn.textContent = STR.saved; setTimeout(function () { btn.textContent = o; }, 1600); } }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () { if (btn) btn.textContent = STR.saveFail; });
    } else if (btn) {
      btn.textContent = STR.saveFail;
    }
  }

  /* ------------------------------------------------------ event handling */
  function onClick(e) {
    var root = e.target.closest && e.target.closest('[data-prh-root]');
    if (!root) return;
    var actionEl = e.target.closest('[data-prh-action]');
    if (!actionEl) return;
    var action = actionEl.getAttribute('data-prh-action');
    if (action === 'pick') {
      var field = actionEl.getAttribute('data-prh-field');
      var value = actionEl.getAttribute('data-prh-value');
      if (field === 'purpose') state.purpose = value;
      else if (field === 'card') state.card = value;
      else if (field === 'loc') state.loc = value;
      else if (field === 'code') state.code = value;
      else if (field === 'expiry') state.expiry = value;
      // Single-choice steps auto-advance for a faster, app-like flow.
      if (field === 'purpose' || field === 'card' || field === 'loc') {
        goNext();
      } else {
        render();
      }
    } else if (action === 'pick-suggestion') {
      state.purpose = actionEl.getAttribute('data-prh-value');
      goNext();
    } else if (action === 'next') {
      goNext();
    } else if (action === 'back') {
      goBack();
    } else if (action === 'restart') {
      reset({ visaCode: state.visaCode });
      render();
    } else if (action === 'save-result') {
      saveResult(actionEl);
    }
  }

  function onChange(e) {
    var t = e.target;
    if (!t || !t.getAttribute) return;
    var field = t.getAttribute('data-prh-field');
    if (!field) return;
    if (field === 'code') { state.code = t.value.trim(); }
    else if (field === 'expiry') { state.expiry = t.value; }
  }

  /* ---------------------------------------------------------- public API */
  function reset(opts) {
    opts = opts || {};
    state.visaCode = opts.visaCode || '';
    state.purpose = '';
    state.card = '';
    state.loc = '';
    state.code = opts.visaCode ? normalizeCode(opts.visaCode) : '';
    state.expiry = '';
    state.step = 1;
    state.view = 'wizard';
    state.lastModel = null;
    // Optional prefill of the most-likely purpose from a status' hikorea task
    // type (e.g. visa_data hikorea_task_type "체류기간 연장허가" → extension).
    // Prefill is a hint surfaced as suggestions/selection only — never forced.
    if (opts.taskType === '체류기간 연장허가') state.purpose = '';
  }

  function open(opts) {
    reset(opts || {});
    render();
  }

  // Wire delegated listeners once. #hikoreaGuideBody exists in the initial HTML
  // (this script is deferred), so document-level delegation is timing-safe.
  document.addEventListener('click', onClick);
  document.addEventListener('change', onChange);

  // Live language switch: re-render whatever view is open.
  window.addEventListener('paradiso-language-applied', function () {
    var overlay = document.getElementById('hikoreaGuideOverlay');
    if (overlay && overlay.classList.contains('active')) {
      try { render(); } catch (e) { /* noop */ }
    }
  });

  window.ParadisoReservationHelper = {
    version: 1,
    open: open,
    render: render,
    reset: reset,
    computeReservationPath: computeReservationPath,
    suggestionsFor: suggestionsFor
  };
})();
