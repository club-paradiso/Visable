# Waymaker Artemis — Gemma 4 foundation specification

Evidence checked 2026-10-29; integrity hardening checked 2026-10-30. Operational status: **file integrity verified; MLX-VLM
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
Their hashes are in the policy. The post-audit check also streamed the tokenizer,
weight index and every shard against pinned SHA-256 references. The original
2026-10-29 size-only result remains historical; it is not full-integrity evidence.
Strict runtime loading remains necessary. E4B is about 8B total parameters with
embeddings, not a 4B storage footprint. The E2B profile has 35 layers and hidden
size 1536 and is development-only. [Google model card](https://huggingface.co/google/gemma-4-E4B-it),
[conversion card](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit).

## Runtime contract

`foundation.select_profile` rejects unknown families, sizes, runtimes and
unaudited revisions before invoking any ML library. A missing pinned directory
never causes selection of another cached snapshot. `validate_snapshot` checks
architecture, processor, quantization and pinned metadata bytes. Full artifact
verification requires trusted references for tokenizer, index and all index-named
shards; missing references, extra shards or same-size corruption fail closed.
LFS SHA-256 references come from the pinned Hub API. Index SHA-256 references
come from the small pinned index downloads, cross-checked against API Git blob
IDs. Files are read in 1 MiB chunks; an in-process cache binds resolved path,
device, inode, size, mtime and ctime. A changed identity or new process hashes again.
This assumes a trusted local filesystem/kernel and reviewed policy; it does not
authenticate the publisher independently of the Hub. Cache roots
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

The shared `waymaker_ai.inference_input` projection is used before subprocess
handoff, again in the worker, by smoke prompt construction and by blind evidence
projection. It retains verbatim evidence id/title/text and allowlisted scalar
citation/source fields. It never serializes review notes, answer keys, approval
flags or nested objects masquerading as a source identifier or text field.
The textual research judge also uses common identity/integrity/resource preflight;
new judge cache keys include model provenance instead of reusing historical keys.

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
Metadata-only legacy records fail the new real-inference provenance gate; full
checkpoint integrity is a separate explicit field. Frozen independent benchmark
manifests remain `isolation_not_verified` until external enforcement is verified.
Content hashes and declarative role policies cannot certify isolation. Contamination
screening reports UNKNOWN with a null score for unusable inputs/corpora, and
otherwise reports only scoped lexical overlap with a named, hashed corpus.

Official Gold Accuracy remains N/A. The promotion ledger and scorer both fail
closed without an independent trusted review verifier. Local names, dates,
integrity hashes and fabricated attestation bundles never establish approval.

## Licensing and release limits

The Google card identifies Apache-2.0. The pinned MLX conversion card still says
`license: gemma`; this discrepancy is recorded, not silently normalized. Verify
the exact distribution license/NOTICE before publishing weights or adapters.
No redistribution or deployment was performed. The checkpoint itself has not
been fine-tuned by this project.

Post-audit evidence: [hardening report](PR-726-POST-AUDIT-HARDENING.ko.md),
[full E4B SHA-256 verification](runs/post-audit-20261030/checkpoint_sha256_verification.json).
Reference formats: [Hub file metadata](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api),
[Git object identity](https://git-scm.com/docs/git-hash-object).
