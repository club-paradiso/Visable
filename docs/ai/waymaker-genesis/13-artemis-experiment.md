# 13 — Artemis: the first fine-tuning experiment (prepared, NOT RUN)

Status: **NOT RUN.** The configs, scripts, gates and tests are ready. No model
was trained, served or evaluated in Mission 001. There was no GPU on the
preparation machine, paid compute was not authorised, and benchmark v0 has no
train split.

The arms are defined in `experiments/waymaker-ai/configs/artemis/`, and the
procedure is in
[`experiments/waymaker-ai/training/README.md`](../../../experiments/waymaker-ai/training/README.md).
The evidence comes from
[research-notes/training-distill.md](research-notes/training-distill.md),
[models.md](research-notes/models.md), [cost.md](research-notes/cost.md) and
[status-classifier.md](research-notes/status-classifier.md).

## 1. Decision in one paragraph

Artemis is the compact routing and extraction step. From the text of a question
it reads the parent status code, the exact subcode, the procedure and the dates
with their roles. It never answers the question, and it never states a
requirement, fee, period or eligibility rule. Most of that work can be settled
by rules, and the workspace rule is to prefer a deterministic check to a model
call. So the experiment is built to decide **whether to train at all**:

1. Build the cheap rule fixes (§6).
2. Score the rules, and the untuned model (arm A), on the frozen benchmark.
3. Train arm B (QLoRA SFT on reviewed labels) only if the fixed rules stay
   below the targets in [12](12-evaluation-methodology.md) on text-only
   subcode or procedure detection.
4. Run arm C (B plus gated, human-reviewed teacher labels) only if B passed
   its safety gate and still has a gap that more label variety could close.

Facts are never trained into the weights. The only training targets are
structured labels.

The names Artemis, Athena and Hestia appear nowhere in the repository
(training-distill.md §2.0, VERIFIED absence). The role used here is the one
the notes define (INFERRED there): a compact model of roughly 2-12B dense
parameters, or about 3-4B active parameters for a mixture-of-experts model.
training-distill.md §2.0 gives that range; models.md §5 narrows it to about
9B total or less.

## 2. Hypotheses

| Arm | Hypothesis | Null hypothesis (what ends it) |
|---|---|---|
| A (untuned) | Prompted Gemma 4 E4B-it, given the runner's `openai_compatible` prompt and constrained to its 7-key schema, matches the best fixed rules on text-only status detection. It exceeds them on procedure detection for colloquial and non-ko/en questions. It makes zero parent-for-subcode substitutions and zero visa/stay scope mixes | It beats the fixed rules on no text-only metric, or it adds critical errors that the rules do not make. The rules then stay authoritative |
| B (SFT QLoRA) | SFT on human-reviewed classification labels raises `subcode_exact` and `procedure_fine` over A on `test` and `adversarial_holdout`, with a 95% CI that excludes 0, and adds no critical error | No gain beyond the CI, or a gain that comes with critical errors. The adapter is discarded |
| C (verified distillation) | At equal tokens and steps, adding teacher labels that passed the deterministic checks, the teacher gate and human review beats B on `adversarial_holdout` (classes I and K) and on non-ko/en items (training-distill.md §4.1 H2) | Not better than B beyond the CI, or it inherits teacher errors. B, or the rules, stands |

training-distill.md H3 (no memorisation of facts) does not apply in its
original form. The targets carry no facts, so there is no fact to memorise.
What an adapter can still memorise is question templates. The leakage guard
and the split-by-template rule (§5) address that, and `adversarial_holdout`
measures it.

## 3. Baselines and arms

