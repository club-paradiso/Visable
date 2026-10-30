# Waymaker Artemis

Canonical foundation: **Google Gemma 4 E4B Instruct**. The authoritative policy
is [artemis_foundation.json](../configs/artemis_foundation.json); inference and
training validate against it. E2B is an explicitly selected development profile.
No implicit model or revision fallback is allowed.

Current Mission 005-B status, 2026-10-30: the dedicated local `.venv` now has
MLX-VLM 0.7.11 and Pillow, and real processor/tokenizer/template initialization
passed. The 32-token probe remains **not_executed** because used swap exceeded
the unchanged 2GB limit. No model weights were loaded into MLX and no tokens
were generated. See [the execution report](MISSION-005-B-REAL-INFERENCE-REPORT.ko.md)
and [hash-locked runtime dependencies](requirements-mlx-vlm-0.7.11.lock).
The recovery observations below describe earlier environment states.

Mission 005-C, 2026-10-30: a separate CUDA path loads the official
`google/gemma-4-E4B-it` checkpoint at the pinned upstream revision with explicit
NF4 4-bit quantization ([gemma4_cuda_runtime.py](gemma4_cuda_runtime.py),
[cuda policy](../configs/artemis_cuda_runtime.json)). It never pools metrics with
MLX. A free Colab T4 run was audited from the exported notebook only; it is **not
independently verified**, and no new CUDA generation has run from this code yet.
See the [audit](COLAB-T4-RUN-AUDIT.ko.md), the [Mission 005-C report](MISSION-005-C-REPORT.ko.md)
and the [reproduction notebook](notebooks/artemis_gemma4_e4b_cuda_colab.ipynb).
Mission 005-C.1 (Draft PR #730, stacked on PR #726) requires full model provenance
before a CUDA run record counts, pins the notebook to an exact code commit and
package versions, and keeps the new runtime at `not_executed` until a real GPU run.
Record checks are self-checks of our own JSON, not external attestation. See the
[Mission 005-C.1 report](MISSION-005-C1-REPORT.ko.md).

Recovery status, 2026-10-29: checkpoint metadata verified; new MLX-VLM weight
loading and generation **not executed** on this M1 8GB machine. The runtime is
missing and disk/swap limits block loading. This is not a Gemma 4 accuracy result.
Official Gold Accuracy = **N/A**. No training, deployment or PR merge occurred.

Post-audit hardening, 2026-10-30: full cached E4B SHA-256 verification completed;
new inference remains `not_executed` because MLX-VLM is missing. See the
[PR #726 hardening report](PR-726-POST-AUDIT-HARDENING.ko.md) for the four audit
fixes, regression evidence and the 78-file review scope.

## Run and verify

From `experiments/waymaker-ai`, with a Python environment containing pytest and
backend development dependencies:

```bash
python -m pytest -q -p no:cacheprovider tests
python artemis_bootstrap/check_model_identity.py
python artemis_bootstrap/probe_gemma4.py --python /path/to/isolated-mlx-vlm/bin/python \
  --out /path/to/new-run/inference_probe.json
python artemis_bootstrap/artemis_runner.py --adapter local_mlx \
  --local-profile gemma4_e4b --local-runtime mlx_vlm \
  --local-python /path/to/isolated-mlx-vlm/bin/python --local-max-tokens 32 \
  --benchmark artemis_bootstrap/benchmarks/artemis_eval_dev_20.json \
  --out-dir /path/to/new-evaluation
```

The last two commands never download weights. Unavailable checkpoints/runtime
or unsafe resources produce `not_executed` and exit 3. Model operation errors
produce failed/partial status. Raw output and telemetry are retained even when
structured JSON fails. The adapter strips answer keys and rubrics from the prompt.
Candidate scoring still requires the evaluator's answer key; passing a blind
projection alone is a compatibility check, not a valid candidate accuracy run.

MLX-VLM 0.7.11 is the source-inspected runtime target; its dependency environment
must be installed separately on each machine. The local Mission 005-B environment
is isolated from verification/backend packages; use the recorded lock and explicit
Python path to reproduce it. No automatic sibling-worktree discovery is used.
The current bounds are 32 tokens in the probe (256 maximum), 2,048 prompt tokens,
120 seconds per worker, at least 6GB free disk, at most 2GB used swap, and 6GB MLX
allocation. These are conservative engineering limits, not measured requirements.

## Evidence and design

- [Recovery audit](WAYMAKER-ARTEMIS-RECOVERY-AUDIT.ko.md)
- [Foundation specification](WAYMAKER-ARTEMIS-GEMMA4-FOUNDATION-SPEC.md)
- [Inference report](WAYMAKER-ARTEMIS-GEMMA4-INFERENCE-REPORT.ko.md)
- [Fine-tuning plan](WAYMAKER-ARTEMIS-FINETUNING-PLAN.md)
- [Cleanup manifest](WAYMAKER-ARTEMIS-LOCAL-CLEANUP-MANIFEST.json)
- [Historical migration](WAYMAKER-ARTEMIS-LEGACY-MIGRATION.md)
- [Corrected Mission 005-A](MISSION-005-A-REPORT.ko.md)
- [Mission 005-B](MISSION-005-B-NEXT-STEPS.md)

The 60 candidate cases, dev/held-out partitions, evidence ledgers, review
workbench, source versioning and security regressions remain in place. The
original 40 held-out cases remain `isolation_not_verified`. Reviewer names,
dates and local signatures cannot authorize gold; an independent verifier is
not connected. Software tests do not establish legal accuracy.

Earlier E4B experiments and their limits are preserved in
[the first-inference history](history/FIRST-INFERENCE-20261026.md). They used an
older text-tower MLX-LM path and synthetic/repeated research cases. They do not
validate the new MLX-VLM adapter or supply an independent legal baseline.
