#!/usr/bin/env node
/**
 * check_short_stay_rules.mjs — validation for the short-stay country checker.
 * No external dependencies; no network required.
 *
 * Run: node scripts/check_short_stay_rules.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) { console.log(`  PASS  ${label}`); }
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

const rules = JSON.parse(read('data/short-stay/rules.json'));
const sources = JSON.parse(read('data/short-stay/sources.json'));
const checkerJs = read('assets/js/short-stay-checker.js');
const indexHtml = read('index.html');

/* ---------------------------------------------------------- schema shape */
section('Schema shape');
ok(rules.schemaVersion === 1, 'schemaVersion === 1');
ok(/^\d{4}-\d{2}-\d{2}$/.test(rules.lastUpdated || ''), 'lastUpdated is YYYY-MM-DD');
ok(typeof rules.generatedAt === 'string' && rules.generatedAt.length > 10, 'generatedAt present');
ok(['verified', 'needs_refresh', 'partial'].includes(rules.sourceStatus), 'sourceStatus is a known value');
ok(rules.countries && typeof rules.countries === 'object', 'countries map present');
ok(rules.aliases && typeof rules.aliases === 'object', 'aliases map present');
for (const key of ['b1VisaWaiverAgreement', 'b21GeneralVisaFreeKeta', 'b22JejuVisaFree', 'c3Fallback']) {
  ok(rules.rules && typeof rules.rules[key] === 'object', `rules.${key} present`);
}

/* --------------------------------------------------------- country records */
section('Country records');
const countries = Object.values(rules.countries);
ok(countries.length >= 150, `country count ${countries.length} >= 150`);
let aliasMissing = 0, ketaStayMissing = 0, deniedConflict = 0, expansionFree = 0;
for (const c of countries) {
  if (!Array.isArray(c.aliasesKo) || !c.aliasesKo.length || !Array.isArray(c.aliasesEn) || !c.aliasesEn.length) aliasMissing++;
  if (c.keta && c.keta.eligible && !c.keta.allowedStay) ketaStayMissing++;
  if (c.b22Jeju.jejuEntryDenied && (c.b22Jeju.stayAreaExpansionPermitRequired ||
      c.b22Jeju.mainlandMovement === 'general_visa_free_path_available')) deniedConflict++;
  if (c.b22Jeju.stayAreaExpansionPermitRequired &&
      c.b22Jeju.mainlandMovement !== 'requires_stay_area_expansion_permit') expansionFree++;
}
ok(aliasMissing === 0, 'every country has Korean + English aliases', `${aliasMissing} missing`);
ok(ketaStayMissing === 0, 'every K-ETA-eligible country has an allowed stay', `${ketaStayMissing} missing`);
ok(deniedConflict === 0, 'Jeju entry-denied countries are never also marked Jeju-allowed/permit-track', `${deniedConflict} conflicts`);
ok(expansionFree === 0, 'expansion-permit countries are never treated as free mainland movement', `${expansionFree} wrong`);

/* -------------------------------------------------------------- Vietnam */
section('Vietnam classification (explicit)');
const vn = rules.countries.VN;
ok(!!vn, 'Vietnam (VN) record exists');
if (vn) {
  ok(vn.b1.ordinaryEligible === false, 'VN: B-1 ordinary NOT eligible');
  ok(vn.b21.listed === false, 'VN: B-2-1 general visa-free NOT listed');
  ok(vn.b22Jeju.jejuEntryDenied === false, 'VN: NOT in Jeju entry-denied list');
  ok(vn.b22Jeju.stayAreaExpansionPermitRequired === true, 'VN: stay-area expansion permit required');
  ok(vn.b22Jeju.passportScope === 'ordinary', 'VN: expansion permit scope = ordinary passports');
  ok(vn.keta.eligible === false, 'VN: K-ETA not eligible');
}

/* ----------------------------------------------------------- C-3 fallback */
section('C-3 fallback');
const pm = rules.rules.c3Fallback.purposeMap;
ok(pm && pm.tourism && pm.tourism.code === 'C-3-9', 'tourism → C-3-9');
ok(pm.group_tourism && pm.group_tourism.code === 'C-3-2', 'group tourism → C-3-2');
ok(pm.business && pm.business.code === 'C-3-4', 'business → C-3-4');
ok(pm.medical && pm.medical.code === 'C-3-3', 'medical → C-3-3');
ok(pm.transit && pm.transit.code === 'C-3-10', 'transit → C-3-10');
ok(pm.overseas_korean && pm.overseas_korean.code === 'C-3-8', 'overseas Korean → C-3-8');
ok(pm.work_or_profit && pm.work_or_profit.code === null && /C-4/.test(pm.work_or_profit.note), 'work/profit → no B/C path, C-4 warning');