| Id | What it is | Source | Known limits |
|---|---|---|---|
| B1-python | Production `/api/ask` contract: `_detect_visa_codes` + `_detect_task_type` + `understand()`, with `PYTHONHASHSEED=0` | status-classifier.md §9 | Reads no subcode from free text (R4). Nondeterministic without the seed pin (R2) |
| B2-js | Search and quick-answer contract: `VisableStatusGuidance.interpret` + `nextStep` | status-classifier.md §9 | Article false positives such as "a 3" → A-3 (R3), token glue (R6), no procedure for zh/ja/vi/ru (R12) |
| **B-fixed** | The better of B1 and B2 after the cheap fixes in §6 | this document §6 | **Not built in Mission 001.** D1 cannot be decided until it exists |
| A | Untuned `google/gemma-4-E4B-it` with the runner's `openai_compatible` prompt and constrained 7-key JSON | `exp_a_untuned.json` | No Korean benchmark exists for Gemma 4 (models.md §7) |
| B | A + QLoRA adapter trained on reviewed labels | `exp_b_sft_qlora.json` | Train split EMPTY |
| C | B + gated teacher labels from self-hosted gpt-oss-120b and Gemma 4 31B-it | `exp_c_verified_distill_sft.json` | Train split EMPTY, legal sign-off pending, no teacher served |

Scoring follows status-classifier.md §9:

- Only text-only items count (`payload_status_code` null).
- A subcode is credited only from the explicit `subcode` field. A parent in that
  field, or a parent fallback, is wrong.
- Procedures are scored on the 16 fine ids and mapped through
  `contracts.FINE_TO_COARSE`. Items without a coarse equivalent are reported as
  not scorable for the backend baselines.

## 4. Models

| Role | Repo id @ revision | Licence | Why |
|---|---|---|---|
| primary | `google/gemma-4-E4B-it` @ `ee0ef6023621cff504d758262d4e04895a5af4a2` | Apache-2.0, `gated: false` | models.md §5 Artemis rank 1. It is the same family as the production router, has the widest tooling, and fits a 16-24 GB GPU for QLoRA (about 9-12 GB, INFERRED) |
| secondary | `google/gemma-4-E2B-it` @ `3e22461f65e89153144f8adb70e3b8c2cc9845a7` | Apache-2.0, `gated: false` | Cheaper sibling. It fits a free T4 (about 6-8 GB, INFERRED) and is used for the smoke run. It is preferred if it scores within E4B's CI (models.md §5 design note) |

Both SHAs are the HF HEAD values that models.md recorded on 2026-10-19 and
that its verifier re-checked. `test_training_configs.py` fails if a config's
SHA differs from the one in models.md.

Caveats, all carried into the configs:

- No Gemma 4 repo ships a LICENSE file. Archive Google's licence page beside
  the SHA.
- Whether Google's Gemma Prohibited Use Policy binds Apache-2.0 Gemma 4 is
  unresolved (models.md §4, §8). Waymaker stays "information, not legal
  advice".
- Whether `AutoModelForCausalLM` loads the `Gemma4ForConditionalGeneration`
  checkpoint text-only, and whether all seven LoRA target names exist, is
  UNVERIFIED. The smoke run checks both, and `train_qlora.py` refuses if a
  target has no language-model match.

Alternatives are recorded, not configured:

- Kanana-2-3B is Korean-native, but its licence requires "Powered by Kanana"
  and naming duties;
- Granite 4.2 3B/8B;
- Mi:dm 2.0 Mini;
- Qwen3.5 is technically the strongest but policy-blocked (models.md §5).

## 5. Data

- **Evaluation:** benchmark v0 `dev`, `test` and `adversarial_holdout`. The
  configs assume the path `datasets/benchmark/v0`; align it with the benchmark
  task's output before the first run. The guard reads that directory
  recursively, as the runner does.
- **Train split: EMPTY.** v0 has no train split, and every config says so
  (`dataset.train.status: "EMPTY"`). A train split must:
  - be benchmark-format examples with `split: "train"`;
  - pass `waymaker_ai.dataset.validate`;
  - be split by case template, so that no template appears on both sides;
  - be reviewed, with critical labels `human_verified` by a named reviewer.

  The working target is 1,500-3,000 examples. That is training-distill.md
  §4.2's range for task-specific SFT, applied to Artemis (INFERRED).
- **Tasks:** `status_procedure_classification` and `entity_date_extraction`
  only. Citation verification and temporal version selection belong to the
  deterministic WLIE gate ([07](07-evidence-verification-design.md)), and
  abstention belongs to Athena. The builder refuses any other task.
