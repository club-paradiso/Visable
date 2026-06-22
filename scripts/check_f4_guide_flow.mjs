#!/usr/bin/env node
/**
 * check_f4_guide_flow.mjs — offline end-to-end verification of the unified F-4
 * complex-status guide FLOW (assets/js/f4-route-guide.js).
 *
 * No DOM/browser is available offline, so instead of a screenshot test this
 * loads the module's REAL pure functions (the same code the browser runs):
 *   - F4_STEPS / renderStepHtml  → the one-question-per-step flow
 *   - buildResultModel           → answers → checklist-first result model
 *   - buildChecklistText         → the "Copy checklist" payload
 * and drives them against the REAL data/f4/*.json so every flow path produces a
 * complete, source-grounded, non-undefined result (no empty cards, no invented
 * documents, uncertain items flagged).
 *
 * Run: node scripts/check_f4_guide_flow.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const readJson = (p) => JSON.parse(read(p));
const require = createRequire(import.meta.url);

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

// The module is an IIFE that publishes its API on globalThis and early-returns
// the DOM integration when `document` is undefined (Node). Requiring it runs it.
require('../assets/js/f4-route-guide.js');
const F4 = globalThis.ParadisoF4Guide;

section('Module API surface');
ok(F4 && typeof F4.buildResultModel === 'function', 'buildResultModel exposed');
ok(F4 && typeof F4.renderStepHtml === 'function', 'renderStepHtml exposed');
ok(F4 && Array.isArray(F4.F4_STEPS) && F4.F4_STEPS.length === 5, 'F4_STEPS has 5 steps (one question per step)');
ok(globalThis.ParadisoComplexGuide && typeof globalThis.ParadisoComplexGuide.register === 'function',
  'reusable ParadisoComplexGuide engine registered');
ok(globalThis.ParadisoComplexGuide && globalThis.ParadisoComplexGuide.has('F-4'),
  'F-4 registered with the engine');

// Wire the real data into the module state (what loadAll() does in the browser).
const data = {
  base: readJson('data/f4/base.json'),
  diagnostic: readJson('data/f4/diagnostic.json'),
  faq: readJson('data/f4/faq.json'),
  countries: readJson('data/f4/countries.json'),
  overlays: readJson('data/f4/country_overlays.json'),
  sources: readJson('data/f4/sources.json')
};
F4._state.data = data;
const srcIds = new Set((data.sources.sources || []).map((s) => s.id));

/* ------------------------- recommended-start block (CTA discoverability) */
section('Recommended-start block — dominant CTA, correct hierarchy');
ok(typeof F4.recStartBlockHtml === 'function', 'recStartBlockHtml exposed');
const rec = F4.recStartBlockHtml(data);
ok(typeof rec === 'string' && rec.length > 0 && !/undefined/.test(rec), 'block renders with no undefined');
ok(rec.includes('추천 시작점'), 'block shows the recommended-start title');
ok(rec.includes('세부코드를 몰라도'), 'block body reassures users who do not know their subcategory');
ok(rec.includes('내 상황에 맞는 F-4 준비서류 찾기'), 'block shows the document-checklist-focused primary CTA');
ok(rec.includes('약 1분'), 'block shows the supporting microcopy (time / question count)');
// Hierarchy: the primary CTA must appear BEFORE the secondary actions, and the
// secondary actions must still be present (demoted, not removed).
const iPrimary = rec.indexOf('f4g-primary-cta');
const iSecondary = rec.indexOf('다른 방식으로 보기');
ok(iPrimary !== -1 && iSecondary !== -1 && iPrimary < iSecondary,
  'primary CTA precedes the demoted secondary actions');
for (const s of ['전체 세부자격 보기', '공통서류 보기', '신청 절차 보기', '공식 근거 보기']) {
  ok(rec.includes(s), `secondary action still available: ${s}`);
}
// Exactly one labelled heading id for the F-4 guide region (a11y / uniqueness).
ok((rec.match(/id="f4RouteGuideTitle"/g) || []).length === 1, 'block exposes a single labelled title id');

/* ----------------------------------------- one-question-per-step rendering */
section('Flow steps (one question per step + "I am not sure")');
const EXPECT_Q = {
  situation: '현재 어떤 상황에 가까우신가요?',
  nationality: '본인 또는 가족의 대한민국 국적 이력이 있나요?',
  location: '현재 어디에 있나요?',
  procedure: '지금 필요한 절차는 무엇인가요?'
};
for (const step of F4.F4_STEPS) {
  F4._state.flowAnswers = { confirmations: [] };
  const html = F4.renderStepHtml(step);
  ok(typeof html === 'string' && html.length > 0 && !/undefined/.test(html), `step "${step.id}" renders non-empty HTML with no undefined`);
  if (EXPECT_Q[step.id]) ok(html.includes(EXPECT_Q[step.id]), `step "${step.id}" shows its question`, EXPECT_Q[step.id]);
  // every single-select step offers the "잘 모르겠어요" path
  if (step.type === 'single') ok(html.includes('잘 모르겠어요'), `step "${step.id}" offers "잘 모르겠어요"`);
  // option roles for a11y
  if (step.type === 'single') ok(/role="radio"/.test(html), `step "${step.id}" options are radios`);
  if (step.type === 'multi') ok(/role="checkbox"/.test(html), `step "${step.id}" options are checkboxes`);
}

