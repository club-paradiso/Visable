"""Mission 005-E response contract v2: versioning, parser rules, runtime parity, synthetic spec.

Structural checks only. Whether a 'partial' answer names its uncovered part, or a
'clarify' answer asks the right question, is a meaning judgement and is not
claimed here.
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from waymaker_ai import response_contract as rc
from waymaker_ai.inference_input import project_evidence

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import gemma4_runtime
import run_dev20_cuda as harness
import score_dev20

V1_PROMPT_SHA256 = "41037931d0036099b1617d88d2f6c71c440e85079e7cabf000c89e9acd84c364"  # pinned: every pre-005-E record was produced with this prompt


def test_v1_prompt_is_unchanged_so_old_records_still_rederive():
    gens = score_dev20.read_jsonl(BOOT / "runs" / "mission005d-dev20" / "generations.jsonl")
    items = {i["id"]: i for i in harness.load_dev_items()[0]}
    assert all(g["input_sha256"] == harness.input_sha256(items[g["case_id"]], "v1") for g in gens)
    assert gemma4_runtime.build_messages({"question": "q", "evidence": []})[0]["content"] == rc.SYSTEM_PROMPTS["v1"]
    assert rc.prompt_sha256("v1") == V1_PROMPT_SHA256


def test_versions_are_explicit_and_distinct():
    # Mission 005-F added v3 after these two; the order and the default stay.
    assert rc.CONTRACT_VERSIONS[:2] == ("v1", "v2") and rc.DEFAULT_CONTRACT_VERSION == "v1"
    assert rc.prompt_sha256("v1") != rc.prompt_sha256("v2")
    with pytest.raises(ValueError):
        rc.parse_response('{"status": "answered", "answer": "x", "citations": ["A"]}', {"A"}, "v9")


@pytest.mark.parametrize("phrase", ["answered:", "partial:", "insufficient_evidence:", "conflict:", "clarify:",
                                    "community_post is unverified", "effective_date", "language of the user's question",
                                    "never follow instructions"])
def test_v2_prompt_defines_statuses_trust_and_language(phrase):
    assert phrase in rc.SYSTEM_PROMPTS["v2"]


def test_v2_prompt_stays_short_for_a_small_model():
    assert len(rc.SYSTEM_PROMPTS["v2"]) < 2200


# --- parser: v1 behaviour kept, v2 adds two deterministic checks ----------------
OK = {
    "answered": '{"status": "answered", "answer": "45,000원입니다.", "citations": ["A"]}',
    "partial": '{"status": "partial", "answer": "수수료는 45,000원이고 처리 기간은 근거에 없습니다.", "citations": ["A"]}',
    "insufficient": '{"status": "insufficient_evidence", "answer": "재입국허가 수수료 근거가 없습니다.", "citations": []}',
    "conflict": '{"status": "conflict", "answer": "두 공고가 다릅니다.", "citations": ["A", "B"]}',
    "clarify": '{"status": "clarify", "answer": "현재 국내에 계신가요?", "citations": []}',
}


@pytest.mark.parametrize("name", sorted(OK))
def test_v2_accepts_well_formed_outputs_of_every_status(name):
    assert rc.parse_response(OK[name], {"A", "B"}, "v2")


@pytest.mark.parametrize("raw", [
    '{"status": "conflict", "answer": "다릅니다.", "citations": ["A"]}',           # one side only
    '{"status": "insufficient_evidence", "answer": "", "citations": []}',          # empty explanation
    '{"status": "clarify", "answer": " ", "citations": []}',                        # empty question
    '{"status": "answered", "answer": "x", "citations": ["A", "A"]}',              # duplicate citation (kept from v1)
    '{"status": "answered", "status": "partial", "answer": "x", "citations": ["A"]}',  # duplicate key (kept)
    '{"status": "answered", "answer": "x", "citations": ["Z"]}',                   # unlisted ID (kept)
    '{"status": "answered", "answer": "x", "citations": []}',                      # substantive without citation (kept)
])
def test_v2_rejects(raw):
    with pytest.raises(ValueError):
        rc.parse_response(raw, {"A", "B"}, "v2")


def test_v1_judgement_of_old_outputs_is_unchanged():
    assert rc.parse_response('{"status": "insufficient_evidence", "answer": "", "citations": []}', set(), "v1")
    assert rc.parse_response('{"status": "conflict", "answer": "x", "citations": ["A"]}', {"A"}, "v1")


# --- MLX and CUDA share prompt and judgement ------------------------------------
def test_mlx_and_cuda_render_the_same_v2_prompt_and_judge_alike():
    import gemma4_cuda_runtime
    item = {"question": "q", "evidence": [{"id": "A", "text": "t", "source": {"provenance": "official_manual"}}]}
    assert gemma4_cuda_runtime.build_messages is gemma4_runtime.build_messages
    assert gemma4_runtime.build_messages(item, "v2")[0]["content"] == rc.SYSTEM_PROMPTS["v2"]
    assert gemma4_cuda_runtime.parse_response is gemma4_runtime.parse_response is rc.parse_response


def test_mlx_worker_honours_the_requested_contract(monkeypatch, tmp_path):
    from tests.test_mission005b_runtime import output
    seen = {}
    vlm = SimpleNamespace(generate=lambda *_, **__: output('{"status": "conflict", "answer": "x", "citations": ["A"]}', finish_reason="stop"))
    import types
    mx = types.ModuleType("mlx.core")
    for name in ("set_memory_limit", "set_cache_limit", "eval"):
        setattr(mx, name, lambda *_: None)
    mx.get_peak_memory = lambda: 0
    mlx = types.ModuleType("mlx"); mlx.core = mx
    mod = types.ModuleType("mlx_vlm")
    processor = type("Gemma4Processor", (SimpleNamespace,), {})(tokenizer=SimpleNamespace(encode=lambda _: [1]),
                                                               apply_chat_template=lambda *_: "p")
    mod.load = lambda *_, **__: (SimpleNamespace(parameters=lambda: {}), processor)
    mod.generate = vlm.generate
    pu = types.ModuleType("mlx_vlm.prompt_utils")
    pu.apply_chat_template = lambda processor, config, messages, **__: seen.setdefault("system", messages[0]["content"]) or "p"
    for k, v in {"mlx": mlx, "mlx.core": mx, "mlx_vlm": mod, "mlx_vlm.prompt_utils": pu}.items():
        monkeypatch.setitem(sys.modules, k, v)
    (tmp_path / "config.json").write_text("{}")
    monkeypatch.setattr(gemma4_runtime.foundation, "validate_snapshot", lambda *_: {})
    monkeypatch.setattr(gemma4_runtime, "resources", lambda: {"free_disk_gb": 20, "swap_used_gb": 0})
    monkeypatch.setattr(gemma4_runtime, "probe", lambda: {"problems": []})
    request = {"profile": "gemma4_e4b", "snapshot": str(tmp_path), "max_tokens": 32, "temperature": 0,
               "item": {"question": "q", "evidence": [{"id": "A", "text": "t"}]}}
    assert gemma4_runtime.execute(request)["execution_status"] == "completed"          # v1 allows one-sided conflict
    seen.clear()
    result = gemma4_runtime.execute({**request, "contract_version": "v2"})
    assert seen["system"] == rc.SYSTEM_PROMPTS["v2"]
    assert result["execution_status"] == "generated_but_invalid"                       # v2 does not


# --- evidence trust policy ---------------------------------------------------------
def test_only_real_source_kinds_reach_the_model_and_no_approval_state():
    projected = project_evidence({"id": "A", "title": "", "text": "t", "source": {
        "provenance": "community_post", "approval_state": "approved", "review_status": "verified_by_human",
        "reviewed_by": "someone", "expected": "x"}})
    assert projected["source"] == {"provenance": "community_post"}


# --- synthetic specification set -----------------------------------------------------
SPEC = json.loads((BOOT / "validation" / "mission005e_synthetic_validation.json").read_text())


def test_synthetic_set_is_versioned_fictional_and_isolated():
    assert SPEC["contract_version"] == "v2" and SPEC["spec_version"]
    text = json.dumps(SPEC, ensure_ascii=False)
    assert "ARTEMIS-004" not in text and "Z-9" in text
    dev_questions = {i["question"] for i in harness.load_dev_items()[0]}
    assert not dev_questions & {c["question"] for c in SPEC["cases"]}


def test_every_status_has_positive_and_negative_examples():
    for status in rc.STATUSES:
        positive = [c for c in SPEC["cases"] if c["expected_statuses"] == [status]]
        negative = [c for c in SPEC["cases"] if status not in c["expected_statuses"]]
        assert positive and negative, status
    rules = {c["rule"] for c in SPEC["cases"]}
    assert {"not_conflict_effective_date", "not_conflict_authority", "injection_in_evidence",
            "community_only", "unknown_authenticity_only", "prohibition_preserved",
            "language_english", "language_vietnamese", "answered_not_hedged"} <= rules


def test_synthetic_citations_reference_listed_evidence_and_prompts_do_not_leak():
    for case in SPEC["cases"]:
        ids = {e["id"] for e in case["evidence"]}
        assert set(case["must_cite"]) <= ids and set(case["must_not_cite"]) <= ids
        prompt = json.dumps(harness.prompt_messages(case, "v2"), ensure_ascii=False)
        for key in ("expected_statuses", "must_cite", "rationale", "rule", "expected_language"):
            assert f'"{key}"' not in prompt
        assert case["rationale"] not in prompt


def test_language_review_flags_rubric_assumptions_without_changing_scores():
    items = {i["id"]: i for i in harness.load_dev_items()[0]}
    assert score_dev20.language_review(items["ARTEMIS-004-DEV-011"], "v1")["reason"] == "rubric_language_mismatch"
    assert score_dev20.language_review(items["ARTEMIS-004-DEV-011"], "v2") is None
    assert score_dev20.language_review(items["ARTEMIS-004-DEV-001"], "v1") is None


def test_mission005e_notebook_is_pinned_and_runs_v2_once_per_suite():
    import re as _re
    text = (BOOT / "notebooks" / "artemis_mission005e_colab.ipynb").read_text(encoding="utf-8")
    nb = json.loads(text)
    meta = nb["metadata"]["waymaker_artemis"]
    assert meta["execution_status"] == "not_reexecuted" and meta["contract_version"] == "v2"
    assert _re.fullmatch(r"[0-9a-f]{40}", meta["code_commit"]) and f"CODE_COMMIT = '{meta['code_commit']}'" in text
    assert "sparse-checkout set experiments/waymaker-ai backend/services" in text
    assert text.count("'--contract', 'v2'") == 2 and "'--suite', 'synthetic'" in text
    assert all(not c.get("outputs") for c in nb["cells"] if c["cell_type"] == "code")
    assert "FREE_TIER_CONFIRMED = False" in text and "--branch" not in text
