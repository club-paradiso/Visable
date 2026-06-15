#!/usr/bin/env node
/**
 * smoke_f4_hub.mjs — automated stand-in for the F-4 hub manual-QA scenarios.
 *
 * No DOM/browser is available offline, so this exercises the real routing
 * function (extracted from the guide JS) and asserts that every renderer input
 * the diagnostic/hub/country paths depend on is present and well-formed — i.e.
 * each Phase-11 scenario produces a complete, non-undefined view.
 *
 * Run: node scripts/smoke_f4_hub.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const readJson = (p) => JSON.parse(read(p));

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const base = readJson('data/f4/base.json');
const diagnostic = readJson('data/f4/diagnostic.json');
const faq = readJson('data/f4/faq.json');
const countries = readJson('data/f4/countries.json');
const overlays = readJson('data/f4/country_overlays.json').overlays;
const guideJs = read('assets/js/f4-route-guide.js');

const computeRoute = new Function(`${guideJs.match(/function computeRoute\(a\)\s*\{[\s\S]*?\n  \}/)[0]}; return computeRoute;`)();

/* ----------------------------------------------- Phase 11 diagnostic flows */
section('Diagnostic scenarios (Phase 11)');
const flows = [
  { name: '1) foreign national overseas, no F-4', a: { nationality: 'foreign', location: 'overseas_apply', visa_status: 'no' }, route: 'overseas_application' },
  { name: '2) F-4 issued overseas, not yet entered', a: { nationality: 'foreign', visa_status: 'yes_not_entered' }, route: 'overseas_application', note: 'visaIssuedNotEntered' },
  { name: '3) entered, no residence report, <90d', a: { nationality: 'foreign', visa_status: 'yes_entered', residence_report: 'not_yet', entry_timing: 'under90' }, route: 'residence_report', note: 'enteredNoReportUnder90' },
  { name: '4) entered, no report, 90d passed', a: { nationality: 'foreign', visa_status: 'yes_entered', residence_report: 'not_yet', entry_timing: 'over90' }, route: 'official_check', note: 'enteredNoReportOver90' },
  { name: '5) in Korea, wants status change', a: { nationality: 'foreign', location: 'domestic_change' }, route: 'status_change' },
  { name: '6) currently Korean national', a: { nationality: 'korean' }, route: 'nationality_check', note: 'nationalityKorean' },
  { name: '7) nationality-loss unsure', a: { nationality: 'unsure' }, route: 'nationality_check', note: 'nationalityUnsure' }
];
for (const f of flows) {
  const r = computeRoute(f.a);
  ok(r.routeId === f.route, `${f.name} → ${f.route}`, `got ${r.routeId}`);
  if (f.note) ok(r.contextNote === f.note && diagnostic.contextNotes[f.note], `${f.name} carries note ${f.note}`);
}

section('Route render inputs complete');
for (const [id, route] of Object.entries(diagnostic.routes)) {
  const fieldsOk = route.title && route.recommended && route.why && Array.isArray(route.checkFirst) && Array.isArray(route.ctas);
  ok(fieldsOk, `route "${id}" has all render fields`);
  const ctasResolve = route.ctas.every((c) => diagnostic.ctaCatalog[c]);
  ok(ctasResolve, `route "${id}" CTAs resolve in ctaCatalog`);
  ok(['overview', 'overseasApplication', 'residenceReport', 'statusChange'].includes(route.hubTab), `route "${id}" hubTab valid`);
}

section('90-day prominence');
ok(diagnostic.routes.residence_report.warnings.join(' ').includes('자동으로 발급되지 않'), 'residence_report warns 거소증 not automatic');
ok(diagnostic.contextNotes.enteredNoReportUnder90.includes('90일 이내'), 'under-90 note states the 90-day deadline');
ok(/하이코리아|1345/.test(diagnostic.contextNotes.enteredNoReportOver90), 'over-90 note routes to HiKorea/1345 (no legal conclusion)');
ok(!/불법|위반입니다|처벌됩니다/.test(diagnostic.contextNotes.enteredNoReportOver90), 'over-90 note avoids legal conclusions');

