#!/usr/bin/env node
/*
 * Static rendering-contract checks for index.html visa result cards.
 *
 * These checks intentionally avoid screenshot baselines. They assert the
 * all-status procedure-tab contract that should hold regardless of visa code:
 * source-confirmed structured requirements are consumed by the selected
 * procedure tab, duplicate post-tab blocks are not mounted, placeholder
 * document rows stay hidden, and raw diagnostics are not rendered in cards.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const INDEX = path.join(ROOT, 'index.html');
const VISA_DATA = path.join(ROOT, 'visa_data.json');
const BACKEND_VISAS = path.join(ROOT, 'backend', 'data', 'visas.json');
const STRUCTURED = path.join(ROOT, 'backend', 'data', 'manual_grounding', 'structured_requirements_2026_06_01.json');

const failures = [];
function check(condition, message) {
  if (!condition) failures.push(message);
}

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function readJson(file) {
  return JSON.parse(read(file));
}

function extractFunction(src, name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(', 'g');
  const m = re.exec(src);
  if (!m) return '';
  const braceStart = src.indexOf('{', re.lastIndex);
  if (braceStart < 0) return '';
  let depth = 0;
  for (let i = braceStart; i < src.length; i++) {
    const ch = src[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return src.slice(m.index, i + 1);
    }
  }
  return '';
}

const html = read(INDEX);
const renderResults = extractFunction(html, 'renderResults');
const getProcedure = extractFunction(html, 'getProcedure');
const insertFeeNotice = extractFunction(html, 'insertFeeNotice');

check(Boolean(renderResults), 'renderResults() not found');
check(Boolean(getProcedure), 'getProcedure() not found');
check(Boolean(insertFeeNotice), 'insertFeeNotice() not found');

check(
  /getSourceConfirmedEntriesForProcedure\(v,\s*cfg\.key\)/.test(getProcedure),
  'getProcedure() must consume source-confirmed structured entries by procedure key'
);
check(
  /mergeDocGroups\(structuredDocs,\s*rawDocs,\s*legacyDocs\)/.test(getProcedure),
  'getProcedure() must merge structured docs before raw/legacy fallback docs'
);
check(
  /sourceConfirmed:\s*hasAnyDocs\(structuredDocs\)/.test(getProcedure),
  'procedure source-confirmed flag missing'
);
check(
  !/renderSourceConfirmedRequirements\(v\)/.test(renderResults),
  'renderResults() must not mount duplicate source-confirmed requirements block'
);
check(
  !/renderDeadlineCalculator\(v,\s*isVisaCode\)/.test(renderResults),
  'renderResults() must not mount the global deadline calculator for every card'
);
check(
  /function\s+insertFeeNotice[\s\S]{0,180}return;/.test(insertFeeNotice),
  'legacy fee shim must not inject duplicate fee notices'
);
check(
  /SOURCE_CONFIRMED_PROCEDURE_KEY_MAP/.test(html)
    && /registration:\s*'registration'/.test(html)
    && /extension:\s*'extension'/.test(html)
    && /visa_issuance:\s*'visaIssuance'/.test(html),
  'source-confirmed procedure type map must cover registration, extension, and visa issuance'
);
check(
  /procedureKeyForSourceConfirmedType/.test(html)
    && /groupSourceConfirmedDocuments/.test(html)
    && /renderProcedureHeader/.test(html),
  'procedure source-confirmed helper/render functions missing'
);
check(
  /통합신청서\(별지 제34호 서식\)/.test(html),
  'domestic procedure application form canonical label must be preserved'
);
check(
  /const\s+summarySubs\s*=\s*activeSubs\.length\s*\?\s*activeSubs\s*:\s*subs;/.test(html),
  'broad subcode summaries must fall back to review-gated subcode names instead of rendering an empty name list'
);
check(
  /매뉴얼\\s\*참조\\s\*코드\|manual\\s\*review\\s\*code/.test(html),
  'broad subcode summaries must suppress placeholder-like manual-review subcode labels'
);

const visaDataText = read(VISA_DATA);
const backendVisasText = read(BACKEND_VISAS);
for (const [label, text] of [['visa_data.json', visaDataText], ['backend/data/visas.json', backendVisasText]]) {
  check(!text.includes('문서명 미상'), `${label} must not contain placeholder document name rows`);
  check(!text.includes('비고 정보 없음'), `${label} must not contain placeholder note rows`);
}

const visas = readJson(VISA_DATA);
const supported = new Map((Array.isArray(visas) ? visas : []).map(v => [String(v.code || '').toUpperCase(), v]));
for (const code of ['D-2', 'H-1', 'E-7', 'F-6', 'G-1', 'F-4', 'H-2', 'C-3']) {
  check(supported.has(code), `representative status ${code} missing from visa_data.json`);
}
const g1 = supported.get('G-1') || {};
const g1Subcodes = JSON.stringify(g1.subCodes || g1.subcodes || g1.subTypes || g1.types || []);
check(g1Subcodes.includes('G-1-5'), 'G-1-5 sub-code must remain present in committed data');

const structured = readJson(STRUCTURED);
const entries = Array.isArray(structured.entries) ? structured.entries : [];
const d2Registration = entries.find(entry =>
  entry.statusCode === 'D-2'
  && entry.procedureType === 'registration'
  && entry.confidence === 'HIGH'
  && entry.readinessLabel === 'STRUCTURED_EVIDENCE_READY'
);
check(Boolean(d2Registration), 'D-2 registration fixture source-confirmed entry missing');
if (d2Registration) {
  const docs = (d2Registration.documents || []).map(doc => String(doc.textKo || ''));
  check(docs.some(text => text.includes('신청서')), 'source-confirmed D-2 registration documents must include the official application-form line');
  check(docs.some(text => text.includes('체류지 입증서류')), 'source-confirmed D-2 registration documents must include residence proof');
}

const rawCardDiagnostics = [
  'bad_response',
  'planned_not_wired',
  'manual: attempted',
  'escaped raw newline dumps',
];
for (const marker of rawCardDiagnostics) {
  check(!renderResults.includes(marker), `renderResults() must not render raw diagnostic marker: ${marker}`);
}

if (failures.length) {
  console.error('[check_static_visa_result_cards] failed');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('[check_static_visa_result_cards] OK');
