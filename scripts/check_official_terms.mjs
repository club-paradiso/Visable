#!/usr/bin/env node
/**
 * Official-terms glossary + i18n safety validator.
 *
 * Fails on:
 * - broken JSON anywhere in data/i18n/
 * - manifest regressions (zh-CN removed, ko not default/fallback, missing
 *   locale labels, locale files missing)
 * - language-selector locales not declared in the manifest
 * - glossary schema violations (bad ids, missing Korean canonical, invalid
 *   confidence/sourceType, unverified non-null translations without
 *   preserveKoreanWhenUnverified, docIds that don't exist in DOC_DICT)
 * - visa/status codes present in a Korean value but missing/altered in the
 *   en or zh-CN value (locale packs and glossary)
 * - suspicious invisible Unicode (U+202F etc.; U+200D emoji ZWJ allowed)
 * - client-side exposure of credential env-var names or secret-shaped tokens
 *
 * Warns (does not fail) on glossary terms with no usage links.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const i18nDir = path.join(repoRoot, 'data', 'i18n');

let failures = 0;
function fail(message) {
  console.error(`[check_official_terms] FAIL: ${message}`);
  failures += 1;
}
function warn(message) {
  console.warn(`[check_official_terms] warn: ${message}`);
}

function readJson(file) {
  const full = path.isAbsolute(file) ? file : path.join(repoRoot, file);
  try {
    return JSON.parse(fs.readFileSync(full, 'utf8'));
  } catch (err) {
    fail(`broken JSON: ${file} — ${err.message}`);
    return null;
  }
}

// ── 1. All i18n JSON parses ────────────────────────────────────────────────
for (const file of fs.readdirSync(i18nDir).filter((f) => f.endsWith('.json'))) {
  readJson(path.join('data/i18n', file));
}

// ── 2. Manifest invariants (zh-CN must stay; ko canonical) ────────────────
const manifest = readJson('data/i18n/manifest.json') || {};
if (manifest.defaultLocale !== 'ko') fail('manifest.defaultLocale must be ko');
if ((manifest.fallbackLocale || 'ko') !== 'ko') fail('manifest.fallbackLocale must be ko');
const supported = manifest.supportedLocales || [];
if (supported.join(',') !== 'ko,en,zh-CN') {
  fail(`manifest.supportedLocales must be exactly ko,en,zh-CN (got: ${supported.join(',')})`);
}
for (const locale of supported) {
  if (!manifest.localeLabels?.[locale]) fail(`manifest.localeLabels missing ${locale}`);
  const file = manifest.files?.[locale];
  if (!file || !fs.existsSync(path.join(i18nDir, file))) fail(`locale file missing for ${locale}`);
}

// ── 3. Selector locales must be declared in the manifest ──────────────────
const html = fs.readFileSync(path.join(repoRoot, 'index.html'), 'utf8');
const optionsBlock = html.match(/const LANGUAGE_OPTIONS = \[([\s\S]*?)\n\];/);
if (!optionsBlock) {
  fail('could not locate LANGUAGE_OPTIONS in index.html');
} else {
  const declared = new Set([
    ...(supported || []),
    ...(manifest.pendingLocales || []),
    ...Object.keys(manifest.localeAliases || {}),
  ]);
  for (const match of optionsBlock[1].matchAll(/code:\s*'([^']+)'/g)) {
    if (!declared.has(match[1])) {
      fail(`language selector exposes locale '${match[1]}' not declared in manifest supported/pending locales`);
    }
  }
}

// ── 4. Glossary schema ─────────────────────────────────────────────────────
const glossary = readJson('data/i18n/official-terms.json') || {};
const CONFIDENCE = new Set(['canonical', 'official', 'manual-derived', 'curated', 'fallback', 'needs-verification']);
const DISPLAYABLE = new Set(['canonical', 'official', 'manual-derived', 'curated']);
const SOURCE_TYPES = new Set(['law-api', 'english-law', 'manual-derived', 'hikorea', 'visa-portal', 'mofa', 'curated', 'unknown']);
const LOCALES = ['en', 'zh-CN'];

const docDictBlock = html.match(/const DOC_DICT = \{([\s\S]*?)\n\};/);
const docDictIds = new Set();
if (docDictBlock) {
  for (const match of docDictBlock[1].matchAll(/"(doc_[a-z0-9_]+)"\s*:/g)) docDictIds.add(match[1]);
} else {
  fail('could not locate DOC_DICT in index.html');
}

const terms = glossary.terms || {};
if (!Object.keys(terms).length) fail('official-terms.json has no terms');
const referenceOnlyTerms = [];
for (const [termId, entry] of Object.entries(terms)) {
  const where = `official-terms.${termId}`;
  if (!/^[a-z0-9_]+$/.test(termId)) fail(`${where}: term id must be snake_case ascii`);
  if (typeof entry.ko !== 'string' || !entry.ko.trim()) fail(`${where}: ko canonical term is required`);
  if (!SOURCE_TYPES.has(entry.sourceType)) fail(`${where}: invalid sourceType '${entry.sourceType}'`);
  if (entry.confidence?.ko && entry.confidence.ko !== 'canonical') {
    fail(`${where}: confidence.ko must be 'canonical'`);
  }
  for (const locale of LOCALES) {
    const value = entry[locale];
    if (value !== null && typeof value !== 'string') {
      fail(`${where}: ${locale} must be a string or null`);
      continue;
    }
    const confidence = entry.confidence?.[locale];
    if (confidence !== undefined && !CONFIDENCE.has(confidence)) {
      fail(`${where}: invalid confidence.${locale} '${confidence}'`);
    }
    if (typeof value === 'string' && value.trim()) {
      if (!confidence) fail(`${where}: non-null ${locale} translation requires a confidence entry`);
      if (confidence && !DISPLAYABLE.has(confidence) && entry.preserveKoreanWhenUnverified !== true) {
        fail(`${where}: unverified ${locale} translation must set preserveKoreanWhenUnverified: true`);
      }
    }
  }
  for (const docId of entry.docIds || []) {
    if (!docDictIds.has(docId)) fail(`${where}: docIds references '${docId}' which is not in DOC_DICT`);
  }
  if (!(entry.docIds || []).length) referenceOnlyTerms.push(termId);
}
if (referenceOnlyTerms.length) {
  warn(`${referenceOnlyTerms.length} reference-only glossary term(s) without docIds links (fine, listed for visibility): ${referenceOnlyTerms.join(', ')}`);
}

// ── 5. Visa/status codes must survive translation untouched ───────────────
const CODE_RE = /\b[A-Z]{1,3}-\d{1,2}(?:-(?:\d{1,2}[A-Z]?|T))?\b/g;
function codesIn(value) {
  return typeof value === 'string' ? value.match(CODE_RE) || [] : [];
}
function flatten(value, prefix = '') {
  if (Array.isArray(value)) return value.flatMap((item, i) => flatten(item, `${prefix}[${i}]`));
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([k, v]) => flatten(v, prefix ? `${prefix}.${k}` : k));
  }
  return [[prefix, value]];
}
const packs = {};
for (const locale of ['ko', ...LOCALES]) {
  packs[locale] = readJson(path.join('data/i18n', manifest.files?.[locale] || `${locale}.json`)) || {};
}
const koFlat = new Map(flatten(packs.ko));
for (const locale of LOCALES) {
  const localeFlat = new Map(flatten(packs[locale]));
  for (const [key, koValue] of koFlat) {
    const koCodes = codesIn(koValue);
    if (!koCodes.length) continue;
    const localeValue = localeFlat.get(key);
    if (typeof localeValue !== 'string') continue;
    for (const code of new Set(koCodes)) {
      if (!localeValue.includes(code)) {
        fail(`${locale}.${key}: visa/status code '${code}' from the Korean value is missing or altered`);
      }
    }
  }
}
for (const [termId, entry] of Object.entries(terms)) {
  const koCodes = new Set(codesIn(entry.ko));
  for (const locale of LOCALES) {
    if (typeof entry[locale] !== 'string') continue;
    for (const code of koCodes) {
      if (!entry[locale].includes(code)) {
        fail(`official-terms.${termId}.${locale}: visa/status code '${code}' missing from translation`);
      }
    }
  }
}

// ── 6. Invisible / suspicious Unicode ──────────────────────────────────────
// U+200D (emoji ZWJ) is allowed; everything below is banned.
const INVISIBLE_RE = /[\u202F\u200B\u200C\u200E\u200F\u2060\uFEFF\u00AD\u180E]/;
const unicodeTargets = [
  'index.html',
  'ai.html',
  'form-helper.html',
  ...fs.readdirSync(i18nDir).map((f) => path.join('data/i18n', f)),
];
for (const file of unicodeTargets) {
  const full = path.join(repoRoot, file);
  if (!fs.existsSync(full)) continue;
  const text = fs.readFileSync(full, 'utf8');
  const match = text.match(INVISIBLE_RE);
  if (match) {
    const codePoint = match[0].codePointAt(0).toString(16).toUpperCase().padStart(4, '0');
    const line = text.slice(0, match.index).split('\n').length;
    fail(`${file}:${line} contains banned invisible character U+${codePoint}`);
  }
}

// ── 7. No client-side credential exposure ──────────────────────────────────
const CREDENTIAL_RES = [
  /LAW_OPEN_API_OC/,
  /DATA_GO_KR_API_KEY/,
  /\bsk-[A-Za-z0-9]{20,}/,
  /\bAIza[0-9A-Za-z_-]{30,}/,
  /serviceKey=[A-Za-z0-9%+/=]{20,}/,
];
for (const file of ['index.html', 'ai.html', 'form-helper.html']) {
  const full = path.join(repoRoot, file);
  if (!fs.existsSync(full)) continue;
  const text = fs.readFileSync(full, 'utf8');
  for (const re of CREDENTIAL_RES) {
    const match = text.match(re);
    if (match) {
      const line = text.slice(0, match.index).split('\n').length;
      fail(`${file}:${line} exposes credential-looking content (${re})`);
    }
  }
}

if (failures) {
  console.error(`[check_official_terms] ${failures} failure(s)`);
  process.exit(1);
}
console.log(`[check_official_terms] OK — glossary schema, manifest invariants, code preservation, Unicode and credential scans passed (${Object.keys(terms).length} glossary terms)`);
