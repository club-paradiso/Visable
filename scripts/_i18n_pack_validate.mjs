#!/usr/bin/env node
/**
 * Structural validator for a translated i18n pack against the Korean canonical.
 * Usage: node scripts/_i18n_pack_validate.mjs <locale-code> [pack-path]
 *
 * Checks (hard = exit 1):
 *  - identical set of leaf paths vs ko.json (no missing / extra)
 *  - identical value shapes (string/array length/object) at every path
 *  - every visa/status code in the ko value survives verbatim in the translation
 *  - every {placeholder} in the ko value is present in the translation
 *  - no banned invisible/bidi unicode (U+202F/200B/200C/200E/200F/2060/FEFF/00AD/180E)
 * Warns (does not fail) on:
 *  - translated string still containing Hangul (likely untranslated → would leak)
 *    except leaves whose ko is itself code/number/url-only.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const i18nDir = path.join(repoRoot, 'data', 'i18n');

const code = process.argv[2];
if (!code) { console.error('usage: node scripts/_i18n_pack_validate.mjs <locale> [path]'); process.exit(2); }
const packPath = process.argv[3] || path.join(i18nDir, `${code}.json`);

const ko = JSON.parse(fs.readFileSync(path.join(i18nDir, 'ko.json'), 'utf8'));
let pack;
try { pack = JSON.parse(fs.readFileSync(packPath, 'utf8')); }
catch (e) { console.error(`[validate ${code}] CANNOT READ/PARSE ${packPath}: ${e.message}`); process.exit(1); }

const CODE_RE = /\b[A-Z]{1,3}-\d{1,2}(?:-(?:\d{1,2}[A-Z]?|T))?\b/g;
const PH_RE = /\{[a-zA-Z0-9_]+\}/g;
const HANGUL_RE = /[가-힣ᄀ-ᇿ㄰-㆏]/;
const INVISIBLE_RE = /[\u202F\u200B\u200C\u200E\u200F\u2060\uFEFF\u00AD\u180E]/;

function flatten(value, prefix, out) {
  if (Array.isArray(value)) value.forEach((v, i) => flatten(v, `${prefix}[${i}]`, out));
  else if (value && typeof value === 'object') {
    for (const k of Object.keys(value)) flatten(value[k], prefix ? `${prefix}.${k}` : k, out);
  } else out.set(prefix, value);
}
function shape(v) { return Array.isArray(v) ? `array:${v.length}` : (v && typeof v === 'object') ? 'object' : typeof v; }

// shape map (includes container nodes) for structural compare
function shapes(value, prefix, out) {
  out.set(prefix, shape(value));
  if (Array.isArray(value)) value.forEach((v, i) => shapes(v, `${prefix}[${i}]`, out));
  else if (value && typeof value === 'object') for (const k of Object.keys(value)) shapes(value[k], prefix ? `${prefix}.${k}` : k, out);
}

const koLeaves = new Map(); flatten(ko, '', koLeaves);
const pkLeaves = new Map(); flatten(pack, '', pkLeaves);
const koShapes = new Map(); shapes(ko, '', koShapes);
const pkShapes = new Map(); shapes(pack, '', pkShapes);

let hard = 0; const warns = [];
const koPaths = new Set(koLeaves.keys()), pkPaths = new Set(pkLeaves.keys());
const missing = [...koPaths].filter(p => !pkPaths.has(p));
const extra = [...pkPaths].filter(p => !koPaths.has(p));
if (missing.length) { hard++; console.error(`[validate ${code}] MISSING ${missing.length} leaf path(s), e.g.: ${missing.slice(0,8).join(' | ')}`); }
if (extra.length) { hard++; console.error(`[validate ${code}] EXTRA ${extra.length} leaf path(s), e.g.: ${extra.slice(0,8).join(' | ')}`); }

for (const [p, s] of koShapes) {
  if (pkShapes.has(p) && pkShapes.get(p) !== s) { hard++; console.error(`[validate ${code}] SHAPE ${p}: expected ${s} got ${pkShapes.get(p)}`); }
}

let codeViol = 0, phViol = 0, hangulWarn = 0, invis = 0;
for (const [p, koVal] of koLeaves) {
  if (typeof koVal !== 'string' || !pkLeaves.has(p)) continue;
  const tr = pkLeaves.get(p);
  if (typeof tr !== 'string') continue;
  for (const cd of new Set(koVal.match(CODE_RE) || [])) {
    if (!tr.includes(cd)) { hard++; codeViol++; if (codeViol <= 8) console.error(`[validate ${code}] CODE ${p}: '${cd}' missing from translation`); }
  }
  for (const ph of new Set(koVal.match(PH_RE) || [])) {
    if (!tr.includes(ph)) { hard++; phViol++; if (phViol <= 8) console.error(`[validate ${code}] PLACEHOLDER ${p}: '${ph}' missing from translation`); }
  }
  if (INVISIBLE_RE.test(tr)) { hard++; invis++; if (invis <= 8) console.error(`[validate ${code}] INVISIBLE-UNICODE at ${p}`); }
  // untranslated-Hangul warning: only when ko itself is "real" text (has Hangul) and
  // the translation still has Hangul AND target isn't Korean-ish.
  if (code !== 'ko' && HANGUL_RE.test(tr) && HANGUL_RE.test(koVal)) { hangulWarn++; if (hangulWarn <= 12) warns.push(`${p}: "${tr.slice(0,40)}"`); }
}

if (hangulWarn) console.warn(`[validate ${code}] WARN: ${hangulWarn} translated leaf(s) still contain Hangul (possible leak). e.g.: ${warns.slice(0,12).join(' | ')}`);

if (hard) { console.error(`[validate ${code}] FAIL — ${hard} hard issue(s) (codeViol=${codeViol} phViol=${phViol} invisible=${invis})`); process.exit(1); }
console.log(`[validate ${code}] OK — ${koLeaves.size} leaves, structure+codes+placeholders match (Hangul-warnings: ${hangulWarn})`);
