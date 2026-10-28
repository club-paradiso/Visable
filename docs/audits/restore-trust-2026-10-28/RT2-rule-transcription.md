# RT2 — filling "정리된 안내가 아직 없어요" from the official manuals (2026-10-28)

**Owner decision.** Fill the cells that showed only the official source, and show no "AI draft" label. Hide internal review labels and keep one plain reference line.

## Result

| | Before (main, a4753e0) | After |
|---|---|---|
| Authored rules | 141 | 533 |
| Document items | 838 | 3,777 |
| Status × procedure cells showing `원문 확인` | 1,449 of 2,456 | 433 of 2,528 |
| F-4 chooser badges | 7 of 12 (10 before #718) | 4 of 12 |
| Badge/outcome mismatches | 0 | 0 |
| Parent cells answered by one subcode's rule | 1 (pre-existing: D-9 연장) | 0 |

The cell count grew from 2,456 to 2,528 because new parent rules give subcodes cells they inherit. Inheritance is the existing build rule, and CLAUDE.md's parent/subcode separation is enforced by the resolver.

### The 433 cells that are still source-only

They stay source-only because the manual says nothing usable for that status and procedure. Each batch report lists them with a reason:

- **e-visa (129):** the 전자사증 lists name only a few statuses.
- **Not addressed for that subcode:** status grant (49), visa (41), confirmation (39) and status change (39).
- **Re-entry (42):** the handbook is silent for some statuses.
- **Codes with no section of their own** (F-2-R/T, F-1-72, D-8-91 …).

Nothing was invented to shrink this number.

## How the content was made

1. **Eight family batches** (`scripts/status_guidance/rules/*.py`) were transcribed from the 2026-10-19 manuals, using the HWP-derived text and the per-page PDF corpus.
2. **Every rule and document item carries an `anchor`.** The anchor is a verbatim substring of the manual, and `build_status_coverage_manifest.py` fails the build on any anchor it cannot find. This is the repository's existing gate.
3. **Two independent faithfulness reviews** compared the paraphrase (summaries, conditions, levels, states) with the manual. Sample sizes and outcomes:

   | Review | Rules sampled | Faithful | Defects |
   |---|---|---|---|
   | First | 155 | 142 | 13 rules, 11 findings |
   | Second | ~165 | 154 | 11 findings |

   Every finding was checked against the manual text before editing. Two were in the pilot rule. One finding was mine, and I withdrew it as a false positive.
4. **The stricter existing checks** (`check_status_coverage_manifest`, `check_document_guidance`, `check_document_physical_form`) then found 4 rules on an unconfirmed code (`E-7-91FTA`, removed), 3 anchors not on the cited page, misused alternative groups, and conditional items without a condition. All of these were fixed in the rules, not by loosening the checks.

The two checks that changed now test *more*:

- **Far page citations:** a far page is accepted only within the author's declared window *and* when the item's own phrase is on the cited page.
- **Lease documents:** a lease may show a physical form only when the item's own manual phrase states 원본/사본.

## Verification states (unchanged and honest)

- **No rule claims human legal review.** Every new rule keeps `review_state: SEPT_2026_ORIGINAL_UNREVIEWED`.
- **The review flags mean different things.** The manuals' `approval_state: approved` in `data/manual-corpus/catalog.json` is the owner's 2026-10-23 approval of the PDF/HWP files as the current edition. `needs_review` on the guidance means the authored content was not compared line by line by a person.
- **What users see** is no internal label. Instead there is one line, "참고용 안내예요 · 신청 전 공식 원문을 확인하세요". The law-article notice keeps its date: "요약은 이전 판본(2026-09-22) 기준이라 현행 조문은 국가법령정보센터에서 확인하세요".

## Items for a human to check (from the batch and review reports)

- **F-4 early-adaptation footnote:** is the "1회에 한해 제출 유예" deferral about the early-adaptation certificate or the criminal record? (F-4 자격변경)
- **E-7-91 "제한":** it is transcribed as GENERALLY_NOT_PERMITTED, but EXCEPTION_ONLY may fit better, since humanitarian exceptions exist.
- **C-3-8: two manual passages disagree.** The handbook lists no criminal record; the C-3 chapter's 중국동포 multiple-visa guideline asks for one at age 14+.
- **F-3-19 / F-3-20:** the heading names F-3, but the body says the stay is permitted as F-1.
- **F-2-99 activities outside status:** the employment section conflicts with the outside-status section.
- **Subcodes that inherit parent rules but may have their own chapter:** E-7-T, E-7-4R, E-7-M and the F-3 / F-2 regional (-R) codes.
- **Code names in `author_rules.py` that disagree with the manual:** F-1-21, F-1-22, F-1-72.
- **H-2 사증발급:** p.386 says new H-2 visas are suspended, and the cell is GENERALLY_NOT_PERMITTED with that sentence as the anchor.
