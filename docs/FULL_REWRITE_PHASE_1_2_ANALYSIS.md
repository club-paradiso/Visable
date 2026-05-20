# Paradiso Full Rewrite — Phase 1+2 Analysis

**Scope:** Pre-rewrite analysis only. No HTML/CSS changes in this PR.
**Branch:** `feature/full-rewrite-figma-aligned`
**Base:** `main` (HEAD: `aeb67fc`, all prior PRs merged)
**Source:** `index.html` @ 12,887 lines / 766 KB
**Figma reference:** Figma Make file `N695iXnoavEOSHITttdCCu` ("Paradiso 후보")

This document delivers the **Phase 1 preservation inventory** and **Phase 2 design system spec** required by the full-rewrite brief. It is intentionally split from the actual rewrite so the user can validate the extraction (especially the JS preservation contract) before any code is replaced.

---

## 0. Executive Summary

### 0.1 Baseline metrics (current `index.html`)

| Metric | Value | Source |
|--------|-------|--------|
| Total lines | 12,887 | `wc -l index.html` |
| `<style>` block | lines 14–7,318 (~7,305 lines) | grep |
| First `<script>` (config) | lines 7,319–7,321 | grep |
| Body markup | lines 7,323–8,251 (~929 lines) | grep |
| Main `<script>` block | lines 8,253–12,885 (~4,633 lines) | grep |
| `:root` blocks | 13 | grep |
| `!important` declarations | 368 | grep |
| Unique hex colors (`#XXXXXX`) | 196 | `grep -oE '#[0-9a-fA-F]{6}'` |
| Distinct `@media` conditions | 16 | audit |
| JS function definitions | **180** | audit |
| JS-referenced DOM IDs (static + dynamic) | ~100 | audit |
| JS-referenced CSS classes | ~90 | audit |
| `data-action` dispatch values | 47 | audit |
| API endpoints | 3 (`/api/visas`, `/api/ask`, `/api/jobcodekeywords`) | audit |
| Static data files | 5 (`visa_data.json`, `data/jobcode_master.json`, `data/agent_registry_2026-04-30.json`, `data/designated_medical_institutions_2026_04_30.json`, `doc_master.json`) | audit |
| Inline `onclick` handlers | 2 (visa-track-card open/close) | grep |
| `localStorage` keys | 2 (`paradiso_city`, `paradiso:language`) | audit |
| `window.*` exports | 3 (`verifyFaqWithAi`, `updateAgentFinderLanguage`, `updateMedFinderLanguage`) + debug | audit |

### 0.2 Brief reconciliation

The rewrite brief stated:
- "JavaScript code from lines **8287 to 12887**" — **actual** main `<script>` block is **8253–12885**. Lines 8253–8285 are the hero spotlight IIFE that listens to `pointermove` on `#hero`. Per agreed scope, the **entire** `<script>...</script>` (8253–12885) is preserved byte-for-byte, plus the 2-line config script at 7319–7321.
- "~167 functions" — **actual: 180** (count includes nested helpers in IIFEs).
- "~36 unique hex colors" — **actual: 196** (deduplicated to ~156 if 3-char `#fff` and uppercase/lowercase are unified).
- "13 conflicting `:root` blocks" — ✅ confirmed.

### 0.3 Recommended path forward

The extraction is clean. The new HTML can deterministically reproduce every wiring point. The new CSS can collapse to ~3,000–4,500 lines if the consolidations in §6 are accepted.

**Critical risks** to surface before Phase 3 begins:

1. **JS reads `document.getElementById('hero')` from the hero spotlight IIFE** — the new HTML must keep `<header id="hero">` (or an equivalent element of that exact id) at the same position so spotlight tracking still works.
2. **47 `data-action` values are dispatched from one central click handler** — every static button + every JS-rendered button must continue to emit the same `data-action` strings. The JS-rendered values (e.g., `open-doc-modal`, `select-procedure`, `select-docs-tab`, `hikorea-next`, etc.) are emitted from inside the preserved JS — they will keep working automatically. Static-HTML ones (e.g., `toggle-search`, `open-jobcode-modal`, `close-*-modal`) must be re-emitted by the new HTML.
3. **`body.searched` vs `body:not(.searched)`** controls landing-vs-result layout via 49 occurrences of `:not(.searched)` selectors in the current CSS. The new CSS should follow the same pattern (`body.landing` is a near-equivalent alternative but `body.searched` is the JS-controlled class — keep it).
4. **`[data-theme="dark"]` is set on `<body>` by `toggleTheme()`** — the new CSS must continue to scope dark-mode overrides to `[data-theme="dark"]` (not `@media (prefers-color-scheme: dark)`) because the user toggle overrides the OS preference.

See §11 (Open questions) for items needing your input before Phase 3.

---

## 1. Hard constraints (re-stated)

Per the rewrite brief, these are immutable:

1. **JS bytes preserved**: `<script>` at lines 8253–12885 is copied verbatim — no function bodies, names, variables, event handlers, fetch URLs, or data flow may change. The 2-line config script at 7319–7321 is also preserved.
2. **Single-file architecture**: one `index.html`, no bundler, no external JS modules.
3. **Vanilla only**: no React, Tailwind, shadcn, npm.
4. **Pretendard font** (CDN as today).
5. **GitHub Pages + Railway API** unchanged.
6. **JS-referenced IDs and classes preserved** — new HTML may add ids/classes, but every existing one in the JS must still exist.
7. **No data file changes** (`visa_data.json` etc. untouched).
8. **No invented immigration facts** — content stays factually equivalent.

---

## 2. Phase 1.1 — JavaScript preservation inventory

### 2.1 Function count by domain

