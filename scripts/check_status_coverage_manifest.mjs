/*
 * check_status_coverage_manifest.mjs
 * ----------------------------------------------------------------------------
 * Machine-level coverage QA over EVERY entry of data/status-coverage-202609.json
 * (built from the September 2026 manuals by scripts/build_status_coverage_manifest.py).
 *
 * For each manual chapter / status / substatus / scenario / special regime it asserts:
 *   - exists in the manifest with a source edition
 *   - the exact code maps to its parent correctly
 *   - the source page / section exists in the PDF corpus (and the anchor text is on it)
 *   - every procedure has an explicit state from the enum
 *   - document coverage has an explicit state
 *   - no unsupported procedure (NOT_APPLICABLE / GENERALLY_NOT_PERMITTED / UNVERIFIED /
 *     SOURCE_ONLY) is presented as a normal action by the guidance bundle
 *   - no unverified content becomes definitive (UNVERIFIED codes carry no SUPPORTED guidance)
 *   - the source-only fallback resolves (a page is recorded)
 * A missing manual chapter is a blocking failure. Prints the coverage report counts.
 *
 *   node scripts/check_status_coverage_manifest.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(ROOT, 'data/status-coverage-202609.json'), 'utf8'));
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
const rules = JSON.parse(readFileSync(join(ROOT, 'data/guidance-rules-202609.json'), 'utf8'));
const corpora = {
  stay_manual_2026_09_18: JSON.parse(readFileSync(join(ROOT, 'data/manual-corpus/stay_manual_2026_09_18_pdf.json'), 'utf8')),
  visa_manual_2026_09_01: JSON.parse(readFileSync(join(ROOT, 'data/manual-corpus/visa_manual_2026_09_01_pdf.json'), 'utf8')),
};
const pageText = {};
for (const [id, pages] of Object.entries(corpora)) { pageText[id] = new Map(pages.map((p) => [p.page, norm(p.text)])); }

function norm(s) {
  return String(s || '').normalize('NFKC').replace(/[․·‧ㆍ∙‥]/g, '·').replace(/[‐‑‒–—−－]/g, '-')
    .replace(/[①-⑳❍○◦▪‣□■•▣※*㉮-㉻➀-➉ⅰ-ⅹ]/g, '').replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/[｢｣]/g, (c) => (c === '｢' ? '「' : '」'))
    .replace(/（/g, '(').replace(/）/g, ')').replace(/[∼～]/g, '~').replace(/\s+/g, '').toLowerCase();
}
const DUP = /(.{2,25}?)\1/g;
function dedup(t) { let prev; do { prev = t; t = t.replace(DUP, '$1'); } while (prev !== t); return t; }
function pageHas(manual, page, anchor) {
  const raw = norm(anchor); const a = dedup(raw); const la = loose(raw);
  const t = pageText[manual].get(page) || ''; const n = pageText[manual].get(page + 1) || '';
  return t.includes(raw) || t.includes(a) || dedup(t).includes(a) || (t + n).includes(a) || dedup(t + n).includes(a) || loose(t).includes(la) || loose(t + n).includes(la);
}
const FRAGS = ['목차', '체류자격외활동', '근무처의변경·추가', '체류자격변경허가', '체류기간연장허가', '체류자격변경', '체류기간연장', '재입국허가', '외국인등록', '체류자격부여', '활동범위', '해당자', '제출서류', '체류기간', '연장허가', '변경허가', '체류자격', '부여', '재입국', '자격외활동', '근무처', '변경·추가', '상한'].sort((a, b) => b.length - a.length);
function loose(t) { for (const f of FRAGS) t = t.split(f).join(''); return dedup(t.replace(/-\d{1,3}-/g, '')); }

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

const COVERAGE = new Set(manifest.coverage_states);
const PROC = new Set(manifest.procedure_states);
const DOCSTATES = new Set(['FULLY_STRUCTURED', 'PARTIALLY_STRUCTURED', 'SOURCE_ONLY', 'REQUIRES_CLARIFICATION', 'UNVERIFIED', 'NOT_APPLICABLE', 'INHERITS_PARENT']);
const PROCEDURES = rules.procedures.map((p) => p.id);
const records = manifest.records;
const byCode = new Map(records.map((r) => [r.code, r]));

/* ---------------------------------------------------------- chapters ---- */
const EXPECTED_STAY = ['A-1', 'A-2', 'A-3', 'B-1', 'B-2', 'C-1', 'C-3', 'C-4', 'D-1', 'D-2', 'D-3', 'D-4', 'D-5', 'D-6', 'D-7', 'D-8', 'D-9', 'D-10', 'E-1', 'E-2', 'E-3', 'E-4', 'E-5', 'E-6', 'E-7', 'E-8', 'E-9', 'E-10', 'F-1', 'F-2', 'F-3', 'F-5', 'F-6', 'G-1', 'H-1', 'DONGPO', 'REGION', 'YOUTH', 'TOPTIER', 'METRO', 'KSTAR'];
const EXPECTED_VISA = ['A-1', 'A-2', 'A-3', 'B-1', 'B-2', 'C-1', 'C-3', 'C-4', 'D-1', 'D-2', 'D-3', 'D-4', 'D-5', 'D-6', 'D-7', 'D-8', 'D-9', 'D-10', 'E-1', 'E-2', 'E-3', 'E-4', 'E-5', 'E-6', 'E-7', 'E-8', 'E-9', 'E-10', 'F-1', 'F-2', 'F-3', 'F-4', 'F-5', 'F-6', 'G-1', 'H-1', 'H-2', 'DONGPO', 'TOPTIER', 'KSTAR'];
for (const [manual, expected] of [['stay_manual_2026_09_18', EXPECTED_STAY], ['visa_manual_2026_09_01', EXPECTED_VISA]]) {
  const chapters = manifest.chapters[manual];
  const keys = new Set(chapters.map((c) => c.key));
  for (const key of expected) {
    check(`${manual} chapter ${key} inventoried`, () => {
      assert(keys.has(key), 'missing chapter (blocking)');
      const c = chapters.find((x) => x.key === key);
      assert(Number.isInteger(c.pdf_start) && c.pdf_start >= 1, `no PDF start page (${c.detection})`);
      assert(Number.isInteger(c.pdf_end) && c.pdf_end >= c.pdf_start, 'PDF range inverted');
      assert(Number.isInteger(c.hwp_start), 'no HWP line');
      assert(pageText[manual].has(c.pdf_start), 'PDF start page not in corpus');
    });
  }
  check(`${manual} chapters are in manual order`, () => {
    const seq = chapters.filter((c) => c.kind !== 'reference' && c.pdf_start).map((c) => c.pdf_start);
    for (let i = 1; i < seq.length; i++) assert(seq[i] > seq[i - 1], `chapter ${chapters[i].key} starts before its predecessor`);
  });
}

