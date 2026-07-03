// Real-browser QA for Easy Mode (쉬운 안내) — the per-card Standard/Easy/Official
// view switcher and the Easy panel content contract.
//
// Guards the accuracy regressions fixed in the Easy Mode overhaul:
//   - the summary resolves through the same chain as the compact card
//     (summary → newReq → extReq), so the "not ready" fallback notice only
//     appears when a record genuinely has no canonical prose;
//   - document names are grouped per procedure stage under the Standard view's
//     own stage labels and stages are never merged into one flat list
//     (사증발급/입국 전 docs must not read as in-Korea 체류 requirements);
//   - fee lines ("수수료…"), caution markers ("…주의") and dangling footnote
//     asterisks are never presented as documents to prepare;
//   - the view switcher is an aria-pressed toggle-button group (no fake tabs)
//     and the in-panel "공식 근거 보기" hand-off keeps keyboard focus.
import { test, expect } from '@playwright/test';

async function searchStatus(page, code) {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof dataReady !== 'undefined' && dataReady, null, { timeout: 30_000 });
  await page.evaluate((c) => {
    const q = document.getElementById('q'); if (q) { q.disabled = false; q.value = c; }
    document.body.classList.add('searched');
    renderResults(c);
  }, code);
  const card = page.locator(`#rlist .vc[data-code="${code}"]`).first();
  await card.waitFor({ timeout: 15_000 });
  return card;
}

async function openEasyView(page, code) {
  const card = await searchStatus(page, code);
  await card.locator('.view-mode-btn[data-card-mode="easy"]').click();
  await expect(card).toHaveClass(/card-mode-easy/);
  return card;
}

test.describe('easy mode content contract', () => {
  test('D-2: canonical summary + stage-scoped documents, no non-doc rows', async ({ page }) => {
    const card = await openEasyView(page, 'D-2');
    const panel = card.locator('.easy-mode-panel');

    // Canonical summary present → no "not ready" fallback notice.
    await expect(panel.locator('.easy-fallback-notice')).toHaveCount(0);
    await expect(panel.locator('.easy-card').first()).toContainText('체류자격');

    // Documents are grouped under the Standard view's stage labels; the
    // extension stage must be present (the old flat list dropped it at 8).
    const groupLabels = panel.locator('.easy-doc-group .easy-subtitle');
    await expect(groupLabels).not.toHaveCount(0);
    const labels = await groupLabels.allTextContents();
    expect(labels.some((l) => l.includes('연장')), '체류기간 연장 stage present').toBeTruthy();

    // No fee / caution / dangling-asterisk rows presented as documents.
    const items = await panel.locator('.easy-doc-group li').allTextContents();
    expect(items.length).toBeGreaterThan(0);
    for (const name of items.map((s) => s.trim())) {
      expect(name, 'fee line rendered as document').not.toMatch(/수수료/);
      expect(name, 'caution marker rendered as document').not.toMatch(/주의$/);
      expect(name, 'dangling footnote asterisk').not.toMatch(/\*$/);
    }
  });

  test('view switcher is an accessible toggle group with focus continuity', async ({ page }) => {
    const card = await openEasyView(page, 'D-2');

    // Toggle-button semantics: role=group + aria-pressed, no fake tab roles.
    await expect(card.locator('.view-mode-btns')).toHaveAttribute('role', 'group');
    await expect(card.locator('.view-mode-btn[role="tab"], .view-mode-btn[aria-selected]')).toHaveCount(0);
    await expect(card.locator('.view-mode-btn[data-card-mode="easy"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(card.locator('.view-mode-btn[data-card-mode="standard"]')).toHaveAttribute('aria-pressed', 'false');
    await expect(card.locator('.easy-mode-panel')).toHaveAttribute('role', 'region');

    // The in-panel official-source button hides itself on switch; focus must
    // land on the official view-switcher button instead of dropping to <body>.
    await card.locator('.easy-official-btn').click();
    await expect(card).toHaveClass(/card-mode-official/);
    const focused = await page.evaluate(() => ({
      cls: document.activeElement ? document.activeElement.className : '',
      mode: document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.cardMode : ''
    }));
    expect(focused.cls).toContain('view-mode-btn');
    expect(focused.mode).toBe('official');
  });

  test('global Easy Mode toggle applies to result cards and persists', async ({ page }) => {
    const card = await searchStatus(page, 'E-7');
    await page.click('#easyModeBtn');
    await expect(page.locator('#easyModeBtn')).toHaveAttribute('aria-pressed', 'true');
    await expect(card).toHaveClass(/card-mode-easy/);
    const stored = await page.evaluate(() => localStorage.getItem('paradiso:easyMode'));
    expect(stored).toBe('1');
    await page.click('#easyModeBtn');
    await expect(card).not.toHaveClass(/card-mode-easy/);
  });
});
