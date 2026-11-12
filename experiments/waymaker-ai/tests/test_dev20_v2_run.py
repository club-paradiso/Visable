"""DEV-20 v2 through the 005-Q guarded pipeline with the v2 registry: the stored free-T4 run.

One free Colab T4 model load (commit 5f25f18) re-checked the 005-Q pass and ran DEV-20 v2 once.
The files are stored unmodified and re-score byte for byte. Development Candidate Diagnostic only;
not Official Gold Accuracy.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
from score_dev20_guarded import read_jsonl

RUN = BOOT / "runs" / "dev20_v2"
RAW_SHA256 = {
    "generations.jsonl": "274dadcc42f07e1728af35062cb94f7f240748539d8909c59e5dd462d6c070e1",
    "sessions.jsonl": "79443c9ced959276989f8f62fe552b0ef023553269141e290b597f24b550d302",
    "pipeline.jsonl": "8deb3ba31ff4da0d3c0b8cd86094b126423d665e4f3ae2822fab92507634f3c4",
    "dev20_v2_results.json": "abe8ef4b4d3b8c4eb7fe610424b96c4f19d462888f35d1685a30be87cb3513e2",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_stored_files_are_the_colab_outputs():
    assert {name: sha(RUN / name) for name in RAW_SHA256} == RAW_SHA256


def test_one_session_on_the_pinned_commit_and_the_v2_split():
    sessions = read_jsonl(RUN / "sessions.jsonl")
    assert len(sessions) == 1
    assert sessions[0]["code"]["git_commit"] == "5f25f18c31e62f44c027138bd2870628772ea215"
    assert sessions[0]["code"]["code_files_modified_from_commit"] is False
    assert sessions[0]["benchmark_sha256"] == dev20_v2.load_items()[1]


def test_rescoring_reproduces_the_stored_results_byte_for_byte(tmp_path):
    for name in ("generations.jsonl", "sessions.jsonl", "pipeline.jsonl"):
        shutil.copy(RUN / name, tmp_path / name)
    assert dev20_v2.main(["--out-dir", str(tmp_path)]) == 0
    assert (tmp_path / "dev20_v2_results.json").read_bytes() == (RUN / "dev20_v2_results.json").read_bytes()


def test_summary_and_per_item_outcomes():
    result = json.loads((RUN / "dev20_v2_results.json").read_text(encoding="utf-8"))
    summary = result["summary"]
    assert (summary["model_called"], summary["withheld_before_model"]) == (13, 7)
    assert (summary["passed_all_dimensions"], summary["passed_among_model_called"]) == (14, 9)
    failed = sorted(c["case_id"][-3:] for c in result["cases"] if not c["passed"])
    assert failed == ["002", "003", "005", "010", "011", "020"]


def test_no_unsafe_release_and_no_rejected_evidence_cited():
    records = read_jsonl(RUN / "pipeline.jsonl")
    called = [r for r in records if r["model_called"]]
    assert all(r["guard"]["decision"] == "release" for r in called)
    for r in records:
        admissible = {d["evidence_id"] for d in r.get("trust_decisions") or [] if d["decision"] == "admissible"}
        assert set(r["released"].get("citations") or []) <= admissible
    result = json.loads((RUN / "dev20_v2_results.json").read_text(encoding="utf-8"))
    unsafe = ("forbidden_claim", "polarity", "subject_binding", "invented_amount", "unwarranted_answer")
    assert not [f for c in result["cases"] for f in c["failures"] if any(u in f for u in unsafe)]
