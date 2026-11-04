// @ts-nocheck
/**
 * i18n runtime of index.html (structure map C27): locale resolution, pack loading, the visa-name pack, the official-terms
 * glossary, `tx`/`txAt`/`txArray`, the DOM setters, `localizeStaticDom`, the language menu and `applyLanguage`. Every
 * owner of shared state stays inline in index.html on purpose: `let selectedLocale`, `currentLanguage`, `I18N_MANIFEST`,
 * `VISA_NAME_I18N`, `OFFICIAL_TERMS`, `OFFICIAL_DOC_TERM_INDEX`, `OFFICIAL_TERM_BY_KO_TEXT` and the consts
 * `LANGUAGE_STORAGE_KEY`, `LANGUAGE_OPTIONS`, `LANGUAGE_SUPPORT`, `I18N_MANIFEST_PATH`, `I18N_BASE_PATH`,
 * `UI_TRANSLATIONS`, `BOOTSTRAP_KO_FALLBACK`, `I18N_DEV_WARNINGS` (parse-time localStorage read) and the glossary
 * tables — assets/js (civic-search, visa-route-guide, index-i18n-fallback, …), the e2e specs and legacy scripts read
 * them by bare name or regex-parse them from index.html. This module reads and assigns them by bare name (global
 * lexical scope) and uses Visable.data/state and the inline stubs at call time only (compatibility surface, ADR-009).
 * `tx`, `txAt`, `applyLanguage`, `loadI18nTranslations`, `isLanguageSelectable`, `renderAnnotatedDocLabel`,
 * `findOfficialTermIdForKoreanLabel`, `getLandingHintItems`, `getQuickFilterItems`, `hasFullKoI18nPack`,
 * `languageSupportLevel` and `renderLanguageMenu` keep inline stubs for those runtime callers. Covered by
 * tests/golden/specs/home.spec.mjs (15 languages, language dialog) and search.spec.mjs (guidance language).
 * Moved verbatim from index.html lines 16723-17505 (701 lines; kept inline: ['BOOTSTRAP_KO_FALLBACK', 'I18N_BASE_PATH', 'I18N_DEV_WARNINGS', 'I18N_MANIFEST', 'I18N_MANIFEST_PATH', 'I18N_WARNED_MISSING_KEYS', 'LANGUAGE_OPTIONS', 'LANGUAGE_STORAGE_KEY', 'LANGUAGE_SUPPORT', 'OFFICIAL_DOC_TERM_INDEX', 'OFFICIAL_TERMS', 'OFFICIAL_TERMS_PATH', 'OFFICIAL_TERM_BY_KO_TEXT', 'OFFICIAL_TERM_DISPLAY_CONFIDENCE', 'OFFICIAL_TERM_VERIFIED_CONFIDENCE', 'UI_TRANSLATIONS', 'VISA_NAME_I18N', 'VISA_NAME_I18N_PATH', 'currentLanguage', 'selectedLocale']).
 * Exposed on window.Visable.i18n; 24 inline stubs with the same names delegate here.
 */
// The user's actual selection (drives the selector + persistence). For zh-TW
// this differs from currentLanguage, which holds the *content* locale used by
// tx() and the inline render ternaries (zh-CN, then converted to Traditional).
// Map a selectable locale to the content locale that actually renders.
function contentLocaleFor(code) { return code === 'zh-TW' ? 'zh-CN' : code; }

// Language support level. `full` packs are actively maintained for the main UI
// surfaces; every other selectable language is treated as `partial` (some text
// still falls back to Korean). Drives the partial-language notice + selector
// badge so users are told transparently rather than silently shown Korean.
function languageSupportLevel(code) {
    const normalized = normalizeLocaleCode(code);
    const level = LANGUAGE_SUPPORT[normalized];
    if (level === 'preparing') return 'preparing';
    return level === 'full' && code === normalized ? 'full' : 'partial';
}
// A 'preparing' language (e.g. zh-CN) is kept visible in the selector but cannot
// be activated until its translation pack is complete — this prevents silently
// showing Korean source text under a Chinese label. Assets are preserved.
function isLanguageSelectable(code) {
    return LANGUAGE_OPTIONS.some(lang => lang.code === normalizeLocaleCode(code))
        && languageSupportLevel(code) !== 'preparing';
}


function normalizeLocaleCode(code) {
    if (!code) return 'ko';
    if (I18N_MANIFEST.supportedLocales && I18N_MANIFEST.supportedLocales.includes(code)) return code;
    return (I18N_MANIFEST.localeAliases && I18N_MANIFEST.localeAliases[code]) || code;
}

async function loadI18nTranslations() {
    const fetchJson = (url) => Visable.data.fetchJson(url, { errorMessage: 'i18n load failed: ' + url });
    try {
        I18N_MANIFEST = await fetchJson(I18N_MANIFEST_PATH);
    } catch (err) {
        console.warn('[i18n] manifest unavailable; using built-in ko fallback shell', err);
    }
    const files = I18N_MANIFEST.files || { ko: 'ko.json', en: 'en.json', 'zh-CN': 'zh-CN.json' };
    const supported = I18N_MANIFEST.supportedLocales || Object.keys(files);
    const loaded = await Promise.all(supported.map(async (locale) => {
        const file = files[locale] || (locale + '.json');
        try {
            UI_TRANSLATIONS[locale] = await fetchJson(I18N_BASE_PATH + file);
            return true;
        } catch (err) {
            console.warn('[i18n] ' + locale + ' unavailable', err);
            return false;
        }
    }));
    if (!UI_TRANSLATIONS.ko) UI_TRANSLATIONS.ko = BOOTSTRAP_KO_FALLBACK;
    try {
        const glossary = await fetchJson(OFFICIAL_TERMS_PATH);
        OFFICIAL_TERMS = (glossary && glossary.terms) || {};
    } catch (err) {
        console.warn('[i18n] glossary unavailable; labels fall back to Korean canonical text', err);
        OFFICIAL_TERMS = {};
    }
    indexOfficialTerms();
    try {
        const visaNames = await fetchJson(VISA_NAME_I18N_PATH);
        VISA_NAME_I18N = (visaNames && visaNames.names) || {};
    } catch (err) {
        console.warn('[i18n] name pack unavailable; falling back to Korean canonical names', err);
        VISA_NAME_I18N = {};
    }
    return loaded.some(Boolean);
}

