#!/usr/bin/env node
/*
 * check_search_multilingual.mjs — the home search in every UI language
 * ----------------------------------------------------------------------------
 * Visable offers 15 UI languages (index.html LANGUAGE_OPTIONS). For each one this
 * pins, through the same code the home uses (status-guidance interpret → search
 * router → search-suggest):
 *   1. a status code + "extension" in that language → F-6 × extension;
 *   2. a status-independent task (card lost / moved) → the right procedure;
 *   3. tool discovery words → the enforcement page and the short-stay checker;
 *   4. typing without tones/accents (vi, fr, es, de, tr) and Arabic without
 *      hamza reads the same as the full spelling;
 *   5. Traditional Chinese (zh-TW) reads like Simplified (via ParadisoZhT);
 *   6. folding never changes a Korean or English query.
 *
 *   node scripts/check_search_multilingual.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
new Function('window', read('assets/js/zh-traditional.js'))(globalThis);
new Function(read('assets/js/status-guidance.js'))();
new Function(read('assets/js/search-router.js'))();
new Function(read('assets/js/search-suggest.js'))();
const S = globalThis.VisableSearchSuggest, R = globalThis.VisableSearchRouter, SG = globalThis.VisableStatusGuidance;
const index = JSON.parse(read('data/search-suggest-index.json'));
const bundle = JSON.parse(read('data/status-guidance-202609.json'));

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }
const run = (q) => S.suggest(q, index, { lang: 'en' });
const show = (r) => r.items.map((i) => `${i.kind}:${i.label || i.labelKey}`).join(' | ') || '(none)';
const first = (q, pred) => run(q).items.find(pred);
const procOf = (q) => SG.interpret(q, bundle).procedure;

// Every locale in LANGUAGE_OPTIONS must appear below.
const html = read('index.html');
const locales = [...html.slice(html.indexOf('const LANGUAGE_OPTIONS'), html.indexOf('];', html.indexOf('const LANGUAGE_OPTIONS'))).matchAll(/code: '([^']+)'/g)].map((m) => m[1]);

const E = (r) => r.kind === 'tool' && r.href === 'enforcement.html';
const SH = (r) => r.kind === 'tool' && r.action === 'open-short-stay';
// [locale, extension query, [task query, procedure], enforcement query, short-stay query]
const MATRIX = [
  ['ko', 'F-6 연장', ['외국인등록증 잃어버렸어요', 'card_reissue'], '벌금 계산', '제주 무사증 국가'],
  ['en', 'F-6 extension', ['I lost my residence card', 'card_reissue'], 'overstay fine', 'visa free countries'],
  ['zh-CN', 'F-6 续签', ['外国人登录证 丢失 补办', 'card_reissue'], '罚款怎么计算', '济州免签国家'],
  ['zh-TW', 'F-6 續簽', ['外國人登錄證 遺失 補辦', 'card_reissue'], '罰款怎麼計算', '濟州免簽國家'],
  ['ja', 'F-6 在留期間更新', ['在留カード 紛失 再交付', 'card_reissue'], '罰金', '済州 ビザなし'],
  ['vi', 'F-6 gia hạn', ['mất thẻ cư trú cấp lại', 'card_reissue'], 'tiền phạt', 'miễn thị thực jeju'],
  ['tl', 'F-6 pagpapalawig', ['nawala ang residence card', 'card_reissue'], 'multa sa overstay', 'walang visa'],
  ['id', 'F-6 perpanjangan', ['kartu tinggal hilang', 'card_reissue'], 'denda overstay', 'bebas visa jeju'],
  ['ru', 'F-6 продление', ['потерял вид на жительство', 'card_reissue'], 'штраф за просрочку визы', 'без визы'],
  ['fr', 'F-6 prolongation', ['carte de séjour perdue', 'card_reissue'], 'amende séjour irrégulier', 'sans visa'],
  ['es', 'F-6 prórroga', ['perdí mi tarjeta de residencia', 'card_reissue'], 'multa por estancia irregular', 'países sin visa'],
  ['ar', 'F-6 تمديد', ['فقدان بطاقة الإقامة', 'card_reissue'], 'غرامة', 'دخول بدون تأشيرة'],
  ['de', 'F-6 Verlängerung', ['Aufenthaltskarte verloren', 'card_reissue'], 'Geldstrafe Overstay', 'visumfrei'],
  ['tr', 'F-6 uzatma', ['ikamet kartı kayboldu', 'card_reissue'], 'vize cezası', 'vizesiz ülkeler'],
  ['uk', 'F-6 продовження', ['загубив посвідку на проживання', 'card_reissue'], 'штраф', 'без візи'],
];
const MOVES = [
  ['ko', '이사했어요'], ['en', 'I moved to a new address'], ['zh-CN', '搬家 地址变更'], ['zh-TW', '搬家 地址變更'], ['ja', '引越し 住所'],
  ['vi', 'chuyển nhà địa chỉ'], ['tl', 'lumipat ng bahay bagong tirahan'], ['id', 'pindah rumah alamat'], ['ru', 'переехал новый адрес'],
  ['fr', "j'ai déménagé adresse"], ['es', 'mudanza cambio de domicilio'], ['ar', 'تغيير السكن عنوان'], ['de', 'umgezogen neue Adresse'],
  ['tr', 'taşındım adres değişikliği'], ['uk', 'переїхав нова адреса'],
];

check('every UI language is covered', () => {
  assert(locales.length === 15, `LANGUAGE_OPTIONS has ${locales.length}`);
  for (const l of locales) assert(MATRIX.some((m) => m[0] === l) && MOVES.some((m) => m[0] === l), `${l} missing from the matrix`);
});
for (const [loc, ext, [task, proc], enf, short] of MATRIX) {
  check(`${loc}: "${ext}" → F-6 × extension`, () => { const t = run(ext).items[0]; assert(t && t.code === 'F-6' && t.procedure === 'extension', show(run(ext))); });
  check(`${loc}: "${task}" → ${proc}`, () => { assert(procOf(task) === proc, `${procOf(task)} · ${show(run(task))}`); assert(first(task, (i) => i.procedure === proc), show(run(task))); });
  check(`${loc}: "${enf}" → enforcement`, () => { const t = run(enf).items[0]; assert(t && E(t), show(run(enf))); });
  check(`${loc}: "${short}" → short-stay checker`, () => { const t = run(short).items[0]; assert(t && SH(t), show(run(short))); });
}
for (const [loc, q] of MOVES) check(`${loc}: "${q}" → change-of-address report`, () => assert(procOf(q) === 'residence_report', `${procOf(q)} · ${show(run(q))}`));

/* typed without tones / accents */
const PLAIN = [
  ['F-6 gia hạn', 'F-6 gia han'], ['mất thẻ cư trú cấp lại', 'mat the cu tru cap lai'], ['tiền phạt', 'tien phat'], ['miễn thị thực jeju', 'mien thi thuc jeju'],
  ['bệnh viện chỉ định', 'benh vien chi dinh'], ['F-6 prórroga', 'F-6 prorroga'], ['países sin visa', 'paises sin visa'], ['F-6 Verlängerung', 'F-6 Verlangerung'],
  ['carte de séjour perdue', 'carte de sejour perdue'], ['ikamet kartı kayboldu', 'ikamet karti kayboldu'], ['vize cezası', 'vize cezasi'],
  ['غرامة', 'غرامه'], ['دخول بدون تأشيرة', 'دخول بدون تاشيرة'], ['F-6 İkamet uzatma', 'f-6 ikamet uzatma'],
];
for (const [full, plain] of PLAIN) {
  check(`"${plain}" reads like "${full}"`, () => {
    const a = run(full).items.map((i) => i.kind + (i.code || '') + (i.procedure || '') + (i.tool || ''));
    const b = run(plain).items.map((i) => i.kind + (i.code || '') + (i.procedure || '') + (i.tool || ''));
    assert(a.length && JSON.stringify(a) === JSON.stringify(b), `${show(run(full))}  ≠  ${show(run(plain))}`);
  });
}

