// Real-browser search smoke: every query below must resolve to at least one
// result card, and code-like queries must land on the expected record.
//
// Guards the PARADISO_SEARCH_QUERY_FIX_20260702 regressions:
//   * multi-word queries were whitespace-collapsed into one token and returned
//     zero results (including the app's own suggestion chips);
//   * compact subcode queries (G15, D21, F442, D10T) resolved to nonexistent
//     parent codes (G-15, D-21, …) and returned zero results;
//   * ALIAS_MAP routed 난민/불법체류 to removed records (RF-1/OVS-1).
import { test, expect } from '@playwright/test';

const CASES = [
  // exact + compact codes → expected top card
  { q: 'D-2', top: 'D-2' },
  { q: 'd2', top: 'D-2' },
  { q: 'G-1-5', top: 'G-1' },
  { q: 'G15', top: 'G-1' },
  { q: 'D21', top: 'D-2' },
  { q: 'E74', top: 'E-7' },
  { q: 'F442', top: 'F-4' },
  { q: 'D10T', top: 'D-10' },
  { q: 'E7M', top: 'E-7' },
  { q: 'D42K', top: 'D-4-2K' },
  { q: 'H27', top: 'H-2' },
  // aliases routed to real records
  { q: '난민', top: 'G-1' },
  { q: '난민신청', top: 'G-1' },
  { q: '인도적체류', top: 'G-1' },
  { q: '체류지 변경', top: 'FAQ-0' },
  { q: '여권 변경', top: 'FAQ-0' },
  // multi-word natural queries (min result count only)
  { q: '체류기간 연장', min: 5 },
  { q: '결핵 제출 대상', min: 1 },
  { q: '점수제 비자', min: 1 },
  { q: '재입국 허가', min: 5 },
  { q: '불법체류', min: 1 },
  // code embedded mid-query
  { q: '숙련기능(E-7-4)', top: 'E-7' },
  { q: '동반(F-3) 소득요건', top: 'F-3' },
];

test('search resolves codes, compact codes, aliases, and multi-word queries', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && typeof renderResults === 'function'; } catch (e) { return false; } }, null, { timeout: 30000 });

  for (const c of CASES) {
    const r = await page.evaluate((query) => {
      document.body.classList.add('searched');
      renderResults(query);
      const cards = [...document.querySelectorAll('#rlist article.vc')];
      return { count: cards.length, codes: cards.map(el => el.dataset.code) };
    }, c.q);
    expect(r.count, `query "${c.q}" should return results`).toBeGreaterThanOrEqual(c.min || 1);
    if (c.top) expect(r.codes[0], `query "${c.q}" top card`).toBe(c.top);
  }
});

test('every suggestion chip query returns at least one result', async ({ page }) => {
  await page.goto('/index.html');
  await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && typeof renderResults === 'function'; } catch (e) { return false; } }, null, { timeout: 30000 });

  const chipQueries = await page.evaluate(() => {
    const landing = getLandingHintItems().map(x => x.q);
    const quick = getQuickFilterItems().map(x => x.q);
    const predef = (typeof PREDEF_KEYWORDS !== 'undefined') ? PREDEF_KEYWORDS : [];
    return [...new Set([...landing, ...quick, ...predef])];
  });
  expect(chipQueries.length).toBeGreaterThan(10);

  for (const q of chipQueries) {
    const count = await page.evaluate((query) => {
      document.body.classList.add('searched');
      renderResults(query);
      return document.querySelectorAll('#rlist article.vc').length;
    }, q);
    expect(count, `suggestion chip query "${q}" should not be a dead end`).toBeGreaterThanOrEqual(1);
  }
});