- **Prompt and target: the runner's, not a training-only format.** The
  runner's `openai_compatible` baseline asks the model one system prompt and
  one 7-key schema (`status_code, subcode, procedure, current_status,
  target_status, dates, needs_clarification`) for both Artemis tasks, and the
  user turn does not say which task is being scored. The SFT builder imports
  that prompt (`baselines.model.build_messages`) and that schema
  (`predictions.model_output_schema`) instead of defining its own, so the
  adapter is trained on exactly the request it is scored on.
- **One record per question, both labels required.** Because the model cannot
  tell the two tasks apart, one question has one target object. A benchmark
  example labels only its own task, so the builder pairs the
  `status_procedure_classification` and `entity_date_extraction` examples that
  share the exact question text and payload code. A question with only one of
  them is refused. The classification label must state `current_status`,
  `target_status` (null allowed) and `needs_clarification` explicitly; `dates`
  comes from the entity label. No key is ever filled with a guess: writing
  `"dates": []` for a question that names a date would teach the model to drop
  dates. `not_status_tokens` and `status_codes` stay scoring labels and are not
  target keys.
- **Labels only.** The target carries no reasoning, no evidence text and no
  legal content. This is how training-distill.md §0.6 ("train only
  behaviour") applies to a classifier.
- **Leakage guard** (`waymaker_ai/distillation/leakage.py`):
  - word 3-grams, Jaccard similarity, threshold 0.5;
  - exact duplicates (after normalisation) refused within the train split and
    against every eval split.

  A refusal is fixed by re-splitting by template, never by raising the
  threshold. Word grams, not character grams: two unrelated Korean questions
  about the same procedure share many character 3-grams, while template
  siblings share most word 3-grams. Status codes stay whole tokens.
  The guard reads every file the runner reads (any depth, manifests and
  dotfiles excepted), and an unreadable eval file is a refusal. The dataset
  validator is run on the train file *together with* the benchmark, so its own
  character-3-gram contamination rule (Jaccard ≥ 0.85, an error between train
  and every eval split) runs as well.
- **Teacher labels (arm C only):** teachers see train prompts only. Each answer
  becomes a `TeacherRecord`, which `gate_record` must accept (§8). The surviving
  examples are `teacher_generated`, with `expected` byte-equal to the gated
  output. They are mixed about 1:1 with gold and subsampled to arm B's tokens.
  A teacher shown the runner's prompt answers with the 7-key object; the
  (unbuilt) harness must split that answer into one `TeacherRecord` per task
  label, so that each half passes the gate on its own.

## 6. Where deterministic rules beat a trained Artemis, and the decision rule

The notes are explicit: parsing codes, keeping parent and subcode apart,
keeping visa and stay procedures apart, deadlines and model escalation are
rules, not judgements (training-distill.md §5). Most of the defects
status-classifier.md found in the existing classifiers have a cheap
deterministic fix. The fixes below are proposals; none was built in Mission 001.
R9-R11 (circular golden labels, over-tagging, data shape) are dataset and
tagging problems outside this table.

| Defect (status-classifier.md §10) | Cheap rule fix (B-fixed) | Why a model would be worse |
|---|---|---|
| R2: same-length codes win by hash seed (`paradiso_backend.py:3881`) | Sort candidates by (length, text) | A model adds variance where a sort removes it |
| R3: "a 3 month" → A-3, "a 2nd year" → A-2 | Accept a code only as letter-hyphen-digits, or a compact form validated against the inventory. Never letter-space-digit in English text | The rule is exact; a model only learns it statistically |
| R4: Python reads no subcode from text | Read 3+-segment codes and `*-T` and validate them against the inventory, as JS `normalizeCode` already does | Validation against the inventory is ground truth; the model's output has to pass it anyway |
| R5: `D-4-2K` → `D-4-2`, `F-2-7S` → `F-2-7` (a different real code) | Capture letter-suffixed segments whole and check them against the inventory | Same |
| R6: "D-10 to" → `D-10-TO`, "D-10 E-7" → `D-10-E` | A segment is digits or a suffix that exists in the inventory | Same |
| R7: no visa issuance, CVI or re-entry branch; "A에서 B로 변경" and "change from X to Y" missed | Add the missing procedure keywords and the two transition patterns | A keyword list is auditable and costs nothing per call |
| R13: `\b` fails before Hangul (`D-2-1비자` → D-2) | Explicit non-alphanumeric lookarounds | Same |
| R1: `understand()` fills the parent silently | Never fill a parent when the text names a subcode; report the gap | This is a correctness rule (CLAUDE.md), not a prediction |
| R8: JS and Python encode opposite inheritance policies | A person decides | Neither a model nor a rule can settle a policy question |

B-fixed must be built as a separate deterministic baseline in
`experiments/waymaker-ai`, not by editing `backend/paradiso_backend.py`, which
carries the owner's unpushed work.

A model can plausibly add value only where no rule reaches:

- questions in zh, ja, vi and ru, where every component loses the procedure
  (R12);
- phrasing that no keyword list covers;
- deciding that a question is ambiguous (`needs_clarification`).

**Decision rule D1** (it is a gate in every config):

1. Build B-fixed, then score B1, B2, B-fixed and arm A on `dev`, on text-only
   items.
2. If B-fixed meets the [12](12-evaluation-methodology.md) targets on
   `subcode_exact` and `procedure_fine`, **do not train**. Artemis is not needed
   for these tasks. If only the multilingual slice misses, scope a narrower
   experiment to that slice.
3. If B-fixed misses a target and arm A closes the gap while passing G1, the
   proposal is: rules first, the prompted model only for the items where the
   rules return nothing or flag ambiguity, and every model output re-validated
   against the inventory. No training.
4. Train arm B only if both B-fixed and arm A miss the target. Run arm C only
   if B passed G1 and a gap remains.

Whatever happens, the deterministic layer keeps the last word on code
hierarchy. An Artemis output that names a parent as a subcode, or a subcode
that does not exist, is rejected by the same validator the benchmark uses.

## 7. Configs and hyper-parameters

| Config | Arm | Trains | Base | Status |
|---|---|---|---|---|
| `configs/artemis/exp_a_untuned.json` | A | no (`training: null`) | E4B, secondary E2B | NOT RUN |
| `configs/artemis/exp_b_sft_qlora.json` | B | QLoRA | E4B, secondary E2B | NOT RUN |
| `configs/artemis/exp_c_verified_distill_sft.json` | C | QLoRA + gated teacher labels | E4B; teachers gpt-oss-120b @ `b5c939de…`, Gemma 4 31B-it @ `842da379…` | NOT RUN |

Arms B and C share every hyper-parameter, so a difference comes from the data.
Each value carries a one-line `why` in the config, and the loader rejects a
missing one.

| Parameter | Value | Justification (short) |
|---|---|---|
| quantisation | 4-bit NF4, double quantisation | QLoRA; the arm B setting (training-distill.md §4.2); assumed by the models.md §6 VRAM rule |
| compute dtype | `auto` | bf16 where supported, fp16 on a T4. The old scaffold hard-coded bf16 |
| LoRA r / alpha / dropout | 16 / 32 / 0.05 | r and alpha from §4.2. Dropout is INFERRED (light regularisation for a few thousand short examples) |
| target modules | q, k, v, o, gate, up, down projections | All linear projections of the language model (§4.2). Vision and audio towers are excluded |
| learning rate / schedule / warm-up | 2e-4, cosine, 3% | §4.2; scheduler and warm-up are common defaults (INFERRED) |
| epochs | 2 | §4.2 gives 1-3. Only dev loss can move it to 1 or 3, decided before test is scored |
| max sequence length | 2048 | Question cap of 2,000 characters plus the prompt. The script refuses rather than truncates |
| batch | 1 × 16 gradient accumulation | Micro-batch 1 is the VRAM assumption; about 90-190 steps per epoch |
| optimiser | paged AdamW 8-bit | models.md §6 VRAM assumption |
| loss | completion only | Loss on the JSON target only; TRL `completion_only_loss` (VERIFIED in the notes) |
| seeds | 1, 2, 3 | §4.2 controls; mean with a 95% bootstrap CI |
| decoding at evaluation | the runner's `DECODING`: temperature 0, seed 0, `max_tokens` 512, strict JSON schema | Labels, not prose. §4.2's temperature 0.2 is for answer wording. The config restates the values and the loader rejects any that contradict the runner |

`waymaker_ai/distillation/experiment_config.py` validates the configs. It
refuses unknown keys, a revision that is neither a 40-character SHA nor
`REVISION_REQUIRED`, `cost.paid_runs_authorised` other than false, eval splits
other than the three frozen ones, decoding values that contradict the runner's,
and a prompt hash that differs from the runner's current prompt, schema and
decoding.

## 8. Teacher policy and the distillation gate

`configs/teacher_policy.json` records the reading in training-distill.md §3
for every provider and model family it covers, per serving channel. It adds
the four models.md §4 families whose licences say something about outputs or
distillation (EXAONE 4.x, HyperCLOVA X SEED, Muse Spark Open, Kanana 2). 34
entries:

| Verdict | Entries |
|---|---|
| `permitted_with_conditions` (6 entries, all self-hosted) | Nemotron 3 Ultra / 3.5 Lightning (OpenMDW), Nemotron 3 Super (Nemotron OML), Gemma 4, Inkling, gpt-oss, Llama 3.1/3.3 |
| `not_permitted` (9) | NVIDIA API Trial (via OpenRouter `:free` and direct), Thinking Machines free research tier (both routes), OpenAI API, Anthropic API, Gemma 1-3 (Model Derivatives), EXAONE 4.x (non-commercial; outputs may not build competing models), HyperCLOVA X SEED (a distilled student is a Derivative Model under the legal-services AUP and competition clause; models.md Rec. 5) |
| `requires_legal_review` (19) | Gemini API, Gemma via AI Studio or OpenRouter, every paid OpenRouter host, NVIDIA NIM subscription, Groq, Llama, Hermes and gpt-oss `:free` routes, Qwen, DeepSeek, MiniMax M3, InclusionAI Ling, Muse Spark Open (distilled student is a Derivative under its unlicensed-practice AUP), Kanana 2 (distillation counts as a Derivative Work) |

A family no note assessed (K-EXAONE 2.0, for example) has no entry and is
denied by default.

Rules the policy enforces:

- **Default deny.** No entry, an unknown channel or a missing field all mean
  "not a teacher".
- **The most restrictive match wins.** A permissive weights licence never
  outvotes a restrictive channel: the same Nemotron weights are permitted
  self-hosted and denied on the trial route.
- **An API route id cannot be self-hosted.** A model id with a `:` suffix
  (`google/gemma-4-31b-it:free`) declared `self_hosted` is denied.
- **Only families Waymaker's model policy accepts may be permitted.**
  China-origin families are `chinese_routes_only` and stay
  `requires_legal_review`.
- **No invented clauses.** The notes paraphrase nearly every clause and quote
  only the NVIDIA trial clause verbatim, as the weightiest one. The policy
  therefore carries exactly one verbatim fragment, 11 words of NVIDIA trial
  §1.2, and the notes' paraphrase everywhere else. A test checks that every
  quote appears verbatim in the notes.
- **Two readings are stricter than the notes' wording, and say so.** Groq is
  `requires_legal_review`, because "a domain student does not compete" is
  INFERRED. MiniMax M3 is `requires_legal_review`, following the verifier's
  correction.
- **`legal_signoff.status` is `pending`.** Until a named reviewer approves,
  `gate_record` refuses every record, whatever its entry says.

`waymaker_ai/distillation/teacher_policy.py` provides:

- `load_policy` and `parse_policy`, which reject a malformed policy and list
  every problem;
- `is_permitted(provider, model, channel)`, which returns a decision with
  reasons and conditions;
- the `TeacherRecord` schema: teacher identity and weights revision, channel,
  serving host and terms, request date, prompt and evidence-pack hashes, the
  structured output, deterministic checks, WLIE claim results, human review and
  the permitted flag;
- `gate_record`, which refuses a record if any of these holds:
  - the policy (recomputed now, not trusted from the record) does not permit
    the teacher;
  - a policy condition is not acknowledged;
  - a self-hosted teacher has no pinned revision;
  - reasoning was requested, or the output carries reasoning keys or `<think>`
    markers;
  - the output is not exactly the task's label schema;
  - a deterministic check failed;
  - a legal conclusion is not WLIE `verified` and `human_verified`;
  - a critical label lacks a named human reviewer.

Teachers are never asked for chain-of-thought, and a teacher's conclusion is
only ever a candidate label.

## 9. Evaluation: prompt, schema and the runner

Arms A, B and C are scored with identical inputs and decoding, and training
uses the same request:

- **Prompt:** `waymaker_ai.evaluation.baselines.model.build_messages`, the
  runner's own. One system prompt serves both Artemis tasks; the user turn is
  the question, prefixed by `[UI-selected status code: …]` when the example
  carries a payload code. Labels, scenario notes and source bundles never
  reach the prompt.
- **Output schema:** `waymaker_ai.evaluation.predictions.model_output_schema`,
  sent as a strict `json_schema` response format. The SFT target is that
  object, with keys in the schema's order, because constrained decoders emit
  properties in schema order.
- **Decoding:** the runner's `DECODING` (temperature 0, seed 0,
  `max_tokens` 512).
