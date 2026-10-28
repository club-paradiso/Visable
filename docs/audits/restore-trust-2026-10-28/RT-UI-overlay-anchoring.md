# Restore Trust — P1 UI Reliability: language selector anchoring & global overlay audit (2026-10-28)

Scope: rendering/interaction only. No legal, immigration, or data content changed;
no protected data file touched.

## Task entry

| ID | Priority | Title | Status |
|---|---|---|---|
| RT-UI-01 | **P1** UI Reliability | KO language panel opens at the left screen edge instead of under the button | Fixed |
| RT-UI-02 | P1 (found during audit) | Arabic/RTL: language panel stranded ~219px from the mirrored button | Fixed (same root cause) |
| RT-UI-03 | P1 (found during audit) | After picking a language with the keyboard, focus fell to `<body>` instead of the trigger | Fixed |
| RT-UI-04 | P2 | Language listbox had no ↑/↓/Home/End navigation (Tab only) | Fixed |
| RT-UI-05 | P3 — manual review | Breakpoint mismatch: language panel becomes a sheet at ≤680px, theme picker at ≤600px (601–680px shows a theme popover next to a language sheet) | Logged, not changed |

Not raised to P0: the panel was misplaced, but it stayed fully operable (focus moved
into it, keyboard and mouse selection worked, Escape closed it). No reproduction blocked
the language feature or accessibility outright.

No pre-existing "Restore Trust" task list exists in the repository or in GitHub issues.
This file is the record for this item. Merge it into the master list when one is published.

## Reproduction (before)

Measured with Playwright (Chromium 1243) on `index.html`, the same build as production:

| Viewport | Trigger (x, y, w, h) | Panel (x, y, w, h) |
|---|---|---|
| 1440×900 | 1141, 24, 108, 44 | **0**, 76, 320, 560 |
| 1280×900 | 981, 24, 108, 44 | **0**, 76, 320, 560 |
| 900×800 | 637, 24, 108, 44 | **0**, 76, 320, 560 |
| 768×1024 | 505, 24, 108, 44 | **0**, 76, 320, 560 |
| 390×844 | (bottom sheet, correct) | 0, 152, 390, 692 |

The searched-result header showed the same defect (panel x = 0 at 1280/1024/768).
Screenshots: `screenshots/before-language-panel-{1280,768,390}.png`.

## Root cause

`assets/js/civic-search.js` opens the panel as a modal `<dialog>` (`showModal()`).
The UA stylesheet gives every `<dialog>` `inset-inline-start: 0; inset-inline-end: 0`.
The old code wrote only `top` and `right`, and `civic-search.css` fixes `width: 320px`
with `margin: 0`. That made the box over-constrained (left + width + right all set).
CSS 2 §10.3.7 then ignores `right` in LTR, so the panel sat at `left: 0`, the left edge
of the viewport. In RTL the browser ignores `left` instead. The panel was then
right-aligned to the viewport, not to the mirrored button. Hence RT-UI-02.

Causes checked and ruled out:

- **Portal / containing block.** The dialog sits in the top layer, so the viewport is its containing block. No ancestor `transform` or `filter` is involved.
- **`getBoundingClientRect()` and scroll offsets.** Correct, the y coordinate was right.
- **z-index and stacking context.** Top layer, correct.
- **Popover library.** None is used.

The theme picker worked only because its own copy of the placement code happened to
set `left: auto`. Each overlay had its own hand-rolled placement code with the same
latent defect. None of them did horizontal collision detection or followed the
trigger on scroll.

## Fix (common layer)

New shared primitive `assets/js/anchored-overlay.js` (`window.VisableOverlay`).
It loads before `visable-theme.js` on all 10 pages that use the header overlays.

- It writes **every** inset explicitly (`left`/`top` set, `right`/`bottom: auto`), so UA or skin rules can't over-constrain the box. It measures the panel only after it is displayed.
- **Alignment:** the panel is end-aligned with the trigger. Right edges line up in LTR; left edges line up in RTL.
- **Gap:** 8px between trigger and panel.
- **Collision:** a 12px viewport margin. The panel flips above the trigger when there is more room there. When it still doesn't fit, it gets a `max-height` and its list scrolls inside.
- `track()` re-places the panel on window resize, any (captured) scroll, and `visualViewport` resize, which covers pinch zoom. It returns a cleanup that runs on close.
- A `when()` predicate hands control back to the stylesheet's bottom sheet on narrow screens: ≤680px for language, ≤600px for theme. Resizing across the breakpoint while the panel is open switches between popover and sheet.

The fix doesn't hard-code coordinates or offsets. Consumers:

