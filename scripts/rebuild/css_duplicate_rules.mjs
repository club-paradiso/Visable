// Manual audit tool (Phase 4 of the frontend rebuild): exact-duplicate rule analysis over the
// index.html stylesheet cascade. A rule that appears twice with the same at-rule context, selector
// text and declarations can lose its earlier copy without any cascade change (the later copy wins
// in every case the earlier one did). Run from the repo root: node scripts/rebuild/css_duplicate_rules.mjs [--list]
// Uses postcss, which is present through vite's dependencies; not wired into CI.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module'; const postcss = createRequire(new URL('../../package.json', import.meta.url))('postcss');
const html = readFileSync('index.html', 'utf8');
const files = [...html.matchAll(/<link rel="stylesheet" href="(assets\/css\/[^"?]+)[^"]*"/g)].map((m) => m[1]);
const norm = (s) => s.replace(/\s+/g, ' ').trim();
const rules = []; // {file, ctx, selector, decls, important, node}
for (const file of files) {
  const root = postcss.parse(readFileSync(file, 'utf8'), { from: file });
  root.walkRules((rule) => {
    const ctx = [];
    for (let p = rule.parent; p && p.type === 'atrule'; p = p.parent) ctx.unshift(`@${p.name} ${norm(p.params)}`);
    const decls = rule.nodes.filter((n) => n.type === 'decl').map((d) => `${d.prop.trim()}:${norm(d.value)}${d.important ? ' !important' : ''}`);
    if (rule.nodes.some((n) => n.type === 'rule')) return; // nested rules: skip
    rules.push({ file, ctx: ctx.join(' > '), selector: norm(rule.selector), decls, important: decls.filter((d) => d.endsWith('!important')).length, line: rule.source.start.line });
  });
}
const byKey = new Map();
for (const r of rules) { const k = `${r.ctx}|${r.selector}|${r.decls.join(';')}`; (byKey.get(k) || byKey.set(k, []).get(k)).push(r); }
let dupRules = 0, dupDecls = 0, dupImportant = 0; const perFile = {};
for (const [k, list] of byKey) if (list.length > 1 && list[0].decls.length) {
  for (const r of list.slice(0, -1)) { dupRules++; dupDecls += r.decls.length; dupImportant += r.important; perFile[r.file] = (perFile[r.file] || 0) + 1; }
}
console.log(`rules ${rules.length}; exact duplicate rules (earlier copies, keep last): ${dupRules}; declarations ${dupDecls}; of which !important ${dupImportant}`);
console.log(perFile);
if (process.argv[2] === '--list') for (const [k, list] of byKey) if (list.length > 1 && list[0].decls.length) console.log(list.map((r) => `${r.file}:${r.line}`).join(' == '), '|', list[0].selector.slice(0, 80), '|', list[0].decls.length);
