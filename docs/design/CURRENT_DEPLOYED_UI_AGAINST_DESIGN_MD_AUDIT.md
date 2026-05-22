# CURRENT DEPLOYED UI AGAINST DESIGN.md AUDIT

## 1) Executive verdict

**Verdict: Misaligned with DESIGN.md (with isolated partial alignment in base color family and dark-theme intent).**

The currently deployed frontend is functionally rich, but visually fragmented due to **accumulated CSS layering and conflicting token systems**. The dominant UX quality issues are not a single bug; they are systemic:

1. **Token drift** (multiple parallel color/radius/spacing systems in same files).
2. **Hierarchy breakdown** (too many high-emphasis elements simultaneously).
3. **Density inconsistency** (mixed compact and oversized components without rhythm).
4. **Component shape inconsistency** (radius scale ranges from 4px to 32px + pills).
5. **Mobile readability risk** at 390px due to heavy chip/badge/meta density and mixed text sizing.

Practical conclusion: before visual polish, the codebase needs a controlled token/hierarchy normalization pass.

---

## 2) Design token alignment audit (DESIGN.md vs implementation)

### 2.1 Color usage
- **Partially aligned:** core palette values appear in both pages (`#0EA37B`, `#085E48`, `#FF6B5B`, dark greens) and dark theme variables exist.
- **Misaligned in application:** index and ai introduce many extra aliases (`--ac`, `--ac2`, legacy `--bg*`, `--p-*`, ad-hoc literal gradients), which weakens predictable component semantics.
- **Impact:** designers cannot reliably infer whether a given CTA/chip/card color reflects primary intent or historical override.

### 2.2 Primary / secondary CTA treatment
- DESIGN.md defines clear primary/secondary button system; implementation uses multiple unrelated CTA styles (white hero CTA, green gradients, transparent outline variants, per-module button styles).
- **Result:** CTA priority is ambiguous; users see many “important-looking” controls.

### 2.3 Typography weights
- DESIGN.md body defaults favor 400 with controlled heading weights.
- Current CSS uses frequent 700/800 and explicit 900 in multiple spots (e.g., jurisdiction numerals/messages and marker dots), creating visual shouting and reducing scannability in Korean paragraphs.

### 2.4 Korean body readability
- Body line-height baseline is close in many areas, but readability suffers from high local contrast spikes, dense label stacks, and frequent mixed-size microcopy blocks within cards/panels.

### 2.5 Border-radius scale
- DESIGN.md radius scale is controlled (4/8/12/16/20/24 + pill).
- Current UI mixes 4, 6, 8, 10, 12, 14, 16, 20, 24, and 32px, plus many pills. This creates inconsistent component personality and contributes to cluttered perception.

### 2.6 Spacing rhythm
- There is a nominal spacing token system, but many sections still use hardcoded rem/px values and local overrides. Rhythm differs drastically between hero, cards, modals, and info panes.

### 2.7 Card elevation
- DESIGN.md expects restrained paper/ink card treatment.
- Current implementation combines multiple shadow recipes and translucent layers; some sections feel heavy/glassy while others are flat, reducing cohesion.

### 2.8 Focus-visible states
- **Partially aligned:** focus-visible is implemented globally.
- **Misaligned detail:** use of `!important` and selector-level overrides indicates accessibility styling is not governed by a single canonical layer.

### 2.9 Dark mode implementation
- Dark mode exists and is extensive.
- However, there are multiple dark-mode styling passes and alias maps in both pages, suggesting iterative layering rather than consolidated token binding.

### 2.10 Repeated ad-hoc CSS layers
- Both pages contain repeated “design token” blocks, “legacy mapped vars,” and later harmonization sections. This strongly indicates drift accumulation as the root of current visual weakness.

---

## 3) Highest-impact UX/UI problems (top 12)

1. **Hero visual language diverges from DESIGN.md tone** (bright multi-stop gradient + oversized decorative treatment), diluting “calm civic paper+ink” authority.
2. **Primary CTA semantics are inconsistent across contexts** (hero, AI actions, modal actions, utility controls).
3. **Landing/search entry hierarchy is overloaded**: too many concurrent controls, badges, and emphasized surfaces near first interaction zone.
4. **Search result cards lack consistent scan pattern** due to mixed label weights/radii/border accents.
5. **Visa result card internals overuse high-emphasis text** (700/800/900), making priority cues indistinct.
6. **Required document sections are information-rich but visually dense**, causing low at-a-glance comprehension.
7. **Procedure tab/step readability suffers from compact spacing + competing emphasis markers**, especially when combined with other metadata blocks.
8. **Source/grounding panels are semantically useful but visually noisy** (many chips, states, badges, and subtle variants together).
9. **HiKorea-related CTA visibility is inconsistent with overall CTA hierarchy**, sometimes blending with other action clusters.
10. **Paradiso.ai answer card/source panel has strong feature depth but too many micro-surfaces**, increasing cognitive load.
11. **390px mobile risk:** chip/badge rows, action clusters, and auxiliary labels wrap aggressively and can produce “stacked clutter” feel.
12. **CSS layer accumulation itself is now a UX issue**: visual intent is hard to maintain, so regressions are likely with each small change.

---

## 4) Implementation risk map

