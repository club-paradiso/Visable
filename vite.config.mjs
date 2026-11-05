// Vite multi-page build for Visable (docs/rebuild/DECISIONS.md ADR-008).
//
// Staged approach: the HTML pages are the entries; Vite bundles their
// <link rel="stylesheet"> and <script type="module"> references into hashed
// files. Everything else that the site serves by URL today (data JSON, the
// classic IIFE scripts under assets/js, fonts, PDFs, forms, the root JSON
// files) is copied verbatim into dist/ so every public path keeps working.
// Classic scripts move to hashed modules one at a time in Phase 3.
import { defineConfig } from 'vite';
import { cpSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';

const root = dirname(new URL(import.meta.url).pathname);

// Every HTML page at the repo root is an entry; URLs are unchanged.
const pages = readdirSync(root).filter((f) => f.endsWith('.html') && statSync(join(root, f)).isFile());

// Public paths that must exist byte-identical in dist/ (see phase0-inventory.md §A,
// phase0 data canon, .vercelignore). Directories are copied recursively.
const STATIC_COPIES = [
  'data',
  'assets',
  'agency-directory',
  'docs/forms_official',
  'docs/source-manuals/2026-10-19/visa_manual_261019.pdf',
  'docs/source-manuals/2026-11-02/stay_manual_261102.pdf',
  'scripts/employment_code_analyzer.mjs',
  'scripts/employment_work_relations.mjs',
  'scripts/employment_checklist.mjs',
  'scripts/employment_interpret_client.mjs',
  'scripts/enforcement-ui.mjs',
  'visa_data.json',
  'doc_master.json',
  'ATTRIBUTIONS.md',
  'THIRD_PARTY_NOTICES.md',
  'README.md',
  'DESIGN.md'
];

// Phase 2 keeps the CSS cascade byte-identical: every local <link rel="stylesheet">
// and every inline <style> is marked vite-ignore before Vite's HTML plugin runs, so the
// stylesheets stay separate files in their original order (the static copy above keeps
// them at assets/css/<name>.css?v=…). Inline <style> blocks are still parsed by Vite
// (url() rewriting to hashed assets) but not minified (build.cssMinify = false), so the
// cascade is unchanged. Hashed CSS bundles arrive in Phase 4 with the visual baselines (ADR-008).
function keepCssRaw() {
  return {
    name: 'visable-keep-css-raw',
    enforce: 'pre',
    transformIndexHtml: {
      order: 'pre',
      handler(html) {
        return html
          .replace(/<link\b([^>]*rel="stylesheet"[^>]*href="(?!https?:)[^"]+"[^>]*)>/g, (m, attrs) => attrs.includes('vite-ignore') ? m : `<link vite-ignore${attrs}>`);
      }
    }
  };
}

function copyStatic() {
  return {
    name: 'visable-copy-static',
    apply: 'build',
    closeBundle() {
      const out = resolve(root, 'dist');
      for (const rel of STATIC_COPIES) {
        const src = resolve(root, rel);
        if (!existsSync(src)) { this.warn(`static copy skipped, missing: ${rel}`); continue; }
        const dest = resolve(out, rel);
        mkdirSync(dirname(dest), { recursive: true });
        cpSync(src, dest, { recursive: true, force: true, dereference: true });
      }
    }
  };
}

export default defineConfig({
  root,
  appType: 'mpa',
  publicDir: false,
  plugins: [keepCssRaw(), copyStatic()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsInlineLimit: 0,
    cssMinify: false,
    modulePreload: false,
    rollupOptions: {
      input: Object.fromEntries(pages.map((p) => [p.replace(/\.html$/, ''), resolve(root, p)]))
    }
  },
  server: { port: 5173, strictPort: false },
  preview: { port: 4173 }
});
