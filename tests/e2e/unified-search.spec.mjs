// Real-browser tests for the unified search layer (assets/js/unified-search.js).
//
// The layer is an *enhancement* over the existing result renderer, so the load-
// bearing assertions are about what still works when it — or the backend, or the
// AI provider — is unavailable:
//
//   * organic results render before (and without) any AI Overview;
//   * an AI failure leaves a visible quiet-failure card and untouched results;
//   * a backend outage removes the layer entirely and breaks nothing;
//   * ?q= is shareable and back/forward restores state;
//   * 390px never scrolls horizontally;
//   * the page reaches a searched state with zero console errors.
//
// The static server has no backend, so /api/* is routed per-test with
// page.route(). That is the point: it lets each failure mode be exercised
// deterministically instead of hoping the real backend misbehaves.
import { test, expect } from '@playwright/test';

const UNIFIED = '**/api/search/unified';
const AI_OVERVIEW = '**/api/search/unified/ai-overview';
const AI_STREAM = '**/api/search/unified/ai-overview/stream';

// The frontend tries the SSE endpoint first and falls back to the buffered one.
// Unless a test is specifically exercising streaming it aborts the stream, so the
// fallback path is what gets tested — which is also the path most users hit when
// the provider cannot stream.
function stubStream(page) {
  return page.route(AI_STREAM, (route) => route.abort());
}

function sseBody(frames) {
  return frames.map((f) => `event: ${f.event}\ndata: ${JSON.stringify(f.data)}\n\n`).join('');
}

function unifiedBody(overrides = {}) {
  return {
    query: 'D-2-1',
    intent: 'exact_visa_code',
    detectedVisaCodes: ['D-2-1'],
    interpretation: {
      intent: 'exact_visa_code', intentRule: 'code_only', confidence: 'high',
      signals: ['visa_code'], recognizedVisaCodes: ['D-2-1'],
      unrecognizedCodeLikeTokens: [], editable: true
    },
    organicResults: [],
    suggestions: ['D-2-1 체류기간 연장'],
    sourceCards: [{
      id: 'hikorea', title: '하이코리아 (HiKorea)',
      url: 'https://www.hikorea.go.kr', sourceType: 'official_portal', note: '공식 안내'
    }],
    manualEvidence: { status: 'ok', approvedCount: 0, reviewPendingCount: 0 },
    aiOverview: null, aiOverviewStatus: 'pending', fallbackAvailable: true,
    requestId: 'test', latency: { deterministicMs: 5 },
    ...overrides
  };
}

// The hero search form starts hidden (`#searchForm{display:none}`) and is only
// revealed by the gateway toggle, so every UI-driven test has to open it first.
async function openSearch(page, url = '/index.html') {
  await page.goto(url);
  await page.waitForFunction(
    () => {
      try {
        return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10
          && typeof renderResults === 'function';
      } catch (e) { return false; }
    },
    null, { timeout: 30_000 });
  const input = page.locator('#q');
  if (!(await input.isVisible())) {
    await page.locator('#searchToggleBtn').click();
  }
  await expect(input).toBeVisible({ timeout: 10_000 });
  await expect(input).toBeEnabled({ timeout: 10_000 });
  return input;
}

async function submitSearch(page) {
  await page.locator('#searchForm').evaluate((f) =>
    f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 20_000 });
}

async function search(page, query) {
  const input = await openSearch(page);
  await input.fill(query);
  await submitSearch(page);
}

test.describe('organic results never depend on AI', () => {
  test('results render while the AI Overview is still pending', async ({ page }) => {
    await page.route(UNIFIED, (route) =>
      route.fulfill({ json: unifiedBody() }));
    // Hang the overview for the whole test: results must not wait for it.
    await stubStream(page);
    await page.route(AI_OVERVIEW, () => { /* never resolves */ });

    await search(page, 'D-2-1');

    await expect(page.locator('#rlist article.vc, #rlist .es').first()).toBeVisible();
    await expect(page.locator('#unifiedSearchLayer .us-ai.is-loading')).toBeVisible();
  });

  test('an AI failure leaves a visible card and intact results', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.fulfill({
      status: 200,
      json: {
        status: 'unavailable', reason: 'no_provider_configured', overview: null,
        fallbackAvailable: true,
        message: 'AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요.'
      }
    }));

    await search(page, 'D-2-1');

    await expect(page.locator('#unifiedSearchLayer .us-ai.is-unavailable')).toBeVisible();
    await expect(page.locator('#rlist article.vc, #rlist .es').first()).toBeVisible();
  });

  test('a backend outage removes the layer without breaking search', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.abort());
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');

    await expect(page.locator('#rlist article.vc, #rlist .es').first()).toBeVisible();
    await expect(page.locator('#unifiedSearchLayer .us-ai')).toHaveCount(0);
  });

  test('a 500 from the unified endpoint is survivable', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ status: 500, body: 'boom' }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'E-7-4');
    await expect(page.locator('#rlist article.vc, #rlist .es').first()).toBeVisible();
  });
});

