# Hard-Case Scenario Procedure Coverage (2026-05)

Real user-facing coverage expansion for hard-case scenario procedures that
earlier batches (PR #234 batch-1, PR #239 batch-2) deferred. All records are
transcribed from the official 2026-05 stay manual already committed in the
repository (`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`), with
printed-page citations verified via `scripts/extract_manual_page_text.py`
(footer `- N -` == printed page N).

Helper: `scripts/populate_hard_case_scenario_procedure_variants_2026_05.py`
(idempotent, `--check`-aware, additive on top of batch-1/batch-2; preserves
existing parent-level procedure records; updates both `visa_data.json` and
`backend/data/visas.json`).

> **Safety note:** Scenario-specific requirements were added only as labeled
> needs-review variants and were not flattened into parent-level procedures.

---

## 1. Summary counts

| Metric | Value |
|--------|-------|
| Variants added | **12** |
| Statuses affected | **3** (F-6, G-1, F-2) |
| Procedure keys affected | **1** (`statusChange` / 체류자격 변경허가) |
| Routable variant-bearing smoke targets (before → after) | **22 → 25** |
| Statuses with routable variants in all-status sweep (before → after) | **13 → 16** |

All variants are `change_of_status` (체류자격 변경허가). The `statusChange`
procedure key is already routable by the AI task detector, so no detector
change was required.

---

## 2. Added variants

Source file for every entry:
`docs/source-manuals/2026-05/stay_manual_2026_05.pdf` (manual `체류민원` v2026.5).
Every `manualRefs` entry carries `confidence: "manual_extracted_needs_review"`
and `needsManualReview: true`. Document groups below list which of
`commonDocs / requiredDocs / additionalDocs / conditionalDocs` were populated.

### 결혼이민(F-6) — statusChange

| variant id | labelKo | scenarioKo (short) | page | groups | key conditions preserved |
|---|---|---|---|---|---|
| `f-6-2-child-rearing-status-change` | 자녀양육자(F-6-2) 체류자격 변경허가 | 국민과의 혼인관계에서 출생한 미성년 자녀를 양육하는 부·모의 F-6-2 변경 | p. 488 | common, required, conditional | 혼인단절자(이혼·사망·실종) 사유 입증서류는 해당자에 한함 (conditional); 1년 체류허가·개별심사 (notes) |
| `f-6-3-marriage-terminated-status-change` | 혼인단절자(F-6-3) 체류자격 변경허가 | 본인 책임 없는 사유(사망·실종·이혼)로 혼인이 단절된 사람의 F-6-3 변경 | pp. 488-489 | common, required, conditional | 사망/이혼/실종별 입증서류 분리 (conditional); 제한 대상·F-6-1 연장 대상 구분 (notes) |

### 기타(G-1) — statusChange (humanitarian / protected-stay sub-codes)

| variant id | labelKo | page | groups | key conditions preserved |
|---|---|---|---|---|
| `g-1-1-industrial-accident-status-change` | 산업재해 청구·치료자(G-1-1) | p. 504 | common, required, conditional | 가족 동반 시 입증서류 (conditional); 1년 범위 (notes) |
| `g-1-2-illness-treatment-status-change` | 질병·사고 치료자(G-1-2) | pp. 504-505 | common, required, conditional | 단기사증 입국자는 G-1-10 대상일 수 있음 (notes) |
| `g-1-3-litigation-status-change` | 각종 소송 진행자(G-1-3) | p. 505 | common, required, conditional | 6개월 범위 (notes) |
| `g-1-4-wage-claim-status-change` | 임금체불 중재자(G-1-4) | pp. 505-506 | common, required | 6개월 범위 (notes) |
| `g-1-5-6-refugee-humanitarian-status-change` | 난민신청자(G-1-5)·인도적체류허가자(G-1-6) | p. 506 | common, required | 난민 인정 여부/결과를 의미하지 않음 (notes) |
| `g-1-9-pregnancy-status-change` | 임신·출산 인도적 배려자(G-1-9) | pp. 506-507 | common, required | 1년 부여 (notes) |
| `g-1-10-medical-patient-status-change` | 외국인환자(G-1-10) | p. 507 | common, required, conditional | 동반가족·간병인 입증, 보증인 시 비용서류 생략 (conditional) |
| `g-1-11-rights-protection-status-change` | 성폭력피해자 등 인도적 고려 대상자(G-1-11) | p. 507 | common, required | 권리구제 절차 진행 중 (notes) |

### 거주(F-2) — statusChange (clearly bounded family sub-codes)

| variant id | labelKo | page | groups | key conditions preserved |
|---|---|---|---|---|
| `f-2-2-national-minor-child-status-change` | 국민의 미성년 외국인자녀(F-2-2) 거주 변경허가 | p. 365 | common, required, conditional | 양육권 입증 불가 시 친권자/후견인 동의서; F-1-1 자녀 무료 변경 (conditional); 병역 관련 제한 (notes) |
| `f-2-permanent-resident-family-status-change` | 영주(F-5) 소지자의 배우자·미성년 자녀 거주 변경허가 | p. 365 | common, required | 배우자/미성년 자녀 제출서류 구분 (required prefixes + notes) |

---

## 3. Skipped hard cases (with exact reasons)

| Status / candidate | Reason skipped |
|---|---|
| **F-6-1 (국민의 배우자) statusChange** | The change-of-status document set (pp. 475-479) is the full marriage-migrant packet with extensive income / housing / Korean-ability / relationship-evidence tables and multiple "서류 간소화 사례별" lists. Representing it as one variant risks flattening many conditional sub-cases. *Parent-flattening risk + scenario split.* |
| **가사정리(F-1-6) statusChange** | Already covered by batch-1 `f-1-6-marriage-cleanup-status-change` (destination status F-1). Not duplicated. |
| **D-10 (구직) all keys** | The 구직(D-10) section is dominated by 체류기간 연장 and general 체류자격외활동 면제 notes; document-item extraction is sparse (only pp. 148, 159) and the D-10→E-series transition documents live under the destination employment statuses (already captured by batch-2 E-series statusChange variants, e.g. `e-1-d2-d10-status-change`). *No D-10-side scenario-scoped routable document list found.* |
| **H-2 (방문취업) all keys** | The H-2 employment content (e.g. p. 400) is 취업활동 범위 / 가족관계 입증 / reporting-duty oriented, not a cleanly bounded change-of-status, workplace-change, or activity-permission **제출서류** block. *Procedure key not safely routable + parent-flattening risk.* |
| **F-4 (재외동포) all keys** | The committed extraction (`part4_document_items.csv`) shows no scenario document items for F-4; the section is activity-scope / reporting oriented with no cleanly bounded routable document list. *No clear official manual section found.* |
| **F-5 (영주) statusChange** | 영주 is a destination PR status; its procedures are 영주자격 심사 (point/eligibility) and card/reporting, which do not form a cleanly routable scenario-variant document list under the supported keys. The F-5-holder's *family → F-2* change is instead captured under F-2 (`f-2-permanent-resident-family-status-change`). *Procedure key not safely routable.* |
| **F-2-7 (점수제) / F-2-8 (투자) subtypes** | Spread across many pages (pp. 364, 374, 377, 385, 406, …) with intricate score / income / investment tables and interdependent conditions. *Subtype split + page boundary unclear + high mixing risk.* (Task explicitly cautions against mixing F-2 subtypes.) |
| **`extension` / `registration` variants** | The current frontend/backend/data model routes scenario variants for `statusChange / workplaceChange / activitiesOutsideStatus / statusGrant`. No extension- or registration-level scenario variant was added because parent-level extension/registration records already exist and a sub-code/scenario-level split was not clearly safer here. *Procedure key not part of the variant-routing model for these statuses.* |

---

## 4. Runtime exposure

- **`/api/visas`** — the 12 variants are exposed under
  `procedures.statusChange.variants[]` for F-6, G-1, F-2 (verified via the
  `HardCaseScenarioVariantTests` API tests).
- **AI variant context (`/api/ask`)** — a change-of-status–worded question
  (e.g. `F-6 체류자격 변경 서류 알려줘`) routes the matching needs-review variants
  into `procedure_variant_context_sources` (safe fields only) without setting
  `grounding_used`. Generic questions do **not** force these variants.
- **Source panel** — rendered under `시나리오별 서류 근거 · 매뉴얼 기반 후보 · 최종 확인 필요`
  (PR #240), clearly distinct from source-confirmed grounding, with the
  `세부 자격·사유가 맞는 경우에만 참고하세요.` note.
- **Smoke discovery** — `scripts/smoke_ai_variant_grounding.py` now discovers
  **25** routable variant-bearing targets (was 22), and the all-status sweep
  reports **16** statuses with routable variants (was 13).

### Routing nuance (F-6)

A purely divorce-worded F-6 question (`이혼`, `혼인단절`, `사별` …) is detected as the
high-risk `marriage_divorce_status_change` task and stays on the conservative
advisory path with **no** variant context and **no** grounding — unchanged from
PR #240. The F-6-2 / F-6-3 variants surface on change-of-status wording
(`체류자격 변경`) or explicit sub-code wording (`F-6-3 체류자격 변경 …`). This keeps
the most sensitive divorce path conservative while still exposing the labeled
candidate document sets through `/api/visas` and the source panel.

---

## 5. Validation results

- `python3 -m json.tool` on `visa_data.json`, `backend/data/visas.json`,
  `doc_master.json` → valid.
- `populate_hard_case_scenario_procedure_variants_2026_05.py --check` → OK
  (12 variants; canonical and deploy mirror match).
- `populate_scenario_procedure_variants_2026_05.py --check` → OK (24).
- `populate_scenario_procedure_variants_batch2_2026_05.py --check` → OK (15).
- `sync_visa_data.py --check` → OK.
- `check_required_documents_coverage.py` → PASS.
- `validate_structured_requirements.py … structured_requirements_2026_05.json` → PASS.
- `py_compile` for both smoke scripts and the new populate helper → OK.
- `smoke_ai_variant_grounding.py` (local no-provider backend) → **25 targets, 25 passed, 0 failed**.
- `smoke_ai_all_status_safeguards.py` (local + live no-provider backend) → **58/58 OK, 0 failures**.
- `pytest backend/tests/test_scenario_procedure_variants.py` → **57 passed** (incl. 8 new hard-case tests).
- `pytest …::GoldenEvalSuiteTests` → passed; golden runner **50/50**.
- `pytest backend/tests` → **296 passed**.
- `bash scripts/check_repo.sh` → success.

Local backend started with
`uvicorn paradiso_backend:app --host 127.0.0.1 --port 8011` (no provider keys),
exercising the no-provider 503 metadata path.

---

## 6. Known limitations / unresolved risks

- All variants are **needs-review** candidates; document applicability depends
  on the individual's specific facts and is decided by the competent office.
- F-6-1, F-2 point/investment subtypes, H-2, D-10, F-4, F-5 were intentionally
  deferred (see §3) to avoid flattening, subtype mixing, or unsafe routing.
- Korean document strings are condensed transcriptions of the manual's
  enumerated `제출서류`; the manual remains authoritative.
- Final confirmation always points to HiKorea / 1345 / the competent
  immigration office (unchanged disclaimers).
