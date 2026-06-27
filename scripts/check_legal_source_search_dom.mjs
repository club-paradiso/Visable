#!/usr/bin/env node
/**
 * check_legal_source_search_dom.mjs — jsdom DOM smoke test for the Waymaker
 * Legal Research module (assets/js/legal-source-search.js).
 *
 * Drives the REAL module against a stubbed fetch and asserts the load-bearing
 * UI guarantees:
 *   - the panel mounts into #legalSourceSearchRoot (title, tabs, chips, disclaimer);
 *   - the toggle expands the collapsed body;
 *   - a law search renders result cards from the backend envelope;
 *   - a MALICIOUS upstream title/snippet is escaped in the LIVE DOM (no injected
 *     <img>/<script> element — defends against precedent/law HTML injection);
 *   - the missing-API-key envelope renders the friendly config state;
 *   - a rejected fetch renders the error state;
 *   - switching to the Precedents tab queries the precedents endpoint.
 *
 * Gracefully SKIPS (exit 0) if jsdom is not installed, so CI without jsdom still
 * passes. Run: node scripts/check_legal_source_search_dom.mjs
 */
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);

let JSDOM;
try { ({ JSDOM } = require('jsdom')); }
catch (e) {
  console.log('• jsdom not installed — skipping DOM smoke test (run `npm install`). SKIP.');
  process.exit(0);
}

let failures = 0, checks = 0;
function ok(cond, msg) { checks++; if (cond) console.log('  PASS  ' + msg); else { failures++; console.error('  FAIL  ' + msg); } }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- jsdom environment ------------------------------------------------------
const dom = new JSDOM(
  '<!doctype html><html><head></head><body>'
  + '<section id="legalSourceSearchRoot"></section></body></html>',
  { url: 'https://example.com/ai.html' }
);
global.window = dom.window;
global.document = dom.window.document;
global.location = dom.window.location;
global.currentLanguage = 'ko';

// Controllable fetch stub: each call resolves `nextResponse` (or rejects when
// `nextReject` is set) and records the requested URL.
let nextResponse = { ok: true, results: [] };
let nextReject = false;
let lastUrl = '';
let lastBody = null;
function fakeFetch(url, opts) {
  lastUrl = String(url);
  lastBody = (opts && opts.body) ? (() => { try { return JSON.parse(opts.body); } catch (e) { return null; } })() : null;
  if (nextReject) return Promise.reject(new Error('network'));
  const body = nextResponse;
  return Promise.resolve({ json: () => Promise.resolve(body) });
}
global.fetch = fakeFetch;
dom.window.fetch = fakeFetch;

require('../assets/js/legal-source-search.js');
const L = globalThis.ParadisoLegalSearch;
const root = document.getElementById('legalSourceSearchRoot');

