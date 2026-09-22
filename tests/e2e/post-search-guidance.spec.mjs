// Real-browser tests for the post-search status guidance layer
// (assets/js/status-guidance.js + assets/css/status-guidance.css).
//
// The layer mounts above the legacy result tabs after a search and owns the
// new information hierarchy:
//
//   1 what Visable understood  2 clarification (only if needed)  3 answer
//   4 procedure  5 required documents  6 next actions  7 evidence  8 related
//
// The load-bearing assertions are about *not being confidently wrong*:
//
//   * a parent code (F-1 연장) asks before showing any required list;
//   * an exact subcode (F-2-7 연장) skips the questions;
//   * intent controls the procedure (E-9 호텔 never turns into a checklist for
//     another subtype; D-2 아르바이트 is 체류자격외 활동, not 연장);
//   * status change is a transition (F-6 자격변경 asks the current status and
//     refuses short-stay by default, with the manual's exceptions);
//   * "잘 모르겠어요" degrades to candidates + evidence, never a checklist;
//   * the language switch keeps the answered state;
//   * evidence opens the September 2026 manual page;
//   * the AI FAB never covers the answer, and nothing scrolls horizontally.
//
// The static server has no backend: /api/* is aborted so the guidance layer is
// exercised exactly as it behaves when the backend is down.
import { test, expect } from '@playwright/test';

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

async function answer(page, value) {
  await page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${value}"]`).first().click();
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

test.describe('resolver: parent code asks, exact code answers', () => {
  test('F-1 연장 asks the stay reason before any document list, then resolves F-1-5 step by step', async ({ page }) => {
    const errors = await boot(page);
    const sg = await search(page, 'F-1 연장');
    await expect(sg).toHaveAttribute('data-sg-kind', 'question');
    // 1. interpretation first, 2. question next, no checklist yet
    await expect(sg.locator('.sg-interp')).toBeVisible();
    await expect(sg.locator('.sg-question')).toBeVisible();
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
    await expect(sg.locator('[data-sg-action="answer"][data-sg-value="unsure"]')).toBeVisible();
    await answer(page, 'marriage_family');
    await answer(page, 'marriage_migrant');
    await answer(page, 'first');
    // back goes to the previous question
    await sg.locator('[data-sg-action="back"]').first().click();
    await expect(sg.locator('[data-sg-action="answer"][data-sg-value="first"]')).toBeVisible();
    await answer(page, 'first');
    await answer(page, 'childcare');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('F-1-5');
    await expect(sg.locator('.sg-doc-group-required')).toBeVisible();
    // provenance per item and the officer note exactly once
    expect(await sg.locator('.sg-doc-group-required .sg-doc').count()).toBeGreaterThan(3);
    await expect(sg.locator('.sg-officer')).toHaveCount(1);
    await expect(sg.locator('.sg-evidence')).toBeVisible();
    await expect(sg.locator('.sg-next')).toBeVisible();
    await noHorizontalScroll(page);
    expect(errors).toEqual([]);
  });

  test('F-2-7 연장 (exact subcode) resolves without a question', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-2-7 연장');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('.sg-question')).toHaveCount(0);
    await expect(sg.locator('#sgAnswerTitle')).toContainText('F-2-7');
    await expect(sg.locator('.sg-evidence')).toBeVisible();
  });

  test('잘 모르겠어요 degrades to candidates and evidence, never a checklist', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-1 연장');
    await answer(page, 'unsure');
    await expect(sg).toHaveAttribute('data-sg-kind', 'unresolved');
    expect(await sg.locator('.sg-candidate').count()).toBeGreaterThanOrEqual(10);
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
    await expect(sg.locator('.sg-evidence')).toBeVisible();
    await noHorizontalScroll(page);
  });
});

