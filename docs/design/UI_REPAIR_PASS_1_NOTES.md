# UI REPAIR PASS 1 NOTES

## What changed
- Added a **small CSS-only normalization layer** in `index.html` and `ai.html` to align visible tokens and hierarchy with `DESIGN.md`.
- Standardized focus-visible ring tone to emerald, and kept keyboard focus behavior intact.
- Reduced over-heavy visual emphasis in selected high-noise selectors (not globally destructive).
- Normalized key radii toward the 8/12/16/20/24 family for major cards/modals/search shells.
- Improved Korean readability in core text containers via `line-height: 1.68` and `word-break: keep-all`.
- Added safe overflow/wrapping guards for crowded metadata/chip/source areas, including 390px handling in `ai.html`.

## Why this is safe
- Patch is **CSS-only**; no backend, JSON, dependency, or API changes.
- No IDs, `data-action` hooks, modal overlays, or state-machine classes were removed.
- No feature paths were removed or hidden; warnings/sources/uncertainty states remain visible.
- No law-grounding behavior was enabled or modified.

## What was intentionally not changed
- No component redesign or layout rewrite.
- No JS rendering/control-flow changes.
- No restructuring of visa/document source data display logic.
- No copy changes that imply legal/official verification.

## Deferred to PR C / D / E
- PR C: deeper search-result/document/procedure readability restructuring.
- PR D: landing/hero/search-entry visual polish after Figma stabilizes.
- PR E: broader mobile 390px regression sweep and final density tuning.

## Manual QA targets
- Landing → searching → searched state continuity.
- Direct visa code search and keyword search.
- Theme toggle and language toggle visibility/operation.
- HiKorea guide modal open/close and action hooks.
- Paradiso.ai answer card + source panel readability on desktop and 390px.
- Keyboard-only navigation: focus ring visibility and tab order continuity.
