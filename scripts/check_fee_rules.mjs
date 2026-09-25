/*
 * check_fee_rules.mjs
 * ----------------------------------------------------------------------------
 * Fee registry QA (bundle.fees, authored in scripts/status_guidance/author_rules.py).
 *
 *  - fees are never documents: no `fee` item survives into a document group;
 *  - every amount matches 출입국관리법 시행규칙 제72조 (read 2026-09-22) and cites it;
 *  - the payment instrument follows 제73조: card issue/reissue fees are cash or a
 *    cash-payment receipt (never a revenue stamp); permits are revenue stamp /
 *    card / e-payment;
 *  - online reductions exist only where 제74조 제2항 grants them;
 *  - exemptions are conditional rules with their own source and review state; the
 *    GKS / G-1-99 / F-6 cases from the brief are represented as investigated, not
 *    assumed; the 시간제 취업 regulation-vs-manual disagreement stays a CONFLICT;
 *  - resolution by status / target picks the specific row and shows other cases;
 *  - unknown fees are never invented; rendering shows the amount at a glance.
 *
 *   node scripts/check_fee_rules.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
const rules = JSON.parse(readFileSync(join(ROOT, 'data/guidance-rules-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
const fees = bundle.fees; const byId = Object.fromEntries(fees.map((f) => [f.id, f]));
const INSTR = new Set(rules.enums.payment_instruments); const REVIEW = new Set(rules.enums.fee_review_states); const AMT = new Set(rules.enums.amount_states);

/* schema */
for (const f of fees) {
  check(`fee ${f.id}: schema + sources`, () => {
    assert(bundle.procedures.some((p) => p.id === f.procedure), 'procedure');
    assert(Number.isInteger(f.amount) && f.amount >= 0 && f.currency === 'KRW', 'amount');
    assert(AMT.has(f.amount_state) && REVIEW.has(f.review_state), 'states');
    assert(f.label_ko && f.label_en, 'labels');
    for (const i of f.payment_instruments) assert(INSTR.has(i), `instrument ${i}`);
    assert(bundle.law_sources[f.law], `law ${f.law}`);
    if (f.payment_instruments.length) assert(f.payment_law && bundle.law_sources[f.payment_law], 'payment method must cite 제73조');
    if (f.manual_anchor) assert(Number.isInteger(f.pdf_page), 'manual anchor resolved to a page');
    if (f.amount_state === 'FIXED') assert(f.amount > 0 && f.law_quote.length > 5, 'fixed amount needs a quote');
    for (const ex of f.exemptions) { assert(ex.id && ex.condition_ko && ex.condition_en && REVIEW.has(ex.review_state), `exemption ${ex.id}`); assert((ex.law && bundle.law_sources[ex.law]) || Number.isInteger(ex.pdf_page), `exemption ${ex.id} needs a source`); }
    for (const n of f.not_exempt) assert(n.ko && n.en && (bundle.law_sources[n.law] || Number.isInteger(n.pdf_page)), 'not-exempt note sourced');
    if (f.online_reduction) assert(f.online_reduction.rate === 0.2 && f.online_reduction.law === 'rule_74', 'online reduction cites 제74조 제2항');
    assert(!/수입인지/.test(f.label_ko), 'labels do not casually call every fee a revenue stamp');
  });
}

