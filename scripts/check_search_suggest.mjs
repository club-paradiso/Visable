#!/usr/bin/env node
/*
 * check_search_suggest.mjs — home search suggestions (assets/js/search-suggest.js)
 * ----------------------------------------------------------------------------
 *  1. the derived index is current and reads queries exactly like the full
 *     guidance bundle (same codes, procedures and unknown-code flags);
 *  2. the mandatory search matrix: exact codes and subcodes, spacing variants,
 *     status × procedure, procedure-only, colloquial Korean and English
 *     situations, issuance vs extension, tools, unknown codes, empty input;
 *  3. invariants over a broad query corpus: every suggested code exists in the
 *     bundle, every row that searches reads back as the same status and
 *     procedure, subcodes always name their parent, tool destinations are an
 *     allow-list, ranking is deterministic and sorted;
 *  4. the editorial examples on the home resolve to real procedures;
 *  5. router phrases and the subcode reader stay narrow (no false positives);
 *  6. local ranking is fast enough to run on every keystroke.
 *
 *   node scripts/check_search_suggest.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildIndex, serialize, OUT } from './build_search_suggest_index.mjs';
import { loadCivic } from './build_landing_shell.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
const indexText = readFileSync(join(ROOT, OUT), 'utf8');
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-suggest.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;
const S = globalThis.VisableSearchSuggest;
const index = JSON.parse(indexText);

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
const run = (q, lang = 'ko') => S.suggest(q, index, { lang });
const top = (q, lang) => run(q, lang).items[0] || null;
const show = (r) => r.items.map((i) => `${i.kind}:${i.label || i.labelKey}`).join(' | ');

/* 1. derived index ------------------------------------------------------- */
check('index is current with the guidance bundle', () => assert(indexText === serialize(buildIndex()), `run: node scripts/build_search_suggest_index.mjs`));
check('index carries no UNVERIFIED procedure state', () => {
  for (const [code, c] of Object.entries(index.codes)) for (const [pid, st] of Object.entries(c.procedures)) assert(st.s !== 'UNVERIFIED', `${code}/${pid}`);
});