test.describe('intent controls the procedure', () => {
  test('E-9 호텔 keeps the hotel subtype and asks the procedure instead of guessing manufacturing', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'E-9 호텔');
    await expect(sg).toHaveAttribute('data-sg-kind', 'question');
    await expect(sg.locator('.sg-question')).toContainText('E-9');
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
    await answer(page, 'extension');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('#sgAnswerTitle')).toContainText('E-9-5');
    await expect(sg.locator('.sg-interp')).not.toContainText('제조업');
  });

  test('D-2 연장 resolves; D-2 아르바이트 opens 체류자격외 활동, not 연장', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('.sg-kicker').first()).toContainText('연장');
    await search(page, 'D-2 아르바이트');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await expect(sg.locator('.sg-kicker').first()).toContainText('시간제 취업');
    await expect(sg.locator('.sg-kicker').first()).not.toContainText('연장');
  });

  test('F-6 자격변경 is a transition: asks the current status, refuses short-stay by default with the exceptions', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-6 자격변경');
    await expect(sg).toHaveAttribute('data-sg-kind', 'question');
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
    await answer(page, 'short_stay');
    await expect(sg.locator('.sg-transition')).toBeVisible();
    await expect(sg.locator('.sg-transition .sg-warn')).toBeVisible();
    await expect(sg.locator('.sg-transition')).toContainText('독일인');
    await expect(sg.locator('.sg-transition')).toContainText('임신');
    await expect(sg.locator('.sg-doc-group-required')).toHaveCount(0);
  });

  test('a special program query is answered as a program, not a status', async ({ page }) => {
    await boot(page);
    const sg = await search(page, '톱티어');
    await expect(sg).toHaveAttribute('data-sg-kind', 'program');
    await expect(sg.locator('#sgAnswerTitle')).toContainText(/Top-Tier|톱티어/);
    await expect(sg.locator('.sg-question')).toHaveCount(0);
    await expect(sg.locator('.sg-evidence')).toBeVisible();
  });
});

test.describe('evidence, language and layout', () => {
  test('evidence opens the September 2026 manual page in the civic page dialog', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-2-7 연장');
    await sg.locator('[data-sg-action="open-page"]').first().click();
    const dialog = page.locator('#civicPageDialog[open]');
    await expect(dialog).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('#civicPageTitle')).not.toHaveText('');
    await page.keyboard.press('Escape');
  });

  test('switching to English keeps the answered state', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-1 연장');
    await answer(page, 'marriage_family');
    await answer(page, 'marriage_migrant');
    await answer(page, 'first');
    await answer(page, 'childcare');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved');
    await page.evaluate(() => document.querySelector('[data-action="apply-language"][data-lang="en"]')?.click());
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved', { timeout: 10_000 });
    await expect(sg.locator('#sgAnswerTitle')).toContainText('F-1-5');
    await expect(sg.locator('.sg-docs h3').first()).toContainText(/Documents|documents/);
    await noHorizontalScroll(page);
  });

  test('the AI FAB is hidden in the searched state and a contextual Waymaker link exists instead', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'D-2 연장');
    const fab = page.locator('.ai-fab');
    if (await fab.count()) await expect(fab).toBeHidden();
    await expect(sg.locator('.sg-next-ai a')).toHaveAttribute('href', /ai\.html\?visa_code=D-2/);
  });

  test('every interactive control in the guidance layer is at least 44px tall', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-1 연장');
    const small = await sg.evaluate((root) => [...root.querySelectorAll('button, a, summary')]
      .filter((el) => { const s = getComputedStyle(el); const r = el.getBoundingClientRect(); return s.display !== 'none' && r.width > 0 && r.height > 0; })
      .map((el) => ({ cls: el.className, h: el.getBoundingClientRect().height }))
      .filter((x) => x.h < 44 && !/sg-link-inline|sg-answered-item/.test(x.cls)));
    expect(small, JSON.stringify(small)).toEqual([]);
    await noHorizontalScroll(page);
  });

  test('a code typed into the correction field re-runs the resolver', async ({ page }) => {
    await boot(page);
    const sg = await search(page, 'F-1 연장');
    await sg.locator('[data-sg-action="edit"]').click();
    const form = sg.locator('form[data-sg-form="code"]');
    await expect(form).toBeVisible();
    await form.locator('input').fill('F-1-13');
    await form.locator('input').press('Enter');
    await expect(sg).toHaveAttribute('data-sg-kind', 'resolved', { timeout: 10_000 });
    await expect(sg.locator('#sgAnswerTitle')).toContainText('F-1-13');
  });
});