/* ------------------------------------------------------------ records ---- */
check('every top-level status in the manuals has a status record', () => {
  for (const code of [...EXPECTED_STAY.filter((k) => /^[A-H]-\d/.test(k)), 'F-4', 'H-2']) assert(byCode.has(code) && byCode.get(code).kind === 'status', `missing status record ${code}`);
});
for (const r of records) {
  check(`record ${r.code}: explicit states and provenance`, () => {
    assert(COVERAGE.has(r.coverage_state), `coverage_state ${r.coverage_state} not in enum`);
    assert(r.temporal && r.temporal.source_edition === '2026.9', 'source edition not recorded');
    assert(typeof r.lifecycle === 'string', 'lifecycle missing');
    assert(DOCSTATES.has(r.document_guidance), `document_guidance ${r.document_guidance} not explicit`);
    assert(typeof r.source_verification === 'string', 'source_verification missing');
    if (r.kind === 'substatus') {
      assert(r.parent && r.code.startsWith(r.parent + '-'), `parent ${r.parent} does not match code`);
      assert(byCode.has(r.parent), 'parent record missing');
      assert(r.name_ko, 'no Korean display name');
      assert(r.name_en_state === (r.name_en ? 'AVAILABLE' : 'NOT_AVAILABLE'), 'name_en_state disagrees with name_en');
    }
    if (r.kind !== 'program') {
      for (const pid of PROCEDURES) {
        const st = r.procedures[pid];
        if (r.kind === 'scenario' && !st) continue;
        assert(st && PROC.has(st.state), `procedure ${pid} has no explicit state`);
        assert(DOCSTATES.has(st.document_guidance), `procedure ${pid} document state ${st.document_guidance} not explicit`);
        if (['SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY', 'NOT_APPLICABLE', 'GENERALLY_NOT_PERMITTED', 'SOURCE_ONLY'].includes(st.state) && st.state !== 'NOT_APPLICABLE') {
          assert(st.source && Number.isInteger(st.source.pdf_page), `procedure ${pid} (${st.state}) has no source page — source-only fallback would dead-end`);
          assert(pageText[st.source.manual].has(st.source.pdf_page), `procedure ${pid} source page ${st.source.pdf_page} not in corpus`);
        }
      }
    }
    if (r.coverage_state === 'UNVERIFIED') {
      assert(r.source_verification === 'NOT_IN_SEPT_2026_MANUALS', 'UNVERIFIED record must state it is not in the manuals');
      assert(!Object.values(r.procedures).some((s) => s.state === 'SUPPORTED' && !s.inherited_from_parent), 'UNVERIFIED code must not carry its own SUPPORTED guidance');
      assert(!bundle.guidance.some((g) => g.target.split('~')[0] === r.code), 'UNVERIFIED code must not have guidance entries');
    }
    if (r.coverage_state === 'SUPPORTED' && r.kind !== 'program') {
      assert(Object.values(r.procedures).some((s) => s.state === 'SUPPORTED' || s.state === 'CONDITIONAL'), 'SUPPORTED record needs a supported procedure');
    }
    if (r.kind !== 'program') {
      const src = r.source && (r.source.stay || r.source.visa);
      if (r.coverage_state !== 'UNVERIFIED') assert(src, 'record present in the manuals must carry a source block');
    }
    if (r.lifecycle === 'legacy_holders_only' || r.lifecycle === 'abolished') {
      assert(r.temporal.legacy_source && r.temporal.legacy_source.pdf_page, 'legacy marker must be anchored to a page');
      assert(pageHas(r.temporal.legacy_source.anchor && (r.temporal.legacy_source.pdf_page > 400 ? 'stay_manual_2026_09_18' : 'stay_manual_2026_09_18'), r.temporal.legacy_source.pdf_page, r.temporal.legacy_source.anchor), 'legacy anchor text not on the recorded page');
      assert(r.temporal.new_application_allowed === false || r.temporal.legacy_holder_rule, 'legacy record must say new applications are not allowed or carry a holder rule');
    }
  });
}

