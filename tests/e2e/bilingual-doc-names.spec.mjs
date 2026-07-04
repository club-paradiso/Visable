// Real-browser QA for bilingual document-name display: the Korean canonical
// document name plus a glossary-verified translation in parentheses, shown in
// BOTH the Standard-mode procedure checklist (.doc-chk-item) and the Easy Mode
// document groups (.easy-doc-group) whenever the active locale isn't Korean.
//
// The translation always comes from data/i18n/official-terms.json — never
// invented — matched via index.html's findOfficialTermIdForKoreanLabel()
// (whitespace-normalized full-text match, or the existing document-family
// classifier only when its output is textually identical to a glossary term's
// Korean field). A term renders only when its confidence for the active
// locale is canonical/official/manual-derived/curated; needs-verification and
// fallback entries stay Korean-only. See renderAnnotatedDocLabel() (Standard
// docs-list-name / Easy Mode) and the doc_*-id-then-text-fallback annotation
// inside renderDocTags() (Standard procedure checklist).
import { test, expect } from '@playwright/test';

async function openCard(page, code) {
  await page.evaluate((c) => {
    const q = document.getElementById('q'); if (q) { q.disabled = false; q.value = c; }
    document.body.classList.add('searched');
    renderResults(c);
  }, code);
  const card = page.locator(`#rlist .vc[data-code="${code}"]`).first();
  await card.waitFor({ timeout: 15_000 });
  return card;
}

async function gotoReady(page) {
  await page.goto('/index.html');
  await page.waitForFunction(() => typeof dataReady !== 'undefined' && dataReady, null, { timeout: 30_000 });
}

test.describe('bilingual document names', () => {
  test('EN: Standard procedure checklist appends verified translations, skips needs-verification', async ({ page }) => {
    await gotoReady(page);
    await page.evaluate(async () => { await applyLanguage('en'); });
    const card = await openCard(page, 'D-2');
    const rows = await card.locator('.doc-chk-item span').allTextContents();
    expect(rows.some(r => r.includes('여권') && r.includes('(Passport)'))).toBeTruthy();
    expect(rows.some(r => r.includes('수수료') && r.includes('(Fee)'))).toBeTruthy();
    // 표준입학허가서's English candidate is marked needs-verification in the
    // glossary — it must stay Korean-only, never silently promoted to render.
    const admissionRow = rows.find(r => r.includes('표준입학허가서'));
    expect(admissionRow, '표준입학허가서 row present').toBeTruthy();
    expect(admissionRow).not.toContain('Admission Letter');
  });

  test('ZH-CN: same procedure checklist shows Chinese translations', async ({ page }) => {
    await gotoReady(page);
    await page.evaluate(async () => { await applyLanguage('zh-CN'); });
    const card = await openCard(page, 'D-2');
    const rows = await card.locator('.doc-chk-item span').allTextContents();
    expect(rows.some(r => r.includes('여권') && r.includes('(护照)'))).toBeTruthy();
    expect(rows.some(r => r.includes('수수료') && r.includes('(手续费)'))).toBeTruthy();
  });

  test('KO: no translation text is ever appended to the procedure checklist', async ({ page }) => {
    await gotoReady(page);
    await page.evaluate(async () => { await applyLanguage('ko'); });
    const card = await openCard(page, 'D-2');
    const rows = await card.locator('.doc-chk-item span').allTextContents();
    const KNOWN_TRANSLATIONS = ['Passport', 'Fee', 'Application Form', 'Residence Card'];
    expect(rows.some(r => KNOWN_TRANSLATIONS.some(t => r.includes(t)))).toBeFalsy();
  });

  test('EN: Easy Mode document groups show the same bilingual annotation with correct lang span', async ({ page }) => {
    await gotoReady(page);
    await page.evaluate(async () => { await applyLanguage('en'); });
    const card = await openCard(page, 'D-2');
    await card.locator('.view-mode-btn[data-card-mode="easy"]').click();
    await expect(card).toHaveClass(/card-mode-easy/);
    const items = card.locator('.easy-doc-group li');
    const html = (await items.allInnerTexts()).join(' | ');
    expect(html).toContain('통합신청서');
    const i18nSpan = card.locator('.easy-doc-group .doc-name-i18n').first();
    await expect(i18nSpan).toHaveAttribute('lang', 'en');
    await expect(i18nSpan).toHaveText(/Application Form/);
  });

  test('renderDocumentTabPanel (standalone docs-tabs path) annotates bilingual names directly', async ({ page }) => {
    // No current visa record exercises this renderer with non-empty document
    // fields end-to-end (the one non-procedure-owned record, YOUTH-STAY, has
    // empty documents_* fields) — unit-test the renderer function directly so
    // this surface's contract stays covered.
    await gotoReady(page);
    await page.evaluate(async () => { await applyLanguage('en'); });
    const html = await page.evaluate(() => {
      const fakeV = { code: 'TEST', cat: 'work', documents_initial: ['여권 사본', '수수료', '표준입학허가서'] };
      return renderDocumentTabPanel(fakeV, DOCUMENT_TAB_CONFIG[0], true);
    });
    expect(html).toContain('doc-name-i18n');
    expect(html).toContain('(Passport)');
    expect(html).toContain('(Fee)');
    expect(html).not.toContain('Standard Admission Letter');
  });

  test('every supported locale renders the E-9 procedure checklist without crashing or leaking raw objects', async ({ page }) => {
    await gotoReady(page);
    // Read the live-supported locale list from the manifest rather than a
    // hardcoded array, so a future locale addition is covered automatically.
    const LOCALES = await page.evaluate(() => I18N_MANIFEST.supportedLocales);
    for (const loc of LOCALES) {
      await page.evaluate(async (l) => { await applyLanguage(l); }, loc);
      const card = await openCard(page, 'E-9');
      const rows = await card.locator('.doc-chk-item span').allTextContents();
      expect(rows.length, `${loc}: rows present`).toBeGreaterThan(0);
      expect(rows.some(r => /undefined|\[object/.test(r)), `${loc}: no raw-object leak`).toBeFalsy();
    }
  });
});