/* ------------------------------------------ result model for every path */
section('Result model — checklist-first, source-grounded, nothing invented');
const SOURCE_BACKED = new Set(['overseas_application', 'status_change', 'residence_report']);
function checkModel(answers, expectRoute, label) {
  const m = F4.buildResultModel(answers);
  ok(m.routeId === expectRoute, `${label}: routeId = ${expectRoute}`, m.routeId);
  ok(!!m.labelKey, `${label}: has a cautious route label`);
  // procedure steps always present (source-backed or generic process list)
  ok(Array.isArray(m.procSteps) && m.procSteps.length > 0, `${label}: procedure step list is non-empty`);
  ok(m.procSteps.every((s) => typeof s === 'string' && s.trim() && !/undefined/.test(s)), `${label}: no undefined procedure step`);
  // sources resolve in sources.json (no fake citations)
  ok(Array.isArray(m.sourceRefs) && m.sourceRefs.length > 0, `${label}: has official source refs`);
  ok(m.sourceRefs.every((r) => srcIds.has(r)), `${label}: every source ref resolves in sources.json`, JSON.stringify(m.sourceRefs));
  // documents: source-backed routes list docs; others say "needs confirmation"
  if (SOURCE_BACKED.has(expectRoute)) {
    ok(m.basicDocs.length > 0 && m.basicDocs.every((d) => d && !/undefined/.test(d)), `${label}: basic documents are source-backed`);
  } else {
    ok(m.basicDocs.length === 0 && !!m.basicNote, `${label}: no invented docs — shows a "needs confirmation" note instead`);
  }
  // no empty card: first steps OR warnings OR a fallback note always render
  ok(m.firstSteps.length > 0 || m.warnings.length > 0 || expectRoute === 'extension' || expectRoute === 'official_check',
    `${label}: first-steps section is not empty`);
  return m;
}
checkModel({ procedure: 'visa_issuance' }, 'overseas_application', 'visa issuance');
checkModel({ procedure: 'change_of_status' }, 'status_change', 'change of status');
checkModel({ procedure: 'residence_registration' }, 'residence_report', 'residence registration');
checkModel({ procedure: 'extension' }, 'extension', 'extension');
checkModel({ situation: 'apply_abroad', procedure: 'not_sure' }, 'overseas_application', 'situation: apply abroad');
checkModel({ situation: 'not_sure', procedure: 'not_sure' }, 'official_check', 'all unsure');

/* ------------------------------ additional documents from Step-5 confirmations */
section('Situation-specific documents (Step 5) are source-backed or flagged');
const withConf = F4.buildResultModel({ procedure: 'visa_issuance', confirmations: ['criminal_record', 'military', 'family_proof'] });
ok(withConf.addItems.length === 3, 'selected confirmation items all surface');
const crim = withConf.addItems.find((i) => i.name && (i.name.includes('범죄') || /criminal/i.test(i.name)));
ok(crim && crim.sourceBacked && crim.note && crim.note.length > 0, 'criminal-record item carries a source-backed note');
const fam = withConf.addItems.find((i) => i.name && (i.name.includes('가족') || /family/i.test(i.name)));
ok(fam && fam.sourceBacked === false, 'family-relationship item is flagged for official confirmation (not invented)');
const none = F4.buildResultModel({ procedure: 'visa_issuance', confirmations: [] });
ok(none.addItems.length === 0, 'no confirmations selected → empty addItems (renderer shows a cautious note, not an empty card)');

/* ------------------------------ nationality safety caution surfaces */
section('Korean-nationality safety caution');
const unsureNat = F4.buildResultModel({ procedure: 'visa_issuance', nationality: 'not_sure' });
ok(!!unsureNat.natCaution && unsureNat.natCaution.length > 0, 'unsure nationality → caution surfaced');
const selfNat = F4.buildResultModel({ procedure: 'visa_issuance', nationality: 'self_held' });
ok(!!selfNat.natCaution, 'previously-held nationality → caution surfaced');
const naNat = F4.buildResultModel({ procedure: 'visa_issuance', nationality: 'not_applicable' });
ok(!naNat.natCaution, 'not-applicable nationality → no extra caution');

/* ------------------------------ copy-checklist payload */
section('Copy-checklist payload');
const m = F4.buildResultModel({ procedure: 'residence_registration', confirmations: ['apostille'] });
const text = F4.buildChecklistText(m);
ok(typeof text === 'string' && text.length > 0 && !/undefined/.test(text), 'checklist text builds with no undefined');
ok(text.includes('[ ] ') , 'checklist text contains checkbox doc lines');
ok(/추가서류가 요구될 수 있습니다/.test(text), 'checklist text carries the cautious safety note');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_f4_guide_flow: ALL PASS');
