"""Turn validated benchmark examples into chat-format SFT records for Artemis.

Why a separate builder instead of exporting questions and answers directly:

* **Train exactly what is evaluated.** An adapter is scored through the
  evaluation runner's ``openai_compatible`` baseline. That baseline sends one
  system prompt and one seven-key JSON schema for both Artemis tasks, and it
  never tells the model which task it is answering
  (``waymaker_ai.evaluation.baselines.model.build_messages``,
  ``waymaker_ai.evaluation.predictions.model_output_schema``). This builder
  imports that prompt and that schema instead of defining its own. A different
  prompt or key set at training time would make an arm A vs arm B comparison
  measure the prompt change, not the adapter.
* **One record per question, every key labelled.** Because the model sees the
  same prompt for both tasks, one question has exactly one target object. A
  benchmark example labels only its own task's keys, so a question can be
  trained on only when the train split holds both its
  ``status_procedure_classification`` label and its ``entity_date_extraction``
  label, and the classification label states ``current_status``,
  ``target_status`` (null is allowed) and ``needs_clarification`` explicitly.
  A missing key is never filled with a guess: writing ``"dates": []`` for a
  question that names a date would teach the model to drop dates.
* **Labels, not facts.** Artemis is trained only on the classification suite.
  The target is the structured label object. No legal requirement, fee or
  period is ever a training target, because facts change with every manual
  edition and must stay in retrieval (research-notes/training-distill.md §0.6,
  §2.2).
* **Fail closed.** One bad example refuses the whole build. A partial training
  file that silently dropped the hard cases would look like a clean run.
* **Same gate for every source.** Human-authored and teacher-generated
  examples pass the same schema and review checks; teacher-generated ones also
  need a ``TeacherRecord`` that ``teacher_policy.gate_record`` accepts and whose
  output is exactly the label being trained.
* **Deterministic output.** The same inputs always serialise to the same bytes,
  so ``train_qlora.py`` can rebuild the file and refuse to train on anything
  that differs from what the gates passed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import compact
from waymaker_ai.dataset import schema as example_schema
# Manifest names and example suffixes: one definition, shared with the runner and the validator.
from waymaker_ai.dataset.layout import EXAMPLE_SUFFIXES, MANIFEST_NAMES
from waymaker_ai.dataset.tasks import SCHEMA_VERSION, TASK_EXPECTED_KEYS, TASK_SUITE
from waymaker_ai.distillation import leakage
from waymaker_ai.distillation.teacher_policy import (
    LEGAL_CONCLUSION_TASKS,
    TeacherPolicy,
    TeacherRecord,
    gate_record,
    hash_prompt,
)
from waymaker_ai.evaluation import predictions
from waymaker_ai.evaluation.baselines import model as runner_model

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]

#: Tasks Artemis may be trained on. Citation verification and temporal version
#: selection are owned by the deterministic WLIE gate; abstention is scored on
#: Athena's answers. None of them is an Artemis training target.
ARTEMIS_TASKS: Tuple[str, ...] = ("status_procedure_classification", "entity_date_extraction")
CLASSIFICATION_TASK, EXTRACTION_TASK = ARTEMIS_TASKS

SFT_RECORD_VERSION = "waymaker-artemis-sft/0.2"
#: v1 = the runner's openai_compatible request (messages, schema, decoding).
PROMPT_TEMPLATE_ID = "artemis-sft/v1"

#: Target key -> the task whose label supplies it. Every other key of the
#: runner's schema would have no label behind it, which eval_contract_problems
#: reports as a refusal.
TARGET_SOURCES: Dict[str, str] = {
    "status_code": CLASSIFICATION_TASK,
    "subcode": CLASSIFICATION_TASK,
    "procedure": CLASSIFICATION_TASK,
    "current_status": CLASSIFICATION_TASK,
    "target_status": CLASSIFICATION_TASK,
    "needs_clarification": CLASSIFICATION_TASK,
    "dates": EXTRACTION_TASK,
}

#: Optional classification keys a train label must still state, because the
#: runner's schema requires them in every answer.
EXPLICIT_CLASSIFICATION_KEYS: Tuple[str, ...] = ("current_status", "target_status", "needs_clarification")

#: The benchmark's own validator. Its command-line exit status is the contract:
#: 0 means every example in the given files passed.
VALIDATOR_MODULE = "waymaker_ai.dataset.validate"

Validator = Callable[[Sequence[Path]], Tuple[bool, str]]


# ---------------------------------------------------------------------------
# The evaluation contract the records are trained for
# ---------------------------------------------------------------------------
def canonical_sha256(value: Any) -> str:
    material = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def target_keys() -> Tuple[str, ...]:
    """Keys of the assistant target, in the order the runner's schema lists them."""
    return tuple(predictions.model_output_schema(CLASSIFICATION_TASK)["properties"])