- **Drift guard:** `sft_dataset.prompt_sha256()` hashes the messages (with and
  without a payload code), the schemas and the decoding. Template
  `artemis-sft/v1`, sha256 `f488fd1b…`, is recorded in every config. If the
  runner changes any of them, the configs stop loading until the SFT file is
  rebuilt and the adapter retrained. If the runner ever gives the two tasks
  different prompts or schemas, the builder refuses, because pairing two
  labels into one target would then be wrong.
- **Serving:** vLLM, or llama.cpp on a T4, on localhost, at the pinned
  revision, with the adapter. The runner's `openai_compatible` baseline calls
  it through `WAYMAKER_EVAL_MODEL_ENDPOINT` (loopback only) and
  `WAYMAKER_EVAL_MODEL_NAME`. Scoring uses the runner's metrics
  (`status_exact`, `subcode_exact`, `procedure_fine`, `procedure_coarse`,
  `not_status_token_respected`, `dates_exact`, plus flags such as
  `parent_fallback` and `parent_in_subcode_field`), as defined in
  [12](12-evaluation-methodology.md).
- **Contamination:** every SFT record repeats its question at the top level,
  so `runner --contamination-check <sft file>` hashes every scored question
  against the training file. Its `overlap_count` must be 0.

A consequence of the shared prompt is the two-labels-per-question rule in §5.
A runner that told the model which task it was answering, with a per-task
schema, would let single-task labels train; that is a change to the runner's
contract, recorded as a request, not made here.

