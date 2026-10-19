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
