// Search-first home: the combobox on #civicQuery and the suggestions under it.
//
//   * hierarchy: no pre/post journey cards, one primary field, a few examples,
//     tools below, disclosures intact, no horizontal overflow (320–1280);
//   * the mandatory query matrix in a real browser (codes, subcodes, spacing
//     variants, status × procedure, situations in Korean and English, issuance
//     vs extension, tools, unknown codes, empty input);
//   * WAI-ARIA combobox: arrows, Enter, Escape, Tab, aria-activedescendant,
//     live count, clear button, Korean IME composition never selects/submits;
//   * history and resilience: Back/Forward/refresh, rapid successive queries,
//     language switch, slow or missing suggestion index, backend and AI down;
//   * privacy: typing sends nothing over the network.
import { test, expect } from '@playwright/test';

async function bootHome(page, url = '/index.html') {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto(url);
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery') && !!window.VisableCivicSearch && !!window.VisableSearchSuggest; } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}
const options = (page) => page.locator('#civicSuggest [role="option"]');
async function typeQuery(page, text) {
  const input = page.locator('#civicQuery');
  await input.click();
  await input.fill('');
  await input.pressSequentially(text, { delay: 15 });
}
async function firstOption(page, text) {
  await typeQuery(page, text);
  await expect(options(page).first()).toBeVisible();
  return options(page).first();
}

test.describe('search-first hierarchy', () => {
  test('one primary search, examples, compact tools and the disclosures; no journey cards', async ({ page }) => {
    await bootHome(page);
    await expect(page.locator('.cs-route, .cs-journey')).toHaveCount(0);
    await expect(page.locator('#civicLanding')).not.toContainText('한국 입국 후');
    await expect(page.locator('#civicLanding [role="search"]')).toHaveCount(1);
    const input = page.locator('#civicQuery');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('role', 'combobox');
    await expect(input).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('.cs-suggest')).toBeHidden();
    const examples = page.locator('.cs-examples button:visible, .cs-example-link:visible');
    const n = await examples.count();
    expect(n).toBeGreaterThanOrEqual(3);
    expect(n).toBeLessThanOrEqual(page.viewportSize().width <= 680 ? 4 : 5);
    await expect(page.locator('.cs-examples-label')).toHaveText('이렇게 검색해 보세요');
    await expect(page.locator('.cs-footer')).toContainText('공식 정부 서비스가 아닙니다');
    await expect(page.locator('.cs-source-strip a')).toHaveCount(2);
    const layout = await page.evaluate(() => {
      const bar = document.querySelector('.cs-searchbar').getBoundingClientRect();
      const tools = document.querySelector('.cs-tools').getBoundingClientRect();
      return { overflow: document.documentElement.scrollWidth - innerWidth, barAboveTools: bar.bottom < tools.top, barInFirstScreen: bar.bottom <= innerHeight };
    });
    expect(layout.overflow).toBeLessThanOrEqual(1);
    expect(layout.barAboveTools).toBe(true);
    expect(layout.barInFirstScreen).toBe(true);
  });

  test('examples search; the forms example opens Form Helper', async ({ page }) => {
    await bootHome(page);
    await page.locator('.cs-examples button[data-cs-query="주소 변경 신고"]').click();
    await expect(page.locator('body')).toHaveClass(/searched/);
    await expect(page.locator('#q')).toHaveValue('주소 변경 신고');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
    await bootHome(page);
    await page.locator('.cs-example-link').click();
    await expect(page).toHaveURL(/form-helper\.html$/);
  });
});

