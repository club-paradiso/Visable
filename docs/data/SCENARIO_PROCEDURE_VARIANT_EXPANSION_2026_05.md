# Scenario Procedure Variant Expansion — 2026-05

## Summary

This batch populates the `procedures.<key>.variants[]` model added in PR #233.
It reduces user-visible generic fallbacks for official-manual-backed procedures
that cannot safely be represented as parent-level checklists.

The only authority used was:

`docs/source-manuals/2026-05/stay_manual_2026_05.pdf`

Every cited printed page was checked with
`scripts/extract_manual_page_text.py`, which verifies that the PDF page footer
matches the cited printed page.

| Metric | Count |
|---|---:|
| New scenario/sub-code variants | 24 |
| Parent statuses affected | 8 |
| Procedure types affected | 4 |
| `statusChange` variants | 15 |
| `workplaceChange` variants | 6 |
| `activitiesOutsideStatus` variants | 1 |
| `statusGrant` variants | 2 |

Affected parent statuses:
`D-4`, `D-8`, `D-9`, `E-4`, `E-5`, `E-6`, `E-9`, `F-1`.

## Population Helper

`scripts/populate_scenario_procedure_variants_2026_05.py` is the curated source
map and deterministic writer.

- It adds only missing variant IDs.
- It refuses to overwrite an existing variant when the same ID has different
  content.
- It preserves existing parent-level procedure records and richer data.
- It creates an additive procedure shell only when the parent procedure does
  not exist.
- New procedure shells keep parent `requiredDocs` empty.
- It updates `visa_data.json` and `backend/data/visas.json` identically.
- `--check` replays the transformation and fails on drift.

## Added Variants

All populated groups retain `needsManualReview: true` and
`confidence: "manual_extracted_needs_review"`. No variant sets `verified=true`.

