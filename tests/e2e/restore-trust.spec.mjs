// Restore Trust (2026-10-28): the F-4 재외동포 → 사증발급 path, before/after contract.
//
//   * the procedure chooser marks 원문 확인 only where picking it really ends on the
//     official text (3 of F-4's former 10 badges led to structured common rules),
//     and explains what the mark means;
//   * 사증발급 cites the page that holds the F-4 visa section (393), not the
//     handbook cover (383);
//   * the source-only answer shows that page verbatim, labelled as unreviewed
//     extracted text, readable in every skin — no organised guidance is invented;
//   * the related-source list for a visa procedure contains visa-manual pages only.
import { test, expect } from '@playwright/test';

async function boot(page) {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto('/index.html');
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch (e) { return false; } }, null, { timeout: 30_000 });
}
async function chooser(page) {
  await page.fill('#civicQuery', 'F-4 재외동포');
  await page.press('#civicQuery', 'Enter');
  const sg = page.locator('#statusGuidance[data-sg-kind="question"]');
  await expect(sg).toBeVisible({ timeout: 20_000 });
  return sg;
}
// WCAG relative-luminance contrast between an element's text and the first opaque background behind it.
async function contrast(locator) {
  return locator.evaluate((el) => {
    const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
    const lum = ({ r, g, b }) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const fg = parse(getComputedStyle(el).color);
    let n = el, bg = null;
    while (n && n.nodeType === 1) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0.5) { bg = c; break; } n = n.parentElement; }
    bg = bg || { r: 255, g: 255, b: 255 };
    const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
    return (a + 0.05) / (b + 0.05);
  });
}

test('F-4 chooser: 원문 확인 only on procedures that end on the official text, with a legend', async ({ page }) => {
  await boot(page);
  const sg = await chooser(page);
  await expect(sg.locator('.sg-option')).toHaveCount(12);
  // structured common rules are no longer flagged
  for (const pid of ['residence_report', 'registration_info_report', 'card_reissue', 'extension', 'registration']) {
    await expect(sg.locator(`.sg-option[data-sg-value="${pid}"] .sg-state-source_only`), pid).toHaveCount(0);
  }
  for (const pid of ['visa_issuance', 'visa_issuance_confirmation', 'electronic_visa', 'status_grant', 'status_change', 'activities_outside_status', 'reentry']) {
    await expect(sg.locator(`.sg-option[data-sg-value="${pid}"] .sg-state-source_only`), pid).toHaveCount(1);
  }
  await expect(sg.locator('.sg-chip-legend')).toContainText('공식 원문');
});

test('F-4 → 사증발급 cites page 393 and shows that page verbatim, labelled as unreviewed', async ({ page }, info) => {
  await boot(page);
  const sg = await chooser(page);
  await sg.locator('.sg-option[data-sg-value="visa_issuance"]').click();
  const ans = page.locator('#statusGuidance[data-sg-kind="source-only"]');
  await expect(ans).toBeVisible({ timeout: 20_000 });
  await expect(ans.locator('.sg-btn-source')).toContainText('393');
  await expect(ans.locator('.sg-btn-source')).toHaveAttribute('data-sg-page', '393');
  // the honest state stays: no organised guidance, review notice present
  await expect(ans.locator('.sg-source-only .sg-lead')).toContainText('정리된 안내가 아직 없어요');
  await expect(ans).toContainText('참고용 안내예요 · 신청 전 공식 원문을 확인하세요');
  await expect(ans).not.toContainText(/검토 전|대조 검토|needs_review|approved/);
  const prev = ans.locator('.sg-source-preview');
  await expect(prev).toBeVisible({ timeout: 15_000 });
  await expect(prev.locator('.sg-preview-title')).toContainText('393');
  await expect(prev.locator('.sg-preview-note')).toContainText('공식 원문 그대로');
  await expect(prev.locator('.sg-source-excerpt')).toContainText('재외동포(F-4) 자격 기본 대상');
  // verbatim: every excerpt line occurs on the cited corpus page
  const lines = await prev.locator('.sg-source-excerpt p').allInnerTexts();
  const pageText = await page.evaluate(() => fetch('data/manual-corpus/visa_manual_2026_10_19_pdf.json').then((r) => r.json()).then((rows) => rows.find((r) => r.page === 393).text.replace(/\s+/g, ' ')));
  for (const l of lines.filter((x) => x !== '…')) expect(pageText, `not on p.393: ${l}`).toContain(l.replace(/\s+/g, ' ').trim());
  // one way into the full page: the answer's source button (the preview adds no second call to action)
  await expect(ans.locator('[data-sg-action="open-page"][data-sg-page="393"]')).toHaveCount(2);
  await ans.locator('.sg-btn-source').click();
  await expect(page.locator('#civicPageDialog[open]')).toContainText('393');
  await page.keyboard.press('Escape');
  await info.attach('f4-visa-issuance', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
});

test('the verbatim excerpt stays readable in every skin', async ({ page }) => {
  await boot(page);
  for (const skin of ['default', 'stamp', 'chrome', 'neon']) {
    // a fresh search each time: the result page restores the last search from session storage
    await page.evaluate((s) => { localStorage.setItem('visable:theme', s); sessionStorage.clear(); }, skin);
    await boot(page);
    await expect.poll(() => page.evaluate(() => document.documentElement.getAttribute('data-vt'))).toBe(skin);
    const sg = await chooser(page);
    await sg.locator('.sg-option[data-sg-value="visa_issuance"]').click();
    const ex = page.locator('#statusGuidance .sg-source-excerpt p').first();
    await expect(ex).toBeVisible({ timeout: 15_000 });
    expect(await contrast(ex), `${skin}: excerpt contrast`).toBeGreaterThanOrEqual(4.5);
    expect(await contrast(page.locator('#statusGuidance .sg-preview-title')), `${skin}: title contrast`).toBeGreaterThanOrEqual(4.5);
  }
});

test('related sources for 사증발급 come from the visa manual only', async ({ page }) => {
  await boot(page);
  const sg = await chooser(page);
  await sg.locator('.sg-option[data-sg-value="visa_issuance"]').click();
  await expect(page.locator('#statusGuidance[data-sg-kind="source-only"]')).toBeVisible({ timeout: 20_000 });
  const summary = page.locator('#civicRawSources summary');
  await expect(summary).toContainText(/\d/, { timeout: 15_000 });
  const n = Number((await summary.innerText()).replace(/[^\d]/g, ''));
  expect(n, 'related source count').toBeGreaterThan(0);
  expect(n, 'related source count').toBeLessThanOrEqual(25);
});
