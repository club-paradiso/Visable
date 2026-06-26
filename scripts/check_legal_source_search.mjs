#!/usr/bin/env node
/**
 * check_legal_source_search.mjs — offline validation of the Waymaker
 * "법령·판례 근거 검색 / Legal source search" module (assets/js/legal-source-search.js).
 *
 * Loads the module's REAL pure functions (no jsdom needed) and asserts:
 *  - HTML escaping + official-source-URL allow-listing (no XSS injection vector);
 *  - law/precedent card builders escape all upstream fields and only emit a
 *    link for a valid law.go.kr URL (else a "check official text" hint);
 *  - the response→state classifier maps ok/empty/missing-key/error correctly;
 *  - KO/EN string-pack parity + the exact required labels & disclaimers;
 *  - the quick chips and panel skeleton (tabs / input / chips) are present;
 *  - no forbidden dummy / fake-professional strings in the module.
 *
 * Run: node scripts/check_legal_source_search.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);

let failures = 0, checks = 0;
function ok(cond, label, extra) {
  checks++;
  if (cond) console.log(`  PASS  ${label}`);
  else { failures++; console.log(`  FAIL  ${label}${extra ? ' — ' + extra : ''}`); }
}
function section(t) { console.log(`\n== ${t}`); }

global.currentLanguage = 'ko';
require('../assets/js/legal-source-search.js');
const L = globalThis.ParadisoLegalSearch;

section('module surface');
ok(L && typeof L === 'object', 'ParadisoLegalSearch exposed');
for (const fn of ['escapeHtml', 'safeSourceUrl', 'buildLawCardHtml', 'buildPrecedentCardHtml', 'buildResultsHtml', 'classifyResponse', 'panelHtml', 'S']) {
  ok(typeof L[fn] === 'function', `exposes ${fn}()`);
}

section('escaping + URL safety (no injection)');
ok(L.escapeHtml('<script>x</script>') === '&lt;script&gt;x&lt;/script&gt;', 'escapeHtml neutralizes tags');
ok(L.escapeHtml('a&b"c\'d') === 'a&amp;b&quot;c&#39;d', 'escapeHtml handles & " \'');
ok(L.safeSourceUrl('https://www.law.go.kr/법령/출입국관리법') === 'https://www.law.go.kr/법령/출입국관리법', 'allows www.law.go.kr');
ok(L.safeSourceUrl('http://law.go.kr/x') === 'http://law.go.kr/x', 'allows law.go.kr');
ok(L.safeSourceUrl('javascript:alert(1)') === '', 'rejects javascript: URL');
ok(L.safeSourceUrl('data:text/html,x') === '', 'rejects data: URL');
ok(L.safeSourceUrl('https://evil.com/x') === '', 'rejects non-law.go.kr host');
ok(L.safeSourceUrl('https://law.go.kr.evil.com/x') === '', 'rejects look-alike host law.go.kr.evil.com');
ok(L.safeSourceUrl('https://evillaw.go.kr/x') === '', 'rejects look-alike host evillaw.go.kr');
ok(L.safeSourceUrl('') === '', 'empty URL → empty');

section('law card builder');
const malicious = { title: '<img src=x onerror=alert(1)>', snippet: '<b>boom</b>', sourceUrl: 'https://www.law.go.kr/법령/x', type: '법률', articleNo: '제10조', promulgationDate: '20240101' };
const lawHtml = L.buildLawCardHtml(malicious, 'ko');
ok(lawHtml.indexOf('<img src=x') === -1, 'law card does NOT contain raw <img');
ok(lawHtml.indexOf('&lt;img') !== -1, 'law card escapes the malicious title');
ok(lawHtml.indexOf('<b>boom</b>') === -1 && lawHtml.indexOf('&lt;b&gt;boom') !== -1, 'law card escapes the snippet');
ok(/href="https:\/\/www\.law\.go\.kr\/[^"]*"/.test(lawHtml) && lawHtml.indexOf('rel="noopener noreferrer"') !== -1, 'law card renders a safe official-source link');
const lawNoLink = L.buildLawCardHtml({ title: 'x', sourceUrl: 'javascript:alert(1)' }, 'ko');
ok(lawNoLink.indexOf('<a ') === -1 && lawNoLink.indexOf('lss-needsrc') !== -1, 'law card with unsafe URL shows no link, shows check-official hint');

section('precedent card builder');
const precHtml = L.buildPrecedentCardHtml({ title: '<script>', court: '대법원', caseNumber: '2020두1', decisionDate: '20210115', summary: 'x', sourceUrl: 'https://www.law.go.kr/precInfoP.do?precSeq=9' }, 'ko');
ok(precHtml.indexOf('<script>') === -1 && precHtml.indexOf('&lt;script&gt;') !== -1, 'precedent card escapes title');
ok(precHtml.indexOf('lss-prec-flag') !== -1 && precHtml.indexOf('원문 확인 필요') !== -1, 'precedent card shows "원문 확인 필요"');
ok(precHtml.indexOf('대법원') !== -1 && precHtml.indexOf('2020두1') !== -1, 'precedent card shows court + case number');

section('results state machine');
ok(L.buildResultsHtml('idle', 'laws', [], 'ko').indexOf(L.S('idleTitle', 'ko')) !== -1, 'idle state renders');
ok(L.buildResultsHtml('loading', 'precedents', [], 'ko').indexOf('lss-spinner') !== -1, 'loading state renders spinner');
ok(L.buildResultsHtml('loading', 'precedents', [], 'ko').indexOf(L.S('loadingPrec', 'ko')) !== -1, 'loading precedent label');
ok(L.buildResultsHtml('missing-key', 'laws', [], 'ko').indexOf('API 설정이 필요합니다') !== -1, 'missing-key state renders');
ok(L.buildResultsHtml('error', 'laws', [], 'ko').indexOf('검색에 실패했습니다') !== -1, 'error state renders');
ok(L.buildResultsHtml('empty', 'laws', [], 'ko').indexOf('검색 결과가 없습니다') !== -1, 'empty state renders');
ok(L.buildResultsHtml('results', 'laws', [], 'ko').indexOf('검색 결과가 없습니다') !== -1, 'results with no data falls back to empty');
ok(L.buildResultsHtml('results', 'laws', [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x' }], 'ko').indexOf('lss-results') !== -1, 'results state renders cards');

section('response classifier');
ok(L.classifyResponse({ ok: true, results: [1, 2] }).state === 'results', 'ok + results → results');
ok(L.classifyResponse({ ok: true, results: [] }).state === 'empty', 'ok + no results → empty');
ok(L.classifyResponse({ ok: false, error: 'LAW_API_OC is not configured' }).state === 'missing-key', 'not-configured error → missing-key');
ok(L.classifyResponse({ ok: false, reason: 'not_configured' }).state === 'missing-key', 'not_configured reason → missing-key');
ok(L.classifyResponse({ ok: false, error: 'search_failed' }).state === 'error', 'other failure → error');
ok(L.classifyResponse(null).state === 'error', 'null → error');

section('i18n parity + required labels');
const koKeys = Object.keys(L.STR_KO).sort();
const enKeys = Object.keys(L.STR_EN).sort();
ok(JSON.stringify(koKeys) === JSON.stringify(enKeys), 'KO and EN packs have identical key sets',
  `missing in EN: ${koKeys.filter(k => !enKeys.includes(k))}; missing in KO: ${enKeys.filter(k => !koKeys.includes(k))}`);
const required = {
  title: ['법령·판례 근거 검색', 'Legal source search'],
  tabLaws: ['법령', 'Laws'],
  tabPrec: ['판례', 'Precedents'],
  inputPlaceholder: ['검색어 입력', 'Enter a search term'],
  searchBtn: ['검색', 'Search'],
  viewSource: ['공식 원문 보기', 'View official source'],
  checkOfficial: ['원문 확인 필요', 'Check official text'],
  emptyTitle: ['검색 결과가 없습니다', 'No results found'],
  missingKeyTitle: ['API 설정이 필요합니다', 'API configuration required'],
  loadingLaws: ['법령 검색 중입니다', 'Searching legal sources'],
  loadingPrec: ['판례 검색 중입니다', 'Searching precedents'],
  errorTitle: ['검색에 실패했습니다', 'Search failed']
};
for (const [key, [ko, en]] of Object.entries(required)) {
  ok(L.STR_KO[key] === ko, `KO label "${key}" = "${ko}"`, `got "${L.STR_KO[key]}"`);
  ok(L.STR_EN[key] === en, `EN label "${key}" = "${en}"`, `got "${L.STR_EN[key]}"`);
}
ok(L.STR_KO.disclaimer.includes('변호사·행정사의 법률 자문을 대체하지 않으며'), 'KO disclaimer present & cautious');
ok(L.STR_EN.disclaimer.includes('does not replace legal advice'), 'EN disclaimer present & cautious');

section('quick chips');
ok(Array.isArray(L.CHIPS) && L.CHIPS.length === 10, 'ten quick chips defined');
ok(L.CHIPS.every(c => c.label && c.labelEn && c.query), 'every chip has label + labelEn + query');
for (const need of ['출입국관리법', '체류자격 변경', '체류기간 연장', '재외동포 F-4', '결혼이민 F-6', '유학생 D-2', '난민 G-1', '강제퇴거', '사증발급', '귀화']) {
  ok(L.CHIPS.some(c => c.label === need), `chip present: ${need}`);
}

section('panel skeleton');
const panel = L.panelHtml('ko');
ok(panel.indexOf('role="tablist"') !== -1, 'panel has a tablist');
ok(panel.indexOf('data-lss-tab="laws"') !== -1 && panel.indexOf('data-lss-tab="precedents"') !== -1, 'panel has Laws + Precedents tabs');
ok(panel.indexOf('data-lss-input') !== -1 && panel.indexOf('data-lss-search') !== -1, 'panel has search input + button');
ok(panel.indexOf('lss-disclaimer') !== -1, 'panel shows the disclaimer');
ok((panel.match(/data-lss-chip=/g) || []).length === 10, 'panel renders all 10 chips');
const panelEn = L.panelHtml('en');
ok(panelEn.indexOf('Legal source search') !== -1 && panelEn.indexOf('Immigration Act') !== -1, 'EN panel uses English labels + chip glosses');

section('no dummy / fake-professional strings');
const src = readFileSync(join(ROOT, 'assets/js/legal-source-search.js'), 'utf8');
for (const bad of ['Mr.Visa', 'Mr Visa', 'lorem ipsum', '행정사 검토', '법무법인']) {
  ok(src.toLowerCase().indexOf(bad.toLowerCase()) === -1, `module free of forbidden term "${bad}"`);
}

console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
process.exit(failures ? 1 : 0);
