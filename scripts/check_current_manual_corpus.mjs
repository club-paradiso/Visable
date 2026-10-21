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
  // The 2026.9 editions are the owner-approved current editions (2026-10-16):
  // registry, approval index, catalog and manifest `current` must all agree.
  assert.equal(registry.sources.find(s => s.id === source.id).status, 'active');
  assert.equal(approvals.documents[source.id].approval_state, 'approved');
  assert.ok(approvals.documents[source.id].reviewer && approvals.documents[source.id].reviewed_at);
  assert.equal(source.approval_state, 'approved');
  const current = Object.values(manifest.current).find(s => s.file === source.file);
  assert.ok(current, `${source.id} must be a manifest current edition`);
  assert.equal(current.file_sha256, source.sha256);
  assert.ok(!(manifest.pending_review_editions || []).some(s => s.registry_id_when_promoted === source.id));
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
// Markdown-derived texts (owner-supplied HWP→Markdown, 2026-10-19). Each is
// pinned by digest, and every chunk that may back a citation has a PDF page of
// its own edition whose text it was actually matched against.
const norm = text => text.normalize('NFKC').replace(/[‐‑‒–—―−－─﹣]/g, '-').replace(/[^0-9A-Za-z\-\uac00-\ud7a3\u4e00-\u9fff]+/g, '');
const pdfBySource = Object.fromEntries(catalog.sources.map(s => [s.id, read(s.sections)]));
const derivedCounts = {};
for (const entry of Object.values(manifest.current)) {
  for (const derived of entry.derived_texts || []) {
    const sha = crypto.createHash('sha256').update(fs.readFileSync(derived.file)).digest('hex');
    assert.equal(sha, derived.file_sha256, `${derived.file} must match its pinned sha256`);
    assert.ok(!/approved/.test(derived.verification_status) && /not_human_reviewed/.test(derived.verification_status));
    const map = read(derived.page_map);
    assert.equal(map.source_sha256, sha, `${derived.page_map} must be rebuilt from the pinned Markdown`);
    assert.equal(map.source_id, derived.id);
    assert.equal(map.page_source_file, entry.file);
    const pdf = pdfBySource[derived.page_source_id];
    assert.ok(pdf, `${derived.id} must map onto a catalogued PDF edition`);
    const domain = pdf[0].domain;
    const pageText = Object.fromEntries(pdf.map(row => [row.page, norm(row.text)]));
    let direct = 0;
    map.sections.forEach((row, i) => {
      assert.equal(row.chunk, i + 1);
      assert.equal(row.source_id, derived.id);
      assert.equal(row.page_source_id, derived.page_source_id);
      // Stay and visa texts are never mixed: a chunk carries its own manual's domain.
      assert.equal(row.domain, domain, `${derived.id} chunk ${row.chunk} is not in the ${domain} domain`);
      assert.ok(row.text.trim());
      assert.equal(row.direct_evidence, ['high', 'medium'].includes(row.match.confidence));
      if (!row.direct_evidence) {
        assert.equal(row.page, 0, `${derived.id} chunk ${row.chunk} is not page-mapped, so it must not carry a page`);
        return;
      }
      direct += 1;
      assert.ok(Number.isInteger(row.page) && row.page >= 1 && row.page <= pdf.length, `${derived.id} chunk ${row.chunk} needs a page`);
      assert.equal(row.page, row.pages[0]);
      assert.ok(row.pages.at(-1) - row.pages[0] <= 2 && !row.match.out_of_sequence && !row.match.unresolved_tie);
      assert.ok(row.match.coverage >= 0.7);
      // Independent re-check: most of the chunk's lines and table cells start
      // with text that is literally on its mapped page(s). (Cells are probed
      // one by one because the PDF text layer interleaves a row's cells.)
      const hay = row.pages.map(p => pageText[p]).join('');
      // A table row's label ("열이름: ") is context, not text of that cell.
      const probes = row.text.split(/\n| \| | \/ /).map(t => norm(t.split(': ').at(-1))).filter(t => t.length >= 12).map(t => t.slice(0, 8));
      if (probes.length >= 3) {
        const found = probes.filter(t => hay.includes(t)).length;
        // Wrapped table cells interleave in the PDF text, so tables get a lower bar.
        const bar = row.kind === 'table' ? 0.25 : 0.5;
        assert.ok(found / probes.length >= bar, `${derived.id} chunk ${row.chunk}: only ${found}/${probes.length} line probes on p.${row.pages}`);
      }
    });
    assert.equal(direct, map.summary.direct_evidence_chunks);
    derivedCounts[derived.id] = [map.sections.length, direct];
  }
}
// Pinned so a converter or mapping change shows up as a reviewed diff.
assert.deepEqual(derivedCounts, {
  visa_manual_2026_09_01_md: [1793, 1331],
  stay_manual_2026_09_18_md: [1504, 1134],
});
console.log(`PASS current manual corpus: ${pages.length} pinned pages; code aliases, exact subcodes, AND keywords, domain filter, empty state, immutability; Markdown derived texts ${JSON.stringify(derivedCounts)} [chunks, page-mapped]`);
