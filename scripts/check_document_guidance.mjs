/*
 * check_document_guidance.mjs
 * ----------------------------------------------------------------------------
 * Document QA over every structured procedure in data/status-guidance-202609.json.
 *
 * For every displayed document it asserts that it
 *   - belongs to the correct procedure and status/substatus/path (entry-level target)
 *   - has a valid 2026.9 source reference (page inside the manual, near the section page)
 *   - has a requirement level from the enum and an applicant role
 *   - carries conditional logic when its level is conditional / applicable / alternative
 * and that
 *   - alternatives are grouped, never rendered as cumulative mandatory items
 *   - conditional documents never land in the required group
 *   - officer-discretion items are labelled as such and the officer note is shown once
 *   - source-only / partially structured checklists are never titled as the full list
 *   - common overlays apply only when their scope matches
 *   - the rendered checklist changes when resolver answers change
 *
 *   node scripts/check_document_guidance.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
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

const LEVELS = new Set(rules.enums.requirement_levels);
const ROLES = new Set(rules.enums.roles);
const CONDITIONAL_LEVELS = new Set(['CONDITIONAL_REQUIRED', 'ADDITIONAL_IF_APPLICABLE', 'ALTERNATIVE_DOCUMENT']);
const corpusPages = { stay_manual_2026_09_18: 810, visa_manual_2026_09_01: 519 };
let itemCount = 0;

for (const g of bundle.guidance) {
  const label = `${g.target}|${g.procedure}${g.scenario ? '#' + g.scenario : ''}`;
  const authored = rules.guidance.find((r) => r.target === g.target && r.procedure === g.procedure && (r.scenario || null) === (g.scenario || null));
  check(`${label}: checklist completeness is honest`, () => {
    if (g.completeness === 'FULLY_STRUCTURED') {
      assert(g.documents.length > 0, 'FULLY_STRUCTURED with no documents');
      assert(!g.documents.some((d) => d.requirement_level === 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED'), 'FULLY_STRUCTURED list contains unstructured source mentions');
    }
    if (g.documents.some((d) => d.requirement_level === 'SOURCE_MENTIONS_BUT_NOT_STRUCTURED')) assert(g.completeness !== 'FULLY_STRUCTURED', 'unstructured mention must downgrade completeness');
    if (['NOT_APPLICABLE', 'GENERALLY_NOT_PERMITTED', 'SOURCE_ONLY'].includes(g.state)) assert(!g.documents.some((d) => d.requirement_level === 'REQUIRED_BASELINE'), `${g.state} entry must not carry a required baseline list`);
  });
  const seenAlt = {};
  g.documents.forEach((d, i) => {
    itemCount += 1;
    const a = authored && authored.documents[i];
    check(`${label} doc[${i}] ${d.ref}`, () => {
      assert(a && a.ref === d.ref, 'compiled item does not match the authored rule (procedure/path drift)');
      assert(LEVELS.has(d.requirement_level), `requirement level ${d.requirement_level}`);
      assert(ROLES.has(d.applicant_role), `applicant role ${d.applicant_role}`);
      assert(d.name_ko && d.name_en, 'names');
      assert(d.source && Number.isInteger(d.source.pdf_page) && d.source.pdf_page >= 1 && d.source.pdf_page <= corpusPages[g.source.manual], 'no valid 2026.9 page');
      assert(Math.abs(d.source.pdf_page - g.source.pdf_page) <= 3, `item page ${d.source.pdf_page} far from section page ${g.source.pdf_page}`);
      assert(d.review_state === 'SEPT_2026_ORIGINAL_UNREVIEWED', 'review state must stay explicit');
      if (CONDITIONAL_LEVELS.has(d.requirement_level)) assert(d.applies_when_ko || d.does_not_apply_when_ko || d.alternatives_group, 'conditional document without conditional logic');
      if (d.requirement_level === 'REQUIRED_BASELINE') assert(!d.applies_when_ko, 'required baseline item carries an applies_when — should be conditional');
      if (d.alternatives_group) { seenAlt[d.alternatives_group] = (seenAlt[d.alternatives_group] || 0) + 1; assert(d.substitution_allowed === true, 'alternatives group without substitution flag'); assert(Array.isArray(d.alternatives) && d.alternatives.length >= 1 && d.alternatives.every((a) => a.ko && a.en), 'alternatives group needs at least one bilingual substitute'); }
      if (d.requirement_level === 'MAY_BE_REQUESTED_BY_OFFICER') assert(SG.groupDocuments(g).find((grp) => grp.key === 'officer').items.includes(d), 'officer item not in the officer group');
    });
  });
  check(`${label}: alternatives are one group each, not cumulative`, () => {
    for (const [grp, n] of Object.entries(seenAlt)) assert(n === 1, `alternatives group ${grp} appears ${n} times as separate mandatory items`);
    const groups = SG.groupDocuments(g);
    const required = groups.find((x) => x.key === 'required');
    if (required) for (const d of required.items) assert(!CONDITIONAL_LEVELS.has(d.requirement_level), `${d.ref} conditional rendered as required`);
  });
}

/* --------------------------------------------------- overlay scoping ---- */
check('overlays apply only when their scope matches', () => {
  const stayOnly = SG.applicableOverlays(bundle, 'F-1-5', 'extension', null).map((o) => o.id);
  assert(stayOnly.includes('must_be_in_korea') && stayOnly.includes('domestic_doc_validity_3m'), 'stay overlays missing');
  assert(!stayOnly.includes('occupation_income_report'), 'income report overlay leaked onto F-1 (not a work-eligible status)');
  const a1 = SG.applicableOverlays(bundle, 'A-1', 'extension', null).map((o) => o.id);
  assert(!a1.includes('tb_certificate') && !a1.includes('passport_validity_cap'), 'A-1 must be exempt from TB / passport-cap overlays');
  const e9 = SG.applicableOverlays(bundle, 'E-9-5', 'extension', null).map((o) => o.id);
  assert(e9.includes('occupation_income_report') && e9.includes('tb_certificate'), 'E-9 must carry income report + TB overlays');
  const visa = SG.applicableOverlays(bundle, 'D-2', 'visa_issuance', null).map((o) => o.id);
  assert(!visa.includes('must_be_in_korea') && !visa.includes('fees_non_refundable'), 'stay-only overlays leaked into the visa domain');
  const g1 = SG.applicableOverlays(bundle, 'G-1-5', 'extension', null).map((o) => o.id);
  assert(!g1.includes('passport_validity_cap'), 'G-1 exempt from passport cap');
  const withGuarantor = SG.applicableOverlays(bundle, 'F-1-13', 'extension', bundle.guidance.find((g) => g.target === 'F-1-13')).map((o) => o.id);
  assert(!withGuarantor.includes('guarantee_4y_cap'), 'guarantee cap must only show when a guarantee document is listed');
  const withG = SG.applicableOverlays(bundle, 'G-1-3', 'extension', bundle.guidance.find((g) => g.target === 'G-1-3')).map((o) => o.id);
  assert(withG.includes('guarantee_4y_cap'), 'guarantee cap missing where a guarantee is required');
  assert(!stayOnly.includes('officer_discretion'), 'officer discretion is rendered once as the persistent note, not as an overlay');
});

