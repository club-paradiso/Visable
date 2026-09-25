// Waymaker (ai.html) + New Home (new-home.html) responsive / visual QA.
//
// Drives the real pages in Chromium across the phone → large-desktop matrix,
// light + dark (+ Editorial-pop spot checks), Korean + English and several
// long / non-Latin locales, and asserts what a screenshot alone cannot prove:
//
//   · no page-level horizontal overflow (scrollWidth ≤ clientWidth)
//   · critical controls visible, with ≥44×44 CSS px tap targets
//   · no visible text under 12px, no horizontally clipped control labels
//   · dialogs fit the viewport and scroll inside themselves
//   · state contracts: welcome → conversation (mocked /api/ask), ?nav=1,
//     research route, consent dialog, New Home dialogs and hand-off links
//
// Screenshots are written as evidence next to a JSON + Markdown report; the
// assertions are the verdict. Exit code 1 when any check fails.
//
//   python3 -m http.server 4173 &              # repo root
//   node scripts/qa/waymaker_new_home_visual_qa.mjs [outDir]
//
// Env: BASE (default http://127.0.0.1:4173), PARADISO_PW_EXECUTABLE (Chromium
// path), PRETENDARD_DIR (serve the Pretendard CDN files from a local copy of
// the `pretendard` npm package's dist/web/variable/ when the CDN is blocked),
// QA_QUICK=1 (a reduced matrix for iteration).
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const OUT = process.argv[2] || 'artifacts/waymaker-new-home-qa';
fs.mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE || 'http://127.0.0.1:4173';
const FONT_DIR = process.env.PRETENDARD_DIR || '';
const QUICK = process.env.QA_QUICK === '1';
const UA_IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1';

const VIEWPORTS = QUICK
  ? [[320, 568], [390, 844], [768, 1024], [1440, 900]]
  : [[320, 568], [360, 800], [375, 812], [390, 844], [393, 852], [414, 896], [430, 932], [768, 1024], [844, 390], [1024, 768], [1280, 900], [1440, 900], [1920, 1080]];
const SHOT_WIDTHS = new Set([320, 390, 768, 844, 1024, 1440, 1920]);
const LONG_LOCALES = QUICK ? ['de', 'ar'] : ['de', 'ru', 'vi', 'id', 'ar', 'ja', 'zh-CN'];

const ANSWER = {
  answer: 'D-2(유학) 체류기간 연장은 체류기간 만료 전에 관할 출입국·외국인관서에 신청합니다.\n\n- 통합신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료\n- 재정입증 서류(잔고증명 등)\n- 재학증명서\n\n**신청 시점**을 놓치지 않도록 HiKorea 방문예약 가능 여부를 먼저 확인하세요. 최종 판단은 1345 또는 관할 기관에 확인하세요.',
  grounding_used: true,
  grounding_sources: [{ source_title: '외국인체류 안내매뉴얼', source_date: '2026.09', issuing_body: '법무부 출입국·외국인정책본부', section: '유학(D-2)', procedure_type: '체류기간 연장허가', page_range: '43-44' }],
  visa_code_detected: 'D-2', task_type_detected: 'extension', model: 'qa-model', provider: 'openrouter', model_resolved: 'qa-model',
  law_grounding_attempted: true, law_grounding_used: false, law_grounding_warnings: ['SOURCE_UNAVAILABLE'],
  related_statuses_not_sources: ['D-4']
};

const browser = await chromium.launch({
  executablePath: process.env.PARADISO_PW_EXECUTABLE || (fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined),
  headless: true, args: ['--no-sandbox']
});

const rows = [];
const failures = [];
function record(row) {
  rows.push(row);
  for (const f of row.fail) failures.push(`${row.page} · ${row.state} · ${row.vp} · ${row.theme} · ${row.lang}: ${f}`);
}

