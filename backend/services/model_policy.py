"""Paradiso model role policy.

This module keeps model routing policy explicit and testable:

- Gemma is the default low-risk router / translation model.
- Hermes 3 (Llama 3.1 405B) is the Basic final-answer model, with Gemma 4 as the
  Basic fallback.
- gpt-oss is the verifier / structured audit model.
- China-origin model families are reserved for Chinese-language tasks only by policy.

The module never reads or exposes provider secrets. It only resolves public model
catalog identifiers from environment variables.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Sequence

MODEL_POLICY_VERSION = "2026-07-fast-complexity-escalation-v1"

DEFAULT_ROUTER_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_TRANSLATION_MODEL = "google/gemma-4-31b-it:free"

# Basic answer tier (final answers): Hermes 3 405B primary with a 4-deep
# fallback chain across multiple providers (NousResearch, Google, Meta).
# A 4-candidate chain prevents the "all online model candidates failed" fallback
# banner when 1–2 models are simultaneously rate-limited or their upstream is
# temporarily down — a common occurrence on OpenRouter's free tier.
DEFAULT_FINAL_ANSWER_MODEL = "nousresearch/hermes-3-llama-3.1-405b:free"
DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES: List[str] = [
    "nousresearch/hermes-3-llama-3.1-405b:free",  # Basic primary (Hermes 3 405B)
    "google/gemma-4-26b-a4b-it:free",             # Fallback 1 — Gemma 4 MoE (~3.8B active)
    "meta-llama/llama-3.3-70b-instruct:free",     # Fallback 2 — Llama 3.3 70B (diverse provider)
    "meta-llama/llama-4-scout:free",              # Fallback 3 — Llama 4 Scout 17B MoE
]

# ---------------------------------------------------------------------------
# Answer-speed tiers ("Waymaker" answer modes)
# ---------------------------------------------------------------------------
# The frontend exposes a Fast / Basic / Pro selector. Each tier maps to a
# distinct OpenRouter candidate chain so users can trade depth for latency:
#
#   * fast  — a small, low-latency model first (snappy answers; less depth).
#   * basic — the default Hermes 3 final-answer chain (current behavior).
#   * pro   — reserved / "coming soon"; not yet wired to a model chain.
#
# Random routing stays forbidden; every tier is an explicit, auditable chain.
ANSWER_MODES = ("fast", "basic", "pro")
DEFAULT_ANSWER_MODE = "basic"

# Fast is a latency promise for genuinely small questions, not a request to
# answer a source-heavy or multi-factor immigration problem with a weaker
# model.  These issue families are deterministic signals that the Basic chain
# is the safer minimum.  The list intentionally uses issue *types* produced by
# legal_analysis rather than visa-code exceptions.
_BASIC_MINIMUM_ISSUES = frozenset({
    "denial_revocation_or_remedy",
    "constitutional_or_fundamental_rights",
    "discretionary_or_ambiguous_interpretation",
    "overstay_or_risk",
    "nationality_or_refugee_context",
    "workplace_change_addition",
    "status_change",
    "outside_status_activity",
    "work_on_non_work_status",
    "employment_restriction",
    "approval_condition",
    "post_status_change_residual_duty",
})

_SOURCE_HEAVY_RE = re.compile(
    r"판례|재결례|행정심판|행정소송|불허|취소처분|강제퇴거|출국명령|"
    r"난민|귀화\s*불허|법령\s*(?:과|및|·)?\s*판례|조문|법적\s*근거|"
    r"precedent|case\s+law|administrative\s+appeal|litigation|denial|"
    r"revocation|deportation|statutory\s+basis",
    re.IGNORECASE,
)

_PROCEDURE_RISK_RE = re.compile(
    r"근무처\s*(?:변경|추가)|고용주\s*변경|체류자격\s*변경|"
    r"체류자격\s*외\s*활동|사전\s*허가|신고\s*기한|허가\s*전|"
    r"과태료|범칙금|벌금|위반|"
    r"change\s+(?:of\s+)?(?:employer|workplace|status)|"
    r"activities?\s+outside\s+status|prior\s+permission|reporting\s+deadline|penalt",
    re.IGNORECASE,
)

# Fast tier: a light, low-latency primary with a 4-deep fallback chain.
# Each fallback is tried in order when the previous model is rate-limited
# (429) or its upstream is temporarily unavailable (503). A 4-candidate chain
# means all four models must fail simultaneously before the "no candidates
# available" deterministic fallback is shown — substantially less likely than
# with a 2-candidate chain.
#
# qwen/* is intentionally NOT used here — it is reserved for Chinese-language
# routes by policy.
DEFAULT_FAST_ANSWER_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_FAST_ANSWER_MODEL_CANDIDATES: List[str] = [
    "google/gemma-4-26b-a4b-it:free",            # Fast primary — Gemma 4 MoE (~3.8B active)
    "openai/gpt-oss-20b:free",                   # Fast fallback 1 — small, fast gpt-oss
    "google/gemma-4-31b-it:free",                # Fast fallback 2 — Gemma 4 31B dense
    "meta-llama/llama-3.3-70b-instruct:free",    # Fast fallback 3 — Llama 3.3 70B
]

# Enforcement structured extraction/prediction is deliberately isolated from
# the deploy-wide Fast answer env overrides. Railway can carry older Fast-tier
# settings for unrelated features; enforcement must not inherit those silently.
# Keep this chain short: both models are current free OpenRouter endpoints with
# structured-output support, and the caller applies a hard total latency budget.
DEFAULT_ENFORCEMENT_STRUCTURED_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_ENFORCEMENT_STRUCTURED_MODEL_CANDIDATES: List[str] = [
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-20b:free",
]

DEFAULT_VERIFIER_MODEL = "openai/gpt-oss-120b:free"

DEFAULT_CHINESE_MODEL = "deepseek/deepseek-r1-0528:free"
DEFAULT_CHINESE_FALLBACK_MODELS: List[str] = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "moonshotai/kimi-k2.6:free",
]

# These are public provider/model-family labels, not secrets.
# They are excluded from Paradiso's default final-answer candidate chain unless a
# Chinese-language route explicitly asks for them.
CHINESE_ONLY_MODEL_PREFIXES = ("deepseek/", "qwen/", "moonshotai/", "z-ai/")


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return list(default)
    out: List[str] = []
    seen = set()
    for item in raw.split(","):
        clean = item.strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    return out or list(default)


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        clean = (item or "").strip()
        if clean and clean not in seen:
            out.append(clean)
            seen.add(clean)
    return out


def resolve_model_role_policy() -> Dict[str, Any]:
    final_model = _env("OPENROUTER_MODEL", DEFAULT_FINAL_ANSWER_MODEL)
    final_candidates = _dedupe_preserve_order(
        [final_model, *_csv_env("OPENROUTER_MODEL_CANDIDATES", DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES)]
    )
    enforcement_model = _env(
        "OPENROUTER_ENFORCEMENT_MODEL", DEFAULT_ENFORCEMENT_STRUCTURED_MODEL
    )
    enforcement_candidates = _dedupe_preserve_order(
        [
            enforcement_model,
            *_csv_env(
                "OPENROUTER_ENFORCEMENT_MODEL_CANDIDATES",
                DEFAULT_ENFORCEMENT_STRUCTURED_MODEL_CANDIDATES,
            ),
        ]
    )

    return {
        "version": MODEL_POLICY_VERSION,
        "router_model": _env("AI_ROUTER_MODEL", DEFAULT_ROUTER_MODEL),
        "translation_model": _env("AI_TRANSLATION_MODEL", DEFAULT_TRANSLATION_MODEL),
        "final_answer_model": final_model,
        "final_answer_model_candidates": final_candidates,
        "verifier_model": _env("AI_VERIFIER_MODEL", DEFAULT_VERIFIER_MODEL),
        "enforcement_structured_model": enforcement_model,
        "enforcement_structured_model_candidates": enforcement_candidates,
        "chinese_model": _env("AI_CHINESE_MODEL", DEFAULT_CHINESE_MODEL),
        "chinese_fallback_models": _csv_env("AI_CHINESE_FALLBACK_MODELS", DEFAULT_CHINESE_FALLBACK_MODELS),
        "chinese_only_model_prefixes": list(CHINESE_ONLY_MODEL_PREFIXES),
        "policy_notes": [
            "Gemma is reserved for translation, language detection, and low-risk routing by default.",
            "Hermes 3 (Llama 3.1 405B) is the default Basic final-answer model, with Gemma 4 as the Basic fallback.",
            "gpt-oss is the default verifier / structured audit model (gpt-oss-20b is the Fast-tier fallback).",
            "DeepSeek, Qwen, Kimi, and Z.ai families are reserved for Chinese-language routes by policy.",
            "Random OpenRouter routing such as openrouter/auto or openrouter/free is not allowed.",
        ],
    }


def normalize_answer_mode(mode: Any) -> str:
    """Coerce an arbitrary client value into a supported answer mode label."""
    value = str(mode or "").strip().lower()
    if value in ANSWER_MODES:
        return value
    return DEFAULT_ANSWER_MODE


def resolve_question_answer_mode(
    mode: Any,
    *,
    question: str = "",
    legal_issue_types: Optional[Sequence[str]] = None,
    risk_level: str = "",
) -> Dict[str, Any]:
    """Resolve the user-requested tier into the minimum safe answer tier.

    Only Fast can be automatically promoted.  Basic is never downgraded, and
    the existing Pro-unavailable behavior remains explicit.  The router is
    deterministic, secret-free, and returns public reason codes so the client
    can explain why a question took the more careful path.
    """
    requested = normalize_answer_mode(mode)
    if requested == "pro":
        return {
            "requested_mode": "pro",
            "effective_mode": "basic",
            "auto_escalated": False,
            "available": False,
            "escalation_reasons": ["pro_unavailable_basic_fallback"],
            "version": MODEL_POLICY_VERSION,
        }
    if requested != "fast":
        return {
            "requested_mode": requested,
            "effective_mode": requested,
            "auto_escalated": False,
            "available": True,
            "escalation_reasons": [],
            "version": MODEL_POLICY_VERSION,
        }

    text = " ".join(str(question or "").split())
    reasons: List[str] = []
    issues = {str(v or "").strip() for v in (legal_issue_types or []) if str(v or "").strip()}
    if issues & _BASIC_MINIMUM_ISSUES:
        reasons.append("complex_legal_issue")
    if str(risk_level or "").strip().lower() == "high":
        reasons.append("high_risk_question")
    if _SOURCE_HEAVY_RE.search(text):
        reasons.append("source_heavy_question")
    if _PROCEDURE_RISK_RE.search(text):
        reasons.append("permission_or_deadline_risk")

    clause_count = (
        text.count("?") + text.count("？") + text.count(",") + text.count("、")
        + text.count("그리고") + text.lower().count(" and ") + text.count("동시에")
    )
    if len(text) >= 80 or clause_count >= 3:
        reasons.append("multi_factor_question")

    reasons = list(dict.fromkeys(reasons))
    return {
        "requested_mode": "fast",
        "effective_mode": "basic" if reasons else "fast",
        "auto_escalated": bool(reasons),
        "available": True,
        "escalation_reasons": reasons,
        "version": MODEL_POLICY_VERSION,
    }


def resolve_answer_mode_models(mode: Any) -> Dict[str, Any]:
    """Resolve the OpenRouter primary model + candidate chain for an answer mode.

    Returns a dict with ``mode`` (normalized), ``primary``, ``candidates`` and
    ``available``. The ``pro`` tier is intentionally NOT wired to a model yet
    ("coming soon") — callers should fall back to the basic chain and surface the
    tier as unavailable rather than silently answering with a different depth.
    Env overrides keep deploys flexible: ``OPENROUTER_FAST_MODEL`` /
    ``OPENROUTER_FAST_MODEL_CANDIDATES`` for the fast tier; the basic tier reuses
    ``OPENROUTER_MODEL`` / ``OPENROUTER_MODEL_CANDIDATES``.
    """
    normalized = normalize_answer_mode(mode)

    if normalized == "fast":
        primary = _env("OPENROUTER_FAST_MODEL", DEFAULT_FAST_ANSWER_MODEL)
        candidates = _dedupe_preserve_order(
            [primary, *_csv_env("OPENROUTER_FAST_MODEL_CANDIDATES", DEFAULT_FAST_ANSWER_MODEL_CANDIDATES)]
        )
        return {"mode": "fast", "primary": primary, "candidates": candidates, "available": True}

    # basic (and pro -> basic fallback)
    primary = _env("OPENROUTER_MODEL", DEFAULT_FINAL_ANSWER_MODEL)
    candidates = _dedupe_preserve_order(
        [primary, *_csv_env("OPENROUTER_MODEL_CANDIDATES", DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES)]
    )
    return {
        "mode": normalized if normalized == "basic" else "basic",
        "primary": primary,
        "candidates": candidates,
        # 'pro' is requested-but-not-yet-available; we answered on the basic chain.
        "available": normalized == "basic",
        "requested_mode": normalized,
    }


def sanitize_model_role_policy_for_public() -> Dict[str, Any]:
    # All values are public model identifiers or plain policy labels. Keep this
    # helper anyway so /health never has to know about secrets or raw env access.
    return dict(resolve_model_role_policy())


def model_family_is_chinese_only(model_id: str) -> bool:
    low = (model_id or "").strip().lower()
    return any(low.startswith(prefix) for prefix in CHINESE_ONLY_MODEL_PREFIXES)
