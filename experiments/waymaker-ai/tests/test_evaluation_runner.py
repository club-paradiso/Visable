"""The runner end to end on a tiny inline benchmark (never the real benchmark files).

What is pinned here: per-baseline / per-split scoring, the train split never
being scored, determinism of the scoring digest, false absences and accepted
future versions listed as critical legal errors, invalid examples and manifest
mismatches reported rather than repaired, crashes and unavailable baselines
counted as not scorable, the held-out ledger, the contamination check, and
that the evaluation package imports nothing outside the standard library.

The inline source bundle uses fictional law names only (가상체류관리법,
가상응답장애법) and ``synthetic_fixture`` provenance.
"""
from __future__ import annotations

import ast
import hashlib
import json
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pytest

from waymaker_ai.evaluation import runner
from waymaker_ai.evaluation.baselines.base import Baseline, EvalItem, ItemResult, RunContext
from waymaker_ai.evaluation.baselines.model import MockModel
from waymaker_ai.evaluation.benchmark import load_benchmark

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any socket connection from this process fails the test (child processes block their own)."""
    def refuse(*_args, **_kwargs):
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


# ---------------------------------------------------------------------------
# Inline fixtures
# ---------------------------------------------------------------------------
BUNDLE_ID = "eval-syn"
ACT = "EVAL-ACT-0001"


def _version(version_id: str, effective: str, *, changed: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"stable_id": ACT, "version_id": version_id, "effective_date": effective,
            "promulgation_date": effective, "promulgation_no": f"가상법률 제{version_id[-1]}호",
            "amendment_type": "일부개정", "end_date": None, "provision_effective_dates": {}, "official_url": None,
            "retrieved_at": None, "content_sha256": None, "parse_status": "complete",
            "provenance": "synthetic_fixture", "has_transitional_provisions": False, "is_repeal": False,
            "changed_provisions": changed}


def _provision(version_id: str, effective: str, key: str, text: str, *, kind: str = "article",
               heading: Optional[str] = None) -> Dict[str, Any]:
    suffix = f"heading-{key}" if kind == "heading" else key
    return {"evidence_id": f"{BUNDLE_ID}:{ACT}:{version_id}@{effective}:{suffix}", "stable_id": ACT,
            "version_id": version_id, "effective_date": effective, "provision_key": key, "unit_kind": kind,
            "heading": heading, "text": text, "paragraphs": {}, "items": {}, "scope": None, "official_url": None,
            "provenance": "synthetic_fixture"}


def make_bundle() -> Dict[str, Any]:
    return {
        "bundle_id": BUNDLE_ID, "bundle_version": 1, "provenance": "synthetic_fixture",
        "attribution": "Synthetic evaluation-runner test fixture. Every law in it is fictional.",
        "captured_at": None, "title_index_coverage": "complete", "history_coverage": {ACT: "complete"},
        "identities": [{"provider": "synthetic", "family": "statute", "stable_id": ACT,
                        "official_title": "가상체류관리법", "former_titles": [], "short_titles": [],
                        "competent_ministry": "가상법무부"}],
        "versions": [_version("EVAL-V1", "2020-01-01"), _version("EVAL-V2", "2027-06-01", changed=["제5조"])],
        "provisions": [
            _provision("EVAL-V1", "2020-01-01", "제1조", "제1장 총칙", kind="heading"),
            _provision("EVAL-V1", "2020-01-01", "제5조",
                       "제5조(가상 신고) 가상체류자는 체류지를 변경한 날부터 14일 이내에 신고하여야 한다.",
                       heading="가상 신고"),
            _provision("EVAL-V2", "2027-06-01", "제5조",
                       "제5조(가상 신고) 가상체류자는 체류지를 변경한 날부터 20일 이내에 신고하여야 한다.",
                       heading="가상 신고"),
        ],
        "addenda": [], "guidance": [],
        "faults": [{"operation": "resolve_title", "match": {"title": "가상응답장애법"}, "status": "unavailable_parse",
                    "raw_body_kind": "html", "detail": "search returned an HTML page"}],
    }


def make_example(ident: str, task: str, split: str, question: str, expected: Dict[str, Any], *,
                 critical: bool = False, cls: Optional[str] = None, anchor: Optional[str] = None,
                 label: str = "machine_checked", **inp: Any) -> Dict[str, Any]:
    return {
        "id": ident, "schema_version": "waymaker-example/0.1", "suite": "classification", "task": task,
        "language": "ko", "input": {"question": question, **inp}, "expected": expected,
        "scenario": {"adversarial_class": cls, "relevant_dates": {"question_date": "2026-10-19"}, "anchor": anchor},
        "source_refs": [], "provenance": {"authoring": "synthetic_authored", "authored_by": "test",
                                          "created_at": "2026-10-19", "license": "test",
                                          "contains_personal_data": False},
        "label_review": {"status": label, "checks": []}, "split": split, "critical": critical,
        "revision": 1, "revision_history": [],
    }


def citation(ident: str, split: str, text: str, cites: Sequence[str], expected: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    claim = {"text": text, "citations": list(cites)}
    claim.update(kw.pop("claim_extra", {}))
    return make_example(ident, "citation_verification", split, text, expected, fixture_set=BUNDLE_ID,
                        anchor="question_date", claim=claim, **kw)


def make_examples() -> List[Dict[str, Any]]:
    return [
        make_example("cls-0001", "status_procedure_classification", "dev", "E-7-4 연장 서류",
                     {"status_code": "E-7", "subcode": "E-7-4", "procedure": "extension"}, critical=True, cls="I"),
        make_example("cls-0002", "status_procedure_classification", "test", "D-2 연장 서류",
                     {"status_code": "D-2", "subcode": None, "procedure": "extension"}),
        make_example("cls-0003", "status_procedure_classification", "test", "연장 서류",
                     {"status_code": "E-7", "subcode": "E-7-1", "procedure": "extension"},
                     payload_status_code="E-7-1"),
        make_example("cls-0004", "status_procedure_classification", "train", "학습 전용 문장",
                     {"status_code": "D-2", "subcode": None, "procedure": "extension"}),
        make_example("ent-0001", "entity_date_extraction", "test", "2026년 11월 3일에 체류기간이 끝나요",
                     {"dates": [{"value": "2026-11-03", "role": "stay_expiry_date"}]}),
        citation("cit-0001", "test", "가상체류관리법 제5조에 따라 14일 이내에 신고하여야 한다.", ["가상체류관리법 제5조"],
                 {"overall": "human_review_required", "layer_codes": {"source_identity": "source_verified"}}),
        citation("cit-0002", "adversarial_holdout", "가상응답장애법 제2조에 따라 신고하여야 한다.", ["가상응답장애법 제2조"],
                 {"overall": "verification_unavailable", "layer_codes": {"source_identity": "verification_unavailable"},
                  "forbidden_codes": ["source_not_found"]}, critical=True, cls="H"),
        citation("cit-0003", "adversarial_holdout", "가상체류관리법 제5조에 따라 20일 이내에 신고하여야 한다.",
                 ["가상체류관리법 제5조"],
                 {"overall": "failed", "layer_codes": {"source_identity": "source_verified",
                                                       "version_identity": "future_not_yet_effective"}},
                 critical=True, cls="E",
                 claim_extra={"quoted_text": "변경한 날부터 20일 이내에 신고하여야 한다", "numbers": ["20일"]}),
        make_example("tmp-0001", "temporal_version_selection", "test", "가상체류관리법 제5조 현재 버전",
                     {"candidate_version_keys": [["EVAL-V1", "2020-01-01"]], "warnings": ["future_version_pending"],
                      "forbidden_warnings": ["anchor_missing"]}, fixture_set=BUNDLE_ID, anchor="question_date",
                     temporal_query={"stable_id": ACT, "provision": "제5조", "anchor": "question_date"}),
        make_example("abs-0001", "abstention", "test", "제가 내년에 허가를 받을 수 있을까요?",
                     {"must_withhold_conclusion": True, "required_issue_keys": ["insufficient_context"]}),
    ]


def write_benchmark(root: Path, examples: Sequence[Mapping[str, Any]], *, manifest: bool = True,
                    extra_lines: Sequence[str] = ()) -> Path:
    bench = root / "bench"
    bench.mkdir(parents=True, exist_ok=True)
    path = bench / "examples.jsonl"
    lines = [json.dumps(ex, ensure_ascii=False) for ex in examples] + list(extra_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if manifest:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        (bench / "MANIFEST.json").write_text(json.dumps({"files": [{"path": "examples.jsonl", "sha256": digest}]}),
                                             encoding="utf-8")
    sources = root / "sources"
    sources.mkdir(exist_ok=True)
    (sources / f"{BUNDLE_ID}.json").write_text(json.dumps(make_bundle(), ensure_ascii=False), encoding="utf-8")
    return bench


def config_for(root: Path, bench: Path, baselines: Sequence[str], splits: Sequence[str], **kw: Any) -> runner.RunConfig:
    return runner.RunConfig(benchmark=bench, baselines=list(baselines), splits=list(splits),
                            fixtures=root / "sources", backend_python=Path(sys.executable), **kw)


# ---------------------------------------------------------------------------
# Stub baselines (in-process, deterministic)
# ---------------------------------------------------------------------------
class ParentOnly(Baseline):
    """Answers the parent and never a subcode: the silent-parent failure."""

    name = "stub_parent_only"
    emits = {"status_procedure_classification": frozenset({"status_code", "subcode", "procedure_coarse"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        out = {}
        for item in items:
            expected = item.example["expected"]
            out[item.id] = ItemResult(item.id, "ok", prediction={
                "status_code": expected["status_code"], "subcode": None, "procedure_fine": None,
                "procedure_coarse": "extension"}, latency_ms=1.0, upstream_calls=0)
        return out


class AbsenceClaimer(Baseline):
    """Declares every cited law absent: the failure-is-not-absence violation."""

    name = "stub_absence"
    emits = {"citation_verification": frozenset({"overall", "layer_codes", "codes"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        return {item.id: ItemResult(item.id, "ok", prediction={
            "overall": "failed", "layer_codes": {"source_identity": "source_not_found"},
            "codes": ["source_not_found"]}, upstream_calls=1) for item in items}


class Accepter(Baseline):
    """Accepts every claim at L1 and L3: the existing backend's shape of answer."""

    name = "stub_accepter"
    emits = {"citation_verification": frozenset({"overall", "layer_codes", "codes", "highest_verified_layer"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        layers = {"source_identity": "source_verified", "citation_identity": "citation_verified"}
        return {item.id: ItemResult(item.id, "ok", prediction={
            "overall": "verified_partial", "layer_codes": layers, "codes": sorted(layers.values()),
            "highest_verified_layer": 1}) for item in items}


class Crasher(Baseline):
    name = "stub_crash"
    emits = {"status_procedure_classification": frozenset({"status_code"})}

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        raise RuntimeError("boom")


class NeverAvailable(Baseline):
    name = "stub_unavailable"
    emits = {"status_procedure_classification": frozenset({"status_code"})}

    def available(self, ctx: RunContext):
        return False, "dependency missing"


def items_of(report: Mapping[str, Any], baseline: str) -> Dict[str, Dict[str, Any]]:
    return {record["id"]: record for record in report["items"][baseline]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_scores_per_baseline_and_split_and_never_the_train_split(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["dev", "test"]), baselines=[ParentOnly()])
    records = items_of(report, "stub_parent_only")
    assert sorted(records) == ["cls-0001", "cls-0002", "cls-0003"]   # cls-0004 is train: never scored
    assert set(report["results"]["stub_parent_only"]) == {"dev", "test"}
    dev = report["headline"]["stub_parent_only"]["dev"]
    assert dev["classification.subcode_exact_accuracy"]["numerator"] == 0
    assert dev["classification.hierarchy_violations"]["numerator"] == 1
    assert records["cls-0001"]["flags"] == ["parent_fallback"]
    assert report["critical_legal_errors"]["stub_parent_only"][0]["example_id"] == "cls-0001"
    # The text-only slice drops the payload item.
    text_only = report["headline_text_only"]["stub_parent_only"]["test"]["classification.status_exact_accuracy"]
    assert text_only["denominator"] == 1
    assert report["headline"]["stub_parent_only"]["test"]["classification.status_exact_accuracy"]["denominator"] == 2


def test_train_split_cannot_be_requested(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    with pytest.raises(runner.RunnerError):
        runner.run_evaluation(config_for(tmp_path, bench, [], ["train"]), baselines=[ParentOnly()])


def test_false_absence_and_accepted_future_version_are_critical_legal_errors(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test", "adversarial_holdout"]),
                                   baselines=[AbsenceClaimer(), Accepter()])
    absence = {e["example_id"]: e["categories"] for e in report["critical_legal_errors"]["stub_absence"]}
    assert absence["cit-0002"] == ["critical_example_wrong", "false_absence_declaration"]
    head = report["headline"]["stub_absence"]["adversarial_holdout"]
    assert head["citation.false_absence_declarations"]["numerator"] == 1
    assert report["gates"]["stub_absence"]["decision"] == "NO_GO"

    accepted = {e["example_id"]: e["categories"] for e in report["critical_legal_errors"]["stub_accepter"]}
    assert "accepted_future_not_yet_effective" in accepted["cit-0003"]
    gate = next(g for g in report["gates"]["stub_accepter"]["gates"] if g["id"] == "HG-2")
    assert (gate["status"], gate["numerator"]) == ("fail", 1)


def test_scoring_digest_is_deterministic(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    config = config_for(tmp_path, bench, [], ["dev", "test", "adversarial_holdout"])
    first = runner.run_evaluation(config, baselines=[ParentOnly(), AbsenceClaimer(), MockModel()])
    second = runner.run_evaluation(config, baselines=[ParentOnly(), AbsenceClaimer(), MockModel()])
    assert first["scoring_digest"] == second["scoring_digest"]
    strip = ("latency_ms", "peak_memory_bytes")
    for name in first["items"]:
        a = [{k: v for k, v in r.items() if k not in strip} for r in first["items"][name]]
        b = [{k: v for k, v in r.items() if k not in strip} for r in second["items"][name]]
        assert a == b
    assert json.dumps(first["results"], sort_keys=True) == json.dumps(second["results"], sort_keys=True)


def test_invalid_examples_are_reported_and_left_out(tmp_path):
    bench = write_benchmark(tmp_path, make_examples(), extra_lines=["{not json", json.dumps({"id": "x-1"})])
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"]), baselines=[ParentOnly()])
    reasons = [entry["reason"] for entry in report["benchmark"]["invalid_examples"]]
    assert len(reasons) == 2 and reasons[0].startswith("invalid JSON") and reasons[1] == "missing task"


def test_manifest_mismatch_is_reported_never_fixed(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    (bench / "MANIFEST.json").write_text(json.dumps({"files": [{"path": "examples.jsonl", "sha256": "0" * 64}]}),
                                         encoding="utf-8")
    loaded = load_benchmark(bench)
    assert not loaded.manifest.ok and loaded.manifest.mismatches[0]["path"] == "examples.jsonl"
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"]), baselines=[ParentOnly()])
    assert report["benchmark"]["manifest"]["ok"] is False
    assert report["benchmark"]["manifest"]["manifest_files"][0]["sha256"]


def test_crash_is_counted_not_scored_and_fails_the_crash_gate(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"]), baselines=[Crasher()])
    records = items_of(report, "stub_crash")
    assert {r["status"] for r in records.values()} == {"error"}
    assert all(r["verdict"] == "not_scorable" for r in records.values())
    assert report["not_scorable"]["stub_crash"]["test"]["baseline_error"] > 0
    gate = next(g for g in report["gates"]["stub_crash"]["gates"] if g["id"] == "HG-9")
    assert gate["status"] == "fail" and report["gates"]["stub_crash"]["decision"] == "NO_GO"


def test_unavailable_baseline_is_reported_with_its_reason(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"]), baselines=[NeverAvailable()])
    assert report["baselines"]["stub_unavailable"]["available"] is False
    assert report["baselines"]["stub_unavailable"]["unavailable_reason"] == "dependency missing"
    assert {r["status"] for r in report["items"]["stub_unavailable"]} == {"unavailable"}
    assert report["gates"]["stub_unavailable"]["decision"] == "INSUFFICIENT_EVIDENCE"


def test_mock_model_runs_the_structured_output_path(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"]), baselines=[MockModel()])
    records = items_of(report, "mock_model")
    assert set(records) == {"cls-0002", "cls-0003", "ent-0001", "abs-0001"}   # never citation / temporal
    assert records["abs-0001"]["metrics"]["withhold_correct"][0] == "correct"
    assert records["abs-0001"]["metrics"]["required_issues_covered"][0] == "wrong"
    head = report["headline"]["mock_model"]["test"]
    assert head["model.structured_output_valid_rate"]["value"] == 1.0
    assert records["cls-0002"]["upstream_calls"] == 1 and records["cls-0002"]["tokens"] is None


def test_markdown_names_provenance_errors_and_gates(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test", "adversarial_holdout"]),
                                   baselines=[AbsenceClaimer()])
    text = runner.report_mod.render_markdown(report)
    for needle in ("scoring digest", "manifest verified", "## Critical legal errors", "false_absence_declaration",
                   "project hypotheses", "NO_GO", "Wilson", "## Verdicts per adversarial class"):
        assert needle in text, needle


def test_cli_writes_report_files_and_the_exact_command(tmp_path, capsys):
    bench = write_benchmark(tmp_path, make_examples())
    out, md = tmp_path / "r.json", tmp_path / "r.md"
    code = runner.main(["--benchmark", str(bench), "--baselines", "mock_model", "--splits", "test",
                        "--fixtures", str(tmp_path / "sources"), "--backend-python", sys.executable,
                        "--out", str(out), "--markdown", str(md)])
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["command"]["argv"][1:4] == ["-m", "waymaker_ai.evaluation.runner", "--benchmark"]
    assert report["environment"]["python"] and "git_commit" in report["environment"]
    assert md.read_text(encoding="utf-8").startswith("# Waymaker evaluation report")
    assert "scoring digest" in capsys.readouterr().err


def test_cli_rejects_an_unknown_baseline(tmp_path, capsys):
    bench = write_benchmark(tmp_path, make_examples())
    assert runner.main(["--benchmark", str(bench), "--baselines", "nope", "--splits", "test"]) == 2
    assert "unknown baseline" in capsys.readouterr().err


def test_holdout_ledger_marks_a_second_run_as_a_repeat(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    ledger = tmp_path / "ledger.jsonl"
    config = config_for(tmp_path, bench, [], ["adversarial_holdout"], holdout_ledger=ledger)
    first = runner.run_evaluation(config, baselines=[AbsenceClaimer()])
    second = runner.run_evaluation(config, baselines=[AbsenceClaimer()])
    assert first["holdout_ledger"]["repeat"] is False
    assert second["holdout_ledger"] == {"path": str(ledger), "prior_runs_for_this_benchmark": 1, "repeat": True}
    assert first["scoring_digest"] == second["scoring_digest"]   # the ledger is not part of the score


def test_a_post_hoc_holdout_run_is_recorded_as_one_even_under_a_new_digest(tmp_path):
    # A relabel changes the benchmark digest, so the digest count says "first look".
    # A declared post-hoc run must say otherwise, in the ledger, the report and the Markdown.
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps({"benchmark_digest": "0" * 64, "generated_at": "2026-10-19T00:00:00+00:00",
                                  "git_commit": None, "baselines": ["x"]}) + "\n", encoding="utf-8")
    bench = write_benchmark(tmp_path, make_examples())
    config = config_for(tmp_path, bench, [], ["adversarial_holdout"], holdout_ledger=ledger,
                        holdout_post_hoc="  relabelled after   spec decisions ")
    report = runner.run_evaluation(config, baselines=[AbsenceClaimer()])
    assert report["holdout_ledger"] == {"path": str(ledger), "prior_runs_for_this_benchmark": 0, "repeat": False,
                                        "post_hoc": True, "post_hoc_reason": "relabelled after spec decisions",
                                        "prior_ledger_entries": 1}
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["post_hoc"] is True and entry["post_hoc_reason"] == "relabelled after spec decisions"
    assert entry["prior_ledger_entries"] == 1 and entry["benchmark_digest"] == report["benchmark"]["digest"]
    assert "POST-HOC RE-SCORING" in runner.report_mod.render_markdown(report)
    plain = runner.run_evaluation(config_for(tmp_path, bench, [], ["adversarial_holdout"], holdout_ledger=ledger),
                                  baselines=[AbsenceClaimer()])
    assert "post_hoc" not in plain["holdout_ledger"] and plain["scoring_digest"] == report["scoring_digest"]


def test_cli_refuses_a_post_hoc_run_without_a_ledger_or_a_reason(tmp_path, capsys):
    bench = write_benchmark(tmp_path, make_examples())
    base = ["--benchmark", str(bench), "--baselines", "mock_model", "--splits", "adversarial_holdout"]
    with pytest.raises(SystemExit):
        runner.parse_args(base + ["--holdout-post-hoc", "relabelled"])
    with pytest.raises(SystemExit):
        runner.parse_args(base + ["--holdout-ledger", str(tmp_path / "l.jsonl"), "--holdout-post-hoc", " "])
    assert "--holdout-post-hoc" in capsys.readouterr().err
    config = runner.parse_args(base + ["--holdout-ledger", str(tmp_path / "l.jsonl"), "--holdout-post-hoc", "x"])
    assert config.holdout_post_hoc == "x"


def test_contamination_check_finds_exact_normalized_overlap(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    train = tmp_path / "train.jsonl"
    train.write_text(json.dumps({"messages": [{"role": "user", "content": "D-2   연장 서류"}]}, ensure_ascii=False)
                     + "\n" + json.dumps({"input": {"question": "전혀 다른 질문"}}, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    report = runner.run_evaluation(config_for(tmp_path, bench, [], ["test"], contamination_files=[train]),
                                   baselines=[ParentOnly()])
    assert report["contamination"]["overlaps"] == {"cls-0002": ["train.jsonl"]}


# ---------------------------------------------------------------------------
# The evaluation package stays standard-library only
# ---------------------------------------------------------------------------
def _imported_roots(path: Path) -> List[str]:
    roots = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append(node.module.split(".")[0])
    return roots


def test_runner_side_imports_only_the_standard_library_and_the_experiment():
    package = EXPERIMENT_ROOT / "waymaker_ai" / "evaluation"
    allowed = set(sys.stdlib_module_names) | {"waymaker_ai"}
    for path in sorted(package.rglob("*.py")):
        if "drivers" in path.parts:
            continue   # drivers run inside the backend interpreter, never in the runner
        bad = sorted(set(_imported_roots(path)) - allowed)
        assert not bad, f"{path.relative_to(EXPERIMENT_ROOT)} imports {bad}"


def test_drivers_import_backend_code_only_after_blocking_sockets():
    drivers = EXPERIMENT_ROOT / "waymaker_ai" / "evaluation" / "drivers"
    for name in ("b1_driver.py", "existing_law_driver.py"):
        text = (drivers / name).read_text(encoding="utf-8")
        main = text[text.index("def main()"):]
        assert main.index("_block_network()") < main.index("from services")


def test_command_output_keeps_the_leading_porcelain_status_column():
    # ``git status --porcelain`` prints " M backend/x.py"; stripping the leading
    # space turned the first dirty path into "ackend/x.py" in a real report.
    from waymaker_ai.evaluation import report as report_mod

    out = report_mod._run([sys.executable, "-c", "print(' M backend/x.py'); print('?? docs/y.md')"])
    lines = out.splitlines()
    assert [line[3:] for line in lines] == ["backend/x.py", "docs/y.md"]