/* amounts per 시행규칙 제72조 */
const EXPECTED = { extension_general: 60000, extension_f6: 30000, status_change_general: 100000, status_change_f5: 200000, status_grant_general: 80000, status_grant_f6: 40000, activities_outside_status: 120000, workplace_change: 120000, reentry_single: 30000, reentry_multiple: 50000, registration_card: 35000, card_reissue: 35000, part_time_work: 20000 };
check('amounts match 출입국관리법 시행규칙 제72조', () => { for (const [id, amt] of Object.entries(EXPECTED)) assert(byId[id] && byId[id].amount === amt, `${id}: ${byId[id] && byId[id].amount} ≠ ${amt}`); });
check('payment instruments follow 제73조 (card fees: cash / cash receipt, never a revenue stamp)', () => {
  for (const id of ['registration_card', 'card_reissue']) { assert(byId[id].payment_instruments.includes('CASH_OR_CASH_RECEIPT') && !byId[id].payment_instruments.includes('REVENUE_STAMP'), id); }
  for (const id of ['extension_general', 'status_change_general', 'reentry_single']) assert(byId[id].payment_instruments.includes('REVENUE_STAMP'), id);
});
check('fee metadata keeps the statutory 20% reductions granted by 제74조 제2항', () => {
  for (const id of ['extension_general', 'extension_f6', 'status_change_general', 'workplace_change', 'reentry_single', 'reentry_multiple']) assert(byId[id].online_reduction && byId[id].online_reduction.rate === 0.2, id);
  for (const id of ['registration_card', 'card_reissue', 'activities_outside_status', 'status_grant_general']) assert(!byId[id].online_reduction, `${id} must not be reduced online`);
});
check('electronic-service eligibility gates whether the statutory 20% reduction is actually shown', () => {
  const cases = [
    ['extension', 'D-2-1', null, true],
    ['extension', 'D-3', null, false],
    ['extension', 'D-8-1', null, false],
    ['extension', 'E-7-4', null, false],
    ['extension', 'F-2-7', null, false],
    ['extension', 'F-6-1', null, false],
    ['extension', 'G-1-5', null, false],
    ['workplace_change', 'E-9-1', null, true],
    ['workplace_change', 'E-7-4', null, false],
    ['reentry', 'F-6-1', null, true],
    ['status_change', 'D-4-1', 'D-2-1', true],
    ['status_change', 'H-2', 'F-4-24', true],
    ['status_change', 'E-9-1', 'E-7-4', true],
    ['status_change', 'E-10-1', 'E-7-4R', true],
    ['status_change', 'E-7-1', 'F-5-1', false],
  ];
  for (const [procedure, status, target, eligible] of cases) {
    const actual = SG.electronicServiceEligibility(bundle, procedure, status, target);
    assert(actual.eligible === eligible, `${procedure} ${status}→${target || '-'}: ${actual.state}`);
  }
  const f1 = SG.electronicServiceEligibility(bundle, 'extension', 'F-1', null);
  assert(f1.state === 'PARTIAL' && !f1.eligible, 'F-1 is officially partial, so generic F-1 must fail closed');
  assert(!SG.electronicServiceEligibility(bundle, 'status_change', 'D-4-1', null).eligible, 'change target is required');
});
check('exemptions are conditional and sourced: A-1~A-3/D-8; government-invited D-1/D-2/D-4 (conditional, needs review); issuing-error reissue; re-entry within 1 year / F-5 2 years', () => {
  const ext = byId.extension_general;
  assert(ext.exemptions.some((e) => e.id === 'a_series_d8' && e.law === 'rule_74'), 'A/D-8');
  const gov = ext.exemptions.find((e) => e.id === 'gov_invited_study'); assert(gov && gov.program === 'gks' && gov.review_state === 'CONDITIONAL_NEEDS_REVIEW' && gov.evidence_required_ko, 'GKS is conditional, not automatic');
  assert(byId.card_reissue.exemptions.some((e) => e.id === 'issuing_error_reissue' && e.law === 'rule_74'), 'issuing error');
  assert(byId.reentry_single.exemptions.some((e) => e.id === 'reentry_within_1y' && e.law === 'rule_44_2') && byId.reentry_single.exemptions.some((e) => e.id === 'reentry_f5_2y' && e.scope && e.scope.parents.includes('F-5')), 're-entry');
  assert(byId.status_change_general.exemptions.some((e) => e.id === 'gks_status_change_d2' && e.review_state === 'MANUAL_EXPLICIT' && Number.isInteger(e.pdf_page)), 'GKS status-change exemption is manual-explicit with a page');
  assert(ext.exemptions.some((e) => e.id === 'd2_registration_with_extension' && e.scope.parents.includes('D-2') && Number.isInteger(e.pdf_page)), 'D-2 registration+extension exemption');
});
check('card fees are explicitly NOT exempt for scholarship students (manual + 제74조) and the G-1-99 exemption is recorded as not found', () => {
  for (const id of ['registration_card', 'card_reissue']) assert(byId[id].not_exempt.length && /정부초청장학생/.test(byId[id].not_exempt[0].ko) && Number.isInteger(byId[id].not_exempt[0].pdf_page), id);
  const inv = byId.extension_general.investigations.find((i) => i.topic === 'g1_99_exemption'); assert(inv && inv.state === 'NOT_FOUND' && Number.isInteger(inv.pdf_page), 'G-1-99 investigation');
});
check('the 시간제 취업 fee stays a recorded CONFLICT (규칙 2만원 vs 매뉴얼 수수료 면제), never silently reconciled', () => {
  const f = byId.part_time_work; assert(f.amount_state === 'CONFLICT' && f.review_state === 'CONFLICT' && f.conflicts.length === 1 && Number.isInteger(f.pdf_page), 'conflict row');
  assert(/2만원/.test(f.conflicts[0].regulation_ko) && /면제/.test(f.conflicts[0].manual_ko) && f.conflicts[0].interim_ko, 'both values + interim behaviour');
});
check('no-fee and not-listed procedures are stated, not invented', () => {
  assert(byId.registration_info_report.amount_state === 'NO_FEE' && byId.registration_info_report.review_state === 'MANUAL_EXPLICIT' && Number.isInteger(byId.registration_info_report.pdf_page), 'info report: manual says 수수료 없음');
  assert(byId.residence_report.amount_state === 'NOT_LISTED' && byId.residence_report.review_state === 'NEEDS_REVIEW' && byId.residence_report.payment_instruments.length === 0, 'address report: not listed → needs review');
  for (const pid of ['visa_issuance', 'workplace_report', 'program_condition_change']) assert(SG.feesFor(bundle, pid, null, null) === null, `${pid}: no fee row → nothing rendered`);
});

