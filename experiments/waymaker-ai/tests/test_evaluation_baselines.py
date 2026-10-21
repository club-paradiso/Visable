"""Baseline adapters, tested without the backend, Node or a model server.

* B2: parent and subcode come from the guidance bundle's own kind / parent
  records and an exact code; an inherited ``target`` is never a subcode.
* existing_law: the spec 07 §4 mapping table, row by row, and the worst-per-layer
  combination over several citations.
* model: the structured-output contract, the loopback-only endpoint rule, and
  the OpenAI-compatible client against a fake poster (no socket is opened).
* wlie: the exact keyword calls into ``waymaker_ai.legal`` (with stub modules),
  and the real modules on an inline bundle when they are importable.
"""
from __future__ import annotations

import datetime as dt
import json
import socket
from pathlib import Path
from typing import Any, Dict, List

import pytest

from waymaker_ai.contracts import (
    ClaimVerification,
    Coverage,
    LayerOutcome,
    LayerResult,
    LookupResult,
    LookupStatus,
    TemporalAssessment,
    VerificationCode,
    VerificationLayer,
)
from waymaker_ai.evaluation.baselines import create
from waymaker_ai.evaluation.baselines.b2_js import derive_classification
from waymaker_ai.evaluation.baselines.base import EvalItem, RunContext
from waymaker_ai.evaluation.baselines.existing_law import backend_question, map_backend_verification
from waymaker_ai.evaluation.baselines.model import (
    ENDPOINT_ENV,
    MODEL_ENV,
    OpenAICompatible,
    OpenAICompatibleClient,
    build_messages,
    loopback_problem,
)
from waymaker_ai.evaluation.baselines.wlie import CountingAdapter, Wlie, claim_input_of
from waymaker_ai.evaluation.benchmark import LoadedBundle
from waymaker_ai.evaluation.predictions import parse_model_output

from tests.test_evaluation_runner import BUNDLE_ID, make_bundle, make_examples


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def ctx(tmp_path: Path) -> RunContext:
    return RunContext(repo_root=tmp_path, backend_python=Path("/nonexistent/python"), node=None, scratch_dir=tmp_path)


# ---------------------------------------------------------------------------
# B2
# ---------------------------------------------------------------------------
INDEX = {
    "E-7": {"kind": "status", "parent": None},
    "E-7-4": {"kind": "substatus", "parent": "E-7"},
    "F-2": {"kind": "status", "parent": None},
    "F-2-T": {"kind": "substatus", "parent": "F-2"},
    "D-10": {"kind": "status", "parent": None},
}


def test_b2_exact_subcode_and_parent_from_the_bundle():
    raw = {"codes": [{"code": "E-7-4", "exact": True}], "displayCode": "E-7-4", "target": "E-7", "inherited": True,
           "procedure": "extension", "stepKind": "resolved"}
    got = derive_classification(raw, INDEX)
    assert (got["status_code"], got["subcode"], got["procedure_fine"]) == ("E-7", "E-7-4", "extension")
    assert got["needs_clarification"] is False


def test_b2_t_variant_is_classified_by_bundle_data():
    got = derive_classification({"codes": [{"code": "F-2-T", "exact": True}], "stepKind": "source-only"}, INDEX)
    assert (got["status_code"], got["subcode"]) == ("F-2", "F-2-T")


def test_b2_inherited_parent_target_is_never_a_subcode():
    # Only the parent was recognised; the resolver's target is the parent too.
    got = derive_classification({"codes": [{"code": "E-7", "exact": True}], "target": "E-7", "inherited": True}, INDEX)
    assert (got["status_code"], got["subcode"]) == ("E-7", None)


def test_b2_non_exact_code_gives_a_parent_only_through_the_bundle():
    got = derive_classification({"codes": [{"code": "E-7-4", "exact": False}], "target": "E-7-4~"}, INDEX)
    assert (got["status_code"], got["subcode"]) == ("E-7", None)
    unknown = derive_classification({"codes": [{"code": "Z-9", "exact": True}]}, INDEX)
    assert unknown["status_code"] is None and unknown["subcode"] is None


def test_b2_transition_roles():
    raw = {"codes": [{"code": "E-7-4", "exact": True, "role": "target"}, {"code": "D-10", "exact": False}],
           "transitionFrom": "D-10", "procedure": "status_change", "stepKind": "source-only"}
    got = derive_classification(raw, INDEX)
    assert (got["current_status"], got["target_status"]) == ("D-10", "E-7-4")


def test_b2_cannot_receive_a_payload_code(tmp_path):
    payload_item = next(ex for ex in make_examples() if ex["input"].get("payload_status_code"))
    b2 = create(["b2_js"])[0]
    results = b2.run([EvalItem(payload_item)], RunContext(repo_root=tmp_path, backend_python=Path("x"),
                                                          node="node", scratch_dir=tmp_path))
    assert results[payload_item["id"]].status == "not_equivalent_input"


