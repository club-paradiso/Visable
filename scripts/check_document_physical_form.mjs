/*
 * check_document_physical_form.mjs
 * ----------------------------------------------------------------------------
 * Physical-form (original / copy) QA over every document rule in the guidance
 * bundle, plus the coverage report the PR quotes.
 *
 *  - every item carries an explicit submission_form from the enum (never absent);
 *  - a form is set ONLY from the transcribed source phrase of that rule or from a
 *    quoted regulation clause — never from what the document "usually" is;
 *  - the same document name carries different forms across procedures when the
 *    sources differ (passport, residence card, employment contract, letter of
 *    guarantee, business registration), and a shared generic definition
 *    ("여권") is never upgraded anywhere;
 *  - the renderer shows a form label only when explicit and shows an explicit
 *    "not specified" state otherwise (no silent default);
 *  - writes reports/data-coverage/document-physical-form-202609.{md,json}.
 *
 *   node scripts/check_document_physical_form.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
const rules = JSON.parse(readFileSync(join(ROOT, 'data/guidance-rules-202609.json'), 'utf8'));
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;

let passed = 0; const failures = [];
function check(name, fn) { try { fn(); passed += 1; } catch (e) { failures.push(`${name}: ${e.message}`); } }
function assert(c, m) { if (!c) throw new Error(m || 'assertion failed'); }

const FORMS = new Set(rules.enums.submission_forms);
const EXPLICIT = new Set(['ORIGINAL_ONLY', 'COPY_ONLY', 'ORIGINAL_AND_COPY', 'ORIGINAL_PRESENT_COPY_SUBMIT', 'CERTIFIED_COPY', 'ONE_OF_ORIGINAL_OR_COPY', 'ELECTRONIC_DOCUMENT_ACCEPTED']);
const items = [];
for (const g of bundle.guidance) for (const d of g.documents) if (d.ref !== 'fee') items.push({ g, d });

/* ------------------------------------------------ per-item invariants ---- */
for (const { g, d } of items) {
  const label = `${g.target}|${g.procedure}${g.scenario ? '#' + g.scenario : ''} ${d.ref}`;
  check(`${label}: explicit form with a legitimate basis`, () => {
    assert(FORMS.has(d.submission_form), `form ${d.submission_form}`);
    assert(['SOURCE_PHRASE', 'REGULATION', 'NONE'].includes(d.form_basis), `basis ${d.form_basis}`);
    if (d.submission_form === 'SOURCE_DOES_NOT_SPECIFY') assert(d.form_basis === 'NONE', 'unspecified form must not claim a basis');
    else assert(d.form_basis !== 'NONE', 'a stated form needs a basis');
    if (d.form_basis === 'SOURCE_PHRASE') assert(/원본|사본/.test(d.name_ko), 'source-phrase form without 원본/사본 in the transcribed name');
    if (d.form_basis === 'REGULATION') assert(d.source && (d.source.type === 'regulation' || d.source.law), 'regulation form without a regulation source');
    if (d.copy_count != null) assert(Number.isInteger(d.copy_count) && d.copy_count > 0 && ['COPY_ONLY', 'ORIGINAL_AND_COPY', 'ORIGINAL_PRESENT_COPY_SUBMIT'].includes(d.submission_form), 'copy count only with a copy form');
    if (d.original_returned != null) assert(typeof d.original_returned === 'boolean' && d.submission_form === 'ORIGINAL_ONLY', 'return flag only for an original');
  });
}

/* --------------------------------------- never a document-name default ---- */
check('a shared generic definition is never upgraded: "여권" (passport) is unspecified in every rule that uses it', () => {
  const generic = items.filter(({ d }) => d.ref === 'passport');
  assert(generic.length > 20, 'passport is used widely');
  for (const { g, d } of generic) assert(d.submission_form === 'SOURCE_DOES_NOT_SPECIFY', `${g.target}|${g.procedure}: passport upgraded to ${d.submission_form}`);
});
check('items with 원본/사본 in the transcribed phrase never sit at SOURCE_DOES_NOT_SPECIFY unless the anchor disproves the phrase', () => {
  for (const { g, d } of items) {
    if (/원본|사본/.test(d.name_ko) && d.submission_form === 'SOURCE_DOES_NOT_SPECIFY') assert(d.form_review_state === 'PHRASE_NOT_IN_ANCHOR', `${g.target}|${g.procedure} ${d.ref}: phrase marker ignored without a review flag`);
  }
});

