// Real-browser QA for the Waymaker procedure navigator (assets/js/waymaker-navigator.js
// mounted on the explicit ai.html?nav=1 route).
//
// Covers what the offline/jsdom harness cannot: actual layout at the mobile
// breakpoints (360 / 390 / 430 / 768 / desktop), no horizontal overflow,
// >=44px touch targets, the guided intake -> deterministic packet flow, the
// coverage-limited render, and that the deterministic flow never calls /api/ask.
//
// Run locally per playwright.config.mjs (it serves the repo statically; the page
// falls back to the committed visa_data.json when /api/visas is absent):
//   npm install && npm run test:e2e -- waymaker-navigator
import { test, expect } from '@playwright/test';

// A deterministic D-2 extension packet (mirrors the real builder's shape) so the
// FULL packet layout is exercised regardless of backend availability.
const D2_EXTENSION = {
  packetId: 'packet.D-2.extension', packetType: 'extension', statusCode: 'D-2',
  exactStatusCode: 'D-2', parentStatusCode: 'D-2', titleKo: '체류기간 연장허가', titleEn: 'Extension of Stay',
  userScenarioSummaryKo: '학사일정을 고려하여 체류기간을 부여합니다. 신청 시점과 재정입증 서류를 확인하세요.',
  applicability: { summaryKo: '유학(D-2) 체류기간 연장 준비 안내입니다.', conditions: [], limitations: [] },
  timing: { sourceBacked: false, limitationKo: '정확한 신청 가능 시점·기한은 1345/HiKorea/관할기관에서 확인하세요.', triggerEventKo: '체류기간 만료 전', stayPeriodHintKo: '1회 부여 체류기간 상한 2년' },
  documents: {
    commonDocs: [{ nameKo: '통합신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료', sourceBacked: true, sourceRefs: [{ sourceNameKo: '외국인체류 안내매뉴얼', versionDate: '2026.5', pageRange: 'pp. 43-44', evidenceLevel: 'source_confirmed' }], isOfficialForm: true }],
    requiredDocs: [{ nameKo: '재정입증 서류(잔고증명 등 장기 체류에 필요한 비용을 부담할 능력을 입증하는 서류)', sourceBacked: true, sourceRefs: [{ sourceNameKo: '외국인체류 안내매뉴얼', versionDate: '2026.5', pageRange: 'pp. 43-44', evidenceLevel: 'source_confirmed' }], isOfficialForm: false }],
    conditionalDocs: [{ nameKo: '수료증명서, 지도교수 및 유학담당자 확인서 (해당자)', sourceBacked: true, conditionKo: '해당자', sourceRefs: [], isOfficialForm: false }],
    additionalDocs: [], sourceBacked: true
  },
  fees: { items: [{ labelKo: '체류기간 연장허가 수수료', amountKo: '정부수입인지 60,000원', sourceBacked: false, sourceRefs: [] }], sourceBacked: false, limitationKo: '수수료는 면제·감면 여부에 따라 달라질 수 있어 최종 확인이 필요합니다.' },
  channels: { immigrationOfficeVisit: { availableKo: '관할 출입국·외국인관서 방문', sourceBacked: false }, limitationKo: '예약 필요 여부는 HiKorea/1345/관할기관에서 확인하세요.', hikoreaReservation: { taskTypeKo: '체류기간 연장허가', noteKo: 'HiKorea 전자민원 또는 방문예약 가능 여부를 확인하세요.', sourceBacked: false } },
  officeAndJurisdiction: { summaryKo: '관할 출입국·외국인관서(체류지 기준)에서 처리됩니다.', limitationKo: '정확한 관할 기관은 체류지에 따라 다릅니다.' },
  riskFlags: [{ flagKo: '신청 시점 주의', detailKo: '신청 시점을 놓치면 체류기간 초과 등 불이익이 생길 수 있습니다.', severity: 'reminder' }],
  sourceLens: { overallLevel: 'source_confirmed', overallLabelKo: '공식근거 직접 확인', overallLabelEn: 'Confirmed in official source', sources: [{ sourceNameKo: '외국인체류 안내매뉴얼', versionDate: '2026.5', pageRange: 'pp. 43-44' }], finalAgencyDiscretionKo: '관할기관 최종심사 필요', finalAgencyDiscretionEn: "Subject to competent authority's final review" },
  coverageSummary: { level: 'full', isLimited: false, hasDocuments: true, procedureAvailable: true },
  nextActions: ['준비 서류 목록을 공식 기준에 맞춰 하나씩 확인·준비하세요.', 'HiKorea 예약 또는 관할 출입국·외국인관서 방문 가능 여부를 확인하세요.'],
  finalAgencyNoteKo: '이 패킷은 신청 준비를 돕는 안내이며, 실제 허가 여부는 관할 출입국·외국인관서 기준에 따릅니다.',
  finalAgencyNoteEn: 'This packet is preparation guidance only.', version: 'test'
};