/* Localized display names for top-level status-of-stay codes
   (data/i18n/visa-names.json). Korean stays canonical; missing locales fall
   back along the manifest chain (locale → fallbackLocale). */

function localizedVisaNameFromPack(code, locale = currentLanguage) {
    const lang = normalizeLocaleCode(locale);
    if (lang === 'ko' || !code) return '';
    const entry = VISA_NAME_I18N[String(code).toUpperCase()];
    if (!entry) return '';
    const chain = [lang];
    const fallback = I18N_MANIFEST.fallbackLocale || 'ko';
    if (fallback !== 'ko' && !chain.includes(fallback)) chain.push(fallback);
    for (const key of chain) {
        const value = entry[key];
        if (typeof value === 'string' && value.trim()) return value.trim();
    }
    return '';
}

/* Official terminology glossary (data/i18n/official-terms.json).
   Korean stays canonical everywhere; a glossary translation is appended
   whenever the glossary has ANY value for the active locale (by explicit
   product decision: showing a possibly-imprecise English name is preferred
   over Korean-only). Entries whose confidence is below the "verified" tier
   (fallback / needs-verification) still render, but renderAnnotatedDocLabel
   marks them with a distinct, dotted-underline style + tooltip so a reader
   can tell a machine/best-effort gloss from a confirmed official name. Only
   a genuinely missing glossary entry falls back to Korean-only. */
// Whitespace-normalized Korean-text -> termId index, keyed on each glossary
// entry's own canonical `ko` field. This is the SAME glossary as the docId
// index above; it only adds a second, independent way to reach an already-
// vetted term for document names that never carry a doc_* id (the direct
// documents_initial/extension/registration string fields most records use).
function normalizeOfficialTermMatchText(s) {
    return String(s || '').replace(/\s+/g, '');
}

function indexOfficialTerms() {
    OFFICIAL_DOC_TERM_INDEX = {};
    OFFICIAL_TERM_BY_KO_TEXT = {};
    Object.keys(OFFICIAL_TERMS).forEach((termId) => {
        const entry = OFFICIAL_TERMS[termId];
        const docIds = entry && Array.isArray(entry.docIds) ? entry.docIds : [];
        docIds.forEach((docId) => {
            if (docId && !OFFICIAL_DOC_TERM_INDEX[docId]) OFFICIAL_DOC_TERM_INDEX[docId] = termId;
        });
        const koKey = normalizeOfficialTermMatchText(entry && entry.ko);
        if (koKey && !OFFICIAL_TERM_BY_KO_TEXT[koKey]) OFFICIAL_TERM_BY_KO_TEXT[koKey] = termId;
    });
}

/* Resolve a rendered Korean document-name string to a glossary termId without
   requiring a doc_* id. Two lookup passes, both grounded in the SAME curated
   glossary — neither can ever assert a translation the glossary doesn't
   already carry:
     1. Whitespace-normalized full-text match against a term's `ko` field
        (tolerates incidental spacing differences, e.g. DOC_DICT's
        "통합신청서 (별지 제34호 서식)" vs the glossary's "통합신청서(별지 제34호 서식)").
     2. Fallback to the existing document-family classifier
        (normalizeDocumentRequirementKey, already used by the Standard
        checklist's own fee/dedupe logic) — trusted ONLY when the family
        label it returns is itself textually identical to a glossary term's
        `ko` field (e.g. family '여권' === term ko '여권'). This never invents
        a new mapping; it only confirms two already-vetted labels agree, so a
        specific numbered form (별지 제34호) can never be over-generalized
        from a generic family match. */
function findOfficialTermIdForKoreanLabel(koreanLabel) {
    // The canonical display wording of the generic application form is the same
    // document as the glossary's 별지 제34호 entry; reuse that existing term
    // instead of inventing a new translation.
    if (typeof paradisoGlossaryLabelForAppForm === 'function') koreanLabel = paradisoGlossaryLabelForAppForm(koreanLabel);
    const directKey = normalizeOfficialTermMatchText(koreanLabel);
    if (directKey && OFFICIAL_TERM_BY_KO_TEXT[directKey]) return OFFICIAL_TERM_BY_KO_TEXT[directKey];
    if (typeof normalizeDocumentRequirementKey === 'function') {
        const familyKey = normalizeOfficialTermMatchText(normalizeDocumentRequirementKey(koreanLabel));
        if (familyKey && OFFICIAL_TERM_BY_KO_TEXT[familyKey]) return OFFICIAL_TERM_BY_KO_TEXT[familyKey];
    }
    return '';
}

function officialTermTranslation(termId, locale = currentLanguage) {
    const entry = OFFICIAL_TERMS[termId];
    if (!entry) return null;
    const code = normalizeLocaleCode(locale);
    if (code === 'ko') return null;
    const value = entry[code];
    if (typeof value !== 'string' || !value.trim()) return null;
    const confidence = entry.confidence && entry.confidence[code];
    if (!OFFICIAL_TERM_DISPLAY_CONFIDENCE.includes(confidence)) return null;
    return value.trim();
}