## 10. Gates

Thresholds come from training-distill.md §4.7 and are proposals. The targets
D1 compares against are set in [12](12-evaluation-methodology.md), and this
document sets none of its own. A NO-GO ends an arm, and a threshold is never
relaxed to let an arm pass.

| Gate | Arms | Condition | Enforced by |
|---|---|---|---|
| G0-data | B, C | Train split exists; the validator passes; critical labels are `human_verified`; zero leakage pairs; the SFT file is a byte-identical fresh build | `preflight.py` → `train_qlora.py` refuses |
| G0-legal | C | Policy sign-off approved; every teacher permitted | `preflight.py`, `gate_record` |
| G0-eval-frozen | all | Hash manifest of the eval splits committed before the first scored run | runbook, runner manifest check |
| D1-need-for-a-model | all | §6 | the person running the experiment |
| G1-safety | all | The runner's flags `parent_fallback`, `parent_in_subcode_field` and `procedure_scope_mixed` occur 0 times on `test` and `adversarial_holdout` for every seed, and nothing is worse than the previous arm beyond its CI | runner report |
| G2-improvement | B, C | CI lower bound above 0 on the hypothesis metric | runner report |
| G4-format | all | 100% schema-valid under constrained decoding | runner report |
| G5-human-review | B, C | 200 stratified outputs, two reviewers, κ ≥ 0.6 (proposal), every disagreement adjudicated | people |
| G6-latency | all | p95 well inside the Quick Answer 7 s timeout | runner report |

