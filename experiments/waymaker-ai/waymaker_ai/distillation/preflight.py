"""Everything a training run must pass before any GPU library is imported.

Why one function: ``train_qlora.py`` and ``build_sft_dataset.py`` both need
the same answer to "is this train split usable?", and a test must be able to
ask it without torch. The checks, in order:

1. config-level blockers (``experiment_config.training_blockers``): untuned arm,
   paid endpoint, licence allow-list, unpinned revision, gated weights;
2. for arm C, the teacher policy: every configured teacher permitted by the
   recorded terms, and counsel sign-off recorded;
3. data: the benchmark validator passes on the train file read together with
   the benchmark directory (so its own train/eval contamination rule runs too),
   every example passes the SFT gates (schema, review, teacher gate, Artemis
   task list, both labels for every question), nothing overlaps dev / test /
   adversarial_holdout above the word 3-gram threshold, and the SFT file on
   disk is byte-identical to a fresh build.

Every check reports; none stops the others, so one run of ``--check-only``
lists everything that has to be fixed.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from waymaker_ai.distillation import sft_dataset
from waymaker_ai.distillation.experiment_config import ExperimentConfig, training_blockers
from waymaker_ai.distillation.teacher_policy import (
    RecordError,
    TeacherPolicy,
    TeacherRecord,
    default_policy,
    is_pinned_revision,
    load_teacher_records,
)


def build_from_config(
    config: ExperimentConfig,
    *,
    validator: sft_dataset.Validator = sft_dataset.run_dataset_validator,
    policy: Optional[TeacherPolicy] = None,
) -> Tuple[Optional[sft_dataset.BuildResult], List[str]]:
    """Validate and build the config's train split. Returns (result, problems)."""
    train_path = config.resolve(config.train_examples_file)
    if not train_path.is_file():
        note = ""
        if config.train_state == "EMPTY":
            note = " (the config records the train split as EMPTY: benchmark v0 has no train split)"
        return None, [f"train examples file {config.train_examples_file} does not exist{note}"]

    benchmark_dir = config.resolve(config.benchmark_dir)
    validated = [train_path] + ([benchmark_dir] if benchmark_dir.is_dir() else [])
    passed, detail = validator(validated)
    if not passed:
        scope = " together with the benchmark" if len(validated) > 1 else ""
        return None, [f"dataset validator did not pass on {config.train_examples_file}{scope}: {detail}"]

    try:
        train_examples = sft_dataset.load_examples(train_path)
        eval_examples = sft_dataset.load_eval_examples(config.resolve(config.benchmark_dir), config.eval_splits)
    except sft_dataset.DatasetFileError as exc:
        return None, [str(exc)]

    teacher_records: List[TeacherRecord] = []
    problems: List[str] = []
    if config.allow_teacher_generated and config.teacher_records_file:
        ledger = config.resolve(config.teacher_records_file)
        if ledger.is_file():
            try:
                teacher_records = load_teacher_records(ledger)
            except RecordError as exc:
                problems.append(str(exc))

    result = sft_dataset.build_records(
        train_examples,
        eval_examples,
        allowed_tasks=config.tasks,
        teacher_records=teacher_records,
        policy=policy,
        allow_teacher_generated=config.allow_teacher_generated,
        ngram=config.ngram,
        max_overlap=config.max_overlap,
    )
    problems.extend(refusal.describe() for refusal in result.refusals)
    if result.empty:
        problems.append(f"{config.train_examples_file} holds 0 train examples")
    return result, problems


def data_blockers(
    config: ExperimentConfig,
    *,
    validator: sft_dataset.Validator = sft_dataset.run_dataset_validator,
    policy: Optional[TeacherPolicy] = None,
) -> List[str]:
    result, problems = build_from_config(config, validator=validator, policy=policy)
    if problems or result is None:
        return problems
    sft_path = config.resolve(config.sft_file)
    if not sft_path.is_file():
        return [f"SFT file {config.sft_file} is missing: run training/build_sft_dataset.py first"]
    if sft_path.read_text(encoding="utf-8") != result.text():
        return [f"SFT file {config.sft_file} differs from a fresh build of the validated train split: rebuild it"]
    return []


def teacher_blockers(config: ExperimentConfig, policy: TeacherPolicy) -> List[str]:
    problems: List[str] = []
    if not policy.signoff.approved:
        problems.append(
            f"teacher policy legal_signoff is {policy.signoff.status!r}: arm C cannot start before counsel approves it"
        )
    for teacher in config.data.get("teachers") or []:
        decision = policy.is_permitted(teacher["provider"], teacher["model"], teacher["channel"])
        if not decision.permitted:
            problems.extend(f"teacher {teacher['model']}: {reason}" for reason in decision.reasons)
        elif teacher["policy_entry"] not in decision.entry_ids:
            problems.append(
                f"teacher {teacher['model']}: config names policy entry {teacher['policy_entry']!r} "
                f"but the policy matched {list(decision.entry_ids)}"
            )
        if not is_pinned_revision(teacher["revision"]):
            problems.append(f"teacher {teacher['model']}: revision is not pinned")
    return problems


def preflight(
    config: ExperimentConfig,
    *,
    paid_endpoint_flag: bool = False,
    validator: sft_dataset.Validator = sft_dataset.run_dataset_validator,
    policy: Optional[TeacherPolicy] = None,
) -> List[str]:
    """Every reason this config may not train now. An empty list is the only go."""
    problems = training_blockers(config, paid_endpoint_flag=paid_endpoint_flag)
    if config.arm == "A":
        return problems
    active_policy = policy or default_policy()
    if config.arm == "C":
        problems.extend(teacher_blockers(config, active_policy))
    problems.extend(data_blockers(config, validator=validator, policy=active_policy))
    return problems
