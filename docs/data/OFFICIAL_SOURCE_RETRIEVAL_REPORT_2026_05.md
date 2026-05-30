# Official Source Retrieval Report — 2026-05

## Executive summary

This report consolidates two official-source retrieval inputs for PR #222 and
records what each can and cannot support for future Paradiso data corrections.
It is a **source-map / evidence-strengthening** update: it adds an official
source registry and procedure-level source references. It does **not** broadly
rewrite `visa_data.json`, and it does **not** patch any status-specific
required-document list from these sources.

Two inputs:

- **Input A — user-provided KIS/MOJ source map** (`docs/data/official_source_map_2026_05.json`):
  5 official Korea Immigration Service / Ministry of Justice sources (under
  `corrections.go.kr/immigration_eng`) plus 3 attachments, including the Visa
  Navigator announcement/manuals and the E-7-4 Skilled Worker Points System page.
- **Input B — ChatGPT-retrieved HiKorea / Korea Visa Portal source map**:
  official HiKorea procedure pages and the Visa Portal entry-purpose visa
  category structure. These were retrieved via ChatGPT web access; they are
  **blocked in Claude Code cloud execution** (egress allowlist, see below).

The single production data correction on this branch remains the prior
local-manual-grounded **D-4 extension `pageRange` `p. 90` → `pp. 90-91`**. No
new production data correction was made from these source-map inputs.

## Source access limitations

- In this Claude Code cloud environment, `visa.go.kr` and `hikorea.go.kr` are
  **not on the egress allowlist**: the inspecting egress proxy returns
  `HTTP 403` with `x-deny-reason: host_not_allowed` (diagnosed via verbose
  `curl`; TLS cert issuer `CN=sandbox-egress-production TLS Inspection CA`). See
  `docs/data/OFFICIAL_WEB_SOURCE_EVIDENCE_2026_05.md`.
- Input B's HiKorea / Visa Portal content was therefore **retrieved out-of-band
  by ChatGPT web access**, not fetched here. It is recorded as evidence for the
  source registry and procedure-level references, but per task policy it is
  **not** treated as field-level required-document authority and was not used to
  rewrite per-status documents.
- Input A's KIS/MOJ pages and PDFs (`corrections.go.kr`) are likewise not
  fetched/extracted here; the attachments are marked `downloaded: false`.

## Input A — user-provided KIS/MOJ source inventory

| source_id | type | supports_level | readiness | use / do-not-use |
| --- | --- | --- | --- | --- |
| MOJ-KIS-VisaNavigator-Announcement-2023 | notice | status_level | READY_FOR_SOURCE_REGISTRY | Use: confirm official release of Visa Navigator. Do not use: field-level required-document patching. |
| MOJ-KIS-VisaNavigator-PDF-ENG-2023 | PDF | status_level | READY_FOR_SOURCE_REGISTRY | Use: status category/activity/eligibility overview, general application & reporting methods. Do not use: required-document patching. |
| MOJ-KIS-VisaNavigator-PDF-KOR-2022 | PDF | status_level | READY_FOR_SOURCE_REGISTRY | Use: Korean terminology, status category cross-check. Do not use: required-document patching. |
| MOJ-KIS-SkilledWorkerPoints-E7-4-Info | HTML | procedure_level | READY_FOR_PROCEDURE_SOURCE_REFERENCE | Use: E-7-4 eligibility/quota source note. Do not use: required-document patching; broad parent E-7 correction. |
| MOJ-KIS-ForeignRegistrationCardVerification-2025 | notice | procedure_level | DO_NOT_USE_FOR_PATCH | Use: completeness only. Do not use: any visa/stay data patching. |

Key conclusions preserved from Input A:
- Visa Navigator is useful for status categories, eligibility overview, periods
  of stay, activity scope, and general procedure explanations.
- Visa Navigator does **not** provide detailed required-document lists and points
  users to HiKorea for that information → it is **not** a required-document
  authority.
- The E-7-4 page supports E-7-4 eligibility/quota discussion only, not
  required-document patching and not broad parent-E-7 changes.

## Input B — ChatGPT-retrieved HiKorea source inventory

> Retrieved by ChatGPT web access; **blocked in Claude Code cloud**. Usable for
> procedure-level / source-map evidence; **not sufficient alone** for per-status
> required-document rewrites.

| # | page | URL | readiness | procedure scope |
| --- | --- | --- | --- | --- |
| 1 | HiKorea main | https://www.hikorea.go.kr/Main.pt | READY_FOR_SOURCE_REGISTRY | site hierarchy: 비자내비게이터, 체류자격별 안내메뉴얼, 출입국/체류안내, 법령지침정보 |
| 2 | 출입국/체류안내 main | https://www.hikorea.go.kr/info/InfoMain.pt | READY_FOR_PROCEDURE_SOURCE_REFERENCE | lists 체류일반 / 외국인등록 / 체류기간 연장 / 체류자격변경 / 체류자격외활동 / 근무처변경·추가 / 체류자격부여 / 재입국허가 / 각종신고의무 |
| 3 | 체류일반 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=170&PARENT_ID=19 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | stay classes; 90-day registration rule; employment-capable statuses (C-4, E-1~E-7, E-9, E-10, F-2, F-4, F-5, F-6, H-1) |
| 4 | 외국인등록 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=176&PARENT_ID=139 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | registration scope, exemptions, timing (within 90 days; immediately on grant/change) |
| 5 | 체류기간연장 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=181&PARENT_ID=140 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | extension window (4 months before → expiry); Art.25 penalty; F-6 representation limit |
| 6 | 체류자격변경 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=184&PARENT_ID=141 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | change-of-status principle; before-activity rule; A-1/A-2/A-3 30-day rule |
| 7 | 체류자격외활동 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=187&PARENT_ID=142 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | prior permission; short-term (≤90d) cannot; D-2/D-4-1 fee exemption note |
| 8 | 근무처변경/추가 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=189&PARENT_ID=143 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | prior-permission vs report-after targets (E-7 occupation-specific = high-risk, do not generalize) |
| 9 | 체류자격부여 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=191&PARENT_ID=144 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | status-grant timing (birth 90d / loss 60d) and example outcomes (F-3/F-5/F-1) |
| 10 | 재입국허가 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=7203&PARENT_ID=145 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | re-entry exemptions (1yr A-1~F-3,F-6~H-2; 2yr F-5; F-4 within stay); fee 50,000 KRW |
| 11 | 각종신고의무 | https://www.hikorea.go.kr/info/InfoDatail.pt?CAT_SEQ=196&PARENT_ID=146 | READY_FOR_PROCEDURE_SOURCE_REFERENCE | 15-day registration-info change reporting; reasons; documents |

