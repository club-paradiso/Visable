// Golden: "관할 출입국 찾기" — the office responsible for an address. Expected office and address
// come from the jurisdiction tables (src/features/jurisdiction-data.js, moved verbatim from index.html).
import { test, expect } from '@playwright/test';
import { pack } from '../helpers/data.mjs';
import { boot, normalize } from '../helpers/page.mjs';
import { JUR_DB, OFFICE_INFO, JUR_SOURCE_URL } from '../../../src/features/jurisdiction-data.js';

const c = pack('ko').civic;

test('choosing a 시·도 and 시·군·구 shows the responsible immigration office and its address', async ({ page }) => {
  const sido = '서울특별시';
  const sigungu = '종로구';
  const office = JUR_DB[sido][sigungu];
  const info = OFFICE_INFO[office];
  expect(info, 'office info exists for the chosen district').toBeTruthy();
  const errors = await boot(page);
  const summary = page.locator('#csTools summary');
  if (!(await page.locator('#csTools[open]').count())) await summary.click();
  await page.getByRole('button', { name: new RegExp(normalize(c.office)) }).first().click();
  const sidoSel = page.locator('#jurSido');
  await expect(sidoSel).toBeVisible({ timeout: 30_000 });
  await expect(sidoSel.locator('option')).toHaveCount(Object.keys(JUR_DB).length + 1);
  await sidoSel.selectOption(sido);
  const sigunguSel = page.locator('#jurSigungu');
  await expect(sigunguSel).toBeEnabled();
  await expect(sigunguSel.locator('option')).toHaveCount(Object.keys(JUR_DB[sido]).length + 1);
  await sigunguSel.selectOption(sigungu);
  await expect(page.getByText(office, { exact: true }).first()).toBeVisible();
  await expect(page.getByText(info.addr, { exact: true }).first()).toBeVisible();
  await expect(page.locator('#jurOfficialSource')).toHaveAttribute('href', JUR_SOURCE_URL[sido]);
  expect(errors).toEqual([]);
});

// Independent cases from the Ministry of Justice five regional office tables (2026-11-04).
// These must NOT derive expected values from JUR_DB itself.
test('jurisdiction map includes corrected branch areas, service counters and official sources', () => {
  const cases = [
    ['경상북도', '김천시', '대구출입국·외국인사무소 구미출장소'],
    ['경상북도', '칠곡군', '대구출입국·외국인사무소 구미출장소'],
    ['경상북도', '경주시', '울산출입국·외국인사무소'],
    ['충청북도', '영동군', '대전출입국·외국인사무소'],
    ['충청북도', '옥천군', '대전출입국·외국인사무소'],
    ['충청남도', '예산군', '대전출입국·외국인사무소 천안출장소'],
    ['충청남도', '서산시', '대전출입국·외국인사무소 서산출장소'],
    ['충청남도', '당진시', '대전출입국·외국인사무소 당진출장소'],
    ['경상남도', '김해시', '부산출입국·외국인청 김해출장소'],
    ['경상남도', '거제시', '창원출입국·외국인사무소 거제출장소'],
    ['경기도', '안산시', '안산출입국·외국인사무소 종합민원센터'],
    ['경기도', '가평군', '춘천출입국·외국인사무소'],
    ['전라남도', '광양시', '여수출입국·외국인사무소 광양출장소'],
    ['전라남도', '해남군', '광주출입국·외국인사무소 목포출장소'],
    ['전북특별자치도', '군산시', '전주출입국·외국인사무소 군산출장소'],
    ['부산광역시', '중구', '부산출입국·외국인청 별관'],
  ];
  for (const [sido, district, expected] of cases) {
    expect(JUR_DB[sido][district], `${sido}/${district}`).toBe(expected);
  }
  const addresses = [
    ['서울출입국·외국인청', '서울특별시 송파구 정의로 55'],
    ['인천출입국·외국인청', '인천광역시 제물포구 서해대로 393'],
    ['안산출입국·외국인사무소 종합민원센터', '경기도 안산시 단원구 광덕4로 96, 2층'],
    ['부산출입국·외국인청 별관', '부산광역시 중구 충장대로 7, 교보생명 중앙동사옥'],
    ['대전출입국·외국인사무소', '대전광역시 중구 목중로26번길 7'],
  ];
  for (const [office, address] of addresses) expect(OFFICE_INFO[office].addr).toBe(address);
  for (const [sido, districts] of Object.entries(JUR_DB)) {
    expect(JUR_SOURCE_URL[sido], `source for ${sido}`).toMatch(/^https:\/\/www\.immigration\.go\.kr\/immigration\/20\d{2}\/subview\.do$/);
    for (const [district, office] of Object.entries(districts)) {
      expect(OFFICE_INFO[office], `missing office info: ${sido}/${district}`).toBeTruthy();
    }
  }
});
