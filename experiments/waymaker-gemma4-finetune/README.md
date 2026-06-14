# Waymaker × Gemma 4 — LoRA/QLoRA fine-tuning experiment

> **⚠️ Experimental only. Not production-ready. Not wired into the live Waymaker
> backend, and it must not be until it has passed manual review.**

## Purpose

A minimal, reproducible Google Colab experiment that fine-tunes Gemma 4 instruction
models for **Waymaker answer behavior and output formatting only**:

- answer **only** from the `evidence_pack` supplied in the user message
- refuse or defer when the evidence is insufficient
- never invent fees, periods, document lists, or eligibility rules
- produce a consistent 6-section Korean guidance structure
  (`1. 요약 / 2. 근거에서 확인되는 내용 / 3. 아직 확인이 필요한 내용 / 4. 주의할 점 / 5. 다음 단계 / 6. 사용한 근거`)
- preserve source grounding (cite the sources used)

### Why the model must NOT memorize legal rules

Visa rules, fees, periods, eligibility requirements, and document lists change.
A model that memorizes them will confidently repeat stale or wrong rules — the exact
failure mode Waymaker exists to prevent. The correct architecture is: facts live in
the `evidence_pack` (retrieved at answer time from curated sources), and the model is
trained only on *how to behave* with that evidence. Accordingly, every excerpt in the
sample dataset is a **clearly marked fake placeholder** — there are no real legal
facts to memorize, by design. Do not replace placeholders with real legal text unless
it comes from supplied, reviewed evidence excerpts.

## Model strategy: smoke test → quality run

The notebook has a **model preset selector** (in the config cell). Everything except
`gemma-12b` is a **wiring smoke test** — it proves the dataset format, chat template,
LoRA/QLoRA code, adapter save/load, inference cells, and eval script work. Answer
quality on the small models is **not** a signal.

| Preset | Model | Free Colab T4 | HF token | Role |
|---|---|---|---|---|
| `qwen-0.6b` | `Qwen/Qwen3-0.6B` | ✅ safest | not needed | smallest smoke test |
| `qwen-1.7b` *(default)* | `Qwen/Qwen3-1.7B` | ✅ good default | not needed | smoke test |
| `qwen-4b` | `Qwen/Qwen3-4B` | ⚠️ only if GPU has spare memory | not needed | larger smoke test |
| `gemma-e4b` | `google/gemma-4-E4B-it` | ⚠️ **may still OOM** | **required (gated)** | original Gemma smoke path |
| `gemma-12b` | `google/gemma-4-12B-it` | ❌ Colab Pro L4/A100 | **required (gated)** | **actual quality experiment** |

Never skip the smoke test: every wiring bug found on a small/cheap model is a wasted
(and expensive) `gemma-12b` run avoided. The original Gemma 4 E4B path is preserved
(`MODEL_CHOICE = "gemma-e4b"`), but on **free Colab it may still OOM** even in 4-bit —
the open Qwen presets are the reliable free-tier choice and need no Hugging Face token
or license acceptance.

## Running on Google Colab Free (T4)

The notebook is set up to pass an end-to-end **smoke test on a free Colab T4**:

1. Open `notebooks/waymaker_gemma4_lora_colab.ipynb` in Colab. **Runtime → Change
   runtime type → T4 GPU → Save.**
2. Run the **GPU + memory check** cell first. It reports the assigned GPU and free
   memory, recommends a preset, and — if **no GPU** is assigned — prints the exact
   fallback steps (change runtime type → restart → rerun). The model-load and train
   cells are guarded and will stop with a clear message if there is no GPU.
3. Leave the defaults: `MODEL_CHOICE = "qwen-1.7b"` and `ULTRA_LOW_MEM = True`
   (`max_seq_length 512`, batch 1, grad accum 4, `max_steps 30`). No `HF_TOKEN` is
   required for the Qwen presets.
4. Run the cells top to bottom. Upload `dataset/train.sample.jsonl`,
   `dataset/eval.sample.jsonl`, and `scripts/eval_outputs.py` when prompted (or set the
   paths to a Drive copy).
5. A green smoke test = training runs the capped steps, the adapter saves locally
   (`SAVE_TO_DRIVE = False` by default), the four inference behavior tests print output,
   and the eval report prints. **Ignore answer quality** on the smoke-test models.

If a preset OOMs, step down (`qwen-1.7b` → `qwen-0.6b`), keep `ULTRA_LOW_MEM = True`,
and **Runtime → Restart session** before retrying. `gemma-e4b` may OOM on a T4; that is
expected, not a bug — switch to a Qwen preset.

