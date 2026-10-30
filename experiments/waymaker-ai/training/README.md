# Waymaker Artemis training runbook

**Status: NOT RUN.** Nothing in this directory has been executed with a GPU.
The scripts were written on a machine with no GPU, no training packages and no
authorisation for paid compute (Mission 001, 2026-10-19). Every gate below was
tested offline (`tests/test_training_configs.py`); the TRL, PEFT and
bitsandbytes calls were not.

Design, hypotheses and the go/no-go rules are in
[`docs/ai/waymaker-genesis/13-artemis-experiment.md`](../../../docs/ai/waymaker-genesis/13-artemis-experiment.md).
This file is the step-by-step procedure. The current model policy and recovery limitations are in
[`artemis_foundation.json`](../configs/artemis_foundation.json) and the
[Gemma 4 adaptation plan](../artemis_bootstrap/WAYMAKER-ARTEMIS-FINETUNING-PLAN.md).
The older cost/time assumptions below are historical estimates; use the dated
prices and validation gates in that plan before scheduling any job.

| File | What it does | Needs |
|---|---|---|
| `build_sft_dataset.py` | Validated benchmark-format train examples → chat-format JSONL, one record per question. The prompt is the evaluation runner's own `openai_compatible` request and the assistant turn is its 7-key JSON object | Python 3 (tested on 3.11), standard library |
| `train_qlora.py` | QLoRA SFT (TRL `SFTTrainer` + PEFT + bitsandbytes NF4). Refuses unless every gate passes | `--check-only`: standard library. Training: a CUDA GPU and `requirements-train.txt` |
| `requirements-train.txt` | Pins. `trl==1.16.0` is pinned from the notes; the rest are `TODO(pin)` until a smoke run records them | — |

Run every command from `experiments/waymaker-ai/`.

---

## 0. Before anything: the run must be allowed

Do not start until all of these are true. `train_qlora.py` checks the ones that
code can check, and you check the rest.

1. **D1 holds.** Arm A and the cheap-rule-fix baseline (B-fixed) were scored on
   `dev`, and B-fixed is below the target in `12-evaluation-methodology.md` on
   text-only `subcode_exact` or `procedure_fine`. If the rules already meet the
   target, stop here: Artemis is not trained (13 §6).
2. **A train split exists.** Benchmark v0 has only `dev`, `test` and
   `adversarial_holdout`. The config records `dataset.train.status: "EMPTY"`.
   A train split has to be written as benchmark-format examples with
   `split: "train"`, split by case template, and reviewed. Every critical label
   needs `human_verified` with a named reviewer (11-dataset-governance.md).
   **Every train question needs two examples**: a
   `status_procedure_classification` example and an `entity_date_extraction`
   example with the same exact question text and payload code. The
   classification label must state `current_status`, `target_status` (null is
   fine) and `needs_clarification` (true or false). The reason: the runner asks
   the model one prompt and one 7-key schema for both tasks, so one question has
   one target, and the builder never guesses a key that no label states.
3. **Evaluation splits are frozen.** A committed hash manifest of `dev`, `test`
   and `adversarial_holdout` exists before the first scored run.
4. **No paid compute.** Use a local GPU, free Colab or Kaggle. A rented GPU or a
   managed fine-tuning API (Together, Fireworks) needs the owner's explicit
   authorisation. Even then `train_qlora.py` refuses it, so the config and this
   runbook would have to change first, in a reviewed commit.
5. **Arm C only:** `configs/teacher_policy.json` has `legal_signoff.status:
   "approved"` with a named reviewer. Every teacher record has passed the gate.
   That pass includes human review: 100% of critical items and at least 10% of
   the rest.

## 1. Choose a machine

| Machine | GPU | Model | dtype | Notes |
|---|---|---|---|---|
| Local workstation | any CUDA GPU with 16-24 GB (L4, RTX 4090, A5000) | E4B, including its smoke run | `auto` → bf16 on Ampere and later | Preferred: nothing leaves the machine |
| Colab Pro ($9.99/month, cost.md §5) | L4 or A100 | E4B | bf16 | Only if a free option is not enough. Needs the owner's OK, because it is a paid plan |
| Colab Free | T4 16 GB, not guaranteed | E4B may run out of memory; stop or choose larger hardware | `auto` → **fp16**: a T4 has no native bf16 | Sessions can end without warning; keep `--max-steps` runs short |
| Kaggle | T4 (or P100), about 30 GPU-hours a week (cost.md §5, UNVERIFIED) | E4B fit unverified | fp16 | bitsandbytes 4-bit on a P100 was not checked; use the T4 |

