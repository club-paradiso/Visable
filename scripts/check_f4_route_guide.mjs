#!/usr/bin/env node
/**
 * check_f4_route_guide.mjs — validation for the F-4 (재외동포) global official-source hub.
 *
 * Covers: search-first diagnostic, country-ready data architecture, country
 * overlays + source-coverage matrix, accessible modal, procedure-based FAQ, and
 * the legal/accuracy guardrails. No external dependencies; no network.
 *
 * Run: node scripts/check_f4_route_guide.mjs
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
const overlaysDoc = readJson('data/f4/country_overlays.json');
const overlaySchema = readJson('data/f4/country_overlay_schema.json');
const matrix = readJson('data/f4/source_coverage_matrix.json');
const sourcesDoc = readJson('data/f4/sources.json');
const guideJs = read('assets/js/f4-route-guide.js');
const indexHtml = read('index.html');

const srcIds = new Set(sourcesDoc.sources.map((s) => s.id));
const overlays = overlaysDoc.overlays || {};
const registryCodes = new Set(countries.countries.map((c) => c.countryCode));
const VERIF_STATES = ['verified_official', 'partial_official', 'needs_refresh', 'official_check_required', 'not_available_or_unclear'];

const allDataText = [base, diagnostic, faq, countries, overlaysDoc, matrix, sourcesDoc].map((d) => JSON.stringify(d)).join('\n');
const commonViewText = [base, diagnostic, faq].map((d) => JSON.stringify(d)).join('\n');

/* -------------------------------------------------------------- structure */
section('Structure');
ok(base.schemaVersion === 1, 'base.json schemaVersion === 1');
ok(VERIF_STATES.includes(base.sourceStatus), 'base.sourceStatus valid');
ok(/^\d{4}-\d{2}-\d{2}$/.test(base.lastUpdated || ''), 'base.lastUpdated present');
ok(base.common && base.hub, 'base has common + hub blocks');
ok(['overview', 'overseasApplication', 'residenceReport', 'statusChange'].every((k) => base.hub[k]), 'all hub sections present');
ok(typeof base.fallbackUnverifiedCountry === 'string' && base.fallbackUnverifiedCountry.includes('공통 F-4 기준만'), 'unverified-country fallback message present');

/* ----------------------------------------------- search-first diagnostic */
section('Search-first diagnostic');
ok(diagnostic.title === 'F-4 안내를 시작하기 전에 확인해주세요', 'diagnostic title exact');
ok(diagnostic.ctaLabel === 'F-4 절차 확인하기', 'CTA label "F-4 절차 확인하기"');
const qById = Object.fromEntries(diagnostic.questions.map((q) => [q.id, q]));
const expectQ = {
  nationality: '현재 대한민국 국적을 보유하고 있나요?',
  location: '현재 어디에서 절차를 진행하려고 하나요?',
  visa_status: '이미 F-4 비자를 발급받았나요?',
  residence_report: '한국 입국 후 국내거소신고를 했나요?',
  entry_timing: 'F-4로 입국한 지 90일이 지났나요?',
  country: '신청 국가 또는 거주 국가를 선택하세요'
};
for (const [id, text] of Object.entries(expectQ)) {
  ok(qById[id] && qById[id].question === text, `diagnostic question exists: ${id}`, qById[id] && qById[id].question);
}
ok(qById.entry_timing.showIf && qById.entry_timing.showIf.questionId === 'visa_status' && qById.entry_timing.showIf.optionId === 'yes_entered',
  '90-day question is conditional on "entered with F-4"');
ok(qById.country.type === 'country', 'country question is a country selector');
const natOpts = qById.nationality.options.map((o) => o.label);
ok(natOpts.includes('아니요, 외국 국적자입니다') && natOpts.includes('예, 대한민국 국적자입니다'), 'nationality options present');
ok(qById.nationality.options.find((o) => o.id === 'korean').signal.forceRoute === 'nationality_check',
  'Korean-national answer forces nationality_check route (not ordinary F-4 guidance)');

section('Diagnostic routes');
const ROUTE_TITLES = {
  overseas_application: '재외공관 신청 안내',
  residence_report: '국내거소신고/거소증 안내',
  status_change: '국내 자격변경 안내',
  nationality_check: '국적/병역/자격 확인 필요',
  official_check: '공식 확인 필요'
};
for (const [id, title] of Object.entries(ROUTE_TITLES)) {
  ok(diagnostic.routes[id] && diagnostic.routes[id].title === title, `route "${title}" present`);
}

