# Employment Reporting Full Table and UI Follow-up - 2026.5

## Purpose

This note records the merged implementation direction for three previously separate tasks:

1. expand C-3/D-10/E-special-track procedure citations,
2. prepare full KSCO8 and KSIC11 employment reporting table extraction,
3. align the employment reporting helper UI with the actual HiKorea flow.

## Current PR boundary

This PR does not claim fully validated lower-level KSCO8 or KSIC11 tables. It prepares the extraction and UI alignment direction while keeping the existing seed data safe.

The current seed remains:

- KSCO8 occupation major/middle rows,
- KSIC11 industry major rows,
- employment reporting context from the uploaded HiKorea guidance.

## Full table extraction target

The next generated data should include:

| Classification | Current seed | Full target |
| --- | --- | --- |
| KSCO8 occupation | major/middle | major, middle, minor, unit, detailed-unit |
| KSIC11 industry | major | major, middle, minor, unit, detailed-unit |

The extraction must preserve:

- code,
- Korean label,
- classification version,
- level,
- parent code,
- source document,
- validation status.

## HiKorea UI alignment target

The employment helper should not behave as a generic job-code lookup. It should guide users through the actual employment-information report:

1. Check reporting target status.
2. Check whether the user is engaged in profit-making activity.
3. Select 직종 from KSCO8.
4. Select 업종 from KSIC11.
5. Select annual-income band.
6. Choose or explain reporting route:
   - visit-reservation flow,
   - electronic-petition flow.

## Required UI copy

Recommended labels:

- `직종(한국표준직업분류)`
- `업종(한국표준산업분류)`
- `연간소득 구간`
- `하이코리아 신고 경로`

Recommended warnings:

- `F-5 영주자격자는 취업정보 신고 대상에서 제외됩니다.`
- `영리활동을 하지 않는 경우에는 신고 대상이 아닙니다.`
- `영리활동 개시 또는 신고사항 변경 후 15일 이내 신고가 필요할 수 있습니다.`
- `현재 Paradiso 데이터는 seed 단계이므로 상세 코드 확정 전에는 HiKorea 또는 통계분류포털 확인이 필요합니다.`

## Data patch boundary

Do not use this PR to patch visa/status records. Employment reporting helper data is separate from stay-status document checklists.

## Recommended next implementation PR

`feat: render employment reporting helper steps in index`

That PR should be small and should only wire the already committed helper flow data into the UI.
