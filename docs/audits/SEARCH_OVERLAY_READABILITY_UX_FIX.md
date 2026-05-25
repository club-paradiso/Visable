# Search Overlay Readability UX Fix

## Issue

A deployed UI check showed that opening the landing search overlay and typing a query such as `f-1` made the related search/autocomplete rows difficult to read. The rows appeared washed out, inconsistent in width, and visually collided with the dark hero artwork.

## Scope

This pass is intentionally narrow:

- Improve the readability of autocomplete/search suggestion containers and rows.
- Normalize suggestion row width, spacing, contrast, and hover/focus states.
- Improve recommended keyword chip contrast.
- Preserve current data, search logic, branding, and layout architecture.

## Changed area

- `index.html`
  - Added additive CSS overrides for common search/autocomplete/suggestion containers.
  - Added light/dark theme CSS variables for suggestion surfaces.
  - Added mobile overflow protection for suggestion panels.

## Manual QA checklist

- [ ] Open `index.html`.
- [ ] Click search start/direct search.
- [ ] Type `f-1`.
- [ ] Confirm related suggestions are readable.
- [ ] Confirm suggestion rows have consistent width.
- [ ] Confirm hover/focus states are visible.
- [ ] Confirm dark mode remains readable.
- [ ] Confirm mobile width does not overflow.
- [ ] Search `제주 무사증` and confirm result cards still render.
- [ ] Confirm `visa_data.json` was not changed.

## Scope guardrails

- No backend changes.
- No `visa_data.json` changes.
- No legal or visa data content changes.
- No broad redesign.
- No new dependencies.
