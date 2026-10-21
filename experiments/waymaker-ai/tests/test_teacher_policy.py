"""Teacher policy (configs/teacher_policy.json) and the TeacherRecord gate.

The real policy is checked for what it must never say (a permitted trial or
competing-model channel, an invented quote). The gate is exercised against a
fictional policy with an approved sign-off, because the real one is pending
and must refuse everything.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from waymaker_ai.distillation import teacher_policy as tp

REPO_ROOT = Path(__file__).resolve().parents[3]
NOTES_DIR = REPO_ROOT / "docs" / "ai" / "waymaker-genesis" / "research-notes"

SHA_A = "a" * 64
SHA_B = "b" * 64
REVISION = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture(scope="module")
def real_policy() -> tp.TeacherPolicy:
    return tp.load_policy(tp.DEFAULT_POLICY_PATH)


@pytest.fixture(scope="module")
def real_policy_json() -> dict:
    return json.loads(tp.DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))


def fictional_policy_dict(signoff: str = "approved") -> dict:
    """A well-formed policy about fictional teachers. Nothing here reads any real terms."""
    return {
        "schema_version": tp.POLICY_SCHEMA_VERSION,
        "accessed": tp.POLICY_ACCESS_DATE,
        "status": "TEST ONLY: fictional providers and a fictional sign-off.",
        "default_decision": "deny",
        "legal_signoff": {
            "status": signoff,
            "reviewer": "fixture-reviewer" if signoff == "approved" else None,
            "date": "2026-10-19" if signoff == "approved" else None,
            "scope": "fixture",
            "note": "fixture",
        },
        "channels": {
            "self_hosted": {"description": "fixture", "terms_url": None},
            "fixture_api": {"description": "fixture", "terms_url": None},
        },
        "entries": [
            {
                "id": "fixture-open-weights",
                "provider": "fixture-lab",
                "channel": "self_hosted",
                "models": ["fixture-lab/teacher-*"],
                "weights_license": "fixture licence (fictional)",
                "output_use_for_training": "permitted_with_conditions",
                "waymaker_policy": "accepted",
                "conditions": [{"id": "fixture-notice", "text": "Keep the fixture notice."}],
                "clause_ref": {
                    "url": "https://example.invalid/fixture-terms",
                    "accessed": tp.POLICY_ACCESS_DATE,
                    "section": "fixture §1",
                    "quote": None,
                    "paraphrase": "Fictional clause.",
                },
                "notes": "",
            },
            {
                "id": "fixture-api-denied",
                "provider": "fixture-lab",
                "channel": "fixture_api",
                "models": ["*"],
                "weights_license": "n/a",
                "output_use_for_training": "not_permitted",
                "waymaker_policy": "accepted",
                "conditions": [],
                "clause_ref": {
                    "url": "https://example.invalid/fixture-api-terms",
                    "accessed": tp.POLICY_ACCESS_DATE,
                    "section": "fixture §2",
                    "quote": None,
                    "paraphrase": "Fictional denial.",
                },
                "notes": "",
            },
        ],
    }


@pytest.fixture()
def fictional_policy() -> tp.TeacherPolicy:
    return tp.parse_policy(fictional_policy_dict())


def record_dict(**overrides) -> dict:
    """A TeacherRecord that the fictional policy accepts; tests break one thing at a time."""
    record = {
        "schema_version": tp.RECORD_SCHEMA_VERSION,
        "record_id": "tr-0001",
        "example_id": "train-class-0001",
        "task": "status_procedure_classification",
        "teacher": {
            "provider": "fixture-lab",
            "model": "fixture-lab/teacher-1",
            "channel": "self_hosted",
            "weights_license": "fixture licence (fictional)",
            "revision": REVISION,
            "serving_host": "fixture vLLM",
            "serving_terms_url": None,
            "serving_terms_version": None,
        },
        "request_date": "2026-10-19",
        "prompt_sha256": SHA_A,
        "evidence_pack_sha256": None,
        "output": {"status_code": "E-7", "subcode": "E-7-4", "procedure": "extension"},
        "reasoning_requested": False,
        "has_legal_conclusions": False,
        "critical": False,
        "verification": {
            "deterministic_checks": [{"name": "label_schema", "passed": True, "detail": ""}],
            "wlie_claims": [],
            "human_review": {"status": "machine_checked", "reviewer": None, "reviewed_at": None},
        },
        "permitted": True,
        "acknowledged_condition_ids": ["fixture-notice"],
    }
    for key, value in overrides.items():
        record[key] = value
    return record


def gate(policy: tp.TeacherPolicy, **overrides) -> tp.GateResult:
    return tp.gate_record(tp.TeacherRecord.from_dict(record_dict(**overrides)), policy)


# ---------------------------------------------------------------------------
# is_permitted on the real policy
# ---------------------------------------------------------------------------
def test_real_policy_loads_with_default_deny_and_pending_signoff(real_policy, real_policy_json):
    assert real_policy_json["default_decision"] == "deny"
    assert real_policy.signoff.status == "pending"
    assert not real_policy.signoff.approved


@pytest.mark.parametrize("provider, model, channel", [
    ("unknown-lab", "unknown-lab/model-x", "self_hosted"),       # no entry
    ("openai", "openai/gpt-oss-120b", "made_up_channel"),        # unknown channel
    ("", "openai/gpt-oss-120b", "self_hosted"),                  # missing field
    ("openai", "openai/gpt-5-mini", "self_hosted"),              # listed provider, unlisted model
])
def test_default_deny(real_policy, provider, model, channel):
    decision = tp.is_permitted(provider, model, channel, real_policy)
    assert decision.permitted is False
    assert decision.verdict == "no_entry"
    assert decision.reasons


@pytest.mark.parametrize("provider, model, channel", [
    ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter_free"),
    ("nvidia", "nvidia/nemotron-3-super-120b-a12b:free", "openrouter_free"),
    ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b", "nvidia_api_catalog_trial"),
    ("thinkingmachines", "thinkingmachines/inkling:free", "openrouter_free"),
    ("thinkingmachines", "inkling", "tml_free_research_api"),
    ("openai", "gpt-5.6-terra", "openai_api"),
    ("anthropic", "claude-sonnet-5.5", "anthropic_api"),
    ("google", "google/gemma-3-27b-it", "self_hosted"),
    ("lgai-exaone", "LGAI-EXAONE/EXAONE-4.5-33B", "self_hosted"),            # NC licence, no competing models
    ("naver-hyperclovax", "naver-hyperclovax/HyperCLOVAX-SEED-Think-32B", "self_hosted"),
])
def test_known_not_permitted_teachers_are_denied(real_policy, provider, model, channel):
    decision = real_policy.is_permitted(provider, model, channel)
    assert decision.permitted is False
    assert decision.verdict == "not_permitted"
    assert decision.conditions == ()


@pytest.mark.parametrize("provider, model, channel", [
    ("google", "gemini-3.1-pro", "gemini_api"),
    ("google", "google/gemma-4-31b-it:free", "openrouter_free"),
    ("openai", "openai/gpt-oss-120b", "openrouter_paid"),
    ("meta", "llama-3.1-8b-instant", "groq"),
    ("qwen", "Qwen/Qwen3.5-9B", "self_hosted"),
    ("deepseek", "deepseek-ai/DeepSeek-R1", "self_hosted"),
    ("minimax", "MiniMaxAI/MiniMax-M3", "self_hosted"),
    ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b", "nvidia_nim_subscription"),
    ("kakao", "kakaocorp/kanana-2-3b-instruct", "self_hosted"),
    ("meta", "meta-models/Muse-Spark-Open-816B-A42B", "self_hosted"),
])
def test_requires_legal_review_is_not_a_permission(real_policy, provider, model, channel):
    decision = real_policy.is_permitted(provider, model, channel)
    assert decision.permitted is False
    assert decision.verdict == "requires_legal_review"


def test_permitted_with_conditions_returns_its_conditions(real_policy):
    decision = real_policy.is_permitted("openai", "openai/gpt-oss-120b", "self_hosted")
    assert decision.permitted is True
    assert decision.verdict == "permitted_with_conditions"
    assert decision.entry_ids == ("gpt-oss-self-hosted",)
    assert {"apache-2.0-notice", "pinned-weights-revision"} <= set(decision.condition_ids())

    gemma = real_policy.is_permitted("google", "google/gemma-4-31B-it", "self_hosted")
    assert gemma.permitted and "gemma-prohibited-use-policy-unresolved" in gemma.condition_ids()

    llama = real_policy.is_permitted("meta", "meta-llama/Llama-3.3-70B-Instruct", "self_hosted")
    assert llama.permitted and {"llama-name-prefix", "llama-built-with-notice"} <= set(llama.condition_ids())


def test_a_family_the_notes_never_assessed_is_denied_by_default(real_policy):
    # K-EXAONE 2.0 is Apache-2.0, but no note assessed it as a teacher.
    decision = real_policy.is_permitted("lgai-exaone", "LGAI-EXAONE/K-EXAONE-2.0-750B-A37B", "self_hosted")
    assert decision.permitted is False and decision.verdict == "no_entry"


def test_same_weights_on_a_trial_channel_stay_denied(real_policy):
    # OpenMDW permits the self-hosted weights; the trial channel still decides its own route.
    assert real_policy.is_permitted("nvidia", "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16", "self_hosted").permitted
    assert not real_policy.is_permitted("nvidia", "nvidia/nemotron-3.5-lightning:free", "openrouter_free").permitted


def test_an_api_route_id_cannot_be_declared_self_hosted(real_policy):
    decision = real_policy.is_permitted("google", "google/gemma-4-31b-it:free", "self_hosted")
    assert decision.permitted is False
    assert "API route id" in decision.reasons[0]


def test_real_policy_covers_every_provider_family_in_the_notes(real_policy):
    providers = {entry.provider for entry in real_policy.entries}
    assert {
        "nvidia", "google", "thinkingmachines", "openai", "anthropic", "meta",
        "nousresearch", "qwen", "deepseek", "minimax", "inclusionai",
        # models.md §4 families whose licences say something about outputs or distillation
        "lgai-exaone", "naver-hyperclovax", "kakao",
    } <= providers
    channels = {entry.channel for entry in real_policy.entries}
    assert {"openrouter_free", "openrouter_paid", "groq", "ollama_local", "self_hosted"} <= channels


def test_only_waymaker_accepted_families_are_ever_permitted(real_policy):
    for entry in real_policy.entries:
        if entry.output_use in (tp.OutputUse.PERMITTED, tp.OutputUse.PERMITTED_WITH_CONDITIONS):
            assert entry.waymaker_policy == "accepted", entry.id
            assert entry.channel == tp.SELF_HOSTED_CHANNEL, entry.id


def test_clause_refs_are_dated_and_quotes_are_copied_from_the_notes(real_policy):
    notes = "".join(
        (NOTES_DIR / name).read_text(encoding="utf-8") for name in ("training-distill.md", "models.md")
        if (NOTES_DIR / name).is_file()
    )
    if not notes:
        pytest.skip("research notes are not in this checkout")
    quotes = [entry.clause_ref.quote for entry in real_policy.entries if entry.clause_ref.quote]
    assert len(quotes) <= 1, "the notes recorded one verbatim clause; everything else is paraphrase"
    for entry in real_policy.entries:
        ref = entry.clause_ref
        assert ref.accessed == "2026-10-19"
        assert ref.url.startswith("https://")
        if ref.quote:
            assert len(ref.quote.split()) <= tp.MAX_QUOTE_WORDS
            assert ref.quote in notes, f"{entry.id}: quote is not verbatim in the verified notes"
        else:
            assert ref.paraphrase


# ---------------------------------------------------------------------------
# Malformed policies
# ---------------------------------------------------------------------------
def _broken(mutate) -> dict:
    data = fictional_policy_dict()
    mutate(data)
    return data


@pytest.mark.parametrize("mutate, expected", [
    (lambda d: d.update(default_decision="allow"), "default_decision must be 'deny'"),
    (lambda d: d.update(schema_version="v9"), "schema_version"),
    (lambda d: d.update(surprise=True), "unknown key 'surprise'"),
    (lambda d: d.pop("entries"), "entries must be a non-empty list"),
    (lambda d: d["entries"][0].update(output_use_for_training="maybe"), "output_use_for_training must be one of"),
    (lambda d: d["entries"][0].update(channel="nowhere"), "is not declared in channels"),
    (lambda d: d["entries"][0].update(conditions=[]), "needs at least one condition"),
    (lambda d: d["entries"][0].update(waymaker_policy="chinese_routes_only"), "only a family Waymaker's policy accepts"),
    (lambda d: d["entries"][0]["clause_ref"].update(quote=" ".join(["word"] * 26)), "at most 25 words"),
    (lambda d: d["entries"][0]["clause_ref"].update(accessed="2026-01-01"), "clause_ref.accessed"),
    (lambda d: d["entries"][0]["clause_ref"].update(url="http://insecure.example"), "https URL"),
    (lambda d: d["entries"][1].update(id="fixture-open-weights"), "duplicate id"),
    (lambda d: d["legal_signoff"].update(reviewer=None), "must name the reviewer"),
    (lambda d: d["legal_signoff"].update(status="probably"), "legal_signoff.status"),
])
def test_malformed_policy_is_rejected_with_the_reason(mutate, expected):
    with pytest.raises(tp.PolicyError) as caught:
        tp.parse_policy(_broken(mutate))
    assert any(expected in problem for problem in caught.value.problems), caught.value.problems


def test_policy_that_is_not_json_is_rejected(tmp_path: Path):
    path = tmp_path / "policy.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(tp.PolicyError):
        tp.load_policy(path)
    with pytest.raises(tp.PolicyError):
        tp.parse_policy(["a", "list"])


# ---------------------------------------------------------------------------
# The record gate
# ---------------------------------------------------------------------------
def test_a_clean_record_passes_the_fictional_gate(fictional_policy):
    result = gate(fictional_policy)
    assert result.accepted, result.reasons
    assert [c.id for c in result.conditions] == ["fixture-notice"]


def test_record_round_trips_through_dict():
    record = tp.TeacherRecord.from_dict(record_dict())
    assert tp.TeacherRecord.from_dict(record.to_dict()) == record


def test_real_policy_refuses_every_record_until_signoff(real_policy):
    record = tp.TeacherRecord.from_dict(record_dict(
        teacher={
            "provider": "openai", "model": "openai/gpt-oss-120b", "channel": "self_hosted",
            "weights_license": "apache-2.0", "revision": REVISION,
        },
        acknowledged_condition_ids=["apache-2.0-notice", "gpt-oss-usage-policy", "pinned-weights-revision"],
    ))
    result = tp.gate_record(record, real_policy)
    assert not result.accepted
    assert any("legal_signoff is 'pending'" in reason for reason in result.reasons)
    assert len(result.reasons) == 1, "the teacher itself is permitted; only the sign-off is missing"


def test_unpermitted_teacher_is_refused_even_if_the_record_says_permitted(fictional_policy):
    result = gate(fictional_policy, teacher={
        "provider": "fixture-lab", "model": "fixture-lab/teacher-1", "channel": "fixture_api",
        "weights_license": "n/a",
    })
    assert not result.accepted
    assert any("may not be used for training" in reason for reason in result.reasons)


def test_record_flagged_not_permitted_is_refused(fictional_policy):
    assert not gate(fictional_policy, permitted=False).accepted


def test_unacknowledged_condition_is_refused(fictional_policy):
    result = gate(fictional_policy, acknowledged_condition_ids=[])
    assert any("not acknowledged" in reason for reason in result.reasons)


def test_self_hosted_teacher_needs_a_pinned_revision(fictional_policy):
    teacher = dict(record_dict()["teacher"], revision="main")
    assert any("revision SHA" in reason for reason in gate(fictional_policy, teacher=teacher).reasons)


@pytest.mark.parametrize("overrides", [
    {"reasoning_requested": True},
    {"output": {"status_code": "E-7", "subcode": "E-7-4", "procedure": "extension", "reasoning": "because"}},
    {"output": {"status_code": "E-7", "subcode": "<think>E-7-4</think>", "procedure": "extension"}},
])
def test_chain_of_thought_never_passes(fictional_policy, overrides):
    assert not gate(fictional_policy, **overrides).accepted


def test_output_must_be_exactly_the_task_label_schema(fictional_policy):
    missing = gate(fictional_policy, output={"status_code": "E-7"})
    extra = gate(fictional_policy, output={"status_code": "E-7", "subcode": None, "procedure": None, "fee": "x"})
    assert any("lacks required" in reason for reason in missing.reasons)
    assert any("outside the" in reason for reason in extra.reasons)


def test_failed_deterministic_check_is_refused(fictional_policy):
    verification = copy.deepcopy(record_dict()["verification"])
    verification["deterministic_checks"] = [{"name": "subcode_hierarchy", "passed": False, "detail": "parent as subcode"}]
    assert not gate(fictional_policy, verification=verification).accepted


def _legal_record(claim_overall: str, review_status: str) -> dict:
    return record_dict(
        task="citation_verification",
        output={"overall": "verified", "layer_codes": {"source_identity": "source_verified"}},
        has_legal_conclusions=True,
        evidence_pack_sha256=SHA_B,
        verification={
            "deterministic_checks": [{"name": "label_schema", "passed": True}],
            "wlie_claims": [{"claim_id": "c1", "overall": claim_overall, "highest_verified_layer": 7}],
            "human_review": {
                "status": review_status,
                "reviewer": "fixture-reviewer" if review_status == "human_verified" else None,
                "reviewed_at": "2026-10-19" if review_status == "human_verified" else None,
            },
        },
    )


def test_legal_conclusion_needs_wlie_verified_and_human_verified(fictional_policy):
    accepted = tp.gate_record(tp.TeacherRecord.from_dict(_legal_record("verified", "human_verified")), fictional_policy)
    assert accepted.accepted, accepted.reasons

    not_verified = tp.gate_record(
        tp.TeacherRecord.from_dict(_legal_record("verified_partial", "human_verified")), fictional_policy
    )
    assert any("WLIE did not verify" in reason for reason in not_verified.reasons)

    machine_only = tp.gate_record(tp.TeacherRecord.from_dict(_legal_record("verified", "machine_checked")), fictional_policy)
    assert any("need 'human_verified'" in reason for reason in machine_only.reasons)


def test_legal_task_cannot_claim_it_has_no_legal_conclusions(fictional_policy):
    data = _legal_record("verified", "human_verified")
    data["has_legal_conclusions"] = False
    result = tp.gate_record(tp.TeacherRecord.from_dict(data), fictional_policy)
    assert any("has_legal_conclusions cannot be false" in reason for reason in result.reasons)


def test_critical_classification_label_needs_a_named_human(fictional_policy):
    result = gate(fictional_policy, critical=True)
    assert any("need 'human_verified'" in reason for reason in result.reasons)


def test_unreviewed_label_is_refused(fictional_policy):
    verification = copy.deepcopy(record_dict()["verification"])
    verification["human_review"] = {"status": "unreviewed"}
    assert not gate(fictional_policy, verification=verification).accepted


@pytest.mark.parametrize("overrides, expected", [
    ({"prompt_sha256": "not-a-hash"}, "prompt_sha256"),
    ({"task": "write_an_essay"}, "not a benchmark task"),
    ({"request_date": "19/10/2026"}, "request_date"),
    ({"output": "E-7"}, "structured labels"),
    ({"teacher": {"provider": "fixture-lab"}}, "teacher.model"),
])
def test_malformed_record_is_rejected(overrides, expected):
    with pytest.raises(tp.RecordError) as caught:
        tp.TeacherRecord.from_dict(record_dict(**overrides))
    assert any(expected in problem for problem in caught.value.problems), caught.value.problems


def test_hash_prompt_is_stable_and_order_sensitive():
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert tp.hash_prompt(messages) == tp.hash_prompt([dict(m) for m in messages])
    assert tp.hash_prompt(messages) != tp.hash_prompt(list(reversed(messages)))