/* ----------------------------------------------- C-3-10 순수환승 transit rule */
section('Transit rule (순수환승 C-3-10)');
const tr = rules.rules.c3Fallback.transitRule;
ok(tr && tr.code === 'C-3-10', 'transitRule present with code C-3-10');
if (tr) {
  ok(Array.isArray(tr.visaRequiredIso2) && ['SY', 'SD', 'YE', 'EG'].every(x => tr.visaRequiredIso2.includes(x)),
    'transit visa-required nationalities = 시리아·수단·예멘·이집트 (SY/SD/YE/EG)', tr.visaRequiredIso2 && tr.visaRequiredIso2.join(','));
  ok(tr.diplomaticOfficialExempt === true, 'diplomatic/official passports are C-3-10 exempt');
  ok(/0일/.test(tr.stayPeriod || ''), 'transit C-3-10 stay period is 0일 (not an entry route)');
  ok(tr.transitAreaHours === 72, 'transit-area temporary stay = 72 hours');
  ok(Array.isArray(tr.sourceRefs) && tr.sourceRefs.includes('visa_manual_2026_05_b1_b2_c3'), 'transitRule cites the visa manual source');
}

/* -------------------------------------------------------------- sources */
section('Sources');
const srcIds = new Set(sources.sources.map(s => s.id));
for (const id of ['law_immigration_enforcement_decree_table_1', 'visa_manual_2026_05_b1_b2_c3',
  'stay_manual_2026_05_b1_b2_extension_change', 'k_eta_eligible_countries',
  'moj_jeju_notice_2022_189', 'mofa_jeju_notice_copy_2023_09_18']) {
  ok(srcIds.has(id), `required source id present: ${id}`);
}
ok(sources.sources.every(s => s.sourceDate || s.effectiveDate), 'every source has a sourceDate/effectiveDate');
const staleNoticeShown = rules.sourceStatus !== 'verified'
  ? /현재 저장된 자료 기준입니다|공식 최신성 확인 필요/.test(checkerJs)
  : true;
ok(staleNoticeShown, 'stale-source warning copy exists when sourceStatus is not verified');

