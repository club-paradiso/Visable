# Benchmark v0 adjudication log (WLIE vs labels)

Mission 001 "Waymaker Genesis". Worktree `<repo>`, branch
`research/waymaker-genesis-legal-intelligence`, based on origin/main `fc896c2`. Two stages:

* **Stage 2 (2026-10-21, hardening integration)**, at the snapshot commit `1481605`. It
  covers the blind-label audit, the re-scoring after the spec decisions of 2026-10-20, and
  the before/after of the law-stack fixes F1–F12. This section comes first.
* **Stage 1 (2026-10-20, first integration)**, the first look at the decision splits and
  the four ambiguities A1–A4. It is kept below as it was written, with the A1–A4 headings
  marked resolved.

This log records every disagreement between the WLIE reference implementation
(`experiments/waymaker-ai/waymaker_ai/legal/`) and the benchmark v0 labels
(`experiments/waymaker-ai/datasets/benchmark/v0/`), and how each one was decided.
Specs [06](../06-temporal-law-and-source-identity.md) and
[07](../07-evidence-verification-design.md) are the arbiter. Verdicts:

* **implementation bug**: the code contradicts the spec. Fix the code and add a unit test.
* **label bug**: the label contradicts the spec or the captured evidence. Fix the label,
  bump `revision`, add a `revision_history` entry.
* **spec ambiguity / spec gap**: the spec does not decide the case. Nothing is changed, so
  that nobody picks a reading silently. The open question goes to the spec owner.
* **annotator error**: a blind annotator contradicts the spec or the evidence (stage 2).
* **genuine baseline failure**: a deterministic baseline (B1, B2, existing_law) is wrong
  against a correct label. Labels are never edited to make a baseline pass.

No label in this log has been reviewed by a person. Nothing here is a statement about
Korean law; it is about whether readings of the same spec agree.

## Stage 2 (2026-10-21): runs

All commands from `experiments/waymaker-ai` unless noted, with
`PY=<python3.11-venv>/bin/python` (3.11.15; Node v24.14.0)
and `S=<scratch>/harden-integ`.
The working tree was clean at `1481605` for every scored run. Only the reports and the
ledger changed during the pass.

| # | What | Command (abridged) | Result |
|---|---|---|---|
| H1 | Package tests | `$PY -m pytest -q -p no:cacheprovider tests` | 1032 passed |
| H2 | Backend suite | `cd ../.. && $PY scripts/run_backend_tests.py` | 83 modules: PASS 83, KNOWN 0, SKIP 0, NEW 0, FIXED 0, "full backend suite clean", exit 0 |
| H3 | Dataset validator | `$PY -m waymaker_ai.dataset datasets/benchmark/v0 --registry datasets/registry` | PASS: 188 examples, 0 errors, 16 warnings (all `case_template_dev_eval`) |
| H4 | Audit look (WLIE, legal tasks) | `… --baselines wlie --tasks citation_verification,temporal_version_selection --splits dev,test,adversarial_holdout --out $S/r2/audit-wlie.json --holdout-ledger reports/holdout-ledger.jsonl --holdout-post-hoc '…'` | scoring digest `4e929c77…47dd6`. Ledger entry 7 |
| H5 | **Final report** | `… --baselines b1_python,b1_python_raw,b2_js,wlie,existing_law,mock_model --splits dev,test,adversarial_holdout --out reports/benchmark-v0-2026-10-20.json --markdown reports/benchmark-v0-2026-10-20.md --holdout-ledger reports/holdout-ledger.jsonl --holdout-post-hoc '…'` | scoring digest `c83cb110…25dbfa1c`. Ledger entry 8 |
| H6 | Before (pre-fix backend) | `git -C ../.. archive fc896c2 backend \| tar -x -C $S/pristine`; `… --baselines b1_python,existing_law --splits dev,test,adversarial_holdout --backend-root $S/pristine --out $S/r2/before-fc896c2.json --holdout-ledger … --holdout-post-hoc '…'` | scoring digest `be536e46…dccae`. Ledger entry 9. Backend content sha256 `eb42ed9e…3d60` (328 files) |
| H7 | Raw payloads, dev and test only | `… --baselines existing_law --splits dev,test --include-raw`, once with `--backend-root $S/pristine` and once without (scratch, no holdout, no ledger) | the same scoring digest `1515a9b0…b61b` on both trees. 7 of 13 raw payloads differ, only in `citations[0].snippet_sha256` |

