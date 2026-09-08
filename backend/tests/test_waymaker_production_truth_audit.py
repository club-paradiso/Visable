from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
for path in (BACKEND_DIR, REPO_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import audit_waymaker_production as audit  # noqa: E402
import paradiso_backend as pb  # noqa: E402
from services.legal_analysis import (  # noqa: E402
    classify_legal_issue_types,
    extract_immigration_facts,
)
from services.grounding_config import GroundingConfig  # noqa: E402
from services.law_grounding import build_law_grounding_context  # noqa: E402
from services.law_tools import LawHttpResponse, classify_law_question_type  # noqa: E402


def test_korean_object_particle_workplace_change_is_not_status_change():
    question = "E-7 체류자격으로 근무처를 변경하려면 사전 허가가 필요한가요?"
    facts = extract_immigration_facts(question, visa_code="E-7")
    issues = classify_legal_issue_types(question, facts)
    assert "workplace_change_addition" in issues
    assert "status_change" not in issues
    assert "workplace_change" in facts["proposed_activities"]
    assert "status_change_route" not in facts["proposed_activities"]
    law_classification = classify_law_question_type(
        question, visa_code="E-7", task_type="workplace_change"
    )
    assert law_classification["question_type"] == "deadline_or_report"


def test_law_search_plan_has_total_budget():
    calls = []

    def slow_no_result(url, timeout):
        calls.append((url, timeout))
        time.sleep(0.03)
        return LawHttpResponse(
            ok=False,
            status_code=200,
            text="",
            error_type="law_api_no_results",
        )

    cfg = GroundingConfig(
        law_api_oc="sentinel",
        mode="enabled",
        timeout_seconds=1,
        total_budget_seconds=0.05,
    )
    with patch("services.grounding_config.load_grounding_config", return_value=cfg), patch(
        "services.law_grounding.load_grounding_config", return_value=cfg
    ), patch("services.law_tools._default_transport", slow_no_result):
        result = build_law_grounding_context(
            "E-7 근무처를 변경할 때 신고와 허가의 법적 근거를 알려주세요"
        )
    assert len(calls) <= 2
    assert "LAW_GROUNDING_BUDGET_EXHAUSTED" in result["grounding_warnings"]


def test_buffered_candidate_chain_has_total_budget():
    calls = []

    async def hangs(prompt, model=None, max_tokens=None):
        calls.append(model)
        await asyncio.sleep(1)
        return "late"

    async def run():
        with patch.object(pb, "_call_openrouter", hangs), patch.object(
            pb, "OPENROUTER_CHAIN_BUDGET_SECONDS", 0.02
        ), patch.object(pb, "_cooling_down_models", return_value=[]), patch.object(
            pb, "_mark_openrouter_model_cooling_down"
        ):
            return await pb._openrouter_complete_with_candidates(
                "synthetic", candidate_models=["test/one", "test/two"]
            )

    result = asyncio.run(run())
    assert result["ok"] is False
    assert result["chain_budget_exhausted"] is True
    assert result["provider_error_type"] == "openrouter_chain_budget_exhausted"
    assert calls == ["test/one"]


def test_streaming_does_not_retry_models_when_all_are_cooling():
    calls = []

    async def must_not_run(*args, **kwargs):
        calls.append((args, kwargs))
        yield "unexpected"

    async def collect():
        frames = []
        with patch.object(pb, "_cooling_down_models", return_value=["test/one", "test/two"]), patch.object(
            pb, "_stream_openrouter_text", must_not_run
        ), patch.object(pb, "_build_deterministic_fallback_payload", return_value={"answer": "safe note"}):
            async for frame in pb._sse_answer_stream(
                "synthetic", ["test/one", "test/two"], 10, {},
                prompt="synthetic", lang="ko",
            ):
                frames.append(frame)
        return frames

    frames = asyncio.run(collect())
    assert not calls
    assert any("all_candidates_cooling_down" in frame for frame in frames)
    assert any("safe note" in frame for frame in frames)


def _health(candidates):
    return {
        "llm": {
            "model": candidates[0],
            "primary_model": candidates[0],
            "code_default_model": "current/default",
            "model_env_override": True,
            "model_candidates": candidates,
        }
    }


def _ready(cooling=None):
    return {
        "aiReady": True,
        "activeProvider": "openrouter",
        "candidateWarnings": ["OPENROUTER_MODEL_ENV_OVERRIDE"],
        "environmentOverrides": {"model": {"OPENROUTER_MODEL": True}},
        "cooldown": {"cooling_down_models": cooling or [], "chainBudgetSeconds": 45},
        "grounding": {
            "law": {"configured": True, "effectiveMode": "enabled", "citationsTrustworthy": True},
            "manual": {
                "approvedEditions": 0,
                "indexAvailable": False,
                "indexedChunks": 0,
                "indexedDirectEvidenceChunks": 0,
                "ready": False,
                "blocker": "no approved edition",
            },
            "documentRegistry": {"resolved": True, "source": "backend-data", "entries": 101},
        },
    }


def test_failed_audit_detects_stale_chain_and_is_privacy_safe():
    stale = ["gone/one:free", "live/two:free"]
    replies = iter([
        (200, _health(stale), 1),
        (200, _ready(), 1),
        (503, {"detail": {
            "provider_error_type": "model_not_found",
            "attempted_models": stale,
            "upstream_statuses": [404, 429],
            "task_type_detected": "workplace_change",
            "question_type_detected": "status_change",
            "legal_issue_types": ["status_change"],
            "law_grounding_warnings": ["LAW_API_OC_PLACEHOLDER_IGNORED_FOR_RAILWAY_KEY_FALLBACK"],
        }}, 100),
        (200, _ready(["live/two:free"]), 1),
    ])

    with patch.object(audit, "http_json", side_effect=lambda *a, **k: next(replies)), patch.object(
        audit, "_catalog", return_value={"reachable": True, "errorType": "", "ids": {"live/two:free"}}
    ):
        report = audit.run_audit("https://example.invalid", timeout=10)

    codes = {item["code"] for item in report["findings"]}
    assert {"LIVE_COMPLETION_FAILED", "STALE_MODEL_CANDIDATES", "LAW_OC_DISCARDED"} <= codes
    serialized = json.dumps(report, ensure_ascii=False)
    assert audit.SYNTHETIC_QUESTION not in serialized
    assert "answer" not in report["liveCompletion"]
    assert report["privacy"]["credentialValuesStored"] is False


def test_successful_audit_reports_hash_and_structural_alignment():
    model = "current/model:free"
    replies = iter([
        (200, _health([model]), 1),
        (200, {**_ready(), "candidateWarnings": []}, 1),
        (200, {
            "answer": "공식 확인이 필요한 안전한 안내입니다.",
            "provider": "openrouter",
            "selected_model": model,
            "final_model": model,
            "attempted_models": [model],
            "upstream_statuses": [],
            "task_type_detected": "workplace_change",
            "question_type_detected": "workplace_change",
            "legal_issue_types": ["workplace_change_addition"],
            "manual_grounding_status": "present",
            "direct_evidence_count": 1,
            "law_grounding_verified": True,
            "law_evidence_count": 1,
            "unverified_law_citation_detected": False,
            "law_citation_guard_action": "none",
        }, 50),
        (200, _ready(), 1),
    ])
    with patch.object(audit, "http_json", side_effect=lambda *a, **k: next(replies)), patch.object(
        audit, "_catalog", return_value={"reachable": True, "errorType": "", "ids": {model}}
    ):
        report = audit.run_audit("https://example.invalid", timeout=10)
    assert report["liveCompletion"]["completed"] is True
    assert report["liveCompletion"]["answerSha256Prefix"]
    assert report["answerEvidenceAlignment"]["status"] == "structurally_consistent"
