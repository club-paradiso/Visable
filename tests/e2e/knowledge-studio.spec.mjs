// Real-browser tests for the Waymaker Knowledge Studio (knowledge-studio.html)
// and the public answer-feedback control (ai.html).
//
// The operator API is mocked with responses shaped exactly like
// services/knowledge/api.py returns them (the backend test
// test_knowledge_studio_contract pins those shapes). Asserted at every
// viewport project:
//
//   * the Studio is closed without a token and says so in product language;
//   * review: proposed vs current diff, provenance, evidence, impact, and a
//     reason is REQUIRED before publish / reject reach the API;
//   * all API values render as text (no markup injection);
//   * tabs are keyboard-operable; no horizontal page overflow;
//   * the token never lands in localStorage;
//   * answer feedback posts only a fixed reason + the opaque answer_ref.
import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const TOKEN = 'e2e-operator-token-0123456789';
const XSS = '<img src=x onerror="window.__pwned=1">';

const citation = (edition, page) => ({
  source_title: '외국인체류 안내매뉴얼', version_label: edition, page_start: page, page_end: page,
  section_title: '유학(D-2) 체류기간 연장허가 — 다. 제출서류', locator: 'hwp_line:1266',
  content_review_state: edition === '2026.9' ? 'needs_review' : 'approved', version_status: edition === '2026.9' ? 'staged' : 'superseded',
});
const proposed = {
  fact_id: 'kf_new', value_text: '재정입증 서류', lifecycle_state: 'HUMAN_REVIEW_REQUIRED', variant_key: 'D-2|*|extension|general',
  property: 'required_document', origin: 'parser_extraction', created_by_kind: 'parser',
  extraction_warnings: ['document anchor resolves before the section heading; verify the page'],
  citations: [citation('2026.9', 43)],
};
const task = {
  task_id: 'rt_1', fact_id: 'kf_new', task_kind: 'update_fact', status: 'open', priority_score: 54,
  priority_factors: { gap_frequency: 0, user_feedback: 0, procedure_risk: 2, source_authority_rank: 2, affected_evals: 1, open_conflicts: 0, age_days: 0 },
  value_text: '재정입증 서류', lifecycle_state: 'HUMAN_REVIEW_REQUIRED', status_code: 'D-2', subcode: null, procedure: 'extension',
  variant_key: 'D-2|*|extension|general', compare_fact_id: 'kf_old',
};
const MOCK = {
  '/overview': { operator: 'e2e-operator', storage: { durable: true, open_error: '' },
    metrics: { pending_review: 43, open_review_tasks: 43, open_conflicts: 1, unresolved_gaps: 5, new_unknown_clusters_7d: 4,
      published_facts: 42, superseded_facts: 0, failing_eval_cases: 0, sources_needing_refresh: 1, feedback_7d: 1 },
    sources_needing_refresh: [{ source_key: 'stay_guide_manual', title: '외국인체류 안내매뉴얼', stale_editions: ['stay_manual_2026_06_23_pdf'], current_editions: ['stay_manual_2026_07_31_hwp'] }] },
  '/review-queue': { tasks: [task, { ...task, task_id: 'rt_2', fact_id: 'kf_xss', task_kind: 'new_fact', priority_score: 30, value_text: XSS }] },
  '/review-queue/rt_1': {
    task, proposed, conflicts: [],
    current_published: { ...proposed, fact_id: 'kf_old', lifecycle_state: 'PUBLISHED', citations: [citation('2026.6', 43)] },
    diff: { current: { value_text: '재정입증 서류', requirement_level: 'required', condition_kind: 'always', source: '외국인체류 안내매뉴얼 2026.6', pages: '43-44' },
            proposed: { value_text: '재정입증 서류', requirement_level: 'conditional', condition_kind: 'conditional', source: '외국인체류 안내매뉴얼 2026.9', pages: '43' },
            changed_fields: ['requirement_level', 'condition_kind', 'source', 'pages'] },
    impact: { affected_eval_count: 1, affected_eval_cases: [{ case_key: 'd2.extension.documents.ko' }], would_supersede: ['kf_old'], requires_regression_rerun: true },
    audit: [{ at: '2026-09-25T00:00:00Z', actor: 'parser:status_guidance', actor_kind: 'parser', action: 'propose', reason: '' }],
  },
  '/review-queue/rt_2': { task: { ...task, task_id: 'rt_2' }, proposed: { ...proposed, fact_id: 'kf_xss', value_text: XSS }, conflicts: [],
    current_published: null, diff: null, impact: { affected_eval_count: 0, would_supersede: [] }, audit: [] },
  '/evidence/kf_new': { evidence: [{ source: '외국인체류 안내매뉴얼 2026.9', pages: '43', kind: 'parsed_page_text', match_found: true, text: '재정입증 서류 생략 ' + XSS }] },
  '/evidence/kf_xss': { evidence: [{ source: '외국인체류 안내매뉴얼 2026.9', pages: '43', kind: 'none', match_found: false, text: '' }] },
  '/facts': { facts: [{ ...proposed, fact_id: 'kf_old', lifecycle_state: 'PUBLISHED', condition_kind: 'always', verified_by: 'legacy:stay', reviewer_kind: 'legacy_repository_verification' }] },
  '/conflicts': { conflicts: [{ conflict_id: 'kc_1', slot_key: 'H-2|*|extension|general|required_document|고용보험', conflict_kind: 'value_mismatch', status: 'open', fact_a_id: 'kf_a', fact_b_id: 'kf_b',
    fact_a: { value_text: '고용보험 가입내역', condition_kind: 'always', lifecycle_state: 'HUMAN_REVIEW_REQUIRED', authority_type: 'approved_manual', source: { title: '외국인체류 안내매뉴얼', version: '2026.9', pages: '540' } },
    fact_b: { value_text: '고용보험 가입내역 (해당자)', condition_kind: 'conditional', lifecycle_state: 'AI_EXTRACTED', authority_type: 'approved_manual', source: { title: '외국인체류 안내매뉴얼', version: '2026.9', pages: '541' } } }] },
  '/sources': { sources: [{ source_id: 'src_1', source_key: 'stay_guide_manual', title_ko: '외국인체류 안내매뉴얼', refresh_state: 'refresh_due', versions: [
    { source_version_id: 'srv_9', version_label: '2026.9', edition_ref: 'stay_manual_2026_09_18_pdf', status: 'staged', content_review_state: 'needs_review', effective_from: null, published_fact_count: 0, pending_fact_count: 43 },
    { source_version_id: 'srv_6', version_label: '2026.6', edition_ref: 'stay_manual_2026_06_23_pdf', status: 'superseded', content_review_state: 'needs_review', effective_from: '2026-06-23', published_fact_count: 42, pending_fact_count: 0 }] }] },
  '/diff': { from: { version: '2026.6' }, to: { version: '2026.9' }, summary: { ADDED: 0, REMOVED: 0, CHANGED: 1, UNCHANGED: 1 }, records: [
    { change: 'CHANGED', status_code: 'D-2', subcode: null, procedure: 'extension', changed_fields: ['requirement_level', 'condition'],
      from: { value_text: '재정입증 서류', requirement_level: 'required' }, to: { value_text: '재정입증 서류', requirement_level: 'conditional' }, affected_eval_cases: ['d2.extension.documents.ko'] },
    { change: 'UNCHANGED', status_code: 'D-2', subcode: null, procedure: 'extension', changed_fields: [],
      from: { value_text: '여권', requirement_level: 'common' }, to: { value_text: '여권', requirement_level: 'common' }, affected_eval_cases: [] }] },
  '/gaps': { gaps: [{ gap_id: 'gap_1', reason_code: 'NO_VERIFIED_KNOWLEDGE', status_code: 'H-2', subcode: null, procedure: 'extension', intent: 'required_documents',
    occurrence_count: 2, feedback_count: 0, last_seen: '2026-09-25T00:00:00Z', example_query: 'H-2 연장 서류 알려줘요. 제 번호 [PHONE]', resolution_status: 'open' }] },
  '/evals': { cases: [{ case_id: 'ev_1', case_key: 'd2.extension.documents.ko', query: 'D-2 연장시 필수 서류', origin: 'seed_foundation', state: 'approved', last_result: { passed: true, failures: [] } },
    { case_id: 'ev_2', case_key: 'gap.h2.extension', query: 'H-2 체류기간 연장 필요 서류', origin: 'promoted_gap', state: 'draft', last_result: null }] },
  '/audit': { audit: [{ at: '2026-09-25T00:00:00Z', actor: 'e2e-operator', actor_kind: 'human_operator', entity_type: 'fact', entity_id: 'kf_old', action: 'transition:PUBLISHED', reason: 'p.43' }] },
};

