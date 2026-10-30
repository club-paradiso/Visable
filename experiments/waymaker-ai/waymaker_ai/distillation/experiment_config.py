"""Load and check the Artemis experiment configs (configs/artemis/*.json).

Why configs are validated in code: an experiment config is the record of what
was supposed to run. If the base-model revision, the licence or the eval split
list can silently drift, a later result cannot be tied to the hypothesis it
was meant to test. The loader therefore rejects unknown keys, insists on a
one-line justification for every hyper-parameter, checks that the prompt hash
in the config matches the evaluation runner's prompt, schema and decoding (the
contract the SFT builder trains for), and refuses decoding values that
contradict the runner's.

``training_blockers`` is separate from parsing on purpose: a config may
legitimately describe something that must not run yet (an unpinned revision,
an empty train split). Parsing says "this is a well-formed plan";
``training_blockers`` says "this plan may start now", and in Mission 001 the
answer is always no for at least one reason.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.distillation import leakage, sft_dataset
from waymaker_ai import foundation
from waymaker_ai.distillation.teacher_policy import is_pinned_revision

CONFIG_SCHEMA_VERSION = "waymaker-artemis-experiment/0.1"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = EXPERIMENT_ROOT / "configs" / "artemis"

#: Placeholder a config uses when the notes recorded no revision SHA.
REVISION_REQUIRED = "REVISION_REQUIRED"

#: Base-model licences a training run may start from. Apache-2.0 and MIT carry
#: no field-of-use restriction or derivative-naming duty
#: (research-notes/models.md §4). Anything else needs a person to decide.
ALLOWED_BASE_LICENSES: Tuple[str, ...] = ("apache-2.0", "mit")

STATUSES: Tuple[str, ...] = ("NOT RUN", "IN PROGRESS", "COMPLETED", "ABANDONED")
ARMS: Tuple[str, ...] = ("A", "B", "C")
TRAIN_DATA_STATES: Tuple[str, ...] = ("EMPTY", "BUILT")

_TOP_LEVEL_KEYS = frozenset({
    "schema_version", "id", "arm", "title", "status", "status_detail", "created", "hypothesis",
    "null_hypothesis", "baselines", "base_model", "secondary_model", "dataset", "prompt", "training",
    "teachers", "hardware", "compute", "cost", "evaluation", "gates", "references", "limitations",
})
_REQUIRED_KEYS = _TOP_LEVEL_KEYS - {"secondary_model", "teachers", "references", "limitations", "status_detail"}

#: Hyper-parameters every QLoRA arm must state, by section.
REQUIRED_HYPERPARAMETERS: Dict[str, Tuple[str, ...]] = {
    "quantization": ("load_in_4bit", "bnb_4bit_quant_type", "bnb_4bit_use_double_quant", "compute_dtype"),
    "lora": ("r", "alpha", "dropout", "target_modules", "bias"),
    "optimization": (
        "learning_rate", "num_train_epochs", "max_seq_length", "per_device_train_batch_size",
        "gradient_accumulation_steps", "optimizer", "lr_scheduler", "warmup_ratio",
        "gradient_checkpointing", "loss", "seeds",
    ),
}


class ConfigError(ValueError):
    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("invalid Artemis experiment config: " + "; ".join(self.problems))


@dataclass(frozen=True)
class BaseModel:
    role: str
    repo_id: str
    revision: str
    license: str
    gated: bool
    loader: str

    @property
    def revision_pinned(self) -> bool:
        return is_pinned_revision(self.revision)


@dataclass(frozen=True)
class ExperimentConfig:
    path: Optional[Path]
    data: Mapping[str, Any]
    id: str
    arm: str
    status: str
    base_model: BaseModel
    secondary_model: Optional[BaseModel]
    tasks: Tuple[str, ...]
    train_state: str
    train_examples_file: str
    sft_file: str
    teacher_records_file: Optional[str]
    allow_teacher_generated: bool
    benchmark_dir: str
    eval_splits: Tuple[str, ...]
    ngram: int
    max_overlap: float
    paid_endpoint: bool
    managed_finetuning: Optional[str]

    @property
    def training(self) -> Optional[Mapping[str, Any]]:
        return self.data.get("training")

    def hyperparameter(self, section: str, name: str) -> Any:
        """The ``value`` of one hyper-parameter, e.g. hyperparameter('lora', 'r')."""
        training = self.training or {}
        return training[section][name]["value"]

    def resolve(self, relative: str) -> Path:
        """A path from the config: absolute as written, otherwise relative to the experiment root."""
        candidate = Path(relative)
        return candidate if candidate.is_absolute() else EXPERIMENT_ROOT / candidate


def config_paths() -> List[Path]:
    return sorted(CONFIG_DIR.glob("*.json"))


def load_config(path: Path) -> ExperimentConfig:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError([f"{path.name} is not valid JSON: {exc}"]) from exc
    return parse_config(data, path)


def parse_config(data: Any, path: Optional[Path] = None) -> ExperimentConfig:
    """Validate a config dict. Raises ConfigError listing every problem found."""
    if not isinstance(data, Mapping):
        raise ConfigError(["config must be a JSON object"])
    problems: List[str] = []
    problems.extend(f"unknown key {key!r}" for key in sorted(set(data) - _TOP_LEVEL_KEYS))
    problems.extend(f"missing key {key!r}" for key in sorted(_REQUIRED_KEYS - set(data)))
    if problems:
        raise ConfigError(problems)

    if data["schema_version"] != CONFIG_SCHEMA_VERSION:
        problems.append(f"schema_version must be {CONFIG_SCHEMA_VERSION!r}")
    arm = data["arm"]
    if arm not in ARMS:
        problems.append(f"arm must be one of {ARMS}")
    if data["status"] not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")
    for name in ("id", "title", "created", "hypothesis", "null_hypothesis"):
        if not isinstance(data.get(name), str) or not data.get(name):
            problems.append(f"{name} must be a non-empty string")

    base_model, model_problems = _parse_model(data["base_model"], "base_model")
    problems.extend(model_problems)
    secondary: Optional[BaseModel] = None
    if data.get("secondary_model") is not None:
        secondary, secondary_problems = _parse_model(data["secondary_model"], "secondary_model")
        problems.extend(secondary_problems)

    dataset, dataset_problems = _parse_dataset(data["dataset"], arm)
    problems.extend(dataset_problems)
    problems.extend(_prompt_problems(data["prompt"]))
    problems.extend(_training_problems(data["training"], arm))
    problems.extend(_teacher_problems(data.get("teachers"), arm))
    problems.extend(_evaluation_problems(data["evaluation"]))
    problems.extend(_gate_problems(data["gates"]))
    problems.extend(_cost_problems(data["cost"]))
    compute = data["compute"]
    if not isinstance(compute, Mapping) or not isinstance(compute.get("paid_endpoint"), bool):
        problems.append("compute.paid_endpoint must be true or false")
        compute = {"paid_endpoint": True, "managed_finetuning": None}
    if not isinstance(data["baselines"], list) or not data["baselines"]:
        problems.append("baselines must be a non-empty list")
    if not isinstance(data["hardware"], Mapping) or not data["hardware"].get("assumption"):
        problems.append("hardware.assumption must describe the GPU this plan assumes")

    if problems or base_model is None or dataset is None:
        raise ConfigError(problems)
    return ExperimentConfig(
        path=path,
        data=data,
        id=data["id"],
        arm=arm,
        status=data["status"],
        base_model=base_model,
        secondary_model=secondary,
        tasks=tuple(dataset["tasks"]),
        train_state=dataset["train"]["status"],
        train_examples_file=dataset["train"]["examples_file"],
        sft_file=dataset["train"]["sft_file"],
        teacher_records_file=dataset["train"].get("teacher_records_file"),
        allow_teacher_generated=dataset["train"]["allow_teacher_generated"],
        benchmark_dir=dataset["benchmark_dir"],
        eval_splits=tuple(dataset["eval_splits"]),
        ngram=dataset["leakage_guard"]["ngram"],
        max_overlap=dataset["leakage_guard"]["max_overlap"],
        paid_endpoint=compute["paid_endpoint"],
        managed_finetuning=compute.get("managed_finetuning"),
    )


def _parse_model(raw: Any, where: str) -> Tuple[Optional[BaseModel], List[str]]:
    if not isinstance(raw, Mapping):
        return None, [f"{where} must be an object"]
    problems: List[str] = []
    for name in ("role", "repo_id", "revision", "license", "loader", "source"):
        if not isinstance(raw.get(name), str) or not raw.get(name):
            problems.append(f"{where}.{name} must be a non-empty string")
    repo_id = raw.get("repo_id") or ""
    if repo_id.count("/") != 1 or ":" in repo_id:
        problems.append(f"{where}.repo_id must be an exact Hugging Face repo id 'org/name'")
    revision = raw.get("revision")
    selected = foundation.profile("gemma4_e2b" if where == "secondary_model" else "gemma4_e4b")
    if repo_id != selected["upstream"]:
        problems.append(f"{where}.repo_id must match the canonical Gemma 4 profile")
    if revision not in (selected["upstream_revision"], REVISION_REQUIRED):
        problems.append(f"{where}.revision differs from the audited foundation revision")
    if raw.get("loader") != "AutoModelForImageTextToText":
        problems.append(f"{where}.loader must support Gemma4ForConditionalGeneration")
    if revision != REVISION_REQUIRED and not is_pinned_revision(revision):
        problems.append(f"{where}.revision must be a 40-character commit SHA or {REVISION_REQUIRED!r}")
    if not isinstance(raw.get("gated"), bool):
        problems.append(f"{where}.gated must be true or false")
    if problems:
        return None, problems
    return BaseModel(
        role=raw["role"],
        repo_id=repo_id,
        revision=revision,
        license=raw["license"],
        gated=raw["gated"],
        loader=raw["loader"],
    ), []


def _parse_dataset(raw: Any, arm: str) -> Tuple[Optional[Mapping[str, Any]], List[str]]:
    if not isinstance(raw, Mapping):
        return None, ["dataset must be an object"]
    problems: List[str] = []
    tasks = raw.get("tasks")
    if tasks != list(sft_dataset.ARTEMIS_TASKS):
        problems.append(
            f"dataset.tasks must be exactly {list(sft_dataset.ARTEMIS_TASKS)}: the runner asks one prompt for both "
            "Artemis tasks, so every train question carries both labels"
        )
    if raw.get("eval_splits") != list(leakage.EVAL_SPLITS):
        problems.append(f"dataset.eval_splits must be exactly {list(leakage.EVAL_SPLITS)}")
    if not isinstance(raw.get("benchmark_dir"), str) or not raw.get("benchmark_dir"):
        problems.append("dataset.benchmark_dir must be a path")
    train = raw.get("train")
    if not isinstance(train, Mapping):
        problems.append("dataset.train must be an object")
    else:
        if train.get("status") not in TRAIN_DATA_STATES:
            problems.append(f"dataset.train.status must be one of {TRAIN_DATA_STATES}")
        for name in ("examples_file", "sft_file", "builder", "note"):
            if not isinstance(train.get(name), str) or not train.get(name):
                problems.append(f"dataset.train.{name} must be a non-empty string")
        if not isinstance(train.get("allow_teacher_generated"), bool):
            problems.append("dataset.train.allow_teacher_generated must be true or false")
        elif train["allow_teacher_generated"] and arm != "C":
            problems.append("only arm C may train on teacher_generated examples")
        if arm == "C" and not train.get("teacher_records_file"):
            problems.append("arm C needs dataset.train.teacher_records_file (the teacher ledger)")
    guard = raw.get("leakage_guard")
    if not isinstance(guard, Mapping):
        problems.append("dataset.leakage_guard must be an object")
    else:
        ngram = guard.get("ngram")
        overlap = guard.get("max_overlap")
        if not isinstance(ngram, int) or isinstance(ngram, bool) or ngram < 1:
            problems.append("dataset.leakage_guard.ngram must be a positive integer")
        if not isinstance(overlap, (int, float)) or isinstance(overlap, bool) or not 0 < overlap <= 1:
            problems.append("dataset.leakage_guard.max_overlap must be in (0, 1]")
        if not guard.get("why"):
            problems.append("dataset.leakage_guard.why must justify the threshold")
    return (raw if not problems else None), problems


def _prompt_problems(raw: Any) -> List[str]:
    if not isinstance(raw, Mapping):
        return ["prompt must be an object"]
    problems: List[str] = []
    if raw.get("template_id") != sft_dataset.PROMPT_TEMPLATE_ID:
        problems.append(f"prompt.template_id must be {sft_dataset.PROMPT_TEMPLATE_ID!r}")
    if raw.get("sha256") != sft_dataset.prompt_sha256():
        problems.append(
            "prompt.sha256 does not match the runner's openai_compatible prompt, schema and decoding "
            "(the prompt drifted; see sft_dataset.prompt_sha256)"
        )
    return problems


def _hyperparameter_problems(section: Any, name: str, keys: Sequence[str]) -> List[str]:
    if not isinstance(section, Mapping):
        return [f"training.{name} must be an object"]
    problems: List[str] = []
    for key in keys:
        entry = section.get(key)
        if not isinstance(entry, Mapping) or "value" not in entry:
            problems.append(f"training.{name}.{key} must be {{value, why}}")
        elif not isinstance(entry.get("why"), str) or not entry["why"].strip():
            problems.append(f"training.{name}.{key} needs a one-line justification in 'why'")
    return problems


def _training_problems(raw: Any, arm: str) -> List[str]:
    if arm == "A":
        return [] if raw is None else ["arm A is the untuned control: training must be null"]
    if not isinstance(raw, Mapping):
        return [f"arm {arm} needs a training section"]
    problems: List[str] = []
    if raw.get("method") != "qlora":
        problems.append("training.method must be 'qlora'")
    for section, keys in REQUIRED_HYPERPARAMETERS.items():
        problems.extend(_hyperparameter_problems(raw.get(section), section, keys))
    if problems:
        return problems
    quantization = raw["quantization"]
    if quantization["load_in_4bit"]["value"] is not True or quantization["bnb_4bit_quant_type"]["value"] != "nf4":
        problems.append("QLoRA here means a 4-bit NF4 base: load_in_4bit true, bnb_4bit_quant_type 'nf4'")
    if quantization["compute_dtype"]["value"] not in ("auto", "float16", "bfloat16"):
        problems.append("training.quantization.compute_dtype must be auto, float16 or bfloat16")
    modules = raw["lora"]["target_modules"]["value"]
    if not isinstance(modules, list) or not modules or not all(isinstance(m, str) and m for m in modules):
        problems.append("training.lora.target_modules must be a non-empty list of module names")
    seeds = raw["optimization"]["seeds"]["value"]
    if not isinstance(seeds, list) or len(seeds) < 3:
        problems.append("training.optimization.seeds must list at least 3 seeds (training-distill.md §4.2)")
    return problems


def _teacher_problems(raw: Any, arm: str) -> List[str]:
    if arm != "C":
        return [] if raw in (None, []) else ["only arm C lists teachers"]
    if not isinstance(raw, list) or not raw:
        return ["arm C must list its teachers"]
    problems: List[str] = []
    for position, teacher in enumerate(raw):
        where = f"teachers[{position}]"
        if not isinstance(teacher, Mapping):
            problems.append(f"{where} must be an object")
            continue
        for name in ("policy_entry", "provider", "model", "channel", "revision"):
            if not isinstance(teacher.get(name), str) or not teacher.get(name):
                problems.append(f"{where}.{name} must be a non-empty string")
        revision = teacher.get("revision")
        if revision != REVISION_REQUIRED and not is_pinned_revision(revision):
            problems.append(f"{where}.revision must be a 40-character commit SHA or {REVISION_REQUIRED!r}")
    return problems


def _evaluation_problems(raw: Any) -> List[str]:
    if not isinstance(raw, Mapping):
        return ["evaluation must be an object"]
    problems: List[str] = []
    if raw.get("splits") != list(leakage.EVAL_SPLITS):
        problems.append(f"evaluation.splits must be exactly {list(leakage.EVAL_SPLITS)}")
    if raw.get("baseline_kind") != "openai_compatible":
        problems.append("evaluation.baseline_kind must be 'openai_compatible' (the runner baseline that calls a served model)")
    if not isinstance(raw.get("metrics"), list) or not raw.get("metrics"):
        problems.append("evaluation.metrics must be a non-empty list")
    decoding = raw.get("decoding")
    if not isinstance(decoding, Mapping):
        problems.append("evaluation.decoding must be an object")
    else:
        # The config restates the runner's decoding so a reader sees it; it may not contradict it.
        for key, value in sft_dataset.runner_model.DECODING.items():
            if decoding.get(key) != value:
                problems.append(f"evaluation.decoding.{key} must be {value!r}, the runner's openai_compatible setting")
        if decoding.get("constrained_json") is not True:
            problems.append("evaluation.decoding.constrained_json must be true")
    return problems


def _gate_problems(raw: Any) -> List[str]:
    if not isinstance(raw, list) or not raw:
        return ["gates must be a non-empty list"]
    problems: List[str] = []
    for position, gate in enumerate(raw):
        if not isinstance(gate, Mapping):
            problems.append(f"gates[{position}] must be an object")
            continue
        for name in ("id", "condition", "source", "on_fail"):
            if not isinstance(gate.get(name), str) or not gate.get(name):
                problems.append(f"gates[{position}].{name} must be a non-empty string")
        applies = gate.get("applies_to")
        if not isinstance(applies, list) or not applies or any(a not in ARMS for a in applies):
            problems.append(f"gates[{position}].applies_to must list arms from {ARMS}")
    return problems


def _cost_problems(raw: Any) -> List[str]:
    if not isinstance(raw, Mapping):
        return ["cost must be an object"]
    problems: List[str] = []
    if raw.get("paid_runs_authorised") is not False:
        problems.append("cost.paid_runs_authorised must be false: paid training is not authorised in Mission 001")
    if not isinstance(raw.get("sources"), list) or not raw.get("sources"):
        problems.append("cost.sources must cite where each price came from")
    return problems


# ---------------------------------------------------------------------------
# May this plan start?
# ---------------------------------------------------------------------------
def model_blockers(model: BaseModel) -> List[str]:
    problems: List[str] = []
    if not model.revision_pinned:
        problems.append(
            f"{model.repo_id}: revision is {model.revision!r}; pin the 40-character SHA before any run"
        )
    if model.license not in ALLOWED_BASE_LICENSES:
        problems.append(f"{model.repo_id}: licence {model.license!r} is not in the allow-list {ALLOWED_BASE_LICENSES}")
    if model.gated:
        problems.append(f"{model.repo_id}: gated weights need a credential; this runbook never handles tokens")
    return problems


def training_blockers(config: ExperimentConfig, *, paid_endpoint_flag: bool = False) -> List[str]:
    """Reasons this config may not start a training run (empty list = no config-level blocker)."""
    problems: List[str] = []
    if config.arm == "A" or config.training is None:
        problems.append("arm A is the untuned control: there is nothing to train")
    if config.status in ("COMPLETED", "ABANDONED"):
        problems.append(f"config status is {config.status}; start a new experiment id instead of re-running it")
    if paid_endpoint_flag or config.paid_endpoint:
        problems.append("paid endpoints are refused: paid training is not authorised (Mission 001)")
    if config.managed_finetuning:
        problems.append(f"managed fine-tuning ({config.managed_finetuning}) is a paid endpoint and is refused")
    problems.extend(model_blockers(config.base_model))
    return problems
