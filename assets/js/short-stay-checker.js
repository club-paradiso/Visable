/* ============================================================================
 * Paradiso — 국적별 단기입국 경로 확인 (Short-stay entry checker)
 * ----------------------------------------------------------------------------
 * Answers, in plain language, whether a nationality can enter Korea without a
 * visa (B-1 agreement / B-2-1 general visa-free + K-ETA), whether Jeju-only
 * B-2-2 entry is a separate possibility, and which C-3 subtype applies when a
 * visa is required.
 *
 * Data: fetched lazily from data/short-stay/rules.json (NEVER embedded in
 * index.html). Source metadata: data/short-stay/sources.json.
 *
 * Safety contract (do not weaken):
 *  - K-ETA is described as travel authorization, never as a visa.
 *  - Entry is never described as guaranteed; the immigration officer decides.
 *  - General visa-free (B-2-1/K-ETA) is kept separate from Jeju B-2-2.
 *  - "Not in a denial list" is never converted into "guaranteed eligible".
 *  - Deterministic list results use deterministic wording (no "~로 보입니다").
 *  - Source date + freshness status are always displayed.
 * ========================================================================== */
(function () {
  'use strict';

  var RULES_URL = 'data/short-stay/rules.json';

  /* ---------------------------------------------------------------- strings */
  var STR = {
    title: '국적별 단기입국 경로 확인',
    titleEn: 'Short-stay entry checker',
    subtitle: '국적·여권·방문지역·목적을 기준으로 무사증, 제주 무사증, C-3 사증 가능성을 확인합니다.',
    eyebrow: 'Short-stay entry',
    countryLabel: '1. 국적 (여권 발행국)',
    countryPlaceholder: '예: 베트남, Vietnam, 일본, United States',
    countryHelper: '국가명을 입력하면 후보를 보여드립니다.',
    countryMissing: '국적을 먼저 입력해 주세요.',
    countryNotFound: '국가명을 찾지 못했습니다. 영문명 또는 한국어 국가명으로 다시 입력해 주세요.',
    passportLabel: '2. 여권 종류',
    purposeLabel: '3. 방문 목적',
    destinationLabel: '4. 방문 지역',
    stayLabel: '5. 예정 체류일수',
    stayHelper: '며칠 정도 머무를 예정인가요?',
    ageLabel: '나이대 (선택)',
    submit: '경로 확인하기',
    reset: '다시 입력',
    loading: '공식 목록 데이터를 불러오는 중입니다…',
    fetchFail: '국가별 목록 데이터를 불러오지 못했습니다. 이 상태에서는 무사증 가능 여부를 안내할 수 없습니다. K-ETA 공식 누리집, 비자포털 또는 관할 재외공관에서 직접 확인해 주세요.',
    resultPath: '추천 경로',
    resultWhy: '왜 이 경로인가요?',
    resultNext: '다음에 해야 할 일',
    resultWarn: '반드시 확인할 점',
    resultOfficial: '공식 확인',
    resultAlt: '다른 가능성',
    sourceBadgeVerified: '공식 기준 확인됨',
    sourceBadgeNeedsRefresh: '공식 최신성 확인 필요',
    sourceBadgePartial: '일부 자료 기준',
    sourceDatePrefix: '출처 기준일'
  };

  var PASSPORT_OPTIONS = [
    { value: 'ordinary', label: '일반여권' },
    { value: 'diplomatic', label: '외교여권' },
    { value: 'official', label: '관용/공무여권' },
    { value: 'special', label: '특별/서비스여권' },
    { value: 'unknown', label: '잘 모르겠음' }
  ];
  var PURPOSE_OPTIONS = [
    { value: 'tourism', label: '관광' },
    { value: 'family_visit', label: '가족·지인 방문' },
    { value: 'transit', label: '환승' },
    { value: 'business', label: '출장·상담·계약' },
    { value: 'medical', label: '의료관광' },
    { value: 'event', label: '행사·회의' },
    { value: 'overseas_korean', label: '동포 방문' },
    { value: 'work_or_profit', label: '취업·영리활동' },
    { value: 'unknown', label: '잘 모르겠음' }
  ];
  var DESTINATION_OPTIONS = [
    { value: 'mainland', label: '한국 본토' },
    { value: 'jeju_only', label: '제주만 방문' },
    { value: 'jeju_then_mainland', label: '제주 입국 후 본토 이동 희망' },
    { value: 'transit_only', label: '공항 환승만' },
    { value: 'unknown', label: '잘 모르겠음' }
  ];
  var AGE_OPTIONS = [
    { value: 'unknown', label: '선택 안 함' },
    { value: '17_or_younger', label: '만 17세 이하' },
    { value: '18_to_64', label: '만 18~64세' },
    { value: '65_or_older', label: '만 65세 이상' }
  ];

  /* ------------------------------------------------------------ pure utils */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  function normalizeCountryInput(input) {
    return String(input == null ? '' : input).toLowerCase().normalize('NFC')
      .replace(/[\s\-–—'’.()]/g, '');
  }
  /* 은/는 particle for natural Korean (final consonant check). */
  function topicParticle(word) {
    var s = String(word || '');
    var last = s.charCodeAt(s.length - 1);
    if (last >= 0xAC00 && last <= 0xD7A3) return ((last - 0xAC00) % 28) !== 0 ? '은' : '는';
    return '은(는)';
  }
  function withParticle(word) { return word + topicParticle(word); }
  function uniq(arr) {
    var out = [], seen = {};
    (arr || []).forEach(function (x) { if (x != null && !seen[x]) { seen[x] = true; out.push(x); } });
    return out;
  }

  function resolveCountryAlias(input, rules) {
    var norm = normalizeCountryInput(input);
    if (!norm || !rules) return { country: null, suggestions: [] };
    var iso = rules.aliases[norm];
    if (iso && rules.countries[iso]) return { country: rules.countries[iso], suggestions: [] };
    /* prefix / substring suggestions over alias keys */
    var seen = {};
    var suggestions = [];
    var keys = Object.keys(rules.aliases);
    for (var pass = 0; pass < 2 && suggestions.length < 7; pass++) {
      for (var i = 0; i < keys.length && suggestions.length < 7; i++) {
        var k = keys[i];
        var hit = pass === 0 ? k.indexOf(norm) === 0 : k.indexOf(norm) > 0;
        if (!hit) continue;
        var iso2 = rules.aliases[k];
        if (seen[iso2]) continue;
        seen[iso2] = true;
        var c = rules.countries[iso2];
        if (c) suggestions.push(c);
      }
    }
    return { country: null, suggestions: suggestions };
  }

  function parseStayDays(stay) {
    if (!stay) return null;
    var m = /(\d+)\s*일/.exec(stay);
    if (m) return parseInt(m[1], 10);
    m = /(\d+)\s*개월/.exec(stay);
    if (m) return parseInt(m[1], 10) * 30;
    return null;
  }

  /* ------------------------------------------------- deterministic wording */
  function phraseB21NotListed(c) {
    return '현재 반영된 공식 K-ETA 대상국 목록 기준으로, ' + c.nameKo +
      ' 일반여권은 일반 무사증/B-2-1·K-ETA 대상국으로 등재되어 있지 않습니다.';
  }
  function phraseB21Listed(c) {
    return '현재 반영된 공식 K-ETA 대상국 목록 기준으로, ' + withParticle(c.nameKo) +
      ' 일반 무사증/B-2-1·K-ETA 대상국으로 등재되어 있습니다(허용 체류 ' + c.b21.stay + ').';
  }
  function phraseB1Listed(c) {
    return '현재 반영된 사증면제협정 목록 기준으로, ' + c.nameKo +
      ' 일반여권은 사증면제협정(B-1) 대상국으로 등재되어 있습니다(협정상 체류 ' + c.b1.stay +
      (c.b1.stayNote ? ' · ' + c.b1.stayNote : '') + ').';
  }
  function phraseB1Suspended(c) {
    return '현재 반영된 사증면제협정 목록 기준으로, ' + c.nameKo +
      ' 일반여권은 협정 적용이 일시정지 상태로 등재되어 있습니다(' + (c.b1.suspensionNote || '일시정지') + ').';
  }
  function phraseJejuNotDenied(c) {
    return '현재 반영된 제주 무사증 고시 기준으로, ' + withParticle(c.nameKo) +
      ' 제주 무사증 입국불허 국가 목록에는 포함되어 있지 않습니다.';
  }
  function phraseJejuDenied(c) {
    return '현재 반영된 제주 무사증 고시 기준으로, ' + withParticle(c.nameKo) +
      ' 제주 무사증 입국불허 국가 목록에 포함되어 있습니다.';
  }
  /* Legal note reused by the Jeju → mainland resolution. The Jeju visa-free
     (B-2-2) stay area is limited to Jeju, and 체류지역 확대허가 (expanding it to the
     mainland) is, as a rule, NOT granted — it is an exceptional measure, not a
     planning route. So we never present a "Jeju visa-free + expansion permit"
     answer; instead we state the limitation plainly and steer to a route that
     actually reaches the mainland. */
  function phraseJejuStayAreaLimited(c) {
    var deniedPrefix = (c.b22Jeju && c.b22Jeju.jejuEntryDenied)
      ? (phraseJejuDenied(c) + ' 또한 ') : '';
    return deniedPrefix + '제주 무사증(B-2-2)은 체류지역이 제주특별자치도로 한정되는 별도 제도이며, ' +
      '제주에서 본토(타 지역)로 이동하는 체류지역 확대는 원칙적으로 허용되지 않습니다.';
  }

  var WARN_FINAL_DECISION = '최종 입국 여부는 입국심사관이 결정합니다. 어떤 경로도 입국을 보장하지 않습니다.';
  var WARN_AIRLINE = '항공사 탑승 가능 여부, 입국 경로, 최신 고시·목록을 출발 전에 반드시 확인하세요.';
  var WARN_KETA_NOT_VISA = 'K-ETA는 사증(비자)이 아닌 전자여행허가이며, K-ETA 승인 또는 무사증 대상 여부가 입국을 보장하지는 않습니다.';
  var WARN_JEJU_SEPARATE = '제주 무사증은 일반 무사증/B-2-1·K-ETA와 별도 제도입니다.';
  var WARN_NO_EXTENSION = 'B-1·B-2로 입국한 경우 원칙적으로 체류기간 연장·체류자격 변경이 허용되지 않습니다. 허용 기간을 초과해 머무르려면 사증을 받아 입국해야 합니다.';
  var WARN_CONSULATE_VARIES = '재외공관별 제출서류와 심사 기준은 다를 수 있습니다. 항공권 구매 전 관할 재외공관 또는 비자포털에서 확인하세요.';
  var WARN_TRANSIT_NOT_ENTRY = '공항 밖으로 나가는 것은 환승이 아니라 입국입니다. 입국이 필요하면 무사증·사증 등 입국 경로를 별도로 확인해야 합니다.';

  /* -------------------------------------------------------------- the engine */
  function getShortStayEntryOptions(input, rules) {
    var c = input.country;
    var passport = input.passportType || 'unknown';
    var purpose = input.purpose || 'unknown';
    var destination = input.destination || 'unknown';
    var stayDays = input.stayDays || null;
    var ageGroup = input.ageGroup || 'unknown';

    var r = {
      country: c,
      passportType: passport,
      purpose: purpose,
      destination: destination,
      stayDays: stayDays,
      primary: null,            /* { path, status, explanation[] } */
      alternatives: [],         /* [{ path, note }] */
      steps: [],
      warnings: [],
      officialLinks: defaultOfficialLinks(),
      sourceRefs: (c && c.sourceRefs) || [],
      sourceStatus: rules.sourceStatus,
      sourceDate: rules.lastUpdated,
      showKeta: false,
      provisional: false,
      verdict: null
    };

    var c3map = rules.rules.c3Fallback.purposeMap;
    var visaFreeB1 = !!(c.b1 && c.b1.ordinaryEligible);
    var visaFreeB21 = !!(c.b21 && c.b21.listed);
    var visaFree = visaFreeB1 || visaFreeB21;
    var ordinaryLike = passport === 'ordinary' || passport === 'unknown';

    if (passport === 'unknown') {
      r.warnings.push('여권 종류를 모르는 경우 일반여권 기준으로 안내합니다. 외교·관용·특별여권은 적용 범위가 다를 수 있습니다.');
    }

    /* --- pure airport transit (공항 환승만) ------------------------------------
       Resolved FIRST, before the passport/purpose branches: airside transit is
       not 입국 (출입국관리법 제7조), so the right answer depends on the C-3-10
       순수환승 nationality/passport rule, not on the entry-oriented logic below.
       Kept strictly separate from entry routes; never claims transit/boarding is
       guaranteed. */
    if (destination === 'transit_only' || (purpose === 'transit' && destination === 'unknown')) {
      resolveTransit(r, c, passport, rules);
      return finalizeResult(r, rules);
    }

    /* --- non-ordinary passports: stored data is partial → official check --- */
    if (!ordinaryLike) {
      var dipl = c.b1 && c.b1.diplomaticOfficialOnly;
      r.primary = {
        path: '관할 재외공관 공식 확인',
        status: 'needs_official_check',
        explanation: [
          '외교·관용·특별여권의 사증면제 적용 범위는 협정별로 달라, 현재 저장된 자료에는 일부 국가만 반영되어 있습니다.'
        ].concat(dipl ? ['마지막으로 반영된 공식 목록 기준으로는 ' + c.nameKo + ' ' + c.b1.diplomaticOfficialScope +
          ' 여권에 대해 사증면제협정(B-1)이 적용되는 것으로 기록되어 있습니다(체류 ' + c.b1.diplomaticOfficialStay + '). 최신 공식 확인이 필요합니다.'] : [])
      };
      r.steps = [
        '관할 재외공관 또는 소속 기관을 통해 해당 여권 종류의 사증면제 적용 여부를 확인하세요.',
        '적용되지 않으면 목적에 맞는 사증(C-3 계열 등)을 신청하세요.'
      ];
      r.warnings.push(WARN_FINAL_DECISION);
      return finalizeResult(r, rules);
    }

    /* --- profit-making work: never a B/C tourism answer --------------------- */
    if (purpose === 'work_or_profit') {
      r.primary = {
        path: '단기취업(C-4) 또는 취업 자격(D/E 계열) 공식 확인',
        status: 'needs_official_check',
        explanation: [
          '보수를 받는 활동·영리활동은 무사증(B-1·B-2)이나 단기방문(C-3)의 활동범위가 아닙니다.',
          '단기 보수 활동은 단기취업(C-4), 계속 취업은 D/E 계열 등 별도 체류자격이 필요할 수 있습니다.'
        ]
      };
      r.steps = [
        '활동 내용·기간·보수 여부를 정리하세요.',
        '관할 재외공관 또는 비자포털에서 해당 활동에 맞는 자격(C-4, E 계열 등)을 확인하세요.'
      ];
      r.warnings.push('무사증·관광 목적 입국 후 보수 활동을 하면 출입국관리법 위반이 될 수 있습니다.');
      r.warnings.push(WARN_FINAL_DECISION);
      return finalizeResult(r, rules);
    }

    /* --- overseas Korean ------------------------------------------------------ */
    if (purpose === 'overseas_korean') {
      r.primary = {
        path: '동포방문(C-3-8) 또는 재외동포(F-4) 경로 확인',
        status: 'needs_official_check',
        explanation: [
          '외국국적동포는 동포방문(C-3-8, 5년 유효 복수사증·90일) 또는 재외동포(F-4) 경로를 검토할 수 있습니다.',
          '단기 일반 무사증 입국이 가능한 국적이라도, 동포 자격 확인과 활동 범위는 별도 절차입니다.'
        ].concat(visaFree ? [visaFreeB21 ? phraseB21Listed(c) : phraseB1Listed(c)] : [])
      };
      r.steps = [
        '본인·부모·조부모의 한국 국적 이력 등 동포 해당 여부를 확인하세요.',
        '단순 방문이면 C-3-8, 장기 체류·취업 계획이 있으면 F-4 경로를 검토하세요(이 페이지의 "F-4 재외동포 경로 찾기" 참고).',
        '관할 재외공관에서 제출서류를 확인하세요.'
      ];
      r.warnings.push('단기방문(C-3) 자격으로는 취업활동이 허용되지 않습니다.');
      r.warnings.push(WARN_FINAL_DECISION);
      r.showKeta = visaFree;
      return finalizeResult(r, rules);
    }

    /* --- Jeju destinations ----------------------------------------------------- */
    var jeju = c.b22Jeju || {};

    /* Jeju → mainland: the traveler ultimately wants to reach the Korean mainland.
       Legal basis (제주특별법 제197·198조): Jeju visa-free entry (B-2-2) is granted only
       "for the purpose of staying in Jeju" and, as an exception to 출입국관리법 제7조제1항;
       moving on to the mainland needs a discretionary 체류지역 확대 허가 (제198조). So we
       NEVER answer "Jeju visa-free + 체류지역 확대허가". We resolve by the route that
       actually reaches the mainland:
         - General visa-free (B-1 사증면제 / B-2-1 일반무사증) is a NATIONWIDE status, not
           the Jeju-only B-2-2 program: such travelers enter under general visa-free
           even via Jeju, so the B-2-2 Jeju-only limitation does NOT apply to them and
           must not be shown as a constraint on their trip.
         - Otherwise a proper visa is required, and the B-2-2 limitation note IS shown
           because the Jeju route genuinely cannot be expanded to the mainland.
       When the route is clearly determined we do not surface speculative "다른 가능성". */
    if (destination === 'jeju_then_mainland') {
      var purposeJTM = (purpose === 'unknown') ? 'tourism' : purpose;
      if (purpose === 'unknown') {
        r.provisional = true;
        r.warnings.push('방문 목적을 알 수 없어 관광 기준의 잠정 안내입니다. 목적을 선택하면 더 정확한 경로를 안내합니다.');
      }

      if (visaFree) {
        var phraseJTM = visaFreeB21 ? phraseB21Listed(c) : phraseB1Listed(c);
        var allowedJTM = parseStayDays(visaFreeB21 ? c.b21.stay : c.b1.stay);
        var explainJTM = [phraseJTM];
        if (purposeJTM === 'business') explainJTM.push('출장(회의·상담·계약 등 비영리 상용 활동)은 일반적으로 단기 방문 범위에서 검토되지만, 협정·제도별 활동범위 제한이 있을 수 있습니다.');
        if (purposeJTM === 'medical') explainJTM.push('의료관광 일정·기관에 따라 의료관광(C-3-3) 사증이 더 적합할 수 있습니다.');
        explainJTM.push('일반 무사증(B-1·B-2-1) 대상국은 제주로 입국하더라도 제주 무사증(B-2-2)이 아니라 일반 무사증 자격으로 입국하므로 체류지역이 제주로 한정되지 않습니다. 따라서 제주로 입국한 뒤 본토로 이동하거나 제주와 본토를 함께 방문하는 데 제약이 없으며, 별도의 체류지역 확대허가도 필요하지 않습니다.');
        r.primary = {
          path: visaFreeB21 ? '일반 무사증(B-2-1) + K-ETA 확인' : '사증면제협정(B-1) 무사증 입국 + K-ETA 확인',
          status: 'likely_available',
          explanation: explainJTM
        };
        r.showKeta = true;
        r.steps = [
          ketaStepText(c, rules, ageGroup),
          '여권 유효기간과 왕복 항공권 등 기본 요건을 확인하세요.',
          '입국심사 시 방문 목적과 일정을 설명할 수 있도록 준비하세요.'
        ];
        if (visaFreeB1) r.warnings.push('사증면제협정은 협정상 활동범위·기간 제한이 있을 수 있습니다. 협정 기간(' + c.b1.stay + ')을 초과하거나 영리활동을 하려면 사증이 필요합니다.');
        r.warnings.push(WARN_JEJU_SEPARATE, WARN_KETA_NOT_VISA, WARN_NO_EXTENSION, WARN_AIRLINE, WARN_FINAL_DECISION);
        if (allowedJTM && stayDays && stayDays > allowedJTM) {
          r.primary.status = 'visa_required';
          r.primary.path = c3PathLabel(c3map, purposeJTM) + ' 신청 (무사증 허용기간 초과)';
          r.primary.explanation.push('예정 체류일수(' + stayDays + '일)가 무사증 허용 기간(' + (visaFreeB21 ? c.b21.stay : c.b1.stay) + ')을 초과하므로 사증을 발급받아 입국해야 합니다.');
          r.steps = c3Steps(purposeJTM);
          r.showKeta = false;
        }
        return finalizeResult(r, rules);
      }

      /* not general visa-free → a proper visa is required to reach the mainland.
         Here the B-2-2 limitation note IS shown: these nationals might consider the
         Jeju visa-free route, so we explain why it does not reach the mainland. */
      var jejuLimitNote = phraseJejuStayAreaLimited(c);
      var deniedNoteJTM = c.b1 && c.b1.suspended ? phraseB1Suspended(c) : null;
      var c3jtm = c3map[purposeJTM] || c3map.tourism;
      r.primary = {
        path: c3jtm.code ? (c3jtm.nameKo + ' 사증(' + c3jtm.code + ') 신청') : '목적에 맞는 사증 신청 또는 공식 확인',
        status: 'visa_required',
        explanation: [
          phraseB21NotListed(c),
          deniedNoteJTM,
          jejuLimitNote,
          '따라서 본토를 방문하려면 처음부터 목적에 맞는 사증을 받아 입국해야 합니다.'
        ].filter(Boolean)
      };
      r.steps = c3Steps(purposeJTM);
      r.warnings.push(WARN_JEJU_SEPARATE, WARN_CONSULATE_VARIES, WARN_FINAL_DECISION);
      return finalizeResult(r, rules);
    }

    if (destination === 'jeju_only') {
      /* General visa-free (B-1 사증면제 / B-2-1 일반무사증) is a nationwide status that
         already covers Jeju. Such travelers enter under general visa-free — NOT the
         Jeju-only B-2-2 program (제주특별법 제197조) — so B-2-2's Jeju-only limitation /
         체류지역 확대 허가 (제198조) does not apply to them. We present the general
         visa-free route, not B-2-2. */
      if (visaFree) {
        var purposeJO = (purpose === 'unknown') ? 'tourism' : purpose;
        if (purpose === 'unknown') {
          r.provisional = true;
          r.warnings.push('방문 목적을 알 수 없어 관광 기준의 잠정 안내입니다. 목적을 선택하면 더 정확한 경로를 안내합니다.');
        }
        var allowedJO = parseStayDays(visaFreeB21 ? c.b21.stay : c.b1.stay);
        r.primary = {
          path: visaFreeB21 ? '일반 무사증(B-2-1) + K-ETA 확인' : '사증면제협정(B-1) 무사증 입국 + K-ETA 확인',
          status: 'likely_available',
          explanation: [
            visaFreeB21 ? phraseB21Listed(c) : phraseB1Listed(c),
            '일반 무사증(B-1·B-2-1) 대상국은 제주만 방문하더라도 제주 무사증(B-2-2)이 아니라 일반 무사증 자격으로 입국합니다. 일반 무사증은 체류지역이 제주로 한정되지 않으므로 제주 무사증의 제주 한정·체류지역 확대허가 제약은 적용되지 않습니다.'
          ]
        };
        r.showKeta = true;
        r.steps = [
          ketaStepText(c, rules, ageGroup),
          '여권 유효기간과 왕복 항공권 등 기본 요건을 확인하세요.',
          '입국심사 시 방문 목적과 일정을 설명할 수 있도록 준비하세요.'
        ];
        if (visaFreeB1) r.warnings.push('사증면제협정은 협정상 활동범위·기간 제한이 있을 수 있습니다. 협정 기간(' + c.b1.stay + ')을 초과하거나 영리활동을 하려면 사증이 필요합니다.');
        r.warnings.push(WARN_KETA_NOT_VISA, WARN_NO_EXTENSION, WARN_AIRLINE, WARN_FINAL_DECISION);
        if (allowedJO && stayDays && stayDays > allowedJO) {
          r.primary.status = 'visa_required';
          r.primary.path = c3PathLabel(c3map, purposeJO) + ' 신청 (무사증 허용기간 초과)';
          r.primary.explanation.push('예정 체류일수(' + stayDays + '일)가 무사증 허용 기간(' + (visaFreeB21 ? c.b21.stay : c.b1.stay) + ')을 초과하므로 사증을 발급받아 입국해야 합니다.');
          r.steps = c3Steps(purposeJO);
          r.showKeta = false;
        }
        return finalizeResult(r, rules);
      }

      /* non-visa-free nationals → the Jeju visa-free (B-2-2) program is the relevant
         route (subject to the entry-denied 고시 list). */
      if (jeju.jejuEntryDenied) {
        r.primary = {
          path: c3PathLabel(c3map, purpose) + ' 신청 또는 공식 확인',
          status: 'visa_required',
          explanation: [
            phraseJejuDenied(c),
            jeju.conflictNote ? '참고: ' + jeju.conflictNote : null,
            '따라서 제주 방문도 사증 경로로 준비해야 합니다.'
          ].filter(Boolean)
        };
        r.steps = c3Steps(purpose);
        r.warnings.push(WARN_JEJU_SEPARATE, WARN_CONSULATE_VARIES, WARN_FINAL_DECISION);
        return finalizeResult(r, rules);
      }

      var jejuDays = jeju.jejuStayDays || 30;
      var jejuExplain = [phraseJejuNotDenied(c)];
      jejuExplain.push('따라서 제주만 방문하는 경우 사증 없이 제주 무사증(B-2-2)으로 입국할 수 있습니다(체류 ' + jejuDays + '일). 단, 제주 직항 등 제주 무사증이 인정되는 입국경로(항공편·선편)로 들어와야 합니다.');
      r.primary = {
        path: '제주 무사증(B-2-2) 무비자 입국',
        status: 'jeju_visa_free',
        explanation: jejuExplain
      };
      r.steps = [
        '제주 직항 등 제주 무사증 인정 입국 경로(항공편·선편)를 확인하세요.',
        '이용 항공사에 탑승 가능 여부를 확인하세요.',
        '최신 법무부 고시와 입국 요건을 출발 전에 다시 확인하세요.'
      ];
      addAlternative(r, '일반관광 사증(C-3-9)', '본토를 함께 방문하거나 일정이 바뀔 수 있다면 처음부터 사증 신청이 안전합니다.');
      r.warnings.push(WARN_JEJU_SEPARATE, WARN_AIRLINE, WARN_FINAL_DECISION);
      if (stayDays && stayDays > (jeju.jejuStayDays || 30)) {
        r.warnings.push('예정 체류일수(' + stayDays + '일)가 제주 무사증 허용 기간(' + (jeju.jejuStayDays || 30) + '일)을 초과합니다. 사증 경로를 확인하세요.');
      }
      return finalizeResult(r, rules);
    }

    /* --- mainland (or unknown destination) ------------------------------------- */
    var purposeForC3 = (purpose === 'unknown') ? 'tourism' : purpose;
    if (purpose === 'unknown') {
      r.provisional = true;
      r.warnings.push('방문 목적을 알 수 없어 관광 기준의 잠정 안내입니다. 목적을 선택하면 더 정확한 경로를 안내합니다.');
    }

    if (visaFree) {
      var phrase = visaFreeB21 ? phraseB21Listed(c) : phraseB1Listed(c);
      var allowed = parseStayDays(visaFreeB21 ? c.b21.stay : c.b1.stay);
      var label = visaFreeB21 ? '일반 무사증(B-2-1) + K-ETA 확인' : '사증면제협정(B-1) 무사증 입국 + K-ETA 확인';
      var explain = [phrase];
      if (purpose === 'business') {
        explain.push('출장(회의·상담·계약 등 비영리 상용 활동)은 일반적으로 단기 방문 범위에서 검토되지만, 협정·제도별 활동범위 제한이 있을 수 있습니다.');
      }
      if (purpose === 'medical') {
        explain.push('의료관광 일정·기관에 따라 의료관광(C-3-3) 사증이 더 적합할 수 있습니다.');
      }
      r.primary = { path: label, status: 'likely_available', explanation: explain };
      r.showKeta = true;
      r.steps = [
        ketaStepText(c, rules, ageGroup),
        '여권 유효기간과 왕복 항공권 등 기본 요건을 확인하세요.',
        '입국심사 시 방문 목적을 명확히 설명할 수 있도록 준비하세요.'
      ];
      if (visaFreeB1) r.warnings.push('사증면제협정은 협정상 활동범위·기간 제한이 있을 수 있습니다. 협정 기간(' + c.b1.stay + ')을 초과하거나 영리활동을 하려면 사증이 필요합니다.');
      r.warnings.push(WARN_KETA_NOT_VISA, WARN_NO_EXTENSION, WARN_AIRLINE, WARN_FINAL_DECISION);
      if (allowed && stayDays && stayDays > allowed) {
        r.primary.status = 'visa_required';
        r.primary.path = c3PathLabel(c3map, purposeForC3) + ' 신청 (무사증 허용기간 초과)';
        r.primary.explanation.push('예정 체류일수(' + stayDays + '일)가 무사증 허용 기간(' + (visaFreeB21 ? c.b21.stay : c.b1.stay) + ')을 초과하므로 사증을 발급받아 입국해야 합니다.');
        r.steps = c3Steps(purposeForC3);
        r.showKeta = false;
      }
      addAlternative(r, c3PathLabel(c3map, purposeForC3), '무사증 요건이 맞지 않거나 장기 일정이면 사증 경로를 이용하세요.');
      return finalizeResult(r, rules);
    }

    /* visa required for mainland */
    var deniedNote = c.b1 && c.b1.suspended ? phraseB1Suspended(c) : null;
    var c3 = c3map[purposeForC3] || c3map.tourism;
    r.primary = {
      path: c3.code ? (c3.nameKo + ' 사증(' + c3.code + ') 신청' ) : '공식 확인 필요',
      status: 'visa_required',
      explanation: [
        phraseB21NotListed(c),
        deniedNote,
        purposeForC3 === 'tourism'
          ? '한국 본토 관광은 일반관광 사증(C-3-9)을 재외공관 또는 비자포털에서 신청해야 합니다.'
          : (c3.note + ' — 재외공관 또는 비자포털에서 신청해야 합니다.')
      ].filter(Boolean)
    };
    r.steps = c3Steps(purposeForC3);
    r.warnings.push(WARN_CONSULATE_VARIES, WARN_FINAL_DECISION);
    if (purposeForC3 === 'tourism') {
      addAlternative(r, '단체관광(C-3-2)', '지정 여행사를 통한 단체관광·보증된 개별관광이라면 별도 경로가 있습니다.');
    }
    return finalizeResult(r, rules);
  }

  function c3PathLabel(c3map, purpose) {
    var c3 = c3map[purpose] || c3map.tourism;
    return c3.code ? c3.nameKo + ' 사증(' + c3.code + ')' : '공식 확인';
  }
  function c3Steps(purpose) {
    var base = [
      '관할 재외공관(대사관·총영사관)과 비자포털에서 해당 사증의 제출서류를 확인하세요.',
      '서류를 준비해 재외공관 또는 비자포털(온라인 가능 시)로 신청하세요.',
      '심사 기간을 고려해 항공권 구매 전에 신청하세요.'
    ];
    if (purpose === 'group_tourism') base.unshift('법무부 지정 여행사를 통해서만 신청할 수 있습니다.');
    if (purpose === 'medical') base.unshift('법무부 지정 의료기관의 초청·예약을 먼저 확인하세요.');
    return base;
  }
  function transitNoVisaSteps() {
    return [
      '이용 항공사에 환승 가능 여부와 환승구역 통과 조건(연결편 항공권 등)을 확인하세요.',
      '공항 밖으로 나가거나 입국심사가 필요하면, 그것은 환승이 아니라 입국이므로 방문 지역을 선택해 입국 경로를 다시 확인하세요.',
      '최종 목적지(제3국)의 입국·비자 요건도 함께 확인하세요.'
    ];
  }
  /* Pure airport-transit (공항 환승만) resolver. Mutates r. Manual/legal basis is
     carried in rules.rules.c3Fallback.transitRule (순수환승 C-3-10). Distinguishes:
       (1) C-3-10 사증 대상 일반여권 (시리아·수단·예멘·이집트) → 사증 필요,
       (2) 같은 국적의 외교·관용여권 → 매뉴얼상 면제,
       (3) C-3-10 대상이나 특별/서비스여권 등 → 매뉴얼 미명시 → 공식 확인,
       (4) 그 밖의 국적 → 입국심사 없는 환승은 원칙적으로 별도 사증 불요.
     Never claims transit/boarding/entry is guaranteed. */
  function resolveTransit(r, c, passport, rules) {
    var tr = (rules.rules.c3Fallback && rules.rules.c3Fallback.transitRule) || {};
    var ordinaryLike = passport === 'ordinary' || passport === 'unknown';
    var diplomaticOfficial = passport === 'diplomatic' || passport === 'official';
    var listed = (tr.visaRequiredIso2 || []).indexOf(c.iso2) !== -1;
    var hours = tr.transitAreaHours || 72;
    /* attach the manual/law as the basis for this transit answer */
    r.sourceRefs = uniq((tr.sourceRefs || []).concat(r.sourceRefs || []));

    /* (1) C-3-10 사증 대상 일반여권 */
    if (listed && ordinaryLike) {
      r.primary = {
        path: '순수환승 사증(C-3-10) 신청',
        status: 'transit_visa_required',
        explanation: [
          c.nameKo + ' 일반여권 소지자가 대한민국을 경유해 제3국으로 가려면, 입국심사를 거치지 않는 공항 환승이라도 현재 반영된 공식 매뉴얼 기준 순수환승(C-3-10) 사증을 받아야 합니다.',
          '순수환승(C-3-10)은 ' + (tr.validity || '단수사증') + ' · ' + (tr.stayPeriod || '체류기간 0일') + '이며, 환승구역 내에서 ' + hours + '시간 동안 임시 체재만 가능합니다. 입국심사(입국) 목적으로는 사용할 수 없습니다.',
          (passport === 'unknown' ? '외교·관용여권 소지자는 순수환승(C-3-10) 사증 없이 환승할 수 있습니다.' : null)
        ].filter(Boolean)
      };
      r.steps = [
        tr.applicationDocsNote ? (tr.applicationDocsNote + '를 준비하세요.') : '여행계획서 등 제출서류를 준비하세요.',
        '관할 재외공관에 순수환승(C-3-10) 사증을 신청하세요.',
        '연결편 항공권과 최종 목적지(제3국)의 입국·비자 요건을 함께 확인하세요.'
      ];
      r.warnings.push('순수환승(C-3-10)으로는 대한민국에 입국(공항 밖 이동)할 수 없습니다. 한국을 방문하려면 목적에 맞는 사증을 별도로 받아 입국해야 합니다.');
      r.warnings.push(WARN_AIRLINE, WARN_FINAL_DECISION);
      return r;
    }

    /* (2) 같은 국적의 외교·관용여권 → 매뉴얼상 C-3-10 면제 */
    if (listed && diplomaticOfficial && tr.diplomaticOfficialExempt) {
      r.primary = {
        path: '공항 환승 (외교·관용여권 순수환승 사증 면제)',
        status: 'transit_no_visa',
        explanation: [
          '현재 반영된 공식 매뉴얼 기준, ' + c.nameKo + ' 외교·관용여권 소지자는 순수환승(C-3-10) 사증 없이 대한민국 공항에서 환승할 수 있습니다.',
          '입국심사를 거치지 않고 환승구역만 통과하는 환승은 출입국관리법 제7조의 사증이 필요한 입국에 해당하지 않습니다.',
          '같은 국적이라도 일반여권 소지자는 순수환승(C-3-10) 사증이 필요합니다.'
        ]
      };
      r.steps = transitNoVisaSteps();
      r.warnings.push(WARN_TRANSIT_NOT_ENTRY, WARN_AIRLINE, WARN_FINAL_DECISION);
      return r;
    }

    /* (3) C-3-10 대상국이나 일반/외교·관용 외 여권(특별·서비스 등) → 매뉴얼 미명시 */
    if (listed) {
      r.primary = {
        path: '환승 사증 필요 여부 공식 확인',
        status: 'needs_official_check',
        explanation: [
          c.nameKo + ' 일반여권은 순수환승(C-3-10) 사증이 필요하고 외교·관용여권은 면제되지만, 선택하신 여권 종류는 공식 매뉴얼에 환승 기준이 명시되어 있지 않아 단정하기 어렵습니다.',
          '관할 재외공관 또는 1345에서 해당 여권 종류의 순수환승(C-3-10) 사증 필요 여부를 확인하세요.'
        ]
      };
      r.steps = [
        '관할 재외공관 또는 1345에 해당 여권 종류의 순수환승(C-3-10) 사증 필요 여부를 문의하세요.',
        '연결편 항공권과 최종 목적지(제3국)의 입국·비자 요건을 함께 확인하세요.'
      ];
      r.warnings.push(WARN_TRANSIT_NOT_ENTRY, WARN_AIRLINE, WARN_FINAL_DECISION);
      return r;
    }

    /* (4) 그 밖의 모든 국적 → 입국심사 없는 공항 환승은 원칙적으로 별도 사증 불요 */
    r.primary = {
      path: '공항 환승 (입국심사 없이 환승구역 통과)',
      status: 'transit_no_visa',
      explanation: [
        '입국심사를 거치지 않고 공항 환승구역만 통과하는 환승은 대한민국 입국이 아니므로, 현재 반영된 공식 기준으로는 별도의 대한민국 사증이 필요하지 않은 경우가 많습니다.',
        '다만 순수환승(C-3-10) 사증 대상 국적(시리아·수단·예멘·이집트 일반여권)이거나 노선·항공사 규정에 따라 환승 조건이 달라질 수 있습니다.'
      ]
    };
    r.steps = transitNoVisaSteps();
    r.warnings.push(WARN_TRANSIT_NOT_ENTRY, WARN_AIRLINE, WARN_FINAL_DECISION);
    return r;
  }
  function ketaStepText(c, rules, ageGroup) {
    var b21node = rules.rules.b21GeneralVisaFreeKeta || {};
    var keta = b21node.ketaProgram || {};
    var exempt = b21node.ketaTemporaryExemption || {};
    var tmp = c.keta && c.keta.temporaryExemption;
    var t = 'K-ETA 공식 누리집에서 전자여행허가를 신청하세요(수수료 ' + Number(keta.feeKRW).toLocaleString('ko-KR') + '원).';
    if (tmp) {
      var through = exempt.lastVerifiedThrough;
      if (through && exempt.extensionUnverified === false) {
        /* Within a confirmed temporary-exemption window: no K-ETA application
           is required. Keep the forward caveat for travel after the end date. */
        t = 'K-ETA가 ' + through + '까지 한시 면제된 국가·지역이므로, 면제 기간 중 무사증 입국 시에는 K-ETA를 신청하지 않아도 됩니다. ' + through + ' 이후 출발한다면 면제 연장·종료 여부를 K-ETA 공식 누리집에서 확인하세요.';
      } else {
        t = '마지막으로 반영된 공식 목록 기준으로는 K-ETA 한시 면제 국가·지역에 포함되어 있으나, 면제 연장·종료 여부가 확인되지 않았으므로 출발 전 K-ETA 공식 누리집에서 반드시 확인하세요.';
      }
    } else if (ageGroup === '17_or_younger' || ageGroup === '65_or_older') {
      t += ' 저장된 자료 기준으로 만 17세 이하·만 65세 이상은 K-ETA 신청 면제 대상이지만, 공식 누리집에서 최신 기준을 확인하세요.';
    }
    return t;
  }
  function addAlternative(r, path, note) { r.alternatives.push({ path: path, note: note }); }
  function defaultOfficialLinks() {
    return [
      { label: 'K-ETA 확인하기', url: 'https://www.k-eta.go.kr' },
      { label: '비자포털 확인하기', url: 'https://www.visa.go.kr' },
      { label: 'HiKorea', url: 'https://www.hikorea.go.kr' },
      { label: '1345 확인 권장', url: 'tel:1345' },
      { label: '재외공관 확인하기', url: 'https://www.mofa.go.kr' }
    ];
  }
  /* Map the internal primary.status into a single, scannable top-line verdict.
     The verdict is a clear conclusion based on the stored official lists; it does
     NOT replace the mandatory caveats, which stay visible in the "반드시 확인할 점"
     block (entry is never guaranteed, K-ETA is not a visa, no extension, etc.). */
  function passportLabelKo(v) {
    var m = { ordinary: '일반여권', diplomatic: '외교여권', official: '관용/공무여권', special: '특별/서비스여권', unknown: '일반여권' };
    return m[v] || '일반여권';
  }
  function computeVerdict(r) {
    var c = r.country, st = r.primary && r.primary.status, name = (c && c.nameKo) || '';
    if (st === 'likely_available') {
      var b21 = String(r.primary.path).indexOf('B-2-1') !== -1;
      var stay = b21 ? (c.b21 && c.b21.stay) : (c.b1 && c.b1.stay);
      return {
        tone: 'go',
        headline: '무사증으로 입국할 수 있습니다',
        summary: name + ' ' + withParticle(passportLabelKo(r.passportType)) + ' 현재 저장된 공식 목록 기준 무사증 대상입니다'
          + (stay ? '(허용 체류 ' + stay + ').' : '.') + ' 아래 준비사항과 반드시 확인할 점을 함께 확인하세요.'
      };
    }
    if (st === 'visa_required') {
      return {
        tone: 'visa',
        headline: '사증(비자)을 받아야 입국할 수 있습니다',
        summary: '현재 저장된 공식 목록 기준 무사증 대상이 아니거나 예정 일정이 허용 기간을 넘습니다. 아래 경로로 재외공관·비자포털에서 신청하세요.'
      };
    }
    if (st === 'jeju_visa_free') {
      var jstay = (c.b22Jeju && c.b22Jeju.jejuStayDays) || 30;
      return {
        tone: 'jeju',
        headline: '제주 무사증으로 제주를 방문할 수 있습니다',
        summary: name + ' ' + withParticle(passportLabelKo(r.passportType)) +
          ' 현재 저장된 제주 무사증 고시 기준 입국불허 국가가 아니므로, 제주만 방문하는 경우 사증 없이 제주 무사증(B-2-2)으로 입국할 수 있습니다(체류 ' + jstay + '일). 제주 직항 등 인정 입국경로 조건과 아래 “반드시 확인할 점”을 함께 확인하세요.'
      };
    }
    if (st === 'transit_visa_required') {
      return {
        tone: 'visa',
        headline: '환승에도 순수환승(C-3-10) 사증이 필요합니다',
        summary: name + ' ' + withParticle(passportLabelKo(r.passportType)) +
          ' 현재 저장된 공식 매뉴얼 기준 순수환승(C-3-10) 사증 대상입니다. 입국심사를 거치지 않는 공항 환승이라도 사증이 필요하며, 이 사증으로는 입국할 수 없습니다(체류 0일).'
      };
    }
    if (st === 'transit_no_visa') {
      return {
        tone: 'transit',
        headline: '사증 없이 공항 환승이 가능한 경우입니다',
        summary: '입국심사를 거치지 않고 환승구역만 통과하는 환승은 대한민국 입국이 아니므로 별도 사증이 필요하지 않은 경우가 많습니다. 공항 밖으로 나가려면 입국 경로를 별도로 확인하세요. 탑승·환승 가능 여부는 항공사·노선 규정에 따릅니다.'
      };
    }
    if (st === 'not_available') {
      return { tone: 'visa', headline: '무사증 입국이 어렵습니다 — 사증 경로 확인', summary: '아래 안내된 사증 경로를 확인하세요.' };
    }
    return {
      tone: 'check',
      headline: '공식 확인이 필요한 사례입니다',
      summary: '국적·여권·목적 조합상 저장된 자료만으로 단정하기 어렵습니다. 아래 안내에 따라 관할 재외공관·공식 누리집에서 확인하세요.'
    };
  }
  function finalizeResult(r, rules) {
    if (r.showKeta) {
      if (r.warnings.indexOf(WARN_KETA_NOT_VISA) === -1) r.warnings.push(WARN_KETA_NOT_VISA);
    }
    if (rules.sourceStatus !== 'verified') {
      r.warnings.push('현재 저장된 자료 기준입니다. 공식 목록이 업데이트되었을 수 있으므로 출발 전 공식 누리집에서 확인하세요.');
    }
    r.verdict = computeVerdict(r);
    r.alternatives = rankShortStayOptions(r.alternatives);
    return r;
  }
  function rankShortStayOptions(options) {
    /* stable, light ranking: keep insertion order but cap at 3 */
    return (options || []).slice(0, 3);
  }
  function getShortStayProcedureSteps(result) { return result && result.steps ? result.steps : []; }
  function formatShortStayWarnings(result) {
    var seen = {};
    return (result && result.warnings ? result.warnings : []).filter(function (w) {
      if (seen[w]) return false; seen[w] = true; return true;
    });
  }

  /* ----------------------------------------------------------------- badge */
  function renderSourceFreshnessBadge(sourceStatus, sourceDate) {
    var cls = sourceStatus === 'verified' ? 'ok' : (sourceStatus === 'partial' ? 'partial' : 'refresh');
    var label = sourceStatus === 'verified' ? STR.sourceBadgeVerified
      : sourceStatus === 'partial' ? STR.sourceBadgePartial : STR.sourceBadgeNeedsRefresh;
    return '<span class="ssc-badge ssc-badge-' + cls + '">' + esc(label) + '</span>' +
      (sourceDate ? '<span class="ssc-badge ssc-badge-date">' + esc(STR.sourceDatePrefix + ': ' + sourceDate) + '</span>' : '');
  }

  /* expose pure API for validation scripts / tests */
  var api = {
    STR: STR,
    normalizeCountryInput: normalizeCountryInput,
    resolveCountryAlias: resolveCountryAlias,
    getShortStayEntryOptions: getShortStayEntryOptions,
    rankShortStayOptions: rankShortStayOptions,
    getShortStayProcedureSteps: getShortStayProcedureSteps,
    formatShortStayWarnings: formatShortStayWarnings,
    renderSourceFreshnessBadge: renderSourceFreshnessBadge,
    topicParticle: topicParticle,
    parseStayDays: parseStayDays
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoShortStay = api;

  /* ====================== DOM layer (browser only) ======================== */
  if (typeof document === 'undefined') return;

  var state = { rules: null, loadPromise: null, loadError: false, formRendered: false };

  function loadShortStayRules() {
    if (state.rules) return Promise.resolve(state.rules);
    if (state.loadPromise) return state.loadPromise;
    state.loadPromise = fetch(RULES_URL, { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (json) {
        if (!json || json.schemaVersion !== 1 || !json.countries || !json.aliases) {
          throw new Error('unexpected rules schema');
        }
        state.rules = json;
        state.loadError = false;
        return json;
      })
      .catch(function (err) {
        state.loadError = true;
        state.loadPromise = null;
        throw err;
      });
    return state.loadPromise;
  }
  api.loadShortStayRules = loadShortStayRules;

  function injectStyles() {
    if (document.getElementById('shortStayCheckerStyles')) return;
    var css = '' +
'.short-stay-checker{margin:1.25rem 0;}' +
'.modal-body .short-stay-checker{margin:0;}' +
'.ssc-card{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1.1rem 1.15rem;}' +
'.ssc-card-modal{background:transparent;border:0;border-radius:0;box-shadow:none;padding:0;}' +
'.ssc-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.ssc-title{font-size:1.15rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .25rem;}' +
'.ssc-sub{font-size:.85rem;color:var(--t2,#4f5552);margin:0 0 .7rem;word-break:keep-all;}' +
'.ssc-badges{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.8rem;}' +
'.ssc-badge{display:inline-block;font-size:.72rem;font-weight:700;padding:.18rem .55rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t2,#4f5552);background:var(--bg2,#f1ece2);}' +
'.ssc-badge-refresh{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.ssc-badge-ok{border-color:var(--cSt,#0EA37B);color:var(--cSt,#0a7a5c);background:transparent;}' +
'.ssc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.7rem .8rem;margin-bottom:.8rem;}' +
'.ssc-field{display:flex;flex-direction:column;gap:.3rem;position:relative;}' +
'.ssc-field>span{font-size:.78rem;font-weight:700;color:var(--t2,#4f5552);}' +
'.ssc-field input,.ssc-field select{font:inherit;font-size:.9rem;padding:.55rem .6rem;border:1px solid var(--bd,#d1c6b4);border-radius:8px;background:var(--bgI,#fff);color:var(--t1,#202221);min-height:44px;}' +
'.ssc-field input:focus-visible,.ssc-field select:focus-visible,.ssc-btn:focus-visible,.ssc-sug button:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.ssc-helper{font-size:.72rem;color:var(--t3,#757a76);}' +
'.ssc-sug{position:absolute;z-index:30;top:100%;left:0;right:0;background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:8px;box-shadow:var(--sh2,0 8px 20px rgba(0,0,0,.1));max-height:220px;overflow:auto;margin-top:2px;}' +
'.ssc-sug button{display:block;width:100%;text-align:left;background:none;border:0;padding:.5rem .6rem;font:inherit;font-size:.85rem;color:var(--t1,#202221);cursor:pointer;min-height:40px;}' +
'.ssc-sug button:hover{background:var(--bg2,#f1ece2);}' +
'.ssc-actions{display:flex;gap:.5rem;flex-wrap:wrap;}' +
'.ssc-btn{font:inherit;font-weight:800;font-size:.9rem;border-radius:10px;padding:.6rem 1.1rem;cursor:pointer;min-height:44px;border:1px solid var(--ac,#2f5e67);}' +
'.ssc-btn-primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.ssc-btn-ghost{background:transparent;color:var(--ac,#2f5e67);}' +
'.ssc-result{margin-top:1rem;border-top:2px solid var(--bd2,#ddd3c3);padding-top:1rem;}' +
'.ssc-status{display:inline-block;font-size:.75rem;font-weight:800;padding:.2rem .6rem;border-radius:999px;margin-left:.4rem;vertical-align:middle;}' +
'.ssc-status-likely{background:var(--acG,rgba(47,94,103,.1));color:var(--ac,#2f5e67);border:1px solid var(--ac,#2f5e67);}' +
'.ssc-status-jeju{background:var(--acG,rgba(14,163,123,.1));color:var(--cSt,#0a7a5c);border:1px solid var(--cSt,#0EA37B);}' +
'.ssc-status-visa{background:var(--cyL,#FFE2DB);color:var(--hlT,#8A3426);border:1px solid var(--cy,#FF6B5B);}' +
'.ssc-status-check{background:transparent;color:var(--cWk,#a85f1c);border:1px solid var(--cWk,#E68A3A);}' +
'.ssc-result h4{font-size:.85rem;font-weight:800;color:var(--t2,#4f5552);margin:1rem 0 .35rem;}' +
'.ssc-result h3{font-size:1.05rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 .2rem;word-break:keep-all;}' +
'.ssc-result p,.ssc-result li{font-size:.88rem;line-height:1.65;color:var(--t1,#202221);word-break:keep-all;}' +
'.ssc-result ul,.ssc-result ol{margin:.2rem 0 .2rem;padding-left:1.2rem;}' +
'.ssc-warn{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.7rem .8rem;margin-top:.4rem;}' +
'.ssc-warn li{color:var(--hlT,#8A3426);}' +
'.ssc-links{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.4rem;}' +
'.ssc-links a{display:inline-flex;align-items:center;min-height:40px;padding:.35rem .8rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font-size:.82rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;}' +
'.ssc-links a:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.ssc-alt{border:1px dashed var(--bd,#d1c6b4);border-radius:10px;padding:.55rem .7rem;margin-top:.35rem;}' +
'.ssc-alt strong{font-size:.85rem;}' +
'.ssc-error{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.8rem;font-size:.88rem;color:var(--hlT,#8A3426);word-break:keep-all;}' +
'.ssc-details{margin-top:.6rem;}' +
'.ssc-details summary{cursor:pointer;font-size:.8rem;font-weight:700;color:var(--t2,#4f5552);min-height:32px;}' +
'.ssc-srcline{font-size:.74rem;color:var(--t3,#757a76);margin-top:.55rem;}' +
'.ssc-verdict{display:flex;gap:.6rem;align-items:flex-start;border-radius:12px;padding:.8rem .9rem;margin:.2rem 0 .7rem;border:1px solid var(--bd,#d1c6b4);}' +
'.ssc-verdict-icon{font-size:1.45rem;line-height:1.15;flex:0 0 auto;}' +
'.ssc-verdict-head{font-size:1.08rem;font-weight:800;margin:0 0 .2rem;color:var(--t1,#202221);word-break:keep-all;}' +
'.ssc-verdict-sum{font-size:.85rem;line-height:1.6;margin:0;color:var(--t2,#4f5552);word-break:keep-all;}' +
'.ssc-verdict-go{background:var(--acG,rgba(14,163,123,.10));border-color:var(--cSt,#0EA37B);}' +
'.ssc-verdict-go .ssc-verdict-head{color:var(--cSt,#0a7a5c);}' +
'.ssc-verdict-jeju{background:var(--acG,rgba(14,163,123,.10));border-color:var(--cSt,#0EA37B);}' +
'.ssc-verdict-jeju .ssc-verdict-head{color:var(--cSt,#0a7a5c);}' +
'.ssc-verdict-transit{background:var(--acG,rgba(47,94,103,.10));border-color:var(--ac,#2f5e67);}' +
'.ssc-verdict-transit .ssc-verdict-head{color:var(--ac,#2f5e67);}' +
'.ssc-verdict-visa{background:var(--cyL,#FFE2DB);border-color:var(--cy,#FF6B5B);}' +
'.ssc-verdict-visa .ssc-verdict-head{color:var(--hlT,#8A3426);}' +
'.ssc-verdict-check{background:var(--bg2,#f7f3ea);border-color:var(--cWk,#E68A3A);}' +
'.ssc-verdict-check .ssc-verdict-head{color:var(--cWk,#a85f1c);}' +
'.ssc-route{font-size:.95rem;font-weight:700;color:var(--t1,#202221);margin:.1rem 0 .2rem;word-break:keep-all;}' +
'.ssc-must{background:var(--cyL,#FFF4E6);border:1px solid var(--cWk,#E68A3A);border-radius:10px;padding:.4rem .85rem .7rem;margin-top:.5rem;}' +
'.ssc-result .ssc-must h4{margin:.55rem 0 .3rem;color:var(--cWk,#a85f1c);}' +
'.ssc-must li{color:var(--t1,#202221);}' +
'.ssc-note{border:1px solid var(--bd,#d1c6b4);border-left:3px solid var(--ac,#2f5e67);border-radius:8px;padding:.45rem .8rem .55rem;margin-top:.55rem;background:var(--bg2,#f7f3ea);}' +
'.ssc-note strong{font-size:.8rem;color:var(--ac,#2f5e67);}' +
'.ssc-note li{font-size:.82rem;color:var(--t2,#4f5552);}' +
'.ssc-srcrefs{margin:.2rem 0 .2rem;padding-left:1.1rem;}' +
'.ssc-srcrefs li{font-size:.74rem;color:var(--t3,#757a76);line-height:1.5;}' +
'@media (max-width:480px){.ssc-grid{grid-template-columns:1fr;}.ssc-card{padding:.9rem .8rem;}.ssc-verdict-head{font-size:1rem;}}' +
'@media (prefers-reduced-motion: no-preference){.ssc-result{animation:sscFade .25s ease-out;}@keyframes sscFade{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}}';
    var style = document.createElement('style');
    style.id = 'shortStayCheckerStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function optionHtml(opts, selected) {
    return opts.map(function (o) {
      return '<option value="' + esc(o.value) + '"' + (o.value === selected ? ' selected' : '') + '>' + esc(o.label) + '</option>';
    }).join('');
  }

  function renderShortStayChecker(container) {
    injectStyles();
    /* When rendered inside the page popup (modal), the modal header already
       carries the title, so drop the redundant eyebrow/title here (and avoid a
       duplicate #shortStayCheckerTitle id). The subtitle stays as a description. */
    var inModal = !!(container.closest && container.closest('.modal-body'));
    container.innerHTML =
      '<div class="ssc-card' + (inModal ? ' ssc-card-modal' : '') + '">' +
        (inModal ? '' :
          '<p class="ssc-eyebrow">' + esc(STR.eyebrow) + '</p>' +
          '<h2 class="ssc-title" id="shortStayCheckerTitle">' + esc(STR.title) + ' <span lang="en" style="font-weight:600;font-size:.8rem;color:var(--t3,#757a76);">' + esc(STR.titleEn) + '</span></h2>') +
        '<p class="ssc-sub">' + esc(STR.subtitle) + '</p>' +
        '<div class="ssc-badges" data-ssc-badges></div>' +
        '<form data-ssc-form novalidate>' +
          '<div class="ssc-grid">' +
            '<label class="ssc-field" style="grid-column:1/-1;">' +
              '<span>' + esc(STR.countryLabel) + '</span>' +
              '<input type="text" name="country" autocomplete="off" spellcheck="false" placeholder="' + esc(STR.countryPlaceholder) + '" aria-describedby="sscCountryHelp" role="combobox" aria-expanded="false" aria-autocomplete="list">' +
              '<span class="ssc-helper" id="sscCountryHelp">' + esc(STR.countryHelper) + '</span>' +
              '<div class="ssc-sug" data-ssc-sug role="listbox" aria-label="국가 후보" hidden></div>' +
            '</label>' +
            '<label class="ssc-field"><span>' + esc(STR.passportLabel) + '</span><select name="passport">' + optionHtml(PASSPORT_OPTIONS, 'ordinary') + '</select></label>' +
            '<label class="ssc-field"><span>' + esc(STR.purposeLabel) + '</span><select name="purpose">' + optionHtml(PURPOSE_OPTIONS, 'tourism') + '</select></label>' +
            '<label class="ssc-field"><span>' + esc(STR.destinationLabel) + '</span><select name="destination">' + optionHtml(DESTINATION_OPTIONS, 'mainland') + '</select></label>' +
            '<label class="ssc-field"><span>' + esc(STR.stayLabel) + '</span><input type="number" name="stayDays" min="1" max="365" inputmode="numeric" aria-describedby="sscStayHelp"><span class="ssc-helper" id="sscStayHelp">' + esc(STR.stayHelper) + '</span></label>' +
            '<label class="ssc-field"><span>' + esc(STR.ageLabel) + '</span><select name="age">' + optionHtml(AGE_OPTIONS, 'unknown') + '</select></label>' +
          '</div>' +
          '<div class="ssc-actions">' +
            '<button type="submit" class="ssc-btn ssc-btn-primary">' + esc(STR.submit) + '</button>' +
            '<button type="reset" class="ssc-btn ssc-btn-ghost">' + esc(STR.reset) + '</button>' +
          '</div>' +
        '</form>' +
        '<div class="ssc-result" data-ssc-result role="status" aria-live="polite" hidden></div>' +
      '</div>';
    bindForm(container);
  }

  function statusBadge(status) {
    if (status === 'likely_available') return '<span class="ssc-status ssc-status-likely">확인 가능 경로</span>';
    if (status === 'jeju_visa_free') return '<span class="ssc-status ssc-status-jeju">제주 무사증 가능</span>';
    if (status === 'transit_no_visa') return '<span class="ssc-status ssc-status-jeju">환승 사증 불요</span>';
    if (status === 'transit_visa_required') return '<span class="ssc-status ssc-status-visa">순수환승 사증 필요</span>';
    if (status === 'visa_required') return '<span class="ssc-status ssc-status-visa">사증 필요</span>';
    if (status === 'not_available') return '<span class="ssc-status ssc-status-visa">불가</span>';
    return '<span class="ssc-status ssc-status-check">공식 확인 필요</span>';
  }

  function renderShortStayResult(result) {
    var alt = result.alternatives.map(function (a) {
      return '<div class="ssc-alt"><strong>' + esc(a.path) + '</strong><p>' + esc(a.note) + '</p></div>';
    }).join('');
    /* (A) Map the answer's source IDs to readable titles + 기준일 + 신뢰도 via the
       sourceCatalog baked into rules.json (single source of truth, no extra fetch). */
    var catalog = (state.rules && state.rules.sourceCatalog) || [];
    var catById = {};
    catalog.forEach(function (s) { catById[s.id] = s; });
    var srcItems = (result.sourceRefs || []).map(function (id) {
      var s = catById[id];
      return s ? (esc(s.title) + ' · 기준일 ' + esc(s.sourceDate) + ' · 신뢰도 ' + esc(s.confidence)) : esc(id);
    });
    var srcListHtml = srcItems.length
      ? '<ul class="ssc-srcrefs">' + srcItems.map(function (t) { return '<li>' + t + '</li>'; }).join('') + '</ul>'
      : '<p class="ssc-srcline">—</p>';
    /* (B) Per-country data notes (source conflicts, designation revocations) are
       recorded in rules.json; surface them so the basis/uncertainty is visible. */
    var countryNotes = (result.country && result.country.notes) || [];
    var notesHtml = countryNotes.length
      ? '<div class="ssc-note"><strong>자료 유의</strong><ul>' +
        countryNotes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul></div>'
      : '';
    var v = result.verdict || { tone: 'check', headline: result.primary.path, summary: '' };
    var toneClass = { go: 'ssc-verdict-go', jeju: 'ssc-verdict-jeju', transit: 'ssc-verdict-transit', visa: 'ssc-verdict-visa', check: 'ssc-verdict-check' }[v.tone] || 'ssc-verdict-check';
    var toneIcon = { go: '✅', jeju: '🛫', transit: '✈️', visa: '📋', check: '⚠️' }[v.tone] || '⚠️';
    return '' +
      '<div class="ssc-verdict ' + toneClass + '" role="status">' +
        '<span class="ssc-verdict-icon" aria-hidden="true">' + toneIcon + '</span>' +
        '<div><p class="ssc-verdict-head">' + esc(v.headline) + statusBadge(result.primary.status) + '</p>' +
          (v.summary ? '<p class="ssc-verdict-sum">' + esc(v.summary) + '</p>' : '') +
        '</div>' +
      '</div>' +
      '<h4>' + esc(STR.resultPath) + '</h4>' +
      '<p class="ssc-route">' + esc(result.primary.path) + '</p>' +
      '<h4>' + esc(STR.resultWhy) + '</h4>' +
      result.primary.explanation.map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('') +
      '<h4>' + esc(STR.resultNext) + '</h4>' +
      '<ol>' + getShortStayProcedureSteps(result).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' +
      '<div class="ssc-must">' +
        '<h4>' + esc(STR.resultWarn) + '</h4>' +
        '<ul>' + formatShortStayWarnings(result).map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('') + '</ul>' +
      '</div>' +
      notesHtml +
      '<h4>' + esc(STR.resultOfficial) + '</h4>' +
      '<div class="ssc-links">' + result.officialLinks.map(function (l) {
        var external = l.url.indexOf('http') === 0;
        return '<a href="' + esc(l.url) + '"' + (external ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' + esc(l.label) + '</a>';
      }).join('') + '</div>' +
      (alt ? '<h4>' + esc(STR.resultAlt) + '</h4>' + alt : '') +
      '<details class="ssc-details"><summary>출처·자료 기준 자세히</summary>' +
        '<p class="ssc-srcline">' + renderSourceFreshnessBadge(result.sourceStatus, result.sourceDate) + '</p>' +
        '<p class="ssc-srcline">이 답변이 근거한 공식 출처:</p>' +
        srcListHtml +
        '<p class="ssc-srcline">전체 출처 메타데이터: data/short-stay/sources.json</p>' +
        '<p class="ssc-srcline">이 안내는 저장된 공식 목록 사본 기준의 참고 정보이며 법적 효력이 없습니다. 최종 확인은 K-ETA·비자포털·재외공관·1345에서 하세요.</p>' +
      '</details>';
  }

  /* After a result renders, gently bring the verdict into view. Inside the page
     popup the modal body is the scroll container, so a short result is already
     visible; on small screens this scrolls the verdict to the top so the user
     sees the answer immediately instead of an unchanged-looking form. */
  function revealResult(resultHost) {
    try {
      var target = resultHost.querySelector('.ssc-verdict') || resultHost;
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'nearest' });
    } catch (e) { /* non-fatal */ }
  }

  function bindForm(container) {
    var form = container.querySelector('[data-ssc-form]');
    var resultHost = container.querySelector('[data-ssc-result]');
    var countryInput = form.querySelector('input[name="country"]');
    var sugHost = form.querySelector('[data-ssc-sug]');

    function hideSug() { sugHost.hidden = true; sugHost.innerHTML = ''; countryInput.setAttribute('aria-expanded', 'false'); }

    countryInput.addEventListener('input', function () {
      ensureRules().then(function (rules) {
        var v = countryInput.value.trim();
        if (!v) { hideSug(); return; }
        var res = resolveCountryAlias(v, rules);
        var list = res.country ? [] : res.suggestions;
        if (!list.length) { hideSug(); return; }
        sugHost.innerHTML = list.map(function (c) {
          return '<button type="button" role="option" data-iso="' + esc(c.iso2) + '">' + esc(c.nameKo) + ' · ' + esc(c.nameEn) + '</button>';
        }).join('');
        sugHost.hidden = false;
        countryInput.setAttribute('aria-expanded', 'true');
      }).catch(function () { hideSug(); });
    });
    countryInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' && !sugHost.hidden) {
        var first = sugHost.querySelector('button');
        if (first) { e.preventDefault(); first.focus(); }
      }
    });
    sugHost.addEventListener('keydown', function (e) {
      var items = Array.prototype.slice.call(sugHost.querySelectorAll('button'));
      var idx = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown' && idx < items.length - 1) { e.preventDefault(); items[idx + 1].focus(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); (idx <= 0 ? countryInput : items[idx - 1]).focus(); }
      if (e.key === 'Escape') { hideSug(); countryInput.focus(); }
    });
    sugHost.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-iso]');
      if (!btn) return;
      var rules = state.rules;
      var c = rules && rules.countries[btn.dataset.iso];
      if (c) countryInput.value = c.nameKo;
      hideSug();
      countryInput.focus();
    });
    document.addEventListener('click', function (e) {
      if (!sugHost.hidden && !form.contains(e.target)) hideSug();
    });

    form.addEventListener('reset', function () {
      resultHost.hidden = true; resultHost.innerHTML = ''; hideSug();
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      hideSug();
      var raw = countryInput.value.trim();
      if (!raw) {
        resultHost.innerHTML = '<div class="ssc-error">' + esc(STR.countryMissing) + '</div>';
        resultHost.hidden = false;
        countryInput.focus();
        return;
      }
      resultHost.innerHTML = '<p class="ssc-srcline">' + esc(STR.loading) + '</p>';
      resultHost.hidden = false;
      ensureRules().then(function (rules) {
        var res = resolveCountryAlias(raw, rules);
        if (!res.country) {
          var sug = res.suggestions.map(function (c) { return c.nameKo + '(' + c.nameEn + ')'; }).join(', ');
          resultHost.innerHTML = '<div class="ssc-error">' + esc(STR.countryNotFound) +
            (sug ? '<br>비슷한 국가: ' + esc(sug) : '') +
            '<br>현재 반영된 목록 데이터에 없는 국가라면, 일반적으로 사증(C-3 등) 신청 또는 재외공관·1345 공식 확인이 필요합니다.</div>';
          return;
        }
        var stayVal = parseInt(form.querySelector('input[name="stayDays"]').value, 10);
        var result = getShortStayEntryOptions({
          country: res.country,
          passportType: form.querySelector('select[name="passport"]').value,
          purpose: form.querySelector('select[name="purpose"]').value,
          destination: form.querySelector('select[name="destination"]').value,
          stayDays: isNaN(stayVal) ? null : stayVal,
          ageGroup: form.querySelector('select[name="age"]').value
        }, rules);
        resultHost.innerHTML = renderShortStayResult(result);
        revealResult(resultHost);
      }).catch(function () {
        resultHost.innerHTML = '<div class="ssc-error">' + esc(STR.fetchFail) + '</div>' +
          '<div class="ssc-links" style="margin-top:.5rem;">' + defaultOfficialLinks().map(function (l) {
            var external = l.url.indexOf('http') === 0;
            return '<a href="' + esc(l.url) + '"' + (external ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' + esc(l.label) + '</a>';
          }).join('') + '</div>';
      });
    });
  }

  function refreshBadges(section) {
    var badgesEl = section && section.querySelector('[data-ssc-badges]');
    if (!badgesEl) return;
    if (state.loadError || !state.rules) {
      badgesEl.innerHTML = '<span class="ssc-badge ssc-badge-refresh">데이터 로드 실패 — 공식 누리집 직접 확인 필요</span>';
    } else {
      badgesEl.innerHTML = renderSourceFreshnessBadge(state.rules.sourceStatus, state.rules.lastUpdated);
    }
  }

  function ensureRules() {
    var section = document.getElementById('shortStayChecker');
    return loadShortStayRules().then(function (rules) {
      if (section) refreshBadges(section);
      return rules;
    }).catch(function (err) {
      if (section) refreshBadges(section);
      throw err;
    });
  }

  /* ------------------------------------------------ search-result integration */
  var SHORT_STAY_CODE = /^(b-?1|b-?2(-?[12])?|c-?3(-?\d{1,2})?|k-?eta)$/i;
  var SHORT_STAY_KEYWORDS = ['무사증', '무비자', '제주', 'k-eta', 'keta', '케이이티에이', '전자여행허가', '단기방문', '관광통과', '사증면제', '비자면제', '협정국', '단기 입국', '관광비자', '관광 비자'];

  function queryIsShortStayRelevant(detail) {
    var q = String((detail && detail.query) || '').toLowerCase();
    var qNorm = q.replace(/\s+/g, '');
    if (!q) return false;
    var tokens = q.split(/\s+/);
    for (var i = 0; i < tokens.length; i++) {
      if (SHORT_STAY_CODE.test(tokens[i])) return true;
    }
    for (var j = 0; j < SHORT_STAY_KEYWORDS.length; j++) {
      var kw = SHORT_STAY_KEYWORDS[j].replace(/\s+/g, '');
      if (qNorm.indexOf(kw) !== -1) return true;
    }
    var codes = (detail && detail.codes) || [];
    return codes.indexOf('B-1') !== -1 || codes.indexOf('B-2') !== -1 || codes.indexOf('C-3') !== -1;
  }

  function mountIfNeeded() {
    var section = document.getElementById('shortStayChecker');
    if (!section) return null;
    if (!state.formRendered) {
      renderShortStayChecker(section);
      state.formRendered = true;
      /* lazy data: load when the section first becomes visible */
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) { ensureRules().catch(function () {}); io.disconnect(); }
          });
        }, { rootMargin: '200px' });
        io.observe(section);
      } else {
        ensureRules().catch(function () {});
      }
    }
    return section;
  }

  function injectCardCta(detail) {
    var codes = ['B-1', 'B-2', 'C-3'];
    for (var i = 0; i < codes.length; i++) {
      var slot = document.querySelector('.external-guide-slot[data-guide-slot="' + codes[i] + '"]');
      if (!slot || slot.querySelector('.ssc-cta')) continue;
      var cta = document.createElement('button');
      cta.type = 'button';
      cta.className = 'ssc-btn ssc-btn-ghost ssc-cta';
      cta.style.cssText = 'margin:.5rem 0;width:100%;text-align:left;';
      cta.textContent = '🧭 ' + STR.title + ' — 내 국적으로 무사증·제주·C-3 가능성 확인하기';
      cta.addEventListener('click', openShortStayUI);
      slot.appendChild(cta);
    }
  }

  /* ------------------------------------------------------ popup (modal) host */
  /* The checker lives inside a page popup (#shortStayModalOverlay in index.html)
     instead of expanding the landing page. Opening renders the form lazily and
     shows the modal via the host page's modal helpers (focus-trap + ESC + overlay
     click), falling back to a self-managed reveal if no modal host is present. */
  function focusCountrySoon(section) {
    var input = section && section.querySelector('input[name="country"]');
    if (input) setTimeout(function () { try { input.focus(); } catch (e) {} }, 250);
  }
  function openShortStayUI() {
    var section = mountIfNeeded();
    if (!section) return;
    ensureRules().catch(function () {});
    var overlay = document.getElementById('shortStayModalOverlay');
    if (overlay) {
      if (typeof window.openModal === 'function') {
        window.openModal('shortStayModalOverlay');
      } else {
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
      }
      focusCountrySoon(section);
      return;
    }
    /* fallback: no modal host on this page — reveal inline as before */
    section.hidden = false;
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    focusCountrySoon(section);
  }
  function closeShortStayUI() {
    var overlay = document.getElementById('shortStayModalOverlay');
    if (overlay && overlay.classList.contains('active')) {
      if (typeof window.closeModal === 'function') {
        window.closeModal('shortStayModalOverlay');
      } else {
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
      }
    } else {
      var section = document.getElementById('shortStayChecker');
      if (section && !overlay) section.hidden = true;
    }
  }

  document.addEventListener('paradiso:results-rendered', function (e) {
    if (!document.getElementById('shortStayChecker')) return;
    /* Pre-render the form on a relevant search so the popup opens instantly, but
       never auto-expand the landing page — entry is via the CTA / utility button. */
    if (queryIsShortStayRelevant(e.detail || {})) mountIfNeeded();
    injectCardCta(e.detail || {});
  });
  document.addEventListener('paradiso:landing-reset', closeShortStayUI);

  /* Public entry points: a landing-page button (data-action="open-short-stay")
     opens the popup directly, not only as a contextual panel after a search. */
  api.open = openShortStayUI;
  api.close = closeShortStayUI;
})();
