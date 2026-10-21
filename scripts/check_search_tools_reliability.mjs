import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { JSDOM } from 'jsdom';
import { loadCivic } from './build_landing_shell.mjs';
const require = createRequire(import.meta.url);
const router = require('../assets/js/search-router.js');
const civic = loadCivic();
for (const query of [
  'F-6 연장', 'F-6 연장 서류가 뭐예요?', '외국인등록', '주소 변경 신고',
  'D-2에서 D-10 변경', 'D-2 체류기간 연장 수수료와 서류',
  'E-7 workplace change documents', 'How do I extend my F-6 visa?',
  '여권을 재발급했는데 변경 신고 서류가 뭐예요?',
  'F-6 extension documents before visiting the office',
]) assert.equal(router.assessComplexity(query).complex, false, query);
for (const query of [
  'F-6 연장 심사 중인데 출국했다가 돌아와도 되나요?',
  'D-2 만료 전에 D-10으로 자격 변경하면서 아르바이트도 계속할 수 있나요?',
  'F-2와 F-6 중 어느 비자가 더 유리한지 비교해 주세요',
  'My visa expires next week but I need to travel and return to Korea.',
  'Can I change my status while I change my employer?',
]) assert.equal(router.assessComplexity(query).complex, true, query);
for (let i = 0; i < 100; i++) {
  const ids = civic.selectExamples(Math.random, null);
  assert.equal(new Set(ids).size, 4);
  assert(ids.every(id => civic.examplePool[id]?.length === 2));
  const previous = civic.selectExamples(() => 0.5, null);
  const next = civic.selectExamples(() => 0.5, previous);
  assert.notEqual(previous.slice().sort().join(','), next.slice().sort().join(','));
}
// Mount the actual home controller, then use its controls as a user would.
const dom = new JSDOM('<!doctype html><html lang="ko"><body class="landing"><header id="hero"></header><input id="q"><main id="mainContent"></main></body></html>', { url: 'https://visable.test/', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
w.matchMedia = () => ({ matches: false, addEventListener() {} });
w.HTMLElement.prototype.scrollIntoView = function () {};
w.fetch = async () => ({ ok: true, json: async () => ({ sources: [], entries: [] }) });
w.eval(readFileSync(new URL('../assets/js/civic-search.js', import.meta.url), 'utf8'));
w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
const doc = w.document;
assert.equal(doc.querySelectorAll('.cs-service').length, 15);
assert(doc.querySelector('.cs-directory').open);
assert(doc.querySelector('.cs-directory').compareDocumentPosition(doc.querySelector('.cs-footer')) & w.Node.DOCUMENT_POSITION_FOLLOWING);
const filter = doc.querySelector('[data-cs-tool-filter]');
filter.value = '병원'; filter.dispatchEvent(new w.Event('input'));
assert.deepEqual([...doc.querySelectorAll('.cs-service')].filter(x => !x.hidden).map(x => x.textContent.trim()), ['법무부지정 병원법무부 지정 의료기관과 위치를 확인해요.']);
filter.value = '없는 도구'; filter.dispatchEvent(new w.Event('input'));
assert.equal(doc.querySelector('.cs-tool-empty').hidden, false);
filter.value = ''; filter.dispatchEvent(new w.Event('input'));
doc.querySelector('[data-cs-tool-group="stay"]').click();
assert([...doc.querySelectorAll('.cs-service')].filter(x => !x.hidden).every(x => x.dataset.serviceGroup === 'stay'));
assert.equal(doc.querySelector('[data-cs-tool-group="stay"]').getAttribute('aria-pressed'), 'true');
doc.querySelector('[data-cs-tool-group="all"]').click();
assert.equal([...doc.querySelectorAll('.cs-service')].filter(x => !x.hidden).length, 15);
assert.equal(new Set([...doc.querySelectorAll('.cs-examples button')].map(x => x.dataset.csQuery)).size, 4);
dom.window.close();

// Regression: response headers arrive, but its body never completes. The
// request deadline must still abort it rather than leave the spinner forever.
const src = readFileSync(new URL('./enforcement-ui.mjs', import.meta.url), 'utf8');
const start = src.indexOf('async function request('), end = src.indexOf('\nfunction detectLocale', start);
const request = new Function('fetch', 'AbortController', 'setTimeout', 'clearTimeout', 'apiBase', src.slice(start, end) + '; return request;')(
  async (_url, options) => ({ ok: true, headers: { get: () => 'application/json' }, json: () => new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('timeout', 'AbortError')))) }),
  AbortController, setTimeout, clearTimeout, '',
);
await assert.rejects(request('/api/enforcement/analyze', {}, { timeoutMs: 15 }), /분석 시간이 길어져/);
const { analyzeBaselineCase } = require('../lib/enforcement-grounded-ai.js');
assert.throws(() => analyzeBaselineCase(null));
const baseline = analyzeBaselineCase({ schemaVersion: '1', statusOfStay: 'D-2', violationCode: 'STATUS_OUTSIDE_ACTIVITY_ART20', durationDays: 30, authorizationObtained: false, assessmentDate: '2026-10-21', priorViolations: 0 });
assert.equal(baseline.legalBaseline.status, 'AVAILABLE');
assert.equal(baseline.lawGrounding.status, 'UNAVAILABLE');
console.log('Search/tools reliability passed: simple vs complex questions, refresh selection, mounted catalogue filters, empty/reset states, body timeout and baseline fallback.');
