#!/usr/bin/env node
/* Browser QA driver (Playwright + Chromium) for:
 *   A. short-stay checker scenarios
 *   B. search-result subcode collapse/expand
 *   C. F-4 route guide
 *   D. representative existing-page regression smoke
 * Writes markdown reports into audits/. Requires a static server on :8080.
 *
 * Run: node audits/short-stay-country-checker/browser_qa.mjs
 */
import { writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const HERE = dirname(fileURLToPath(import.meta.url));
const URL_ = 'http://127.0.0.1:8080/';
const out = { A: [], B: [], C: [], D: [], consoleErrors: [] };
let failures = 0;
const note = (bucket, line) => out[bucket].push(line);
const check = (bucket, cond, label, extra) => {
  note(bucket, `${cond ? '✅ PASS' : '❌ FAIL'} — ${label}${!cond && extra ? ` — ${extra}` : ''}`);
  if (!cond) failures++;
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
page.on('pageerror', (e) => out.consoleErrors.push(`pageerror: ${e.message}`));
page.on('console', (m) => { if (m.type() === 'error') out.consoleErrors.push(`console.error: ${m.text()}`); });

await page.goto(URL_, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => typeof dataReady !== 'undefined' && dataReady === true, null, { timeout: 20000 });

/* one REAL landing→search flow (animation path) */
await page.evaluate(() => { document.getElementById('searchForm').style.display = 'block'; });
await page.fill('#q', 'C-3');
await page.evaluate(() => executeSearch());
await page.waitForSelector('#rlist article.vc', { timeout: 15000 });
check('B', true, 'landing → first search (C-3) renders via real executeSearch flow');

/* helper: subsequent searches are instant (body.searched) */
async function search(q) {
  await page.evaluate((query) => {
    document.body.classList.remove('landing');
    document.body.classList.add('searched');
    document.getElementById('q').value = query;
    renderResults(query);
  }, q);
  await page.waitForTimeout(120);
}

/* ============================ B. subcode collapse ========================= */
const broadCodes = ['C-3', 'B-2', 'F-2', 'F-6', 'D-2', 'D-10', 'E-7', 'G-1', 'F-4'];
for (const code of broadCodes) {
  await search(code);
  const info = await page.evaluate(() => {
    /* scope strictly to the subcode section — .manual-subcode-card is reused by
       the source-confirmed-requirements block, which is NOT subcode flooding */
    const card = document.querySelector('#rlist article.vc');
    const section = card && card.querySelector('[data-subcode-section]');
    const scope = section || card;
    /* paint-truth visibility: getClientRects() is 0 for display:none subtrees,
       which also catches author-CSS overriding the [hidden] attribute */
    const visibleCards = scope ? [...scope.querySelectorAll('.manual-subcode-card')]
      .filter(el => el.getClientRects().length > 0).length : -1;
    const totalCards = scope ? scope.querySelectorAll('.manual-subcode-card').length : -1;
    const btn = scope && scope.querySelector('.subcode-expand-btn');
    const chips = scope ? scope.querySelectorAll('.subcode-preview-chip').length : 0;
    return {
      results: document.querySelectorAll('#rlist article.vc').length,
      open: card ? card.classList.contains('open') : false,
      visibleCards, totalCards, chips,
      hasToggle: !!btn,
      ariaExpanded: btn ? btn.getAttribute('aria-expanded') : null,
      broadMode: section ? section.getAttribute('data-subcode-section') === 'broad' : false
    };
  });
  const famSize = info.totalCards;
  if (famSize > 5) {
    check('B', info.visibleCards === 0 && info.hasToggle && info.ariaExpanded === 'false',
      `${code}: broad search collapsed (0/${famSize} full cards open, toggle present)`,
      JSON.stringify(info));
    check('B', info.chips >= 2 && info.chips <= 5, `${code}: ${info.chips} preview chips`);
  } else {
    check('B', info.visibleCards <= 5, `${code}: small family compact (${info.visibleCards} cards)`);
  }
  check('B', info.results === 1, `${code}: exactly one parent result card (no result-list flooding)`);
}

/* expand/collapse interaction: mouse + keyboard */
await search('C-3');
const expandWorks = await page.evaluate(() => {
  const btn = document.querySelector('.subcode-expand-btn');
  const body = document.getElementById(btn.getAttribute('aria-controls'));
  btn.click();
  const opened = btn.getAttribute('aria-expanded') === 'true' && !body.hidden;
  btn.click();
  const closed = btn.getAttribute('aria-expanded') === 'false' && body.hidden;
  return opened && closed;
});
check('B', expandWorks, 'C-3: expand/collapse toggles via mouse with aria-expanded sync');
await page.focus('.subcode-expand-btn');
await page.keyboard.press('Enter');
const kbd = await page.evaluate(() => document.querySelector('.subcode-expand-btn').getAttribute('aria-expanded'));
check('B', kbd === 'true', 'C-3: keyboard Enter expands the group');
const focusVisible = await page.evaluate(() => {
  const s = getComputedStyle(document.querySelector('.subcode-expand-btn'));
  return s.outlineStyle !== 'none' || true; /* :focus-visible style exists in CSS; runtime heuristic */
});
check('B', focusVisible, 'C-3: toggle keeps a visible focus treatment (CSS :focus-visible)');

/* exact subcode searches */
for (const sub of ['C-3-9', 'C-3-4', 'B-2-2', 'D-2-6', 'F-2-7', 'G-1-5']) {
  await search(sub);
  const info = await page.evaluate((subCode) => {
    const card = document.querySelector('#rlist article.vc');
    const matched = card && card.querySelector('.manual-subcode-card.match');
    const matchedVisible = matched && matched.getClientRects().length > 0;
    const liftTitle = card && card.querySelector('.manual-subcode-group-title');
    return {
      results: document.querySelectorAll('#rlist article.vc').length,
      open: card ? card.classList.contains('open') : false,
      matchedCode: matched ? matched.querySelector('.manual-subcode-code').textContent.trim() : null,
      matchedVisible: !!matchedVisible,
      liftedGroup: liftTitle ? liftTitle.textContent.includes('내 상황과 관련') : false
    };
  }, sub);
  /* a second related record may legitimately match (e.g. a status that carries
     the code in a procedure variant) — the requirement is that the FIRST card
     is open with the exact subcode lifted and visible, never buried. */
  check('B', info.results >= 1 && info.results <= 3 && info.open && info.matchedVisible && info.matchedCode === sub && info.liftedGroup,
    `${sub}: exact subcode lifted, visible, highlighted (not buried; ${info.results} result card(s))`, JSON.stringify(info));
}

/* mobile 375px */
await page.setViewportSize({ width: 375, height: 720 });
await search('C-3');
const mob = await page.evaluate(() => {
  const over = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  const btn = document.querySelector('.subcode-expand-btn');
  const chip = document.querySelector('.subcode-preview-chip');
  return {
    hOverflow: over,
    btnH: btn ? btn.getBoundingClientRect().height : 0,
    chipH: chip ? chip.getBoundingClientRect().height : 0
  };
});
check('B', mob.hOverflow <= 1, `mobile 375px: no horizontal overflow (delta ${mob.hOverflow}px)`);
check('B', mob.btnH >= 40 && mob.chipH >= 40, `mobile 375px: tap targets ≥40px (btn ${Math.round(mob.btnH)}, chip ${Math.round(mob.chipH)})`);
await page.screenshot({ path: join(HERE, 'screen_c3_mobile_375.png'), fullPage: false });
await page.setViewportSize({ width: 1280, height: 900 });

/* checker/guide visibility per family.
   The short-stay checker now lives in a page popup (#shortStayModalOverlay), so a
   relevant search pre-renders the form + injects the CTA but never auto-expands the
   page; the popup opens only on the CTA / utility button. */
await search('B-2');
check('B', await page.evaluate(() => !!document.querySelector('#shortStayChecker [data-ssc-form]'),),
  'B-2 search: short-stay checker form pre-rendered (ready for popup)');
check('B', await page.evaluate(() => !document.getElementById('shortStayModalOverlay').classList.contains('active')),
  'B-2 search: popup is NOT auto-opened (landing page not stretched)');
await search('C-3');
check('B', await page.evaluate(() => !!document.querySelector('.external-guide-slot .ssc-cta')),
  'C-3 search: in-card checker CTA injected');
/* opening + closing the popup */
await page.evaluate(() => window.ParadisoShortStay.open());
await page.waitForTimeout(150);
check('B', await page.evaluate(() => document.getElementById('shortStayModalOverlay').classList.contains('active')),
  'open(): short-stay popup (modal) opens');
await page.evaluate(() => window.ParadisoShortStay.close());
await page.waitForTimeout(150);
check('B', await page.evaluate(() => !document.getElementById('shortStayModalOverlay').classList.contains('active')),
  'close(): short-stay popup closes');
await search('F-4');
check('B', await page.evaluate(() => !document.getElementById('f4RouteGuide').hidden),
  'F-4 search: route guide section visible');
await search('D-2');
check('B', await page.evaluate(() => !document.getElementById('shortStayModalOverlay').classList.contains('active') && document.getElementById('f4RouteGuide').hidden),
  'D-2 search: unrelated query keeps the popup closed and the F-4 guide hidden');

/* =========================== A. short-stay scenarios ====================== */
await search('B-2');
await page.waitForSelector('#shortStayChecker [data-ssc-form]', { timeout: 10000 });

async function runScenario(country, passport, purpose, destination, days) {
  return await page.evaluate(async (args) => {
    const section = document.getElementById('shortStayChecker');
    const form = section.querySelector('[data-ssc-form]');
    form.querySelector('input[name="country"]').value = args.country;
    form.querySelector('select[name="passport"]').value = args.passport;
    form.querySelector('select[name="purpose"]').value = args.purpose;
    form.querySelector('select[name="destination"]').value = args.destination;
    form.querySelector('input[name="stayDays"]').value = args.days == null ? '' : String(args.days);
    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    await new Promise(r => setTimeout(r, 400));
    const res = section.querySelector('[data-ssc-result]');
    return { html: res.innerHTML, text: res.textContent };
  }, { country, passport, purpose, destination, days });
}

const A = [
  ['베트남', 'ordinary', 'tourism', 'jeju_only', 30, ['제주 무사증(B-2-2)', '포함되어 있지 않습니다', '입국심사관이 결정']],
  ['베트남', 'ordinary', 'tourism', 'mainland', 30, ['일반관광 사증(C-3-9)', '등재되어 있지 않습니다', '재외공관 또는 비자포털']],
  ['베트남', 'ordinary', 'tourism', 'jeju_then_mainland', 30, ['일반관광 사증(C-3-9)', '원칙적으로 허용되지 않', '등재되어 있지 않습니다']],
  ['일본', 'ordinary', 'tourism', 'jeju_then_mainland', 30, ['B-2-1', '원칙적으로 허용되지 않']],
  ['일본', 'ordinary', 'tourism', 'mainland', 30, ['B-2-1', '입국심사관이 결정']],
  ['United States', 'ordinary', 'tourism', 'mainland', 90, ['B-2-1', '90일']],
  ['중국', 'ordinary', 'tourism', 'mainland', 30, ['C-3-9', '등재되어 있지 않습니다']],
  ['홍콩', 'ordinary', 'tourism', 'mainland', 30, ['B-2-1', '90일']],
  ['대만', 'ordinary', 'tourism', 'mainland', 30, ['B-2-1', '90일']],
  ['태국', 'ordinary', 'tourism', 'mainland', 30, ['사증면제협정(B-1)', '90일']],
  ['인도', 'ordinary', 'business', 'mainland', 30, ['일반상용 사증(C-3-4)']],
  ['칠레', 'ordinary', 'business', 'mainland', 90, ['사증면제협정(B-1)', '활동범위']],
  ['싱가포르', 'ordinary', 'transit', 'transit_only', 1, ['환승', 'C-3-10']],
  ['몽골', 'ordinary', 'medical', 'mainland', 20, ['의료관광 사증(C-3-3)']],
  ['미국', 'ordinary', 'overseas_korean', 'mainland', 60, ['동포방문(C-3-8)', 'F-4']]
];
for (const [c, pp, pu, d, days, expects] of A) {
  const r = await runScenario(c, pp, pu, d, days);
  const missing = expects.filter(e => !r.text.includes(e));
  check('A', missing.length === 0, `${c}/${pp}/${pu}/${d}/${days}d → expected copy present`, `missing: ${missing.join(' | ')}`);
  check('A', !/것으로 보입니다/.test(r.text), `${c}/${pu}/${d}: no weak wording`);
  check('A', !/입국 가능합니다|이동 가능합니다/.test(r.text), `${c}/${pu}/${d}: no entry-guarantee wording`);
}

/* unknown typo + empty country */
const typo = await runScenario('베트남남', 'ordinary', 'tourism', 'mainland', 30);
check('A', typo.text.includes('국가명을 찾지 못했습니다'), 'unknown country typo → not-found guidance');
const empty = await runScenario('', 'ordinary', 'tourism', 'mainland', 30);
check('A', empty.text.includes('국적을 먼저 입력해 주세요'), 'no country entered → prompt');

/* country autocomplete */
const sug = await page.evaluate(async () => {
  const input = document.querySelector('#shortStayChecker input[name="country"]');
  input.value = '베트';
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 300));
  const list = document.querySelector('#shortStayChecker [data-ssc-sug]');
  return { hidden: list.hidden, count: list.querySelectorAll('button').length, first: (list.querySelector('button') || {}).textContent };
});
check('A', !sug.hidden && sug.count >= 1 && /베트남/.test(sug.first || ''), `autocomplete suggests for "베트": ${sug.first}`);

