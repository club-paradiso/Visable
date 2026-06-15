#!/usr/bin/env node
/*
 * Smoke contract for the unified 사증발급 (visa issuance) procedure UI.
 *
 * Verifies that every NON-F-4 visa-issuance record carries the data needed to
 * render the unified procedure UI and that the renderer wiring is in place:
 *   A. header (Ko/En title + an evidence level that maps to a friendly badge),
 *   B. plain-language summary,
 *   C. standardized application-route chips — produced by executing the REAL
 *      index.html derivation function against each record,
 *   D. step list, E. document groups (common/additional/conditional),
 *   F. warnings (where present), G. source/evidence pointer for the 근거 block.
 *
 * It also proves F-4 is present in the data yet excluded from the generic
 * renderer (it keeps its dedicated diaspora route guide), and that no raw
 * placeholders or internal enum names leak into user-facing fields.
 *
 * Pure Node — no DOM, no deps. Run: node scripts/check_visa_issuance_ui.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

let checks = 0;
let failures = 0;
const failed = [];
function ok(cond, label) {
  checks += 1;
  if (!cond) { failures += 1; failed.push(label); }
}
function readJson(rel) { return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')); }
function readText(rel) { return fs.readFileSync(path.join(ROOT, rel), 'utf8'); }

// Brace-matched function extractor (same approach as check_static_visa_result_cards.js).
function extractFunction(src, name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(', 'g');
  const m = re.exec(src);
  if (!m) return '';
  const braceStart = src.indexOf('{', re.lastIndex);
  if (braceStart < 0) return '';
  let depth = 0;
  for (let i = braceStart; i < src.length; i += 1) {
    const ch = src[i];
    if (ch === '{') depth += 1;
    else if (ch === '}') { depth -= 1; if (depth === 0) return src.slice(m.index, i + 1); }
  }
  return '';
}

const EXCLUDED = new Set(['F-4']);
const issuance = readJson('data/visa_issuance_records.json');
const evidence = readJson('data/procedure_evidence_bindings.json');
const koPack = readJson('data/i18n/ko.json');
const indexHtml = readText('index.html');

const records = Array.isArray(issuance.records) ? issuance.records : [];
const bindings = (Array.isArray(evidence.records) ? evidence.records : [])
  .filter((r) => r.procedureType === 'visa_issuance');
const bindingByCode = new Map(bindings.map((r) => [r.code, r]));

// Evidence levels the UI maps to a friendly Korean/English badge label
// (mirror of SOURCE_EVIDENCE_LABELS in index.html). None render as a raw enum.
const FRIENDLY_EVIDENCE = new Set(['source_confirmed', 'contextual', 'limited', 'unavailable', 'not_applicable']);

// User-facing fields must never be a bare placeholder, nor contain internal tokens.
const PLACEHOLDER_EXACT = ['null', 'undefined', 'n/a', 'na', 'tbd'];
const INTERNAL_TOKENS = ['source_limited', 'official_source_limited', 'not_applicable',
  'consular_discretion', 'visa_issuance_confirmation', 'visa_exempt', '�'];

function userFacingStrings(record) {
  const out = [];
  const push = (v) => { if (typeof v === 'string' && v.trim()) out.push(v); };
  push(record.titleKo); push(record.titleEn);
  push(record.issuanceSummaryKo); push(record.issuanceSummaryEn);
  push(record.disclaimerKo); push(record.disclaimerEn);
  for (const mode of record.issuanceModes || []) {
    push(mode.labelKo); push(mode.labelEn); push(mode.appliesToKo); push(mode.appliesToEn);
    for (const s of mode.steps || []) { push(s.ko); push(s.en); }
    const d = mode.documents || {};
    [...(d.common || []), ...(d.additional || []), ...(d.conditional || [])].forEach(push);
    (mode.warnings || []).forEach(push);
  }
  return out;
}

// --- Execute the REAL route-chip derivation from index.html ------------------
const deriveSrc = extractFunction(indexHtml, 'deriveIssuanceRouteChips');
ok(!!deriveSrc, 'index.html defines deriveIssuanceRouteChips');
ok(/ISSUANCE_ROUTE_CHIP_INDEX\s*=\s*\{[\s\S]*?consular:\s*0[\s\S]*?perMission:\s*5/.test(indexHtml),
  'ISSUANCE_ROUTE_CHIP_INDEX mapping present and ordered (consular..perMission)');
const CHIP_INDEX = { consular: 0, confirmation: 1, eVisa: 2, visaPortal: 3, sponsor: 4, perMission: 5 };
const txAtStub = (key, idx, fallback = '') => (
  key === 'issuanceRouteChipLabels' ? (koPack.issuanceRouteChipLabels?.[idx] ?? fallback) : fallback
);
let deriveIssuanceRouteChips = () => [];
try {
  deriveIssuanceRouteChips = new Function('txAt', 'ISSUANCE_ROUTE_CHIP_INDEX',
    `${deriveSrc}\nreturn deriveIssuanceRouteChips;`)(txAtStub, CHIP_INDEX);
  ok(true, 'deriveIssuanceRouteChips is executable');
} catch (err) {
  ok(false, `deriveIssuanceRouteChips is executable: ${err.message}`);
}

// --- Per-record render contract (non-F-4) ------------------------------------
let nonF4 = 0;
for (const record of records) {
  const code = record.code || '(missing)';
  if (EXCLUDED.has(code)) continue;
  nonF4 += 1;
  const binding = bindingByCode.get(code);
  const mode = (record.issuanceModes || [])[0];

  // A. Header
  ok(!!(record.titleKo && record.titleEn), `${code}: header has Ko/En title`);
  ok(!!binding && FRIENDLY_EVIDENCE.has(binding.evidenceLevel),
    `${code}: evidence level maps to a friendly badge (no raw enum)`);
  // B. Summary
  ok(!!String(record.issuanceSummaryKo || '').trim(), `${code}: has a plain Korean summary`);
  // C. Route chips — execute the real derivation
  ok(!!mode, `${code}: has an issuance mode`);
  const chips = mode ? deriveIssuanceRouteChips(mode, record) : [];
  const isApplicationRoute = !!mode && !['visa_exempt', 'not_applicable'].includes(mode.type);
  if (isApplicationRoute) {
    ok(chips.length >= 1 && chips.every((c) => c.label),
      `${code}: produces >= 1 labeled application-route chip`);
  } else {
    ok(chips.length === 0, `${code}: non-application route (${mode && mode.type}) shows no route chips`);
  }
  // D. Steps
  ok(!!mode && Array.isArray(mode.steps) && mode.steps.length > 0
    && mode.steps.every((s) => String(s.ko || '').trim()), `${code}: has a Korean step list`);
  // E. Document groups
  const docs = (mode && mode.documents) || {};
  ok(typeof docs === 'object'
    && ['common', 'additional', 'conditional'].every((g) => Array.isArray(docs[g])),
    `${code}: documents expose common/additional/conditional groups`);
  if (binding && binding.evidenceLevel === 'source_confirmed') {
    ok((docs.common || []).length > 0, `${code}: source-confirmed route lists >= 1 common document`);
  }
  // F. Warnings (only where data exists)
  if (mode && Array.isArray(mode.warnings) && mode.warnings.length) {
    ok(mode.warnings.every((w) => String(w || '').trim()), `${code}: warnings are non-empty strings`);
  }
  // G. Source/evidence pointer for the 근거 block
  const hasSource = (binding && Array.isArray(binding.manualSources) && binding.manualSources.length > 0)
    || (mode && Array.isArray(mode.sourceRefs) && mode.sourceRefs.length > 0)
    || !!record.manualSource;
  ok(hasSource, `${code}: has a source/evidence pointer for the 근거 block`);
  // No raw placeholders/enums in user-facing fields
  for (const s of userFacingStrings(record)) {
    ok(!PLACEHOLDER_EXACT.includes(s.trim().toLowerCase()),
      `${code}: no bare placeholder field value ("${s.trim()}")`);
    const tok = INTERNAL_TOKENS.find((k) => s.includes(k));
    ok(!tok, `${code}: user-facing text free of internal token "${tok}"`);
  }
}
ok(nonF4 >= 38, `covered ${nonF4} non-F-4 issuance records (>= 38 expected)`);

// --- F-4 exclusion proof -----------------------------------------------------
ok(records.some((r) => r.code === 'F-4'), 'F-4 issuance record is present in data (not deleted)');
ok(/GENERIC_VISA_ISSUANCE_EXCLUDED_CODES\s*=\s*new Set\(\[\s*'F-4'/.test(indexHtml),
  'index.html declares F-4 in GENERIC_VISA_ISSUANCE_EXCLUDED_CODES');
ok(/function renderVisaIssuanceSection[\s\S]*?isGenericVisaIssuanceExcluded\(\s*v\.code\s*\)/.test(indexHtml),
  'renderVisaIssuanceSection short-circuits excluded codes before rendering');
// Execute the real exclusion guard to prove it filters F-4 (all spellings).
const normSrc = extractFunction(indexHtml, 'normalizeVisaCode');
const guardSrc = extractFunction(indexHtml, 'isGenericVisaIssuanceExcluded');
const setSrc = (indexHtml.match(/const GENERIC_VISA_ISSUANCE_EXCLUDED_CODES = new Set\(\[[^\]]*\]\);/) || [''])[0];
try {
  const guard = new Function(`${normSrc}\n${setSrc}\n${guardSrc}\nreturn isGenericVisaIssuanceExcluded;`)();
  ok(guard('F-4') && guard('f-4') && guard('F4'), 'guard excludes F-4 across code spellings');
  ok(!guard('D-2') && !guard('E-7') && !guard('F-5'), 'guard does not exclude normal codes');
} catch (err) {
  ok(false, `F-4 guard is executable: ${err.message}`);
}
// F-4 keeps its dedicated route guide.
ok(indexHtml.includes('assets/js/f4-route-guide.js') && indexHtml.includes('id="f4RouteGuide"'),
  'F-4 dedicated route guide wiring intact');

console.log(`\n[check_visa_issuance_ui] ${checks} checks, ${failures} failures (covered ${nonF4} non-F-4 records)`);
if (failures) {
  for (const f of failed) console.error(` - FAIL ${f}`);
  process.exit(1);
}
console.log('[check_visa_issuance_ui] ALL PASS');
