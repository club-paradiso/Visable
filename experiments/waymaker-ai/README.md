# Waymaker Artemis and Waymaker AI offline experiments

This package is the Mission 001 "Waymaker Genesis" experiment code for Visable's
assistant, Waymaker. It holds a reference implementation of layered legal
verification (WLIE), a benchmark with its validator, an evaluation runner that
scores WLIE against the existing backend, and the gates that a first
fine-tuning run (Artemis) must pass. Nothing here is wired into `/api/ask` or
any page a user sees.

- **Offline only.** No code or test opens a network connection. Laws come from
  recorded or synthetic source bundles. The existing backend is measured
  against a fake law.go.kr in a child process with sockets disabled. No API key
  is read.
- **Standard library only** for the package itself. The backend baselines run
  the backend in child processes, so a full run needs the backend's
  dependencies (`backend/requirements-dev.txt`) and Node for the JS baseline.
- **Not legal advice.** A label states what specs
  [06](../../docs/ai/waymaker-genesis/06-temporal-law-and-source-identity.md)
  and [07](../../docs/ai/waymaker-genesis/07-evidence-verification-design.md)
  require of a verifier. It does not state what Korean law is. No label has
  been reviewed by a person yet. Statute text in the bundles is attributed
  `출처: 법제처 국가법령정보센터 (law.go.kr)`.

Current Artemis foundation, runtime and recovery evidence: [Waymaker Artemis](artemis_bootstrap/README.md).

## Status

COMPLETED: finished and fixed. VERIFIED: checked by tests or by a recorded
run. IMPLEMENTED BUT NOT VALIDATED: the code exists and its tests pass, but it
has not been shown to work on real data or real traffic. NOT STARTED: nothing
built.

| Part | Where | Status |
|---|---|---|
| Shared vocabulary (statuses, layers, codes, `ClaimInput`, `ProvisionText`) | `waymaker_ai/contracts.py`, `waymaker_ai/dataset/tasks.py`, `schemas/` | COMPLETED (fixed contracts) |
| WLIE reference: source identity, temporal version candidates, citations, L1-L7 verification, evidence package, injection flagging | `waymaker_ai/legal/` | VERIFIED by tests on fixtures. IMPLEMENTED BUT NOT VALIDATED against real answers |
| WLIE in `/api/ask` | — | NOT STARTED (deliberately; [05](../../docs/ai/waymaker-genesis/05-legal-intelligence-architecture.md)) |
| Benchmark v0: 188 examples, 4 suites | `datasets/` ([datasets/README.md](datasets/README.md)) | IMPLEMENTED BUT NOT VALIDATED: labels are machine-checked or unreviewed, none `human_verified` |
| Dataset validator | `waymaker_ai/dataset/` | VERIFIED by tests. On v0: 0 errors, 16 warnings (2026-10-20) |
| One benchmark layout for validator, runner and SFT leakage guard | `waymaker_ai/dataset/layout.py` | COMPLETED, VERIFIED (`tests/test_dataset_layout.py`) |
| Template-level split check (`scenario.case_template`) | `waymaker_ai/dataset/validate.py` | VERIFIED by tests. No train split exists, so the train-against-eval rule has only run on fixtures |
| Evaluation runner, metrics, gates, report | `waymaker_ai/evaluation/` | VERIFIED by tests. Run on v0: [reports/](reports/) |
| `--backend-root` (before/after), `--fail-on-hard-gates` (CI), raw-payload omission | `waymaker_ai/evaluation/runner.py`, `report.py` | VERIFIED by tests and by a local before/after run against an archive of `fc896c2` |
| Local-model baseline (`openai_compatible`) | `waymaker_ai/evaluation/baselines/model.py` | IMPLEMENTED BUT NOT VALIDATED: never run against a served model |
| CI workflow | `.github/workflows/waymaker-ai-experiments.yml` | IMPLEMENTED BUT NOT VALIDATED: the YAML parses and each command passes locally; not yet run on GitHub |
| SFT builder, leakage guard, teacher-policy gate, training preflight | `waymaker_ai/distillation/`, `training/` | VERIFIED offline by tests. The preflight refuses today: no train split |
| QLoRA training (Artemis arms B and C) | `training/train_qlora.py`, `configs/artemis/` | IMPLEMENTED BUT NOT VALIDATED: never run (no GPU, no train split; [13](../../docs/ai/waymaker-genesis/13-artemis-experiment.md)) |
| Teacher-generated examples | `configs/teacher_policy.json` | NOT STARTED: refused until counsel's `legal_signoff` is `approved` (it is `pending`) |
| Train split; evidence-passage dedup across splits; paired significance tests | — | NOT STARTED |

## Layout

```
experiments/waymaker-ai/
  waymaker_ai/
    contracts.py         shared vocabulary (fixed contract)
    legal/               WLIE reference implementation (L1-L7, temporal resolver, adapters)
    dataset/             validator: layout.py, schema.py, validate.py, pii.py, inventory.py, tasks.py
    evaluation/          runner, benchmark loader, metrics, gates, report, fake law.go.kr,
                         baselines/ (wlie, b1_python, b2_js, existing_law, mock_model,
                         openai_compatible) and drivers/ (child-process entry points)
    distillation/        SFT builder, leakage guard, teacher policy, experiment config, preflight
  datasets/              benchmark v0, law identity registry, source bundles
  schemas/               example and source-bundle JSON schemas
  configs/               Artemis experiment configs, teacher policy
  training/              SFT build and QLoRA scripts (runbook: training/README.md)
  reports/               evaluation reports and the adversarial_holdout ledger
  tests/                 offline tests (tests/fixtures_dataset/: tiny validator fixtures)
```

