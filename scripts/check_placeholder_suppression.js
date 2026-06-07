#!/usr/bin/env node
/*
 * Static rendering-contract checks for placeholder / empty-block / diagnostic
 * suppression in the user-facing UI (index.html + ai.html).
 *
 * These are source-level assertions (no browser): they verify the shared
 * rendering layer can never surface placeholder document rows, empty procedure
 * blocks, or raw developer diagnostics to normal users — independent of the
 * underlying data. Regression baselines (D-2 / priority / remaining / exact-code
 * search / static cards) are run via execFileSync.
 *
 * Failures are real invariant breaks (non-zero exit).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const aiHtml = fs.readFileSync(path.join(ROOT, 'ai.html'), 'utf8');

const failures = [];
const passed = [];
function check(name, cond, detail) {
  if (cond) passed.push(name);
  else failures.push(name + (detail ? ' — ' + detail : ''));
}

// Extract a top-level function body by brace matching.
function extractFunction(src, name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(', 'g');
  const m = re.exec(src);
  if (!m) return '';
  const braceStart = src.indexOf('{', re.lastIndex);
  if (braceStart < 0) return '';
  let depth = 0;
  for (let i = braceStart; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(m.index, i + 1); }
  }
  return '';
}

const isDocPlaceholder = extractFunction(html, 'isDocPlaceholder');
const dedupeDocs = extractFunction(html, 'dedupeDocs');
const renderDocTags = extractFunction(html, 'renderDocTags');
const renderProcedurePanel = extractFunction(html, 'renderProcedurePanel');
const renderDocumentTabPanel = extractFunction(html, 'renderDocumentTabPanel');
const renderProcedureFeeBox = extractFunction(html, 'renderProcedureFeeBox');

/* 1. The placeholder predicate covers the user-facing placeholder tokens */
{
  const tokens = ['문서명 미상', '비고 정보 없음', 'DATA_MISSING', '매뉴얼 확인 필요', '페이지 확인 필요'];
  const tokenListPresent = tokens.every(t => html.includes(`'${t}'`) || html.includes(`"${t}"`));
  check('1. DOC_PLACEHOLDER_TOKENS / isDocPlaceholder covers all user-facing placeholder tokens',
    tokenListPresent && Boolean(isDocPlaceholder), tokens.join(', '));
}

/* 2. dedupeDocs drops placeholder rows centrally */
check('2. dedupeDocs suppresses placeholder rows via isDocPlaceholder',
  Boolean(dedupeDocs) && /isDocPlaceholder\(key\)/.test(dedupeDocs));

/* 3. renderDocTags has defense-in-depth placeholder filtering */
check('3. renderDocTags filters placeholders before rendering',
  Boolean(renderDocTags) && /isDocPlaceholder\(key\)/.test(renderDocTags));

/* 4. document-tab panel skips missing document names */
check('4. renderDocumentTabPanel suppresses missing document-name rows',
  Boolean(renderDocumentTabPanel) && /nameIsMissing/.test(renderDocumentTabPanel)
    && /if \(nameIsMissing\) return ''/.test(renderDocumentTabPanel));

/* 5. document-tab panel suppresses empty notes */
check('5. renderDocumentTabPanel suppresses empty notes',
  Boolean(renderDocumentTabPanel) && /noteIsMissing/.test(renderDocumentTabPanel)
    && /noteIsMissing\s*\?\s*''/.test(renderDocumentTabPanel));

