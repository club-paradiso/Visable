// Text-overflow scan (release visual sign-off, 2026-09-23): 14 languages × 9 widths × landing,
// Form Helper home and editor. Flags any visible text node that leaves the viewport, is wider
// than its own box, or runs past its Form Helper card. Found the CJK keep-all headline clip,
// the French chip overflow and the German source-strip label. Needs the static server on :4173.
import { chromium } from '@playwright/test';
const b = await chromium.launch({ executablePath: process.env.PARADISO_PW_EXECUTABLE || '/opt/pw-browsers/chromium' });
let n = 0, total = 0;
for (const w of [320, 360, 375, 390, 393, 414, 430, 768, 1280]) {
  const p = await b.newPage({ viewport: { width: w, height: 800 }, isMobile: w < 768 });
  for (const lang of ['ko', 'en', 'de', 'ru', 'vi', 'ja', 'ar', 'zh-CN', 'es', 'fr', 'id', 'tl', 'tr', 'uk']) {
    for (const url of ['/index.html?lang=' + lang, '/form-helper.html?lang=' + lang, '/form-helper.html?form=F01&lang=' + lang]) {
      total++;
      await p.goto('http://127.0.0.1:4173' + url); await p.waitForSelector(url.includes('form-helper') ? 'body.fh-ready' : '#civicLanding [data-cs-journey="pre"]'); await p.waitForTimeout(200);
      const r = await p.evaluate(() => {
        const vw = document.documentElement.clientWidth; const out = [];
        for (const e of document.querySelectorAll('body *')) {
          if (e.closest('.cs-sr,[hidden],.fh-skip,script,style,canvas,.fh-rail,dialog:not([open])')) continue;
          const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
          const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
          const txt = [...e.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim());
          const over = txt && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' ? e.scrollWidth - e.clientWidth : 0;
          const par = e.parentElement && e.parentElement.getBoundingClientRect();
          const outOfParent = txt && par && e.closest('.fh-card') && (r.right > par.right + 1);
          if ((txt && (r.right > vw + 1 || r.left < -1)) || over > 1 || outOfParent) out.push(`${e.tagName}.${String(e.className).split(' ')[0]} over=${over} "${e.textContent.trim().slice(0, 20)}"`);
        }
        return out;
      });
      if (r.length) { n++; console.log(w, lang, url, r.slice(0, 3).join(' | ')); }
    }
  }
  await p.close();
}
console.log(`pages with clipped/escaping text: ${n} of ${total}`);
await b.close();