/* 2. mandatory matrix ---------------------------------------------------- */
check('E-7-1 → the exact subcode, under its parent', () => {
  const t = top('E-7-1');
  assert(t && t.kind === 'substatus' && t.code === 'E-7-1' && t.match === 'exact', show(run('E-7-1')));
  assert(t.sub.some((s) => s.key === 'subOf' && /^E-7 /.test(s.vars.parent)), 'subcode names its parent');
  assert(!run('E-7-1').items.some((i) => i.kind === 'status' && i.code === 'E-7'), 'the parent is not offered as the match for a subcode');
});
check('e 7 1 / e71 / Ｅ－７－１ normalise to E-7-1 (a code that exists)', () => {
  for (const q of ['e 7 1', 'e71', 'E7-1', 'Ｅ－７－１', ' E-7-1 ']) { const t = top(q); assert(t && t.code === 'E-7-1' && t.kind === 'substatus', `${q}: ${show(run(q))}`); }
});
check('e 7 99 never becomes a code: unknown-code note + parent only', () => {
  const r = run('e 7 99');
  assert(r.notes.some((n) => (n.key === 'unknownCode' || n.key === 'notACode') && n.vars.code === 'E-7-99'), JSON.stringify(r.notes));
  assert(r.items.every((i) => !i.code || i.code === 'E-7'), show(r));
});
check('F-6 체류기간 연장 → F-6 × extension first', () => {
  const t = top('F-6 체류기간 연장');
  assert(t && t.kind === 'status_procedure' && t.code === 'F-6' && t.procedure === 'extension' && t.match === 'strong', show(run('F-6 체류기간 연장')));
  assert(t.sub.some((s) => s.key === 'domainStay'), 'marked as a stay procedure');
});
check('D-2 외국인등록 → D-2 × registration first', () => {
  const t = top('D-2 외국인등록');
  assert(t && t.code === 'D-2' && t.procedure === 'registration', show(run('D-2 외국인등록')));
});
check('주소 바꿨어요 / I moved to a different apartment → residence report (status-independent)', () => {
  for (const q of ['주소 바꿨어요', '이사했어요', 'I moved to a different apartment']) {
    const t = top(q);
    assert(t && t.kind === 'procedure' && t.procedure === 'residence_report', `${q}: ${show(run(q))}`);
    assert(t.sub.some((s) => s.key === 'procAnyStatus'), 'said to be the same for every status');
  }
});
check('I changed my workplace / 직장 바꿨어요 / 회사 옮겼어요 → workplace change', () => {
  for (const q of ['I changed my workplace', 'I need to change my workplace', '직장 바꿨어요', '회사를 옮겼어요', 'I changed my job']) {
    const t = top(q, 'en');
    assert(t && t.procedure === 'workplace_change', `${q}: ${show(run(q, 'en'))}`);
    assert(t.sub.some((s) => s.key === 'procNeedsStatus'), 'asks for the status (the procedure is status-dependent)');
  }
});
check('G-1-5 → the subcode, never promoted to a top-level family', () => {
  const r = run('G-1-5'); const t = r.items[0];
  assert(t && t.code === 'G-1-5' && t.kind === 'substatus', show(r));
  assert(t.sub.some((s) => s.key === 'subOf' && /^G-1 /.test(s.vars.parent)), 'names G-1 as its parent');
  assert(!r.items.some((i) => i.kind === 'status' && i.code === 'G-1-5'), 'not rendered as a status');
});
check('C-3 비자 발급 → visa issuance, never extension', () => {
  const r = run('C-3 비자 발급'); const t = r.items[0];
  assert(t && t.code === 'C-3' && t.procedure === 'visa_issuance', show(r));
  assert(t.sub.some((s) => s.key === 'domainVisa'), 'marked as a visa (before-entry) procedure');
  assert(!r.items.some((i) => i.procedure === 'extension'), 'no extension row for an issuance query');
});
check('비자 연장 → extension of stay, not visa issuance', () => {
  const r = run('비자 연장'); const t = r.items[0];
  assert(t && t.procedure === 'extension', show(r));
  assert(!r.items.some((i) => i.procedure === 'visa_issuance'), show(r));
});
check('E-7-4 소득 → E-7-4 first (subcode not buried under E-7)', () => {
  const r = run('E-7-4 소득');
  assert(r.items[0] && r.items[0].code === 'E-7-4' && r.items[0].kind === 'substatus', show(r));
  assert(!r.items.some((i) => i.kind === 'status' && i.code === 'E-7'), 'no generic parent row');
});
check('통합신청서 → Form Helper', () => {
  for (const q of ['통합신청서', '신청서 작성', 'integrated application form']) {
    const t = top(q, 'en');
    assert(t && t.kind === 'tool' && t.href === 'form-helper.html', `${q}: ${show(run(q, 'en'))}`);
  }
});
check('매뉴얼 / manual → the manual reader', () => {
  for (const q of ['매뉴얼', '매뉴얼 원문 읽기', 'read the manual']) {
    const t = top(q, 'en');
    assert(t && t.kind === 'tool' && t.href === 'manual.html', `${q}: ${show(run(q, 'en'))}`);
  }
});
check('XYZ-999 → nothing matched, a not-a-code note', () => {
  for (const q of ['XYZ-999', 'Z-3', 'K-99']) {
    const r = run(q);
    assert(!r.items.some((i) => i.code), `${q}: ${show(r)}`);
    assert(r.notes.some((n) => n.key === 'notACode'), `${q}: ${JSON.stringify(r.notes)}`);
  }
});
check('words that start with A–H are not code prefixes (family, english, go, bank, child)', () => {
  for (const q of ['family', 'english', 'go', 'bank', 'child', 'diploma']) {
    const r = run(q, 'en');
    assert(!r.items.some((i) => i.match === 'prefix' || i.match === 'exact'), `${q}: ${show(r)}`);
  }
});
check('a number with a unit after a code is a duration, not a subcode', () => {
  for (const [q, code] of [['F-6 3개월 연장', 'F-6'], ['F-6 1년 연장', 'F-6'], ['D-2 2년', 'D-2'], ['E-9 3 years', 'E-9'], ['F-6 2 months extension', 'F-6']]) {
    const i = SG.interpret(q, bundle);
    assert(i.codes[0] && i.codes[0].code === code && !i.unknownCodes.length, `${q} → ${JSON.stringify(i.codes)}`);
    assert(top(q).code === code, `${q}: ${show(run(q))}`);
  }
});
check('numbers inside a sentence are not code-shaped', () => {
  for (const q of ['I am 25', 'a 3 month stay', '집 2 곳']) assert(!run(q, 'en').notes.length, `${q}: ${JSON.stringify(run(q, 'en').notes)}`);
});
check('empty and whitespace input → nothing', () => {
  for (const q of ['', '   ', '​', null, undefined]) { const r = run(q); assert(r.items.length === 0 && r.notes.length === 0, JSON.stringify(q)); }
});
check('natural-language questions get the procedure, and Waymaker last', () => {
  const r = run('비자 연장하려면 뭐 필요해?');
  assert(r.items[0].procedure === 'extension', show(r));
  assert(r.items[r.items.length - 1].kind === 'tool' && r.items[r.items.length - 1].href === 'ai.html', 'Waymaker offered for the open question');
});
check('한국에 와서 처음 등록하려고 해요 / D-2 student registration documents → registration', () => {
  assert(top('한국에 와서 처음 등록하려고 해요').procedure === 'registration');
  const t = top('D-2 student registration documents', 'en');
  assert(t.code === 'D-2' && t.procedure === 'registration', show(run('D-2 student registration documents', 'en')));
});
check('E-7 → the status, its likely procedures and its subcodes', () => {
  const r = run('E-7');
  assert(r.items[0].code === 'E-7' && r.items[0].kind === 'status' && r.items[0].match === 'exact', show(r));
  assert(r.items.some((i) => i.kind === 'status_procedure' && i.code === 'E-7'), 'a code × procedure row');
  assert(r.items.some((i) => i.kind === 'substatus' && i.code === 'E-7-1'), 'E-7-1 offered as a continuation');
});
check('alias groups ask, they do not pick: 유학생 연장 → D-2 and D-4', () => {
  const r = run('유학생 연장');
  assert(r.items[0].procedure === 'extension' && !r.items[0].code, show(r));
  assert(['D-2', 'D-4'].every((c) => r.items.some((i) => i.code === c)), show(r));
});
check('English UI: labels in English, queries the search reads', () => {
  const r = run('E-7', 'en');
  assert(r.items.every((i) => i.kind === 'tool' || i.labelLang === 'en'), 'labelLang en');
  const change = r.items.find((i) => i.procedure === 'status_change');
  assert(change && change.label === 'E-7 Change of status' && change.query === 'E-7 Change of status', JSON.stringify(change));
});

