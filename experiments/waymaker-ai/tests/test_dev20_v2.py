"""DEV-20 v2: the 2026-11-03 rubric decisions applied to a new file, with v1 and its registry unchanged.

The decisions are Claude's under the owner's delegation, by the rule in the review file's decision_meta.
Development Candidate Diagnostic only; not Official Gold Accuracy and not legal review.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_eval
import build_dev20_v2 as v2
import dev20_v2
import real_world_registry as rwr
import run_dev20_cuda
from score_dev20_guarded import read_jsonl, released_response

REVIEW = json.loads(v2.REVIEW.read_text(encoding="utf-8"))
V1 = json.loads(v2.DEV20_V1.read_text(encoding="utf-8"))
V2 = json.loads(v2.DEV20_V2.read_text(encoding="utf-8"))
ITEMS = {i["id"]: i for i in V2["items"]}
OPTIONS = {i["id"]: i["decision"]["option"] for i in REVIEW["items"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_v2_rebuilds_byte_for_byte_and_the_manifest_pins_all_three_files():
    assert v2.dump(v2.build(V1, REVIEW)) == v2.DEV20_V2.read_bytes()
    manifest = json.loads(v2.V2_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["dev20_v1_sha256"] == sha(v2.DEV20_V1)
    assert manifest["dev20_v2_sha256"] == sha(v2.DEV20_V2)
    assert manifest["rubric_review_sha256"] == sha(v2.REVIEW)
    assert manifest["options"] == OPTIONS


def test_v1_stays_the_isolation_manifest_split():
    iso = json.loads(run_dev20_cuda.ISOLATION_MANIFEST.read_text(encoding="utf-8"))
    assert sha(v2.DEV20_V1) == iso["partitions"]["dev_sha256"]
    items, digest = run_dev20_cuda.load_dev_items()
    assert digest == iso["partitions"]["dev_sha256"] and len(items) == 20
    with pytest.raises(ValueError, match="manifest-recorded"):
        run_dev20_cuda.load_dev_items(v2.DEV20_V2)


def test_loader_reads_v2_only_with_its_own_digest(tmp_path):
    items, digest = dev20_v2.load_items()
    assert digest == sha(v2.DEV20_V2) and [i["id"] for i in items] == [i["id"] for i in V1["items"]]
    tampered = tmp_path / "v2.json"
    tampered.write_bytes(v2.DEV20_V2.read_bytes().replace("원칙적으로 제한".encode(), "원칙적으로 허용".encode(), 1))
    with pytest.raises(ValueError, match="manifest-recorded"):
        dev20_v2.load_items(tampered)


def test_every_review_item_is_decided_with_the_stated_rule():
    assert REVIEW["status"] == "decided" and "not independent legal review" in REVIEW["decision_meta"]["rule"]
    assert OPTIONS == {
        **{f"ARTEMIS-004-DEV-{n}": "update" for n in ("001", "005", "011", "017", "020")},
        **{f"ARTEMIS-004-DEV-{n}": "withhold_correct" for n in ("007", "009", "019")},
        **{f"ARTEMIS-004-DEV-{n}": "accept_conditional" for n in ("015", "016")},
        **{f"ARTEMIS-004-DEV-{n}": "loosen" for n in ("003", "004", "006")},
    }
    for item in REVIEW["items"]:
        assert item["decision"]["note"] and item["decision"]["decided_at"]


def test_v2_is_a_valid_dataset_with_fresh_hashes():
    report = artemis_eval.validate_dataset(v2.DEV20_V2)
    assert report.valid and report.errors == 0
    for item in V2["items"]:
        for ev in item["evidence"]:
            assert ev["source"]["content_sha256"] == hashlib.sha256(ev["text"].encode("utf-8")).hexdigest()


def test_updated_items_carry_the_checked_text_and_drop_the_contradicted_rubric():
    one = ITEMS["ARTEMIS-004-DEV-001"]
    assert [e["id"] for e in one["evidence"]] == ["EV-DEV-001-A2"]
    assert "원칙적으로 제한" in one["evidence"][0]["text"] and "재외공관" not in one["evidence"][0]["text"]
    assert one["expected"]["source_fidelity"]["forbidden_subject_bindings"] == []
    assert "3만 5천원" in ITEMS["ARTEMIS-004-DEV-005"]["evidence"][0]["text"]
    assert "15 days" in ITEMS["ARTEMIS-004-DEV-011"]["evidence"][0]["text"]
    assert ITEMS["ARTEMIS-004-DEV-017"]["expected"]["source_fidelity"]["required_facts"] == ["2년", "3년", "6년"]
    twenty = ITEMS["ARTEMIS-004-DEV-020"]
    assert twenty["expected"]["citation_accuracy"] == {"must_cite": ["EV-DEV-020-OFFICIAL-A2"],
                                                        "must_not_cite": ["EV-DEV-020-CHAT"], "allow_unlisted_citations": False}
    assert "30,000원" in twenty["expected"]["source_fidelity"]["forbidden_claims"]


def test_withhold_correct_items_expect_withholding():
    for n in ("007", "009", "019"):
        exp = ITEMS[f"ARTEMIS-004-DEV-{n}"]["expected"]
        assert exp["allowed_statuses"] == ["insufficient_evidence"]
        assert exp["abstention_appropriateness"]["should_withhold"] is True
        assert exp["citation_accuracy"]["must_cite"] == []


def test_unreviewed_items_are_identical_to_v1():
    v1 = {i["id"]: i for i in V1["items"]}
    for item_id in set(v1) - set(OPTIONS):
        assert ITEMS[item_id] == v1[item_id]


def test_a_v2_rubric_that_lists_clarify_accepts_a_clarification_and_an_answer():
    item = ITEMS["ARTEMIS-004-DEV-015"]
    assert item["expected"]["procedural_integrity"]["must_clarify"] is False
    asked = dev20_v2.score_response(item, {"status": "clarify", "answer": "어떤 체류자격인가요?",
                                           "citations": ["EV-DEV-015-A"]})
    assert not [f for f in asked.all_failures if "clarif" in f]
    answered = dev20_v2.score_response(item, {"status": "answered", "citations": ["EV-DEV-015-A"],
                                              "answer": "체류자격에 따라 제출서류가 달라집니다."})
    assert not [f for f in answered.all_failures if "clarif" in f or "status" in f]
    assert item["expected"]["procedural_integrity"]["must_clarify"] is False  # the item is not modified
    direct = ITEMS["ARTEMIS-004-DEV-002"]  # clarify is not allowed there: still wrong
    scored = dev20_v2.score_response(direct, {"status": "clarify", "answer": "?", "citations": []})
    assert "[procedural_integrity] unnecessary_clarification:expected_direct_action" in scored.all_failures


def test_v2_registry_rebuilds_and_v1_registry_is_unchanged():
    decisions = json.loads((BOOT / "registry" / "dev20_v2_decisions.json").read_text(encoding="utf-8"))
    built = rwr.build_registry(decisions, v2.DEV20_V2, rwr.PROPOSALS_V2)
    stored = json.loads((BOOT / "registry" / "real_world_registry_v2.json").read_text(encoding="utf-8"))
    assert built == stored
    v1_decisions = json.loads((BOOT / "registry" / "dev20_decisions.json").read_text(encoding="utf-8"))
    assert rwr.build_registry(v1_decisions) == json.loads(rwr.REGISTRY.read_text(encoding="utf-8"))
    new = {"EV-DEV-001-A2", "EV-DEV-005-A2", "EV-DEV-011-A2", "EV-DEV-017-A2", "EV-DEV-020-OFFICIAL-A2"}
    assert {k for k, v in decisions.items() if k != "_meta" and v["decision"] == "approve"} >= new
    assert all(decisions[k] == v1_decisions[k] for k in decisions if k not in new and k != "_meta")


def test_v2_admission_reaches_the_model_for_the_rewritten_evidence():
    records = json.loads((BOOT / "registry" / "real_world_registry_v2.json").read_text(encoding="utf-8"))["records"]
    preview = rwr.admission_preview(V2["items"], records)
    proceed = sorted(k[-3:] for k, v in preview.items() if v["outcome"] == "proceed")
    assert proceed == ["001", "003", "004", "005", "006", "008", "011", "012", "015", "016", "017", "018", "020"]


def test_stored_answers_of_unchanged_items_rescore_under_v2():
    """Diagnostic: the 2026-11-03 released responses, for items whose evidence v2 did not change."""
    records = {r["case_id"]: r for r in read_jsonl(BOOT / "runs" / "dev20_registry" / "pipeline.jsonl")}
    rewritten = {f"ARTEMIS-004-DEV-{n}" for n in ("001", "005", "011", "017", "020")}
    passed = {i: dev20_v2.score_response(ITEMS[i], released_response(records[i])).overall_passed
              for i in ITEMS if i not in rewritten}
    assert sorted(k[-3:] for k, ok in passed.items() if not ok) == ["002", "003", "010"]