# ---------------------------------------------------------------------------
# existing_law: spec 07 §4 mapping
# ---------------------------------------------------------------------------
def _raw(*citations: Dict[str, Any], status: str = "") -> Dict[str, Any]:
    return {"citation_verification": {"status": status, "citations": list(citations)}}


def test_verified_maps_to_l1_and_l3_only_never_l2():
    got = map_backend_verification(_raw({"verification_status": "verified"}))
    assert got["layer_codes"] == {"source_identity": "source_verified", "citation_identity": "citation_verified"}
    assert got["overall"] == "verified_partial" and "version_identity" not in got["layer_codes"]


def test_declared_absence_is_mapped_as_declared():
    got = map_backend_verification(_raw({"verification_status": "failed_verification",
                                         "warnings": ["CITED_LAW_NOT_FOUND"]}))
    assert got["layer_codes"] == {"source_identity": "source_not_found"} and got["overall"] == "failed"


def test_detail_lookup_failure_and_article_miss_are_unavailable_not_absent():
    detail_error = map_backend_verification(_raw({"verification_status": "failed_verification",
                                                  "warnings": ["LAW_API_TIMEOUT"]}))
    article_miss = map_backend_verification(_raw({"verification_status": "source_linked_unverified",
                                                  "warnings": ["ARTICLE_TEXT_NOT_FOUND"]}))
    for got in (detail_error, article_miss):
        assert got["layer_codes"] == {"source_identity": "source_verified",
                                      "citation_identity": "verification_unavailable"}
        assert got["overall"] == "verification_unavailable"


def test_search_error_and_unchecked_states():
    error = map_backend_verification(_raw({"verification_status": "error", "warnings": ["SOURCE_UNAVAILABLE"]}))
    assert error["layer_codes"] == {"source_identity": "verification_unavailable"}
    extracted = map_backend_verification(_raw({"verification_status": "extracted_only"}))
    assert extracted["layer_codes"] == {"source_identity": "not_checked"}
    assert extracted["overall"] == "verification_unavailable"


def test_no_citation_extracted_uses_the_claim_level_status():
    assert map_backend_verification(_raw(status="verified_law_evidence"))["layer_codes"] == {
        "source_identity": "source_verified"}
    assert map_backend_verification(_raw(status="law_api_unavailable"))["overall"] == "verification_unavailable"


def test_worst_outcome_per_layer_over_several_citations():
    got = map_backend_verification(_raw({"verification_status": "verified"},
                                        {"verification_status": "failed_verification",
                                         "warnings": ["CITED_LAW_NOT_FOUND"]}))
    assert got["layer_codes"]["source_identity"] == "source_not_found"
    assert got["layer_codes"]["citation_identity"] == "citation_verified"
    assert got["overall"] == "failed"


def test_backend_question_appends_only_missing_citations():
    text, notes = backend_question({"text": "가상체류관리법 제5조에 따라 신고한다.", "citations": ["가상체류관리법 제5조"]})
    assert text == "가상체류관리법 제5조에 따라 신고한다." and notes == []
    text, notes = backend_question({"text": "신고 기한은 14일이다.", "citations": ["가상체류관리법 제5조"],
                                    "quoted_text": "14일 이내에 신고하여야 한다"})
    assert text.endswith("(가상체류관리법 제5조)")
    assert notes == ["citations_appended=1", "quoted_text_has_no_backend_channel"]
    text, notes = backend_question({"text": "같은 법 제5조에 따라 신고한다.", "citations": ["같은 법 제5조"],
                                    "context_title": "가상체류관리법"})
    assert text == "같은 법 제5조에 따라 신고한다." and notes == ["context_title_has_no_backend_channel"]


# ---------------------------------------------------------------------------
# Model contract
# ---------------------------------------------------------------------------
def test_model_classification_contract_keeps_wrong_values_for_scoring():
    answer = {"status_code": "E-7", "subcode": "E-7-4", "procedure": "extension", "current_status": None,
              "target_status": None, "dates": [{"value": "2026-11-03", "role": "stay_expiry_date"}],
              "needs_clarification": False}
    prediction, violations = parse_model_output(json.dumps(answer), "status_procedure_classification")
    assert violations == [] and prediction["subcode"] == "E-7-4" and prediction["procedure_fine"] == "extension"
    entity, _ = parse_model_output(answer, "entity_date_extraction")
    assert entity["dates"] == [{"value": "2026-11-03", "role": "stay_expiry_date"}]
    bad, violations = parse_model_output(dict(answer, subcode="E-7", procedure="visa"), "status_procedure_classification")
    assert bad["subcode"] == "E-7" and bad["procedure_fine"] == "visa"   # kept, so it is scored wrong
    assert "subcode is not a 3+-segment code" in violations and "procedure is not a fine procedure id" in violations


