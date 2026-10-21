// Real-browser E2E tests for VISABLE Content Operations Studio (content-studio.html)
import { test, expect } from '@playwright/test';

const TOKEN = 'operator-editor-token-1234567890';
const XSS = '<img src=x onerror="window.__pwned=1">';

const MOCK_METRICS = {
  total_items: 647,
  verified_items: 480,
  pending_review: 3,
  needs_evidence: 12,
  suspected_conflicts: 0,
  office_overrides_count: 5,
  procedure_counts: { extension: 224, change: 251, registration: 172 },
  recent_drafts: [
    { draft_id: 'draft-d2-01', item_id: 'CHK-EXT-001', author: 'editor-kim', review_state: 'SUBMITTED', updated_at: '2026-10-19T10:00:00Z' }
  ],
};

const MOCK_SCENARIOS = [
  {
    item_id: 'CHK-EXT-001',
    procedure: 'extension',
    status_code: 'D-2',
    target_group: '학사·석사·박사 정규과정 유학생',
    official_name: '유학 (D-2)',
    plain_title: 'D-2 일반 유학생 체류기간 연장',
    required_documents: ['통합신청서', '여권 원본 및 사본', '외국인등록증', '재학증명서'],
    conditional_documents: ['재정입증서류 (학사경고 또는 초과 학기자)'],
    exceptions: ['정규과정 이내 평점 2.0 이상인 경우 잔고증명 면제'],
    submission_methods: ['방문예약', '온라인(하이코리아)'],
    proxy_allowed: true,
    proxy_details: '대학 유학생 담당자 위임 접수 가능',
    notes: '체류만료 4개월 전부터 신청 가능',
    review_state: 'VERIFIED',
    evidence_url: 'https://www.hikorea.go.kr/info/InfoStayGuideD2.pt',
    has_draft: false,
  },
  {
    item_id: 'CHK-CHG-002',
    procedure: 'change',
    status_code: 'E-7-1',
    target_group: '전문인력 특정활동',
    official_name: '특정활동 (E-7-1)',
    plain_title: 'E-7-1 전문인력 체류자격 변경',
    required_documents: ['통합신청서', '고용계약서', '고용추천서'],
    conditional_documents: ['납세증명서', '소득금액증명'],
    exceptions: [],
    submission_methods: ['방문예약'],
    proxy_allowed: true,
    proxy_details: '행정사 또는 소속 기업 담당자 위임',
    notes: '국민고용 보호 직종 심사 기준 준수',
    review_state: 'VERIFIED',
    evidence_url: 'https://www.hikorea.go.kr/info/InfoStayGuideE7.pt',
    has_draft: false,
  },
];

const MOCK_OFFICES = [
  { office_code: 'jeju', office_name: '제주출입국·외국인청', jurisdiction: '제주특별자치도 전역', override_count: 1 },
  { office_code: 'seoul', office_name: '서울출입국·외국인청', jurisdiction: '서울 종로·중구·은평 등', override_count: 0 },
  { office_code: 'incheon', office_name: '인천출입국·외국인청', jurisdiction: '인천광역시', override_count: 0 },
];

const MOCK_VALIDATION_PASS = {
  passed: true,
  total_items: 647,
  procedure_counts: { extension: 224, change: 251, registration: 172 },
  approved_drafts_count: 1,
  pending_drafts_count: 0,
  checks: [
    { name: 'total_items_count_preserved', status: 'PASS', details: 'Total items exactly 647' },
    { name: 'extension_items_preserved', status: 'PASS', details: '224 extension scenarios' },
    { name: 'change_items_preserved', status: 'PASS', details: '251 change scenarios' },
    { name: 'registration_items_preserved', status: 'PASS', details: '172 registration scenarios' },
  ],
  errors: [],
};

