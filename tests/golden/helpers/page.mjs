// Browser-side helpers. Interaction locators may use the stable control ids
// (#civicQuery / #q are the public search controls); assertions in the specs
// stay on user-observable outcomes (text, roles, labels, URL, notices).
import { expect } from '@playwright/test';

export const API_GLOB = '**/api/**';

export function trackErrors(page) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  return errors;
}

/**
 * Open a page with every /api/* call aborted by default (the site must stay
 * grounded on its static data), plus optional extra routes.
 */
export async function boot(page, { path = '/index.html', query = {}, routes = [], blockApi = true, waitForSearch = true } = {}) {
  if (blockApi) await page.route(API_GLOB, (route) => route.abort());
  // Count the page's `paradiso-language-applied` events (installed before any page script runs).
  // The home re-renders its search form on the first one, after the i18n packs load; typing before
  // that can land on the element that is about to be replaced (seen under CI load, see waitForSearchReady).
  await page.addInitScript(() => { window.addEventListener('paradiso-language-applied', () => { window.__goldenLanguageApplied = (window.__goldenLanguageApplied || 0) + 1; }); });
  for (const [pattern, handler] of routes) await page.route(pattern, handler);
  const errors = trackErrors(page);
  const qs = new URLSearchParams(query).toString();
  await page.goto(path + (qs ? (path.includes('?') ? '&' : '?') + qs : ''));
  if (waitForSearch) await waitForSearchReady(page);
  return errors;
}

export async function waitForSearchReady(page) {
  // Either the home search field or the searched-state field is usable.
  const field = page.locator('#civicQuery:visible, #q:visible:not([disabled])').first();
  await expect(field).toBeVisible({ timeout: 30_000 });
  // The home ships a static first-paint shell; its search field only handles Enter once
  // civic-search.js has hydrated it (data-cs-hydrated flips from "static" to "rendered"/"reused").
  // Under CI load a keypress before that point hits a plain <form> instead of the search.
  const landing = page.locator('#civicLanding');
  if (await landing.count()) {
    await expect(landing).not.toHaveAttribute('data-cs-hydrated', 'static', { timeout: 30_000 });
    // The bootstrap applies the initial language once the i18n packs have loaded and civic-search.js
    // re-renders the landing (a new #civicQuery) in that event's handler. Wait for that first event so a
    // keypress cannot hit the element being replaced. Tolerant: pages whose packs never load (fail-closed
    // specs) continue after the timeout instead of failing here.
    await page.waitForFunction(() => (window.__goldenLanguageApplied || 0) >= 1, null, { timeout: 15_000 }).catch(() => {});
  }
}

export async function search(page, query) {
  const searched = await page.evaluate(() => document.body.classList.contains('searched'));
  const field = page.locator(searched ? '#q' : '#civicQuery');
  await field.fill(query);
  await field.press('Enter');
  await expect(guidanceHeading(page, query)).toBeAttached({ timeout: 30_000 });
}

/** The guidance block's heading reads "<answerTitle> · <query>" (ko "안내", en "Guidance"). */
export function guidanceHeading(page, query) {
  return page.getByRole('heading', { level: 1, name: new RegExp(`^(안내|Guidance) · ${escapeRe(query)}$`) });
}

export const mainText = (page) => page.evaluate(() => (document.getElementById('mainContent') || document.body).innerText);
export const bodyText = (page) => page.evaluate(() => document.body.innerText);
export const normalize = (s) => String(s).replace(/\s+/g, ' ').trim();
export const escapeRe = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export async function noHorizontalScroll(page) {
  const o = await page.evaluate(() => ({ doc: document.documentElement.scrollWidth, inner: innerWidth }));
  expect(o.doc, `document scrollWidth ${o.doc} > viewport ${o.inner}`).toBeLessThanOrEqual(o.inner + 1);
}

export const storage = (page, key) => page.evaluate((k) => { try { return localStorage.getItem(k); } catch (e) { return null; } }, key);

export const jsonRoute = (status, body) => (route) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