/* 3. invariants over a corpus -------------------------------------------- */
const corpus = new Set(['E', 'E-', 'E-7', 'E-7-', 'E-7-S', 'F-', 'F-2-7', 'D-10-T', 'F-5-T', 'E-7-T', 'F-2-T', 'D-1', 'A-3', 'H-2', 'B-2-2', 'G-1', '난민', '결혼이민', '유학', '취업비자', '배우자 연장', '외국인등록증', '등록증 재발급', '재입국', '시간제 취업', '아르바이트', '체류자격 변경', 'D-2에서 E-7으로 변경', 'F-4 동포', '하이코리아 예약', '관할 출입국관서', '귀화', 'Waymaker', 'passport renewal', '여권 재발급', 'e-visa', 'K-ETA', 'student visa extension', 'E-9 이직', '근무처 변경', 'D-8 visa', 'what documents for F-6 extension?', '수수료 얼마', '체류지 변경']);
for (const code of Object.keys(bundle.codes)) if (/^[A-H]-\d/.test(code) && !code.includes('~')) { corpus.add(code); corpus.add(code.toLowerCase().replace(/-/g, ' ')); }
for (const p of bundle.procedures) { corpus.add(p.ko); corpus.add(p.en); corpus.add('F-6 ' + p.ko); corpus.add('E-7-1 ' + p.en); }
const TOOL_HREFS = new Set(['form-helper.html', 'ai.html', 'new-home.html', 'manual.html']);
const TOOL_ACTIONS = new Set(['open-hikorea-guide', 'open-jurisdiction-modal']);
let rows = 0;
for (const q of corpus) {
  for (const lang of ['ko', 'en']) {
    const r = run(q, lang);
    check(`invariants: ${lang} "${q}"`, () => {
      assert(r.items.length <= 7, 'limit');
      for (let i = 1; i < r.items.length; i++) assert(r.items[i - 1].score >= r.items[i].score, 'sorted by score');
      const again = run(q, lang);
      assert(JSON.stringify(again.items) === JSON.stringify(r.items), 'deterministic');
      const keys = new Set();
      for (const it of r.items) {
        rows += 1;
        const key = it.kind + '|' + (it.query || it.href || it.action);
        assert(!keys.has(key), 'no duplicate rows'); keys.add(key);
        if (it.code) {
          const c = bundle.codes[it.code];
          assert(c && (c.kind === 'status' || c.kind === 'substatus'), `${it.code} exists in the bundle as a status`);
          assert(it.label.indexOf(it.code) === 0, 'label starts with the code');
          if (c.kind === 'substatus') assert(it.kind === 'tool' || it.sub.some((s) => s.key === 'subOf' && s.vars.parent.indexOf(c.parent) === 0), `${it.code} names its parent`);
        }
        if (it.procedure) assert(bundle.procedures.some((p) => p.id === it.procedure), `${it.procedure} exists`);
        if (it.procedure && it.code) assert(bundle.codes[it.code].procedures[it.procedure] && bundle.codes[it.code].procedures[it.procedure].s !== 'UNVERIFIED', `${it.code} × ${it.procedure} is a recorded state`);
        if (it.query) {
          const back = SG.interpret(it.query, bundle);
          assert((back.codes[0] ? back.codes[0].code : null) === (it.code || null), `"${it.query}" reads back as ${back.codes[0] && back.codes[0].code}, not ${it.code}`);
          assert((back.procedure || null) === (it.procedure || null), `"${it.query}" reads back as ${back.procedure}, not ${it.procedure}`);
          assert(!back.unknownCodes.length, `"${it.query}" has no unknown code`);
        }
        if (it.kind === 'tool') assert((it.href && TOOL_HREFS.has(it.href)) || (it.action && TOOL_ACTIONS.has(it.action)), 'tool destination allow-listed');
        assert(!/[<>]/.test(it.label || ''), 'labels are plain text');
      }
    });
  }
}
check('the index reads every corpus query like the full bundle', () => {
  const diff = [];
  for (const q of corpus) {
    const a = SG.interpret(q, index), b = SG.interpret(q, bundle);
    const sig = (r) => JSON.stringify([r.codes.map((c) => c.code), r.unknownCodes, r.procedure, r.procedureCandidates, r.aliasCandidates]);
    if (sig(a) !== sig(b)) diff.push(q);
  }
  assert(!diff.length, diff.slice(0, 5).join(', '));
});