async function newPage({ w, h, theme = 'light', lang = 'ko', pop = false, consent = true }) {
  const mobile = w < 768;
  const ctx = await browser.newContext({
    viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile || w < 1024,
    userAgent: mobile ? UA_IOS : undefined, locale: lang === 'ko' ? 'ko-KR' : 'en-US'
  });
  await ctx.addInitScript(([t, l, p, c]) => {
    try {
      localStorage.setItem('paradiso:brightness', t);
      localStorage.setItem('paradiso:language', l);
      localStorage.setItem('paradiso:editorial-theme', p ? 'archive_diary' : 'civic_editorial');
      if (c) localStorage.setItem('paradiso_ai_consent', JSON.stringify({ agreed: true, at: Date.now() }));
      else localStorage.removeItem('paradiso_ai_consent');
    } catch (e) { /* storage blocked */ }
  }, [theme, lang, pop, consent]);
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e.message || e)));
  if (FONT_DIR) {
    await page.route('**/pretendard@v1.3.9/dist/web/variable/**', (r) => {
      const rel = new URL(r.request().url()).pathname.split('/dist/web/variable/')[1].replace('.min.css', '.css');
      const file = path.join(FONT_DIR, rel);
      if (!fs.existsSync(file)) return r.abort();
      return r.fulfill({ path: file, contentType: file.endsWith('.css') ? 'text/css' : 'font/woff2' });
    });
  }
  await page.route('**/api/**', (r) => r.abort());
  await page.route('**/api/ask', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ANSWER) }));
  return { ctx, page, errors };
}

// ── Measurements (run in the page) ────────────────────────────────────────
async function measure(page, { targets = [], visible = [], modal = null } = {}) {
  return page.evaluate(({ targets, visible, modal }) => {
    const out = { overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, smallTargets: [], missing: [], tinyText: [], clipped: [], modal: null, masked: [] };
    const shown = (el) => {
      if (!el) return false;
      const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) > 0.01;
    };
    // A page that clips its own overflow would pass the scrollWidth check while
    // still cutting content off — treat that as a failure, not a fix.
    // (Both axes hidden is legitimate: the desktop Waymaker app shell and the
    // dialog scroll lock. Then the inner scroll containers are checked below.)
    for (const el of [document.documentElement, document.body]) {
      const cs = getComputedStyle(el);
      const xOnly = (cs.overflowX === 'hidden' || cs.overflowX === 'clip') && cs.overflowY !== 'hidden' && cs.overflowY !== 'clip';
      if (xOnly) out.masked.push(el.tagName.toLowerCase() + ' overflow-x:' + cs.overflowX);
    }
    for (const el of document.querySelectorAll('.chat-history, .wm-workspace-main, #legalSourceSearchRoot, #waymakerNavigatorRoot, .nh-modal-body, .modal-body')) {
      if (!shown(el)) continue;
      if (el.scrollWidth > el.clientWidth + 1) out.masked.push((el.id ? '#' + el.id : '.' + el.className.split(' ')[0]) + ` inner overflow ${el.scrollWidth - el.clientWidth}px`);
    }
    const label = (el) => (el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '')) + ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 24) + '"';
    for (const sel of visible) if (![...document.querySelectorAll(sel)].some(shown)) out.missing.push(sel);
    for (const sel of targets) {
      for (const el of document.querySelectorAll(sel)) {
        if (!shown(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.height < 43.5 || r.width < 43.5) out.smallTargets.push(label(el) + ` ${Math.round(r.width)}×${Math.round(r.height)}`);
      }
    }
    // Text contrast against the nearest opaque background (WCAG 2.2 AA:
    // 4.5:1, or 3:1 for large text). Gradients are ignored — the page's
    // decorative washes are kept faint enough for this to stay conservative.
    const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
    const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
    const bgOf = (el) => {
      let layers = [];
      for (let n = el; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) break; } }
      let base = { r: 255, g: 255, b: 255 };
      for (let i = layers.length - 1; i >= 0; i -= 1) { const c = layers[i]; base = { r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a) }; }
      return base;
    };
    out.lowContrast = [];
    const scope = modal ? document.querySelector(modal) : document.body;
    const walker = document.createTreeWalker(scope || document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    while (walker.nextNode()) {
      const t = walker.currentNode; const el = t.parentElement;
      if (!el || seen.has(el) || !t.textContent.trim()) continue;
      seen.add(el);
      if (el.closest('.sr-only, .cs-sr, [aria-hidden="true"], script, style, template, noscript, .skip-link')) continue;
      if (!shown(el)) continue;
      const cs = getComputedStyle(el);
      const fs = parseFloat(cs.fontSize);
      if (fs < 11.9) out.tinyText.push(label(el) + ' ' + fs + 'px');
      const fg = parse(cs.color);
      if (fg && fg.a > 0.5 && !el.closest('button:disabled, [aria-disabled="true"]') && Number(cs.opacity) > 0.9) {
        const bg = bgOf(el); const L1 = lum(fg), L2 = lum(bg);
        const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
        const large = fs >= 24 || (fs >= 18.66 && Number(cs.fontWeight) >= 700);
        if (ratio < (large ? 3 : 4.5) - 0.05) out.lowContrast.push(label(el) + ' ' + ratio.toFixed(2) + ':1');
      }
    }
    for (const el of document.querySelectorAll('button, a, .nh-lang-btn, .vf-product, .ai-mode-btn, .wm-workspace-nav-link')) {
      if (!shown(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.overflowX === 'visible' && cs.textOverflow !== 'ellipsis') continue;
      if (el.scrollWidth > el.clientWidth + 1 && cs.textOverflow !== 'ellipsis') out.clipped.push(label(el));
    }
    if (modal) {
      const m = document.querySelector(modal);
      if (m && shown(m)) {
        const r = m.getBoundingClientRect();
        out.modal = { top: Math.round(r.top), bottom: Math.round(r.bottom), vh: innerHeight, fits: r.top >= -1 && r.bottom <= innerHeight + 1 && r.left >= -1 && r.right <= innerWidth + 1 };
      } else out.modal = { fits: false, missing: true };
    }
    return out;
  }, { targets, visible, modal });
}

