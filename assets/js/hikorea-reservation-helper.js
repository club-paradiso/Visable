/* ============================================================================
 * Paradiso — 하이코리아 방문예약 도우미 / HiKorea Reservation Helper
 * ----------------------------------------------------------------------------
 * A friendly, mobile-first, photo/screenshot-based step-by-step guide that takes
 * a first-time user all the way from "do I even need an account?" to a confirmed
 * visit reservation — without needing any external explanation.
 *
 * It is organized as a tabbed guide rendered inside the existing
 * #hikoreaGuideOverlay modal shell (index.html owns the shell + focus trap /
 * Escape / focus restore; this module owns the content + logic):
 *
 *   처음 이용하기 (overview + quick-path selector)
 *   회원가입       (account sign-up, photo step cards)
 *   로그인         (login, photo step cards)
 *   방문예약 잡기   (booking photo steps + the interactive "예약 목적 찾기" wizard)
 *   예약 확인·변경  (check / change a reservation)
 *   문제 해결       (troubleshooting accordion)
 *
 * The interactive reservation-purpose finder (one-question-at-a-time flow built
 * on computeReservationPath) is preserved unchanged and now lives inside the
 * 방문예약 잡기 tab.
 *
 * Design contract (do not weaken):
 *  - Deterministic + testable: computeReservationPath() is a pure function with
 *    no DOM/network/model dependency. The visible flow is fully rule-based — it
 *    never calls any language model. (scripts/check_hikorea_reservation_helper.mjs)
 *  - Cautious wording only. Recommendations are framed as "likely", never as
 *    official rules. The result and footer always carry the official-source
 *    disclaimer (HiKorea / 1345 / 관할 출입국), plus a clear non-affiliation note.
 *  - No invented immigration-law claims; no document requirements beyond the
 *    generic preparation reminders below.
 *  - Korean is canonical; English chrome is paired 1:1 (STR_KO/STR_EN — checked
 *    by scripts/check_popup_i18n.mjs). Per the repo i18n fallback policy, locales
 *    other than en resolve to Korean canonical chrome rather than machine text.
 *  - Screenshots are a navigation aid only, never Paradiso branding. No HiKorea
 *    logos/marks. No personal information in bundled assets. See
 *    assets/hikorea-guide/README.md for the naming + privacy-masking process.
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
  // Locales with a full chrome pack below. Anything not listed falls back to ko.
  var PRH_SUPPORTED = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
  function prhLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return PRH_SUPPORTED.indexOf(l) !== -1 ? l : 'ko';
  }

  var STR_KO = {
    modalAria: '하이코리아 방문예약 도우미',
    headerTitle: '하이코리아 예약 도우미',
    headerSub: '하이코리아 회원가입부터 방문예약 확인까지, 화면을 보며 순서대로 따라 하는 안내입니다.',
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

    disclaimer: '이 도우미는 예약 전에 필요한 정보를 정리해 주는 안내입니다. 실제 신청 가능 여부와 처리 기준은 하이코리아, 1345, 또는 관할 출입국에서 최종 확인하세요.',

    /* ---- tabbed photo guide chrome (added 2026-06) ---- */
    tablistAria: '하이코리아 안내 단계',
    tabOverview: '처음 이용하기',
    tabSignup: '회원가입',
    tabLogin: '로그인',
    tabReservation: '방문예약 잡기',
    tabManage: '예약 확인·변경',
    tabTrouble: '문제 해결',

    ovTitle: '하이코리아 방문예약 도우미',
    ovLead: '처음 하이코리아를 쓰는 분도 이 순서대로 따라오면 됩니다. 회원가입부터 방문예약 확인까지, 화면을 보면서 차근차근 안내해 드려요.',
    ovStart: '안내 시작하기',
    ovScreensWarn: '실제 하이코리아 화면은 수시로 바뀔 수 있어요. 버튼 이름이나 위치가 안내와 다르면, 비슷한 메뉴를 찾아보거나 하이코리아 공식 안내를 확인하세요.',
    quickTitle: '어떤 도움이 필요하세요?',
    qp1Title: '회원가입부터 필요해요',
    qp1Sub: '하이코리아 계정 만들기부터 시작합니다.',
    qp2Title: '이미 계정이 있어요',
    qp2Sub: '로그인하고 바로 방문예약을 잡습니다.',
    qp3Title: '예약만 확인하고 싶어요',
    qp3Sub: '잡아둔 예약을 확인하거나 변경합니다.',
    qp4Title: '문제가 생겼어요',
    qp4Sub: '예약이 안 되거나 막혔을 때 해결 방법을 봅니다.',
    affiliation: 'Paradiso는 하이코리아나 법무부와 제휴된 서비스가 아닙니다. 이 안내의 화면 설명은 길찾기용 참고 자료일 뿐이며, 실제 신청 내용은 하이코리아 공식 사이트에서 최종 확인하세요.',

    stepDoLabel: '여기서 할 일',
    stepCautionLabel: '주의할 점',
    stepEnLabel: '영어로 보면',
    stepNext: '다음 단계',
    stepDone: '체크 완료',
    stepDoneOn: '완료됨',
    progressDoneOf: '단계 완료',
    shotPending: '스크린샷 준비 중',
    shotPendingSub: '실제 화면 캡처는 곧 추가될 예정이에요. 아래 설명을 먼저 참고하세요.',
    guideProgressAria: '안내 진행률',
    prevTab: '이전',
    nextTab: '다음',
    openFinder: '내 상황에 맞는 예약 목적 찾기',
    openFinderSub: '체류자격과 상황을 몇 가지만 고르면 어떤 민원으로 예약할지 정리해 드려요.',
    backToPhotos: '사진 안내로 돌아가기',
    enlarge: '크게 보기',
    closeImage: '닫기',

    sgIntro: '하이코리아 계정을 만드는 과정이에요. 외국인은 보통 본인인증을 거쳐 가입합니다.',
    sgT1: '언어 선택하고 회원가입 시작',
    sgD1: '하이코리아 첫 화면에서 언어를 고르고, 상단 또는 메뉴의 회원가입을 누르세요.',
    sgC1: '언어를 영어로 바꿔도 일부 화면은 한국어로 나올 수 있어요.',
    sgE1: 'Pick your language, then tap “Sign Up / 회원가입” at the top.',
    sgT2: '약관 동의',
    sgD2: '이용약관과 개인정보 수집 항목을 읽고 동의에 체크한 뒤 다음으로 넘어가세요.',
    sgC2: '필수 항목에 동의하지 않으면 가입이 진행되지 않아요.',
    sgT3: '본인인증',
    sgD3: '외국인등록번호나 여권 정보, 휴대폰 등으로 본인인증을 합니다. 안내에 나온 인증 방법 중 가능한 것을 고르세요.',
    sgC3: '이름과 생년월일은 여권·등록증과 똑같이 입력해야 인증이 됩니다.',
    sgE3: 'Verify your identity with your ARC or passport details. Names must match your documents exactly.',
    sgT4: '아이디·비밀번호 등 계정 정보 입력',
    sgD4: '아이디, 비밀번호, 연락처 등 계정 정보를 입력하고 가입을 완료하세요.',
    sgC4: '비밀번호는 안전하게 보관하고, 가입에 쓴 이메일·전화번호를 기억해 두세요.',

    lgIntro: '계정이 있다면 로그인한 뒤 방문예약 메뉴로 이동합니다.',
    lgT1: '로그인 화면 열기',
    lgD1: '하이코리아 첫 화면에서 로그인을 누르고, 아이디와 비밀번호를 입력하세요.',
    lgC1: '비밀번호를 잊었다면 아이디·비밀번호 찾기를 이용하세요.',
    lgE1: 'Tap “Login”, then enter your ID and password.',
    lgT2: '간편인증 또는 비회원 인증 확인',
    lgD2: '회원 로그인이 어려우면 간편인증이나 비회원 인증으로 진행할 수 있는지 확인하세요.',
    lgC2: '인증서가 필요할 수 있으니 미리 준비해 두면 편해요.',

    resIntro: '로그인한 다음, 방문예약을 잡는 과정이에요. 화면 순서대로 따라오세요.',
    rsT1: '방문예약 메뉴 들어가기',
    rsD1: '민원신청 → 방문예약 → 방문예약 신청 순서로 들어갑니다.',
    rsC1: '당일 예약은 어려울 수 있어요. 보통 다음 날부터 예약할 수 있습니다.',
    rsE1: 'Go to Civil Petitions → Visit Reservation → Apply.',
    rsT2: '방문할 출입국관서 선택',
    rsD2: '이 화면에서는 방문할 출입국관서를 고릅니다. 보통 현재 사는 곳을 관할하는 관서를 선택해요.',
    rsC2: '관할 관서를 모르면 주소를 기준으로 확인하거나 1345에 문의하세요.',
    rsT3: '민원(예약 목적) 선택',
    rsD3: '외국인등록, 체류기간 연장 같은 민원 종류를 고릅니다. 본인이 하려는 업무를 선택하세요.',
    rsC3: '민원 종류 이름은 체류자격과 상황에 따라 다르게 보일 수 있어요.',
    rsE3: 'Choose your civil-service purpose (for example, registration or extension).',
    rsT4: '날짜와 시간 선택',
    rsD4: '달력에서 예약 가능한 날짜와 시간을 고릅니다.',
    rsC4: '예약 가능한 시간이 보이지 않으면 다른 날짜를 먼저 확인해 보세요.',
    rsT5: '예약 내용 확인하고 저장',
    rsD5: '선택한 관서·날짜·민원을 확인한 뒤 예약을 완료하고, 예약 확인증을 저장하거나 캡처하세요.',
    rsC5: '예약은 실제 방문하는 사람 이름으로 해야 합니다.',

    mngIntro: '잡아둔 예약을 확인하거나 변경·취소하는 방법이에요.',
    mgT1: '예약 내역 확인',
    mgD1: '로그인 후 방문예약 메뉴에서 내 예약 내역을 확인할 수 있어요.',
    mgC1: '예약 확인증은 방문 전에 저장해 두면 편해요.',
    mgE1: 'Check your reservation under the Visit Reservation menu.',
    mgT2: '예약 변경·취소',
    mgD2: '날짜를 바꾸려면 기존 예약을 취소하고 다시 예약하거나, 변경 메뉴가 있으면 그 안내를 따르세요.',
    mgC2: '방문이 어려우면 미리 취소해서 다른 사람이 예약할 수 있게 해주세요.',

    purposeGuideTitle: '예약 목적(민원 종류) 고르기',
    purposeGuideBody: '체류자격과 민원 유형에 따라 선택지가 달라질 수 있습니다. Paradiso의 체류자격별 안내와 하이코리아의 현재 선택지를 함께 확인하세요.',

    troubleIntro: '자주 막히는 상황과 안전한 해결 방법이에요. 해결되지 않으면 하이코리아 공식 안내나 1345를 이용하세요.',
    troubleCauseLabel: '왜 이런가요',
    troubleFixLabel: '이렇게 해보세요',
    t1t: '예약 가능한 날짜·시간이 보이지 않아요',
    t1c: '예약 가능한 자리가 이미 다 찼거나, 당일·임박한 날짜라 예약이 막혔을 수 있어요.',
    t1f: '다른 날짜를 먼저 확인하고, 며칠 뒤 날짜로 다시 시도해 보세요. 계속 안 되면 관할 출입국이나 1345에 문의하세요.',
    t2t: '본인인증이 되지 않아요',
    t2c: '이름·생년월일·등록번호가 여권이나 등록증과 다르게 입력됐을 수 있어요.',
    t2f: '문서에 적힌 그대로 다시 입력해 보세요. 그래도 안 되면 다른 인증 방법을 시도하거나 1345에 문의하세요.',
    t3t: '공동인증서·간편인증이 안 돼요',
    t3c: '인증서가 만료됐거나, 브라우저·앱에서 인증 프로그램이 제대로 동작하지 않을 수 있어요.',
    t3f: '인증서 유효기간을 확인하고, 다른 브라우저나 휴대폰 간편인증을 시도해 보세요. 인증 자체 문제는 해당 인증기관 안내를 따르세요.',
    t4t: '관할 출입국관서를 모르겠어요',
    t4c: '보통 현재 사는 곳(주소지)을 기준으로 관할 관서가 정해집니다.',
    t4f: '현재 주소를 기준으로 관할 관서를 확인하세요. 주소가 애매하면 1345에 문의하면 알려줍니다.',
    t5t: '어떤 민원 목적을 골라야 할지 모르겠어요',
    t5c: '같은 업무라도 체류자격과 상황에 따라 민원 이름이 다르게 보일 수 있어요.',
    t5f: 'Paradiso의 체류자격별 안내로 내 상황을 먼저 정리하고, 헷갈리면 1345나 관할 출입국에 정확한 민원 종류를 확인하세요.',
    t6t: '예약 완료 후 예약증을 저장하지 못했어요',
    t6c: '저장 버튼을 누르기 전에 화면을 닫았거나, 캡처를 못 했을 수 있어요.',
    t6f: '다시 로그인해 방문예약 내역에서 예약을 확인하고, 화면을 캡처하거나 예약번호를 메모해 두세요.',
    t7t: '모바일에서 화면이 잘려서 보여요',
    t7c: '작은 화면에서는 표나 달력이 가로로 넘칠 수 있어요.',
    t7f: '화면을 가로로 돌리거나, 확대·축소해서 보세요. 가능하면 PC에서 진행하면 더 편합니다.',
    t8t: '한국어 화면 때문에 막혀요 (외국어 사용자)',
    t8c: '언어를 바꿔도 일부 화면은 한국어로만 나올 수 있어요.',
    t8f: '이 안내의 화면 설명과 “영어로 보면” 메모를 참고하세요. 그래도 막히면 1345는 외국어 상담도 제공합니다.'
  };

  var STR_EN = {
    modalAria: 'HiKorea Visit Reservation Helper',
    headerTitle: 'HiKorea Reservation Helper',
    headerSub: 'From signing up to checking your reservation — a screen-by-screen HiKorea guide.',
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

    disclaimer: 'This helper organizes information before booking. Final availability and processing standards should be confirmed with HiKorea, 1345, or your immigration office.',

    /* ---- tabbed photo guide chrome (added 2026-06) ---- */
    tablistAria: 'HiKorea guide sections',
    tabOverview: 'Getting started',
    tabSignup: 'Sign up',
    tabLogin: 'Log in',
    tabReservation: 'Book a visit',
    tabManage: 'Check / change',
    tabTrouble: 'Troubleshooting',

    ovTitle: 'HiKorea Visit Reservation Guide',
    ovLead: 'New to HiKorea? Just follow these steps in order. From creating an account to checking your reservation, this guide walks you through each screen.',
    ovStart: 'Start the guide',
    ovScreensWarn: 'The real HiKorea screens can change at any time. If a button name or location differs from this guide, look for a similar menu or check the official HiKorea site.',
    quickTitle: 'What do you need help with?',
    qp1Title: 'I need to sign up first',
    qp1Sub: 'Start by creating a HiKorea account.',
    qp2Title: 'I already have an account',
    qp2Sub: 'Log in and book a visit reservation.',
    qp3Title: 'I just want to check a reservation',
    qp3Sub: 'View or change a reservation you already made.',
    qp4Title: 'Something went wrong',
    qp4Sub: 'See fixes for booking problems.',
    affiliation: 'Paradiso is not affiliated with HiKorea or the Ministry of Justice. The screen descriptions here are only a navigation aid; always confirm the final details on the official HiKorea website.',

    stepDoLabel: 'What to do here',
    stepCautionLabel: 'Watch out for',
    stepEnLabel: 'In English',
    stepNext: 'Next step',
    stepDone: 'Mark done',
    stepDoneOn: 'Done',
    progressDoneOf: 'steps done',
    shotPending: 'Screenshot coming soon',
    shotPendingSub: 'A real screen capture will be added here. Follow the text below for now.',
    guideProgressAria: 'Guide progress',
    prevTab: 'Back',
    nextTab: 'Next',
    openFinder: 'Find the right reservation purpose for me',
    openFinderSub: 'Answer a few questions about your status and situation to see which civil-service purpose to book.',
    backToPhotos: 'Back to the photo guide',
    enlarge: 'View larger',
    closeImage: 'Close',

    sgIntro: 'This is how to create a HiKorea account. Foreign residents usually sign up after identity verification.',
    sgT1: 'Choose a language and start sign-up',
    sgD1: 'On the HiKorea home screen, choose your language and tap Sign Up.',
    sgC1: 'Even in English, some screens may still appear in Korean.',
    sgE1: 'Pick your language, then tap Sign Up at the top.',
    sgT2: 'Agree to the terms',
    sgD2: 'Read the terms and the personal-data items, check the boxes, then continue.',
    sgC2: 'If you do not agree to the required items, sign-up will not continue.',
    sgT3: 'Verify your identity',
    sgD3: 'Verify with your alien registration number, passport details, or phone. Choose an available method from the options shown.',
    sgC3: 'Enter your name and date of birth exactly as on your passport or card, or verification will fail.',
    sgE3: 'Verify your identity with your ARC or passport details. Names must match your documents exactly.',
    sgT4: 'Enter your account details',
    sgD4: 'Enter your ID, password, and contact details, then finish signing up.',
    sgC4: 'Keep your password safe and remember the email and phone you used.',

    lgIntro: 'If you have an account, log in and go to the visit reservation menu.',
    lgT1: 'Open the login screen',
    lgD1: 'On the HiKorea home screen, tap Login and enter your ID and password.',
    lgC1: 'If you forgot your password, use the find ID / password option.',
    lgE1: 'Tap Login, then enter your ID and password.',
    lgT2: 'Check simple or non-member verification',
    lgD2: 'If member login is hard, check whether simple verification or non-member verification is available.',
    lgC2: 'You may need a certificate, so prepare it in advance.',

    resIntro: 'After logging in, this is how to book a visit. Follow the screens in order.',
    rsT1: 'Enter the visit reservation menu',
    rsD1: 'Go to Civil Petitions, then Visit Reservation, then Apply.',
    rsC1: 'Same-day reservations may not be possible. Booking is usually available from the next day.',
    rsE1: 'Go to Civil Petitions, then Visit Reservation, then Apply.',
    rsT2: 'Select the immigration office',
    rsD2: 'On this screen you choose the immigration office to visit. Usually pick the office for the area where you live.',
    rsC2: 'If you do not know your office, check by address or call 1345.',
    rsT3: 'Select the civil service (purpose)',
    rsD3: 'Choose the type of service, such as registration or extension of stay. Pick the task you want to do.',
    rsC3: 'The purpose names can look different depending on your status and situation.',
    rsE3: 'Choose your civil-service purpose (for example, registration or extension).',
    rsT4: 'Select a date and time',
    rsD4: 'Choose an available date and time on the calendar.',
    rsC4: 'If no times appear, check another date first.',
    rsT5: 'Review and save your reservation',
    rsD5: 'Check the office, date, and purpose, finish the reservation, and save or screenshot the confirmation.',
    rsC5: 'The reservation must be under the name of the person who will actually visit.',

    mngIntro: 'This is how to check, change, or cancel a reservation you already made.',
    mgT1: 'Check your reservation',
    mgD1: 'After logging in, view your reservations in the Visit Reservation menu.',
    mgC1: 'Save the confirmation before your visit so it is handy.',
    mgE1: 'Check your reservation under the Visit Reservation menu.',
    mgT2: 'Change or cancel',
    mgD2: 'To change the date, cancel and rebook, or follow the change menu if one is available.',
    mgC2: 'If you cannot make it, cancel early so someone else can book.',

    purposeGuideTitle: 'Choosing the reservation purpose',
    purposeGuideBody: 'The options can differ by status and civil-service type. Check Paradiso status guidance together with the current options on HiKorea.',

    troubleIntro: 'Common sticking points and safe fixes. If a problem is not solved, use the official HiKorea help or call 1345.',
    troubleCauseLabel: 'Why this happens',
    troubleFixLabel: 'Try this',
    t1t: 'No available dates or times appear',
    t1c: 'Slots may already be full, or booking is blocked because the date is today or too soon.',
    t1f: 'Check another date first and try again a few days out. If it keeps failing, contact your immigration office or 1345.',
    t2t: 'Identity verification fails',
    t2c: 'Your name, date of birth, or registration number may not match your documents.',
    t2f: 'Re-enter the details exactly as written on your documents. If it still fails, try another method or call 1345.',
    t3t: 'Joint certificate or simple verification fails',
    t3c: 'Your certificate may be expired, or the verification program may not run in your browser or app.',
    t3f: 'Check the certificate expiry, and try another browser or phone-based simple verification. For certificate issues, follow your certificate provider guidance.',
    t4t: 'I do not know my immigration office',
    t4c: 'Your office is usually decided by where you currently live (your address).',
    t4f: 'Check the office by your current address. If your address is unclear, 1345 can help you find it.',
    t5t: 'I do not know which purpose to choose',
    t5c: 'The same task can appear under different names depending on your status and situation.',
    t5f: 'Sort out your situation with Paradiso status guidance first, and if unsure, confirm the exact service type with 1345 or your immigration office.',
    t6t: 'I could not save the confirmation after booking',
    t6c: 'You may have closed the screen before saving, or missed the screenshot.',
    t6f: 'Log in again, find the booking in your reservation list, and screenshot it or note the reservation number.',
    t7t: 'The screen is cut off on mobile',
    t7c: 'On small screens, tables or calendars can overflow sideways.',
    t7f: 'Rotate your screen to landscape, or zoom in and out. If you can, a PC is more comfortable.',
    t8t: 'The Korean screens block me (for non-Korean speakers)',
    t8c: 'Even after changing the language, some screens may appear only in Korean.',
    t8f: 'Use the screen descriptions and the In English notes in this guide. If still stuck, 1345 offers foreign-language support.'
  };

  var STR_ZH = {
    modalAria: 'HiKorea 访问预约助手',
    headerTitle: 'HiKorea 预约助手',
    headerSub: '从 HiKorea 注册到确认访问预约，看着屏幕按顺序跟着做的指引。',
    notOfficialChip: '非官方服务',
    progressAria: '进行步骤',
    next: '下一步',
    back: '上一步',
    findPath: '查找预约路径',
    restart: '从头开始',
    close: '关闭',
    goHikorea: '前往 HiKorea',
    viewDocs: '查看所需材料清单',
    saveResult: '保存结果',
    saved: '已复制',
    saveFail: '复制失败，请自行保存屏幕。',
    hotline: '如果对预约或手续有疑问，请拨打外国人综合服务中心 1345 咨询。',
    call1345: '拨打 1345',

    q1: '您因为什么事去出入境？',
    q1Help: '不知道准确名称也没关系，请选择最接近的情况。',
    q2: '您有外国人登录证或居所证吗？',
    q2Help: '是否持有登录证，会影响预约目的。',
    q3: '您现在在韩国吗？',
    q3Help: 'HiKorea 访问预约通常用于在韩国境内前往出入境时。',
    q4: '您知道当前的居留资格吗？',
    q4Help: '例如 D-2、F-4、E-7 这样写在护照签证页或登录证上的代码。',
    q4Placeholder: '例：D-2, F-4, E-7',
    q4Skip: '不太清楚',
    q5: '您的居留期限到期日是什么时候？',
    q5Help: '延期申请须在到期日前办理。准确的可办理期间请在访问前再次确认。',
    q5Skip: '不太清楚',

    optYes: '有',
    optNo: '没有',
    optNotSure: '不太清楚',
    optInKorea: '我在韩国',
    optOverseas: '我还在海外',

    pRegistration: '外国人登录',
    pExtension: '居留期限延长',
    pChange: '居留资格变更',
    pActivity: '资格外活动许可',
    pWorkplace: '工作单位变更/追加',
    pAddress: '居留地变更',
    pReissue: '登录证补发',
    pUnsure: '不太清楚',
    pResidenceReport: '国内居所申报',
    pResidenceReissue: '居所证补发',
    pRegChange: '登录事项变更',
    pConsult: '其他居留相关咨询',
    pConsultF5: '居留资格相关咨询',

    resultLabel: '推荐预约目的',
    resultLead: '根据您输入的内容来看，在 HiKorea 以此项业务预约的可能性较高。',
    resultLeadLow: '目前尚难确定推荐项。请参考下方指引，并向 1345 或管辖出入境确认准确的预约目的。',
    confLabel: '推荐可信度',
    confHigh: '高',
    confMedium: '中',
    confLow: '低',

    secClick: '在 HiKorea 上要点击的',
    secBefore: '预约前要准备的',
    secAfter: '预约后要确认的',
    secBlocked: '预约不成功时',
    cautionsTitle: '务必记住的事',

    click1: '访问 HiKorea',
    click2: '选择民愿申请',
    click3: '选择访问预约',
    click4: '选择访问预约申请',
    click5: '会员登录或非会员认证',
    click6: '选择管辖出入境机关',
    click7: '选择访问目的',
    click8: '选择日期和时间',
    click9: '预约完成后保存受理证',

    bIdentity: '护照或身份证',
    bRealNameAcct: '以实际前往者本人名义的信息',
    bDocsReady: '提前确认申请所需材料',
    bAddressKnown: '确认当前居住地地址',
    bOfficeKnown: '确认要前往的管辖出入境',

    aSaveConfirm: '请保存或截图预约受理证（确认证）。',
    aCheckDateOffice: '请再次确认预约的日期和要前往的出入境办事处。',
    aVisitorName: '请确认预约是否以实际前往者的姓名办理。',
    aSameDayReminder: '当日预约可能无法办理，请提前确认预约日期。',

    wSameDay: '当日预约可能无法办理。访问预约通常从次日起才可预约。',
    wRealName: '预约须以实际前往者的姓名办理。',
    wOverseasNotice: 'HiKorea 访问预约通常用于在韩国境内前往出入境时。如果您还在海外，请入境后再确认。',
    wUnsureGuidance: '如果不知道该选哪项业务，请向 1345 或管辖出入境确认。',
    wExtensionWindow: '延期申请须在签证到期前办理。准确的可申请期间请在访问前再次确认。',
    wExpired: '您输入的到期日已过。逾期可能会有不利后果，请立即向 1345 或管辖出入境确认。',
    wImminent: '距到期日已所剩无几。请尽快预约并准备申请。',
    wRegisterFirst: '可能需要先办理外国人登录。如果没有登录证，请先确认登录手续。',
    wAlreadyRegistered: '如果已有登录证，可能无需再次办理外国人登录。请重新确认所需业务。',
    wF4ResidenceReport: 'F-4 多数情况下办理的是国内居所申报，而非外国人登录。',

    blkNoDatesT: '看不到日期',
    blkNoDatesB: '可预约的时间可能已约满。请确认其他日期，或向管辖出入境或 1345 咨询。',
    blkTodayT: '我想今天就去',
    blkTodayB: 'HiKorea 访问预约可能难以当日预约。请先确认可预约的日期。',
    blkOfficeT: '不知道该选哪个出入境',
    blkOfficeB: '通常以当前住址为准确定管辖出入境。如地址不明确，请向 1345 或管辖出入境咨询。',
    blkLoginT: '无法登录或认证',
    blkLoginB: '如果会员登录有困难，请确认是否可用非会员认证。若仍不行，请使用 HiKorea 指引或 1345。',
    blkPurposeT: '不知道该选哪项业务',
    blkPurposeB: '请保存 Paradiso 的推荐结果，并向 1345 或管辖出入境确认准确的预约目的。',

    statusSuggTitle: '此居留资格常用的预约目的',
    statusSuggCaution: '以下项目是此居留资格常见的预约目的。实际应选择哪项业务，会因您的具体情况而不同。',

    disclaimer: '本助手用于在预约前整理所需信息。实际能否申请及处理标准，请在 HiKorea、1345 或管辖出入境最终确认。',

    tablistAria: 'HiKorea 指引步骤',
    tabOverview: '初次使用',
    tabSignup: '注册',
    tabLogin: '登录',
    tabReservation: '预约访问',
    tabManage: '确认·变更预约',
    tabTrouble: '问题解决',

    ovTitle: 'HiKorea 访问预约助手',
    ovLead: '初次使用 HiKorea 的人也可以按此顺序跟着做。从注册到确认访问预约，看着屏幕一步步为您指引。',
    ovStart: '开始指引',
    ovScreensWarn: '实际的 HiKorea 界面可能随时变动。如果按钮名称或位置与指引不同，请查找类似菜单，或确认 HiKorea 官方指引。',
    quickTitle: '您需要哪方面的帮助？',
    qp1Title: '需要从注册开始',
    qp1Sub: '从创建 HiKorea 账户开始。',
    qp2Title: '我已有账户',
    qp2Sub: '登录后直接预约访问。',
    qp3Title: '只想确认预约',
    qp3Sub: '确认或变更已预约的内容。',
    qp4Title: '我遇到了问题',
    qp4Sub: '预约不成功或受阻时查看解决方法。',
    affiliation: 'Paradiso 不是与 HiKorea 或法务部有合作关系的服务。本指引的屏幕说明仅为引导参考，实际申请内容请在 HiKorea 官方网站最终确认。',

    stepDoLabel: '在这里要做的事',
    stepCautionLabel: '注意事项',
    stepEnLabel: '英文界面对照',
    stepNext: '下一步',
    stepDone: '勾选完成',
    stepDoneOn: '已完成',
    progressDoneOf: '步骤已完成',
    shotPending: '截图准备中',
    shotPendingSub: '实际屏幕截图即将添加。请先参考下方说明。',
    guideProgressAria: '指引进度',
    prevTab: '上一步',
    nextTab: '下一步',
    openFinder: '查找符合我情况的预约目的',
    openFinderSub: '只需选择几项居留资格和情况，即可为您整理出该以哪项民愿预约。',
    backToPhotos: '返回图片指引',
    enlarge: '放大查看',
    closeImage: '关闭',

    sgIntro: '这是创建 HiKorea 账户的过程。外国人通常需经过本人认证后注册。',
    sgT1: '选择语言并开始注册',
    sgD1: '在 HiKorea 首页选择语言，点击顶部或菜单中的“注册”。',
    sgC1: '即使把语言切换为英文，部分界面仍可能显示韩文。',
    sgE1: 'Pick your language, then tap “Sign Up / 회원가입” at the top.',
    sgT2: '同意条款',
    sgD2: '阅读使用条款和个人信息收集项目，勾选同意后进入下一步。',
    sgC2: '若不同意必选项目，将无法继续注册。',
    sgT3: '本人认证',
    sgD3: '用外国人登录号、护照信息或手机等进行本人认证。请在指引提供的认证方式中选择可用的一种。',
    sgC3: '姓名和出生日期须与护照·登录证完全一致才能认证成功。',
    sgE3: 'Verify your identity with your ARC or passport details. Names must match your documents exactly.',
    sgT4: '输入账号、密码等账户信息',
    sgD4: '输入账号、密码、联系方式等账户信息，完成注册。',
    sgC4: '请妥善保管密码，并记住注册时使用的邮箱·电话号码。',

    lgIntro: '如已有账户，登录后进入访问预约菜单。',
    lgT1: '打开登录界面',
    lgD1: '在 HiKorea 首页点击“登录”，输入账号和密码。',
    lgC1: '如忘记密码，请使用“查找账号·密码”。',
    lgE1: 'Tap “Login”, then enter your ID and password.',
    lgT2: '确认简易认证或非会员认证',
    lgD2: '如果会员登录有困难，请确认是否可用简易认证或非会员认证办理。',
    lgC2: '可能需要认证证书，提前准备会更方便。',

    resIntro: '登录之后，这是预约访问的过程。请按屏幕顺序跟着做。',
    rsT1: '进入访问预约菜单',
    rsD1: '按 民愿申请 → 访问预约 → 访问预约申请 的顺序进入。',
    rsC1: '当日预约可能较难。通常从次日起才可预约。',
    rsE1: 'Go to Civil Petitions → Visit Reservation → Apply.',
    rsT2: '选择要前往的出入境机关',
    rsD2: '在此界面选择要前往的出入境机关。通常选择管辖当前居住地的机关。',
    rsC2: '如不知道管辖机关，可按地址确认或向 1345 咨询。',
    rsT3: '选择民愿（预约目的）',
    rsD3: '选择外国人登录、居留期限延长等民愿种类。请选择您要办理的业务。',
    rsC3: '民愿种类的名称可能因居留资格和情况而显示不同。',
    rsE3: 'Choose your civil-service purpose (for example, registration or extension).',
    rsT4: '选择日期和时间',
    rsD4: '在日历中选择可预约的日期和时间。',
    rsC4: '如果看不到可预约的时间，请先确认其他日期。',
    rsT5: '确认预约内容并保存',
    rsD5: '确认所选的机关·日期·民愿后完成预约，并保存或截图预约确认证。',
    rsC5: '预约须以实际前往者的姓名办理。',

    mngIntro: '这是确认、变更或取消已预约内容的方法。',
    mgT1: '确认预约记录',
    mgD1: '登录后，可在访问预约菜单中确认我的预约记录。',
    mgC1: '预约确认证在访问前保存好会更方便。',
    mgE1: 'Check your reservation under the Visit Reservation menu.',
    mgT2: '变更·取消预约',
    mgD2: '如需更改日期，请取消现有预约后重新预约；若有变更菜单，则按其指引操作。',
    mgC2: '如难以前往，请提前取消，以便他人预约。',

    purposeGuideTitle: '选择预约目的（民愿种类）',
    purposeGuideBody: '选项可能因居留资格和民愿类型而不同。请将 Paradiso 的各居留资格指引与 HiKorea 当前的选项一并确认。',

    troubleIntro: '这是常见受阻情况和安全的解决方法。如仍无法解决，请使用 HiKorea 官方指引或 1345。',
    troubleCauseLabel: '为什么会这样',
    troubleFixLabel: '请试试这样做',
    t1t: '看不到可预约的日期·时间',
    t1c: '可预约名额可能已满，或因当日·临近日期而无法预约。',
    t1f: '请先确认其他日期，并以几天后的日期重试。若仍不行，请向管辖出入境或 1345 咨询。',
    t2t: '本人认证不通过',
    t2c: '姓名·出生日期·登录号可能与护照或登录证输入得不一致。',
    t2f: '请按文件上的内容原样重新输入。若仍不行，请尝试其他认证方式或向 1345 咨询。',
    t3t: '共同认证证书·简易认证不可用',
    t3c: '认证证书可能已过期，或浏览器·应用中的认证程序未正常运行。',
    t3f: '请确认证书有效期，并尝试其他浏览器或手机简易认证。认证本身的问题请遵循相应认证机构的指引。',
    t4t: '不知道管辖出入境机关',
    t4c: '通常以当前居住地（地址）为准确定管辖机关。',
    t4f: '请以当前地址确认管辖机关。如地址不明确，向 1345 咨询即可获知。',
    t5t: '不知道该选哪个民愿目的',
    t5c: '即使是同一业务，民愿名称也可能因居留资格和情况而显示不同。',
    t5f: '请先用 Paradiso 的各居留资格指引理清您的情况，如有疑惑，向 1345 或管辖出入境确认准确的民愿种类。',
    t6t: '预约完成后未能保存预约证',
    t6c: '可能在点击保存按钮前关闭了界面，或未能截图。',
    t6f: '请重新登录，在访问预约记录中确认预约，并截图或记下预约号。',
    t7t: '在手机上界面显示被截断',
    t7c: '在小屏幕上，表格或日历可能横向溢出。',
    t7f: '请将屏幕横置，或放大·缩小查看。如可能，用电脑办理会更方便。',
    t8t: '因韩文界面受阻（外语使用者）',
    t8c: '即使切换语言，部分界面仍可能仅显示韩文。',
    t8f: '请参考本指引的屏幕说明和“英文界面对照”备注。若仍受阻，1345 也提供外语咨询。'
  };
  // Only KO / EN / 'zh-CN' have dedicated packs in this module. The locales below
  // are fully translated elsewhere in the site but not (yet) here, so they fall
  // back to the English pack rather than to undefined STR_* identifiers — the
  // latter threw a ReferenceError while building this literal, which aborted the
  // whole IIFE and left window.ParadisoReservationHelper unassigned (the modal
  // opened but rendered nothing). English is the safer universal fallback for
  // non-Korean speakers than the per-key STR_KO fallback in the Proxy below.
  var STR_PACKS = {
    ko: STR_KO, en: STR_EN, 'zh-CN': STR_ZH,
    ja: STR_EN, vi: STR_EN, tl: STR_EN, id: STR_EN, ru: STR_EN,
    fr: STR_EN, es: STR_EN, ar: STR_EN, de: STR_EN, tr: STR_EN, uk: STR_EN
  };
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

  /* --------------------------------------------------- screenshot manifest */
  // Where sanitized screenshots live. See assets/hikorea-guide/README.md for the
  // naming convention + privacy-masking process. Each entry has available:false
  // until a real, sanitized capture is dropped in (flip to true — that is the
  // ONLY edit needed). While unavailable an accessible placeholder renders, so
  // there is never a broken image path or a 404.
  var SHOT_DIR = 'assets/hikorea-guide/';
  var GUIDE_STEPS = {
    signup: [
      { id: 'sg1', file: 'hikorea-signup-01-language.png', available: false, titleKey: 'sgT1', doKey: 'sgD1', cautionKey: 'sgC1', enKey: 'sgE1' },
      { id: 'sg2', file: 'hikorea-signup-02-terms.png', available: false, titleKey: 'sgT2', doKey: 'sgD2', cautionKey: 'sgC2' },
      { id: 'sg3', file: 'hikorea-signup-03-identity-verification.png', available: false, titleKey: 'sgT3', doKey: 'sgD3', cautionKey: 'sgC3', enKey: 'sgE3' },
      { id: 'sg4', file: 'hikorea-signup-04-account-info.png', available: false, titleKey: 'sgT4', doKey: 'sgD4', cautionKey: 'sgC4' }
    ],
    login: [
      { id: 'lg1', file: 'hikorea-login-01-login-page.png', available: false, titleKey: 'lgT1', doKey: 'lgD1', cautionKey: 'lgC1', enKey: 'lgE1' },
      { id: 'lg2', file: 'hikorea-login-02-verification.png', available: false, titleKey: 'lgT2', doKey: 'lgD2', cautionKey: 'lgC2' }
    ],
    reservation: [
      { id: 'rs1', file: 'hikorea-reservation-01-entry.png', available: false, titleKey: 'rsT1', doKey: 'rsD1', cautionKey: 'rsC1', enKey: 'rsE1' },
      { id: 'rs2', file: 'hikorea-reservation-02-office-select.png', available: false, titleKey: 'rsT2', doKey: 'rsD2', cautionKey: 'rsC2' },
      { id: 'rs3', file: 'hikorea-reservation-03-purpose-select.png', available: false, titleKey: 'rsT3', doKey: 'rsD3', cautionKey: 'rsC3', enKey: 'rsE3' },
      { id: 'rs4', file: 'hikorea-reservation-04-date-time.png', available: false, titleKey: 'rsT4', doKey: 'rsD4', cautionKey: 'rsC4' },
      { id: 'rs5', file: 'hikorea-reservation-05-confirmation.png', available: false, titleKey: 'rsT5', doKey: 'rsD5', cautionKey: 'rsC5' }
    ],
    manage: [
      { id: 'mg1', file: 'hikorea-reservation-06-reservation-check.png', available: false, titleKey: 'mgT1', doKey: 'mgD1', cautionKey: 'mgC1', enKey: 'mgE1' },
      { id: 'mg2', file: 'hikorea-reservation-07-change-cancel.png', available: false, titleKey: 'mgT2', doKey: 'mgD2', cautionKey: 'mgC2' }
    ]
  };

  var TROUBLE_ITEMS = [
    { id: 't1', titleKey: 't1t', causeKey: 't1c', fixKey: 't1f' },
    { id: 't2', titleKey: 't2t', causeKey: 't2c', fixKey: 't2f' },
    { id: 't3', titleKey: 't3t', causeKey: 't3c', fixKey: 't3f' },
    { id: 't4', titleKey: 't4t', causeKey: 't4c', fixKey: 't4f' },
    { id: 't5', titleKey: 't5t', causeKey: 't5c', fixKey: 't5f' },
    { id: 't6', titleKey: 't6t', causeKey: 't6c', fixKey: 't6f' },
    { id: 't7', titleKey: 't7t', causeKey: 't7c', fixKey: 't7f' },
    { id: 't8', titleKey: 't8t', causeKey: 't8c', fixKey: 't8f' }
  ];

  // Tab order drives both the tablist and the prev/next tab navigation.
  var TAB_ORDER = ['overview', 'signup', 'login', 'reservation', 'manage', 'trouble'];
  var TAB_LABEL_KEY = {
    overview: 'tabOverview', signup: 'tabSignup', login: 'tabLogin',
    reservation: 'tabReservation', manage: 'tabManage', trouble: 'tabTrouble'
  };
  var GUIDE_INTRO_KEY = { signup: 'sgIntro', login: 'lgIntro', reservation: 'resIntro', manage: 'mngIntro' };

  /* --------------------------------------------------------------- styles */
  var STYLE_ID = 'prh-styles';
  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      // Spacious, mobile-first panel (avoid the tiny-modal feel). Override the
      // shell's 760px cap from here so index.html stays untouched.
      '#hikoreaGuideOverlay .hikorea-modal{width:min(96vw,1040px);max-width:1040px;max-height:92vh;}',
      '@media (max-width:680px){#hikoreaGuideOverlay .hikorea-modal{width:100vw;max-width:100vw;height:100dvh;max-height:100dvh;border-radius:0;}}',
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

      /* ---- tabbed photo guide ---- */
      '#hikoreaGuideBody .prh-tabs{position:sticky;top:0;z-index:4;display:flex;gap:.35rem;flex-wrap:wrap;background:var(--bg1);padding:.15rem 0 .55rem;margin:-.25rem 0 0;border-bottom:1px solid var(--bd2);}',
      '#hikoreaGuideBody .prh-tab{appearance:none;border:1.5px solid var(--bd2);background:var(--bg0);color:var(--t2);font-family:inherit;font-size:.82rem;font-weight:800;padding:.5rem .8rem;border-radius:999px;cursor:pointer;min-height:40px;white-space:nowrap;transition:border-color .15s,color .15s,background .15s;}',
      '#hikoreaGuideBody .prh-tab:hover{border-color:var(--ac);color:var(--ac);}',
      '#hikoreaGuideBody .prh-tab:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-tab.is-active{background:color-mix(in srgb,var(--ac) 14%,var(--bg1));border-color:var(--ac);color:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-hero{border:1.5px solid var(--ac);border-radius:var(--radius-lg,14px);background:color-mix(in srgb,var(--ac) 7%,var(--bg1));padding:1.1rem 1.15rem;display:flex;flex-direction:column;gap:.6rem;}',
      '#hikoreaGuideBody .prh-hero-kicker{align-self:flex-start;font-size:.7rem;font-weight:800;letter-spacing:.02em;padding:.2rem .55rem;border-radius:999px;border:1px solid color-mix(in srgb,var(--ac) 32%,transparent);color:var(--ac2,var(--ac));background:var(--bg1);}',
      '#hikoreaGuideBody .prh-hero-title{font-size:1.5rem;font-weight:900;line-height:1.25;margin:0;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-hero-lead{font-size:.94rem;line-height:1.6;color:var(--t2);margin:0;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-hero-actions{display:flex;flex-wrap:wrap;gap:.5rem;}',
      '#hikoreaGuideBody .prh-hero-actions .prh-primary{margin-left:0;}',
      '#hikoreaGuideBody .prh-hero-warn{font-size:.8rem;line-height:1.55;color:var(--t2);margin:0;padding:.6rem .7rem;border-radius:var(--radius-md,10px);background:color-mix(in srgb,var(--color-warning,#b88600) 10%,var(--bg1));border:1px solid color-mix(in srgb,var(--color-warning,#b88600) 32%,transparent);}',
      '#hikoreaGuideBody .prh-section-h{font-size:1.02rem;font-weight:800;margin:.2rem 0 0;}',
      '#hikoreaGuideBody .prh-quick{display:grid;gap:.6rem;grid-template-columns:1fr;}',
      '@media (min-width:560px){#hikoreaGuideBody .prh-quick{grid-template-columns:1fr 1fr;}}',
      '#hikoreaGuideBody .prh-qp{display:flex;flex-direction:column;gap:.25rem;text-align:left;width:100%;padding:.9rem 1rem;border:1.5px solid var(--bd);border-radius:var(--radius-md,10px);background:var(--bg1);color:var(--t1);font-family:inherit;cursor:pointer;min-height:72px;transition:border-color .15s,transform .15s,box-shadow .15s;}',
      '#hikoreaGuideBody .prh-qp:hover{border-color:var(--ac);transform:translateY(-1px);box-shadow:0 2px 10px color-mix(in srgb,var(--ac) 14%,transparent);}',
      '#hikoreaGuideBody .prh-qp:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-qp strong{font-size:.98rem;font-weight:800;line-height:1.3;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-qp small{font-size:.8rem;color:var(--t3);line-height:1.45;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-affiliation{font-size:.78rem;line-height:1.6;color:var(--t2);background:var(--bg0);border:1px solid var(--bd2);border-left:3px solid color-mix(in srgb,var(--ac) 55%,var(--bd2));border-radius:var(--radius-md,10px);padding:.75rem .85rem;margin:0;}',
      '#hikoreaGuideBody .prh-guide-head{display:flex;flex-direction:column;gap:.55rem;}',
      '#hikoreaGuideBody .prh-guide-intro{font-size:.92rem;line-height:1.6;color:var(--t2);margin:0;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-steps{display:flex;flex-direction:column;gap:.85rem;}',
      '#hikoreaGuideBody .prh-step{border:1px solid var(--bd2);border-radius:var(--radius-lg,14px);background:var(--bg1);padding:.95rem 1rem;display:flex;flex-direction:column;gap:.6rem;scroll-margin-top:64px;}',
      '#hikoreaGuideBody .prh-step.is-done{border-color:var(--ac);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--ac) 35%,transparent);}',
      '#hikoreaGuideBody .prh-step-head{display:flex;align-items:center;gap:.6rem;}',
      '#hikoreaGuideBody .prh-step-num{flex:none;width:1.85rem;height:1.85rem;border-radius:999px;background:var(--ac);color:#fff;font-weight:900;font-size:.92rem;display:flex;align-items:center;justify-content:center;}',
      '#hikoreaGuideBody .prh-step.is-done .prh-step-num{background:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-step-title{font-size:1.04rem;font-weight:800;line-height:1.35;margin:0;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-shot{margin:0;border:1px solid var(--bd2);border-radius:var(--radius-md,10px);overflow:hidden;background:var(--bg0);}',
      '#hikoreaGuideBody .prh-shot-img{display:block;width:100%;height:auto;cursor:zoom-in;}',
      '#hikoreaGuideBody .prh-shot-ph{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.35rem;min-height:170px;padding:1.2rem 1rem;text-align:center;border:2px dashed var(--bd3);border-radius:var(--radius-md,10px);background:repeating-linear-gradient(45deg,var(--bg0),var(--bg0) 10px,var(--bg2) 10px,var(--bg2) 20px);}',
      '#hikoreaGuideBody .prh-shot-ph-icon{font-size:1.7rem;line-height:1;}',
      '#hikoreaGuideBody .prh-shot-ph-title{font-size:.86rem;font-weight:800;color:var(--t2);}',
      '#hikoreaGuideBody .prh-shot-ph-sub{font-size:.76rem;color:var(--t3);line-height:1.5;max-width:34ch;}',
      '#hikoreaGuideBody .prh-shot-ph-file{font-size:.7rem;color:var(--t3);background:var(--bg1);border:1px solid var(--bd2);border-radius:6px;padding:.15rem .4rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}',
      '#hikoreaGuideBody .prh-step-block{display:flex;flex-direction:column;gap:.2rem;}',
      '#hikoreaGuideBody .prh-step-label{font-size:.74rem;font-weight:800;letter-spacing:.01em;text-transform:uppercase;color:var(--t3);}',
      '#hikoreaGuideBody .prh-step-do p,#hikoreaGuideBody .prh-step-caution p{margin:0;font-size:.9rem;line-height:1.6;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-step-caution{border-left:3px solid var(--color-warning,#b88600);padding:.1rem 0 .1rem .7rem;}',
      '#hikoreaGuideBody .prh-step-caution .prh-step-label{color:var(--color-warning,#b88600);}',
      '#hikoreaGuideBody .prh-step-en{border:1px dashed var(--bd2);border-radius:var(--radius-md,10px);padding:.1rem .2rem;}',
      '#hikoreaGuideBody .prh-step-en summary{cursor:pointer;font-size:.82rem;font-weight:700;color:var(--t2);padding:.5rem .6rem;list-style:none;}',
      '#hikoreaGuideBody .prh-step-en summary::-webkit-details-marker{display:none;}',
      '#hikoreaGuideBody .prh-step-en summary::before{content:"EN  ";font-weight:900;color:var(--ac);}',
      '#hikoreaGuideBody .prh-step-en p{margin:0;font-size:.86rem;line-height:1.55;color:var(--t2);padding:0 .6rem .6rem;}',
      '#hikoreaGuideBody .prh-step-foot{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-top:.1rem;}',
      '#hikoreaGuideBody .prh-check{display:inline-flex;align-items:center;gap:.45rem;min-height:42px;padding:.5rem .85rem;border:1.5px solid var(--bd);border-radius:999px;background:var(--bg1);color:var(--t2);font-family:inherit;font-weight:800;font-size:.82rem;cursor:pointer;}',
      '#hikoreaGuideBody .prh-check:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-check.is-on{border-color:var(--ac);background:color-mix(in srgb,var(--ac) 14%,var(--bg1));color:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-check-box{width:1.05rem;height:1.05rem;border-radius:5px;border:1.5px solid currentColor;display:inline-flex;align-items:center;justify-content:center;font-size:.72rem;}',
      '#hikoreaGuideBody .prh-step-next{margin-left:auto;appearance:none;border:1.5px solid var(--bd);background:var(--bg1);color:var(--t1);font-family:inherit;font-weight:800;font-size:.82rem;min-height:42px;padding:.5rem .85rem;border-radius:999px;cursor:pointer;}',
      '#hikoreaGuideBody .prh-step-next:hover{border-color:var(--ac);color:var(--ac);}',
      '#hikoreaGuideBody .prh-step-next:focus-visible{outline:3px solid color-mix(in srgb,var(--ac) 45%,transparent);outline-offset:2px;}',
      '#hikoreaGuideBody .prh-finder{display:flex;flex-direction:column;gap:.45rem;border:1.5px solid var(--ac);border-radius:var(--radius-lg,14px);background:color-mix(in srgb,var(--ac) 6%,var(--bg1));padding:.95rem 1rem;}',
      '#hikoreaGuideBody .prh-finder-title{font-size:1rem;font-weight:800;margin:0;}',
      '#hikoreaGuideBody .prh-finder-sub{font-size:.84rem;line-height:1.55;color:var(--t2);margin:0;}',
      '#hikoreaGuideBody .prh-finder button{align-self:flex-start;}',
      '#hikoreaGuideBody .prh-tabnav{display:flex;gap:.6rem;align-items:center;justify-content:space-between;margin-top:.2rem;}',
      '#hikoreaGuideBody .prh-tabnav .prh-spacer{flex:1;}',
      '#hikoreaGuideBody .prh-tx details{border:1px solid var(--bd2);border-radius:var(--radius-md,10px);background:var(--bg1);margin-bottom:.5rem;overflow:hidden;}',
      '#hikoreaGuideBody .prh-tx summary{cursor:pointer;font-size:.92rem;font-weight:800;padding:.8rem .9rem;list-style:none;display:flex;align-items:center;gap:.5rem;word-break:keep-all;}',
      '#hikoreaGuideBody .prh-tx summary::-webkit-details-marker{display:none;}',
      '#hikoreaGuideBody .prh-tx summary::after{content:"+";margin-left:auto;font-weight:900;color:var(--t3);}',
      '#hikoreaGuideBody .prh-tx details[open] summary::after{content:"–";}',
      '#hikoreaGuideBody .prh-tx-body{padding:0 .9rem .85rem;display:flex;flex-direction:column;gap:.5rem;}',
      '#hikoreaGuideBody .prh-tx-block{display:flex;flex-direction:column;gap:.15rem;}',
      '#hikoreaGuideBody .prh-tx-block p{margin:0;font-size:.86rem;line-height:1.6;color:var(--t2);word-break:keep-all;}',
      '#hikoreaGuideBody .prh-tx-block .prh-step-label{color:var(--t3);}',
      '#hikoreaGuideBody .prh-tx-block.is-fix .prh-step-label{color:var(--ac2,var(--ac));}',
      '#hikoreaGuideBody .prh-lightbox{position:fixed;inset:0;z-index:50;display:flex;align-items:center;justify-content:center;padding:1.2rem;background:rgba(0,0,0,.78);}',
      '#hikoreaGuideBody .prh-lightbox img{max-width:96vw;max-height:84vh;border-radius:8px;box-shadow:0 8px 40px rgba(0,0,0,.5);}',
      '#hikoreaGuideBody .prh-lightbox-close{position:absolute;top:1rem;right:1rem;min-height:44px;padding:.55rem 1rem;border-radius:999px;border:1.5px solid #fff;background:rgba(0,0,0,.5);color:#fff;font-family:inherit;font-weight:800;cursor:pointer;}',
      // Mobile sticky action bar keeps the primary control reachable.
      '@media (max-width:560px){#hikoreaGuideBody .prh-nav{position:sticky;bottom:0;background:var(--bg0);padding:.6rem 0 .2rem;border-top:1px solid var(--bd2);z-index:2;}#hikoreaGuideBody .prh-ctas .prh-cta{flex:1 1 100%;}#hikoreaGuideBody .prh-tabs{gap:.3rem;overflow-x:auto;flex-wrap:nowrap;-webkit-overflow-scrolling:touch;}#hikoreaGuideBody .prh-tab{flex:0 0 auto;}}'
    ].join('\n');
    var el = document.createElement('style');
    el.id = STYLE_ID;
    el.textContent = css;
    document.head.appendChild(el);
  }

  /* ----------------------------------------------------------------- state */
  var DONE_KEY = 'paradiso_hikorea_steps_done';
  var state = {
    visaCode: '',
    purpose: '',
    card: '',
    loc: '',
    code: '',
    expiry: '',
    step: 1,
    tab: 'overview',
    view: 'guide',     // reservation tab sub-view: 'guide' | 'wizard' | 'result'
    done: {},
    zoom: ''
  };

  function loadDone() {
    try {
      var raw = window.localStorage && window.localStorage.getItem(DONE_KEY);
      state.done = raw ? (JSON.parse(raw) || {}) : {};
    } catch (e) { state.done = {}; }
  }
  function persistDone() {
    try { if (window.localStorage) window.localStorage.setItem(DONE_KEY, JSON.stringify(state.done)); } catch (e) { /* noop */ }
  }

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
      : '<button type="button" class="prh-btn" data-prh-action="back-to-photos">' + esc(STR.backToPhotos) + '</button>';
    var nextLabel = opts.last ? STR.findPath : STR.next;
    var nextDisabled = opts.nextDisabled ? ' disabled' : '';
    var next = '<button type="button" class="prh-btn prh-primary" data-prh-action="next"' + nextDisabled + '>' + esc(nextLabel) + '</button>';
    return '<div class="prh-nav">' + back + next + '</div>';
  }

  function hotlineHtml() {
    return '<div class="prh-strip">' + esc(STR.hotline) + ' <a href="tel:1345">' + esc(STR.call1345) + '</a></div>';
  }

  function disclaimerHtml() {
    return '<p class="prh-disclaimer">' + esc(STR.disclaimer) + '</p>';
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

  /* ----------------------------------------------------------- tab chrome */
  function tabBarHtml() {
    return '<div class="prh-tabs" role="tablist" aria-label="' + esc(STR.tablistAria) + '">' +
      TAB_ORDER.map(function (id) {
        var sel = state.tab === id;
        return '<button type="button" role="tab" id="prhtab-' + id + '" aria-selected="' + (sel ? 'true' : 'false') +
          '" tabindex="' + (sel ? '0' : '-1') + '" class="prh-tab' + (sel ? ' is-active' : '') +
          '" data-prh-action="go-tab" data-prh-tab="' + id + '">' + esc(STR[TAB_LABEL_KEY[id]]) + '</button>';
      }).join('') + '</div>';
  }

  function tabNavHtml(tabId) {
    var idx = TAB_ORDER.indexOf(tabId);
    var prev = idx > 0 ? TAB_ORDER[idx - 1] : null;
    var next = idx < TAB_ORDER.length - 1 ? TAB_ORDER[idx + 1] : null;
    var html = '<div class="prh-tabnav">';
    html += prev
      ? '<button type="button" class="prh-btn" data-prh-action="go-tab" data-prh-tab="' + prev + '">‹ ' + esc(STR.prevTab) + '</button>'
      : '<span class="prh-spacer"></span>';
    html += next
      ? '<button type="button" class="prh-btn prh-primary" data-prh-action="go-tab" data-prh-tab="' + next + '">' + esc(STR.nextTab) + ' ›</button>'
      : '<span class="prh-spacer"></span>';
    html += '</div>';
    return html;
  }

  /* ------------------------------------------------------ overview (tab 1) */
  function quickCard(tab, titleKey, subKey) {
    return '<button type="button" class="prh-qp" data-prh-action="go-tab" data-prh-tab="' + tab + '">' +
      '<strong>' + esc(STR[titleKey]) + '</strong><small>' + esc(STR[subKey]) + '</small></button>';
  }

  function overviewHtml() {
    var html = '<section class="prh-hero">' +
      '<span class="prh-hero-kicker">' + esc(STR.notOfficialChip) + '</span>' +
      '<h3 class="prh-hero-title">' + esc(STR.ovTitle) + '</h3>' +
      '<p class="prh-hero-lead">' + esc(STR.ovLead) + '</p>' +
      '<div class="prh-hero-actions"><button type="button" class="prh-btn prh-primary" data-prh-action="go-tab" data-prh-tab="signup">' + esc(STR.ovStart) + '</button>' +
      '<a class="prh-cta" href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">' + esc(STR.goHikorea) + '</a></div>' +
      '<p class="prh-hero-warn">' + esc(STR.ovScreensWarn) + '</p>' +
      '</section>';
    html += '<h4 class="prh-section-h">' + esc(STR.quickTitle) + '</h4>';
    html += '<div class="prh-quick">' +
      quickCard('signup', 'qp1Title', 'qp1Sub') +
      quickCard('reservation', 'qp2Title', 'qp2Sub') +
      quickCard('manage', 'qp3Title', 'qp3Sub') +
      quickCard('trouble', 'qp4Title', 'qp4Sub') +
      '</div>';
    html += '<p class="prh-affiliation">' + esc(STR.affiliation) + '</p>';
    html += hotlineHtml();
    html += disclaimerHtml();
    return html;
  }

  /* -------------------------------------------------- photo step guide tab */
  function shotFigureHtml(shot) {
    var alt = STR[shot.titleKey];
    if (shot.available) {
      return '<figure class="prh-shot"><img class="prh-shot-img" loading="lazy" decoding="async" src="' +
        esc(SHOT_DIR + shot.file) + '" alt="' + esc(alt) + '" data-prh-action="zoom" data-prh-src="' + esc(SHOT_DIR + shot.file) +
        '"></figure>';
    }
    // Accessible placeholder — no <img>, so no network request / no broken path.
    // The full instruction is still conveyed by the do/caution text below.
    return '<figure class="prh-shot"><div class="prh-shot-ph" role="img" aria-label="' +
      esc(alt + ' — ' + STR.shotPending) + '">' +
      '<span class="prh-shot-ph-icon" aria-hidden="true">🖼️</span>' +
      '<span class="prh-shot-ph-title">' + esc(STR.shotPending) + '</span>' +
      '<span class="prh-shot-ph-sub">' + esc(STR.shotPendingSub) + '</span>' +
      '<code class="prh-shot-ph-file">' + esc(shot.file) + '</code>' +
      '</div></figure>';
  }

  function stepCardHtml(shot, idx, total, nextShot) {
    var done = !!state.done[shot.id];
    var n = idx + 1;
    var html = '<article class="prh-step' + (done ? ' is-done' : '') + '" id="prhstep-' + esc(shot.id) + '">';
    html += '<div class="prh-step-head"><span class="prh-step-num">' + n + '</span>' +
      '<h4 class="prh-step-title">' + esc(STR[shot.titleKey]) + '</h4></div>';
    html += shotFigureHtml(shot);
    html += '<div class="prh-step-block prh-step-do"><span class="prh-step-label">' + esc(STR.stepDoLabel) +
      '</span><p>' + esc(STR[shot.doKey]) + '</p></div>';
    if (shot.cautionKey) {
      html += '<div class="prh-step-block prh-step-caution"><span class="prh-step-label">' + esc(STR.stepCautionLabel) +
        '</span><p>' + esc(STR[shot.cautionKey]) + '</p></div>';
    }
    if (shot.enKey) {
      html += '<details class="prh-step-en"><summary>' + esc(STR.stepEnLabel) + '</summary><p>' + esc(STR[shot.enKey]) + '</p></details>';
    }
    html += '<div class="prh-step-foot">';
    html += '<button type="button" class="prh-check' + (done ? ' is-on' : '') + '" data-prh-action="toggle-done" data-prh-step="' +
      esc(shot.id) + '" aria-pressed="' + (done ? 'true' : 'false') + '"><span class="prh-check-box" aria-hidden="true">' +
      (done ? '✓' : '') + '</span>' + esc(done ? STR.stepDoneOn : STR.stepDone) + '</button>';
    if (nextShot) {
      html += '<button type="button" class="prh-step-next" data-prh-action="goto-step" data-prh-target="prhstep-' +
        esc(nextShot.id) + '">' + esc(STR.stepNext) + ' ↓</button>';
    }
    html += '</div></article>';
    return html;
  }

  function guideProgressHtml(steps) {
    var total = steps.length;
    var doneCount = steps.filter(function (s) { return state.done[s.id]; }).length;
    var pct = total ? Math.round((doneCount / total) * 100) : 0;
    return '<div class="prh-progress" role="progressbar" aria-label="' + esc(STR.guideProgressAria) +
      '" aria-valuemin="0" aria-valuemax="' + total + '" aria-valuenow="' + doneCount + '">' +
      '<div class="prh-progress-track"><div class="prh-progress-fill" style="width:' + pct + '%"></div></div>' +
      '<span class="prh-progress-label">' + doneCount + ' / ' + total + ' ' + esc(STR.progressDoneOf) + '</span></div>';
  }

  function guideTabHtml(tabId) {
    var steps = GUIDE_STEPS[tabId] || [];
    var html = '<div class="prh-guide-head">';
    if (GUIDE_INTRO_KEY[tabId]) html += '<p class="prh-guide-intro">' + esc(STR[GUIDE_INTRO_KEY[tabId]]) + '</p>';
    html += guideProgressHtml(steps);
    html += '</div>';

    if (tabId === 'reservation') {
      html += '<div class="prh-finder">' +
        '<p class="prh-finder-title">' + esc(STR.openFinder) + '</p>' +
        '<p class="prh-finder-sub">' + esc(STR.openFinderSub) + '</p>' +
        '<button type="button" class="prh-btn prh-primary" data-prh-action="start-finder">' + esc(STR.findPath) + '</button>' +
        '</div>';
    }

    html += '<div class="prh-steps">' + steps.map(function (s, i) {
      return stepCardHtml(s, i, steps.length, steps[i + 1]);
    }).join('') + '</div>';

    if (tabId === 'reservation') {
      html += '<div class="prh-sugg"><p class="prh-sugg-title">' + esc(STR.purposeGuideTitle) + '</p>' +
        '<p class="prh-sugg-caution">' + esc(STR.purposeGuideBody) + '</p></div>';
    }

    html += tabNavHtml(tabId);
    html += hotlineHtml();
    html += disclaimerHtml();
    return html;
  }

  /* --------------------------------------------------- troubleshooting tab */
  function troubleHtml() {
    var html = '<p class="prh-guide-intro">' + esc(STR.troubleIntro) + '</p>';
    html += '<div class="prh-tx">' + TROUBLE_ITEMS.map(function (t) {
      return '<details><summary>' + esc(STR[t.titleKey]) + '</summary><div class="prh-tx-body">' +
        '<div class="prh-tx-block"><span class="prh-step-label">' + esc(STR.troubleCauseLabel) + '</span><p>' + esc(STR[t.causeKey]) + '</p></div>' +
        '<div class="prh-tx-block is-fix"><span class="prh-step-label">' + esc(STR.troubleFixLabel) + '</span><p>' + esc(STR[t.fixKey]) + '</p></div>' +
        '</div></details>';
    }).join('') + '</div>';
    html += tabNavHtml('trouble');
    html += hotlineHtml();
    html += disclaimerHtml();
    return html;
  }

  /* ----------------------------------------------- reservation purpose wizard */
  // The interactive one-question-per-step finder (preserved). Returns HTML.
  function wizardStepHtml() {
    var html = '<div class="prh-nav" style="margin-top:0"><button type="button" class="prh-btn" data-prh-action="back-to-photos">‹ ' + esc(STR.backToPhotos) + '</button></div>';
    html += progressHtml();

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
    html += disclaimerHtml();
    return html;
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

  function wizardResultHtml() {
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

    var html = '<div class="prh-nav" style="margin-top:0"><button type="button" class="prh-btn" data-prh-action="back-to-photos">‹ ' + esc(STR.backToPhotos) + '</button></div>';

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
    html += disclaimerHtml();
    return html;
  }

  /* ---------------------------------------------------------- lightbox */
  function lightboxHtml() {
    if (!state.zoom) return '';
    return '<div class="prh-lightbox" data-prh-action="close-zoom">' +
      '<button type="button" class="prh-lightbox-close" data-prh-action="close-zoom">' + esc(STR.closeImage) + '</button>' +
      '<img src="' + esc(state.zoom) + '" alt="' + esc(STR.enlarge) + '"></div>';
}

  /* ------------------------------------------------------------- compose */
  function tabPanelHtml() {
    switch (state.tab) {
      case 'overview': return overviewHtml();
      case 'signup': return guideTabHtml('signup');
      case 'login': return guideTabHtml('login');
      case 'reservation':
        if (state.view === 'wizard') return wizardStepHtml();
        if (state.view === 'result') return wizardResultHtml();
        return guideTabHtml('reservation');
      case 'manage': return guideTabHtml('manage');
      case 'trouble': return troubleHtml();
      default: return overviewHtml();
    }
  }

  function render() {
    ensureStyles();
    header();
    var body = getBody();
    if (!body) return;
    var inner = tabBarHtml() + '<div class="prh-tabpanel" id="prhTabPanel">' + tabPanelHtml() + '</div>' + lightboxHtml();
    body.innerHTML = '<div class="prh-root" data-prh-root>' + inner + '</div>';
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
    if (state.step > 1) { state.step -= 1; render(); return; }
    // step 1 → leave the wizard back to the photo guide
    state.view = 'guide';
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
    } else if (action === 'go-tab') {
      var tab = actionEl.getAttribute('data-prh-tab');
      if (tab && TAB_ORDER.indexOf(tab) !== -1) {
        state.tab = tab;
        state.view = 'guide';
        render();
        // Move focus to the newly active tab for keyboard users.
        var t = document.getElementById('prhtab-' + tab);
        if (t && typeof t.focus === 'function') t.focus();
      }
    } else if (action === 'start-finder') {
      state.tab = 'reservation';
      state.view = 'wizard';
      state.step = 1;
      render();
    } else if (action === 'back-to-photos') {
      state.tab = 'reservation';
      state.view = 'guide';
      render();
    } else if (action === 'toggle-done') {
      var sid = actionEl.getAttribute('data-prh-step');
      if (sid) { if (state.done[sid]) delete state.done[sid]; else state.done[sid] = true; persistDone(); render(); }
    } else if (action === 'goto-step') {
      var target = actionEl.getAttribute('data-prh-target');
      var el = target && document.getElementById(target);
      if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (action === 'zoom') {
      var src = actionEl.getAttribute('data-prh-src');
      if (src) { state.zoom = src; render(); }
    } else if (action === 'close-zoom') {
      state.zoom = '';
      render();
    } else if (action === 'restart') {
      // Restart the finder only — stay inside the reservation tab.
      state.purpose = ''; state.card = ''; state.loc = '';
      state.code = state.visaCode ? normalizeCode(state.visaCode) : '';
      state.expiry = ''; state.step = 1; state.lastModel = null;
      state.tab = 'reservation'; state.view = 'wizard';
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

  // Roving-tabindex arrow-key navigation across the tablist.
  function onKeydown(e) {
    var t = e.target;
    if (!t || !t.getAttribute || t.getAttribute('role') !== 'tab') return;
    var key = e.key;
    if (key !== 'ArrowLeft' && key !== 'ArrowRight' && key !== 'Home' && key !== 'End') return;
    e.preventDefault();
    var idx = TAB_ORDER.indexOf(state.tab);
    var nextIdx = idx;
    if (key === 'ArrowLeft') nextIdx = (idx - 1 + TAB_ORDER.length) % TAB_ORDER.length;
    else if (key === 'ArrowRight') nextIdx = (idx + 1) % TAB_ORDER.length;
    else if (key === 'Home') nextIdx = 0;
    else if (key === 'End') nextIdx = TAB_ORDER.length - 1;
    state.tab = TAB_ORDER[nextIdx];
    state.view = 'guide';
    render();
    var el = document.getElementById('prhtab-' + state.tab);
    if (el && typeof el.focus === 'function') el.focus();
  }

  // Escape closes the lightbox first (without closing the whole modal).
  // Must run on KEYDOWN in the capture phase: index.html's global Escape
  // handler is a bubble-phase document keydown listener that closes the whole
  // #hikoreaGuideOverlay — the old keyup listener always fired after it, so
  // Escape tore down the modal instead of just dismissing the lightbox.
  function onZoomKeydown(e) {
    if (e.key === 'Escape' && state.zoom) {
      e.stopPropagation();
      e.preventDefault();
      state.zoom = '';
      render();
    }
  }

  /* ---------------------------------------------------------- public API */
  function reset(opts) {
    opts = opts || {};
    loadDone();
    state.visaCode = opts.visaCode || '';
    state.purpose = '';
    state.card = '';
    state.loc = '';
    state.code = opts.visaCode ? normalizeCode(opts.visaCode) : '';
    state.expiry = '';
    state.step = 1;
    state.zoom = '';
    // Opened from a specific visa → jump straight to the reservation finder,
    // prefilled. Opened from the gateway card → start on the overview.
    if (opts.visaCode) {
      state.tab = 'reservation';
      state.view = 'wizard';
    } else {
      state.tab = 'overview';
      state.view = 'guide';
    }
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
  document.addEventListener('keydown', onKeydown);
  document.addEventListener('keydown', onZoomKeydown, true);

  // Live language switch: re-render whatever view is open.
  window.addEventListener('paradiso-language-applied', function () {
    var overlay = document.getElementById('hikoreaGuideOverlay');
    if (overlay && overlay.classList.contains('active')) {
      try { render(); } catch (e) { /* noop */ }
    }
  });

  window.ParadisoReservationHelper = {
    version: 2,
    open: open,
    render: render,
    reset: reset,
    computeReservationPath: computeReservationPath,
    suggestionsFor: suggestionsFor
  };
})();