test.describe('streamed AI Overview', () => {
  test('deltas render as they arrive, then the verified payload replaces them', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_STREAM, (route) => route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sseBody([
        { event: 'start', data: { status: 'streaming', requestId: 't' } },
        { event: 'delta', data: { text: 'D-2 자격으로 ' } },
        { event: 'delta', data: { text: '졸업 후에는 D-10으로 변경할 수 있어요.' } },
        { event: 'done', data: {
          status: 'ok', overview: 'D-2 자격으로 졸업 후에는 D-10으로 변경할 수 있어요.',
          citationVerification: { failureCount: 0, unverifiableCount: 0 },
          sources: [{ label: '체류매뉴얼 p.412' }]
        } }
      ])
    }));
    // If the stream works the buffered endpoint must never be called.
    let bufferedCalls = 0;
    await page.route(AI_OVERVIEW, (route) => { bufferedCalls += 1; route.abort(); });

    await search(page, 'D-2-1');

    const card = page.locator('#unifiedSearchLayer .us-ai');
    await expect(card).toHaveAttribute('data-us-ai-state', 'ready', { timeout: 15_000 });
    await expect(card).toContainText('D-10으로 변경할 수 있어요');
    expect(bufferedCalls, 'a working stream must not also hit the buffered endpoint')
      .toBe(0);
  });

  test('a stream that reports streaming_not_available falls back to buffered', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_STREAM, (route) => route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sseBody([{ event: 'done', data: {
        status: 'unavailable', reason: 'streaming_not_available', fallbackAvailable: true
      } }])
    }));
    await page.route(AI_OVERVIEW, (route) => route.fulfill({
      status: 200,
      json: { status: 'ok', overview: '버퍼드 요약입니다.',
              citationVerification: { failureCount: 0, unverifiableCount: 0 } }
    }));

    await search(page, 'D-2-1');
    await expect(page.locator('#unifiedSearchLayer .us-ai')).toContainText('버퍼드 요약입니다.');
  });

  test('a stream that dies mid-flight keeps the partial text visible', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    // Frames arrive, then the body ends with no `done` — the card must not blank.
    await page.route(AI_STREAM, (route) => route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sseBody([
        { event: 'start', data: { status: 'streaming' } },
        { event: 'delta', data: { text: '중간까지 도착한 문장' } }
      ])
    }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await expect(page.locator('#unifiedSearchLayer .us-ai')).toContainText('중간까지 도착한 문장');
  });

  test('a blocked stream states the reason', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_STREAM, (route) => route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sseBody([{ event: 'done', data: {
        status: 'blocked', reason: '검색된 근거 0건', fallbackAvailable: true
      } }])
    }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'ㅁㄴㅇㄹ');
    const card = page.locator('#unifiedSearchLayer .us-ai');
    await expect(card).toHaveAttribute('data-us-ai-state', 'blocked', { timeout: 15_000 });
    await expect(card).toContainText('검색된 근거 0건');
  });
});

test.describe('interpretation and evidence labelling', () => {
  test('the interpretation strip shows the detected code', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');

    const strip = page.locator('#unifiedSearchLayer .us-interpret');
    await expect(strip).toBeVisible();
    await expect(strip.locator('.us-chip--code')).toContainText('D-2-1');
  });

  test('an unrecognized code is called out, not rendered as a status', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({
      json: unifiedBody({
        query: 'D-2-99', detectedVisaCodes: ['D-2'],
        interpretation: {
          intent: 'exact_visa_code', intentRule: 'code_only', confidence: 'high',
          signals: [], recognizedVisaCodes: ['D-2'],
          unrecognizedCodeLikeTokens: ['D-2-99'], editable: true
        }
      })
    }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-99');
    await expect(page.locator('#unifiedSearchLayer .us-warn')).toContainText('D-2-99');
  });

  test('review-pending manual evidence is never shown as settled', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({
      json: unifiedBody({
        organicResults: [{
          kind: 'manual_card', title: '체류자격 변경', summary: '발췌…',
          approvalState: 'parsed', usableAsDirectEvidence: false, page: 42,
          matchReason: 'manual_index', score: 300
        }],
        manualEvidence: { status: 'ok', approvedCount: 0, reviewPendingCount: 1 }
      })
    }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, '체류자격 변경');

    const card = page.locator('#unifiedSearchLayer .us-ev').first();
    await expect(card).toBeVisible();
    // The visual bucket says "not settled"…
    await expect(card.locator('.us-ev-state.is-needsreview')).toBeVisible();
    // …and the exact backend state survives the bucketing.
    await expect(card).toHaveAttribute('data-us-evidence-state', 'parsed');
    await expect(card.locator('.us-ev-state.is-verified')).toHaveCount(0);
  });

  test('a repealed statute is not bucketed with verified evidence', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({
      json: unifiedBody({
        organicResults: [{
          kind: 'manual_card', title: '구 출입국관리법 제10조', summary: '발췌…',
          approvalState: 'repealed', usableAsDirectEvidence: false,
          matchReason: 'manual_index', score: 300
        }]
      })
    }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, '출입국관리법 제10조');

    const card = page.locator('#unifiedSearchLayer .us-ev').first();
    await expect(card).toHaveAttribute('data-us-evidence-state', 'repealed');
    await expect(card.locator('.us-ev-state.is-superseded')).toBeVisible();
    await expect(card.locator('.us-ev-state.is-verified')).toHaveCount(0);
  });

  test('official source links are safe anchors', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');

    const link = page.locator('#unifiedSearchLayer .us-sources a').first();
    await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    await expect(link).toHaveAttribute('target', '_blank');
    expect(await link.getAttribute('href')).toMatch(/^https:\/\/(www\.)?(hikorea|law|immigration)\.go\.kr/);
  });

  test('a disallowed source URL never becomes an anchor', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({
      json: unifiedBody({
        sourceCards: [{ id: 'evil', title: 'Not official',
                        url: 'javascript:alert(1)', sourceType: 'official_portal' }]
      })
    }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await expect(page.locator('#unifiedSearchLayer .us-sources a')).toHaveCount(0);
    await expect(page.locator('#unifiedSearchLayer .us-source-link--plain')).toBeVisible();
  });
});

