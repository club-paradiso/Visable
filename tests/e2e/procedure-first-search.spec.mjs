// Real-browser tests for procedure-first search
// (assets/js/search-router.js + assets/js/status-guidance.js).
//
// The confirmed production regression: "외국인등록증 재발급" rendered
// "체류자격을 찾지 못했어요" because the search layer assumed every query
// needs a status first. These tests pin the architectural fix:
//
//   * status-independent procedures (card reissue, address report,
//     registration-info report) answer without a status, in Korean and English;
//   * the reissue reason only moves the "existing card" item, never the list;
//   * fees are rendered in a fee section, never as a document;
//   * physical form is shown only where the source says it;
//   * status-required procedures ask a plain-language status question;
//   * evidence is collapsed and still opens the September 2026 page;
//   * the disclaimer is concise with an "안내 기준 보기" expander;
//   * the local-practice report dialog opens and closes; the Jeju case is an
//     unverified report on top of the national baseline, never policy;
//   * nothing scrolls horizontally on any viewport project.
//
// The static server has no backend: /api/* is aborted.
import { test, expect } from '@playwright/test';

const DEAD_END = '체류자격을 찾지 못했어요';

async function boot(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  page.on('console', (m) => {
    if (m.type() === 'error' && !/net::ERR|Failed to load resource/.test(m.text())) errors.push(m.text());
  });
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

async function answer(page, value, dim) {
  const dimSel = dim ? `[data-sg-dim="${dim}"]` : '';
  await page.locator(`#statusGuidance [data-sg-action="answer"]${dimSel}[data-sg-value="${value}"]`).first().click();
  await page.waitForTimeout(150);
}

async function noHorizontalScroll(page) {
  const o = await page.evaluate(() => ({ doc: document.documentElement.scrollWidth, body: document.body.scrollWidth, inner: innerWidth }));
  expect(o.doc, `document scrollWidth ${o.doc} > ${o.inner}`).toBeLessThanOrEqual(o.inner + 1);
  expect(o.body, `body scrollWidth ${o.body} > ${o.inner}`).toBeLessThanOrEqual(o.inner + 1);
  const leaks = await page.evaluate(() => [...document.querySelectorAll('#statusGuidance *')]
    .filter((el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.right > innerWidth + 1; })
    .slice(0, 5).map((el) => el.className || el.tagName));
  expect(leaks, `guidance elements leave the viewport: ${leaks.join(', ')}`).toEqual([]);
}

const ownErrors = (errors) => errors.filter((e) => /search-router|status-guidance|waymaker-quick-answer|local-practice/.test(e));

test.describe('status-independent procedures answer without a status', () => {
  test('외국인등록증 재발급 renders the common procedure, documents, fee and form — never the dead end', async ({ page }) => {
    const errors = await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    await expect(sg).toHaveAttribute('data-sg-kind', 'procedure');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('외국인등록증 재발급');
    await expect(sg).not.toContainText(DEAD_END);
    await expect(sg.locator('.sg-interp')).toBeVisible();
    // a status question is not asked for a status-independent procedure
    await expect(sg.locator('.sg-question')).toHaveCount(0);
    await expect(sg.locator('.sg-doc-group-required')).toBeVisible();
    // the fee lives in the fee section with amount + instrument, never as a document
    const fee = sg.locator('.sg-fee');
    await expect(fee).toBeVisible();
    await expect(fee.locator('.sg-fee-amount')).toHaveText('₩35,000');
    await expect(fee).toContainText('납부 방식');
    const docNames = await sg.locator('.sg-doc-name').allTextContents();
    expect(docNames.filter((n) => /수수료/.test(n))).toEqual([]);
    // physical form only where the regulation says it (existing card = original, not returned)
    await expect(sg.locator('.sg-doc-form').first()).toBeVisible();
    await noHorizontalScroll(page);
    expect(ownErrors(errors)).toEqual([]);
  });

  test('the reissue reason moves only the existing-card item (lost → not needed, damaged → required)', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    await expect(sg.locator('.sg-doc-group-conditional')).toContainText('원래의 외국인등록증');
    await answer(page, 'lost', 'reissue_reason');
    await expect(sg.locator('.sg-doc-group-na')).toBeVisible();
    await expect(sg.locator('.sg-doc-group-na')).toContainText('원래의 외국인등록증');
    await expect(sg.locator('.sg-doc-group-required')).toBeVisible();
    await answer(page, 'damaged', 'reissue_reason');
    await expect(sg.locator('.sg-doc-group-na')).toHaveCount(0);
    await expect(sg.locator('.sg-doc-group-required')).toContainText('원래의 외국인등록증');
    // the fee never changes with the reason
    await expect(sg.locator('.sg-fee-amount')).toHaveText('₩35,000');
  });

  for (const q of ['등록증 재발급', 'ARC 재발급', 'residence card reissue', '외국인등록증 분실', '외국인등록증 재발급 수수료']) {
    test(`"${q}" resolves to the card reissue procedure`, async ({ page }) => {
      await boot(page);
      const sg = await search(page, q);
      await expect(sg).toHaveAttribute('data-sg-kind', 'procedure');
      await expect(sg).not.toContainText(DEAD_END);
      await expect(sg.locator('#sgAnswerTitle')).toContainText(/외국인등록증 재발급|Residence card reissue/);
      await expect(sg.locator('.sg-fee-amount')).toHaveText('₩35,000');
    });
  }

  test('체류지 변경 신고 answers without a status, with the alternatives group and the 15-day rule', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '체류지 변경 신고');
    await expect(sg).toHaveAttribute('data-sg-kind', 'procedure');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('체류지 변경 신고');
    await expect(sg).toContainText('15일');
    // the alternatives (임대차계약서 / 매매계약서 / 기타) live inside the collapsed document row
    const altRow = sg.locator('.sg-doc-details').filter({ has: page.locator('.sg-doc-alts') }).first();
    await expect(altRow).toBeVisible();
    await altRow.locator('> summary').click();
    await expect(altRow.locator('.sg-doc-alts')).toBeVisible();
    // the regulation lists no fee item for this report: rendered as "not listed", never as an invented amount
    await expect(sg.locator('.sg-fee')).toBeVisible();
    await expect(sg.locator('.sg-fee')).not.toContainText('₩');
  });

  test('여권 재발급 후 신고 is the registration-info report: status optional, no fee, no fake card reissue', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '여권 재발급 후 신고');
    await expect(sg).toHaveAttribute('data-sg-kind', 'procedure');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('등록사항 변경신고');
    await expect(sg.locator('[data-sg-action="ask-status"]')).toBeVisible();
    await expect(sg.locator('.sg-fee-amount')).toContainText('수수료 없음');
  });

  test('English query gets the English procedure label and the same fee', async ({ page }) => {
    await boot(page, '/index.html?lang=en');
    const sg = await search(page, 'residence card reissue');
    await expect(sg).toHaveAttribute('data-sg-kind', 'procedure');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('Residence card reissue');
    await expect(sg.locator('.sg-fee-amount')).toHaveText('₩35,000');
    await noHorizontalScroll(page);
  });
});

