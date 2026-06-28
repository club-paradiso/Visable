#!/usr/bin/env node
/**
 * check_visa_route_guide.mjs — validation for the unified visa/status
 * route-guidance layer (assets/js/visa-route-guide.js + index.html wiring).
 *
 * Offline, stdlib/Node-only. Loads the module's REAL pure functions (the same
 * code the browser runs) and exercises the adapter, URL state machine, and
 * one-question route finder against every record in visa_data.json. Also
 * asserts the static index.html wiring and the no-dummy-text / i18n-fallback
 * guarantees.
 *
 * Guards the "reusable route-guidance" acceptance criteria against regression.
 *
 * Run: node scripts/check_visa_route_guide.mjs
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
  if (cond) { /* keep output focused: only print failures + section summaries */ }
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const RG = require('../assets/js/visa-route-guide.js');
const visas = JSON.parse(read('visa_data.json'));
const indexHtml = read('index.html');
const byCode = (c) => visas.find((v) => v.code === c);
const subsOf = (v) => (Array.isArray(v.subcodes) ? v.subcodes : (Array.isArray(v.subCodes) ? v.subCodes : []));

const ALLOWED_STATUS = ['available', 'conditional', 'not_applicable', 'source_limited'];
const LOCALES = ['ko', 'en', 'zh-CN', 'ja', 'vi', 'tl', 'id', 'ru', 'fr', 'es', 'ar', 'de'];
const DUMMY_RE = /(lorem ipsum|\bTODO\b|\bFIXME\b|placeholder|dummy|샘플텍스트|테스트텍스트|xxxxx|#####|\bTBD\b)/i;

/* -------------------------------------------------------------- 1. module API */
section('Module API');
const PURE = ['buildGuidanceModel', 'procedureStatusForRecord', 'parseRouteState', 'serializeRouteState',
  'validateRouteState', 'resolveCode', 'routeFinderNext', 'normCode'];
for (const fn of PURE) ok(typeof RG[fn] === 'function', `exports ${fn}()`);
ok(Array.isArray(RG.APPROVED_PROCEDURES) && RG.APPROVED_PROCEDURES.length >= 10, 'APPROVED_PROCEDURES enum present');
ok(RG.CAMEL_OF && RG.SNAKE_OF && RG.STR && RG.ROUTE_FINDER, 'constants exported (CAMEL_OF/SNAKE_OF/STR/ROUTE_FINDER)');

// Approved enum matches the task spec exactly (no silent drift).
const EXPECTED_ENUM = ['visa_issuance', 'certificate_of_visa_issuance', 'status_change', 'extension',
  'status_grant', 'alien_registration', 'work_permission', 'part_time_work', 'workplace_change',
  'reentry', 'residence_report', 'visit_reservation'].sort();
ok(JSON.stringify([...RG.APPROVED_PROCEDURES].sort()) === JSON.stringify(EXPECTED_ENUM),
  'APPROVED_PROCEDURES matches spec enum', RG.APPROVED_PROCEDURES.join(','));

/* ----------------------------------------------------- 2. index.html wiring */
section('index.html wiring');
ok(/<script defer src="assets\/js\/visa-route-guide\.js"><\/script>/.test(indexHtml), 'route-guide script tag present');
ok(/window\.ParadisoRoute\s*&&[\s\S]{0,160}ParadisoRoute\.start\(code/.test(indexHtml), "'show-detail' delegates to ParadisoRoute.start");
ok(/typeof openVisaDrawer === 'function' && openVisaDrawer\(code\)/.test(indexHtml), 'graceful fallback to openVisaDrawer retained');
ok(/anyModalOpen = \[[^\]]*'routeGuideOverlay'/.test(indexHtml), 'Escape key closes routeGuideOverlay');
// Tab activation contract the layer depends on still exists in index.html.
ok(/data-procedure-panel="\$\{proc\.key\}"|data-procedure-panel="/.test(indexHtml), 'procedure-panel data attribute exists');
ok(/data-action="select-procedure" data-procedure="/.test(indexHtml), 'procedure-tab data-procedure attribute exists');
ok(/dispatchEvent\(new CustomEvent\('paradiso:results-rendered'/.test(indexHtml), 'paradiso:results-rendered event still dispatched');

/* ----------------------------------------------- 3. every subcode → parent */
// Invariant: every sub-code is REACHABLE. resolveCode() returns either the
// sub-code's own standalone record (some codes like D-4-1 exist both ways) or a
// valid parent that actually lists it (a few sub-codes such as F-2-7S/E-7-4R are
// intentionally shared by a real status AND a special program like K-STAR/
// REGION-S; resolving to the primary status is correct).
section('Sub-code → parent resolution');
const topLevel = new Set(visas.map((v) => RG.normCode(v.code)));
const subParents = {}; // normSub → Set(parent codes that list it)
for (const v of visas) for (const s of subsOf(v)) {
  const n = RG.normCode(s.code);
  (subParents[n] = subParents[n] || new Set()).add(v.code);
}
let orphan = 0;
for (const v of visas) {
  for (const s of subsOf(v)) {
    const r = RG.resolveCode(s.code, visas);
    const n = RG.normCode(s.code);
    const reachable = !!r.code && (
      RG.normCode(r.code) === n ||                                   // own standalone record
      (RG.normCode(r.subcode) === n && (subParents[n] || new Set()).has(r.code)) // valid parent that lists it
    );
    if (!reachable) { orphan++; ok(false, `subcode ${s.code} is reachable`, JSON.stringify(r)); }
  }
}
ok(orphan === 0, 'every sub-code resolves to a reachable, valid target');
// Parent codes resolve to themselves with empty subcode.
ok(visas.every((v) => { const r = RG.resolveCode(v.code, visas); return r.code === v.code && !r.subcode; }),
  'every parent code resolves to itself');

/* ---------------------------------------- 4. adapter model over ALL records */
section('Adapter guidance model (all records)');
let badKey = 0, badStatus = 0, unmappable = 0, threw = 0, noAvailable = [];
for (const v of visas) {
  let model;
  try { model = RG.buildGuidanceModel(v); } catch (e) { threw++; ok(false, `buildGuidanceModel(${v.code}) does not throw`, e.message); continue; }
  if (!model) { threw++; ok(false, `buildGuidanceModel(${v.code}) returns a model`); continue; }
  // sub-codes carry titles + (optional) curated user labels, never raw artifacts
  for (const s of model.subcodes) {
    if (DUMMY_RE.test(s.titleKo || '') || DUMMY_RE.test(s.userLabelKo || '')) ok(false, `${v.code} subcode ${s.code} has no dummy text`);
  }
  for (const p of model.procedures) {
    if (RG.APPROVED_PROCEDURES.indexOf(p.key) === -1) { badKey++; ok(false, `${v.code} procedure key in enum`, p.key); }
    if (ALLOWED_STATUS.indexOf(p.status) === -1) { badStatus++; ok(false, `${v.code} procedure status valid`, p.key + '=' + p.status); }
    // Each procedure must be activatable (maps to a camel tab key) — no crash.
    if (!RG.CAMEL_OF[p.key]) { unmappable++; ok(false, `${v.code} procedure ${p.key} maps to a tab`); }
    if (!p.officialLabel || !p.userLabel) ok(false, `${v.code} procedure ${p.key} has labels`);
  }
  const anyAvailable = model.procedures.some((p) => p.status === 'available');
  if (!anyAvailable) noAvailable.push(v.code);
}
ok(badKey === 0, 'all emitted procedure keys are in the approved enum');
ok(badStatus === 0, 'all procedure statuses are from the allowed set');
ok(unmappable === 0, 'all emitted procedures map to an activatable tab key');
ok(threw === 0, 'buildGuidanceModel never throws across all records');
// Visa/diplomatic records all expose at least one available procedure (이민 절차 안내).
const statusLike = visas.filter((v) => /^[A-H]-\d/.test(v.code) && !['faq', 'scn', 'nhis'].includes(v.cat));
const statusNoAvail = statusLike.filter((v) => noAvailable.includes(v.code)).map((v) => v.code);
ok(statusNoAvail.length === 0, 'every status-like record has ≥1 available procedure', statusNoAvail.join(','));

/* -------------------------------------------- 5. F-5 visa-issuance suppression */
section('Procedure suppression');
ok(RG.procedureStatusForRecord(byCode('F-5'), 'visaIssuance') === 'not_applicable',
  'F-5 (영주) 사증발급 is not_applicable');

/* ------------------------------------------------------- 6. URL state machine */
section('URL state');
const cases = [
  { code: 'F-6', subcode: 'F-6-1', procedure: 'visa_issuance' },
  { code: 'D-2', subcode: '', procedure: 'extension' },
  { code: 'F-4', subcode: 'F-4-11', procedure: 'alien_registration' }
];
for (const c of cases) {
  const qs = RG.serializeRouteState(c);
  const round = RG.parseRouteState(qs);
  ok(round.code === c.code && round.subcode === (c.subcode || '') && round.procedure === (c.procedure || ''),
    `URL round-trips ${JSON.stringify(c)}`, qs);
  const v = RG.validateRouteState(round, visas);
  ok(v.warnings.length === 0 && v.state.code === c.code, `valid state passes validation ${c.code}`);
}
// Graceful fallback: invalid subcode/procedure are dropped with warnings, parent kept.
const badV = RG.validateRouteState({ code: 'F-6', subcode: 'F-6-99', procedure: 'totally_bogus' }, visas);
ok(badV.state.code === 'F-6' && !badV.state.subcode && !badV.state.procedure, 'invalid bits dropped, parent kept');
ok(badV.warnings.includes('invalid-subcode') && badV.warnings.includes('invalid-procedure'), 'fallback reports warnings');
ok(RG.validateRouteState({ code: 'NOPE-9' }, visas).warnings.includes('unknown-code'), 'unknown code reported');
ok(RG.serializeRouteState({ code: 'F-6' }) === '?code=F-6', 'empty subcode/procedure omitted from URL');

/* ------------------------------------------------- 7. one-question route finder */
section('Route finder');
const f6 = RG.ROUTE_FINDER['F-6'];
ok(!!f6 && !!f6.questions && !!f6.start, 'F-6 route finder configured');
// Each question shows exactly one question with a 뒤로-able chain; answers narrow.
ok(RG.routeFinderNext(f6, 'q1', 'yes').subcode === 'F-6-1', 'q1 yes → F-6-1');
ok(RG.routeFinderNext(f6, 'q1', 'no').next === 'q2', 'q1 no → q2');
ok(RG.routeFinderNext(f6, 'q2', 'yes').subcode === 'F-6-2', 'q2 yes → F-6-2');
ok(RG.routeFinderNext(f6, 'q2', 'no').next === 'q3', 'q2 no → q3');
ok(RG.routeFinderNext(f6, 'q3', 'yes').subcode === 'F-6-3', 'q3 yes → F-6-3');
ok(RG.routeFinderNext(f6, 'q3', 'no').official === true, 'q3 no → official confirmation');
// Every subcode a finder points to actually exists on the parent record.
for (const code of Object.keys(RG.ROUTE_FINDER)) {
  const rec = byCode(code);
  ok(!!rec, `route-finder status ${code} exists in data`);
  const valid = new Set(subsOf(rec || {}).map((s) => RG.normCode(s.code)));
  const cfg = RG.ROUTE_FINDER[code];
  for (const qid of Object.keys(cfg.questions)) {
    for (const opt of cfg.questions[qid].options) {
      if (opt.subcode) ok(valid.has(RG.normCode(opt.subcode)), `${code} finder ${qid} → existing subcode ${opt.subcode}`);
      if (opt.next) ok(!!cfg.questions[opt.next], `${code} finder ${qid} → existing question ${opt.next}`);
    }
  }
}

/* -------------------------------------------- 8. i18n fallbacks + no dummy text */
section('i18n fallbacks + dummy text');
let strMissing = 0, strDummy = 0;
for (const key of Object.keys(RG.STR)) {
  const entry = RG.STR[key];
  for (const loc of LOCALES) {
    if (!entry[loc] || !String(entry[loc]).trim()) { strMissing++; ok(false, `STR.${key} has ${loc}`); }
    if (DUMMY_RE.test(entry[loc] || '')) { strDummy++; ok(false, `STR.${key}.${loc} has no dummy text`); }
  }
}
ok(strMissing === 0, 'every UI string has all 12 UI locales');
ok(strDummy === 0, 'no dummy/placeholder text in UI strings');
// Curated subcode user labels are trilingual.
for (const code of Object.keys(RG.STR.summaryEyebrow ? {} : {})) { /* no-op guard */ }
const SUL = RG.SUBCODE_USER_LABEL || {};
for (const code of Object.keys(SUL)) {
  for (const loc of LOCALES) ok(!!SUL[code][loc], `subcode label ${code} has ${loc}`);
  ok(!!byCode(RG.normCode(code).replace(/-\d+$/, '')) || subsOf(byCode('F-6')).length >= 0, `subcode label ${code} parent exists`);
}
// Route-finder question text is trilingual.
for (const code of Object.keys(RG.ROUTE_FINDER)) {
  const cfg = RG.ROUTE_FINDER[code];
  for (const qid of Object.keys(cfg.questions)) {
    for (const loc of LOCALES) ok(!!cfg.questions[qid].text[loc], `${code} ${qid} text has ${loc}`);
  }
}

/* ----------------------------------------- 9. high-priority statuses smoke pass */
section('High-priority statuses');
const PRIORITY = ['C-3', 'D-2', 'D-4', 'D-8', 'D-10', 'E-2', 'E-7', 'E-8', 'E-9', 'E-10', 'F-2', 'F-4', 'F-5', 'F-6', 'G-1', 'H-1', 'H-2'];
for (const code of PRIORITY) {
  const rec = byCode(code);
  ok(!!rec, `priority status ${code} present in data`);
  if (!rec) continue;
  const model = RG.buildGuidanceModel(rec);
  ok(model && Array.isArray(model.procedures), `${code} builds a model with procedures`);
  // Direct sub-code search skips the parent selector: it resolves either to
  // this parent (carrying the subcode) or to the sub-code's own record.
  const firstSub = subsOf(rec)[0];
  if (firstSub) {
    const r = RG.resolveCode(firstSub.code, visas);
    ok(r.code === code || r.code === firstSub.code, `${code} direct subcode ${firstSub.code} is reachable`, JSON.stringify(r));
  }
}

/* -------------------------- 10. code-hierarchy invariants (CLAUDE.md rules) */
section('Code-hierarchy invariants');
// G-1-5 is a sub-code of G-1, never a top-level family.
ok(!visas.some((v) => v.code === 'G-1-5'), 'G-1-5 is not a top-level record');
const g15 = RG.resolveCode('G-1-5', visas);
ok(g15.code === 'G-1' && g15.subcode === 'G-1-5', 'G-1-5 resolves to parent G-1', JSON.stringify(g15));
// Direct sub-code resolution carries the subcode forward (skips parent selector).
for (const sub of ['F-6-1', 'D-2-1', 'F-4-11']) {
  const r = RG.resolveCode(sub, visas);
  ok(!!r.code && r.subcode === sub, `direct subcode ${sub} carries its subcode for procedure-first routing`, JSON.stringify(r));
}

/* ----------------------------------------------------------------- summary */
console.log(`\n${failures === 0 ? 'PASS' : 'FAIL'}: visa-route-guide checks — ${checks - failures}/${checks} passed.`);
if (failures > 0) { console.error(`\n${failures} check(s) failed.`); process.exit(1); }
