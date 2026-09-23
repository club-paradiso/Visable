// Real-browser tests for the Waymaker Quick Answer
// (assets/js/waymaker-quick-answer.js on top of status-guidance.js).
//
//   * a question-form query gets a deterministic Quick Answer above the full
//     guidance; a terse query does not;
//   * the full guidance is collapsed behind "전체 안내 보기" and expands;
//   * "근거 보기" opens the evidence section;
//   * the AI endpoint is optional: aborted / 404 / NOT_CONFIGURED stay silent,
//     a validated rewrite replaces the summary, a hallucinated rewrite is
//     rejected and the deterministic sentence stays;
//   * fee questions answer in fee mode without calling any model;
//   * the follow-up hands the context to ai.html and prefills the question.
import { test, expect } from '@playwright/test';

const FAITHFUL = '외국인등록증 재발급은 통합신청서에 사진 1장을 붙여 내고, 수수료 ₩35,000은 현금 또는 카드로 냅니다. 잃어버린 경우가 아니면 기존 등록증도 함께 냅니다.';
const HALLUCINATED = '외국인등록증 재발급 수수료는 면제이고 여권 사본 2부와 아포스티유 출생증명서가 필요합니다.';

async function boot(page, url = '/index.html', apiHandler = null) {
  await page.route('**/api/**', (route) => route.abort());
  if (apiHandler) await page.route('**/api/waymaker/quick-answer', apiHandler);
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; }
  }, null, { timeout: 30_000 });
  return errors;
}

async function search(page, query) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const sel = searched ? '#q' : '#civicQuery';
  await page.fill(sel, query);
  await page.press(sel, 'Enter');
  const sg = page.locator('#statusGuidance[data-sg-kind]');
  await expect(sg).toBeVisible({ timeout: 20_000 });
  return sg;
}

const json = (status, body) => (route) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

test.describe('deterministic Quick Answer', () => {
  test('a question gets a Quick Answer first; the full guidance is collapsed and expands', async ({ page }) => {
    const errors = await boot(page);
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    const quick = sg.locator('.sg-quick');
    await expect(quick).toBeVisible();
    await expect(quick).toHaveAttribute('data-sg-quick-mode', 'answer');
    await expect(quick.locator('#sgQuickTitle')).toContainText('외국인등록증 재발급');
    const summary = quick.locator('#sgQuickSummary');
    await expect(summary).toHaveAttribute('data-sg-ai', 'deterministic');
    await expect(summary).not.toHaveText('');
    await expect(quick.locator('.sg-quick-grid')).toContainText('₩35,000');
    // quick answer sits above the full answer, which is collapsed
    const order = await page.evaluate(() => {
      const q = document.querySelector('.sg-quick'); const a = document.querySelector('#sgFull');
      return q && a ? Boolean(q.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING) : null;
    });
    expect(order).toBe(true);
    const full = sg.locator('#sgFull');
    await expect(full).toBeHidden();
    const toggle = quick.locator('[data-sg-action="toggle-full"]');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await toggle.click();
    await expect(sg.locator('#sgFull')).toBeVisible();
    await expect(sg.locator('#sgFull .sg-doc-group-required')).toBeVisible();
    await expect(sg.locator('.sg-quick [data-sg-action="toggle-full"]')).toHaveAttribute('aria-expanded', 'true');
    // no AI note when the endpoint is unreachable
    await page.waitForTimeout(400);
    await expect(sg.locator('#sgQuickNote')).toBeHidden();
    expect(errors.filter((e) => /waymaker-quick-answer|status-guidance/.test(e))).toEqual([]);
  });

  test('"근거 보기" opens the collapsed evidence section', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    await expect(sg.locator('#sgEvidence')).not.toHaveAttribute('open', /.*/);
    await sg.locator('.sg-quick [data-sg-action="show-evidence"]').click();
    await expect(sg.locator('#sgEvidence')).toHaveAttribute('open', /.*/);
    await expect(sg.locator('#sgEvidence .sg-ev').first()).toBeVisible();
  });

  test('a terse query gets the full guidance directly, without a Quick Answer block', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    await expect(sg.locator('.sg-quick')).toHaveCount(0);
    await expect(sg.locator('.sg-doc-group-required')).toBeVisible();
  });

  test('a fee question answers in fee mode with the amount and instrument, never calling a model', async ({ page }) => {
    let called = 0;
    await boot(page, '/index.html', (route) => { called += 1; return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, summary: FAITHFUL }) }); });
    const sg = await search(page, 'F-6-1 연장 수수료 얼마야?');
    await expect(sg).toHaveAttribute('data-sg-kind', 'question');
    await page.locator('#statusGuidance [data-sg-action="answer"][data-sg-value="normal"]').first().click();
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    const quick = sg.locator('.sg-quick');
    await expect(quick).toHaveAttribute('data-sg-quick-mode', 'fee');
    await expect(quick.locator('.sg-quick-grid')).toContainText('₩30,000');
    await page.waitForTimeout(500);
    expect(called).toBe(0);
    await expect(quick.locator('#sgQuickSummary')).toHaveAttribute('data-sg-ai', 'deterministic');
  });
});

