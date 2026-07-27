/* ============================================================================
 * Visable by Paradiso — Unified Search layer
 * ----------------------------------------------------------------------------
 * One hero input absorbs everything: a code (D-2-1, E74), a keyword (결혼이민),
 * a situation (졸업 후 취업), a question (회사 옮기려면 뭘 해야 하나요), a statute
 * reference (출입국관리법 제20조), or a job description (카페에서 음료를 만들어요).
 *
 * This module renders the interpretation strip, the AI Overview slot and the
 * source panel ABOVE the existing organic result list. It deliberately does NOT
 * take over search: index.html still owns #rlist rendering and still dispatches
 * `paradiso:results-rendered`. This module reacts to that event, so:
 *
 *   - organic results paint first, always, with zero network dependency;
 *   - the AI Overview is a separate, later, cancellable request;
 *   - an AI outage removes the overview card and changes nothing else.
 *
 * Safety contract:
 *  - Every backend/user string is HTML-escaped before touching the DOM. No
 *    remote content is ever assigned as raw innerHTML.
 *  - Official links are allow-listed to known government hosts and opened with
 *    rel="noopener noreferrer".
 *  - The backend never returns LAW_API_OC / API keys; this module never stores
 *    or forwards credentials.
 *  - A visa code is rendered only when the backend recognized it against
 *    visa_data.json. Unrecognized code-shaped tokens are shown as "not found",
 *    never as if they were real statuses.
 *
 * Pure builders are exposed on globalThis.ParadisoUnifiedSearch BEFORE the DOM
 * guard so they unit-test in plain Node, matching the other standalone modules.
 * ========================================================================== */
