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

# Fast tier: a light, low-latency model first, then a GUARANTEED-working tail.
#
# The fast chain must never be able to fail as a whole while the basic chain
# would have answered. Earlier the fast tier was a set of ultralight free slugs
# (gemma-4-26b-a4b / gemma-3-4b / qwen / llama-3.2-3b) that were DISJOINT from
# the proven basic chain, so whenever those light free endpoints were all down
# or rate-limited, every fast request collapsed into the deterministic
# "all online model candidates failed" preparation note — even though the basic
# tier's models were answering fine. The fast chain now ENDS with the same
# proven-working models the basic chain uses (gpt-oss-120b, gemma-4-31b): the
# light primary keeps answers snappy when it is available, and the candidate-skip
# logic (model_not_found / rate-limit -> next candidate) falls through to a model
# that is known to answer instead of giving up.
#
# qwen/* is intentionally NOT used here — it is reserved for Chinese-language
# routes by policy, and it was one of the unreliable slugs in the broken chain.
DEFAULT_FAST_ANSWER_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_FAST_ANSWER_MODEL_CANDIDATES: List[str] = [
    "google/gemma-4-26b-a4b-it:free",   # Gemma 4 MoE (~3.8B active) — light, fast primary
    "google/gemma-3-4b-it:free",        # Gemma 3 4B — lightest Gemma fallback
    "openai/gpt-oss-120b:free",         # proven-working tail (shared with the basic chain)
    "google/gemma-4-31b-it:free",       # proven-working tail (shared with the basic chain)
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
