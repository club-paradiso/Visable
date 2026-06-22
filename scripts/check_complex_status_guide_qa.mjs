#!/usr/bin/env node
/**
 * check_complex_status_guide_qa.mjs — cross-status QA regression guard for the
 * complex status guide system (F-4 + F-6/G-1/E-7/F-5/D-2/D-4).
 *
 * Real-browser automation is not available in CI (no browser binary; the repo
 * runs only `bash scripts/check_repo.sh`), so this is the offline stand-in: it
 * loads the REAL guide modules (the same code the browser runs) and exercises
 * their pure render/result functions across all seven statuses, in BOTH Korean
 * and English, asserting the QA contract that future PRs must not silently break:
 *   - recommended-start block + the document-checklist primary CTA copy
 *   - secondary actions grouped + demoted under "다른 방식으로 보기"
 *   - one-question-per-step flow with an "I am not sure" path
 *   - checklist-first result section labels
 *   - full-screen / wide overlay (never a tiny modal) + a11y attributes
 *   - source-safety: no overconfident wording; "공식근거 확인 필요" present
 *   - theme-token CSS (civic_editorial / archive_diary safe)
 *   - F-4 regression (new CTA copy; old copy gone)
 *   - index.html / visa-route-guide CTA-suppression wiring for all seven
 *
 * The companion real-browser Playwright suite (tests/e2e/) covers actual
 * rendering / viewport / focus and is run manually in a browser-capable env.
 *
 * Run: node scripts/check_complex_status_guide_qa.mjs
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

/* ----------------------------------------------------------- load modules */
global.window = {};
global.currentLanguage = 'ko';
const RG = require('../assets/js/visa-route-guide.js');
global.window.ParadisoRoute = RG;
const visas = readJson('visa_data.json');
global.VISA_DATA = visas;
require('../assets/js/complex-status-guide.js');
const CSG = globalThis.ParadisoStatusGuide;
require('../assets/js/f4-route-guide.js');
const F4 = globalThis.ParadisoF4Guide;

// F-4 reads its data from data/f4/* (the browser fetches these); wire them in.
const f4data = {
  base: readJson('data/f4/base.json'),
  diagnostic: readJson('data/f4/diagnostic.json'),
  faq: readJson('data/f4/faq.json'),
  countries: readJson('data/f4/countries.json'),
  overlays: readJson('data/f4/country_overlays.json'),
  sources: readJson('data/f4/sources.json')
};
F4._state.data = f4data;
F4._state.flowAnswers = { confirmations: [] };
const docMaster = CSG.buildDocMasterMap(readJson('doc_master.json'));
const byCode = (c) => visas.find((v) => v.code === c);

