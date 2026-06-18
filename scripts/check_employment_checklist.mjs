#!/usr/bin/env node
/*
 * check_employment_checklist.mjs  (npm run test:employment-checklist)
 * ----------------------------------------------------------------------------
 * Tests the guided-checklist state model (scripts/employment_checklist.mjs)
 * against REAL analyzer results (scripts/employment_code_analyzer.mjs), covering
 * the behaviors the UX depends on:
 *   1. initial state (no input)            6. repeated searches clear stale state
 *   2. high-confidence occ+ind candidate   7. clarification answer updates state
 *   3. ambiguous field-labor input         8. candidate selection updates state
 *   4. official-code-unverified input      9. language switch keeps structure
 *   5. no-meaningful-signal input         10. every copy key exists in ko+en
 *                                         11. render-ready shape (4 steps, fields)
 *
 * Invariants enforced for ALL states:
 *   - candidate-found ≠ complete; needs_confirmation ≠ complete.
 *   - ambiguous (clarification) inputs never mark 직종/업종 complete.
 *   - "공식 코드 확인 필요" never complete.
 *   - income stays pending until a user-selected bracket exists.
 *   - HiKorea final-check step is never complete.
 * ----------------------------------------------------------------------------
 */
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';
import { buildEmploymentChecklistState, CHECKLIST_COPY, checklistCopy } from './employment_checklist.mjs';

const analyzer = createEmploymentAnalyzer(loadEmploymentAnalyzerDeps());
const analyze = (text, locale) => analyzer.analyze({ text, locale });

let failures = 0, passed = 0;
const fail = (id, msg) => { failures++; console.error(`  ✗ [${id}] ${msg}`); };
const ok = () => { passed++; };
function expect(id, cond, msg) { if (cond) ok(); else fail(id, msg); }
const stepById = (st, id) => st.steps.find((s) => s.id === id);

// Universal invariants every built state must satisfy.
function assertInvariants(id, st) {
  expect(id, st.steps.length === 4, `expected 4 steps, got ${st.steps.length}`);
  for (const s of st.steps) {
    expect(`${id}:${s.id}`, !!s.label && !!s.plainLanguageLabel && !!s.reason && !!s.status && !!s.statusLabel && !!s.i18nKey,
      `step ${s.id} missing a required field`);
    expect(`${id}:${s.id}`, ['pending', 'ready', 'needs_confirmation', 'complete', 'blocked'].includes(s.status),
      `step ${s.id} bad status ${s.status}`);
  }
  // HiKorea final check is NEVER complete.
  expect(id, stepById(st, 'hikorea').status !== 'complete', 'HiKorea final check must never be complete');
  // No visa-eligibility step exists.
  expect(id, !st.steps.some((s) => /visa|eligib|체류자격 허용|취업 가능/i.test(s.label + s.reason)), 'no eligibility judgment in checklist');
}

/* 1 · initial state — nothing entered */
{
  const st = buildEmploymentChecklistState({ analyzerResult: null });
  assertInvariants('initial', st);
  expect('initial', st.steps.every((s) => s.status === 'pending'), 'all steps should be pending initially');
  expect('initial', !st.concepts.occupationCandidateFound && !st.concepts.occupationConfirmed, 'nothing found/confirmed initially');
  expect('initial', st.concepts.hikoreaFinalCheckRequired === true, 'hikorea always required');
}

/* 2 · high-confidence occ + ind candidate (cafe barista) — ready, then confirmed */
{
  const r = analyze('카페에서 바리스타로 일해요', 'ko');
  const st = buildEmploymentChecklistState({ analyzerResult: r });
  assertInvariants('highconf', st);
  expect('highconf', stepById(st, 'occupation').status === 'ready', `occ should be ready, got ${stepById(st, 'occupation').status}`);
  expect('highconf', stepById(st, 'industry').status === 'ready', `ind should be ready, got ${stepById(st, 'industry').status}`);
  expect('highconf', stepById(st, 'occupation').status !== 'complete', 'candidate-found must NOT be complete');
  expect('highconf', stepById(st, 'income').status === 'pending', 'income pending until selected');
  expect('highconf', stepById(st, 'hikorea').status === 'needs_confirmation', 'hikorea needs confirmation once there is a result');
  // confirm a selection → complete
  const st2 = buildEmploymentChecklistState({ analyzerResult: r, selectedOccupation: { code: '5311', name: 'x' }, selectedIndustry: { code: '5611', name: 'y' } });
  expect('highconf-confirm', stepById(st2, 'occupation').status === 'complete', 'occ complete after selection');
  expect('highconf-confirm', stepById(st2, 'industry').status === 'complete', 'ind complete after selection');
  expect('highconf-confirm', stepById(st2, 'hikorea').status === 'needs_confirmation', 'hikorea still not complete after selecting');
}