function limitedPacket(status, procedure) {
  return {
    packetId: 'packet.' + status + '.' + procedure, packetType: procedure, statusCode: status, exactStatusCode: status,
    titleKo: '체류자격 변경허가', titleEn: 'Change of Status',
    applicability: { summaryKo: '', conditions: [], limitations: ['이 체류자격에서 해당 절차의 적용 여부가 공식근거로 확인되지 않았습니다.'] },
    timing: { sourceBacked: false, limitationKo: '기한 확인 필요' },
    documents: { commonDocs: [], requiredDocs: [], conditionalDocs: [], additionalDocs: [], sourceBacked: false, limitationKo: '공식 서류 목록이 아직 구조화되지 않았습니다.' },
    fees: { items: [], sourceBacked: false, limitationKo: '확인 필요' }, channels: { limitationKo: 'HiKorea 확인' },
    officeAndJurisdiction: { summaryKo: '관할기관', limitationKo: 'HiKorea/1345 확인' }, riskFlags: [],
    sourceLens: { overallLevel: 'unavailable', overallLabelKo: '공식근거 확인 불가', overallLabelEn: 'No current source coverage', sources: [], finalAgencyDiscretionKo: '관할기관 최종심사 필요' },
    coverageSummary: { level: 'unavailable', isLimited: true, hasDocuments: false },
    nextActions: ['1345/HiKorea/관할 출입국·외국인관서에서 공식 목록을 확인하세요.'],
    finalAgencyNoteKo: '준비 안내', finalAgencyNoteEn: 'Preparation guidance.', version: 'test'
  };
}

let askCalled = false;

async function stubBackend(page) {
  askCalled = false;
  // The deterministic packet must come from /api/procedure-packet; /api/ask must
  // never be hit during the packet flow.
  await page.route('**/api/procedure-packet*', (route) => {
    const url = new URL(route.request().url());
    const proc = url.searchParams.get('procedure');
    const status = url.searchParams.get('status');
    const body = proc === 'extension' ? D2_EXTENSION : limitedPacket(status, proc);
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.route('**/api/ask', (route) => {
    askCalled = true;
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ answer: '설명입니다.', copy_safe_answer: '설명입니다.' }) });
  });
  // /api/visas is absent on the static server → navigator falls back to
  // ./visa_data.json (served by the http.server). Let it through.
}

async function mountAndStart(page) {
  await page.goto('/ai.html?nav=1');
  await page.waitForSelector('#waymakerNavigatorRoot.wm-root', { timeout: 20_000 });
  // intake catalog loaded → Start button present
  const start = page.locator('.wm-intro .wm-btn-primary');
  await expect(start).toBeVisible({ timeout: 20_000 });
  return start;
}

async function noHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'no horizontal overflow').toBeLessThanOrEqual(1);
}

async function touchTargetsOk(page, selector) {
  const small = await page.evaluate((sel) => {
    const els = [...document.querySelectorAll(sel)].filter((e) => e.offsetParent !== null);
    return els.map((e) => Math.round(e.getBoundingClientRect().height)).filter((h) => h > 0 && h < 44);
  }, selector);
  expect(small, `${selector} all >=44px (offenders: ${small.join(',')})`).toEqual([]);
}

async function driveToD2Extension(page, start) {
  await start.click();
  await page.locator('.wm-chip', { hasText: '한국어' }).click();
  await page.locator('.wm-chip', { hasText: '한국 내' }).click();
  await page.locator('.wm-search').fill('D-2');
  await page.locator('.wm-status-row', { hasText: 'D-2' }).first().click();
  await page.locator('.wm-proc-row', { hasText: '체류기간 연장' }).click();
  // D-2 is materially ambiguous → sub-status clarification; choose "잘 모르겠어요"
  await page.locator('.wm-status-row', { hasText: '잘 모르겠어요' }).click();
  await page.waitForSelector('.wm-packet-title', { timeout: 15_000 });
}

