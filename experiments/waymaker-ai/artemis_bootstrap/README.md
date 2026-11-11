# Waymaker Artemis

Canonical foundation: **Google Gemma 4 E4B Instruct**. The authoritative policy
is [artemis_foundation.json](../configs/artemis_foundation.json); inference and
training validate against it. E2B is an explicitly selected development profile.
No implicit model or revision fallback is allowed.

Current Mission 005-B status, 2026-10-30: the dedicated local `.venv` now has
MLX-VLM 0.7.11 and Pillow, and real processor/tokenizer/template initialization
passed. The 32-token probe remains **not_executed** because used swap exceeded
the unchanged 2GB limit. No model weights were loaded into MLX and no tokens
were generated. See [the execution report](MISSION-005-B-REAL-INFERENCE-REPORT.ko.md)
and [hash-locked runtime dependencies](requirements-mlx-vlm-0.7.11.lock).
The recovery observations below describe earlier environment states.

Mission 005-C, 2026-10-30: a separate CUDA path loads the official
`google/gemma-4-E4B-it` checkpoint at the pinned upstream revision with explicit
NF4 4-bit quantization ([gemma4_cuda_runtime.py](gemma4_cuda_runtime.py),
[cuda policy](../configs/artemis_cuda_runtime.json)). It never pools metrics with
MLX. A free Colab T4 run was audited from the exported notebook only; it is **not
independently verified**, and no new CUDA generation has run from this code yet.
See the [audit](COLAB-T4-RUN-AUDIT.ko.md), the [Mission 005-C report](MISSION-005-C-REPORT.ko.md)
and the [reproduction notebook](notebooks/artemis_gemma4_e4b_cuda_colab.ipynb).
Mission 005-C.1 (Draft PR #730, stacked on PR #726) requires full model provenance
before a CUDA run record counts, pins the notebook to an exact code commit and
package versions, and keeps the new runtime at `not_executed` until a real GPU run.
Record checks are self-checks of our own JSON, not external attestation. See the
[Mission 005-C.1 report](MISSION-005-C1-REPORT.ko.md).
Mission 005-C.2: code commit `59858c5` ran on a free Colab T4. It loaded the
official E4B (NF4 verified on all 42 decoder layers) and completed the three
synthetic cases; the record passed its structural self-check. This is an
execution result on synthetic evidence, not legal accuracy. See the
[Mission 005-C.2 report](runs/mission005c2-cuda/MISSION-005-C2-REPORT.ko.md) and the
[Mission 005-D plan](MISSION-005-D-PLAN.ko.md).
Mission 005-D: the 20 development candidates ran once on a free Colab T4
(one model load, commit `6dfe161`). Valid JSON 20/20; Development Candidate
Diagnostic Performance 0/20, driven by status selection (17 `partial`) and by
prompt-contract and evaluator defects more than by model reasoning. See the
[Mission 005-D report](runs/mission005d-dev20/MISSION-005-D-REPORT.ko.md) and
[005-E recommendations](runs/mission005d-dev20/MISSION-005-E-RECOMMENDATIONS.ko.md).
Mission 005-E: response contract v2, evaluator repairs E1-E3 and one free T4 run
(one model load, commit `f7c751b`). Kept apart: Original DEV-20 baseline 0/20,
Evaluator-only rescoring 0/20, Contract-v2 model re-evaluation 13/20 (12/20 under the
original evaluator). The gain is mostly status selection on cases the contract was
written against; the independent synthetic set passed 11/15. See the
[Mission 005-E report](runs/mission005e/MISSION-005-E-REPORT.ko.md) and
[005-F recommendations](runs/mission005e/MISSION-005-F-RECOMMENDATIONS.ko.md).
Mission 005-F: response contract v3, language and claim-support checks, and a
code-enforced synthetic safety gate frozen before inference (commit `9332333`). On a
free T4 the locked 48-case acceptance set passed 28/48 with 12 critical failures
(unverified or forged sources treated as official), so the gate failed and DEV-20 was
not run. See the [Mission 005-F report](runs/mission005f/MISSION-005-F-REPORT.ko.md) and
[005-G recommendations](runs/mission005f/MISSION-005-G-RECOMMENDATIONS.ko.md).
Mission 005-G: a trusted-evidence pipeline (registry, admissibility, contract v4,
post-generation guard) and gate v2 frozen before inference (commit `e12cf43`). On a
free T4 the locked 63-case acceptance set had no trust bypass and 55/63 correct
end-to-end releases, but 2 answers that should have been withheld were released, so the
gate failed and DEV-20 was not run. See the
[Mission 005-G report](runs/mission005g/MISSION-005-G-REPORT.ko.md).
Mission 005-H: withhold when no asked item is covered, a labelled system notice on
partial answers, contract v5 and gate v3, frozen before inference (commit `460d40c`).
On a free T4 the new locked 75-case set had no trust bypass, no false block and no
release of an answer to something not asked; 68/75 end-to-end correct. One answer that
followed an instruction written in the question was released, so the gate failed and
DEV-20 was not run. See the [Mission 005-H report](runs/mission005h/MISSION-005-H-REPORT.ko.md).
Mission 005-I: a guard for reply instructions written in the question, an exact item
word table, contract v6 and gate v4, frozen before inference (commit `de1502d`). On a
free T4 the new locked 81-case set released nothing unsafe (no trust bypass, no false
block; the guard blocked both raw answers that obeyed a question-borne instruction);
76/81 end-to-end correct. The gate still failed on the raw-model thresholds, so DEV-20
was not run. See the [Mission 005-I report](runs/mission005i/MISSION-005-I-REPORT.ko.md).
Mission 005-J: thresholds kept; reply instructions removed from the question the model
sees, one model call per sub-code when evidence splits by sub-code, contract v7 and gate
v5, frozen before inference (commit `9dc34d2`). On a free T4 the new locked 81-case set
had no raw-model critical, nothing unsafe released and 78/81 end-to-end correct. The
gate failed on one missed situation (A05J-37), one correct answer scored wrong by an
over-tightened mention group (A05J-63) and language checks left unresolved by Korean
names quoted inline, so DEV-20 was not run. See the
[Mission 005-J report](runs/mission005j/MISSION-005-J-REPORT.ko.md).
Mission 005-K: thresholds kept; one model call per situation (in Korea / abroad), the
question's date passed to the model, Korean names copied from evidence ignored by the
language check, contract v8 and gate v6, frozen before inference (commit `abbae5f`). On a
free T4 the new locked 81-case set had 80/81 end-to-end correct, no raw-model critical and
nothing unsafe released. The gate failed on a single raw category (one answer ignored the
system reply language when the question named two languages), so DEV-20 was not run. See
the [Mission 005-K report](runs/mission005k/MISSION-005-K-REPORT.ko.md).
Mission 005-L: thresholds kept; reply-language requests removed from the question the
model receives (the system still picks the reply language from the user's question),
contract v9 and gate v7, frozen before inference (commit `be4726a`). On a free T4 all ten
language-request and neighbour cases passed, end-to-end 79/81, no raw-model critical and
nothing unsafe released. The gate failed on two raw categories: the claim-support check
read a year in a cited document title ("2026년판") as a period, and one partial answer did
not name its missing item. DEV-20 was not run. See the
[Mission 005-L report](runs/mission005l/MISSION-005-L-REPORT.ko.md).
Mission 005-M: thresholds kept; claim support reads a cited document's source fields (its
name), partial answers are given the sentence naming uncovered items (contract v10), two
more language-request forms removed, gate v8, frozen before inference (commit `824e091`).
On a free T4 the document-name and language fixes held, but the gate failed: end-to-end
72/81 and three releases counted as critical by the frozen rules (two answers gave both
conflicting values under status "answered", one correct answer hit a faulty suite
pattern). Location words inside a document name and a narrow method-question pattern
also surfaced. DEV-20 was not run. See the
[Mission 005-M report](runs/mission005m/MISSION-005-M-REPORT.ko.md).
Mission 005-N: thresholds kept; document and office names in the question are not read
as the user's location, procedure or asked items, "how can … apply" allows several words,
claim support does not read an age as a period, an opening language request is removed,
contract v11 and gate v9, frozen before inference (commit `b74210c`). On a free T4 every
system fix held: pre-inference 81/81 and end-to-end 78/81. The gate failed on three
releases counted as critical by the frozen rules: two answers again gave both conflicting
values under status "answered" (the v11 sentence did not change this), and one correct
answer hit a faulty suite pattern. The conflict-status rule is left to the owner. DEV-20 was
not run. See the [Mission 005-N report](runs/mission005n/MISSION-005-N-REPORT.ko.md).
Owner decision after 005-N: an expected conflict counts as resolved (critical) by content,
not by the status label. An answer that gives every side's value and cites every record
in conflict without preferring one is a status error. `conflict_resolution.py` holds the
rule. Gate v10 will use it, and the frozen 005-M and 005-N decisions stand.
Mission 005-O: gate v10 (the content conflict rule, and a raw category passes with 2 of 3
cases, both owner decisions), a new locked 81-case suite, system and contract v11 unchanged,
frozen before inference (commit `2891cea`). On a free T4 the gate **passed**, the first pass
since 005-F: no critical release, no trust bypass, end-to-end 78/81, raw 59/63. At the old 0.75
category bar two categories would have failed. The model labelled all three conflicts
`conflict`, so the new rule was not exercised. The three misses are Korean answers to
Vietnamese questions, which the guard withheld. DEV-20 then ran and withheld all 20 items
before the model, because no real-world registry exists (fail closed, not an accuracy result).
See the [Mission 005-O report](runs/mission005o/MISSION-005-O-REPORT.ko.md).
Mission 005-P: when the reply language is the guard's only objection, the system asks once
more with a `language_retry` note (contract v12, gate v11; raw scoring keeps the first answer).
A new locked 81-case suite was frozen before inference (commit `158e797`). On a free T4 the gate
failed on one reason, raw partial_response 1/3. One of those two misses is a correct answer that
a too-narrow suite mention group rejected (A05P-41); without it the gate would have passed, but
the frozen decision stands. All 63 answers were in the reply language, so the retry never ran.
A new system gap: claim support reads the Vietnamese date "ngày 1 tháng 6 năm 2026" as two periods
and withheld a correct answer (A05P-24). DEV-20 was not run. See the
[Mission 005-P report](runs/mission005p/MISSION-005-P-REPORT.ko.md).
Mission 005-Q: claim support reads Vietnamese dates ("ngày 1 tháng 6 năm 2026") as dates, not
periods (gate v12; contract v12 unchanged); a new locked 81-case suite was frozen before
inference (commit `541cee6`). On a free T4 the gate **passed**: end-to-end 80/81, raw 60/63, no
critical release, no trust bypass, no false block. Four correct Vietnamese answers repeated an
evidence date and were released; the 005-P reading would have withheld all four. The content
conflict rule judged its first real case (A05Q-28, both values under status "answered") as a
status error. The pass depends on the 2-of-3 category bar (true_conflict and partial_response
2/3). DEV-20 ran and withheld all 20 items before the model, because no real-world registry
exists. See the [Mission 005-Q report](runs/mission005q/MISSION-005-Q-REPORT.ko.md).
DEV-20 with a real-world registry (2026-11-03): the owner delegated the registry decisions; Claude
applied one stated rule (approve only items whose concrete claims match current statute text or the
261019 manuals, reject contradictions, leave out what cannot be checked) and recorded it in every
record. 10 approved, 5 rejected, 8 left out (`registry/dev20_decisions.json`). On a free T4, after
re-checking the 005-Q pass, 8 of 20 items reached the model and 3 passed every rubric check; 3 more
missed a literal contrast phrase and 2 answered where the 2026-10 rubric expects clarify. 12 were
withheld before the model. Five of those had evidence that contradicts current law, though the rubric
takes each item's own evidence as true. No unsafe release. See the
[DEV-20 registry report](runs/dev20_registry/DEV20-REGISTRY-REPORT.ko.md).
DEV-20 v2 (2026-11-03, not run yet): the owner delegated the 13 rubric decisions; Claude decided them
by the rule in `benchmarks/dev20_rubric_review.json` (5 rewritten from current statute text or the
261019 manuals, 3 where withholding is the right answer, 2 that accept a conditional answer, 3
loosened phrases). `build_dev20_v2.py` writes `benchmarks/artemis_eval_dev_20_v2.json`, pinned by
`DEV20_V2_MANIFEST.json`; v1 and its registry are unchanged. The five new evidence texts have their
own records in `registry/real_world_registry_v2.json`, and 13 of 20 items now reach the model.
`dev20_v2.py` loads, runs and scores v2 without touching the files the 005-Q gate freezes. See
[the decisions](benchmarks/DEV20-V2-DECISIONS.ko.md). Free T4 run (commit 5f25f18, one model
load): 13 items reached the model and 9 passed every check; 14 of 20 passed overall (v1: 3). The
failures are 002 and 010 (withheld before the model, as in v1), 011 (half the answer missing), 005
(an unasked item added), 003 (contrast missing) and 020 (same meaning, other words). No unsafe
release. See the [DEV-20 v2 report](runs/dev20_v2/DEV20-V2-REPORT.ko.md).
Mission 005-R (frozen 2026-11-03, not run yet): DEV-20 v2 item 011 released only one of the two
cases its evidence states. `branch_coverage.py` finds an answer that gives one case of a two-case
passage (markers such as `; any other`, `다만`, `trừ trường hợp`; a lexical word rule). The pipeline
asks that part once more with `branch_retry` (contract v13), and quotes a case still left out in a
labelled system notice; nothing is withheld for it. Across the 666 answers released by earlier runs it
fires only on 011. Spec section 5 states the rule; gate v13 = gate v12 with the 005-R manifest, scoring
the released retry end to end. A new locked 81-case suite (Q-4 family) has nine two-case positives,
three sub-code exceptions and two cross-language passages; its expected values were re-derived blind,
and the deterministic pipeline matches it in all 81 cases. DEV-20 v2 now runs only after a gate v13 pass.
Free T4 run (commit 9101a0a): gate v13 **failed** on one raw critical, A05R-37, a correct answer
("must obtain permission … must not exceed 18 hours per week") that the existing polarity reader takes
for a prohibition; the guard withheld it. Raw 59/63, end to end 78/81, no unsafe release, no trust
bypass. The model gave both cases in all nine two-case positives, so no branch retry happened; the
retry itself is so far shown only by unit tests. DEV-20 v2 did not run. See the
[Mission 005-R report](runs/mission005r/MISSION-005-R-REPORT.ko.md).
Mission 005-S (frozen 2026-11-03, not run yet): claim support reads a cap on an amount as a cap, not a
prohibition (`caps_apart=True` in the guard and gate v14): "must not exceed 18 hours", "not allowed to
work more than twenty", "18시간을 넘지 않는", "이 금액을 넘으면 안", "không được vượt quá 25 giờ".
Number-less negations stay prohibitions. Across the 829 answers recorded by earlier runs it changes
only A05R-37, which the 005-S guard releases and gate v14 scores correct. Gate v14 = gate v13 with the
005-S manifest; contract v13 and thresholds unchanged. A new locked 81-case suite (M-8 family) has nine
cap cases, three cap-negatives, six two-case positives and four role-reversal cases; its expected values
were re-derived blind, and the review's natural cap wordings were added to the rule before freezing.
Free T4 run (commit e12f8f5): gate v14 **passed** (raw 60/63, no critical, end to end 79/81, no unsafe
release), and DEV-20 v2 ran: 15 of 20 passed every check (first v2 run: 14). Item 011 again first gave
only one of its two cases; the branch retry quoted the other, and the retried answer stating both was
released and passes, the first time the retry fired on the real model. All nine cap cases and three
cap-negatives passed. Remaining: 005 (unasked item added), 020 (literal 내야), 003, and 002/010 withheld
before the model. See the [Mission 005-S report](runs/mission005s/MISSION-005-S-REPORT.ko.md).
Mission 005-T (frozen 2026-11-03, run 2026-11-03): a released answer whose status or form is visibly wrong
is asked once more with `status_retry` (contract v14; `status_check.py`): two cited records that differ
only in their numbers answered as answered/partial (A05M/N-28·29, A05Q/R/S-28), partial with nothing
uncovered (A05P/R/S-60), or an input field name in the answer (A05K-41, A05R/S-60). Across the recorded
answers it fires on exactly those. Nothing is withheld for it. "am I permitted / able" now counts as a
decision request (spec 2; the new suite's A05T-35 found the gap; no recorded result changes). Gate v15 =
gate v14 with the 005-T manifest; thresholds unchanged. New locked 81-case suite (J-7 family) with seven
conflict-template cases, three not-conflicts and three partial traps, re-derived blind (81/81).
DEV-20 item 005 is not this habit: the question-item reader put 'method' in uncovered_items.
Free T4 run (commit 83f5f27): gate v15 **failed** on raw true_conflict 0/3 alone; end to end was 81/81
for the first time, with no critical, no unsafe release and no trust bypass. In five conflict cases
asking what each record says the first answer was status answered; the status retry turned all five
into released conflict answers, but the raw channel scores first answers. DEV-20 v2 did not run. See
the [Mission 005-T report](runs/mission005t/MISSION-005-T-REPORT.ko.md).
Mission 005-U (frozen 2026-11-03, run 2026-11-03): the first model call names the records in conflict as
`conflict_records` (contract v15): each pair of a part's admissible records whose texts differ only in their
numbers (status_check's rule). In 005-T five conflict cases asking what each record says were answered first
and fixed only by the status retry, which the raw channel does not score. The status retry stays as the
second line. Across the 14 earlier suites the mark falls on 33 cases, all expected conflicts, and on no
DEV-20 v2 item. Gate v16 = gate v15 with the 005-U manifest; thresholds unchanged. New locked 81-case suite
(N-6 family) with seven conflict-template cases (six asking what each text says), re-derived blind (81/81);
the review changed only five patterns and one mention group.
Free T4 run (commit 829de8d): gate v16 **passed** — raw 62/63, zero critical, end to end 81/81. All seven
conflict cases answered conflict on the first call, so the status retry never fired; the one raw miss
(A05U-48) left out the uncovered item and the notice repaired it. DEV-20 v2 14/20: item 004 got the same
input as in 005-S under the longer v15 instructions and dropped its E-7-1 sentence. See the
[Mission 005-U report](runs/mission005u/MISSION-005-U-REPORT.ko.md).
Mission 005-V (frozen 2026-11-04, run 2026-11-04): a question that asks which of two sibling status codes
applies, answered with only one of them though the cited evidence names both, is asked once more with
`choice_retry` (contract v16; `choice_coverage.py`); a code still left out is quoted in a system notice.
Across 2,034 recorded questions it applies only to DEV-20 v2 items 003 and 004 (all six recorded runs of 003,
three of 004); a code and its own parent (A05N-01) is not a choice. Gate v17 = gate v16 with the 005-V manifest;
thresholds unchanged. New locked 81-case suite (X-4 family) with six choice cases and three near-misses, re-derived
blind (81/81). Of the review's edits, the cap and polarity fixes were applied; its value-to-code swap patterns
were not, because they fired on correct answers that put the value before the code.
Free T4 run (commit 8421c4d): gate v17 **failed** on raw releasable_answer 1/3 and evidence_named_code 1/3;
end to end 81/81, zero critical. All six choice questions got a first answer naming only the right code; the
choice retry added the other code in two (Vietnamese) and the notice quoted it in four. Raw scores the first
answer, as in 005-T, so DEV-20 v2 did not run. All seven conflict cases were again conflicts first. See the
[Mission 005-V report](runs/mission005v/MISSION-005-V-REPORT.ko.md).
Mission 005-W (frozen 2026-11-06, run 2026-11-09): the first model call names the codes a choice question asks
between as `choice_codes` (contract v17): the question's sibling codes that the part's admissible evidence names,
two or more, in question order. Across DEV-20 v2 and the 005-F..V suites the mark falls on exactly DEV-20 003/004
and A05V-45/62/63/68/70/71. The choice retry stays as the second line. The new suite (I-5 family) found that the
first-person reader took the "I" of I-5-1 for the pronoun; a status code letter no longer counts (spec 2), and
replaying 1,401 recorded cases changes no earlier result. Gate v18 = gate v17 with the 005-W manifest; thresholds
unchanged. Six choice cases, one per category; re-derived blind (81/81); all 19 review edits applied after checking
them against correct, value-first and real-model conflict answers.
Free T4 run (code e4464b0; notebook f1ab8b7 installs the pinned torch 2.11.0+cu130 because Colab's image moved
to 2.14.1 and the preflight blocked it): gate v18 **passed**, raw 57/63 with no critical, end to end 81/81. The
mark made the first answer name both codes in two of six choice questions (both Vietnamese); the choice retry
added the other code in one more (A05W-68) and the notice quoted it in three. Spreading the six choice cases one
per category, fixed at the freeze, is why four first-answer misses still pass. All seven conflicts were conflicts
first. DEV-20 v2: 15/20; 003 now passes with the notice, 004 still misses 숙련기능인력. See the
[Mission 005-W report](runs/mission005w/MISSION-005-W-REPORT.ko.md).
Mission 005-X (frozen 2026-11-09, run 2026-11-11): a choice question that is not split otherwise is asked one
choice code at a time (`choice_part`, contract v18) and the answers are joined in question order, as sub-code parts
are, so the raw channel scores a first answer covering every code. Across DEV-20 v2 and the 005-F..W suites exactly
the 14 known choice questions split; every other question gets the 005-W model items. A part that gives a value the
evidence states only for another choice code (`choice_coverage.swapped_values`) is asked once more (`value_retry`)
and withheld if it still does; a value the question itself quotes counts only when the part states none of its own
code's values. Gate v19 = gate v18 with the 005-X manifest and the value retry; thresholds unchanged. New locked
suite (K-3 family): six choice cases, one per category, two each in ko/en/vi, four near-misses; re-derived blind
(81/81); all 35 review edits applied after checking them against correct, value-first and 62 real-model conflict answers.
Free T4 run (commit 7c09062, pinned torch): gate v19 **passed**, raw 61/63 with no critical, end to end 81/81. All
six synthetic choice questions got a joined first answer naming both codes with their values (6/6; 005-W 2/6), but
10 of 12 parts compared both codes instead of keeping to their own, so the answer repeats the comparison; no value
retry fired. DEV-20 v2: 14/20. Items 003 and 004 got the same one-code answer from both parts, and the 005-V check,
switched off for choice parts, no longer added the notice, so 003 fails; 006 lost a phrase and 020 now passes. See
the [Mission 005-X report](runs/mission005x/MISSION-005-X-REPORT.ko.md).

Recovery status, 2026-10-29: checkpoint metadata verified; new MLX-VLM weight
loading and generation **not executed** on this M1 8GB machine. The runtime is
missing and disk/swap limits block loading. This is not a Gemma 4 accuracy result.
Official Gold Accuracy = **N/A**. No training, deployment or PR merge occurred.

Post-audit hardening, 2026-10-30: full cached E4B SHA-256 verification completed;
new inference remains `not_executed` because MLX-VLM is missing. See the
[PR #726 hardening report](PR-726-POST-AUDIT-HARDENING.ko.md) for the four audit
fixes, regression evidence and the 78-file review scope.

## Run and verify

From `experiments/waymaker-ai`, with a Python environment containing pytest and
backend development dependencies:

```bash
python -m pytest -q -p no:cacheprovider tests
python artemis_bootstrap/check_model_identity.py
python artemis_bootstrap/probe_gemma4.py --python /path/to/isolated-mlx-vlm/bin/python \
  --out /path/to/new-run/inference_probe.json
python artemis_bootstrap/artemis_runner.py --adapter local_mlx \
  --local-profile gemma4_e4b --local-runtime mlx_vlm \
  --local-python /path/to/isolated-mlx-vlm/bin/python --local-max-tokens 32 \
  --benchmark artemis_bootstrap/benchmarks/artemis_eval_dev_20.json \
  --out-dir /path/to/new-evaluation
```

The last two commands never download weights. Unavailable checkpoints/runtime
or unsafe resources produce `not_executed` and exit 3. Model operation errors
produce failed/partial status. Raw output and telemetry are retained even when
structured JSON fails. The adapter strips answer keys and rubrics from the prompt.
Candidate scoring still requires the evaluator's answer key; passing a blind
projection alone is a compatibility check, not a valid candidate accuracy run.

MLX-VLM 0.7.11 is the source-inspected runtime target; its dependency environment
must be installed separately on each machine. The local Mission 005-B environment
is isolated from verification/backend packages; use the recorded lock and explicit
Python path to reproduce it. No automatic sibling-worktree discovery is used.
The current bounds are 32 tokens in the probe (256 maximum), 2,048 prompt tokens,
120 seconds per worker, at least 6GB free disk, at most 2GB used swap, and 6GB MLX
allocation. These are conservative engineering limits, not measured requirements.

## Evidence and design

- [Recovery audit](WAYMAKER-ARTEMIS-RECOVERY-AUDIT.ko.md)
- [Foundation specification](WAYMAKER-ARTEMIS-GEMMA4-FOUNDATION-SPEC.md)
- [Inference report](WAYMAKER-ARTEMIS-GEMMA4-INFERENCE-REPORT.ko.md)
- [Fine-tuning plan](WAYMAKER-ARTEMIS-FINETUNING-PLAN.md)
- [Cleanup manifest](WAYMAKER-ARTEMIS-LOCAL-CLEANUP-MANIFEST.json)
- [Historical migration](WAYMAKER-ARTEMIS-LEGACY-MIGRATION.md)
- [Corrected Mission 005-A](MISSION-005-A-REPORT.ko.md)
- [Mission 005-B](MISSION-005-B-NEXT-STEPS.md)

The 60 candidate cases, dev/held-out partitions, evidence ledgers, review
workbench, source versioning and security regressions remain in place. The
original 40 held-out cases remain `isolation_not_verified`. Reviewer names,
dates and local signatures cannot authorize gold; an independent verifier is
not connected. Software tests do not establish legal accuracy.

Earlier E4B experiments and their limits are preserved in
[the first-inference history](history/FIRST-INFERENCE-20261026.md). They used an
older text-tower MLX-LM path and synthetic/repeated research cases. They do not
validate the new MLX-VLM adapter or supply an independent legal baseline.
