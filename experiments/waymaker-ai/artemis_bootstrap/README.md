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
[the decisions](benchmarks/DEV20-V2-DECISIONS.ko.md).

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
