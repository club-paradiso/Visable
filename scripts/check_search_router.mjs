/*
 * check_search_router.mjs
 * ----------------------------------------------------------------------------
 * Procedure-first routing QA (assets/js/search-router.js + status-guidance.js).
 *
 *  1. card-reissue procedure-only queries resolve to the common rule — never the
 *     "체류자격을 찾지 못했어요" dead end (release-blocking regression);
 *  2. address-change / registration-info queries work without a status;
 *  3. status-required procedures (extension, registration) ask for the status in
 *     ordinary language instead of dead-ending;
 *  4. object × action composition beats keyword collisions (ARC 재발급, residence
 *     card reissue, 외국인등록증 alone → ask which);
 *  5. offices, user programs, reasons, question facets are extracted separately;
 *  6. the procedure registry is complete and consistent with the COMMON rules;
 *  7. the procedure intent survives a language switch;
 *  8. unsupported input produces a useful fallback; markup never leaks.
 *
 *   node scripts/check_search_router.mjs
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
const R = globalThis.VisableSearchRouter;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
const DEAD_END = '체류자격을 찾지 못했어요';

function run(query, answers = {}, lang = 'ko', overrides = {}) {
  const interp = SG.interpret(query, bundle);
  const state = { interp, answers: { ...answers }, procedure: null, status: null, history: [], lang, query, ...overrides };
  const step = SG.nextStep(state, bundle);
  const out = SG.renderModel(step, state, bundle);
  return { interp, route: interp.route, state, step, ...out, text: out.html.replace(/<[^>]+>/g, ' ') };
}
const groupOf = (model, ref) => (model.documentGroups.find((g) => g.items.some((d) => d.ref === ref)) || {}).key || null;

/* 1. card reissue — the regression */
const CARD = ['외국인등록증 재발급', '등록증 재발급', 'ARC 재발급', 'residence card reissue', '외국인등록증 재발급하려면?', 'ARC 잃어버렸어', '등록증 훼손됐어', '등록증 잃어버렸는데?', 'lost my alien registration card', 'arc reissue'];
for (const q of CARD) {
  check(`card reissue: "${q}" → common procedure, no dead end`, () => {
    const r = run(q);
    assert(r.route.procedure === 'card_reissue', `procedure ${r.route.procedure} (${r.route.procedureWhy})`);
    assert(['ADMINISTRATIVE_TASK', 'NATURAL_LANGUAGE_QUESTION'].includes(r.route.intent), `intent ${r.route.intent}`);
    assert(r.step.kind === 'procedure' && r.step.common && r.step.status === null, `kind ${r.step.kind}`);
    assert(!r.html.includes(DEAD_END), 'dead end rendered');
    // exact procedure names read definitively; sentences keep the "이해했어요" reading
    const exactName = ['외국인등록증 재발급', '등록증 재발급', 'residence card reissue'].includes(q);
    const strip = (r.html.match(/<div class="sg-interp"[^]*?<\/div>/) || [''])[0];
    assert(strip.includes(exactName ? 'data-sg-match="EXACT_PROCEDURE"' : '(으)로 이해했어요') && strip.includes(r.model.procedureLabel), `interpretation strip (${exactName ? 'exact' : 'natural'}): ${strip.replace(/<[^>]+>/g, ' ').trim()}`);
    assert(r.model.docCounts.required >= 2, 'baseline documents');
    assert(r.html.includes('sg-fee-amount') && r.html.includes('₩35,000'), 'fee shown separately');
    assert(!r.model.documentGroups.some((g) => g.items.some((d) => d.ref === 'fee')), 'fee must not be a document');
    assert(r.model.evidence.some((e) => e.type === 'regulation' && e.id === 'decree_42'), 'decree 42 evidence');
    assert(r.html.includes('data-sg-action="answer" data-sg-dim="reissue_reason"'), 'reason chips offered, not required');
  });
}
check('card reissue: reason changes only the existing-card item (lost → not needed; damaged → required)', () => {
  const lost = run('등록증 잃어버렸어'); const damaged = run('등록증 훼손됐어'); const plain = run('외국인등록증 재발급');
  assert(lost.route.conditions.reissue_reason === 'lost' && damaged.route.conditions.reissue_reason === 'damaged', 'reason extraction');
  assert(groupOf(lost.model, 'arc_existing_original') === 'na', 'lost: existing card not required');
  assert(groupOf(damaged.model, 'arc_existing_original') === 'required', 'damaged: existing card required');
  assert(groupOf(plain.model, 'arc_existing_original') === 'conditional', 'no reason: conditional with its condition');
  assert(lost.model.docCounts.required === damaged.model.docCounts.required - 1, 'exactly one item differs');
  const fee = (r) => SG.feeSummary('ko', r.model);
  assert(fee(lost) === fee(damaged) && fee(lost) === '₩35,000', 'fee identical across reasons');
});
check('card reissue with a status still serves the common rule and says so', () => {
  const r = run('F-6 외국인등록증 재발급');
  assert(r.route.intent === 'STATUS_PROCEDURE' && r.step.kind === 'procedure' && r.step.status === 'F-6', JSON.stringify([r.route.intent, r.step.kind, r.step.status]));
  assert(r.html.includes('F-6도 같은 공통 기준이 적용돼요'), 'common lead with status');
});

