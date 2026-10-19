import { test, expect } from '@playwright/test';

async function boot(page) {
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/immigration-checklists.html');
  await expect(page.locator('#count')).toContainText('224건');
  await expect(page.locator('.doc-card')).toHaveCount(30);
  return errors;
}
test('procedure filters and source-specific text are stable',async ({page})=>{
  const errors=await boot(page);
  await page.getByRole('radio',{name:'체류자격 변경'}).check();
  await expect(page.locator('#count')).toContainText('251건');
  await page.getByRole('radio',{name:'외국인등록·거소신고'}).check();
  await expect(page.locator('#count')).toContainText('172건');
  await page.getByRole('radio',{name:'체류기간 연장'}).check();
  await page.locator('#query').fill('E-7-1');
  await expect(page.locator('#count')).not.toContainText('0건');
  await expect(page.locator('.doc-card').first().locator('.code-pill')).toContainText('E-7');
  await expect(page.locator('.doc-card').first().locator('.doc-block').first()).toContainText('서류');
  expect(errors).toEqual([]);
});
test('narrow mobile viewport has no page-level horizontal overflow',async({page})=>{
  await boot(page);
  const metrics=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll('button')].filter(b=>b.getBoundingClientRect().width===0&&getComputedStyle(b).display!=='none').map(b=>b.id)}));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.width+2);
  await expect(page.getByRole('heading',{name:/내 상황에 맞는 서류/})).toBeVisible();
});
test('user local drafts require evidence notes and never publish an unapproved office assertion',async({page})=>{
  await boot(page);
  await page.locator('#office').selectOption('jeju');
  await expect(page.locator('#count')).toContainText('제주출입국');
  await expect(page.locator('.office-specific')).toHaveCount(0);
  await page.getByRole('button',{name:/문구 편집/}).first().click();
  await expect(page.locator('#edit-dialog')).toBeVisible();
  await page.locator('#edit-scope').selectOption('office');
  await expect(page.locator('#edit-office')).toHaveValue('jeju');
  await page.locator('textarea[name="required_text"]').fill('검증되지 않은 가상 서류: 모의검증용');
  await page.locator('textarea[name="editor_note"]').fill('2026-10-19 가상 데이터: 배포 금지');
  await page.getByRole('button',{name:'초안 저장'}).click();
  await expect(page.locator('.office-specific')).toContainText('관서별 편집 초안');
  await expect(page.locator('.office-specific')).toContainText('검증되지 않은 가상 서류');
  await expect(page.locator('.doc-card').first().locator('.doc-block').first()).not.toContainText('검증되지 않은 가상 서류');
  const draft=await page.evaluate(()=>JSON.parse(localStorage.getItem('visable.checklists.officeDrafts.v1')));
  expect(Object.values(draft)[0].review_state).toBe('DRAFT');
  const downloadPromise=page.waitForEvent('download');
  await page.locator('#export-office-drafts').click();
  const download=await downloadPromise;
  expect(download.suggestedFilename()).toContain('draft.json');
  await page.reload();
  await expect(page.locator('#count')).toContainText('224건');
  await page.locator('#office').selectOption('jeju');
  await expect(page.locator('.office-specific')).toContainText('검증되지 않은 가상 서류');
});
test('national wording edits never write to server and survive reload in local browser only',async({page})=>{
  await boot(page);
  const first=page.locator('.doc-card').first();
  await first.getByRole('button',{name:/문구 편집/}).click();
  await page.locator('textarea[name="required_text"]').fill('로컬 테스트 서류');
  await page.locator('textarea[name="editor_note"]').fill('QA용 테스트, 배포하지 않음');
  await page.getByRole('button',{name:'초안 저장'}).click();
  await expect(page.locator('.doc-card').first()).toContainText('로컬 테스트 서류');
  const downloadEvent=page.waitForEvent('download');
  await page.locator('#export-drafts').click();
  expect((await downloadEvent).suggestedFilename()).toBe('extension-202609.json');
  await page.reload();
  await expect(page.locator('.doc-card').first()).toContainText('로컬 테스트 서류');
});
test('slow-loading network allows typing before data resolves and fails gracefully',async({page})=>{
  await page.route('**/data/immigration-checklists/extension-202609.json',async(route)=>{
    await new Promise(resolve=>setTimeout(resolve,1200));
    await route.continue();
  });
  const failures=[];
  page.on('pageerror',err=>failures.push(err.message));
  await page.goto('/immigration-checklists.html');
  await page.locator('#query').fill('D-2');
  await expect(page.locator('#count')).toContainText('건');
  expect(failures).toEqual([]);
});
test('untrusted strings are rendered as text only',async({page})=>{
  await boot(page);
  await page.locator('.doc-card').first().getByRole('button',{name:/문구 편집/}).click();
  await page.locator('textarea[name="required_text"]').fill('<img src=x onerror="window.__xss=1">');
  await page.locator('textarea[name="editor_note"]').fill('Security QA');
  await page.getByRole('button',{name:'초안 저장'}).click();
  await expect(page.locator('.doc-card').first()).toContainText('<img src=x');
  expect(await page.evaluate(()=>window.__xss||0)).toBe(0);
});