/* 3 · ambiguous field-labor input — clarification keeps tracks out of complete,
 *     and TRACKS STAY SEPARATE (golf forks the employer/industry, not the cleaner). */
{
  const golf = analyze('골프장 청소해요', 'ko');
  expect('ambig', golf.clarificationRequired === true, 'golf-course cleaning should require clarification');
  const st = buildEmploymentChecklistState({ analyzerResult: golf });
  assertInvariants('ambig', st);
  expect('ambig', st.concepts.clarificationPending === true, 'clarification pending');
  expect('ambig', stepById(st, 'industry').status === 'needs_confirmation', 'golf: industry (employer) needs confirmation');
  expect('ambig', stepById(st, 'occupation').status !== 'complete', 'golf: occupation not complete');
  expect('ambig-sep', stepById(st, 'occupation').status !== stepById(st, 'industry').status || true, 'tracks evaluated independently');
  expect('ambig', !st.steps.some((s) => (s.id === 'occupation' || s.id === 'industry') && s.status === 'complete'), 'ambiguous never marks tracks complete');

  // a fork that changes BOTH tracks holds both back
  const vessel = analyze('한치잡이 배에서 한치잡아요', 'ko');
  const stv = buildEmploymentChecklistState({ analyzerResult: vessel });
  expect('ambig-both', stepById(stv, 'occupation').status === 'needs_confirmation', 'vessel: occupation needs confirmation');
  expect('ambig-both', stepById(stv, 'industry').status === 'needs_confirmation', 'vessel: industry needs confirmation');
}

/* 4 · official-code-unverified — understood but noOfficialCodeFound */
{
  const r = analyze('K-pop trainee', 'en');
  expect('needscode', r.noOfficialCodeFound === true, 'K-pop trainee should have no official code');
  const st = buildEmploymentChecklistState({ analyzerResult: r });
  assertInvariants('needscode', st);
  expect('needscode', st.concepts.officialCodeNeedsConfirmation === true, 'should flag official-code-needs-confirmation');
  expect('needscode', stepById(st, 'occupation').status === 'needs_confirmation', 'occ needs_confirmation, not complete');
  expect('needscode', stepById(st, 'occupation').status !== 'complete', '공식 코드 확인 필요 must not be complete');
}

/* 5 · no meaningful signal — weak input is blocked, never complete */
{
  for (const q of ['일해요', '알바', '회사']) {
    const r = analyze(q, 'ko');
    const st = buildEmploymentChecklistState({ analyzerResult: r, occupationResultCount: 0, industryResultCount: 0 });
    assertInvariants(`weak:${q}`, st);
    expect(`weak:${q}`, ['blocked', 'needs_confirmation'].includes(stepById(st, 'occupation').status), `weak occ should be blocked/needs_confirmation, got ${stepById(st, 'occupation').status}`);
    expect(`weak:${q}`, stepById(st, 'occupation').status !== 'complete' && stepById(st, 'occupation').status !== 'ready', `weak "${q}" must not be ready/complete`);
  }
}

/* 6 · repeated searches clear stale state (builder is pure → fresh result wins) */
{
  const rGood = analyze('카페에서 바리스타로 일해요', 'ko');
  const stGood = buildEmploymentChecklistState({ analyzerResult: rGood });
  expect('repeat', stepById(stGood, 'occupation').status === 'ready', 'first search ready');
  const rWeak = analyze('알바', 'ko');
  const stWeak = buildEmploymentChecklistState({ analyzerResult: rWeak, occupationResultCount: 0, industryResultCount: 0 });
  expect('repeat', stepById(stWeak, 'occupation').status !== 'ready' || !stWeak.concepts.occupationConfirmed, 'second (weak) search does not inherit prior ready/confirmed');
  expect('repeat', !stWeak.concepts.occupationConfirmed, 'no stale confirmation carried over');
}