For the **actual quality experiment**, set `MODEL_CHOICE = "gemma-12b"`,
`ULTRA_LOW_MEM = False`, switch to a **Colab Pro L4/A100** runtime, add an `HF_TOKEN`
secret (with the Gemma license accepted), and rerun.

## Layout

```
experiments/waymaker-gemma4-finetune/
├── README.md
├── dataset/
│   ├── train.sample.jsonl      # 6 placeholder examples (D-2 시간제취업, F-4, E-7 근무처 변경,
│   │                           #   insufficient evidence, overstay risk, exact-fee request)
│   └── eval.sample.jsonl       # 4 placeholder examples (incl. overclaim bait, exact-period request)
├── scripts/
│   ├── validate_dataset.py     # structural + overclaim/fee/period checks on JSONL
│   ├── build_colab_dataset.py  # dedupe/shuffle/split real exports into Colab-ready JSONL
│   └── eval_outputs.py         # scores model outputs (citation, structure, defer, overclaims)
├── notebooks/
│   └── waymaker_gemma4_lora_colab.ipynb
└── prompts/
    └── fable5_colab_build_prompt.md   # the build spec used to (re)generate this experiment
```

## Dataset format

JSONL; each line is one example with a `messages` array of exactly
`system` / `user` / `assistant` (final visible answers only — never hidden
chain-of-thought). The user message contains the question and the evidence:

```
[질문]
<user_question>

[evidence_pack]
- source_title: <title>
  source_date: <YYYY-MM-DD, if available>
  status_code: <e.g. D-2, if applicable>
  excerpt: <source excerpt>
```

The assistant answer must follow the 6-section Korean structure above and end with a
non-legal-advice disclaimer.

## How to run

See **Running on Google Colab Free (T4)** above for the step-by-step smoke test. In
short: select a T4 GPU runtime, run the GPU check cell, keep the `qwen-1.7b` /
`ULTRA_LOW_MEM` defaults (no token needed), and run top to bottom. To switch models,
change `MODEL_CHOICE` in the config cell (or uncomment a line in the optional override
cell) and rerun from there down — set `gemma-12b` only on a Colab Pro L4/A100 with an
`HF_TOKEN` secret.

## Replacing the samples with real Waymaker data

1. Export real evidence_pack examples in the same `messages` JSONL format. Excerpts
   must come from reviewed Waymaker sources — never write legal content by hand.
2. Build the split: `python scripts/build_colab_dataset.py --input <your>.jsonl --outdir dataset/build`
3. Validate: `python scripts/validate_dataset.py dataset/build/train.jsonl dataset/build/eval.jsonl`
   — fix every error and review every warning before training.
4. Point the notebook's `TRAIN_PATH` / `EVAL_PATH` at the new files (Drive or upload).

## Interpreting results

- **Smoke test (qwen-\* / gemma-e4b):** pass/fail on wiring only. Ignore answer quality
  entirely.
- **Quality run (gemma-12b on Colab Pro):** run `scripts/eval_outputs.py` on generated
  outputs and look at:
  - `citation` / `structure` — does every answer keep the 6-section grounded format?
  - `defer_ok` — does the model defer on the insufficient-evidence cases?
  - `no_overclaim` — no "무조건 가능 / 반드시 허가"-style absolutes, even when baited?
  - `no_invented_fee_period` / `no_invented_doc_list` — no numbers or document lists
    that aren't in the evidence?
- These are **heuristic string checks**, not legal review. Read the outputs manually.
  A high score means the *format and refusal behavior* look right — it does not mean
  the answers are legally correct, and nothing here claims legal correctness.

## Limitations

- Sample dataset is tiny and placeholder-only — sufficient for wiring tests, not for
  drawing quality conclusions.
- `gemma-4-E4B-it` / `gemma-4-12B-it` are gated and need a recent `transformers`
  release and an accepted Gemma license. On a free Colab T4, `gemma-e4b` **may still
  OOM** even in 4-bit; the open `Qwen/Qwen3-*` presets are the reliable free-tier path.
- The `qwen-*` presets are smoke-test stand-ins only — they verify the pipeline, not
  Waymaker answer quality. Qwen3 may emit a `<think>` reasoning preamble at inference;
  that is cosmetic for the wiring test.
- Nothing in this directory is imported by the Paradiso app or backend.