E2B requires explicit development selection and separate metrics; it never
replaces E4B for smoke validation or serving.

The configs leave `compute_dtype` as `auto`. Never hard-code bf16. That was
defect 3 of the old scaffold (knowledge-platform.md §4).

Gemma 4 E4B and E2B are Apache-2.0 and **not gated** (models.md §0 item 2).
No Hugging Face token is needed, and the scripts never read or print one. Do not
paste a token into a notebook. Leave `HF_TOKEN` unset, because the Hugging Face
libraries would pick it up from the environment on their own.

## 2. Get the code and check the gates (any machine, no GPU)

If the repository is private, do not put a token in a notebook. Upload a zip
that keeps the repository layout and holds `experiments/waymaker-ai/`,
`visa_data.json` and `data/manual_approval_index.json`. The dataset validator
reads the last two from the repository root.

```bash
git clone https://github.com/club-paradiso/Visable.git
cd Visable/experiments/waymaker-ai

# The train split must already exist (step 0.2). Build the SFT file from it:
python training/build_sft_dataset.py --config configs/artemis/exp_b_sft_qlora.json

# Every gate, without importing torch:
python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --check-only
```

Today both commands exit 1 with
`train examples file datasets/benchmark/v0/train.jsonl does not exist (... EMPTY ...)`.
That is the correct answer.

`build_sft_dataset.py` refuses the **whole** build if any example fails a check.
Read every line it prints. The fix is always in the data:

- re-split by case template if a train question overlaps an eval question;
- get a reviewer if a critical label is not `human_verified`;
- remove reasoning text from a teacher record.

The threshold is never the fix.

## 3. Install (GPU machine only)

```bash
pip install -r training/requirements-train.txt   # installs trl==1.16.0
pip install transformers peft bitsandbytes accelerate datasets   # the TODO(pin) packages; see below
```

On Colab and Kaggle, torch is preinstalled with the right CUDA build. Do not
reinstall it. Its version is recorded, not pinned.

`transformers` must be a v5.x release for Gemma 4 (models.md §3b). If pip
resolves an older one, install `"transformers>=5,<6"` explicitly.

## 4. Smoke run (E4B, five steps; E2B only by explicit selection)

```bash
python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json \
  --model primary --seed 1 --max-steps 5
```

The smoke run is allowed with `TODO(pin)` packages. It checks the things the
notes left UNVERIFIED (models.md §8):

- `AutoModelForImageTextToText` loads the `Gemma4ForConditionalGeneration` checkpoint
  text-only. If it does not, change `loader` in the config, which counts as a
  config change;
- all seven LoRA target names exist in the language model. Vision and audio
  tower matches are excluded and listed;
- the chat template accepts a `system` turn;
- no record exceeds `max_seq_length` 2048. The script refuses rather than
  truncate;
- the adapter saves.

Then pin. Copy the versions from
`training/runs/artemis-exp-b-sft-qlora/smoke-primary-seed1/run_record.json` →
`packages` into `requirements-train.txt`. Replace each `# TODO(pin): name ...`
line with `name==version`. Commit that change before the real run, because a
real run refuses while any TODO pin remains or any installed version differs.

A smoke adapter is never evaluated. Its `run_record.json` says `"evaluate": false`.

## 5. Real runs (three seeds)

```bash
for seed in 1 2 3; do
  python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --seed "$seed" || break
done
```

Each run writes `training/runs/<config id>/primary-seed<k>/adapter/` and
`run_record.json`. The record holds:

- the config sha256 and the SFT file sha256;
- the base revision and the package versions;
- the GPU and the dtype;
- the trainable parameter count;
- the wall-clock time and the loss history.

A run directory that already holds a result is never overwritten.

Arm C uses the same commands with `configs/artemis/exp_c_verified_distill_sft.json`,
after step 0.5.

**Expected time (INFERRED; the smoke run measures the real numbers).** Per seed:

- 1,500-3,000 examples × about 600 tokens × 2 epochs = 1.8-3.6M training tokens;
- at the 1,500-3,000 tokens/s that cost.md §7 assumes for an 8B-class QLoRA on
  one A100-80GB, that is about 10-40 minutes;
- an L4 is probably 2-4× slower;
- a T4 with E2B is slower still.

**Expected cost:**

- $0 on a local GPU, Colab Free or Kaggle;
- $9.99 if Colab Pro is needed (cost.md §5);
- at RunPod Secure A100-80GB $1.79/h, three seeds would be about $1-4 plus
  30-100% overhead (cost.md §6-7). That is a paid run and is not authorised.

## 6. Serve the adapter locally

Serve the base at the **pinned revision** plus the adapter. Bind to localhost
only.

