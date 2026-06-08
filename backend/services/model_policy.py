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


def sanitize_model_role_policy_for_public() -> Dict[str, Any]:
    # All values are public model identifiers or plain policy labels. Keep this
    # helper anyway so /health never has to know about secrets or raw env access.
    return dict(resolve_model_role_policy())


def model_family_is_chinese_only(model_id: str) -> bool:
    low = (model_id or "").strip().lower()
    return any(low.startswith(prefix) for prefix in CHINESE_ONLY_MODEL_PREFIXES)
