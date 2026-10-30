# Waymaker Artemis — Gemma 4 adaptation plan

Status: architecture and guarded scaffold; **no training executed**. The local
preflight refuses because `datasets/benchmark/v0/train.jsonl` does not exist.
The 60 candidate evaluation cases are not a training dataset.

## Five distinct subsystems

| Subsystem | Responsibility |
|---|---|
| Foundation | Pinned Google Gemma 4 E4B Instruct; E2B only an explicit development profile |
| Legal grounding | Retrieve versioned official statutes and public administrative guidance; preserve source identity, dates, hashes and conflicts |
| Adaptation | Train actual LoRA parameters on reviewed Korean instruction/evidence/response pairs |
| Evaluation | Independent review, frozen unseen questions, model/revision-specific scoring and security probes |
| Deployment | Serve a verified base-plus-adapter artifact with versioned retrieval and fail-closed response checks |

RAG supplies evidence at inference time. It does not update parameters and does
not count as fine-tuning. Keep the existing classification-only B/C arms; add a
separate legal response adaptation arm after its dataset and response schema
are reviewed. Do not relabel the existing seven-key classifier SFT as legal QA.

## Checkpoints and frameworks

Train from `google/gemma-4-E4B-it` at the upstream revision in the foundation
policy, not from the MLX affine inference conversion. The scaffold now validates
both its model/revision and `AutoModelForImageTextToText` + `AutoProcessor` path
before loading weights. The language tokenizer supplies text-only training
batches. Verify the actual forward/loss path, processor and adapter save/reload
on a five-step CUDA smoke run before declaring compatibility. Transformers
documents Gemma 4 multimodal architecture and text usage.
[Transformers Gemma 4](https://huggingface.co/docs/transformers/model_doc/gemma4).

The intended stack is Transformers + TRL SFTTrainer + PEFT LoRA + bitsandbytes
NF4 double quantization. Freeze base weights; train rank-16 language projection
adapters with alpha 32, dropout 0.05, gradient checkpointing and batch size 1.
These are initial experimental settings, not validated optima. Enumerate actual
module names; require the selected q/k/v/o and feed-forward projections, exclude
vision/audio towers, log trainable parameters and refuse missing targets. Keep
existing loss, leakage, teacher-policy and paid-compute gates. PEFT documents
quantized adapter training; TRL supports conversational prompt/completion SFT.
[PEFT quantization](https://huggingface.co/docs/peft/developer_guides/quantization),
[TRL SFT](https://huggingface.co/docs/trl/sft_trainer).

Unsloth explicitly documents E4B QLoRA and estimates 10GB VRAM for its optimized
recipe, 17GB for E4B LoRA. Those are framework-specific claims, not measurements
of this repository. It is a credible alternative experiment on the **same E4B
foundation**, subject to checkpoint conversion/revision verification.
[Unsloth Gemma 4 training](https://unsloth.ai/docs/models/gemma-4/train).

## Data and Korean legal supervision

Author each record with a Korean question, applicability date, procedure scope,
versioned evidence, source IDs, allowed response status, answer and cited
passage IDs. Preserve protected residence-status codes and official terminology.
Train citation-to-passage alignment, uncertainty, clarification, conflict and
refusal behavior. Never supervise unsupported requirements from model memory.
A citation string alone is insufficient: reviewers must check the passage and
its effective date. Store reviewer attestations outside the developer-controlled
label file and require trusted verification before gold promotion.

Use conversational prompt/completion JSONL with completion-only loss on the
reviewed response. Do not train on private applicant records or hidden reasoning
traces. For the proposed legal-QA arm, hash the grounding prompt and schema;
existing classifier records cannot be reused under a different schema by renaming.

Split by scenario template, evidence passage, statutory version and near-duplicate
question clusters before training. Freeze manifests and provenance. Development
chooses checkpoints; unseen validation checks overfitting; the independent test
set is scored once after freeze. Existing 40 held-out cases are visible in git
and stay `isolation_not_verified`; use them only for diagnostics/regressions.
A genuinely independent benchmark must be authored/reviewed outside that access
boundary. Official Gold Accuracy stays N/A until that process is authenticated.

## Hardware and budget

Engineering estimate for this unexecuted stack: start with a 24GB CUDA GPU for
QLoRA, 32–48GB host RAM, 40–60GB free storage, sequence length 2,048, batch size 1
and gradient accumulation. A 16GB GPU may fit a shorter optimized run but is not
a promised configuration. BF16 LoRA should budget 32–48GB VRAM for headroom;
E4B's roughly 8B stored parameters alone are about 16GB at 16 bits. Measure
peak allocated/reserved VRAM, tokens/s and loss on the five-step smoke run.
M1 8GB is for code/offline validation and bounded inference when resources allow.

Runpod's public price page, checked 2026-10-29, lists L4 24GB at $0.59/h and A100
80GB at $1.79/h. A **hypothetical** 2–8 GPU-hour pilot therefore costs $1.18–$4.72
or $3.58–$14.32 in GPU time, excluding storage, setup and retries. Duration is a
planning envelope, not a performance prediction. Obtain a current capacity quote
and authorization before provisioning. No paid job or weight download started.
[Runpod pricing](https://www.runpod.io/pricing).

## Adapter lifecycle and deployment

Each adapter manifest must bind upstream revision, tokenizer/template hashes,
training dataset hash, split manifest, seed, framework versions, target-module
list, precision, step count, losses, VRAM and compute cost. Save immutable adapter
checkpoints outside Git and verify save/reload equivalence. Never overwrite a
run. Keep E2B and E4B adapter namespaces separate.

Initially serve on the validated CUDA training stack to avoid conversion drift.
Evaluate plain base, base+RAG, adapted base and adapted base+RAG separately using
identical evidence and decoding where applicable. Verify vLLM LoRA support or
merge into the exact base before exporting; both are deployment validation gates,
not completed tasks. An MLX export requires explicit conversion plus logits/text
regression checks and new provenance. Do not attach an adapter to the older MLX
conversion source revision without proving compatibility. Preserve Apache-2.0
license/NOTICE obligations for upstream distribution and resolve the community
conversion's conflicting `gemma` card label before redistribution.
