/*
 * check_local_practice.mjs
 * ----------------------------------------------------------------------------
 * Local-office variation layer QA (data/local-practice-202609.json, the router's
 * office extraction, the guidance renderer and the report contract).
 *
 *  - the truth layers and moderation states exist and every variation uses them;
 *  - an unverified/reviewed user report can never carry an official source or
 *    generalise; verified practice needs ≥2 corroborated reports; official local
 *    guidance needs an official source;
 *  - the Jeju F-6-1 case is stored as an UNVERIFIED_USER_REPORT and rendered
 *    with that label while the national baseline document stays required;
 *  - offices are recognised from queries (Korean and Latin), never inferred;
 *  - stale reports are relabelled; the report schema/API reject identifiers.
 *
 *   node scripts/check_local_practice.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const lp = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));
const schema = JSON.parse(readFileSync(join(ROOT, 'data/schemas/local_practice_report.schema.json'), 'utf8'));
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = lp;
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/waymaker-quick-answer.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance; const R = globalThis.VisableSearchRouter;
const reportApi = require(join(ROOT, 'api/local-practice/report.js'));
const reportClient = require(join(ROOT, 'assets/js/local-practice-report.js'));

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

const LAYERS = ['NATIONAL_OFFICIAL_BASELINE', 'OFFICIAL_LOCAL_GUIDANCE', 'VERIFIED_LOCAL_PRACTICE', 'REVIEWED_USER_REPORT', 'UNVERIFIED_USER_REPORT', 'CONFLICTING_REPORTS', 'STALE_REPORT', 'UNKNOWN'];
const MOD = ['SUBMITTED', 'UNDER_REVIEW', 'REVIEWED', 'CORROBORATED', 'CONFLICTING', 'REJECTED', 'STALE'];
check('truth layers, moderation states and promotion rule are declared', () => {
  assert(LAYERS.every((l) => lp.truth_layers.some((x) => x.id === l && x.ko && x.en)), 'layers');
  assert(MOD.every((m) => lp.moderation_states.includes(m)), 'moderation');
  assert(lp.promotion_rule_ko && lp.promotion_rule_en && /2건|two/i.test(lp.promotion_rule_ko + lp.promotion_rule_en), 'promotion rule requires corroboration');
  assert(Number.isInteger(lp.stale_after_days) && lp.stale_after_days > 0, 'stale window');
});
check('offices are unique, aliased and cover the jurisdiction directory', () => {
  const ids = new Set(); for (const o of lp.offices) { assert(!ids.has(o.id), `dup ${o.id}`); ids.add(o.id); assert(o.name_ko && o.name_en && o.aliases.length >= 2, o.id); }
  assert(ids.has('jeju') && ids.has('seoul') && ids.has('seoul-southern') && ids.has('suwon') && lp.offices.length >= 20, 'coverage');
});
for (const v of lp.variations) {
  check(`variation ${v.id}: layered, sourced honestly, never generalised`, () => {
    assert(lp.offices.some((o) => o.id === v.office), 'office');
    assert(bundle.procedures.some((p) => p.id === v.procedure), 'procedure');
    assert(LAYERS.includes(v.layer) && MOD.includes(v.moderation), 'layer/moderation');
    assert(v.summary_ko && v.summary_en && v.detail_ko && v.detail_en && v.national_baseline_ko && v.national_baseline_en, 'bilingual text + baseline');
    if (/USER_REPORT|CONFLICTING|STALE/.test(v.layer)) { assert(v.official_source === null, 'a report must not claim an official source'); assert(v.do_not_generalize === true, 'reports never generalise'); assert(v.moderation !== 'CORROBORATED' || v.layer !== 'UNVERIFIED_USER_REPORT', 'corroborated ≠ unverified'); }
    if (v.layer === 'VERIFIED_LOCAL_PRACTICE') assert(v.report_count >= 2 && v.moderation === 'CORROBORATED', 'verified practice needs ≥2 corroborated reports');
    if (v.layer === 'OFFICIAL_LOCAL_GUIDANCE') assert(v.official_source && /^https:\/\//.test(v.official_source), 'official guidance needs an official source');
    assert(!/필요 없음|필요없|not required|no need/i.test(v.summary_ko + v.summary_en) || v.layer === 'OFFICIAL_LOCAL_GUIDANCE', 'no categorical "not required" wording without an official source');
  });
}
check('the Jeju F-6-1 residence-proof case is an unverified report, not policy', () => {
  const j = lp.variations.find((v) => v.id === 'jeju-f6-1-extension-residence-proof');
  assert(j && j.layer === 'UNVERIFIED_USER_REPORT' && j.moderation === 'UNDER_REVIEW' && j.official_source === null && j.do_not_generalize === true && j.report_count === 1, JSON.stringify(j && [j.layer, j.moderation]));
  assert(/체류지 입증서류/.test(j.national_baseline_ko), 'baseline names the document');
});

/* router */
check('offices are recognised from Korean and Latin aliases and never invented', () => {
  const office = (q) => (R.route(q, bundle, { localPractice: lp }).office || {}).id || null;
  assert(office('제주에서 F-6-1 연장') === 'jeju' && office('Jeju F-6-1 extension') === 'jeju' && office('수원 D-2 연장') === 'suwon' && office('서울남부 E-7 연장') === 'seoul-southern' && office('서울 출입국 연장') === 'seoul', 'aliases');
  assert(office('D-2 연장') === null && office('F-6 연장') === null && office('jejudo weather') === null, 'no office invented');
});

