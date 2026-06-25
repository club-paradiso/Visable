#!/usr/bin/env node
/**
 * check_waymaker_navigator_dom.mjs — DOM smoke test for the Waymaker navigator UI
 * controller (assets/js/waymaker-navigator.js :: createNavigator).
 *
 * Uses jsdom to drive the guided intake -> packet -> AI-follow-up flow and assert
 * the load-bearing product guarantees:
 *   - opening the navigator shows guided navigation (a Start button), not a blank
 *     chat transcript;
 *   - the deterministic packet is fetched from /api/procedure-packet and the AI
 *     /api/ask path is NEVER invoked before the user opens the follow-up and
 *     submits a question;
 *   - the AI follow-up sends ONLY safe categorical context (no checklist, no
 *     personal identifiers);
 *   - a coverage-limited packet renders the warning and fabricates nothing;
 *   - the local checklist persists in localStorage only.
 *
 * Gracefully SKIPS (exit 0) if jsdom is not installed, so CI without jsdom still
 * passes. Install with `npm install` (jsdom is a devDependency).
 *
 * Run: node scripts/check_waymaker_navigator_dom.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);

let JSDOM;
try { ({ JSDOM } = require('jsdom')); }
catch (e) {
  console.log('• jsdom not installed — skipping DOM smoke test (run `npm install`). SKIP.');
  process.exit(0);
}

const records = JSON.parse(readFileSync(join(ROOT, 'visa_data.json'), 'utf8'));
let failures = 0, checks = 0;
function ok(cond, msg) { checks++; if (!cond) { failures++; console.error('  ✗ ' + msg); } }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- canned backend packets (deterministic; mirror real builder output) -----
function cannedPacket(status, procedure) {
  if (procedure === 'extension') {
    return {
      packetId: 'packet.' + status + '.extension', packetType: 'extension',
      statusCode: status, exactStatusCode: status, parentStatusCode: status,
      titleKo: '체류기간 연장허가', titleEn: 'Extension of Stay',
      userScenarioSummaryKo: '학사일정을 고려하여 체류기간을 부여합니다.',
      applicability: { summaryKo: '연장 안내', conditions: [], limitations: [] },
      timing: { sourceBacked: false, limitationKo: '기한은 확인 필요', triggerEventKo: '체류기간 만료 전' },
      documents: {
        commonDocs: [{ nameKo: '신청서', sourceBacked: true, sourceRefs: [{ sourceNameKo: '외국인체류 안내매뉴얼', versionDate: '2026.5', pageRange: 'pp. 43-44', evidenceLevel: 'source_confirmed' }], isOfficialForm: false }],
        requiredDocs: [{ nameKo: '재정입증 서류', sourceBacked: true, sourceRefs: [{ sourceNameKo: '외국인체류 안내매뉴얼', evidenceLevel: 'source_confirmed' }], isOfficialForm: false }],
        conditionalDocs: [{ nameKo: '수료증명서 (해당자)', sourceBacked: true, conditionKo: '해당자', sourceRefs: [], isOfficialForm: false }],
        additionalDocs: [], sourceBacked: true
      },
      fees: { items: [{ labelKo: '연장허가 수수료', amountKo: '60,000원', sourceBacked: false, sourceRefs: [] }], sourceBacked: false, limitationKo: '최종 확인 필요' },
      channels: { immigrationOfficeVisit: { availableKo: '관할 출입국·외국인관서 방문', sourceBacked: false }, limitationKo: 'HiKorea 확인', hikoreaReservation: { taskTypeKo: '체류기간 연장허가', noteKo: '확인', sourceBacked: false } },
      officeAndJurisdiction: { summaryKo: '관할 출입국·외국인관서', limitationKo: 'HiKorea/1345 확인' },
      riskFlags: [{ flagKo: '신청 시점 주의', detailKo: '만료 전 신청', severity: 'reminder' }],
      sourceLens: { overallLevel: 'source_confirmed', overallLabelKo: '공식근거 직접 확인', overallLabelEn: 'Confirmed in official source', sources: [{ sourceNameKo: '외국인체류 안내매뉴얼', versionDate: '2026.5', pageRange: 'pp. 43-44' }], finalAgencyDiscretionKo: '관할기관 최종심사 필요' },
      coverageSummary: { level: 'full', isLimited: false, hasDocuments: true },
      nextActions: ['준비 서류 목록을 확인하세요.', 'HiKorea 예약 가능 여부를 확인하세요.'],
      finalAgencyNoteKo: '이 패킷은 준비 안내이며 최종 판단은 관할 출입국·외국인관서 기준에 따릅니다.',
      finalAgencyNoteEn: 'This packet is preparation guidance only.',
      version: 'test'
    };
  }
  // coverage-limited
  return {
    packetId: 'packet.' + status + '.' + procedure, packetType: procedure,
    statusCode: status, exactStatusCode: status, titleKo: '절차', titleEn: 'Procedure',
    applicability: { summaryKo: '', conditions: [], limitations: ['확인되지 않음'] },
    timing: { sourceBacked: false, limitationKo: '확인 필요' },
    documents: { commonDocs: [], requiredDocs: [], conditionalDocs: [], additionalDocs: [], sourceBacked: false, limitationKo: '구조화되지 않음' },
    fees: { items: [], sourceBacked: false, limitationKo: '확인 필요' },
    channels: { limitationKo: 'HiKorea 확인' },
    officeAndJurisdiction: { summaryKo: '관할기관', limitationKo: 'HiKorea 확인' },
    riskFlags: [],
    sourceLens: { overallLevel: 'unavailable', overallLabelKo: '공식근거 확인 불가', overallLabelEn: 'No current source coverage', sources: [], finalAgencyDiscretionKo: '관할기관 최종심사 필요' },
    coverageSummary: { level: 'unavailable', isLimited: true, hasDocuments: false },
    nextActions: ['1345/HiKorea에서 확인하세요.'],
    finalAgencyNoteKo: '준비 안내', finalAgencyNoteEn: 'Preparation guidance.', version: 'test'
  };
}

async function run() {
  const dom = new JSDOM('<!doctype html><html lang="ko"><body><section id="root"></section></body></html>', { url: 'https://example.test/ai.html', pretendToBeVisual: true });
  const { window } = dom;
  // Only these globals are needed: the UMD picks up `window` as its `global`
  // (so it reads window.localStorage / window.navigator / window.open), while
  // bare `document` / `fetch` inside the controller resolve to Node globals.
  global.window = window;
  global.document = window.document;

  // load the module fresh against this window (UMD attaches to window)
  delete require.cache[require.resolve(join(ROOT, 'assets/js/waymaker-navigator.js'))];
  const WM = require(join(ROOT, 'assets/js/waymaker-navigator.js'));

  // --- instrument fetch + onAskFollowup ---
  let fetchUrls = [];
  global.fetch = window.fetch = (url, opts) => {
    fetchUrls.push(String(url));
    const u = new URL(String(url), 'https://example.test/');
    const status = u.searchParams.get('status'); const procedure = u.searchParams.get('procedure');
    return Promise.resolve({ ok: true, json: () => Promise.resolve(cannedPacket(status, procedure)) });
  };
  let askCalls = [];
  const onAskFollowup = (ctx, q) => { askCalls.push({ ctx, q }); return Promise.resolve('설명입니다.'); };
  let hikoreaOpened = [];
  const openHiKorea = (s, p, t) => { hikoreaOpened.push([s, p, t]); };

  const root = window.document.getElementById('root');
  const ctrl = WM.createNavigator({ root, apiBase: '', getRecords: () => Promise.resolve(records), onAskFollowup, openHiKorea });
  ctrl.mount();
  await sleep(20);

  // 1. intro shows a Start button (guided navigation, not blank chat)
  const startBtn = [...root.querySelectorAll('button')].find((b) => /내 상황 선택하기|Choose my situation/.test(b.textContent));
  ok(!!startBtn, 'intro shows Start button (guided navigation)');
  ok(askCalls.length === 0 && fetchUrls.length === 0, 'no network before intake starts');
  startBtn.click(); await sleep(5);

  // 2. language step -> pick Korean
  const koBtn = [...root.querySelectorAll('button')].find((b) => b.textContent.trim() === '한국어');
  ok(!!koBtn, 'language step shows 한국어'); koBtn.click(); await sleep(5);

  // 3. location -> In Korea
  const inKorea = [...root.querySelectorAll('button')].find((b) => /한국 내/.test(b.textContent));
  ok(!!inKorea, 'location step shows 한국 내'); inKorea.click(); await sleep(5);

  // 4. status -> search D-2
  const search = root.querySelector('.wm-search');
  ok(!!search, 'status step shows search input');
  search.value = 'D-2'; search.dispatchEvent(new window.Event('input')); await sleep(5);
  const d2row = [...root.querySelectorAll('.wm-status-row')].find((r) => /D-2\b/.test(r.textContent) && !/D-2-/.test(r.textContent));
  ok(!!d2row, 'D-2 appears in status results'); d2row.click(); await sleep(5);

  // 5. procedure -> extension
  const extRow = [...root.querySelectorAll('.wm-proc-row')].find((r) => /체류기간 연장/.test(r.textContent));
  ok(!!extRow, 'procedure step shows 체류기간 연장'); extRow.click(); await sleep(5);

  // 6. D-2 is materially ambiguous -> sub-status step. Choose "잘 모르겠어요".
  const dontKnow = [...root.querySelectorAll('.wm-status-row')].find((r) => /잘 모르겠어요/.test(r.textContent));
  ok(!!dontKnow, 'D-2 extension asks sub-status clarification'); dontKnow.click(); await sleep(30);

  // 7. packet rendered, deterministic, no /api/ask
  ok(fetchUrls.some((u) => /\/api\/procedure-packet\?/.test(u)), 'fetched /api/procedure-packet');
  ok(fetchUrls.every((u) => !/\/api\/ask/.test(u)), 'never fetched /api/ask during deterministic flow');
  ok(askCalls.length === 0, 'AI follow-up NOT called before user opens it');
  const packetTitle = root.querySelector('.wm-packet-title');
  ok(!!packetTitle && /체류기간 연장허가/.test(packetTitle.textContent), 'packet title rendered');
  ok([...root.querySelectorAll('.wm-next-list li')].length >= 1, 'next actions rendered');
  ok(!!root.querySelector('.wm-cov-badge'), 'source coverage badge rendered');

  // 8. checklist persists to localStorage only
  // expand documents accordion (open by default for non-limited), toggle a checkbox
  const docCheck = root.querySelector('.wm-doc-check');
  ok(!!docCheck, 'document checklist rendered');
  ok(!!docCheck.id && /wm-chk-/.test(docCheck.id), 'doc checkbox has id');
  docCheck.checked = true; docCheck.dispatchEvent(new window.Event('change', { bubbles: true })); await sleep(5);
  let storedKeys = [];
  for (let i = 0; i < window.localStorage.length; i++) storedKeys.push(window.localStorage.key(i));
  ok(storedKeys.some((k) => /paradiso_waymaker_checklist/.test(k)), 'checklist state persisted to localStorage only');

  // 9. HiKorea CTA
  const hk = [...root.querySelectorAll('button')].find((b) => /HiKorea 예약 경로 확인/.test(b.textContent));
  ok(!!hk, 'HiKorea CTA present'); hk.click(); await sleep(5);
  ok(hikoreaOpened.length === 1 && hikoreaOpened[0][0] === 'D-2', 'HiKorea handoff prefilled with status');

  // 10. AI follow-up: open, then submit -> /api/ask via onAskFollowup with safe ctx
  const aiToggle = [...root.querySelectorAll('button')].find((b) => /이 패킷에서 헷갈리는 점 묻기/.test(b.textContent));
  ok(!!aiToggle, 'AI follow-up CTA present (secondary)');
  aiToggle.click(); await sleep(5);
  ok(askCalls.length === 0, 'opening follow-up does not call /api/ask');
  const ta = root.querySelector('.wm-ai-input');
  ok(!!ta, 'AI follow-up input shown after opening');
  ta.value = '재정서류가 면제될 수 있나요? (passport 1234567)';
  const sendBtn = [...root.querySelectorAll('.wm-ai button')].find((b) => /질문하기|Ask/.test(b.textContent));
  ok(!!sendBtn, 'AI send button present'); sendBtn.click(); await sleep(10);
  ok(askCalls.length === 1, 'AI follow-up called only after submit');
  const ctx = askCalls[0].ctx;
  ok(ctx.statusCode === 'D-2' && ctx.procedureKey === 'extension', 'follow-up context carries status+procedure');
  ok(!('checklist' in ctx), 'follow-up context has no checklist');
  ok(JSON.stringify(ctx).indexOf('passport') === -1, 'follow-up context has no personal identifiers');

  // 11. coverage-limited journey: a fresh navigator, D-2 -> statusChange (the
  //     canned backend returns an 'unavailable' packet) must render the warning
  //     card and fabricate nothing.
  const root2 = window.document.createElement('section');
  window.document.body.appendChild(root2);
  const ctrl2 = WM.createNavigator({ root: root2, apiBase: '', getRecords: () => Promise.resolve(records), onAskFollowup, openHiKorea });
  ctrl2.mount(); await sleep(20);
  [...root2.querySelectorAll('button')].find((b) => /내 상황 선택하기|Choose my situation/.test(b.textContent)).click(); await sleep(5);  // start
  [...root2.querySelectorAll('button')].find((b) => b.textContent.trim() === '한국어').click(); await sleep(5);
  [...root2.querySelectorAll('button')].find((b) => /한국 내/.test(b.textContent)).click(); await sleep(5);
  const s2 = root2.querySelector('.wm-search'); s2.value = 'D-2'; s2.dispatchEvent(new window.Event('input')); await sleep(5);
  [...root2.querySelectorAll('.wm-status-row')].find((r) => /D-2\b/.test(r.textContent) && !/D-2-/.test(r.textContent)).click(); await sleep(5);
  const procRows = [...root2.querySelectorAll('.wm-proc-row')];
  const chgRow = procRows.find((r) => /체류자격 변경/.test(r.textContent));
  ok(!!chgRow, 'limited: 체류자격 변경 procedure offered' + (chgRow ? '' : ' [rows: ' + procRows.map((r) => r.textContent).join(' | ') + ']'));
  if (!chgRow) { console.log('  (procedure rows seen: ' + procRows.length + ')'); }
  (chgRow || procRows[0]).click(); await sleep(5);
  [...root2.querySelectorAll('.wm-status-row')].find((r) => /잘 모르겠어요/.test(r.textContent)).click(); await sleep(30);
  const warn = root2.querySelector('.wm-card-warn');
  ok(!!warn, 'coverage-limited packet renders the warning card');
  ok(/공식 근거가 충분히 구조화되어 있지 않습니다/.test(warn.textContent), 'warning shows the exact coverage-limited copy');
  ok([...root2.querySelectorAll('.wm-doc-row')].length === 0, 'coverage-limited packet fabricates no documents');
  ok(/HiKorea|1345/.test(warn.textContent), 'coverage-limited points to official channels');

  console.log('\n' + (failures === 0
    ? `✓ Waymaker navigator DOM smoke: all ${checks} checks passed.`
    : `✗ Waymaker navigator DOM smoke: ${failures}/${checks} checks FAILED.`));
  process.exit(failures === 0 ? 0 : 1);
}

run().catch((e) => { console.error('DOM smoke test crashed:', e); process.exit(1); });
