// Golden: fail-closed behaviour. When data, scripts or the AI layer are missing
// the site must say so and never fabricate guidance. Expected notices come from
// data/i18n/ko.json (civic.*) and fixtures/guidance-strings.mjs.
import { test, expect } from '@playwright/test';
import { pack, fee, won } from '../helpers/data.mjs';
import { GUIDANCE_STR as STR } from '../fixtures/guidance-strings.mjs';
import { boot, search, guidanceHeading, bodyText, mainText, normalize, jsonRoute } from '../helpers/page.mjs';

const ko = pack('ko');
const abort = (route) => route.abort();

test('visa data unavailable: no guidance is rendered, the disclaimer stays, no page errors', async ({ page }) => {
  const errors = await boot(page, { waitForSearch: false, routes: [['**/visa_data.json*', abort], ['**/backend/data/visas.json*', abort]] });
  await page.waitForTimeout(4000);
  const text = normalize(await bodyText(page));
  expect(text).toContain(normalize(ko.civic.disclaimer));
  expect(text).not.toContain(STR.ko.docsTitle);
  expect(text).not.toContain(STR.ko.feeTitle);
  await expect(page.getByRole('heading', { level: 1, name: /^(안내|Guidance) · / })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('guidance bundle unavailable: the failure notice and retry are shown instead of a guessed document list', async ({ page }) => {
  await boot(page, { query: { q: 'D-2 체류기간 연장' }, waitForSearch: false, routes: [['**/status-guidance-202609.json*', abort]] });
  await expect(page.getByText(STR.ko.failed, { exact: false })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('button', { name: STR.ko.retry })).toBeVisible();
  const text = normalize(await mainText(page));
  expect(text).not.toContain(STR.ko.docsTitle);
  expect(text).not.toContain(won(fee('extension_general').amount));
  expect(normalize(await bodyText(page))).toContain(normalize(ko.civic.disclaimer));
});

test('home script fails to load: the page says so and offers reload + official PDFs instead of a blank screen', async ({ page }) => {
  await boot(page, { waitForSearch: false, routes: [['**/civic-search*.js*', abort]] });
  await expect(page.getByText(normalize(ko.civic.bootFailed), { exact: false })).toBeVisible({ timeout: 30_000 });
  const text = normalize(await bodyText(page));
  expect(text).toContain(normalize(ko.civic.disclaimer));
  await expect(page.locator('a[href*="source-manuals"][href$=".pdf"]:visible').first()).toBeVisible();
});

test.describe('Waymaker Quick Answer AI layer is optional', () => {
  const question = '외국인등록증 재발급하려면 뭐 필요해?'; // question-form query → Quick Answer (deterministic) + optional AI rewrite
  const reissueFee = fee('card_reissue');

  test('AI endpoint aborted: the deterministic answer, fee and notices still render', async ({ page }) => {
    await boot(page);
    await search(page, question);
    const text = normalize(await mainText(page));
    expect(text).toContain(won(reissueFee.amount));
    // The Quick Answer card carries its own review caveat (assets/js/waymaker-quick-answer.js `review`).
    expect(text).toMatch(/검토는 아직 끝나지 않았어요/);
    expect(text).toContain(STR.ko.disclaimer);
  });

  test('AI endpoint says NOT_CONFIGURED (503): nothing changes for the user', async ({ page }) => {
    await boot(page, { blockApi: false, routes: [['**/api/waymaker/quick-answer', jsonRoute(503, { ok: false, status: 'NOT_CONFIGURED' })], ['**/api/**', abort]] });
    await search(page, question);
    const text = normalize(await mainText(page));
    expect(text).toContain(won(reissueFee.amount));
    expect(text).not.toMatch(/NOT_CONFIGURED|503|undefined|\[object/);
  });

  test('a hallucinated AI rewrite (wrong fee, invented documents) is rejected; the grounded answer stays', async ({ page }) => {
    // The fabricated sentence contradicts the fee registry (₩35,000, cash) and
    // the document list (form + photo [+ old card]); it must never be shown.
    const HALLUCINATED = '외국인등록증 재발급 수수료는 면제이고 여권 사본 2부와 아포스티유 출생증명서가 필요합니다.';
    await boot(page, { blockApi: false, routes: [['**/api/waymaker/quick-answer', jsonRoute(200, { ok: true, status: 'OK', summary: HALLUCINATED })], ['**/api/**', abort]] });
    const aiCall = page.waitForResponse((r) => r.url().includes('/api/waymaker/quick-answer'), { timeout: 30_000 }).catch(() => null);
    await search(page, question);
    await aiCall;
    await page.waitForTimeout(500);
    const text = normalize(await mainText(page));
    expect(text).not.toContain('아포스티유 출생증명서');
    expect(text).not.toContain('여권 사본 2부');
    expect(text).toContain(won(reissueFee.amount));
    expect(text).toContain(STR.ko.disclaimer);
  });
});

test('backend and every provider down: a status search still resolves from static data', async ({ page }) => {
  await boot(page); // all /api/** aborted
  await search(page, 'D-2');
  await expect(guidanceHeading(page, 'D-2')).toBeAttached();
  expect(normalize(await mainText(page))).toContain(STR.ko.disclaimer);
});
