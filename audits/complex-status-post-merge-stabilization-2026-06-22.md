# Complex status guide — post-merge stabilization audit (2026-06-22)

Strict post-merge audit of the complex status guide system (F-4 + F-6/G-1/E-7/
F-5/D-2/D-4) after PRs #457–#461 (and alongside the just-merged #462 HiKorea
helper, which is **out of scope** and untouched here).

**Outcome: no confirmed bugs or regressions found.** Per the task's critical
rule, this PR therefore adds **only** targeted regression coverage that locks the
audited invariants, plus this report. **No guide engine, config, data, i18n, or
UI file was changed** (no churn).

## 1. What was audited (static + functional, KO + EN)

For all seven statuses I loaded the **real** modules (`visa-route-guide.js`
adapter, `complex-status-guide.js`, `f4-route-guide.js`) and exercised their pure
render/result functions across **every available procedure**, in **KO and EN**,
inspecting the actual rendered strings for: empty cards, empty/fake source
panels, duplicate documents, prose leaks, raw i18n keys / `undefined`,
overconfident wording, and "공식근거 확인 필요" frequency.

## 2. Current implementation status

| Status | Level | Verified | Remaining gap |
| --- | --- | --- | --- |
| **F-4** | A (reference) | Recommended-start block + single CTA, full-screen flow, checklist result, source-safe; regression tests green; **not modified**. | — |
| **F-6** | A (visa issuance) / B | visa_issuance renders a real 9-item `doc_master` checklist + manual ref; F-6-1/2/3 subcodes source-safe; other procedures = manual ref + handoff. | extension/registration docs are prose, not `doc_master`-mapped. |
| **D-2** | B (strong) | 8 study subcodes; every procedure carries a manual reference; safe handoff for prose docs; distinct from D-4. | docs are prose (not `doc_master`-mapped). |
| **D-4** | B | 7 training subcodes; extension/reentry render the one resolvable `doc_master` item + manual ref; distinct from D-2. | mostly prose docs; `registration`/`statusChange`/`visa_issuance` have no data → safe needs-confirmation. |
| **E-7** | B | 11 occupation subcodes (manual-review codes excluded); extension manual ref; **does not** duplicate the job/industry analyzer. | only extension documented; cautious occupation note. |
| **F-5** | B/C | 8 active 영주 subcodes (22 manual-review placeholders excluded); 사증발급 not_applicable (not offered); cautious PR note. | only extension documented (sparse). |
| **G-1** | B/C | 16 reason-based subcodes, all review-gated; cautious note. | only extension has (1 prose) doc; `visa_issuance` has no data → safe needs-confirmation. |

## 3. Tests & QA coverage

- `scripts/check_complex_status_guide_qa.mjs` (the #461 offline guard, run in
  `check_repo.sh [9d-4]`) — extended this PR to **182 checks**, now including a
  new section that exercises **every status × every available procedure × KO/EN**
  and asserts each renders a *safe* result (no `undefined`, no prose leak, no
  overconfident wording, `sourceRefs` always an array) and that **data-less
  procedures degrade to a non-empty needs-confirmation result** (never an empty
  card or fabricated source). The banned-phrase list was expanded to the task's
  full set (added *definitely required, must be approved, 반드시 승인, 자격이 확정*).
- `scripts/check_complex_status_guide.mjs` (160) + `scripts/check_f4_*` (F-4
  regression) + the `tests/e2e/` Playwright suite (real-browser, run locally)
  remain in place.

## 4. Bugs found and fixed

**None.** No behavioral bug or regression was confirmed; no guide code was
changed.

## 5. Source-safety audit

- Scanned all user-facing rendered strings across all seven statuses × every
  available procedure × KO+EN: **zero** overconfident phrases (the expanded
  banned list). The only "guaranteed" occurrences in source are safe negations
  ("never/cannot be guaranteed").
- **No empty cards / fake source panels:** every result section renders content —
  resolved documents, a source-backed manual reference, or an explicit
  "공식근거 확인 필요 / Official source needs confirmation" + safe handoff.
- **"공식근거 확인 필요" is not over-triggered by a mapping bug.** Confirmed the
  camelKey mapping is correct (`visa_issuance → visaIssuance`); the data-less
  results for **G-1/E-7/D-4 `visa_issuance`** are genuine — those records have no
  `procedures.visaIssuance` entry in `visa_data.json`, while the tested adapter
  reports the procedure available. Showing needs-confirmation + handoff there is
  the correct, conservative behavior (we never invent docs/sources to fill it).

## 6. Files changed

| File | Purpose |
| --- | --- |
| `scripts/check_complex_status_guide_qa.mjs` | +regression section (safe result for every available procedure, incl. data-less ones) + expanded banned-phrase list. |
| `audits/complex-status-post-merge-stabilization-2026-06-22.md` | This report. |

No changes to `index.html`, `assets/js/*` guide modules, `data/*`, or `data/i18n/*`.

## 7. Commands run

- `node scripts/check_complex_status_guide_qa.mjs` → **182/182** ✅
- functional audit dump (per-procedure result, KO+EN) → 0 overconfident phrases,
  0 `undefined`, no all-empty status.
- `bash scripts/check_repo.sh` (ALLOW_BACKEND_TEST_SKIP=1) → **Success** — F-4
  regression (`check_f4_route_guide`/`smoke_f4_hub`/`check_f4_guide_flow`),
  `check_complex_status_guide`, `[9d-4]` QA matrix, i18n parity, and 251 + 26
  backend tests all pass. Only the network-gated golden eval is skipped.

## 8. Remaining risks / data gaps (honest)

- **Prose-vs-`doc_master` documents.** D-2/D-4/E-7/F-5/G-1 store procedure
  documents as prose, so the in-overlay checklist only lights up for `doc_master`-
  ID procedures (F-6 visa issuance today). Everything else routes to the
  source-backed card detail. Unchanged this PR (data work, not a bug).
- **Data-less `visa_issuance` for G-1/E-7/D-4.** Offered (adapter) but no record
  data → safe needs-confirmation result. Resolving requires source-reviewed data
  (add the procedure's docs/manual refs), not a code change.
- **Minor polish (not a bug, not changed):** when a procedure has no resolvable
  docs, the result shows a "전체 준비서류·절차 보기" handoff button in both the
  basic-docs section and the next-actions row (same action, two contexts).
- **Playwright suite unverified in CI** (browser egress blocked); the offline
  guard is the CI safety net.

## 9. Recommended next PR

A **source-reviewed data pass** that (a) maps the six statuses' prose procedure
documents to `doc_master` IDs and (b) adds the missing `visa_issuance` procedure
data (or marks it not_applicable) for G-1/E-7/D-4 where appropriate. That single
data task removes the remaining needs-confirmation results and unlocks real
in-overlay Level-A checklists — and it must be source-reviewed, not guessed.
Pair with a one-time local run of the `tests/e2e/` Playwright suite to verify it
and capture baseline screenshots.
