#!/usr/bin/env node
/*
 * All-status procedure journey audit.
 *
 * This is a read-only auditing harness. It scans every visa/status record in
 * visa_data.json (cross-checked against backend/data/visas.json) and reports,
 * for each of the user-facing procedure tabs, whether the underlying data is
 * good enough to drive a reliable user journey.
 *
 * It does NOT modify any production data. It only reads the data files,
 * computes a per-status procedure matrix, raises risk flags, and writes a
 * machine-readable JSON report plus a human-readable Markdown report.
 *
 * The audit intentionally does not fail on data-quality warnings. Existing
 * data-quality issues are surfaced as warnings; the companion test harness
 * (scripts/check_procedure_journey_audit.js) is what fails CI when a newly
 * added invariant expectation is broken.
 *
 * Usage:
 *   node scripts/audit_procedure_journeys.js            # run + write reports
 *   node scripts/audit_procedure_journeys.js --no-write # run, skip report files
 *   node scripts/audit_procedure_journeys.js --quiet    # compute only, no stdout
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const VISA_DATA = path.join(ROOT, 'visa_data.json');
const BACKEND_VISAS = path.join(ROOT, 'backend', 'data', 'visas.json');
const INDEX_HTML = path.join(ROOT, 'index.html');
const JSON_REPORT = path.join(ROOT, 'docs', 'data', 'procedure_journey_audit_2026_06.json');
const MD_REPORT = path.join(ROOT, 'docs', 'data', 'PROCEDURE_JOURNEY_AUDIT_2026_06.md');

// Procedure tabs the audit walks, in user-facing order.
const PROCEDURE_KEYS = [
  'visaIssuance',
  'registration',
  'extension',
  'statusChange',
  'activitiesOutsideStatus',
  'workplaceChange',
  'statusGrant',
  'reentry',
];

// Statuses the audit must surface clearly. These are NOT fixed here; they are
// only highlighted so reviewers can scan them quickly.
const PRIORITY_STATUSES = [
  'D-2', 'D-4', 'C-3', 'H-1', 'H-2', 'G-1', 'G-1-5',
  'F-4', 'F-6', 'E-7', 'D-10', 'F-2', 'F-5', 'E-9',
];

// Placeholder text that should never reach a user-facing card.
const PLACEHOLDER_TOKENS = ['문서명 미상', '비고 정보 없음', 'DATA_MISSING'];

// Raw pipeline diagnostics that should never appear in shipped procedure data.
const DIAGNOSTIC_TOKENS = [
  'bad_response',
  'unsupported',
  'not_attempted',
  'source_family_statuses',
  'law_grounding_warnings',
  'grounding_used',
];

// Generic "we don't really know" notices that are too broad to help a user.
const GENERIC_NOTICE_PATTERNS = [
  '매뉴얼 확인 필요',
  '정보 없음',
  '정보가 없습니다',
  '확인이 필요',
  '추후 업데이트',
  '준비 중',
];

// Domestic-stay vocabulary that should not appear inside a visa-issuance tab.
const DOMESTIC_STAY_TERMS = ['외국인등록', '체류기간 연장', '체류자격 변경', '재입국'];

// Application-form vocabulary that a source-backed registration tab should carry.
const APPLICATION_FORM_TERMS = ['통합신청서', '신청서', 'doc_app_form'];

// Map a procedure key to the fee block key used in feeInfo.*.procedures.
const FEE_KEY_BY_PROCEDURE = {
  visaIssuance: 'visaIssuance',
  registration: 'foreignRegistration',
  extension: 'extension',
  statusChange: 'statusChange',
  statusGrant: 'grantStatus',
};

// A real status code: A-H followed by a number, or the two named codes.
const STATUS_CODE_RE = /^(?:[A-H]-\d|K-STAR$|REGION-S$)/;

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function readJson(file) {
  return JSON.parse(read(file));
}

function isStatusCode(code) {
  return typeof code === 'string' && STATUS_CODE_RE.test(code);
}

// Flatten any of the doc-group shapes we see in the data into a flat string
// list. Procedures may carry requiredDocs as an object of grouped arrays
// (commonDocs/requiredDocs/additionalDocs/conditionalDocs) or as a flat list.
function flattenDocs(requiredDocs) {
  const out = [];
  const pushAll = (arr) => {
    if (!Array.isArray(arr)) return;
    for (const item of arr) {
      if (typeof item === 'string') out.push(item);
      else if (item && typeof item === 'object' && typeof item.name === 'string') out.push(item.name);
      else if (item && typeof item === 'object' && typeof item.label === 'string') out.push(item.label);
    }
  };
  if (Array.isArray(requiredDocs)) {
    pushAll(requiredDocs);
  } else if (requiredDocs && typeof requiredDocs === 'object') {
    pushAll(requiredDocs.commonDocs);
    pushAll(requiredDocs.requiredDocs);
    pushAll(requiredDocs.additionalDocs);
    pushAll(requiredDocs.conditionalDocs);
  }
  return out;
}

// Collect every string buried anywhere inside a value (for token scans).
function collectStrings(value, out) {
  if (value == null) return out;
  if (typeof value === 'string') {
    out.push(value);
    return out;
  }
  if (Array.isArray(value)) {
    for (const v of value) collectStrings(v, out);
    return out;
  }
  if (typeof value === 'object') {
    for (const k of Object.keys(value)) collectStrings(value[k], out);
  }
  return out;
}

function findDuplicates(list) {
  const seen = new Map();
  const dups = [];
  for (const raw of list) {
    const key = String(raw).trim();
    if (!key) continue;
    const n = (seen.get(key) || 0) + 1;
    seen.set(key, n);
    if (n === 2) dups.push(key);
  }
  return dups;
}

// Has at least one manualRef pointing at a concrete page/source file?
function hasConcreteSource(manualRefs) {
  if (!Array.isArray(manualRefs)) return false;
  return manualRefs.some((m) => {
    if (!m || typeof m !== 'object') return false;
    if (typeof m.sourceFile === 'string' && m.sourceFile.trim()) return true;
    const pr = typeof m.pageRange === 'string' ? m.pageRange : '';
    return /p\.?\s*\d/.test(pr) || /\d+\s*(쪽|페이지)/.test(pr);
  });
}

function classifySource(manualRefs) {
  if (!Array.isArray(manualRefs) || manualRefs.length === 0) return 'none';
  if (hasConcreteSource(manualRefs)) return 'source-backed';
  return 'needs-review';
}

// Detect whether a procedure object carries any real content at all. Used to
// distinguish "procedure exists but is empty" from "procedure absent".
function hasProcedureContent(proc) {
  if (!proc || typeof proc !== 'object') return false;
  if (proc.available === true) return true;
  const docs = flattenDocs(proc.requiredDocs);
  if (docs.length > 0) return true;
  if (typeof proc.summary === 'string' && proc.summary.trim()) return true;
  if (Array.isArray(proc.notes) && proc.notes.some((n) => String(n).trim())) return true;
  if (Array.isArray(proc.manualRefs) && proc.manualRefs.length > 0) return true;
  return false;
}

function feePresentForProcedure(record, procKey) {
  // Per-procedure inline fee fields take priority.
  const proc = (record.procedures || {})[procKey];
  if (proc && typeof proc === 'object') {
    if (proc.fee || proc.fees || proc.feeInfo) return true;
    if (typeof proc.feeNote === 'string' && proc.feeNote.trim()) return true;
  }
  // Otherwise consult the shared feeInfo block.
  const feeKey = FEE_KEY_BY_PROCEDURE[procKey];
  if (!feeKey) return false;
  const blocks = record.feeInfo || {};
  for (const block of Object.values(blocks)) {
    if (!block || typeof block !== 'object') continue;
    const procs = block.procedures || {};
    const entry = procs[feeKey];
    if (entry && Array.isArray(entry.items) && entry.items.length > 0) return true;
  }
  return false;
}

// Count fee blocks/notes that repeat verbatim across the record's feeInfo.
function countDuplicateFeeBlocks(record) {
  const displays = [];
  const blocks = record.feeInfo || {};
  for (const block of Object.values(blocks)) {
    if (!block || typeof block !== 'object') continue;
    const procs = block.procedures || {};
    for (const entry of Object.values(procs)) {
      if (!entry || !Array.isArray(entry.items)) continue;
      for (const item of entry.items) {
        if (item && typeof item.display === 'string' && item.display.trim()) {
          displays.push(item.display.trim());
        }
      }
    }
  }
  return findDuplicates(displays).length;
}

// Extract the procedure keys the frontend render path actually handles, so we
// can detect source-confirmed data that the UI may never surface.
function extractRenderedProcedureKeys(html) {
  const keys = new Set();
  const m = html.match(/const PROCEDURE_CONFIG\s*=\s*\[([\s\S]*?)\];/);
  if (!m) return keys;
  const re = /key:\s*'([^']+)'/g;
  let hit;
  while ((hit = re.exec(m[1])) !== null) keys.add(hit[1]);
  return keys;
}

function auditProcedure(record, procKey, ctx) {
  const proc = (record.procedures || {})[procKey];
  const exists = hasProcedureContent(proc);
  const docs = exists ? flattenDocs(proc && proc.requiredDocs) : [];
  const manualRefs = (proc && Array.isArray(proc.manualRefs)) ? proc.manualRefs : [];
  const sourceStatus = classifySource(manualRefs);
  const feePresent = feePresentForProcedure(record, procKey);

  // All strings inside this procedure, for token scans.
  const strings = collectStrings(proc, []);
  const joined = strings.join('\n');

  const duplicateDocs = findDuplicates(docs);
  const placeholderRows = docs.filter((d) =>
    PLACEHOLDER_TOKENS.some((tok) => d.includes(tok)) || !String(d).trim());
  const placeholderHits = PLACEHOLDER_TOKENS.filter((tok) => joined.includes(tok));
  const diagnosticHits = DIAGNOSTIC_TOKENS.filter((tok) => strings.some((s) => s === tok || s.includes(tok)));

  const flags = [];
  const addFlag = (id, detail) => flags.push({ id, detail });

  // 1. procedure exists but has no documents
  if (exists && docs.length === 0) {
    addFlag('PROCEDURE_NO_DOCS', 'Procedure is present/available but lists no documents.');
  }
  // 2. documents exist but no source references
  if (docs.length > 0 && manualRefs.length === 0) {
    addFlag('DOCS_WITHOUT_SOURCE', `${docs.length} documents but 0 manualRefs/source refs.`);
  }
  // 3. duplicate document names within same procedure
  if (duplicateDocs.length > 0) {
    addFlag('DUPLICATE_DOCS', `Duplicate document rows: ${duplicateDocs.slice(0, 5).join(' | ')}`);
  }
  // 5. placeholder text
  if (placeholderHits.length > 0 || placeholderRows.length > 0) {
    addFlag('PLACEHOLDER_TEXT', `Placeholder content: ${placeholderHits.join(', ') || `${placeholderRows.length} empty/placeholder row(s)`}`);
  }
  // 6. raw diagnostics
  if (diagnosticHits.length > 0) {
    addFlag('RAW_DIAGNOSTIC', `Raw diagnostic token(s) in data: ${diagnosticHits.join(', ')}`);
  }
  // 7. visa issuance mixed with domestic stay procedure. We scan the actual
  // document rows (not summary/notes prose) so that a legitimate contrast
  // sentence — e.g. "이 절차는 외국인등록과 별개입니다" — is not mis-flagged.
  if (procKey === 'visaIssuance' && exists) {
    const docsText = docs.join('\n');
    const mixed = DOMESTIC_STAY_TERMS.filter((t) => docsText.includes(t));
    if (mixed.length > 0) {
      addFlag('ISSUANCE_MIXED_DOMESTIC', `Visa-issuance document list references domestic-stay procedures: ${mixed.join(', ')}`);
    }
  }
  // 8. registration lacks application form where source-backed data suggests it
  if (procKey === 'registration' && exists && sourceStatus !== 'none') {
    const hasForm = APPLICATION_FORM_TERMS.some((t) => joined.includes(t));
    if (!hasForm) {
      addFlag('REGISTRATION_MISSING_APPLICATION_FORM', 'Source-backed registration tab does not mention 통합신청서/신청서.');
    }
  }
  // 9. source-confirmed requirements that the render path may not expose
  if (sourceStatus === 'source-backed' && docs.length > 0) {
    if (!ctx.renderedProcedureKeys.has(procKey)) {
      addFlag('RENDER_PATH_GAP', `Procedure key '${procKey}' not found in frontend PROCEDURE_CONFIG.`);
    } else if (proc && proc.available === false) {
      addFlag('RENDER_PATH_GAP', 'Source-confirmed docs exist but available=false, so the tab is filtered out of the UI.');
    }
  }
  // 11. missing user-facing next-action hint
  if (exists) {
    const hasSummary = typeof proc.summary === 'string' && proc.summary.trim();
    const hasNotes = Array.isArray(proc.notes) && proc.notes.some((n) => String(n).trim());
    const hasNext = (typeof proc.nextStep === 'string' && proc.nextStep.trim())
      || (typeof proc.nextAction === 'string' && proc.nextAction.trim());
    if (!hasSummary && !hasNotes && !hasNext) {
      addFlag('NO_NEXT_ACTION_HINT', 'No summary, notes, or next-action hint for an existing procedure.');
    }
  }
  // 12. overly broad generic missing-data notices
  if (exists) {
    const noteStrings = []
      .concat(Array.isArray(proc.notes) ? proc.notes : [])
      .concat(manualRefs.map((m) => (m && m.pageRange) || ''))
      .map((n) => String(n));
    const generic = GENERIC_NOTICE_PATTERNS.filter((p) => noteStrings.some((n) => n.includes(p)));
    if (generic.length > 0 && sourceStatus !== 'source-backed') {
      addFlag('GENERIC_MISSING_NOTICE', `Generic notice(s) without concrete source: ${generic.join(', ')}`);
    }
  }

  return {
    statusCode: record.code,
    statusName: record.nameKo || record.name || '',
    procedureKey: procKey,
    exists,
    available: Boolean(proc && proc.available === true),
    documentCount: docs.length,
    sourceRefCount: manualRefs.length,
    feePresent,
    duplicateDocCount: duplicateDocs.length,
    placeholderRowCount: placeholderHits.length + placeholderRows.length,
    diagnosticCount: diagnosticHits.length,
    sourceStatus,
    riskFlags: flags,
  };
}

function auditRecord(record, ctx) {
  const procedures = PROCEDURE_KEYS.map((k) => auditProcedure(record, k, ctx));

  // 4. duplicate fee blocks (record-level)
  const duplicateFeeBlocks = countDuplicateFeeBlocks(record);

  // 10. exact sub-code vs parent distinction unclear (record-level)
  const subCodeNotes = [];
  const hasSubCodesCamel = Array.isArray(record.subCodes);
  const hasSubCodesLower = Array.isArray(record.subcodes);
  if (hasSubCodesCamel && hasSubCodesLower) {
    subCodeNotes.push('Record carries both subCodes and subcodes; parent/sub structure is ambiguous.');
  }
  const subList = []
    .concat(hasSubCodesCamel ? record.subCodes : [])
    .concat(hasSubCodesLower ? record.subcodes : []);
  const exactSubCodes = subList
    .map((s) => (s && typeof s.code === 'string' ? s.code : ''))
    .filter((c) => /^[A-H]-\d+-/.test(c));
  if (exactSubCodes.length > 0 && !record.subcodeDisambiguation && !record._subcodeNote) {
    subCodeNotes.push(`Exact sub-codes present (${exactSubCodes.slice(0, 6).join(', ')}) without explicit parent/sub disambiguation metadata.`);
  }

  const recordFlags = [];
  if (duplicateFeeBlocks > 0) {
    recordFlags.push({ id: 'DUPLICATE_FEE_BLOCKS', detail: `${duplicateFeeBlocks} repeated fee display string(s).` });
  }
  for (const note of subCodeNotes) {
    recordFlags.push({ id: 'SUBCODE_AMBIGUOUS', detail: note });
  }

  const allFlags = procedures.flatMap((p) => p.riskFlags).concat(recordFlags);
  const flagCounts = {};
  for (const f of allFlags) flagCounts[f.id] = (flagCounts[f.id] || 0) + 1;

  return {
    statusCode: record.code,
    statusName: record.nameKo || record.name || '',
    category: record.cat || '',
    sourceVerified: Boolean((record.sourceManualStatus || {}).verified),
    procedureCount: procedures.filter((p) => p.exists).length,
    duplicateFeeBlocks,
    riskScore: allFlags.length,
    flagCounts,
    recordFlags,
    procedures,
  };
}

function runAudit(options) {
  const opts = options || {};
  const visaData = opts.visaData || readJson(VISA_DATA);
  const html = opts.html != null ? opts.html : (fs.existsSync(INDEX_HTML) ? read(INDEX_HTML) : '');
  const renderedProcedureKeys = extractRenderedProcedureKeys(html);
  const ctx = { renderedProcedureKeys };

  const statusRecords = visaData
    .filter((r) => r && isStatusCode(r.code))
    .sort((a, b) => String(a.code).localeCompare(String(b.code)));

  const records = statusRecords.map((r) => auditRecord(r, ctx));

  // Summary totals.
  const totalFlags = {};
  let totalProcedures = 0;
  let totalDocs = 0;
  for (const rec of records) {
    for (const [id, n] of Object.entries(rec.flagCounts)) {
      totalFlags[id] = (totalFlags[id] || 0) + n;
    }
    for (const p of rec.procedures) {
      if (p.exists) totalProcedures += 1;
      totalDocs += p.documentCount;
    }
  }

  const topHighRisk = records
    .filter((r) => r.riskScore > 0)
    .sort((a, b) => b.riskScore - a.riskScore || a.statusCode.localeCompare(b.statusCode))
    .slice(0, 15)
    .map((r) => ({ statusCode: r.statusCode, statusName: r.statusName, riskScore: r.riskScore, flagCounts: r.flagCounts }));

  const byCode = new Map(records.map((r) => [r.statusCode, r]));
  const priorityFindings = PRIORITY_STATUSES.map((code) => {
    const rec = byCode.get(code);
    return {
      statusCode: code,
      present: Boolean(rec),
      riskScore: rec ? rec.riskScore : null,
      flagCounts: rec ? rec.flagCounts : null,
    };
  });

  const summary = {
    generatedFor: '2026-06',
    statusRecordsAudited: records.length,
    proceduresAudited: totalProcedures,
    procedureKeys: PROCEDURE_KEYS,
    totalDocuments: totalDocs,
    totalRiskFlags: Object.values(totalFlags).reduce((a, b) => a + b, 0),
    riskFlagBreakdown: totalFlags,
  };

  const nextFixBatches = buildNextFixBatches(records, byCode);

  return { summary, topHighRisk, records, priorityFindings, nextFixBatches };
}

// Recommend follow-up fix batches, ordered per the agreed roadmap. The audit
// only *recommends*; it never applies fixes.
function buildNextFixBatches(records, byCode) {
  const flaggedIn = (codes) => codes.filter((c) => {
    const r = byCode.get(c);
    return r && r.riskScore > 0;
  });
  return [
    { order: 1, name: 'D-2 student journey cleanup (golden path)', statuses: flaggedIn(['D-2']) },
    { order: 2, name: 'Priority batch 1: C-3, H-1, H-2, G-1/G-1-5', statuses: flaggedIn(['C-3', 'H-1', 'H-2', 'G-1', 'G-1-5']) },
    { order: 3, name: 'Priority batch 2: E-7, F-6, F-4, D-10', statuses: flaggedIn(['E-7', 'F-6', 'F-4', 'D-10']) },
    { order: 4, name: 'Exact-code search accessibility and QA hooks', statuses: records.filter((r) => r.flagCounts.SUBCODE_AMBIGUOUS).map((r) => r.statusCode) },
    { order: 5, name: 'Placeholder/empty block suppression across all statuses', statuses: records.filter((r) => r.flagCounts.PLACEHOLDER_TEXT || r.flagCounts.GENERIC_MISSING_NOTICE).map((r) => r.statusCode) },
    { order: 6, name: 'Auth/Stay Dashboard scaffold (only after core journeys reliable)', statuses: [] },
  ];
}

/* -------------------------------------------------------------------------- */
/* Reporting                                                                  */
/* -------------------------------------------------------------------------- */