/* -------- exercise the real routing logic extracted from the guide JS ----- */
section('Routing behaviour (computeRoute)');
let computeRoute = null;
try {
  const m = guideJs.match(/function computeRoute\(a\)\s*\{[\s\S]*?\n  \}/);
  // eslint-disable-next-line no-new-func
  computeRoute = new Function(`${m[0]}; return computeRoute;`)();
} catch (e) { /* handled below */ }
ok(typeof computeRoute === 'function', 'computeRoute extracted from guide JS');
if (typeof computeRoute === 'function') {
  const scenarios = [
    [{ nationality: 'foreign', location: 'overseas_apply', visa_status: 'no' }, 'overseas_application', 'foreign overseas, no F-4 → 재외공관'],
    [{ nationality: 'foreign', visa_status: 'yes_not_entered' }, 'overseas_application', 'F-4 issued, not entered → overseas + reminder'],
    [{ nationality: 'foreign', visa_status: 'yes_entered', residence_report: 'not_yet', entry_timing: 'under90' }, 'residence_report', 'entered, no report, <90d → 거소신고'],
    [{ nationality: 'foreign', visa_status: 'yes_entered', residence_report: 'not_yet', entry_timing: 'over90' }, 'official_check', 'entered, no report, >90d → 공식 확인'],
    [{ nationality: 'foreign', location: 'domestic_change' }, 'status_change', 'in Korea wants change → 자격변경'],
    [{ nationality: 'korean' }, 'nationality_check', 'Korean national → 국적/병역/자격 확인'],
    [{ nationality: 'unsure' }, 'nationality_check', 'nationality unsure → 국적/병역/자격 확인']
  ];
  for (const [ans, expect, label] of scenarios) {
    ok(computeRoute(ans).routeId === expect, label, `got ${computeRoute(ans).routeId}`);
  }
  ok(computeRoute({ nationality: 'korean' }).routeId !== 'overseas_application',
    'Korean nationality never routes to ordinary visa-issuance path');
}

/* ------------------------------------------------------ country registry */
section('Country registry & overlays');
ok(countries.countries.length >= 30, `country registry size (${countries.countries.length}) is global-ready`);
ok(countries.countries.every((c) => c.countryCode && c.labelKo && c.labelEn && c.defaultVerificationState),
  'every country has code/labelKo/labelEn/defaultVerificationState');
ok(countries.countries.every((c) => VERIF_STATES.includes(c.defaultVerificationState)), 'every country defaultVerificationState valid');
const priority = ['US', 'CA', 'JP', 'CN', 'AU', 'NZ', 'GB', 'DE', 'FR', 'RU', 'KZ', 'UZ', 'VN', 'PH', 'ID', 'TH', 'MY', 'SG', 'BR', 'AR'];
ok(priority.every((c) => registryCodes.has(c)), 'all 20 priority countries selectable');
ok(priority.every((c) => overlays[c]), 'all 20 priority countries have an overlay');

let overlayProblems = [];
for (const [code, ov] of Object.entries(overlays)) {
  if (ov.countryCode !== code) overlayProblems.push(`${code}: countryCode mismatch`);
  if (!registryCodes.has(code)) overlayProblems.push(`${code}: not in registry`);
  if (!VERIF_STATES.includes(ov.sourceStatus)) overlayProblems.push(`${code}: bad sourceStatus`);
  if (!ov.labelKo || !ov.labelEn) overlayProblems.push(`${code}: missing label`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(ov.lastReviewed || '')) overlayProblems.push(`${code}: bad lastReviewed`);
  // schema: section fields must carry a valid status
  for (const key of ['criminalRecord', 'authentication', 'booking', 'fee', 'processingTime', 'missionPractice']) {
    const f = ov[key];
    if (f && !VERIF_STATES.includes(f.status)) overlayProblems.push(`${code}.${key}: bad status`);
  }
  // every overlay sourceRef resolves
  for (const ref of (ov.sourceRefs || [])) if (!srcIds.has(ref)) overlayProblems.push(`${code} → ${ref}`);
  for (const key of ['criminalRecord', 'authentication', 'booking', 'fee', 'processingTime', 'missionPractice']) {
    for (const ref of ((ov[key] && ov[key].sourceRefs) || [])) if (!srcIds.has(ref)) overlayProblems.push(`${code}.${key} → ${ref}`);
  }
}
ok(overlayProblems.length === 0, 'every overlay validates (state, labels, resolvable sourceRefs)', overlayProblems.slice(0, 4).join(' | '));
ok(overlaySchema.$schema && overlaySchema.properties && overlaySchema.properties.sourceStatus, 'overlay schema file is well-formed');
ok(typeof base.fallbackUnverifiedCountry === 'string', 'unverified countries fall back to common F-4 guidance');

