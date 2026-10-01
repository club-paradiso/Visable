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
  await expect(page.locator('#civicQuery')).toBeVisible({ timeout: 20_000 });
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
  // Before a search the visible main region is the civic landing, not the empty
  // results region: focus must land there and the next Tab must reach search.
  await expect(page.locator('#civicLanding main')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('#civicQuery')).toBeFocused();
});

test('after a search the skip link moves focus to the results region', async ({ page }) => {
  await settled(page);
  await page.fill('#civicQuery', 'D-2 연장');
  await page.press('#civicQuery', 'Enter');
  await expect(page.locator('#statusGuidance[data-sg-kind]')).toBeVisible({ timeout: 20_000 });
  const skip = page.locator('a.skip-link');
  await skip.focus();
  await skip.press('Enter');
  await expect(page).toHaveURL(/#mainContent$/);
  await expect(page.locator('#mainContent')).toBeFocused();
});

// The visible result region under the civic refresh is #statusGuidance (the
// unified-search layer is intentionally not fetched there, see
// civicOwnsResults() in assets/js/unified-search.js). Its first search loads the
// guidance bundle, so holding or failing that request exercises both paths.
async function search(page, term) {
  await page.fill('#civicQuery', term);
  await page.press('#civicQuery', 'Enter');
}

test('the results region reports busy only while the answer is loading', async ({ page }) => {
  let release;
  const held = new Promise((r) => { release = r; });
  await page.route('**/data/status-guidance-202609.json', async (route) => {
    await held;                                  // hold the request open
    await route.continue();
  });

  await settled(page);
  await search(page, 'D-2 연장');
  const region = page.locator('#statusGuidance');
  await expect(region).toHaveAttribute('aria-busy', 'true');
  release();
  await expect(region).toHaveAttribute('aria-busy', 'false', { timeout: 20_000 });
  await expect(region).toHaveAttribute('data-sg-kind', /.+/);
});

test('a failed answer load clears busy instead of leaving it stuck', async ({ page }) => {
  await page.route('**/data/status-guidance-202609.json', (route) => route.abort('failed'));
  await settled(page);
  await search(page, 'D-2 연장');
  // The region fails to a note with a retry, not to a permanent spinner: a stuck
  // aria-busy tells a screen reader to keep waiting for content that never arrives.
  await expect(page.locator('#statusGuidance')).toHaveAttribute('aria-busy', 'false', { timeout: 20_000 });
  await expect(page.locator('body')).toHaveAttribute('data-sg-state', 'failed');
  await expect(page.locator('#statusGuidance [data-sg-action="retry"]')).toBeVisible();
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