async function studio(page, { token = TOKEN, closed = false } = {}) {
  const posts = [];
  await page.route('**/api/knowledge/studio/**', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const sub = url.pathname.replace(/^.*\/api\/knowledge\/studio/, '');
    if (closed) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: { error: 'operator_auth_not_configured' } }) });
    if (req.headers().authorization !== `Bearer ${token}`) return route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":{"error":"operator_auth_invalid"}}' });
    if (req.method() === 'POST') {
      posts.push({ path: sub, body: JSON.parse(req.postData() || '{}') });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ fact: { ...proposed, lifecycle_state: 'HUMAN_REVIEWED' }, ok: true }) });
    }
    const body = MOCK[sub];
    return route.fulfill({ status: body ? 200 : 404, contentType: 'application/json', body: JSON.stringify(body || { detail: { error: 'NOT_FOUND' } }) });
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  await page.goto('/knowledge-studio.html');
  return { posts, errors };
}

async function signIn(page) {
  await page.fill('#ks-token', TOKEN);
  await page.click('#ks-login-form button[type="submit"]');
  await expect(page.locator('#ks-app')).toBeVisible();
}

async function noPageOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

test.describe('Waymaker Knowledge Studio', () => {
  test('is closed when the server has no operator tokens', async ({ page }) => {
    await studio(page, { closed: true });
    await page.fill('#ks-token', TOKEN);
    await page.click('#ks-login-form button[type="submit"]');
    await expect(page.locator('#ks-login-error')).toContainText('꺼져 있습니다');
    await expect(page.locator('#ks-app')).toBeHidden();
  });

  test('rejects a wrong token and keeps it out of localStorage', async ({ page }) => {
    await studio(page, { token: 'another-token-0000000000' });
    await page.fill('#ks-token', TOKEN);
    await page.click('#ks-login-form button[type="submit"]');
    await expect(page.locator('#ks-login-error')).toContainText('유효하지 않습니다');
    expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(TOKEN);
  });

  test('overview answers "what should I review next?"', async ({ page }) => {
    const { errors } = await studio(page);
    await signIn(page);
    await expect(page.locator('#ks-operator')).toContainText('e2e-operator');
    await expect(page.locator('.ks-metric').filter({ hasText: '검토 대기 지식' })).toContainText('43');
    await expect(page.locator('.ks-banner')).toContainText('stay_manual_2026_06_23_pdf');
    await expect(page.locator('tbody tr')).toHaveCount(2);
    expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(TOKEN);
    await noPageOverflow(page);
    expect(errors).toEqual([]);
  });

  test('review shows diff, provenance, evidence, impact; publish and reject need a reason', async ({ page }) => {
    const { posts } = await studio(page);
    await signIn(page);
    await page.getByRole('tab', { name: '검토 대기열' }).click();
    await page.locator('tbody tr').filter({ hasText: '재정입증 서류' }).first().click();
    const detail = page.locator('#ks-task-detail');
    await expect(detail.locator('table.ks-diff')).toContainText('요건 수준 (변경)');
    await expect(detail.locator('table.ks-diff')).toContainText('conditional');
    await expect(detail).toContainText('외국인체류 안내매뉴얼 2026.9, p. 43');
    await expect(detail).toContainText('d2.extension.documents.ko');
    await expect(detail.locator('.ks-evidence')).toContainText('재정입증 서류 생략');
    await expect(detail).toContainText('문구 일치 확인');
    await noPageOverflow(page);

    // Reject without a reason never reaches the API.
    await detail.getByRole('button', { name: '반려' }).click();
    await expect(page.locator('#ks-dialog')).toBeVisible();
    await page.locator('#ks-dialog-confirm').click();
    // The reason field is required: native validation keeps the dialog open.
    await expect(page.locator('#ks-dialog')).toBeVisible();
    expect(await page.locator('#ks-action-reason').evaluate((el) => el.validity.valueMissing)).toBe(true);
    await page.locator('#ks-dialog-cancel').click();
    await expect(page.locator('#ks-dialog')).toBeHidden();
    expect(posts).toEqual([]);

    await detail.getByRole('button', { name: '승인(검토 완료)' }).click();
    await page.fill('#ks-action-reason', 'p.43 제출서류 목록과 일치');
    await page.locator('#ks-dialog-confirm').click();
    await expect.poll(() => posts.length).toBe(1);
    expect(posts[0]).toEqual({ path: '/facts/kf_new/actions', body: { action: 'approve', reason: 'p.43 제출서류 목록과 일치' } });
  });

  test('API values render as text, never as markup', async ({ page }) => {
    await studio(page);
    await signIn(page);
    await page.getByRole('tab', { name: '검토 대기열' }).click();
    await expect(page.locator('tbody')).toContainText('<img src=x');
    await page.locator('tbody tr').filter({ hasText: '<img' }).first().click();
    await expect(page.locator('#ks-task-detail h2').first()).toContainText('<img src=x');
    await expect(page.locator('#ks-view img')).toHaveCount(0);
    expect(await page.evaluate(() => window.__pwned)).toBeUndefined();
  });

  test('conflicts, source diff, gaps, evals and audit views render', async ({ page }) => {
    const { errors } = await studio(page);
    await signIn(page);
    await page.getByRole('tab', { name: '충돌' }).click();
    await expect(page.locator('#ks-view')).toContainText('고용보험 가입내역 (해당자)');
    await expect(page.getByRole('button', { name: 'A 유지' })).toBeVisible();
    await page.getByRole('tab', { name: '출처·버전' }).click();
    await page.getByRole('button', { name: '비교', exact: true }).click();
    await expect(page.locator('#ks-diff-out')).toContainText('변경 1');
    await expect(page.locator('#ks-diff-out')).toContainText('requirement_level');
    await page.getByRole('tab', { name: '미지 질문' }).click();
    await expect(page.locator('#ks-view')).toContainText('[PHONE]');
    await page.getByRole('tab', { name: '평가' }).click();
    await expect(page.locator('#ks-view')).toContainText('gap.h2.extension');
    await page.getByRole('tab', { name: '감사 기록' }).click();
    await expect(page.locator('#ks-view')).toContainText('transition:PUBLISHED');
    await noPageOverflow(page);
    expect(errors).toEqual([]);
  });

  test('tabs are keyboard operable', async ({ page }) => {
    await studio(page);
    await signIn(page);
    const first = page.getByRole('tab', { name: '개요' });
    await first.focus();
    await page.keyboard.press('ArrowDown');
    await expect(page.getByRole('tab', { name: '검토 대기열' })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('tab', { name: '검토 대기열' })).toBeFocused();
  });
});