High-risk caution (item 8): E-7 occupation-specific prior-permission handling
must not be generalized without exact occupation/sub-code handling.

## Input B — ChatGPT-retrieved Visa Portal source inventory

| page | URL | readiness | use / do-not-use |
| --- | --- | --- | --- |
| Korea Visa Portal main + entry-purpose visa guide | https://www.visa.go.kr/ | READY_FOR_SOURCE_REGISTRY | Use: visa issuance / entry-purpose source map, visa-category discovery, source registry. Do not use: as authority for in-country extension/registration/change documents unless a specific Visa Portal page explicitly covers those procedure details. |

The Visa Portal entry-purpose guide enumerates a detailed sub-code catalog
(e.g. B-2-1/B-2-2; C-3-1…C-3-9; D-2-1…D-2-6; D-4-1/D-4-3/D-4-7; D-8 series;
E-6-1…E-6-3; E-7-1/E-7-91; F-1/F-2/F-3/F-4/F-5/F-6 sub-codes; H-2 sub-codes;
A-1/A-2 …). This is useful for **category discovery only**, per the source's
own authority scope (entry-purpose visa issuance), not for in-country procedure
document lists.

## Readiness label counts

Input A (KIS/MOJ):
- READY_FOR_SOURCE_REGISTRY: 3
- READY_FOR_PROCEDURE_SOURCE_REFERENCE: 1
- DO_NOT_USE_FOR_PATCH: 1
- READY_FOR_FIELD_PATCH: 0

Input B (HiKorea / Visa Portal, ChatGPT-retrieved):
- READY_FOR_SOURCE_REGISTRY: 3 (HiKorea main, Visa Portal main; + 출입국/체류안내 index as a registry/index page)
- READY_FOR_PROCEDURE_SOURCE_REFERENCE: 9 (체류일반, 외국인등록, 체류기간연장, 체류자격변경, 체류자격외활동, 근무처변경/추가, 체류자격부여, 재입국허가, 각종신고의무)
- READY_FOR_FIELD_PATCH: 0

## Attachment table (Input A)

| attachment_id | parent_source | filename | type | downloaded |
| --- | --- | --- | --- | --- |
| ATT-454085-ENG-VisaNavigator | MOJ-KIS-VisaNavigator-Announcement-2023 | VISA NAVIGATOR(Customized Stay Guide)(Eng).pdf | PDF | false |
| ATT-454086-KOR-VisaNavigator | MOJ-KIS-VisaNavigator-Announcement-2023 | 비자 내비게이터(Visa Navigator) 전자책 (국문).pdf | PDF | false |
| ATT-599268-ForeignRegistrationCardVerification | MOJ-KIS-ForeignRegistrationCardVerification-2025 | Foreign Registration Card Verification Service Expanded to the Non-Banking Sector.pdf | PDF | false |

## What can support future patches

- **Status-level / category fields** (visa category naming, eligibility overview,
  period of stay, activity scope): Visa Navigator (ENG/KOR) + Visa Portal
  category catalog, as a registry/cross-check — only if mapped to a real existing
  field and not implying full verification.
- **Procedure-level source references / citations** (extension window, change
  principle, registration timing, re-entry exemptions, reporting duty): HiKorea
  procedure pages — as source-reference notes, not as new required-document data.
- **E-7-4 eligibility/quota reference**: KIS E-7-4 page — as a procedure source
  note for the E-7-4 sub-code only.

## What cannot support future patches

- **Per-status required-document lists** from any of these sources alone. Visa
  Navigator explicitly defers to HiKorea; the HiKorea pages collected here are
  the *common* procedure overviews, which themselves defer status-specific
  document lists to the status-specific manual/table.
- **Sub-code/scenario-specific required documents** (e.g. E-7 occupation
  prior-permission, F-6 sub-cases) without the exact status-specific manual.
- Anything from `MOJ-KIS-ForeignRegistrationCardVerification-2025`
  (`DO_NOT_USE_FOR_PATCH`).

## Recommended next steps (for field-level corrections)

1. Retrieve/extract the HiKorea **2026-05-21 status-specific manuals**
   (체류자격별 안내메뉴얼) — i.e. the same family as the already-committed
   `stay_manual_grounding_2026_05.json`, extended per status.
2. Map exact manual section → exact JSON path (status → procedure →
   `requiredDocs`/`manualRefs`), preserving conditional and sub-code boundaries.
3. Patch only source-confirmed fields, keeping `needsManualReview: true` and
   without promoting `verified=true`.
4. Where a needed field/boundary has no safe schema, record `SCHEMA_GAP` rather
   than inventing fields.