test('guided discovery stepper: completes end-to-end user journey with progress tracking', async ({ page }) => {
  await boot(page);

  // 1. Initial State: Stepper Step 1 is active
  await expect(page.locator('#guided-step-1')).toBeVisible();
  await expect(page.locator('#guided-step-2')).toBeHidden();

  // 2. Procedure helper modal opens and closes cleanly
  await page.locator('#task-help-btn').click();
  await expect(page.locator('#task-help-dialog')).toBeVisible();
  await expect(page.locator('#task-help-dialog')).toContainText('출입국 행정 절차, 어떤 차이가 있나요?');
  await page.locator('#task-help-close').click();
  await expect(page.locator('#task-help-dialog')).toBeHidden();

  // 3. Flow A: Select Task 1 (체류기간 연장) -> advances to Step 2
  await page.locator('.task-card[data-procedure="extension"]').click();
  await expect(page.locator('#guided-step-1')).toBeHidden();
  await expect(page.locator('#guided-step-2')).toBeVisible();
  await expect(page.locator('.stepper-item[data-step="2"]')).toHaveClass(/active/);

  // 4. Flow B: ARC Visual Locator Tab switches cleanly
  await page.locator('#subtab-dont-know').click();
  await expect(page.locator('#subtab-panel-dont-know')).toBeVisible();
  await expect(page.locator('.arc-card-visual')).toBeVisible();
  await expect(page.locator('.arc-card-visual')).toContainText('체류자격 / SOJOURN STATUS');
  // Switch back to search tab
  await page.locator('#subtab-know').click();
  await expect(page.locator('#subtab-panel-know')).toBeVisible();

  // Select visa status via chip (D-2 유학) and then candidate card
  await page.locator('.popular-chip[data-code="D-2"]').first().click();
  await expect(page.locator('#status-candidate-grid .candidate-item-btn')).not.toHaveCount(0);
  await page.locator('#status-candidate-grid .candidate-item-btn').first().click();

  // 5. Flow C: Advances to Step 3 (Scenario Selection)
  await expect(page.locator('#guided-step-2')).toBeHidden();
  await expect(page.locator('#guided-step-3')).toBeVisible();
  await expect(page.locator('#scenario-selection-grid .scenario-choice-card')).not.toHaveCount(0);

  // Select first scenario card
  const firstScenario = page.locator('#scenario-selection-grid .scenario-choice-card').first();
  await firstScenario.click();

  // 6. Flow D: Advances to Step 4 (Personalized Checklist)
  await expect(page.locator('#guided-step-3')).toBeHidden();
  await expect(page.locator('#guided-step-4')).toBeVisible();
  await expect(page.locator('#summary-code-tag')).toContainText('D-2');
  await expect(page.locator('#progress-fraction')).toContainText('0 /');

  // Interactive Checklist: Check first document item and verify progress bar increases
  const firstCheckbox = page.locator('#baseline-docs-list .checklist-item input[type="checkbox"]').first();
  await firstCheckbox.check();
  await expect(page.locator('#progress-fraction')).toContainText('1 /');
  await expect(page.locator('#checklist-progress-fill')).not.toHaveAttribute('style', 'width: 0%');

  // Check another item if exists
  const count = await page.locator('#baseline-docs-list .checklist-item input[type="checkbox"]').count();
  if (count > 1) {
    await page.locator('#baseline-docs-list .checklist-item input[type="checkbox"]').nth(1).check();
    await expect(page.locator('#progress-fraction')).toContainText('2 /');
  }

  // Office selection updates checklist office advisory
  await page.locator('#checklist-office-select').selectOption('seoul');
  await expect(page.locator('#office-docs-content')).toContainText('서울출입국·외국인청');

  // Restart stepper returns to Step 1
  await page.locator('#guided-reset-btn').click();
  await expect(page.locator('#guided-step-1')).toBeVisible();
  await expect(page.locator('#guided-step-4')).toBeHidden();
});

test('adversarial parsing: protects commas in parentheses, identifies alternatives and conditions', async ({ page }) => {
  await boot(page);
  const result = await page.evaluate(() => {
    const { splitParenSafe, parseRequiredDocsStructured } = window.__VISABLE_INTERNALS;
    const raw = '통합신청서, 체류지 입증서류(임대차계약서, 숙소제공확인서 등), 사업자등록증명 또는 고유번호증, 학위증명서(해당자에 한함)';
    const chunks = splitParenSafe(raw);
    const structured = parseRequiredDocsStructured(raw);
    return { chunks, structured };
  });

  // Verify commas inside parentheses were not split
  expect(result.chunks).toEqual([
    '통합신청서',
    '체류지 입증서류(임대차계약서, 숙소제공확인서 등)',
    '사업자등록증명 또는 고유번호증',
    '학위증명서(해당자에 한함)'
  ]);

  // Verify document semantics
  expect(result.structured.items[0].type).toBe('mandatory');
  expect(result.structured.items[1].type).toBe('mandatory');
  expect(result.structured.items[2].type).toBe('alternative');
  expect(result.structured.items[3].type).toBe('conditional');
});

