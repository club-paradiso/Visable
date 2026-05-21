# Result Card & Paradiso.ai Answer Card — Structural Rewrite v2 Notes

**Date:** 2026-05-21
**Branch:** `feature/result-and-ai-card-structural-rewrite`
**Base:** `main` (already includes PR #112 — the v1 structural pass)
**Status:** Draft PR; CSS + small JS body edits to two grounding-panel
functions, plus this note. No backend changes, no preserved contract
broken.

This document explains what *this* PR adds on top of PR #112, what it
intentionally does **not** do, and what still has to be wired in a
future PR.

---

## 1. Relationship to prior work

PR #112 (merged on `main`) shipped:

- A "STRUCTURAL RESULT-CARD HIERARCHY" CSS block at the end of the
  visual-overhaul layer in `index.html` that sharpens the 9-step
  scan path defined in `docs/design/PARADISO_UX_DIRECTION_LOCK.md` §4.
- A `<template id="pa-answer-card-shell">` plus a "PARADISO.AI
  STRUCTURED ANSWER CARD SHELL" CSS layer in `ai.html` that maps to the
  11 slots in `docs/ai/ANSWER_QUALITY_CONTRACT.md` §3.
- Mobile 480px guards, badge-density tuning, and 5-bucket doc-group
  shell (`group-common` / `group-required` / `group-additional` /
  `group-conditional` / `group-missing`) with `DATA_MISSING` honesty
  preserved.

The contract from `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` (PR #104)
remained intact in that PR.

## 2. What this PR (v2) changes

### 2.1 `renderGroundingSourcePanel` — `index.html`

The function still returns the same overall shape (`.ai-grounding-panel >
.gp-title + .gp-row*`). The body now:

- Reads `metadata.citation_verification.status` and the
  `law_grounding_warnings` array to attach an *honest disclosure state
  class* to each `.gp-row`. States mirror
  `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`:
  `state-verified`, `state-source-supported`, `state-partial`,
  `state-extracted-only`, `state-source-linked-unverified`,
  `state-disabled`, `state-not-wired`, `state-failed`.
- Replaces the previously over-confident `"검증됨"` label on the
  manual-source row with `"매뉴얼 출처 있음 (개별 검증은 진행 중)"`
  (`state-source-supported`), so the result-card grounding block no
  longer reads as a verification stamp when verification hasn't run.
- Replaces the public-data row's `"확인 필요"` label with `"출처 표시
  · 개별 항목 검증은 진행 중"` (`state-partial`).
- Adds a closing `.gp-disclosure` paragraph that points the user to
  1345 / HiKorea / the competent immigration office before acting.

The function signature is unchanged. No other call sites need
updates. The `47` `data-action` dispatch values are untouched. No
`window.*` exports, no IDs, and no JS-referenced class names from
`docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` §2.8 / §2.9 were renamed.

### 2.2 `renderGroundingSourcePanel` — `ai.html`

Symmetric change: rows now carry the same `state-*` class names
(scoped to `.source-list .source-row` in `ai.html`), copy is the same
honest-disclosure text, and the panel ends with a `.source-disclosure`
line.

### 2.3 CSS — `index.html`

Added a new block: `STRUCTURAL RESULT-CARD HIERARCHY v2`. It sits
*before* the v1 block's end marker so the v1 layer remains the
authoritative pixel-parity baseline. The v2 block:

- Styles `.manual-result .ai-grounding-panel .gp-row.state-*` so each
  row shows a small uppercase status chip (`검증됨`, `출처 있음`,
  `부분`, `미검증`, `링크만`, `사용 안 함`, `미연결`, `검증 실패`)
  driven purely by the class added in §2.1.
- Styles the `.gp-disclosure` closing paragraph.
- Tightens header badge density (domain + review badges keep priority,
  period/data badges shrink) so the scan path reads
  identity → procedure → docs → warnings → sources → next-action.
- Mobile-480px guards for the grounding panel (chips stack), narrower
  `.docs-list-row` grid columns, and `.manual-detail-block` overflow
  guards.

No new CSS custom properties. No additional emerald/coral/amber
families. The block only consumes existing `--p-emerald*`,
`--p-line`, `--p-ink*`, `--p-paper-surface-2`, `--color-warning`.

### 2.4 CSS — `ai.html`

Added a new block: `SOURCE PANEL HONEST DISCLOSURE`. It styles
`.source-list .source-row.state-*` to mirror the same disclosure
chips, on the dark answer-canvas background. No new tokens.

## 3. What this PR intentionally does NOT do

- **No backend change.** `/api/ask`, `/api/visas`,
  `/api/jobcodekeywords` are untouched.
- **No law grounding rollout.** `mode` remains `disabled` by default;
  the new `state-not-wired` row class makes that visible rather than
  silently absent.
- **No claim of completed citation verification.** Where the metadata
  says `extracted_only` / `not_wired`, the row's chip and copy say
  so explicitly; the row never collapses.
- **No `visa_data.json` edit.** No data is hidden or invented.
- **No deletion of features.** Language toggle, theme toggle, direct
  visa search, keyword search, the
  `landing → searching → searched` state machine, HiKorea guide,
  reminder feature, agent finder, medical institution finder, and all
  modals remain in place. `starCanvas`, `#hero`, and the config
  scripts are untouched.
- **No new framework, no new dependency.** Vanilla HTML + CSS + one
  large inline `<script>` per file, exactly as before.
- **No rewrite of `renderResults`, `renderProcedurePanel`,
  `renderDocumentTabs`, `renderSourceEvidencePanel`,
  `renderManualActions`, `renderNextActionArea`**, etc. The 9-step
  scan path inside the result card is still the v1 layout from
  PR #112.
- **No `<template id="pa-answer-card-shell">` wiring into
  `appendAiAnswer()`.** That remains a future-PR item — see §5.

## 4. Preservation-contract notes

Cross-checked against `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` §10
and §2.8 / §2.9:

- All static `data-action` values still appear in body markup
  (`open-hikorea-guide`, `open-doc-modal`, `open-ai-modal`,
  `select-procedure`, `select-docs-tab`, etc.). Grep verified.
- `hikoreaGuideOverlay`, `starCanvas`, `#hero`, `topCtrls`,
  `mainContent`, `aiModalOverlay`, etc. — all still present.
- `body.searched` / `body.searching` / `body.landing` state machine
  unchanged. The CSS selectors `:not(.searched)` and `.searched` were
  not touched.
- `[data-theme="dark"]` selector path unchanged — no
  `prefers-color-scheme` shortcut.
- `<canvas id="starCanvas">` still sits directly inside `<body>` and
  before `<header id="hero">`.
- `window.PARADISO_BACKEND_URL` config script unchanged.
- Function-body edits in this PR are confined to the two
  `renderGroundingSourcePanel` functions (one per file) and only add
  class-name attachment + safer copy. No fetch URL, no parameter
  shape, no return contract change beyond an extra trailing `<p>`
  inside the returned `<section>` / `<div>` wrapper.

## 5. What remains for a future PR

The Paradiso.ai answer-card shell exists in `ai.html` but is not yet
rendered into the live `.chat-history` flow. `appendAiAnswer()`
still produces the legacy `.answer-card` markup. Wiring the template
requires:

1. A backend change to surface the structured answer object as a
   debug field (`/api/ask` Phase C in `ANSWER_QUALITY_CONTRACT.md`
   §10). This PR does not do that — backend is frozen.
2. Once the field is available, a frontend pass to clone
   `#pa-answer-card-shell`, fill each `[data-slot-body]` element, and
   toggle `[hidden]` per slot.
3. Eval coverage from `docs/ai/ANSWER_EXAMPLES.md` against the new
   render path.

Until then, the existing `.answer-card` rendering remains
authoritative on `ai.html`, and the `pa-*` template stays inert. This
matches the user-facing scope item that says "If only CSS/HTML shell
preparation is possible, do that and document what remains."

## 6. Validation

Locally run (per the brief):

- `git status --short`
- `python3 -m json.tool visa_data.json > /dev/null`
- `bash scripts/check_repo.sh` (with `ALLOW_BACKEND_TEST_SKIP=1` if
  the environment lacks `fastapi`/`httpx`/`pydantic`)
- `rg -n "open-hikorea-guide|hikoreaGuideOverlay|updateCategoryCounts|renderGroundingSourcePanel|data-action" index.html ai.html`
- `rg -n -i "legally verified|official decision|guaranteed|production-ready law grounding|legally binding" index.html ai.html docs`

The over-claim grep is expected to surface only the *negation*
copy added by this PR (and the existing docs that *prohibit* such
claims). It must not surface any new assertive copy.

Manual QA — UI not runnable in this environment, deferred to a
human pass per `PARADISO_UX_DIRECTION_LOCK.md` §11.7. Targets:

- D-2, E-7, F-1, F-6
- "address change", "passport information change", "unknown visa code"
- language toggle, theme toggle
- HiKorea guide modal end-to-end
- Reminder feature
- 390px viewport — no horizontal overflow, doc tabs scroll within
  their row only, grounding chips stack cleanly, HiKorea CTA stays
  the visually distinct primary action.

## 7. Remaining risks

- **`mapLawWarningToFriendly` legacy mapping** still returns
  `'법령 검증 기능이 꺼져 있음'` etc. The row-level state chip and
  the warning text are now layered; a careful Korean reader will see
  the row says `사용 안 함` and the warning detail repeats the same
  fact. Acceptable, but a future PR may want to collapse the two.
- **Citation status values** in the metadata are read but not
  validated against the schema in
  `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`. If the backend ever
  returns an unrecognized status string, the row falls through to
  `state-partial`. Safer than over-claiming, but worth a
  follow-up tightening.
- **`appendAiAnswer()` wiring** is still future work, as noted in §5.
