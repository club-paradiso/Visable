# KSCO8 occupation-code source update - 2026.5

## Purpose

This note records the source correction for Paradiso's occupation-code/job-code result data.

The previous job-code pipeline used placeholder/API-oriented wording and did not record a reliable official source. That is not acceptable for user-facing occupation-code results, because wrong occupation codes can mislead visa/work eligibility screening. Humanity has somehow made even job codes a trapdoor. Fine, we fix the trapdoor.

## Official source baseline

Use the 8th Korean Standard Classification of Occupations (KSCO) as the source baseline.

- Korean title: 제8차 한국표준직업분류
- Issuing body: 통계청
- Notice: 통계청 고시 제2024-328호
- Announced: 2024-07-01
- Effective: 2025-01-01
- User-provided source file: `(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf`
- Official classification portal route supplied by user: `kssc.mods.go.kr` KSCO classification content page

## Verified structure from the PDF

The PDF states that the 8th KSCO has:

- 10 major groups,
- 57 middle groups,
- 167 minor groups,
- 495 unit groups,
- 1,270 detailed unit groups.

This PR should use the major/middle-group seed only. Full minor/unit/detailed-unit extraction should be a separate PR because a 1,270-row extraction deserves validation, not vibes wearing a statistics hat.

## Major groups

| Code | Korean title |
| --- | --- |
| 1 | 관리자 |
| 2 | 전문가 및 관련 종사자 |
| 3 | 사무 종사자 |
| 4 | 서비스 종사자 |
| 5 | 판매 종사자 |
| 6 | 농림어업 숙련 종사자 |
| 7 | 기능원 및 관련 기능 종사자 |
| 8 | 장치·기계 조작 및 조립 종사자 |
| 9 | 단순 노무 종사자 |
| A | 군인 |

## Patch boundary

This source update should not claim complete KSCO coverage until the full table is extracted and validated.

Recommended follow-up:

`data: extract full KSCO8 occupation code table`
