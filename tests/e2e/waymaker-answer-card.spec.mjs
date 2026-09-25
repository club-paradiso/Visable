// Real-browser tests for the Waymaker answer card (ai.html).
//
// The D-2 document lookup ("D-2 연장시 필수 서류") used to render the provider
// and exact model id in the header, raw "### 필수 서류" Markdown, an internal
// "source file 2026-06-23" citation and engineering status pills
// (BASIS / SOURCE / DISABLED). These tests render the REAL public /api/ask
// projection (tests/fixtures/waymaker/*.json, regenerated from the backend by
// scripts/build_waymaker_answer_fixtures.py) and assert, at every viewport
// project:
//
//   * the structured renderer (pa-answer-card-shell) shows the short answer,
//     the document buckets as semantic lists, notes and a compact source card;
//   * no raw Markdown, no internal source metadata, no provider/model names —
//     in visible text, accessibility attributes or the clipboard;
//   * no horizontal overflow, and the sticky composer never covers the
//     answer actions;
//   * free-form answers are formatted safely (headings, lists) and escaped;
//   * developer diagnostics appear only with ?debug=1.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const FIXTURES = path.join(process.cwd(), 'tests', 'fixtures', 'waymaker');
const fixture = (name) => JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf8'));

const VENDOR_RE = /openrouter|groq|ollama|nemotron|gemma|nvidia|inkling|thinkingmachines/i;
const INTERNAL_RE = /source[\s_-]*file|source_revision_date|grounding packet|fixture|parser[_ ]status/i;
const ENGINEERING_LABEL_RE = /\b(?:BASIS|SOURCED?|DISABLED|NOT WIRED|PARTIAL|UNVERIFIED)\b|기능 꺼짐/;

async function ask(page, payload, { question = 'D-2 연장시 필수 서류', query = '' } = {}) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await page.addInitScript(() => {
    window.__copied = [];
    try {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText: (text) => { window.__copied.push(String(text)); return Promise.resolve(); } },
      });
    } catch (e) { /* ignore */ }
  });
  let sentBody = null;
  await page.route('**/api/ask', (route) => {
    sentBody = JSON.parse(route.request().postData() || '{}');
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) });
  });
  await page.goto('/ai.html' + query);
  await page.fill('#aiQ', question);
  await page.click('#sendBtn');
  const agree = page.locator('#consentModal .btn-agree');
  if (await agree.isVisible().catch(() => false)) await agree.click();
  const card = page.locator('.answer-card').last();
  await expect(card).toBeVisible({ timeout: 15_000 });
  return { card, errors, sent: () => sentBody };
}

async function accessibleStrings(locator) {
  return locator.evaluate((root) => {
    const out = [];
    root.querySelectorAll('*').forEach((el) => {
      ['aria-label', 'title', 'alt', 'aria-description', 'data-tooltip'].forEach((a) => {
        const v = el.getAttribute(a);
        if (v) out.push(v);
      });
    });
    return out.join('\n');
  });
}