/* ------------------------------------------------ country selection paths */
section('Country selection coverage (every registry country renders)');
function detectCountry(query) {
  const q = String(query || '').toLowerCase();
  let hit = '';
  countries.countries.forEach((c) => {
    if (hit) return;
    if (q.indexOf(c.labelKo) !== -1 || (c.labelEn && q.indexOf(c.labelEn.toLowerCase()) !== -1)) hit = c.countryCode;
  });
  return hit;
}
const detectCases = [['미국 F-4', 'US'], ['캐나다 F-4', 'CA'], ['일본 F-4', 'JP'], ['중국 F-4', 'CN'], ['호주 F-4', 'AU']];
for (const [q, code] of detectCases) ok(detectCountry(q) === code, `query "${q}" preselects ${code}`, detectCountry(q));

let renderProblems = [];
for (const c of countries.countries) {
  const ov = overlays[c.countryCode];
  if (ov) {
    // overlay path: must have a verification state and links
    if (!ov.sourceStatus || !ov.missionFinderUrl) renderProblems.push(`${c.countryCode}: overlay missing status/links`);
  }
  // common rules are ALWAYS available regardless of overlay
  if (!base.common.separationWarning || !base.fallbackUnverifiedCountry) renderProblems.push('base common/fallback missing');
}
ok(renderProblems.length === 0, 'every country renders (overlay or safe fallback) with common rules present', renderProblems.slice(0, 3).join(' | '));
ok(countries.countries.some((c) => !overlays[c.countryCode]), 'at least one country uses the official-check fallback (e.g. tier 2/3)');

section('US-only specifics do not surface for other countries');
const usBlob = JSON.stringify(overlays.US);
ok(/FBI|미 국무부/.test(usBlob), 'US overlay carries FBI / 미 국무부 specifics');
const nonUsLeak = Object.entries(overlays).filter(([code, ov]) => code !== 'US' && /FBI|Identity History Summary|미 국무부/.test(JSON.stringify(ov))).map(([c]) => c);
ok(nonUsLeak.length === 0, 'no non-US country surfaces US-only specifics', nonUsLeak.join(', '));

/* ----------------------------------------------------- search relevance */
section('Search relevance (Phase 11 terms)');
const F4_QUERY = /f-?4|재외동포|동포\s*비자/i;
const EXTRA = ['거소증', '국내거소', '거소신고', 'fbi', '범죄경력', '아포스티유', '영사확인', '국적상실', '복수국적', '병역', '이중국적', '자격변경', '재외공관', '국내거소신고'];
function isF4Relevant(q) {
  if (F4_QUERY.test(q)) return true;
  const lower = String(q).toLowerCase();
  return EXTRA.some((t) => lower.indexOf(t) !== -1);
}
const relevant = ['F-4', '재외동포', '미국 F-4', '캐나다 F-4', '일본 F-4', '중국 F-4', '호주 F-4', '거소증', '국내거소신고', 'F-4 자격변경', 'FBI 아포스티유', '재외공관 신청', 'H-2 F-4'];
for (const q of relevant) ok(isF4Relevant(q), `search term is F-4-relevant: "${q}"`);
ok(!isF4Relevant('제주 무사증'), 'unrelated term is not F-4-relevant');

/* ----------------------------------------------------------- hub tabs */
section('Hub tab render inputs');
for (const tab of ['overview', 'overseasApplication', 'residenceReport', 'statusChange']) {
  ok(base.hub[tab] && base.hub[tab].title, `hub tab "${tab}" has content`);
}
ok(faq.groups.length === 3 && faq.groups.every((g) => g.items.length >= 3), 'FAQ tab has 3 groups with multiple items each');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('smoke_f4_hub: ALL PASS');
