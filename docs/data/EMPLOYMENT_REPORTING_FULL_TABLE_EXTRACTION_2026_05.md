# Employment Reporting Full Table Extraction - 2026.5

## Purpose

This report records the first full-table extraction pass for Paradiso's HiKorea employment-information helper.

HiKorea employment-information reporting requires users to select both:

- 직종 from the Korean Standard Classification of Occupations (KSCO8), and
- 업종 from the Korean Standard Industrial Classification (KSIC11).

The attached employment-reporting guides also show that users must enter an annual-income band and choose either the visit-reservation flow or the electronic-petition flow.

## Extracted source files

| Source | Role | Extraction result |
| --- | --- | --- |
| `(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf` | KSCO8 occupation table | 1,999 candidate rows extracted |
| `[별표2-2] 한국표준산업분류 제11차 개정 해설서(신구연계표 포함).pdf` | KSIC11 industry table | 2,038 candidate rows extracted |
| `붙임 1. 외국인 취업정보 온라인 신고제 개요_수정.hwpx` | reporting scope and timing | used for workflow context |
| `붙임 2. 온라인 신고 절차(관서 방문예약 시 함께 신고하는 경우).hwpx` | visit-reservation reporting flow | used for workflow context |
| `붙임 3. 온라인 신고 절차(방문예약 없이 최초 신고 또는 변경 신고하는 경우).hwpx` | electronic-petition reporting flow | used for workflow context |
| `붙임 4. 취업정보 신고 자주 묻는 질문(FAQ).docx` | FAQ and income bands | used for workflow context |

## Candidate extraction counts

| Classification | Major | Middle | Minor | Unit | Detailed unit | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| KSCO8 occupation | 10 | 57 | 167 | 495 | 1,270 | 1,999 |
| KSIC11 industry | 21 | 77 | 234 | 501 | 1,205 | 2,038 |

The extracted counts match the source summary counts found in the PDFs.

## Data status

Classification: `CANDIDATE_EXTRACTED_FROM_USER_PROVIDED_PDFS`.

This is a full-table extraction candidate, not a production runtime switch.

Do not replace runtime search with the full tables until:

1. table-level spot checks pass,
2. parent-code relationships are reviewed,
3. UI performance is checked with 4,000+ combined rows,
4. search labels clearly distinguish 직종 from 업종,
5. the frontend still tells users to confirm final codes on HiKorea or the Statistics Classification Portal.

## Employment-reporting context from attachments

The uploaded overview and FAQ confirm the following operational context:

- employment information means occupation, industry, and income;
- reporting target statuses include E-1 through E-10, F-2, F-4, F-6, H-2, D-7, D-8, and D-9;
- F-5 and people not engaged in profit-making activity are excluded;
- self-employed people are included when they are engaged in profit-making activity;
- changes in occupation, industry, or annual-income band should be reported within 15 days;
- the two online flows are visit reservation with employment reporting and electronic petition for first/change reporting.

## Files prepared by the extraction run

Local generated artifacts:

- `employment_reporting_ksco8_full_candidate.csv`
- `employment_reporting_ksic11_full_candidate.csv`
- `employment_reporting_full_table_extraction_manifest_2026_05.json`

Repository PR artifacts:

- `scripts/extract_employment_reporting_full_tables.py`
- `data/employment_reporting_full_table_extraction_manifest_2026_05.json`
- `docs/data/EMPLOYMENT_REPORTING_FULL_TABLE_EXTRACTION_2026_05.md`

## Runtime boundary

This PR does not change:

- `visa_data.json`,
- `backend/data/visas.json`,
- `verified`,
- `needsManualReview`,
- `index.html`,
- production runtime code selection.

## Recommended next PR

`data: validate KSCO8 and KSIC11 extracted table samples`

That follow-up should spot-check representative rows from each level and category before wiring the full tables into frontend search.