test.describe('Waymaker navigator — guided intake & deterministic packet', () => {
  test.beforeEach(async ({ page }) => { await stubBackend(page); });

  test('opens to guided navigation, not a blank chat', async ({ page }) => {
    await mountAndStart(page);
    // chat transcript + composer hidden by default (wm-active)
    await expect(page.locator('#chatHistory')).toBeHidden();
    await expect(page.locator('.chat-input-area')).toBeHidden();
    await expect(page.locator('#aiModeSelector')).toBeHidden(); // Fast/Basic/Pro hidden
    await expect(page.locator('.quota-badge')).toBeHidden();    // quota hidden
    await expect(page.locator('.ai-title')).toBeHidden();       // legacy "AI 도우미" title hidden
    await noHorizontalOverflow(page);
  });

  test('D-2 extension → deterministic Action Packet, no /api/ask', async ({ page }) => {
    const start = await mountAndStart(page);
    await driveToD2Extension(page, start);
    await expect(page.locator('.wm-packet-title')).toContainText('체류기간 연장허가');
    await expect(page.locator('.wm-next-list li').first()).toBeVisible();
    await expect(page.locator('.wm-cov-badge').first()).toBeVisible();
    // a source_confirmed (full) packet must show the confirmed coverage label on
    // the hero badge — NOT the limited "관할기관 확인 필요" fallback.
    await expect(page.locator('.wm-card-hero .wm-cov-badge')).toHaveText('공식 원문 확인');
    await expect(page.locator('.wm-doc-check').first()).toBeVisible();          // checklist
    await expect(page.locator('button', { hasText: 'HiKorea 예약 경로 확인' })).toBeVisible();
    await expect(page.locator('button', { hasText: '이 패킷에서 헷갈리는 점 묻기' })).toBeVisible();
    expect(askCalled, '/api/ask must not be called before AI follow-up').toBe(false);
    await noHorizontalOverflow(page);
    // The doc checkbox's real tap target is its label (clickable via for=).
    await touchTargetsOk(page, '.wm-btn, .wm-acc-head, .wm-doc-label');
  });

  test('coverage-limited packet renders warning, fabricates nothing', async ({ page }) => {
    const start = await mountAndStart(page);
    await start.click();
    await page.locator('.wm-chip', { hasText: '한국어' }).click();
    await page.locator('.wm-chip', { hasText: '한국 내' }).click();
    await page.locator('.wm-search').fill('D-2');
    await page.locator('.wm-status-row', { hasText: 'D-2' }).first().click();
    await page.locator('.wm-proc-row', { hasText: '체류자격 변경' }).click();
    await page.locator('.wm-status-row', { hasText: '잘 모르겠어요' }).click();
    await page.waitForSelector('.wm-card-warn', { timeout: 15_000 });
    await expect(page.locator('.wm-card-warn')).toContainText('공식 근거가 충분히 구조화되어 있지 않습니다');
    expect(await page.locator('.wm-doc-row').count(), 'no fabricated documents').toBe(0);
    await noHorizontalOverflow(page);
  });

  test('AI follow-up only after packet, gated on consent, then calls /api/ask', async ({ page }) => {
    const start = await mountAndStart(page);
    await driveToD2Extension(page, start);
    expect(askCalled).toBe(false);
    await page.locator('button', { hasText: '이 패킷에서 헷갈리는 점 묻기' }).click();
    const input = page.locator('.wm-ai-input');
    await expect(input).toBeVisible();
    expect(askCalled, 'opening follow-up does not call /api/ask').toBe(false);
    await input.fill('재정서류가 면제될 수 있나요?');
    // First submit WITHOUT consent → must NOT call /api/ask; the consent modal appears.
    await page.locator('.wm-ai button', { hasText: '질문하기' }).click();
    await page.waitForTimeout(400);
    expect(askCalled, '/api/ask gated until consent accepted').toBe(false);
    await expect(page.locator('#consentModal.active')).toBeVisible();
    // Accept consent via the real modal, then submit again → now it sends.
    await page.locator('#consentModal .btn-agree').click();
    await expect(page.locator('#consentModal.active')).toHaveCount(0);
    await page.locator('.wm-ai button', { hasText: '질문하기' }).click();
    await expect.poll(() => askCalled, { timeout: 10_000 }).toBe(true);
  });
});

test('Waymaker default route restores the evidence-grounded AI workspace', async ({ page }) => {
  await page.goto('/ai.html');
  await expect(page.locator('#chatHistory')).toBeVisible();
  await expect(page.locator('.chat-input-area')).toBeVisible();
  await expect(page.locator('#waymakerNavigatorRoot')).toBeHidden();
  await expect(page.locator('[data-workspace-route="chat"]')).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('#welcomeMessage')).toContainText('공개 법령·매뉴얼');
  await noHorizontalOverflow(page);
});

// Layout must hold across the mobile breakpoints (run via the per-viewport
// Playwright projects: mobile-360 / mobile-390 / mobile-430 / tablet-768 / desktop-1280).
test('responsive: no horizontal overflow + tappable through the packet', async ({ page }) => {
  await stubBackend(page);
  const start = await mountAndStart(page);
  await noHorizontalOverflow(page);                 // intro
  await driveToD2Extension(page, start);            // through to packet
  await noHorizontalOverflow(page);                 // packet
  await touchTargetsOk(page, '.wm-btn, .wm-status-row, .wm-proc-row, .wm-chip, .wm-acc-head');
  // long official document name must wrap, not force a scrollbar
  await noHorizontalOverflow(page);
});
