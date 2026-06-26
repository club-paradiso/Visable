/* ============================================================================
 * Waymaker by Paradiso — 법령·판례 근거 검색 / Legal source search
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
    title: '법령·판례 근거 검색',
    subtitle: '공식 법령·판례 원문을 직접 확인할 수 있도록 도와드립니다.',
    refChip: '참고용',
    toggleOpen: '법령·판례 근거 검색 열기',
    toggleClose: '접기',
    disclaimer: '법령·판례 검색은 공식 원문 확인을 돕기 위한 기능입니다. Waymaker는 변호사·행정사의 법률 자문을 대체하지 않으며, 실제 허가 여부와 최종 판단은 관계 기관의 심사에 따릅니다.',
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
    precNote: '판례는 개별 사건 판단이며 결과를 보장하지 않습니다. 자세한 내용은 공식 원문을 확인하세요.'
  };
  var STR_EN = {
    title: 'Legal source search',
    subtitle: 'Helps you check official statutes and court precedents for yourself.',
    refChip: 'Reference',
    toggleOpen: 'Open legal source search',
    toggleClose: 'Collapse',
    disclaimer: 'Legal source search helps you check official source materials. Waymaker does not replace legal advice from a qualified professional, and final decisions are made by the competent authorities.',
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
    precNote: 'Precedents are individual case decisions and do not guarantee any outcome. See the official text for details.'
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

  function buildLawCardHtml(r, lang) {
    r = r || {};
    var title = r.title ? escapeHtml(r.title) : escapeHtml(S('untitled', lang));
    var dates = [];
    if (r.promulgationDate) dates.push(S('promulgated', lang) + ' ' + r.promulgationDate);
    if (r.effectiveDate) dates.push(S('effective', lang) + ' ' + r.effectiveDate);
    var sub = metaLine([r.type, r.articleNo].concat(dates));
    var snippet = r.snippet ? '<p class="lss-snip">' + escapeHtml(r.snippet) + '</p>' : '';
    return '<article class="lss-card">'
      + '<h4 class="lss-card-title">' + title + '</h4>'
      + (sub ? '<p class="lss-card-sub">' + sub + '</p>' : '')
      + snippet
      + '<div class="lss-card-foot">' + sourceLinkHtml(r.sourceUrl, lang) + '</div>'
      + '</article>';
  }
  function buildPrecedentCardHtml(r, lang) {
    r = r || {};
    var title = r.title ? escapeHtml(r.title) : escapeHtml(S('untitled', lang));
    var sub = metaLine([r.court, r.caseNumber, r.decisionDate]);
    var snippet = r.summary ? '<p class="lss-snip">' + escapeHtml(r.summary) + '</p>' : '';
    return '<article class="lss-card lss-card-prec">'
      + '<h4 class="lss-card-title">' + title + '</h4>'
      + (sub ? '<p class="lss-card-sub">' + sub + '</p>' : '')
      + snippet
      + '<div class="lss-card-foot">'
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

  /* ------------------------------------------------------ panel markup ---- */
  function panelHtml(lang) {
    var chips = CHIPS.map(function (c, i) {
      return '<button type="button" class="lss-chip" data-lss-chip="' + i + '">' + escapeHtml(chipLabel(c, lang)) + '</button>';
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
      + '</div>'
      + '<div class="lss-searchbar">'
      + '<input type="search" class="lss-input" data-lss-input placeholder="' + escapeHtml(S('inputPlaceholder', lang)) + '" aria-label="' + escapeHtml(S('inputAria', lang)) + '" maxlength="' + MAX_QUERY + '">'
      + '<button type="button" class="lss-search-btn" data-lss-search>' + escapeHtml(S('searchBtn', lang)) + '</button>'
      + '</div>'
      + '<div class="lss-chips" aria-label="' + escapeHtml(S('chipsLabel', lang)) + '">' + chips + '</div>'
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
    CHIPS: CHIPS,
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
      + '.lss-state{text-align:center;padding:1.6rem 1rem;color:var(--t2,#C7BFA8);}'
      + '.lss-state-ic{font-size:1.6rem;margin-bottom:.4rem;}'
      + '.lss-state-title{font-size:.92rem;font-weight:750;color:var(--t1,#F3EEDF);margin:0 0 .25rem;word-break:keep-all;}'
      + '.lss-state-body{font-size:.8rem;line-height:1.55;color:var(--t2,#C7BFA8);margin:0;word-break:keep-all;}'
      + '.lss-spinner{width:30px;height:30px;margin:.2rem auto .5rem;border:3px solid var(--bd,#2D5A50);border-top-color:var(--ac,#34D4A8);border-radius:50%;animation:lss-spin .8s linear infinite;}'
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
  var state = { kind: 'laws', lastQuery: '' };
  var root = null;

  function out() { return root && root.querySelector('[data-lss-out]'); }
  function setOut(html) { var o = out(); if (o) o.innerHTML = html; }

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

  function setTab(kind) {
    state.kind = (kind === 'precedents') ? 'precedents' : 'laws';
    root.querySelectorAll('[data-lss-tab]').forEach(function (btn) {
      var on = btn.getAttribute('data-lss-tab') === state.kind;
      btn.classList.toggle('lss-tab-on', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    if (state.lastQuery) doSearch(state.lastQuery);
    else setOut(buildResultsHtml('idle', state.kind, [], lssLang()));
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
  }

  function render() {
    if (!root) return;
    var lang = lssLang();
    root.innerHTML = panelHtml(lang);
    wire();
    // Re-open + re-run if we already had a query (e.g. language switch).
    if (state.lastQuery) {
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
  api.doSearch = function (q) { if (root) doSearch(q); };
  api.openWith = function (q, kind) { if (!root && !mount()) return; if (kind) state.kind = kind; doSearch(q); };

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
})();