async function run() {
  // jsdom's readyState is 'loading' when the module's IIFE runs (DOMContentLoaded
  // fires on a later tick), so mount explicitly for a deterministic test.
  L.mount();
  ok(!!root && root.querySelector('.lss-panel'), 'panel mounted into #legalSourceSearchRoot');
  ok(root.textContent.indexOf('Waymaker 리걸 리서치') !== -1, 'panel shows the KO Legal Research product title');
  ok(root.querySelectorAll('[data-lss-tab]').length === 3, 'three tabs rendered (Laws / Precedents / Research)');
  ok(root.querySelectorAll('[data-lss-chip]').length === 10, 'ten quick chips rendered');
  ok(!!root.querySelector('.lss-disclaimer'), 'disclaimer rendered');

  // toggle expands the collapsed body
  const body = root.querySelector('#lssBody');
  const toggle = root.querySelector('[data-lss-toggle]');
  ok(body.hasAttribute('hidden'), 'body collapsed by default');
  toggle.dispatchEvent(new dom.window.Event('click'));
  ok(!body.hasAttribute('hidden'), 'toggle expands the body');

  // law search renders cards
  nextResponse = {
    ok: true, kind: 'laws',
    results: [{ title: '출입국관리법', type: '법률', snippet: '외국인의 입국과 체류', sourceUrl: 'https://www.law.go.kr/법령/출입국관리법', promulgationDate: '20240101' }]
  };
  L.doSearch('출입국관리법');
  await sleep(25);
  ok(lastUrl.indexOf('/api/legal/laws/search?q=') !== -1, 'law search hit the laws endpoint');
  ok(root.querySelector('.lss-card') && root.querySelector('.lss-card-title').textContent.indexOf('출입국관리법') !== -1, 'law result card rendered');
  ok(!!root.querySelector('a.lss-src'), 'official-source link anchor rendered');

  // MALICIOUS upstream content must be escaped in the live DOM
  nextResponse = {
    ok: true, kind: 'laws',
    results: [{ title: '<img src=x onerror="window.__pwned=1">', snippet: '<script>window.__pwned=1</script>', sourceUrl: 'https://www.law.go.kr/법령/x' }]
  };
  L.doSearch('xss');
  await sleep(25);
  ok(root.querySelectorAll('img').length === 0, 'no <img> element injected from malicious title');
  ok(root.querySelectorAll('script').length === 0, 'no <script> element injected from malicious snippet');
  ok(!dom.window.__pwned, 'no injected handler executed');
  ok(root.querySelector('.lss-card-title').textContent.indexOf('<img') !== -1, 'malicious title rendered as inert text');

  // missing-key envelope → config state
  nextResponse = { ok: false, error: 'LAW_API_OC is not configured', reason: 'not_configured', results: [] };
  L.doSearch('국적법');
  await sleep(25);
  ok(root.querySelector('[data-lss-out]').textContent.indexOf('API 설정이 필요합니다') !== -1, 'missing-key state rendered');

  // rejected fetch → error state
  nextReject = true;
  L.doSearch('난민법');
  await sleep(25);
  nextReject = false;
  ok(root.querySelector('[data-lss-out]').textContent.indexOf('검색에 실패했습니다') !== -1, 'network error state rendered');

  // empty results → empty state
  nextResponse = { ok: true, kind: 'laws', results: [] };
  L.doSearch('존재하지않는zzz');
  await sleep(25);
  ok(root.querySelector('[data-lss-out]').textContent.indexOf('검색 결과가 없습니다') !== -1, 'empty state rendered');

  // switching to Precedents tab queries the precedents endpoint
  nextResponse = { ok: true, kind: 'precedents', results: [{ title: '판례', court: '대법원', caseNumber: '2020두1', sourceUrl: 'https://www.law.go.kr/precInfoP.do?precSeq=1' }] };
  const precTab = root.querySelector('[data-lss-tab="precedents"]');
  precTab.dispatchEvent(new dom.window.Event('click'));
  await sleep(25);
  ok(lastUrl.indexOf('/api/legal/precedents/search?q=') !== -1, 'precedent tab + prior query hit the precedents endpoint');
  ok(root.querySelector('.lss-prec-flag') && root.querySelector('[data-lss-out]').textContent.indexOf('원문 확인 필요') !== -1, 'precedent card shows "원문 확인 필요"');

  // --- Research (depth) tab ---
  const researchTab = root.querySelector('[data-lss-tab="research"]');
  researchTab.dispatchEvent(new dom.window.Event('click'));
  ok(root.querySelector('.lss-research-area') && !root.querySelector('.lss-research-area').hidden, 'research tab reveals the research area');
  ok(root.querySelector('.lss-search-area').hidden, 'term-search area hidden on research tab');
  ok(root.querySelectorAll('[data-lss-depth]').length === 3, 'depth selector has 3 options (fast/basic/pro)');
  ok(root.querySelector('[data-lss-rinput]'), 'research question input rendered');

  // run a Pro research; backend returns the structured envelope
  nextResponse = {
    ok: true, depth: 'pro', depthLabel: '심층 리서치', depthAutoSelected: true, mode: 'memo', locale: 'ko',
    headings: ['리서치 메모', '1. 쟁점', '2. 사실관계에서 중요한 부분', '3. 관련 법령', '4. 관련 판례 또는 판례 검색 결과', '5. 출입국 실무상 확인할 자료', '6. 적용 가능성', '7. 위험 신호', '8. 부족한 사실관계', '9. 다음 확인사항', '10. 출처', '주의'],
    issues: ['강제퇴거명령과 출국명령의 요건·효과 구분'],
    lawSearchTerms: ['출입국관리법 강제퇴거'], precedentSearchTerms: ['강제퇴거명령 취소'],
    laws: [{ title: '출입국관리법', type: '법률', snippet: '<b>x</b>', sourceUrl: 'https://www.law.go.kr/법령/x', strength: 'direct', strengthLabel: '직접 근거' }],
    precedents: [{ title: '취소', caseNumber: '2020두1', summary: 'y', sourceUrl: 'https://www.law.go.kr/precInfoP.do?precSeq=1', strength: 'related', strengthLabel: '관련 근거' }],
    riskFlags: ['입국금지·재입국 제한 가능성'], missingFacts: ['처분서 송달일'], nextChecks: ['1345에 사실관계 확인'],
    limitations: ['이 정리는 검색·구조화 결과이며 법적 결론이 아닙니다.'],
    sourceGroups: [{ group: 'law', label: '법령', cards: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }] }, { group: 'precedent', label: '판례', cards: [{ title: '취소', caseNumber: '2020두1', sourceUrl: 'https://www.law.go.kr/precInfoP.do?precSeq=1' }] }],
    disclaimer: '법령·판례 리서치는 공식 원문 확인을 돕기 위한 정리이며, 변호사·행정사의 법률 자문이나 최종 판단을 대체하지 않습니다.'
  };
  L.doResearch('강제퇴거명령과 출국명령을 비교하고 다툴 쟁점을 정리해줘');
  await sleep(25);
  ok(lastUrl.indexOf('/api/legal/research') !== -1, 'research run hit the /api/legal/research endpoint');
  const outText = root.querySelector('[data-lss-out]').textContent;
  ok(root.querySelector('.lss-research'), 'structured research result rendered');
  ok(outText.indexOf('심층 리서치') !== -1, 'depth label shown');
  ok(outText.indexOf('강제퇴거명령과 출국명령의 요건') !== -1, 'issues rendered');
  ok(outText.indexOf('입국금지') !== -1, 'risk flags rendered');
  ok(outText.indexOf('처분서 송달일') !== -1, 'missing facts rendered');
  ok(root.querySelector('.lss-rgroup-title'), 'pro source groups rendered');
  ok(root.querySelectorAll('img').length === 0, 'research law snippet HTML rendered inert (no <img>)');
  ok(outText.indexOf('변호사·행정사의 법률 자문이나 최종 판단을 대체하지 않습니다') !== -1, 'research disclaimer shown');

  // --- AI synthesis layer ---
  ok(root.querySelector('[data-lss-synth-toggle]'), 'AI synthesis toggle rendered');
  ok(root.querySelector('[data-lss-synth-toggle]').checked, 'synthesis toggle on by default');
  ok(!root.querySelector('[data-lss-synth-wrap]').hidden, 'synthesis toggle visible for basic/pro depth');

  // source-grounded LLM synthesis result
  nextResponse = {
    ok: true, depth: 'pro', depthLabel: '심층 리서치', synthesisStatus: 'llm', providerConfigured: true, mode: 'memo', locale: 'ko',
    laws: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }],
    precedents: [{ title: '취소', caseNumber: '2020두1', sourceUrl: 'https://www.law.go.kr/p', strengthLabel: '관련 근거' }],
    sourceGroups: [{ group: 'law', label: '법령', cards: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x' }] }],
    synthesisSources: [{ sourceId: 's1', title: '출입국관리법' }],
    synthesis: { summary: '출처 기반 정리 <img src=x>', issues: ['강제퇴거 쟁점'], sourceBackedRules: [{ text: '출입국관리법 관련 근거', sourceIds: ['s1'] }], analysis: [{ text: '재량 검토', sourceIds: ['s1'], confidence: 'medium' }], riskFlags: ['재입국 제한'], missingFacts: ['송달일'], nextQuestions: ['질문1'], nextDocuments: ['서류1'], limitations: ['참고용'], caution: '최종 판단은 관할기관' }
  };
  L.doResearch('강제퇴거 쟁점 정리해줘');
  await sleep(25);
  const sout = root.querySelector('[data-lss-out]').textContent;
  ok(sout.indexOf('AI 리서치 요약') !== -1, 'AI synthesis badge shown');
  ok(root.querySelector('.lss-synth'), 'synthesis view rendered');
  ok(sout.indexOf('강제퇴거 쟁점') !== -1, 'synthesis issues rendered');
  ok(sout.indexOf('[근거: 출입국관리법]') !== -1, 'source-basis tags rendered');
  ok(root.querySelectorAll('img').length === 0, 'synthesis escapes malicious summary (no <img>)');
  ok(root.querySelector('.lss-rgroup-title') || root.querySelector('.lss-card'), 'source cards still shown under synthesis');

  // validation_failed → failed badge + warning + deterministic content
  nextResponse = {
    ok: true, depth: 'pro', depthLabel: '심층 리서치', synthesisStatus: 'validation_failed', synthesisWarning: 'AI 요약 검증 실패: 기본 결과 표시', providerConfigured: true,
    issues: ['쟁점det'], laws: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x', strengthLabel: '직접 근거' }], precedents: [], riskFlags: ['위험'], missingFacts: ['사실'], nextChecks: ['확인'], limitations: ['l'], disclaimer: 'd', sourceGroups: [{ group: 'law', label: '법령', cards: [{ title: '출입국관리법', sourceUrl: 'https://www.law.go.kr/법령/x' }] }]
  };
  L.doResearch('강제퇴거 쟁점 다시 정리');
  await sleep(25);
  const vout = root.querySelector('[data-lss-out]').textContent;
  ok(vout.indexOf('AI 요약 검증 실패: 기본 결과 표시') !== -1, 'validation-failed badge + warning shown');
  ok(vout.indexOf('쟁점det') !== -1, 'deterministic content shown on validation failure');

  // provider not configured → toggle disabled + standard badge
  nextResponse = { ok: true, depth: 'basic', depthLabel: '기본 리서치', synthesisStatus: 'deterministic', providerConfigured: false, issues: ['x'], laws: [], precedents: [], limitations: ['l'], disclaimer: 'd' };
  L.doResearch('간단히 확인할 것 하나');
  await sleep(25);
  ok(root.querySelector('[data-lss-synth-toggle]').disabled, 'toggle disabled when provider not configured');
  ok(root.querySelector('[data-lss-out]').textContent.indexOf('기본 리서치 결과') !== -1, 'standard badge when provider not configured');

  // Fast depth hides the synthesis toggle
  const fastBtn = root.querySelector('[data-lss-depth="fast"]');
  fastBtn.dispatchEvent(new dom.window.Event('click'));
  ok(root.querySelector('[data-lss-synth-wrap]').hidden, 'synthesis toggle hidden for Fast depth');

  // --- professional UX redesign (positioning / examples / options) ---
  ok(root.querySelector('.lss-positioning') && root.querySelector('.lss-positioning').textContent.indexOf('리서치 도구') !== -1, 'research area shows positioning text');
  const exampleBtns = root.querySelectorAll('[data-lss-example]');
  ok(exampleBtns.length >= 4, 'example question chips rendered');
  ok(!!root.querySelector('[data-lss-opt-prec]') && !!root.querySelector('[data-lss-opt-orig]'), 'precedents + show-original options rendered');
  ok(root.querySelector('[data-lss-run]').textContent.indexOf('분석 시작하기') !== -1, 'CTA labelled 분석 시작하기');

  // clicking an example chip prefills the question textarea
  exampleBtns[0].dispatchEvent(new dom.window.Event('click'));
  ok(root.querySelector('[data-lss-rinput]').value.length > 0, 'example chip prefills the question input');

  // unchecking "search precedents too" is reflected in the request payload
  const precOpt = root.querySelector('[data-lss-opt-prec]');
  precOpt.checked = false;
  precOpt.dispatchEvent(new dom.window.Event('change'));
  nextResponse = { ok: true, depth: 'basic', depthLabel: '기본 리서치', synthesisStatus: 'deterministic', providerConfigured: false, issues: ['x'], laws: [], precedents: [], limitations: ['l'], disclaimer: 'd' };
  L.doResearch('판례 제외하고 확인할 사항');
  await sleep(25);
  ok(lastBody && lastBody.includePrecedents === false, 'includePrecedents:false sent when option unchecked');

  // --- Waymaker → Legal Research handoff event (§6) ---
  nextResponse = { ok: true, depth: 'pro', depthLabel: '심층 리서치', synthesisStatus: 'deterministic', providerConfigured: false, issues: ['핸드오프 쟁점'], laws: [], precedents: [], riskFlags: [], missingFacts: [], nextChecks: [], limitations: ['l'], disclaimer: 'd' };
  lastUrl = '';
  dom.window.dispatchEvent(new dom.window.CustomEvent('paradiso:legal-research', { detail: { question: '변경허가에서 다툴 쟁점', visaCode: 'F-6', depth: 'pro' } }));
  await sleep(25);
  ok(lastUrl.indexOf('/api/legal/research') !== -1, 'handoff event runs a research request');
  ok(lastBody && typeof lastBody.question === 'string' && lastBody.question.indexOf('F-6') !== -1, 'handoff prefills the visa code into the question');
  ok(root.querySelector('[data-lss-rinput]').value.indexOf('변경허가에서 다툴 쟁점') !== -1, 'handoff prefills the question text');

  console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
  process.exit(failures ? 1 : 0);
}

run().catch((e) => { console.error('DOM test crashed:', e); process.exit(1); });
