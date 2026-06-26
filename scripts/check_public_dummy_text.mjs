#!/usr/bin/env node
/*
 * Public-surface dummy / placeholder / legacy-wording regression guard.
 * -----------------------------------------------------------------------------
 * Companion to scripts/check_dummy_text.mjs (which scans the JSON DATA files +
 * the two HTML entry points for a curated provenance list). This guard widens
 * coverage to ALL shipped front-end entry files and the standalone JS/CSS
 * modules, and is the regression backstop requested for the Waymaker readiness
 * pass: forbidden dummy/professional-name/marketing-filler terms must never be
 * able to reach users.
 *
 * Two scans, by design — to catch real issues WITHOUT failing on legitimate
 * developer comments (the explicit requirement):
 *
 *  1) RENDERED scan (needs jsdom; self-skips if absent, like the repo's other
 *     DOM tests). Parses each HTML entry file, DROPS <script>/<style>/<template>/
 *     <noscript> and comments, then scans only the VISIBLE text + user-facing
 *     attribute VALUES (placeholder/title/aria-label/alt). Because <script> is
 *     dropped, a `// TODO` code comment never trips it; because we read attribute
 *     VALUES (not names), the `placeholder="…"` attribute itself never trips it.
 *     This surface is what an end user actually sees, so the full banned list
 *     (incl. dummy/placeholder/lorem/TODO/FIXME) applies here.
 *
 *  2) RAW scan (always runs, zero deps). Scans the raw bytes of every shipped
 *     front-end file (HTML + assets/js/*.js + assets/css/*.css) for ONLY the
 *     high-confidence terms that must never appear ANYWHERE user-shippable, not
 *     even in a comment: fake professional/agency names ("Mr. Visa", "행정사 검토")
 *     and "lorem ipsum". These are unambiguous — they have no legitimate use in
 *     this codebase — so scanning comments too is safe and intentional.
 *
 * Exit non-zero on any finding; print file + location + matched term.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

const HTML_ENTRY_FILES = ['index.html', 'ai.html', 'form-helper.html', 'new-home.html'];
const JS_CSS_DIRS = ['assets/js', 'assets/css'];

// [needle, reason] — ASCII matched case-insensitively; Hangul matched exactly.
// Applied to the RENDERED surface only (visible text + user-facing attrs).
const RENDERED_BANNED = [
  ['lorem ipsum', 'lorem ipsum filler'],
  ['lorem', 'lorem filler'],
  ['ipsum', 'ipsum filler'],
  ['dummy', 'dummy placeholder text'],
  ['placeholder text', 'placeholder filler text'],
  ['todo:', 'TODO marker rendered to users'],
  ['todo ', 'TODO marker rendered to users'],
  ['fixme', 'FIXME marker rendered to users'],
  ['mr. visa', 'fake professional/agency name'],
  ['mr.visa', 'fake professional/agency name'],
  ['mr visa', 'fake professional/agency name'],
  ['행정사 검토', 'private third-party reviewer credited as official'],
  ['사설 검토', 'private-review provenance (not official)'],
  ['민간 검토', 'private-review provenance (not official)'],
  ['민간 자문', 'private-advisory provenance (not official)'],
  ['보수적 자동 추출', 'raw auto-extraction diagnostic (reads as unfinished)'],
  ['확정하지 못했습니다', 'raw auto-extraction diagnostic (reads as unfinished)'],
  ['asdf', 'keyboard-mash placeholder'],
  ['qwerty', 'keyboard-mash placeholder'],
  ['xxxxx', 'XXXX placeholder'],
];

// Applied to RAW file bytes (incl. comments). Only unambiguous, never-legitimate
// terms — so we never fail on honest developer comments.
const RAW_BANNED = [
  ['lorem ipsum', 'lorem ipsum filler'],
  ['mr. visa', 'fake professional/agency name'],
  ['mr.visa', 'fake professional/agency name'],
  ['mr visa', 'fake professional/agency name'],
  ['행정사 검토', 'private third-party reviewer credited as official'],
  ['사설 검토', 'private-review provenance (not official)'],
  ['민간 검토', 'private-review provenance (not official)'],
  ['민간 자문', 'private-advisory provenance (not official)'],
];

const USER_FACING_ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];

const findings = [];

function matchNeedles(text, needles, file, where) {
  const lower = text.toLowerCase();
  for (const [needle, reason] of needles) {
    const idx = lower.indexOf(needle.toLowerCase());
    if (idx >= 0) {
      const snippet = text.slice(Math.max(0, idx - 25), idx + 45).replace(/\s+/g, ' ').trim();
      findings.push({ file, where, needle, reason, snippet });
    }
  }
}

/* ---------------------------------------------------------------- raw scan */
function collectFrontEndFiles() {
  const files = [];
  for (const rel of HTML_ENTRY_FILES) {
    if (fs.existsSync(path.join(repoRoot, rel))) files.push(rel);
  }
  for (const dir of JS_CSS_DIRS) {
    const abs = path.join(repoRoot, dir);
    if (!fs.existsSync(abs)) continue;
    for (const name of fs.readdirSync(abs)) {
      if (/\.(js|css)$/.test(name)) files.push(path.join(dir, name));
    }
  }
  return files;
}

let rawScanned = 0;
for (const rel of collectFrontEndFiles()) {
  const text = fs.readFileSync(path.join(repoRoot, rel), 'utf8');
  rawScanned++;
  matchNeedles(text, RAW_BANNED, rel, 'raw');
}

/* ----------------------------------------------------------- rendered scan */
let jsdom = null;
try {
  ({ JSDOM: jsdom } = await import('jsdom'));
} catch {
  jsdom = null;
}

let renderedScanned = 0;
if (jsdom) {
  for (const rel of HTML_ENTRY_FILES) {
    const abs = path.join(repoRoot, rel);
    if (!fs.existsSync(abs)) continue;
    renderedScanned++;
    const dom = new jsdom(fs.readFileSync(abs, 'utf8')); // scripts NOT executed by default
    const doc = dom.window.document;
    // Drop everything that is not part of the rendered, user-visible surface.
    doc.querySelectorAll('script, style, template, noscript').forEach((el) => el.remove());
    const visibleText = (doc.body && doc.body.textContent) || '';
    matchNeedles(visibleText, RENDERED_BANNED, rel, 'visible text');
    for (const attr of USER_FACING_ATTRS) {
      doc.querySelectorAll(`[${attr}]`).forEach((el) => {
        const v = el.getAttribute(attr);
        if (v) matchNeedles(v, RENDERED_BANNED, rel, `@${attr}`);
      });
    }
  }
} else {
  console.warn('[check_public_dummy_text] jsdom not installed — rendered-surface scan skipped (raw scan still ran). Run `npm install` for full coverage.');
}

/* ----------------------------------------------------------------- report */
if (findings.length) {
  console.error('[check_public_dummy_text] Forbidden dummy/placeholder/legacy wording on a public surface:');
  findings.slice(0, 80).forEach((f) => {
    console.error(` - ${f.file} :: ${f.where} -> "${f.needle}" (${f.reason}) :: ${f.snippet}`);
  });
  if (findings.length > 80) console.error(` - ... ${findings.length - 80} more`);
  process.exit(1);
}
console.log(`[check_public_dummy_text] OK — no forbidden public-surface wording (raw: ${rawScanned} files; rendered: ${renderedScanned} HTML files${jsdom ? '' : ' [jsdom skipped]'})`);