| Domain | Functions | Representative names |
|--------|-----------|----------------------|
| UI helpers | 4 | `escapeHtml`, `escapeRegExp`, `hl`, `showToast` |
| Canvas / horizon background | 10 | `initParadisoHorizon`, `draw`, `mountainPath`, `wavePath`, `themeColors` |
| City / timezone | 6 | `applyCity`, `updateHourFromCity`, `renderCityList`, `toggleCityMenu`, `getTzHour`, `formatTzTime` |
| Search debug | 3 | `getSearchDebugSnapshot`, `ensureSearchDebugPanel`, `debugSearchState` |
| Modal management | 7 | `openModal`, `closeModal`, `openAiModal`, `openDocModal`, `openFaqModal`, `trapModalFocus`, `getLabels` |
| Job code finder | 7 | `loadJobcodeData`, `openJobCodeModal`, `renderJobcodeResults`, `searchJobcodeWithAI`, `renderUnifiedAiResults`, `copyJobcode`, `fallbackCopy` |
| Jurisdiction modal | 4 | `initJurisdictionSelects`, `updateSigungu`, `showJurisdiction`, `openJurisdictionModal` |
| AI / grounding | 8 | `submitAiAnalysis`, `renderGroundingSourcePanel`, `buildModelBadgeHtml`, `mapLawWarningToFriendly`, `renderDocTags`, `formatWon`, `getProcedureFeeInfo`, `renderProcedureFeeBox` |
| Visa data / lookups | 16 | `normalizeVisaCode`, `getVisaNameKo/En`, `getLocalizedVisaName`, `getVisaSubcodes`, `getProcedureLabel`, `keywordMatchesCode`, `getMatchingSubcodes`, `getManualDomains`, `renderDomainBadges`, … |
| Document processing | 17 | `getProcedure`, `toDocArray`, `dedupeDocs`, `mergeDocGroups`, `normalizeDocGroups`, `flattenDocGroups`, `renderDocGroup`, `renderManualDetailBlock`, `renderProcedurePanel`, `renderProcedures`, `renderSubcodes`, … |
| HiKorea guide | 5 | `openHikoreaGuide`, `renderHikoreaGuide`, `hikoreaHotlineStrip`, `hikoreaStepLabel` |
| Result card | 12 | `renderResults`, `renderManualActions`, `renderNextActionArea`, `renderCardSummary`, `renderCautionBlock`, `renderDocumentTabPanel`, `renderDocumentTabs`, `renderSourceEvidencePanel`, `copyVisaResult`, `calculateScore`, `expandKeywords`, `showSuggestions` |
| Search execution | 10 | `executeSearch`, `setDirectSearchToggleState`, `closeDirectSearchMode`, `openDirectSearchMode`, `resetToLanding`, `handleInput`, `handleAutocompleteKeydown`, `clearSearch`, `setSearchMode` |
| Localization | 21 | `tx`, `setText`, `setHtml`, `setAttr`, `setIndexedText`, `txArray`, `txAt`, `getLanguageOption`, `applyLanguage`, `renderLanguageMenu`, `toggleLanguageMenu`, … |
| Theme + accordion | 3 | `updateNightLightClass`, `toggleTheme`, `toggleAccordions` |
| Initialization | 7 | `initUI`, `injectLocalData`, `setSearchEnabled`, `loadVisaData`, `runCountUp`, `initScrollReveal`, `resetReveal` |
| Diaspora flow | 5 | `buildLines`, `startPreEntryTrack`, `startInKoreaTrack`, `showVisaRecommendations`, `selectInKoreaAction` |
| In-Korea visa filter | 4 | `getCurrentInKoreaAction`, `filterInKoreaVisaList`, `searchInKoreaVisa`, `showVisaDocForAction` |
| Agent finder (IIFE) | ~8 internal | `escapeText`, `copyToClipboard`, `buildCard`, `renderSlice`, `applyFilter`, `populateRegions`, `showError`, `loadDataset` + `window.updateAgentFinderLanguage` |
| Medical finder (IIFE) | ~8 internal | same shape as agent finder + `setActiveChip` + `window.updateMedFinderLanguage` |
| Reminder manager (IIFE) | ~13 internal | `load`, `save`, `uid`, `daysUntil`, `formatKoreanDate`, `ddayLabel`, `urgency`, `buildIcs`, `downloadIcs`, `googleCalUrl`, `render`, `showBanner`, `showError` |

Total: **180 function definitions**.

### 2.2 API endpoints (preserved unchanged)

| Method | URL | Caller | Purpose |
|--------|-----|--------|---------|
| POST | `${API_BASE}/api/visas` | `loadVisaData` | Authoritative visa dataset |
| POST | `${API_BASE}/api/ask` | `submitAiAnalysis`, `verifyFaqWithAi` | LLM analysis |
| POST | `${API_BASE}/api/jobcodekeywords` | `searchJobcodeWithAI` | AI job-code keyword expansion |

`API_BASE = window.PARADISO_BACKEND_URL || "https://web-production-14f9a.up.railway.app"` (defined at ~line 8691). Falls back to local `./visa_data.json` if the API call fails.

### 2.3 Static data files (paths must remain valid)

- `./visa_data.json`
- `data/jobcode_master.json` (and root-level `./jobcode_master.json` as fallback)
- `data/output.json` (and `./output.json` fallback) — alternative jobcode source
- `data/agent_registry_2026-04-30.json`
- `data/designated_medical_institutions_2026_04_30.json`
- `doc_master.json` — referenced for procedure metadata

### 2.4 Persistence

- `localStorage.paradiso_city` — selected city object, JSON-stringified
- `localStorage["paradiso:language"]` — language code (`ko` / `en` / `zh` / `vi`)

### 2.5 Window globals exported

- `window.verifyFaqWithAi(visaCode, question)` — called from JS-rendered FAQ buttons
- `window.updateAgentFinderLanguage()` — language switch hook
- `window.updateMedFinderLanguage()` — language switch hook
- `window.__PARADISO_SEARCH_DEBUG__` — debug snapshot (gated by `SEARCH_DEBUG_ENABLED`)
- `window.dispatchEvent(new Event('paradiso-language-applied'))` — listened by agent/med/reminder IIFEs

### 2.6 Central event delegation

One global listener: `document.addEventListener('click', e => { … })`.
It branches on `e.target.closest('[data-action]')?.dataset.action`. **All 47 dispatched values** must be present somewhere in the (static or JS-generated) HTML:

```
clear-search · close-ai-modal · close-jobcode-modal · close-jurisdiction-modal ·
close-doc-modal · close-faq-modal · close-hikorea-guide · open-ai-modal ·
open-hikorea-guide · open-doc-modal · open-faq-modal · set-guide-lang ·
start-hikorea-guide · hikorea-prev · hikorea-next · hikorea-pick-task ·
hikorea-clear-task · hikorea-complete · select-procedure · select-docs-tab ·
search-hint · quick-filter · set-search-mode · toggle-accordions ·
toggle-search · open-jobcode-modal · open-jurisdiction-modal ·
search-jobcode-ai · copy-jobcode · copy-visa-result · verify-faq ·
reset-to-landing · toggle-city · apply-city · toggle-language-menu ·
apply-language · toggle-theme · scroll-to-brand · toggle-su
```

(plus a separate class-based handler for `.ai-action-btn` that reads `dataset.type`)

A subset is **statically authored** in body markup (must be preserved in new HTML):
`toggle-city, toggle-language-menu, toggle-theme, reset-to-landing, toggle-search, open-hikorea-guide, open-jobcode-modal, open-jurisdiction-modal, clear-search, set-search-mode, toggle-accordions, scroll-to-brand, search-hint, close-ai-modal, close-jobcode-modal, close-jurisdiction-modal, close-doc-modal, close-faq-modal, close-hikorea-guide, search-jobcode-ai`.

The remainder (`open-ai-modal`, `open-doc-modal`, `open-faq-modal`, `select-procedure`, `select-docs-tab`, `hikorea-*`, `apply-city`, `apply-language`, `quick-filter`, `copy-jobcode`, `copy-visa-result`, `verify-faq`, `toggle-su`) is emitted by JS innerHTML — those keep working automatically.

### 2.7 Custom events

| Event | Dispatcher | Listeners |
|-------|------------|-----------|
| `paradiso-language-applied` | `applyLanguage` | Agent finder IIFE, medical finder IIFE, reminder IIFE |

### 2.8 IDs the JS reads (canonical preservation list)

> **This is the contract.** Every id in this list must exist in the new static HTML at the same semantic position. Tag may change; id may not.

**Top controls / chrome:**
`starCanvas, cityWrap, cityBtn, cityBtnFlag, cityBtnLabel, cityBtnTime, cityMenu, citySearch, cityList, languageWrap, languageBtn, languageBtnCode, languageBtnNative, languageMenu, mainThemeBtn, topCtrls, reminderBanner, reminderBannerText, reminderBannerClose`

**Hero / search:**
`hero, pHeroTitle, heroActions, searchToggleBtn, qaMain, hikoreaLandingCta, hikoreaCTATitle, hikoreaCTASub, hikoreaCTABtn, visaManualSection, visaManualDynamic, searchForm, q, xb, auto-list, rc, rh, ma, mo, landingHintsTitle, landingHints, scrollCue`

