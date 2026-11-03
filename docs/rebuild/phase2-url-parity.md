# Phase 2 — URL status parity (source tree vs Vite build)

Date: 2026-11-03. Tool: `node scripts/check_url_parity.mjs` (serves `.` and `dist/` on local ports,
HEAD-requests every URL referenced from the shipped HTML, `assets/js/**` and the four runtime
`scripts/*.mjs`, compares status codes).

Result: **checked 218 URLs, status mismatches: 0.**
42 referenced paths already return 404 in the source tree (dead references in code or data strings,
pre-existing; unchanged by the build). They are not part of this rebuild's scope and are listed by
running the tool with `--json` after extending it, or by inspecting `test-results`; left as a Phase 7 note.

How the build keeps every URL:
- Pages: all 12 root HTML files are Vite entries at the same paths.
- `data/**`, `assets/**`, `agency-directory/**`, `docs/forms_official/**`, the two current manual PDFs,
  `scripts/employment_*.mjs`, `scripts/enforcement-ui.mjs`, `visa_data.json`, `doc_master.json` and the
  root Markdown files are copied verbatim into `dist/` (vite.config.mjs `STATIC_COPIES`).
- Local `<link rel="stylesheet">` tags are marked `vite-ignore` before Vite's HTML plugin runs, so the
  8 index.html stylesheets stay separate files in their original cascade order (first build attempt
  merged them into 3 chunks and moved `visable-product-2026.css` behind the others — reverted).
- Inline `<style>` blocks are parsed by Vite (asset `url()` rewrites to hashed copies) but not minified
  (`build.cssMinify: false`); `diff index.html dist/index.html` = 69 lines, all `url()`/favicon rewrites
  and the module `<script>` tag.
- Vercel: `vercel.json` gains `buildCommand: npm run build`, `outputDirectory: dist`, `installCommand`.
  `api/**` functions are unaffected (they live outside `dist`).
