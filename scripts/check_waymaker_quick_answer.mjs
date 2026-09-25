/*
 * check_waymaker_quick_answer.mjs
 * ----------------------------------------------------------------------------
 * Waymaker Quick Answer QA (assets/js/waymaker-quick-answer.js + api/waymaker/quick-answer.js).
 *
 * For every mandatory question it asserts: classification, clarification
 * behaviour, the structured answer (documents, physical forms, fee, sources),
 * the full-detail handoff and the AI follow-up handoff. Then the grounding
 * contract: the AI may only rephrase — any number, amount, document, form,
 * office or fee outside the validated model is rejected by the shared
 * validator (client and server), deterministic questions never call the model,
 * and a provider failure leaves the deterministic answer in place.
 *
 *   node scripts/check_waymaker_quick_answer.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/waymaker-quick-answer.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance; const QA = globalThis.VisableQuickAnswer;
const AI = require(join(ROOT, 'lib/waymaker-quick-answer-ai.js'));
const handler = require(join(ROOT, 'api/waymaker/quick-answer.js'));

let passed = 0; const failures = [];
function check(name, fn) { try { const r = fn(); if (r && typeof r.then === 'function') return r.then(() => { passed += 1; }).catch((e) => { failures.push(`${name}: ${e.message}`); }); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
function run(q, answers = {}, lang = 'ko', extra = {}) { const interp = SG.interpret(q, bundle); const state = { interp, answers, procedure: null, status: null, history: [], lang, query: q, ...extra }; const step = SG.nextStep(state, bundle); const out = SG.renderModel(step, state, bundle); return { interp, state, step, ...out, qa: out.model.quick }; }
const DEAD_END = '체류자격을 찾지 못했어요';

/* ------------------------------------------------- mandatory queries ---- */
const CASES = [
  { q: 'F-6 연장하려면 뭐 필요해?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'question', mode: 'clarify', dim: 'subtype' }, answers: { subtype: 'spouse', f61_phase: 'normal' }, then: { kind: 'resolved', mode: 'answer', fee: 30000, docsMin: 5, formLabelled: false } },
  { q: '외국인등록증 재발급하려면 뭐 필요해?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'procedure', mode: 'answer', fee: 35000, docsMin: 2 } },
  { q: '등록증 잃어버렸는데?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'procedure', mode: 'answer', fee: 35000, docsMin: 2, reason: 'lost' } },
  { q: 'GKS 장학생인데 연장수수료 면제돼?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'question', mode: 'fee', dim: '__alias', fee: 60000, gks: true } },
  { q: '제주에서 F-6-1 연장할 때 체류지입증서류 필요해?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'question', mode: 'clarify', dim: 'f61_phase' }, answers: { f61_phase: 'normal' }, then: { kind: 'resolved', mode: 'answer', focus: 'residence_proof', office: 'jeju', fee: 30000 } },
  { q: 'D-2인데 아르바이트하려면?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'resolved', mode: 'answer', feeState: 'CONFLICT', docsMin: 5 } },
  { q: '주소 바꿨는데 뭐 해야 해?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'procedure', mode: 'answer', feeState: 'NOT_LISTED', docsMin: 3 } },
  { q: '외국인등록증에 여권번호 바꾸려면?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'procedure', mode: 'answer', feeState: 'NO_FEE', docsMin: 3 } },
  { q: 'F-6 연장 수수료 얼마야?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'question', mode: 'fee', dim: 'subtype', fee: 30000 } },
  { q: 'E-7-4 연장 준비물 알려줘', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'resolved', mode: 'answer', fee: 60000, docsMin: 6 } },
  { q: '가족비자 연장하고 싶어', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'question', mode: 'clarify', dim: '__alias' } },
  { q: 'F-4 연장하려면?', intent: 'NATURAL_LANGUAGE_QUESTION', first: { kind: 'source-only', mode: 'fallback' } },
];
function expect(r, exp, label) {
  assert(r.step.kind === exp.kind, `${label}: kind ${r.step.kind} ≠ ${exp.kind}`);
  assert(r.qa && r.qa.mode === exp.mode, `${label}: mode ${r.qa && r.qa.mode} ≠ ${exp.mode}`);
  assert(QA.validateModel(r.qa).ok, `${label}: invalid model ${JSON.stringify(QA.validateModel(r.qa).errors)}`);
  assert(!r.html.includes(DEAD_END), `${label}: dead end`);
  assert(r.html.includes('id="sgQuickTitle"') && r.html.includes('id="sgQuickSummary"'), `${label}: quick block rendered`);
  if (exp.dim) { assert(r.step.dimension === exp.dim, `${label}: dimension ${r.step.dimension}`); assert(r.qa.needsClarification && r.qa.clarification && r.qa.clarification.question, `${label}: clarification model`); assert(r.html.includes('sg-question'), `${label}: question UI still shown`); }
  if (exp.mode === 'clarify') { assert(r.qa.interpretation.confidence === 'MEDIUM', `${label}: confidence`); assert(!r.html.includes('id="sgFull"'), `${label}: clarify must not hide the question`); }
  if (exp.mode === 'answer' || exp.mode === 'fee') {
    assert(r.qa.interpretation.confidence === 'HIGH' && r.qa.sources.length >= 1, `${label}: HIGH + sources`);
    assert(r.qa.sources.every((s) => (s.type === 'regulation' && s.article && s.url) || (s.type === 'manual' && s.page && s.date)), `${label}: source binding`);
    assert(!/\bHIGH\b|\bMEDIUM\b|confidence: \d|\d{2}%/.test(r.html.split('sg-quick')[1] || ''), `${label}: no numeric confidence exposed`);
  }
  if (exp.mode === 'answer') {
    assert(r.html.includes('data-sg-action="toggle-full"') && r.html.includes('id="sgFull" hidden'), `${label}: full-detail handoff (collapsed detail)`);
    assert(r.html.includes('data-sg-action="followup"') && r.html.includes('data-sg-action="show-evidence"'), `${label}: follow-up + evidence actions`);
    assert(r.qa.documents.required.every((d) => d.name && d.form), `${label}: documents with forms`);
    assert(r.qa.uncertainties.length >= 1, `${label}: uncertainties listed`);
  }
  if (exp.mode === 'fallback') { assert(r.qa.interpretation.confidence === 'LOW' && !r.html.includes('id="sgFull" hidden'), `${label}: fallback shows the structured evidence, no synthesized answer`); assert(!/준비할 서류[는:]/.test(r.qa.summary), `${label}: no invented list`); }
  if (exp.fee) assert(r.qa.fees.length && r.qa.fees[0].amount === exp.fee && r.qa.fees[0].amountState === 'FIXED', `${label}: fee ${JSON.stringify(r.qa.fees[0])}`);
  if (exp.feeState) assert(r.qa.fees.length && r.qa.fees[0].amountState === exp.feeState, `${label}: fee state ${r.qa.fees[0] && r.qa.fees[0].amountState}`);
  if (exp.docsMin) assert(r.qa.documents.required.length >= exp.docsMin, `${label}: ${r.qa.documents.required.length} required docs`);
  if (exp.reason) assert(r.model.reason === exp.reason && !r.qa.documents.required.some((d) => d.ref === 'arc_existing_original'), `${label}: lost → no existing card`);
  if (exp.gks) assert(/GKS/.test(r.qa.summary) && /조건부|확인/.test(r.qa.summary) && r.qa.fees[0].exemptions.some((e) => e.program === 'gks' && e.review === 'CONDITIONAL_NEEDS_REVIEW'), `${label}: GKS conditional`);
  if (exp.focus) { assert(r.qa.focus && r.qa.focus.ref === 'residence_proof' && r.qa.focus.level === 'required', `${label}: focus`); assert(/체류지 입증서류: 필수예요/.test(r.qa.title) && /표기는 없어요/.test(r.qa.summary), `${label}: focus answer with honest form state`); }
  if (exp.office) assert(r.qa.localPractice.office && r.qa.localPractice.office.id === exp.office && r.qa.localPractice.variations[0].layer === 'UNVERIFIED_USER_REPORT', `${label}: office layer`);
  if (exp.formLabelled === false) assert(r.qa.documents.required.find((d) => d.ref === 'passport').form === 'SOURCE_DOES_NOT_SPECIFY', `${label}: passport form not guessed`);
}
for (const c of CASES) {
  check(`quick answer: ${c.q}`, () => {
    const r = run(c.q); assert(r.interp.route.intent === c.intent, `intent ${r.interp.route.intent}`); expect(r, c.first, 'first');
    if (c.answers) { const r2 = run(c.q, c.answers); expect(r2, c.then, 'after clarification'); }
  });
}
check('deterministic fee questions do not depend on a pending clarification when every candidate shares the fee', () => {
  const g = run('GKS 장학생인데 연장수수료 면제돼?'); assert(g.qa.mode === 'fee' && QA.feeInvariant(bundle, 'extension', ['D-2', 'D-4']) === 'D-2', 'fee invariant across D-2/D-4');
  assert(QA.feeInvariant(bundle, 'extension', ['F-6', 'F-3']) === null, 'F-6 vs F-3 differ → not invariant');
});
check('question form triggers the Quick Answer; a plain code search does not', () => {
  assert(run('외국인등록증 재발급').qa === null && run('F-6 연장').qa === null, 'no quick block for terse queries');
  assert(run('외국인등록증 재발급하려면?').qa !== null, 'question form gets one');
  const forced = run('외국인등록증 재발급', {}, 'ko', { quick: true }); assert(forced.qa && forced.qa.mode === 'answer', 'explicit quick flag');
});
check('EN rendering of the Quick Answer uses English copy and the same facts', () => {
  const ko = run('외국인등록증 재발급하려면 뭐 필요해?'); const en = run('외국인등록증 재발급하려면 뭐 필요해?', {}, 'en');
  assert(en.qa.mode === 'answer' && en.html.includes('Quick answer') && en.html.includes('Full guidance') && en.qa.fees[0].amount === ko.qa.fees[0].amount, 'EN');
  assert(en.qa.documents.required.length === ko.qa.documents.required.length && en.qa.documents.required[0].name !== ko.qa.documents.required[0].name, 'translated names, same list');
});

/* ------------------------------------------------ AI grounding tests ---- */
check('validateEnhancement rejects new facts, numbers, forms, offices and overclaims; accepts a faithful rewrite', () => {
  const r = run('외국인등록증 재발급하려면 뭐 필요해?'); const qa = r.qa;
  const ok = QA.validateEnhancement(qa, '외국인등록증 재발급은 통합신청서에 사진 1장을 붙여 내고, 수수료 ₩35,000은 현금 또는 카드로 냅니다. 잃어버린 경우가 아니면 기존 등록증도 함께 냅니다.');
  assert(ok.ok, JSON.stringify(ok.reasons));
  const cases = [
    ['여권 원본과 사본 2부를 준비하세요. 수수료는 5만원입니다.', /number|fact word|off-topic/],
    ['외국인등록증 재발급에는 아포스티유 받은 출생증명서가 필요합니다.', /아포스티유/],
    ['외국인등록증 재발급 수수료는 면제입니다.', /면제/],
    ['외국인등록증 재발급은 무조건 허가됩니다. 확실해요.', /overclaim/],
    ['외국인등록증 재발급은 3일 이내에 신청해야 하고 과태료가 있어요.', /3일|과태료/],
    ['외국인등록증 재발급은 제주출입국·외국인청에서만 가능합니다.', /off-topic|fact/],
    ['<b>외국인등록증 재발급</b> 안내 http://x', /markup/],
    ['외국인등록증 재발급은 하이코리아 예약 후 방문해야 합니다.', /하이코리아|예약/],
    ['Bring your passport original and two copies; the fee is ₩35,000 for residence card reissue.', /original|copies|copy/],
  ];
  for (const [text, re] of cases) { const v = QA.validateEnhancement(qa, text); assert(!v.ok && v.reasons.some((x) => re.test(x)), `accepted or wrong reason: ${text} → ${JSON.stringify(v.reasons)}`); }
});
check('server enhancement shares the validator: faithful → ok; hallucinated → rejected; no key → NOT_CONFIGURED; bad input → REJECTED_INPUT; fee/clarify modes never call the model', async () => {
  const r = run('외국인등록증 재발급하려면 뭐 필요해?'); const compact = QA.compactForAi(r.qa);
  const cfg = { key: 'test', models: ['stub'], timeoutMs: 1000, siteUrl: '', siteTitle: '' };
  let calls = 0;
  const faithful = async () => { calls += 1; return { ok: true, model: 'stub', text: JSON.stringify({ summary: '외국인등록증 재발급은 통합신청서와 사진 1장을 내고 수수료 ₩35,000을 현금이나 카드로 냅니다. 분실이 아니면 기존 외국인등록증도 함께 냅니다.' }) }; };
  const out = await AI.enhanceQuickAnswer({ lang: 'ko', model: compact }, { config: cfg, callOpenRouter: faithful }); assert(out.ok && out.status === 'OK' && /₩35,000/.test(out.summary), JSON.stringify(out));
  const bad = await AI.enhanceQuickAnswer({ lang: 'ko', model: compact }, { config: cfg, callOpenRouter: async () => ({ ok: true, text: '{"summary":"여권 원본과 사본 2부, 수수료 5만원을 준비하세요."}' }) }); assert(!bad.ok && bad.status === 'REJECTED_OUTPUT', JSON.stringify(bad));
  const nokey = await AI.enhanceQuickAnswer({ lang: 'ko', model: compact }, { config: { key: '', models: [], timeoutMs: 1 } }); assert(!nokey.ok && nokey.status === 'NOT_CONFIGURED', 'not configured');
  const junk = await AI.enhanceQuickAnswer({ lang: 'ko', model: { mode: 'answer', summary: 'x' } }, { config: cfg }); assert(!junk.ok && junk.status === 'REJECTED_INPUT', 'rejected input');
  const feeQ = run('F-6 연장 수수료 얼마야?'); calls = 0;
  const fee = await AI.enhanceQuickAnswer({ lang: 'ko', model: QA.compactForAi(feeQ.qa) }, { config: cfg, callOpenRouter: faithful }); assert(!fee.ok && fee.status === 'NOT_NEEDED' && calls === 0, 'fee mode never calls the model');
  const prov = await AI.enhanceQuickAnswer({ lang: 'ko', model: compact }, { config: cfg, callOpenRouter: async () => ({ ok: false, error: 'timeout' }) }); assert(!prov.ok && prov.status === 'PROVIDER_FAILED', 'provider failure surfaces as ok:false');
  assert(/새로 만들지|do not add|Forbidden/i.test(AI.systemPrompt('ko') + AI.systemPrompt('en')), 'prompt forbids new facts');
});
check('the Vercel handler answers GET without secrets and turns a missing key into 503 NOT_CONFIGURED', async () => {
  const saved = process.env.OPENROUTER_API_KEY; delete process.env.OPENROUTER_API_KEY;
  const mk = () => ({ headers: {}, code: null, body: null, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } });
  const g = mk(); await handler({ method: 'GET' }, g); assert(g.code === 200 && g.body.status === 'NOT_CONFIGURED' && !JSON.stringify(g.body).includes('sk-'), 'GET');
  const p = mk(); await handler({ method: 'POST', body: { lang: 'ko', model: QA.compactForAi(run('외국인등록증 재발급하려면 뭐 필요해?').qa) } }, p); assert(p.code === 503 && p.body.status === 'NOT_CONFIGURED', JSON.stringify([p.code, p.body]));
  const m = mk(); await handler({ method: 'PUT' }, m); assert(m.code === 405, 'method');
  if (saved) process.env.OPENROUTER_API_KEY = saved;
});
check('client afterRender: AI unavailable (404/network) stays silent; provider failure shows the fallback note; success is validated before it touches the DOM', async () => {
  const r = run('외국인등록증 재발급하려면 뭐 필요해?');
  function fakeHost(html) { const map = {}; const el = (id) => (map[id] = map[id] || { textContent: '', hidden: true, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } }); return { querySelector: (sel) => el(sel.replace('#', '')), map }; }
  async function scenario(fetchImpl) { const host = fakeHost(); const savedFetch = globalThis.fetch; globalThis.fetch = fetchImpl; try { QA.afterRender(host, r.model, r.state, bundle); await new Promise((res) => setTimeout(res, 30)); } finally { globalThis.fetch = savedFetch; } return host.map; }
  const q1 = run('외국인등록증 재발급하려면 뭐 필요해? (1)'); // distinct cache keys per scenario
  const notDeployed = await (async () => { const host = fakeHost(); const saved = globalThis.fetch; globalThis.fetch = async () => ({ status: 404, json: async () => ({}) }); try { QA.afterRender(host, q1.model, q1.state, bundle); await new Promise((res) => setTimeout(res, 30)); } finally { globalThis.fetch = saved; } return host.map; })();
  assert(notDeployed.sgQuickNote.hidden === true && notDeployed.sgQuickSummary.textContent === '', '404 → silent');
  const q2 = run('외국인등록증 재발급하려면 뭐 필요해? (2)');
  const failed = await (async () => { const host = fakeHost(); const saved = globalThis.fetch; globalThis.fetch = async () => ({ status: 200, json: async () => ({ ok: false, status: 'PROVIDER_FAILED' }) }); try { QA.afterRender(host, q2.model, q2.state, bundle); await new Promise((res) => setTimeout(res, 30)); } finally { globalThis.fetch = saved; } return host.map; })();
  assert(failed.sgQuickNote.hidden === false && /AI 요약을 만들지 못했지만/.test(failed.sgQuickNote.textContent), 'provider failure → fallback note, deterministic answer kept');
  const q3 = run('외국인등록증 재발급하려면 뭐 필요해? (3)');
  const halluc = await (async () => { const host = fakeHost(); const saved = globalThis.fetch; globalThis.fetch = async () => ({ status: 200, json: async () => ({ ok: true, summary: '여권 원본과 사본 2부를 준비하고 5만원을 내세요.' }) }); try { QA.afterRender(host, q3.model, q3.state, bundle); await new Promise((res) => setTimeout(res, 30)); } finally { globalThis.fetch = saved; } return host.map; })();
  assert(halluc.sgQuickSummary.textContent === '' && halluc.sgQuickSummary.attrs['data-sg-ai'] !== 'enhanced', 'hallucinated summary never reaches the DOM');
  const q4 = run('외국인등록증 재발급하려면 뭐 필요해? (4)');
  const good = await (async () => { const host = fakeHost(); const saved = globalThis.fetch; globalThis.fetch = async () => ({ status: 200, json: async () => ({ ok: true, summary: '외국인등록증 재발급은 통합신청서와 사진 1장을 내고 ₩35,000을 냅니다. 분실이 아니면 기존 외국인등록증도 함께 냅니다.' }) }); try { QA.afterRender(host, q4.model, q4.state, bundle); await new Promise((res) => setTimeout(res, 30)); } finally { globalThis.fetch = saved; } return host.map; })();
  assert(good.sgQuickSummary.attrs['data-sg-ai'] === 'enhanced' && /₩35,000/.test(good.sgQuickSummary.textContent), 'validated summary applied via textContent');
  void scenario;
});

check('Quick Answer and Waymaker handoff never resurrect an unavailable F-6 online reduction', () => {
  const r = run('제주에서 F-6-1 연장할 때 체류지입증서류 필요해?', { f61_phase: 'normal' });
  assert(!r.html.includes('온라인 신청 시 20% 감경'), 'rendered Quick Answer must not show F-6 online reduction');
  const p = QA.buildHandoff(r.model, r.state, bundle, 'ko');
  assert(!p.fees.join(' ').includes('20%'), 'handoff must not carry F-6 online reduction');
});

/* -------------------------------------------------- follow-up handoff ---- */
check('follow-up handoff carries query, status, procedure, documents, forms, fees, local practice, sources and uncertainties, and instructs the chatbot not to extend them', () => {
  const r = run('제주에서 F-6-1 연장할 때 체류지입증서류 필요해?', { f61_phase: 'normal' });
  const p = QA.buildHandoff(r.model, r.state, bundle, 'ko');
  assert(p.version === 1 && p.query && p.status === 'F-6-1' && p.procedure === 'extension' && p.office && p.office.id === 'jeju', 'identity');
  assert(p.documents.required.length >= 5 && p.forms.length && p.fees.some((f) => /₩30,000/.test(f)) && p.localPractice.some((l) => /UNVERIFIED_USER_REPORT/.test(l)) && p.sources.length >= 3 && p.uncertainties.length >= 1, 'content');
  for (const bad of ['passport_number', 'arc_number', 'name']) assert(!(bad in p), `handoff carries ${bad}`);
  const ctx = QA.handoffContextLine(p, 'ko'); assert(/새로 만들지 마십시오/.test(ctx) && ctx.includes('체류지 입증서류') && ctx.includes('₩30,000') && /관서 정보\(전국 기준이 아님\)/.test(ctx), 'context line');
  const en = QA.handoffContextLine(p, 'en'); assert(/do not add documents/.test(en) && en.includes('F-6-1'), 'EN context');
  assert(QA.readHandoff() === null, 'no sessionStorage in Node → null, never a throw');
});

/* ------------------------------------------------------ adversarial ---- */
check('adversarial premises never produce a confident wrong Quick Answer', () => {
  for (const q of ['여권은 무조건 원본이랑 사본 내는 거지?', '임대차계약서는 항상 원본 사본 둘 다지?', '제주는 체류지서류 무조건 필요 없지?']) { const r = run(q); assert(r.qa === null && r.step.kind === 'no-status' && !r.html.includes(DEAD_END), `${q}: ${r.step.kind}`); }
  const f = run('F-6는 전국 어디서나 똑같은 서류 받지?'); assert(f.qa && f.qa.mode === 'clarify', 'universal-office premise → clarify, not confirm');
  const g = run('GKS면 수수료 다 면제지?'); assert(g.qa && g.qa.mode === 'clarify' && /면제 대상자도 납부/.test(g.html), 'GKS blanket exemption not confirmed');
});

await new Promise((r) => setTimeout(r, 200));
console.log('[check_waymaker_quick_answer] report', JSON.stringify({ cases: CASES.length }));
if (failures.length) { console.error(`[check_waymaker_quick_answer] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_waymaker_quick_answer] OK — ${passed} checks passed`);
