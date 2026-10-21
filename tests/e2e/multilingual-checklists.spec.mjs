import { test, expect } from '@playwright/test';

test.describe('VISABLE R4 Multilingual & Accessibility Verification', () => {

  test('language dropdown changes UI across all 4 steps and persists to localStorage', async ({ page }) => {
    await page.goto('/immigration-checklists.html');
    await expect(page.locator('#count')).toContainText('224');

    // Default locale is Korean
    await expect(page.locator('#page-title')).toContainText('내 상황에 맞는 서류');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('업무 선택');

    // Switch to English
    await page.locator('#lang-select').selectOption('en');
    await expect(page.locator('#page-title')).toContainText('Immigration Documents');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('Procedure');
    await expect(page.locator('#stepper-btn-2 .step-label')).toHaveText('Visa Status');
    await expect(page.locator('#stepper-btn-3 .step-label')).toHaveText('Scenario');
    await expect(page.locator('#stepper-btn-4 .step-label')).toHaveText('Checklist');

    // Verify localStorage persistence
    const savedLang = await page.evaluate(() => localStorage.getItem('paradiso:language'));
    expect(savedLang).toBe('en');

    // Switch to Simplified Chinese
    await page.locator('#lang-select').selectOption('zh-CN');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('业务选择');
    await expect(page.locator('#step-1-title')).toContainText('出入境业务');

    // Switch to Vietnamese
    await page.locator('#lang-select').selectOption('vi');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('Chọn thủ tục');
    await expect(page.locator('#step-1-title')).toContainText('xuất nhập cảnh');

    // Switch to Indonesian
    await page.locator('#lang-select').selectOption('id');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('Pilih Prosedur');
    await expect(page.locator('#step-1-title')).toContainText('imigrasi');
  });

  test('URL parameter ?lang= respects requested language on initial load', async ({ page }) => {
    await page.goto('/immigration-checklists.html?lang=en');
    await expect(page.locator('#lang-select')).toHaveValue('en');
    await expect(page.locator('#page-title')).toContainText('Immigration Documents');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('Procedure');
  });

  test('Arabic (RTL) mode sets dir="rtl", rtl-layout class, and causes no horizontal scroll', async ({ page }) => {
    await page.goto('/immigration-checklists.html?lang=ar');
    await expect(page.locator('#lang-select')).toHaveValue('ar');

    const htmlDir = await page.evaluate(() => document.documentElement.dir);
    expect(htmlDir).toBe('rtl');

    const hasRtlClass = await page.evaluate(() => document.body.classList.contains('rtl-layout'));
    expect(hasRtlClass).toBe(true);

    // Verify no page-level horizontal overflow
    const metrics = await page.evaluate(() => ({
      width: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth
    }));
    expect(metrics.scroll).toBeLessThanOrEqual(metrics.width + 2);
  });

  test('Full 4-step guided journey in English preserves canonical Korean names alongside translations', async ({ page }) => {
    await page.goto('/immigration-checklists.html?lang=en');

    // Step 1: Click Extension task card
    await page.locator('.task-card[data-procedure="extension"]').click();
    await expect(page.locator('#guided-step-2')).toBeVisible();
    await expect(page.locator('#step-2-proc-badge')).toContainText('Extension of Stay');

    // Step 2: Search and select D-2
    await page.locator('#status-picker-input').fill('D-2');
    const d2Btn = page.locator('#status-candidate-grid button').first();
    await expect(d2Btn).toBeVisible();
    await expect(d2Btn).toContainText('D-2');
    await expect(d2Btn).toContainText('유학');
    await d2Btn.click();

    // Step 3: Verify scenario list
    await expect(page.locator('#guided-step-3')).toBeVisible();
    await expect(page.locator('#step-3-code-pill')).toHaveText('D-2');
    await expect(page.locator('#step-3-name-label')).toContainText('유학');

    // Select first scenario
    const scenarioCard = page.locator('#scenario-selection-grid button').first();
    await expect(scenarioCard).toBeVisible();
    await scenarioCard.click();

    // Step 4: Checklist view
    await expect(page.locator('#guided-step-4')).toBeVisible();
    await expect(page.locator('#step-4-title')).toHaveText('Personalized Document Checklist');

    // Statutory supremacy banner
    const legalBanner = page.locator('.legal-warning-banner');
    await expect(legalBanner).toBeVisible();
    await expect(legalBanner).toContainText('authoritative standard');

    // Check document item and progress tracker
    const checkbox = page.locator('.checklist-item input[type="checkbox"]').first();
    await checkbox.check();
    await expect(page.locator('#progress-fraction')).toContainText(/ready/i);

    // Link to form helper includes ?lang=en
    const formHelperLink = page.locator('a.checklist-form-helper-btn').first();
    if (await formHelperLink.count() > 0) {
      const href = await formHelperLink.getAttribute('href');
      expect(href).toContain('lang=en');
    }
  });

  test('Multilingual keyword search in Step 2 status picker', async ({ page }) => {
    await page.goto('/immigration-checklists.html?lang=en');
    await page.locator('.task-card[data-procedure="extension"]').click();

    // English keyword: "study"
    await page.locator('#status-picker-input').fill('study');
    await expect(page.locator('#status-candidate-grid')).toContainText('D-2');

    // Switch to Chinese and search Chinese keyword
    await page.locator('#lang-select').selectOption('zh-CN');
    await page.locator('#status-picker-input').fill('留学');
    await expect(page.locator('#status-candidate-grid')).toContainText('D-2');

    // Switch to Vietnamese and search Vietnamese keyword
    await page.locator('#lang-select').selectOption('vi');
    await page.locator('#status-picker-input').fill('du học');
    await expect(page.locator('#status-candidate-grid')).toContainText('D-2');
  });

  test('Cross-page preference sync from localStorage', async ({ page }) => {
    // Seed localStorage with Vietnamese
    await page.goto('/immigration-checklists.html');
    await page.evaluate(() => localStorage.setItem('paradiso:language', 'vi'));

    // Reload page and verify Vietnamese is applied
    await page.reload();
    await expect(page.locator('#lang-select')).toHaveValue('vi');
    await expect(page.locator('#stepper-btn-1 .step-label')).toHaveText('Chọn thủ tục');
  });

});
