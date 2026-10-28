# Operation Restore Trust — final report (2026-10-28)

This is rendering, routing and source-linking work. It is not a legal revalidation.
No eligibility rule, document, fee, period or procedure state was added or changed.

## A. Executive summary

**Main problems found**

1. **Badges didn't match the outcome.** On the procedure chooser, `원문 확인` reflected a stored cell state, not what the pick renders.
   - Grid-wide, 172 cells flagged as source-only actually render a structured rule. Examples are 체류지 변경 신고, 등록사항 변경신고 and 외국인등록증 재발급.
   - 16 cells showed `안내 가능` beside "정리된 안내가 아직 없어요".
   - Nothing on the page explained what the mark means.
2. **F-4 사증발급 cited the wrong page.** It pointed at the 동포 handbook cover (p.383); the F-4 visa section starts on p.393. The answer itself was empty.
3. **`관련 원문 129건` was inflated** by pages about other statuses in a shared chapter (47 of 129 never mention F-4). Procedure evidence also mixed visa and stay manuals: for F-4 사증발급, 16 of 38 pages came from the stay manual.
4. **The KO language panel opened at the left screen edge** (P1 UI reliability). RTL was also misplaced, and focus was lost after picking a language.

**Root causes**

- The chooser badge read stored data instead of the resolver's outcome.
- The coverage build fell back to the chapter's start page, which for the shared handbook is its cover.
- The evidence filter admitted any page in the chapter range, and treated the procedure's manual only as a score penalty.
- The modal `<dialog>` was over-constrained (UA inset + fixed width + `right`).

**Fixes:** see §C.

**Largest remaining risk:** 1,449 of 2,456 cells still have no organised guidance. That gap can only be closed by authored, human-reviewed rules (U-1).

## B. Audit inventory

| Measure | Count | Population |
|---|---|---|
| Status × procedure cells walked through the real resolver | 2,456 | 2,456 (263 codes × their procedures) |
| Status/substatus codes searched in a real browser (batches of 10, 390px) | 258 | 258 (status + substatus kinds) |
| Source-only answers opened in the browser | 254 | 254 of 258 choosers had one |
| Findings logged | 15 | `findings.csv` |
| Fixed and VERIFIED | 12 | RT-01…RT-12 |
| Open (manual review / out of scope) | 3 | RT-13, RT-14, RT-15 |
| Legal claims added | 0 | — |
| Verification states promoted | 0 | — |

## C. Code changes

See `remediation-log.md` §3 for the file list. Key logic:

- **`chipState()`** in `status-guidance.js` derives the chooser badge from the resolver's outcome for that pick.
- **A SUPPORTED cell with no answering rule** is reported as SOURCE_ONLY on that path.
- **`fillSourcePreview()`** shows the cited page verbatim, and `pageRow()` in `civic-search.js` supplies the page.
- **`manual-corpus-search.js`** excludes chapter pages that name only other statuses, and filters evidence by the resolved procedure's manual.
- **`build_status_coverage_manifest.py`** uses confirmed pages for visa procedures in the 동포 handbook.
- **`assets/js/anchored-overlay.js`** is the shared overlay anchoring.

**Data changes:** 6 page numbers, made by rebuilding with the repo's scripts.

**Schema changes:** none. The UI only reads existing fields.

## D. Test evidence

See `test-results.md`. It lists the commands, pass/fail counts and the parts that were not run.

## E. Before / after (`F-4 재외동포 → 사증발급`, same machine, base 06390bc vs this branch)

| | Before | After |
|---|---|---|
| `원문 확인` badges on the F-4 chooser | 10 of 12 | 7 of 12 (each one leads to source text or a summary only), plus a legend |
| Cited page | 383 (handbook cover / contents) | 393 (`나. 재외동포(F-4) 자격 사증발급 등 절차`) |
| Content on the answer | none | verbatim p.393 excerpt, labelled unreviewed |
| `관련 원문`, status-only screen | 129 (47 never mention F-4) | 113 (33; 0 that name only other statuses) |
| `관련 원문`, 사증발급 screen | 40 in the browser (38 in Node, 16 from the stay manual) | 19 in the browser (18 in Node, 0 from the stay manual) |
| Review notice / disclaimer | shown | shown, unchanged |
| Page errors / overflow at 390px | 0 / 0 | 0 / 0 |

Screenshots: `screenshots/before-f4-*.png`, `screenshots/after-f4-*.png`, and `screenshots/*language-panel*`.

## F. Pull request

Draft PR from `claude/gracious-rubin-37fmu4`; the link is in the session summary. It was not merged and not deployed.

## G. Remaining risks

See `unresolved-risks.md` (U-1…U-11). They are grouped by what each needs: human legal review, an additional official source, environment access, or a design decision.
