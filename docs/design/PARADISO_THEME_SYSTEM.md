# Paradiso Theme System

How Paradiso ships multiple visual themes from a single set of components, using
CSS custom properties only. No component is forked or duplicated; no external
CDN is added; no existing JS behavior changes.

---

## 1. Theme names & roles

| Theme | Role | Mood |
|-------|------|------|
| `civic_editorial` | **Default** | Warm civic-editorial paper interface — public-service trust + youthful Korean editorial rhythm. |
| `archive_diary` | Optional alternate | Soft civic-paperwork "archive diary" — cream paper, ivory cards, warm gray-brown borders, brown-black ink, restrained blue links, muted green for verified sources, muted red for cautions, soft yellow highlights. |

## 2. Two independent axes (important)

Paradiso has **two orthogonal visual axes**, on **two different elements**:

| Axis | Element | Attribute | Values | Owner |
|------|---------|-----------|--------|-------|
| **Style theme** (this system) | `<html>` (root) | `data-theme` | `civic_editorial` \| `archive_diary` | new, this PR |
| **Brightness** (pre-existing) | `<body>` | `data-theme` | `light` \| `dark` | unchanged |

The two value-spaces are disjoint and live on different elements, so they never
collide in selectors:

- Existing brightness rules (`[data-theme="dark"]`, `body[data-theme="dark"]`)
  only ever match `<body>` (value `dark`/`light`).
- New style-theme rules (`:root[data-theme="archive_diary"]`) only ever match
  `<html>` (value `civic_editorial`/`archive_diary`).

All existing JS reads `document.body.getAttribute('data-theme')` for brightness;
the root attribute is exclusively the style theme. This satisfies the brief's
"root-level `data-theme`" requirement without disturbing the heavily-used
brightness mechanism documented in `DESIGN.md`.

## 3. `data-theme` strategy

- Default markup: the bootstrap script (see §5) sets
  `document.documentElement.setAttribute('data-theme', …)` to the persisted
  theme, or `civic_editorial` if none.
- Theme rules are written as `:root[data-theme="<name>"]`. The attribute
  selector raises specificity above bare `:root`, so theme tokens win over the
  base regardless of source order — robust against the many `:root` blocks in
  `index.html`.

## 4. CSS variable strategy

Components already consume a stable token vocabulary:

- **Foundational:** `--bg0..3`, `--bgI`, `--bd/--bd2/--bd3`, `--t1/--t2/--t3`,
  `--ac/--ac2`, `--acG/--acL`, `--cy/--cyL`, `--hlB/--hlT`.
- **Semantic:** `--color-primary*`, `--color-accent*`, `--color-surface*`,
  `--color-text*`, `--color-border`, `--color-success/warning/error`.
- **Surfaces/CTA:** `--result-page-bg`, `--p-paper-surface*`,
  `--color-primary-green*`, `--p-emerald*`, `--ui-*`.

A theme overrides **only the foundational + key semantic tokens.** Many derived
tokens use `color-mix()` over the foundational ones (e.g.
`--result-surface: color-mix(in srgb, var(--bg1) 98%, white)`); because custom
properties resolve at point of use, those recompute automatically from the
themed base. This is why `archive_diary` needs a small override block, not a
full re-skin.

- `civic_editorial` carries **no token overrides** — it *is* the canonical
  `:root` palette. This guarantees the shipped default never regresses. It sets
  only a `--paradiso-theme` marker.
- `archive_diary` overrides the warm-cream/brown-black/blue/muted-green palette.

Both blocks live in one clearly-commented section in `index.html`
(`PARADISO EDITORIAL THEME SYSTEM`).

## 5. localStorage behavior

- Key: `paradiso:editorial-theme`. Values: `civic_editorial` | `archive_diary`.
- **Read before paint:** an inline `<head>` bootstrap sets the root attribute
  from `localStorage` (try/catch, defaults to `civic_editorial`) to avoid a
  flash of the wrong theme.
- **Init:** `applyEditorialTheme(getStoredEditorialTheme(), {persist:false})`
  runs on `DOMContentLoaded`.
- **On change:** `applyEditorialTheme(theme)` persists the new value.
- Brightness (light/dark) persistence is unchanged by this PR.

## 6. Token categories (what a theme may set)

A theme block should set, at most:

