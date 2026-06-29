# Visable Aurora Mesh Hero Implementation

Status: implementation support
Figma source: `Visable by Paradiso · UX UI Workspace`, page `10 FINAL APPLIED · Landing System`
Branch: `design/visable-aurora-hero-20260629`

## What this adds

This change introduces the Figma-approved Visable landing background as code:

- `assets/css/visable-aurora-hero.css`
  - Aurora Mesh visual system
  - landing-only selectors
  - dark-mode styling
  - mobile fallback
  - `prefers-reduced-motion` fallback
- `assets/js/visable-aurora-hero.js`
  - injects the decorative background layer into `#hero`
  - loads the CSS file if it is not already linked
  - uses `requestAnimationFrame` throttling for pointer parallax and scroll depth
- `scripts/apply_visable_aurora_hero.mjs`
  - safe codemod to link the CSS and JS in `index.html`
- `package.json`
  - adds `npm run apply:visable-aurora-hero`

## Integration step

Run this once on the branch before final merge if `index.html` has not already been linked:

```bash
npm run apply:visable-aurora-hero
```

Expected result:

```html
<link id="visableAuroraHeroStylesheet" rel="stylesheet" href="assets/css/visable-aurora-hero.css?v=20260629">
<script src="assets/js/visable-aurora-hero.js?v=20260629" defer></script>
```

The script does not rewrite the hero markup. The JS file injects the decorative layer at runtime so the existing `header#hero`, `canvas#starCanvas`, body state machine, `data-action` handlers, and backend config stay untouched.

## UX constraints

- Use Aurora Mesh only on the landing hero.
- Do not apply it to search results, document checklist, source panels, or legal/manual reading surfaces.
- Keep official-source warnings and disclaimers visually prominent.
- Keep `prefers-reduced-motion` and mobile fallbacks.
- Keep pointer motion subtle. This is a visa platform, not a screensaver audition.

## QA checklist

After linking and serving locally:

```bash
npm run validate
npm run test:public-dummy
```

Manual checks:

1. Open `index.html` on desktop.
2. Confirm the hero shows Aurora Mesh background behind existing content.
3. Move the pointer over the hero and confirm subtle parallax.
4. Search for a visa/status code and confirm the decorative layer disappears outside landing state.
5. Test mobile viewport and confirm only the low-cost blobs remain.
6. Enable reduced motion in OS/browser and confirm parallax is effectively static.