## 11. Cost

All prices are from cost.md and were accessed on 2026-10-19. Hours and tokens
are INFERRED.

| Arm | Estimate | Basis |
|---|---|---|
| A | $0-2 | Inference only. $0 locally, on Colab Free or on Kaggle; 1-3 h of an L4 at RunPod Secure $0.59/h if a rental were ever authorised (cost.md §6) |
| B | $0-15 | 5.4-10.8M training tokens for 3 seeds. At 1,500-3,000 tokens/s on an A100-80GB that is 0.5-2 GPU-hours, about $0.9-3.6 at $1.79/h, plus 30-100% for failures and evaluation (cost.md §7). $0 on free GPUs; Colab Pro $9.99/month (cost.md §5) |
| C | $10-50 | B, plus a teacher pass on rented 80 GB GPUs: gpt-oss-120b on an H100 at $2.89-3.99/h and Gemma 4 31B on an A100-80GB at $1.79/h, 2-6 h each. No free tier offers 80 GB |

The dominant cost is human review of labels and counsel time for the policy,
not GPU time (cost.md §7). Paid runs are not authorised: every config sets
`cost.paid_runs_authorised: false` and `compute.paid_endpoint: false`.
`train_qlora.py --paid-endpoint` always refuses, and the cost acknowledgement
flag unlocks nothing.

