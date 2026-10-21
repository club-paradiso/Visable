/* ============================================================================
 * check_i18n_quality.mjs
 * ----------------------------------------------------------------------------
 * Rigorous quality, completeness, and governance validation for VISABLE R4
 * multilingual assets and runtime layer (VisableI18n).
 *
 * Checks:
 *   1. 15 supported locales cataloged and configured with valid metadata.
 *   2. Tier 1 completeness (ko, en, zh-CN, vi, id) across all checklist UI keys.
 *   3. Graceful fallback resolution for Tier 2 and Tier 3 locales.
 *   4. Arabic (ar) RTL metadata and direction configuration.
 *   5. Traditional Chinese (zh-TW) variant mapping.
 *   6. Statutory supremacy disclaimers present in all Tier 1 translations.
 *   7. Placeholder variable integrity ({code}, {name}) across languages.
 *   8. Procedure title mapping across languages.
 * ============================================================================
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const i18nCode = readFileSync(join(ROOT, 'assets/js/visable-i18n.js'), 'utf8');

// Execute script in mock global
const sandbox = {
  window: {
    location: { search: '' },
    localStorage: {
      getItem: () => null,
      setItem: () => {}
    },
    addEventListener: () => {},
    fetch: async (url) => {
      try {
        const full = join(ROOT, String(url).replace(/^\//, ''));
        const content = readFileSync(full, 'utf8');
        return { ok: true, json: async () => JSON.parse(content) };
      } catch (_) {
        return { ok: false, status: 404 };
      }
    }
  },
  document: {
    documentElement: { lang: 'ko', dir: 'ltr', setAttribute: () => {}, getAttribute: () => null, removeAttribute: () => {} },
    body: {
      setAttribute: () => {},
      getAttribute: () => null,
      removeAttribute: () => {},
      classList: {
        add: () => {},
        remove: () => {}
      }
    }
  }
};

const runInSandbox = new Function('window', 'document', 'localStorage', 'location', 'fetch', i18nCode);
runInSandbox(sandbox.window, sandbox.document, sandbox.window.localStorage, sandbox.window.location, sandbox.window.fetch);

const VisableI18n = sandbox.window.VisableI18n;
if (!VisableI18n) {
  console.error('FAIL: VisableI18n was not exported on window');
  process.exit(1);
}

let passed = 0;
const failures = [];

function check(title, fn) {
  try {
    fn();
    passed++;
  } catch (err) {
    failures.push(`${title}: ${err.message}`);
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

// 1. Locale Catalog Check
check('15 supported locales cataloged with correct Tier assignments', () => {
  const locales = VisableI18n.getAvailableLocales();
  assert(locales.length === 15, `Expected 15 locales, found ${locales.length}`);

  const tier1 = locales.filter(l => l.tier === 1).map(l => l.code);
  const expectedTier1 = ['ko', 'en', 'zh-CN', 'vi', 'id'];
  for (const exp of expectedTier1) {
    assert(tier1.includes(exp), `Tier 1 missing expected locale: ${exp}`);
  }

  const tier2 = locales.filter(l => l.tier === 2).map(l => l.code);
  const expectedTier2 = ['zh-TW', 'ja', 'tl', 'ru', 'ar'];
  for (const exp of expectedTier2) {
    assert(tier2.includes(exp), `Tier 2 missing expected locale: ${exp}`);
  }
});

// 2. Arabic RTL Check
check('Arabic (ar) correctly flagged as RTL direction', () => {
  assert(VisableI18n.isRTL('ar') === true, 'ar should be RTL');
  assert(VisableI18n.isRTL('ko') === false, 'ko should not be RTL');
  assert(VisableI18n.isRTL('en') === false, 'en should not be RTL');
  assert(VisableI18n.isRTL('zh-CN') === false, 'zh-CN should not be RTL');
});

// 3. Tier 1 Translation Completeness in CHECKLIST_STRINGS
check('All CHECKLIST_STRINGS have translations for all Tier 1 locales (ko, en, zh-CN, vi, id)', () => {
  const strings = VisableI18n.CHECKLIST_STRINGS;
  const keys = Object.keys(strings);
  assert(keys.length >= 30, `Expected at least 30 UI string keys, found ${keys.length}`);

  const tier1 = ['ko', 'en', 'zh-CN', 'vi', 'id'];
  for (const k of keys) {
    const entry = strings[k];
    if (typeof entry === 'object') {
      for (const loc of tier1) {
        assert(
          typeof entry[loc] === 'string' && entry[loc].trim().length > 0,
          `String '${k}' missing or empty translation for Tier 1 locale '${loc}'`
        );
      }
    }
  }
});

// 4. Fallback Verification for Tier 2 and Tier 3 Locales
check('Fallback to English or Korean works reliably for all locales without throwing', () => {
  const locales = VisableI18n.getAvailableLocales();
  const sampleKeys = ['navGuided', 'heroEyebrow', 'step1Title', 'badgeRequired', 'legalWarningNote'];

  for (const loc of locales) {
    VisableI18n.setLocale(loc.code);
    for (const key of sampleKeys) {
      const val = VisableI18n.t(key);
      assert(typeof val === 'string' && val.length > 0, `t('${key}') returned empty for locale '${loc.code}'`);
    }
  }
  // Reset to ko
  VisableI18n.setLocale('ko');
});

// 5. Statutory Supremacy Banner & Caveat Quality
check('Statutory supremacy warning banner is present in all Tier 1 translations', () => {
  const strings = VisableI18n.CHECKLIST_STRINGS;
  const warning = strings.legalWarningNote;
  assert(warning, 'legalWarningNote key must exist');

  const tier1 = ['ko', 'en', 'zh-CN', 'vi', 'id'];
  for (const loc of tier1) {
    const text = warning[loc];
    assert(text && text.length > 30, `legalWarningNote in '${loc}' is suspiciously short`);
    if (loc === 'ko') {
      assert(text.includes('법무부') && text.includes('원문'), 'Korean legal warning must mention MOJ and authoritative text');
    } else if (loc === 'en') {
      assert(text.includes('authoritative') && text.includes('Korean'), 'English legal warning must mention Korean authoritative text');
    }
  }
});

// 6. Placeholder Parameter Integrity
check('Parameter placeholders ({code}, {name}) match across translations', () => {
  const strings = VisableI18n.CHECKLIST_STRINGS;
  for (const [key, map] of Object.entries(strings)) {
    if (typeof map !== 'object') continue;
    const koText = map.ko || '';
    const koPlaceholders = (koText.match(/\{[a-zA-Z0-9_]+\}/g) || []).sort();
    if (!koPlaceholders.length) continue;

    for (const [loc, text] of Object.entries(map)) {
      if (typeof text !== 'string') continue;
      const placeholders = (text.match(/\{[a-zA-Z0-9_]+\}/g) || []).sort();
      assert(
        JSON.stringify(placeholders) === JSON.stringify(koPlaceholders),
        `Placeholder mismatch in '${key}' for '${loc}': expected ${koPlaceholders}, got ${placeholders}`
      );
    }
  }
});

// 7. Procedure Name Mapping
check('getProcedureName produces localized procedures for all Tier 1 locales', () => {
  const procs = ['extension', 'change', 'registration'];
  const tier1 = ['ko', 'en', 'zh-CN', 'vi', 'id'];

  for (const proc of procs) {
    for (const loc of tier1) {
      const name = VisableI18n.getProcedureName(proc, loc);
      assert(typeof name === 'string' && name.length > 0, `getProcedureName('${proc}', '${loc}') was empty`);
    }
  }
});

// Report
console.log(`[check_i18n_quality] Passed ${passed} checks.`);
if (failures.length > 0) {
  console.error(`[check_i18n_quality] FAILURES (${failures.length}):`);
  failures.forEach(f => console.error(`  - ${f}`));
  process.exit(1);
} else {
  console.log('[check_i18n_quality] ALL QUALITY CHECKS PASSED.');
}
