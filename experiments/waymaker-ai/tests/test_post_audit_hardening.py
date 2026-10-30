"""Reproductions for PR #726's independent post-recovery audit.

All model responses and checkpoints here are synthetic; no inference is run.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from artemis_bootstrap import evaluation_isolation, independent_benchmark_intake as intake
from waymaker_ai import foundation

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_runner as runner
import gemma4_runtime as runtime
import smoke_grader


def poisoned_item():
    return {"id": "SYN-HARDENING", "question": "A fictional question", "expected": {"private_answer": "SECRET_ANSWER"},
            "evidence": [{"id": "SYN-E1", "title": "A citation title", "text": "Legitimate evidence text",
                          "review_note": "SECRET_ANSWER", "rubric": {"answer": "SECRET_ANSWER"},
                          "source": {"document_id": "DOC-1", "provision": "section 1", "effective_date": "2026-10-30",
                                     "source_url": "https://example.invalid/document", "page": 7,
                                     "review_note": {"answer_key": "SECRET_ANSWER"},
                                     "unapproved_field": "SECRET_ANSWER", "approval_state": "approved",
                                     "reviewed_by": "SECRET_ANSWER"}}]}


def test_runtime_prompt_drops_nested_review_and_preserves_citations():
    item = poisoned_item()
    original = copy.deepcopy(item)
    messages = runtime.build_messages(item)
    assert "SECRET_ANSWER" not in json.dumps(messages)
    evidence = json.loads(messages[1]["content"])["evidence"][0]
    assert evidence["text"] == "Legitimate evidence text"
    assert evidence["title"] == "A citation title"
    for key in ("document_id", "provision", "effective_date", "source_url", "page"):
        assert evidence["source"][key] == item["evidence"][0]["source"][key]
    assert "approval_state" not in evidence["source"]
    assert item == original


def test_nested_values_in_allowed_metadata_are_never_serialized():
    item = poisoned_item()
    item["evidence"][0]["source"]["document_id"] = {"review_note": "SECRET_ANSWER"}
    assert "SECRET_ANSWER" not in json.dumps(runtime.build_messages(item))


def test_smoke_prompt_rejects_metadata_objects_disguised_as_text():
    item = poisoned_item()
    item["evidence"][0]["title"] = {"review_note": "SECRET_ANSWER"}
    with pytest.raises(ValueError, match="title"):
        smoke_grader.build_messages(item)


def test_runner_to_worker_boundary_is_blind(tmp_path, monkeypatch):
    item = poisoned_item()
    benchmark = tmp_path / "benchmark.json"
    benchmark.write_text(json.dumps({"items": [item]}))
    adapter = runner.LocalModelAdapter(max_tokens=32)
    monkeypatch.setattr(adapter, "check_availability", lambda: (True, None))
    monkeypatch.setattr(adapter, "get_metadata", lambda: runner.MockModelAdapter().get_metadata())
    monkeypatch.setattr(adapter, "_find_snapshot_path", lambda: tmp_path)
    monkeypatch.setattr(runner.ArtemisEvaluationRunner, "_get_system_info", lambda self: {"fixture": True})
    monkeypatch.setattr(runner.ArtemisEvaluationRunner, "_get_git_commit", lambda self: "synthetic")
    sent = []
    def invoke(command, **kwargs):
        request = json.loads(kwargs["input"])
        sent.append(request)
        assert "SECRET_ANSWER" not in kwargs["input"]
        assert request["item"]["evidence"][0]["source"]["document_id"] == "DOC-1"
        assert "SECRET_ANSWER" not in json.dumps(runtime.build_messages(request["item"]))
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "execution_status": "completed", "response": {"status": "insufficient_evidence", "answer": "", "citations": []}}))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    result = runner.ArtemisEvaluationRunner(adapter, benchmark_path=benchmark,
        mode=runner.EvaluationMode.CANDIDATE_EVAL, out_dir=tmp_path / "run").run()
    assert len(sent) == 1
    assert result.execution_status == runner.ExecutionStatus.COMPLETED
    assert result.suite_summary.official_gold_pass_rate is None
    manifest = json.loads((tmp_path / "run" / "run_manifest.json").read_text())
    assert manifest["file_digests"]["inference_input_code"] == hashlib.sha256(
        (BOOT.parent / "waymaker_ai" / "inference_input.py").read_bytes()).hexdigest()


def test_frozen_hashes_and_role_strings_do_not_certify_isolation():
    manifest = intake.BlindBenchmarkPartitionManager.create_frozen_manifest("SYNTHETIC", [])
    assert manifest["isolation_status"] == evaluation_isolation.get_environment_isolation_audit()["isolation_status"]
    assert manifest["clean_room_verified"] is False
    assert manifest["isolation_protocol"] == "blind_projection_only"
    assert manifest["isolation_evidence"] == []
    assert manifest["required_verification_evidence"]
    assert manifest["isolation_transitions"]
    assert manifest["author_attestations_authenticated"] is False


@pytest.mark.parametrize("corpus,question,answer", [([], "question words", "answer words"),
    (["!", " "], "question words", "answer words"), (["reference words"], "!?", " "),
    (["reference words"], "", "answer words"), (["reference words"], None, "answer words")])
def test_unanalysable_contamination_is_unknown(corpus, question, answer):
    risk, score, description = intake.ContaminationAuditor(corpus).check_item_contamination(question, answer)
    assert risk.value == "unknown"
    assert score is None
    assert description


def test_contamination_report_binds_corpus_scope_and_limits():
    auditor = intake.ContaminationAuditor(["reference question words"], corpus_id="synthetic-corpus-v1")
    report = auditor.check_item_report("novel question", "novel answer")
    assert report["corpus_id"] == "synthetic-corpus-v1"
    assert len(report["corpus_sha256"]) == 64
    assert report["reference_documents_analyzed"] == 1
    assert report["scope"] == "question_and_answer_key_against_supplied_corpus"
    assert report["limitations"]
    assert report["independence_verified"] is False


def checkpoint_fixture(tmp_path):
    selected = copy.deepcopy(foundation.profile())
    snapshot = tmp_path / selected["inference_revision"]
    snapshot.mkdir()
    files = {"config.json": json.dumps({"model_type": "gemma4", "architectures": selected["architectures"],
             "text_config": selected["text_config"], "quantization": selected["quantization"]}),
             "processor_config.json": '{"processor_class":"Gemma4Processor"}',
             "tokenizer_config.json": "{}", "chat_template.jinja": "template", "README.md": "synthetic",
             "tokenizer.json": '{"tokens":"synthetic"}',
             "model.safetensors.index.json": '{"weight_map":{"tensor":"model.safetensors"}}',
             "model.safetensors": "synthetic-not-model-weights"}
    for name, text in files.items():
        (snapshot / name).write_text(text)
    selected["metadata_sha256"] = {name: hashlib.sha256((snapshot / name).read_bytes()).hexdigest()
                                   for name in selected["metadata_sha256"]}
    selected["artifact_integrity"] = {"reference_source": "synthetic-test-fixture", "files": {
        name: {"algorithm": "sha256", "digest": hashlib.sha256((snapshot / name).read_bytes()).hexdigest(),
               "size_bytes": (snapshot / name).stat().st_size}
        for name in ("tokenizer.json", "model.safetensors.index.json", "model.safetensors")}}
    return snapshot, selected


@pytest.mark.parametrize("name", ["tokenizer.json", "model.safetensors.index.json", "model.safetensors"])
def test_same_length_corrupt_checkpoint_artifact_is_rejected(tmp_path, name):
    snapshot, selected = checkpoint_fixture(tmp_path)
    foundation.validate_snapshot(snapshot, selected)
    path = snapshot / name
    original = path.read_bytes()
    # Valid JSON for tokenizer/index, same length for every corruption.
    path.write_bytes(original.replace(b"synthetic", b"corrupted", 1) if b"synthetic" in original
                     else original.replace(b"tensor", b"broken", 1))
    assert path.stat().st_size == len(original)
    with pytest.raises(ValueError, match="integrity|digest|mismatch"):
        foundation.validate_snapshot(snapshot, selected)


def test_full_integrity_requires_trusted_references(tmp_path):
    snapshot, selected = checkpoint_fixture(tmp_path)
    verified = foundation.validate_snapshot(snapshot, selected)
    assert verified["checkpoint_integrity_verified"] is True
    assert verified["weight_integrity"] == "sha256_verified"
    selected.pop("artifact_integrity")
    with pytest.raises(ValueError, match="integrity|reference"):
        foundation.validate_snapshot(snapshot, selected)


def test_metadata_only_record_is_not_verified_real_inference():
    selected = foundation.profile()
    metadata = {"inference_kind": "real_inference", "profile": "gemma4_e4b", "runtime": "mlx_vlm",
                "model_name": selected["inference_checkpoint"], "model_revision": selected["inference_revision"],
                "checkpoint_metadata_verified": True, "weight_integrity": "presence_and_size_only"}
    with pytest.raises(ValueError, match="provenance"):
        foundation.metric_group(metadata)


def test_unreferenced_shard_is_rejected_even_with_valid_index_hash(tmp_path):
    snapshot, selected = checkpoint_fixture(tmp_path)
    index = snapshot / "model.safetensors.index.json"
    index.write_text('{"weight_map":{"tensor":"extra.safetensors"}}')
    (snapshot / "extra.safetensors").write_bytes(b"synthetic")
    selected["artifact_integrity"]["files"][index.name].update(
        digest=hashlib.sha256(index.read_bytes()).hexdigest(), size_bytes=index.stat().st_size)
    with pytest.raises(ValueError, match="shards"):
        foundation.validate_snapshot(snapshot, selected)


def test_git_blob_identity_uses_object_header(tmp_path):
    path = tmp_path / "index.json"
    path.write_bytes(b'{"synthetic":true}')
    reference = {"algorithm": "git_blob_sha1", "size_bytes": path.stat().st_size,
                 "digest": hashlib.sha1(b"blob " + str(path.stat().st_size).encode() + b"\0" + path.read_bytes()).hexdigest()}
    assert foundation.verify_artifact(path, reference)["digest"] == reference["digest"]
    reference["digest"] = hashlib.sha1(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="digest"):
        foundation.verify_artifact(path, reference)


def test_artifact_hashing_reads_bounded_chunks(tmp_path, monkeypatch):
    import io
    payload = b"synthetic" * 300000
    path = tmp_path / "weights"
    path.write_bytes(payload)
    reference = {"algorithm": "sha256", "digest": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
    class BoundedRead(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024
            return super().read(size)
    monkeypatch.setattr(Path, "open", lambda self, mode: BoundedRead(payload))
    assert foundation.verify_artifact(path, reference)["digest"] == reference["digest"]


def test_research_judge_cannot_bypass_model_preflight(monkeypatch):
    import flip_judge
    monkeypatch.setattr(runner.LocalModelAdapter, "check_availability", lambda self: (False, "synthetic blocker"))
    with pytest.raises(RuntimeError, match="not_executed.*synthetic blocker"):
        flip_judge.load_e4b()


def test_judge_cache_keeps_new_runtime_separate_from_historical_results(tmp_path):
    import flip_judge
    path = tmp_path / "cache.jsonl"
    prompt = "synthetic prompt"
    path.write_text(json.dumps({"key": hashlib.sha256(prompt.encode()).hexdigest(), "verdict": "same"}) + "\n")
    def generate(_):
        return '{"verdict":"opposite"}'
    generate.model_metadata = {"profile": "gemma4_e4b", "runtime": "synthetic-test-runtime"}
    assert flip_judge.Cache(path).get(prompt, generate) == "opposite"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert records[0]["verdict"] == "same"
    assert records[1]["model_metadata"] == generate.model_metadata