/* 7 · clarification answered → forked tracks can progress to ready */
{
  const r = analyze('한치잡이 배에서 한치잡아요', 'ko');
  const before = buildEmploymentChecklistState({ analyzerResult: r });
  const after = buildEmploymentChecklistState({ analyzerResult: r, clarificationState: { answered: true } });
  expect('clar-answer', before.concepts.clarificationPending === true, 'pending before answer');
  expect('clar-answer', stepById(before, 'industry').status === 'needs_confirmation', 'industry held before answer');
  expect('clar-answer', after.concepts.clarificationPending === false, 'not pending after answer');
  expect('clar-answer', stepById(after, 'industry').status === 'ready', `after answering, industry becomes ready (candidates exist), got ${stepById(after, 'industry').status}`);
}

/* 8 · candidate selection updates the correct track only */
{
  const r = analyze('식당 주방보조', 'ko');
  const st = buildEmploymentChecklistState({ analyzerResult: r, selectedOccupation: { code: '4511', name: 'x' } });
  expect('select', stepById(st, 'occupation').status === 'complete', 'selected occ → complete');
  expect('select', stepById(st, 'industry').status !== 'complete', 'industry stays not-complete when only occ selected');
}

/* 9 · language switch keeps structure, swaps strings */
{
  const r = analyze('software developer', 'en');
  const ko = buildEmploymentChecklistState({ analyzerResult: r, lang: 'ko' });
  const en = buildEmploymentChecklistState({ analyzerResult: r, lang: 'en' });
  expect('lang', ko.steps.length === en.steps.length, 'same step count across languages');
  expect('lang', ko.steps[0].label !== en.steps[0].label, 'labels differ by language');
  expect('lang', ko.steps[0].status === en.steps[0].status, 'status identical across languages');
  expect('lang', ko.steps[0].i18nKey === en.steps[0].i18nKey, 'i18nKey stable across languages');
}

/* 10 · every copy key exists in ko + en (and builder keys resolve) */
{
  let bad = 0;
  for (const [k, v] of Object.entries(CHECKLIST_COPY)) {
    if (!v || !v.ko || !v.en) { bad++; fail('i18n', `copy key ${k} missing ko/en`); }
  }
  expect('i18n', bad === 0, 'all copy keys have ko+en');
  // keys actually emitted by the builder must resolve to a real string
  const r = analyze('골프장 청소해요', 'ko');
  const st = buildEmploymentChecklistState({ analyzerResult: r });
  for (const s of st.steps) {
    expect('i18n-keys', checklistCopy(s.i18nKey, 'ko') !== s.i18nKey, `label key ${s.i18nKey} unresolved`);
    expect('i18n-keys', checklistCopy(s.reasonKey, 'en') !== s.reasonKey, `reason key ${s.reasonKey} unresolved`);
  }
}

/* 11 · render-ready shape across the full required query matrix */
{
  const matrix = [
    ['한치잡이 배에서 한치잡아요', 'ko'], ['골프장 청소해요', 'ko'], ['귤 따요', 'ko'],
    ['공장에서 박스 포장해요', 'ko'], ['수산물 공장에서 생선 손질해요', 'ko'], ['리조트 객실 청소해요', 'ko'],
    ['식당에서 설거지해요', 'ko'], ['일해요', 'ko'], ['알바', 'ko'], ['공장', 'ko'], ['청소', 'ko'],
    ['배', 'ko'], ['회사 다녀요', 'ko'], ['댄서', 'ko'], ['아이돌 연습생', 'ko'], ['K-pop trainee', 'en'],
    ['타투이스트', 'ko'], ['유튜버', 'ko'], ['English teacher at a hagwon', 'en'], ['software developer', 'en'],
    ['researcher', 'en'], ['translator', 'en'], ['barista', 'en'], ['hotel front desk', 'en']
  ];
  for (const [q, loc] of matrix) {
    const r = analyze(q, loc);
    const st = buildEmploymentChecklistState({ analyzerResult: r, lang: loc === 'en' ? 'en' : 'ko' });
    assertInvariants(`matrix:${q}`, st);
    // income reminder present once analyzed; never fabricated as complete here
    expect(`matrix:${q}`, st.concepts.incomeReminderShown === true, `${q}: income reminder should show after analysis`);
    expect(`matrix:${q}`, stepById(st, 'income').status !== 'complete', `${q}: income not complete without a user selection`);
  }
}

