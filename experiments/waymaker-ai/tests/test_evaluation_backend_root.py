"""--backend-root drives the real existing-law driver against another backend tree.

The tree here is a stub backend written into tmp_path: a ``services`` package
with exactly the names the driver imports, and a ``law_grounding`` that sends
its law.go.kr request through ``urllib.request.build_opener().open`` (the
transport the in-progress law_tools fix of 2026-10-20 uses) instead of
``urllib.request.urlopen``. It runs under this interpreter: the stub needs only
the standard library, so the test never needs the backend's dependencies.

What is pinned:

* the subprocess baselines import the backend under ``--backend-root``, not
  the repository's own backend;
* a request made through any urllib opener reaches the fake law.go.kr;
* a connection that bypasses the fake (hits the disabled socket) makes the item
  an ``error``, never a scored "unavailable".
"""
from __future__ import annotations

from pathlib import Path

import pytest

from waymaker_ai.evaluation import runner

from tests.test_evaluation_runner import (
    citation,
    config_for,
    items_of,
    no_network,  # noqa: F401  (autouse fixture: any socket connection from this process fails the test)
    write_benchmark,
)

STUB_GROUNDING = '''\
"""Stub law grounding for the evaluation tests: one title search per claim."""
import json
import socket
import urllib.request
from urllib.parse import quote

load_grounding_config = None
STUB_MARKER = "stub-backend-for-waymaker-eval-tests"


def build_law_grounding_context(question):
    if "SOCKET" in question:
        try:
            socket.create_connection(("127.0.0.1", 9), timeout=1)
        except OSError:
            pass
        return {"attempted": True, "citation_verification": {"status": "error", "citations": [
            {"raw": question, "verification_status": "error", "warnings": ["SOURCE_UNAVAILABLE"]}]}}
    url = "https://www.law.go.kr/DRF/lawSearch.do?OC=placeholder&target=law&type=JSON&query=" + quote("가상체류관리법")
    opener = urllib.request.build_opener()
    with opener.open(urllib.request.Request(url), timeout=5) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    rows = (body.get("LawSearch") or {}).get("law") or []
    found = any(row.get("법령명한글") == "가상체류관리법" for row in rows)
    status = "source_linked_unverified" if found else "failed_verification"
    warnings = [] if found else ["CITED_LAW_NOT_FOUND"]
    return {"attempted": True, "law_search_queries": ["가상체류관리법"],
            "citation_verification": {"status": status, "citations": [
                {"raw": question, "law_name": "가상체류관리법", "verification_status": status, "warnings": warnings}]}}
'''

STUB_FILES = {
    "backend/paradiso_backend.py": '"""Stub: the availability check only needs the file."""\n',
    "backend/services/__init__.py": "",
    "backend/services/law_grounding.py": STUB_GROUNDING,
    "backend/services/law_cloud_fallback.py": "_PAGE_CACHE = {}\n",
    "backend/services/law_tools.py": (
        "load_grounding_config = None\nLAW_TOOL_LAYER_VERSION = 'stub'\n\n\ndef get_law_detail(**kwargs):\n"
        "    return {}\n"),
    "backend/services/citation_verifier.py": (
        "def extract_korean_legal_citations(question):\n    return {'citations': [question]}\n"),
    "backend/services/grounding_config.py": (
        "class GroundingConfig:\n    def __init__(self, **kwargs):\n        self.__dict__.update(kwargs)\n"),
}


def make_stub_backend(root: Path) -> Path:
    for rel, text in STUB_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _examples():
    return [
        citation("cit-opener", "test", "가상체류관리법 제5조에 따라 14일 이내에 신고하여야 한다.", ["가상체류관리법 제5조"],
                 {"overall": "human_review_required", "layer_codes": {"source_identity": "source_verified"}}),
        citation("cit-socket", "test", "SOCKET 가상체류관리법 제5조", ["가상체류관리법 제5조"],
                 {"overall": "verification_unavailable", "layer_codes": {"source_identity": "verification_unavailable"}}),
    ]


def test_existing_law_runs_against_the_backend_root_through_any_urllib_opener(tmp_path):
    tree = make_stub_backend(tmp_path / "archive")
    bench = write_benchmark(tmp_path, _examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, ["existing_law"], ["test"], backend_root=tree,
                                              include_raw=True))
    info = report["baselines"]["existing_law"]
    assert info["available"], info
    records = items_of(report, "existing_law")

    opener = records["cit-opener"]
    assert opener["status"] == "ok", opener["error"]
    assert opener["upstream_calls"] == 1                         # the build_opener() request reached the fake
    assert opener["raw"]["calls"][0]["operation"] == "search"
    assert opener["prediction"]["layer_codes"]["source_identity"] == "source_verified"
    assert opener["raw"]["blocked_network_attempts"] == 0

    backend = report["environment"]["backend"]
    assert backend["root"] == str(tree.resolve()) and backend["separate_from_repo_root"] is True
    assert backend["files"] == len(STUB_FILES)


def test_a_connection_that_bypasses_the_fake_is_an_error_not_a_score(tmp_path):
    tree = make_stub_backend(tmp_path / "archive")
    bench = write_benchmark(tmp_path, _examples())
    report = runner.run_evaluation(config_for(tmp_path, bench, ["existing_law"], ["test"], backend_root=tree))
    socket_item = items_of(report, "existing_law")["cit-socket"]
    assert socket_item["status"] == "error" and socket_item["prediction"] is None
    assert "bypassed the fake law.go.kr transport" in socket_item["error"]
    assert socket_item["verdict"] == "not_scorable"
    gate = next(g for g in report["gates"]["existing_law"]["gates"] if g["id"] == "HG-9")
    assert gate["status"] == "fail"   # a harness gap fails the crash gate instead of passing as "unavailable"


def test_a_backend_root_without_a_backend_is_refused_before_anything_runs(tmp_path):
    empty = tmp_path / "empty"
    (empty / "backend").mkdir(parents=True)
    bench = write_benchmark(tmp_path, _examples())
    with pytest.raises(runner.RunnerError, match="has no backend/paradiso_backend.py"):
        runner.run_evaluation(config_for(tmp_path, bench, ["existing_law"], ["test"], backend_root=empty))