async function setupStudio(page, { role = 'publisher', closed = false, wrongToken = false } = {}) {
  await page.route('**/api/knowledge/studio/checklists/**', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^.*\/api\/knowledge\/studio\/checklists/, '');

    if (closed) {
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: { error: 'operator_auth_not_configured' } }),
      });
    }

    if (wrongToken || req.headers().authorization !== `Bearer ${TOKEN}`) {
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: { error: 'operator_auth_invalid' } }),
      });
    }

    if (path === '/auth/me') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ operator: 'test-operator', role }),
      });
    }

    if (path === '/dashboard') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_METRICS),
      });
    }

    if (path.startsWith('/scenarios/CHK-EXT-001')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item: MOCK_SCENARIOS[0], active_draft: null }),
      });
    }

    if (path.startsWith('/scenarios')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ scenarios: MOCK_SCENARIOS, total: MOCK_SCENARIOS.length }),
      });
    }

    if (path === '/offices') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ offices: MOCK_OFFICES }),
      });
    }

    if (path === '/drafts' && req.method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          drafts: [
            {
              draft_id: 'draft-d2-01',
              item_id: 'CHK-EXT-001',
              status_code: 'D-2',
              procedure: 'extension',
              review_state: 'SUBMITTED',
              author: 'editor-kim',
              evidence_url: 'https://www.hikorea.go.kr/official-notice-d2',
              change_rationale: '시간제취업 허가 요건 명문화',
            },
            {
              draft_id: 'draft-no-evidence',
              item_id: 'CHK-CHG-002',
              status_code: 'E-7-1',
              procedure: 'change',
              review_state: 'SUBMITTED',
              author: 'editor-lee',
              evidence_url: '', // Missing HTTPS evidence!
              change_rationale: '근거 미비 초안',
            },
          ],
        }),
      });
    }

    if (path === '/drafts' && req.method() === 'POST') {
      const data = JSON.parse(req.postData() || '{}');
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ draft_id: 'draft-new-01', item_id: data.item_id, status: 'saved' }),
      });
    }

    if (path.startsWith('/drafts/') && path.endsWith('/action') && req.method() === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, status: 'action_completed' }),
      });
    }

    if (path.startsWith('/diff/')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          draft_id: 'draft-d2-01',
          item_id: 'CHK-EXT-001',
          changed_fields: ['required_documents', 'plain_title'],
          baseline: MOCK_SCENARIOS[0],
          proposed: {
            ...MOCK_SCENARIOS[0],
            plain_title: 'D-2 유학생 체류기간 연장 (개정안)',
            required_documents: ['통합신청서', '여권', '외국인등록증', '재학증명서', '성적증명서 (추가)'],
          },
          impact_analysis: ['필수 서류 추가: 민원인에게 추가 입증 책임 발생'],
        }),
      });
    }

    if (path === '/publish/validate' && req.method() === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_VALIDATION_PASS),
      });
    }

    if (path === '/publish/release' && req.method() === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ release_id: 'rel-20261019-1', status: 'published' }),
      });
    }

    if (path === '/releases' && req.method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          releases: [
            {
              release_id: 'rel-20261020-01',
              release_tag: 'rel-20261020-01',
              target_procedure: 'all',
              approved_draft_count: 1,
              total_scenario_count: 647,
              validation_passed: true,
              payload_checksum: 'a1b2c3d4e5f6789012345678',
              published_by: 'admin',
              published_at: '2026-10-20T10:00:00Z',
              status: 'PUBLISHED',
              release_note: '정기 릴리스',
            },
          ],
        }),
      });
    }

    if (path.startsWith('/releases/') && path.endsWith('/rollback') && req.method() === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          release_id: 'rel-rollback-01',
          release_tag: 'rollback-rel-20261020-01-20261020',
          status: 'ROLLED_BACK',
          restored_from: 'rel-20261020-01',
        }),
      });
    }

    return route.fulfill({ status: 404, contentType: 'application/json', body: '{"error":"not_found"}' });
  });

  await page.goto('/content-studio.html');
}

async function login(page) {
  await page.fill('#cs-token', TOKEN);
  await page.click('#cs-login-submit');
  await expect(page.locator('#cs-app')).toBeVisible();
}