| Parent | Procedure | Variant ID | Label | Scenario | Manual pages | Populated groups | Conditions preserved |
|---|---|---|---|---|---|---|---|
| D-4 | `statusChange` | `d-4-1-7-language-training-status-change` | 어학연수(D-4-1·D-4-7) 체류자격 변경허가 | 장기체류자의 한국어·외국어연수 변경 | pp. 83-84 | required, conditional | 부모 잔고증명 추가서류; 고시국가 소명자료 |
| D-4 | `statusChange` | `d-4-2-graduate-training-status-change` | 졸업생 일반연수(D-4-2) 체류자격 변경허가 | 국내 대학 졸업생의 공식 열거 기관 연수 | p. 84 | required | 대상 기관·연수 장소는 시나리오에 보존 |
| D-4 | `statusChange` | `d-4-3-school-student-status-change` | 고등학교 이하 외국인유학생(D-4-3) 체류자격 변경허가 | 자비부담 학생의 허용 교육기관 입학 | pp. 85-86 | required, conditional | 후견인 면제; 불법체류 다발국가 추가서류 |
| D-8 | `statusChange` | `d-8-1-corporate-investment-status-change` | 법인 투자(D-8-1) 체류자격 변경허가 | 외국인투자 법인의 필수전문인력 | pp. 119-120 | required, conditional | 주재활동; 3억원 미만 투자자; 금융지주 자회사 |
| D-8 | `statusChange` | `d-8-2-venture-investment-status-change` | 벤처 투자(D-8-2) 체류자격 변경허가 | 벤처기업 대표자 등 | p. 120 | required | 지식재산권 또는 우수 기술력 입증 |
| D-8 | `statusChange` | `d-8-3-individual-enterprise-status-change` | 개인기업 투자(D-8-3) 체류자격 변경허가 | 국민 경영 개인기업의 필수전문인력 | pp. 120-121 | required, conditional | 주재활동; 3억원 미만 신청자 |
| D-8 | `statusChange` | `d-8-4-tech-startup-status-change` | 기술창업(D-8-4) 체류자격 변경허가 | 기술창업 법인 창업자 | pp. 121-122 | required, conditional | 법인 미설립 예외; 점수제; 특례 유형 |
| D-9 | `statusChange` | `d-9-equipment-specialist-status-change` | 산업설비·선박건조 필수전문인력(D-9) 체류자격 변경허가 | 부득이한 단기입국 후 기술 제공 | pp. 131-132 | required, conditional | 개인 납세내역 부재 시 회사 증명 |
| D-9 | `statusChange` | `d-9-foreign-sole-proprietor-status-change` | 외국인 개인사업자(D-9) 체류자격 변경허가 | 공식 투자금·사업자 요건 충족 개인사업자 | pp. 132-133 | required, conditional | 공동사업자; OASIS; 변경 전 영업행위 |
| E-4 | `workplaceChange` | `e-4-registered-workplace-change` | 기술지도(E-4) 등록외국인 근무처 변경·추가 신고 | 등록 E-4의 사후 신고 | p. 197 | required, conditional | 원 근무처 동의 면제·대체; 변경 시 추천서 |
| E-4 | `statusChange` | `e-4-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 기술지도(E-4) 체류자격 변경허가 | D-2·D-10에서 E-4 취업 변경 | pp. 197-198 | required, conditional | 소관부처 고용추천서 필요시 |
| E-5 | `workplaceChange` | `e-5-registered-workplace-change` | 전문직업(E-5) 등록외국인 근무처 변경·추가 신고 | 등록 E-5의 사후 신고 | pp. 201-202 | required, conditional | 원 근무처 동의 면제·대체; 변경 시 추천서 |
| E-5 | `statusChange` | `e-5-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 전문직업(E-5) 체류자격 변경허가 | D-2·D-10에서 E-5 취업 변경 | p. 202 | required | 자격증·학위·고용추천서 |
| E-6 | `activitiesOutsideStatus` | `e-6-broadcast-film-model-activities-outside-status` | 방송·영화·모델 활동 체류자격외활동허가 | 합법체류 등록외국인의 E-6-2 외 활동 | pp. 205-206 | required, conditional | 원 근무처 동의; A-1·A-2 추천서; E-6-2 제외 |
| E-6 | `workplaceChange` | `e-6-1-3-workplace-change` | 예술흥행(E-6-1·E-6-3) 근무처 변경·추가 신고 | E-6-1·E-6-3 사후 신고 | pp. 206-207 | required, conditional | 원 근무처 동의 면제·대체 |
| E-6 | `workplaceChange` | `e-6-2-employer-workplace-change` | 관광유흥업소 예술흥행(E-6-2) 고용주 변경·추가허가 | E-6-2 공연기획사 등 고용주 변동 | p. 207 | required | 고용주 변동만 포함; 장소 변경은 제외 |
| E-6 | `statusChange` | `e-6-d2-d10-status-change` | 유학(D-2)·구직(D-10) → 예술흥행(E-6) 체류자격 변경허가 | D-2·D-10에서 E-6-1·E-6-3 취업 변경 | pp. 208-209 | required | E-6-1·E-6-3 제한적 변경 |
| E-9 | `workplaceChange` | `e-9-standard-workplace-change` | 비전문취업(E-9) 일반 사업장 변경허가 | 고용센터 절차 후 일반 사업장 변경 | pp. 327-328 | required, conditional | 건설현장 추가서류 |
| F-1 | `statusGrant` | `f-1-employment-parent-born-child-status-grant` | 취업계열 체류자격자 등의 국내출생 자녀 체류자격 부여 | D-3·E-9·E-10·H-2·F-4 부모의 국내출생 자녀 | p. 343 | required, conditional | 중국 국적 호구부 |
| F-1 | `statusGrant` | `f-1-refugee-born-child-status-grant` | 난민인정자의 국내출생 미성년 자녀 체류자격 부여 | 난민인정자 부모의 국내출생 미성년 자녀 | p. 343 | required | 부모 체류기간 범위 |
| F-1 | `statusChange` | `f-1-6-marriage-cleanup-status-change` | 혼인단절 결혼이민자 가사정리(F-1-6) 체류자격 변경허가 | 재산분할·가사정리 목적 | pp. 345-346 | required, conditional | 기타 심사 필요 서류 |
| F-1 | `statusChange` | `f-1-nationality-procedure-status-change` | 국적취득절차 진행자 방문동거(F-1) 체류자격 변경허가 | 국적회복·귀화·국적판정 절차 진행 | p. 346 | required | 국적취득절차 진행 시나리오 |
| F-1 | `statusChange` | `f-1-16-refugee-family-status-change` | 난민인정자 가족(F-1-16) 체류자격 변경허가 | 난민인정자의 배우자·미성년 자녀 | p. 348 | required | 배우자가 있는 미성년 자녀 제외 |
| F-1 | `statusChange` | `f-1-52-prior-marriage-child-status-change` | 결혼이민자 전혼관계 출생 미성년 자녀(F-1-52) 체류자격 변경허가 | 혼인 유지 중 결혼이민자의 친생 미성년 자녀 | p. 350 | required, conditional | 재학증명; 결핵진단; 해외서류 확인 |

