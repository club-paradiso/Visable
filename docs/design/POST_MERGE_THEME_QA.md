# Post-Merge Theme QA — `civic_editorial` / `archive_diary`

QA pass run after the editorial theme-system PR merged. Scope is **UI/UX only**:
no visa data, legal content, AI grounding, source mappings, or backend logic
were inspected for change. Goal: verify both themes on the core UI, find
layout / readability / hierarchy / mobile / source-warning regressions, and ship
the smallest safe polish.

## Method

- Rendered the live `index.html` against the static `visa_data.json` fallback
  (localhost → `API_BASE=""`) in headless Chromium (Playwright 1.56).
- Both themes set via `localStorage['paradiso:editorial-theme']` before paint.
- Both brightness-independent paths exercised at **1280×900 (desktop)** and
  **390×844 (mobile)**.
- Deep-linked each test case with the `?q=` hook from the exact-code-search PR.
- Captured screenshots and **computed-style contrast / overflow measurements**
  (WCAG 2.1 contrast ratios from resolved colors).

### Test cases (each, both themes, desktop + mobile)

`D-2` · `F-6` · `G-1-5` · `H-1` · `E-7`, plus the landing/search page.

## What was checked

| Area | civic_editorial | archive_diary | Notes |
|------|:---:|:---:|------|
| Landing / search page | ✅ | ✅ | Distinct palettes; hero, search field, quick actions intact |
| Theme selector | ✅ | ✅ | Cycles + persists + relabels (시빅 ⇄ 아카이브); no flash |
| Language selector | ✅ | ✅ | Fits top bar in both themes/viewports |
| Search results | ✅ | ✅ | Count meta, sort meta, cards render |
| Result cards | ✅ | ✅ | Code chip, title, subtype badge, badges row |
| Detail cards | ✅ | ✅ | Expand/collapse, next-action area, summary |
| Procedure tabs | ✅ | ✅ | 4–6 tabs; horizontally scrollable strip (`overflow-x:auto`), no clipping |
| Required documents | ✅ | ✅ | Checklist scannable; 18–109 rows render grouped |
| AI guidance card | ✅ | ✅ | Renders; backend offline in QA → degraded-state copy (expected) |
| Source / citation block | ✅ | ✅ | `.sep-note` 7.08:1 / 7.53:1 — readable in both |
| Warning / disclaimer block | ✅ | ✅ | Caution rows 7.60:1; reference disclaimer 19.3:1 / 17.8:1 |
| Mobile (~390px) | ✅ | ✅ | No horizontal overflow (`scrollWidth == clientWidth`) |

### Critical-rule verification

- **Official-source warnings visible** — source panel + the `2026.5 매뉴얼 확인 필요`
  freshness badge render prominently in both themes. ✅
- **Legal disclaimers not softened/hidden** — reference disclaimer and caution
  rows are the highest-contrast text on the card. ✅
- **Required documents scannable** — grouped checklist with critical-doc icons;
  doc-item text 15.3:1 / 14.3:1. ✅
- **archive_diary not generic pastel/Y2K** — warm cream/ivory paper, brown-black
  ink, restrained archival blue links, muted green/red status. Reads as civic
  paperwork, not a fan page. ✅
- **civic_editorial unchanged as default** — no token overrides; only one shared
  badge token was darkened (see below), no layout/structure change. ✅
- **No per-theme component duplication; CSS variables only** — confirmed. ✅

## Measured contrast (WCAG 2.1, resolved colors)

| Element | civic | archive | Threshold | Result |
|---------|------:|--------:|-----------|--------|
| Procedure summary text | 7.63 | 8.28 | 4.5 | ✅ |
| Required-doc item | 15.34 | 14.26 | 4.5 | ✅ |
| Source note (`.sep-note`) | 7.08 | 7.53 | 4.5 | ✅ |
| Critical-doc caution | 7.60 | 7.60 | 4.5 | ✅ |
| Reference disclaimer | 19.27 | 17.84 | 4.5 | ✅ |
| Code/link (`.bc`) | 6.66 | 6.64 | 4.5 | ✅ |
| **Subtype badge (`.bn`) — before** | 3.28 | **2.95** | 3.0 (small badge) | ⚠ / ❌ |
| **Subtype badge (`.bn`) — after fix** | **5.72** | **5.98** | 3.0 | ✅ |
| Active procedure tab | 3.21 | 5.06 | 4.5 | ⚠ civic (see known issues) |

## What was fixed

**One change, `index.html` only:** the subtype-count badge `.bn`
(“세부 N”) used `--t3` (lightest ink) on `--bg3` (warm tan). In
`archive_diary` that resolved to **2.95:1** — below the 3:1 floor — and was
borderline (3.28:1) in `civic_editorial`. Switched the badge text token from
`--t3` → `--t2` (mid ink). This is a single shared, token-based change (no
component fork, no layout change, no per-theme rule) that raises both themes to
**5.7–6.0:1** while keeping the badge visually subtle.

## What was intentionally left unchanged

- **Active procedure tab in `civic_editorial`** (white on the brand green
  `#0ea37b`, 3.21:1). The brand green is used widely and changing it is a
  brand-level decision outside "minimal polish"; `archive_diary` already renders
  it at 5.06:1. Logged as a known issue rather than altered, to keep the default
  theme production-ready and visually unchanged.
- All `civic_editorial` palette tokens (it remains the canonical, override-free
  default).
- Visa data, legal copy, source/verification status, AI grounding, and backend.
- `ai.html` standalone shell (out of scope for the theme system per the design
  doc).
- Top-control density on mobile — visually tight but measured non-clipping
  (`top-ctrls` right edge 275–299px within 390px); no fix needed.

## Known remaining UI issues (follow-up candidates)

1. **Active procedure tab contrast in `civic_editorial`** — white-on-green
   3.21:1 (passes AA-large only). Consider a slightly deeper green for the
   active tab/CTA in a dedicated brand-contrast PR.
2. **Mobile top-control density** — functional and non-clipping, but the
   clock + language + 2 theme toggles sit close together on the dark landing
   hero. Could group or compact in a later pass.
3. **`archive_diary` in dark brightness mode** — by design the body-level dark
   tokens win for content; the editorial theme primarily shapes the light/paper
   experience (documented limitation, not a regression).

## Validation

- `node scripts/check_static_visa_result_cards.js` → OK
- `node scripts/check_placeholder_suppression.js` → 19/19
- `node scripts/check_i18n.js` → OK (674 ko/en keys; 49 required UI keys)
- `node scripts/check_ai_shell_semantics.js` → OK
- `node scripts/audit_procedure_journeys.js` → OK
- `bash scripts/check_repo.sh` → All regression checks passed (backend
  regression + AI golden eval green; `pdfinfo` page-count check skipped — tool
  not installed in env)
