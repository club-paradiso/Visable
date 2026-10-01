import { test, expect } from '@playwright/test';

// Console errors that matter are first-party. The pages load Pretendard from a
// public CDN; when the runner cannot reach it (sandboxed CI, offline laptop) the
// browser logs "Failed to load resource: net::ERR_…" for that cross-origin URL.
// Only that exact shape — a failed load of a resource on another origin — is
// ignored; a failed same-origin load or any other console error still fails.
function collectConsoleErrors(page) {
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message || error}`));
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    const source = message.location()?.url || '';
    if (/^Failed to load resource: net::ERR_/.test(text) && isCrossOrigin(page, source)) return;
    errors.push(source ? `${text} (${source})` : text);
  });
  return errors;
}

function isCrossOrigin(page, url) {
  try {
    return new URL(url).origin !== new URL(page.url()).origin;
  } catch (error) {
    return false;
  }
}

async function expectNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'no horizontal overflow').toBeLessThanOrEqual(1);
}

test('New Home exposes a useful entry point and an accessible readiness dialog', async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  await page.goto('/new-home.html');
  await expect(page.locator('.nh-section-nav')).toBeVisible();
  // 확정 시안(507:2876)의 히어로는 중앙 정렬 단일 컬럼이라 우측 가이드 카드가 없다.
  // 진입점은 히어로 CTA 두 개 — 준비 점검(모달)과 Visable 이동.
  await expect(page.locator('.nh-hero .nh-btn-primary')).toBeVisible();
  await expect(page.locator('.nh-hero .nh-btn-secondary')).toHaveAttribute('href', 'index.html');
  // 확정 시안(122:13-14)의 카드 아이콘은 순번이 아니라 한 글자 타일이다.
  await expect(page.locator('.nh-card-icon').first()).toHaveText('귀');
  await expectNoHorizontalOverflow(page);

  const trigger = page.locator('[data-action="open-readiness"]').first();
  await trigger.click();
  const modal = page.locator('#readinessModal');
  await expect(modal).toHaveClass(/active/);
  const progress = modal.getByRole('progressbar');
  await expect(progress).toHaveAttribute('aria-valuenow', '1');
  await expect(progress).toHaveAttribute('aria-valuemax', '8');
  await expect(modal.locator('legend')).toBeFocused();

  const next = modal.locator('.nh-modal-foot button.primary');
  await expect(next).toBeDisabled();
  await modal.locator('input[type="radio"]').first().check();
  await expect(next).toBeEnabled();

  await page.keyboard.press('Escape');
  await expect(modal).not.toHaveClass(/active/);
  await expect(trigger).toBeFocused();
  await expectNoHorizontalOverflow(page);
  expect(consoleErrors).toEqual([]);
});

test('New Home explains nationality and KIIP routes with scoped official sources', async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  await page.goto('/new-home.html');
  const pathIds = await page.evaluate(() => fetch('/data/nationality_paths.json').then((response) => response.json()).then((data) => data.paths.map((item) => item.id)));
  expect(pathIds).toEqual(expect.arrayContaining(['general', 'marriage', 'family', 'special', 'restoration', 'determination', 'dual', 'loss', 'renunciation', 'after']));
  await expect(page.locator('.nh-hub-item[data-id="loss"]')).toBeVisible();
  await expect(page.locator('.nh-hub-item[data-id="renunciation"]')).toBeVisible();
  await expect(page.locator('#kiip')).toContainText(/자동으로 보장하지 않습니다|do not automatically establish eligibility/);
  await expect(page.locator('.nh-source-disclaimer')).toContainText(/제휴 또는 소속 관계가 없습니다|is not affiliated/);
  await expect(page.locator('.nh-source-card')).toHaveCount(16);
  await expect(page.locator('.nh-source-scope').first()).toBeVisible();
  await expect(page.locator('.nh-source-meta').first()).toContainText(/확인일|Accessed/);
  await expect(page.locator('.nh-source-link[href="https://mojminwon.moj.go.kr/minwon/2014/subview.do"]')).toBeVisible();
  await expect(page.getByText(/향후 시행 — 현재 기준 아님|Future effective date — not current law/)).toBeVisible();
  await expectNoHorizontalOverflow(page);
  expect(consoleErrors).toEqual([]);
});

test('homepage visa search settles without reopening blocking menus', async ({ page }) => {
  test.skip(page.viewportSize().width < 1000, 'The gateway search transition is a desktop homepage flow.');
  const consoleErrors = collectConsoleErrors(page);
  await page.goto('/index.html');
  // The civic shell's search box is the home entry (the old gateway toggle is
  // hidden under body.civic-refresh).
  const query = page.locator('#civicQuery');
  await expect(query).toBeVisible({ timeout: 30_000 });
  // A status + procedure query reaches the procedure result, where the
  // "기존 체류자격 카드 보기" action lives (a bare code first asks for the procedure).
  await query.fill('D-2 연장');
  await query.press('Enter');
  await expect(page.locator('body')).toHaveClass(/searched/, { timeout: 10_000 });
  await expect(page.locator('body')).not.toHaveClass(/launching/);
  await expect(page.locator('#cityMenu')).toBeHidden();
  // Procedure guidance comes first; the status card opens only on the explicit
  // "기존 체류자격 카드 보기" request (see procedure-first-search.spec.mjs).
  const guidance = page.locator('#statusGuidance[data-sg-kind]');
  await expect(guidance).toBeVisible({ timeout: 20_000 });
  await guidance.locator('[data-sg-action="legacy-card"]').click();
  await expect(page.locator('#cityMenu')).toBeHidden();
  await expect(page.locator('.vc[data-code="D-2"]')).toBeVisible();
  const missionSources = page.locator('.vc[data-code="D-2"] details.issuance-mission-sources').first();
  await expect(missionSources).toBeVisible();
  await missionSources.locator('summary').click();
  await expect(missionSources.locator('a.issuance-mission-link').first()).toHaveAttribute('href', /overseas\.mofa\.go\.kr/);
  await expect(missionSources).toContainText('해당 공관 범위만 적용');
  await expectNoHorizontalOverflow(page);
  expect(consoleErrors).toEqual([]);
});
