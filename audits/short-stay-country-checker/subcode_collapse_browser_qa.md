# Subcode collapse/expand — browser QA (2026-06-11T07:56:00.591Z)

Environment: Playwright Chromium 141, http://127.0.0.1:8080, viewport 1280×900 & 375×720

- ✅ PASS — landing → first search (C-3) renders via real executeSearch flow
- ✅ PASS — C-3: broad search collapsed (0/11 full cards open, toggle present)
- ✅ PASS — C-3: 4 preview chips
- ✅ PASS — C-3: exactly one parent result card (no result-list flooding)
- ✅ PASS — B-2: small family compact (2 cards)
- ✅ PASS — B-2: exactly one parent result card (no result-list flooding)
- ✅ PASS — F-2: broad search collapsed (0/10 full cards open, toggle present)
- ✅ PASS — F-2: 4 preview chips
- ✅ PASS — F-2: exactly one parent result card (no result-list flooding)
- ✅ PASS — F-6: small family compact (3 cards)
- ✅ PASS — F-6: exactly one parent result card (no result-list flooding)
- ✅ PASS — D-2: broad search collapsed (0/8 full cards open, toggle present)
- ✅ PASS — D-2: 4 preview chips
- ✅ PASS — D-2: exactly one parent result card (no result-list flooding)
- ✅ PASS — D-10: small family compact (4 cards)
- ✅ PASS — D-10: exactly one parent result card (no result-list flooding)
- ✅ PASS — E-7: broad search collapsed (0/11 full cards open, toggle present)
- ✅ PASS — E-7: 4 preview chips
- ✅ PASS — E-7: exactly one parent result card (no result-list flooding)
- ✅ PASS — G-1: broad search collapsed (0/16 full cards open, toggle present)
- ✅ PASS — G-1: 4 preview chips
- ✅ PASS — G-1: exactly one parent result card (no result-list flooding)
- ✅ PASS — F-4: broad search collapsed (0/13 full cards open, toggle present)
- ✅ PASS — F-4: 4 preview chips
- ✅ PASS — F-4: exactly one parent result card (no result-list flooding)
- ✅ PASS — C-3: expand/collapse toggles via mouse with aria-expanded sync
- ✅ PASS — C-3: keyboard Enter expands the group
- ✅ PASS — C-3: toggle keeps a visible focus treatment (CSS :focus-visible)
- ✅ PASS — C-3-9: exact subcode lifted, visible, highlighted (not buried; 1 result card(s))
- ✅ PASS — C-3-4: exact subcode lifted, visible, highlighted (not buried; 2 result card(s))
- ✅ PASS — B-2-2: exact subcode lifted, visible, highlighted (not buried; 1 result card(s))
- ✅ PASS — D-2-6: exact subcode lifted, visible, highlighted (not buried; 1 result card(s))
- ✅ PASS — F-2-7: exact subcode lifted, visible, highlighted (not buried; 2 result card(s))
- ✅ PASS — G-1-5: exact subcode lifted, visible, highlighted (not buried; 1 result card(s))
- ✅ PASS — mobile 375px: no horizontal overflow (delta 0px)
- ✅ PASS — mobile 375px: tap targets ≥40px (btn 44, chip 44)
- ✅ PASS — B-2 search: short-stay checker section visible
- ✅ PASS — C-3 search: short-stay checker visible (tourist guidance CTA path)
- ✅ PASS — C-3 search: in-card checker CTA injected
- ✅ PASS — F-4 search: route guide section visible
- ✅ PASS — D-2 search: unrelated query keeps both tools hidden

## Console errors captured
- console.error: Failed to load resource: net::ERR_CERT_AUTHORITY_INVALID

(Note: `ERR_CERT_AUTHORITY_INVALID` is the PRE-EXISTING backend-first data fetch (`API_BASE/api/visas`, index.html:17607) being blocked by the sandbox TLS proxy; the page falls back to static `visa_data.json` as designed. Not introduced by this change.)