/* 2. address / registration-information reports */
check('주소 변경 신고 / 체류지 변경 / 이사했어요 → common address report', () => {
  for (const q of ['주소 변경 신고', '체류지 변경', '이사했는데 신고해야 해?', 'address change report', 'I moved to a new address']) {
    const r = run(q);
    assert(r.route.procedure === 'residence_report' && r.step.kind === 'procedure', `${q}: ${r.route.procedure}/${r.step.kind}`);
    assert(!r.html.includes(DEAD_END), q);
    assert(r.html.includes('15일'), `${q}: deadline from the Act`);
    assert(r.model.evidence.some((e) => e.type === 'regulation' && e.id === 'act_36'), `${q}: Act 36 evidence`);
    assert(r.html.includes('임대차계약서') && r.html.includes('매매계약서'), `${q}: Rule 49-3 attachments`);
  }
});
check('여권 변경 신고 / 외국인등록사항 변경 / 여권번호 바꾸려면 → registration-information report (baseline, status optional)', () => {
  for (const q of ['여권 변경 신고', '외국인등록사항 변경', '외국인등록증에 여권번호 바꾸려면?', '새 여권 받았는데 신고해야 하나요', 'passport renewed, do I need to report']) {
    const r = run(q);
    assert(r.route.procedure === 'registration_info_report', `${q}: ${r.route.procedure} (${r.route.procedureWhy})`);
    assert(r.step.kind === 'procedure' && r.step.optionalStatus === true, `${q}: ${r.step.kind}`);
    assert(r.html.includes('data-sg-action="ask-status"'), `${q}: optional status prompt`);
    assert(r.html.includes('수수료 없음'), `${q}: no fee`);
  }
  const p = run('외국인등록증에 여권번호 바꾸려면?');
  assert(p.route.conditions.change_kind === 'passport', 'change kind');
  assert(p.html.includes('재발급되지는 않습니다'), 'passport change does not by itself trigger a card reissue (Act 35(2))');
});
check('D-2 학교 변경 → the D-2 status rule (manual) rather than the common baseline', () => {
  const r = run('D-2 학교 변경');
  assert(r.route.procedure === 'registration_info_report' && r.step.kind === 'resolved' && r.step.target === 'D-2', `${r.step.kind}/${r.step.target}`);
  assert(r.html.includes('제적증명서'), 'previous-school withdrawal certificate');
});

/* 3. status-required procedures ask instead of dead-ending */
check('체류기간 연장 / 외국인등록 (no status) → ordinary-language status question, no dead end, no checklist', () => {
  for (const [q, proc] of [['체류기간 연장', 'extension'], ['외국인등록', 'registration'], ['연장하고 싶어요', 'extension'], ['체류자격 변경', 'status_change']]) {
    const r = run(q);
    assert(r.route.procedure === proc && r.route.intent === 'PROCEDURE_ONLY' || r.route.intent === 'NATURAL_LANGUAGE_QUESTION', `${q}: ${r.route.intent}/${r.route.procedure}`);
    assert(r.step.kind === 'need-status' && r.step.dimension === '__status', `${q}: ${r.step.kind}`);
    assert(!r.html.includes(DEAD_END) && !r.html.includes('sg-doc-group-required'), q);
    assert(r.step.options.length >= 6 && !r.step.options.some((o) => /^[A-H]-\d/.test(o.ko)), 'plain-language options, not raw codes');
    assert(r.html.includes('data-sg-form="code"'), 'code entry still offered');
  }
});
check('status prompt walks to a resolved answer (marriage → F-6 → subtype), and two-level picks (study → D-2/D-4)', () => {
  const a = run('체류기간 연장', { __status: 'marriage' }, 'ko', { status: 'F-6' });
  assert(a.step.kind === 'question' && a.step.dimension === 'subtype', `after marriage: ${a.step.kind}/${a.step.dimension}`);
  const b = run('체류기간 연장', { __status: 'study' });
  assert(b.step.kind === 'need-status' && b.step.dimension === '__status2' && b.step.options.map((o) => o.id).join(',') === 'D-2,D-4', 'second-level status pick');
  const c = run('체류기간 연장', { __status: 'study' }, 'ko', { status: 'D-2' });
  assert(c.step.kind === 'resolved' && c.step.target === 'D-2', 'D-2 extension resolves');
  const u = run('체류기간 연장', { __status: 'unsure' });
  assert(u.step.kind === 'need-status' && !u.html.includes(DEAD_END), 'unsure keeps the prompt, never the dead end');
});

