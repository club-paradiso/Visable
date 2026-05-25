# Autocomplete Row Readability Fix

## Issue

A deployed visual check showed that the landing search autocomplete rows were still hard to read after typing a query such as `f` or `f-1`.

The visible failure was specific:
- autocomplete rows used a pale/white background;
- text and highlighted code fragments appeared low-contrast;
- rows visually collided with the dark hero background;
- the list was difficult to scan quickly.

## Scope

This patch directly targets the existing autocomplete selectors:

- `.auto-list`
- `.auto-list.active`
- `.auto-item`
- `.auto-item` descendants and highlighted fragments

It also improves recommended keyword chip contrast without changing data, backend logic, or search behavior.

## Manual QA checklist

- [ ] Open the deployed page or local `index.html`.
- [ ] Open the direct search / landing search overlay.
- [ ] Type `f`.
- [ ] Type `f-1`.
- [ ] Confirm autocomplete rows are dark, readable, and full-width.
- [ ] Confirm highlighted code fragments remain visible.
- [ ] Confirm hover/focus states are visible.
- [ ] Confirm recommended keyword chips remain readable.
- [ ] Confirm mobile width does not overflow.
- [ ] Search `제주 무사증` and confirm result cards still render.
- [ ] Confirm `visa_data.json` was not changed.

## Scope guardrails

- No backend changes.
- No `visa_data.json` changes.
- No legal or visa data content changes.
- No broad redesign.
- No new dependencies.
