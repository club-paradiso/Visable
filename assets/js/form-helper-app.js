/*
 * Visable Form Helper 2.0 — page application (form-helper.html).
 *
 * Screens: home (search + task groups) → explain → edit (step rail + fields + live
 * preview) → review → preview / export. Browser Back walks the same screens with
 * every value kept in memory. Nothing typed here leaves the browser: the only
 * network requests are the static data files, the template PDF, the font and the
 * two PDF libraries; there is no analytics call and no storage of form values.
 *
 * All rendering, validation and PDF placement go through assets/js/form-engine.js
 * so the preview canvas and the exported PDF draw the identical operations.
 */
(function () {
  'use strict';
  var E = window.VisableFormEngine;
  if (!E) return;

  /* ── constants ─────────────────────────────────────────────────────────── */
  var LOCALES = ['ko', 'en', 'zh-CN', 'zh-TW', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de', 'tr', 'uk'];
  var LABELS = { ko: '한국어', en: 'English', 'zh-CN': '简体中文', 'zh-TW': '繁體中文', ja: '日本語', vi: 'Tiếng Việt', tl: 'Tagalog', id: 'Bahasa Indonesia', ru: 'Русский', fr: 'Français', es: 'Español', ar: 'العربية', de: 'Deutsch', tr: 'Türkçe', uk: 'Українська' };
  var MOBILE_QUERY = '(max-width: 900px)';
  var PREVIEW_SCALE = 1.5; // assets/forms/preview/*.png are rendered at 1.5× (see form_schemas._meta.preview)

  /* ── state ─────────────────────────────────────────────────────────────── */
  var data = { defs: null, schemas: null, inventory: null, charset: null, packs: {}, manifest: null };
  var st = { lang: 'ko', screen: 'home', formId: null, values: {}, stepIndex: 0, ops: [], issues: [], validation: [], query: '', from: null, zoom: 1, focusKey: null, pageImages: {}, fontReady: false, measure: null, glyphs: null, dirtyForms: {} };
  var app = {};
  var els = {};

  /* ── i18n ──────────────────────────────────────────────────────────────── */
  function packFor(lang) { return data.packs[lang === 'zh-TW' ? 'zh-CN' : lang] || data.packs.ko || {}; }
  function t(key, vars) {
    var pack = packFor(st.lang), fh = pack.fh || {}, ko = (data.packs.ko && data.packs.ko.fh) || {};
    var s = fh[key] != null ? fh[key] : (ko[key] != null ? ko[key] : key);
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split('{' + k + '}').join(String(vars[k])); });
    if (st.lang === 'zh-TW' && window.ParadisoZhT) s = window.ParadisoZhT.convert(s);
    return s;
  }
  function L(obj) { return E.pick(obj, st.lang === 'zh-TW' ? 'zh-CN' : st.lang); }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') el.textContent = attrs[k];
      else if (k === 'html') el.innerHTML = attrs[k];
      else if (k.indexOf('on') === 0 && typeof attrs[k] === 'function') el.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] === false || attrs[k] == null) {}
      else el.setAttribute(k, attrs[k] === true ? '' : attrs[k]);
    });
    (children || []).forEach(function (c) { if (c == null || c === false) return; el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return el;
  }
  function isMobile() { return window.matchMedia(MOBILE_QUERY).matches; }

  /* ── loading ───────────────────────────────────────────────────────────── */
  function fetchJson(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); }
  function readLang() {
    var q = new URLSearchParams(location.search).get('lang');
    if (q && LOCALES.indexOf(q) >= 0) return q;
    try { var s = localStorage.getItem('paradiso:language') || ''; if (LOCALES.indexOf(s) >= 0) return s; } catch (e) {}
    return 'ko';
  }
  function loadPack(lang) {
    var file = lang === 'zh-TW' ? 'zh-CN' : lang;
    if (data.packs[file]) return Promise.resolve();
    return fetchJson('data/i18n/' + file + '.json').then(function (p) { data.packs[file] = p; }).catch(function () {});
  }
  function loadFont() {
    if (!window.FontFace) return Promise.resolve(false);
    var ff = new FontFace('VisableNanum', 'url(assets/forms/fonts/NanumGothic-Regular.ttf)');
    return ff.load().then(function (f) { document.fonts.add(f); st.fontReady = true; return true; }).catch(function () { return false; });
  }
  function makeMeasure() {
    var c = document.createElement('canvas'); var ctx = c.getContext('2d');
    var cache = {};
    return function (text, size) {
      var k = size + '|' + text;
      if (cache[k] != null) return cache[k];
      ctx.font = size + 'px ' + (st.fontReady ? 'VisableNanum' : 'sans-serif');
      var w = ctx.measureText(text).width;
      if (!st.fontReady) w *= 1.04;
      cache[k] = w; return w;
    };
  }

  /* ── router ────────────────────────────────────────────────────────────── */
  function hashFor(s) {
    var p = [];
    if (s.formId) p.push('form=' + s.formId);
    if (s.screen && s.screen !== 'home') p.push('screen=' + s.screen);
    if (s.screen === 'edit') p.push('step=' + s.stepIndex);
    return p.length ? '#' + p.join('&') : location.pathname;
  }
  function go(screen, opts, replace) {
    opts = opts || {};
    if (opts.formId !== undefined) st.formId = opts.formId;
    if (opts.stepIndex !== undefined) st.stepIndex = opts.stepIndex;
    st.screen = screen;
    var state = { screen: screen, formId: st.formId, stepIndex: st.stepIndex };
    try { history[replace ? 'replaceState' : 'pushState'](state, '', hashFor(state)); } catch (e) {}
    render();
    window.scrollTo({ top: 0, behavior: 'auto' });
  }
  window.addEventListener('popstate', function (ev) {
    var s = ev.state || parseHash();
    st.screen = s.screen || 'home'; st.formId = s.formId || st.formId; st.stepIndex = s.stepIndex || 0;
    if (st.formId && !st.values[st.formId]) ensureValues(st.formId);
    if (st.screen !== 'home' && !st.formId) st.screen = 'home';
    render();
  });
  function parseHash() {
    var out = { screen: 'home', formId: null, stepIndex: 0 };
    var hp = new URLSearchParams(location.hash.replace(/^#/, ''));
    if (hp.get('form') && data.defs.forms[hp.get('form')]) out.formId = hp.get('form');
    if (hp.get('screen')) out.screen = hp.get('screen');
    if (hp.get('step')) out.stepIndex = parseInt(hp.get('step'), 10) || 0;
    return out;
  }

  /* ── model helpers ────────────────────────────────────────────────────── */
  function form() { return st.formId ? data.defs.forms[st.formId] : null; }
  function values() { return st.values[st.formId]; }
  function ensureValues(fid) { if (!st.values[fid]) st.values[fid] = E.initialValues(data.defs.forms[fid]); return st.values[fid]; }
  function edition() { return E.editionOf(form(), values()); }
  function spec() { return data.schemas.forms[edition()]; }
  function labelsByOverlay() {
    var f = form(), map = E.overlayToField(f), out = {};
    var byKey = {}; f.fields.forEach(function (x) { byKey[x.key] = x; });
    Object.keys(map).forEach(function (ok) { out[ok] = byKey[map[ok]] ? L(byKey[map[ok]].label) : ok; });
    return out;
  }
  function recompute() {
    var f = form(); if (!f) return;
    var v = values();
    var ov = E.overlayValues(f, v);
    var lay = E.layout(spec(), ov, st.measure, st.glyphs, labelsByOverlay());
    var o2f = E.overlayToField(f);
    lay.ops.forEach(function (op) { op.field = o2f[op.key] || op.key; });
    lay.issues.forEach(function (i) { i.field = o2f[i.key] || i.key; });
    st.ops = lay.ops; st.issues = lay.issues;
    st.validation = E.validate(f, v, st.lang, t);
    st.dirtyForms[st.formId] = f.fields.some(function (x) { var d = E.initialValues(f)[x.key]; return x.type !== 'note' && !E.isEmpty(v[x.key]) && v[x.key] !== d; });
  }
  function setValue(fieldDef, raw) {
    var v = values();
    v[fieldDef.key] = E.normalizeValue(fieldDef, raw);
    recompute();
    schedulePreview();
    updateRail();
  }

  /* ── render root ──────────────────────────────────────────────────────── */
  function render() {
    document.documentElement.lang = st.lang;
    document.documentElement.dir = st.lang === 'ar' ? 'rtl' : 'ltr';
    document.title = t('title') + ' — Visable';
    renderChrome();
    ['home', 'explain', 'edit', 'review', 'preview'].forEach(function (s) { els[s].hidden = st.screen !== s; });
    closeSheet();
    if (st.screen === 'home') renderHome();
    else if (st.screen === 'explain') renderExplain();
    else if (st.screen === 'edit') renderEdit();
    else if (st.screen === 'review') renderReview();
    else if (st.screen === 'preview') renderPreviewScreen();
    document.body.classList.toggle('fh-in-form', st.screen === 'edit');
  }
  function renderChrome() {
    els.backLink.textContent = t('back');
    els.privacy.textContent = t('privacyShort');
    els.langSelect.setAttribute('aria-label', t('langLabel'));
    els.themeBtn.setAttribute('aria-label', t('themeToggle'));
    els.footerLegal.textContent = t('legal');
    els.footerLine.textContent = t('footer');
    els.skip.textContent = t('back');
    els.brandTitle.textContent = t('title');
  }

  /* ── HOME ─────────────────────────────────────────────────────────────── */
  var searchIndex = null;
  function renderHome() {
    var root = els.home; root.innerHTML = '';
    var inv = data.inventory || {};
    var cov = { supported: (inv.supported_now || []).length, partial: (inv.partial_now || []).length, total: (inv.inventory || []).length };
    root.appendChild(h('div', { 'class': 'fh-hero' }, [
      h('p', { 'class': 'fh-kicker', text: 'Visable' }),
      h('h1', { 'class': 'fh-h1', text: t('title') }),
      h('p', { 'class': 'fh-lead', text: t('tagline') }),
    ]));
    var input = h('input', { 'class': 'fh-search-input', type: 'search', id: 'fhSearch', placeholder: t('searchPlaceholder'), autocomplete: 'off', value: st.query, 'aria-label': t('searchLabel') });
    var results = h('div', { 'class': 'fh-results', id: 'fhResults', role: 'region', 'aria-live': 'polite', 'aria-label': t('results') });
    var box = h('section', { 'class': 'fh-search', 'aria-label': t('searchLabel') }, [
      h('label', { 'class': 'fh-search-label', 'for': 'fhSearch', text: t('searchLabel') }),
      h('div', { 'class': 'fh-search-row' }, [h('span', { 'class': 'fh-search-icon', 'aria-hidden': 'true' }), input]),
      h('p', { 'class': 'fh-search-hint', text: t('searchHint') }),
      results,
    ]);
    root.appendChild(box);
    input.addEventListener('input', function () { st.query = input.value; renderResults(results); });
    renderResults(results);
    // task groups
    var groups = h('section', { 'class': 'fh-groups', 'aria-labelledby': 'fhGroupsTitle' }, [h('h2', { id: 'fhGroupsTitle', 'class': 'fh-h2', text: t('groupsTitle') })]);
    data.defs.groups.forEach(function (g) {
      var members = Object.keys(data.defs.forms).filter(function (fid) { return (data.defs.forms[fid].groups || []).indexOf(g.id) >= 0; });
      if (!members.length) return;
      var list = h('div', { 'class': 'fh-cards' });
      members.forEach(function (fid) { list.appendChild(formCard(fid)); });
      groups.appendChild(h('div', { 'class': 'fh-group' }, [h('h3', { 'class': 'fh-h3', text: L(g.label) }), h('p', { 'class': 'fh-muted', text: L(g.lead) }), list]));
    });
    root.appendChild(groups);
    root.appendChild(h('p', { 'class': 'fh-coverage' }, [
      h('span', { text: t('coverageLine', cov) }), ' ',
      h('a', { href: 'docs/forms_official/FORM_HELPER_COVERAGE_20260923.md', text: t('coverageLink') }), ' · ',
      h('span', { 'class': 'fh-muted', text: t('noAutoFill') }),
    ]));
    if (st.from) {
      root.insertBefore(h('aside', { 'class': 'fh-waymaker', role: 'note' }, [h('strong', { text: t('waymakerFrom') }), ' ', h('span', { text: [st.from.visa, st.from.procedure].filter(Boolean).join(' · ') }), ' ', h('a', { href: 'ai.html?nav=1', text: t('backToWaymaker') })]), box);
    }
  }
  function statusChip(status, cls) {
    var key = { FILLABLE: 'statusFillable', SUPPORTED: 'statusFillable', PARTIAL: 'statusPartial', BLOCKED: 'statusBlocked', EXCLUDED: cls === 'excluded_refugee' ? 'statusExcludedRefugee' : 'statusExcludedDeparture', NOT_APPLICABLE: 'statusOfficial' }[status] || 'statusBlocked';
    var tone = (status === 'FILLABLE' || status === 'SUPPORTED') ? 'ok' : status === 'PARTIAL' ? 'mid' : status === 'EXCLUDED' ? 'no' : 'off';
    return h('span', { 'class': 'fh-chip fh-chip-' + tone, text: t(key) });
  }
  function supportStatus(fid) {
    var f = data.defs.forms[fid]; var s = data.schemas.forms[f.schema];
    var stt = (s.support && s.support.status) || 'PARTIAL';
    return stt === 'SUPPORTED' ? 'FILLABLE' : 'PARTIAL';
  }
  function formCard(fid) {
    var f = data.defs.forms[fid];
    var dirty = !!st.dirtyForms[fid];
    return h('button', { 'class': 'fh-card', type: 'button', 'data-form': fid, onclick: function () { openForm(fid); } }, [
      h('span', { 'class': 'fh-card-top' }, [statusChip(supportStatus(fid)), dirty ? h('span', { 'class': 'fh-chip fh-chip-dirty', text: t('dirty') }) : null]),
      h('span', { 'class': 'fh-card-title', text: L(f.short) || L(f.name) }),
      h('span', { 'class': 'fh-card-sub', text: L(f.name) !== L(f.short) ? L(f.name) : L(f.number) }),
      h('span', { 'class': 'fh-card-num', text: L(f.number) }),
    ]);
  }
  function renderResults(container) {
    container.innerHTML = '';
    var q = (st.query || '').trim();
    if (!q) return;
    if (!searchIndex) searchIndex = E.buildSearchIndex(data.defs, data.inventory, st.lang);
    var hits = E.search(searchIndex, q, 10);
    if (!hits.length) { container.appendChild(h('p', { 'class': 'fh-empty', text: t('searchNone') })); return; }
    var list = h('ul', { 'class': 'fh-result-list' });
    hits.forEach(function (r) {
      var e = r.entry;
      if (e.kind === 'form') {
        var f = e.form;
        list.appendChild(h('li', {}, [h('button', { 'class': 'fh-result', type: 'button', 'data-form': e.id, onclick: function () { openForm(e.id); } }, [
          statusChip(supportStatus(e.id)), h('span', { 'class': 'fh-result-title', text: L(f.name) }), h('span', { 'class': 'fh-result-sub', text: L(f.number) })])]));
      } else {
        var it = e.item;
        var cls = it['class'];
        var body = cls === 'excluded_refugee' || cls === 'excluded_departure' ? t('handoffExcluded') : (cls === 'official_use' || cls === 'enforcement') ? t('handoffOfficial') : t('handoffBlocked');
        list.appendChild(h('li', {}, [h('div', { 'class': 'fh-result fh-result-static' }, [
          statusChip(it.status, cls), h('span', { 'class': 'fh-result-title', text: it.title }), h('span', { 'class': 'fh-result-sub', text: t('annexOf', { law: it.source === 'overseas_koreans_rule' ? t('lawOverseas') : t('lawImmigration'), number: it.number }) + (it.revision ? ' · ' + it.revision : '') }),
          h('p', { 'class': 'fh-handoff' }, [h('strong', { text: t('handoffTitle') }), ' ', body]),
          h('p', { 'class': 'fh-handoff-links' }, [h('a', { href: 'https://www.hikorea.go.kr', target: '_blank', rel: 'noopener noreferrer', text: t('hikorea') }), ' · ', h('a', { href: 'tel:1345', text: t('call1345') })]),
        ])]));
      }
    });
    container.appendChild(list);
  }
  function openForm(fid) { ensureValues(fid); go('explain', { formId: fid, stepIndex: 0 }); }

  /* ── EXPLAIN ──────────────────────────────────────────────────────────── */
  function sourceLine(f) {
    var s = data.schemas.forms[E.editionOf(f, ensureValues(st.formId))];
    var tpl = s.template || {};
    var ver = tpl.verification === 'MATCHES_RULE_1106_TEXT' ? t('verificationMatches') : tpl.verification === 'RULE_1106_PDF' ? (tpl.edition || '') : t('verificationPending');
    return t('sourceLine', { basis: s.legalBasis + ' · ' + (tpl.revisionOnForm || s.revisionDate), edition: ver });
  }
  function renderExplain() {
    var f = form(); var root = els.explain; root.innerHTML = '';
    var dirty = !!st.dirtyForms[st.formId];
    root.appendChild(h('nav', { 'class': 'fh-crumbs', 'aria-label': 'breadcrumb' }, [h('a', { href: '#', onclick: function (e) { e.preventDefault(); go('home'); }, text: t('title') }), h('span', { text: ' / ' }), h('span', { text: L(f.short) })]));
    root.appendChild(h('header', { 'class': 'fh-form-head' }, [statusChip(supportStatus(st.formId)), h('h1', { 'class': 'fh-h1', text: L(f.name) }), h('p', { 'class': 'fh-muted', text: L(f.number) })]));
    var rows = [['aboutTitle', L(f.summary)], ['who', L(f.who)], ['when', f.when ? L(f.when) : ''], ['where', L(f.where)], ['attachments', L(f.attachments)]];
    var dl = h('dl', { 'class': 'fh-facts' });
    rows.forEach(function (r) { if (!r[1]) return; dl.appendChild(h('div', {}, [h('dt', { text: t(r[0]) }), h('dd', { text: r[1] })])); });
    if (f.notes && f.notes.length) dl.appendChild(h('div', {}, [h('dt', { text: t('notes') }), h('dd', {}, [h('ul', {}, f.notes.map(function (n) { return h('li', { text: L(n) }); }))])]));
    root.appendChild(dl);
    if (f.editions && f.editions.length > 1) root.appendChild(h('p', { 'class': 'fh-muted fh-editions' }, [h('strong', { text: t('editionsTitle') + ': ' }), f.editions.map(function (e) { return L(e.label); }).join(' · ')]));
    root.appendChild(h('p', { 'class': 'fh-source', text: sourceLine(f) }));
    var steps = E.visibleSteps(f, values());
    root.appendChild(h('ol', { 'class': 'fh-step-list', 'aria-label': t('stepsTitle') }, steps.map(function (s, i) { return h('li', {}, [h('span', { 'class': 'fh-step-n', text: String(i + 1) }), h('span', { text: L(s.title) })]); })));
    // easy guide (shared plain-language pack arrays)
    var pack = packFor(st.lang);
    if (Array.isArray(pack.easyModeNextSteps)) {
      var easy = h('div', { 'class': 'fh-easy', hidden: true }, [
        h('p', { 'class': 'fh-easy-notice', text: pack.easyModeNotice || '' }),
        h('h3', { text: pack.easyModeNextStepsTitle || '' }), h('ul', {}, pack.easyModeNextSteps.map(function (x) { return h('li', { text: x }); })),
        h('h3', { text: pack.easyModeWarningsTitle || '' }), h('ul', {}, (pack.easyModeWarnings || []).map(function (x) { return h('li', { text: x }); })),
        h('p', {}, [h('a', { 'class': 'fh-btn fh-btn-ghost', href: 'tel:1345', text: pack.easyModeCallHelp || '1345' })]),
      ]);
      var tg = h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', 'aria-expanded': 'false', text: t('easyToggle'), onclick: function () { var open = easy.hidden; easy.hidden = !open; tg.setAttribute('aria-expanded', String(open)); tg.textContent = open ? t('easyOff') : t('easyToggle'); } });
      root.appendChild(h('div', { 'class': 'fh-easy-wrap' }, [tg, easy]));
    }
    root.appendChild(h('div', { 'class': 'fh-actions' }, [
      h('button', { 'class': 'fh-btn fh-btn-primary', type: 'button', id: 'fhStart', text: dirty ? t('resume') : t('start'), onclick: function () { go('edit', { stepIndex: 0 }); } }),
      h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', text: t('changeForm'), onclick: function () { go('home'); } }),
    ]));
    root.appendChild(h('p', { 'class': 'fh-muted fh-small', text: t('privacyShort') }));
  }

  /* ── EDIT ─────────────────────────────────────────────────────────────── */
  var previewTimer = null;
  function schedulePreview() { clearTimeout(previewTimer); previewTimer = setTimeout(drawAllPreviews, 60); }
  function currentSteps() { return E.visibleSteps(form(), values()); }
  function stepStatus(step) {
    var f = form(), v = values();
    var fields = E.visibleFields(f, v, step.id).filter(function (x) { return x.type !== 'note'; });
    var req = fields.filter(function (x) { return E.isRequired(x, v); });
    var missing = req.filter(function (x) { return E.isEmpty(v[x.key]); });
    var filled = fields.filter(function (x) { return !E.isEmpty(v[x.key]); }).length;
    return { total: fields.length, filled: filled, missing: missing.length, done: !missing.length && filled > 0 };
  }
  function renderEdit() {
    var f = form(); var root = els.edit; root.innerHTML = '';
    var steps = currentSteps();
    if (st.stepIndex >= steps.length) st.stepIndex = Math.max(0, steps.length - 1);
    var step = steps[st.stepIndex];
    recompute();
    var rail = h('nav', { 'class': 'fh-rail', 'aria-label': t('stepsTitle'), id: 'fhRail' });
    var main = h('div', { 'class': 'fh-editor' }, [
      h('div', { 'class': 'fh-editor-head' }, [
        h('p', { 'class': 'fh-kicker', text: L(f.short) + ' · ' + t('stepOf', { n: st.stepIndex + 1, total: steps.length }) }),
        h('h1', { 'class': 'fh-h2', id: 'fhStepTitle', text: L(step.title) }),
        step.lead ? h('p', { 'class': 'fh-muted', text: L(step.lead) }) : null,
        st.lang !== 'ko' && st.lang !== 'en' ? h('p', { 'class': 'fh-muted fh-small', text: t('labelNote') + ' ' + t('otherLangNote') }) : null,
      ]),
      h('div', { 'class': 'fh-fields', id: 'fhFields' }),
      h('div', { 'class': 'fh-nav' }, [
        h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', id: 'fhPrev', text: t('prev'), disabled: st.stepIndex === 0 ? true : null, onclick: function () { go('edit', { stepIndex: st.stepIndex - 1 }); } }),
        h('button', { 'class': 'fh-btn fh-btn-primary', type: 'button', id: 'fhNext', text: st.stepIndex === steps.length - 1 ? t('review') : t('next'), onclick: function () { if (st.stepIndex === steps.length - 1) go('review'); else go('edit', { stepIndex: st.stepIndex + 1 }); } }),
      ]),
    ]);
    var aside = h('aside', { 'class': 'fh-aside', 'aria-label': t('previewTitle') }, [
      h('div', { 'class': 'fh-aside-head' }, [h('strong', { text: t('previewTitle') }), h('span', { 'class': 'fh-muted fh-small', id: 'fhIssueBadge' })]),
      h('div', { 'class': 'fh-aside-body', id: 'fhAsidePreview', dir: 'ltr' }),
      h('p', { 'class': 'fh-muted fh-small', text: t('previewHint') }),
      h('div', { 'class': 'fh-aside-actions' }, [
        h('button', { 'class': 'fh-btn fh-btn-ghost fh-btn-small', type: 'button', text: t('reset'), onclick: openReset }),
        h('button', { 'class': 'fh-btn fh-btn-ghost fh-btn-small', type: 'button', text: t('changeForm'), onclick: function () { go('home'); } }),
      ]),
    ]);
    root.appendChild(h('div', { 'class': 'fh-edit-grid' }, [rail, main, aside]));
    root.appendChild(h('div', { 'class': 'fh-mobile-bar', id: 'fhMobileBar' }, [
      h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', text: t('prev'), disabled: st.stepIndex === 0 ? true : null, onclick: function () { go('edit', { stepIndex: st.stepIndex - 1 }); } }),
      h('button', { 'class': 'fh-btn fh-btn-secondary', type: 'button', id: 'fhOpenSheet', text: t('toPreview'), onclick: function () { openSheet(); } }),
      h('button', { 'class': 'fh-btn fh-btn-primary', type: 'button', text: st.stepIndex === steps.length - 1 ? t('review') : t('next'), onclick: function () { if (st.stepIndex === steps.length - 1) go('review'); else go('edit', { stepIndex: st.stepIndex + 1 }); } }),
    ]));
    renderFields(step);
    updateRail();
    buildPreviewCanvases(document.getElementById('fhAsidePreview'), 'aside');
    schedulePreview();
  }
  function updateRail() {
    var rail = document.getElementById('fhRail'); if (!rail) return;
    rail.innerHTML = '';
    var steps = currentSteps();
    var ol = h('ol', { 'class': 'fh-rail-list' });
    steps.forEach(function (s, i) {
      var stt = stepStatus(s);
      var cls = i === st.stepIndex ? 'current' : (stt.done ? 'done' : 'todo');
      ol.appendChild(h('li', { 'class': 'fh-rail-item fh-rail-' + cls }, [h('button', { type: 'button', 'aria-current': i === st.stepIndex ? 'step' : null, onclick: function () { go('edit', { stepIndex: i }); } }, [
        h('span', { 'class': 'fh-rail-n', text: stt.done && i !== st.stepIndex ? '✓' : String(i + 1) }),
        h('span', { 'class': 'fh-rail-label' }, [h('span', { text: L(s.title) }), h('small', { text: t('fieldCount', { filled: stt.filled, total: stt.total }) })]),
      ])]));
    });
    rail.appendChild(ol);
    var badge = document.getElementById('fhIssueBadge');
    if (badge) badge.textContent = st.issues.length ? t('fitIssues') + ' ' + st.issues.length : '';
    var sheetBtn = document.getElementById('fhOpenSheet');
    if (sheetBtn) sheetBtn.textContent = t('toPreview') + (st.issues.length ? ' · ' + st.issues.length : '');
  }
  function renderFields(step) {
    var f = form(), v = values(); var box = document.getElementById('fhFields'); box.innerHTML = '';
    var fields = E.visibleFields(f, v, step.id);
    fields.forEach(function (fd) { box.appendChild(fieldControl(fd)); });
    if (step.id === f.steps[f.steps.length - 1].id) box.appendChild(h('p', { 'class': 'fh-muted fh-small', text: t('signNote') }));
  }
  function fieldControl(fd) {
    var v = values(); var id = 'f_' + fd.key;
    var req = E.isRequired(fd, v);
    var labelText = L(fd.label);
    var koLabel = fd.label.ko;
    var wrap = h('div', { 'class': 'fh-field fh-field-' + fd.type + (fd.layout === 'cards' ? ' fh-field-cards' : ''), 'data-key': fd.key });
    if (fd.type === 'note') { wrap.appendChild(h('p', { 'class': 'fh-note', text: L(fd.text) })); return wrap; }
    var lab = h('label', { 'class': 'fh-label', 'for': id }, [h('span', { 'class': 'fh-label-text', text: labelText }), h('span', { 'class': 'fh-tag ' + (req ? 'fh-tag-req' : ''), text: req ? t('required') : t('optional') })]);
    if (fd.type === 'choice' || fd.type === 'yesno') { lab = h('div', { 'class': 'fh-label', id: id + '_l' }, [h('span', { 'class': 'fh-label-text', text: labelText }), h('span', { 'class': 'fh-tag ' + (req ? 'fh-tag-req' : ''), text: req ? t('required') : t('optional') })]); }
    wrap.appendChild(lab);
    if (st.lang !== 'ko' && koLabel && koLabel !== labelText) wrap.appendChild(h('p', { 'class': 'fh-official', text: t('officialLabel') + ': ' + koLabel }));
    if (!fd.map && fd.type !== 'choice' && fd.type !== 'yesno') wrap.appendChild(h('p', { 'class': 'fh-official', text: t('notPrinted') }));
    var control;
    if (fd.type === 'choice') {
      var opts = fd.options || [];
      var group = h('div', { 'class': 'fh-choices' + (fd.layout === 'cards' ? ' fh-choices-cards' : ''), role: 'radiogroup', 'aria-labelledby': id + '_l' });
      opts.forEach(function (o, i) {
        var oid = id + '_' + i;
        var input = h('input', { type: 'radio', name: id, id: oid, value: String(o.v), checked: String(v[fd.key]) === String(o.v) && !E.isEmpty(v[fd.key]) ? true : null });
        input.addEventListener('change', function () { setValue(fd, o.v); afterChoice(fd); });
        group.appendChild(h('label', { 'class': 'fh-choice', 'for': oid }, [input, h('span', { 'class': 'fh-choice-body' }, [h('span', { 'class': 'fh-choice-title', text: L(o.label) }), o.sub ? h('span', { 'class': 'fh-choice-sub', text: L(o.sub) }) : null, o.note ? h('span', { 'class': 'fh-choice-note', text: L(o.note) }) : null])]));
      });
      control = group;
    } else if (fd.type === 'yesno') {
      var cb = h('input', { type: 'checkbox', id: id, checked: v[fd.key] ? true : null });
      cb.addEventListener('change', function () { setValue(fd, cb.checked); afterChoice(fd); });
      control = h('label', { 'class': 'fh-switch', 'for': id }, [cb, h('span', { 'class': 'fh-switch-track', 'aria-hidden': 'true' }), h('span', { text: v[fd.key] ? t('yes') : t('no'), 'class': 'fh-switch-text' })]);
      cb.addEventListener('change', function () { control.querySelector('.fh-switch-text').textContent = cb.checked ? t('yes') : t('no'); });
    } else if (fd.type === 'textarea') {
      control = h('textarea', { id: id, rows: 3, maxlength: fd.maxLen || 200, placeholder: fd.placeholder ? L(fd.placeholder) : null });
      control.value = v[fd.key] || '';
    } else {
      var type = fd.type === 'date' ? 'date' : fd.type === 'email' ? 'email' : fd.type === 'phone' ? 'tel' : 'text';
      control = h('input', { id: id, type: type, value: v[fd.key] || '', placeholder: fd.placeholder ? L(fd.placeholder) : (fd.type === 'arc' ? '000000-0000000' : null), autocomplete: 'off', inputmode: (fd.type === 'arc' || fd.type === 'number') ? 'numeric' : (fd.type === 'phone' ? 'tel' : null), maxlength: fd.maxLen && fd.type !== 'date' ? (fd.type === 'arc' ? 14 : fd.maxLen) : null, 'class': fd.type === 'upper' ? 'fh-upper' : null });
    }
    if (control.tagName === 'INPUT' || control.tagName === 'TEXTAREA') {
      control.addEventListener('input', function () {
        setValue(fd, control.value);
        if (fd.type === 'upper' && control.value !== v[fd.key]) { var pos = control.selectionStart; control.value = v[fd.key]; try { control.setSelectionRange(pos, pos); } catch (e) {} }
        if (fd.type === 'arc' && control.value !== v[fd.key] && E.digitsOnly(control.value).length === 13) control.value = v[fd.key];
        markIssue(wrap, fd.key);
      });
      control.addEventListener('focus', function () { st.focusKey = fd.key; drawAllPreviews(); scrollPreviewTo(fd.key); });
      control.addEventListener('blur', function () { if (st.focusKey === fd.key) { st.focusKey = null; drawAllPreviews(); } });
    }
    wrap.appendChild(control);
    if (fd.help) wrap.appendChild(h('p', { 'class': 'fh-help', text: L(fd.help) }));
    wrap.appendChild(h('p', { 'class': 'fh-field-issue', id: id + '_issue', role: 'status' }));
    markIssue(wrap, fd.key);
    return wrap;
  }
  function afterChoice(fd) {
    // visibility of steps / fields may change: re-render the fields of this step and the rail
    var steps = currentSteps(); var step = steps[Math.min(st.stepIndex, steps.length - 1)];
    var active = document.activeElement;
    renderFields(step); updateRail();
    if (active && active.id) { var again = document.getElementById(active.id); if (again) again.focus(); }
    if (fd.role === 'edition') { recompute(); var aside = document.getElementById('fhAsidePreview'); if (aside) buildPreviewCanvases(aside, 'aside'); }
    drawAllPreviews();
  }
  function markIssue(wrap, key) {
    var el = wrap.querySelector('.fh-field-issue'); if (!el) return;
    var fit = st.issues.filter(function (i) { return i.field === key; })[0];
    var val = st.validation.filter(function (i) { return i.key === key && i.code !== 'required'; })[0];
    var msg = fit ? fitMessage(fit) : (val ? val.msg : '');
    el.textContent = msg; wrap.classList.toggle('fh-has-issue', !!msg);
  }
  function fitMessage(i) {
    if (i.kind === 'OVERFLOW') return t('fitOverflow', { label: i.label, dropped: i.dropped });
    if (i.kind === 'SHRUNK') return t('fitShrunk', { label: i.label, size: i.size });
    return t('fitFont', { label: i.label, chars: (i.chars || []).join(' ') });
  }

  /* ── preview canvases ─────────────────────────────────────────────────── */
  function pageImage(ed, n) {
    var key = ed + '-' + n;
    if (st.pageImages[key]) return st.pageImages[key];
    var img = new Image(); img.decoding = 'async'; img.src = 'assets/forms/preview/' + key + '.png';
    img.onload = function () { drawAllPreviews(); };
    st.pageImages[key] = img; return img;
  }
  function buildPreviewCanvases(container, mode) {
    container.innerHTML = '';
    var s = spec(); var ed = edition();
    for (var p = 0; p < s.pages; p++) {
      var c = h('canvas', { 'class': 'fh-canvas', 'data-page': String(p), 'data-mode': mode, 'aria-label': t('previewPage', { n: p + 1 }), role: 'img' });
      c.addEventListener('click', onCanvasClick);
      container.appendChild(h('figure', { 'class': 'fh-page' }, [c, h('figcaption', { 'class': 'fh-muted fh-small', text: t('previewPage', { n: p + 1 }) + ' · ' + ed })]));
      pageImage(ed, p + 1);
    }
  }
  function drawAllPreviews() {
    document.querySelectorAll('canvas.fh-canvas').forEach(drawCanvas);
  }
  function drawCanvas(c) {
    var s = spec(); if (!s) return;
    var p = parseInt(c.getAttribute('data-page'), 10) || 0;
    var mode = c.getAttribute('data-mode');
    var cssW = mode === 'sheet' ? Math.max(320, Math.floor((window.innerWidth - 32) * st.zoom)) : (mode === 'full' ? Math.floor(Math.min(s.pageWidth * 1.4, (c.parentElement.parentElement.clientWidth || 800) - 8) * st.zoom) : (c.parentElement.parentElement.clientWidth || 360));
    var scale = cssW / s.pageWidth; var cssH = Math.round(s.pageHeight * scale);
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.style.width = cssW + 'px'; c.style.height = cssH + 'px';
    if (c.width !== Math.round(cssW * dpr) || c.height !== Math.round(cssH * dpr)) { c.width = Math.round(cssW * dpr); c.height = Math.round(cssH * dpr); }
    var ctx = c.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cssW, cssH);
    var img = pageImage(edition(), p + 1);
    if (img.complete && img.naturalWidth) ctx.drawImage(img, 0, 0, cssW, cssH);
    else { ctx.fillStyle = '#e8ecea'; ctx.fillRect(0, 0, cssW, cssH); }
    var ink = 'rgb(' + s.ink.join(',') + ')';
    ctx.save(); ctx.scale(scale, scale);
    st.ops.forEach(function (op) {
      if (op.page !== p) return;
      if (op.type === 'rect') { ctx.fillStyle = '#fff'; ctx.fillRect(op.x0, op.y0, op.x1 - op.x0, op.y1 - op.y0); return; }
      if (op.type === 'check') {
        ctx.strokeStyle = ink; ctx.lineWidth = 1.1; ctx.lineCap = 'round'; ctx.beginPath();
        ctx.moveTo(op.cx - 0.45 * op.s, op.cy - 0.02 * op.s); ctx.lineTo(op.cx - 0.12 * op.s, op.cy + 0.38 * op.s); ctx.lineTo(op.cx + 0.55 * op.s, op.cy - 0.5 * op.s); ctx.stroke(); return;
      }
      if (st.focusKey && op.field === st.focusKey) { ctx.fillStyle = 'rgba(33,79,67,.16)'; ctx.fillRect(op.x - 2, op.y - op.size, (op.maxWidth || op.w) + 4, op.size + 4); }
      ctx.fillStyle = op.overflow ? '#b3261e' : ink; ctx.font = op.size + 'px ' + (st.fontReady ? 'VisableNanum' : 'sans-serif'); ctx.textBaseline = 'alphabetic';
      ctx.fillText(op.text, op.x, op.y);
    });
    if (st.focusKey) {
      // highlight empty cells of the focused field too (so the user sees where it will land)
      var s2 = spec(); var o2f = E.overlayToField(form());
      Object.keys(s2.overlay).forEach(function (k) {
        if (o2f[k] !== st.focusKey) return; var o = s2.overlay[k]; if ((o.page || 0) !== p) return;
        ctx.strokeStyle = 'rgba(33,79,67,.9)'; ctx.lineWidth = 1; ctx.setLineDash([3, 2]);
        if (o.check) ctx.strokeRect(o.cx - 5, o.cy - 5, 10, 10);
        else ctx.strokeRect(o.x - 2, o.y - (o.size || 9), (o.maxWidth || 60) + 4, ((o.lines || 1) * (o.lineHeight || (o.size || 9) * 1.2)) + 3);
        ctx.setLineDash([]);
      });
    }
    ctx.restore();
  }
  function onCanvasClick(ev) {
    var c = ev.currentTarget; var s = spec(); var rect = c.getBoundingClientRect();
    var scale = rect.width / s.pageWidth; var x = (ev.clientX - rect.left) / scale, y = (ev.clientY - rect.top) / scale;
    var p = parseInt(c.getAttribute('data-page'), 10) || 0; var o2f = E.overlayToField(form());
    var hit = null;
    Object.keys(s.overlay).forEach(function (k) {
      var o = s.overlay[k]; if ((o.page || 0) !== p || !o2f[k]) return;
      var inside = o.check ? (Math.abs(x - o.cx) < 9 && Math.abs(y - o.cy) < 9) : (x >= o.x - 3 && x <= o.x + (o.maxWidth || 60) + 3 && y >= o.y - (o.size || 9) - 2 && y <= o.y + ((o.lines || 1) - 1) * (o.lineHeight || 11) + 4);
      if (inside && !hit) hit = o2f[k];
    });
    if (!hit) return;
    focusField(hit);
  }
  function focusField(key) {
    var f = form(); var fd = f.fields.filter(function (x) { return x.key === key; })[0]; if (!fd) return;
    var steps = currentSteps(); var idx = steps.map(function (s) { return s.id; }).indexOf(fd.step);
    if (idx < 0) return;
    closeSheet();
    if (st.screen !== 'edit' || idx !== st.stepIndex) go('edit', { stepIndex: idx });
    setTimeout(function () { var el = document.getElementById('f_' + key) || document.querySelector('[data-key="' + key + '"] input, [data-key="' + key + '"] textarea'); if (el) { el.focus(); el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } }, 30);
  }
  function scrollPreviewTo(key) {
    var box = document.getElementById('fhAsidePreview'); if (!box) return;
    var op = st.ops.filter(function (o) { return o.field === key; })[0]; var s = spec();
    var o = null;
    if (!op) { var o2f = E.overlayToField(form()); Object.keys(s.overlay).forEach(function (k) { if (!o && o2f[k] === key) o = s.overlay[k]; }); }
    var page = op ? op.page : (o ? (o.page || 0) : 0); var y = op ? op.y : (o ? (o.cy || o.y) : 0);
    var c = box.querySelectorAll('canvas')[page]; if (!c) return;
    var scale = c.getBoundingClientRect().width / s.pageWidth;
    box.scrollTo({ top: c.offsetTop + y * scale - box.clientHeight / 2, behavior: 'smooth' });
  }

  /* ── mobile preview sheet ─────────────────────────────────────────────── */
  function openSheet() {
    var sheet = els.sheet; sheet.hidden = false; document.body.classList.add('fh-sheet-open');
    sheet.innerHTML = '';
    var body = h('div', { 'class': 'fh-sheet-body', dir: 'ltr' });
    sheet.appendChild(h('div', { 'class': 'fh-sheet-head' }, [
      h('strong', { text: t('previewTitle') }),
      h('div', { 'class': 'fh-zoom' }, [h('button', { type: 'button', 'class': 'fh-btn fh-btn-ghost fh-btn-small', 'aria-label': t('zoomOut'), text: '−', onclick: function () { st.zoom = Math.max(1, st.zoom - 0.5); drawAllPreviews(); } }), h('button', { type: 'button', 'class': 'fh-btn fh-btn-ghost fh-btn-small', 'aria-label': t('zoomIn'), text: '+', onclick: function () { st.zoom = Math.min(3, st.zoom + 0.5); drawAllPreviews(); } })]),
      h('button', { type: 'button', 'class': 'fh-btn fh-btn-ghost fh-btn-small', id: 'fhSheetClose', text: t('closePreview'), onclick: closeSheet }),
    ]));
    sheet.appendChild(h('p', { 'class': 'fh-muted fh-small fh-sheet-hint', text: t('previewHint') + (st.issues.length ? ' · ' + t('fitIssues') + ' ' + st.issues.length : '') }));
    sheet.appendChild(body);
    buildPreviewCanvases(body, 'sheet'); drawAllPreviews();
    setTimeout(function () { var b = document.getElementById('fhSheetClose'); if (b) b.focus(); }, 20);
  }
  function closeSheet() { if (!els.sheet || els.sheet.hidden) return; els.sheet.hidden = true; els.sheet.innerHTML = ''; document.body.classList.remove('fh-sheet-open'); st.zoom = 1; }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && els.sheet && !els.sheet.hidden) closeSheet(); });

  /* ── REVIEW ───────────────────────────────────────────────────────────── */
  function renderReview() {
    var f = form(); var root = els.review; root.innerHTML = ''; recompute();
    var errs = st.validation.filter(function (i) { return i.level === 'error'; });
    var warns = st.validation.filter(function (i) { return i.level !== 'error'; });
    var comp = E.completeness(f, values());
    root.appendChild(h('nav', { 'class': 'fh-crumbs' }, [h('a', { href: '#', onclick: function (e) { e.preventDefault(); go('explain'); }, text: L(f.short) }), h('span', { text: ' / ' }), h('span', { text: t('review') })]));
    root.appendChild(h('h1', { 'class': 'fh-h1', text: t('reviewTitle') }));
    root.appendChild(h('p', { 'class': 'fh-progress', text: t('progress', comp) }));
    function list(title, items, tone, fmt) {
      if (!items.length) return null;
      return h('section', { 'class': 'fh-issues fh-issues-' + tone }, [h('h2', { 'class': 'fh-h3', text: title + ' (' + items.length + ')' }), h('ul', {}, items.map(function (i) {
        return h('li', {}, [h('span', { text: fmt(i) }), ' ', h('button', { type: 'button', 'class': 'fh-link', text: t('goFix'), onclick: function () { focusField(i.field || i.key); } })]);
      }))]);
    }
    var e1 = list(t('errors'), errs, 'error', function (i) { return i.msg; });
    var e2 = list(t('warnings'), warns, 'warn', function (i) { return i.msg; });
    var e3 = list(t('fitIssues'), st.issues, 'fit', fitMessage);
    if (!e1 && !e2 && !e3) root.appendChild(h('p', { 'class': 'fh-allgood', text: t('allGood') }));
    [e1, e2, e3].forEach(function (x) { if (x) root.appendChild(x); });
    root.appendChild(h('div', { 'class': 'fh-actions' }, [
      h('button', { 'class': 'fh-btn fh-btn-primary', type: 'button', id: 'fhToPreview', text: t('toPreview'), onclick: function () { go('preview'); } }),
      h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', text: t('toEdit'), onclick: function () { go('edit', { stepIndex: 0 }); } }),
    ]));
  }

  /* ── PREVIEW + EXPORT ─────────────────────────────────────────────────── */
  function renderPreviewScreen() {
    var f = form(); var root = els.preview; root.innerHTML = ''; recompute();
    root.appendChild(h('nav', { 'class': 'fh-crumbs' }, [h('a', { href: '#', onclick: function (e) { e.preventDefault(); go('explain'); }, text: L(f.short) }), h('span', { text: ' / ' }), h('span', { text: t('previewTitle') })]));
    root.appendChild(h('h1', { 'class': 'fh-h1', text: t('previewTitle') }));
    var head = h('div', { 'class': 'fh-preview-tools' }, [
      h('div', { 'class': 'fh-zoom' }, [h('button', { type: 'button', 'class': 'fh-btn fh-btn-ghost fh-btn-small', 'aria-label': t('zoomOut'), text: '−', onclick: function () { st.zoom = Math.max(0.5, st.zoom - 0.25); drawAllPreviews(); } }), h('button', { type: 'button', 'class': 'fh-btn fh-btn-ghost fh-btn-small', 'aria-label': t('zoomIn'), text: '+', onclick: function () { st.zoom = Math.min(2.5, st.zoom + 0.25); drawAllPreviews(); } })]),
      h('span', { 'class': 'fh-muted fh-small', text: t('previewHint') }),
    ]);
    root.appendChild(head);
    var pages = h('div', { 'class': 'fh-preview-pages', dir: 'ltr', id: 'fhFullPreview' });
    root.appendChild(pages);
    buildPreviewCanvases(pages, 'full');
    var status = h('p', { 'class': 'fh-status', id: 'fhExportStatus', role: 'status', 'aria-live': 'polite' });
    var errs = st.validation.filter(function (i) { return i.level === 'error'; }).length;
    root.appendChild(h('div', { 'class': 'fh-export' }, [
      st.issues.length ? h('p', { 'class': 'fh-warn', text: t('exportConfirmBody', { n: st.issues.length }) }) : null,
      errs ? h('p', { 'class': 'fh-warn', text: t('errors') + ': ' + errs }) : null,
      h('div', { 'class': 'fh-actions' }, [
        h('button', { 'class': 'fh-btn fh-btn-primary', type: 'button', id: 'fhExport', text: t('export'), onclick: function () { if (st.issues.length) openExportDialog(); else exportPdf(); } }),
        h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', text: t('toEdit'), onclick: function () { go('edit', { stepIndex: 0 }); } }),
        h('button', { 'class': 'fh-btn fh-btn-ghost', type: 'button', text: t('reset'), onclick: openReset }),
      ]),
      status,
      h('p', { 'class': 'fh-muted fh-small', text: t('signNote') }),
      h('p', { 'class': 'fh-source', text: sourceLine(f) }),
    ]));
    drawAllPreviews();
  }
  var vendorsLoaded = null;
  function loadScript(src) { return new Promise(function (res, rej) { var s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = function () { rej(new Error(src)); }; document.head.appendChild(s); }); }
  function ensureVendors() {
    if (!vendorsLoaded) vendorsLoaded = Promise.all([window.PDFLib ? null : loadScript(data.schemas.vendor.pdfLib), window.fontkit ? null : loadScript(data.schemas.vendor.fontkit)]);
    return vendorsLoaded;
  }
  function setStatus(msg, cls) { var el = document.getElementById('fhExportStatus'); if (!el) return; el.textContent = msg; el.className = 'fh-status' + (cls ? ' fh-status-' + cls : ''); }
  function exportPdf() {
    var f = form(); var s = spec(); var btn = document.getElementById('fhExport'); if (btn) btn.disabled = true;
    setStatus(t('exporting'), 'busy');
    var ops = st.ops.slice();
    return ensureVendors().then(function () {
      return Promise.all([
        fetch(s.pdf).then(function (r) { if (!r.ok) throw new Error(t('pdfLoadFail')); return r.arrayBuffer(); }),
        fetch(data.schemas.fontKorean).then(function (r) { if (!r.ok) throw new Error(t('fontLoadFail')); return r.arrayBuffer(); }),
      ]);
    }).then(function (res) {
      var PDFLib = window.PDFLib;
      return PDFLib.PDFDocument.load(res[0]).then(function (doc) {
        doc.registerFontkit(window.fontkit);
        return doc.embedFont(res[1]).then(function (font) {
          var pages = doc.getPages(); var H = s.pageHeight;
          var ink = PDFLib.rgb(s.ink[0] / 255, s.ink[1] / 255, s.ink[2] / 255); var white = PDFLib.rgb(1, 1, 1);
          ops.forEach(function (op) {
            var page = pages[op.page]; if (!page) return;
            if (op.type === 'rect') { page.drawRectangle({ x: op.x0, y: H - op.y1, width: op.x1 - op.x0, height: op.y1 - op.y0, color: white }); return; }
            if (op.type === 'check') {
              var cx = op.cx, cy = H - op.cy, sz = op.s;
              page.drawLine({ start: { x: cx - 0.45 * sz, y: cy + 0.02 * sz }, end: { x: cx - 0.12 * sz, y: cy - 0.38 * sz }, thickness: 1.1, color: ink });
              page.drawLine({ start: { x: cx - 0.12 * sz, y: cy - 0.38 * sz }, end: { x: cx + 0.55 * sz, y: cy + 0.5 * sz }, thickness: 1.1, color: ink });
              return;
            }
            page.drawText(op.text, { x: op.x, y: H - op.y, size: op.size, font: font, color: ink });
          });
          return doc.save();
        });
      });
    }).then(function (bytes) {
      var blob = new Blob([bytes], { type: 'application/pdf' }); var url = URL.createObjectURL(blob);
      var a = document.createElement('a'); a.href = url; a.download = E.filename(f, values(), edition(), st.lang === 'ko' ? 'ko' : 'en');
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
      setStatus(t('exported'), 'ok');
      app.lastExport = { filename: a.download, bytes: bytes.length, ops: ops.length };
    }).catch(function (err) {
      setStatus(t('exportFailed', { error: err && err.message ? err.message : String(err) }), 'err');
    }).then(function () { if (btn) btn.disabled = false; });
  }
  function openExportDialog() {
    var d = els.exportDialog; d.innerHTML = '';
    d.appendChild(h('form', { method: 'dialog', 'class': 'fh-dialog' }, [
      h('h2', { text: t('exportConfirmTitle') }), h('p', { text: t('exportConfirmBody', { n: st.issues.length }) }),
      h('ul', { 'class': 'fh-dialog-list' }, st.issues.slice(0, 6).map(function (i) { return h('li', { text: fitMessage(i) }); })),
      h('div', { 'class': 'fh-actions' }, [
        h('button', { 'class': 'fh-btn fh-btn-ghost', value: 'fix', text: t('exportFix') }),
        h('button', { 'class': 'fh-btn fh-btn-primary', value: 'go', text: t('exportAnyway') }),
      ]),
    ]));
    d.onclose = function () { if (d.returnValue === 'go') exportPdf(); else if (d.returnValue === 'fix') go('review'); };
    d.showModal();
  }
  function openReset() {
    var d = els.resetDialog; d.innerHTML = '';
    d.appendChild(h('form', { method: 'dialog', 'class': 'fh-dialog' }, [
      h('h2', { text: t('resetTitle') }), h('p', { text: t('resetBody') }),
      h('div', { 'class': 'fh-actions' }, [h('button', { 'class': 'fh-btn fh-btn-ghost', value: 'cancel', text: t('cancel') }), h('button', { 'class': 'fh-btn fh-btn-danger', value: 'reset', text: t('resetConfirm') })]),
    ]));
    d.onclose = function () { if (d.returnValue === 'reset') { delete st.values[st.formId]; delete st.dirtyForms[st.formId]; ensureValues(st.formId); st.ops = []; st.issues = []; go('explain', { stepIndex: 0 }); } };
    d.showModal();
  }

  /* ── language / theme ─────────────────────────────────────────────────── */
  function setLang(lang) {
    if (LOCALES.indexOf(lang) < 0) return;
    st.lang = lang; searchIndex = null;
    try { localStorage.setItem('paradiso:language', lang); } catch (e) {}
    loadPack(lang).then(function () { els.langSelect.value = lang; render(); });
  }
  function initTheme() {
    var dark = false;
    try { dark = localStorage.getItem('paradiso:brightness') === 'dark'; } catch (e) {}
    document.body.setAttribute('data-theme', dark ? 'dark' : 'light');
    els.themeBtn.setAttribute('aria-pressed', String(dark));
    els.themeBtn.addEventListener('click', function () {
      var next = document.body.getAttribute('data-theme') !== 'dark';
      document.body.setAttribute('data-theme', next ? 'dark' : 'light'); els.themeBtn.setAttribute('aria-pressed', String(next));
      try { localStorage.setItem('paradiso:brightness', next ? 'dark' : 'light'); } catch (e) {}
    });
  }

  /* ── boot ─────────────────────────────────────────────────────────────── */
  function boot() {
    ['home', 'explain', 'edit', 'review', 'preview'].forEach(function (s) { els[s] = document.getElementById('fh' + s.charAt(0).toUpperCase() + s.slice(1)); });
    els.sheet = document.getElementById('fhSheet'); els.resetDialog = document.getElementById('fhResetDialog'); els.exportDialog = document.getElementById('fhExportDialog');
    els.backLink = document.getElementById('fhBack'); els.privacy = document.getElementById('fhPrivacy'); els.langSelect = document.getElementById('fhLang'); els.themeBtn = document.getElementById('fhTheme');
    els.footerLegal = document.getElementById('fhFooterLegal'); els.footerLine = document.getElementById('fhFooterLine'); els.skip = document.getElementById('fhSkip'); els.brandTitle = document.getElementById('fhBrandTitle');
    st.lang = readLang();
    LOCALES.forEach(function (l) { els.langSelect.appendChild(h('option', { value: l, text: LABELS[l] })); });
    els.langSelect.value = st.lang;
    els.langSelect.addEventListener('change', function () { setLang(els.langSelect.value); });
    initTheme();
    st.measure = makeMeasure();
    var params = new URLSearchParams(location.search);
    return Promise.all([fetchJson('data/form_definitions.json'), fetchJson('data/form_schemas.json'), fetchJson('data/forms_inventory.json').catch(function () { return null; }), fetchJson('assets/forms/fonts/NanumGothic-Regular.charset.json').catch(function () { return null; }), loadPack('ko'), loadPack(st.lang)])
      .then(function (res) {
        data.defs = res[0]; data.schemas = res[1]; data.inventory = res[2]; data.charset = res[3];
        st.glyphs = data.charset ? E.makeGlyphChecker(data.charset) : null;
        // entry from Waymaker / deep links
        var formParam = (params.get('form') || '').toUpperCase(); var typeParam = params.get('type') || ''; var proc = params.get('procedure') || '';
        var initial = parseHash();
        if (params.get('source') === 'waymaker') st.from = { visa: params.get('visa') || '', procedure: proc };
        var target = null, preset = {};
        if (formParam && data.defs.forms[formParam]) { target = formParam; var wt = data.defs.forms[formParam].waymakerTypes || {}; if (typeParam && wt[typeParam]) preset = wt[typeParam]; }
        else if (formParam) { Object.keys(data.defs.forms).forEach(function (fid) { var f = data.defs.forms[fid]; if (!target && (f.editions || []).some(function (e) { return e.v === formParam; })) { target = fid; preset = { edition: formParam }; } }); }
        else if (proc && data.defs.waymaker[proc]) { target = data.defs.waymaker[proc].form; preset = data.defs.waymaker[proc].values || {}; }
        if (initial.formId) { st.formId = initial.formId; ensureValues(st.formId); st.screen = initial.screen; st.stepIndex = initial.stepIndex; }
        if (target) { st.formId = target; var v = ensureValues(target); Object.keys(preset).forEach(function (k) { v[k] = preset[k]; }); st.screen = initial.formId ? initial.screen : 'explain'; }
        if (st.screen !== 'home' && !st.formId) st.screen = 'home';
        try { history.replaceState({ screen: st.screen, formId: st.formId, stepIndex: st.stepIndex }, '', hashFor(st)); } catch (e) {}
        render();
        document.body.classList.add('fh-ready');
        return loadFont().then(function () { st.measure = makeMeasure(); if (st.formId) { recompute(); drawAllPreviews(); } });
      }).catch(function (err) {
        document.body.classList.add('fh-boot-failed');
        var el = document.getElementById('fhBootError'); if (el) { el.hidden = false; el.textContent = (err && err.message) ? err.message : String(err); }
      });
  }
  app.state = st; app.data = data; app.engine = E; app.go = go; app.setLang = setLang; app.recompute = recompute; app.exportPdf = exportPdf; app.t = t;
  window.VisableFormHelper = app;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
