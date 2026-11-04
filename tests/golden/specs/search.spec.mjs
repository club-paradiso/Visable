// Golden: status search → interpretation, procedure question, subcodes, unknown
// codes, shareable ?q= URLs, and guidance language. Expected names come from
// visa_data.json / data/i18n/visa-names.json; copy from fixtures/guidance-strings.mjs.
import { test, expect } from '@playwright/test';
import { LOCALES, visaRecord, subcodeRecord, VISA_NAMES, STAY_EDITION } from '../helpers/data.mjs';
import { GUIDANCE_STR as STR, fill, editionKo } from '../fixtures/guidance-strings.mjs';
import { boot, search, guidanceHeading, mainText, normalize } from '../helpers/page.mjs';

const d2 = visaRecord('D-2');

test.describe('exact status code', () => {
  test('D-2 (ko): interpretation, procedure question, disclaimer, ?q= in the URL', async ({ page }) => {
    const errors = await boot(page);
    await search(page, 'D-2');
    const text = normalize(await mainText(page));
    expect(text).toContain(`${STR.ko.interpLabel}: D-2 ${d2.name}`);
    expect(text).toContain(fill(STR.ko.askProcedure, { status: 'D-2' }));
    expect(text).toContain(STR.ko.askProcedureHint);
    // Procedure options are offered as buttons, extension among them.
    await expect(page.getByRole('button', { name: '체류기간 연장', exact: true }).first()).toBeVisible();
    expect(text).toContain(STR.ko.disclaimer);
    expect(text).toContain(STR.ko.disclaimerMore);
    expect(new URL(page.url()).searchParams.get('q')).toBe('D-2');
    expect(errors).toEqual([]);
  });

  test('D-2 (en): the same question in English with the English visa name', async ({ page }) => {
    await boot(page, { query: { lang: 'en' } });
    await search(page, 'D-2');
    const text = normalize(await mainText(page));
    expect(text).toContain(`${STR.en.interpLabel}: D-2 ${VISA_NAMES['D-2'].en}`);
    expect(text).toContain(fill(STR.en.askProcedure, { status: 'D-2' }));
    expect(text).toContain(STR.en.disclaimer);
  });

  test('a ?q= URL opens straight into the searched state (no landing)', async ({ page }) => {
    await boot(page, { query: { q: 'D-2' } });
    await expect(guidanceHeading(page, 'D-2')).toBeAttached({ timeout: 30_000 });
    const text = normalize(await mainText(page));
    expect(text).toContain(fill(STR.ko.askProcedure, { status: 'D-2' }));
    await expect(page.locator('#civicQuery')).toBeHidden();
  });
});

test.describe('subcodes are never flattened into the parent', () => {
  test('E-7-1 is interpreted as E-7-1, not E-7', async ({ page }) => {
    const { parent, sub } = subcodeRecord('E-7-1');
    await boot(page);
    await search(page, 'E-7-1');
    const text = normalize(await mainText(page));
    expect(text).toContain(`${STR.ko.interpLabel}: E-7-1`);
    expect(text).not.toContain(`${STR.ko.interpLabel}: E-7 ${parent.name}`);
    expect(text).toContain(fill(STR.ko.askProcedure, { status: 'E-7-1' }));
    // The subcode's own name (visa_data.json E-7.subCodes) leads the interpretation.
    expect(text).toContain(sub.name.replace(/\(.*$/, '').trim());
  });
});

test.describe('fail-closed on unknown codes', () => {
  test('Z-9 is reported as not in the current edition; no documents or fees are shown', async ({ page }) => {
    await boot(page);
    await search(page, 'Z-9');
    const text = normalize(await mainText(page));
    expect(text).toContain(fill(STR.ko.unknownCode, { code: 'Z-9', edition: editionKo(STAY_EDITION.edition) }));
    expect(text).toContain(STR.ko.noStatus);
    expect(text).not.toContain(STR.ko.docsTitle);
    expect(text).not.toContain('₩');
    expect(text).toContain(STR.ko.disclaimer);
    expect(text).toContain(STR.ko.wmCta);
  });
});

test('the guidance renders in Korean for ko and in English for every other UI language', async ({ page }) => {
  test.slow();
  for (const locale of LOCALES) {
    await page.goto('about:blank');
    await boot(page, { query: { lang: locale, q: 'D-2' } });
    await expect(guidanceHeading(page, 'D-2')).toBeAttached({ timeout: 30_000 });
    const text = normalize(await mainText(page));
    const expected = locale === 'ko' ? STR.ko : STR.en; // status-guidance.js:1595 lang(): ko | en
    expect(text, locale).toContain(expected.disclaimer);
    expect(text, locale).toContain(fill(expected.askProcedure, { status: 'D-2' }));
  }
});
