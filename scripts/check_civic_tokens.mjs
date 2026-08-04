/*
 * check_civic_tokens.mjs
 * ----------------------------------------------------------------------------
 * Contrast guard for the sitewide civic token layer (Figma UX-10 › Spec /
 * Foundations, node 445:5).
 *
 * Why this file exists, separately from check_unified_search.mjs:
 *
 * The Foundations migration moved --bg0 / --bd / --t1 / --t2 / --ac / --cWk /
 * --cy and added --cta. Those are read by every screen in both themes, and the
 * WCAG floors the migration was required to hold (body AA 4.5:1, primary CTA
 * AAA 7:1) lived only in prose — in the handoff document and the design
 * contract.
 *
 * Prose does not hold. When the civic layer moved --ac from #0B7357 to
 * #177366, the unified-search layer aliases --ac, so its derived tint quietly
 * fell to 4.98:1 while every check in the repo stayed green. That regression
 * shipped. check_unified_search.mjs now computes that one ratio; this file does
 * the same for the sitewide tokens, so the palette cannot drift past its floors
 * unnoticed either.
 *
 * Everything here is computed from the shipped CSS in index.html. No expected
 * ratios are hardcoded — only the thresholds.
 *
 *   node scripts/check_civic_tokens.mjs
 * ----------------------------------------------------------------------------
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const indexHtml = readFileSync(join(REPO_ROOT, 'index.html'), 'utf8');

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (error) {
    failures.push(`${name}: ${error.message}`);
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message || 'assertion failed');
}

/* ------------------------------------------------------- colour math ------ */

function srgbToLinear(channel) {
  const x = channel / 255;
  return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
}