const f4Src = read('assets/js/f4-route-guide.js');
const csgSrc = read('assets/js/complex-status-guide.js');
const indexHtml = read('index.html');
const STATUSES = ['F-4', 'F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];
const SIX = ['F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];

function setLang(l) { global.currentLanguage = l; }
function blockHtml(code) { return code === 'F-4' ? F4.recStartBlockHtml(f4data) : CSG.recStartBlockHtml(code); }
function unsureLabel() { return CSG.S('optUnsure'); }
const SECTIONS = {
  ko: ['먼저 해야 할 일', '기본 준비서류', '내 상황에서 추가될 수 있는 서류', '신청 절차', '공식 근거', '다음 행동'],
  en: ['First steps', 'Basic required documents', 'Documents that may be added for your situation', 'Procedure', 'Official sources', 'Next actions']
};
// Section labels live in F-4's STR pack (resAdditionalDocs) and CSG's S() (resAddDocs).
function sectionValues(code) {
  if (code === 'F-4') return [F4.STR.resFirstSteps, F4.STR.resBasicDocs, F4.STR.resAdditionalDocs, F4.STR.resProcedure, F4.STR.resSources, F4.STR.resNextActions];
  return [CSG.S('resFirstSteps'), CSG.S('resBasicDocs'), CSG.S('resAddDocs'), CSG.S('resProcedure'), CSG.S('resSources'), CSG.S('resNextActions')];
}

/* ----------------------------------- 1. recommended-start block + CTA (KO/EN) */
for (const lang of ['ko', 'en']) {
  setLang(lang);
  section(`Recommended-start block + dominant CTA (${lang})`);
  const recTitle = lang === 'en' ? 'Recommended starting point' : '추천 시작점';
  const secLabel = lang === 'en' ? 'Other ways to view this status' : '다른 방식으로 보기';
  for (const code of STATUSES) {
    const html = blockHtml(code);
    ok(typeof html === 'string' && html.length > 0 && !/undefined/.test(html), `${code} (${lang}): block renders, no undefined`);
    ok(html.includes(recTitle), `${code} (${lang}): shows "${recTitle}"`);
    const cta = lang === 'en' ? ('Find My ' + code + ' Document Checklist') : ('내 상황에 맞는 ' + code + ' 준비서류 찾기');
    ok(html.includes(cta), `${code} (${lang}): primary CTA "${cta}"`);
    ok(html.includes(secLabel), `${code} (${lang}): secondary actions under "${secLabel}"`);
    // primary CTA precedes the demoted secondary group (hierarchy)
    const iCta = Math.max(html.indexOf('primary-cta'), html.indexOf(cta));
    ok(iCta !== -1 && iCta < html.indexOf(secLabel), `${code} (${lang}): primary CTA precedes secondary actions`);
  }
}
setLang('ko');

/* ----------------------------------- 2. one-question-per-step + "I am not sure" */
for (const lang of ['ko', 'en']) {
  setLang(lang);
  section(`Flow: one question per step + "I am not sure" (${lang})`);
  // F-4: 5-step flow, each renders a question + the unsure option.
  F4._state.flowAnswers = { confirmations: [] };
  ok(Array.isArray(F4.F4_STEPS) && F4.F4_STEPS.length >= 4, `F-4 (${lang}): multi-step flow (${F4.F4_STEPS.length} steps)`);
  let f4UnsureSteps = 0;
  F4.F4_STEPS.forEach(function (s) { const h = F4.renderStepHtml(s); if (h.includes(F4.STR.optUnsure)) f4UnsureSteps++; });
  ok(f4UnsureSteps >= 4, `F-4 (${lang}): "${F4.STR.optUnsure}" offered on the single-select steps`);
  // The six: subcode + procedure steps; each single-select step offers unsure.
  for (const code of SIX) {
    const steps = CSG.buildSteps(RG.buildGuidanceModel(byCode(code)));
    ok(steps.length >= 1 && steps.every((s) => s.options && s.options.length >= 2), `${code} (${lang}): each step has a question with options`);
    ok(steps.every((s) => s.options.some((o) => o.label === unsureLabel())), `${code} (${lang}): every step offers "${unsureLabel()}"`);
  }
}
setLang('ko');

/* ----------------------------------- 3. checklist-first result section labels */
for (const lang of ['ko', 'en']) {
  setLang(lang);
  section(`Checklist-first result section labels (${lang})`);
  for (const code of STATUSES) {
    const vals = sectionValues(code);
    const want = SECTIONS[lang];
    ok(want.every((w) => vals.indexOf(w) !== -1), `${code} (${lang}): all 6 result section labels present`, vals.join(' | '));
  }
}
setLang('ko');

/* ----------------------------------- 4. result content (checklist-first, safe) */
section('Result models build with content (no undefined)');
for (const code of SIX) {
  const m = RG.buildGuidanceModel(byCode(code));
  const steps = CSG.buildSteps(m);
  const proc = steps.find((s) => s.id === 'procedure');
  const sub = steps.find((s) => s.id === 'subcode');
  const rm = CSG.buildResultModel(code, m, { subcode: sub ? sub.options[0].id : 'unsure', procedure: proc.options[0].id }, { record: byCode(code), docMaster });
  ok(rm.firstSteps.length > 0 && rm.procSteps.length >= 5, `${code}: result has first steps + procedure steps`);
  ok(Array.isArray(rm.sourceRefs), `${code}: result exposes a sourceRefs array (empty → needs-confirmation)`);
  const text = CSG.checklistText(code, rm);
  ok(typeof text === 'string' && !/undefined/.test(text), `${code}: copy-checklist text has no undefined`);
}
// Manual references DO render for procedures that have them — `extension` exists
// with manualRefs for all six (procedures the data lacks → "공식근거 확인 필요", safe).
for (const code of SIX) {
  const rmExt = CSG.buildResultModel(code, RG.buildGuidanceModel(byCode(code)), { subcode: 'unsure', procedure: 'extension' }, { record: byCode(code), docMaster });
  ok(rmExt.sourceRefs.length > 0 && rmExt.sourceRefs.every((r) => r.name), `${code}: extension result shows source-backed manual references`);
}
// F-4 result model
const f4rm = F4.buildResultModel({ situation: 'apply_abroad', nationality: 'not_applicable', location: 'outside_korea', procedure: 'visa_issuance', confirmations: [] });
ok(f4rm && Array.isArray(f4rm.firstSteps) && f4rm.firstSteps.length > 0, 'F-4: result model builds with first steps');
ok(!/undefined/.test(F4.buildChecklistText(f4rm)), 'F-4: copy-checklist text has no undefined');

/* ----------------------------------- 5. source safety (no overconfident wording) */
section('Source safety — no overconfident claims; needs-confirmation present');
const BANNED = ['you are eligible', 'you will be approved', 'always required', 'definitely required', 'must be approved',
  'guarantees approval', 'guaranteed approval',
  '반드시 발급', '무조건 가능', '승인됩니다', '항상 필요', '반드시 승인', '자격이 확정', '보장합니다'];
// Collect user-facing rendered strings across all statuses + both languages.
let corpus = '';
for (const lang of ['ko', 'en']) {
  setLang(lang);
  for (const code of STATUSES) corpus += '\n' + blockHtml(code);
  for (const code of SIX) {
    const m = RG.buildGuidanceModel(byCode(code));
    const steps = CSG.buildSteps(m);
    steps.forEach((s) => s.options.forEach((o) => { corpus += '\n' + o.label; }));
    const proc = steps.find((s) => s.id === 'procedure');
    const rm = CSG.buildResultModel(code, m, { subcode: 'unsure', procedure: proc.options[0].id }, { record: byCode(code), docMaster });
    corpus += '\n' + CSG.checklistText(code, rm) + '\n' + (rm.noteKey ? CSG.S(rm.noteKey) : '');
  }
  corpus += '\n' + sectionValues('F-6').join('\n');
}
setLang('ko');
const lc = corpus.toLowerCase();
for (const phrase of BANNED) ok(lc.indexOf(phrase.toLowerCase()) === -1, `no overconfident phrase in user-facing strings: "${phrase}"`);
// Needs-confirmation wording is available in both modules (both languages).
setLang('ko'); ok(CSG.S('officialSourceNeedsConfirm') === '공식근거 확인 필요', 'CSG: "공식근거 확인 필요" (ko)');
setLang('en'); ok(CSG.S('officialSourceNeedsConfirm') === 'Official source needs confirmation', 'CSG: "Official source needs confirmation" (en)');
setLang('ko');
ok(/공식근거 확인 필요/.test(csgSrc) && /Official source needs confirmation/.test(csgSrc), 'CSG source carries needs-confirmation (ko+en)');
ok(/공식근거 확인 필요|공식근거 확인/.test(f4Src) || /officialSourceNeedsConfirm/.test(f4Src), 'F-4 source carries needs-confirmation wording');
// F-4 keeps explicit no-guarantee wording.
ok(/보장하지\s*않/.test(f4Src) && /does not guarantee/.test(f4Src), 'F-4 keeps explicit "does not guarantee" wording');

/* ----------------------------------- 6. full-screen / wide overlay (not tiny) */
section('Full-screen / wide overlay (not a tiny modal) + mobile full-screen');
ok(/min\(960px/.test(f4Src) && /@media \(max-width:640px\)/.test(f4Src) && /height:100%/.test(f4Src), 'F-4 overlay: wide desktop + full-screen mobile');
ok(/min\(900px/.test(csgSrc) && /@media \(max-width:640px\)/.test(csgSrc) && /height:100%/.test(csgSrc), 'CSG overlay: wide desktop + full-screen mobile');

/* ----------------------------------- 7. accessibility attributes */
section('Accessibility attributes (dialog / focus trap / radios / progress)');
for (const [name, src] of [['F-4', f4Src], ['CSG', csgSrc]]) {
  ok(/aria-modal/.test(src) && /'role', 'dialog'|role="dialog"/.test(src), `${name}: role=dialog + aria-modal`);
  ok(/Escape/.test(src) && /shiftKey/.test(src) && /lastFocus/.test(src), `${name}: ESC + Tab focus-trap + focus restore`);
  ok((/role="radiogroup"/.test(src) || /'radiogroup'/.test(src)) && (/role="radio"/.test(src) || /'radio'/.test(src)) && /aria-checked/.test(src), `${name}: keyboard radio options`);
  ok(/role="progressbar"/.test(src) && /aria-valuenow/.test(src), `${name}: progressbar exposed to AT`);
  ok(/aria-label="' \+ esc\(/.test(src) || /aria-label="' \+ esc\(S\(/.test(src) || /aria-label/.test(src), `${name}: controls carry accessible names`);
}

/* ----------------------------------- 8. theme-token CSS (both themes safe) */
section('Theme-token CSS (civic_editorial / archive_diary safe)');
for (const [name, src] of [['F-4', f4Src], ['CSG', csgSrc]]) {
  ok(/var\(--bg1/.test(src) && /var\(--ac/.test(src) && /var\(--t1/.test(src) && /var\(--bd/.test(src),
    `${name}: surfaces use theme tokens (--bg1/--ac/--t1/--bd)`);
}

/* ----------------------------------- 9. F-4 regression */
section('F-4 regression (reference implementation)');
setLang('ko'); ok(F4.recStartBlockHtml(f4data).includes('내 상황에 맞는 F-4 준비서류 찾기'), 'F-4: KO CTA is the document-checklist copy');
setLang('en'); ok(F4.recStartBlockHtml(f4data).includes('Find My F-4 Document Checklist'), 'F-4: EN CTA is the document-checklist copy');
setLang('ko');
ok(!f4Src.includes('내 F-4 준비경로 확인하기') && !f4Src.includes('Check My F-4 Preparation Path'), 'F-4: old "preparation path" CTA copy removed');
ok(/external-guide-slot\[data-guide-slot="F-4"\]/.test(f4Src), 'F-4: recommended-start block promoted to the top of the card');

/* ----------------------------------- 10. CTA-suppression wiring (all seven) */
section('No competing CTAs for the seven (index.html + visa-route-guide)');
ok(/COMPLEX_GUIDE_MIGRATED = \[[^\]]*'F-4'[^\]]*'F-6'[^\]]*'G-1'[^\]]*'E-7'[^\]]*'F-5'[^\]]*'D-2'[^\]]*'D-4'/.test(indexHtml),
  'index.html: legacy route-wizard suppressed for all seven');
ok(/COMPLEX_GUIDE_OWNED = \[[^\]]*'F-4'[^\]]*'F-6'[^\]]*'G-1'[^\]]*'E-7'[^\]]*'F-5'[^\]]*'D-2'[^\]]*'D-4'/.test(read('assets/js/visa-route-guide.js')),
  'visa-route-guide: generic in-card CTA suppressed for all seven');