An earlier integration attempt was interrupted on 2026-10-20. It wrote ledger entries 4–6
and the first version of `reports/benchmark-v0-2026-10-20.*`, on `e736072` plus
uncommitted changes, with the same scoring digests as H5 and H6. Its integration fixes
are now committed in `1481605`, and this pass checked each one with the tests named:

* `evaluation/baselines/wlie.py::claim_input_of` passes `input.claim.context_title` into
  `ClaimInput` (align-wlie's finding; without it `ver-dev-nationality-same-act-context`
  scores `source_ambiguous`). Test:
  `tests/test_evaluation_baselines.py::test_wlie_passes_every_claim_field_of_the_schema_into_claim_input`.
* `evaluation/baselines/existing_law.py::backend_question` records
  `context_title_has_no_backend_channel` instead of changing the question.
* `--holdout-post-hoc REASON` for the runner. It marks a re-scoring of items already
  seen, even under a new benchmark digest, in the ledger, the JSON and the Markdown. Tests:
  `test_a_post_hoc_holdout_run_is_recorded_as_one_even_under_a_new_digest` and
  `test_cli_refuses_a_post_hoc_run_without_a_ledger_or_a_reason`.

H5 regenerates the canonical report on the clean commit. Its scores equal those of the
earlier attempt's report. Only the provenance lines changed: commit `1481605`, no dirty
measured paths, `HEAD:backend` tree `d8c7f649…`.

### Holdout ledger

| Entry | When (UTC) | Commit | Benchmark digest | Baselines | Why |
|---|---|---|---|---|---|
| 1 | 2026-10-20 03:00 | fc896c2 + F1–F8 uncommitted | `db882bf2` | all six | **first look** (`benchmark-v0-2026-10-19-first-look.md`) |
| 2 | 2026-10-20 03:06 | same | `db882bf2` | all six | repeat for the canonical `benchmark-v0-2026-10-19.*` |
| 3 | 2026-10-20 07:55 | e736072 | `49c28618` | five | infra's CI-shaped check (scratch output) |
| 4 | 2026-10-20 08:54 | e736072 + changes | `24528514` | wlie | earlier attempt: audit look, post hoc |
| 5 | 2026-10-20 13:17 | e736072 + changes | `24528514` | b1_python, existing_law | earlier attempt: before run, post hoc |
| 6 | 2026-10-20 17:27 | e736072 + changes | `24528514` | all six | earlier attempt: report, post hoc |
| 7 | 2026-10-21 04:10 | 1481605 | `24528514` | wlie | H4, post hoc |
| 8 | 2026-10-21 05:13 | 1481605 | `24528514` | all six | H5, post hoc |
| 9 | 2026-10-21 05:13 | 1481605 | `24528514` | b1_python, existing_law | H6, post hoc |

The holdout has been looked at nine times, and its first-look numbers are those of entry 1.
The spec decisions of 2026-10-20 were written to settle disagreements seen on that look.
For WLIE, v0's adversarial_holdout is therefore no longer held out. Benchmark v1 needs a
fresh holdout, written and frozen before WLIE is run on it.

## Stage 2: how A1–A4 were resolved

| Item | Stage 1 | Decision (spec 07, 2026-10-20) | What changed | WLIE now |
|---|---|---|---|---|
| A1 `ver-syn-shared-short-title` | WLIE `human_review_required`, label `verification_unavailable` | §3 "Blocked layers": dependent layers carry the earliest blocker's outcome with `not_checked`; an ambiguous title gives `human_review_required` | label overall → `human_review_required`, blocked layers `not_checked` (revision 2, align-bench) | correct |
| A2 `ver-real-r73-item4-absent` | WLIE L3 `unavailable`, label `citation_not_found` | §3 L3: a missing 항/호/목 is `citation_not_found` only when `ProvisionText.structure_complete` is true | bundle provisions carry `structure_complete` (제73조 at (289833, 2026-09-15) true); the adapter reads it per provision; label unchanged | correct (L3 `citation_not_found`) |
| A3 `ver-real-nationality-pending-quote` | L3 unlabelled, WLIE `citation_not_found` | §3 L3 checks the candidate C | label L3 → `citation_not_found` | agrees |
| A4 `ver-syn-manual-conflicts-and-predates` | L7 unlabelled, WLIE `contradictory_evidence` | §3 L7: both findings give `contradictory_evidence` and both `ConflictRecord`s | label L7 → `contradictory_evidence` | agrees |

