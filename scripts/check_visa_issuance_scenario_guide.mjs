#!/usr/bin/env node
/*
 * Regression contract for the 사증발급 시나리오 안내 팝업 (visa-issuance
 * scenario-guide popup) and the E-8/E-9/E-10 source-grounded enrichment.
 *
 * Verifies:
 *   A. E-8/E-9/E-10 issuance records are scenario guides with >= 2 source-backed
 *      modes, each carrying a friendly icon + choice title + steps + page refs.
 *   B. The first mode of each is render-contract complete (>= 1 common document).
 *   C. The E-9 "wrong required documents" fix: the mis-mapped STUDENT document
 *      (doc_enroll / 표준입학허가서·재학/수료증명서) is gone from E-9's initial/new
 *      doc fields in BOTH protected files, replaced by the EPS core doc (doc_eps /
 *      고용허가서), and no E-9 issuance text mentions a student document.
 *   D. index.html wires the popup (render fn, modal, dispatcher, gating) and the
 *      issuance-guide i18n keys exist in ko/en/zh-CN.
 *
 * Pure Node — no DOM, no deps. Run: node scripts/check_visa_issuance_scenario_guide.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
const readText = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

let checks = 0, failures = 0;
const failed = [];
const ok = (cond, label) => { checks += 1; if (!cond) { failures += 1; failed.push(label); } };

const GUIDE_CODES = ['E-8', 'E-9', 'E-10'];
const issuance = readJson('data/visa_issuance_records.json');
const records = Array.isArray(issuance.records) ? issuance.records : [];
const byCode = new Map(records.map((r) => [r.code, r]));

const hasPageRef = (s) => s && (s.sourceUrl || s.url || (Number.isInteger(s.pageStart) && Number.isInteger(s.pageEnd)));

// --- A/B. Scenario-guide records ------------------------------------------
for (const code of GUIDE_CODES) {
  const rec = byCode.get(code);
  ok(!!rec, `${code}: issuance record exists`);
  if (!rec) continue;
  ok(rec.scenarioGuide === true, `${code}: scenarioGuide flag is true`);
  ok(!!(rec.scenarioQuestionKo && rec.scenarioQuestionEn), `${code}: has a Ko/En scenario question`);
  const modes = Array.isArray(rec.issuanceModes) ? rec.issuanceModes : [];
  ok(modes.length >= 2, `${code}: has >= 2 issuance modes (got ${modes.length})`);
  const ids = new Set();
  modes.forEach((m, i) => {
    ok(!!m.id && !ids.has(m.id), `${code} mode#${i}: has a unique id`);
    if (m.id) ids.add(m.id);
    ok(!!(m.icon && String(m.icon).trim()), `${code} mode#${i}: has a friendly icon`);
    ok(!!(m.choiceTitleKo && m.choiceTitleEn), `${code} mode#${i}: has Ko/En choice title`);
    ok(!!(m.labelKo && m.labelEn), `${code} mode#${i}: has Ko/En label`);
    ok(Array.isArray(m.steps) && m.steps.length > 0 && m.steps.every((s) => String(s.ko || '').trim()),
      `${code} mode#${i}: has a Korean step list`);
    const d = m.documents || {};
    ok(['common', 'additional', 'conditional'].every((g) => Array.isArray(d[g])),
      `${code} mode#${i}: documents expose common/additional/conditional arrays`);
    ok(Array.isArray(m.sourceRefs) && m.sourceRefs.some(hasPageRef),
      `${code} mode#${i}: has source refs with page/url`);
  });
  ok((modes[0]?.documents?.common || []).length >= 1, `${code}: first mode lists >= 1 common document`);
}

// --- C. E-9 wrong-document fix in BOTH protected files ---------------------
const STUDENT_DOC_ID = 'doc_enroll';
const STUDENT_DOC_TEXT = '표준입학허가서';
for (const rel of ['visa_data.json', 'backend/data/visas.json']) {
  const arr = readJson(rel);
  const e9 = arr.find((r) => r && r.code === 'E-9');
  ok(!!e9, `${rel}: E-9 record exists`);
  if (!e9) continue;
  for (const field of ['initialReqDocs', 'newReqDocs']) {
    const list = Array.isArray(e9[field]) ? e9[field] : [];
    ok(!list.includes(STUDENT_DOC_ID), `${rel}: E-9 ${field} no longer includes the student doc id`);
    ok(list.includes('doc_eps'), `${rel}: E-9 ${field} includes the EPS core doc (doc_eps)`);
  }
  const docInitTxt = JSON.stringify(e9.documents_initial || []);
  ok(!docInitTxt.includes(STUDENT_DOC_TEXT), `${rel}: E-9 documents_initial no longer mentions the student admission/enrollment doc`);
  ok(docInitTxt.includes('고용허가서'), `${rel}: E-9 documents_initial includes 고용허가서`);
}
// No E-9 issuance text should mention a student admission/enrollment document.
const e9Issuance = JSON.stringify(byCode.get('E-9') || {});
ok(!e9Issuance.includes(STUDENT_DOC_TEXT) && !e9Issuance.includes('재학증명'),
  'E-9 issuance content does not mention a student admission/enrollment document');

// --- D. index.html wiring + i18n ------------------------------------------
const indexHtml = readText('index.html');
for (const fn of ['renderIssuanceScenarioPicker', 'openIssuanceGuide', 'chooseIssuanceMode', 'applyIssuanceModeSelection', 'clearIssuanceGuide']) {
  ok(indexHtml.includes(`function ${fn}`), `index.html defines ${fn}`);
}
ok(indexHtml.includes('id="issuanceGuideOverlay"'), 'index.html has the #issuanceGuideOverlay modal');
ok(indexHtml.includes('id="issuanceGuideChoices"'), 'index.html has the issuance guide choices host');
for (const action of ['open-issuance-guide', 'choose-issuance-mode', 'close-issuance-guide', 'clear-issuance-guide']) {
  ok(indexHtml.includes(`'${action}'`), `index.html dispatcher wires "${action}"`);
}
ok(/issuance-needs-pick[\s\S]*?issuance-mode-card-wrap/.test(indexHtml) || indexHtml.includes('issuance-mode-card-wrap'),
  'index.html renders gated issuance mode card wraps');
ok(/\.issuance-needs-pick\.has-selection \.issuance-mode-card-wrap\.is-selected/.test(indexHtml),
  'index.html CSS reveals only the selected scenario card');

const GUIDE_I18N_KEYS = ['issuanceGuideTrigger', 'issuanceGuideClear', 'issuanceGuideEmptyHint',
  'issuanceGuideModalCopy', 'issuanceGuideModalTitle', 'issuanceGuideQuestionFallback'];
for (const loc of ['ko', 'en', 'zh-CN']) {
  const pack = readJson(`data/i18n/${loc}.json`);
  for (const k of GUIDE_I18N_KEYS) {
    ok(typeof pack[k] === 'string' && pack[k].trim(), `data/i18n/${loc}.json has ${k}`);
  }
}

console.log(`\n[check_visa_issuance_scenario_guide] ${checks} checks, ${failures} failures`);
if (failures) {
  for (const f of failed) console.error(` - FAIL ${f}`);
  process.exit(1);
}
console.log('[check_visa_issuance_scenario_guide] ALL PASS');