test.describe('optional AI wording is validated, never trusted', () => {
  test('a faithful rewrite replaces the summary and is marked enhanced', async ({ page }) => {
    await boot(page, '/index.html', json(200, { ok: true, status: 'OK', summary: FAITHFUL }));
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    const summary = sg.locator('#sgQuickSummary');
    await expect(summary).toHaveAttribute('data-sg-ai', 'enhanced', { timeout: 10_000 });
    await expect(summary).toHaveText(FAITHFUL);
    await expect(sg.locator('.sg-quick-grid')).toContainText('₩35,000');
  });

  test('a hallucinated rewrite is rejected: the deterministic sentence stays', async ({ page }) => {
    await boot(page, '/index.html', json(200, { ok: true, status: 'OK', summary: HALLUCINATED }));
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    const summary = sg.locator('#sgQuickSummary');
    const before = await summary.textContent();
    await page.waitForTimeout(1_200);
    await expect(summary).toHaveAttribute('data-sg-ai', 'deterministic');
    await expect(summary).toHaveText(before);
    await expect(summary).not.toContainText('아포스티유');
    await expect(summary).not.toContainText('면제');
    // the rejection is reported honestly, without hiding the verified guidance
    await expect(sg.locator('#sgQuickNote')).toBeVisible();
    await expect(sg.locator('.sg-quick-grid')).toContainText('₩35,000');
  });

  test('NOT_CONFIGURED and 404 stay silent; a provider failure shows the honest note', async ({ page }) => {
    await boot(page, '/index.html', json(503, { ok: false, status: 'NOT_CONFIGURED' }));
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    await page.waitForTimeout(800);
    await expect(sg.locator('#sgQuickNote')).toBeHidden();
    await expect(sg.locator('#sgQuickSummary')).toHaveAttribute('data-sg-ai', 'deterministic');

    await page.unroute('**/api/waymaker/quick-answer');
    await page.route('**/api/waymaker/quick-answer', json(404, { error: 'not found' }));
    await search(page, '체류지 변경 신고하려면 어떻게 해?');
    await page.waitForTimeout(800);
    await expect(sg.locator('#sgQuickNote')).toBeHidden();

    await page.unroute('**/api/waymaker/quick-answer');
    await page.route('**/api/waymaker/quick-answer', json(502, { ok: false, status: 'PROVIDER_FAILED' }));
    await search(page, '외국인등록증 재발급하려면?');
    await expect(sg.locator('#sgQuickNote')).toBeVisible({ timeout: 10_000 });
    await expect(sg.locator('#sgQuickSummary')).toHaveAttribute('data-sg-ai', 'deterministic');
  });
});

test.describe('follow-up handoff', () => {
  test('the follow-up link stores the handoff packet and prefills the Waymaker question', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급하려면 뭐 필요해?');
    const link = sg.locator('.sg-quick [data-sg-action="followup"]');
    await expect(link).toHaveAttribute('href', /ai\.html\?/);
    await link.click();
    await page.waitForURL(/ai\.html\?handoff=quick-answer/, { timeout: 15_000 });
    const packet = await page.evaluate(() => { try { return JSON.parse(sessionStorage.getItem('visable.waymaker.handoff') || 'null'); } catch (e) { return null; } });
    expect(packet && packet.query).toBe('외국인등록증 재발급하려면 뭐 필요해?');
    expect(packet.procedure).toBe('card_reissue');
    expect(JSON.stringify(packet)).not.toMatch(/passport_no|arc_no|resident_registration/);
    await expect(page.locator('#aiQ')).toHaveValue('외국인등록증 재발급하려면 뭐 필요해?', { timeout: 15_000 });
  });
});
