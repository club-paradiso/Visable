# Document rendering path audit

## Current state

- Branch start: `7b27da8 fix: dedupe document requirements and improve source-faithful UI (#329)`.
- The expected helper names were absent from `index.html` before this hotfix:
  - `dedupeDocumentSectionsForDisplay`
  - `normalizeDocumentRequirementKey`
  - `getDocumentRequirementDisplayKey`
  - `mergeDocumentRequirementForDisplay`

## Data source

- `loadVisaData()` at `index.html:17480-17504` loads `/api/visas` when `API_BASE` is configured and falls back to `./visa_data.json`.
- The rendered search cards are assembled from `VISA_DATA` in `renderResults()` at `index.html:15760-15845`.
- `renderResults()` places the user-facing document UI through `renderProcedures(v, kw)` and `renderDocumentTabs(v)` at `index.html:15823-15830`.

## Document assembly functions

- `getProcedure()` at `index.html:13466-13498` merges three sources for each procedure:
  - source-confirmed structured requirements from `sourceConfirmedStructuredRequirements`
  - structured `procedures[procedureKey].requiredDocs`
  - legacy visa-level fields such as `commonDocs`, `initialReqDocs`, `extensionReqDocs`, and related aliases
- `normalizeDocGroups()` at `index.html:14067-14081` and `mergeDocGroups()` at `index.html:14011-14022` normalize document buckets into `commonDocs`, `requiredDocs`, `additionalDocs`, and `conditionalDocs`.
- `normalizeProcedureVariants()` at `index.html:14118-14133` applies the same normalization to procedure scenario variants.
- `getDocumentTabItems()` at `index.html:15332-15337` feeds the legacy `documents_initial`, `documents_registration`, and `documents_extension` tab strip when the procedure section does not already own documents.

## Rendering functions

- `renderDocTags()` at `index.html:13026-13078` renders `.doc-chk-item` checklist tiles and is also used by the document modal at `index.html:12016-12018`.
- `paradisoBuildDocDisplayGroups()` at `index.html:13965-13981` converts the four internal buckets into the rendered display groups.
- `renderProcedureDocGroups()` at `index.html:14208-14215` renders the user-facing procedure document groups.
- `renderProcedurePanel()` at `index.html:14576-14596` calls `renderProcedureDocGroups(proc.docs, keywords)`.
- `renderProcedureVariant()` at `index.html:14255-14279` calls `renderProcedureDocGroups(effectiveDocs, keywords)` for scenario/variant cards.
- `renderScenarioChecklist()` at `index.html:14368-14415` builds the selected-scenario checkbox checklist from `paradisoBuildDocDisplayGroups()`.
- `renderDocumentTabPanel()` at `index.html:15344-15373` renders the legacy tab-strip rows from `getDocumentTabItems()`.

## Where dedupe was missing

The previous merge added display-oriented helpers under `paradiso*20260609` names and did some cross-bucket merging during normalization. However, the actual rendered path still had no repository-wide helper boundary named for display dedupe, and `renderDocTags()` accepted flat arrays directly from the modal and grouped renderers. That meant a duplicate family could survive whenever equivalent requirements arrived through different rendering surfaces or after group reshaping.

This hotfix adds the missing display-layer boundary immediately before rendering:

- `renderDocTags()` now calls `dedupeDocumentSectionsForDisplay()` before emitting `.doc-chk-item` rows.
- `paradisoBuildDocDisplayGroups()` now calls `dedupeDocumentSectionsForDisplay()` before grouping `commonDocs`, `requiredDocs`, `additionalDocs`, and `conditionalDocs` into user-facing sections.
- `countRenderableDocs()` now counts the same deduped sections so badges match visible checklist rows.
- `paradisoMergeDocumentTabItemsForDisplay()` uses the same display-key and merge helpers for legacy document tabs.

The source-of-truth data remains unchanged; the new helpers copy rows and dedupe only the display payload.
