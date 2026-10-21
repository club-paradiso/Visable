# Blind-label audit of the benchmark v0 legal suites

Mission 001 "Waymaker Genesis", hardening pass, integration stage, 2026-10-21.
Worktree `<repo>`, branch
`research/waymaker-genesis-legal-intelligence`, audited at the clean snapshot
commit `1481605` (benchmark digest `24528514…bff3`). Nothing in this note was
reviewed by a person, and nothing in it is a statement about Korean law.

**Result in one paragraph.** Two annotators labelled the 73 legal items blind,
working from specs [06](../06-temporal-law-and-source-identity.md) and
[07](../07-evidence-verification-design.md) and the source bundles only. They
agree with each other, with the benchmark labels and with WLIE on the overall
status of all 50 citation items (Cohen's κ = 1.000 for every pair), on every
labelled layer code (289 cells), and on the candidate versions and warning sets
of all 23 temporal items. No item met an adjudication trigger, so no label and
no line of code was changed. Every disagreement left is in a cell the labels do
not score. Each one traces to a rule that spec 07 does not state, and none
changes an overall status. Those cells are recorded below as spec gaps. The
agreement is high because one model family read one spec. That spec was
rewritten on 2026-10-20 to settle the disagreements found on the first
holdout look (the 2026-10-19 report; adjudication log A1–A4). So the agreement shows that the decided
spec can be applied consistently. It does not show that the labels are legally
correct (§6).

## 1. Material

| Input | Where | sha256 |
|---|---|---|
| Blind inputs (73 items: 50 `citation_verification`, 23 `temporal_version_selection`) | scratch `blind/blind_inputs.jsonl` | `3c4316b6…fb815` |
| Annotator 1 | scratch `blind/annotator-1.jsonl` | `ea210539…567ba` |
| Annotator 2 | scratch `blind/annotator-2.jsonl` | `f228176b…15dec` |
| Benchmark labels | `experiments/waymaker-ai/datasets/benchmark/v0/{legal_verification,temporal}.jsonl` (revision 2 labels) | benchmark digest `2452851415eebc7a2b23edea7e281bc5645228f149c90feb1b1d614e5bd94ff3` |
| WLIE | `waymaker_ai.legal` at `1481605`, called through the `wlie` baseline's own functions (`claim_input_of`, `verify_claim`, `select_candidate_versions`) | runner scoring digest `4e929c77…47dd6` (ledger entry 7) |
| Source bundles | `datasets/fixtures/sources/*.json`, bundle_version 2, unchanged since 2026-10-20 12:38 (before both annotators started) | as in the report header |

Scratch dir: `<scratch>/`.

Each blind input carries only `id`, `task`, `language`, `input` and the
scenario's `relevant_dates` and `anchor`. It carries no `expected`, no
`adversarial_class`, no notes and no `source_refs`. All 73 inputs are
byte-identical to the current benchmark inputs (checked field by field), so the
annotators labelled exactly what is scored.

The two annotators were separate Claude agents. Each was allowed specs 06 and
07, the enum strings in `contracts.py`, `dataset/tasks.py`, the example and
bundle schemas, and the three source bundles. They were not allowed the
benchmark files, `waymaker_ai/legal/`, `waymaker_ai/evaluation/`, `reports/`,
the tests, the adjudication log or each other's file. Both state that they
kept to this (§6 explains why that cannot be verified). Both files audited here
come from a second attempt (written 2026-10-20, 16:50–17:03 local time). The
first attempts ran around midday, while the bundles were still being given
`structure_complete` (one of them saw a synthetic_core flag appear at 12:28).
They wrote to the same paths and were overwritten unread. Only their
summaries survive. The first annotator-2 summary reports 16 `failed` and 15
`verification_unavailable`, one item away from the final counts. That
summary says the flag was missing on 제73조, so it read
`ver-real-r73-item4-absent` as L3 `unavailable` and overall
`verification_unavailable`. Each annotator wrote,
per citation item, the overall status, an outcome and a code for all seven
layers, a confidence and a rationale. Per temporal item each wrote the candidate
version keys, the warnings, a confidence and a rationale. Labels carry codes
only; they leave a layer out when the spec does not decide it for that input.

## 2. Method

* **Overall status.** Exact agreement, Cohen's κ (unweighted, four observed
  categories), and a 95% Wilson interval for the agreement rate. Pairs: A1–A2,
  A1–label, A2–label, label–WLIE, A1–WLIE, A2–WLIE.