// Whether a term's translation for this locale is at the "verified" tier
// (canonical/official/manual-derived/curated) vs. a lower, still-displayed
// tier (fallback/needs-verification) — drives the unverified visual marker.
function isOfficialTermVerified(termId, locale = currentLanguage) {
    const entry = OFFICIAL_TERMS[termId];
    if (!entry) return false;
    const code = normalizeLocaleCode(locale);
    const confidence = entry.confidence && entry.confidence[code];
    return OFFICIAL_TERM_VERIFIED_CONFIDENCE.includes(confidence);
}

function annotateOfficialDocLabel(docId, koreanLabel) {
    const termId = OFFICIAL_DOC_TERM_INDEX[docId];
    if (!termId) return koreanLabel;
    const translation = officialTermTranslation(termId);
    if (!translation) return koreanLabel;
    const label = String(koreanLabel);
    if (label.toLowerCase().includes(translation.toLowerCase())) return label;
    return label + ' (' + translation + ')';
}

/* Safe-HTML document-name label: Korean canonical name, plus a glossary
   translation in parentheses when (and only when) findOfficialTermIdForKoreanLabel
   resolves one — the Standard 구비서류 tabs and the Easy Mode checklist both use
   this so a document name reads the same bilingual way in both views. Returns
   pre-escaped HTML (both parts individually escaped) — callers must NOT wrap
   the result in escapeHtml() again. The translation span carries its own
   explicit lang so it reads correctly even inside a Korean-lang ancestor
   (Easy Mode's <ul lang="ko">). A fallback/needs-verification-tier
   translation gets an extra modifier class + title tooltip so a reader can
   tell it apart from a confirmed official name. */
function renderAnnotatedDocLabel(koreanLabel) {
    const label = String(koreanLabel || '');
    const escaped = escapeHtml(label);
    if (!label) return escaped;
    const termId = findOfficialTermIdForKoreanLabel(label);
    const translation = termId ? officialTermTranslation(termId) : null;
    if (!translation || label.toLowerCase().includes(translation.toLowerCase())) return escaped;
    const lang = normalizeLocaleCode(currentLanguage);
    const verified = isOfficialTermVerified(termId);
    const cls = verified ? 'doc-name-i18n' : 'doc-name-i18n doc-name-i18n--unverified';
    const title = verified ? '' : ` title="${escapeHtml(tx('docNameTranslationUnverifiedHint') || 'Not an officially confirmed translation — check the Korean name with the office if unsure.')}"`;
    return `${escaped} <span class="${cls}" lang="${escapeHtml(lang)}"${title}>(${escapeHtml(translation)})</span>`;
}

function hasFullKoI18nPack() {
    return Boolean(
        UI_TRANSLATIONS.ko &&
        UI_TRANSLATIONS.ko.heroTitle &&
        Array.isArray(UI_TRANSLATIONS.ko.landingHints) &&
        Array.isArray(UI_TRANSLATIONS.ko.quickFilters)
    );
}


function tx(key, vars = {}) {
    const koPack = UI_TRANSLATIONS.ko || BOOTSTRAP_KO_FALLBACK;
    const pack = UI_TRANSLATIONS[normalizeLocaleCode(currentLanguage)] || koPack;
    let value = pack[key] ?? koPack[key];
    if (value === undefined) {
        if (I18N_DEV_WARNINGS && !I18N_WARNED_MISSING_KEYS.has(key)) {
            I18N_WARNED_MISSING_KEYS.add(key);
            console.warn('[i18n] missing key: ' + key);
        }
        value = key;
    }
    if (typeof value !== 'string') return value;
    Object.entries(vars).forEach(([k, v]) => { value = value.replaceAll(`{${k}}`, v); });
    return value;
}

function setText(selector, text) {
    const el = document.querySelector(selector);
    if (el) el.textContent = text;
}

function setHtml(selector, html) {
    const el = document.querySelector(selector);
    if (el) el.innerHTML = html;
}

function setAttr(selector, attr, value) {
    const el = document.querySelector(selector);
    if (el) el.setAttribute(attr, value);
}

function setIndexedText(selector, values) {
    document.querySelectorAll(selector).forEach((el, idx) => {
        if (values[idx] !== undefined) el.textContent = values[idx];
    });
}

function setIndexedHtml(selector, values) {
    document.querySelectorAll(selector).forEach((el, idx) => {
        if (values[idx] !== undefined) el.innerHTML = values[idx];
    });
}

function setIndexedAttr(selector, attr, values) {
    document.querySelectorAll(selector).forEach((el, idx) => {
        if (values[idx] !== undefined) el.setAttribute(attr, values[idx]);
    });
}

/* Declarative static-markup localizer. The HTML is authored in Korean (the
   no-JS fallback); elements that carry one of these attributes get their text
   swapped to the active language pack on load and on every language change:
     data-i18n="key"            → textContent  = tx(key)
     data-i18n-html="key"       → innerHTML     = tx(key)   (allows inline tags)
     data-i18n-attr="attr:key;…"→ setAttribute(attr, tx(key))   (placeholders/aria)
   Fail-safe: when a key is missing the pack, tx() returns the key itself, so we
   leave the authored Korean untouched rather than printing a raw key. This is
   the single mechanism that prevents Korean leaking through surfaces that were
   never wired into the explicit setText() calls below. */
