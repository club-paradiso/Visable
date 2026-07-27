/*
 * check_unified_search.mjs
 * ----------------------------------------------------------------------------
 * Unit tests for the pure builders in assets/js/unified-search.js.
 *
 * Runs in plain Node with no jsdom: the module exposes its builders on
 * globalThis BEFORE the `typeof document === 'undefined'` guard, exactly like
 * the other Paradiso standalone modules.
 *
 * Focus: XSS containment, official-URL allow-listing, AI-failure states that
 * stay visible, review-pending labelling, and shareable-URL round-tripping.
 *
 *   node scripts/check_unified_search.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

// Load the IIFE. `document` is undefined here, so DOM wiring is skipped.
const source = readFileSync(join(REPO_ROOT, 'assets/js/unified-search.js'), 'utf8');
// eslint-disable-next-line no-new-func
new Function(source)();

const US = globalThis.ParadisoUnifiedSearch;

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'assertion failed');
}

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`${message || 'not equal'} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

/* ------------------------------------------------------------- module ---- */
check('module exposes its pure builders', () => {
  assert(US, 'ParadisoUnifiedSearch is not defined');
  for (const fn of ['escapeHtml', 'safeOfficialUrl', 'buildInterpretationHtml',
                    'buildAiOverviewHtml', 'buildSourceCardsHtml', 'buildUnifiedLayerHtml',
                    'classifyAiResponse', 'readQueryFromUrl', 'buildShareableUrl']) {
    assert(typeof US[fn] === 'function', `missing builder: ${fn}`);
  }
});

/* --------------------------------------------------------------- XSS ----- */
check('escapeHtml neutralizes markup', () => {
  assertEqual(US.escapeHtml('<script>alert(1)</script>'),
    '&lt;script&gt;alert(1)&lt;/script&gt;');
  assertEqual(US.escapeHtml(`"'&`), '&quot;&#39;&amp;');
  assertEqual(US.escapeHtml(null), '');
});

check('a script tag in a backend string never reaches the DOM as markup', () => {
  const html = US.buildInterpretationHtml({
    query: 'x',
    intent: 'unknown',
    detectedVisaCodes: ['<img src=x onerror=alert(1)>'],
    interpretation: { unrecognizedCodeLikeTokens: [] }
  });
  assert(!html.includes('<img'), 'raw <img> leaked into the interpretation strip');
  assert(html.includes('&lt;img'), 'the value should appear escaped');
});

check('AI overview text is escaped, not injected', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: '<b>bold</b> and <script>bad()</script>',
    citationVerification: {}
  });
  assert(!html.includes('<script>'), 'script tag leaked from AI text');
  assert(!html.includes('<b>bold</b>'), 'raw markup leaked from AI text');
});

check('source card titles and notes are escaped', () => {
  const html = US.buildSourceCardsHtml([
    { id: 'x', title: '<svg onload=alert(1)>', url: 'https://www.law.go.kr', note: '<i>n</i>' }
  ]);
  assert(!html.includes('<svg'), 'raw <svg> leaked');
  assert(!html.includes('<i>n</i>'), 'raw note markup leaked');
});

/* ----------------------------------------------------- URL allow-list ---- */
check('official government https URLs are allowed', () => {
  assert(US.safeOfficialUrl('https://www.law.go.kr/x'), 'law.go.kr should be allowed');
  assert(US.safeOfficialUrl('https://www.hikorea.go.kr/'), 'hikorea should be allowed');
});

check('javascript: and data: URLs are rejected', () => {
  assertEqual(US.safeOfficialUrl('javascript:alert(1)'), '');
  assertEqual(US.safeOfficialUrl('data:text/html,<script>x</script>'), '');
});