/* folding is invisible for Korean and English */
check('fold leaves Korean and plain English unchanged', () => {
  for (const q of ['F-6 체류기간 연장', '외국인등록증 재발급', '이사했어요', 'f-6 extension', 'i lost my residence card', '제주 무사증 국가']) {
    const l = q.toLowerCase(); // the router folds already lower-cased text
    assert(R.fold(l) === l, `${q} → ${R.fold(l)}`);
    assert(S.fold(l) === l, `suggest fold: ${q}`);
  }
});
check('router and suggest fold agree', () => {
  for (const q of ['Tiền Phạt', 'PRÓRROGA', 'Verlängerung', 'İKAMET', 'Ёлка', 'غرامة', '續簽', 'straße']) assert(R.fold(q) === S.fold(q), q);
});
/* no new false positives for ordinary words */
check('ordinary words in other languages open no tool', () => {
  for (const q of ['السلام عليكم', 'bonjour', 'hola', 'guten tag', 'merhaba', 'привет', 'xin chào', 'xin chao', 'kumusta', 'selamat pagi']) {
    assert(!run(q).items.some((i) => i.kind === 'tool' && i.tool !== 'waymaker'), `${q}: ${show(run(q))}`);
  }
});

if (failures.length) {
  console.error(`[check_search_multilingual] FAIL — ${failures.length} failing, ${passed} passed`);
  for (const f of failures) console.error('  ✗ ' + f);
  process.exit(1);
}
console.log(`[check_search_multilingual] OK — ${passed} checks passed over ${locales.length} UI languages`);
