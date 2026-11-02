import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error; });
});

async function home(page) {
  await page.route('**/api/**', route => route.abort());
  await page.goto('/');
  await expect(page.locator('#civicLanding')).toHaveAttribute('data-cs-hydrated', /reused|rendered/);
  await page.waitForFunction(() => !!window.VisableReminderDialog && !!window.VisablePictograms);
  await page.waitForFunction(() => typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10);
  await page.evaluate(() => document.fonts.ready);
}
const reminder = page => page.locator('.cs-tools-core [data-cs-tool="reminders"]');
const geometry = page => page.evaluate(() => {
  const logo = document.querySelector('.cs-nav .cs-brand img').getBoundingClientRect();
  return { x: logo.x, y: logo.y + scrollY, width: logo.width, height: logo.height, scroll: scrollY, overflow: document.documentElement.scrollWidth - innerWidth };
});

test('an early reminder tap opens once and stays closed after deferred data arrives', async ({ page }) => {
  let release;
  const ready = new Promise(resolve => { release = resolve; });
  await page.route('**/api/**', route => route.abort());
  await page.route('**/data/i18n/**', async route => {
    await ready;
    await route.continue();
  });
  await page.goto('/', { waitUntil: 'commit' });
  await page.waitForFunction(() => !!window.VisableReminderDialog);
  await reminder(page).click();
  await expect(page.locator('#reminderDialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#reminderDialog')).not.toBeVisible();
  release();
  await page.waitForFunction(() => typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10);
  await expect(page.locator('#reminderDialog')).not.toBeVisible();
  await reminder(page).click();
  await expect(page.locator('#reminderDialog')).toBeVisible();
  await expect(page.locator('#reminderForm')).toHaveCount(1);
  await page.keyboard.press('Escape');
});

test('reminder popup restores focus, scrolling and logo geometry after repeated closes', async ({ page }) => {
  await home(page);
  const trigger = reminder(page);
  await trigger.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
  const before = await geometry(page);
  for (const method of ['button', 'escape', 'backdrop', 'button']) {
    // Pointer activation avoids the test driver's own automatic scrolling.
    const target = await trigger.boundingBox();
    await page.mouse.click(target.x + target.width / 2, target.y + target.height / 2);
    const popup = page.locator('#reminderDialog');
    await expect(popup).toBeVisible();
    await expect(page.locator('#reminderForm')).toHaveCount(1);
    const bounds = await popup.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.width).toBeLessThanOrEqual(page.viewportSize().width);
    expect(bounds.height).toBeLessThanOrEqual(page.viewportSize().height);
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab');
      expect(await page.evaluate(() => document.querySelector('#reminderDialog').contains(document.activeElement))).toBe(true);
    }
    if (method === 'escape') await page.keyboard.press('Escape');
    else if (method === 'backdrop') await page.mouse.click(1, 1);
    else await popup.locator('[data-vs-reminder-close]').click();
    await expect(popup).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await expect(page.locator('html')).not.toHaveClass(/vs-reminder-open/);
    const after = await geometry(page);
    for (const key of ['x', 'y', 'width', 'height', 'scroll']) expect(Math.abs(after[key] - before[key]), key).toBeLessThanOrEqual(1);
    expect(after.overflow).toBeLessThanOrEqual(1);
  }
});

test('reminders save, edit, export and delete in one persistent popup form', async ({ page }) => {
  await home(page);
  await reminder(page).click();
  await page.locator('#reminderType').selectOption('visa');
  await page.locator('#reminderDate').fill('2031-12-31');
  await page.locator('#reminderMemo').fill('QA calendar check');
  await page.locator('#reminderForm [type="submit"]').click();
  const item = page.locator('#reminderItems > li');
  await expect(item).toHaveCount(1);
  await page.keyboard.press('Escape');
  await reminder(page).click();
  await expect(item).toContainText('QA calendar check');
  const download = page.waitForEvent('download');
  await item.locator('button').filter({ hasText: /캘린더|Calendar/ }).click();
  const file = await download;
  expect(await readFile(await file.path(), 'utf8')).toContain('DTSTART;VALUE=DATE:20311231');
  await item.getByRole('button', { name: /수정|Edit/, exact: true }).click();
  await page.locator('#reminderDate').fill('2032-01-15');
  await page.locator('#reminderForm [type="submit"]').click();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('paradisoReminders'))[0].date)).toBe('2032-01-15');
  page.once('dialog', dialog => dialog.accept());
  await item.getByRole('button', { name: /삭제|Delete/, exact: true }).click();
  await expect(item).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.locator('#civicQuery')).toBeVisible();
});

