#!/usr/bin/env node
// Measure what a Vercel git deployment would upload: every tracked file minus the
// patterns in .vercelignore (gitignore syntax, as Vercel applies it). Prints file
// count and bytes, by top-level directory. Used for the Phase 1 before/after record
// in docs/rebuild/STATUS.md. Read-only.
//
//   node scripts/measure_deploy_set.mjs            # with the current .vercelignore (if any)
//   node scripts/measure_deploy_set.mjs --no-ignore  # as if there were no .vercelignore
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const noIgnore = process.argv.includes('--no-ignore');
const files = execFileSync('git', ['ls-files', '-z'], { cwd: root }).toString().split('\0').filter(Boolean);

function globToRegExp(glob) {
  // gitignore-style: leading '/' anchors; trailing '/' means directory; '**' any depth; no leading slash → match at any depth.
  let g = glob.trim();
  let anchored = false;
  if (g.startsWith('/')) { anchored = true; g = g.slice(1); }
  const dirOnly = g.endsWith('/'); if (dirOnly) g = g.slice(0, -1);
  if (!anchored && !g.includes('/')) g = '**/' + g;
  const re = g.split('/').map((seg) => seg === '**' ? '(?:.*)' : seg.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]')).join('/').replace(/\(\?:\.\*\)\//g, '(?:.*/)?');
  return new RegExp('^' + re + (dirOnly ? '(?:/.*)?' : '(?:/.*)?') + '$');
}

const rules = [];
if (!noIgnore && fs.existsSync(path.join(root, '.vercelignore'))) {
  for (const line of fs.readFileSync(path.join(root, '.vercelignore'), 'utf8').split('\n')) {
    const t = line.trim(); if (!t || t.startsWith('#')) continue;
    const neg = t.startsWith('!');
    rules.push({ neg, re: globToRegExp(neg ? t.slice(1) : t) });
  }
}
function ignored(f) { let ig = false; for (const r of rules) if (r.re.test(f)) ig = !r.neg; return ig; }

let count = 0, bytes = 0; const byTop = new Map();
for (const f of files) {
  if (ignored(f)) continue;
  let size = 0; try { size = fs.statSync(path.join(root, f)).size; } catch { continue; }
  count += 1; bytes += size;
  const top = f.includes('/') ? f.split('/')[0] : '(root)';
  byTop.set(top, (byTop.get(top) || 0) + size);
}
const mb = (n) => (n / 1048576).toFixed(1) + ' MB';
console.log(`${noIgnore ? 'without' : 'with'} .vercelignore: ${count} files, ${mb(bytes)}`);
for (const [k, v] of [...byTop.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15)) console.log(`  ${mb(v).padStart(10)}  ${k}`);
