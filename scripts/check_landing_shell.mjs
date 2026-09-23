#!/usr/bin/env node
/*
 * check_landing_shell.mjs — first-paint contract for the civic landing.
 *
 *  1. index.html carries the static civic shell and it is byte-identical to the
 *     Korean output of civic-search.js homeHtml() (run build_landing_shell.mjs
 *     after changing either side);
 *  2. the static <body> already carries `civic-refresh` and `landing`, so the
 *     legacy hero is hidden by CSS from the first frame, without JavaScript;
 *  3. the critical hide rules are inline in <head> (they cannot depend on the
 *     external civic stylesheet arriving);
 *  4. the civic script tag reports a load failure into the boot-failed state and
 *     the shell contains the reload row + <noscript> fallback;
 *  5. the bootstrap copy in civic-search.js equals the ko/en `civic` packs and
 *     every locale pack carries every civic key (the landing is pack-driven);
 *  6. the journey controls exist twice (pre/post), each a real <button> with
 *     aria-expanded="false" and aria-controls on the panel, and the core tools
 *     link to form-helper.html, ai.html and new-home.html.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadCivic, renderShellBlock, START, END } from './build_landing_shell.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(ROOT, 'index.html'), 'utf8');
let failures = 0, passed = 0;
function ok(cond, label) { if (cond) { passed++; console.log(`  PASS  ${label}`); } else { failures++; console.log(`  FAIL  ${label}`); } }

const civic = loadCivic();
const a = html.indexOf(START), b = html.indexOf(END);
ok(a > 0 && b > a, 'index.html contains the generated shell block');
const current = html.slice(a, b + END.length);
ok(current === renderShellBlock(civic), 'static shell equals civic-search.js homeHtml() for Korean (run: node scripts/build_landing_shell.mjs)');
ok(a < html.indexOf('<header class="hero-container" id="hero">'), 'shell sits before the legacy hero in document order');

const bodyTag = html.match(/<body class="([^"]*)"/);
ok(bodyTag && /\bcivic-refresh\b/.test(bodyTag[1]) && /\blanding\b/.test(bodyTag[1]), 'static <body> carries civic-refresh + landing (legacy hero hidden before any script runs)');
const headEnd = html.indexOf('</head>');
const head = html.slice(0, headEnd);
ok(/body\.civic-refresh\.landing #hero\s*\{[^}]*display:\s*none\s*!important/.test(head), 'critical inline CSS hides the legacy hero in <head>');
ok(/body\.civic-refresh #topCtrls[^{]*\{[^}]*display:\s*none\s*!important/.test(head), 'critical inline CSS hides the legacy top controls in <head>');
ok(/<script defer src="assets\/js\/civic-search\.js" onerror="document\.body\.classList\.add\('civic-boot-failed'\)">/.test(html), 'civic-search.js load failure flips the boot-failed state');
ok(current.includes('class="cs-boot-failed" role="alert"') && current.includes('<noscript>'), 'shell carries the reload row and the <noscript> fallback');
const googleFontLinks = [...head.matchAll(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/g)];
ok(googleFontLinks.length > 0 && googleFontLinks.every((m) => /media="print" onload=/.test(m[0]) || head.slice(Math.max(0, m.index - 12), m.index).includes('<noscript>')), 'decorative Google Fonts are not render-blocking (media=print swap or <noscript> only)');
ok(/assets\/css\/civic-search\.css/.test(head), 'civic stylesheet still linked in <head>');

// packs
const packsDir = join(ROOT, 'data/i18n');
const manifest = JSON.parse(readFileSync(join(packsDir, 'manifest.json'), 'utf8'));
const keys = Object.keys(civic.copy.ko).sort();
ok(JSON.stringify(Object.keys(civic.copy.en).sort()) === JSON.stringify(keys), 'bootstrap copy: en has exactly the ko keys');
for (const locale of manifest.supportedLocales) {
  const pack = JSON.parse(readFileSync(join(packsDir, manifest.files[locale]), 'utf8'));
  const c = pack.civic || {};
  const missing = keys.filter((k) => typeof c[k] !== 'string' || !c[k].trim());
  ok(missing.length === 0, `${locale}: civic pack carries every key${missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''}`);
  if (locale === 'ko' || locale === 'en') {
    const drift = keys.filter((k) => c[k] !== civic.copy[locale][k]);
    ok(drift.length === 0, `${locale}: civic pack equals the bootstrap copy in civic-search.js${drift.length ? ' (drift: ' + drift.join(', ') + ')' : ''}`);
  }
}

// journey + core tools contract in the shell
ok((current.match(/<button type="button" class="cs-route" data-cs-journey="(pre|post)" aria-expanded="false" aria-controls="civicJourneyPanel">/g) || []).length === 2, 'two journey triggers: real buttons with aria-expanded/aria-controls');
ok(current.includes('id="civicJourneyPanel" class="cs-journey-panel" hidden'), 'journey panel starts hidden (CLOSED)');
for (const href of ['form-helper.html', 'ai.html', 'new-home.html']) ok(new RegExp(`<a class="cs-tool" href="${href}"`).test(current), `core tool entry links to ${href}`);
ok(/<h2 id="csCoreTitle">/.test(current) && current.indexOf('csCoreTitle') < current.indexOf('csSupportTitle'), 'core tools precede supporting tools');
ok(current.indexOf('id="civicSearchForm"') < current.indexOf('class="cs-journey"') && current.indexOf('class="cs-journey"') < current.indexOf('csCoreTitle'), 'hierarchy: search → journey → core tools');

console.log(`\n[check_landing_shell] ${failures ? 'FAIL' : 'OK'} — ${passed}/${passed + failures} checks passed`);
process.exit(failures ? 1 : 0);
