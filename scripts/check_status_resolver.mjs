/*
 * check_status_resolver.mjs
 * ----------------------------------------------------------------------------
 * Resolver QA for assets/js/status-guidance.js (pure functions, no DOM).
 *
 *  A. exact subcode supplied              → no unnecessary questions
 *  B. parent code + one discriminator     → resolves correctly
 *  C. multiple discriminators needed      → progressive questions
 *  D. "잘 모르겠어요"                      → safe recovery (unresolved, candidates, evidence)
 *  E. conflicting answers                 → unresolved / source-only, never fake certainty
 *  F. user changes an earlier answer      → downstream result updates
 *  G. language switch during resolver     → state preserved
 *  H. query intent changes                → procedure changes correctly
 * plus the cross-status matrix from the sprint brief.
 *
 *   node scripts/check_status_resolver.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

function run(query, answers = {}, procedure = null, lang = 'ko', status = null) {
  const interp = SG.interpret(query, bundle);
  const state = { interp, answers: { ...answers }, procedure, status, history: [], lang };
  const step = SG.nextStep(state, bundle);
  return { interp, state, step, ...SG.renderModel(step, state, bundle) };
}
function walk(query, picks, procedure = null) {
  // picks: array of option ids applied to successive questions
  const interp = SG.interpret(query, bundle);
  const state = { interp, answers: {}, procedure, status: null, history: [], lang: 'ko' };
  const steps = [];
  for (let i = 0; i < 10; i++) {
    const step = SG.nextStep(state, bundle); steps.push(step);
    if (step.kind !== 'question') break;
    const pick = picks.shift(); assert(pick !== undefined, `walk(${query}) ran out of picks at question ${step.dimension}`);
    assert(step.options.some((o) => o.id === pick) || pick === 'unsure', `walk(${query}): option ${pick} not offered for ${step.dimension} (offered: ${step.options.map((o) => o.id).join(',')})`);
    if (step.dimension === '__procedure') state.procedure = pick; else if (step.dimension === '__alias') { state.answers.__alias = pick; const o = step.options.find((x) => x.id === pick); if (o) state.status = o.targets[0]; } else state.answers[step.dimension] = pick;
  }
  return { state, steps, last: steps[steps.length - 1] };
}
const questions = (w) => w.steps.filter((s) => s.kind === 'question').map((s) => s.dimension);

/* A. exact subcode → no unnecessary questions */
check('A. F-2-7 연장 resolves directly with no question', () => { const r = run('F-2-7 연장'); assert(r.step.kind === 'resolved' && r.step.target === 'F-2-7', JSON.stringify(r.step.kind)); assert(r.interp.codes[0].exact, 'exact flag'); });
check('A. F-1-13 연장 resolves directly', () => { const r = run('F-1-13 연장'); assert(r.step.kind === 'resolved' && r.step.target === 'F-1-13'); });
check('A. E-7-4 연장 inherits the E-7 common rule and says so', () => { const r = run('E-7-4 연장'); assert(r.step.kind === 'resolved' && r.step.inherited && r.step.displayCode === 'E-7-4' && r.step.target === 'E-7'); assert(r.html.includes('E-7 공통 기준이 적용돼요')); });
check('A. E-7-1 연장 / E-8-1 연장 / E-8-7 연장 / E-9-1 연장 / E-9-5 연장 resolve without questions', () => { for (const q of ['E-7-1 연장', 'E-8-1 연장', 'E-8-7 연장', 'E-9-1 연장', 'E-9-5 연장']) { const r = run(q); assert(r.step.kind === 'resolved', `${q}: ${r.step.kind}`); } });
check('A. compact codes resolve (F27, E74, D10T, G15)', () => { assert(run('F27 연장').step.target === 'F-2-7'); assert(run('E74 연장').step.displayCode === 'E-7-4'); assert(run('D10T 연장').step.target === 'D-10-T'); assert(run('G15 연장').step.target === 'G-1-5'); });
check('A. an exact code still asks only when the subtype has phases (F-1-5, F-6-1)', () => { const w = walk('F-1-5 연장', ['first', 'childcare']); assert(questions(w).join(',') === 'f15_phase,f15_purpose', questions(w).join(',')); assert(w.last.kind === 'resolved' && w.last.scenario === 'first-extension-childcare'); const f6 = walk('F-6-1 연장', ['normal']); assert(questions(f6).join(',') === 'f61_phase' && f6.last.scenario === 'extension'); });
check('A. unknown subcode never becomes a real status (a known procedure asks for the status instead of a dead end)', () => { const r = run('F-9-9 연장'); assert(r.step.kind === 'need-status' && r.step.procedure === 'extension', `got ${r.step.kind}`); assert(!r.html.includes('체류자격을 찾지 못했어요'), 'no dead end'); assert(r.html.includes('sg-doc-group-required') === false, 'no checklist before the status is known'); const u = run('F-1-77 연장'); assert(u.interp.unknownCodes.includes('F-1-77') && u.interp.codes[0].code === 'F-1', 'falls back to the parent with a warning'); assert(u.html.includes('확인되지 않는 코드')); });

