#!/usr/bin/env node
/*
 * check_employment_multilingual.mjs
 * ----------------------------------------------------------------------------
 * Regression tests for "describe your work in any language" in the
 * employment-code analyzer (data/employment/multilingual_pivot.json +
 * matchMultilingualPivot in scripts/employment_code_analyzer.mjs).
 *
 * Asserts:
 *   - PARITY: a foreign-language sentence reaches the SAME top official
 *     occupation/industry codes as the equivalent Korean sentence.
 *   - The typed language is detected (independent of the UI language).
 *   - No hallucinated code: every candidate exists in jobcode_master.json.
 *   - No false translation: words that merely look alike in another language
 *     (хотел "wanted" vs отель "hotel", ครอบครัว "family" vs ครัว "kitchen",
 *     English "marketing"/"cuisine"/"academia") are not translated.
 *   - Unspaced chat-style Korean ("공장에서일합니당") is understood.
 *   - The pivot file carries no classification codes.
 *
 * Run:  node scripts/check_employment_multilingual.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';
import { loadEmploymentAnalyzerDeps } from './employment_data_loader.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const deps = loadEmploymentAnalyzerDeps();
const analyzer = createEmploymentAnalyzer(deps);
const validCodes = { occupation: new Set(), industry: new Set() };
for (const r of deps.data.data) if (validCodes[r.type]) validCodes[r.type].add(String(r.code));

let failures = 0;
let checks = 0;
const fail = (msg) => { failures++; console.error(`  ✗ ${msg}`); };
const ok = (cond, msg) => { checks++; if (!cond) fail(msg); };
const top = (r, track) => {
  const list = track === 'occupation' ? r.occupationCandidates : r.industryCandidates;
  return list && list[0] ? String(list[0].code) : null;
};

// [input, expected input language, Korean equivalent]
const PARITY = [
  ['Tôi làm phụ bếp ở nhà hàng', 'vi', '식당 주방보조'],
  ['toi lam cong nhan nha may', 'vi', '공장'],
  ['Saya bekerja di pabrik', 'id', '공장'],
  ['nagtatrabaho ako sa pabrika', 'tl', '공장'],
  ['Я работаю на заводе', 'ru', '공장'],
  ['Я повар в ресторане', 'ru', '식당 요리사'],
  ['ฉันทำงานในโรงงาน', 'th', '공장'],
  ['मैं फैक्ट्री में काम करता हूँ', 'hi', '공장'],
  ['Би үйлдвэрт ажилладаг', 'mn', '공장'],
  ['Men zavodda ishlayman', 'uz', '공장'],
  ['Fabrikada çalışıyorum', 'tr', '공장'],
  ['工場で働いています', 'ja', '공장'],
  ['trabajo en un restaurante', 'es', '식당'],
  ['je travaille dans une usine', 'fr', '공장'],
  ['Ich arbeite in einer Fabrik', 'de', '공장'],
  ['أعمل في مصنع', 'ar', '공장'],
  ['ខ្ញុំធ្វើការនៅរោងចក្រ', 'km', '공장'],
  ['Tôi dọn phòng ở khách sạn', 'vi', '호텔 객실 청소'],
  ['Saya nelayan di kapal ikan', 'id', '어선'],
  ['Я работаю водителем', 'ru', '운전기사'],
  ['ฉันเป็นพนักงานเสิร์ฟ', 'th', '서빙'],
  ['Trabajo en la construcción', 'es', '건설현장'],
  ['construction worker', 'en', '건설현장'],
];

for (const [input, lang, ko] of PARITY) {
  const r = analyzer.analyze({ text: input });
  const k = analyzer.analyze({ text: ko });
  ok(r.inputLanguage === lang, `"${input}" detected as ${r.inputLanguage}, expected ${lang}`);
  ok(Array.isArray(r.translatedTerms) && r.translatedTerms.length > 0, `"${input}" translated nothing`);
  for (const track of ['occupation', 'industry']) {
    const want = top(k, track);
    if (!want) continue;
    ok(top(r, track) === want, `"${input}" ${track} top ${top(r, track)} ≠ Korean "${ko}" top ${want}`);
  }
  for (const c of [...r.occupationCandidates, ...r.industryCandidates]) {
    ok(validCodes[c.classification] && validCodes[c.classification].has(String(c.code)),
      `"${input}" returned code ${c.code} not in the official ${c.classification} table`);
  }
  ok(!(r.specialStates || []).some((s) => s.id === 'mixed_language'),
    `"${input}" was understood but still asked to be rewritten`);
}

// Look-alike words must NOT be translated.
const NO_PIVOT = [
  'Я хотел работать',            // хотел (wanted) ≠ отель (hotel)
  'ฉันอยู่กับครอบครัว',            // ครอบครัว (family) ≠ ครัว (kitchen)
  'marketing manager',          // ≠ Turkish market
  'chef at a Korean cuisine restaurant', // English cuisine ≠ French kitchen
  'I work in academia',         // ≠ Spanish academia (cram school)
  'Tôi sống ở Hàn Quốc',        // Hàn Quốc (Korea) ≠ hàn (weld)
  'فهمت المعلومات',              // معلومات (information) ≠ teacher
];
for (const input of NO_PIVOT) {
  const r = analyzer.analyze({ text: input });
  ok((r.translatedTerms || []).length === 0,
    `"${input}" falsely translated: ${(r.translatedTerms || []).map((h) => `${h.surface}→${h.ko}`).join(', ')}`);
}

// Unspaced, chat-style Korean.
for (const [input, ko] of [['공장에서일합니당', '공장'], ['식당주방보조해여', '식당 주방보조'], ['택배상하차', '택배 상하차']]) {
  const r = analyzer.analyze({ text: input });
  const k = analyzer.analyze({ text: ko });
  ok(top(r, 'occupation') === top(k, 'occupation'), `"${input}" occupation ${top(r, 'occupation')} ≠ "${ko}" ${top(k, 'occupation')}`);
  ok(r.inputLanguage === 'ko', `"${input}" detected as ${r.inputLanguage}`);
}

// Unrecognised foreign input gets the "use simpler words" state, not silence.
{
  const r = analyzer.analyze({ text: 'Mi trabajo es muy interesante' });
  ok(r.noOfficialCodeFound === true, 'nonsense Spanish unexpectedly matched a code');
  ok((r.specialStates || []).some((s) => s.id === 'mixed_language'),
    'unrecognised foreign input did not offer the rewrite state');
}

// The pivot file may hold translations only — never codes.
{
  const pivot = JSON.parse(readFileSync(join(root, 'data/employment/multilingual_pivot.json'), 'utf8'));
  for (const e of pivot.entries) {
    const keys = Object.keys(e).sort().join(',');
    ok(keys === 'id,ko,surface', `pivot entry ${e.id} has unexpected keys: ${keys}`);
    ok(!/\d/.test(e.ko), `pivot entry ${e.id} Korean term contains a digit (looks like a code): ${e.ko}`);
  }
}

console.log(`\nEmployment multilingual input: ${checks} checks, ${failures} failure(s).`);
if (failures > 0) process.exit(1);
console.log('OK — foreign-language input reaches the same official codes as Korean, look-alike words are not mistranslated, no codes in the pivot file.');
