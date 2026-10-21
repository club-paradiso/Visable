# VISABLE Developer Guide: Internationalization (i18n) Architecture & Extension

This document provides technical guidelines for engineers maintaining, updating, and extending VISABLE's internationalization layer (`assets/js/visable-i18n.js`).

---

## 1. System Architecture Overview

VISABLE uses a lightweight, client-side internationalization layer designed for performance, resilience, and offline capability:

- **Core Module**: `assets/js/visable-i18n.js`
- **Supported Locales (15)**:
  - **Tier 1 (Core)**: `ko`, `en`, `zh-CN`, `vi`, `id`
  - **Specialized**: `zh-TW` (powered by `assets/js/zh-traditional.js` OpenCC converter)
  - **Tier 2**: `ja`, `tl`, `ru`, `ar` (RTL)
  - **Tier 3**: `fr`, `es`, `de`, `tr`, `uk`
- **Zero Third-Party Dependencies**: Native ES modules / vanilla JS with no external runtime bloat.

---

## 2. Deterministic Locale Resolution Hierarchy

When a user visits any VISABLE page, `visableI18n.resolveInitialLocale()` evaluates the target locale in strict order of priority:

```
1. URL Query Parameter (?lang=...)  -> Highest priority (allows explicit shared links)
2. Local Storage (localStorage['paradiso:language']) -> Returning user preference
3. Default Authoritative Locale ('ko') -> Safe fallback (Korean administrative baseline)
```

> [!IMPORTANT]
> **Never auto-coerce to `navigator.language` without explicit user intent.**
> Automated test runners, server-side renders, and corporate proxy networks frequently report `en-US` or `C`, which would disrupt Korean baseline validation if coerced automatically.

---

## 3. How to Add a New Localization String

All checklist strings are organized under `CHECKLIST_STRINGS` in `assets/js/visable-i18n.js`.

### Step 1: Add the String Key to Korean (`ko`) and English (`en`)
Korean is the authoritative legal baseline; English is the universal fallback for all other languages.
```javascript
CHECKLIST_STRINGS.ko.myNewKey = "새로운 안내 문구";
CHECKLIST_STRINGS.en.myNewKey = "New guidance message";
```

### Step 2: Add Translations for Tier 1 Languages (`zh-CN`, `vi`, `id`)
```javascript
CHECKLIST_STRINGS['zh-CN'].myNewKey = "新指南信息";
CHECKLIST_STRINGS.vi.myNewKey = "Thông điệp hướng dẫn mới";
CHECKLIST_STRINGS.id.myNewKey = "Pesan panduan baru";
```

### Step 3: Use Placeholders Where Dynamic Data Is Injected
Support parameters using `{paramName}` syntax:
```javascript
CHECKLIST_STRINGS.ko.itemsSelected = "{count}개 항목이 선택되었습니다.";
CHECKLIST_STRINGS.en.itemsSelected = "{count} items selected.";
```
Call with `visableI18n.t('itemsSelected', { count: 3 })`.

---

## 4. Directionality & Right-to-Left (RTL) Support

Arabic (`ar`) triggers RTL mode.

### How Directionality Is Managed
1. `visableI18n.setDocumentDirection(locale)` sets `document.documentElement.dir = 'rtl'` and adds the `.rtl-layout` class to `document.body`.
2. All CSS styles must adhere to **CSS Logical Properties**:
   - Use `margin-inline-start` instead of `margin-left`.
   - Use `margin-inline-end` instead of `margin-right`.
   - Use `padding-inline` instead of `padding-left`/`padding-right`.
3. **Data Isolation**: Any tag that renders code tokens, IDs, phone numbers, or search inputs MUST specify:
   ```css
   [dir="rtl"] .code-pill, [dir="rtl"] code {
     direction: ltr;
     unicode-bidi: isolate;
     display: inline-block;
   }
   ```

---

## 5. Dual-Language Statutory Supremacy Rule

Whenever authoring UI components that display official Korean immigration documents:

> [!WARNING]
> **Never completely replace the Korean official form name.**
> Always preserve the authentic statutory title (e.g. `별지 제34호 통합신청서`) alongside the translation. Korean immigration officers process documents according to statutory names, and foreign applicants must be able to present the exact Korean title at government counters.

---

## 6. Verification & Automated Quality Checks

Before submitting any code changes involving translations:

1. **Run the i18n Quality Validator**:
   ```bash
   node scripts/check_i18n_quality.mjs
   ```
   This validates 15-locale completeness, parameter interpolation, fallback consistency, and procedure name preservation.

2. **Run Playwright Multilingual Suite**:
   ```bash
   CI=1 npx playwright test tests/e2e/multilingual-checklists.spec.mjs
   ```
   Verifies language switching, URL parameters, Arabic RTL layout (with zero horizontal scroll down to 320px), and status search.
