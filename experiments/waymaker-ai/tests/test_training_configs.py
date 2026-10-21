"""Artemis experiment configs, the SFT builder, the leakage guard and train_qlora.py.

Nothing here trains, downloads or imports torch. The configs are checked for
the promises they make (NOT RUN, pinned revisions from models.md, no paid
endpoint, an empty train split stated as empty, the runner's own decoding), and
the gates are exercised on tiny inputs written to a temporary directory.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from waymaker_ai.distillation import experiment_config as ec
from waymaker_ai.distillation import leakage, preflight, sft_dataset
from waymaker_ai.distillation import teacher_policy as tp
from waymaker_ai.evaluation import predictions
from waymaker_ai.evaluation.baselines import model as runner_model

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
MODELS_NOTES = REPO_ROOT / "docs" / "ai" / "waymaker-genesis" / "research-notes" / "models.md"
TRAINING_DIR = EXPERIMENT_ROOT / "training"
CONFIG_FILES = {
    "A": ec.CONFIG_DIR / "exp_a_untuned.json",
    "B": ec.CONFIG_DIR / "exp_b_sft_qlora.json",
    "C": ec.CONFIG_DIR / "exp_c_verified_distill_sft.json",
}
HEAVY_MODULES = ("torch", "transformers", "peft", "trl", "bitsandbytes", "datasets", "accelerate")


def raw_config(arm: str) -> Dict[str, Any]:
    return json.loads(CONFIG_FILES[arm].read_text(encoding="utf-8"))


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, TRAINING_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def example(
    example_id: str,
    question: str,
    *,
    split: str = "train",
    task: str = "status_procedure_classification",
    expected: Optional[Dict[str, Any]] = None,
    critical: bool = False,
    review: Optional[Dict[str, Any]] = None,
    authoring: str = "synthetic_authored",
) -> Dict[str, Any]:
    """A benchmark-format example. Status codes are labels here, not legal content."""
    if expected is None:
        expected = (
            dict(CLASSIFICATION_LABEL)
            if task == "status_procedure_classification"
            else {"dates": [{"value": "2026-10-19", "role": "question_date"}]}
        )
    return {
        "id": example_id,
        "schema_version": "waymaker-example/0.1",
        "suite": "classification",
        "task": task,
        "language": "ko",
        "input": {"question": question, "payload_status_code": None},
        "expected": expected,
        "scenario": {"adversarial_class": None, "relevant_dates": {}, "anchor": None},
        "source_refs": [{"kind": "none", "ref": "none"}],
        "provenance": {
            "authoring": authoring,
            "authored_by": "test_training_configs",
            "created_at": "2026-10-19",
            "license": "CC0-1.0 (test fixture)",
            "contains_personal_data": False,
        },
        "label_review": review or {"status": "machine_checked", "checks": ["waymaker_ai.dataset.validate"]},
        "split": split,
        "critical": critical,
        "revision": 1,
        "revision_history": [{"revision": 1, "date": "2026-10-19", "change": "test fixture"}],
    }


#: A train classification label states every key the runner's schema asks for.
CLASSIFICATION_LABEL = {
    "status_code": "E-7", "subcode": "E-7-4", "procedure": "extension",
    "current_status": None, "target_status": None, "needs_clarification": False,
}
TRAIN_QUESTION = "E-7-4 체류기간 연장 신청하려고 해요"
DEV_QUESTION = "D-2 유학생인데 시간제 취업 허가를 받고 싶어요"


def unit(base_id: str, question: str, *, dates: Optional[List[Dict[str, str]]] = None, **classification: Any) -> List[Dict[str, Any]]:
    """Both Artemis labels for one question: the classification and the entity example."""
    return [
        example(f"{base_id}-cls", question, **classification),
        example(f"{base_id}-ent", question, task="entity_date_extraction", expected={"dates": dates or []}),
    ]


# ---------------------------------------------------------------------------
# The configs themselves
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_config_parses_and_is_not_run(arm):
    config = ec.load_config(CONFIG_FILES[arm])
    assert config.arm == arm
    assert config.status == "NOT RUN"
    assert config.train_state == "EMPTY"
    assert "no train split" in config.data["dataset"]["train"]["note"]
    assert config.eval_splits == ("dev", "test", "adversarial_holdout")
    assert config.data["prompt"]["sha256"] == sft_dataset.prompt_sha256()


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_base_models_are_pinned_to_the_shas_in_models_md(arm):
    config = ec.load_config(CONFIG_FILES[arm])
    assert config.base_model.repo_id == "google/gemma-4-E4B-it"
    assert config.secondary_model is not None and config.secondary_model.repo_id == "google/gemma-4-E2B-it"
    notes = MODELS_NOTES.read_text(encoding="utf-8") if MODELS_NOTES.is_file() else ""
    for model in (config.base_model, config.secondary_model):
        if model.revision == ec.REVISION_REQUIRED:
            assert ec.model_blockers(model), "REVISION_REQUIRED must block a run"
            continue
        assert model.revision_pinned
        assert model.license == "apache-2.0" and model.gated is False
        if notes:
            assert f"`{model.repo_id}` @ {model.revision}" in notes, f"{model.repo_id} SHA is not the one models.md recorded"


def test_revision_required_parses_but_blocks_training():
    data = raw_config("B")
    data["base_model"]["revision"] = ec.REVISION_REQUIRED
    config = ec.parse_config(data)
    assert any("REVISION_REQUIRED" in problem for problem in ec.training_blockers(config))
    data["base_model"]["revision"] = "main"
    with pytest.raises(ec.ConfigError):
        ec.parse_config(data)


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_no_config_uses_or_authorises_a_paid_endpoint(arm):
    data = raw_config(arm)
    assert data["compute"]["paid_endpoint"] is False
    assert data["compute"]["managed_finetuning"] is None
    assert data["cost"]["paid_runs_authorised"] is False
    assert data["cost"]["sources"] and all("cost.md" in s or "training-distill.md" in s for s in data["cost"]["sources"])

    paid = copy.deepcopy(data)
    paid["cost"]["paid_runs_authorised"] = True
    with pytest.raises(ec.ConfigError):
        ec.parse_config(paid)


def test_paid_flags_and_managed_finetuning_block_training():
    config = ec.load_config(CONFIG_FILES["B"])
    assert ec.training_blockers(config) == []
    assert any("paid endpoints are refused" in p for p in ec.training_blockers(config, paid_endpoint_flag=True))
    data = raw_config("B")
    data["compute"]["managed_finetuning"] = "together"
    assert any("managed fine-tuning" in p for p in ec.training_blockers(ec.parse_config(data)))


@pytest.mark.parametrize("licence", ["llama3.1", "gemma", "openmdw-1.1", "exaone-1.2-nc"])
def test_base_licence_outside_the_allow_list_blocks_training(licence):
    data = raw_config("B")
    data["base_model"]["license"] = licence
    assert any("allow-list" in p for p in ec.training_blockers(ec.parse_config(data)))


def test_gated_base_blocks_training():
    data = raw_config("B")
    data["base_model"]["gated"] = True
    assert any("gated" in p for p in ec.training_blockers(ec.parse_config(data)))


def test_untuned_arm_never_trains():
    config = ec.load_config(CONFIG_FILES["A"])
    assert config.training is None
    assert any("untuned control" in p for p in ec.training_blockers(config))


@pytest.mark.parametrize("arm", ["B", "C"])
def test_every_hyperparameter_has_a_justification(arm):
    data = raw_config(arm)
    for section, keys in ec.REQUIRED_HYPERPARAMETERS.items():
        for key in keys:
            assert data["training"][section][key]["why"].strip(), f"{section}.{key}"
    assert data["training"]["quantization"]["bnb_4bit_quant_type"]["value"] == "nf4"
    assert data["training"]["quantization"]["compute_dtype"]["value"] == "auto", "a T4 has no bf16"
    broken = copy.deepcopy(data)
    broken["training"]["lora"]["r"].pop("why")
    with pytest.raises(ec.ConfigError) as caught:
        ec.parse_config(broken)
    assert any("justification" in p for p in caught.value.problems)


def test_drifted_prompt_hash_is_rejected():
    data = raw_config("B")
    data["prompt"]["sha256"] = "0" * 64
    with pytest.raises(ec.ConfigError) as caught:
        ec.parse_config(data)
    assert any("prompt drifted" in p for p in caught.value.problems)


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_config_decoding_is_the_runners_and_cannot_contradict_it(arm):
    data = raw_config(arm)
    decoding = data["evaluation"]["decoding"]
    assert {key: decoding[key] for key in runner_model.DECODING} == runner_model.DECODING
    assert decoding["constrained_json"] is True
    data["evaluation"]["decoding"]["max_tokens"] = 256
    with pytest.raises(ec.ConfigError) as caught:
        ec.parse_config(data)
    assert any("evaluation.decoding.max_tokens" in p for p in caught.value.problems)


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_gates_reference_the_evaluation_methodology(arm):
    gates = raw_config(arm)["gates"]
    assert {"G1-safety", "G4-format", "D1-need-for-a-model"} <= {g["id"] for g in gates}
    assert any("12-evaluation-methodology.md" in g["source"] for g in gates)


def test_configs_must_train_both_artemis_tasks_together():
    data = raw_config("B")
    data["dataset"]["tasks"] = ["status_procedure_classification"]
    with pytest.raises(ec.ConfigError) as caught:
        ec.parse_config(data)
    assert any("every train question carries both labels" in p for p in caught.value.problems)


def test_build_refuses_a_non_artemis_task_even_if_a_caller_allows_it():
    abstention = example("train-0001", TRAIN_QUESTION, task="abstention",
                         expected={"must_withhold_conclusion": True, "required_issue_keys": []})
    abstention["suite"] = "abstention"
    result = sft_dataset.build_records(
        [abstention], [example("dev-0001", DEV_QUESTION, split="dev")],
        allowed_tasks=sft_dataset.ARTEMIS_TASKS + ("abstention",),
    )
    assert any("no place in an Artemis target" in r.reason for r in result.refusals)


def test_only_arm_c_may_use_teacher_labels():
    data = raw_config("B")
    data["dataset"]["train"]["allow_teacher_generated"] = True
    with pytest.raises(ec.ConfigError):
        ec.parse_config(data)


def test_arm_c_teachers_are_permitted_terms_but_blocked_by_pending_signoff():
    config = ec.load_config(CONFIG_FILES["C"])
    policy = tp.default_policy()
    notes = MODELS_NOTES.read_text(encoding="utf-8") if MODELS_NOTES.is_file() else ""
    for teacher in config.data["teachers"]:
        decision = policy.is_permitted(teacher["provider"], teacher["model"], teacher["channel"])
        assert decision.permitted, decision.reasons
        assert teacher["policy_entry"] in decision.entry_ids
        assert tp.is_pinned_revision(teacher["revision"])
        if notes:
            assert f"`{teacher['model']}` @ {teacher['revision']}" in notes
    blockers = preflight.teacher_blockers(config, policy)
    assert blockers == ["teacher policy legal_signoff is 'pending': arm C cannot start before counsel approves it"]


def test_shipped_configs_are_refused_today_because_the_train_split_is_empty():
    for arm in ("B", "C"):
        problems = preflight.preflight(ec.load_config(CONFIG_FILES[arm]))
        assert any("does not exist" in p and "EMPTY" in p for p in problems), problems


# ---------------------------------------------------------------------------
# Leakage guard
# ---------------------------------------------------------------------------
def test_tokenize_keeps_status_codes_whole():
    assert leakage.tokenize("E-7-4 연장, D-10-T?") == ["e-7-4", "연장", "d-10-t"]


def test_overlap_guard_on_tiny_inputs():
    train = [
        leakage.TextItem("t-exact", "train", DEV_QUESTION),
        leakage.TextItem("t-sibling", "train", "D-4 유학생인데 시간제 취업 허가를 받고 싶어요"),
        leakage.TextItem("t-unrelated", "train", TRAIN_QUESTION),
    ]
    evaluation = [leakage.TextItem("d-1", "dev", DEV_QUESTION)]
    overlaps = {o.train_id: o for o in leakage.find_overlaps(train, evaluation)}
    assert overlaps["t-exact"].exact and overlaps["t-exact"].score == 1.0
    assert not overlaps["t-sibling"].exact and overlaps["t-sibling"].score > leakage.DEFAULT_MAX_OVERLAP
    assert "t-unrelated" not in overlaps


def test_exact_duplicate_detection_ignores_spacing():
    items = [leakage.TextItem("a", "train", "E-7-4  연장"), leakage.TextItem("b", "train", "E-7-4 연장")]
    assert leakage.duplicate_texts(items) == [("a", "b")]


def test_build_refuses_a_train_question_that_leaks_into_evaluation():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    result = sft_dataset.build_records(unit("train-0001", DEV_QUESTION), dev, schema=None)
    assert not result.ok
    assert any("leaks into evaluation" in r.reason for r in result.refusals)
    assert result.text() == ""


def test_disjoint_tiny_split_builds_deterministic_records():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    question = "2026-10-19 기준으로 E-7-4 체류기간 연장 신청하려고 해요"
    train = unit("train-0001", question, dates=[{"role": "question_date", "value": "2026-10-19"}])
    first = sft_dataset.build_records(train, dev)
    second = sft_dataset.build_records(copy.deepcopy(train), copy.deepcopy(dev))
    assert first.ok, [r.describe() for r in first.refusals]
    assert first.text() == second.text()
    assert len(first.records) == 1, "one record per question, not per example"
    record = first.records[0]
    assert record["question"] == question
    assert [m["role"] for m in record["prompt"]] == ["system", "user"]
    content = record["completion"][0]["content"]
    assert list(json.loads(content)) == list(predictions.model_output_schema("status_procedure_classification")["properties"])
    assert json.loads(content) == {
        "status_code": "E-7", "subcode": "E-7-4", "procedure": "extension", "current_status": None,
        "target_status": None, "dates": [{"value": "2026-10-19", "role": "question_date"}], "needs_clarification": False,
    }
    assert record["meta"]["example_ids"] == ["train-0001-cls", "train-0001-ent"]
    assert record["meta"]["prompt_template_sha256"] == sft_dataset.prompt_sha256()


def test_record_prompt_and_target_are_the_runners_request_and_schema():
    train = unit("train-0001", TRAIN_QUESTION)
    train[0]["input"]["payload_status_code"] = "E-7"
    train[1]["input"]["payload_status_code"] = "E-7"
    record = sft_dataset.build_records(train, [example("dev-0001", DEV_QUESTION, split="dev")]).records[0]
    assert record["prompt"] == runner_model.build_messages(train[0]) == runner_model.build_messages(train[1])
    assert record["prompt"][1]["content"].startswith("[UI-selected status code: E-7]")
    prediction, violations = predictions.parse_model_output(record["completion"][0]["content"], "status_procedure_classification")
    assert violations == [] and prediction["subcode"] == "E-7-4"
    for task in sft_dataset.ARTEMIS_TASKS:
        assert sft_dataset.target_schema(task) == predictions.model_output_schema(task)
    with pytest.raises(ValueError):
        sft_dataset.target_schema("citation_verification")
    assert sft_dataset.eval_contract_problems() == []


def test_a_runner_that_splits_its_prompt_per_task_stops_the_build(monkeypatch):
    original = runner_model.system_prompt
    monkeypatch.setattr(runner_model, "system_prompt", lambda task: original(task) + task)
    result = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION), [example("dev-0001", DEV_QUESTION, split="dev")])
    assert any("pairing rule must be revisited" in r.reason for r in result.refusals)


def test_a_question_with_only_one_artemis_label_is_refused():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    only_classification = sft_dataset.build_records([example("train-0001", TRAIN_QUESTION)], dev)
    assert any("no entity_date_extraction label" in r.reason for r in only_classification.refusals)
    only_dates = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION)[1:], dev)
    assert any("no status_procedure_classification label" in r.reason for r in only_dates.refusals)
    assert only_classification.text() == only_dates.text() == ""


def test_labels_of_different_questions_are_never_paired():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    cls, ent = unit("train-0001", TRAIN_QUESTION)
    ent["input"]["question"] = TRAIN_QUESTION + " "   # one trailing space is a different prompt
    result = sft_dataset.build_records([cls, ent], dev)
    assert sum("label for this exact question" in r.reason for r in result.refusals) == 2


def test_two_labels_for_one_task_are_refused():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    train = unit("train-0001", TRAIN_QUESTION) + [example("train-0002-cls", TRAIN_QUESTION)]
    result = sft_dataset.build_records(train, dev)
    assert any("2 status_procedure_classification labels" in r.reason for r in result.refusals)


@pytest.mark.parametrize("key", ["current_status", "target_status", "needs_clarification"])
def test_classification_label_must_state_every_schema_key(key):
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    label = dict(CLASSIFICATION_LABEL)
    label.pop(key)
    result = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION, expected=label), dev)
    assert any("must state" in r.reason and key in r.reason for r in result.refusals)


def test_normalised_duplicate_questions_are_refused():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    train = unit("train-0001", TRAIN_QUESTION) + unit("train-0002", TRAIN_QUESTION.replace(" ", "  "))
    result = sft_dataset.build_records(train, dev)
    assert any("same question as train-0001-cls after normalisation" in r.reason for r in result.refusals)


def test_runner_contamination_check_reads_the_sft_file(tmp_path: Path):
    from waymaker_ai.evaluation.runner import contamination_check

    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    built = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION), dev)
    sft_path = tmp_path / "train.sft.jsonl"
    sft_path.write_text(built.text(), encoding="utf-8")
    leaked = [example("test-0001", TRAIN_QUESTION, split="test")]
    assert contamination_check(leaked, [sft_path])["overlap_count"] == 1
    assert contamination_check(dev, [sft_path])["overlap_count"] == 0


def test_build_refuses_without_any_evaluation_examples():
    result = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION), [])
    assert any("disjointness cannot be shown" in r.reason for r in result.refusals)


@pytest.mark.parametrize("variant, expected", [
    (dict(critical=True), "'human_verified' is required"),
    (dict(review={"status": "unreviewed", "checks": []}), "label is unreviewed"),
    (dict(review={"status": "disputed", "checks": []}), "label is disputed"),
    (dict(review={"status": "human_verified", "checks": []}, critical=True), "must name the reviewer"),
    (dict(authoring="teacher_generated"), "not allowed in this experiment arm"),
    (dict(split="dev"), "only 'train' examples"),
])
def test_build_refuses_examples_that_fail_a_gate(variant, expected):
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    result = sft_dataset.build_records(unit("train-0001", TRAIN_QUESTION, **variant), dev)
    assert not result.ok
    assert any(expected in r.reason for r in result.refusals), [r.describe() for r in result.refusals]


def test_build_refuses_tasks_that_are_not_artemis_tasks():
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    abstention = example("train-0001", TRAIN_QUESTION, task="abstention",
                         expected={"must_withhold_conclusion": True, "required_issue_keys": []})
    abstention["suite"] = "abstention"
    result = sft_dataset.build_records([abstention], dev)
    assert any("not an Artemis training task" in r.reason for r in result.refusals)


def test_eval_examples_are_found_like_the_runner_finds_them(tmp_path: Path):
    nested = tmp_path / "v0" / "holdout"
    nested.mkdir(parents=True)
    (nested / "adv.jsonl").write_text(json.dumps(example("adv-0001", DEV_QUESTION, split="adversarial_holdout")) + "\n", encoding="utf-8")
    (tmp_path / "v0" / "MANIFEST.json").write_text("{}", encoding="utf-8")
    (tmp_path / "v0" / "sources").mkdir()
    (tmp_path / "v0" / "sources" / "bundle.json").write_text("{\"bundle_id\": \"x\"}", encoding="utf-8")
    (tmp_path / "v0" / ".draft.jsonl").write_text(json.dumps(example("dot-0001", DEV_QUESTION, split="dev")) + "\n", encoding="utf-8")
    # The runner scores an example wherever it sits, so the guard reads it too.
    (tmp_path / "v0" / "sources" / "stray.json").write_text(json.dumps([example("dev-0009", DEV_QUESTION, split="dev")]), encoding="utf-8")
    found = sft_dataset.load_eval_examples(tmp_path / "v0")
    assert sorted(e["id"] for e in found) == ["adv-0001", "dev-0009"]

    (tmp_path / "v0" / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(sft_dataset.DatasetFileError):
        sft_dataset.load_eval_examples(tmp_path / "v0")


# ---------------------------------------------------------------------------
# End to end on tiny files: validator, builder, preflight, train_qlora --check-only
# ---------------------------------------------------------------------------
def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _tiny_config(tmp_path: Path, train_rows: List[Dict[str, Any]]) -> Path:
    bench = tmp_path / "benchmark"
    _write_jsonl(bench / "dev.jsonl", [example("dev-0001", DEV_QUESTION, split="dev")])
    _write_jsonl(tmp_path / "train" / "train.jsonl", train_rows)
    data = raw_config("B")
    data["dataset"]["benchmark_dir"] = str(bench)
    data["dataset"]["train"]["examples_file"] = str(tmp_path / "train" / "train.jsonl")
    data["dataset"]["train"]["sft_file"] = str(tmp_path / "sft" / "train.sft.jsonl")
    path = tmp_path / "exp_b_tiny.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_validator_reads_the_train_file_together_with_the_benchmark(tmp_path: Path):
    config = ec.load_config(_tiny_config(tmp_path, unit("train-0001", TRAIN_QUESTION)))
    seen: List[List[Path]] = []

    def fake_validator(paths):
        seen.append(list(paths))
        return False, "fake refusal"

    result, problems = preflight.build_from_config(config, validator=fake_validator)
    assert result is None
    assert seen == [[config.resolve(config.train_examples_file), config.resolve(config.benchmark_dir)]]
    assert problems == [f"dataset validator did not pass on {config.train_examples_file} together with the benchmark: fake refusal"]


def test_end_to_end_tiny_split_passes_every_gate_without_torch(tmp_path: Path, capsys):
    config_path = _tiny_config(tmp_path, unit("train-0001", TRAIN_QUESTION))
    config = ec.load_config(config_path)
    problems = preflight.preflight(config)
    assert problems == ["SFT file " + config.sft_file + " is missing: run training/build_sft_dataset.py first"]

    build = load_module("build_sft_dataset")
    assert build.main(["--config", str(config_path)]) == 0
    assert preflight.preflight(config) == []

    train_qlora = load_module("train_qlora")
    assert train_qlora.main(["--config", str(config_path), "--check-only"]) == 0
    assert "every gate passed" in capsys.readouterr().out

    # One byte of drift in the SFT file and the trainer refuses.
    sft_path = Path(config.sft_file)
    sft_path.write_text(sft_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert any("differs from a fresh build" in p for p in preflight.preflight(config))


def test_end_to_end_refuses_a_train_file_the_validator_fails(tmp_path: Path, capsys):
    broken = unit("train-0001", TRAIN_QUESTION)
    broken[0]["expected"]["status_code"] = "E-7-4"  # a subcode filed as the parent
    config_path = _tiny_config(tmp_path, broken)
    build = load_module("build_sft_dataset")
    assert build.main(["--config", str(config_path)]) == 1
    error = capsys.readouterr().err
    assert "dataset validator did not pass" in error and "subcode_hierarchy" in error
    assert not (tmp_path / "sft" / "train.sft.jsonl").exists()


# ---------------------------------------------------------------------------
# train_qlora.py without torch
# ---------------------------------------------------------------------------
BLOCKER = """
import importlib.abc, importlib.util, sys
HEAVY = {heavy!r}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in HEAVY:
            raise ImportError('blocked for this test: ' + name)
        return None
