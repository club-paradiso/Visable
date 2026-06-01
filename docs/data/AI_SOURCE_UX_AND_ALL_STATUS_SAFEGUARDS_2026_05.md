# AI Source UX & All-Status Safeguards (2026-05)

Combined work for the intended PR #240 (AI source/grounding UX) and PR #241
(all-status safeguards), expanded from a "high-risk statuses only" scope to an
**all-status scenario-family sweep**.

This change is deliberately additive and small-surface. It does **not** add a
new batch of scenario variants, does not rewrite the AI pipeline, and does not
redesign the UI.

---

## 1. Source-panel UX changes (`index.html` → `renderGroundingSourcePanel`)

The panel already distinguished several grounding dimensions (PR #238). This
change makes the **four states** clearly readable and adds the missing
needs-review explanatory line and an advisory fallback.

| State | Row label | Status text / badge | Notes |
|-------|-----------|---------------------|-------|
| **Source-confirmed / manual deterministic** | `행정 매뉴얼 근거` | `매뉴얼 출처 확인됨 · 참고용` (badge `출처 있음`) | Now explicitly *reference-only* and "법적 결정이 아니며" — strong, but never a legal decision. |
| **Needs-review scenario variant** | `시나리오별 서류 근거` | `매뉴얼 기반 후보 · 최종 확인 필요` (badge `검토 필요`) | Up to **4 safe items** (`visa_code · procedure_key · label/variant_id · page_range`), overflow `외 N건`, plus the new line `세부 자격·사유가 맞는 경우에만 참고하세요.` |
| **Law / citation / public-data verification** | `법령 인용 검증`, `공공데이터 근거` | unchanged (`검증됨` / `미검증` / `링크만` / `검증 실패` / `미연결`) | Behaviour unchanged; does not overclaim verification. |
| **No strong grounding / advisory fallback** | `일반 안내` | badge `참고` | New: when no grounding signal exists the panel still renders an advisory row so the 1345 / HiKorea / immigration-office disclosure stays visible (previously the panel returned empty). |

Targeted, low-risk additions:

- New CSS classes `gp-row.state-needs-review` and `gp-row.state-advisory`
  (with `검토 필요` / `참고` badges), plus a small `.gp-variant-note` style.
- The variant renderer now filters non-object sources and skips empty items,
  so the panel is resilient to missing/malformed metadata.

Unchanged on purpose: existing visual language and CSS classes, the disclosure
line (`최종 판단은 1345 · HiKorea · 관할 출입국·외국인청에 확인하세요.`), and the law/citation
logic. Raw `requiredDocs` / `manualRefs` / full `visa_data` are still never
surfaced — only the 4 safe metadata fields per variant.

---

## 2. Source-confirmed vs needs-review variant context

These remain two distinct tiers and the UI/metadata never conflate them:

- **Source-confirmed / deterministic grounding** comes from the manual
  grounding fixtures (`grounding_sources`) and HIGH / `STRUCTURED_EVIDENCE_READY`
  structured requirements. It sets `grounding_used=true`.
- **Needs-review scenario variants** are local manual catalog context
  (`procedure_variant_context_sources`). They are weaker, always carry
  `needs_manual_review=true`, and **never set `grounding_used=true`**.

> **Safety note:** Needs-review scenario variants remain local manual context
> and are not treated as source-confirmed determinations.

---

## 3. All-status sweep design (`scripts/smoke_ai_all_status_safeguards.py`)

A new deterministic, **no-provider** safety sweep. By default it imports the
backend helper functions and loads `visa_data.json`, so no live LLM provider is
required. With `--backend-url` it additionally probes `/api/ask` over HTTP,
accepting the no-provider **HTTP 503** metadata pattern.

For every status it:

- Builds generic KO/EN prompts
  (`{code} 체류 관련해서 필요한 절차와 주의사항 알려줘` /
  `What should I watch out for with {code} status in Korea?`).
- Verifies generic questions do **not** force scenario variants and do **not**
  select deterministic grounding.
- Verifies `procedure_variant_context_sources` contain only safe fields.
- Verifies missing/malformed `visa_data` (`None`, `{}`, broken `procedures`)
  neither crashes nor fabricates context.
- For statuses that actually carry routable variants, probes matching task
  wording and confirms variants surface **only** when wording matches, stay
  `needs_manual_review`, and never co-assert grounding.

It prints: total statuses checked, statuses with parent-level procedures,
statuses with variants, statuses with no structured procedures, and
warnings/failures by category. `--json` and `--limit` are supported.

**Current result:** 58 / 58 statuses OK, 0 warnings, 0 failures (locally and
against a live no-provider backend).

---

## 4. Scenario-family matrix coverage (`ScenarioFamilyRegressionMatrixTests`)

Table-driven deterministic regression in
`backend/tests/test_scenario_procedure_variants.py`. Each row asserts task
detection, routing key, grounding suppression, and variant safety (only safe
fields, `needs_manual_review=true`, key-matched). No live-LLM prose.

| Family | Cases |
|--------|-------|
| A short-stay/diplomatic | A-1 generic, B-1 short-stay, C-3 visit, C-4 short-term employment |
| D study/training/job-seeking | D-2 leave-of-absence, D-2 part-time (activitiesOutsideStatus, no fabrication), D-4/D-8/D-9 statusChange, D-10 job-seeking |
| E employment | E-2/E-7/E-7-4/E-9 workplaceChange, E-6 activitiesOutsideStatus, E-8/E-10 advisory-only |
| F family/residence | F-1 statusGrant + generic, F-2 residence extension, F-3 activitiesOutsideStatus + statusGrant, F-4 overseas-Korean, F-5 PR, F-6 divorce |
| G humanitarian | G-1 humanitarian, G-1 work permission |
| H working holiday/visit | H-1 working holiday, H-2 workplace/reporting |
| Cross-cutting negatives | generic work / generic family / generic status — even against variant-bearing records (E-7, F-1, E-9) — must not route |

`test_matrix_covers_all_families` asserts families A–H are all present.

---

## 5. High-risk scenarios with deeper regression (`HighRiskScenarioRegressionTests`)

Deeper assertions for the required high-risk set:

- **F-6** divorce/separation/child-raising → `marriage_divorce_status_change`,
  risk `high`, no grounding, no variant (for all sub-codes).
- **G-1** humanitarian/refugee + work permission → no fabricated pathway,
  no auto work authorization, no variant.
- **D-10** job-seeking → not auto-transition to E-series; no variant, no grounding.
- **E-7 / E-7-4** workplaceChange with incomplete facts → needs-review variants
  only, no grounding, key-matched.
- **F-2** residence extension → extension detected but not a grounded code; no
  grounding, no eligibility variant.
- **F-3** dependent activities vs born-child statusGrant routing kept distinct;
  generic family wording routes to neither.
- **H-2** workplace change → not flattened, not fabricated (H-2 has no variants);
  not confused with F-4.
- Edge: multiple variants under one key (F-1 statusChange, 5 variants) capped to
  ≤ 3 and shape-safe; missing payload never crashes or fabricates.

---

## 6. Golden eval / regression cases added

`backend/data/eval/paradiso_ai_golden_questions.json` grows from 45 → 50
(the suite's hard cap) with 5 all-status-oriented cases:

- `gq_a1_diplomatic_generic_ko_01` — A-series advisory, no fabricated routing.
- `gq_g1_humanitarian_generic_ko_01` — G-series, no invented refugee pathway.
- `gq_h2_workplace_change_ko_01` — H-series, workplace_change without variant flattening.
- `gq_d10_jobseeking_transition_ko_01` — high-risk, no automatic E-series transition.
- `gq_f2_residence_extension_ko_01` — high-risk, F-2 not grounded, no eligibility claim.

The broad **all-status** coverage is provided by the structural sweep
(every status), while these golden rows add A/G/H family breadth and high-risk
depth without making the suite noisy.

---

## 7. Smoke script changes (`scripts/smoke_ai_variant_grounding.py`)

Kept `--deployed-safe` and `--limit`; still no live provider required. Added a
discovery summary that reports:

- total routable variant-bearing targets discovered,
- distinct statuses covered (vs total),
- counts by procedure key,
- the list of statuses **not** covered by routable variant smoke but covered by
  the all-status safeguard sweep.

---

## 8. Validation results

All run from a clean `origin/main` checkout on branch
`feat/all-status-ai-source-ux-and-safeguards`:

- `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json`, golden questions JSON → all valid.
- `populate_scenario_procedure_variants_2026_05.py --check` → OK (24 variants).
- `populate_scenario_procedure_variants_batch2_2026_05.py --check` → OK (15 variants).
- `sync_visa_data.py --check` → OK (deploy mirror matches).
- `check_required_documents_coverage.py` → PASS.
- `validate_structured_requirements.py … structured_requirements_2026_05.json` → PASS.
- `py_compile` + `--help` for both smoke scripts → OK.
- `smoke_ai_all_status_safeguards.py` (local + live no-provider backend) → 58/58 OK.
- `smoke_ai_variant_grounding.py` against local no-provider backend → **22 targets, 22 passed, 0 failed**.
- `pytest backend/tests/test_scenario_procedure_variants.py` → 49 passed.
- `pytest …::GoldenEvalSuiteTests` → 17 passed.
- `pytest backend/tests` → 288 passed.
- `bash scripts/check_repo.sh` → success (golden eval 50/50).

Local backend was started with
`uvicorn paradiso_backend:app --host 127.0.0.1 --port 8000` (no provider keys),
exercising the 503 metadata path.

---

## 9. Known limitations

- The all-status sweep proves **metadata/routing safety**, not legal
  completeness of any answer.
- HTTP probing of `/api/ask` depends on a reachable backend; the default mode is
  fully local/helper-level and is what CI-style runs should use.
- Generic prompts rely on the deterministic `_detect_task_type` regex; new
  wording variants may need detector updates (out of scope here).
- Statuses without structured procedures (17) get advisory-only handling by
  design; no variant context is fabricated for them.

---

## 10. Safety note

> **Needs-review scenario variants remain local manual context and are not
> treated as source-confirmed determinations.**

No variants were marked verified or source-confirmed HIGH, `verified=true` was
not set, `needsManualReview` was not removed, and no disclaimers were removed.