function pad(str, width) {
  const s = String(str);
  return s.length >= width ? s : s + ' '.repeat(width - s.length);
}

function printReport(result) {
  const { summary, topHighRisk, records, priorityFindings, nextFixBatches } = result;

  console.log('============================================================');
  console.log(' ALL-STATUS PROCEDURE JOURNEY AUDIT (2026-06)');
  console.log('============================================================');
  console.log('');
  console.log('1) SUMMARY TOTALS');
  console.log('   Status records audited : ' + summary.statusRecordsAudited);
  console.log('   Procedures present     : ' + summary.proceduresAudited);
  console.log('   Documents counted      : ' + summary.totalDocuments);
  console.log('   Total risk flags       : ' + summary.totalRiskFlags);
  console.log('   Risk flag breakdown:');
  for (const id of Object.keys(summary.riskFlagBreakdown).sort()) {
    console.log('     - ' + pad(id, 38) + summary.riskFlagBreakdown[id]);
  }
  console.log('');

  console.log('2) TOP HIGH-RISK STATUSES');
  if (topHighRisk.length === 0) {
    console.log('   (none)');
  } else {
    for (const r of topHighRisk) {
      console.log('   ' + pad(r.statusCode, 10) + 'risk=' + pad(r.riskScore, 4) + (r.statusName || ''));
    }
  }
  console.log('');

  console.log('3) PER-STATUS PROCEDURE MATRIX');
  console.log('   ' + pad('status', 9) + pad('procedure', 26) + pad('docs', 6) + pad('src', 5) + pad('fee', 5) + pad('dupD', 6) + pad('phRow', 7) + pad('source', 14) + 'flags');
  for (const rec of records) {
    for (const p of rec.procedures) {
      if (!p.exists && p.riskFlags.length === 0) continue;
      const flagIds = p.riskFlags.map((f) => f.id).join(',');
      console.log('   '
        + pad(p.statusCode, 9)
        + pad(p.procedureKey, 26)
        + pad(p.documentCount, 6)
        + pad(p.sourceRefCount, 5)
        + pad(p.feePresent ? 'Y' : '-', 5)
        + pad(p.duplicateDocCount, 6)
        + pad(p.placeholderRowCount, 7)
        + pad(p.sourceStatus, 14)
        + flagIds);
    }
    if (rec.recordFlags.length > 0) {
      for (const f of rec.recordFlags) {
        console.log('   ' + pad(rec.statusCode, 9) + pad('(record)', 26) + pad('', 43) + f.id);
      }
    }
  }
  console.log('');

  console.log('4) PRIORITY-STATUS FINDINGS');
  for (const p of priorityFindings) {
    if (!p.present) {
      console.log('   ' + pad(p.statusCode, 10) + 'NOT PRESENT in data');
      continue;
    }
    const flags = p.flagCounts && Object.keys(p.flagCounts).length
      ? Object.entries(p.flagCounts).map(([k, v]) => `${k}:${v}`).join(', ')
      : 'no flags';
    console.log('   ' + pad(p.statusCode, 10) + 'risk=' + pad(p.riskScore, 4) + flags);
  }
  console.log('');

  console.log('5) RECOMMENDED NEXT FIX BATCHES');
  for (const b of nextFixBatches) {
    const subjects = b.statuses && b.statuses.length ? b.statuses.join(', ') : '(no flagged statuses)';
    console.log('   ' + b.order + '. ' + b.name);
    console.log('      -> ' + subjects);
  }
  console.log('');
}

