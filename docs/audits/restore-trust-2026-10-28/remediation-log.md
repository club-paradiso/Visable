# Remediation log — Restore Trust (2026-10-28)

## 1. Reconnaissance (what the result page is made of)

- **Search box → guidance.** `assets/js/status-guidance.js` is a pure resolver plus renderer. It reads `data/status-guidance-202609.json`, which `scripts/build_status_coverage_manifest.py` builds from the authored rules and the 2026-10-19 manuals.
- **`원문 확인` badge.** It is `stateBadge(SOURCE_ONLY)`. On the procedure chooser it came from `codes[code].procedures[pid].s`.
- **`정리된 안내가 아직 없어요`.** This is `renderSourceOnly`, reached when no authored rule matches the status × procedure (`nextStep`, `!remaining.length`).
- **`공식 원문 N쪽 보기`.** This is `sourceButton()`. The page number is the cell's `p`, and the button opens the page through `VisableCivicSearch.openPage` (civic-search.js).
- **`관련 원문 N건`.** civic-search.js `find()` → `manual-corpus-search.js search()`. A first pass uses the query words. A second pass on `visable:guidance-rendered` uses the interpreted intent: status, procedure, chapter ranges and anchors.
- **Verification notice.** `sources.*.review_state = needs_review` → `ovReview` ("2026년 10월판 원문은 아직 사람이 대조 검토하지 않았어요"). Kept unchanged.

## 2. Issue 2 diagnosis: why F-4 사증발급 is empty

The seven candidate causes from the brief, checked against the code and data:

1. **Content absent?** Yes, for structured guidance. No authored rule targets F-4 × visa_issuance; the guidance rules for F-4 cover extension, registration, status_change and activities_outside_status only. The verbatim page text does exist in the local corpus.
2. **Stored but not retrieved?** No. The resolver found no candidate, and the grid audit confirms there is none.
3. **Hidden by a verification flag?** No. Review flags only add notices; they never hide content.
4. **Extraction failed?** No. The corpus text for p.393 and p.394 is present (the p.394 table is column-interleaved).
5. **Wrong procedure mapping?** Partly. The cited page was wrong: 383 is the handbook cover. Fixed (RT-04).
6. **Query or cache problem?** No.
7. **Over-strict publish condition?** No.

So "no organised guidance" is accurate and is kept. What changed is that the answer now shows the cited page's own text (RT-05) and cites the right page (RT-04). No rules were written, because writing them would mean authoring legal content.

## 3. Changes (in order)

| # | Change | Files |
|---|---|---|
| 1 | Shared anchoring primitive for header overlays, used by the language dialog and both theme pickers. Focus return after a language pick; listbox keys | `assets/js/anchored-overlay.js` (new), `civic-search.js`, `visable-theme.js`, 10 HTML pages (script tag and cache-bust versions) |
| 2 | Chooser badge derived from the resolver's outcome (`chipState`). A SUPPORTED cell that no rule answers is shown as source-only on that path | `status-guidance.js` |
| 3 | Badge legend under the chooser (ko/en) | `status-guidance.js` |
| 4 | Verbatim preview of the cited page on source-only answers. `VisableCivicSearch.pageRow()`. Styling inherits the card colours (contrast ≥ 4.5 in all 4 skins) | `status-guidance.js`, `civic-search.js`, `assets/css/status-guidance.css` |
| 5 | Confirmed 동포-handbook pages for visa procedures: F-4 family → 393, H-2 family → 386. Rebuilt the bundle, the suggest index and the backend deploy copy with the repo scripts | `scripts/build_status_coverage_manifest.py`, `data/status-guidance-202609.json`, `data/status-coverage-202609.json`, `data/search-suggest-index.json`, `backend/data/knowledge_deploy/status-guidance-202609.json` |
| 6 | Evidence search: a shared-chapter page that names only other statuses is excluded; with a procedure resolved, evidence stays in that procedure's manual | `assets/js/manual-corpus-search.js` |
| 7 | Stale fixture: the source-only cases in `check_result_hierarchy.mjs` moved from F-4 연장 (structured since #712) to D-3 연장, matching the e2e twin (#714) | `scripts/check_result_hierarchy.mjs` |
| 8 | New gates wired into `npm run test:status-guidance`: the grid audit (`--check`) and the evidence audit (`--check`) | `package.json`, `scripts/audit_status_procedure_grid.mjs`, `scripts/audit_evidence_volume.mjs` |
| 9 | New tests: `tests/e2e/overlay-anchoring.spec.mjs`, `tests/e2e/restore-trust.spec.mjs`, and the browser matrix harness `scripts/browser_status_matrix.mjs` | — |

Nothing was removed: no disclaimer, caution, review notice, badge state or verification flag.
`visa_data.json`, `backend/data/visas.json`, `doc_master.json` and `backend/data/doc_master.json` are untouched.
