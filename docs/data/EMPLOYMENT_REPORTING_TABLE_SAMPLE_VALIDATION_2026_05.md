# Employment Reporting Table Sample Validation - 2026.5

## Purpose

This report validates representative samples from the candidate KSCO8 and KSIC11 full-table extraction produced for Paradiso's HiKorea employment-information helper.

The validation checks structural integrity and representative rows. It does not switch production runtime to the full tables.

## Source artifact

Validated artifact:

- `employment_reporting_full_tables_candidate_2026_05.zip`

Contained candidate files:

- `data/generated/employment_reporting_ksco8_full_candidate.csv`
- `data/generated/employment_reporting_ksic11_full_candidate.csv`
- `data/generated/employment_reporting_ksco8_full_candidate.json`
- `data/generated/employment_reporting_ksic11_full_candidate.json`
- `data/employment_reporting_full_table_extraction_manifest_2026_05.json`
- `docs/data/EMPLOYMENT_REPORTING_FULL_TABLE_EXTRACTION_2026_05.md`

## Structural validation

| Check | KSCO8 occupation | KSIC11 industry |
| --- | ---: | ---: |
| Total rows | 1,999 | 2,038 |
| Major count | 10 | 21 |
| Middle count | 57 | 77 |
| Minor count | 167 | 234 |
| Unit count | 495 | 501 |
| Detailed-unit count | 1,270 | 1,205 |
| Duplicate code count | 0 | 0 |
| Blank code count | 0 | 0 |
| Blank title count | 0 | 0 |
| No-Hangul title count | 0 | 0 |
| Missing parent count | 0 | 0 |

The candidate tables match the expected source summary counts and preserve parent-code chains for sampled hierarchy checks.

## KSCO8 sample checks

| Code | Title | Level | Parent |
| --- | --- | --- | --- |
| 1 | 관리자 | major |  |
| 11 | 의회‧정부 및 기업 고위직 | middle | 1 |
| 111 | 의회 의원‧고위 공무원 및 공공단체 임원 | minor | 11 |
| 1111 | 의회 의원 | unit | 111 |
| 11111 | 국회의원 | detailed_unit | 1111 |
| 22 | 정보 통신 전문가 및 기술직 | middle | 2 |
| 221 | 컴퓨터 하드웨어 및 통신공학 전문가 | minor | 22 |
| 222 | 컴퓨터 시스템 및 소프트웨어 전문가 | minor | 22 |
| 261 | 대학교수 및 강사 | minor | 26 |
| 531 | 통신 관련 판매 종사자 | minor | 53 |
| A | 군인 | major |  |
| A0 | 군인 | middle | A |
| A01 | 장교 | minor | A0 |
| A011 | 영관급 이상 장교 | unit | A01 |
| A0110 | 영관급 이상 장교 | detailed_unit | A011 |

## KSIC11 sample checks

| Code | Title | Level | Parent |
| --- | --- | --- | --- |
| A | 농업, 임업 및 어업(01 ~ 03) | major |  |
| 01 | 농업 | middle | A |
| 011 | 작물 재배업 | minor | 01 |
| 0111 | 곡물 및 기타 식량작물 재배업 | unit | 011 |
| 01110 | 곡물 및 기타 식량작물 재배업 | detailed_unit | 0111 |
| C | 제조업(10 ~ 34) | major |  |
| 10 | 식료품 제조업 | middle | C |
| 107 | 도시락 및 식사용 조리식품 제조업 | minor | 10 |
| J | 정보통신업(58 ~ 63) | major |  |
| 62 | 컴퓨터 프로그래밍, 시스템 통합 및 관리업 | middle | J |
| 620 | 컴퓨터 프로그래밍, 시스템 통합 및 관리업 | minor | 62 |
| 6201 | 컴퓨터 프로그래밍 서비스업 | unit | 620 |
| 62010 | 컴퓨터 프로그래밍 서비스업 | detailed_unit | 6201 |
| U | 국제 및 외국기관(99) | major |  |
| 99 | 국제 및 외국기관 | middle | U |
| 990 | 국제 및 외국기관 | minor | 99 |
| 9900 | 국제 및 외국기관 | unit | 990 |
| 99009 | 기타 국제 및 외국기관 | detailed_unit | 9900 |

## Validation verdict

Validation status: `SAMPLE_VALIDATION_PASSED_WITH_RUNTIME_GATES_REMAINING`.

The extracted full-table candidates are structurally coherent enough to proceed to the next UI/performance integration stage, but they should not yet replace runtime data without additional frontend testing.

## Remaining gates

Before production runtime use:

1. Test frontend performance with 4,037 combined rows.
2. Confirm search labels clearly distinguish 직종(KSCO8) from 업종(KSIC11).
3. Keep final-code confirmation guidance visible.
4. Do not use classification data as E-7 eligibility screening by itself.
5. Decide whether full generated tables should be committed to `data/generated/` or kept as regenerated artifacts.

## Scope boundary

This PR does not change:

- `visa_data.json`,
- `backend/data/visas.json`,
- `verified`,
- `needsManualReview`,
- `index.html`,
- production runtime search behavior.