test.describe('query matrix', () => {
  const CASES = [
    ['E-7-1', /^E-7-1 전문인력/, '세부 자격'],
    ['e 7 1', /^E-7-1 전문인력/, '세부 자격'],
    ['F-6 체류기간 연장', /^F-6 체류기간 연장/, '절차'],
    ['D-2 외국인등록', /^D-2 외국인등록/, '절차'],
    ['주소 바꿨어요', /^체류지 변경 신고/, '절차'],
    ['I changed my workplace', /^근무처 변경·추가/, '절차'],
    ['G-1-5', /^G-1-5 난민신청자/, '세부 자격'],
    ['C-3 비자 발급', /^C-3 사증발급/, '절차'],
    ['E-7-4 소득', /^E-7-4 /, '세부 자격'],
    ['통합신청서', /필수 서류 작성/, '도구'],
  ];
  for (const [query, label, kind] of CASES) {
    test(`"${query}" → ${label}`, async ({ page }) => {
      await bootHome(page);
      const first = await firstOption(page, query);
      await expect(first.locator('.cs-sug-label')).toHaveText(label);
      await expect(first.locator('.cs-sug-kind')).toHaveText(kind);
      if (query === 'G-1-5') await expect(first.locator('.cs-sug-sub')).toContainText('G-1 기타(난민등)의 세부 자격');
      if (query === 'C-3 비자 발급') {
        await expect(first.locator('.cs-sug-sub')).toContainText('입국 전 · 사증');
        await expect(options(page).filter({ hasText: '연장' })).toHaveCount(0);
      }
      if (query === 'E-7-4 소득') await expect(options(page).filter({ hasText: /^E-7 특정활동/ })).toHaveCount(0);
    });
  }

  test('XYZ-999 is never matched: a note, no options, and Enter still searches', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'XYZ-999');
    await expect(page.locator('.cs-suggest-note')).toContainText('XYZ-999');
    await expect(options(page)).toHaveCount(0);
    await expect(page.locator('#civicQuery')).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('.cs-suggest-foot')).toContainText('Enter');
    await page.keyboard.press('Enter');
    await expect(page.locator('body')).toHaveClass(/searched/);
  });

  test('an empty query never submits or opens an empty panel', async ({ page }) => {
    await bootHome(page);
    await page.locator('#civicQuery').click();
    await page.keyboard.press('Enter');
    await page.locator('#civicSearchForm .cs-submit').click();
    await page.keyboard.type('   ');
    await page.keyboard.press('Enter');
    await expect(page.locator('body')).not.toHaveClass(/searched/);
    await expect(page.locator('.cs-suggest')).toBeHidden();
    await expect(page.locator('#civicQuery')).toBeFocused();
  });

  test('the Form Helper suggestion navigates to the tool', async ({ page }) => {
    await bootHome(page);
    const first = await firstOption(page, '통합신청서');
    await first.click();
    await expect(page).toHaveURL(/form-helper\.html$/);
  });

  test('dialog tools open the existing dialogs from the keyboard (visit reservations, immigration office)', async ({ page }) => {
    await bootHome(page);
    for (const [query, overlay] of [['방문예약', '#hikoreaGuideOverlay'], ['관할 출입국관서', '#jurisdictionModalOverlay']]) {
      const first = await firstOption(page, query);
      await expect(first.locator('.cs-sug-kind')).toHaveText('도구');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
      await expect(page.locator(overlay)).toHaveClass(/active/);
      await page.evaluate((id) => closeModal(id), overlay.slice(1));
    }
  });
});