A1 was settled in favour of WLIE's reading, and A2 by changing the contract and the bundle.
Both happened after the disagreement had been seen on the holdout. That is why the holdout
rate moved from 43/45 to 45/45 (next section), and why 45/45 is not a first-look number.

## Stage 2: blind-label audit

Full method, statistics, limitations and spec gaps:
[blind-label-audit.md](blind-label-audit.md). Two blind annotators (Claude agents, specs
06/07 and bundles only) labelled the 73 legal items that existed on 2026-10-20. Results:

* Overall status, 50 citation items: all six pairs (A1, A2, label, WLIE) agree 50/50, with
  Cohen's κ 1.000 and Wilson [0.929, 1.000].
* Labelled layer codes, 289 cells: A1, A2 and WLIE each agree with the label in every cell.
* Temporal, 23 items: candidate lists and warning sets agree exactly for every pair.
* Unlabelled cells: annotator 1 and annotator 2 differ on 17 L5 codes (κ 0.517 over all 50).
  Annotators and WLIE differ on 15 L4 outcomes, where the codes agree.
* Adjudication triggers met: 0. So there was **no label fix, no implementation fix and no
  annotator error**. Eight spec gaps (SG-1 to SG-8) are recorded. Only SG-5
  (`ver-syn-manual-predates-law-version`, the L7 walk-back through an unknown
  `changed_provisions`) can flip an overall status.

## Stage 2: side by side, first look against now

The first look is entry 1 / `reports/benchmark-v0-2026-10-19.*`: benchmark `db882bf2`,
revision-1 labels, 175 examples, scoring digest `1f63a82f…74edc`, backend fc896c2 + F1–F8.
Now is entry 8 / `reports/benchmark-v0-2026-10-20.*`: benchmark `24528514`, revision-2
labels, 188 examples (13 new dev legal items), bundles with `structure_complete`, scoring
digest `c83cb110…25dbfa1c`, backend 1481605 (F1–F12). Cells are numerator/denominator. The
two columns differ in labels, items and code at once, so a difference has more than one
cause.

| Baseline | Metric | Split | First look | Now |
|---|---|---|---|---|
| wlie | citation overall status | dev / test / holdout | 2/2, 3/3, 43/45 | 10/10, 3/3, 45/45 |
| wlie | L3 layer agreement | holdout | 28/29 | 44/44 |
| wlie | temporal candidate exact | dev / test / holdout | 1/1, 1/1, 21/21 | 6/6, 1/1, 21/21 |
| wlie | false absences (HG-1) / accepted version failures | holdout | 0/15, 0/5 | 0/14, 0/5 |
| wlie | unlabelled absence codes | holdout | 1/45 | 0/45 |
| wlie | critical legal errors / decision | all | 0 / PROVISIONAL_GO | 0 / PROVISIONAL_GO |
| existing_law | citation overall status | dev / test / holdout | 0/2, 0/3, 9/45 | 0/10, 0/3, 12/45 |
| existing_law | false absences (HG-1) | holdout | 6/15 | 2/14 |
| existing_law | accepted version failures | holdout | 4/5 | 4/5 |
| existing_law | unsupported claims accepted | holdout | 19/25 | 19/26 |
| existing_law | critical legal errors / decision | holdout | 21 / NO_GO | 17 / NO_GO |
| b1_python | status exact | dev / test | 21/24, 47/55 | 21/24, 47/55 |
| b1_python | critical legal errors / decision | dev + test | 12 + 22 / NO_GO | 12 + 22 / NO_GO |
| b1_python_raw | status exact | dev / test | 10/24, 27/55 | 10/24, 27/55 |
| b2_js | status exact | dev / test | 21/24, 49/55 | 21/24, 49/55 |
| b2_js | critical legal errors / decision | dev + test | 3 + 6 / NO_GO | 3 + 6 / NO_GO |
| mock_model | critical legal errors / decision | all | 48 / NO_GO | 48 / NO_GO |

