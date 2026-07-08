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
    source_confirmed: {
      ko: '공식 원문 확인', en: 'Confirmed in official source', 'zh-CN': '已确认官方原文',
      ja: '公式原文で確認済み', vi: 'Đã xác nhận trong nguồn chính thức', tl: 'Nakumpirma sa opisyal na pinagmulan',
      id: 'Dikonfirmasi dalam sumber resmi', ru: 'Подтверждено в официальном источнике', fr: 'Confirmé dans la source officielle',
      es: 'Confirmado en la fuente oficial', ar: 'مؤكَّد في المصدر الرسمي', de: 'In offizieller Quelle bestätigt',
      cls: 'wm-cov-confirmed', tr: "Resmi kaynakta doğrulandı", uk: "Підтверджено в офіційному джерелі"
    },
    contextual: {
      ko: '일부 항목만 공식 확인', en: 'Partially covered by official sources', 'zh-CN': '仅部分项目经官方确认',
      ja: '一部の項目のみ公式に確認', vi: 'Chỉ một phần được nguồn chính thức bao quát', tl: 'Bahagyang saklaw ng opisyal na pinagmulan',
      id: 'Hanya sebagian dikonfirmasi sumber resmi', ru: 'Частично подтверждено официальными источниками', fr: 'Partiellement couvert par les sources officielles',
      es: 'Cubierto parcialmente por fuentes oficiales', ar: 'مغطّى جزئيًا بمصادر رسمية', de: 'Teilweise durch offizielle Quellen abgedeckt',
      cls: 'wm-cov-partial', tr: "Resmi kaynaklarca kısmen kapsanıyor", uk: "Частково охоплено офіційними джерелами"
    },
    limited: {
      ko: '관할기관 확인 필요', en: 'Official confirmation required', 'zh-CN': '需向管辖机关确认',
      ja: '管轄機関での確認が必要', vi: 'Cần xác nhận chính thức', tl: 'Kailangan ng opisyal na kumpirmasyon',
      id: 'Perlu konfirmasi resmi', ru: 'Требуется официальное подтверждение', fr: 'Confirmation officielle requise',
      es: 'Se requiere confirmación oficial', ar: 'يلزم التأكيد الرسمي', de: 'Offizielle Bestätigung erforderlich',
      cls: 'wm-cov-verify', tr: "Resmi teyit gerekli", uk: "Потрібне офіційне підтвердження"
    },
    final_agency_discretion: {
      ko: '관할기관 확인 필요', en: 'Official confirmation required', 'zh-CN': '需向管辖机关确认',
      ja: '管轄機関での確認が必要', vi: 'Cần xác nhận chính thức', tl: 'Kailangan ng opisyal na kumpirmasyon',
      id: 'Perlu konfirmasi resmi', ru: 'Требуется официальное подтверждение', fr: 'Confirmation officielle requise',
      es: 'Se requiere confirmación oficial', ar: 'يلزم التأكيد الرسمي', de: 'Offizielle Bestätigung erforderlich',
      cls: 'wm-cov-verify', tr: "Resmi teyit gerekli", uk: "Потрібне офіційне підтвердження"
    },
    unavailable: {
      ko: '현재 근거 미확보', en: 'No current source coverage', 'zh-CN': '目前尚无依据',
      ja: '現時点で根拠なし', vi: 'Hiện chưa có nguồn căn cứ', tl: 'Walang kasalukuyang saklaw ng pinagmulan',
      id: 'Belum ada dasar sumber saat ini', ru: 'Сейчас нет подтверждающих источников', fr: 'Aucune source disponible actuellement',
      es: 'Sin cobertura de fuentes por ahora', ar: 'لا يوجد سند حاليًا', de: 'Derzeit keine Quellengrundlage',
      cls: 'wm-cov-none', tr: "Şu anda kaynak kapsamı yok", uk: "Наразі немає покриття джерел"
    }
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

  // The badge accepts BOTH vocabularies: the source-lens level
  // (source_confirmed/contextual/limited/unavailable) AND the coverageSummary
  // level (full/partial/limited/unavailable). 'full'/'partial' are aliased to
  // their lens equivalents so a fully source-confirmed packet shows "공식 원문 확인"
  // / "Confirmed in official source" rather than falling through to the limited
  // fallback. (Without this, deriveCoverage().level='full' rendered as "Official
  // confirmation required".)
  var COVERAGE_LEVEL_ALIAS = { full: 'source_confirmed', partial: 'contextual' };
  function _covEntry(level) {
    var key = COVERAGE_LEVEL_ALIAS[level] || level;
    return SOURCE_COVERAGE[key] || SOURCE_COVERAGE.limited;
  }
  function sourceCoverageLabel(level, locale) {
    var c = _covEntry(level);
    return c[locale] || ((locale === 'en') ? c.en : c.ko);
  }
  function sourceCoverageClass(level) {
    return _covEntry(level).cls;
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
      retry: '다시 시도',
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
      secProcedure: '나의 절차', secNext: '지금 할 일', secDecision: '판단 전에 정리할 정보', secApplicability: '적용 가능성',
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
      formHelperCta: '통합신청서 작성 도우미로 이어가기',
      aiFollowupCta: '이 패킷에서 헷갈리는 점 묻기',
      aiFollowupPlaceholder: '이 패킷에서 이해되지 않는 점을 물어보세요. 예: 재정서류가 면제될 수 있나요?',
      aiPrivacyNote: '개인정보(이름, 여권·외국인등록번호, 주소, 전화번호 등)는 입력하지 마세요. 이 도우미는 패킷을 설명할 뿐 새로운 공식 요건을 만들지 않습니다.',
      aiSend: '질문하기',
      aiFollowupFailed: '지금은 답변을 가져오지 못했습니다. 잠시 후 다시 시도하거나 1345 또는 HiKorea에서 확인하세요.',
      aiSafetyKicker: '안전상 답변할 수 없는 요청',
      aiSafetyAltTitle: '대신 안내할 수 있는 정보',
      resumeScenarioTitle: '이어서 진행할까요?',
      resumeScenarioLabelPrefix: '이전에 선택한 상황: ',
      resumeScenarioContinue: '이어서 진행하기',
      resumeScenarioRestart: '처음부터 시작하기',
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
      retry: 'Try again',
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
      secProcedure: 'My procedure', secNext: 'What to do next', secDecision: 'Information to prepare before deciding', secApplicability: 'Applicability',
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
      formHelperCta: 'Continue to the application-form helper',
      aiFollowupCta: 'Ask about this packet',
      aiFollowupPlaceholder: 'Ask about this packet. Example: Could the financial-evidence item be waived?',
      aiPrivacyNote: 'Do not enter personal identifiers (name, passport/ARC number, address, phone). This helper only explains the packet; it does not create new official requirements.',
      aiSend: 'Ask',
      aiFollowupFailed: "We couldn't get an answer right now. Try again in a moment, or check with 1345 or HiKorea.",
      aiSafetyKicker: "A request we can't help with for safety reasons",
      aiSafetyAltTitle: 'What I can help with instead',
      resumeScenarioTitle: 'Continue where you left off?',
      resumeScenarioLabelPrefix: 'Previously selected: ',
      resumeScenarioContinue: 'Continue',
      resumeScenarioRestart: 'Start over',
      noDocs: 'The official document list for this procedure is not yet structured.',
      verifyIntro: 'The items below cannot be confirmed from official sources here. Confirm with the competent office, 1345, or HiKorea.',
      generatedOn: 'Generated',
      sourceVersion: 'Source version',
      disclaimerPrint: 'Final confirmation must be made with HiKorea, 1345, or the competent immigration office.',
      langName: 'English',
      operatorDiag: 'Diagnostics (operator)'
    },
    'zh-CN': {
      title: 'Waymaker - 韩国停留手续路径向导',
      subtitle: '以官方依据为基础，梳理您的手续、材料、预约和下一步行动。',
      empty: '不必先写问题。请选择您当前的居留资格和要办理的事项。',
      start: '选择我的情况',
      back: '上一步',
      next: '下一步',
      restart: '从头开始',
      retry: '重试',
      dontKnow: '不太清楚',
      stepLanguage: '请选择语言',
      stepLocation: '您现在在哪里？',
      locIn: '在韩国', locOut: '在韩国境外', locUnsure: '不太清楚 / 视情况而定',
      stepStatus: '请选择您当前的居留资格',
      statusSearchPlaceholder: '按居留资格代码或名称搜索（例：D-2、留学、E-7）',
      statusUnknown: '我不知道自己的居留资格',
      statusFirstEntry: '我还没有签证 / 正在海外准备首次入境·签证签发',
      noStatusResults: '没有搜索结果。请用代码（如 D-2）或中文/韩文名称重新搜索。',
      programGroup: '项目 / 试点事业（官方依据有限）',
      stepProcedure: '您需要办理哪项手续？',
      procedureLimitedHint: '官方依据有限',
      stepSubStatus: '您属于哪种细分类型？',
      subStatusHelp: '材料和标准会因细分类型而不同。如不确定，请选择“不太清楚”。',
      generating: '正在准备基于官方依据的手续清单…',
      secProcedure: '我的手续', secNext: '现在要做的事', secApplicability: '适用可能性',
      secDocs: '准备材料', secConditional: '按情况追加的材料', secWhere: '办理处·准备方法',
      secTiming: '期限·注意事项', secFees: '手续费', secChannel: 'HiKorea / 访问路径',
      secJurisdiction: '管辖', secCoverage: '官方依据范围', secVerify: '需确认项目',
      grpCommon: '通用材料', grpRequired: '必备材料', grpConditional: '按情况材料',
      grpAdditional: '追加材料', grpVerify: '向机关确认', grpNone: '依据不足',
      checklistTitle: '材料清单', checklistHint: '勾选状态仅保存在本浏览器中。',
      checklistReset: '重置', checklistCopy: '复制', checklistPrint: '打印/导出',
      checklistCopied: '已将清单复制到剪贴板。',
      officialForm: '官方表格',
      coverageLimitedTitle: '此手续的官方依据有限',
      coverageLimited: '目前对此手续的官方依据尚未充分结构化。对于未经确认的材料、手续费、期限和预约路径，不会擅自指引。请向 HiKorea、1345 或管辖出入境机关最终确认。',
      whatWeCanSay: 'Paradiso 可安全提供的信息',
      whatWeCannot: 'Paradiso 无法确认的信息',
      officialChannels: '官方确认渠道',
      call1345: '1345（外国人综合服务中心）',
      hikoreaCta: '确认我的 HiKorea 预约路径',
      aiFollowupCta: '询问此清单中不清楚的地方',
      aiFollowupPlaceholder: '请询问此清单中不理解的地方。例如：财力材料可以被免除吗？',
      aiPrivacyNote: '请勿输入个人信息（姓名、护照·外国人登录号、地址、电话号码等）。本助手只解释清单内容，不会创建新的官方要件。',
      aiSend: '提问',
      noDocs: '此手续的官方材料清单尚未结构化。',
      verifyIntro: '以下项目无法以官方依据确定显示，请向管辖机关/1345/HiKorea 确认。',
      generatedOn: '生成日',
      sourceVersion: '依据版本',
      disclaimerPrint: '最终确认须向 HiKorea、1345 或管辖出入境·外国人机关进行。',
      langName: '简体中文',
      operatorDiag: '诊断（运营者）'
    },
    ja: {
      title: 'Waymaker - 韓国滞在手続きの道案内',
      subtitle: '公式の出典をもとに、あなたの手続き・書類・予約・次の行動を整理します。',
      empty: '最初に質問を書く必要はありません。現在の滞在資格と、これからやりたいことを選んでください。',
      start: '自分の状況を選ぶ',
      back: '戻る',
      next: '次へ',
      restart: '最初から',
      dontKnow: 'よくわかりません',
      stepLanguage: '言語を選択してください',
      stepLocation: '今どちらにいますか？',
      locIn: '韓国国内', locOut: '韓国国外', locUnsure: 'よくわかりません / 状況によります',
      stepStatus: '現在の滞在資格を選択してください',
      statusSearchPlaceholder: '滞在資格コードまたは名称で検索（例：D-2、留学、E-7）',
      statusUnknown: '自分の滞在資格がわかりません',
      statusFirstEntry: 'まだビザがありません / 海外から初回入国・査証発給を準備中',
      noStatusResults: '検索結果がありません。コード（D-2 など）または韓国語の名称で再検索してください。',
      programGroup: 'プログラム / 試験事業（公式根拠は限定的）',
      stepProcedure: 'どの手続きが必要ですか？',
      procedureLimitedHint: '公式根拠が限定的',
      stepSubStatus: 'どの細分類型に該当しますか？',
      subStatusHelp: '細分類型によって書類や基準が異なる場合があります。確実でなければ「よくわかりません」を選んでください。',
      generating: '公式根拠に基づく手続きパケットを準備中…',
      secProcedure: '私の手続き', secNext: '今やること', secApplicability: '適用可能性',
      secDocs: '準備する書類', secConditional: '状況別の追加書類', secWhere: '取得先・準備方法',
      secTiming: '期限・注意事項', secFees: '手数料', secChannel: 'HiKorea / 訪問経路',
      secJurisdiction: '管轄', secCoverage: '公式根拠の範囲', secVerify: '確認が必要な項目',
      grpCommon: '共通書類', grpRequired: '必須書類', grpConditional: '状況別書類',
      grpAdditional: '追加書類', grpVerify: '管轄機関で確認', grpNone: '根拠が未確保',
      checklistTitle: '書類チェックリスト', checklistHint: 'チェック状態はこのブラウザにのみ保存されます。',
      checklistReset: 'リセット', checklistCopy: 'コピー', checklistPrint: '印刷／書き出し',
      checklistCopied: 'チェックリストをクリップボードにコピーしました。',
      officialForm: '公式様式',
      coverageLimitedTitle: '公式根拠が限定的な手続きです',
      coverageLimited: '現在この手続きについて、公式根拠が十分に構造化されていません。確認されていない書類・手数料・期限・予約経路を勝手に案内することはありません。HiKorea、1345、または管轄の出入国機関で最終確認してください。',
      whatWeCanSay: 'Paradiso が安全に案内できる情報',
      whatWeCannot: 'Paradiso が確認できない情報',
      officialChannels: '公式の確認経路',
      call1345: '1345（外国人総合案内センター）',
      hikoreaCta: 'HiKorea の予約経路を確認',
      aiFollowupCta: 'このパケットで分かりにくい点を質問する',
      aiFollowupPlaceholder: 'このパケットで理解できない点を質問してください。例：財政書類は免除されることがありますか？',
      aiPrivacyNote: '個人情報（氏名、パスポート・外国人登録番号、住所、電話番号など）は入力しないでください。このアシスタントはパケットを説明するだけで、新しい公式要件を作ることはありません。',
      aiSend: '質問する',
      noDocs: 'この手続きの公式書類リストはまだ構造化されていません。',
      verifyIntro: '以下の項目は公式根拠で確定表示できないため、管轄機関／1345／HiKorea で確認してください。',
      generatedOn: '作成日',
      sourceVersion: '根拠バージョン',
      disclaimerPrint: '最終確認は HiKorea、1345、または管轄の出入国・外国人官署で行ってください。',
      langName: '日本語',
      operatorDiag: '診断（運営者）'
    },
    vi: {
      title: 'Waymaker - Tìm đường thủ tục cư trú Hàn Quốc',
      subtitle: 'Dựa trên nguồn chính thức, sắp xếp thủ tục, giấy tờ, đặt hẹn và hành động tiếp theo của bạn.',
      empty: 'Bạn không cần phải viết câu hỏi trước. Hãy chọn tư cách cư trú hiện tại và việc bạn muốn làm.',
      start: 'Chọn tình huống của tôi',
      back: 'Quay lại',
      next: 'Tiếp theo',
      restart: 'Bắt đầu lại',
      dontKnow: 'Tôi không chắc',
      stepLanguage: 'Hãy chọn ngôn ngữ',
      stepLocation: 'Bạn đang ở đâu?',
      locIn: 'Trong Hàn Quốc', locOut: 'Ngoài Hàn Quốc', locUnsure: 'Không chắc / tùy trường hợp',
      stepStatus: 'Hãy chọn tư cách cư trú hiện tại của bạn',
      statusSearchPlaceholder: 'Tìm theo mã hoặc tên tư cách cư trú (ví dụ: D-2, du học, E-7)',
      statusUnknown: 'Tôi không biết tư cách cư trú của mình',
      statusFirstEntry: 'Tôi chưa có visa / đang chuẩn bị nhập cảnh lần đầu·cấp visa từ nước ngoài',
      noStatusResults: 'Không có kết quả. Hãy thử mã (ví dụ D-2) hoặc tên tư cách bằng tiếng Hàn.',
      programGroup: 'Chương trình / thí điểm (nguồn chính thức còn hạn chế)',
      stepProcedure: 'Bạn cần làm thủ tục gì?',
      procedureLimitedHint: 'Nguồn chính thức hạn chế',
      stepSubStatus: 'Bạn thuộc loại chi tiết nào?',
      subStatusHelp: 'Giấy tờ và tiêu chí có thể khác nhau tùy loại chi tiết. Nếu không chắc, hãy chọn "Tôi không chắc".',
      generating: 'Đang chuẩn bị gói thủ tục dựa trên nguồn chính thức…',
      secProcedure: 'Thủ tục của tôi', secNext: 'Việc cần làm ngay', secApplicability: 'Khả năng áp dụng',
      secDocs: 'Giấy tờ cần chuẩn bị', secConditional: 'Giấy tờ bổ sung theo tình huống', secWhere: 'Nơi cấp·cách chuẩn bị',
      secTiming: 'Thời hạn·lưu ý', secFees: 'Lệ phí', secChannel: 'HiKorea / lối đến trực tiếp',
      secJurisdiction: 'Cơ quan có thẩm quyền', secCoverage: 'Phạm vi nguồn chính thức', secVerify: 'Mục cần xác nhận',
      grpCommon: 'Giấy tờ chung', grpRequired: 'Giấy tờ bắt buộc', grpConditional: 'Giấy tờ theo tình huống',
      grpAdditional: 'Giấy tờ bổ sung', grpVerify: 'Xác nhận với cơ quan', grpNone: 'Chưa đủ căn cứ',
      checklistTitle: 'Danh mục giấy tờ', checklistHint: 'Trạng thái đánh dấu chỉ được lưu trong trình duyệt này.',
      checklistReset: 'Đặt lại', checklistCopy: 'Sao chép', checklistPrint: 'In / xuất',
      checklistCopied: 'Đã sao chép danh mục vào bộ nhớ tạm.',
      officialForm: 'Mẫu chính thức',
      coverageLimitedTitle: 'Thủ tục này có nguồn chính thức hạn chế',
      coverageLimited: 'Hiện chưa có đủ nguồn chính thức được cấu trúc cho thủ tục này. Sẽ không tự ý hướng dẫn các giấy tờ, lệ phí, thời hạn hay lối đặt hẹn chưa được xác nhận. Vui lòng xác nhận cuối cùng với HiKorea, 1345 hoặc cơ quan xuất nhập cảnh có thẩm quyền.',
      whatWeCanSay: 'Thông tin Paradiso có thể cung cấp an toàn',
      whatWeCannot: 'Thông tin Paradiso không thể xác nhận',
      officialChannels: 'Kênh xác nhận chính thức',
      call1345: '1345 (Trung tâm tư vấn tổng hợp cho người nước ngoài)',
      hikoreaCta: 'Kiểm tra lối đặt hẹn HiKorea của tôi',
      aiFollowupCta: 'Hỏi về điều chưa rõ trong gói này',
      aiFollowupPlaceholder: 'Hãy hỏi về điều bạn chưa hiểu trong gói này. Ví dụ: Giấy tờ chứng minh tài chính có thể được miễn không?',
      aiPrivacyNote: 'Đừng nhập thông tin cá nhân (họ tên, số hộ chiếu·số đăng ký người nước ngoài, địa chỉ, số điện thoại, v.v.). Trợ lý này chỉ giải thích gói thủ tục, không tạo ra yêu cầu chính thức mới.',
      aiSend: 'Hỏi',
      noDocs: 'Danh mục giấy tờ chính thức của thủ tục này chưa được cấu trúc.',
      verifyIntro: 'Các mục dưới đây không thể xác định bằng nguồn chính thức tại đây, hãy xác nhận với cơ quan có thẩm quyền/1345/HiKorea.',
      generatedOn: 'Ngày tạo',
      sourceVersion: 'Phiên bản căn cứ',
      disclaimerPrint: 'Việc xác nhận cuối cùng phải thực hiện với HiKorea, 1345 hoặc cơ quan xuất nhập cảnh·người nước ngoài có thẩm quyền.',
      langName: 'Tiếng Việt',
      operatorDiag: 'Chẩn đoán (người vận hành)'
    },
    tl: {
      title: 'Waymaker - Gabay sa Proseso ng Pananatili sa Korea',
      subtitle: 'Batay sa opisyal na pinagmulan, inaayos namin ang iyong proseso, dokumento, booking, at susunod na hakbang.',
      empty: 'Hindi mo kailangang magsulat muna ng tanong. Piliin ang iyong kasalukuyang status of stay at ang gusto mong gawin.',
      start: 'Piliin ang aking sitwasyon',
      back: 'Bumalik',
      next: 'Susunod',
      restart: 'Magsimula muli',
      dontKnow: 'Hindi ako sigurado',
      stepLanguage: 'Piliin ang iyong wika',
      stepLocation: 'Nasaan ka ngayon?',
      locIn: 'Nasa Korea', locOut: 'Nasa labas ng Korea', locUnsure: 'Hindi sigurado / depende',
      stepStatus: 'Piliin ang iyong kasalukuyang status of stay',
      statusSearchPlaceholder: 'Maghanap ayon sa code o pangalan (hal. D-2, pag-aaral, E-7)',
      statusUnknown: 'Hindi ko alam ang aking status of stay',
      statusFirstEntry: 'Wala pa akong visa / naghahanda ng unang pagpasok·pag-isyu ng visa mula sa ibang bansa',
      noStatusResults: 'Walang tugma. Subukan ang code (hal. D-2) o ang pangalan ng status sa Korean.',
      programGroup: 'Mga programa / pilot (limitado ang opisyal na saklaw)',
      stepProcedure: 'Anong proseso ang kailangan mo?',
      procedureLimitedHint: 'Limitado ang opisyal na saklaw',
      stepSubStatus: 'Aling sub-type ang naaangkop sa iyo?',
      subStatusHelp: 'Maaaring mag-iba ang dokumento at pamantayan ayon sa sub-type. Kung hindi sigurado, piliin ang "Hindi ako sigurado".',
      generating: 'Inihahanda ang procedure packet na batay sa opisyal na pinagmulan…',
      secProcedure: 'Ang aking proseso', secNext: 'Susunod na gagawin', secApplicability: 'Pagkaaplikable',
      secDocs: 'Mga dokumentong ihahanda', secConditional: 'Karagdagang dokumento ayon sa sitwasyon', secWhere: 'Saan kukunin·paano ihahanda',
      secTiming: 'Takdang panahon·babala', secFees: 'Bayad', secChannel: 'HiKorea / daan sa pagbisita',
      secJurisdiction: 'Hurisdiksiyon', secCoverage: 'Saklaw ng opisyal na pinagmulan', secVerify: 'Mga aytem na dapat tiyakin',
      grpCommon: 'Karaniwang dokumento', grpRequired: 'Kailangang dokumento', grpConditional: 'Dokumento ayon sa sitwasyon',
      grpAdditional: 'Karagdagang dokumento', grpVerify: 'Tiyakin sa tanggapan', grpNone: 'Hindi sapat ang batayan',
      checklistTitle: 'Checklist ng dokumento', checklistHint: 'Ang iyong mga tsek ay naka-save lamang sa browser na ito.',
      checklistReset: 'I-reset', checklistCopy: 'Kopyahin', checklistPrint: 'I-print / i-export',
      checklistCopied: 'Nakopya ang checklist sa clipboard.',
      officialForm: 'Opisyal na form',
      coverageLimitedTitle: 'Limitado ang opisyal na saklaw ng prosesong ito',
      coverageLimited: 'Wala pang sapat na nakaayos na opisyal na pinagmulan para sa prosesong ito. Hindi maghuhula ng dokumento, bayad, deadline, o daan sa booking. Mangyaring tiyakin sa HiKorea, 1345, o sa may hurisdiksyong opisina ng imigrasyon.',
      whatWeCanSay: 'Ang ligtas na masasabi ng Paradiso',
      whatWeCannot: 'Ang hindi makukumpirma ng Paradiso',
      officialChannels: 'Saan tiyakin nang opisyal',
      call1345: '1345 (Immigration Contact Center)',
      hikoreaCta: 'Tingnan ang aking daan sa booking ng HiKorea',
      aiFollowupCta: 'Magtanong tungkol sa packet na ito',
      aiFollowupPlaceholder: 'Magtanong tungkol sa packet na ito. Halimbawa: Maaari bang i-waive ang aytem ng pagpapatunay ng pananalapi?',
      aiPrivacyNote: 'Huwag maglagay ng personal na impormasyon (pangalan, numero ng pasaporte·ARC, address, telepono). Ipinapaliwanag lamang ng tulong na ito ang packet; hindi ito lumilikha ng bagong opisyal na kahilingan.',
      aiSend: 'Magtanong',
      noDocs: 'Hindi pa nakaayos ang opisyal na listahan ng dokumento para sa prosesong ito.',
      verifyIntro: 'Ang mga aytem sa ibaba ay hindi makukumpirma mula sa opisyal na pinagmulan dito. Tiyakin sa may hurisdiksyong tanggapan, 1345, o HiKorea.',
      generatedOn: 'Nalikha',
      sourceVersion: 'Bersyon ng batayan',
      disclaimerPrint: 'Ang huling kumpirmasyon ay dapat gawin sa HiKorea, 1345, o sa may hurisdiksyong tanggapan ng imigrasyon·dayuhan.',
      langName: 'Filipino',
      operatorDiag: 'Diagnostics (operator)'
    },
    id: {
      title: 'Waymaker - Penunjuk Jalan Prosedur Tinggal di Korea',
      subtitle: 'Berdasarkan sumber resmi, kami merapikan prosedur, dokumen, pemesanan, dan langkah berikutnya Anda.',
      empty: 'Anda tidak perlu menulis pertanyaan dulu. Pilih status tinggal Anda saat ini dan apa yang ingin Anda lakukan.',
      start: 'Pilih situasi saya',
      back: 'Kembali',
      next: 'Berikutnya',
      restart: 'Mulai dari awal',
      dontKnow: 'Saya tidak yakin',
      stepLanguage: 'Pilih bahasa Anda',
      stepLocation: 'Di mana Anda sekarang?',
      locIn: 'Di Korea', locOut: 'Di luar Korea', locUnsure: 'Tidak yakin / tergantung situasi',
      stepStatus: 'Pilih status tinggal Anda saat ini',
      statusSearchPlaceholder: 'Cari berdasarkan kode atau nama (mis. D-2, studi, E-7)',
      statusUnknown: 'Saya tidak tahu status tinggal saya',
      statusFirstEntry: 'Saya belum punya visa / sedang menyiapkan masuk pertama·penerbitan visa dari luar negeri',
      noStatusResults: 'Tidak ada hasil. Coba kode (mis. D-2) atau nama status dalam bahasa Korea.',
      programGroup: 'Program / uji coba (cakupan resmi terbatas)',
      stepProcedure: 'Prosedur apa yang Anda butuhkan?',
      procedureLimitedHint: 'Cakupan sumber resmi terbatas',
      stepSubStatus: 'Sub-tipe mana yang berlaku untuk Anda?',
      subStatusHelp: 'Dokumen dan kriteria dapat berbeda menurut sub-tipe. Jika tidak yakin, pilih "Saya tidak yakin".',
      generating: 'Menyiapkan paket prosedur berbasis sumber resmi…',
      secProcedure: 'Prosedur saya', secNext: 'Yang harus dilakukan sekarang', secApplicability: 'Keberlakuan',
      secDocs: 'Dokumen yang disiapkan', secConditional: 'Dokumen tambahan menurut situasi', secWhere: 'Tempat memperoleh·cara menyiapkan',
      secTiming: 'Tenggat·peringatan', secFees: 'Biaya', secChannel: 'HiKorea / jalur kunjungan',
      secJurisdiction: 'Yurisdiksi', secCoverage: 'Cakupan sumber resmi', secVerify: 'Item yang perlu dipastikan',
      grpCommon: 'Dokumen umum', grpRequired: 'Dokumen wajib', grpConditional: 'Dokumen menurut situasi',
      grpAdditional: 'Dokumen tambahan', grpVerify: 'Pastikan ke kantor', grpNone: 'Dasar belum cukup',
      checklistTitle: 'Daftar periksa dokumen', checklistHint: 'Status centang hanya disimpan di browser ini.',
      checklistReset: 'Atur ulang', checklistCopy: 'Salin', checklistPrint: 'Cetak / ekspor',
      checklistCopied: 'Daftar periksa disalin ke papan klip.',
      officialForm: 'Formulir resmi',
      coverageLimitedTitle: 'Prosedur ini memiliki cakupan sumber resmi yang terbatas',
      coverageLimited: 'Saat ini belum ada cukup cakupan sumber resmi yang terstruktur untuk prosedur ini. Dokumen, biaya, tenggat, atau jalur pemesanan yang belum terkonfirmasi tidak akan dipandu sembarangan. Mohon konfirmasi terakhir ke HiKorea, 1345, atau kantor imigrasi yang berwenang.',
      whatWeCanSay: 'Informasi yang dapat diberikan Paradiso dengan aman',
      whatWeCannot: 'Informasi yang tidak dapat dikonfirmasi Paradiso',
      officialChannels: 'Saluran konfirmasi resmi',
      call1345: '1345 (Pusat Layanan Terpadu untuk Orang Asing)',
      hikoreaCta: 'Periksa jalur pemesanan HiKorea saya',
      aiFollowupCta: 'Tanyakan hal yang belum jelas pada paket ini',
      aiFollowupPlaceholder: 'Tanyakan hal yang belum Anda pahami pada paket ini. Contoh: Apakah dokumen bukti keuangan bisa dibebaskan?',
      aiPrivacyNote: 'Jangan masukkan data pribadi (nama, nomor paspor·nomor registrasi orang asing, alamat, nomor telepon, dll.). Asisten ini hanya menjelaskan paket; ia tidak membuat persyaratan resmi baru.',
      aiSend: 'Tanya',
      noDocs: 'Daftar dokumen resmi untuk prosedur ini belum terstruktur.',
      verifyIntro: 'Item di bawah ini tidak dapat ditentukan dari sumber resmi di sini, mohon konfirmasi ke kantor yang berwenang/1345/HiKorea.',
      generatedOn: 'Dibuat',
      sourceVersion: 'Versi dasar',
      disclaimerPrint: 'Konfirmasi akhir harus dilakukan ke HiKorea, 1345, atau kantor imigrasi·orang asing yang berwenang.',
      langName: 'Bahasa Indonesia',
      operatorDiag: 'Diagnostik (operator)'
    },
    ru: {
      title: 'Waymaker - Навигатор по процедурам пребывания в Корее',
      subtitle: 'На основе официальных источников упорядочиваем вашу процедуру, документы, запись и следующее действие.',
      empty: 'Вам не нужно сначала писать вопрос. Выберите свой текущий статус пребывания и то, что вы хотите сделать.',
      start: 'Выбрать мою ситуацию',
      back: 'Назад',
      next: 'Далее',
      restart: 'Начать заново',
      dontKnow: 'Я не уверен(а)',
      stepLanguage: 'Выберите язык',
      stepLocation: 'Где вы сейчас находитесь?',
      locIn: 'В Корее', locOut: 'За пределами Кореи', locUnsure: 'Не уверен(а) / зависит от ситуации',
      stepStatus: 'Выберите ваш текущий статус пребывания',
      statusSearchPlaceholder: 'Поиск по коду или названию (например, D-2, учёба, E-7)',
      statusUnknown: 'Я не знаю свой статус пребывания',
      statusFirstEntry: 'У меня ещё нет визы / готовлюсь к первому въезду·выдаче визы из-за рубежа',
      noStatusResults: 'Совпадений нет. Попробуйте код (например, D-2) или название статуса на корейском.',
      programGroup: 'Программы / пилотные проекты (официальная база ограничена)',
      stepProcedure: 'Какая процедура вам нужна?',
      procedureLimitedHint: 'Ограниченная официальная база',
      stepSubStatus: 'Какой подтип вам подходит?',
      subStatusHelp: 'Документы и критерии могут различаться по подтипу. Если не уверены, выберите «Я не уверен(а)».',
      generating: 'Готовим пакет процедуры на основе официальных источников…',
      secProcedure: 'Моя процедура', secNext: 'Что делать сейчас', secApplicability: 'Применимость',
      secDocs: 'Документы для подготовки', secConditional: 'Дополнительные документы по ситуации', secWhere: 'Где получить·как подготовить',
      secTiming: 'Сроки·предупреждения', secFees: 'Сборы', secChannel: 'HiKorea / путь визита',
      secJurisdiction: 'Компетентный орган', secCoverage: 'Охват официальных источников', secVerify: 'Пункты для проверки',
      grpCommon: 'Общие документы', grpRequired: 'Обязательные документы', grpConditional: 'Документы по ситуации',
      grpAdditional: 'Дополнительные документы', grpVerify: 'Уточнить в учреждении', grpNone: 'Недостаточно оснований',
      checklistTitle: 'Чек-лист документов', checklistHint: 'Отметки сохраняются только в этом браузере.',
      checklistReset: 'Сбросить', checklistCopy: 'Копировать', checklistPrint: 'Печать / экспорт',
      checklistCopied: 'Чек-лист скопирован в буфер обмена.',
      officialForm: 'Официальная форма',
      coverageLimitedTitle: 'У этой процедуры ограниченная база официальных источников',
      coverageLimited: 'Сейчас для этой процедуры недостаточно структурированной официальной базы. Неподтверждённые документы, сборы, сроки и пути записи не будут указываться произвольно. Пожалуйста, окончательно уточните в HiKorea, по телефону 1345 или в компетентном иммиграционном органе.',
      whatWeCanSay: 'Что Paradiso может безопасно сообщить',
      whatWeCannot: 'Что Paradiso не может подтвердить',
      officialChannels: 'Официальные каналы для уточнения',
      call1345: '1345 (Центр поддержки иностранцев)',
      hikoreaCta: 'Проверить мой путь записи в HiKorea',
      aiFollowupCta: 'Спросить о неясном в этом пакете',
      aiFollowupPlaceholder: 'Спросите о том, что вам непонятно в этом пакете. Например: можно ли освободить от пункта о подтверждении финансов?',
      aiPrivacyNote: 'Не вводите личные данные (имя, номер паспорта·карты иностранца, адрес, телефон и т. п.). Этот помощник только разъясняет пакет; он не создаёт новых официальных требований.',
      aiSend: 'Спросить',
      noDocs: 'Официальный список документов для этой процедуры ещё не структурирован.',
      verifyIntro: 'Пункты ниже здесь нельзя подтвердить по официальным источникам, уточните в компетентном органе/по телефону 1345/в HiKorea.',
      generatedOn: 'Создано',
      sourceVersion: 'Версия источника',
      disclaimerPrint: 'Окончательное подтверждение необходимо получить в HiKorea, по телефону 1345 или в компетентном органе по делам иммиграции·иностранцев.',
      langName: 'Русский',
      operatorDiag: 'Диагностика (оператор)'
    },
    fr: {
      title: 'Waymaker - Guide des procédures de séjour en Corée',
      subtitle: 'À partir de sources officielles, nous organisons votre procédure, vos documents, votre rendez-vous et votre prochaine action.',
      empty: "Vous n'avez pas besoin d'écrire une question d'abord. Choisissez votre statut de séjour actuel et ce que vous voulez faire.",
      start: 'Choisir ma situation',
      back: 'Retour',
      next: 'Suivant',
      restart: 'Recommencer',
      dontKnow: 'Je ne suis pas sûr(e)',
      stepLanguage: 'Choisissez votre langue',
      stepLocation: 'Où êtes-vous en ce moment ?',
      locIn: 'En Corée', locOut: 'Hors de Corée', locUnsure: 'Pas sûr(e) / cela dépend',
      stepStatus: 'Choisissez votre statut de séjour actuel',
      statusSearchPlaceholder: 'Rechercher par code ou nom (ex. : D-2, études, E-7)',
      statusUnknown: 'Je ne connais pas mon statut de séjour',
      statusFirstEntry: "Je n'ai pas encore de visa / je prépare une première entrée·délivrance de visa depuis l'étranger",
      noStatusResults: 'Aucun résultat. Essayez un code (ex. : D-2) ou le nom du statut en coréen.',
      programGroup: 'Programmes / projets pilotes (couverture officielle limitée)',
      stepProcedure: 'Quelle procédure vous faut-il ?',
      procedureLimitedHint: 'Couverture officielle limitée',
      stepSubStatus: 'Quel sous-type vous concerne ?',
      subStatusHelp: 'Les documents et critères peuvent varier selon le sous-type. En cas de doute, choisissez « Je ne suis pas sûr(e) ».',
      generating: 'Préparation de votre dossier de procédure fondé sur des sources officielles…',
      secProcedure: 'Ma procédure', secNext: 'Ce qu’il faut faire maintenant', secApplicability: 'Applicabilité',
      secDocs: 'Documents à préparer', secConditional: 'Documents supplémentaires selon la situation', secWhere: 'Où l’obtenir·comment préparer',
      secTiming: 'Délais·avertissements', secFees: 'Frais', secChannel: 'HiKorea / parcours de visite',
      secJurisdiction: 'Autorité compétente', secCoverage: 'Couverture des sources officielles', secVerify: 'Éléments à vérifier',
      grpCommon: 'Documents communs', grpRequired: 'Documents obligatoires', grpConditional: 'Documents selon la situation',
      grpAdditional: 'Documents supplémentaires', grpVerify: 'Vérifier auprès du bureau', grpNone: 'Base insuffisante',
      checklistTitle: 'Liste de contrôle des documents', checklistHint: 'Vos coches sont enregistrées uniquement dans ce navigateur.',
      checklistReset: 'Réinitialiser', checklistCopy: 'Copier', checklistPrint: 'Imprimer / exporter',
      checklistCopied: 'Liste de contrôle copiée dans le presse-papiers.',
      officialForm: 'Formulaire officiel',
      coverageLimitedTitle: 'Cette procédure a une couverture de sources officielles limitée',
      coverageLimited: "Paradiso ne dispose pas encore d'une couverture officielle structurée suffisante pour cette procédure. Il ne devinera ni documents, ni frais, ni délais, ni parcours de rendez-vous. Veuillez confirmer auprès de HiKorea, du 1345 ou du bureau d'immigration compétent.",
      whatWeCanSay: 'Ce que Paradiso peut dire en toute sécurité',
      whatWeCannot: 'Ce que Paradiso ne peut pas confirmer',
      officialChannels: 'Où confirmer officiellement',
      call1345: '1345 (Centre d’information pour les étrangers)',
      hikoreaCta: 'Vérifier mon parcours de rendez-vous HiKorea',
      aiFollowupCta: 'Poser une question sur ce dossier',
      aiFollowupPlaceholder: 'Posez une question sur ce dossier. Exemple : l’élément de preuve financière peut-il être dispensé ?',
      aiPrivacyNote: 'N’entrez pas d’identifiants personnels (nom, numéro de passeport·de carte d’étranger, adresse, téléphone). Cet assistant ne fait qu’expliquer le dossier ; il ne crée pas de nouvelles exigences officielles.',
      aiSend: 'Demander',
      noDocs: "La liste officielle des documents pour cette procédure n'est pas encore structurée.",
      verifyIntro: 'Les éléments ci-dessous ne peuvent pas être confirmés ici à partir de sources officielles. Confirmez auprès du bureau compétent, du 1345 ou de HiKorea.',
      generatedOn: 'Généré',
      sourceVersion: 'Version de la source',
      disclaimerPrint: 'La confirmation finale doit être faite auprès de HiKorea, du 1345 ou du bureau d’immigration·des étrangers compétent.',
      langName: 'Français',
      operatorDiag: 'Diagnostic (opérateur)'
    },
    es: {
      title: 'Waymaker - Guía de procedimientos de estancia en Corea',
      subtitle: 'A partir de fuentes oficiales, organizamos su procedimiento, documentos, cita y siguiente acción.',
      empty: 'No necesita escribir una pregunta primero. Elija su estatus de estancia actual y lo que quiere hacer.',
      start: 'Elegir mi situación',
      back: 'Atrás',
      next: 'Siguiente',
      restart: 'Empezar de nuevo',
      dontKnow: 'No estoy seguro/a',
      stepLanguage: 'Elija su idioma',
      stepLocation: '¿Dónde está ahora?',
      locIn: 'En Corea', locOut: 'Fuera de Corea', locUnsure: 'No estoy seguro/a / depende',
      stepStatus: 'Elija su estatus de estancia actual',
      statusSearchPlaceholder: 'Buscar por código o nombre (p. ej. D-2, estudios, E-7)',
      statusUnknown: 'No conozco mi estatus de estancia',
      statusFirstEntry: 'Todavía no tengo visado / estoy preparando la primera entrada·emisión de visado desde el extranjero',
      noStatusResults: 'Sin resultados. Pruebe con un código (p. ej. D-2) o el nombre del estatus en coreano.',
      programGroup: 'Programas / proyectos piloto (cobertura oficial limitada)',
      stepProcedure: '¿Qué procedimiento necesita?',
      procedureLimitedHint: 'Cobertura oficial limitada',
      stepSubStatus: '¿Qué subtipo le corresponde?',
      subStatusHelp: 'Los documentos y criterios pueden variar según el subtipo. Si no está seguro/a, elija «No estoy seguro/a».',
      generating: 'Preparando su paquete de procedimiento basado en fuentes oficiales…',
      secProcedure: 'Mi procedimiento', secNext: 'Qué hacer ahora', secApplicability: 'Aplicabilidad',
      secDocs: 'Documentos a preparar', secConditional: 'Documentos adicionales según la situación', secWhere: 'Dónde obtenerlo·cómo prepararlo',
      secTiming: 'Plazos·avisos', secFees: 'Tasas', secChannel: 'HiKorea / vía de visita',
      secJurisdiction: 'Autoridad competente', secCoverage: 'Cobertura de fuentes oficiales', secVerify: 'Elementos a verificar',
      grpCommon: 'Documentos comunes', grpRequired: 'Documentos obligatorios', grpConditional: 'Documentos según la situación',
      grpAdditional: 'Documentos adicionales', grpVerify: 'Verificar con la oficina', grpNone: 'Base insuficiente',
      checklistTitle: 'Lista de verificación de documentos', checklistHint: 'Sus marcas se guardan solo en este navegador.',
      checklistReset: 'Restablecer', checklistCopy: 'Copiar', checklistPrint: 'Imprimir / exportar',
      checklistCopied: 'Lista de verificación copiada al portapapeles.',
      officialForm: 'Formulario oficial',
      coverageLimitedTitle: 'Este procedimiento tiene una cobertura de fuentes oficiales limitada',
      coverageLimited: 'Paradiso aún no dispone de suficiente cobertura oficial estructurada para este procedimiento. No adivinará documentos, tasas, plazos ni vías de cita. Confirme con HiKorea, el 1345 o la oficina de inmigración competente.',
      whatWeCanSay: 'Lo que Paradiso puede decir con seguridad',
      whatWeCannot: 'Lo que Paradiso no puede confirmar',
      officialChannels: 'Dónde confirmar oficialmente',
      call1345: '1345 (Centro de Atención al Extranjero)',
      hikoreaCta: 'Comprobar mi vía de cita en HiKorea',
      aiFollowupCta: 'Preguntar sobre este paquete',
      aiFollowupPlaceholder: 'Pregunte sobre este paquete. Ejemplo: ¿podría eximirse el elemento de prueba financiera?',
      aiPrivacyNote: 'No introduzca datos personales (nombre, número de pasaporte·de tarjeta de extranjero, dirección, teléfono). Este asistente solo explica el paquete; no crea nuevos requisitos oficiales.',
      aiSend: 'Preguntar',
      noDocs: 'La lista oficial de documentos para este procedimiento aún no está estructurada.',
      verifyIntro: 'Los elementos siguientes no pueden confirmarse aquí a partir de fuentes oficiales. Confirme con la oficina competente, el 1345 o HiKorea.',
      generatedOn: 'Generado',
      sourceVersion: 'Versión de la fuente',
      disclaimerPrint: 'La confirmación final debe realizarse en HiKorea, el 1345 o la oficina de inmigración·extranjería competente.',
      langName: 'Español',
      operatorDiag: 'Diagnóstico (operador)'
    },
    ar: {
      title: 'Waymaker - دليل إجراءات الإقامة في كوريا',
      subtitle: 'استنادًا إلى المصادر الرسمية، ننظّم إجراءك ومستنداتك وحجزك وخطوتك التالية.',
      empty: 'لا حاجة لكتابة سؤال أولًا. اختر وضع إقامتك الحالي وما تريد فعله.',
      start: 'اختيار حالتي',
      back: 'رجوع',
      next: 'التالي',
      restart: 'البدء من جديد',
      dontKnow: 'لست متأكدًا',
      stepLanguage: 'اختر لغتك',
      stepLocation: 'أين أنت الآن؟',
      locIn: 'داخل كوريا', locOut: 'خارج كوريا', locUnsure: 'لست متأكدًا / حسب الحالة',
      stepStatus: 'اختر وضع إقامتك الحالي',
      statusSearchPlaceholder: 'ابحث بالرمز أو الاسم (مثل D-2، دراسة، E-7)',
      statusUnknown: 'لا أعرف وضع إقامتي',
      statusFirstEntry: 'ليس لديّ تأشيرة بعد / أُحضّر لأول دخول·إصدار تأشيرة من الخارج',
      noStatusResults: 'لا توجد نتائج. جرّب رمزًا (مثل D-2) أو اسم الوضع بالكورية.',
      programGroup: 'برامج / مشاريع تجريبية (السند الرسمي محدود)',
      stepProcedure: 'ما الإجراء الذي تحتاجه؟',
      procedureLimitedHint: 'السند الرسمي محدود',
      stepSubStatus: 'أي نوع فرعي ينطبق عليك؟',
      subStatusHelp: 'قد تختلف المستندات والمعايير حسب النوع الفرعي. إن لم تكن متأكدًا فاختر «لست متأكدًا».',
      generating: 'يجري إعداد حزمة الإجراء المستندة إلى المصادر الرسمية…',
      secProcedure: 'إجرائي', secNext: 'ما يجب فعله الآن', secApplicability: 'مدى الانطباق',
      secDocs: 'المستندات المطلوب تجهيزها', secConditional: 'مستندات إضافية حسب الحالة', secWhere: 'جهة الإصدار·طريقة التجهيز',
      secTiming: 'المواعيد·تنبيهات', secFees: 'الرسوم', secChannel: 'HiKorea / مسار الزيارة',
      secJurisdiction: 'الجهة المختصة', secCoverage: 'نطاق المصادر الرسمية', secVerify: 'بنود يلزم التأكد منها',
      grpCommon: 'مستندات مشتركة', grpRequired: 'مستندات إلزامية', grpConditional: 'مستندات حسب الحالة',
      grpAdditional: 'مستندات إضافية', grpVerify: 'التأكد لدى المكتب', grpNone: 'السند غير كافٍ',
      checklistTitle: 'قائمة مراجعة المستندات', checklistHint: 'تُحفظ علامات التحديد في هذا المتصفح فقط.',
      checklistReset: 'إعادة ضبط', checklistCopy: 'نسخ', checklistPrint: 'طباعة / تصدير',
      checklistCopied: 'تم نسخ قائمة المراجعة إلى الحافظة.',
      officialForm: 'نموذج رسمي',
      coverageLimitedTitle: 'هذا الإجراء له نطاق مصادر رسمية محدود',
      coverageLimited: 'لا يتوفر حتى الآن سند رسمي مُنظَّم كافٍ لهذا الإجراء. ولن يتم تخمين المستندات أو الرسوم أو المواعيد النهائية أو مسارات الحجز. يُرجى التأكيد النهائي لدى HiKorea أو 1345 أو مكتب الهجرة المختص.',
      whatWeCanSay: 'ما يمكن لـ Paradiso قوله بأمان',
      whatWeCannot: 'ما لا يمكن لـ Paradiso تأكيده',
      officialChannels: 'قنوات التأكيد الرسمية',
      call1345: '1345 (مركز الاستعلامات الشامل للأجانب)',
      hikoreaCta: 'تحقق من مسار حجز HiKorea الخاص بي',
      aiFollowupCta: 'اسأل عما يلتبس عليك في هذه الحزمة',
      aiFollowupPlaceholder: 'اسأل عما لا تفهمه في هذه الحزمة. مثال: هل يمكن إعفاء بند إثبات القدرة المالية؟',
      aiPrivacyNote: 'لا تُدخل معلومات شخصية (الاسم، رقم جواز السفر·رقم تسجيل الأجانب، العنوان، الهاتف). يشرح هذا المساعد الحزمة فقط ولا ينشئ متطلبات رسمية جديدة.',
      aiSend: 'اسأل',
      noDocs: 'لم تُنظَّم بعد قائمة المستندات الرسمية لهذا الإجراء.',
      verifyIntro: 'لا يمكن تأكيد البنود التالية من مصادر رسمية هنا، تأكّد لدى الجهة المختصة/1345/HiKorea.',
      generatedOn: 'تاريخ الإنشاء',
      sourceVersion: 'إصدار السند',
      disclaimerPrint: 'يجب إجراء التأكيد النهائي لدى HiKorea أو 1345 أو مكتب الهجرة·شؤون الأجانب المختص.',
      langName: 'العربية',
      operatorDiag: 'تشخيص (المشغّل)'
    },
    de: {
      title: 'Waymaker - Wegweiser für Aufenthaltsverfahren in Korea',
      subtitle: 'Auf Grundlage offizieller Quellen ordnen wir Ihr Verfahren, Ihre Unterlagen, Ihren Termin und Ihren nächsten Schritt.',
      empty: 'Sie müssen nicht zuerst eine Frage schreiben. Wählen Sie Ihren aktuellen Aufenthaltstitel und das, was Sie tun möchten.',
      start: 'Meine Situation wählen',
      back: 'Zurück',
      next: 'Weiter',
      restart: 'Von vorn beginnen',
      dontKnow: 'Ich bin nicht sicher',
      stepLanguage: 'Wählen Sie Ihre Sprache',
      stepLocation: 'Wo befinden Sie sich gerade?',
      locIn: 'In Korea', locOut: 'Außerhalb Koreas', locUnsure: 'Nicht sicher / kommt darauf an',
      stepStatus: 'Wählen Sie Ihren aktuellen Aufenthaltstitel',
      statusSearchPlaceholder: 'Nach Code oder Name suchen (z. B. D-2, Studium, E-7)',
      statusUnknown: 'Ich kenne meinen Aufenthaltstitel nicht',
      statusFirstEntry: 'Ich habe noch kein Visum / bereite die erste Einreise·Visumerteilung aus dem Ausland vor',
      noStatusResults: 'Keine Treffer. Versuchen Sie einen Code (z. B. D-2) oder den koreanischen Statusnamen.',
      programGroup: 'Programme / Pilotprojekte (begrenzte offizielle Grundlage)',
      stepProcedure: 'Welches Verfahren benötigen Sie?',
      procedureLimitedHint: 'Begrenzte offizielle Grundlage',
      stepSubStatus: 'Welcher Untertyp trifft auf Sie zu?',
      subStatusHelp: 'Unterlagen und Kriterien können je nach Untertyp unterschiedlich sein. Wenn Sie unsicher sind, wählen Sie „Ich bin nicht sicher“.',
      generating: 'Ihr auf offiziellen Quellen basierendes Verfahrenspaket wird vorbereitet…',
      secProcedure: 'Mein Verfahren', secNext: 'Was jetzt zu tun ist', secApplicability: 'Anwendbarkeit',
      secDocs: 'Vorzubereitende Unterlagen', secConditional: 'Zusätzliche Unterlagen je nach Situation', secWhere: 'Wo erhältlich·wie vorzubereiten',
      secTiming: 'Fristen·Hinweise', secFees: 'Gebühren', secChannel: 'HiKorea / Besuchsweg',
      secJurisdiction: 'Zuständige Behörde', secCoverage: 'Abdeckung durch offizielle Quellen', secVerify: 'Zu prüfende Punkte',
      grpCommon: 'Allgemeine Unterlagen', grpRequired: 'Erforderliche Unterlagen', grpConditional: 'Unterlagen je nach Situation',
      grpAdditional: 'Zusätzliche Unterlagen', grpVerify: 'Bei der Behörde prüfen', grpNone: 'Grundlage nicht ausreichend',
      checklistTitle: 'Unterlagen-Checkliste', checklistHint: 'Ihre Markierungen werden nur in diesem Browser gespeichert.',
      checklistReset: 'Zurücksetzen', checklistCopy: 'Kopieren', checklistPrint: 'Drucken / exportieren',
      checklistCopied: 'Checkliste in die Zwischenablage kopiert.',
      officialForm: 'Amtliches Formular',
      coverageLimitedTitle: 'Dieses Verfahren hat eine begrenzte Abdeckung durch offizielle Quellen',
      coverageLimited: 'Paradiso verfügt für dieses Verfahren noch nicht über genügend strukturierte offizielle Quellengrundlage. Es errät keine Unterlagen, Gebühren, Fristen oder Terminwege. Bitte bestätigen Sie dies bei HiKorea, unter 1345 oder bei der zuständigen Einwanderungsbehörde.',
      whatWeCanSay: 'Was Paradiso sicher sagen kann',
      whatWeCannot: 'Was Paradiso nicht bestätigen kann',
      officialChannels: 'Wo offiziell zu bestätigen',
      call1345: '1345 (Beratungszentrum für Ausländer)',
      hikoreaCta: 'Meinen HiKorea-Terminweg prüfen',
      aiFollowupCta: 'Zu diesem Paket nachfragen',
      aiFollowupPlaceholder: 'Fragen Sie zu diesem Paket. Beispiel: Kann der Nachweis der finanziellen Mittel erlassen werden?',
      aiPrivacyNote: 'Geben Sie keine persönlichen Daten ein (Name, Pass-·Ausländerregisternummer, Adresse, Telefon). Dieser Helfer erklärt nur das Paket; er erstellt keine neuen offiziellen Anforderungen.',
      aiSend: 'Fragen',
      noDocs: 'Die offizielle Unterlagenliste für dieses Verfahren ist noch nicht strukturiert.',
      verifyIntro: 'Die folgenden Punkte können hier nicht aus offiziellen Quellen bestätigt werden. Bestätigen Sie sie bei der zuständigen Behörde, unter 1345 oder bei HiKorea.',
      generatedOn: 'Erstellt',
      sourceVersion: 'Quellenversion',
      disclaimerPrint: 'Die endgültige Bestätigung muss bei HiKorea, unter 1345 oder bei der zuständigen Einwanderungs-·Ausländerbehörde erfolgen.',
      langName: 'Deutsch',
      operatorDiag: 'Diagnose (Betreiber)'
    },
  tr: {
    "title": "Waymaker - Kore İkamet Prosedürü Navigatörü",
    "subtitle": "İkamet statünüzü ve durumunuzu resmi kaynağa dayalı bir prosedüre, kontrol listesine, randevu yoluna ve sonraki adıma dönüştürün.",
    "empty": "Bir soru yazmanıza gerek yok. Mevcut ikamet statünüz ve yapmanız gereken işlemle başlayın.",
    "start": "Durumumu seç",
    "back": "Geri",
    "next": "İleri",
    "restart": "Baştan başla",
    "dontKnow": "Emin değilim",
    "stepLanguage": "Dilinizi seçin",
    "stepLocation": "Şu anda neredesiniz?",
    "locIn": "Kore'de",
    "locOut": "Kore dışında",
    "locUnsure": "Emin değilim / duruma göre değişir",
    "stepStatus": "Mevcut ikamet statünüzü seçin",
    "statusSearchPlaceholder": "Kod veya adla arayın (örn. D-2, öğrenim, E-7)",
    "statusUnknown": "İkamet statümü bilmiyorum",
    "statusFirstEntry": "Henüz vizem yok / yurt dışından ilk giriş veya vize verilmesi için hazırlanıyorum",
    "noStatusResults": "Eşleşme yok. Bir kod (örn. D-2) veya Korece statü adıyla deneyin.",
    "programGroup": "Programlar / pilot uygulamalar (sınırlı resmi kaynak)",
    "stepProcedure": "Ne yapmanız gerekiyor?",
    "procedureLimitedHint": "Sınırlı kaynak kapsamı",
    "stepSubStatus": "Hangi alt tür size uygun?",
    "subStatusHelp": "Belgeler ve kriterler alt türe göre değişebilir. Emin değilseniz \"Emin değilim\" seçeneğini seçin.",
    "generating": "Resmi kaynağa dayalı prosedür paketiniz hazırlanıyor…",
    "secProcedure": "Prosedürüm",
    "secNext": "Sonraki adımda ne yapmalı",
    "secDecision": "Karar vermeden önce hazırlanacak bilgiler",
    "secApplicability": "Uygulanabilirlik",
    "secDocs": "Hazırlanacak belgeler",
    "secConditional": "Duruma bağlı belgeler",
    "secWhere": "Her belgeyi nereden alabilirsiniz",
    "secTiming": "Zamanlama ve riskler",
    "secFees": "Ücretler",
    "secChannel": "HiKorea / ziyaret kanalı",
    "secJurisdiction": "Yetki alanı",
    "secCoverage": "Resmi kaynak kapsamı",
    "secVerify": "Doğrulanması gereken maddeler",
    "grpCommon": "Ortak belgeler",
    "grpRequired": "Zorunlu belgeler",
    "grpConditional": "Duruma bağlı belgeler",
    "grpAdditional": "Ek belgeler",
    "grpVerify": "Yetkili kurumla doğrulayın",
    "grpNone": "Yeterli kaynak kapsamı yok",
    "checklistTitle": "Belge kontrol listesi",
    "checklistHint": "İşaretlemeleriniz yalnızca bu tarayıcıda kaydedilir.",
    "checklistReset": "Sıfırla",
    "checklistCopy": "Kopyala",
    "checklistPrint": "Yazdır / dışa aktar",
    "checklistCopied": "Kontrol listesi panoya kopyalandı.",
    "officialForm": "Resmi form",
    "coverageLimitedTitle": "Bu prosedürün resmi kaynak kapsamı sınırlıdır",
    "coverageLimited": "Paradiso, bu prosedür için henüz yeterince yapılandırılmış resmi kaynak kapsamına sahip değil. Belgeleri, ücretleri, son tarihleri veya randevu yollarını tahmin etmeyecektir. Lütfen HiKorea, 1345 veya yetkili göç idaresiyle teyit edin.",
    "whatWeCanSay": "Paradiso'nun güvenle söyleyebileceği bilgiler",
    "whatWeCannot": "Paradiso'nun doğrulayamadığı bilgiler",
    "officialChannels": "Resmi olarak nerede teyit edilir",
    "call1345": "1345 (Göç İletişim Merkezi)",
    "hikoreaCta": "HiKorea randevu yolumu kontrol et",
    "formHelperCta": "Başvuru formu doldurma yardımcısına devam et",
    "aiFollowupCta": "Bu paket hakkında soru sor",
    "aiFollowupPlaceholder": "Bu paket hakkında soru sorun. Örnek: Mali belge maddesi muaf tutulabilir mi?",
    "aiPrivacyNote": "Kişisel kimlik bilgilerinizi (ad, pasaport/yabancı kayıt numarası, adres, telefon) girmeyin. Bu yardımcı yalnızca paketi açıklar; yeni resmi gereklilikler oluşturmaz.",
    "aiSend": "Sor",
    "aiFollowupFailed": "Şu anda bir yanıt alamadık. Birazdan tekrar deneyin veya 1345 ya da HiKorea'dan kontrol edin.",
    "aiSafetyKicker": "Güvenlik nedeniyle yardımcı olamayacağımız bir istek",
    "aiSafetyAltTitle": "Bunun yerine yardımcı olabileceğim konular",
    "resumeScenarioTitle": "Kaldığınız yerden devam edilsin mi?",
    "resumeScenarioLabelPrefix": "Önceden seçilen: ",
    "resumeScenarioContinue": "Devam et",
    "resumeScenarioRestart": "Baştan başla",
    "noDocs": "Bu prosedür için resmi belge listesi henüz yapılandırılmadı.",
    "verifyIntro": "Aşağıdaki maddeler burada resmi kaynaklardan doğrulanamaz. Yetkili kurum, 1345 veya HiKorea ile teyit edin.",
    "generatedOn": "Oluşturulma tarihi",
    "sourceVersion": "Kaynak sürümü",
    "disclaimerPrint": "Nihai teyit HiKorea, 1345 veya yetkili göç ve yabancılar idaresi ile yapılmalıdır.",
    "langName": "Türkçe",
    "operatorDiag": "Tanılama (operatör)"
  },
  uk: {
    "title": "Waymaker - Навігатор імміграційних процедур Кореї",
    "subtitle": "Перетворіть свій статус і ситуацію на процедуру, підкріплену офіційним джерелом, контрольний список, шлях бронювання та наступну дію.",
    "empty": "Вам не потрібно писати запитання. Почніть із поточного статусу перебування та того, що вам потрібно зробити.",
    "start": "Обрати мою ситуацію",
    "back": "Назад",
    "next": "Далі",
    "restart": "Почати спочатку",
    "dontKnow": "Я не впевнений(-а)",
    "stepLanguage": "Оберіть мову",
    "stepLocation": "Де ви зараз перебуваєте?",
    "locIn": "У Кореї",
    "locOut": "За межами Кореї",
    "locUnsure": "Не впевнений(-а) / залежить від ситуації",
    "stepStatus": "Оберіть свій поточний статус перебування",
    "statusSearchPlaceholder": "Пошук за кодом або назвою (напр. D-2, навчання, E-7)",
    "statusUnknown": "Я не знаю свій статус",
    "statusFirstEntry": "У мене ще немає візи / готуюся до першого в'їзду або видачі візи з-за кордону",
    "noStatusResults": "Немає збігів. Спробуйте код (напр. D-2) або корейську назву статусу.",
    "programGroup": "Програми / пілотні проєкти (обмежене офіційне покриття)",
    "stepProcedure": "Що вам потрібно зробити?",
    "procedureLimitedHint": "Обмежене покриття джерел",
    "stepSubStatus": "Який підтип вам підходить?",
    "subStatusHelp": "Документи та критерії можуть відрізнятися залежно від підтипу. Якщо не впевнені, оберіть \"Я не впевнений(-а)\".",
    "generating": "Готуємо ваш пакет процедур, підкріплений джерелами…",
    "secProcedure": "Моя процедура",
    "secNext": "Що робити далі",
    "secDecision": "Інформація, яку слід підготувати перед прийняттям рішення",
    "secApplicability": "Застосовність",
    "secDocs": "Документи для підготовки",
    "secConditional": "Умовні документи",
    "secWhere": "Де отримати кожен документ",
    "secTiming": "Терміни та ризики",
    "secFees": "Збори",
    "secChannel": "HiKorea / канал відвідування",
    "secJurisdiction": "Юрисдикція",
    "secCoverage": "Покриття офіційними джерелами",
    "secVerify": "Пункти для перевірки",
    "grpCommon": "Загальні документи",
    "grpRequired": "Обов'язкові документи",
    "grpConditional": "Умовні документи",
    "grpAdditional": "Додаткові документи",
    "grpVerify": "Перевірте в компетентному органі",
    "grpNone": "Недостатнє покриття джерел",
    "checklistTitle": "Контрольний список документів",
    "checklistHint": "Ваші позначки зберігаються лише в цьому браузері.",
    "checklistReset": "Скинути",
    "checklistCopy": "Копіювати",
    "checklistPrint": "Друк / експорт",
    "checklistCopied": "Контрольний список скопійовано в буфер обміну.",
    "officialForm": "Офіційна форма",
    "coverageLimitedTitle": "Ця процедура має обмежене покриття офіційними джерелами",
    "coverageLimited": "Paradiso ще не має достатнього структурованого покриття офіційними джерелами для цієї процедури. Він не вгадуватиме документи, збори, терміни чи шляхи бронювання. Будь ласка, підтвердіть у HiKorea, 1345 або компетентному імміграційному органі.",
    "whatWeCanSay": "Що Paradiso може безпечно повідомити",
    "whatWeCannot": "Що Paradiso не може підтвердити",
    "officialChannels": "Де підтвердити офіційно",
    "call1345": "1345 (Контакт-центр для іноземців)",
    "hikoreaCta": "Перевірити мій шлях бронювання HiKorea",
    "formHelperCta": "Перейти до помічника заповнення заяви",
    "aiFollowupCta": "Запитати про цей пакет",
    "aiFollowupPlaceholder": "Запитайте про цей пакет. Приклад: Чи можна звільнити від пункту про фінансові документи?",
    "aiPrivacyNote": "Не вводьте персональні ідентифікатори (ім'я, номер паспорта/картки іноземця, адресу, телефон). Цей помічник лише пояснює пакет; він не створює нових офіційних вимог.",
    "aiSend": "Запитати",
    "aiFollowupFailed": "Наразі не вдалося отримати відповідь. Спробуйте ще раз за мить або зверніться до 1345 чи HiKorea.",
    "aiSafetyKicker": "Запит, з яким ми не можемо допомогти з міркувань безпеки",
    "aiSafetyAltTitle": "З чим я можу допомогти натомість",
    "resumeScenarioTitle": "Продовжити з того місця, де ви зупинилися?",
    "resumeScenarioLabelPrefix": "Раніше обрано: ",
    "resumeScenarioContinue": "Продовжити",
    "resumeScenarioRestart": "Почати спочатку",
    "noDocs": "Офіційний список документів для цієї процедури ще не структуровано.",
    "verifyIntro": "Наведені нижче пункти неможливо підтвердити з офіційних джерел тут. Підтвердіть у компетентному органі, 1345 або HiKorea.",
    "generatedOn": "Створено",
    "sourceVersion": "Версія джерела",
    "disclaimerPrint": "Остаточне підтвердження має бути зроблено в HiKorea, 1345 або компетентному органі з питань імміграції та іноземців.",
    "langName": "Українська",
    "operatorDiag": "Діагностика (оператор)"
  }
};

  var PROCEDURE_LABELS = {
    visaIssuance: {
      ko: '사증발급 / 최초 입국', en: 'Visa issuance / first entry', 'zh-CN': '签证签发 / 首次入境',
      ja: '査証発給 / 初回入国', vi: 'Cấp visa / nhập cảnh lần đầu', tl: 'Pag-isyu ng visa / unang pagpasok',
      id: 'Penerbitan visa / masuk pertama', ru: 'Выдача визы / первый въезд', fr: 'Délivrance de visa / première entrée',
      es: 'Emisión de visado / primera entrada', ar: 'إصدار التأشيرة / أول دخول', de: 'Visumerteilung / Ersteinreise', tr: "Vize verilmesi / ilk giriş", uk: "Видача візи / перший в'їзд"
    },
    registration: {
      ko: '외국인등록', en: 'Alien registration', 'zh-CN': '外国人登录',
      ja: '外国人登録', vi: 'Đăng ký người nước ngoài', tl: 'Pagpaparehistro ng dayuhan',
      id: 'Registrasi orang asing', ru: 'Регистрация иностранца', fr: 'Enregistrement des étrangers',
      es: 'Registro de extranjero', ar: 'تسجيل الأجانب', de: 'Ausländerregistrierung', tr: "Yabancı kaydı", uk: "Реєстрація іноземця"
    },
    extension: {
      ko: '체류기간 연장', en: 'Extension of stay', 'zh-CN': '居留期限延长',
      ja: '滞在期間の延長', vi: 'Gia hạn thời gian cư trú', tl: 'Pagpapahaba ng pananatili',
      id: 'Perpanjangan masa tinggal', ru: 'Продление срока пребывания', fr: 'Prolongation de séjour',
      es: 'Prórroga de estancia', ar: 'تمديد مدة الإقامة', de: 'Verlängerung des Aufenthalts', tr: "İkamet süresinin uzatılması", uk: "Продовження строку перебування"
    },
    statusChange: {
      ko: '체류자격 변경', en: 'Change of status', 'zh-CN': '居留资格变更',
      ja: '滞在資格の変更', vi: 'Thay đổi tư cách cư trú', tl: 'Pagbabago ng status',
      id: 'Perubahan status tinggal', ru: 'Изменение статуса пребывания', fr: 'Changement de statut',
      es: 'Cambio de estatus', ar: 'تغيير وضع الإقامة', de: 'Änderung des Aufenthaltstitels', tr: "Statü değişikliği", uk: "Зміна статусу"
    },
    statusGrant: {
      ko: '체류자격 부여', en: 'Grant of status', 'zh-CN': '居留资格赋予',
      ja: '滞在資格の付与', vi: 'Cấp tư cách cư trú', tl: 'Pagkakaloob ng status',
      id: 'Pemberian status tinggal', ru: 'Предоставление статуса пребывания', fr: 'Octroi du statut',
      es: 'Concesión de estatus', ar: 'منح وضع الإقامة', de: 'Erteilung des Aufenthaltstitels', tr: "Statü verilmesi", uk: "Надання статусу"
    },
    workplaceChange: {
      ko: '근무처 변경·추가', en: 'Workplace change / addition', 'zh-CN': '工作单位变更·追加',
      ja: '勤務先の変更・追加', vi: 'Thay đổi·bổ sung nơi làm việc', tl: 'Pagbabago / pagdaragdag ng pinagtatrabahuhan',
      id: 'Perubahan·penambahan tempat kerja', ru: 'Изменение·добавление места работы', fr: 'Changement / ajout de lieu de travail',
      es: 'Cambio / adición de centro de trabajo', ar: 'تغيير·إضافة جهة العمل', de: 'Wechsel / Hinzufügung des Arbeitsplatzes', tr: "İş yeri değişikliği·eklenmesi", uk: "Зміна·додавання місця роботи"
    },
    activitiesOutsideStatus: {
      ko: '체류자격외 활동', en: 'Activities outside status', 'zh-CN': '资格外活动',
      ja: '資格外活動', vi: 'Hoạt động ngoài tư cách', tl: 'Mga aktibidad na labas sa status',
      id: 'Kegiatan di luar status', ru: 'Деятельность вне статуса', fr: 'Activités hors statut',
      es: 'Actividades fuera del estatus', ar: 'نشاط خارج وضع الإقامة', de: 'Tätigkeiten außerhalb des Status', tr: "Statü dışı faaliyet", uk: "Діяльність поза статусом"
    },
    reentry: {
      ko: '재입국허가', en: 'Re-entry permit', 'zh-CN': '再入境许可',
      ja: '再入国許可', vi: 'Giấy phép tái nhập cảnh', tl: 'Re-entry permit',
      id: 'Izin masuk kembali', ru: 'Разрешение на повторный въезд', fr: 'Permis de réadmission',
      es: 'Permiso de reingreso', ar: 'تصريح إعادة الدخول', de: 'Wiedereinreisegenehmigung', tr: "Yeniden giriş izni", uk: "Дозвіл на повторний в'їзд"
    }
  };

  function t(locale, key) {
    var pack = STRINGS[locale] || STRINGS.ko;
    return (pack[key] != null) ? pack[key] : (STRINGS.ko[key] != null ? STRINGS.ko[key] : key);
  }
  function procedureLabel(key, locale) {
    var l = PROCEDURE_LABELS[key];
    if (!l) return key;
    return l[locale] || ((locale === 'en') ? l.en : l.ko);
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
    // Optional handoff from a host page (e.g. index.html's floating Waymaker
    // CTA): { visaCode, procedureKey, label }. Only offered as a confirmable
    // resume prompt on the intro step, never auto-applied without the user
    // choosing "continue" — the navigator never assumes an eligibility/status
    // match on its own.
    var initialScenario = (options.initialScenario && options.initialScenario.visaCode) ? options.initialScenario : null;
    var CHECKLIST_NS = 'paradiso_waymaker_checklist_v1';
    var LOCALE_KEY = 'paradiso_waymaker_locale';
    // Content locales the navigator can render (ko is the fallback). zh-TW is a
    // display layer over zh-CN, not its own content pack — handled separately.
    var CONTENT_LOCALES = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
    // All raw selections that may flow in from URL / localStorage / global / html
    // lang (includes the zh-TW display variant).
    var RAW_LOCALES = ['ko', 'en', 'zh-CN', 'zh-TW', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
    function isContentLocale(x) { return CONTENT_LOCALES.indexOf(x) !== -1; }
    function isRawLocale(x) { return RAW_LOCALES.indexOf(x) !== -1; }

    var catalog = null;
    var state = {
      step: 'intro',
      locale: resolveInitialLocale(),
      tradCN: rawSelection() === 'zh-TW',
      location: null,
      statusEntry: null,
      statusCode: null,
      exactStatusCode: null,
      subStatusKnown: false,
      procedureKey: null,
      packet: null,
      pendingScenario: initialScenario,
      returnStep: 'location'
    };

    // Raw selection across all sources, including the global Paradiso language
    // key shared with index.html. May be 'ko' | 'en' | 'zh-CN' | 'zh-TW'.
    function rawSelection() {
      try {
        if (global.location && global.URLSearchParams) {
          var ul = (new global.URLSearchParams(global.location.search).get('lang') || '');
          if (ul === 'zh-CN' || ul === 'zh-TW') return ul;
          var two = ul.toLowerCase().slice(0, 2);
          if (isRawLocale(two)) return two;
        }
      } catch (e) {}
      try {
        var wmStored = global.localStorage && global.localStorage.getItem(LOCALE_KEY);
        if (isRawLocale(wmStored)) return wmStored;
        var g = global.localStorage && global.localStorage.getItem('paradiso:language');
        if (isRawLocale(g)) return g;
      } catch (e) {}
      if (isRawLocale(global.PARADISO_LANG)) return global.PARADISO_LANG;
      var htmlLang = (doc.documentElement.getAttribute('lang') || '');
      if (htmlLang === 'zh-TW') return 'zh-TW';
      if (htmlLang.slice(0, 2) === 'zh') return 'zh-CN';
      var htmlTwo = htmlLang.toLowerCase().slice(0, 2);
      if (isRawLocale(htmlTwo)) return htmlTwo;
      return 'ko';
    }
    // Traditional Chinese is a display layer over the zh-CN content (same as
    // index.html). Content always renders in one of ko/en/zh-CN.
    function contentLocale(raw) {
      // zh-TW renders zh-CN content with a Traditional display layer on top.
      if (raw === 'zh-TW' || raw === 'zh-CN') return 'zh-CN';
      return isContentLocale(raw) ? raw : 'ko';
    }
    function resolveInitialLocale() { return contentLocale(rawSelection()); }
    function applyTradLayer(on) {
      try {
        var zt = global.ParadisoZhT;
        if (!zt) return;
        if (on) { if (!zt.isActive()) zt.start(); }
        else if (zt.isActive()) { zt.stop(); }
      } catch (e) {}
    }
    function persistLocale() {
      try { global.localStorage && global.localStorage.setItem(LOCALE_KEY, state.tradCN ? 'zh-TW' : state.locale); } catch (e) {}
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
      // Language is a preference, not work the user must complete.  The actual
      // procedure flow is location → status → goal → optional subtype.
      var steps = ['location', 'status', 'procedure', 'subStatus'];
      var idx = steps.indexOf(state.step);
      var showProgress = idx !== -1;
      var LANG_ORDER = ['ko', 'en', 'zh-CN', 'zh-TW', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
      var LANG_SHORT = {
        ko: '한', en: 'EN', 'zh-CN': '简', 'zh-TW': '繁', ja: '日', vi: 'VI',
        tl: 'TL', id: 'ID', ru: 'RU', fr: 'FR', es: 'ES', ar: 'ع', de: 'DE', tr: 'TR', uk: 'UK'
      };
      var LANG_ARIA = {
        ko: '언어: 한국어', en: 'Language: English', 'zh-CN': '语言：简体中文', 'zh-TW': '語言：繁體中文',
        ja: '言語：日本語', vi: 'Ngôn ngữ: Tiếng Việt', tl: 'Wika: Filipino', id: 'Bahasa: Bahasa Indonesia',
        ru: 'Язык: Русский', fr: 'Langue : Français', es: 'Idioma: Español', ar: 'اللغة: العربية', de: 'Sprache: Deutsch', tr: 'Dil: Türkçe', uk: 'Мова: Українська'
      };
      var curLang = state.tradCN ? 'zh-TW' : state.locale;
      var nextLang = LANG_ORDER[(LANG_ORDER.indexOf(curLang) + 1) % LANG_ORDER.length];
      var langBtn = h('button', {
        class: 'wm-lang-toggle', type: 'button', 'data-s2t': 'off',
        aria: { label: LANG_ARIA[curLang] || LANG_ARIA.ko },
        onclick: function () {
          state.returnStep = (state.step && state.step !== 'language') ? state.step : 'location';
          goto('language');
        }
      }, [LANG_SHORT[curLang] || '한']);
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
      var nodes = [];
      var scenario = state.pendingScenario;
      var matchedEntry = scenario ? findCatalogEntry(scenario.visaCode) : null;
      if (scenario && matchedEntry) {
        var label = scenario.label || (matchedEntry.code + ' · ' + matchedEntry.name);
        nodes.push(h('div', { class: 'wm-card', role: 'note' }, [
          h('p', { class: 'wm-context-line', text: L('resumeScenarioTitle') }),
          h('p', { class: 'wm-muted', text: L('resumeScenarioLabelPrefix') + label }),
          h('div', { class: 'wm-step-nav' }, [
            h('button', {
              class: 'wm-btn wm-btn-primary', type: 'button',
              onclick: function () { resumeScenario(scenario, matchedEntry); }
            }, [L('resumeScenarioContinue')]),
            h('button', {
              class: 'wm-btn wm-btn-ghost', type: 'button',
              onclick: function () { state.pendingScenario = null; goto('location'); }
            }, [L('resumeScenarioRestart')])
          ])
        ]));
      }
      nodes.push(h('p', { class: 'wm-empty', text: L('empty') }));
      nodes.push(h('button', {
        class: 'wm-btn wm-btn-primary wm-btn-lg', type: 'button',
        onclick: function () { state.pendingScenario = null; goto('location'); }
      }, [L('start')]));
      return h('section', { class: 'wm-step wm-intro' }, nodes);
    }

    function renderLanguage() {
      var curLang = state.tradCN ? 'zh-TW' : state.locale;
      function langChip(label, loc) {
        return chip(label, curLang === loc, function () {
          var target = state.returnStep || 'location';
          setLocale(loc);
          track('waymaker_language_selected', { locale: loc });
          goto(target === 'language' ? 'location' : target);
        });
      }
      var ko = langChip('한국어', 'ko');
      var en = langChip('English', 'en');
      // The two Chinese chips must keep their own script regardless of the
      // active Traditional display layer.
      var zhCN = langChip('简体中文', 'zh-CN'); zhCN.setAttribute('data-s2t', 'off');
      var zhTW = langChip('繁體中文', 'zh-TW'); zhTW.setAttribute('data-s2t', 'off');
      // Each additional content locale, labelled in its own script via langName.
      // data-s2t=off keeps the Traditional layer from mangling these scripts.
      var more = ['ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de'].map(function (loc) {
        var c = langChip(t(loc, 'langName'), loc);
        c.setAttribute('data-s2t', 'off');
        if (loc === 'ar') c.setAttribute('dir', 'rtl');
        return c;
      });
      return stepShell('language', L('stepLanguage'), [
        chipGrid([ko, en, zhCN, zhTW].concat(more))
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
      ], 'intro');
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
    function setLocale(loc) {
      state.tradCN = (loc === 'zh-TW');
      state.locale = contentLocale(loc);
      persistLocale();
      applyTradLayer(state.tradCN);
      render();
    }
    function goto(step) { state.step = step; render(); }
    function restart() {
      state.location = null; state.statusEntry = null; state.statusCode = null;
      state.exactStatusCode = null; state.subStatusKnown = false; state.procedureKey = null; state.packet = null;
      state.pendingScenario = null;
      goto('intro');
    }
    function chooseStatus(m) {
      state.statusEntry = m; state.statusCode = m.code; state.exactStatusCode = m.code; state.subStatusKnown = false;
      track('waymaker_status_selected', { locale: state.locale, statusFamily: parentCode(m.code), isProgram: !!m.isProgram });
      goto('procedure');
    }
    // Resolve a handed-off visa code against the loaded catalog. Subcodes
    // (e.g. D-2-1) are resolved to their parent entry for matching, same as
    // status selection elsewhere in this file — the exact subcode is not
    // asserted here; the existing sub-status clarification step still runs.
    function findCatalogEntry(rawCode) {
      if (!rawCode || !catalog) return null;
      var code = String(rawCode).trim().toUpperCase();
      var i;
      for (i = 0; i < catalog.length; i++) { if (catalog[i].code === code) return catalog[i]; }
      var parent = parentCode(code);
      if (parent && parent !== code) {
        for (i = 0; i < catalog.length; i++) { if (catalog[i].code === parent) return catalog[i]; }
      }
      return null;
    }
    // Continue from a handed-off scenario: select the matched status, and the
    // handed-off procedure only if it is actually offered for that status.
    // Never skips the existing sub-status clarification step — this only
    // saves re-picking status + procedure, it does not assert an exact match.
    function resumeScenario(scenario, entry) {
      state.pendingScenario = null;
      chooseStatus(entry);
      var procedureKey = scenario.procedureKey;
      if (!procedureKey) return;
      var procs = proceduresForStatus(entry);
      var i, valid = false;
      for (i = 0; i < procs.length; i++) { if (procs[i].procedureKey === procedureKey) { valid = true; break; } }
      if (valid) chooseProcedure(procedureKey);
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
    // A packet is renderable only if it is a real object: the render path
    // dereferences packet fields (packet._unknownStatus, packet.documents,
    // packet.titleKo …) and would throw on a null/non-object body, stranding
    // the user on the loading spinner. Guard against that shape here.
    function isRenderablePacket(packet) {
      return !!packet && typeof packet === 'object';
    }
    // Route any generate failure — a 200 with a malformed body, or the render
    // path throwing — to the SAME safe coverage-limited shell that fetchPacket's
    // own network failures produce, flagged so the packet view offers a retry.
    function generatePacketFailed(code) {
      var shell = makeCoverageLimitedShell(code, state.procedureKey, null);
      shell._error = true;
      state.packet = shell;
      goto('packet');
    }
    function generatePacket() {
      goto('loading');
      var code = state.exactStatusCode || state.statusCode;
      fetchPacket(code, state.procedureKey).then(function (packet) {
        if (!isRenderablePacket(packet)) { generatePacketFailed(code); return; }
        state.packet = packet;
        var cov = deriveCoverage(packet);
        track('waymaker_packet_rendered', { locale: state.locale, statusFamily: parentCode(state.statusCode), procedureKey: state.procedureKey, packetType: packet.packetType, coverageLevel: cov.level });
        track('waymaker_source_coverage_level', { coverageLevel: cov.level });
        if (cov.isLimited) track('waymaker_packet_limited', { locale: state.locale, procedureKey: state.procedureKey, coverageLevel: cov.level });
        goto('packet');
      }).catch(function () { generatePacketFailed(code); });
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
        backToProcedure: function () { goto('procedure'); },
        retry: function () { generatePacket(); }
      };
    }

    // ---- boot ------------------------------------------------------------
    function mount() {
      applyTradLayer(state.tradCN);
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
      // The packet may be source-limited, but it can still tell the user which
      // facts to collect and which exact questions to ask the competent office.
      var decisionSupport = this.sectionDecisionSupport(c, packet);
      if (decisionSupport) wrap.appendChild(decisionSupport);

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

    sectionDecisionSupport: function (c, packet) {
      var support = packet.decisionSupport || {};
      var facts = support.factsKo || [];
      var questions = support.officialQuestionsKo || [];
      if (!facts.length && !questions.length) return null;
      var nodes = [];
      if (facts.length) {
        nodes.push(c.h('div', { class: 'wm-decision-col' }, [
          c.h('div', { class: 'wm-subhead', text: c.locale === 'en' ? 'Facts to collect' : '먼저 정리할 사실' }),
          c.h('ul', { class: 'wm-decision-list' }, facts.map(function (item) { return c.h('li', { text: item }); }))
        ]));
      }
      if (questions.length) {
        nodes.push(c.h('div', { class: 'wm-decision-col' }, [
          c.h('div', { class: 'wm-subhead', text: c.locale === 'en' ? 'Ask 1345 / the office' : '1345·관할기관에 물을 질문' }),
          c.h('ul', { class: 'wm-decision-list' }, questions.map(function (item) { return c.h('li', { text: item }); }))
        ]));
      }
      return c.h('div', { class: 'wm-card wm-card-decision' }, [
        c.h('div', { class: 'wm-kicker', text: c.L('secDecision') }),
        c.h('div', { class: 'wm-decision-grid' }, nodes)
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
      var card = c.h('div', { class: 'wm-card wm-card-warn', role: 'note' }, [
        c.h('div', { class: 'wm-warn-title', text: c.L('coverageLimitedTitle') }),
        c.h('p', { class: 'wm-warn-body', text: c.L('coverageLimited') }),
        c.h('div', { class: 'wm-warn-channels' }, [
          c.h('div', { class: 'wm-subhead', text: c.L('officialChannels') }),
          channels
        ])
      ]);
      // A shell produced by a failed generate (not a real 400/503 coverage gap)
      // offers a retry so a transient error isn't terminal — reusing the same
      // generate path. Official-channel guidance above stays intact either way.
      if (packet && packet._error && typeof c.retry === 'function') {
        card.appendChild(c.h('button', {
          class: 'wm-btn wm-btn-secondary', type: 'button', onclick: c.retry
        }, [c.L('retry')]));
      }
      return card;
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
      var fh = packet.formHelper || {};
      if (fh.formId && fh.type) {
        var formUrl = 'form-helper.html?source=waymaker&visa=' + encodeURIComponent(packet.statusCode || '')
          + '&procedure=' + encodeURIComponent(packet.packetType || '')
          + '&form=' + encodeURIComponent(fh.formId)
          + '&type=' + encodeURIComponent(fh.type);
        bar.appendChild(c.h('a', {
          class: 'wm-btn wm-btn-secondary wm-btn-block wm-form-helper-link',
          href: formUrl,
          text: c.L('formHelperCta')
        }));
      }
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
      var pending = false; // in-flight guard: one /api/ask request at a time
      var send = c.h('button', { class: 'wm-btn wm-btn-primary', type: 'button', onclick: function () {
        if (pending) return; // ignore clicks while a request is in flight
        var q = (ta.value || '').trim();
        if (!q) return;
        var context = buildAiFollowupContext(c.state, packet);
        out.textContent = '…';
        if (typeof c.onAskFollowup === 'function') {
          pending = true;
          send.disabled = true;
          send.setAttribute('aria-busy', 'true');
          // Re-enable on BOTH success and failure so the button never sticks.
          var done = function () { pending = false; send.disabled = false; send.removeAttribute('aria-busy'); };
          Promise.resolve(c.onAskFollowup(context, q)).then(function (res) {
            done();
            c.clear(out);
            self.renderFollowupResult(c, out, res);
          }).catch(function () {
            done();
            c.clear(out);
            self.renderFollowupResult(c, out, { ok: false });
          });
        }
      } }, [c.L('aiSend')]);
      panel.appendChild(note);
      panel.appendChild(ta);
      panel.appendChild(send);
      panel.appendChild(out);
      return c.h('div', { class: 'wm-ai-wrap' }, [toggle, panel]);
    },

    // Renders the onAskFollowup() result. Expects { ok, answer, safetyBlocked,
    // safetyAlternatives, message } (see ai.html's onAskFollowup). Tolerates a
    // bare string for any other host implementation. Never renders nothing on
    // failure — a silent blank was the original bug (no error, no retry hint).
    renderFollowupResult: function (c, out, res) {
      if (typeof res === 'string') res = { ok: !!res, answer: res };
      res = res || {};
      if (res.safetyBlocked) {
        var card = c.h('div', { class: 'wm-card wm-card-warn', role: 'note' }, [
          c.h('p', { class: 'wm-warn-title', text: c.L('aiSafetyKicker') }),
          c.h('p', { class: 'wm-warn-body', text: res.answer || c.L('aiFollowupFailed') })
        ]);
        if (res.safetyAlternatives && res.safetyAlternatives.length) {
          card.appendChild(c.h('div', { class: 'wm-warn-channels' }, [
            c.h('p', { class: 'wm-warn-title', text: c.L('aiSafetyAltTitle') }),
            c.h('ul', { class: 'wm-verify-list' }, res.safetyAlternatives.map(function (a) {
              return c.h('li', { text: String(a) });
            }))
          ]));
        }
        out.appendChild(card);
        return;
      }
      if (res.message) { out.appendChild(c.h('p', { class: 'wm-ai-note', text: res.message })); return; }
      if (res.ok && res.answer) { out.appendChild(c.h('p', { text: res.answer })); return; }
      out.appendChild(c.h('p', { class: 'wm-ai-note', text: c.L('aiFollowupFailed') }));
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