test.describe('combobox behaviour', () => {
  test('arrows move the active option, Enter opens it, Escape closes, Tab leaves', async ({ page }) => {
    await bootHome(page);
    const input = page.locator('#civicQuery');
    await typeQuery(page, 'E-7');
    await expect(options(page).first()).toBeVisible();
    await expect(input).toHaveAttribute('aria-expanded', 'true');
    const count = await options(page).count();
    expect(count).toBeGreaterThanOrEqual(3);
    await page.keyboard.press('ArrowDown');
    await expect(input).toHaveAttribute('aria-activedescendant', 'civicSuggest-0');
    await expect(options(page).nth(0)).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('ArrowUp'); // wraps to the last option
    await expect(input).toHaveAttribute('aria-activedescendant', `civicSuggest-${count - 1}`);
    await page.keyboard.press('ArrowDown'); // wraps back to the first
    await expect(input).toHaveAttribute('aria-activedescendant', 'civicSuggest-0');
    await page.keyboard.press('Escape');
    await expect(page.locator('.cs-suggest')).toBeHidden();
    await expect(input).toHaveAttribute('aria-expanded', 'false');
    await expect(input).not.toHaveAttribute('aria-activedescendant', /.+/);
    await expect(input).toHaveValue('E-7');
    await page.keyboard.press('ArrowDown'); // reopens on the first option
    await expect(input).toHaveAttribute('aria-activedescendant', 'civicSuggest-0');
    await page.keyboard.press('ArrowDown');
    const second = await options(page).nth(1).locator('.cs-sug-label').innerText();
    await page.keyboard.press('Enter');
    await expect(page.locator('body')).toHaveClass(/searched/);
    await expect(page.locator('#q')).toHaveValue(second);
    await expect(page).toHaveURL(/[?&]q=/);
  });

  test('Tab closes the panel and moves focus on; clicking outside closes it', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'F-6');
    await expect(options(page).first()).toBeVisible();
    await page.keyboard.press('Tab');
    await expect(page.locator('.cs-suggest')).toBeHidden();
    await expect(page.locator('#civicQuery')).not.toBeFocused();
    await typeQuery(page, 'F-6');
    await expect(options(page).first()).toBeVisible();
    // outside the field and the panel (the headline is folded away in the phone search sheet)
    await page.locator('.cs-hero > .cs-basis').click();
    await expect(page.locator('.cs-suggest')).toBeHidden();
  });

  test('Enter without an active option searches exactly what was typed', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'F-6 체류기간 연장');
    await expect(options(page).first()).toBeVisible();
    await page.keyboard.press('Enter');
    await expect(page.locator('#q')).toHaveValue('F-6 체류기간 연장');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  });

  test('the clear button empties the field, keeps focus and brings the examples back', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, '외국인등록');
    await expect(page.locator('.cs-examples')).toBeHidden();
    const clear = page.locator('[data-cs-clear]');
    await expect(clear).toBeVisible();
    await expect(clear).toHaveAttribute('aria-label', '검색어 지우기');
    await clear.click();
    await expect(page.locator('#civicQuery')).toHaveValue('');
    await expect(page.locator('#civicQuery')).toBeFocused();
    await expect(clear).toBeHidden();
    await expect(page.locator('.cs-suggest')).toBeHidden();
    await expect(page.locator('.cs-examples')).toBeVisible();
  });

  test('screen readers get the listbox name, option roles and a settled count', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'F-6 연장');
    await expect(page.locator('#civicSuggest')).toHaveAttribute('role', 'listbox');
    await expect(page.locator('#civicSuggest')).toHaveAttribute('aria-label', '검색 제안');
    await expect(page.locator('[data-cs-suggest-status]')).toHaveText(/제안 \d+개/, { timeout: 3_000 });
    const n = await options(page).count();
    for (let i = 0; i < n; i++) await expect(options(page).nth(i)).toHaveAttribute('aria-selected', /true|false/);
  });

  test('Korean IME composition never selects a suggestion or submits', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'F-6');
    await expect(options(page).first()).toBeVisible();
    const submitted = await page.evaluate(async () => {
      const el = document.getElementById('civicQuery');
      const key = (init) => el.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init }));
      el.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: '' }));
      el.value = 'F-6 ㅇ'; el.dispatchEvent(new InputEvent('input', { bubbles: true, isComposing: true, data: 'ㅇ', inputType: 'insertCompositionText' }));
      el.value = 'F-6 연'; el.dispatchEvent(new InputEvent('input', { bubbles: true, isComposing: true, data: '연', inputType: 'insertCompositionText' }));
      key({ key: 'ArrowDown', isComposing: true, keyCode: 229 });
      key({ key: 'Enter', isComposing: true, keyCode: 229 });
      el.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '연' }));
      // Safari: the committing Enter arrives after compositionend with isComposing false and keyCode 229
      key({ key: 'Enter', isComposing: false, keyCode: 229 });
      await new Promise((r) => setTimeout(r, 50));
      return { searched: document.body.classList.contains('searched'), active: el.getAttribute('aria-activedescendant'), value: el.value };
    });
    expect(submitted).toEqual({ searched: false, active: null, value: 'F-6 연' });
    // after the composition, suggestions follow the committed text and a real Enter searches it
    await expect(options(page).first().locator('.cs-sug-label')).toHaveText(/^F-6/);
    await page.locator('#civicQuery').press('Enter');
    await expect(page.locator('#q')).toHaveValue('F-6 연');
  });

  test('suggestions render well inside the 150 ms target once the index is loaded', async ({ page }) => {
    await bootHome(page);
    await page.waitForFunction(() => window.VisableCivicSearch.suggestions.state().ready, null, { timeout: 10_000 });
    for (const q of ['E', 'E-7', 'F-6 체류기간 연장', '주소 바꿨어요', 'I changed my workplace']) {
      await typeQuery(page, q);
      await expect(options(page).first()).toBeVisible();
      const ms = await page.evaluate(() => window.VisableCivicSearch.suggestions.state().renderMs);
      expect(ms, `${q} rendered in ${ms} ms`).toBeLessThan(150);
    }
  });
});