/* B. parent + one discriminating answer */
check('B. E-9 호텔 연장 → industry pre-answered → E-9-5, never manufacturing', () => { const r = run('E-9 호텔 연장'); assert(r.step.kind === 'resolved' && r.step.displayCode === 'E-9-5', JSON.stringify(r.step.kind + r.step.displayCode)); assert(!r.html.includes('E-9-1') && !r.html.includes('제조업'), 'manufacturing leaked'); });
check('B. G-1 연장 + ground → G-1-5', () => { const w = walk('G-1 연장', ['asylum']); assert(questions(w).join(',') === 'ground' && w.last.target === 'G-1-5'); });
check('B. D-4 연장 + subtype → D-4-3', () => { const w = walk('D-4 연장', ['k12']); assert(w.last.kind === 'resolved' && w.last.target === 'D-4-3'); });
check('B. D-2 연장 needs no subtype question (one rule) but keeps the course nuance in the summary', () => { const r = run('D-2 연장'); assert(r.step.kind === 'resolved' && r.step.target === 'D-2'); assert(r.html.includes('D-2-5') && r.html.includes('교환'), 'course-specific period rules must be visible'); });
check('B. D-2 아르바이트 → part-time rule with the six-month wait for visiting students', () => { const r = run('D-2 아르바이트'); assert(r.step.procedure === 'part_time_work' && r.step.kind === 'resolved'); assert(r.html.includes('6개월'), 'six-month wait'); });

/* C. progressive questions */
check('C. F-1 연장 asks stay reason, then family kind, then phase, then purpose', () => { const w = walk('F-1 연장', ['marriage_family', 'marriage_migrant', 'first', 'childcare']); assert(questions(w).join(',') === 'stay_reason,marriage_family_kind,f15_phase,f15_purpose', questions(w).join(',')); assert(w.last.kind === 'resolved' && w.last.target === 'F-1-5'); });
check('C. F-1 연장 never opens with a list of raw subcodes', () => { const r = run('F-1 연장'); assert(r.step.kind === 'question' && r.step.dimension === 'stay_reason'); assert(!r.step.options.some((o) => /^F-1-\d+$/.test(o.ko)), 'options must be plain-language, not codes'); assert(r.html.includes('여러 체류 유형이 있어요')); });
check('C. F-6 연장 → subtype → phase', () => { const w = walk('F-6 연장', ['ended', 'divorce']); assert(questions(w).join(',') === 'subtype,f63_phase' && w.last.scenario === 'after-divorce'); });
check('C. E-9 (no procedure) asks the procedure first, then resolves with the industry from the query', () => { const w = walk('E-9 호텔', ['extension']); assert(questions(w).join(',') === '__procedure'); assert(w.last.kind === 'resolved' && w.last.displayCode === 'E-9-5'); });
check('C. procedure question only offers procedures with a known state', () => { const r = run('F-5'); assert(r.step.kind === 'question' && r.step.dimension === '__procedure'); assert(!r.step.options.some((o) => o.id === 'extension'), 'F-5 must not offer extension (해당사항 없음)'); });

/* D. unsure → safe recovery */
check('D. F-1 연장 + 잘 모르겠어요 → unresolved with candidates, evidence and no checklist', () => { const r = run('F-1 연장', { stay_reason: 'unsure' }); assert(r.step.kind === 'unresolved' && r.step.candidates.length >= 10, `candidates ${r.step.candidates && r.step.candidates.length}`); assert(r.html.includes('정확한 세부유형을 아직 확인하지 못했어요')); assert(r.model.evidence.length >= 1); assert(!r.html.includes('sg-doc-group-required')); });
check('D. E-7 연장 + unsure lists the common rule and the FTA exception', () => { const r = run('E-7 연장', { subtype: 'unsure' }); assert(r.step.kind === 'unresolved'); const t = r.step.candidates.map((c) => c.target); assert(t.includes('E-7') && t.includes('E-7-91'), t.join(',')); });
check('D. unsure on the alias question falls back to the candidate statuses', () => { const r = run('배우자 비자 연장', { __alias: 'unsure' }); assert(r.step.kind === 'unresolved' && r.step.reason === 'status'); });
check('D. unsure text offers a recovery hint (residence card field)', () => { const r = run('F-1 연장'); assert(r.step.unsure_ko && r.step.unsure_ko.includes('외국인등록증')); });

