# Document taxonomy root cause

## Rendering path

- `getProcedure(v, cfg)` builds each procedure tab's document groups in `index.html:13466-13491`.
- `paradisoBuildDocDisplayGroups(groups)` converts internal groups into user-facing groups in `index.html:13972-13987`.
- `renderProcedureDocGroups(groups, keywords)` renders those groups as cards in `index.html:14215-14221`.
- `renderProcedurePanel(v, proc, keywords, isActive)` places the rendered groups inside each procedure panel in `index.html:14583-14604`.

The display mapping is:

- `commonDocs + requiredDocs` -> `기본 준비서류`
- `additionalDocs + conditionalDocs` -> `상황별 추가서류`
- discretionary catch-all text -> `심사 중 추가 요청 가능`

## F-6 affected data

The browser-observed F-6 issue came from the extension procedure:

- Parent record path: `visa_data.json[28]`
- Extension parent path: `visa_data.json[28].procedures.extension.requiredDocs`
- Current line range after patch: `visa_data.json:14528-14545`

Before the patch, `requiredDocs.requiredDocs` included conditional/status-disruption labels:

- `(부부 사이 출생 자녀가 있을 경우) 자녀 명의 가족관계증명서`
- `그 밖에 심사에 필요하다고 인정되는 서류(요청 시 제출)`
- `별거·이혼소송·실종·사망·혼인단절 사안은 해당 입증서류 추가 필요`

F-6 registration had the same smaller classification problem:

- Registration parent path: `visa_data.json[28].procedures.registration.requiredDocs`
- Current line range after patch: `visa_data.json:14854-14870`
- `(부부 사이 출생 자녀가 있을 경우) ...` belonged in `conditionalDocs`, not parent `requiredDocs`.

F-5 had one clear conditional parent item:

- Parent record path: `visa_data.json[27]`
- Extension parent path: `visa_data.json[27].procedures.extension.requiredDocs`
- Current line range after patch: `visa_data.json:14002-14015`
- `추가서류: 배우자 또는 부모의 외국인등록증 등(사안별 해당 시)` belonged in `conditionalDocs`.

## Exact root cause

The bug was a combination of three issues:

1. **Procedure-tab aggregation bug:** `getProcedure()` always merged explicit procedure-scoped docs with legacy top-level arrays such as `extensionReqDocs`. For F-6 extension this pooled the explicit procedure docs with the old generic 15-item extension list, producing the browser-observed 23-item `기본 준비서류`.
2. **Data-level misclassification:** F-6 and F-5 had clearly conditional items stored under parent `requiredDocs`, so the shared display grouping correctly but misleadingly rendered them as basic/common requirements.
3. **Discretionary classifier gap:** labels like `그 밖에 심사에 필요하다고 인정되는 서류` and `기타 심사에 필요한 자료` did not all route into `심사 중 추가 요청 가능`, leaving review/discretionary text as checklist tiles.

## Why duplicates survived the prior hotfix

The rendered dedupe hotfix removed duplicate document families at display time. It did not change which section a document belonged to. If a conditional item was already in `requiredDocs`, dedupe could hide duplicate labels but still had to render the remaining item in `기본 준비서류`.

## Scope of fix

The fix is frontend/data taxonomy, not a UI redesign:

- `getProcedure()` now treats explicit/source-confirmed procedure docs as the authority and uses legacy top-level arrays only as fallback.
- F-6/F-5 clear conditional parent items moved from `requiredDocs` to `conditionalDocs`.
- The discretionary-text regex now catches both `기타 ... 필요하다고 인정되는 서류`, `그 밖에 ...`, and `기타 심사에 필요한 자료` forms.

## Other records

The automated taxonomy checker still reports `REVIEW_NEEDED` manual-extract findings for some records, especially long parent extension text blobs. These were not silently moved because they need source/manual verification rather than a blind taxonomy rewrite.
