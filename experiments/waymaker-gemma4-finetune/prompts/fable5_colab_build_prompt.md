# Build prompt — Waymaker × Gemma 4 fine-tuning experiment

This is the specification used to generate `experiments/waymaker-gemma4-finetune/`.
Reuse it (with Claude Code or another agent) to regenerate or extend the experiment.
Any regeneration must preserve every constraint below.

---

## Task

Create a minimal, safe, reproducible Google Colab fine-tuning experiment for
Waymaker by Paradiso using Gemma 4 models.

## Hard constraints

- Do not modify production app behavior.
- Do not wire this into the live Waymaker backend. Experimental only.
- Create files under `experiments/waymaker-gemma4-finetune/` only.
- Do not include real legal claims unless they come from supplied evidence excerpts.
- Do not train the model to memorize visa rules, fees, periods, eligibility
  requirements, or document lists.
- Fine-tuning is for behavior and output formatting only:
  - answer only from `evidence_pack`
  - refuse or defer when evidence is insufficient
  - avoid inventing fees, periods, documents, or eligibility rules
  - produce a consistent Korean guidance structure
  - preserve source grounding
- Do not train on hidden chain-of-thought; train only on final visible assistant
  answers.

## Model strategy (two stages)

- **Stage 1 — `google/gemma-4-E4B-it`, smoke test only:** verify dataset format,
  chat template, LoRA/QLoRA training code, adapter save/load, inference cells, and
  the evaluation script.
- **Stage 2 — `google/gemma-4-12B-it`, actual quality experiment:** evaluate
  Waymaker-style answer quality, evidence-grounded Korean immigration guidance
  behavior, hallucination risk, and refusal behavior.

## Platform

Google Colab, single GPU, parameter-efficient fine-tuning only (LoRA or QLoRA).
No full fine-tuning.

## Notebook requirements

1. Designed for Google Colab; installs required packages.
2. Hugging Face auth via Colab secrets or the `HF_TOKEN` environment variable.
3. Switchable between `google/gemma-4-E4B-it` (default) and
   `google/gemma-4-12B-it`, with a clearly marked Stage 2 switch cell.
4. Conservative defaults: `max_seq_length=1024`, `per_device_train_batch_size=1`,
   `gradient_accumulation_steps=4–8`, LoRA rank 8, alpha 16, 1 epoch, small sample
   dataset first.
5. OOM troubleshooting notes: reduce max_seq_length; keep batch size 1; reduce grad
   accumulation if needed; E4B before 12B; Colab Pro L4/A100 for 12B.
6. Save the LoRA adapter to Google Drive and optionally to the Hugging Face Hub.
7. Inference cell testing four behaviors: sufficient-evidence answer,
   insufficient-evidence refusal/defer, dangerous overclaim bait, and a request for
   exact fees/periods not present in the evidence.

## Dataset format

JSONL; each line has a `messages` array (`system`, `user`, `assistant`). The user
message contains the `user_question` plus an `evidence_pack` with source title,
source date (if available), source excerpt, and status code (if applicable). The
assistant output uses this Korean structure:

```
1. 요약
2. 근거에서 확인되는 내용
3. 아직 확인이 필요한 내용
4. 주의할 점
5. 다음 단계
6. 사용한 근거
```

## Sample data

Placeholder-only, clearly marked as placeholders; no invented legal facts. Topics:
D-2 time-limited work permission, F-4 overseas Korean route, E-7 workplace change,
insufficient evidence, overstay / unauthorized work risk, exact-fee request without
evidence.

## Scripts

- `scripts/validate_dataset.py` — load JSONL; validate messages structure; require
  system/user/assistant roles; reject empty `evidence_pack`; warn on unsupported
  absolute claims ("무조건 가능합니다", "반드시 허가됩니다", exact fees/periods
  without evidence); print summary stats.
- `scripts/build_colab_dataset.py` — turn real Waymaker exports into Colab-ready
  train/eval JSONL (validate, dedupe, shuffle with fixed seed, split).
- `scripts/eval_outputs.py` — score model-output JSONL for evidence citation
  presence, refusal/defer when evidence is insufficient, overclaim phrases, and
  exact fee/period/document claims; print a simple score report.

## README

Must explain: experiment purpose; why E4B is only a smoke test; why 12B is the
actual quality test; why the model must not memorize legal rules; how to run the
notebook; how to replace samples with real Waymaker evidence_pack examples; how to
interpret results; and a clear warning that this is not production-ready.

## Google Colab Free constraints (addendum)

The experiment must run an end-to-end smoke test on **Google Colab Free (T4 16 GB)**.
Any regeneration must preserve these in addition to everything above:

- **GPU + memory check cell first:** report the assigned GPU, total/free memory, and a
  recommended preset. If no GPU is assigned, print explicit fallback steps (Runtime →
  Change runtime type → T4 GPU → Save → Restart). Guard the model-load/train cells so
  they stop with a clear message when no CUDA GPU is present.
- **Ultra-low-memory smoke mode (default ON):** `max_seq_length` 512 (or 768), batch
  size 1, gradient accumulation 4, `max_steps` 30–50. A toggle restores the longer
  config for bigger GPUs.
- **Model preset selector.** Keep the Gemma 4 E4B path (`gemma-e4b`) but document that
  it **may still OOM** on free Colab. Add small **open Qwen** presets as the reliable
  free-tier default — `Qwen/Qwen3-0.6B` and `Qwen/Qwen3-1.7B` first, `Qwen/Qwen3-4B`
  only if GPU memory allows. Qwen presets need no HF token; make HF auth non-fatal and
  enforce a token only for the gated Gemma presets.
- Keep `gemma-12b` as the Colab Pro (L4/A100) quality run. Smoke-test presets are not a
  quality signal. Still no real legal facts in any placeholder; still not wired into the
  production Waymaker backend.
