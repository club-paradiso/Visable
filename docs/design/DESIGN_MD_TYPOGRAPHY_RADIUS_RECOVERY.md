# DESIGN.md typography + radius alignment — recovery pass

## Background (why this PR exists)

During a repository private → public visibility toggle, a stacked pair of draft
PRs for the "Visable" rebrand + Figma design alignment appeared lost. On
investigation, nothing was deleted, but the work had become **orphaned**:

- **Rebrand** (`Visable` product / `Club Paradiso` house) actually shipped to
  `main` through a series of smaller phased PRs (#505, #507, #509). The original
  large rebrand draft (#499) was thereby superseded and now conflicts wholesale
  with `main`.
- The **design PR** (#503 — "align default look to DESIGN.md: typography
  hierarchy + radius") was *stacked on #499*. Because #499 can never merge, #503
  was stranded on a dead base and its design fixes never reached `main`.

This pass re-applies that stranded design work directly on top of current `main`,
so the improvement is recovered on a clean, mergeable base.

## What changed (CSS values only — `index.html`)

Addresses the two root causes DESIGN.md names for the "구리다" feel:

1. **Typography hierarchy** — `DESIGN.md` weight ladder ("nothing 900 below h2").
   Demoted the **72 default-look `font-weight: 900`** declarations that flattened
   the visual pyramid:
   - **4 → 800** — genuine display / big-numeral / anagram tier
     (`.footer-hero-title`, `.figma-footer-hero-title`, `.anagram-letter`,
     `.jur-big`), joining the existing 800 top tier (`.p-hero-title` 850,
     `.stat-num` 800).
   - **68 → 700** — headings, titles, labels, badges, buttons, kickers, markers.
2. **Radius** — `DESIGN.md` scale caps 2xl at 24px. Capped the **2 default-look
   `border-radius: 32px`** container radii (`.brand-feature`, `.about-me`) → 24px.

## Preserved (not touched)

- The **4 kitsch / `archive_diary` editorial-theme** `font-weight: 900`
  declarations (`[data-theme="archive_diary"]`, `--k-ink` scoped) — intentional.
- The **4 kitsch `border-radius: 32px !important`** declarations — intentional.
- All markup, JS, `data-action` handlers, the landing/searching/searched state
  machine, theme + language toggles, dark mode, and the canonical token system.

## Verification

- `npm run validate` (check_repo.sh) — PASS (incl. "no forbidden branding strings").
- `test:i18n`, `test:complex-guide-qa`, `test:legal-search`,
  `test:hikorea-reservation-helper`, `test:official-sources` — all PASS.
- Headless render (Chromium) at 1280px and 390px: landing hierarchy is calmer and
  clearer, wordmark + house-of-brands lockups intact, no layout breakage, no
  horizontal overflow on mobile.
- Diff is symmetric (74/74) — pure value swaps, no structural change.

## Deferred (documented, intentionally out of scope for a submitted-entry pass)

- Radius micro-drift (6/10/14px → nearest DESIGN.md scale step) — higher churn,
  lower visible impact.
- Hero/CTA hierarchy polish and source/grounding chip reduction (DESIGN.md audit
  PR C–E) — larger surface, deferred to keep this recovery low-risk.
