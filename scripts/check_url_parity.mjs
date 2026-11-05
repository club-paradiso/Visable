#!/usr/bin/env node
// URL parity between the source tree and the Vite build output (Phase 2 exit criterion:
// "no URL returns a different status than before"). Collects every relative URL the shipped
// HTML and JS reference (pages, assets, data, scripts, docs, root JSON), serves both trees on
// local ports and compares HTTP status codes. Read-only; exits 1 on any mismatch.
//
//   node scripts/check_url_parity.mjs            # source (.) vs dist/
//   node scripts/check_url_parity.mjs --json     # machine-readable report
import { spawn } from 'node:child_process';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(new URL('..', import.meta.url).pathname);
const dist = join(root, 'dist');
if (!existsSync(dist)) { console.error('dist/ missing — run npm run build first'); process.exit(2); }

const pages = readdirSync(root).filter((f) => f.endsWith('.html') && statSync(join(root, f)).isFile());
// Shipped code only: the pages, assets/js, and the scripts/*.mjs files the pages load at runtime
// (the rest of scripts/ is Node tooling that never runs in the browser).
const RUNTIME_SCRIPTS = ['scripts/employment_code_analyzer.mjs', 'scripts/employment_work_relations.mjs', 'scripts/employment_checklist.mjs', 'scripts/employment_interpret_client.mjs', 'scripts/enforcement-ui.mjs'];
const sources = [...pages.map((p) => join(root, p)), ...walk(join(root, 'assets/js')), ...RUNTIME_SCRIPTS.map((p) => join(root, p)).filter(existsSync)];
// Only quoted strings and attribute values count as URL references; a path inside a code
// comment such as "(scripts/check_x.mjs)" is documentation, not a URL the site serves.
const urlRe = /["'=](\.\/)?((?:assets|data|docs|scripts|agency-directory)\/[A-Za-z0-9_./@%+-]+|[A-Za-z0-9_-]+\.(?:html|json|md|pdf|svg|png|webp|jpg|ico|txt|xml))(?=["'?#\s])/g;
const urls = new Set(pages.map((p) => '/' + p));
urls.add('/');
for (const f of sources) {
  const text = readFileSync(f, 'utf8');
  for (const m of text.matchAll(urlRe)) {
    const u = m[2];
    if (/\$\{|\{|\}/.test(u)) continue;             // template expressions
    if (/^(data|docs|scripts|assets|agency-directory)\/$/.test(u)) continue;
    urls.add('/' + u);
  }
}
const list = [...urls].sort();

function walk(dir) { if (!existsSync(dir)) return []; const out = []; for (const e of readdirSync(dir)) { const p = join(dir, e); const s = statSync(p); if (s.isDirectory()) out.push(...walk(p)); else out.push(p); } return out; }
function serve(dirPath, port) { return spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', dirPath], { stdio: 'ignore' }); }
async function waitUp(port) { for (let i = 0; i < 100; i++) { try { const r = await fetch(`http://127.0.0.1:${port}/`, { method: 'HEAD' }); if (r.status) return; } catch {} await new Promise((r) => setTimeout(r, 100)); } throw new Error('server did not start on ' + port); }
async function status(port, u) { try { const r = await fetch(`http://127.0.0.1:${port}${encodeURI(u)}`, { method: 'HEAD', redirect: 'manual' }); return r.status; } catch (e) { return 'ERR'; } }

const A = 4351, B = 4352;
const sa = serve(root, A), sb = serve(dist, B);
try {
  await waitUp(A); await waitUp(B);
  const rows = [];
  for (const u of list) rows.push({ url: u, source: await status(A, u), dist: await status(B, u) });
  const mismatches = rows.filter((r) => r.source !== r.dist);
  const missingInSource = rows.filter((r) => r.source === 404).length;
  if (process.argv.includes('--json')) console.log(JSON.stringify({ checked: rows.length, mismatches }, null, 2));
  else {
    console.log(`checked ${rows.length} URLs referenced by the shipped HTML/JS (source vs dist)`);
    console.log(`  already 404 in source (dead references): ${missingInSource}`);
    console.log(`  status mismatches: ${mismatches.length}`);
    for (const r of mismatches) console.log(`    ${r.url}  source=${r.source}  dist=${r.dist}`);
  }
  process.exitCode = mismatches.length ? 1 : 0;
} finally { sa.kill(); sb.kill(); }
