#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

const manifest = JSON.parse(fs.readFileSync(path.join(repoRoot, 'data/i18n/manifest.json'), 'utf8'));
const packs = Object.fromEntries(manifest.supportedLocales.map((locale) => [
  locale,
  JSON.parse(fs.readFileSync(path.join(repoRoot, 'data/i18n', manifest.files[locale]), 'utf8')),
]));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function tx(locale, key, vars = {}) {
  let value = packs[locale]?.[key] ?? packs.ko[key] ?? key;
  if (typeof value === 'string') {
    for (const [name, replacement] of Object.entries(vars)) value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

assert(manifest.defaultLocale === 'ko', 'default locale must be ko');
assert(manifest.supportedLocales.join(',') === 'ko,en,zh-CN', 'supported locales must be ko/en/zh-CN only');
assert(tx('ko', 'heroTitle') !== tx('en', 'heroTitle'), 'hero title should change between ko and en');
assert(tx('en', 'heroTitle') !== tx('zh-CN', 'heroTitle'), 'hero title should change between en and zh-CN');
assert(tx('en', 'dataReady', { count: 39, source: 'static' }).includes('39'), 'interpolation should substitute {count}');
assert(tx('missing-locale', 'qPlaceholder') === tx('ko', 'qPlaceholder'), 'missing locale should fall back to ko');

const html = fs.readFileSync(path.join(repoRoot, 'index.html'), 'utf8');
assert(html.includes('BOOTSTRAP_KO_FALLBACK'), 'index.html should include a built-in bootstrap fallback for failed i18n fetches');
assert(html.includes('hasFullKoI18nPack()'), 'index.html should guard full language binding when packs fail to load');
assert(!html.includes('UI_TRANSLATIONS.ko.landingHints[idx]'), 'landing hints must not assume ko landingHints exists during fallback');
assert(!html.includes('UI_TRANSLATIONS.ko.quickFilters[idx]'), 'quick filters must not assume ko quickFilters exists during fallback');

const hardcodedCheck = fs.readFileSync(path.join(repoRoot, 'scripts/check_index_hardcoded_text.mjs'), 'utf8');
assert(hardcodedCheck.includes('blockEnd <= i18nStart'), 'hardcoded-text scanner must not skip a script just because it starts before the i18n runtime');
assert(hardcodedCheck.includes('scanStringLiterals'), 'hardcoded-text scanner should parse JS literals without broad template-regex spans');

const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((match) => match[1]);
for (const script of scripts) new Function(script);

const visaData = JSON.parse(fs.readFileSync(path.join(repoRoot, 'visa_data.json'), 'utf8'));
const codes = new Set(visaData.map((record) => record && record.code).filter(Boolean));
for (const code of ['C-3', 'D-2', 'F-6']) {
  assert(codes.has(code), `visa_data.json should still contain ${code}`);
}

console.log('[smoke_static_i18n] OK — static packs load, hero text changes, fallback/interpolation works, inline scripts parse, visa data search fixtures remain');
