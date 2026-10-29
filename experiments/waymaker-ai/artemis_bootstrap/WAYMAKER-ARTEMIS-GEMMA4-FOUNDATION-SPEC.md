# Waymaker Artemis — Gemma 4 foundation specification

Evidence checked 2026-10-29. Operational status: **metadata verified; MLX-VLM
execution blocked locally**, not production-ready. Policy source:
[`configs/artemis_foundation.json`](../configs/artemis_foundation.json).

| Field | Canonical E4B profile |
|---|---|
| Foundation | Google Gemma 4 E4B Instruct |
| Upstream | `google/gemma-4-E4B-it` |
| Upstream revision | `ee0ef6023621cff504d758262d4e04895a5af4a2` |
| Inference artifact | `mlx-community/gemma-4-e4b-it-4bit` |
| Inference revision | `475b9088d29754a3379866cf5aeb6b41acd313c2` |
| Conversion source revision, per card | `fee6332c1abaafb77f6f9624236c63aa2f1d0187` |
| Architecture | `Gemma4ForConditionalGeneration`, `model_type=gemma4` |
| Text tower | 42 layers, hidden size 2560, vocabulary 262144 |
| Processor | `Gemma4Processor` |
| Quantization | affine 4-bit, group size 64 |
| Runtime | explicit `mlx_vlm`, inspected version 0.7.11 |
| Implicit fallback | prohibited |

The upstream, conversion source and conversion revisions are different fields;
none is a synonym for another. The community snapshot's five small metadata
files were compared byte-for-byte by SHA-256 with the same remote revision.
Their hashes are in the policy. Safetensors files must exist and be nonempty;
this recovery checked their sizes, **not a fresh full weight hash**. Strict
runtime loading remains necessary. E4B is about 8B total parameters with
embeddings, not a 4B storage footprint. The E2B profile has 35 layers and hidden
size 1536 and is development-only. [Google model card](https://huggingface.co/google/gemma-4-E4B-it),
[conversion card](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit).

## Runtime contract

`foundation.select_profile` rejects unknown families, sizes, runtimes and
unaudited revisions before invoking any ML library. A missing pinned directory
never causes selection of another cached snapshot. `validate_snapshot` checks
architecture, processor, quantization and pinned metadata bytes. Cache roots
are an explicit CLI path, recognized HF cache environment variables or standard
local cache roots; there is no network resolver.

`gemma4_runtime.py` uses `mlx_vlm.load(..., strict=True,
trust_remote_code=False)` and the returned processor. `apply_chat_template`
receives text messages with zero images/audio and thinking disabled. The worker
passes temperature explicitly (default 0), bounds tokens and refuses oversized
prompts without truncation. Generation returns a `GenerationResult`, not the
plain string expected by the old adapter. The parser requires exactly `status`,
`answer`, `citations`, validates types and rejects unlisted citations. This is
post-generation validation, **not grammar-constrained decoding**. Invalid output
is retained as a failed execution. [MLX-VLM](https://github.com/Blaizzy/mlx-vlm).

The parent imposes a timeout that also covers loading. A worker thread checks
disk/swap while loading; exit 75 means resource abort. MLX memory/cache limits
are set before loading. Process RSS can exceed MLX allocations; the 6GB limit
is not a guarantee of safe total system memory. `run_smoke.py` shares identity,
preflight, runtime and token limits, retaining its fictional-case guardrails.

## Provenance and governance

Every new run carries profile, model/revisions, runtime/version probe, config
hash, metadata hashes, decoding settings and execution status. Successful or
failed generation also retains raw text, warning/error output, load/generation
time, reported token rates, derived prefill/decode duration, MLX peak memory,
RSS and before/after disk/swap where measurable. Missing measurements are null.

`metric_group` separates real inference, mock and recorded fixtures and includes
profile/checkpoint/revision/runtime. Aggregation refuses a different group,
benchmark hash or evaluation mode. Shadow evaluation requires an explicit,
completed provenance-verified run; it has no legacy run-file default. Synthetic
regression results stay separate. Existing benchmark/evidence schema versions
are unchanged; provenance additions use existing extension fields.

Official Gold Accuracy remains N/A. The promotion ledger and scorer both fail
closed without an independent trusted review verifier. Local names, dates,
integrity hashes and fabricated attestation bundles never establish approval.

## Licensing and release limits

The Google card identifies Apache-2.0. The pinned MLX conversion card still says
`license: gemma`; this discrepancy is recorded, not silently normalized. Verify
the exact distribution license/NOTICE before publishing weights or adapters.
No redistribution or deployment was performed. The checkpoint itself has not
been fine-tuned by this project.
