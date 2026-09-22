(function () {
  'use strict';
  if (typeof document === 'undefined') return;
  var lang = function () { return document.documentElement.lang === 'en' ? 'en' : 'ko'; };
  var copy = {
    ko: {
      search: '비자·체류 검색', forms: '서류 작성', about: '이용 안내', submit: '검색', preparing: '검색을 준비하고 있습니다.', unavailable: '안내 데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요.',
      title: '답이 <em>보이는</em> 한국 생활.', sub: '비자 코드나 지금 상황을 검색하세요.',
      placeholder: '예: F-6 체류기간 연장', pre: '입국 전 · 사증 발급', post: '입국 후 · 체류 관리',
      preSub: '사증 종류, 발급 요건, 필요 서류를 확인하세요.', postSub: '체류기간 연장, 체류자격 변경, 신고 절차를 확인하세요.',
      tools: '자주 찾는 업무', paperwork: '필수 서류 작성', paperworkSub: '신청서·숙소제공확인서 등 필수 서류를 단계별로 작성하세요.',
      reservation: '방문예약 안내', reservationSub: '하이코리아 방문예약 방법과 준비사항을 확인하세요.',
      manuals: '공식 원문 찾기', manualsSub: '사증발급·외국인체류 공식 안내 원문에서 필요한 구절을 찾아보세요.',
      visa: '사증 안내', stay: '체류 안내', original: '원문 보기', sourceLabel: '공식 기준 업데이트',
      language: '언어', languageTitle: '언어 선택', languageSearch: '언어 검색', languageNone: '일치하는 언어가 없어요.',
      disclaimer: 'Visable은 공식 정부 서비스가 아닙니다. 제공 정보는 참고용이며 법적 효력이 없습니다. 최종 판단은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요.',
      allTools: '전체 도구 보기', theme: '화면 테마', guide: '체류자격 안내', all: '전체', sourceTab: '원문',
      manualTitle: '관련 공식 원문', sourceNote: '2026년 9월 기준 공식 안내 원문에서 찾은 구절이에요. 위 안내와 판본이 다를 수 있어요.',
      review: '원문 발췌 · 검토 전', caveat: '표·이미지의 내용과 적용 조건은 원문 페이지에서 확인하세요. 발췌문은 개별 요건을 확정하는 안내가 아닙니다.',
      page: '쪽', pages: '건', excerpt: '본문 펼치기', close: '닫기', loading: '공식 원문을 불러오는 중입니다.',
      error: '원문을 불러오지 못했습니다. 다시 시도하거나 원문 PDF를 열어 확인하세요.', retry: '다시 시도',
      empty: '일치하는 원문이 없습니다.', emptyHelp: '체류자격 코드와 짧은 키워드를 함께 입력해 보세요. 예: F-6 연장, E-7-4 소득',
      more: '관련 원문 더 보기', filter: '원문 범위', both: '사증·체류 전체', ai: 'AI 보조 안내 보기',
      info: '공식 안내 원문과 체류자격별 안내를 함께 검색할 수 있습니다. 각 결과의 기준일과 적용 범위를 확인하고, 신청 전 공식 기관에 문의하세요.',
      currentSource: '기준일 사증 2026.09.01 · 체류 2026.09.18', examples: '자주 찾는 질문', quickExtension: '체류기간 연장', quickAddress: '주소 변경', quickArc: '외국인등록증 재발급',
      short: '단기입국 경로', jobs: '직업·산업분류', office: '관할 출입국관서', agencies: '등록 민원대행기관', hospitals: '법무부지정 병원',
      pathways: '생활 경로 8종', reminders: '체류 기한 계산·알림', naturalization: '국적·귀화 안내', enforcement: '출입국 사범처리 예상',
      pendingInfo: '2026년 9월판 공식 안내 원문은 검색용으로 반영되어 있고, 내용 검토는 별도로 진행 중이에요. 구조화된 안내에는 각 근거의 기준일이 함께 표시됩니다.'
    },
    en: {
      search: 'Visa & stay search', forms: 'Forms', about: 'About', submit: 'Search', preparing: 'Preparing your search…', unavailable: 'Could not load the guides. Please reload the page.',
      title: 'A <em>clearer</em> life in Korea.', sub: 'Search a visa code or describe your situation.',
      placeholder: 'e.g. F-6 extension', pre: 'Before entry · Visa issuance', post: 'After entry · Managing your stay',
      preSub: 'Explore visa types, requirements and documents.', postSub: 'Check extensions, status changes and reporting procedures.',
      tools: 'Frequently used services', paperwork: 'Prepare documents', paperworkSub: 'Complete application and accommodation forms step by step.',
      reservation: 'Visit reservations', reservationSub: 'Find the steps and preparation for a HiKorea appointment.',
      manuals: 'Find official source text', manualsSub: 'Search the official visa and residence guidance for the passage you need.',
      visa: 'Visa guidance', stay: 'Stay guidance', original: 'Open original', sourceLabel: 'Official basis updated',
      language: 'Language', languageTitle: 'Choose language', languageSearch: 'Search languages', languageNone: 'No matching language.',
      disclaimer: 'Visable is not a government service. Information is for reference and has no legal effect. Confirm with HiKorea, 1345 or the relevant immigration office.',
      allTools: 'All services', theme: 'Theme', guide: 'Status guides', all: 'All results', sourceTab: 'Sources',
      manualTitle: 'Related official sources', sourceNote: 'Passages from the official guidance as of September 2026. The guidance above may cite a different edition.',
      review: 'Original excerpt · not reviewed', caveat: 'Check tables, images and applicable conditions on the original page. Excerpts do not establish individual requirements.',
      page: 'page', pages: 'passages', excerpt: 'Read page text', close: 'Close', loading: 'Loading official source text…',
      error: 'The source text could not be loaded. Try again or open the original PDFs.', retry: 'Try again',
      empty: 'No matching passages.', emptyHelp: 'The originals are in Korean. Try a code with a short Korean keyword, such as F-6 연장 or E-7-4 소득.',
      more: 'More source passages', filter: 'Source scope', both: 'Visa and stay', ai: 'Show AI assistance',
      info: 'Search the official source text alongside the status guides. Check the basis date and scope of each result, and confirm with an official authority before applying.',
      currentSource: 'Basis: visa 2026.09.01 · stay 2026.09.18', examples: 'Popular questions', quickExtension: 'Extend my stay', quickAddress: 'Report address change', quickArc: 'Reissue residence card',
      short: 'Short-stay entry routes', jobs: 'Occupation & industry codes', office: 'Immigration offices', agencies: 'Registered agencies', hospitals: 'Designated hospitals',
      pathways: 'Eight life pathways', reminders: 'Dates & reminders', naturalization: 'Nationality & naturalization', enforcement: 'Immigration enforcement',
      pendingInfo: 'The September 2026 official guidance is indexed for search; its content review is a separate step. Structured guidance shows the basis date of each source.'
    }
  };
  function t(key) { return copy[lang()][key]; }
  function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function icon(name) { return '<img class="cs-icon" src="assets/icons/civic/' + name + '.svg" alt="" aria-hidden="true">'; }
  var root = document.createElement('div'); root.id = 'civicLanding';
  var catalog, corpus, loadPromise, query = '', domain = '', activeTab = 'all', shown = 3, hits = [], sequence = 0;
  var panel, tabs, dialog, dialogReturn, queuedQuery = '', homeLanguage = '';

  /* ------------------------------------------------------------ language ---- */
  // One global language control for the civic surfaces (home nav + searched header). It renders the same
  // 15 languages index.html owns (LANGUAGE_OPTIONS), prefers native names, and applies a choice through the
  // existing `data-action="apply-language"` delegation so paradiso:language, ?lang=, zh-TW conversion and
  // Arabic RTL keep working exactly as before. Desktop: anchored popover; mobile: bottom sheet (same dialog).
  var LANG_FALLBACK = [['ko', '한국어', 'Korean', 'KO'], ['en', 'English', 'English', 'EN'], ['zh-CN', '简体中文', 'Chinese (Simplified)', '简'], ['zh-TW', '繁體中文', 'Chinese (Traditional)', '繁'], ['ja', '日本語', 'Japanese', '日'], ['vi', 'Tiếng Việt', 'Vietnamese', 'VI'], ['tl', 'Tagalog', 'Tagalog', 'TL'], ['id', 'Bahasa Indonesia', 'Indonesian', 'ID'], ['ru', 'Русский', 'Russian', 'RU'], ['fr', 'Français', 'French', 'FR'], ['es', 'Español', 'Spanish', 'ES'], ['ar', 'العربية', 'Arabic', 'ع'], ['de', 'Deutsch', 'German', 'DE'], ['tr', 'Türkçe', 'Turkish', 'TR'], ['uk', 'Українська', 'Ukrainian', 'UK']];
  function langOptions() {
    if (typeof LANGUAGE_OPTIONS !== 'undefined' && Array.isArray(LANGUAGE_OPTIONS)) return LANGUAGE_OPTIONS.map(function (o) { return { code: o.code, name: o.name, local: o.local, short: o.short, dir: o.dir || 'ltr', html: o.html || o.code }; });
    return LANG_FALLBACK.map(function (o) { return { code: o[0], name: o[1], local: o[2], short: o[3], dir: o[0] === 'ar' ? 'rtl' : 'ltr', html: o[0] }; });
  }
  function currentLangCode() {
    if (typeof selectedLocale !== 'undefined' && selectedLocale) return selectedLocale;
    return document.documentElement.lang || 'ko';
  }
  function langSelectable(code) { return typeof isLanguageSelectable === 'function' ? isLanguageSelectable(code) : true; }
  function langButton(cls) {
    var cur = langOptions().filter(function (o) { return o.code === currentLangCode(); })[0] || langOptions()[0];
    return '<button type="button" class="cs-lang ' + (cls || '') + '" data-cs-lang-open aria-haspopup="dialog" aria-expanded="false" aria-controls="csLangDialog" aria-label="' + esc(t('language')) + ': ' + esc(cur.name) + '"><span class="cs-lang-code" aria-hidden="true">' + esc(cur.short) + '</span><span class="cs-lang-name" lang="' + esc(cur.html) + '">' + esc(cur.name) + '</span></button>';
  }
  var langDialog = null, langOpener = null;
  function renderLangDialog(filter) {
    var cur = currentLangCode(); var f = String(filter || '').trim().toLowerCase();
    var list = langOptions().filter(function (o) { return !f || o.name.toLowerCase().indexOf(f) >= 0 || o.local.toLowerCase().indexOf(f) >= 0 || o.code.toLowerCase().indexOf(f) >= 0; });
    var body = list.length ? list.map(function (o) {
      var selectable = langSelectable(o.code);
      return '<li><button type="button" class="cs-lang-option" role="option" lang="' + esc(o.html) + '" dir="' + esc(o.dir) + '" aria-selected="' + (o.code === cur) + '"' + (selectable ? ' data-action="apply-language" data-lang="' + esc(o.code) + '"' : ' aria-disabled="true" disabled') + '><span class="cs-lang-native">' + esc(o.name) + '</span><span class="cs-lang-local" lang="en">' + esc(o.local) + '</span><span class="cs-lang-check" aria-hidden="true">' + (o.code === cur ? '✓' : '') + '</span></button></li>';
    }).join('') : '<li class="cs-lang-none">' + esc(t('languageNone')) + '</li>';
    langDialog.querySelector('.cs-lang-list').innerHTML = body;
  }
  function openLangDialog(opener) {
    if (!langDialog) {
      langDialog = document.createElement('dialog'); langDialog.id = 'csLangDialog'; langDialog.className = 'cs-lang-dialog'; langDialog.setAttribute('aria-labelledby', 'csLangTitle'); document.body.append(langDialog);
      langDialog.addEventListener('close', function () { document.querySelectorAll('[data-cs-lang-open]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); }); if (langOpener && langOpener.isConnected) langOpener.focus(); });
      langDialog.addEventListener('click', function (e) { if (e.target === langDialog) langDialog.close(); });
      // Escape closes the sheet even when a page-level key handler would otherwise swallow the dialog's cancel.
      langDialog.addEventListener('keydown', function (e) { if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); e.stopPropagation(); langDialog.close(); } });
    }
    langOpener = opener;
    langDialog.innerHTML = '<div class="cs-lang-head"><h2 id="csLangTitle">' + esc(t('languageTitle')) + '</h2><button type="button" class="cs-lang-close" data-cs-lang-close aria-label="' + esc(t('close')) + '">' + icon('x') + '</button></div>' +
      '<label class="cs-lang-search"><span class="cs-sr">' + esc(t('languageSearch')) + '</span><input type="search" autocomplete="off" placeholder="' + esc(t('languageSearch')) + '" data-cs-lang-filter></label>' +
      '<ul class="cs-lang-list" role="listbox" aria-labelledby="csLangTitle"></ul>';
    renderLangDialog('');
    langDialog.querySelector('[data-cs-lang-filter]').addEventListener('input', function (e) { renderLangDialog(e.target.value); });
    langDialog.querySelector('[data-cs-lang-close]').addEventListener('click', function () { langDialog.close(); });
    // Desktop: anchor under the opener like a popover; mobile (≤680px): the stylesheet turns it into a bottom sheet.
    langDialog.style.top = ''; langDialog.style.left = ''; langDialog.style.right = '';
    if (window.innerWidth > 680 && opener) { var r = opener.getBoundingClientRect(); langDialog.style.top = Math.round(r.bottom + 8) + 'px'; langDialog.style.right = Math.max(12, Math.round(window.innerWidth - r.right)) + 'px'; }
    opener && opener.setAttribute('aria-expanded', 'true');
    if (typeof langDialog.showModal === 'function') langDialog.showModal(); else langDialog.setAttribute('open', '');
    var sel = langDialog.querySelector('.cs-lang-option[aria-selected="true"]') || langDialog.querySelector('.cs-lang-option'); if (sel) sel.focus();
  }
  function refreshLangButtons() { document.querySelectorAll('.cs-lang').forEach(function (b) { var tmp = document.createElement('div'); tmp.innerHTML = langButton(b.classList.contains('cs-lang-searched') ? 'cs-lang-searched' : 'cs-lang-home'); b.replaceWith(tmp.firstChild); }); }
  function mountSearchedLangButton() {
    var header = document.querySelector('#hero .header-inner'); if (!header || header.querySelector('.cs-lang-searched')) return;
    var tmp = document.createElement('div'); tmp.innerHTML = langButton('cs-lang-searched'); header.append(tmp.firstChild);
  }

  function home() {
    homeLanguage = lang();
    root.innerHTML = '<header class="cs-nav"><a class="cs-brand" href="./" aria-label="Visable"><img src="assets/brand/visable-wordmark.svg" alt="Visable"></a>' +
      '<nav aria-label="' + t('about') + '"><button data-cs-focus>' + t('search') + '</button><a href="form-helper.html">' + t('forms') + '</a><a href="#civic-about">' + t('about') + '</a>' +
      '<span class="cs-languages">' + langButton('cs-lang-home') + '</span></nav></header>' +
      '<main class="cs-home"><section class="cs-hero"><h1>' + t('title') + '</h1><p>' + t('sub') + '</p>' +
      '<form id="civicSearchForm" role="search"><label class="cs-sr" for="civicQuery">' + t('search') + '</label><div class="cs-searchbar">' + icon('search') +
      '<input id="civicQuery" type="search" maxlength="300" autocomplete="off" placeholder="' + t('placeholder') + '"><button type="submit">' + t('submit') + '</button></div></form>' +
      '<div class="cs-examples" aria-label="' + t('examples') + '"><span class="cs-examples-label">' + t('examples') + '</span><button data-cs-query="체류기간 연장">' + icon('search') + t('quickExtension') + '</button><button data-cs-query="주소 변경 신고">' + icon('search') + t('quickAddress') + '</button><button data-cs-query="외국인등록증 재발급">' + icon('search') + t('quickArc') + '</button></div></section>' +
      '<section class="cs-routes"><button data-action="reveal-home-section" data-target="visaManualSection" data-journey-track="pre"><span class="cs-icon-circle">' + icon('globe') + '</span><span><strong>' + t('pre') + icon('chevron-right') + '</strong><small>' + t('preSub') + '</small></span></button>' +
      '<button data-action="reveal-home-section" data-target="visaManualSection" data-journey-track="in"><span class="cs-icon-circle">' + icon('user-round') + '</span><span><strong>' + t('post') + icon('chevron-right') + '</strong><small>' + t('postSub') + '</small></span></button></section>' +
      '<section class="cs-tools"><h2>' + t('tools') + '</h2><div class="cs-tool-grid">' +
      '<a href="form-helper.html"><span class="cs-icon-circle">' + icon('file-text') + '</span><span><strong>' + t('paperwork') + icon('chevron-right') + '</strong><small>' + t('paperworkSub') + '</small></span></a>' +
      '<button data-action="open-hikorea-guide"><span class="cs-icon-circle">' + icon('calendar-days') + '</span><span><strong>' + t('reservation') + icon('chevron-right') + '</strong><small>' + t('reservationSub') + '</small></span></button>' +
      '<button data-cs-focus data-cs-manual><span class="cs-icon-circle">' + icon('book-open') + '</span><span><strong>' + t('manuals') + icon('chevron-right') + '</strong><small>' + t('manualsSub') + '</small></span></button></div></section>' +
      '<div class="cs-source-strip"><span class="cs-source-strip-label">' + t('sourceLabel') + '</span><a href="docs/source-manuals/2026-09/visa_manual_260901.pdf" target="_blank" rel="noopener">' + icon('file-text') + '<span>' + t('visa') + ' · 2026.09.01</span>' + icon('external-link') + '</a>' +
      '<a href="docs/source-manuals/2026-09/stay_manual_260918.pdf" target="_blank" rel="noopener">' + icon('file-text') + '<span>' + t('stay') + ' · 2026.09.18</span>' + icon('external-link') + '</a></div>' +
      '<details class="cs-directory"><summary>' + t('allTools') + '</summary><div>' +
      [['open-short-stay','short'],['open-jobcode-modal','jobs'],['open-jurisdiction-modal','office'],['open-agent-finder','agencies'],['open-med-finder','hospitals']].map(function (item) { return '<button data-action="' + item[0] + '">' + t(item[1]) + '</button>'; }).join('') +
      '<button data-action="reveal-home-section" data-target="visaManualSection">' + t('pre') + ' / ' + t('post') + '</button><button data-action="reveal-home-section" data-target="pathwaySection">' + t('pathways') + '</button><button data-action="reveal-home-section" data-target="reminderSection">' + t('reminders') + '</button><a href="new-home.html">' + t('naturalization') + '</a><a href="enforcement.html">' + t('enforcement') + '</a><a href="ai.html">Waymaker AI</a><button data-action="toggle-theme">' + t('theme') + '</button></div></details>' +
      '<details id="civic-about" class="cs-about"><summary>' + t('about') + '</summary><p>' + t('info') + '</p><p>' + t('pendingInfo') + '</p><a href="https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&amp;BBS_GB_CD=BS10&amp;NTCCTT_SEQ=1062&amp;page=1" target="_blank" rel="noopener">HiKorea · ' + t('original') + '</a></details>' +
      '<footer class="cs-footer"><img src="assets/brand/visable-wordmark.svg" alt="Visable"><p>' + t('disclaimer') + '</p></footer></main>';
    root.querySelector('form').addEventListener('submit', function (event) { event.preventDefault(); searchFromHome(root.querySelector('input').value); });
    root.querySelector('a[href="#civic-about"]').addEventListener('click', function () { root.querySelector('#civic-about').open = true; });
    var footer = root.querySelector('.cs-footer');
    footer.before(root.querySelector('.cs-source-strip'));
    footer.after(root.querySelector('.cs-directory'), root.querySelector('.cs-about'));
  }
  function homeStatus(message) {
    var status = root.querySelector('.cs-home-status');
    if (!status) { status = document.createElement('p'); status.className = 'cs-home-status'; status.setAttribute('role', 'status'); root.querySelector('form').after(status); }
    status.textContent = message;
  }
  function searchFromHome(value) {
    value = String(value || '').trim();
    if (!value) { root.querySelector('input').focus(); return; }
    document.getElementById('q').value = value;
    document.body.classList.remove('landing', 'launching', 'searching');
    document.body.classList.add('searched');
    document.body.setAttribute('data-scene', 'searched');
    find(value);
    if (typeof dataReady !== 'undefined' && !dataReady) {
      queuedQuery = value; return;
    }
    queuedQuery = '';
    if (typeof executeSearch === 'function') executeSearch();
  }
  function load() {
    if (corpus) return Promise.resolve(corpus);
    if (loadPromise) return loadPromise;
    function fetchJson(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }); }
    loadPromise = fetchJson('data/manual-corpus/catalog.json').then(function (data) {
      catalog = data;
      return Promise.all(data.sources.map(function (source) { return fetchJson(source.sections); }));
    }).then(function (pages) {
      corpus = window.VisableManualSearch.prepare(catalog.sources, [].concat.apply([], pages)); return corpus;
    }).catch(function (error) { loadPromise = null; throw error; });
    return loadPromise;
  }
  function setTab(value) {
    activeTab = value;
    document.body.dataset.civicResults = value;
    tabs.querySelectorAll('button').forEach(function (button) { button.setAttribute('aria-pressed', button.dataset.csTab === value); });
    panel.hidden = value === 'guide';
  }
  function renderTabs() {
    tabs.innerHTML = ['all','guide','manual'].map(function (key) { return '<button data-cs-tab="' + key + '" aria-pressed="' + (activeTab === key) + '">' + t(key === 'manual' ? 'sourceTab' : key) + '</button>'; }).join('');
    tabs.setAttribute('aria-label', t('search'));
    setTab(activeTab);
  }
  function sourceLinks() {
    return '<a href="docs/source-manuals/2026-09/visa_manual_260901.pdf" target="_blank" rel="noopener">' + t('visa') + '</a> · <a href="docs/source-manuals/2026-09/stay_manual_260918.pdf" target="_blank" rel="noopener">' + t('stay') + '</a>';
  }
  function renderResults() {
    hits = window.VisableManualSearch.search(corpus, query, { domain: domain });
    panel.innerHTML = '<div class="cs-results-head"><div><h2>' + t('manualTitle') + '</h2><p>' + t('currentSource') + ' · ' + hits.length + ' ' + t('pages') + '</p></div><label><span class="cs-sr">' + t('filter') + '</span><select id="civicDomain"><option value="">' + t('both') + '</option><option value="visa_issuance">' + t('visa') + '</option><option value="stay">' + t('stay') + '</option></select></label></div>' +
      '<p class="cs-source-note">' + t('sourceNote') + '</p>' +
      (hits.length ? '<ol class="cs-manual-list">' + hits.slice(0, shown).map(function (hit, i) {
        var source = hit.source, page = hit.page;
        return '<li><div class="cs-result-meta">' + esc(lang() === 'en' ? source.title_en : source.title) + ' · ' + esc(source.date) + ' · ' + page.page + ' ' + t('page') + '</div>' +
          '<button class="cs-result-title" data-cs-page="' + i + '">' + esc(page.heading) + '</button><p>' + esc(window.VisableManualSearch.excerpt(page.text, query, corpus)) + '</p>' +
          '<div class="cs-result-actions"><span>' + t('review') + '</span><button data-cs-page="' + i + '">' + t('excerpt') + '</button><a href="' + esc(source.file) + '#page=' + page.page + '" target="_blank" rel="noopener">' + t('original') + icon('external-link') + '</a></div></li>';
      }).join('') + '</ol>' : '<div class="cs-empty"><h3>' + t('empty') + '</h3><p>' + t('emptyHelp') + '</p></div>') +
      (hits.length > shown ? '<button class="cs-more" data-cs-more>' + t('more') + '</button>' : '') + '<p class="cs-caveat">' + t('caveat') + '</p>';
    var select = panel.querySelector('select'); select.value = domain;
    select.addEventListener('change', function () { domain = select.value; shown = 3; renderResults(); });
  }
  function find(queryValue) {
    query = String(queryValue || '').trim(); shown = 3;
    var request = ++sequence;
    renderTabs();
    if (!query) { panel.innerHTML = ''; return; }
    panel.innerHTML = '<p class="cs-load" role="status">' + t('loading') + '</p>';
    load().then(function () { if (request === sequence) renderResults(); }).catch(function () {
      if (request !== sequence) return;
      panel.innerHTML = '<div class="cs-empty" role="status"><p>' + t('error') + '</p><button data-cs-retry>' + t('retry') + '</button><p>' + sourceLinks() + '</p></div>';
    });
  }
  function showHit(hit, origin) {
    dialogReturn = origin;
    dialog.innerHTML = '<div class="cs-dialog-head"><div><p>' + esc(hit.source.title) + ' · ' + esc(hit.source.date) + ' · ' + hit.page.page + ' ' + t('page') + '</p><h2 id="civicPageTitle">' + esc(hit.page.heading) + '</h2></div><button data-cs-close aria-label="' + t('close') + '">' + icon('x') + '</button></div><p class="cs-caveat">' + t('review') + '. ' + t('caveat') + '</p><pre>' + esc(hit.page.text) + '</pre><a class="cs-pdf-link" href="' + esc(hit.source.file) + '#page=' + hit.page.page + '" target="_blank" rel="noopener">' + t('original') + ' · ' + hit.page.page + ' ' + t('page') + icon('external-link') + '</a>';
    dialog.showModal();
  }
  function showPage(index, origin) { var hit = hits[index]; if (hit) showHit(hit, origin); }
  // Page-level evidence bridge for other modules (status guidance): open a manual page by source id + page number.
  function openPage(sourceId, pageNo, origin) {
    return load().then(function () {
      var source = (catalog.sources || []).filter(function (s) { return s.id === sourceId; })[0];
      var row = corpus.rows.filter(function (r) { return r.source && r.source.id === sourceId && r.page.page === Number(pageNo); })[0];
      if (source && row) showHit({ source: source, page: row.page }, origin);
    }).catch(function () { /* the PDF link beside the button remains available */ });
  }
  window.VisableCivicSearch = { load: load, openPage: openPage };
  function init() {
    document.body.classList.add('civic-refresh');
    document.body.insertBefore(root, document.getElementById('hero'));
    home();
    var results = document.getElementById('mainContent');
    results.prepend(document.getElementById('visaManualSection'));
    tabs = document.createElement('div'); tabs.className = 'cs-tabs'; tabs.id = 'civicResultTabs'; tabs.setAttribute('role', 'group');
    panel = document.createElement('section'); panel.id = 'civicManualResults'; panel.className = 'cs-manual-results'; panel.setAttribute('aria-label', t('manuals'));
    results.prepend(panel); results.prepend(tabs);
    dialog = document.createElement('dialog'); dialog.id = 'civicPageDialog'; dialog.setAttribute('aria-labelledby', 'civicPageTitle'); document.body.append(dialog);
    dialog.addEventListener('close', function () { if (dialogReturn && dialogReturn.isConnected) dialogReturn.focus(); });
    mountSearchedLangButton();
    document.addEventListener('click', function (event) {
      var target = event.target.closest('button'); if (!target) return;
      if (target.hasAttribute('data-cs-lang-open')) { openLangDialog(target); return; }
      if (target.hasAttribute('data-cs-focus')) { if (target.hasAttribute('data-cs-manual')) activeTab = 'manual'; root.querySelector('input').focus(); root.querySelector('input').scrollIntoView({ block: 'center', behavior: 'smooth' }); }
      if (target.dataset.csQuery) searchFromHome(target.dataset.csQuery);
      if (target.dataset.csTab) setTab(target.dataset.csTab);
      if (target.hasAttribute('data-cs-page')) showPage(Number(target.dataset.csPage), target);
      if (target.hasAttribute('data-cs-close')) dialog.close();
      if (target.hasAttribute('data-cs-more')) { shown += 12; renderResults(); }
      if (target.hasAttribute('data-cs-retry')) find(query);
    });
    document.addEventListener('paradiso:results-rendered', function (event) { find(event.detail.query); });
    document.addEventListener('paradiso:data-ready', function () { if (queuedQuery) searchFromHome(queuedQuery); });
    document.addEventListener('paradiso:data-failed', function () { if (queuedQuery) homeStatus(t('unavailable')); });
    document.addEventListener('paradiso:landing-reset', function () {
      ++sequence; query = ''; queuedQuery = ''; activeTab = 'all'; domain = ''; panel.innerHTML = ''; tabs.innerHTML = '';
      var url = new URL(location.href); url.searchParams.delete('q'); history.replaceState(null, '', url);
      home();
    });
    window.addEventListener('paradiso-language-applied', function () {
      if (langDialog && langDialog.open) langDialog.close();
      refreshLangButtons();
      if (lang() === homeLanguage) return;
      var draft = root.querySelector('input') ? root.querySelector('input').value : '';
      var directoryOpen = root.querySelector('.cs-directory') && root.querySelector('.cs-directory').open;
      var aboutOpen = root.querySelector('.cs-about') && root.querySelector('.cs-about').open;
      home();
      if (draft && root.querySelector('input')) root.querySelector('input').value = draft;
      if (directoryOpen) root.querySelector('.cs-directory').open = true;
      if (aboutOpen) root.querySelector('.cs-about').open = true;
      if (query) find(query);
    });
    if (document.body.classList.contains('searched')) find(document.getElementById('q').value);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
