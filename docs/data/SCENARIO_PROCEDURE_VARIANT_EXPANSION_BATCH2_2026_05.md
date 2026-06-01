# Scenario Procedure Variant Expansion — Batch 2 (2026-05)

## Summary

Batch 2 adds **15** official-manual-backed scenario/sub-code procedure variants
on top of the 24 batch-1 variants (PR #234) and the AI source-panel / smoke work
(PR #238). Every variant is transcribed from the committed 2026-05 stay manual
(`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`) with a printed-page
citation verified via `scripts/extract_manual_page_text.py` (footer "- N -" ==
printed page N).

| Metric | Value |
|---|---|
| Variants added (batch 2) | 15 |
| Parent statuses affected | 5 — E-1, E-2, E-3, E-7, F-3 |
| Procedure keys affected | 4 — statusChange, workplaceChange, activitiesOutsideStatus, statusGrant |
| Routable variant-bearing smoke targets — before | 13 |
| Routable variant-bearing smoke targets — after | 22 |
| Total curated scenario variants in repo (batch 1 + batch 2) | 39 |

All batch-2 variants carry `confidence: manual_extracted_needs_review`,
`needsManualReview: true`, and no `verified: true`. They are scenario- or
sub-code-scoped and are **not** flattened into parent-level `requiredDocs`.

### Trust boundary (unchanged)

- Deterministic manual grounding → `grounding_used = true`
- Source-confirmed structured requirements (HIGH) → additive block, no flag flip
- **Scenario procedure variants (this batch)** → local manual context only,
  `needsManualReview = true`, never `grounding_used = true`, never HIGH

---

## Added Variants

All `manualName: 체류민원`, `manualVersion: 2026.5`,
`sourceFile: docs/source-manuals/2026-05/stay_manual_2026_05.pdf`.
Document groups use: C=commonDocs, R=requiredDocs, A=additionalDocs, X=conditionalDocs.

### E-1 (교수) — statusChange

| variant id | labelKo | scenarioKo (summary) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `e-1-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 교수(E-1) 체류자격 변경허가 | D-2/D-10 holder changing into E-1 with an employment contract | p. 172 | C,R,X | 조교수 이상 전임교수는 학위증/경력증명서 생략 |
| `e-1-professional-spouse-status-change` | 전문외국인력 배우자(F-3)의 교수(E-1) 등 전문직 체류자격 변경허가 | F-3 spouse of a professional (E-1~E-7, E-6-2 excl.) changing into a professional status | p. 171 | C,R,X | 원 근무처 동의서(해당 시); same provision spans E-1~E-7 |
| `e-1-science-graduate-status-change` | 이공계 졸업 유학생(석사 이상)의 교수(E-1) 체류자격 변경허가 | Science-track graduate (master+) entering education/R&D | p. 172 | C,R | 총(학)장 고용추천서 required |

### E-2 (회화지도) — workplaceChange / statusChange

| variant id | labelKo | scenarioKo (summary) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `e-2-registered-workplace-change` | 회화지도(E-2) 등록외국인 근무처 변경·추가 신고 | Registered E-2 instructor post-notification workplace change/add | p. 180 | R,X | 원 근무처 동의서 면제조건; 잔여 체류기간 부족 시 연장 |
| `e-2-registered-status-change` | 회화지도(E-2) 요건 등록외국인 체류자격 변경허가 | Registered foreigner (incl. A-1/A-2/A-3) meeting E-2 reqs → E-2 | pp. 181-182 | C,R,X | 공적확인 학력/범죄경력 면제·대체 조건; 채용신체검사서 밀봉 |
| `e-2-education-office-instructor-status-change` | 교육부(시·도교육감) 초청 영어강사 회화지도(E-2) 체류자격 변경허가 | Education-office-invited English instructor → E-2 | p. 181 | C,R,X | 초·중등 영어보조교사 최소서류 제출 특례 |
| `e-2-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 회화지도(E-2) 체류자격 변경허가 | D-2/D-10 holder changing into E-2 | pp. 182-183 | C,R | 학위증 또는 경력증명서; 학원설립증 등 |

### E-3 (연구) — workplaceChange / statusChange

| variant id | labelKo | scenarioKo (summary) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `e-3-registered-workplace-change` | 연구(E-3) 등록외국인 근무처 변경·추가 신고 | Registered E-3 researcher post-notification workplace change/add | p. 189 | R,X | 원 근무처 동의서 면제·대체 조건 |
| `e-3-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 연구(E-3) 체류자격 변경허가 | D-2/D-10 holder changing into E-3 | pp. 192-193 | C,R,X | 졸업예정증명서(해당자); 우수 학술논문 입증(해당자) |
| `e-3-a3-sofa-status-change` | 협정(A-3) 자격자의 연구(E-3) 체류자격 변경허가 | A-3 (SOFA) holder meeting E-3 reqs → E-3 | p. 188 | C,R,X | SPONSOR는 원 근무처 동의서; 졸업예정/논문 입증(해당자) |

### E-7 (특정활동) — workplaceChange

| variant id | labelKo | scenarioKo (summary) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `e-7-registered-workplace-change` | 특정활동(E-7) 등록외국인 근무처 변경·추가 사후신고 | Registered E-7 professional post-notification workplace change/add | pp. 221-222 | R,X | 원 근무처 동의서 면제·대체 조건; 사유서·신원보증서 원칙 생략; 사전관리 직종은 별도 허가 절차 |

### F-3 (동반) — activitiesOutsideStatus / statusChange / statusGrant

| variant id | labelKo | scenarioKo (summary) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `f-3-language-proofreader-activities-outside-status` | 동반(F-3) 외국어교열요원(E-7) 체류자격외활동허가 | F-1/F-3 holder as 외국어교열요원(E-7) at a public body | pp. 421-422 | C,R | 기관장 추천서; 학위증 |
| `f-3-instructor-teacher-activities-outside-status` | 동반(F-3) 외국어회화강사(E-2)·외국인학교교사(E-7) 체류자격외활동허가 | F-1/F-3 holder as E-2 instructor or E-7 foreign-school teacher | p. 422 | C,R,X | E-2/E-7 별도 첨부서류 분기(학위·범죄경력·신체검사·교원자격 등) |
| `f-3-humanitarian-status-change` | 인도적 고려 동반(F-3) 체류자격 변경허가 | Humanitarian change into F-3 (pregnancy/birth/childcare/illness) | p. 424 | C,R,A,X | 변경사유서·증빙; 주자격자 외국인등록증; 해외 공적서류 아포스티유/영사확인 |
| `f-3-born-child-status-grant` | 동반(F-3) 국내출생 자녀 체류자격 부여 | Status grant for a domestically-born child of an F-3 holder | pp. 423-424 | C,R,X | 중국 호구부 등; 해외 공적서류 아포스티유/영사확인 |

---

## Skipped Candidates

| Status / procedure | Reason skipped |
|---|---|
| D-10 (구직) — own statusChange/workplaceChange | D-10's own manual procedures are intern (연수) / part-time (시간제) activity notifications that do not map to the four routable variant keys. D-10 → work-visa changes are already captured under destination statuses (E-1/E-2/E-3 `*-d2-d10-status-change`). |
| E-7 (특정활동) — statusChange | The E-7 status-change attachment list (p. 217) is a generic "공통 첨부서류" that varies by 67+ sub-occupations and sub-codes; transcribing it as one variant would risk parent-level flattening across heterogeneous E-7-x scenarios. Deferred pending per-sub-code review. |
| F-2 (거주) — F-2-16 / investment statusChange | F-2 sub-code procedures (F-2-16 special-contribution, investment immigration) span multiple pages with document lists separated from their section headers (e.g., p. 385 header vs. continuation pages); page-accurate transcription needs a focused pass to avoid mis-citation. |
| F-6 (결혼이민), G-1 (기타), H-2 (방문취업) — statusGrant/registration | Section boundaries and document lists are interleaved with cross-status provisions (e.g., F-4/H-2 born-child grants on pp. 425-428); scoping a single safe parent without flattening needs a dedicated review and was deferred. |
| E-1 (교수) — workplaceChange | The E-1 chapter (pp. 171-173) does not expose a clean professor-specific 근무처변경·추가 sub-flow comparable to E-2/E-3/E-4/E-5/E-7; no safe variant extracted. |
| registration (외국인등록) variants | Parent-level registration remains the safe representation for the covered statuses; no sub-code/scenario-level registration requirement was clearly scoped in the manual for the batch-2 parents. |
| extension (체류기간 연장) variants | The current variant model and frontend routing do not safely surface extension-specific variants distinct from existing parent-level extension checklists; no extension variants were added. |

---

## Runtime Exposure

- **`/api/visas`** — all 15 new variants are returned under
  `procedures.<key>.variants[]` for their parent records (verified by
  `ScenarioProcedureVariantBatch2Tests.test_batch2_variants_exposed_through_api`).
- **AI variant context (`/api/ask`)** — the four affected procedure keys
  (statusChange, workplaceChange, activitiesOutsideStatus, statusGrant) are all
  routable by the current classifier, so the new variants are eligible to appear
  in `procedure_variant_context_used` / `procedure_variant_context_sources`
  (and therefore in the PR #238 frontend `시나리오별 서류 근거` panel row) as
  needs-review context. They never set `grounding_used = true`.
- **Smoke discovery** — `scripts/smoke_ai_variant_grounding.py` now discovers
  **22** routable variant-bearing targets (was 13); the 9 new target
  combinations are E-1/statusChange, E-2/workplaceChange, E-2/statusChange,
  E-3/workplaceChange, E-3/statusChange, E-7/workplaceChange,
  F-3/activitiesOutsideStatus, F-3/statusChange, F-3/statusGrant.

---

## Validation Commands and Results

| Command | Result |
|---|---|
| `python3 -m json.tool visa_data.json` | PASS |
| `python3 -m json.tool backend/data/visas.json` | PASS |
| `python3 -m json.tool doc_master.json` | PASS |
| `python3 scripts/populate_scenario_procedure_variants_2026_05.py --check` | PASS (24 batch-1 variants still present; additive helper unaffected) |
| `python3 scripts/populate_scenario_procedure_variants_batch2_2026_05.py --check` | PASS (15 batch-2 variants present; mirror matches) |
| `python3 scripts/sync_visa_data.py --check` | PASS |
| `python3 scripts/check_required_documents_coverage.py` | PASS |
| `python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_05.json` | PASS |
| `python3 -m py_compile scripts/smoke_ai_variant_grounding.py` | PASS |
| `python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q` | PASS (38 passed) |
| `python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q` | PASS (17 passed) |
| `python3 -m pytest backend/tests -q` | PASS (277 passed) |
| `bash scripts/check_repo.sh` | PASS |
| Local no-provider smoke (`BACKEND_URL=… python3 scripts/smoke_ai_variant_grounding.py`) | PASS — 22 targets discovered, 22 passed, 0 failed |

### Local backend smoke note

The local backend was started with `uvicorn paradiso_backend:app` (no LLM
provider configured). The smoke script validates variant metadata from the
503 no-provider response's `detail` payload. All 22 discovered targets passed:
`procedure_variant_context_used = true`, non-empty
`procedure_variant_context_sources`, expected `procedure_key` present, every
matching source `needs_manual_review = true`, no forbidden raw fields, and
`grounding_used` not flipped by variant context.

---

## Safety Rule

> **Needs-review scenario variants remain local manual context and are not
> treated as source-confirmed determinations.**

Scenario-specific requirements were added only as labeled needs-review variants
and were **not** flattened into parent-level procedures. No variant sets
`verified: true`, removes `needsManualReview`, or is promoted to source-confirmed
HIGH. Parent-level checklists, D-2 registration, re-entry coverage, and the
batch-1 variant set are unchanged.