* **Layer codes.** Per layer: agreement of each source with the label over the
  labelled cells, A1–A2 agreement and κ on codes and on outcomes over all 50
  items, annotator–WLIE agreement on codes and outcomes over all 50 items, and
  the same over the unlabelled cells only.
* **Temporal.** Exact equality of the ordered candidate key list, exact
  equality of the warning set, and label consistency (every required warning
  present and no forbidden warning present, which is how the runner scores it).
* **Adjudication triggers** (from the task brief), checked for overall status,
  every labelled layer code, temporal candidates and temporal warnings:
  (a) the label differs from both annotators; (b) the annotators agree with each
  other and not with the label; (c) WLIE differs from the label. Forbidden codes
  emitted by any source were also checked.
* Cells the labels do not score were compared too, and every difference
  between annotators or between an annotator and WLIE was traced to its rule
  in spec 07 (§4).
* Low-confidence premises were re-checked against the bundles (§5).

Scripts (scratch, not part of the repository): `harden-integ/r2/audit.py`
(runs WLIE in-process and computes the comparisons) and `harden-integ/r2/stats2.py`
(per-layer κ, Wilson intervals, unlabelled-cell agreement). Output:
`harden-integ/r2/audit.json`. An earlier, interrupted integration attempt ran the
same script on 2026-10-20 (`harden-integ/audit-1.json`, ledger entry 4). Its
statistics and all 73 WLIE outputs are identical to this run.

## 3. Statistics

### 3.1 Overall status, citation items (n = 50)

| Pair | Agree | Rate [95% Wilson] | Cohen's κ |
|---|---|---|---|
| A1 vs A2 | 50/50 | 1.000 [0.929, 1.000] | 1.000 |
| A1 vs label | 50/50 | 1.000 [0.929, 1.000] | 1.000 |
| A2 vs label | 50/50 | 1.000 [0.929, 1.000] | 1.000 |
| label vs WLIE | 50/50 | 1.000 [0.929, 1.000] | 1.000 |
| A1 vs WLIE | 50/50 | 1.000 [0.929, 1.000] | 1.000 |
| A2 vs WLIE | 50/50 | 1.000 [0.929, 1.000] | 1.000 |

All four sources give the same distribution: `failed` 17,
`verification_unavailable` 14, `human_review_required` 10, `verified` 9. By
split the labels are dev 2 (verified 2), test 3 (verified 2,
human_review_required 1), adversarial_holdout 45 (failed 17,
verification_unavailable 14, human_review_required 9, verified 5).

### 3.2 Layer codes and outcomes, citation items (n = 50)

Labels score 289 of the 350 layer cells.

| Layer | Labelled cells | A1 / A2 / WLIE vs label | A1 vs A2 code (κ) | A1 vs A2 outcome (κ) | A1 vs WLIE outcome | A2 vs WLIE outcome | Unlabelled cells: A1–A2 / A1–WLIE / A2–WLIE code |
|---|---|---|---|---|---|---|---|
| L1 source_identity | 49 | 49 / 49 / 49 | 50/50 (1.000) | 50/50 (1.000) | 50/50 | 50/50 | 1/1, 1/1, 1/1 |
| L2 version_identity | 48 | 48 / 48 / 48 | 50/50 (1.000) | 50/50 (1.000) | 50/50 | 50/50 | 2/2, 2/2, 2/2 |
| L3 citation_identity | 49 | 49 / 49 / 49 | 50/50 (1.000) | 50/50 (1.000) | 50/50 | 50/50 | 1/1, 1/1, 1/1 |
| L4 text_correspondence | 48 | 48 / 48 / 48 | 50/50 (1.000) | 50/50 (1.000) | **35/50** | **35/50** | 2/2, 2/2, 2/2 |
| L5 claim_support | 25 | 25 / 25 / 25 | **33/50 (0.517)** | **34/50 (0.530)** | **33/50** | 49/50 | **8/25**, **7/25**, 24/25 |
| L6 applicability | 20 | 20 / 20 / 20 | 50/50 (1.000) | 50/50 (1.000) | 49/50 | 49/50 | 30/30, 30/30, 30/30 |
| L7 conflict_uncertainty | 50 | 50 / 50 / 50 | 50/50 (1.000) | 50/50 (1.000) | 50/50 | 50/50 | – |