function localizeStaticDom(root = document) {
    root.querySelectorAll('[data-i18n]').forEach((el) => {
        const key = el.getAttribute('data-i18n');
        const value = tx(key);
        if (typeof value === 'string' && value !== key) el.textContent = value;
    });
    root.querySelectorAll('[data-i18n-html]').forEach((el) => {
        const key = el.getAttribute('data-i18n-html');
        const value = tx(key);
        if (typeof value === 'string' && value !== key) el.innerHTML = value;
    });
    root.querySelectorAll('[data-i18n-attr]').forEach((el) => {
        el.getAttribute('data-i18n-attr').split(';').forEach((pair) => {
            const sep = pair.indexOf(':');
            if (sep === -1) return;
            const attr = pair.slice(0, sep).trim();
            const key = pair.slice(sep + 1).trim();
            if (!attr || !key) return;
            const value = tx(key);
            if (typeof value === 'string' && value !== key) el.setAttribute(attr, value);
        });
    });
}

function txArray(key) {
    const value = tx(key);
    return Array.isArray(value) ? value : [];
}

function txAt(key, idx, fallback = '') {
    const values = txArray(key);
    return values[idx] !== undefined ? values[idx] : fallback;
}

function getLanguageOption(code = currentLanguage) {
    const normalized = normalizeLocaleCode(code);
    return LANGUAGE_OPTIONS.find(lang => lang.code === normalized) || LANGUAGE_OPTIONS.find(lang => lang.code === code) || LANGUAGE_OPTIONS[0];
}

function getStoredLanguage() {
    try {
        const stored = normalizeLocaleCode(Visable.state.read(LANGUAGE_STORAGE_KEY));
        return isLanguageSelectable(stored) ? stored : 'ko';
    } catch (e) {
        return 'ko';
    }
}

function getInitialLanguage() {
    try {
        // Only honor an explicit ?lang= override when one is actually present.
        // (normalizeLocaleCode(null) resolves to 'ko', so without this guard the
        // stored language is never restored — persistence would silently break.)
        const raw = new URLSearchParams(window.location.search).get('lang');
        if (raw) {
            const requested = normalizeLocaleCode(raw);
            if (isLanguageSelectable(requested)) return requested;
        }
    } catch (e) {}
    return getStoredLanguage();
}

function renderLanguageMenu() {
    const menu = document.getElementById('languageMenu');
    if (!menu) return;
    const options = LANGUAGE_OPTIONS.map(lang => {
        const level = languageSupportLevel(lang.code);
        if (level === 'preparing') {
            // Disabled + no apply-language action so it can never be activated;
            // the inline note + title explain why.
            const note = escapeHtml(tx('languagePreparingNotice'));
            return `
        <button type="button" class="language-option language-option-preparing" role="option" aria-disabled="true" disabled data-lang="${lang.code}" title="${note}">
            <span class="language-option-code">${lang.short}</span>
            <span><span class="language-option-name">${lang.name}<span class="language-option-badge">${escapeHtml(tx('languagePreparingBadge'))}</span></span><br><span class="language-option-local">${note}</span></span>
            <span class="language-option-check" aria-hidden="true"></span>
        </button>
    `;
        }
        const partial = level === 'partial';
        const badge = partial ? `<span class="language-option-badge">${escapeHtml(tx('languagePartialBadge'))}</span>` : '';
        return `
        <button type="button" class="language-option" role="option" aria-selected="${lang.code === selectedLocale ? 'true' : 'false'}" data-action="apply-language" data-lang="${lang.code}">
            <span class="language-option-code">${lang.short}</span>
            <span><span class="language-option-name">${lang.name}${badge}</span><br><span class="language-option-local">${lang.local}</span></span>
            <span class="language-option-check" aria-hidden="true">${lang.code === selectedLocale ? '✓' : ''}</span>
        </button>
    `;
    }).join('');
    // Non-blocking transparency notice: only shown when the active language is
    // partial, so full languages (ko/en/zh-CN) stay uncluttered.
    const notice = languageSupportLevel(currentLanguage) === 'partial'
        ? `<div class="language-partial-notice" role="note" data-language-partial-notice>${escapeHtml(tx('partialLanguageNotice'))}</div>`
        : '';
    menu.innerHTML = options + notice;
}

function toggleLanguageMenu(forceOpen) {
    const menu = document.getElementById('languageMenu');
    const btn = document.getElementById('languageBtn');
    if (!menu || !btn) return;
    const open = forceOpen === undefined ? !menu.classList.contains('open') : forceOpen;
    menu.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) toggleCityMenu(false);
}

function getLandingHintItems() {
    const labels = txArray('landingHints');
    const koLabels = Array.isArray(UI_TRANSLATIONS.ko?.landingHints) ? UI_TRANSLATIONS.ko.landingHints : BOOTSTRAP_KO_FALLBACK.landingHints;
    const queries = BOOTSTRAP_KO_FALLBACK.landingHints;
    const items = queries.map((q, idx) => ({ l: labels[idx] || koLabels[idx] || q, q }));
    for (let i = items.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [items[i], items[j]] = [items[j], items[i]]; }
    return items;
}

function getQuickFilterItems() {
    const labels = txArray('quickFilters');
    const koLabels = Array.isArray(UI_TRANSLATIONS.ko?.quickFilters) ? UI_TRANSLATIONS.ko.quickFilters : BOOTSTRAP_KO_FALLBACK.quickFilters;
    const queries = BOOTSTRAP_KO_FALLBACK.quickFilters;
    return queries.map((q, idx) => ({ l: labels[idx] || koLabels[idx] || q, q }));
}

