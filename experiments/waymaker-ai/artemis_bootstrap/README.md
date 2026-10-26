# Artemis Gemma 4 — First Inference (2026-10-26)

Status: SETUP ONLY. No model has been downloaded, loaded, served, trained, benchmarked or deployed by this PR.

## Goal
Run an isolated, synthetic-only first inference with google/gemma-4-E4B-it, keeping production VISABLE /api/ask unchanged.
Do not use real applicant records, nonpublic manuals, or production credentials.

## Model identity
- Canonical instruction model: google/gemma-4-E4B-it (Apache-2.0 per official model card).
- Apple Silicon inference conversion: mlx-community/gemma-4-E4B-it-qat-4bit. This is a COMMUNITY QUANTIZED artifact, not the canonical model checkpoint.
- If Mac unified memory is only 8GB or the E4B conversion fails to load, the E2B conversion mlx-community/gemma-4-E2B-it-qat-4bit may be used to test the pipeline. Never count E2B results as E4B.
- E4B means approximately 4.5B effective parameters, approximately 8B total. The MLX community conversion repository contains approximately 6.8GB of files; memory needed in practice also depends on cache, runtime and context length.

## On the owner's MacBook Air M1
1. Check Apple menu > About This Mac > Memory: 8GB or 16GB.
2. Install a compatible Python 3 environment and ensure python3 and pip work.
3. In a separate experiment virtualenv, run:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -U mlx mlx-lm mlx-vlm

4. Start the LOCAL-only compatible model server:

    mlx_vlm.server --model mlx-community/gemma-4-E4B-it-qat-4bit --port 8080

5. If E4B fails due to memory, stop the server and retry a PIPELINE-ONLY smoke test:

    mlx_vlm.server --model mlx-community/gemma-4-E2B-it-qat-4bit --port 8080

6. Keep the server bound to localhost. Do not publish ports, enable tunnels, or share real immigration questions.
7. Call its OpenAI-compatible /v1/chat/completions API using only fictional/synthetic evidence. Do not persist raw prompts by default.

## Minimum smoke tests (synthetic evidence only)
Test A: A fictional office's intake location is explicitly given; ask for location and check grounded response.
Test B: The fictional document contains no fee; ask fee and verify model does NOT make one up.
Test C: Two fictional source snippets disagree on hours; verify clarification or abstention rather than unsupported certainty.
Record model revision (including original and conversion), local hardware and memory, exact runtime versions, inference success/failure and qualitative observations.
These 3 tests are NOT a legal QA benchmark and do not authorize training or production use.

## Existing repository boundaries
- Mission 001 Artemis classifier configs in experiments/waymaker-ai/configs/artemis are prepared but never run; do NOT overwrite with QA experiment results.
- Original configs assume AutoModelForCausalLM; Gemma 4's official Hugging Face text/multimodal loader uses AutoProcessor + AutoModelForMultimodalLM. Verify compatibility before any cloud SFT.
- Mission 002 Artemis v2 prototype plan is a deterministic manual-QA design with an INACTIVE model adapter. Distinguish that from this new optional LLM smoke experiment.
- Follow B-fixed and WLIE deterministic safety gates; do not bypass them.
- No fee, credentials, personal data, real legal judgments, cloud training or API integration is authorized here.

## Follow-on gate
Once baseline local inference actually works, build a small human-reviewed synthetic/public-data question set with stable evidence IDs. Compare oracle-context QA, abstention, citations, Korean/English comprehension, speed, and errors. Only then decide whether QLoRA SFT is needed.

## References
- Google Gemma 4 overview: https://ai.google.dev/gemma/docs/core
- Google MLX guide: https://gemma.ai/deployment/mlx/
- Canonical model: https://huggingface.co/google/gemma-4-E4B-it
- Community MLX conversion: https://huggingface.co/mlx-community/gemma-4-E4B-it-qat-4bit
- Training overview: https://ai.google.dev/gemma/docs/tune