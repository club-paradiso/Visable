// "신청서" wording rule: stay-procedure rows must read "통합신청서 (신고서) [별지 제34호서식]"
// (F-4: 재외동포(F-4) 통합신청서(별지 제1호서식)), including comma-joined rows and
// every renderer that lists required documents. Pre-entry 사증발급 rows are left alone.
import { test, expect } from '@playwright/test';

const GENERIC = '통합신청서 (신고서) [별지 제34호서식]';
const F4 = '재외동포(F-4) 통합신청서(별지 제1호서식)';

async function boot(page) {
  await page.route('**/api/**', (route) => route.abort());
  await page.goto('/index.html');
  await page.waitForFunction(() => {
    try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && typeof paradisoCanonicalAppFormText === 'function'; } catch (e) { return false; }
  }, null, { timeout: 30_000 });
}

test('rule: exact, spaced, F-4 and comma-joined rows', async ({ page }) => {
  await boot(page);
  const r = await page.evaluate(() => {
    const f = paradisoCanonicalAppFormText;
    return {
      bare: f('신청서', 'statusChange', 'D-4'),
      spaced: f('통합신청서 (별지 제34호 서식)', 'extension', 'D-2'),
      joined: f('신청서, 여권, 외국인등록증(소지자), 사진 1매', 'statusChange', 'D-4'),
      joinedMid: f('여권, 통합신청서, 표준규격사진 1매, 수수료', 'statusChange', 'F-1'),
      f4Spaced: f('통합신청서(별지 제1호 서식)', 'registration', 'F-4'),
      f4Prefixed: f('재외동포(F-4) 통합신청서(별지 제1호 서식)', 'statusChange', 'F-4'),
      f4Bare: f('신청서', 'extension', 'F-4'),
      idempotent: f('통합신청서 (신고서) [별지 제34호서식]', 'extension', 'D-2'),
      visaIssuance: f('신청서', 'visaIssuance', 'D-2'),
      otherForm: f('한글병기 신청서(희망자만)', 'statusChange', 'F-4'),
      rangeKept: f('통합신청서(별지 제34호~제34호의2 서식), 여권', 'workplaceChange', 'E-7'),
      noF4OutsideF4: f('통합신청서(별지 제1호 서식)', 'extension', 'D-2')
    };
  });
  expect(r.bare).toBe(GENERIC);
  expect(r.spaced).toBe(GENERIC);
  expect(r.joined).toBe(`${GENERIC}, 여권, 외국인등록증(소지자), 사진 1매`);
  expect(r.joinedMid).toBe(`여권, ${GENERIC}, 표준규격사진 1매, 수수료`);
  expect(r.f4Spaced).toBe(F4);
  expect(r.f4Prefixed).toBe(F4);
  expect(r.f4Bare).toBe(F4);
  expect(r.idempotent).toBe(GENERIC);
  expect(r.visaIssuance).toBe('신청서');
  expect(r.otherForm).toBe('한글병기 신청서(희망자만)');
  expect(r.rangeKept).toBe('통합신청서(별지 제34호~제34호의2 서식), 여권');
  expect(r.noF4OutsideF4).toBe('통합신청서(별지 제1호 서식)');
});

for (const [query, expected] of [['D-4', GENERIC], ['F-1', GENERIC], ['F-4', F4]]) {
  test(`search ${query}: no bare/legacy application-form row is rendered`, async ({ page }) => {
    await boot(page);
    await page.fill('#civicQuery', query);
    await page.press('#civicQuery', 'Enter');
    // Tiles live in procedure tabs that are not all visible: wait for attachment, not visibility.
    await page.waitForSelector('#rlist .vc .doc-chk-item', { state: 'attached' });
    const rows = await page.evaluate(() => {
      const sel = '#rlist .vc .doc-chk-item > span, #rlist .vc .scenario-checklist-itemtext, #rlist .vc .easy-doc-group li, #rlist .vc .docs-list-name';
      return [...document.querySelectorAll(sel)]
        .map((e) => {
          // Search highlighting wraps the query (e.g. "F-4") in <mark>, so read textContent
          // of a clone with the help buttons removed instead of the element's own text nodes.
          const c = e.cloneNode(true);
          c.querySelectorAll('button, .doc-name-i18n').forEach((b) => b.remove());
          return c.textContent.replace(/\s+/g, ' ').trim();
        })
        .filter((t) => /^(통합)?신청서(\s*\(.*\))?$/.test(t) || t === '통합신청서' || /통합신청서/.test(t));
    });
    expect(rows.length).toBeGreaterThan(0);
    for (const t of rows) {
      // Only the canonical wording (or an explicit, untouched F-4 별지 제1호 / 제34호~제34호의2 variant) may appear.
      expect([GENERIC, F4]).toContain(t);
      if (query !== 'F-4') expect(t).toBe(expected);
    }
  });
}
