/*
 * check_r5_review_findings.mjs
 * ----------------------------------------------------------------------------
 * Reproduction & regression tests for the 4 unresolved PR #669 review findings:
 *   - P1-01: Multilingual procedural intent recognition (search-router.js)
 *   - P1-02: Localized visa-name search (immigration-checklists.js)
 *   - P1-03: Arabic search support (search-router.js)
 *   - P2-04: Localized document-name search (immigration-checklists.js)
 *
 * Usage:
 *   node scripts/check_r5_review_findings.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));

// Load status guidance and search router
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;
const R = globalThis.VisableSearchRouter;

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`[PASS] ${name}`);
  } catch (e) {
    failures.push(`${name}: ${e.message}`);
    console.error(`[FAIL] ${name}: ${e.message}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'Assertion failed');
}

console.log('--- Testing P1-01: Multilingual Procedural Intent Recognition ---');

check('P1-01.1: 签证 延期 申请 (Chinese) routes to extension', () => {
  const r = R.route('签证 延期 申请', bundle);
  assert(r.procedure === 'extension', `expected procedure 'extension', got '${r.procedure}'`);
  assert(r.actions && r.actions.extend, 'expected action.extend to be detected');
  assert(['PROCEDURE_ONLY', 'ADMINISTRATIVE_TASK'].includes(r.structure), `unexpected structure '${r.structure}'`);
});

check('P1-01.2: gia hạn visa D-2 (Vietnamese) routes to STATUS_PROCEDURE (D-2 + extension)', () => {
  const r = R.route('gia hạn visa D-2', bundle);
  assert(r.status === 'D-2', `expected status D-2, got '${r.status}'`);
  assert(r.procedure === 'extension', `expected procedure 'extension', got '${r.procedure}'`);
  assert(r.structure === 'STATUS_PROCEDURE', `expected structure STATUS_PROCEDURE, got '${r.structure}'`);
});

check('P1-01.3: perpanjangan visa E-7 (Indonesian) routes to STATUS_PROCEDURE (E-7 + extension)', () => {
  const r = R.route('perpanjangan visa E-7', bundle);
  assert(r.status === 'E-7', `expected status E-7, got '${r.status}'`);
  assert(r.procedure === 'extension', `expected procedure 'extension', got '${r.procedure}'`);
  assert(r.structure === 'STATUS_PROCEDURE', `expected structure STATUS_PROCEDURE, got '${r.structure}'`);
});

check('P1-01.4: 换签 / chuyển đổi visa / ganti visa routes to status_change', () => {
  for (const q of ['换签', 'chuyển đổi visa', 'ganti visa']) {
    const r = R.route(q, bundle);
    assert(r.procedure === 'status_change', `${q}: expected status_change, got '${r.procedure}'`);
  }
});

console.log('--- Testing P1-03: Arabic Search Support ---');

check('P1-03.1: فقدان بطاقة الإقامة routes to card_reissue with lost condition', () => {
  const r = R.route('فقدان بطاقة الإقامة', bundle);
  assert(r.objects && r.objects.card, 'expected object.card for بطاقة الإقامة');
  assert(r.actions && r.actions.reissue, 'expected action.reissue for فقدان');
  assert(r.procedure === 'card_reissue', `expected procedure 'card_reissue', got '${r.procedure}'`);
  assert(r.conditions && r.conditions.reissue_reason === 'lost', `expected condition.reissue_reason 'lost', got '${r.conditions && r.conditions.reissue_reason}'`);
});

check('P1-03.2: تجديد تأشيرة الإقامة routes to extension', () => {
  const r = R.route('تجديد تأشيرة الإقامة', bundle);
  assert(r.actions && r.actions.extend, 'expected action.extend for تجديد');
  assert(r.procedure === 'extension', `expected procedure 'extension', got '${r.procedure}'`);
});

check('P1-03.3: تغيير وضع الإقامة routes to status_change', () => {
  const r = R.route('تغيير وضع الإقامة', bundle);
  assert(r.actions && r.actions.change, 'expected action.change for تغيير');
  assert(r.procedure === 'status_change', `expected procedure 'status_change', got '${r.procedure}'`);
});

console.log('--- Testing P1-02 & P2-04: Localized Visa & Document Search in Checklists ---');

// Mock browser environment for immigration-checklists.js
const checklistsJsCode = readFileSync(join(ROOT, 'assets/js/immigration-checklists.js'), 'utf8');

const makeMockElement = () => ({
  addEventListener: () => {},
  querySelectorAll: () => [],
  style: {},
  replaceChildren: () => {},
  appendChild: () => {},
  setAttribute: () => {},
  classList: { add: () => {}, remove: () => {} },
  textContent: ''
});
const sandbox = {
  document: {
    getElementById: () => makeMockElement(),
    querySelector: () => makeMockElement(),
    querySelectorAll: () => [],
    addEventListener: () => {},
    createElement: () => makeMockElement()
  },
  window: {
    location: { search: '', hash: '' },
    addEventListener: () => {}
  },
  localStorage: { getItem: () => null, setItem: () => {} },
  navigator: { language: 'ko' }
};

const contextFn = new Function('document', 'window', 'localStorage', 'navigator', `
  ${checklistsJsCode}
  const s = window.VisableChecklistSearch || (window.__VISABLE_INTERNALS || {});
  return {
    filterStatusCandidatesByQuery: typeof filterStatusCandidatesByQuery === 'function' ? filterStatusCandidatesByQuery : s.filterStatusCandidatesByQuery,
    searchChecklistsByDocQuery: typeof searchChecklistsByDocQuery === 'function' ? searchChecklistsByDocQuery : s.searchChecklistsByDocQuery,
    VISA_DESCRIPTIONS: typeof VISA_DESCRIPTIONS !== 'undefined' ? VISA_DESCRIPTIONS : s.VISA_DESCRIPTIONS,
    getVisaInfo: typeof getVisaInfo === 'function' ? getVisaInfo : s.getVisaInfo,
    findDocumentAliases: typeof findDocumentAliases === 'function' ? findDocumentAliases : s.findDocumentAliases
  };
`);

const checklistExports = contextFn(sandbox.document, sandbox.window, sandbox.localStorage, sandbox.navigator);

check('P1-02: Searching localized visa aliases (留学, du học) matches D-2', () => {
  assert(checklistExports.getVisaInfo, 'getVisaInfo function must exist');
  // Load visa-names authoritative data
  const visaNamesData = JSON.parse(readFileSync(join(ROOT, 'data/i18n/visa-names.json'), 'utf8'));
  assert(visaNamesData.names['D-2'], 'visa-names must contain D-2');
  
  // Test whether getVisaInfo or candidate search integrates localized names
  const d2InfoZh = checklistExports.getVisaInfo('D-2', 'zh-CN');
  assert(d2InfoZh.localized_name === '留学' || d2InfoZh.zh === '留学', `expected localized_name for D-2 in zh-CN to be '留学', got '${d2InfoZh.localized_name}'`);

  const d2InfoVi = checklistExports.getVisaInfo('D-2', 'vi');
  assert(d2InfoVi.localized_name === 'Du học' || d2InfoVi.vi === 'Du học', `expected localized_name for D-2 in vi to be 'Du học', got '${d2InfoVi.localized_name}'`);
});

check('P2-04: Localized document aliases resolve to canonical Korean concepts', () => {
  assert(checklistExports.findDocumentAliases, 'findDocumentAliases function must exist');
  const enrollmentDocs = checklistExports.findDocumentAliases('Certificate of Enrollment');
  assert(Array.isArray(enrollmentDocs) && enrollmentDocs.some(d => d.includes('재학')), 'Certificate of Enrollment must map to 재학증명서');

  const contractDocs = checklistExports.findDocumentAliases('Employment Contract');
  assert(Array.isArray(contractDocs) && contractDocs.some(d => d.includes('근로계약') || d.includes('고용계약')), 'Employment Contract must map to 근로계약서');

  const residenceDocs = checklistExports.findDocumentAliases('Proof of Residence');
  assert(Array.isArray(residenceDocs) && residenceDocs.some(d => d.includes('체류지') || d.includes('임대차')), 'Proof of Residence must map to 체류지 입증서류');
});

console.log('\n============================================================');
console.log(`Results: ${passed} passed, ${failures.length} failed`);
if (failures.length > 0) {
  console.log('\nFailures:');
  failures.forEach(f => console.log('  - ' + f));
}
console.log('============================================================');

process.exit(failures.length > 0 ? 1 : 0);
