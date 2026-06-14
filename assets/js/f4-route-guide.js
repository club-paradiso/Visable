/* ============================================================================
 * Paradiso — F-4 재외동포 경로 찾기 (Overseas Korean pathway finder)
 * ----------------------------------------------------------------------------
 * Replaces the "pick a legal route name" experience with life-situation cards:
 * the user answers "어떤 상황에 가까우신가요?" and is mapped to a likely F-4
 * route with grouped document checklists, blockers, FBI/apostille preparation,
 * and the post-entry 90-day 국내거소신고(거소증) step.
 *
 * Data: fetched lazily from data/f4/routes.json (kept OUT of index.html).
 *
 * Safety contract (do not weaken):
 *  - Never implies F-4 is available to current Korean nationals.
 *  - Never implies 거소증 can be issued at an overseas consulate.
 *  - Never hides the 90-day domestic residence report requirement.
 *  - Never shows a bare generic "수수료" where the fee context is known.
 *  - Source dates + freshness badges always shown; eligibility never promised.
 * ========================================================================== */
(function () {
  'use strict';

  var ROUTES_URL = 'data/f4/routes.json';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  var STR = {
    loading: 'F-4 경로 데이터를 불러오는 중입니다…',
    fetchFail: 'F-4 경로 데이터를 불러오지 못했습니다. 이 안내 없이 진행하지 마시고, 관할 재외공관·하이코리아·1345에서 직접 확인해 주세요.',
    selectAria: 'F-4 상황 선택',
    resultPath: '추천 경로',
    resultWhy: '왜 이 경로인가요?',
    checkFirst: '먼저 확인할 것',
    documents: '준비서류',
    slow: '시간이 오래 걸릴 수 있는 항목',
    official: '공식 확인',
    caution: '주의',
    timelineTitle: 'F-4 전체 단계 한눈에 보기',
    badgeVerified: '공식 기준 확인됨',
    badgeNeedsRefresh: '공식 고시·목록 기준',
    badgePartial: '일부 자료 기준',
    sourceDatePrefix: '출처 기준일'
  };

  var NEXT_ACTION_LINKS = {
    '관할 공관 확인하기': { url: 'https://overseas.mofa.go.kr', external: true },
    '비자포털 확인하기': { url: 'https://www.visa.go.kr', external: true },
    '1345 확인 권장': { url: 'tel:1345', external: false },
    'HiKorea 확인하기': { url: 'https://www.hikorea.go.kr', external: true },
    'FBI 준비 안내 보기': { action: 'select-route', routeId: 'fbi_apostille_preparation' },
    '거소증 단계 확인하기': { action: 'select-route', routeId: 'domestic_residence_report_after_entry' }
  };

  function freshnessBadge(sourceStatus, sourceDate) {
    var cls = sourceStatus === 'verified' ? 'ok' : (sourceStatus === 'partial' ? 'partial' : 'refresh');
    var label = sourceStatus === 'verified' ? STR.badgeVerified
      : sourceStatus === 'partial' ? STR.badgePartial : STR.badgeNeedsRefresh;
    return '<span class="f4g-badge f4g-badge-' + cls + '">' + esc(label) + '</span>' +
      (sourceDate ? '<span class="f4g-badge">' + esc(STR.sourceDatePrefix + ': ' + sourceDate) + '</span>' : '');
  }

  var api = { STR: STR, freshnessBadge: freshnessBadge };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoF4Guide = api;

  if (typeof document === 'undefined') return;

  var state = { data: null, loadPromise: null, mounted: false, selectedRoute: null };

  function loadRoutes() {
    if (state.data) return Promise.resolve(state.data);
    if (state.loadPromise) return state.loadPromise;
    state.loadPromise = fetch(ROUTES_URL, { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (json) {
        if (!json || json.schemaVersion !== 1 || !Array.isArray(json.routes)) throw new Error('unexpected schema');
        state.data = json;
        return json;
      })
      .catch(function (e) { state.loadPromise = null; throw e; });
    return state.loadPromise;
  }
  api.loadRoutes = loadRoutes;

  function injectStyles() {
    if (document.getElementById('f4RouteGuideStyles')) return;
    var css = '' +
'.f4-route-guide{margin:1.25rem 0;}' +
'.f4g-card{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1.1rem 1.15rem;}' +
'.f4g-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.f4g-title{font-size:1.15rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .25rem;}' +
'.f4g-sub{font-size:.85rem;color:var(--t2,#4f5552);margin:0 0 .55rem;word-break:keep-all;}' +
'.f4g-note{font-size:.8rem;color:var(--hlT,#8A3426);background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:8px;padding:.5rem .65rem;margin:0 0 .8rem;word-break:keep-all;}' +
'.f4g-badges{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.8rem;}' +
'.f4g-badge{display:inline-block;font-size:.72rem;font-weight:700;padding:.18rem .55rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t2,#4f5552);background:var(--bg2,#f1ece2);}' +
'.f4g-badge-refresh{border-color:var(--ac,#2f5e67);color:var(--ac,#2f5e67);background:transparent;}' +
'.f4g-badge-partial{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4g-badge-ok{border-color:var(--cSt,#0EA37B);color:var(--cSt,#0a7a5c);background:transparent;}' +
'.f4g-question{font-size:.95rem;font-weight:800;color:var(--t1,#202221);margin:.2rem 0 .55rem;}' +
'.f4g-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:.6rem;}' +
'.f4g-situation{font:inherit;text-align:left;background:var(--bgI,#fff);border:1.5px solid var(--bd,#d1c6b4);border-radius:12px;padding:.7rem .8rem;cursor:pointer;min-height:44px;color:var(--t1,#202221);}' +
'.f4g-situation:hover{border-color:var(--ac,#2f5e67);}' +
'.f4g-situation:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4g-situation[aria-pressed="true"]{border-color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.08));box-shadow:inset 0 0 0 1px var(--ac,#2f5e67);}' +
'.f4g-situation strong{display:block;font-size:.9rem;margin-bottom:.25rem;word-break:keep-all;}' +
'.f4g-situation small{display:block;font-size:.76rem;color:var(--t3,#757a76);line-height:1.5;word-break:keep-all;}' +
'.f4g-situation .f4g-selected-mark{display:none;font-size:.72rem;font-weight:800;color:var(--ac,#2f5e67);margin-top:.3rem;}' +
'.f4g-situation[aria-pressed="true"] .f4g-selected-mark{display:block;}' +
'.f4g-result{margin-top:1rem;border-top:2px solid var(--bd2,#ddd3c3);padding-top:1rem;}' +
'.f4g-result h3{font-size:1.02rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 .3rem;word-break:keep-all;}' +
'.f4g-result h4{font-size:.85rem;font-weight:800;color:var(--t2,#4f5552);margin:.9rem 0 .35rem;}' +
'.f4g-result p,.f4g-result li{font-size:.88rem;line-height:1.65;color:var(--t1,#202221);word-break:keep-all;}' +
'.f4g-result ul{margin:.2rem 0;padding-left:1.15rem;}' +
'.f4g-chips{display:flex;flex-wrap:wrap;gap:.35rem;}' +
'.f4g-chip{display:inline-block;font-size:.76rem;font-weight:800;padding:.28rem .6rem;border-radius:999px;border:1.5px solid var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4g-docs details{border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.45rem .7rem;margin-top:.4rem;background:var(--bgI,#fff);}' +
'.f4g-docs summary{cursor:pointer;font-size:.84rem;font-weight:800;color:var(--t1,#202221);min-height:32px;display:flex;align-items:center;gap:.4rem;}' +
'.f4g-docs summary::marker{color:var(--ac,#2f5e67);}' +
'.f4g-warnbox{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.7rem .8rem;margin-top:.35rem;}' +
'.f4g-warnbox li{color:var(--hlT,#8A3426);}' +
'.f4g-links{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.4rem;}' +
'.f4g-links a,.f4g-links button{display:inline-flex;align-items:center;min-height:40px;padding:.35rem .8rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.82rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.f4g-links a:hover,.f4g-links button:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.f4g-links a:focus-visible,.f4g-links button:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4g-timeline{margin-top:1rem;}' +
'.f4g-timeline>details{border:1px solid var(--bd,#d1c6b4);border-radius:12px;padding:.5rem .75rem;background:var(--bgI,#fff);}' +
'.f4g-timeline>details>summary{cursor:pointer;font-size:.88rem;font-weight:800;color:var(--t1,#202221);min-height:36px;display:flex;align-items:center;}' +
'.f4g-step{border-left:3px solid var(--ac,#2f5e67);margin:.7rem 0 .7rem .3rem;padding:.1rem 0 .1rem .75rem;}' +
'.f4g-step h5{font-size:.86rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .3rem;}' +
'.f4g-step li{font-size:.83rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;}' +
'.f4g-srcline{font-size:.74rem;color:var(--t3,#757a76);margin-top:.5rem;}' +
'.f4g-error{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.8rem;font-size:.88rem;color:var(--hlT,#8A3426);word-break:keep-all;}' +
'@media (max-width:480px){.f4g-cards{grid-template-columns:1fr;}.f4g-card{padding:.9rem .8rem;}}' +
'@media (prefers-reduced-motion: no-preference){.f4g-result{animation:f4gFade .25s ease-out;}@keyframes f4gFade{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}}';
    var style = document.createElement('style');
    style.id = 'f4RouteGuideStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function renderGuideShell(section, data) {
    injectStyles();
    var cards = data.routes.map(function (r) {
      return '<button type="button" class="f4g-situation" data-route-id="' + esc(r.id) + '" aria-pressed="false">' +
        '<strong>' + esc(r.cardLabel) + '</strong>' +
        '<small>' + esc(r.cardHelper) + '</small>' +
        '<span class="f4g-selected-mark">✓ 선택됨 — 아래 안내를 확인하세요</span>' +
      '</button>';
    }).join('');
    var timeline = data.timeline.map(function (t) {
      return '<div class="f4g-step"><h5>' + esc(t.title) + '</h5><ul>' +
        t.items.map(function (i) { return '<li>' + esc(i) + '</li>'; }).join('') + '</ul></div>';
    }).join('');
    section.innerHTML =
      '<div class="f4g-card">' +
        '<p class="f4g-eyebrow">' + esc(data.intro.eyebrow) + '</p>' +
        '<h2 class="f4g-title" id="f4RouteGuideTitle">' + esc(data.intro.title) + '</h2>' +
        '<p class="f4g-sub">' + esc(data.intro.subtitle) + '</p>' +
        '<div class="f4g-badges">' + freshnessBadge(data.sourceStatus, data.lastUpdated) + '</div>' +
        '<p class="f4g-note">' + esc(data.intro.note) + '</p>' +
        '<p class="f4g-question">' + esc(data.intro.question) + '</p>' +
        '<div class="f4g-cards" role="group" aria-label="' + esc(STR.selectAria) + '">' + cards + '</div>' +
        '<div class="f4g-result" data-f4g-result role="status" aria-live="polite" hidden></div>' +
        '<div class="f4g-timeline"><details><summary>🗺 ' + esc(STR.timelineTitle) + '</summary>' + timeline + '</details></div>' +
        '<p class="f4g-srcline">출처: 2026.5 사증발급 안내매뉴얼(재외동포편·별첨1), 2026.6.1 체류매뉴얼, 주미공관 안내(저장 사본). 자세한 출처: data/f4/sources.json · 이 안내는 자격이나 허가를 보장하지 않습니다.</p>' +
      '</div>';

    section.querySelectorAll('.f4g-situation').forEach(function (btn) {
      btn.addEventListener('click', function () { selectRoute(section, data, btn.dataset.routeId); });
    });
  }

  function renderDocGroups(docGroups, openFirst) {
    var keys = Object.keys(docGroups || {});
    return keys.map(function (k, i) {
      var items = docGroups[k].map(function (d) { return '<li>' + esc(d) + '</li>'; }).join('');
      return '<details' + (openFirst && i === 0 ? ' open' : '') + '><summary>📋 ' + esc(k) + ' (' + docGroups[k].length + ')</summary><ul>' + items + '</ul></details>';
    }).join('');
  }

  function renderNextActions(actions) {
    return (actions || []).map(function (label) {
      var cfg = NEXT_ACTION_LINKS[label];
      if (!cfg) return '';
      if (cfg.action === 'select-route') {
        return '<button type="button" data-f4g-jump="' + esc(cfg.routeId) + '">' + esc(label) + '</button>';
      }
      return '<a href="' + esc(cfg.url) + '"' + (cfg.external ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' + esc(label) + '</a>';
    }).join('');
  }

  function selectRoute(section, data, routeId, scrollIntoView) {
    var route = null;
    for (var i = 0; i < data.routes.length; i++) if (data.routes[i].id === routeId) route = data.routes[i];
    if (!route) return;
    state.selectedRoute = routeId;
    section.querySelectorAll('.f4g-situation').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.routeId === routeId));
    });
    var host = section.querySelector('[data-f4g-result]');
    if (!host) return;
    host.innerHTML =
      '<h4>' + esc(STR.resultPath) + '</h4>' +
      '<h3>' + esc(route.resultLabel) + '</h3>' +
      '<h4>' + esc(STR.resultWhy) + '</h4>' +
      '<p>' + esc(route.why) + '</p>' +
      '<h4>' + esc(STR.checkFirst) + '</h4>' +
      '<div class="f4g-chips">' + route.checkFirst.map(function (c) { return '<span class="f4g-chip">' + esc(c) + '</span>'; }).join('') + '</div>' +
      '<h4>' + esc(STR.documents) + '</h4>' +
      '<div class="f4g-docs">' + renderDocGroups(route.documents, true) + '</div>' +
      '<h4>' + esc(STR.slow) + '</h4>' +
      '<ul>' + data.slowItems.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul>' +
      '<h4>' + esc(STR.official) + '</h4>' +
      '<div class="f4g-links">' + renderNextActions(route.nextActions) + '</div>' +
      '<p class="f4g-srcline">' + freshnessBadge(data.sourceStatus, data.lastUpdated) + ' · 출처 ID: ' + esc((route.sourceRefs || []).join(', ')) + '</p>' +
      '<h4>' + esc(STR.caution) + '</h4>' +
      '<div class="f4g-warnbox"><ul>' +
        (route.blockers || []).map(function (b) { return '<li>' + esc(b) + '</li>'; }).join('') +
        data.commonWarnings.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('') +
      '</ul></div>';
    host.hidden = false;
    host.querySelectorAll('[data-f4g-jump]').forEach(function (btn) {
      btn.addEventListener('click', function () { selectRoute(section, data, btn.dataset.f4gJump, true); });
    });
    if (scrollIntoView) host.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function mountGuide(section) {
    if (state.mounted) return Promise.resolve(section);
    state.mounted = true;
    injectStyles();
    section.innerHTML = '<div class="f4g-card"><p class="f4g-sub">' + esc(STR.loading) + '</p></div>';
    return loadRoutes().then(function (data) {
      renderGuideShell(section, data);
      return section;
    }).catch(function () {
      state.mounted = false;
      section.innerHTML = '<div class="f4g-card"><div class="f4g-error">' + esc(STR.fetchFail) + '</div>' +
        '<div class="f4g-links" style="margin-top:.5rem;">' +
          '<a href="https://overseas.mofa.go.kr" target="_blank" rel="noopener noreferrer">관할 공관 확인하기</a>' +
          '<a href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">HiKorea</a>' +
          '<a href="tel:1345">1345 확인 권장</a>' +
        '</div></div>';
      return section;
    });
  }

  /* ---------------------------------------------- search-result integration */
  var F4_QUERY = /f-?4|재외동포|동포\s*비자/i;
  var EXTRA_TRIGGERS = ['거소증', '국내거소', '거소신고', 'fbi', '범죄경력', '아포스티유', '국적상실', '복수국적', '병역', '이중국적'];

  function detectKeywordRoute(query, data) {
    var q = String(query || '').toLowerCase();
    if (!data || !data.keywordCards) return null;
    var keys = Object.keys(data.keywordCards);
    for (var i = 0; i < keys.length; i++) {
      var card = data.keywordCards[keys[i]];
      for (var j = 0; j < card.match.length; j++) {
        if (q.indexOf(card.match[j].toLowerCase()) !== -1) return card.routeId;
      }
    }
    return null;
  }

  function isF4Relevant(detail) {
    var q = String((detail && detail.query) || '');
    if (F4_QUERY.test(q)) return true;
    var lower = q.toLowerCase();
    for (var i = 0; i < EXTRA_TRIGGERS.length; i++) {
      if (lower.indexOf(EXTRA_TRIGGERS[i]) !== -1) return true;
    }
    var codes = (detail && detail.codes) || [];
    return codes[0] === 'F-4';
  }

  function injectCardCta() {
    var slot = document.querySelector('.external-guide-slot[data-guide-slot="F-4"]');
    if (!slot || slot.querySelector('.f4g-cta')) return;
    injectStyles();
    var cta = document.createElement('button');
    cta.type = 'button';
    cta.className = 'f4g-cta';
    cta.style.cssText = 'font:inherit;font-weight:800;font-size:.9rem;border-radius:10px;padding:.6rem 1.1rem;cursor:pointer;min-height:44px;border:1px solid var(--ac,#2f5e67);background:transparent;color:var(--ac,#2f5e67);margin:.5rem 0;width:100%;text-align:left;';
    cta.textContent = '🧭 F-4 재외동포 경로 찾기 — 내 상황(국적 이력·미국 신청·FBI·거소증)으로 절차 정리하기';
    cta.addEventListener('click', function () {
      var section = document.getElementById('f4RouteGuide');
      if (!section) return;
      section.hidden = false;
      mountGuide(section).then(function () {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    slot.appendChild(cta);
  }

  document.addEventListener('paradiso:results-rendered', function (e) {
    var section = document.getElementById('f4RouteGuide');
    if (!section) return;
    var detail = e.detail || {};
    if (isF4Relevant(detail)) {
      section.hidden = false;
      mountGuide(section).then(function () {
        var routeId = detectKeywordRoute(detail.query, state.data);
        if (routeId) selectRoute(section, state.data, routeId);
      });
    } else {
      section.hidden = true;
    }
    injectCardCta();
  });
  document.addEventListener('paradiso:landing-reset', function () {
    var section = document.getElementById('f4RouteGuide');
    if (section) section.hidden = true;
  });
})();
