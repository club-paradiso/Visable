import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const PORT = 4175;
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
  fs.mkdirSync('reports/screenshots/after', { recursive: true });

  const launchOptions = {
    headless: true,
    ...(process.env.PARADISO_PW_EXECUTABLE ? { executablePath: process.env.PARADISO_PW_EXECUTABLE } : {})
  };
  const browser = await chromium.launch(launchOptions);

  try {
    // -------------------------------------------------------------
    // 1. Desktop 1280x900 Journeys
    // -------------------------------------------------------------
    const ctxDesktop = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const pageDesk = await ctxDesktop.newPage();
    await pageDesk.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });

    // Step 1: Initial Discovery Screen
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-step-1.png', fullPage: false });

    // Procedure Help Dialog
    await pageDesk.locator('#task-help-btn').click();
    await pageDesk.waitForTimeout(300);
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-procedure-dialog.png', fullPage: false });
    await pageDesk.locator('#task-help-close').click();
    await pageDesk.waitForTimeout(200);

    // Step 2: Select Task 1 (Extension)
    await pageDesk.locator('.task-card[data-procedure="extension"]').click();
    await pageDesk.waitForTimeout(300);
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-step-2-know.png', fullPage: false });

    // Step 2: ARC Guidance Tab
    await pageDesk.locator('#subtab-dont-know').click();
    await pageDesk.waitForTimeout(300);
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-step-2-arc.png', fullPage: false });

    // Switch back and pick D-2
    await pageDesk.locator('#subtab-know').click();
    await pageDesk.locator('.popular-chip[data-code="D-2"]').first().click();
    await pageDesk.waitForTimeout(200);
    await pageDesk.locator('#status-candidate-grid .candidate-item-btn').first().click();
    await pageDesk.waitForTimeout(300);

    // Step 3: Scenarios
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-step-3-scenarios.png', fullPage: false });

    // Pick first scenario -> Step 4
    await pageDesk.locator('#scenario-selection-grid .scenario-choice-card').first().click();
    await pageDesk.waitForTimeout(300);

    // Tick first two checkboxes to show progress bar
    const checkboxes = pageDesk.locator('#baseline-docs-list .checklist-item input[type="checkbox"]');
    const chkCount = await checkboxes.count();
    if (chkCount > 0) await checkboxes.nth(0).check();
    if (chkCount > 1) await checkboxes.nth(1).check();
    await pageDesk.waitForTimeout(200);

    // Select Seoul office to show transparency note
    await pageDesk.locator('#checklist-office-select').selectOption('seoul');
    await pageDesk.waitForTimeout(200);

    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-step-4-checklist.png', fullPage: false });

    // Operator Mode screenshot
    await pageDesk.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html#operator`, { waitUntil: 'networkidle' });
    await pageDesk.waitForTimeout(300);
    await pageDesk.screenshot({ path: 'reports/screenshots/after/desktop-1280-operator-mode.png', fullPage: false });

    await ctxDesktop.close();

    // -------------------------------------------------------------
    // 2. Mobile 390x844 Journeys
    // -------------------------------------------------------------
    const ctxMobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const pageMobile = await ctxMobile.newPage();
    await pageMobile.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });

    // Step 1 Mobile
    await pageMobile.screenshot({ path: 'reports/screenshots/after/mobile-390-step-1.png', fullPage: false });

    // Step 2 Mobile ARC Guide
    await pageMobile.locator('.task-card[data-procedure="extension"]').click();
    await pageMobile.locator('#subtab-dont-know').click();
    await pageMobile.waitForTimeout(300);
    await pageMobile.screenshot({ path: 'reports/screenshots/after/mobile-390-step-2-arc.png', fullPage: false });

    // Step 4 Mobile Checklist
    await pageMobile.locator('#subtab-know').click();
    await pageMobile.locator('.popular-chip[data-code="E-7-1"]').first().click();
    await pageMobile.waitForTimeout(200);
    await pageMobile.locator('#status-candidate-grid .candidate-item-btn').first().click();
    await pageMobile.waitForTimeout(200);
    await pageMobile.locator('#scenario-selection-grid .scenario-choice-card').first().click();
    await pageMobile.waitForTimeout(200);
    await pageMobile.screenshot({ path: 'reports/screenshots/after/mobile-390-step-4-checklist.png', fullPage: false });

    await ctxMobile.close();

    // -------------------------------------------------------------
    // 3. Mobile 320x568 Journeys
    // -------------------------------------------------------------
    const ctx320 = await browser.newContext({ viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true });
    const page320 = await ctx320.newPage();
    await page320.goto(`http://127.0.0.1:${PORT}/immigration-checklists.html`, { waitUntil: 'networkidle' });
    await page320.screenshot({ path: 'reports/screenshots/after/mobile-320-step-1.png', fullPage: false });

    // Form Helper Header at 320px
    await page320.goto(`http://127.0.0.1:${PORT}/form-helper.html`, { waitUntil: 'networkidle' });
    await page320.screenshot({ path: 'reports/screenshots/after/mobile-320-form-helper-fixed.png', fullPage: false });

    await ctx320.close();

    console.log('All "after" screenshots successfully captured.');
  } catch (err) {
    console.error('Error taking screenshots:', err);
  } finally {
    await browser.close();
    server.close();
  }
});