All seven codes equal on an item: A1–A2 33/50, A1–WLIE 32/50, A2–WLIE 49/50.
All 17 A1–A2 code differences sit in L5 cells that the labels leave out. Where
the annotators disagree with each other, the label author had already judged
that the spec does not decide the cell.

### 3.3 Temporal items (n = 23)

| Pair | Candidate key list exact | Warning set exact |
|---|---|---|
| A1 vs A2 | 23/23 | 23/23 |
| A1 vs label | 23/23 | 23/23 |
| A2 vs label | 23/23 | 23/23 |
| label vs WLIE | 23/23 | 23/23 |
| A1 vs WLIE, A2 vs WLIE | 23/23 | 23/23 |

Label consistency (required ⊆ predicted, forbidden ∩ predicted = ∅): A1 23/23,
A2 23/23, WLIE 23/23 (Wilson [0.857, 1.000]). The 23 items cover 11 distinct
warning sets, 4 items with no candidate, and 14 items with forbidden warnings.

### 3.4 Confidence

A1: high 51, medium 19, low 3. A2: high 49, medium 21, low 3. The same three
items are low for both: `ver-real-nationality-pending-quote`,
`ver-real-r73-item4-absent` and `ver-syn-manual-predates-law-version`. All
three are among the spec gaps of §4.

## 4. Adjudications

### 4.1 Items that met a trigger

| Trigger | Overall status | Labelled layer codes | Temporal candidates | Temporal warnings |
|---|---|---|---|---|
| (a) label differs from both annotators | 0 | 0 | 0 | 0 |
| (b) annotators agree, label differs | 0 | 0 | 0 | 0 |
| (c) WLIE differs from the label | 0 | 0 | 0 | 0 |
| Forbidden code emitted (A1, A2 or WLIE) | 0 | – | – | – |

No item met a trigger, so this pass has no label fix, no implementation fix
and no annotator error to record.

### 4.2 Differences below the triggers (unscored cells), and spec gaps

Each row was decided against spec 07 §3 and the bundles. In every row the
overall status is the same under each reading, because the differing layer
never decides the roll-up. Nothing was changed, so that no reading is picked
silently. Each row goes to the spec owner.

