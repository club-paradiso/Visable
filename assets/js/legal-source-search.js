/* ============================================================================
 * Waymaker by Paradiso — Waymaker 리걸 리서치 / Waymaker Legal Research
 * ----------------------------------------------------------------------------
 * A source-CHECKING layer inside Waymaker. Lets users look up immigration-
 * related statutes (법령) and court precedents (판례) from the official Open Law
 * API (law.go.kr) via the backend proxy, so they can verify the official text
 * themselves. It is NOT legal advice and never claims eligibility.
 *
 * Safety contract:
 *  - All upstream/user text is HTML-escaped before it touches the DOM. Upstream
 *    precedent/law fields are NEVER injected as raw HTML (no innerHTML of remote
 *    content; only of strings this module built from escaped parts).
 *  - Official-source links are validated to be http(s) law.go.kr URLs only,
 *    opened with rel="noopener noreferrer".
 *  - The backend never returns the LAW_API_OC credential; this module never
 *    sees or stores it. A missing credential renders a friendly config state.
 *  - Precedent body/detail is intentionally not rendered; each precedent card
 *    points to the official text with "원문 확인 필요 / Check official text".
 *
 * The pure builders (escapeHtml, safeSourceUrl, buildLawCardHtml,
 * buildPrecedentCardHtml, buildResultsHtml, classifyResponse) are exposed on
 * globalThis.ParadisoLegalSearch BEFORE the DOM wiring guard, so they unit-test
 * in plain Node (no jsdom) exactly like the other Paradiso standalone modules.
 * ========================================================================== */
