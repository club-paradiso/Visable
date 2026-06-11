#!/usr/bin/env node
/**
 * check_subcode_grouping.js — verifies the search-result subcode collapse UX.
 * No external dependencies.
 *
 * 1) Static checks: helpers + a11y attributes + user-facing copy in index.html.
 * 2) Behavioral checks: extracts the REAL grouping helpers + renderSubcodes from
 *    index.html, runs them in a sandbox against visa_data.json, and verifies:
 *    - broad parent queries (C-3, F-4, G-1 …) do NOT render every subcode as a
 *      full default card (collapsed group + ≤5 preview chips instead),
 *    - exact subcode queries keep the matched subcode prominent.
 *
 * Run: node audits/short-stay-country-checker/check_subcode_grouping.js
 */
'use strict';
const { readFileSync } = require('fs');
const { join } = require('path');

const ROOT = join(__dirname, '..', '..');
const indexHtml = readFileSync(join(ROOT, 'index.html'), 'utf8');
const visaData = JSON.parse(readFileSync(join(ROOT, 'visa_data.json'), 'utf8'));

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

/* ----------------------------------------------------- data relationships */
section('Parent/subcode relationships in visa_data.json');
const FAMILIES = ['C-3', 'B-2', 'F-2', 'F-6', 'D-2', 'D-10', 'E-7', 'G-1', 'F-4'];
const byCode = new Map(visaData.map(v => [v.code, v]));
const subsOf = (v) => Array.isArray(v.subcodes) ? v.subcodes : (Array.isArray(v.subCodes) ? v.subCodes : []);
for (const fam of FAMILIES) {
  const rec = byCode.get(fam);
  ok(!!rec, `top-level record exists: ${fam}`);
  if (rec) ok(subsOf(rec).length > 0, `${fam} has subcodes (${subsOf(rec).length})`);
}

/* -------------------------------------------------------- static UI checks */
section('Static UI checks (index.html)');
for (const fn of ['getParentVisaCode', 'isSubcodeOf', 'groupSearchResultsByParent',
  'shouldAutoExpandSubcodeGroup', 'renderSubcodePreview', 'renderExpandableSubcodeGroup']) {
  ok(indexHtml.includes(`function ${fn}(`), `helper exists: ${fn}`);
}
ok(indexHtml.includes('broadParentQuery'), 'renderResults wires broad-parent detection');
ok(indexHtml.includes('data-action="toggle-subcode-group"'), 'expand/collapse uses delegated action');
ok(indexHtml.includes("'toggle-subcode-group'"), 'toggle handler registered');
ok(/aria-expanded/.test(indexHtml) && indexHtml.includes('aria-controls="${groupId}"'), 'aria-expanded + aria-controls wired');
ok(indexHtml.includes('세부유형 {count}개 보기') || indexHtml.includes('세부유형 보기'), 'expand copy 세부유형 …보기 present');
ok(indexHtml.includes('세부유형 숨기기'), 'collapse copy 세부유형 숨기기 present');
ok(indexHtml.includes('처럼 검색할 수 있습니다'), 'exact-code hint copy present');
ok(indexHtml.includes('.subcode-expand-btn:focus-visible'), 'visible focus style for toggle');
ok(indexHtml.includes('subcode-preview-chip'), 'preview chips present');

/* --------------------------------------------------- behavioral sandbox */
section('Behavioral render checks (real functions from index.html)');
function extractFn(name, src) {
  const start = src.indexOf(`function ${name}(`);
  if (start === -1) throw new Error(`cannot find function ${name}`);
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) break; }
  }
  return src.slice(start, i + 1);
}
const fnSource = ['normalizeVisaCode', 'getParentVisaCode', 'isSubcodeOf', 'groupSearchResultsByParent',
  'shouldAutoExpandSubcodeGroup', 'renderSubcodePreview', 'renderExpandableSubcodeGroup', 'renderSubcodes']
  .map(n => extractFn(n, indexHtml)).join('\n');

/* minimal stubs matching index.html semantics for the rendered strings */
const KO = {
  subcodesTitle: '세부코드',
  subcodeGroupSummary: '세부유형 {count}개: {names} 등으로 나뉩니다.',
  subcodeGroupShowCount: '세부유형 {count}개 보기',
  subcodeGroupHide: '세부유형 숨기기',
  subcodeGroupHint: '정확한 세부코드를 알고 있다면 {example}처럼 검색할 수 있습니다.',
  subcodePreviewAria: '주요 세부유형 미리보기',
  manualNeedsReview: '매뉴얼 확인 필요',
  sourceChipDeprecated: '폐지/중단', sourceChipOfficial: '출처 확인', sourceChipAuto: '자동 추출', sourceChipReview: '검토 필요'
};
const sandbox = `
  const tx = (k, vars = {}) => { let v = ${JSON.stringify(KO)}[k] ?? k; Object.entries(vars).forEach(([a,b]) => { v = v.replaceAll('{'+a+'}', b); }); return v; };
  const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const hl = (t) => escapeHtml(t);
  const getVisaSubcodes = (v) => Array.isArray(v.subcodes) ? v.subcodes : (Array.isArray(v.subCodes) ? v.subCodes : []);
  const getLocalizedSubcodeName = (s) => s.nameKo || s.name || '';
  const subcodeSourceChip = () => '';
  ${fnSource}
  return { normalizeVisaCode, getParentVisaCode, isSubcodeOf, groupSearchResultsByParent, shouldAutoExpandSubcodeGroup, renderSubcodes };
`;
const fns = (new Function(sandbox))();