/* 4. composition beats keyword collisions */
check('외국인등록증 alone → ask which (reissue or first registration), never a silent guess', () => {
  const r = run('외국인등록증');
  assert(r.route.intent === 'AMBIGUOUS' && r.route.procedureAmbiguous, JSON.stringify(r.route.intent));
  assert(r.step.kind === 'question' && r.step.dimension === '__procedure' && r.step.options.map((o) => o.id).sort().join(',') === 'card_reissue,registration', 'both candidates offered');
});
check('여권 재발급 is not an immigration procedure: no fake card reissue, a pointer to the embassy + the report duty', () => {
  const r = run('여권 재발급');
  assert(r.route.procedure === null && r.route.hint === 'passport_reissue', JSON.stringify([r.route.procedure, r.route.hint]));
  assert(r.step.kind === 'no-status' && r.html.includes('대사관'), 'embassy hint');
});
check('object words never turn into the registration procedure (ARC / residence card)', () => {
  for (const q of ['ARC 재발급', 'residence card reissue', 'alien registration card lost']) assert(run(q).route.procedure === 'card_reissue', q);
});

/* 5. extraction */
check('office, program, facet and document focus are extracted separately from status/procedure', () => {
  const j = run('제주에서 F-6-1 연장할 때 체류지입증서류 필요해?');
  assert(j.route.office && j.route.office.id === 'jeju', 'office jeju');
  assert(j.route.status === 'F-6-1' && j.route.statusExact && j.route.procedure === 'extension', 'status + procedure');
  assert(j.route.facet === 'documents' && j.route.conditions.document_focus === 'residence_proof', 'facet + focus');
  assert(j.route.intent === 'NATURAL_LANGUAGE_QUESTION' && j.route.isQuestion, 'question form');
  const g = run('GKS 장학생인데 연장수수료 면제돼?');
  assert(g.route.userProgram === 'gks' && g.route.procedure === 'extension' && g.route.facet === 'fee', JSON.stringify([g.route.userProgram, g.route.procedure, g.route.facet]));
  assert(g.route.aliasQuestion && g.route.statusCandidates.join(',') === 'D-2,D-4', 'GKS implies the student statuses');
  const s = run('수원 D-2 연장'); assert(s.route.office && s.route.office.id === 'suwon', 'office suwon');
  const none = run('D-2 연장'); assert(none.route.office === null, 'no office invented');
  assert(run('D-2인데 아르바이트하려면?').route.procedure === 'part_time_work', 'part-time');
  assert(run('E-7-4 연장 준비물 알려줘').route.facet === 'documents', 'documents facet');
  assert(run('톱티어').route.intent === 'SPECIAL_PROGRAM', 'program');
  assert(run('F-6').route.intent === 'STATUS_ONLY' && run('F-6 연장').route.intent === 'STATUS_PROCEDURE', 'status intents');
});

/* 6. registry consistency */
check('every procedure has a registry entry; status-free procedures have a sourced COMMON rule', () => {
  const REQ = new Set(bundle.enums.context_requirements);
  for (const p of bundle.procedures) {
    const reg = R.registryFor(bundle, p.id);
    assert(reg && REQ.has(reg.context_requirement), `${p.id}: registry`);
    assert(reg.basis_ko && reg.basis_en, `${p.id}: basis`);
    const common = SG.commonEntry(bundle, p.id);
    if (['STATUS_INDEPENDENT', 'STATUS_OPTIONAL'].includes(reg.context_requirement)) {
      assert(common && reg.common_target === 'COMMON', `${p.id}: status-free procedure needs a COMMON rule`);
      assert(common.law_sources.length && common.law_sources.every((id) => bundle.law_sources[id]), `${p.id}: COMMON rule cites regulation`);
    } else assert(!common, `${p.id}: a COMMON rule on a status-dependent procedure`);
    for (const id of reg.law_sources) assert(bundle.law_sources[id], `${p.id}: unknown law ${id}`);
  }
  assert(R.registryFor(bundle, 'card_reissue').context_requirement === 'STATUS_INDEPENDENT', 'card reissue is status-independent (Decree 42)');
  assert(R.registryFor(bundle, 'residence_report').context_requirement === 'STATUS_INDEPENDENT', 'address report is status-independent (Act 36)');
  assert(R.registryFor(bundle, 'registration_info_report').context_requirement === 'STATUS_OPTIONAL', 'info report: status optional (Rule 49-2)');
  assert(R.registryFor(bundle, 'extension').context_requirement === 'STATUS_AND_SUBSTATUS_REQUIRED', 'extension needs status + subtype');
  assert(R.registryFor(bundle, 'status_change').context_requirement === 'CURRENT_AND_TARGET_STATUS_REQUIRED', 'status change needs current + target');
});

