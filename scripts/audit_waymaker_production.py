#!/usr/bin/env python3
"""Privacy-safe Waymaker production truth audit.

The audit intentionally records no prompt, answer text, credential value,
authorization header, or raw provider response. Model identifiers and boolean
environment-variable presence flags are public operational metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from smoke_ai_runtime import http_json  # noqa: E402

DEFAULT_BACKEND_URL = "https://web-production-14f9a.up.railway.app"
CATALOG_URL = "https://openrouter.ai/api/v1/models"
SYNTHETIC_QUESTION = (
    "E-7 체류자격으로 근무처를 변경하려면 사전 허가가 필요한가요? "
    "필요한 절차와 확인할 법적 근거를 알려주세요."
)


def _repo_backend_url() -> str:
    candidates = [
        REPO_ROOT / "assets/js/backend-origin.js",
        REPO_ROOT / "ai.html",
        REPO_ROOT / "index.html",
    ]
    pattern = re.compile(r"https://[A-Za-z0-9.-]+\.up\.railway\.app")
    for path in candidates:
        try:
            match = pattern.search(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if match:
            return match.group(0).rstrip("/")
    return DEFAULT_BACKEND_URL


def _catalog(timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"Accept": "application/json", "User-Agent": "visable-production-truth-audit"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
        return {"reachable": False, "errorType": exc.__class__.__name__, "ids": set()}
    return {
        "reachable": True,
        "errorType": "",
        "ids": {
            str(item.get("id") or "")
            for item in payload.get("data") or []
            if isinstance(item, dict) and item.get("id")
        },
    }


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _detail(status: int, body: Any) -> Dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    if status >= 400 and isinstance(body.get("detail"), dict):
        return body["detail"]
    return body


def _bool_tree(value: Any) -> Any:
    """Keep env names and booleans only, even if a future backend regresses."""
    if isinstance(value, dict):
        return {str(key): _bool_tree(item) for key, item in value.items()}
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return bool(value)


def _cooling_models(readiness: Dict[str, Any]) -> List[str]:
    cooldown = _dict(readiness.get("cooldown"))
    for key in ("coolingModels", "cooling_models", "cooling_down_models", "models"):
        value = cooldown.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, dict):
            return sorted(str(item) for item in value)
    return []


def _finding(severity: str, code: str, detail: str) -> Dict[str, str]:
    return {"severity": severity, "code": code, "detail": detail}


def _alignment(answer: str, response: Dict[str, Any]) -> Dict[str, Any]:
    if not answer:
        return {
            "status": "not_verifiable",
            "reason": "no live model answer was produced",
            "scope": "structural_and_citation_guard",
        }
    reasons: List[str] = []
    unsupported = _list(response.get("unsupported_law_citations"))
    if unsupported or response.get("unverified_law_citation_detected"):
        reasons.append("unsupported_or_unverified_law_citation")
    manual_status = str(response.get("manual_grounding_status") or "")
    if manual_status == "absent" and re.search(r"매뉴얼(?:에|은|이)\s*(?:따르면|명시|규정)", answer):
        reasons.append("answer_claims_manual_authority_while_manual_grounding_absent")
    law_verified = bool(response.get("law_grounding_verified"))
    if not law_verified and re.search(r"(?:법|시행령|시행규칙)\s*제\s*\d+\s*조", answer):
        action = str(response.get("law_citation_guard_action") or "none")
        if action in {"none", "allow"}:
            reasons.append("specific_statute_claim_without_verified_law_grounding")
    return {
        "status": "misaligned" if reasons else "structurally_consistent",
        "reason": ", ".join(reasons) if reasons else "response metadata and citation guard are consistent",
        "scope": "structural_and_citation_guard",
    }


def run_audit(base: str, *, timeout: int) -> Dict[str, Any]:
    base = base.rstrip("/")
    health_status, health_body, health_ms = http_json(f"{base}/health", timeout=timeout)
    ready_status, ready_body, ready_ms = http_json(f"{base}/api/health/ai", timeout=timeout)
    health = _dict(health_body)
    readiness = _dict(ready_body)
    llm = _dict(health.get("llm"))
    grounding = _dict(readiness.get("grounding"))
    law = _dict(grounding.get("law"))
    manual = _dict(grounding.get("manual"))
    registry = _dict(grounding.get("documentRegistry"))
    before_cooling = _cooling_models(readiness)

    catalog = _catalog(timeout)
    candidates = [str(item) for item in _list(llm.get("model_candidates"))]
    catalog_state = [
        {"model": model, "listed": model in catalog["ids"] if catalog["reachable"] else None}
        for model in candidates
    ]

    ask_status, ask_body, ask_ms = http_json(
        f"{base}/api/ask",
        {"question": SYNTHETIC_QUESTION, "visa_code": "E-7", "answer_mode": "basic", "stream": False},
        timeout=timeout,
    )
    response = _detail(ask_status, ask_body)
    answer = str(response.get("answer") or "") if ask_status == 200 else ""

    after_status, after_body, after_ms = http_json(f"{base}/api/health/ai", timeout=timeout)
    after_readiness = _dict(after_body)
    after_cooling = _cooling_models(after_readiness)

    completion = bool(
        ask_status == 200
        and answer.strip()
        and not response.get("deterministic_fallback_answer_used")
    )
    attempts = [str(item) for item in _list(response.get("attempted_models"))]
    statuses = _list(response.get("upstream_statuses"))
    answer_fingerprint = (
        hashlib.sha256(answer.encode("utf-8")).hexdigest()[:16] if answer else ""
    )

    findings: List[Dict[str, str]] = []
    if not completion:
        if ask_status == 200 and response.get("deterministic_fallback_answer_used"):
            completion_detail = (
                "/api/ask returned a deterministic fallback after the live provider chain failed"
            )
        elif ask_status == 200:
            completion_detail = "/api/ask returned HTTP 200 without a usable live-provider answer"
        else:
            completion_detail = f"/api/ask returned HTTP {ask_status}"
        findings.append(_finding("P0", "LIVE_COMPLETION_FAILED", completion_detail))
    missing = [entry["model"] for entry in catalog_state if entry["listed"] is False]
    if missing:
        findings.append(_finding("P0", "STALE_MODEL_CANDIDATES", f"{len(missing)}/{len(candidates)} production candidates are absent from the public catalog"))
    if readiness.get("aiReady") and not completion:
        findings.append(_finding("P1", "CONFIG_READY_RUNTIME_RED", "configuration readiness did not produce a live completion"))
    if ask_ms >= 60_000:
        findings.append(_finding("P1", "LIVE_REQUEST_NEAR_FRONTEND_TIMEOUT", f"request took {ask_ms}ms against the 75s frontend deadline"))
    candidate_warnings = [str(item) for item in _list(readiness.get("candidateWarnings"))]
    active_override_markers = {
        "OPENROUTER_MODEL_ENV_OVERRIDE",
        "OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE",
    }
    ignored_override_markers = {
        "OPENROUTER_MODEL_ENV_OVERRIDE_IGNORED",
        "OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE_IGNORED",
    }
    if active_override_markers.intersection(candidate_warnings) or llm.get("model_env_override"):
        findings.append(_finding("P1", "DEPLOY_MODEL_OVERRIDE_ACTIVE", "deployment environment overrides the committed model policy"))
    elif ignored_override_markers.intersection(candidate_warnings) or llm.get("model_env_override_ignored"):
        findings.append(_finding("P1", "DEPLOY_MODEL_OVERRIDE_IGNORED", "stale deployment model variables are present but safely ignored; remove them from Railway"))
    law_warnings = [str(item) for item in _list(response.get("law_grounding_warnings"))]
    if any("PLACEHOLDER_IGNORED" in item for item in law_warnings):
        findings.append(_finding("P1", "LAW_OC_DISCARDED", "runtime discarded an explicitly configured OC and used legacy fallback"))
    if not manual.get("ready"):
        findings.append(_finding("P1", "MANUAL_GROUNDING_NOT_READY", str(manual.get("blocker") or "manual grounding is not ready")))
    task_type = str(response.get("task_type_detected") or "")
    question_type = str(response.get("question_type_detected") or "")
    issues = [str(item) for item in _list(response.get("legal_issue_types"))]
    if task_type == "workplace_change" and question_type == "status_change":
        findings.append(_finding("P1", "WORKPLACE_CHANGE_MISCLASSIFIED", "workplace-change intent was classified as status change"))

    alignment = _alignment(answer, response)
    if alignment["status"] == "misaligned":
        findings.append(_finding("P0", "ANSWER_EVIDENCE_MISALIGNED", alignment["reason"]))

    p0 = sum(item["severity"] == "P0" for item in findings)
    return {
        "audit": "Waymaker Production Truth Audit",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "backendUrl": base,
        "result": "PASS" if not findings else "FAIL",
        "summary": {"p0": p0, "p1": sum(item["severity"] == "P1" for item in findings)},
        "health": {
            "httpStatus": health_status,
            "latencyMs": health_ms,
            "aiHealthHttpStatus": ready_status,
            "aiHealthLatencyMs": ready_ms,
            "aiReady": readiness.get("aiReady"),
            "activeProvider": readiness.get("activeProvider"),
        },
        "providerAndModel": {
            "primaryModel": llm.get("primary_model") or llm.get("model"),
            "codeDefaultModel": llm.get("code_default_model"),
            "modelEnvOverride": bool(llm.get("model_env_override")),
            "modelEnvOverridePresent": bool(llm.get("model_env_override_present")),
            "modelEnvOverrideIgnored": bool(llm.get("model_env_override_ignored")),
            "modelEnvOverridesAllowed": bool(llm.get("model_env_overrides_allowed")),
            "environmentOverrides": _bool_tree(readiness.get("environmentOverrides") or {}),
            "candidates": catalog_state,
            "catalogReachable": catalog["reachable"],
            "catalogErrorType": catalog["errorType"],
            "candidateWarnings": candidate_warnings,
        },
        "cooldown": {
            "before": before_cooling,
            "after": after_cooling,
            "newlyCooling": sorted(set(after_cooling) - set(before_cooling)),
            "metadata": _dict(after_readiness.get("cooldown")),
            "afterHealthStatus": after_status,
            "afterHealthLatencyMs": after_ms,
        },
        "groundingReadiness": {
            "manual": {
                "approvedEditions": manual.get("approvedEditions"),
                "indexAvailable": manual.get("indexAvailable"),
                "indexedChunks": manual.get("indexedChunks"),
                "indexedDirectEvidenceChunks": manual.get("indexedDirectEvidenceChunks"),
                "ready": manual.get("ready"),
                "blocker": manual.get("blocker"),
            },
            "law": {
                "configured": law.get("configured"),
                "effectiveMode": law.get("effectiveMode"),
                "citationsTrustworthy": law.get("citationsTrustworthy"),
                "totalBudgetSeconds": law.get("totalBudgetSeconds"),
            },
            "documentRegistry": {
                "resolved": registry.get("resolved"),
                "source": registry.get("source"),
                "entries": registry.get("entries") or registry.get("entryCount"),
            },
        },
        "liveCompletion": {
            "completed": completion,
            "httpStatus": ask_status,
            "latencyMs": ask_ms,
            "provider": response.get("provider") or response.get("llm_provider"),
            "selectedModel": response.get("selected_model") or response.get("final_model"),
            "attemptedModels": attempts,
            "upstreamStatuses": statuses,
            "providerErrorType": response.get("provider_error_type"),
            "chainBudgetSeconds": response.get("chain_budget_seconds"),
            "chainBudgetExhausted": response.get("chain_budget_exhausted"),
            "answerChars": len(answer),
            "answerSha256Prefix": answer_fingerprint,
        },
        "evidencePacket": {
            "taskType": task_type,
            "questionType": question_type,
            "legalIssueTypes": issues,
            "manualGroundingStatus": response.get("manual_grounding_status"),
            "directEvidenceCount": response.get("direct_evidence_count"),
            "lawGroundingAttempted": response.get("law_grounding_attempted"),
            "lawGroundingStatus": response.get("law_grounding_status"),
            "lawGroundingStatusDetail": response.get("law_grounding_status_detail"),
            "lawGroundingVerified": response.get("law_grounding_verified"),
            "lawEvidenceCount": response.get("law_evidence_count"),
            "citationVerificationStatus": response.get("citation_verification_status"),
            "unverifiedLawCitationDetected": response.get("unverified_law_citation_detected"),
            "lawCitationGuardAction": response.get("law_citation_guard_action"),
            "lawWarnings": law_warnings,
        },
        "answerEvidenceAlignment": alignment,
        "findings": findings,
        "privacy": {
            "syntheticInputOnly": True,
            "promptStored": False,
            "answerTextStored": False,
            "credentialValuesStored": False,
            "rawProviderBodyStored": False,
        },
    }


def _md(report: Dict[str, Any]) -> str:
    lines = [
        "# Waymaker Production Truth Audit",
        "",
        f"- Result: **{report['result']}**",
        f"- Generated: `{report['generatedAt']}`",
        f"- Backend: `{report['backendUrl']}`",
        f"- P0/P1: `{report['summary']['p0']}` / `{report['summary']['p1']}`",
        "",
        "## Findings",
        "",
    ]
    findings = report["findings"]
    lines.extend(
        f"- **{item['severity']} {item['code']}** — {item['detail']}" for item in findings
    )
    if not findings:
        lines.append("- None")
    live = report["liveCompletion"]
    lines.extend([
        "",
        "## Live completion",
        "",
        f"- Completed: `{live['completed']}`; HTTP `{live['httpStatus']}`; latency `{live['latencyMs']}ms`",
        f"- Provider/model: `{live['provider']}` / `{live['selectedModel']}`",
        f"- Attempted: `{', '.join(live['attemptedModels'])}`",
        f"- Upstream statuses: `{live['upstreamStatuses']}`",
        f"- Chain budget: `{live['chainBudgetSeconds']}`; exhausted: `{live['chainBudgetExhausted']}`",
        f"- Answer: `{live['answerChars']}` chars; SHA-256 prefix `{live['answerSha256Prefix']}`",
        "",
        "## Candidate chain",
        "",
    ])
    lines.extend(
        f"- `{item['model']}` — catalog listed: `{item['listed']}`"
        for item in report["providerAndModel"]["candidates"]
    )
    lines.extend([
        "",
        "## Grounding and alignment",
        "",
        "```json",
        json.dumps({
            "groundingReadiness": report["groundingReadiness"],
            "evidencePacket": report["evidencePacket"],
            "answerEvidenceAlignment": report["answerEvidenceAlignment"],
            "cooldown": report["cooldown"],
            "environmentOverrides": report["providerAndModel"]["environmentOverrides"],
            "privacy": report["privacy"],
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "This report intentionally contains no prompt, answer text, credential value, or raw provider body.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default=_repo_backend_url())
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()

    report = run_audit(args.backend_url, timeout=max(10, args.timeout))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else _md(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")

    if report["summary"]["p0"]:
        return 1
    if args.require_live and not report["liveCompletion"]["completed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