function verdict(m, extra = []) {
  const fail = [...extra];
  if (m.overflow > 1) fail.push(`horizontal overflow ${m.overflow}px`);
  if (m.masked.length) fail.push('overflow masked: ' + m.masked.join(', '));
  if (m.missing.length) fail.push('not visible: ' + m.missing.join(', '));
  if (m.smallTargets.length) fail.push('tap targets <44px: ' + m.smallTargets.slice(0, 6).join('; '));
  if (m.tinyText.length) fail.push('text <12px: ' + m.tinyText.slice(0, 4).join('; '));
  if (m.clipped.length) fail.push('clipped labels: ' + m.clipped.slice(0, 4).join('; '));
  if (m.lowContrast && m.lowContrast.length) fail.push('contrast below AA: ' + m.lowContrast.slice(0, 5).join('; '));
  if (m.modal && !m.modal.fits) fail.push('dialog outside viewport ' + JSON.stringify(m.modal));
  return fail;
}

async function shot(page, name, full = false) {
  await page.screenshot({ path: path.join(OUT, name + '.png'), fullPage: full });
}

const WM_TARGETS = ['.vf-home', '.vf-icon-btn', '.wm-workspace-nav .wm-workspace-nav-link', '.ai-welcome-chip', '.send-btn', '.ai-mode-btn', '.wm-route-link'];
const NH_TARGETS = ['.vf-home', '.nh-ctl', '.nh-section-nav a', '.nh-hero .nh-btn', '.nh-card', '.nh-hub-item', '#waymakerCta', '.nh-footer a[data-c]'];