def eval_contract_problems() -> List[str]:
    """Why one target per question no longer matches the runner (empty list = it matches).

    Pairing two labels into one target is valid only while the runner asks the
    same prompt and schema for both Artemis tasks, and while every schema key
    has a label behind it.
    """
    problems: List[str] = []
    if len({runner_model.system_prompt(task) for task in ARTEMIS_TASKS}) != 1:
        problems.append("the runner now sends a different system prompt per Artemis task; the pairing rule must be revisited")
    if len({canonical_sha256(predictions.model_output_schema(task)) for task in ARTEMIS_TASKS}) != 1:
        problems.append("the runner now uses a different output schema per Artemis task; the pairing rule must be revisited")
    unlabelled = sorted(set(target_keys()) - set(TARGET_SOURCES))
    if unlabelled:
        problems.append(f"the runner's schema asks for keys no label supplies: {unlabelled}")
    gone = sorted(set(TARGET_SOURCES) - set(target_keys()))
    if gone:
        problems.append(f"the runner's schema no longer has keys the builder trains: {gone}")
    return problems


def prompt_messages(example: Mapping[str, Any]) -> List[Dict[str, str]]:
    """The chat messages the runner sends for ``example`` (question and payload code only)."""
    return runner_model.build_messages(example)


def _canary(task: str, payload: Optional[str]) -> Dict[str, Any]:
    return {"task": task, "input": {"question": "<question>", "payload_status_code": payload}}


def prompt_sha256() -> str:
    """Identity of the evaluation contract: messages (with and without a payload code), schema and decoding.

    Recorded in every config, so a change to the runner's prompt, schema or
    decoding shows up as a config error instead of a silently different run.
    """
    material = {
        "template_id": PROMPT_TEMPLATE_ID,
        "messages": {
            task: [prompt_messages(_canary(task, None)), prompt_messages(_canary(task, "<payload_status_code>"))]
            for task in ARTEMIS_TASKS
        },
        "schema": {task: predictions.model_output_schema(task) for task in ARTEMIS_TASKS},
        "decoding": runner_model.DECODING,
    }
    return canonical_sha256(material)


def target_schema(task: str) -> Dict[str, Any]:
    """The JSON Schema used for constrained decoding at evaluation: the runner's, unchanged."""
    if task not in ARTEMIS_TASKS:
        raise ValueError(f"{task} is not an Artemis task")
    return predictions.model_output_schema(task)


# ---------------------------------------------------------------------------
# Question units: one question, both Artemis labels, one target
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class QuestionUnit:
    classification: Mapping[str, Any]
    extraction: Mapping[str, Any]

    @property
    def question(self) -> str:
        return str(self.classification["input"]["question"])

    @property
    def payload(self) -> Optional[str]:
        return self.classification["input"].get("payload_status_code") or None

    @property
    def examples(self) -> Tuple[Mapping[str, Any], Mapping[str, Any]]:
        return (self.classification, self.extraction)

    @property
    def example_ids(self) -> Tuple[str, str]:
        return (str(self.classification["id"]), str(self.extraction["id"]))


def unit_key(example: Mapping[str, Any]) -> Tuple[str, Optional[str]]:
    """What the model sees: the exact question text and the payload code."""
    raw_input = example["input"]
    return (str(raw_input["question"]), raw_input.get("payload_status_code") or None)


def target_object(unit: QuestionUnit) -> Dict[str, Any]:
    """The assistant turn as an object, keys in the runner's schema order."""
    labels = {CLASSIFICATION_TASK: unit.classification["expected"], EXTRACTION_TASK: unit.extraction["expected"]}
    target: Dict[str, Any] = {}
    for key in target_keys():
        value = labels[TARGET_SOURCES[key]][key]
        if key == "dates":
            value = [{"value": item["value"], "role": item["role"]} for item in value]
        target[key] = value
    return target


