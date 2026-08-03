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

function assertNotEqual(actual, unexpected, message) {
  if (actual === unexpected) {
    throw new Error(`${message || 'values must differ'} — both were ${JSON.stringify(actual)}`);
  }
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

/* ------------------------------- Figma UX-03 Search / Interpretation ------ */
check('the interpretation renders as labelled rows, not a chip strip', () => {
  const html = US.buildInterpretationHtml({
    query: 'D-10', intent: 'exact_visa_code', detectedVisaCodes: ['D-10'],
    interpretation: { confidence: 'high', unrecognizedCodeLikeTokens: [] }
  });
  assert(html.includes('us-interpret-rows'), 'expected the row container');
  assert(html.includes('us-interpret-label'), 'expected a row label');
  assert(html.includes('감지된 비자코드'), 'expected the detected-code row label');
});

check('each row carries its own edit affordance', () => {
  const html = US.buildInterpretationHtml({
    query: 'D-10', intent: 'exact_visa_code', detectedVisaCodes: ['D-10'],
    interpretation: { confidence: 'high', unrecognizedCodeLikeTokens: [] }
  });
  const edits = html.split('data-us-action="edit-query"').length - 1;
  assert(edits >= 2, `expected an edit button per row, got ${edits}`);
});

check('the code row is omitted when nothing was detected', () => {
  const html = US.buildInterpretationHtml({
    query: '체류지 변경', intent: 'procedure_question', detectedVisaCodes: [],
    interpretation: { confidence: 'medium', unrecognizedCodeLikeTokens: [] }
  });
  assert(!html.includes('감지된 비자코드'), 'an empty code row must not render');
  assert(html.includes('하려는 일'), 'the intent row should still render');
});

check('the status-transition row appears only when the backend supplies it', () => {
  const without = US.buildInterpretationHtml({
    query: 'x', intent: 'visa_situation', detectedVisaCodes: [],
    interpretation: { confidence: 'low', unrecognizedCodeLikeTokens: [] }
  });
  assert(!without.includes('현재 → 목표 상태'),
    'the transition row must not be invented when there is no data');

  const withData = US.buildInterpretationHtml({
    query: 'x', intent: 'visa_situation', detectedVisaCodes: [],
    interpretation: {
      confidence: 'low', unrecognizedCodeLikeTokens: [],
      statusTransition: { from: 'D-2', to: 'D-10' }
    }
  });
  assert(withData.includes('현재 → 목표 상태'), 'the transition row should render with data');
  assert(withData.includes('D-2') && withData.includes('D-10'));
});

check('a half-populated transition is not rendered', () => {
  const html = US.buildInterpretationHtml({
    query: 'x', intent: 'visa_situation', detectedVisaCodes: [],
    interpretation: {
      confidence: 'low', unrecognizedCodeLikeTokens: [],
      statusTransition: { from: 'D-2' }
    }
  });
  assert(!html.includes('현재 → 목표 상태'), 'a transition missing `to` must not render');
});

check('confidence renders its three levels and nothing else', () => {
  assert(US.buildConfidenceHtml('high').includes('확신도 높음'));
  assert(US.buildConfidenceHtml('medium').includes('is-medium'));
  assert(US.buildConfidenceHtml('low').includes('is-low'));
  assertEqual(US.buildConfidenceHtml('none'), '', 'unknown level renders nothing');
  assertEqual(US.buildConfidenceHtml(undefined), '');
});

check('the unrecognized-code warning stays above the rows', () => {
  const html = US.buildInterpretationHtml({
    query: 'D-2-99', intent: 'exact_visa_code', detectedVisaCodes: ['D-2'],
    interpretation: { confidence: 'high', unrecognizedCodeLikeTokens: ['D-2-99'] }
  });
  assert(html.indexOf('us-warn') < html.indexOf('us-interpret-rows'),
    'the warning must precede the interpreted rows');
});

check('a status transition from upstream is escaped', () => {
  const html = US.buildInterpretationHtml({
    query: 'x', intent: 'visa_situation', detectedVisaCodes: [],
    interpretation: {
      confidence: 'low', unrecognizedCodeLikeTokens: [],
      statusTransition: { from: '<img src=x onerror=alert(1)>', to: 'D-10' }
    }
  });
  assert(!html.includes('<img'), 'transition values must be escaped');
});

/* ------------------------------------------------- evidence labelling ---- */
check('review-pending manual cards are labelled, never shown as settled', () => {
  const html = US.buildExtraResultsHtml([
    { kind: 'manual_card', title: '체류자격 변경', summary: '…',
      approvalState: 'parsed', usableAsDirectEvidence: false, page: 42 }
  ]);
  assert(html.includes('is-approval-parsed'), 'missing the needs-review state');
  assert(!html.includes('is-approval-approved'), 'unreviewed content must not read as approved');
});

check('approved manual cards read as approved', () => {
  const html = US.buildExtraResultsHtml([
    { kind: 'manual_card', title: 'x', summary: 'y',
      approvalState: 'approved', usableAsDirectEvidence: true }
  ]);
  assert(html.includes('is-approval-approved'), 'approved content should read as approved');
  assert(!html.includes('is-approval-parsed'));
});

/* ---------- contract §3.6 — four scales that must not share one ramp ------ */
check('every backend state is filed under exactly one scale', () => {
  const expected = {
    approved: 'approval', parsed: 'approval', needs_review: 'approval',
    draft: 'approval', superseded: 'approval', rejected: 'approval',
    verified: 'lifecycle', repealed: 'lifecycle', scheduled: 'lifecycle',
    ambiguous: 'lifecycle', not_found: 'lifecycle',
    unavailable: 'lookup', forbidden: 'lookup', timeout: 'lookup',
    parse_failed: 'lookup',
    related: 'relevance', background: 'relevance'
  };
  for (const [backend, scale] of Object.entries(expected)) {
    assertEqual(US.evidenceScale(backend), scale, `scale for ${backend}`);
  }
  // No state may appear in two scales.
  const seen = new Map();
  for (const [scale, members] of Object.entries(US.EVIDENCE_SCALES)) {
    for (const state of Object.keys(members)) {
      assert(!seen.has(state), `${state} appears in both ${seen.get(state)} and ${scale}`);
      seen.set(state, scale);
    }
  }
});

check('the four scales never share a visual value', () => {
  // Namespacing the value by scale is what makes a shared CSS rule impossible.
  const values = new Set();
  for (const members of Object.values(US.EVIDENCE_SCALES)) {
    for (const state of Object.keys(members)) {
      const v = US.evidenceVisualState(state);
      assert(!values.has(v), `visual value ${v} is reused across scales`);
      values.add(v);
    }
  }
});

check('approval "approved" and lifecycle "verified" are not the same badge', () => {
  // A human signing off on a manual extract and a statute being in force are
  // different claims about different things.
  assert(US.evidenceScale('approved') !== US.evidenceScale('verified'));
  assertNotEqual(US.evidenceVisualState('approved'), US.evidenceVisualState('verified'));
  const a = US.buildEvidenceCardHtml({ type: 'manual', title: 'x', state: 'approved' });
  const v = US.buildEvidenceCardHtml({ type: 'statute', title: 'y', state: 'verified' });
  assert(a.includes('data-us-evidence-scale="approval"'));
  assert(v.includes('data-us-evidence-scale="lifecycle"'));
});

check('a repealed statute is not the same badge as a superseded manual', () => {
  // "No longer law" and "a newer manual exists" are different facts.
  assert(US.evidenceScale('repealed') !== US.evidenceScale('superseded'));
  assertNotEqual(US.evidenceVisualState('repealed'), US.evidenceVisualState('superseded'));
  const html = US.buildEvidenceCardHtml({
    type: 'statute', title: '출입국관리법', state: 'repealed' });
  assert(html.includes('is-lifecycle-repealed'));
  assert(!html.includes('is-lifecycle-verified'), 'a repealed statute must not read as in force');
});

check('"not found" and "could not check" are different claims', () => {
  // Contract §3.6 names this pair explicitly.
  assertEqual(US.evidenceScale('not_found'), 'lifecycle');
  assertEqual(US.evidenceScale('unavailable'), 'lookup');
  assertNotEqual(US.evidenceVisualState('not_found'), US.evidenceVisualState('unavailable'));
  assertNotEqual(US.evidenceStateLabel('not_found'), US.evidenceStateLabel('unavailable'));
});

check('every lookup failure is neutral and stays in its own scale', () => {
  for (const failure of ['forbidden', 'timeout', 'parse_failed', 'unavailable']) {
    assertEqual(US.evidenceScale(failure), 'lookup', failure);
    const html = US.buildEvidenceCardHtml({ type: 'statute', title: 'x', state: failure });
    assert(html.includes('data-us-evidence-scale="lookup"'), failure);
    // A failed lookup is not a judgement about the source.
    assert(!html.includes('is-approval-'), `${failure} leaked into the approval scale`);
    assert(!html.includes('is-lifecycle-'), `${failure} leaked into the lifecycle scale`);
  }
});

check('each state gets its own words, not a shared bucket label', () => {
  const labels = new Set();
  for (const s of ['approved', 'verified', 'superseded', 'repealed', 'not_found',
                   'unavailable', 'forbidden', 'timeout', 'parse_failed']) {
    labels.add(US.evidenceStateLabel(s));
  }
  assertEqual(labels.size, 9, 'distinct states collapsed onto the same label');
});

check('the precise backend state is preserved on the element', () => {
  const html = US.buildEvidenceCardHtml({
    type: 'statute', title: '출입국관리법', state: 'forbidden' });
  assert(html.includes('data-us-evidence-state="forbidden"'),
    'the exact reason must survive rendering');
  assert(html.includes('data-us-evidence-scale="lookup"'), 'the scale must be carried too');
});

check('an unknown state is not filed under a scale it may not belong to', () => {
  assertEqual(US.evidenceScale('brand_new_state'), 'unknown');
  assertEqual(US.evidenceVisualState('brand_new_state'), 'unknown');
  assertEqual(US.evidenceVisualState(undefined), 'unknown');
  const html = US.buildEvidenceCardHtml({ type: 'statute', title: 'x', state: 'brand_new' });
  assert(!html.includes('is-approval-'), 'unknown state borrowed the approval scale');
  assert(!html.includes('is-lifecycle-'), 'unknown state borrowed the lifecycle scale');
});

check('an evidence card with an official URL becomes a safe anchor', () => {
  const html = US.buildEvidenceCardHtml({
    type: 'statute', title: '출입국관리법', state: 'verified',
    url: 'https://www.law.go.kr/x' });
  assert(html.includes('<a '), 'expected an anchor');
  assert(html.includes('rel="noopener noreferrer"'));
  assert(html.includes('us-ev-ext'), 'expected the external-link mark');
});

check('an evidence card with a disallowed URL is not an anchor', () => {
  const html = US.buildEvidenceCardHtml({
    type: 'manual', title: 'x', state: 'parsed', url: 'javascript:alert(1)' });
  assert(!html.includes('<a '), 'a disallowed URL must not become an anchor');
  assert(!html.includes('us-ev-ext'), 'no external mark without a usable link');
});

check('evidence card content is escaped', () => {
  const html = US.buildEvidenceCardHtml({
    type: 'manual', title: '<img src=x onerror=alert(1)>',
    subtitle: '<b>s</b>', state: 'parsed' });
  assert(!html.includes('<img'), 'title must be escaped');
  assert(!html.includes('<b>s</b>'), 'subtitle must be escaped');
});

check('an evidence card with no title renders nothing', () => {
  assertEqual(US.buildEvidenceCardHtml({ type: 'manual', state: 'parsed' }), '');
  assertEqual(US.buildEvidenceCardHtml(null), '');
});

check('each source type gets its own avatar glyph', () => {
  const seen = new Set();
  for (const type of ['manual', 'statute', 'decree', 'rule', 'precedent']) {
    const html = US.buildEvidenceCardHtml({ type, title: 't', state: 'verified' });
    const m = html.match(/us-ev-avatar"[^>]*>([^<]+)</);
    assert(m, `no avatar for ${type}`);
    seen.add(m[1]);
  }
  assertEqual(seen.size, 5, 'each type should be visually distinguishable');
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

/* -------------------------------------------- UX-03 Search / Suggestion Row */
check('a bare string suggestion still renders as a row', () => {
  const html = US.buildSuggestionsHtml(['D-2 체류기간 연장']);
  assert(html.includes('us-sug'), 'string suggestion did not render a row');
  assert(html.includes('data-us-query="D-2 체류기간 연장"'), 'query attribute lost');
});

check('a typed suggestion keeps its type and both text lines', () => {
  const html = US.buildSuggestionRowHtml({
    type: 'legal_source', query: '출입국관리법 제20조',
    label: '출입국관리법 제20조', sublabel: '법령 원문으로 확인'
  });
  assert(html.includes('data-us-suggest-type="legal_source"'), 'type attribute missing');
  assert(html.includes('us-sug-title'), 'primary line missing');
  assert(html.includes('us-sug-sub'), 'secondary line missing');
  assert(html.includes('법령 원문으로 확인'), 'secondary text lost');
});

check('a row with no sublabel renders no empty secondary line', () => {
  const html = US.buildSuggestionRowHtml({ type: 'procedure', query: '체류기간 연장' });
  assert(html.includes('us-sug-title'), 'primary line missing');
  assert(!html.includes('us-sug-sub'), 'empty secondary line rendered anyway');
});

check('an unknown suggestion type claims no category at all', () => {
  assertEqual(US.suggestionType('legal_source'), 'legal_source');
  for (const input of ['made_up_kind', '', undefined, null, 42]) {
    assertEqual(US.suggestionType(input), US.SUGGEST_UNTYPED);
  }
  const html = US.buildSuggestionRowHtml({ type: 'made_up_kind', query: 'x' });
  assert(!html.includes('legal_source'), 'unknown type borrowed a real category');
  assert(!html.includes('recent_query'), 'unknown type was filed under history');
  // No chip rather than a guessed one.
  assert(!html.includes('us-sug-badge'), 'unknown type rendered a category chip');
  assert(html.includes('<svg'), 'unknown type lost its glyph');
});

check('a bare string suggestion claims no category either', () => {
  const html = US.buildSuggestionRowHtml('체류기간 연장');
  assert(html.includes(`data-us-suggest-type="${US.SUGGEST_UNTYPED}"`),
    'a plain string was assigned a category it never declared');
  assert(!html.includes('us-sug-badge'), 'a plain string got a category chip');
});

check('every design suggestion type has a glyph and a distinct badge label', () => {
  const labels = new Set();
  for (const type of US.SUGGEST_TYPES) {
    const html = US.buildSuggestionRowHtml({ type, query: 'q', label: 'q' });
    assert(html.includes('<svg'), `${type} row has no glyph`);
    assert(html.includes('us-sug-badge'), `${type} row has no badge`);
    const label = US.suggestionBadgeLabel(type);
    assert(label && label !== type, `${type} badge fell through to the raw key`);
    labels.add(label);
  }
  // visa_code and visa_status intentionally share the 체류자격 chip.
  assertEqual(labels.size, US.SUGGEST_TYPES.length - 1);
  assertEqual(US.suggestionBadgeLabel(US.SUGGEST_UNTYPED), '');
});

check('a correction row is a suggestion, never a status card', () => {
  const html = US.buildSuggestionRowHtml({
    type: 'correction', query: 'D-2',
    label: '혹시 “D-2” 을(를) 찾으셨나요?',
    sublabel: '입력하신 “D-2-99” 은(는) 보유한 체류자격 목록에 없습니다'
  });
  assert(html.includes('data-us-suggest-type="correction"'), 'correction type lost');
  assert(!html.includes('us-card'), 'correction rendered as a result card');
  assert(html.includes('D-2-99'), 'the typed token is not named back to the user');
});

check('suggestion text is escaped in both lines', () => {
  const html = US.buildSuggestionRowHtml({
    type: 'procedure', query: 'q',
    label: '<img src=x onerror=alert(1)>',
    sublabel: '"><script>bad()</script>'
  });
  assert(!html.includes('<img'), 'primary line injected raw markup');
  assert(!html.includes('<script>'), 'secondary line injected raw markup');
});

check('inner mode omits the button so it can nest in an existing one', () => {
  const row = { type: 'visa_code', query: 'D-2', label: 'D-2' };
  const inner = US.buildSuggestionRowHtml(row, { inner: true });
  assert(!inner.includes('<button'), 'inner mode still emitted a button');
  assert(inner.includes('us-sug-avatar'), 'inner mode dropped the row content');
  assert(US.buildSuggestionRowHtml(row).includes('<button'), 'default mode lost its button');
});

check('inner mode accepts pre-escaped highlight markup for the title only', () => {
  const inner = US.buildSuggestionRowHtml(
    { type: 'visa_code', query: 'D-2', label: 'D-2 유학', sublabel: '<b>x</b>' },
    { inner: true, labelHtml: '<mark class="h">D-2</mark> 유학' }
  );
  assert(inner.includes('<mark class="h">'), 'highlight markup was escaped away');
  assert(!inner.includes('<b>x</b>'), 'sublabel bypassed escaping');
});

check('a suggestion with no query is dropped rather than rendered blank', () => {
  assertEqual(US.buildSuggestionRowHtml({ type: 'procedure', query: '' }), '');
  assertEqual(US.buildSuggestionRowHtml(''), '');
  assertEqual(US.buildSuggestionRowHtml(null), '');
  assertEqual(US.buildSuggestionsHtml([null, '', { query: '' }]), '');
});

check('the composed layer prefers typed rows over the string list', () => {
  const html = US.buildUnifiedLayerHtml({
    query: 'D-2', intent: 'exact_visa_code', detectedVisaCodes: ['D-2'],
    interpretation: { unrecognizedCodeLikeTokens: [] },
    organicResults: [],
    suggestionRows: [{ type: 'legal_source', query: '출입국관리법 제20조', label: '출입국관리법 제20조' }],
    suggestions: ['ignored fallback']
  }, 'hidden', null);
  assert(html.includes('data-us-suggest-type="legal_source"'), 'typed rows were not used');
  assert(!html.includes('ignored fallback'), 'string list rendered alongside typed rows');
});

/* --- UX-10 Spec / Behavior & A11y (node 447:4) ---------------------------
 * Three rules the spec names that this layer did not satisfy. They are checked
 * against the shipped files, not against a description of them.
 */
const indexHtml = readFileSync(join(REPO_ROOT, 'index.html'), 'utf8');

check('the results layer reports busy while a search is in flight', () => {
  const fn = source.slice(source.indexOf('function setSearchBarState'));
  const body = fn.slice(0, fn.indexOf('\n  }'));
  assert(/aria-busy/.test(body), 'setSearchBarState does not touch aria-busy');
  assert(/state === 'loading' \? 'true' : 'false'/.test(body),
    'aria-busy is not derived from the same state the bar shows — the two can drift');
  // ensureMount, not a lookup: the layer does not exist until the first render,
  // which is after the request resolves — so a lookup silently no-ops on the
  // very first search, the longest wait there is.
  assert(/ensureMount\(\)/.test(body),
    'aria-busy is set via a lookup, so the first search announces no busy state');
});

check('the layer\'s Korean prose does not break mid-word', () => {
  // Every `.us-*` rule that sizes text should either keep Korean words whole or
  // be a short label that cannot wrap. Rather than police all of them, assert
  // the prose-bearing set is covered — those are the ones that hold sentences.
  const prose = ['.us-ai-body', '.us-card-summary', '.us-ev-sub', '.us-warn',
    '.us-interpret-value', '.us-sug-sub', '.us-source-note'];
  const rule = indexHtml.match(/\.us-interpret-value[^{]*\{[^}]*word-break:\s*keep-all[^}]*\}/);
  assert(rule, 'no keep-all rule covers the layer prose');
  for (const sel of prose) {
    assert(rule[0].includes(sel) || new RegExp(`\\${sel}[^{]*\\{[^}]*keep-all`).test(indexHtml),
      `${sel} can break a Korean word mid-syllable`);
  }
  assert(/keep-all;\s*\n?\s*overflow-wrap:\s*anywhere/.test(rule[0]),
    'keep-all without an overflow-wrap escape hatch — a long URL will overflow its card');
});

check('the first tab stop skips to the main content', () => {
  const body = indexHtml.slice(indexHtml.indexOf('<body'));
  const link = body.match(/<a class="skip-link"[^>]*>/);
  assert(link, 'no skip link');
  assert(/href="#mainContent"/.test(link[0]), 'skip link does not point at #mainContent');
  assert(indexHtml.includes('id="mainContent"'), 'skip-link target does not exist');
  assert(/data-i18n="skipToContent"/.test(link[0]), 'skip link is not translated');
  // It has to be genuinely first: anything focusable before it makes it useless.
  const before = body.slice(0, body.indexOf('<a class="skip-link"'));
  assert(!/<(a|button|input|select|textarea)\b/i.test(before),
    'a focusable element precedes the skip link, so it is not the first tab stop');
  // display:none / visibility:hidden would make it unfocusable — i.e. not a link.
  const css = indexHtml.match(/\.skip-link\s*\{[^}]*\}/);
  assert(css && !/display:\s*none|visibility:\s*hidden/.test(css[0]),
    'skip link is hidden in a way that removes it from the tab order');
  assert(/\.skip-link:focus-visible\s*\{[^}]*transform:\s*translateY\(0\)/.test(indexHtml),
    'skip link never becomes visible on focus');
});

/* ----------------------------------------------------------- report ------ */
if (failures.length) {
  console.error(`\nFAIL — ${failures.length} check(s) failed, ${passed} passed:\n`);
  for (const failure of failures) console.error(`  ✗ ${failure}`);
  process.exit(1);
}
console.log(`unified-search: ${passed} checks passed`);