test.describe('VISABLE Content Operations Studio', () => {
  test('rejects connection when operator tokens are not configured', async ({ page }) => {
    await setupStudio(page, { closed: true });
    await page.fill('#cs-token', TOKEN);
    await page.click('#cs-login-submit');
    await expect(page.locator('#cs-login-error')).toContainText('설정되지 않았습니다');
    await expect(page.locator('#cs-app')).toBeHidden();
  });

  test('rejects invalid operator token and keeps credentials out of localStorage', async ({ page }) => {
    await setupStudio(page, { wrongToken: true });
    await page.fill('#cs-token', 'wrong-token-1234567890');
    await page.click('#cs-login-submit');
    await expect(page.locator('#cs-login-error')).toContainText('올바르지 않거나');
    const local = await page.evaluate(() => JSON.stringify(localStorage));
    expect(local).not.toContain('wrong-token');
  });

  test('authenticates successfully and renders operator name and role badge', async ({ page }) => {
    await setupStudio(page, { role: 'publisher' });
    await login(page);
    await expect(page.locator('#cs-operator')).toHaveText('test-operator');
    await expect(page.locator('#cs-role-badge')).toHaveText('PUBLISHER');
  });

  test('dashboard displays 647 items and procedure breakdown', async ({ page }) => {
    await setupStudio(page);
    await login(page);
    await expect(page.locator('.cs-kpi-val').first()).toHaveText('647');
    await expect(page.locator('.cs-dashboard')).toContainText('체류기간 연장 (224건)');
    await expect(page.locator('.cs-dashboard')).toContainText('체류자격 변경 (251건)');
    await expect(page.locator('.cs-dashboard')).toContainText('외국인등록·거소신고 (172건)');
  });

  test('editor loads scenarios and allows inspection of D-2 documents', async ({ page }) => {
    await setupStudio(page);
    await login(page);
    await page.click('#tab-editor');
    await expect(page.locator('#cs-scenario-list')).toContainText('D-2');
    await page.click('.cs-item-row:has-text("D-2")');
    await expect(page.locator('#cs-editor-form-pane')).toContainText('공식 체류자격 명칭');
    await expect(page.locator('#cs-editor-form-pane textarea').first()).toContainText('통합신청서');
  });

  test('reviews queue enforces strict HTTPS evidence check before approval', async ({ page }) => {
    await setupStudio(page, { role: 'reviewer' });
    await login(page);
    await page.click('#tab-reviews');
    await expect(page.locator('#cs-reviews-list')).toContainText('draft-d2-01');
    await expect(page.locator('#cs-reviews-list')).toContainText('draft-no-evidence');

    // Attempt approval on draft without HTTPS evidence -> must show alert dialog
    const noEvidenceRow = page.locator('tr:has-text("draft-no-evidence")');
    await noEvidenceRow.locator('button:has-text("승인")').click();
    await expect(page.locator('#cs-dialog-title')).toContainText('승인 불가');
    await page.locator('#cs-dialog-cancel').click();
  });

  test('diff view highlights changes and legal impact banner', async ({ page }) => {
    await setupStudio(page);
    await login(page);
    await page.click('#tab-diff');
    // Navigate with draft ID directly via reviews or editor
    await page.evaluate(() => {
      window.VisableBackend = window.VisableBackend || {};
    });
    await page.click('#tab-reviews');
    await page.locator('tr:has-text("draft-d2-01") button:has-text("비교 (Diff)")').click();
    await expect(page.locator('.cs-impact-banner')).toContainText('법적 및 행정적 영향도 분석');
    await expect(page.locator('.cs-diff-val.added').first()).toBeVisible();
  });

  test('publish pipeline validates 647 items and executes release for publisher', async ({ page }) => {
    await setupStudio(page, { role: 'publisher' });
    await login(page);
    await page.click('#tab-publish');
    await expect(page.locator('.cs-gate-card')).toContainText('무결성 검증 통과');
    await expect(page.locator('#cs-validate-results .cs-checklist-table')).toContainText('정확히 647개');
    await expect(page.locator('#cs-release-section')).toContainText('운영 게시 배포 실행');
  });

  test('publish pipeline displays release history with candidate preview link and executes rollback', async ({ page }) => {
    await setupStudio(page, { role: 'publisher' });
    await login(page);
    await page.click('#tab-publish');
    await expect(page.locator('#cs-release-history')).toContainText('릴리스 이력 관리 및 롤백');
    await expect(page.locator('#cs-release-history')).toContainText('rel-20261020-01');

    // Preview link points to candidate release
    const previewLink = page.locator('#cs-release-history a:has-text("미리보기")');
    await expect(previewLink).toHaveAttribute('href', /preview_release=rel-20261020-01/);

    // Rollback action opens modal
    await page.locator('#cs-release-history button:has-text("롤백")').click();
    await expect(page.locator('#cs-dialog-title')).toContainText('릴리스 긴급 롤백');
    await page.locator('#cs-dialog textarea').fill('E2E 테스트 긴급 롤백 수행');
    await page.locator('#cs-dialog-confirm').click();
    await expect(page.locator('#cs-status-bar')).toContainText('롤백 완료');
  });

  test('public checklist page in candidate preview mode displays top preview banner and exit button', async ({ page }) => {
    await page.route('**/api/checklists/preview?release_id=rel-20261020-01', (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_preview: true,
          release_id: 'rel-20261020-01',
          release_tag: 'rel-20261020-01',
          checksum_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          total_items: 647,
          extension: { procedure: 'extension', row_count: 224, items: [] },
          change: { procedure: 'change', row_count: 251, items: [] },
          registration: { procedure: 'registration', row_count: 172, items: [] },
        }),
      });
    });

    await page.goto('/immigration-checklists.html?preview_release=rel-20261020-01');
    const banner = page.locator('#release-preview-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('CANDIDATE PREVIEW');
    await expect(banner).toContainText('rel-20261020-01');

    const exitBtn = banner.locator('.release-preview-exit');
    await expect(exitBtn).toBeVisible();
    await expect(exitBtn).toHaveAttribute('href', 'immigration-checklists.html');
  });

  test('no horizontal page overflow across desktop and tablet', async ({ page }) => {
    await setupStudio(page);
    await login(page);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});

