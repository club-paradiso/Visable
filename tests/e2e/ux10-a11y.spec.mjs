// UX-10 Spec / Behavior & A11y (Figma pInhK8Oyg04lpL4PMSCB4l, node 447:4).
//
// Two rules from that frame that markup inspection cannot settle: whether the
// skip link is really the first tab stop in a live document, and whether the
// results region's busy state actually clears on both the success and the
// failure path.
import { test, expect } from '@playwright/test';

// The homepage keeps loading i18n and data after `load`; tabbing before it
// settles races a re-render that can move focus.
async function settled(page) {
  await page.goto('/index.html');
  await expect(page.locator('#searchToggleBtn')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('a.skip-link')).toHaveText(/건너뛰기|Skip/, { timeout: 20_000 });
}

test('the first Tab reaches a skip link that reveals itself and moves to main', async ({ page }) => {
  await settled(page);
  const skip = page.locator('a.skip-link');
  await expect(skip).not.toBeInViewport();      // out of the way until asked for
  await page.keyboard.press('Tab');
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();          // revealed on focus, not merely present
  await skip.press('Enter');
  await expect(page).toHaveURL(/#mainContent$/);
  await expect(page.locator('#mainContent')).toBeVisible();
});

// The layer's documented integration seam (`paradiso:results-rendered`) is the
// real entry point into runUnified → fetchUnified → setSearchBarState. Driving
// it directly keeps this test about the busy state rather than about opening
// the homepage's search chrome.
async function runSearch(page, term) {
  await page.evaluate((q) => {
    document.dispatchEvent(new CustomEvent('paradiso:results-rendered', { detail: { query: q } }));
  }, term);
}
test('the results layer reports busy only while the search is in flight', async ({ page }) => {
  let release;
  const held = new Promise((r) => { release = r; });
  await page.route('**/api/search/unified', async (route) => {
    await held;                                  // hold the request open
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ query: 'D-2', intent: 'exact_visa_code',
        detectedVisaCodes: ['D-2'], organicResults: [], suggestionRows: [] })
    });
  });

  await settled(page);
  await runSearch(page, 'D-2');
  const layer = page.locator('#unifiedSearchLayer');
  await expect(layer).toHaveAttribute('aria-busy', 'true');
  release();
  await expect(layer).toHaveAttribute('aria-busy', 'false');
});

test('a failed search clears busy instead of leaving it stuck', async ({ page }) => {
  await page.route('**/api/search/unified', (route) => route.abort('failed'));
  await settled(page);
  await runSearch(page, 'D-2');
  // The layer fails to a note, not to a permanent spinner: a stuck aria-busy
  // tells a screen reader to keep waiting for content that will never arrive.
  await expect(page.locator('#unifiedSearchLayer')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#searchForm')).toHaveAttribute('data-us-search-state', 'error');
});

test('ai.html carries the same skip link as the homepage', async ({ page }) => {
  await page.goto('/ai.html');
  const skip = page.locator('a.skip-link');
  await expect(skip).toHaveCount(1);
  await expect(skip).not.toBeInViewport();       // hidden until asked for
  await page.keyboard.press('Tab');
  await expect(skip).toBeFocused();              // genuinely the first tab stop
  await expect(skip).toBeInViewport();
  await skip.press('Enter');
  await expect(page).toHaveURL(/#chatHistory$/);
  await expect(page.locator('#chatHistory')).toBeVisible();
});
