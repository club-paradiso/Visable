#!/usr/bin/env node
/*
 * employment_analyze_cli.mjs — local QA CLI for the employment-code analyzer.
 *
 *   node scripts/employment_analyze_cli.mjs "카페에서 바리스타로 일해요"
 *   node scripts/employment_analyze_cli.mjs --json "영어학원 강사"
 *   node scripts/employment_analyze_cli.mjs --visa E-7 "IT 스타트업 개발자"
 *
 * Prints a human-readable summary by default, or raw JSON with --json.
 * No build system / npm required — plain Node ES module.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createEmploymentAnalyzer } from './employment_code_analyzer.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const readJson = (p) => JSON.parse(readFileSync(join(root, p), 'utf8'));

const argv = process.argv.slice(2);
let json = false;
let visa = null;
let locale = null;
const words = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--json') json = true;
  else if (a === '--visa') visa = argv[++i];
  else if (a === '--locale') locale = argv[++i];
  else words.push(a);
}
const text = words.join(' ').trim();
if (!text) {
  console.error('Usage: node scripts/employment_analyze_cli.mjs [--json] [--visa E-7] [--locale ko|en] "<설명>"');
  process.exit(2);
}

const analyzer = createEmploymentAnalyzer({
  data: readJson('data/jobcode_master.json'),
  lexicon: { ko: readJson('data/employment/synonyms.ko.json'), en: readJson('data/employment/synonyms.en.json') },
  sources: readJson('data/employment/classification_sources.json'),
  context: readJson('data/jobcode_master.json').employment_reporting_context
});

const res = analyzer.analyze({ text, visaStatus: visa, locale });

if (json) {
  console.log(JSON.stringify(res, null, 2));
  process.exit(0);
}

const e = res.extracted;
const line = (c) => `    [${c.confidence.toUpperCase().padEnd(6)}] ${c.code.padEnd(6)} ${c.name}  (${c.levelLabel}${c.isReportingLeaf ? ', 신고용 세부코드' : ''})\n        ↳ ${c.reason}`;

console.log(`\n■ 입력: "${text}"`);
console.log(`■ 정규화: ${res.normalizedInput}`);
console.log('\n■ 내가 입력한 내용 해석');
console.log(`    직종(하는 일): ${e.jobRole || '—'}`);
console.log(`    근무처:        ${e.workplaceType || '—'}`);
console.log(`    사업 활동:     ${e.businessActivity || '—'}`);
console.log(`    고용형태:      ${e.employmentTypeLabel || e.employmentType || '—'}`);
console.log(`    체류자격:      ${e.visaStatus || '—'}   언어: ${e.language}`);

console.log('\n■ 직종 후보 (KSCO8) — 본인이 하는 일');
console.log(res.occupationCandidates.length ? res.occupationCandidates.map(line).join('\n') : '    (후보 없음 — 하는 일을 더 구체적으로)');
console.log('\n■ 업종 후보 (KSIC11) — 근무처의 사업');
console.log(res.industryCandidates.length ? res.industryCandidates.map(line).join('\n') : '    (후보 없음 — 근무처 사업을 더 구체적으로)');

if (res.ambiguityQuestions.length) {
  console.log('\n■ 애매한 부분 (더 정확히 고르기)');
  res.ambiguityQuestions.forEach((q) => {
    console.log(`    ? ${q.question}`);
    if (q.chips && q.chips.length) console.log(`      칩: ${q.chips.join(' · ')}`);
  });
}

console.log('\n■ 공식 기준 / 주의');
res.warnings.forEach((w) => console.log(`    • ${w}`));
console.log('\n■ 출처');
res.sourceNotes.forEach((s) => console.log(`    • ${[s.classification, s.version, s.sourceName, s.sourceRef].filter(Boolean).join(' | ')}`));
console.log('');
