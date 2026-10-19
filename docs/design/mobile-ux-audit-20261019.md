# Mobile search and result reading: audit and changes (2026-10-19)

Scope: the home search and the result page at phone widths (≤ 680 px). This is
rendering and interaction work only. No immigration content, dataset or
disclaimer changed.

Screenshots: [`screenshots/mobile-ux-20261019/`](screenshots/mobile-ux-20261019/).
`before-*` were captured on main @ 7b6e68f with an iPhone 13 profile; `after-*` show this change.

## What was wrong on a phone

| Where | Problem |
|---|---|
| Home, typing | Headline and subtitle filled about 45 % of the screen. With the on-screen keyboard open, only one or two suggestions were visible. Each suggestion used three lines: a type badge, the label and a sub line. |
| Home, tools | Tool descriptions were cut to one line with "…". |
| Result header | When focused, the search bar drew a second box inside itself plus a second, blue browser × next to our ×. The header (125 px, sticky) stayed on screen for the whole read. |
| Result body | "수정" was a 28 px-wide target, and "이 자격·업무의 원문 읽기 →" was 17 px tall. "다음 할 일" was a row of inline text links. Field labels were 12 px. |

## The idea: a search sheet

On a phone, tapping the field turns the home into a search sheet:

- The brand and the headline fold away, and the field moves to the top.
- A **닫기** (close) button sits beside the field.
- Examples (empty field) or suggestions (typing) fill the space above the keyboard.

The sheet closes only on an explicit act: **닫기**, Escape on an empty field, or a search. It never closes on blur, so a tap that moves focus cannot reflow the page under the finger.

The same reading carries through to the results:

- **Suggestion rows:** one label line plus one quiet line that starts with the type ("절차 · 입국 후 · 체류"). Rows are at least 56 px tall. Six rows fit above the keyboard on an iPhone 13; before, one or two did.
- **Keyboard hints:** "Enter / Esc" hints are not drawn on touch-only screens.
- **Submit in the sheet:** the keyboard's search key is the main submit. The bar keeps a compact 44 px search button, with its label kept for screen readers.
- **Result header:**
  - One box and one ×; the input's own focus ring and the browser's built-in clear button are removed.
  - The header slides away while reading down and returns on any upward scroll or when focus enters it. Reduced motion is respected.
- **Result body:**
  - "다음 할 일" becomes full-width rows (at least 52 px, with a chevron that mirrors in RTL).
  - "수정" and the manual-reader link are at least 44 px.
  - Field and fee labels are 13 px.
- **Tools:** descriptions get two lines instead of one cut-off line.

Desktop and tablet layouts are unchanged; every rule sits inside `@media (max-width: 680px)`.

## Not done

- No bottom tab bar or floating button: one primary action is enough for this site.
- No new colours, gradients or motion beyond the header slide.

## Verification

`tests/e2e/search-first-home.spec.mjs` covers the following on the 320–430 phone projects:

- The sheet opens and closes, and 닫기 keeps the typed text.
- At least four suggestions fit in the top 60 % of the screen, and the type shows inline.
- The compact submit button is at least 44 px.
- A search from the sheet leaves the sheet.
- The header hides on scroll down and returns on scroll up or focus.
- Next-step rows are at least 48 px and full width.
- The result bar draws a single box.

There is no horizontal overflow at 320 px in light mode, dark mode, or Arabic (RTL).