1. Surfaces — `--bg0..3`, `--bgI`, `--color-surface*`, `--result-page-bg`,
   `--p-paper-surface*`.
2. Ink — `--t1/--t2/--t3`, `--color-text*`, `--p-ink*`.
3. Borders/lines — `--bd*`, `--color-border`, `--p-line*`.
4. Accent/links — `--ac/--ac2`, `--acG/--acL`, `--color-accent*`,
   `--ui-focus`.
5. Status — `--color-success/warning/error`, `--cSt/--cNh/--cIn/--cFq/--cWk`.
6. Highlight — `--hlB/--hlT`, `--cy/--cyL`.
7. CTA — `--color-primary-green*`, `--p-emerald*`, `--shadow-cta*`.

Do **not** set: type scale, spacing, radius, or font tokens — those are shared
across themes and live in the base `:root`.

## 7. Component mapping (archive_diary translation)

The archive_diary mood maps onto existing components — through tokens and copy,
never by forking CSS:

| Component | archive_diary reading |
|-----------|----------------------|
| Visa result card | document folder / file card |
| Required documents | checklist paper |
| Procedure tabs | file-index tabs |
| Source block | receipt / verification stamp / archive record |
| AI answer card | consultation memo |
| Warning block | red-pen administrative caution |
| Language selector | small label sticker |
| Search field | practical intake form (not a chatbot gimmick) |
| CTA buttons | restrained civic action buttons (not flashy) |

Decorative asymmetry is allowed **only** in non-critical areas. Required
information stays aligned, scannable, and readable.

## 8. Theme selector behavior

- Control: `#editorialThemeBtn` in the top controls
  (`data-action="toggle-editorial-theme"`), beside the brightness toggle.
- It cycles `civic_editorial ⇄ archive_diary`, persists, and relabels (시빅 ⇄
  아카이브). Label + `aria-label` localize via `EDITORIAL_THEME_LABELS` /
  `EDITORIAL_THEME_ARIA` with an English fallback, and refresh on language
  change (`applyLanguage` → `updateEditorialThemeLabel`).
- The pre-existing `#mainThemeBtn` (light/dark) is untouched.

## 9. Do / Don't for future themes

**Do**
- Add a new `:root[data-theme="<name>"]` block; override foundational tokens.
- Reuse the existing variable names so every component inherits the theme.
- Keep cautions and source blocks high-contrast and visible.
- Keep body text size and line-height at base or better.
- Add the name to `EDITORIAL_THEMES` and a label to the two label maps.

**Don't**
- Don't fork or duplicate component CSS per theme.
- Don't override type scale, spacing, radius, or fonts in a theme.
- Don't add CDN dependencies or external assets.
- Don't reuse the brightness value-space (`light`/`dark`) for a style theme.
- Don't reduce readability, source visibility, or legal-caution prominence.
- Don't change visa data, legal copy, AI grounding, or source mappings.

## 10. Verification checklist

- [ ] Inline bootstrap sets the root `data-theme` before paint (no flash).
- [ ] Default with empty storage = `civic_editorial`.
- [ ] Selector cycles both themes and persists across reload.
- [ ] Brightness (light/dark) still toggles independently on `<body>`.
- [ ] Resolved tokens differ between themes (verify via computed styles).
- [ ] Landing, search field, language/theme controls render in both themes.
- [ ] Result cards, detail drawer, procedure tabs, required-docs checklist,
      AI card, source block, warning block, HiKorea CTA render in both themes.
- [ ] Mobile (~390px) layout intact in both themes.
- [ ] No component CSS duplicated per theme.
- [ ] No existing JS behavior (search, language, modal, tabs, AI) broken.
- [ ] No change to visa data, legal copy, source status, or AI meaning.

## 11. Known limitations

- `archive_diary` is tuned for the light/paper experience. In dark brightness
  mode, body-level dark tokens intentionally win for content; the editorial
  theme primarily shapes the light experience. (Documented, by design.)
- `ai.html` (standalone AI shell) is out of scope for this PR; it can adopt the
  same root-attribute + token pattern in a follow-up.
- Theme treatment is intentionally token-level. Deeper object-based texture
  (file tabs, receipt edges, sticker labels) is specced as principle in the
  design docs and can be layered later in non-critical areas without forking
  components.