function relativeLuminance(hex) {
  const h = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

function contrastRatio(a, b) {
  const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// color-mix(in srgb, A p%, B) — the same straight sRGB average the browser computes.
function mixHex(a, b, percent) {
  const parse = (hex) => {
    const h = hex.replace('#', '');
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  };
  const [ra, ga, ba] = parse(a);
  const [rb, gb, bb] = parse(b);
  const p = percent / 100;
  const chan = (x, y) => Math.round(x * p + y * (1 - p));
  return '#' + [chan(ra, rb), chan(ga, gb), chan(ba, bb)]
    .map((v) => v.toString(16).padStart(2, '0')).join('');
}

/* ------------------------------------------------------- CSS reading ------ */

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Body of the first rule block whose selector matches exactly. */
function ruleBlock(selector) {
  const m = indexHtml.match(new RegExp('(?:^|\\n)' + escapeRe(selector) + '\\s*\\{([^}]*)\\}'));
  return m ? m[1] : null;
}

function varIn(block, prop) {
  if (!block) return null;
  const m = block.match(new RegExp('--' + escapeRe(prop) + '\\s*:\\s*([^;]+);'));
  return m ? m[1].trim() : null;
}

const CIVIC = ':root:not([data-theme="archive_diary"])';
const CIVIC_DARK = ':root:not([data-theme="archive_diary"]) body[data-theme="dark"]';
const BASE_DARK = '[data-theme="dark"]';

const civicBlock = ruleBlock(CIVIC);
const civicDarkBlock = ruleBlock(CIVIC_DARK);
const baseDarkBlock = ruleBlock(BASE_DARK);

const isHex = (v) => /^#[0-9a-f]{6}$/i.test(v || '');

/**
 * Resolve a token the way the cascade does. Light reads the civic :root layer.
 * Dark reads the base dark theme on top of it, then the civic dark override on
 * top of that — custom properties inherit, so the innermost declaration wins.
 */
function token(name, theme) {
  if (theme === 'light') return varIn(civicBlock, name);
  return varIn(civicDarkBlock, name)
      ?? varIn(baseDarkBlock, name)
      ?? varIn(civicBlock, name);
}

/* ------------------------------------------------- the shipped mapping ---- */

// Figma UX-10 › Spec / Foundations. Locked so a silent palette swap fails here
// rather than in a screenshot nobody takes.
const FOUNDATIONS = {
  bg0: '#F7F4EF',   // PAPER
  bg1: '#FFFCF5',   // CARD_LIGHT
  bd:  '#E6E6EE',   // LINE
  t1:  '#1C1F29',   // DARK
  t2:  '#4D5261',   // GREY
  ac:  '#177366',   // EMERALD_TXT
  cta: '#0B4F44',   // EMERALD_DEEP — introduced by the migration
  cWk: '#F2C879',   // AMBER
  cy:  '#D95C47',   // CORAL
};

check('the civic layer carries every Foundations token', () => {
  assert(civicBlock, `could not find the ${CIVIC} rule block`);
  for (const [name, expected] of Object.entries(FOUNDATIONS)) {
    const got = token(name, 'light');
    assert(isHex(got), `--${name} is missing or not a hex literal (got ${got})`);
    assert(got.toUpperCase() === expected,
      `--${name} is ${got}, but Foundations specifies ${expected}. If this change is ` +
      `intended, update FOUNDATIONS here and re-check the ratios below.`);
  }
});

check('the alternate archive_diary theme is not dragged along', () => {
  // Foundations is explicit that archive_diary is a separate palette. The
  // :not() in the scope selector is the only thing keeping it out.
  assert(civicBlock, 'civic block missing');
  assert(indexHtml.includes(CIVIC),
    'the civic token layer must stay scoped with :not([data-theme="archive_diary"])');
});

/* ---------------------------------------------------- contrast floors ---- */

// [label, foreground, background, threshold]
function pairsFor(theme) {
  const T = Object.fromEntries(
    Object.keys(FOUNDATIONS).map((k) => [k, token(k, theme)]));
  return {
    tokens: T,
    pairs: [
      ['body text on page background',   T.t1, T.bg0, 4.5],
      ['body text on card surface',      T.t1, T.bg1, 4.5],
      ['muted text on page background',  T.t2, T.bg0, 4.5],
      ['muted text on card surface',     T.t2, T.bg1, 4.5],
      ['accent text on card surface',    T.ac, T.bg1, 4.5],
      // Foundations asks for AAA here specifically: this is the one control a
      // user must never fail to see.
      ['white on the primary CTA',   '#FFFFFF', T.cta, 7.0],
      // The raw hues are graphical tones. What is actually read is the derived
      // ink, mixed toward --t1 by the ratios declared in the same block.
      ['derived error ink on surface',   mixHex(T.cy, T.t1, 62),  T.bg1, 4.5],
      ['derived warning ink on surface', mixHex(T.cWk, T.t1, 38), T.bg1, 4.5],
    ],
  };
}

for (const theme of ['light', 'dark']) {
  check(`${theme}: every civic text pair clears its WCAG floor`, () => {
    const { tokens, pairs } = pairsFor(theme);
    for (const [name, value] of Object.entries(tokens)) {
      assert(isHex(value), `${theme} --${name} did not resolve to a hex literal (got ${value})`);
    }
    for (const [label, fg, bg, threshold] of pairs) {
      const ratio = contrastRatio(fg, bg);
      assert(ratio >= threshold,
        `${theme}: ${label} is ${ratio.toFixed(2)}:1 (${fg} on ${bg}) — below ${threshold}:1.`);
    }
  });
}

check('the derived error and warning inks are actually mixed toward the text colour', () => {
  // The ratios above are only meaningful if these declarations still exist. If
  // someone replaces --color-error with the raw hue, the pair check above would
  // keep measuring a mix that the CSS no longer performs.
  for (const [prop, hue, pct] of [['color-error', 'cy', 62], ['color-warning', 'cWk', 38]]) {
    const decl = varIn(civicBlock, prop);
    assert(decl, `--${prop} is missing from the civic layer`);
    const m = decl.match(new RegExp(
      'color-mix\\(in srgb,\\s*var\\(--' + hue + '\\)\\s*(\\d+)%,\\s*var\\(--t1\\)\\s*\\)'));
    assert(m, `--${prop} must stay a color-mix of var(--${hue}) toward var(--t1); got "${decl}"`);
    assert(Number(m[1]) === pct,
      `--${prop} mixes ${m[1]}% but the contrast above is computed at ${pct}%`);
  }
});

check('the raw warning and error hues are never used as text colour', () => {
  // --cWk is 1.54:1 against the card surface. That is fine for a 4px rule or a
  // tint behind --t1 text, and unreadable as type. This is the invariant that
  // keeps the pair table above honest, so it is asserted rather than assumed.
  for (const hue of ['cWk', 'cy']) {
    const direct = indexHtml.match(new RegExp('color:\\s*var\\(--' + hue + '\\)', 'g'));
    assert(!direct,
      `--${hue} is used directly as a text colour (${direct && direct.length} time(s)). ` +
      `Use the derived --color-${hue === 'cy' ? 'error' : 'warning'} ink instead.`);
  }
});

check('the primary CTA colour is not hardcoded past its token', () => {
  // Foundations: "주 CTA 배경은 새 변수로만 쓴다. 하드코딩된 #0B4F44 를 남기지 않는다."
  const hits = indexHtml.match(/#0B4F44/gi) || [];
  const declared = (indexHtml.match(/--(?:cta|ac2):\s*#0B4F44/gi) || []).length;
  assert(hits.length === declared,
    `#0B4F44 appears ${hits.length} time(s) but only ${declared} are token declarations — ` +
    `the rest are hardcoded. Use var(--cta).`);
});

/* ----------------------------------------------------------- report ------ */

if (failures.length) {
  console.error(`\nFAIL — ${failures.length} check(s) failed, ${passed} passed:\n`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`civic-tokens: ${passed} checks passed`);
