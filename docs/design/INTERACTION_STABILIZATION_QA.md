# Interaction Stabilization QA

**Date:** 2026-06-07
**Scope:** Confirm whether the reported modal-close and tab-switching
interaction issues still exist in the current `index.html`, and apply the
**smallest safe fix** only if they are still present.
**Method:** Static code-path review of the modal/tab/drawer logic + the existing
automated audits (`check_procedure_journey_audit.js`,
`check_static_visa_result_cards.js`, `check_i18n.js`). No live browser harness is
available in this environment; findings are code-path-verified, and the relevant
behaviors are exercised by the passing automated audits.

---

## Summary verdict

**The reported interaction issues appear already addressed in the current code.
No UI interaction code was changed** (per the "do not make unnecessary UI
changes / do not redesign" rule). One **minor, non-blocking** focus-trap edge
case is documented as a known item rather than fixed, to avoid regression risk.

The two interface themes (`civic_editorial`, `archive_diary`) are driven purely
by CSS variables / `data-theme`; all modal/tab/drawer handlers are
theme-agnostic, so both themes share the same — already-correct — behavior.

---

## Modal close issues — confirmed fixed

Evidence from `index.html`:

- **Close buttons** (`.modal-close`, `data-action="close-*"`) are all
  `<button type="button">` with `aria-label="닫기"` (lines ~10701–10875), so they
  do not submit forms and have an accessible name.
- **Single delegated click handler** (one `document.addEventListener('click', …)`
  at ~16384) routes every `close-*` action to `closeModal(id)` / `closeVisaDrawer()`.
  Because it is one document-level listener (not per-element re-binding on every
  render), **there are no duplicate listeners** — the classic "needs two clicks"
  cause is absent.
- **`closeModal(id)`** (line ~11447) removes `.active`, sets `aria-hidden="true"`,
  clears `activeModal`, removes the `keydown` trap, and restores focus to
  `lastFocusedElement`. Idempotent and complete.
- **Backdrop click** closes the overlay: `e.target === el` check at ~16477 for all
  six overlays.
- **ESC** (single `document` keydown handler at ~16491): closes the language menu
  first if open, else closes the **topmost active modal in one press**
  (`.some()` returns after the first match), else the visa drawer, else exits
  direct-search mode. A single ESC closes a single open modal — the "press ESC
  multiple times" symptom is not reproducible from this code path.
- **Focus trap / restoration:** `trapModalFocus` (line ~11421) cycles Tab within
  `activeModal`; `lastFocusedElement` is restored on close.

Codes spot-checked for the shared modal path (doc modal / FAQ modal / AI modal
reached from result + drawer): **C-3, F-2, F-5, F-6, H-1** — all use the same
delegated `open-*` / `close-*` actions and the same `openModal`/`closeModal`
core, so behavior is uniform across codes.

## Tab / procedure switching — confirmed fixed

- Procedure tabs render as `<button type="button" class="procedure-tab"
  data-action="select-procedure" data-procedure="KEY">` inside
  `.procedure-tabs[role="tablist"]` (renderer at ~13593); panels render as
  `.procedure-panel[data-procedure-panel="KEY"]` (~13573).
- The `select-procedure` handler (~16411) scopes to
  `actionBtn.closest('.manual-result')` and toggles `active` on the matching tab
  and panel by `data-procedure` ↔ `data-procedure-panel`. It is **scoped** (so it
  never cross-talks between cards) and **idempotent** (re-clicking is harmless).
- The **visa drawer** clones the result card; because the handler is scoped via
  `closest('.manual-result')`, switching tabs inside the drawer affects only the
  drawer's clone, never the hidden `#rlist` copy. Tab state and panel rendering
  update correctly in both surfaces.
- Disabled (`unavailable`) tabs early-return (`actionBtn.disabled`), so empty
  procedures can't switch to a blank panel.

### Special F-2 verification (code-path)
Searching **F-2 → detail → 사증발급-style tab → 체류자격 변경(statusChange)**: the
statusChange tab is present (F-2 has `statusChange` with 6 variants), the
`select-procedure` handler activates its panel and active state, the panel stays
inspectable, and the close button resolves on the first click via the single
delegated handler. No stale/duplicate modal remains; page scroll is not locked
(no `overflow:hidden` is left on `body` by `closeModal`; `closeVisaDrawer`
removes `drawer-open`).

### Automated corroboration
- `node scripts/check_procedure_journey_audit.js` → **11 passed / 0 failed**
  (includes placeholder detection, duplicate-doc detection, raw-diagnostic
  detection, consistent procedure-key recognition across priority statuses).
- `node scripts/check_static_visa_result_cards.js` → OK.

---

## Fixes applied

**None.** The interaction code already implements correct, de-duplicated,
single-press behavior. Per the task rules (smallest safe fix; do not redesign;
preserve class names/IDs/data-attributes), no change was warranted.

## Known remaining issues (minor, not fixed this run)

- **Drawer-over-modal focus trap:** if a modal is opened *on top of* the open
  visa drawer and then closed, `closeModal` removes the shared `keydown`
  `trapModalFocus` listener, so the drawer's Tab focus-trap is dropped until the
  drawer is reopened. **Closing still works** (ESC checks the drawer's `classList`
  directly; the close button works via delegation). This is an accessibility
  nicety, not the reported close/ESC failure, and changing the shared
  `activeModal`/listener bookkeeping carries regression risk — deferred.

## Codes tested (interaction)

C-3, F-2, F-5, F-6, H-1 (shared modal/tab/drawer path), with F-2 given the
dedicated 사증발급 → 체류자격 변경 tab-switch check above.

---

## Phase 4 — AI smoke test (documentation)

A live AI provider is not reachable in this offline environment, so the five
smoke prompts were not executed live. Impact assessment of this PR's data change
on AI answer quality:

1. `D-2 … 외국인등록 … 서류` — **unchanged** (D-2 registration data untouched).
2. `D-2 … 아르바이트(시간제) …` — unchanged.
3. `F-4 … 동성 배우자 … F-1-9 …` — unchanged.
4. `G-1-5 … 한국인과 혼인 → F-6 변경` — unchanged (relies on F-6 grounding).
5. `E-7 … 한국에서 일하려면 어떤 절차 …` — unchanged.

None of the five prompts target E-10 / D-8 / H-1 registration, the only records
changed. **Overclaim risk:** unchanged — fills keep `needsManualReview: true`
and append (do not weaken) caution notes. **Source/legal caution:** unchanged —
no disclaimer, source-warning, or official-source caution was removed. **Status
mix-up / readability:** no AI logic or grounding field used by the answer
pipeline was modified. A live AI smoke run is recommended as a follow-up in an
environment with provider access.
