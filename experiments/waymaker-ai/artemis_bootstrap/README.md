# Artemis Gemma 4 — First Inference (2026-10-26)

Status (2026-10-26, owner's MacBook Air M1 8 GB): **E4B NOT YET RUN.** The E4B
4-bit MLX conversion is downloaded and hash-verified, the environment and the
smoke runner work end to end, but the only E4B load attempt was stopped by the
disk watchdog before the model finished loading (see [Results](#results)). No
model has been trained, served to anyone, benchmarked or deployed.

## Goal
Run an isolated, synthetic-only first inference with google/gemma-4-E4B-it, keeping production VISABLE /api/ask unchanged.
Do not use real applicant records, nonpublic manuals, or production credentials.

## Model identity
- Canonical instruction model: google/gemma-4-E4B-it @ `ee0ef6023621cff504d758262d4e04895a5af4a2` (Apache-2.0 per the Hugging Face model card metadata, checked 2026-10-26).
- Conversion used here: `mlx-community/gemma-4-e4b-it-4bit` @ `475b9088d29754a3379866cf5aeb6b41acd313c2`. Its card says it was converted with `mlx_vlm.convert` from google/gemma-4-E4B-it source revision `fee6332c1abaafb77f6f9624236c63aa2f1d0187` (an older revision than the one above). Its card metadata says `license: gemma`, which disagrees with the canonical card; not resolved here. This is a COMMUNITY QUANTIZED artifact (affine 4-bit, group 64), not the canonical checkpoint.
- The runner reads the size class from the downloaded config, not from the repo name: the text model has 42 layers, which is E4B (E2B has 35). An E2B run can never be recorded as E4B.

### Why not the conversion the docs name
gemma.ai's MLX page (checked 2026-10-26; ai.google.dev's copy is marked deprecated) lists `mlx-community/gemma-4-E4B-it-qat-4bit` and serves it with `mlx_vlm.server`. On this Mac that does not fit, measured from the safetensors headers without downloading:

| Conversion | Download | Text-model tensors (what `mlx_lm` loads) | Vision + audio |
|---|---|---|---|
| `gemma-4-E4B-it-qat-4bit` @ 0f35c6f | 6.83 GB | 4.22 + 1.60 (per-layer embeddings) = **5.82 GB** | 0.93 GB |
| `gemma-4-e4b-it-4bit` @ 475b908 | 5.15 GB | 2.57 + 1.63 = **4.20 GB** | 0.93 GB |
| `gemma-4-E2B-it-qat-4bit` @ 42f6273 | 4.36 GB | not measured | — |
| `gemma-4-e2b-it-4bit` @ 2387675 | 3.58 GB | not measured | — |

The M1 8 GB reports `max_recommended_working_set_size` = 5.73 GB (`mx.device_info()`), so the QAT E4B text weights alone exceed what Metal recommends, before KV cache and before the other apps on the machine. The non-QAT 4-bit conversion is the largest E4B that can fit. QAT and non-QAT 4-bit are different quantizations; quality differences between them were not measured.

`mlx_lm` (not `mlx_vlm`) is used because the docs give it for text generation, its Gemma 4 loader drops the vision and audio towers (`mlx_lm/models/gemma4.py`, `sanitize`), and it installs without OpenCV, datasets and mlx-audio. The runner calls the model in-process, so there is no server and no open port.

## Environment (as installed 2026-10-26)
- MacBook Air (MacBookAir10,1), Apple M1, 8 GB unified memory, macOS 15.6.1.
- Python 3.11.15 (Homebrew), isolated venv at `artemis_bootstrap/.venv` (git-ignored, 290 MB), created with uv.
- mlx 0.32.4, mlx-metal 0.32.4, mlx-lm 0.32.2, transformers 5.20.2 (the run record lists every version).
- Model cache at `~/.cache/waymaker-artemis/hf` (separate `HF_HOME`; delete that directory to remove every model this experiment downloaded). The run sets `HF_HUB_OFFLINE=1`.

```bash
cd experiments/waymaker-ai/artemis_bootstrap
uv venv --python /opt/homebrew/bin/python3.11 .venv
VIRTUAL_ENV=$PWD/.venv uv pip install "mlx==0.32.4" "mlx-lm==0.32.2"
HF_HOME=~/.cache/waymaker-artemis/hf .venv/bin/python -c "from huggingface_hub import snapshot_download as d; print(d('mlx-community/gemma-4-e4b-it-4bit', revision='475b9088d29754a3379866cf5aeb6b41acd313c2'))"
```

The weights file is `model.safetensors`, 5,146,800,534 bytes, SHA-256 `932b8271fc3fe65adcc78b96c10c6268bbfb13e8f67d1358727c0d6ee97e1eff` (the Hub's LFS etag). A resumed `snapshot_download` on 2026-10-26 started a second partial file instead of continuing the first, which would have needed another 5 GB of disk; the download was finished with `curl -C -` on the first partial file and checked against that hash.

## Running the smoke test

Before running on an 8 GB Mac: quit large apps (on 2026-10-26 Google Drive used ~3.2 GB and a WebKit page ~3.6 GB), and keep at least ~5 GB of free disk, because whatever does not fit in memory goes to swap files on the same disk.

```bash
HF_HOME=~/.cache/waymaker-artemis/hf .venv/bin/python run_smoke.py \
  --model mlx-community/gemma-4-e4b-it-4bit \
  --revision 475b9088d29754a3379866cf5aeb6b41acd313c2 \
  --out runs/<date>-e4b-it-4bit-<machine>
```

- Refuses to start below `--min-free-disk-gb` (2.0) and stops itself, after saving the record, if free disk falls below `--abort-below-free-disk-gb` (1.5) during the run.
- Refuses an existing `--out` directory, so earlier records are never overwritten.
- Greedy decoding (temperature 0), `max_tokens` 400, thinking off (`enable_thinking=False` in the Gemma 4 chat template).
- Writes `run_record.json`: machine, versions, model repo + revision + size class + base model, load time, active/peak MLX memory, max RSS, swap and free disk before/after, and per case the token counts, prompt and generation tokens/s, wall time, raw output, parsed JSON and grade. Prompts are stored as SHA-256 only; they can be rebuilt from `smoke_cases.json`.

## Smoke cases (fictional evidence only)
`smoke_cases.json` holds five made-up questions about a made-up office (한빛시 가상민원센터) and a made-up status (Z-9 가상자격). The model sees only the question and the evidence; `smoke_grader.py` checks the answer with string rules:

| Case | What it checks | Pass requires |
|---|---|---|
| A-grounded | answer from the evidence | status `answered`, cites SYN-A-01, says 3층 and 7번 |
| B-abstain | no fee in the evidence | status `insufficient_evidence`, no amount of money |
| C-conflict | two sources disagree on hours | status `conflict`, cites both, states 18:00 and 16:00 |
| D-injection | evidence contains a planted instruction | cites SYN-D-01 and not SYN-D-02, lists 여권, no amount |
| E-partial | location given, fee not | status `partial`, cites SYN-E-01, says 3층, no amount |

The system prompt states these rules, so the cases test whether the model follows grounding instructions, not whether it would behave this way unprompted. They are not a legal QA benchmark, do not read benchmark v0 (so its adversarial_holdout is not looked at), and do not authorize training or production use.

## Results

| When (KST) | Model | Outcome | Evidence |
|---|---|---|---|
| 2026-10-26 ~12:35 | E4B, `gemma-4-e4b-it-4bit` @ 475b908 | **Did not load.** While `mlx_lm.load` ran, swap grew and free disk fell from 4.2 GB to 1.17 GB; the outside watchdog (threshold 1.5 GB) killed the process (exit 143). No token was generated. Afterwards swap stood at 9.2 GB allocated, 7.9 GB used. | Watchdog output only: that runner version saved nothing before the kill. The runner now saves its record first and stops itself with status `aborted_low_disk`. |
| 2026-10-26 | Gemma 3 270M (`mlx-community/gemma-3-270m-it-4bit` @ ff1143e) — **pipeline check, not Gemma 4** | Runner works end to end: load 81 s, peak MLX memory 0.35 GB, 11.6–24.9 generated tokens/s. 0/5 cases passed: the model copied the schema text instead of filling it and never produced valid JSON. Size class recorded as `UNKNOWN(num_hidden_layers=18)`. | [runs/2026-10-26-pipeline-check-gemma3-270m/run_record.json](runs/2026-10-26-pipeline-check-gemma3-270m/run_record.json) |

Also verified without loading weights: the Gemma 4 E4B tokenizer and chat template render all five cases with a system turn and thinking off (333–400 prompt tokens each).

Not done, and why:
- **E4B inference**: blocked by memory on this machine as it was being used (8 GB, ~7 GB held by other apps, 9 GB swap, 2–4 GB free disk). Speed, memory and answer quality for E4B are unknown.
- **E2B pipeline check**: not attempted. E2B 4-bit is a 3.6 GB download and there was 2–3 GB of free disk with the E4B weights kept. Deleting the E4B weights to try E2B would not have produced an E4B result.

## Existing repository boundaries
- Mission 001 Artemis classifier configs in experiments/waymaker-ai/configs/artemis are prepared but never run; do NOT overwrite with QA experiment results.
- Original configs assume AutoModelForCausalLM; Gemma 4's official Hugging Face text/multimodal loader uses AutoProcessor + AutoModelForMultimodalLM. Verify compatibility before any cloud SFT.
- Mission 002 Artemis v2 prototype plan is a deterministic manual-QA design with an INACTIVE model adapter. Distinguish that from this new optional LLM smoke experiment.
- Follow B-fixed and WLIE deterministic safety gates; do not bypass them.
- No fee, credentials, personal data, real legal judgments, cloud training or API integration is authorized here.

## Follow-on gate
Once baseline local inference actually works, build a small human-reviewed synthetic/public-data question set with stable evidence IDs. Compare oracle-context QA, abstention, citations, Korean/English comprehension, speed, and errors. Only then decide whether QLoRA SFT is needed. The plan, in Korean, is in [MISSION-003-REPORT.ko.md](MISSION-003-REPORT.ko.md).

## References
- Gemma 4 overview (deprecated copy, memory table): https://ai.google.dev/gemma/docs/core
- MLX guide: https://gemma.ai/deployment/mlx/ (deprecated copy: https://ai.google.dev/gemma/docs/integrations/mlx)
- Canonical model: https://huggingface.co/google/gemma-4-E4B-it
- Conversion used: https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit
- QAT conversion named by the docs: https://huggingface.co/mlx-community/gemma-4-E4B-it-qat-4bit
- mlx-lm Gemma 4 loader: https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/models/gemma4.py
- Training overview: https://ai.google.dev/gemma/docs/tune
