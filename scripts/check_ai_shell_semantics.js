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

if (failures.length) {
  console.error('[check_ai_shell_semantics] FAIL:');
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log('[check_ai_shell_semantics] OK — ai.html answer-shell source semantics verified.');