## Skipped Candidates

The following candidates remain deliberately unpopulated in this batch.

| Candidate | Procedure | Reason skipped |
|---|---|---|
| D-4-6 우수사설교육기관 외국인 연수 | `statusChange` | Long institution-specific document matrix extends across pp. 87-90; deferred to keep this batch reviewable. |
| D-9 독일인 B-1 장기체류 변경 | `statusChange` | Manual states eligibility but does not provide an isolated D-9-specific document list. |
| D-9 칠레 C-3-4 FTA 변경 | `statusChange` | Manual says only “자격요건을 확인할 수 있는 서류”; no safely enumerable checklist. |
| E-4 소지자격 무관 기술자 변경 | `statusChange` | Eligibility scenario is explicit, but the adjacent checklist is shared with another branch; deferred pending narrower mapping review. |
| E-6-2 공연장소 변경 | `workplaceChange` | This is a 고용주 신고사항, not a 근무처 변경·추가허가 checklist. |
| E-9 G-1 자격 회복 | `statusChange` | Eligibility is explicit on p. 329 but the status-change block does not provide its own required-document list. |
| F-1 F-2-7 국내출생 미성년자녀 | `statusGrant` | Multi-part income and parent-status conditions span pp. 343-344; deferred for a narrower review. |
| F-1 F-1-51 국제입양 아동 | `statusChange` | Safe but large conditional matrix on pp. 349-350; deferred to keep the first expansion batch reviewable. |
| D-10, E-7, F-2, F-3, F-6, G-1, H-2 | multiple | Additional sub-code and scenario splits remain for follow-up extraction. |

## Runtime Exposure

- `/api/visas` preserves all new `variants[]` records.
- Existing parent-level procedures render unchanged because parent
  `requiredDocs` remains the first rendering path.
- Existing PR #232 re-entry records are unchanged.
- Existing D-2 registration remains on the legacy parent-level rendering path.
- When a newly added parent procedure has empty parent `requiredDocs`, the UI
  renders labeled variant cards before the generic fallback.
- Variant cards continue to show the applicability warning added in PR #233.

## Remaining Fallback Categories

Fallbacks remain where the manual does not provide an isolated checklist, where
the scenario split still needs a narrower mapping, or where the first reviewable
batch intentionally stopped. Priority follow-up remains:

1. Remaining `statusChange` branches for D-10, E-7, F-2, F-3, F-6, G-1, H-2.
2. Additional scoped `workplaceChange` and `activitiesOutsideStatus` branches.
3. Deferred high-condition records such as D-4-6 and F-1-51.
4. C-3/C-4 visa-manual issuance or change-related cases where an isolated
   checklist can be confirmed without parent flattening.

## Validation

The final PR validation run includes:

```text
python3 -m json.tool visa_data.json
python3 -m json.tool backend/data/visas.json
python3 -m json.tool doc_master.json
python3 scripts/populate_scenario_procedure_variants_2026_05.py --check
python3 scripts/sync_visa_data.py --check
python3 scripts/check_required_documents_coverage.py
python3 scripts/validate_structured_requirements.py backend/data/manual_grounding/structured_requirements_2026_05.json
python3 -m pytest backend/tests -q
bash scripts/check_repo.sh
```

Results:

- JSON parsing: passed for canonical data, deploy mirror, and `doc_master.json`.
- Population replay: passed; 24 curated variants present and mirrors match.
- Sync check: passed; canonical and deploy JSON are byte-identical.
- Required-document coverage validator: passed.
- Structured-requirements validator: passed unchanged with 352 entries.
- Scenario-variant focused tests: 14 passed.
- Full backend tests: 253 passed.
- Frontend accessibility smoke: passed against the deployed static page.
- Repository validation: passed, including 205 bundled backend regression tests
  and 45/45 Paradiso AI golden-eval questions.

## Safety Note

Scenario-specific requirements were added only as labeled variants and were not
flattened into parent-level procedures.