No classification, extraction or abstention label or baseline changed, so those suites
are identical. The HG-1 denominator went from 15 to 14 because A1's label is no longer
`verification_unavailable`.

## Stage 2: before/after of the law-stack fixes (existing backend)

Same benchmark (`24528514`, revision-2 labels) and same runner. Before = `git archive
fc896c2 backend` (pristine origin/main, no F1–F12); after = `1481605` (F1–F12).

| existing_law | Split | Before (fc896c2) | After (1481605) |
|---|---|---|---|
| overall status accuracy | holdout | 8/45 (0.178) | 12/45 (0.267) |
| false absence declarations (HG-1) | holdout | 6/14 | **2/14** |
| accepted version failures (future / wrong / outdated) | holdout | 4/5 (2/3, 1/1, 1/1) | 4/5 (2/3, 1/1, 1/1) |
| wrong-version detection | holdout | 0/5 | 0/5 |
| unsupported claims accepted (HG-5) | holdout | 19/26 | 19/26 |
| forbidden code violations | holdout | 9/45 | 5/45 |
| L1 layer agreement | holdout | 33/44 | 37/44 |
| unlabelled absence codes | holdout | 10/45 | 6/45 |
| critical legal errors | holdout | 21 | 17 |
| overall status accuracy | dev / test | 0/10, 0/3 | 0/10, 0/3 |
| false absences, accepted version failures | dev / test | not scorable (no such label) | not scorable |

* Four items flipped, all class H upstream faults: `ver-syn-fault-auth`,
  `-empty-body`, `-html` and `-official-error` went from `failed / source_not_found` to
  `verification_unavailable`. This is F9: empty, HTML or official-error bodies are typed
  errors, not "no results", so the F3 path reports `SOURCE_UNAVAILABLE`.
* The two false absences left are `ver-syn-former-title-partial-index` and
  `ver-real-title-outside-capture`. The backend's title search has no notion of index
  coverage, so a title missing from a partial index is still read as absent. This is
  Mission 002 work (06 §5).
* Accepted version failures did not change, which is expected: the backend sends no
  `efYd` and pins no version (06 §5). The four accepted items are
  `ver-real-nationality-outdated-quote`, `ver-real-nationality-pending-quote`,
  `ver-real-r73-card-quote-future` and `ver-syn-later-amendment-past-event`.
* 20 more existing_law items changed only in their raw payload hash, with identical
  scores. On dev and test (H7) the change is the article snippet hash alone. In all 20
  the cited article was fetched and matched on both trees (L1 `source_verified`, L3
  `citation_verified`), so F10, which stops a title-only hit from counting as verified,
  has no item here that shows it.
* b1_python: 0 of 91 items differ (classification and extraction do not touch the
  law stack).
* The dev and test splits cannot tell the two backends apart: H7 gives the same scoring
  digest on both trees. Every upstream-fault item is in the holdout, so only a holdout
  look shows the fix. That is why H6 had to be a holdout look.

## Stage 2: open requests to the spec owner

Consolidated from the hardening agents (align-wlie, align-bench, lawfix2, infra) and the
blind audit, most urgent first. None was acted on silently.

1. **07 §3 L7**: does an enactment (제정) row whose `changed_provisions` is null end the walk
   back to "the latest version that changed the cited provision"? This flips
   `ver-syn-manual-predates-law-version` between `human_review_required` (the label) and
   `verified` (SG-5).
2. **07 §3 blocked layers**: is a cited 항/호/목 that is missing from a retrieved article "no
   provision after L3"? And when the quotation is attributed to another version, do L4–L6
   judge that version (SG-3, SG-4)? WLIE blocks unless the quotation is attributed elsewhere.
3. **07 §3 L4/L5 with `structure_complete` false**: should `text_mismatch` and
   `claim_unsupported` require a structure-complete provision? (align-wlie; invariant §2.2)
4. **07 §3 L5 in a blocked claim with no guidance** (SG-1), and **L4 with nothing to check
   in a blocked claim** (SG-2).