/* resolution */
check('feesFor resolves the specific row by status / target and keeps the others as "other cases"', () => {
  const f61 = SG.feesFor(bundle, 'extension', 'F-6-1', null); assert(f61.primary.length === 1 && f61.primary[0].id === 'extension_f6' && f61.resolvedByStatus && f61.variants.some((v) => v.id === 'extension_general'), 'F-6-1 → 30,000');
  const e7 = SG.feesFor(bundle, 'extension', 'E-7-4', null); assert(e7.primary[0].id === 'extension_general' && !e7.variants.some((v) => v.id === 'extension_f6'), 'E-7-4 → general, F-6 row not offered');
  const unknown = SG.feesFor(bundle, 'extension', null, null); assert(unknown.primary[0].id === 'extension_general' && unknown.variants.some((v) => v.id === 'extension_f6'), 'unknown status → general + F-6 as a variant');
  const f5 = SG.feesFor(bundle, 'status_change', 'E-7', 'F-5'); assert(f5.primary[0].id === 'status_change_f5', 'to F-5 → 200,000');
  const re = SG.feesFor(bundle, 'reentry', 'D-2', null); assert(re.primary.length === 2, 'single + multiple');
  assert(SG.exemptionApplies(byId.extension_general.exemptions.find((e) => e.id === 'd2_registration_with_extension'), 'D-2-1', null) === true, 'D-2 scope');
  assert(SG.exemptionApplies(byId.extension_general.exemptions.find((e) => e.id === 'd2_registration_with_extension'), 'E-7', null) === false, 'E-7 excluded from the D-2 exemption');
});

