"""Report size and layout, report compaction, --backend-root provenance and --fail-on-hard-gates.

All in-process on the tiny inline benchmark of test_evaluation_runner.py, with
stub baselines. No backend code runs here (test_evaluation_backend_root.py
drives the existing-law driver against a stub backend tree).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pytest

from waymaker_ai.evaluation import report as report_mod
from waymaker_ai.evaluation import runner
from waymaker_ai.evaluation.baselines.b1_python import backend_available, backend_dir
from waymaker_ai.evaluation.baselines.base import Baseline, EvalItem, ItemResult, RunContext

from tests.test_evaluation_runner import (
    AbsenceClaimer,
    ParentOnly,
    citation,
    config_for,
    items_of,
    make_examples,
    no_network,  # noqa: F401  (autouse fixture: any socket connection fails the test)
    write_benchmark,
)

BIG = "가상" * 3000   # over report.MAX_RAW_JSON once serialized


class RawEmitter(Baseline):
    """Answers like ParentOnly and returns a raw payload, one of them too large to keep."""

    name = "stub_raw"
    emits = {"status_procedure_classification": frozenset({"status_code", "subcode", "procedure_coarse"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        out = {}
        for index, item in enumerate(items):
            raw = {"driver": "stub", "item": item.id, "blob": BIG if index == 0 else "small"}
            out[item.id] = ItemResult(item.id, "ok", raw=raw, prediction={
                "status_code": item.example["expected"]["status_code"], "subcode": None, "procedure_fine": None,
                "procedure_coarse": "extension"}, latency_ms=1.0)
        return out


class BackendStub(ParentOnly):
    """In-process, but declares that it imports the backend, so the report hashes the tree."""

    name = "stub_backend"
    uses_backend = True


class Oracle(Baseline):
    """Repeats every citation label: passes every hard gate it has evidence for."""

    name = "stub_oracle"
    emits = {"citation_verification": frozenset({"overall", "layer_codes", "codes"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        out = {}
        for item in items:
            expected = item.example["expected"]
            layers = dict(expected["layer_codes"])
            out[item.id] = ItemResult(item.id, "ok", prediction={
                "overall": expected["overall"], "layer_codes": layers, "codes": sorted(set(layers.values()))})
        return out


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _run(tmp_path: Path, baselines: Sequence[Baseline], splits: Sequence[str] = ("dev", "test"), **kw: Any) -> Dict[str, Any]:
    bench = write_benchmark(tmp_path, make_examples())
    return runner.run_evaluation(config_for(tmp_path, bench, [], list(splits), **kw), baselines=list(baselines))


# ---------------------------------------------------------------------------
# Raw payloads
# ---------------------------------------------------------------------------
def test_raw_payloads_are_omitted_by_default_and_kept_as_a_hash(tmp_path):
    report = _run(tmp_path, [RawEmitter()])
    records = report["items"]["stub_raw"]
    assert records and all("raw" not in r for r in records)
    first = records[0]
    assert first["raw_sha256"] == canonical_sha({"driver": "stub", "item": first["id"], "blob": BIG})
    assert first["verdict"] in ("correct", "wrong") and first["metrics"]          # per-item scoring stays
    assert "raw_sha256" in report["policy"]["raw_payloads"]


def test_include_raw_keeps_the_bounded_payload_and_the_scores_do_not_change(tmp_path):
    lean = _run(tmp_path / "a", [RawEmitter()])
    full = _run(tmp_path / "b", [RawEmitter()], include_raw=True)
    records = full["items"]["stub_raw"]
    assert records[0]["raw"]["_truncated"] is True and records[0]["raw"]["sha256"] == records[0]["raw_sha256"]
    assert records[1]["raw"] == {"driver": "stub", "item": records[1]["id"], "blob": "small"}
    assert [r["raw_sha256"] for r in records] == [r["raw_sha256"] for r in lean["items"]["stub_raw"]]
    assert full["scoring_digest"] == lean["scoring_digest"]


def test_an_item_without_raw_output_has_a_null_hash(tmp_path):
    report = _run(tmp_path, [ParentOnly()])
    assert {r["raw_sha256"] for r in report["items"]["stub_parent_only"]} == {None}


# ---------------------------------------------------------------------------
# JSON layout
# ---------------------------------------------------------------------------
def test_dumps_round_trips_and_writes_one_line_per_item(tmp_path):
    report = _run(tmp_path, [RawEmitter(), AbsenceClaimer()], splits=("dev", "test", "adversarial_holdout"))
    text = report_mod.dumps(report)
    assert json.loads(text) == json.loads(json.dumps(report, default=str))
    item_lines = [line for line in text.splitlines() if line.startswith('      {"')]
    assert len(item_lines) == sum(len(records) for records in report["items"].values())
    for line in item_lines:
        record = json.loads(line.strip().rstrip(","))
        assert line.strip().rstrip(",") == json.dumps(record, ensure_ascii=False, sort_keys=True)
    assert text == report_mod.dumps(json.loads(text))   # stable through a load/dump cycle


def test_dumps_without_items_is_a_plain_indented_dump():
    report = {"b": 1, "a": {"c": [1, 2]}, "items": {}}
    assert report_mod.dumps(report) == json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def test_written_report_is_smaller_than_an_indented_dump(tmp_path):
    report = _run(tmp_path, [RawEmitter(), ParentOnly()], include_raw=True)
    path = tmp_path / "r.json"
    report_mod.write_json(report, path)
    indented = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"
    assert len(path.read_bytes()) < len(indented.encode("utf-8"))


# ---------------------------------------------------------------------------
# Compacting a report written with raw payloads
# ---------------------------------------------------------------------------
def test_compact_report_drops_raw_payloads_and_keeps_the_scores(tmp_path):
    full = _run(tmp_path / "a", [RawEmitter()], include_raw=True)
    lean = _run(tmp_path / "b", [RawEmitter()])
    compacted = report_mod.compact_report(full)
    records = compacted["items"]["stub_raw"]
    assert all("raw" not in r for r in records)
    assert [r["raw_sha256"] for r in records] == [r["raw_sha256"] for r in lean["items"]["stub_raw"]]
    assert compacted["compaction"]["scoring_digest_recomputed"] == full["scoring_digest"]
    assert compacted["compaction"]["removed_raw_payloads"] == len(records)
    assert compacted["policy"]["raw_payloads"] == report_mod.RAW_PAYLOAD_POLICY_OMITTED


def test_compact_report_rebuilds_the_hash_of_an_old_report_without_raw_sha256(tmp_path):
    full = _run(tmp_path, [RawEmitter()], include_raw=True)
    for record in full["items"]["stub_raw"]:
        del record["raw_sha256"]   # reports written before 2026-10-20 had raw only
    compacted = report_mod.compact_report(full)
    first, second = compacted["items"]["stub_raw"][:2]
    assert first["raw_sha256"] == canonical_sha({"driver": "stub", "item": first["id"], "blob": BIG})
    assert second["raw_sha256"] == canonical_sha({"driver": "stub", "item": second["id"], "blob": "small"})


def test_compact_cli_rewrites_only_when_the_scoring_digest_is_unchanged(tmp_path, capsys):
    full = _run(tmp_path, [RawEmitter()], include_raw=True)
    source = tmp_path / "full.json"
    report_mod.write_json(full, source)
    out = tmp_path / "lean.json"
    assert report_mod.main(["compact", str(source), "--out", str(out)]) == 0
    lean = json.loads(out.read_text(encoding="utf-8"))
    assert lean["compaction"]["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert lean["scoring_digest"] == full["scoring_digest"]
    assert all("raw" not in record for record in lean["items"]["stub_raw"])
    assert "unchanged" in capsys.readouterr().err

    tampered = json.loads(source.read_text(encoding="utf-8"))
    tampered["items"]["stub_raw"][0]["verdict"] = "correct" if tampered["items"]["stub_raw"][0]["verdict"] == "wrong" else "wrong"
    report_mod.write_json(tampered, source)
    refused = tmp_path / "refused.json"
    assert report_mod.main(["compact", str(source), "--out", str(refused)]) == 1
    assert not refused.exists() and "refused" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# --fail-on-hard-gates
# ---------------------------------------------------------------------------
def _gate_report(gates: List[Dict[str, Any]], *, available: bool = True, splits: Sequence[str] = ("test",)) -> Dict[str, Any]:
    return {"baselines": {"sys": {"available": available, "unavailable_reason": None if available else "no node"}},
            "gates": {"sys": {"decision_splits": list(splits), "gates": gates}}}


def _gate(gate_id: str, status: str, hard: bool = True) -> Dict[str, Any]:
    return {"id": gate_id, "hard": hard, "status": status, "metric": "m", "numerator": 0, "denominator": 1}


def test_hard_gate_check_passes_on_pass_and_not_applicable_only():
    report = _gate_report([_gate("HG-1", "pass"), _gate("HG-7", "not_applicable"), _gate("SG-1", "fail", hard=False)])
    assert runner.hard_gate_failures(report, ["sys"]) == {"sys": []}


@pytest.mark.parametrize("status", ["fail", "insufficient_evidence"])
def test_hard_gate_check_fails_on_a_failed_or_empty_hard_gate(status):
    failures = runner.hard_gate_failures(_gate_report([_gate("HG-1", "pass"), _gate("HG-3", status)]), ["sys"])
    assert failures["sys"] == [f"HG-3 {status} (0/1): m"]


def test_hard_gate_check_fails_when_the_baseline_did_not_really_run():
    assert runner.hard_gate_failures(_gate_report([], available=False), ["sys"])["sys"][0].startswith("baseline unavailable")
    assert runner.hard_gate_failures(_gate_report([], splits=()), ["sys"])["sys"] == [
        "no decision split (test, adversarial_holdout) was scored"]
    assert runner.hard_gate_failures(_gate_report([]), ["other"]) == {"other": ["baseline was not run"]}


def _gate_examples() -> List[Dict[str, Any]]:
    """One citation item per hard gate an oracle needs evidence for (labels are inline test data)."""
    def item(ident: str, l2: str) -> Dict[str, Any]:
        return citation(ident, "test", f"가상체류관리법 제5조 {ident}", ["가상체류관리법 제5조"],
                        {"overall": "failed", "layer_codes": {"source_identity": "source_verified", "version_identity": l2}})
    return [
        citation("gate-unavailable", "test", "가상응답장애법 제2조에 따라 신고", ["가상응답장애법 제2조"],
                 {"overall": "verification_unavailable", "layer_codes": {"source_identity": "verification_unavailable"}}),
        item("gate-future", "future_not_yet_effective"),
        item("gate-wrong", "wrong_version"),
        item("gate-outdated", "source_outdated"),
    ]


def _cli(tmp_path: Path, monkeypatch, systems: Sequence[Baseline], names: str, splits: str, gated: str,
         examples: Sequence[Mapping[str, Any]]) -> int:
    bench = write_benchmark(tmp_path, examples)
    monkeypatch.setattr(runner, "create_baselines", lambda _names: list(systems))
    return runner.main(["--benchmark", str(bench), "--baselines", names, "--splits", splits,
                        "--fixtures", str(tmp_path / "sources"), "--backend-python", sys.executable,
                        "--out", str(tmp_path / "r.json"), "--fail-on-hard-gates", gated])


def test_cli_exits_one_when_a_gated_baseline_fails_a_hard_gate(tmp_path, monkeypatch, capsys):
    code = _cli(tmp_path, monkeypatch, [AbsenceClaimer()], "stub_absence", "test,adversarial_holdout", "stub_absence",
                make_examples())
    assert code == 1
    err = capsys.readouterr().err
    assert "hard-gate check: stub_absence FAILED" in err and "HG-1 fail" in err
    assert (tmp_path / "r.json").is_file()   # the report is written before the exit status is decided


def test_cli_exits_zero_when_every_hard_gate_passes_or_is_not_applicable(tmp_path, monkeypatch, capsys):
    code = _cli(tmp_path, monkeypatch, [Oracle()], "stub_oracle", "test", "stub_oracle", _gate_examples())
    err = capsys.readouterr().err
    assert code == 0, err
    assert "hard-gate check: stub_oracle passed" in err


def test_cli_gate_check_on_dev_only_cannot_pass(tmp_path, monkeypatch, capsys):
    examples = [dict(e, split="dev") for e in _gate_examples()]
    assert _cli(tmp_path, monkeypatch, [Oracle()], "stub_oracle", "dev", "stub_oracle", examples) == 1
    assert "no decision split" in capsys.readouterr().err


def test_cli_without_the_flag_keeps_exit_zero_on_a_no_go(tmp_path, monkeypatch):
    bench = write_benchmark(tmp_path, make_examples())
    monkeypatch.setattr(runner, "create_baselines", lambda _names: [AbsenceClaimer()])
    assert runner.main(["--benchmark", str(bench), "--baselines", "stub_absence", "--splits", "test",
                        "--fixtures", str(tmp_path / "sources"), "--backend-python", sys.executable,
                        "--out", str(tmp_path / "r.json")]) == 0


def test_gated_baseline_must_be_one_of_the_baselines(tmp_path, capsys):
    bench = write_benchmark(tmp_path, make_examples())
    with pytest.raises(SystemExit) as stop:
        runner.main(["--benchmark", str(bench), "--baselines", "mock_model", "--splits", "test",
                     "--fail-on-hard-gates", "wlie"])
    assert stop.value.code == 2 and "not in --baselines: wlie" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# --backend-root
# ---------------------------------------------------------------------------
def make_backend_tree(root: Path, body: str = "VALUE = 1\n") -> Path:
    (root / "backend" / "services").mkdir(parents=True, exist_ok=True)
    (root / "backend" / "paradiso_backend.py").write_text(body, encoding="utf-8")
    (root / "backend" / "services" / "law_grounding.py").write_text("X = 2\n", encoding="utf-8")
    return root


def test_backend_dir_follows_the_backend_root(tmp_path):
    ctx = RunContext(repo_root=tmp_path / "repo", backend_python=Path(sys.executable), node=None, scratch_dir=tmp_path)
    assert backend_dir(ctx) == tmp_path / "repo" / "backend"
    ctx.backend_root = make_backend_tree(tmp_path / "other")
    assert backend_dir(ctx) == tmp_path / "other" / "backend"
    assert backend_available(ctx) == (True, "")


def test_a_backend_root_without_a_backend_is_refused(tmp_path):
    with pytest.raises(runner.RunnerError, match="has no backend/paradiso_backend.py"):
        runner.check_backend_root(tmp_path)
    tree = make_backend_tree(tmp_path / "tree")
    with pytest.raises(runner.RunnerError, match="pass the directory that contains backend/"):
        runner.check_backend_root(tree / "backend")
    runner.check_backend_root(tree)   # accepted


def test_cli_reports_a_bad_backend_root_as_a_usage_error(tmp_path, capsys):
    bench = write_benchmark(tmp_path, make_examples())
    code = runner.main(["--benchmark", str(bench), "--baselines", "mock_model", "--splits", "test",
                        "--fixtures", str(tmp_path / "sources"), "--backend-root", str(tmp_path / "nowhere")])
    assert code == 2 and "--backend-root" in capsys.readouterr().err


def test_report_records_the_backend_tree_it_measured(tmp_path):
    tree = make_backend_tree(tmp_path / "archive")
    report = _run(tmp_path / "run", [BackendStub()], backend_root=tree)
    backend = report["environment"]["backend"]
    assert backend["root"] == str(tree.resolve()) and backend["separate_from_repo_root"] is True
    assert backend["files"] == 2 and backend["git"] is None   # an archive extraction is not a git work tree
    assert backend["content_sha256"] == report_mod.backend_tree(tree, separate=True)["content_sha256"]
    measured = report["environment"]["measured_files"]["backend/paradiso_backend.py"]
    assert measured == hashlib.sha256(b"VALUE = 1\n").hexdigest()
    assert not any(path.startswith("backend/") for path in report["environment"]["git_dirty_paths"])
    text = report_mod.render_markdown(report)
    assert "Backend for b1_python, b1_python_raw and existing_law" in text and "separate from the repo root" in text


def test_default_backend_is_the_repo_root_and_is_hashed_only_when_used(tmp_path):
    report = _run(tmp_path, [ParentOnly()])
    backend = report["environment"]["backend"]
    assert backend["separate_from_repo_root"] is False
    assert backend["root"] == str(runner.REPO_ROOT.resolve())
    assert backend["content_sha256"] is None and backend["not_hashed"]   # no baseline imported the backend


def test_backend_digest_is_deterministic_and_skips_bytecode_state_and_dot_files(tmp_path):
    tree = make_backend_tree(tmp_path / "t")
    digest = report_mod.backend_tree(tree, separate=True)["content_sha256"]
    for rel, text in (("backend/__pycache__/x.cpython-311.pyc", "bytecode"), ("backend/var/safety.log", "state"),
                      ("backend/services/y.pyc", "bytecode"), ("backend/.pytest_cache/v", "cache")):
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text, encoding="utf-8")
    secret = tree / "backend" / ".env"
    secret.write_text("NOT_A_REAL_KEY=placeholder\n", encoding="utf-8")
    os.chmod(secret, 0)   # a .env is never opened, so an unreadable one changes nothing
    try:
        again = report_mod.backend_tree(tree, separate=True)
    finally:
        os.chmod(secret, 0o600)
    assert again["content_sha256"] == digest and again["files"] == 2
    (tree / "backend" / "services" / "law_grounding.py").write_text("X = 3\n", encoding="utf-8")
    assert report_mod.backend_tree(tree, separate=True)["content_sha256"] != digest


def test_backend_root_does_not_change_the_scores_of_in_process_baselines(tmp_path):
    plain = _run(tmp_path / "a", [ParentOnly()])
    moved = _run(tmp_path / "b", [ParentOnly()], backend_root=make_backend_tree(tmp_path / "tree"))
    assert plain["scoring_digest"] == moved["scoring_digest"]
    assert items_of(plain, "stub_parent_only").keys() == items_of(moved, "stub_parent_only").keys()