test('reminder fields remain readable across all themes and brightness modes', async ({ page }) => {
  await home(page);
  for (const theme of ['default', 'stamp', 'chrome', 'neon']) {
    for (const mode of ['라이트', '다크']) {
      await page.locator('.cs-theme-home').click();
      await page.locator('#vt-civic-' + theme).click();
      await page.locator('#vtCivicPop button').filter({ hasText: new RegExp('^' + mode + '$') }).click();
      await page.locator('#vtCivicPop button[aria-label="닫기"]').click();
      await reminder(page).click();
      const contrasts = await page.locator('#reminderDialog input, #reminderDialog select').evaluateAll(fields => {
        const luminance = color => {
          const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(c => {
            c /= 255;
            return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
          });
          return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
        };
        return fields.map(field => {
          const style = getComputedStyle(field);
          const a = luminance(style.color), b = luminance(style.backgroundColor);
          return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
        });
      });
      contrasts.forEach(ratio => expect(ratio, theme + ' ' + mode).toBeGreaterThanOrEqual(4.5));
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      await page.keyboard.press('Escape');
    }
  }
});

test('pictograms survive utility opens, language rerenders and a search round trip', async ({ page }) => {
  await home(page);
  for (const action of ['open-jobcode-modal', 'open-jurisdiction-modal', 'open-hikorea-guide']) {
    await page.locator('.cs-tools-core [data-action="' + action + '"]').click();
    await expect(page.locator('.modal-overlay.active')).toBeVisible();
    await expect.poll(() => page.locator('.modal-overlay.active svg').count()).toBeGreaterThan(0);
    expect(await page.evaluate(() => {
      const walker = document.createTreeWalker(document.querySelector('.modal-overlay.active'), NodeFilter.SHOW_TEXT);
      let node;
      const remaining = [];
      while ((node = walker.nextNode())) {
        const parent = node.parentElement;
        if (!parent.closest('.vs-pictogram,svg,script,style,option') && parent.getClientRects().length && /\p{Emoji_Presentation}/u.test(node.nodeValue)) remaining.push(node.nodeValue);
      }
      return remaining;
    })).toEqual([]);
    await page.keyboard.press('Escape');
    await expect(page.locator('.modal-overlay.active')).toHaveCount(0);
  }
  await page.locator('.cs-lang-home').click();
  await page.locator('#csLangDialog [data-lang="en"]').click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await reminder(page).click();
  await expect(page.locator('#reminderDialog')).toContainText('Save reminder');
  await page.keyboard.press('Escape');
  await page.locator('.cs-lang-home').click();
  await page.locator('#csLangDialog [data-lang="ko"]').click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ko');
  await page.locator('#civicQuery').fill('D-2 연장');
  await page.locator('#civicSearchForm [type="submit"]').click();
  await expect(page.locator('#statusGuidance')).toBeVisible();
  await page.locator('#hero .logo-area').click();
  await expect(page.locator('#civicQuery')).toBeVisible();
  await reminder(page).click();
  await page.keyboard.press('Escape');
  const size = await geometry(page);
  expect(size.width).toBeGreaterThan(60);
  expect(size.overflow).toBeLessThanOrEqual(1);
  await expect(page.locator('#reminderForm')).toHaveCount(1);
});

const brands = [
  ['index.html', '.cs-nav .cs-brand img'],
  ['ai.html', '.vf-home img:visible'],
  ['new-home.html', '.vf-home img:visible'],
  ['form-helper.html', '.fh-brand img'],
  ['immigration-checklists.html', '.topbar .brand img'],
  ['manual.html', '.mr-brand img'],
  ['enforcement.html', '.topbar .brand img'],
  ['nationality-interview-hub.html', '.ni-brand-group .vs-brand-logo'],
  ['preview.html', '.pv-brand-group .vs-brand-logo'],
  ['knowledge-studio.html', '.ks-brand .vs-brand-logo'],
  ['content-studio.html', '.cs-header .vs-brand-logo'],
  ['agency-directory/index.html', 'header .vs-brand-logo']
];
for (const [path, selector] of brands) {
  test('brand remains loaded, proportional and inside the viewport: ' + path, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', route => route.abort());
    await page.goto('/' + path);
    const logo = page.locator(selector).first();
    await expect(logo).toBeVisible();
    await expect.poll(() => logo.evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
    const box = await logo.boundingBox();
    const naturalRatio = await logo.evaluate(img => img.naturalWidth / img.naturalHeight);
    expect(Math.abs(box.width / box.height - naturalRatio)).toBeLessThan(0.1);
    expect(box.x).toBeGreaterThanOrEqual(-1);
    expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width + 1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    expect(errors).toEqual([]);
  });
}