def test_model_prompt_reads_only_question_and_payload():
    example = json.loads(json.dumps(make_examples()[2]))
    example["expected"]["subcode"] = "LABEL-SENTINEL"
    example["scenario"]["notes"] = "NOTES-SENTINEL"
    example["source_refs"] = [{"kind": "none", "ref": "REF-SENTINEL"}]
    joined = json.dumps(build_messages(example), ensure_ascii=False)
    assert "UI-selected status code: E-7-1" in joined and "연장 서류" in joined
    for sentinel in ("LABEL-SENTINEL", "NOTES-SENTINEL", "REF-SENTINEL"):
        assert sentinel not in joined


@pytest.mark.parametrize("endpoint, ok", [
    ("http://127.0.0.1:8000/v1", True), ("http://localhost:11434/v1", True), ("http://[::1]:8000/v1", True),
    ("https://api.example.com/v1", False), ("http://user:pw@127.0.0.1:8000/v1", False), ("ftp://127.0.0.1/", False),
])
def test_model_endpoint_must_be_loopback(endpoint, ok):
    assert (loopback_problem(endpoint) is None) is ok


def test_openai_compatible_is_disabled_without_the_environment(tmp_path):
    baseline = OpenAICompatible(environ={})
    available, reason = baseline.available(ctx(tmp_path))
    assert available is False and ENDPOINT_ENV in reason
    remote = OpenAICompatible(environ={ENDPOINT_ENV: "https://api.example.com/v1", MODEL_ENV: "m"})
    assert remote.available(ctx(tmp_path))[0] is False


