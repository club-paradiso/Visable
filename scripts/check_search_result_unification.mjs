/*
 * check_search_result_unification.mjs
 * ----------------------------------------------------------------------------
 * Search result reliability regressions (2026-09-23 sprint). Offline, Node only.
 * Renders the structured guidance (assets/js/status-guidance.js) the way the
 * page does and ranks the September originals the way the evidence disclosure
 * does (assets/js/manual-corpus-search.js), then asserts:
 *
 *  1. D-2 (exact code): definitive interpretation, never "가장 가까워 보여요";
 *     no internal source ids, no 2026-05 / 2026.6 labels; D-2 → 체류기간 연장
 *     answers "D-2 기준으로 안내해요";
 *  2. fee notes are semantically unique (the data note "…반환되지 않습니다." and
 *     the renderer note "…반환되지 않아요." print once), for every fee row, ko/en;
 *  3. document rows: no repeated silent-source fallback paragraph; the
 *     preparation note appears once per document section;
 *  4. common rules are tiered: rules no document or status triggers (sealed
 *     medical certificates for D-2 extension) sit behind the disclosure;
 *  5. evidence relevance: the D-2 연장 evidence query ranks D-2 extension pages
 *     first and never puts the D-2 → E-1 / D-2 → D-10 change pages in the top
 *     results; the same signals hold for other statuses (not a D-2 special case);
 *  6. the sprint query matrix renders without internal ids, stale labels or
 *     duplicate fee notes.
 *
 *   node scripts/check_search_result_unification.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');
const bundle = JSON.parse(read('data/status-guidance-202609.json'));
bundle.local_practice = JSON.parse(read('data/local-practice-202609.json'));
new Function(read('assets/js/status-guidance.js'))();
new Function(read('assets/js/search-router.js'))();
new Function(read('assets/js/manual-corpus-search.js'))();
const SG = globalThis.VisableStatusGuidance;
const MS = globalThis.VisableManualSearch;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

function run(query, extra = {}, lang = 'ko') {
  const interp = SG.interpret(query, bundle);
  const state = { interp, answers: {}, procedure: null, status: null, history: [], lang, query, ...extra };
  const step = SG.nextStep(state, bundle);
  const out = SG.renderModel(step, state, bundle);
  const text = out.html.replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/g, ' ').replace(/\s+/g, ' ');
  return { interp, state, step, ...out, text };
}
const INTERNAL_ID = /_pdf\b|stay_manual_20|visa_manual_20/;
const STALE = /2026-05|2026\.6 |2026\.06|체류민원 안내매뉴얼 기준/;
const count = (s, needle) => s.split(needle).length - 1;

/* 1. D-2 exact */
check('D-2: exact code reads definitively and asks the procedure', () => {
  const r = run('D-2');
  assert(/data-sg-match="EXACT_CODE"/.test(r.html), 'EXACT_CODE interpretation');
  assert(!r.text.includes('가장 가까워'), 'no "closest" hedge');
  assert(!r.text.includes('이해했어요'), 'no hedged "이해했어요" strip for an exact code');
  assert(r.step.kind === 'question' && r.step.dimension === '__procedure', `kind ${r.step.kind}`);
  assert(r.html.includes('sg-options-grid'), 'compact procedure picker');
  assert(!INTERNAL_ID.test(r.text), 'internal id visible');
  assert(!STALE.test(r.text), 'stale source label visible');
});
check('D-2 → 체류기간 연장: definitive lead, one fee note, one preparation note', () => {
  const r = run('D-2', { procedure: 'extension' });
  assert(r.step.kind === 'resolved', `kind ${r.step.kind}`);
  assert(r.text.includes('D-2 기준으로 안내해요'), 'definitive lead');
  assert(!r.text.includes('가장 가까워'), 'no "closest" hedge');
  assert(count(r.text, '반환되지 않') === 1, `refund note printed ${count(r.text, '반환되지 않')} times`);
  assert(count(r.html, 'sg-doc-prep-note') <= 1, 'preparation note at most once');
  assert(!r.text.includes('공식 안내에 제출 형태가 따로 적혀 있지 않아요'), 'no per-row fallback paragraph');
  assert(!INTERNAL_ID.test(r.text) && !STALE.test(r.text), 'no internal id / stale label');
});
check('D-2 연장 (typed): same definitive answer', () => {
  const r = run('D-2 연장');
  assert(r.step.kind === 'resolved' && /data-sg-match="EXACT_CODE"/.test(r.html), `${r.step.kind}`);
  assert(r.text.includes('D-2 기준으로 안내해요') && !r.text.includes('가장 가까워'), 'definitive');
});