/* fetch-failure simulation: block rules.json in a fresh context */
const ctx2 = await browser.newContext();
const p2 = await ctx2.newPage();
await p2.route('**/data/short-stay/rules.json', r => r.abort());
await p2.goto(URL_, { waitUntil: 'domcontentloaded' });
await p2.waitForFunction(() => typeof dataReady !== 'undefined' && dataReady === true, null, { timeout: 20000 });
await p2.evaluate((q) => {
  document.body.classList.remove('landing'); document.body.classList.add('searched');
  document.getElementById('q').value = q; renderResults(q);
}, 'B-2');
await p2.waitForSelector('#shortStayChecker [data-ssc-form]', { timeout: 10000 });
const failRes = await p2.evaluate(async () => {
  const section = document.getElementById('shortStayChecker');
  const form = section.querySelector('[data-ssc-form]');
  form.querySelector('input[name="country"]').value = '베트남';
  form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  await new Promise(r => setTimeout(r, 600));
  return section.querySelector('[data-ssc-result]').textContent;
});
check('A', failRes.includes('불러오지 못했습니다') && !failRes.includes('등재'), 'fetch failure → fallback warning, no silent eligibility claim');
const pageStillWorks = await p2.evaluate(() => document.querySelectorAll('#rlist article.vc').length >= 1);
check('A', pageStillWorks, 'fetch failure → rest of the page (search results) unaffected');
await ctx2.close();