function updateThemeLabel() {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textEl = document.querySelector('.theme-btn-text');
    const label = isDark ? tx('themeLight') : tx('themeDark');
    if (textEl) textEl.textContent = label;
    setAttr('#mainThemeBtn', 'aria-label', tx('themeButton'));
    setAttr('#mainThemeBtn', 'title', tx('themeButton'));
}

function updateSearchMetaText() {
    if (!rcEl) return;
    if (!dataReady) {
        rcEl.textContent = tx('dataLoading');
    } else if (!document.body.classList.contains('searched') && !qEl?.value) {
        rcEl.textContent = '';
    }
}

// Turn the Traditional-Chinese display layer on/off. In zh-TW mode the app
// still renders Simplified (currentLanguage === 'zh-CN'); zh-traditional.js
// converts the rendered DOM text to Traditional and keeps converting as new
// content is rendered. Switching away re-renders chrome back to the target
// language; the observer is stopped so nothing is re-converted.
function applyTraditionalChineseMode(on) {
    const zt = (typeof window !== 'undefined') && window.ParadisoZhT;
    if (!zt) return;
    if (on) { if (!zt.isActive()) zt.start(); }
    else if (zt.isActive()) { zt.stop(); }
}

function applyLanguage(code, options = {}) {
    if (!hasFullKoI18nPack()) code = 'ko';
    code = normalizeLocaleCode(code);
    // Never activate a non-selectable (preparing) or unknown language; keep the
    // current language if it is valid, otherwise fall back to Korean.
    if (!isLanguageSelectable(code)) code = isLanguageSelectable(selectedLocale) ? selectedLocale : 'ko';
    selectedLocale = code;
    // Content renders in the content locale (zh-TW → zh-CN); the Traditional
    // script conversion is applied to the rendered DOM by zh-traditional.js.
    currentLanguage = contentLocaleFor(code);
    const lang = getLanguageOption(code);
    document.documentElement.lang = lang.html;
    document.documentElement.dir = lang.dir || 'ltr';
    Visable.state.write(LANGUAGE_STORAGE_KEY, code);
    applyTraditionalChineseMode(code === 'zh-TW');
    // Supplementary leak fallback for the 9 non-ko/en/zh locales (inactive otherwise).
    if (typeof window !== 'undefined' && window.ParadisoIndexFallback) window.ParadisoIndexFallback.setLang(currentLanguage);

    setAttr('#languageBtn', 'aria-label', tx('languageButton'));
    setAttr('#languageBtn', 'title', tx('languageButton'));
    setAttr('#languageMenu', 'aria-label', tx('languageMenu'));
    setText('#languageBtnCode', lang.short);
    setText('#languageBtnNative', lang.name);
    renderLanguageMenu();
    setText('.easy-mode-btn-text', tx('easyModeEasy'));
    setAttr('#easyModeBtn', 'aria-label', tx('easyModeEasy'));
    updateEasyModeButton();

    if (!hasFullKoI18nPack()) {
        updateSearchMetaText();
        return;
    }

    setAttr('#cityBtn', 'aria-label', tx('cityButton'));
    setAttr('#citySearch', 'placeholder', tx('cityPlaceholder'));
    setAttr('#citySearch', 'aria-label', tx('citySearchAria'));
    updateThemeLabel();
    updateEditorialThemeLabel();
    setAttr('.logo-area', 'aria-label', tx('reset'));
    setText('.p-hero-eyebrow', tx('heroEyebrow'));
    // 확정 시안(507:2150)의 2행 구성: 1행 = heroTitle + 초록 heroEm, 2행 = heroTail.
    // heroTail 이 빈 로케일(한국어 외)은 1행만 렌더한다.
    const heroTail = tx('heroTail');
    setHtml('#pHeroTitle',
        `<span class="p-hero-line">${tx('heroTitle')} <em>${tx('heroEm')}</em></span>` +
        (heroTail ? `<span class="p-hero-line">${heroTail}</span>` : ''));
    setHtml('.p-hero-sub', tx('heroSub'));
    setAttr('.p-hero-proof', 'aria-label', 'Visable');
    setIndexedText('.p-proof-chip', [tx('proof1'), tx('proof2'), tx('proof3')]);
    setAttr('.p-gateway', 'aria-label', tx('gwAriaLabel'));
    setAttr('.p-gw-primary', 'aria-label', tx('gwPrimaryAria'));
    setAttr('.p-gw-utility', 'aria-label', tx('gwUtilityAria'));
    setText('.p-gw-search-title', tx('heroSearchPlaceholder'));
    setText('.p-gw-search-sub', tx('gwSearchSub'));
    setIndexedText('.p-gw-primary .p-gw-card-label', [tx('gwDocLabel'), tx('gwHikoreaLabel'), tx('gwAiLabel')]);
    setIndexedText('.p-gw-primary .p-gw-card-sub', [tx('gwDocSub'), tx('gwHikoreaSub'), tx('gwAiSub')]);
    setIndexedText('.p-gw-primary .p-gw-card-go', [tx('gwDocGo'), tx('gwHikoreaGo'), tx('gwAiGo')]);
    setText('.p-gw-card-visa .p-gw-card-go', tx('gwSearchGo'));
    setText('.p-gw-card-support .p-gw-card-go', tx('gwSupportGo'));
    setText('#gwNewHomeGo', tx('gwNewHomeGo'));
    setIndexedText('.p-gw-util-label', [tx('gwShortStayLabel'), tx('gwJobcodeLabel'), tx('jurisdiction'), tx('gwAgentLabel'), tx('gwMedLabel')]);
    setIndexedText('.p-gw-util-restored .p-gw-util-label', [tx('gwRestoredEntry'), tx('gwRestoredPathways'), tx('gwRestoredReminder')]);
    setText('#gwNewHomeLabel', tx('gwNewHomeLabel'));
    setText('#gwNewHomeSub', tx('gwNewHomeSub'));
    setText('#gwNewHomeDesc', tx('gwNewHomeDesc'));
    setText('#gwNewHomeTagline', tx('gwNewHomeTagline'));
    setAttr('#gwNewHomeLink', 'aria-label', tx('gwNewHomeAria'));
    setText('#pGwHeadTitle', tx('gwHeadTitle'));
    setText('#pGwHeadSub', tx('gwHeadSub'));
    setText('#pHeroFoot', tx('heroFoot'));
    setText('#pFooterNotice', tx('footerNotice'));
    setIndexedText('.p-kinetic-line', [tx('heroMarquee'), tx('heroMarquee')]);
    setText('#pCmdChipsTitle', tx('cmdChipsTitle'));
    setText('#pCmdDisclaimer', tx('cmdDisclaimer'));
    setText('.p-cmd-close-label', tx('cmdCloseLabel'));
    setAttr('.p-cmd-close', 'aria-label', tx('cmdCloseAria'));
    renderCmdChips();
    setText('#visaDrawerEyebrow', tx('drawerEyebrow'));
    setText('#visaDrawerDisclaimer', tx('drawerDisclaimer'));
    setAttr('.visa-drawer-close', 'aria-label', tx('drawerCloseAria'));
    setAttr('.p-entry-rail', 'aria-label', tx('entryRail'));
    setIndexedText('.p-entry-title', [tx('entryATitle'), tx('entryBTitle')]);
    setIndexedText('.p-entry-sub', [tx('entryASub'), tx('entryBSub')]);
    setAttr('.visa-track-card:nth-child(1)', 'aria-label', tx('preTrackAria'));
    setAttr('.visa-track-card:nth-child(2)', 'aria-label', tx('inTrackAria'));
    setIndexedText('.visa-track-title', [tx('preTrackTitle'), tx('inTrackTitle')]);
    setIndexedText('.visa-track-desc', [tx('preTrackDesc'), tx('inTrackDesc')]);
    document.documentElement.style.setProperty('--lang-visa-label', JSON.stringify(tx('visaLabel')));
    document.documentElement.style.setProperty('--lang-scenario-selected-choice', JSON.stringify(tx('scenarioSelectedChoice')));
    const sourceBadgeLabels = txArray('aiSourceBadgeLabels');
    const sourceBadgeFallbackLabels = BOOTSTRAP_KO_FALLBACK.aiSourceBadgeLabels;
    [
        ['--lang-gp-verified', 0],
        ['--lang-gp-source-supported', 1],
        ['--lang-gp-partial', 2],
        ['--lang-gp-needs-review', 3],
        ['--lang-gp-advisory', 4],
        ['--lang-gp-extracted-only', 5],
        ['--lang-gp-source-linked-unverified', 6],
        ['--lang-gp-disabled', 7],
        ['--lang-gp-not-wired', 8],
        ['--lang-gp-failed', 9],
        ['--lang-gp-related', 10]
    ].forEach(([property, index]) => {
        document.documentElement.style.setProperty(property, JSON.stringify(sourceBadgeLabels[index] || sourceBadgeFallbackLabels[index] || ''));
    });

    setAttr('#q', 'aria-label', tx('qAria'));
    if (qEl) qEl.placeholder = qEl.disabled ? tx('dataLoading') : tx('qPlaceholder');
    setAttr('#xb', 'aria-label', tx('xbAria'));
    setAttr('.sbar-go', 'aria-label', tx('submitSearch'));
    setAttr('.ctrls', 'aria-label', tx('ctrlsAria'));
    setText('[data-action="toggle-accordions"][data-fold="true"]', tx('fold'));
    setText('[data-action="toggle-accordions"][data-fold="false"]', tx('unfold'));
    setText('#landingHintsTitle', tx('hintsTitle'));
    setAttr('#landingHints', 'aria-label', tx('hintsAria'));
    setAttr('.hero-ai-secondary', 'aria-label', tx('aiSecondaryAria'));
    setHtml('.hero-ai-link', `${tx('aiLink')} <strong>Waymaker</strong>`);
    setHtml('.ai-fab', `${tx('aiLink')} <strong>Waymaker</strong>`);
    setText('.reference-disclaimer', tx('reference'));
    setHtml('#brandHeroTitle', tx('brandHeroTitle'));
    setText('.brand-hero-subtitle', tx('brandHeroSubtitle'));
    setIndexedText('.brand-hero-buttons .btn span:first-child', txArray('brandHeroButtons'));
    setIndexedText('.brand-hero-buttons .btn-primary span:first-child, .figma-footer-actions .btn-primary span:first-child', [tx('brandHeroAbout'), tx('footerStart')]);
    setIndexedText('.brand-hero-buttons .btn-secondary span:first-child, .figma-footer-actions .btn-secondary span:first-child', [tx('brandHeroHotline'), tx('footerHotline')]);
    setAttr('.brand-hero-stats', 'aria-label', tx('brandHeroStatsAria'));
    setIndexedHtml('.brand-hero-stats .stat-label', txArray('brandHeroStats'));
    setHtml('#pManualTitle', tx('manualTitle'));
    setText('.p-manual-section .p-section-copy', tx('manualCopy'));
    setIndexedText('.p-manual-kind', txArray('manualCardKinds'));
    setIndexedText('.p-manual-card h3', txArray('manualCardTitles'));
    setIndexedText('.p-manual-card p', txArray('manualCardDescs'));
    // NOTE: the manual-section note (#pManualNote) is localized via data-i18n in
    // markup. A bare '.p-manual-note' selector here would hit #docComposerNote
    // first (it shares the class) and never reach the real note.
    setHtml('#docComposerTitle', tx('docComposerTitle'));
    setText('#docComposerCopy', tx('docComposerCopy'));
    setText('#docComposerFormTitle', tx('docComposerFormTitle'));
    setText('#docComposerFormDesc', tx('docComposerFormDesc'));
    setHtml('#docComposerFormCta', `${escapeHtml(tx('docComposerFormCta'))} →`);
    setText('#docComposerDownloadTitle', tx('docComposerDownloadTitle'));
    setText('#docComposerDownloadDesc', tx('docComposerDownloadDesc'));
    setHtml('#docComposerDownloadCta', `${escapeHtml(tx('docComposerDownloadCta'))} ↗`);
    setText('#docComposerPrintTitle', tx('docComposerPrintTitle'));
    setText('#docComposerPrintDesc', tx('docComposerPrintDesc'));
    setText('#docComposerBadgeLive', tx('docComposerBadgeLive'));
    setText('#docComposerBadgeExternal', tx('docComposerBadgeExternal'));
    setText('#docComposerBadgeGuide', tx('docComposerBadgeGuide'));
    setText('#docComposerNote', tx('docComposerNote'));
    renderDocComposerTags();
    setText('#pPathwayTitle', tx('pathwayTitle'));
    setText('.p-pathway-section .p-section-copy', tx('pathwayCopy'));
    setAttr('.p-pathway-grid', 'aria-label', tx('pathwayAria'));
    setIndexedHtml('.p-pathway-title', txArray('pathwayTitles'));
    setIndexedText('.p-pathway-desc', txArray('pathwayDescs'));
    setIndexedText('.p-pathway-codes .p-code', txArray('pathwayCodes'));
    setText('#pHowTitle', tx('howTitle'));
    setIndexedText('.p-how-step h3', txArray('howStepTitles'));
    setIndexedText('.p-how-step p', txArray('howStepDescs'));
    setText('#pToolsTitle', tx('toolsTitle'));
    setText('.p-tools-section .p-section-copy', tx('toolsCopy'));
    setIndexedText('.p-tool-card h3', txArray('toolTitles'));
    setIndexedText('.p-tool-card p', txArray('toolDescs'));
    setText('#agentFinderTitle', tx('agentTitle'));
    setText('#agentFinder .p-section-copy', tx('agentSectionCopy'));
    setText('#agentFinder .p-section-copy', tx('agentCopy'));
    setText('#agentFinderSourceNote', tx('agentSourceNote'));
    setText('#agentFinderDisclaimerText', tx('agentDisclaimer'));
    setText('label[for="agentFinderRegion"]', tx('agentRegionLabel'));
    setAttr('#agentFinderRegion', 'aria-label', tx('agentRegionLabel'));
    setText('#agentFinderRegion option[value=""]', tx('agentRegionAll'));
    setText('label[for="agentFinderKeyword"]', tx('agentKeywordLabel'));
    setAttr('#agentFinderKeyword', 'placeholder', tx('agentKeywordPlaceholder'));
    setAttr('#agentFinderList', 'aria-label', tx('agentListAria'));
    setText('#agentFinderPrompt', tx('agentPrompt'));
    setText('#agentFinderLoading', tx('agentLoading'));
    setText('#agentFinderEmpty', tx('agentEmpty'));
    setText('#agentFinderErrorText', tx('agentError'));
    setText('#agentFinderShowMore', tx('agentShowMore'));
    setText('#medFinderTitle', tx('medTitle'));
    setText('#medFinder .p-kicker', tx('medKicker'));
    setText('#medFinder .p-section-copy', tx('medCopy'));
    setText('#medFinderSourceNote', tx('medSourceNote'));
    setText('#medFinderDisclaimerText', tx('medDisclaimer'));
    setAttr('#medFinderChips', 'aria-label', tx('medChipsAria'));
    setText('label[for="medFinderKeyword"]', tx('medKeywordLabel'));
    setAttr('#medFinderKeyword', 'placeholder', tx('medKeywordPlaceholder'));
    setAttr('#medFinderClear', 'aria-label', tx('medClearAria'));
    setAttr('#medFinderList', 'aria-label', tx('medListAria'));
    setText('#medFinderPrompt', tx('medPrompt'));
    setText('#medFinderLoading', tx('medLoading'));
    setText('#medFinderEmpty', tx('medEmpty'));
    setText('#medFinderErrorText', tx('medError'));
    setText('#medFinderShowMore', tx('medShowMore'));
    if (typeof window.updateMedFinderLanguage === 'function') window.updateMedFinderLanguage();
    // Reminder feature: Korean-only UI text managed in markup; i18n keys removed (out of scope for MVP).
    setText('#aboutMeTitle', tx('aboutTitle'));
    setAttr('#anagram', 'aria-label', tx('anagramAria'));
    setHtml('.anagram-right h3', tx('philosophyTitle'));
    setIndexedHtml('.philosophy-list li', txArray('philosophyItems'));
    setText('.intro-text h3', tx('aboutStartTitle'));
    setText('.intro-text p', tx('aboutStartBody'));
    setText('.about-hobbies > h3', tx('valuesTitle'));
    setText('.about-hobbies > p', tx('valuesBody'));
    setIndexedAttr('.hobby-card', 'aria-label', txArray('valueCardAria'));
    setIndexedText('.hobby-desc', txArray('valueCardDescs'));
    setHtml('.exp-heading', tx('roadmapTitle'));
    setText('.figma-roadmap-note', tx('roadmapNote'));
    setIndexedText('.exp-company', txArray('roadmapCompanies'));
    setIndexedText('.exp-detail', txArray('roadmapDetails'));
    setHtml('.figma-footer-hero-title', tx('footerHeroTitle'));
    setIndexedText('.figma-footer-chips .footer-chip', txArray('footerChips'));
    setHtml('#pFooterCtaTitle', tx('footerCtaTitle'));
    setText('.p-footer-cta > p', tx('footerCtaCopy'));
    setIndexedText('.p-footer-actions .p-cta-btn', txArray('footerCtaButtons'));
    setText('.p-footer-cta-note', tx('footerCtaNote'));
    setText('.p-reminder-banner__cta', tx('reminderBannerCta'));
    setAttr('#reminderBannerClose', 'aria-label', tx('reminderBannerCloseAria'));
    setAttr('#qf', 'aria-label', tx('quickFiltersAria'));
    setHtml('.ft', `<span class="ft-logo">Visable</span> ${tx('footerLegal')}`);
    setAttr('.modal-close', 'aria-label', tx('closeModal'));
    setText('#docModalTitle', tx('docModalTitle'));
    setHtml('#faqModalTitle', tx('faqModalTitle'));
    setText('#aiModalTitleText', tx('aiModalTitle'));
    setText('#aiModalOverlay .modal-body > p', tx('aiIntro'));
    setText('label[for="aiInput"]', tx('aiInputLabel'));
    setAttr('#aiInput', 'placeholder', tx('aiInputPlaceholder'));
    setIndexedText('.ai-quick-actions .ai-action-btn span', txArray('aiActionLabels'));
    setHtml('#jobCodeModalTitle', jcIcon('compass', 'jc-ic--title') + tx('jobCodeTitle'));
    setText('label[for="jcSearchInput"]', tx('jobCodeSearchLabel'));
    setAttr('#jcSearchInput', 'placeholder', tx('jobCodePlaceholder'));
    setText('#jcAskHeading', tx('jobCodeAskHeading'));
    setText('#jcAskHelper', tx('jobCodeAskHelper'));
    setText('#jcConceptExplain', tx('jobCodeConceptExplain'));
    setText('#jcConceptExpand', tx('jobCodeConceptExpand'));
    setText('#jcExamplesLabel', tx('jobCodeExamplesLabel'));
    setText('#jcStepperH', tx('jobCodeStepperTitle'));
    setText('#jcFinalCheckH', tx('jobCodeFinalCheckTitle'));
    setText('#jcFinalOcc', tx('jobCodeFinalOcc'));
    setText('#jcFinalInd', tx('jobCodeFinalInd'));
    setText('#jcFinalIncome', tx('jobCodeFinalIncome'));
    setText('#jcFinalConfirm', tx('jobCodeFinalConfirm'));
    setText('#jcIncomeReminderTitle', tx('jobCodeIncomeReminderTitle'));
    setText('#jcIncomeReminderBody', tx('jobCodeIncomeNote'));
    updateJobcodeNaturalSearchLabel();
    setHtml('#jurisdictionModalTitle', tx('jurisdictionTitle'));
    // Every modal/drawer close control carries the same Korean aria-label in
    // markup; setAttr() only hits the first, so localize them all here.
    document.querySelectorAll('.modal-close, .visa-drawer-close, .subcode-detail-back, .subcode-detail-close').forEach((el) => {
        if (!el.hasAttribute('data-i18n-attr')) el.setAttribute('aria-label', tx('closeModal'));
    });
    localizeStaticDom();
    localizeFinderRegions();
    if (typeof updateAgentFinderLanguage === 'function') updateAgentFinderLanguage();
    setDirectSearchToggleState(document.getElementById('searchToggleBtn')?.getAttribute('aria-expanded') === 'true');
    if (document.body.classList.contains('searched') && dataReady) renderResults(qEl?.value || '');
    if (dataReady) initUI();
    window.dispatchEvent(new CustomEvent('paradiso-language-applied'));
    updateSearchMetaText();
    if (!options.silent) showToast(tx('languageChanged'), 'success');
}