5. **07 §3 codes**: L6 `not_applicable`, L1–L4 skipped for a claim with no citation (SG-7),
   and L2 after L1 `source_repealed` (SG-8). Also, does L1 become `unavailable` when the
   repeal check cannot run because `list_versions` failed? (annotator 1)
6. **Adapter protocol**: state that the fixture `resolve_title` is an exact-title index
   (near titles give `NOT_FOUND`, with the near matches in `detail`), and say what a fuzzy
   live adapter must return (SG-6).
7. **06 §3 rules 3 and 8 / `contracts.SourceVersion.effective_date_for`**: the enclosing-unit
   fallback that WLIE uses (`제7조제1항` with no entry of its own takes `제7조`'s). Also,
   does an article key return a paragraph-level entry's date (`제4조` versus `제4조제4항` on
   276857)? (align-wlie, align-bench)
8. **06 §3**: are steps 1, 2, 5 and 6 terminal? Does step 7 use `effective_date_for`?
   (annotator 2; all sources already read it this way)
9. **07 §3 L2**: version attribution when the quotation occurs both in C and in another
   version. The labels attribute it to C. (align-bench)
10. **07 §2.1 / 15 §3.6 and §4 mapping**: what counts as positive evidence of an empty DRF
    answer. Also, a mapping row for `law_grounding_source_linked_unverified` when no
    article was fetched, and the backend's cap of 3 checked provisions per question.
    (lawfix2)
11. **Benchmark v1**: opaque item ids for blind labelling, a fresh adversarial holdout,
    more non-adversarial dev legal items, and moving the dev members of the two legal case
    templates shared with the holdout to `test`. (audit, align-bench, infra)

## Stage 1 (2026-10-20): protocol and runs

All commands from `experiments/waymaker-ai`, with
`PY=<python3.11-venv>/bin/python` (3.11.15; Node v24.14.0).
Baselines: `b1_python,b1_python_raw,b2_js,wlie,existing_law,mock_model` (every offline
baseline; `openai_compatible` needs a local model server and was not run).