// ── Waymaker ──────────────────────────────────────────────────────────────
async function waymaker(vp, theme, lang, opts = {}) {
  const [w, h] = vp;
  const tag = `${w}x${h}-${theme}-${lang}${opts.pop ? '-pop' : ''}`;
  const { ctx, page, errors } = await newPage({ w, h, theme, lang, pop: opts.pop });
  await page.goto(BASE + '/ai.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#welcomeMessage .ai-welcome-chip');
  await page.waitForTimeout(500);
  let m = await measure(page, { targets: WM_TARGETS, visible: ['.vf-bar', '.vf-product', '.wm-brand-wordmark', '#aiQ', '#sendBtn', '#welcomeMessage .ai-title-main', '#referenceDisclaimer', '[data-workspace-route="navigator"]', '[data-workspace-route="research"]'] });
  const brand = await page.evaluate(() => ({
    header: [...document.querySelectorAll('.vf-product-wordmark')].some((img) => img.offsetWidth > 0 && img.complete && img.naturalWidth > 0),
    hero: [...document.querySelectorAll('.wm-brand-wordmark-img')].some((img) => img.offsetWidth > 0 && img.complete && img.naturalWidth > 0)
  }));
  const composerTop = await page.locator('.wm-composer').evaluate((el) => el.getBoundingClientRect().top);
  const extra = [];
  if (!brand.header) extra.push('Waymaker family-bar wordmark missing or failed to load');
  if (!brand.hero) extra.push('Waymaker hero wordmark missing or failed to load');
  if (w < 1024 && h >= 700 && composerTop > h) extra.push(`composer below the first screen (${Math.round(composerTop)}px)`);
  const aria = await page.getAttribute('[data-workspace-route="chat"]', 'aria-current');
  if (aria !== 'page') extra.push('chat route not aria-current');
  record({ page: 'waymaker', state: 'welcome', vp: `${w}x${h}`, theme: theme + (opts.pop ? '+pop' : ''), lang, fail: verdict(m, extra.concat(errors.map((e) => 'pageerror ' + e))) });
  if (SHOT_WIDTHS.has(w) && !opts.noShots) await shot(page, `wm-welcome-${tag}`);

  if (opts.full) {
    // typed → context strip, then a mocked conversation turn
    await page.fill('#aiQ', lang === 'en' ? 'What do I need to extend a D-2 visa? My stay expires next month.' : 'D-2 연장에 필요한 서류는? 다음 달에 체류기간이 만료됩니다.');
    await page.waitForTimeout(200);
    const strip = await page.locator('.wm-context-strip').isVisible();
    await page.click('#sendBtn');
    await page.waitForSelector('.answer-card', { timeout: 15000 });
    await page.waitForTimeout(700);
    m = await measure(page, { targets: ['.send-btn', '.ai-mode-btn', '.answer-action', '.vf-icon-btn'], visible: ['.answer-card .answer-body', '.answer-card .source-panel', '.msg-row.user', '#aiQ', '#sendBtn'] });
    const conv = await page.evaluate(() => ({
      conversing: document.body.classList.contains('wm-conversing'),
      auroraOpacity: getComputedStyle(document.querySelector('.wm-aurora')).opacity,
      sendIcon: !!document.querySelector('#sendBtn svg'),
      answerTop: document.querySelector('.msg-row.answer').getBoundingClientRect().top
    }));
    const extra2 = [];
    if (!strip) extra2.push('context strip hidden while typing');
    if (!conv.conversing) extra2.push('body.wm-conversing missing');
    if (conv.auroraOpacity !== '0') extra2.push('aurora still visible in conversation');
    if (!conv.sendIcon) extra2.push('send button lost its icon');
    if (conv.answerTop > h || conv.answerTop < -20) extra2.push(`answer not scrolled to its start (top ${Math.round(conv.answerTop)})`);
    if (w < 1024 && h > 500) {
      const sticky = await page.locator('.chat-input-area').evaluate((el) => getComputedStyle(el).position);
      if (sticky !== 'sticky') extra2.push('composer not sticky while reading on touch widths');
    }
    record({ page: 'waymaker', state: 'conversation', vp: `${w}x${h}`, theme: theme + (opts.pop ? '+pop' : ''), lang, fail: verdict(m, extra2.concat(errors.map((e) => 'pageerror ' + e))) });
    if (SHOT_WIDTHS.has(w)) await shot(page, `wm-conversation-${tag}`);

    // research route (same document, no reload)
    await page.locator('.wm-workspace-nav [data-workspace-route="research"]').click();
    await page.waitForSelector('#legalSourceSearchRoot .lss-panel', { timeout: 15000 });
    await page.waitForTimeout(300);
    m = await measure(page, { targets: ['.lss-search-btn', '.lss-tab', '.vf-icon-btn'], visible: ['#legalSourceSearchRoot .lss-panel', '.lss-input'] });
    const r = await page.evaluate(() => ({ hidden: getComputedStyle(document.getElementById('chatHistory')).display === 'none', current: document.querySelector('.wm-workspace-nav [data-workspace-route="research"]').getAttribute('aria-current') }));
    const extra3 = [];
    if (!r.hidden) extra3.push('chat still visible in research');
    if (r.current !== 'page') extra3.push('research route not aria-current');
    record({ page: 'waymaker', state: 'research', vp: `${w}x${h}`, theme: theme + (opts.pop ? '+pop' : ''), lang, fail: verdict(m, extra3) });
    if (SHOT_WIDTHS.has(w)) await shot(page, `wm-research-${tag}`);
  }
  await ctx.close();
}