test.describe('history, language and resilience', () => {
  test('Back returns to the search home; Forward and refresh restore the result', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'F-6 연장');
    await page.keyboard.press('Enter');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
    await expect(page).toHaveURL(/q=F-6/);
    await page.goBack();
    await expect(page.locator('body')).not.toHaveClass(/searched/);
    await expect(page.locator('#civicQuery')).toBeVisible();
    await expect(page.locator('#civicLanding')).toBeVisible();
    await page.goForward();
    await expect(page.locator('body')).toHaveClass(/searched/);
    await expect(page.locator('#q')).toHaveValue('F-6 연장');
    await page.reload();
    await expect(page.locator('#q')).toHaveValue('F-6 연장', { timeout: 20_000 });
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  });

  test('rapid successive queries never leave stale suggestions or results', async ({ page }) => {
    await bootHome(page);
    const input = page.locator('#civicQuery');
    await input.click();
    for (const q of ['E-7', 'E-7-4', 'D-2', 'F-6 연장']) { await input.fill(q); }
    await expect(options(page).first().locator('.cs-sug-label')).toHaveText(/^F-6 체류기간 연장/);
    await expect(options(page).filter({ hasText: /^E-7/ })).toHaveCount(0);
    await page.keyboard.press('Enter');
    await page.fill('#q', 'E-7-4');
    await page.fill('#q', 'D-2 외국인등록');
    await page.press('#q', 'Enter');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toContainText('D-2', { timeout: 20_000 });
    await expect(page.locator('#statusGuidance .sg-interp')).not.toContainText('F-6');
  });

  test('a language switch keeps the draft and suggests in that language', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'E-7');
    // on phones the search sheet folds the language control away: 닫기 first, as a person would
    if (await page.locator('[data-cs-sheet-close]').isVisible()) await page.locator('[data-cs-sheet-close]').click();
    await page.locator('[data-cs-lang-open]:visible').first().click();
    await page.locator('#csLangDialog .cs-lang-option[data-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.locator('#civicQuery')).toHaveValue('E-7');
    await expect(page.locator('[data-cs-clear]')).toBeVisible();
    await page.locator('#civicQuery').click();
    await page.keyboard.press('ArrowDown');
    await expect(options(page).first().locator('.cs-sug-label')).toHaveText('E-7 Specially Designated Activities');
    await expect(options(page).first().locator('.cs-sug-kind')).toHaveText('Status');
    await expect(page.locator('#civicSuggest')).toHaveAttribute('aria-label', 'Search suggestions');
  });

  test('other locales say which language suggestions use (ja)', async ({ page }) => {
    await bootHome(page, '/index.html?lang=ja');
    await expect(page.locator('html')).toHaveAttribute('lang', 'ja');
    const first = await firstOption(page, 'F-6');
    await expect(first.locator('.cs-sug-kind')).toHaveText('在留資格');
    await expect(first.locator('.cs-sug-label')).toHaveAttribute('lang', 'en');
    await expect(page.locator('.cs-suggest-foot')).toContainText('韓国語・英語');
  });

  test('a slow suggestion index: typing early still gets suggestions once it arrives', async ({ page }) => {
    await page.route('**/data/search-suggest-index.json', async (route) => { await new Promise((r) => setTimeout(r, 1500)); await route.continue(); });
    await bootHome(page);
    await page.locator('#civicQuery').click();
    await page.keyboard.type('D-2 외국인등록');
    await expect(options(page).first().locator('.cs-sug-label')).toHaveText(/^D-2 외국인등록/, { timeout: 10_000 });
  });

  test('a missing suggestion index disables suggestions only; the search still works', async ({ page }) => {
    await page.route('**/data/search-suggest-index.json', (route) => route.abort());
    await bootHome(page);
    await typeQuery(page, 'F-6 연장');
    await page.waitForTimeout(400);
    await expect(page.locator('.cs-suggest')).toBeHidden();
    await page.keyboard.press('Enter');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  });

  test('with the backend and every AI provider down, suggestions and grounded results still work', async ({ page }) => {
    await page.route('**/*', (route) => {
      const url = route.request().url();
      if (/\/api\/|railway\.app|anthropic|openai|googleapis\.com\/v1/.test(url)) return route.abort();
      return route.continue();
    });
    await bootHome(page);
    const first = await firstOption(page, 'D-2 외국인등록');
    await first.click();
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('#statusGuidance')).toContainText('D-2');
  });

  test('typing sends nothing over the network', async ({ page }) => {
    await bootHome(page);
    await page.waitForFunction(() => window.VisableCivicSearch.suggestions.state().ready, null, { timeout: 10_000 });
    const seen = [];
    page.on('request', (req) => seen.push(req.url()));
    await typeQuery(page, '비자 연장하려면 뭐 필요해 secretword');
    await expect(page.locator('.cs-suggest')).toBeVisible();
    await page.waitForTimeout(300);
    expect(seen.filter((u) => /secretword|%EB%B9%84%EC%9E%90|\/api\//i.test(u))).toEqual([]);
  });
});

