import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { webkit } from '@playwright/test';

const ROOT = process.cwd();
const PORT = Number(process.env.MOBILE_WEBKIT_QA_PORT || 4174);
const OUT = path.join(ROOT, 'artifacts', 'mobile-webkit-qa');
const safariUA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';
const profiles = [
  { name: 'iphone-se', width: 375, height: 667 },
  { name: 'iphone-15', width: 390, height: 844 },
  { name: 'iphone-pro', width: 393, height: 852 },
  { name: 'iphone-pro-max', width: 430, height: 932 },
  { name: 'iphone-landscape', width: 844, height: 390 },
];
const criticalSelectors = [
  '#civicLanding', '.cs-nav', '.cs-lang', '.cs-lang-dialog', '.cs-hero', '.cs-searchbar', '.cs-routes', '.cs-tool-grid', '.cs-source-strip', '#civicManualResults',
  '.top-ctrls', '.hero-container', '.p-hero-title', '.p-gateway', '.p-gw-search',
  '.p-gw-card', '.p-gw-util', '.p-gw-newhome', '.hero-actions', '.sbar', '#q',
  '.results-area', '.rlist', '.us-layer', '.us-interpret', '.us-ai', '.ai-fab',
  '#statusGuidance', '.sg-interp', '.sg-quick', '.sg-fee', '.sg-local', '.sg-disclaimer', '.sg-question', '.sg-answer', '.sg-docs', '.sg-next', '.sg-evidence',
];
// Post-search guidance flows (status-guidance.js) exercised on the iphone-15
// profile with real searches: the sprint's four mobile journeys.
const guidanceFlows = [
  { name: 'f1-extension', query: 'F-1 연장', picks: ['marriage_family', 'marriage_migrant', 'first', 'childcare'], expectKind: 'resolved', expectTitle: 'F-1-5' },
  { name: 'e7-extension', query: 'E-7 연장', picks: ['unsure'], expectKind: 'unresolved' },
  { name: 'e9-hotel', query: 'E-9 호텔', picks: ['extension'], expectKind: 'resolved', expectTitle: 'E-9-5' },
  { name: 'd2-extension', query: 'D-2 연장', picks: [], expectKind: 'resolved', expectTitle: 'D-2' },
  // procedure-first search: status-independent procedures answer without a status
  { name: 'card-reissue', query: '외국인등록증 재발급', picks: [], expectKind: 'procedure', expectTitle: '외국인등록증 재발급', expectSelectors: ['.sg-fee', '.sg-doc-form', '.sg-doc-group-required'], forbidText: '체류자격을 찾지 못했어요' },
  { name: 'quick-answer', query: '외국인등록증 재발급하려면 뭐 필요해?', picks: [], expectKind: 'procedure', expectSelectors: ['.sg-quick[data-sg-quick-mode="answer"]', '#sgQuickSummary', '[data-sg-action="toggle-full"]'], forbidText: '체류자격을 찾지 못했어요' },
  { name: 'address-report', query: '체류지 변경 신고', picks: [], expectKind: 'procedure', expectTitle: '체류지 변경 신고', expectSelectors: ['.sg-doc-alts'] },
  { name: 'extension-status-prompt', query: '체류기간 연장', picks: ['study', 'D-2'], expectKind: 'resolved', expectTitle: 'D-2' },
];
const mime = new Map([
  ['.html', 'text/html; charset=utf-8'], ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'], ['.mjs', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'], ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'], ['.jpg', 'image/jpeg'], ['.jpeg', 'image/jpeg'],
  ['.webp', 'image/webp'], ['.woff2', 'font/woff2'],
]);

function resolvePath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split('?')[0]);
  const relative = decoded === '/' ? 'index.html' : decoded.replace(/^\/+/, '');
  const resolved = path.resolve(ROOT, relative);
  if (!resolved.startsWith(`${ROOT}${path.sep}`) && resolved !== path.join(ROOT, 'index.html')) return null;
  return resolved;
}

const server = http.createServer(async (req, res) => {
  try {
    const file = resolvePath(req.url || '/');
    if (!file) throw new Error('invalid path');
    const body = await fs.readFile(file);
    res.statusCode = 200;
    res.setHeader('Content-Type', mime.get(path.extname(file).toLowerCase()) || 'application/octet-stream');
    res.setHeader('Cache-Control', 'no-store');
    res.end(body);
  } catch {
    res.statusCode = 404;
    res.end('not found');
  }
});