| Major issue | Risk bucket | Reason |
|---|---|---|
| Token drift (colors/radius/spacing aliases) | **Safe CSS-only patch** | Consolidate variable usage and remove duplicate semantic paths without changing markup/JS behavior. |
| Overweight typography / hierarchy flattening | **Safe CSS-only patch** | Rebalance font weights/sizes/line-height by selector-level tuning. |
| Card density/readability in search results | **Safe HTML/CSS patch** | Minor wrapper/grouping classes may be needed for consistent spacing. |
| Required documents/procedure readability | **Safe HTML/CSS patch** | Structural grouping and spacing labels likely need small markup adjustment. |
| Source/grounding chip overload | **Safe CSS-only patch** (phase 1), **small JS rendering change** (phase 2) | First reduce visual emphasis; later reduce rendered chip count/states when safe. |
| HiKorea CTA salience normalization | **Safe CSS-only patch** | Emphasis and placement weight can be normalized visually. |
| AI answer card slot clarity | **Requires small JS rendering change** | Better grouping/order may require slight render-template adjustments. |
| 390px mobile regressions | **Safe CSS-only patch** + QA | Mostly media query/overflow/wrapping discipline. |
| Hero/landing final polish | **Defer until Figma stabilizes** | High chance of rework if Figma source remains volatile. |
| Anything requiring changed legal/content claims | **Requires backend/data change** (not in this audit PR) | Out of scope and prohibited here. |

---

## 5) PR sequence proposal (B-E)

### PR B
- **Branch:** `ui/pr-b-token-typography-radius-spacing-repair`
- **Purpose:** normalize token usage and base hierarchy without changing product behavior.
- **Allowed files:** `index.html`, `ai.html`, `DESIGN.md` (only if clarifying token mapping notes), `docs/design/*` audit follow-up.
- **Forbidden files:** backend scripts, any JSON data files (`visa_data.json` 포함), API/server logic.
- **Acceptance criteria:**
  1. Single canonical token mapping path per page (no parallel “legacy vs new” ambiguity for primary colors/radius/spacing).
  2. Body readability pass applied (reduce unnecessary 800/900 in non-heading text).
  3. Radius usage constrained to DESIGN.md scale (except intentional pill components).
  4. No runtime JS behavior changes.
- **Manual QA checklist:**
  - Landing, searching, searched states all render.
  - Keyboard focus-visible remains clear on buttons/links/inputs.
  - Dark/light theme toggle visual parity maintained.
  - No lost click handlers.

### PR C
- **Branch:** `ui/pr-c-search-card-and-document-readability`
- **Purpose:** repair scanability of search result cards + required docs/procedure readability.
- **Allowed files:** `index.html`, optional docs under `docs/design/`.
- **Forbidden files:** backend, JSON data, API contracts.
- **Acceptance criteria:**
  1. Search result cards have consistent title/meta/body spacing.
  2. Required document buckets are visually distinct with reduced clutter.
  3. Procedure steps prioritize order readability over decorative badges.
- **Manual QA checklist:**
  - Direct visa code search still works.
  - Keyword search still works.
  - Card interactions and modals unchanged functionally.

### PR D
- **Branch:** `ui/pr-d-landing-hero-entry-polish-after-figma-stable`
- **Purpose:** finalize landing hero/search entry polish after Figma stabilizes.
- **Allowed files:** `index.html`, design docs.
- **Forbidden files:** backend, JSON data, AI runtime logic.
- **Acceptance criteria:**
  1. Hero/search entry matches stabilized Figma direction while preserving current feature set.
  2. CTA hierarchy becomes unambiguous (1 primary, 1 secondary, utilities demoted).
- **Manual QA checklist:**
  - Above-the-fold at 390/768/1280 widths.
  - Theme and language toggles remain discoverable.

### PR E
- **Branch:** `ui/pr-e-mobile-390-regression-qa-final-polish`
- **Purpose:** mobile-specific cleanup and regression hardening.
- **Allowed files:** `index.html`, `ai.html`, QA docs.
- **Forbidden files:** backend/data/JSON.
- **Acceptance criteria:**
  1. 390px no horizontal overflow in core flows.
  2. Chip/badge/action rows wrap cleanly without hierarchy collapse.
  3. Modal and source panels remain readable and keyboard accessible.
- **Manual QA checklist:**
  - iPhone 12/13 mini viewport checks.
  - Search → result → modal → back flow.
  - Paradiso.ai answer + source panel checks.

---

## 6) Preservation contract (must not regress)

The following capabilities must remain functionally intact in all follow-up UI PRs:

- direct visa code search
- keyword search
- language toggle
- theme toggle
- HiKorea guide modal
- reminder feature
- agent finder
- medical institution finder
- Paradiso.ai page/modal
- body landing/searching/searched state machine
- starCanvas / hero effects (if present in current runtime)
- backend config script behavior
- all existing `data-action` handlers
- all existing modal overlays

---

## 7) Recommended next PR (specific): PR B

Execute **PR B** immediately with strict boundaries:

1. **Token unification pass only** in `index.html` and `ai.html`:
   - keep existing semantic intent,
   - map legacy aliases to one canonical layer,
   - remove contradictory duplicate declarations where safe.
2. **Typography hierarchy repair**:
   - demote non-heading 800/900 usages to 400/500/600 as appropriate,
   - preserve explicit numerical/status emphasis only where truly functional.
3. **Radius normalization**:
   - enforce DESIGN.md radius steps,
   - keep pill only for chips/badges that require it.
4. **Spacing rhythm correction**:
   - replace local hardcoded one-off spacing with token steps in high-traffic components first (search bar, visa cards, doc buckets, source panels).
5. **No JS logic changes, no feature deletions, no backend/data edits.**

Definition of done for PR B: visual noise is materially reduced, typography and spacing become predictable, and every existing user flow remains behaviorally identical.