test.describe('status-required procedures ask a plain-language status question', () => {
  test('체류기간 연장 asks the status in plain language, then resolves the picked code', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '체류기간 연장');
    await expect(sg).toHaveAttribute('data-sg-kind', 'need-status');
    await expect(sg).not.toContainText(DEAD_END);
    await expect(sg.locator('.sg-question')).toBeVisible();
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
    await expect(sg.locator('[data-sg-action="answer"][data-sg-value="unsure"]')).toBeVisible();
    await answer(page, 'study', '__status');
    await expect(sg.locator('[data-sg-dim="__status2"][data-sg-value="D-2"]')).toBeVisible();
    await answer(page, 'D-2', '__status2');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('D-2');
    await expect(sg.locator('.sg-doc-group-required')).toBeVisible();
    await noHorizontalScroll(page);
  });
});

test.describe('one result system: the legacy per-status cards are gated, not rendered', () => {
  for (const q of ['체류기간 연장', '체류지 변경 신고', 'D-2 연장']) {
    test(`"${q}": the legacy card list and the backend layer never display; the page stays short`, async ({ page }) => {
      await boot(page);
      await search(page, q);
      await expect(page.locator('#rlist')).toBeHidden();
      await expect(page.locator('#unifiedSearchLayer')).toBeHidden();
      await expect(page.locator('#hero .reference-disclaimer')).toBeHidden();
      await expect(page.locator('#civicResultTabs')).toHaveCount(0);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollHeight), { timeout: 10_000 }).toBeLessThan(8_000);
    });
  }

  test('the legacy card opens only on the explicit "기존 체류자격 카드 보기" request', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    await expect(page.locator('#rlist')).toBeHidden();
    await sg.locator('[data-sg-action="legacy-card"]').click();
    await expect(page.locator('#rlist article.vc').first()).toBeVisible();
    expect(await page.evaluate(() => document.body.getAttribute('data-legacy-card'))).toBe('open');
    // a new search closes it again
    await search(page, 'F-6 연장');
    await expect(page.locator('#rlist')).toBeHidden();
  });
});

