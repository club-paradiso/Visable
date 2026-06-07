# Paradiso — Design Reference Inventory

> Scope: a single, honest catalogue of every design input that informs the
> Paradiso interface, what each one legitimately contributes, and — equally
> important — what must **not** be copied from it. This file exists so future
> design work pulls from *principles*, not from imitation.

Paradiso is an AI-assisted Korean visa / residence information platform for
foreigners in Korea. The interface must stay **clear, trustworthy,
source-visible, legally cautious, mobile-first, multilingual, and practical.**
It is not a government portal, a law firm, a filing service, a fan interface, a
generic SaaS app, or a decorative mockup.

Design thesis: **Contemporary Korean Editorial Civic-Tech.**

---

## 1. Current Paradiso UI (primary reference)

- **Live site:** https://lucanomics.github.io/Paradiso/
- **Repository:** https://github.com/lucanomics/Paradiso
- **Implementation:** `index.html` (single-file app) + `ai.html` (AI shell).

**Contributes:** the real, shipped product is the source of truth for
information architecture — search-first landing, result cards (`.vc`),
procedure tabs, required-document checklists, AI answer cards, source/citation
blocks, warning blocks, the HiKorea reservation CTA, language controls, the
light/dark brightness toggle, and the existing CSS custom-property token system
(`--bg*`, `--t*`, `--ac`, `--color-*`, `--p-*`).

**Must not change:** visa data, legal copy, AI grounding, source mappings, or
the meaning of any guidance. Theme work is token-level and additive only.

## 2. Existing design documents

| File | Contributes | Notes |
|------|-------------|-------|
| `DESIGN.md` | Canonical token + component spec (colors, type scale, radius, card scan order, button hierarchy, accessibility, Do/Don't). Korean. | Authoritative. The "warm paper + ink" civic language and `[data-theme]` attribute approach come from here. |
| `docs/design/PARADISO_UX_DIRECTION_LOCK.md` | Locked UX direction / non-negotiables. | Read before any UX change. |
| `docs/design/CURRENT_DEPLOYED_UI_AGAINST_DESIGN_MD_AUDIT.md` | Gap audit: deployed UI vs `DESIGN.md`. | Evidence of intended direction. |
| `docs/design/RESULT_AND_AI_CARD_STRUCTURAL_REWRITE_V2_NOTES.md` | Result-card + AI-card structure rationale. | Card hierarchy reference. |
| `docs/design/MANUAL_BASED_INTERFACE_REBUILD_REVIEW.md` | Manual-grounded interface rebuild. | Source-forward layout. |
| `docs/design/UI_REPAIR_PASS_1_NOTES.md` | Incremental UI repair log. | Historical context. |
| `docs/design/CLAUDE_DESIGN_INTEGRATION_AUDIT.md` | Claude Design integration audit. | SkillUI / Claude Design output review. |
| `docs/design/STITCH_PROTOTYPE_FIX_REPORT.md` | Stitch prototype fixes. | Stitch output review. |
| `docs/design/UI_REVIEW_FIGMA_INDEX_POLISH_20260507.md`, `FIGMA_LANGUAGE_MIGRATION_NOTES.md` | Figma Make handoff reviews. | The header/footer "KEEP" decisions live here. |

**Contributes:** the documented vocabulary — warm paper surfaces, emerald as a
single restrained accent, keep-all Korean line-breaking, badge-only visa codes,
always-visible legal disclaimer, 44px touch targets, focus rings.

**Must not be weakened:** legal disclaimers, official-source cautions, the rule
that AI answers are *secondary guidance, not authority*.

## 3. SiteInspire / external editorial references

No SiteInspire URLs are committed to the repo at time of writing. They are used
only as **principle evidence** for contemporary editorial layout rhythm
(generous whitespace, strong type hierarchy, restrained palette, curated
discovery over loud promotion). If specific references are later added, list
them here with a one-line "what it contributes" note.

**Must not be copied:** specific layouts, color schemes, or brand marks.

## 4. Workingtable / soft Korean desktop-diary references

No committed asset files. Used only as principle evidence for the
`archive_diary` theme mood: a soft civic-paperwork desk — application forms,
document folders, receipt slips, file-index tabs, numbered tickets, travel
notes, scanned paper, subtle stickers, handwritten-annotation energy, and
source stamps.

**Must not be copied:** any specific product's stickers, illustrations, or
packaging. Translate the *feeling* into tokens (paper surfaces, warm borders,
muted ink), never into literal decoration that buries the information.

## 5. SkillUI / Stitch / Figma / Claude Design outputs

Reviewed and reconciled in the audit docs above (§2). They contributed layout
ideas that were selectively adopted (and explicitly *rejected* where they
conflicted with civic-tech trust — e.g. the marketing-only nav and decorative
glass overuse were declined in `UI_REVIEW_FIGMA_INDEX_POLISH_20260507.md`).

**Must not be copied:** generated mock content, placeholder data, or any visual
that reduces source visibility or legal caution.

---

## 6. Principle references — NOT imitation targets

NewJeans, ADOR, and Min Hee-jin are cited **only** as broad design-principle
evidence. They are **not** imitation targets. A previous AI attempt failed by
collapsing this mood into generic pastel Y2K styling — **do not repeat that.**

**Extract only these broad principles:**

- nostalgic but not retro cosplay
- ordinary but iconic
- natural but carefully art-directed
- relaxed but controlled
- tactile but not cluttered
- soft but not childish
- minimal elements with rich emotional texture
- curated discovery instead of loud promotion
- object-based identity through ordinary records — files, notes, tabs, labels,
  receipts, forms, checklists, and source stamps

**Never directly copy, imitate, or expose in the UI:** NewJeans · ADOR ·
Min Hee-jin · album packaging · music-video visuals · bunny motifs · member
references · official typography · logos · recognizable color schemes · fan
interface patterns.

## 7. Failure conditions (any one = reject the design)

- Looks like generic pastel Y2K.
- Looks like a NewJeans fan page.
- Looks like an ADOR / Min Hee-jin imitation.
- Looks like a glossy SaaS template.
- Looks like a fake government portal.
- Body text becomes smaller or harder to read.
- Legal / source warnings become less visible.
- Required documents become decorative instead of scannable.
- Components are duplicated instead of themed through CSS variables.
- Existing JS behavior breaks.
- Visa data, legal copy, AI grounding, or source mappings are changed.