**Main / sections:**
`mainContent, brandHero, brandHeroTitle, stat-work, stat-study, stat-residence, stat-visit, brandFeature, brandFeatureTitle, pPathwayTitle, pHowTitle, pSourceTitle, pToolsTitle, agentFinder, agentFinderTitle, agentFinderSourceNote, agentFinderDisclaimer, agentFinderDisclaimerText, agentFinderRegion, agentFinderKeyword, agentFinderPrompt, agentFinderLoading, agentFinderCount, agentFinderList, agentFinderEmpty, agentFinderError, agentFinderErrorText, agentFinderRetry, agentFinderMore, agentFinderShowMore, jejuRegionFilter, medFinder, medFinderTitle, medFinderSourceNote, medFinderDisclaimer, medFinderDisclaimerText, medFinderChips, medFinderKeyword, medFinderClear, medFinderPrompt, medFinderLoading, medFinderCount, medFinderList, medFinderEmpty, medFinderError, medFinderErrorText, medFinderRetry, medFinderMore, medFinderShowMore, reminderSection, pReminderTitle, reminderForm, reminderType, reminderDate, reminderMemo, reminderFormError, reminderSaveStatus, reminderEmpty, reminderItems, aboutMe, aboutMeTitle, anagram, anagram-top, anagram-svg, anagram-bot, pFooterCtaTitle, qf, rlist`

**Modals (overlay + title + body + dynamic spots):**
`aiModalOverlay, aiModalTitle, aiModalTitleText, aiInput, btnJurisdiction, btnJobCode, aiResult, jobCodeModalOverlay, jobCodeModalTitle, jcSearchInput, jcCountBadge, jcJobResults, jcIndResults, jcAiSpinner, jurisdictionModalOverlay, jurisdictionModalTitle, jurSido, jurSigungu, jurResultCard, jurMsg, jurOfficeName, jurOfficeAddr, jurNaver, jurKakao, docModalOverlay, docModalTitle, docModalDesc, docModalChecklist, faqModalOverlay, faqModalTitle, faqModalBody, hikoreaGuideOverlay, hikoreaGuideTitle, hikoreaGuideBody`

**SVG inline refs (used by url() in CSS or JS):**
`pdsclip, pdssky, pdssea, ag-arr-active, ag-arr-dim`

**Conditional (created at runtime, included for completeness):**
`searchDebugPanel, inKoreaVisaList, inKoreaVisaSearch, hkStartBtn, hkExpMsg`

### 2.9 Classes the JS toggles / queries (must be styled by new CSS)

**Body / global state classes:**
`landing, searched, searching, launched`

**Hero spotlight / canvas:**
`spotlight-ready`

**Scroll reveal:**
`revealed, v` (data attrs `data-reveal`, `data-stagger`, `data-stagger-delay`)

**Toast:**
`toast, toast-warning, toast-error, toast-success, show`

**Generic interactive:**
`active, open, on, copied`

**Result card / manual:**
`manual-result, vc, vc-h, vc-c, su, h (highlight mark), sep-badges, sep-badge, sep-badge.structured, .unverified, .visa-manual, .stay-manual, manual-layout, manual-head-main, manual-title-row, manual-title-stack, manual-name-ko, manual-name-en, manual-badges, manual-badge, manual-badge.domain-visa, .domain-stay, .review-ok, .review-needed, manual-section-title, manual-source-box, manual-source-title, manual-warning-box, manual-subcode-grid, manual-subcode-card, manual-subcode-top, manual-subcode-name, manual-subcode-code, manual-subcode-desc, manual-subcode-more, manual-actions, manual-detail-block, manual-detail-body, manual-preview, subcode-warning`

**Procedure & document tabs:**
`procedure-tabs, procedure-tab, procedure-panel, procedure-list, procedure-fee-box, procedure-fee-title, procedure-fee-list, procedure-fee-amount, procedure-fee-note, procedure-summary, procedure-doc-count, docs-tabs, docs-tab, docs-tab-icon, docs-tab-label, docs-panel, docs-section, doc-checklist, doc-group, doc-group-title, doc-group-grid, doc-group-empty, doc-chk-item, doc-req-box, docs-list-row, docs-list-name, docs-list-note, docs-list-missing, docs-missing-notice`

**Next action panel:**
`next-action-panel, next-action-grid, next-action-title, next-action-kicker, next-action-btn, next-action-btn.primary, hikorea-guide-btn`

**HiKorea modal internals:**
`hikorea-lang-btn, hikorea-lang-row, hikorea-progress, hikorea-step-box, hikorea-task-picker, hikorea-task-btn, hikorea-task-change, hikorea-check-grid, hikorea-footer-actions, hikorea-strip, hikorea-task-buttons, hikorea-task-picker-hint, step0a-block, step0a-section, guide-screenshot`

**Job code modal:**
`jc-item, jc-code, jc-code.lv1, .lv2, .lv3, .lv4, .lv5, jc-level-tag, jc-desc, jc-copy-btn, jc-empty, jc-loading, jc-results-split`

**AI modal:**
`ai-btn, ai-cta, ai-grounding-panel, ai-action-btn, ai-textarea, ai-result, gp-row, gp-title`

**Source evidence:**
`source-evidence-panel, manual-source-box, manual-source-title`

**Autocomplete:**
`auto-item`

**Agent / medical finder (rendered cards):**
`p-agent-finder__card, p-agent-finder__region, p-agent-finder__actions, p-med-finder__card, p-med-finder__region, p-med-finder__actions, p-med-finder__card-source`

**Reminder cards:**
`p-reminder-item, p-reminder-item__type, p-reminder-item__head, p-reminder-item__dday`

**Language menu:**
`language-option, language-option-code, language-option-name, language-option-local, language-option-check`

**FAQ:**
`faq-item, faq-q, faq-a`

**Other small UI:**
`fab-spark, more-open, more-close, tgl, en-label, text-desc, cb, qb`

### 2.10 data-* attributes consumed

`data-action` (47 values, §2.6), `data-type` (analyze / doc_guide / jurisdiction / job_code), `data-visa-code`, `data-vcode`, `data-code`, `data-query`, `data-mode` (and/or), `data-fold` (true/false), `data-procedure`, `data-docs-tab`, `data-docs-panel`, `data-procedure-panel`, `data-subidx`, `data-city` (JSON-encoded), `data-task`, `data-q`, `data-step`, `data-lang`, `data-region`, `data-med-region`, `data-reveal` (fade-up/left/right), `data-stagger`, `data-stagger-delay`, `data-reveal-delay`, `data-count`, `data-theme` (on `<body>`), `data-scene`, `data-hour` (on `<body>`), `data-i`, `data-tgt` (anagram letters), `data-idx`, `data-meta`, `data-regions`, `data-agencies`, `data-institutions`, `data-agent-copy`, `data-med-copy`, `data-urgency`

---

## 3. Phase 1.2 — HTML static-structure inventory

Body (lines 7,323–8,251) is organized as follows:

```
<body class="landing" data-theme="light">
  <canvas id="starCanvas">                                  L7324
  <div id="reminderBanner" class="p-reminder-banner" hidden> L7327-7334
  <header id="topCtrls" class="top-ctrls">                  L7337-7360
    └── city / language / theme controls
  <header id="hero" class="hero-container">                 L7362-7527
    ├── logo area + brand wordmark + SVG horizon
    ├── hero copy (eyebrow, #pHeroTitle, subtitle)
    ├── entry rail (.p-entry-card buttons)
    ├── #heroActions (search toggle + #qaMain quick actions)
    ├── #hikoreaLandingCta banner
    ├── #visaManualSection + #visaManualDynamic
    ├── #searchForm (hidden by default, #q + #xb + #auto-list)
    ├── search meta (#rc, #rh, #ma, #mo)
    ├── #landingHintsTitle + #landingHints
    └── #scrollCue
  <main id="mainContent" class="results-area">              L7529-8069
    ├── #brandHero (StatBridge equivalent)
    ├── #brandFeature (FeatureTrust equivalent)
    ├── .p-pathway-section (8 quick-search cards, data-action="search-hint")
    ├── .p-how-section
    ├── .p-source-section
    ├── .p-tools-section (incl. open-jobcode-modal / open-jurisdiction-modal)
    ├── #agentFinder
    ├── #medFinder
    ├── #reminderSection
    ├── #aboutMe (AnagramBrandStory + RoadmapSection inside)
    └── .p-footer-cta
  <div id="qf">  <div id="rlist">                           L8067-8069
  <footer class="ft">                                       L8247-8249
  <a class="ai-fab" href="ai.html">                         L8251
  <!-- 6 modal overlays -->                                 L8071-8245
    ├── #aiModalOverlay (#aiModalTitle, #aiInput, action buttons, #aiResult)
    ├── #jobCodeModalOverlay (#jcSearchInput, split #jcJobResults / #jcIndResults)
    ├── #jurisdictionModalOverlay (#jurSido / #jurSigungu / #jurResultCard)
    ├── #docModalOverlay (#docModalTitle, #docModalDesc, #docModalChecklist)
    ├── #faqModalOverlay (#faqModalTitle, #faqModalBody)
    └── #hikoreaGuideOverlay (#hikoreaGuideTitle, #hikoreaGuideBody)
  <script>(spotlight IIFE + main app, 8253-12885)</script>
</body>
```

