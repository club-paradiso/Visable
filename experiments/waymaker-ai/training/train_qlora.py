"""Artemis QLoRA training: TRL SFTTrainer + PEFT LoRA on a 4-bit NF4 base.

Why this script refuses so much before it trains: an adapter is only worth
evaluating if nobody can later ask "what exactly was it trained on?". So,
before any GPU library is imported, ``waymaker_ai.distillation.preflight``
must report nothing:

* the config is a model arm (B or C), not paid, and its base model has a
  pinned 40-character revision and a licence in the allow-list;
* the dataset validator passes on the train file read together with the
  benchmark;
* every train example passes the SFT gates (schema, label review, teacher
  gate for teacher-generated labels), every train question carries both
  Artemis labels, and none overlaps dev, test or adversarial_holdout above the
  configured word 3-gram threshold;
* the SFT file on disk is byte-identical to a fresh build of that split, whose
  prompts and targets are the evaluation runner's own ``openai_compatible``
  request and schema (so the adapter is trained on what it is scored on).

Only then are torch, transformers, peft, trl and bitsandbytes imported (inside
``train``), so this module imports, ``--help`` works and ``--check-only`` runs
on a machine with none of them installed. A real run additionally needs every
package in requirements-train.txt pinned and installed at that version, and a
local CUDA GPU.

Paid compute: there is no flag that unlocks it. ``--paid-endpoint`` exists so
that an operator who is about to use one is told no, and the cost
acknowledgement flag is accepted but never needed (local GPUs) and never
sufficient (paid endpoints). Paid training is not authorised in Mission 001.

Status: written against the TRL v1.16.0, PEFT and transformers documentation
the research notes cite. NEVER EXECUTED: there was no GPU and no package was
installed while it was written. The first run must be a smoke run.

Usage, from experiments/waymaker-ai::

    python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --check-only
    python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --model secondary --seed 1 --max-steps 5
    python training/train_qlora.py --config configs/artemis/exp_b_sft_qlora.json --seed 1

Exit status: 0 trained (or ``--check-only`` passed), 1 refused by a gate,
2 command line error, 3 environment not ready (packages, pins, GPU).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from waymaker_ai.distillation import experiment_config, preflight  # noqa: E402  (path set above)

REQUIREMENTS_PATH = Path(__file__).resolve().parent / "requirements-train.txt"
#: Run directories live beside this script; training/.gitignore keeps adapters out of git.
RUNS_DIR = Path(__file__).resolve().parent / "runs"
RUN_RECORD_VERSION = "waymaker-artemis-run/0.1"

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_ENVIRONMENT = 3

#: Module-path fragments of the non-text towers in Gemma 4 E-models (text,
#: image and audio, models.md §3a). LoRA on those layers trains nothing
#: Artemis uses and costs memory, so matches there are excluded and recorded.
TOWER_MARKERS: Tuple[str, ...] = ("vision", "audio", "multi_modal")

#: Packages whose installed version a run must match. torch is recorded only.
TRAINING_PACKAGES: Tuple[str, ...] = ("trl", "transformers", "peft", "bitsandbytes", "accelerate", "datasets")


# ---------------------------------------------------------------------------
# requirements-train.txt
# ---------------------------------------------------------------------------
@dataclass
class Requirements:
    pinned: Dict[str, str] = field(default_factory=dict)
    todo: List[str] = field(default_factory=list)
    recorded: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)


def _canonical_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_requirements(text: str) -> Requirements:
    """Read the three line kinds documented at the top of requirements-train.txt.

    A requirement line that is not ``name==version`` (``>=``, an extra, a URL)
    is a problem: a range is not a pin.
    """
    found = Requirements()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            if body.startswith("TODO(pin):"):
                name = body[len("TODO(pin):"):].split()
                if name:
                    found.todo.append(_canonical_name(name[0]))
            elif body.startswith("RECORDED:"):
                name = body[len("RECORDED:"):].split()
                if name:
                    found.recorded.append(_canonical_name(name[0]))
            continue
        requirement = line.split("#", 1)[0].strip()
        name, separator, version = requirement.partition("==")
        if separator != "==" or not name.strip() or not version.strip() or any(c in name for c in "<>=!~[;@ "):
            found.problems.append(f"requirements-train.txt line {number}: {requirement!r} is not pinned as name==version")
            continue
        found.pinned[_canonical_name(name)] = version.strip()
    for name in TRAINING_PACKAGES:
        if name not in found.pinned and name not in found.todo:
            found.problems.append(f"requirements-train.txt does not list {name} (pinned or TODO)")
    return found


def pin_problems(requirements: Requirements, installed: Mapping[str, Optional[str]], *, smoke: bool) -> List[str]:
    """Why the installed packages do not match the pins. A smoke run tolerates TODO pins only."""
    problems = list(requirements.problems)
    for name, version in sorted(requirements.pinned.items()):
        have = installed.get(name)
        if have is None:
            problems.append(f"{name}=={version} is pinned but not installed")
        elif have != version:
            problems.append(f"{name} {have} is installed but requirements-train.txt pins {version}")
    for name in requirements.todo:
        if installed.get(name) is None:
            problems.append(f"{name} is not installed")
        elif not smoke:
            problems.append(
                f"{name} is still TODO(pin) in requirements-train.txt: pin the version a smoke run recorded "
                "before a real run"
            )
    return problems


def installed_versions(names: Sequence[str]) -> Dict[str, Optional[str]]:
    """Installed distribution versions, read from package metadata (no import of the package)."""
    from importlib import metadata

    versions: Dict[str, Optional[str]] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


# ---------------------------------------------------------------------------
# Small decisions that do not need torch
# ---------------------------------------------------------------------------
def resolve_compute_dtype(configured: str, bf16_supported: bool) -> Tuple[Optional[str], str]:
    """(dtype name, explanation). None means the configured dtype cannot run on this GPU.

    A T4 has no native bf16. The old scaffold hard-coded bf16 while recommending
    a T4 (knowledge-platform.md §4, defect 3); "auto" picks fp16 there instead.
    """
    if configured == "auto":
        if bf16_supported:
            return "bfloat16", "auto: the GPU supports bf16"
        return "float16", "auto: the GPU has no native bf16 (e.g. a T4), so fp16"
    if configured == "bfloat16" and not bf16_supported:
        return None, "the config asks for bfloat16 but this GPU has no native bf16; use 'auto' or 'float16'"
    if configured in ("bfloat16", "float16"):
        return configured, "as configured"
    return None, f"unknown compute dtype {configured!r}"


def select_target_modules(
    linear_names: Sequence[str], targets: Sequence[str]
) -> Tuple[List[str], List[str], List[str]]:
    """Split the model's linear layers into (included, excluded tower layers, missing targets).

    A layer matches a target when the last segment of its dotted name equals
    the target (PEFT's suffix rule). Layers inside a vision or audio tower are
    excluded. A target with no language-model match is reported as missing,
    which train() treats as a refusal: the config would be describing an
    adapter that does not exist.
    """
    wanted = set(targets)
    included: List[str] = []
    excluded: List[str] = []
    hit: set = set()
    for name in linear_names:
        leaf = name.rsplit(".", 1)[-1]
        if leaf not in wanted:
            continue
        lowered = name.lower()
        if any(marker in lowered for marker in TOWER_MARKERS):
            excluded.append(name)
            continue
        included.append(name)
        hit.add(leaf)
    missing = sorted(wanted - hit)
    return included, excluded, missing


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_directory(
    config: experiment_config.ExperimentConfig, model_role: str, seed: int, smoke: bool, root: Path = RUNS_DIR
) -> Path:
    name = f"{model_role}-seed{seed}"
    return Path(root) / config.id / (f"smoke-{name}" if smoke else name)


def chosen_model(
    config: experiment_config.ExperimentConfig, role: str
) -> Optional[experiment_config.BaseModel]:
    return config.base_model if role == "primary" else config.secondary_model


def configured_seeds(config: experiment_config.ExperimentConfig) -> List[int]:
    return list(config.hyperparameter("optimization", "seeds"))


def load_sft_records(path: Path) -> List[Dict[str, Any]]:
    """prompt/completion pairs only. The meta block stays in the file for audit, not in the trainer."""
    records: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records.append({"prompt": record["prompt"], "completion": record["completion"]})
    return records


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Artemis QLoRA SFT. Refuses unless every data, licence and cost gate passes.",
    )
    parser.add_argument("--config", type=Path, required=True, help="configs/artemis/<arm>.json")
    parser.add_argument("--check-only", action="store_true", help="run every gate, import nothing heavy, train nothing")
    parser.add_argument("--seed", type=int, help="one of the config's seeds (required to train)")
    parser.add_argument(
        "--model", choices=("primary", "secondary"), default="primary",
        help="train the config's base_model (default) or its pinned secondary_model, with the same hyper-parameters",
    )
    parser.add_argument(
        "--max-steps", type=int, default=None,
        help="smoke run: stop after N optimiser steps; the adapter is never evaluated",
    )
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR, help="where run directories are created")
    parser.add_argument(
        "--paid-endpoint", metavar="NAME", default=None,
        help="name a paid endpoint (rented GPU, managed fine-tuning API) to be refused; nothing unlocks it",
    )
    parser.add_argument(
        "--i-understand-this-may-cost-money", dest="cost_acknowledged", action="store_true",
        help="accepted for compatibility; not needed for a local GPU and not sufficient for a paid endpoint",
    )
    return parser


def gate_problems(config: experiment_config.ExperimentConfig, args: argparse.Namespace) -> List[str]:
    problems = preflight.preflight(config, paid_endpoint_flag=bool(args.paid_endpoint))
    if args.paid_endpoint and args.cost_acknowledged:
        problems.append("--i-understand-this-may-cost-money does not unlock a paid endpoint in Mission 001")
    if args.model == "secondary":
        secondary = chosen_model(config, "secondary")
        if secondary is None:
            problems.append("--model secondary: the config has no secondary_model")
        else:
            problems.extend(experiment_config.model_blockers(secondary))
    if not args.check_only:
        seeds = configured_seeds(config) if config.training else []
        if args.seed is None:
            problems.append(f"--seed is required to train; the config lists {seeds}")
        elif args.seed not in seeds:
            problems.append(f"seed {args.seed} is not one of the config's seeds {seeds}")
        if args.max_steps is not None and args.max_steps < 1:
            problems.append("--max-steps must be a positive integer")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = experiment_config.load_config(args.config)
    except (OSError, experiment_config.ConfigError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    problems = gate_problems(config, args)
    if problems:
        print(f"REFUSED: {config.id} may not train ({len(problems)} problem(s)):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return EXIT_REFUSED
    if args.check_only:
        print(f"{config.id}: every gate passed. Package pins and the GPU are checked when training starts.")
        return EXIT_OK
    return train(config, args)


# ---------------------------------------------------------------------------
# Training (heavy imports live only here)
# ---------------------------------------------------------------------------
def environment_problems(smoke: bool) -> Tuple[List[str], Dict[str, Optional[str]]]:
    requirements = parse_requirements(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    names = sorted(set(TRAINING_PACKAGES) | set(requirements.pinned) | set(requirements.todo) | set(requirements.recorded))
    installed = installed_versions(names)
    return pin_problems(requirements, installed, smoke=smoke), installed


def train(config: experiment_config.ExperimentConfig, args: argparse.Namespace) -> int:  # pragma: no cover - needs a GPU
    smoke = args.max_steps is not None
    problems, installed = environment_problems(smoke)
    if problems:
        print("ENVIRONMENT NOT READY:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return EXIT_ENVIRONMENT

    out_dir = run_directory(config, args.model, args.seed, smoke, args.runs_dir)
    if (out_dir / "run_record.json").exists() or (out_dir / "adapter").exists():
        print(f"REFUSED: {out_dir} already holds a run; results are never overwritten", file=sys.stderr)
        return EXIT_REFUSED

    import torch  # heavy imports are deliberately local to train()
    import transformers
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        print("ENVIRONMENT NOT READY: no CUDA GPU is visible; this script trains on a local GPU only", file=sys.stderr)
        return EXIT_ENVIRONMENT

    quantization = config.training["quantization"]
    lora = config.training["lora"]
    opt = config.training["optimization"]
    dtype_name, dtype_note = resolve_compute_dtype(quantization["compute_dtype"]["value"], torch.cuda.is_bf16_supported())
    if dtype_name is None:
        print(f"ENVIRONMENT NOT READY: {dtype_note}", file=sys.stderr)
        return EXIT_ENVIRONMENT
    compute_dtype = getattr(torch, dtype_name)

    base = chosen_model(config, args.model)
    loader = getattr(transformers, base.loader, None)
    if loader is None:
        print(f"REFUSED: transformers has no loader class {base.loader!r}", file=sys.stderr)
        return EXIT_REFUSED

    sft_path = config.resolve(config.sft_file)
    records = load_sft_records(sft_path)
    processor = transformers.AutoProcessor.from_pretrained(
        base.repo_id, revision=base.revision, trust_remote_code=False)
    upstream_config = transformers.AutoConfig.from_pretrained(
        base.repo_id, revision=base.revision, trust_remote_code=False).to_dict()
    selected = experiment_config.foundation.profile("gemma4_e2b" if args.model == "secondary" else "gemma4_e4b")
    if (upstream_config.get("model_type") != selected["model_type"]
            or upstream_config.get("architectures") != selected["architectures"]
            or any(upstream_config.get("text_config", {}).get(k) != v for k, v in selected["text_config"].items())
            or type(processor).__name__ != selected["processor_class"]):
        print("REFUSED: incompatible Gemma 4 architecture/processor", file=sys.stderr)
        return EXIT_REFUSED
    tokenizer = processor.tokenizer

    max_length = int(opt["max_seq_length"]["value"])
    too_long = []
    for position, record in enumerate(records):
        encoded = tokenizer.apply_chat_template(record["prompt"] + record["completion"], tokenize=True, enable_thinking=False)
        # A list of ids, or a BatchEncoding when the installed version returns a dict.
        token_ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        if len(token_ids) > max_length:
            too_long.append((position, len(token_ids)))
    if too_long:
        print(f"REFUSED: {len(too_long)} record(s) exceed max_seq_length {max_length} and would be truncated "
              f"(first: record {too_long[0][0]}, {too_long[0][1]} tokens)", file=sys.stderr)
        return EXIT_REFUSED

    bnb_config = transformers.BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"]["value"],
        bnb_4bit_quant_type=quantization["bnb_4bit_quant_type"]["value"],
        bnb_4bit_use_double_quant=quantization["bnb_4bit_use_double_quant"]["value"],
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = loader.from_pretrained(
        base.repo_id,
        revision=base.revision,
        trust_remote_code=False,
        quantization_config=bnb_config,
        dtype=compute_dtype,
        device_map={"": 0},
    )

    linear_names = [
        name for name, module in model.named_modules()
        if isinstance(module, torch.nn.Linear) or type(module).__name__ in ("Linear4bit", "Linear8bitLt")
    ]
    included, excluded, missing = select_target_modules(linear_names, lora["target_modules"]["value"])
    if missing or not included:
        print(f"REFUSED: configured LoRA targets with no language-model layer: {missing or 'all'}", file=sys.stderr)
        return EXIT_REFUSED

    gradient_checkpointing = bool(opt["gradient_checkpointing"]["value"])
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=gradient_checkpointing)
    model = get_peft_model(model, LoraConfig(
        r=lora["r"]["value"],
        lora_alpha=lora["alpha"]["value"],
        lora_dropout=lora["dropout"]["value"],
        bias=lora["bias"]["value"],
        target_modules=included,
        task_type="CAUSAL_LM",
    ))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

    sft_args = SFTConfig(
        output_dir=str(out_dir / "trainer"),
        num_train_epochs=opt["num_train_epochs"]["value"],
        max_steps=args.max_steps if smoke else -1,
        per_device_train_batch_size=opt["per_device_train_batch_size"]["value"],
        gradient_accumulation_steps=opt["gradient_accumulation_steps"]["value"],
        learning_rate=opt["learning_rate"]["value"],
        lr_scheduler_type=opt["lr_scheduler"]["value"],
        warmup_ratio=opt["warmup_ratio"]["value"],
        optim=opt["optimizer"]["value"],
        gradient_checkpointing=gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=dtype_name == "bfloat16",
        fp16=dtype_name == "float16",
        max_length=max_length,
        completion_only_loss=opt["loss"]["value"] == "completion_only",
        seed=args.seed,
        data_seed=args.seed,
        logging_steps=10,
        save_strategy="no",
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        args=sft_args,
        train_dataset=Dataset.from_list(records),
        processing_class=tokenizer,
    )

    started = dt.datetime.now(dt.timezone.utc)
    clock = time.monotonic()
    trainer.train()
    elapsed = time.monotonic() - clock
    trainer.save_model(str(out_dir / "adapter"))

    record = {
        "schema_version": RUN_RECORD_VERSION,
        "config_id": config.id,
        "arm": config.arm,
        "config_path": str(Path(args.config)),
        "config_sha256": file_sha256(Path(args.config)),
        "sft_file": config.sft_file,
        "sft_sha256": file_sha256(sft_path),
        "records": len(records),
        "model_profile": "gemma4_e2b" if args.model == "secondary" else "gemma4_e4b",
        "base_model": {
            "role": args.model, "repo_id": base.repo_id, "revision": base.revision,
            "license": base.license, "loader": base.loader,
        },
        "seed": args.seed,
        "smoke": smoke,
        "max_steps": args.max_steps,
        "evaluate": not smoke,
        "compute_dtype": dtype_name,
        "compute_dtype_note": dtype_note,
        "lora_targets": {"included": len(included), "excluded_tower_layers": excluded},
        "trainable_parameters": trainable,
        "packages": {**installed, "torch": torch.__version__, "torch_cuda": torch.version.cuda},
        "python": platform.python_version(),
        "gpu": torch.cuda.get_device_name(0),
        "started_at": started.isoformat(),
        "wall_clock_seconds": round(elapsed, 1),
        "log_history": trainer.state.log_history,
        "status": "COMPLETED",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{config.id} seed {args.seed}: adapter saved to {out_dir / 'adapter'}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
