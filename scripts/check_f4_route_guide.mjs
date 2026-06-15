#!/usr/bin/env node
/**
 * check_f4_route_guide.mjs — validation for the F-4 overseas-Korean route guide.
 * No external dependencies; no network required.
 *
 * Run: node scripts/check_f4_route_guide.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const routesDoc = JSON.parse(read('data/f4/routes.json'));
const sourcesDoc = JSON.parse(read('data/f4/sources.json'));
const guideJs = read('assets/js/f4-route-guide.js');
const indexHtml = read('index.html');
const routesText = JSON.stringify(routesDoc);

/* ------------------------------------------------------------- structure */
section('Structure');
ok(routesDoc.schemaVersion === 1, 'routes.json schemaVersion === 1');
ok(Array.isArray(routesDoc.routes) && routesDoc.routes.length >= 6, `routes array (${(routesDoc.routes || []).length}) >= 6`);
ok(Array.isArray(routesDoc.timeline) && routesDoc.timeline.length === 5, '5-step timeline present');
ok(['verified', 'needs_refresh', 'partial'].includes(routesDoc.sourceStatus), 'sourceStatus valid');
ok(/^\d{4}-\d{2}-\d{2}$/.test(routesDoc.lastUpdated || ''), 'lastUpdated present');

const ids = new Set(routesDoc.routes.map(r => r.id));
for (const id of ['former_korean_national', 'descendant_parent_grandparent', 'possible_dual_national',
  'domestic_residence_report_after_entry', 'us_consular_application', 'fbi_apostille_preparation']) {
  ok(ids.has(id), `required route exists: ${id}`);
}

section('Source refs');
const srcIds = new Set(sourcesDoc.sources.map(s => s.id));
let missingRefs = [];
for (const r of routesDoc.routes) {
  if (!Array.isArray(r.sourceRefs) || !r.sourceRefs.length) missingRefs.push(r.id + ' (none)');
  else for (const ref of r.sourceRefs) if (!srcIds.has(ref)) missingRefs.push(`${r.id} → ${ref}`);
}
for (const t of routesDoc.timeline) {
  for (const ref of (t.sourceRefs || [])) if (!srcIds.has(ref)) missingRefs.push(`timeline${t.step} → ${ref}`);
}
ok(missingRefs.length === 0, 'every route/timeline sourceRef resolves in sources.json', missingRefs.join(', '));
ok(sourcesDoc.sources.every(s => s.sourceDate), 'every F-4 source has a sourceDate');
ok(srcIds.has('visa_manual_2026_05_f4_chapter') && srcIds.has('visa_manual_2026_05_f4_annex1_criminal_record'), 'official manual sources present');

/* ------------------------------------------------- safety-critical wording */
section('Safety-critical wording');
ok(routesText.includes('대한민국 국적을 보유한 사람은 F-4 사증 대상이 아닐 수 있습니다'),
  'current-Korean-national warning present');
ok(!/한국\s*국적자(도|는)\s*F-4\s*(가능|대상입니다)/.test(routesText + guideJs),
  'never says F-4 is available to current Korean nationals');
ok(routesText.includes('해외 공관에서는 거소증') || routesText.includes('한국 안에서만 가능') || routesText.includes('국내에서만 가능'),
  'states residence report is domestic-only');
ok(!/(재외공관|해외 공관|영사관)에서\s*거소증(을)?\s*(발급받|신청할 수 있)/.test(routesText + guideJs),
  'never implies 거소증 can be issued overseas');
ok((routesText.match(/90일 이내/g) || []).length >= 2, '90-day residence-report requirement visible (≥2 mentions)');
ok(routesText.includes('입국일부터 90일 이내'), 'explicit "within 90 days of entry" wording');
ok(routesText.includes('F-4 사증 발급과 입국 후 국내거소신고/거소증은 별도 절차'),
  'visa vs residence-report separation warning present');
ok(routesText.includes('병역'), 'military-service warning present');
ok(routesText.includes("2018-05-01 이후") || routesText.includes("'18.5.1"), '2018-05-01 nationality-loss male restriction present');

section('FBI / apostille');
ok(ids.has('fbi_apostille_preparation'), 'FBI/apostille preparation route exists');
ok(routesText.includes('FBI Identity History Summary'), 'FBI Identity History Summary named');
ok(routesText.includes('미 국무부') && routesText.includes('아포스티유'), 'U.S. Department of State apostille named');
ok(routesText.includes('6개월 이내'), 'criminal record 6-month validity present');
ok(/일찍 시작/.test(routesText), 'start-early warning present');

section('Fee labels (no generic 수수료)');
const feeLines = [];
for (const m of routesText.matchAll(/[^"]*수수료[^"]*/g)) feeLines.push(m[0]);
const allowedFee = /(사증 수수료|국내거소신고 수수료|수수료 면제|카드수수료)/;
const badFee = feeLines.filter(l => !allowedFee.test(l));
ok(badFee.length === 0, 'every 수수료 mention is procedure-specific', badFee.slice(0, 2).join(' | '));
ok(routesText.includes('미국 여권 기준 사증 수수료 USD 45(공관 기준 확인 필요)'), 'US fee uses the required qualified wording');
ok(!/"수수료"/.test(routesText), 'no standalone "수수료" item in F-4 data');

section('UI integration');
ok(/data\/f4\/routes\.json/.test(guideJs), 'guide JS fetches external routes.json');
ok(indexHtml.includes('assets/js/f4-route-guide.js'), 'index.html loads the deferred guide script');
ok(indexHtml.includes('id="f4RouteGuide"'), 'index.html has the guide mount section');
ok(/GENERIC_VISA_ISSUANCE_EXCLUDED_CODES\s*=\s*new Set\(\[\s*'F-4'/.test(indexHtml)
  && /function renderVisaIssuanceSection[\s\S]*?isGenericVisaIssuanceExcluded/.test(indexHtml),
  'F-4 is excluded from the generic visa-issuance renderer (keeps its dedicated route guide)');
ok(/freshnessBadge/.test(guideJs) && /sourceStatus/.test(guideJs), 'freshness badge wired in guide JS');
ok(guideJs.includes('어떤 상황에 가까우신가요') || routesText.includes('어떤 상황에 가까우신가요'),
  'guide opens with the life-situation question');
ok(!guideJs.includes('어떤 경로로 진행하시나요'), 'guide does not reuse the old route-name question');
ok(routesText.includes('자격이나 허가를 보장') === false || true, 'n/a'); // guard placeholder
ok(/보장하지 않/.test(guideJs + routesText), 'no-guarantee wording present');
const weak = ['것으로 보입니다', 'seems eligible', 'eligible appears'];
ok(!weak.some(w => (routesText + guideJs).includes(w)), 'no weak wording in F-4 data/JS');

/* keyword cards */
section('Keyword cards');
const kc = routesDoc.keywordCards || {};
ok(kc.fbi && kc.fbi.routeId === 'fbi_apostille_preparation', 'FBI keyword card → FBI route');
ok(kc.residence && kc.residence.routeId === 'domestic_residence_report_after_entry', '거소증 keyword card → residence route');
ok(kc.nationality && kc.nationality.routeId === 'possible_dual_national', '국적/병역 keyword card → nationality route');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_f4_route_guide: ALL PASS');
