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

  var current = resolve();
  if (current) root.setAttribute('data-vt', current);

  /* ---- copy (brand names stay Latin; descriptions per language) ---- */
  var COPY = {
    ko: { title: '화면 테마', fab: '테마', default: '기본 · 맑은 파랑', stamp: '여권 도장', chrome: '유리와 금속', neon: '밤의 네온 · 라이트 모드는 낮 화면' },
    en: { title: 'Display theme', fab: 'Theme', default: 'Default · clear blue', stamp: 'Passport stamps', chrome: 'Glass and metal', neon: 'Night neon · light mode is Day' },
    zh: { title: '界面主题', fab: '主题', default: '默认 · 清蓝', stamp: '护照印章', chrome: '玻璃与金属', neon: '夜间霓虹 · 浅色为白天' }
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

  /* Stamp is the only skin with a display face the site doesn't already load. */
  function ensureFonts(t) {
    if (t !== 'stamp' || document.getElementById('vt-font-stamp')) return;
    var l = document.createElement('link');
    l.id = 'vt-font-stamp';
    l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap';
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
    var coins = document.querySelectorAll('.vt-fab .vt-coin');
    for (var j = 0; j < coins.length; j++) coins[j].setAttribute('data-c', current || 'default');
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
      b.innerHTML = '<span class="vt-coin" data-c="' + t + '" aria-hidden="true"></span><span><span class="vt-name"></span><small></small></span>';
      b.querySelector('.vt-name').textContent = NAMES[t];
      b.querySelector('small').textContent = c[t];
      b.addEventListener('click', function () { apply(t); });
      fs.appendChild(b);
    });
    fs.addEventListener('keydown', function (e) {
      var keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
      if (!(e.key in keys)) return;
      e.preventDefault();
      var i = THEMES.indexOf(current || 'default');
      var n = THEMES[(i + keys[e.key] + THEMES.length) % THEMES.length];
      apply(n);
      var el = fs.querySelector('[data-vt-value="' + n + '"]');
      if (el) el.focus();
    });
    return fs;
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
      var h = document.createElement('h2');
      h.id = 'vtPopTitle';
      h.textContent = c.title;
      pop.appendChild(h);
      pop.appendChild(buildGroup(c, 'vt-pop-'));
      // Narrow screens: the header has no room for one more button, so a floating pill takes over.
      var fabs = [fab];
      if (anchor) {
        var narrow = fab.cloneNode(true);
        narrow.className = 'vt-fab vt-fab-narrow';
        fabs.push(narrow);
      }
      var opener = fab;
      function close(focusFab) {
        pop.hidden = true;
        fabs.forEach(function (f) { f.setAttribute('aria-expanded', 'false'); });
        if (focusFab) opener.focus();
      }
      fabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
          var open = pop.hidden;
          opener = btn;
          if (btn.classList.contains('vt-inline')) {
            var r = btn.getBoundingClientRect();
            pop.style.top = Math.round(r.bottom + 8) + 'px';
            pop.style.right = Math.max(14, Math.round(window.innerWidth - r.right)) + 'px';
            pop.style.left = 'auto';
            pop.style.bottom = 'auto';
          } else {
            pop.style.top = pop.style.right = pop.style.left = pop.style.bottom = '';
          }
          pop.hidden = !open;
          btn.setAttribute('aria-expanded', open ? 'true' : 'false');
          if (open) { var on = pop.querySelector('[aria-checked="true"]') || pop.querySelector('.vt-opt'); if (on) on.focus(); }
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
        (window.requestAnimationFrame || setTimeout)(function () { pending = false; syncWordmarks(); syncMeta(); });
      });
      mo.observe(document.body, { attributes: true, attributeFilter: ['data-theme'], childList: true, subtree: true });
      mo.observe(root, { attributes: true, attributeFilter: ['data-theme', 'lang'] });
    }
  }

  window.VisableTheme = { get: function () { return current; }, set: apply, themes: THEMES.slice() };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
