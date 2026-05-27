# Employment reporting job/industry guide - 2026.5

## Purpose

This note records how Paradiso should support HiKorea employment-information reporting.

The actual HiKorea flow asks users to report three pieces of employment information:

1. 직종,
2. 업종,
3. 연간소득.

Paradiso's helper must therefore show both the occupation classification and the industry classification. Showing only 직종 is incomplete and can mislead users during the HiKorea 신고 flow.

## Uploaded sources reviewed

| Source | Role |
| --- | --- |
| `(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf` | KSCO8 occupation source |
| `[별표2-2] 한국표준산업분류 제11차 개정 해설서(신구연계표 포함).pdf` | KSIC11 industry source |
| `붙임 1. 외국인 취업정보 온라인 신고제 개요_수정.hwpx` | reporting target, timing, method |
| `붙임 2. 온라인 신고 절차(관서 방문예약 시 함께 신고하는 경우).hwpx` | HiKorea visit-reservation flow |
| `붙임 3. 온라인 신고 절차(방문예약 없이 최초 신고 또는 변경 신고하는 경우).hwpx` | HiKorea electronic-petition flow |
| `붙임 4. 취업정보 신고 자주 묻는 질문(FAQ).docx` | FAQ, income bands, late filing caution, main activity rule |

## Employment reporting scope from attached guidance

The attached overview states that the online reporting system is for foreign nationals reporting employment information: occupation, industry, and income.

Target statuses listed in the overview:

- E-1, E-2, E-3, E-4, E-5, E-6, E-7, E-8, E-9, E-10,
- F-2, F-4, F-6,
- H-2,
- D-7, D-8, D-9.

Exclusions and limits:

- F-5 permanent residents are excluded.
- People not engaged in profit-making activity are excluded.
- Self-employed people are included when they engage in profit-making activity.

Reporting timing:

- report at foreigner registration or domestic residence report stage if already engaged in profit-making activity;
- report within 15 days from the start of profit-making activity if activity begins later;
- report within 15 days when the reported occupation, industry, or annual-income band changes.

## HiKorea flow alignment

The uploaded procedure guides show two paths.

### Path A - visit-reservation flow

When the user is making a HiKorea visit reservation, the employment-information screen may appear during the reservation flow for reporting-target statuses.

The flow includes:

1. access HiKorea visit reservation,
2. check existing employment information,
3. search and select 직종,
4. search and select 업종,
5. enter annual income,
6. complete reservation and employment-information report.

### Path B - electronic petition flow

When the user is not making a visit reservation, the employment-information report can be submitted through the electronic civil petition route.

The flow includes:

1. access HiKorea electronic petition,
2. select 취업정보 (변경)신고,
3. search and select 직종,
4. search and select 업종,
5. enter annual income,
6. confirm entered information and print/report receipt if needed.

## UI guidance for Paradiso

Paradiso should not present this helper as a single job-code lookup. It should match the HiKorea task:

- Step 1: confirm whether the user is in a reporting-target status and is engaged in profit-making activity.
- Step 2: choose 직종 using KSCO8.
- Step 3: choose 업종 using KSIC11.
- Step 4: choose annual-income band.
- Step 5: explain whether the user should use visit reservation flow or electronic petition flow.

Recommended user-facing labels:

- `직종(한국표준직업분류)`
- `업종(한국표준산업분류)`
- `연간소득 구간`
- `하이코리아 신고 경로`

## Annual-income bands from FAQ

Use these bands exactly until later official-source review changes them:

- 소득없음
- 연간 1천만 원 미만
- 1천만~2천만 원 미만
- 2천만~3천만 원 미만
- 3천만~4천만 원 미만
- 4천만~5천만 원 미만
- 5천만 원 이상

## Multiple jobs or side work

The FAQ says the report uses one main occupation, industry, and annual-income value. The main activity should be based on the profit-making activity to which the person devotes the most working time.

Paradiso should therefore avoid encouraging multiple repeated reports for every side job. Instead, it should explain the main-activity rule and warn that changes to the main occupation, main industry, or income band may trigger a 15-day change report.

## Data-source boundary

This PR seeds:

- KSCO8 major/middle occupation groups,
- KSIC11 major industry groups,
- employment-reporting context from the attached HiKorea guidance.

This PR does not claim:

- full KSCO8 1,270 detailed-unit coverage,
- full KSIC11 lower-level coverage,
- final E-7 occupation eligibility screening,
- legal decision-making authority.

## Next required work

1. Extract full KSCO8 table.
2. Extract full KSIC11 table.
3. Build a UI that separately asks for 직종, 업종, and 연간소득.
4. Add search/result labels that match the actual HiKorea reporting flow.
5. Add warnings for F-5 exclusion, non-profit-activity exclusion, and 15-day change-report deadline.