check('plain http and unknown hosts are rejected', () => {
  assertEqual(US.safeOfficialUrl('http://www.law.go.kr'), '', 'http must be rejected');
  assertEqual(US.safeOfficialUrl('https://evil.example.com'), '');
  assertEqual(US.safeOfficialUrl('//evil.example.com'), '');
  assertEqual(US.safeOfficialUrl(''), '');
});

check('a rejected URL degrades to plain text, never to an anchor', () => {
  const html = US.buildSourceCardsHtml([{ id: 'x', title: 'T', url: 'javascript:alert(1)' }]);
  assert(!html.includes('<a '), 'a disallowed URL must not become an anchor');
  assert(html.includes('us-source-link--plain'), 'expected the plain-text fallback');
});

check('allowed anchors carry rel="noopener noreferrer"', () => {
  const html = US.buildSourceCardsHtml([{ id: 'x', title: 'T', url: 'https://www.law.go.kr' }]);
  assert(html.includes('rel="noopener noreferrer"'), 'missing rel hardening');
  assert(html.includes('target="_blank"'), 'expected target=_blank');
});

/* ------------------------------------------------- AI failure states ----- */
check('AI response classification covers every backend status', () => {
  assertEqual(US.classifyAiResponse({ status: 'ok', overview: 'text' }, true), 'ok');
  assertEqual(US.classifyAiResponse({ status: 'unavailable' }, true), 'unavailable');
  assertEqual(US.classifyAiResponse({ status: 'no_evidence' }, true), 'no_evidence');
  assertEqual(US.classifyAiResponse({ status: 'not_applicable' }, true), 'hidden');
  assertEqual(US.classifyAiResponse(null, false), 'unavailable');
  assertEqual(US.classifyAiResponse({ status: 'ok' }, true), 'unavailable',
    'status ok with no overview text is not a usable overview');
});

check('an AI failure renders a visible card rather than disappearing', () => {
  const html = US.buildAiOverviewHtml('unavailable', null);
  assert(html.includes('us-ai'), 'the failure state must still render a card');
  assert(html.includes('is-unavailable'), 'missing the unavailable modifier');
  assert(html.length > 80, 'the failure card must carry an explanation');
});

check('loading state shows a skeleton and says results are already available', () => {
  const html = US.buildAiOverviewHtml('loading', null);
  assert(html.includes('us-ai-skeleton'), 'expected a loading skeleton');
  assert(html.includes('is-loading'), 'missing the loading modifier');
});

check('hidden state renders nothing at all', () => {
  assertEqual(US.buildAiOverviewHtml('hidden', null), '');
});

check('an unverified citation raises a visible warning on the overview', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: '출입국관리법 제20조에 따릅니다.',
    citationVerification: { failureCount: 0, unverifiableCount: 1 }
  });
  assert(html.includes('us-ai-banner--citation'), 'expected a citation warning banner');
  assert(html.includes('data-us-ai-state="citation_failed"'), 'expected the citation_failed state');
});

check('a fully verified overview shows no citation warning', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text',
    citationVerification: { failureCount: 0, unverifiableCount: 0 }
  });
  assert(!html.includes('us-ai-banner--citation'), 'unexpected citation warning');
});

/* ------------------------------------------ Figma UX-03 AI Overview states -- */
check('streaming renders the partial text with a caret', () => {
  const html = US.buildAiOverviewHtml('streaming', { overview: '작성 중인 문장' });
  assert(html.includes('us-ai-caret'), 'expected a streaming caret');
  assert(html.includes('작성 중인 문장'), 'expected the partial text');
  assert(html.includes('data-us-ai-state="streaming"'));
});

check('blocked states the reason instead of pretending to answer', () => {
  const html = US.buildAiOverviewHtml('blocked', {
    message: '요약을 제공하지 않았습니다.', reason: '근거 부족'
  });
  assert(html.includes('data-us-ai-state="blocked"'));
  assert(html.includes('근거 부족'), 'expected the reason to be shown');
});

