import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const PORT = 4174;
const ROOT = process.cwd();

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png'
};

const server = http.createServer((req, res) => {
  let reqPath = decodeURIComponent(req.url.split('?')[0]);
  if (reqPath === '/') reqPath = '/index.html';
  const filePath = path.join(ROOT, reqPath);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.statusCode = 404;
    res.end('Not found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, async () => {
  console.log(`Server listening on port ${PORT}`);
  const launchOptions = {
    headless: true,
    ...(process.env.PARADISO_PW_EXECUTABLE ? { executablePath: process.env.PARADISO_PW_EXECUTABLE } : {})
  };
  const browser = await chromium.launch(launchOptions);

  try {
    // 1. Desktop 1280x900 initial
    const ctxDesktop = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const pageDesk = await ctxDesktop.newPage();
    await pageDesk.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });
    await pageDesk.screenshot({ path: 'reports/screenshots/before/desktop-1280-initial.png', fullPage: false });
    
    // Open editor modal on desktop
    await pageDesk.locator('.doc-card button').first().click();
    await pageDesk.waitForTimeout(300);
    await pageDesk.screenshot({ path: 'reports/screenshots/before/desktop-1280-editor-modal.png', fullPage: false });
    await ctxDesktop.close();

    // 2. Mobile 390x844 initial
    const ctxMobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const pageMobile = await ctxMobile.newPage();
    await pageMobile.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });
    await pageMobile.screenshot({ path: 'reports/screenshots/before/mobile-390-initial.png', fullPage: false });

    // Mobile editor modal
    await pageMobile.locator('.doc-card button').first().click();
    await pageMobile.waitForTimeout(300);
    await pageMobile.screenshot({ path: 'reports/screenshots/before/mobile-390-editor-modal.png', fullPage: false });

    // 3. Mobile 320x568 initial
    const ctx320 = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
    const page320 = await ctx320.newPage();
    await page320.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });
    await page320.screenshot({ path: 'reports/screenshots/before/mobile-320-initial.png', fullPage: false });

    // Form helper header at 320px
    await page320.goto(`http://127.0.0.1:${PORT}/form-helper.html`, { waitUntil: 'networkidle' });
    await page320.screenshot({ path: 'reports/screenshots/before/mobile-320-form-helper-header.png', fullPage: false });
    await ctx320.close();

    await ctxMobile.close();
    console.log('Baseline screenshots saved successfully.');
  } catch (err) {
    console.error('Error taking screenshots:', err);
  } finally {
    await browser.close();
    server.close();
  }
});
