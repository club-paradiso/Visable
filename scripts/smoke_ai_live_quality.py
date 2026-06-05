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
  * answer-quality signals (Part K): answer_quality_mode, source_confidence_level,
    question_type_detected, related_statuses_not_sources, and — on a live 200
    answer — whether the direct answer appears in the first two paragraphs,
    whether the official-confirmation checklist surfaced when expected, whether
    mixed-language artifacts appear, whether raw provider/source codes leak into
    the answer text, the answer length bucket, and the warning-repetition count
  * whether the no-provider 503 behavior is safe

Answer-quality signals are WARN-ONLY: this harness never fails CI on live LLM
wording. It only fails on clearly unsafe approval/guarantee language or an
unsafe no-provider 503.

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
    {"id": "h1_study", "visa_code": "H-1", "question": "H-1 비자인데 한국 대학에서 학점 계절학기를 수강할 수 있을까요?", "lang": "ko", "expect_confirmation_checklist": True, "expect_related_statuses": ["D-2", "D-4"]},
    {"id": "g1_5_study_audit", "visa_code": "G-1-5", "question": "G-1-5 난민소송 중 대학 정규 등록이나 청강 수업이 가능한가요?", "lang": "ko", "expect_confirmation_checklist": True},
    {"id": "g1_5_study_multi", "visa_code": "G-1-5", "question": "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?", "lang": "ko", "expect_confirmation_checklist": True},
    {"id": "e7_to_f299_side_job", "question": "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?", "lang": "ko", "expect_confirmation_checklist": True},
    {"id": "h1_foreigner_registration", "visa_code": "H-1", "question": "H-1 외국인등록은 언제 해야 하나요?", "lang": "ko", "expect_confirmation_checklist": True},
    {"id": "h1_to_f299_change", "visa_code": "H-1", "question": "Can I change status to F-2-99?", "lang": "en", "expect_confirmation_checklist": True},
    {"id": "d2_work", "visa_code": "D-2", "question": "D-2 비자로 시간제 아르바이트를 할 수 있나요?", "lang": "ko"},
    {"id": "d10_freelance", "visa_code": "D-10", "question": "D-10 구직비자로 프리랜서 일을 해도 되나요?", "lang": "ko"},
    {"id": "e7_side_job", "visa_code": "E-7", "question": "E-7인데 본업 외 부업을 해도 되나요?", "lang": "ko"},
    {"id": "f4_employment", "visa_code": "F-4", "question": "F-4 재외동포의 취업 제한은 어떻게 확인하나요?", "lang": "ko"},
    {"id": "f4_domestic_residence", "visa_code": "F-4", "question": "F-4 재외동포는 국내거소신고를 해야 하나요?", "lang": "ko"},
    {"id": "c3_paid_work", "visa_code": "C-3", "question": "C-3 단기방문으로 paid work를 할 수 있나요?", "lang": "ko"},
    {"id": "one_day_overstay", "question": "체류기간이 하루 overstay 됐습니다. 어떻게 해야 하나요?", "lang": "ko", "expect_confirmation_checklist": True},
    {"id": "refugee_g1", "visa_code": "G-1", "question": "난민 신청 후 G-1 체류 context에서 연장해야 하나요?", "lang": "ko"},
    {"id": "f6_divorce_extension", "visa_code": "F-6", "question": "F-6인데 이혼 후 체류기간 연장이 가능한가요?", "lang": "ko"},
    {"id": "g1_medical", "visa_code": "G-1", "question": "G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?", "lang": "ko"},
]

# Chinese legal fragments
# Chinese legal fragments that must NOT appear in an English-mode answer.
_CJK_LEGAL_FRAGMENTS = (
    "资格", "資格", "签证", "簽證", "滞留", "滯留", "居留",
    "在留", "许可", "許可", "申请", "申請",
)


def _mixed_language_artifacts(answer, lang):
    """Conservative mixed-language scan (Part I). English mode only flags CJK
    legal fragments; other modes are not failed here (warn-only harness)."""
    if (lang or "").lower() != "en":
        return []
    return [frag for frag in _CJK_LEGAL_FRAGMENTS if frag in (answer or "")]


def _length_bucket(answer):
    n = len((answer or "").split())
    if n <= 60:
        return "short"
    if n <= 200:
        return "medium"
    if n <= 400:
        return "long"
    return "very_long"


def _direct_answer_early(answer):
    """Heuristic: the first two paragraphs should carry the practical answer,
    not a long 'currently known facts' preamble or a heading wall."""
    paras = [p.strip() for p in (answer or "").split("\n\n") if p.strip()]
    if not paras:
        return False
    head = " ".join(paras[:2]).lower()
    # A preamble that opens with a 'known facts' style heading is a red flag.
    bad_openers = ("currently known", "현재 알려진", "known facts", "已知")
    if any(head.startswith(b) for b in bad_openers):
        return False
    # A direct answer paragraph is reasonably short and not just a heading.
    return len(paras[0].split()) <= 120


# Raw status/provider codes that should never be the user-facing answer text.
_RAW_CODE_LEAKS = (
    "source_unavailable", "source_limited", "generic_advisory",
    "SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED",
    "LAW_GROUNDING_DISABLED", "no_llm_provider_configured",
    "manual_grounding_absent", "provider_unavailable",
)

# Over-confident certainty phrases that must be softened when the source state
# is limited/unavailable (Part N). Mirrors
# services.answer_quality.RISKY_CONFIDENCE_PHRASES; inlined so this script stays
# dependency-free. Warn-only — never fails CI on LLM wording.
_RISKY_CONFIDENCE_PHRASES = (
    "may be permissible", "is allowed", "you can", "no need to", "does not require",
    "definitely", "guaranteed", "will be approved", "will be denied",
    "automatically", "always", "never",
    "신고 의무는 없습니다", "반드시 신고해야 합니다", "허용됩니다", "가능합니다",
    "더 이상 적용되지 않습니다",
)


