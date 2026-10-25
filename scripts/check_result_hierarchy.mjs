/*
 * check_result_hierarchy.mjs
 * ----------------------------------------------------------------------------
 * Search result hierarchy (assets/js/status-guidance.js renderModel), pre-launch
 * rescue 2026-10-24. The page a person reads after a search must:
 *
 *  1. open with the answer identity, then an "at a glance" overview that is
 *     DERIVED from the composed model and separates confirmed facts, case-
 *     dependent items and what must be read in the source;
 *  2. present a special scheme attached to a status (동포 통합 제도 on F-4) as a
 *     collapsed, explicitly conditional block AFTER the general answer — never
 *     as a universal rule above the fee;
 *  3. offer only the fee exemptions whose rule names the person's status;
 *  4. list the procedure's own sources first and keep fee law behind a disclosure;
 *  5. lead a source-only answer with its manual page as the primary action;
 *  6. render next actions as labelled rows, and name the current edition
 *     (never a hard-coded "September") in review notices.
 *
 *   node scripts/check_result_hierarchy.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
function run(query, lang = 'ko', answers = {}) {
  const interp = SG.interpret(query, bundle);
  const state = { query, interp, answers: { ...answers }, procedure: null, status: null, history: [], lang };
  const step = SG.nextStep(state, bundle);
  const out = SG.renderModel(step, state, bundle);
  return { step, ...out, text: out.html.replace(/<[^>]+>/g, ' ') };
}
const at = (html, needle) => { const i = html.indexOf(needle); assert(i >= 0, `missing: ${needle}`); return i; };
const ordered = (html, ...needles) => { let last = -1; for (const n of needles) { const i = at(html, n); assert(i > last, `${n} must come after ${needles[needles.indexOf(n) - 1]}`); last = i; } };
const count = (html, re) => (html.match(re) || []).length;

check('F-4 extension (source-only): identity → source action → overview → fee → scheme → actions → evidence', () => {
  const r = run('F-4 체류기간 연장');
  assert(r.step.kind === 'source-only', r.step.kind);
  ordered(r.html, 'class="sg-answer sg-source-only"', 'sg-btn-source', 'class="sg-overview"', 'class="sg-fee"', 'class="sg-program"', 'class="sg-next"', 'class="sg-evidence"');
  assert(/sg-btn-source" data-sg-action="open-page" data-sg-source="stay_manual_2026_10_19_pdf" data-sg-page="537"/.test(r.html), 'primary action opens the F-4 extension page (537)');
});

check('F-4 overview is derived from the model: fee confirmed, scheme conditional, documents in the source', () => {
  const r = run('F-4 체류기간 연장');
  const ov = r.html.slice(at(r.html, 'class="sg-overview"'), at(r.html, 'class="sg-fee"'));
  ordered(ov, '확인된 내용', '수수료 ₩60,000 · 시행규칙 기준', '조건에 따라 달라요', '외국국적동포 통합 체류제도 (F-4 통합) — 일부 대상자에게만 해당', '원문에서 확인할 내용', '537쪽');
  assert(ov.includes('2026년 10월판 원문은 아직 사람이 대조 검토하지 않았어요'), 'review notice names the current edition');
  assert(ov.includes('기준일 2026-10-23 · 공식 근거 6건'), 'basis line includes the current regulation version date');
  assert(r.html.includes('해당 조문만 대조했습니다. 법령·서식 전체 검증은 아닙니다.'), 'the latest source check must not claim whole-law review');
});

check('the 동포 scheme is a collapsed, conditional disclosure after the fee — never a universal rule', () => {
  const r = run('F-4 체류기간 연장');
  assert(r.html.includes('<details class="sg-program-details"><summary>'), 'collapsed details');
  assert(!/<details class="sg-program-details" open/.test(r.html), 'starts closed');
  assert(r.html.includes('일부 대상자만') && r.html.includes('일부 대상자에게만 적용되는 별도 제도예요'), 'conditional wording');
  assert(!r.text.includes('아래 조건이 추가로 적용돼요'), 'the old universal wording is gone');
  assert(at(r.html, 'class="sg-program"') > at(r.html, 'class="sg-fee"'), 'after the fee');
});

check('fee exemptions are offered only to the statuses their rule names', () => {
  for (const q of ['F-4 체류기간 연장', 'F-5 체류기간 연장']) assert(!run(q).html.includes('면제·감경 조건'), `${q}: no inapplicable exemption list`);
  const e7 = run('E-7 근무처 변경').html;
  const e7fee = e7.slice(at(e7, 'class="sg-fee"'), at(e7, 'class="sg-next"'));
  assert(e7fee.includes('면제·감경 조건 · 1') && e7fee.includes('신고 대상') && !e7fee.includes('외교(A-1)'), 'E-7 keeps only the report-not-permit exemption');
  const d2all = run('D-2 체류기간 연장').html;
  const d2 = d2all.slice(at(d2all, 'class="sg-fee"'), at(d2all, 'class="sg-cond-section"'));
  assert(d2.includes('면제·감경 조건 · 2') && d2.includes('정부초청장학생') && d2.includes('동시에 신청하는 경우'), 'D-2 keeps the government-invited and registration+extension exemptions');
  assert(!d2.includes('외교(A-1)'), 'A-1~A-3/D-8 exemption is not offered to D-2');
  const aSeries = bundle.fees.find((f) => f.id === 'extension_general').exemptions.find((e) => e.id === 'a_series_d8');
  for (const [status, expected] of [['D-8', true], ['D-8-1', true], ['A-1', true], ['A-3', true], ['F-4', false], ['D-2', false], ['E-7', false]]) assert(SG.exemptionApplies(aSeries, status, null) === expected, `A/D-8 exemption for ${status}`);
  const gov = bundle.fees.find((f) => f.id === 'extension_general').exemptions.find((e) => e.id === 'gov_invited_study');
  for (const [status, expected] of [['D-2', true], ['D-2-1', true], ['D-4', true], ['D-1', true], ['F-4', false], ['E-7', false]]) assert(SG.exemptionApplies(gov, status, null) === expected, `government-invited exemption for ${status}`);
});

check('evidence: the procedure page first, fee law behind a disclosure, counts unchanged', () => {
  const r = run('F-4 체류기간 연장');
  const ev = r.html.slice(at(r.html, 'class="sg-evidence"'));
  ordered(ev, '<details class="sg-evidence-details" id="sgEvidence" open>', '이 절차의 공식 안내', 'sg-ev sg-ev-manual sg-ev-primary', '537쪽', '<details class="sg-ev-more"><summary>수수료·법령 근거 5건</summary>');
  assert(count(ev, /<li class="sg-ev /g) === 6, `six evidence items (${count(ev, /<li class="sg-ev /g)})`);
  assert(ev.includes('2026년 10월판 원문은 아직 사람이 한 줄씩') && !r.text.includes('9월판'), 'review notice names the current edition');
  const d2 = run('D-2 체류기간 연장').html;
  assert(!/id="sgEvidence" open/.test(d2), 'structured answers keep the evidence collapsed');
});

check('next actions are labelled rows and every call to action appears once on the page', () => {
  const f4 = run('F-4 체류기간 연장').html;
  const next = f4.slice(at(f4, 'class="sg-next"'), at(f4, 'class="sg-wm"'));
  assert(next.startsWith('class="sg-next"') && next.includes('<ul class="sg-actions">'), 'action list');
  // source-only: the manual page is the answer head's primary button, not repeated as a row;
  // Waymaker follows as its own block, so there is no follow-up row either.
  assert(count(f4, /data-sg-action="open-page" data-sg-source="stay_manual_2026_10_19_pdf" data-sg-page="537"/g) === 2, 'page 537: answer-head button + evidence item only');
  assert(!next.includes('data-sg-action="open-page"') && !next.includes('class="sg-next-ai"'), 'no duplicate source / follow-up rows');
  assert(count(f4, /data-sg-action="followup"/g) === 1, 'one Waymaker call to action');
  assert(count(next, /class="sg-action-body"/g) === 4, `four rows with a body (${count(next, /class="sg-action-body"/g)})`);
  for (const s of ['data-action="open-hikorea-guide"', 'href="form-helper.html"', 'href="tel:1345"', 'data-sg-action="legacy-card"']) assert(next.includes(s), s);
  assert(!next.includes('sg-action-primary'), 'no primary row when the head already carries the primary action');
  const d2 = run('D-2 체류기간 연장').html;
  const next2 = d2.slice(at(d2, 'class="sg-next"'), at(d2, 'class="sg-evidence"'));
  assert(/<li class="sg-action-primary"><button type="button" class="sg-action" data-action="open-hikorea-guide"/.test(next2), 'structured: first row is the visit guide');
  assert(next2.includes('class="sg-next-ai"') && count(d2, /data-sg-action="followup"/g) === 1, 'structured: the follow-up row is the one Waymaker call to action');
  assert(count(next2, /class="sg-action-body"/g) === 5, 'structured: five rows');
});

check('structured answers: overview sits between the answer and the documents; a common procedure gets one too', () => {
  const d2 = run('D-2 체류기간 연장');
  assert(d2.step.kind === 'resolved', d2.step.kind);
  ordered(d2.html, 'class="sg-answer"', 'class="sg-overview"', '필수 서류 6개', '조건에 따라 내는 서류 1개', 'class="sg-docs"', 'class="sg-fee"', 'class="sg-cond-section"');
  assert(!d2.html.includes('class="sg-program"'), 'D-2 has no scheme block');
  const card = run('외국인등록증 재발급');
  assert(card.step.kind === 'procedure', card.step.kind);
  ordered(card.html, 'class="sg-overview"', '수수료 ₩35,000', '필수 서류 2개');
});

check('English copy and the edition label follow the bundle', () => {
  const r = run('F-4 extension', 'en');
  assert(r.step.kind === 'source-only', r.step.kind);
  for (const s of ['At a glance', 'Confirmed', 'Depends on your case', 'Check in the source', 'Special schemes that may apply', 'some holders only', 'Open the source, p.537', 'The October 2026 source text has not yet been reviewed']) assert(r.text.includes(s), s);
  assert(count(r.html, /Open the source, p\.537/g) === 1, 'the source action is printed once');
  assert(!/September/.test(r.text), 'no hard-coded September');
  const unknown = run('Z-9 연장');
  assert(unknown.text.includes('Z-9') && unknown.text.includes('2026년 10월판') && !unknown.text.includes('9월 기준'), 'unknown-code warning names the current edition');
});

check('the overview respects applicability: no confirmed fee for a procedure that does not apply', () => {
  const r = run('D-2 근무처 변경');
  assert(r.step.kind === 'source-only' && r.step.state === 'NOT_APPLICABLE', `${r.step.kind}/${r.step.state}`);
  assert(!r.html.includes('class="sg-overview"'), 'no overview for an inapplicable procedure');
  assert(!r.html.includes('class="sg-fee"') && !r.text.includes('₩120,000'), 'no fee section either');
  assert(r.text.includes('해당하지 않아요'), 'the not-applicable warning stays');
  const ok = run('D-2 체류기간 연장');
  assert(ok.html.includes('class="sg-overview"') && ok.text.includes('수수료 ₩60,000 · 시행규칙 기준'), 'applicable procedures keep the confirmed fee');
});
check('the inferred current status can be reopened and changed', () => {
  const q = 'C-3에서 F-6 변경';
  const interp = SG.interpret(q, bundle);
  const state = { query: q, interp, answers: {}, procedure: null, status: null, history: [], lang: 'ko' };
  let step = SG.nextStep(state, bundle);
  assert(step.kind !== 'question' && state.answers.current_status === 'short_stay', `inferred: ${step.kind} ${JSON.stringify(state.answers)}`);
  // "변경" on the answered line: the question must come back instead of being re-inferred
  delete state.answers.current_status; state.answers.__ask_current_status = true;
  step = SG.nextStep(state, bundle);
  assert(step.kind === 'question' && step.dimension === 'current_status', `reopened: ${step.kind}/${step.dimension}`);
  state.answers.current_status = 'illegal'; delete state.answers.__ask_current_status;
  step = SG.nextStep(state, bundle);
  assert(step.kind !== 'question' && state.answers.current_status === 'illegal', 'the chosen answer is kept');
});

check('no raw markup or stray characters leak into the result', () => {
  for (const q of ['F-4 체류기간 연장', 'D-2 체류기간 연장', '외국인등록증 재발급', 'H-2에서 F-4 변경', 'Z-9 연장']) {
    const r = run(q);
    assert(!/<ol class="sg-evidence-list"><\/ol>/.test(r.html) && !/<ol class="sg-evidence-list"><[^l]/.test(r.html), `${q}: evidence list renders its items`);
    assert(!/&lt;li|\[object Object\]|undefined|NaN/.test(r.html), `${q}: no leak`);
  }
});

console.log('[check_result_hierarchy] report', JSON.stringify({ cases: passed + failures.length }));
if (failures.length) { console.error(`[check_result_hierarchy] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_result_hierarchy] OK — ${passed} checks passed`);
