(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  /* ------------------------------------------------------------------ copy ---
   * Bootstrap copy for the civic landing. Korean and English live here so the
   * static shell in index.html (generated from this builder) and the very first
   * render never wait for a network fetch. The same strings — and the twelve
   * other locales — live in data/i18n/<locale>.json under the `civic` object;
   * t() prefers the loaded pack and falls back to this table.
   * scripts/check_landing_shell.mjs asserts ko/en here == ko/en packs. */
  var copy = {
    ko: {
      search: '비자·체류 검색', forms: '서류 작성', about: '이용 안내', submit: '검색', preparing: '검색을 준비하고 있습니다.', unavailable: '안내 데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요.',
      title: '답이 <em>보이는</em> 한국 생활.', sub: '비자 코드, 절차 이름, 지금 상황을 그대로 입력하세요.',
      placeholder: '예: F-6 연장, 이사했어요', pre: '입국 전 · 사증 발급', post: '입국 후 · 체류 관리',
      browse: '목적별로 둘러보기', journeyClose: '닫기',
      coreTools: '바로 쓰는 도구',
      paperwork: '필수 서류 작성', paperworkSub: '통합신청서 등 공식 서식을 단계별로 채우고 PDF로 내려받아요.',
      waymaker: 'Waymaker', waymakerSub: '복잡한 상황을 설명하면 필요한 절차와 근거를 단계별로 정리하는 AI 안내예요.',
      newHome: 'New Home', newHomeSub: '국적·귀화와 한국 정착 준비를 한곳에서 안내해요.',
      reservation: '방문예약 안내', reservationSub: '하이코리아 방문예약 방법과 준비사항을 확인하세요.',
      manuals: '공식 원문 찾기', manualsSub: '사증발급·외국인체류 공식 안내 원문에서 필요한 구절을 찾아보세요.',
      reader: '매뉴얼 원문 읽기', readerSub: '사증발급·외국인체류 매뉴얼 원문을 체류자격·업무별로 나눠 읽어요.', readerOpen: '이 자격·업무의 원문 읽기',
      officeSub: '내 주소지를 담당하는 출입국·외국인관서를 확인하세요.',
      visa: '사증 안내', stay: '체류 안내', original: '원문 보기', sourceLabel: '체류자격별 매뉴얼',
      language: '언어', languageTitle: '언어 선택', languageSearch: '언어 검색', languageNone: '일치하는 언어가 없어요.',
      disclaimer: 'Visable은 공식 정부 서비스가 아닙니다. 제공 정보는 참고용이며 법적 효력이 없습니다. 최종 판단은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요.',
      allTools: '전체 도구 보기', theme: '화면 테마', easyModeEasy: '쉬운 안내', guide: '체류자격 안내', all: '전체', sourceTab: '원문',
      manualTitle: '관련 공식 원문', sourceNote: '2026년 9월 기준 공식 안내 원문에서 찾은 구절이에요. 위 안내와 판본이 다를 수 있어요.',
      review: '원문 발췌 · 검토 전', caveat: '표·이미지의 내용과 적용 조건은 원문 페이지에서 확인하세요. 발췌문은 개별 요건을 확정하는 안내가 아닙니다.',
      page: '쪽', pages: '건', excerpt: '본문 펼치기', close: '닫기', loading: '공식 원문을 불러오는 중입니다.',
      error: '원문을 불러오지 못했습니다. 다시 시도하거나 원문 PDF를 열어 확인하세요.', retry: '다시 시도',
      empty: '일치하는 원문이 없습니다.', emptyHelp: '체류자격 코드와 짧은 키워드를 함께 입력해 보세요. 예: F-6 연장, E-7-4 소득',
      more: '관련 원문 더 보기', rawTitle: '관련 원문', filter: '원문 범위', both: '사증·체류 전체', ai: 'AI 보조 안내 보기',
      info: '공식 안내 원문과 체류자격별 안내를 함께 검색할 수 있습니다. 각 결과의 기준일과 적용 범위를 확인하고, 신청 전 공식 기관에 문의하세요.',
      currentSource: '기준일 사증 2026.09.01 · 체류 2026.09.18', examples: '이렇게 검색해 보세요',
      exF6Extension: 'F-6 체류기간 연장', exRegistration: '외국인등록', exAddress: '주소 변경 신고', exE7Workplace: 'E-7 근무처 변경', exForms: '통합신청서 작성',
      clear: '검색어 지우기', suggestLabel: '검색 제안', suggestCount: '제안 {n}개가 있어요. 위아래 화살표로 고르고 Enter로 여세요.',
      suggestEmpty: '맞는 제안이 없어요. Enter를 누르면 전체 검색 결과를 보여 드려요.', suggestFoot: 'Enter 전체 검색 · Esc 닫기',
      suggestLimited: '제안 이름은 한국어·영어 공식 용어로 표시돼요.',
      kindStatus: '체류자격', kindSubstatus: '세부 자격', kindProcedure: '절차', kindTool: '도구',
      subOf: '{parent}의 세부 자격', statusSubs: '세부 자격 {n}개', statusKind: '체류자격 개요',
      domainVisa: '입국 전 · 사증', domainStay: '입국 후 · 체류',
      procAnyStatus: '체류자격과 관계없이 같은 절차', procNeedsStatus: '체류자격 코드를 함께 입력하면 더 정확해요',
      stateNotApplicable: '이 자격에는 해당 없음', stateRestricted: '원칙적으로 제한 · 예외 확인 필요',
      lifecycleLegacy: '기존 체류자만', lifecycleAbolished: '폐지된 자격', lifecycleUnverified: '확인 필요',
      unknownCode: '{code}는 2026년 9월 공식 안내에서 찾을 수 없는 코드예요. 오타가 없는지 확인하거나 상위 코드를 살펴보세요.',
      notACode: '{code}는 공식 안내에 있는 체류자격 코드가 아니에요. 코드 대신 지금 상황을 입력해 보세요.',
      waymakerAsk: '상황을 설명하면 절차와 근거를 단계별로 정리해요',
      short: '단기입국 경로', jobs: '직업·산업분류', office: '관할 출입국관서', agencies: '등록 민원대행기관', hospitals: '법무부지정 병원',
      pathways: '생활 경로 8종', reminders: '체류 기한 계산·알림', naturalization: '국적·귀화 안내', enforcement: '출입국 사범처리 예상',
      pendingInfo: '2026년 9월판 공식 안내 원문은 검색용으로 반영되어 있고, 내용 검토는 별도로 진행 중이에요. 구조화된 안내에는 각 근거의 기준일이 함께 표시됩니다.',
      bootFailed: '화면을 준비하지 못했어요. 새로고침하면 대부분 해결돼요.', reload: '새로고침',
      bootLinks: '그래도 안 되면 공식 원문(PDF)과 다른 도구를 바로 열 수 있어요.',
      noscript: 'JavaScript가 꺼져 있으면 검색과 안내를 사용할 수 없어요. 공식 원문 PDF는 아래 링크에서 바로 열 수 있어요.'
    },
    en: {
      search: 'Visa & stay search', forms: 'Forms', about: 'About', submit: 'Search', preparing: 'Preparing your search…', unavailable: 'Could not load the guides. Please reload the page.',
      title: 'Life in Korea, made <img class="cs-hero-wordmark" src="assets/brand/visable-wordmark-green.svg" alt="VISABLE">', sub: 'Type a visa code, a procedure, or just describe your situation.',
      placeholder: 'e.g. F-6 extension, I moved', pre: 'Before entry · Visa issuance', post: 'After entry · Managing your stay',
      browse: 'Browse by purpose', journeyClose: 'Close',
      coreTools: 'Tools you can use now',
      paperwork: 'Prepare documents', paperworkSub: 'Fill official forms such as the integrated application step by step and download a PDF.',
      waymaker: 'Waymaker', waymakerSub: 'Describe a complex situation and get the steps and sources laid out in order, with AI assistance.',
      newHome: 'New Home', newHomeSub: 'Nationality, naturalization and settling in Korea, guided in one place.',
      reservation: 'Visit reservations', reservationSub: 'Find the steps and preparation for a HiKorea appointment.',
      manuals: 'Find official source text', manualsSub: 'Search the official visa and residence guidance for the passage you need.',
      reader: 'Read the manuals', readerSub: 'Read the visa and residence manuals by status and procedure (Korean original).', readerOpen: 'Read this section of the manual',
      officeSub: 'Find the immigration office responsible for your address.',
      visa: 'Visa guidance', stay: 'Stay guidance', original: 'Open original', sourceLabel: 'Official basis updated',
      language: 'Language', languageTitle: 'Choose language', languageSearch: 'Search languages', languageNone: 'No matching language.',
      disclaimer: 'Visable is not a government service. Information is for reference and has no legal effect. Confirm with HiKorea, 1345 or the relevant immigration office.',
      allTools: 'All services', theme: 'Theme', easyModeEasy: 'Easy Mode', guide: 'Status guides', all: 'All results', sourceTab: 'Sources',
      manualTitle: 'Related official sources', sourceNote: 'Passages from the official guidance as of September 2026. The guidance above may cite a different edition.',
      review: 'Original excerpt · not reviewed', caveat: 'Check tables, images and applicable conditions on the original page. Excerpts do not establish individual requirements.',
      page: 'page', pages: 'passages', excerpt: 'Read page text', close: 'Close', loading: 'Loading official source text…',
      error: 'The source text could not be loaded. Try again or open the original PDFs.', retry: 'Try again',
      empty: 'No matching passages.', emptyHelp: 'The originals are in Korean. Try a code with a short Korean keyword, such as F-6 연장 or E-7-4 소득.',
      more: 'More source passages', rawTitle: 'Related source passages', filter: 'Source scope', both: 'Visa and stay', ai: 'Show AI assistance',
      info: 'Search the official source text alongside the status guides. Check the basis date and scope of each result, and confirm with an official authority before applying.',
      currentSource: 'Basis: visa 2026.09.01 · stay 2026.09.18', examples: 'Try searching for',
      exF6Extension: 'F-6 extension of stay', exRegistration: 'Foreign resident registration', exAddress: 'Report an address change', exE7Workplace: 'E-7 workplace change', exForms: 'Fill in the integrated application',
      clear: 'Clear search', suggestLabel: 'Search suggestions', suggestCount: '{n} suggestions. Use the up and down arrows to choose, and Enter to open.',
      suggestEmpty: 'No matching suggestions. Press Enter to see all search results.', suggestFoot: 'Enter to search · Esc to close',
      suggestLimited: 'Suggestions use the official Korean and English terms.',
      kindStatus: 'Status', kindSubstatus: 'Subcode', kindProcedure: 'Procedure', kindTool: 'Tool',
      subOf: 'Subcode of {parent}', statusSubs: '{n} subcodes', statusKind: 'Status overview',
      domainVisa: 'Before entry · Visa', domainStay: 'After entry · Stay',
      procAnyStatus: 'Same procedure for every status', procNeedsStatus: 'Add your status code for a more precise answer',
      stateNotApplicable: 'Does not apply to this status', stateRestricted: 'Generally restricted · check the exceptions',
      lifecycleLegacy: 'Existing holders only', lifecycleAbolished: 'Abolished status', lifecycleUnverified: 'Needs checking',
      unknownCode: '{code} is not a code in the September 2026 official guidance. Check for a typo, or look at the parent code.',
      notACode: '{code} is not a status code in the official guidance. Try describing your situation instead.',
      waymakerAsk: 'Describe your situation and get the steps and sources in order',
      short: 'Short-stay entry routes', jobs: 'Occupation & industry codes', office: 'Immigration offices', agencies: 'Registered agencies', hospitals: 'Designated hospitals',
      pathways: 'Eight life pathways', reminders: 'Dates & reminders', naturalization: 'Nationality & naturalization', enforcement: 'Immigration enforcement',
      pendingInfo: 'The September 2026 official guidance is indexed for search; its content review is a separate step. Structured guidance shows the basis date of each source.',
      bootFailed: 'The page could not finish loading. Reloading usually fixes it.', reload: 'Reload',
      bootLinks: 'If it still fails, the official source PDFs and the other tools open directly.',
      noscript: 'Search and guidance need JavaScript. The official source PDFs open from the links below.'
    }
  };

  /* -------------------------------------------------------------- locale ----
   * uiLang(): the selected product locale (content code — zh-TW renders zh-CN).
   * lang(): the bilingual data language (en or ko) used for source titles etc. */
  function contentLocale(code) { return code === 'zh-TW' ? 'zh-CN' : code; }
  function uiLang() {
    if (typeof selectedLocale !== 'undefined' && selectedLocale) return contentLocale(selectedLocale);
    return contentLocale(document.documentElement.lang || 'ko');
  }
  function lang() { return uiLang() === 'ko' ? 'ko' : 'en'; }
  function packFor(loc) {
    if (typeof UI_TRANSLATIONS === 'undefined' || !UI_TRANSLATIONS) return null;
    var pack = UI_TRANSLATIONS[loc];
    return pack && pack.civic && typeof pack.civic === 'object' ? pack.civic : null;
  }
  function t(key) {
    var loc = uiLang();
    var pack = packFor(loc);
    if (pack && typeof pack[key] === 'string') return pack[key];
    if (loc !== 'ko' && loc !== 'en') { var ko = packFor('ko'); if (ko && typeof ko[key] === 'string') return ko[key]; }
    return (copy[lang()] || copy.ko)[key];
  }
  // The civic shell hides the old header controls, so the global Easy Mode toggle
  // is offered here (same data-action and storage key as index.html).
  function easyModeOn() { try { return localStorage.getItem('paradiso:easyMode') === '1'; } catch (e) { return false; } }
  function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function icon(name) { return '<img class="cs-icon" src="assets/icons/civic/' + name + '.svg" alt="" aria-hidden="true">'; }
  var VISA_PDF = 'docs/source-manuals/2026-09/visa_manual_260901.pdf', STAY_PDF = 'docs/source-manuals/2026-09/stay_manual_260918.pdf';
  var root = null;
  var catalog, corpus, loadPromise, query = '', domain = '', shown = 3, hits = [], sequence = 0, intent = null, rawFirst = false;
  var panel, raw, dialog, dialogReturn, queuedQuery = '', homeLanguage = '';

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
  function langButton(cls, code, T) {
    T = T || t;
    var want = code || currentLangCode();
    var cur = langOptions().filter(function (o) { return o.code === want; })[0] || langOptions()[0];
    return '<button type="button" class="cs-lang ' + (cls || '') + '" data-cs-lang-open aria-haspopup="dialog" aria-expanded="false" aria-controls="csLangDialog" aria-label="' + esc(T('language')) + ': ' + esc(cur.name) + '"><span class="cs-lang-code" aria-hidden="true">' + esc(cur.short) + '</span><span class="cs-lang-name" lang="' + esc(cur.html) + '">' + esc(cur.name) + '</span></button>';
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

  /* ------------------------------------------------------------ home ----
   * homeHtml(T, ctx) is a pure builder: it is what the browser renders and
   * what scripts/build_landing_shell.mjs writes into index.html as the static
   * first-paint shell. Keep it free of DOM access.
   *
   * Search is the one primary action. The page does not ask "before or after
   * entering Korea?" first: the suggestions under the field say which side a
   * procedure belongs to, and the purpose pickers that used to sit behind two
   * large journey cards stay reachable from the directory ("목적별로 둘러보기"). */
  function toolLink(T, href, iconName, title, sub, extra) {
    return '<a class="cs-tool" href="' + href + '"' + (extra || '') + '><span class="cs-icon-circle">' + icon(iconName) + '</span><span class="cs-tool-body"><strong>' + esc(T(title)) + icon('chevron-right') + '</strong><small>' + esc(T(sub)) + '</small></span></a>';
  }
  function toolButton(T, attrs, iconName, title, sub) {
    return '<button type="button" class="cs-tool" ' + attrs + '><span class="cs-icon-circle">' + icon(iconName) + '</span><span class="cs-tool-body"><strong>' + esc(T(title)) + icon('chevron-right') + '</strong><small>' + esc(T(sub)) + '</small></span></button>';
  }
  // Editorial examples, not usage data: each query is one the search resolves to
  // a status × procedure or a procedure (scripts/check_search_suggest.mjs).
  var EXAMPLES = [['F-6 체류기간 연장', 'exF6Extension'], ['외국인등록', 'exRegistration'], ['주소 변경 신고', 'exAddress'], ['E-7 근무처 변경', 'exE7Workplace']];
  function homeHtml(T, ctx) {
    ctx = ctx || {};
    var langHtml = ctx.langButton || langButton('cs-lang-home', ctx.langCode, T);
    var sourceLinksHtml = '<a href="' + VISA_PDF + '" target="_blank" rel="noopener">' + esc(T('visa')) + ' PDF</a> · <a href="' + STAY_PDF + '" target="_blank" rel="noopener">' + esc(T('stay')) + ' PDF</a>';
    return '<header class="cs-nav"><a class="cs-brand" href="./" aria-label="Visable"><img src="assets/brand/visable-wordmark.svg" alt="Visable"></a>' +
      '<nav aria-label="' + esc(T('about')) + '"><button type="button" data-cs-focus>' + esc(T('search')) + '</button><a href="form-helper.html">' + esc(T('forms')) + '</a><a href="#civic-about">' + esc(T('about')) + '</a>' +
      '<span class="cs-languages">' + langHtml + '</span></nav></header>' +
      '<main class="cs-home"><section class="cs-hero"><h1>' + T('title') + '</h1><p id="civicSearchSub">' + esc(T('sub')) + '</p>' +
      '<form id="civicSearchForm" role="search" novalidate><label class="cs-sr" for="civicQuery">' + esc(T('search')) + '</label><div class="cs-searchbar">' + icon('search') +
      '<input id="civicQuery" type="search" maxlength="300" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="civicSuggest" aria-describedby="civicSearchSub" placeholder="' + esc(T('placeholder')) + '">' +
      '<button type="button" class="cs-clear" data-cs-clear aria-label="' + esc(T('clear')) + '" hidden>' + icon('x') + '</button><button type="submit" class="cs-submit"><span class="cs-submit-label">' + esc(T('submit')) + '</span>' + icon('search') + '</button></div>' +
      '<button type="button" class="cs-sheet-close" data-cs-sheet-close>' + esc(T('close')) + '</button>' +
      '<div class="cs-suggest" hidden><p class="cs-suggest-note" hidden></p><ul id="civicSuggest" class="cs-suggest-list" role="listbox" aria-label="' + esc(T('suggestLabel')) + '"></ul><p class="cs-suggest-foot"></p></div>' +
      '<p class="cs-sr" role="status" aria-live="polite" data-cs-suggest-status></p></form>' +
      '<div class="cs-boot-failed" role="alert"><span>' + esc(T('bootFailed')) + '</span> <button type="button" class="cs-boot-reload" onclick="location.reload()">' + esc(T('reload')) + '</button><span class="cs-boot-links">' + esc(T('bootLinks')) + ' ' + sourceLinksHtml + ' · <a href="form-helper.html">' + esc(T('paperwork')) + '</a> · <a href="ai.html">Waymaker</a> · <a href="new-home.html">New Home</a></span></div>' +
      '<noscript><p class="cs-noscript">' + esc(T('noscript')) + ' ' + sourceLinksHtml + '</p></noscript>' +
      '<div class="cs-examples" role="group" aria-labelledby="csExamplesLabel"><span class="cs-examples-label" id="csExamplesLabel">' + esc(T('examples')) + '</span>' +
      EXAMPLES.map(function (ex) { return '<button type="button" data-cs-query="' + esc(ex[0]) + '">' + icon('search') + '<span>' + esc(T(ex[1])) + '</span></button>'; }).join('') +
      '<a class="cs-example-link" href="form-helper.html">' + icon('file-text') + '<span>' + esc(T('exForms')) + '</span></a></div>' +
      '<p class="cs-basis">' + esc(T('currentSource')) + '</p></section>' +
      '<section class="cs-tools cs-tools-core" aria-labelledby="csCoreTitle"><h2 id="csCoreTitle">' + esc(T('coreTools')) + '</h2><div class="cs-tool-grid">' +
      toolLink(T, 'form-helper.html', 'file-text', 'paperwork', 'paperworkSub', ' data-cs-tool="forms"') +
      toolLink(T, 'ai.html', 'compass', 'waymaker', 'waymakerSub', ' data-cs-tool="waymaker"') +
      toolLink(T, 'new-home.html', 'house', 'newHome', 'newHomeSub', ' data-cs-tool="newhome"') +
      toolButton(T, 'data-action="open-hikorea-guide" data-cs-tool="reservation"', 'calendar-days', 'reservation', 'reservationSub') +
      toolButton(T, 'data-cs-focus data-cs-manual data-cs-tool="manuals"', 'search', 'manuals', 'manualsSub') +
      toolLink(T, 'manual.html', 'book-open', 'reader', 'readerSub', ' data-cs-tool="reader"') +
      toolButton(T, 'data-action="open-jurisdiction-modal" data-cs-tool="office"', 'landmark', 'office', 'officeSub') + '</div></section>' +
      '<div class="cs-source-strip"><span class="cs-source-strip-label">' + esc(T('sourceLabel')) + '</span><a href="' + VISA_PDF + '" target="_blank" rel="noopener">' + icon('file-text') + '<span>' + esc(T('visa')) + ' · 2026.09.01</span>' + icon('external-link') + '</a>' +
      '<a href="' + STAY_PDF + '" target="_blank" rel="noopener">' + icon('file-text') + '<span>' + esc(T('stay')) + ' · 2026.09.18</span>' + icon('external-link') + '</a></div>' +
      '<footer class="cs-footer"><img src="assets/brand/visable-wordmark.svg" alt="Visable"><p>' + esc(T('disclaimer')) + '</p></footer>' +
      '<details class="cs-directory"><summary>' + esc(T('allTools')) + '</summary><div>' +
      '<button type="button" data-action="reveal-home-section" data-target="visaManualSection" aria-controls="civicBrowsePanel" aria-expanded="false">' + esc(T('browse')) + '</button>' +
      [['open-short-stay', 'short'], ['open-jobcode-modal', 'jobs'], ['open-jurisdiction-modal', 'office'], ['open-agent-finder', 'agencies'], ['open-med-finder', 'hospitals']].map(function (item) { return '<button type="button" data-action="' + item[0] + '">' + esc(T(item[1])) + '</button>'; }).join('') +
      '<button type="button" data-action="reveal-home-section" data-target="pathwaySection">' + esc(T('pathways')) + '</button><button type="button" data-action="reveal-home-section" data-target="reminderSection">' + esc(T('reminders')) + '</button><a href="form-helper.html">' + esc(T('paperwork')) + '</a><a href="manual.html">' + esc(T('reader')) + '</a><a href="new-home.html">' + esc(T('naturalization')) + '</a><a href="enforcement.html">' + esc(T('enforcement')) + '</a><a href="ai.html">Waymaker</a><button type="button" data-action="toggle-theme">' + esc(T('theme')) + '</button><button type="button" data-action="toggle-easy-mode" aria-pressed="' + (easyModeOn() ? 'true' : 'false') + '">' + esc(T('easyModeEasy')) + '</button></div></details>' +
      '<section id="civicBrowsePanel" class="cs-browse" aria-labelledby="csBrowseTitle" hidden><div class="cs-browse-head"><h2 id="csBrowseTitle">' + esc(T('browse')) + '</h2>' +
      '<div class="cs-browse-tabs" role="group" aria-labelledby="csBrowseTitle"><button type="button" data-cs-journey="pre" aria-pressed="false">' + esc(T('pre')) + '</button><button type="button" data-cs-journey="post" aria-pressed="false">' + esc(T('post')) + '</button></div>' +
      '<button type="button" class="cs-journey-close" data-cs-journey="close" aria-label="' + esc(T('journeyClose')) + '">' + icon('x') + '</button></div><div class="cs-journey-slot"></div></section>' +
      '<details id="civic-about" class="cs-about"><summary>' + esc(T('about')) + '</summary><p>' + esc(T('info')) + '</p><p>' + esc(T('pendingInfo')) + '</p><a href="https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&amp;BBS_GB_CD=BS10&amp;NTCCTT_SEQ=1062&amp;page=1" target="_blank" rel="noopener">HiKorea · ' + esc(T('original')) + '</a></details></main>';
  }

  /* ------------------------------------------------------------ browse ----
   * The purpose pickers (index.html startPreEntryTrack() / startInKoreaTrack()
   * into #visaManualDynamic) are a secondary, on-demand browse path:
   *   CLOSED | PRE_ENTRY_OPEN | POST_ENTRY_OPEN
   * The directory entry and index.html's `reveal-home-section` handler open it
   * through window.VisableCivicSearch.journey; the two tabs inside the panel
   * switch tracks. This layer owns only the panel, its ARIA state and where the
   * legacy #visaManualSection node lives. */
  var TRACK_STATE = { pre: 'PRE_ENTRY_OPEN', post: 'POST_ENTRY_OPEN' };
  var journey = { state: 'CLOSED', opener: null };
  // A home() re-render (language change, landing reset) replaces the panel, so the
  // legacy node is held here and re-attached rather than looked up in a DOM it left.
  var journeySection = null;
  function journeyTrack(state) { return state === 'PRE_ENTRY_OPEN' ? 'pre' : state === 'POST_ENTRY_OPEN' ? 'post' : null; }
  function journeyPanel() { return root ? root.querySelector('#civicBrowsePanel') : null; }
  function journeyTab(track) { return root ? root.querySelector('.cs-browse-tabs [data-cs-journey="' + track + '"]') : null; }
  function browseEntry() { return root ? root.querySelector('.cs-directory [data-target="visaManualSection"]') : null; }
  function mountJourneySection() {
    var slot = root && root.querySelector('.cs-journey-slot');
    if (!journeySection || !journeySection.isConnected) journeySection = document.getElementById('visaManualSection') || journeySection;
    if (slot && journeySection && journeySection.parentNode !== slot) slot.appendChild(journeySection);
  }
  function renderTrackContent(track) {
    var dynamicEl = document.getElementById('visaManualDynamic');
    if (track === 'pre' && typeof startPreEntryTrack === 'function') startPreEntryTrack();
    else if (track === 'post' && typeof startInKoreaTrack === 'function') startInKoreaTrack();
    else if (dynamicEl) dynamicEl.innerHTML = '<p class="cs-home-status" role="status">' + esc(t('preparing')) + '</p>';
  }
  function prefersReducedMotion() { try { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } }
  function setJourney(next, opts) {
    opts = opts || {};
    if (next !== 'CLOSED' && next !== 'PRE_ENTRY_OPEN' && next !== 'POST_ENTRY_OPEN') next = 'CLOSED';
    var previous = journey.state;
    journey.state = next;
    var track = journeyTrack(next);
    var panel = journeyPanel();
    ['pre', 'post'].forEach(function (k) { var b = journeyTab(k); if (b) b.setAttribute('aria-pressed', k === track ? 'true' : 'false'); });
    var entry = browseEntry(); if (entry) entry.setAttribute('aria-expanded', track ? 'true' : 'false');
    if (root) root.setAttribute('data-cs-journey-state', next);
    if (!panel) return;
    if (!track) {
      panel.hidden = true; panel.removeAttribute('data-track');
      if (opts.focus !== false && previous !== 'CLOSED') { var back = journey.opener && journey.opener.isConnected ? journey.opener : entry; if (back) back.focus(); }
      return;
    }
    mountJourneySection();
    panel.hidden = false; panel.setAttribute('data-track', track);
    // Content renders only when the track changes: re-opening the same track keeps the picker the user was in.
    if (previous !== next || opts.rerender) renderTrackContent(track);
    if (opts.scroll !== false && previous === 'CLOSED' && typeof panel.scrollIntoView === 'function') panel.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
  }
  function openJourney(track) {
    if (!TRACK_STATE[track]) return;
    if (journey.state === 'CLOSED') journey.opener = document.activeElement && document.activeElement !== document.body ? document.activeElement : browseEntry();
    setJourney(TRACK_STATE[track]);
  }
  function toggleJourney(track) {
    var target = TRACK_STATE[track];
    if (!target) return;
    if (journey.state === target) setJourney('CLOSED'); else openJourney(track);
  }
  function closeJourney() { setJourney('CLOSED'); }

  /* --------------------------------------------------------- suggestions ----
   * WAI-ARIA combobox (list autocomplete) on #civicQuery. Suggestions are local
   * and deterministic (assets/js/search-suggest.js over the derived index): no
   * request leaves the browser while typing, and nothing typed is stored. */
  var SUGGEST_INDEX_URL = 'data/search-suggest-index.json';
  var suggestIndex = null, suggestLoading = null, suggestFailed = false;
  var sugg = { items: [], active: -1, frame: 0, announce: 0, composing: false, lastRender: 0, renderMs: 0 };
  function loadSuggestIndex() {
    if (suggestIndex) return Promise.resolve(suggestIndex);
    if (suggestLoading) return suggestLoading;
    suggestLoading = fetch(SUGGEST_INDEX_URL).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }).then(function (data) {
      suggestIndex = data; suggestFailed = false;
      if (window.VisableSearchSuggest) window.VisableSearchSuggest.hydrate(suggestIndex);
      return suggestIndex;
    }).catch(function (error) { suggestLoading = null; suggestFailed = true; throw error; });
    return suggestLoading;
  }
  function el(sel) { return root ? root.querySelector(sel) : null; }
  function fmt(text, vars) { return String(text || '').replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function narrow() { try { return window.matchMedia('(max-width: 680px)').matches; } catch (e) { return false; } }
  function highlight(label, query) {
    var q = String(query || '').trim(), i = q ? label.toLowerCase().indexOf(q.toLowerCase()) : -1;
    if (i < 0) return esc(label);
    return esc(label.slice(0, i)) + '<mark>' + esc(label.slice(i, i + q.length)) + '</mark>' + esc(label.slice(i + q.length));
  }
  var KIND_KEY = { status: 'kindStatus', substatus: 'kindSubstatus', status_procedure: 'kindProcedure', procedure: 'kindProcedure', tool: 'kindTool' };
  var SAFE_TOOL_HREF = /^(form-helper|ai|new-home|manual)\.html$/;
  var SAFE_TOOL_ACTION = { 'open-hikorea-guide': true, 'open-jurisdiction-modal': true };
  function optionHtml(item, i, query) {
    var label = item.kind === 'tool' ? t(item.labelKey) : item.label;
    var labelLang = item.kind === 'tool' ? '' : ' lang="' + (item.labelLang === 'ko' ? 'ko' : 'en') + '"';
    var sub = (item.sub || []).map(function (s) { return esc(fmt(t(s.key), s.vars)); }).filter(Boolean).join(' · ');
    // Phones fold the type badge into the sub line, so a row is one label and one quiet line.
    var kindText = esc(t(KIND_KEY[item.kind] || 'kindTool'));
    var subHtml = '<span class="cs-sug-sub"><span class="cs-sug-kind-inline">' + kindText + '</span>' + (sub ? '<span class="cs-sug-sep" aria-hidden="true"> · </span>' + sub : '') + '</span>';
    var attrs = '';
    if (item.kind === 'tool' && item.action && SAFE_TOOL_ACTION[item.action]) attrs = ' data-action="' + esc(item.action) + '"';
    return '<li id="civicSuggest-' + i + '" class="cs-sug" role="option" aria-selected="false" data-cs-sug="' + i + '" data-kind="' + esc(item.kind) + '" data-match="' + esc(item.match) + '"' + attrs + '>' +
      '<span class="cs-sug-kind">' + kindText + '</span>' +
      '<span class="cs-sug-main"><span class="cs-sug-label" dir="auto"' + labelLang + '>' + highlight(label, query) + '</span>' + subHtml + '</span>' +
      icon(item.kind === 'tool' ? 'chevron-right' : 'search') + '</li>';
  }
  function setActive(i) {
    var input = el('#civicQuery'), list = el('#civicSuggest');
    if (!input || !list) return;
    sugg.active = i;
    var opts = list.querySelectorAll('[role="option"]');
    opts.forEach(function (o, k) { o.setAttribute('aria-selected', k === i ? 'true' : 'false'); });
    if (i >= 0 && opts[i]) { input.setAttribute('aria-activedescendant', opts[i].id); if (typeof opts[i].scrollIntoView === 'function') opts[i].scrollIntoView({ block: 'nearest' }); }
    else input.removeAttribute('aria-activedescendant');
  }
  function announce(text) {
    var live = el('[data-cs-suggest-status]'); if (!live) return;
    clearTimeout(sugg.announce);
    // Debounced so a screen reader hears the settled count, not one message per keystroke.
    sugg.announce = setTimeout(function () { live.textContent = text; }, 450);
  }
  function closeSuggest() {
    var box = el('.cs-suggest'), input = el('#civicQuery'), list = el('#civicSuggest');
    cancelAnimationFrame(sugg.frame);
    clearTimeout(sugg.announce);
    var live = el('[data-cs-suggest-status]'); if (live) live.textContent = '';
    sugg.items = []; sugg.active = -1;
    if (list) list.innerHTML = '';
    if (box) box.hidden = true;
    if (input) { input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); }
  }
  function syncTyping() {
    var input = el('#civicQuery'), hero = el('.cs-hero'), clear = el('[data-cs-clear]');
    var has = !!(input && input.value.trim());
    if (hero) hero.classList.toggle('cs-typing', has);
    if (clear) clear.hidden = !(input && input.value);
  }
  function renderSuggest() {
    var input = el('#civicQuery'), box = el('.cs-suggest'), list = el('#civicSuggest');
    if (!input || !box || !list) return;
    syncTyping();
    var value = input.value;
    if (!value.trim() || document.activeElement !== input) { closeSuggest(); return; }
    var engine = window.VisableSearchSuggest;
    // The engine script itself failed to load: suggestions are off for this page view (no retry loop).
    if (!engine) { suggestFailed = true; closeSuggest(); return; }
    if (!suggestIndex) {
      if (!suggestFailed) loadSuggestIndex().then(function () { scheduleSuggest(); }).catch(function () { /* the plain search keeps working */ });
      return;
    }
    var started = (window.performance && performance.now) ? performance.now() : Date.now();
    var result = engine.suggest(value, suggestIndex, { lang: lang(), limit: narrow() ? 6 : 7 });
    sugg.items = result.items; sugg.active = -1;
    var note = el('.cs-suggest-note'), foot = el('.cs-suggest-foot');
    var noteText = result.notes.map(function (n) { return fmt(t(n.key), n.vars); }).join(' ');
    note.hidden = !noteText; note.textContent = noteText;
    list.innerHTML = result.items.map(function (item, i) { return optionHtml(item, i, result.query); }).join('');
    list.hidden = !result.items.length;
    // Locales without their own procedure names see the official Korean/English terms, and are told so.
    var limited = uiLang() !== 'ko' && uiLang() !== 'en' ? '<span>' + esc(t('suggestLimited')) + '</span> ' : '';
    // Keyboard hints only where there is a keyboard to press them (not on touch-only screens).
    var keys = ''; try { keys = window.matchMedia('(hover: none)').matches ? '' : '<span class="cs-suggest-keys">' + esc(t('suggestFoot')) + '</span>'; } catch (e) { keys = ''; }
    var footHtml = result.items.length ? (limited || keys ? limited + keys : '') : esc(t('suggestEmpty'));
    foot.hidden = !footHtml; foot.innerHTML = footHtml;
    box.hidden = false;
    input.setAttribute('aria-expanded', result.items.length ? 'true' : 'false');
    input.removeAttribute('aria-activedescendant');
    announce(result.items.length ? fmt(t('suggestCount'), { n: result.items.length }) : (noteText || t('suggestEmpty')));
    sugg.renderMs = ((window.performance && performance.now) ? performance.now() : Date.now()) - started;
    sugg.lastRender = Date.now();
  }
  function scheduleSuggest() {
    cancelAnimationFrame(sugg.frame);
    sugg.frame = requestAnimationFrame(renderSuggest);
  }
  function chooseSuggestion(i) {
    var item = sugg.items[i], input = el('#civicQuery');
    if (!item || !input) return;
    if (item.kind === 'tool') {
      closeSuggest();
      if (item.href && SAFE_TOOL_HREF.test(item.href)) location.href = item.href;
      // data-action tools are handled by index.html's delegated click handler on the option itself.
      return;
    }
    input.value = item.query;
    closeSuggest(); syncTyping();
    searchFromHome(item.query);
  }
  function onQueryKeydown(event) {
    // Korean (and every other IME) composition: arrows move the candidate window and
    // Enter commits the syllable — never a suggestion selection or a search.
    if (event.isComposing || event.keyCode === 229 || sugg.composing) return;
    var input = event.target, box = el('.cs-suggest'), open = box && !box.hidden, n = sugg.items.length;
    if (event.key === 'ArrowDown' || event.key === 'Down') {
      event.preventDefault();
      if (!open || !n) { renderSuggest(); n = sugg.items.length; if (n) setActive(0); return; }
      setActive(sugg.active + 1 >= n ? 0 : sugg.active + 1);
    } else if (event.key === 'ArrowUp' || event.key === 'Up') {
      if (!open || !n) return;
      event.preventDefault();
      setActive(sugg.active <= 0 ? n - 1 : sugg.active - 1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (open && sugg.active >= 0) { var opt = el('#civicSuggest-' + sugg.active); if (opt) opt.click(); }
      else { closeSuggest(); searchFromHome(input.value); }
    } else if (event.key === 'Escape' || event.key === 'Esc') {
      if (open) { event.preventDefault(); closeSuggest(); }
      else if (input.value) { event.preventDefault(); input.value = ''; syncTyping(); }
      else if (document.body.classList.contains('cs-sheet')) { event.preventDefault(); closeSheet(); }
    } else if (event.key === 'Tab') {
      closeSuggest();
    }
  }
  /* Phone search sheet: focusing the field folds the brand and headline away and pins the field
   * to the top, so suggestions get the space above the on-screen keyboard. It closes only on an
   * explicit act (닫기, Escape on an empty field, a search) — never on blur — so a tap that moves
   * focus can never reflow the page under the finger. The CSS applies only at phone widths. */
  function openSheet() {
    if (document.body.classList.contains('cs-sheet') || !narrow()) return;
    document.body.classList.add('cs-sheet');
    try { window.scrollTo(0, 0); } catch (e) { /* ignore */ }
  }
  function closeSheet() {
    if (!document.body.classList.contains('cs-sheet')) return;
    document.body.classList.remove('cs-sheet');
    closeSuggest();
    var input = el('#civicQuery'); if (input) input.blur();
  }
  function bindSuggest() {
    var form = el('#civicSearchForm'), input = el('#civicQuery'), list = el('#civicSuggest');
    if (!form || !input || !list) return;
    input.addEventListener('input', function () { setActive(-1); scheduleSuggest(); });
    // A composition cancelled by blur may never send compositionend; focus starts clean.
    input.addEventListener('focus', function () { sugg.composing = false; openSheet(); loadSuggestIndex().catch(function () {}); if (input.value.trim()) scheduleSuggest(); });
    var sheetClose = el('[data-cs-sheet-close]');
    if (sheetClose) sheetClose.addEventListener('click', closeSheet);
    input.addEventListener('blur', function () { sugg.composing = false; });
    input.addEventListener('keydown', onQueryKeydown);
    input.addEventListener('compositionstart', function () { sugg.composing = true; });
    // compositionend can precede the committing Enter's keydown (Safari): stay "composing" for that one task.
    input.addEventListener('compositionend', function () { setTimeout(function () { sugg.composing = false; scheduleSuggest(); }, 0); });
    // Leaving the field and the panel closes the panel; clicks inside it keep focus (mousedown below).
    form.addEventListener('focusout', function (event) { if (!form.contains(event.relatedTarget)) closeSuggest(); });
    list.addEventListener('mousedown', function (event) { event.preventDefault(); });
    list.addEventListener('click', function (event) {
      var option = event.target.closest('[data-cs-sug]'); if (!option) return;
      chooseSuggestion(Number(option.getAttribute('data-cs-sug')));
    });
    var clear = el('[data-cs-clear]');
    if (clear) clear.addEventListener('click', function () { input.value = ''; closeSuggest(); syncTyping(); input.focus(); });
    syncTyping();
  }

  function bindHome() {
    var form = root.querySelector('#civicSearchForm');
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (sugg.composing) return;
      closeSuggest();
      searchFromHome(root.querySelector('#civicQuery').value);
    });
    root.querySelector('a[href="#civic-about"]').addEventListener('click', function () { root.querySelector('#civic-about').open = true; });
    var panel = journeyPanel();
    if (panel) panel.addEventListener('keydown', function (e) { if ((e.key === 'Escape' || e.key === 'Esc') && journey.state !== 'CLOSED') { e.preventDefault(); e.stopPropagation(); closeJourney(); } });
    bindSuggest();
    mountJourneySection();
  }
  function home(opts) {
    opts = opts || {};
    homeLanguage = uiLang();
    if (!journeySection) journeySection = document.getElementById('visaManualSection');
    var reuse = Boolean(opts.reuse) && root.getAttribute('data-cs-shell') === homeLanguage && root.querySelector('#civicBrowsePanel') && root.querySelector('.cs-tools-core');
    closeSuggest();
    if (!reuse) root.innerHTML = homeHtml(t, { langCode: currentLangCode() });
    root.setAttribute('data-cs-shell', homeLanguage);
    root.setAttribute('data-cs-hydrated', reuse ? 'reused' : 'rendered');
    bindHome();
    var state = opts.keepJourney ? journey.state : 'CLOSED';
    setJourney(state, { scroll: false, focus: false, rerender: true });
  }
  function homeStatus(message) {
    var status = root.querySelector('.cs-home-status');
    if (!status) { status = document.createElement('p'); status.className = 'cs-home-status'; status.setAttribute('role', 'status'); root.querySelector('form').after(status); }
    status.textContent = message;
  }
  function searchFromHome(value) {
    value = String(value || '').trim();
    if (!value) { root.querySelector('#civicQuery').focus(); return; }
    closeSuggest();
    document.body.classList.remove('cs-sheet');
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
  /* Raw source search is evidence, not a result system: one collapsed disclosure
   * ("관련 원문") that lives inside the guidance's 공식 근거 section, or right
   * after the guidance when that section is absent. */
  function rawSummary(count) {
    raw.querySelector('summary').innerHTML = '<span>' + esc(t('rawTitle')) + '</span>' + (count != null ? ' <span class="cs-raw-count">' + esc(count + ' ' + t('pages')) + '</span>' : '');
  }
  function placeRaw() {
    if (!raw) return;
    var slot = document.getElementById('sgRawSlot');
    var sg = document.getElementById('statusGuidance');
    if (slot) { if (raw.parentNode !== slot) slot.appendChild(raw); }
    else if (sg && sg.parentNode) { if (raw.previousElementSibling !== sg) sg.after(raw); }
    else { var results = document.getElementById('mainContent'); if (results && raw.parentNode !== results) results.prepend(raw); }
  }
  function openRaw() {
    placeRaw();
    var ev = document.getElementById('sgEvidence'); if (ev && ev.contains(raw)) ev.open = true;
    raw.open = true;
  }
  function sourceLinks() {
    return '<a href="' + VISA_PDF + '" target="_blank" rel="noopener">' + esc(t('visa')) + '</a> · <a href="' + STAY_PDF + '" target="_blank" rel="noopener">' + esc(t('stay')) + '</a>';
  }
  function evidenceQuery() {
    // excerpt highlighting follows the interpreted intent (status + procedure vocabulary)
    if (!intent) return query;
    var terms = intent.procedure && window.VisableManualSearch.PROCEDURE_TERMS ? (window.VisableManualSearch.PROCEDURE_TERMS[intent.procedure] || []) : [];
    return [intent.status || '', terms[terms.length - 1] || ''].join(' ').trim() || query;
  }
  /* Deep link into manual.html (readable original, sectioned by status and procedure).
   * Uses the guidance intent when present, else a status code typed in the query. */
  function readerLink() {
    var route = window.VisableManualReaderRoute;
    var code = intent && intent.status ? intent.status : ((String(query).toUpperCase().match(/\b[A-H]-\d{1,2}(?:-[0-9A-Z]+)?\b/) || [])[0] || '');
    var href = route ? route.href(code, intent ? intent.procedure : null, { domain: domain || (intent && intent.domain) }) : null;
    return '<p class="cs-reader-link"><a href="' + esc(href || 'manual.html') + '">' + esc(t('readerOpen')) + ' →</a></p>';
  }
  function renderResults() {
    hits = window.VisableManualSearch.search(corpus, query, { domain: domain, intent: intent });
    rawSummary(hits.length);
    var eq = evidenceQuery();
    panel.innerHTML = '<div class="cs-results-head"><div><h4>' + esc(t('manualTitle')) + '</h4><p>' + esc(t('currentSource')) + '</p></div><label><span class="cs-sr">' + esc(t('filter')) + '</span><select id="civicDomain"><option value="">' + esc(t('both')) + '</option><option value="visa_issuance">' + esc(t('visa')) + '</option><option value="stay">' + esc(t('stay')) + '</option></select></label></div>' +
      '<p class="cs-source-note">' + esc(t('sourceNote')) + '</p>' + readerLink() +
      (hits.length ? '<ol class="cs-manual-list">' + hits.slice(0, shown).map(function (hit, i) {
        var source = hit.source, page = hit.page;
        return '<li><div class="cs-result-meta">' + esc(lang() === 'en' ? source.title_en : source.title) + ' · ' + esc(source.date) + ' · ' + page.page + ' ' + esc(t('page')) + '</div>' +
          '<button type="button" class="cs-result-title" lang="ko" data-cs-page="' + i + '">' + esc(page.heading) + '</button><p lang="ko">' + esc(window.VisableManualSearch.excerpt(page.text, eq, corpus)) + '</p>' +
          '<div class="cs-result-actions"><span>' + esc(t('review')) + '</span><button type="button" data-cs-page="' + i + '">' + esc(t('excerpt')) + '</button><a href="' + esc(source.file) + '#page=' + page.page + '" target="_blank" rel="noopener">' + esc(t('original')) + icon('external-link') + '</a></div></li>';
      }).join('') + '</ol>' : '<div class="cs-empty"><h3>' + esc(t('empty')) + '</h3><p>' + esc(t('emptyHelp')) + '</p></div>') +
      (hits.length > shown ? '<button type="button" class="cs-more" data-cs-more>' + esc(t('more')) + '</button>' : '') + '<p class="cs-caveat">' + esc(t('caveat')) + '</p>';
    var select = panel.querySelector('select'); select.value = domain;
    select.addEventListener('change', function () { domain = select.value; shown = 3; renderResults(); });
  }
  function find(queryValue, nextIntent) {
    var q = String(queryValue || '').trim();
    if (q !== query) intent = null;
    if (nextIntent !== undefined) intent = nextIntent;
    query = q; shown = 3;
    var request = ++sequence;
    placeRaw();
    if (!query) { panel.innerHTML = ''; rawSummary(null); raw.open = false; return; }
    rawSummary(null);
    panel.innerHTML = '<p class="cs-load" role="status">' + esc(t('loading')) + '</p>';
    load().then(function () { if (request === sequence) renderResults(); }).catch(function () {
      if (request !== sequence) return;
      panel.innerHTML = '<div class="cs-empty" role="status"><p>' + esc(t('error')) + '</p><button type="button" data-cs-retry>' + esc(t('retry')) + '</button><p>' + sourceLinks() + '</p></div>';
    });
  }
  function showHit(hit, origin) {
    dialogReturn = origin;
    dialog.innerHTML = '<div class="cs-dialog-head"><div><p>' + esc(hit.source.title) + ' · ' + esc(hit.source.date) + ' · ' + hit.page.page + ' ' + esc(t('page')) + '</p><h2 id="civicPageTitle">' + esc(hit.page.heading) + '</h2></div><button type="button" data-cs-close aria-label="' + esc(t('close')) + '">' + icon('x') + '</button></div><p class="cs-caveat">' + esc(t('review')) + '. ' + esc(t('caveat')) + '</p><pre>' + esc(hit.page.text) + '</pre><a class="cs-pdf-link" href="' + esc(hit.source.file) + '#page=' + hit.page.page + '" target="_blank" rel="noopener">' + esc(t('original')) + ' · ' + hit.page.page + ' ' + esc(t('page')) + icon('external-link') + '</a>';
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
  window.VisableCivicSearch = {
    load: load, openPage: openPage, homeHtml: homeHtml, copy: copy, langButton: langButton,
    journey: { open: openJourney, close: closeJourney, toggle: toggleJourney, state: function () { return journey.state; } },
    // Read-only view of the suggestion panel for tests and QA (no query text is kept anywhere else).
    suggestions: { state: function () { return { ready: !!suggestIndex, failed: suggestFailed, count: sugg.items.length, active: sugg.active, renderMs: sugg.renderMs, items: sugg.items.map(function (i) { return { kind: i.kind, match: i.match, label: i.label || i.labelKey, query: i.query || null, href: i.href || null, action: i.action || null }; }) }; } }
  };
  // Pages (and the Node parity check) that have no landing DOM stop here: the API above is still published.
  if (!document.getElementById('mainContent')) return;

  function init() {
    var existing = document.getElementById('civicLanding');
    root = existing || document.createElement('div');
    root.id = 'civicLanding';
    // The static document already carries this class; keeping the add() makes the JS
    // path self-sufficient on any page that still lacks the static shell.
    document.body.classList.add('civic-refresh');
    if (!existing) document.body.insertBefore(root, document.getElementById('hero'));
    home({ reuse: Boolean(existing) });
    raw = document.createElement('details'); raw.id = 'civicRawSources'; raw.className = 'cs-raw';
    raw.innerHTML = '<summary></summary>';
    panel = document.createElement('section'); panel.id = 'civicManualResults'; panel.className = 'cs-manual-results'; panel.setAttribute('aria-label', t('manuals'));
    raw.append(panel); rawSummary(null);
    placeRaw();
    dialog = document.createElement('dialog'); dialog.id = 'civicPageDialog'; dialog.setAttribute('aria-labelledby', 'civicPageTitle'); document.body.append(dialog);
    dialog.addEventListener('close', function () { if (dialogReturn && dialogReturn.isConnected) dialogReturn.focus(); });
    mountSearchedLangButton();
    document.addEventListener('click', function (event) {
      var target = event.target.closest('button'); if (!target) return;
      if (target.hasAttribute('data-cs-lang-open')) { openLangDialog(target); return; }
      // Tabs inside the browse panel switch tracks; pressing the open tab again keeps it open.
      if (target.hasAttribute('data-cs-journey')) { var track = target.getAttribute('data-cs-journey'); if (track === 'close') closeJourney(); else openJourney(track); return; }
      if (target.hasAttribute('data-cs-focus')) { if (target.hasAttribute('data-cs-manual')) rawFirst = true; var field = root.querySelector('#civicQuery'); field.focus(); field.scrollIntoView({ block: 'center', behavior: prefersReducedMotion() ? 'auto' : 'smooth' }); }
      if (target.dataset.csQuery) searchFromHome(target.dataset.csQuery);
      if (target.hasAttribute('data-cs-page')) showPage(Number(target.dataset.csPage), target);
      if (target.hasAttribute('data-cs-close')) dialog.close();
      if (target.hasAttribute('data-cs-more')) { shown += 12; renderResults(); }
      if (target.hasAttribute('data-cs-retry')) find(query);
    });
    document.addEventListener('paradiso:results-rendered', function (event) { find(event.detail.query); });
    // The guidance resolved the query: re-rank the raw sources by its intent and keep them under 공식 근거.
    document.addEventListener('visable:guidance-rendered', function (event) {
      var d = event.detail || {};
      placeRaw();
      if (String(d.query || '').trim() === query && JSON.stringify(d.evidenceIntent || null) !== JSON.stringify(intent)) find(query, d.evidenceIntent || null);
      if (rawFirst) { rawFirst = false; openRaw(); raw.scrollIntoView({ block: 'start' }); }
    });
    // Back from the first result reaches the bare home URL: show the search home again instead of an
    // empty result page. Forward from the home to a ?q= entry runs that search again. (Moving between
    // two ?q= entries is unified-search.js's popstate.)
    window.addEventListener('popstate', function () {
      var q = ''; try { q = new URL(location.href).searchParams.get('q') || ''; } catch (e) { /* keep the page as is */ return; }
      var searched = document.body.classList.contains('searched');
      if (!q.trim() && searched && typeof resetToLanding === 'function') resetToLanding();
      else if (q.trim() && !searched) searchFromHome(q);
    });
    document.addEventListener('paradiso:data-ready', function () { if (queuedQuery) searchFromHome(queuedQuery); });
    document.addEventListener('paradiso:data-failed', function () { if (queuedQuery) homeStatus(t('unavailable')); });
    document.addEventListener('paradiso:landing-reset', function () {
      ++sequence; query = ''; queuedQuery = ''; intent = null; rawFirst = false; domain = ''; panel.innerHTML = ''; rawSummary(null); raw.open = false;
      document.body.classList.remove('cs-sheet');
      var url = new URL(location.href); url.searchParams.delete('q'); history.replaceState(null, '', url);
      home();
    });
    window.addEventListener('paradiso-language-applied', function () {
      if (langDialog && langDialog.open) langDialog.close();
      refreshLangButtons();
      if (uiLang() === homeLanguage) return;
      var draft = root.querySelector('#civicQuery') ? root.querySelector('#civicQuery').value : '';
      var directoryOpen = root.querySelector('.cs-directory') && root.querySelector('.cs-directory').open;
      var aboutOpen = root.querySelector('.cs-about') && root.querySelector('.cs-about').open;
      home({ keepJourney: true });
      if (draft && root.querySelector('#civicQuery')) { root.querySelector('#civicQuery').value = draft; syncTyping(); }
      if (directoryOpen) root.querySelector('.cs-directory').open = true;
      if (aboutOpen) root.querySelector('.cs-about').open = true;
      if (query) find(query);
    });
    if (document.body.classList.contains('searched')) find(document.getElementById('q').value);
    // Phones, result page: the sticky search header slides away while reading down and returns on
    // any upward scroll or when focus enters it, so the answer gets the screen.
    var lastY = window.scrollY || 0, ticking = false, header = document.getElementById('hero');
    function syncHeader() {
      ticking = false;
      var y = window.scrollY || 0, dy = y - lastY;
      var hide = document.body.classList.contains('searched') && narrow() && header && !header.contains(document.activeElement) && y > 160;
      if (!hide) document.body.classList.remove('cs-hdr-away');
      else if (dy > 8) document.body.classList.add('cs-hdr-away');
      else if (dy < -8) document.body.classList.remove('cs-hdr-away');
      if (Math.abs(dy) > 8 || !hide) lastY = y;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(syncHeader); } }, { passive: true });
    if (header) header.addEventListener('focusin', function () { document.body.classList.remove('cs-hdr-away'); });
    // The suggestion index is small (derived, ~12 KB gzipped): fetch it when the page is idle so the
    // first keystroke never waits. A failure only disables suggestions; the search itself still works.
    var warm = function () { loadSuggestIndex().catch(function () {}); };
    if (typeof window.requestIdleCallback === 'function') window.requestIdleCallback(warm, { timeout: 2500 }); else setTimeout(warm, 1200);
  }
  function boot() {
    try { init(); }
    catch (error) {
      // A failed boot must never leave a silent, dead page: the static shell shows a reload row.
      document.body.classList.add('civic-boot-failed');
      throw error;
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
