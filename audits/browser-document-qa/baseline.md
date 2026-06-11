# Browser document taxonomy QA baseline

## Repository state

- Branch: `fix/browser-document-taxonomy-qa`
- Base commit: `c0cdf68 fix: restore FastAPI Starlette compatibility (#330)`
- Recent history includes rendered checklist dedupe: `0c4bf55 fix: wire rendered document dedupe into checklist (#331)`
- Working tree at baseline: clean before audit files were created

## Data validity

- `visa_data.json`: JSON parse OK
- `backend/data/visas.json`: JSON parse OK
- `doc_master.json`: JSON parse OK

## Rendered dedupe hotfix presence

The current branch includes the rendered document dedupe helpers in `index.html`:

- `renderDocTags()` calls `dedupeDocumentSectionsForDisplay()` at `index.html:13029`
- `normalizeDocumentRequirementKey()` at `index.html:13791`
- `getDocumentRequirementDisplayKey()` at `index.html:13815`
- `mergeDocumentRequirementForDisplay()` at `index.html:13844`
- `dedupeDocumentSectionsForDisplay()` at `index.html:13874`
- `renderProcedureDocGroups()` renders the user-facing checklist groups at `index.html:14209`
- `renderDocumentTabs()` hides legacy document tabs when procedure-scoped documents own the checklist at `index.html:15393`

## F-6 likely affected before patch

Data inspection and local browser QA both show F-6 is still affected after the dedupe hotfix:

- `visa_data.json[28].procedures.extension.requiredDocs.requiredDocs` contains parent-level F-6 extension documents.
- That parent list includes conditional/scenario labels such as `(부부 사이 출생 자녀가 있을 경우) ...`, `그 밖에 심사에 필요하다고 인정되는 서류(요청 시 제출)`, and `별거·이혼소송·실종·사망·혼인단절 사안은 해당 입증서류 추가 필요`.
- `getProcedure()` merges explicit procedure docs with legacy top-level `extensionReqDocs`, so F-6 extension renders a larger parent `기본 준비서류` group than the explicit procedure source alone.
- Browser before-state for `?q=F-6` confirmed the extension panel has `기본 준비서류` with 23 visible items, including `별거`, `이혼소송`, `실종`, `사망`, and `혼인단절 사안은 해당 입증서류 추가 필요`.

## Initial diagnosis

The dedupe hotfix removed duplicate display families but did not change taxonomy. It cannot correct a source or assembly path that places conditional/scenario documents into `requiredDocs`, because `paradisoBuildDocDisplayGroups()` intentionally maps `commonDocs + requiredDocs` to `기본 준비서류`.