| # | What | Command (abridged) | Result |
|---|---|---|---|
| 1 | Package tests | `$PY -m pytest -q tests` | 893 passed (before this stage's one added test), 894 passed after |
| 2 | Dataset validator | `$PY -m waymaker_ai.dataset datasets/benchmark/v0 --registry datasets/registry` | PASS, 0 errors, 1 warning (`abstention_rubric.json` is not an example container; skipped) |
| 3 | Dev only | `$PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 --baselines … --splits dev` (scratch output) | scoring digest `1ece8264…5286e`. WLIE 3/3 legal items correct |
| 4 | **First look** at test + adversarial_holdout (and dev) | `… --splits dev,test,adversarial_holdout --out reports/benchmark-v0-2026-10-19-first-look.json --markdown reports/benchmark-v0-2026-10-19-first-look.md --holdout-ledger reports/holdout-ledger.jsonl` | scoring digest `1f63a82f…74edc`. Ledger entry 1. The first-look JSON was deleted on 2026-10-20 (its scores equal run 5's); the `.md` is kept |
| 5 | Final report | same, `--out reports/benchmark-v0-2026-10-19.json --markdown reports/benchmark-v0-2026-10-19.md` | scoring digest `1f63a82f…74edc` (identical). Ledger entry 2, `THIS RUN IS A REPEAT` |

Between runs 4 and 5 nothing in a measured path changed: no code, no label, no fixture.
Run 5 exists only so the canonical report path carries the runner's own output, and its
scoring digest equals run 4's. The ledger marks it as a repeat, and it is one. There is
therefore no pre-fix/post-fix pair to report: the numbers below are first-look numbers.

One harness bug was fixed **before** run 3, so it touched no scored result:
`evaluation/report.py::_run` stripped leading whitespace from `git status --porcelain`,
so the first dirty path was printed as `ackend/services/law_citation_guard.py`. It now
uses `rstrip()`. Regression test:
`tests/test_evaluation_runner.py::test_command_output_keeps_the_leading_porcelain_status_column`.

### The dev split could not do its job for the legal suites

The validator's `hard_negative` rule (from the task brief) keeps every adversarial item
in `test` or `adversarial_holdout`, and the benchmark puts all of them in the holdout.
Only 5 of 50 citation items and 2 of 23 temporal items have no adversarial class, so
`dev` holds 2 citation items and 1 temporal item (and `test` 3 + 1). Dev iteration on WLIE
was therefore close to empty, and the adjudication below happened on the first holdout
look. Nothing was tuned on it (no change at all followed). The next benchmark version
needs either many more non-adversarial legal items, or a change to the brief that allows
a dev pool of adversarial items, separate from the held-out ones.

## Stage 1: WLIE first-look results

| Split | citation_verification overall | temporal_version_selection | critical legal errors |
|---|---|---|---|
| dev | 2/2 | 1/1 | 0 |
| test | 3/3 | 1/1 | 0 |
| adversarial_holdout | 43/45 (0.956, 95% CI 0.852–0.988) | 21/21 | 0 |

Hard gates HG-1 to HG-6, HG-8 and HG-9 pass on the decision splits; the decision is
`PROVISIONAL_GO` because no scored label is human-verified.

Three items have at least one metric where WLIE and the label disagree. All three are
spec ambiguities. No implementation bug and no label bug was found.

### A1. `ver-syn-shared-short-title` (adversarial_holdout, class A): spec ambiguity (resolved 2026-10-20, see stage 2)

* **Input.** Claim cites `가상특례절차법 제2조` on `synthetic_adversarial`. Two identities
  (SYN-ADV-ACT-02 `가상체류절차특례법`, SYN-ADV-ACT-03 `가상체류절차지원법`) carry that
  exact short title.
* **Label.** L1 `needs_review / source_ambiguous`; overall `verification_unavailable`,
  read through the L5 rule "the evidence could not be retrieved: `unavailable`".
* **WLIE.** L1 `needs_review / source_ambiguous` (agrees). L2–L6 are
  `not_applicable / not_checked` with the blocking layer named in `detail`; L7
  `pass / no_conflict_detected`. Overall `human_review_required`.
* **Why the spec does not decide it.** Spec 07 §3 says nothing about L2–L7 after an L1
  that is `needs_review`. Three readings are each defensible from its text:
  1. Blocked layers are `not_applicable`, and the blocker carries the outcome, so the
     roll-up is `human_review_required` (WLIE). Support: §3's preamble uses
     `not_applicable` for skipped layers ("skips L1–L4 (`not_applicable`)").
  2. A blocked L5 "could not run", which is the §1 definition of `unavailable`, so the
     roll-up is `verification_unavailable` (label).
  3. An ambiguous citation is not a "resolvable citation", so the preamble applies: L5 is
     judged on guidance alone, and with no guidance L5 is `fail / claim_unsupported`, so
     the roll-up is `failed`.
  All three keep the claim from being accepted. They differ in what the user is told:
  "a person has to say which law was meant" against "the source could not be checked".
* **Decision.** Nothing changed. Both readings 1 and 2 are listed for the spec owner.
  The benchmark author had already asked for this (contract request "define what L2–L7
  report after L1 is needs_review or unavailable").
* **Effect on scores.** WLIE is scored `wrong` on this item (overall status). This is the
  difference between 45/45 and 44/45 on the holdout.

### A2. `ver-real-r73-item4-absent` (adversarial_holdout, class B): spec ambiguity (resolved 2026-10-20, see stage 2)

* **Input.** Claim cites `출입국관리법 시행규칙 제73조제4호` on the real capture bundle,
  anchor = question date 2026-10-19. The candidate is (289833, 2026-09-15), whose
  `parse_status` is `partial` (only 제73조 was captured for that version).
* **Evidence.** The capture `v05_v06_art73_extract.txt` (sha256
  `e0223bf3d074267ae36c7550ecc62aced5334cdbde183c7fba7676d20acc0dd0`, the value recorded
  as `content_sha256` of both 289833 rows) holds the whole of 제73조 for
  efYd 20260915: the lead-in "다음 각 호와 같다", items 1 to 3, then the closing
  "[전문개정 2003. 9. 24.]". There is no 제4호. The label's factual premise is right.
* **Label.** L1 `source_verified`, L2 `version_verified`, L3 `fail / citation_not_found`
  (spec 07 §3 L3: "A cited 항 / 호 / 목 is absent from the provision structure");
  overall `failed`.
* **WLIE.** L1 and L2 agree. L3 is `unavailable / verification_unavailable` with
  "item 0:4 is not in 제73조, but the provision structure was only partly parsed";
  overall `verification_unavailable`. The cause is in `legal/adapters.py::get_provision`:
  a found provision gets `Coverage.PARTIAL` whenever its version's `parse_status` is not
  `complete`, and `verification._check_citation` only fails a missing sub-unit under
  complete coverage.
* **Why the spec does not decide it.** Two fixed texts pull in opposite directions:
  * Spec 07 §3 L3 states the sub-unit rule with no coverage condition, and §1 defines
    `fail` as "the check ran to completion on evidence that was retrieved". The bundle
    schema (`schemas/source_bundle.schema.json`) defines `parse_status` at the level of
    the provision set ("complete = every provision of this version is in the bundle").
    On that reading a captured provision is whole, and the label is right.
  * Spec 07 §2.1 says only `NOT_FOUND` with complete coverage can produce
    `citation_not_found` (taken literally, the sub-unit rule could then never fire, since
    the provision lookup is `FOUND`), and §2.2 says partial coverage is not absence. The
    fixed contract `contracts.ParseStatus.PARTIAL` is documented as content damage
    ("e.g. tables flattened, annex images not read"), which can lose a 호 inside a
    provision that was found. On that reading WLIE's conservative `unavailable` is right.
  Neither the bundle format nor `ProvisionText` records whether one provision's
  structure was captured whole, so the adapter cannot tell the two cases apart.
* **Decision.** Nothing changed. WLIE's direction is the safe one: it neither accepts
  the claim nor declares an absence. The fix belongs in the contract, not in either side
  alone: add a per-provision completeness signal (for example
  `ProvisionText.structure_complete`, or a documented meaning of `Coverage` on a `FOUND`
  provision lookup), state the sub-unit rule's coverage condition in 07 §3 L3, then have
  the adapter report complete coverage for a provision captured whole.
* **Effect on scores.** WLIE is scored `wrong` on overall status and on the L3 layer
  code. It also costs one point of L3 layer agreement on the holdout (28/29).

### A3. `ver-real-nationality-pending-quote` (adversarial_holdout, class E): spec ambiguity, no scored mismatch (resolved 2026-10-20, see stage 2)

* **Input.** Claim cites `국적법 제6조제3항` with a quotation that occurs only in
  286415 (effective 2026-12-03); anchor = question date 2026-10-19; the candidate is
  244609 (effective 2022-10-01, `parse_status` complete), which has no 제6조제3항.
* **Label.** L1 `source_verified`, L2 `fail / future_not_yet_effective`, overall
  `failed`. L3 is deliberately unlabelled: "the spec does not say whether L3 then checks
  the candidate or the attributed version".
* **WLIE.** Agrees on L1, L2 and overall (verdict `correct`). It checks L3 on the
  candidate and reports `fail / citation_not_found` (complete coverage), and L4/L5 on the
  attributed version (`text_match_verified`, `claim_supported`).
* **Why it is listed.** The runner counts an absence code the label does not list
  (`citation.unlabelled_absence_codes` = 1 for WLIE on the holdout). The count is not a
  gate. Spec 07's layer table ("in that version", after L2's "the version that applies
  on the anchor date") and `contracts.VerificationLayer` lean towards the candidate, but
  L4 says "for the attributed version" explicitly and L3 does not, so the label author's
  reading is also open. Nothing changed. Request: spec 07 §3 L3 should name the version
  it checks when attribution moved the claim to another version.

### A4. `ver-syn-manual-conflicts-and-predates` (adversarial_holdout, class J): spec ambiguity, unlabelled (resolved 2026-10-20, see stage 2)

Both L7 rules fire (a guidance value differs from the claim, and the guidance edition
predates the version). WLIE reports `contradictory_evidence`: `worst()` keeps the first
of two equally severe findings, and the value check runs first. Both `ConflictRecord`s
are produced. The label leaves the L7 code unlabelled, so nothing is scored. Request:
spec 07 §3 L7 should say which code the layer reports when both apply (or allow both).

## Stage 1: baseline failures (genuine; no label changed)

None of these led to a label change. Each was checked for a harness cause (fake server
shape, driver) before it was accepted as the baseline's own behaviour.

* **existing_law, cited 약칭 never matches.** `ver-real-ewa-short-title-numbers` and
  `ver-syn-short-title-pending-change` (dev). The fake `lawSearch.do` returns the law
  for the 약칭 query (row with `법령명한글` and `법령약칭명`), but
  `law_grounding._verify_requested_articles` compares the cited name only with the row's
  official title and reports `failed_verification` + `CITED_LAW_NOT_FOUND`
  (`source_not_found`) for a law it just found.
* **existing_law, failure bodies read as "no results".** `ver-syn-fault-empty-body`,
  `ver-syn-fault-official-error`, `ver-syn-fault-auth` (holdout, H). An empty 200 body
  and the official error envelope come back as `law_api_no_results`, so the F3 fix
  (search errors become `error` / `SOURCE_UNAVAILABLE`) never sees an error and the
  backend declares absence. With `ver-syn-former-title-partial-index`,
  `ver-real-title-outside-capture` and `ver-syn-shared-short-title` this gives
  HG-1 false absence 6/15 on the holdout. Fixing the parser is backend work outside this
  stage (only regressions of this mission's backend changes could be fixed here).
* **existing_law, no version pinning.** 4 of 5 version-failure items accepted
  (future-not-yet-effective 2/3, wrong version 1/1, outdated 1/1); wrong-version
  detection 0/5. Expected: the backend sends no `efYd` (spec 06 §5).
* **existing_law, unsupported claims accepted.** 19 of 25 holdout claims that should be
  rejected are reported verified (a title hit plus an article match is the whole check).
* **b1_python / b1_python_raw.** Subcodes are never emitted (0/29 subcode-expected on
  test), and `b1_python` places a subcode in the status field or falls back to a parent
  on 26 of 55 test items (HG-10). Critical classification errors: 22 on test.
* **b2_js.** Status exact 0.891 and fine procedure 0.800 on test. Typical misses:
  `cls-en-a3-month-trap` and `cls-en-2nd-year-trap` ("a 3", "a 2" read as A-3/A-2),
  `cls-ko-f10-nonexistent` and `cls-en-f10-visa-application` (F-10 read as F-1), and
  non-Korean wording with no status-guidance keyword (procedure `null`).
* **mock_model.** A floor by design (always abstains or returns nulls).

## Stage 1: backend suite after the law-stack fixes

`cd <repo> && $PY scripts/run_backend_tests.py` on the full
checkout, with the uncommitted F1-F8 changes in place: 83 modules, PASS 83, KNOWN 0,
SKIP 0, NEW 0, FIXED 0, "Result: full backend suite clean.", exit 0, 3 min 32 s. The
sparse-checkout baseline was 77 of 82 passing, with the failures attributed to files the
sparse checkout lacked (the brief names `test_ai_shell_source_semantics`,
`test_i18n_law_fallback_live_smoke`, `test_i18n_sweep_route_wizard` and
`test_source_grounding_pipeline`). On the full checkout every module passes, and the
83rd module is the new `test_law_stack_genesis_regressions.py`. No backend file was
changed in this stage.

## Stage 1: requests to the spec owner (all five answered on 2026-10-20, see stage 2)

1. 07 §3: what L2–L7 report after L1 is `needs_review` (A1); state whether blocked layers
   are `not_applicable` with the blocker carrying the roll-up, or `unavailable`.
2. 07 §3 L3 and §2.1: the coverage condition for a missing 항/호/목 inside a provision
   that was found, plus a per-provision completeness signal in the bundle format and
   `ProvisionText` (A2).
3. 07 §3 L3: which version L3 checks when L2 attributed the claim to another version (A3).
4. 07 §3 L7: the code when `contradictory_evidence` and `manual_predates_law_change`
   both apply (A4).
5. Benchmark v1: enough legal items in `dev` to iterate on before the holdout is looked
   at. That means more non-adversarial citation and temporal items, or a brief change that
   allows a dev pool of adversarial items (the `hard_negative` rule forbids it today).
