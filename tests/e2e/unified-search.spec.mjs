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

async function search(page, query) {
  await page.goto('/index.html');
  const input = page.locator('#q');
  await expect(input).toBeEnabled({ timeout: 20_000 });
  await input.fill(query);
  await page.locator('#searchForm').evaluate((f) =>
    f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
  await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 20_000 });
}

test.describe('organic results never depend on AI', () => {
  test('results render while the AI Overview is still pending', async ({ page }) => {
    await page.route(UNIFIED, (route) =>
      route.fulfill({ json: unifiedBody() }));
    // Hang the overview for the whole test: results must not wait for it.
    await page.route(AI_OVERVIEW, () => { /* never resolves */ });

    await search(page, 'D-2-1');

    await expect(page.locator('#rlist .rc, #rlist .es').first()).toBeVisible();
    await expect(page.locator('#unifiedSearchLayer .us-ai.is-loading')).toBeVisible();
  });

  test('an AI failure leaves a visible card and intact results', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
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
    await expect(page.locator('#rlist .rc, #rlist .es').first()).toBeVisible();
  });

  test('a backend outage removes the layer without breaking search', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.abort());
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');

    await expect(page.locator('#rlist .rc, #rlist .es').first()).toBeVisible();
    await expect(page.locator('#unifiedSearchLayer .us-ai')).toHaveCount(0);
  });

  test('a 500 from the unified endpoint is survivable', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ status: 500, body: 'boom' }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'E-7-4');
    await expect(page.locator('#rlist .rc, #rlist .es').first()).toBeVisible();
  });
});

test.describe('interpretation and evidence labelling', () => {
  test('the interpretation strip shows the detected code', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
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
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-99');
    await expect(page.locator('#unifiedSearchLayer .us-warn')).toContainText('D-2-99');
  });

  test('review-pending manual evidence is badged 검토 전', async ({ page }) => {
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
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, '체류자격 변경');
    await expect(page.locator('#unifiedSearchLayer .us-badge--review').first()).toBeVisible();
  });

  test('official source links are safe anchors', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
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
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await expect(page.locator('#unifiedSearchLayer .us-sources a')).toHaveCount(0);
    await expect(page.locator('#unifiedSearchLayer .us-source-link--plain')).toBeVisible();
  });
});

test.describe('URL state', () => {
  test('a search is shareable through ?q=', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await expect(page).toHaveURL(/[?&]q=D-2-1/);
  });

  test('a shared ?q= URL reproduces the search on load', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await page.goto('/index.html?q=D-2-1');
    await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 20_000 });
    await expect(page.locator('#q')).toHaveValue('D-2-1');
  });

  test('back navigation restores the previous query', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await search(page, 'D-2-1');
    await page.locator('#q').fill('E-7-4');
    await page.locator('#searchForm').evaluate((f) =>
      f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
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
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await page.goto('/index.html');
    const input = page.locator('#q');
    await expect(input).toBeEnabled({ timeout: 20_000 });
    await input.focus();
    await expect(input).toBeFocused();
    await input.type('D-2-1');
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
    await page.route(AI_OVERVIEW, (route) => route.fulfill({
      status: 200,
      json: { status: 'ok', overview: '요약입니다.',
              citationVerification: { failureCount: 0, unverifiableCount: 0 } }
    }));

    await search(page, 'D-2-1');
    await expect(page.locator('#unifiedSearchLayer .us-ai.is-ok')).toBeVisible();

    // Static-server 404s for optional assets are not app errors.
    const appErrors = errors.filter((e) => !/404|Failed to load resource/i.test(e));
    expect(appErrors, appErrors.join('\n')).toEqual([]);
  });

  test('the layer renders in dark theme', async ({ page }) => {
    await page.route(UNIFIED, (route) => route.fulfill({ json: unifiedBody() }));
    await page.route(AI_OVERVIEW, (route) => route.abort());

    await page.goto('/index.html');
    await page.evaluate(() => document.body.setAttribute('data-theme', 'dark'));
    const input = page.locator('#q');
    await expect(input).toBeEnabled({ timeout: 20_000 });
    await input.fill('D-2-1');
    await page.locator('#searchForm').evaluate((f) =>
      f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));

    const strip = page.locator('#unifiedSearchLayer .us-interpret');
    await expect(strip).toBeVisible();
    const bg = await strip.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(bg).not.toBe('rgba(0, 0, 0, 0)');
  });
});