check('legacy no_evidence maps onto the blocked state', () => {
  const html = US.buildAiOverviewHtml('no_evidence', {});
  assert(html.includes('data-us-ai-state="blocked"'), 'no_evidence should render as blocked');
});

check('a degraded law lookup downgrades ready to partial_sources', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text', evidenceState: { law: 'timeout', manual: 'approved_direct' }
  });
  assert(html.includes('data-us-ai-state="partial_sources"'));
});

check('review-pending-only manual evidence is a partial source set', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text', evidenceState: { law: 'verified', manual: 'review_pending_only' }
  });
  assert(html.includes('data-us-ai-state="partial_sources"'));
});

check('official confirmation raises the amber banner', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text', requiresOfficialConfirmation: true
  });
  assert(html.includes('us-ai-banner--confirm'), 'expected the confirm banner');
  assert(html.includes('data-us-ai-state="official_confirm_required"'));
});

check('an unverified citation outranks a partial source set', () => {
  // Both conditions true: the citation caution is the stronger claim and wins.
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text',
    citationVerification: { unverifiableCount: 1 },
    evidenceState: { law: 'timeout' },
    requiresOfficialConfirmation: true
  });
  assert(html.includes('data-us-ai-state="citation_failed"'));
});

check('state refinement never upgrades a failure into a success', () => {
  for (const failing of ['unavailable', 'blocked', 'loading']) {
    assertEqual(US.resolveAiOverviewState(failing, { overview: 'x' }), failing);
  }
});

check('unretrieved sources are dimmed, never dropped', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text',
    sources: [{ label: '체류매뉴얼 p.412' }, { label: '판례', unavailable: true }]
  });
  assert(html.includes('is-muted'), 'expected the unavailable source to be dimmed');
  assert(html.includes('판례'), 'the unavailable source must still be listed');
});

check('next steps render as a numbered list', () => {
  const html = US.buildAiOverviewHtml('ok', {
    overview: 'text', nextSteps: ['D-10 변경 서류 확인', 'HiKorea 방문 예약']
  });
  assert(html.includes('us-ai-step-num'), 'expected numbered step badges');
  assert(html.includes('HiKorea 방문 예약'));
});

check('unavailable offers a retry action', () => {
  const html = US.buildAiOverviewHtml('unavailable', null);
  assert(html.includes('data-us-action="retry-overview"'), 'expected a retry affordance');
});

check('every non-hidden state keeps the official-confirmation line', () => {
  for (const state of ['loading', 'streaming', 'ok', 'unavailable', 'blocked']) {
    const html = US.buildAiOverviewHtml(state, { overview: 'text' });
    assert(html.includes('us-ai-confirm'), `missing confirm line in ${state}`);
  }
});

check('streaming status with no text yet falls back to loading', () => {
  assertEqual(US.classifyAiResponse({ status: 'streaming' }, true), 'loading');
  assertEqual(US.classifyAiResponse({ status: 'streaming', overview: 'partial' }, true), 'streaming');
});

check('blocked status is classified, not collapsed into unavailable', () => {
  assertEqual(US.classifyAiResponse({ status: 'blocked' }, true), 'blocked');
});

/* ------------------------------------------------- evidence labelling ---- */
check('review-pending manual cards are labelled, never shown as settled', () => {
  const html = US.buildExtraResultsHtml([
    { kind: 'manual_card', title: '체류자격 변경', summary: '…',
      approvalState: 'parsed', usableAsDirectEvidence: false, page: 42 }
  ]);
  assert(html.includes('us-badge--review'), 'missing the 검토 전 badge');
});

check('approved manual cards carry no review badge', () => {
  const html = US.buildExtraResultsHtml([
    { kind: 'manual_card', title: 'x', summary: 'y',
      approvalState: 'approved', usableAsDirectEvidence: true }
  ]);
  assert(!html.includes('us-badge--review'), 'approved content must not be badged 검토 전');
});