test.describe('URL state', () => {
  test('a search is shareable through ?q=', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await expect(page).toHaveURL(/[?&]q=D-2-1/);
  });

  test('a shared ?q= URL reproduces the search on load', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await openSearch(page, '/index.html?q=D-2-1');
    await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 20_000 });
    await expect(page.locator('#q')).toHaveValue('D-2-1');
  });

  test('back navigation restores the previous query', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await page.locator('#q').fill('E-7-4');
    await submitSearch(page);
    await expect(page).toHaveURL(/[?&]q=E-7-4/);

    await page.goBack();
    await expect(page.locator('#q')).toHaveValue('D-2-1');
  });
});

test.describe('layout, a11y and console hygiene', () => {
  test('390px never scrolls horizontally', async ({ page }) => {
    test.skip(test.info().project.name !== 'mobile-390', 'viewport-specific');
    await page.route(UNIFIED, (route) => route.fulfill({
      json: unifiedBody({
        organicResults: [{
          kind: 'manual_card',
          title: '아주 긴 제목 '.repeat(20),
          summary: '아주 긴 본문 '.repeat(60),
          approvalState: 'parsed', usableAsDirectEvidence: false,
          matchReason: 'manual_index', score: 300
        }]
      })
    }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.fulfill({
      status: 200,
      json: { status: 'ok', overview: '요약 '.repeat(120),
              citationVerification: { failureCount: 0, unverifiableCount: 0 } }
    }));

    await search(page, '체류자격 변경');
    await expect(page.locator('#unifiedSearchLayer .us-interpret')).toBeVisible();

    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('the search input is keyboard reachable and submits with Enter', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    const input = await openSearch(page);
    await input.focus();
    await expect(input).toBeFocused();
    await input.pressSequentially('D-2-1');
    await input.press('Enter');
    await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 20_000 });
  });

  test('the search form exposes its search role and label', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('#searchForm')).toHaveAttribute('role', 'search');
    await expect(page.locator('#q')).toHaveAttribute('aria-label', /.+/);
  });

  test('a completed search logs no console errors', async ({ page }) => {
    const errors = [];
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', (err) => errors.push(String(err)));

    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.fulfill({
      status: 200,
      json: { status: 'ok', overview: '요약입니다.',
              citationVerification: { failureCount: 0, unverifiableCount: 0 } }
    }));

    await search(page, 'D-2-1');
    // `ok` is refined into a specific presentation state, so assert on the
    // state attribute rather than a class that the refinement can change.
    await expect(page.locator('#unifiedSearchLayer .us-ai[data-us-ai-state="ready"]'))
      .toBeVisible();

    // Static-server 404s for optional assets are not app errors.
    const appErrors = errors.filter((e) => !/404|Failed to load resource/i.test(e));
    expect(appErrors, appErrors.join('\n')).toEqual([]);
  });

  test('the layer renders in dark theme', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await stubStream(page);
    await page.route(AI_OVERVIEW, (route) => route.abort());

    const input = await openSearch(page);
    await page.evaluate(() => document.body.setAttribute('data-theme', 'dark'));
    await input.fill('D-2-1');
    await submitSearch(page);

    const strip = page.locator('#unifiedSearchLayer .us-interpret');
    await expect(strip).toBeVisible();
    const bg = await strip.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(bg).not.toBe('rgba(0, 0, 0, 0)');
  });
});
