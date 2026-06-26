#!/usr/bin/env node
// Stage 6 guard: fails if user-facing DATA files (or the frontend index.html /
// ai.html) contain dummy / placeholder / stale / internal-note markers, private
// third-party provenance, or raw auto-extraction diagnostics that should never
// reach users.
//
// Design notes:
//  - Scans string VALUES only (not keys), recursively, skipping internal/audit
//    fields whose key starts with "_" (e.g. _source_notes, _searchAliasAudit).
//  - Uses a CURATED, high-confidence banned list. Legitimate Korean words the
//    task lists as search terms (예시, 임시, 준비 중) and the legitimate
//    abbreviation "N/A" are intentionally NOT banned, to avoid false positives
//    on honest copy. Honest source-gap messaging ("매뉴얼 확인 필요", and the
//    "…수동 검토 필요." review-gate notes) is allowed by design: those are real
//    review gates that the renderer display-suppresses (verified by
//    check_placeholder_suppression.js), so banning them here would erase a gate.
//  - PROVENANCE/DIAGNOSTIC guard (2026-06 final professionalism pass): private
//    third-party reviewer credits (e.g. "Mr. Visa Korea 행정사 검토") and raw
//    auto-extraction diagnostics (e.g. "보수적 자동 추출 … 확정하지 못했습니다")
//    must NEVER appear in generated user-facing data OR in the frontend
//    (index.html / ai.html). The PROVENANCE_DIAGNOSTIC list below is checked in
//    BOTH the JSON data files and the two HTML entry points.
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

// Private third-party provenance + raw auto-extraction diagnostics. These must
// NEVER appear in generated user-facing data OR the frontend (index.html/ai.html).
// ASCII matched case-insensitively; Hangul matched exactly.
const PROVENANCE_DIAGNOSTIC = [
  ['mr. visa', 'private third-party reviewer credited as if official source'],
  ['mr.visa', 'private third-party reviewer credited as if official source'],
  ['행정사 검토', 'private third-party reviewer provenance stamp (not official)'],
  ['private third-party reviewer', 'private reviewer provenance label'],
  ['third-party reviewer', 'private reviewer provenance label'],
  ['사설 검토', 'private-review provenance (not official)'],
  ['민간 검토', 'private-review provenance (not official)'],
  ['민간 자문', 'private-advisory provenance (not official)'],
  ['보수적 자동 추출', 'raw auto-extraction diagnostic (reads as unfinished)'],
  ['확정하지 못했습니다', 'raw auto-extraction diagnostic (reads as unfinished)'],
  ['not found in evidence', 'internal evidence-gap diagnostic'],
];
const DATA_BANNED = [...BANNED, ...PROVENANCE_DIAGNOSTIC];

const findings = [];
function scanValue(value, keyPath, file) {
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    for (const [needle, reason] of DATA_BANNED) {
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

// Frontend scan: the provenance/diagnostic strings must also be absent from the
// two HTML entry points (rendered copy + inline scripts). We deliberately do NOT
// run the full BANNED list against HTML — attributes like placeholder="…" and dev
// TODO comments would false-positive; only the high-confidence provenance/diagnostic
// strings (which must never appear anywhere user-facing) are checked here.
const HTML_FILES = ['index.html', 'ai.html'];
for (const rel of HTML_FILES) {
  const abs = path.join(repoRoot, rel);
  if (!fs.existsSync(abs)) continue;
  scanned++;
  const text = fs.readFileSync(abs, 'utf8');
  const lower = text.toLowerCase();
  for (const [needle, reason] of PROVENANCE_DIAGNOSTIC) {
    const idx = lower.indexOf(needle.toLowerCase());
    if (idx >= 0) {
      findings.push({ file: rel, keyPath: `offset ${idx}`, needle, reason, snippet: text.slice(Math.max(0, idx - 20), idx + 60).replace(/\s+/g, ' ') });
    }
  }
}

if (findings.length) {
  console.error('[check_dummy_text] User-facing dummy/placeholder/stale/provenance text found:');
  findings.slice(0, 60).forEach(f => console.error(` - ${f.file} :: ${f.keyPath} -> "${f.needle}" (${f.reason}) :: ${f.snippet}`));
  if (findings.length > 60) console.error(` - ... ${findings.length - 60} more`);
  process.exit(1);
}
console.log(`[check_dummy_text] OK — no user-facing dummy/placeholder/stale/provenance markers across ${scanned} data + frontend files`);
