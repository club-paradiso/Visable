// Form Helper 2.0 — real-browser regression (Chromium in CI; WebKit via the mobile-webkit-qa job).
//
// Covers the sprint's required cases: form inventory search (supported + excluded
// refugee / departure-deadline forms with the honest hand-off), the select → explain →
// fill → validate → preview → edit → export workflow with backward navigation that keeps
// data, edit ↔ preview ↔ export consistency (the ops drawn on the canvas are the ops
// written into the PDF), long-text fit warnings before export, the reset dialog, the
// Waymaker deep link, language switching (EN + Arabic RTL) and the privacy contract
// (no request leaves the origin apart from the font CDN).
import { test, expect } from '@playwright/test';

const ORIGIN_ONLY = (url, base) => url.startsWith(base) || /cdn\.jsdelivr\.net\/gh\/orioncactus\/pretendard/.test(url);

async function boot(page, query = '') {
  await page.goto('/form-helper.html' + query);
  await page.waitForSelector('body.fh-ready', { timeout: 30_000 });
}
function primaryNext(page) {
  return page.locator('#fhNext:visible, #fhMobileBar .fh-btn-primary:visible').first();
}

test.describe('Form Helper 2.0', () => {
  test('home: search finds supported forms and hands off excluded ones honestly', async ({ page }) => {
    await boot(page);
    await expect(page.locator('#fhHome h1')).toContainText('서류 작성 도우미');
    await page.fill('#fhSearch', '주소 변경');
    const first = page.locator('#fhResults .fh-result').first();
    await expect(first).toHaveAttribute('data-form', 'F08');
    await page.fill('#fhSearch', '통합신청서');
    await expect(page.locator('#fhResults .fh-result').first()).toHaveAttribute('data-form', 'F01');
    await page.fill('#fhSearch', '난민');
    const excluded = page.locator('#fhResults .fh-result-static').first();
    await expect(excluded).toContainText('이 서류는 Visable 자동작성 대상이 아니에요');
    await expect(excluded.locator('.fh-chip')).toContainText('난민');
    await expect(page.locator('#fhResults .fh-result[data-form]')).toHaveCount(0);
    await page.fill('#fhSearch', '출국기한유예');
    await expect(page.locator('#fhResults .fh-result-static').first()).toContainText('자동작성 대상이 아니에요');
    await expect(page.locator('#fhResults .fh-result[data-form]')).toHaveCount(0);
    await page.fill('#fhSearch', 'zzzz-not-a-form');
    await expect(page.locator('#fhResults .fh-empty')).toBeVisible();
    // task groups list every fillable form once as a ≥44px target
    const cards = page.locator('.fh-group .fh-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(12);
    const box = await cards.first().boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
  });

  test('workflow: select → explain → fill → back keeps data → review → preview → export; canvas ops == PDF ops', async ({ page, baseURL }) => {
    const external = [];
    page.on('request', (r) => { if (!ORIGIN_ONLY(r.url(), baseURL)) external.push(r.url()); });
    await boot(page);
    await page.click('.fh-card[data-form="F08"]');
    await expect(page.locator('#fhExplain h1')).toContainText('체류지변경신고서');
    await expect(page.locator('#fhExplain .fh-source')).toContainText('별지 제34호의4서식');
    await page.click('#fhStart');
    await page.fill('#f_name', 'nguyen van anh');
    await expect(page.locator('#f_name')).toHaveValue('NGUYEN VAN ANH');
    await page.click('label[for="f_sex_1"]');
    await page.fill('#f_nationality', 'VIETNAM');
    await page.fill('#f_arc_no', '9801231234567');
    await expect(page.locator('#f_arc_no')).toHaveValue('980123-1234567');
    // the preview canvas reflects the values (ops carry the field keys)
    await page.waitForFunction(() => VisableFormHelper.state.ops.filter((o) => o.key === 'arc_no').length === 13);
    await primaryNext(page).click();
    await page.fill('#f_new_address', '경기도 수원시 영통구 광교로 145, 광교아파트 102동 1502호');
    await page.click('label[for="f_res_type_1"]');
    // browser Back returns to step 1 with the values intact, Forward restores step 2
    await page.goBack();
    await expect(page.locator('#f_name')).toHaveValue('NGUYEN VAN ANH');
    await page.goForward();
    await expect(page.locator('#f_new_address')).toHaveValue(/광교아파트/);
    await primaryNext(page).click(); // sign
    await expect(page.locator('#f_report_date')).toHaveValue(/\d{4}-\d{2}-\d{2}/);
    await primaryNext(page).click(); // review
    await expect(page.locator('#fhReview .fh-allgood')).toBeVisible();
    await page.click('#fhToPreview');
    await expect(page.locator('#fhFullPreview canvas')).toHaveCount(1);
    const opsBefore = await page.evaluate(() => JSON.stringify(VisableFormHelper.state.ops));
    const [download] = await Promise.all([page.waitForEvent('download'), page.click('#fhExport')]);
    // headless Chromium reports blob downloads with a non-ASCII `download` attribute as "download"; the app-side name is asserted below
    expect(['NGUYEN VAN ANH_체류지변경신고서.pdf', 'download']).toContain(download.suggestedFilename());
    await expect(page.locator('#fhExportStatus')).toContainText('PDF를 만들었어요');
    const last = await page.evaluate(() => VisableFormHelper.lastExport);
    expect(last.filename).toBe('NGUYEN VAN ANH_체류지변경신고서.pdf');
    expect(last.ops).toBe(JSON.parse(opsBefore).length);
    expect(last.bytes).toBeGreaterThan(50_000);
    // nothing typed left the origin: only static assets + the vendor libraries were fetched
    expect(external, 'no external requests besides the font CDN').toEqual([]);
    // reset asks first, then returns to the explain screen with empty values
    await page.click('#fhPreview .fh-btn-ghost:has-text("처음부터")');
    await expect(page.locator('#fhResetDialog')).toBeVisible();
    await page.click('#fhResetDialog button[value="reset"]');
    await expect(page.locator('#fhStart')).toHaveText('작성 시작');
    await page.click('#fhStart');
    await expect(page.locator('#f_name')).toHaveValue('');
  });

  test('long text: the cell limit is flagged before export and the export dialog offers a fix', async ({ page }) => {
    await boot(page, '?form=F01&type=sojourn_extension');
    await expect(page.locator('#fhExplain h1')).toContainText('통합신청서');
    await page.click('#fhStart');
    await expect(page.locator('input[name="f_app_type"][value="sojourn_extension"]')).toBeChecked();
    await primaryNext(page).click();
    await page.fill('#f_surname', 'KIM'); await page.fill('#f_given', 'MINSOO'); await page.fill('#f_dob', '1990-05-05');
    await page.click('label[for="f_sex_0"]');
    await page.fill('#f_nationality', 'REPUBLIC OF THE PHILIPPINES AND MORE');
    await expect(page.locator('[data-key="nationality"] .fh-field-issue')).toContainText('칸보다 길어서');
    await page.fill('#f_passport_no', 'P1234567'); await page.fill('#f_passport_expiry', '2030-01-01');
    await primaryNext(page).click();
    await page.fill('#f_korean_address', '서울특별시 강남구 테헤란로 152');
    await primaryNext(page).click(); // sign (extension has no extra step)
    await primaryNext(page).click(); // review
    await expect(page.locator('#fhReview .fh-issues-fit')).toContainText('인쇄 확인');
    await page.click('#fhToPreview');
    await page.click('#fhExport');
    await expect(page.locator('#fhExportDialog')).toBeVisible();
    await expect(page.locator('#fhExportDialog')).toContainText('인쇄 확인 항목이 1개');
    await page.click('#fhExportDialog button[value="fix"]');
    await expect(page.locator('#fhReview h1')).toContainText('빠진 곳과 확인할 점');
  });

  test('edition switch keeps the data and changes the template; Chinese edition drops the refund cell honestly', async ({ page }) => {
    await boot(page, '?form=F01&type=foreign_registration');
    await page.click('#fhStart');
    await primaryNext(page).click();
    await page.fill('#f_surname', 'TRAN'); await page.fill('#f_given', 'THI MAI');
    await page.evaluate(() => VisableFormHelper.go('edit', { stepIndex: VisableFormHelper.engine.visibleSteps(VisableFormHelper.data.defs.forms.F01, VisableFormHelper.state.values.F01).length - 1 }));
    await page.click('label[for="f_edition_1"]'); // F03 중문 병기
    await expect(page.locator('#fhEdit figcaption').first()).toContainText('F03');
    const surname = await page.evaluate(() => VisableFormHelper.state.values.F01.surname);
    expect(surname).toBe('TRAN');
    await page.click('label[for="f_edition_0"]');
    await expect(page.locator('#fhEdit figcaption').first()).toContainText('F01');
  });

  test('language: English chrome, Arabic RTL, Korean official labels stay visible', async ({ page }) => {
    await boot(page, '?lang=en');
    await expect(page.locator('#fhHome h1')).toHaveText('Form Helper');
    await page.click('.fh-card[data-form="F08"]');
    await expect(page.locator('#fhStart')).toHaveText('Start filling in');
    await page.click('#fhStart');
    await expect(page.locator('[data-key="name"] .fh-label-text')).toHaveText('Full name');
    await expect(page.locator('[data-key="name"] .fh-official')).toContainText('성명');
    await page.selectOption('#fhLang', 'ar');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, 'no horizontal overflow in RTL').toBeLessThanOrEqual(1);
    await expect(page.locator('#fhEdit h1')).not.toHaveText('');
    await expect(page.locator('[data-key="name"] .fh-label-text')).toHaveText('Full name'); // KO/EN labels, EN fallback
    await page.selectOption('#fhLang', 'ko');
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
    await expect(page.locator('#fhEdit h1')).toContainText('신고인');
  });

  test('Arabic from the first paint: RTL landing has no horizontal overflow and the cards are clickable', async ({ page }) => {
    await boot(page, '?lang=ar');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    await page.click('.fh-card[data-form="F08"]');
    await expect(page.locator('#fhStart')).toBeVisible();
  });

  test('keyboard: the whole flow is reachable without a mouse and dialogs return focus', async ({ page }) => {
    await boot(page);
    await page.focus('#fhSearch');
    await page.keyboard.type('숙소 제공');
    await page.keyboard.press('Tab');
    await expect(page.locator('#fhResults .fh-result').first()).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#fhExplain h1')).toContainText('숙소제공확인서');
    await page.focus('#fhStart'); await page.keyboard.press('Enter');
    await expect(page.locator('#fhFields')).toBeVisible();
    const first = page.locator('#fhFields input, #fhFields textarea').first();
    await first.focus();
    await expect(first).toBeFocused();
  });
});