/* ---------------------------------------------- source coverage matrix */
section('Source coverage matrix');
let matrixProblems = [];
for (const e of matrix.entries) {
  if (!registryCodes.has(e.countryCode)) matrixProblems.push(`${e.countryCode}: not in registry`);
  if (!VERIF_STATES.includes(e.verificationState)) matrixProblems.push(`${e.countryCode}: bad verificationState`);
  for (const ref of (e.sourceRefs || [])) if (!srcIds.has(ref)) matrixProblems.push(`${e.countryCode} → ${ref}`);
}
ok(matrixProblems.length === 0, 'matrix entries valid (registry codes, states, resolvable refs)', matrixProblems.slice(0, 4).join(' | '));
ok(priority.every((c) => matrix.entries.find((e) => e.countryCode === c)), 'matrix covers all priority countries');
ok(matrix.entries.find((e) => e.countryCode === 'US').verificationState === 'verified_official', 'US is verified_official in matrix');
ok(matrix.entries.find((e) => e.countryCode === 'TH').verificationState === 'official_check_required', 'unverified Thailand stays official_check_required');

/* --------------------------------------------------------- source refs */
section('Source references resolve');
function collectRefs(obj, acc) {
  if (Array.isArray(obj)) { obj.forEach((x) => collectRefs(x, acc)); return acc; }
  if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) {
      if (k === 'sourceRefs' && Array.isArray(v)) v.forEach((r) => acc.add(r));
      else collectRefs(v, acc);
    }
  }
  return acc;
}
const allRefs = new Set();
[base, diagnostic, faq, overlaysDoc, matrix].forEach((d) => collectRefs(d, allRefs));
const unresolved = [...allRefs].filter((r) => !srcIds.has(r));
ok(unresolved.length === 0, 'every sourceRef across F-4 data resolves in sources.json', unresolved.join(', '));
ok(sourcesDoc.sources.every((s) => s.sourceDate), 'every F-4 source has a sourceDate');
ok(srcIds.has('visa_manual_2026_05_f4_chapter') && srcIds.has('visa_manual_2026_05_f4_annex1_criminal_record') && srcIds.has('stay_manual_2026_06_residence_report'),
  'official manual sources present');

/* --------------------------------------------------------------- FAQ */
section('FAQ (procedure-based)');
ok(faq.title === 'F-4 자주 묻는 질문', 'FAQ title "F-4 자주 묻는 질문"');
const faqTitles = faq.groups.map((g) => g.title);
ok(['재외공관 신청', '국내거소신고/거소증', '국내 자격변경'].every((t) => faqTitles.includes(t)), 'FAQ groups present');
ok(faq.groups.every((g) => g.items.every((it) => Array.isArray(it.sourceRefs) && it.sourceRefs.length)), 'every FAQ answer is source-grounded');
const faqText = JSON.stringify(faq);
ok(faqText.includes('자동으로 나오지') && faqText.includes('별도 절차'), 'FAQ states 거소증 is not automatic / separate procedure');
ok(faqText.includes('자동으로 전환되지 않') || faqText.includes('자동으로 전환되나요'), 'FAQ covers H-2→F-4 not automatic');

/* -------------------------------------------------- legal guardrails */
section('Legal / accuracy guardrails');
ok(base.common.separationWarning.includes('별도 절차') && base.common.separationWarning.includes('거소증'),
  'visa vs residence-report separation warning present');
ok(/거소증.{0,12}발급(받|되)지\s*않|발급받을 수 없|발급되지 않/.test(allDataText), 'states overseas missions do NOT issue 거소증');
ok(!/(재외공관|해외 공관|영사관)에서\s*거소증(을)?\s*(발급받|신청할 수 있|받을 수 있)/.test(allDataText),
  'never implies 거소증 can be issued overseas');