**SG-1. L5 in a blocked claim with no guidance evidence (17 items, unlabelled).**
Items: `ver-real-near-title-rule`, `ver-real-title-outside-capture`,
`ver-real-rule-article-not-captured`, `ver-real-decree-cited-for-rule`,
`ver-syn-shared-short-title`, `ver-syn-former-title-partial-index`,
`ver-syn-repealed-law-current`, `ver-syn-invented-article`,
`ver-syn-decree-text-cited-as-act`, `ver-core-near-title-complete-index`,
and the seven `ver-syn-fault-*` items (html, empty-body, official-error,
auth, history-malformed-json, provision-malformed-xml, provision-http-429).
None of the 17 claims asserts a number. Fifteen have no quotation, and two
(the decree items) quote text that L3 never reached. A1 runs the L5 rules on
empty evidence and reports `needs_review / human_review_required` for all 17:
the "no quotation and no numbers" rule for the fifteen, and "no deterministic
support signal" (invariant §2.4) for the two. A2 and WLIE carry the blocker's
outcome with `not_checked`. Spec 07 §3 says only that L5 still
runs "on guidance-only support". It does not say what that gives when there is
no guidance. The no-citation rule ("neither citations nor guidance evidence →
`fail / claim_unsupported`") would contradict the roll-ups that §3 states for
blocked claims, so neither reading can be derived from the text. **Verdict:
spec gap.** No overall effect: `needs_review` is the mildest non-pass outcome,
and the blocker already decides the roll-up. Also raised by align-bench, A1 and A2.

**SG-2. L4 in a blocked claim with no quotation and no heading (15 items,
codes agree, outcomes differ).** Items: the SG-1 list without
`ver-real-decree-cited-for-rule` and `ver-syn-decree-text-cited-as-act`. Both
annotators carry the blocker's outcome with `not_checked`. WLIE reports
`not_applicable / not_checked`, following L4's first rule ("no claimed heading
and no quoted text"), which needs no provision. The blocked-layer rule covers
a layer that "cannot produce a result because an earlier layer did not pass".
The spec does not say whether a layer with nothing to check counts as blocked.
WLIE's reading is the literal one. The annotators' reading is the more uniform
one. **Verdict: spec gap.** The code (`not_checked`) is the same, outcomes are
not scored, and the roll-up does not change. Raised by A2.

**SG-3. A cited 호 missing from a retrieved, structure-complete article:
`ver-real-r73-item4-absent` (L5 and L6 unlabelled).** Bundle evidence
(re-checked, §5): (289833, 2026-09-15) 제73조 has items 1–3 only and
`structure_complete` true, so L3 is `fail / citation_not_found` for all four
sources. The annotators agree with each other that the missing 호 does not
block, because the article itself was retrieved. They give L5
`needs_review / human_review_required` (no quotation, no numbers) and L6
`not_applicable / not_checked` (no scope). WLIE treats a missing sub-unit as
"no provision after L3". That rule was added by align-wlie on 2026-10-20 so
that L4 and L5 never judge the rest of a partly parsed article (invariants
§2.1–2.2). So L5 and L6 carry `fail / not_checked`. Spec 07 §3 lists "no
provision after L3" as a blocker but does not say whether a missing 항/호/목
counts. **Verdict: spec gap.** The overall is `failed` under both readings.
WLIE's reading never accepts a claim on text the citation did not point to, so
it is the conservative one. Raised by align-wlie, align-bench, A1 and A2.

**SG-4. Sub-unit absent from the candidate, quotation in another version:
`ver-real-nationality-pending-quote` (L4 unlabelled; all sources agree).**
Bundle: 244609 (effective 2022-10-01) 제6조 has ① and ② only, with
`structure_complete` true. 286415 (effective 2026-12-03) has ①–③, and the
quotation is in ③. All four sources give L2 `future_not_yet_effective` and
L3 `citation_not_found` (L3 checks the candidate, decided 2026-10-20). A1, A2
and WLIE also give L4 `text_match_verified` and L5 `claim_supported` against
the attributed 286415. WLIE does this by its own exception to SG-3's blocking
rule. The annotators do it because they do not block at all. The agreement
comes from two different rules, so it says nothing about whether the spec
decides L4 here. **Verdict: spec gap (consensus by convention).** The label
correctly leaves L4 out. Overall `failed` in every reading.

**SG-5. L7 walk-back through an unknown `changed_provisions`:
`ver-syn-manual-predates-law-version` (labelled; all sources agree).** Bundle:
`SYN-ADV-A1-0001` (제정, 2018-03-01) has `changed_provisions` null. A1-0002
and A1-0003 list theirs, and neither includes 제10조. C is A1-0003
(2026-03-01). The guidance edition is 2025-12-01. All four sources apply the
conservative fallback (C's date) and give L7
`needs_review / manual_predates_law_change`, overall `human_review_required`.
The other reading is that a 제정 row with an unknown list ends the walk at
2018-03-01. It gives `no_conflict_detected` and overall `verified`. **Verdict:
spec gap.** It is the one gap in this audit that flips an overall status, so
it is the most urgent. The labels follow 07 §3's own sentence ("When
`changed_provisions` is unknown, the comparison uses C's effective date"), which
does not say whose list. Raised by align-bench, A1 and A2.

**SG-6. Near title on a complete index: `ver-core-near-title-complete-index`
(labelled; all sources agree, both annotators medium).** 07 §3 L1 separates
"no rows" (`source_not_found`) from "rows returned, none exact"
(`source_ambiguous`). The fixture adapter is an exact-title index: it returns
`NOT_FOUND` and puts near matches in `detail`
(`waymaker_ai/legal/adapters.py`, `FixtureAdapter.resolve_title`). The label
(`fail / source_not_found`) is right for this adapter. The spec does not state
it as part of the adapter protocol. A fuzzy live adapter would make this
`needs_review / source_ambiguous`. **Verdict: spec gap (adapter contract).**

**SG-7. Codes for skipped and not-applicable layers.** For the no-citation
claim (`ver-syn-no-source-at-all`, L1–L4 unlabelled) all three sources use
`not_applicable / not_checked`. For L6 with no scope (30 unlabelled cells) all
three agree 30/30, using `not_checked` for `not_applicable`. Spec 07 names the
outcome but not the code. **Verdict: spec gap.** The labels correctly leave
these cells out. Unanimous, but by analogy with L4 and L7, not by rule.

**SG-8. L2 after a repeal at L1: `ver-syn-repealed-law-current` (L2
unlabelled; all sources agree on `not_checked`).** 07 §3 L2 does not say what
L2 reports after L1 `fail / source_repealed`. The blocked-layer rule reads
naturally as `fail / not_checked`, and that is what all three report.
**Verdict: spec gap**, raised by align-bench.

## 5. Evidence re-checked for the low-confidence items

* (289833, 2026-09-15) 제73조, law_go_kr_capture_2026_10_19: `structure_complete`
  true. Items `0:1`–`0:3` (청·사무소·출장소, 시·군·구·읍·면·동, 재외공관), no
  `0:4`, no paragraphs. The 2027-09-16 row of the same 289833 also has 1–3.
  This is the premise of SG-3.
* 244609 (2022-10-01) 제6조: `structure_complete` true, paragraphs 1 and 2.
  286415 (2026-12-03) 제6조: paragraphs 1–3. This is the premise of SG-4.
* SYN-ADV-ACT-01 history in synthetic_adversarial: A1-0001 2018-03-01 제정
  `changed_provisions` null; A1-0002 2023-07-01 [제12조, 제20조]; A1-0003
  2026-03-01 [제12조, 제15조, 제20조], `has_transitional_provisions` true;
  A1-0004 2027-01-01 [제12조, 제15조]. Guidance `extension-window-2025-12`,
  edition 2025-12-01, value `from_4_months_before_expiry`, equal to the claim's
  value. This is the premise of SG-5.

None of these was compared with law.go.kr in this pass, because no network
was allowed. They are the captured facts as recorded on 2026-10-19 and 2026-10-20.

## 6. Limitations

1. **One model family.** Both annotators, the label author (align-bench) and
   the WLIE authors are Claude agents. Agreement measures how clearly and
   consistently the spec can be applied by readers who share training and
   habits. It is not inter-rater reliability between independent people, and it
   says nothing about legal correctness. Shared blind spots are invisible to
   this audit.
2. **The spec was fitted to the holdout first.** The "decided 2026-10-20"
   rules in spec 07 settle exactly the disagreements A1–A4 that the first
   holdout look on 2026-10-19 exposed. The annotators read the decided spec. So
   their agreement on those items measures the decision, not the original
   spec, and the holdout is no longer a clean held-out set for WLIE (§7).
3. **Item ids leak intent.** Blind inputs keep descriptive ids such as
   `ver-real-r73-item4-absent` or `ver-syn-manual-predates-law-version`. Both
   annotators noted that an id "suggests" the designer's reading. A blind
   re-run should use opaque ids.
4. **Blindness rests on self-report.** The annotators could read the
   repository. Nothing technical stopped them from opening a label file. Both
   report that they did not, and their files show real independent variation
   (SG-1, SG-3), but this is not proof.
5. **Shared conventions fill the gaps.** Wherever the spec names no code (SG-7)
   or no result (SG-1, SG-2), the sources converged on `not_checked` by the
   same analogy. Unanimity there shows the convention is natural, not that it
   is specified.
6. **Coverage.** The audit covers the 73 legal items that existed on
   2026-10-20 at 12:14. The 13 dev items added later by align-bench (8
   citation, 5 temporal) were not blind-labelled. They are checked only label
   vs WLIE by the runner (dev 10/10 citation, 6/6 temporal). Labels leave 61
   of 350 citation layer cells out (mostly L5 and L6), and the audit cannot
   score those.
7. **Small n.** 50 and 23 items. A perfect score still has 95% Wilson
   intervals of [0.929, 1.000] and [0.857, 1.000]. κ on four categories with
   n = 50 is a coarse measure.

## 7. Holdout accounting

This audit is a look at adversarial_holdout (45 citation and 21 temporal items
are holdout items). It was recorded before the results were read:
`reports/holdout-ledger.jsonl` entry 7 (2026-10-21T04:10:54Z, commit
`1481605`, `post_hoc: true`, baselines `wlie`). The holdout was first scored on
2026-10-19 (entries 1–2). Every holdout number since then is post hoc.
[adjudication-log.md](adjudication-log.md) gives the side-by-side numbers.

## 8. Reproduce

```bash
cd <repo>/experiments/waymaker-ai
PY=<python3.11-venv>/bin/python
S=<scratch>
$PY $S/harden-integ/r2/audit.py "$PWD" $S/blind $S/harden-integ/r2/audit.json
$PY -I $S/harden-integ/r2/stats2.py "$PWD" $S/blind $S/harden-integ/r2/audit.json
```

The scratch dir is not durable. To repeat this audit later, copy the two
annotator files and the two scripts into the repository first.
