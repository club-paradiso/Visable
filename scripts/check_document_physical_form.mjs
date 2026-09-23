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
const run = (q, answers = {}, lang = 'ko') => { const interp = SG.interpret(q, bundle); const state = { interp, answers, procedure: null, status: null, history: [], lang }; const step = SG.nextStep(state, bundle); return SG.renderModel(step, state, bundle).html; };
check('formLabel: explicit forms get a label; "원본" alone never claims presentation or surrender', () => {
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_AND_COPY', copy_count: 1 }) === '원본 + 사본 1부', 'ORIGINAL_AND_COPY label');
  assert(SG.formLabel('ko', { submission_form: 'COPY_ONLY' }) === '사본', 'COPY_ONLY label');
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_ONLY' }) === '원본', 'bare original stays bare');
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_ONLY', original_returned: true }) === '원본 제시 · 돌려받음', 'returned original = presentation');
  assert(SG.formLabel('ko', { submission_form: 'ORIGINAL_ONLY', original_returned: false }) === '원본 제출 · 반환되지 않음', 'kept original = surrender');
  assert(SG.formLabel('en', { submission_form: 'ORIGINAL_ONLY', original_returned: false }) === 'Original submitted · not returned', 'EN surrender');
  assert(SG.formLabel('en', { submission_form: 'ORIGINAL_ONLY', original_returned: true }) === 'Original shown · returned to you', 'EN presentation');
  assert(SG.formLabel('ko', { submission_form: 'SOURCE_DOES_NOT_SPECIFY' }) === '' && SG.formLabel('ko', {}) === '', 'no default label');
});
check('preparation policy: official-explicit vs preparation-recommendation vs not-applicable, source beats heuristic', () => {
  const p = (d) => SG.preparation(d);
  // silent passport → recommendation, possession-sensitive: bring + copy, never "submit original"
  const passport = p({ ref: 'passport', name_ko: '여권', submission_form: 'SOURCE_DOES_NOT_SPECIFY' });
  assert(passport.kind === 'PREPARATION_RECOMMENDATION' && passport.policy === 'KEEP_ORIGINAL', JSON.stringify(passport));
  assert(SG.preparationLabel('ko', { ref: 'passport', name_ko: '여권', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }) === '원본 지참 · 사본 준비', 'passport label');
  assert(SG.preparationLabel('en', { ref: 'passport', name_ko: '여권', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }) === 'Bring the original · prepare a copy', 'passport EN label');
  // silent contract / lease → possession-sensitive
  for (const d of [{ ref: 'employment_contract', name_ko: '고용계약서' }, { ref: 'lease', name_ko: '임대차계약서' }, { ref: 'residence_proof', name_ko: '체류지 입증서류' }]) {
    const r = p(Object.assign({ submission_form: 'SOURCE_DOES_NOT_SPECIFY' }, d));
    assert(r.kind === 'PREPARATION_RECOMMENDATION', `${d.ref} recommendation`);
    assert(!/제출/.test(SG.preparationLabel('ko', Object.assign({ submission_form: 'SOURCE_DOES_NOT_SPECIFY' }, d))), `${d.ref}: never "제출" for a silent original`);
  }
  assert(p({ ref: 'employment_contract', name_ko: '고용계약서', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }).policy === 'KEEP_ORIGINAL', 'contract keeps the original');
  assert(p({ ref: 'residence_proof', name_ko: '체류지 입증서류', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }).policy === 'BRING_ORIGINAL', 'generic residence proof (utility bill etc.) is a plain bring-original recommendation');
  // silent generic certificate → bring original (copy optional)
  const cert = p({ ref: 'marriage_cert', name_ko: '혼인관계증명서(상세)', submission_form: 'SOURCE_DOES_NOT_SPECIFY' });
  assert(cert.kind === 'PREPARATION_RECOMMENDATION' && cert.policy === 'BRING_ORIGINAL', 'certificate → bring original');
  // forms, fees and photos carry no physical-form advice
  assert(p({ ref: 'app_form_34', name_ko: '통합신청서 (별지 제34호 서식)', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }).kind === 'NOT_APPLICABLE', 'application form');
  assert(p({ ref: 'fee', name_ko: '수수료', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }).kind === 'NOT_APPLICABLE', 'fee');
  assert(p({ ref: 'photo_reissue', name_ko: '사진 1장', submission_form: 'SOURCE_DOES_NOT_SPECIFY' }).kind === 'NOT_APPLICABLE', 'photo');
  // explicit source wins even for possession-sensitive classes
  const explicit = p({ ref: 'contract_original_copy', name_ko: '고용계약서 원본 및 사본', submission_form: 'ORIGINAL_AND_COPY', form_basis: 'SOURCE_PHRASE' });
  assert(explicit.kind === 'OFFICIAL_EXPLICIT' && explicit.form === 'ORIGINAL_AND_COPY', 'explicit contract form kept');
  const kept = p({ ref: 'arc_existing_original', name_ko: '원래의 외국인등록증', submission_form: 'ORIGINAL_ONLY', form_basis: 'REGULATION', original_returned: false });
  assert(kept.kind === 'OFFICIAL_EXPLICIT' && kept.returnKnown === true, 'regulation-backed surrender is explicit');
});
check('renderer: explicit rows carry official labels, silent rows carry dashed advice, forms/fees carry nothing, one section note', () => {
  const d2 = run('D-2 외국인등록'); assert(d2.includes('data-sg-form-kind="OFFICIAL_EXPLICIT">원본 + 사본 1부<'), 'D-2 registration passport shows 원본 + 사본 1부 as official');
  const f6 = run('F-6-1 연장', { f61_phase: 'normal' });
  assert(f6.includes('sg-doc-form sg-doc-form-rec" data-sg-form-kind="PREPARATION_RECOMMENDATION">원본 지참 · 사본 준비<'), 'F-6-1 passport row: dashed keep-original advice');
  assert(/통합신청서 \(별지 제34호 서식\)<\/span>(?:<span class="sg-doc-ko"[^>]*>[^<]*<\/span>)?(?:<span class="sg-doc-tag">)?/.test(f6) && !/통합신청서 \(별지 제34호 서식\)<\/span><span class="sg-doc-form/.test(f6), 'application form row carries no physical-form tag');
  assert((f6.match(/sg-doc-prep-note/g) || []).length === 1, 'exactly one section-level preparation note');
  assert(f6.includes('준비 권장 · 공식 표기 없음'), 'recommendation basis is labelled as advice in the details');
  assert(!/지참하면 안전해요|원문에 원본·사본 표기가 없어요/.test(f6), 'the weak fallback sentence is gone');
  const e9 = run('E-9-1 연장'); assert(e9.includes('data-sg-form-kind="OFFICIAL_EXPLICIT">사본<'), 'E-9 copies labelled as official');
  const addr = run('주소 변경 신고'); assert(addr.includes('원본 제시 · 돌려받음'), 'address report: card is shown and returned (Act 36(2))');
  const reissue = run('외국인등록증 재발급', { reissue_reason: 'damaged' }); assert(reissue.includes('원본 제출 · 반환되지 않음'), 'card reissue: existing card is handed in and destroyed (Decree 42)');
  const en = run('F-6-1 연장', { f61_phase: 'normal' }, 'en'); assert(en.includes('Bring the original · prepare a copy') && en.includes('preparation advice · not stated in the source'), 'EN advice');
  // a silent contract row never renders as "원본 제출"
  const e7 = run('E-7 연장'); const contractRow = e7.split('고용계약서')[1] || ''; assert(!/원본 제출/.test(contractRow.split('</li>')[0]), 'E-7 silent contract: no surrender wording');
});
check('source: the weak wording is gone from every renderer and the Quick Answer', () => {
  const files = ['assets/js/status-guidance.js', 'assets/js/waymaker-quick-answer.js', 'lib/waymaker-quick-answer-ai.js'];
  for (const f of files) { const src = readFileSync(join(ROOT, f), 'utf8'); assert(!/지참하면 안전해요|원문에 원본·사본 표기가 없어요|관서 확인\)/.test(src), `${f} still carries the weak wording`); }
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