(function () {
  'use strict';

  var DEFAULT_API_BASE = 'https://web-production-14f9a.up.railway.app';
  var MAX_QUERY = 150;

  /* ----------------------------------------------------------- language --- */
  function lssLang() {
    var l = (typeof currentLanguage !== 'undefined' && currentLanguage) ? currentLanguage : 'ko';
    // zh-CN gracefully falls back to ko (repo policy for standalone modules:
    // no low-quality machine Chinese in these flows).
    return l === 'en' ? 'en' : 'ko';
  }

  /* ------------------------------------------------ strings (KO + EN) ------ */
  var STR_KO = {
    title: 'Waymaker 리걸 리서치',
    subtitle: '공식 법령·판례·출입국 자료를 바탕으로 쟁점을 정리합니다.',
    refChip: '참고용',
    toggleOpen: 'Waymaker 리걸 리서치 열기',
    toggleClose: '접기',
    disclaimer: 'Waymaker 리걸 리서치는 검색된 공식 법령·판례·출입국 자료를 바탕으로 쟁점을 정리하는 참고용 도구입니다. 변호사·행정사의 법률 자문을 대체하지 않으며, 실제 허가 여부와 최종 판단은 관계 기관의 심사에 따릅니다.',
    tabLaws: '법령',
    tabPrec: '판례',
    inputPlaceholder: '검색어 입력',
    inputAria: '법령·판례 검색어',
    searchBtn: '검색',
    chipsLabel: '빠른 검색',
    viewSource: '공식 원문 보기',
    checkOfficial: '원문 확인 필요',
    promulgated: '공포',
    effective: '시행',
    untitled: '(제목 없음)',
    idleTitle: '확인하고 싶은 법령이나 판례를 검색해 보세요',
    idleBody: '예: 출입국관리법, 체류자격 변경, 강제퇴거. 아래 빠른 검색을 눌러도 됩니다.',
    loadingLaws: '법령 검색 중입니다',
    loadingPrec: '판례 검색 중입니다',
    emptyTitle: '검색 결과가 없습니다',
    emptyBody: '검색어를 바꾸거나, 공식 자료에서 직접 확인해 보세요.',
    errorTitle: '검색에 실패했습니다',
    errorBody: '잠시 후 다시 시도하거나, 하이코리아·1345 또는 공식 자료에서 확인하세요.',
    missingKeyTitle: 'API 설정이 필요합니다',
    missingKeyBody: '법령 검색 서비스가 아직 설정되지 않았습니다. 공식 자료(law.go.kr·하이코리아·1345)에서 직접 확인하세요.',
    precNote: '판례는 개별 사건 판단이며 결과를 보장하지 않습니다. 자세한 내용은 공식 원문을 확인하세요.',
    tabResearch: '리걸 리서치',
    researchDepthLabel: '리서치 깊이',
    depthFast: '빠른 확인',
    depthBasic: '기본 리서치',
    depthPro: '심층 리서치',
    depthFastDesc: '빠른 확인: 핵심 경로와 근거 후보를 짧게 확인합니다.',
    depthBasicDesc: '기본 리서치: 공식자료 기반으로 쟁점과 다음 확인사항을 정리합니다.',
    depthProDesc: '심층 리서치: 법령·판례·실무자료를 함께 검토해 리서치 메모 형태로 정리합니다.',
    researchPlaceholder: '상황이나 질문을 적어주세요 (예: 강제퇴거명령과 출국명령의 차이와 다툴 쟁점)',
    researchInputAria: '리서치 질문',
    researchRun: '분석 시작하기',
    researchIdleTitle: '상황을 적으면 쟁점과 확인할 근거를 정리해 드립니다',
    researchIdleBody: '깊이를 고르고 질문을 입력하세요. 질문에 따라 깊이를 자동으로 제안합니다.',
    researchLoading: '리서치 준비 중입니다',
    autoSuggested: '질문에 맞춰 자동 선택됨',
    secIssues: '쟁점',
    secLawTerms: '법령 검색어',
    secPrecTerms: '판례 검색어',
    secLaws: '관련 법령·자료',
    secPrecedents: '관련 판례',
    secApply: '적용 가능성',
    secRisks: '위험 신호',
    secMissing: '부족한 사실관계',
    secNext: '다음 확인사항',
    secSources: '출처',
    secLimits: '한계',
    applyNote: '아래 근거를 본인 사실관계에 직접 대입해 확인하세요. 이 정리는 결론이 아닙니다.',
    proSteps: ['쟁점 추출 중', '법령 검색 중', '판례 검색 중', '공식자료 대조 중', '리서치 메모 작성 중'],
    synthToggle: 'AI 리서치 요약 사용',
    badgeStandard: '기본 리서치 결과',
    badgeAI: 'AI 리서치 요약',
    badgeFailed: 'AI 요약 검증 실패: 기본 결과 표시',
    synthMemoTitle: '리서치 메모',
    synthSummary: '요약',
    synthRules: '확인된 법령·자료',
    synthAnalysis: '사실관계에 비추어 볼 때의 검토 포인트',
    synthNextQ: '다음 질문',
    synthNextDocs: '다음 서류',
    synthBasis: '근거',
    // positioning + professional UX
    positioning: '공식 법령·판례·출입국 자료를 바탕으로 쟁점을 정리하는 리서치 도구입니다. 법률 자문이나 합격·승소 예측이 아닙니다.',
    examplesLabel: '예시 질문',
    optPrecedents: '판례도 함께 검색',
    optShowOriginal: '공식 원문 함께 보기',
    // source-language delivery
    srcKoBadge: '한국어 원문',
    srcShowOriginal: '원문 보기',
    srcHideOriginal: '원문 접기',
    officialKoNotice: '',
    translatedSummaryNotice: '',
    // richer answer sections
    secIssueMap: '주요 쟁점',
    secApplyPoints: '적용 포인트',
    secDocsToCheck: '확인할 서류',
    whyItMattersLabel: '왜 중요한가',
    basicSteps: ['쟁점 정리 중', '법령·자료 검색 중', '확인사항 정리 중'],
    handoffToResearch: '법령·판례 기준으로 더 분석하기'
  };
  var STR_EN = {
    title: 'Waymaker Legal Research',
    subtitle: 'A research tool that organizes immigration issues based on official statutes, precedents, and immigration materials.',
    refChip: 'Reference',
    toggleOpen: 'Open Waymaker Legal Research',
    toggleClose: 'Collapse',
    disclaimer: 'Waymaker Legal Research is a reference tool that organizes issues based on retrieved official statutes, precedents, and immigration materials. It does not replace advice from a qualified professional, and final decisions are made by the competent authorities.',
    tabLaws: 'Laws',
    tabPrec: 'Precedents',
    inputPlaceholder: 'Enter a search term',
    inputAria: 'Legal source search term',
    searchBtn: 'Search',
    chipsLabel: 'Quick search',
    viewSource: 'View official source',
    checkOfficial: 'Check official text',
    promulgated: 'Promulgated',
    effective: 'Effective',
    untitled: '(untitled)',
    idleTitle: 'Search for a statute or precedent you want to check',
    idleBody: 'e.g. Immigration Act, status change, deportation. You can also tap a quick search below.',
    loadingLaws: 'Searching legal sources',
    loadingPrec: 'Searching precedents',
    emptyTitle: 'No results found',
    emptyBody: 'Try a different term, or check the official source directly.',
    errorTitle: 'Search failed',
    errorBody: 'Please try again shortly, or check with HiKorea / 1345 or the official source.',
    missingKeyTitle: 'API configuration required',
    missingKeyBody: 'The legal search service is not configured yet. Please check official sources (law.go.kr / HiKorea / 1345) directly.',
    precNote: 'Precedents are individual case decisions and do not guarantee any outcome. See the official text for details.',
    tabResearch: 'Legal Research',
    researchDepthLabel: 'Research depth',
    depthFast: 'Quick check',
    depthBasic: 'Standard research',
    depthPro: 'Deep research',
    depthFastDesc: 'Quick check: Quickly identifies key routes and source candidates.',
    depthBasicDesc: 'Standard research: Organizes issues and next checks based on official materials.',
    depthProDesc: 'Deep research: Reviews laws, precedents, and practice materials in a research memo format.',
    researchPlaceholder: 'Describe your situation or question (e.g. difference between a deportation order and a departure order and how to challenge each)',
    researchInputAria: 'Research question',
    researchRun: 'Start analysis',
    researchIdleTitle: 'Describe your situation and we will organize the issues and sources to check',
    researchIdleBody: 'Choose a depth and enter your question. Depth is auto-suggested based on the question.',
    researchLoading: 'Preparing research',
    autoSuggested: 'Auto-selected for this question',
    secIssues: 'Issues',
    secLawTerms: 'Law search terms',
    secPrecTerms: 'Precedent search terms',
    secLaws: 'Relevant laws & materials',
    secPrecedents: 'Relevant precedents',
    secApply: 'Possible application',
    secRisks: 'Risk flags',
    secMissing: 'Missing facts',
    secNext: 'Next checks',
    secSources: 'Sources',
    secLimits: 'Limitations',
    applyNote: 'Apply the sources below to your own facts and verify. This is not a conclusion.',
    proSteps: ['Spotting issues', 'Searching laws', 'Searching precedents', 'Cross-checking official materials', 'Drafting research memo'],
    synthToggle: 'Use AI research synthesis',
    badgeStandard: 'Standard research result',
    badgeAI: 'AI research synthesis',
    badgeFailed: 'AI synthesis validation failed: showing standard result',
    synthMemoTitle: 'Research memo',
    synthSummary: 'Summary',
    synthRules: 'Confirmed statutes and materials',
    synthAnalysis: 'Application points based on the facts provided',
    synthNextQ: 'Next questions',
    synthNextDocs: 'Next documents',
    synthBasis: 'basis',
    // positioning + professional UX
    positioning: 'A research tool that organizes immigration issues based on official statutes, precedents, and immigration materials. It is not legal advice or a prediction of approval or lawsuit outcomes.',
    examplesLabel: 'Example questions',
    optPrecedents: 'Search precedents too',
    optShowOriginal: 'Show official source text',
    // source-language delivery
    srcKoBadge: 'Korean source',
    srcShowOriginal: 'Show original Korean',
    srcHideOriginal: 'Hide original',
    officialKoNotice: 'Official source text may be in Korean.',
    translatedSummaryNotice: 'This summary is generated by Waymaker and is unofficial. Official source text may be in Korean — see the sources below.',
    // richer answer sections
    secIssueMap: 'Key issues',
    secApplyPoints: 'Application points',
    secDocsToCheck: 'Documents to check',
    whyItMattersLabel: 'Why it matters',
    basicSteps: ['Organizing issues', 'Searching laws & materials', 'Compiling checks'],
    handoffToResearch: 'Analyze with legal sources'
  };
  var STR_PACKS = { ko: STR_KO, en: STR_EN };
  function S(k, lang) {
    var p = STR_PACKS[lang || lssLang()] || STR_KO;
    return (p[k] != null) ? p[k] : STR_KO[k];
  }

  /* ------------------------------------------------------- quick chips ---- */
  // label = Korean legal term shown in KO mode (and the search query sent to the
  // Korean law DB); labelEn = English gloss shown in EN mode; query = the term
  // actually searched (Korean — the law DB is Korean-only).
  var CHIPS = [
    { label: '출입국관리법', labelEn: 'Immigration Act', query: '출입국관리법' },
    { label: '체류자격 변경', labelEn: 'Status change', query: '체류자격 변경' },
    { label: '체류기간 연장', labelEn: 'Stay extension', query: '체류기간 연장' },
    { label: '재외동포 F-4', labelEn: 'Overseas Korean (F-4)', query: '재외동포' },
    { label: '결혼이민 F-6', labelEn: 'Marriage migrant (F-6)', query: '결혼이민' },
    { label: '유학생 D-2', labelEn: 'Student (D-2)', query: '유학' },
    { label: '난민 G-1', labelEn: 'Refugee (G-1)', query: '난민법' },
    { label: '강제퇴거', labelEn: 'Deportation', query: '강제퇴거' },
    { label: '사증발급', labelEn: 'Visa issuance', query: '사증' },
    { label: '귀화', labelEn: 'Naturalization', query: '귀화' }
  ];
  function chipLabel(c, lang) { return (lang || lssLang()) === 'en' ? c.labelEn : c.label; }

  /* ------------------------------------------------ research examples ------ */
  // Realistic, non-expert starting questions (foreign residents, students,
  // marriage migrants, refugee applicants). `depth` is only a UI suggestion; the
  // backend still auto-selects authoritatively.
  var RESEARCH_EXAMPLES = [
    { ko: 'F-6 결혼이민 체류자격 변경에서 소득요건과 혼인의 진정성은 어떻게 보나요?',
      en: 'For an F-6 marriage-migrant status change, how are the income requirement and genuineness of marriage assessed?', depth: 'basic' },
    { ko: '유학생인데 졸업 후 D-2에서 E-7으로 바꾸려면 무엇을 확인해야 하나요?',
      en: 'I am a student — what should I check to change from D-2 to E-7 after graduation?', depth: 'basic' },
    { ko: '강제퇴거명령과 출국명령의 차이와 다툴 수 있는 쟁점은 무엇인가요?',
      en: 'What is the difference between a deportation order and a departure order, and what issues can be challenged?', depth: 'pro' },
    { ko: '난민 불인정 결정에 대한 이의신청과 행정소송 절차는 어떻게 되나요?',
      en: 'What are the objection and administrative-litigation procedures against a refugee non-recognition decision?', depth: 'pro' },
    { ko: '귀화 신청에서 품행 단정 요건은 어떻게 판단되나요?',
      en: 'How is the "good conduct" requirement assessed in a naturalization application?', depth: 'pro' }
  ];
  function exampleText(e, lang) { return (lang || lssLang()) === 'en' ? e.en : e.ko; }

  /* --------------------------------------------------- pure helpers ------- */
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }
  // Only allow official law.go.kr http(s) links to become anchors. Anything else
  // (javascript:, data:, other hosts, empty) returns '' → rendered as a plain
  // "check official text" hint instead of a link.
  function safeSourceUrl(url) {
    var u = String(url == null ? '' : url).trim();
    if (!/^https?:\/\//i.test(u)) return '';
    var rest = u.replace(/^https?:\/\//i, '');
    var host = rest.split('/')[0].split('?')[0].toLowerCase();
    if (host === 'law.go.kr' || /(^|\.)law\.go\.kr$/.test(host)) return u;
    return '';
  }
  function metaLine(parts) {
    return parts.filter(function (p) { return p != null && String(p).trim() !== ''; })
      .map(escapeHtml).join(' · ');
  }
  function sourceLinkHtml(url, lang) {
    var safe = safeSourceUrl(url);
    if (!safe) return '<span class="lss-needsrc">' + escapeHtml(S('checkOfficial', lang)) + '</span>';
    return '<a class="lss-src" href="' + escapeHtml(safe) + '" target="_blank" rel="noopener noreferrer">'
      + escapeHtml(S('viewSource', lang)) + ' ↗</a>';
  }

  // When true, the original Korean source snippet is shown expanded in a non-KO
  // UI (set by the "공식 원문 함께 보기 / Show official source text" option). Default
  // collapsed so non-KO users are never shown raw Korean legal text unasked, but
  // it is always one click away — never hidden, never machine-translated.
  var optShowOriginalOpen = false;
  function setShowOriginal(on) { optShowOriginalOpen = !!on; }

  // Render a source snippet honestly by UI language. In KO the Korean text is the
  // source language, shown as-is. In a non-KO UI the Korean source text is kept
  // accessible behind a clearly-labelled "Show original Korean" toggle (never
  // presented as an official English/translated version).
  function _snippetHtml(text, lang) {
    if (!text) return '';
    var esc = '<p class="lss-snip">' + escapeHtml(text) + '</p>';
    if ((lang || lssLang()) === 'en') {
      var sum = escapeHtml(S('srcShowOriginal', lang)) + ' · ' + escapeHtml(S('srcKoBadge', lang));
      return '<details class="lss-orig"' + (optShowOriginalOpen ? ' open' : '')
        + '><summary class="lss-orig-sum">' + sum + '</summary>' + esc + '</details>';
    }
    return esc;
  }
  // Korean-source language badge (shown only in a non-KO UI).
  function _langBadgeHtml(lang) {
    return (lang || lssLang()) === 'en'
      ? '<span class="lss-langbadge">' + escapeHtml(S('srcKoBadge', lang)) + '</span>' : '';
  }
  // Per-card honest notice that the official text is Korean (backend-provided in a
  // non-KO UI, with a static fallback). Never shown in KO.
  function _noticeHtml(r, lang) {
    var notice = (r && r.translationNotice) ? r.translationNotice
      : ((lang || lssLang()) === 'en' ? S('officialKoNotice', lang) : '');
    return notice ? '<p class="lss-srcnotice">' + escapeHtml(notice) + '</p>' : '';
  }

  function buildLawCardHtml(r, lang) {
    r = r || {};
    var title = r.title ? escapeHtml(r.title) : escapeHtml(S('untitled', lang));
    var dates = [];
    if (r.promulgationDate) dates.push(S('promulgated', lang) + ' ' + r.promulgationDate);
    if (r.effectiveDate) dates.push(S('effective', lang) + ' ' + r.effectiveDate);
    var sub = metaLine([r.type, r.articleNo].concat(dates));
    var snippet = _snippetHtml(r.snippet, lang);
    var strength = r.strengthLabel ? '<span class="lss-strength">' + escapeHtml(r.strengthLabel) + '</span>' : '';
    return '<article class="lss-card">'
      + '<h4 class="lss-card-title">' + title + '</h4>'
      + (sub ? '<p class="lss-card-sub">' + sub + '</p>' : '')
      + _noticeHtml(r, lang)
      + snippet
      + '<div class="lss-card-foot">' + strength + _langBadgeHtml(lang) + sourceLinkHtml(r.sourceUrl, lang) + '</div>'
      + '</article>';
  }
  function buildPrecedentCardHtml(r, lang) {
    r = r || {};
    var title = r.title ? escapeHtml(r.title) : escapeHtml(S('untitled', lang));
    var sub = metaLine([r.court, r.caseNumber, r.decisionDate]);
    var snippet = _snippetHtml(r.summary, lang);
    var strength = r.strengthLabel ? '<span class="lss-strength">' + escapeHtml(r.strengthLabel) + '</span>' : '';
    return '<article class="lss-card lss-card-prec">'
      + '<h4 class="lss-card-title">' + title + '</h4>'
      + (sub ? '<p class="lss-card-sub">' + sub + '</p>' : '')
      + _noticeHtml(r, lang)
      + snippet
      + '<div class="lss-card-foot">'
      + strength
      + _langBadgeHtml(lang)
      + sourceLinkHtml(r.sourceUrl, lang)
      + '<span class="lss-prec-flag">' + escapeHtml(S('checkOfficial', lang)) + '</span>'
      + '</div>'
      + '</article>';
  }

  function stateBlock(icon, title, body) {
    return '<div class="lss-state">'
      + '<div class="lss-state-ic" aria-hidden="true">' + icon + '</div>'
      + '<p class="lss-state-title">' + escapeHtml(title) + '</p>'
      + (body ? '<p class="lss-state-body">' + escapeHtml(body) + '</p>' : '')
      + '</div>';
  }
  // state: 'idle' | 'loading' | 'empty' | 'error' | 'missing-key' | 'results'
  function buildResultsHtml(state, kind, data, lang) {
    if (state === 'loading') {
      return '<div class="lss-state lss-loading"><div class="lss-spinner" aria-hidden="true"></div>'
        + '<p class="lss-state-title">' + escapeHtml(kind === 'precedents' ? S('loadingPrec', lang) : S('loadingLaws', lang)) + '</p></div>';
    }
    if (state === 'missing-key') return stateBlock('🔧', S('missingKeyTitle', lang), S('missingKeyBody', lang));
    if (state === 'error') return stateBlock('⚠️', S('errorTitle', lang), S('errorBody', lang));
    if (state === 'idle') return stateBlock('🔎', S('idleTitle', lang), S('idleBody', lang));
    var list = data || [];
    if (state === 'empty' || !list.length) return stateBlock('📭', S('emptyTitle', lang), S('emptyBody', lang));
    var cards = list.map(function (r) {
      return kind === 'precedents' ? buildPrecedentCardHtml(r, lang) : buildLawCardHtml(r, lang);
    }).join('');
    var note = kind === 'precedents'
      ? '<p class="lss-results-note">' + escapeHtml(S('precNote', lang)) + '</p>'
      : '';
    return '<div class="lss-results">' + cards + '</div>' + note;
  }

  // Map a backend JSON envelope to a UI state. Pure → unit-testable.
  function classifyResponse(json) {
    if (!json || typeof json !== 'object') return { state: 'error', results: [] };
    if (json.ok) {
      var results = Array.isArray(json.results) ? json.results : [];
      return { state: results.length ? 'results' : 'empty', results: results };
    }
    if (json.error === 'LAW_API_OC is not configured' || json.reason === 'not_configured') {
      return { state: 'missing-key', results: [] };
    }
    return { state: 'error', results: [] };
  }

  /* --------------------------------------------------- research (depth) --- */
  var DEPTHS = ['fast', 'basic', 'pro'];
  var DEPTH_KEY = { fast: 'depthFast', basic: 'depthBasic', pro: 'depthPro' };
  var DEPTH_DESC_KEY = { fast: 'depthFastDesc', basic: 'depthBasicDesc', pro: 'depthProDesc' };
  // Client-side mirror of the backend auto-selector (UI suggestion only; the
  // backend decides authoritatively). Keep the heuristics in sync.
  var PRO_TRIGGERS = ['판례', '불허', '취소소송', '강제퇴거', '출국명령', '난민', '귀화 불허', '행정심판', '소송', 'appeal', 'precedent', 'refusal', 'denial', 'deportation'];
  function clientAutoDepth(question) {
    var t = String(question == null ? '' : question).trim();
    var low = t.toLowerCase();
    for (var i = 0; i < PRO_TRIGGERS.length; i++) {
      var kw = PRO_TRIGGERS[i];
      if (/^[\x00-\x7F]*$/.test(kw)) { if (low.indexOf(kw) !== -1) return 'pro'; }
      else if (t.indexOf(kw) !== -1) return 'pro';
    }
    var clauses = (t.split('?').length - 1) + (t.split('，').length - 1) + (t.split(',').length - 1);
    if (t.length >= 90 || clauses >= 3) return 'pro';
    if (t.length <= 22) return 'fast';
    return 'basic';
  }
  function buildDepthSelectorHtml(depth, lang) {
    var cur = DEPTHS.indexOf(depth) === -1 ? 'basic' : depth;
    var btns = DEPTHS.map(function (d) {
      var on = d === cur;
      return '<button type="button" class="lss-depth-btn' + (on ? ' lss-depth-on' : '') + '" role="radio" aria-checked="' + (on ? 'true' : 'false') + '" data-lss-depth="' + d + '">' + escapeHtml(S(DEPTH_KEY[d], lang)) + '</button>';
    }).join('');
    return '<div class="lss-depth">'
      + '<span class="lss-depth-label">' + escapeHtml(S('researchDepthLabel', lang)) + '</span>'
      + '<div class="lss-depth-row" role="radiogroup" aria-label="' + escapeHtml(S('researchDepthLabel', lang)) + '">' + btns + '</div>'
      + '<p class="lss-depth-desc">' + escapeHtml(S(DEPTH_DESC_KEY[cur], lang)) + '</p>'
      + '</div>';
  }

  function _ul(items) {
    if (!items || !items.length) return '';
    return '<ul class="lss-rlist">' + items.map(function (i) { return '<li>' + escapeHtml(i) + '</li>'; }).join('') + '</ul>';
  }
  function _termChips(terms, kind) {
    if (!terms || !terms.length) return '';
    return '<div class="lss-rterms">' + terms.map(function (t) {
      return '<button type="button" class="lss-rterm" data-lss-rterm-kind="' + escapeHtml(kind) + '" data-lss-rterm="' + escapeHtml(t) + '">' + escapeHtml(t) + ' ↗</button>';
    }).join('') + '</div>';
  }
  function _cards(list, kind, lang) {
    if (!list || !list.length) return '';
    return '<div class="lss-results">' + list.map(function (r) {
      return kind === 'precedents' ? buildPrecedentCardHtml(r, lang) : buildLawCardHtml(r, lang);
    }).join('') + '</div>';
  }
  function _sec(title, inner) {
    if (!inner) return '';
    return '<section class="lss-rsec"><h4 class="lss-rsec-title">' + escapeHtml(title) + '</h4>' + inner + '</section>';
  }
  // Collapsible section (source drawer). Native <details> gives built-in
  // aria-expanded semantics and keyboard support (§7/§8). Open by default.
  function _secDrawer(title, inner) {
    if (!inner) return '';
    return '<details class="lss-rsec lss-rdrawer" open><summary class="lss-rsec-title lss-rsummary">'
      + escapeHtml(title) + '</summary>' + inner + '</details>';
  }

  // Normalize a synthesis object into the canonical rich shape (mirrors the
  // backend _normalize_synthesis). Accepts BOTH the richer BetterLegalResearch
  // shape (issueMap / applicationPoints / object riskFlags / documentsToCheck /
  // rule) AND the original flatter shape (issues / analysis / string riskFlags /
  // nextDocuments / text). Pure → unit-testable.
  function _normSidList(v) {
    if (Array.isArray(v)) return v.map(function (x) { return String(x == null ? '' : x).trim(); }).filter(Boolean);
    if (typeof v === 'string' && v.trim()) return [v.trim()];
    return [];
  }
  function normalizeSynthesis(raw) {
    var syn = raw || {};
    var out = { summary: String(syn.summary || '').trim(), caution: String(syn.caution || '').trim() };
    var issueMap = [];
    if (Array.isArray(syn.issueMap) && syn.issueMap.length) {
      syn.issueMap.forEach(function (it) {
        if (it && typeof it === 'object') {
          var issue = String(it.issue || it.text || '').trim();
          if (issue) issueMap.push({ issue: issue, whyItMatters: String(it.whyItMatters || '').trim(), sourceIds: _normSidList(it.sourceIds) });
        } else if (String(it || '').trim()) { issueMap.push({ issue: String(it).trim(), whyItMatters: '', sourceIds: [] }); }
      });
    } else {
      _normSidList(syn.issues).forEach(function (s) { issueMap.push({ issue: s, whyItMatters: '', sourceIds: [] }); });
    }
    out.issueMap = issueMap;
    out.sourceBackedRules = (syn.sourceBackedRules || []).map(function (it) {
      if (it && typeof it === 'object') { var rule = String(it.rule || it.text || '').trim(); return rule ? { rule: rule, sourceIds: _normSidList(it.sourceIds) } : null; }
      return String(it || '').trim() ? { rule: String(it).trim(), sourceIds: [] } : null;
    }).filter(Boolean);
    var rawPts = (Array.isArray(syn.applicationPoints) && syn.applicationPoints.length) ? syn.applicationPoints : syn.analysis;
    out.applicationPoints = (rawPts || []).map(function (it) {
      if (it && typeof it === 'object') {
        var p = String(it.point || it.text || '').trim();
        if (!p) return null;
        var c = String(it.confidence || '').toLowerCase();
        return { point: p, confidence: (c === 'high' || c === 'medium' || c === 'low') ? c : 'low', sourceIds: _normSidList(it.sourceIds) };
      }
      return String(it || '').trim() ? { point: String(it).trim(), confidence: 'low', sourceIds: [] } : null;
    }).filter(Boolean);
    out.riskFlags = (syn.riskFlags || []).map(function (it) {
      if (it && typeof it === 'object') { var r = String(it.risk || it.text || '').trim(); return r ? { risk: r, why: String(it.why || '').trim(), sourceIds: _normSidList(it.sourceIds) } : null; }
      return String(it || '').trim() ? { risk: String(it).trim(), why: '', sourceIds: [] } : null;
    }).filter(Boolean);
    out.missingFacts = _normSidList(syn.missingFacts);
    out.nextQuestions = _normSidList(syn.nextQuestions);
    out.documentsToCheck = (Array.isArray(syn.documentsToCheck) && syn.documentsToCheck.length) ? _normSidList(syn.documentsToCheck) : _normSidList(syn.nextDocuments);
    out.limitations = _normSidList(syn.limitations);
    return out;
  }

  // Status badge (기본 리서치 결과 / AI 리서치 요약 / 검증 실패).
  function _badgeHtml(status, lang, warning) {
    var cls = 'lss-badge', label;
    if (status === 'llm') { cls += ' lss-badge-ai'; label = S('badgeAI', lang); }
    else if (status === 'validation_failed') { cls += ' lss-badge-fail'; label = S('badgeFailed', lang); }
    else { label = S('badgeStandard', lang); }
    var warn = (status === 'validation_failed' && warning)
      ? '<p class="lss-badge-warn">' + escapeHtml(warning) + '</p>' : '';
    return '<div class="lss-badge-row"><span class="' + cls + '">' + escapeHtml(label) + '</span></div>' + warn;
  }

  // Source cards (always shown): grouped by type for pro, flat otherwise.
  function _sourceCardsHtml(result, lang) {
    if (result.depth === 'pro' && result.sourceGroups && result.sourceGroups.length) {
      return result.sourceGroups.map(function (g) {
        var cards = (g.cards || []).map(function (c) {
          if (g.group === 'precedent') return buildPrecedentCardHtml(c, lang);
          if (g.group === 'paradiso') return '<article class="lss-card"><h4 class="lss-card-title">' + escapeHtml(c.title || '') + '</h4>'
            + (c.note ? '<p class="lss-card-sub">' + escapeHtml(c.note) + '</p>' : '') + '</article>';
          return buildLawCardHtml(c, lang);
        }).join('');
        return '<div class="lss-rgroup"><h5 class="lss-rgroup-title">' + escapeHtml(g.label) + '</h5><div class="lss-results">' + cards + '</div></div>';
      }).join('');
    }
    return _cards(result.laws, 'laws', lang) + _cards(result.precedents, 'precedents', lang);
  }

  // Render the validated source-grounded LLM synthesis. Pure → unit-testable.
  // Every dynamic string is escaped; sourceId references resolve to source titles.
  function buildSynthesisHtml(result, lang) {
    lang = lang || lssLang();
    var syn = normalizeSynthesis(result.synthesis);
    var depth = result.depth || 'basic';
    var cautionLabel = lang === 'en' ? 'Caution' : '주의';
    var srcMap = {};
    (result.synthesisSources || []).forEach(function (s) { srcMap[s.sourceId] = s.title || s.sourceId; });
    function basis(ids) {
      if (!ids || !ids.length) return '';
      return ' <span class="lss-basis">' + ids.map(function (id) {
        return '[' + escapeHtml(S('synthBasis', lang)) + ': ' + escapeHtml(srcMap[id] || id) + ']';
      }).join(' ') + '</span>';
    }
    function issueList(items) {
      if (!items || !items.length) return '';
      return '<ul class="lss-rlist">' + items.map(function (it) {
        var why = it.whyItMatters
          ? ' <span class="lss-why">— ' + escapeHtml(S('whyItMattersLabel', lang)) + ': ' + escapeHtml(it.whyItMatters) + '</span>' : '';
        return '<li>' + escapeHtml(it.issue || '') + why + basis(it.sourceIds) + '</li>';
      }).join('') + '</ul>';
    }
    function ruleList(items) {
      if (!items || !items.length) return '';
      return '<ul class="lss-rlist">' + items.map(function (it) {
        return '<li>' + escapeHtml(it.rule || '') + basis(it.sourceIds) + '</li>';
      }).join('') + '</ul>';
    }
    function pointList(items) {
      if (!items || !items.length) return '';
      return '<ul class="lss-rlist">' + items.map(function (it) {
        var conf = it.confidence || 'low';
        return '<li>' + escapeHtml(it.point || '') + ' <span class="lss-conf lss-conf-' + escapeHtml(conf) + '">' + escapeHtml(conf) + '</span>' + basis(it.sourceIds) + '</li>';
      }).join('') + '</ul>';
    }
    function riskList(items) {
      if (!items || !items.length) return '';
      return '<ul class="lss-rlist">' + items.map(function (it) {
        var why = it.why ? ' — ' + escapeHtml(it.why) : '';
        return '<li>' + escapeHtml(it.risk || '') + why + basis(it.sourceIds) + '</li>';
      }).join('') + '</ul>';
    }
    var html = '<div class="lss-research lss-synth" role="status" aria-live="polite">';
    html += '<div class="lss-rhead"><span class="lss-rdepth">' + escapeHtml(result.depthLabel || S(DEPTH_KEY[depth], lang)) + '</span></div>';
    if (depth === 'pro') html += '<p class="lss-rmemo">' + escapeHtml(S('synthMemoTitle', lang)) + '</p>';
    // Honest "unofficial / source may be Korean" notice (non-KO UI only).
    var tNotice = S('translatedSummaryNotice', lang);
    if (tNotice) html += '<p class="lss-synth-notice">' + escapeHtml(tNotice) + '</p>';
    if (syn.summary) html += _sec(S('synthSummary', lang), '<p class="lss-rnote">' + escapeHtml(syn.summary) + '</p>');
    html += _sec(S('secIssueMap', lang), issueList(syn.issueMap));
    html += _sec(S('synthRules', lang), ruleList(syn.sourceBackedRules));
    html += _sec(S('secApplyPoints', lang), pointList(syn.applicationPoints));
    html += _sec(S('secRisks', lang), riskList(syn.riskFlags));
    html += _sec(S('secMissing', lang), _ul(syn.missingFacts));
    html += _sec(S('synthNextQ', lang), _ul(syn.nextQuestions));
    html += _sec(S('secDocsToCheck', lang), _ul(syn.documentsToCheck));
    html += _sec(S('secLimits', lang), _ul(syn.limitations));
    html += _secDrawer(S('secSources', lang), _sourceCardsHtml(result, lang)); // always show source cards (collapsible drawer)
    var caution = syn.caution || result.disclaimer || S('disclaimer', lang);
    html += '<div class="lss-rcaution"><strong>' + escapeHtml(cautionLabel) + '</strong> ' + escapeHtml(caution) + '</div>';
    html += '</div>';
    return html;
  }

  // Render the deterministic backend research result into depth-structured,
  // escaped HTML. Pure → unit-testable.
  function buildDeterministicResearchHtml(result, lang) {
    var depth = result.depth || 'basic';
    var cautionLabel = lang === 'en' ? 'Caution' : '주의';
    var html = '<div class="lss-research" role="status" aria-live="polite">';
    html += '<div class="lss-rhead"><span class="lss-rdepth">' + escapeHtml(result.depthLabel || S(DEPTH_KEY[depth], lang)) + '</span>'
      + (result.depthAutoSelected ? '<span class="lss-rauto">' + escapeHtml(S('autoSuggested', lang)) + '</span>' : '') + '</div>';

    if (depth === 'fast') {
      html += _sec(S('secIssues', lang), _ul(result.issues));
      html += _sec(S('secLawTerms', lang), _termChips(result.lawSearchTerms, 'laws'));
      html += _sec(S('secLaws', lang), _cards(result.laws, 'laws', lang));
    } else {
      if (depth === 'pro') html += '<p class="lss-rmemo">' + escapeHtml((result.headings && result.headings[0]) || '') + '</p>';
      html += _sec(S('secIssues', lang), _ul(result.issues));
      html += _sec(S('secMissing', lang), _ul(result.missingFacts));
      html += _sec(S('secLawTerms', lang), _termChips(result.lawSearchTerms, 'laws'));
      html += _sec(S('secLaws', lang), _cards(result.laws, 'laws', lang));
      var precInner = _termChips(result.precedentSearchTerms, 'precedents') + _cards(result.precedents, 'precedents', lang);
      html += _sec(S('secPrecedents', lang), precInner);
      if (depth === 'pro') html += _sec(S('secApply', lang), '<p class="lss-rnote">' + escapeHtml(S('applyNote', lang)) + '</p>');
      html += _sec(S('secRisks', lang), _ul(result.riskFlags));
      html += _sec(S('secNext', lang), _ul(result.nextChecks));
      if (depth === 'pro' && result.sourceGroups && result.sourceGroups.length) {
        html += _secDrawer(S('secSources', lang), _sourceCardsHtml(result, lang));
      }
    }
    html += _sec(S('secLimits', lang), _ul(result.limitations));
    html += '<div class="lss-rcaution"><strong>' + escapeHtml(cautionLabel) + '</strong> ' + escapeHtml(result.disclaimer || S('disclaimer', lang)) + '</div>';
    html += '</div>';
    return html;
  }

  // Top-level research render: status badge + (synthesis | deterministic) view.
  function buildResearchHtml(result, lang) {
    if (!result || result.ok === false) {
      var st = (result && result.error === 'LAW_API_OC is not configured') ? 'missing-key'
        : (result && result.error === 'empty_question') ? 'idle' : 'error';
      return buildResultsHtml(st, 'laws', [], lang);
    }
    var status = result.synthesisStatus || 'deterministic';
    var badge = _badgeHtml(status, lang, result.synthesisWarning);
    if (status === 'llm' && result.synthesis) return badge + buildSynthesisHtml(result, lang);
    return badge + buildDeterministicResearchHtml(result, lang);
  }

  /* ------------------------------------------------------ panel markup ---- */
  function panelHtml(lang) {
    var chips = CHIPS.map(function (c, i) {
      return '<button type="button" class="lss-chip" data-lss-chip="' + i + '">' + escapeHtml(chipLabel(c, lang)) + '</button>';
    }).join('');
    var examples = RESEARCH_EXAMPLES.map(function (e, i) {
      return '<button type="button" class="lss-example" data-lss-example="' + i + '">' + escapeHtml(exampleText(e, lang)) + '</button>';
    }).join('');
    return '<div class="lss-panel">'
      + '<button type="button" class="lss-head" data-lss-toggle aria-expanded="false" aria-controls="lssBody">'
      + '<span class="lss-head-main"><span class="lss-head-title">' + escapeHtml(S('title', lang)) + '</span>'
      + '<span class="lss-ref-chip">' + escapeHtml(S('refChip', lang)) + '</span></span>'
      + '<span class="lss-head-sub">' + escapeHtml(S('subtitle', lang)) + '</span>'
      + '<span class="lss-chevron" aria-hidden="true">▾</span>'
      + '</button>'
      + '<div class="lss-body" id="lssBody" hidden>'
      + '<p class="lss-disclaimer">' + escapeHtml(S('disclaimer', lang)) + '</p>'
      + '<div class="lss-tabs" role="tablist" aria-label="' + escapeHtml(S('title', lang)) + '">'
      + '<button type="button" class="lss-tab lss-tab-on" role="tab" aria-selected="true" data-lss-tab="laws">' + escapeHtml(S('tabLaws', lang)) + '</button>'
      + '<button type="button" class="lss-tab" role="tab" aria-selected="false" data-lss-tab="precedents">' + escapeHtml(S('tabPrec', lang)) + '</button>'
      + '<button type="button" class="lss-tab" role="tab" aria-selected="false" data-lss-tab="research">' + escapeHtml(S('tabResearch', lang)) + '</button>'
      + '</div>'
      // Term-search area (Laws / Precedents tabs)
      + '<div class="lss-search-area" data-lss-area="search">'
      + '<div class="lss-searchbar">'
      + '<input type="search" class="lss-input" data-lss-input placeholder="' + escapeHtml(S('inputPlaceholder', lang)) + '" aria-label="' + escapeHtml(S('inputAria', lang)) + '" maxlength="' + MAX_QUERY + '">'
      + '<button type="button" class="lss-search-btn" data-lss-search>' + escapeHtml(S('searchBtn', lang)) + '</button>'
      + '</div>'
      + '<div class="lss-chips" aria-label="' + escapeHtml(S('chipsLabel', lang)) + '">' + chips + '</div>'
      + '</div>'
      // Research area (Research tab) — positioning + examples + depth + options + question + run
      + '<div class="lss-research-area" data-lss-area="research" hidden>'
      + '<p class="lss-positioning">' + escapeHtml(S('positioning', lang)) + '</p>'
      + '<div class="lss-examples"><span class="lss-examples-label">' + escapeHtml(S('examplesLabel', lang)) + '</span>'
      + '<div class="lss-examples-row">' + examples + '</div></div>'
      + buildDepthSelectorHtml('basic', lang)
      + '<div class="lss-options" role="group" aria-label="' + escapeHtml(S('examplesLabel', lang)) + '">'
      + '<label class="lss-opt"><input type="checkbox" data-lss-opt-prec checked><span>' + escapeHtml(S('optPrecedents', lang)) + '</span></label>'
      + '<label class="lss-opt"><input type="checkbox" data-lss-opt-orig><span>' + escapeHtml(S('optShowOriginal', lang)) + '</span></label>'
      + '<label class="lss-synth-toggle lss-opt" data-lss-synth-wrap><input type="checkbox" data-lss-synth-toggle checked><span>' + escapeHtml(S('synthToggle', lang)) + '</span></label>'
      + '</div>'
      + '<div class="lss-searchbar">'
      + '<textarea class="lss-rinput" data-lss-rinput placeholder="' + escapeHtml(S('researchPlaceholder', lang)) + '" aria-label="' + escapeHtml(S('researchInputAria', lang)) + '" maxlength="800" rows="2"></textarea>'
      + '<button type="button" class="lss-search-btn" data-lss-run>' + escapeHtml(S('researchRun', lang)) + '</button>'
      + '</div>'
      + '</div>'
      + '<div class="lss-out" data-lss-out aria-live="polite">' + buildResultsHtml('idle', 'laws', [], lang) + '</div>'
      + '</div>'
      + '</div>';
  }

  /* --------------------------------------------------------- public API --- */
  var api = {
    escapeHtml: escapeHtml,
    safeSourceUrl: safeSourceUrl,
    buildLawCardHtml: buildLawCardHtml,
    buildPrecedentCardHtml: buildPrecedentCardHtml,
    buildResultsHtml: buildResultsHtml,
    classifyResponse: classifyResponse,
    panelHtml: panelHtml,
    buildDepthSelectorHtml: buildDepthSelectorHtml,
    buildResearchHtml: buildResearchHtml,
    buildSynthesisHtml: buildSynthesisHtml,
    normalizeSynthesis: normalizeSynthesis,
    clientAutoDepth: clientAutoDepth,
    DEPTHS: DEPTHS,
    CHIPS: CHIPS,
    RESEARCH_EXAMPLES: RESEARCH_EXAMPLES,
    STR_KO: STR_KO,
    STR_EN: STR_EN,
    S: S
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoLegalSearch = api;

  // Everything below needs a real DOM. Skip in Node/pure-test contexts.
  if (typeof document === 'undefined') return;

  /* --------------------------------------------------------- API base ----- */
  function apiBase() {
    try {
      if (typeof window !== 'undefined' && window.PARADISO_BACKEND_URL && String(window.PARADISO_BACKEND_URL).trim()) {
        return String(window.PARADISO_BACKEND_URL).trim();
      }
    } catch (e) { /* ignore */ }
    try {
      var h = (location && location.hostname) || '';
      if (h === 'localhost' || h === '127.0.0.1' || (location && location.protocol === 'file:')) return '';
    } catch (e) { /* ignore */ }
    return DEFAULT_API_BASE;
  }

  /* --------------------------------------------------------- styling ------ */
  function injectStyles() {
    if (document.getElementById('lssStyles')) return;
    var css = ''
      + '.lss-root{display:block;width:100%;max-width:720px;margin:1rem auto 0;padding:0 1rem;'
      + 'font-family:var(--ff,"Pretendard Variable",-apple-system,BlinkMacSystemFont,system-ui,sans-serif);box-sizing:border-box;}'
      + '.lss-root *,.lss-root *::before,.lss-root *::after{box-sizing:border-box;}'
      + '.lss-panel{border:1px solid var(--bd,#2D5A50);border-radius:var(--btn-r-lg,14px);background:var(--bg1,#113B32);overflow:hidden;}'
      + '.lss-head{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem .6rem;width:100%;text-align:left;'
      + 'min-height:56px;padding:.85rem 1rem;background:transparent;border:0;cursor:pointer;color:var(--t1,#F3EEDF);}'
      + '.lss-head:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:-2px;}'
      + '.lss-head-main{display:inline-flex;align-items:center;gap:.5rem;}'
      + '.lss-head-title{font-size:1rem;font-weight:850;color:var(--ac,#34D4A8);}'
      + '.lss-ref-chip{font-size:.66rem;font-weight:800;letter-spacing:.04em;padding:.1rem .45rem;border-radius:999px;'
      + 'border:1px solid var(--bd,#2D5A50);color:var(--t2,#C7BFA8);}'
      + '.lss-head-sub{flex:1 1 100%;font-size:.8rem;color:var(--t2,#C7BFA8);line-height:1.45;}'
      + '.lss-chevron{margin-left:auto;color:var(--t3,#8C8572);transition:transform .2s;}'
      + '.lss-head[aria-expanded="true"] .lss-chevron{transform:rotate(180deg);}'
      + '.lss-body{padding:0 1rem 1.1rem;}'
      + '.lss-body[hidden]{display:none;}'
      + '.lss-disclaimer{font-size:.78rem;line-height:1.6;color:var(--t2,#C7BFA8);background:rgba(0,0,0,.12);'
      + 'border:1px solid var(--bd2,#224A41);border-left:3px solid var(--warning,#E68A3A);border-radius:8px;padding:.6rem .7rem;margin:.2rem 0 .9rem;word-break:keep-all;}'
      + '.lss-tabs{display:flex;gap:.4rem;margin:0 0 .7rem;}'
      + '.lss-tab{flex:0 0 auto;min-height:40px;padding:.4rem 1rem;border-radius:999px;cursor:pointer;font:inherit;'
      + 'font-size:.88rem;font-weight:750;border:1.5px solid var(--bd,#2D5A50);background:transparent;color:var(--t2,#C7BFA8);}'
      + '.lss-tab:hover{border-color:var(--ac,#34D4A8);}'
      + '.lss-tab:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-tab-on{background:var(--acL,#163E36);border-color:var(--ac2,#17B388);color:var(--t1,#F3EEDF);}'
      + '.lss-searchbar{display:flex;gap:.5rem;margin:0 0 .7rem;}'
      + '.lss-input{flex:1 1 auto;min-width:0;min-height:46px;padding:.6rem .85rem;border-radius:10px;'
      + 'border:1.5px solid var(--bd,#2D5A50);background:var(--bg0,#0B2A24);color:var(--t1,#F3EEDF);font:600 16px/1.3 inherit;}'
      + '.lss-input:focus{outline:2px solid var(--ac,#34D4A8);outline-offset:1px;border-color:var(--ac,#34D4A8);}'
      + '.lss-search-btn{flex:0 0 auto;min-height:46px;padding:0 1.1rem;border-radius:10px;cursor:pointer;font:inherit;'
      + 'font-weight:800;font-size:.9rem;border:1px solid var(--ac,#34D4A8);background:var(--ac,#34D4A8);color:#06231C;}'
      + '.lss-search-btn:hover{background:var(--ac2,#17B388);border-color:var(--ac2,#17B388);}'
      + '.lss-search-btn:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 .9rem;}'
      + '.lss-chip{min-height:38px;padding:.35rem .75rem;border-radius:999px;cursor:pointer;font:inherit;font-size:.82rem;font-weight:600;'
      + 'border:1px solid var(--bd,#2D5A50);background:var(--bg2,#184B40);color:var(--t1,#F3EEDF);}'
      + '.lss-chip:hover{border-color:var(--ac,#34D4A8);color:var(--ac,#34D4A8);}'
      + '.lss-chip:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-out{min-height:60px;}'
      + '.lss-results{display:flex;flex-direction:column;gap:.6rem;}'
      + '.lss-results-note{font-size:.76rem;color:var(--t3,#8C8572);line-height:1.5;margin:.6rem 0 0;word-break:keep-all;}'
      + '.lss-card{border:1px solid var(--bd2,#224A41);border-radius:12px;background:var(--bg2,#184B40);padding:.8rem .9rem;}'
      + '.lss-card-prec{border-left:3px solid var(--ac2,#17B388);}'
      + '.lss-card-title{font-size:.95rem;font-weight:800;color:var(--t1,#F3EEDF);margin:0 0 .25rem;line-height:1.4;word-break:keep-all;}'
      + '.lss-card-sub{font-size:.78rem;color:var(--t2,#C7BFA8);margin:0 0 .35rem;word-break:keep-all;}'
      + '.lss-snip{font-size:.84rem;line-height:1.6;color:var(--t1,#F3EEDF);margin:.2rem 0 .45rem;word-break:keep-all;}'
      + '.lss-card-foot{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem .8rem;}'
      + '.lss-src{display:inline-flex;align-items:center;min-height:36px;font-size:.82rem;font-weight:750;color:var(--ac,#34D4A8);text-decoration:none;}'
      + '.lss-src:hover{text-decoration:underline;}'
      + '.lss-src:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-needsrc,.lss-prec-flag{font-size:.74rem;font-weight:700;color:var(--warning,#E68A3A);}'
      + '.lss-strength{font-size:.7rem;font-weight:800;padding:.1rem .45rem;border-radius:999px;border:1px solid var(--bd,#2D5A50);color:var(--t2,#C7BFA8);}'
      // depth selector
      + '.lss-depth{margin:0 0 .7rem;}'
      + '.lss-depth-label{display:block;font-size:.74rem;font-weight:800;color:var(--t2,#C7BFA8);letter-spacing:.03em;margin:0 0 .4rem;}'
      + '.lss-depth-row{display:flex;gap:.4rem;flex-wrap:wrap;}'
      + '.lss-depth-btn{flex:1 1 auto;min-height:42px;padding:.4rem .7rem;border-radius:10px;cursor:pointer;font:inherit;font-size:.85rem;font-weight:750;'
      + 'border:1.5px solid var(--bd,#2D5A50);background:transparent;color:var(--t2,#C7BFA8);}'
      + '.lss-depth-btn:hover{border-color:var(--ac,#34D4A8);}'
      + '.lss-depth-btn:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-depth-on{background:var(--acL,#163E36);border-color:var(--ac2,#17B388);color:var(--t1,#F3EEDF);}'
      + '.lss-depth-desc{font-size:.78rem;line-height:1.55;color:var(--t3,#8C8572);margin:.5rem 0 0;word-break:keep-all;}'
      + '.lss-rinput{flex:1 1 auto;min-width:0;min-height:48px;padding:.6rem .85rem;border-radius:10px;resize:vertical;'
      + 'border:1.5px solid var(--bd,#2D5A50);background:var(--bg0,#0B2A24);color:var(--t1,#F3EEDF);font:600 16px/1.45 inherit;}'
      + '.lss-rinput:focus{outline:2px solid var(--ac,#34D4A8);outline-offset:1px;border-color:var(--ac,#34D4A8);}'
      // research result
      + '.lss-research{display:flex;flex-direction:column;gap:.2rem;}'
      + '.lss-rhead{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:.2rem 0 .4rem;}'
      + '.lss-rdepth{font-size:.78rem;font-weight:850;color:var(--ac,#34D4A8);background:var(--acL,#163E36);border:1px solid var(--ac2,#17B388);border-radius:999px;padding:.18rem .6rem;}'
      + '.lss-rauto{font-size:.72rem;font-weight:700;color:var(--t3,#8C8572);}'
      + '.lss-rmemo{font-size:1rem;font-weight:850;color:var(--t1,#F3EEDF);margin:.2rem 0 .3rem;}'
      + '.lss-rsec{border-top:1px solid var(--bd2,#224A41);padding:.6rem 0 .2rem;}'
      + '.lss-rsec-title{font-size:.86rem;font-weight:800;color:var(--t1,#F3EEDF);margin:0 0 .4rem;}'
      + '.lss-rlist{margin:.1rem 0 .3rem;padding-left:1.15rem;}'
      + '.lss-rlist li{font-size:.86rem;line-height:1.6;color:var(--t1,#F3EEDF);margin:.15rem 0;word-break:keep-all;}'
      + '.lss-rnote{font-size:.83rem;line-height:1.6;color:var(--t2,#C7BFA8);margin:.1rem 0;word-break:keep-all;}'
      + '.lss-rterms{display:flex;flex-wrap:wrap;gap:.4rem;margin:.1rem 0 .4rem;}'
      + '.lss-rterm{min-height:34px;padding:.25rem .65rem;border-radius:999px;cursor:pointer;font:inherit;font-size:.8rem;font-weight:650;'
      + 'border:1px dashed var(--bd,#2D5A50);background:transparent;color:var(--ac,#34D4A8);}'
      + '.lss-rterm:hover{border-style:solid;}'
      + '.lss-rterm:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-rgroup{margin:.3rem 0 .5rem;}'
      + '.lss-rgroup-title{font-size:.78rem;font-weight:800;color:var(--ac,#34D4A8);margin:.2rem 0 .35rem;}'
      + '.lss-rcaution{margin:.6rem 0 .2rem;font-size:.8rem;line-height:1.6;color:var(--t2,#C7BFA8);background:rgba(0,0,0,.12);'
      + 'border:1px solid var(--bd2,#224A41);border-left:3px solid var(--warning,#E68A3A);border-radius:8px;padding:.55rem .7rem;word-break:keep-all;}'
      // synthesis: status badge, toggle, basis tags, confidence
      + '.lss-badge-row{margin:.2rem 0 .5rem;}'
      + '.lss-badge{display:inline-block;font-size:.74rem;font-weight:850;padding:.2rem .6rem;border-radius:999px;border:1px solid var(--bd,#2D5A50);color:var(--t2,#C7BFA8);}'
      + '.lss-badge-ai{color:var(--ac,#34D4A8);background:var(--acL,#163E36);border-color:var(--ac2,#17B388);}'
      + '.lss-badge-fail{color:var(--warning,#E68A3A);border-color:var(--warning,#E68A3A);}'
      + '.lss-badge-warn{margin:.35rem 0 0;font-size:.78rem;line-height:1.5;color:var(--warning,#E68A3A);word-break:keep-all;}'
      + '.lss-synth-toggle{display:flex;align-items:center;gap:.45rem;margin:0 0 .7rem;font-size:.85rem;font-weight:650;color:var(--t1,#F3EEDF);cursor:pointer;}'
      + '.lss-synth-toggle[hidden]{display:none;}'
      + '.lss-synth-toggle input{width:18px;height:18px;accent-color:var(--ac,#34D4A8);cursor:pointer;}'
      + '.lss-synth-off{opacity:.55;}'
      + '.lss-basis{font-size:.74rem;font-weight:700;color:var(--t3,#8C8572);}'
      + '.lss-conf{font-size:.68rem;font-weight:850;padding:.05rem .4rem;border-radius:999px;border:1px solid currentColor;}'
      + '.lss-conf-high{color:var(--cov-confirmed,#34D4A8);}'
      + '.lss-conf-medium{color:var(--wm-cov-partial,#F2C879);}'
      + '.lss-conf-low{color:var(--t3,#8C8572);}'
      + '.lss-why{font-size:.8rem;color:var(--t2,#C7BFA8);}'
      // positioning + examples + options (professional UX)
      + '.lss-positioning{font-size:.82rem;line-height:1.6;color:var(--t2,#C7BFA8);margin:.1rem 0 .8rem;word-break:keep-all;}'
      + '.lss-examples{margin:0 0 .8rem;}'
      + '.lss-examples-label{display:block;font-size:.74rem;font-weight:800;color:var(--t2,#C7BFA8);letter-spacing:.03em;margin:0 0 .4rem;}'
      + '.lss-examples-row{display:flex;flex-direction:column;gap:.4rem;}'
      + '.lss-example{text-align:left;min-height:40px;padding:.45rem .7rem;border-radius:10px;cursor:pointer;font:inherit;font-size:.82rem;line-height:1.45;font-weight:600;'
      + 'border:1px solid var(--bd,#2D5A50);background:var(--bg2,#184B40);color:var(--t1,#F3EEDF);word-break:keep-all;}'
      + '.lss-example:hover{border-color:var(--ac,#34D4A8);color:var(--ac,#34D4A8);}'
      + '.lss-example:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-options{display:flex;flex-wrap:wrap;gap:.5rem 1.1rem;margin:0 0 .8rem;}'
      + '.lss-opt{display:flex;align-items:center;gap:.4rem;font-size:.83rem;font-weight:650;color:var(--t1,#F3EEDF);cursor:pointer;}'
      + '.lss-opt input{width:18px;height:18px;accent-color:var(--ac,#34D4A8);cursor:pointer;}'
      // source-language delivery (badge / notice / original toggle)
      + '.lss-langbadge{font-size:.68rem;font-weight:800;padding:.08rem .4rem;border-radius:999px;border:1px solid var(--bd,#2D5A50);color:var(--t2,#C7BFA8);}'
      + '.lss-srcnotice{font-size:.74rem;line-height:1.5;color:var(--t3,#8C8572);margin:.1rem 0 .35rem;word-break:keep-all;}'
      + '.lss-orig{margin:.2rem 0 .45rem;}'
      + '.lss-orig-sum{font-size:.78rem;font-weight:700;color:var(--ac,#34D4A8);cursor:pointer;list-style:none;}'
      + '.lss-orig-sum:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-orig[open] .lss-orig-sum{margin-bottom:.3rem;}'
      // synthesis honesty notice + collapsible source drawer
      + '.lss-synth-notice{font-size:.78rem;line-height:1.55;color:var(--t2,#C7BFA8);background:rgba(0,0,0,.12);'
      + 'border:1px solid var(--bd2,#224A41);border-left:3px solid var(--warning,#E68A3A);border-radius:8px;padding:.5rem .65rem;margin:.2rem 0 .6rem;word-break:keep-all;}'
      + '.lss-rdrawer>.lss-rsummary{cursor:pointer;list-style:none;}'
      + '.lss-rdrawer>.lss-rsummary::-webkit-details-marker{display:none;}'
      + '.lss-rsummary:focus-visible{outline:2px solid var(--ac,#34D4A8);outline-offset:2px;}'
      + '.lss-state{text-align:center;padding:1.6rem 1rem;color:var(--t2,#C7BFA8);}'
      + '.lss-state-ic{font-size:1.6rem;margin-bottom:.4rem;}'
      + '.lss-state-title{font-size:.92rem;font-weight:750;color:var(--t1,#F3EEDF);margin:0 0 .25rem;word-break:keep-all;}'
      + '.lss-state-body{font-size:.8rem;line-height:1.55;color:var(--t2,#C7BFA8);margin:0;word-break:keep-all;}'
      + '.lss-spinner{width:30px;height:30px;margin:.2rem auto .5rem;border:3px solid var(--bd,#2D5A50);border-top-color:var(--ac,#34D4A8);border-radius:50%;animation:lss-spin .8s linear infinite;}'
      + '.lss-rsteps{list-style:none;margin:.4rem 0 0;padding:0;display:inline-block;text-align:left;}'
      + '.lss-rsteps li{font-size:.8rem;color:var(--t2,#C7BFA8);margin:.2rem 0;}'
      + '.lss-rsteps li::before{content:"· ";color:var(--ac,#34D4A8);}'
      + '@keyframes lss-spin{to{transform:rotate(360deg);}}'
      + '@media (max-width:480px){.lss-head-title{font-size:.95rem;}.lss-searchbar{flex-wrap:wrap;}.lss-search-btn{flex:1 1 auto;}}'
      + '@media (prefers-reduced-motion:reduce){.lss-spinner{animation:none;}}'
      // archive_diary (light) theme contrast — mirror the navigator's overrides.
      + 'html[data-editorial-theme="archive_diary"] .lss-input{background:#FFFFFF;}'
      + 'html[data-editorial-theme="archive_diary"] .lss-search-btn{color:#FFFFFF;}'
      + 'html[data-editorial-theme="archive_diary"] .lss-disclaimer{background:rgba(0,0,0,.04);}';
    var style = document.createElement('style');
    style.id = 'lssStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* ----------------------------------------------------------- runtime ---- */
  var state = { kind: 'laws', lastQuery: '', researchDepth: 'basic', depthManual: false, lastResearch: '', useSynthesis: true, providerConfigured: null, includePrecedents: true, showOriginal: false, lastResearchJson: null };
  var root = null;

  function out() { return root && root.querySelector('[data-lss-out]'); }
  function setOut(html) { var o = out(); if (o) { o.innerHTML = html; wireOut(); } }

  // (Re)wire dynamic controls inside the output area (research term chips).
  function wireOut() {
    var o = out();
    if (!o) return;
    o.querySelectorAll('[data-lss-rterm]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var term = btn.getAttribute('data-lss-rterm');
        var kind = btn.getAttribute('data-lss-rterm-kind') === 'precedents' ? 'precedents' : 'laws';
        setTab(kind);
        var input = root.querySelector('[data-lss-input]');
        if (input) input.value = term;
        doSearch(term);
      });
    });
  }

  function doSearch(query) {
    var q = String(query == null ? '' : query).trim().slice(0, MAX_QUERY);
    if (!q) return;
    state.lastQuery = q;
    var input = root.querySelector('[data-lss-input]');
    if (input && input.value !== q) input.value = q;
    var kind = state.kind;
    var lang = lssLang();
    setOut(buildResultsHtml('loading', kind, [], lang));
    var path = kind === 'precedents' ? '/api/legal/precedents/search' : '/api/legal/laws/search';
    var url = apiBase() + path + '?q=' + encodeURIComponent(q);
    fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (json) {
        // Ignore a stale response if the user moved on to a newer query.
        if (state.lastQuery !== q) return;
        var c = classifyResponse(json);
        setOut(buildResultsHtml(c.state, kind, c.results, lssLang()));
      })
      .catch(function () {
        if (state.lastQuery !== q) return;
        setOut(buildResultsHtml('error', kind, [], lssLang()));
      });
  }

  function syncDepthUI() {
    var row = root.querySelector('.lss-depth');
    if (!row) return;
    row.querySelectorAll('[data-lss-depth]').forEach(function (btn) {
      var on = btn.getAttribute('data-lss-depth') === state.researchDepth;
      btn.classList.toggle('lss-depth-on', on);
      btn.setAttribute('aria-checked', on ? 'true' : 'false');
    });
    var desc = row.querySelector('.lss-depth-desc');
    if (desc) desc.textContent = S(DEPTH_DESC_KEY[state.researchDepth] || 'depthBasicDesc', lssLang());
    syncSynthToggle();
  }

  function syncSynthToggle() {
    if (!root) return;
    var wrap = root.querySelector('[data-lss-synth-wrap]');
    var box = root.querySelector('[data-lss-synth-toggle]');
    if (!wrap || !box) return;
    // Hidden for Fast (lightweight, deterministic); shown for Basic/Pro.
    wrap.hidden = (state.researchDepth === 'fast');
    if (state.providerConfigured === false) {
      box.checked = false;
      box.disabled = true;
      state.useSynthesis = false;
      wrap.classList.add('lss-synth-off');
    } else {
      box.disabled = false;
      box.checked = !!state.useSynthesis;
      wrap.classList.remove('lss-synth-off');
    }
  }

  function researchIdleHtml(lang) {
    return '<div class="lss-state"><div class="lss-state-ic" aria-hidden="true">🔬</div>'
      + '<p class="lss-state-title">' + escapeHtml(S('researchIdleTitle', lang)) + '</p>'
      + '<p class="lss-state-body">' + escapeHtml(S('researchIdleBody', lang)) + '</p></div>';
  }

  function doResearch(question) {
    var q = String(question == null ? '' : question).trim().slice(0, 800);
    if (!q) return;
    state.lastResearch = q;
    var lang = lssLang();
    // Deep research can take longer (multiple source searches) — surface the
    // staged work so the wait is legible (§8).
    var effectiveDepth = state.depthManual ? state.researchDepth : clientAutoDepth(q);
    // Surface the staged work so the wait is legible and trustworthy (§2/§8).
    var steps = (effectiveDepth === 'pro') ? (S('proSteps', lang) || []) : (S('basicSteps', lang) || []);
    var stepsHtml = steps.length
      ? '<ul class="lss-rsteps">' + steps.map(function (s) { return '<li>' + escapeHtml(s) + '</li>'; }).join('') + '</ul>'
      : '';
    setOut('<div class="lss-state lss-loading" aria-busy="true"><div class="lss-spinner" aria-hidden="true"></div>'
      + '<p class="lss-state-title">' + escapeHtml(S('researchLoading', lang)) + '</p>' + stepsHtml + '</div>');
    var payload = { question: q, locale: lang, includePrecedents: !!state.includePrecedents };
    // Only pin depth when the user manually chose one; otherwise let the backend
    // auto-select and reflect its choice back into the selector.
    if (state.depthManual) payload.depth = state.researchDepth;
    // Request AI synthesis per the toggle (fast stays deterministic anyway).
    payload.synthesis = (state.useSynthesis && effectiveDepth !== 'fast') ? 'source_grounded_llm' : 'deterministic';
    fetch(apiBase() + '/api/legal/research', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (json) {
        if (state.lastResearch !== q) return;
        state.lastResearchJson = json;
        if (json && json.ok && !state.depthManual && json.depth) { state.researchDepth = json.depth; syncDepthUI(); }
        // Reflect provider availability: disable the toggle if no provider.
        if (json && typeof json.providerConfigured === 'boolean') {
          state.providerConfigured = json.providerConfigured;
          syncSynthToggle();
        }
        setOut(buildResearchHtml(json, lssLang()));
      })
      .catch(function () {
        if (state.lastResearch !== q) return;
        setOut(buildResearchHtml({ ok: false, error: 'search_failed' }, lssLang()));
      });
  }

  function setTab(kind) {
    var valid = (kind === 'precedents' || kind === 'research') ? kind : 'laws';
    state.kind = valid;
    root.querySelectorAll('[data-lss-tab]').forEach(function (btn) {
      var on = btn.getAttribute('data-lss-tab') === valid;
      btn.classList.toggle('lss-tab-on', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    var isResearch = valid === 'research';
    var searchArea = root.querySelector('.lss-search-area');
    var researchArea = root.querySelector('.lss-research-area');
    if (searchArea) searchArea.hidden = isResearch;
    if (researchArea) researchArea.hidden = !isResearch;
    var lang = lssLang();
    if (isResearch) {
      if (state.lastResearch) doResearch(state.lastResearch);
      else setOut(researchIdleHtml(lang));
    } else if (state.lastQuery) {
      doSearch(state.lastQuery);
    } else {
      setOut(buildResultsHtml('idle', valid, [], lang));
    }
  }

  function wire() {
    var toggle = root.querySelector('[data-lss-toggle]');
    var body = root.querySelector('#lssBody');
    if (toggle && body) {
      toggle.addEventListener('click', function () {
        var open = body.hasAttribute('hidden');
        if (open) { body.removeAttribute('hidden'); toggle.setAttribute('aria-expanded', 'true'); }
        else { body.setAttribute('hidden', ''); toggle.setAttribute('aria-expanded', 'false'); }
      });
    }
    root.querySelectorAll('[data-lss-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { setTab(btn.getAttribute('data-lss-tab')); });
    });
    var searchBtn = root.querySelector('[data-lss-search]');
    var input = root.querySelector('[data-lss-input]');
    if (searchBtn && input) {
      searchBtn.addEventListener('click', function () { doSearch(input.value); });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); doSearch(input.value); } });
    }
    root.querySelectorAll('[data-lss-chip]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(btn.getAttribute('data-lss-chip'), 10);
        var chip = CHIPS[idx];
        if (chip) doSearch(chip.query);
      });
    });
    // research: depth selector
    root.querySelectorAll('[data-lss-depth]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.researchDepth = btn.getAttribute('data-lss-depth');
        state.depthManual = true;
        syncDepthUI();
      });
    });
    // research: question + run
    var runBtn = root.querySelector('[data-lss-run]');
    var rinput = root.querySelector('[data-lss-rinput]');
    if (runBtn && rinput) {
      runBtn.addEventListener('click', function () { doResearch(rinput.value); });
      rinput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); doResearch(rinput.value); }
      });
      // Live depth suggestion until the user manually overrides.
      rinput.addEventListener('input', function () {
        if (state.depthManual) return;
        var suggested = clientAutoDepth(rinput.value);
        if (suggested !== state.researchDepth) { state.researchDepth = suggested; syncDepthUI(); }
      });
    }
    // research: example questions → prefill (+ suggest depth), let the user run it
    root.querySelectorAll('[data-lss-example]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var ex = RESEARCH_EXAMPLES[parseInt(btn.getAttribute('data-lss-example'), 10)];
        if (!ex) return;
        var ri = root.querySelector('[data-lss-rinput]');
        if (ri) { ri.value = exampleText(ex, lssLang()); ri.focus(); }
        if (!state.depthManual) {
          var suggested = clientAutoDepth(exampleText(ex, lssLang()));
          if (suggested !== state.researchDepth) { state.researchDepth = suggested; syncDepthUI(); }
        }
      });
    });
    // research: AI synthesis toggle
    var synthBox = root.querySelector('[data-lss-synth-toggle]');
    if (synthBox) {
      synthBox.addEventListener('change', function () { state.useSynthesis = !!synthBox.checked; });
    }
    // research: "search precedents too" option
    var precBox = root.querySelector('[data-lss-opt-prec]');
    if (precBox) {
      precBox.addEventListener('change', function () { state.includePrecedents = !!precBox.checked; });
    }
    // research: "show official source text" option → re-render last result with
    // the Korean original expanded (never machine-translated, just made visible).
    var origBox = root.querySelector('[data-lss-opt-orig]');
    if (origBox) {
      origBox.addEventListener('change', function () {
        state.showOriginal = !!origBox.checked;
        setShowOriginal(state.showOriginal);
        if (state.lastResearchJson) setOut(buildResearchHtml(state.lastResearchJson, lssLang()));
      });
    }
  }

  function render() {
    if (!root) return;
    var lang = lssLang();
    root.innerHTML = panelHtml(lang);
    wire();
    syncDepthUI();
    // Re-open + re-run if we already had a query/research (e.g. language switch).
    if (state.lastQuery || state.lastResearch) {
      var body = root.querySelector('#lssBody');
      var toggle = root.querySelector('[data-lss-toggle]');
      if (body) body.removeAttribute('hidden');
      if (toggle) toggle.setAttribute('aria-expanded', 'true');
      setTab(state.kind);
    }
  }

  function mount() {
    root = document.getElementById('legalSourceSearchRoot');
    if (!root) return false;
    if (!root.classList.contains('lss-root')) root.classList.add('lss-root');
    injectStyles();
    render();
    return true;
  }

  // Expose a tiny runtime surface for the DOM smoke test + future integrations.
  api.mount = mount;
  api.setShowOriginal = setShowOriginal;
  api.doSearch = function (q) { if (root) doSearch(q); };
  api.doResearch = function (q) { if (!root && !mount()) return; setTab('research'); doResearch(q); };
  api.openWith = function (q, kind) { if (!root && !mount()) return; if (kind) state.kind = kind; doSearch(q); };
  // Waymaker → Legal Research handoff (§6): open the Research tab prefilled with
  // the visa code + question + suggested depth, then run.
  api.openResearch = function (opts) {
    opts = opts || {};
    if (!root && !mount()) return;
    var bodyEl = root.querySelector('#lssBody');
    var toggleEl = root.querySelector('[data-lss-toggle]');
    if (bodyEl) bodyEl.removeAttribute('hidden');
    if (toggleEl) toggleEl.setAttribute('aria-expanded', 'true');
    var q = String(opts.question || opts.query || '').trim();
    var code = String(opts.visaCode || '').trim();
    if (code && q.indexOf(code) === -1) q = code + ' ' + q;
    if (opts.depth && DEPTHS.indexOf(opts.depth) !== -1) { state.researchDepth = opts.depth; state.depthManual = true; }
    setTab('research');
    var ri = root.querySelector('[data-lss-rinput]');
    if (ri) ri.value = q;
    syncDepthUI();
    if (q) doResearch(q);
    try { if (root.scrollIntoView) root.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { /* non-fatal */ }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
  window.addEventListener('paradiso-language-applied', function () { try { render(); } catch (e) { /* non-fatal */ } });

  // Decoupled integration seam (§5): Waymaker answers / scenario results can
  // suggest a source check by dispatching
  //   window.dispatchEvent(new CustomEvent('paradiso:legal-search', {detail:{query:'결혼이민 F-6', kind:'laws'}}))
  // which opens this panel and runs the search — without coupling to (or
  // weakening) the gated /api/ask answer pipeline.
  window.addEventListener('paradiso:legal-search', function (e) {
    var d = (e && e.detail) || {};
    if (d && d.query) { try { api.openWith(d.query, d.kind); } catch (err) { /* non-fatal */ } }
  });

  // Richer handoff: open the Legal Research tab prefilled (visa code + question +
  // depth). Dispatched by Waymaker answers via the "법령·판례 기준으로 더 분석하기 /
  // Analyze with legal sources" action.
  //   window.dispatchEvent(new CustomEvent('paradiso:legal-research',
  //     {detail:{question:'...', visaCode:'F-6', depth:'pro'}}))
  window.addEventListener('paradiso:legal-research', function (e) {
    var d = (e && e.detail) || {};
    if (d && (d.question || d.query)) {
      try { api.openResearch({ question: d.question || d.query, visaCode: d.visaCode, depth: d.depth }); }
      catch (err) { /* non-fatal */ }
    }
  });
})();
