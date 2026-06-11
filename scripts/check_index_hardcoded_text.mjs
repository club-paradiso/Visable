#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const indexPath = process.env.CHECK_I18N_INDEX || path.join(repoRoot, 'index.html');
const html = fs.readFileSync(indexPath, 'utf8');

const allowlist = [
  /Paradiso(?:\.ai)?/, /HiKorea/, /1345/, /K-ETA/, /Naver|Kakao|Google|Gmail/,
  /\b[A-H]-\d(?:-\d[A-Z]?)?\b/, /\bF-\d\b/, /\bE-\d\b/, /\bD-\d\b/, /\bC-\d\b/,
  /LAW_API_OC/, /visa_data\.json/, /doc_master\.json/, /TRANSLATION_PENDING/,
  /출입국관리법|출입국관리매뉴얼|출입국·외국인정책본부|법무부|하이코리아/,
];

const requiredRuntimeMarkers = [
  'I18N_MANIFEST_PATH',
  'loadI18nTranslations',
  'tx(',
  'data/i18n/manifest.json',
];

const suspicious = [];
const scriptBlocks = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
const jsStringRe = /(['"`])((?:\\.|(?!\1)[\s\S]){4,}?)\1/g;
const i18nStart = html.indexOf('const LANGUAGE_STORAGE_KEY');
const i18nEnd = html.indexOf('function toggleTheme()', i18nStart);
const textRe = /[가-힯\u3400-\u9fff]|\b(?:search|find|loading|error|source|document|deadline|hospital|agency|visa|residence|official)\b/i;

function isAllowed(value) {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length < 4) return true;
  if (allowlist.some((re) => re.test(trimmed))) return true;
  if (/^[.#?[<>{}()/:;,\s\w=-]+$/.test(trimmed) && !/[가-힯\u3400-\u9fff]/.test(trimmed)) return true;
  return false;
}

for (const marker of requiredRuntimeMarkers) {
  if (!html.includes(marker)) suspicious.push(`missing runtime marker: ${marker}`);
}

for (const block of scriptBlocks) {
  if (i18nStart >= 0 && block.index < i18nStart) continue;
  let script = block[1];
  if (block.index <= i18nStart && i18nEnd > i18nStart) {
    script = html.slice(i18nStart, i18nEnd);
  } else if (i18nEnd > i18nStart && block.index > i18nEnd) {
    continue;
  }
  script = script
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
  for (const match of script.matchAll(jsStringRe)) {
    const value = match[2];
    if (!textRe.test(value)) continue;
    if (isAllowed(value)) continue;
    const line = html.slice(0, block.index + match.index).split('\n').length;
    suspicious.push(`${line}: ${value.slice(0, 120).replace(/\s+/g, ' ')}`);
  }
}

if (suspicious.length) {
  console.error('[check_index_hardcoded_text] Suspicious inline UI strings remain:');
  suspicious.slice(0, 80).forEach((item) => console.error(`- ${item}`));
  if (suspicious.length > 80) console.error(`- ... ${suspicious.length - 80} more`);
  process.exit(1);
}

console.log('[check_index_hardcoded_text] OK — i18n runtime present; no suspicious unallowlisted inline UI strings found');