await fs.mkdir(OUT, { recursive: true });
await new Promise((resolve) => server.listen(PORT, '127.0.0.1', resolve));
const browser = await webkit.launch({ headless: true });
const report = { generatedAt: new Date().toISOString(), engine: 'webkit', profiles: [], failures: [] };

// WebKit cannot screenshot pages taller than 32767px; a mobile results page that
// tall is itself a defect, so record it as a failure and fall back to a viewport shot.
const MAX_PAGE_HEIGHT = 30000;
async function fullPageShot(page, file, failures) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  if (height > MAX_PAGE_HEIGHT) failures.push(`page is ${height}px tall (mobile results must stay under ${MAX_PAGE_HEIGHT}px)`);
  await page.screenshot({ path: file, fullPage: height <= MAX_PAGE_HEIGHT });
}

async function inspect(page, profile, state) {
  const data = await page.evaluate(({ criticalSelectors, profile, state }) => {
    const visible = (el) => {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity || 1) > 0 && r.width > 0 && r.height > 0;
    };
    const criticalOverflow = criticalSelectors.flatMap((selector) => [...document.querySelectorAll(selector)]
      .filter(visible)
      .map((el) => ({ selector, rect: el.getBoundingClientRect() }))
      .filter(({ rect }) => rect.left < -2 || rect.right > innerWidth + 2 || rect.width > innerWidth + 2)
      .map(({ selector, rect }) => ({ selector, left: rect.left, right: rect.right, width: rect.width })));
    const smallInputs = [...document.querySelectorAll('input, textarea, select')]
      .filter(visible)
      .map((el) => ({ tag: el.tagName.toLowerCase(), type: el.getAttribute('type') || '', fontSize: parseFloat(getComputedStyle(el).fontSize) || 0 }))
      .filter((entry) => entry.fontSize > 0 && entry.fontSize < 16);
    const touchTargets = [...document.querySelectorAll('.cs-languages button, .cs-lang, .cs-lang-option, .cs-lang-close, #statusGuidance .sg-chip, #statusGuidance [data-sg-action="toggle-full"], .cs-examples button, .cs-searchbar button, .cs-routes button, .cs-tool-grid > *, .top-ctrls button, .top-ctrls [role="button"], .hero-actions .ha, .p-gw-search, .p-gw-card, .p-gw-util, .p-gw-newhome, .sbar button, .sbar [role="button"], #statusGuidance .sg-option, #statusGuidance .sg-btn, #statusGuidance .sg-candidate, #statusGuidance .sg-next a, #statusGuidance .sg-evidence-actions a')]
      .filter(visible)
      .map((el) => el.getBoundingClientRect())
      .filter((r) => r.width < 40 || r.height < 40)
      .map((r) => ({ width: r.width, height: r.height }));
    const viewport = document.querySelector('meta[name="viewport"]')?.getAttribute('content') || '';
    return {
      state,
      viewport,
      innerWidth,
      innerHeight,
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body?.scrollWidth || 0,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 2 || (document.body?.scrollWidth || 0) > innerWidth + 2,
      mobileAuthorityLoaded: Boolean(document.getElementById('visable-mobile-authority-styles')),
      mobileHardeningLoaded: Boolean(document.getElementById('visable-mobile-qa-hardening-styles')),
      landscapeCompatLoaded: Boolean(document.getElementById('visable-mobile-landscape-compat')),
      criticalOverflow,
      smallInputs,
      undersizedTargets: touchTargets,
      expectedLandscapeCompat: profile.name === 'iphone-landscape',
    };
  }, { criticalSelectors, profile, state });

  const failures = [];
  if (/maximum-scale\s*=\s*1|user-scalable\s*=\s*no/i.test(data.viewport)) failures.push('viewport blocks pinch zoom');
  if (!data.mobileAuthorityLoaded || !data.mobileHardeningLoaded) failures.push('mobile style loader is incomplete');
  if (data.expectedLandscapeCompat && !data.landscapeCompatLoaded) failures.push('landscape compatibility style was not injected');
  if (data.horizontalOverflow) failures.push(`horizontal overflow (${data.documentScrollWidth}px > ${data.innerWidth}px)`);
  if (data.criticalOverflow.length) failures.push(`${data.criticalOverflow.length} critical element(s) leave the viewport`);
  if (data.smallInputs.length) failures.push(`${data.smallInputs.length} visible form control(s) use <16px text`);
  if (data.undersizedTargets.length) failures.push(`${data.undersizedTargets.length} critical touch target(s) are <40px`);
  return { ...data, failures };
}

