# Remaining Complex Subtype Scenario Coverage (2026-05)

## Summary

This batch adds remaining high-value complex-subtype cards after the guided
scenario selector and selected-variant AI handoff landed. The records are
additive: existing parent procedures and the prior batch-1, batch-2, and
hard-case variants remain in place.

| Metric | Before | After |
| --- | ---: | ---: |
| Scenario procedure variants | 54 | 74 |
| Variants added in this batch | 0 | 20 |
| Statuses affected in this batch | 0 | 5 |
| Procedure keys affected in this batch | 0 | 4 |
| Routable smoke targets | 25 | 28 |

Affected statuses: `F-6`, `F-2`, `H-2`, `D-10`, `F-4`.

Affected procedure keys: `statusChange`, `workplaceChange`, `extension`,
`registration`.

The official source for every card is:
`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`.

The `H-2` and `F-4` sections are embedded in that PDF with a restarted printed
page footer. Their citations record both the PDF page and embedded-manual page
so the evidence boundary stays explicit.

## Added Variants

Every card populates grouped `requiredDocs`, records `manualRefs`, keeps
`confidence: "manual_extracted_needs_review"`, and retains
`needsManualReview: true`. `additionalDocs` remains present but empty where the
manual did not require a separate additional-documents group.

| Parent | Procedure | Variant ID | `labelKo` | `scenarioKo` | Source file | Page range | Populated document groups | Key conditions preserved | Selected AI handoff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F-6` | `extension` | `f-6-1-marriage-maintenance-extension` | F-6-1 혼인관계 유지 중 체류기간 연장 | 혼인관계를 유지하는 국민의 배우자 | `stay_manual_2026_05.pdf` | pp. 490-491 | common, required, conditional | 자녀 양육 여부에 따른 체류기간 차이 | Yes |
| `F-6` | `extension` | `f-6-1-separated-extension` | F-6-1 별거 중 체류기간 연장 | 한국인 배우자와 별거 중인 국민의 배우자 | `stay_manual_2026_05.pdf` | p. 491 | common, required, conditional | 별거 사유별 입증자료, 수감 시 추가자료 | Yes |
| `F-6` | `extension` | `f-6-1-divorce-lawsuit-extension` | F-6-1 이혼소송 중 체류기간 연장 | 한국인 배우자와 이혼소송 중인 국민의 배우자 | `stay_manual_2026_05.pdf` | p. 491 | common, required, conditional | 이혼소송 계속 사실 입증 | Yes |
| `F-6` | `extension` | `f-6-1-spouse-missing-extension` | F-6-1 배우자 실종 중 체류기간 연장 | 배우자 실종선고 전 단계의 국민의 배우자 | `stay_manual_2026_05.pdf` | p. 491 | common, required, conditional | 실종선고 청구·실종신고 등 해당 자료 | Yes |
| `F-2` | `statusChange` | `f-2-7-point-based-talent-status-change` | F-2-7 점수제 우수인재 체류자격 변경 | 점수제 우수인재 요건 충족 신청인 | `stay_manual_2026_05.pdf` | pp. 368-374 | common, required, conditional | 대상 유형별 기본요건과 점수요건 | Yes |
| `F-2` | `statusChange` | `f-2-7s-potential-talent-status-change` | F-2-7S 잠재적 우수인재 체류자격 변경 | 이공계 특성화 대학·연구기관 석박사 추천 대상 | `stay_manual_2026_05.pdf` | pp. 369-374 | common, required, conditional | 점수 면제 범위, 추천 대상과 시점 | Yes |
| `F-2` | `statusChange` | `f-2-8-tourism-investment-status-change` | F-2-8 관광·휴양시설 투자 거주자격 변경 | 지정 관광·휴양시설 등 투자자 | `stay_manual_2026_05.pdf` | pp. 375-378 | common, required, conditional | 투자 대상·방식·금액·자기자금 요건 | Yes |
| `F-2` | `statusChange` | `f-2-12-13-14-public-interest-investment-status-change` | F-2-12·13·14 공익사업 투자 거주자격 변경 | 공익사업 투자이민 일반형·고액형·퇴직이민형 | `stay_manual_2026_05.pdf` | pp. 379-385 | common, required, conditional | 유형별 투자금액과 대상 범위 | Yes |
| `H-2` | `registration` | `h-2-existing-holder-registration` | H-2 기존 체류자 외국인등록 | 2026-02-12 이전 H-2 부여 기존 체류자 | `stay_manual_2026_05.pdf` | PDF pp. 524-525 (embedded pp. 4-5) | common, required, conditional | 신규 발급 중단, 90일 내 등록 | Yes |
| `H-2` | `workplaceChange` | `h-2-employment-start-workplace-change-report` | H-2 취업개시·근무처변경 신고 | 허용 업종 취업개시 또는 근무처변경 후 신고 | `stay_manual_2026_05.pdf` | PDF pp. 525-526 (embedded pp. 5-6) | common, required, conditional | 15일 내 신고, 허용 업종 범위 별도 확인 | Yes |
| `D-10` | `statusChange` | `d-10-1-points-status-change` | D-10-1 점수제 구직 체류자격 변경 | 점수제 일반 구직활동 대상자 | `stay_manual_2026_05.pdf` | pp. 143-149 | common, required, conditional | 기본항목·총점·일부 출신국 별도 점수요건 | Yes |
| `D-10` | `statusChange` | `d-10-1-first-graduate-status-change` | D-10-1 국내 졸업 후 최초 구직 체류자격 변경 | 국내 정규 대학 졸업 후 최초 변경 신청자 | `stay_manual_2026_05.pdf` | p. 149 | common, required | 제한된 점수제 면제, 체류비 입증 면제 | Yes |
| `D-10` | `statusChange` | `d-10-2-tech-startup-status-change` | D-10-2 기술창업준비 체류자격 변경 | 기술창업 준비활동 신청자 | `stay_manual_2026_05.pdf` | p. 151 | common, required, conditional | 지식재산권·OASIS·OECD 자료 해당 시 제출 | Yes |
| `D-10` | `statusChange` | `d-10-3-high-tech-intern-status-change` | D-10-3 첨단기술 인턴 체류자격 변경 | 해외 우수대학 첨단기술 분야 학생·졸업자 | `stay_manual_2026_05.pdf` | pp. 151-152 | common, required, conditional | 대학순위·분야·인턴기간·초청기업 요건 | Yes |
| `D-10` | `extension` | `d-10-1-points-extension` | D-10-1 점수제 구직 체류기간 연장 | 점수제 일반 구직활동 계속 신청자 | `stay_manual_2026_05.pdf` | pp. 155-156 | common, required, conditional | 점수 요건과 연장 체류기간 | Yes |
| `D-10` | `extension` | `d-10-2-tech-startup-extension` | D-10-2 기술창업준비 체류기간 연장 | 기술창업 준비활동 계속 신청자 | `stay_manual_2026_05.pdf` | p. 157 | common, required, conditional | K-Startup 참여자의 체류비 자료 면제 여부 | Yes |
| `D-10` | `extension` | `d-10-3-high-tech-intern-extension` | D-10-3 첨단기술 인턴 체류기간 연장 | 첨단기술 인턴활동 계속 신청자 | `stay_manual_2026_05.pdf` | p. 157 | common, required, conditional | 인턴 계속성과 초청기업 요건 유지 | Yes |
| `F-4` | `statusChange` | `f-4-overseas-korean-status-change` | F-4 재외동포 국내 체류자격 변경 | 국내 발급·전산 확인 가능한 자료를 갖춘 재외동포 | `stay_manual_2026_05.pdf` | PDF pp. 528-530 (embedded pp. 8-10) | common, required, conditional | 국내 변경 자료 범위, H-2와 구분 | Yes |
| `F-4` | `registration` | `f-4-domestic-residence-report` | F-4 국내거소신고 | 90일 초과 체류 예정 F-4 재외동포 | `stay_manual_2026_05.pdf` | PDF p. 530 (embedded p. 10) | common, required, conditional | 국내거소신고 대상과 이수 면제 여부 | Yes |
| `F-4` | `extension` | `f-4-overseas-korean-extension` | F-4 재외동포 체류기간 연장 | F-4 재외동포의 체류기간 연장 | `stay_manual_2026_05.pdf` | PDF pp. 530-531 (embedded pp. 10-11) | common, required, conditional | 한국어능력과 법 위반 여부에 따른 부여 범위 | Yes |

## Skipped Complex Candidates

The following candidates were inspected but not forced into this batch:

| Candidate | Added in this batch | Exact reason for skipped scope |
| --- | --- | --- |
| `F-6-1` 국민의 배우자 | Four `extension` cards | The broader marriage-migrant issuance/change packet contains income, housing, relationship-proof, and simplified-case branches. Flattening those into a parent checklist or one guided card would hide material scenario splits. |
| `F-2-7` 점수제 우수인재 | Two `statusChange` cards | Change cards were added. Extension and eligibility-determination cards were skipped because score reassessment and subtype conditions should not be presented as an automatic residence determination. |
| `F-2-8` 투자 거주 | One `F-2-8` and one separate public-interest investment `statusChange` card | The investment families were kept separate. No vague parent-level investment card was added because investment type, amount, business structure, and proof conditions differ. |
| `H-2` 방문취업 | Existing-holder `registration` and employment report cards | Broad employment-scope guidance and extension prerequisites were not flattened into document cards. The reporting card is limited to the clear employment-start/workplace-change report block and does not imply employment permission. |
| `D-10` 구직 | Seven change/extension cards | The training-start and training-institution-change report block was skipped because the existing model has no clearly matching procedure key. E-series destination paths were not duplicated under `D-10`. |
| `F-4` 재외동포 | Three change/report/extension cards | The narrow former-`H-2` employment-continuity activity block was deferred for a dedicated employment-scope review so the guided selector does not imply a general F-4 work determination. |
| `F-5` 영주 | None | The inspected section combines subtype qualification, financial conditions, card duties, and reporting duties. A parent-level card would create status-versus-card/reporting ambiguity and parent-flattening risk. |
| `C-3` / `C-4` | None | Short-stay and short-employment blocks remain tier-2 follow-up work. `C-4` workplace material spans permission and reporting situations; it needs a separate boundary review before selector exposure. No long-term transition path was invented. |
| `D-2` / `D-4` | None | `D-4` change scenarios already have prior-batch coverage. `D-2` time-part work, attendance, graduation/completion, and leave branches need a focused mapping review so activity conditions are not forced into the wrong procedure key. |
| Existing `F-2` family variants | None | Existing hard-case family coverage remains unchanged. This batch adds only distinct talent and investment change cards. |

## Runtime Exposure

- `/api/visas` exposes all 20 variants from both mirrored data files.
- The guided scenario selector renders the cards automatically from
  `procedures.<key>.variants[]`; no UI change is required.
- All 20 cards are eligible for explicit selected-variant AI handoff through
  `selected_procedure_key` and `selected_procedure_variant_id`.
- Default classifier routing discovers three additional targets:
  `D-10/statusChange`, `H-2/workplaceChange`, and `F-4/statusChange`.
- `extension` and `registration` cards remain selector-driven. Generic
  questions do not force them into AI context.
- The source panel continues to show these records as needs-review scenario
  context, separate from source-confirmed grounding.
- `scripts/smoke_ai_variant_grounding.py` discovers 28 routable targets after
  this batch, up from 25.

## Validation

Completed during implementation:

- `python3 scripts/populate_scenario_procedure_variants_2026_05.py --check`
- `python3 scripts/populate_scenario_procedure_variants_batch2_2026_05.py --check`
- `python3 scripts/populate_hard_case_scenario_procedure_variants_2026_05.py --check`
- `python3 scripts/populate_remaining_complex_subtype_scenario_variants_2026_05.py --check`
- `python3 -m py_compile scripts/populate_remaining_complex_subtype_scenario_variants_2026_05.py scripts/smoke_ai_variant_grounding.py scripts/smoke_ai_all_status_safeguards.py`
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests/test_scenario_procedure_variants.py -q`
  (`71 passed`, `66 subtests passed`)
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests/test_paradiso_backend.py::GoldenEvalSuiteTests -q`
  (`17 passed`)
- `PYTHONPATH=/private/tmp/paradiso-pytest python3 -m pytest backend/tests -q`
  (`310 passed`, `66 subtests passed`)
- `bash scripts/check_repo.sh`
  (`205` backend regression tests and `50/50` non-strict golden questions passed)
- `BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_variant_grounding.py`
  (`28 passed`, `0` skipped, `0` failed)
- `BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_variant_grounding.py --selected-variant-smoke`
  (`28 passed`, `0` skipped, `0` failed)
- `BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_all_status_safeguards.py`
  (`58 OK`, `0` warnings, `0` failures)
- `git diff --check`

The HTTP smoke commands ran against a local Uvicorn backend with provider keys
removed. The smoke scripts accepted the expected no-provider `503` responses
only when the safe scenario metadata path remained intact.

## Safety Note

Scenario-specific requirements were added only as labeled needs-review variants and were not flattened into parent-level procedures.
