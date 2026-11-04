// @ts-nocheck
/**
 * Legacy block `visable-global-settings-20260713` (Phase 3, moved verbatim from the inline <script> block in index.html).
 * The IIFE looks up the settings overlay markup (parsed before any module runs), defines
 * window.setGlobalBrightness / openGlobalSettings / closeGlobalSettings and registers listeners; it ran at parse
 * time before and runs at module evaluation now — before DOMContentLoaded and before any user event, with no
 * first-paint side effect (brightness is applied by assets/js/visable-theme.js). Side-effect import from src/main.js.
 */
(function () {
  'use strict';
  var overlay = document.getElementById('globalSettingsOverlay');
  var languageRoot = document.getElementById('globalSettingsLanguages');
  var search = document.getElementById('globalSettingsLanguageSearch');
  var trigger = document.getElementById('editorialThemeBtn');
  var returnFocus = null;
  var systemQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function activeBrightnessChoice() {
    try { return localStorage.getItem('paradiso:brightness') || 'light'; } catch (e) { return 'light'; }
  }

  function renderLanguages(filter) {
    if (!languageRoot || typeof LANGUAGE_OPTIONS === 'undefined') return;
    var needle = String(filter || '').trim().toLowerCase();
    languageRoot.innerHTML = '';
    LANGUAGE_OPTIONS.forEach(function (lang) {
      var haystack = [lang.code, lang.name, lang.local, lang.short].join(' ').toLowerCase();
      if (needle && haystack.indexOf(needle) === -1) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'p-settings-language' + (lang.code === selectedLocale ? ' is-active' : '');
      btn.dataset.action = 'apply-language';
      btn.dataset.lang = lang.code;
      btn.setAttribute('role', 'option');
      btn.setAttribute('aria-selected', lang.code === selectedLocale ? 'true' : 'false');
      btn.textContent = lang.name + ' · ' + lang.short;
      languageRoot.appendChild(btn);
    });
  }

  function syncSettingsState() {
    var city = document.getElementById('cityBtnLabel');
    var time = document.getElementById('cityBtnTime');
    var cityOut = document.getElementById('globalSettingsCity');
    var timeOut = document.getElementById('globalSettingsTime');
    if (cityOut && city) cityOut.textContent = city.textContent;
    if (timeOut && time) timeOut.textContent = time.textContent;
    var easy = document.getElementById('globalSettingsEasy');
    var easySource = document.getElementById('easyModeBtn');
    if (easy && easySource) easy.setAttribute('aria-pressed', easySource.getAttribute('aria-pressed') || 'false');
    var choice = activeBrightnessChoice();
    document.querySelectorAll('[data-action="set-brightness"]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', btn.dataset.brightness === choice ? 'true' : 'false');
    });
    renderLanguages(search ? search.value : '');
  }

  window.setGlobalBrightness = function (choice) {
    if (['light', 'dark', 'system'].indexOf(choice) === -1) return;
    var resolved = choice === 'system'
      ? (systemQuery && systemQuery.matches ? 'dark' : 'light')
      : choice;
    document.body.setAttribute('data-theme', resolved);
    try { localStorage.setItem('paradiso:brightness', choice); } catch (e) {}
    if (typeof updateThemeLabel === 'function') updateThemeLabel();
    if (typeof updateThemeColorMeta === 'function') updateThemeColorMeta();
    syncSettingsState();
  };

  window.openGlobalSettings = function () {
    if (!overlay) return;
    returnFocus = document.activeElement;
    overlay.hidden = false;
    trigger && trigger.setAttribute('aria-expanded', 'true');
    syncSettingsState();
    if (typeof localizeStaticDom === 'function') localizeStaticDom(overlay);
    var close = overlay.querySelector('.p-settings-close');
    if (close) close.focus();
  };

  window.closeGlobalSettings = function () {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    trigger && trigger.setAttribute('aria-expanded', 'false');
    if (returnFocus && typeof returnFocus.focus === 'function') returnFocus.focus();
  };

  if (search) search.addEventListener('input', function () { renderLanguages(search.value); });
  if (overlay) overlay.addEventListener('click', function (event) {
    if (event.target === overlay) window.closeGlobalSettings();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && overlay && !overlay.hidden) window.closeGlobalSettings();
  });
  window.addEventListener('paradiso-language-applied', syncSettingsState);
  if (systemQuery) {
    var onSystemChange = function () {
      if (activeBrightnessChoice() === 'system') window.setGlobalBrightness('system');
    };
    if (typeof systemQuery.addEventListener === 'function') systemQuery.addEventListener('change', onSystemChange);
    else if (typeof systemQuery.addListener === 'function') systemQuery.addListener(onSystemChange);
  }
})();
