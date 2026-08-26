#!/usr/bin/env python3
"""Live AI runtime smoke across EVERY LLM-backed Visable feature.

Why every feature, not just /api/ask
------------------------------------
The existing live smoke exercised /api/ask only. Two other endpoints were
completely broken — every request reporting a healthy provider as an outage —
and nothing noticed, because nothing ever asked them to succeed.

So this harness calls each AI feature and asks the only question that matters:
did it actually produce output? "Returned 200 with a graceful degradation
message" is a PASS for resilience and a FAIL for readiness, and those are
tracked separately here.

Honesty rules
-------------
* Without ``--require-live`` an unreachable or unconfigured backend is reported
  as **LIVE AI NOT VERIFIED**, never as "healthy". A skipped check is not a
  passing check.
* With ``--require-live`` an unreachable backend, an unconfigured provider, or
  a real completion failure is a FAILURE. That is the flag CI uses when it
  genuinely intends to gate on production AI.
* Questions are synthetic and non-personal.
* No credential is read, sent or printed. Provider keys live in the backend
  environment; this tool only reads non-secret booleans and public model ids
  from the readiness descriptor.

Usage
-----
    python3 scripts/smoke_ai_runtime.py --backend-url https://HOST
    python3 scripts/smoke_ai_runtime.py --backend-url https://HOST --require-live
    python3 scripts/smoke_ai_runtime.py --backend-url https://HOST --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TIMEOUT = 60

# Synthetic, non-personal questions spanning the scenarios the architecture
# brief calls out. Each names the behaviour it is probing so a failure report
# says what broke rather than just which index failed.
ASK_CASES: List[Tuple[str, str, Dict[str, Any]]] = [
    ("general_ko", "한국 비자 종류에는 어떤 것들이 있나요?", {}),
    ("d2_parttime_ko", "D-2 유학 자격으로 아르바이트를 할 수 있나요?", {"visa_code": "D-2"}),
    ("e7_workplace_ko", "E-7 자격인데 근무처를 변경하려면 어떻게 해야 하나요?", {"visa_code": "E-7"}),
    ("f6_divorce_ko", "F-6 자격인데 이혼 후 체류기간 연장이 가능한가요?", {"visa_code": "F-6"}),
    ("overstay_ko", "체류기간을 하루 넘겼습니다. 어떻게 해야 하나요?", {}),
    ("g1_refugee_ko", "G-1 자격의 체류기간 연장 절차가 궁금합니다.", {"visa_code": "G-1"}),
    ("english", "Can I work part-time on a D-2 student visa in Korea?", {"lang": "en"}),
    ("chinese", "D-2 留学签证可以打工吗？", {"lang": "zh-CN"}),
    ("fast_tier", "D-4 비자 연장 서류가 무엇인가요?", {"answer_mode": "fast"}),
    ("basic_tier", "체류자격 변경 절차를 알려주세요.", {"answer_mode": "basic"}),
    ("pro_tier", "E-7 근무처 변경 시 법적 근거와 판례를 알려주세요.", {"answer_mode": "pro"}),
]


class Check:
    def __init__(self, name: str, feature: str):
        self.name, self.feature = name, feature
        self.status = "not_run"     # ok | degraded | failed | skipped
        self.detail = ""
        self.latency_ms = 0
        self.metadata: Dict[str, Any] = {}

    def as_dict(self) -> Dict[str, Any]:
        return {"check": self.name, "feature": self.feature, "status": self.status,
                "detail": self.detail, "latencyMs": self.latency_ms,
                "metadata": self.metadata}


def http_json(url: str, payload: Optional[Dict[str, Any]] = None,
              timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, Any, int]:
    """GET/POST returning (status, parsed_body_or_text, latency_ms). Never raises."""
    started = time.monotonic()
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except Exception as exc:
        return 0, f"{exc.__class__.__name__}: {exc}", int((time.monotonic() - started) * 1000)

    latency = int((time.monotonic() - started) * 1000)
    try:
        return status, json.loads(raw), latency
    except ValueError:
        return status, raw, latency


def check_readiness(base: str) -> Tuple[Check, Dict[str, Any]]:
    check = Check("ai_readiness", "health")
    status, body, latency = http_json(f"{base}/api/health/ai")
    check.latency_ms = latency
    if status != 200 or not isinstance(body, dict):
        check.status = "failed"
        check.detail = f"/api/health/ai returned {status}"
        return check, {}

    check.metadata = {
        "aiReady": body.get("aiReady"),
        "activeProvider": body.get("activeProvider"),
        "runtimeVersion": body.get("runtimeVersion"),
        "modelPolicyVersion": body.get("modelPolicyVersion"),
        "lawMode": (body.get("grounding") or {}).get("law", {}).get("effectiveMode"),
        "manualReady": (body.get("grounding") or {}).get("manual", {}).get("ready"),
        "manualBlocker": (body.get("grounding") or {}).get("manual", {}).get("blocker"),
        "candidateWarnings": body.get("candidateWarnings"),
    }
    check.status = "ok" if body.get("aiReady") else "degraded"
    check.detail = ("provider configured" if body.get("aiReady")
                    else "no LLM provider configured on the backend")
    return check, body


def check_ask(base: str, name: str, question: str, extra: Dict[str, Any]) -> Check:
    check = Check(f"ask_{name}", "waymaker_ask")
    status, body, latency = http_json(f"{base}/api/ask", {"question": question, **extra})
    check.latency_ms = latency

    if status == 0:
        check.status, check.detail = "failed", f"transport failure: {body}"
        return check
    if status == 429:
        # Visable's OWN rate limiter, not a provider or feature fault. Running
        # 11 ask cases back to back trips it by design; counting that as a
        # failure would make the smoke report a working backend as broken.
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status == 503:
        detail = body.get("detail", {}) if isinstance(body, dict) else {}
        check.status = "degraded"
        check.detail = f"503 {detail.get('error', 'unavailable')}"
        check.metadata = {"providerErrorType": detail.get("provider_error_type")}
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check

    answer = (body.get("answer") or "").strip()
    check.metadata = {
        "finalModel": body.get("final_model"),
        "provider": body.get("provider"),
        "fallbackUsed": body.get("model_fallback_used"),
        "deterministicFallback": body.get("deterministic_fallback_answer_used"),
        "lawGroundingStatus": body.get("law_grounding_status"),
        "manualGroundingStatus": body.get("manual_grounding_status"),
        "answerChars": len(answer),
        "effectiveAnswerMode": body.get("effective_answer_mode") or body.get("answer_mode"),
    }
    if not answer:
        check.status, check.detail = "failed", "200 with an empty answer"
    elif body.get("deterministic_fallback_answer_used"):
        # Resilience worked; the model did not answer. Not a pass.
        check.status, check.detail = "degraded", "deterministic fallback answered, not the model"
    else:
        check.status, check.detail = "ok", f"{len(answer)} chars from {body.get('final_model')}"
    return check


def check_ai_overview(base: str) -> Check:
    check = Check("unified_ai_overview", "unified_search_ai_overview")
    status, body, latency = http_json(
        f"{base}/api/search/unified/ai-overview", {"query": "D-2 유학"})
    check.latency_ms = latency
    if status == 429:
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check

    check.metadata = {"status": body.get("status"), "reason": body.get("reason"),
                      "model": body.get("model")}
    state = body.get("status")
    if state == "ok" and (body.get("overview") or "").strip():
        check.status, check.detail = "ok", f"overview from {body.get('model')}"
    elif state in {"unavailable", "blocked", "not_applicable"}:
        check.status = "degraded"
        check.detail = f"{state}: {body.get('reason')}"
    else:
        check.status, check.detail = "failed", f"unexpected status {state!r}"
    return check


def check_employment_interpret(base: str) -> Check:
    check = Check("employment_interpret", "employment_interpret")
    status, body, latency = http_json(
        f"{base}/api/employment/interpret", {"text": "카페에서 음료를 만들고 손님을 응대합니다"})
    check.latency_ms = latency
    if status == 429:
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check

    check.metadata = {"status": body.get("status"), "reason": body.get("reason"),
                      "model": body.get("model")}
    state = body.get("status")
    if state == "ok":
        check.status, check.detail = "ok", "extraction produced"
        # The safety invariant: no classification code may originate here.
        blob = json.dumps(body, ensure_ascii=False)
        if any(code in blob for code in ("KSCO", "KSIC")):
            check.status = "failed"
            check.detail = "a classification code appeared in the extraction response"
    elif state in {"unavailable", "extraction_failed", "empty_input"}:
        check.status, check.detail = "degraded", f"{state}: {body.get('reason')}"
    else:
        check.status, check.detail = "failed", f"unexpected status {state!r}"
    return check


def check_nationality_coach(base: str) -> Check:
    check = Check("nationality_coach", "nationality_coach")
    status, body, latency = http_json(f"{base}/api/nationality-coach", {
        "mode": "naturalization_interview_prep",
        "question": "귀화를 신청한 이유는 무엇입니까?",
        "answer": "한국에서 오래 일했고 앞으로도 계속 살고 싶습니다.",
    })
    check.latency_ms = latency
    if status == 429:
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status == 503:
        check.status, check.detail = "degraded", "coach unavailable (hub falls back locally)"
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check

    check.metadata = {"provider": body.get("provider"), "model": body.get("model")}
    if body.get("ai_available"):
        check.status, check.detail = "ok", f"feedback from {body.get('provider')}"
        if not body.get("caution"):
            check.status, check.detail = "failed", "practice-only caution missing from feedback"
    else:
        check.status, check.detail = "degraded", "ai_available false"
    return check


def check_legal_research(base: str) -> Check:
    check = Check("legal_research", "legal_research")
    status, body, latency = http_json(
        f"{base}/api/legal/research", {"question": "체류자격 변경 요건", "depth": "basic"})
    check.latency_ms = latency
    if status == 429:
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check
    check.metadata = {"synthesisStatus": body.get("synthesisStatus"),
                      "synthesisModel": body.get("synthesisModel"),
                      "providerConfigured": body.get("providerConfigured")}
    if body.get("synthesisStatus") == "llm":
        check.status, check.detail = "ok", f"LLM synthesis via {body.get('synthesisModel')}"
    else:
        # Deterministic research still ran and is a valid product state.
        check.status = "degraded"
        check.detail = f"deterministic only ({body.get('synthesisStatus')})"
    return check


def check_enforcement(base: str) -> Check:
    check = Check("enforcement_intelligence", "enforcement_intelligence")
    status, body, latency = http_json(f"{base}/api/enforcement/extract", {
        "text": "D-2 자격으로 허가 없이 3개월간 음식점에서 일했습니다."})
    check.latency_ms = latency
    if status == 429:
        check.status = "skipped"
        check.detail = "skipped: Visable rate limit reached (re-run with --pace)"
        return check
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check
    case = body.get("case") or {}
    check.metadata = {"warnings": case.get("extraction_warnings", [])[:3]}
    check.status = "ok" if case else "failed"
    check.detail = "structured case produced" if case else "no case returned"
    return check


def check_deterministic_search_survives(base: str) -> Check:
    """The most important non-AI check: organic results never depend on the AI."""
    check = Check("organic_search_independent", "unified_search")
    status, body, latency = http_json(f"{base}/api/search/unified", {"query": "D-2"})
    check.latency_ms = latency
    if status != 200 or not isinstance(body, dict):
        check.status, check.detail = "failed", f"HTTP {status}"
        return check
    results = body.get("organicResults") or []
    check.metadata = {"organicResultCount": len(results)}
    if results:
        check.status, check.detail = "ok", f"{len(results)} organic results without any AI call"
    else:
        check.status, check.detail = "failed", "organic search returned nothing for D-2"
    return check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL", ""))
    parser.add_argument("--require-live", action="store_true",
                        help="Unreachable/unconfigured/failed completion = FAILURE.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--pace", type=float, default=0.0,
                        help="Seconds to wait between calls so Visable's own rate "
                             "limiter does not skip checks (try 8).")
    args = parser.parse_args()

    base = (args.backend_url or "").rstrip("/")
    if not base:
        message = ("No backend URL. Pass --backend-url or set BACKEND_URL.\n"
                   "LIVE AI NOT VERIFIED.")
        if args.json:
            print(json.dumps({"liveVerified": False, "reason": "no_backend_url",
                              "checks": []}, indent=2))
        else:
            print(message)
        return 1 if args.require_live else 0

    checks: List[Check] = []
    readiness, readiness_body = check_readiness(base)
    checks.append(readiness)

    reachable = readiness.status != "failed"
    provider_ready = bool(readiness.metadata.get("aiReady"))

    if reachable:
        checks.append(check_deterministic_search_survives(base))
        for index, (name, question, extra) in enumerate(ASK_CASES):
            if args.pace and index:
                time.sleep(args.pace)
            checks.append(check_ask(base, name, question, extra))
        checks.append(check_ai_overview(base))
        checks.append(check_employment_interpret(base))
        checks.append(check_nationality_coach(base))
        checks.append(check_legal_research(base))
        checks.append(check_enforcement(base))

    ok = [c for c in checks if c.status == "ok"]
    degraded = [c for c in checks if c.status == "degraded"]
    failed = [c for c in checks if c.status == "failed"]
    skipped = [c for c in checks if c.status == "skipped"]

    # A completion actually happened only if some AI feature produced output.
    ai_features = {"waymaker_ask", "unified_search_ai_overview", "employment_interpret",
                   "nationality_coach", "legal_research"}
    live_verified = any(c.status == "ok" and c.feature in ai_features for c in checks)

    exit_code = 1 if failed else 0
    if args.require_live and not live_verified:
        exit_code = 1

    if args.json:
        print(json.dumps({
            "backendUrl": base,
            "liveVerified": live_verified,
            "requireLive": args.require_live,
            "providerConfigured": provider_ready,
            "summary": {"ok": len(ok), "degraded": len(degraded),
                        "failed": len(failed), "skipped": len(skipped)},
            "checks": [c.as_dict() for c in checks],
            "exitCode": exit_code,
        }, ensure_ascii=False, indent=2))
        return exit_code

    print(f"Visable AI runtime smoke — {base}")
    print("=" * 68)
    for check in checks:
        marker = {"ok": "PASS", "degraded": "DEGR", "failed": "FAIL",
                  "skipped": "SKIP", "not_run": "----"}[check.status]
        print(f"  [{marker}] {check.name:<30} {check.latency_ms:>6}ms  {check.detail}")

    print(f"\n  PASS {len(ok)}   DEGRADED {len(degraded)}   "
          f"FAILED {len(failed)}   SKIPPED {len(skipped)}")
    if skipped:
        print("  Skipped checks were NOT verified. Re-run with --pace 8 to cover them.")

    if not reachable:
        print("\n  Backend unreachable from here.")
    elif not provider_ready:
        print("\n  Backend reachable but NO LLM PROVIDER IS CONFIGURED.")

    blocker = readiness.metadata.get("manualBlocker")
    if blocker:
        print(f"\n  Manual grounding blocker: {blocker}")

    if live_verified:
        print("\n  LIVE AI VERIFIED — at least one feature produced a real completion.")
    else:
        # The whole point: never let "we did not check" read as "it is fine".
        print("\n  LIVE AI NOT VERIFIED — no AI feature produced a real completion.")
        if not args.require_live and not failed:
            print("  (Not a failure without --require-live, but NOT a healthy result either.)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