function buildMarkdown(result) {
  const { summary, topHighRisk, records, priorityFindings, nextFixBatches } = result;
  const lines = [];
  lines.push('# All-Status Procedure Journey Audit (2026-06)');
  lines.push('');
  lines.push('> Generated by `scripts/audit_procedure_journeys.js`. Read-only audit.');
  lines.push('> Warnings describe existing data-quality issues; no production data was changed.');
  lines.push('');
  lines.push('## 1. Summary totals');
  lines.push('');
  lines.push('| Metric | Value |');
  lines.push('| --- | --- |');
  lines.push(`| Status records audited | ${summary.statusRecordsAudited} |`);
  lines.push(`| Procedures present | ${summary.proceduresAudited} |`);
  lines.push(`| Documents counted | ${summary.totalDocuments} |`);
  lines.push(`| Total risk flags | ${summary.totalRiskFlags} |`);
  lines.push('');
  lines.push('### Risk flag breakdown');
  lines.push('');
  lines.push('| Flag | Count |');
  lines.push('| --- | --- |');
  for (const id of Object.keys(summary.riskFlagBreakdown).sort()) {
    lines.push(`| ${id} | ${summary.riskFlagBreakdown[id]} |`);
  }
  lines.push('');

  lines.push('## 2. Top high-risk statuses');
  lines.push('');
  lines.push('| Status | Name | Risk score | Flags |');
  lines.push('| --- | --- | --- | --- |');
  for (const r of topHighRisk) {
    const flags = Object.entries(r.flagCounts).map(([k, v]) => `${k}:${v}`).join(', ');
    lines.push(`| ${r.statusCode} | ${r.statusName} | ${r.riskScore} | ${flags} |`);
  }
  lines.push('');

  lines.push('## 3. Per-status procedure matrix');
  lines.push('');
  lines.push('| Status | Name | Procedure | Docs | Src refs | Fee | Dup docs | Placeholder rows | Source status | Risk flags |');
  lines.push('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |');
  for (const rec of records) {
    for (const p of rec.procedures) {
      if (!p.exists && p.riskFlags.length === 0) continue;
      const flags = p.riskFlags.map((f) => f.id).join(', ') || '-';
      lines.push(`| ${p.statusCode} | ${p.statusName} | ${p.procedureKey} | ${p.documentCount} | ${p.sourceRefCount} | ${p.feePresent ? 'Y' : '-'} | ${p.duplicateDocCount} | ${p.placeholderRowCount} | ${p.sourceStatus} | ${flags} |`);
    }
    for (const f of rec.recordFlags) {
      lines.push(`| ${rec.statusCode} | ${rec.statusName} | (record) | - | - | - | - | - | - | ${f.id} |`);
    }
  }
  lines.push('');

  lines.push('## 4. Priority-status findings');
  lines.push('');
  lines.push('| Status | Present | Risk score | Flags |');
  lines.push('| --- | --- | --- | --- |');
  for (const p of priorityFindings) {
    const flags = p.present && p.flagCounts
      ? (Object.entries(p.flagCounts).map(([k, v]) => `${k}:${v}`).join(', ') || 'none')
      : '-';
    lines.push(`| ${p.statusCode} | ${p.present ? 'yes' : 'NO'} | ${p.present ? p.riskScore : '-'} | ${flags} |`);
  }
  lines.push('');

  lines.push('## 5. Recommended next fix batches');
  lines.push('');
  for (const b of nextFixBatches) {
    const subjects = b.statuses && b.statuses.length ? b.statuses.join(', ') : '_(no flagged statuses)_';
    lines.push(`${b.order}. **${b.name}** — ${subjects}`);
  }
  lines.push('');
  return lines.join('\n');
}