/* rendering */
function render(q, answers = {}, lang = 'ko') { const interp = SG.interpret(q, bundle); const state = { interp, answers, procedure: null, status: null, history: [], lang, query: q }; const step = SG.nextStep(state, bundle); return { step, ...SG.renderModel(step, state, bundle) }; }
check('fees are separate from documents in every rendered answer', () => {
  for (const [q, a] of [['F-6-1 연장', { f61_phase: 'normal' }], ['E-9-1 연장', {}], ['D-2 외국인등록', {}], ['외국인등록증 재발급', {}], ['F-2-7 연장', {}]]) {
    const r = render(q, a); assert(r.step.kind === 'resolved' || r.step.kind === 'procedure', `${q}: ${r.step.kind}`);
    assert(!r.model.documentGroups.some((g) => g.items.some((d) => d.ref === 'fee' || d.name_ko === '수수료')), `${q}: fee inside documents`);
    assert(r.html.includes('class="sg-fee"') && r.html.includes('sg-fee-amount'), `${q}: fee section`);
  }
});
check('F-6-1 extension shows ₩30,000 but never advertises the unavailable online reduction', () => {
  const r = render('F-6-1 연장', { f61_phase: 'normal' }); const fee = r.html.split('class="sg-fee"')[1];
  assert(fee.includes('₩30,000') && fee.includes('정부수입인지') && fee.includes('시행규칙 기준') && fee.includes('₩60,000'), 'fee block');
  assert(!fee.includes('온라인 신청 시 20% 감경') && fee.includes('전자민원 대상이 아니어서'), 'F-6 online reduction must be suppressed');
  assert(SG.feeSummary('ko', r.model) === '₩30,000', 'summary');
  assert(!r.html.includes('6만원 (결혼이민 F-6: 3만원)'), 'no unresolved table string');
});
check('eligible D-2 extension keeps the 20% reduction while G-1 does not', () => {
  const d2 = render('D-2-1 연장'); assert(d2.html.includes('온라인 신청 시 20% 감경'), 'D-2 should show online reduction');
  const g1 = render('G-1-5 연장'); assert(!g1.html.includes('온라인 신청 시 20% 감경') && g1.html.includes('전자민원 대상이 아니어서'), 'G-1 should not show online reduction');
});
check('card reissue shows ₩35,000, cash/receipt, not-exempt note, and no online reduction', () => {
  const r = render('외국인등록증 재발급'); const fee = r.html.split('class="sg-fee"')[1];
  assert(fee.includes('₩35,000') && fee.includes('현금 또는 현금 납입 증표') && !fee.includes('정부수입인지') && !fee.includes('20%') && fee.includes('정부초청장학생'), fee.slice(0, 200));
});
check('D-2 part-time shows both values and 확인 필요 instead of picking one', () => {
  const r = render('D-2 아르바이트'); const fee = r.html.split('class="sg-fee"')[1];
  assert(fee.includes('₩20,000') && fee.includes('확인 필요') && fee.includes('수수료 면제'), 'conflict rendering');
});
check('no fee section for procedures without a fee row; no-fee procedures say 수수료 없음; GKS highlights the conditional exemption', () => {
  const info = render('외국인등록사항 변경'); assert(info.html.split('class="sg-fee"')[1].includes('수수료 없음'), 'no fee');
  const g = render('GKS 장학생 D-2 연장'); const fee = g.html.split('class="sg-fee"')[1]; assert(fee.includes('sg-fee-hi') && fee.includes('조건부 · 확인 필요'), 'GKS highlight');
  const en = render('F-6-1 연장', { f61_phase: 'normal' }, 'en'); assert(en.html.includes('Cost / payment') && en.html.includes('Government revenue stamp'), 'EN copy');
  for (const s of ['REVENUE_STAMP', 'VERIFIED_REGULATION', 'CASH_OR_CASH_RECEIPT']) assert(!en.html.includes(s) && !g.html.includes(s), `enum ${s} leaked`);
});

console.log('[check_fee_rules] report', JSON.stringify({ fees: fees.length, verified: fees.filter((f) => f.review_state === 'VERIFIED_REGULATION').length, manual_explicit: fees.filter((f) => f.review_state === 'MANUAL_EXPLICIT').length, conflict: fees.filter((f) => f.review_state === 'CONFLICT').length, needs_review: fees.filter((f) => f.review_state === 'NEEDS_REVIEW').length, exemptions: fees.reduce((n, f) => n + f.exemptions.length, 0) }));
if (failures.length) { console.error(`[check_fee_rules] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_fee_rules] OK — ${passed} checks passed`);