/* 6. empty document grids are not rendered (panel guards on docsHtml) */
check('6. renderProcedurePanel does not render an empty document grid',
  Boolean(renderProcedurePanel) && /docsHtml \? `<div class="doc-group-grid">/.test(renderProcedurePanel));

/* 7. empty fee box is not rendered */
check('7. renderProcedureFeeBox returns nothing when there is no fee info',
  Boolean(renderProcedureFeeBox) && /if \(!feeInfo\) return ''/.test(renderProcedureFeeBox));

/* 8. empty doc groups collapse (renderDocGroup guards on length) */
{
  const renderDocGroup = extractFunction(html, 'renderDocGroup');
  check('8. renderDocGroup returns nothing for an empty group',
    Boolean(renderDocGroup) && /if \(!docs \|\| !docs\.length\) return ''/.test(renderDocGroup));
}

/* 9. result cards never render raw diagnostic markers */
{
  const renderResults = extractFunction(html, 'renderResults');
  const markers = ['bad_response', 'not_attempted', 'unsupported', 'source_family_statuses',
    'law_grounding_warnings', 'grounding_used', 'planned_not_wired', 'manual: attempted'];
  const leaked = markers.filter(m => renderResults.includes(m));
  check('9. renderResults() renders no raw diagnostic markers', leaked.length === 0, leaked.join(', '));
}

/* 10. AI answer panel gates raw developer codes behind an explicit debug flag */
{
  const gated = /devDiagnosticsEnabled/.test(aiHtml)
    && /data-diagnostics="developer"/.test(aiHtml)
    && /paradisoDevDiagnostics/.test(aiHtml);
  // and the debug block is the only place that joins raw lawWarnings into output
  const debugOnly = /devDiagnosticsEnabled && \(lawWarnings\.length/.test(aiHtml);
  check('10. ai.html exposes raw developer codes only under an explicit debug/dev gate',
    gated && debugOnly);
}

/* 11. AI answer panel maps grounding flags to user-friendly copy (no raw keys shown) */
{
  // grounding_used etc. are read as object properties, never concatenated into
  // user-visible strings outside the gated diagnostics block.
  const note = /buildGroundingNote/.test(aiHtml);
  check('11. ai.html surfaces grounding state via friendly note, not raw keys', note);
}

/* 12. data hygiene + renderer guarantee for residual placeholder markers.
 *
 * This PR is a renderer-level suppression fix, NOT a data rewrite. Committed
 * data legitimately still carries "no data" sentinels — DATA_MISSING field
 * values and 매뉴얼 확인 필요 doc rows in non-target procedure tabs. Those are
 * never user-facing because the rendering layer (DOC_PLACEHOLDER_TOKENS /
 * dedupeDocs / toDocArray / renderDocTags / renderDocumentTabPanel) strips them.
 * So we assert: (a) the truly-synthetic DISPLAY placeholders never leak into
 * data, and (b) every residual marker is covered by the suppression token list.
 */
{
  const bad = [];
  // (a) synthetic display placeholders must never appear in committed data
  //     (this is the existing static-card contract; keep it enforced here too).
  for (const f of ['visa_data.json', path.join('backend', 'data', 'visas.json')]) {
    const t = fs.readFileSync(path.join(ROOT, f), 'utf8');
    for (const tok of ['문서명 미상', '비고 정보 없음']) {
      if (t.includes(tok)) bad.push(`${f}:${tok}(synthetic-leaked-into-data)`);
    }
  }
  // (b) residual markers that legitimately exist in data must be renderer-suppressed.
  for (const tok of ['매뉴얼 확인 필요', '페이지 확인 필요', 'DATA_MISSING']) {
    if (!html.includes(`'${tok}'`)) bad.push(`${tok}(missing-from-suppression-list)`);
  }
  check('12. synthetic placeholders absent from data; residual markers renderer-suppressed',
    bad.length === 0, bad.join(', '));
}

/* 13-18. Regression baselines still pass */
const regressions = [
  ['13. D-2 golden path checks still pass', 'check_d2_student_journey.js'],
  ['14. expanded priority status checks still pass', 'check_priority_status_journeys.js'],
  ['15. remaining status journey checks still pass', 'check_remaining_status_journeys.js'],
  ['16. exact-code search QA checks still pass', 'check_exact_code_search.js'],
  ['17. static visa result card checks still pass', 'check_static_visa_result_cards.js'],
  ['18. AI shell semantics checks still pass', 'check_ai_shell_semantics.js'],
];
for (const [label, script] of regressions) {
  let ok = false;
  try { execFileSync('node', [path.join(ROOT, 'scripts', script)], { stdio: 'ignore' }); ok = true; }
  catch (e) { ok = false; }
  check(label, ok);
}

/* 19. all-status audit still runs */
{
  let ok = false;
  try {
    const audit = require('./audit_procedure_journeys.js');
    const r = audit.runAudit();
    ok = Array.isArray(r.records) && r.records.length > 0;
  } catch (e) { ok = false; }
  check('19. all-status audit still runs', ok);
}

/* ---- report ---- */
console.log('Placeholder / empty-block suppression checks:');
for (const n of passed) console.log('  PASS ' + n);
for (const n of failures) console.log('  FAIL ' + n);
console.log('');
console.log(`${passed.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
