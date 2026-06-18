#!/usr/bin/env node
/*
 * Deterministic checks for the AI answer-shell source semantics in ai.html.
 *
 * Part functional, part static:
 *   - extracts the real `t`, `tt`, and `generateBadges` functions from ai.html
 *     and exercises them for the H-1 study golden case, asserting that
 *     D-2 / D-4 render as "Related status to verify" chips (not Manual sources)
 *     and that the detected H-1 status renders as a "Checked status" chip when
 *     the answer is not manual-grounded;
 *   - static-asserts the answer-basis labels, the four-language footer
 *     disclaimer (incl. natural English), the friendly law-unavailable text,
 *     and that raw SOURCE_UNAVAILABLE is not used as default user-facing copy.
 *
 * Usage:  node scripts/check_ai_shell_semantics.js
 * Exits 0 on success, 1 with a list of failures.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const AI_HTML = process.env.CHECK_AI_HTML
  || path.join(__dirname, '..', 'ai.html');

const src = fs.readFileSync(AI_HTML, 'utf8');
const failures = [];
function check(cond, msg) { if (!cond) failures.push(msg); }

// --- Extract a top-level `function NAME(...) { ... }` by brace matching. -----
function extractFunction(name) {
  const re = new RegExp('function\\s+' + name + '\\s*\\(', 'g');
  const m = re.exec(src);
  if (!m) return null;
  // Find the opening brace of the body.
  let i = src.indexOf('{', re.lastIndex);
  if (i < 0) return null;
  let depth = 0;
  for (let j = i; j < src.length; j++) {
    const ch = src[j];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) {
        return src.slice(m.index, j + 1);
      }
    }
  }
  return null;
}

const tSrc = extractFunction('t');
const ttSrc = extractFunction('tt');
const genSrc = extractFunction('generateBadges');

check(Boolean(tSrc), 'could not extract function t() from ai.html');
check(Boolean(ttSrc), 'could not extract function tt() from ai.html');
check(Boolean(genSrc), 'could not extract function generateBadges() from ai.html');

let generateBadges = null;
if (tSrc && ttSrc && genSrc) {
  // eslint-disable-next-line no-eval
  generateBadges = eval('(function(){' + tSrc + '\n' + ttSrc + '\n' + genSrc + '\nreturn generateBadges;})()');
}

// --- Functional: H-1 study golden case --------------------------------------
if (generateBadges) {
  const answer = 'On H-1 you may face activity-scope limits. A D-2 or D-4 status '
    + 'is for study. Call 1345 to confirm.';
  const meta = {
    related_statuses_not_sources: ['D-2', 'D-4'],
    visa_code_detected: 'H-1',
    grounding_used: false,
  };
  const en = generateBadges(answer, 'en', meta);

  // D-2 / D-4 must be related-status chips, never "Manual" source chips.
  check(/data-chip-kind="related"[^>]*>Related status to verify: D-2/.test(en)
        || /Related status to verify: D-2/.test(en),
        'D-2 should render as a "Related status to verify" chip');
  check(/Related status to verify: D-4/.test(en),
        'D-4 should render as a "Related status to verify" chip');
  check(!/Manual: D-2/.test(en), 'D-2 must NOT render as "Manual: D-2"');
  check(!/Manual: D-4/.test(en), 'D-4 must NOT render as "Manual: D-4"');
  check(!/Manual source: D-2/.test(en), 'D-2 must NOT render as a manual source chip');

  // H-1 is the detected status and the answer is not grounded -> "Checked status".
  check(/data-chip-kind="checked"/.test(en), 'detected H-1 should be a checked-status chip when not grounded');
  check(/Checked status: H-1/.test(en), 'H-1 should render with the "Checked status" label');
  check(!/Manual: H-1/.test(en), 'ungrounded H-1 must NOT render as "Manual: H-1"');

  // Direct vs related chips use different classes.
  check(/class="bdg bdg-related"/.test(en), 'related chips must use the bdg-related class');
  check(/class="bdg bdg-checked"/.test(en), 'checked chips must use the bdg-checked class');

  // When the answer IS manual-grounded, the detected status may be a manual chip.
  const grounded = generateBadges('Extend your D-2 status.', 'en', {
    visa_code_detected: 'D-2', grounding_used: true, related_statuses_not_sources: [],
  });
  check(/Manual source: D-2/.test(grounded), 'grounded detected status should render as a manual source chip');

  // Korean labels for the related chip.
  const ko = generateBadges(answer, 'ko', meta);
  check(/함께 확인할 관련 체류자격: D-2/.test(ko), 'Korean related-status label missing for D-2');
  check(/확인한 체류자격: H-1/.test(ko), 'Korean checked-status label missing for H-1');
}

// --- Static: answer-basis labels (4 languages) ------------------------------
check(/Source-limited guidance/.test(src), 'English answer-basis "Source-limited guidance" missing');
check(/Source-confirmed manual guidance/.test(src), 'English answer-basis "Source-confirmed manual guidance" missing');
check(/General advisory guidance/.test(src), 'English answer-basis "General advisory guidance" missing');
check(/제한적 근거 안내/.test(src), 'Korean answer-basis "제한적 근거 안내" missing');
check(/공식 매뉴얼 근거 확인/.test(src), 'Korean answer-basis "공식 매뉴얼 근거 확인" missing');
check(/일반 참고 안내/.test(src), 'Korean answer-basis "일반 참고 안내" missing');
check(/依据有限的指引/.test(src), 'Simplified Chinese answer-basis label missing');
check(/依據有限的指引/.test(src), 'Traditional Chinese answer-basis label missing');

// --- Static: related-status labels (4 languages) ----------------------------
check(/Related status to verify/.test(src), 'English "Related status to verify" label missing');
check(/함께 확인할 관련 체류자격/.test(src), 'Korean related-status label missing');
check(/需一并确认的相关居留资格/.test(src), 'Simplified Chinese related-status label missing');
check(/需一併確認的相關居留資格/.test(src), 'Traditional Chinese related-status label missing');

// --- Static: checked-status labels (4 languages) ----------------------------
check(/Checked status/.test(src), 'English "Checked status" label missing');
check(/확인한 체류자격/.test(src), 'Korean "확인한 체류자격" label missing');
check(/已确认的居留资格/.test(src), 'Simplified Chinese checked-status label missing');
check(/已確認的居留資格/.test(src), 'Traditional Chinese checked-status label missing');

// --- Static: friendly law-unavailable text + raw code only in details -------
check(/Legal source lookup returned an unsupported response format\. Paradiso is using limited guidance until this is fixed\./.test(src),
      'English friendly law-unavailable text missing');
check(/법령 출처 조회가 지원되지 않는 응답 형식을 반환했습니다\. 수정 전까지 Paradiso는 제한적 안내를 사용합니다\./.test(src),
      'Korean friendly law-unavailable text missing');
// Raw SOURCE_UNAVAILABLE must only appear inside the warning-code mapping /
// technical details, never as default user-facing prose. We approximate this
// by requiring it not to appear in a friendly sentence context.
check(!/SOURCE_UNAVAILABLE[^A-Z_]*could not/.test(src),
      'raw SOURCE_UNAVAILABLE leaked into user-facing prose');

// --- Static: public source-status chips -------------------------------------
check(/source-status-chips/.test(src), 'public source-status chip wrapper missing');
check(/source-chip/.test(src), 'public source-status chip style missing');
check(/data-row-kind="public-source-status"/.test(src), 'public source-status row marker missing');
check(/source-name-list/.test(src), 'public source name/version subnote missing');
check(/versionDate/.test(src), 'public source-status renderer must include source version dates');
check(/manualSources\.length && !publicLabels\.length/.test(src),
      'manual fallback row should be suppressed when public source labels are present');
check(/@media \(max-width: 480px\)[\s\S]*source-status-chips/.test(src),
      'mobile source-status chip wrapping rule missing');

// --- Static: footer disclaimer i18n (4 languages, natural English) ----------
check(/id="referenceDisclaimer"/.test(src), 'footer is missing the referenceDisclaimer id');
check(/SHELL_FOOTER_DISCLAIMER\s*=/.test(src), 'SHELL_FOOTER_DISCLAIMER map missing');
check(/Paradiso provides public law\/manual-based reference information/.test(src),
      'English footer disclaimer text missing');
check(/Paradiso 提供基于公开法令与手册的参考信息/.test(src), 'Simplified Chinese footer missing');
check(/Paradiso 提供基於公開法令與手冊的參考資訊/.test(src), 'Traditional Chinese footer missing');
check(/applyShellLanguage\(userLang\)/.test(src), 'applyShellLanguage is not wired into the send flow');

// --- Static: warning de-duplication wiring ----------------------------------
check(/const hasPanel = Boolean\(sourcePanelHtml\)/.test(src), 'panel-presence dedup guard missing');
check(/answerBasisCommunicatesLimit/.test(src), 'answerBasisCommunicatesLimit dedup helper missing');

// ===========================================================================
// AI answer pipeline contract & rendering checks (Part F).
//
// These guard the class of bug that produced the production
// "Can't find variable: errorType" ReferenceError: a source-panel renderer
// referencing a variable that is only declared inside a sibling helper. Full
// JS AST tooling is intentionally avoided (no new deps); we use brace-matched
// function extraction plus targeted free-variable scans.
// ===========================================================================

// Strip a `function name(args) {` signature, returning just the body text.
function bodyOf(fnSrc) {
  if (!fnSrc) return '';
  const i = fnSrc.indexOf('{');
  return i < 0 ? fnSrc : fnSrc.slice(i + 1, fnSrc.length - 1);
}
// True when `name` is declared (const/let/var) or is a parameter of fnSrc.
function declaresLocal(fnSrc, name) {
  if (!fnSrc) return false;
  const body = bodyOf(fnSrc);
  if (new RegExp('(?:const|let|var)\\s+' + name + '\\b').test(body)) return true;
  const sig = fnSrc.slice(0, fnSrc.indexOf('{'));
  return new RegExp('\\(([^)]*\\b)?' + name + '\\b').test(sig);
}
function references(fnSrc, name) {
  return new RegExp('\\b' + name + '\\b').test(bodyOf(fnSrc));
}

const renderPanelSrc = extractFunction('renderGroundingSourcePanel');
const sourceCopySrc = extractFunction('sourcePanelCopyForState');
const lawMsgSrc = extractFunction('lawSourcePanelMessage');
const normalizeSrc = extractFunction('normalizeAnswerMetadata');

check(Boolean(renderPanelSrc), 'could not extract renderGroundingSourcePanel() from ai.html');
check(Boolean(normalizeSrc), 'normalizeAnswerMetadata() is missing from ai.html');

if (renderPanelSrc) {
  // (1) errorType: if referenced, it MUST be declared locally (the original bug).
  check(!references(renderPanelSrc, 'errorType') || declaresLocal(renderPanelSrc, 'errorType'),
        'renderGroundingSourcePanel() references errorType without declaring it locally (the production ReferenceError)');
  // (2) parser-status variables must be locally declared, not borrowed.
  for (const v of ['topParser', 'familyStatuses', 'parserByFamily', 'PARSE_FAIL', 'parserFailed']) {
    check(!references(renderPanelSrc, v) || declaresLocal(renderPanelSrc, v),
          'renderGroundingSourcePanel() references ' + v + ' without a local declaration');
  }
  // (3) obvious free variables that only exist inside sibling helpers must not
  // leak into the panel renderer.
  for (const v of ['hasBadLawResponse', 'normalized', 'legalAnalysis', 'directCount', 'relatedCount']) {
    check(!references(renderPanelSrc, v) || declaresLocal(renderPanelSrc, v),
          'renderGroundingSourcePanel() references helper-local variable ' + v);
  }
  // (7) the renderer must route metadata through normalizeAnswerMetadata().
  check(/normalizeAnswerMetadata\(/.test(renderPanelSrc),
        'renderGroundingSourcePanel() does not call normalizeAnswerMetadata()');
}

// Sibling source-panel helpers must also declare their own errorType.
for (const [name, fn] of [['sourcePanelCopyForState', sourceCopySrc], ['lawSourcePanelMessage', lawMsgSrc]]) {
  if (fn) {
    check(!references(fn, 'errorType') || declaresLocal(fn, 'errorType'),
          name + '() references errorType without declaring it locally');
  }
}

// (4) developer diagnostics: raw codes must come AFTER the human-readable line.
const detailsPos = src.indexOf('실시간 법령 조회 응답을 파싱하지 못했습니다');
const rawCodesPos = src.indexOf('raw developer codes', detailsPos >= 0 ? detailsPos : 0);
check(detailsPos >= 0, 'human-readable parse-failure diagnostic line missing');
check(rawCodesPos > detailsPos, 'raw developer codes must appear AFTER the human-readable diagnostic line');

// (5) the developer-diagnostics <details> block must NOT be open by default.
check(!/<details\s+open/i.test(src), 'developer diagnostics <details> must not be open by default');

// (6) copy-safe answer must not weld in developer diagnostics. The COPY_PAYLOADS
// assignments only ever carry { answer, source }.
const copyAssigns = src.match(/COPY_PAYLOADS\[[^\]]+\]\s*=\s*\{[^}]*\}/g) || [];
check(copyAssigns.length > 0, 'no COPY_PAYLOADS assignments found');
for (const a of copyAssigns) {
  check(!/data-diagnostics|error-details|developer/.test(a),
        'copy payload must not include developer diagnostics: ' + a);
}

// normalizeAnswerMetadata must default the contract fields to stable types.
if (normalizeSrc) {
  for (const field of [
    'law_grounding_warnings', 'law_lookup_error_type', 'parser_status',
    'source_family_statuses', 'parser_status_by_family', 'law_sources',
    'grounding_sources', 'related_statuses_not_sources', 'legal_analysis',
    'legal_analysis_exists', 'source_panel_state', 'citation_verification',
    'deterministic_fallback_answer_used', 'fallback_answer_kind', 'copy_safe_answer',
  ]) {
    check(new RegExp(field + '\\s*:').test(normalizeSrc),
          'normalizeAnswerMetadata() does not default the ' + field + ' field');
  }
}

// Frontend error classification (Part C): the four error classes must exist and
// a render crash must not be reported only as a network/communication error.
check(/function classifyAskError\(/.test(src), 'classifyAskError() error-classifier missing');
check(/frontend_render/.test(src), 'frontend_render error class missing');
check(/frontend_render_error/.test(src), 'frontend_render_error developer-diagnostic record missing');
for (const cls of ['backend_http', 'provider', 'network']) {
  check(new RegExp("'" + cls + "'").test(src), 'error class ' + cls + ' missing from classifyAskError wiring');
}
// appendAiAnswer must be wrapped so a render exception is classified, not leaked
// as a network error.
check(/catch \(renderErr\)/.test(src), 'appendAiAnswer render-exception guard missing');

// ---------------------------------------------------------------------------
// Behavioral: exercise the real renderGroundingSourcePanel against hostile and
// empty metadata. None may throw or leak a "Can't find variable" string.
// ---------------------------------------------------------------------------
function extractConst(name) {
  const re = new RegExp('const\\s+' + name + '\\s*=\\s*', 'g');
  const m = re.exec(src);
  if (!m) return null;
  let i = src.indexOf('{', re.lastIndex);
  if (i < 0) return null;
  let depth = 0;
  for (let j = i; j < src.length; j++) {
    const ch = src[j];
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (depth === 0) return src.slice(m.index, j + 1) + ';'; }
  }
  return null;
}

let renderPanel = null;
try {
  // Minimal document stub so escapeHtml works under node.
  const docStub = { createElement: function () { let _t = ''; return { set textContent(v) { _t = v == null ? '' : String(v); }, get innerHTML() { return _t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); } }; } };
  const deps = ['normalizeAnswerMetadata', 't', 'tt', 'escapeHtml', 'sourceValue',
    'answerBasisText', 'buildAnswerBasisRow', 'answerBasisCommunicatesLimit',
    'buildLawGroundingStatusRow',
    'sourcePanelCopyForState', 'lawSourcePanelMessage', 'mapLawWarningToFriendly',
    'lawVerificationStatus', 'renderGroundingSourcePanel'];
  let code = (extractConst('ANSWER_BASIS_LABELS') || '') + '\n';
  for (const n of deps) { const f = extractFunction(n); if (!f) throw new Error('missing dep ' + n); code += f + '\n'; }
  code += 'return renderGroundingSourcePanel;';
  // eslint-disable-next-line no-eval
  renderPanel = eval('(function(document){' + code + '})')(docStub);
} catch (e) {
  check(false, 'could not assemble renderGroundingSourcePanel harness: ' + e.message);
}

if (renderPanel) {
  const COMBOS = [
    {}, null, undefined,
    { law_grounding_attempted: true },
    { law_grounding_attempted: true, law_grounding_warnings: [] },
    { law_grounding_attempted: true, law_lookup_error_type: 'LAW_API_PARSE_ERROR' },
    { law_grounding_attempted: true, source_family_statuses: { statute: 'no_results' } },
    { law_grounding_attempted: true, legal_analysis: { analysis_mode: 'analogical_analysis' }, legal_analysis_exists: true },
    { law_grounding_attempted: true, source_panel_state: 'totally_unknown_state' },
    { law_grounding_warnings: 'not-an-array', source_family_statuses: ['x'], law_sources: null, citation_verification: 'oops', legal_analysis: 7, parser_status_by_family: 5 },
    { law_grounding_attempted: true, law_grounding_warnings: ['LAW_API_BAD_RESPONSE'], legal_analysis_exists: true, answer_quality_mode: 'source_limited' },
    { deterministic_fallback_answer_used: true, fallback_answer_kind: 'legal_analysis_preparation_note', source_panel_state: 'structured_fallback_available', legal_analysis_exists: true },
  ];
  for (const meta of COMBOS) {
    for (const lang of ['ko', 'en', 'zh', 'zh-tw']) {
      try {
        const html = renderPanel(meta, lang);
        check(typeof html === 'string', 'renderGroundingSourcePanel returned a non-string for ' + JSON.stringify(meta));
        check(!/Can't find variable|is not defined/.test(html), 'renderGroundingSourcePanel leaked a runtime-error string for ' + JSON.stringify(meta));
      } catch (e) {
        check(false, 'renderGroundingSourcePanel threw for meta=' + JSON.stringify(meta) + ' lang=' + lang + ': ' + e.message);
      }
    }
  }
}

// ===========================================================================
// Part H: quota-safety ordering, date rendering, form reload, diagnostic-key
// leakage. Added for fix/ai-rendering-quota-safety.
// ===========================================================================

// --- H-1: useQuota must be called AFTER appendAiAnswer in sendAi ------------
const sendAiSrc = extractFunction('sendAi');
check(Boolean(sendAiSrc), 'could not extract sendAi() from ai.html');
if (sendAiSrc) {
  const body = bodyOf(sendAiSrc);
  const appendPos = body.indexOf('appendAiAnswer(');
  const quotaPos  = body.indexOf('useQuota();');
  check(appendPos >= 0, 'sendAi() does not call appendAiAnswer()');
  check(quotaPos  >= 0, 'sendAi() does not call useQuota()');
  check(quotaPos > appendPos,
        'quota-safety: sendAi() must call useQuota() AFTER appendAiAnswer() — quota must not be consumed before visible render');
}

// --- H-2: formatAnswerText preserves D-2 / E-7 date strings verbatim -------
{
  let formatText = null;
  try {
    const docStub2 = {
      createElement: function () {
        let _t = '';
        return {
          set textContent(v) { _t = v == null ? '' : String(v); },
          get innerHTML() { return _t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
        };
      }
    };
    let code2 = '';
    for (const n of ['escapeHtml', 'inlineFormat', 't', 'formatAnswerText']) {
      const f = extractFunction(n);
      if (!f) throw new Error('missing dep ' + n);
      code2 += f + '\n';
    }
    code2 += 'return formatAnswerText;';
    // eslint-disable-next-line no-eval
    formatText = eval('(function(document){' + code2 + '})')(docStub2);
  } catch (e) {
    check(false, 'could not assemble formatAnswerText harness: ' + e.message);
  }
  if (formatText) {
    const d2Html = formatText('D-2 비자 등록 마감일은 2026-05-28입니다.', 'ko');
    check(d2Html.indexOf('2026-05-28') !== -1,
          'formatAnswerText must preserve D-2 date 2026-05-28 verbatim');
    const e7Html = formatText('E-7 registration deadline: 2026-05-30.', 'en');
    check(e7Html.indexOf('2026-05-30') !== -1,
          'formatAnswerText must preserve E-7 date 2026-05-30 verbatim');
  }
}

// --- H-3: send button must be type="button" and Enter handler must call
//          e.preventDefault() — prevent accidental form-reload on submit. ----
check(/type="button"[^>]*id="sendBtn"|id="sendBtn"[^>]*type="button"/.test(src),
      'sendBtn must have type="button" to prevent accidental form submission / page reload');
check(/e\.preventDefault\(\)[\s\S]{0,120}sendAi\(\)/.test(src),
      'Enter-key handler must call e.preventDefault() before sendAi() to block form submit');

// --- H-4: raw diagnostic keys must NOT appear in user-facing panel HTML -----
// In the node harness devDiagnosticsEnabled is always false (window/localStorage/
// location are all undefined), so the <details> block is suppressed. None of
// the raw internal status codes should appear verbatim in the rendered rows.
if (renderPanel) {
  const diagMeta = {
    law_grounding_attempted: true,
    law_grounding_used: false,
    grounding_used: false,
    law_grounding_warnings: ['LAW_API_BAD_RESPONSE'],
    source_family_statuses: { statute: 'bad_response', enforcement_rule: 'not_attempted' },
    parser_status: 'bad_response',
    answer_quality_mode: 'source_limited',
  };
  for (const lang of ['ko', 'en']) {
    let panelHtml = '';
    try {
      panelHtml = renderPanel(diagMeta, lang);
    } catch (e) {
      check(false, 'renderPanel threw for diagnostic-key leak test (lang=' + lang + '): ' + e.message);
      continue;
    }
    for (const rawKey of ['bad_response', 'not_attempted', 'source_family_statuses', 'law_grounding_warnings']) {
      check(panelHtml.indexOf(rawKey) === -1,
            'raw diagnostic key "' + rawKey + '" must not appear in user-facing panel HTML (lang=' + lang + ')');
    }
  }
}

if (failures.length) {
  console.error('[check_ai_shell_semantics] FAIL:');
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log('[check_ai_shell_semantics] OK — ai.html answer-shell source semantics verified.');