/* ------------------------------ same document, different procedure ---- */
function find(target, procedure, ref, scenario) { const g = bundle.guidance.find((x) => x.target === target && x.procedure === procedure && (scenario === undefined || (x.scenario || null) === scenario)); const d = g && g.documents.find((x) => x.ref === ref); assert(d, `missing ${target}|${procedure} ${ref}`); return d; }
check('passport: copy only (D-10-1 extension) vs original only (B-1 extension) vs original + 1 copy (D-2 registration) vs not specified (F-6-1 extension)', () => {
  assert(find('D-10-1', 'extension', 'passport_copy').submission_form === 'COPY_ONLY', 'D-10-1');
  assert(find('B-1', 'extension', 'passport_original').submission_form === 'ORIGINAL_ONLY', 'B-1');
  const d2 = find('D-2', 'registration', 'passport_and_copy'); assert(d2.submission_form === 'ORIGINAL_AND_COPY' && d2.copy_count === 1, 'D-2 registration');
  assert(find('F-6-1', 'extension', 'passport', 'extension').submission_form === 'SOURCE_DOES_NOT_SPECIFY', 'F-6-1 stays unspecified');
});
check('residence card: original presented and returned (address report, Act 36(2)) vs not specified (D-2 info report) vs existing card handed in and destroyed (reissue, Decree 42)', () => {
  const rep = find('COMMON', 'residence_report', 'arc'); assert(rep.submission_form === 'ORIGINAL_ONLY' && rep.original_returned === true && rep.form_basis === 'REGULATION', 'address report');
  assert(find('D-2', 'registration_info_report', 'arc').submission_form === 'SOURCE_DOES_NOT_SPECIFY', 'D-2 info report');
  const re = find('COMMON', 'card_reissue', 'arc_existing_original'); assert(re.submission_form === 'ORIGINAL_ONLY' && re.original_returned === false, 'reissue');
});
check('employment contract: original and copy (E-1 extension) vs not specified (E-7 extension)', () => {
  assert(find('E-1', 'extension', 'contract_original_copy').submission_form === 'ORIGINAL_AND_COPY', 'E-1');
  assert(find('E-7', 'extension', 'employment_contract').submission_form === 'SOURCE_DOES_NOT_SPECIFY', 'E-7');
});
check('letter of guarantee: original (E-7 occupations) vs not specified (F-1 relative visit)', () => {
  assert(find('E-7', 'extension', 'guarantor_original_occupations').submission_form === 'ORIGINAL_ONLY', 'E-7');
  assert(find('F-1~relative-visit', 'extension', 'guarantor').submission_form === 'SOURCE_DOES_NOT_SPECIFY', 'F-1');
});
check('business registration: copy (E-9 extension) vs varies-by-item composite (E-7 "사본 또는 법인등기부등본") vs not specified (bare 사업자등록증)', () => {
  assert(find('E-9', 'extension', 'business_reg_copy').submission_form === 'COPY_ONLY', 'E-9');
  assert(find('E-7', 'extension', 'business_reg_or_corp').submission_form === 'VARIES_BY_ITEM', 'E-7 composite');
  const bare = items.find(({ d }) => d.ref === 'business_reg'); assert(bare && bare.d.submission_form === 'SOURCE_DOES_NOT_SPECIFY', 'bare 사업자등록증');
});
check('residence proof / lease: no rule states a physical form, so none is shown (the law lists the document, not its form)', () => {
  for (const { g, d } of items) if (/residence|lease/.test(d.ref)) assert(d.submission_form === 'SOURCE_DOES_NOT_SPECIFY', `${g.target}|${g.procedure} ${d.ref}`);
});

/* --------------------------------------------------------- rendering ---- */
check('renderer: explicit forms get a label; unspecified forms get none on the row and an explicit note in the details', () => {
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_AND_COPY', copy_count: 1 }) === '원본 + 사본 1부', 'ORIGINAL_AND_COPY label');
  assert(SG.formLabel('ko', { submission_form: 'COPY_ONLY' }) === '사본', 'COPY_ONLY label');
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_ONLY', original_returned: true }) === '원본 · 돌려받음', 'returned original');
  assert(SG.formLabel('en', { submission_form: 'ORIGINAL_ONLY', original_returned: false }) === 'Original', 'EN original');
  assert(SG.formLabel('ko', { submission_form: 'SOURCE_DOES_NOT_SPECIFY' }) === '' && SG.formLabel('ko', {}) === '', 'no default label');
  const run = (q, answers = {}) => { const interp = SG.interpret(q, bundle); const state = { interp, answers, procedure: null, status: null, history: [], lang: 'ko' }; const step = SG.nextStep(state, bundle); return SG.renderModel(step, state, bundle).html; };
  const d2 = run('D-2 외국인등록'); assert(d2.includes('sg-doc-form">원본 + 사본 1부<'), 'D-2 registration passport shows 원본 + 사본 1부');
  const f6 = run('F-6-1 연장', { f61_phase: 'normal' }); assert(!/여권<\/span>(<span class="sg-doc-ko"[^>]*>[^<]*<\/span>)?<span class="sg-doc-form">/.test(f6), 'F-6-1 passport row carries no form label'); assert(f6.includes('원본·사본 표기가 없어요'), 'explicit not-specified note in details');
  const e9 = run('E-9-1 연장'); assert(e9.includes('sg-doc-form">사본<'), 'E-9 copies labelled');
  const addr = run('주소 변경 신고'); assert(addr.includes('원본 · 돌려받음'), 'address report card returned');
});

