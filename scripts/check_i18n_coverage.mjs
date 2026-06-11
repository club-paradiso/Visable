#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const i18nDir = path.join(repoRoot, 'data', 'i18n');
const requiredLocales = ['ko', 'en', 'zh-CN'];

function fail(message) {
  console.error(`[check_i18n_coverage] ${message}`);
  process.exitCode = 1;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(path.join(i18nDir, file), 'utf8'));
}

function flatten(value, prefix = '') {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flatten(item, `${prefix}[${index}]`));
  }
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().flatMap((key) => flatten(value[key], prefix ? `${prefix}.${key}` : key));
  }
  return [prefix];
}

function typeShape(value) {
  if (Array.isArray(value)) return `array:${value.length}`;
  if (value && typeof value === 'object') return 'object';
  return typeof value;
}

function getByPath(root, flatPath) {
  return flatPath.split('.').reduce((value, part) => {
    const match = part.match(/^(.+)\[(\d+)\]$/);
    if (match) return value?.[match[1]]?.[Number(match[2])];
    return value?.[part];
  }, root);
}

const manifest = readJson('manifest.json');
for (const locale of requiredLocales) {
  if (!manifest.supportedLocales?.includes(locale)) {
    fail(`manifest.supportedLocales is missing ${locale}`);
  }
  const file = manifest.files?.[locale];
  if (!file || !fs.existsSync(path.join(i18nDir, file))) {
    fail(`manifest file entry for ${locale} is missing or unreadable`);
  }
}

const packs = Object.fromEntries(requiredLocales.map((locale) => [locale, readJson(manifest.files[locale])]));
const canonicalKeys = flatten(packs.ko).sort();

for (const locale of requiredLocales.filter((locale) => locale !== 'ko')) {
  const keys = flatten(packs[locale]).sort();
  const missing = canonicalKeys.filter((key) => !keys.includes(key));
  const extra = keys.filter((key) => !canonicalKeys.includes(key));
  if (missing.length) fail(`${locale} is missing keys: ${missing.join(', ')}`);
  if (extra.length) fail(`${locale} has extra keys: ${extra.join(', ')}`);
  for (const key of canonicalKeys) {
    if (!keys.includes(key)) continue;
    const koShape = typeShape(getByPath(packs.ko, key));
    const localeShape = typeShape(getByPath(packs[locale], key));
    if (koShape !== localeShape) fail(`${locale}.${key} shape mismatch: expected ${koShape}, got ${localeShape}`);
  }
}

if (!process.exitCode) {
  console.log(`[check_i18n_coverage] OK — ${canonicalKeys.length} keys match across ${requiredLocales.join('/')}`);
}
