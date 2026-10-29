# Waymaker Artemis

Canonical foundation: **Google Gemma 4 E4B Instruct**. The authoritative policy
is [artemis_foundation.json](../configs/artemis_foundation.json); inference and
training validate against it. E2B is an explicitly selected development profile.
No implicit model or revision fallback is allowed.

Recovery status, 2026-10-29: checkpoint metadata verified; new MLX-VLM weight
loading and generation **not executed** on this M1 8GB machine. The runtime is
missing and disk/swap limits block loading. This is not a Gemma 4 accuracy result.
Official Gold Accuracy = **N/A**. No training, deployment or PR merge occurred.

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
must be installed separately. No automatic sibling-worktree discovery is used.
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