/* 4. examples on the home ------------------------------------------------- */
check('home examples are queries the search resolves', () => {
  const civic = loadCivic();
  const html = civic.homeHtml((k) => civic.copy.ko[k], { langCode: 'ko' });
  const queries = [...html.matchAll(/data-cs-query="([^"]+)"/g)].map((m) => m[1]);
  assert(queries.length >= 3, 'examples present');
  for (const q of queries) {
    const r = SG.interpret(q, bundle);
    assert(r.procedure, `${q} resolves to a procedure`);
    const code = (q.match(/^[A-H]-\d+/) || [])[0];
    if (code) assert(r.codes[0] && r.codes[0].code === code, `${q} keeps ${code}`);
    assert(top(q) && top(q).procedure === r.procedure, `${q}: the first suggestion is the same procedure`);
  }
});

/* 5. narrow router phrases and subcode reading ---------------------------- */
check('an explicit procedure word beats the colloquial phrase', () => {
  assert(SG.interpret('직장 바꿨는데 체류자격 변경해야 하나요', bundle).procedure === 'status_change');
  assert(SG.interpret('회사 근무처 신고', bundle).procedure === 'workplace_report');
});
check('first-registration phrase needs an arrival cue', () => {
  assert(SG.interpret('사업자 등록하려고 해요', bundle).procedure !== 'registration');
  assert(SG.interpret('입국 후 등록하려면', bundle).procedure === 'registration');
});
check('a word after a code is never read as a subcode', () => {
  for (const [q, code] of [['E-7 Change of status', 'E-7'], ['C-3 Visa issuance', 'C-3'], ['F-6 extension of stay', 'F-6'], ['D-2 Study', 'D-2']]) {
    const r = SG.interpret(q, bundle);
    assert(r.codes[0] && r.codes[0].code === code && !r.unknownCodes.length, `${q}: ${JSON.stringify(r.codes)} ${r.unknownCodes}`);
  }
  for (const [q, code] of [['E-7-S', 'E-7-S'], ['E7S', 'E-7-S'], ['e71', 'E-7-1'], ['e 7 1', 'E-7-1'], ['D-8-4S', 'D-8-4S'], ['E-7 4', 'E-7-4'], ['E-7-91FTA', 'E-7-91FTA'], ['F-2-7 연장', 'F-2-7']]) {
    const r = SG.interpret(q, bundle);
    assert(r.codes[0] && r.codes[0].code === code, `${q} → ${JSON.stringify(r.codes)}`);
  }
});

/* 6. speed ---------------------------------------------------------------- */
check('local ranking is fast enough for every keystroke', () => {
  const list = [...corpus]; const times = [];
  for (let k = 0; k < 3; k++) for (const q of list) { const t0 = performance.now(); run(q); times.push(performance.now() - t0); }
  times.sort((a, b) => a - b);
  const p95 = times[Math.floor(times.length * 0.95)];
  console.log(`[check_search_suggest] ${list.length} queries × 3 · median ${times[Math.floor(times.length / 2)].toFixed(2)} ms · p95 ${p95.toFixed(2)} ms (Node)`);
  assert(p95 < 20, `p95 ${p95.toFixed(2)} ms`);
});

console.log(`[check_search_suggest] corpus ${corpus.size} queries × 2 languages, ${rows} suggestion rows verified`);
if (failures.length) {
  console.error(`[check_search_suggest] FAIL — ${failures.length} failing, ${passed} passed`);
  failures.slice(0, 40).forEach((f) => console.error('  ✗ ' + f));
  process.exit(1);
}
console.log(`[check_search_suggest] OK — ${passed} checks passed`);