**vLLM** (L4/A100), OpenAI-compatible:

```bash
vllm serve google/gemma-4-E4B-it \
  --revision ee0ef6023621cff504d758262d4e04895a5af4a2 \
  --enable-lora --max-lora-rank 16 \
  --lora-modules artemis-b-primary-seed1=training/runs/artemis-exp-b-sft-qlora/primary-seed1/adapter \
  --host 127.0.0.1 --port 8000
```

**llama.cpp** (T4-only setups). Convert the base and the adapter to GGUF with
llama.cpp's `convert_hf_to_gguf.py` and `convert_lora_to_gguf.py`, then:

```bash
llama-server -m gemma-4-E4B-it.gguf --lora artemis-adapter.gguf --jinja --host 127.0.0.1 --port 8000
```

Neither path was run. LoRA conversion for Gemma 4 is UNVERIFIED.

## 7. Evaluate with the runner (openai_compatible baseline)

Arms A, B and C are scored with exactly the request the adapter was trained
on, because the SFT builder imports it from the runner:

1. messages: `waymaker_ai.evaluation.baselines.model.build_messages` (one
   system prompt for both Artemis tasks; the user turn is the question,
   prefixed by `[UI-selected status code: …]` when a payload code is set);
2. schema: `waymaker_ai.evaluation.predictions.model_output_schema(task)`,
   sent as a strict `json_schema` `response_format`;
3. decoding: `model.DECODING` = temperature 0, seed 0, `max_tokens` 512.

Their combined hash is `prompt.sha256` in every config
(`sft_dataset.prompt_sha256()`, template `artemis-sft/v1`). If the runner
changes any of the three, the configs stop loading until someone rebuilds the
SFT file and retrains: an adapter is never scored on a request it was not
trained on.

The `openai_compatible` baseline reads its endpoint from the environment and
accepts only a loopback address. It reads no API key:

```bash
export WAYMAKER_EVAL_MODEL_ENDPOINT=http://127.0.0.1:8000/v1   # the runner POSTs to <endpoint>/chat/completions
export WAYMAKER_EVAL_MODEL_NAME=artemis-b-primary-seed1        # the --lora-modules name, or the base repo id for arm A

python -m waymaker_ai.evaluation.runner \
  --benchmark datasets/benchmark/v0 \
  --baselines openai_compatible,b1_python,b2_js \
  --tasks status_procedure_classification,entity_date_extraction \
  --splits dev \
  --contamination-check datasets/sft/artemis-v0/train.sft.jsonl \
  --out reports/artemis/exp_b/primary-seed1-dev.json \
  --markdown reports/artemis/exp_b/primary-seed1-dev.md
```

- `--contamination-check` makes the runner hash every scored question against
  the SFT file's `question` field. Its `overlap_count` must be 0; the builder's
  word 3-gram guard should already have made it so.
- Use `dev` only to choose epochs and checkpoints. Score `test` and
  `adversarial_holdout` **once per seed** (`--splits test,adversarial_holdout`),
  after the benchmark manifest is frozen. The report's `benchmark.digest` names
  the exact bytes scored.
- Score arm A, the untuned control, the same way: serve the base without
  `--lora-modules` and set `WAYMAKER_EVAL_MODEL_NAME=google/gemma-4-E4B-it`.
- Do not point the endpoint anywhere but the local server. The runner refuses
  a non-loopback host, and a hosted API would be a different experiment with
  different terms that may cost money.
- Run `python -m waymaker_ai.evaluation.runner --help` first. The flags above
  were read from the runner's source on 2026-10-19; it is a sibling task's
  code and may change.

## 8. What to record

Commit the following with the results. Leave the adapters out of git; they go
to private storage. `training/.gitignore` already excludes `adapter/` and
`trainer/` under `training/runs/`:

- each `run_record.json`, and each runner report (`reports/artemis/...`);
- the serving stack used for scoring: vLLM or llama.cpp version, the exact
  serve command, and the `prompt.sha256` the configs carried;
- the benchmark manifest hash that was scored, and the SFT file sha256;
- the GPU, the wall-clock time and the actual cost, even when it is $0;
- every gate in the config, each marked PASS or NO-GO with the measured value.
  A NO-GO ends the arm, and thresholds are never relaxed;
- the human-review sample (G5): who reviewed it, the agreement and the
  adjudications;
- the config `status`, changed by hand from `NOT RUN` to `COMPLETED` or
  `ABANDONED` in the same commit, with `status_detail` saying why.

Never commit a token, a user question or any personal data. The train split is
synthetic or scrubbed benchmark data only.
