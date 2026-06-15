/* ============================================================================
 * Paradiso — F-4 재외동포 공식 안내 허브 (Overseas Korean official-source hub)
 * ----------------------------------------------------------------------------
 * Search-first guided experience for the F-4 (재외동포) status of stay.
 *
 * Flow:
 *   1) An F-4-relevant search renders a COMPACT diagnostic entry panel into
 *      #f4RouteGuide (title: "F-4 안내를 시작하기 전에 확인해주세요"). It never
 *      auto-expands the full hub.
 *   2) The primary CTA "F-4 절차 확인하기" opens an accessible modal that begins
 *      with the guided status diagnostic (nationality → location → visa status →
 *      residence report → 90-day → country) and routes the user to one path.
 *   3) From the diagnostic result, "F-4 절차 자세히 보기" opens the full hub
 *      (재외공관 신청 / 국내거소신고 / 자격변경 / 국가별 확인 / FAQ) with a
 *      country selector. Country selection only changes country-specific guidance.
 *
 * Data (kept OUT of index.html, fetched lazily from data/f4/):
 *   base.json · diagnostic.json · faq.json · countries.json ·
 *   country_overlays.json · sources.json
 *
 * Safety contract (do not weaken):
 *  - F-4 is for FOREIGN-NATIONAL overseas Koreans. Current Korean nationals are
 *    routed to "국적/병역/자격 확인 필요", never into ordinary applicant guidance.
 *  - F-4 visa issuance and 국내거소신고/거소증 are SEPARATE procedures.
 *  - Overseas missions NEVER issue a 거소증.
 *  - The 90-day domestic residence-report deadline is never hidden.
 *  - Country-specific rules (FBI/apostille/fee/booking/processing) live in the
 *    country overlay only — never in the common view, never universalized.
 *  - Eligibility/approval is never guaranteed; source confidence is explicit.
 * ========================================================================== */
