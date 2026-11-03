// Golden: the legacy per-status result card. It is hidden behind the guidance's
// "기존 체류자격 카드 보기" action (status-guidance.js `legacy-card`) and renders from
// visa_data.json through the inline renderers (renderResults → renderProcedures → …).
// Expected values come from visa_data.json, data/i18n/*.json, data/i18n/visa-names.json
// and data/status-guidance-202609.json (fee); hard-coded renderer strings are recorded
// in fixtures/guidance-strings.mjs LEGACY_CARD_STR.
import { test, expect } from '@playwright/test';
import { pack, visaRecord, VISA_NAMES, fee } from '../helpers/data.mjs';
import { LEGACY_CARD_STR as LC, fill } from '../fixtures/guidance-strings.mjs';
import { boot, search, normalize } from '../helpers/page.mjs';

const v = visaRecord('D-2');
const ext = v.procedures.extension;
const extDocs = ext.requiredDocs; // { commonDocs, requiredDocs, additionalDocs, conditionalDocs }
const docCount = ['commonDocs', 'requiredDocs', 'additionalDocs', 'conditionalDocs'].reduce((n, k) => n + (extDocs[k] || []).length, 0);
const extFee = fee('extension_general');
// Procedures the D-2 record exposes, in the card's tab order, mapped to ko.procedureLabels indexes
// (recorded from the current render: the card lists these eight tabs for D-2).
const TAB_LABEL_INDEX = { visaIssuance: 0, statusChange: 2, extension: 3, registration: 5, activitiesOutsideStatus: 6, reentry: 8, partTimeWork: 9, schoolChange: 10 };

async function openLegacyCard(page, locale) {
  const btn = page.locator('[data-sg-action="legacy-card"]');
  await expect(btn).toBeVisible({ timeout: 30_000 });
  await expect(btn).toContainText(LC.openLegacy[locale]);
  await btn.click();
  await expect(page.locator('body')).toHaveAttribute('data-legacy-card', 'open');
}

test('ko: the legacy D-2 card shows the record header, subcodes, procedure tabs and the extension documents', async ({ page }) => {
  const ko = pack('ko');
  const errors = await boot(page);
  await search(page, 'D-2 체류기간 연장');
  await openLegacyCard(page, 'ko');
  const card = page.locator('#rlist article.vc[data-code="D-2"]');
  await expect(card).toBeVisible();
  const head = normalize(await card.locator('.vc-h').innerText());
  expect(head).toContain('D-2');
  expect(head).toContain(v.name); // 유학
  expect(head).toContain(VISA_NAMES['D-2'].en); // secondary name in ko mode
  expect(head).toContain(fill(ko.resultSubtypes, { count: v.subcodes.length }));
  expect(head).toContain(normalize(v.period));
  // Subcode preview lists the first subcodes with their names.
  const cardText = normalize(await card.innerText());
  for (const sub of v.subcodes.slice(0, 4)) {
    expect(cardText).toContain(sub.code);
    expect(cardText).toContain(sub.name);
  }
  // Procedure tabs: one per procedure in the record, labelled from the ko pack.
  const tabs = card.locator('[data-action="select-procedure"]');
  const labels = (await tabs.allInnerTexts()).map(normalize);
  const expected = Object.keys(v.procedures).filter((k) => k in TAB_LABEL_INDEX).map((k) => ko.procedureLabels[TAB_LABEL_INDEX[k]]);
  expect(labels).toEqual(expect.arrayContaining(expected));
  expect(labels.length).toBe(expected.length);
  // Select 체류기간 연장: summary, fee, document count and every document group.
  await tabs.filter({ hasText: ko.procedureLabels[TAB_LABEL_INDEX.extension] }).first().click();
  const panel = card.locator('[data-procedure-panel="extension"]');
  await expect(panel).toBeVisible();
  const text = normalize(await panel.innerText());
  expect(text).toContain(normalize(ext.summary.split(/(?<=다\.)\s/)[0]));
  expect(text).toContain(LC.feeTile.ko);
  expect(text).toContain(`${Number(extFee.amount).toLocaleString('en-US')}원`);
  expect(text).toContain(fill(ko.documentCountLabel, { count: docCount }));
  expect(text).toContain(ko.docUxGroupLabels[0]);
  expect(text).toContain(ko.docUxGroupLabels[1]);
  // Document rows: the application form is canonicalised; compound rows keep their main item;
  // "체류지 입증서류(예: …)" is split into the item plus a footnote.
  expect(text).toContain(LC.canonicalAppForm);
  for (const d of extDocs.commonDocs.filter((x) => !x.startsWith('통합신청서'))) expect(text).toContain(normalize(d));
  expect(text).toContain('지도교수 및 유학담당자 확인서');
  expect(text).toContain(extDocs.requiredDocs[1]); // 학업을 정상적으로 수행하고 있음을 입증하는 서류
  expect(text).toContain('체류지 입증서류');
  for (const d of extDocs.conditionalDocs) expect(text).toContain(normalize(d));
  // The card keeps its own caution and the data date.
  expect(cardText).toContain(normalize(ko.cautionText));
  expect(cardText).toContain(`${ko.resultDataDate} ${v.dataDate}`);
  expect(errors).toEqual([]);
});

test('en: an English keyword query opens the legacy card on its empty state (keyword search is Korean-only)', async ({ page }) => {
  const en = pack('en');
  await page.addInitScript(() => { try { localStorage.setItem('paradiso:language', 'en'); } catch (e) {} });
  const errors = await boot(page);
  await search(page, 'D-2 extension');
  await openLegacyCard(page, 'en');
  await expect(page.locator('#rlist .es-t')).toHaveText(en.resultEmptyTitle);
  await expect(page.locator('#rc')).toHaveText(fill(en.resultCount, { count: 0 }));
  expect(errors).toEqual([]);
});
