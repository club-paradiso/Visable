# Paradiso Design System

**Design thesis: Contemporary Korean Editorial Civic-Tech.**

A warm, paper-and-ink civic interface with youthful Korean editorial rhythm.
It carries the trust of a public-service tool and the clarity of a good
editorial page — calm, structured, source-forward, and easy to read on a phone.

This document is the human-readable spec. The machine-readable token baseline
lives in `DESIGN.md` and in the `:root` blocks of `index.html`. The theme
mechanics live in `docs/design/PARADISO_THEME_SYSTEM.md`.

---

## 1. Product identity

Paradiso is an AI-assisted Korean visa / residence information platform for
foreigners in Korea. It is **not** a government portal, a law firm, a filing
service, a fan interface, a generic SaaS app, or a decorative mockup.

Non-negotiable product principles (preserve all):

- Search-first experience.
- Source-visible results.
- Clear result cards.
- Procedure and document clarity.
- AI answer cards are **secondary guidance, not legal authority.**
- Official-source caution stays visible.
- Multilingual accessibility.
- Mobile-first readability.
- The Paradiso logo remains the primary brand mark.
- The UI must never look like a fan page, a fake government site, or a generic
  SaaS template.

## 2. Brand principles

- **Calm over loud.** Curated discovery, not promotion.
- **One restrained accent.** Emerald/green carries emphasis; ≤ 3 accent moments
  per screen. Coral is for numeric stat accents only — never borders/backgrounds.
- **Paper + ink texture.** Warm surfaces, soft borders, low shadow.
- **Object-based identity.** Records, files, tabs, labels, receipts, checklists,
  and source stamps — ordinary civic objects, never literal fan/album motifs.
- **Tactile but not cluttered. Soft but not childish.**

## 3. Typography rules

- Family: Pretendard (variable), system-sans fallback. One family across UI.
- Korean body text: `word-break: keep-all` and `line-height ≥ 1.65`.
- Type scale is fixed in tokens (`--p-fs-*`). **Never** shrink body text below
  the base — readability is a hard requirement.
- `font-weight: 900` is reserved for the hero/logo; never on `h2` or smaller
  (it collapses hierarchy).
- Visa codes (`D-2`, `E-7`) are always **badges**, never inline in prose.

## 4. Color rules

Color is delivered exclusively through CSS custom properties so themes can
re-map it without touching components (see §15 and the Theme System doc).

- **Default (civic_editorial):** warm ivory/paper surfaces, deep-green/civic
  primary, muted neutral ink, subtle borders, low shadow, a calm
  official-source highlight.
- Emerald (`#0EA37B`) + white text is **banned** (WCAG AA fail, 3.21:1). Use
  `primary-ink (#085E48)` background + paper text for primary buttons.
- Semantic colors are tokenized: `--color-success` (verified/official),
  `--color-warning`, `--color-error` (caution). Cautions must keep strong
  contrast in every theme.
- No heavy gradients. No glossy SaaS sheen. Glassmorphism only on the landing
  hero, never reused elsewhere.

## 5. Spacing rules

- 4pt / 8pt rhythm via `--p-s-*` / `--sp-*` / `--r2-sp-*` tokens.
- Generous, readable spacing on legal/administrative content.
- Intentional density *contrast* between sections — not uniform padding, and
  never a single `border-radius` applied to everything.

## 6. Card hierarchy

Cards are the primary unit. Scan order is fixed (from `DESIGN.md`):

1. Code badge + KO/EN name
2. Manual-domain badge
3. Procedure control (segmented tabs)
4. Documents for the selected procedure only
5. Source / citation block

Never dump an entire document set onto one screen — split by procedure tab.

## 7. Search UI rules

- Search is the front door: a calm, practical intake field — **not** a chatbot
  gimmick.
- Landing: a pill search bar; results: a compact sticky bar. Both keep the
  same `#q` input and JS hooks.
- Quick filters and suggestions support discovery without shouting.

## 8. Result-card rules

- One result card per status/visa; KO + EN name always shown.
- Badges (period, docs, review) summarize at a glance.
- Keep the card scannable; push depth into tabs and the detail drawer.

## 9. Procedure-tab rules

- Segmented file-index tabs (initial / registration / extension, etc.).
- Show only the selected procedure's documents.
- Tabs stay aligned and readable — decorative treatment must not impede
  scanning.

## 10. Required-document checklist rules

- A scannable checklist (`.doc-chk-item`), not decoration.
- Critical items are visually distinct (and stay distinct in every theme).
- Checkbox state persists locally; never let styling break the scan or the
  persistence hook.

## 11. AI guidance card rules

- Presented as a **consultation memo** — helpful, secondary, clearly labeled.
- Must never read as legal authority or a HiKorea substitute.
- AI grounding, citations, and uncertainty markers are content — out of scope
  for theming and must not change meaning.

## 12. Source / citation block rules

- Source-forward: every result shows where it came from.
- Styled like a receipt / verification stamp / archive record.
- Verified/official status uses the success token; it must remain legible and
  trustworthy. Never reduce source visibility for aesthetics.

## 13. Warning / disclaimer block rules

- Always visible. The footer legal disclaimer and 1345 hotline are required.
- Caution blocks read like a red-pen administrative note: muted-red token with
  strong contrast in both themes.
- **Theming must never make a warning quieter than it is today.**

## 14. Multilingual UI rules

- All UI strings flow through `UI_TRANSLATIONS` / `tx()`. Korean is canonical;
  many languages are supported with graceful fallback.
- New controls must localize via the translation tables or a contained label
  map with an English fallback (see the editorial-theme button).
- `dir` (LTR/RTL) and `lang` are set on the document; respect both.

## 15. Mobile-first rules

- Design for ~390px width first; enhance up.
- 44px minimum touch targets.
- Required information stays aligned and readable on small screens; decorative
  asymmetry is allowed only in non-critical areas.

## 16. Accessibility rules

- `:focus-visible` rings on every interactive element (tokenized color).
- WCAG AA contrast minimum for text and essential UI; cautions stronger.
- `.sr-only` labels for icon-only affordances; `aria-label`/`aria-expanded`
  on menus and toggles.
- Honor reduced-motion expectations; motion is supportive, never required.

## 17. Strict anti-imitation rules

- NewJeans / ADOR / Min Hee-jin are **principle references only** — never
  imitation targets, never exposed in the UI.
- Never copy: album packaging, music-video visuals, bunny motifs, member
  references, official typography, logos, recognizable color schemes, or fan
  interface patterns.
- Never collapse the intended mood into generic pastel Y2K.
- Translate mood into **tokens and ordinary civic objects**, never literal
  decoration that competes with information.

## 18. Theme overview

Two themes ship, both expressions of this one system (full mechanics in
`PARADISO_THEME_SYSTEM.md`):

- **civic_editorial** — default. Warm civic-editorial paper interface; modern
  public-service trust + youthful Korean editorial rhythm.
- **archive_diary** — optional alternate. A soft civic-paperwork "archive
  diary": cream paper, ivory cards, warm gray-brown borders, brown-black ink,
  restrained blue links, muted green for verified sources, muted red for
  cautions, soft yellow highlights — clean, readable, and never childish.