/* E. conflicting answers */
check('E. contradictory answers (student parent + F-1-5 phase) do not produce a checklist for the wrong subtype', () => { const r = run('F-1 연장', { stay_reason: 'student_parent', f15_phase: 'first', f15_purpose: 'childcare' }); assert(r.step.kind === 'resolved' && r.step.target === 'F-1-13', 'the answered stay reason wins; F-1-5 phases are ignored'); assert(!r.html.includes('비취업서약서')); });
check('E. exact code contradicted by a family answer stays on the exact code', () => { const r = run('F-1-13 연장', { stay_reason: 'marriage_family' }); assert(r.step.kind === 'source-only' || (r.step.kind === 'resolved' && r.step.target === 'F-1-13'), 'must not jump to F-1-5'); assert(!r.html.includes('F-1-5 기준으로 안내해요')); });

/* F. changing an earlier answer updates downstream */
check('F. changing phase from first to subsequent changes the documents', () => { const a = run('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'first', f15_purpose: 'childcare' }); const b = run('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'subsequent', f15_purpose: 'childcare' }); assert(a.step.scenario !== b.step.scenario); assert(a.html.includes('비취업서약서') && !b.html.includes('비취업서약서')); assert(b.html.includes('재학증명서')); });

/* G. language switch preserves state */
check('G. the same answers render in EN with the same target and document count', () => { const ko = run('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'first', f15_purpose: 'childcare' }, null, 'ko'); const en = run('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'first', f15_purpose: 'childcare' }, null, 'en'); assert(ko.step.target === en.step.target && ko.step.scenario === en.step.scenario); assert(ko.model.documentGroups.length === en.model.documentGroups.length); assert(en.html.includes('Documents to prepare') && en.html.includes('Pledge not to work')); assert(!en.html.includes('준비할 서류')); });
check('G. EN copy does not leak internal enums or Korean-only labels in group titles', () => { const en = run('G-1 연장', { ground: 'industrial' }, null, 'en'); assert(en.html.includes('Required') && en.html.includes('Industrial accident')); assert(!/REQUIRED_BASELINE|CONDITIONAL_REQUIRED|SOURCE_ONLY/.test(en.html)); });

/* H. intent controls the procedure */
check('H. 연장 never defaults to 사증발급; 자격변경 opens the change flow; 외국인등록 opens registration; 근무처 변경 opens workplace', () => {
  assert(run('F-2 연장').interp.procedure === 'extension'); assert(run('F-6 자격변경').interp.procedure === 'status_change'); assert(run('F-6-1 외국인등록').interp.procedure === 'registration'); assert(run('E-9 근무처 변경').interp.procedure === 'workplace_change'); assert(run('D-2 학교 변경').interp.procedure === 'registration_info_report');
});
check('H. F-6 자격변경 asks the current status and refuses short-stay by default with the German/pregnancy exceptions', () => { const r = run('F-6 자격변경'); assert(r.step.kind === 'question' && r.step.dimension === 'current_status'); const s = run('F-6 자격변경', { current_status: 'short_stay' }); assert(s.model.transitionOutcome && s.model.transitionOutcome.state === 'GENERALLY_NOT_PERMITTED'); assert(s.html.includes('독일인') && s.html.includes('임신')); assert(!s.html.includes('sg-doc-group-required'), 'no checklist before the transition is established'); const h = run('F-6 자격변경', { current_status: 'h1' }); assert(h.model.transitionOutcome.state === 'GENERALLY_NOT_PERMITTED'); const l = run('F-6 자격변경', { current_status: 'long_term' }); assert(l.step.kind === 'source-only' && l.model.transitionOutcome.state === 'SUPPORTED', 'documents are source-only (준용 사증발급 서류)'); });
check('H. a procedure override changes the answer', () => { const a = run('D-2 연장'); const b = run('D-2 연장', {}, 'registration'); assert(a.step.procedure === 'extension' && b.step.procedure === 'registration' && b.step.kind === 'resolved'); });
check('H. natural-language aliases ask instead of guessing', () => { const r = run('학생비자 연장'); assert(r.step.kind === 'question' && r.step.dimension === '__alias'); const w = run('취업비자 연장'); assert(w.step.dimension === '__alias' && w.step.options.length >= 3); });

