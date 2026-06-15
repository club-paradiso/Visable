# 사증발급 Procedure UI Unification — Audit (2026-06-15)

## Objective
Unify and improve the **사증발급 / visa issuance** UI so it reads as one more
procedure type inside the existing **절차별 안내** system, for **all supported
non‑F‑4** stay/visa categories. **F‑4 is explicitly excluded** and keeps its
dedicated diaspora route‑guide behaviour.

This is rendering / UI‑hygiene work on **non‑protected** files only. No legal or
immigration content was invented; no document requirement was added; no
disclaimer/caution/uncertainty notice was removed or weakened. The protected
data files (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`) and
the source‑grounded `data/visa_issuance_records.json` / `procedure_evidence_bindings.json`
were **not edited**.

## Renderer / data path discovered
- `사증발급` was **already integrated** as `PROCEDURE_CONFIG[0]` (key `visaIssuance`)
  inside the 절차별 안내 tab system — not a separate module. The procedure header
  (code + Korean/English title + evidence badge + collapsible `근거 보기`) and the
  document checklist already come from the **shared** procedure renderer
  (`renderProcedureHeader`, `renderProcedureDocGroups`, `source-limitation-detail`).
- The embedded issuance card (`renderVisaIssuanceSection` → `renderIssuanceModeCard`)
  was the only part using a **bespoke vocabulary** (`issuance-meta-grid`,
  `issuance-doc-groups`) and it lacked application‑route chips. That mismatch was
  the unification target.
- **Data contract:** `data/visa_issuance_records.json` (42 records, each with
  exactly **one** `issuanceMode`) supplies summary/steps/documents/warnings;
  `data/procedure_evidence_bindings.json` supplies the trust `evidenceLevel`
  (`source_confirmed` 36 / `contextual` 3 / `not_applicable` 3). Friendly badge
  labels come from `SOURCE_EVIDENCE_LABELS` → `getSourceEvidenceLabel()`, so raw
  enum names never reach users. `official_web_overlays.json` `records[]` is empty
  (seed‑only), so the overlay `<select>` stays dormant.

## What changed (files)
| File | Change |
|---|---|
| `index.html` (JS) | Added `GENERIC_VISA_ISSUANCE_EXCLUDED_CODES` + `isGenericVisaIssuanceExcluded()` (F‑4 guard); added `deriveIssuanceRouteChips()` / `renderIssuanceRouteChips()` (standardized application‑route chips from structured `type`/`actor`/`whereToApply` + route facts already in the record's own source text); reworked `renderIssuanceModeCard` (chips replace the dense 2‑box meta‑grid); switched `renderIssuanceDocGroups` to the shared `doc-group-grid`/`doc-group`/`doc-group-title` vocabulary; added the `입국 전 사증발급` stage‑label kicker and the F‑4 short‑circuit in `renderVisaIssuanceSection`; removed three now‑dead helpers (`ISSUANCE_ACTOR_LABELS`, `ISSUANCE_APPLY_PLACE_LABELS`, `localizedMetaLabel`); deduped exact‑duplicate citations in the shared `getFormattedSourceRefs()`. |
| `index.html` (CSS) | Aligned `.issuance-scenario-card` surface to `.manual-subcode-card`; added `.issuance-stage-label`, `.issuance-route-chips/-label/-chip(.is-check)`, calm `.issuance-warnings` caution block; removed dead meta‑grid rules; extended the `archive_diary` (light + dark) card overrides to `.issuance-scenario-card` for theme parity. All rules use existing `var(--*)` tokens — both editorial themes and light/dark are preserved; no new palette. |
| `data/i18n/{ko,en,zh-CN}.json` | +3 keys each: `issuanceStageLabel`, `issuanceRouteLabel`, `issuanceRouteChipLabels` (6‑item array). Identical key set + array length across all three locales. |
| `scripts/validate_visa_issuance_enrichment.js` | +7 checks: F‑4 exclusion set/guard present, F‑4 record still in data, route‑chip renderer present, 6‑item chip i18n pack, stage label via i18n. |
| `scripts/check_f4_route_guide.mjs` | +1 regression assertion: F‑4 excluded from the generic issuance renderer. |
| `scripts/check_visa_issuance_ui.mjs` | **New** smoke. Executes the real `deriveIssuanceRouteChips` + `isGenericVisaIssuanceExcluded` from `index.html` and asserts the full render contract for every non‑F‑4 record. |

Diff: **6 files changed, 153 insertions(+), 45 deletions(-)** + 1 new script.

## Target UI structure (per non‑F‑4 record) — verified rendered
A. **Header** — shared code + Ko/En title + evidence badge (`공식근거 직접 확인` /
`관련 공식근거 있음` / `해당 없음`) + collapsible `근거 보기`; plus the small
`입국 전 사증발급` stage label.
B. **Summary** — one plain Korean paragraph (`visa-issuance-summary`).
C. **Application route chips** — `재외공관 신청` · `사증발급인정서` · `전자사증` ·
`비자포털 확인` · `초청기관·고용주 진행` · `공관별 확인 필요`(dashed “check” chip),
derived only from structured fields + the record's own source text (no invention).
`visa_exempt` / `not_applicable` routes correctly render **no** chips.
D. **Steps** — existing `issuance-steps` `<ol>` (matches the app's simple‑list convention).
E. **Documents** — shared `doc-group-grid` groups (공통/추가/해당 시), rendered by the
host panel; the card suppresses its duplicate copy.
F. **Warnings** — `issuance-warnings` calm caution block (not alarmist), data‑driven only.
G. **Source block** — shared `source-limitation-detail` accordion with manual,
section, page range, revision date, and friendly Korean evidence level.

Representative rendered output was captured by executing the real render chain
(see commands). Example — **D‑2** chips: `재외공관 신청 / 사증발급인정서 / 전자사증 /
공관별 확인 필요`; **E‑8** chips: `사증발급인정서 / 초청기관·고용주 진행 / 공관별 확인 필요`;
**B‑1 / H‑2**: no route chips, badge `해당 없음`.

## Non‑F‑4 codes tested (41)
D-2, D-4, D-10, E-7, E-8, E-9, F-1, F-2, F-6, G-1, H-2, C-3, B-1, B-2, D-8, C-4,
C-1, D-1, D-3, D-5, D-6, D-7, D-9, E-1, E-2, E-3, E-4, E-5, E-6, E-10, F-3, F-5,
H-1, A-2, A-3, D-4-1, D-4-2K, K-STAR, A-1, REGION-S, YOUTH-STAY.

Each was asserted (via `check_visa_issuance_ui.mjs`, 2233 checks) to expose a
Ko/En title, a friendly evidence level, a plain summary, ≥1 labelled route chip
for application routes (0 for `visa_exempt`/`not_applicable`), a Korean step list,
common/additional/conditional document groups, non‑empty warnings where present,
and a source/evidence pointer — with no bare placeholder values and no internal
enum tokens in any user‑facing string.

## F‑4 exclusion — verification
- **Guard:** `GENERIC_VISA_ISSUANCE_EXCLUDED_CODES = new Set(['F-4'])` +
  `isGenericVisaIssuanceExcluded(v.code)` short‑circuits `renderVisaIssuanceSection`
  (covers both the embedded 사증발급 tab and the standalone fallback). The protected
  F‑4 issuance record is left intact; exclusion is in code only.
- **Behavioural proof:** the render harness emitted `(empty string — NOT rendered)`
  for F‑4 while emitting full cards for D‑2/E‑8/B‑1/H‑2. The new smoke executes the
  real guard and confirms `guard('F-4'|'f-4'|'F4') === true` and
  `guard('D-2'|'E-7'|'F-5') === false`.
- **F‑4 special UI untouched:** `assets/js/f4-route-guide.js`, `data/f4/routes.json`,
  `data/f4/sources.json`, the `#f4RouteGuide` mount, `ROUTE_WIZARD_CONFIG['F-4']`,
  and F‑4 form‑name canonicalization were not modified. `check_f4_route_guide.mjs`
  passes **44/44** (43 original + 1 new exclusion assertion).

## Source‑grounding safeguards
- Chips/labels are derived from structured enum fields and from text **already
  present** in the record's own manual‑sourced label/appliesTo — never invented.
- No `필수서류` framing introduced; document group names stay neutral
  (공통/추가/해당 시 서류). Disclaimers, variance notes, caution blocks, and the
  `근거 보기` evidence accordion are preserved.
- Evidence levels render only through `getSourceEvidenceLabel()`; raw enums
  (`source_confirmed`, `consular_discretion`, `visa_exempt`, …) never surface.
- No protected file edited; no fee/timing/eligibility claim added. The official
  source hierarchy (local manuals → visa.go.kr → hikorea → mofa → law.go.kr) is
  unchanged.

## Commands run — exact results
```
node scripts/check_visa_issuance_ui.mjs        → 2233 checks, 0 failures (41 non-F-4 records); ALL PASS
node scripts/validate_visa_issuance_enrichment.js → 409 passed, 0 warnings, 0 failed
node scripts/check_f4_route_guide.mjs          → 44 checks, 0 failures; ALL PASS
node scripts/check_placeholder_suppression.js  → 19 passed, 0 failed
node scripts/check_static_visa_result_cards.js → OK
node scripts/check_index_hardcoded_text.mjs    → OK
node scripts/check_i18n_coverage.mjs           → OK — 1039 keys match across ko/en/zh-CN
node scripts/smoke_static_i18n.mjs             → OK (inline scripts parse)
node scripts/check_i18n.js                     → OK
python3 scripts/audit_duplicate_render_content.py --check → OK: 0 severe (discovered==audited==273)
python3 -m json.tool data/i18n/{ko,en,zh-CN}.json → valid JSON
```
Render verification: a throwaway harness executed the real `renderVisaIssuanceSection`
chain for D‑2/E‑8/B‑1/H‑2 (correct chips, calm warnings, friendly badges, deduped
近거) and F‑4 (empty); the harness was removed after use.

## Accessibility & responsive
- Route‑chip group uses `role="group"` + `aria-label`; the source block is a native
  `<details>/<summary>` (keyboard‑focusable, the existing `aria-expanded` accordion
  pattern). Semantic headings (`h5`/`h6`) retained.
- Chips `flex-wrap`; card is `min-width:0` with `word-break:keep-all` — no horizontal
  overflow at ≤640px (the global `html{overflow-x:hidden}` guard remains).

## Remaining known limitations
- No headless browser was available in this environment, so a pixel screenshot was
  not captured; rendering was verified by executing the real render functions and by
  the static + data smoke. (Prior PRs verified the live site at the same insertion point.)
- `official_web_overlays.json` is still seed‑only; the per‑country/post overlay
  `<select>` remains intentionally dormant until verified overlays exist.
- `bash scripts/check_repo.sh` was **not** run end‑to‑end here: its backend
  regression stage (13–14) requires FastAPI/httpx deps and a network `pip install`
  into `.venv-check`, and is a pre‑existing failure unrelated to this UI change
  (documented in `audits/visa-issuance-enrichment/02_validation_report.txt`). All of
  its static/i18n/render stages that this change touches pass individually (above).
  CI (`repo-validation.yml`) runs the full script with deps installed.
- The 3 `contextual` records (A‑1, REGION‑S, YOUTH‑STAY) and the `not_applicable`
  records (B‑1, B‑2, H‑2) intentionally show cautious badges and (for
  exempt/not‑applicable routes) no application‑route chips.
