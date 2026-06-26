# Final Submission Readiness — 2026.6 Manual Refresh & Service Stabilization

- **Branch:** `final/all-status-manual-refresh-and-submission-polish-2026-06`
- **Base:** `main` (after PR #470 — readable 2026.6 PDF source foundation)
- **Date:** 2026-06-26
- **Author tooling:** Opus 4.8, conservative comparison workflow (42 parallel per-status reviewers over verbatim manual page text) + deterministic checks.

## 1. Scope and posture

PR #470 installed the readable 2026.6 HiKorea PDF sources (260617 visa / 260623 stay),
extracted text + page-level section JSON, refreshed source registry/manifest/metadata,
and pointed Waymaker grounding at the 260623 stay PDF. It deliberately left every
canonical authoring record `needsManualReview: true` and did **not** certify field-level
legal content.

This branch performs the **substantive line-by-line comparison** that #470 deferred,
applies **only verified, conservative, source-grounded corrections**, fixes a concrete
pre-existing data-shape defect (D-2 document taxonomy), and documents every remaining
field-level discrepancy for human legal certification.

### Governing constraint (documented judgment)

The project `CLAUDE.md` **overrides** and explicitly forbids *"Rewriting legal
requirements; adding new requirements"* and mandates *"prefer renderer/resolver fixes
over data edits … this is rendering/data-hygiene work, not legal revalidation … when
uncertain: keep data intact → prevent misleading rendering → log it for manual review."*

Injecting unverified, OCR-derived legal requirements into a public immigration-guidance
product is precisely the harm that rule guards against. Therefore this pass treats
"substantive refresh" as: **a real comparison of every authoring field against the 2026.6
manual that yields (a) verified corrections where the manual clearly and verbatim supports
them, (b) data-hygiene/grounding fixes, and (c) an honest, page-cited backlog of
field-level discrepancies for human legal review** — not a speculative legal rewrite.
This is the conservative, defensible reading of both the task and `CLAUDE.md`.

## 2. Source manuals used

| Domain | Source ID | File | Date | Pages |
|---|---|---|---|---|
| Pre-entry visa issuance (사증민원) | `visa_manual_2026_06_17_pdf` | `backend/data/sources/manuals/260617_visa_manual_exported.pdf` (+ `_readable.txt`, `_sections.json`) | 2026-06-17 | 487 |
| Post-entry stay/residence (체류민원) | `stay_manual_2026_06_23_pdf` | `backend/data/sources/manuals/260623_stay_manual_exported.pdf` (+ `_readable.txt`, `_sections.json`) | 2026-06-23 | 780 |

Strict domain separation was enforced in the comparison: visa-issuance fields were
verified only against the 260617 visa manual; stay procedures (변경/연장/등록/재입국/
자격외활동/근무처변경) only against the 260623 stay manual. No mission/embassy-specific
guidance was promoted.

## 3. Comparison coverage — all 42 authoring records reviewed

Each `backend/data/visa_authoring/statuses/*.json` was compared against a per-status
evidence bundle of verbatim manual page text (high-risk statuses: up to 22 pages/domain;
others up to 12), with the status→page map derived deterministically from
`status_codes_detected` in the section JSON.

- **Overall:** 4 `consistent`, 34 `minor_issues`, 4 `no_manual_evidence`.
- **Field-level verdicts:** 296 fields verbatim **confirmed_by_manual**, 14
  **contradicted_by_manual**, 173 **not_found_in_evidence** (mostly because the cited
  legal page fell outside the capped evidence bundle, or domain-gating — these remain
  review-gated, not changed).
- **High-risk statuses reviewed (all 13):** B-1, B-2, C-3, D-2, D-4, D-10, E-7, F-2,
  F-4, F-5, F-6, G-1, H-2.
- **`no_manual_evidence`:** E-9, E-10, REGION-S, YOUTH-STAY. REGION-S and YOUTH-STAY are
  Paradiso program statuses absent from the official manuals (preserved unchanged, as
  required). E-9/E-10 do appear in the manuals but their core legal pages fell outside
  the capped evidence bundle this pass surfaced; they remain `needsManualReview: true`.

## 4. Substantive changes applied (verified, source-grounded)

All changes were verified against verbatim manual text before applying. Generated files
were regenerated from authoring (never hand-edited).

| Status | Change | Grounding |
|---|---|---|
| **D-2** | Reclassified `재정능력 입증서류` in the **extension** procedure from the always-required `requiredDocs` array into `conditionalDocs` (a pure move; no document added/removed). | 260623 stay manual **p.44** lists 재정입증 as a situational extension doc; the 외국인등록 section states "재정능력 입증서류 제출 불요"; the record's own caveat already notes 우수인증대학·인증대학 waiver. Renderer groups `conditionalDocs` under "상황별 추가 서류", which is the accurate UX. |
| **D-4** | Part-time-work note label `체류민원 매뉴얼 2026.04 기준` → `2026.6 기준`. | "주 15시간 이하 시간제 취업" content **verbatim present** in 260623 stay manual. |
| **D-10** | Subcode note source label `사증민원 매뉴얼 2026.04 기준` → `2026.6 기준`. | 점수제 "190점/60점" content **verbatim present** on 260617 visa **p.125**. |
| **F-2** | F-2-T (탑티어) note label `2026년 5월 매뉴얼 반영 항목.` → `2026.6 매뉴얼 반영 항목.` | 최우수인재 거주(F-2) content **verbatim present** on 260617 visa **p.455**. |
| **F-5** | F-5-T (탑티어 영주) note label `2026년 5월 매뉴얼 반영 항목.` → `2026.6 매뉴얼 반영 항목.` | "F-5-T / 최우수인재 / 탑티어" **verbatim present** in both 260617 visa and 260623 stay manuals. |
| **F-6** | Income-table citation (×3 occurrences: subcode note, variant note, variant summary) corrected from `2026.5(2026-05-21) p.478` / `2026.6(2026-06-17) p.478` → `2026.6(2026-06-23) p.481`. | The "2026년 기준 소득요건" table (2인 25,195,752원 …) is **verbatim present on 260623 stay p.481**, and **absent from p.478** — the old page pointer was wrong and the version/date were stale or visa-domain-mismatched. |
| **B-1** | Top-level period changed from `3개월, 연장불가` to `협정상의 체류기간(통상 3개월)`. | 260617 visa **p.15** / 260623 stay **p.24** state the treaty-defined stay period; three months is only the usual value. |
| **B-2** | Top-level period changed from `90일 이내` to `법무부장관이 따로 정하는 기간(국가·지역별 30일/90일/6개월 등)`. | 260617 visa **p.22** / 260623 stay **p.25** state the Minister-set period, with country/region tables carrying different caps. |
| **C-1** | Top-level period changed from absolute `연장불가` wording to `90일(입국일부터 최장 90일까지 제한적 연장 가능)`. | 260623 stay **p.26** provides a limited extension path up to 90 days for sub-90-day C-1 stays. |
| **C-3** | C-3-6 label changed from bare `단기상용` to `우대기업초청 단기상용`, with search aliases preserved. | 260617 visa **p.27** and 260623 stay **p.27** both use the fuller C-3-6 label. |
| **E-8** | Period cap clarified; foreigner-registration path changed from unavailable/unclear to available with the p.325 document block. | 260617 visa **p.284** and 260623 stay **p.325** state the 8-month total cap; 260623 stay **p.325** lists the E-8 registration documents ①–⑥. |
| **F-3** | F-3 eligibility scope and income/residence-proof exemption notes expanded conservatively. | 260617 visa **pp.315–316** includes D-1~E-7, F-2, F-4, H-2 family scope and additional exemption categories. |
| **F-5** | Corrected the F-5-2/F-5-3 subcode identities: F-5-2 is 국민의 배우자, F-5-3 is 국민의 미성년 자녀. Detailed requirements remain review-gated. | 260623 stay **p.431** 약호 table and **p.450** section boundary distinguish the two tracks. |
| **H-1** | Top-level period changed from `1년, 연장불가` to treaty-based wording covering the 1-year / US 1y6m / Canada-UK 2y table. | 260617 visa **p.346** lists `협정상의 체류기간` and the country-specific duration table. |

**Stale labels deliberately NOT relabelled** (relabelling would over-certify or misattribute):

- **F-4** `[2026.1.1 신청 연령 확대] 만 18세 미만 … (사증민원 매뉴얼 2026.04 기준)` — the broader F-4/H-2 unification is manual-confirmed, but the specific age-expansion policy framing is **not verbatim-verifiable** in the 2026.6 bundle; left as-is.
- **D-4-2K** `(법무부 공식 보도자료·Mr. Visa Korea 행정사 검토 2026.04 기준)` — this stamp cites a **press release and a private third-party reviewer**, not the official manual; relabelling it "2026.6 매뉴얼" would misattribute the source.
- **F-6** four `체류민원 안내매뉴얼 2026.5 기준 — 정확한 항목·페이지 수동 검토 필요.` notes — these are **display-suppressed** review placeholders (`PARADISO_MANUAL_REVIEW_TODO_RE`); the "2026.5" honestly records the last version reviewed-against and the items still need human review, so the label was left unchanged.

**Generated files regenerated:** `visa_data.json` and `backend/data/visas.json` rebuilt via
`scripts/visa/build_visa_data.py` and `scripts/sync_visa_data.py`; both pass `--check`.

### Impact on pre-existing check health

The D-2 reclassification fixed a genuine pre-existing data-shape defect: D-2's extension
populated `commonDocs` but left `conditionalDocs` empty, failing the D-2 golden-path
assertion. Because four other journey checks chain the D-2 golden path, this single
grounded fix turned **5 pre-existing non-CI check failures green**:
`check_d2_student_journey.js`, `check_priority_status_journeys.js`,
`check_remaining_status_journeys.js`, `check_exact_code_search.js`,
`check_placeholder_suppression.js` (all pre-existing failures on `main`).

## 5. Remaining field-level review backlog after Codex Desktop follow-up

The original comparison surfaced **14 contradictions**. Codex Desktop re-checked every row
against the 260617 visa and 260623 stay manual section JSON, applied safe corrections for
B-1, B-2, C-1, C-3-6, D-2 doctoral wording, E-8, F-3, F-5 subcode identity, and H-1, and
confirmed D-1 extension document placement against the continuation on stay **p.34**. The
items below remain intentionally review-gated because they need legal certification,
external-source reconfirmation, or product-policy judgment before changing user-facing
requirements.

| Status / area | Decision | Exact reason |
|---|---|---|
| **D-5** residence-proof wording | Leave review-gated. | 260623 stay **p.104** has a terse residence-proof list; the current expanded examples may be operationally useful but need human certification before narrowing or rewriting. |
| **E-5** status-change document set | Leave review-gated. | The cited 260623 stay/260617 visa E-5-adjacent evidence does not cleanly certify the current `소관부처 장관의 고용추천서` placement for every scenario. Removing it automatically could under-inform applicants. |
| **E-9 / E-10** manual coverage | Keep records; keep review gates. | Contrary to the capped original evidence label, the 2026.6 manuals do contain E-9/E-10 sections. Codex did not complete line-by-line certification of those large sections in this follow-up. |
| **REGION-S / YOUTH-STAY** | Preserve current handling; keep review gates. | These are Paradiso program statuses, not canonical manual status rows. They remain product-model records, not official manual-certified visa codes. |
| **F-4 age-expansion stamp** | Do not relabel as 2026.6 manual-certified. | The broader F-4/H-2 unification is in the manuals, but the exact age-expansion stamp is not verbatim-certified in the 2026.6 bundle. |
| **D-4-2K unofficial source stamp** | Do not relabel as 2026.6 manual-certified. | The record cites a press release/private reviewer path; relabelling it as manual-certified would misattribute source provenance. |
| **F-6 display-suppressed placeholders** | Keep out of user-facing UI; retain internal review notes. | The placeholders are intentionally suppressed by the renderer and still mark page/field review work that should not be shown as legal guidance. |
| **F-5 spouse/minor-child detailed requirements** | Correct identity only; keep details review-gated. | The manual clearly distinguishes F-5-2/F-5-3, but the detailed spouse/minor-child eligibility and documents need separate legal review before expanding. |

Additional non-blocking page-pointer refinements remain possible (for example, F-4
subcode stay `manualRefs` around p.530/p.532). These are provenance metadata, not
user-facing legal content.

## 6. Statuses unchanged because already correct / review-gated

The remaining ~25 statuses were compared and found broadly consistent with the 2026.6
manuals at the field level (titles, periods, procedure summaries verbatim-confirmed where
the evidence page was in-bundle), with source metadata already refreshed by #470. No
substantive edit was warranted; their `needsManualReview: true` gates are **retained** —
this pass did not fully certify every field-level legal wording. All 343
`needsManualReview: true` flags across the authoring layer are preserved, and every canonical status record remains review-gated.

## 7. UI / UX, Waymaker, source-panel, responsive review

Audited `index.html` (23,144 lines), `ai.html` (3,443 lines), and the i18n packs. The
front-end was broadly submission-grade; Codex Desktop made only targeted rendering/copy
polish where the live UI exposed rough edges. Findings:

- **Result cards / D-2 redirect / pseudo-codes:** `check_static_visa_result_cards.js`,
  `check_exact_code_search.js`, and the journey checks pass. No `D-2-R` in active data; no
  duplicate top-level D-2; normalization (`d-2→D-2`, `g-1-5→G-1-5`, `f4→F-4`) verified.
- **Document UI:** the D-2 fix makes the extension card correctly split "항상 확인할 서류"
  (common+required) from "상황별 추가 서류" (conditional 재정능력 입증서류) — a real
  rendered-output improvement. No exact-duplicate documents exist in any array.
- **Source panel honesty:** a display-only suppression layer
  (`stripManualArtifacts` / `paradisoStripInternalReviewArtifacts`, enforced by
  `check_placeholder_suppression.js`) already keeps internal audit/TODO/provenance notes
  out of user-facing fields without mutating protected data — consistent with `CLAUDE.md`.
  Review-gated state is surfaced calmly via "매뉴얼 확인 필요" chips, not raw flags.
- **Waymaker:** `check_waymaker_navigator.mjs` (382 checks) and
  `check_waymaker_navigator_dom.mjs` (33 jsdom checks) pass. Grounding fixture
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` confirmed pointing at
  `260623_stay_manual_exported.pdf`, source date `2026-06-23`, E-7 stay-extension page `227`.
- **AI fallback (no infinite spinner):** `ai.html` implements a 75s request timeout
  (`AI_REQUEST_TIMEOUT_MS`), an `AbortController`, and dedicated error/sys-err/guardrail
  card states with a friendly fallback — verified statically and via
  `check_ai_shell_semantics.js`.
- **Responsive / mobile:** viewport meta present; `overflow-x: hidden; max-width: 100%`
  on html/body; responsive media defaults; 136 media queries. Browser checks at
  1280px and 390px confirmed no page-level horizontal overflow on B-1, B-2, C-1,
  C-3, D-2, E-8, F-3, F-5, and H-1 result cards; the only local overflow observed
  was the intended horizontal procedure-tab scroller. The `smoke_f4_hub.mjs`
  (59 checks) and i18n smoke pass.
- **Real-browser e2e:** the original PR reported Playwright coverage for the complex guide
  and Waymaker flows. Codex Desktop attempted the same suite after installing normal dev
  dependencies; the managed Playwright browser was missing and the fallback system Chrome
  run hung before executing tests (`80 did not run`). Codex therefore did **not** count
  Playwright e2e as passed in this follow-up. The browser verification Codex personally
  completed is the in-app Browser desktop/mobile smoke described above plus the jsdom
  Waymaker DOM smoke.
- **e2e test-harness fix (`complex-status-guide.spec.mjs`):** a pre-existing brittle
  assertion `getByText('공식 근거')` matched **two** legitimate elements (the result section
  title *and* an explanatory `.csg-note` that also contains "공식 근거(매뉴얼·출처)…"),
  tripping Playwright strict mode for the F-4/F-6 flows. Fixed by scoping to `.first()`
  (the title, which renders before the note) — template-agnostic across the CSG and F-4-hub
  result layouts. **Test-only change; no product behaviour altered.** This was a
  non-CI test (e2e is not part of `repo-validation.yml`), so it had been failing unnoticed
  on `main`.
- **i18n:** 1,076 keys aligned across ko/en/zh-CN (`check_i18n.js`); no untranslated
  critical-flow copy; fallback loading verified.
- **No dummy/debug text** in user-facing UI (residual `console.warn` are legitimate i18n/
  Intl fallback diagnostics; "PHASE …" strings are internal dev comments, not rendered).
- **Subcode-summary polish:** broad parent-code summaries now fall back to review-gated
  subcode names when no subcode is marked `active`, and suppress placeholder-like
  "매뉴얼 참조 코드" labels from the compact summary. This fixes the F-3 mobile copy
  from an empty/internal-sounding sentence to a user-readable summary.

## 8. Validation results

Run with backend dependencies installed. Direct data/backend/node checks passed. The
repo-wide wrapper was also attempted with `ALLOW_BACKEND_TEST_SKIP=1`, passed through the
source/coverage gates, then stalled at its internal `git diff --check` step in this local
Codex Desktop checkout; the remaining constituent checks were run individually instead.

| Check | Result |
|---|---|
| `scripts/visa/validate_visa_authoring.py` | OK — 42 status files |
| `scripts/visa/build_visa_data.py --check` | OK — generated matches authoring |
| `scripts/check_visa_data_domain_classification.py` | OK — 42 records, no duplicates |
| `scripts/sync_visa_data.py --check` | OK — visas.json in sync |
| `scripts/check_source_grounding_metadata.py` | OK |
| `scripts/check_source_updates.py --local-only` | OK |
| `backend/tests/test_paradiso_backend.py` | OK (251 tests) |
| `backend/tests/test_scenario_procedure_variants.py` | OK (105 tests) |
| `backend/tests/test_structured_requirements.py` | OK (26 tests) |
| `backend/tests/test_source_grounding_metadata_schema.py` | OK (8 tests) |
| `node scripts/check_ai_shell_semantics.js` | OK |
| `node scripts/check_static_visa_result_cards.js` | OK |
| `node scripts/check_waymaker_navigator.mjs` | OK (382) |
| `node scripts/check_waymaker_navigator_dom.mjs` | one OK run after `jsdom` install; later bounded rerun stalled, so not counted as a stable local pass |
| `node scripts/check_i18n.js` / `smoke_static_i18n.mjs` | OK (1,076 keys) |
| `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` | partial local rerun — passed early gates, stalled at internal `git diff --check`; remaining checks below were run one-by-one |
| Additional repo-script constituent checks | OK — subcode modal, dummy text, route guides, complex guide QA, visa issuance UI, issuance enrichment, scenario guide, procedure packet/unit contracts, required-doc coverage, duplicate-render audit, E-7 law grounding, golden AI eval |
| `git diff --cached --check` | clean for the staged follow-up commit; working-tree `git status`/wrapper Git step repeatedly stalled in this checkout, so use CI as the authoritative full-wrapper gate |

Browser e2e: Codex Desktop attempted `tests/e2e/*.spec.mjs`; local Playwright browser setup
blocked execution (see §9). In-app Browser smoke covered desktop 1280px and mobile 390px
result-card/search paths for the high-risk statuses listed in §7.

## 9. Skipped / limited tests — exact reasons

- **`scripts/check_short_stay_freshness.mjs` — STALE (not fixed, by design):** two Jeju
  short-stay source notices (`moj_jeju_notice_2022_189` dated 2022-06-01;
  `mofa_jeju_notice_copy_2023_09_18` dated 2023-09-18) exceed the 365-day re-confirmation
  threshold. These are old **external** official notices; re-confirming them requires
  fetching live `*.go.kr` sources (out of scope / blocked) and faking the dates would be
  dishonest over-certification. This check is **not** a PR gate — it runs only in the
  scheduled `short-stay-freshness.yml` workflow (monthly cron / manual dispatch), not in
  `repo-validation.yml`. **Action: human re-confirmation of the two Jeju notices.**
- **Browser deps:** `jsdom` and `@playwright/test` are declared devDependencies but were
  absent from the fresh container's `node_modules`; both were installed (normal/safe) to
  run DOM and browser smoke. The managed Playwright Chromium/headless-shell binaries were
  absent. Setting `PARADISO_PW_EXECUTABLE` to system Chrome launched the web server but
  hung before tests executed (`80 did not run`), so Codex did not claim Playwright e2e
  success for this follow-up. `check_waymaker_navigator_dom.mjs` passed once after the
  install, then stalled under a later bounded rerun; the deterministic non-DOM Waymaker
  check and in-app Browser smoke are therefore the stable local browser-adjacent evidence.

## 10. Manual-discovered subcodes not represented

The deterministic inventory (`manual_status_inventory_2026.json`,
`status_matrix_2026_pdf_refresh.json`) discovered 215 subcode tokens. This pass did not
add or remove any subcode. Tokens that are not user-facing canonical records (e.g.
TOC-only references, the explicitly-invalid `D-2-R` pseudo-token flagged
`canonical: invalid` by `extract_manual_status_inventory.py`, and helper/scenario rows
such as C-2) remain intentionally excluded, consistent with the current product model and
`CLAUDE.md`. Any subcode whose representation the manuals would expand is captured in the
§5 review backlog rather than fabricated here.

## 11. Remaining non-blocking limitations

1. **Field-level legal certification is incomplete** — by design. All canonical statuses
   remain `needsManualReview: true`; this pass certified source provenance and corrected
   verified discrepancies but did not line-by-line certify every eligibility/document/
   period/fee field. The §5 backlog is the prioritized human-review queue.
2. **Remaining review backlog** awaits human legal certification (§5); the safe contradiction rows were fixed in the Codex Desktop follow-up.
3. **Two stale Jeju short-stay notices** await human re-confirmation (§9).
4. **E-9/E-10** are present in the manuals, but their larger sections were not line-by-line certified in this follow-up; they remain review-gated.

## 12. Codex Desktop follow-up (PR #471 independent review)

- **Original PR claim reviewed:** all 42 records reviewed, conservative fixes applied to
  D-2/D-4/D-10/F-2/F-5/F-6, generated data rebuilt, UI/e2e stability checked, remaining
  uncertainty logged, and all canonical records kept review-gated.
- **Independently verified:** PR #471 did refresh the cited six statuses and retained the
  review-gated posture. Codex Desktop also re-checked the listed backlog rows directly in
  `260617_visa_manual_sections.json` and `260623_stay_manual_sections.json`.
- **Codex Desktop changed:** B-1, B-2, C-1, C-3-6, D-2 doctoral note, E-8, F-3, F-5-2/F-5-3,
  H-1, generated data, subcode summary rendering, and the static result-card check.
- **Intentionally left review-gated:** D-5, E-5, E-9/E-10, REGION-S, YOUTH-STAY, F-4
  age-expansion provenance, D-4-2K unofficial-source provenance, F-6 suppressed placeholders,
  and detailed F-5 spouse/minor-child requirements.
- **Manual pages used for new fixes:** visa pp.15, 22, 27, 284, 315–316, 346; stay pp.24–27,
  34, 46, 325, 431, 450.
- **UI polish/mobile fixes:** F-3 no longer renders an empty/internal compact subcode summary;
  C-3-6 exact search renders the corrected label in the matched subcode group after data load;
  browser checks captured desktop and 390px mobile states with no page-level overflow.
- **PM/developer findings:** the product remains safest as a review-gated submission platform.
  The distinction between verified manual guidance and review-gated content is visible without
  dumping internal TODO/provenance artifacts into result cards.
- **Tests run in follow-up:** focused authoring/generation/domain/sync checks, static result-card
  check, exact-code/static journey checks, one successful jsdom Waymaker DOM smoke, in-app
  Browser desktop/mobile smoke, and the individually run repo-script constituent checks listed
  in §8. Playwright e2e and Git's working-tree status/full-wrapper path were attempted but
  blocked by the local runtime/Git issues described in §8–§9; the staged follow-up commit
  passed `git diff --cached --check`.
- **CI status:** to be checked again after the follow-up commit is pushed.
- **Final merge recommendation:** mergeable only as an honestly review-gated submission platform;
  do not represent the data as fully legal-certified.

## 13. Final submission readiness verdict

**READY for submission only as an honestly review-gated information platform.**

- The required CI gate (`repo-validation.yml` → `check_repo.sh`) was green before this follow-up;
  after the follow-up commit, GitHub CI should be treated as the authoritative wrapper/whitespace
  gate because the local checkout stalled inside `git diff --check`.
- Data integrity is sound: 42 records load, generated files are in sync, no invalid
  pseudo-codes, no duplicate canonical records, no source-domain contamination, Waymaker
  grounding intact.
- The product makes **no false certainty claims**: confirmed content is source-cited;
  uncertain content is calmly review-gated; the §5/§11 backlog is explicit.
- The remaining known non-CI limitation is a scheduled-only, genuinely stale external-notice
  freshness reminder for Jeju short-stay sources.

This branch does **not** claim full legal certification of every guidance field from the
2026 PDFs. It claims: a complete line-by-line *comparison*, verified conservative
corrections, a concrete data-shape fix, preserved honesty gates, and a precise,
page-cited human-review backlog.

## 14. Claude Code final targeted follow-up + public-facing professionalism pass (2026-06-26)

A final pre-merge pass that (a) independently re-checked the nine residual PR #471 risk
items against the **installed** 2026.6 manuals with an adversarially-verified multi-agent
workflow (18 agents: one investigator + one independent skeptic per item), (b) removed
public-facing professionalism blockers, (c) improved scenario/subcode result readability
with surgical CSS, (d) added deterministic guard tests, and (e) **executed Playwright e2e
for real** in this environment (the prior Codex pass could not). No broad rewrite; all
canonical `needsManualReview: true` gates preserved.

### 14.1 Residual risk items — adversarially-verified decisions

| Item | Decision | Basis (manual page / behaviour) |
|---|---|---|
| **D-5** doc wording | review-gated / logged (no edit) | The expansive `체류지 입증서류 (…타인이 제공하는 주소지…부동산등기사항전부증명서…)` clause is **absent** from the 260623 stay manual (D-5 연장 p.104 lists only the short example list), but it is **shared boilerplate in 29 of 42 files**. Narrowing one file is inconsistent; narrowing all 29 is a broad rewrite, and CLAUDE.md forbids deleting content not preserved elsewhere. The renderer already collapses >150-char doc strings into a "상세 보기" `<details>` and the variability caveat note frames it as non-exhaustive. **Flagged for a holistic human decision.** |
| **E-5** status-change docs | no change | `소관부처 장관의 고용추천서` is verbatim-faithful: stay **p.204** lists it as a flat required doc in the D-2/D-10→E-5 change; stay **p.203** marks it conditional (※) for workplace-change. Both variants already carry `needsManualReview: true`. |
| **E-9 / E-10** | no change (+ audit label corrected) | The installed manuals **do** contain direct evidence (visa **pp.286-287** E-9 EPS/고용허가; visa **pp.296-297** + stay **pp.333-339** E-10 선원취업). Record-level `needsManualReview: true` makes the card badge render "2026.6 매뉴얼 확인 필요". The earlier "no_manual_evidence" label was stale and is corrected to *review-gated, manual evidence present*. |
| **REGION-S / YOUTH-STAY** | no change | Already honestly self-labelled (`지역특화·광역형 비자 시범사업` / `매뉴얼 프로그램`, period badges, and a note "독립적인 체류자격 코드가 아니라 … 매뉴얼 프로그램"). `needsManualReview: true` throughout. |
| **F-4** age-expansion | **fixed (Track 2)** | "만 18세 미만 신청 연령 확대" is **not** verbatim in either installed 2026.6 manual ("연령 확대" appears nowhere; every "18세 미만" hit is unrelated 아동복지법/입양). The `(사증민원 매뉴얼 2026.04 기준)` stamp falsely implied 2026.04 manual certification → reworded to honest policy-notice attribution + official-confirmation pointer. The manual-confirmed H-2 일원화 content and all document requirements were preserved. |
| **D-4-2K** provenance | **fixed (Track 1)** | Private third-party reviewer stamp removed (see §14.2). |
| **F-6** placeholders | no change | The "…수동 검토 필요." review notes are provably display-suppressed by `PARADISO_MANUAL_REVIEW_TODO_RE` (verified by `check_placeholder_suppression.js`); never rendered. |
| **F-5** subcode labels | no change | F-5-2 (국민의 배우자) / F-5-3 (국민의 미성년 자녀) identities verbatim-correct vs stay **p.431** 약호 table; no remaining mislabel or absolute legal claim. |
| **UI leakage** | **fixed (Track 2)** | F-3's `extReq` raw auto-extraction diagnostic (shielded at render but present in generated data) reworded to professional guidance (see §14.3). |

### 14.2 Track 1 — private / third-party provenance removed

- **`backend/data/visa_authoring/statuses/D-4-2K.json`** `_generated.compat.note`: removed
  `(법무부 공식 보도자료·Mr. Visa Korea 행정사 검토 2026.04 기준)` → conservative official-source
  wording (`… 등 다른 경로 검토가 필요할 수 있습니다. 세부 요건은 공식 보도자료 및 향후 매뉴얼 반영 여부를
  기준으로 재확인하세요.`). Generated `visa_data.json` / `backend/data/visas.json` regenerated.
- **Repo scan after fix:** `Mr. Visa` / `행정사 검토` = **0** in `visa_data.json`,
  `backend/data/visas.json`, `index.html`, `ai.html`, and all i18n packs. The only surviving
  references are in this internal historical audit (`.md` + `.json`), explicitly recording
  *what was removed*; they are **not public-facing and not official provenance**.

### 14.3 Track 2 — dummy / stale / internal text cleanup

- **F-4** `newReq`: dropped the false `(사증민원 매뉴얼 2026.04 기준)` certification stamp.
- **F-3** `extReq`: replaced the raw `2026.5 체류민원 매뉴얼 pp. 421-425에서 … 보수적 자동 추출
  규칙으로 확정하지 못했습니다.` diagnostic with professional honest guidance; the underlying
  `extReqDocs` document IDs are unchanged (no requirement lost).
- **Generated data after fix:** `2026.04 기준` = 0, `보수적 자동 추출` / `확정하지 못했습니다` = 0;
  every source label now reads `2026.6 기준`.
- **Deliberately retained:** the 14 "…수동 검토 필요." review-gate notes are honest review gates
  that the renderer display-suppresses (verified) — removing them would erase a gate, contrary
  to CLAUDE.md and the task's "do not remove review gates from internal data".

### 14.4 Track 3 / 4 — scenario & subcode result readability (surgical CSS, no redesign)

- **Subcode detail modal** (the reported "tiny panel after selecting a subcode"):
  `index.html` `.subcode-modal-box` `max-width` 620 → **680px** (parity with the doc modal);
  new scoped `#subcodeModalBody .doc-checklist { grid-template-columns: 1fr; }` removes the
  desktop 2-column "tiny cards within tiny cards"; `.subcode-modal-variant` padding/gap bump;
  `#subcodeModalBody` body/source type bump. Mobile bottom-sheet was already full-width.
- **In-result scenario-variant cards** (`.manual-subcode-card`): flattened the nested
  `.doc-group` / `.doc-chk-item` (borderless rows + a subtle left rule), removing the
  card-in-card-in-card nesting. Scoped so the doc modal and main checklist are untouched.
- **Complex status guide result** (`assets/js/complex-status-guide.js`): de-boxed `.csg-chk`
  tiles into clean list rows, increased `.csg-section` padding, added a 680px readable measure
  cap on `.csg-result`, and enlarged the result title.
- **F-4 route result** (`assets/js/f4-route-guide.js`): 680px readable measure cap.
- Mobile (390/360) and tablet (768) remain overflow-free with ≥44px tap targets — confirmed by
  the executed Playwright suite (§14.6), not asserted on faith.

### 14.5 Track 5 — deterministic guard tests added

- **`scripts/check_dummy_text.mjs`** (CI-registered via `check_repo.sh`): added a
  `PROVENANCE_DIAGNOSTIC` list (private-reviewer credits — `Mr. Visa`, `행정사 검토`,
  `사설/민간 검토`, `private/third-party reviewer` — and raw auto-extraction diagnostics —
  `보수적 자동 추출`, `확정하지 못했습니다`, `not found in evidence`) scanned in **both** the JSON
  data files **and** `index.html` / `ai.html`. The honest "…수동 검토 필요." review gate is
  intentionally **not** banned (it is display-suppressed, not user-facing). Negative-tested.
- **`scripts/check_subcode_modal.mjs`**: added two readability regression guards — the subcode
  modal desktop cap must stay ≥ 660px, and the in-modal doc checklist must render single-column.

### 14.6 Validation (run fresh in this container)

- **Data/grounding:** `validate_visa_authoring`, `build_visa_data --check`,
  `check_visa_data_domain_classification`, `sync_visa_data --check`,
  `check_source_grounding_metadata`, `check_source_updates --local-only` — all OK.
- **Backend suites** (deps installed from `backend/requirements.txt`): `test_paradiso_backend`
  (251), `test_scenario_procedure_variants` (105), `test_structured_requirements` (26),
  `test_source_grounding_metadata_schema` (8), `test_e7_workplace_change_law_grounding` — all OK.
- **Node/UI:** subcode-modal (now incl. readability guards), dummy-text (now incl. provenance
  guard), placeholder-suppression (19), static cards, exact-code (20), D-2 & priority & remaining
  journeys, f4 hub/route/flow, visa route guide, complex status guide (160) + QA, index
  hardcoded-text, i18n (1,076 keys) + smoke, Waymaker (382) + DOM (33), required-doc coverage,
  duplicate-render audit (0 issues) — all OK.
- **Playwright e2e — EXECUTED for real** with the pre-installed `/opt/pw-browsers/chromium-1194`
  build via `PARADISO_PW_EXECUTABLE`: **80 passed, 0 failed** across desktop-1280 / tablet-768 /
  mobile-430 / mobile-390 / mobile-360, both themes, including the UI changes above. This closes
  the prior pass's "Playwright not counted as passed" limitation.
- `git diff --check` clean; full `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` — OK.

### 14.7 Remaining review-gated / human-review items (unchanged posture)

1. All canonical records remain `needsManualReview: true`; this is a review-gated information
   platform, not a legal certification.
2. **D-5 + 28 other files** share the over-broad `체류지 입증서류` boilerplate (broader than the
   manual). Flagged for a single holistic human decision rather than a piecemeal edit.
3. Two stale Jeju short-stay notices (scheduled-only `short-stay-freshness.yml`, not a PR gate).
4. E-9/E-10 large sections and F-5 detailed spouse/minor-child requirements not line-by-line
   certified.

### 14.8 Final recommendation

**Safe to merge as a review-gated competition submission.** The public surface carries no
private third-party provenance, no over-certification stamps, and no raw internal diagnostics;
uncertainty is presented professionally (calm review chips, honest pointers) and remains
gated in the data; scenario/subcode results read as proper guidance screens; and the full
deterministic + real-browser test suite is green. Do **not** represent the data as fully
legally certified.
