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

## Two-stage model strategy

| Stage | Model | Role |
|---|---|---|
| 1 | `google/gemma-4-E4B-it` | **Smoke test only.** Small enough to run cheaply on a free Colab T4. Verifies the dataset format, chat template, LoRA/QLoRA training code, adapter save/load, inference cells, and the eval script. Its answer quality is **not** a signal. |
| 2 | `google/gemma-4-12B-it` | **The actual quality experiment.** Evaluates Waymaker-style answer quality, evidence-grounded Korean immigration guidance behavior, hallucination risk, and refusal behavior. Needs a Colab Pro L4/A100. |

Never skip Stage 1: every wiring bug found on E4B is a wasted (and expensive) 12B run
avoided.

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

1. Open `notebooks/waymaker_gemma4_lora_colab.ipynb` in Google Colab
   (upload it, or open from GitHub). Select a **GPU runtime**.
2. Add a Colab secret named `HF_TOKEN` (a Hugging Face token whose account has
   accepted the Gemma license on both model pages).
3. Run the cells top to bottom with the default `google/gemma-4-E4B-it`. Upload
   `dataset/train.sample.jsonl`, `dataset/eval.sample.jsonl`, and
   `scripts/eval_outputs.py` when prompted.
4. Confirm the smoke test: training completes, the adapter saves to Google Drive,
   the four inference behavior tests produce output, and the eval report prints.
5. In the clearly marked **STAGE 2 SWITCH** cell, uncomment
   `MODEL_ID = "google/gemma-4-12B-it"`, switch to an L4/A100 runtime, and rerun
   from the model-loading cell down.

## Replacing the samples with real Waymaker data

1. Export real evidence_pack examples in the same `messages` JSONL format. Excerpts
   must come from reviewed Waymaker sources — never write legal content by hand.
2. Build the split: `python scripts/build_colab_dataset.py --input <your>.jsonl --outdir dataset/build`
3. Validate: `python scripts/validate_dataset.py dataset/build/train.jsonl dataset/build/eval.jsonl`
   — fix every error and review every warning before training.
4. Point the notebook's `TRAIN_PATH` / `EVAL_PATH` at the new files (Drive or upload).

## Interpreting results

- **Stage 1 (E4B):** pass/fail on wiring only. Ignore answer quality entirely.
- **Stage 2 (12B):** run `scripts/eval_outputs.py` on generated outputs and look at:
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
- `gemma-4-E4B-it` / `gemma-4-12B-it` are gated models; loading may require a recent
  `transformers` release.
- Nothing in this directory is imported by the Paradiso app or backend.