def target_json(unit: QuestionUnit) -> str:
    """Compact JSON, keys in schema order (constrained decoders emit properties in that order)."""
    return json.dumps(target_object(unit), ensure_ascii=False, separators=(",", ":"))


def to_record(
    unit: QuestionUnit,
    teacher_record_ids: Mapping[str, Optional[str]],
    template_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """One prompt/completion record in TRL's conversational prompt-completion format.

    ``question`` is repeated at the top level because the runner's
    ``--contamination-check`` reads it there.
    """
    prompt = prompt_messages(unit.classification)
    return {
        "schema_version": SFT_RECORD_VERSION,
        "question": unit.question,
        "prompt": prompt,
        "completion": [{"role": "assistant", "content": target_json(unit)}],
        "meta": {
            "example_ids": list(unit.example_ids),
            "language": unit.classification["language"],
            "payload_status_code": unit.payload,
            "critical": any(bool(example["critical"]) for example in unit.examples),
            "examples": [
                {
                    "id": example["id"],
                    "task": example["task"],
                    "authoring": example["provenance"]["authoring"],
                    "label_review": example["label_review"]["status"],
                    "example_sha256": canonical_sha256(example),
                    "teacher_record_id": teacher_record_ids.get(str(example["id"])),
                }
                for example in unit.examples
            ],
            "prompt_template": PROMPT_TEMPLATE_ID,
            "prompt_template_sha256": template_sha256 or prompt_sha256(),
            "prompt_sha256": hash_prompt(prompt),
        },
    }


def serialize(records: Sequence[Mapping[str, Any]]) -> str:
    """JSONL, one record per line, stable key order. The bytes train_qlora.py compares."""
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
class DatasetFileError(ValueError):
    pass


def load_examples(path: Path) -> List[Dict[str, Any]]:
    """Examples from a .jsonl file (one per line) or a .json file (a list, or {"examples": [...]})."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        examples: List[Dict[str, Any]] = []
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DatasetFileError(f"{path.name} line {number}: {exc}") from exc
        return examples
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DatasetFileError(f"{path.name}: {exc}") from exc
    if isinstance(data, Mapping) and isinstance(data.get("examples"), list):
        data = data["examples"]
    if not isinstance(data, list):
        raise DatasetFileError(f"{path.name}: expected a list of examples or {{\"examples\": [...]}}")
    return list(data)


def benchmark_files(benchmark_dir: Path) -> List[Path]:
    """Every file under ``benchmark_dir`` the evaluation runner reads examples from, in sorted order.

    The selection mirrors the runner's loader (waymaker_ai.evaluation.benchmark):
    every .json / .jsonl file at any depth except manifests and dotfiles. The
    guard must read at least what the runner scores: an eval file the guard
    skipped would be scored without ever having been compared with the train
    split.
    """
    directory = Path(benchmark_dir)
    if not directory.is_dir():
        return []
    return [
        path for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix in EXAMPLE_SUFFIXES
        and path.name not in MANIFEST_NAMES and not path.name.startswith(".")
    ]


def _benchmark_file_examples(path: Path) -> List[Any]:
    """Examples in one benchmark file, read the way the runner reads them.

    A .json object that is not an example container (a source bundle, a split
    index) holds no examples, as in the runner. Unparseable JSON raises
    DatasetFileError: an unreadable eval file is a refusal, never a skip.
    """
    if path.suffix == ".jsonl":
        return load_examples(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetFileError(f"{path.name}: {exc}") from exc
    if isinstance(data, Mapping) and isinstance(data.get("examples"), list):
        data = data["examples"]
    return list(data) if isinstance(data, list) else []


def load_eval_examples(benchmark_dir: Path, splits: Sequence[str] = leakage.EVAL_SPLITS) -> List[Dict[str, Any]]:
    """Every example under ``benchmark_dir`` whose ``split`` is an evaluation split.

    Files are found by content, not by name, so a renamed split file cannot hide
    from the leakage guard.
    """
    found: List[Dict[str, Any]] = []
    for path in benchmark_files(benchmark_dir):
        for example in _benchmark_file_examples(path):
            if isinstance(example, Mapping) and example.get("split") in splits:
                found.append(dict(example))
    return found


def run_dataset_validator(paths: Sequence[Path], *, timeout: int = 600) -> Tuple[bool, str]:
    """Run the benchmark's validator on ``paths`` as a subprocess. Exit status 0 is the only pass.

    Passing the benchmark directory together with the train file also runs the
    validator's own cross-split rules (its character-3-gram contamination check
    between train and every eval split). A missing validator is a refusal,
    never a skip: without it nobody has shown the file meets the dataset rules.
    """
    if str(EXPERIMENT_ROOT) not in sys.path:
        sys.path.insert(0, str(EXPERIMENT_ROOT))
    try:
        spec = importlib.util.find_spec(VALIDATOR_MODULE)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        return False, f"{VALIDATOR_MODULE} is not available in this tree, so the file cannot be validated"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(EXPERIMENT_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-m", VALIDATOR_MODULE, *[str(path) for path in paths]],
            cwd=str(EXPERIMENT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"validator did not complete: {exc}"
    tail = "\n".join((completed.stdout + completed.stderr).strip().splitlines()[-20:])
    return completed.returncode == 0, tail


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Refusal:
    example_id: str
    reason: str

    def describe(self) -> str:
        return f"{self.example_id}: {self.reason}"


@dataclass
class BuildResult:
    records: List[Dict[str, Any]] = field(default_factory=list)
    refusals: List[Refusal] = field(default_factory=list)
    overlaps: List[leakage.Overlap] = field(default_factory=list)
    train_count: int = 0
    eval_count: int = 0

    @property
    def empty(self) -> bool:
        return self.train_count == 0

    @property
    def ok(self) -> bool:
        return not self.refusals and not self.empty and bool(self.records)

    def text(self) -> str:
        return serialize(self.records) if self.ok else ""


def structure_problems(
    example: Mapping[str, Any], schema: Mapping[str, Any], allowed_tasks: Sequence[str]
) -> List[str]:
    """Schema, task-key and split checks. Everything the label itself must satisfy."""
    problems = [
        f"schema: {example_schema.describe_path(v.path)} {v.message}"
        for v in example_schema.validate_instance(example, schema)
    ]
    if problems:
        return problems
    task = example["task"]
    if example["schema_version"] != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    if TASK_SUITE[task] != example["suite"]:
        problems.append(f"task {task} belongs to suite {TASK_SUITE[task]}, not {example['suite']}")
    if task not in allowed_tasks:
        owner = "the deterministic WLIE gate" if task in LEGAL_CONCLUSION_TASKS else "another component"
        problems.append(f"task {task} is not an Artemis training task ({owner} owns it)")
    required, optional = TASK_EXPECTED_KEYS[task]
    keys = set(example["expected"])
    if required - keys:
        problems.append(f"expected lacks {sorted(required - keys)}")
    if keys - required - optional:
        problems.append(f"expected has keys outside the {task} label schema {sorted(keys - required - optional)}")
    if example["split"] != "train":
        problems.append(f"split is {example['split']!r}; only 'train' examples may be trained on")
    return problems


def review_problems(example: Mapping[str, Any]) -> List[str]:
    """Label review gate. Critical labels need a named human reviewer; nothing unreviewed is trained."""
    review = example["label_review"]
    status = review["status"]
    if status == "disputed":
        return ["label is disputed"]
    if status == "unreviewed":
        return ["label is unreviewed"]
    problems: List[str] = []
    if example["critical"] and status != "human_verified":
        problems.append(f"critical example has label_review {status!r}; 'human_verified' is required")
    if status == "human_verified" and (not review.get("reviewer") or not review.get("reviewed_at")):
        problems.append("human_verified label must name the reviewer and the review date")
    if status == "machine_checked" and not review.get("checks"):
        problems.append("machine_checked label must list the checks that ran")
    return problems


def teacher_problems(
    example: Mapping[str, Any],
    records_by_example: Mapping[str, Sequence[TeacherRecord]],
    policy: Optional[TeacherPolicy],
    allow_teacher_generated: bool,
) -> Tuple[List[str], Optional[str]]:
    """Teacher gate for teacher_generated examples. Returns (problems, accepted record id)."""
    provenance = example["provenance"]
    if provenance["authoring"] != "teacher_generated":
        return [], None
    if not allow_teacher_generated:
        return ["teacher_generated examples are not allowed in this experiment arm"], None
    declared = provenance.get("teacher")
    if not isinstance(declared, Mapping) or declared.get("permitted") is not True:
        return ["provenance.teacher must name the teacher and say permitted: true"], None
    records = list(records_by_example.get(str(example["id"]), ()))
    if len(records) != 1:
        return [f"needs exactly one teacher record in the ledger, found {len(records)}"], None
    record = records[0]
    problems: List[str] = []
    if (record.teacher.provider, record.teacher.model) != (declared.get("provider"), declared.get("model")):
        problems.append("teacher record and provenance.teacher name different teachers")
    if record.task != example["task"]:
        problems.append("teacher record is for a different task")
    if canonical_sha256(dict(record.output)) != canonical_sha256(dict(example["expected"])):
        problems.append("expected is not exactly the gated teacher output")
    gate = gate_record(record, policy)
    if not gate.accepted:
        problems.extend(f"teacher gate: {reason}" for reason in gate.reasons)
    return problems, (record.record_id if not problems else None)


def pair_examples(examples: Sequence[Mapping[str, Any]]) -> Tuple[List[QuestionUnit], List[Refusal]]:
    """Group structurally valid Artemis examples into question units, in input order."""
    groups: Dict[Tuple[str, Optional[str]], Dict[str, List[Mapping[str, Any]]]] = {}
    for example in examples:
        members = groups.setdefault(unit_key(example), {task: [] for task in ARTEMIS_TASKS})
        members[example["task"]].append(example)

    units: List[QuestionUnit] = []
    refusals: List[Refusal] = []
    for (_question, payload), members in groups.items():
        ids = [str(e["id"]) for task in ARTEMIS_TASKS for e in members[task]]
        where = f" (payload_status_code {payload})" if payload else ""
        problems: List[str] = []
        for task in ARTEMIS_TASKS:
            if not members[task]:
                problems.append(
                    f"no {task} label for this exact question{where}: the runner asks one prompt for both Artemis "
                    "tasks, so every train question needs both labels"
                )
            elif len(members[task]) > 1:
                problems.append(f"{len(members[task])} {task} labels for the same question{where}: {ids}")
        if problems:
            refusals.extend(Refusal(ids[0], problem) for problem in problems)
            continue
        classification, extraction = members[CLASSIFICATION_TASK][0], members[EXTRACTION_TASK][0]
        unit_problems = _unit_label_problems(classification, extraction)
        if unit_problems:
            refusals.extend(Refusal(str(classification["id"]), problem) for problem in unit_problems)
            continue
        units.append(QuestionUnit(classification, extraction))
    return units, refusals


def _unit_label_problems(classification: Mapping[str, Any], extraction: Mapping[str, Any]) -> List[str]:
    problems: List[str] = []
    expected = classification["expected"]
    missing = [key for key in EXPLICIT_CLASSIFICATION_KEYS if key not in expected]
    if missing:
        problems.append(
            f"classification label must state {missing} explicitly (null is allowed for the statuses): "
            "the runner's schema asks for every key, and an unstated key would have to be guessed"
        )
    if "needs_clarification" in expected and not isinstance(expected["needs_clarification"], bool):
        problems.append("needs_clarification must be true or false")
    dates = extraction["expected"].get("dates")
    if not isinstance(dates, list) or not all(isinstance(d, Mapping) and "value" in d and "role" in d for d in dates):
        problems.append(f"{extraction['id']}: dates must be a list of {{value, role}} objects")
    if classification["language"] != extraction["language"]:
        problems.append(f"the two labels of one question disagree on language ({classification['language']} vs {extraction['language']})")
    return problems


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_records(
    train_examples: Sequence[Mapping[str, Any]],
    eval_examples: Sequence[Mapping[str, Any]],
    *,
    allowed_tasks: Sequence[str] = ARTEMIS_TASKS,
    teacher_records: Iterable[TeacherRecord] = (),
    policy: Optional[TeacherPolicy] = None,
    allow_teacher_generated: bool = False,
    ngram: int = leakage.DEFAULT_NGRAM,
    max_overlap: float = leakage.DEFAULT_MAX_OVERLAP,
    schema: Optional[Mapping[str, Any]] = None,
) -> BuildResult:
    """Check every example, pair them into question units, then build records.

    Any refusal means no record is usable (``BuildResult.text()`` is empty).
    """
    active_schema = schema if schema is not None else example_schema.load_schema()
    result = BuildResult(train_count=len(train_examples), eval_count=len(eval_examples))
    if result.empty:
        return result
    contract_problems = eval_contract_problems()
    if contract_problems:
        # Nothing can be built: a target would not match what the runner asks.
        result.refusals.extend(Refusal("(evaluation contract)", p) for p in contract_problems)
        return result
    if not eval_examples:
        result.refusals.append(Refusal("(dataset)", "no evaluation examples found: disjointness cannot be shown"))

    records_by_example: Dict[str, List[TeacherRecord]] = {}
    for record in teacher_records:
        records_by_example.setdefault(record.example_id, []).append(record)

    seen_ids: Dict[str, int] = {}
    eval_ids = {str(example.get("id")) for example in eval_examples}
    well_formed: List[Mapping[str, Any]] = []
    teacher_record_ids: Dict[str, Optional[str]] = {}
    for example in train_examples:
        if not isinstance(example, Mapping):
            result.refusals.append(Refusal("(not an object)", "example must be a JSON object"))
            continue
        example_id = str(example.get("id"))
        seen_ids[example_id] = seen_ids.get(example_id, 0) + 1
        if example_id in eval_ids:
            result.refusals.append(Refusal(example_id, "id is also used by an evaluation example"))
        problems = structure_problems(example, active_schema, allowed_tasks)
        if not problems and example["task"] not in ARTEMIS_TASKS:
            problems.append(f"task {example['task']} has no place in an Artemis target")
        if problems:
            result.refusals.extend(Refusal(example_id, p) for p in problems)
            continue
        well_formed.append(example)
        problems = review_problems(example)
        teacher_issues, teacher_record_id = teacher_problems(
            example, records_by_example, policy, allow_teacher_generated
        )
        problems.extend(teacher_issues)
        result.refusals.extend(Refusal(example_id, p) for p in problems)
        teacher_record_ids[example_id] = teacher_record_id

    for example_id, count in sorted(seen_ids.items()):
        if count > 1:
            result.refusals.append(Refusal(example_id, f"id appears {count} times in the train file"))

    units, unit_refusals = pair_examples(well_formed)
    result.refusals.extend(unit_refusals)
    _refuse_normalised_duplicates(units, result)
    template_sha256 = prompt_sha256()
    result.records = [to_record(unit, teacher_record_ids, template_sha256) for unit in units]
    _refuse_leaks(train_examples, eval_examples, result, ngram=ngram, max_overlap=max_overlap)
    return result


def _refuse_normalised_duplicates(units: Sequence[QuestionUnit], result: BuildResult) -> None:
    """Two units whose questions differ only in spacing or case are one question twice."""
    first_seen: Dict[Tuple[str, Optional[str]], str] = {}
    for unit in units:
        key = (compact(unit.question).lower(), unit.payload)
        anchor = unit.example_ids[0]
        if key in first_seen:
            result.refusals.append(Refusal(anchor, f"same question as {first_seen[key]} after normalisation"))
        else:
            first_seen[key] = anchor


def _refuse_leaks(
    train_examples: Sequence[Mapping[str, Any]],
    eval_examples: Sequence[Mapping[str, Any]],
    result: BuildResult,
    *,
    ngram: int,
    max_overlap: float,
) -> None:
    train_items = leakage.items_from_examples(e for e in train_examples if isinstance(e, Mapping))
    eval_items = leakage.items_from_examples(eval_examples)
    result.overlaps = leakage.find_overlaps(train_items, eval_items, n=ngram, max_overlap=max_overlap)
    for overlap in result.overlaps:
        result.refusals.append(Refusal(overlap.train_id, f"leaks into evaluation: {overlap.describe()}"))