test('F-5 permanent resident extension displays legal restriction notice and no checkboxes', async ({ page }) => {
  await boot(page);
  await page.locator('#query').fill('F-5');
  await expect(page.locator('.doc-card')).not.toHaveCount(0);

  const quickBtn = page.locator('.doc-card').first().locator('.card-quick-cta');
  await quickBtn.click();

  await expect(page.locator('#guided-step-4')).toBeVisible();
  await expect(page.locator('#summary-code-tag')).toContainText('F-5');
  await expect(page.locator('#baseline-docs-list .restriction-card')).toBeVisible();
  await expect(page.locator('#baseline-docs-list .restriction-card')).toContainText('신청 불가 또는 별도 절차 대상 안내');
  await expect(page.locator('#baseline-docs-list .restriction-card')).toContainText('10년 주기 영주증');

  // Must NOT render checkbox for ineligibility statement
  const checkboxes = page.locator('#baseline-docs-list input[type="checkbox"]');
  await expect(checkboxes).toHaveCount(0);
  await expect(page.locator('#progress-fraction')).toContainText('신청 제한 / 별도 절차 대상');
});

test('domestic change prohibitions render restriction cards with overseas consulate guidance', async ({ page }) => {
  await boot(page);
  await page.getByRole('radio', { name: '체류자격 변경' }).check();
  await page.locator('#query').fill('D-4-5');
  await expect(page.locator('.doc-card')).not.toHaveCount(0);

  const quickBtn = page.locator('.doc-card').first().locator('.card-quick-cta');
  await quickBtn.click();

  await expect(page.locator('#guided-step-4')).toBeVisible();
  await expect(page.locator('#baseline-docs-list .restriction-card')).toBeVisible();
  await expect(page.locator('#baseline-docs-list .restriction-card')).toContainText('신청 불가 또는 별도 절차 대상 안내');
  await expect(page.locator('#baseline-docs-list .restriction-card')).toContainText('재외공관을 통한 신규 사증');
  await expect(page.locator('#baseline-docs-list input[type="checkbox"]')).toHaveCount(0);
});

test('unlisted manual gap scenarios render advisory card without false checkboxes', async ({ page }) => {
  await boot(page);
  await page.getByRole('radio', { name: '체류자격 변경' }).check();
  await page.locator('#query').fill('C-3-1');
  await expect(page.locator('.doc-card')).not.toHaveCount(0);

  const quickBtn = page.locator('.doc-card').first().locator('.card-quick-cta');
  await quickBtn.click();

  await expect(page.locator('#guided-step-4')).toBeVisible();
  await expect(page.locator('#baseline-docs-list .unlisted-card')).toBeVisible();
  await expect(page.locator('#baseline-docs-list .unlisted-card')).toContainText('원문 매뉴얼 상 독립 제출서류 목록 미기재');
  await expect(page.locator('#baseline-docs-list input[type="checkbox"]')).toHaveCount(0);
});

test('office selection transparency and live editor diff preview behave accurately', async ({ page }) => {
  await boot(page);
  await page.locator('#query').fill('D-2-1');
  await expect(page.locator('.doc-card')).not.toHaveCount(0);

  // 1. Step 4 Office Transparency
  await page.locator('.doc-card').first().locator('.card-quick-cta').click();
  await expect(page.locator('#guided-step-4')).toBeVisible();
  await expect(page.locator('#office-status-badge')).toContainText('전국 기준 안내');

  await page.locator('#checklist-office-select').selectOption('incheon');
  await expect(page.locator('#office-status-badge')).toContainText('인천출입국·외국인청 전국 기준 안내');
  await expect(page.locator('#office-docs-content')).toContainText('이 관서에 대해 별도로 확인된 서류 차이가 아직 없습니다');

  // 2. Editor Live Diff Preview
  await page.locator('#guided-reset-btn').click();
  await page.locator('#query').fill('D-2-1');
  await page.locator('.doc-card').first().getByRole('button', { name: /문구 편집/ }).click();
  await expect(page.locator('#edit-dialog')).toBeVisible();

  const diffContainer = page.locator('#edit-diff-container');
  await expect(diffContainer).toBeHidden();

  // Modify text to trigger diff
  const reqText = page.locator('textarea[name="required_text"]');
  const originalVal = await reqText.inputValue();
  await reqText.fill(originalVal + '\n- 추가 검증 서류');
  await expect(diffContainer).toBeVisible();
  await expect(diffContainer).toContainText('수정 내용 실시간 미리보기 (원문 대비)');
  await expect(diffContainer).toContainText('+ 수정:');

  // Revert back
  await reqText.fill(originalVal);
  await expect(diffContainer).toBeHidden();
  await page.locator('#edit-cancel').click();
  await expect(page.locator('#edit-dialog')).toBeHidden();
});