Which files under a benchmark directory are examples is defined once, in
`waymaker_ai/dataset/layout.py`. Every `.json` / `.jsonl` file that is neither a
manifest nor dot-named is a data file, and the runner hashes all of them. A data
file is an example file unless it is under a hidden or evidence directory
(`fixtures`, `registry`, `sources`, `config`, `configs`, `schemas`, `reports`),
is a rubric (`*_rubric.json`), or is listed under `non_example_files` in a
`MANIFEST.json`. The validator checks example files and the runner scores
them. The SFT leakage guard reads every data file
([11 §5.1](../../docs/ai/waymaker-genesis/11-dataset-governance.md)).

## Commands

Run from `experiments/waymaker-ai` with a Python 3.11 interpreter that has
`backend/requirements-dev.txt` installed (`$PY`). Put scratch output outside
the repository (`$SCRATCH`).

```bash
# Tests (offline). The subprocess tests skip cleanly without the backend deps or Node.
$PY -m pytest -q -p no:cacheprovider tests

# Dataset validator: exit 0 = no errors (warnings may remain), 1 = errors, 2 = unusable input
$PY -m waymaker_ai.dataset.validate datasets/benchmark/v0 [--json "$SCRATCH/validation.json"]

# Evaluation runner, as CI runs it: exit 1 unless WLIE's hard gates pass
$PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines wlie,b1_python,b2_js,existing_law,mock_model \
  --splits dev,test,adversarial_holdout \
  --out "$SCRATCH/eval.json" --fail-on-hard-gates wlie

# A reported run (writes into reports/ and records the holdout look in the ledger)
$PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines b1_python,b1_python_raw,b2_js,wlie,existing_law,mock_model \
  --splits dev,test,adversarial_holdout \
  --out reports/<name>.json --markdown reports/<name>.md \
  --holdout-ledger reports/holdout-ledger.jsonl

# Before/after: the backend baselines against another backend tree
mkdir -p "$SCRATCH/main" && git -C ../.. archive origin/main backend | tar -x -C "$SCRATCH/main"
$PY -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \
  --baselines b1_python,existing_law --splits dev,test \
  --backend-root "$SCRATCH/main" --out "$SCRATCH/before.json"

# Training preflight (no GPU, imports nothing heavy). Today it exits 1:
# datasets/benchmark/v0/train.jsonl does not exist, which is the correct answer.
$PY training/build_sft_dataset.py --config configs/artemis/exp_b_sft_qlora.json
$PY training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --check-only
```

`adversarial_holdout` is reported once per frozen benchmark version. Do not
tune on it. A run whose numbers you report passes `--holdout-ledger`, and the
ledger marks a repeat look. A re-scoring of items already seen (for example
after a relabel, which changes the benchmark digest) also passes
`--holdout-post-hoc REASON`. CI scores it as a pass/fail check only and writes
no ledger entry
([12 §6](../../docs/ai/waymaker-genesis/12-evaluation-methodology.md)). v0's
holdout has been looked at nine times (ledger entries 1-9). Every number after
entry 1 is post hoc.

Last local check (2026-10-21, commit `1481605`, Python 3.11.15, Node
v24.14.0): 1032 tests passed, the validator gave PASS (0 errors, 16 warnings),
and the backend suite gave 83/83. The current report is
[reports/benchmark-v0-2026-10-20.md](reports/benchmark-v0-2026-10-20.md), which
is post hoc. Its first-look counterpart and the before/after of the law-stack
fixes are in
[adjudication-log.md](../../docs/ai/waymaker-genesis/research-notes/adjudication-log.md).
The CI-shaped runner command (`--fail-on-hard-gates wlie`) was not re-run as a
separate holdout look. In the current report every WLIE hard gate is `pass` or
`not_applicable`, and that is what the command checks.

## Documents

| Doc | Topic |
|---|---|
| [05](../../docs/ai/waymaker-genesis/05-legal-intelligence-architecture.md) | WLIE architecture decision |
| [06](../../docs/ai/waymaker-genesis/06-temporal-law-and-source-identity.md) | Temporal law and source identity (normative) |
| [07](../../docs/ai/waymaker-genesis/07-evidence-verification-design.md) | Evidence verification, layers L1-L7 (normative) |
| [08](../../docs/ai/waymaker-genesis/08-foundation-model-research.md) | Foundation model research (researched only) |
| [09](../../docs/ai/waymaker-genesis/09-training-and-distillation.md) | Training and distillation (researched only) |
| [10](../../docs/ai/waymaker-genesis/10-athena-and-hestia-strategy.md) | Athena and Hestia strategy (researched only) |
| [11](../../docs/ai/waymaker-genesis/11-dataset-governance.md) | Dataset governance and validator rules (normative for the validator) |
| [12](../../docs/ai/waymaker-genesis/12-evaluation-methodology.md) | Evaluation methodology, gates, reports, CI (normative) |
| [13](../../docs/ai/waymaker-genesis/13-artemis-experiment.md) | Artemis fine-tuning experiment (prepared, not run) |
