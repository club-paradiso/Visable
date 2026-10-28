// Restore Trust (2026-10-28): the F-4 재외동포 result path, before/after contract.
//
//   * the procedure chooser marks 원문 확인 only where picking it really ends on the
//     official text, and explains what the mark means (10 of 12 at the start, 4 now);
//   * 사증발급 renders the documents transcribed from the F-4 visa section and cites
//     pp. 393–394, never the handbook cover (383);
//   * a procedure the manual gives no list for (체류자격 부여, p.532) shows that page
//     verbatim, from the F-4 lines, readable in every skin — nothing is invented;
//   * no internal review label reaches the page; one plain reference line stays;
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
  for (const pid of ['extension', 'registration', 'status_change', 'activities_outside_status', 'residence_report', 'registration_info_report', 'card_reissue', 'visa_issuance']) {
    await expect(sg.locator(`.sg-option[data-sg-value="${pid}"] .sg-state-source_only`), pid).toHaveCount(0);
  }
  for (const pid of ['visa_issuance_confirmation', 'electronic_visa', 'status_grant', 'reentry']) {
    await expect(sg.locator(`.sg-option[data-sg-value="${pid}"] .sg-state-source_only`), pid).toHaveCount(1);
  }
  await expect(sg.locator('.sg-chip-legend')).toContainText('공식 원문');
});

test('F-4 → 사증발급 lists the transcribed documents and cites pages 393–394, never the cover', async ({ page }, info) => {
  await boot(page);
  const sg = await chooser(page);
  await sg.locator('.sg-option[data-sg-value="visa_issuance"]').click();
  const ans = page.locator('#statusGuidance[data-sg-kind="resolved"]');
  await expect(ans).toBeVisible({ timeout: 20_000 });
  await expect(ans).not.toContainText('정리된 안내가 아직 없어요');
  await expect(ans.locator('.sg-docs')).toContainText('한국어능력 입증서류');
  await expect(ans.locator('.sg-docs')).toContainText('외국국적동포임을 증명하는 서류');
  await expect(ans.locator('.sg-docs')).toContainText('393쪽');
  await expect(ans.locator('.sg-docs')).toContainText('394쪽');
  await expect(ans).not.toContainText('383쪽');
  await expect(ans).toContainText('40세가 되는 해');   // the military-service restriction stays with the rule
  await expect(ans).toContainText('참고용 안내예요 · 신청 전 공식 원문을 확인하세요');
  await expect(ans).not.toContainText(/검토 전|대조 검토|needs_review|approved/);
  await info.attach('f4-visa-issuance', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
});

test('F-4 → 체류자격 부여 (no list in the manual) shows page 532 verbatim from the F-4 lines', async ({ page }) => {
  await boot(page);
  const sg = await chooser(page);
  await sg.locator('.sg-option[data-sg-value="status_grant"]').click();
  const ans = page.locator('#statusGuidance[data-sg-kind="source-only"]');
  await expect(ans).toBeVisible({ timeout: 20_000 });
  await expect(ans.locator('.sg-source-only .sg-lead')).toContainText('정리된 안내가 아직 없어요');
  await expect(ans.locator('.sg-btn-source')).toHaveAttribute('data-sg-page', '532');
  const prev = ans.locator('.sg-source-preview');
  await expect(prev).toBeVisible({ timeout: 15_000 });
  await expect(prev.locator('.sg-preview-title')).toContainText('532');
  await expect(prev.locator('.sg-preview-note')).toContainText('공식 원문 그대로');
  const lines = (await prev.locator('.sg-source-excerpt p').allInnerTexts()).filter((x) => x !== '…');
  expect(lines[0], 'the excerpt starts at the F-4 lines, not the H-2 text above them').toContain('F-4');
  const pageText = await page.evaluate(() => fetch('data/manual-corpus/stay_manual_2026_10_19_pdf.json').then((r) => r.json()).then((rows) => rows.find((r) => r.page === 532).text.replace(/[\uE000-\uF8FF\u{F0000}-\u{FFFFD}]/gu, '').replace(/\s+/g, ' ')));
  for (const l of lines) expect(pageText, `not on p.532: ${l}`).toContain(l.replace(/\s+/g, ' ').trim());
  await expect(ans.locator('[data-sg-action="open-page"][data-sg-page="532"]')).toHaveCount(2);
});

test('the verbatim excerpt stays readable in every skin', async ({ page }) => {
  await boot(page);
  for (const skin of ['default', 'stamp', 'chrome', 'neon']) {
    // a fresh search each time: the result page restores the last search from session storage
    await page.evaluate((s) => { localStorage.setItem('visable:theme', s); sessionStorage.clear(); }, skin);
    await boot(page);
    await expect.poll(() => page.evaluate(() => document.documentElement.getAttribute('data-vt'))).toBe(skin);
    const sg = await chooser(page);
    await sg.locator('.sg-option[data-sg-value="status_grant"]').click();
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
  await expect(page.locator('#statusGuidance[data-sg-kind="resolved"]')).toBeVisible({ timeout: 20_000 });
  // structured answers keep the evidence (and the related sources inside it) collapsed until opened
  await page.locator('#sgEvidence > summary').click();
  const summary = page.locator('#civicRawSources summary');
  await expect(summary).toContainText(/\d/, { timeout: 15_000 });
  const n = Number((await summary.innerText()).replace(/[^\d]/g, ''));
  expect(n, 'related source count').toBeGreaterThan(0);
  expect(n, 'related source count').toBeLessThanOrEqual(25);
});