(function () {
  'use strict';

  var DATA_BASE = 'data/f4/';
  var FILES = {
    base: 'base.json',
    diagnostic: 'diagnostic.json',
    faq: 'faq.json',
    countries: 'countries.json',
    overlays: 'country_overlays.json',
    sources: 'sources.json'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  /* ---- UI strings (Korean-first; this subsystem is Korean-canonical) ------ */
  var STR = {
    loading: 'F-4 안내 데이터를 불러오는 중입니다…',
    fetchFail: 'F-4 안내 데이터를 불러오지 못했습니다. 이 안내 없이 진행하지 마시고, 관할 재외공관·하이코리아·1345에서 직접 확인해 주세요.',
    entryEyebrow: '재외동포 F-4 · 공식 출처 기반 안내',
    startCtaFallback: 'F-4 절차 확인하기',
    modalAria: 'F-4 재외동포 안내',
    close: '닫기',
    back: '← 이전',
    restart: '처음부터 다시',
    seeResult: '결과 보기',
    recommended: '추천 경로',
    why: '왜 이 경로인가요?',
    checkFirst: '먼저 확인할 것',
    nextStep: '다음 단계',
    cautions: '주의',
    officialWarn: '공식 확인 안내',
    countryGuide: '국가별 확인',
    openHub: 'F-4 절차 자세히 보기',
    backToDiagnostic: '← 진단으로 돌아가기',
    hubTitle: 'F-4 절차 안내 허브',
    selectCountryLabel: '신청 국가 또는 거주 국가를 선택하세요',
    selectCountryHint: '국가별 공관 절차, 범죄경력증명서, 인증 방식, 예약, 수수료, 처리기간은 다를 수 있습니다. 검증되지 않은 국가는 공통 F-4 기준만 안내합니다.',
    selectCountryPlaceholder: '— 국가 선택 (선택 사항) —',
    noCountrySelected: '아직 국가를 선택하지 않았습니다. 공통 F-4 기준만 표시됩니다. 국가를 선택하면 해당 국가의 공관 안내(검증된 경우)가 함께 표시됩니다.',
    commonRulesHeading: '공통 F-4 기준 (모든 국가 공통)',
    countryRulesHeading: '국가별 안내',
    docsHeading: '공통 제출서류',
    stepsHeading: '단계',
    sourcesHeading: '출처',
    notGuaranteeFootnote: '이 안내는 자격이나 허가를 보장하지 않습니다. 실제 적용 여부는 관할 재외공관·출입국·외국인관서·하이코리아(1345)에서 확인하세요.',
    badgeVerified: '공식 기준 확인됨',
    badgePartial: '일부 공식 자료',
    badgeRefresh: '공식 최신성 확인 필요',
    badgeOfficialCheck: '공식 확인 필요',
    badgeUnclear: '확인 자료 없음',
    sourceDatePrefix: '기준일'
  };

  var TAB_LABEL = {
    overview: 'F-4 한눈에 보기',
    overseasApplication: '재외공관 신청',
    residenceReport: '국내거소신고/거소증',
    statusChange: '국내 자격변경',
    country: '국가별 확인',
    faq: 'F-4 자주 묻는 질문'
  };
  var HUB_TABS = ['overview', 'overseasApplication', 'residenceReport', 'statusChange', 'country', 'faq'];

  function stateBadge(status) {
    var map = {
      verified_official: ['ok', STR.badgeVerified],
      partial_official: ['partial', STR.badgePartial],
      needs_refresh: ['refresh', STR.badgeRefresh],
      official_check_required: ['check', STR.badgeOfficialCheck],
      not_available_or_unclear: ['check', STR.badgeUnclear]
    };
    var m = map[status] || ['check', STR.badgeOfficialCheck];
    return '<span class="f4h-badge f4h-badge-' + m[0] + '">' + esc(m[1]) + '</span>';
  }

  /* ----------------------------------------------------------- module state */
  var state = {
    data: null,
    loadPromise: null,
    answers: {},
    revealed: 1,        // how many diagnostic questions are revealed
    selectedCountry: '',
    view: 'diagnostic', // 'diagnostic' | 'hub'
    hubTab: 'overview',
    modal: null,
    lastFocus: null,
    keyHandler: null
  };

  function loadAll() {
    if (state.data) return Promise.resolve(state.data);
    if (state.loadPromise) return state.loadPromise;
    var fetchJson = function (name) {
      return fetch(DATA_BASE + FILES[name], { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + name);
        return r.json();
      });
    };
    state.loadPromise = Promise.all(['base', 'diagnostic', 'faq', 'countries', 'overlays', 'sources'].map(fetchJson))
      .then(function (arr) {
        var data = { base: arr[0], diagnostic: arr[1], faq: arr[2], countries: arr[3], overlays: arr[4], sources: arr[5] };
        if (!data.base || !data.diagnostic || !data.diagnostic.questions) throw new Error('unexpected F-4 schema');
        state.data = data;
        return data;
      })
      .catch(function (e) { state.loadPromise = null; throw e; });
    return state.loadPromise;
  }

  /* ----------------------------------------------------- diagnostic routing */
  // Computes the recommended route id + optional context note from the current
  // answers. Pure function (exposed for tests). Never promises eligibility.
  function computeRoute(a) {
    a = a || {};
    var nat = a.nationality;
    // Nationality is a routing/caution check ONLY — never an eligibility gate.
    if (nat === 'korean') return { routeId: 'nationality_check', contextNote: 'nationalityKorean' };
    if (nat === 'unsure') return { routeId: 'nationality_check', contextNote: 'nationalityUnsure' };

    var loc = a.location, vs = a.visa_status, rr = a.residence_report, et = a.entry_timing;

    if (vs === 'yes_entered') {
      var noReport = (rr === 'not_yet' || rr === 'unsure' || rr == null);
      if (noReport && et === 'over90') return { routeId: 'official_check', contextNote: 'enteredNoReportOver90' };
      if (noReport) return { routeId: 'residence_report', contextNote: 'enteredNoReportUnder90' };
      return { routeId: 'residence_report' };
    }
    if (vs === 'yes_not_entered') return { routeId: 'overseas_application', contextNote: 'visaIssuedNotEntered' };

    if (loc === 'overseas_apply') return { routeId: 'overseas_application' };
    if (loc === 'need_residence_report') return { routeId: 'residence_report' };
    if (loc === 'domestic_change') return { routeId: 'status_change' };

    if (vs === 'no') return { routeId: 'overseas_application' };
    return { routeId: 'official_check' };
  }

  // Which questions are currently applicable (entry_timing is conditional).
  function applicableQuestions() {
    var qs = state.data.diagnostic.questions;
    return qs.filter(function (q) {
      if (!q.showIf) return true;
      return state.answers[q.showIf.questionId] === q.showIf.optionId;
    });
  }

  /* --------------------------------------------------------------- styling */
  function injectStyles() {
    if (document.getElementById('f4HubStyles')) return;
    var css = '' +
'.f4-route-guide{margin:1.1rem 0;}' +
'.f4h-entry{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:var(--radius-lg,16px);box-shadow:var(--sh1,0 1px 2px rgba(0,0,0,.05));padding:1rem 1.1rem;}' +
'.f4h-eyebrow{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ac,#2f5e67);font-weight:800;margin:0 0 .3rem;}' +
'.f4h-h2{font-size:1.12rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .3rem;word-break:keep-all;}' +
'.f4h-sub{font-size:.86rem;line-height:1.6;color:var(--t2,#4f5552);margin:0 0 .7rem;word-break:keep-all;}' +
'.f4h-badges{display:flex;flex-wrap:wrap;gap:.35rem;margin:.1rem 0 .7rem;}' +
'.f4h-badge{display:inline-block;font-size:.72rem;font-weight:700;padding:.16rem .5rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t2,#4f5552);background:var(--bg2,#f1ece2);}' +
'.f4h-badge-ok{border-color:var(--cSt,#0EA37B);color:var(--cSt,#0a7a5c);background:transparent;}' +
'.f4h-badge-partial{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4h-badge-refresh{border-color:var(--cWk,#E68A3A);color:var(--cWk,#a85f1c);background:transparent;}' +
'.f4h-badge-check{border-color:var(--cy,#FF6B5B);color:var(--hlT,#8A3426);background:transparent;}' +
'.f4h-cta{font:inherit;font-weight:800;font-size:.92rem;border-radius:12px;padding:.7rem 1.15rem;cursor:pointer;min-height:46px;border:1px solid var(--ac,#2f5e67);background:var(--ac,#2f5e67);color:#fff;}' +
'.f4h-cta:hover{filter:brightness(1.05);}' +
'.f4h-cta:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:2px;}' +
'.f4h-cta-help{font-size:.78rem;color:var(--t3,#757a76);margin:.5rem 0 0;word-break:keep-all;}' +
'.f4h-card-cta{font:inherit;font-weight:800;font-size:.86rem;border-radius:10px;padding:.55rem .9rem;cursor:pointer;min-height:44px;border:1px solid var(--ac,#2f5e67);background:transparent;color:var(--ac,#2f5e67);margin:.5rem 0;width:100%;text-align:left;}' +
'.f4h-card-panel{margin:.4rem 0;padding:.6rem .75rem;border:1px solid var(--bd,#d1c6b4);border-radius:12px;background:var(--bg2,#f7f3ea);}' +
'.f4h-card-panel .f4h-eyebrow{margin-bottom:.2rem;}' +
'.f4h-card-line{font-size:.82rem;color:var(--t2,#4f5552);margin:0 0 .5rem;word-break:keep-all;}' +
/* modal */
'.f4h-overlay{position:fixed;inset:0;z-index:9000;display:none;align-items:center;justify-content:center;padding:1rem;background:rgba(20,20,18,.55);}' +
'.f4h-overlay.open{display:flex;}' +
'.f4h-box{background:var(--bg1,#fff);border:1px solid var(--bd,#d1c6b4);border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.25);width:100%;max-width:640px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;}' +
'.f4h-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.6rem;padding:.95rem 1.1rem .7rem;border-bottom:1px solid var(--bd2,#e5dccb);}' +
'.f4h-head h2{font-size:1.08rem;font-weight:800;color:var(--t1,#202221);margin:.1rem 0 0;word-break:keep-all;}' +
'.f4h-close{font:inherit;font-size:1.2rem;line-height:1;border:1px solid var(--bd,#d1c6b4);background:var(--bg2,#f1ece2);color:var(--t1,#202221);border-radius:10px;min-width:40px;min-height:40px;cursor:pointer;}' +
'.f4h-close:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-body{padding:.9rem 1.1rem 1.1rem;overflow-y:auto;}' +
'.f4h-q{border:1px solid var(--bd,#d1c6b4);border-radius:12px;padding:.7rem .8rem;margin:0 0 .7rem;background:var(--bgI,#fff);}' +
'.f4h-q-title{font-size:.95rem;font-weight:800;color:var(--t1,#202221);margin:0 0 .15rem;word-break:keep-all;}' +
'.f4h-q-help{font-size:.76rem;color:var(--t3,#757a76);margin:0 0 .5rem;word-break:keep-all;}' +
'.f4h-opts{display:grid;gap:.4rem;}' +
'.f4h-opt{font:inherit;text-align:left;background:var(--bgI,#fff);border:1.5px solid var(--bd,#d1c6b4);border-radius:10px;padding:.6rem .75rem;cursor:pointer;min-height:44px;color:var(--t1,#202221);font-size:.88rem;word-break:keep-all;}' +
'.f4h-opt:hover{border-color:var(--ac,#2f5e67);}' +
'.f4h-opt:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-opt[aria-pressed="true"]{border-color:var(--ac,#2f5e67);background:var(--acG,rgba(47,94,103,.1));box-shadow:inset 0 0 0 1px var(--ac,#2f5e67);font-weight:700;}' +
'.f4h-select{font:inherit;font-size:.9rem;width:100%;min-height:46px;padding:.5rem .6rem;border:1.5px solid var(--bd,#d1c6b4);border-radius:10px;background:var(--bgI,#fff);color:var(--t1,#202221);}' +
'.f4h-result{border-top:2px solid var(--bd2,#ddd3c3);margin-top:.6rem;padding-top:.9rem;}' +
'.f4h-result h3{font-size:1.05rem;font-weight:800;color:var(--ac,#2f5e67);margin:.1rem 0 .35rem;word-break:keep-all;}' +
'.f4h-h4{font-size:.82rem;font-weight:800;color:var(--t2,#4f5552);margin:.85rem 0 .3rem;text-transform:none;}' +
'.f4h-p{font-size:.87rem;line-height:1.65;color:var(--t1,#202221);margin:.2rem 0;word-break:keep-all;}' +
'.f4h-ul{margin:.2rem 0;padding-left:1.15rem;}' +
'.f4h-ul li{font-size:.85rem;line-height:1.6;color:var(--t1,#202221);margin:.15rem 0;word-break:keep-all;}' +
'.f4h-chips{display:flex;flex-wrap:wrap;gap:.35rem;}' +
'.f4h-chip{display:inline-block;font-size:.76rem;font-weight:800;padding:.26rem .58rem;border-radius:999px;border:1.5px solid var(--ac,#2f5e67);color:var(--ac,#2f5e67);background:transparent;}' +
'.f4h-warn{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.6rem .75rem;margin:.5rem 0;}' +
'.f4h-warn .f4h-h4{color:var(--hlT,#8A3426);margin-top:0;}' +
'.f4h-warn li,.f4h-warn .f4h-p{color:var(--hlT,#8A3426);}' +
'.f4h-note{background:var(--bg2,#f1ece2);border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.6rem .75rem;margin:.5rem 0;font-size:.84rem;line-height:1.6;color:var(--t1,#202221);word-break:keep-all;}' +
'.f4h-links{display:flex;flex-wrap:wrap;gap:.45rem;margin:.6rem 0 .2rem;}' +
'.f4h-links a,.f4h-links button{display:inline-flex;align-items:center;min-height:42px;padding:.4rem .85rem;border:1px solid var(--ac,#2f5e67);border-radius:999px;font:inherit;font-size:.82rem;font-weight:700;color:var(--ac,#2f5e67);text-decoration:none;background:transparent;cursor:pointer;}' +
'.f4h-links a.primary,.f4h-links button.primary{background:var(--ac,#2f5e67);color:#fff;}' +
'.f4h-links a:hover,.f4h-links button:hover{background:var(--acG,rgba(47,94,103,.1));}' +
'.f4h-links a:focus-visible,.f4h-links button:focus-visible{outline:3px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-tabs{display:flex;flex-wrap:wrap;gap:.3rem;border-bottom:1px solid var(--bd2,#e5dccb);margin-bottom:.7rem;}' +
'.f4h-tab{font:inherit;font-size:.82rem;font-weight:700;border:none;border-bottom:2.5px solid transparent;background:transparent;color:var(--t2,#4f5552);padding:.5rem .55rem;cursor:pointer;min-height:40px;}' +
'.f4h-tab[aria-selected="true"]{color:var(--ac,#2f5e67);border-bottom-color:var(--ac,#2f5e67);}' +
'.f4h-tab:focus-visible{outline:2px solid var(--ac,#2f5e67);outline-offset:1px;}' +
'.f4h-foot{font-size:.74rem;color:var(--t3,#757a76);margin-top:.8rem;padding-top:.6rem;border-top:1px dashed var(--bd2,#ddd3c3);word-break:keep-all;}' +
'.f4h-faq details{border:1px solid var(--bd,#d1c6b4);border-radius:10px;padding:.45rem .7rem;margin:.4rem 0;background:var(--bgI,#fff);}' +
'.f4h-faq summary{cursor:pointer;font-size:.86rem;font-weight:800;color:var(--t1,#202221);min-height:34px;display:flex;align-items:center;word-break:keep-all;}' +
'.f4h-faq-group-title{font-size:.92rem;font-weight:800;color:var(--ac,#2f5e67);margin:.9rem 0 .2rem;}' +
'.f4h-tag{display:inline-block;font-size:.68rem;font-weight:700;padding:.1rem .45rem;border-radius:999px;border:1px solid var(--bd,#d1c6b4);color:var(--t3,#757a76);margin-left:.35rem;}' +
'.f4h-error{background:var(--cyL,#FFE2DB);border:1px solid var(--cy,#FF6B5B);border-radius:10px;padding:.8rem;font-size:.88rem;color:var(--hlT,#8A3426);word-break:keep-all;}' +
'body.f4h-modal-open{overflow:hidden;}' +
'@media (max-width:560px){.f4h-overlay{padding:0;align-items:flex-end;}.f4h-box{max-width:100%;max-height:94vh;border-radius:18px 18px 0 0;}}';
    var style = document.createElement('style');
    style.id = 'f4HubStyles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------------- entry panel UI */
  function entryPanelHtml(data) {
    var d = data.diagnostic;
    var b = data.base;
    return '<div class="f4h-entry">' +
      '<p class="f4h-eyebrow">' + esc(STR.entryEyebrow) + '</p>' +
      '<h2 class="f4h-h2" id="f4RouteGuideTitle">' + esc(d.title) + '</h2>' +
      '<div class="f4h-badges">' + stateBadge(b.sourceStatus) + '<span class="f4h-badge">' + esc(STR.sourceDatePrefix + ': ' + b.lastUpdated) + '</span></div>' +
      '<p class="f4h-sub">' + esc(d.intro) + '</p>' +
      '<button type="button" class="f4h-cta" data-f4h-open>' + esc(d.ctaLabel || STR.startCtaFallback) + '</button>' +
      '<p class="f4h-cta-help">' + esc(d.ctaHelper || '') + '</p>' +
      '</div>';
  }

  function mountEntryPanel(section, data, preselectCountry) {
    injectStyles();
    section.innerHTML = entryPanelHtml(data);
    var btn = section.querySelector('[data-f4h-open]');
    if (btn) btn.addEventListener('click', function () { openHubModal('diagnostic', { country: preselectCountry }); });
  }

  /* ----------------------------------------------- compact in-card CTA panel */
  function injectCardCta(preselectCountry) {
    var slot = document.querySelector('.external-guide-slot[data-guide-slot="F-4"]');
    if (!slot || slot.querySelector('.f4h-card-panel')) return;
    injectStyles();
    var d = (state.data && state.data.diagnostic) || {};
    var panel = document.createElement('div');
    panel.className = 'f4h-card-panel';
    panel.innerHTML = '<p class="f4h-eyebrow">' + esc(STR.entryEyebrow) + '</p>' +
      '<p class="f4h-card-line">' + esc(d.ctaHelper || '재외공관 신청, 국내거소신고, 자격변경 중 내 상황에 맞는 흐름을 확인합니다.') + '</p>';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'f4h-card-cta';
    btn.textContent = '🧭 ' + (d.ctaLabel || STR.startCtaFallback);
    btn.addEventListener('click', function () { openHubModal('diagnostic', { country: preselectCountry }); });
    panel.appendChild(btn);
    slot.appendChild(panel);
  }

  /* --------------------------------------------------------------- modal UI */
  function buildModalSkeleton() {
    if (state.modal) return state.modal;
    injectStyles();
    var overlay = document.createElement('div');
    overlay.className = 'f4h-overlay';
    overlay.id = 'f4HubModalOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'f4HubModalTitle');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML =
      '<div class="f4h-box" role="document">' +
        '<div class="f4h-head">' +
          '<h2 id="f4HubModalTitle"></h2>' +
          '<button type="button" class="f4h-close" data-f4h-close aria-label="' + esc(STR.close) + '">✕</button>' +
        '</div>' +
        '<div class="f4h-body" id="f4HubModalBody"></div>' +
      '</div>';
    document.body.appendChild(overlay);
    // Backdrop click closes (informational dialog, safe to dismiss).
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeHubModal(); });
    overlay.querySelector('[data-f4h-close]').addEventListener('click', closeHubModal);
    state.modal = overlay;
    return overlay;
  }

  function focusables(container) {
    return Array.prototype.slice.call(container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) { return el.offsetParent !== null || el === document.activeElement; });
  }

  function onKeydown(e) {
    if (!state.modal || !state.modal.classList.contains('open')) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeHubModal(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables(state.modal);
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function openHubModal(view, opts) {
    opts = opts || {};
    return loadAll().then(function () {
      buildModalSkeleton();
      state.lastFocus = document.activeElement;
      if (opts.country) state.selectedCountry = opts.country;
      state.view = view || 'diagnostic';
      if (state.view === 'diagnostic') { state.answers = {}; state.revealed = 1; }
      render();
      state.modal.classList.add('open');
      state.modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('f4h-modal-open');
      if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
      var closeBtn = state.modal.querySelector('[data-f4h-close]');
      if (closeBtn) closeBtn.focus();
    }).catch(function () {
      buildModalSkeleton();
      var body = state.modal.querySelector('#f4HubModalBody');
      state.modal.querySelector('#f4HubModalTitle').textContent = 'F-4 안내';
      body.innerHTML = '<div class="f4h-error">' + esc(STR.fetchFail) + '</div>' +
        '<div class="f4h-links"><a href="https://overseas.mofa.go.kr" target="_blank" rel="noopener noreferrer">관할 재외공관 찾기</a>' +
        '<a href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">HiKorea 확인하기</a>' +
        '<a href="tel:1345">1345 확인 권장</a></div>';
      state.modal.classList.add('open');
      state.modal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('f4h-modal-open');
      if (!state.keyHandler) { state.keyHandler = onKeydown; document.addEventListener('keydown', state.keyHandler, true); }
      state.modal.querySelector('[data-f4h-close]').focus();
    });
  }

  function closeHubModal() {
    if (!state.modal) return;
    state.modal.classList.remove('open');
    state.modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('f4h-modal-open');
    if (state.keyHandler) { document.removeEventListener('keydown', state.keyHandler, true); state.keyHandler = null; }
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') {
      try { state.lastFocus.focus(); } catch (e) {}
    }
    state.lastFocus = null;
  }

  /* ------------------------------------------------------------- rendering */
  function render() {
    if (!state.modal) return;
    var titleEl = state.modal.querySelector('#f4HubModalTitle');
    var body = state.modal.querySelector('#f4HubModalBody');
    if (state.view === 'hub') {
      titleEl.textContent = STR.hubTitle;
      body.innerHTML = renderHub();
      wireHub(body);
    } else {
      titleEl.textContent = state.data.diagnostic.title;
      body.innerHTML = renderDiagnostic();
      wireDiagnostic(body);
    }
    body.scrollTop = 0;
  }

  function ctaButtonsHtml(ctaIds) {
    var cat = state.data.diagnostic.ctaCatalog || {};
    return (ctaIds || []).map(function (id) {
      var c = cat[id];
      if (!c) return '';
      if (c.action === 'open-hub') {
        return '<button type="button" class="primary" data-f4h-openhub>' + esc(c.labelKo) + '</button>';
      }
      var ext = c.external ? ' target="_blank" rel="noopener noreferrer"' : '';
      return '<a href="' + esc(c.url) + '"' + ext + '>' + esc(c.labelKo) + '</a>';
    }).join('');
  }

  function countrySelectHtml() {
    var byRegion = {};
    state.data.countries.countries.forEach(function (c) {
      (byRegion[c.region] = byRegion[c.region] || []).push(c);
    });
    var groups = Object.keys(byRegion).map(function (region) {
      var opts = byRegion[region].map(function (c) {
        var sel = c.countryCode === state.selectedCountry ? ' selected' : '';
        return '<option value="' + esc(c.countryCode) + '"' + sel + '>' + esc(c.labelKo) + ' (' + esc(c.labelEn) + ')</option>';
      }).join('');
      return '<optgroup label="' + esc(region) + '">' + opts + '</optgroup>';
    }).join('');
    return '<label class="f4h-h4" for="f4hCountrySelect">' + esc(STR.selectCountryLabel) + '</label>' +
      '<p class="f4h-q-help">' + esc(STR.selectCountryHint) + '</p>' +
      '<select class="f4h-select" id="f4hCountrySelect" data-f4h-country>' +
        '<option value="">' + esc(STR.selectCountryPlaceholder) + '</option>' + groups +
      '</select>';
  }

  // -------- diagnostic view
  function renderDiagnostic() {
    var d = state.data.diagnostic;
    var qs = applicableQuestions();
    var html = '';
    var routeReady = false;
    for (var i = 0; i < qs.length && i < state.revealed; i++) {
      var q = qs[i];
      if (q.type === 'country') {
        html += '<div class="f4h-q">' + countrySelectHtml() + '</div>';
        continue;
      }
      var picked = state.answers[q.id];
      var opts = q.options.map(function (o) {
        var pressed = picked === o.id ? 'true' : 'false';
        return '<button type="button" class="f4h-opt" data-f4h-answer data-q="' + esc(q.id) + '" data-o="' + esc(o.id) + '" aria-pressed="' + pressed + '">' + esc(o.label) + '</button>';
      }).join('');
      html += '<div class="f4h-q">' +
        '<p class="f4h-q-title">' + esc(q.question) + '</p>' +
        (q.help ? '<p class="f4h-q-help">' + esc(q.help) + '</p>' : '') +
        '<div class="f4h-opts" role="group" aria-label="' + esc(q.question) + '">' + opts + '</div>' +
      '</div>';
    }
    // Determine whether we can show a result.
    var forced = (state.answers.nationality === 'korean' || state.answers.nationality === 'unsure');
    var enough = forced || (state.answers.nationality === 'foreign' &&
      (state.answers.location || state.answers.visa_status));
    if (enough) { routeReady = true; html += renderResult(); }
    if (!routeReady) {
      html += '<p class="f4h-cta-help">위 질문에 답하면 추천 경로가 나타납니다.</p>';
    }
    html += '<p class="f4h-foot">' + esc(STR.notGuaranteeFootnote) + '</p>';
    return html;
  }

  function renderResult() {
    var d = state.data.diagnostic;
    var r = computeRoute(state.answers);
    var route = d.routes[r.routeId];
    if (!route) return '';
    var note = r.contextNote ? d.contextNotes[r.contextNote] : '';
    var html = '<div class="f4h-result" role="status" aria-live="polite">' +
      '<p class="f4h-eyebrow">' + esc(STR.recommended) + '</p>' +
      '<h3>' + esc(route.title) + '</h3>' +
      '<p class="f4h-p">' + esc(route.recommended) + '</p>';
    if (note) html += '<div class="f4h-note">' + esc(note) + '</div>';
    html += '<p class="f4h-h4">' + esc(STR.why) + '</p><p class="f4h-p">' + esc(route.why) + '</p>';
    if (route.checkFirst && route.checkFirst.length) {
      html += '<p class="f4h-h4">' + esc(STR.checkFirst) + '</p><div class="f4h-chips">' +
        route.checkFirst.map(function (c) { return '<span class="f4h-chip">' + esc(c) + '</span>'; }).join('') + '</div>';
    }
    if (route.warnings && route.warnings.length) {
      html += '<div class="f4h-warn"><p class="f4h-h4">' + esc(STR.cautions) + '</p><ul class="f4h-ul">' +
        route.warnings.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join('') + '</ul></div>';
    }
    // Country-specific guidance (only if a country is selected).
    html += renderCountryResultBlock();
    // Official-source warning.
    html += '<div class="f4h-note">' + esc(state.data.base.common.officialCheckWarning) + '</div>';
    html += '<div class="f4h-links">' + ctaButtonsHtml(route.ctas) + '</div>';
    html += '</div>';
    return html;
  }

  function getOverlay(code) {
    var ov = state.data.overlays && state.data.overlays.overlays;
    return (ov && ov[code]) || null;
  }
  function getCountry(code) {
    var found = null;
    state.data.countries.countries.forEach(function (c) { if (c.countryCode === code) found = c; });
    return found;
  }

  function renderCountryResultBlock() {
    if (!state.selectedCountry) return '';
    var c = getCountry(state.selectedCountry);
    if (!c) return '';
    var ov = getOverlay(state.selectedCountry);
    var html = '<p class="f4h-h4">' + esc(STR.countryGuide) + ' · ' + esc(c.labelKo) + '</p>';
    if (!ov) {
      html += '<div class="f4h-note">' + stateBadge('official_check_required') + '<br>' + esc(state.data.base.fallbackUnverifiedCountry) + '</div>';
      return html;
    }
    html += '<div class="f4h-note">' + stateBadge(ov.sourceStatus) + ' ' + esc(c.labelKo) + ' — ' + esc(ov.sourceStatusReason || '') + '</div>';
    return html;
  }

  function wireDiagnostic(body) {
    body.querySelectorAll('[data-f4h-answer]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var qid = btn.dataset.q, oid = btn.dataset.o;
        state.answers[qid] = oid;
        // Reveal the next question (advance one step). Forced-route answers still
        // reveal so the user can optionally pick a country.
        var qs = applicableQuestions();
        var idx = -1;
        qs.forEach(function (q, i) { if (q.id === qid) idx = i; });
        if (idx + 1 >= state.revealed) state.revealed = Math.min(qs.length, idx + 2);
        render();
      });
    });
    var sel = body.querySelector('[data-f4h-country]');
    if (sel) sel.addEventListener('change', function () { state.selectedCountry = sel.value; render(); });
    body.querySelectorAll('[data-f4h-openhub]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var r = computeRoute(state.answers);
        var route = state.data.diagnostic.routes[r.routeId];
        state.hubTab = (route && route.hubTab) || 'overview';
        state.view = 'hub';
        render();
        var closeBtn = state.modal.querySelector('[data-f4h-close]');
        if (closeBtn) closeBtn.focus();
      });
    });
  }

  // -------- hub view
  function srcLine(refs) {
    if (!refs || !refs.length) return '';
    var byId = {};
    (state.data.sources.sources || []).forEach(function (s) { byId[s.id] = s; });
    var titles = refs.map(function (id) {
      var s = byId[id];
      return s ? esc(s.title) + (s.sourceDate ? ' (' + esc(s.sourceDate) + ')' : '') : esc(id);
    });
    return '<p class="f4h-foot">' + esc(STR.sourcesHeading) + ': ' + titles.join(' · ') + '</p>';
  }

  function renderHub() {
    var tabs = HUB_TABS.map(function (t) {
      var sel = t === state.hubTab ? 'true' : 'false';
      return '<button type="button" class="f4h-tab" role="tab" aria-selected="' + sel + '" data-f4h-tab="' + t + '">' + esc(TAB_LABEL[t]) + '</button>';
    }).join('');
    var html = '<div class="f4h-links" style="margin-top:0;"><button type="button" data-f4h-back>' + esc(STR.backToDiagnostic) + '</button></div>' +
      '<div class="f4h-tabs" role="tablist" aria-label="' + esc(STR.hubTitle) + '">' + tabs + '</div>' +
      '<div role="tabpanel">' + renderHubTab(state.hubTab) + '</div>';
    return html;
  }

  function listHtml(arr) {
    return '<ul class="f4h-ul">' + (arr || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
  }

  function commonRulesHtml() {
    var c = state.data.base.common;
    return '<div class="f4h-warn"><p class="f4h-h4">' + esc(STR.commonRulesHeading) + '</p>' +
      '<ul class="f4h-ul">' +
        '<li>' + esc(c.separationWarning) + '</li>' +
        '<li>' + esc(c.deadline90) + '</li>' +
        '<li>' + esc(c.militaryCaution) + '</li>' +
      '</ul></div>';
  }

  function renderHubTab(tab) {
    var b = state.data.base;
    if (tab === 'overview') {
      var ov = b.hub.overview;
      return '<h3 class="f4h-result" style="border:none;margin:0;padding:0;">' + esc(ov.title) + '</h3>' +
        '<p class="f4h-p">' + esc(ov.summary) + '</p>' + listHtml(ov.points) +
        '<p class="f4h-h4">' + esc(b.common.whoTitle) + '</p>' + listHtml(b.common.who) +
        '<p class="f4h-h4">' + esc(b.common.notForTitle) + '</p>' + listHtml(b.common.notFor) +
        commonRulesHtml() + srcLine(ov.sourceRefs);
    }
    if (tab === 'overseasApplication') {
      var s = b.hub.overseasApplication;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(s.title) + '</h3>' +
        '<p class="f4h-p">' + esc(s.intro) + '</p>' +
        '<p class="f4h-h4">' + esc(STR.stepsHeading) + '</p>' + listHtml(s.steps) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(s.commonDocs) +
        '<div class="f4h-note">' + esc(s.note) + '</div>' +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">관할 재외공관 찾기</a>' +
        '<a href="' + esc(b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">비자포털 확인하기</a></div>' +
        srcLine(s.sourceRefs);
    }
    if (tab === 'residenceReport') {
      var rr = b.hub.residenceReport;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(rr.title) + '</h3>' +
        '<p class="f4h-p">' + esc(rr.intro) + '</p>' +
        '<div class="f4h-warn"><p class="f4h-p">' + esc(rr.warning) + '</p></div>' +
        '<p class="f4h-h4">' + esc(STR.stepsHeading) + '</p>' + listHtml(rr.steps) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(rr.docs) +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">HiKorea 확인하기</a>' +
        '<a href="tel:1345">1345 확인 권장</a></div>' +
        srcLine(rr.sourceRefs);
    }
    if (tab === 'statusChange') {
      var sc = b.hub.statusChange;
      return '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(sc.title) + '</h3>' +
        '<p class="f4h-p">' + esc(sc.intro) + '</p>' +
        '<p class="f4h-h4">조건</p>' + listHtml(sc.conditions) +
        '<p class="f4h-h4">' + esc(STR.docsHeading) + '</p>' + listHtml(sc.docs) +
        '<div class="f4h-note">' + esc(sc.h2Note) + '</div>' +
        '<div class="f4h-note">' + esc(sc.note) + '</div>' +
        '<div class="f4h-links"><a href="' + esc(b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">HiKorea 확인하기</a>' +
        '<a href="tel:1345">1345 확인 권장</a></div>' +
        srcLine(sc.sourceRefs);
    }
    if (tab === 'country') return renderCountryTab();
    if (tab === 'faq') return renderFaqTab();
    return '';
  }

  function sectionFieldHtml(label, field) {
    if (!field) return '';
    var html = '<p class="f4h-h4">' + esc(label) + ' ' + stateBadge(field.status) + '</p>';
    if (field.summaryKo) html += '<p class="f4h-p">' + esc(field.summaryKo) + '</p>';
    if (field.detailKo && field.detailKo.length) html += listHtml(field.detailKo);
    return html;
  }

  function renderCountryTab() {
    var b = state.data.base;
    var html = '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(STR.countryGuide) + '</h3>' +
      '<div class="f4h-q">' + countrySelectHtml() + '</div>';
    // Common rules ALWAYS stay visibly separate from country specifics.
    html += commonRulesHtml();
    if (!state.selectedCountry) {
      html += '<div class="f4h-note">' + esc(STR.noCountrySelected) + '</div>';
      return html;
    }
    var c = getCountry(state.selectedCountry);
    var ov = getOverlay(state.selectedCountry);
    html += '<p class="f4h-h4">' + esc(STR.countryRulesHeading) + ' · ' + esc(c ? c.labelKo : state.selectedCountry) + '</p>';
    if (!ov) {
      html += '<div class="f4h-note">' + stateBadge('official_check_required') + '<br>' + esc(b.fallbackUnverifiedCountry) + '</div>';
      html += '<div class="f4h-links"><a href="' + esc(b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">관할 재외공관 찾기</a>' +
        '<a href="' + esc(b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">비자포털 확인하기</a>' +
        '<a href="tel:1345">1345 확인 권장</a></div>';
      return html;
    }
    html += '<div class="f4h-note">' + stateBadge(ov.sourceStatus) + ' ' + esc(ov.sourceStatusReason || '') + '</div>';
    html += sectionFieldHtml('범죄경력증명서', ov.criminalRecord);
    html += sectionFieldHtml('문서 인증(아포스티유/영사확인)', ov.authentication);
    html += sectionFieldHtml('예약', ov.booking);
    html += sectionFieldHtml('수수료(사증 수수료)', ov.fee);
    html += sectionFieldHtml('처리기간', ov.processingTime);
    html += sectionFieldHtml('공관 실무', ov.missionPractice);
    if (ov.warnings && ov.warnings.length) {
      html += '<div class="f4h-warn"><p class="f4h-h4">' + esc(STR.cautions) + '</p>' + listHtml(ov.warnings) + '</div>';
    }
    var links = '<div class="f4h-links">';
    if (ov.missionUrl) links += '<a href="' + esc(ov.missionUrl) + '" target="_blank" rel="noopener noreferrer">공관 안내 페이지</a>';
    links += '<a href="' + esc(ov.missionFinderUrl || b.ctaLinks.missionFinder.url) + '" target="_blank" rel="noopener noreferrer">관할 재외공관 찾기</a>' +
      '<a href="' + esc(ov.visaPortalUrl || b.ctaLinks.visaPortal.url) + '" target="_blank" rel="noopener noreferrer">비자포털 확인하기</a>' +
      '<a href="' + esc(ov.hikoreaUrl || b.ctaLinks.hikorea.url) + '" target="_blank" rel="noopener noreferrer">HiKorea 확인하기</a>' +
      '<a href="tel:1345">1345 확인 권장</a></div>';
    html += links;
    html += srcLine(ov.sourceRefs);
    return html;
  }

  function renderFaqTab() {
    var faq = state.data.faq;
    var html = '<h3 style="margin:.1rem 0 .3rem;color:var(--ac,#2f5e67);">' + esc(faq.title) + '</h3>';
    faq.groups.forEach(function (g) {
      html += '<p class="f4h-faq-group-title">' + esc(g.title) + '</p><div class="f4h-faq">';
      g.items.forEach(function (it) {
        var tags = '';
        if (it.countryVaries) tags += '<span class="f4h-tag">국가별 상이</span>';
        if (it.officialCheck) tags += '<span class="f4h-tag">공식 확인</span>';
        html += '<details><summary>' + esc(it.q) + tags + '</summary>' +
          '<p class="f4h-p">' + esc(it.a) + '</p>' + srcLine(it.sourceRefs) + '</details>';
      });
      html += '</div>';
    });
    return html;
  }

  function wireHub(body) {
    body.querySelectorAll('[data-f4h-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.hubTab = btn.dataset.f4hTab; render(); });
    });
    body.querySelectorAll('[data-f4h-back]').forEach(function (btn) {
      btn.addEventListener('click', function () { state.view = 'diagnostic'; render(); });
    });
    var sel = body.querySelector('[data-f4h-country]');
    if (sel) sel.addEventListener('change', function () { state.selectedCountry = sel.value; render(); });
  }

  /* ----------------------------------------------------- public API (tests) */
  var api = {
    STR: STR,
    loadAll: loadAll,
    computeRoute: computeRoute,
    openHubModal: openHubModal,
    closeHubModal: closeHubModal,
    stateBadge: stateBadge,
    _state: state
  };
  if (typeof globalThis !== 'undefined') globalThis.ParadisoF4Guide = api;

  if (typeof document === 'undefined') return;

  /* ----------------------------------------------- search-result integration */
  var F4_QUERY = /f-?4|재외동포|동포\s*비자/i;
  var EXTRA_TRIGGERS = ['거소증', '국내거소', '거소신고', 'fbi', '범죄경력', '아포스티유', '영사확인',
    '국적상실', '복수국적', '병역', '이중국적', '자격변경', '재외공관', '국내거소신고'];

  function isF4Relevant(detail) {
    var q = String((detail && detail.query) || '');
    if (F4_QUERY.test(q)) return true;
    var lower = q.toLowerCase();
    for (var i = 0; i < EXTRA_TRIGGERS.length; i++) {
      if (lower.indexOf(EXTRA_TRIGGERS[i]) !== -1) return true;
    }
    var codes = (detail && detail.codes) || [];
    return codes[0] === 'F-4' || (detail && detail.primaryCode === 'F-4');
  }

  // Detect a country mentioned in the query (e.g., "미국 F-4") to preselect.
  function detectCountry(query) {
    if (!state.data) return '';
    var q = String(query || '').toLowerCase();
    var hit = '';
    state.data.countries.countries.forEach(function (c) {
      if (hit) return;
      if (q.indexOf(c.labelKo) !== -1 || (c.labelEn && q.indexOf(c.labelEn.toLowerCase()) !== -1)) hit = c.countryCode;
    });
    return hit;
  }

  document.addEventListener('paradiso:results-rendered', function (e) {
    var section = document.getElementById('f4RouteGuide');
    if (!section) return;
    var detail = e.detail || {};
    if (!isF4Relevant(detail)) { section.hidden = true; return; }
    section.hidden = false;
    loadAll().then(function (data) {
      var preselect = detectCountry(detail.query);
      mountEntryPanel(section, data, preselect);
      injectCardCta(preselect);
    }).catch(function () {
      injectStyles();
      section.innerHTML = '<div class="f4h-entry"><div class="f4h-error">' + esc(STR.fetchFail) + '</div>' +
        '<div class="f4h-links" style="margin-top:.5rem;">' +
          '<a href="https://overseas.mofa.go.kr" target="_blank" rel="noopener noreferrer">관할 재외공관 찾기</a>' +
          '<a href="https://www.hikorea.go.kr" target="_blank" rel="noopener noreferrer">HiKorea 확인하기</a>' +
          '<a href="tel:1345">1345 확인 권장</a>' +
        '</div></div>';
    });
  });

  document.addEventListener('paradiso:landing-reset', function () {
    var section = document.getElementById('f4RouteGuide');
    if (section) section.hidden = true;
    if (state.modal && state.modal.classList.contains('open')) closeHubModal();
  });
})();