function writeReports(result) {
  fs.writeFileSync(JSON_REPORT, JSON.stringify(result, null, 2) + '\n', 'utf8');
  fs.writeFileSync(MD_REPORT, buildMarkdown(result), 'utf8');
}

function main() {
  const argv = process.argv.slice(2);
  const quiet = argv.includes('--quiet');
  const noWrite = argv.includes('--no-write');

  let result;
  try {
    result = runAudit();
  } catch (err) {
    console.error('ERROR: procedure journey audit could not run: ' + err.message);
    process.exit(2);
    return;
  }

  if (!quiet) printReport(result);
  if (!noWrite) {
    writeReports(result);
    if (!quiet) {
      console.log('Wrote JSON report : ' + path.relative(ROOT, JSON_REPORT));
      console.log('Wrote MD report   : ' + path.relative(ROOT, MD_REPORT));
    }
  }
  // Warnings never fail the audit run itself.
  process.exit(0);
}

module.exports = {
  PROCEDURE_KEYS,
  PRIORITY_STATUSES,
  PLACEHOLDER_TOKENS,
  DIAGNOSTIC_TOKENS,
  STATUS_CODE_RE,
  isStatusCode,
  flattenDocs,
  findDuplicates,
  classifySource,
  runAudit,
  buildMarkdown,
  VISA_DATA,
  BACKEND_VISAS,
};

if (require.main === module) {
  main();
}
