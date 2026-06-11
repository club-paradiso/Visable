# Document taxonomy policy

This policy applies to user-facing document grouping in `index.html` and to the browser QA script in this audit folder.

## Rules

1. The basic/common section may include only documents that are broadly required for the selected procedure/status.
2. Conditional documents must not appear as basic/common just because they exist somewhere in the record.
3. Scenario-specific documents must stay in the scenario, condition, or procedure section where they belong.
4. Labels containing explicit conditions should usually not be in basic/common:
   - `해당 시`
   - `사안`
   - `경우`
   - `필요 시`
   - `혼인단절`
   - `이혼`
   - `별거`
   - `실종`
   - `사망`
   - `자녀`
   - `초청인`
   - `피부양`
   - `입증`
5. A document may remain in basic/common only if official/manual context clearly says it is universally required for the active procedure/status.
6. Dedupe must not hide taxonomy errors. If a document is in the wrong section, fix grouping/classification rather than only removing duplicates.
7. If data is ambiguous, do not silently move it. Mark it as needs manual verification.

## QA classification

- `HIGH_CONFIDENCE_VIOLATION`: visible rendered basic/common item is clearly conditional or scenario-specific in its current scope.
- `REVIEW_NEEDED`: suspicious wording may be a manual extraction artifact, long source note, or procedure-specific requirement that needs human source review.
- `OK_COMMON`: visible rendered basic/common item is acceptable for the current procedure/status.
- `NO_DOCUMENTS`: no document arrays were found for the scanned scope.

## Display grouping contract

The UI group names are Paradiso reader-friendly labels, not official manual headings:

- `기본 준비서류`: rendered from `commonDocs` and `requiredDocs`
- `상황별 추가서류`: rendered from `additionalDocs` and `conditionalDocs`
- `심사 중 추가 요청 가능`: rendered from discretionary catch-all wording