def test_openai_compatible_client_with_a_fake_poster(tmp_path):
    sent: List[Dict[str, Any]] = []
    answer = {"status_code": "D-2", "subcode": None, "procedure": "extension", "current_status": None,
              "target_status": None, "dates": [], "needs_clarification": False}

    def post(url: str, body: bytes, timeout: float):
        sent.append({"url": url, "body": json.loads(body)})
        reply = {"choices": [{"message": {"content": json.dumps(answer)}}],
                 "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}}
        return 200, json.dumps(reply).encode("utf-8")

    baseline = OpenAICompatible(environ={ENDPOINT_ENV: "http://127.0.0.1:8000/v1", MODEL_ENV: "local-test"}, post=post)
    assert baseline.available(ctx(tmp_path)) == (True, "")
    item = EvalItem(make_examples()[1])
    result = baseline.run([item], ctx(tmp_path))[item.id]
    assert result.status == "ok" and result.prediction["status_code"] == "D-2"
    assert result.tokens == {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    request = sent[0]["body"]
    assert sent[0]["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert request["temperature"] == 0 and request["response_format"]["type"] == "json_schema"
    assert "authorization" not in json.dumps(request).lower()


def test_openai_compatible_http_error_is_a_baseline_error():
    client = OpenAICompatibleClient("http://127.0.0.1:1/v1", "m", post=lambda *_a: (503, b""))
    with pytest.raises(Exception, match="HTTP 503"):
        client.complete({"messages": []}, "abstention")


# ---------------------------------------------------------------------------
# WLIE
# ---------------------------------------------------------------------------
class _StubAdapter:
    def __init__(self, bundle, *, path=None):
        self.bundle, self.path = bundle, path

    def list_versions(self, stable_id):
        return LookupResult(LookupStatus.FOUND, Coverage.COMPLETE, calls=1), ["v"]


class _StubAdapters:
    FixtureAdapter = _StubAdapter


class _StubVerification:
    calls: List[Dict[str, Any]] = []

    @classmethod
    def verify_claim(cls, claim, adapter, *, dates, anchor, question_date, context_title=None, secondary_anchors=()):
        cls.calls.append({"claim": claim, "anchor": anchor, "question_date": question_date})
        layer = LayerResult(VerificationLayer.SOURCE_IDENTITY, LayerOutcome.UNAVAILABLE,
                            VerificationCode.VERIFICATION_UNAVAILABLE, "stub")
        return ClaimVerification(claim.claim_id, (layer,))


class _StubTemporal:
    calls: List[Dict[str, Any]] = []

    @classmethod
    def select_candidate_versions(cls, versions, *, history, dates, anchor, secondary_anchors=(),
                                  provision_key=None, question_date):
        cls.calls.append({"versions": versions, "history": history, "provision_key": provision_key,
                          "question_date": question_date, "anchor": anchor})
        return TemporalAssessment(candidates=(), warnings=(), anchor=anchor, anchor_date=question_date)


def _bundle_item(example: Dict[str, Any], tmp_path: Path) -> EvalItem:
    path = tmp_path / f"{BUNDLE_ID}.json"
    path.write_text(json.dumps(make_bundle(), ensure_ascii=False), encoding="utf-8")
    return EvalItem(example, LoadedBundle(BUNDLE_ID, path, "0" * 64, make_bundle()))


def test_wlie_calls_the_contract_signatures_by_keyword(tmp_path):
    wlie = Wlie(modules={"adapters": _StubAdapters, "verification": _StubVerification, "temporal": _StubTemporal})
    examples = {ex["id"]: ex for ex in make_examples()}
    items = [_bundle_item(examples["cit-0002"], tmp_path), _bundle_item(examples["tmp-0001"], tmp_path)]
    results = wlie.run(items, ctx(tmp_path))
    assert results["cit-0002"].prediction["overall"] == "verification_unavailable"
    assert results["cit-0002"].prediction["injection_flagged"] is False
    verify = _StubVerification.calls[-1]
    assert verify["claim"].citations == ("가상응답장애법 제2조",)
    assert verify["anchor"].value == "question_date" and verify["question_date"] == dt.date(2026, 10, 19)
    temporal = _StubTemporal.calls[-1]
    assert temporal["provision_key"] == "제5조" and temporal["versions"] == ["v"]
    assert temporal["history"].status is LookupStatus.FOUND
    assert results["tmp-0001"].upstream_calls == 1
    assert results["tmp-0001"].prediction == {"candidate_version_keys": [], "warnings": [],
                                              "determination": "candidate_only"}


def test_wlie_passes_every_claim_field_of_the_schema_into_claim_input():
    # input.claim.context_title (the law 같은 법 / 영 / 규칙 refer to) must reach
    # contracts.ClaimInput, or a "같은 법 제18조" citation names no law at L1.
    example = {"id": "cit-ctx", "input": {"claim": {
        "text": "같은 법 제18조제2항에 따라 3년 내에 양도해야 한다.", "citations": ["같은 법 제18조제2항"],
        "context_title": "국적법", "quoted_text": "3년 내에", "numbers": ["3년"], "topic": "t", "value": "v",
        "asserted_version_key": ["244609", "2022-10-01"],
    }}}
    claim = claim_input_of(example)
    assert claim.context_title == "국적법"
    assert claim.citations == ("같은 법 제18조제2항",) and claim.numbers == ("3년",)
    assert claim.asserted_version_key == ("244609", "2022-10-01")
    example["input"]["claim"].pop("context_title")
    assert claim_input_of(example).context_title is None


def test_wlie_signature_drift_is_a_baseline_error_not_a_guess(tmp_path):
    class Renamed:
        @staticmethod
        def verify_claim(claim, adapter, *, relevant_dates, anchor_kind):
            raise AssertionError("must not be reached")

    wlie = Wlie(modules={"adapters": _StubAdapters, "verification": Renamed, "temporal": _StubTemporal})
    item = _bundle_item(next(ex for ex in make_examples() if ex["id"] == "cit-0002"), tmp_path)
    result = wlie.run([item], ctx(tmp_path))[item.id]
    assert result.status == "error" and "unexpected keyword argument" in result.error


def test_counting_adapter_sums_lookup_calls():
    counted = CountingAdapter(_StubAdapter({}))
    counted.list_versions("x")
    counted.list_versions("y")
    assert (counted.lookups, counted.upstream_calls) == (2, 2)
    assert counted.statuses == ["list_versions:found", "list_versions:found"]


def test_wlie_reference_implementation_on_the_inline_bundle(tmp_path):
    wlie = Wlie()
    available, reason = wlie.available(ctx(tmp_path))
    if not available:
        pytest.skip(f"waymaker_ai.legal not importable yet: {reason}")
    examples = {ex["id"]: ex for ex in make_examples()}
    items = [_bundle_item(examples[i], tmp_path) for i in ("cit-0002", "cit-0003", "tmp-0001")]
    results = wlie.run(items, ctx(tmp_path))
    assert {r.status for r in results.values()} == {"ok"}, {k: r.error for k, r in results.items()}
    unavailable = results["cit-0002"].prediction
    assert unavailable["overall"] == "verification_unavailable"
    assert not {"source_not_found", "citation_not_found"} & set(unavailable["codes"])   # failure is not absence
    future = results["cit-0003"].prediction
    assert future["overall"] == "failed"
    assert future["layer_codes"]["version_identity"] == "future_not_yet_effective"
    temporal = results["tmp-0001"].prediction
    assert temporal["candidate_version_keys"] == [["EVAL-V1", "2020-01-01"]]
    assert "future_version_pending" in temporal["warnings"]