async function waymakerNavigator(vp, theme) {
  const [w, h] = vp;
  const { ctx, page, errors } = await newPage({ w, h, theme });
  await page.goto(BASE + '/ai.html?nav=1', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.wm-intro .wm-btn-primary', { timeout: 20000 });
  let m = await measure(page, { targets: ['.wm-btn', '.vf-icon-btn', '.wm-workspace-nav .wm-workspace-nav-link'], visible: ['.wm-intro .wm-btn-primary', '.vf-product'] });
  const hidden = await page.evaluate(() => ['#chatHistory', '.chat-input-area', '.quota-badge', '.ai-title'].filter((s) => { const e = document.querySelector(s); return e && getComputedStyle(e).display !== 'none'; }));
  const btnContrast = await page.locator('.wm-intro .wm-btn-primary').evaluate((el) => { const cs = getComputedStyle(el); return cs.color + ' on ' + cs.backgroundColor; });
  record({ page: 'waymaker', state: 'navigator-intro', vp: `${w}x${h}`, theme, lang: 'ko', fail: verdict(m, hidden.map((s) => s + ' visible in navigator').concat(errors.map((e) => 'pageerror ' + e))), note: btnContrast });
  if (SHOT_WIDTHS.has(w)) await shot(page, `wm-navigator-${w}x${h}-${theme}`);
  await page.click('.wm-intro .wm-btn-primary');
  await page.waitForSelector('.wm-chip', { timeout: 10000 });
  m = await measure(page, { targets: ['.wm-chip', '.wm-btn'], visible: ['.wm-chip'] });
  record({ page: 'waymaker', state: 'navigator-step', vp: `${w}x${h}`, theme, lang: 'ko', fail: verdict(m) });
  if (SHOT_WIDTHS.has(w)) await shot(page, `wm-navigator-step-${w}x${h}-${theme}`);
  await ctx.close();
}

async function waymakerConsent(vp, theme) {
  const [w, h] = vp;
  const { ctx, page } = await newPage({ w, h, theme, consent: false });
  await page.goto(BASE + '/ai.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#aiQ');
  await page.fill('#aiQ', '테스트 질문입니다');
  await page.click('#sendBtn');
  await page.waitForSelector('#consentModal.active');
  await page.waitForTimeout(200);
  const m = await measure(page, { targets: ['.btn-agree', '.btn-cancel'], visible: ['.btn-agree', '.btn-cancel', '#consentTitle'], modal: '#consentModal .modal-box' });
  const focused = await page.evaluate(() => document.activeElement && document.activeElement.classList.contains('btn-agree'));
  record({ page: 'waymaker', state: 'consent-dialog', vp: `${w}x${h}`, theme, lang: 'ko', fail: verdict(m, focused ? [] : ['agree button not focused']) });
  if (SHOT_WIDTHS.has(w)) await shot(page, `wm-consent-${w}x${h}-${theme}`);
  await ctx.close();
}

// ── New Home ──────────────────────────────────────────────────────────────
async function newHome(vp, theme, lang, opts = {}) {
  const [w, h] = vp;
  const tag = `${w}x${h}-${theme}-${lang}${opts.pop ? '-pop' : ''}`;
  const { ctx, page, errors } = await newPage({ w, h, theme, lang, pop: opts.pop });
  await page.goto(BASE + '/new-home.html', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.nh-card-icon');
  await page.waitForTimeout(400);
  let m = await measure(page, { targets: NH_TARGETS, visible: ['.vf-bar', '.vf-product', '.nh-brand-wordmark', '.nh-section-nav', '.nh-hero .nh-title', '.nh-hero .nh-btn-primary', '.nh-hero .nh-btn-secondary', '#langBtn', '#brightBtn'] });
  const brand = await page.evaluate(() => ({
    header: [...document.querySelectorAll('.vf-product-wordmark')].some((img) => img.offsetWidth > 0 && img.complete && img.naturalWidth > 0),
    hero: [...document.querySelectorAll('.nh-brand-wordmark-img')].some((img) => img.offsetWidth > 0 && img.complete && img.naturalWidth > 0)
  }));
  const hero = await page.evaluate(() => {
    const cta = document.querySelector('.nh-hero .nh-btn-primary').getBoundingClientRect();
    const title = document.querySelector('.nh-title').getBoundingClientRect();
    return { ctaBottom: cta.bottom, titleLeft: title.left, titleRight: title.right };
  });
  const extra = [];
  if (!brand.header) extra.push('New Home family-bar wordmark missing or failed to load');
  if (!brand.hero) extra.push('New Home hero wordmark missing or failed to load');
  if (hero.ctaBottom > h + 1 && h >= 700) extra.push(`primary CTA below the first screen (${Math.round(hero.ctaBottom)}px)`);
  const dark = await page.evaluate(() => document.body.getAttribute('data-theme'));
  if ((theme === 'dark') !== (dark === 'dark')) extra.push('brightness not applied');
  record({ page: 'new-home', state: 'landing', vp: `${w}x${h}`, theme: theme + (opts.pop ? '+pop' : ''), lang, fail: verdict(m, extra.concat(errors.map((e) => 'pageerror ' + e))) });
  if (SHOT_WIDTHS.has(w) && !opts.noShots) await shot(page, `nh-landing-${tag}`);
  if (opts.fullShot) await shot(page, `nh-full-${tag}`, true);

  if (opts.full) {
    // below-the-fold sections: tap targets and overflow at the hand-off and sources
    await page.locator('#waymaker').scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    m = await measure(page, { targets: ['#waymakerCta', '.nh-next .nh-btn', '.nh-hub-item'], visible: ['#waymakerCta', '#interviewBridge .nh-btn'] });
    const href = await page.getAttribute('#waymakerCta', 'href');
    record({ page: 'new-home', state: 'waymaker-handoff', vp: `${w}x${h}`, theme, lang, fail: verdict(m, href === 'ai.html?domain=nationality' ? [] : ['hand-off href changed: ' + href]) });
    if (SHOT_WIDTHS.has(w)) await shot(page, `nh-handoff-${tag}`);

    // readiness dialog: focus, progress semantics, fit, Escape restores focus
    await page.evaluate(() => window.scrollTo(0, 0));
    const trigger = page.locator('.nh-hero [data-action="open-readiness"]');
    await trigger.click();
    await page.waitForSelector('#readinessModal.active');
    await page.waitForTimeout(250);
    await page.locator('#readinessModal input[type="radio"]').first().check();
    m = await measure(page, { targets: ['#readinessModal .nh-opt', '#readinessModal .nh-btn-sm', '#readinessModal .nh-modal-close'], visible: ['#readinessModal legend', '#readinessModal .nh-btn-sm.primary'], modal: '#readinessModal .nh-modal' });
    const legendFocus = await page.evaluate(() => document.activeElement && document.activeElement.tagName);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
    const back = await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-action'));
    const extraR = [];
    if (back !== 'open-readiness') extraR.push('focus not restored to trigger after Escape');
    record({ page: 'new-home', state: 'readiness-dialog', vp: `${w}x${h}`, theme, lang, fail: verdict(m, extraR), note: 'focus after open: ' + legendFocus });
    await trigger.click();
    await page.waitForSelector('#readinessModal.active');
    await page.waitForTimeout(200);
    if (SHOT_WIDTHS.has(w)) await shot(page, `nh-readiness-${tag}`);
    await page.keyboard.press('Escape');

    // hub detail dialog
    await page.locator('.nh-hub-item[data-id="loss"]').scrollIntoViewIfNeeded();
    await page.locator('.nh-hub-item[data-id="loss"]').click();
    await page.waitForSelector('#detailModal.active');
    await page.waitForTimeout(200);
    m = await measure(page, { targets: ['#detailModal .nh-modal-close', '#detailModal .nh-btn-sm'], visible: ['#detailModal .nh-modal-title', '#detailModal .nh-btn-sm.primary'], modal: '#detailModal .nh-modal' });
    record({ page: 'new-home', state: 'hub-detail-dialog', vp: `${w}x${h}`, theme, lang, fail: verdict(m) });
    if (SHOT_WIDTHS.has(w)) await shot(page, `nh-detail-${tag}`);
    await page.keyboard.press('Escape');

    // path finder → result with the Waymaker hand-off
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.locator('.nh-card[data-action="open-pathfinder"]').click();
    await page.waitForSelector('#pathfinderModal.active');
    for (let i = 0; i < 3; i += 1) {
      await page.locator('#pathfinderModal input[type="radio"]').first().check();
      await page.locator('#pathfinderModal .nh-btn-sm.primary').click();
      await page.waitForTimeout(120);
    }
    await page.waitForSelector('#pathfinderBody [data-nh-result]');
    const first = page.locator('#pathfinderBody .nh-path-head').first();
    await first.click();
    await page.waitForTimeout(150);
    m = await measure(page, { targets: ['#pathfinderModal .nh-path-head', '#pathfinderModal .nh-btn-sm'], visible: ['#pathfinderModal .nh-path-body', '#pathfinderModal a.nh-btn-sm.primary'], modal: '#pathfinderModal .nh-modal' });
    const expanded = await first.getAttribute('aria-expanded');
    record({ page: 'new-home', state: 'pathfinder-result', vp: `${w}x${h}`, theme, lang, fail: verdict(m, expanded === 'true' ? [] : ['path card did not expand']) });
    if (SHOT_WIDTHS.has(w)) await shot(page, `nh-pathfinder-${tag}`);
    await page.keyboard.press('Escape');

    // language menu
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.click('#langBtn');
    await page.waitForSelector('#nhLangMenu.open');
    m = await measure(page, { targets: ['.nh-lang-option'], visible: ['#nhLangMenu.open'] });
    const menuBox = await page.locator('#nhLangMenu').evaluate((el) => { const r = el.getBoundingClientRect(); return { l: r.left, r: r.right, vw: innerWidth }; });
    record({ page: 'new-home', state: 'language-menu', vp: `${w}x${h}`, theme, lang, fail: verdict(m, menuBox.l < 0 || menuBox.r > menuBox.vw + 1 ? ['language menu off-screen'] : []) });
    await page.keyboard.press('Escape');
  }
  await ctx.close();
}

// ── Run ───────────────────────────────────────────────────────────────────
for (const vp of VIEWPORTS) {
  for (const theme of ['light', 'dark']) {
    const full = theme === 'light' || [390, 1440].includes(vp[0]);
    await waymaker(vp, theme, 'ko', { full });
    await newHome(vp, theme, 'ko', { full, fullShot: [390, 1440].includes(vp[0]) });
  }
  await waymaker(vp, 'light', 'en', { full: [320, 390, 768, 1280].includes(vp[0]), noShots: ![390, 1440].includes(vp[0]) });
  await newHome(vp, 'light', 'en', { full: [320, 390, 1280].includes(vp[0]), noShots: ![390, 1440].includes(vp[0]) });
  if ([360, 390, 768, 1024, 1440].includes(vp[0]) || QUICK) {
    await waymakerNavigator(vp, 'light');
    if ([390, 1440].includes(vp[0])) await waymakerNavigator(vp, 'dark');
  }
  if ([320, 390, 844, 1440].includes(vp[0])) await waymakerConsent(vp, 'light');
}
for (const lang of LONG_LOCALES) {
  for (const vp of [[320, 568], [1280, 900]]) {
    await waymaker(vp, 'light', lang, { noShots: vp[0] !== 320 });
    await newHome(vp, 'light', lang, { noShots: vp[0] !== 320 });
  }
}
for (const theme of ['light', 'dark']) {
  await waymaker([390, 844], theme, 'ko', { pop: true, full: true });
  await waymaker([1440, 900], theme, 'ko', { pop: true });
  await newHome([390, 844], theme, 'ko', { pop: true });
  await newHome([1440, 900], theme, 'ko', { pop: true });
}
await browser.close();

const byState = {};
for (const r of rows) {
  const k = r.page + ' · ' + r.state;
  byState[k] = byState[k] || { runs: 0, failed: 0 };
  byState[k].runs += 1;
  if (r.fail.length) byState[k].failed += 1;
}
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ base: BASE, viewports: VIEWPORTS, rows }, null, 2));
const md = ['# Waymaker + New Home visual QA', '', `Runs: ${rows.length} · failures: ${failures.length}`, '', '| surface · state | runs | failed |', '|---|---:|---:|']
  .concat(Object.entries(byState).map(([k, v]) => `| ${k} | ${v.runs} | ${v.failed} |`))
  .concat(['', failures.length ? '## Failures' : '## No failures', ''], failures.map((f) => '- ' + f));
fs.writeFileSync(path.join(OUT, 'report.md'), md.join('\n') + '\n');
console.log(md.join('\n'));
process.exit(failures.length ? 1 : 0);