try {
  for (const profile of profiles) {
    const context = await browser.newContext({
      viewport: { width: profile.width, height: profile.height },
      deviceScaleFactor: 1,
      isMobile: true,
      hasTouch: true,
      userAgent: safariUA,
    });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(String(error.message || error)));
    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(900);
    const profileReport = { ...profile, pageErrors, states: [] };
    const states = profile.name === 'iphone-15' ? ['landing', 'searching', 'searched'] : ['landing'];
    for (const state of states) {
      await page.evaluate((nextState) => {
        document.body.classList.remove('landing', 'searched', 'searching');
        document.body.classList.add(nextState === 'searching' ? 'landing' : nextState);
        if (nextState === 'searching') document.querySelector('#civicQuery')?.focus();
      }, state);
      await page.waitForTimeout(120);
      const stateReport = await inspect(page, profile, state);
      profileReport.states.push(stateReport);
      const suffix = state === 'landing' ? '' : `-${state}`;
      await page.screenshot({ path: path.join(OUT, `${profile.name}${suffix}.png`), fullPage: true });
      for (const failure of stateReport.failures) report.failures.push(`${profile.name}/${state}: ${failure}`);
    }
    if (profile.name === 'iphone-15') {
      for (const flow of guidanceFlows) {
        const flowReport = { name: flow.name, query: flow.query, failures: [] };
        try {
          await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
          await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('#civicQuery'); } catch { return false; } }, null, { timeout: 30000 });
          await page.fill('#civicQuery', flow.query);
          await page.press('#civicQuery', 'Enter');
          await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
          for (const pick of flow.picks) {
            await page.locator(`#statusGuidance [data-sg-action="answer"][data-sg-value="${pick}"]`).first().tap();
            await page.waitForTimeout(150);
          }
          await page.waitForTimeout(300);
          const kind = await page.getAttribute('#statusGuidance', 'data-sg-kind');
          if (kind !== flow.expectKind) flowReport.failures.push(`expected ${flow.expectKind}, got ${kind}`);
          if (flow.expectTitle) {
            const title = (await page.locator('#sgAnswerTitle').textContent().catch(() => '')) || '';
            if (!title.includes(flow.expectTitle)) flowReport.failures.push(`answer title "${title.trim()}" lacks ${flow.expectTitle}`);
          }
          for (const selector of flow.expectSelectors || []) {
            const shown = await page.evaluate((sel) => { const el = document.querySelector(sel); if (!el) return false; const r = el.getBoundingClientRect(); return getComputedStyle(el).display !== 'none' && r.width > 0 && r.height > 0; }, selector);
            if (!shown) flowReport.failures.push(`expected ${selector} to be visible`);
          }
          if (flow.forbidText) {
            const text = (await page.locator('#statusGuidance').textContent().catch(() => '')) || '';
            if (text.includes(flow.forbidText)) flowReport.failures.push(`guidance still says "${flow.forbidText}"`);
          }
          const fabShown = await page.evaluate(() => { const f = document.querySelector('.ai-fab'); return !!f && getComputedStyle(f).display !== 'none'; });
          if (fabShown) flowReport.failures.push('AI FAB still shown over the searched state');
          const stateReport = await inspect(page, profile, `guidance:${flow.name}`);
          profileReport.states.push(stateReport);
          flowReport.failures.push(...stateReport.failures);
          await fullPageShot(page, path.join(OUT, `${profile.name}-guidance-${flow.name}.png`), flowReport.failures);
        } catch (error) {
          flowReport.failures.push(`flow error: ${String(error.message || error)}`);
        }
        profileReport.guidanceFlows = profileReport.guidanceFlows || [];
        profileReport.guidanceFlows.push(flowReport);
        for (const failure of flowReport.failures) report.failures.push(`${profile.name}/guidance:${flow.name}: ${failure}`);
      }
    }
    if (profile.name === 'iphone-15') {
      // Global language control: bottom sheet on mobile, 15 native names, Arabic → RTL, control still present after a search.
      const langReport = { name: 'language-sheet', failures: [] };
      try {
        await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForFunction(() => { try { return typeof VISA_DATA !== 'undefined' && VISA_DATA.length > 10 && !!document.querySelector('[data-cs-lang-open]'); } catch { return false; } }, null, { timeout: 30000 });
        await page.locator('[data-cs-lang-open]:visible').first().tap();
        await page.waitForSelector('#csLangDialog[open]', { timeout: 5000 });
        const sheet = await page.evaluate(() => { const d = document.querySelector('#csLangDialog[open]'); const r = d.getBoundingClientRect(); return { count: d.querySelectorAll('.cs-lang-option').length, width: r.width, bottom: r.bottom, innerWidth, innerHeight }; });
        if (sheet.count !== 15) langReport.failures.push(`expected 15 languages, got ${sheet.count}`);
        if (sheet.width < sheet.innerWidth - 2 || sheet.bottom < sheet.innerHeight - 2) langReport.failures.push(`language dialog is not a bottom sheet (${Math.round(sheet.width)}x, bottom ${Math.round(sheet.bottom)} of ${sheet.innerHeight})`);
        const sheetState = await inspect(page, profile, 'language-sheet');
        profileReport.states.push(sheetState);
        langReport.failures.push(...sheetState.failures);
        await page.screenshot({ path: path.join(OUT, `${profile.name}-language-sheet.png`), fullPage: false });
        await page.locator('#csLangDialog .cs-lang-option[data-lang="ar"]').tap();
        await page.waitForTimeout(400);
        const dir = await page.evaluate(() => document.documentElement.dir);
        if (dir !== 'rtl') langReport.failures.push(`Arabic did not switch the document to RTL (dir=${dir})`);
        const rtlState = await inspect(page, profile, 'landing-rtl');
        profileReport.states.push(rtlState);
        langReport.failures.push(...rtlState.failures);
        await fullPageShot(page, path.join(OUT, `${profile.name}-landing-rtl.png`), langReport.failures);
        await page.fill('#civicQuery', '외국인등록증 재발급');
        await page.press('#civicQuery', 'Enter');
        await page.waitForSelector('#statusGuidance[data-sg-kind]', { timeout: 20000 });
        const searchedLang = await page.evaluate(() => { const b = [...document.querySelectorAll('[data-cs-lang-open]')].find((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }); return { present: !!b, dir: document.documentElement.dir }; });
        if (!searchedLang.present) langReport.failures.push('language control missing from the searched header');
        if (searchedLang.dir !== 'rtl') langReport.failures.push('RTL lost after the search');
        const searchedState = await inspect(page, profile, 'searched-rtl');
        profileReport.states.push(searchedState);
        langReport.failures.push(...searchedState.failures);
        await fullPageShot(page, path.join(OUT, `${profile.name}-searched-rtl.png`), langReport.failures);
      } catch (error) {
        langReport.failures.push(`flow error: ${String(error.message || error)}`);
      }
      profileReport.guidanceFlows = profileReport.guidanceFlows || [];
      profileReport.guidanceFlows.push(langReport);
      for (const failure of langReport.failures) report.failures.push(`${profile.name}/language-sheet: ${failure}`);
    }
    if (profile.name === 'iphone-15' || profile.name === 'iphone-se') {
      // Journey state machine (CLOSED → PRE_ENTRY_OPEN → CLOSED) and the Form Helper 2.0 phone flow
      // (card → explain → editor → preview sheet) on real WebKit.
      const fhReport = { name: 'journey+form-helper', failures: [] };
      try {
        await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('#civicLanding [data-cs-journey="pre"]', { timeout: 20000 });
        await page.locator('[data-cs-journey="pre"]').tap();
        await page.waitForTimeout(300);
        if ((await page.getAttribute('[data-cs-journey="pre"]', 'aria-expanded')) !== 'true') fhReport.failures.push('journey did not open on tap');
        const panelShown = await page.evaluate(() => { const p = document.getElementById('civicJourneyPanel'); return !!p && !p.hidden && p.getBoundingClientRect().height > 40; });
        if (!panelShown) fhReport.failures.push('journey panel not shown');
        await page.locator('[data-cs-journey="pre"]').tap();
        await page.waitForTimeout(200);
        if ((await page.getAttribute('[data-cs-journey="pre"]', 'aria-expanded')) !== 'false') fhReport.failures.push('second tap did not collapse the journey');
        const journeyState = await inspect(page, profile, 'journey');
        profileReport.states.push(journeyState);
        fhReport.failures.push(...journeyState.failures);
        await page.goto(`http://127.0.0.1:${PORT}/form-helper.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('body.fh-ready', { timeout: 20000 });
        await page.waitForTimeout(400);
        const home = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, cards: document.querySelectorAll('.fh-card').length }));
        if (home.overflow > 1) fhReport.failures.push(`form helper home overflows by ${home.overflow}px`);
        if (home.cards < 12) fhReport.failures.push(`form helper lists ${home.cards} cards`);
        await page.screenshot({ path: path.join(OUT, `${profile.name}-form-helper-home.png`), fullPage: false });
        await page.locator('.fh-card[data-form="F08"]').first().tap();
        await page.waitForSelector('#fhStart', { timeout: 10000 });
        await page.locator('#fhStart').tap();
        await page.waitForSelector('#f_name', { timeout: 10000 });
        await page.fill('#f_name', 'nguyen van anh');
        await page.fill('#f_arc_no', '9801231234567');
        await page.waitForTimeout(300);
        const edit = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, name: document.getElementById('f_name').value, arc: document.getElementById('f_arc_no').value, ops: (window.VisableFormHelper && VisableFormHelper.state.ops.length) || 0, bar: !!document.querySelector('#fhMobileBar') && getComputedStyle(document.querySelector('#fhMobileBar')).display !== 'none' }));
        if (edit.overflow > 1) fhReport.failures.push(`form helper editor overflows by ${edit.overflow}px`);
        if (edit.name !== 'NGUYEN VAN ANH') fhReport.failures.push(`upper-case normalisation failed (${edit.name})`);
        if (edit.arc !== '980123-1234567') fhReport.failures.push(`registration number normalisation failed (${edit.arc})`);
        if (edit.ops < 14) fhReport.failures.push(`preview ops missing (${edit.ops})`);
        if (!edit.bar) fhReport.failures.push('mobile action bar not shown');
        await page.screenshot({ path: path.join(OUT, `${profile.name}-form-helper-edit.png`), fullPage: false });
        await page.locator('#fhOpenSheet').tap();
        await page.waitForSelector('#fhSheet canvas', { timeout: 10000 });
        await page.waitForTimeout(500);
        const sheet = await page.evaluate(() => { const c = document.querySelector('#fhSheet canvas'); const r = c.getBoundingClientRect(); return { width: r.width, innerWidth, overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth }; });
        if (sheet.width < sheet.innerWidth - 40) fhReport.failures.push(`preview sheet canvas is only ${Math.round(sheet.width)}px wide`);
        await page.screenshot({ path: path.join(OUT, `${profile.name}-form-helper-sheet.png`), fullPage: false });
        await page.locator('#fhSheetClose').tap();
        await page.waitForTimeout(200);
      } catch (error) {
        fhReport.failures.push(`flow error: ${String(error.message || error)}`);
      }
      profileReport.guidanceFlows = profileReport.guidanceFlows || [];
      profileReport.guidanceFlows.push(fhReport);
      for (const failure of fhReport.failures) report.failures.push(`${profile.name}/journey+form-helper: ${failure}`);
    }
    {
      // Waymaker answer card (ai.html) on real WebKit, every iPhone profile: the
      // REAL public /api/ask projection for "D-2 연장시 필수 서류" must render as
      // the structured checklist with no provider/model identity, no raw
      // Markdown, no internal source metadata, no overflow, and a composer that
      // does not cover the answer actions. The provider-failed projection
      // (every Fast model failed, deterministic structured answer delivered)
      // must render through the same renderer with no error card.
      for (const [wmName, wmFixture] of [
        ['waymaker-answer', 'd2_documents_ko_fast.json'],
        ['waymaker-answer-provider-failed', 'd2_documents_ko_fast_provider_failed.json'],
      ]) {
      const wmReport = { name: wmName, failures: [] };
      const fixture = await fs.readFile(path.join(ROOT, 'tests', 'fixtures', 'waymaker', wmFixture), 'utf8');
      try {
        await page.route('**/api/ask', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: fixture }));
        await page.goto(`http://127.0.0.1:${PORT}/ai.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('#aiQ', { timeout: 20000 });
        await page.locator('.ai-mode-btn[data-mode="fast"]').tap();
        await page.fill('#aiQ', 'D-2 연장시 필수 서류');
        await page.locator('#sendBtn').tap();
        const agree = page.locator('#consentModal .btn-agree');
        if (await agree.isVisible().catch(() => false)) await agree.tap();
        await page.waitForSelector('.answer-card .pa-answer-card', { timeout: 15000 });
        await page.waitForTimeout(300);
        const card = await page.evaluate(() => {
          const el = document.querySelector('.answer-card');
          const text = el.innerText;
          const attrs = [...document.querySelectorAll('[aria-label], [title]')].map((n) => `${n.getAttribute('aria-label') || ''} ${n.getAttribute('title') || ''}`).join(' ');
          const r = el.getBoundingClientRect();
          const copy = el.querySelector('[data-copy-kind="answer"]');
          copy.scrollIntoView({ block: 'center' });
          const cr = copy.getBoundingClientRect();
          const top = document.elementFromPoint(cr.left + cr.width / 2, cr.top + cr.height / 2);
          return {
            text, attrs, left: r.left, right: r.right, innerWidth,
            commonDocs: el.querySelectorAll('[data-bucket-list="common"] > li').length,
            modeChip: (el.querySelector('.answer-mode-chip') || {}).textContent || '',
            copyCovered: !(top === copy || copy.contains(top)),
            errorCards: document.querySelectorAll('.error-card').length,
            sourceCard: Boolean(el.querySelector('.pa-source-card')),
          };
        });
        if (card.commonDocs !== 4) wmReport.failures.push(`expected 4 basic documents, got ${card.commonDocs}`);
        if (card.modeChip !== '빠른 답변') wmReport.failures.push(`mode chip shows "${card.modeChip}"`);
        if (/openrouter|groq|ollama|nemotron|gemma|nvidia|inkling/i.test(card.text + card.attrs)) wmReport.failures.push('provider/model identity visible');
        if (/(^|\n)\s*#{1,6}\s|###/.test(card.text)) wmReport.failures.push('raw Markdown heading visible');
        if (/source[\s_-]*file|source_revision_date/i.test(card.text)) wmReport.failures.push('internal source metadata visible');
        if (/\b(?:BASIS|DISABLED|NOT WIRED)\b|기능 꺼짐/.test(card.text)) wmReport.failures.push('engineering status label visible');
        if (card.left < -1 || card.right > card.innerWidth + 1) wmReport.failures.push(`answer card leaves the viewport (${Math.round(card.left)}..${Math.round(card.right)})`);
        if (card.copyCovered) wmReport.failures.push('composer covers the answer actions');
        if (card.errorCards) wmReport.failures.push('error card rendered for a structured answer');
        if (/답변 생성 오류|일시적인 문제/.test(card.text)) wmReport.failures.push('error/degraded wording on a structured answer');
        if (!card.sourceCard) wmReport.failures.push('structured source card missing');
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
        if (overflow > 2) wmReport.failures.push(`ai.html overflows horizontally by ${overflow}px`);
        await page.locator('.answer-card').screenshot({ path: path.join(OUT, `${profile.name}-${wmName}.png`) });
        await page.unroute('**/api/ask');
      } catch (error) {
        wmReport.failures.push(`flow error: ${String(error.message || error)}`);
      }
      profileReport.guidanceFlows = profileReport.guidanceFlows || [];
      profileReport.guidanceFlows.push(wmReport);
      for (const failure of wmReport.failures) report.failures.push(`${profile.name}/${wmName}: ${failure}`);
      }
    }
    report.profiles.push(profileReport);
    await context.close();
  }
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

await fs.writeFile(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ engine: report.engine, profiles: report.profiles.map((p) => ({ name: p.name, states: p.states.map((s) => ({ state: s.state, failures: s.failures })) })), failures: report.failures }, null, 2));
if (report.failures.length) process.exitCode = 1;