/* model + rendering */
function run(q, answers = {}, office = null, lang = 'ko') { const interp = SG.interpret(q, bundle); const state = { interp, answers, procedure: null, status: null, history: [], lang, query: q, office }; const step = SG.nextStep(state, bundle); return { step, ...SG.renderModel(step, state, bundle) }; }
check('Jeju F-6-1 extension: baseline document still required; report shown as an unverified report with its date state', () => {
  const r = run('제주에서 F-6-1 연장할 때 체류지입증서류 필요해?', { f61_phase: 'normal' });
  assert(r.step.kind === 'resolved', r.step.kind);
  assert(r.model.localPractice.office && r.model.localPractice.office.id === 'jeju' && r.model.localPractice.variations.length === 1 && r.model.localPractice.variations[0].effectiveLayer === 'UNVERIFIED_USER_REPORT', 'variation attached');
  const req = r.model.documentGroups.find((g) => g.key === 'required'); assert(req && req.items.some((d) => d.ref === 'residence_proof'), 'national baseline still lists proof of residence as required');
  assert(r.html.includes('확인되지 않은 이용자 제보') && r.html.includes('전국 기준을 바꾸는 정보가 아니에요') && r.html.includes('아직 확인되지 않음'), 'labels');
  assert(!r.html.includes('필요 없음'), 'never renders the premise as fact');
  assert(r.model.quick && r.model.quick.localPractice.office.id === 'jeju' && r.model.quick.uncertainties.some((u) => u.id === 'local'), 'Quick Answer carries the office + uncertainty');
});
check('no office → national baseline + picker; another office → no differences on record', () => {
  const none = run('F-6-1 연장', { f61_phase: 'normal' }); assert(none.model.localPractice.office === null && none.model.localPractice.variations.length === 0 && none.html.includes('data-sg-office') && none.html.includes('관할 관서별로 실제 요구 서류나 절차가 조금 다를 수 있어요'), 'picker');
  const seoul = run('F-6-1 연장', { f61_phase: 'normal' }, 'seoul'); assert(seoul.model.localPractice.variations.length === 0 && seoul.html.includes('확인된 차이 정보가 없어요'), 'seoul');
  const other = run('제주 D-2 연장'); assert(other.model.localPractice.office.id === 'jeju' && other.model.localPractice.variations.length === 0, 'Jeju report does not leak to other statuses');
});
check('stale reports are relabelled STALE_REPORT', () => {
  const clone = JSON.parse(JSON.stringify(bundle)); clone.local_practice = JSON.parse(JSON.stringify(lp));
  clone.local_practice.variations[0].last_checked = '2020-01-01';
  const m = SG.localPracticeFor(clone, { office: 'jeju', interp: { office: null } }, 'extension', 'F-6-1');
  assert(m.variations[0].effectiveLayer === 'STALE_REPORT', m.variations[0].effectiveLayer);
});
check('report button and follow-up context are present; nothing collects identifiers', () => {
  const r = run('F-6-1 연장', { f61_phase: 'normal' }, 'jeju');
  assert(r.html.includes('data-sg-action="report"'), 'report CTA');
  const props = Object.keys(schema.properties); for (const bad of ['passport_number', 'arc_number', 'resident_registration_number', 'case_number', 'full_name', 'name', 'email', 'phone']) assert(!props.includes(bad), `schema collects ${bad}`);
  assert(schema.properties.consent.const === true && schema['x-forbidden-patterns'].patterns.length >= 3, 'consent + privacy patterns');
});
check('report validation (API + client) accepts a clean report and rejects identifiers / missing consent / empty outcome', () => {
  const ok = reportApi.validateReport({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', status: 'F-6-1', outcome: { document_expected_not_requested: ['체류지 입증서류'] }, consent: true });
  assert(ok.ok, JSON.stringify(ok.errors));
  assert(reportApi.validateReport({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', notes: 'ARC 900101-5123456', consent: true }).errors.includes('identifier_pattern'), 'ARC number');
  assert(reportApi.validateReport({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', notes: 'passport M12345678', consent: true }).errors.includes('identifier_pattern'), 'passport number');
  assert(reportApi.validateReport({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', notes: 'x', consent: false }).errors.includes('consent'), 'consent');
  assert(reportApi.validateReport({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', consent: true }).errors.includes('outcome'), 'empty outcome');
  const c = reportClient.validate({ office: 'jeju', visit_month: '2026-09', procedure: 'extension', outcome: { document_expected_not_requested: [], document_requested_not_expected: [], fee_difference: null, process_difference: null }, notes: '1234-5678-9012', consent: true }, 'ko');
  assert(c.some((e) => /여권번호/.test(e)), 'client identifier guard');
});
check('the report API is honest when no intake is configured', async () => {
  delete process.env.LOCAL_PRACTICE_REPORTS_WEBHOOK_URL;
  const res = { headers: {}, code: null, body: null, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
  await reportApi({ method: 'POST', body: { office: 'jeju', visit_month: '2026-09', procedure: 'extension', outcome: { fee_difference: 'x' }, consent: true } }, res);
  assert(res.code === 503 && res.body.status === 'NOT_CONFIGURED' && res.body.ok === false, JSON.stringify([res.code, res.body]));
  const get = { headers: {}, code: null, body: null, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
  await reportApi({ method: 'GET' }, get); assert(get.body.persistence === 'none', 'GET reports no persistence');
});

await new Promise((r) => setTimeout(r, 50));
console.log('[check_local_practice] report', JSON.stringify({ offices: lp.offices.length, variations: lp.variations.length, layers: lp.variations.map((v) => v.layer) }));
if (failures.length) { console.error(`[check_local_practice] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_local_practice] OK — ${passed} checks passed`);
