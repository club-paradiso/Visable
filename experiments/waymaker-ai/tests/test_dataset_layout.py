"""One benchmark layout for the validator, the runner's loader and the SFT leakage guard.

The three components used to keep their own copies of "which files are
examples" and drifted: the validator skipped evidence directories that the
runner still scored. ``waymaker_ai.dataset.layout`` now holds the rule. These
tests build one tree with every kind of file and check that:

* the validator checks exactly the files the runner reads examples from;
* the runner still hashes every data file (so the benchmark digest covers a
  rubric), and lists each non-example file with its reason;
* the leakage guard reads at least what the runner scores.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from waymaker_ai.dataset import layout
from waymaker_ai.dataset import validate as v
from waymaker_ai.distillation import sft_dataset
from waymaker_ai.evaluation import benchmark

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures_dataset"
OPTIONS = v.Options(
    registry_dir=FIXTURES / "registry",
    sources_dir=FIXTURES / "sources",
    manual_index_path=FIXTURES / "config" / "manual_approval_index.json",
    teacher_policy_path=FIXTURES / "config" / "teacher_policy.json",
)


def _example(ident: str, split: str = "dev") -> Dict[str, Any]:
    return {"id": ident, "task": "status_procedure_classification", "split": split,
            "input": {"question": f"질문 {ident}"}, "expected": {"status_code": None, "subcode": None, "procedure": None},
            "scenario": {"adversarial_class": None, "relevant_dates": {}}}


def _write(path: Path, data: Any, *, jsonl: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if jsonl:
        path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in data), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def make_tree(root: Path) -> Path:
    """A benchmark directory with one file of every kind the layout distinguishes."""
    bench = root / "bench"
    _write(bench / "a.jsonl", [_example("ex-a1"), _example("ex-a2", "test")], jsonl=True)
    _write(bench / "b.json", {"examples": [_example("ex-b1", "adversarial_holdout")]})
    _write(bench / "abstention_rubric.json", {"required_issue_keys": {"ask_missing_facts": "Asks for the facts."}})
    _write(bench / "notes" / "split_index.json", {"dev": ["ex-a1"]})
    _write(bench / "sources" / "stray.json", [_example("ex-stray")])           # evidence directory
    _write(bench / ".hidden" / "x.jsonl", [_example("ex-hidden")], jsonl=True)  # hidden directory
    _write(bench / ".draft.jsonl", [_example("ex-draft")], jsonl=True)          # dot file: not even data
    _write(bench / "sub" / "c_index.json", {"files": []})
    _write(bench / "sub" / "d.jsonl", [_example("ex-d1", "test")], jsonl=True)
    _write(bench / "sub" / "MANIFEST.json", {"non_example_files": ["c_index.json"]})
    _write(bench / "MANIFEST.json", {"files": {}, "non_example_files": ["notes/split_index.json"]})
    (bench / "SHA256SUMS").write_text("", encoding="utf-8")
    (bench / "readme.txt").write_text("not data", encoding="utf-8")
    return bench


def rel(paths: List[Path], root: Path) -> List[str]:
    return [p.relative_to(root).as_posix() for p in paths]


EXAMPLE_FILES = ["a.jsonl", "b.json", "sub/d.jsonl"]
NON_EXAMPLE = {
    ".hidden/x.jsonl": layout.REASON_HIDDEN_DIR,
    "abstention_rubric.json": layout.REASON_RUBRIC,
    "notes/split_index.json": layout.REASON_DECLARED,
    "sources/stray.json": f"{layout.REASON_NON_EXAMPLE_DIR} sources/",
    "sub/c_index.json": layout.REASON_DECLARED,
}


def test_layout_classifies_every_kind_of_file(tmp_path):
    bench = make_tree(tmp_path)
    examples, skipped, _index = layout.classify(bench)
    assert rel(examples, bench) == EXAMPLE_FILES
    assert {p.relative_to(bench).as_posix(): reason for p, reason in skipped} == NON_EXAMPLE
    assert sorted(rel(layout.data_files(bench), bench)) == sorted(EXAMPLE_FILES + list(NON_EXAMPLE))


def test_validator_checks_exactly_what_the_runner_scores(tmp_path):
    bench = make_tree(tmp_path)
    files, issues = v.discover([bench])
    assert rel(files, bench) == EXAMPLE_FILES
    assert issues == []
    loaded = benchmark.load_benchmark(bench)
    read_as_examples = sorted(f.path for f in loaded.files if f.path not in {n.path for n in loaded.non_example_files})
    assert read_as_examples == EXAMPLE_FILES
    assert sorted(e["id"] for e in loaded.examples) == ["ex-a1", "ex-a2", "ex-b1", "ex-d1"]


def test_runner_hashes_every_data_file_and_names_the_non_example_ones(tmp_path):
    bench = make_tree(tmp_path)
    loaded = benchmark.load_benchmark(bench)
    hashed = {f.path: f.examples for f in loaded.files}
    assert sorted(hashed) == sorted(EXAMPLE_FILES + list(NON_EXAMPLE))   # the digest covers the rubric
    assert all(hashed[path] == 0 for path in NON_EXAMPLE)
    assert {n.path: n.reason for n in loaded.non_example_files} == NON_EXAMPLE


def test_leakage_guard_reads_at_least_what_the_runner_scores(tmp_path):
    bench = make_tree(tmp_path)
    assert sft_dataset.benchmark_files(bench) == layout.data_files(bench)
    assert set(layout.example_files(bench)) <= set(sft_dataset.benchmark_files(bench))
    guarded = {e["id"] for e in sft_dataset.load_eval_examples(bench)}
    scored = {e["id"] for e in benchmark.load_benchmark(bench).examples}
    assert scored <= guarded
    assert "ex-stray" in guarded and "ex-draft" not in guarded   # the guard reads by content, dot files never


def test_one_definition_of_the_shared_names():
    assert v.MANIFEST_NAMES is layout.MANIFEST_NAMES
    assert benchmark.MANIFEST_NAMES is layout.MANIFEST_NAMES
    assert sft_dataset.MANIFEST_NAMES is layout.MANIFEST_NAMES
    assert v.NON_EXAMPLE_DIRS is layout.NON_EXAMPLE_DIRS
    assert sft_dataset.EXAMPLE_SUFFIXES is layout.EXAMPLE_SUFFIXES


def test_real_benchmark_rubric_is_a_non_example_file_and_raises_no_warning():
    bench = EXPERIMENT_ROOT / "datasets" / "benchmark" / "v0"
    if not (bench / "abstention_rubric.json").is_file():
        pytest.skip("benchmark v0 has no abstention_rubric.json in this checkout")
    _examples, skipped, _index = layout.classify(bench)
    assert (bench / "abstention_rubric.json", layout.REASON_RUBRIC) in skipped
    report = v.validate_paths([bench], v.Options())
    assert not [i for i in report.issues if "abstention_rubric.json" in i.file], [i.render() for i in report.issues]


# ---------------------------------------------------------------------------
# Declarations the validator checks (rule ``layout``)
# ---------------------------------------------------------------------------
def _layout_issues(bench: Path) -> List[v.Issue]:
    _files, issues = v.discover([bench])
    return [i for i in issues if i.rule == "layout"]


@pytest.mark.parametrize("declared", ["not-a-list", ["../outside.json"], ["/abs.json"], [" spaced.json"], [3], ["a\\b.json"]])
def test_malformed_declarations_are_errors(tmp_path, declared):
    bench = tmp_path / "bench"
    _write(bench / "a.jsonl", [_example("ex-a1")], jsonl=True)
    _write(bench / "MANIFEST.json", {"non_example_files": declared})
    issues = _layout_issues(bench)
    assert [i.severity for i in issues] == [v.ERROR], [i.render() for i in issues]
    assert issues[0].file.endswith("MANIFEST.json")


def test_a_declaration_naming_no_file_is_a_warning(tmp_path):
    bench = tmp_path / "bench"
    _write(bench / "a.jsonl", [_example("ex-a1")], jsonl=True)
    _write(bench / "MANIFEST.json", {"non_example_files": ["gone.json", {"path": "./also_gone.json"}]})
    issues = _layout_issues(bench)
    assert [i.severity for i in issues] == [v.WARNING, v.WARNING]
    assert "\"also_gone.json\"" in issues[0].message + issues[1].message


@pytest.mark.parametrize("name, declare", [("hidden_rubric.json", False), ("notes.json", True), ("ledger.jsonl", True)])
def test_a_non_example_file_that_holds_examples_is_an_error(tmp_path, name, declare):
    bench = tmp_path / "bench"
    _write(bench / "a.jsonl", [_example("ex-a1")], jsonl=True)
    _write(bench / name, [_example("ex-hidden-away")], jsonl=name.endswith(".jsonl"))
    if declare:
        _write(bench / "MANIFEST.json", {"non_example_files": [name]})
    issues = _layout_issues(bench)
    assert [(i.severity, Path(i.file).name) for i in issues] == [(v.ERROR, name)], [i.render() for i in issues]
    assert "neither validated nor scored" in issues[0].message


def test_a_directory_walked_twice_reports_each_layout_problem_once(tmp_path):
    bench = tmp_path / "bench"
    _write(bench / "sub" / "a.jsonl", [_example("ex-a1")], jsonl=True)
    _write(bench / "sub" / "MANIFEST.json", {"non_example_files": ["gone.json"]})
    files, issues = v.discover([bench, bench / "sub", bench])
    assert rel(files, bench) == ["sub/a.jsonl"]
    assert [(i.rule, i.severity) for i in issues] == [("layout", v.WARNING)], [i.render() for i in issues]


def test_a_declared_ledger_without_example_records_is_fine(tmp_path):
    bench = tmp_path / "bench"
    _write(bench / "a.jsonl", [_example("ex-a1")], jsonl=True)
    _write(bench / "ledger.jsonl", [{"benchmark_digest": "0" * 64, "baselines": ["wlie"]}], jsonl=True)
    _write(bench / "MANIFEST.json", {"non_example_files": ["ledger.jsonl"]})
    assert _layout_issues(bench) == []


def test_a_file_named_on_the_command_line_is_always_read_as_examples(tmp_path):
    bench = make_tree(tmp_path)
    files, _issues = v.discover([bench / "abstention_rubric.json"])
    assert files == [bench / "abstention_rubric.json"]


def test_layout_rules_reach_the_validator_report(tmp_path):
    bench = tmp_path / "bench"
    _write(bench / "examples.jsonl", [json.loads((FIXTURES / "examples" / "minimal_valid.jsonl").read_text(encoding="utf-8").splitlines()[0])], jsonl=True)
    _write(bench / "MANIFEST.json", {"non_example_files": ["missing.json"]})
    report = v.validate_paths([bench], OPTIONS)
    assert report.rules() == ["layout"] and report.ok   # a stale declaration warns, it does not fail


@pytest.mark.parametrize("raw, expected", [
    ("a.json", "a.json"), ("./notes/x.json", "notes/x.json"), ("notes//x.json", "notes/x.json"), ("..", None),
    ("", None), (None, None), ("x/../y.json", None), (".", None),
])
def test_declared_paths_are_normalized_or_refused(raw, expected):
    assert layout.normalize_declared_path(raw) == expected
