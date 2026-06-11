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
  /^(?:한국어|简体中文|繁體中文|日本語|हिन्दी|नेपाली|ไทย|ភាសាខ្មែរ|العربية|Монгол|فارسی|Русский)$/,
];

const requiredRuntimeMarkers = [
  'I18N_MANIFEST_PATH',
  'loadI18nTranslations',
  'tx(',
  'data/i18n/manifest.json',
];

const suspicious = [];
const scriptBlocks = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
const i18nStart = html.indexOf('const LANGUAGE_STORAGE_KEY');
const i18nEnd = html.indexOf('function toggleTheme()', i18nStart);
const textRe = /[가-힯\u3400-\u9fff]|\b(?:search|find|loading|error|source|document|deadline|hospital|agency|visa|residence|official)\b/i;
const bootstrapFallbackRe = /const BOOTSTRAP_KO_FALLBACK\s*=\s*\{[\s\S]*?\n\};/;

function skipQuoted(source, start) {
  const quote = source[start];
  let i = start + 1;
  while (i < source.length) {
    if (source[i] === '\\') {
      i += 2;
      continue;
    }
    if (source[i] === quote) return i + 1;
    i += 1;
  }
  return source.length;
}

function skipTemplateLiteral(source, start) {
  let i = start + 1;
  while (i < source.length) {
    if (source[i] === '\\') {
      i += 2;
      continue;
    }
    if (source[i] === '$' && source[i + 1] === '{') {
      i = skipTemplateExpression(source, i + 2);
      continue;
    }
    if (source[i] === '`') return i + 1;
    i += 1;
  }
  return source.length;
}

function skipTemplateExpression(source, start) {
  let depth = 1;
  let i = start;
  while (i < source.length && depth > 0) {
    const ch = source[i];
    if (ch === '"' || ch === "'") {
      i = skipQuoted(source, i);
      continue;
    }
    if (ch === '`') {
      i = skipTemplateLiteral(source, i);
      continue;
    }
    if (ch === '{') depth += 1;
    if (ch === '}') depth -= 1;
    i += 1;
  }
  return i;
}

function* scanStringLiterals(source, baseOffset = 0) {
  let i = 0;
  while (i < source.length) {
    const quote = source[i];
    if (quote === '"' || quote === "'") {
      const start = i;
      i += 1;
      let value = '';
      while (i < source.length) {
        if (source[i] === '\\') {
          value += source[i + 1] || '';
          i += 2;
          continue;
        }
        if (source[i] === quote) {
          i += 1;
          break;
        }
        value += source[i];
        i += 1;
      }
      yield { value, index: baseOffset + start, end: baseOffset + i };
      continue;
    }
    if (quote === '`') {
      i += 1;
      let segmentStart = i;
      let value = '';
      while (i < source.length) {
        if (source[i] === '\\') {
          value += source[i + 1] || '';
          i += 2;
          continue;
        }
        if (source[i] === '`') {
          if (value) yield { value, index: baseOffset + segmentStart, end: baseOffset + i };
          i += 1;
          break;
        }
        if (source[i] === '$' && source[i + 1] === '{') {
          if (value) yield { value, index: baseOffset + segmentStart, end: baseOffset + i };
          i = skipTemplateExpression(source, i + 2);
          segmentStart = i;
          value = '';
          continue;
        }
        value += source[i];
        i += 1;
      }
      continue;
    }
    i += 1;
  }
}

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
  const blockStart = block.index;
  const blockEnd = block.index + block[0].length;
  const scriptContentStart = block.index + block[0].indexOf(block[1]);
  let script = block[1];
  let scriptOffset = scriptContentStart;
  if (i18nStart >= 0 && i18nEnd > i18nStart) {
    if (blockEnd <= i18nStart || blockStart >= i18nEnd) continue;
    const sliceStart = Math.max(i18nStart, blockStart);
    const sliceEnd = Math.min(i18nEnd, blockEnd);
    script = html.slice(sliceStart, sliceEnd);
    scriptOffset = sliceStart;
  }
  script = script.replace(bootstrapFallbackRe, '');
  script = script
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
  for (const literal of scanStringLiterals(script)) {
    const value = literal.value;
    if (!textRe.test(value)) continue;
    if (isAllowed(value)) continue;
    const line = html.slice(0, scriptOffset + literal.index).split('\n').length;
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
