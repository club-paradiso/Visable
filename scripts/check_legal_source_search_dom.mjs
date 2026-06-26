#!/usr/bin/env node
/**
 * check_legal_source_search_dom.mjs — jsdom DOM smoke test for the Waymaker
 * Legal source search module (assets/js/legal-source-search.js).
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
function fakeFetch(url) {
  lastUrl = String(url);
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
  ok(root.textContent.indexOf('법령·판례 근거 검색') !== -1, 'panel shows the KO title');
  ok(root.querySelectorAll('[data-lss-tab]').length === 2, 'two tabs rendered');
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

  console.log(`\n${failures ? 'FAIL' : 'OK'} — ${checks - failures}/${checks} checks passed`);
  process.exit(failures ? 1 : 0);
}

run().catch((e) => { console.error('DOM test crashed:', e); process.exit(1); });