**Two inline `onclick` handlers exist** (must be preserved or migrated to delegated handlers very carefully):

| Line | Element | Handler |
|------|---------|---------|
| ~7472 | `<div class="visa-track-card">` (pre-entry) | `onclick="startPreEntryTrack()"` |
| ~7477 | `<div class="visa-track-card">` (in-Korea) | `onclick="startInKoreaTrack()"` |

Both functions exist in the preserved JS. Recommendation: **keep `onclick=`** in the new HTML rather than refactoring — the brief's "preserve byte-for-byte" applies to JS, and keeping the inline handlers is the lowest-risk option.

**Hidden-by-default elements** (need a CSS `[hidden]` rule + JS toggles the attribute):
`reminderBanner, searchForm (display:none inline), aiModalOverlay, jobCodeModalOverlay, jurisdictionModalOverlay, docModalOverlay, faqModalOverlay, hikoreaGuideOverlay, docModalDesc (inline display:none), btnJobCode (inline display:none), agentFinderLoading/Empty/Error/More, medFinderLoading/Empty/Error/More/Clear, reminderFormError, reminderSaveStatus`.

Full detail in §2.8/§2.9.

---

## 4. Phase 1.3 — CSS structural audit

### 4.1 The 13 `:root` blocks (lines + dominant content)

| # | Line | Dominant content | Status |
|---|------|------------------|--------|
| 1 | 33 | `--p-*` palette (ink, paper, green/coral families) + 8-pt spacing + radius + shadow + motion | **Partly retire** — early design language, replaced by emerald system |
| 2 | 83 | Font families, `--color-primary/accent/surface/text`, legacy `--bg0..3 / --t1..3 / --ac` shorthands, `--sp-1..8`, `--btn-r-*`, `--btn-h-*` | **Keep semantic naming**, retire legacy shorthand |
| 3 | 329 | `--hikorea-strip-bg/bd`, `--hikorea-warn-bg/bd` (`color-mix`) | **Keep as scoped modal tokens** |
| 4 | 1131 | `--result-page-bg`, `--result-surface*`, `--color-primary-green*`, `--shadow-cta*`, `--shadow-lift` | **Canonical for result page** — fold into main `:root` |
| 5 | 2093 | `--ease-spring`, `--ease-out-soft`, `--ease-in-out-smooth`, `--shadow-float/lift/press`, `--highlight-top`, `--ff-serif` | **Canonical motion + multi-layer shadow** |
| 6 | 2280 | Font families (duplicate) | **Delete** |
| 7 | 2316 | Font families (duplicate, adds `--font-logo`) | **Delete (keep `--font-logo`)** |
| 8 | 2348 | `--ff-serif` only | **Delete** |
| 9 | 2358 | `--jeju-hero-coast`, `--jeju-brand-field`, `--jeju-start-stone`, `--jeju-footer-night` (asset URLs) | **Keep** as asset map |
| 10 | 4976 | `--fig-glass-*`, `--fig-card-shadow`, `--fig-green-glow`, `--fig-coral-glow`, `--fig-ease-out` | **Canonical glass + glow** — rename without `fig-` prefix |
| 11 | 5585 | `--p-emerald`, `--p-emerald-deep`, `--p-emerald-glow*`, `--p-paper-surface*`, `--p-divider-soft/dashed` | **Canonical emerald + paper** |
| 12 | 6096 | `--r2-r-chip/btn/pri/card`, `--r2-h-chip/btn/pri/ghost`, `--r2-sp-1..6`, `--r2-focus-ring` | **Canonical button/chip rhythm** |
| 13 | 6952 | `--pf-emerald*`, `--pf-hero-tint`, `--pf-ivory`, `--pf-paper-glass*`, `--pf-coral*`, `--pf-hairline*`, `--pf-w-display/strong/body/meta` | **Most current Figma Make v21 tokens** — base for canonical palette |