/* ----------------------------------------------------------- guidance ---- */
for (const g of bundle.guidance) {
  check(`guidance ${g.target}|${g.procedure}${g.scenario ? '#' + g.scenario : ''}: provenance`, () => {
    assert(PROCEDURES.includes(g.procedure), 'unknown procedure');
    assert(PROC.has(g.state), 'state not in enum');
    assert(['FULLY_STRUCTURED', 'PARTIALLY_STRUCTURED', 'SOURCE_ONLY', 'REQUIRES_CLARIFICATION', 'UNVERIFIED'].includes(g.completeness), 'completeness not explicit');
    assert(g.source && g.source.edition === '2026.9' && Number.isInteger(g.source.pdf_page), 'no 2026.9 page provenance');
    assert(pageText[g.source.manual].has(g.source.pdf_page), 'page not in corpus');
    const authored = rules.guidance.find((r) => r.target === g.target && r.procedure === g.procedure && (r.scenario || null) === (g.scenario || null));
    assert(authored, 'no authored rule behind the compiled entry');
    assert(pageHas(g.source.manual, g.source.pdf_page, authored.source.anchor), `section anchor not on page ${g.source.pdf_page}`);
    const base = g.target.split('~')[0].split('#')[0];
    if (base === 'COMMON') {
      // Status-independent rule: not a status record. It must be declared in the procedure registry and carry the
      // regulation that defines it, otherwise the router could serve a baseline nobody sourced.
      const reg = (bundle.procedure_registry || []).find((r) => r.procedure === g.procedure);
      assert(reg && reg.common_target === 'COMMON', 'COMMON entry without a procedure-registry declaration');
      assert(['STATUS_INDEPENDENT', 'STATUS_OPTIONAL'].includes(reg.context_requirement), `COMMON entry for a ${reg && reg.context_requirement} procedure`);
      assert(Array.isArray(g.law_sources) && g.law_sources.length && g.law_sources.every((id) => bundle.law_sources && bundle.law_sources[id]), 'COMMON entry must cite regulation sources present in the bundle');
      return;
    }
    assert(byCode.has(base) || byCode.has(g.target), 'target not in manifest');
    const rec = byCode.get(g.target) || byCode.get(base);
    assert(rec.coverage_state !== 'UNVERIFIED', 'guidance attached to an UNVERIFIED code');
    if (['NOT_APPLICABLE', 'GENERALLY_NOT_PERMITTED', 'EXCEPTION_ONLY', 'SOURCE_ONLY', 'UNVERIFIED'].includes(g.state)) {
      assert(g.completeness !== 'FULLY_STRUCTURED' || g.state === 'EXCEPTION_ONLY', `${g.state} entry must not present a definitive checklist`);
    }
  });
}
check('state overrides are anchored inside their chapter', () => {
  for (const o of bundle.state_overrides) {
    assert(Number.isInteger(o.pdf_page), `${o.target}|${o.procedure} no page`);
    assert(PROC.has(o.state), `${o.target}|${o.procedure} state not in enum`);
    const rec = byCode.get(o.target); assert(rec, `${o.target} missing`);
    assert(rec.procedures[o.procedure].state === o.state, `${o.target}|${o.procedure} manifest state ${rec.procedures[o.procedure].state} != override ${o.state}`);
  }
});
check('programs are first-class records with chapter provenance', () => {
  for (const p of bundle.programs) {
    const rec = byCode.get('PROGRAM:' + p.id); assert(rec, `program ${p.id} missing`);
    assert(Number.isInteger(p.pdf_page) && pageHas('stay_manual_2026_09_18', p.pdf_page, rules.programs.find((x) => x.id === p.id).anchor), `program ${p.id} anchor not on page`);
    assert(rec.source.stay.pdf_page_start, `program ${p.id} has no chapter range`);
    for (const code of p.codes) assert(byCode.has(code), `program ${p.id} code ${code} not in manifest`);
    for (const code of p.codes) assert((byCode.get(code).programs || []).includes(p.id), `${code} does not list program ${p.id}`);
  }
  const ids = new Set(bundle.programs.map((p) => p.id));
  for (const id of ['dongpo', 'regional', 'youth', 'top-tier', 'metro', 'k-star']) assert(ids.has(id), `program ${id} missing`);
});
check('transitions model current status and anchor every exclusion', () => {
  for (const t of bundle.transitions) {
    assert(byCode.has(t.to), `transition ${t.id} target ${t.to} missing`);
    assert(Number.isInteger(t.pdf_page), `transition ${t.id} not anchored`);
    for (const ex of t.exclusions || []) { assert(PROC.has(ex.state), `${t.id} exclusion state`); assert(Number.isInteger(ex.pdf_page), `${t.id} exclusion ${ex.class} not anchored`); for (const e2 of ex.exceptions || []) assert(Number.isInteger(e2.pdf_page), `${t.id} exception not anchored`); }
    assert(['SOURCE_ONLY', 'FULLY_STRUCTURED', 'PARTIALLY_STRUCTURED'].includes(t.documents_state), `${t.id} documents_state`);
  }
  const f6 = bundle.transitions.find((t) => t.to === 'F-6-1');
  assert(f6 && f6.exclusions.some((e) => e.class === 'SHORT_STAY') && f6.exclusions.some((e) => e.class === 'H-1'), 'F-6-1 transition must exclude short-stay and H-1');
});
check('overlays are anchored and scoped', () => {
  for (const o of bundle.overlays) { assert(Number.isInteger(o.pdf_page), `overlay ${o.id} no page`); assert(o.scope && o.scope.domains, `overlay ${o.id} unscoped`); assert(o.ko && o.en, `overlay ${o.id} copy`); }
  for (const id of ['domestic_doc_validity_3m', 'previously_submitted_omitted', 'foreign_doc_apostille', 'admin_info_sharing', 'sealed_medical_docs', 'must_be_in_korea', 'fees_non_refundable', 'fee_table', 'passport_validity_cap', 'occupation_income_report', 'school_enrollment_6_18', 'tb_certificate', 'officer_discretion']) assert(bundle.overlays.some((o) => o.id === id), `overlay ${id} missing`);
});
check('resolver families point only at manifest codes', () => {
  for (const [fam, spec] of Object.entries(bundle.families)) {
    assert(byCode.has(fam), `family ${fam} not a status`);
    for (const d of spec.dimensions) for (const o of d.options) for (const t of o.targets) {
      const base = t.split('#')[0];
      assert(byCode.has(base) || byCode.has(base.split('~')[0]), `family ${fam} option ${o.id} targets unknown ${t}`);
      if (t.includes('#')) assert(bundle.guidance.some((g) => g.target + '#' + g.scenario === t), `family ${fam} option ${o.id} targets unknown scenario ${t}`);
    }
  }
});
check('bundle code index mirrors the manifest', () => {
  for (const r of records) { const c = bundle.codes[r.code]; assert(c, `bundle missing ${r.code}`); assert(c.coverage_state === r.coverage_state, `${r.code} coverage drift`); }
});
check('legacy taxonomy conflicts are recorded, not silently resolved', () => {
  assert(Array.isArray(manifest.conflicts) && manifest.conflicts.length > 0, 'no conflict records');
  assert(manifest.conflicts.some((c) => c.kind === 'edition_lag'), 'edition lag not recorded');
  assert(manifest.conflicts.some((c) => c.status === 'F-2-6'), 'abolished F-2-6 not recorded');
  assert(byCode.get('H-2').temporal.new_application_allowed === false, 'H-2 must be existing-holder only');
  assert(byCode.get('F-2-6').coverage_state === 'LEGACY_ONLY', 'F-2-6 must be LEGACY_ONLY');
});

/* ------------------------------------------------------------- report ---- */
const s = manifest.summary;
const report = {
  TOTAL_MANUAL_CHAPTERS: `stay ${s.numbered_chapters.stay} (+2 preambles) · visa ${s.numbered_chapters.visa} (+2 preambles)`,
  TOTAL_STATUS_RECORDS: s.total_status_records, TOTAL_SUBSTATUS_RECORDS: s.total_substatus_records, TOTAL_SCENARIO_RECORDS: s.total_scenario_records, TOTAL_SPECIAL_PROGRAM_RECORDS: s.total_special_program_records,
  ...Object.fromEntries(['SUPPORTED', 'PARTIAL', 'SOURCE_ONLY', 'UNVERIFIED', 'NOT_APPLICABLE', 'LEGACY_ONLY'].map((k) => [k, s.coverage_states_all[k] || 0])),
};
console.log('[check_status_coverage_manifest] coverage report', JSON.stringify(report));
if (failures.length) { console.error(`[check_status_coverage_manifest] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_status_coverage_manifest] OK — ${passed} checks passed over ${records.length} records`);
