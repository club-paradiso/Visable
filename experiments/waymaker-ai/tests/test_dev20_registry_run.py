"""DEV-20 through the 005-Q guarded pipeline with the real-world registry: the stored free-T4 run.

One free Colab T4 model load (commit e37299c) re-checked the 005-Q pass and ran DEV-20 once with
registry/real_world_registry.json. The files are stored unmodified and re-score byte for byte.
Development Candidate Diagnostic only; not Official Gold Accuracy.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import real_world_registry as rwr
import score_dev20_guarded as scorer

RUN = BOOT / "runs" / "dev20_registry"
RAW_SHA256 = {
    "generations.jsonl": "f5ed235e603ddf702d82061ae51cb0280fa1f6f5e33a6aa5902553e283d50230",
    "sessions.jsonl": "3908bc217709dbf246807439989e3f5dfcab8e176f0c452abcbe5a088334bdfe",
    "pipeline.jsonl": "cc06b8c05c24b8b56d721d7affe273b682a1b678ce904bfe9afefa80699c5e12",
    "dev20_guarded_results.json": "6758be3c72d6688a244867c073ad7d5a9b1ca21e2061373ef1d677626642a9c0",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pipeline():
    return {json.loads(l)["case_id"]: json.loads(l) for l in (RUN / "pipeline.jsonl").read_text().splitlines()}


@pytest.mark.parametrize("name", sorted(RAW_SHA256))
def test_files_are_the_unmodified_colab_outputs(name):
    assert sha(RUN / name) == RAW_SHA256[name]


def test_one_model_load_at_the_registry_commit_with_the_committed_registry():
    sessions = [json.loads(l) for l in (RUN / "sessions.jsonl").read_text().splitlines()]
    assert len(sessions) == 1 and sessions[0]["code"]["git_commit"] == "e37299c10bdbd6414d7dc4560b439e8e6bd57a98"
    assert sessions[0]["code"]["code_files_modified_from_commit"] is False
    assert sha(rwr.REGISTRY) == "86a90a31ba960dc7eb99809477c9606ec5c4743a4401053bcc50b53b5e3d97a3"
    assert {r["registry_status"] for r in pipeline().values()} == {"loaded"}


def test_the_scores_reproduce_byte_for_byte(tmp_path):
    shutil.copy(RUN / "pipeline.jsonl", tmp_path / "pipeline.jsonl")
    result = scorer.score(tmp_path)
    (tmp_path / "out.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    assert sha(tmp_path / "out.json") == RAW_SHA256["dev20_guarded_results.json"]


def test_eight_items_reached_the_model_and_every_guard_released():
    s = json.loads((RUN / "dev20_guarded_results.json").read_text())["summary"]
    assert (s["model_called"], s["withheld_before_model"], s["passed_all_dimensions"]) == (8, 12, 5)
    assert s["guard_decisions"] == {"release": 8} and s["passed_among_model_called"] == 3


def test_rejected_or_left_out_evidence_never_reached_the_model():
    registry = json.loads(rwr.REGISTRY.read_text())["records"]
    trusted = {e for e, r in registry.items() if r["verification"]["result"] == "verified"}
    for rec in pipeline().values():
        cited = set((rec["released"] or {}).get("citations") or [])
        assert cited <= trusted
        if rec["model_called"]:
            assert set(rec["admissible_ids"]) <= trusted


def test_the_report_groups_match_the_results():
    analysis = json.loads((RUN / "analysis_dev20_registry.json").read_text())
    cases = {c["case_id"]: c for c in json.loads((RUN / "dev20_guarded_results.json").read_text())["cases"]}
    g = analysis["groups"]
    assert all(cases[c]["passed"] and cases[c]["model_called"] for c in g["model_called_passed"])
    assert all(not cases[c]["model_called"] for c in g["withheld_evidence_rejected_contradicts_current_text"])
    assert all(cases[c]["expected_statuses"] == ["clarify"] for c in g["model_called_rubric_expects_clarify"])
