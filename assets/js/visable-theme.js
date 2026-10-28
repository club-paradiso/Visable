/* Visable theme skins — boot + picker (2026.10)
 * Load synchronously in <head> (after the page's own theme bootstrap) so the
 * chosen skin is on <html data-vt> before first paint. Colour tokens live in
 * assets/css/visable-theme-skins.css. Storage key: "visable:theme".
 * - No stored choice → "default" (the Visable Blue rebrand), unless the
 *   visitor had explicitly chosen the legacy archive_diary look; that choice is
 *   respected (no data-vt) until they pick a skin here.
 * - Picking a skin resets the legacy editorial theme to civic_editorial so the
 *   two systems never stack.
 */
(function () {
  'use strict';
  var KEY = 'visable:theme';
  var EDITORIAL_KEY = 'paradiso:editorial-theme';
  var THEMES = ['default', 'stamp', 'chrome', 'neon'];
  var root = document.documentElement;

  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function write(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function resolve() {
    var t = read(KEY);
    if (THEMES.indexOf(t) >= 0) return t;
    if (read(EDITORIAL_KEY) === 'archive_diary') return null;
    return 'default';
  }

  /* Page id for page-scoped skin rules (visable-theme-legacy.css). */
  (function () {
    var parts = location.pathname.split('/').filter(Boolean);
    var last = parts.length ? parts[parts.length - 1] : '';
    var id = /\.html$/.test(last) ? last.replace(/\.html$/, '') : (last || 'index');
    if (id === 'index' && parts.length > 1) id = parts[parts.length - 2];
    root.setAttribute('data-vt-page', id);
  })();

  /* Knowledge Studio follows the OS colour scheme with no brightness attribute;
     expose it so the skins pick their dark face there too. */
  if (root.getAttribute('data-vt-page') === 'knowledge-studio' && window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var syncScheme = function () { if (mq.matches) root.setAttribute('data-theme', 'dark'); else root.removeAttribute('data-theme'); };
    syncScheme();
    if (mq.addEventListener) mq.addEventListener('change', syncScheme); else if (mq.addListener) mq.addListener(syncScheme);
  }

  var current = resolve();
  if (current) root.setAttribute('data-vt', current);

  /* ---- copy (brand names stay Latin; descriptions per language) ---- */
  var COPY = {
    ko: { title: '화면 테마', fab: '테마', close: '닫기', bright: '밝기', brightHint: '테마는 그대로, 밝기만 바뀌어요', light: '라이트', dark: '다크',
      default: '기본 · 맑은 파랑', stamp: '여권 수첩 · 밤에는 표지', chrome: '유리와 금속 · 어두우면 그래파이트', neon: '네온 간판 · 라이트는 낮 화면' },
    en: { title: 'Display theme', fab: 'Theme', close: 'Close', bright: 'Brightness', brightHint: 'Keeps the theme, changes only brightness', light: 'Light', dark: 'Dark',
      default: 'Default · clear blue', stamp: 'Passport booklet · Cover at night', chrome: 'Glass and metal · Graphite when dark', neon: 'Neon signs · light mode is Day' },
    zh: { title: '界面主题', fab: '主题', close: '关闭', bright: '亮度', brightHint: '只改变亮度，不改变主题', light: '浅色', dark: '深色',
      default: '默认 · 清蓝', stamp: '护照手册 · 深色为封面', chrome: '玻璃与金属 · 深色为石墨', neon: '霓虹招牌 · 浅色为白天' }
  };
  var NAMES = { default: 'Visable', stamp: 'Stamp', chrome: 'Chrome', neon: 'Neon' };
  function lang() {
    var l = (root.getAttribute('lang') || 'ko').toLowerCase();
    if (l.indexOf('zh') === 0) return COPY.zh;
    if (l.indexOf('ko') === 0) return COPY.ko;
    return COPY.en;
  }

  function isDark() {
    var b = document.body;
    return (b && b.getAttribute('data-theme') === 'dark') || root.getAttribute('data-theme') === 'dark';
  }

  /* Display and numeral faces from the approved canvas, fetched only after a
     visitor picks that skin: Stamp → Gowun Batang + IBM Plex Mono, Chrome →
     Unbounded (numerals/codes), Neon → JetBrains Mono. The default skin makes
     no extra font request (privacy pages such as Form Helper allow only the
     Pretendard CDN); its mono face falls back to the system monospace. */
  var FONTS = {
    stamp: 'family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500;600',
    chrome: 'family=Unbounded:wght@500;700',
    neon: 'family=JetBrains+Mono:wght@400;500;600'
  };
  function ensureFonts(t) {
    var q = FONTS[t];
    if (!q || !document.head || document.getElementById('vt-font-' + t)) return;
    var l = document.createElement('link');
    l.id = 'vt-font-' + t;
    l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?' + q + '&display=swap';
    document.head.appendChild(l);
  }

  var WORDMARK_LIGHT = 'assets/brand/logos/visable-wordmark-blue.svg';
  function syncWordmarks() {
    var imgs = document.querySelectorAll('img[src*="visable-wordmark"], img[data-vt-src]');
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      var orig = img.getAttribute('data-vt-src');
      if (!orig) {
        orig = img.getAttribute('src');
        // Only the default ink wordmark is swapped; white/green variants are the page's own dark handling.
        if (!/visable-wordmark\.svg/.test(orig)) continue;
        img.setAttribute('data-vt-src', orig);
      }
      var want = current && !isDark() ? orig.replace(/assets\/brand\/visable-wordmark\.svg/, WORDMARK_LIGHT) : orig;
      if (img.getAttribute('src') !== want) img.setAttribute('src', want);
    }
  }

  function syncMeta() {
    var m = document.querySelector('meta[name="theme-color"]');
    if (!m || !current) return;
    var v = getComputedStyle(root).getPropertyValue('--vs-meta').trim();
    var bodyV = document.body ? getComputedStyle(document.body).getPropertyValue('--vs-meta').trim() : '';
    if (bodyV || v) m.setAttribute('content', bodyV || v);
  }

  function syncPickers() {
    var opts = document.querySelectorAll('.vt-opt');
    for (var i = 0; i < opts.length; i++) {
      opts[i].setAttribute('aria-checked', opts[i].getAttribute('data-vt-value') === current ? 'true' : 'false');
      opts[i].tabIndex = opts[i].getAttribute('data-vt-value') === (current || 'default') ? 0 : -1;
    }
    var coins = document.querySelectorAll('.vt-fab .vt-coin, [data-vt-open] .vt-coin');
    for (var j = 0; j < coins.length; j++) coins[j].setAttribute('data-c', current || 'default');
    syncBrightnessSeg();
  }

  /* Brightness lives on each page's own control; the panel only mirrors and
     drives it, so theme and brightness never change each other. */
  function syncBrightnessSeg() {
    var dark = isDark();
    var segs = document.querySelectorAll('.vt-seg button');
    for (var i = 0; i < segs.length; i++) {
      var want = segs[i].getAttribute('data-bright') === 'dark';
      segs[i].setAttribute('aria-pressed', want === dark ? 'true' : 'false');
    }
  }
  /* Programmatic clicks on the page's own brightness control must not be
     read as an outside click that closes the panel. */
  var internalClick = false;
  function clickInternal(el) { internalClick = true; try { el.click(); } finally { internalClick = false; } }
  function setBrightness(dark) {
    if (isDark() === dark) return;
    var direct = document.querySelector('[data-action="set-brightness"][data-brightness="' + (dark ? 'dark' : 'light') + '"]');
    if (direct) clickInternal(direct);
    if (isDark() !== dark && typeof window.toggleTheme === 'function') window.toggleTheme();
    if (isDark() !== dark) {
      var existing = document.getElementById('mainThemeBtn');
      if (existing) clickInternal(existing);
    }
    syncBrightnessSeg();
  }

  function setBrightnessDark() {
    if (isDark()) return;
    var btn = document.querySelector('[data-action="set-brightness"][data-brightness="dark"]');
    if (btn) { btn.click(); return; }
    var toggles = ['#aiThemeBtn', '#fhTheme', '#brightToggle', '#brightBtn', '#pvBrightToggle', '#mainThemeBtn'];
    for (var i = 0; i < toggles.length; i++) {
      var el = document.querySelector(toggles[i]);
      if (el) { el.click(); if (isDark()) return; }
    }
  }

  function apply(t, opts) {
    if (THEMES.indexOf(t) < 0) t = 'default';
    var changed = t !== current;
    current = t;
    if (changed && document.body) {
      root.classList.add('vt-switching');
      clearTimeout(apply._t);
      apply._t = setTimeout(function () { root.classList.remove('vt-switching'); }, 320);
    }
    root.setAttribute('data-vt', t);
    write(KEY, t);
    if (read(EDITORIAL_KEY) === 'archive_diary') write(EDITORIAL_KEY, 'civic_editorial');
    if (root.getAttribute('data-theme') === 'archive_diary') root.setAttribute('data-theme', 'civic_editorial');
    ensureFonts(t);
    // Neon is a night skin first; its light face (Day) stays one brightness tap away.
    if (changed && t === 'neon' && !(opts && opts.keepBrightness)) setBrightnessDark();
    syncWordmarks();
    syncPickers();
    syncMeta();
  }

  function buildGroup(c, idPrefix) {
    var fs = document.createElement('div');
    fs.className = 'vt-picker';
    fs.setAttribute('role', 'radiogroup');
    fs.setAttribute('aria-label', c.title);
    THEMES.forEach(function (t) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'vt-opt';
      b.id = idPrefix + t;
      b.setAttribute('role', 'radio');
      b.setAttribute('data-vt-value', t);
      b.innerHTML = '<span class="vt-mini" data-p="' + t + '" aria-hidden="true"><i></i><b></b></span>' +
        '<span class="vt-opt-row"><span class="vt-coin" data-c="' + t + '" aria-hidden="true"></span>' +
        '<span class="vt-opt-txt"><span class="vt-name"></span><small></small></span></span>' +
        '<span class="vt-check" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span>';
      b.querySelector('.vt-name').textContent = NAMES[t];
      b.querySelector('small').textContent = c[t];
      b.addEventListener('click', function () { apply(t, { keepBrightness: true }); });
      fs.appendChild(b);
    });
    fs.addEventListener('keydown', function (e) {
      var keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
      if (!(e.key in keys)) return;
      e.preventDefault();
      var i = THEMES.indexOf(current || 'default');
      var n = THEMES[(i + keys[e.key] + THEMES.length) % THEMES.length];
      apply(n, { keepBrightness: true });
      var el = fs.querySelector('[data-vt-value="' + n + '"]');
      if (el) el.focus();
    });
    return fs;
  }

  /* Re-apply picker copy for the current document language (home loads its
     locale pack after mount, and visitors can switch language later). */
  function relabel() {
    var c = lang();
    var groups = document.querySelectorAll('.vt-picker');
    for (var i = 0; i < groups.length; i++) groups[i].setAttribute('aria-label', c.title);
    var opts = document.querySelectorAll('.vt-opt');
    for (var j = 0; j < opts.length; j++) {
      var small = opts[j].querySelector('small');
      if (small) small.textContent = c[opts[j].getAttribute('data-vt-value')];
    }
    var fabs = document.querySelectorAll('.vt-fab');
    for (var k = 0; k < fabs.length; k++) {
      fabs[k].setAttribute('aria-label', c.title);
      var lbl = fabs[k].querySelector('.vt-fab-label');
      if (lbl) lbl.textContent = c.fab;
    }
    var t = document.getElementById('vtPopTitle');
    if (t) t.textContent = c.title;
    var quickTitle = document.getElementById('vtCivicTitle');
    if (quickTitle) quickTitle.textContent = c.title;
    document.querySelectorAll('[data-vt-open]').forEach(function (btn) {
      btn.setAttribute('aria-label', c.title);
      btn.setAttribute('title', c.title);
      var label = btn.querySelector('.cs-theme-label');
      if (label) label.textContent = c.title;
    });
    document.querySelectorAll('.vt-pop-close').forEach(function (x) { x.setAttribute('aria-label', c.close); });
    document.querySelectorAll('.vt-bright').forEach(function (row) { labelBrightness(row, c); });
    syncBrightnessSeg();
  }

  /* Shared panel head: title + close button (44px). */
  function buildHead(c, titleId, onClose) {
    var head = document.createElement('div');
    head.className = 'vt-pop-head';
    var h = document.createElement('h2');
    h.id = titleId;
    h.textContent = c.title;
    var x = document.createElement('button');
    x.type = 'button';
    x.className = 'vt-pop-close';
    x.setAttribute('aria-label', c.close);
    x.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    x.addEventListener('click', onClose);
    head.appendChild(h);
    head.appendChild(x);
    return head;
  }

  function buildBrightness(c) {
    var row = document.createElement('div');
    row.className = 'vt-bright';
    row.innerHTML = '<span class="vt-bright-label" id="vtBrightLabel"></span>' +
      '<span class="vt-seg" role="group" aria-labelledby="vtBrightLabel">' +
      '<button type="button" data-bright="light" aria-pressed="false"></button>' +
      '<button type="button" data-bright="dark" aria-pressed="false"></button></span>';
    row.querySelectorAll('.vt-seg button').forEach(function (b) {
      b.addEventListener('click', function () { setBrightness(b.getAttribute('data-bright') === 'dark'); });
    });
    labelBrightness(row, c);
    return row;
  }
  function labelBrightness(row, c) {
    var l = row.querySelector('.vt-bright-label');
    if (l) { l.textContent = c.bright; var sm = document.createElement('small'); sm.textContent = c.brightHint; l.appendChild(sm); }
    var lb = row.querySelector('[data-bright="light"]'); if (lb) lb.textContent = c.light;
    var db = row.querySelector('[data-bright="dark"]'); if (db) db.textContent = c.dark;
  }
  /* Kept for callers from the previous release (labels the brightness row). */
  function syncCivicBrightnessLabel() {
    var row = document.querySelector('#vtCivicPop .vt-bright');
    if (row) labelBrightness(row, lang());
    syncBrightnessSeg();
  }

  /* The Civic homepage/result headers are rebuilt by civic-search.js. One
     delegated trigger ([data-vt-open]) serves both headers. Popover from
     601px, bottom sheet with a scrim below. Picking applies at once and keeps
     the panel open so the four faces can be compared; Escape, the close
     button, the scrim or an outside click closes it and focus returns to the
     header button. */
  function mountCivicPicker(c) {
    if (!document.getElementById('civicLanding') || document.getElementById('vtCivicPop')) return;
    var opener = null;
    var scrim = document.createElement('div');
    scrim.className = 'vt-scrim';
    scrim.hidden = true;
    var pop = document.createElement('div');
    pop.id = 'vtCivicPop';
    pop.className = 'vt-pop vt-civic-pop';
    pop.setAttribute('role', 'dialog');
    pop.setAttribute('aria-modal', 'false');
    pop.setAttribute('aria-labelledby', 'vtCivicTitle');
    pop.hidden = true;
    pop.appendChild(buildHead(c, 'vtCivicTitle', function () { close(true); }));
    var choices = buildGroup(c, 'vt-civic-');
    pop.appendChild(choices);
    pop.appendChild(buildBrightness(c));
    document.body.appendChild(scrim);
    document.body.appendChild(pop);

    function narrow() { return window.matchMedia ? window.matchMedia('(max-width: 600px)').matches : window.innerWidth <= 600; }
    function setExpanded(open) {
      document.querySelectorAll('[data-vt-open]').forEach(function (b) {
        b.setAttribute('aria-expanded', open && b === opener ? 'true' : 'false');
      });
    }
    // Popover placement is the shared anchoring (assets/js/anchored-overlay.js): under the opener, end-aligned,
    // kept inside the viewport and re-placed on scroll/resize. ≤600px the stylesheet makes it a bottom sheet.
    var stopTrack = null;
    function popover() { return !narrow(); }
    function close(focus) {
      if (pop.hidden) return;
      if (stopTrack) { stopTrack(); stopTrack = null; }
      pop.hidden = true;
      scrim.hidden = true;
      setExpanded(false);
      if (focus && opener && opener.isConnected) opener.focus();
    }
    function open(btn) {
      opener = btn;
      pop.hidden = false;
      scrim.hidden = !narrow();
      pop.setAttribute('aria-modal', narrow() ? 'true' : 'false');
      syncPickers();
      relabel();
      if (stopTrack) stopTrack();
      stopTrack = window.VisableOverlay ? window.VisableOverlay.track(pop, opener, { when: popover }) : null;
      setExpanded(true);
      var selected = pop.querySelector('.vt-opt[aria-checked="true"]') || pop.querySelector('.vt-opt');
      if (selected) selected.focus({ preventScroll: true });
    }

    document.addEventListener('click', function (e) {
      if (internalClick) return;
      var btn = e.target.closest('[data-vt-open]');
      if (btn) {
        e.preventDefault();
        if (!pop.hidden && btn === opener) close(true);
        else open(btn);
        return;
      }
      if (!pop.hidden && !pop.contains(e.target)) close(false);
    });
    document.addEventListener('keydown', function (e) {
      if (pop.hidden) return;
      if (e.key === 'Escape') { e.preventDefault(); close(true); return; }
      // Keep keyboard focus inside the sheet while it is modal.
      if (e.key === 'Tab' && pop.getAttribute('aria-modal') === 'true') {
        var f = pop.querySelectorAll('button:not([disabled])');
        var vis = Array.prototype.filter.call(f, function (el) { return el.tabIndex !== -1; });
        if (!vis.length) return;
        var first = vis[0], last = vis[vis.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
    window.addEventListener('resize', function () { if (!pop.hidden) { scrim.hidden = !narrow(); pop.setAttribute('aria-modal', narrow() ? 'true' : 'false'); } });
  }

  function mount() {
    var c = lang();
    // Home: the global settings sheet already has an "interface theme" block — the picker replaces its old two-way toggle there.
    var old = document.querySelector('#globalSettingsOverlay [data-action="toggle-editorial-theme"]');
    if (old && old.parentNode) {
      var holder = old.parentNode;
      holder.innerHTML = '';
      holder.appendChild(buildGroup(c, 'vt-set-'));
    } else if (!document.querySelector('.vt-fab')) {
      // Pages with their own brightness button get the theme button right beside it; others get a floating pill.
      var anchor = document.querySelector('#aiThemeBtn, #fhTheme, #brightToggle, #brightBtn, #pvBrightToggle');
      var fab = document.createElement('button');
      fab.type = 'button';
      fab.className = anchor ? 'vt-fab vt-inline' : 'vt-fab';
      fab.setAttribute('aria-haspopup', 'dialog');
      fab.setAttribute('aria-expanded', 'false');
      fab.setAttribute('aria-controls', 'vtPop');
      fab.setAttribute('aria-label', c.title);
      fab.innerHTML = '<span class="vt-coin" aria-hidden="true"></span><span class="vt-fab-label"></span>';
      fab.querySelector('.vt-fab-label').textContent = c.fab;
      var pop = document.createElement('div');
      pop.className = 'vt-pop';
      pop.id = 'vtPop';
      pop.setAttribute('role', 'dialog');
      pop.setAttribute('aria-labelledby', 'vtPopTitle');
      pop.hidden = true;
      pop.appendChild(buildHead(c, 'vtPopTitle', function () { close(true); }));
      pop.appendChild(buildGroup(c, 'vt-pop-'));
      // Narrow screens: the header has no room for one more button, so a floating pill takes over.
      var fabs = [fab];
      if (anchor) {
        var narrow = fab.cloneNode(true);
        narrow.className = 'vt-fab vt-fab-narrow';
        fabs.push(narrow);
      }
      var opener = fab, stopTrack = null;
      function close(focusFab) {
        if (stopTrack) { stopTrack(); stopTrack = null; }
        pop.hidden = true;
        fabs.forEach(function (f) { f.setAttribute('aria-expanded', 'false'); });
        if (focusFab) opener.focus();
      }
      fabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
          var open = pop.hidden;
          if (!open) { close(false); return; }
          opener = btn;
          pop.hidden = false;
          // An in-header button anchors the panel under itself (shared anchoring); the floating pill keeps the stylesheet's corner.
          if (stopTrack) stopTrack();
          if (btn.classList.contains('vt-inline') && window.VisableOverlay) stopTrack = window.VisableOverlay.track(pop, btn, { margin: 14 });
          else if (window.VisableOverlay) window.VisableOverlay.clear(pop);
          btn.setAttribute('aria-expanded', 'true');
          var on = pop.querySelector('[aria-checked="true"]') || pop.querySelector('.vt-opt'); if (on) on.focus();
        });
      });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !pop.hidden) close(true); });
      document.addEventListener('click', function (e) {
        if (pop.hidden || pop.contains(e.target)) return;
        for (var i = 0; i < fabs.length; i++) if (fabs[i].contains(e.target)) return;
        close(false);
      });
      document.body.appendChild(pop);
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(fab, anchor.nextSibling);
        document.body.appendChild(fabs[1]);
      } else document.body.appendChild(fab);
    }
    mountCivicPicker(c);
    relabel();
    ensureFonts(current);
    syncPickers();
    syncWordmarks();
    syncMeta();
    // Brightness toggles and late-rendered headers: keep wordmark + meta in step.
    if (window.MutationObserver) {
      var pending = false;
      var mo = new MutationObserver(function () {
        if (pending) return;
        pending = true;
        (window.requestAnimationFrame || setTimeout)(function () { pending = false; syncWordmarks(); syncMeta(); syncPickers(); });
      });
      mo.observe(document.body, { attributes: true, attributeFilter: ['data-theme'], childList: true, subtree: true });
      mo.observe(root, { attributes: true, attributeFilter: ['data-theme', 'lang'] });
      new MutationObserver(relabel).observe(root, { attributes: true, attributeFilter: ['lang'] });
    }
  }

  window.VisableTheme = { get: function () { return current; }, set: apply, themes: THEMES.slice() };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