**Conflict spots:**
- `--p-accent` (#1F4F3D legacy green) vs `--color-primary` (#2f5e67 teal) vs `--p-emerald` (#0EA37B) — **canonical: emerald `#0EA37B`**
- `--shadow-lift` defined twice with different values (block #4 vs #5) — canonical: block #5 multi-layer
- `--ff` redeclared in blocks #2, #6, #7 — canonical: Pretendard
- `--fs-md`, `--fs-lg`, etc. exist only in block #1 (`--p-fs-*`) — keep, alias both

### 4.2 `!important` distribution

| Region | Count | Verdict |
|--------|-------|---------|
| Lines 14–6,935 (pre-Figma layer) | ~336 | Accumulated cascade-fighting debt; ~60–70% removable in rewrite |
| Lines 6,936–7,318 (FIGMA PIXEL-PERFECT LAYER) | ~32 | Intentional final-cascade overrides; new CSS will not need them once the layer is the *first* expression of the design |
| Total | 368 | Target after rewrite: **<30** |

### 4.3 Color palette state

196 unique 6-char hex matches (case-insensitive dedupe → 156). Distribution:
- **Brand emerald family**: ~22 (canonical `#0EA37B`, deep `#085E48`, hover `#0c8c69`, plus 10 one-off greens to delete)
- **Neutrals / paper**: ~48 (rationalize to 8-step warm-paper + ink scale)
- **Coral / warning**: ~12 (canonical `#FF6B5B`, deep `#E0513E`, light `#FF8B7A`)
- **Off-brand Tailwind defaults**: `#6d28d9 / #7c3aed / #ca8a04 / #d97706 / #f59e0b / #03c75a / #fee500 / #4285f4` — **delete**, replace with brand tokens
- **One-off teals from old "color-primary" era**: `#0a3d2f / #2a4f57 / #2f5e67 / #6b9a8e / #163e36 / #205a4e` — **delete**

Target canonical palette: **~40 tokens** (down from 156 unique).

### 4.4 Selector duplication

Top offenders (>3 occurrences per selector):

| Selector | Count |
|----------|-------|
| `body:not(.searched) .sbar` | 7 |
| `body:not(.searched) .hero-container::before` | 7 |
| `body:not(.searched) .brand-wordmark-img` | 7 |
| `body:not(.searched) .lh` (+ `:hover` variant) | 11 |
| `body.searched .smeta` | 5 |
| `.p-reminder-card` | 5 |
| `.vc.manual-result` | **119** |
| `.hero-container` (all variants) | 49 |
| `body:not(.searched) *` (all variants) | 49 |
| `body.searched *` (all variants) | ~30 |

Total selectors with >3 occurrences: ~40+. The new CSS organizes by component (single block per selector) + a clearly marked state section for `.searched` vs `.landing`.

### 4.5 Dark mode

Implemented as `[data-theme="dark"]` attribute on `<body>` (set by `toggleTheme()`). ~49 rules use this prefix. **Not** `@media (prefers-color-scheme: dark)` — user toggle wins.

### 4.6 Media queries

16 distinct conditions across 3 informal breakpoint families (mobile/tablet/desktop) + reduced-motion + min-width inversions. Recommendation: collapse to canonical 4:
- `(max-width: 480px)` — mobile
- `(max-width: 768px)` — tablet
- `(max-width: 1024px)` — small desktop
- `(prefers-reduced-motion: reduce)` — accessibility

---

## 5. Phase 2.1 — Canonical `:root {}` token block

Single block, organized by category. Names chosen to be semantic, brief, and stable. Where multiple legacy names existed, the canonical is listed first; an aliases sub-block (also inside `:root`) keeps every legacy name pointing at the new value so the existing JS-rendered HTML keeps rendering correctly without CSS changes during transition.

```css
:root {
  /* ─── Color: brand ─────────────────────────────────────────── */
  --emerald:           #0EA37B;
  --emerald-deep:      #085E48;
  --emerald-hover:     #0c8c69;
  --emerald-mint:      #7DD8B8;
  --emerald-tint-12:   rgba(14, 163, 123, 0.12);
  --emerald-tint-6:    rgba(14, 163, 123, 0.06);
  --emerald-tint-3:    rgba(14, 163, 123, 0.03);

  --coral:             #C95440;
  --coral-bright:      #FF6B5B;
  --coral-light:       #FF8B7A;
  --coral-deep:        #E0513E;
  --coral-soft:        #F2C9BD;

  --amber-warn:        #E68A3A;

  /* ─── Color: neutral (warm paper + ink) ────────────────────── */
  --paper:             #F4EEE0;
  --paper-2:           #EAE2D0;
  --paper-3:           #DDD4BD;
  --paper-surface:     #FBF5E6;   /* result page surface */
  --paper-surface-2:   #F6EFDB;
  --ivory:             #FCFAF5;
  --ink:               #0E1F1A;
  --ink-2:             #233530;
  --ink-3:             #4A5852;
  --ink-muted:         #7A8580;
  --line:              #C9BFA5;
  --line-2:            #DCD3BC;
  --hairline:          rgba(14, 31, 26, 0.08);
  --hairline-strong:   rgba(14, 31, 26, 0.14);
  --white:             #FFFFFF;
  --black:             #0E1F1A;

  /* ─── Color: surfaces & overlays ───────────────────────────── */
  --color-bg:          var(--paper);
  --color-surface:     var(--white);
  --color-surface-2:   var(--paper-surface-2);
  --color-text:        var(--ink);
  --color-text-muted:  var(--ink-muted);
  --color-border:      var(--line);

  --glass-bg:          rgba(255, 255, 255, 0.13);
  --glass-bg-hi:       rgba(255, 255, 255, 0.18);
  --glass-border:      rgba(255, 255, 255, 0.20);
  --glass-border-hi:   rgba(255, 255, 255, 0.36);
  --glass-blur:        20px;

  /* ─── Color: semantic ──────────────────────────────────────── */
  --color-primary:     var(--emerald);
  --color-accent:      var(--coral-bright);
  --color-success:     var(--emerald);
  --color-warning:     var(--amber-warn);
  --color-error:       var(--coral-deep);

  /* ─── Typography ───────────────────────────────────────────── */
  --ff: "Pretendard Variable", "Pretendard", -apple-system,
        BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --ff-display: var(--ff);
  --ff-logo:    var(--ff);
  --ff-serif:   "Iowan Old Style", "Apple Garamond", "Baskerville",
                "Times New Roman", Georgia, serif;

  --fs-xs:     0.75rem;     /* 12 */
  --fs-sm:     0.8125rem;   /* 13 */
  --fs-base:   0.9375rem;   /* 15 */
  --fs-md:     1.0625rem;   /* 17 */
  --fs-lg:     1.25rem;     /* 20 */
  --fs-xl:     1.5rem;      /* 24 */
  --fs-2xl:    2rem;        /* 32 */
  --fs-3xl:    2.5rem;      /* 40 */

  --fw-body:    400;
  --fw-meta:    500;
  --fw-strong:  600;
  --fw-heavy:   700;
  --fw-display: 800;

  --lh-tight:   1.15;
  --lh-snug:    1.35;
  --lh-base:    1.55;
  --lh-relax:   1.75;

  --tracking-tight: -0.01em;
  --tracking-base:   0;
  --tracking-wide:   0.04em;

  /* ─── Spacing (8-pt grid) ──────────────────────────────────── */
  --sp-1:  0.25rem;    /*  4 */
  --sp-2:  0.5rem;     /*  8 */
  --sp-3:  0.75rem;    /* 12 */
  --sp-4:  1rem;       /* 16 */
  --sp-5:  1.5rem;     /* 24 */
  --sp-6:  2rem;       /* 32 */
  --sp-7:  3rem;       /* 48 */
  --sp-8:  4rem;       /* 64 */
  --sp-9:  6rem;       /* 96 */
  --sp-10: 8rem;       /* 128 */

  /* ─── Radius ───────────────────────────────────────────────── */
  --r-xs:   4px;
  --r-sm:   8px;
  --r-md:   12px;
  --r-lg:   16px;
  --r-xl:   20px;
  --r-2xl:  24px;
  --r-pill: 999px;

  /* ─── Elevation / shadow ──────────────────────────────────── */
  --sh-1:        0 1px 0 rgba(14,31,26,0.04), 0 1px 2px rgba(14,31,26,0.05);
  --sh-2:        0 4px 12px rgba(14,31,26,0.06), 0 1px 2px rgba(14,31,26,0.04);
  --sh-3:        0 12px 32px rgba(14,31,26,0.10), 0 2px 6px rgba(14,31,26,0.05);
  --sh-float:    0 2px 4px rgba(11,42,36,0.04), 0 8px 20px rgba(11,42,36,0.06),
                 0 20px 40px rgba(11,42,36,0.06);
  --sh-cta:      0 4px 18px rgba(14,163,123,0.32), 0 2px 4px rgba(14,163,123,0.18);
  --sh-cta-hi:   0 8px 24px rgba(14,163,123,0.42), 0 4px 8px rgba(14,163,123,0.22);
  --sh-coral:    0 4px 14px rgba(255,107,91,0.28), 0 2px 4px rgba(255,107,91,0.16);
  --sh-glass:    0 16px 48px -8px rgba(0,0,0,0.28),
                 inset 0 1px 0 rgba(255,255,255,0.10);

  --highlight-top: inset 0 1px 0 rgba(255,255,255,0.55);

  /* ─── Motion ───────────────────────────────────────────────── */
  --ease:            cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-soft:   cubic-bezier(0.16, 1, 0.30, 1);
  --ease-spring:     cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out:     cubic-bezier(0.45, 0, 0.55, 1);

  --dur-1: 180ms;
  --dur-2: 320ms;
  --dur-3: 500ms;

  /* ─── Z-index scale ────────────────────────────────────────── */
  --z-base:     1;
  --z-elevated: 10;
  --z-sticky:   100;
  --z-overlay:  500;
  --z-modal:    1000;
  --z-toast:    2000;
  --z-debug:    5000;

  /* ─── Layout ──────────────────────────────────────────────── */
  --container-narrow:  720px;
  --container:         960px;
  --container-wide:    1180px;
  --gutter:            clamp(1rem, 4vw, 2rem);

  --bp-mobile:  480px;
  --bp-tablet:  768px;
  --bp-desk:    1024px;

  /* ─── Focus ───────────────────────────────────────────────── */
  --focus-ring: 0 0 0 3px rgba(14,163,123,0.35);

  /* ─── Asset URLs (Jeju hero, etc.) ────────────────────────── */
  --jeju-hero-coast:   url('assets/jeju/coast.webp');
  --jeju-brand-field:  url('assets/jeju/field.webp');
  --jeju-start-stone:  url('assets/jeju/stone.webp');
  --jeju-footer-night: url('assets/jeju/night.webp');

  /* ─── Legacy aliases (until JS-rendered HTML migrates) ────── */
  --p-emerald:        var(--emerald);
  --p-emerald-deep:   var(--emerald-deep);
  --p-emerald-glow:   var(--sh-cta);
  --p-paper-surface:  var(--paper-surface);
  --p-paper-surface-2:var(--paper-surface-2);
  --p-divider-soft:   var(--hairline);
  --p-divider-dashed: 1px dashed var(--line-2);
  --p-ink:            var(--ink);
  --p-line:           var(--line);
  --color-primary-green:       var(--emerald);
  --color-primary-green-hover: var(--emerald-hover);
  --color-primary-green-deep:  var(--emerald-deep);
  --r2-r-chip:   var(--r-pill);
  --r2-r-btn:    var(--r-md);
  --r2-r-pri:    var(--r-md);
  --r2-r-card:   var(--r-lg);
  --r2-h-chip:   32px;
  --r2-h-btn:    44px;
  --r2-h-pri:    52px;
  --r2-h-ghost:  40px;
  --r2-sp-1: var(--sp-1); --r2-sp-2: var(--sp-2);
  --r2-sp-3: var(--sp-3); --r2-sp-4: var(--sp-4);
  --r2-sp-5: var(--sp-5); --r2-sp-6: var(--sp-6);
  --r2-focus-ring: var(--focus-ring);
  --fig-glass-bg:       var(--glass-bg);
  --fig-glass-bg-hi:    var(--glass-bg-hi);
  --fig-glass-border:   var(--glass-border);
  --fig-glass-blur:     var(--glass-blur);
  --fig-card-shadow:    var(--sh-2);
  --fig-card-shadow-hi: var(--sh-3);
  --fig-green-glow:     var(--sh-cta);
  --fig-coral-glow:     var(--sh-coral);
  --fig-ease-out:       var(--ease-out-soft);
  --pf-emerald:         var(--emerald);
  --pf-emerald-deep:    var(--emerald-deep);
  --pf-emerald-mint:    var(--emerald-mint);
  --pf-emerald-tint-1:  var(--emerald-tint-12);
  --pf-emerald-tint-2:  var(--emerald-tint-6);
  --pf-ivory:           var(--ivory);
  --pf-paper-glass:     var(--paper-surface);
  --pf-coral:           var(--coral-bright);
  --pf-hairline:        var(--hairline);
  --pf-hairline-2:      var(--hairline-strong);
  --pf-w-display:       var(--fw-display);
  --pf-w-strong:        var(--fw-strong);
  --pf-w-body:          var(--fw-body);
  --pf-w-meta:          var(--fw-meta);
}

[data-theme="dark"] {
  --color-bg:         #0d1f1b;
  --color-surface:    #132f2a;
  --color-surface-2:  #1a3a32;
  --color-text:       #f5f2ea;
  --color-text-muted: #b7c5be;
  --color-border:     rgba(255,255,255,0.10);
  --paper:            #0d1f1b;
  --paper-surface:    #132f2a;
  --paper-surface-2:  #1a3a32;
  --ivory:            #1a3a32;
  --line:             rgba(255,255,255,0.10);
  --hairline:         rgba(255,255,255,0.08);
  --hairline-strong:  rgba(255,255,255,0.18);
  --sh-1:    0 1px 0 rgba(0,0,0,0.30), 0 1px 2px rgba(0,0,0,0.40);
  --sh-2:    0 4px 12px rgba(0,0,0,0.40), 0 1px 2px rgba(0,0,0,0.30);
  --sh-3:    0 12px 32px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.30);
  --sh-float:0 2px 4px rgba(0,0,0,0.32), 0 8px 20px rgba(0,0,0,0.40),
             0 20px 40px rgba(0,0,0,0.45);
  --highlight-top: inset 0 1px 0 rgba(255,255,255,0.07);
}
```

---

## 6. Phase 2.2 — Component CSS specs

Sketches only — final implementation in Phase 4. All values reference tokens from §5.

### 6.1 Buttons

```css
/* Base button */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--sp-2);
  min-height: 44px; padding: 0 var(--sp-5);
  border: 1px solid transparent; border-radius: var(--r-md);
  font: var(--fw-strong) var(--fs-base)/1.2 var(--ff);
  cursor: pointer; transition: background var(--dur-1) var(--ease),
                               box-shadow var(--dur-1) var(--ease),
                               transform var(--dur-1) var(--ease);
  -webkit-tap-highlight-color: transparent;
}
.btn:focus-visible { outline: 0; box-shadow: var(--focus-ring); }
.btn:active        { transform: translateY(1px); }
.btn[disabled]     { opacity: 0.55; cursor: not-allowed; }

/* Primary — emerald CTA (dominant on result page + HiKorea) */
.btn-primary {
  background: var(--emerald); color: #fff; border-color: var(--emerald-deep);
  box-shadow: var(--sh-cta);
  min-height: 52px;
}
.btn-primary:hover { background: var(--emerald-hover); box-shadow: var(--sh-cta-hi); }

/* Secondary — paper surface with ink */
.btn-secondary {
  background: var(--color-surface); color: var(--ink);
  border-color: var(--hairline-strong);
}
.btn-secondary:hover { background: var(--paper-surface); }

/* Ghost — no border, text-only */
.btn-ghost {
  background: transparent; color: var(--ink-2);
  min-height: 40px; padding: 0 var(--sp-4);
}
.btn-ghost:hover { background: var(--emerald-tint-6); color: var(--emerald-deep); }

/* Danger / coral */
.btn-danger {
  background: var(--coral-bright); color: #fff;
  border-color: var(--coral-deep); box-shadow: var(--sh-coral);
}

/* Chip / pill */
.btn-chip {
  min-height: 32px; padding: 0 var(--sp-4);
  border-radius: var(--r-pill); font-size: var(--fs-sm);
  background: var(--color-surface); border-color: var(--hairline);
}
.btn-chip[aria-pressed="true"],
.btn-chip.active {
  background: var(--emerald); color: #fff; border-color: var(--emerald-deep);
}
```

### 6.2 Cards

```css
.card {
  background: var(--color-surface); color: var(--ink);
  border: 1px solid var(--hairline); border-radius: var(--r-lg);
  padding: var(--sp-5); box-shadow: var(--sh-2);
}
.card-elevated   { box-shadow: var(--sh-3); }
.card-glass      { background: var(--glass-bg); backdrop-filter: blur(var(--glass-blur));
                   border-color: var(--glass-border); box-shadow: var(--sh-glass); }
.card-paper      { background: var(--paper-surface); border-color: var(--line-2); }

/* Result card (single surface, no nested boxes) */
.manual-result {
  background: var(--paper-surface); color: var(--ink);
  border: 1px solid var(--line-2); border-radius: var(--r-xl);
  padding: var(--sp-6); box-shadow: var(--sh-2);
}
```

### 6.3 Inputs

```css
.input, .select, .textarea {
  width: 100%; min-height: 44px;
  padding: 0 var(--sp-4);
  background: var(--color-surface); color: var(--ink);
  border: 1px solid var(--hairline-strong); border-radius: var(--r-md);
  font: var(--fw-body) var(--fs-base)/1.4 var(--ff);
  transition: border-color var(--dur-1) var(--ease),
              box-shadow var(--dur-1) var(--ease);
}
.input:focus, .select:focus, .textarea:focus {
  outline: 0; border-color: var(--emerald);
  box-shadow: 0 0 0 3px var(--emerald-tint-12);
}
.input::placeholder { color: var(--ink-muted); }

/* Search bar — pill, glass on landing */
.sbar {
  display: flex; align-items: center; gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-5);
  background: var(--color-surface); border: 1px solid var(--hairline-strong);
  border-radius: var(--r-pill); box-shadow: var(--sh-2);
}
body:not(.searched) .sbar {
  background: var(--glass-bg-hi); border-color: var(--glass-border-hi);
  backdrop-filter: blur(var(--glass-blur));
  box-shadow: var(--sh-glass);
}
.sbar:focus-within {
  border-color: var(--emerald); box-shadow: var(--sh-cta);
}
```

### 6.4 Tabs

```css
.procedure-tabs, .docs-tabs {
  display: flex; gap: var(--sp-2);
  padding: var(--sp-1); background: var(--paper-surface-2);
  border-radius: var(--r-md);
}
.procedure-tab, .docs-tab {
  flex: 1; min-height: 40px; padding: 0 var(--sp-4);
  background: transparent; border: 0; color: var(--ink-2);
  border-radius: var(--r-sm); font: var(--fw-strong) var(--fs-sm) var(--ff);
  cursor: pointer;
  transition: background var(--dur-1) var(--ease),
              color var(--dur-1) var(--ease);
}
.procedure-tab.active, .docs-tab.active {
  background: var(--color-surface); color: var(--emerald-deep);
  box-shadow: var(--sh-1);
}
.procedure-tab[disabled] { opacity: 0.4; cursor: not-allowed; }
.procedure-panel, .docs-panel { padding-top: var(--sp-4); }
```

### 6.5 Modals

```css
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(14, 31, 26, 0.55); backdrop-filter: blur(8px);
  display: none; align-items: flex-start; justify-content: center;
  padding: var(--sp-5); z-index: var(--z-modal);
  overflow-y: auto;
}
.modal-overlay.open { display: flex; }

.modal-box {
  width: 100%; max-width: 640px;
  background: var(--color-surface); color: var(--ink);
  border: 1px solid var(--hairline); border-radius: var(--r-xl);
  box-shadow: var(--sh-float);
  overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--sp-4) var(--sp-5);
  border-bottom: 1px solid var(--hairline);
}
.modal-title { font: var(--fw-heavy) var(--fs-lg)/1.3 var(--ff); }
.modal-close {
  width: 40px; height: 40px; border-radius: var(--r-sm);
  background: transparent; border: 0; color: var(--ink-3);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 1.4rem; cursor: pointer;
}
.modal-close:hover { background: var(--paper-surface-2); color: var(--ink); }
.modal-body   { padding: var(--sp-5); }
.modal-footer { padding: var(--sp-4) var(--sp-5);
                border-top: 1px solid var(--hairline);
                display: flex; gap: var(--sp-3); justify-content: flex-end; }
```

### 6.6 Badges & chips

```css
.badge {
  display: inline-flex; align-items: center; gap: var(--sp-1);
  height: 24px; padding: 0 var(--sp-3);
  border-radius: var(--r-pill);
  font: var(--fw-strong) var(--fs-xs)/1 var(--ff);
  background: var(--emerald-tint-12); color: var(--emerald-deep);
}
.badge-coral   { background: rgba(255,107,91,0.12); color: var(--coral-deep); }
.badge-warning { background: rgba(230,138,58,0.14); color: #7a4a13; }
.badge-neutral { background: var(--paper-surface-2); color: var(--ink-3); }

.sep-badge.structured  { background: var(--emerald-tint-12); color: var(--emerald-deep); }
.sep-badge.unverified  { background: rgba(230,138,58,0.14); color: #7a4a13; }
.sep-badge.visa-manual { background: var(--paper-surface-2); color: var(--ink-2); }
.sep-badge.stay-manual { background: var(--paper-surface-2); color: var(--ink-2); }
```

### 6.7 Navigation bar (`#topCtrls`)

```css
.top-ctrls {
  position: fixed; top: var(--sp-4); right: var(--sp-4);
  display: flex; gap: var(--sp-2); z-index: var(--z-sticky);
  align-items: center;
}
.city-btn, .theme-btn, .language-btn {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  height: 40px; padding: 0 var(--sp-4);
  background: var(--glass-bg-hi); color: var(--ink);
  border: 1px solid var(--glass-border-hi); border-radius: var(--r-pill);
  font: var(--fw-strong) var(--fs-sm) var(--ff);
  cursor: pointer; backdrop-filter: blur(var(--glass-blur));
  transition: background var(--dur-1) var(--ease);
}
.city-btn:hover, .theme-btn:hover, .language-btn:hover { background: var(--white); }
```

### 6.8 Highlight mark (`<mark class="h">`)

```css
mark.h {
  background: var(--emerald-tint-12); color: var(--emerald-deep);
  padding: 0 0.15em; border-radius: 0.2em;
  font-weight: var(--fw-strong);
}
```

---

## 7. Phase 2.3 — Layout specs

### 7.1 Hero (`#hero` / HeroGateway)

- Atmospheric: SVG horizon backdrop + emerald-tinted spotlight follows pointer (`--mx` / `--my` set by spotlight IIFE — must keep working).
- Vertical rhythm: top padding `clamp(4rem, 8vh, 6rem)`; bottom padding `var(--sp-7)`.
- Centered column, `max-width: var(--container)`.
- Wordmark: `clamp(72px, 9vw, 128px)` height (matches current pixel-perfect layer).
- Eyebrow + `#pHeroTitle` + subtitle stack with `gap: var(--sp-3)`.
- Entry rail (2 buttons) below copy, `display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4)` on tablet+; stacks on mobile.

### 7.2 Section vertical rhythm

- Section vertical padding: `clamp(var(--sp-7), 8vw, var(--sp-9))`.
- Inner container max-widths:
  - Narrow text (StatBridge headline, AnagramBrandStory): `--container-narrow` (720px)
  - Default sections (FeatureTrust, RoadmapSection, Pathway, Tools): `--container` (960px)
  - Wide sections (Result list with side context): `--container-wide` (1180px)
- Section gap inside containers: `var(--sp-6)` (32px) between major children.

### 7.3 Container max-widths & breakpoints

| Token | Value | Used by |
|-------|-------|---------|
| `--container-narrow` | 720px | Hero copy, brand story |
| `--container` | 960px | Most sections |
| `--container-wide` | 1180px | Footer CTA, result list |
| `--gutter` | `clamp(1rem, 4vw, 2rem)` | Side padding |

### 7.4 Mobile-first strategy

- Default styles target **390px width** (iPhone 13 mini baseline).
- Single column at <480px; two-column grids start at `(min-width: 768px)`; three+ columns at `(min-width: 1024px)`.
- Touch target minimum 44px (×4px = 11rem at 1rem=16px baseline → use `--sp-7` height for primary CTAs, `--sp-5×1.5` for chips).
- Body base font 16px.
- Reduced-motion respected on hero spotlight + canvas + reveal animations.

---

## 8. Phase 2.4 — New HTML structure outline (sketch)

```
<head>
  meta + Pretendard CDN + favicon + single <style>
</head>
<body class="landing" data-theme="light">
  <canvas id="starCanvas">
  <div id="reminderBanner" hidden>...</div>

  <header id="topCtrls">
    city / language / theme controls (all current ids/data-action preserved)
  </header>

  <header id="hero" class="hero">
    logo + brand wordmark + hero copy
    .p-entry-rail (2 cards — `data-action="toggle-search"` etc.)
    #heroActions (#searchToggleBtn + #qaMain + #hikoreaLandingCta inside)
    #visaManualSection + #visaManualDynamic (hidden, populated by visa-track flow)
    #searchForm (hidden by default — #q + #xb + #auto-list + meta)
    #landingHints + #landingHintsTitle
    #scrollCue
  </header>

  <main id="mainContent">
    <section id="brandHero">       (StatBridge)
    <section id="brandFeature">    (FeatureTrust)
    <section class="p-pathway-section">  (KeywordsHints — 8 cards)
    <section class="p-how-section">      (how it works — 4 steps)
    <section class="p-source-section">   (source credibility)
    <section class="p-tools-section">    (tools — opens jobcode/jurisdiction modals)
    <section id="agentFinder">     (agent finder — full controls preserved)
    <section id="medFinder">       (medical institution finder)
    <section id="reminderSection"> (deadline reminder form + list)
    <section id="aboutMe">         (AnagramBrandStory + RoadmapSection inside)
    <section class="p-footer-cta"> (FooterCTA)
  </main>

  <div id="qf"></div>
  <div id="rlist"></div>

  <footer class="ft">Paradiso v38 · ...</footer>
  <a class="ai-fab" href="ai.html">AI로 더 자세히 묻기 ...</a>

  <!-- 6 modal overlays, all ids preserved -->
  <div id="aiModalOverlay" class="modal-overlay">...</div>
  <div id="jobCodeModalOverlay" class="modal-overlay">...</div>
  <div id="jurisdictionModalOverlay" class="modal-overlay">...</div>
  <div id="docModalOverlay" class="modal-overlay">...</div>
  <div id="faqModalOverlay" class="modal-overlay">...</div>
  <div id="hikoreaGuideOverlay" class="modal-overlay">...</div>

  <script> (config) </script>      <!-- 7319-7321 preserved -->
  <script>
    /* lines 8253-12885 preserved verbatim */
  </script>
</body>
```

Every id in §2.8 is present at the same semantic position; every static `data-action` from §2.6 is re-emitted on the same kind of element. Class names from §2.9 are styled by the new CSS even when they only appear in JS-emitted markup.

---

## 9. Phase 2.5 — New CSS organization plan

Single `<style>` block, ~3,500–4,500 lines target (vs current 7,305):

```
/* 1. Canonical :root + dark-mode override                                ~250 */
/* 2. Reset / normalize                                                    ~80 */
/* 3. Base typography (html, body, headings, p, a)                        ~120 */
/* 4. Layout primitives (.container, .stack, .grid, .row, .center, hidden)~120 */
/* 5. Components — order: buttons, inputs, cards, tabs, modals, badges,
      chips, toast, autocomplete, mark.h                                  ~900 */
/* 6. Sections — top ctrls, hero, brand hero, brand feature, pathway,
      how, source, tools, agent finder, med finder, reminder, about,
      footer cta, ai fab, footer                                         ~1100 */
/* 7. Result page (.searched state) — search bar variant, results area,
      manual-result card system (single-surface), procedure tabs,
      doc tabs, subcodes, source evidence, next-action panel             ~700 */
/* 8. State classes — body.searched / .landing / .searching / .launched,
      modal-overlay.open, hero spotlight vars                             ~120 */
/* 9. JS-emitted class styles (agent/med finder cards, job code rows,
      reminder cards, HiKorea step boxes, FAQ items)                      ~400 */
/* 10. Animations + reveal + count-up                                    ~120 */
/* 11. Responsive — @media (max-width: 768px), (max-width: 480px)        ~300 */
/* 12. Accessibility — focus-visible, sr-only, reduced motion             ~80 */
```

Hard rules:
- 0 hardcoded hex outside `:root {}` and `[data-theme="dark"]`.
- 0 `!important` outside a single small "utility override" section (target: <10).
- 0 selectors defined more than once outside an explicit responsive `@media` block.
- All measurements use spacing scale, all colors semantic, all radii from radius scale.

---

## 10. Preservation contract (the absolute checklist)

The new HTML **MUST**:

1. Keep every id in §2.8 at the same semantic location.
2. Keep every static `data-action` from the §2.6 "static" list on a button or link element.
3. Keep the two inline `onclick` handlers (`startPreEntryTrack()`, `startInKoreaTrack()`) on visa-track-card elements.
4. Keep `<body class="landing" data-theme="light">` as initial state.
5. Keep `data-vcode` / `data-type` / `data-subidx` attributes on AI/doc/FAQ trigger buttons that are JS-rendered (no static ones to preserve; the JS templates them).
6. Keep the 2-line config script `window.PARADISO_BACKEND_URL = window.PARADISO_BACKEND_URL || ""` at end of `<head>`.
7. Keep the main `<script>` block at end of `<body>`, byte-for-byte (lines 8253-12885).
8. Keep the favicon link, Pretendard CDN link, `<title>`, `<meta theme-color>`.
9. Keep `<canvas id="starCanvas">` as a direct child of `<body>` (renderer expects it in document flow before `#hero`).
10. Keep `<header id="hero">` so the spotlight IIFE's `getElementById('hero')` resolves.

The new CSS **MUST** provide styles for every class in §2.9 (even classes that only appear in JS innerHTML), since the new design language is the only source of styling for JS-emitted cards/rows/badges.

---

## 11. Open questions / risks before Phase 3

1. **Visa-track inline `onclick`** — the brief says "preserve byte-for-byte" for JS; should I treat these two inline handlers as JS (preserve as-is) or migrate them to delegated `data-action` handlers? Lowest risk = keep them.
2. **Pixel-perfect layer (current lines 6936–7315)** — should it be retired entirely (its rules absorbed into the new component CSS) or kept as a "final cascade" section? Cleaner is to absorb; safer is to keep.
3. **`docs/i18n/` translation files** — the rewrite doesn't touch them, but the JS reads them via `tx()` / GUIDE_I18N. Confirm they're loaded from JS string tables inside the script, not from external files I might miss. (From the inventory, no extra fetch URLs beyond §2.3; confirmed safe.)
4. **`ai.html`** (`<a href="ai.html">` and `.ai-fab`) — this is a separate static page, not touched by the rewrite. Confirmed.
5. **Asset paths** — `assets/brand/paradiso-wordmark-brush-white.png`, `assets/brand/paradiso-favicon-o.png?v=2`, and the Jeju image URLs in `:root` #9. New CSS continues to use them.
6. **Figma source files inaccessible via MCP** — I cannot directly read `theme.css`, `Landing.tsx`, `HeroGateway.tsx`, etc. The MCP `get_design_context` tool requires a `nodeId` which is not exposed by the `figma.com/make/<fileKey>/<name>` URL form. I've worked from the existing "FIGMA PIXEL-PERFECT LAYER" in `index.html` as the source of truth. **If you want the rewrite to be aligned to a *newer* state of the Figma Make file than what's already encoded in the pixel-perfect layer, you'll need to either**:
   - Provide specific nodeIds from the Make file (right-click frame → Copy link → extract `node-id` param), or
   - Paste the relevant `theme.css` / component `.tsx` contents into chat, or
   - Confirm "pixel-perfect layer is the source of truth — rewrite from there".
7. **Mobile 390px verification** — the brief requires manual visual testing. I can't run a browser in this environment; verification will have to happen on your end after the rewrite is pushed (the brief acknowledges this with its QA checklist).
8. **i18n parity** — the JS supports ko/en/zh/vi via `tx()`. The new static HTML markup will be authored in Korean (matching current behaviour) and `applyLanguage()` will translate at runtime via `data-*` keys the JS already sets. No new translation work needed.

---

## 12. Recommended next step

If §5 token block, §6 component sketches, and the §2.8 + §2.9 preservation contract look right to you, **green-light Phase 3** (HTML structure rewrite) as a follow-up PR.

Phase 3 will:
- Cut a fresh `index.html` body (lines 7,323–8,251 replaced).
- Re-create every id from §2.8 in the new structure.
- Re-emit every static `data-action` from §2.6.
- Output the diff for review *before* Phase 4 (CSS) touches anything.

Phase 4 (CSS) and Phase 5 (paste preserved JS + run §2.9 class verification) follow as separate commits on the same branch, with Phase 8 validation (the bash commands from the brief) as the final commit.

Estimated additional work after green-light: ~3–4 hours for Phases 3–8.