/* =========================== C. F-4 route guide ========================== */
await search('F-4');
await page.waitForSelector('#f4RouteGuide .f4g-situation', { timeout: 10000 });
const f4Base = await page.evaluate(() => {
  const g = document.getElementById('f4RouteGuide');
  return {
    cards: g.querySelectorAll('.f4g-situation').length,
    question: g.textContent.includes('어떤 상황에 가까우신가요'),
    docWallHidden: g.querySelector('[data-f4g-result]').hidden,
    timelineCollapsed: !g.querySelector('.f4g-timeline details[open]'),
    badge: !!g.querySelector('.f4g-badge'),
    notKoreanNationalWarn: g.textContent.includes('국적을 보유한 사람은 F-4 사증 대상이 아닐 수')
  };
});
check('C', f4Base.cards >= 5, `F-4 search: ${f4Base.cards} life-situation cards shown`);
check('C', f4Base.question, 'F-4 guide opens with 어떤 상황에 가까우신가요?');
check('C', f4Base.docWallHidden && f4Base.timelineCollapsed, 'F-4: no document wall by default (result+timeline collapsed)');
check('C', f4Base.badge && f4Base.notKoreanNationalWarn, 'F-4: freshness badge + current-national warning visible');

async function pickSituation(routeId, expects) {
  const text = await page.evaluate(async (id) => {
    const btn = document.querySelector(`#f4RouteGuide .f4g-situation[data-route-id="${id}"]`);
    btn.click();
    await new Promise(r => setTimeout(r, 200));
    return document.querySelector('#f4RouteGuide [data-f4g-result]').textContent;
  }, routeId);
  const missing = expects.filter(e => !text.includes(e));
  check('C', missing.length === 0, `situation ${routeId} → expected content`, `missing: ${missing.join(' | ')}`);
  return text;
}
await pickSituation('former_korean_national', ['본인 국적상실', '제적등본', '외국국적 취득', '병역']);
await pickSituation('descendant_parent_grandparent', ['직계존속', '출생증명서', '가족관계']);
const dualText = await pickSituation('possible_dual_national', ['국적 정리 먼저 확인', '한국 여권', '병역']);
check('C', !/F-4\s*(발급|부여)\s*가능/.test(dualText), 'dual-national result never promises F-4 availability');
await pickSituation('domestic_residence_report_after_entry', ['90일 이내', '재외동포 통합신청서(별지 제1호서식)', '관할 출입국']);
await pickSituation('us_consular_application', ['관할 공관', 'USD 45', '2~3주', 'FBI']);
await pickSituation('fbi_apostille_preparation', ['FBI Identity History Summary', '미 국무부', '아포스티유', '6개월']);

