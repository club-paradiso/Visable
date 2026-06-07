# UI Containment QA — overflow, sticky controls, grid density

Emergency UI **containment** pass (not a redesign) after the merged theme/UI
PRs. Scope is layout stability and readability only: no visa data, legal
content, source mappings, AI grounding, verification logic, backend, or
guidance meaning was touched. No new themes, no external dependencies.

## Method

Rendered the live `index.html` against the static `visa_data.json` fallback
(localhost) in headless Chromium (Playwright), Korean UI, in both
`civic_editorial` and `archive_diary`, at **desktop 1280px**, **tablet
landscape 1024px**, **tablet portrait 768px**, and **mobile 390px**.

For each code the harness opened the result card, exercised the `statusChange`
and `extension` procedure tabs (where the dense scenario/document grids live),
scrolled to mid-page and bottom, and asserted the failure conditions:
card-vs-card overlap, child-overflows-parent, horizontal page overflow,
sticky controls covering content, and the floating AI CTA covering
caution/source/disclaimer text.

Codes tested: **F-1, F-6, D-2, G-1-5, E-7** (the brief's set). Result:
**40/40 combinations clean** (5 codes × 4 viewports × 2 themes).

## What was broken (observed on live iPad screenshots + measured)

1. **Sticky top controls floated over content.** `#topCtrls` is
   `position: fixed; z-index: 100`, an independent layer above the sticky
   search header. On tablet/mobile it overlapped procedure tabs and section
   headers while scrolling (mobile measured overlap with the scenario grid).
2. **Scenario (procedure-variant) cards packed into 3–4 narrow columns.**
   `.manual-subcode-grid` used `minmax(min(190px,100%),1fr)` → **4 columns at
   1024px, 3 at 768px** for document-heavy cards (each carrying nested
   필수/조건부/공통 doc groups). Cramped and hard to scan.
3. **Required-document checklist too dense.** `.doc-checklist` went to
   `repeat(auto-fill, minmax(280px,1fr))` → up to **3 columns** on tablet,
   with heavy per-item chrome (border + shadow + padding).
4. **Long manual excerpts became oversized cards.** A long excerpt rendered as
   one `.doc-chk-item` ballooned into a giant block dominating the doc grid.
5. **Floating AI CTA could sit over the last content.** `.ai-fab` is fixed
   bottom-right (full-width bar at ≤640px) with no bottom clearance reserved.

## What was fixed (all in `index.html`)

A single appended, clearly-commented **"UI CONTAINMENT"** CSS block (placed
last so it wins on source order) plus two tiny layout-class additions in the
renderer. Token-based and theme-agnostic — no component is duplicated per
theme, all colors come from existing CSS variables.

1. **Scenario grid** — added a `manual-subcode-grid--docs` modifier class to
   the document-heavy variant grid (the simple sub-code chip grid is
   untouched). It is now **1 column on tablet/mobile, max 2 on desktop**
   (`@media (min-width:1025px)`), with `min-width:0; max-width:100%` on cards.
2. **Document checklist** — capped at **2 columns** from 640px up
   (`.manual-result .doc-checklist`), down from 3.
3. **Per-item weight** — `.manual-result .doc-chk-item` loses its drop shadow,
   trims padding, top-aligns, and wraps long text (`overflow-wrap:anywhere`).
   Critical (red) styling is preserved.
4. **Oversized excerpts** — items whose text exceeds ~80 chars get a
   `doc-chk-item--block` class (renderer) and **span the full row** as a light
   block instead of forming a lopsided giant card.
5. **Sticky controls** — on the searched view at `≤1024px`,
   `#topCtrls` becomes `position: absolute` so it scrolls away with the page
   top instead of permanently covering procedure tabs / headers. The sticky
   search header remains the persistent top bar.
6. **Floating AI CTA** — compact padding + `env(safe-area-inset-*)` docking at
   `≤1024px`, and `body.searched .results-area` reserves `padding-bottom` so
   the last card / caution / source block is never trapped beneath it.
7. **Long-text safety** — `min-width:0; overflow-wrap:anywhere` on subcode
   cards, doc groups, and procedure summaries to stop Korean text forcing
   horizontal overflow.

## What was intentionally NOT changed (containment, not redesign)

- No restructuring of components, DOM, or JS behavior (search, tabs, language,
  theme, AI handoff). Only two layout **class** additions in the renderer.
- The deliberate **full-width bottom AI bar at ≤640px** (`!important` rule) was
  left in place — measurements confirm it no longer traps critical content
  once `results-area` reserves bottom space. Copy is unchanged (the
  `Paradiso.ai` tag and labels stay).
- Source / verification badges, caution blocks, and the legal disclaimer were
  not restyled or de-emphasized — they remain the highest-contrast elements.
- No visa data, document requirements, procedure content, or AI/legal grounding
  changes. No new themes, no external assets.

## Viewports tested

Desktop 1280 · Tablet landscape 1024 · Tablet portrait 768 · Mobile 390.

## Codes tested

F-1 · F-6 · D-2 · G-1-5 · E-7 (Korean UI, both themes).

## Verification results

- Layout harness: **40/40 clean** — no card overlap, no child/parent or page
  horizontal overflow, no sticky-control coverage, no AI-CTA coverage of
  caution/source/disclaimer, in both themes at all four widths.
- `check_static_visa_result_cards.js` → OK
- `check_placeholder_suppression.js` → 19/19
- `check_exact_code_search.js` → 17/17
- `check_i18n.js` → OK · `check_ai_shell_semantics.js` → OK · audit → OK
- `bash scripts/check_repo.sh` → All regression checks passed (backend
  regression + AI golden eval green; `pdfinfo` page-count check skipped — tool
  not installed in env).

## Known remaining limitations

- On mobile (≤640px) the AI CTA is still a full-width bottom bar by the
  existing design; it is now safely docked (safe-area) with reserved content
  clearance, but a future pass could make it a compact corner pill if desired.
- Tablet-landscape scenario cards are intentionally single-column (these cards
  are document-heavy); a future enhancement could offer 2-up only when a card's
  content is short enough to fit without cramping.
- Pre-existing `civic_editorial` active-tab contrast (white-on-brand-green,
  AA-large only) is unrelated to layout and tracked separately in
  `POST_MERGE_THEME_QA.md`.
