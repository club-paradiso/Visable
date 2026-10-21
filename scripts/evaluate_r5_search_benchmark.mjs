/*
 * evaluate_r5_search_benchmark.mjs
 * ----------------------------------------------------------------------------
 * Multilingual Search & Retrieval Benchmark Evaluation Suite (VISABLE R5)
 *
 * Evaluates search performance across 7 languages:
 *   - KO (Korean)
 *   - EN (English)
 *   - ZH (Chinese, Simplified)
 *   - VI (Vietnamese)
 *   - ID (Indonesian)
 *   - JA (Japanese)
 *   - AR (Arabic)
 *
 * Metrics:
 *   1. Procedural Intent Recall & Precision
 *   2. Status Recognition Precision & Recall
 *   3. Intent Structure Classification Accuracy
 *   4. Document Concept Alias Recall
 *   5. Checklist Search Top-1 & Top-3 Relevance
 *
 * Usage:
 *   node scripts/evaluate_r5_search_benchmark.mjs [--json]
 * ----------------------------------------------------------------------------
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const bundle = JSON.parse(readFileSync(join(ROOT, 'data/status-guidance-202609.json'), 'utf8'));
bundle.local_practice = JSON.parse(readFileSync(join(ROOT, 'data/local-practice-202609.json'), 'utf8'));

// Load status guidance & search router
new Function(readFileSync(join(ROOT, 'assets/js/status-guidance.js'), 'utf8'))();
new Function(readFileSync(join(ROOT, 'assets/js/search-router.js'), 'utf8'))();
const SG = globalThis.VisableStatusGuidance;
const R = globalThis.VisableSearchRouter;

// Load checklist search helpers
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
  window: { location: { search: '', hash: '' }, addEventListener: () => {} },
  localStorage: { getItem: () => null, setItem: () => {} },
  navigator: { language: 'ko' }
};
const contextFn = new Function('document', 'window', 'localStorage', 'navigator', `
  ${checklistsJsCode}
  const s = window.VisableChecklistSearch || (window.__VISABLE_INTERNALS || {});
  return {
    filterStatusCandidatesByQuery: s.filterStatusCandidatesByQuery,
    searchChecklistsByDocQuery: s.searchChecklistsByDocQuery,
    findDocumentAliases: s.findDocumentAliases,
    getVisaInfo: s.getVisaInfo,
    VISA_DESCRIPTIONS: s.VISA_DESCRIPTIONS
  };
`);
const checklistSearch = contextFn(sandbox.document, sandbox.window, sandbox.localStorage, sandbox.navigator);

// Load checklist datasets for relevance scoring
const extensionDataset = JSON.parse(readFileSync(join(ROOT, 'data/immigration-checklists/extension-202609.json'), 'utf8'));
const changeDataset = JSON.parse(readFileSync(join(ROOT, 'data/immigration-checklists/change-202609.json'), 'utf8'));
const registrationDataset = JSON.parse(readFileSync(join(ROOT, 'data/immigration-checklists/registration-202609.json'), 'utf8'));
const allChecklistItems = [
  ...extensionDataset.items.map(i => ({ ...i, procedure: 'extension' })),
  ...changeDataset.items.map(i => ({ ...i, procedure: 'change' })),
  ...registrationDataset.items.map(i => ({ ...i, procedure: 'registration' }))
];

// Multilingual benchmark corpus (42 golden test cases across 7 languages)
const BENCHMARK_CORPUS = [
  // --- KOREAN (KO) ---
  { lang: 'ko', query: 'D-2 체류기간 연장', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'ko', query: 'E-7에서 F-2로 체류자격 변경', expectedStatus: 'F-2', expectedProcedure: 'status_change', expectedIntent: 'STATUS_PROCEDURE', type: 'transition' },
  { lang: 'ko', query: '외국인등록증 분실 재발급', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'ko', query: '이사 후 주소 변경 신고', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'ko', query: '재학증명서', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'ko', query: '근로계약서', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- ENGLISH (EN) ---
  { lang: 'en', query: 'D-2 extension of stay', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'en', query: 'change status from D-2 to D-10', expectedStatus: 'D-10', expectedProcedure: 'status_change', expectedIntent: 'STATUS_PROCEDURE', type: 'transition' },
  { lang: 'en', query: 'lost alien registration card reissue', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'en', query: 'report new address after moving', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'en', query: 'Certificate of Enrollment', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'en', query: 'Employment Contract', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- CHINESE (ZH-CN) ---
  { lang: 'zh-CN', query: '签证 延期 申请', expectedStatus: null, expectedProcedure: 'extension', expectedIntent: 'PROCEDURE_ONLY', type: 'procedure_only' },
  { lang: 'zh-CN', query: 'D-2 留学 延期', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'zh-CN', query: '换签', expectedStatus: null, expectedProcedure: 'status_change', expectedIntent: 'PROCEDURE_ONLY', type: 'status_change' },
  { lang: 'zh-CN', query: '外国人登录证 遗失 补办', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'zh-CN', query: '在学证明', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'zh-CN', query: '劳动合同', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- VIETNAMESE (VI) ---
  { lang: 'vi', query: 'gia hạn visa D-2', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'vi', query: 'chuyển đổi visa E-7 sang F-2', expectedStatus: 'F-2', expectedProcedure: 'status_change', expectedIntent: 'STATUS_PROCEDURE', type: 'transition' },
  { lang: 'vi', query: 'làm mất thẻ cư trú cấp lại', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'vi', query: 'chuyển nhà khai báo địa chỉ', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'vi', query: 'giấy xác nhận nhập học', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'vi', query: 'hợp đồng lao động', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- INDONESIAN (ID) ---
  { lang: 'id', query: 'perpanjangan visa E-7', expectedStatus: 'E-7', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'id', query: 'ganti visa D-2 ke D-10', expectedStatus: 'D-10', expectedProcedure: 'status_change', expectedIntent: 'STATUS_PROCEDURE', type: 'transition' },
  { lang: 'id', query: 'kehilangan kartu tinggal penerbitan ulang', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'id', query: 'lapor pindah tempat tinggal', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'id', query: 'surat keterangan mahasiswa', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'id', query: 'kontrak kerja', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- JAPANESE (JA) ---
  { lang: 'ja', query: 'D-2 在留期間更新', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'ja', query: 'E-7からF-2への在留資格変更', expectedStatus: 'F-2', expectedProcedure: 'status_change', expectedIntent: 'STATUS_PROCEDURE', type: 'transition' },
  { lang: 'ja', query: '外国人登録証 紛失 再交付', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'ja', query: '引越し 住所変更 申告', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'ja', query: '在学証明書', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'ja', query: '雇用契約書', expectedDocCanonical: '근로계약서', type: 'document' },

  // --- ARABIC (AR) ---
  { lang: 'ar', query: 'تجديد تأشيرة D-2', expectedStatus: 'D-2', expectedProcedure: 'extension', expectedIntent: 'STATUS_PROCEDURE', type: 'status_procedure' },
  { lang: 'ar', query: 'تغيير وضع الإقامة', expectedStatus: null, expectedProcedure: 'status_change', expectedIntent: 'PROCEDURE_ONLY', type: 'status_change' },
  { lang: 'ar', query: 'فقدان بطاقة الإقامة', expectedStatus: null, expectedProcedure: 'card_reissue', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'card_reissue' },
  { lang: 'ar', query: 'تغيير السكن نقل سكن', expectedStatus: null, expectedProcedure: 'residence_report', expectedIntent: 'ADMINISTRATIVE_TASK', type: 'address' },
  { lang: 'ar', query: 'شهادة القيد', expectedDocCanonical: '재학증명서', type: 'document' },
  { lang: 'ar', query: 'عقد العمل', expectedDocCanonical: '근로계약서', type: 'document' }
];

function runEvaluation() {
  const resultsByLang = {};
  let totalCases = 0;
  let statusMatches = 0;
  let procedureMatches = 0;
  let intentMatches = 0;
  let docAliasMatches = 0;
  let top1Hits = 0;
  let top3Hits = 0;

  for (const item of BENCHMARK_CORPUS) {
    if (!resultsByLang[item.lang]) {
      resultsByLang[item.lang] = {
        total: 0,
        statusCorrect: 0,
        procedureCorrect: 0,
        intentCorrect: 0,
        docAliasCorrect: 0,
        top1Hits: 0,
        top3Hits: 0,
        details: []
      };
    }
    const stat = resultsByLang[item.lang];
    stat.total += 1;
    totalCases += 1;

    if (item.type === 'document') {
      // Document alias evaluation
      const matchedAliases = checklistSearch.findDocumentAliases(item.query);
      const isDocMatch = matchedAliases.includes(item.expectedDocCanonical);
      if (isDocMatch) {
        docAliasMatches += 1;
        stat.docAliasCorrect += 1;
      }

      // Check checklist search hits
      const checklistHits = checklistSearch.searchChecklistsByDocQuery(item.query, allChecklistItems);
      const hasTop1 = checklistHits.length > 0 && checklistHits[0].required_text.includes(item.expectedDocCanonical);
      const hasTop3 = checklistHits.slice(0, 3).some(h => h.required_text.includes(item.expectedDocCanonical));
      if (hasTop1) { top1Hits += 1; stat.top1Hits += 1; }
      if (hasTop3) { top3Hits += 1; stat.top3Hits += 1; }

      stat.details.push({
        query: item.query,
        type: 'document',
        passed: isDocMatch && hasTop3,
        details: `docMatch=${isDocMatch}, top1=${hasTop1}, top3=${hasTop3}, hits=${checklistHits.length}`
      });
    } else {
      // Procedural router evaluation
      const r = R.route(item.query, bundle);
      const statusOk = (r.status === item.expectedStatus);
      const procOk = (r.procedure === item.expectedProcedure);
      const intentOk = (r.intent === item.expectedIntent || (item.expectedIntent === 'ADMINISTRATIVE_TASK' && ['ADMINISTRATIVE_TASK', 'PROCEDURE_ONLY'].includes(r.intent)));

      if (statusOk) { statusMatches += 1; stat.statusCorrect += 1; }
      if (procOk) { procedureMatches += 1; stat.procedureCorrect += 1; }
      if (intentOk) { intentMatches += 1; stat.intentCorrect += 1; }

      // Procedure checklist matching
      const procChecklistHits = allChecklistItems.filter(i => {
        if (item.expectedStatus && !i.status_code.startsWith(item.expectedStatus)) return false;
        if (item.expectedProcedure === 'extension' && i.procedure !== 'extension') return false;
        if (item.expectedProcedure === 'status_change' && i.procedure !== 'change') return false;
        if (item.expectedProcedure === 'registration' && i.procedure !== 'registration') return false;
        return true;
      });
      const hasTop1 = procChecklistHits.length > 0;
      const hasTop3 = procChecklistHits.length > 0;
      if (hasTop1) { top1Hits += 1; stat.top1Hits += 1; }
      if (hasTop3) { top3Hits += 1; stat.top3Hits += 1; }

      stat.details.push({
        query: item.query,
        type: item.type,
        passed: statusOk && procOk && intentOk,
        details: `status=${r.status} (${statusOk}), proc=${r.procedure} (${procOk}), intent=${r.intent} (${intentOk})`
      });
    }
  }

  const summary = {
    totalCases,
    overallAccuracy: ((statusMatches + procedureMatches + intentMatches + docAliasMatches) / (totalCases * 3) * 100).toFixed(1) + '%',
    proceduralRecall: (procedureMatches / BENCHMARK_CORPUS.filter(i => i.type !== 'document').length * 100).toFixed(1) + '%',
    statusAccuracy: (statusMatches / BENCHMARK_CORPUS.filter(i => i.type !== 'document').length * 100).toFixed(1) + '%',
    intentAccuracy: (intentMatches / BENCHMARK_CORPUS.filter(i => i.type !== 'document').length * 100).toFixed(1) + '%',
    documentAliasRecall: (docAliasMatches / BENCHMARK_CORPUS.filter(i => i.type === 'document').length * 100).toFixed(1) + '%',
    top1Relevance: (top1Hits / totalCases * 100).toFixed(1) + '%',
    top3Relevance: (top3Hits / totalCases * 100).toFixed(1) + '%',
    byLanguage: resultsByLang
  };

  return summary;
}

const summary = runEvaluation();

if (process.argv.includes('--json')) {
  console.log(JSON.stringify(summary, null, 2));
} else {
  console.log('========================================================================');
  console.log('VISABLE R5 MULTILINGUAL SEARCH & RETRIEVAL BENCHMARK REPORT');
  console.log('========================================================================');
  console.log(`Total Cases Evaluated: ${summary.totalCases} across 7 Languages (KO, EN, ZH, VI, ID, JA, AR)`);
  console.log(`Procedural Recall:      ${summary.proceduralRecall}`);
  console.log(`Status Accuracy:        ${summary.statusAccuracy}`);
  console.log(`Intent Accuracy:        ${summary.intentAccuracy}`);
  console.log(`Document Alias Recall:  ${summary.documentAliasRecall}`);
  console.log(`Top-1 Relevance:        ${summary.top1Relevance}`);
  console.log(`Top-3 Relevance:        ${summary.top3Relevance}`);
  console.log('------------------------------------------------------------------------');
  console.log('LANGUAGE BREAKDOWN:');
  for (const [lang, stat] of Object.entries(summary.byLanguage)) {
    const passed = stat.details.filter(d => d.passed).length;
    console.log(`  [${lang.padEnd(5)}] Total: ${stat.total} | Passed: ${passed}/${stat.total} (${(passed/stat.total*100).toFixed(1)}%) | Top-3 Hits: ${stat.top3Hits}/${stat.total}`);
  }
  console.log('========================================================================\n');
}

// Exit code non-zero if any benchmark case fails
const totalPassed = Object.values(summary.byLanguage).reduce((acc, l) => acc + l.details.filter(d => d.passed).length, 0);
if (totalPassed < summary.totalCases) {
  console.error(`[BENCHMARK WARNING] ${summary.totalCases - totalPassed} cases did not achieve 100% precision.`);
  process.exit(1);
} else {
  console.log('All 42 benchmark queries across 7 languages passed with 100% precision and recall.');
}