## 12. Runbook summary

The full procedure is
[`training/README.md`](../../../experiments/waymaker-ai/training/README.md).
In short:

1. Confirm D1 and the G0 gates.
2. `build_sft_dataset.py --config …` (standard library; refuses the whole
   build on any problem).
3. `train_qlora.py --check-only`.
4. Install `requirements-train.txt`. Only `trl==1.16.0` is pinned from the
   notes; the other packages are `TODO(pin)`.
5. Smoke run on E2B: `--model secondary --max-steps 5`. It confirms the loader,
   the targets, the chat template and that no record is truncated. Then pin the
   versions the smoke run recorded.
6. Three seeds on E4B.
7. Serve with vLLM or llama.cpp on localhost, and score through the runner's
   `openai_compatible` baseline: dev for choices, test and adversarial_holdout
   once.
8. Commit the run records, reports, gate outcomes and the config status change
   by hand.

## 13. The old `experiments/waymaker-gemma4-finetune` scaffold

The old scaffold is not modified. Two things were kept:

- **Its principle.** It trains behaviour, never facts. Its placeholder-only
  evidence was the right instinct.
- **Its techniques.**
  - Loss on the assistant turn only. That becomes `completion_only_loss` on
    prompt-completion records here.
  - The ladder from a smoke test to a quality run. That becomes
    `--model secondary --max-steps`.
  - Gemma 4 E4B and 12B as targets.
  - Its `validate_dataset.py` and `eval_outputs.py` heuristics (overclaims,
    invented fees and periods, deferral). They do not fit Artemis, which writes
    no prose, but they are the natural starting point for an Athena experiment
    (knowledge-platform.md §4 "Reusable").

It is superseded for Artemis because of these defects (knowledge-platform.md
§4, models.md §0 and §9, training-distill.md §1):

1. **Eval rows merged into training.** `build_colab_dataset.py` merges train
   and eval by default and re-splits, which leaks eval items into training.
   Here, eval splits are never inputs to training, and a 3-gram guard refuses
   overlap.
2. **bf16 on a T4.** `bf16=True` and a bf16 compute dtype are hard-coded while
   the README recommends a free T4, which has no native bf16. Here the dtype is
   `auto` and resolves to fp16 on a T4.
3. **Unpinned dependencies.** `%pip install -q -U …`. Here, pins are enforced
   for real runs, and the smoke run records versions.
4. **Stale gating assumption.** The README and notebook treat Gemma 4 E4B and
   12B as gated and stop without `HF_TOKEN`. Gemma 4 is Apache-2.0 and
   ungated (models.md §0 item 2, VERIFIED). No token is used here, and models
   are pinned by revision SHA, which the scaffold never did.
5. **The eval set was never scored.** The 8 eval rows lack the fields
   `eval_outputs.py` expects, and the trainer runs no evaluation. Here,
   evaluation is the benchmark runner's job, on frozen splits.
