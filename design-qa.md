# September search refresh — design QA

final result: passed

## Target and evidence

Selected option 1: `exec-7db25247-f432-484e-b4fa-e3d4f0ede894.png` (1487 × 1058).
Implementation: local home at `http://127.0.0.1:4174/`, Chrome viewport 1487 × 1058, device pixel ratio 1, Korean, light mode, no query. The source and final implementation were opened together in one comparison input. No browser frame or density normalization was needed.

Evidence is delivered in the task's `outputs` directory: `visable-home-final.png`, `visable-mobile-home-final.png`, `visable-mobile-search-final.png`, and `visable-form-helper-final.png`. The search capture used a static local server, so its existing unified-API fallback notice is expected; the original-PDF search itself succeeds independently.

## Iterations and fixes

1. Initial comparison found P2 typography and color drift: the heading was too small and a legacy theme overrode the white background. Increased the responsive heading and excluded the new home from the legacy background rule.
2. Revised comparison found P2 control/layout drift: the search button was narrow and the footer fell below the target viewport. Adjusted button padding and footer spacing. A focused search-button capture confirmed the Korean label, contrast, and font size.
3. Shared-surface inspection found P2 legacy gradients on the form helper. Scoped the civic theme override to its actual theme selectors. A new capture verifies white surfaces; a real dark-mode toggle verifies dark background and light foreground.
4. Mobile interaction inspection found the unused journey section visible below the initial home. Hid it until a journey button is selected, then rechecked that the pre-entry button reveals its real purpose choices.

The final home was compared again with the selected image at identical dimensions after the fixes. No remaining actionable P0/P1/P2 visual difference was found.

## Required fidelity surfaces

| Surface | Result |
| --- | --- |
| Fonts and typography | Loaded Pretendard; clear large headline, smaller supporting line, legible search label. Native font metrics differ slightly from the generated concept, with the intended hierarchy retained. |
| Spacing and layout | Same centered search, two journey rows, three utility columns, source strip, and footer. At 390 px, these stack without horizontal overflow. |
| Colors and tokens | White page, forest-green primary controls, pale green accents, restrained borders. Related tools share the same base tokens; semantic warning colors remain intact. |
| Image quality | Existing vector brand and licensed Lucide SVG icons remain sharp. No rasterized UI or missing assets. |
| Copy and content | Core concept copy retained. Each manual gets its own dated PDF link. Existing legal disclaimer remains complete. Other tools remain accessible through the service directory. |

## Interaction evidence and intentional differences

- Korean and English home states, exact code/alias search, parent-code search, source filtering, result tabs, empty state, original-page dialog, Escape dismissal, PDF page links, and landing reset were exercised.
- Mobile controls use at least 44 px targets and 16 px input text. Measured scroll width is 390 px at a 390 px viewport.
- All eight previous landing utilities remain reachable. Entry/stay routes reveal the original functional guide rather than a decorative card.
- Separate manual dates, unreviewed-source notices, and longer legal disclaimers are intentional product requirements. The concept did not specify result, error, or dialog states; these use the same visual system.
- Original text search is source retrieval, not approval of changed immigration requirements. Structured legal summaries retain their existing basis and review status.
