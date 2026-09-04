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
  '.top-ctrls', '.hero-container', '.p-hero-title', '.p-gateway', '.p-gw-search',
  '.p-gw-card', '.p-gw-util', '.p-gw-newhome', '.hero-actions', '.sbar', '#q',
  '.results-area', '.rlist', '.us-layer', '.us-interpret', '.us-ai', '.ai-fab',
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
    const touchTargets = [...document.querySelectorAll('.top-ctrls button, .top-ctrls [role="button"], .hero-actions .ha, .p-gw-search, .p-gw-card, .p-gw-util, .p-gw-newhome, .sbar button, .sbar [role="button"]')]
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
        document.body.classList.remove('searched', 'searching');
        if (nextState !== 'landing') document.body.classList.add(nextState);
      }, state);
      await page.waitForTimeout(120);
      const stateReport = await inspect(page, profile, state);
      profileReport.states.push(stateReport);
      const suffix = state === 'landing' ? '' : `-${state}`;
      await page.screenshot({ path: path.join(OUT, `${profile.name}${suffix}.png`), fullPage: true });
      for (const failure of stateReport.failures) report.failures.push(`${profile.name}/${state}: ${failure}`);
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