/* --------------------------------------- rendering follows the resolver ---- */
function render(query, answers, procedure) {
  const interp = SG.interpret(query, bundle);
  const state = { interp, answers: { ...answers }, procedure: procedure || null, status: null, history: [], lang: 'ko' };
  const step = SG.nextStep(state, bundle);
  const out = SG.renderModel(step, state, bundle);
  return { step, ...out };
}
check('document rendering changes when resolver answers change', () => {
  const a = render('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'first', f15_purpose: 'childcare' });
  const b = render('F-1 연장', { stay_reason: 'marriage_family', marriage_family_kind: 'marriage_migrant', f15_phase: 'subsequent', f15_purpose: 'childcare' });
  const c = render('F-1 연장', { stay_reason: 'student_parent' });
  assert(a.step.kind === 'resolved' && b.step.kind === 'resolved' && c.step.kind === 'resolved', 'paths must resolve');
  const names = (x) => x.model.documentGroups.flatMap((g) => g.items.map((d) => g.key + ':' + d.ref)).join(',');
  assert(names(a) !== names(b), 'first vs subsequent F-1-5 lists must differ (비취업서약서 only at first extension)');
  assert(names(a).includes('required:non_employment_pledge') && !names(b).includes('non_employment_pledge'), '비취업서약서 must appear only at the first extension');
  assert(names(b).includes('conditional:child_enrollment'), 'subsequent extension must add the conditional enrollment certificate');
  assert(names(c).includes('required:student_enrollment_proof') && !names(c).includes('non_employment_pledge'), 'F-1-13 list must be its own');
});
check('unresolved and parent-level states never render a definitive required list', () => {
  const u = render('F-1 연장', {});
  assert(u.step.kind === 'question', 'F-1 parent must ask first');
  assert(!u.html.includes('sg-doc-group-required'), 'no required list before the subtype is known');
  const unsure = render('F-1 연장', { stay_reason: 'unsure' });
  assert(unsure.step.kind === 'unresolved', 'unsure → unresolved');
  assert(!unsure.html.includes('준비할 서류'), 'unresolved state must not be titled as the full document list');
  const partial = render('F-2-7 연장', {});
  assert(partial.step.kind === 'resolved' && partial.model.completeness === 'PARTIALLY_STRUCTURED', 'F-2-7 is partially structured');
  assert(partial.html.includes('현재 확인된 기본 서류') && !partial.html.includes('>준비할 서류<'), 'partial checklist must use the partial title');
});
check('officer-discretion note is rendered once per checklist', () => {
  const r = render('E-9 호텔 연장', {});
  assert(r.step.kind === 'resolved', 'E-9 호텔 연장 resolves');
  const n = r.html.split('심사 과정에서 추가 서류가 요청되거나').length - 1;
  assert(n === 1, `officer note rendered ${n} times`);
  assert(r.html.includes('E-9-5'), 'E-9 호텔 must resolve to the service-industry subcode');
  assert(!r.html.includes('E-9-1'), 'manufacturing subcode must not appear in the hotel answer');
});
check('every document group key has a user-facing label in both languages', () => {
  for (const g of bundle.guidance) for (const grp of SG.groupDocuments(g)) { assert(SG.STR.ko[grp.labelKey] && SG.STR.en[grp.labelKey], `label ${grp.labelKey} missing`); }
  for (const lvl of rules.enums.requirement_levels) assert(!Object.values(SG.STR.ko).some((v) => typeof v === 'string' && v.includes(lvl)), `internal enum ${lvl} leaked into KO copy`);
});
check('every applicant role and place has a label in KO and EN', () => {
  for (const role of rules.enums.roles) assert(SG.STR.ko.roles[role] && SG.STR.en.roles[role], `role ${role}`);
  const places = new Set(rules.document_definitions.map((d) => d.where_to_obtain).filter(Boolean));
  for (const p of places) assert(SG.STR.ko.where_labels[p] && SG.STR.en.where_labels[p], `place ${p}`);
});

const structured = bundle.guidance.filter((g) => g.completeness === 'FULLY_STRUCTURED').length;
const partial = bundle.guidance.filter((g) => g.completeness === 'PARTIALLY_STRUCTURED').length;
const sourceOnly = bundle.guidance.filter((g) => g.completeness === 'SOURCE_ONLY').length;
console.log('[check_document_guidance] document QA report', JSON.stringify({ guidance_entries: bundle.guidance.length, document_items: itemCount, fully_structured_procedures: structured, partially_structured_procedures: partial, source_only_procedures: sourceOnly }));
if (failures.length) { console.error(`[check_document_guidance] FAIL — ${failures.length} failure(s), ${passed} passed`); for (const f of failures) console.error('  - ' + f); process.exit(1); }
console.log(`[check_document_guidance] OK — ${passed} checks passed over ${itemCount} document items`);
