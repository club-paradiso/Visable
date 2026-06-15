"""Paradiso model role policy.

This module keeps model routing policy explicit and testable:

- Gemma is the default low-risk router / translation model.
- Nemotron is the final-answer model family for Paradiso's core visa/status AI.
- gpt-oss is the verifier / structured audit model.
- China-origin model families are reserved for Chinese-language tasks only by policy.

The module never reads or exposes provider secrets. It only resolves public model
catalog identifiers from environment variables.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

MODEL_POLICY_VERSION = "2026-06-nemotron-final-gemma-i18n"

DEFAULT_ROUTER_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_TRANSLATION_MODEL = "google/gemma-4-31b-it:free"

DEFAULT_FINAL_ANSWER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES: List[str] = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
]

# ---------------------------------------------------------------------------
# Answer-speed tiers ("Waymaker" answer modes)
# ---------------------------------------------------------------------------
# The frontend exposes a Fast / Basic / Pro selector. Each tier maps to a
# distinct OpenRouter candidate chain so users can trade depth for latency:
#
#   * fast  — a small, low-latency model first (snappy answers; less depth).
#   * basic — the default Nemotron final-answer chain (current behavior).
#   * pro   — reserved / "coming soon"; not yet wired to a model chain.
#
# Random routing stays forbidden; every tier is an explicit, auditable chain.
ANSWER_MODES = ("fast", "basic", "pro")
DEFAULT_ANSWER_MODE = "basic"

# Fast tier: prefer the lightest reliable free model for low latency. Order is
# Gemma first (requested), then Qwen, then Llama as a last resort — every entry
# is a small / MoE-active-light free model so the fast tier stays snappy. The
# candidate-skip logic (model_not_found -> next candidate) means a momentarily
# unavailable slug simply falls through to the next, so the chain is resilient.
# NOTE: qwen/* is normally reserved for Chinese-language routes by policy; it is
# included here ONLY as an explicit fast-tier fallback per product request, and
# never as a default for the (basic) final-answer chain.
DEFAULT_FAST_ANSWER_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_FAST_ANSWER_MODEL_CANDIDATES: List[str] = [
    "google/gemma-4-26b-a4b-it:free",   # Gemma 4 MoE (~3.8B active) — light + preferred
    "google/gemma-3-4b-it:free",        # Gemma 3 4B — lightest Gemma fallback
    "qwen/qwen3-next-80b-a3b-instruct:free",  # Qwen free (A3B active) — fallback
    "meta-llama/llama-3.2-3b-instruct:free",  # Llama free 3B — last-resort fallback
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

    return {
        "version": MODEL_POLICY_VERSION,
        "router_model": _env("AI_ROUTER_MODEL", DEFAULT_ROUTER_MODEL),
        "translation_model": _env("AI_TRANSLATION_MODEL", DEFAULT_TRANSLATION_MODEL),
        "final_answer_model": final_model,
        "final_answer_model_candidates": final_candidates,
        "verifier_model": _env("AI_VERIFIER_MODEL", DEFAULT_VERIFIER_MODEL),
        "chinese_model": _env("AI_CHINESE_MODEL", DEFAULT_CHINESE_MODEL),
        "chinese_fallback_models": _csv_env("AI_CHINESE_FALLBACK_MODELS", DEFAULT_CHINESE_FALLBACK_MODELS),
        "chinese_only_model_prefixes": list(CHINESE_ONLY_MODEL_PREFIXES),
        "policy_notes": [
            "Gemma is reserved for translation, language detection, and low-risk routing by default.",
            "Nemotron is the default final-answer model family for core Paradiso visa/status answers.",
            "gpt-oss is the default verifier / structured audit model.",
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
