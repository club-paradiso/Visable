#!/usr/bin/env node
/**
 * check_complex_status_guide.mjs — validation for the multi-status
 * ComplexStatusGuide (assets/js/complex-status-guide.js) covering F-6, G-1, E-7,
 * F-5, D-2, D-4.
 *
 * Offline, stdlib/Node-only. Loads the module's REAL pure functions and exercises
 * them against the real visa_data.json via the tested ParadisoRoute adapter, so:
 *  - every target status gets a recommended-start block + ONE dominant CTA with
 *    the document-checklist-focused copy, and demoted secondary actions;
 *  - flow options are source-backed only (active subcodes; available procedures);
 *    manual-review / reference-only placeholders and not_applicable procedures are
 *    never offered;
 *  - the result is checklist-first and NEVER invents documents — it hands off to
 *    the existing source-backed detail and marks uncertain items "공식근거 확인 필요";
 *  - index.html / visa-route-guide wiring suppresses the competing CTAs;
 *  - F-4 is untouched (not a target here).
 *
 * Run: node scripts/check_complex_status_guide.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const require = createRequire(import.meta.url);

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const RG = require('../assets/js/visa-route-guide.js');
global.window = { ParadisoRoute: RG };
global.currentLanguage = 'ko';
require('../assets/js/complex-status-guide.js');
const CSG = globalThis.ParadisoStatusGuide;

const visas = JSON.parse(read('visa_data.json'));
const byCode = (c) => visas.find((v) => v.code === c);
const engineSrc = read('assets/js/complex-status-guide.js');
const indexHtml = read('index.html');
const routeGuideSrc = read('assets/js/visa-route-guide.js');

const TARGETS = ['F-6', 'G-1', 'E-7', 'F-5', 'D-2', 'D-4'];

/* -------------------------------------------------------------- module API */
section('Module API');
ok(CSG && Array.isArray(CSG.TARGETS), 'ParadisoStatusGuide published');
ok(JSON.stringify(CSG.TARGETS) === JSON.stringify(TARGETS), 'targets are exactly F-6/G-1/E-7/F-5/D-2/D-4', (CSG.TARGETS || []).join(','));
ok(CSG.TARGETS.indexOf('F-4') === -1, 'F-4 is NOT a target (reference impl untouched)');
ok(['buildSteps', 'buildResultModel', 'recStartBlockHtml', 'checklistText', 'open', 'close'].every((f) => typeof CSG[f] === 'function'),
  'pure + control functions exposed');

/* ------------------------------------- never re-renders protected doc data */
section('Source safety (no protected doc rendering, handoff present)');
// Property-access only (e.g. rec.requiredDocs) — not UI ref-id string literals like 'commonDocs'.
ok(!/\.(requiredDocs|commonDocs|manualRefs|docs)\b/.test(engineSrc), 'engine never reads/renders raw document fields from records');
ok(/ParadisoRoute/.test(engineSrc) && /goToResult/.test(engineSrc), 'engine hands off to the source-backed detail (ParadisoRoute.goToResult)');
ok(/공식근거 확인 필요/.test(engineSrc) && /Official source needs confirmation/.test(engineSrc), 'uncertain items marked needing official confirmation (KO/EN)');
ok(!/KSCO|jobcode|job_code|industrycode/i.test(engineSrc), 'engine does not duplicate E-7 job/industry-code logic');