ok(/<script defer src="assets\/js\/complex-status-guide\.js"><\/script>/.test(indexHtml) && /<script defer src="assets\/js\/f4-route-guide\.js"><\/script>/.test(indexHtml),
  'index.html loads both guide modules');

/* ----------------------------------- 11. source-backed docs regression (#460) */
section('Source-backed document checklist (regression for #460)');
setLang('ko');
const f6 = CSG.buildResultModel('F-6', RG.buildGuidanceModel(byCode('F-6')), { subcode: 'unsure', procedure: 'visa_issuance' }, { record: byCode('F-6'), docMaster });
ok(f6.basicDocs.length >= 5 && f6.basicDocs.every((d) => /^doc_/.test(d.id)), 'F-6 visa issuance: resolvable doc_master checklist (Level A path)');
let leaked = 0;
for (const code of SIX) {
  const m = RG.buildGuidanceModel(byCode(code));
  for (const o of CSG.buildSteps(m).find((s) => s.id === 'procedure').options) {
    if (o.id === 'unsure') continue;
    const rm = CSG.buildResultModel(code, m, { subcode: 'unsure', procedure: o.id }, { record: byCode(code), docMaster });
    rm.basicDocs.concat(rm.sitDocs).forEach((d) => { if (!/^doc_/.test(d.id)) leaked++; });
  }
}
ok(leaked === 0, 'no prose ever leaks into a rendered document checklist (all six)');