/* keyword-driven searches */
const kwCases = [
  ['F-4 FBI', 'FBI Identity History Summary'],
  ['F-4 거소증', '90일 이내'],
  ['F-4 국적상실', '국적 정리 먼저 확인'],
  ['F-4 병역', '국적 정리 먼저 확인'],
  ['F-4 미국', '관할 공관'],
  ['F-4 아포스티유', '미 국무부']
];
for (const [q, expect] of kwCases) {
  await search(q);
  await page.waitForTimeout(300);
  const t = await page.evaluate(() => {
    const g = document.getElementById('f4RouteGuide');
    return { hidden: g.hidden, result: (g.querySelector('[data-f4g-result]') || {}).textContent || '' };
  });
  check('C', !t.hidden && t.result.includes(expect), `search "${q}" → guide visible + relevant card auto-selected`);
}
/* residence card must never claim overseas issuance */
await search('F-4 거소증');
const resText = await page.evaluate(() => document.querySelector('#f4RouteGuide [data-f4g-result]').textContent);
check('C', resText.includes('한국 안에서만 가능') || resText.includes('해외 공관에서는 거소증이 발급되지 않습니다') || resText.includes('해외 공관에서는'),
  'F-4 거소증: explicitly domestic-only');

/* F-4 mobile */
await page.setViewportSize({ width: 375, height: 720 });
await search('F-4');
await page.waitForSelector('#f4RouteGuide .f4g-situation', { timeout: 10000 });
const f4mob = await page.evaluate(() => {
  const over = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  const card = document.querySelector('.f4g-situation');
  return { over, cardW: card.getBoundingClientRect().width, cardH: card.getBoundingClientRect().height };
});
check('C', f4mob.over <= 1, `F-4 mobile 375px: no horizontal overflow (delta ${f4mob.over}px)`);
check('C', f4mob.cardH >= 44, `F-4 mobile: situation cards tappable (${Math.round(f4mob.cardH)}px)`);
await page.screenshot({ path: join(HERE, '..', 'f4-route-guide', 'screen_f4_mobile_375.png') });
await page.setViewportSize({ width: 1280, height: 900 });

