import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const helper = require('../assets/js/document-help.js');
const records = JSON.parse(fs.readFileSync(new URL('../data/document_help.json', import.meta.url), 'utf8'));
const indexHtml = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');

const requiredIds = [
  'integrated_application_form',
  'identity_guarantee_form',
  'residence_proof',
  'accommodation_provision_confirmation',
  'family_relationship_evidence',
  'guardian_proxy_guidance'
];

assert.ok(Array.isArray(records), 'document_help.json must be an array');
assert.deepEqual(requiredIds.filter(id => !records.some(record => record.id === id)), [], 'all first-release records must exist');

for (const record of records) {
  assert.ok(record.titleKo && record.titleEn, `${record.id}: bilingual titles are required`);
  assert.ok(record.summaryKo && record.summaryEn, `${record.id}: bilingual summaries are required`);
  assert.ok(Array.isArray(record.sourceRefs) && record.sourceRefs.length > 0, `${record.id}: sourceRefs are required`);
  assert.ok(record.sourceRefs.every(ref => /^https:\/\//.test(ref.url) && ref.checkedAt), `${record.id}: sources need safe official URLs and checkedAt`);
}

const matcher = helper.createMatcher(records);
const cases = [
  ['통합신청서 (별지 제34호 서식)', 'integrated_application_form'],
  ['  통합신청서(신고서)  ', 'integrated_application_form'],
  ['doc_unified_application_form_change', 'integrated_application_form'],
  ['신원보증서 (보증기간 명시)', 'identity_guarantee_form'],
  ['체류지 입증서류(임대차계약서, 숙소제공 확인서 등)', 'residence_proof'],
  ['주소지 입증 서류', 'residence_proof'],
  ['거주/숙소제공확인서', 'accommodation_provision_confirmation'],
  ['숙소 제공 확인서 및 제공자 신분증 사본', 'accommodation_provision_confirmation'],
  ['출생증명서 등 가족관계 입증서류', 'family_relationship_evidence'],
  ['혼인관계증명서 (상세)', 'family_relationship_evidence'],
  ['대리인 신청 시 위임장·대리인 신분증', 'guardian_proxy_guidance'],
  ['가족관계·보호자 입증서류', 'guardian_proxy_guidance']
];

for (const [label, expected] of cases) {
  assert.equal(matcher.find(label)?.id, expected, `alias match failed: ${label}`);
}
assert.equal(matcher.find('여권 원본 및 사본'), null, 'unknown documents must not crash or receive an unrelated guide');

const integrated = matcher.find('통합신청서');
const renderedKo = helper.renderPanel(integrated, 'ko');
const renderedEn = helper.renderPanel(integrated, 'en');
assert.match(renderedKo, /공식 출처/);
assert.match(renderedKo, /target="_blank" rel="noopener noreferrer"/);
assert.match(renderedEn, /Official sources/);
assert.equal(helper.ui('fr').open, '이 서류가 뭔가요?', 'unsupported locales must safely fall back to Korean');

for (const marker of [
  'id="documentHelpOverlay"',
  'loadDocumentHelp();',
  'renderDocumentHelpButton(key, officialName)',
  'renderDocumentHelpButton(rawText, text)',
  'renderDocumentHelpButton(rawName, rawName)',
  'renderDocumentHelpButton(label, label)'
]) {
  assert.ok(indexHtml.includes(marker), `index integration marker missing: ${marker}`);
}

console.log(`Document help checks passed (${records.length} records, ${cases.length} alias cases).`);