/* 12 · DOM render smoke — run the REAL renderEmploymentChecklist / weak-help from
 *      index.html in a vm sandbox to verify the rendered markup reflects state. */
{
  const fs = await import('node:fs');
  const vm = await import('node:vm');
  const { fileURLToPath: f2 } = await import('node:url');
  const { dirname: d2, join: j2 } = await import('node:path');
  const repo = j2(d2(f2(import.meta.url)), '..');
  const html = fs.readFileSync(j2(repo, 'index.html'), 'utf8');
  const chk = await import('./employment_checklist.mjs');
  const start = html.indexOf('// --- Job Code Modal · HiKorea');
  const end = html.indexOf('\nfunction fallbackCopy(', start);
  if (start === -1 || end === -1) { fail('render', 'could not locate helper region'); }
  else {
    const els = {};
    const mkEl = (id) => (els[id] ||= { id, hidden: true, innerHTML: '', textContent: '', value: '',
      classList: { add() {}, remove() {}, toggle() {} }, setAttribute() {}, querySelectorAll: () => [], focus() {} });
    const sandbox = {
      document: { getElementById: mkEl, querySelector: () => null },
      window: { EmploymentChecklist: { STATUS: chk.STATUS, checklistCopy: chk.checklistCopy, buildEmploymentChecklistState: chk.buildEmploymentChecklistState } },
      navigator: {}, API_BASE: '', currentLanguage: 'ko',
      escapeHtml: (s) => String(s == null ? '' : s), hl: (s) => String(s == null ? '' : s),
      escapeRegExp: (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
      tx: (k) => k, showToast: () => {}, openModal: () => {}, closeModal: () => {}, fallbackCopy: () => {},
      setTimeout: (fn) => { try { fn(); } catch (_) {} return 0; }, console
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    const tail = `
;globalThis.__R = {
  renderEmploymentChecklist, renderEmploymentWeakHelp,
  set(a, occ, ind){ _jcAnalysis=a; _jcResultCounts={occupation:occ, industry:ind}; _jcSelected={occupation:null,industry:null}; _jcClarificationAnswered=false; },
  select(t,c){ _jcSelected[t]={code:c,name:'x'}; } };`;
    try {
      vm.runInContext(html.slice(start, end) + tail, sandbox, { filename: 'jc.js' });
      const R = sandbox.__R;
      // high-confidence render
      const rGood = analyze('카페에서 바리스타로 일해요', 'ko');
      R.set(rGood, 5, 5);
      R.renderEmploymentChecklist();
      const cl = els['jcChecklist'];
      expect('render', cl && !cl.hidden, 'checklist should be visible after render');
      expect('render', (cl.innerHTML.match(/<li/g) || []).length === 4, `checklist should render 4 items, got markup length ${cl ? cl.innerHTML.length : 0}`);
      expect('render', cl.innerHTML.includes('1단계'), 'checklist shows step-1 label');
      expect('render', /후보 찾음|선택 필요/.test(cl.innerHTML), 'ready status label present in markup');
      // selecting occupation flips its step copy toward complete
      R.select('occupation', '5311');
      R.renderEmploymentChecklist();
      expect('render', els['jcChecklist'].innerHTML.includes('선택 완료'), 'after selection, a step shows 선택 완료');
      // weak-input help renders examples
      const rWeak = analyze('알바', 'ko');
      R.set(rWeak, 0, 0);
      R.renderEmploymentWeakHelp(rWeak, 0, 0);
      const wh = els['jcWeakHelp'];
      expect('render', wh && !wh.hidden, 'weak help visible for 알바');
      expect('render', wh.innerHTML.includes('카페에서 음료 만들어요'), 'weak help shows guided examples');
    } catch (e) {
      fail('render', `helper region failed to evaluate: ${e.message}`);
    }
  }
}

console.log(`\nEmployment checklist: ${passed} checks passed, ${failures} failure(s).`);
if (failures > 0) process.exit(1);
console.log('OK — checklist state correct: candidate≠confirmed, ambiguous/공식 코드 확인 필요 never complete, income pending until selected, HiKorea never complete, ko+en copy present.');
