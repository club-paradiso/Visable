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
 *  6. search-first hierarchy: one primary search field that is a WAI-ARIA
 *     combobox (listbox, live status, clear button), editorial examples (not
 *     "popular"), compact tools, then sources/disclaimer; the pre-entry /
 *     post-entry journey cards are gone and the purpose pickers they used to
 *     open sit in a hidden browse panel reached from the directory;
 *  7. the suggestion engine is loaded before civic-search.js and its derived
 *     index (data/search-suggest-index.json) is current with the guidance bundle.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadCivic, renderShellBlock, START, END } from './build_landing_shell.mjs';
import { buildIndex, serialize, OUT as SUGGEST_INDEX } from './build_search_suggest_index.mjs';

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

// search-first contract in the shell
const at = (needle) => current.indexOf(needle);
ok(!/class="cs-route\b|class="cs-journey"|class="cs-routes"/.test(current), 'the pre-entry / post-entry journey cards are gone from the home');
ok(!/한국 입국 전|한국 입국 후/.test(current), 'no "한국 입국 전 / 한국 입국 후" card copy remains in the shell');
const input = (current.match(/<input id="civicQuery"[^>]*>/) || [''])[0];
ok(/role="combobox"/.test(input) && /aria-autocomplete="list"/.test(input) && /aria-expanded="false"/.test(input) && /aria-controls="civicSuggest"/.test(input), 'the search field is a combobox (aria-autocomplete=list, aria-expanded=false, aria-controls=civicSuggest)');
ok(/autocomplete="off"/.test(input) && /maxlength="300"/.test(input) && /enterkeyhint="search"/.test(input), 'the field keeps autocomplete off, a length cap and a search enter key');
ok((current.match(/id="civicQuery"/g) || []).length === 1 && (current.match(/role="search"/g) || []).length === 1, 'exactly one primary search field on the home');
ok(/<div class="cs-suggest" hidden>/.test(current) && /<ul id="civicSuggest" class="cs-suggest-list" role="listbox" aria-label="[^"]+"><\/ul>/.test(current), 'suggestion listbox exists, starts empty and hidden (no empty panel paints)');
ok(/role="status" aria-live="polite" data-cs-suggest-status/.test(current), 'a polite live region announces the suggestion count');
ok(/<button type="button" class="cs-clear" data-cs-clear aria-label="[^"]+" hidden>/.test(current), 'clear button is labelled and hidden until there is text');
const examples = [...current.matchAll(/<button type="button" data-cs-query="([^"]+)">/g)].map((m) => m[1]);
ok(examples.length >= 3 && examples.length <= 5, `a restrained set of example searches (${examples.length})`);
ok(/class="cs-examples" role="group" aria-labelledby="csExamplesLabel"/.test(current) && !/자주 찾는|인기|popular/i.test(current.slice(at('class="cs-examples"'), at('class="cs-basis"'))), 'examples are a labelled group and do not claim popularity');
ok(/<a class="cs-example-link" href="form-helper\.html">/.test(current), 'the integrated application example opens Form Helper directly');
for (const href of ['form-helper.html', 'ai.html', 'new-home.html', 'manual.html']) ok(new RegExp(`<a class="cs-tool" href="${href}"`).test(current), `tool entry links to ${href}`);
for (const action of ['open-hikorea-guide', 'open-jurisdiction-modal']) ok(new RegExp(`<button type="button" class="cs-tool" data-action="${action}"`).test(current), `tool entry opens ${action}`);
ok((current.match(/class="cs-tool"/g) || []).length === 7, 'seven tools, in one secondary grid');
ok(at('<h1>') < at('id="civicSearchForm"') && at('id="civicSearchForm"') < at('class="cs-examples"') && at('class="cs-examples"') < at('id="csCoreTitle"') && at('id="csCoreTitle"') < at('class="cs-source-strip"') && at('class="cs-source-strip"') < at('class="cs-footer"'), 'hierarchy: headline → search → examples → tools → sources → disclaimer');
ok(/<footer class="cs-footer">[\s\S]*Visable은 공식 정부 서비스가 아닙니다/.test(current), 'the not-a-government-service disclaimer stays in the shell');
ok(/visa_manual_261019\.pdf/.test(current) && /stay_manual_261019\.pdf/.test(current) && (current.match(/2026\.10\.19/g) || []).length >= 2, 'official source PDFs and their basis dates stay on the home');
ok(/<section id="civicBrowsePanel" class="cs-browse" aria-labelledby="csBrowseTitle" hidden>/.test(current) && at('class="cs-directory"') < at('id="civicBrowsePanel"'), 'the purpose pickers live in a hidden browse panel after the directory');
ok(/<button type="button" data-action="reveal-home-section" data-target="visaManualSection" aria-controls="civicBrowsePanel" aria-expanded="false"[^>]*>/.test(current), 'the directory entry still reaches the purpose pickers (reveal-home-section → browse panel)');
ok((current.match(/<button type="button" data-cs-journey="(pre|post)" aria-pressed="false">/g) || []).length === 2, 'browse panel tabs switch tracks (aria-pressed)');

// suggestion engine wiring
const suggestTag = html.indexOf('<script defer src="assets/js/search-suggest.js"></script>');
ok(suggestTag > 0 && suggestTag < html.indexOf('<script defer src="assets/js/civic-search.js"'), 'search-suggest.js loads (deferred) before civic-search.js');
let indexCurrent = false;
try { indexCurrent = readFileSync(join(ROOT, SUGGEST_INDEX), 'utf8') === serialize(buildIndex()); } catch (e) { indexCurrent = false; }
ok(indexCurrent, `${SUGGEST_INDEX} is current with the guidance bundle (run: node scripts/build_search_suggest_index.mjs)`);

console.log(`\n[check_landing_shell] ${failures ? 'FAIL' : 'OK'} — ${passed}/${passed + failures} checks passed`);
process.exit(failures ? 1 : 0);
