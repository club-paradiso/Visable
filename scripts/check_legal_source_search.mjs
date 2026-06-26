#!/usr/bin/env node
/**
 * check_legal_source_search.mjs — offline validation of the Waymaker
 * "Waymaker 리걸 리서치 / Waymaker Legal Research" module (assets/js/legal-source-search.js).
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
  title: ['Waymaker 리걸 리서치', 'Waymaker Legal Research'],
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
ok(L.STR_EN.disclaimer.includes('does not replace advice from a qualified professional'), 'EN disclaimer present & cautious');

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
ok(panelEn.indexOf('Waymaker Legal Research') !== -1 && panelEn.indexOf('Immigration Act') !== -1, 'EN panel uses English labels + chip glosses');

section('research depth — labels, selector, auto-select');
ok(Array.isArray(L.DEPTHS) && L.DEPTHS.join(',') === 'fast,basic,pro', 'DEPTHS = fast/basic/pro (internal names)');
const depthRequired = {
  depthFast: ['빠른 확인', 'Quick check'], depthBasic: ['기본 리서치', 'Standard research'], depthPro: ['심층 리서치', 'Deep research'],
  researchDepthLabel: ['리서치 깊이', 'Research depth'], tabResearch: ['리걸 리서치', 'Legal Research'],
};
for (const [key, [ko, en]] of Object.entries(depthRequired)) {
  ok(L.STR_KO[key] === ko, `KO label "${key}" = "${ko}"`, `got "${L.STR_KO[key]}"`);
  ok(L.STR_EN[key] === en, `EN label "${key}" = "${en}"`, `got "${L.STR_EN[key]}"`);
}
ok(L.STR_KO.depthFastDesc === '빠른 확인: 핵심 경로와 근거 후보를 짧게 확인합니다.', 'KO fast description exact');
ok(L.STR_KO.depthBasicDesc === '기본 리서치: 공식자료 기반으로 쟁점과 다음 확인사항을 정리합니다.', 'KO basic description exact');
ok(L.STR_KO.depthProDesc === '심층 리서치: 법령·판례·실무자료를 함께 검토해 리서치 메모 형태로 정리합니다.', 'KO pro description exact');
ok(L.STR_EN.depthFastDesc === 'Quick check: Quickly identifies key routes and source candidates.', 'EN fast description exact');
const depthSel = L.buildDepthSelectorHtml('basic', 'ko');
ok((depthSel.match(/data-lss-depth=/g) || []).length === 3, 'depth selector renders 3 options');
ok(depthSel.indexOf('aria-checked="true"') !== -1 && depthSel.indexOf('빠른 확인') !== -1, 'depth selector marks current + shows labels');
ok(L.clientAutoDepth('F-4?') === 'fast', 'auto-depth: short → fast');
ok(L.clientAutoDepth('강제퇴거 다툴 수 있어?') === 'pro', 'auto-depth: keyword → pro');
ok(L.clientAutoDepth('귀화 불허 어떻게 다퉈?') === 'pro', 'auto-depth: 불허 → pro');
ok(L.clientAutoDepth('D-2에서 D-10으로 바꾸려면 서류가 뭐가 필요한가요') === 'basic', 'auto-depth: normal → basic');

section('research result render (deterministic backend envelope)');
const proResult = {
  ok: true, depth: 'pro', depthLabel: '심층 리서치', depthAutoSelected: true, mode: 'memo', locale: 'ko',
  headings: ['리서치 메모', '1. 쟁점', '2. 사실관계에서 중요한 부분', '3. 관련 법령', '4. 관련 판례 또는 판례 검색 결과', '5. 출입국 실무상 확인할 자료', '6. 적용 가능성', '7. 위험 신호', '8. 부족한 사실관계', '9. 다음 확인사항', '10. 출처', '주의'],
  issues: ['강제퇴거명령과 출국명령의 요건·효과 구분'], lawSearchTerms: ['출입국관리법 강제퇴거'], precedentSearchTerms: ['강제퇴거명령 취소'],
  laws: [{ title: '출입국관리법', type: '법률', snippet: '<img src=x onerror=alert(1)>', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }],
  precedents: [{ title: '취소', caseNumber: '2020두1', summary: 'y', sourceUrl: 'https://www.law.go.kr/precInfoP.do?precSeq=1', strengthLabel: '관련 근거' }],
  riskFlags: ['입국금지·재입국 제한 가능성'], missingFacts: ['처분서 송달일'], nextChecks: ['1345에 사실관계 확인'],
  limitations: ['이 정리는 검색·구조화 결과이며 법적 결론이 아닙니다.'],
  sourceGroups: [{ group: 'law', label: '법령', cards: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }] }],
  disclaimer: '법령·판례 리서치는 공식 원문 확인을 돕기 위한 정리이며, 변호사·행정사의 법률 자문이나 최종 판단을 대체하지 않습니다.'
};
const proHtml = L.buildResearchHtml(proResult, 'ko');
ok(proHtml.indexOf('심층 리서치') !== -1, 'pro render shows depth label');
ok(proHtml.indexOf('리서치 메모') !== -1, 'pro render shows memo title');
ok(proHtml.indexOf('강제퇴거명령과 출국명령의 요건') !== -1, 'pro render shows issues');
ok(proHtml.indexOf('입국금지') !== -1, 'pro render shows risk flags');
ok(proHtml.indexOf('처분서 송달일') !== -1, 'pro render shows missing facts');
ok(proHtml.indexOf('직접 근거') !== -1, 'pro render shows source-strength label');
ok(proHtml.indexOf('lss-rgroup-title') !== -1, 'pro render groups sources by type');
ok(proHtml.indexOf('<img src=x') === -1 && proHtml.indexOf('&lt;img') !== -1, 'pro render escapes malicious law snippet');
ok(proHtml.indexOf('대체하지 않습니다') !== -1, 'pro render shows disclaimer');
const fastResult = { ok: true, depth: 'fast', depthLabel: '빠른 확인', locale: 'ko', headings: ['빠른 요약', '관련 경로', '확인할 근거', '주의'], issues: ['경로'], lawSearchTerms: ['출입국관리법'], laws: [], precedents: [], riskFlags: [], missingFacts: [], nextChecks: [], limitations: ['x'], disclaimer: 'd' };
const fastHtml = L.buildResearchHtml(fastResult, 'ko');
ok(fastHtml.indexOf('리서치 메모') === -1, 'fast render omits the memo title');
ok(fastHtml.indexOf('위험 신호') === -1, 'fast render omits risk-flag section');
ok(L.buildResearchHtml({ ok: false, error: 'LAW_API_OC is not configured' }, 'ko').indexOf('API 설정이 필요합니다') !== -1, 'research missing-key → config state');
ok(L.buildResearchHtml({ ok: false, error: 'search_failed' }, 'ko').indexOf('검색에 실패했습니다') !== -1, 'research failure → error state');

section('AI synthesis — labels, status badges, synthesis render');
const synthRequired = {
  synthToggle: ['AI 리서치 요약 사용', 'Use AI research synthesis'],
  badgeStandard: ['기본 리서치 결과', 'Standard research result'],
  badgeAI: ['AI 리서치 요약', 'AI research synthesis'],
  badgeFailed: ['AI 요약 검증 실패: 기본 결과 표시', 'AI synthesis validation failed: showing standard result'],
};
for (const [key, [ko, en]] of Object.entries(synthRequired)) {
  ok(L.STR_KO[key] === ko, `KO label "${key}" = "${ko}"`, `got "${L.STR_KO[key]}"`);
  ok(L.STR_EN[key] === en, `EN label "${key}" = "${en}"`, `got "${L.STR_EN[key]}"`);
}
ok(typeof L.buildSynthesisHtml === 'function', 'exposes buildSynthesisHtml()');
// deterministic status → standard badge
ok(L.buildResearchHtml({ ok: true, depth: 'basic', issues: ['x'], laws: [], precedents: [], limitations: ['l'], disclaimer: 'd', synthesisStatus: 'deterministic' }, 'ko').indexOf('기본 리서치 결과') !== -1, 'deterministic status → 기본 리서치 결과 badge');
// validation_failed → failed badge + warning + deterministic content
const vf = L.buildResearchHtml({ ok: true, depth: 'pro', issues: ['쟁점x'], laws: [], precedents: [], riskFlags: ['위험'], missingFacts: ['사실'], limitations: ['l'], disclaimer: 'd', synthesisStatus: 'validation_failed', synthesisWarning: 'AI 요약 검증 실패: 기본 결과 표시' }, 'ko');
ok(vf.indexOf('AI 요약 검증 실패: 기본 결과 표시') !== -1, 'validation_failed shows failed badge + warning');
ok(vf.indexOf('쟁점x') !== -1, 'validation_failed still shows deterministic content');
// llm status → AI synthesis view
const synthResult = {
  ok: true, depth: 'pro', depthLabel: '심층 리서치', synthesisStatus: 'llm',
  laws: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }],
  precedents: [{ title: '취소', caseNumber: '2020두1', sourceUrl: 'https://www.law.go.kr/p', strengthLabel: '관련 근거' }],
  sourceGroups: [{ group: 'law', label: '법령', cards: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x' }] }, { group: 'precedent', label: '판례', cards: [{ title: '취소', caseNumber: '2020두1', sourceUrl: 'https://www.law.go.kr/p' }] }],
  synthesisSources: [{ sourceId: 's1', title: '출입국관리법' }, { sourceId: 's2', title: '강제퇴거명령취소' }],
  synthesis: {
    summary: '출처 기반 정리 <img src=x>', issues: ['강제퇴거 쟁점'],
    sourceBackedRules: [{ text: '출입국관리법 관련 근거', sourceIds: ['s1'] }],
    analysis: [{ text: '재량 일탈 여부 검토', sourceIds: ['s2'], confidence: 'medium' }],
    riskFlags: ['재입국 제한'], missingFacts: ['송달일'], nextQuestions: ['질문1'], nextDocuments: ['서류1'],
    limitations: ['참고용'], caution: '최종 판단은 관할기관'
  }
};
const sh = L.buildResearchHtml(synthResult, 'ko');
ok(sh.indexOf('AI 리서치 요약') !== -1, 'llm status → AI 리서치 요약 badge');
ok(sh.indexOf('리서치 메모') !== -1, 'pro synthesis shows memo title');
ok(sh.indexOf('강제퇴거 쟁점') !== -1, 'synthesis issues rendered');
ok(sh.indexOf('출입국관리법 관련 근거') !== -1 && sh.indexOf('[근거: 출입국관리법]') !== -1, 'source-backed rules + basis tags rendered');
ok(sh.indexOf('재량 일탈 여부 검토') !== -1 && sh.indexOf('lss-conf-medium') !== -1, 'analysis + confidence rendered');
ok(sh.indexOf('재입국 제한') !== -1 && sh.indexOf('송달일') !== -1, 'risk flags + missing facts rendered');
ok(sh.indexOf('질문1') !== -1 && sh.indexOf('서류1') !== -1, 'next questions + documents rendered');
ok(sh.indexOf('최종 판단은 관할기관') !== -1, 'synthesis caution rendered');
ok(sh.indexOf('<img src=x') === -1 && sh.indexOf('&lt;img') !== -1, 'synthesis escapes malicious summary');
ok(sh.indexOf('lss-rgroup-title') !== -1, 'synthesis still shows source cards (always)');

section('no dummy / fake-professional strings');
const src = readFileSync(join(ROOT, 'assets/js/legal-source-search.js'), 'utf8');
for (const bad of ['Mr.Visa', 'Mr Visa', 'lorem ipsum', '행정사 검토', '법무법인']) {
  ok(src.toLowerCase().indexOf(bad.toLowerCase()) === -1, `module free of forbidden term "${bad}"`);
}

console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
process.exit(failures ? 1 : 0);
