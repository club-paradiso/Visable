/* check_address_helper.mjs — Address Helper (JUSOYUNO folded into Visable) wiring.
 *
 * Offline, jsdom-only. Verifies:
 *  1. the page carries every element id the ported controller queries, and its
 *     three local assets + the Tesseract CDN script are wired in order;
 *  2. the civic directory registers the tool exactly once (tile + keys in the
 *     ko/en bootstrap copy and in every locale pack);
 *  3. the controller actually runs: language switching re-renders copy in all
 *     six shipped languages, a NOT_CONFIGURED answer opens the honest manual
 *     fallback, a stubbed official answer renders candidates, and choosing one
 *     fills the Korean/English card and the combined copy text.
 * The live JUSO API is never called: fetch is stubbed, and no key is read.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const read = (rel) => readFileSync(new URL('../' + rel, import.meta.url), 'utf8');

/* ---- 1. static wiring ---------------------------------------------------- */
const html = read('address-helper.html');
const appSrc = read('assets/js/address-helper.js');
for (const asset of ['assets/js/address-ocr-core.js', 'assets/js/address-helper.js', 'assets/css/address-helper.css',
  'https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js']) {
  assert.ok(html.includes(asset), 'address-helper.html wires ' + asset);
}
const queriedIds = [...new Set([...appSrc.matchAll(/\$\("([A-Za-z]+)"\)/g)].map((m) => m[1]))];
assert.ok(queriedIds.length >= 20, 'controller queries a real id set (' + queriedIds.length + ')');
for (const id of queriedIds) {
  assert.ok(new RegExp('id="' + id + '"').test(html), 'page carries #' + id + ' queried by the controller');
}
assert.ok(!/\/api\/handwriting|cloudRun|cloudConsent|cloudPanel|handwritingEnabled|AZURE_VISION/.test(html + appSrc),
  'the Azure handwriting block stays out of the port');

/* ---- 2. civic registration ----------------------------------------------- */
const civic = read('assets/js/civic-search.js');
assert.equal((civic.match(/address-helper\.html/g) || []).length, 1, 'directory links the tool exactly once');
assert.ok(civic.includes("tile('address','addressSub','house','href=\"address-helper.html\"','prepare')"), 'directory tile registered in prepare');
for (const loc of ['ko', 'en']) {
  const pack = JSON.parse(read('data/i18n/' + loc + '.json')).civic;
  assert.ok(pack.address && pack.addressSub, loc + ' pack carries address keys');
  assert.ok(civic.includes('address: "' + pack.address + '"'), loc + ' bootstrap copy matches pack title');
  assert.ok(civic.includes("addressSub: '" + pack.addressSub + "'"), loc + ' bootstrap copy matches pack sub');
}
const manifest = JSON.parse(read('data/i18n/manifest.json'));
for (const loc of manifest.supportedLocales) {
  const pack = JSON.parse(read('data/i18n/' + loc + '.json')).civic;
  assert.ok(typeof pack.address === 'string' && pack.address.trim(), loc + ' pack carries address');
  assert.ok(typeof pack.addressSub === 'string' && pack.addressSub.trim(), loc + ' pack carries addressSub');
  // Overflow precheck (see web_copy_overflow_precheck): a tile title/sub is a
  // single card line group at 390px; no unbroken token may be viewport-wide.
  for (const value of [pack.address, pack.addressSub]) {
    // CJK characters may break between any two glyphs, so only non-CJK runs
    // can form an unbreakable token wide enough to overflow a 390px card.
    for (const token of value.split(/[\s\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]+/)) {
      assert.ok([...token].length <= 24, loc + ' civic string has an unbroken token too long for 390px: ' + token);
    }
  }
}

/* ---- 3. controller behaviour in jsdom ------------------------------------- */
const dom = new JSDOM(html, { url: 'https://visable.test/address-helper.html', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;
w.matchMedia = () => ({ matches: false, addEventListener() {} });
w.HTMLElement.prototype.scrollIntoView = function () {};
let clipboard = '';
Object.defineProperty(w.navigator, 'clipboard', { value: { writeText: async (s) => { clipboard = s; } }, configurable: true });
let fetchMode = 'not-configured';
w.fetch = async (url, options) => {
  assert.ok(String(url).startsWith('/api/address/'), 'only the address API is called, got ' + url);
  if (fetchMode === 'not-configured') return { ok: false, status: 503, json: async () => ({ code: 'NOT_CONFIGURED' }) };
  const body = JSON.parse(options.body);
  assert.equal(body.keyword, '제주시 중앙로 1');
  return { ok: true, status: 200, json: async () => ({ code: 'OK', totalCount: 1, results: [{ roadAddr: '제주특별자치도 제주시 중앙로 1', roadAddrPart2: '', engAddr: '1, Jungang-ro, Jeju-si, Jeju-do, Republic of Korea', jibunAddr: '제주특별자치도 제주시 이도일동 1', zipNo: '63264', buildingName: '' }] }) };
};
w.eval(read('assets/js/address-ocr-core.js'));
w.eval(appSrc);
const doc = w.document;
const tick = () => new Promise((r) => setTimeout(r, 10));

// Default language is Korean on Visable; all six shipped languages re-render.
assert.equal(doc.documentElement.lang, 'ko');
const labels = {};
for (const lang of ['ko', 'en', 'zh', 'vi', 'id', 'hi']) {
  const sel = doc.querySelector('#language');
  sel.value = lang;
  sel.dispatchEvent(new w.Event('change'));
  labels[lang] = doc.querySelector('#search').textContent.trim();
  assert.ok(labels[lang] && labels[lang] !== 'searchBtn', lang + ' renders a real search label');
  assert.equal(doc.documentElement.lang, lang === 'zh' ? 'zh' : lang);
}
assert.equal(new Set(Object.values(labels)).size, 6, 'six languages render six distinct search labels');
const sel = doc.querySelector('#language');
sel.value = 'ko'; sel.dispatchEvent(new w.Event('change'));

// NOT_CONFIGURED: the honest manual fallback opens, nothing is fabricated.
doc.querySelector('#keyword').value = '제주시 중앙로 1';
doc.querySelector('#search').click();
await tick(); await tick();
assert.equal(doc.querySelector('#manualHelp').hidden, false, 'manual fallback shows when the API is not configured');
assert.equal(doc.querySelector('#candidates').hidden, true, 'no fabricated candidates');

// Configured: candidates render, selection fills the card, copy composes.
fetchMode = 'ok';
doc.querySelector('#search').click();
await tick(); await tick();
const candidate = doc.querySelector('#candidates .candidate');
assert.ok(candidate, 'candidate renders from the official-shaped response');
assert.ok(candidate.textContent.includes('제주시 중앙로 1'));
candidate.click();
assert.equal(doc.querySelector('#selected').hidden, false);
assert.equal(doc.querySelector('#krResult').textContent, '제주특별자치도 제주시 중앙로 1');
assert.ok(doc.querySelector('#enResult').textContent.includes('Jungang-ro'));
doc.querySelector('#unit').value = '101동 202호';
doc.querySelector('#copyComplete').click();
await tick();
assert.equal(clipboard, '제주특별자치도 제주시 중앙로 1 101동 202호', 'combined copy = base address + self-entered unit');
dom.window.close();

console.log('Address helper passed: static wiring, civic registration in 14 packs, six-language rendering, NOT_CONFIGURED fallback, candidate → card → copy flow.');
