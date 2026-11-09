// Golden: procedure guidance = documents, fees, conditions and uncertainty notices.
// Expected documents/fees come from data/status-guidance-202609.json; copy from
// fixtures/guidance-strings.mjs. Fee amounts are asserted exactly (hard stop 4).
import { test, expect } from '@playwright/test';
import { guidanceEntry, commonProcedure, fee, docsByLevel, won, STAY_EDITION } from '../helpers/data.mjs';
import { GUIDANCE_STR as STR, fill } from '../fixtures/guidance-strings.mjs';
import { boot, search, mainText, normalize } from '../helpers/page.mjs';

const ext = guidanceEntry('D-2', 'extension');
const extFee = fee('extension_general');
const reissue = commonProcedure('card_reissue');
const reissueFee = fee('card_reissue');

// Golden assertions track the *display* vocabulary, not the immutable manual
// source's legacy generic title. The original document ref and evidence stay intact.
function displayedStayFormName(d, lang) {
  if (d.ref === 'app_form' || d.ref === 'app_form_34')
    return lang === 'ko' ? '통합신청서 (별지 제34호 서식)' : 'Integrated Application Form (Form 34)';
  return lang === 'ko' ? d.name_ko : d.name_en;
}

test.describe('D-2 → 체류기간 연장 (status-specific procedure)', () => {
  test('ko: period, every required document, conditional document, fee and notices', async ({ page }) => {
    const errors = await boot(page);
    await search(page, 'D-2 체류기간 연장');
    const text = normalize(await mainText(page));
    expect(text).toContain(`${STR.ko.interpLabel}: D-2 유학 · 체류기간 연장`);
    expect(text).toContain(fill(STR.ko.exact, { target: 'D-2' }));
    expect(text).toContain(normalize(ext.summary_ko));
    expect(text).toContain(normalize(ext.period_ko));
    const required = docsByLevel(ext, 'REQUIRED_BASELINE');
    const conditional = docsByLevel(ext, 'CONDITIONAL_REQUIRED');
    expect(required.length).toBeGreaterThan(0);
    expect(text).toContain(STR.ko.docsTitle);
    expect(text).toContain(`${fill(STR.ko.docsCount, { n: required.length })} · ${fill(STR.ko.docsCountCond, { n: conditional.length })}`);
    for (const d of required) expect(text, d.ref).toContain(normalize(displayedStayFormName(d, 'ko')));
    for (const d of conditional) expect(text, d.ref).toContain(normalize(displayedStayFormName(d, 'ko')));
    // Fee: exact amount, label and review state from the fee registry.
    expect(text).toContain(STR.ko.feeTitle);
    expect(text).toContain(won(extFee.amount));
    expect(text).toContain(extFee.label_ko);
    expect(text).toContain(fill(STR.ko.ovFee, { amount: won(extFee.amount), review: STR.ko.feeReview.VERIFIED_REGULATION }));
    for (const inst of extFee.payment_instruments) expect(text).toContain(STR.ko.instruments[inst]);
    expect(text).toContain(fill(STR.ko.ovDocs, { n: required.length }));
    // Uncertainty and officer-discretion notices are present.
    expect(text).toContain(STR.ko.ovReview);
    expect(text).toContain(STR.ko.officer);
    expect(text).toMatch(new RegExp(fill(STR.ko.ovBasis, { date: STAY_EDITION.date, n: '\\d+' })));
    expect(text).toContain(STR.ko.evidenceTitle);
    expect(text).toContain(STR.ko.disclaimer);
    expect(errors).toEqual([]);
  });

  test('en: the same procedure with English document names and fee label', async ({ page }) => {
    await boot(page, { query: { lang: 'en' } });
    await search(page, 'D-2 체류기간 연장');
    const text = normalize(await mainText(page));
    expect(text).toContain(normalize(ext.summary_en));
    expect(text).toContain(normalize(ext.period_en));
    for (const d of docsByLevel(ext, 'REQUIRED_BASELINE')) expect(text, d.ref).toContain(normalize(displayedStayFormName(d, 'en')));
    expect(text).toContain(won(extFee.amount));
    expect(text).toContain(extFee.label_en);
    expect(text).toContain(STR.en.disclaimer);
  });
});

test.describe('외국인등록증 재발급 (status-independent procedure)', () => {
  test('ko: common-procedure framing, documents, cash-only fee', async ({ page }) => {
    await boot(page);
    await search(page, '외국인등록증 재발급');
    const text = normalize(await mainText(page));
    expect(text).toContain(`${STR.ko.interpLabel}: 외국인등록증 재발급`);
    expect(text).toContain(STR.ko.commonKicker);
    expect(text).toContain(STR.ko.commonLead);
    expect(text).toContain(normalize(reissue.summary_ko));
    const required = docsByLevel(reissue, 'REQUIRED_BASELINE');
    const conditional = docsByLevel(reissue, 'CONDITIONAL_REQUIRED');
    // The generated bundle still has the baseline list; the UI adds two passport forms.
    const extraPassportDocs = ['여권 원본', '여권 인적사항면 사본'];
    expect(text).toContain(`${fill(STR.ko.docsCount, { n: required.length + extraPassportDocs.length })} · ${fill(STR.ko.docsCountCond, { n: conditional.length })}`);
    for (const name of extraPassportDocs) expect(text).toContain(name);
    for (const d of [...required, ...conditional]) expect(text, d.ref).toContain(normalize(d.name_ko));
    expect(text).toContain(won(reissueFee.amount));
    expect(text).toContain(reissueFee.label_ko);
    for (const inst of reissueFee.payment_instruments) expect(text).toContain(STR.ko.instruments[inst]);
    expect(text).toContain(STR.ko.ovReview);
    expect(text).toContain(STR.ko.officer);
    expect(text).toContain(STR.ko.disclaimer);
  });

  test('a fee question answers from the fee registry without any model call', async ({ page }) => {
    // Count model / AI requests only. The visa catalog load (`/api/visas`, src/boot.js loadVisaData) is a data
    // request the page makes whenever a backend origin is configured — i.e. on every deployment but not on a
    // local server — and it falls back to the committed JSON when aborted, so it is not what this test guards.
    let apiCalls = 0;
    await boot(page, { blockApi: false, routes: [['**/api/**', (route) => { if (!/\/api\/visas(\?|$)/.test(route.request().url())) apiCalls += 1; return route.abort(); }]] });
    await search(page, '외국인등록증 재발급 수수료');
    const text = normalize(await mainText(page));
    expect(text).toContain(won(reissueFee.amount));
    expect(text).toContain(reissueFee.label_ko);
    expect(text).toContain(STR.ko.feeTitle);
    expect(apiCalls, 'no model/API call for a fee lookup').toBe(0);
  });
});