sys.meta_path.insert(0, Block())
spec = importlib.util.spec_from_file_location('train_qlora', {script!r})
module = importlib.util.module_from_spec(spec)
sys.modules['train_qlora'] = module
spec.loader.exec_module(module)
code = module.main({argv!r})
loaded = sorted(m for m in sys.modules if m.split('.')[0] in HEAVY)
print('EXIT', code, 'LOADED', loaded)
"""


def _run_without_heavy_packages(argv: List[str]) -> subprocess.CompletedProcess:
    program = BLOCKER.format(heavy=HEAVY_MODULES, script=str(TRAINING_DIR / "train_qlora.py"), argv=argv)
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", program],
        cwd=str(EXPERIMENT_ROOT), capture_output=True, text=True, timeout=120, check=False,
    )


def test_train_qlora_imports_and_refuses_without_torch():
    completed = _run_without_heavy_packages(["--config", str(CONFIG_FILES["B"]), "--check-only"])
    assert "EXIT 1 LOADED []" in completed.stdout, completed.stdout + completed.stderr
    assert "does not exist" in completed.stderr


def test_train_qlora_refuses_paid_endpoints_and_arm_a_without_torch():
    paid = _run_without_heavy_packages(
        ["--config", str(CONFIG_FILES["B"]), "--seed", "1", "--paid-endpoint", "rented-gpu", "--i-understand-this-may-cost-money"]
    )
    assert "EXIT 1 LOADED []" in paid.stdout, paid.stdout + paid.stderr
    assert "paid endpoints are refused" in paid.stderr
    assert "does not unlock a paid endpoint" in paid.stderr
    untuned = _run_without_heavy_packages(["--config", str(CONFIG_FILES["A"]), "--check-only"])
    assert "EXIT 1 LOADED []" in untuned.stdout
    assert "untuned control" in untuned.stderr


def test_train_qlora_helpers():
    train_qlora = load_module("train_qlora")
    assert train_qlora.resolve_compute_dtype("auto", False)[0] == "float16"
    assert train_qlora.resolve_compute_dtype("auto", True)[0] == "bfloat16"
    assert train_qlora.resolve_compute_dtype("bfloat16", False)[0] is None

    included, excluded, missing = train_qlora.select_target_modules(
        [
            "model.language_model.layers.0.self_attn.q_proj",
            "model.language_model.layers.0.mlp.down_proj",
            "model.vision_tower.encoder.layers.0.self_attn.q_proj",
            "model.audio_tower.layers.0.mlp.down_proj",
        ],
        ["q_proj", "down_proj", "gate_proj"],
    )
    assert included == ["model.language_model.layers.0.self_attn.q_proj", "model.language_model.layers.0.mlp.down_proj"]
    assert len(excluded) == 2 and missing == ["gate_proj"]

    config = ec.load_config(CONFIG_FILES["B"])
    assert train_qlora.chosen_model(config, "secondary").repo_id == "google/gemma-4-E2B-it"
    run_dir = train_qlora.run_directory(config, "secondary", 1, True, Path("/runs"))
    assert run_dir == Path("/runs/artemis-exp-b-sft-qlora/smoke-secondary-seed1")


def test_requirements_file_pins_or_flags_every_training_package():
    train_qlora = load_module("train_qlora")
    requirements = train_qlora.parse_requirements(train_qlora.REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    assert requirements.problems == []
    assert requirements.pinned["trl"] == "1.16.0"
    assert set(train_qlora.TRAINING_PACKAGES) <= set(requirements.pinned) | set(requirements.todo)
    assert "torch" in requirements.recorded

    installed = {name: "9.9.9" for name in train_qlora.TRAINING_PACKAGES}
    installed["trl"] = "1.16.0"
    assert train_qlora.pin_problems(requirements, installed, smoke=True) == []
    real = train_qlora.pin_problems(requirements, installed, smoke=False)
    assert real and all("TODO(pin)" in p for p in real)
    installed["trl"] = "1.15.0"
    assert any("pins 1.16.0" in p for p in train_qlora.pin_problems(requirements, installed, smoke=True))

    ranged = train_qlora.parse_requirements("trl>=1.0\n")
    assert any("is not pinned" in p for p in ranged.problems)


# ---------------------------------------------------------------------------
# teacher_generated examples (arm C) on tiny inputs
# ---------------------------------------------------------------------------
def _teacher_unit() -> List[Dict[str, Any]]:
    """A teacher-generated classification label paired with a human-authored entity label."""
    rows = unit("train-teacher-0001", TRAIN_QUESTION, authoring="teacher_generated")
    rows[0]["provenance"]["teacher"] = {
        "provider": "fixture-lab", "model": "fixture-lab/teacher-1", "channel": "self_hosted",
        "terms_ref": "fixture-open-weights", "permitted": True,
    }
    return rows


def _teacher_build(policy: tp.TeacherPolicy, **record_overrides) -> sft_dataset.BuildResult:
    from tests.test_teacher_policy import record_dict

    record_overrides.setdefault("output", dict(CLASSIFICATION_LABEL))
    record = tp.TeacherRecord.from_dict(record_dict(example_id="train-teacher-0001-cls", **record_overrides))
    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    return sft_dataset.build_records(
        _teacher_unit(), dev, teacher_records=[record], policy=policy, allow_teacher_generated=True,
    )


def test_teacher_generated_example_passes_only_with_an_accepted_record():
    from tests.test_teacher_policy import fictional_policy_dict

    approved = tp.parse_policy(fictional_policy_dict("approved"))
    result = _teacher_build(approved)
    assert result.ok, [r.describe() for r in result.refusals]
    assert [e["teacher_record_id"] for e in result.records[0]["meta"]["examples"]] == ["tr-0001", None]

    pending = tp.parse_policy(fictional_policy_dict("pending"))
    refused = _teacher_build(pending)
    assert any("legal_signoff is 'pending'" in r.reason for r in refused.refusals)

    different = _teacher_build(approved, output={**CLASSIFICATION_LABEL, "subcode": None})
    assert any("not exactly the gated teacher output" in r.reason for r in different.refusals)


def test_teacher_generated_example_without_a_record_is_refused():
    from tests.test_teacher_policy import fictional_policy_dict

    dev = [example("dev-0001", DEV_QUESTION, split="dev")]
    result = sft_dataset.build_records(
        _teacher_unit(), dev, teacher_records=[], policy=tp.parse_policy(fictional_policy_dict()),
        allow_teacher_generated=True,
    )
    assert any("exactly one teacher record" in r.reason for r in result.refusals)


def test_real_run_stops_at_the_environment_check_while_pins_are_todo(tmp_path: Path):
    config_path = _tiny_config(tmp_path, unit("train-0001", TRAIN_QUESTION))
    assert load_module("build_sft_dataset").main(["--config", str(config_path)]) == 0
    completed = _run_without_heavy_packages(
        ["--config", str(config_path), "--seed", "1", "--runs-dir", str(tmp_path / "runs")]
    )
    assert "EXIT 3 LOADED []" in completed.stdout, completed.stdout + completed.stderr
    assert "ENVIRONMENT NOT READY" in completed.stderr
    assert "TODO(pin)" in completed.stderr or "not installed" in completed.stderr
    assert not (tmp_path / "runs").exists()
