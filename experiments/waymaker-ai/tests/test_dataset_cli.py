"""The dataset validator command line: discovery, parse errors, exit codes, reports."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

from waymaker_ai.dataset.validate import discover, main

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures_dataset"
FIXTURE_FLAGS: List[str] = [
    "--registry", str(FIXTURES / "registry"),
    "--sources", str(FIXTURES / "sources"),
    "--manual-index", str(FIXTURES / "config" / "manual_approval_index.json"),
    "--teacher-policy", str(FIXTURES / "config" / "teacher_policy.json"),
]


def test_passing_fixture_exits_zero(capsys):
    assert main([str(FIXTURES / "examples"), *FIXTURE_FLAGS]) == 0
    out = capsys.readouterr().out
    assert "examples: 10  errors: 0  warnings: 0" in out
    assert out.rstrip().endswith("result: PASS")


def test_summary_is_deterministic_and_sorted(capsys):
    main([str(FIXTURES / "examples"), *FIXTURE_FLAGS])
    first = capsys.readouterr().out
    main([str(FIXTURES / "examples"), *FIXTURE_FLAGS])
    assert capsys.readouterr().out == first
    split_block = first.split("by split:\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert [line.split()[0] for line in split_block] == ["adversarial_holdout", "dev", "test", "train"]


def test_parse_errors_are_reported_per_line(capsys):
    assert main([str(FIXTURES / "invalid"), *FIXTURE_FLAGS]) == 1
    out = capsys.readouterr().out
    name = (FIXTURES / "invalid" / "parse_errors.jsonl").as_posix()
    assert f"[parse] {name}:1 - (root): invalid JSON: duplicate key 'id'" in out
    assert f"[parse] {name}:2 - (root): invalid JSON" in out
    assert f"[parse] {name}:4 - (root): invalid JSON: NaN is not valid JSON" in out
    assert f"[parse] {name}:5 - (root): an example must be a JSON object" in out
    assert f"{name}:3" not in out   # blank lines are skipped


def test_json_report(tmp_path, capsys):
    out_path = tmp_path / "report.json"
    assert main([str(FIXTURES / "invalid"), *FIXTURE_FLAGS, "--json", str(out_path)]) == 1
    capsys.readouterr()
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "waymaker-dataset-report/0.1"
    assert report["result"] == "fail"
    assert report["error_count"] == len([i for i in report["issues"] if i["severity"] == "error"]) == 4
    assert set(report["counts"]) == {"suite", "task", "language", "split", "adversarial_class", "label_status", "authoring"}


def test_missing_path_is_an_error(capsys, tmp_path):
    assert main([str(tmp_path / "missing.jsonl"), *FIXTURE_FLAGS]) == 1
    assert "path does not exist" in capsys.readouterr().out


def test_directories_skip_evidence_and_configuration():
    files, issues = discover([FIXTURES])
    assert issues == []
    assert [p.relative_to(FIXTURES).as_posix() for p in files] == ["examples/minimal_valid.jsonl", "invalid/parse_errors.jsonl"]


def test_json_array_files_report_indexes(tmp_path, capsys):
    examples = [json.loads(line) for line in (FIXTURES / "examples" / "minimal_valid.jsonl").read_text(encoding="utf-8").splitlines()]
    broken = dict(examples[0], id="fx-array-second", split="validation")
    path = tmp_path / "examples.json"
    path.write_text(json.dumps([examples[0], broken], ensure_ascii=False), encoding="utf-8")
    assert main([str(path), *FIXTURE_FLAGS]) == 1
    out = capsys.readouterr().out
    assert f"[schema] {path.as_posix()}[1] fx-array-second split:" in out


def _fixture_examples() -> List[dict]:
    lines = (FIXTURES / "examples" / "minimal_valid.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_examples_container_object_is_read_like_the_benchmark_loader(tmp_path, capsys):
    path = tmp_path / "examples.json"
    path.write_text(json.dumps({"examples": _fixture_examples()}, ensure_ascii=False), encoding="utf-8")
    assert main([str(path), *FIXTURE_FLAGS]) == 0
    assert "examples: 10  errors: 0  warnings: 0" in capsys.readouterr().out


def test_a_named_json_object_that_is_not_a_container_is_an_error(tmp_path, capsys):
    path = tmp_path / "single.json"
    path.write_text(json.dumps(_fixture_examples()[0], ensure_ascii=False), encoding="utf-8")
    assert main([str(path), *FIXTURE_FLAGS]) == 1
    assert f"[parse] {path.as_posix()} - (root): is not an example container" in capsys.readouterr().out


def test_a_discovered_json_object_is_skipped_with_a_warning(tmp_path, capsys):
    (tmp_path / "examples.jsonl").write_text(json.dumps(_fixture_examples()[0], ensure_ascii=False) + "\n", encoding="utf-8")
    (tmp_path / "split_index.json").write_text(json.dumps({"train": ["fx-class-e74-extension"]}), encoding="utf-8")
    assert main([str(tmp_path), *FIXTURE_FLAGS]) == 0
    out = capsys.readouterr().out
    assert "examples: 1  errors: 0  warnings: 1" in out
    assert "split_index.json - (root): is not an example container" in out and out.count("; skipped") == 1


def test_manifest_and_hidden_files_are_never_examples(tmp_path):
    for name in ("MANIFEST.json", "SHA256SUMS", ".draft.jsonl", "examples.jsonl"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    files, issues = discover([tmp_path])
    assert issues == []
    assert [p.name for p in files] == ["examples.jsonl"]


def test_manifest_names_mirror_the_benchmark_loader():
    from waymaker_ai.dataset.validate import MANIFEST_NAMES
    from waymaker_ai.evaluation.benchmark import MANIFEST_NAMES as LOADER_MANIFEST_NAMES

    assert MANIFEST_NAMES == LOADER_MANIFEST_NAMES


def test_unusable_schema_exits_two(tmp_path, capsys):
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps({"type": "object", "oneOf": []}), encoding="utf-8")
    assert main([str(FIXTURES / "examples"), *FIXTURE_FLAGS, "--schema", str(schema)]) == 2
    assert "oneOf" in capsys.readouterr().err


def test_documented_module_entry_points_agree():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    args = [str(FIXTURES / "examples"), *FIXTURE_FLAGS]
    runs = [
        subprocess.run([sys.executable, "-m", module, *args], cwd=EXPERIMENT_ROOT, env=env, capture_output=True, text=True, timeout=120)
        for module in ("waymaker_ai.dataset.validate", "waymaker_ai.dataset")
    ]
    assert [r.returncode for r in runs] == [0, 0], [r.stderr for r in runs]
    assert runs[0].stdout == runs[1].stdout