test.describe('phone search sheet and result reading', () => {
  test.skip(({ viewport }) => viewport.width > 680, 'phone layout');

  test('focusing the field folds the headline away; 닫기 brings it back without losing the text', async ({ page }) => {
    await bootHome(page);
    await expect(page.locator('.cs-hero h1')).toBeVisible();
    await expect(page.locator('[data-cs-sheet-close]')).toBeHidden();
    await page.locator('#civicQuery').click();
    await expect(page.locator('body')).toHaveClass(/cs-sheet/);
    await expect(page.locator('.cs-hero h1')).toBeHidden();
    await expect(page.locator('.cs-nav')).toBeHidden();
    const close = page.locator('[data-cs-sheet-close]');
    await expect(close).toBeVisible();
    await expect(close).toHaveText('닫기');
    const bar = await page.locator('.cs-searchbar').boundingBox();
    expect(bar.y).toBeLessThan(40);
    await page.keyboard.type('F-6');
    await expect(options(page).first()).toBeVisible();
    // more suggestions fit above a ~40% on-screen keyboard than the old two
    const fit = await page.evaluate(() => [...document.querySelectorAll('#civicSuggest [role="option"]')].filter((o) => o.getBoundingClientRect().bottom <= innerHeight * 0.6).length);
    expect(fit).toBeGreaterThanOrEqual(4);
    // the type sits in the quiet second line, not as a separate badge row
    await expect(options(page).first().locator('.cs-sug-kind')).toBeHidden();
    await expect(options(page).first().locator('.cs-sug-kind-inline')).toHaveText('체류자격');
    // the compact submit still searches
    const submit = page.locator('#civicSearchForm .cs-submit');
    const box = await submit.boundingBox();
    expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44);
    await close.click();
    await expect(page.locator('body')).not.toHaveClass(/cs-sheet/);
    await expect(page.locator('.cs-hero h1')).toBeVisible();
    await expect(page.locator('#civicQuery')).toHaveValue('F-6');
    await expect(page.locator('.cs-suggest')).toBeHidden();
  });

  test('a search from the sheet leaves it; the result header slides away while reading and returns on scroll up', async ({ page }) => {
    await bootHome(page);
    await page.locator('#civicQuery').click();
    await page.keyboard.type('외국인등록증 재발급');
    await page.keyboard.press('Enter');
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('body')).not.toHaveClass(/cs-sheet/);
    await page.mouse.wheel(0, 700);
    await expect(page.locator('body')).toHaveClass(/cs-hdr-away/);
    await page.mouse.wheel(0, -120);
    await expect(page.locator('body')).not.toHaveClass(/cs-hdr-away/);
    await page.mouse.wheel(0, 500);
    await expect(page.locator('body')).toHaveClass(/cs-hdr-away/);
    await page.locator('#q').focus();
    await expect(page.locator('body')).not.toHaveClass(/cs-hdr-away/);
    // next steps are full-width rows a thumb can hit
    const rows = await page.locator('#statusGuidance .sg-next li > a, #statusGuidance .sg-next li > button').evaluateAll((els) => els.map((e) => { const r = e.getBoundingClientRect(); return { w: r.width, h: r.height }; }));
    expect(rows.length).toBeGreaterThan(1);
    for (const r of rows) { expect(r.h).toBeGreaterThanOrEqual(48); expect(r.w).toBeGreaterThan(page.viewportSize().width * 0.8); }
  });

  test('the result search bar draws one box and one clear button', async ({ page }) => {
    await bootHome(page, '/index.html?q=' + encodeURIComponent('F-6 연장'));
    await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
    await page.locator('#q').focus();
    // getComputedStyle cannot read ::-webkit-search-cancel-button, so the rule itself is checked
    const s = await page.evaluate(() => { const q = document.getElementById('q'); const cs = getComputedStyle(q); const rule = [...document.styleSheets].flatMap((sh) => { try { return [...sh.cssRules]; } catch (e) { return []; } }).find((r) => r.selectorText && r.selectorText.includes('#q::-webkit-search-cancel-button')); return { shadow: cs.boxShadow, outline: cs.outlineStyle, cancel: rule ? rule.style.getPropertyValue('appearance') : null }; });
    expect(s.shadow === 'none' || /0px 0px 0px 0px/.test(s.shadow)).toBe(true);
    expect(s.outline).toBe('none');
    expect(s.cancel).toBe('none');
  });
});