test.describe('Waymaker answer feedback', () => {
  test('sends a fixed reason and the opaque answer reference only', async ({ page }) => {
    const fixture = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'tests', 'fixtures', 'waymaker', 'd2_documents_ko_fast.json'), 'utf8'));
    let feedback = null;
    await page.route('**/api/ask', (route) => route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ ...fixture, answer_ref: 'obs_0123456789abcdef0123' }) }));
    await page.route('**/api/feedback', (route) => { feedback = JSON.parse(route.request().postData() || '{}');
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' }); });
    await page.goto('/ai.html');
    await page.fill('#aiQ', 'D-2 연장시 필수 서류');
    await page.click('#sendBtn');
    const agree = page.locator('#consentModal .btn-agree');
    if (await agree.isVisible().catch(() => false)) await agree.click();
    const box = page.locator('.answer-card').last().locator('.answer-feedback');
    await expect(box).toBeVisible({ timeout: 15_000 });
    await box.locator('summary').click();
    await box.getByRole('button', { name: '빠진 정보가 있어요' }).click();
    await expect(box.locator('[role="status"]')).toContainText('고마워요');
    expect(feedback).toEqual({ reason: 'MISSING_INFORMATION', answer_ref: 'obs_0123456789abcdef0123', language: 'ko' });
    await expect(box.locator('textarea, input[type="text"]')).toHaveCount(0);
  });

  test('is not shown without a knowledge reference', async ({ page }) => {
    const fixture = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'tests', 'fixtures', 'waymaker', 'd2_documents_ko_fast.json'), 'utf8'));
    await page.route('**/api/ask', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fixture) }));
    await page.goto('/ai.html');
    await page.fill('#aiQ', 'D-2 연장시 필수 서류');
    await page.click('#sendBtn');
    const agree = page.locator('#consentModal .btn-agree');
    if (await agree.isVisible().catch(() => false)) await agree.click();
    await expect(page.locator('.answer-card').last()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.answer-feedback')).toHaveCount(0);
  });
});