/* ------------------------------------------------------------- report ---- */
const counts = { TOTAL_DOCUMENT_RULES: items.length, FORM_EXPLICIT: 0, ORIGINAL_ONLY: 0, COPY_ONLY: 0, ORIGINAL_AND_COPY: 0, ORIGINAL_PRESENT_COPY_SUBMIT: 0, CERTIFIED_COPY: 0, ONE_OF_ORIGINAL_OR_COPY: 0, ELECTRONIC_DOCUMENT_ACCEPTED: 0, VARIES_BY_ITEM: 0, SOURCE_DOES_NOT_SPECIFY: 0, UNVERIFIED: 0, BASIS_SOURCE_PHRASE: 0, BASIS_REGULATION: 0 };
for (const { d } of items) {
  counts[d.submission_form] = (counts[d.submission_form] || 0) + 1;
  if (EXPLICIT.has(d.submission_form)) counts.FORM_EXPLICIT += 1;
  if (d.form_review_state === 'PHRASE_NOT_IN_ANCHOR') counts.UNVERIFIED += 1;
  if (d.form_basis === 'SOURCE_PHRASE') counts.BASIS_SOURCE_PHRASE += 1;
  if (d.form_basis === 'REGULATION') counts.BASIS_REGULATION += 1;
}
const pct = (n) => (items.length ? (100 * n / items.length).toFixed(1) + '%' : '0%');
const explicitRows = items.filter(({ d }) => d.submission_form !== 'SOURCE_DOES_NOT_SPECIFY').map(({ g, d }) => `| ${g.target}${g.scenario ? '#' + g.scenario : ''} | ${g.procedure} | ${d.name_ko} | ${d.submission_form}${d.copy_count ? ' ×' + d.copy_count : ''}${d.original_returned === true ? ' (returned)' : d.original_returned === false ? ' (kept)' : ''} | ${d.form_basis} | ${d.source && d.source.type === 'regulation' ? bundle.law_sources[d.source.law].title_ko + ' ' + bundle.law_sources[d.source.law].article : 'p.' + (d.source && d.source.pdf_page)} |`);
const md = `# Document physical-form coverage — 2026.9 bundle

Generated by \`scripts/check_document_physical_form.mjs\` from \`data/status-guidance-202609.json\`.
A form is recorded only when the rule's own source phrase (or a quoted regulation clause) states it.
**${pct(counts.SOURCE_DOES_NOT_SPECIFY)} of document rules carry no original/copy statement in the source; the UI says so instead of guessing.**

| Metric | Count | Share |
| --- | ---: | ---: |
| TOTAL DOCUMENT RULES (fee items excluded) | ${counts.TOTAL_DOCUMENT_RULES} | 100% |
| FORM_EXPLICIT (a definite form) | ${counts.FORM_EXPLICIT} | ${pct(counts.FORM_EXPLICIT)} |
| ORIGINAL_ONLY | ${counts.ORIGINAL_ONLY} | ${pct(counts.ORIGINAL_ONLY)} |
| COPY_ONLY | ${counts.COPY_ONLY} | ${pct(counts.COPY_ONLY)} |
| ORIGINAL_AND_COPY | ${counts.ORIGINAL_AND_COPY} | ${pct(counts.ORIGINAL_AND_COPY)} |
| ORIGINAL_PRESENT_COPY_SUBMIT | ${counts.ORIGINAL_PRESENT_COPY_SUBMIT} | ${pct(counts.ORIGINAL_PRESENT_COPY_SUBMIT)} |
| CERTIFIED_COPY | ${counts.CERTIFIED_COPY} | ${pct(counts.CERTIFIED_COPY)} |
| VARIES_BY_ITEM (composite entry, mixed markers) | ${counts.VARIES_BY_ITEM} | ${pct(counts.VARIES_BY_ITEM)} |
| SOURCE_DOES_NOT_SPECIFY | ${counts.SOURCE_DOES_NOT_SPECIFY} | ${pct(counts.SOURCE_DOES_NOT_SPECIFY)} |
| UNVERIFIED (phrase marker not confirmed on the anchored page) | ${counts.UNVERIFIED} | ${pct(counts.UNVERIFIED)} |
| basis: source phrase / regulation clause | ${counts.BASIS_SOURCE_PHRASE} / ${counts.BASIS_REGULATION} | |

Full document accuracy is **not** claimed: most rules are silent on physical form, and the 2026.9 manual text itself is still \`needs_review\`.

## Explicit forms (${explicitRows.length})

| Target | Procedure | Document | Form | Basis | Source |
| --- | --- | --- | --- | --- | --- |
${explicitRows.join('\n')}
`;
mkdirSync(join(ROOT, 'reports/data-coverage'), { recursive: true });
writeFileSync(join(ROOT, 'reports/data-coverage/document-physical-form-202609.md'), md);
writeFileSync(join(ROOT, 'reports/data-coverage/document-physical-form-202609.json'), JSON.stringify({ generated_from: 'data/status-guidance-202609.json', counts }, null, 1) + '\n');

console.log('[check_document_physical_form] coverage', JSON.stringify(counts));
if (failures.length) { console.error(`[check_document_physical_form] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_document_physical_form] OK — ${passed} checks passed over ${items.length} document rules`);
