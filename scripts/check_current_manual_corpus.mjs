import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import vm from 'node:vm';
const read = path => JSON.parse(fs.readFileSync(path, 'utf8'));
const catalog = read('data/manual-corpus/catalog.json');
const registry = read('data/source_registry.json');
const approvals = read('data/manual_approval_index.json');
const manifest = read('docs/source-manuals/source_manifest.json');
const pages = catalog.sources.flatMap(source => {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(source.file)).digest('hex'), source.sha256);
  const rows = read(source.sections);
  assert.equal(rows.length, source.pages);
  rows.forEach((row, i) => {
    assert.equal(row.source_id, source.id);
    assert.equal(row.source_file, source.file);
    assert.equal(row.page, i + 1);
    assert.equal(row.domain, source.domain);
    assert.ok(row.text.trim() && !row.text.includes('\uFFFD'));
    assert.ok(row.heading && row.heading.length <= 140);
  });
  assert.equal(source.characters, rows.reduce((n, row) => n + [...row.text].length, 0));
  assert.equal(registry.sources.find(s => s.id === source.id).status, 'needs_manual_review');
  assert.equal(approvals.documents[source.id].approval_state, 'needs_review');
  assert.equal(approvals.documents[source.id].reviewer, '');
  assert.equal(manifest.pending_review_editions.find(s => s.registry_id_when_promoted === source.id).file_sha256, source.sha256);
  return rows;
});
assert.equal(pages.length, 1329);
assert.deepEqual(catalog.sources.map(s => s.pages), [519, 810]);
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('assets/js/manual-corpus-search.js', 'utf8'), context);
const api = context.VisableManualSearch;
const before = JSON.stringify(pages);
const index = api.prepare(catalog.sources, pages);
const exact = api.search(index, 'E-7-4');
assert.ok(exact.length > 0);
assert.ok(exact.every(hit => hit.page.status_codes_detected.includes('E-7-4')));
assert.equal(api.search(index, 'ｅ７４').length, exact.length);
assert.equal(api.search(index, 'E–7–4').length, exact.length);
const stay = api.search(index, 'F-6 연장', {domain:'stay'});
assert.ok(stay.length > 0);
assert.ok(stay.every(hit => hit.source.domain === 'stay' && hit.page.status_codes_detected.some(code => code === 'F-6' || code.startsWith('F-6-')) && hit.page.text.includes('연장')));
assert.ok(stay.some(hit => hit.page.page === 498), 'Parent searches must retrieve extension pages naming F-6-1');
assert.equal(api.search(index, '').length, 0);
assert.equal(api.search(index, 'ZZZZnonexistentmanualterm').length, 0);
assert.ok(api.excerpt(stay[0].page.text, 'F-6 연장', index).length <= 222);
assert.equal(JSON.stringify(pages), before, 'Search must not rewrite official originals');
const synthetic = api.prepare([{id:'a',domain:'stay',date:'2026-09-18'}], [
  {source_id:'a',page:3,heading:'G-1-5',text:'G-1-5 체류기간 연장',status_codes_detected:['G-1-5']},
  {source_id:'a',page:4,heading:'G-1',text:'G-1 체류기간 연장',status_codes_detected:['G-1']},
  {source_id:'a',page:5,heading:'E-7-4R',text:'E-7-4R 체류기간 연장',status_codes_detected:['E-7-4R']}
]);
assert.equal(api.search(synthetic, 'G-1-5')[0].page.page, 3);
assert.equal(api.search(synthetic, 'G-1-5').length, 1);
assert.equal(api.search(synthetic, 'G-1').length, 2, 'A parent search includes its subtypes');
assert.equal(api.search(synthetic, 'E-7-4').length, 0, 'E-7-4 must not match E-7-4R');
console.log(`PASS current manual corpus: ${pages.length} pinned pages; code aliases, exact subcodes, AND keywords, domain filter, empty state, immutability`);
