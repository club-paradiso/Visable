(function () {
  'use strict';

  var VISA_RE = /\b([A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?)?)\b/i;
  // `key` is the stable goal id; the label comes from COPY in the chrome language.
  var GOALS = [
    { terms: ['근무처 변경', '근무처를 변경', '이직', '고용주 변경', 'workplace change', 'change employer'], key: 'workplace' },
    { terms: ['체류기간 연장', '연장', 'extension'], key: 'extension' },
    { terms: ['체류자격 변경', '비자 변경', 'status change'], key: 'statusChange' },
    { terms: ['외국인등록', '등록증', 'registration'], key: 'registration' },
    { terms: ['귀화', '국적', 'naturalization'], key: 'nationality' },
    { terms: ['서류', 'documents'], key: 'documents' }
  ];

  // Context-strip copy in the same three chrome languages ai.html's shell uses
  // (ko / en / zh; zh-TW is converted by zh-traditional.js like the rest).
  var COPY = {
    ko: {
      detect: '질문에서 자동 감지', auto: '절차 자동 분류', empty: '구체적인 상황을 알려주시면 좁혀 드립니다',
      workplace: '근무처 변경', extension: '체류기간 연장', statusChange: '체류자격 변경', registration: '외국인등록', nationality: '국적·귀화', documents: '제출서류 확인',
      needWorkplace: '세부 직종 · 새 사업장 업종 · 변경 예정일', needExtension: '현재 만료일 · 체류 중 변경사항',
      needStatusChange: '현재 자격 · 목표 자격 · 변경 사유', needDefault: '현재 체류자격 · 원하는 결과 · 처리 예정일'
    },
    en: {
      detect: 'Detected from your question', auto: 'Sorted automatically', empty: 'Tell us more and Waymaker will narrow it down',
      workplace: 'Workplace change', extension: 'Extension of stay', statusChange: 'Change of status', registration: 'Alien registration', nationality: 'Nationality / naturalization', documents: 'Required documents',
      needWorkplace: 'Exact job type · new workplace industry · planned change date', needExtension: 'Current expiry date · changes during your stay',
      needStatusChange: 'Current status · target status · reason for the change', needDefault: 'Current status · the outcome you want · planned date'
    },
    zh: {
      detect: '从提问中自动识别', auto: '自动分类手续', empty: '请告诉我们具体情况，我们会帮您缩小范围',
      workplace: '工作单位变更', extension: '居留期限延长', statusChange: '居留资格变更', registration: '外国人登录', nationality: '国籍·归化', documents: '确认提交材料',
      needWorkplace: '具体职种 · 新单位行业 · 预计变更日期', needExtension: '当前到期日 · 居留期间的变化',
      needStatusChange: '当前资格 · 目标资格 · 变更理由', needDefault: '当前居留资格 · 希望的结果 · 预计办理日期'
    }
  };

  function chromeLang() {
    var raw = '';
    try { raw = (new URLSearchParams(location.search).get('lang') || '').trim(); } catch (e) {}
    if (!raw) { try { raw = (localStorage.getItem('paradiso:language') || '').trim(); } catch (e) {} }
    if (raw === 'en') return 'en';
    if (raw.indexOf('zh') === 0) return 'zh';
    return 'ko';
  }
  function copy(key) { var c = COPY[chromeLang()] || COPY.ko; return c[key] || COPY.ko[key] || ''; }

  function detectGoal(text) {
    var low = String(text || '').toLowerCase();
    for (var i = 0; i < GOALS.length; i += 1) {
      if (GOALS[i].terms.some(function (term) { return low.indexOf(term.toLowerCase()) !== -1; })) {
        return GOALS[i].key;
      }
    }
    return '';
  }

  function missingHint(text, goal) {
    var value = String(text || '').trim();
    if (!value) return copy('empty');
    if (goal === 'workplace') return copy('needWorkplace');
    if (goal === 'extension') return copy('needExtension');
    if (goal === 'statusChange') return copy('needStatusChange');
    return copy('needDefault');
  }

  function updateContext(text) {
    var status = document.getElementById('wmContextStatus');
    var goal = document.getElementById('wmContextGoal');
    var missing = document.getElementById('wmContextMissing');
    if (!status || !goal || !missing) return;
    var match = String(text || '').toUpperCase().match(VISA_RE);
    var detectedGoal = detectGoal(text);
    status.textContent = match ? match[1] : copy('detect');
    goal.textContent = detectedGoal ? copy(detectedGoal) : copy('auto');
    missing.textContent = missingHint(text, detectedGoal);
  }

  function setActiveRoute(route) {
    document.querySelectorAll('[data-workspace-route]').forEach(function (link) {
      link.classList.toggle('is-active', link.getAttribute('data-workspace-route') === route);
      if (link.getAttribute('data-workspace-route') === route) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  }

  function openResearch(options) {
    options = options || {};
    if (document.body.classList.contains('wm-active')) return;
    document.body.classList.add('wm-research-open');
    setActiveRoute('research');
    var root = document.getElementById('legalSourceSearchRoot');
    if (root) root.style.display = 'block';
    try {
      if (window.ParadisoLegalSearch && typeof window.ParadisoLegalSearch.openPanel === 'function') {
        window.ParadisoLegalSearch.openPanel();
      }
    } catch (e) { /* panel remains visible; its own toggle still works */ }
    if (options.updateHash !== false && location.hash !== '#legalSourceSearchRoot') {
      history.replaceState(null, '', location.pathname + location.search + '#legalSourceSearchRoot');
    }
  }

  function openChat() {
    document.body.classList.remove('wm-research-open');
    var root = document.getElementById('legalSourceSearchRoot');
    if (root) root.style.display = '';
    setActiveRoute('chat');
  }

  function initialize() {
    var params = new URLSearchParams(location.search);
    var navigatorMode = params.get('nav') === '1' && document.body.classList.contains('wm-active');
    if (navigatorMode) setActiveRoute('navigator');
    else if (location.hash === '#legalSourceSearchRoot') openResearch({ updateHash: false });
    else setActiveRoute('chat');

    var input = document.getElementById('aiQ');
    if (input) {
      updateContext(input.value);
      input.addEventListener('input', function () { updateContext(input.value); });
    }

    var visaHint = params.get('visa_code') || '';
    var procedureHint = params.get('selected_procedure_key') || '';
    if (visaHint || procedureHint) updateContext([visaHint, procedureHint].join(' '));

    document.addEventListener('click', function (event) {
      var researchLink = event.target.closest && event.target.closest('[data-workspace-route="research"]');
      if (researchLink && !document.body.classList.contains('wm-active')) {
        event.preventDefault();
        openResearch();
        return;
      }
      var chatLink = event.target.closest && event.target.closest('[data-workspace-route="chat"]');
      if (chatLink && !document.body.classList.contains('wm-active') && location.pathname.endsWith('/ai.html')) {
        event.preventDefault();
        history.replaceState(null, '', location.pathname + location.search.replace(/([?&])nav=1(&|$)/, '$1').replace(/[?&]$/, ''));
        openChat();
      }
      var handoff = event.target.closest && event.target.closest('[data-wm-handoff]');
      if (handoff) openResearch();
    });

    window.addEventListener('hashchange', function () {
      if (location.hash === '#legalSourceSearchRoot') openResearch({ updateHash: false });
      else if (!document.body.classList.contains('wm-active')) openChat();
    });

    var historyEl = document.getElementById('chatHistory');
    if (historyEl && window.MutationObserver) {
      var observer = new MutationObserver(function () {
        var pills = historyEl.querySelectorAll('.context-pill');
        if (!pills.length) return;
        var text = Array.prototype.map.call(pills, function (el) { return el.textContent || ''; }).join(' ');
        if (text) updateContext(text);
      });
      observer.observe(historyEl, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();

  window.WaymakerWorkspace = { openResearch: openResearch, openChat: openChat, updateContext: updateContext };
})();