def _risky_phrase_warnings(answer, mode):
    """Risky certainty phrases found in a weak-source-mode answer (warn-only)."""
    if not answer or mode not in ("source_limited", "source_unavailable", "limited", "unavailable"):
        return []
    low = answer.lower()
    return [p for p in _RISKY_CONFIDENCE_PHRASES if p in low]


def _warning_repetition_count(answer):
    """Count how many times the same official-confirmation caution is repeated.
    A modern answer states it once; repeated copies are a readability smell."""
    lowered = (answer or "").lower()
    markers = ["1345", "hikorea", "하이코리아", "immigration office", "출입국"]
    return max((lowered.count(m) for m in markers), default=0)


def _extract_js_function(src, name):
    """Brace-match a top-level ``function NAME(...) { ... }`` body (no deps)."""
    import re

    m = re.search(r"function\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return ""
    try:
        i = src.index("{", m.end())
    except ValueError:
        return ""
    depth = 0
    for j in range(i, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    return ""


def _ai_shell_static_signals():
    """Static signals about the ai.html answer shell (Part G + answer pipeline
    contract).

    These describe the rendered shell (chips/footer) and the answer-rendering
    contract, which the API response cannot show, so we read the local ai.html.
    Returns None if ai.html is not found (e.g. running against a remote backend
    from elsewhere). Warn-only."""
    import re

    here = os.path.dirname(os.path.abspath(__file__))
    ai_html = os.path.join(os.path.dirname(here), "ai.html")
    try:
        with open(ai_html, encoding="utf-8") as fh:
            html = fh.read()
    except OSError:
        return None

    render_fn = _extract_js_function(html, "renderGroundingSourcePanel")
    normalize_fn = _extract_js_function(html, "normalizeAnswerMetadata")

    # The original production bug: renderGroundingSourcePanel referenced a
    # helper-local ``errorType`` it never declared.
    possible_free_variable_errortype = bool(
        render_fn
        and re.search(r"\berrorType\b", render_fn)
        and not re.search(r"const\s+errorType\s*=", render_fn)
    )
    contract_fields = (
        "law_grounding_warnings", "law_lookup_error_type", "parser_status",
        "source_family_statuses", "parser_status_by_family", "law_sources",
        "grounding_sources", "related_statuses_not_sources", "legal_analysis",
        "legal_analysis_exists", "citation_verification",
        "deterministic_fallback_answer_used", "fallback_answer_kind",
        "copy_safe_answer", "answer_certainty_level", "source_panel_state",
    )
    missing_source_panel_metadata_defaults = (
        not normalize_fn
        or "normalizeAnswerMetadata(" not in render_fn
        or any(f not in normalize_fn for f in contract_fields)
    )
    copy_assigns = re.findall(r"COPY_PAYLOADS\[[^\]]+\]\s*=\s*\{[^}]*\}", html)
    copy_safe_answer_diagnostic_leak = any(
        any(tok in a for tok in ("data-diagnostics", "error-details", "developer"))
        for a in copy_assigns
    )
    raw_code_default_ui_leak = any(
        code in html and (code + " could") in html
        for code in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED")
    )
    error_classes_wired = all(
        ("'%s'" % cls) in html for cls in ("network", "backend_http", "provider", "frontend_render")
    )
    details_open_by_default = "<details open" in html.lower()

    answer_rendering_contract_ok = (
        bool(render_fn)
        and not possible_free_variable_errortype
        and not missing_source_panel_metadata_defaults
        and not copy_safe_answer_diagnostic_leak
        and not raw_code_default_ui_leak
        and not details_open_by_default
        and "function classifyAskError(" in html
        and "frontend_render_error" in html
        and error_classes_wired
    )
    frontend_contract_risk = not answer_rendering_contract_ok

    return {
        "related_chips_distinct": ("bdg-related" in html) and ("Related status to verify" in html),
        "related_shown_as_related_not_source": "related_statuses_not_sources" in html,
        "answer_basis_row_present": "answer-basis-row" in html,
        "footer_english_present": "Paradiso provides public law/manual-based reference information" in html,
        "english_footer_leak": "Paradiso provides public law/manual-based reference information" not in html,
        "raw_source_code_in_prose": "SOURCE_UNAVAILABLE could not" in html,
        "raw_internal_codes_in_default_ui": raw_code_default_ui_leak,
        # AI answer pipeline contract & rendering signals.
        "answer_rendering_contract_ok": answer_rendering_contract_ok,
        "frontend_contract_risk": frontend_contract_risk,
        "possible_free_variable_errorType": possible_free_variable_errortype,
        "missing_source_panel_metadata_defaults": missing_source_panel_metadata_defaults,
        "raw_code_default_ui_leak": raw_code_default_ui_leak,
        "copy_safe_answer_diagnostic_leak": copy_safe_answer_diagnostic_leak,
        "error_classes_wired": error_classes_wired,
        "developer_diagnostics_open_by_default": details_open_by_default,
    }

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


# Internal backend field names that must never appear in a user-facing memo
# (Part H). These leaked from legal_analysis.decisive_facts before the fix.
_INTERNAL_SNAKE_LABELS = (
    "current_status/sub_status", "previous_status/approval_conditions",
    "target_status/route", "paid_or_credit_bearing", "duration/employer_or_school",
    "current_sub_status", "proposed_activities", "activity_facts",
)
# English official-confirmation question stems that must not appear inside a
# Korean fallback answer (Part E / Part H).
_ENGLISH_QUESTION_STEMS = (
    "what exact current status", "what is your current sojourn", "is the course credit-bearing",
    "does the school require", "what event starts the deadline", "where and how must the report",
    "what are the activity start date",
)
# Study terms that must NOT show up in a registration/reporting answer (Part H).
_STUDY_TERMS_FOR_REGISTRATION = ("계절학기", "학점", "대학 수업", "수강", "청강", "D-2/D-4", "D-2", "D-4")


def _korean_fallback_snake_case_warnings(answer):
    return [lbl for lbl in _INTERNAL_SNAKE_LABELS if lbl in (answer or "")]


def _korean_fallback_english_question_warnings(answer):
    low = (answer or "").lower()
    return [stem for stem in _ENGLISH_QUESTION_STEMS if stem in low]


def _registration_answer_study_leak(answer, question):
    q = question or ""
    if not any(t in q for t in ("외국인등록", "거소신고", "신고")):
        return []
    if any(t in q for t in ("수강", "청강", "계절학기", "학점", "대학", "수업")):
        return []  # the question itself is about study — not a leak
    return [t for t in _STUDY_TERMS_FOR_REGISTRATION if t in (answer or "")]


def _family_statuses_collapse_warnings(result):
    """Part H: detect the dominant-LAW_API_BAD_RESPONSE / mislabeled-parser bug."""
    warnings = []
    fam = result.get("source_family_statuses")
    parser_by_family = result.get("parser_status_by_family") or {}
    if isinstance(fam, dict) and fam:
        values = {str(v).lower() for v in fam.values() if v}
        # All families collapsed to bad_response is the symptom we fixed.
        if values and values <= {"bad_response"}:
            warnings.append("all source family statuses collapse to bad_response")
        # no_results / unsupported are normal; the panel must NOT call them a
        # parser failure.
        normal = {"no_results", "unsupported", "not_configured", "no_results_or_unsupported"}
        only_normal = bool(values) and values <= normal
        parser_vals = {str(v).lower() for v in parser_by_family.values() if v}
        top_parser = str(result.get("parser_status") or "").lower()
        parser_actually_failed = bool(
            ({"parse_error", "bad_response"} & parser_vals)
            or top_parser in {"parse_error", "bad_response"}
            or str(result.get("law_lookup_error_type") or "").upper() in {"LAW_API_PARSE_ERROR", "LAW_API_BAD_RESPONSE"}
        )
        if only_normal and parser_actually_failed:
            warnings.append("source panel labels parser failure while families are only no_results/unsupported")
    # no_results misclassified as bad_response at the top-level error type.
    if str(result.get("law_error_type") or "").upper() == "LAW_API_BAD_RESPONSE" and str(result.get("response_shape_hint") or "").lower() in {"empty", "json_object", "json_list", "xml"}:
        warnings.append("no_results-shaped response classified as LAW_API_BAD_RESPONSE")
    return warnings


def _contains_unrelated_h1_study_template(answer, question):
    combined = (answer or "")
    q = question or ""
    h1_leak = "H-1" in combined and "H-1" not in q
    study_leak = any(term in combined for term in ("H-1의 허용 활동범위", "credit-bearing university summer course", "계절학기", "학점 인정", "D-2/D-4")) and not any(term in q for term in ("H-1", "계절학기", "학점", "summer", "course", "등록", "청강"))
    return bool(h1_leak or study_leak)


def _check_question(base, q):
    """POST one sample question and classify the outcome safely."""
    payload = {
        "question": q["question"],
        "consent": True,
        "lang": q.get("lang", "ko"),
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
        "attempted_models": None,
        "final_model": None,
        "provider_error_type": None,
        "model_fallback_used": None,
        "provider_family_fallback_used": None,
        "skipped_models_due_to_cooldown": None,
        "cooling_down_models": None,
        "ollama_fallback_enabled": None,
        "ollama_fallback_used": None,
        "deterministic_fallback_answer_used": None,
        "fallback_answer_kind": None,
        "legal_analysis_exists": None,
        "answer_contains_unrelated_h1_study_template": None,
        "visa_code_detected": None,
        "llm_provider": None,
        "unsafe_approval_language": None,
        "metadata_present": None,
        # Answer-quality signals (Part K).
        "answer_quality_mode": None,
        "source_confidence_level": None,
        "requires_official_confirmation": None,
        "related_statuses_not_sources": None,
        "grounded_answer_limited": None,
        "answer_style_version": None,
        "question_type_detected": None,
        # Law evidence tool-layer signals (Part I).
        "planned_law_queries": None,
        "law_evidence_count": None,
        "law_error_type": None,
        "parser_status": None,
        "response_shape_hint": None,
        "citation_verification_status": None,
        "source_panel_status": None,
        "source_panel_state": None,
        "source_panel_confidence": None,
        "direct_authority_available": None,
        "direct_citation_available": None,
        "legal_analysis_available": None,
        "law_lookup_failed": None,
        "answer_certainty_level": None,
        "source_panel_default_label": None,
        "source_panel_default_raw_code_leak": None,
        "default_source_panel_trust_warning": None,
        "raw_code_copy_leak": None,
        "overconfident_phrase_warning": None,
        "technical_details_collapsed": None,
        "law_lookup_error_type": None,
        "legal_analysis": None,
        "immigration_facts": None,
        "legal_issue_types": None,
        "proposed_activity_type": None,
        "source_plan": None,
        "analysis_mode": None,
        "risk_posture": None,
        "confidence": None,
        "decisive_facts": None,
        "official_confirmation_questions": None,
        "first_sentence_quality_warning": None,
        "raw_code_default_ui_leak": None,
        "direct_evidence_count": None,
        "related_evidence_count": None,
        "analogical_evidence_count": None,
        "missing_direct_authority": None,
        "source_types_attempted": None,
        "ontology_detected": None,
        "evidence_query_plan": None,
        "evidence_goal_by_query": None,
        "source_families_planned": None,
        "source_family_support": None,
        "direct_official_evidence_available": None,
        "contextual_official_evidence_available": None,
        "analogical_evidence_available": None,
        "background_evidence_available": None,
        "raw_internal_codes_in_default_ui": None,
        "h1_first_line_warning": None,
        "risky_phrase_warnings": None,
        "direct_answer_early": None,
        "confirmation_checklist_present": None,
        "mixed_language_artifacts": None,
        "raw_code_leak": None,
        "answer_length_bucket": None,
        "warning_repetition_count": None,
        "quality_warnings": [],
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
    # OpenRouter candidate-fallback transparency (non-secret).
    result["attempted_models"] = meta.get("attempted_models")
    result["final_model"] = meta.get("final_model")
    result["provider_error_type"] = meta.get("provider_error_type")
    result["model_fallback_used"] = meta.get("model_fallback_used")
    result["provider_family_fallback_used"] = meta.get("provider_family_fallback_used")
    result["skipped_models_due_to_cooldown"] = meta.get("skipped_models_due_to_cooldown")
    result["cooling_down_models"] = meta.get("cooling_down_models")
    result["ollama_fallback_enabled"] = meta.get("ollama_fallback_enabled")
    result["ollama_fallback_used"] = meta.get("ollama_fallback_used")
    result["deterministic_fallback_answer_used"] = meta.get("deterministic_fallback_answer_used")
    result["fallback_answer_kind"] = meta.get("fallback_answer_kind")
    result["legal_analysis_exists"] = meta.get("legal_analysis_exists") if meta.get("legal_analysis_exists") is not None else bool(meta.get("legal_analysis"))
    result["visa_code_detected"] = meta.get("visa_code_detected")
    result["llm_provider"] = meta.get("llm_provider")
    # Answer-quality contract metadata (non-secret) — available on both the
    # 503 no-provider path and the live 200 path.
    result["answer_quality_mode"] = meta.get("answer_quality_mode")
    result["source_confidence_level"] = meta.get("source_confidence_level")
    result["requires_official_confirmation"] = meta.get("requires_official_confirmation")
    result["related_statuses_not_sources"] = meta.get("related_statuses_not_sources")
    result["grounded_answer_limited"] = meta.get("grounded_answer_limited")
    result["answer_style_version"] = meta.get("answer_style_version")
    result["question_type_detected"] = meta.get("question_type_detected")
    # Law evidence tool-layer signals (Part I) — sanitized, no secrets.
    result["planned_law_queries"] = meta.get("planned_law_queries")
    result["law_evidence_count"] = meta.get("law_evidence_count")
    result["law_error_type"] = meta.get("law_grounding_error")
    result["parser_status"] = meta.get("parser_status")
    result["response_shape_hint"] = meta.get("response_shape_hint")
    result["source_families_planned"] = meta.get("source_families_planned")
    result["source_families_attempted"] = meta.get("source_families_attempted")
    result["source_family_statuses"] = meta.get("source_family_statuses")
    result["source_family_result_counts"] = meta.get("source_family_result_counts")
    result["response_shape_hint_by_family"] = meta.get("response_shape_hint_by_family")
    result["parser_status_by_family"] = meta.get("parser_status_by_family")
    result["law_error_type_by_family"] = meta.get("law_error_type_by_family")
    result["normalized_evidence_count"] = meta.get("normalized_evidence_count") or meta.get("law_evidence_count")
    result["sanitized_source_urls"] = meta.get("sanitized_source_urls")
    cv = meta.get("citation_verification") if isinstance(meta.get("citation_verification"), dict) else {}
    result["citation_verification_status"] = cv.get("status")
    result["source_panel_status"] = meta.get("source_panel_status") or cv.get("status")
    result["source_panel_state"] = meta.get("source_panel_state")
    result["source_panel_confidence"] = meta.get("source_panel_confidence")
    result["direct_authority_available"] = meta.get("direct_authority_available")
    result["direct_citation_available"] = meta.get("direct_citation_available")
    result["legal_analysis_available"] = meta.get("legal_analysis_available")
    result["law_lookup_failed"] = meta.get("law_lookup_failed")
    result["answer_certainty_level"] = meta.get("answer_certainty_level")
    result["law_lookup_error_type"] = meta.get("law_lookup_error_type") or meta.get("law_grounding_error")
    label_key = meta.get("source_panel_label_key")
    label_map = {
        "structured_fallback": "Structured legal analysis note",
        "structured_legal_analysis_law_lookup_issue": "Structured legal analysis used",
        "related_legal_context": "Related legal context analysis",
        "source_unavailable": "Source unavailable",
        "live_law_lookup_technical_issue": "Source lookup technical issue",
    }
    result["source_panel_default_label"] = label_map.get(label_key) or label_key or result.get("source_panel_state")
    raw_codes = ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE")
    result["source_panel_default_raw_code_leak"] = any(code in str(result["source_panel_default_label"] or "") for code in raw_codes)
    result["technical_details_collapsed"] = True
    result["legal_analysis"] = meta.get("legal_analysis")
    result["immigration_facts"] = meta.get("immigration_facts") or ((meta.get("legal_analysis") or {}).get("immigration_facts") if isinstance(meta.get("legal_analysis"), dict) else None)
    result["legal_issue_types"] = meta.get("legal_issue_types") or ((meta.get("legal_analysis") or {}).get("legal_issue_types") if isinstance(meta.get("legal_analysis"), dict) else None)
    result["proposed_activity_type"] = meta.get("proposed_activity_type") or ((result.get("immigration_facts") or {}).get("proposed_activities") if isinstance(result.get("immigration_facts"), dict) else None)
    result["source_plan"] = meta.get("source_plan") or ((meta.get("legal_analysis") or {}).get("source_plan") if isinstance(meta.get("legal_analysis"), dict) else None)
    result["analysis_mode"] = meta.get("analysis_mode") or ((meta.get("legal_analysis") or {}).get("analysis_mode") if isinstance(meta.get("legal_analysis"), dict) else None)
    result["risk_posture"] = (meta.get("legal_analysis") or {}).get("risk_posture") if isinstance(meta.get("legal_analysis"), dict) else None
    result["confidence"] = (meta.get("legal_analysis") or {}).get("confidence") if isinstance(meta.get("legal_analysis"), dict) else None
    result["decisive_facts"] = (meta.get("legal_analysis") or {}).get("decisive_facts") if isinstance(meta.get("legal_analysis"), dict) else None
    result["official_confirmation_questions"] = (meta.get("legal_analysis") or {}).get("official_confirmation_questions") or meta.get("official_confirmation_questions")
    result["direct_evidence_count"] = meta.get("direct_evidence_count")
    result["related_evidence_count"] = meta.get("related_evidence_count")
    result["analogical_evidence_count"] = meta.get("analogical_evidence_count")
    result["missing_direct_authority"] = meta.get("missing_direct_authority")
    result["source_types_attempted"] = meta.get("source_types_attempted")

    # Generalized official-evidence ontology + query-plan signals (Part H).
    ontology = meta.get("evidence_ontology") or {}
    query_plan = meta.get("evidence_query_plan") or []
    facts = result.get("immigration_facts") or {}
    issues = list(result.get("legal_issue_types") or [])
    result["ontology_detected"] = bool(ontology)
    result["evidence_query_plan"] = query_plan
    result["evidence_goal_by_query"] = meta.get("evidence_goal_by_query") or [
        q.get("evidence_goal") for q in query_plan
    ]
    result["source_families_planned"] = (
        ontology.get("source_families_planned") or result.get("source_families_planned")
    )
    result["source_family_support"] = meta.get("source_family_support") or {}
    result["direct_official_evidence_available"] = bool(result.get("direct_evidence_count"))
    result["contextual_official_evidence_available"] = bool(result.get("related_evidence_count"))
    result["analogical_evidence_available"] = bool(result.get("analogical_evidence_count"))
    result["background_evidence_available"] = bool(meta.get("background_evidence_count"))

    # WARN: planner emitted no query although a legal issue was detected.
    substantive_issues = [
        i for i in issues if i not in ("legal_general", "non_immigration_adjacent_issue")
    ]
    if substantive_issues and not query_plan:
        result["quality_warnings"].append(
            "evidence planner emitted no query for legal issues: %s" % substantive_issues
        )
    # WARN: direct evidence exists but answer certainty stayed unavailable.
    if result.get("direct_evidence_count") and result.get("answer_certainty_level") in (
        "unavailable", "source_unavailable",
    ):
        result["quality_warnings"].append(
            "direct evidence exists but answer_certainty_level is unavailable"
        )
    # WARN: previous-status evidence planned as direct for a current-status issue.
    if facts.get("status_transition_detected"):
        for q in query_plan:
            if q.get("status_role") == "previous_status" and q.get("evidence_goal") == "direct":
                result["quality_warnings"].append(
                    "previous-status query planned as direct authority after a status transition"
                )
                break
    # WARN: target status lost in a status-change question.
    target = facts.get("target_status")
    if "status_change" in issues and target:
        target_in_plan = any(
            target in (q.get("expected_status_codes") or []) for q in query_plan
        )
        if not target_in_plan:
            result["quality_warnings"].append(
                "target status %s lost in status-change query plan" % target
            )
    # WARN: a registration/reporting question drifted into study enrollment.
    activities = list(result.get("proposed_activity_type") or [])
    if "registration_or_residence_report" in issues and (
        "study_on_non_study_status" in issues or "formal_enrollment" in activities
    ):
        result["quality_warnings"].append(
            "registration/reporting question classified as study enrollment"
        )
    # WARN: an unsupported/unwired source family is labeled a parser bad_response.
    fam_support = result["source_family_support"]
    fam_statuses = result.get("source_family_statuses") or {}
    for fam, support in fam_support.items():
        if support == "planned_not_wired" and str(fam_statuses.get(fam, "")).lower() in (
            "bad_response", "parse_error",
        ):
            result["quality_warnings"].append(
                "unsupported source family %s labeled bad_response" % fam
            )

    if result.get("source_panel_default_raw_code_leak"):
        result["quality_warnings"].append("raw law diagnostic code appears in default source panel label")
    if result.get("legal_analysis_exists") and result.get("source_panel_state") == "source_unavailable":
        result["default_source_panel_trust_warning"] = "legal_analysis_exists=true but source_panel_state=source_unavailable"
        result["quality_warnings"].append(result["default_source_panel_trust_warning"])
    if result.get("law_lookup_error_type") == "LAW_API_BAD_RESPONSE" and result.get("source_panel_default_raw_code_leak"):
        result["quality_warnings"].append("LAW_API_BAD_RESPONSE appears as default source label")
    if result.get("deterministic_fallback_answer_used") and result.get("source_panel_state") not in ("structured_fallback_available", "direct_source_verified"):
        result["quality_warnings"].append("deterministic fallback source_panel_state is not structured_fallback_available or equivalent")

    if status == 503:
        # Safe no-provider mode: live answer check is intentionally skipped.
        result["live_answer_checked"] = False
        result["metadata_present"] = ("law_grounding_status" in meta) and ("answer_quality_mode" in meta)
        # The contract metadata must still be present and self-consistent.
        expect_related = q.get("expect_related_statuses")
        if expect_related is not None and result["related_statuses_not_sources"] != expect_related:
            result["quality_warnings"].append(
                "related_statuses mismatch: got %s expected %s"
                % (result["related_statuses_not_sources"], expect_related)
            )
        result["ok"] = (meta.get("error") == "no_llm_provider_configured") and result["metadata_present"]
        result["note"] = "no-provider 503 (live answer skipped; contract metadata checked)"
        return result

    if status == 200:
        answer = str(body.get("answer") or "")
        lowered = answer.lower()
        lang = q.get("lang", "ko")
        unsafe = [p for p in UNSAFE_APPROVAL_PHRASES if p.lower() in lowered]
        result["live_answer_checked"] = True
        result["unsafe_approval_language"] = unsafe
        # Answer-quality signals on the live answer text (warn-only — never fail
        # CI on LLM wording, per Part K).
        result["direct_answer_early"] = _direct_answer_early(answer)
        result["mixed_language_artifacts"] = _mixed_language_artifacts(answer, lang)
        result["raw_code_leak"] = [c for c in _RAW_CODE_LEAKS if c in answer]
        result["answer_length_bucket"] = _length_bucket(answer)
        result["warning_repetition_count"] = _warning_repetition_count(answer)
        # Over-confident wording in a weak source mode (Part N) — warn-only.
        result["risky_phrase_warnings"] = _risky_phrase_warnings(
            answer, result.get("answer_quality_mode")
        )
        first_line = next((line.strip() for line in answer.splitlines() if line.strip()), "")
        bad_starts = ("paradiso cannot verify", "whether you can", "it depends", "specific manual guidance was not found")
        for bad in bad_starts:
            if first_line.lower().startswith(bad):
                result["h1_first_line_warning"] = "answer starts with %s" % bad
                result["first_sentence_quality_warning"] = result["h1_first_line_warning"]
                result["quality_warnings"].append(result["h1_first_line_warning"])
                break
        if result.get("question_type_detected") in ("activity_on_status", "status_change", "deadline_report", "documents_needed") and not result.get("legal_analysis"):
            result["quality_warnings"].append("no legal_analysis object for legal/procedure question")
        if (result.get("related_evidence_count") or 0) and result.get("analysis_mode") == "direct_authority" and not (result.get("direct_evidence_count") or 0):
            result["quality_warnings"].append("related evidence mislabeled as direct authority")
        if result.get("answer_quality_mode") in ("source_limited", "source_unavailable") and "may be permissible" in lowered:
            result["quality_warnings"].append("unsupported may be permissible in source-limited answer")
        result["overconfident_phrase_warning"] = bool(result["risky_phrase_warnings"] and (result.get("answer_certainty_level") in ("limited", "unavailable") or result.get("answer_quality_mode") in ("source_limited", "source_unavailable")))
        if result["risky_phrase_warnings"]:
            result["quality_warnings"].append(
                "overconfident_phrase_warning: %s" % result["risky_phrase_warnings"]
            )
        copy_text = str(body.get("copy_safe_answer") or body.get("fallback_answer") or "")
        result["raw_code_copy_leak"] = [c for c in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED") if c in copy_text]
        if result["raw_code_copy_leak"]:
            result["quality_warnings"].append("raw_code_copy_leak: %s" % result["raw_code_copy_leak"])
        checklist_qs = meta.get("official_confirmation_questions") or []
        if q.get("expect_confirmation_checklist") and not checklist_qs:
            result["quality_warnings"].append("official confirmation section lacks concrete questions")
        if q.get("expect_confirmation_checklist"):
            # The deterministic checklist questions should be reflected in the
            # answer when the contract requested them.
            present = bool(checklist_qs) and any(
                str(cq).split("?")[0][:18].lower() in lowered for cq in checklist_qs
            )
            result["confirmation_checklist_present"] = present
            if not present:
                result["quality_warnings"].append("expected official-confirmation checklist not surfaced")
        result["raw_code_default_ui_leak"] = bool(result.get("raw_code_leak"))
        result["answer_contains_unrelated_h1_study_template"] = _contains_unrelated_h1_study_template(answer, q.get("question"))
        if result["answer_contains_unrelated_h1_study_template"]:
            result["quality_warnings"].append("unrelated H-1 study template detected")
        # Part H — fallback localization + diagnostics taxonomy warnings.
        is_ko_answer = str(q.get("lang", "")).lower().startswith("ko")
        if is_ko_answer:
            snake = _korean_fallback_snake_case_warnings(answer)
            if snake:
                result["quality_warnings"].append("internal snake_case labels in Korean fallback: %s" % snake)
            eng_qs = _korean_fallback_english_question_warnings(answer)
            if eng_qs:
                result["quality_warnings"].append("English official questions in Korean fallback: %s" % eng_qs)
        reg_leak = _registration_answer_study_leak(answer, q.get("question"))
        if reg_leak:
            result["quality_warnings"].append("registration/reporting answer leaks study terms: %s" % reg_leak)
        for w in _family_statuses_collapse_warnings(result):
            result["quality_warnings"].append(w)
        if result.get("first_sentence_quality_warning") is None:
            result["first_sentence_quality_warning"] = ""
        for w in ("mixed_language_artifacts", "raw_code_leak"):
            if result[w]:
                result["quality_warnings"].append("%s: %s" % (w, result[w]))
        if result["direct_answer_early"] is False:
            result["quality_warnings"].append("direct answer not in first 2 paragraphs")
        if (result["warning_repetition_count"] or 0) >= 5:
            result["quality_warnings"].append(
                "warning repetition high (%s)" % result["warning_repetition_count"]
            )
        # Metadata/source/law-grounding status should be present on a real answer.
        result["metadata_present"] = ("law_grounding_status" in body) and ("answer" in body) and ("answer_quality_mode" in body)
        # Warn rather than fail when all live candidates are unavailable but the
        # deterministic fallback answer exists; fail if provider failure has no
        # fallback answer.
        has_fallback = bool(meta.get("fallback_answer") or meta.get("copy_safe_answer"))
        if meta.get("deterministic_fallback_answer_used") and has_fallback:
            result["quality_warnings"].append("online candidates unavailable; deterministic fallback answer rendered")
        if meta.get("provider_unavailable") and not has_fallback:
            result["quality_warnings"].append("provider failure produced no fallback answer")
            result["ok"] = False
        else:
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
    parser.add_argument("--ollama-smoke", action="store_true", help="Report Ollama fallback fields when backend enables them; does not require Ollama.")
    parser.add_argument("--mock-provider-failure", action="store_true", help="Reserved for local harnesses that mock provider failure; no-op for remote smoke.")
    parser.add_argument("--force-openrouter-failure", action="store_true", help="Reserved for local harnesses that force OpenRouter failure; no-op for remote smoke.")
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
        "primary_model": None,
        "model_candidates": None,
        "candidate_warnings": None,
        "cooling_down_models": None,
        "model_cooldown_seconds": None,
        "cooldown_enabled": None,
        "provider_family_fallback_allowed": None,
        "ollama_fallback_enabled": None,
        "ollama_model": None,
        "ollama_configured": None,
        "ollama_timeout_seconds": None,
        "groq_fallback_allowed": None,
        "llm_warnings": None,
        "law_grounding_mode": None,
        # Non-secret Open Law API posture (booleans only, never the OC/key value).
        "law_api_oc_configured": None,
        "law_api_key_fallback_configured": None,
        "live_answer_executed": False,
        "manual_to_law_fallback_executed": False,
        "model_fallback_executed": False,
        "questions": [],
        "no_provider_safe": None,
        "ai_shell": _ai_shell_static_signals(),
        "blocker": None,
    }

    health = _safe_health(base)
    if health is None:
        report["blocker"] = "backend /health not reachable at %s" % base
        _emit(report, args)
        if args.require_live:
            print("\nFAIL: --require-live set but backend is unreachable.", file=sys.stderr)
            return 1
        # The ai.html answer-rendering contract is a STATIC check, so surface it
        # even when the backend is unreachable (it does not need a live backend).
        sh = report.get("ai_shell")
        if sh is not None:
            print("\n  ai answer pipeline contract (static, ai.html):")
            print("    answer rendering ok    : %s" % sh.get("answer_rendering_contract_ok"))
            print("    frontend contract risk : %s" % sh.get("frontend_contract_risk"))
            print("    free-var errorType risk: %s" % sh.get("possible_free_variable_errorType"))
            print("    missing metadata defs  : %s" % sh.get("missing_source_panel_metadata_defaults"))
            print("    raw_code default leak  : %s" % sh.get("raw_code_default_ui_leak"))
            print("    copy_safe diag leak    : %s" % sh.get("copy_safe_answer_diagnostic_leak"))
            print("    error classes wired    : %s" % sh.get("error_classes_wired"))
        print(
            "\nSKIPPED: backend unreachable (live answer checks). The static ai.html\n"
            "answer-rendering contract above does not require a live backend.\n"
            "To run live checks against the deployed Railway backend:\n"
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
    # Non-secret OpenRouter candidate-fallback posture (public model ids only).
    report["primary_model"] = llm.get("primary_model")
    report["model_candidates"] = llm.get("model_candidates")
    report["candidate_warnings"] = llm.get("candidate_warnings")
    report["cooling_down_models"] = llm.get("cooling_down_models")
    report["model_cooldown_seconds"] = llm.get("model_cooldown_seconds")
    report["cooldown_enabled"] = llm.get("cooldown_enabled")
    report["provider_family_fallback_allowed"] = llm.get("provider_family_fallback_allowed")
    report["ollama_fallback_enabled"] = llm.get("ollama_fallback_enabled")
    report["ollama_model"] = llm.get("ollama_model")
    report["ollama_configured"] = llm.get("ollama_configured")
    report["ollama_timeout_seconds"] = llm.get("ollama_timeout_seconds")
    # Non-secret Groq-fallback posture surfaced by /health (no key material).
    report["groq_fallback_allowed"] = llm.get("groq_fallback_allowed")
    report["llm_warnings"] = llm.get("warnings")
    report["law_grounding_mode"] = health.get("law_grounding_mode")
    # Non-secret Open Law API flags from /health (booleans only; no OC/key value).
    law_api = health.get("law_api") if isinstance(health.get("law_api"), dict) else {}
    report["law_api_oc_configured"] = law_api.get("law_api_oc_configured")
    report["law_api_key_fallback_configured"] = law_api.get("law_api_key_fallback_configured")

    results = [_check_question(base, q) for q in SAMPLE_QUESTIONS]
    report["questions"] = results
    report["live_answer_executed"] = any(r["live_answer_checked"] for r in results)
    report["model_fallback_executed"] = any(
        bool(r.get("model_fallback_used")) for r in results
    )
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
    print("  primary model            : %s" % report["primary_model"])
    print("  model candidates         : %s" % report["model_candidates"])
    print("  candidate warnings       : %s" % report["candidate_warnings"])
    print("  cooling down models      : %s" % report["cooling_down_models"])
    print("  cooldown enabled/seconds : %s / %s" % (report["cooldown_enabled"], report["model_cooldown_seconds"]))
    print("  provider-family fallback : %s" % report["provider_family_fallback_allowed"])
    print("  Ollama enabled/configured: %s / %s" % (report["ollama_fallback_enabled"], report["ollama_configured"]))
    print("  Ollama model/timeout     : %s / %s" % (report["ollama_model"], report["ollama_timeout_seconds"]))
    print("  groq fallback allowed    : %s" % report["groq_fallback_allowed"])
    print("  llm warnings             : %s" % report["llm_warnings"])
    print("  law grounding mode       : %s" % report["law_grounding_mode"])
    print("  law_api oc configured    : %s" % report["law_api_oc_configured"])
    print("  law_api key fallback     : %s" % report["law_api_key_fallback_configured"])
    print("  live answer executed     : %s" % report["live_answer_executed"])
    print("  model fallback hit       : %s" % report["model_fallback_executed"])
    print("  manual->law fallback hit : %s" % report["manual_to_law_fallback_executed"])
    print("  no-provider 503 safe     : %s" % report["no_provider_safe"])
    if report.get("ai_shell") is not None:
        sh = report["ai_shell"]
        print("  ai shell (static, ai.html):")
        print("    related chips distinct : %s" % sh["related_chips_distinct"])
        print("    answer-basis row       : %s" % sh["answer_basis_row_present"])
        print("    english footer present : %s" % sh["footer_english_present"])
        print("    english footer leak    : %s" % sh["english_footer_leak"])
        print("    raw source code in UI  : %s" % sh["raw_source_code_in_prose"])
        print("    raw internal code leak : %s" % sh.get("raw_internal_codes_in_default_ui"))
        print("  ai answer pipeline contract (static, ai.html):")
        print("    answer rendering ok    : %s" % sh.get("answer_rendering_contract_ok"))
        print("    frontend contract risk : %s" % sh.get("frontend_contract_risk"))
        print("    free-var errorType risk: %s" % sh.get("possible_free_variable_errorType"))
        print("    missing metadata defs  : %s" % sh.get("missing_source_panel_metadata_defaults"))
        print("    raw_code default leak  : %s" % sh.get("raw_code_default_ui_leak"))
        print("    copy_safe diag leak    : %s" % sh.get("copy_safe_answer_diagnostic_leak"))
        print("    error classes wired    : %s" % sh.get("error_classes_wired"))
        print("    diagnostics open default: %s" % sh.get("developer_diagnostics_open_by_default"))
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
        suffix += " [provider=%s final_model=%s err=%s model_fallback=%s family_fallback=%s]" % (
            r["llm_provider"], r["final_model"], r["provider_error_type"],
            r["model_fallback_used"], r["provider_family_fallback_used"],
        )
        suffix += " [cooldown skipped=%s cooling=%s ollama_enabled=%s ollama_used=%s deterministic_fallback=%s kind=%s legal_analysis_exists=%s visa=%s unrelated_h1_study_template=%s]" % (
            r["skipped_models_due_to_cooldown"], r["cooling_down_models"],
            r["ollama_fallback_enabled"], r["ollama_fallback_used"],
            r["deterministic_fallback_answer_used"], r.get("fallback_answer_kind"),
            r.get("legal_analysis_exists"), r["visa_code_detected"],
            r.get("answer_contains_unrelated_h1_study_template"),
        )
        # Answer-quality signals (Part K).
        suffix += " [quality=%s conf=%s certainty=%s panel_conf=%s direct_auth=%s direct_cite=%s legal_analysis=%s law_failed=%s qtype=%s related=%s]" % (
            r["answer_quality_mode"], r["source_confidence_level"], r.get("answer_certainty_level"),
            r.get("source_panel_confidence"), r.get("direct_authority_available"), r.get("direct_citation_available"),
            r.get("legal_analysis_available"), r.get("law_lookup_failed"),
            r["question_type_detected"], r["related_statuses_not_sources"],
        )
        # Law evidence tool-layer signals (Part I).
        suffix += " [facts=%s issues=%s activities=%s source_plan=%s mode=%s risk=%s conf=%s decisive=%s confirm_qs=%s first_warn=%s raw_ui_leak=%s]" % (
            bool(r.get("immigration_facts")), r.get("legal_issue_types"), r.get("proposed_activity_type"),
            bool(r.get("source_plan")), r.get("analysis_mode"), r.get("risk_posture"), r.get("confidence"),
            r.get("decisive_facts"), r.get("official_confirmation_questions"), r.get("first_sentence_quality_warning"),
            r.get("raw_code_default_ui_leak"),
        )
        suffix += " [law_planned=%s law_evidence=%s law_error=%s parser=%s shape=%s citation=%s panel=%s state=%s label=%s raw_panel_leak=%s details_collapsed=%s law_lookup_error=%s risky=%s]" % (
            len(r["planned_law_queries"]) if r["planned_law_queries"] else 0,
            r["law_evidence_count"], r["law_error_type"], r["parser_status"],
            r["response_shape_hint"], r["citation_verification_status"],
            r["source_panel_status"], r.get("source_panel_state"), r.get("source_panel_default_label"),
            r.get("source_panel_default_raw_code_leak"), r.get("technical_details_collapsed"),
            r.get("law_lookup_error_type"), r["risky_phrase_warnings"],
        )
        suffix += " [overconfident=%s trust_warn=%s raw_ui=%s raw_copy=%s]" % (
            r.get("overconfident_phrase_warning"), r.get("default_source_panel_trust_warning"),
            r.get("raw_code_default_ui_leak"), r.get("raw_code_copy_leak"),
        )
        # Generalized official-evidence ontology / query-plan signals (Part H).
        suffix += " [ontology=%s families_planned=%s n_queries=%s goals=%s direct_ev=%s contextual_ev=%s analogical_ev=%s background_ev=%s certainty=%s panel_state=%s]" % (
            r.get("ontology_detected"), r.get("source_families_planned"),
            len(r.get("evidence_query_plan") or []), r.get("evidence_goal_by_query"),
            r.get("direct_official_evidence_available"), r.get("contextual_official_evidence_available"),
            r.get("analogical_evidence_available"), r.get("background_evidence_available"),
            r.get("answer_certainty_level"), r.get("source_panel_state"),
        )
        if r["live_answer_checked"]:
            suffix += " [direct_early=%s len=%s warn_reps=%s checklist=%s mixed=%s leak=%s]" % (
                r["direct_answer_early"], r["answer_length_bucket"],
                r["warning_repetition_count"], r["confirmation_checklist_present"],
                r["mixed_language_artifacts"], r["raw_code_leak"],
            )
        print("    %s  %-22s %s%s" % (tag, r["id"], r["note"], suffix))
        for w in (r.get("quality_warnings") or []):
            print("           WARN: %s" % w)
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