(function () {
  'use strict';

  var DEFAULT_API_BASE = 'https://web-production-14f9a.up.railway.app';
  var MAX_QUERY = 300;
  var AI_OVERVIEW_TIMEOUT_MS = 20000;

  /* --------------------------------------------------------------- i18n --- */
  function usLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    return l === 'en' ? 'en' : 'ko';
  }

  var STR = {
    ko: {
      interpretedAs: '이렇게 이해했어요',
      edit: '수정',
      intentExactCode: '체류자격 코드',
      intentVisaKeyword: '체류자격 주제',
      intentVisaSituation: '상황 설명',
      intentProcedure: '절차 질문',
      intentLegal: '법령·판례 질문',
      intentEmployment: '취업정보 신고',
      intentFeature: '기능 찾기',
      intentUnknown: '해석하지 못함',
      aiOverviewTitle: 'AI 요약',
      aiOverviewLoading: 'AI 요약을 만드는 중입니다. 아래 결과는 이미 확인할 수 있어요.',
      aiOverviewStreaming: '작성 중이에요',
      aiOverviewUnavailable: 'AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요.',
      aiOverviewNoEvidence: '근거를 찾지 못해 요약을 만들지 않았습니다.',
      aiRefLabel: '참고용 요약',
      nextSteps: '다음에 할 일',
      retry: '다시 시도',
      reasonLabel: '사유 ·',
      officialConfirmTitle: '공식 확인이 필요해요',
      officialConfirmHelp: '이 내용은 개별 심사에 따라 달라질 수 있습니다. 신청 전에 관할 관서에서 확인하세요.',
      partialSourcesHelp: '일부 출처를 확인하지 못했습니다. 회색 표시된 출처는 이번 검색에서 조회되지 않았어요.',
      moreInWaymaker: 'Waymaker에서 더 자세히',
      analyzeLegal: '법령·판례 기준으로 분석',
      sourcesTitle: '공식 출처',
      unknownCodeTitle: '확인되지 않은 코드',
      unknownCodeBody: '입력하신 %s 은(는) 저희 데이터에 없는 코드입니다. 오타가 아닌지 확인해 주세요.',
      reviewPending: '검토 전',
      reviewPendingHelp: '사람이 원문과 대조·승인하기 전 상태입니다. 확정 내용은 공식 출처에서 확인하세요.',
      officialKorean: '공식 원문 (한국어)',
      confirmOfficial: '최종 확인은 하이코리아 또는 1345에서 하세요.',
      suggestionsLabel: '이어서 찾아보기',
      citationUnverified: '인용 확인 실패',
      citationUnverifiedHelp: '요약에 인용된 법령 조문을 확인하지 못했습니다. 공식 원문을 확인하세요.',
      parentCodeBadge: '상위 자격',
      subCodeBadge: '세부코드'
    },
    en: {
      interpretedAs: 'How we read this',
      edit: 'Edit',
      intentExactCode: 'Status code',
      intentVisaKeyword: 'Status topic',
      intentVisaSituation: 'Situation',
      intentProcedure: 'Procedure question',
      intentLegal: 'Law / precedent question',
      intentEmployment: 'Employment reporting',
      intentFeature: 'Find a tool',
      intentUnknown: 'Could not interpret',
      aiOverviewTitle: 'AI overview',
      aiOverviewLoading: 'Generating an AI overview. The results below are already available.',
      aiOverviewStreaming: 'Writing…',
      aiOverviewUnavailable: 'The AI overview is unavailable. Please use the results and official sources below.',
      aiOverviewNoEvidence: 'No grounded evidence was found, so no overview was generated.',
      aiRefLabel: 'Reference summary',
      nextSteps: 'What to do next',
      retry: 'Try again',
      reasonLabel: 'Reason ·',
      officialConfirmTitle: 'Official confirmation needed',
      officialConfirmHelp: 'This can differ case by case. Confirm with the competent office before applying.',
      partialSourcesHelp: 'Some sources could not be checked. Dimmed sources were not retrieved in this search.',
      moreInWaymaker: 'Ask Waymaker for detail',
      analyzeLegal: 'Analyze against law and precedent',
      sourcesTitle: 'Official sources',
      unknownCodeTitle: 'Unrecognized code',
      unknownCodeBody: '%s is not a code in our dataset. Please check for a typo.',
      reviewPending: 'Not yet reviewed',
      reviewPendingHelp: 'This manual text has not been checked against the original by a human. Confirm with an official source.',
      officialKorean: 'Official text (Korean)',
      confirmOfficial: 'Confirm with HiKorea or 1345.',
      suggestionsLabel: 'Try next',
      citationUnverified: 'Citation not verified',
      citationUnverifiedHelp: 'A statute reference in this summary could not be verified. Check the official text.',
      parentCodeBadge: 'Parent status',
      subCodeBadge: 'Sub-code'
    }
  };

  function t(key) {
    var pack = STR[usLang()] || STR.ko;
    return pack[key] || STR.ko[key] || key;
  }

  /* ------------------------------------------------------------ helpers --- */
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  // Only official government hosts may become anchors. Anything else renders as
  // plain text, so a compromised or unexpected upstream URL cannot become a link.
  var OFFICIAL_HOSTS = [
    'law.go.kr', 'www.law.go.kr',
    'hikorea.go.kr', 'www.hikorea.go.kr',
    'immigration.go.kr', 'www.immigration.go.kr',
    'moj.go.kr', 'www.moj.go.kr',
    'kostat.go.kr', 'kssc.kostat.go.kr'
  ];

  function safeOfficialUrl(url) {
    var u = String(url == null ? '' : url).trim();
    if (!u || /[\u0000-\u001F\u007F]/.test(u) || /^\/\//.test(u)) return '';
    if (!/^https:\/\//i.test(u)) return '';
    var parsed;
    try { parsed = new URL(u); } catch (_) { return ''; }
    if (OFFICIAL_HOSTS.indexOf(parsed.hostname.toLowerCase()) === -1) return '';
    return parsed.href;
  }

  function intentLabel(intent) {
    switch (intent) {
      case 'exact_visa_code': return t('intentExactCode');
      case 'visa_keyword': return t('intentVisaKeyword');
      case 'visa_situation': return t('intentVisaSituation');
      case 'procedure_question': return t('intentProcedure');
      case 'legal_question': return t('intentLegal');
      case 'employment_reporting': return t('intentEmployment');
      case 'feature_navigation': return t('intentFeature');
      default: return t('intentUnknown');
    }
  }

  /* ------------------------------------------------- pure HTML builders --- */

  /** Interpretation strip: detected chips + unrecognized-code warning. */
  function buildInterpretationHtml(payload) {
    if (!payload || !payload.query) return '';
    var interpretation = payload.interpretation || {};
    var codes = payload.detectedVisaCodes || [];
    var unknown = interpretation.unrecognizedCodeLikeTokens || [];

    var chips = codes.map(function (code) {
      return '<button type="button" class="us-chip us-chip--code" data-us-code="' +
        escapeHtml(code) + '">' + escapeHtml(code) + '</button>';
    }).join('');

    var html = '<div class="us-interpret" role="status" aria-live="polite">' +
      '<div class="us-interpret-head">' +
      '<span class="us-interpret-label">' + escapeHtml(t('interpretedAs')) + '</span>' +
      '<span class="us-chip us-chip--intent">' + escapeHtml(intentLabel(payload.intent)) + '</span>' +
      chips +
      '<button type="button" class="us-interpret-edit" data-us-action="edit-query">' +
      escapeHtml(t('edit')) + '</button>' +
      '</div>';

    if (unknown.length) {
      html += '<div class="us-warn" role="note">' +
        '<strong>' + escapeHtml(t('unknownCodeTitle')) + '</strong> ' +
        escapeHtml(t('unknownCodeBody').replace('%s', unknown.join(', '))) +
        '</div>';
    }
    html += '</div>';
    return html;
  }

  /**
   * Resolve the render state of the AI Overview from the backend payload.
   *
   * The backend reports a coarse `status`; the Figma design distinguishes finer
   * presentation states on top of it (UX-03 `AI Overview`, node 406:92). The
   * refinement is deliberately one-way — it never upgrades a failure into a
   * success, only splits a success into the specific caution it warrants.
   *
   * Precedence matters: an unverified citation outranks a partial source set,
   * because an unconfirmable legal reference is a stronger caution than a
   * source list with a gap in it.
   */
  function resolveAiOverviewState(state, data) {
    if (state !== 'ok') return state;
    var d = data || {};
    var verification = d.citationVerification || {};
    if (verification.failureCount > 0 || verification.unverifiableCount > 0) {
      return 'citation_failed';
    }
    var evidence = d.evidenceState || {};
    var degraded = ['unavailable', 'forbidden', 'timeout', 'parse_failed', 'index_unavailable'];
    if (degraded.indexOf(evidence.law) !== -1 || degraded.indexOf(evidence.manual) !== -1 ||
        evidence.manual === 'review_pending_only') {
      return 'partial_sources';
    }
    if (d.requiresOfficialConfirmation) return 'official_confirm_required';
    return 'ready';
  }

  function aiSourceChipsHtml(sources) {
    if (!sources || !sources.length) return '';
    var chips = sources.slice(0, 8).map(function (src) {
      var label = typeof src === 'string' ? src : (src && src.label) || '';
      if (!label) return '';
      // A source the backend could not confirm is rendered dimmed rather than
      // dropped — a missing chip would silently shrink the apparent evidence set.
      var muted = typeof src === 'object' && src && src.unavailable ? ' is-muted' : '';
      return '<span class="us-ai-src' + muted + '">' +
        '<span class="us-ai-src-dot" aria-hidden="true"></span>' +
        escapeHtml(label) + '</span>';
    }).join('');
    return chips ? '<div class="us-ai-srcs">' + chips + '</div>' : '';
  }

  function aiNextStepsHtml(steps) {
    if (!steps || !steps.length) return '';
    var rows = steps.slice(0, 5).map(function (step, i) {
      var label = typeof step === 'string' ? step : (step && step.label) || '';
      if (!label) return '';
      return '<li class="us-ai-step">' +
        '<span class="us-ai-step-num" aria-hidden="true">' + (i + 1) + '</span>' +
        '<span class="us-ai-step-label">' + escapeHtml(label) + '</span></li>';
    }).join('');
    if (!rows) return '';
    return '<div class="us-ai-steps">' +
      '<p class="us-ai-sublabel">' + escapeHtml(t('nextSteps')) + '</p>' +
      '<ol class="us-ai-step-list">' + rows + '</ol></div>';
  }

  function aiBannerHtml(kind, title, bodyText) {
    return '<div class="us-ai-banner us-ai-banner--' + kind + '" role="note">' +
      '<strong class="us-ai-banner-title">' + escapeHtml(title) + '</strong> ' +
      '<span class="us-ai-banner-body">' + escapeHtml(bodyText) + '</span></div>';
  }

  /**
   * AI Overview card — the 8 states specified in Figma UX-03 (node 406:92):
   *   loading · streaming · ready · partial_sources · official_confirm_required
   *   · citation_failed · unavailable · blocked   (plus `hidden` = render nothing)
   *
   * Legacy state names from the first implementation still work so existing
   * callers and tests keep passing: `ok` is refined via resolveAiOverviewState,
   * and `no_evidence` maps onto `blocked` ("요약 미제공 + 사유").
   *
   * A failure is never silently dropped: every non-hidden state renders a card,
   * because a user who watched a spinner is owed the news that it stopped.
   */
  function buildAiOverviewHtml(state, data) {
    if (state === 'hidden') return '';
    if (state === 'no_evidence') state = 'blocked';
    var resolved = resolveAiOverviewState(state, data);
    var d = data || {};
    var text = String(d.overview || '').trim();
    var parts = [];
    var cls;

    if (resolved === 'loading') {
      cls = 'is-loading';
      parts.push('<p class="us-ai-body">' + escapeHtml(t('aiOverviewLoading')) + '</p>');
      parts.push('<div class="us-ai-skeleton" aria-hidden="true"><span></span><span></span><span></span></div>');
    } else if (resolved === 'streaming') {
      cls = 'is-streaming';
      parts.push('<p class="us-ai-body">' + escapeHtml(text).replace(/\n+/g, '<br>') +
        '<span class="us-ai-caret" aria-hidden="true"></span></p>');
      parts.push('<p class="us-ai-sublabel">' + escapeHtml(t('aiOverviewStreaming')) + '</p>');
    } else if (resolved === 'unavailable') {
      cls = 'is-unavailable';
      parts.push('<p class="us-ai-body">' +
        escapeHtml(d.message || t('aiOverviewUnavailable')) + '</p>');
      parts.push('<div class="us-ai-actions">' +
        '<button type="button" class="us-ai-action" data-us-action="retry-overview">' +
        escapeHtml(t('retry')) + '</button></div>');
    } else if (resolved === 'blocked') {
      cls = 'is-blocked';
      parts.push('<p class="us-ai-body">' +
        escapeHtml(d.message || t('aiOverviewNoEvidence')) + '</p>');
      if (d.reason) {
        parts.push('<p class="us-ai-sublabel">' + escapeHtml(t('reasonLabel')) + ' ' +
          escapeHtml(d.reason) + '</p>');
      }
    } else {
      // ready / partial_sources / official_confirm_required / citation_failed
      cls = 'is-' + resolved.replace(/_/g, '-');
      if (resolved === 'citation_failed') {
        parts.push(aiBannerHtml('citation', t('citationUnverified'), t('citationUnverifiedHelp')));
      } else if (resolved === 'official_confirm_required') {
        parts.push(aiBannerHtml('confirm', t('officialConfirmTitle'), t('officialConfirmHelp')));
      }
      parts.push('<p class="us-ai-body">' + escapeHtml(text).replace(/\n+/g, '<br>') + '</p>');
      parts.push(aiNextStepsHtml(d.nextSteps));
      parts.push('<div class="us-ai-divider" aria-hidden="true"></div>');
      parts.push('<div class="us-ai-sources"><p class="us-ai-sublabel">' +
        escapeHtml(t('sourcesTitle')) + '</p>' + aiSourceChipsHtml(d.sources) + '</div>');
      if (resolved === 'partial_sources') {
        parts.push('<p class="us-ai-sublabel us-ai-sublabel--warn">' +
          escapeHtml(t('partialSourcesHelp')) + '</p>');
      }
      if (d.evidenceLabel) {
        parts.push('<p class="us-ai-sublabel">' + escapeHtml(d.evidenceLabel) + '</p>');
      }
      parts.push('<div class="us-ai-actions">' +
        '<button type="button" class="us-ai-action us-ai-action--cta" data-us-action="open-waymaker">' +
        escapeHtml(t('moreInWaymaker')) + '</button>' +
        '<button type="button" class="us-ai-action" data-us-action="open-legal">' +
        escapeHtml(t('analyzeLegal')) + '</button></div>');
    }

    parts.push('<p class="us-ai-confirm">' + escapeHtml(t('confirmOfficial')) + '</p>');

    return '<section class="us-ai ' + cls + '" aria-labelledby="usAiTitle" data-us-ai-state="' +
      escapeHtml(resolved) + '">' +
      '<div class="us-ai-head">' +
      '<h3 class="us-ai-title" id="usAiTitle">' + escapeHtml(t('aiOverviewTitle')) + '</h3>' +
      '<span class="us-badge us-badge--ref">' + escapeHtml(t('aiRefLabel')) + '</span>' +
      '</div>' + parts.join('') + '</section>';
  }

  /** Official source panel. Non-allow-listed URLs degrade to plain text. */
  function buildSourceCardsHtml(cards) {
    if (!cards || !cards.length) return '';
    var items = cards.map(function (card) {
      var url = safeOfficialUrl(card && card.url);
      var title = escapeHtml((card && card.title) || '');
      var note = escapeHtml((card && card.note) || '');
      var head = url
        ? '<a class="us-source-link" href="' + escapeHtml(url) +
          '" target="_blank" rel="noopener noreferrer">' + title + '</a>'
        : '<span class="us-source-link us-source-link--plain">' + title + '</span>';
      var badge = '';
      if (card && card.sourceType === 'manual_review_pending') {
        badge = '<span class="us-badge us-badge--review">' + escapeHtml(t('reviewPending')) + '</span>';
      } else if (card && card.sourceType === 'official_law') {
        badge = '<span class="us-badge us-badge--official">' + escapeHtml(t('officialKorean')) + '</span>';
      }
      return '<li class="us-source">' + head + badge +
        (note ? '<p class="us-source-note">' + note + '</p>' : '') + '</li>';
    }).join('');
    return '<section class="us-sources" aria-labelledby="usSourcesTitle">' +
      '<h3 class="us-sources-title" id="usSourcesTitle">' + escapeHtml(t('sourcesTitle')) + '</h3>' +
      '<ul class="us-source-list">' + items + '</ul></section>';
  }

  /** Follow-up suggestion chips. */
  function buildSuggestionsHtml(suggestions) {
    if (!suggestions || !suggestions.length) return '';
    var chips = suggestions.map(function (s) {
      return '<button type="button" class="us-chip us-chip--suggest" data-us-query="' +
        escapeHtml(s) + '">' + escapeHtml(s) + '</button>';
    }).join('');
    return '<section class="us-suggest" aria-label="' + escapeHtml(t('suggestionsLabel')) + '">' +
      '<span class="us-suggest-label">' + escapeHtml(t('suggestionsLabel')) + '</span>' +
      chips + '</section>';
  }

  /** Manual/tool cards the base result list does not render itself. */
  function buildExtraResultsHtml(results) {
    if (!results || !results.length) return '';
    var extras = results.filter(function (r) {
      return r && (r.kind === 'manual_card' || r.kind === 'employment_tool' ||
                   r.kind === 'legal_card' || r.kind === 'feature_card');
    });
    if (!extras.length) return '';

    var items = extras.map(function (card) {
      var badge = '';
      if (card.kind === 'manual_card' && !card.usableAsDirectEvidence) {
        badge = '<span class="us-badge us-badge--review" title="' +
          escapeHtml(t('reviewPendingHelp')) + '">' + escapeHtml(t('reviewPending')) + '</span>';
      }
      var action = '';
      if (card.toolId) {
        action = ' data-us-tool="' + escapeHtml(card.toolId) + '"';
      }
      var page = card.page ? '<span class="us-card-page">p.' + escapeHtml(String(card.page)) + '</span>' : '';
      return '<li class="us-card us-card--' + escapeHtml(card.kind) + '"' + action + '>' +
        '<div class="us-card-head"><span class="us-card-title">' +
        escapeHtml(card.title || '') + '</span>' + badge + page + '</div>' +
        (card.summary ? '<p class="us-card-summary">' + escapeHtml(card.summary) + '</p>' : '') +
        '</li>';
    }).join('');
    return '<section class="us-extra" aria-label="' + escapeHtml(t('sourcesTitle')) + '">' +
      '<ul class="us-card-list">' + items + '</ul></section>';
  }

  /** Compose the whole unified layer. Organic cards stay in #rlist, untouched. */
  function buildUnifiedLayerHtml(payload, aiState, aiData) {
    if (!payload || !payload.query) return '';
    return buildInterpretationHtml(payload) +
      buildAiOverviewHtml(aiState, aiData) +
      buildExtraResultsHtml(payload.organicResults) +
      buildSuggestionsHtml(payload.suggestions) +
      buildSourceCardsHtml(payload.sourceCards);
  }

  /** Classify a fetch outcome into an AI Overview render state. */
  function classifyAiResponse(body, httpOk) {
    if (!httpOk || !body) return 'unavailable';
    // A partial overview still arriving renders as `streaming`, so the reader
    // sees words appear instead of an opaque spinner.
    if (body.status === 'streaming') return body.overview ? 'streaming' : 'loading';
    if (body.status === 'ok' && body.overview) return 'ok';
    if (body.status === 'blocked') return 'blocked';
    if (body.status === 'no_evidence') return 'no_evidence';
    if (body.status === 'not_applicable') return 'hidden';
    return 'unavailable';
  }

  /** Shareable query string: `?q=...`. Reading and writing are symmetric. */
  function readQueryFromUrl(href) {
    try {
      var url = new URL(String(href || ''), 'https://example.invalid');
      return (url.searchParams.get('q') || '').slice(0, MAX_QUERY);
    } catch (_) { return ''; }
  }

  function buildShareableUrl(href, query) {
    try {
      var url = new URL(String(href || ''), 'https://example.invalid');
      if (query) url.searchParams.set('q', String(query).slice(0, MAX_QUERY));
      else url.searchParams.delete('q');
      return url.pathname + url.search + url.hash;
    } catch (_) { return ''; }
  }

  var api = {
    escapeHtml: escapeHtml,
    safeOfficialUrl: safeOfficialUrl,
    intentLabel: intentLabel,
    buildInterpretationHtml: buildInterpretationHtml,
    buildAiOverviewHtml: buildAiOverviewHtml,
    buildSourceCardsHtml: buildSourceCardsHtml,
    buildSuggestionsHtml: buildSuggestionsHtml,
    buildExtraResultsHtml: buildExtraResultsHtml,
    buildUnifiedLayerHtml: buildUnifiedLayerHtml,
    classifyAiResponse: classifyAiResponse,
    resolveAiOverviewState: resolveAiOverviewState,
    readQueryFromUrl: readQueryFromUrl,
    buildShareableUrl: buildShareableUrl,
    OFFICIAL_HOSTS: OFFICIAL_HOSTS,
    MAX_QUERY: MAX_QUERY
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoUnifiedSearch = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;

  /* ====================== everything below needs a DOM ==================== */
  if (typeof document === 'undefined') return;

  function apiBase() {
    try {
      if (typeof window !== 'undefined' && window.PARADISO_BACKEND_URL &&
          String(window.PARADISO_BACKEND_URL).trim()) {
        return String(window.PARADISO_BACKEND_URL).trim();
      }
    } catch (e) { /* ignore */ }
    try {
      var host = location.hostname;
      if (host === 'localhost' || host === '127.0.0.1' || location.protocol === 'file:') return '';
    } catch (e) { /* ignore */ }
    return DEFAULT_API_BASE;
  }

  var mountEl = null;
  var lastPayload = null;
  var aiController = null;
  var currentToken = 0;

  function ensureMount() {
    if (mountEl && mountEl.isConnected) return mountEl;
    var rlist = document.getElementById('rlist');
    if (!rlist || !rlist.parentNode) return null;
    mountEl = document.getElementById('unifiedSearchLayer');
    if (!mountEl) {
      mountEl = document.createElement('div');
      mountEl.id = 'unifiedSearchLayer';
      mountEl.className = 'us-layer';
      rlist.parentNode.insertBefore(mountEl, rlist);
    }
    return mountEl;
  }

  function render(aiState, aiData) {
    var host = ensureMount();
    if (!host) return;
    if (!lastPayload || !lastPayload.query) { host.innerHTML = ''; return; }
    host.innerHTML = buildUnifiedLayerHtml(lastPayload, aiState, aiData);
  }

  function fetchUnified(query) {
    var token = ++currentToken;
    var base = apiBase();
    return fetch(base + '/api/search/unified', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, lang: usLang() })
    }).then(function (res) {
      if (!res.ok) throw new Error('unified search failed');
      return res.json();
    }).then(function (body) {
      if (token !== currentToken) return null;   // a newer query superseded this
      lastPayload = body;
      render('loading', null);
      return body;
    }).catch(function () {
      if (token !== currentToken) return null;
      // The deterministic layer is an enhancement; #rlist already has results.
      lastPayload = null;
      render('hidden', null);
      return null;
    });
  }

  function aiRequestBody(query, payload) {
    return JSON.stringify({
      query: query,
      lang: usLang(),
      intent: payload.intent,
      detectedVisaCodes: payload.detectedVisaCodes || []
    });
  }

  /** Buffered overview — the fallback whenever streaming is not usable. */
  function fetchAiOverviewBuffered(query, payload, token, timer) {
    return fetch(apiBase() + '/api/search/unified/ai-overview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: aiRequestBody(query, payload),
      signal: aiController ? aiController.signal : undefined
    }).then(function (res) {
      return res.json().then(function (body) { return { ok: res.ok, body: body }; });
    }).then(function (result) {
      clearTimeout(timer);
      if (token !== currentToken) return;
      render(classifyAiResponse(result.body, result.ok), result.body);
    }).catch(function () {
      clearTimeout(timer);
      if (token !== currentToken) return;
      // Quiet failure card — the organic results below are untouched.
      render('unavailable', null);
    });
  }

  /**
   * Streamed overview. Renders `streaming` deltas as they arrive so the reader
   * sees words instead of a spinner, then swaps to the verified final payload on
   * `done` — the citation guard only runs on the complete text, so nothing is
   * presented as verified until then.
   *
   * Any failure before the first delta falls back to the buffered endpoint; a
   * failure mid-stream keeps whatever text arrived and marks it unavailable
   * rather than blanking the card.
   */
  function fetchAiOverviewStreamed(query, payload, token, timer) {
    if (typeof ReadableStream === 'undefined' || typeof TextDecoder === 'undefined') {
      return fetchAiOverviewBuffered(query, payload, token, timer);
    }
    return fetch(apiBase() + '/api/search/unified/ai-overview/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: aiRequestBody(query, payload),
      signal: aiController ? aiController.signal : undefined
    }).then(function (res) {
      if (!res.ok || !res.body) throw new Error('stream unavailable');
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var accumulated = '';
      var settled = false;

      function handleFrame(frame) {
        var lines = frame.split('\n');
        var event = '';
        var dataText = '';
        for (var i = 0; i < lines.length; i++) {
          if (lines[i].indexOf('event:') === 0) event = lines[i].slice(6).trim();
          else if (lines[i].indexOf('data:') === 0) dataText += lines[i].slice(5).trim();
        }
        if (!dataText) return;
        var data;
        try { data = JSON.parse(dataText); } catch (e) { return; }

        if (event === 'delta' && data.text) {
          accumulated += data.text;
          render('streaming', { overview: accumulated });
        } else if (event === 'done') {
          settled = true;
          clearTimeout(timer);
          if (token !== currentToken) return;
          if (data.status === 'unavailable' && data.reason === 'streaming_not_available') {
            fetchAiOverviewBuffered(query, payload, token, timer);
            return;
          }
          render(classifyAiResponse(data, true), data);
        }
      }

      function pump() {
        return reader.read().then(function (chunk) {
          if (chunk.done) {
            if (!settled && token === currentToken) {
              // Stream ended without a `done` frame: keep the partial text but
              // stop claiming it is finished.
              clearTimeout(timer);
              render('unavailable', accumulated ? { message: accumulated } : null);
            }
            return;
          }
          buffer += decoder.decode(chunk.value, { stream: true });
          var frames = buffer.split('\n\n');
          buffer = frames.pop();
          for (var i = 0; i < frames.length; i++) handleFrame(frames[i]);
          if (token !== currentToken) { try { reader.cancel(); } catch (e) { /* ignore */ } return; }
          return pump();
        });
      }
      return pump();
    }).catch(function () {
      if (token !== currentToken) return;
      // Nothing streamed — fall back rather than showing a failure the buffered
      // endpoint might not have.
      return fetchAiOverviewBuffered(query, payload, token, timer);
    });
  }

  function fetchAiOverview(query, payload) {
    if (!payload || !payload.query) return;
    var token = currentToken;
    if (aiController) { try { aiController.abort(); } catch (e) { /* ignore */ } }
    aiController = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (aiController) { try { aiController.abort(); } catch (e) { /* ignore */ } }
    }, AI_OVERVIEW_TIMEOUT_MS);
    fetchAiOverviewStreamed(query, payload, token, timer);
  }

  function runUnified(query) {
    var q = String(query || '').trim().slice(0, MAX_QUERY);
    if (!q) { lastPayload = null; render('hidden', null); return; }
    fetchUnified(q).then(function (payload) {
      if (payload) fetchAiOverview(q, payload);
    });
  }

  /* --------------------------------------------------------- URL state --- */
  function syncUrl(query) {
    try {
      var next = buildShareableUrl(window.location.href, query);
      if (next && next !== (window.location.pathname + window.location.search + window.location.hash)) {
        window.history.pushState({ paradisoQuery: query }, '', next);
      }
    } catch (e) { /* history is best-effort */ }
  }

  window.addEventListener('popstate', function () {
    var q = readQueryFromUrl(window.location.href);
    var input = document.getElementById('q');
    if (input && input.value !== q) {
      input.value = q;
      try { input.dispatchEvent(new Event('input', { bubbles: true })); } catch (e) { /* ignore */ }
    }
    if (q) runUnified(q); else { lastPayload = null; render('hidden', null); }
  });

  /* ------------------------------------------------- integration seams --- */
  // index.html owns organic rendering and announces it. We react — never block.
  document.addEventListener('paradiso:results-rendered', function (event) {
    var query = (event && event.detail && event.detail.query) || '';
    if (!query) { lastPayload = null; render('hidden', null); return; }
    syncUrl(query);
    runUnified(query);
  });

  // Delegated actions inside the unified layer.
  document.addEventListener('click', function (event) {
    var host = document.getElementById('unifiedSearchLayer');
    if (!host || !host.contains(event.target)) return;

    var chip = event.target.closest('[data-us-query]');
    if (chip) {
      var input = document.getElementById('q');
      if (input) {
        input.value = chip.getAttribute('data-us-query') || '';
        var form = document.getElementById('searchForm');
        if (form) {
          try { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }
          catch (e) { /* ignore */ }
        }
      }
      return;
    }

    var codeChip = event.target.closest('[data-us-code]');
    if (codeChip) {
      var codeInput = document.getElementById('q');
      if (codeInput) {
        codeInput.value = codeChip.getAttribute('data-us-code') || '';
        var codeForm = document.getElementById('searchForm');
        if (codeForm) {
          try { codeForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }
          catch (e) { /* ignore */ }
        }
      }
      return;
    }

    var action = event.target.closest('[data-us-action]');
    if (action) {
      var name = action.getAttribute('data-us-action');
      if (name === 'edit-query') {
        var editInput = document.getElementById('q');
        if (editInput) { editInput.focus(); try { editInput.select(); } catch (e) { /* ignore */ } }
      } else if (name === 'open-waymaker') {
        var q = (lastPayload && lastPayload.query) || '';
        window.location.href = 'ai.html' + (q ? ('?q=' + encodeURIComponent(q)) : '');
      } else if (name === 'open-legal') {
        try {
          window.dispatchEvent(new CustomEvent('paradiso:legal-search', {
            detail: { query: (lastPayload && lastPayload.query) || '', kind: 'laws' }
          }));
        } catch (e) { /* ignore */ }
      } else if (name === 'retry-overview') {
        // Retry only the overview. The organic results below are already correct
        // and must not be refetched or cleared.
        if (lastPayload && lastPayload.query) {
          render('loading', null);
          fetchAiOverview(lastPayload.query, lastPayload);
        }
      }
      return;
    }

    var tool = event.target.closest('[data-us-tool]');
    if (tool) {
      var toolId = tool.getAttribute('data-us-tool');
      if (toolId === 'employment-reporting') {
        var opener = document.querySelector('[data-action="open-jobcode-modal"]');
        if (opener) opener.click();
      } else if (toolId === 'legal-research') {
        try {
          window.dispatchEvent(new CustomEvent('paradiso:legal-search', {
            detail: { query: (lastPayload && lastPayload.query) || '', kind: 'laws' }
          }));
        } catch (e) { /* ignore */ }
      }
    }
  });

  window.addEventListener('paradiso-language-applied', function () {
    try { if (lastPayload) render('hidden', null); } catch (e) { /* non-fatal */ }
  });

  // Deep link: ?q=... runs a search on load once the base app is ready.
  function bootFromUrl() {
    var q = readQueryFromUrl(window.location.href);
    if (!q) return;
    var input = document.getElementById('q');
    if (!input || input.disabled) { setTimeout(bootFromUrl, 300); return; }
    if (input.value === q) return;
    input.value = q;
    var form = document.getElementById('searchForm');
    if (form) {
      try { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }
      catch (e) { /* ignore */ }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootFromUrl);
  } else {
    bootFromUrl();
  }
})();
