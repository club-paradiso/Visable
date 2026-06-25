/*
 * Waymaker Navigator — all-status Korean immigration *procedure navigator*.
 *
 * Product intent: Waymaker's default experience is NOT an AI chatbot. It is a
 * deterministic, official-source-grounded procedure navigator. The authoritative
 * result is the backend Procedure Packet (GET /api/procedure-packet), built from
 * structured/reviewed data — never from an LLM. AI follow-up is secondary support
 * only and appears *after* a packet is shown.
 *
 * This module owns:
 *   - the guided intake state machine (language -> location -> status -> procedure
 *     -> minimal situation questions),
 *   - the procedure adapter (UI procedure key -> backend packet type) — it REUSES
 *     the backend enums, it does NOT introduce a second taxonomy,
 *   - mapping a packet into the 12 Action Packet sections + coverage-limited state,
 *   - a local-only checklist (browser localStorage; never sent to backend/LLM),
 *   - item/section-level source-coverage labels (user-facing, never raw codes),
 *   - HiKorea handoff + AI-follow-up hooks (wired by the host page).
 *
 * Safety invariants (mirrors backend safety_guardrails + packet builder):
 *   - No fabricated documents/fees/deadlines/citations/HiKorea tasks. Missing
 *     coverage renders as a clearly-labelled coverage-limited state.
 *   - No personal identifiers are requested, stored, logged, or sent to the LLM.
 *     Only categorical selections are persisted locally.
 *   - AI follow-up cannot override the deterministic packet's limitations.
 *
 * Dual environment: exports a small pure-logic surface for Node tests AND attaches
 * a UI controller to window for the browser. Pure logic has no DOM/network deps.
 */