test.describe('evidence, disclaimer, report, local practice', () => {
  test('evidence is collapsed by default and still opens the September 2026 page', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    const ev = sg.locator('#sgEvidence');
    await expect(ev).toBeVisible();
    await expect(ev).not.toHaveAttribute('open', /.*/);
    await ev.locator('> summary').click();
    await expect(ev).toHaveAttribute('open', /.*/);
    await sg.locator('[data-sg-action="open-page"]').first().click();
    await expect(page.locator('#civicPageDialog[open]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('#civicPageTitle')).not.toHaveText('');
    await page.keyboard.press('Escape');
  });

  test('the disclaimer is one concise line with an "안내 기준 보기" expander; the hero disclaimer is hidden', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    const d = sg.locator('.sg-disclaimer');
    await expect(d).toBeVisible();
    await expect(d).toContainText('참고 안내');
    const more = d.locator('details.sg-disclaimer-more');
    await expect(more.locator('> summary')).toHaveText('안내 기준 보기');
    await expect(more).not.toHaveAttribute('open', /.*/);
    await more.locator('> summary').click();
    await expect(more).toContainText('법적 효력이 없습니다');
    const hero = page.locator('#hero .reference-disclaimer');
    if (await hero.count()) await expect(hero.first()).toBeHidden();
  });

  test('the local-practice report dialog opens from the guidance, requires consent and closes on Escape', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '외국인등록증 재발급');
    // office information is collapsed until the reader opens it
    await expect(sg.locator('.sg-local-details')).not.toHaveAttribute('open', /.*/);
    await sg.locator('.sg-local-details > summary').click();
    await sg.locator('[data-sg-action="report"]').first().click();
    const dialog = page.locator('#sgReportDialog[open]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });
    await expect(dialog.locator('select[name="office"]')).toBeVisible();
    await expect(dialog.locator('input[name="consent"]')).toHaveAttribute('required', /.*/);
    await page.keyboard.press('Escape');
    await expect(page.locator('#sgReportDialog[open]')).toHaveCount(0);
  });

  test('Jeju F-6-1: picking the office shows the unverified report while the national document stays required', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-6-1 연장');
    await expect(sg).toHaveAttribute('data-sg-kind', 'question');
    await answer(page, 'normal');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('.sg-doc-group-required')).toContainText('체류지');
    await sg.locator('.sg-local-details > summary').click();
    await sg.locator('#sgOffice').selectOption('jeju');
    // a chosen office keeps the section open across re-renders
    await expect(sg.locator('.sg-local-details')).toHaveAttribute('open', /.*/);
    await expect(sg.locator('.sg-local-has')).toBeVisible();
    await expect(sg.locator('.sg-local')).toContainText('확인되지 않은 이용자 제보');
    await expect(sg.locator('.sg-local')).toContainText('전국 기준을 바꾸는 정보가 아니에요');
    await expect(sg.locator('.sg-doc-group-required')).toContainText('체류지');
    await sg.locator('#sgOffice').selectOption('seoul');
    await expect(sg.locator('.sg-local')).toContainText('확인된 차이 정보가 없어요');
    await noHorizontalScroll(page);
  });
});
