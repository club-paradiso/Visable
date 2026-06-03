#!/usr/bin/env python3
"""
Provider-aware live AI answer-quality smoke for Paradiso /api/ask.

This harness is SAFE BY DEFAULT:
  * It runs in no-provider mode without failing (records a skipped-live status).
  * It only performs live answer-quality checks when the backend reports an LLM
    provider is configured (e.g. the deployed Railway backend with keys set).
  * It NEVER prints API keys or secrets — it reads only non-secret booleans and
    public model identifiers from the /health descriptor.
  * It does NOT require live LLM calls in CI (CI keeps LAW_GROUNDING_MODE/provider
    unset, so this records skipped-live and exits 0).

What it reports:
  * backend URL tested
  * whether an LLM provider is configured (boolean only)
  * the selected model (public catalog id)
  * whether Groq fallback is allowed (non-secret boolean) + any llm warnings
  * the law-grounding mode (disabled / audit / enabled)
  * for each sample question: whether the live answer check was skipped (503
    no-provider) or executed, whether law grounding was attempted, whether the
    manual-to-law fallback was triggered, and whether selected route/variant
    context was echoed in the response metadata
  * whether the no-provider 503 behavior is safe

Usage (local, no provider — records skipped, exits 0):
    python3 scripts/smoke_ai_live_quality.py
    BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_live_quality.py

Usage (deployed Railway backend with provider keys configured):
    BACKEND_URL="https://YOUR-RAILWAY-BACKEND.up.railway.app" \
        python3 scripts/smoke_ai_live_quality.py
    python3 scripts/smoke_ai_live_quality.py \
        --backend-url https://YOUR-RAILWAY-BACKEND.up.railway.app

Options:
    --json            Emit a machine-readable JSON report.
    --backend-url U   Override BACKEND_URL.
    --require-live    Fail (exit 1) if no provider is configured or the backend
                      is unreachable. Off by default so CI stays green.

Secrets: do NOT pass API keys to this script. Provider keys are read from the
backend environment (e.g. Railway) and are never transmitted to or printed by
this tool.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BACKEND = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# Representative, route-relevant sample questions. Each carries minimal,
# non-personal visa_data context (code only) plus optional selected route/variant
# identifiers (never checklist/reminder state, never personal data).
SAMPLE_QUESTIONS = [
    {
        "id": "h1_seasonal_course",
        "visa_code": "H-1",
        "question": "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?",
    },
    {
        "id": "f4_domestic_residence",
        "visa_code": "F-4",
        "question": "F-4로 들어왔는데 국내거소신고를 해야 하나요?",
    },
    {
        "id": "b2_to_f4",
        "visa_code": "F-4",
        "question": "B-2로 들어와서 F-4로 바꿀 수 있나요?",
    },
    {
        "id": "f6_divorce_extension",
        "visa_code": "F-6",
        "question": "F-6인데 이혼 후에도 체류기간 연장이 가능한가요?",
        # Route -> source-backed F-6 marriage-terminated variant (safe ids only).
        "selected_procedure_key": "statusChange",
        "selected_procedure_variant_id": "f-6-3-marriage-terminated-status-change",
    },
    {
        "id": "g1_medical",
        "visa_code": "G-1",
        "question": "G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?",
        "selected_procedure_key": "statusChange",
        "selected_procedure_variant_id": "g-1-10-medical-patient-status-change",
    },
    {
        "id": "d10_to_e7",
        "visa_code": "D-10",
        "question": "D-10에서 E-7로 바꾸려면 무엇을 봐야 하나요?",
        "selected_procedure_key": "statusChange",
        "selected_procedure_variant_id": "d-10-1-points-status-change",
    },
    {
        "id": "h2_to_f4",
        "visa_code": "H-2",
        "question": "H-2에서 F-4로 변경할 수 있나요?",
    },
]

# Conservative, obviously-unsupported approval/guarantee phrasing. We do NOT
# overfit to exact LLM wording — only a tiny denylist of clearly unsafe claims.
UNSAFE_APPROVAL_PHRASES = [
    "guaranteed approval",
    "guarantee approval",
    "approval is guaranteed",
    "100% approval",
    "100% approved",
    "will definitely be approved",
    "반드시 승인",
    "승인을 보장",
    "승인이 보장",
    "100% 승인",
    "무조건 승인",
    "무조건 허가",
    "반드시 허가",
]


def _http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), json.loads(resp.read().decode())


def _http_post(url, payload, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = {}
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            body = {}
        return exc.code, body


def _safe_health(base):
    """Return a non-secret health descriptor, or None if unreachable."""
    try:
        _, body = _http_get(base.rstrip("/") + "/health")
        return body if isinstance(body, dict) else None
    except Exception:
        return None


def _check_question(base, q):
    """POST one sample question and classify the outcome safely."""
    payload = {
        "question": q["question"],
        "consent": True,
        "lang": "ko",
        "visa_data": {"code": q["visa_code"]},
    }
    if q.get("selected_procedure_key") and q.get("selected_procedure_variant_id"):
        payload["selected_procedure_key"] = q["selected_procedure_key"]
        payload["selected_procedure_variant_id"] = q["selected_procedure_variant_id"]

    sent_selected_context = bool(q.get("selected_procedure_variant_id"))
    result = {
        "id": q["id"],
        "visa_code": q["visa_code"],
        "sent_selected_context": sent_selected_context,
        "status": None,
        "live_answer_checked": False,
        "law_grounding_attempted": None,
        "law_grounding_status": None,
        "manual_grounding_status": None,
        "manual_to_law_fallback_used": None,
        "variant_context_used": None,
        "unsafe_approval_language": None,
        "metadata_present": None,
        "ok": False,
        "note": "",
    }

    try:
        status, body = _http_post(base.rstrip("/") + "/api/ask", payload)
    except Exception as exc:  # pragma: no cover - network dependent
        result["status"] = "unreachable"
        result["note"] = "request failed: %s" % type(exc).__name__
        return result

    result["status"] = status
    body = body if isinstance(body, dict) else {}
    # The no-provider 503 payload nests its safe metadata under "detail".
    meta = body.get("detail") if (status == 503 and isinstance(body.get("detail"), dict)) else body

    result["law_grounding_attempted"] = meta.get("law_grounding_attempted")
    result["law_grounding_status"] = meta.get("law_grounding_status")
    result["manual_grounding_status"] = meta.get("manual_grounding_status")
    result["manual_to_law_fallback_used"] = meta.get("manual_to_law_fallback_used")
    result["variant_context_used"] = meta.get("procedure_variant_context_used")

    if status == 503:
        # Safe no-provider mode: live answer check is intentionally skipped.
        result["live_answer_checked"] = False
        result["metadata_present"] = ("law_grounding_status" in meta)
        result["ok"] = (meta.get("error") == "no_llm_provider_configured")
        result["note"] = "no-provider 503 (live answer skipped)"
        return result

    if status == 200:
        answer = str(body.get("answer") or "")
        lowered = answer.lower()
        unsafe = [p for p in UNSAFE_APPROVAL_PHRASES if p.lower() in lowered]
        result["live_answer_checked"] = True
        result["unsafe_approval_language"] = unsafe
        # Metadata/source/law-grounding status should be present on a real answer.
        result["metadata_present"] = ("law_grounding_status" in body) and ("answer" in body)
        result["ok"] = bool(answer) and not unsafe and result["metadata_present"]
        if unsafe:
            result["note"] = "FAILED: unsafe approval/guarantee language detected"
        else:
            result["note"] = "live answer checked"
        return result

    result["note"] = "unexpected status %s" % status
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Provider-aware live AI answer-quality smoke (safe by default)."
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--backend-url", default=None, help="Override BACKEND_URL.")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail if no provider is configured or backend is unreachable.",
    )
    args = parser.parse_args(argv)

    base = args.backend_url or DEFAULT_BACKEND
    report = {
        "backend_url": base,
        "reachable": False,
        "provider_configured": None,
        "provider_flags": None,
        "model": None,
        "groq_fallback_allowed": None,
        "llm_warnings": None,
        "law_grounding_mode": None,
        "live_answer_executed": False,
        "manual_to_law_fallback_executed": False,
        "questions": [],
        "no_provider_safe": None,
        "blocker": None,
    }

    health = _safe_health(base)
    if health is None:
        report["blocker"] = "backend /health not reachable at %s" % base
        _emit(report, args)
        if args.require_live:
            print("\nFAIL: --require-live set but backend is unreachable.", file=sys.stderr)
            return 1
        print(
            "\nSKIPPED: backend unreachable. To run against deployed Railway backend:\n"
            "  BACKEND_URL=\"https://YOUR-RAILWAY-BACKEND.up.railway.app\" "
            "python3 scripts/smoke_ai_live_quality.py"
        )
        return 0

    report["reachable"] = True
    llm = health.get("llm") if isinstance(health.get("llm"), dict) else {}
    # Only non-secret booleans / public model id are read; API keys never are.
    report["provider_configured"] = bool(llm.get("configured"))
    report["provider_flags"] = health.get("providers")
    report["model"] = llm.get("model")
    # Non-secret Groq-fallback posture surfaced by /health (no key material).
    report["groq_fallback_allowed"] = llm.get("groq_fallback_allowed")
    report["llm_warnings"] = llm.get("warnings")
    report["law_grounding_mode"] = health.get("law_grounding_mode")

    results = [_check_question(base, q) for q in SAMPLE_QUESTIONS]
    report["questions"] = results
    report["live_answer_executed"] = any(r["live_answer_checked"] for r in results)
    report["manual_to_law_fallback_executed"] = any(
        bool(r.get("manual_to_law_fallback_used")) for r in results
    )
    report["no_provider_safe"] = all(
        (r["status"] != 503) or r["ok"] for r in results
    )

    _emit(report, args)

    # Determine exit status. By default we do NOT fail on the no-provider path.
    any_unsafe = any(r.get("unsafe_approval_language") for r in results)
    live_failures = [r for r in results if r["live_answer_checked"] and not r["ok"]]
    no_provider_unsafe = any(r["status"] == 503 and not r["ok"] for r in results)

    if any_unsafe or live_failures or no_provider_unsafe:
        print("\nFAIL: see results above.", file=sys.stderr)
        return 1

    if args.require_live and not report["live_answer_executed"]:
        print(
            "\nFAIL: --require-live set but no live answer check executed "
            "(provider not configured?).",
            file=sys.stderr,
        )
        return 1

    return 0


def _emit(report, args):
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print("Provider-aware live AI quality smoke")
    print("  backend URL              : %s" % report["backend_url"])
    print("  reachable                : %s" % report["reachable"])
    if report["blocker"]:
        print("  blocker                  : %s" % report["blocker"])
        return
    print("  provider configured      : %s" % report["provider_configured"])
    print("  provider flags           : %s" % report["provider_flags"])
    print("  model                    : %s" % report["model"])
    print("  groq fallback allowed    : %s" % report["groq_fallback_allowed"])
    print("  llm warnings             : %s" % report["llm_warnings"])
    print("  law grounding mode       : %s" % report["law_grounding_mode"])
    print("  live answer executed     : %s" % report["live_answer_executed"])
    print("  manual->law fallback hit : %s" % report["manual_to_law_fallback_executed"])
    print("  no-provider 503 safe     : %s" % report["no_provider_safe"])
    print("  questions:")
    for r in report["questions"]:
        tag = "OK  " if r["ok"] else ("SKIP" if r["status"] == 503 else "FAIL")
        suffix = ""
        if r["sent_selected_context"]:
            suffix += " [route/variant ctx sent; used=%s]" % r["variant_context_used"]
        suffix += " [manual=%s law=%s m2l=%s]" % (
            r["manual_grounding_status"], r["law_grounding_status"],
            r["manual_to_law_fallback_used"],
        )
        print("    %s  %-22s %s%s" % (tag, r["id"], r["note"], suffix))
    if not report["live_answer_executed"]:
        print(
            "\nNote: live answer checks were skipped (no provider configured here).\n"
            "Railway has provider keys configured — run this against the deployed\n"
            "backend to exercise live answer quality:\n"
            "  BACKEND_URL=\"https://YOUR-RAILWAY-BACKEND.up.railway.app\" "
            "python3 scripts/smoke_ai_live_quality.py"
        )


if __name__ == "__main__":
    raise SystemExit(main())
