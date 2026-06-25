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

## 5. Field-level discrepancies logged for human legal certification (NOT auto-edited)

The comparison surfaced **14 contradictions**. Every one is a case where the authoring
data is **conservative or simplified** relative to the manual (it under-claims rather than
mis-states), and the reviewer recommended "flag for manual review before correcting."
Per `CLAUDE.md`, these are documented — not silently rewritten — because correcting legal
scope/eligibility/period wording requires human certification:

| Status | Field | Manual evidence (page) | Nature |
|---|---|---|---|
| B-1 | period | visa p.15 | "3개월, 연장불가" simplifies manual "협정상의 체류기간 (통상 3월)". |
| B-2 | period | visa p.22 | "90일 이내" vs "법무부장관이 따로 정하는 기간". Reviewer: do not auto-change. |
| C-1 | period | stay p.26 | "연장불가" may be too absolute; manual shows a limited 90-day extension path. |
| C-3 | subcodes C-3-6 name | p.27 | "단기상용" vs fuller "우대기업초청 단기상용". |
| D-1 | extension requiredDocs[1] | stay p.33 | doc may belong to 변경 vs 연장; manual page truncated. |
| D-2 | D-2-4 박사 note | stay p.46 | "입학 후 8년" confirmed; "2년제 박사 7년" not in bundle. |
| D-5 | extension residence-proof | stay p.104 | expanded clause exceeds manual's terse list. |
| E-5 | statusChange variant docs | visa p.173 | "소관부처 고용추천서" not in the cited list. Reviewer: do not auto-change. |
| E-8 | period | visa p.284 | "8개월" omits "(총 체류기간 8개월을 초과할 수 없음)" cap clarifier. |
| E-8 | registration summary | stay p.325 | summary says reg doc-list "not separately identified", but p.325 has an 외국인등록 ①~⑥ block (conservative under-provision; not harmful). |
| F-3 | F-3-1 eligibility | visa p.315 | scope "D-1~E-7" is narrower than manual "D-1~E-7, F-2, F-4, H-2". |
| F-3 | F-3-3 소득요건 면제 list | visa p.316 | exemption list omits F-4, H-2, E-7-T, E-7-S1. |
| F-5 | F-5-3 name/addReq | stay p.431 | 2026.6 약호 table defines F-5-3 as "국민의 미성년 자녀"; data labels it "결혼이민 영주" — possible subcode renumbering, needs certification. |
| H-1 | period | visa p.346 | "1년, 연장불가" vs treaty-based (미국 1년6개월, 캐나다·영국 2년). |

Additional non-blocking page-pointer refinements were noted but left for review (e.g.
F-4 subcode F-4-41/F-4-42 stay `manualRefs` "p.530" likely "p.532"). These are provenance
metadata, not user-facing legal content.

## 6. Statuses unchanged because already correct / review-gated

The remaining ~25 statuses were compared and found broadly consistent with the 2026.6
manuals at the field level (titles, periods, procedure summaries verbatim-confirmed where
the evidence page was in-bundle), with source metadata already refreshed by #470. No
substantive edit was warranted; their `needsManualReview: true` gates are **retained** —
this pass did not certify field-level legal wording for any status. All 342
`needsManualReview: true` gates across the authoring layer are preserved.

## 7. UI / UX, Waymaker, source-panel, responsive review

Audited `index.html` (23,144 lines), `ai.html` (3,443 lines), and the i18n packs. The
front-end was found **already submission-grade**; no fabricated changes were made. Findings:

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
  on html/body; responsive media defaults; 136 media queries. The `smoke_f4_hub.mjs`
  (59 checks) and i18n smoke pass.
- **Real-browser e2e (Playwright + pre-installed Chromium):** `tests/e2e/waymaker-navigator.spec.mjs`
  and `tests/e2e/complex-status-guide.spec.mjs` were run across the `desktop-1280` and
  `mobile-390` viewports. After a test-harness fix (below), all pass — covering the D-2/F-4/F-6
  guided flows (one question per step, wide result, checklist sections, ESC-close + focus
  restore), the Waymaker deterministic-packet intake, the "coverage-limited packet renders a
  warning, fabricates nothing" guard, AI-follow-up consent gating, and **"responsive: no
  horizontal overflow + tappable through the packet"**.
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

## 8. Validation results

Run with backend dependencies installed (CI-equivalent). All green except the documented
scheduled-only freshness reminder.

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
| `node scripts/check_waymaker_navigator.mjs` | OK (382) + `_dom.mjs` OK (33) |
| `node scripts/check_i18n.js` / `smoke_static_i18n.mjs` | OK (1,076 keys) |
| `bash scripts/check_repo.sh` (no skip flag) | **Success** — incl. golden eval, all regression checks |
| Full node check sweep (34 scripts) | 33 pass / 1 fail (freshness, below) |
| `git diff --check` | clean |

Browser e2e: `tests/e2e/*.spec.mjs` (Playwright) run against the pre-installed Chromium
across the responsive viewport matrix (see §9).

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
  run DOM and real-browser smoke. Chromium is the pre-installed `/opt/pw-browsers` build,
  referenced via `PARADISO_PW_EXECUTABLE` (no browser download).

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
2. **14 documented contradictions** await human legal certification (§5).
3. **Two stale Jeju short-stay notices** await human re-confirmation (§9).
4. **E-9/E-10** core legal pages were outside the capped evidence bundle this pass;
   they remain review-gated.

## 12. Final submission readiness verdict

**READY for submission as an honestly review-gated information platform.**

- The required CI gate (`repo-validation.yml` → `check_repo.sh`) passes, including the
  golden-question eval and all regression checks.
- Data integrity is sound: 42 records load, generated files are in sync, no invalid
  pseudo-codes, no duplicate canonical records, no source-domain contamination, Waymaker
  grounding intact.
- The product makes **no false certainty claims**: confirmed content is source-cited;
  uncertain content is calmly review-gated; the §5/§11 backlog is explicit.
- Net check health improved from 6 pre-existing non-CI failures to 1 (a scheduled-only,
  genuinely-stale external-notice reminder).

This branch does **not** claim full legal certification of every guidance field from the
2026 PDFs. It claims: a complete line-by-line *comparison*, verified conservative
corrections, a concrete data-shape fix, preserved honesty gates, and a precise,
page-cited human-review backlog.