/* cross-status matrix */
const MATRIX = [
  ['F-3 연장', 'resolved', 'F-3'], ['F-4 연장', 'source-only', null], ['F-5 연장', 'resolved', 'F-5'], ['H-1 연장', 'resolved', 'H-1'], ['H-2 연장', 'resolved', 'H-2'], ['A-1 연장', 'resolved', 'A-1'], ['A-2 연장', 'resolved', 'A-2'], ['B-1 연장', 'resolved', 'B-1'], ['C-3 연장', 'question', null], ['C-3-2 연장', 'resolved', 'C-3-2'], ['E-10 연장', 'question', null], ['E-8 연장', 'resolved', 'E-8'], ['D-10 연장', 'question', null], ['D-8 연장', 'question', null], ['F-1-D 연장', 'resolved', 'F-1-D'], ['F-2-R 연장', 'source-only', null], ['E-7-4R 연장', 'resolved', 'E-7'], ['F-2-7S 연장', 'resolved', 'F-2-7'], ['톱티어', 'program', null], ['K-STAR', 'program', null], ['지역특화형 비자', 'program', null],
];
for (const [q, kind, target] of MATRIX) check(`matrix: ${q} → ${kind}${target ? ' ' + target : ''}`, () => { const r = run(q); assert(r.step.kind === kind, `got ${r.step.kind}`); if (target) assert(r.step.target === target, `got ${r.step.target}`); });
check('matrix: F-5 연장 is NOT_APPLICABLE and says so', () => { const r = run('F-5 연장'); assert(r.model.state === 'NOT_APPLICABLE' && r.html.includes('해당하지 않아요')); });
check('matrix: H-2 연장 flags existing holders only', () => { const r = run('H-2 연장'); assert(r.html.includes('2026-02-12') && r.html.includes('기존 소지자')); });
check('matrix: F-2-7S 연장 uses the F-2-7 rule and shows the K-STAR program', () => { const r = run('F-2-7S 연장'); assert(r.step.displayCode === 'F-2-7S' && r.model.programs.some((p) => p.id === 'k-star')); });
check('matrix: E-7-4R 연장 carries the regional program conditions', () => { const r = run('E-7-4R 연장'); assert(r.model.programs.some((p) => p.id === 'regional') && r.html.includes('지자체')); });
check('matrix: B-1 연장 is EXCEPTION_ONLY', () => { const r = run('B-1 연장'); assert(r.model.state === 'EXCEPTION_ONLY' && r.html.includes('예외')); });
check('matrix: F-4 연장 falls back to source-only evidence with a page', () => { const r = run('F-4 연장'); assert(r.step.kind === 'source-only' && r.model.evidence.length >= 1 && r.model.evidence[0].page); });
check('matrix: the A-series registration is conditional (면제 대상이나 본인이 원할 경우)', () => { const r = run('A-1 외국인등록'); assert(r.step.kind === 'resolved' && r.model.state === 'CONDITIONAL'); });
check('evidence: every resolved answer exposes at least one 2026.9 page with the manual title (regulation sources sit beside it)', () => { for (const q of ['F-2-7 연장', 'E-9 호텔 연장', 'D-2 연장', 'G-1-5 연장', 'F-6-1 외국인등록']) { const r = run(q); const manual = r.model.evidence.filter((e) => e.type === 'manual'); assert(manual.length >= 1 && manual.every((e) => e.page && e.file && e.date === '2026-09-18'), q); assert(r.model.evidence.filter((e) => e.type === 'regulation').every((e) => e.law && e.law.url && e.law.article), q + ' regulation evidence must carry article + url'); } });
check('render: no internal enum names in the Korean HTML', () => { for (const q of ['F-2-7 연장', 'F-5 연장', 'B-1 연장', 'F-6 자격변경']) { const r = run(q, q === 'F-6 자격변경' ? { current_status: 'short_stay' } : {}); assert(!/REQUIRED_BASELINE|SOURCE_ONLY|GENERALLY_NOT_PERMITTED|FULLY_STRUCTURED/.test(r.html.replace(/sg-state-[a-z_]+/g, '')), q); } });
check('render: HTML escapes untrusted query text', () => { const r = run('<img src=x onerror=alert(1)> F-1 연장'); assert(!r.html.includes('<img src=x'), 'unescaped query'); });

console.log('[check_status_resolver] resolver QA report', JSON.stringify({ flows: passed + failures.length }));
if (failures.length) { console.error(`[check_status_resolver] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_status_resolver] OK — ${passed} checks passed`);