/* ------------------------------------------ full-screen / wide (not tiny) */
section('Full-screen / wide overlay + a11y (not a tiny modal)');
ok(/min\(900px/.test(engineSrc) && /@media \(max-width:640px\)/.test(engineSrc) && /height:100%/.test(engineSrc),
  'overlay is a wide sheet (desktop) / full-screen (mobile)');
ok(/aria-modal/.test(engineSrc) && /role', 'dialog'|role="dialog"|setAttribute\('role', 'dialog'\)/.test(engineSrc), 'overlay has role=dialog + aria-modal');
ok(/Escape/.test(engineSrc) && /shiftKey/.test(engineSrc) && /lastFocus/.test(engineSrc), 'ESC + Tab focus-trap + focus restore');
ok(/role="radiogroup"/.test(engineSrc) && /role="radio"/.test(engineSrc) && /aria-checked/.test(engineSrc), 'step options are keyboard radios with aria-checked');
ok(/role="progressbar"/.test(engineSrc) && /aria-valuenow/.test(engineSrc), 'progress indicator is exposed to screen readers');

/* ----------------------------------------- recommended-start block per status */
section('Recommended-start block + dominant CTA + demoted secondary (per status)');
for (const code of TARGETS) {
  const html = CSG.recStartBlockHtml(code);
  ok(typeof html === 'string' && html.length > 0 && !/undefined/.test(html), `${code}: block renders, no undefined`);
  ok(html.includes('추천 시작점'), `${code}: shows 추천 시작점`);
  ok(html.includes(`내 상황에 맞는 ${code} 준비서류 찾기`), `${code}: KO primary CTA copy`);
  ok(html.includes('다른 방식으로 보기'), `${code}: secondary actions grouped under 다른 방식으로 보기`);
  for (const s of ['전체 세부자격 보기', '공통서류 보기', '신청 절차 보기', '공식 근거 보기']) ok(html.includes(s), `${code}: secondary action ${s}`);
  const iCta = html.indexOf('csg-primary-cta');
  const iSec = html.indexOf('다른 방식으로 보기');
  ok(iCta !== -1 && iSec !== -1 && iCta < iSec, `${code}: primary CTA precedes demoted secondary actions`);
}
// English copy present too
global.currentLanguage = 'en';
for (const code of TARGETS) ok(CSG.recStartBlockHtml(code).includes(`Find My ${code} Document Checklist`), `${code}: EN primary CTA copy`);
global.currentLanguage = 'ko';

/* ----------------------------------------- source-backed flow options */
section('Flow steps are source-backed (active subcodes / available procedures only)');
function model(code) { return RG.buildGuidanceModel(byCode(code)); }
for (const code of TARGETS) {
  const m = model(code);
  const steps = CSG.buildSteps(m);
  const proc = steps.find((s) => s.id === 'procedure');
  ok(!!proc, `${code}: has a procedure step`);
  // procedure options (minus the trailing "I am not sure") must all be available
  const realProc = proc.options.filter((o) => o.id !== 'unsure');
  const availKeys = new Set(m.procedures.filter((p) => p.status === 'available').map((p) => p.key));
  ok(realProc.length > 0 && realProc.every((o) => availKeys.has(o.id)), `${code}: only available procedures offered`, realProc.map((o) => o.id).join(','));
  ok(proc.options.some((o) => o.id === 'unsure'), `${code}: procedure step offers "I am not sure"`);
  const sub = steps.find((s) => s.id === 'subcode');
  if (sub) {
    const realSub = sub.options.filter((o) => o.id !== 'unsure');
    const activeCodes = new Set(m.subcodes.filter((s) => s.status === 'active').map((s) => s.code));
    ok(realSub.length > 0 && realSub.every((o) => activeCodes.has(o.id)), `${code}: only active subcodes offered (no manual-review/reference placeholders)`);
    ok(sub.options.some((o) => o.id === 'unsure'), `${code}: subcode step offers "I am not sure"`);
  }
}
// F-5 specifics: 사증발급 is not_applicable → must NOT be offered; placeholder subcodes excluded.
const f5 = model('F-5');
const f5steps = CSG.buildSteps(f5);
ok(!f5steps.find((s) => s.id === 'procedure').options.some((o) => o.id === 'visa_issuance'), 'F-5: 사증발급(not_applicable) is not offered');
const f5sub = f5steps.find((s) => s.id === 'subcode');
ok(f5sub && !f5sub.options.some((o) => /manual_review|매뉴얼 참조/.test(o.label)), 'F-5: manual-review placeholder subcodes excluded');
// E-7: manual-review codes excluded
const e7sub = CSG.buildSteps(model('E-7')).find((s) => s.id === 'subcode');
ok(e7sub && !e7sub.options.some((o) => /manual_review|매뉴얼 참조|수동검토/.test(o.label)), 'E-7: manual-review subcodes excluded');
// D-2 and D-4 stay distinct
ok(byCode('D-2') && byCode('D-4'), 'D-2 and D-4 both present (kept distinct)');

/* --------------------------------------------- checklist-first, safe result */
section('Result is checklist-first and never invents documents');
const NOTE = { 'E-7': true, 'G-1': true, 'F-5': true };
for (const code of TARGETS) {
  const m = model(code);
  const steps = CSG.buildSteps(m);
  const sub = steps.find((s) => s.id === 'subcode');
  const proc = steps.find((s) => s.id === 'procedure');
  const ans = { subcode: sub ? sub.options[0].id : 'unsure', procedure: proc.options[0].id };
  const rm = CSG.buildResultModel(code, m, ans);
  ok(rm && Array.isArray(rm.firstSteps) && rm.firstSteps.length > 0, `${code}: result has first steps`);
  ok(Array.isArray(rm.procSteps) && rm.procSteps.length >= 5 && rm.procSteps.every((s) => s && !/undefined/.test(s)), `${code}: generic procedure step list (no undefined)`);
  if (NOTE[code]) ok(!!rm.noteKey, `${code}: carries a cautious status-specific note`);
  const text = CSG.checklistText(code, rm);
  ok(typeof text === 'string' && text.length > 0 && !/undefined/.test(text), `${code}: copyable checklist text has no undefined`);
  ok(/공식근거 확인 필요/.test(text) && /추가서류가 요구될 수 있습니다/.test(text), `${code}: checklist text carries needs-confirmation + safety note`);
}
// "unsure" answers never crash and produce a safe result.
const us = CSG.buildResultModel('G-1', model('G-1'), { subcode: 'unsure', procedure: 'unsure' });
ok(us && us.subLabel === '' && us.procLabel === '', 'unsure answers → empty selection, still a valid result model');

/* ------------------------------------------------------------- wiring */
section('index.html + visa-route-guide wiring (single CTA, no competition)');
ok(/<script defer src="assets\/js\/complex-status-guide\.js"><\/script>/.test(indexHtml), 'index.html loads complex-status-guide.js');
ok(/COMPLEX_GUIDE_MIGRATED = \[[^\]]*'F-6'[^\]]*'G-1'[^\]]*'E-7'[^\]]*'F-5'[^\]]*'D-2'[^\]]*'D-4'/.test(indexHtml),
  'renderF4RouteChooser suppresses the legacy route-wizard for all six');
ok(/COMPLEX_GUIDE_OWNED = \[[^\]]*'F-6'[^\]]*'G-1'[^\]]*'E-7'[^\]]*'F-5'[^\]]*'D-2'[^\]]*'D-4'/.test(routeGuideSrc),
  'visa-route-guide suppresses the generic in-card CTA for all six');
ok(/COMPLEX_GUIDE_MIGRATED[\s\S]{0,80}'F-4'/.test(indexHtml) && /COMPLEX_GUIDE_OWNED[\s\S]{0,40}'F-4'/.test(routeGuideSrc),
  'F-4 remains suppressed too (no regression)');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_complex_status_guide: ALL PASS');
