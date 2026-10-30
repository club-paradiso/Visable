"""Regressions anchored on the first real CUDA run of the repository runtime (Mission 005-C.2).

The record was produced on a free Colab T4 by commit 59858c5 and is stored
unmodified. These tests keep the validator, the evidence views and the metric
separation honest against real output, not only synthetic stand-ins. They do
not re-run the model and say nothing about legal accuracy.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from waymaker_ai import cuda_policy, foundation

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import split_cuda_record

RUN = BOOT / "runs" / "mission005c2-cuda"
RAW = RUN / "raw_record.json"
DIGEST = "d79ec336d4c7ae90bceed6cea9a90b42690896173de8e38eefe7a195edafdf99"
VIEWS = ("execution_manifest.json", "raw_inference.json", "gpu_performance.json",
         "checkpoint_provenance.json", "validation_summary.json")


@pytest.fixture
def record():
    return json.loads(RAW.read_text(encoding="utf-8"))


def test_raw_record_is_the_unmodified_colab_file():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == DIGEST
    note = json.loads((RUN / "transfer_note.json").read_text())
    assert note["sha256"] == DIGEST and {h["sha256"] for h in note["hash_chain"]} == {DIGEST}


def test_real_record_passes_the_validator(record):
    cuda_policy.validate_run_record(record)
    assert record["record_validation"]["passed"] is True
    assert record["execution_status"] == "completed" and record["reproduction_pins_matched"] is True


def test_real_record_matches_the_pinned_model_code_and_hardware(record):
    policy = cuda_policy.configuration()
    assert record["model"]["checkpoint"] == "google/gemma-4-E4B-it"
    assert record["model"]["revision"] == policy["model"]["revision"]
    assert record["provenance"]["artifact_integrity"]["model.safetensors"]["digest"] == \
        policy["model"]["artifacts"]["model.safetensors"]["digest"]
    notebook = json.loads((BOOT / "notebooks" / "artemis_gemma4_e4b_cuda_colab.ipynb").read_text())
    assert record["code"]["git_commit"] == notebook["metadata"]["waymaker_artemis"]["code_commit"]
    assert record["code"]["code_files_modified_from_commit"] is False
    assert record["environment"]["cuda_device"] == "Tesla T4"
    assert record["environment"]["version_drift"] == []


def test_real_gemma4_module_names_satisfy_the_42_layer_nf4_check(record):
    quantization = record["load"]["quantization"]
    assert quantization["quantized_decoder_layers"] == quantization["expected_decoder_layers"] == 42
    assert quantization["linear4bit_modules"] > 0 and quantization["parameter_devices"] == ["cuda:0"]


def test_three_cases_completed_with_grounded_statuses(record):
    cases = {c["case_id"]: c for c in record["cases"]}
    assert set(cases) == {"no_evidence", "synthetic_citation", "synthetic_conflict"}
    assert cases["no_evidence"]["response"] == {"status": "insufficient_evidence", "answer": "", "citations": []}
    assert cases["synthetic_citation"]["response"]["citations"] == ["SYN-1"]
    assert cases["synthetic_conflict"]["response"]["status"] == "conflict"
    assert cases["synthetic_conflict"]["response"]["citations"] == ["SYN-1", "SYN-2"]
    assert all(c["finish_reason"] == "eos" and c["generated_token_count"] > 0 for c in cases.values())


@pytest.mark.parametrize("mutate", [
    lambda r: r["load"]["quantization"].update(quantized_decoder_layers=41),
    lambda r: r["provenance"]["artifact_integrity"]["model.safetensors"].update(digest="0" * 64),
    lambda r: r["model"].update(checkpoint="google/gemma-4-E2B-it"),
    lambda r: r["cases"][1].update(raw_output=r["cases"][1]["raw_output"].replace("SYN-1", "SYN-9")),
    lambda r: r.update(official_gold_accuracy=1.0),
])
def test_tampering_with_the_real_record_is_rejected(record, mutate):
    forged = copy.deepcopy(record)
    mutate(forged)
    with pytest.raises(ValueError):
        cuda_policy.validate_run_record(forged)


def test_evidence_views_trace_back_to_the_raw_record(record):
    for name in VIEWS:
        view = json.loads((RUN / name).read_text(encoding="utf-8"))
        assert view["source_record_sha256"] == DIGEST, name
    summary = json.loads((RUN / "validation_summary.json").read_text())
    assert summary["record_validation_recomputed"] == {"passed": True, "error": None}
    assert summary["official_gold_accuracy"] is None and summary["independent_legal_review"] == "not_verified"


def test_split_script_reproduces_the_committed_views(tmp_path):
    split_cuda_record.main([str(RAW), "--out-dir", str(tmp_path / "views")])
    for name in VIEWS:
        assert (tmp_path / "views" / name).read_text() == (RUN / name).read_text(), name


def test_real_cuda_metadata_never_pools_with_mlx(record):
    cuda_meta = {"adapter_type": "cuda_transformers", "inference_kind": "real_inference",
                 "runtime": record["runtime"], "profile": "gemma4_e4b",
                 "model_name": record["model"]["checkpoint"], "model_revision": record["model"]["revision"],
                 "quantization": record["model"]["quantization"],
                 "quantization_verified": record["load"]["quantization"]["passed"],
                 "cuda_device": record["environment"]["cuda_device"],
                 "checkpoint_metadata_verified": record["provenance"]["checkpoint_metadata_verified"],
                 "checkpoint_integrity_verified": record["provenance"]["checkpoint_integrity_verified"],
                 "weight_integrity": record["provenance"]["weight_integrity"],
                 "weights_sha256": record["provenance"]["artifact_integrity"]["model.safetensors"]["digest"]}
    selected = foundation.profile("gemma4_e4b")
    mlx_meta = {"inference_kind": "real_inference", "runtime": "mlx_vlm", "profile": "gemma4_e4b",
                "model_name": selected["inference_checkpoint"], "model_revision": selected["inference_revision"],
                "checkpoint_metadata_verified": True, "checkpoint_integrity_verified": True,
                "weight_integrity": "sha256_verified"}
    assert foundation.metric_group(cuda_meta) != foundation.metric_group(mlx_meta)