(function (global, factory) {
  'use strict';
  var api = factory(global);
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof global !== 'undefined') {
    global.WaymakerNavigator = api;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function (global) {
  'use strict';

  // =========================================================================
  // 1. Procedure adapter — single source of truth, MIRRORS the backend.
  //    backend/services/procedure_packet_builder.py :: PACKET_TYPE_BY_PROCEDURE_KEY
  //    A drift guard test (test_navigator_adapter_parity) asserts these match.
  // =========================================================================
  var PACKET_TYPE_BY_PROCEDURE_KEY = {
    registration: 'foreigner_registration',
    extension: 'extension',
    statusChange: 'status_change',
    activitiesOutsideStatus: 'activities_outside_status',
    workplaceChange: 'workplace_change',
    reentry: 'reentry_permit',
    statusGrant: 'status_grant',
    visaIssuance: 'visa_issuance'
  };

  // Display order for the procedure step (first-entry first, then in-Korea life).
  var PROCEDURE_ORDER = [
    'visaIssuance', 'registration', 'extension', 'statusChange', 'statusGrant',
    'workplaceChange', 'activitiesOutsideStatus', 'reentry'
  ];

  // Source-lens enum (backend SOURCE_LENS_LEVELS) -> user-facing labels.
  // These are the Phase-7 user-facing labels (intentionally plainer than the
  // backend's internal KO labels). Color is NEVER the only indicator.
  var SOURCE_COVERAGE = {
    source_confirmed: { ko: '공식 원문 확인', en: 'Confirmed in official source', cls: 'wm-cov-confirmed' },
    contextual:       { ko: '일부 항목만 공식 확인', en: 'Partially covered by official sources', cls: 'wm-cov-partial' },
    limited:          { ko: '관할기관 확인 필요', en: 'Official confirmation required', cls: 'wm-cov-verify' },
    final_agency_discretion: { ko: '관할기관 확인 필요', en: 'Official confirmation required', cls: 'wm-cov-verify' },
    unavailable:      { ko: '현재 근거 미확보', en: 'No current source coverage', cls: 'wm-cov-none' }
  };

  // Statuses whose sub-status materially changes the procedure/documents, so the
  // navigator asks a clarification before showing a *definitive* packet (Phase 2 /
  // acceptance #10). "I'm not sure" is always allowed -> proceed at parent level
  // with sections marked "official confirmation required".
  var MATERIALLY_AMBIGUOUS_FAMILIES = {
    'F-6': true, 'F-1': true, 'F-2': true, 'F-4': true, 'F-5': true,
    'G-1': true, 'D-2': true, 'E-7': true, 'D-4': true, 'D-8': true, 'D-9': true
  };

  // Records that are pilot programs / helper scenarios, not canonical primary
  // statuses. They remain selectable (no status crashes) but are grouped under
  // "프로그램/기타" and flagged so the UI can explain limited coverage.
  var NONCANONICAL_PROGRAM_CODES = {
    'K-STAR': true, 'REGION-S': true, 'YOUTH-STAY': true, 'D-4-2K': true
  };

  // =========================================================================
  // 2. Pure logic (DOM/network-free; exported for tests)
  // =========================================================================

  function packetTypeForProcedureKey(procedureKey) {
    if (!procedureKey) return null;
    if (Object.prototype.hasOwnProperty.call(PACKET_TYPE_BY_PROCEDURE_KEY, procedureKey)) {
      return PACKET_TYPE_BY_PROCEDURE_KEY[procedureKey];
    }
    // tolerate a public packet type passed directly
    for (var k in PACKET_TYPE_BY_PROCEDURE_KEY) {
      if (PACKET_TYPE_BY_PROCEDURE_KEY[k] === procedureKey) return procedureKey;
    }
    return null;
  }

  function parentCode(code) {
    var c = String(code || '').trim().toUpperCase();
    var parts = c.split('-');
    if (parts.length >= 3) return parts[0] + '-' + parts[1];
    return c;
  }

  function subCodesOf(record) {
    if (!record) return [];
    var subs = record.subCodes || record.subcodes || [];
    if (!Array.isArray(subs)) return [];
    return subs.map(function (s) {
      if (s && typeof s === 'object') {
        return { code: s.code || '', name: s.name || s.title || '' };
      }
      return { code: String(s), name: '' };
    }).filter(function (s) { return s.code; });
  }

  /*
   * Build a normalized, de-duplicated status catalog from visa_data records.
   * Each entry: { code, name, cat, isProgram, hasSubCodes, procedureKeys }.
   * procedureKeys = the procedures present in record.procedures (relevance set),
   * regardless of the `available` flag — every present procedure becomes a safe
   * selectable choice (available -> full/partial packet, otherwise coverage-limited).
   */
  function buildStatusCatalog(records) {
    var out = [];
    var seen = {};
    (records || []).forEach(function (r) {
      if (!r || !r.code) return;
      var code = String(r.code).trim().toUpperCase();
      if (seen[code]) return;
      seen[code] = true;
      var procs = (r.procedures && typeof r.procedures === 'object') ? r.procedures : {};
      var procedureKeys = PROCEDURE_ORDER.filter(function (k) {
        return Object.prototype.hasOwnProperty.call(procs, k);
      });
      out.push({
        code: code,
        name: r.name || '',
        cat: r.cat || '',
        dataBadge: r.dataBadge || '',
        isProgram: !!NONCANONICAL_PROGRAM_CODES[code],
        hasSubCodes: subCodesOf(r).length > 0,
        subCodes: subCodesOf(r),
        procedureKeys: procedureKeys,
        // availability per procedure (true when data marks it available)
        availability: PROCEDURE_ORDER.reduce(function (acc, k) {
          var p = procs[k];
          acc[k] = !!(p && typeof p === 'object' && p.available);
          return acc;
        }, {}),
        searchText: [code, r.name || '', (r.aliases || []).join(' '),
          (r.searchAliases || []).join(' ')].join(' ').toLowerCase()
      });
    });
    return out;
  }

  function filterStatusCatalog(catalog, query) {
    var q = String(query || '').trim().toLowerCase();
    if (!q) return catalog;
    // normalize "d2" -> "d-2" style queries
    var qNorm = q.replace(/\s+/g, '');
    return catalog.filter(function (s) {
      return s.searchText.indexOf(q) !== -1 ||
        s.code.toLowerCase().replace(/-/g, '').indexOf(qNorm.replace(/-/g, '')) !== -1;
    });
  }

  /*
   * Procedures to offer for a status. Returns ordered list of
   * { procedureKey, packetType, available }. If the status lists no procedures
   * at all (should not happen for canonical data), returns [] and the caller
   * shows a coverage-limited "no procedures" state — never a blank.
   */
  function proceduresForStatus(statusEntry) {
    if (!statusEntry) return [];
    return statusEntry.procedureKeys.map(function (k) {
      return {
        procedureKey: k,
        packetType: PACKET_TYPE_BY_PROCEDURE_KEY[k] || null,
        available: !!statusEntry.availability[k]
      };
    }).filter(function (p) { return p.packetType; });
  }

  /*
   * Does this (status, procedure) pair need a sub-status clarification before a
   * definitive packet? True only when the family is materially ambiguous AND the
   * status actually has sub-codes AND the procedure is document-bearing.
   */
  function needsSubStatusClarification(statusEntry, procedureKey) {
    if (!statusEntry || !statusEntry.hasSubCodes) return false;
    if (!MATERIALLY_AMBIGUOUS_FAMILIES[parentCode(statusEntry.code)]) return false;
    return ['registration', 'extension', 'statusChange', 'workplaceChange', 'visaIssuance']
      .indexOf(procedureKey) !== -1;
  }

  /*
   * Derive coverage from a packet. Prefers the backend coverageSummary; falls
   * back to deriving from sourceLens + document counts so the UI can never render
   * an empty packet as if it were complete.
   */
  function deriveCoverage(packet) {
    if (!packet) return { level: 'unavailable', isLimited: true, hasDocuments: false };
    if (packet.coverageSummary && typeof packet.coverageSummary === 'object') {
      return {
        level: packet.coverageSummary.level || 'limited',
        isLimited: packet.coverageSummary.isLimited !== false ? !!packet.coverageSummary.isLimited : false,
        hasDocuments: !!packet.coverageSummary.hasDocuments
      };
    }
    var level = (packet.sourceLens && packet.sourceLens.overallLevel) || 'limited';
    var count = countDocuments(packet);
    var coverageLevel = { source_confirmed: 'full', contextual: 'partial', limited: 'limited', unavailable: 'unavailable' }[level] || 'limited';
    return {
      level: coverageLevel,
      isLimited: (coverageLevel === 'limited' || coverageLevel === 'unavailable' || count === 0),
      hasDocuments: count > 0
    };
  }

  function countDocuments(packet) {
    var d = (packet && packet.documents) || {};
    var groups = ['commonDocs', 'requiredDocs', 'conditionalDocs', 'additionalDocs'];
    return groups.reduce(function (n, g) { return n + ((d[g] && d[g].length) || 0); }, 0);
  }

  /*
   * Group a packet's documents into the user-facing checklist groups (Phase 6).
   * Each item: { id, name, group, sourceBacked, isOfficialForm, conditionKo,
   *              coverage }. Stable id derived from group+name for local checklist.
   */
  function groupChecklistItems(packet) {
    var d = (packet && packet.documents) || {};
    var groupMap = [
      ['commonDocs', 'common'],
      ['requiredDocs', 'required'],
      ['conditionalDocs', 'conditional'],
      ['additionalDocs', 'additional']
    ];
    var items = [];
    groupMap.forEach(function (pair) {
      (d[pair[0]] || []).forEach(function (doc, i) {
        var name = doc.nameKo || doc.name || '';
        if (!name) return;
        items.push({
          id: pair[1] + ':' + slug(name) + ':' + i,
          name: name,
          noteKo: doc.noteKo || '',
          conditionKo: doc.conditionKo || '',
          group: pair[1],
          sourceBacked: !!doc.sourceBacked,
          isOfficialForm: !!doc.isOfficialForm,
          sourceRefs: doc.sourceRefs || [],
          coverage: doc.sourceBacked ? (bestRefLevel(doc.sourceRefs) || 'source_confirmed') : 'limited'
        });
      });
    });
    return items;
  }

  function bestRefLevel(refs) {
    var order = ['source_confirmed', 'contextual', 'limited', 'unavailable'];
    var best = null;
    (refs || []).forEach(function (r) {
      var lvl = r && r.evidenceLevel;
      if (order.indexOf(lvl) !== -1 && (best === null || order.indexOf(lvl) < order.indexOf(best))) best = lvl;
    });
    return best;
  }

  function slug(s) {
    return String(s).toLowerCase().replace(/[^a-z0-9가-힣]+/gi, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  }

  function sourceCoverageLabel(level, locale) {
    var c = SOURCE_COVERAGE[level] || SOURCE_COVERAGE.limited;
    return (locale === 'en') ? c.en : c.ko;
  }
  function sourceCoverageClass(level) {
    var c = SOURCE_COVERAGE[level] || SOURCE_COVERAGE.limited;
    return c.cls;
  }

  /*
   * Build the SAFE context object sent to /api/ask for an AI follow-up. Contains
   * ONLY categorical, non-personal identifiers. NEVER the checklist, free-text
   * situation notes, or any personal identifier. The user's typed question is
   * passed separately by the host (it is the user's own question about the packet).
   */
  function buildAiFollowupContext(state, packet) {
    var cov = deriveCoverage(packet);
    return {
      domain: 'waymaker_packet_followup',
      locale: state.locale || 'ko',
      location: state.location || null,           // categorical: in_korea | outside | unsure
      statusCode: state.statusCode || null,
      exactStatusCode: state.exactStatusCode || state.statusCode || null,
      subStatusKnown: !!state.subStatusKnown,
      procedureKey: state.procedureKey || null,
      packetType: packet ? packet.packetType : null,
      packetId: packet ? packet.packetId : null,
      coverageLevel: cov.level,
      coverageLimited: cov.isLimited
    };
  }

  // =========================================================================
  // 3. i18n strings (KO/EN) — navigator chrome only. Exact product copy.
  // =========================================================================
  var STRINGS = {
    ko: {
      title: 'Waymaker - 한국 체류 절차 길찾기',
      subtitle: '공식 출처를 바탕으로 내 절차, 서류, 예약, 다음 행동을 정리합니다.',
      empty: '질문부터 쓰지 않아도 됩니다. 현재 체류자격과 하려는 일을 선택하세요.',
      start: '내 상황 선택하기',
      back: '이전',
      next: '다음',
      restart: '처음부터',
      dontKnow: '잘 모르겠어요',
      stepLanguage: '언어를 선택하세요',
      stepLocation: '지금 어디에 계신가요?',
      locIn: '한국 내', locOut: '한국 밖', locUnsure: '잘 모르겠어요 / 상황에 따라 달라요',
      stepStatus: '현재 체류자격을 선택하세요',
      statusSearchPlaceholder: '체류자격 코드나 이름으로 검색 (예: D-2, 유학, E-7)',
      statusUnknown: '내 체류자격을 모르겠어요',
      statusFirstEntry: '아직 비자가 없어요 / 해외에서 최초 입국·사증발급 준비 중',
      noStatusResults: '검색 결과가 없습니다. 코드(D-2 등)나 한글 명칭으로 다시 검색해 보세요.',
      programGroup: '프로그램 / 시범사업 (공식 근거 제한적)',
      stepProcedure: '어떤 절차가 필요하신가요?',
      procedureLimitedHint: '공식 근거 제한',
      stepSubStatus: '어떤 세부 유형에 해당하나요?',
      subStatusHelp: '세부 유형에 따라 서류와 기준이 달라질 수 있습니다. 확실하지 않으면 "잘 모르겠어요"를 선택하세요.',
      generating: '공식 근거 기반 절차 패킷을 준비하는 중…',
      // packet section titles
      secProcedure: '나의 절차', secNext: '지금 할 일', secApplicability: '적용 가능성',
      secDocs: '준비 서류', secConditional: '상황별 추가서류', secWhere: '발급처·준비 방법',
      secTiming: '기한·주의사항', secFees: '수수료', secChannel: 'HiKorea / 방문 경로',
      secJurisdiction: '관할', secCoverage: '공식 근거 범위', secVerify: '확인 필요 항목',
      // checklist groups
      grpCommon: '공통 서류', grpRequired: '필수 서류', grpConditional: '상황별 서류',
      grpAdditional: '추가 서류', grpVerify: '관할기관 확인', grpNone: '근거 미확보',
      checklistTitle: '서류 체크리스트', checklistHint: '체크 상태는 이 브라우저에만 저장됩니다.',
      checklistReset: '초기화', checklistCopy: '복사', checklistPrint: '인쇄/내보내기',
      checklistCopied: '체크리스트를 클립보드에 복사했습니다.',
      officialForm: '공식 서식',
      coverageLimitedTitle: '공식 근거가 제한된 절차입니다',
      coverageLimited: '현재 이 절차에 대해 공식 근거가 충분히 구조화되어 있지 않습니다. 확인되지 않은 서류, 수수료, 기한, 예약 경로는 임의로 안내하지 않습니다. HiKorea, 1345 또는 관할 출입국기관에서 최종 확인하세요.',
      whatWeCanSay: 'Paradiso가 안전하게 안내할 수 있는 정보',
      whatWeCannot: 'Paradiso가 확인할 수 없는 정보',
      officialChannels: '공식 확인 경로',
      call1345: '1345 (외국인종합안내센터)',
      hikoreaCta: 'HiKorea 예약 경로 확인',
      aiFollowupCta: '이 패킷에서 헷갈리는 점 묻기',
      aiFollowupPlaceholder: '이 패킷에서 이해되지 않는 점을 물어보세요. 예: 재정서류가 면제될 수 있나요?',
      aiPrivacyNote: '개인정보(이름, 여권·외국인등록번호, 주소, 전화번호 등)는 입력하지 마세요. 이 도우미는 패킷을 설명할 뿐 새로운 공식 요건을 만들지 않습니다.',
      aiSend: '질문하기',
      noDocs: '이 절차의 공식 서류 목록이 아직 구조화되지 않았습니다.',
      verifyIntro: '아래 항목은 공식 근거로 확정 표시할 수 없으므로 관할기관/1345/HiKorea에서 확인하세요.',
      generatedOn: '생성일',
      sourceVersion: '근거 버전',
      disclaimerPrint: '최종 확인은 HiKorea, 1345 또는 관할 출입국·외국인관서에서 하셔야 합니다.',
      langName: '한국어',
      operatorDiag: '진단(운영자)'
    },
    en: {
      title: 'Waymaker - Korea Immigration Procedure Navigator',
      subtitle: 'Turn your status and situation into a source-backed procedure, checklist, booking path, and next action.',
      empty: 'You do not need to write a question. Start with your current status and what you need to do.',
      start: 'Choose my situation',
      back: 'Back',
      next: 'Next',
      restart: 'Start over',
      dontKnow: "I'm not sure",
      stepLanguage: 'Choose your language',
      stepLocation: 'Where are you right now?',
      locIn: 'In Korea', locOut: 'Outside Korea', locUnsure: 'Not sure / it depends',
      stepStatus: 'Choose your current status',
      statusSearchPlaceholder: 'Search by code or name (e.g. D-2, study, E-7)',
      statusUnknown: "I don't know my status",
      statusFirstEntry: "I don't have a visa yet / preparing first entry or visa issuance from abroad",
      noStatusResults: 'No matches. Try a code (e.g. D-2) or the Korean status name.',
      programGroup: 'Programs / pilots (limited official coverage)',
      stepProcedure: 'What do you need to do?',
      procedureLimitedHint: 'Limited source coverage',
      stepSubStatus: 'Which sub-type applies to you?',
      subStatusHelp: 'Documents and criteria can differ by sub-type. If unsure, choose "I\'m not sure".',
      generating: 'Preparing your source-backed procedure packet…',
      secProcedure: 'My procedure', secNext: 'What to do next', secApplicability: 'Applicability',
      secDocs: 'Documents to prepare', secConditional: 'Conditional documents', secWhere: 'Where to get each document',
      secTiming: 'Timing and risks', secFees: 'Fees', secChannel: 'HiKorea / visit channel',
      secJurisdiction: 'Jurisdiction', secCoverage: 'Official-source coverage', secVerify: 'Items to verify',
      grpCommon: 'Common documents', grpRequired: 'Required documents', grpConditional: 'Conditional documents',
      grpAdditional: 'Additional documents', grpVerify: 'Verify with office', grpNone: 'Not enough source coverage',
      checklistTitle: 'Document checklist', checklistHint: 'Your checks are saved only in this browser.',
      checklistReset: 'Reset', checklistCopy: 'Copy', checklistPrint: 'Print / export',
      checklistCopied: 'Checklist copied to clipboard.',
      officialForm: 'Official form',
      coverageLimitedTitle: 'This procedure has limited official-source coverage',
      coverageLimited: 'Paradiso does not yet have enough structured official-source coverage for this procedure. It will not guess documents, fees, deadlines, or booking paths. Please confirm with HiKorea, 1345, or the competent immigration office.',
      whatWeCanSay: 'What Paradiso can safely say',
      whatWeCannot: 'What Paradiso cannot confirm',
      officialChannels: 'Where to confirm officially',
      call1345: '1345 (Immigration Contact Center)',
      hikoreaCta: 'Check my HiKorea booking path',
      aiFollowupCta: 'Ask about this packet',
      aiFollowupPlaceholder: 'Ask about this packet. Example: Could the financial-evidence item be waived?',
      aiPrivacyNote: 'Do not enter personal identifiers (name, passport/ARC number, address, phone). This helper only explains the packet; it does not create new official requirements.',
      aiSend: 'Ask',
      noDocs: 'The official document list for this procedure is not yet structured.',
      verifyIntro: 'The items below cannot be confirmed from official sources here. Confirm with the competent office, 1345, or HiKorea.',
      generatedOn: 'Generated',
      sourceVersion: 'Source version',
      disclaimerPrint: 'Final confirmation must be made with HiKorea, 1345, or the competent immigration office.',
      langName: 'English',
      operatorDiag: 'Diagnostics (operator)'
    }
  };

  var PROCEDURE_LABELS = {
    visaIssuance:           { ko: '사증발급 / 최초 입국', en: 'Visa issuance / first entry' },
    registration:           { ko: '외국인등록', en: 'Alien registration' },
    extension:              { ko: '체류기간 연장', en: 'Extension of stay' },
    statusChange:           { ko: '체류자격 변경', en: 'Change of status' },
    statusGrant:            { ko: '체류자격 부여', en: 'Grant of status' },
    workplaceChange:        { ko: '근무처 변경·추가', en: 'Workplace change / addition' },
    activitiesOutsideStatus:{ ko: '체류자격외 활동', en: 'Activities outside status' },
    reentry:                { ko: '재입국허가', en: 'Re-entry permit' }
  };

  function t(locale, key) {
    var pack = STRINGS[locale] || STRINGS.ko;
    return (pack[key] != null) ? pack[key] : (STRINGS.ko[key] != null ? STRINGS.ko[key] : key);
  }
  function procedureLabel(key, locale) {
    var l = PROCEDURE_LABELS[key];
    if (!l) return key;
    return (locale === 'en') ? l.en : l.ko;
  }

  // =========================================================================
  // 4. Analytics — privacy-safe, categorical-only, no-op by default.
  //    Never logs prompts, free text, IDs, or checklist contents.
  // =========================================================================
  var ALLOWED_EVENTS = {
    waymaker_flow_started: 1, waymaker_language_selected: 1, waymaker_location_selected: 1,
    waymaker_status_selected: 1, waymaker_substatus_selected: 1, waymaker_procedure_selected: 1,
    waymaker_packet_rendered: 1, waymaker_packet_limited: 1, waymaker_checklist_interacted: 1,
    waymaker_hikorea_opened: 1, waymaker_ai_followup_opened: 1, waymaker_fallback_used: 1,
    waymaker_source_coverage_level: 1
  };
  // Only these categorical property keys may be attached to an event.
  var ALLOWED_PROP_KEYS = {
    locale: 1, location: 1, statusFamily: 1, procedureKey: 1, packetType: 1,
    coverageLevel: 1, subStatusKnown: 1, isProgram: 1
  };
  function makeAnalytics(sink) {
    return function track(event, props) {
      if (!ALLOWED_EVENTS[event]) return;
      var safe = {};
      if (props) {
        for (var k in props) {
          if (ALLOWED_PROP_KEYS[k] && (typeof props[k] === 'string' || typeof props[k] === 'boolean')) {
            safe[k] = props[k];
          }
        }
      }
      try {
        if (typeof sink === 'function') sink(event, safe);
        else if (global.PARADISO_ANALYTICS && typeof global.PARADISO_ANALYTICS.track === 'function') {
          global.PARADISO_ANALYTICS.track(event, safe);
        }
      } catch (e) { /* analytics must never break the flow */ }
    };
  }

  // =========================================================================
  // 5. Browser UI controller (only runs when document is present)
  // =========================================================================
  function createNavigator(options) {
    options = options || {};
    if (typeof document === 'undefined') {
      throw new Error('createNavigator requires a DOM environment');
    }
    var doc = document;
    var root = options.root;
    var apiBase = (options.apiBase || '').replace(/\/$/, '');
    var getRecords = options.getRecords; // async () => records[]
    var onAskFollowup = options.onAskFollowup; // (contextObj, questionText) => Promise|void
    var openHiKorea = options.openHiKorea; // (statusCode, procedureKey, packetType) => void
    var track = makeAnalytics(options.analytics);
    var CHECKLIST_NS = 'paradiso_waymaker_checklist_v1';
    var LOCALE_KEY = 'paradiso_waymaker_locale';

    var catalog = null;
    var state = {
      step: 'intro',
      locale: resolveInitialLocale(),
      location: null,
      statusEntry: null,
      statusCode: null,
      exactStatusCode: null,
      subStatusKnown: false,
      procedureKey: null,
      packet: null
    };

    function resolveInitialLocale() {
      // Honor a ?lang=ko|en deep-link first (preserves the legacy ai.html URL
      // parameter — e.g. index.html's handoff FAB passes &lang=en).
      try {
        if (global.location && global.URLSearchParams) {
          var urlLang = (new global.URLSearchParams(global.location.search).get('lang') || '').toLowerCase().slice(0, 2);
          if (urlLang === 'ko' || urlLang === 'en') return urlLang;
        }
      } catch (e) {}
      try {
        var stored = global.localStorage && global.localStorage.getItem(LOCALE_KEY);
        if (stored === 'ko' || stored === 'en') return stored;
      } catch (e) {}
      if (global.PARADISO_LANG === 'en' || global.PARADISO_LANG === 'ko') return global.PARADISO_LANG;
      var htmlLang = (doc.documentElement.getAttribute('lang') || '').slice(0, 2);
      if (htmlLang === 'en') return 'en';
      return 'ko';
    }
    function persistLocale() {
      try { global.localStorage && global.localStorage.setItem(LOCALE_KEY, state.locale); } catch (e) {}
    }
    function L(key) { return t(state.locale, key); }

    // ---- tiny DOM helper -------------------------------------------------
    function h(tag, attrs, children) {
      var node = doc.createElement(tag);
      if (attrs) {
        for (var k in attrs) {
          if (k === 'class') node.className = attrs[k];
          else if (k === 'text') node.textContent = attrs[k];
          else if (k === 'html') node.innerHTML = attrs[k];
          else if (k.indexOf('on') === 0 && typeof attrs[k] === 'function') node.addEventListener(k.slice(2), attrs[k]);
          else if (k === 'aria' && attrs[k]) { for (var a in attrs[k]) node.setAttribute('aria-' + a, attrs[k][a]); }
          else if (attrs[k] != null && attrs[k] !== false) node.setAttribute(k, attrs[k]);
        }
      }
      (children || []).forEach(function (c) {
        if (c == null) return;
        node.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c);
      });
      return node;
    }
    function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

    // ---- checklist local store ------------------------------------------
    function checklistKey() {
      return CHECKLIST_NS + ':' + (state.exactStatusCode || state.statusCode) + ':' + state.procedureKey;
    }
    function loadChecklist() {
      try { return JSON.parse(global.localStorage.getItem(checklistKey()) || '{}') || {}; } catch (e) { return {}; }
    }
    function saveChecklist(map) {
      try { global.localStorage.setItem(checklistKey(), JSON.stringify(map)); } catch (e) {}
    }

    // ---- network: deterministic packet ----------------------------------
    function fetchPacket(statusCode, procedureKey) {
      var url = apiBase + '/api/procedure-packet?status=' + encodeURIComponent(statusCode) +
        '&procedure=' + encodeURIComponent(procedureKey) + '&locale=' + encodeURIComponent(state.locale);
      return fetch(url, { cache: 'no-store' }).then(function (res) {
        if (!res.ok) {
          return res.json().catch(function () { return {}; }).then(function (body) {
            // 400 unsupported / 503 unavailable -> synthesize a safe coverage-limited shell
            return makeCoverageLimitedShell(statusCode, procedureKey, body);
          });
        }
        return res.json();
      }).catch(function () {
        return makeCoverageLimitedShell(statusCode, procedureKey, null);
      });
    }

    // A front-end safe shell when the endpoint is unreachable/unsupported. It
    // fabricates NOTHING — only labels the gap and points to official channels.
    function makeCoverageLimitedShell(statusCode, procedureKey, body) {
      var packetType = packetTypeForProcedureKey(procedureKey);
      return {
        packetId: 'shell.' + statusCode + '.' + (packetType || 'unknown'),
        packetType: packetType || 'unknown',
        statusCode: statusCode,
        exactStatusCode: statusCode,
        titleKo: (PROCEDURE_LABELS[procedureKey] && PROCEDURE_LABELS[procedureKey].ko) || '절차',
        titleEn: (PROCEDURE_LABELS[procedureKey] && PROCEDURE_LABELS[procedureKey].en) || 'Procedure',
        documents: { commonDocs: [], requiredDocs: [], conditionalDocs: [], additionalDocs: [], sourceBacked: false },
        fees: { items: [], sourceBacked: false },
        channels: {},
        sourceLens: { overallLevel: 'unavailable' },
        coverageSummary: { level: 'unavailable', isLimited: true, hasDocuments: false },
        _shell: true
      };
    }

    // =====================================================================
    // Render: dispatch on state.step
    // =====================================================================
    function render() {
      if (!root) return;
      clear(root);
      root.appendChild(renderHeader());
      var body = h('div', { class: 'wm-body' });
      switch (state.step) {
        case 'intro': body.appendChild(renderIntro()); break;
        case 'language': body.appendChild(renderLanguage()); break;
        case 'location': body.appendChild(renderLocation()); break;
        case 'status': body.appendChild(renderStatus()); break;
        case 'procedure': body.appendChild(renderProcedure()); break;
        case 'subStatus': body.appendChild(renderSubStatus()); break;
        case 'loading': body.appendChild(renderLoading()); break;
        case 'packet': body.appendChild(renderPacket()); break;
        default: body.appendChild(renderIntro());
      }
      root.appendChild(body);
      // focus management: move focus to the step heading for keyboard/AT users
      var heading = root.querySelector('[data-wm-focus]');
      if (heading && state.step !== 'intro') { try { heading.focus(); } catch (e) {} }
    }

    function renderHeader() {
      var steps = ['language', 'location', 'status', 'procedure', 'subStatus'];
      var idx = steps.indexOf(state.step);
      var showProgress = idx !== -1;
      var langBtn = h('button', {
        class: 'wm-lang-toggle', type: 'button',
        aria: { label: state.locale === 'en' ? 'Language: English' : '언어: 한국어' },
        onclick: function () { setLocale(state.locale === 'en' ? 'ko' : 'en'); }
      }, [state.locale === 'en' ? 'EN' : '한']);
      var head = h('div', { class: 'wm-head' }, [
        h('div', { class: 'wm-head-titles' }, [
          h('div', { class: 'wm-title', text: L('title') }),
          h('div', { class: 'wm-subtitle', text: L('subtitle') })
        ]),
        langBtn
      ]);
      if (showProgress) {
        var pct = Math.round(((idx + 1) / steps.length) * 100);
        head.appendChild(h('div', {
          class: 'wm-progress', role: 'progressbar',
          'aria-valuenow': String(idx + 1), 'aria-valuemin': '1', 'aria-valuemax': String(steps.length),
          aria: { label: (state.locale === 'en' ? 'Step ' : '단계 ') + (idx + 1) + '/' + steps.length }
        }, [h('span', { class: 'wm-progress-bar', style: 'width:' + pct + '%' })]));
      }
      return head;
    }

    function renderIntro() {
      track('waymaker_flow_started', { locale: state.locale });
      return h('section', { class: 'wm-step wm-intro' }, [
        h('p', { class: 'wm-empty', text: L('empty') }),
        h('button', {
          class: 'wm-btn wm-btn-primary wm-btn-lg', type: 'button',
          onclick: function () { goto('language'); }
        }, [L('start')])
      ]);
    }

    function renderLanguage() {
      return stepShell('language', L('stepLanguage'), [
        chipGrid([
          chip('한국어', state.locale === 'ko', function () { setLocale('ko'); track('waymaker_language_selected', { locale: 'ko' }); goto('location'); }),
          chip('English', state.locale === 'en', function () { setLocale('en'); track('waymaker_language_selected', { locale: 'en' }); goto('location'); })
        ])
      ], null);
    }

    function renderLocation() {
      function pick(v) { state.location = v; track('waymaker_location_selected', { locale: state.locale, location: v }); goto('status'); }
      return stepShell('location', L('stepLocation'), [
        chipGrid([
          chip(L('locIn'), state.location === 'in_korea', function () { pick('in_korea'); }),
          chip(L('locOut'), state.location === 'outside', function () { pick('outside'); }),
          chip(L('locUnsure'), state.location === 'unsure', function () { pick('unsure'); })
        ])
      ], 'language');
    }

    function renderStatus() {
      var resultsWrap = h('div', { class: 'wm-status-results', role: 'listbox', aria: { label: L('stepStatus') } });
      var input = h('input', {
        class: 'wm-search', type: 'search', inputmode: 'search',
        placeholder: L('statusSearchPlaceholder'),
        aria: { label: L('statusSearchPlaceholder') },
        oninput: function () { renderResults(input.value); }
      });
      function renderResults(q) {
        clear(resultsWrap);
        // special quick-paths first (only when query empty)
        if (!q) {
          resultsWrap.appendChild(specialRow(L('statusFirstEntry'), function () { chooseFirstEntry(); }));
          resultsWrap.appendChild(specialRow(L('statusUnknown'), function () { chooseUnknownStatus(); }));
        }
        var matches = filterStatusCatalog(catalog || [], q);
        if (!matches.length) {
          resultsWrap.appendChild(h('p', { class: 'wm-muted', text: L('noStatusResults') }));
          return;
        }
        var canon = matches.filter(function (m) { return !m.isProgram; });
        var prog = matches.filter(function (m) { return m.isProgram; });
        canon.forEach(function (m) { resultsWrap.appendChild(statusRow(m)); });
        if (prog.length) {
          resultsWrap.appendChild(h('div', { class: 'wm-group-label', text: L('programGroup') }));
          prog.forEach(function (m) { resultsWrap.appendChild(statusRow(m)); });
        }
      }
      function statusRow(m) {
        return h('button', {
          class: 'wm-status-row', type: 'button', role: 'option',
          onclick: function () { chooseStatus(m); }
        }, [
          h('span', { class: 'wm-status-code', text: m.code }),
          h('span', { class: 'wm-status-name', text: m.name })
        ]);
      }
      function specialRow(label, cb) {
        return h('button', { class: 'wm-status-row wm-status-special', type: 'button', role: 'option', onclick: cb },
          [h('span', { class: 'wm-status-name', text: label })]);
      }
      var shell = stepShell('status', L('stepStatus'), [input, resultsWrap], 'location');
      renderResults('');
      return shell;
    }

    function renderProcedure() {
      var entry = state.statusEntry;
      var procs = proceduresForStatus(entry);
      var rows = procs.map(function (p) {
        var children = [h('span', { class: 'wm-proc-name', text: procedureLabel(p.procedureKey, state.locale) })];
        if (!p.available) children.push(h('span', { class: 'wm-proc-hint', text: L('procedureLimitedHint') }));
        return h('button', {
          class: 'wm-proc-row' + (p.available ? '' : ' wm-proc-limited'), type: 'button',
          onclick: function () { chooseProcedure(p.procedureKey); }
        }, children);
      });
      if (!rows.length) {
        rows.push(h('p', { class: 'wm-muted', text: L('coverageLimited') }));
      }
      var titleSuffix = entry ? (entry.code + ' · ' + entry.name) : '';
      return stepShell('procedure', L('stepProcedure'), [
        h('p', { class: 'wm-context-line', text: titleSuffix }),
        h('div', { class: 'wm-proc-list' }, rows)
      ], 'status');
    }

    function renderSubStatus() {
      var entry = state.statusEntry;
      var subs = (entry && entry.subCodes) || [];
      var rows = subs.map(function (s) {
        return h('button', {
          class: 'wm-status-row', type: 'button', role: 'option',
          onclick: function () { chooseSubStatus(s.code); }
        }, [
          h('span', { class: 'wm-status-code', text: s.code }),
          h('span', { class: 'wm-status-name', text: s.name })
        ]);
      });
      rows.push(h('button', {
        class: 'wm-status-row wm-status-special', type: 'button', role: 'option',
        onclick: function () { chooseSubStatus(null); }
      }, [h('span', { class: 'wm-status-name', text: L('dontKnow') })]));
      return stepShell('subStatus', L('stepSubStatus'), [
        h('p', { class: 'wm-muted', text: L('subStatusHelp') }),
        h('div', { class: 'wm-status-results', role: 'listbox' }, rows)
      ], 'procedure');
    }

    function renderLoading() {
      return h('section', { class: 'wm-step wm-loading' }, [
        h('div', { class: 'wm-spinner', aria: { hidden: 'true' } }),
        h('p', { class: 'wm-muted', tabindex: '-1', 'data-wm-focus': '1', text: L('generating') })
      ]);
    }

    // ---- step shell with heading + back ---------------------------------
    function stepShell(stepName, heading, children, backTo) {
      var top = [
        h('h2', { class: 'wm-step-heading', tabindex: '-1', 'data-wm-focus': '1', text: heading })
      ];
      var nodes = top.concat(children);
      var nav = h('div', { class: 'wm-step-nav' }, [
        backTo ? h('button', { class: 'wm-btn wm-btn-ghost', type: 'button', onclick: function () { goto(backTo); } }, [L('back')]) : null,
        h('button', { class: 'wm-btn wm-btn-ghost wm-btn-restart', type: 'button', onclick: function () { restart(); } }, [L('restart')])
      ]);
      nodes.push(nav);
      return h('section', { class: 'wm-step' }, nodes);
    }
    function chipGrid(chips) { return h('div', { class: 'wm-chip-grid' }, chips); }
    function chip(label, selected, cb) {
      return h('button', {
        class: 'wm-chip' + (selected ? ' wm-chip-on' : ''), type: 'button',
        aria: { pressed: selected ? 'true' : 'false' }, onclick: cb
      }, [label]);
    }

    // =====================================================================
    // Transitions
    // =====================================================================
    function setLocale(loc) { state.locale = loc; persistLocale(); render(); }
    function goto(step) { state.step = step; render(); }
    function restart() {
      state.location = null; state.statusEntry = null; state.statusCode = null;
      state.exactStatusCode = null; state.subStatusKnown = false; state.procedureKey = null; state.packet = null;
      goto('language');
    }
    function chooseStatus(m) {
      state.statusEntry = m; state.statusCode = m.code; state.exactStatusCode = m.code; state.subStatusKnown = false;
      track('waymaker_status_selected', { locale: state.locale, statusFamily: parentCode(m.code), isProgram: !!m.isProgram });
      goto('procedure');
    }
    function chooseFirstEntry() {
      // Route first-entry to the status step with visa issuance pre-intent: pick a
      // status, then visaIssuance procedure. Here we just keep status selection,
      // but bias toward visaIssuance later. For safety we still require a status.
      state.location = 'outside';
      goto('status'); // user still selects which status they're applying for
    }
    function chooseUnknownStatus() {
      // Safe handling: cannot fabricate a status. Guide to official confirmation.
      state.statusEntry = null; state.statusCode = null; state.exactStatusCode = null;
      state.procedureKey = null;
      track('waymaker_fallback_used', { locale: state.locale });
      state.packet = makeUnknownStatusShell();
      goto('packet');
    }
    function makeUnknownStatusShell() {
      return {
        packetId: 'shell.unknown-status', packetType: 'unknown',
        statusCode: '', exactStatusCode: '',
        titleKo: '체류자격 확인 필요', titleEn: 'Status needs confirmation',
        documents: { commonDocs: [], requiredDocs: [], conditionalDocs: [], additionalDocs: [], sourceBacked: false },
        fees: { items: [], sourceBacked: false }, channels: {},
        sourceLens: { overallLevel: 'unavailable' },
        coverageSummary: { level: 'unavailable', isLimited: true, hasDocuments: false },
        _unknownStatus: true
      };
    }
    function chooseProcedure(procedureKey) {
      state.procedureKey = procedureKey;
      track('waymaker_procedure_selected', { locale: state.locale, statusFamily: parentCode(state.statusCode), procedureKey: procedureKey });
      if (needsSubStatusClarification(state.statusEntry, procedureKey)) {
        goto('subStatus');
      } else {
        generatePacket();
      }
    }
    function chooseSubStatus(subCode) {
      if (subCode) { state.exactStatusCode = subCode; state.subStatusKnown = true; }
      else { state.exactStatusCode = state.statusCode; state.subStatusKnown = false; }
      track('waymaker_substatus_selected', { locale: state.locale, statusFamily: parentCode(state.statusCode), subStatusKnown: !!subCode });
      generatePacket();
    }
    function generatePacket() {
      goto('loading');
      var code = state.exactStatusCode || state.statusCode;
      fetchPacket(code, state.procedureKey).then(function (packet) {
        state.packet = packet;
        var cov = deriveCoverage(packet);
        track('waymaker_packet_rendered', { locale: state.locale, statusFamily: parentCode(state.statusCode), procedureKey: state.procedureKey, packetType: packet.packetType, coverageLevel: cov.level });
        track('waymaker_source_coverage_level', { coverageLevel: cov.level });
        if (cov.isLimited) track('waymaker_packet_limited', { locale: state.locale, procedureKey: state.procedureKey, coverageLevel: cov.level });
        goto('packet');
      });
    }

    // =====================================================================
    // Packet rendering (Action Packet + coverage-limited) — see render-packet.js
    // The renderer is attached below to keep this file navigable.
    // =====================================================================
    function renderPacket() { return PacketView.render(ctx()); }

    // context handed to the packet view
    function ctx() {
      return {
        h: h, clear: clear, L: L, locale: state.locale, state: state, packet: state.packet,
        track: track, openHiKorea: openHiKorea, onAskFollowup: onAskFollowup,
        loadChecklist: loadChecklist, saveChecklist: saveChecklist, restart: restart,
        backToProcedure: function () { goto('procedure'); }
      };
    }

    // ---- boot ------------------------------------------------------------
    function mount() {
      Promise.resolve(typeof getRecords === 'function' ? getRecords() : []).then(function (records) {
        catalog = buildStatusCatalog(records || []);
        render();
      }).catch(function () { catalog = []; render(); });
      return controller;
    }

    var controller = {
      mount: mount,
      getState: function () { return state; },
      getCatalog: function () { return catalog; },
      _render: render,
      _goto: goto
    };
    return controller;
  }

  // =========================================================================
  // 6. PacketView — renders the 12 Action Packet sections + coverage-limited.
  //    Kept as a separate object operating on the controller ctx so the file
  //    stays modular without a build step.
  // =========================================================================
  var PacketView = {
    render: function (c) {
      var packet = c.packet;
      var cov = deriveCoverage(packet);
      var wrap = c.h('section', { class: 'wm-packet' + (cov.isLimited ? ' wm-packet-limited' : '') }, []);

      // Section 1 — My procedure (always first)
      wrap.appendChild(this.sectionProcedure(c, packet));
      // unknown-status special case
      if (packet._unknownStatus) {
        wrap.appendChild(this.coverageLimitedCard(c, packet, true));
        wrap.appendChild(this.footerActions(c, packet, cov));
        return wrap;
      }
      // Section 2 — What to do next (always near top)
      wrap.appendChild(this.sectionNext(c, packet, cov));

      if (cov.isLimited) {
        wrap.appendChild(this.coverageLimitedCard(c, packet, false));
      }

      // Accordions for the rest (progressive disclosure on mobile)
      var acc = c.h('div', { class: 'wm-accordions' }, []);
      acc.appendChild(this.sectionApplicability(c, packet));
      acc.appendChild(this.sectionDocuments(c, packet, cov));     // 4 + 5 + checklist + 6
      acc.appendChild(this.sectionTiming(c, packet));             // 7
      acc.appendChild(this.sectionFees(c, packet));               // 8
      acc.appendChild(this.sectionChannel(c, packet));            // 9
      acc.appendChild(this.sectionJurisdiction(c, packet));       // 10
      acc.appendChild(this.sectionCoverage(c, packet, cov));      // 11
      acc.appendChild(this.sectionVerify(c, packet, cov));        // 12
      wrap.appendChild(acc);

      wrap.appendChild(this.footerActions(c, packet, cov));
      return wrap;
    },

    coverageBadge: function (c, level) {
      return c.h('span', {
        class: 'wm-cov-badge ' + sourceCoverageClass(level),
        text: sourceCoverageLabel(level, c.locale)
      });
    },

    sectionProcedure: function (c, packet) {
      var title = c.locale === 'en' ? (packet.titleEn || packet.titleKo) : (packet.titleKo || packet.titleEn);
      var cov = deriveCoverage(packet);
      return c.h('div', { class: 'wm-card wm-card-hero' }, [
        c.h('div', { class: 'wm-kicker', text: c.L('secProcedure') }),
        c.h('h2', { class: 'wm-packet-title', tabindex: '-1', 'data-wm-focus': '1' }, [
          (packet.statusCode ? c.h('span', { class: 'wm-code-chip', text: packet.statusCode }) : null),
          c.h('span', { text: ' ' + title })
        ]),
        packet.userScenarioSummaryKo ? c.h('p', { class: 'wm-hero-summary', text: packet.userScenarioSummaryKo }) : null,
        this.coverageBadge(c, cov.level)
      ]);
    },

    sectionNext: function (c, packet, cov) {
      var actions = packet.nextActions || [];
      var list = c.h('ol', { class: 'wm-next-list' }, actions.map(function (a) {
        return c.h('li', { text: a });
      }));
      return c.h('div', { class: 'wm-card wm-card-next' }, [
        c.h('div', { class: 'wm-kicker', text: c.L('secNext') }),
        actions.length ? list : c.h('p', { class: 'wm-muted', text: c.L('coverageLimited') })
      ]);
    },

    coverageLimitedCard: function (c, packet, isUnknownStatus) {
      var canSay = [];
      if (!isUnknownStatus) {
        // safe statements: the procedure name + the official channels.
        canSay.push(c.L('secProcedure') + ': ' + (c.locale === 'en' ? (packet.titleEn || packet.titleKo) : packet.titleKo));
      }
      var channels = c.h('ul', { class: 'wm-channel-list' }, [
        c.h('li', {}, [c.h('a', { href: 'https://www.hikorea.go.kr', target: '_blank', rel: 'noopener', text: 'HiKorea (hikorea.go.kr)' })]),
        c.h('li', { text: c.L('call1345') })
      ]);
      return c.h('div', { class: 'wm-card wm-card-warn', role: 'note' }, [
        c.h('div', { class: 'wm-warn-title', text: c.L('coverageLimitedTitle') }),
        c.h('p', { class: 'wm-warn-body', text: c.L('coverageLimited') }),
        c.h('div', { class: 'wm-warn-channels' }, [
          c.h('div', { class: 'wm-subhead', text: c.L('officialChannels') }),
          channels
        ])
      ]);
    },

    accordion: function (c, titleKey, level, bodyNodes, openByDefault) {
      var bodyId = 'wm-acc-' + slug(titleKey) + '-' + Math.floor(Math.random() * 1e6);
      var body = c.h('div', { class: 'wm-acc-body', id: bodyId }, bodyNodes);
      var btn = c.h('button', {
        class: 'wm-acc-head', type: 'button',
        'aria-expanded': openByDefault ? 'true' : 'false', 'aria-controls': bodyId,
        onclick: function () {
          var open = btn.getAttribute('aria-expanded') === 'true';
          btn.setAttribute('aria-expanded', open ? 'false' : 'true');
          wrap.classList.toggle('wm-acc-open', !open);
        }
      }, [
        c.h('span', { class: 'wm-acc-title', text: c.L(titleKey) }),
        level ? this.coverageBadge(c, level) : null,
        c.h('span', { class: 'wm-acc-chev', aria: { hidden: 'true' }, text: '⌄' })
      ]);
      var wrap = c.h('div', { class: 'wm-acc' + (openByDefault ? ' wm-acc-open' : '') }, [btn, body]);
      return wrap;
    },

    sectionApplicability: function (c, packet) {
      var a = packet.applicability || {};
      var nodes = [];
      if (a.summaryKo) nodes.push(c.h('p', { text: a.summaryKo }));
      (a.limitations || []).forEach(function (lim) { nodes.push(c.h('p', { class: 'wm-muted', text: lim })); });
      if (!nodes.length) nodes.push(c.h('p', { class: 'wm-muted', text: c.L('verifyIntro') }));
      return this.accordion(c, 'secApplicability', null, nodes, false);
    },

    sectionDocuments: function (c, packet, cov) {
      var items = groupChecklistItems(packet);
      var self = this;
      var body = c.h('div', { class: 'wm-docs' }, []);
      if (!items.length) {
        body.appendChild(c.h('p', { class: 'wm-muted', text: c.L('noDocs') }));
      } else {
        var checks = c.loadChecklist();
        var groups = [['common', 'grpCommon'], ['required', 'grpRequired'], ['conditional', 'grpConditional'], ['additional', 'grpAdditional']];
        groups.forEach(function (g) {
          var inGroup = items.filter(function (it) { return it.group === g[0]; });
          if (!inGroup.length) return;
          body.appendChild(c.h('div', { class: 'wm-doc-group-label', text: c.L(g[1]) }));
          inGroup.forEach(function (it) {
            body.appendChild(self.docRow(c, it, checks));
          });
        });
        // checklist controls
        body.appendChild(self.checklistControls(c, packet, items));
      }
      return this.accordion(c, 'secDocs', deriveCoverage(packet).level, [body], !cov.isLimited);
    },

    docRow: function (c, it, checks) {
      var cb = c.h('input', {
        class: 'wm-doc-check', type: 'checkbox',
        id: 'wm-chk-' + it.id, checked: checks[it.id] ? 'checked' : false,
        aria: { label: it.name }
      });
      cb.addEventListener('change', function () {
        var map = c.loadChecklist();
        if (cb.checked) map[it.id] = true; else delete map[it.id];
        c.saveChecklist(map);
        c.track('waymaker_checklist_interacted', { locale: c.locale });
      });
      var labelChildren = [c.h('span', { class: 'wm-doc-name', text: it.name })];
      if (it.isOfficialForm) labelChildren.push(c.h('span', { class: 'wm-tag wm-tag-form', text: c.L('officialForm') }));
      labelChildren.push(this.coverageBadge(c, it.coverage));
      var label = c.h('label', { class: 'wm-doc-label', for: 'wm-chk-' + it.id }, labelChildren);
      var sub = [];
      if (it.conditionKo) sub.push(c.h('div', { class: 'wm-doc-cond', text: it.conditionKo }));
      // Section 6 "where to get / how to prepare" — only from source refs, never invented.
      var where = this.whereFromRefs(c, it.sourceRefs);
      if (where) sub.push(where);
      return c.h('div', { class: 'wm-doc-row' }, [cb, c.h('div', { class: 'wm-doc-main' }, [label].concat(sub))]);
    },

    whereFromRefs: function (c, refs) {
      if (!refs || !refs.length) return null;
      var parts = refs.map(function (r) {
        var bits = [];
        if (r.sourceNameKo) bits.push(r.sourceNameKo);
        if (r.versionDate) bits.push(r.versionDate);
        if (r.pageRange) bits.push(r.pageRange);
        if (r.article) bits.push(r.article);
        return bits.join(' · ');
      }).filter(Boolean);
      if (!parts.length) return null;
      return c.h('div', { class: 'wm-doc-where' }, [
        c.h('span', { class: 'wm-doc-where-label', text: c.L('secWhere') + ': ' }),
        c.h('span', { text: parts.join(' / ') })
      ]);
    },

    checklistControls: function (c, packet, items) {
      var self = this;
      var status = c.h('span', { class: 'wm-checklist-status', aria: { live: 'polite' } }, []);
      function announce(msg) { status.textContent = msg; }
      var reset = c.h('button', { class: 'wm-btn wm-btn-ghost wm-btn-sm', type: 'button', onclick: function () {
        c.saveChecklist({});
        c.track('waymaker_checklist_interacted', { locale: c.locale });
        // re-render doc rows quickly
        var boxes = c.h ? null : null;
        var inputs = document.querySelectorAll('.wm-doc-check');
        Array.prototype.forEach.call(inputs, function (b) { b.checked = false; });
      } }, [c.L('checklistReset')]);
      var copy = c.h('button', { class: 'wm-btn wm-btn-ghost wm-btn-sm', type: 'button', onclick: function () {
        var text = self.checklistText(c, packet, items);
        if (global.navigator && global.navigator.clipboard) {
          global.navigator.clipboard.writeText(text).then(function () { announce(c.L('checklistCopied')); }).catch(function () {});
        }
        c.track('waymaker_checklist_interacted', { locale: c.locale });
      } }, [c.L('checklistCopy')]);
      var print = c.h('button', { class: 'wm-btn wm-btn-ghost wm-btn-sm', type: 'button', onclick: function () {
        self.printChecklist(c, packet, items);
        c.track('waymaker_checklist_interacted', { locale: c.locale });
      } }, [c.L('checklistPrint')]);
      return c.h('div', { class: 'wm-checklist-foot' }, [
        c.h('p', { class: 'wm-muted wm-checklist-hint', text: c.L('checklistHint') }),
        c.h('div', { class: 'wm-checklist-btns' }, [reset, copy, print]),
        status
      ]);
    },

    checklistText: function (c, packet, items) {
      var checks = c.loadChecklist();
      var lines = [];
      var title = c.locale === 'en' ? (packet.titleEn || packet.titleKo) : packet.titleKo;
      lines.push((packet.statusCode || '') + ' · ' + title);
      var ver = (packet.sourceLens && packet.sourceLens.sources && packet.sourceLens.sources[0] && packet.sourceLens.sources[0].versionDate) || '';
      if (ver) lines.push(c.L('sourceVersion') + ': ' + ver);
      lines.push('');
      var groups = { common: c.L('grpCommon'), required: c.L('grpRequired'), conditional: c.L('grpConditional'), additional: c.L('grpAdditional') };
      Object.keys(groups).forEach(function (g) {
        var inGroup = items.filter(function (it) { return it.group === g; });
        if (!inGroup.length) return;
        lines.push('[' + groups[g] + ']');
        inGroup.forEach(function (it) {
          lines.push((checks[it.id] ? '[x] ' : '[ ] ') + it.name + ' (' + sourceCoverageLabel(it.coverage, c.locale) + ')');
        });
        lines.push('');
      });
      var cov = deriveCoverage(packet);
      if (cov.isLimited) { lines.push('* ' + c.L('coverageLimited')); lines.push(''); }
      lines.push('— ' + c.L('disclaimerPrint'));
      return lines.join('\n');
    },

    printChecklist: function (c, packet, items) {
      var text = this.checklistText(c, packet, items);
      var win = global.open('', '_blank');
      if (!win) return;
      var esc = function (s) { return String(s).replace(/[&<>]/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[m]; }); };
      win.document.write('<!doctype html><meta charset="utf-8"><title>Paradiso · ' + esc(packet.statusCode || '') + '</title>' +
        '<style>body{font:14px/1.6 sans-serif;padding:24px;max-width:640px}pre{white-space:pre-wrap}</style>' +
        '<pre>' + esc(text) + '</pre>');
      win.document.close();
      try { win.focus(); win.print(); } catch (e) {}
    },

    sectionTiming: function (c, packet) {
      var t0 = packet.timing || {};
      var nodes = [];
      if (t0.triggerEventKo) nodes.push(c.h('p', {}, [c.h('strong', { text: '· ' }), c.h('span', { text: t0.triggerEventKo })]));
      if (t0.stayPeriodHintKo) nodes.push(c.h('p', { text: t0.stayPeriodHintKo }));
      (packet.riskFlags || []).forEach(function (r) {
        nodes.push(c.h('div', { class: 'wm-risk' }, [
          c.h('span', { class: 'wm-risk-flag', text: r.flagKo }),
          c.h('span', { class: 'wm-risk-detail', text: r.detailKo })
        ]));
      });
      if (t0.limitationKo) nodes.push(c.h('p', { class: 'wm-muted', text: t0.limitationKo }));
      var level = t0.sourceBacked ? 'source_confirmed' : 'limited';
      return this.accordion(c, 'secTiming', level, nodes, false);
    },

    sectionFees: function (c, packet) {
      var f = packet.fees || {};
      var nodes = [];
      (f.items || []).forEach(function (it) {
        nodes.push(c.h('div', { class: 'wm-fee' }, [
          c.h('span', { class: 'wm-fee-label', text: it.labelKo || '' }),
          c.h('span', { class: 'wm-fee-amount', text: it.amountKo || '' })
        ]));
      });
      if (f.limitationKo) nodes.push(c.h('p', { class: 'wm-muted', text: f.limitationKo }));
      if (!nodes.length) nodes.push(c.h('p', { class: 'wm-muted', text: c.L('verifyIntro') }));
      var level = f.sourceBacked ? 'source_confirmed' : 'limited';
      return this.accordion(c, 'secFees', level, nodes, false);
    },

    sectionChannel: function (c, packet) {
      var ch = packet.channels || {};
      var nodes = [];
      if (ch.immigrationOfficeVisit && ch.immigrationOfficeVisit.availableKo) {
        nodes.push(c.h('p', { text: ch.immigrationOfficeVisit.availableKo }));
      }
      if (ch.hikoreaReservation && ch.hikoreaReservation.taskTypeKo) {
        nodes.push(c.h('p', {}, [c.h('strong', { text: 'HiKorea: ' }), c.h('span', { text: ch.hikoreaReservation.taskTypeKo })]));
        if (ch.hikoreaReservation.noteKo) nodes.push(c.h('p', { class: 'wm-muted', text: ch.hikoreaReservation.noteKo }));
      }
      if (ch.limitationKo) nodes.push(c.h('p', { class: 'wm-muted', text: ch.limitationKo }));
      var level = (ch.hikoreaReservation && ch.hikoreaReservation.sourceBacked) ? 'source_confirmed' : 'limited';
      return this.accordion(c, 'secChannel', level, nodes, false);
    },

    sectionJurisdiction: function (c, packet) {
      var j = packet.officeAndJurisdiction || {};
      var nodes = [];
      if (j.summaryKo) nodes.push(c.h('p', { text: j.summaryKo }));
      if (j.limitationKo) nodes.push(c.h('p', { class: 'wm-muted', text: j.limitationKo }));
      if (!nodes.length) nodes.push(c.h('p', { class: 'wm-muted', text: c.L('verifyIntro') }));
      return this.accordion(c, 'secJurisdiction', 'limited', nodes, false);
    },

    sectionCoverage: function (c, packet, cov) {
      var lens = packet.sourceLens || {};
      var nodes = [this.coverageBadge(c, cov.level)];
      (lens.sources || []).forEach(function (s) {
        var bits = [s.sourceNameKo, s.versionDate, s.pageRange, s.article].filter(Boolean).join(' · ');
        nodes.push(c.h('div', { class: 'wm-source-row' }, [
          c.h('span', { class: 'wm-source-name', text: bits })
        ]));
      });
      if (lens.limitationKo) nodes.push(c.h('p', { class: 'wm-muted', text: lens.limitationKo }));
      var noteKo = packet.finalAgencyNoteKo, noteEn = packet.finalAgencyNoteEn;
      nodes.push(c.h('p', { class: 'wm-final-note', text: c.locale === 'en' ? (noteEn || noteKo || '') : (noteKo || '') }));
      return this.accordion(c, 'secCoverage', cov.level, nodes, false);
    },

    sectionVerify: function (c, packet, cov) {
      // Aggregate every section that is not source-backed into one honest list.
      var nodes = [c.h('p', { class: 'wm-muted', text: c.L('verifyIntro') })];
      var verify = [];
      if (!(packet.timing && packet.timing.sourceBacked)) verify.push(c.L('secTiming'));
      if (!(packet.fees && packet.fees.sourceBacked)) verify.push(c.L('secFees'));
      var ch = packet.channels || {};
      if (!(ch.hikoreaReservation && ch.hikoreaReservation.sourceBacked)) verify.push(c.L('secChannel'));
      verify.push(c.L('secJurisdiction'));
      if (cov.isLimited) verify.push(c.L('secDocs'));
      nodes.push(c.h('ul', { class: 'wm-verify-list' }, verify.map(function (v) { return c.h('li', { text: v }); })));
      return this.accordion(c, 'secVerify', null, nodes, false);
    },

    footerActions: function (c, packet, cov) {
      var self = this;
      var bar = c.h('div', { class: 'wm-actionbar' }, []);
      // HiKorea CTA — present in every full or partial packet (Phase 8). For
      // coverage-limited we still offer it but it routes to generic guidance.
      var hk = c.h('button', { class: 'wm-btn wm-btn-primary wm-btn-block', type: 'button', onclick: function () {
        c.track('waymaker_hikorea_opened', { locale: c.locale, procedureKey: c.state.procedureKey, coverageLevel: cov.level });
        if (typeof c.openHiKorea === 'function') c.openHiKorea(packet.statusCode, c.state.procedureKey, packet.packetType, cov.isLimited);
        else global.open('https://www.hikorea.go.kr', '_blank');
      } }, [c.L('hikoreaCta')]);
      bar.appendChild(hk);
      // AI follow-up — SECONDARY, appears only after a packet is shown, and only
      // calls /api/ask when the user opens it and submits.
      bar.appendChild(self.aiFollowup(c, packet));
      // restart
      bar.appendChild(c.h('button', { class: 'wm-btn wm-btn-ghost wm-btn-block', type: 'button', onclick: c.restart }, [c.L('restart')]));
      return bar;
    },

    aiFollowup: function (c, packet) {
      var self = this;
      var panel = c.h('div', { class: 'wm-ai', hidden: 'hidden' }, []);
      var opened = false;
      var toggle = c.h('button', {
        class: 'wm-btn wm-btn-secondary wm-btn-block', type: 'button',
        'aria-expanded': 'false',
        onclick: function () {
          opened = !opened;
          panel.hidden = !opened;
          toggle.setAttribute('aria-expanded', opened ? 'true' : 'false');
          if (opened) { c.track('waymaker_ai_followup_opened', { locale: c.locale, procedureKey: c.state.procedureKey }); ta.focus(); }
        }
      }, [c.L('aiFollowupCta')]);
      var ta = c.h('textarea', { class: 'wm-ai-input', rows: '3', placeholder: c.L('aiFollowupPlaceholder'), aria: { label: c.L('aiFollowupCta') } });
      var note = c.h('p', { class: 'wm-ai-note', text: c.L('aiPrivacyNote') });
      var out = c.h('div', { class: 'wm-ai-out', aria: { live: 'polite' } }, []);
      var send = c.h('button', { class: 'wm-btn wm-btn-primary', type: 'button', onclick: function () {
        var q = (ta.value || '').trim();
        if (!q) return;
        var context = buildAiFollowupContext(c.state, packet);
        out.textContent = '…';
        if (typeof c.onAskFollowup === 'function') {
          Promise.resolve(c.onAskFollowup(context, q)).then(function (answer) {
            c.clear(out);
            if (answer && typeof answer === 'string') out.appendChild(c.h('p', { text: answer }));
          }).catch(function () { out.textContent = ''; });
        }
      } }, [c.L('aiSend')]);
      panel.appendChild(note);
      panel.appendChild(ta);
      panel.appendChild(send);
      panel.appendChild(out);
      return c.h('div', { class: 'wm-ai-wrap' }, [toggle, panel]);
    }
  };

  // =========================================================================
  // 7. Public API
  // =========================================================================
  return {
    // pure logic (tested in Node)
    PACKET_TYPE_BY_PROCEDURE_KEY: PACKET_TYPE_BY_PROCEDURE_KEY,
    PROCEDURE_ORDER: PROCEDURE_ORDER,
    SOURCE_COVERAGE: SOURCE_COVERAGE,
    MATERIALLY_AMBIGUOUS_FAMILIES: MATERIALLY_AMBIGUOUS_FAMILIES,
    NONCANONICAL_PROGRAM_CODES: NONCANONICAL_PROGRAM_CODES,
    STRINGS: STRINGS,
    PROCEDURE_LABELS: PROCEDURE_LABELS,
    packetTypeForProcedureKey: packetTypeForProcedureKey,
    parentCode: parentCode,
    subCodesOf: subCodesOf,
    buildStatusCatalog: buildStatusCatalog,
    filterStatusCatalog: filterStatusCatalog,
    proceduresForStatus: proceduresForStatus,
    needsSubStatusClarification: needsSubStatusClarification,
    deriveCoverage: deriveCoverage,
    countDocuments: countDocuments,
    groupChecklistItems: groupChecklistItems,
    sourceCoverageLabel: sourceCoverageLabel,
    sourceCoverageClass: sourceCoverageClass,
    buildAiFollowupContext: buildAiFollowupContext,
    procedureLabel: procedureLabel,
    t: t,
    makeAnalytics: makeAnalytics,
    // UI (browser only)
    createNavigator: createNavigator
  };
});