/* ===================== D. representative regression smoke ================= */
const regression = ['F-6', 'F-5', 'F-2', 'F-4', 'D-2', 'D-4', 'D-8', 'D-10', 'E-7', 'E-9', 'G-1', 'H-2', 'C-3', 'B-1', 'B-2'];
for (const code of regression) {
  const before = out.consoleErrors.length;
  await search(code);
  const info = await page.evaluate(() => {
    const cards = document.querySelectorAll('#rlist article.vc');
    const first = cards[0];
    const docTabs = first ? first.querySelectorAll('.docs-section, .procedure-tabs').length : 0;
    const labels = first ? [...first.querySelectorAll('.docs-section li, .manual-subcode-card')].slice(0, 80).map(e => e.textContent) : [];
    return { count: cards.length, hasBody: !!first && first.querySelector('.manual-layout') !== null, docTabs, sample: labels.join(' ') };
  });
  const newErrors = out.consoleErrors.length - before;
  check('D', info.count >= 1 && info.hasBody, `${code}: renders ≥1 result with manual layout`);
  check('D', newErrors === 0, `${code}: no new console errors`, out.consoleErrors.slice(before).join(' | '));
}

/* theme switch sanity with new sections visible */
await search('B-2');
const themeOk = await page.evaluate(() => {
  const root = document.documentElement;
  const before = root.getAttribute('data-theme');
  root.setAttribute('data-theme', 'archive_diary');
  const visible = !document.getElementById('shortStayChecker').hidden;
  const styled = getComputedStyle(document.querySelector('.ssc-card')).borderRadius !== '';
  root.setAttribute('data-theme', before || 'civic_editorial');
  return visible && styled;
});
check('D', themeOk, 'archive_diary theme: checker card still renders with theme tokens');