6. **Its target format is not production's.** The 6-section answer exists
   nowhere in production, and Artemis targets the evaluation runner's 7-key
   label object.

## 14. Limitations

- **Nothing was executed with a GPU.** The TRL, PEFT, bitsandbytes and
  transformers calls follow the documentation the notes cite, including TRL
  v1.16.0, but are unverified. Throughput, VRAM and token counts are estimates.
- **The train split does not exist.** B-fixed does not exist. The runner's
  `openai_compatible` baseline exists, and the runbook's evaluation command was
  written from its source, but it has never been pointed at a served model.
- **Two labels per train question.** Because the runner shares one prompt and
  one schema between the Artemis tasks, the train split costs two reviewed
  examples per question (§5). The benchmark's eval splits are not affected.
- **The benchmark directory path is assumed** (`datasets/benchmark/v0`).
- **There is no Korean measurement of Gemma 4 anywhere.** Arm A would be the
  first.
- **The teacher policy is a reading of terms, not legal advice**, and sign-off
  is pending.
- **The arm C teacher harness is specified but not built**: serving, prompting
  and the ledger writer.
- **Only one model family is configured.** The Qwen question (does
  `CHINESE_ONLY_MODEL_PREFIXES` cover self-hosted weights?) is an owner
  decision (models.md Rec. 2). The smoke run uses E2B, so the old scaffold's
  Qwen smoke default is not needed.

## 15. Next decision

In order, each step only if the previous one says so:

1. **Build B-fixed** (§6) as an experiment-side baseline, and score B1, B2,
   B-fixed and arm A on `dev`. Arm A needs a local or free GPU.
2. **Apply D1.** If the rules meet the targets, close Artemis as "not needed"
   and spend the effort on retrieval and validators, as training-distill.md §5
   recommends.
3. **Only if D1 says to train:** write and review the train split (both
   Artemis labels for every question, §5), and run arm B on a local or free
   GPU.
4. **Only if arm C is wanted:** get counsel's sign-off on
   `teacher_policy.json`, and get the owner's authorisation for the rented
   80 GB teacher pass.

## 16. What was run in Mission 001

All runs were offline, from `experiments/waymaker-ai`, with the
`.venv-check` Python 3.11 interpreter and `PYTHONDONTWRITEBYTECODE=1`. No
package was installed, no model was downloaded and no network request was
made. Results as of 2026-10-20:

- `python -B -m pytest -q -p no:cacheprovider tests/test_teacher_policy.py`:
  69 passed.
- `python -B -m pytest -q -p no:cacheprovider tests/test_training_configs.py`:
  63 passed.
- `python -B -m pytest -q -p no:cacheprovider tests` (the whole experiment
  package, including sibling tasks' tests at that moment): 834 passed.
- `python -B training/build_sft_dataset.py --config configs/artemis/<arm>.json`
  for arms A, B and C: all three exit 1, as intended. Arm A has nothing to
  build, and the train files for B and C do not exist (EMPTY).
- `python -B training/train_qlora.py --config … --check-only`:
  - arm A exits 1 (untuned control);
  - arm B exits 1 (train file missing);
  - arm C exits 1 (sign-off pending, train file missing);
  - `--seed 1 --paid-endpoint rented-gpu --i-understand-this-may-cost-money`
    exits 1 with the paid refusal, and says the flag unlocks nothing.
- On a tiny synthetic train split in a temporary directory (tests):
  - the validator (run on the train file together with the benchmark), the
    builder and every preflight gate pass, and `--check-only` exits 0;
  - the record's prompt equals the runner's `build_messages`, its target
    parses under the runner's `parse_model_output` with no violation, and the
    runner's `contamination_check` finds a train question planted in `test`;
  - a question with one label, an unstated `needs_clarification`, two labels
    for one task, or a runner that splits its prompt per task each refuse the
    build;
  - one byte of drift in the SFT file makes `train_qlora.py` refuse;
  - the train script imports and refuses with torch, transformers, peft, trl,
    bitsandbytes, datasets and accelerate all blocked from import;
  - a real run (`--seed 1`, no `--max-steps`) stops at the environment check
    with exit 3, because the packages are not installed and pins are TODO, and
    it creates no run directory.
