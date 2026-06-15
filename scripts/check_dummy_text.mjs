#!/usr/bin/env node
// Stage 6 guard: fails if user-facing DATA files contain dummy / placeholder /
// stale / internal-note markers that should never reach users.
//
// Design notes:
//  - Scans string VALUES only (not keys), recursively, skipping internal/audit
//    fields whose key starts with "_" (e.g. _source_notes, _searchAliasAudit).
//  - Uses a CURATED, high-confidence banned list. Legitimate Korean words the
//    task lists as search terms (예시, 임시, 준비 중) and the legitimate
//    abbreviation "N/A" are intentionally NOT banned, to avoid false positives
//    on honest copy. Honest source-gap messaging is allowed by design.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

const TARGET_FILES = [
  'data/i18n/ko.json',
  'data/i18n/en.json',
  'data/i18n/zh-CN.json',
  'visa_data.json',
  'backend/data/visas.json',
  'doc_master.json',
  'data/doc_guide.json',
  'data/scenario_help_records.json',
];

// [needle, reason] — ASCII matched case-insensitively; Hangul matched exactly.
const BANNED = [
  ['lorem ipsum', 'lorem ipsum filler'],
  ['lorem', 'lorem filler'],
  ['ipsum', 'ipsum filler'],
  ['scaffold', 'scaffold placeholder framing'],
  ['샘플 데이터', 'stale "sample data" framing'],
  ['더미 데이터', 'dummy-data placeholder'],
  ['더미데이터', 'dummy-data placeholder'],
  ['dummy data', 'dummy-data placeholder'],
  ['테스트 문구', 'test placeholder copy'],
  ['내부용', 'internal-only note exposed to users'],
  ['placeholder text', 'placeholder text'],
  ['todo:', 'TODO marker in user-facing copy'],
  ['fixme', 'FIXME marker in user-facing copy'],
  ['asdf', 'keyboard-mash placeholder'],
  ['qwerty', 'keyboard-mash placeholder'],
  ['xxxxx', 'XXXX placeholder'],
];

const findings = [];
function scanValue(value, keyPath, file) {
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    for (const [needle, reason] of BANNED) {
      if (lower.includes(needle.toLowerCase())) {
        findings.push({ file, keyPath, needle, reason, snippet: value.slice(0, 100).replace(/\s+/g, ' ') });
      }
    }
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => scanValue(v, `${keyPath}[${i}]`, file));
  } else if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      if (k.startsWith('_')) continue; // internal/audit fields, not user-facing
      scanValue(v, keyPath ? `${keyPath}.${k}` : k, file);
    }
  }
}

let scanned = 0;
for (const rel of TARGET_FILES) {
  const abs = path.join(repoRoot, rel);
  if (!fs.existsSync(abs)) continue;
  scanned++;
  let data;
  try { data = JSON.parse(fs.readFileSync(abs, 'utf8')); }
  catch (e) { findings.push({ file: rel, keyPath: '(root)', needle: 'JSON parse error', reason: e.message, snippet: '' }); continue; }
  scanValue(data, '', rel);
}

if (findings.length) {
  console.error('[check_dummy_text] User-facing dummy/placeholder/stale text found:');
  findings.slice(0, 60).forEach(f => console.error(` - ${f.file} :: ${f.keyPath} -> "${f.needle}" (${f.reason}) :: ${f.snippet}`));
  if (findings.length > 60) console.error(` - ... ${findings.length - 60} more`);
  process.exit(1);
}
console.log(`[check_dummy_text] OK — no user-facing dummy/placeholder/stale markers across ${scanned} data files`);