ok(fns.getParentVisaCode('C-3-9') === 'C-3', 'getParentVisaCode(C-3-9) === C-3');
ok(fns.getParentVisaCode('G-1-5') === 'G-1', 'getParentVisaCode(G-1-5) === G-1 (never a top-level family)');
ok(fns.getParentVisaCode('D-10-T') === 'D-10', 'getParentVisaCode(D-10-T) === D-10');
ok(fns.isSubcodeOf('C-3', 'C-3-9') === true, 'isSubcodeOf(C-3, C-3-9)');
ok(fns.isSubcodeOf('C-3', 'C-3') === false, 'isSubcodeOf(C-3, C-3) is false');
ok(fns.isSubcodeOf('B-2', 'C-3-9') === false, 'isSubcodeOf(B-2, C-3-9) is false');
const grouped = fns.groupSearchResultsByParent([{ code: 'C-3' }, { code: 'C-3-9' }, { code: 'B-2' }]);
ok(grouped.get('C-3') && grouped.get('C-3').length === 2 && grouped.get('B-2').length === 1, 'groupSearchResultsByParent groups by family');

function extractBalancedDiv(html, startIdx) {
  /* startIdx points at '<div'; walk tags to the matching close. */
  const tag = /<\/?div\b[^>]*>/g;
  tag.lastIndex = startIdx;
  let depth = 0, m;
  while ((m = tag.exec(html))) {
    depth += m[0][1] === '/' ? -1 : 1;
    if (depth === 0) return html.slice(startIdx, tag.lastIndex);
  }
  return html.slice(startIdx);
}
function countVisibleFullCards(html) {
  /* full default cards = manual-subcode-card occurrences OUTSIDE hidden containers */
  let hiddenCount = 0;
  const re = /<div id="subgroup-[^"]*" class="subcode-expand-body" hidden>/g;
  let m;
  while ((m = re.exec(html))) {
    const block = extractBalancedDiv(html, m.index);
    hiddenCount += (block.match(/manual-subcode-card/g) || []).length;
  }
  const total = (html.match(/manual-subcode-card/g) || []).length;
  return { total, visible: total - hiddenCount, hiddenCount };
}

for (const fam of FAMILIES) {
  const rec = byCode.get(fam);
  if (!rec) continue;
  const subs = subsOf(rec);
  const html = fns.renderSubcodes(rec, [fam.toLowerCase()], [], { broadParentQuery: true, queryCode: fam });
  const { visible } = countVisibleFullCards(html);
  if (subs.length > 5) {
    ok(visible === 0, `${fam} broad search: 0 full subcode cards rendered open (was ${subs.length})`, `visible=${visible}`);
    ok(html.includes('subcode-expand-btn') && html.includes('aria-expanded="false"'), `${fam} broad search: collapsed expandable group present`);
    const chips = (html.match(/class="subcode-preview-chip"/g) || []).length;
    ok(chips >= 2 && chips <= 5, `${fam} broad search: ${chips} preview chips (3–5 target)`);
  } else {
    ok(visible <= 5, `${fam} broad search: small family renders compact (${visible} cards ≤ 5)`);
  }
}

/* exact subcode query stays prominent */
const c3 = byCode.get('C-3');
const c39 = subsOf(c3).find(s => s.code === 'C-3-9');
const exactHtml = fns.renderSubcodes(c3, ['c-3-9'], [c39], { broadParentQuery: false, queryCode: 'C-3-9' });
ok(exactHtml.includes('내 상황과 관련') && exactHtml.indexOf('C-3-9') < exactHtml.indexOf('subcode-expand-btn'),
  'exact C-3-9 search: matched subcode lifted above the collapsed group');
const exactCount = countVisibleFullCards(exactHtml);
ok(exactCount.visible <= 2, `exact C-3-9 search: only the matched card is open (${exactCount.visible} visible)`);
ok(fns.shouldAutoExpandSubcodeGroup('C-3-9', subsOf(c3)) === true, 'shouldAutoExpandSubcodeGroup finds exact match');
ok(fns.shouldAutoExpandSubcodeGroup('C-3', subsOf(c3)) === false, 'shouldAutoExpandSubcodeGroup ignores parent query');

console.log(`\n${checks} checks, ${failures} failures`);
if (failures) process.exit(1);
console.log('check_subcode_grouping: ALL PASS');