test.describe('Waymaker structured D-2 document answer', () => {
  test('renders the canonical checklist as a polished structured card', async ({ page }) => {
    const { card, errors } = await ask(page, fixture('d2_documents_ko_fast.json'));
    await expect(card.locator('.pa-answer-card[data-answer-kind="documents"]')).toHaveCount(1);
    await expect(card.locator('.answer-kicker')).toHaveText('Waymaker by Paradiso');
    await expect(card.locator('.answer-subline')).toHaveText('공식 자료 기반 안내');
    await expect(card.locator('.answer-mode-chip')).toHaveText('빠른 답변');
    await expect(card.locator('.pa-lead')).toContainText('D-2');
    // Semantic lists with the canonical buckets.
    const common = card.locator('[data-bucket-list="common"] > li');
    await expect(common).toHaveText(['신청서', '여권', '외국인등록증', '수수료']);
    await expect(card.locator('[data-bucket-title="common"]')).toHaveText('기본 서류');
    await expect(card.locator('[data-bucket-list="required"] > li')).toHaveCount(3);
    await expect(card.locator('[data-bucket-list="conditional"] > li')).toHaveCount(1);
    await expect(card.locator('[data-bucket-list="conditional"] > li')).toContainText('수료증명서');
    await expect(card.locator('[data-bucket="additional"]')).toBeHidden();
    // Compact source component.
    const source = card.locator('.pa-source-card');
    await expect(source).toContainText('외국인체류 안내매뉴얼 · 2026.6');
    await expect(source).toContainText('법무부 출입국·외국인정책본부');
    await expect(source).toContainText('pp. 43–44');
    // One disclaimer, no verbose evidence register, no diagnostics.
    await expect(card.locator('.pa-disclaimer')).toHaveCount(1);
    await expect(card.locator('.source-panel')).toHaveCount(0);
    await expect(card.locator('[data-diagnostics="developer"]')).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test('never shows Markdown, internal metadata, providers or engineering states', async ({ page }) => {
    const { card } = await ask(page, fixture('d2_documents_ko_fast.json'));
    const text = await card.innerText();
    expect(text).not.toMatch(/(^|\n)\s*#{1,6}\s/);
    expect(text).not.toContain('###');
    expect(text).not.toMatch(INTERNAL_RE);
    expect(text).not.toMatch(VENDOR_RE);
    expect(text).not.toMatch(ENGINEERING_LABEL_RE);
    const a11y = await accessibleStrings(page.locator('body'));
    expect(a11y).not.toMatch(VENDOR_RE);
    const pageText = await page.locator('body').innerText();
    expect(pageText).not.toMatch(VENDOR_RE);
    // Pseudo-element status pills are gone from the stylesheet too.
    const pseudo = await card.evaluate((root) => Array.from(root.querySelectorAll('*'))
      .map((el) => getComputedStyle(el, '::before').content)
      .filter((c) => c && c !== 'none' && c !== 'normal' && c !== '""').join(' '));
    expect(pseudo).not.toMatch(ENGINEERING_LABEL_RE);
  });

  test('copies clean plain text with section titles', async ({ page }) => {
    const { card } = await ask(page, fixture('d2_documents_ko_fast.json'));
    await card.locator('[data-copy-kind="answer"]').click();
    const copied = await page.evaluate(() => window.__copied.join('\n---\n'));
    expect(copied).toContain('기본 서류\n• 신청서\n• 여권');
    expect(copied).toContain('해당하는 경우 제출\n• 수료증명서');
    expect(copied).toContain('출처\n외국인체류 안내매뉴얼 2026.6, pp. 43-44');
    expect(copied).not.toMatch(/#{1,6}\s|\*\*/);
    expect(copied).not.toMatch(VENDOR_RE);
    expect(copied).not.toMatch(INTERNAL_RE);
    expect(copied).not.toMatch(/data-|<\/?[a-z]/i);
  });

  test('fits the viewport and the composer does not cover the answer actions', async ({ page }) => {
    const { card } = await ask(page, fixture('d2_documents_ko_fast.json'));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const cardBox = await card.boundingBox();
    const vw = page.viewportSize().width;
    expect(cardBox.x).toBeGreaterThanOrEqual(0);
    expect(cardBox.x + cardBox.width).toBeLessThanOrEqual(vw + 0.5);
    const copy = card.locator('[data-copy-kind="answer"]');
    await copy.scrollIntoViewIfNeeded();
    await page.waitForTimeout(150);
    const covered = await copy.evaluate((btn) => {
      const r = btn.getBoundingClientRect();
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return !(top === btn || btn.contains(top));
    });
    expect(covered).toBe(false);
  });

  test('localizes the product chrome in English', async ({ page }) => {
    const { card } = await ask(page, fixture('d2_documents_en_fast.json'), { question: 'What documents do I need to extend a D-2?' });
    await expect(card.locator('.answer-subline')).toHaveText('Guidance from official sources');
    await expect(card.locator('.answer-mode-chip')).toHaveText('Quick answer');
    await expect(card.locator('[data-bucket-title="common"]')).toHaveText('Basic documents');
    await expect(card.locator('[data-bucket-title="conditional"]')).toHaveText('Only if it applies to you');
    await expect(card.locator('.pa-lead')).toContainText('D-2 extension');
    expect(await card.innerText()).not.toMatch(VENDOR_RE);
  });
});

test.describe('Waymaker free-form answers and routing', () => {
  const base = () => {
    const f = fixture('d2_documents_ko_fast.json');
    delete f.structured_answer;
    return f;
  };

  test('formats Markdown headings and lists safely and escapes HTML', async ({ page }) => {
    const payload = {
      ...base(),
      copy_safe_answer: '',
      answer: '### 필수 서류\n- 신청서 <img src=x onerror="window.__xss=1">\n1. <script>window.__xss=2</script>첫째\n\n**중요**: 확인하세요 <b>raw</b>',
    };
    const { card } = await ask(page, payload);
    const body = card.locator('.answer-body');
    await expect(body.locator('h4.answer-subhead')).toHaveText('필수 서류');
    await expect(body.locator('ul > li')).toHaveCount(1);
    await expect(body.locator('ol > li')).toHaveCount(1);
    await expect(body.locator('img, script, b')).toHaveCount(0);
    expect(await body.innerText()).not.toContain('###');
    expect(await body.innerText()).toContain('<img src=x');
    expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  });

  test('structured data is rendered as text, never as HTML', async ({ page }) => {
    const f = fixture('d2_documents_ko_fast.json');
    f.structured_answer.short_answer = '<img src=x onerror="window.__xss=3">요약';
    f.structured_answer.required_documents.common[0].label = '<script>window.__xss=4</script>신청서';
    const { card } = await ask(page, f);
    await expect(card.locator('.pa-answer-card img, .pa-answer-card script')).toHaveCount(0);
    await expect(card.locator('.pa-lead')).toContainText('<img src=x');
    expect(await page.evaluate(() => window.__xss)).toBeUndefined();
  });

  test('shows the effective mode and a product-level escalation note', async ({ page }) => {
    const payload = { ...base(), answer: '답변입니다.', copy_safe_answer: '답변입니다.', answer_mode: 'basic', answer_mode_requested: 'fast', answer_mode_auto_escalated: true, answer_mode_escalation_reasons: ['complex_legal_issue'] };
    const { card } = await ask(page, payload);
    await expect(card.locator('.answer-mode-chip')).toHaveText('정밀 답변');
    await expect(card.locator('.answer-routing-note')).toHaveText('이 질문은 정확한 자료 확인이 필요해 정밀 답변으로 처리했어요.');
  });

  test('sends the selected mode, remembers it, and labels it without model names', async ({ page }) => {
    await page.goto('/ai.html');
    const fast = page.locator('.ai-mode-btn[data-mode="fast"]');
    await expect(fast).toContainText('빠른 답변');
    await expect(page.locator('.ai-mode-btn[data-mode="basic"]')).toContainText('정밀 답변');
    await fast.click();
    await expect(fast).toHaveAttribute('aria-checked', 'true');
    const { sent } = await ask(page, fixture('d2_documents_ko_fast.json'));
    expect(sent().answer_mode).toBe('fast');
    expect(sent().diagnostics).toBeUndefined();
    await page.reload();
    await expect(page.locator('.ai-mode-btn[data-mode="fast"]')).toHaveAttribute('aria-checked', 'true');
    const selectorText = await page.locator('#aiModeSelector').innerText();
    expect(selectorText).not.toMatch(VENDOR_RE);
  });

  test('limited fallback uses product language', async ({ page }) => {
    const f = fixture('d2_documents_ko_fast.json');
    const payload = { ...f, deterministic_fallback_answer_used: true, fallback_answer_kind: 'structured_document_checklist' };
    const { card } = await ask(page, payload);
    const text = await card.innerText();
    expect(text).toContain('확인된 공식 자료를 기준으로 기본 안내를 대신 표시합니다');
    expect(text).not.toMatch(/모델|provider|제공자|후보/i);
  });
});

test.describe('Waymaker developer diagnostics', () => {
  test('are available only with ?debug=1', async ({ page }) => {
    const f = fixture('d2_documents_ko_fast.json');
    const diagnostic = { ...f, provider: 'openrouter', llm_provider: 'openrouter', final_model: 'vendor/fast-model:free', selected_model: 'vendor/fast-model:free', primary_model: 'vendor/fast-model:free' };
    const { card, sent } = await ask(page, diagnostic, { query: '?debug=1' });
    expect(sent().diagnostics).toBe(true);
    const diag = card.locator('[data-diagnostics="developer"]');
    await expect(diag).toHaveCount(1);
    await diag.locator('summary').click();
    await expect(diag).toContainText('selected_model: vendor/fast-model:free');
    await expect(diag).toContainText('answer_mode_requested: fast');
    // Diagnostics never enter the clipboard.
    await card.locator('[data-copy-kind="answer"]').click();
    const copied = await page.evaluate(() => window.__copied.join('\n'));
    expect(copied).not.toContain('vendor/fast-model');
  });
});