/* ----------------------------------- 12. safe result for EVERY procedure (incl.
 * procedures the data lacks, e.g. G-1/E-7/D-4 visa_issuance — the adapter reports
 * them available but visa_data has no entry). Every such result must stay safe:
 * no undefined, no overconfident wording, no prose leak, and a fully-empty
 * procedure must still produce a non-empty needs-confirmation result (never an
 * empty card or a fabricated source). This locks the post-merge audited state. */
section('Every available procedure yields a safe result (no empty/broken/overconfident)');
let unsafe = 0, emptyProcChecked = 0;
for (const lang of ['ko', 'en']) {
  setLang(lang);
  const needsConfirm = CSG.S('officialSourceNeedsConfirm');
  const safetyNote = CSG.S('safetyNote');
  for (const code of SIX) {
    const m = RG.buildGuidanceModel(byCode(code));
    for (const o of CSG.buildSteps(m).find((s) => s.id === 'procedure').options) {
      if (o.id === 'unsure') continue;
      const rm = CSG.buildResultModel(code, m, { subcode: 'unsure', procedure: o.id }, { record: byCode(code), docMaster });
      const text = CSG.checklistText(code, rm);
      let bad = '';
      if (/undefined/.test(text)) bad = 'undefined';
      else if (rm.basicDocs.concat(rm.sitDocs).some((d) => !/^doc_/.test(d.id))) bad = 'prose-leak';
      else if (BANNED.some((b) => text.toLowerCase().includes(b.toLowerCase()))) bad = 'overconfident';
      else if (!Array.isArray(rm.sourceRefs)) bad = 'sourceRefs-not-array';
      if (bad) { unsafe++; ok(false, `${code}/${o.id} (${lang}) safe result`, bad); }
      // Fully-empty procedure (no docs, no source refs) → still a safe,
      // non-empty needs-confirmation result with the safety note.
      if (rm.basicDocs.length === 0 && rm.sitDocs.length === 0 && rm.sourceRefs.length === 0) {
        emptyProcChecked++;
        const okEmpty = text.length > 0 && text.includes(needsConfirm) && text.includes(safetyNote);
        if (!okEmpty) { unsafe++; ok(false, `${code}/${o.id} (${lang}) empty procedure → safe needs-confirmation result`); }
      }
    }
  }
}
setLang('ko');
ok(unsafe === 0, 'every status × every available procedure renders a safe result (KO+EN)');
ok(emptyProcChecked > 0, 'data-less procedures exercised → confirmed they degrade to a safe needs-confirmation result', String(emptyProcChecked));

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_complex_status_guide_qa: ALL PASS');
