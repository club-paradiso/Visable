"""Subprocess baselines: the backend (B1, existing_law) and the JS resolver (B2).

These run the real backend / JS code in child processes on the tiny inline
benchmark. They skip cleanly when the backend interpreter cannot import the
backend (wrong interpreter, sparse checkout without backend/) or when Node is
not installed. No test here opens a network connection: the drivers disable
sockets before importing backend code, and the existing-law driver answers
every law.go.kr request from the inline bundle.

Assertions are limited to behaviour that does not depend on in-flight backend
fixes: the backend pins no law version (so it accepts a claim drawn from a
not-yet-effective version), B1 reads no subcode from free text, and the fake
DRF bodies parse with the backend's own parser.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from waymaker_ai.evaluation import runner
from waymaker_ai.evaluation.baselines.base import RunContext, child_env

from tests.test_evaluation_runner import EXPERIMENT_ROOT, config_for, items_of, make_examples, write_benchmark

REPO_ROOT = EXPERIMENT_ROOT.parents[1]
BACKEND = REPO_ROOT / "backend"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture(scope="module")
def backend_python(tmp_path_factory) -> Path:
    """This interpreter, if it can import the backend in the drivers' minimal environment."""
    if not (BACKEND / "paradiso_backend.py").is_file():
        pytest.skip("backend/ is not present in this checkout")
    scratch = tmp_path_factory.mktemp("probe")
    env = child_env(RunContext(repo_root=REPO_ROOT, backend_python=Path(sys.executable), node=None,
                               scratch_dir=scratch), {"LAW_GROUNDING_MODE": "disabled"})
    probe = ("import sys; sys.path.insert(0, sys.argv[1]); import paradiso_backend; "
             "from services import law_grounding, law_tools, grounding_config")
    proc = subprocess.run([sys.executable, "-B", "-s", "-W", "ignore", "-c", probe, str(BACKEND)],
                          capture_output=True, env=env, cwd=str(scratch), timeout=120, check=False)
    if proc.returncode != 0:
        pytest.skip("this interpreter cannot import the backend (run with the backend venv python)")
    return Path(sys.executable)


def test_child_environment_inherits_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("LAW_API_OC", "must-not-reach-the-child")
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-reach-the-child")
    env = child_env(RunContext(repo_root=REPO_ROOT, backend_python=Path(sys.executable), node=None,
                               scratch_dir=tmp_path))
    assert "must-not-reach-the-child" not in "".join(env.values())
    assert env["PYTHONHASHSEED"] == "0" and env["WAYMAKER_KNOWLEDGE_DB"] == ":memory:"
    assert env["LOG_LEVEL"] == "ERROR" and env["PATH"] == "/usr/bin:/bin"
    assert not any("KEY" in name or name.endswith("_OC") for name in env)


def test_b1_python_reads_no_subcode_from_text_but_keeps_a_payload_subcode(tmp_path, backend_python):
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, ["b1_python", "b1_python_raw"], ["dev", "test"]))
    assert report["baselines"]["b1_python"]["available"], report["baselines"]["b1_python"]
    b1 = items_of(report, "b1_python")
    assert {r["status"] for r in b1.values()} == {"ok"}, {k: r["error"] for k, r in b1.items()}
    text_item = b1["cls-0001"]["prediction"]                    # "E-7-4 연장 서류"
    assert (text_item["status_code"], text_item["subcode"]) == ("E-7", None)
    assert text_item["procedure_coarse"] == "extension" and text_item["procedure_fine"] is None
    assert b1["cls-0001"]["flags"] == ["parent_fallback"]
    assert b1["cls-0003"]["prediction"]["subcode"] == "E-7-1"   # payload_status_code reaches the backend
    assert b1["cls-0001"]["metrics"]["procedure_fine"] == ["not_scorable", "baseline_emits_coarse_only"]
    process = report["baselines"]["b1_python"]["process"]
    assert process["pythonhashseed"] == "0" and process["hash_randomization"] == 0
    raw_view = items_of(report, "b1_python_raw")["cls-0001"]["prediction"]
    assert raw_view["subcode"] is None


def test_existing_law_against_the_fake_drf_server(tmp_path, backend_python):
    bench = write_benchmark(tmp_path, make_examples())
    # include_raw: the call log below lives in the raw payload, which reports omit by default.
    report = runner.run_evaluation(config_for(tmp_path, bench, ["existing_law"], ["test", "adversarial_holdout"],
                                              include_raw=True))
    records = items_of(report, "existing_law")
    assert {r["status"] for r in records.values()} == {"ok"}, {k: r["error"] for k, r in records.items()}

    # The fake lawService.do body parses with the backend's own parser: the article is found.
    plain = records["cit-0001"]
    assert plain["prediction"]["layer_codes"]["citation_identity"] == "citation_verified"
    assert plain["upstream_calls"] >= 2

    # The backend pins no version, so a claim drawn from a not-yet-effective version is accepted.
    future = records["cit-0003"]
    assert future["prediction"]["overall"] == "verified_partial"
    assert "accepted_future_not_yet_effective" in future["critical_categories"]
    assert "quoted_text_has_no_backend_channel" in future["notes"]

    # The scripted HTML fault reached the backend through its real transport.
    faulted = records["cit-0002"]
    calls = faulted["raw"]["calls"]
    assert any((call.get("fault") or "").startswith("resolve_title:unavailable_parse:html") for call in calls)
    assert faulted["prediction"]["overall"] in ("failed", "verification_unavailable")
    assert all("OC" not in call["params"] for call in calls)   # the credential is never logged


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_b2_js_resolver_reports_exact_subcodes_and_skips_payload_items(tmp_path):
    for rel in ("assets/js/status-guidance.js", "assets/js/search-router.js", "data/status-guidance-202609.json"):
        if not (REPO_ROOT / rel).is_file():
            pytest.skip(f"{rel} is not present in this checkout")
    bench = write_benchmark(tmp_path, make_examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, ["b2_js"], ["dev", "test"], node="node"))
    records = items_of(report, "b2_js")
    assert records["cls-0003"]["status"] == "not_equivalent_input"
    first = records["cls-0001"]
    assert first["status"] == "ok", first["error"]
    assert (first["prediction"]["status_code"], first["prediction"]["subcode"]) == ("E-7", "E-7-4")
    assert first["prediction"]["procedure_fine"] == "extension"
    assert first["memory_kind"] == "js_heap_used"
    assert report["baselines"]["b2_js"]["process"]["node"].startswith("v")


def test_unreachable_backend_interpreter_is_unavailable_not_a_crash(tmp_path):
    bench = write_benchmark(tmp_path, make_examples())
    config = config_for(tmp_path, bench, ["b1_python"], ["test"])
    config.backend_python = tmp_path / "no-such-python"
    report = runner.run_evaluation(config)
    assert report["baselines"]["b1_python"]["available"] is False
    assert os.fspath(config.backend_python) in report["baselines"]["b1_python"]["unavailable_reason"]