check('unrecognized code-like tokens are surfaced as not-found', () => {
  const html = US.buildInterpretationHtml({
    query: 'D-2-99', intent: 'unknown', detectedVisaCodes: [],
    interpretation: { unrecognizedCodeLikeTokens: ['D-2-99'] }
  });
  assert(html.includes('us-warn'), 'expected an unrecognized-code warning');
  assert(html.includes('D-2-99'), 'the token itself should be named');
});

check('the manual review-pending source card is rendered without a link', () => {
  const html = US.buildSourceCardsHtml([
    { id: 'manual_review_pending', title: '매뉴얼 본문 (검토 전)', url: '',
      sourceType: 'manual_review_pending', note: 'n' }
  ]);
  assert(html.includes('us-badge--review'), 'missing the review badge');
  assert(!html.includes('<a '), 'a card with no URL must not become an anchor');
});

/* ------------------------------------------------------- URL sharing ----- */
check('a query round-trips through the shareable URL', () => {
  const url = US.buildShareableUrl('https://example.com/index.html', 'D-2-1');
  assert(url.includes('q=D-2-1'), `expected q=D-2-1 in ${url}`);
  assertEqual(US.readQueryFromUrl('https://example.com/index.html?q=D-2-1'), 'D-2-1');
});

check('Korean queries survive the URL round-trip', () => {
  const url = US.buildShareableUrl('https://example.com/', '체류지 변경');
  assertEqual(US.readQueryFromUrl('https://example.com/' + url.slice(url.indexOf('?'))),
    '체류지 변경');
});

check('an empty query clears the parameter', () => {
  const url = US.buildShareableUrl('https://example.com/?q=old', '');
  assert(!url.includes('q='), `expected q to be dropped, got ${url}`);
});

check('a malformed href never throws', () => {
  assertEqual(US.readQueryFromUrl(null), '');
  assertEqual(US.readQueryFromUrl('%%%'), '');
});

check('an over-long query is truncated at the documented ceiling', () => {
  const long = 'a'.repeat(5000);
  const url = US.buildShareableUrl('https://example.com/', long);
  assert(US.readQueryFromUrl('https://example.com/' + url.slice(url.indexOf('?'))).length
    <= US.MAX_QUERY, 'query exceeded MAX_QUERY');
});

/* ------------------------------------------------------ full composition -- */
check('the composed layer is empty for an empty query', () => {
  assertEqual(US.buildUnifiedLayerHtml({ query: '' }, 'hidden', null), '');
  assertEqual(US.buildUnifiedLayerHtml(null, 'hidden', null), '');
});

check('the composed layer renders without an AI overview', () => {
  const html = US.buildUnifiedLayerHtml({
    query: 'D-2-1', intent: 'exact_visa_code', detectedVisaCodes: ['D-2-1'],
    interpretation: { unrecognizedCodeLikeTokens: [] },
    organicResults: [], suggestions: ['D-2-1 체류기간 연장'],
    sourceCards: [{ id: 'hikorea', title: 'HiKorea', url: 'https://www.hikorea.go.kr' }]
  }, 'hidden', null);
  assert(html.includes('us-interpret'), 'interpretation strip missing');
  assert(html.includes('us-sources'), 'source panel missing');
  assert(!html.includes('us-ai'), 'no AI card should render in the hidden state');
});

check('suggestion chips carry their query as data, not as markup', () => {
  const html = US.buildSuggestionsHtml(['"><script>x</script>']);
  assert(!html.includes('<script>'), 'suggestion injected raw markup');
  assert(html.includes('data-us-query='), 'suggestion missing its data attribute');
});

/* ----------------------------------------------------------- report ------ */
if (failures.length) {
  console.error(`\nFAIL — ${failures.length} check(s) failed, ${passed} passed:\n`);
  for (const failure of failures) console.error(`  ✗ ${failure}`);
  process.exit(1);
}
console.log(`unified-search: ${passed} checks passed`);