/* 2. fee note dedupe — every fee row, both languages */
check('fee notes: data note and renderer note are one note (ko/en, every fee row)', () => {
  for (const lang of ['ko', 'en']) {
    const renderer = SG.STR[lang].feeNonRefundable;
    for (const f of bundle.fees) {
      for (const n of (lang === 'en' ? f.notes_en : f.notes_ko) || []) {
        if (/반환|refund/i.test(n)) assert(SG.uniqueNotes([n, renderer]).length === 1, `${lang} ${f.id}: "${n}" vs "${renderer}"`);
      }
    }
  }
  assert(SG.uniqueNotes(['심사수수료이므로 접수 후 반환되지 않습니다.', '심사수수료이므로 접수 후 반환되지 않아요.']).length === 1, 'register variants');
  assert(SG.uniqueNotes(['온라인 신청 시 20% 감경', '심사수수료이므로 접수 후 반환되지 않아요.']).length === 2, 'different notes stay');
});
for (const q of ['D-2 연장', 'F-6-1 연장', 'E-7-4 연장', '외국인등록증 재발급', 'D-10 연장']) {
  check(`fee section of "${q}" has no semantically duplicate lines`, () => {
    const r = run(q);
    const m = r.html.match(/<section class="sg-fee"[^]*?<\/section>/);
    if (!m) return;
    const lines = [...m[0].matchAll(/<p class="sg-fee-line[^"]*">([^<]*)<\/p>/g)].map((x) => x[1]);
    assert(SG.uniqueNotes(lines).length === lines.length, `duplicates in ${JSON.stringify(lines)}`);
  });
}

/* 4. common rules tiered */
check('common rules: D-2 extension shows presence + passport cap, keeps sealed medical rule behind the disclosure', () => {
  const r = run('D-2', { procedure: 'extension' });
  const t = r.model.overlayTiers;
  const ids = (list) => list.map((o) => o.id);
  assert(ids(t.critical).includes('must_be_in_korea') && ids(t.critical).includes('passport_validity_cap'), `critical ${ids(t.critical)}`);
  assert(ids(t.reference).includes('sealed_medical_docs'), `sealed medical rule not in reference: ${ids(t.reference)}`);
  assert(r.html.includes('sg-rules-more'), 'reference rules behind one disclosure');
});
check('common rules: a medical certificate on the list triggers the sealed-document rule', () => {
  const hit = bundle.guidance.find((g) => (g.documents || []).some((d) => /건강진단|마약|신체검사/.test(d.name_ko || '')) && g.target !== 'COMMON');
  if (!hit) return;
  const tiers = SG.tierOverlays(bundle.overlays.filter((o) => o.id === 'sealed_medical_docs'), hit);
  assert(tiers.contextual.length === 1, `${hit.target} ${hit.procedure}`);
});

/* 5. evidence relevance */
const catalog = JSON.parse(read('data/manual-corpus/catalog.json'));
const pages = catalog.sources.flatMap((s) => JSON.parse(read(s.sections)));
const index = MS.prepare(catalog.sources, pages);
function intentFor(query, extra = {}) {
  const r = run(query, extra);
  const parent = r.model.status ? SG.parentOf(r.model.status) : null;
  const chapters = {};
  if (parent) for (const [mid, ch] of Object.entries(bundle.chapters)) { const c = ch[parent]; if (c && bundle.sources[mid]) chapters[bundle.sources[mid].corpus_source_id] = [c.pdf_start, c.pdf_end]; }
  const anchors = r.model.evidence.filter((e) => e.type === 'manual' && e.corpusId && e.kind !== 'fee').map((e) => ({ source: e.corpusId, page: Number(e.page) }));
  const proc = bundle.procedures.find((p) => p.id === r.model.procedure);
  return { status: r.model.status, procedure: r.model.procedure, chapters, anchors, domain: proc ? (proc.domain === 'visa' ? 'visa_issuance' : 'stay') : null };
}
const STAY = 'stay_manual_2026_09_18_pdf';
check('D-2 연장 evidence: D-2 extension pages first; D-2 → E-1 (p.173) and D-2 → D-10 (p.210) out of the top results', () => {
  const intent = intentFor('D-2 연장');
  const hits = MS.search(index, 'D-2 연장', { intent });
  const top = hits.slice(0, 5).map((h) => `${h.source.id}:${h.page.page}`);
  assert(hits[0].source.id === STAY && hits[0].page.page === 43, `top ${top}`);
  assert(!top.includes(`${STAY}:173`) && !top.includes(`${STAY}:210`), `transition pages in top 5: ${top}`);
  const [a, b] = intent.chapters[STAY];
  assert(hits.slice(0, 3).every((h) => h.source.id === STAY && h.page.page >= a && h.page.page <= b), `top 3 inside the D-2 chapter: ${top}`);
  // the raw keyword search (no intent) still reproduces the old failure, proving the intent path is what fixes it
  const rawTop = MS.search(index, 'D-2 연장', {})[0];
  assert(rawTop.page.page === 173, `raw baseline top ${rawTop.page.page}`);
});
check('D-2 evidence (status only): the chapter opening outranks transition pages', () => {
  const intent = intentFor('D-2');
  const hits = MS.search(index, 'D-2', { intent });
  assert(hits[0].page.page === 35 || hits[0].page.page === 62, `top ${hits[0].source.id}:${hits[0].page.page}`);
  assert(!hits.slice(0, 5).some((h) => /➠/.test(h.page.heading)), 'no "A ➠ B" heading in the top 5');
});
for (const [q, extra] of [['F-6-1 연장', { answers: { f6_1_route: 'normal' } }], ['E-7-4 연장', {}], ['D-2 아르바이트', {}], ['D-10 연장', {}]]) {
  check(`${q} evidence: top result sits in the status chapter and speaks the procedure`, () => {
    const intent = intentFor(q, extra);
    if (!intent.status) return;
    const hits = MS.search(index, q, { intent });
    assert(hits.length, 'no hits');
    const h = hits[0];
    const range = intent.chapters[h.source.id];
    const anchored = intent.anchors.some((a) => a.source === h.source.id && Math.abs(a.page - h.page.page) <= 1);
    assert(anchored || (range && h.page.page >= range[0] && h.page.page <= range[1]), `top ${h.source.id}:${h.page.page} outside chapter ${JSON.stringify(range)}`);
    assert(!/➠/.test(h.page.heading) || intent.procedure === 'status_change', `transition page on top: ${h.page.heading}`);
  });
}

/* 6. query matrix */
const MATRIX = ['D-2', 'D-2 연장', 'D-2 연장하려면 뭐 필요해?', 'D-2 아르바이트', 'F-6', 'F-6 연장', '외국인등록증 재발급', '주소 변경 신고', 'E-7-4 연장', 'GKS 장학생인데 연장수수료 면제돼?'];
for (const q of MATRIX) {
  for (const lang of ['ko', 'en']) {
    check(`matrix [${lang}] "${q}": no internal ids, no stale labels, no duplicate fee lines`, () => {
      const r = run(q, {}, lang);
      assert(!INTERNAL_ID.test(r.text), `internal id in: ${(r.text.match(INTERNAL_ID) || [])[0]}`);
      assert(!STALE.test(r.text), 'stale label');
      const fee = ((r.html.match(/<section class="sg-fee"[^]*?<\/section>/) || [''])[0]).replace(/<[^>]+>/g, ' ');
      assert(count(fee, lang === 'ko' ? '반환되지 않' : 'not refunded') <= 1, 'refund note repeated in the fee section');
      if (/^[A-H]-\d/.test(q)) assert(!r.text.includes('가장 가까워') && !r.text.includes('looks closest'), 'hedged wording on an exact code');
    });
  }
}
check('evidence rows use human manual titles, never the internal id, even when a title is missing', () => {
  assert(SG.manualTitle('ko', { manual: 'stay_manual_2026_09_18', title_ko: '' }) === '외국인체류 안내매뉴얼', 'stay fallback');
  assert(SG.manualTitle('en', { manual: 'visa_manual_2026_09_01', title_en: '' }) === 'Visa issuance manual', 'visa fallback');
});

if (failures.length) {
  console.error(`[check_search_result_unification] FAIL — ${failures.length} failure(s), ${passed} passed`);
  failures.forEach((f) => console.error('  - ' + f));
  process.exit(1);
}
console.log(`[check_search_result_unification] OK — ${passed} checks passed`);
