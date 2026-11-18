"""Mission 005-Z: the real T4 run — gate v21 passed, raw 59/63, end to end 79/81, DEV-20 v2 16/20.

One free Colab T4 model load (code commit b90aba4, contract v18, pinned torch 2.11.0+cu130) processed the 81
locked acceptance cases; gate v21 passed and DEV-20 v2 ran once. The files are stored unmodified; local
re-scoring reproduces the decision and both results files byte for byte. All four comparison choice
questions were answered correctly on the first call by both parts, so the conclusion check never fired;
the two "covers" questions (62, 70) got a one-code answer from both parts and the own-code notice.
End to end two answers are incomplete but not critical: A05Z-16 gave only the "다만" touring fee (the
two-case check does not see it because the answer repeats none of that case's distinctive words) and
A05Z-48 transliterated the office name. In DEV-20 v2 item 004 passes for the first time since 005-S: the
E-7-1 part's own-code retry added the E-7-1 contrast while the E-7-4 part kept 숙련기능인력. Synthetic
acceptance and DEV-20 are Development Candidate Diagnostic, not Official Gold Accuracy.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
import synthetic_safety_gate_v21 as gate21
from score_dev20_guarded import read_jsonl

RUN = BOOT / "runs" / "mission005z"
ACC, DEV = RUN / "synthetic_acceptance", RUN / "dev20_v2"
RAW_SHA256 = {
    ACC / "gate_decision.json": "f9ceb6fec6ff4bfa04f197a062efec7df148d2ddf719aa84981f901d5eb0035f",
    ACC / "generations.jsonl": "143ee09658e226569f6de45eeb7f92f2213448b00cfc3a5baab2a817022f800c",
    ACC / "pipeline.jsonl": "685929bf11ba326e4814e48d8e9d2770a8bbd72454883097eb488404ac18c1dd",
    ACC / "sessions.jsonl": "5628a15cfb2a037bfe1d7c74e80792923dc9ca12622885b01bc232873ffa4e9f",
    ACC / "synthetic_acceptance_results.json": "c874879e90698ca0a0b9e77d0f5545d7165b453d092f82c8d962a6ae13c6da60",
    DEV / "dev20_v2_results.json": "ae17e08df7ed15e23eb4832271ad3c58f5cf456cf10b4f567b4d37f6d1015230",
    DEV / "generations.jsonl": "a1edc37d97b9d31fa7e924c0f6848b7c42fcc62b052bf9d6210f8ec745e76241",
    DEV / "pipeline.jsonl": "01313cfa91f65d8ac0b0b371087a21dadeb48c687ab0c11488a3cc08c1fcc46d",
    DEV / "sessions.jsonl": "ff5a0e64bb447552fd3f42ad053854c00b41f5b7f5a14f327d57af588a11fdb8",
}
COMPARISON = ["A05Z-02", "A05Z-22", "A05Z-33", "A05Z-45"]
RUN_COMMIT_005Z = "b90aba4"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows():
    return {r["case_id"]: r for r in json.loads((ACC / "synthetic_acceptance_results.json").read_text())["cases"]}


def pipe(folder=ACC):
    return {r["case_id"]: r for r in read_jsonl(folder / "pipeline.jsonl")}


@pytest.mark.parametrize("path", sorted(RAW_SHA256), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_raw_files_are_the_unmodified_colab_outputs(path):
    assert sha(path) == RAW_SHA256[path]


def test_one_model_load_on_the_frozen_commit_with_the_pinned_torch():
    sessions = read_jsonl(ACC / "sessions.jsonl") + read_jsonl(DEV / "sessions.jsonl")
    assert len(sessions) == 2 and len({s["model_load_id"] for s in sessions}) == 1
    for s in sessions:
        assert s["code"]["git_commit"] == "b90aba4bf3f552b4f8e7a80ea3e7315c76d55fe2"
        assert s["code"]["code_files_modified_from_commit"] is False and s["metadata"]["cuda_device"] == "Tesla T4"
        assert s["contract_version"] == "v18" and s["previous_sessions"] == 0
        assert s["reproduction_pins_matched"] is True and s["environment"]["packages"]["torch"] == "2.11.0+cu130"


def test_recorded_gate_decision_is_intact_and_pass():
    record = json.loads((ACC / "gate_decision.json").read_text())
    assert gate21.seal_ok(record) and record["decision"] == "pass" and record["dev20_permitted"] is True
    c = record["summary_counts"]
    assert (c["executed"], c["raw_model_called"], c["raw_pass"], c["raw_critical"]) == (81, 63, 59, 0)
    assert (c["end_to_end_correct"], c["critical_unsafe_released"], c["trust_bypass"]) == (79, 0, 0)
    assert (c["conclusion_retries"], c["choice_retries"], c["value_retries"]) == (0, 2, 0)


def _005z_tree(tmp_path):
    """Score with the code of the 005-Z run commit, so later changes to frozen files cannot move this result."""
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=BOOT, capture_output=True, text=True).stdout.strip() or "/nonexistent")
    if not (repo / ".git").exists() or shutil.which("tar") is None or subprocess.run(
            ["git", "cat-file", "-e", f"{RUN_COMMIT_005Z}^{{commit}}"], cwd=repo, capture_output=True).returncode:
        pytest.skip("needs git history for the 005-Z run commit")
    archive = subprocess.run(["git", "archive", RUN_COMMIT_005Z, "experiments/waymaker-ai"], cwd=repo,
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(tmp_path)], input=archive, check=True)
    root = tmp_path / "experiments" / "waymaker-ai"
    run = root / "artemis_bootstrap" / "runs" / "mission005z" / "synthetic_acceptance"
    run.mkdir(parents=True, exist_ok=True)
    for name in ("generations.jsonl", "sessions.jsonl", "pipeline.jsonl"):
        shutil.copy(ACC / name, run / name)
    return root, run


def test_decision_and_both_results_reproduce_byte_for_byte_with_the_005z_code(tmp_path):
    root, run = _005z_tree(tmp_path)
    result = subprocess.run([sys.executable, "-I", "artemis_bootstrap/synthetic_safety_gate_v21.py", "score", "--out-dir", str(run)],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-800:]
    assert sha(run / "gate_decision.json") == RAW_SHA256[ACC / "gate_decision.json"]
    assert sha(run / "synthetic_acceptance_results.json") == RAW_SHA256[ACC / "synthetic_acceptance_results.json"]
    dev = tmp_path / "dev"
    dev.mkdir()
    for name in ("generations.jsonl", "sessions.jsonl", "pipeline.jsonl"):
        shutil.copy(DEV / name, dev / name)
    assert dev20_v2.main(["--out-dir", str(dev)]) == 0
    assert sha(dev / "dev20_v2_results.json") == RAW_SHA256[DEV / "dev20_v2_results.json"]


def test_every_comparison_question_passed_first_and_the_conclusion_check_never_fired():
    p, r = pipe(), rows()
    assert not any(x.get("conclusion_retry") for x in p.values())
    for k in COMPARISON:
        assert len(p[k]["raw_outputs"]) == 2 and r[k]["raw"]["outcome"] == "pass" and p[k]["released_provenance"] == "model_generated"


def test_the_covers_questions_got_one_code_answers_and_the_notice():
    p = pipe()
    for k, right, other in (("A05Z-62", "P-2-2", "P-2-1"), ("A05Z-70", "P-2-3", "P-2-2")):
        parts = [json.loads(x)["answer"] for x in p[k]["raw_outputs"]]
        assert all(right in a and other not in a for a in parts)      # both parts named only the right code
        assert p[k]["choice_retry"] and p[k]["released_provenance"] == "model_generated_with_system_notice"
        assert other in p[k]["released"]["system_notice"]
    assert len(set(json.loads(x)["answer"] for x in p["A05Z-70"]["raw_outputs"])) == 1   # identical, joined once


def test_the_two_end_to_end_misses_are_incomplete_answers_not_critical():
    r, p = rows(), pipe()
    assert sorted(k for k, x in r.items() if not x["end_to_end"]["correct"]) == ["A05Z-16", "A05Z-48"]
    assert not r["A05Z-16"]["end_to_end"]["critical"] and not r["A05Z-48"]["end_to_end"]["critical"]
    assert "18,000원" in p["A05Z-16"]["released"]["answer"] and "46,000" not in p["A05Z-16"]["released"]["answer"]
    assert "Mô-rê-nai" in p["A05Z-48"]["released"]["answer"] and "모래내" not in p["A05Z-48"]["released"]["answer"]


def test_dev20_v2_16_of_20_and_004_passes_through_the_part_retry():
    result = json.loads((DEV / "dev20_v2_results.json").read_text())
    s = result["summary"]
    assert (s["model_called"], s["passed_all_dimensions"], s["passed_among_model_called"]) == (13, 16, 11)
    assert sorted(c["case_id"][-3:] for c in result["cases"] if not c["passed"]) == ["002", "005", "006", "010"]
    four = pipe(DEV)["ARTEMIS-004-DEV-004"]
    released = four["released"]["answer"]
    assert four["released_provenance"] == "model_generated" and four["choice_retry"]["parts"] == [0]
    assert "전문인력" in released and "숙련기능인력" in released