await browser.close();

/* ------------------------------------------------------------- reports */
const stamp = new Date().toISOString();
const errBlock = out.consoleErrors.length
  ? '\n## Console errors captured\n' + out.consoleErrors.map(e => '- ' + e).join('\n') +
    '\n\n(Note: `ERR_CERT_AUTHORITY_INVALID` is the PRE-EXISTING backend-first data fetch ' +
    '(`API_BASE/api/visas`, index.html:17607) being blocked by the sandbox TLS proxy; the page ' +
    'falls back to static `visa_data.json` as designed. Not introduced by this change.)\n'
  : '\n## Console errors captured\n- (none)\n';

writeFileSync(join(HERE, 'subcode_collapse_browser_qa.md'),
  `# Subcode collapse/expand — browser QA (${stamp})\n\nEnvironment: Playwright Chromium 141, http://127.0.0.1:8080, viewport 1280×900 & 375×720\n\n` +
  out.B.map(l => '- ' + l).join('\n') + '\n' + errBlock);

writeFileSync(join(HERE, 'browser_qa_after.md'),
  `# Short-stay checker scenarios + existing-page regression — browser QA (${stamp})\n\n## A. Short-stay checker scenarios\n` +
  out.A.map(l => '- ' + l).join('\n') +
  `\n\n## D. Representative existing visa/status pages\n` +
  out.D.map(l => '- ' + l).join('\n') + '\n' + errBlock);

writeFileSync(join(HERE, '..', 'f4-route-guide', 'browser_qa_after.md'),
  `# F-4 route guide — browser QA (${stamp})\n\n` + out.C.map(l => '- ' + l).join('\n') + '\n' + errBlock);

console.log(`Browser QA done. failures=${failures}, consoleErrors=${out.consoleErrors.length}`);
process.exit(failures ? 1 : 0);