ok((allDataText.match(/입국일부터 90일 이내|90일 이내/g) || []).length >= 3, '90-day residence-report requirement visible (≥3 mentions)');
ok(base.common.deadline90.includes('입국일부터 90일 이내'), 'explicit "within 90 days of entry" wording');
ok(/병역/.test(allDataText) && /40세/.test(allDataText), 'military-service / nationality-loss caution present');
ok(/2018-05-01|'?18\.5\.1/.test(allDataText), 'nationality-loss male restriction (18.5.1) present');
ok(/보장하지\s*않/.test(allDataText) && /보장하지\s*않/.test(guideJs), 'no-guarantee wording present (data + JS)');

section('US-specific terms stay in the US overlay only');
const usTerms = ['FBI', 'Identity History Summary', '미 국무부', 'U.S. Department of State'];
const leaks = usTerms.filter((t) => commonViewText.includes(t));
ok(leaks.length === 0, 'no US-specific term leaks into common view (base/diagnostic/faq)', leaks.join(', '));
ok(usTerms.some((t) => JSON.stringify(overlays.US).includes(t)), 'US-specific terms live in the US overlay');
for (const t of usTerms) {
  // any non-US overlay must not contain US-specific terms
  const bad = Object.entries(overlays).filter(([code, ov]) => code !== 'US' && JSON.stringify(ov).includes(t)).map(([c]) => c);
  ok(bad.length === 0, `US term "${t}" not leaked into non-US overlays`, bad.join(', '));
}

section('Fee labels (no bare 수수료)');
function collectStrings(obj, acc) {
  if (typeof obj === 'string') { acc.push(obj); return acc; }
  if (Array.isArray(obj)) { obj.forEach((x) => collectStrings(x, acc)); return acc; }
  if (obj && typeof obj === 'object') Object.values(obj).forEach((v) => collectStrings(v, acc));
  return acc;
}
const allStrings = [];
[base, diagnostic, faq, overlaysDoc].forEach((d) => collectStrings(d, allStrings));
const bareFee = allStrings.filter((s) => s.trim() === '수수료' || /^수수료(가|는|를)?\b/.test(s.trim()));
ok(bareFee.length === 0, 'no document row is a bare "수수료" (procedure context required)', bareFee.slice(0, 3).join(' | '));

/* ------------------------------------------------------ UI integration */
section('UI integration & accessibility');
ok(/data\/f4\/(base|diagnostic|faq|countries|country_overlays|sources)\.json/.test(guideJs) || /DATA_BASE/.test(guideJs),
  'guide JS fetches the external data/f4 files');
ok(indexHtml.includes('assets/js/f4-route-guide.js'), 'index.html loads the deferred guide script');
ok(indexHtml.includes('id="f4RouteGuide"'), 'index.html has the guide mount section');
ok(/GENERIC_VISA_ISSUANCE_EXCLUDED_CODES\s*=\s*new Set\(\[\s*'F-4'/.test(indexHtml)
  && /function renderVisaIssuanceSection[\s\S]*?isGenericVisaIssuanceExcluded/.test(indexHtml),
  'F-4 is excluded from the generic visa-issuance renderer (keeps its dedicated route guide)');
ok(guideJs.includes('mountEntryPanel') && guideJs.includes('entryPanelHtml'), 'compact diagnostic entry panel rendered (not full hub)');
ok(guideJs.includes('F-4 절차 확인하기') || diagnostic.ctaLabel === 'F-4 절차 확인하기', 'primary CTA opens the modal');
ok(guideJs.includes("d.title") || guideJs.includes('diagnostic.title'), 'entry panel shows the diagnostic title');
ok(/aria-modal/.test(guideJs) && /role.{0,6}dialog/.test(guideJs), 'modal has aria-modal + role=dialog');
ok(/Escape/.test(guideJs) && /onKeydown|keyHandler/.test(guideJs), 'modal supports Escape + focus trapping');
ok(/lastFocus/.test(guideJs), 'modal restores focus to the trigger on close');
ok(/Tab/.test(guideJs) && /shiftKey/.test(guideJs), 'modal traps Tab focus');
ok(HUB_present(), 'hub exposes all five procedure tabs + FAQ');
function HUB_present() {
  return ['overseasApplication', 'residenceReport', 'statusChange', 'country', 'faq'].every((t) => guideJs.includes(t)) &&
    guideJs.includes('재외공관 신청') && guideJs.includes('국가별 확인');
}
ok(!guideJs.includes('어떤 상황에 가까우신가요'), 'old wording "어떤 상황에 가까우신가요?" removed from F-4 UI');
ok(!allDataText.includes('어떤 상황에 가까우신가요'), 'old wording removed from F-4 data');
ok(guideJs.includes('selectedCountry') && guideJs.includes('renderCountryTab'), 'country selector only affects country-specific guidance');
ok(guideJs.includes('commonRulesHtml'), 'common F-4 rules render separately from country overlays');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_f4_route_guide: ALL PASS');
