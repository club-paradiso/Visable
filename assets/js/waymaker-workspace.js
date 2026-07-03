(function () {
  'use strict';

  var VISA_RE = /\b([A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?)?)\b/i;
  var GOALS = [
    { terms: ['근무처 변경', '근무처를 변경', '이직', '고용주 변경', 'workplace change', 'change employer'], ko: '근무처 변경' },
    { terms: ['체류기간 연장', '연장', 'extension'], ko: '체류기간 연장' },
    { terms: ['체류자격 변경', '비자 변경', 'status change'], ko: '체류자격 변경' },
    { terms: ['외국인등록', '등록증', 'registration'], ko: '외국인등록' },
    { terms: ['귀화', '국적', 'naturalization'], ko: '국적·귀화' },
    { terms: ['서류', 'documents'], ko: '제출서류 확인' }
  ];

  function detectGoal(text) {
    var low = String(text || '').toLowerCase();
    for (var i = 0; i < GOALS.length; i += 1) {
      if (GOALS[i].terms.some(function (term) { return low.indexOf(term.toLowerCase()) !== -1; })) {
        return GOALS[i].ko;
      }
    }
    return '절차 자동 분류';
  }

  function missingHint(text, goal) {
    var value = String(text || '').trim();
    if (!value) return '구체적인 상황을 알려주시면 좁혀 드립니다';
    if (goal === '근무처 변경') return '세부 직종 · 새 사업장 업종 · 변경 예정일';
    if (goal === '체류기간 연장') return '현재 만료일 · 체류 중 변경사항';
    if (goal === '체류자격 변경') return '현재 자격 · 목표 자격 · 변경 사유';
    return '현재 체류자격 · 원하는 결과 · 처리 예정일';
  }

  function updateContext(text) {
    var status = document.getElementById('wmContextStatus');
    var goal = document.getElementById('wmContextGoal');
    var missing = document.getElementById('wmContextMissing');
    if (!status || !goal || !missing) return;
    var match = String(text || '').toUpperCase().match(VISA_RE);
    var detectedGoal = detectGoal(text);
    status.textContent = match ? match[1] : '질문에서 자동 감지';
    goal.textContent = detectedGoal;
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