- the language dialog (`civic-search.js`): home and searched headers;
- the Civic theme picker `#vtCivicPop` (`visable-theme.js`);
- the in-header theme picker `#vtPop`, which ai.html, form-helper.html, new-home.html and nationality-interview-hub.html anchor under a header button. The floating pill keeps its stylesheet corner, unchanged.

Other changes:

- **RT-UI-03 (focus after a pick):** applying a language re-renders the header buttons before the dialog's async `close` event fires. The close handler now returns focus to the button that replaced the opener.
- **RT-UI-04 (listbox keys):** ↑/↓ move through the enabled languages, and ↓ from the filter enters the list. Home/End jump to the ends; inside the filter field they keep their caret behaviour.
- **Cache busting:** `visable-theme.js` and `civic-search.js` query versions bumped to `20261028-anchor`.

The i18n path is unchanged. Selection still goes through
`data-action="apply-language"` → `applyLanguage()`. Storage (`paradiso:language`),
the `?lang=` bootstrap, and `lang`/`dir` updates are the same as before.

## Global overlay audit

| Overlay | Before | After / note |
|---|---|---|
| Language selector, home header (`#csLangDialog`) | **Broken** (x = 0) on desktop/tablet | Anchored, tested |
| Language selector, searched header | **Broken** | Anchored, tested after scroll |
| Language selector, RTL | **Misaligned** | Anchored to the mirrored button |
| Language selector ≤680px (bottom sheet) | OK | Unchanged, full width, flush bottom |
| Civic theme picker `#vtCivicPop` | OK by accident; no scroll tracking | Shared anchoring; follows the trigger on scroll |
| In-header theme picker `#vtPop` (ai, form-helper, new-home, nationality hub) | OK by accident | Shared anchoring; verified 1280/768 |
| Floating theme pill (manual, checklists, enforcement, studios) | OK | Unchanged, stylesheet corner |
| Search suggestions `.cs-suggest` | OK: in flow under the search bar, same width | Not changed |
| Page dialog `#civicPageDialog` | Centered modal (UA default) | Not changed |
| Legacy `#languageMenu` (index.html) | Hidden under `civic-refresh` (not visible at any viewport) | Not changed |
| Global settings sheet, other modals | Not anchored to a trigger (full-screen or centered) | Not changed |

## Verification

New spec: `tests/e2e/overlay-anchoring.spec.mjs`. It runs 7 tests × 6 viewport
projects (1280, 768, 430, 390, 360, 320) and asserts the trigger/panel bounding-box
contract:

- the panel is adjacent (below, or above when flipped), end-aligned, and fully inside the viewport;
- ≤680px gets a full-width bottom sheet;
- the contract holds after a search plus scroll, and while scrolling with the panel open;
- resizing 1440 → 900 → 700 → 520 → 1200 with the panel open keeps the contract;
- Escape and backdrop click close it with focus returned, across 4 consecutive open/close cycles at an identical position;
- full keyboard flow: Enter opens, Home/End/↓ move, Enter picks; English is stored, the panel closes and focus returns;
- Arabic RTL;
- all 4 theme skins, including the theme picker's own anchoring.

Each run attaches screenshots. `PARADISO_VISUAL=1` also enables pixel comparison
(`--update-snapshots` writes the baselines). It is opt-in because baselines are
platform- and font-specific.

Browser zoom changes the CSS viewport width: 200% at 1280px ≈ 640px. The resize
sweep and the 320–430px projects cover that. `visualViewport` resize keeps the
popover attached during pinch zoom.

| Check | Result |
|---|---|
| `overlay-anchoring` + `language-control`, all 6 projects | 78 / 78 passed |
| `overlay-anchoring` on the **pre-fix** JS (desktop-1280) | 6 / 7 failed, as expected. The 1 passing test is the Escape/backdrop focus cycle, which already worked |
| Other 9 pages, theme picker at 1280/768/390 | Anchored or unchanged; no page errors |
| `bash scripts/check_repo.sh` | Exit 0; backend 99/99 modules (after installing `backend/requirements-dev.txt`) |
| Full E2E suite, desktop-1280 / tablet-768 / mobile-390 | See PR description |

After screenshots: `screenshots/after-language-panel-{1280,768,390}.png`.

## Open items for manual review

- **RT-UI-05:** unify the sheet breakpoints (600 vs 680px) in a design pass. Left as is, because each value is pinned by existing tests and theme-layout CSS.
- **Mobile sheets don't lock background scroll.** The theme sheet's own list uses `overscroll-behavior: contain`. A body-level lock is a design decision and was not added.
