// Golden: the other pages. Offline-testable behaviour is asserted from data
// files; features that need live keys or a backend are marked BLOCKED with
// test.fixme and only their offline fail-closed path is checked.
import { test, expect } from '@playwright/test';
import { pack, FORMS, MANUAL_CATALOG, CHECKLIST_EXTENSION, NATIONALITY_CONTENT } from '../helpers/data.mjs';
import { boot, bodyText, normalize, noHorizontalScroll } from '../helpers/page.mjs';

const abort = (route) => route.abort();

test.describe('manual.html — official manual reader', () => {
  test('home: edition banner, status picker, official PDF links, no page errors', async ({ page }) => {
    const errors = await boot(page, { path: '/manual.html', waitForSearch: false });
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const text = normalize(await bodyText(page));
    // The edition banner names both current manuals (dates from data/manual-reader/catalog.json sources).
    for (const src of Object.values(MANUAL_CATALOG.sources || {})) if (src.date) expect(text).toContain(fmtDotDate(src.date));
    // Every status in visa_data has a card; D-2 is one of them.
    expect(text).toContain('D-2');
    await expect(page.locator('a[href*="source-manuals"][href$=".pdf"]')).toHaveCount(await page.locator('a[href*="source-manuals"][href$=".pdf"]').count());
    expect(await page.locator('a[href*="source-manuals"][href$=".pdf"]').count()).toBeGreaterThanOrEqual(2);
    await noHorizontalScroll(page);
    expect(errors).toEqual([]);
  });

  test('deep link #c-common.s opens the stay-manual common chapter with its table of contents', async ({ page }) => {
    const common = MANUAL_CATALOG.chapters.find((c) => c.key === 'common');
    await boot(page, { path: '/manual.html#c-common.s', waitForSearch: false });
    await expect(page.getByText(common.s.title, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    // The stay (s) chapter renders, not the visa (v) chapter of the same key.
    expect(text).toContain(common.s.title);
    expect(text).not.toContain(common.v.title);
    expect(page.url()).toContain('#c-common.s');
  });
});

test.describe('form-helper.html — official forms', () => {
  test('home lists the forms from data/form_definitions.json with the privacy and reference notes', async ({ page }) => {
    const fh = pack('ko').fh;
    const errors = await boot(page, { path: '/form-helper.html', waitForSearch: false });
    await expect(page.getByText(normalize(fh.privacyShort), { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    // The form list renders after data/form_definitions.json loads; wait for the first form.
    await expect(page.getByText(FORMS.forms.F01.name.ko, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    for (const f of Object.values(FORMS.forms)) expect(text, f.name.ko).toContain(normalize(f.name.ko));
    expect(text).toContain(normalize(fh.legal));
    expect(errors).toEqual([]);
  });

  test('a form deep link (#form=F01&screen=explain) shows that form in ko and en', async ({ page }) => {
    const f01 = FORMS.forms.F01;
    await boot(page, { path: '/form-helper.html#form=F01&screen=explain', waitForSearch: false });
    await expect(page.getByText(f01.name.ko, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    await page.goto('/form-helper.html?lang=en#form=F01&screen=explain');
    await expect(page.getByText(f01.name.en, { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('en');
  });
});

test.describe('immigration-checklists.html — checklists by situation', () => {
  test('loads the 2026-09 extension/change/registration data offline and states its scope and limits', async ({ page }) => {
    const errors = await boot(page, { path: '/immigration-checklists.html', waitForSearch: false, query: { procedure: 'extension', code: 'D-2' } });
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    expect(text).toContain(`${CHECKLIST_EXTENSION.row_count}개 상황`);
    expect(text).toContain('체류기간 연장');
    expect(text).toContain('체류자격 변경');
    expect(text).toContain('외국인등록');
    await noHorizontalScroll(page);
    expect(errors).toEqual([]);
  });

  test('?lang=en switches the page language', async ({ page }) => {
    await boot(page, { path: '/immigration-checklists.html', waitForSearch: false, query: { lang: 'en' } });
    await expect.poll(() => page.evaluate(() => document.documentElement.lang), { timeout: 30_000 }).toBe('en');
    const text = normalize(await bodyText(page));
    expect(text).toContain('Extension of Stay');
    expect(text).toContain('Change of Status');
  });
});

test.describe('new-home.html — nationality landing', () => {
  for (const locale of ['ko', 'en']) {
    test(`hero, notice and caution from data/nationality_content.json (${locale})`, async ({ page }) => {
      // The page reads the shared `paradiso:language` key once at init (else the browser
      // language), so the returning-user state is set before the first navigation.
      await page.addInitScript((l) => { try { localStorage.setItem('paradiso:language', l); } catch (e) {} }, locale);
      const errors = await boot(page, { path: '/new-home.html', waitForSearch: false });
      const hero = NATIONALITY_CONTENT.hero;
      const notice = normalize(NATIONALITY_CONTENT.notice[locale]);
      await expect(page.getByText(normalize(hero.kicker[locale]), { exact: false }).first()).toBeVisible({ timeout: 30_000 });
      // The notice block renders after the hero; poll the page text instead of reading it early.
      await expect.poll(async () => normalize(await bodyText(page)), { timeout: 30_000 }).toContain(notice);
      const text = normalize(await bodyText(page));
      expect(text).toContain(normalize(hero.title[locale]));
      expect(text).toContain(normalize(NATIONALITY_CONTENT.notice[locale]));
      expect(errors).toEqual([]);
    });
  }
});

test.describe('preview.html — pre-arrival checker', () => {
  test('with the public-data API down it labels the sample data as a fallback and keeps the disclaimer', async ({ page }) => {
    await boot(page, { path: '/preview.html', waitForSearch: false });
    await page.selectOption('#pvCountry', 'vn');
    await page.getByRole('button', { name: '입국 전 확인사항 보기' }).click();
    await expect(page.getByText('현재 공공데이터 API 응답을 불러오지 못해 MVP 샘플 데이터를 표시합니다', { exact: false })).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    expect(text).toContain('최종 사증 발급 여부, 접수 가능 여부, 요구서류, 심사 결과는 관할 재외공관의 공식 안내와 판단을 따라야 합니다.');
  });
});

test.describe('ai.html — Waymaker (AI answers BLOCKED: need /api/ask + provider key)', () => {
  test('offline shell: reference disclaimer, consent-first send, and no fabricated answer', async ({ page }) => {
    const errors = await boot(page, { path: '/ai.html', waitForSearch: false });
    await expect(page.getByText('이 서비스는 공개 법령·매뉴얼을 바탕으로 한 참고용 정보 제공 도구이며, 법적 상담이나 민원 대행이 아닙니다', { exact: false })).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    expect(text).toContain('답변은 법적 효력이 없으며, 최종 판단은 HiKorea·1345·관할 출입국기관에서 확인하세요.');
    expect(errors).toEqual([]);
  });
  test.fixme('BLOCKED — live AI answer quality needs the Railway backend and a provider key', async () => {});
});

test.describe('enforcement.html — disposition estimator (analysis BLOCKED: backend + provider)', () => {
  test('offline: the connection failure is stated and no fine or prediction is shown', async ({ page }) => {
    await boot(page, { path: '/enforcement.html', waitForSearch: false });
    await page.fill('#case-text', '유학생인데 주당 25시간 식당에서 일했습니다.');
    await page.getByRole('button', { name: /내용 확인하기/ }).click();
    await expect(page.getByText('Visable 분석 서버에 연결하지 못했습니다', { exact: false })).toBeVisible({ timeout: 30_000 });
    const text = normalize(await bodyText(page));
    expect(text).toContain('정보 제공용 도구이며 출입국 당국의 최종 처분 또는 법률 자문을 대신하지 않습니다.');
    expect(text).not.toMatch(/범칙금\s*₩|예상 처분:/);
  });
  test.fixme('BLOCKED — extraction/analysis need /api/enforcement/* with a provider key', async () => {});
});

test.describe('operator pages (BLOCKED: operator token + backend)', () => {
  test('knowledge-studio.html shows only the operator login offline', async ({ page }) => {
    await boot(page, { path: '/knowledge-studio.html', waitForSearch: false });
    await expect(page.getByText('운영자 로그인', { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  });
  test('content-studio.html shows only the operator authentication offline', async ({ page }) => {
    await boot(page, { path: '/content-studio.html', waitForSearch: false });
    await expect(page.getByText('운영자 인증', { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  });
  test.fixme('BLOCKED — studio workflows need WAYMAKER_OPERATOR_TOKENS on the backend', async () => {});
});

test.describe('nationality-interview-hub.html', () => {
  test('loads its guides offline; the AI coach is BLOCKED but has a local fallback (not exercised here)', async ({ page }) => {
    const errors = await boot(page, { path: '/nationality-interview-hub.html', waitForSearch: false });
    await expect(page.getByText('국적민원 알아보기', { exact: false }).first()).toBeVisible({ timeout: 30_000 });
    expect(errors).toEqual([]);
  });
});

function fmtDotDate(iso) { const [y, m, d] = iso.split('-').map(Number); return `${y}. ${m}. ${d}.`; }