/* --------------------------------------------- index.html stays lightweight */
section('index.html stays lightweight (no embedded country lists)');
const obscure = ['감비아', '상투메프린시페', '부르키나파소', '코트디브아르', '적도기니', '카보베르데', '모리타니', '시에라리온', '투르크메니스탄', '키리바시'];
const embedded = obscure.filter(n => indexHtml.includes(n));
ok(embedded.length === 0, 'no Jeju/expansion list countries embedded in index.html', embedded.join(','));
ok(indexHtml.includes('assets/js/short-stay-checker.js'), 'index.html loads the deferred checker script');
ok(indexHtml.includes('id="shortStayChecker"'), 'index.html has the checker mount section');
ok(indexHtml.includes('id="shortStayModalOverlay"'), 'index.html hosts the short-stay checker as a page popup (modal)');
ok(/fetch\(RULES_URL/.test(checkerJs) && /data\/short-stay\/rules\.json/.test(checkerJs), 'checker JS fetches external rules.json');

/* ------------------------------------------------------- forbidden wording */
section('Forbidden / required wording');
const myFiles = {
  'rules.json': JSON.stringify(rules),
  'checker JS': checkerJs,
  'sources.json': JSON.stringify(sources)
};
const weak = ['것으로 보입니다', '대상이 아닌 것으로 보입니다', '가능한 것으로 보입니다', '포함되지 않은 것으로 보입니다', 'seems eligible', 'seems not eligible', 'eligible appears'];
for (const [name, text] of Object.entries(myFiles)) {
  const hit = weak.find(w => text.includes(w));
  ok(!hit, `no weak wording in ${name}`, hit);
}
const guarantee = [/입국\s*가능합니다/, /무조건\s*입국/, /입국(이|을|은)\s*보장(됩|됩니다|합니다)/, /본토\s*이동\s*가능합니다/, /반드시\s*입국할\s*수\s*있/];
for (const [name, text] of Object.entries(myFiles)) {
  const hit = guarantee.find(g => g.test(text));
  ok(!hit, `no entry-guarantee wording in ${name}`, hit && String(hit));
}
ok(/K-ETA는 사증\(비자\)이 아닌/.test(checkerJs), 'K-ETA explicitly described as NOT a visa');
ok(!/K-ETA\s*(비자|사증)\b/.test(checkerJs.replace(/사증\(비자\)이 아닌/g, '')), 'K-ETA never called a visa');
ok(/최종 입국 여부는 입국심사관이 결정/.test(checkerJs), 'final-entry-decision warning present');
ok(/항공사 탑승 가능 여부/.test(checkerJs), 'airline boarding warning present');
ok(/제주 무사증은 일반 무사증\/B-2-1·K-ETA와 별도 제도/.test(checkerJs), 'Jeju vs general separation warning present');
ok(!/제주\s*무사증\s*\+/.test(checkerJs), 'checker never builds a "Jeju visa-free + ..." route label (no expansion-permit answer)');
ok(/체류지역 확대는 원칙적으로 허용되지 않습니다/.test(checkerJs), 'checker states Jeju 체류지역 확대 is not allowed in principle');
ok(/국적을 먼저 입력해 주세요/.test(checkerJs), 'empty-country prompt present');
ok(/국가명을 찾지 못했습니다/.test(checkerJs), 'unknown-country prompt present');

/* ------------------------------------------- engine behavioral scenarios */
section('Engine scenarios (deterministic)');
(new Function(checkerJs))();
const api = globalThis.ParadisoShortStay;
ok(!!api, 'engine API exported for tests');
function scenario(nameKo, passport, purpose, destination, stayDays) {
  const c = api.resolveCountryAlias(nameKo, rules).country;
  return api.getShortStayEntryOptions({ country: c, passportType: passport, purpose, destination, stayDays }, rules);
}
const vnJeju = scenario('베트남', 'ordinary', 'tourism', 'jeju_only', 30);
ok(vnJeju.primary.path.includes('제주 무사증(B-2-2)'), 'VN jeju_only → Jeju B-2-2 check path');
ok(vnJeju.primary.explanation.join(' ').includes('포함되어 있지 않습니다'), 'VN jeju_only → deterministic not-in-denial wording');
const vnMain = scenario('베트남', 'ordinary', 'tourism', 'mainland', 30);
ok(vnMain.primary.path.includes('C-3-9') && vnMain.primary.status === 'visa_required', 'VN mainland → C-3-9 visa_required');
ok(vnMain.primary.explanation.join(' ').includes('등재되어 있지 않습니다'), 'VN mainland → deterministic not-listed wording');
const vnBoth = scenario('베트남', 'ordinary', 'tourism', 'jeju_then_mainland', 30);
ok(vnBoth.primary.path.includes('C-3-9') && vnBoth.primary.status === 'visa_required',
  'VN jeju→mainland → resolves to the mainland visa route (C-3-9), not a Jeju-expansion route');
ok(!/체류지역\s*확대허가/.test(vnBoth.primary.path) && !vnBoth.primary.path.includes('제주 무사증 +'),
  'VN jeju→mainland → never offers a "Jeju visa-free + 체류지역 확대허가" path');
ok(vnBoth.primary.explanation.join(' ').includes('원칙적으로 허용되지 않'),
  'VN jeju→mainland → states 체류지역 확대 is not allowed in principle');
ok(vnBoth.alternatives.length === 0,
  'VN jeju→mainland → no speculative "다른 가능성" when the required visa is determined');
const jpBoth = scenario('일본', 'ordinary', 'tourism', 'jeju_then_mainland', 30);
ok(jpBoth.primary.status === 'likely_available' && /B-2-1/.test(jpBoth.primary.path),
  'JP jeju→mainland → general visa-free route (covers the mainland), not Jeju expansion');
ok(jpBoth.primary.explanation.join(' ').includes('체류지역이 제주로 한정되지 않'),
  'JP jeju→mainland → explains general visa-free is nationwide (not limited to Jeju)');
ok(!jpBoth.primary.explanation.join(' ').includes('원칙적으로 허용되지 않'),
  'JP jeju→mainland → does NOT show the B-2-2 expansion-not-allowed note (inapplicable to general visa-free travelers)');
ok(jpBoth.alternatives.length === 0, 'JP jeju→mainland → no speculative "다른 가능성"');
const jpJeju = scenario('일본', 'ordinary', 'tourism', 'jeju_only', 20);
ok(jpJeju.primary.status === 'likely_available' && /B-2-1/.test(jpJeju.primary.path),
  'JP jeju_only → general visa-free primary (B-1/B-2-1 nationals are not B-2-2 targets)');
ok(!/제주 무사증\(B-2-2\) 경로 확인/.test(jpJeju.primary.path),
  'JP jeju_only → B-2-2 is NOT presented as the primary route for general visa-free nationals');
ok(jpJeju.primary.explanation.join(' ').includes('체류지역 확대허가 제약은 적용되지 않'),
  'JP jeju_only → explains B-2-2 Jeju-only/expansion limits do not apply to general visa-free travelers');
const jp = scenario('일본', 'ordinary', 'tourism', 'mainland', 30);
ok(jp.primary.status === 'likely_available' && /B-2-1/.test(jp.primary.path), 'JP mainland → B-2-1 likely_available');
ok(api.formatShortStayWarnings(jp).some(w => w.includes('입국심사관이 결정')), 'JP result carries final-decision warning');
const np = scenario('네팔', 'ordinary', 'tourism', 'jeju_only', 20);
ok(np.primary.status === 'visa_required' && np.primary.explanation.join(' ').includes('목록에 포함되어 있습니다'), 'NP jeju_only → denied, deterministic wording');
const usWork = scenario('미국', 'ordinary', 'work_or_profit', 'mainland', 30);
ok(/C-4/.test(usWork.primary.path), 'work/profit → C-4/official-check path');
const dipl = scenario('베트남', 'diplomatic', 'tourism', 'mainland', 30);
ok(dipl.primary.status === 'needs_official_check', 'non-ordinary passport → needs_official_check');

/* transit (공항 환승만) */
const syTransit = scenario('시리아', 'ordinary', 'transit', 'transit_only', 1);
ok(syTransit.primary.status === 'transit_visa_required' && /C-3-10/.test(syTransit.primary.path),
  'SY ordinary transit_only → 순수환승(C-3-10) 사증 필요');
ok(syTransit.primary.explanation.join(' ').includes('체류기간 0일') || syTransit.primary.explanation.join(' ').includes('0일'),
  'SY transit → states C-3-10 is stay 0 days (not entry)');
ok(syTransit.verdict.tone === 'visa', 'SY transit → visa-tone verdict');
const egDip = scenario('이집트', 'diplomatic', 'transit', 'transit_only', 1);
ok(egDip.primary.status === 'transit_no_visa' && /면제/.test(egDip.primary.path),
  'EG diplomatic transit_only → C-3-10 사증 면제 (no-visa transit)');
ok(egDip.primary.explanation.join(' ').includes('일반여권 소지자는 순수환승(C-3-10) 사증이 필요'),
  'EG diplomatic transit → still notes ordinary passport needs C-3-10');
const yeSpecial = scenario('예멘', 'special', 'transit', 'transit_only', 1);
ok(yeSpecial.primary.status === 'needs_official_check',
  'YE special passport transit_only → official check (manual does not specify)');
const jpTransit = scenario('일본', 'ordinary', 'transit', 'transit_only', 1);
ok(jpTransit.primary.status === 'transit_no_visa', 'JP ordinary transit_only → no-visa airside transit');
ok(jpTransit.primary.explanation.join(' ').includes('입국이 아니므로'),
  'JP transit → explains airside transit is not 입국');
ok(api.formatShortStayWarnings(jpTransit).some(w => /공항 밖으로 나가는 것은 환승이 아니라 입국/.test(w)),
  'transit no-visa carries the "leaving airside = entry" warning');
const vnTransit = scenario('베트남', 'ordinary', 'tourism', 'transit_only', 1);
ok(vnTransit.primary.status === 'transit_no_visa',
  'VN ordinary transit_only → no-visa transit regardless of stated purpose');
ok(vnTransit.sourceRefs.includes('visa_manual_2026_05_b1_b2_c3'),
  'transit answer cites the visa manual as its basis');
/* transit answers must never overclaim entry (positive-guarantee wording only;
   the safety warning "입국을 보장하지 않습니다" must NOT be flagged) */
for (const t of [syTransit, egDip, jpTransit, vnTransit]) {
  const text = JSON.stringify(t.primary) + ' ' + api.formatShortStayWarnings(t).join(' ');
  const bad = [/입국\s*가능합니다/, /이동\s*가능합니다/, /입국(이|을|은)\s*보장(됩|됩니다|합니다)/, /환승(이|을|은)?\s*보장(됩|됩니다|합니다)/].find(g => g.test(text));
  ok(!bad, `${t.country.nameKo} transit answer makes no entry/transit guarantee`, bad && String(bad));
}

/* -------------------------------------------------------------- summary */
console.log(`\n${checks} checks, ${failures} failures`);
if (failures) { process.exit(1); }
console.log('check_short_stay_rules: ALL PASS');