/* 7. language switch */
check('procedure intent and resolution survive a language switch (KO → EN)', () => {
  for (const q of ['외국인등록증 재발급', '주소 변경 신고', '체류기간 연장', 'residence card reissue']) {
    const ko = run(q, {}, 'ko'); const en = run(q, {}, 'en');
    assert(ko.step.kind === en.step.kind && ko.step.procedure === en.step.procedure, `${q}: kind/procedure drift`);
    assert(!en.html.includes(DEAD_END) && !/No status recognised/.test(en.html), `${q}: EN dead end`);
    if (ko.step.kind === 'procedure') assert(en.html.includes('The same rule applies regardless of your status'), `${q}: EN common lead`);
  }
  assert(run('residence card reissue', {}, 'en').html.includes('Residence card reissue'), 'EN procedure label');
});

/* 8. fallbacks + safety */
check('an unsupported task gets a useful fallback (common tasks + code entry), no crash, no dead-end phrasing', () => {
  const r = run('비트코인 세금 신고');
  assert(r.route.intent === 'UNKNOWN' && r.step.kind === 'no-status', 'unknown');
  assert(r.html.includes('data-sg-action="search"') && r.html.includes('외국인등록증 재발급'), 'common tasks offered');
  assert(!r.html.includes(DEAD_END), 'old dead-end copy retired');
});
check('false premises are not confirmed: original/copy varies by procedure, offices never override the baseline, GKS exemption is conditional', () => {
  const p = run('여권은 무조건 원본이랑 사본 내는 거지?');
  assert(p.route.hint === 'form_varies' && p.route.procedure === null, JSON.stringify([p.route.hint, p.route.procedure]));
  assert(p.text.includes('절차별 원문 표기에 따라 달라요') && p.text.includes('원본 + 사본 1부') && p.text.includes('표기 없음'), 'procedure-specific examples from the bundle');
  const l = run('임대차계약서는 항상 원본 사본 둘 다지?');
  assert(l.route.hint === 'form_varies' && !/원본 \+ 사본/.test(l.text.split('확인된 예시')[1] || ''), 'no invented lease form');
  const j = run('제주는 체류지서류 무조건 필요 없지?');
  assert(j.route.procedure === null && j.route.office && j.route.office.id === 'jeju' && j.route.hint === 'local_premise', JSON.stringify([j.route.procedure, j.route.hint]));
  assert(j.text.includes('전국 기준을 바꾸지 않아요') && j.text.includes('확인되지 않은 이용자 제보'), 'office report labelled, baseline kept');
  const f = run('F-6는 전국 어디서나 똑같은 서류 받지?');
  assert(f.step.kind === 'question' && !f.text.includes('똑같은 서류를 받'), 'no universal confirmation');
  const g = run('GKS면 수수료 다 면제지?');
  assert(g.text.includes('절차마다 달라요') && g.text.includes('면제 대상자도 납부'), 'conditional exemption + card fee not exempt');
});
check('HTML escapes untrusted query text in every kind', () => {
  for (const q of ['<img src=x onerror=alert(1)> 외국인등록증 재발급', '<script>x</script> 체류기간 연장', '"><b>F-6 연장']) assert(!run(q).html.includes('<img src=x') && !run(q).html.includes('<script>x'), q);
});
check('router output shape', () => {
  const r = R.route('외국인등록증 재발급', bundle, { localPractice: bundle.local_practice });
  for (const k of ['intent', 'structure', 'isQuestion', 'facet', 'status', 'substatus', 'procedure', 'procedureCandidates', 'object', 'office', 'program', 'userProgram', 'conditions', 'contextRequirement', 'needs', 'confidence']) assert(k in r, `missing ${k}`);
  assert(R.INTENTS.includes(r.intent) && r.confidence === 'HIGH' && r.needs.length === 0, 'shape values');
  assert(['HIGH', 'MEDIUM', 'LOW'].includes(r.confidence) && !/\d/.test(String(r.confidence)), 'no numeric confidence');
});

console.log('[check_search_router] report', JSON.stringify({ cases: passed + failures.length }));
if (failures.length) { console.error(`[check_search_router] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_search_router] OK — ${passed} checks passed`);
