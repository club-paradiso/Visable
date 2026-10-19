#!/usr/bin/env node
/*
 * build_search_suggest_index.mjs — derive the homepage autocomplete index.
 *
 * The home search suggests status codes, procedures and status × procedure
 * pairs while the user types. Fetching the 1.2 MB guidance bundle for that would
 * make the first keystroke wait on the whole corpus, so this script derives a
 * small index from it. Nothing here is authored: every code, name, procedure,
 * keyword, alias and per-code procedure state is copied from
 * data/status-guidance-202609.json (the canonical bundle), in the same shape
 * VisableStatusGuidance.interpret() reads, so the browser reuses the existing
 * interpreter instead of a second one.
 *
 *   node scripts/build_search_suggest_index.mjs          # rewrite the index
 *   node scripts/build_search_suggest_index.mjs --check  # CI: index is current
 *
 * Dropped from the bundle: guidance bodies, evidence, fees, overlays, and every
 * procedure state of UNVERIFIED (interpret() never offers those either).
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE = 'data/status-guidance-202609.json';
export const OUT = 'data/search-suggest-index.json';

export function buildIndex() {
  const raw = readFileSync(join(ROOT, SOURCE));
  const bundle = JSON.parse(raw.toString('utf8'));
  const codes = {};
  for (const [code, entry] of Object.entries(bundle.codes)) {
    const procedures = {};
    for (const [pid, st] of Object.entries(entry.procedures || {})) {
      if (st && st.s && st.s !== 'UNVERIFIED') procedures[pid] = { s: st.s };
    }
    codes[code] = { kind: entry.kind, parent: entry.parent || null, name_ko: entry.name_ko || '', name_en: entry.name_en || '', lifecycle: entry.lifecycle || 'active', procedures };
  }
  return {
    schema: 'visable.search-suggest-index/1',
    generated_by: 'scripts/build_search_suggest_index.mjs',
    generated_from: SOURCE,
    source_sha256: createHash('sha256').update(raw).digest('hex'),
    note: 'Derived, not authored. Regenerate after the guidance bundle changes.',
    procedures: bundle.procedures.map((p) => ({ id: p.id, domain: p.domain, ko: p.ko, en: p.en, keywords: p.keywords })),
    procedure_registry: (bundle.procedure_registry || []).map((r) => ({ procedure: r.procedure, context_requirement: r.context_requirement })),
    aliases: bundle.aliases.map((a) => ({ terms: a.terms, candidates: a.candidates })),
    families: {},
    codes,
  };
}

export function serialize(index) { return JSON.stringify(index) + '\n'; }

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const file = join(ROOT, OUT);
  const next = serialize(buildIndex());
  const current = existsSync(file) ? readFileSync(file, 'utf8') : '';
  if (process.argv.includes('--check')) {
    if (current !== next) { console.error(`[build_search_suggest_index] ${OUT} is stale — run: node scripts/build_search_suggest_index.mjs`); process.exit(1); }
    console.log(`[build_search_suggest_index] ${OUT} is current (${Buffer.byteLength(next)} bytes)`);
  } else if (current === next) console.log(`[build_search_suggest_index] ${OUT} already current`);
  else { writeFileSync(file, next); console.log(`[build_search_suggest_index] wrote ${OUT} (${Buffer.byteLength(next)} bytes)`); }
}