// Keep the mobile browser chrome (theme-color) in sync with the active theme's
// surface colour instead of a fixed dark navy that clashed with the cream UI.
function updateThemeColorMeta(){
    const meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) return;
    // Read from <body>: the light/dark override sets --bg0 on body[data-theme],
    // while the editorial theme sets it on <html> — body inherits both.
    let bg = (getComputedStyle(document.body).getPropertyValue('--bg0') || '').trim();
    if (!bg) bg = getComputedStyle(document.body).backgroundColor;
    if (bg) meta.setAttribute('content', bg);
}

export {
    contentLocaleFor, languageSupportLevel, isLanguageSelectable, normalizeLocaleCode, loadI18nTranslations, localizedVisaNameFromPack,
    normalizeOfficialTermMatchText, indexOfficialTerms, findOfficialTermIdForKoreanLabel, officialTermTranslation, isOfficialTermVerified, annotateOfficialDocLabel,
    renderAnnotatedDocLabel, hasFullKoI18nPack, tx, setText, setHtml, setAttr,
    setIndexedText, setIndexedHtml, setIndexedAttr, localizeStaticDom, txArray, txAt,
    getLanguageOption, getStoredLanguage, getInitialLanguage, renderLanguageMenu, toggleLanguageMenu, getLandingHintItems,
    getQuickFilterItems, updateThemeLabel, updateSearchMetaText, applyTraditionalChineseMode, applyLanguage, updateThemeColorMeta
};