test.describe('small screens', () => {
  test('the panel stays in the flow under the field, options are large enough, nothing overflows', async ({ page }) => {
    await bootHome(page);
    await typeQuery(page, 'E-7 workplace change');
    await expect(options(page).first()).toBeVisible();
    const m = await page.evaluate(() => {
      const box = document.querySelector('.cs-suggest'), bar = document.querySelector('.cs-searchbar');
      const r = box.getBoundingClientRect(), b = bar.getBoundingClientRect();
      const opts = [...document.querySelectorAll('#civicSuggest [role="option"]')].map((o) => o.getBoundingClientRect());
      return { position: getComputedStyle(box).position, below: r.top >= b.bottom - 1, insideX: r.left >= -1 && r.right <= innerWidth + 1, minHeight: Math.min(...opts.map((o) => o.height)), overflow: document.documentElement.scrollWidth - innerWidth };
    });
    expect(m.position).toBe('static');
    expect(m.below).toBe(true);
    expect(m.insideX).toBe(true);
    expect(m.minHeight).toBeGreaterThanOrEqual(44);
    expect(m.overflow).toBeLessThanOrEqual(1);
  });

  test('Arabic is right-to-left and the field still works', async ({ page }) => {
    await bootHome(page, '/index.html?lang=ar');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    const first = await firstOption(page, 'F-6');
    await expect(first).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
