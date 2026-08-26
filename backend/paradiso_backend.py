"""Paradiso backend service.

FastAPI application exposing the routes used by the Paradiso frontend:

- GET  /
- GET  /health
- GET  /api/visas
- POST /api/ask
- POST /api/jobcodekeywords

Configuration is read from the environment. No secrets are baked in;
the service degrades gracefully when optional integrations (LLM
providers, database) are not configured and returns a clear JSON error
instead of crashing.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
import dataclasses
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from rate_limit import rate_limit
from services import legal_evidence
from services.law_grounding import (
    build_law_grounding_context,
    build_law_search_query,
    build_law_search_queries,
    classify_law_host_reachability,
    derive_law_grounding_status_detail,
    law_grounding_preflight,
    law_grounding_status_detail_is_verified,
    should_attempt_law_grounding,
)
from services.law_citation_guard import (
    build_citation_safety_directive,
    build_unverified_citation_notice,
    guard_answer_citations,
)
from services.grounding_config import load_grounding_config
from services.law_tools import build_law_evidence_pack, search_laws, search_laws_ranked
from services import unified_search as _unified_search
from services import manual_search as _manual_search
from services import manual_registry as _manual_registry
from services import statute_citation_guard as _statute_guard
from services import employment_nl as _employment_nl
from services import precedent_sources
from services.enforcement_models import StructuredCase
from services.enforcement_service import analyze_enforcement_case, extract_structured_case
from services import legal_research
from services import legal_synthesis
from services import mofa_public_data
from services.citation_verifier import extract_korean_legal_citations, verify_case_decision_citations
from services.legal_analysis import first_sentence_quality_warning, is_registration_deadline_query, status_work_capability
from services.answer_quality import (
    ANSWER_STYLE_VERSION,
    build_answer_directives,
    classify_answer_quality,
    enforce_source_confidence_invariants,
)
from services import answer_quality as _answer_quality
from services.answer_shape import (
    ANSWER_SHAPE_VERSION,
    build_answer_shape_contract,
    evaluate_answer_shape,
)
from services.model_policy import (
    CHINESE_ONLY_MODEL_PREFIXES,
    DEFAULT_ANSWER_MODE,
    DEFAULT_FINAL_ANSWER_MODEL,
    DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES,
    MODEL_POLICY_VERSION,
    normalize_answer_mode,
    resolve_answer_mode_models,
    resolve_question_answer_mode,
    sanitize_model_role_policy_for_public,
)
from services.providers.nvidia_nim import NvidiaNimProvider

# First-stage Trust & Safety guardrail. Imported UNGUARDED on purpose: safety is
# not an optional feature, so a broken safety module must fail the deploy (fail
# closed) rather than silently let unsafe requests through (fail open). Both
# modules are standard-library-only and have no heavy dependencies.
import safety_guardrails
import safety_events


class UTF8JSONResponse(JSONResponse):
    # Starlette only auto-appends `charset=utf-8` to text/* media types,
    # so the default application/json response carries no charset and
    # legacy clients (older browsers, some proxies, terminal viewers)
    # may decode the UTF-8 body as latin-1 and render Korean text as
    # mojibake. JSON is always UTF-8 (RFC 8259); say so explicitly.
    media_type = "application/json; charset=utf-8"

try:  # httpx is listed in requirements.txt; guard so the file still imports
    import httpx  # type: ignore
except Exception:  # pragma: no cover - import-time guard only
    httpx = None  # type: ignore

try:  # optional structured manual-evidence layer (PR #228); guard import
    import structured_requirements as _structured_requirements  # type: ignore
except Exception:  # pragma: no cover - import-time guard only
    _structured_requirements = None  # type: ignore

try:  # procedure packet builder + safe 통합신청서 typing helper (scaffold)
    from services.procedure_packet_builder import (  # type: ignore
        build_procedure_packet as _build_procedure_packet,
        build_available_packets_for_status as _build_available_packets_for_status,
        SUPPORTED_PACKET_TYPES as _SUPPORTED_PACKET_TYPES,
    )
except Exception:  # pragma: no cover - import-time guard only
    _build_procedure_packet = None  # type: ignore
    _build_available_packets_for_status = None  # type: ignore
    _SUPPORTED_PACKET_TYPES = ()  # type: ignore


logger = logging.getLogger("paradiso.backend")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY: Optional[str] = os.environ.get("OPENROUTER_API_KEY")
GROQ_API_KEY: Optional[str] = os.environ.get("GROQ_API_KEY")
LAW_API_KEY: Optional[str] = os.environ.get("LAW_API_KEY")
DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")
SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY: Optional[str] = os.environ.get("SUPABASE_SERVICE_KEY")

# Pin Paradiso AI to a deterministic OpenRouter model rather than the
# variable `openrouter/auto` router. The model-role policy lives in
# services.model_policy so the final-answer, router, translation, verifier, and
# Chinese-language model choices remain explicit and testable.
#
# Core policy:
# - final answers: Nemotron Ultra -> Nemotron Super -> gpt-oss -> Gemma
# - router / translation: Gemma
# - verifier: gpt-oss
# - Chinese-language route only: DeepSeek / Qwen / Kimi family
#
# Override per-deploy with OPENROUTER_MODEL and OPENROUTER_MODEL_CANDIDATES if
# the OpenRouter catalog changes. Random routing is still forbidden.
_DEFAULT_OPENROUTER_MODEL: str = DEFAULT_FINAL_ANSWER_MODEL
OPENROUTER_MODEL: str = (
    os.environ.get("OPENROUTER_MODEL", "").strip() or _DEFAULT_OPENROUTER_MODEL
)

# Explicit, predictable OpenRouter fallback candidates. When the primary model
# is rate-limited (429) or its upstream is unavailable (503 / "no healthy
# upstream"), Paradiso retries the NEXT OpenRouter candidate rather than
# silently switching providers or surfacing raw provider JSON. Random
# free-model routing (openrouter/auto) is intentionally NOT used — Paradiso
# needs predictable model behaviour and auditable response metadata.
_DEFAULT_OPENROUTER_MODEL_CANDIDATES: List[str] = list(DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES)

# Model ids that denote random / non-deterministic routing — disallowed here.
_RANDOM_ROUTING_TOKENS = {"openrouter/auto", "openrouter/free", "auto", "free"}
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+$")


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        clean = (item or "").strip()
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def _resolve_openrouter_candidates() -> List[str]:
    """Ordered, de-duplicated OpenRouter candidate list (primary model first).

    OPENROUTER_MODEL is always attempted first. OPENROUTER_MODEL_CANDIDATES
    (optional, comma-separated) supplies the rest; when unset we fall back to the
    built-in policy list. Random-routing ids are never injected by us.
    """
    raw = (os.environ.get("OPENROUTER_MODEL_CANDIDATES") or "").strip()
    configured = (
        [c.strip() for c in raw.split(",")]
        if raw
        else list(_DEFAULT_OPENROUTER_MODEL_CANDIDATES)
    )
    # Primary model is always first; duplicates are collapsed preserving order.
    return _dedupe_preserve_order([OPENROUTER_MODEL, *configured])


OPENROUTER_MODEL_CANDIDATES: List[str] = _resolve_openrouter_candidates()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return max(0.0, float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


OPENROUTER_MODEL_COOLDOWN_SECONDS: float = _env_float("OPENROUTER_MODEL_COOLDOWN_SECONDS", 300.0)
# In-memory only: model id -> unix timestamp when the retryable failure occurred.
_OPENROUTER_MODEL_COOLDOWNS: Dict[str, float] = {}

ENABLE_OLLAMA_FALLBACK: bool = _env_bool("ENABLE_OLLAMA_FALLBACK", False)
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen3:8b").strip() or "qwen3:8b"
OLLAMA_TIMEOUT_SECONDS: float = _env_float("OLLAMA_TIMEOUT_SECONDS", 20.0)

# Hard ceiling for a single outbound LLM provider request (OpenRouter / Groq).
# A provider that hangs must never stall /api/ask indefinitely: when this
# timeout is hit the request is converted into a *retryable* upstream error so
# the candidate fallback chain, the per-model cooldown, and the deterministic
# source-grounded preparation note all still engage (instead of bubbling up as
# an uncaught 500). The default preserves the historical 60s behaviour; lower
# it per-deploy (e.g. OPENROUTER_TIMEOUT_SECONDS=40) for snappier failure.
OPENROUTER_TIMEOUT_SECONDS: float = _env_float("OPENROUTER_TIMEOUT_SECONDS", 60.0)

# Output-length cap for the final answer. Unbounded generation over Paradiso's
# large grounded prompt was a major perceived-latency source ("Waymaker is too
# slow"): a long answer takes proportionally longer to generate and stream back.
# Capping completion tokens keeps answers focused and materially faster without
# changing model selection. 0 / negative disables the cap (legacy behaviour).
# The fast answer tier uses a tighter cap for snappier responses.
OPENROUTER_MAX_TOKENS: int = int(_env_float("OPENROUTER_MAX_TOKENS", 1400.0))
OPENROUTER_FAST_MAX_TOKENS: int = int(_env_float("OPENROUTER_FAST_MAX_TOKENS", 900.0))


def _validate_model_candidates(candidates: List[str]) -> List[str]:
    """Non-secret formatting/policy warnings about the candidate list."""
    warnings: List[str] = []
    if not candidates:
        warnings.append("MODEL_CANDIDATES_EMPTY")
        return warnings
    for c in candidates:
        low = c.strip().lower()
        if low in _RANDOM_ROUTING_TOKENS or low.endswith("/auto"):
            warnings.append("MODEL_CANDIDATES_RANDOM_ROUTING")
        elif not _MODEL_ID_RE.match(c.strip()):
            warnings.append("MODEL_CANDIDATES_MALFORMED")
        elif any(low.startswith(prefix) for prefix in CHINESE_ONLY_MODEL_PREFIXES):
            warnings.append("MODEL_CANDIDATES_CHINESE_MODEL_RESTRICTED_TO_CHINESE")
    return _dedupe_preserve_order(warnings)

GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

# Whether Groq may be used as a fallback when OpenRouter is not configured.
# Production intent is strict OpenRouter-first, so the default is now FALSE:
# Groq is only ever reached when OPENROUTER_API_KEY is unset AND the operator
# has explicitly opted in with ALLOW_GROQ_FALLBACK=true. With the default,
# /api/ask returns a safe 503 (no_llm_provider_configured) instead of silently
# answering via a different provider/model when OpenRouter is expected.
#
# Migration note: a deployment that ran Groq-only and relied on the previous
# default (true) must now set ALLOW_GROQ_FALLBACK=true explicitly. Deployments
# that configure OPENROUTER_API_KEY (the intended production setup, including
# Railway) are unaffected because OpenRouter always takes precedence.
_GROQ_FALLBACK_TRUE_TOKENS = {"1", "true", "yes", "on"}
ALLOW_GROQ_FALLBACK: bool = (
    (os.environ.get("ALLOW_GROQ_FALLBACK", "false") or "false").strip().lower()
    in _GROQ_FALLBACK_TRUE_TOKENS
)

# ---------------------------------------------------------------------------
# Client-supplied model allowlist (pre-launch hardening, finding H-1b)
# ---------------------------------------------------------------------------
# ``req.model`` used to be forwarded verbatim into the OpenRouter/Groq payload,
# letting any anonymous caller run arbitrary (including paid) model ids on the
# server's API keys. A client-requested model is now honored ONLY when it is
# one of the model ids this deployment already references (the configured
# primary + candidate chains and the answer-mode tiers). Anything else is
# silently ignored with a warning log — never a 400, because the normal UI
# paths do not send `model` at all and must keep working unchanged.


def _allowed_client_models(provider: str) -> set:
    """Public model ids a client may explicitly request for one provider."""
    allowed: set = set()
    if provider == "openrouter":
        allowed.add(OPENROUTER_MODEL)
        allowed.update(OPENROUTER_MODEL_CANDIDATES)
        for mode in ("fast", "basic"):
            try:
                plan = resolve_answer_mode_models(mode) or {}
            except Exception:  # pragma: no cover - policy resolution is total
                plan = {}
            allowed.update(plan.get("candidates") or [])
            if plan.get("primary"):
                allowed.add(plan["primary"])
    elif provider == "groq":
        allowed.add(GROQ_MODEL)
    return {m for m in allowed if isinstance(m, str) and m.strip()}


def _sanitize_requested_model(requested: Optional[str], provider: str) -> Optional[str]:
    """Return the requested model only if allowlisted; else None (use default)."""
    clean = (requested or "").strip()
    if not clean:
        return None
    if clean in _allowed_client_models(provider):
        return clean
    logger.warning(
        "Ignoring client-requested model not in the configured %s allowlist: %r",
        provider,
        clean[:120],
    )
    return None


SITE_URL: str = os.environ.get("SITE_URL", "")
SITE_TITLE: str = os.environ.get("SITE_TITLE", "Paradiso")

# Optional pointer to the human-facing Paradiso frontend (e.g. the
# GitHub Pages deployment). Surfaced by GET / so that a person who hits
# the bare Railway URL on a phone is not greeted by a raw 404 detail
# blob with no hint where the actual app lives.
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "").strip()

CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
] or ["*"]

# ---------------------------------------------------------------------------
# /api/ask input caps (pre-launch hardening, finding H-1c)
# ---------------------------------------------------------------------------
# Sized comfortably ABOVE every legitimate frontend payload so no real user is
# ever rejected, while stopping megabyte-scale prompt/context abuse:
#   * prompt      — ai.html caps the question at 500 chars client-side
#                   (MAX_CHARS); the index.html AI panel and the Waymaker
#                   navigator follow-up have no client cap but send short typed
#                   questions. 4000 chars = 8x the largest client cap.
#   * history     — ai.html sends at most 12 turns of <=1200 chars each
#                   (rememberTurn); caps are 24 items / 2000 chars. Oversize is
#                   safely TRUNCATED (newest kept): history feeds only the
#                   Trust & Safety repeat-abuse classifier, never the prompt.
#   * context     — buildAskContext() tops out around ~2.5k chars (directives +
#                   optional nationality/interview/scenario lines); the field
#                   is currently unused server-side, so oversize is truncated.
#   * visa_data   — the largest legitimate compactVisaRecord payload measured
#                   from visa_data.json is ~116k chars serialized (F-5), so the
#                   300k cap leaves ~2.5x headroom for data growth; beyond it a
#                   structured 400 is returned (silently dropping the record
#                   could degrade answer grounding without the user knowing).
ASK_MAX_PROMPT_CHARS: int = int(_env_float("PARADISO_ASK_MAX_PROMPT_CHARS", 4000.0))
ASK_MAX_HISTORY_ITEMS: int = int(_env_float("PARADISO_ASK_MAX_HISTORY_ITEMS", 24.0))
ASK_MAX_HISTORY_ITEM_CHARS: int = int(_env_float("PARADISO_ASK_MAX_HISTORY_ITEM_CHARS", 2000.0))
ASK_MAX_CONTEXT_CHARS: int = int(_env_float("PARADISO_ASK_MAX_CONTEXT_CHARS", 8000.0))
ASK_MAX_VISA_DATA_CHARS: int = int(_env_float("PARADISO_ASK_MAX_VISA_DATA_CHARS", 300000.0))


def _debug_endpoints_enabled() -> bool:
    """Live env read so the flag can be flipped without code changes (M-10)."""
    return _env_bool("PARADISO_ENABLE_DEBUG_ENDPOINTS", False)


def _require_debug_endpoints_enabled() -> None:
    """Gate for diagnostic endpoints that reveal deployment/network topology.

    Default OFF: the gated endpoints answer with the same plain 404 an unknown
    route gets, so their existence is not advertised to anonymous scanners.
    Operators set PARADISO_ENABLE_DEBUG_ENDPOINTS=true (e.g. temporarily on
    Railway) when they need the live selftest/netdiag/grounding debug views.
    The boolean-only readiness preflight stays open.
    """
    if not _debug_endpoints_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


# ---------------------------------------------------------------------------
# Law-grounding runtime state (single source of truth)
# ---------------------------------------------------------------------------
def _law_grounding_runtime_state(cfg=None):
    """Resolve the runtime law-grounding state from the one config source.

    Returns ``(configured_mode, effective_mode, active)``:

    * ``configured_mode`` — the resolved LAW_GROUNDING_MODE (default ``enabled``
      via grounding_config; NOT the stale ``disabled`` literal that /health and
      the startup log used to hardcode, which misreported an active deployment).
    * ``effective_mode`` — applies the enabled-without-credential rule: an
      ``enabled`` deploy with no LAW_API_OC makes no external call and does not
      degrade answers, so it behaves like ``disabled``.
    * ``active`` — True only when a real-time law lookup will actually be
      attempted (``audit`` always; ``enabled`` only with a credential).

    The same helper drives the /api/ask gate, /health, and the startup log so the
    reported mode can never disagree with the behavior.
    """
    cfg = cfg or load_grounding_config()
    mode = cfg.mode
    effective = "disabled" if (mode == "enabled" and not cfg.law_api_configured) else mode
    active = effective in {"audit", "enabled"}
    return mode, effective, active


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    """Log the active provider/model and law-grounding mode at startup.

    Reports only non-secret descriptors (provider name, public model id,
    feature flags). API keys are never logged.
    """
    llm = _resolve_llm_config()
    law_mode, law_effective, law_active = _law_grounding_runtime_state()
    logger.info(
        "Paradiso backend startup: llm_provider=%s llm_model=%s groq_fallback_allowed=%s "
        "law_grounding_mode=%s law_grounding_effective=%s law_grounding_active=%s",
        llm["provider"],
        llm["model"],
        llm["groq_fallback_allowed"],
        law_mode,
        law_effective,
        law_active,
    )
    yield


app = FastAPI(
    title="Paradiso Backend",
    version="0.1.0",
    default_response_class=UTF8JSONResponse,
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    # Prompt aliases. Resolution order: message -> query -> question.
    # `question` is the field the Paradiso frontend currently sends; the
    # other two keep parity with curl-driven clients and earlier docs.
    message: Optional[str] = None
    query: Optional[str] = None
    question: Optional[str] = None

    # Optional metadata accepted to keep the contract stable. These fields
    # are not yet used for answer generation, but declaring them prevents
    # accidental schema rejection and documents the wire format.
    visa_code: Optional[str] = None
    visa_data: Optional[Dict[str, Any]] = None
    selected_procedure_key: Optional[str] = None
    selected_procedure_variant_id: Optional[str] = None
    context: Optional[str] = None
    lang: Optional[str] = None
    consent: Optional[bool] = None
    history: Optional[List[Dict[str, Any]]] = None
    model: Optional[str] = None
    # Answer-speed tier selected in the UI: "fast" | "basic" | "pro".
    # Controls which OpenRouter candidate chain + output cap is used. Unknown /
    # missing values fall back to the default ("basic"). "pro" is not yet wired
    # to a model chain and transparently answers on the basic chain.
    answer_mode: Optional[str] = None
    # When true, the answer is streamed back token-by-token as Server-Sent
    # Events (text/event-stream) for a far snappier perceived response. The
    # in-prompt safety/confidence directives still apply, and the post-hoc
    # safety review runs on the fully-accumulated text after the final token
    # (a tripped review replaces the answer via SSE before the stream closes).
    # The post-hoc answer-shape repair gate stays buffered-only: its repair
    # rewrites the complete answer, which is not meaningful after streaming.
    stream: Optional[bool] = None


class AskResponse(BaseModel):
    answer: str
    provider: str
    model: str
    grounding_used: bool = False
    grounding_sources: List[Dict[str, Any]] = Field(default_factory=list)
    procedure_variant_context_used: bool = False
    procedure_variant_context_sources: List[Dict[str, Any]] = Field(default_factory=list)
    visa_code_detected: Optional[str] = None
    visa_sub_code_detected: Optional[str] = None
    task_type_detected: Optional[str] = None
    risk_level_detected: Optional[str] = None
    law_grounding_used: bool = False
    law_grounding_attempted: bool = False
    # Coarse, non-secret state for the source panel. One of:
    #   "not_attempted" — the question did not trigger law-grounding intent.
    #   "disabled"      — intent matched but LAW_GROUNDING_MODE is disabled.
    #   "unavailable"   — intent matched, grounding attempted, but no usable result.
    #   "used"          — intent matched and law grounding contributed context.
    law_grounding_status: str = "not_attempted"
    # Granular, mutually-exclusive, user-visible law-grounding status. One of:
    #   law_grounding_not_attempted / law_grounding_disabled /
    #   law_grounding_audit_only / law_grounding_verified /
    #   law_grounding_attempted_no_results / law_grounding_attempted_failed.
    # ``law_grounding_verified`` is the ONLY value that means specific real-time
    # statute citations may be trusted as confirmed.
    law_grounding_status_detail: str = "law_grounding_not_attempted"
    law_grounding_verified: bool = False
    law_grounding_retrieval_timestamp: str = ""
    # User-facing notice (non-empty only when grounding is NOT verified) and the
    # structured "실시간 법령 확인" panel payload.
    law_grounding_user_notice: str = ""
    law_grounding_display: Dict[str, Any] = Field(default_factory=dict)
    # Unverified-citation guardrail (non-secret). Detected article tokens, the
    # subset not backed by verified/local evidence, and the action taken.
    law_citations_detected: List[str] = Field(default_factory=list)
    unsupported_law_citations: List[str] = Field(default_factory=list)
    unverified_law_citation_detected: bool = False
    law_citation_guard_action: str = "none"
    law_grounding_intent_reasons: List[str] = Field(default_factory=list)
    law_search_query: str = ""
    law_search_queries: List[str] = Field(default_factory=list)
    law_grounding_warnings: List[str] = Field(default_factory=list)
    citation_verification: Optional[Dict[str, Any]] = None
    case_decision_citation_verification: Optional[Dict[str, Any]] = None
    case_decision_citation_verification_status: str = ""
    # Manual-to-law fallback transparency. Coarse, non-secret signals only.
    #   manual_grounding_status: "present" when deterministic manual / source-
    #     confirmed structured requirements were available for this question;
    #     "absent" when no manual document grounding was found.
    #   manual_to_law_fallback_used: True when manual document grounding was
    #     absent for a legal/activity-scope question and the system therefore
    #     leaned on law-grounding (statute/enforcement-decree) context instead.
    #     This NEVER produces a required-document checklist — only legal context.
    #   manual_to_law_fallback_reason: short machine-readable reason code.
    manual_grounding_status: str = "absent"
    manual_to_law_fallback_used: bool = False
    manual_to_law_fallback_reason: str = ""
    # General answer-quality contract (non-secret). Computed deterministically
    # from the grounding state above so the frontend can render honest
    # source/state chips and the answer reads like a careful modern assistant.
    #   answer_quality_mode: one of source_confirmed / source_assisted /
    #     source_limited / source_unavailable / generic_advisory.
    #   source_confidence_level: coarse UI hint (high/moderate/low/none).
    #   requires_official_confirmation: True unless the answer is source_confirmed.
    #   official_confirmation_questions: exact questions to ask 1345/HiKorea/office.
    #   related_statuses_not_sources: comparison statuses to verify — NEVER a
    #     source that proves what the asked-about status permits (e.g. D-2/D-4 for
    #     an H-1 study question).
    #   grounded_answer_limited: True when direct source support is incomplete.
    #   answer_style_version: bumps when the answer contract changes.
    answer_quality_mode: str = "generic_advisory"
    source_confidence_level: str = "none"
    requires_official_confirmation: bool = True
    official_confirmation_questions: List[str] = Field(default_factory=list)
    related_statuses_not_sources: List[str] = Field(default_factory=list)
    grounded_answer_limited: bool = True
    source_confidence_invariant_reasons: List[str] = Field(default_factory=list)
    answer_style_version: str = ANSWER_STYLE_VERSION
    question_type_detected: str = "general"
    # Structured law/manual evidence pack (Part D). Non-secret: sanitized source
    # URLs only, OC/API-key values never appear. ``law_evidence_pack`` is the
    # full structured object; the flat fields below are convenience projections
    # for the frontend source panel and the smoke harness.
    law_evidence_pack: Optional[Dict[str, Any]] = None
    planned_law_queries: List[str] = Field(default_factory=list)
    law_sources: List[Dict[str, Any]] = Field(default_factory=list)
    precedent_evidence_items: List[Dict[str, Any]] = Field(default_factory=list)
    law_evidence_count: int = 0
    # Supplementary case-law / administrative-decision evidence (판례 / 재결례).
    # A SEPARATE field from manual/statute evidence so the UI distinguishes them.
    # Case law is contextual only and never a primary source for current rules.
    legal_evidence: Optional[Dict[str, Any]] = None
    legal_evidence_status: str = "not_attempted"
    legal_evidence_used: bool = False
    legal_evidence_cases: List[Dict[str, Any]] = Field(default_factory=list)
    legal_evidence_source_types: List[str] = Field(default_factory=list)
    legal_analysis: Optional[Dict[str, Any]] = None
    legal_analysis_exists: bool = False
    immigration_facts: Dict[str, Any] = Field(default_factory=dict)
    legal_issue_types: List[str] = Field(default_factory=list)
    proposed_activity_type: List[str] = Field(default_factory=list)
    source_plan: Dict[str, Any] = Field(default_factory=dict)
    query_classification: Dict[str, Any] = Field(default_factory=dict)
    official_grounding_context: Dict[str, Any] = Field(default_factory=dict)
    public_source_status: Dict[str, Any] = Field(default_factory=dict)
    public_official_sources: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_mode: str = ""
    main_issue: str = ""
    source_types_attempted: List[str] = Field(default_factory=list)
    source_types_returned: List[str] = Field(default_factory=list)
    source_type_statuses: Dict[str, str] = Field(default_factory=dict)
    # Source-panel developer-diagnostics contract (AI answer pipeline contract).
    # These back the per-family diagnostics rows the frontend source panel reads
    # (parser_status / source_family_statuses / parser_status_by_family). They are
    # declared here so the values are part of the stable, type-checked response
    # rather than being silently dropped as undeclared kwargs. Non-secret:
    # coarse status strings only, never URLs/keys.
    parser_status: str = ""
    response_shape_hint: str = ""
    source_panel_status: str = ""
    source_family_statuses: Dict[str, str] = Field(default_factory=dict)
    parser_status_by_family: Dict[str, str] = Field(default_factory=dict)
    # Generalized official-evidence ontology + structured query plan (non-secret).
    # The ontology snapshot describes the detected issue dimensions; the query
    # plan is a list of structured query objects (source_family, evidence_goal,
    # status anchors, reason). source_family_support flags wired vs planned-not-
    # wired families. See evidence_ontology.py / the generalized-retrieval doc.
    evidence_ontology: Dict[str, Any] = Field(default_factory=dict)
    evidence_query_plan: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_goal_by_query: List[str] = Field(default_factory=list)
    source_family_support: Dict[str, str] = Field(default_factory=dict)
    direct_evidence_count: int = 0
    related_evidence_count: int = 0
    analogical_evidence_count: int = 0
    background_evidence_count: int = 0
    missing_direct_authority: bool = True
    authority_summary: str = ""
    source_state: str = ""
    source_panel_state: str = ""
    source_panel_label_key: str = ""
    law_lookup_error_type: str = ""
    default_source_panel_should_show_raw_codes: bool = False
    source_panel_confidence: str = "none"
    direct_authority_available: bool = False
    direct_citation_available: bool = False
    legal_analysis_available: bool = False
    law_lookup_failed: bool = False
    citation_verification_status: str = ""
    manual_grounding_status_detail: str = ""
    answer_certainty_level: str = "unavailable"
    answer_first_sentence: str = ""
    first_sentence_quality_warning: str = ""
    # Evidence-backed answer-shape quality gate (Part A/B/C/F). Non-secret: a
    # contract key, pass/fail, and coarse warning strings only. These let the
    # frontend + smoke harness see whether the final answer satisfied the
    # issue-type answer-shape contract, and whether a weak live-model answer was
    # repaired by deterministic synthesis instead of being shown unmodified.
    answer_shape_contract: str = ""
    answer_shape_version: str = ANSWER_SHAPE_VERSION
    answer_quality_gate_passed: bool = True
    answer_quality_gate_warnings: List[str] = Field(default_factory=list)
    missing_answer_slots: List[str] = Field(default_factory=list)
    final_model_quality_warning: bool = False
    answer_shape_failed_by_model: bool = False
    model_answer_repaired_by_deterministic_synthesis: bool = False
    case_decision_citation_repaired: bool = False
    case_decision_citation_rejected: bool = False
    direct_manual_sources: List[Dict[str, Any]] = Field(default_factory=list)
    related_manual_sources: List[Dict[str, Any]] = Field(default_factory=list)
    law_grounding_error: str = ""
    # OpenRouter model-candidate fallback transparency (non-secret). When the
    # primary model is rate-limited / upstream-unavailable, Paradiso retries the
    # next explicit OpenRouter candidate rather than switching providers.
    llm_provider: str = ""
    # Answer-speed tier transparency. `answer_mode` is the tier actually used;
    # `answer_mode_requested` echoes what the client asked for so a "pro"
    # (coming-soon) request that fell back to basic is auditable.
    answer_mode: str = ""
    answer_mode_requested: str = ""
    answer_mode_available: bool = True
    # Fast may be promoted to Basic when the question is source-heavy,
    # high-risk, or multi-factor.  These public reason codes let the UI explain
    # the routing decision without exposing prompts or provider internals.
    answer_mode_auto_escalated: bool = False
    answer_mode_escalation_reasons: List[str] = Field(default_factory=list)
    answer_mode_route_version: str = ""
    requested_model: Optional[str] = None
    primary_model: Optional[str] = None
    model_candidates: List[str] = Field(default_factory=list)
    attempted_models: List[str] = Field(default_factory=list)
    final_model: Optional[str] = None
    # Debug alias for the model that actually produced the answer (== final_model).
    # Surfaced so Fast vs Basic routing is auditable from the client without
    # parsing the candidate chain.
    selected_model: Optional[str] = None
    # True when answer_mode == "fast" but the answer was produced by a model that
    # is NOT the configured fast primary (OPENROUTER_FAST_MODEL) — i.e. Fast fell
    # back down its chain. Lets the UI/operators see when Fast did not actually
    # use the fast model.
    fast_mode_fell_back: bool = False
    model_fallback_used: bool = False
    provider_family_fallback_used: bool = False
    provider_error_type: Optional[str] = None
    upstream_statuses: List[int] = Field(default_factory=list)
    retryable_provider_error: bool = False
    all_candidates_failed: bool = False
    skipped_models_due_to_cooldown: List[str] = Field(default_factory=list)
    cooling_down_models: List[str] = Field(default_factory=list)
    model_cooldown_seconds: float = 0
    cooldown_enabled: bool = False
    deterministic_fallback_answer_used: bool = False
    llm_unavailable: bool = False
    provider_unavailable: bool = False
    fallback_answer_reason: str = ""
    fallback_answer_kind: str = ""
    fallback_answer: str = ""
    copy_safe_answer: str = ""
    ollama_fallback_enabled: bool = False
    ollama_fallback_used: bool = False
    ollama_model: Optional[str] = None
    ollama_error_type: Optional[str] = None
    # First-stage Trust & Safety guardrail (non-secret, coarse signals only).
    #   safety_action: "allow" | "warn" | "block" | "escalate" | "emergency_review".
    #   safety_blocked: True when the model was NOT called and a refusal is shown.
    #   safety_category: coarse policy category (never an accusation about the user).
    #   safety_notice: optional brief caution shown for "warn" answers.
    #   safety_alternatives: lawful topics Waymaker CAN help with instead.
    # Pattern labels / matched signals are intentionally NOT exposed to clients;
    # they live only in the server-side safety event log.
    safety_action: str = "allow"
    safety_blocked: bool = False
    safety_category: str = "SAFE_LEGAL_INFO"
    safety_severity: int = 0
    safety_reason: str = ""
    safety_notice: str = ""
    safety_alternatives: List[str] = Field(default_factory=list)
    safety_event_id: str = ""
    safety_version: str = safety_guardrails.SAFETY_VERSION


SOURCE_PANEL_DIRECT_SOURCE_VERIFIED = "direct_source_verified"
SOURCE_PANEL_MANUAL_GROUNDING_AVAILABLE = "manual_grounding_available"
SOURCE_PANEL_LAW_GROUNDING_AVAILABLE = "law_grounding_available"
SOURCE_PANEL_RELATED_LEGAL_CONTEXT_AVAILABLE = "related_legal_context_available"
SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE = "structured_legal_analysis_available"
SOURCE_PANEL_STRUCTURED_FALLBACK_AVAILABLE = "structured_fallback_available"
SOURCE_PANEL_NO_DIRECT_AUTHORITY_FOUND = "no_direct_authority_found"
SOURCE_PANEL_LIVE_LAW_LOOKUP_TECHNICAL_ISSUE = "live_law_lookup_technical_issue"
SOURCE_PANEL_SOURCE_UNAVAILABLE = "source_unavailable"

_LAW_LOOKUP_ERROR_CODES = {
    "SOURCE_UNAVAILABLE",
    "LAW_API_BAD_RESPONSE",
    "LAW_API_PARSE_ERROR",
    "LAW_API_TIMEOUT",
    "LAW_API_OFFICIAL_ERROR",
    "LAW_API_NOT_CONFIGURED",
    "LAW_API_KEY_MISSING",
    "CITATION_VERIFICATION_NOT_WIRED",
}

def _source_panel_label_key(state: str, *, legal_analysis_exists: bool, law_lookup_error_type: str) -> str:
    if state == SOURCE_PANEL_STRUCTURED_FALLBACK_AVAILABLE:
        return "structured_fallback"
    if legal_analysis_exists and law_lookup_error_type in {"LAW_API_BAD_RESPONSE", "LAW_API_PARSE_ERROR", "SOURCE_UNAVAILABLE"}:
        return "structured_legal_analysis_law_lookup_issue"
    if state == SOURCE_PANEL_RELATED_LEGAL_CONTEXT_AVAILABLE:
        return "related_legal_context"
    if state == SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE:
        return "structured_legal_analysis"
    if state == SOURCE_PANEL_LIVE_LAW_LOOKUP_TECHNICAL_ISSUE:
        return "live_law_lookup_technical_issue"
    if state == SOURCE_PANEL_DIRECT_SOURCE_VERIFIED:
        return "direct_source_verified"
    if state == SOURCE_PANEL_MANUAL_GROUNDING_AVAILABLE:
        return "manual_grounding_available"
    if state == SOURCE_PANEL_LAW_GROUNDING_AVAILABLE:
        return "law_grounding_available"
    if state == SOURCE_PANEL_NO_DIRECT_AUTHORITY_FOUND:
        return "no_direct_authority_found"
    return "source_unavailable"

def _derive_law_lookup_error_type(pack: Optional[Dict[str, Any]], citation_verification: Optional[Dict[str, Any]], law_grounding_warnings: Optional[List[str]], law_grounding_error: str = "") -> str:
    candidates: List[Any] = []
    if law_grounding_error:
        candidates.append(law_grounding_error)
    if pack:
        candidates.extend([pack.get("law_grounding_error"), pack.get("error_type"), pack.get("law_lookup_error_type")])
        candidates.extend(pack.get("law_grounding_warnings") or [])
    candidates.extend(law_grounding_warnings or [])
    if citation_verification:
        candidates.extend([citation_verification.get("status"), citation_verification.get("error_type")])
        candidates.extend(citation_verification.get("warnings") or [])
    normalized = [str(candidate or "").upper() for candidate in candidates]
    for preferred in ("LAW_API_BAD_RESPONSE", "LAW_API_PARSE_ERROR", "LAW_API_TIMEOUT", "LAW_API_OFFICIAL_ERROR", "SOURCE_UNAVAILABLE"):
        if preferred in normalized:
            return preferred
    for code in normalized:
        if code in _LAW_LOOKUP_ERROR_CODES:
            return code
    return ""


def _derive_answer_certainty_level(*, direct_evidence_count: int, related_evidence_count: int, analogical_evidence_count: int, legal_analysis_exists: bool, citation_status: str, law_lookup_failed: bool) -> str:
    """Map evidence state to the public answer-certainty contract."""
    verified = str(citation_status or "").lower() == "verified"
    if direct_evidence_count > 0 and verified:
        return "direct"
    if related_evidence_count > 0 or analogical_evidence_count > 0:
        return "contextual"
    if legal_analysis_exists:
        return "limited"
    return "unavailable"


def _answer_requires_confidence_gating(meta: Dict[str, Any]) -> bool:
    if str(meta.get("answer_certainty_level") or "") != "direct":
        return True
    state = str(meta.get("source_panel_state") or "")
    if state in {SOURCE_PANEL_STRUCTURED_FALLBACK_AVAILABLE, SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE, SOURCE_PANEL_LIVE_LAW_LOOKUP_TECHNICAL_ISSUE, SOURCE_PANEL_NO_DIRECT_AUTHORITY_FOUND}:
        return True
    err = str(meta.get("law_lookup_error_type") or "").upper()
    return bool(err in {"LAW_API_BAD_RESPONSE", "SOURCE_UNAVAILABLE", "BAD_RESPONSE", "SOURCE_UNAVAILABLE"})


def _confidence_gate_answer_text(answer: str, meta: Dict[str, Any]) -> str:
    """Soften unsafe deterministic/LLM wording when direct authority is absent."""
    if not answer or not _answer_requires_confidence_gating(meta):
        return answer
    facts = meta.get("immigration_facts") if isinstance(meta.get("immigration_facts"), dict) else {}
    current_status = facts.get("current_status") or meta.get("visa_code_detected") or "현재 체류자격"
    previous_status = facts.get("previous_status")
    target_status = facts.get("target_status")
    activities = facts.get("proposed_activities") or meta.get("proposed_activity_type") or []
    activity_text = ", ".join(str(a) for a in activities if a) or "해당 활동"
    route_text = f"{previous_status}에서 {current_status}" if previous_status else str(current_status)
    if target_status and target_status != current_status:
        route_text = f"{current_status}에서 {target_status}"
    replacement = (
        f"{route_text} 맥락에서는 {activity_text}을(를) 이전 자격 기준만으로 단정하지 말고 "
        f"{current_status}의 활동범위, 승인 조건, 신고·허가 대상 여부를 기준으로 다시 확인해야 합니다. "
        "종전 자격의 의무가 자동으로 계속 적용되거나 소멸한다고 단정하려면 직접 공식 근거와 개별 승인 조건 확인이 필요합니다."
    )
    risky_patterns = [
        r"체류자격이\s*[A-H]-?\d{1,2}(?:-\d{1,3})?.{0,40}?[A-H]-?\d{1,2}(?:-\d{1,3})?.{0,80}?더\s*이상\s*적용되지\s*않습니다\. ?",
        r"원칙적으로\s*이전\s*자격.{0,100}?더\s*이상\s*적용되지\s*않습니다\. ?",
        r"previous\s+status.{0,100}?(?:no\s+longer|does\s+not)\s+apply\. ?",
    ]
    out = answer
    for pat in risky_patterns:
        out = re.sub(pat, replacement + " ", out)
    softeners = {
        "신고 의무는 없습니다": "신고 의무가 없는지 단정하려면 현재 승인 조건과 활동 형태 확인이 필요합니다",
        "반드시 신고해야 합니다": "신고 대상인지 여부는 현재 승인 조건과 활동 형태에 따라 확인해야 합니다",
        "허용됩니다": "허용 여부를 확인해야 합니다",
        "가능합니다": "가능 여부를 확인해야 합니다",
    }
    for risky, soft in softeners.items():
        if risky in out:
            out = out.replace(risky, soft)
    return out


def _case_law_uncertainty_answer(*, lang: Optional[str] = None) -> str:
    if str(lang or "").lower().startswith("en"):
        return (
            "I cannot verify a specific case-law or decision citation from the retrieved official evidence for this question. "
            "Use this as general preparation guidance only, and confirm the remedy, deadline, and filing path with HiKorea, 1345, "
            "the competent immigration office, or a qualified professional before relying on it."
        )
    return (
        "이 질문에 대해 특정 판례·재결·결정 번호나 판시 내용을 확인할 수 있는 공식 근거가 확보되지 않았습니다. "
        "따라서 판례 인용 없이 일반 준비 안내로만 보아야 하며, 구제절차·기한·제출 경로는 HiKorea, 1345, "
        "관할 출입국·외국인관서 또는 자격 있는 전문가에게 확인하세요."
    )


def _collect_law_evidence_texts(
    law_evidence_pack: Optional[Dict[str, Any]],
    grounding_sources: Optional[List[Dict[str, Any]]],
    structured_block: str,
) -> List[str]:
    """Gather the local/official evidence text a citation could legitimately come
    from (manual grounding, the law evidence pack, source-confirmed structured
    requirements). Used to tell a backed citation from a hallucinated one."""
    texts: List[str] = []
    pack = law_evidence_pack or {}
    if pack.get("evidence_summary"):
        texts.append(str(pack.get("evidence_summary")))
    for src in pack.get("law_sources", []) or []:
        if isinstance(src, dict):
            texts.append(" ".join(str(src.get(k) or "") for k in ("law_name", "article", "title", "summary")))
    for src in grounding_sources or []:
        if isinstance(src, dict):
            texts.append(" ".join(str(v) for v in src.values() if isinstance(v, str)))
    if structured_block:
        texts.append(str(structured_block))
    return texts


def _apply_law_citation_guard(
    answer: str,
    *,
    law_grounding_verified: bool,
    law_evidence_pack: Optional[Dict[str, Any]],
    grounding_sources: Optional[List[Dict[str, Any]]],
    structured_block: str,
    lang: Optional[str],
) -> tuple:
    """Run the unverified-citation guardrail and return (answer, guard_meta)."""
    evidence_texts = _collect_law_evidence_texts(law_evidence_pack, grounding_sources, structured_block)
    guarded = guard_answer_citations(
        answer,
        law_grounding_verified=law_grounding_verified,
        evidence_texts=evidence_texts,
        lang=lang,
    )
    new_answer = guarded.pop("answer")
    # Keep the copy-safe mirror in sync with the (possibly augmented) answer.
    guarded["copy_safe_answer"] = new_answer
    return new_answer, guarded


def _derive_source_panel_metadata(
    *,
    law_evidence_pack: Optional[Dict[str, Any]],
    citation_verification: Optional[Dict[str, Any]],
    law_grounding_used: bool,
    law_grounding_attempted: bool,
    law_grounding_status: str,
    law_grounding_warnings: Optional[List[str]],
    manual_grounding_status: str,
    deterministic_fallback_answer_used: bool = False,
    fallback_answer_kind: str = "",
) -> Dict[str, Any]:
    pack = law_evidence_pack or {}
    legal_analysis = pack.get("legal_analysis") if isinstance(pack.get("legal_analysis"), dict) else None
    legal_analysis_exists = bool(legal_analysis)
    direct_count = int(pack.get("direct_evidence_count") or 0)
    related_count = int(pack.get("related_evidence_count") or 0)
    analogical_count = int(pack.get("analogical_evidence_count") or 0)
    law_evidence_count = int(pack.get("law_evidence_count") or 0)
    law_lookup_error_type = _derive_law_lookup_error_type(pack, citation_verification, law_grounding_warnings, pack.get("law_grounding_error", ""))
    citation_status = str((citation_verification or {}).get("status") or "")

    law_lookup_failed = bool(law_lookup_error_type) or law_grounding_status in {"unavailable", "disabled"} or (law_grounding_attempted and not law_grounding_used)
    direct_citation_available = citation_status == "verified"
    direct_authority_available = direct_count > 0 and direct_citation_available
    manual_available = manual_grounding_status in {"manual_grounding_available", "present"}
    law_available = law_evidence_count > 0 or bool(pack.get("law_sources"))
    has_lookup_issue = law_lookup_failed
    answer_certainty_level = _derive_answer_certainty_level(
        direct_evidence_count=direct_count,
        related_evidence_count=related_count,
        analogical_evidence_count=analogical_count,
        legal_analysis_exists=legal_analysis_exists,
        citation_status=citation_status,
        law_lookup_failed=law_lookup_failed,
    )

    if direct_authority_available:
        state = SOURCE_PANEL_DIRECT_SOURCE_VERIFIED
    elif deterministic_fallback_answer_used and legal_analysis_exists:
        state = SOURCE_PANEL_STRUCTURED_FALLBACK_AVAILABLE
    elif legal_analysis_exists and has_lookup_issue and (direct_count == 0 or pack.get("missing_direct_authority", True)):
        state = SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE
    elif manual_available:
        state = SOURCE_PANEL_MANUAL_GROUNDING_AVAILABLE
    elif law_available and not has_lookup_issue:
        state = SOURCE_PANEL_LAW_GROUNDING_AVAILABLE
    elif legal_analysis_exists and has_lookup_issue:
        state = SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE
    elif legal_analysis_exists and (related_count > 0 or analogical_count > 0):
        state = SOURCE_PANEL_RELATED_LEGAL_CONTEXT_AVAILABLE
    elif legal_analysis_exists:
        state = SOURCE_PANEL_STRUCTURED_LEGAL_ANALYSIS_AVAILABLE
    elif law_grounding_attempted and has_lookup_issue:
        state = SOURCE_PANEL_LIVE_LAW_LOOKUP_TECHNICAL_ISSUE
    elif pack.get("missing_direct_authority"):
        state = SOURCE_PANEL_NO_DIRECT_AUTHORITY_FOUND
    else:
        state = SOURCE_PANEL_SOURCE_UNAVAILABLE

    return {
        "source_panel_state": state,
        "source_panel_label_key": _source_panel_label_key(state, legal_analysis_exists=legal_analysis_exists, law_lookup_error_type=law_lookup_error_type),
        "legal_analysis_exists": legal_analysis_exists,
        "law_lookup_error_type": law_lookup_error_type,
        "default_source_panel_should_show_raw_codes": False,
        "source_panel_confidence": {"direct": "high", "contextual": "moderate", "limited": "low", "unavailable": "none"}.get(answer_certainty_level, "none"),
        "direct_authority_available": direct_authority_available,
        "direct_citation_available": direct_citation_available,
        "legal_analysis_available": legal_analysis_exists,
        "law_lookup_failed": law_lookup_failed,
        "citation_verification_status": citation_status,
        "manual_grounding_status_detail": manual_grounding_status,
        "answer_certainty_level": answer_certainty_level,
    }

class JobCodeKeywordsRequest(BaseModel):
    query: str = Field(..., min_length=1)


class JobCodeKeywordsResponse(BaseModel):
    query: str
    keywords: List[str]


class DebugLawGroundingRequest(BaseModel):
    question: Optional[str] = None
    text: Optional[str] = None
    visa_code: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _providers_configured() -> Dict[str, bool]:
    # law_api reflects the EFFECTIVE Open Law API credential (preferred
    # LAW_API_OC, or the legacy LAW_API_KEY fallback) read live, so the flag is
    # accurate when only LAW_API_OC is set. The value itself is never exposed.
    try:
        law_api_configured = load_grounding_config().law_api_configured
    except Exception:  # pragma: no cover - defensive
        law_api_configured = bool(LAW_API_KEY)
    return {
        "openrouter": bool(OPENROUTER_API_KEY),
        "groq": bool(GROQ_API_KEY),
        "law_api": law_api_configured,
        "ollama": bool(ENABLE_OLLAMA_FALLBACK and OLLAMA_BASE_URL),
        "database": bool(DATABASE_URL),
        "supabase": bool(SUPABASE_URL and SUPABASE_SERVICE_KEY),
    }


def _groq_fallback_warnings(provider: str) -> List[str]:
    """Non-secret advisory markers about Groq fallback posture.

    Strict OpenRouter-first is the intended production posture. These markers
    let /health and the debug endpoint flag when the silent-provider-switch
    path is armed (``GROQ_FALLBACK_ENABLED``) or actually selected
    (``GROQ_FALLBACK_ACTIVE``) without ever exposing a key value.
    """
    warnings: List[str] = []
    if ALLOW_GROQ_FALLBACK:
        warnings.append("GROQ_FALLBACK_ENABLED")
    if provider == "groq":
        warnings.append("GROQ_FALLBACK_ACTIVE")
    return warnings


def _resolve_llm_config() -> Dict[str, Any]:
    """Resolve the active LLM provider + model without exposing any secret.

    Precedence:
      1. OpenRouter, whenever OPENROUTER_API_KEY is set (model = OPENROUTER_MODEL).
      2. Groq, only if OpenRouter is unset, Groq key is present, AND
         ALLOW_GROQ_FALLBACK is true (model = GROQ_MODEL). This is opt-in: the
         default for ALLOW_GROQ_FALLBACK is now false, so a Groq-only deployment
         must set it explicitly.
      3. Otherwise no provider is configured (strict OpenRouter-first intent).

    Returns only non-sensitive descriptors (provider name, model id, flags,
    advisory warnings). Model ids (e.g. ``google/gemma-4-31b-it:free``) are
    public catalog identifiers, not secrets, so they are safe to surface on
    /health. ``warnings`` never contains key material.
    """
    model_role_policy = sanitize_model_role_policy_for_public()
    if OPENROUTER_API_KEY:
        return {
            "provider": "openrouter",
            "model": OPENROUTER_MODEL,
            "configured": True,
            "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
            "warnings": _groq_fallback_warnings("openrouter"),
            "model_policy_version": MODEL_POLICY_VERSION,
            "model_role_policy": model_role_policy,
        }
    if GROQ_API_KEY and ALLOW_GROQ_FALLBACK:
        return {
            "provider": "groq",
            "model": GROQ_MODEL,
            "configured": True,
            "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
            "warnings": _groq_fallback_warnings("groq"),
            "model_policy_version": MODEL_POLICY_VERSION,
            "model_role_policy": model_role_policy,
        }
    return {
        "provider": "none",
        "model": None,
        "configured": False,
        "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
        "warnings": _groq_fallback_warnings("none"),
            "model_policy_version": MODEL_POLICY_VERSION,
            "model_role_policy": model_role_policy,
    }


def _extract_keywords(text: str, max_keywords: int = 12) -> List[str]:
    """Best-effort keyword extraction without external dependencies.

    Splits on non-word characters, lowercases, drops short tokens and a
    small Korean/English stopword set, and de-duplicates while keeping
    insertion order.
    """
    import re

    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "into",
        "have", "has", "are", "was", "were", "you", "your", "but", "not",
        "위해", "그리고", "있는", "있습니다", "관련", "대한",
    }
    tokens = re.split(r"[^0-9A-Za-z가-힣]+", text or "")
    seen: List[str] = []
    for token in tokens:
        token = token.strip().lower()
        if not token or len(token) < 2 or token in stopwords:
            continue
        if token in seen:
            continue
        seen.append(token)
        if len(seen) >= max_keywords:
            break
    return seen


# ---------------------------------------------------------------------------
# Waymaker governance system prompt
# ---------------------------------------------------------------------------
# Sent as the system role on EVERY LLM call (OpenRouter / Groq / Ollama, buffered
# and streamed). It is additive to the per-request grounding/answer-shape
# directives already built into the user prompt — it never removes or weakens
# them. It reinforces official-source-only grounding, no-guarantee language,
# refusal of deceptive/fraudulent help, refugee-question neutrality, and the
# information-vs-advice distinction, consistent with CLAUDE.md's constraints.
WAYMAKER_SYSTEM_PROMPT = (
    "You are Waymaker by Paradiso, an official-source-grounded Korean visa, "
    "residence, immigration, and document guidance assistant.\n\n"
    "Core rules:\n"
    "1. Answer only within the scope of official sources retrieved by the system, "
    "including Korean immigration manuals, statutes, regulations, official government "
    "pages, visa portal materials, embassy/consulate notices, recognized legal "
    "decisions, and trusted international protection sources such as UNHCR where "
    "relevant.\n"
    "2. Do not rely on the model's general memory for current visa, residence, "
    "refugee, or immigration rules.\n"
    "3. If official evidence is missing, incomplete, outdated, or conflicting, state "
    "the limitation clearly and do not infer a definitive answer.\n"
    "4. Never guarantee approval, recognition, issuance, extension, permission, or "
    "acceptance.\n"
    "5. Never provide strategies to deceive, misrepresent, conceal facts, fabricate "
    "evidence, forge documents, evade immigration control, work without "
    "authorization, or exploit procedural loopholes.\n"
    "6. For refugee/asylum-related questions, do not advise users on how to be "
    "recognized as a refugee, which grounds to claim, what story to tell, what facts "
    "to emphasize or hide, or how to pass an interview. Provide only neutral "
    "procedural information, official document categories, truthful fact-organization "
    "assistance, and referrals to qualified legal or protection support.\n"
    "7. When helping draft or translate applications, statements, explanations, or "
    "letters, use only facts provided by the user. Do not invent dates, places, "
    "incidents, threats, relationships, documents, diagnoses, affiliations, or "
    "evidence.\n"
    "8. If the user asks for high-risk help, refuse briefly and redirect to lawful, "
    "truthful, official-source-based alternatives.\n"
    "9. Distinguish legal information from legal advice. For individualized legal "
    "judgment, litigation, appeals, refugee credibility issues, or severe "
    "consequences, recommend contacting a qualified lawyer, legal aid organization, "
    "UNHCR-related support channel, or the competent immigration office.\n"
    "10. Always produce structured outputs suitable for UI cards when requested: "
    "summary, applicable status, required documents, steps, caveats, official "
    "sources, and confidence level."
)


def _llm_messages(prompt: str) -> List[Dict[str, str]]:
    """Chat messages for an LLM call: the Waymaker governance system prompt first,
    then the fully-built (grounded + answer-shaped) user prompt. Shared by every
    provider/path so the governance instruction is applied uniformly."""
    return [
        {"role": "system", "content": WAYMAKER_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


async def _call_openrouter(
    prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None
) -> str:
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "openrouter_not_configured",
                "message": "OPENROUTER_API_KEY is not set on the server.",
            },
        )
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "httpx_missing", "message": "httpx is not installed."},
        )

    payload: Dict[str, Any] = {
        "model": model or OPENROUTER_MODEL,
        "messages": _llm_messages(prompt),
    }
    effective_max_tokens = OPENROUTER_MAX_TOKENS if max_tokens is None else max_tokens
    if effective_max_tokens and effective_max_tokens > 0:
        payload["max_tokens"] = int(effective_max_tokens)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if SITE_URL:
        headers["HTTP-Referer"] = SITE_URL
    if SITE_TITLE:
        headers["X-Title"] = SITE_TITLE
    try:
        async with httpx.AsyncClient(timeout=OPENROUTER_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        # A hung/slow provider must surface as a *retryable* upstream timeout
        # (status 504 classifies as upstream_unavailable) so the candidate loop
        # marks the model cooling-down and falls through to the next candidate
        # and, ultimately, the deterministic source-grounded preparation note.
        raise HTTPException(
            status_code=504,
            detail={
                "error": "openrouter_timeout",
                "status": 504,
                "message": f"OpenRouter request timed out after {OPENROUTER_TIMEOUT_SECONDS:.0f}s: {str(exc)[:200]}",
            },
        )
    except httpx.HTTPError as exc:
        # Connection/transport-level failures (DNS, refused, reset) are also
        # transient upstream unavailability — keep them retryable, never a 500.
        raise HTTPException(
            status_code=503,
            detail={
                "error": "openrouter_network_error",
                "status": 503,
                "message": f"OpenRouter request failed: {str(exc)[:200]}",
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openrouter_upstream_error",
                "status": resp.status_code,
                "message": resp.text[:500],
            },
        )
    try:
        data = resp.json()
    except ValueError:
        # A 2xx response with a non-JSON body is an upstream contract
        # violation. Parsing used to happen OUTSIDE any guard, so it surfaced
        # as a bare 500 without CORS headers; keep it a structured 502 like
        # the malformed-payload path below so the candidate loop / frontend
        # error cards handle it normally.
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openrouter_bad_response",
                "status": 502,
                "message": "OpenRouter returned a non-JSON response body.",
            },
        )
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openrouter_bad_response",
                "message": f"Unexpected OpenRouter payload: {exc}",
            },
        )
    if not isinstance(content, str) or not content.strip():
        # `content: null` (or empty) is valid JSON but unusable: it used to
        # flow into AskResponse(answer=None) and crash with a 500-producing
        # ValidationError. A retryable 502 lets the candidate loop try the
        # next model and, ultimately, the deterministic fallback note.
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openrouter_empty_completion",
                "status": 502,
                "message": "OpenRouter returned an empty completion.",
            },
        )
    return content


async def _call_groq(prompt: str, model: Optional[str] = None) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "groq_not_configured",
                "message": "GROQ_API_KEY is not set on the server.",
            },
        )
    if httpx is None:
        raise HTTPException(
            status_code=500,
            detail={"error": "httpx_missing", "message": "httpx is not installed."},
        )

    payload = {
        "model": model or GROQ_MODEL,
        "messages": _llm_messages(prompt),
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=OPENROUTER_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        # Groq is only ever an explicitly-enabled provider-family fallback; a
        # timeout/transport failure here must stay a clean HTTPException so the
        # caller (try/except HTTPException) drops to the deterministic note
        # rather than crashing /api/ask with an uncaught 500.
        is_timeout = isinstance(exc, httpx.TimeoutException)
        raise HTTPException(
            status_code=504 if is_timeout else 503,
            detail={
                "error": "groq_timeout" if is_timeout else "groq_network_error",
                "status": 504 if is_timeout else 503,
                "message": f"Groq request failed: {str(exc)[:200]}",
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "groq_upstream_error",
                "status": resp.status_code,
                "message": resp.text[:500],
            },
        )
    try:
        data = resp.json()
    except ValueError:
        # Same guard as _call_openrouter: a 2xx non-JSON body must be a
        # structured 502 (CORS + friendly error card), never a bare 500.
        raise HTTPException(
            status_code=502,
            detail={
                "error": "groq_bad_response",
                "status": 502,
                "message": "Groq returned a non-JSON response body.",
            },
        )
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "groq_bad_response",
                "message": f"Unexpected Groq payload: {exc}",
            },
        )
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(
            status_code=502,
            detail={
                "error": "groq_empty_completion",
                "status": 502,
                "message": "Groq returned an empty completion.",
            },
        )
    return content


# ---------------------------------------------------------------------------
# OpenRouter provider-error classification + candidate fallback
# ---------------------------------------------------------------------------

# Retryable classes trigger the NEXT OpenRouter candidate; non-retryable classes
# stop the candidate loop (the failure is not transient/model-specific load).
_RETRYABLE_PROVIDER_ERROR_TYPES = {
    "rate_limited",
    "upstream_unavailable",
    "provider_unavailable",
}

# Model-SPECIFIC failures: the failure is tied to ONE model id (a bad/unknown
# slug, or "no endpoints"/"no allowed providers" for a free model that has no
# capacity right now). These are not transient in a way that benefits from a
# cooldown retry of the SAME model, but they must NOT abort the whole request:
# the candidate loop skips to the NEXT candidate instead of breaking, so one bad
# model id can never sink an otherwise-answerable request (this is what made
# Basic mode return only a fallback note while Fast mode worked).
_PER_MODEL_SKIP_ERROR_TYPES = {
    "model_not_found",
}


def _classify_openrouter_error(
    status: Optional[int], message: Optional[str], error_code: Optional[str] = None
) -> tuple:
    """Map an OpenRouter failure to ``(error_type, retryable)`` — no secrets.

    ``status`` is the upstream HTTP status (e.g. 429/503) when known; ``message``
    is sanitized provider text. The observed production failure (503 with
    "no healthy upstream", preceded by a Google AI Studio 429) classifies as a
    retryable ``upstream_unavailable`` / ``rate_limited`` error.
    """
    msg = (message or "").lower()
    code = (error_code or "").lower()
    try:
        status_int = int(status) if status is not None else None
    except (TypeError, ValueError):
        status_int = None

    if (
        status_int == 429
        or "rate limit" in msg
        or "rate-limit" in msg
        or "too many requests" in msg
        or "quota" in msg
        or "429" in msg
    ):
        return "rate_limited", True
    if (
        status_int in (502, 503, 504)
        or "no healthy upstream" in msg
        or "no instances available" in msg
        or "overloaded" in msg
        or "temporarily unavailable" in msg
        or "service unavailable" in msg
        or "bad gateway" in msg
    ):
        return "upstream_unavailable", True
    if "timeout" in msg or "timed out" in msg or code == "timeout":
        return "upstream_unavailable", True
    # Auth / config: affects every candidate -> do not retry.
    if (
        status_int in (401, 403)
        or "invalid api key" in msg
        or "unauthorized" in msg
        or "no auth credentials" in msg
        or "authentication" in msg
    ):
        return "invalid_provider_config", False
    # Model-specific: bad/unknown slug, or no available provider/endpoint for
    # this model right now. Not retryable on the SAME model, but the candidate
    # loop skips to the NEXT candidate (see _PER_MODEL_SKIP_ERROR_TYPES) so a
    # single bad model id never aborts the whole request.
    if (
        status_int == 404
        or "not found" in msg
        or "no endpoints" in msg
        or "no allowed providers" in msg
        or "no endpoints found" in msg
        or "unknown model" in msg
        or "not a valid model" in msg
    ):
        return "model_not_found", False
    # Safety / moderation / policy rejection.
    if (
        status_int == 451
        or "moderation" in msg
        or "flagged" in msg
        or "safety" in msg
        or "content policy" in msg
        or "content filter" in msg
    ):
        return "policy_or_safety_rejection", False
    # Bad request / validation / malformed payload.
    if (
        status_int == 400
        or code == "openrouter_bad_response"
        or "bad request" in msg
        or "invalid request" in msg
        or "validation" in msg
    ):
        return "invalid_request", False
    # Other 5xx without a clearer reason -> retryable provider unavailability.
    if status_int is not None and status_int >= 500:
        return "provider_unavailable", True
    return "unknown_provider_error", False


def _now() -> float:
    return time.time()


def _cooldown_enabled() -> bool:
    return OPENROUTER_MODEL_COOLDOWN_SECONDS > 0


def _cooling_down_models(now: Optional[float] = None) -> List[str]:
    if not _cooldown_enabled():
        return []
    ts = _now() if now is None else now
    expired = [
        model for model, failed_at in _OPENROUTER_MODEL_COOLDOWNS.items()
        if ts - failed_at >= OPENROUTER_MODEL_COOLDOWN_SECONDS
    ]
    for model in expired:
        _OPENROUTER_MODEL_COOLDOWNS.pop(model, None)
    return [
        model for model, failed_at in _OPENROUTER_MODEL_COOLDOWNS.items()
        if ts - failed_at < OPENROUTER_MODEL_COOLDOWN_SECONDS
    ]


def _mark_openrouter_model_cooling_down(model: str, now: Optional[float] = None) -> None:
    if not model or not _cooldown_enabled():
        return
    _OPENROUTER_MODEL_COOLDOWNS[model] = _now() if now is None else now


def _reset_openrouter_model_cooldowns_for_tests() -> None:
    _OPENROUTER_MODEL_COOLDOWNS.clear()


def _openrouter_cooldown_metadata() -> Dict[str, Any]:
    return {
        "cooling_down_models": _cooling_down_models(),
        "model_cooldown_seconds": OPENROUTER_MODEL_COOLDOWN_SECONDS,
        "cooldown_enabled": _cooldown_enabled(),
    }


async def _call_ollama(prompt: str, model: Optional[str] = None) -> str:
    """Disabled-by-default private Ollama fallback adapter.

    This helper is only called when ENABLE_OLLAMA_FALLBACK=true and OpenRouter
    candidates have already failed. It never runs during /health and tests mock
    it, so CI does not need a live Ollama server.
    """
    if not ENABLE_OLLAMA_FALLBACK:
        raise HTTPException(status_code=503, detail={"error": "ollama_disabled"})
    if httpx is None:
        raise HTTPException(status_code=500, detail={"error": "httpx_missing"})
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": _llm_messages(prompt),
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                OLLAMA_BASE_URL.rstrip("/") + "/api/chat",
                json=payload,
            )
    except Exception as exc:  # httpx timeout/connect errors are optional-fallback only
        name = exc.__class__.__name__.lower()
        err = "ollama_timeout" if "timeout" in name else "ollama_unavailable"
        raise HTTPException(status_code=503, detail={"error": err, "message": str(exc)[:200]})
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=503,
            detail={"error": "ollama_unavailable", "status": resp.status_code, "message": resp.text[:200]},
        )
    try:
        data = resp.json()
        content = data.get("message", {}).get("content") or data.get("response")
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass
    raise HTTPException(status_code=502, detail={"error": "ollama_bad_response"})


def _classify_ollama_error(exc: HTTPException) -> str:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = str(detail.get("error") or "").strip()
    if code in {"ollama_unavailable", "ollama_timeout", "ollama_bad_response", "ollama_disabled"}:
        return code
    if exc.status_code == 504:
        return "ollama_timeout"
    return "ollama_unavailable"


def _legal_analysis_facts_for_answer(base_meta: Dict[str, Any], legal_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(legal_analysis, dict):
        facts = legal_analysis.get("immigration_facts")
        if isinstance(facts, dict):
            merged = dict(base_meta.get("immigration_facts") or {})
            merged.update({k: v for k, v in facts.items() if v not in (None, "", [], {})})
            return merged
    return dict(base_meta.get("immigration_facts") or {})


def _issue_labels_for_fallback(issues: List[str], *, is_ko: bool) -> List[str]:
    labels_ko = {
        "activity_scope": "현재 체류자격의 활동범위",
        "outside_status_activity": "자격외활동 허가 필요성",
        "status_change": "체류자격 변경 경로",
        "extension": "체류기간 연장",
        "documents_needed": "공식 매뉴얼 기준 서류 확인",
        "reporting_duty": "신고의무",
        "workplace_change_addition": "근무처 변경·추가 신고/허가",
        "registration_or_residence_report": "외국인등록·거소신고 등 체류 신고",
        "registration_deadline": "외국인등록 기한",
        "deadline_trigger": "신고 기산일",
        "reentry": "재입국·출국 절차",
        "overstay_or_risk": "초과체류 등 체류 위험",
        "approval_condition": "개별 승인 조건",
        "status_purpose_alignment": "체류 목적과 활동의 정합성",
        "employment_restriction": "취업 제한",
        "study_on_non_study_status": "비유학 체류자격에서의 수학 활동",
        "work_on_non_work_status": "비취업·제한 체류자격에서의 근로/사업 활동",
        "post_status_change_residual_duty": "체류자격 변경 후 이전 자격 관련 잔존 신고 쟁점",
        "nationality_or_refugee_context": "국적·난민 관련 체류 맥락",
        "legal_general": "일반 법률 쟁점",
        "non_immigration_adjacent_issue": "인접 쟁점",
    }
    labels_en = {
        "activity_scope": "current-status activity scope",
        "outside_status_activity": "activities outside status / permission risk",
        "status_change": "status-change route",
        "extension": "extension procedure",
        "documents_needed": "official-manual document checklist boundary",
        "reporting_duty": "reporting duty",
        "workplace_change_addition": "workplace change/addition reporting or permission",
        "registration_or_residence_report": "alien registration / residence reporting",
        "registration_deadline": "alien-registration deadline",
        "deadline_trigger": "deadline trigger",
        "reentry": "re-entry or departure procedure",
        "overstay_or_risk": "overstay/status-risk triage",
        "approval_condition": "case-specific approval conditions",
        "status_purpose_alignment": "alignment with the purpose of stay",
        "employment_restriction": "employment restrictions",
        "study_on_non_study_status": "study activity on a non-study status",
        "work_on_non_work_status": "work or business activity on a non-work/restricted status",
        "post_status_change_residual_duty": "residual duty after a status change",
        "nationality_or_refugee_context": "nationality/refugee residence context",
        "legal_general": "general legal issue",
        "non_immigration_adjacent_issue": "adjacent issue",
    }
    labels = labels_ko if is_ko else labels_en
    return [labels.get(issue, issue.replace("_", " ")) for issue in issues if issue][:6]


def _activity_labels_for_fallback(activities: List[str], *, is_ko: bool) -> List[str]:
    labels_ko = {
        "credit_bearing_study": "학점 인정 수업",
        "formal_enrollment": "학교 등록/정규 수학",
        "non_credit_audit": "청강/비학점 수강",
        "non_credit_cultural_or_hobby": "취미·문화 비학점 활동",
        "language_training": "어학연수/한국어 수업",
        "paid_work": "보수 있는 근로",
        "unpaid_internship": "무급 인턴",
        "paid_internship": "유급 인턴",
        "freelance_work": "프리랜서/외주",
        "side_job": "부업",
        "additional_employment": "추가 고용",
        "business_activity": "사업활동/사업자등록",
        "workplace_change": "근무처 변경",
        "workplace_addition": "근무처 추가",
        "registration_or_reporting": "외국인등록·신고",
        "status_change_route": "체류자격 변경",
    }
    labels_en = {k: k.replace("_", " ") for k in [
        "credit_bearing_study", "formal_enrollment", "non_credit_audit", "non_credit_cultural_or_hobby",
        "language_training", "paid_work", "unpaid_internship", "paid_internship", "freelance_work",
        "side_job", "additional_employment", "business_activity", "workplace_change", "workplace_addition",
        "registration_or_reporting", "status_change_route",
    ]}
    labels = labels_ko if is_ko else labels_en
    return [labels.get(activity, activity.replace("_", " ")) for activity in activities if activity][:6]


def _localized_source_boundary_note(*, is_ko: bool, source_state: str, legal_analysis: Dict[str, Any]) -> str:
    confidence = legal_analysis.get("confidence") or "limited"
    missing_direct = bool(legal_analysis.get("missing_direct_authority"))
    if is_ko:
        if source_state in {"source_unavailable", "unavailable", "disabled"}:
            return "출처 조회가 제한되었지만, 추출된 사실관계와 법률 쟁점 구조를 기준으로 준비 메모를 표시합니다."
        if missing_direct:
            return "직접적인 사안별 근거가 충분하지 않을 수 있어, 이 메모는 확인 질문과 쟁점 정리에 초점을 둡니다."
        return f"확인된 근거 수준은 {confidence}이며, 최종 판단은 관할 기관 확인이 필요합니다."
    if source_state in {"source_unavailable", "unavailable", "disabled"}:
        return "Source lookup is limited, but Paradiso can still organize the extracted facts and legal issues into a preparation note."
    if missing_direct:
        return "Direct scenario-specific authority may be limited, so this note focuses on the issues and facts to confirm."
    return f"The available source confidence is {confidence}; final outcomes still require competent-office confirmation."




def _is_work_limited_status(facts: Dict[str, Any]) -> bool:
    parent = facts.get("current_parent_status") or facts.get("current_status")
    return status_work_capability(parent) == "work_limited"


def _format_korean_iso_date(value: Any) -> str:
    text = str(value or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not m:
        return text
    return f"{int(m.group(1))}년 {int(m.group(2))}월 {int(m.group(3))}일"


def _format_registration_deadline_formula(facts: Dict[str, Any], *, is_ko: bool) -> Optional[str]:
    entry_date = facts.get("entry_date")
    deadline = facts.get("registration_deadline_date")
    if not entry_date or not deadline:
        return None
    status = facts.get("current_status") or ("현재 체류자격" if is_ko else "the current status")
    if is_ko:
        return (
            f"결론: {status} 외국인등록 기한은 입국일 {entry_date}에 90일을 더해 계산하면 "
            f"{deadline}({_format_korean_iso_date(deadline)})입니다."
        )
    return (
        f"Bottom line: for {status} alien registration, adding 90 calendar days "
        f"to the entry date {entry_date} gives a deadline of {deadline}."
    )


def _korean_practical_fallback(issues: List[str], facts: Dict[str, Any], activities: List[str], activity_labels: List[str]) -> str:
    current = facts.get("current_status") or "현재 체류자격"
    previous = facts.get("previous_status")
    target = facts.get("target_status")
    if "post_status_change_residual_duty" in issues and previous:
        return f"현재 {current}의 활동범위와 승인 조건을 먼저 보되, 이전 {previous} 승인 조건·신고 이력이 현재 활동 판단에 관련 사실로 남는지 확인해야 합니다."
    if "status_change" in issues and target:
        return f"{current}에서 {target}로의 체류자격 변경 가능성과 국내 변경 절차를 목표 자격 기준으로 검토해야 합니다."
    if "study_on_non_study_status" in issues:
        acts = ", ".join(activity_labels) or "수학 활동"
        return f"{current}에서 {acts}이/가 현재 체류 목적과 활동범위 안에 들어가는지, 또는 자격외활동허가나 체류자격 변경이 필요한지 확인해야 합니다."
    if "employment_restriction" in issues and _is_work_limited_status(facts):
        # Work-limited statuses (H-1 Working Holiday 등): paid work is not
        # automatically an outside-status violation. Distinguish job type and
        # duration rather than treating any compensation as a high-risk activity.
        return (
            f"{current}은(는) 체류 목적과 국가별 협정 한도 안에서 단기 취업이 일부 허용될 수 있는 체류자격이므로, "
            "보수를 받는다는 사실만으로 곧바로 자격외활동 위반이 되는 것은 아닙니다. 다만 일의 형태(예: 단기 일반 "
            "통역·번역 보조 / 장기·전임 전문 통역사 취업 / 관광통역안내(가이드) / 외국어 교습·강의)와 근무 기간, "
            "국가별 협정 조건, 국내 자격·면허 요건, 주된 체류 목적 부합 여부에 따라 허용 범위가 달라지므로 이를 "
            "기준으로 확인해야 합니다."
        )
    if "registration_deadline" in issues and facts.get("entry_date") and facts.get("registration_deadline_date"):
        return _format_registration_deadline_formula(facts, is_ko=True) or ""
    if "workplace_change_addition" in issues:
        return (
            "근무처 변경·추가는 현재 E-7 세부자격과 직종, 새 사업장의 업종·직무, 기존 근로관계 종료일과 "
            "새 근무 시작일을 기준으로 사전 허가 대상인지 사후 신고 대상인지 먼저 구분해야 합니다. "
            "공식 확인 전에는 새 근무를 시작하지 않는 쪽이 안전합니다."
        )
    if "registration_or_residence_report" in issues:
        return (
            f"{current} 외국인등록은 보통 입국일 또는 체류자격 부여·변경일을 기준으로, 체류기간이 90일을 초과하는 "
            "경우 등록 대상이 되는 신고성 절차로 접근하는 것이 실무적입니다. 다만 정확한 등록 기한과 대상 여부는 "
            "개별 체류자격과 부여받은 체류기간에 따라 달라질 수 있으므로, 아래 사실관계를 먼저 확인해야 합니다."
        )
    if "reporting_duty" in issues:
        return "신고 대상 사건인지, 신고 기산일이 언제인지, 사전 허가가 필요한지부터 확인해야 합니다."
    return "추출된 체류자격, 활동 유형, 신고·허가 쟁점을 기준으로 공식 확인 질문을 준비해야 합니다."


def _korean_main_issue_fallback(issues: List[str], facts: Dict[str, Any], activity_labels: List[str]) -> str:
    current = facts.get("current_status") or "현재 체류자격"
    previous = facts.get("previous_status")
    target = facts.get("target_status")
    if "post_status_change_residual_duty" in issues and previous:
        return f"추가 활동이 현재 {current}의 활동범위, 승인 조건, 일반 신고/허가 의무와 충돌하는지, 그리고 이전 {previous} 관련 신고 의무가 잔존하는지입니다."
    if "status_change" in issues and target:
        return f"{current}에서 {target}로 국내 체류자격 변경을 신청할 수 있는 경로와 제한 조건입니다."
    if "study_on_non_study_status" in issues:
        acts = ", ".join(activity_labels) or "수학 활동"
        return f"{acts}이/가 {current}의 허용 활동범위 안인지, 아니면 자격외활동허가 또는 D-2/D-4 등 다른 체류자격 검토가 필요한지입니다."
    if "employment_restriction" in issues and _is_work_limited_status(facts):
        return (
            f"해당 일이 {current}에서 허용되는 단기 취업 범위에 들어가는지, 아니면 직종·근무 기간·국가별 협정 조건이나 "
            "국내 자격·면허 요건 때문에 제한되는지입니다."
        )
    if "registration_deadline" in issues and facts.get("entry_date") and facts.get("registration_deadline_date"):
        return f"{current} 보유자의 입국일 기준 외국인등록 기한 계산입니다."
    if "workplace_change_addition" in issues:
        return "현재 E-7 세부자격·직종과 새 사업장의 직무가 허용 범위에 맞는지, 그리고 근무 시작 전에 허가 또는 신고가 필요한지입니다."
    if "registration_or_residence_report" in issues:
        return f"{current} 보유자의 외국인등록·체류 신고 시점과 절차입니다."
    if "workplace_change_addition" in issues or "reporting_duty" in issues:
        return "해당 사실변경이 신고 대상인지, 근무처 변경·추가 또는 별도 허가 사안인지입니다."
    return "한국 출입국 체류 절차에서 어떤 공식 근거와 사실관계가 판단을 좌우하는지입니다."


_STUDY_ACTS = {
    "credit_bearing_study", "formal_enrollment", "non_credit_audit",
    "non_credit_cultural_or_hobby", "language_training",
}
_WORK_ACTS = {
    "paid_work", "paid_internship", "freelance_work", "side_job",
    "additional_employment", "business_activity", "workplace_change",
    "workplace_addition",
}


def _fallback_activity_kinds(issues: List[str], activities: List[str]) -> Dict[str, bool]:
    """Classify a fallback question into mutually-aware activity kinds.

    Used so the deterministic memo asks issue-appropriate facts/questions and
    never leaks study wording into a registration or side-job question (or vice
    versa).
    """
    issue_set = set(issues or [])
    act_set = set(activities or [])
    study = bool(act_set & _STUDY_ACTS) or "study_on_non_study_status" in issue_set
    work = bool(act_set & _WORK_ACTS) or bool(
        issue_set & {"work_on_non_work_status", "workplace_change_addition", "post_status_change_residual_duty"}
    )
    registration = bool(issue_set & {"registration_or_residence_report", "registration_deadline", "deadline_trigger"}) and not study and "workplace_change_addition" not in issue_set
    status_change = "status_change" in issue_set
    return {"study": study, "work": work, "registration": registration, "status_change": status_change}


def _fallback_fact_lines_localized(issues: List[str], facts: Dict[str, Any], activities: List[str], *, is_ko: bool) -> List[str]:
    """Issue-aware 'facts to confirm' bullets with natural-language labels.

    Replaces the internal snake_case ``decisive_facts`` list (current_status/
    sub_status, paid_or_credit_bearing, duration/employer_or_school, ...) so the
    user-facing memo never exposes backend field names (Part D / Part E).
    """
    kinds = _fallback_activity_kinds(issues, activities)
    work_limited = _is_work_limited_status(facts)
    lines: List[str] = []
    if is_ko:
        if kinds["study"]:
            lines.append("학점 인정 여부 또는 학위 과정 관련성")
            lines.append("수업 기간, 주당 시간, 학교 등록 방식")
        if kinds["work"] and work_limited:
            lines.append("국가별 워킹홀리데이·협정에서 정한 취업 가능 직종과 근무 기간·시간 제한")
            lines.append("일의 형태: 단기 일반 통역·번역 보조인지, 장기·전임 전문 통역사 취업인지, 관광통역안내(가이드)인지, 외국어 교습·강의인지")
            lines.append("관광통역안내사·교원 등 국내 자격·면허가 필요한 직종인지")
        elif kinds["work"]:
            lines.append("보수 발생 여부와 부업·근로 형태(고용/프리랜서/사업/단순 부수입)")
            lines.append("추가 고용주·사업자등록 여부, 업종·근무시간·계약형태")
        if "post_status_change_residual_duty" in set(issues or []):
            lines.append("이전 체류자격의 승인 조건과 신고 이력이 현재 활동에 남는지")
        if kinds["registration"]:
            if facts.get("entry_date"):
                deadline = facts.get("registration_deadline_date")
                if deadline:
                    lines.append(f"입국일 {facts.get('entry_date')} + 90일 = {deadline}({_format_korean_iso_date(deadline)})")
                else:
                    lines.append(f"입국일 {facts.get('entry_date')}을 기준으로 한 신고 기산일")
            else:
                lines.append("입국일 또는 체류자격 부여·변경일 등 신고 기산일")
            lines.append("부여받은 체류기간과 90일 초과 여부 등 외국인등록 대상·기한 기준")
            lines.append("신고 접수 방법(하이코리아 또는 관할 출입국·외국인청)")
        return list(dict.fromkeys(lines))[:6]
    if kinds["study"]:
        lines.append("whether the course is credit-bearing or degree-related")
        lines.append("the course duration, weekly hours, and how the school registers it")
    if kinds["work"] and work_limited:
        lines.append("the work types and the work-period/hour limits set by your nationality's working-holiday or agreement terms")
        lines.append("the work form: short-term general interpretation/translation help, long-term professional interpreter employment, tourist-guide interpretation, or foreign-language teaching")
        lines.append("whether the job needs a domestic license or qualification (e.g. tourist guide, teaching)")
    elif kinds["work"]:
        lines.append("whether it is paid and the work form (employment/freelance/business/incidental)")
        lines.append("any additional employer/business registration, industry, hours, and contract type")
    if "post_status_change_residual_duty" in set(issues or []):
        lines.append("whether the previous status's approval conditions or reporting history still apply")
    if kinds["registration"]:
        if facts.get("entry_date"):
            deadline = facts.get("registration_deadline_date")
            if deadline:
                lines.append(f"entry date {facts.get('entry_date')} + 90 calendar days = {deadline}")
            else:
                lines.append(f"the deadline trigger based on entry date {facts.get('entry_date')}")
        else:
            lines.append("the event that starts the deadline (entry date or status grant/change date)")
        lines.append("your granted period of stay and whether it exceeds the 90-day registration threshold")
        lines.append("the filing channel (HiKorea or the competent immigration office)")
    return list(dict.fromkeys(lines))[:6]


def _fallback_confirmation_questions_localized(issues: List[str], facts: Dict[str, Any], activities: List[str], *, is_ko: bool) -> List[str]:
    """Localized, issue-scoped official-confirmation questions for the memo.

    Korean questions stay Korean; English stays English (Part E). Unrelated
    deadline/address-change questions are only emitted for genuine
    registration/reporting issues (Part D). Returns ``[]`` when no issue-specific
    set applies, so the caller can fall back to existing localized questions.
    """
    issue_set = set(issues or [])
    kinds = _fallback_activity_kinds(issues, activities)
    work_limited = _is_work_limited_status(facts)
    current = facts.get("current_status") or ("현재 체류자격" if is_ko else "the current status")
    if is_ko:
        if "post_status_change_residual_duty" in issue_set:
            return [
                f"현재 ARC상 {current}인지",
                f"{current} 승인 조건",
                "부업 형태: 고용/프리랜서/사업/단순 부수입",
                "추가 고용주 또는 사업자등록 여부",
                "업종/근무시간/보수/계약형태",
                "출입국이 이를 근무처 추가, 신고 대상, 자격외활동, 또는 별도 제한으로 보는지",
            ]
        if kinds["study"]:
            return [
                f"현재 {current} 부여 사유가 무엇인지",
                "등록/청강/계절학기 중 어떤 활동인지",
                "학점 인정 또는 학위 과정 관련성이 있는지",
                "수업 기간과 주당 시간이 얼마인지",
                "학교가 D-2/D-4 등 유학 체류자격을 요구하는지",
                f"출입국이 이를 {current} 체류 목적과 양립 가능한 활동으로 보는지",
                "자격외활동허가 또는 체류자격 변경이 필요한지",
            ]
        if "workplace_change_addition" in issue_set:
            return [
                f"현재 ARC상 {current}의 정확한 세부코드와 승인 직종이 무엇인지",
                "기존 회사의 퇴사일과 새 회사의 근무 시작 예정일이 언제인지",
                "새 사업장의 업종과 실제 담당 직무가 무엇인지",
                "새 근로계약의 임금·근무시간·계약기간이 승인 기준에 맞는지",
                "근무 시작 전에 허가가 필요한지, 사후 신고가 가능한 유형인지",
                "관할 출입국기관이 요구하는 공식 제출서류와 접수 경로가 무엇인지",
            ]
        if kinds["registration"]:
            questions = []
            if not facts.get("entry_date"):
                questions.append("한국에 입국한 날짜(입국일)는 언제인지")
            else:
                questions.append(f"입국일 {facts.get('entry_date')} 기준 계산일 {facts.get('registration_deadline_date') or '확인 필요'}을 적용해도 되는지")
            questions.extend([
                "부여받은 체류기간은 얼마인지",
                "외국인등록 등 신고 기한은 며칠인지",
                "신고를 어디서·어떻게(하이코리아 또는 관할 출입국·외국인청 방문) 하는지",
            ])
            return questions
        if kinds["status_change"] and facts.get("target_status"):
            target = facts.get("target_status")
            return [
                f"현재 체류자격이 {current}인지, 세부 코드는 무엇인지",
                f"{target}로의 변경 요건을 충족하는지",
                "국내 변경인지, 재외공관 사증 신청인지",
                "남은 체류기간과 변경 신청 시점",
            ]
        if kinds["work"] and work_limited:
            return [
                f"현재 체류자격이 {current}인지와 활동범위",
                "국적별 워킹홀리데이·협정에서 정한 취업 가능 직종과 근무 기간·시간 제한",
                "일의 형태: 단기 일반 통역·번역 보조 / 장기·전임 전문 통역사 취업 / 관광통역안내(가이드) / 외국어 교습·강의 중 무엇인지",
                "관광통역안내사·교원 등 국내 자격·면허가 필요한 직종인지",
                "출입국이 이를 허용 범위 내 단기 취업으로 보는지, 아니면 자격외활동허가나 별도 제한 대상으로 보는지",
            ]
        if kinds["work"]:
            return [
                f"현재 체류자격이 {current}인지와 활동범위",
                "보수 발생 여부와 근로·사업 형태",
                "고용주·업종·근무시간·계약형태",
                "출입국이 이를 자격외활동 또는 신고/허가 대상으로 보는지",
            ]
        return []
    if "post_status_change_residual_duty" in issue_set:
        return [
            f"whether your ARC currently shows {current}",
            f"the {current} approval conditions",
            "the side-activity form: employment / freelance / business / incidental income",
            "whether there is an additional employer or business registration",
            "the industry, working hours, compensation, and contract type",
            "whether immigration treats this as a workplace addition, a reportable change, activities outside status, or a separate restriction",
        ]
    if kinds["study"]:
        return [
            f"what the basis for your {current} status is",
            "which activity it is: enrollment, audit, or summer-session course",
            "whether it is credit-bearing or degree-related",
            "the course duration and weekly hours",
            "whether the school requires D-2 / D-4 or another study status",
            f"whether immigration sees it as compatible with the purpose of {current}",
            "whether it needs permission for activities outside status or a change of status",
        ]
    if "workplace_change_addition" in issue_set:
        return [
            f"the exact {current} sub-code and approved occupation shown on your ARC/approval",
            "the prior employment end date and planned start date with the new employer",
            "the new employer's industry and your actual duties",
            "the wage, hours, and contract term in the new employment agreement",
            "whether permission is required before work starts or post-reporting is accepted",
            "the official document list and filing channel required by the competent office",
        ]
    if kinds["registration"]:
        questions = []
        if not facts.get("entry_date"):
            questions.append("your date of entry into Korea")
        else:
            questions.append(
                f"whether the calculated date {facts.get('registration_deadline_date') or 'to be confirmed'}"
                f" from entry date {facts.get('entry_date')} applies to your case"
            )
        questions.extend([
            "the period of stay you were granted",
            "the alien-registration / reporting deadline in days",
            "where and how to file (HiKorea or the competent immigration office)",
        ])
        return questions
    if kinds["status_change"] and facts.get("target_status"):
        target = facts.get("target_status")
        return [
            f"whether your current status is {current} and its sub-code",
            f"whether you meet the requirements to change to {target}",
            "whether this is an in-country change or a consular visa application",
            "your remaining period of stay and when you would apply",
        ]
    if kinds["work"] and work_limited:
        return [
            f"whether your current status is {current} and its activity scope",
            "the permitted work types and the work-period/hour limits under your nationality's working-holiday or agreement terms",
            "the work form: short-term general interpretation/translation, long-term professional interpreter employment, tourist-guide interpretation, or foreign-language teaching",
            "whether the job needs a domestic license or qualification (e.g. tourist guide, teaching)",
            "whether immigration treats this as short-term work within the allowed scope or as activities needing separate permission",
        ]
    if kinds["work"]:
        return [
            f"whether your current status is {current} and its activity scope",
            "whether it is paid and the work/business form",
            "the employer, industry, working hours, and contract type",
            "whether immigration treats this as activities outside status or a reportable/permission-required change",
        ]
    return []


def build_legal_analysis_fallback_answer(
    *,
    prompt: str,
    lang: Optional[str],
    base_meta: Dict[str, Any],
    legal_analysis: Optional[Dict[str, Any]],
    intro_mode: str = "outage",
) -> str:
    """Build a deterministic synthesis from generalized legal_analysis.

    This deliberately avoids status/activity templates. Study-specific wording
    appears only when legal_analysis actually classified the issue/activity as
    study-related.

    ``intro_mode`` controls the leading line:
      * ``"outage"`` (default): the provider was unavailable, so the note opens
        by saying Paradiso is showing a structured analysis instead.
      * ``"quality_repair"``: the live model DID answer but failed the
        answer-shape gate, so we lead directly with the practical answer (no
        outage line and no uncertainty-first opening — Part C / Part G).
    """
    norm = str(lang or "").lower()
    is_ko = norm.startswith("ko") or bool(re.search(r"[가-힣]", prompt or ""))
    la = legal_analysis if isinstance(legal_analysis, dict) else {}
    facts = _legal_analysis_facts_for_answer(base_meta, la)
    issues = list(la.get("legal_issue_types") or base_meta.get("legal_issue_types") or [])
    activities = list(facts.get("proposed_activities") or base_meta.get("proposed_activity_type") or [])
    issue_labels = _issue_labels_for_fallback(issues, is_ko=is_ko)
    activity_labels = _activity_labels_for_fallback(activities, is_ko=is_ko)
    # Localized, issue-scoped facts/questions. We deliberately do NOT render the
    # backend ``decisive_facts`` (internal snake_case) or the English-canonical
    # ``official_confirmation_questions`` into the user-facing memo (Part D/E).
    extra_fact_lines = _fallback_fact_lines_localized(issues, facts, activities, is_ko=is_ko)
    questions = _fallback_confirmation_questions_localized(issues, facts, activities, is_ko=is_ko)
    if not questions:
        # Fall back to localized confirmation questions (ko/en) only — never the
        # raw English-canonical set when answering in Korean.
        localized = base_meta.get("official_confirmation_questions_localized")
        if is_ko and isinstance(localized, list) and localized:
            questions = [q for q in localized if isinstance(q, str) and not re.search(r"[A-Za-z]{4,}", q)][:8]
        elif not is_ko:
            questions = list(la.get("official_confirmation_questions") or base_meta.get("official_confirmation_questions") or [])[:8]
    questions = list(dict.fromkeys([q for q in questions if isinstance(q, str) and q.strip()]))[:8]
    current = facts.get("current_status") or base_meta.get("visa_code_detected")
    previous = facts.get("previous_status")
    target = facts.get("target_status")
    source_state = str(base_meta.get("source_state") or la.get("analysis_mode") or "").lower()
    source_note = _localized_source_boundary_note(is_ko=is_ko, source_state=source_state, legal_analysis=la)
    # Part G: for registration/reporting answers, use concise source-limitation
    # wording that points to the official channels for the deadline/filing detail
    # instead of a generic "this is not based on the manual" disclaimer.
    if "registration_or_residence_report" in issues or "registration_deadline" in issues or "reporting_duty" in issues:
        source_note = (
            "현재 연결된 직접 근거는 제한적이므로, 최종 기한과 제출 방식은 1345/HiKorea/관할 관서에서 확인하세요."
            if is_ko else
            "Direct sources are currently limited, so confirm the exact deadline and"
            " filing method with 1345 / HiKorea / the competent immigration office."
        )

    practical = str(la.get("practical_posture") or "").strip()
    main_issue = str(la.get("main_issue") or base_meta.get("main_issue") or "").strip()
    if is_ko:
        practical = _korean_practical_fallback(issues, facts, activities, activity_labels)
        main_issue = _korean_main_issue_fallback(issues, facts, activity_labels)
        if intro_mode == "quality_repair":
            lines = []
        else:
            lines = ["AI 모델이 일시적으로 응답하지 않아, Paradiso가 구조화된 법률 분석 메모를 대신 표시합니다.", ""]
        if "post_status_change_residual_duty" in issues and previous and current:
            lines.append(
                f"{current}로 체류자격 변경이 완료되었다면, 부업 여부는 이전 {previous} 기준만으로 판단할 사안은 아니고 "
                f"현재 {current}의 활동범위와 승인 조건을 기준으로 다시 검토해야 합니다. 다만 {previous}의 근무처 추가 신고 의무가 "
                "자동으로 계속 적용되는지, 또는 전혀 적용되지 않는지는 개별 승인 조건과 부업의 형태를 확인해야 합니다."
            )
        elif "status_change" in issues and target:
            from_status = current or previous or "현재 체류자격"
            lines.append(f"이 질문은 {from_status}에서 {target}로 체류자격을 변경할 수 있는지에 관한 경로와 요건을 먼저 확인해야 하는 사안입니다.")
        elif "study_on_non_study_status" in issues:
            status = current or "현재 체류자격"
            acts = ", ".join(activity_labels) or "수학 활동"
            lines.append(f"{status} 상태에서 {acts}을/를 하려는 사안이므로, 먼저 현재 체류자격의 활동범위와 체류 목적 정합성 기준에서 검토해야 합니다.")
        elif "employment_restriction" in issues and _is_work_limited_status(facts):
            status = current or "현재 체류자격"
            lines.append(
                f"{status}은(는) 체류 목적과 국가별 협정 한도 안에서 단기 취업이 일부 허용될 수 있는 체류자격이므로, "
                "보수를 받는다는 사실만으로 자격외활동 위반으로 단정할 사안은 아니고, 일의 형태와 근무 기간, 협정 조건을 "
                "기준으로 허용 범위를 검토해야 합니다."
            )
        elif "registration_deadline" in issues and facts.get("entry_date") and facts.get("registration_deadline_date"):
            lines.append(_format_registration_deadline_formula(facts, is_ko=True) or "")
        elif "registration_or_residence_report" in issues or "registration_deadline" in issues:
            status = current or "현재 체류자격"
            if facts.get("entry_date"):
                lines.append(
                    f"{status} 외국인등록은 입국일 {facts.get('entry_date')}을 기준으로 90일 이내 원칙을 적용해 "
                    "기한을 계산하고, 대상 여부와 접수 방식은 관할 기관에서 확인해야 합니다."
                )
            else:
                lines.append(f"{status} 외국인등록·체류 신고 사안이므로, 출입국 체류 신고의 기산일·기한·대상·관할을 중심으로 확인해야 합니다.")
        elif practical:
            lines.append(practical)
        elif current or activity_labels:
            lines.append(f"현재 체류자격 {current or '미확인'}에서 {', '.join(activity_labels) or '해당 활동'}에 관한 쟁점을 기준으로 확인해야 합니다.")
        if practical and practical not in lines[-1:]:
            lines.extend(["", f"실무상 접근: {practical}"])
        if main_issue:
            lines.extend(["", f"핵심 쟁점은 {main_issue}"])
        if issue_labels:
            lines.extend(["", "주요 쟁점:", *[f"* {label}" for label in issue_labels]])
        fact_lines: List[str] = []
        if current:
            fact_lines.append(f"현재 ARC상 체류자격/세부자격이 {current}인지")
        if previous:
            fact_lines.append(f"이전 체류자격 {previous}의 승인 조건이나 신고 이력이 남아 있는지")
        if target:
            fact_lines.append(f"목표 체류자격/절차가 {target}인지")
        if activity_labels:
            fact_lines.append(f"활동 유형이 {', '.join(activity_labels)} 중 무엇인지")
        fact_lines.extend([d for d in extra_fact_lines if isinstance(d, str) and d not in fact_lines])
        if fact_lines:
            lines.extend(["", "확인할 사실:", *[f"* {item}" for item in fact_lines[:8]]])
        if questions:
            lines.extend(["", "공식 확인 질문:", *[f"* {q}" for q in questions]])
        lines.extend(["", source_note, "이 메모는 최종 판단이 아니며, 시작 전 1345, HiKorea 또는 관할 출입국·외국인청에 위 사실관계를 기준으로 확인하세요."])
        return "\n".join(lines)

    if intro_mode == "quality_repair":
        lines = []
    else:
        lines = ["The AI model is temporarily unavailable, so Paradiso is showing a structured legal-analysis preparation note.", ""]
    if "post_status_change_residual_duty" in issues and previous and current:
        lines.append(
            f"Because the status has already changed from {previous} to {current}, analyze the side activity first under the current {current} status. "
            f"A reporting logic tied to the former {previous} status does not automatically continue, but it also cannot be treated as automatically irrelevant without checking approval conditions and reporting rules."
        )
    elif "status_change" in issues and target:
        from_status = current or previous or "the current status"
        lines.append(f"Treat this as a route question about changing from {from_status} to {target}, not merely as an activity-scope question about the current status.")
    elif "study_on_non_study_status" in issues:
        status = current or "the current status"
        acts = ", ".join(activity_labels) or "study activity"
        lines.append(f"For {acts} on {status}, review the current status's permitted activity scope and purpose-of-stay alignment first.")
    elif "employment_restriction" in issues and _is_work_limited_status(facts):
        status = current or "the current status"
        lines.append(
            f"{status} may allow short-term paid work within the status purpose and your nationality's agreement limits, "
            "so being paid does not by itself make this an outside-status violation. Whether it is allowed turns on the "
            "work type (short-term general interpretation/translation, long-term professional interpreter employment, "
            "tourist-guide interpretation, or foreign-language teaching), the duration, the agreement terms, and any "
            "domestic license requirement."
        )
    elif "registration_deadline" in issues and facts.get("entry_date") and facts.get("registration_deadline_date"):
        lines.append(_format_registration_deadline_formula(facts, is_ko=False) or "")
    elif "registration_or_residence_report" in issues or "registration_deadline" in issues:
        status = current or "the current status"
        if facts.get("entry_date"):
            lines.append(
                f"For {status} alien registration, calculate from entry date {facts.get('entry_date')}"
                " using the 90-calendar-day rule, then confirm applicability and filing method with the competent office."
            )
        else:
            lines.append(f"This is an alien-registration/residence-reporting issue for {status}; focus on the filing trigger, deadline, scope, and competent office.")
    elif practical:
        lines.append(practical)
    elif current or activity_labels:
        lines.append(f"Review {', '.join(activity_labels) or 'the activity'} under {current or 'the current status'}.")
    if practical and practical not in lines[-1:]:
        lines.extend(["", f"Practical posture: {practical}"])
    if main_issue:
        lines.extend(["", f"Main issue: {main_issue}"])
    if issue_labels:
        lines.extend(["", "Key issues:", *[f"* {label}" for label in issue_labels]])
    fact_lines = []
    if current:
        fact_lines.append(f"current ARC status/sub-status: {current}")
    if previous:
        fact_lines.append(f"previous-status approval/reporting conditions tied to {previous}")
    if target:
        fact_lines.append(f"target status/procedure: {target}")
    if activity_labels:
        fact_lines.append(f"activity category: {', '.join(activity_labels)}")
    fact_lines.extend([d for d in extra_fact_lines if isinstance(d, str) and d not in fact_lines])
    if fact_lines:
        lines.extend(["", "Facts to confirm:", *[f"* {item}" for item in fact_lines[:8]]])
    if questions:
        lines.extend(["", "Questions to confirm with the official office:", *[f"* {q}" for q in questions]])
    lines.extend(["", source_note, "This is not a final determination. Before acting, confirm the fact pattern with 1345, HiKorea, or the competent immigration office."])
    return "\n".join(lines)

def _build_deterministic_fallback_payload(prompt: str, lang: Optional[str], base_meta: Dict[str, Any], attempt_meta: Dict[str, Any], reason: str) -> Dict[str, Any]:
    legal_analysis = base_meta.get("legal_analysis") if isinstance(base_meta.get("legal_analysis"), dict) else None
    answer = build_legal_analysis_fallback_answer(
        prompt=prompt,
        lang=lang,
        base_meta=base_meta,
        legal_analysis=legal_analysis,
    )
    legal_analysis_exists = bool(legal_analysis)
    fallback_meta = dict(base_meta)
    answer = _confidence_gate_answer_text(answer, fallback_meta)
    fallback_meta["legal_analysis_exists"] = legal_analysis_exists
    if legal_analysis_exists:
        fallback_meta["fallback_answer_kind"] = "legal_analysis_preparation_note"
        if fallback_meta.get("answer_quality_mode") == "source_unavailable":
            fallback_meta["answer_quality_mode"] = "source_limited"
            fallback_meta["source_confidence_level"] = "low"
        if str(fallback_meta.get("source_state") or "").lower() in {"", "source_unavailable", "unavailable", "disabled"}:
            fallback_meta["source_state"] = "legal_analysis_preparation_note"
        if str(fallback_meta.get("source_panel_state") or "") != SOURCE_PANEL_DIRECT_SOURCE_VERIFIED:
            fallback_meta["source_panel_state"] = SOURCE_PANEL_STRUCTURED_FALLBACK_AVAILABLE
            fallback_meta["source_panel_label_key"] = "structured_fallback"
        fallback_meta["default_source_panel_should_show_raw_codes"] = False
    else:
        fallback_meta["fallback_answer_kind"] = "structured_preparation_note"
        if not fallback_meta.get("source_panel_state"):
            fallback_meta["source_panel_state"] = SOURCE_PANEL_SOURCE_UNAVAILABLE
            fallback_meta["source_panel_label_key"] = "source_unavailable"
    return {
        **attempt_meta,
        **fallback_meta,
        "answer": answer,
        "provider": "deterministic_fallback",
        "model": "legal-analysis-preparation-note",
        "llm_provider": "deterministic_fallback",
        "final_model": None,
        "provider_family_fallback_used": False,
        "deterministic_fallback_answer_used": True,
        "llm_unavailable": True,
        "provider_unavailable": True,
        "fallback_answer_reason": reason,
        "fallback_answer_kind": fallback_meta.get("fallback_answer_kind") or "legal_analysis_preparation_note",
        "fallback_answer": answer,
        "copy_safe_answer": answer,
        "ollama_fallback_enabled": ENABLE_OLLAMA_FALLBACK,
        "ollama_fallback_used": False,
        "ollama_model": OLLAMA_MODEL,
    }


def _apply_answer_shape_gate(
    answer: str,
    response_meta: Dict[str, Any],
    answer_shape_contract: Dict[str, Any],
    *,
    prompt: str,
    lang: Optional[str],
    final_model: Optional[str],
    primary_model: Optional[str],
) -> tuple:
    """Run the answer-shape quality gate on a live model answer (Part B/C/F).

    Returns ``(final_answer, gate_meta)``. When the live answer fails the
    issue-type contract *structurally* and a backend legal_analysis exists, the
    weak answer is replaced by deterministic synthesis (leading with the
    practical answer, not an outage notice). Never raises; never changes
    provider/model selection or the model attempt metadata.
    """
    contract_key = answer_shape_contract.get("contract_key", "")
    final_model_quality_warning = bool(
        final_model and primary_model and final_model != primary_model
    )
    gate_meta: Dict[str, Any] = {
        "answer_shape_contract": contract_key,
        "answer_shape_version": answer_shape_contract.get("answer_shape_version", ANSWER_SHAPE_VERSION),
        "final_model_quality_warning": final_model_quality_warning,
        "answer_shape_failed_by_model": False,
        "model_answer_repaired_by_deterministic_synthesis": False,
    }

    try:
        gate = evaluate_answer_shape(answer, response_meta, answer_shape_contract)
    except Exception:  # pragma: no cover - the gate must never break /api/ask
        gate_meta.update(
            answer_quality_gate_passed=True,
            answer_quality_gate_warnings=[],
            missing_answer_slots=[],
            copy_safe_answer=answer,
        )
        return answer, gate_meta

    gate_meta.update(
        answer_quality_gate_passed=gate["passed"],
        answer_quality_gate_warnings=gate["warnings"],
        missing_answer_slots=gate["missing_slots"],
    )

    legal_analysis = (
        response_meta.get("legal_analysis")
        if isinstance(response_meta.get("legal_analysis"), dict)
        else None
    )
    law_pack = response_meta.get("law_evidence_pack") if isinstance(response_meta.get("law_evidence_pack"), dict) else {}
    precedent_items = law_pack.get("precedent_evidence_items") or []
    try:
        original_case_check = verify_case_decision_citations(answer, evidence_items=precedent_items)
    except Exception:  # pragma: no cover - verifier must never break /api/ask
        original_case_check = {
            "status": "error",
            "warnings": ["CASE_DECISION_VERIFIER_ERROR"],
            "citations": [],
            "quotes": [],
        }
    gate_meta["case_decision_citation_verification"] = original_case_check
    gate_meta["case_decision_citation_verification_status"] = original_case_check.get("status", "")

    if (not gate["passed"]) and gate["repair_strategy"] == "deterministic_synthesis" and legal_analysis:
        repaired = build_legal_analysis_fallback_answer(
            prompt=prompt,
            lang=lang,
            base_meta=response_meta,
            legal_analysis=legal_analysis,
            intro_mode="quality_repair",
        )
        repaired = _confidence_gate_answer_text(repaired, response_meta)
        regate = evaluate_answer_shape(repaired, response_meta, answer_shape_contract)
        gate_meta.update(
            answer_shape_failed_by_model=True,
            model_answer_repaired_by_deterministic_synthesis=True,
            answer_quality_gate_passed=regate["passed"],
            answer_quality_gate_warnings=regate["warnings"],
            missing_answer_slots=regate["missing_slots"],
            copy_safe_answer=repaired,
        )

    answer = gate_meta.get("copy_safe_answer") or answer

    # Case / decision citations need a stricter verifier than statute citations.
    # Fabricated case numbers, unsupported authority claims, or direct holdings
    # backed only by list/contextual evidence must not be shown to users.
    try:
        case_check = verify_case_decision_citations(answer, evidence_items=precedent_items)
    except Exception:  # pragma: no cover - verifier must never break /api/ask
        case_check = {"status": "error", "warnings": ["CASE_DECISION_VERIFIER_ERROR"], "citations": [], "quotes": []}
    gate_meta["case_decision_citation_verification"] = case_check
    gate_meta["case_decision_citation_verification_status"] = case_check.get("status", "")
    if original_case_check.get("status") == "failed" and case_check.get("status") != "failed":
        gate_meta["case_decision_citation_repaired"] = True
    if case_check.get("status") == "failed":
        if legal_analysis:
            repaired = build_legal_analysis_fallback_answer(
                prompt=prompt,
                lang=lang,
                base_meta=response_meta,
                legal_analysis=legal_analysis,
                intro_mode="quality_repair",
            )
            repaired = _confidence_gate_answer_text(repaired, response_meta)
            try:
                repair_check = verify_case_decision_citations(repaired, evidence_items=precedent_items)
            except Exception:  # pragma: no cover
                repair_check = {"status": "error", "warnings": ["CASE_DECISION_VERIFIER_ERROR"]}
            if repair_check.get("status") != "failed":
                gate_meta.update(
                    model_answer_repaired_by_deterministic_synthesis=True,
                    case_decision_citation_repaired=True,
                    case_decision_citation_verification=repair_check,
                    case_decision_citation_verification_status=repair_check.get("status", ""),
                    copy_safe_answer=repaired,
                )
                return repaired, gate_meta
        safe = _case_law_uncertainty_answer(lang=lang)
        gate_meta.update(
            answer_shape_failed_by_model=True,
            case_decision_citation_rejected=True,
            copy_safe_answer=safe,
        )
        return safe, gate_meta

    gate_meta["copy_safe_answer"] = answer
    return answer, gate_meta


async def _openrouter_complete_with_candidates(
    prompt: str,
    requested_model: Optional[str] = None,
    candidate_models: Optional[List[str]] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Try OpenRouter candidates in order, skipping models in short cooldown.

    Retryable failures (429/503/timeout/temporary upstream unavailability) mark
    that model in an in-memory cooldown map. Later requests skip cooling models.
    If every candidate is cooling down, this function does not hammer any model;
    it returns deterministic metadata so /api/ask can use the preparation-note
    fallback (or an explicitly enabled provider-family/private fallback).
    """
    base_candidates = candidate_models or OPENROUTER_MODEL_CANDIDATES
    if requested_model:
        candidates = _dedupe_preserve_order([requested_model, *base_candidates])
    else:
        candidates = list(base_candidates) or [OPENROUTER_MODEL]

    cooling = set(_cooling_down_models())
    runnable = [model for model in candidates if model not in cooling]
    skipped = [model for model in candidates if model in cooling]

    if not runnable:
        return {
            "ok": False,
            "answer": None,
            "primary_model": candidates[0] if candidates else OPENROUTER_MODEL,
            "requested_model": requested_model,
            "model_candidates": candidates,
            "attempted_models": [],
            "skipped_models_due_to_cooldown": skipped,
            "cooling_down_models": _cooling_down_models(),
            "model_cooldown_seconds": OPENROUTER_MODEL_COOLDOWN_SECONDS,
            "cooldown_enabled": _cooldown_enabled(),
            "final_model": None,
            "model_fallback_used": False,
            "provider_error_type": "all_candidates_cooling_down",
            "upstream_statuses": [],
            "retryable_provider_error": True,
            "all_candidates_failed": True,
        }

    attempted: List[str] = []
    upstream_statuses: List[int] = []
    last_error_type: Optional[str] = None
    last_retryable = False

    for model in runnable:
        attempted.append(model)
        try:
            answer = await _call_openrouter(prompt, model=model, max_tokens=max_tokens)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            upstream = detail.get("status", exc.status_code)
            try:
                upstream_statuses.append(int(upstream))
            except (TypeError, ValueError):
                pass
            last_error_type, last_retryable = _classify_openrouter_error(
                detail.get("status"), detail.get("message"), detail.get("error")
            )
            if last_retryable:
                _mark_openrouter_model_cooling_down(model)
                continue
            if last_error_type in _PER_MODEL_SKIP_ERROR_TYPES:
                # Bad/unknown model id or no endpoints for THIS model: skip to the
                # next candidate instead of aborting the whole request.
                continue
            break  # account-wide auth / bad-request / safety: stop early
        return {
            "ok": True,
            "answer": answer,
            "primary_model": candidates[0],
            "requested_model": requested_model,
            "model_candidates": candidates,
            "attempted_models": attempted,
            "skipped_models_due_to_cooldown": skipped,
            "cooling_down_models": _cooling_down_models(),
            "model_cooldown_seconds": OPENROUTER_MODEL_COOLDOWN_SECONDS,
            "cooldown_enabled": _cooldown_enabled(),
            "final_model": model,
            "model_fallback_used": model != candidates[0],
            "provider_error_type": last_error_type,
            "upstream_statuses": upstream_statuses,
            "retryable_provider_error": last_retryable,
            "all_candidates_failed": False,
        }

    return {
        "ok": False,
        "answer": None,
        "primary_model": candidates[0],
        "requested_model": requested_model,
        "model_candidates": candidates,
        "attempted_models": attempted,
        "skipped_models_due_to_cooldown": skipped,
        "cooling_down_models": _cooling_down_models(),
        "model_cooldown_seconds": OPENROUTER_MODEL_COOLDOWN_SECONDS,
        "cooldown_enabled": _cooldown_enabled(),
        "final_model": None,
        "model_fallback_used": len(attempted) > 1 or bool(skipped),
        "provider_error_type": last_error_type or "unknown_provider_error",
        "upstream_statuses": upstream_statuses,
        "retryable_provider_error": last_retryable,
        "all_candidates_failed": len(attempted) + len(skipped) == len(candidates),
    }


# ---------------------------------------------------------------------------
# Streaming (Server-Sent Events) answer path
# ---------------------------------------------------------------------------
def _sse(event: str, data: Dict[str, Any]) -> str:
    """Format one Server-Sent Event frame (named event + JSON data)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_openrouter_text(
    prompt: str, model: str, max_tokens: Optional[int] = None
):
    """Async generator yielding answer text deltas from one OpenRouter model.

    Raises HTTPException BEFORE the first yield on a pre-stream failure (bad
    status, timeout, transport error) so the orchestrator can classify it and
    fall through to the next candidate. Once deltas start flowing the model is
    committed. No secrets are ever surfaced.
    """
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail={"error": "openrouter_not_configured", "status": 503, "message": "OPENROUTER_API_KEY is not set on the server."})
    if httpx is None:
        raise HTTPException(status_code=500, detail={"error": "httpx_missing", "message": "httpx is not installed."})

    payload: Dict[str, Any] = {
        "model": model or OPENROUTER_MODEL,
        "messages": _llm_messages(prompt),
        "stream": True,
    }
    effective_max_tokens = OPENROUTER_MAX_TOKENS if max_tokens is None else max_tokens
    if effective_max_tokens and effective_max_tokens > 0:
        payload["max_tokens"] = int(effective_max_tokens)
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if SITE_URL:
        headers["HTTP-Referer"] = SITE_URL
    if SITE_TITLE:
        headers["X-Title"] = SITE_TITLE
    try:
        async with httpx.AsyncClient(timeout=OPENROUTER_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST", "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    raw = await resp.aread()
                    try:
                        text = raw.decode("utf-8", errors="ignore")
                    except Exception:
                        text = ""
                    raise HTTPException(
                        status_code=502,
                        detail={"error": "openrouter_upstream_error", "status": resp.status_code, "message": text[:500]},
                    )
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except (ValueError, TypeError):
                        continue
                    try:
                        delta = obj["choices"][0]["delta"].get("content")
                    except (KeyError, IndexError, TypeError):
                        delta = None
                    if delta:
                        yield delta
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail={"error": "openrouter_timeout", "status": 504, "message": f"OpenRouter stream timed out after {OPENROUTER_TIMEOUT_SECONDS:.0f}s: {str(exc)[:200]}"})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail={"error": "openrouter_network_error", "status": 503, "message": f"OpenRouter stream failed: {str(exc)[:200]}"})


def _post_stream_safety_review_frames(
    full_text: str,
    base_meta: Dict[str, Any],
    *,
    prompt: str,
    lang: Optional[str],
) -> Optional[List[str]]:
    """Post-generation Trust & Safety re-check for the streamed path (H-7).

    The buffered /api/ask path runs ``safety_guardrails.post_generation_review``
    on the complete answer; the streamed path historically skipped it. This
    helper runs the SAME review over the fully-accumulated streamed text AFTER
    the final token, so it adds zero latency before the first token. When the
    review trips it returns the SSE frames that replace the on-screen answer
    with the neutral safety refusal, reusing ONLY events ai.html already
    handles (no frontend change needed):

      * ``meta``     — the original stream metadata plus the same safety_*
                       fields the buffered refusal response carries
                       (safety_blocked etc.), so the client's existing
                       renderSafetyResponse card takes over on finalize.
      * ``fallback`` — carries the refusal text; the client replaces the
                       accumulated answer with it (matching the buffered
                       path's answer-replacement semantics).

    Returns None when the answer passes review. Any internal error also
    returns None — a review crash must never break stream termination; the
    review is trip-only defense-in-depth, exactly like the buffered path's.
    Note: the buffered path's answer-shape repair gate is intentionally NOT
    applied post-stream — its repair rewrites the full (already watched)
    answer via deterministic synthesis, which is not meaningful after
    streaming. Safety review is covered; the shape gate remains buffered-only.
    """
    try:
        if not (full_text or "").strip():
            return None
        postgen = safety_guardrails.post_generation_review(full_text)
        if postgen is None:
            return None
        postgen.language = safety_guardrails.detect_language(prompt, lang)
        try:
            event_id = safety_events.log_safety_event(
                action=safety_guardrails.ACTION_ESCALATE,
                category=postgen.category,
                severity=postgen.severity,
                reason=postgen.reason,
                matched_signals=postgen.matched_signals,
                input_text=prompt,
                language=postgen.language,
                route="/api/ask:post_generation_stream",
                request_id=None,
            )
        except Exception:  # pragma: no cover - logging must not break the stream
            event_id = ""
        refusal = _build_safety_refusal_response(postgen, lang=lang, event_id=event_id)
        refusal_payload = refusal.model_dump()
        refusal_meta = dict(base_meta)
        for key in (
            "safety_action",
            "safety_blocked",
            "safety_category",
            "safety_severity",
            "safety_reason",
            "safety_alternatives",
            "safety_event_id",
            "answer_quality_mode",
            "source_confidence_level",
            "requires_official_confirmation",
            "grounded_answer_limited",
            "question_type_detected",
            "copy_safe_answer",
        ):
            if key in refusal_payload:
                refusal_meta[key] = refusal_payload[key]
        refusal_meta["post_generation_review_blocked"] = True
        return [
            _sse("meta", refusal_meta),
            _sse("fallback", {"answer": refusal_payload.get("answer") or ""}),
        ]
    except Exception:  # pragma: no cover - review must never break the stream
        logger.exception("post-stream safety review failed; keeping streamed answer")
        return None


async def _sse_answer_stream(
    final_prompt: str,
    candidates: List[str],
    max_tokens: Optional[int],
    base_meta: Dict[str, Any],
    *,
    prompt: str,
    lang: Optional[str],
):
    """Orchestrate the streamed answer over the candidate chain.

    Emits a ``meta`` event first, then ``model`` + ``delta`` events for the
    committed model, then ``done``. A per-model failure before the first token
    skips to the next candidate (mirroring the non-streaming loop). If every
    candidate fails it emits a ``fallback`` event carrying the same deterministic
    preparation note the non-streaming path uses, so the client never hangs.

    After the final token, the accumulated answer runs through the SAME
    post-generation safety review as the buffered path (see
    ``_post_stream_safety_review_frames``); a tripped review replaces the
    answer with the neutral refusal via existing ``meta`` + ``fallback`` events.
    """
    # Non-secret meta event (grounding/answer-mode/source panel state).
    yield _sse("meta", base_meta)

    cooling = set(_cooling_down_models())
    runnable = [m for m in candidates if m not in cooling] or list(candidates)
    attempted: List[str] = []
    last_error_type: Optional[str] = None

    for model in runnable:
        attempted.append(model)
        committed = False
        answer_parts: List[str] = []
        try:
            async for delta in _stream_openrouter_text(final_prompt, model=model, max_tokens=max_tokens):
                if not committed:
                    committed = True
                    _primary = candidates[0] if candidates else model
                    _is_fast = str(base_meta.get("answer_mode") or "") == "fast"
                    yield _sse("model", {
                        "final_model": model,
                        "selected_model": model,
                        "primary_model": _primary,
                        "model_fallback_used": bool(candidates) and model != _primary,
                        "fast_mode_fell_back": bool(_is_fast and model != _primary),
                        "answer_mode": base_meta.get("answer_mode", ""),
                        "attempted_models": list(attempted),
                    })
                answer_parts.append(delta)
                yield _sse("delta", {"text": delta})
            if committed:
                # Post-generation safety re-check on the COMPLETE accumulated
                # answer (H-7) — zero added latency before the first token.
                review_frames = _post_stream_safety_review_frames(
                    "".join(answer_parts), base_meta, prompt=prompt, lang=lang,
                )
                if review_frames:
                    for frame in review_frames:
                        yield frame
                    yield _sse("done", {"final_model": model, "attempted_models": list(attempted), "post_review_blocked": True})
                    return
                yield _sse("done", {"final_model": model, "attempted_models": list(attempted)})
                return
            # Stream ended with zero tokens: treat as a soft failure, try next.
            last_error_type = "empty_stream"
            continue
        except HTTPException as exc:
            if committed:
                # Failure AFTER partial output: stop cleanly (can't switch models
                # mid-answer) and let the client keep what it has — unless the
                # partial text already trips the post-generation safety review,
                # in which case it is replaced by the refusal before closing.
                review_frames = _post_stream_safety_review_frames(
                    "".join(answer_parts), base_meta, prompt=prompt, lang=lang,
                )
                if review_frames:
                    for frame in review_frames:
                        yield frame
                yield _sse("done", {"final_model": model, "attempted_models": list(attempted), "interrupted": True})
                return
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            etype, retryable = _classify_openrouter_error(
                detail.get("status"), detail.get("message"), detail.get("error")
            )
            last_error_type = etype
            if retryable:
                _mark_openrouter_model_cooling_down(model)
                continue
            if etype in _PER_MODEL_SKIP_ERROR_TYPES:
                continue
            break

    # Every candidate failed: stream the deterministic preparation note so the
    # user still gets a safe, source-aware response instead of nothing.
    attempt_meta = {
        "llm_provider": "openrouter",
        "attempted_models": list(attempted),
        "final_model": None,
        "provider_error_type": last_error_type or "unknown_provider_error",
        "all_candidates_failed": True,
    }
    try:
        fallback_payload = _build_deterministic_fallback_payload(
            prompt, lang, base_meta, attempt_meta,
            reason="openrouter_all_candidates_failed",
        )
        note = fallback_payload.get("answer") or ""
    except Exception:  # pragma: no cover - the fallback must never break the stream
        note = ""
    yield _sse("fallback", {"answer": note, "provider_error_type": last_error_type or "unknown_provider_error"})


# ---------------------------------------------------------------------------
# Static visa data
# ---------------------------------------------------------------------------

DEFAULT_VISAS: List[Dict[str, Any]] = [
    {
        "code": "E-7",
        "name": "특정활동",
        "category": "취업",
        "summary": "한국 산업 수요에 맞는 특정 직업에 종사하기 위한 비자.",
    },
    {
        "code": "D-8",
        "name": "기업투자",
        "category": "투자",
        "summary": "외국인 투자기업의 경영, 관리 또는 생산기술 분야 종사자에게 발급되는 비자.",
    },
    {
        "code": "D-10",
        "name": "구직",
        "category": "구직",
        "summary": "국내 기업 구직 활동을 위한 단기 체류 비자.",
    },
    {
        "code": "F-2",
        "name": "거주",
        "category": "장기체류",
        "summary": "장기 거주 자격을 부여받은 외국인을 위한 거주 비자.",
    },
    {
        "code": "F-5",
        "name": "영주",
        "category": "영주",
        "summary": "영주권자에게 발급되는 영주 비자.",
    },
]


_VISAS_CACHE: Optional[Dict[str, Any]] = None


def _candidate_visa_paths() -> List[str]:
    """Search order for the authoritative visa JSON file.

    1. `VISA_DATA_PATH` env var (absolute path, for explicit Railway
       configuration).
    2. `backend/data/visas.json` (committed override, e.g. for tests).
    3. `<repo-root>/visa_data.json` (works for local dev and any deploy
       whose build context includes the repo root).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    paths: List[str] = []
    explicit = os.environ.get("VISA_DATA_PATH", "").strip()
    if explicit:
        paths.append(explicit)
    paths.extend(
        [
            os.path.join(here, "data", "visas.json"),
            os.path.join(repo_root, "visa_data.json"),
        ]
    )
    return paths


def _coerce_visa_list(raw: Any) -> Optional[List[Dict[str, Any]]]:
    """Accept the common shapes for a visa data file.

    Supported:
    - a JSON list of records;
    - an object with a list under one of: visas, data, records, items.
    """
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("visas", "data", "records", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return None


def _classify_source(path: str) -> str:
    """Tag where a discovered visa file came from for response metadata."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    if path == os.path.join(here, "data", "visas.json"):
        return "backend-data"
    if path == os.path.join(repo_root, "visa_data.json"):
        return "repo-root"
    return "explicit"


def _load_visas() -> Dict[str, Any]:
    """Load and cache the visa list.

    Returns a dict with `visas` and either a `source_type` tag (real data
    loaded) or a `warning` describing why the DEFAULT_VISAS fallback was
    used. The file is read once per process and cached in module-level
    state. `source` always exposes only a short tag, not an absolute
    path, to avoid leaking the runtime layout.

    E-4A: the union resolver (record_store_union) is attempted first so the
    backend reads from the deterministic union of visa_data.json +
    data/scenario_help_records.json. During E-4A the union is identical to
    visa_data.json (zero behavior change); the resolver merely proves the
    plumbing works for E-4B. Falls back to path-based loading transparently.
    """
    global _VISAS_CACHE
    if _VISAS_CACHE is not None:
        return _VISAS_CACHE

    # E-4A: try the union resolver first. It is deterministic and de-duped.
    # The union equals visa_data.json today so behavior is unchanged.
    try:
        from record_store_union import load_union_view  # noqa: WPS433
        records = load_union_view()
        logger.info(
            "Loaded %d visa records (source_type=union-resolver) via record_store_union",
            len(records),
        )
        _VISAS_CACHE = {
            "visas": records,
            "source": "union-resolver",
            "source_type": "union-resolver",
        }
        return _VISAS_CACHE
    except Exception as exc:  # noqa: BLE001
        logger.warning("record_store_union unavailable (%s); falling back to path-based loading", exc)

    last_error: Optional[str] = None
    for path in _candidate_visa_paths():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            last_error = f"failed to read {path}: {exc}"
            logger.warning(last_error)
            continue
        records = _coerce_visa_list(raw)
        if records is None:
            last_error = (
                f"{path} did not contain a recognizable visa list shape"
            )
            logger.warning(last_error)
            continue
        source_type = _classify_source(path)
        logger.info(
            "Loaded %d visa records (source_type=%s) from %s",
            len(records),
            source_type,
            path,
        )
        _VISAS_CACHE = {
            "visas": records,
            "source": source_type,
            "source_type": source_type,
        }
        return _VISAS_CACHE

    warning = (
        "using fallback DEFAULT_VISAS because no visa data file was found"
        if last_error is None
        else f"using fallback DEFAULT_VISAS because {last_error}"
    )
    _VISAS_CACHE = {
        "visas": DEFAULT_VISAS,
        "source": "fallback",
        "source_type": "fallback",
        "warning": warning,
    }
    return _VISAS_CACHE


def _reset_visas_cache_for_tests() -> None:
    """Test hook only — clears the module-level cache."""
    global _VISAS_CACHE
    _VISAS_CACHE = None


# ---------------------------------------------------------------------------
# Manual grounding (narrow, deterministic)
# ---------------------------------------------------------------------------
#
# This is intentionally a single-file lookup, not a full RAG pipeline. Each
# supported (visa_code, procedure_type) pair must be backed by a verified
# entry in the stay_manual_grounding_2026_05.json fixture. Currently grounded:
#   - ("D-2", "체류기간 연장허가")
#   - ("D-4", "체류기간 연장허가")  # 어학연수생(D-4-1, D-4-7) only
#   - ("E-7", "체류기간 연장허가")
# Anything else falls through to the ungrounded path so behavior is unchanged
# for questions outside the verified scope.

_STAY_MANUAL_GROUNDING_FILE = "stay_manual_grounding_2026_05.json"
_GROUNDING_CACHE: Optional[Dict[str, Any]] = None


def _stay_manual_grounding_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "data", "manual_grounding", _STAY_MANUAL_GROUNDING_FILE)


def _load_stay_manual_grounding() -> Optional[Dict[str, Any]]:
    """Load the stay manual grounding fixture once per process."""
    global _GROUNDING_CACHE
    if _GROUNDING_CACHE is not None:
        return _GROUNDING_CACHE
    path = _stay_manual_grounding_path()
    if not os.path.isfile(path):
        logger.info("stay manual grounding fixture missing at %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            _GROUNDING_CACHE = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to read %s: %s", path, exc)
        return None
    return _GROUNDING_CACHE


def _reset_grounding_cache_for_tests() -> None:
    global _GROUNDING_CACHE
    _GROUNDING_CACHE = None


# Valid top-level main codes the normalizer recognizes. Used as a parsing
# oracle to disambiguate contiguous letter+digit inputs like 'd101' (D-10-1
# vs D-1-0-1) or 'd42k' (D-4-2K vs D-42-K). Two-digit forms like F-10 and
# E-10 are included to preserve the existing regression-guard behavior even
# though F-10 is not a real Korean visa category.
_VALID_MAIN_CODES: frozenset = frozenset(
    [
        "A-1", "A-2", "A-3",
        "B-1", "B-2",
        "C-1", "C-3", "C-4",
        "D-1", "D-2", "D-3", "D-4", "D-5", "D-6", "D-7", "D-8", "D-9", "D-10",
        "E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-8", "E-9", "E-10",
        "F-1", "F-2", "F-3", "F-4", "F-5", "F-6", "F-10",
        "G-1",
        "H-1", "H-2",
    ]
)


def _normalize_visa_code(code: Optional[str]) -> Optional[str]:
    """Normalize a visa code to the canonical 'A-N' or 'A-N-SUB' form.

    Examples (main codes):
        'd2', 'D2', 'd-2', 'D 2' -> 'D-2'
        'd10', 'D10', 'd-10', 'D 10' -> 'D-10'
        'K-ETA', 'k-eta' -> 'K-ETA' (no digits, pass through)

    Examples (sub-codes):
        'D-2-1', 'd2-1' -> 'D-2-1'
        'D-10-1', 'D10-1', 'd101' -> 'D-10-1'
        'D-4-2K', 'D4-2K', 'd42k' -> 'D-4-2K'
        'F-6-1', 'F6-1', 'f61' -> 'F-6-1'
        'E-7-4', 'E7-4', 'e74' -> 'E-7-4'

    For contiguous inputs (no separator between main and sub), the parser
    uses a static list of known main codes (_VALID_MAIN_CODES) to choose
    the longest valid main-code prefix. This is the only way to tell
    'd10' (main code D-10) apart from 'd101' (sub-code D-10-1) without
    explicit separators.

    Codes that do not start with letter+digits (e.g. K-ETA, K-STAR,
    REGION-S) pass through after strip+upper. Empty/None returns None.
    """
    if not isinstance(code, str):
        return None
    cleaned = code.strip().upper()
    if not cleaned:
        return None
    import re

    # Letter-only prefixed codes with no digits anywhere (K-ETA, K-STAR,
    # REGION-S) keep their canonical form after upper-casing.
    if not re.search(r"\d", cleaned):
        return cleaned

    # Must start with a single letter followed (optionally via separator)
    # by a digit. Anything else (e.g. a bare number, weird inputs) falls
    # through unchanged.
    head = re.match(r"^([A-Z])[\s\-]?(\d.*)$", cleaned)
    if not head:
        return cleaned
    letter = head.group(1)
    body = head.group(2)

    # Capture the first contiguous digit run, then whatever remains.
    digit_run = re.match(r"^(\d+)(.*)$", body)
    leading_digits = digit_run.group(1)
    tail = digit_run.group(2)
    # Strip any leading separator(s) between main digits and the sub part.
    tail = re.sub(r"^[\s\-]+", "", tail)

    # Choose the longest valid main-code prefix from the leading digits.
    # _VALID_MAIN_CODES is bounded to 1-2 digit forms, so iterate from 2
    # down to 1 to prefer 'D-10' over 'D-1' when both are valid.
    main_digits = leading_digits
    sub_from_digits = ""
    for prefix_len in range(min(len(leading_digits), 2), 0, -1):
        candidate = f"{letter}-{leading_digits[:prefix_len]}"
        if candidate in _VALID_MAIN_CODES:
            main_digits = leading_digits[:prefix_len]
            sub_from_digits = leading_digits[prefix_len:]
            break

    sub_raw = sub_from_digits + tail
    # Internal separators in the sub-code segment collapse to a single hyphen.
    sub_normalized = re.sub(r"[\s\-]+", "-", sub_raw)
    sub_normalized = sub_normalized.strip("-")

    if sub_normalized:
        return f"{letter}-{main_digits}-{sub_normalized}"
    return f"{letter}-{main_digits}"


def _split_visa_code(normalized: Optional[str]) -> tuple:
    """Split a normalized code into (top_visa_code, visa_sub_code).

    'D-4-2K' -> ('D-4', 'D-4-2K')
    'D-10-1' -> ('D-10', 'D-10-1')
    'D-2'    -> ('D-2', None)
    'K-ETA'  -> ('K-ETA', None)  (only one '-' segment after the letter)
    None     -> (None, None)

    A sub-code is recognized when the normalized form has three or more
    hyphen-separated segments where the first looks like 'L' and the
    second looks like a number — i.e. 'L-NN-...'. This keeps non-digit
    compound codes (K-ETA, REGION-S) from being mis-split.
    """
    if not isinstance(normalized, str) or not normalized:
        return None, None
    parts = normalized.split("-")
    if len(parts) >= 3 and len(parts[0]) == 1 and parts[1].isdigit():
        top = f"{parts[0]}-{parts[1]}"
        return top, normalized
    return normalized, None


# Visa codes for which a deterministic grounding entry exists. Used to
# bound the text-detection regex so we never claim detection for a code
# that has no backing grounding entry.
_GROUNDED_VISA_CODES: tuple = ("D-2", "D-4", "E-7")


def _detect_visa_code(payload_code: Optional[str], visa_data: Optional[Dict[str, Any]], text: str) -> Optional[str]:
    """Best-effort visa code detection (top-level only).

    Backwards-compatible wrapper around _detect_visa_codes that returns
    just the top-level visa_code, for callers that do not need sub-code
    routing. New code should call _detect_visa_codes directly.
    """
    top, _sub = _detect_visa_codes(payload_code, visa_data, text)
    return top


def _detect_visa_codes(
    payload_code: Optional[str],
    visa_data: Optional[Dict[str, Any]],
    text: str,
) -> tuple:
    """Return ``(top_visa_code, visa_sub_code)``.

    Priority: explicit ``visa_code`` -> ``visa_data.code`` -> regex match in
    text. Explicit payload values are normalized so ``d2``, ``D2``, ``d-2``
    all resolve to ``D-2`` and ``d42k``, ``D4-2K``, ``D-4-2K`` all resolve
    to ``D-4-2K`` (top ``D-4``, sub ``D-4-2K``).

    Sub-code detection is intentionally **payload-only**. Free-text
    detection still returns ``(top, None)`` even if the prompt mentions a
    sub-code in passing — sub-code routing is a binding declaration about
    *which* document list applies and must come from the caller, not from
    a free-text guess.

    Text detection preserves explicit status-code mentions before any LLM call,
    even for statuses without deterministic manual grounding (for example H-1
    activity-scope questions). Manual grounding remains a separate decision.
    """
    import re

    for candidate in (
        payload_code,
        (visa_data or {}).get("detected_code") if visa_data else None,
        (visa_data or {}).get("code") if visa_data else None,
    ):
        if isinstance(candidate, str) and candidate.strip():
            normalized = _normalize_visa_code(candidate)
            return _split_visa_code(normalized)
    if not text:
        return None, None
    # Match explicit status codes like "H-1", "D2", "F-6" before the LLM call.
    # Preserve intent/status metadata even when the status has no deterministic
    # manual grounding fixture. The negative lookahead avoids claiming D-4 for
    # a longer D-4-2 sub-code; free-text sub-code routing still stays disabled.
    for code in sorted(_VALID_MAIN_CODES, key=len, reverse=True):
        letter, digit = code.split("-", 1)
        pattern = rf"\b{letter}[\s-]?{re.escape(digit)}\b(?!-?\d)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return code, None
    return None, None


def _detect_task_type(text: str) -> Optional[str]:
    """Detect the procedure the user is asking about from the prompt text.

    Returns the highest-priority task type that matches. When both
    'marriage_divorce_status_change' and 'extension' signals co-occur
    (e.g. "getting divorced and my F-6-1 extension is next month"),
    the marriage/divorce task wins because it carries higher risk.

    Korean and English wording are both checked for each task type.
    """
    import re

    if not text:
        return None

    # --- foreigner_registration / registration deadline ---
    # Run before work/status detectors so "외국인등록 언제까지" with an entry
    # date does not get routed to an activity/work template just because the
    # sentence contains Korean date suffixes such as "27일".
    if is_registration_deadline_query(text):
        return "foreigner_registration"

    # --- marriage_divorce_status_change (highest priority, high risk) ---
    divorce_ko = ("이혼", "혼인 무효", "혼인단절", "별거", "사별", "재혼", "혼인관계 해소")
    divorce_en = r"\b(divorce[ds]?|divorcing|separated|separation|widow(?:ed)?|remarr(?:y|ied|ying)|annul(?:led|ment)?)\b"
    if any(sig in text for sig in divorce_ko) or re.search(divorce_en, text, flags=re.IGNORECASE):
        return "marriage_divorce_status_change"

    # --- academic_status_change ---
    academic_ko = ("휴학", "복학", "자퇴", "제적", "정학", "학점 미달", "학적 변동", "학적 상태")
    academic_en = r"\b(leave of absence|gap semester|drop(?:\s?out|ped out)|expelled|return(?:ing)? from leave|academic(?:\s+status)?)\b"
    if any(sig in text for sig in academic_ko) or re.search(academic_en, text, flags=re.IGNORECASE):
        return "academic_status_change"

    # --- overstay_deadline_risk ---
    overstay_ko = ("초과체류", "불법체류", "체류 만료", "만료 임박", "오버스테이", "기간이 지났")
    overstay_en = r"\b(overstay(?:ed)?|visa expired|expired visa|stay expired)\b"
    if any(sig in text for sig in overstay_ko) or re.search(overstay_en, text, flags=re.IGNORECASE):
        return "overstay_deadline_risk"

    # --- status_change (체류자격 변경) ---
    status_change_ko = ("체류자격 변경", "자격 변경", "변경허가", "체류 자격을 바꾸")
    status_change_en = r"\b(change of status|status change|switch (?:to|from) [A-Z]-\d|change (?:my )?visa (?:type|category|status))\b"
    if any(sig in text for sig in status_change_ko) or re.search(status_change_en, text, flags=re.IGNORECASE):
        return "status_change"

    # --- workplace_change ---
    workplace_ko = (
        "근무처 변경", "근무처를 변경", "근무처를 바꾸", "근무처 추가", "근무처를 추가",
        "근무처 변경신고", "이직", "직장을 바꾸", "직장 변경", "고용주 변경",
    )
    workplace_en = r"\b(change (?:of )?workplace|change employer|switch (?:jobs?|employer)|add (?:a )?second job)\b"
    if any(sig in text for sig in workplace_ko) or re.search(workplace_en, text, flags=re.IGNORECASE):
        return "workplace_change"

    # --- activities_outside_status / 체류자격외활동 ---
    activities_outside_ko = (
        "체류자격외활동", "체류자격 외 활동", "자격외활동", "자격 외 활동",
        "외 활동허가", "활동허가", "아르바이트 허가", "시간제취업",
        "시간제 취업", "파트타임", "부업",
    )
    activities_outside_en = (
        r"\b(activities outside status|activity outside status|outside status activity|"
        r"part[- ]?time work permission|side job permission|extra activity permission)\b"
    )
    if any(sig in text for sig in activities_outside_ko) or re.search(
        activities_outside_en, text, flags=re.IGNORECASE
    ):
        return "activities_outside_status"

    # --- address_report ---
    address_ko = ("체류지 변경신고", "주소 변경신고", "이사 신고", "주소를 바꾸", "체류지 변경", "이사를 했")
    address_en = r"\b(address change|change of address|report (?:my )?(?:new )?address|moved (?:house|apartment|address))\b"
    if any(sig in text for sig in address_ko) or re.search(address_en, text, flags=re.IGNORECASE):
        return "address_report"

    # --- passport_info_report ---
    passport_ko = ("여권 재발급 신고", "여권 정보 변경", "여권정보 변경", "새 여권 신고")
    passport_en = r"\b(report (?:new|renewed|reissued) passport|passport (?:renewed|reissued|information change))\b"
    if any(sig in text for sig in passport_ko) or re.search(passport_en, text, flags=re.IGNORECASE):
        return "passport_info_report"

    # --- family_status_change ---
    family_ko = (
        "가족관계 변동", "자녀 출생 신고", "부양 가족 변경", "출생 신고", "가족 구성 변경",
        "체류자격 부여", "자격 부여", "국내출생", "국내 출생", "국내출생 자녀", "출생 자녀 체류",
    )
    family_en = r"\b(family status change|(?:had|born) a child|dependent added|child born|new dependent|status grant|grant of status|child status grant)\b"
    if any(sig in text for sig in family_ko) or re.search(family_en, text, flags=re.IGNORECASE):
        return "family_status_change"

    # --- extension (medium risk; comes after high-risk marriage check) ---
    korean_signals = ("체류기간 연장", "체류 연장", "비자 연장", "연장 신청", "연장허가", "연장")
    if any(signal in text for signal in korean_signals):
        return "extension"
    if re.search(r"\b(extend|extension|renew|renewal)\b", text, flags=re.IGNORECASE):
        return "extension"

    return None


_TASK_RISK_LEVELS: Dict[str, str] = {
    "extension": "medium",
    "status_change": "high",
    "foreigner_registration": "medium",
    "workplace_change": "medium",
    "activities_outside_status": "low",
    "address_report": "low",
    "passport_info_report": "low",
    "academic_status_change": "medium",
    "family_status_change": "medium",
    "marriage_divorce_status_change": "high",
    "overstay_deadline_risk": "high",
    "general_status_summary": "low",
}


def _risk_level_for_task(task_type: Optional[str]) -> str:
    """Return a risk label for the detected task type."""
    return _TASK_RISK_LEVELS.get(task_type or "", "low")


def _select_grounding(
    visa_code: Optional[str],
    task_type: Optional[str],
    visa_sub_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return the grounding record for the request, or None.

    The selector is sub-code-aware:

    1. If ``visa_sub_code`` is set, prefer an entry whose
       ``visa_sub_code`` matches exactly.
    2. Otherwise fall back to a "general" entry (``visa_sub_code`` is
       null) **only** when that general entry explicitly lists the
       requested sub-code in ``sub_codes_covered``. A general entry that
       does not declare coverage is treated as not covering the sub-code,
       so e.g. an E-7-4 request never silently inherits the general E-7
       document list.
    3. If ``visa_sub_code`` is not provided, only entries with
       ``visa_sub_code`` null are eligible.

    Codes outside _GROUNDED_VISA_CODES return None so unrelated visa
    categories — including any sub-code whose top-level is not yet
    grounded (D-10, F-6) — are unaffected.
    """
    if task_type != "extension":
        return None
    if visa_code not in _GROUNDED_VISA_CODES:
        return None
    bundle = _load_stay_manual_grounding()
    if not bundle:
        return None
    entries = bundle.get("groundings", []) or []

    if visa_sub_code:
        # 1. Exact sub-code match wins.
        for entry in entries:
            if (
                entry.get("visa_code") == visa_code
                and entry.get("procedure_type") == "체류기간 연장허가"
                and entry.get("visa_sub_code") == visa_sub_code
            ):
                return entry
        # 2. Fall back to a general entry only if it explicitly covers this sub-code.
        for entry in entries:
            if (
                entry.get("visa_code") == visa_code
                and entry.get("procedure_type") == "체류기간 연장허가"
                and entry.get("visa_sub_code") in (None, "")
            ):
                covered = entry.get("sub_codes_covered") or []
                if isinstance(covered, list) and visa_sub_code in covered:
                    return entry
        return None

    # 3. No sub-code supplied: only general entries are eligible.
    for entry in entries:
        if (
            entry.get("visa_code") == visa_code
            and entry.get("procedure_type") == "체류기간 연장허가"
            and entry.get("visa_sub_code") in (None, "")
        ):
            return entry
    return None


def _answer_language_instruction(lang: Optional[str]) -> str:
    """Map a request lang hint to a one-line answer-language instruction.

    The grounding content (제출서류, 출처) is Korea-specific regardless of
    answer language. Only the language the model writes the answer in
    varies.

    Delegates to ``services.answer_quality.answer_language_instruction`` so the
    instruction also carries anti-mixed-language guardrails (no ``sojourn资格``
    artifacts) and explicit Simplified/Traditional Chinese handling.
    """
    return _answer_quality.answer_language_instruction(lang)


def _build_grounded_prompt(
    user_prompt: str,
    grounding: Dict[str, Any],
    bundle: Dict[str, Any],
    lang: Optional[str] = None,
) -> str:
    """Inject Korea-specific manual context into the user prompt.

    The wording explicitly instructs the model to stay within Korean
    immigration scope and to cite the manual, which guards against generic
    global-immigration boilerplate (USCIS, Home Office, etc.) and keeps the
    answer aligned with the source. The answer language is taken from the
    request `lang` field — Korea-specific grounding is preserved regardless.
    """
    docs = grounding.get("required_documents", []) or []
    caveats = grounding.get("caveats", []) or []
    excerpt = grounding.get("source_excerpt", "") or ""
    source_title = bundle.get("source_title", "외국인체류 안내매뉴얼")
    source_date = bundle.get("source_date", "2026.6")
    source_revision_date = bundle.get("source_revision_date")
    source_date_label = (
        f"{source_date}; source file {source_revision_date}"
        if source_revision_date and source_revision_date != source_date
        else source_date
    )
    issuing_body = bundle.get("issuing_body", "법무부 출입국·외국인정책본부")
    page_range = grounding.get("page_range")
    page_label = f", pp. {page_range}" if page_range else ""

    docs_block = "\n".join(f"- {item}" for item in docs)
    caveats_block = "\n".join(f"- {item}" for item in caveats)
    answer_language_line = _answer_language_instruction(lang)

    section_label = grounding.get("section") or grounding.get("visa_code", "")
    procedure_label = grounding.get("procedure_type", "체류기간 연장허가")
    return (
        "당신은 대한민국 출입국·외국인정책본부의 공식 매뉴얼을 근거로 답하는 한국 비자 안내 도우미입니다.\n"
        "아래 '참고 자료' 범위 안에서만 답하고, 다른 나라의 이민 절차나 일반적인 글로벌 이민 안내로"
        " 확장하지 마십시오. 모호한 표현 대신 한국의 출입국 제도를 구체적으로 적시하고,"
        " 매뉴얼에 없는 항목을 임의로 추가하지 마십시오. 본 매뉴얼 발췌에 포함되지 않은 다른 체류자격(비자)의"
        " 제출서류를 끌어와 답변에 섞지 마십시오.\n\n"
        f"[참고 자료] {source_title} ({source_date_label}) — {issuing_body}{page_label}\n"
        f"섹션: {section_label} / {procedure_label}\n\n"
        "제출서류 (매뉴얼 발췌):\n"
        f"{docs_block}\n\n"
        "유의사항:\n"
        f"{caveats_block}\n\n"
        "원문 발췌:\n"
        f"{excerpt}\n\n"
        "[사용자 질문]\n"
        f"{user_prompt}\n\n"
        "[답변 지침]\n"
        f"{answer_language_line}\n"
        "- 위 제출서류와 유의사항을 명시적으로 인용하십시오.\n"
        f"- 출처를 다음과 같이 명시하십시오: {source_title} ({source_date_label}), {issuing_body}.\n"
        "- 관할 출입국·외국인청/사무소/출장소가 개별 사안에 따라 서류를 추가하거나 면제할 수 있다는 점을 명시하십시오."
    )


def _grounding_source_summary(grounding: Dict[str, Any], bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Public-facing grounding metadata returned to the client.

    Keep this conservative: include only fields needed for UI attribution
    and downstream verification, not the full prompt-building payload.
    """
    return {
        "source_file": bundle.get("source_file"),
        "source_title": bundle.get("source_title"),
        "source_date": bundle.get("source_date"),
        "source_revision_date": bundle.get("source_revision_date"),
        "issuing_body": bundle.get("issuing_body"),
        "visa_code": grounding.get("visa_code"),
        "procedure_type": grounding.get("procedure_type"),
        "section": grounding.get("section"),
        "page_range": grounding.get("page_range"),
        "source_verification_status": grounding.get("source_verification_status"),
        "source_confidence": grounding.get("source_confidence"),
        "verification_note": grounding.get("verification_note"),
    }


def _build_visa_data_context_block(visa_data: Optional[Dict[str, Any]]) -> str:
    """Build a compact local-catalog context block from frontend visa_data.

    The Paradiso frontend (ai.html) sends a record from visa_data.json when
    the user question mentions a known visa code (D-2 / E-7 / F-6 / ...).
    This helper surfaces a small, conservative selection of safe fields so
    the LLM has some local context even when no deterministic manual
    grounding fixture matches the request. The block is marked as a local
    catalog reference, not as a legal source and not as an immigration-
    office determination, and individual fields are size-capped.

    Returns an empty string when ``visa_data`` is ``None``, is not a dict,
    or yields no usable fields. Callers are expected to skip appending the
    block in that case so behavior is unchanged for empty payloads.
    """
    if not isinstance(visa_data, dict) or not visa_data:
        return ""

    MAX_FIELD = 240

    def _trim(value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip()
        if len(s) > MAX_FIELD:
            s = s[:MAX_FIELD].rstrip() + "…"
        return s

    lines: List[str] = []

    code = _trim(visa_data.get("code"))
    if code:
        lines.append(f"- code: {code}")

    name_ko = _trim(visa_data.get("nameKo") or visa_data.get("name"))
    name_en = _trim(visa_data.get("nameEn"))
    if name_ko and name_en and name_ko != name_en:
        lines.append(f"- name: {name_ko} / {name_en}")
    elif name_ko:
        lines.append(f"- name: {name_ko}")
    elif name_en:
        lines.append(f"- name: {name_en}")

    category = _trim(visa_data.get("category") or visa_data.get("cat"))
    if category:
        lines.append(f"- category: {category}")

    summary = _trim(visa_data.get("summary"))
    if summary:
        lines.append(f"- summary: {summary}")

    period = _trim(
        visa_data.get("period")
        or visa_data.get("stayPeriod")
        or visa_data.get("stayPeriodCap")
    )
    if period:
        lines.append(f"- period: {period}")

    manual_domains = visa_data.get("manualDomains")
    if isinstance(manual_domains, list) and manual_domains:
        compact = ", ".join(
            str(item).strip()
            for item in manual_domains[:6]
            if isinstance(item, str) and item.strip()
        )
        if compact:
            lines.append(f"- manual domains (local catalog tag): {compact}")

    status = visa_data.get("sourceManualStatus")
    if isinstance(status, dict) and status:
        flags: List[str] = []
        vmv = _trim(status.get("visaManualVersion"))
        smv = _trim(status.get("stayManualVersion"))
        if vmv:
            flags.append(f"visa manual {vmv}")
        if smv and smv != vmv:
            flags.append(f"stay manual {smv}")
        if status.get("verified") is True:
            flags.append("local catalog marker: locally reviewed")
        elif status.get("verified") is False:
            flags.append("local catalog marker: not yet locally reviewed")
        if status.get("needsManualReview") is True:
            flags.append("local catalog marker: needs manual review")
        if flags:
            lines.append(
                "- source manual status (local catalog): " + "; ".join(flags)
            )

    procedures = visa_data.get("procedures")
    proc_lines: List[str] = []
    if isinstance(procedures, dict):
        for proc_key in (
            "extension",
            "statusChange",
            "registration",
            "workplaceChange",
        ):
            proc = procedures.get(proc_key)
            if not isinstance(proc, dict):
                continue
            ps = _trim(proc.get("summary"))
            if ps:
                proc_lines.append(f"  - {proc_key}: {ps}")
            if len(proc_lines) >= 3:
                break
    if proc_lines:
        lines.append("- procedure summaries (local catalog):")
        lines.extend(proc_lines)

    doc_groups: List[str] = []
    for label, key in (
        ("initial", "documents_initial"),
        ("extension", "documents_extension"),
        ("registration", "documents_registration"),
        ("change", "documents_change"),
    ):
        items = visa_data.get(key)
        if isinstance(items, list) and items:
            doc_groups.append(
                f"  - {label}: {len(items)} item(s) in local catalog"
            )
    if doc_groups:
        lines.append(
            "- document group labels (local catalog, not authoritative):"
        )
        lines.extend(doc_groups)

    if not lines:
        return ""

    header = (
        "[Local catalog context — reference only]\n"
        "The block below is the user's local visa catalog entry passed from"
        " the frontend. Treat it as local reference data only. It is not a"
        " legal source, not an immigration-office determination, and may be"
        " incomplete or out of date. Do not invent missing fields and do not"
        " present this block as definitive procedural guidance."
    )
    return f"{header}\n" + "\n".join(lines)


_PROCEDURE_VARIANT_TASK_KEYS: Dict[str, str] = {
    "status_change": "statusChange",
    "workplace_change": "workplaceChange",
    "activities_outside_status": "activitiesOutsideStatus",
}


def _procedure_variant_key_for_task(
    task_type: Optional[str],
    user_text: Optional[str] = None,
) -> Optional[str]:
    """Return the one procedure key eligible for needs-review variant context.

    Family questions are deliberately narrower than the other mappings:
    ``statusGrant`` is eligible only when the prompt itself explicitly signals
    birth or status grant. A generic family change must not pull child-specific
    checklists into the prompt.
    """
    mapped = _PROCEDURE_VARIANT_TASK_KEYS.get(task_type or "")
    if mapped:
        return mapped
    if task_type != "family_status_change":
        return None

    text = user_text or ""
    explicit_grant_ko = (
        "자녀 출생", "출생 신고", "국내출생", "국내 출생",
        "국내출생 자녀", "출생 자녀 체류",
        "체류자격 부여", "자격 부여",
    )
    if any(signal in text for signal in explicit_grant_ko):
        return "statusGrant"

    import re
    if re.search(r"\b(child born|born child|had a child|status grant|grant of status|child status grant)\b", text, flags=re.IGNORECASE):
        return "statusGrant"
    return None


def _select_procedure_variants(
    visa_data: Optional[Dict[str, Any]],
    task_type: Optional[str],
    visa_sub_code: Optional[str] = None,
    *,
    user_text: Optional[str] = None,
    selected_procedure_key: Optional[str] = None,
    selected_procedure_variant_id: Optional[str] = None,
    max_variants: int = 3,
) -> tuple:
    """Select a small scenario-variant set from a frontend local-catalog record.

    An explicit frontend-selected procedure key takes priority over task
    detection, and a matching selected variant id narrows the result to that
    one scenario. Invalid selected ids safely return no variant context rather
    than broadening back out. Without a selection, exact sub-code matches win.
    If none exists, at most ``max_variants`` are returned as visibly labeled
    scenario options under the matching procedure key only. Empty and
    explicitly unavailable variants are ignored.
    """
    requested_key = (
        selected_procedure_key.strip()
        if isinstance(selected_procedure_key, str) and selected_procedure_key.strip()
        else None
    )
    requested_variant_id = (
        selected_procedure_variant_id.strip()
        if isinstance(selected_procedure_variant_id, str) and selected_procedure_variant_id.strip()
        else None
    )
    procedure_key = requested_key or _procedure_variant_key_for_task(task_type, user_text)
    if not procedure_key or not isinstance(visa_data, dict):
        return None, []
    procedures = visa_data.get("procedures")
    if not isinstance(procedures, dict):
        return procedure_key, []
    procedure = procedures.get(procedure_key)
    if not isinstance(procedure, dict):
        return procedure_key, []
    variants = procedure.get("variants")
    if not isinstance(variants, list):
        return procedure_key, []

    usable: List[Dict[str, Any]] = []
    for variant in variants:
        if not isinstance(variant, dict) or variant.get("available") is False:
            continue
        required_docs = variant.get("requiredDocs")
        if not isinstance(required_docs, dict):
            continue
        if not any(
            isinstance(required_docs.get(group), list) and required_docs.get(group)
            for group in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs")
        ):
            continue
        usable.append(variant)

    if requested_variant_id:
        selected = [
            variant for variant in usable
            if str(variant.get("id") or "").strip() == requested_variant_id
        ]
        return procedure_key, selected[:1]

    normalized_sub_code = _normalize_visa_code(visa_sub_code) if visa_sub_code else None
    if normalized_sub_code:
        exact = [
            variant for variant in usable
            if _normalize_visa_code(str(variant.get("statusCode") or "")) == normalized_sub_code
        ]
        if exact:
            return procedure_key, exact[:max_variants]
    return procedure_key, usable[:max_variants]


def _procedure_variant_context_sources(
    visa_data: Optional[Dict[str, Any]],
    task_type: Optional[str],
    visa_sub_code: Optional[str] = None,
    *,
    user_text: Optional[str] = None,
    selected_procedure_key: Optional[str] = None,
    selected_procedure_variant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return safe response metadata for selected needs-review variants."""
    procedure_key, variants = _select_procedure_variants(
        visa_data,
        task_type,
        visa_sub_code,
        user_text=user_text,
        selected_procedure_key=selected_procedure_key,
        selected_procedure_variant_id=selected_procedure_variant_id,
    )
    if not procedure_key or not isinstance(visa_data, dict):
        return []

    visa_code = visa_data.get("code")
    sources: List[Dict[str, Any]] = []
    for variant in variants:
        refs = variant.get("manualRefs")
        ref = refs[0] if isinstance(refs, list) and refs and isinstance(refs[0], dict) else {}
        sources.append({
            "visa_code": visa_code,
            "procedure_key": procedure_key,
            "variant_id": variant.get("id"),
            "label": variant.get("labelKo") or variant.get("label"),
            "status_code": variant.get("statusCode"),
            "page_range": ref.get("pageRange"),
            "manual_name": ref.get("manualName"),
            "manual_version": ref.get("manualVersion"),
            "needs_manual_review": ref.get("needsManualReview") is True,
        })
    return sources


def _build_procedure_variant_context_block(
    visa_data: Optional[Dict[str, Any]],
    task_type: Optional[str],
    visa_sub_code: Optional[str] = None,
    *,
    user_text: Optional[str] = None,
    selected_procedure_key: Optional[str] = None,
    selected_procedure_variant_id: Optional[str] = None,
) -> str:
    """Build compact needs-review prompt context for scenario variants.

    This local catalog block is intentionally weaker than deterministic manual
    grounding and HIGH / STRUCTURED_EVIDENCE_READY structured requirements.
    """
    procedure_key, variants = _select_procedure_variants(
        visa_data,
        task_type,
        visa_sub_code,
        user_text=user_text,
        selected_procedure_key=selected_procedure_key,
        selected_procedure_variant_id=selected_procedure_variant_id,
    )
    if not procedure_key or not variants or not isinstance(visa_data, dict):
        return ""

    MAX_FIELD = 180
    MAX_DOCS_PER_GROUP = 5
    MAX_NOTES = 3

    def _trim(value: Any, limit: int = MAX_FIELD) -> str:
        text = str(value or "").strip()
        return (text[:limit].rstrip() + "…") if len(text) > limit else text

    lines = [
        f"- parent visa code: {_trim(visa_data.get('code'))}",
        f"- procedure key: {procedure_key}",
    ]
    for variant in variants:
        lines.append(f"- variant id: {_trim(variant.get('id'))}")
        label = _trim(variant.get("labelKo") or variant.get("label"))
        if label:
            lines.append(f"  - label: {label}")
        status_code = _trim(variant.get("statusCode"))
        if status_code:
            lines.append(f"  - status code: {status_code}")
        scenario = _trim(variant.get("scenarioKo"))
        if scenario:
            lines.append(f"  - applies only when: {scenario}")

        required_docs = variant.get("requiredDocs")
        if isinstance(required_docs, dict):
            for group in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"):
                items = required_docs.get(group)
                if not isinstance(items, list) or not items:
                    continue
                lines.append(f"  - {group}:")
                for item in items[:MAX_DOCS_PER_GROUP]:
                    text = _trim(item)
                    if text:
                        lines.append(f"    - {text}")

        notes = variant.get("notes")
        if isinstance(notes, list) and notes:
            lines.append("  - notes:")
            for note in notes[:MAX_NOTES]:
                text = _trim(note)
                if text:
                    lines.append(f"    - {text}")

        refs = variant.get("manualRefs")
        if isinstance(refs, list) and refs:
            ref = refs[0] if isinstance(refs[0], dict) else {}
            source_bits = [
                _trim(ref.get("manualName")),
                _trim(ref.get("manualVersion")),
                _trim(ref.get("pageRange")),
                _trim(ref.get("sourceFile")),
            ]
            lines.append("  - manual ref: " + " · ".join(bit for bit in source_bits if bit))
            lines.append(f"  - needsManualReview: {ref.get('needsManualReview') is True}")

    header = (
        "[Manual-backed local procedure variant context — needs review]\n"
        "The checklist items below are scenario-specific local catalog records"
        " extracted from the cited official manual pages. They are not final"
        " source-confirmed determinations. Do not generalize them to all users"
        " under the parent visa. Use a checklist only if the labeled scenario"
        " matches the user's facts; otherwise say it may not apply. Do not invent"
        " missing documents, deadlines, fees, or legal citations."
        " needsManualReview: true means the user must verify the applicable"
        " checklist with HiKorea, 1345, or the competent immigration office."
    )
    return header + "\n" + "\n".join(lines)


_STRUCTURED_PROCEDURE_BY_TASK = {
    "extension": "extension",
    "foreigner_registration": "registration",
}


def _matching_source_confirmed_structured_requirements(
    visa_code: Optional[str],
    visa_sub_code: Optional[str] = None,
    task_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return direct structured evidence only for the asked procedure/scope."""
    if _structured_requirements is None or not visa_code:
        return []
    procedure_type = _STRUCTURED_PROCEDURE_BY_TASK.get(task_type or "")
    # A classified procedure with no exact structured equivalent is a mismatch,
    # not permission to use every record for the same status.
    if task_type and procedure_type is None:
        return []
    options = {"procedureType": procedure_type} if procedure_type else None
    try:
        entries = _structured_requirements.get_source_confirmed_structured_requirements(
            visa_code, options
        )
    except Exception:  # pragma: no cover - defensive only
        return []
    if not visa_sub_code:
        return entries
    scoped: List[Dict[str, Any]] = []
    for entry in entries:
        exact = entry.get("subCode")
        covered = entry.get("subCodesCovered") or []
        # Parent-code-level entries apply to every sub-code; explicitly scoped
        # entries must match the user's exact sub-code.
        if not exact and not covered:
            scoped.append(entry)
        elif exact == visa_sub_code or visa_sub_code in covered:
            scoped.append(entry)
    return scoped


def _structured_requirement_source_summaries(
    entries: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for entry in entries:
        manual = entry.get("manualSource") or {}
        start, end = manual.get("pageStart"), manual.get("pageEnd")
        page_range = f"{start}-{end}" if start and end and start != end else str(start or "")
        summaries.append({
            "source_type": "manual",
            "source_file": manual.get("file") or "",
            "source_title": manual.get("manualName") or "Stay Manual",
            "source_date": manual.get("manualVersion") or "",
            "visa_code": entry.get("statusCode") or "",
            "procedure_type": entry.get("procedureType") or "",
            "section": manual.get("sectionTitle") or "",
            "page_range": page_range,
            "source_verification_status": "verified",
            "source_confidence": "HIGH",
            "query": " ".join(filter(None, [
                str(entry.get("statusCode") or ""),
                str(entry.get("procedureType") or ""),
                str(manual.get("sectionTitle") or ""),
            ])),
        })
    return summaries


def _build_source_confirmed_structured_requirements_block(
    visa_code: Optional[str],
    visa_sub_code: Optional[str] = None,
    task_type: Optional[str] = None,
) -> str:
    """Build a prompt block from SOURCE-CONFIRMED structured requirements.

    Only entries that are HIGH confidence AND STRUCTURED_EVIDENCE_READY are
    surfaced (the `structured_requirements` accessor enforces this). Candidate
    / needs-review entries are never included. Returns "" when the optional
    module is unavailable or the status has no source-confirmed entries, so
    callers can skip the block with zero behavior change.

    This block SUPPLEMENTS existing manual grounding; it must not override
    canonical warnings, disclaimers, or manualRefs.
    """
    entries = _matching_source_confirmed_structured_requirements(
        visa_code, visa_sub_code, task_type
    )
    if not entries:
        return ""

    MAX_DOCS = 12

    def _trim(value: Any, limit: int = 200) -> str:
        s = str(value or "").strip()
        return (s[:limit].rstrip() + "…") if len(s) > limit else s

    lines: List[str] = []
    for e in entries:
        ms = e.get("manualSource") or {}
        ps, pe = ms.get("pageStart"), ms.get("pageEnd")
        if ps and pe and ps != pe:
            page = f"pp. {ps}-{pe}"
        elif ps:
            page = f"p. {ps}"
        else:
            page = ""
        scope = e.get("subCode")
        covered = e.get("subCodesCovered") or []
        if covered:
            scope = ", ".join(covered)
        scope_note = f" (적용 세부약호: {scope})" if scope else ""
        header_bits = [b for b in (
            _trim(ms.get("sectionTitle"), 120),
            e.get("procedureType"),
            page,
        ) if b]
        lines.append(
            f"- {visa_code}{scope_note} — " + " · ".join(header_bits)
        )
        for d in (e.get("documents") or [])[:MAX_DOCS]:
            txt = _trim(d.get("textKo"), 200) if isinstance(d, dict) else ""
            if txt:
                lines.append(f"    • {txt}")

    if not lines:
        return ""

    header = (
        "[Source-confirmed structured requirements from current official manuals]\n"
        "The items below were locally verified against the current official"
        " manual source at the cited page(s) and are limited to the exact section/"
        "sub-code scope shown. They SUPPLEMENT — and do not override — the"
        " manual grounding, warnings, disclaimers, and page references above."
        " Do not generalize a sub-code-scoped list to other sub-codes, and do"
        " not present this as a final immigration-office determination."
    )
    return f"{header}\n" + "\n".join(lines)


def _build_ungrounded_korea_scoped_prompt(
    user_prompt: str,
    *,
    visa_code: Optional[str] = None,
    visa_sub_code: Optional[str] = None,
    task_type: Optional[str] = None,
    risk_level: str = "low",
    lang: Optional[str] = None,
) -> str:
    """Build a Korea-immigration-scoped system prompt for ungrounded answers.

    When no verified manual entry exists for the requested (visa_code,
    procedure_type) pair, the raw user prompt would be sent to the LLM with
    zero guardrails. This builder injects a scoped system role and explicit
    forbidden-content instructions so that:

    - the answer stays inside Korean immigration/stay-status context,
    - the model does not fabricate document lists, grace-period day counts,
      or legal citations,
    - generic global-immigration boilerplate (USCIS, Home Office, embassy)
      is excluded,
    - for high-risk tasks the model is instructed to surface missing facts
      and to mark every candidate pathway as "must be verified".

    This intentionally does NOT include source attribution from
    외국인체류 안내매뉴얼 — there is no verified grounding here.
    """
    answer_language_line = _answer_language_instruction(lang)

    code_label = visa_sub_code or visa_code or ""
    code_block = f"\n탐지된 체류자격: {code_label}" if code_label else ""
    task_label = task_type or ""
    task_block = f"\n탐지된 절차 유형: {task_label}" if task_label else ""

    # Conditional block for marriage/divorce + F-6 combination.
    f6_divorce_addendum = ""
    is_divorce = task_type == "marriage_divorce_status_change"
    is_f6 = (visa_code or "").startswith("F-6") or (visa_sub_code or "").startswith("F-6")
    if is_divorce and is_f6:
        f6_divorce_addendum = (
            "\n이혼·혼인단절 관련 F-6 체류자격 질문입니다. 아래를 반드시 준수하십시오:\n"
            "- F-6-1(국민의 배우자), F-6-2(자녀양육), F-6-3(혼인단절), F-1-6, E계열·D계열 등 전환 경로를"
            " 언급하는 경우, 각 경로마다 반드시 '관할 출입국·외국인청 또는 1345·HiKorea에서 확인 필요'라고 명시하십시오.\n"
            "- '이혼과 동시에 비자가 즉시 취소됩니다', '즉시 출국해야 합니다', '외국인등록증이 당일 말소됩니다' 등"
            " 즉각적 취소나 강제 출국에 관한 단정 표현을 사용하지 마십시오.\n"
            "- '현재 ARC 유효기간이 언제까지인지', '이혼이 최종 확정(협의이혼 또는 재판이혼)되었는지',"
            " '자녀의 유무·양육권·면접교섭권', '배우자 귀책사유(혼인단절)가 인정되는지',"
            " '독립적인 체류 자격(취업비자 등) 전환 가능성'을 사용자에게 확인하도록 요청하십시오.\n"
            "- 검증된 매뉴얼 발췌 없이 특정 제출서류 목록, 법령 조문 번호, 유예 기간(예: '30일') 등을"
            " 임의로 제시하지 마십시오."
        )
    elif is_divorce:
        f6_divorce_addendum = (
            "\n이혼·혼인단절 관련 질문입니다. 이혼은 체류자격에 중대한 영향을 줄 수 있으므로,"
            " 사안에 따라 결과가 달라집니다. 단정적인 표현을 피하고 관할 출입국·외국인청에"
            " 확인하도록 안내하십시오."
        )

    high_risk_addendum = ""
    if risk_level == "high":
        high_risk_addendum = (
            "\n[고위험 사안 지침]\n"
            "이 질문은 체류 지위에 중대한 영향을 미칠 수 있는 고위험 사안입니다.\n"
            "- 답변의 각 섹션(현재 알려진 사실 / 한국 체류 측면의 쟁점 / 가능한 경로(검증 필요) /"
            " 확인이 필요한 정보 / 다음 단계 / 출처 한계)을 명확히 구분하십시오.\n"
            "- 모든 경로 및 결과 예측에 '확인 필요(must be verified)' 표기를 포함하십시오.\n"
            "- '즉시', '반드시', '자동으로' 등 단정적 표현으로 결과를 예측하지 마십시오."
        )

    return (
        "당신은 한국 비자·체류 안내 도우미 Paradiso입니다. 대한민국 출입국·외국인 체류 제도의 범위 안에서만 답하십시오.\n"
        "본 답변은 검증된 매뉴얼 발췌가 없는 상황에서 제공되는 일반 안내입니다."
        " 이 답변은 공식 출입국·외국인정책본부 매뉴얼에 근거하지 않습니다.\n\n"
        "[금지 사항 — 반드시 준수]\n"
        "- 사용자가 다른 국가를 명시적으로 요청하지 않는 한, 비한국(non-Korean) 이민제도,"
        " 외국 행정기관, 외국 법률절차 보일러플레이트를 언급하지 마십시오.\n"
        "- 검증된 출처 없이 다음을 임의로 제시하지 마십시오: 제출서류, 기한/유예기간,"
        " 수수료/비용, 양식/서식 번호, 법령 조문 번호, 자격요건, 절차상 보장·결과 보장.\n"
        "- '본 답변은 외국인체류 안내매뉴얼에 근거합니다' 등 공식 매뉴얼 인용을 암시하는 표현을"
        " 사용하지 마십시오.\n"
        "- '해당 국가 기관에 문의', '현지 이민청에 문의', '외국 대사관/영사관 문의'"
        " 같은 외국 기관 유도 표현을 사용하지 마십시오.\n\n"
        "[탐지 정보]"
        f"{code_block}"
        f"{task_block}\n\n"
        f"{f6_divorce_addendum}"
        f"{high_risk_addendum}\n\n"
        "[답변 형식]\n"
        "긴 '현재 알려진 사실' 단락으로 시작하지 말고, 먼저 핵심에 대한 실용적인 답을 제시하십시오."
        " 아래 [답변 품질 지침]의 유연한 구조를 따르되, 단순한 질문에는 짧게, 복잡한 시나리오에만"
        " 깊이 있게 답하십시오. 같은 주의사항을 여러 번 반복하지 말고 한 번만 명확히 적으십시오."
        " 확인이 필요한 사항은 1345 외국인종합안내센터 · HiKorea · 관할 출입국·외국인청에"
        " 문의하도록 안내하십시오(미국·영국 등 타국 기관 제외).\n\n"
        "[답변 지침]\n"
        f"{answer_language_line}\n\n"
        "[사용자 질문]\n"
        f"{user_prompt}"
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> Dict[str, Any]:
    """Service-info page for humans who hit the bare backend URL.

    The Paradiso backend is API-only; the human-facing frontend is
    served elsewhere (currently GitHub Pages). Without this route,
    FastAPI returns a bare `{"detail":"Not Found"}` for `GET /`, which
    is confusing for anyone (especially mobile users) who opens the
    Railway URL directly. Returns a small JSON descriptor instead.
    """
    return {
        "service": "paradiso-backend",
        "status": "ok",
        "message": (
            "Paradiso backend is running. "
            "Use /health, /api/visas, /api/ask."
        ),
        "frontend": FRONTEND_URL or None,
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    llm = _resolve_llm_config()
    candidates = OPENROUTER_MODEL_CANDIDATES
    candidate_warnings = _validate_model_candidates(candidates)
    if llm.get("groq_fallback_allowed"):
        candidate_warnings = [*candidate_warnings, "PROVIDER_FAMILY_FALLBACK_ENABLED"]
    # Make a deploy-time env override of the answer model VISIBLE. The active
    # OPENROUTER_MODEL / *_CANDIDATES env vars override the committed code policy
    # default by design, so a stale Railway env var (e.g. an old pinned model)
    # silently keeps the live answer model on the old value even after the code
    # default is updated. Surfacing this turns that invisible override into an
    # obvious, diagnosable signal (model ids are public; no secrets here).
    _model_env_override = bool((os.environ.get("OPENROUTER_MODEL") or "").strip())
    _candidates_env_override = bool((os.environ.get("OPENROUTER_MODEL_CANDIDATES") or "").strip())
    if _model_env_override and OPENROUTER_MODEL != _DEFAULT_OPENROUTER_MODEL:
        candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_ENV_OVERRIDE"]
    if _candidates_env_override and candidates != list(_DEFAULT_OPENROUTER_MODEL_CANDIDATES):
        candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE"]
    # Non-secret Open Law API posture. NEVER exposes LAW_API_OC / LAW_API_KEY
    # values — only booleans, the resolved mode, and which env var supplied the
    # credential. Computed live so LAW_API_OC-only deployments report correctly.
    try:
        law_cfg = load_grounding_config()
        law_mode, law_effective_mode, law_grounding_active = _law_grounding_runtime_state(law_cfg)
        law_api_status: Dict[str, Any] = {
            "law_api_configured": law_cfg.law_api_configured,
            "law_api_oc_configured": law_cfg.law_api_oc_configured,
            "law_api_key_fallback_configured": law_cfg.law_api_key_fallback_configured,
            "law_api_credential_source": law_cfg.law_api_credential_source,
        }
    except Exception:  # pragma: no cover - defensive
        law_mode = (os.environ.get("LAW_GROUNDING_MODE") or "enabled").strip().lower()
        law_effective_mode = law_mode if LAW_API_KEY else ("disabled" if law_mode == "enabled" else law_mode)
        law_grounding_active = law_effective_mode in {"audit", "enabled"}
        law_api_status = {
            "law_api_configured": bool(LAW_API_KEY),
            "law_api_oc_configured": False,
            "law_api_key_fallback_configured": bool(LAW_API_KEY),
            "law_api_credential_source": "LAW_API_KEY" if LAW_API_KEY else "",
        }
    provider_status = {
        "openrouter": {"configured": bool(OPENROUTER_API_KEY), "enabled": llm["provider"] == "openrouter"},
        "groq": {"configured": bool(GROQ_API_KEY), "fallback_allowed": ALLOW_GROQ_FALLBACK},
        "law_grounding": {"mode": law_mode, "effective_mode": law_effective_mode},
        "legal_evidence": {"configured": bool(law_api_status["law_api_configured"])},
        "nvidia_nim": NvidiaNimProvider().health_check(),
    }
    return {
        "status": "ok",
        "service": "paradiso-backend",
        "version": app.version,
        "providers": _providers_configured(),
        "provider_status": provider_status,
        # Non-secret active LLM descriptor. Model ids are public catalog
        # identifiers; API keys are never included here. ``warnings`` flags the
        # Groq-fallback posture (e.g. GROQ_FALLBACK_ENABLED) so operators can see
        # at a glance whether strict OpenRouter-first is in effect.
        "llm": {
            "provider": llm["provider"],
            "model": llm["model"],
            "configured": llm["configured"],
            "groq_fallback_allowed": llm["groq_fallback_allowed"],
            "warnings": llm.get("warnings", []),
            # OpenRouter candidate fallback posture (non-secret).
            "primary_model": OPENROUTER_MODEL,
            "model_candidates": candidates,
            # Committed code-policy default + whether an env var is overriding it,
            # so "the answer model did not update after merge" is self-diagnosing:
            # if model_env_override is true and primary_model != code_default_model,
            # a deploy env var (e.g. a stale Railway OPENROUTER_MODEL) is pinning it.
            "code_default_model": _DEFAULT_OPENROUTER_MODEL,
            "code_default_model_candidates": list(_DEFAULT_OPENROUTER_MODEL_CANDIDATES),
            "model_env_override": _model_env_override or _candidates_env_override,
            "provider_family_fallback_allowed": llm["groq_fallback_allowed"],
            "candidate_warnings": candidate_warnings,
            **_openrouter_cooldown_metadata(),
            "ollama_fallback_enabled": ENABLE_OLLAMA_FALLBACK,
            "ollama_model": OLLAMA_MODEL,
            "ollama_configured": bool(ENABLE_OLLAMA_FALLBACK and OLLAMA_BASE_URL),
            "ollama_timeout_seconds": OLLAMA_TIMEOUT_SECONDS,
        },
        # Single source of truth (default "enabled"); was previously hardcoded to
        # "disabled" here, which misreported active deployments. `effective` and
        # `active` make the enabled-without-credential degradation explicit so an
        # operator can see at a glance whether real-time law calls actually fire.
        "law_grounding_mode": law_mode,
        "law_grounding_effective_mode": law_effective_mode,
        "law_grounding_active": law_grounding_active,
        # Granular, non-secret Open Law API configuration flags (Part A).
        "law_api": law_api_status,
    }


def _enrich_with_source_confirmed_requirements(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Return records with an additive ``sourceConfirmedStructuredRequirements``
    field on any status that has HIGH / STRUCTURED_EVIDENCE_READY entries.

    Additive and backward-compatible: records without source-confirmed entries
    are returned unchanged (same object), and the record count is preserved.
    Candidate / needs-review entries are never included.
    """
    if _structured_requirements is None:
        return records
    out: List[Dict[str, Any]] = []
    for rec in records:
        code = rec.get("code") if isinstance(rec, dict) else None
        summaries: List[Dict[str, Any]] = []
        if code:
            try:
                entries = _structured_requirements.get_source_confirmed_structured_requirements(code)
                summaries = [_structured_requirements.public_summary(e) for e in entries]
            except Exception:  # pragma: no cover - defensive only
                summaries = []
        if summaries:
            enriched = dict(rec)
            enriched["sourceConfirmedStructuredRequirements"] = summaries
            out.append(enriched)
        else:
            out.append(rec)
    return out


@app.get("/api/visas")
async def list_visas() -> Dict[str, Any]:
    """Return the visa catalog.

    Response shape preserves backwards-compatibility with frontend
    consumers that read either a bare array or `{data: [...]}`:

    - `data`: list of visa records (frontend's `parse()` reads this)
    - `visas`: same list under the explicit name used by newer code
    - `count`: convenience integer
    - `warning`: present only when DEFAULT_VISAS fallback is in use

    Records for statuses with source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY)
    structured requirements carry an additive
    ``sourceConfirmedStructuredRequirements`` field; all other records are
    unchanged. Needs-review candidate evidence is never exposed here.
    """
    cached = _load_visas()
    visas = _enrich_with_source_confirmed_requirements(cached["visas"])
    payload: Dict[str, Any] = {
        "count": len(visas),
        "data": visas,
        "visas": visas,
        "source": cached.get("source", "unknown"),
        "source_type": cached.get("source_type", "unknown"),
    }
    if "warning" in cached:
        payload["warning"] = cached["warning"]
    return payload


@app.get("/api/visas/{status_code}/structured-requirements")
async def get_structured_requirements_endpoint(
    status_code: str, include_needs_review: bool = False
) -> Dict[str, Any]:
    """Return structured requirements for a status.

    Default: ONLY source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY) entries,
    projected to the safe user-facing shape. ``include_needs_review=1`` is an
    INTERNAL/debug flag that returns raw candidate entries too — these must not
    be shown to end users.
    """
    if _structured_requirements is None:
        return {"statusCode": status_code, "sourceConfirmed": [], "available": False}
    confirmed = _structured_requirements.get_source_confirmed_structured_requirements(status_code)
    payload: Dict[str, Any] = {
        "statusCode": status_code,
        "available": True,
        "sourceConfirmedCount": len(confirmed),
        "sourceConfirmed": [_structured_requirements.public_summary(e) for e in confirmed],
    }
    if include_needs_review:
        all_entries = _structured_requirements.get_structured_requirements(
            status_code, {"includeNeedsReview": True}
        )
        needs_review = [e for e in all_entries if not _structured_requirements.is_source_confirmed(e)]
        payload["internalNeedsReviewCount"] = len(needs_review)
        payload["internalNeedsReview"] = needs_review
        payload["internalWarning"] = (
            "Entries under internalNeedsReview are unverified candidate evidence "
            "and must not be shown to end users."
        )
    return payload


@app.get("/api/procedure-packet")
async def get_procedure_packet_endpoint(
    status: str, procedure: str, locale: str = "ko"
) -> Dict[str, Any]:
    """Build a source-graded procedure preparation packet (deterministic).

    Inputs are non-personal only: ``status`` (a status/visa code, parent or
    exact sub-code) and ``procedure`` (a procedure key such as
    ``registration``/``extension``/``statusChange`` or a public packet type such
    as ``foreigner_registration``). No personal field values are accepted or
    stored, no LLM is called, and the output carries only public-safe source
    labels (never raw developer diagnostics). The packet's
    ``applicationTypingHelper`` is typing-guide-only and never holds values.
    """
    if _build_procedure_packet is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "packet_builder_unavailable",
                    "message": "Procedure packet builder is not available."},
        )
    status_code = (status or "").strip()
    procedure_key = (procedure or "").strip()
    if not status_code or not procedure_key:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_parameters",
                    "message": "Provide non-empty 'status' and 'procedure'."},
        )
    packet = _build_procedure_packet(status_code, procedure_key, locale=locale or "ko")
    if packet.get("packetType") == "unknown":
        raise HTTPException(
            status_code=400,
            detail={"error": "unsupported_procedure",
                    "message": "요청한 절차 유형을 인식할 수 없습니다.",
                    "supportedPacketTypes": list(_SUPPORTED_PACKET_TYPES)},
        )
    return packet


@app.get("/api/visas/{status_code}/packets")
async def get_available_packets_endpoint(
    status_code: str, locale: str = "ko"
) -> Dict[str, Any]:
    """List preparation packets buildable for a status (deterministic, no LLM)."""
    if _build_available_packets_for_status is None:
        return {"statusCode": status_code, "available": False, "packets": []}
    summaries = _build_available_packets_for_status(status_code, locale=locale or "ko")
    return {
        "statusCode": status_code,
        "available": bool(summaries),
        "packetCount": len(summaries),
        "packets": summaries,
    }


# Legal-issue dimensions for which supplementary case law / adjudication
# decisions add genuine value (adjudicative / discretionary / remedy / overstay /
# refugee / status-change / extension). Routine document/registration lookups are
# intentionally excluded so case-law retrieval never fires for them.
_CASE_LAW_WARRANTED_ISSUES = frozenset({
    "denial_revocation_or_remedy", "constitutional_or_fundamental_rights",
    "discretionary_or_ambiguous_interpretation", "overstay_or_risk",
    "nationality_or_refugee_context", "status_change", "extension",
    "activity_scope", "outside_status_activity",
})
# Issues where administrative-appeal (행정심판 재결례) is most relevant.
_ADMIN_APPEAL_WARRANTED_ISSUES = frozenset({
    "denial_revocation_or_remedy", "overstay_or_risk",
    "discretionary_or_ambiguous_interpretation",
})


def _maybe_retrieve_legal_evidence(
    prompt: str,
    *,
    answer_mode: str,
    effective_mode: str,
    grounding_cfg,
    law_intent: bool,
    law_evidence_pack: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Gated, supplementary 판례/재결례 retrieval for /api/ask.

    SEPARATE from the manual/statute pipeline and SUPPLEMENTARY only — manuals,
    statutes, and official guidance remain primary. It fires (in BOTH Fast and
    Basic modes; Fast uses a lighter case budget) when:
      * law grounding is actually active (audit/enabled + credential),
      * the question carries legal intent AND a case-law-warranted issue.
    Never raises; any failure degrades to a skip/unavailable status so it can
    never break Fast/Basic routing or the request.
    """
    meta: Dict[str, Any] = {
        "legal_evidence": None,
        "legal_evidence_status": "not_attempted",
        "legal_evidence_used": False,
        "legal_evidence_cases": [],
        "legal_evidence_source_types": [],
        "legal_evidence_prompt": "",
    }
    if effective_mode not in {"audit", "enabled"} or not law_intent:
        return meta

    issues = list((law_evidence_pack or {}).get("legal_issue_types") or [])
    if not (set(issues) & _CASE_LAW_WARRANTED_ISSUES):
        meta["legal_evidence_status"] = "not_warranted"
        return meta

    try:
        from services.evidence_ontology import ISSUE_CONCEPT_KO

        source_types = [legal_evidence.LegalEvidenceSourceType.PRECEDENT]
        if set(issues) & _ADMIN_APPEAL_WARRANTED_ISSUES:
            source_types.append(legal_evidence.LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL)
        issue_concepts = [ISSUE_CONCEPT_KO[i] for i in issues if i in ISSUE_CONCEPT_KO]
        statute_refs = [
            s.get("law_name", "") for s in (law_evidence_pack or {}).get("law_sources", []) if s.get("law_name")
        ][:5]

        # Real-time case-law lookup runs in BOTH Fast and Basic modes. Fast keeps a
        # lighter budget (fewer cases) so it stays snappy while still surfacing live
        # 판례/재결례 citations; the in-memory cache makes repeat queries cheap.
        max_cases = 2 if answer_mode == "fast" else 3
        result = legal_evidence.retrieve_legal_evidence(
            prompt,
            source_types=source_types,
            issue_concepts=issue_concepts,
            statute_refs=statute_refs,
            config=dataclasses.replace(grounding_cfg, mode=effective_mode),
            max_cases=max_cases,
        )
    except Exception:  # pragma: no cover - case law must never break /api/ask
        meta["legal_evidence_status"] = "error"
        return meta

    meta["legal_evidence"] = result.to_dict()
    meta["legal_evidence_status"] = result.status
    meta["legal_evidence_source_types"] = list(result.source_types)
    meta["legal_evidence_cases"] = list(result.citations)
    meta["legal_evidence_used"] = result.status == "available" and bool(result.cases)
    if meta["legal_evidence_used"]:
        meta["legal_evidence_prompt"] = _render_legal_evidence_prompt(result)
    return meta


def _render_legal_evidence_prompt(result) -> str:
    """Compact, safe prompt rendering of the top case-law evidence: the directive
    plus citations and the preferred chunks (판시사항/판결요지/참조조문 + top
    reasoning). Never the raw full body; never invents anything."""
    lines: List[str] = [legal_evidence.LEGAL_EVIDENCE_PROMPT_DIRECTIVE, ""]
    for case in result.cases[:3]:
        cite = case.citation()
        head = (
            f"- [{cite['source_type']}] {cite['case_name']} "
            f"({cite['case_number']}, {cite['court_or_tribunal']}, {cite['decision_date']}) "
            f"[id:{cite['retrieved_source_id']}]"
        )
        lines.append(head)
        for chunk in case.chunks[:4]:
            text = (chunk.text or "").strip()
            if text:
                lines.append(f"    · {chunk.label}: {text[:280]}")
    lines.append("")
    lines.append(legal_evidence.CASE_LAW_CAUTION_KO)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trust & Safety guardrail integration helpers
# ---------------------------------------------------------------------------
def _safety_history_texts(req: "AskRequest") -> List[Any]:
    """Best-effort extraction of recent turns for repeat-abuse detection.

    The classifier itself defensively handles strings or {role, content} dicts;
    here we just forward whatever the client sent without trusting its shape.
    """
    history = req.history if isinstance(req.history, list) else []
    return history[-8:]


def _build_safety_refusal_response(
    decision: "safety_guardrails.SafetyDecision",
    *,
    lang: Optional[str],
    event_id: str,
) -> "AskResponse":
    """Construct the user-facing refusal for a blocking safety decision.

    No model is called. The copy is neutral and non-accusatory, and includes the
    lawful topics Waymaker can still help with. The frontend renders this as a
    visually distinct (but not alarming) safety card.
    """
    refusal_text, alternatives = safety_guardrails.refusal_copy(decision)
    is_en = decision.language == "en"
    alt_heading = "What I can help with instead:" if is_en else "대신 안내할 수 있는 정보:"
    answer_text = refusal_text + "\n\n" + alt_heading + "\n" + "\n".join(
        f"- {item}" for item in alternatives
    )
    return AskResponse(
        answer=answer_text,
        copy_safe_answer=answer_text,
        provider="safety_guardrail",
        model=safety_guardrails.SAFETY_VERSION,
        llm_provider="safety_guardrail",
        # Coarse, non-secret safety signals for the frontend.
        safety_action=decision.action,
        safety_blocked=True,
        safety_category=decision.category,
        safety_severity=decision.severity,
        safety_reason=decision.reason,
        safety_alternatives=alternatives,
        safety_event_id=event_id,
        # This answer is intentionally NOT a grounded legal answer; keep the
        # source/quality contract honest so no "grounded" chip is shown.
        answer_quality_mode="safety_refusal",
        source_confidence_level="none",
        requires_official_confirmation=False,
        grounded_answer_limited=False,
        question_type_detected="safety",
    )


def _evaluate_request_safety(
    prompt: str, req: "AskRequest"
) -> "safety_guardrails.SafetyDecision":
    """Run the deterministic guardrail. Never raises — a guardrail crash must
    not break /api/ask, but it also must not silently allow: on an unexpected
    internal error we conservatively return a generic block."""
    try:
        return safety_guardrails.classify_request(
            prompt, lang=req.lang, history=_safety_history_texts(req)
        )
    except Exception:  # pragma: no cover - defensive; classifier is pure/total
        logger.exception("safety guardrail classifier raised; failing closed")
        return safety_guardrails.SafetyDecision(
            action=safety_guardrails.ACTION_BLOCK,
            category=safety_guardrails.CAT_SAFE,
            severity=3,
            reason="guardrail_internal_error",
            matched_signals=["guardrail.internal_error"],
            language=safety_guardrails.detect_language(prompt, req.lang),
        )


@app.post(
    "/api/ask",
    response_model=AskResponse,
    # Per-client sliding-window limit (H-1a); covers stream AND buffered paths.
    dependencies=[Depends(rate_limit("ask", per_minute=8, per_day=300))],
)
async def ask(req: AskRequest) -> AskResponse:
    prompt = (req.message or req.query or req.question or "").strip()
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_prompt",
                "message": "Provide a non-empty 'message', 'query', or 'question'.",
            },
        )
    # ------------------------------------------------------------------
    # Input caps (H-1c). Every limit sits comfortably above the largest
    # legitimate frontend payload (see the ASK_MAX_* constants): a too-long
    # prompt is a clear 400; oversized history/context are safely truncated
    # (they never feed the answer prompt); an absurdly large visa_data blob
    # is a 400 rather than silently degraded grounding.
    # ------------------------------------------------------------------
    if len(prompt) > ASK_MAX_PROMPT_CHARS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_too_long",
                "status": 400,
                "message": (
                    f"The question is too long ({len(prompt)} chars); "
                    f"the maximum is {ASK_MAX_PROMPT_CHARS} characters."
                ),
            },
        )
    if isinstance(req.history, list) and req.history:
        capped_history: List[Dict[str, Any]] = []
        for item in req.history[-ASK_MAX_HISTORY_ITEMS:]:
            if not isinstance(item, dict):
                continue
            # Only role/content are ever consumed (safety repeat-abuse check);
            # keeping just those two bounds memory regardless of extra keys.
            content = item.get("content")
            if isinstance(content, str) and len(content) > ASK_MAX_HISTORY_ITEM_CHARS:
                content = content[:ASK_MAX_HISTORY_ITEM_CHARS]
            capped_history.append({"role": item.get("role"), "content": content})
        req.history = capped_history
    if isinstance(req.context, str) and len(req.context) > ASK_MAX_CONTEXT_CHARS:
        req.context = req.context[:ASK_MAX_CONTEXT_CHARS]
    if req.visa_data is not None:
        try:
            visa_data_size = len(json.dumps(req.visa_data, ensure_ascii=False))
        except (TypeError, ValueError):  # non-serializable shapes handled downstream
            visa_data_size = 0
        if visa_data_size > ASK_MAX_VISA_DATA_CHARS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "visa_data_too_large",
                    "status": 400,
                    "message": (
                        f"The visa_data payload is too large ({visa_data_size} chars serialized); "
                        f"the maximum is {ASK_MAX_VISA_DATA_CHARS} characters."
                    ),
                },
            )

    # ------------------------------------------------------------------
    # First-stage Trust & Safety guardrail (deterministic, pre-generation).
    # Runs BEFORE any grounding work or model call so blocked requests never
    # reach an LLM provider. A "block"/"escalate"/"emergency_review" decision
    # returns a neutral refusal + lawful alternatives; "escalate"/"emergency"
    # additionally log a redacted, data-minimized safety event for manual
    # review. "warn" and "allow" continue the normal flow.
    # ------------------------------------------------------------------
    safety_decision = _evaluate_request_safety(prompt, req)
    if safety_decision.blocked:
        safety_event_id = ""
        if safety_decision.should_log:
            safety_event_id = safety_events.log_safety_event(
                action=safety_decision.action,
                category=safety_decision.category,
                severity=safety_decision.severity,
                reason=safety_decision.reason,
                matched_signals=safety_decision.matched_signals,
                input_text=prompt,
                language=safety_decision.language,
                route="/api/ask",
                request_id=req.selected_procedure_variant_id or None,
            )
        return _build_safety_refusal_response(
            safety_decision, lang=req.lang, event_id=safety_event_id
        )
    # Non-blocking decisions ("allow"/"warn") carry coarse safety metadata
    # through every downstream response path for transparency.
    safety_meta: Dict[str, Any] = {
        "safety_action": safety_decision.action,
        "safety_blocked": False,
        "safety_category": safety_decision.category,
        "safety_severity": safety_decision.severity,
        "safety_reason": safety_decision.reason,
    }
    if safety_decision.action == safety_guardrails.ACTION_WARN:
        safety_meta["safety_notice"] = safety_guardrails.warn_caution(safety_decision)

    visa_code_detected, visa_sub_code_detected = _detect_visa_codes(
        req.visa_code, req.visa_data, prompt
    )
    task_type_detected = _detect_task_type(prompt)
    risk_level_detected = _risk_level_for_task(task_type_detected)
    grounding = _select_grounding(
        visa_code_detected, task_type_detected, visa_sub_code_detected
    )
    grounding_sources: List[Dict[str, Any]] = []
    visa_data_block = _build_visa_data_context_block(req.visa_data)
    procedure_variant_block = _build_procedure_variant_context_block(
        req.visa_data,
        task_type_detected,
        visa_sub_code_detected,
        user_text=prompt,
        selected_procedure_key=req.selected_procedure_key,
        selected_procedure_variant_id=req.selected_procedure_variant_id,
    )
    procedure_variant_context_sources = _procedure_variant_context_sources(
        req.visa_data,
        task_type_detected,
        visa_sub_code_detected,
        user_text=prompt,
        selected_procedure_key=req.selected_procedure_key,
        selected_procedure_variant_id=req.selected_procedure_variant_id,
    )
    # The API path must know which procedure the user is asking about before
    # promoting same-status structured records to direct evidence.  The helper
    # retains its task-less compatibility behavior for internal/reporting
    # callers, but an unclassified /api/ask request gets no direct structured
    # evidence rather than every record for that status.
    structured_entries = (
        _matching_source_confirmed_structured_requirements(
            visa_code_detected, visa_sub_code_detected, task_type_detected
        )
        if task_type_detected
        else []
    )
    structured_procedure_mismatch = False
    if _structured_requirements is not None and visa_code_detected and task_type_detected:
        try:
            structured_procedure_mismatch = bool(
                _structured_requirements.get_source_confirmed_structured_requirements(visa_code_detected)
            ) and not bool(structured_entries)
        except Exception:  # pragma: no cover - optional evidence must not break /api/ask
            structured_procedure_mismatch = False
    structured_sources = _structured_requirement_source_summaries(structured_entries)
    structured_block = (
        _build_source_confirmed_structured_requirements_block(
            visa_code_detected, visa_sub_code_detected, task_type_detected
        )
        if task_type_detected
        else ""
    )
    if grounding is not None:
        bundle = _load_stay_manual_grounding() or {}
        final_prompt = _build_grounded_prompt(prompt, grounding, bundle, lang=req.lang)
        grounding_sources = [_grounding_source_summary(grounding, bundle)]
        if visa_data_block:
            # Manual grounding above remains primary; the local catalog block
            # is appended as supplemental context only and must not be used
            # to override the verified manual content.
            final_prompt += (
                "\n\n[Supplemental — local catalog context]\n"
                "The manual grounding above remains the primary source."
                " The block below is reference-only and must not override it.\n\n"
                + visa_data_block
            )
    else:
        final_prompt = _build_ungrounded_korea_scoped_prompt(
            prompt,
            visa_code=visa_code_detected,
            visa_sub_code=visa_sub_code_detected,
            task_type=task_type_detected,
            risk_level=risk_level_detected,
            lang=req.lang,
        )
        if visa_data_block:
            final_prompt += "\n\n" + visa_data_block

    if procedure_variant_block:
        # Needs-review local manual context only. This is weaker than both
        # deterministic grounding and HIGH / STRUCTURED_EVIDENCE_READY
        # structured requirements, and never flips grounding_used.
        final_prompt += "\n\n" + procedure_variant_block

    if structured_block:
        # Source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY) only. Supplements
        # the grounding/disclaimers above; never overrides them.
        final_prompt += "\n\n" + structured_block

    # Law grounding metadata. Intent is computed for EVERY question so the
    # source panel can honestly distinguish "not_attempted" (no legal intent)
    # from "disabled" (intent detected but the feature is off) from
    # "unavailable" / "used". External law-API calls still only happen when
    # LAW_GROUNDING_MODE is audit/enabled (default disabled, safe-by-default).
    law_grounding_used = False
    law_grounding_attempted = False
    law_grounding_status = "not_attempted"
    law_grounding_intent_reasons: List[str] = []
    law_search_query = ""
    law_search_queries: List[str] = []
    law_grounding_warnings: List[str] = []
    citation_verification: Optional[Dict[str, Any]] = None
    law_context: Dict[str, Any] = {}
    # Single source of truth for the grounding mode (default "enabled"): the same
    # config the preflight/debug endpoints and the evidence pack read.
    #
    # IMPORTANT: full activation ("enabled") only HELPS when a credential
    # (LAW_API_OC / legacy LAW_API_KEY) is present. Without one, an "enabled"
    # deploy used to push EVERY legal question into the "law unavailable" hedge
    # path (manual-to-law fallback + downgraded confidence), producing degraded
    # "source-limited preparation note" answers instead of normal helpful ones.
    # So when enabled-but-uncredentialed, behave like "disabled" for the user
    # answer (no external call, no hedging, no downgrade). The moment LAW_API_OC
    # is set, this becomes fully active with no code change. The diagnostic
    # "audit" mode is intentionally left untouched (operators opt into it).
    grounding_cfg = load_grounding_config()
    mode, effective_mode, _law_active = _law_grounding_runtime_state(grounding_cfg)
    intent = should_attempt_law_grounding(prompt)
    if intent.get("should_attempt"):
        law_grounding_intent_reasons = list(intent.get("reasons", []) or [])
        if effective_mode in {"audit", "enabled"}:
            law_context = build_law_grounding_context(prompt)
            law_grounding_attempted = bool(law_context.get("attempted"))
            law_grounding_used = bool(law_context.get("law_grounding_used"))
            law_grounding_warnings = law_context.get("grounding_warnings", []) or []
            citation_verification = law_context.get("citation_verification")
            law_search_query = law_context.get("law_search_query", "") or ""
            law_search_queries = list(law_context.get("law_search_queries") or [])
            law_grounding_status = "used" if law_grounding_used else "unavailable"
            # The normalized law evidence is injected below via the structured
            # evidence pack (a single compact summary), not as a second raw dump.
        else:
            # Off (or enabled-without-credential): surface the query that WOULD be
            # issued, make NO external call, and do NOT degrade the answer.
            law_grounding_status = "disabled"
            law_search_query = build_law_search_query(prompt, law_grounding_intent_reasons)
            law_search_queries = build_law_search_queries(prompt, law_grounding_intent_reasons)
            law_grounding_warnings = (
                ["LAW_GROUNDING_DISABLED"] if mode == "disabled"
                else ["LAW_GROUNDING_NOT_CONFIGURED"]
            )

    if citation_verification is None:
        extracted_citations = extract_korean_legal_citations(prompt)
        if extracted_citations.get("citations"):
            citation_verification = {
                **extracted_citations,
                "citation_specific": True,
            }
            law_context["citation_verification"] = citation_verification

    # Granular, user-visible law-grounding status (single source of truth). This
    # distinguishes not_attempted / disabled / audit_only / verified /
    # attempted_no_results / attempted_failed so the UI never implies the answer
    # is real-time-law-grounded when it is not, and the citation guardrail below
    # knows whether specific 조문 numbers may be trusted.
    law_grounding_status_detail = derive_law_grounding_status_detail(
        configured_mode=mode,
        effective_mode=effective_mode,
        intent_attempted=bool(intent.get("should_attempt")),
        lookup_attempted=law_grounding_attempted,
        lookup_used=law_grounding_used,
        citation_specific=bool((citation_verification or {}).get("citation_specific")),
        citation_verified=(citation_verification or {}).get("status") == "verified",
        error_type=(law_context or {}).get("error_type", ""),
        warnings=law_grounding_warnings,
    )
    law_grounding_verified = law_grounding_status_detail_is_verified(law_grounding_status_detail)
    law_grounding_retrieval_timestamp = (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if law_grounding_attempted else ""
    )

    # Manual-to-law fallback policy. When NO deterministic manual / source-
    # confirmed structured requirements grounding was found for a legal or
    # activity-scope question (legal basis, activity scope, reporting/permission
    # duty, deadlines, status-change/extension framing, etc.), lean on law
    # grounding for legal CONTEXT instead of generic-only guidance. This never
    # fabricates a required-document checklist — manual/HiKorea/office sources
    # remain authoritative for documents, fees, and operational steps.
    manual_present = (grounding is not None) or bool(structured_block)
    manual_grounding_status = "present" if manual_present else "absent"
    manual_to_law_fallback_used = False
    manual_to_law_fallback_reason = ""
    if not manual_present and intent.get("should_attempt"):
        if effective_mode in {"audit", "enabled"}:
            manual_to_law_fallback_used = True
            manual_to_law_fallback_reason = "manual_grounding_absent_law_intent"
            # Tell the model to frame the answer honestly: manual-specific
            # document guidance was not found, legal context may still apply,
            # and it must NOT invent a document checklist.
            final_prompt += (
                "\n\n[Manual-to-law fallback]\n"
                "- Specific manual document guidance was NOT found for this question.\n"
                "- Do NOT invent or imply a required-document checklist.\n"
                "- You MAY explain legal basis, activity scope, activities outside status,"
                " permission/reporting duties, deadlines, and definitions in general terms.\n"
                "- State that manual-specific guidance was not found and that these points"
                " should be confirmed with HiKorea / 1345 / the competent immigration office.\n"
                "- Preserve official Korean legal/administrative terms; any English/Chinese"
                " rendering is a non-authoritative helper, not an official translation."
            )
        else:
            # Fallback was warranted but law grounding is disabled by config.
            # Expose the state without making any external call.
            manual_to_law_fallback_reason = "manual_grounding_absent_law_intent_grounding_disabled"

    # General answer-quality contract. Folds the grounding state above + the
    # question's user intent into (a) non-secret response metadata for honest
    # source/state chips and (b) prompt directives that make the answer read
    # like a careful modern assistant (direct first, readable, source-aware,
    # not a wall of warnings). This NEVER changes provider/model selection.
    quality = classify_answer_quality(
        prompt=prompt,
        visa_code=visa_code_detected,
        task_type=task_type_detected,
        manual_grounding_present=(grounding is not None),
        structured_requirements_present=bool(structured_block),
        procedure_variant_present=bool(procedure_variant_block),
        law_grounding_used=law_grounding_used,
        law_grounding_status=law_grounding_status,
        manual_to_law_fallback_used=manual_to_law_fallback_used,
        law_intent=bool(intent.get("should_attempt")),
    )

    # Structured evidence pack (Part D). Reuses the already-fetched law_context
    # (NO second external call) and the computed quality so the pack's source
    # confidence agrees with the response metadata. Never raises; secret-free.
    try:
        law_evidence_pack = build_law_evidence_pack(
            prompt,
            visa_code=visa_code_detected,
            task_type=task_type_detected,
            lang=req.lang or "",
            manual_evidence={"direct": [*grounding_sources, *structured_sources], "related": []},
            manual_present=(grounding is not None),
            structured_present=bool(structured_block),
            procedure_variant_present=bool(procedure_variant_block),
            law_context=law_context,
            quality=quality,
            # Use the effective mode so an enabled-without-credential deploy does
            # not surface "source unavailable" chips / downgrade the source panel.
            config=dataclasses.replace(grounding_cfg, mode=effective_mode),
        )
    except Exception:  # pragma: no cover - the pack must never break /api/ask
        law_evidence_pack = None

    if law_evidence_pack and law_evidence_pack.get("citation_verification"):
        citation_verification = law_evidence_pack.get("citation_verification")

    citation_status = str((citation_verification or {}).get("status") or "")
    citation_specific = bool((citation_verification or {}).get("citation_specific"))
    direct_evidence_count = int((law_evidence_pack or {}).get("direct_evidence_count", 0) or 0)
    related_evidence_count = int((law_evidence_pack or {}).get("related_evidence_count", 0) or 0)
    missing_direct_authority = bool(
        (law_evidence_pack or {}).get("missing_direct_authority", direct_evidence_count == 0)
    )
    law_lookup_failed = law_grounding_status_detail in {
        "law_grounding_attempted_no_results",
        "law_grounding_attempted_failed",
        "law_grounding_source_linked_unverified",
    }
    quality = enforce_source_confidence_invariants(
        quality,
        prompt=prompt,
        visa_code=visa_code_detected,
        task_type=task_type_detected,
        direct_evidence_count=direct_evidence_count,
        related_evidence_count=related_evidence_count,
        missing_direct_authority=missing_direct_authority,
        law_lookup_failed=law_lookup_failed,
        citation_specific=citation_specific,
        citation_verification_status=citation_status,
        structured_procedure_mismatch=structured_procedure_mismatch,
    )
    if law_evidence_pack is not None:
        law_evidence_pack["answer_quality_mode"] = quality["answer_quality_mode"]
        law_evidence_pack["source_confidence_level"] = quality["source_confidence_level"]
        law_evidence_pack["requires_official_confirmation"] = quality["requires_official_confirmation"]
        law_evidence_pack["official_confirmation_questions"] = quality["official_confirmation_questions"]
        law_evidence_pack["source_confidence_invariant_reasons"] = quality.get(
            "source_confidence_invariant_reasons", []
        )
        if isinstance(law_evidence_pack.get("legal_analysis"), dict):
            law_evidence_pack["legal_analysis"]["confidence"] = quality["source_confidence_level"]

    # Resolve answer depth before supplementary case retrieval.  Fast remains
    # genuinely fast for short, low-risk questions, but source-heavy,
    # permission/deadline-sensitive, high-risk, or multi-factor questions are
    # promoted to Basic.  The *effective* tier also controls the evidence
    # budget, so an escalated question gets the same case-law depth as Basic.
    answer_mode_route = resolve_question_answer_mode(
        req.answer_mode,
        question=prompt,
        legal_issue_types=(law_evidence_pack or {}).get("legal_issue_types") or [],
        risk_level=risk_level_detected or "",
    )
    answer_mode_requested = answer_mode_route["requested_mode"]
    _model_plan_mode = answer_mode_requested if answer_mode_requested == "pro" else answer_mode_route["effective_mode"]
    answer_mode_plan = resolve_answer_mode_models(_model_plan_mode)
    answer_mode_used = answer_mode_plan["mode"]

    # Supplementary case-law / administrative-decision evidence (판례 / 재결례).
    # Gated and relevance-filtered; never breaks the request (see helper).
    legal_evidence_meta = _maybe_retrieve_legal_evidence(
        prompt,
        answer_mode=answer_mode_used,
        effective_mode=effective_mode,
        grounding_cfg=grounding_cfg,
        law_intent=bool(intent.get("should_attempt")),
        law_evidence_pack=law_evidence_pack,
    )

    # Shared, non-secret grounding/law metadata reused across prompt and response paths.
    source_panel_meta = _derive_source_panel_metadata(
        law_evidence_pack=law_evidence_pack,
        citation_verification=citation_verification,
        law_grounding_used=law_grounding_used,
        law_grounding_attempted=law_grounding_attempted,
        law_grounding_status=law_grounding_status,
        law_grounding_warnings=law_grounding_warnings,
        manual_grounding_status=manual_grounding_status,
    )

    # Evidence-backed answer-shape contract (Part A). Picks ONE issue-type
    # contract (registration / activity-scope / workplace-change / status-change
    # / documents / study / work-restriction) and the required answer slots. The
    # same object feeds the prompt directive, the post-answer quality gate, and
    # the deterministic synthesis repair so all three agree on what a good answer
    # for this issue must contain.
    answer_shape_contract = build_answer_shape_contract(
        legal_issue_types=(law_evidence_pack or {}).get("legal_issue_types") or [],
        immigration_facts=(law_evidence_pack or {}).get("immigration_facts") or {},
        answer_certainty_level=source_panel_meta.get("answer_certainty_level", ""),
        question_type=quality.get("question_type", ""),
    )

    # Answer-prompt integration (Part E): inject ONE compact, normalized
    # evidence summary (never a raw API dump) plus the backend-prepared legal
    # analysis object. The model may explain this object; it must not invent it.
    if law_evidence_pack and (
        law_evidence_pack.get("law_sources") or law_evidence_pack.get("law_api_attempted") or law_evidence_pack.get("legal_analysis")
    ):
        legal_analysis = law_evidence_pack.get("legal_analysis") or {}
        confirmation_lines = "\n".join(
            f"  - {q}" for q in (legal_analysis.get("official_confirmation_questions") or [])[:8]
        )
        final_prompt += (
            "\n\n[Law/manual evidence pack — normalized context only]\n"
            "- This is supplemental legal CONTEXT, not a required-document checklist.\n"
            "- Manual / HiKorea / competent-office sources control documents, fees,"
            " deadlines, and operational procedures.\n"
            "- Do not invent article numbers, deadlines, fees, or documents.\n"
            + law_evidence_pack.get("evidence_summary", "")
        )
        if law_evidence_pack.get("grounding_context_prompt"):
            final_prompt += (
                "\n\n[Generalized official-source grounding context]\n"
                + law_evidence_pack.get("grounding_context_prompt", "")
            )
        if legal_analysis:
            final_prompt += (
                "\n\n[Backend-prepared legal_analysis — explain this; do not invent it]\n"
                f"analysis_mode: {legal_analysis.get('analysis_mode')}\n"
                f"risk_posture: {legal_analysis.get('risk_posture')}\n"
                f"confidence: {legal_analysis.get('confidence')}\n"
                f"practical_posture: {legal_analysis.get('practical_posture')}\n"
                f"main_issue: {legal_analysis.get('main_issue')}\n"
                f"legal_issue_types: {legal_analysis.get('legal_issue_types')}\n"
                f"immigration_facts: {json.dumps(legal_analysis.get('immigration_facts') or {}, ensure_ascii=False)}\n"
                f"answer_template: {legal_analysis.get('answer_template')}\n"
                f"authority_summary: {legal_analysis.get('authority_summary')}\n"
                f"missing_direct_authority: {legal_analysis.get('missing_direct_authority')}\n"
                f"source_panel_state: {source_panel_meta.get('source_panel_state')}\n"
                f"direct_evidence_count: {(law_evidence_pack or {}).get('direct_evidence_count', 0)}\n"
                f"related_evidence_count: {(law_evidence_pack or {}).get('related_evidence_count', 0)}\n"
                f"law_lookup_error_type: {source_panel_meta.get('law_lookup_error_type')}\n"
                f"citation_verification_status: {source_panel_meta.get('citation_verification_status')}\n"
                f"manual_grounding_status: {manual_grounding_status}\n"
                f"answer_certainty_level: {source_panel_meta.get('answer_certainty_level')}\n"
                "Confidence gate: if answer_certainty_level is not direct, missing_direct_authority is true, direct_evidence_count is 0, or law_lookup_error_type indicates a lookup issue, avoid final conclusion verbs. Do not say 신고 의무는 없습니다, 반드시 신고해야 합니다, 허용됩니다, 가능합니다, or that previous-status duties automatically continue/expire unless direct authority supports it. When previous/current/target statuses are present, analyze current status first, treat previous status as related/comparative unless a direct source says otherwise, and identify decisive facts such as approval conditions, activity form, employer/client, industry, hours, compensation, timing, and jurisdiction.\n"
                "Required framing: use the issue-based template; practical legal posture first; identify current status/activity/issue; explain backend legal_analysis; source basis later; concrete official-confirmation questions fourth; no final administrative determination.\n"
                "Official-confirmation questions:\n" + confirmation_lines
            )

    # Supplementary case-law / adjudication evidence: the safe directive + the
    # preferred chunks for the top cases. Manuals/statutes stay primary; this is
    # context only and is governed by the case-law safety directive.
    if legal_evidence_meta.get("legal_evidence_prompt"):
        final_prompt += "\n\n" + legal_evidence_meta["legal_evidence_prompt"]

    if answer_mode_route.get("auto_escalated"):
        final_prompt += (
            "\n\n[Answer-depth routing]\n"
            "- The user selected Fast, but this question was automatically promoted to Basic because it "
            "requires a more careful multi-factor or source-grounded answer.\n"
            "- Prefer correctness, issue separation, and explicit evidence limits over brevity."
        )

    final_prompt += "\n\n" + build_answer_directives(quality, lang=req.lang)

    # Legal-citation safety directive. For ANY law-intent question, forbid the
    # model from inventing statute/article numbers from memory; when real-time
    # law grounding is not verified, require it to say the specific citation could
    # not be verified. This is the primary defense on the streamed path (where the
    # post-hoc text guard below cannot run).
    if intent.get("should_attempt"):
        final_prompt += "\n\n" + build_citation_safety_directive(
            status_detail=law_grounding_status_detail, lang=req.lang
        )

    # Steer the live model toward the issue-type answer-shape contract so the
    # post-answer quality gate has to repair fewer answers. This is guidance
    # only; it never invents facts and never changes provider/model selection.
    if answer_shape_contract.get("required_slots"):
        final_prompt += (
            "\n\n[Answer shape contract — required content for this issue type]\n"
            f"- Issue-type contract: {answer_shape_contract['contract_key']}.\n"
            "- Make sure the answer actually contains, in natural prose (not as"
            " labels): " + ", ".join(answer_shape_contract["required_slots"]).replace("_", " ") + ".\n"
            "- Lead with the direct practical answer; put any source-limitation"
            " note AFTER the practical analysis, not as the first line; do not say"
            " the answer is not based on the manual when structured legal analysis"
            " context is provided; do not introduce study/course wording unless the"
            " issue is genuinely about study."
        )

    # Trust & Safety "warn" steer: the request touched a sensitive enforcement
    # theme but explicitly asked for the lawful route. Keep the answer strictly
    # within lawful options and never provide evasion/concealment techniques.
    if safety_decision.action == safety_guardrails.ACTION_WARN:
        final_prompt += (
            "\n\n[Trust & Safety directive]\n"
            "- Answer ONLY with lawful, above-board options (correct visa/status,"
            " official procedures, authorized-work rules).\n"
            "- Do NOT provide any method to avoid inspections/enforcement, work"
            " without authorization, or conceal status.\n"
            "- If the lawful answer is 'this is not permitted', say so plainly and"
            " point to official channels (1345 / HiKorea / competent immigration office)."
        )

    llm = _resolve_llm_config()

    # Public detected-status display preserves an explicit sub-code the user typed
    # (e.g. G-1-5) even though sub-code DOCUMENT ROUTING stays payload-only. The
    # parent code (G-1) remains available internally for family-level lookup; only
    # the public chip / answer metadata gets the exact sub-code so it is not
    # collapsed to the parent.
    _detected_facts = (law_evidence_pack or {}).get("immigration_facts") or {}
    _exact_sub = _detected_facts.get("current_sub_status")
    _exact_current = _detected_facts.get("current_status")
    public_visa_code_detected = visa_code_detected
    public_visa_sub_code_detected = visa_sub_code_detected
    if _exact_sub and not public_visa_sub_code_detected:
        public_visa_code_detected = (
            _detected_facts.get("current_parent_status")
            or public_visa_code_detected
            or _exact_sub.rsplit("-", 1)[0]
        )
        public_visa_sub_code_detected = _exact_sub
    elif _exact_current and not public_visa_code_detected:
        public_visa_code_detected = _detected_facts.get("current_parent_status") or _exact_current

    # User-visible "실시간 법령 확인" payload. When verified, surface the concrete
    # law source(s) actually returned (title, law name, article, retrieval time,
    # primary/background role); otherwise carry the standard not-verified notice
    # the UI shows verbatim. Secret-free (URLs are already sanitized upstream).
    _law_sources_for_display = (law_evidence_pack or {}).get("law_sources", []) or []
    law_grounding_user_notice = (
        "" if law_grounding_verified else build_unverified_citation_notice(req.lang)
    )
    law_grounding_display: Dict[str, Any] = {
        "verified": law_grounding_verified,
        "status_detail": law_grounding_status_detail,
        "retrieval_timestamp": law_grounding_retrieval_timestamp,
        # Real-time law is supplementary unless no manual grounding exists.
        "evidence_role": (
            ("primary" if manual_grounding_status != "present" else "background")
            if law_grounding_verified else ""
        ),
        "sources": [],
        "notice": law_grounding_user_notice,
    }
    if law_grounding_verified:
        for _src in _law_sources_for_display[:3]:
            if not isinstance(_src, dict):
                continue
            law_grounding_display["sources"].append({
                "source_title": _src.get("title") or _src.get("law_name") or "",
                "law_name": _src.get("law_name") or "",
                "article": _src.get("article") or "",
                "source_url": _src.get("source_url") or "",
                "relevance": _src.get("relevance") or "background",
            })

    base_meta: Dict[str, Any] = dict(
        grounding_used=bool(grounding),
        grounding_sources=grounding_sources,
        procedure_variant_context_used=bool(procedure_variant_block),
        procedure_variant_context_sources=procedure_variant_context_sources,
        visa_code_detected=public_visa_code_detected,
        visa_sub_code_detected=public_visa_sub_code_detected,
        task_type_detected=task_type_detected,
        risk_level_detected=risk_level_detected,
        law_grounding_used=law_grounding_used,
        law_grounding_attempted=law_grounding_attempted,
        law_grounding_status=law_grounding_status,
        law_grounding_status_detail=law_grounding_status_detail,
        law_grounding_verified=law_grounding_verified,
        law_grounding_retrieval_timestamp=law_grounding_retrieval_timestamp,
        law_grounding_user_notice=law_grounding_user_notice,
        law_grounding_display=law_grounding_display,
        law_grounding_intent_reasons=law_grounding_intent_reasons,
        law_search_query=law_search_query,
        law_search_queries=law_search_queries,
        law_grounding_warnings=law_grounding_warnings,
        citation_verification=citation_verification,
        manual_grounding_status=manual_grounding_status,
        manual_to_law_fallback_used=manual_to_law_fallback_used,
        manual_to_law_fallback_reason=manual_to_law_fallback_reason,
        answer_quality_mode=quality["answer_quality_mode"],
        source_confidence_level=quality["source_confidence_level"],
        requires_official_confirmation=quality["requires_official_confirmation"],
        official_confirmation_questions=quality["official_confirmation_questions"],
        related_statuses_not_sources=quality["related_statuses_not_sources"],
        grounded_answer_limited=quality["grounded_answer_limited"],
        source_confidence_invariant_reasons=quality.get("source_confidence_invariant_reasons", []),
        answer_style_version=quality["answer_style_version"],
        question_type_detected=quality["question_type"],
        # Answer-shape contract (Part A). Gate pass/warnings are filled on the
        # live-answer path below; defaults (passed, empty warnings) hold for the
        # deterministic-synthesis / provider-family fallback paths whose answers
        # are gate-safe by construction.
        answer_shape_contract=answer_shape_contract["contract_key"],
        answer_shape_version=answer_shape_contract["answer_shape_version"],
        # Structured law/manual evidence pack (Part D) + convenience fields.
        # Secret-free: source URLs are sanitized and OC/keys never appear.
        law_evidence_pack=law_evidence_pack,
        planned_law_queries=(law_evidence_pack or {}).get("planned_law_queries", []),
        law_sources=(law_evidence_pack or {}).get("law_sources", []),
        precedent_evidence_items=(law_evidence_pack or {}).get("precedent_evidence_items", []),
        law_evidence_count=(law_evidence_pack or {}).get("law_evidence_count", 0),
        legal_analysis=(law_evidence_pack or {}).get("legal_analysis"),
        immigration_facts=(law_evidence_pack or {}).get("immigration_facts", {}),
        legal_issue_types=(law_evidence_pack or {}).get("legal_issue_types", []),
        proposed_activity_type=(law_evidence_pack or {}).get("proposed_activity_type", []),
        source_plan=(law_evidence_pack or {}).get("source_plan", {}),
        query_classification=(law_evidence_pack or {}).get("query_classification", {}),
        official_grounding_context=(law_evidence_pack or {}).get("official_grounding_context", {}),
        public_source_status=(law_evidence_pack or {}).get("public_source_status", {}),
        public_official_sources=(law_evidence_pack or {}).get("public_official_sources", []),
        analysis_mode=(law_evidence_pack or {}).get("analysis_mode", ""),
        main_issue=(law_evidence_pack or {}).get("main_issue", ""),
        source_types_attempted=(law_evidence_pack or {}).get("source_types_attempted", []),
        source_types_returned=(law_evidence_pack or {}).get("source_types_returned", []),
        source_type_statuses=(law_evidence_pack or {}).get("source_type_statuses", {}),
        source_family_statuses=(law_evidence_pack or {}).get("source_family_statuses", {}),
        parser_status_by_family=(law_evidence_pack or {}).get("parser_status_by_family", {}),
        evidence_ontology=(law_evidence_pack or {}).get("evidence_ontology", {}),
        evidence_query_plan=(law_evidence_pack or {}).get("evidence_query_plan", []),
        evidence_goal_by_query=(law_evidence_pack or {}).get("evidence_goal_by_query", []),
        source_family_support=(law_evidence_pack or {}).get("source_family_support", {}),
        direct_evidence_count=(law_evidence_pack or {}).get("direct_evidence_count", 0),
        related_evidence_count=(law_evidence_pack or {}).get("related_evidence_count", 0),
        analogical_evidence_count=(law_evidence_pack or {}).get("analogical_evidence_count", 0),
        background_evidence_count=(law_evidence_pack or {}).get("background_evidence_count", 0),
        missing_direct_authority=(law_evidence_pack or {}).get("missing_direct_authority", True),
        authority_summary=(law_evidence_pack or {}).get("authority_summary", ""),
        source_state=(law_evidence_pack or {}).get("analysis_mode", "") or law_grounding_status,
        direct_manual_sources=(law_evidence_pack or {}).get("direct_manual_sources", []),
        related_manual_sources=(law_evidence_pack or {}).get("related_manual_sources", []),
        # Supplementary case-law / adjudication evidence (판례 / 재결례), kept as a
        # SEPARATE response field from manual/statute evidence so the UI can
        # distinguish them. Secret-free; OC/full bodies never appear.
        legal_evidence=legal_evidence_meta["legal_evidence"],
        legal_evidence_status=legal_evidence_meta["legal_evidence_status"],
        legal_evidence_used=legal_evidence_meta["legal_evidence_used"],
        legal_evidence_cases=legal_evidence_meta["legal_evidence_cases"],
        legal_evidence_source_types=legal_evidence_meta["legal_evidence_source_types"],
        law_grounding_error=(law_evidence_pack or {}).get("law_grounding_error", ""),
        parser_status=(law_evidence_pack or {}).get("parser_status", ""),
        response_shape_hint=(law_evidence_pack or {}).get("response_shape_hint", ""),
        source_panel_status=((law_evidence_pack or {}).get("citation_verification") or {}).get("status", ""),
        **source_panel_meta,
        # Coarse, non-secret Trust & Safety signals ("allow"/"warn" here; blocked
        # requests returned earlier and never reach this path).
        **safety_meta,
    )

    # Apply the already-resolved question-aware tier.  This is deliberately
    # computed before case-law retrieval above so evidence depth and model depth
    # cannot disagree.
    answer_mode_max_tokens = (
        OPENROUTER_FAST_MAX_TOKENS if answer_mode_used == "fast" else OPENROUTER_MAX_TOKENS
    )
    base_meta.update(
        answer_mode=answer_mode_used,
        answer_mode_requested=answer_mode_requested,
        answer_mode_available=bool(answer_mode_route.get("available", True))
        and bool(answer_mode_plan.get("available", True)),
        answer_mode_auto_escalated=bool(answer_mode_route.get("auto_escalated")),
        answer_mode_escalation_reasons=list(answer_mode_route.get("escalation_reasons") or []),
        answer_mode_route_version=str(answer_mode_route.get("version") or MODEL_POLICY_VERSION),
    )

    # Streaming path (SSE): snappier perceived response. Only OpenRouter supports
    # it here; other providers fall through to the normal buffered path. The
    # in-prompt safety/confidence directives still apply, and the post-generation
    # safety review runs on the accumulated text after the final token (H-7,
    # see _post_stream_safety_review_frames). Only the post-hoc answer-shape
    # repair gate stays buffered-only (its repair rewrites the complete answer).
    if req.stream and llm["provider"] == "openrouter":
        stream_meta = dict(base_meta)
        stream_meta["streamed"] = True
        return StreamingResponse(
            _sse_answer_stream(
                final_prompt,
                answer_mode_plan["candidates"],
                answer_mode_max_tokens,
                stream_meta,
                prompt=prompt,
                lang=req.lang,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if llm["provider"] == "openrouter":
        # H-1b: honor req.model ONLY when it is an allowlisted, already-
        # configured model id; anything else silently uses the default chain.
        result = await _openrouter_complete_with_candidates(
            final_prompt,
            requested_model=_sanitize_requested_model(req.model, "openrouter"),
            candidate_models=answer_mode_plan["candidates"],
            max_tokens=answer_mode_max_tokens,
        )
        # Fast-tier transparency: did Fast actually answer on the fast primary, or
        # fall back to a non-fast model in its chain?
        _fast_primary = (answer_mode_plan.get("candidates") or [None])[0]
        fast_mode_fell_back = bool(
            answer_mode_used == "fast"
            and result["final_model"]
            and result["final_model"] != _fast_primary
        )
        # Non-secret attempt metadata (model ids + classified error only).
        attempt_meta: Dict[str, Any] = dict(
            llm_provider="openrouter",
            requested_model=result["requested_model"],
            primary_model=result["primary_model"],
            model_candidates=result["model_candidates"],
            attempted_models=result["attempted_models"],
            final_model=result["final_model"],
            selected_model=result["final_model"],
            fast_mode_fell_back=fast_mode_fell_back,
            model_fallback_used=result["model_fallback_used"],
            provider_error_type=result["provider_error_type"],
            upstream_statuses=result["upstream_statuses"],
            retryable_provider_error=result["retryable_provider_error"],
            all_candidates_failed=result["all_candidates_failed"],
            skipped_models_due_to_cooldown=result.get("skipped_models_due_to_cooldown", []),
            cooling_down_models=result.get("cooling_down_models", []),
            model_cooldown_seconds=result.get("model_cooldown_seconds", OPENROUTER_MODEL_COOLDOWN_SECONDS),
            cooldown_enabled=result.get("cooldown_enabled", _cooldown_enabled()),
        )
        if result["ok"]:
            response_meta = dict(base_meta)
            answer_text = _confidence_gate_answer_text(result["answer"], response_meta)
            # Evidence-backed answer-shape quality gate (Part B/C/F). If the live
            # model answer fails the issue-type contract structurally, repair it
            # with deterministic synthesis instead of showing the weak answer.
            answer_text, gate_meta = _apply_answer_shape_gate(
                answer_text,
                response_meta,
                answer_shape_contract,
                prompt=prompt,
                lang=req.lang,
                final_model=result.get("final_model"),
                primary_model=result.get("primary_model"),
            )
            response_meta.update(gate_meta)
            # Unverified-citation guardrail. If the answer cites specific statutes/
            # articles, real-time law grounding is NOT verified, and those citations
            # are not backed by the manual/law evidence we actually retrieved, prepend
            # an honest notice instead of silently presenting hallucinated law.
            answer_text, citation_guard_meta = _apply_law_citation_guard(
                answer_text,
                law_grounding_verified=law_grounding_verified,
                law_evidence_pack=law_evidence_pack,
                grounding_sources=grounding_sources,
                structured_block=structured_block,
                lang=req.lang,
            )
            response_meta.update(citation_guard_meta)
            # Post-generation safety sanity check (defense-in-depth). Conservative
            # and low-latency: only the most acute facilitation categories trip,
            # which a compliant answer never matches. If it trips, withhold the
            # model text and return the neutral refusal instead.
            postgen = safety_guardrails.post_generation_review(answer_text)
            if postgen is not None:
                postgen.language = safety_guardrails.detect_language(prompt, req.lang)
                postgen_event_id = safety_events.log_safety_event(
                    action=safety_guardrails.ACTION_ESCALATE,
                    category=postgen.category,
                    severity=postgen.severity,
                    reason=postgen.reason,
                    matched_signals=postgen.matched_signals,
                    input_text=prompt,
                    language=postgen.language,
                    route="/api/ask:post_generation",
                    request_id=req.selected_procedure_variant_id or None,
                )
                return _build_safety_refusal_response(
                    postgen, lang=req.lang, event_id=postgen_event_id
                )
            response_meta["answer_first_sentence"] = (answer_text or "").strip().split(".", 1)[0].strip()
            response_meta["first_sentence_quality_warning"] = first_sentence_quality_warning(answer_text)
            return AskResponse(
                answer=answer_text,
                provider="openrouter",
                model=result["final_model"] or OPENROUTER_MODEL,
                provider_family_fallback_used=False,
                **attempt_meta,
                **response_meta,
            )
        if not result.get("retryable_provider_error"):
            # Non-retryable provider failures (bad credentials, malformed
            # requests, unavailable model ids, or safety/policy rejections) are
            # not normal model-capacity outages. Do not convert them into a
            # deterministic answer or fall through to another provider: surface a
            # safe 503 with non-secret diagnostics so operators can repair the
            # configuration/request while users do not see raw provider JSON.
            raise HTTPException(
                status_code=503,
                detail={
                    **attempt_meta,
                    **base_meta,
                    "error": "openrouter_provider_error",
                    "message": "AI provider configuration or request error. Please retry after the service configuration is checked.",
                    "llm_unavailable": True,
                    "provider_unavailable": False,
                    "deterministic_fallback_answer_used": False,
                    "provider_family_fallback_used": False,
                },
            )
        # All retryable OpenRouter candidates failed.
        # Provider-family fallback to Groq ONLY if explicitly enabled + configured
        # (strict OpenRouter-first is the default — no silent provider switch).
        if ALLOW_GROQ_FALLBACK and GROQ_API_KEY:
            try:
                groq_answer = await _call_groq(final_prompt, model=None)
            except HTTPException:
                groq_answer = None
            if groq_answer is not None:
                fam = dict(attempt_meta)
                fam["llm_provider"] = "groq"
                return AskResponse(
                    answer=groq_answer,
                    provider="groq",
                    model=GROQ_MODEL,
                    provider_family_fallback_used=True,
                    **fam,
                    **base_meta,
                )
        # Optional private Ollama fallback scaffold. Disabled by default; never
        # reached unless the operator explicitly enables it and OpenRouter failed.
        ollama_error_type = "ollama_disabled"
        if ENABLE_OLLAMA_FALLBACK:
            try:
                ollama_answer = await _call_ollama(final_prompt, model=OLLAMA_MODEL)
            except HTTPException as exc:
                ollama_error_type = _classify_ollama_error(exc)
            else:
                ollama_answer = _confidence_gate_answer_text(ollama_answer, base_meta)
                ollama_meta = dict(attempt_meta)
                ollama_meta.update({
                    "llm_provider": "ollama",
                    "final_model": OLLAMA_MODEL,
                    "ollama_fallback_enabled": True,
                    "ollama_fallback_used": True,
                    "ollama_model": OLLAMA_MODEL,
                    "ollama_error_type": None,
                    "deterministic_fallback_answer_used": False,
                    "copy_safe_answer": ollama_answer,
                })
                return AskResponse(
                    answer=ollama_answer,
                    provider="ollama",
                    model=OLLAMA_MODEL,
                    provider_family_fallback_used=False,
                    **ollama_meta,
                    **base_meta,
                )

        fallback_payload = _build_deterministic_fallback_payload(
            prompt, req.lang, base_meta, attempt_meta,
            reason="openrouter_all_candidates_failed",
        )
        fallback_payload["ollama_error_type"] = ollama_error_type
        fallback_payload["answer_first_sentence"] = (fallback_payload.get("answer") or "").strip().split(".", 1)[0].strip()
        fallback_payload["first_sentence_quality_warning"] = first_sentence_quality_warning(fallback_payload.get("answer") or "")
        return AskResponse(**fallback_payload)

    if llm["provider"] == "groq":
        # H-1b: same allowlist rule as OpenRouter — an unlisted client model id
        # silently falls back to the configured GROQ_MODEL.
        groq_requested_model = _sanitize_requested_model(req.model, "groq")
        answer = await _call_groq(final_prompt, model=groq_requested_model)
        groq_model = groq_requested_model or GROQ_MODEL
        response_meta = dict(base_meta)
        answer = _confidence_gate_answer_text(answer, response_meta)
        response_meta["answer_first_sentence"] = (answer or "").strip().split(".", 1)[0].strip()
        response_meta["first_sentence_quality_warning"] = first_sentence_quality_warning(answer)
        return AskResponse(
            answer=answer,
            provider="groq",
            model=groq_model,
            llm_provider="groq",
            requested_model=groq_requested_model,
            primary_model=GROQ_MODEL,
            model_candidates=[groq_model],
            attempted_models=[groq_model],
            final_model=groq_model,
            model_fallback_used=False,
            provider_family_fallback_used=False,
            **response_meta,
        )

    raise HTTPException(
        status_code=503,
        detail={
            "error": "no_llm_provider_configured",
            "message": (
                "No LLM provider is configured. Set OPENROUTER_API_KEY or "
                "GROQ_API_KEY in the backend environment."
            ),
            "llm_provider": "none",
            **base_meta,
        },
    )


@app.post("/api/jobcodekeywords", response_model=JobCodeKeywordsResponse)
async def job_code_keywords(req: JobCodeKeywordsRequest) -> JobCodeKeywordsResponse:
    keywords = _extract_keywords(req.query)
    return JobCodeKeywordsResponse(query=req.query, keywords=keywords)


# ---------------------------------------------------------------------------
# Public legal source search — Waymaker "법령·판례 근거 검색" / "Legal source search"
# ---------------------------------------------------------------------------
# Thin, read-only proxy over the Open Law API (law.go.kr), reusing the TESTED
# adapters law_tools.search_laws / precedent_sources.search_precedents. Design:
#   * The OC credential (LAW_API_OC, or legacy LAW_API_KEY fallback) is read
#     server-side via load_grounding_config() and NEVER returned to the client;
#     the adapters already OC-redact every upstream URL (_sanitize_url).
#   * This is a source-CHECKING layer: it returns pointers to official text and
#     short snippets, never a legal conclusion or eligibility judgement.
#   * Detail/body lookup is intentionally deferred to the official source link
#     (no raw upstream HTML is fetched or rendered) — see PR notes.
#   * Both endpoints never raise to the client: upstream/timeout failures and a
#     missing credential degrade to a safe JSON envelope.
_LEGAL_SEARCH_MAX_QUERY = 150
_LEGAL_SEARCH_MAX_RESULTS = 10
_LAW_API_NOT_CONFIGURED_MESSAGE = "LAW_API_OC is not configured"


def _legal_search_clean_query(raw: Optional[str]) -> str:
    """Trim and length-cap a user query (defensive; adapters also guard)."""
    return (raw or "").strip()[:_LEGAL_SEARCH_MAX_QUERY]


def _public_law_url(law_name: str) -> str:
    """Build a clean, secret-free public law.go.kr link for a statute name."""
    name = (law_name or "").strip()
    if not name or name.startswith("("):
        return "https://www.law.go.kr/LSW/lsAstSc.do?menuId=1"
    return "https://www.law.go.kr/법령/" + quote(name, safe="")


def _public_precedent_url(item: Dict[str, Any], query: str) -> str:
    """Prefer the API-provided (already OC-redacted) detail link; else a search link."""
    url = precedent_sources.normalize_law_go_kr_url(item.get("url") or "")
    if url:
        return url
    return "https://www.law.go.kr/LSW/precSc.do?menuId=7&query=" + quote((query or "").strip(), safe="")


def _map_law_result(r: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one law_tools candidate into the frontend LegalLawResult shape."""
    title = r.get("title") or r.get("law_name") or ""
    return {
        "id": str(r.get("law_serial_no") or r.get("law_id") or r.get("reference") or ""),
        "title": title,
        "type": r.get("law_division") or r.get("source_type") or "",
        "articleNo": r.get("article") or "",
        "articleTitle": "",
        "snippet": (r.get("summary") or "")[:300],
        "promulgationDate": r.get("promulgation_date") or "",
        "effectiveDate": r.get("enforcement_date") or "",
        "sourceUrl": _public_law_url(title),
        "rawSource": "law.go.kr",
        # Lifecycle + hierarchy annotations from the ranked search. A repealed or
        # not-yet-in-force statute must be visibly labelled, and 법률 / 시행령 /
        # 시행규칙 is a display layer, never a filter.
        "lifecycleStatus": r.get("lifecycle_status") or "",
        "hierarchyLevel": r.get("hierarchy_level") or "",
        "nameMatch": bool(r.get("name_match", True)),
    }


def _map_precedent_item(item: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Normalize one precedent_sources item into the frontend LegalPrecedentResult shape."""
    source_id = str(item.get("serialNumber") or "")
    display_id = source_id or str(item.get("caseNumber") or item.get("decisionNumber") or "")
    body_available = item.get("resultKind") == "body_result"
    return {
        "id": display_id,
        "title": item.get("title") or "",
        "court": item.get("courtOrAgency") or item.get("sourceName") or "",
        "decisionDate": item.get("decisionDate") or "",
        "caseNumber": item.get("caseNumber") or "",
        "summary": (
            (item.get("holdingSummary") or item.get("snippet") or "")[:500]
            if body_available else ""
        ),
        "sourceUrl": _public_precedent_url(item, query),
        "detailAvailable": bool(source_id),
        "detailApiPath": "/api/legal/precedents/detail?id=" + quote(source_id, safe="") if source_id else "",
        "rawSource": "law.go.kr",
    }


def _legal_not_configured_response() -> JSONResponse:
    return UTF8JSONResponse(
        content={"ok": False, "error": _LAW_API_NOT_CONFIGURED_MESSAGE,
                 "reason": "not_configured", "results": []},
    )


@app.get("/api/legal/laws/search")
async def legal_laws_search(q: str = "") -> Any:
    """Search immigration-related statutes / decrees / rules on the Open Law API.

    Read-only proxy. Returns ``{ok, kind, query, count, results}`` (results are
    LegalLawResult objects) or a safe ``{ok:false, error}`` envelope. The OC
    credential is never exposed; upstream URLs are OC-redacted by the adapter.
    """
    cfg = load_grounding_config()
    if not cfg.law_api_configured:
        return _legal_not_configured_response()
    query = _legal_search_clean_query(q)
    if not query:
        return UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_query", "results": []})
    outcome = search_laws(query, limit=_LEGAL_SEARCH_MAX_RESULTS, config=cfg)
    if outcome.get("status") != "ok":
        error_type = outcome.get("error_type") or "search_failed"
        if error_type == "law_api_not_configured":
            return _legal_not_configured_response()
        if error_type == "law_api_no_results":
            return {"ok": True, "kind": "laws", "query": query, "count": 0, "results": [], "rawSource": "law.go.kr"}
        return UTF8JSONResponse(
            content={"ok": False, "error": "search_failed", "reason": error_type, "query": query, "results": []},
        )
    results = [_map_law_result(r) for r in (outcome.get("results") or []) if isinstance(r, dict)]
    return {"ok": True, "kind": "laws", "query": query, "count": len(results), "results": results, "rawSource": "law.go.kr"}


@app.get("/api/legal/precedents/search")
async def legal_precedents_search(q: str = "") -> Any:
    """Search court precedent (판례) on the Open Law API (``target=prec``).

    Read-only list search. Returns ``{ok, kind, query, count, results}``
    (LegalPrecedentResult objects) or a safe ``{ok:false, error}`` envelope.
    Body/detail lookup is deferred to the official source link by design.
    """
    cfg = load_grounding_config()
    if not cfg.law_api_configured:
        return _legal_not_configured_response()
    query = _legal_search_clean_query(q)
    if not query:
        return UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_query", "results": []})
    env = precedent_sources.search_precedents(query, limit=_LEGAL_SEARCH_MAX_RESULTS, config=cfg)
    status = env.get("status")
    if status == "not_configured":
        return _legal_not_configured_response()
    if status == "results_found":
        items = precedent_sources.dedupe_precedent_items(env.get("items") or [])
        results = [
            _map_precedent_item(it, query)
            for it in items
            if isinstance(it, dict) and it.get("publicStatus") != "unavailable"
        ]
        return {"ok": True, "kind": "precedents", "query": query, "count": len(results), "results": results, "rawSource": "law.go.kr"}
    if status == "no_results":
        return {"ok": True, "kind": "precedents", "query": query, "count": 0, "results": [], "rawSource": "law.go.kr"}
    # http_error / timeout / bad_response / official_error → graceful, no crash.
    return UTF8JSONResponse(
        content={"ok": False, "error": "search_failed",
                 "reason": env.get("errorType") or status or "unknown", "query": query, "results": []},
    )


@app.get("/api/legal/precedents/detail")
async def legal_precedent_detail(id: str = "") -> Any:
    """Return bounded official precedent body fields for one stable source ID."""
    cfg = load_grounding_config()
    if not cfg.law_api_configured:
        return _legal_not_configured_response()
    source_id = re.sub(r"[^A-Za-z0-9_-]", "", str(id or ""))[:80]
    if not source_id:
        return UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_id", "results": []})
    env = precedent_sources.get_precedent_detail(source_id, config=cfg)
    if env.get("status") == "results_found":
        items = [
            _map_precedent_item(item, source_id)
            for item in (env.get("items") or [])
            if isinstance(item, dict) and item.get("resultKind") == "body_result"
        ]
        if items:
            return {"ok": True, "kind": "precedent_detail", "id": source_id, "count": len(items), "results": items, "rawSource": "law.go.kr"}
    if env.get("status") == "no_results":
        return {"ok": True, "kind": "precedent_detail", "id": source_id, "count": 0, "results": [], "rawSource": "law.go.kr"}
    return UTF8JSONResponse(content={
        "ok": False,
        "error": "detail_failed",
        "reason": env.get("errorType") or env.get("status") or "unknown",
        "id": source_id,
        "results": [],
    })


class LegalResearchRequest(BaseModel):
    question: str = ""
    locale: Optional[str] = "ko"
    # mode controls the task shape; depth controls retrieval + answer depth.
    mode: Optional[str] = None
    depth: Optional[str] = None
    visaStatusHint: Optional[str] = None
    includePrecedents: Optional[bool] = None
    includeManuals: Optional[bool] = None
    # "deterministic" (scaffold only) | "source_grounded_llm" (optional synthesis).
    synthesis: Optional[str] = None


_LEGAL_RESEARCH_MAX_QUESTION = 800


def _aggregate_research_stage_status(statuses: Sequence[str], *, found: int) -> str:
    """Collapse per-query outcomes without turning an outage into no results."""
    if found:
        return "done"
    normalized = [str(status or "").strip().lower() for status in statuses]
    if normalized and all(status in {"not_found", "no_results"} for status in normalized):
        return "no_results"
    return "failed"


def _run_research_law_retrieval(
    plan: Dict[str, Any], cfg
) -> Tuple[List[Dict[str, Any]], str]:
    """Return deduped law cards plus a no-results/failure-aware stage status.

    Uses the ranked search so alias input resolves, substring noise is filtered by
    the name guard, and each card carries its lifecycle state. A ranked outcome
    whose status is a *failure* (timeout / forbidden / parse) contributes nothing
    rather than being read as "this law does not exist".
    """
    laws: List[Dict[str, Any]] = []
    statuses: List[str] = []
    seen = set()
    for term in plan.get("lawTerms", []):
        outcome = search_laws_ranked(term, limit=_LEGAL_SEARCH_MAX_RESULTS, config=cfg)
        statuses.append(str(outcome.get("status") or ""))
        if outcome.get("status") in {"unavailable", "forbidden", "timeout",
                                     "parse_failed", "not_found"}:
            continue
        for r in (outcome.get("results") or []):
            if not isinstance(r, dict):
                continue
            card = _map_law_result(r)
            key = (card.get("id"), card.get("title"))
            if key in seen:
                continue
            seen.add(key)
            laws.append(card)
        if len(laws) >= 12:
            break
    items = laws[:12]
    return items, _aggregate_research_stage_status(statuses, found=len(items))


def _run_research_precedent_retrieval(
    plan: Dict[str, Any], cfg
) -> Tuple[List[Dict[str, Any]], str]:
    """Return deduped precedent cards plus an honest aggregate stage status."""
    out: List[Dict[str, Any]] = []
    statuses: List[str] = []
    seen = set()
    for term in plan.get("precedentTerms", []):
        env = precedent_sources.search_precedents(term, limit=_LEGAL_SEARCH_MAX_RESULTS, config=cfg)
        statuses.append(str(env.get("status") or ""))
        if env.get("status") != "results_found":
            continue
        for it in (env.get("items") or []):
            if not isinstance(it, dict) or it.get("publicStatus") == "unavailable":
                continue
            card = _map_precedent_item(it, term)
            key = (card.get("id"), card.get("title"))
            if key in seen:
                continue
            seen.add(key)
            out.append(card)
        if len(out) >= 8:
            break
    items = out[:8]
    return items, _aggregate_research_stage_status(statuses, found=len(items))


# ---------------------------------------------------------------------------
# Shared research pipeline (UX-07 `Legal / Progress`, node 435:8).
#
# Both /api/legal/research and /api/legal/research/stream drain THIS generator,
# so a streamed run and a buffered run cannot diverge. A second copy would let
# the rules that keep synthesis grounded — the source packet and its validation —
# be updated on one path only.
#
# A step is yielded only AFTER its stage ran, carrying that stage's real count,
# so a progress event can never claim a finding that has not happened yet. That
# is precisely what the frontend could not do before: the buffered endpoint had
# no way to say "the statute search found 3".
# ---------------------------------------------------------------------------
LEGAL_RESEARCH_STEPS = ("issues", "manuals", "laws", "precedents", "citations", "memo")


async def _legal_research_pipeline(req: LegalResearchRequest, question: str):
    _started = time.monotonic()

    def _step(name: str, found: int, status: str = "done") -> Dict[str, Any]:
        return {
            "step": name,
            "index": LEGAL_RESEARCH_STEPS.index(name) + 1,
            "total": len(LEGAL_RESEARCH_STEPS),
            "status": status,
            "foundCount": int(found),
            "elapsedMs": int((time.monotonic() - _started) * 1000),
        }

    plan = legal_research.build_research_plan(
        question,
        depth=req.depth,
        mode=req.mode,
        visa_status_hint=req.visaStatusHint,
        include_precedents=req.includePrecedents,
        include_manuals=req.includeManuals,
        locale=req.locale,
    )
    yield _step("issues", len(
        plan.get("issuesKo" if plan.get("locale") == "ko" else "issuesEn") or []))

    paradiso_sources: List[Dict[str, Any]] = []
    hint = (req.visaStatusHint or "").strip()
    if hint:
        paradiso_sources.append({
            "title": hint, "type": "paradiso",
            "strength": "background",
            "note": "Paradiso 구조화 데이터" if plan.get("locale") == "ko" else "Paradiso structured data",
        })
    yield _step("manuals", len(paradiso_sources))

    cfg = load_grounding_config()
    retrieval_available = bool(cfg.law_api_configured)
    laws: List[Dict[str, Any]] = []
    precs: List[Dict[str, Any]] = []
    retrieval_statuses = {"laws": "unavailable", "precedents": "unavailable"}
    if retrieval_available:
        laws, retrieval_statuses["laws"] = _run_research_law_retrieval(plan, cfg)
        yield _step("laws", len(laws), status=retrieval_statuses["laws"])
        if plan.get("runPrecedents"):
            precs, retrieval_statuses["precedents"] = _run_research_precedent_retrieval(plan, cfg)
            yield _step("precedents", len(precs), status=retrieval_statuses["precedents"])
        else:
            # The caller turned precedents off. "Skipped" and "we looked and
            # found none" are different claims and must not share a status.
            retrieval_statuses["precedents"] = "skipped"
            yield _step("precedents", 0, status="skipped")
    else:
        # No law API configured: neither retrieval stage ran at all, which is
        # again not the same as finding nothing.
        yield _step("laws", 0, status="unavailable")
        yield _step("precedents", 0, status="unavailable")


    result = legal_research.build_research_result(
        plan, law_results=laws, precedent_results=precs,
        paradiso_sources=paradiso_sources, retrieval_available=retrieval_available,
        retrieval_statuses=retrieval_statuses,
    )
    yield _step("citations",
                len(result.get("laws") or []) + len(result.get("precedents") or []))

    # ---- Optional source-grounded LLM synthesis (strictly after retrieval) ----
    # The deterministic result above is always the fallback. Synthesis runs only
    # for basic/pro when a provider is configured AND sources exist; the model
    # may synthesize ONLY from the retrieved-source packet, and the output is
    # validated (no phantom sources, no fabricated statute/case numbers, no
    # final-advice/guarantee/impersonation, no raw HTML) before being shown.
    depth = result.get("depth", "basic")
    locale = plan.get("locale", "ko")
    provider_configured = bool(OPENROUTER_API_KEY)
    res_laws = result.get("laws") or []
    res_precs = result.get("precedents") or []
    has_sources = bool(res_laws or res_precs)
    effective = legal_synthesis.resolve_synthesis_mode(
        req.synthesis, depth, provider_configured=provider_configured, has_sources=has_sources,
    )
    result["providerConfigured"] = provider_configured
    result["synthesis"] = None
    result["synthesisStatus"] = "deterministic"

    if effective == "source_grounded_llm":
        packet, _used = legal_synthesis.build_source_packet(
            question, mode=result.get("mode") or "memo", depth=depth, locale=locale,
            laws=res_laws, precedents=res_precs, paradiso=paradiso_sources,
        )
        prompt = legal_synthesis.build_synthesis_prompt(packet, depth=depth, locale=locale)
        candidates = (resolve_answer_mode_models(depth) or {}).get("candidates")
        max_tok = 1800 if depth == "pro" else 1200
        try:
            llm = await _openrouter_complete_with_candidates(
                prompt, requested_model=None, candidate_models=candidates, max_tokens=max_tok,
            )
        except Exception:  # provider/network failure → silent deterministic fallback
            llm = {"ok": False, "answer": None}

        if llm and llm.get("ok") and llm.get("answer"):
            parsed = legal_synthesis.parse_synthesis_json(llm.get("answer"))
            if parsed is None:
                ok_syn, reason, cleaned = False, "parse_failed", None
            else:
                ok_syn, reason, cleaned = legal_synthesis.validate_synthesis(parsed, packet=packet, locale=locale)
            if ok_syn:
                result["synthesis"] = cleaned
                result["synthesisStatus"] = "llm"
                result["synthesisModel"] = llm.get("final_model")
                result["synthesisSources"] = packet.get("sources")
            else:
                # Unsafe / unparseable synthesis → keep deterministic + warn.
                result["synthesisStatus"] = "validation_failed"
                result["synthesisWarning"] = legal_synthesis.VALIDATION_FAILED_MESSAGE.get(
                    locale, legal_synthesis.VALIDATION_FAILED_MESSAGE["ko"])
                result["synthesisFailureReason"] = reason
        # else: LLM unavailable/failed → leave synthesisStatus = "deterministic".

    yield _step("memo", 1 if result.get("synthesis") else 0,
                status="failed" if result.get("synthesisStatus") == "validation_failed" else "done")
    yield {"__result__": result}


@app.post(
    "/api/legal/research",
    dependencies=[Depends(rate_limit("legal_research", per_minute=4, per_day=60))],
)
async def legal_research_endpoint(req: LegalResearchRequest) -> Any:
    """Deterministic, source-grounded legal research scaffold (no LLM).

    Plans retrieval by research depth (fast / basic / pro), runs the budgeted
    law/precedent searches via the OC-safe adapters, and returns a depth-
    structured result: issues to verify, source-strength-labelled cards (grouped
    by source type in pro), risk flags, missing facts, next checks, limitations,
    and a disclaimer. It never fabricates citations, never states a legal
    conclusion, and never infers facts the user did not provide.
    """
    question = (req.question or "").strip()[:_LEGAL_RESEARCH_MAX_QUESTION]
    if not question:
        return UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_question"})

    result = None
    async for _rec in _legal_research_pipeline(req, question):
        if isinstance(_rec, dict) and "__result__" in _rec:
            result = _rec["__result__"]
    return result


@app.post(
    "/api/legal/research/stream",
    dependencies=[Depends(rate_limit("legal_research", per_minute=4, per_day=60))],
)
async def legal_research_stream_endpoint(req: LegalResearchRequest) -> Any:
    """The same research run as /api/legal/research, reported as it happens.

    Frames: ``start`` -> ``step`` per stage -> ``done`` with the identical
    payload the buffered endpoint returns. Both drain
    `_legal_research_pipeline`, so the two cannot answer the same question
    differently.

    ``status`` separates ``done`` (sources found), ``no_results`` (the search
    ran cleanly), ``failed`` (upstream/parse failure), ``skipped`` (the caller
    turned it off), and ``unavailable`` (the law API is not configured) —
    because "found nothing", "search failed", and "never ran" are different
    claims about our coverage.
    """
    question = (req.question or "").strip()[:_LEGAL_RESEARCH_MAX_QUESTION]
    if not question:
        return UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_question"})

    async def _gen():
        yield _sse("start", {"status": "running", "total": len(LEGAL_RESEARCH_STEPS),
                             "steps": list(LEGAL_RESEARCH_STEPS)})
        result = None
        try:
            async for rec in _legal_research_pipeline(req, question):
                if isinstance(rec, dict) and "__result__" in rec:
                    result = rec["__result__"]
                else:
                    yield _sse("step", rec)
        except Exception:
            # The buffered endpoint stays available, so report the failure
            # rather than leaving the client on a spinner forever.
            yield _sse("done", {"ok": False, "error": "search_failed",
                                "reason": "pipeline_error"})
            return
        yield _sse("done", result if result is not None
                   else {"ok": False, "error": "search_failed", "reason": "no_result"})

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Shared per-client limiter for ALL /api/debug/law-grounding* endpoints (H-1a).
_debug_rate_limit = rate_limit("debug", per_minute=5)


@app.get(
    "/api/debug/law-grounding/preflight",
    dependencies=[Depends(_debug_rate_limit)],
)
async def debug_law_grounding_preflight(question: Optional[str] = None) -> Dict[str, Any]:
    """Operator-safe law-grounding readiness preflight (no external call, no secrets).

    Reports the resolved mode, whether the API key / endpoint are configured
    (booleans only), whether a sample question would trigger grounding, the
    statutory query that would be issued, and explicit warning markers
    (LAW_GROUNDING_DISABLED / LAW_GROUNDING_AUDIT_ONLY / LAW_API_KEY_MISSING /
    LAW_API_ENDPOINT_MISSING). Useful even when external calls are disabled.
    """
    return law_grounding_preflight(question or "")


@app.get(
    "/api/debug/law-grounding/selftest",
    dependencies=[Depends(_debug_rate_limit)],
)
async def debug_law_grounding_selftest(question: Optional[str] = None) -> Dict[str, Any]:
    """Browser-friendly, one-call LIVE check of Open Law API grounding.

    Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404): it can
    trigger a live outbound call and reveals deployment readiness detail that
    anonymous callers have no business probing (M-10).

    Unlike the preflight (which makes NO external call), this performs the same
    mode-gated, secret-free law.go.kr search the answer path uses — against a
    default statute query — and returns a plain-language verdict. An operator
    can open this single URL on the deployed host (e.g. Railway) to confirm
    whether law grounding actually works, distinguishing the common failure
    modes: grounding disabled, no credential, HTTP 403 (OC valid but the
    calling IP is not allow-listed on open.law.go.kr), unreachable host
    (outbound/egress blocked), timeout, or reachable-but-no-results.

    The OC value is NEVER returned; the source URL is sanitized at the tool
    boundary. Read-only; never raises (beyond the availability gate above).
    """
    _require_debug_endpoints_enabled()
    sample = (question or "").strip() or "출입국관리법"
    cfg = load_grounding_config()
    result: Dict[str, Any] = {}

    if cfg.mode == "disabled":
        verdict = "DISABLED"
        message = ("법령 조회가 꺼져 있습니다. 환경변수 LAW_GROUNDING_MODE=audit "
                   "(또는 enabled)로 설정하세요.")
    elif not cfg.law_api_configured:
        verdict = "NO_CREDENTIAL"
        message = ("법령 API 인증값이 없습니다. open.law.go.kr에서 발급받은 OC를 "
                   "환경변수 LAW_API_OC에 설정하세요.")
    else:
        try:
            result = search_laws(sample, config=cfg)
        except Exception:  # pragma: no cover - selftest must never crash
            result = {"status": "error", "error_type": "selftest_exception",
                      "raw_status": 0, "result_count": 0, "source_url": ""}
        status = result.get("status")
        error_type = result.get("error_type", "")
        raw_status = int(result.get("raw_status", 0) or 0)
        count = int(result.get("result_count", 0) or 0)
        if status == "ok" and count > 0:
            verdict = "WORKING"
            message = (f"✅ 정상 작동 — law.go.kr 응답 OK, 결과 {count}건. "
                       "실시간 법령 조회와 인용 검증이 켜졌습니다.")
        elif status == "ok":
            verdict = "REACHABLE_NO_RESULTS"
            message = ("⚠️ law.go.kr 연결은 되지만 이 질의에 결과가 없습니다. "
                       "다른 질의로 재시도하세요(예: ?question=출입국관리법).")
        elif error_type == "law_api_http_error" and raw_status == 403:
            verdict = "FORBIDDEN_403"
            message = ("❌ law.go.kr이 403(접근 거부)을 반환했습니다. OC는 전달됐지만 "
                       "호출 서버 IP가 open.law.go.kr에 허용 등록되지 않았을 가능성이 "
                       "큽니다. open.law.go.kr OPEN API 신청에서 이 서버의 아웃바운드 "
                       "IP를 허용 목록에 등록하세요.")
        elif error_type == "law_api_http_error":
            verdict = f"HTTP_{raw_status or 'ERROR'}"
            message = f"❌ law.go.kr이 HTTP {raw_status or '오류'}를 반환했습니다."
        elif error_type == "law_api_timeout":
            verdict = "TIMEOUT"
            message = "❌ law.go.kr 응답 시간 초과. 잠시 후 다시 시도하세요."
        elif error_type == "law_api_bad_response" and raw_status == 0:
            verdict = "UNREACHABLE"
            message = ("❌ law.go.kr에 네트워크로 연결되지 않습니다(아웃바운드/egress "
                       "차단 또는 DNS 문제). 배포 환경에서 www.law.go.kr 아웃바운드 "
                       "접근이 허용돼야 합니다.")
        else:
            verdict = "ERROR"
            message = f"❌ 법령 조회 실패: {error_type or 'unknown'}."

    return {
        "verdict": verdict,
        "message": message,
        "mode": cfg.mode,
        "law_api_credential_source": cfg.law_api_credential_source,
        "law_api_oc_configured": cfg.law_api_oc_configured,
        "law_api_key_fallback_configured": cfg.law_api_key_fallback_configured,
        "ready_for_external_calls": (
            cfg.mode in {"audit", "enabled"} and cfg.law_api_configured
        ),
        "sample_query": sample,
        "live_call_status": result.get("status", "not_attempted"),
        "live_error_type": result.get("error_type", ""),
        "live_http_status": int(result.get("raw_status", 0) or 0),
        "live_result_count": int(result.get("result_count", 0) or 0),
        "sanitized_source_url": result.get("source_url", ""),
    }


@app.get(
    "/api/debug/law-grounding/netdiag",
    dependencies=[Depends(_debug_rate_limit)],
)
async def debug_law_grounding_netdiag() -> Dict[str, Any]:
    """Deep, read-only network diagnostic for the Open Law API host.

    Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404): it
    returns resolved outbound IPs / network topology and triggers external
    probes, which must not be available to anonymous callers (M-10).

    When the selftest reports UNREACHABLE (HTTP status 0 / law_api_bad_response)
    the failure is below HTTP and could be DNS, a fully-blocked egress, the
    Korean government server refusing this server's (foreign / cloud) IP, a
    port-80-only block, or an HTTP-layer issue. This endpoint runs a small set
    of layered probes and returns the precise, secret-free cause plus a
    recommended remediation.

    The OC is NEVER sent in any probe and NEVER returned. Each probe is bounded
    by ``LAW_NETDIAG_TIMEOUT_SECONDS`` (default 4s). Never raises (beyond the
    availability gate above).
    """
    _require_debug_endpoints_enabled()
    import socket as _socket
    import urllib.error as _uerr
    import urllib.request as _ureq

    law_host = "www.law.go.kr"
    drf_path = "/DRF/lawSearch.do?target=law&type=JSON&query=test"  # no OC sent
    try:
        timeout = float(os.environ.get("LAW_NETDIAG_TIMEOUT_SECONDS") or 4.0)
    except (TypeError, ValueError):
        timeout = 4.0
    timeout = timeout if timeout > 0 else 4.0

    cfg = load_grounding_config()
    secrets = [s for s in (cfg.law_api_oc, cfg.law_api_key) if s]

    def _scrub(text: str) -> str:
        out = str(text or "")
        for secret in secrets:
            out = out.replace(secret, "[REDACTED]")
        return out[:300]

    def _tcp(host: str, port: int) -> Dict[str, Any]:
        try:
            with _socket.create_connection((host, port), timeout=timeout):
                return {"ok": True, "detail": f"TCP connect {host}:{port} OK"}
        except Exception as exc:  # noqa: BLE001 - diagnostic must never raise
            return {"ok": False, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

    def _http(url: str) -> Dict[str, Any]:
        req = _ureq.Request(
            url,
            headers={"User-Agent": "Paradiso-netdiag/1.0", "Accept": "*/*"},
        )
        try:
            with _ureq.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                code = int(getattr(resp, "status", 0) or getattr(resp, "code", 0) or 0)
                return {"ok": True, "http_status": code, "detail": f"HTTP {code}"}
        except _uerr.HTTPError as exc:
            # Any HTTP status (even 4xx/5xx) proves end-to-end reachability.
            code = int(getattr(exc, "code", 0) or 0)
            return {"ok": True, "http_status": code, "detail": _scrub(f"HTTPError {code}")}
        except Exception as exc:  # noqa: BLE001 - diagnostic must never raise
            return {"ok": False, "http_status": 0, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

    # 1) DNS resolution of the law host (no connection made).
    try:
        infos = _socket.getaddrinfo(law_host, None)
        dns = {"ok": True, "resolved_ips": sorted({i[4][0] for i in infos})}
    except Exception as exc:  # noqa: BLE001
        dns = {"ok": False, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

    # 2) Control egress to a neutral host by IP literal (no DNS dependency).
    egress = _tcp("1.1.1.1", 443)
    # 3) Raw TCP reachability of the law host on :80 and :443.
    law_tcp_80 = _tcp(law_host, 80)
    law_tcp_443 = _tcp(law_host, 443)
    # 4) HTTP(S) GET without the OC — distinguishes HTTP-layer from TCP-layer.
    law_http = _http(f"http://{law_host}{drf_path}")
    law_https = _http(f"https://{law_host}{drf_path}")

    diagnosis = classify_law_host_reachability({
        "dns_ok": dns.get("ok", False),
        "egress_ok": egress.get("ok", False),
        "law_https_ok": law_https.get("ok", False),
        "law_http_ok": law_http.get("ok", False),
        "law_tcp_443_ok": law_tcp_443.get("ok", False),
        "law_tcp_80_ok": law_tcp_80.get("ok", False),
    })

    recommendations = {
        "DNS_FAILURE": ("배포 환경이 www.law.go.kr 도메인을 DNS로 해석하지 못합니다. "
                        "Railway DNS 설정/도메인 차단 여부를 확인하세요."),
        "EGRESS_BLOCKED": ("아웃바운드 자체가 막혀 있습니다(중립 호스트 1.1.1.1:443도 실패). "
                           "Railway 네트워킹/방화벽에서 외부 접속을 허용하세요."),
        "REACHABLE_HTTPS": ("www.law.go.kr에 HTTPS로 연결됩니다. 실시간 법령 호출은 이미 https를 "
                            "기본으로 사용하므로 전송 경로는 정상입니다. 직전 selftest 실패는 일시적이거나 "
                            "OC/호출 IP 허용 문제일 수 있으니 selftest 결과(403=IP 미등록)를 확인하세요."),
        "REACHABLE_HTTP": ("www.law.go.kr에 HTTP로 연결됩니다. 직전 selftest 실패는 일시적"
                           "(타임아웃 등)일 수 있으니 selftest를 다시 실행해 보세요."),
        "LAWGOKR_CONNECTION_REFUSED": ("중립 호스트는 되지만 www.law.go.kr은 80/443 모두 연결이 "
                                       "거부/차단됩니다. 한국 정부 서버가 해외·클라우드 IP의 접속을 "
                                       "막는 것으로 보입니다. 한국 소재 프록시를 거치도록 LAW_API_BASE_URL을 "
                                       "설정하거나, open.law.go.kr에 호출 IP 허용을 요청해야 합니다."),
        "HTTP_PORT_80_BLOCKED": ("443은 열리지만 80이 막힙니다. 실시간 법령 호출은 이미 https(443)를 "
                                 "기본으로 사용하므로 전송 경로는 정상입니다."),
        "HTTP_LAYER_ISSUE": ("TCP는 연결되지만 HTTP 응답을 받지 못합니다. 프록시/방화벽의 HTTP 검사 "
                             "또는 서버 측 차단 가능성이 있습니다."),
    }

    return {
        "diagnosis": diagnosis,
        "recommendation": recommendations.get(diagnosis, ""),
        "law_host": law_host,
        "probe_timeout_seconds": timeout,
        "probes": {
            "dns_resolution": dns,
            "egress_control_1_1_1_1_443": egress,
            "law_tcp_80": law_tcp_80,
            "law_tcp_443": law_tcp_443,
            "law_http_get_no_oc": law_http,
            "law_https_get_no_oc": law_https,
        },
        "note": "이 진단은 OC 값을 전송하지 않으며 응답에도 포함하지 않습니다.",
    }


@app.post(
    "/api/debug/law-grounding",
    dependencies=[Depends(_debug_rate_limit)],
)
async def debug_law_grounding(req: DebugLawGroundingRequest) -> Dict[str, Any]:
    """Development/debug endpoint only, not a legal-advice production route.

    Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404, M-10).
    Always includes a non-secret `preflight` readiness block. When a question
    is supplied, also returns the (mode-gated, non-crashing) grounding context.
    """
    _require_debug_endpoints_enabled()
    prompt = (req.question or req.text or "").strip()
    if not prompt:
        # Empty body keeps the documented 400 contract. Operators who want a
        # no-question readiness probe should use GET /api/debug/law-grounding/preflight.
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_prompt",
                "message": "Provide a non-empty 'question' or 'text', or use GET /api/debug/law-grounding/preflight.",
            },
        )
    logger.info("debug-law-grounding request received (text_length=%d)", len(prompt))
    context = build_law_grounding_context(prompt)
    context["preflight"] = law_grounding_preflight(prompt)

    # Structured, secret-free evidence-pack view (Part F). Detects status /
    # question type, exposes the deterministic plan, and reports the normalized
    # evidence count + source confidence. Reuses ``context`` so it makes no extra
    # external call. OC / API-key values never appear; source URLs are sanitized.
    visa_hint = (req.visa_code or req.status or "").strip() or None
    visa_code_detected, _sub = _detect_visa_codes(visa_hint, None, prompt)
    task_type_detected = _detect_task_type(prompt)
    try:
        pack = build_law_evidence_pack(
            prompt,
            visa_code=visa_code_detected,
            task_type=task_type_detected,
            law_context=context,
        )
    except Exception:  # pragma: no cover - debug view must never crash
        pack = None

    cfg = load_grounding_config()
    context["evidence_pack"] = pack
    context["debug"] = {
        "mode": cfg.mode,
        "law_api_configured": cfg.law_api_configured,
        "law_api_oc_configured": cfg.law_api_oc_configured,
        "law_api_key_fallback_configured": cfg.law_api_key_fallback_configured,
        "law_api_credential_source": cfg.law_api_credential_source,
        "law_grounding_mode": cfg.mode,
        "detected_status": visa_code_detected,
        "task_type_detected": task_type_detected,
        "question_type": (pack or {}).get("question_type"),
        "risk_level": (pack or {}).get("risk_level"),
        "immigration_facts": (pack or {}).get("immigration_facts", {}),
        "legal_issue_types": (pack or {}).get("legal_issue_types", []),
        "proposed_activity_type": (pack or {}).get("proposed_activity_type", []),
        "source_plan": (pack or {}).get("source_plan", {}),
        "planned_law_queries": (pack or {}).get("planned_law_queries", []),
        "law_api_attempted": (pack or {}).get("law_api_attempted", False),
        "law_queries_attempted": (pack or {}).get("law_queries_attempted", []),
        "normalized_evidence_count": (pack or {}).get("law_evidence_count", 0),
        "error_type": (pack or {}).get("law_grounding_error", "") or context.get("error_type", ""),
        "parser_status": (pack or {}).get("parser_status", "") or context.get("parser_status", ""),
        "response_shape_hint": (pack or {}).get("response_shape_hint", "") or context.get("response_shape_hint", ""),
        "sanitized_source_url": (pack or {}).get("sanitized_source_url", "") or context.get("source_url", ""),
        "attempted_targets": (pack or {}).get("attempted_targets", []),
        "citation_verification_status": ((pack or {}).get("citation_verification") or context.get("citation_verification") or {}).get("status", ""),
        "law_grounding_status": (pack or {}).get("law_grounding_status"),
        "source_confidence_level": (pack or {}).get("source_confidence_level"),
        "answer_quality_mode": (pack or {}).get("answer_quality_mode"),
        "law_grounding_error": (pack or {}).get("law_grounding_error", ""),
        "legal_analysis": (pack or {}).get("legal_analysis"),
        "analysis_mode": (pack or {}).get("analysis_mode"),
        "main_issue": (pack or {}).get("main_issue"),
        "risk_posture": ((pack or {}).get("legal_analysis") or {}).get("risk_posture"),
        "confidence": ((pack or {}).get("legal_analysis") or {}).get("confidence"),
        "decisive_facts": ((pack or {}).get("legal_analysis") or {}).get("decisive_facts", []),
        "official_confirmation_questions": ((pack or {}).get("legal_analysis") or {}).get("official_confirmation_questions", []),
        "official_confirmation_questions_localized": (pack or {}).get("official_confirmation_questions_localized", []),
        "source_types_attempted": (pack or {}).get("source_types_attempted", []),
        "source_types_returned": (pack or {}).get("source_types_returned", []),
        "source_families_planned": (pack or {}).get("source_families_planned", []),
        "source_families_attempted": (pack or {}).get("source_families_attempted", []),
        "source_family_statuses": (pack or {}).get("source_family_statuses", {}),
        "source_family_result_counts": (pack or {}).get("source_family_result_counts", {}),
        "response_shape_hint_by_family": (pack or {}).get("response_shape_hint_by_family", {}),
        "parser_status_by_family": (pack or {}).get("parser_status_by_family", {}),
        "law_error_type_by_family": (pack or {}).get("law_error_type_by_family", {}),
        "sanitized_source_urls": (pack or {}).get("sanitized_source_urls", []),
        "normalized_evidence_count": (pack or {}).get("normalized_evidence_count", (pack or {}).get("law_evidence_count", 0)),
        "legal_analysis_confidence": ((pack or {}).get("legal_analysis") or {}).get("confidence"),
        "source_panel_state": (pack or {}).get("source_panel_state", ""),
        "direct_evidence_count": (pack or {}).get("direct_evidence_count", 0),
        "related_evidence_count": (pack or {}).get("related_evidence_count", 0),
        "analogical_evidence_count": (pack or {}).get("analogical_evidence_count", 0),
        "background_evidence_count": (pack or {}).get("background_evidence_count", 0),
        "missing_direct_authority": (pack or {}).get("missing_direct_authority", True),
        "source_state": (pack or {}).get("analysis_mode") or (pack or {}).get("law_grounding_status"),
        "answer_first_sentence": "",
        "first_sentence_quality_warning": "",
        "raw_code_default_ui_leak": False,
        # Source URLs are sanitized (OC removed) at the tool boundary before
        # they ever reach a caller; the debug view never reconstructs the OC.
        "source_urls_sanitized": True,
    }
    return context


# ---------------------------------------------------------------------------
# Nationality services / naturalization interview coach (text-first Waymaker)
#
# Isolated, additive endpoint for the 국적민원·귀화면접 준비 hub. It does NOT
# touch the /api/ask pipeline. Provider routing for this endpoint is Groq-first
# (fast short feedback) then OpenRouter (quality/fallback); when neither is
# configured it raises a 503 so the frontend falls back to local heuristic
# feedback. It never predicts pass/fail, never invents official sources, and
# never handles audio.
# ---------------------------------------------------------------------------

NATIONALITY_SERVICES_SYSTEM_PROMPT = (
    "You are Waymaker by Paradiso, acting as a source-aware Korean nationality "
    "civil affairs guide. You explain nationality-related procedures such as "
    "naturalization, nationality restoration, nationality loss, nationality "
    "renunciation, nationality retention, multiple nationality, oath and "
    "certificate issuance, review periods, interview preparation, and "
    "KIIP/evaluation relationships. You do not provide legal guarantees. You do "
    "not invent sources. You distinguish primary law, administrative rules, "
    "official notices, local notices, practice content, and secondary "
    "explainers. You give practical, natural Korean guidance and tell users when "
    "competent immigration office confirmation is needed. Reply with a single "
    "valid JSON object only (no prose, no markdown fences)."
)

NATURALIZATION_INTERVIEW_PREP_SYSTEM_PROMPT = (
    "You are Waymaker by Paradiso, acting as a text-first Korean naturalization "
    "interview preparation coach. You help users practice interview-style answers "
    "and pre-evaluation study flow. You do not provide legal guarantees, do not "
    "predict approval or failure, and do not claim unofficial content is "
    "official. You distinguish official-source-based guidance from practice "
    "questions and video reference topics. You give concise, natural Korean "
    "feedback unless the user requests another language. Never sound machine-"
    "translated, never over-flatter, never scare the user. Reply with a single "
    "valid JSON object only (no prose, no markdown fences)."
)


class NationalityCoachRequest(BaseModel):
    mode: Optional[str] = None
    lang: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    message: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None


def _coach_extract_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of the first JSON object from a model reply."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except (ValueError, TypeError):
        return None


async def _coach_complete(system_prompt: str, user_prompt: str) -> Dict[str, str]:
    """Groq-first, then OpenRouter. Bounded timeout. Raises 503 if no provider
    is configured or all providers fail — the caller turns that into the
    frontend's local-feedback fallback (never an infinite spinner)."""
    if httpx is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "httpx_missing", "message": "httpx is not installed."},
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    timeout = min(float(OPENROUTER_TIMEOUT_SECONDS), 20.0)
    providers: List[Dict[str, str]] = []
    if GROQ_API_KEY:
        providers.append({
            "name": "groq",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key": GROQ_API_KEY,
            "model": GROQ_MODEL,
        })
    if OPENROUTER_API_KEY:
        providers.append({
            "name": "openrouter",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key": OPENROUTER_API_KEY,
            "model": OPENROUTER_MODEL,
        })
    if not providers:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "coach_no_provider",
                "message": "No GROQ_API_KEY or OPENROUTER_API_KEY configured.",
            },
        )
    last_error: Optional[str] = None
    for prov in providers:
        payload = {
            "model": prov["model"],
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 700,
        }
        headers = {
            "Authorization": f"Bearer {prov['key']}",
            "Content-Type": "application/json",
        }
        if prov["name"] == "openrouter":
            if SITE_URL:
                headers["HTTP-Referer"] = SITE_URL
            if SITE_TITLE:
                headers["X-Title"] = SITE_TITLE
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(prov["url"], headers=headers, json=payload)
            if resp.status_code >= 400:
                last_error = f"{prov['name']} HTTP {resp.status_code}"
                continue
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"content": content, "provider": prov["name"], "model": prov["model"]}
        except Exception as exc:  # noqa: BLE001 — any provider failure → next/fallback
            last_error = f"{prov['name']}: {str(exc)[:120]}"
            continue
    raise HTTPException(
        status_code=503,
        detail={"error": "coach_unavailable", "message": last_error or "all providers failed"},
    )


@app.post(
    "/api/nationality-coach",
    dependencies=[Depends(rate_limit("nationality_coach", per_minute=6, per_day=100))],
)
async def nationality_coach(req: NationalityCoachRequest) -> Dict[str, Any]:
    mode = (req.mode or "naturalization_interview_prep").strip()
    lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"
    lang_line = (
        "Write all string values in natural English."
        if lang == "en"
        else "Write all string values in natural Korean (자연스러운 한국어)."
    )

    if mode == "nationality_services":
        system_prompt = NATIONALITY_SERVICES_SYSTEM_PROMPT
        question = (req.message or req.question or "").strip()
        user_prompt = (
            f"{lang_line}\n"
            "The user asks about Korean nationality civil affairs. Give general, "
            "source-aware guidance. Do not state final eligibility. Prefer hedged "
            "phrasing (일반적으로는 / 공식 안내 기준으로는 / 개별 사안은 관할 "
            "출입국외국인관서 확인이 필요합니다). Do not invent article numbers or "
            "source URLs.\n\n"
            f"User question: {question}\n\n"
            "Return ONLY this JSON object:\n"
            "{\n"
            '  "summary": "",\n'
            '  "relevantCategory": "",\n'
            '  "generalFlow": [],\n'
            '  "documentsNote": "",\n'
            '  "sourceBasedPoints": [],\n'
            '  "cautions": [],\n'
            '  "relatedSources": [],\n'
            '  "nextBestAction": ""\n'
            "}"
        )
    else:
        mode = "naturalization_interview_prep"
        system_prompt = NATURALIZATION_INTERVIEW_PREP_SYSTEM_PROMPT
        question = (req.question or "").strip()
        answer = (req.answer or "").strip()
        user_prompt = (
            f"{lang_line}\n"
            "This is naturalization-interview PRACTICE, not official adjudication. "
            "The question is practice material, not an official past question. "
            "Review the user's typed answer. Never predict pass/fail, never say "
            "the answer guarantees approval, never claim the question is official.\n"
            "Evaluate the answer along these practice dimensions (do NOT score or "
            "grade): 직접성(질문에 바로 답했는가), 구체성(경험·예시가 있는가), "
            "구조(이유→예시→결론), 태도·안전성(혜택·금전·의무회피만 강조하지 않는가). "
            "Put concrete, dimension-aware points in strengths/improvements.\n\n"
            f"Practice question (category={req.category or ''}, difficulty={req.difficulty or ''}):\n{question}\n\n"
            f"User's typed answer:\n{answer}\n\n"
            "Return ONLY this JSON object:\n"
            "{\n"
            '  "strengths": [],\n'
            '  "improvements": [],\n'
            '  "revisedAnswer": "",\n'
            '  "riskyExpressions": [],\n'
            '  "followUpQuestion": "",\n'
            '  "studyTip": "",\n'
            '  "caution": "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다."\n'
            "}"
        )

    result = await _coach_complete(system_prompt, user_prompt)
    parsed = _coach_extract_json(result["content"])
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=502,
            detail={"error": "coach_unparseable", "message": "Model did not return valid JSON."},
        )
    if mode == "naturalization_interview_prep":
        if not parsed.get("caution"):
            parsed["caution"] = "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다."
    parsed["mode"] = mode
    parsed["provider"] = result["provider"]
    parsed["ai_available"] = True
    return parsed


# ---------------------------------------------------------------------------
# PreView by Paradiso — read-only MOFA public-data proxy
# ---------------------------------------------------------------------------


@app.get(
    "/api/preview/mission",
    dependencies=[Depends(rate_limit("preview_mission", per_minute=20))],
)
def preview_mission(country: str = "", countryName: str = "") -> Any:
    """Pre-arrival mission lookup for PreView (외교부_국가·지역별 재외공관 정보).

    Read-only proxy: validates the query, resolves the portal service key
    (MOFA_EMBASSY_SERVICE_KEY -> PUBLIC_DATA_SERVICE_KEY), and returns a safe
    envelope in every case. The frontend falls back to labeled MVP sample
    data whenever ``ok`` is false or ``items`` is empty.

    Deliberately a sync route: the upstream call uses a blocking httpx
    client, so FastAPI must run it in the threadpool instead of stalling
    the event loop while data.go.kr responds.
    """
    outcome = mofa_public_data.fetch_mission_directory(
        country_iso2=country or None,
        country_name=countryName or None,
    )
    if outcome.get("error") == "invalid_query":
        return UTF8JSONResponse(status_code=400, content=outcome)
    return outcome


# ---------------------------------------------------------------------------
# Unified search (Visable hero) — deterministic organic results + optional
# AI Overview on a SEPARATE endpoint.
#
# The split is the whole point: /api/search/unified touches nothing but local
# data and returns in milliseconds, so the frontend can paint results while the
# overview is still in flight (or never arrives at all). An AI outage degrades
# the page to "no overview", never to "no results".
# ---------------------------------------------------------------------------
class UnifiedSearchRequest(BaseModel):
    query: str = ""
    lang: Optional[str] = None
    limit: Optional[int] = None
    includeManualEvidence: Optional[bool] = True


class UnifiedAiOverviewRequest(BaseModel):
    query: str = ""
    lang: Optional[str] = None
    intent: Optional[str] = None
    detectedVisaCodes: Optional[List[str]] = None


_UNIFIED_SEARCH_MAX_QUERY = _unified_search.MAX_QUERY_LENGTH


def _unified_manual_search(query: str) -> Dict[str, Any]:
    """Manual-index lookup for unified search; never raises, never blocks."""
    try:
        return _manual_search.search_manuals(query, limit=5)
    except Exception:
        return {"status": "index_unavailable", "approved": [], "needs_review": []}


@app.post(
    "/api/search/unified",
    dependencies=[Depends(rate_limit("search_unified", per_minute=60, per_day=2000))],
)
async def search_unified(req: UnifiedSearchRequest) -> Any:
    """Deterministic unified search. Local data only — no LLM, no outbound HTTP.

    Returns the organic result set, the detected intent, and an editable
    interpretation. ``aiOverview`` is always ``null`` here and
    ``aiOverviewStatus`` is ``pending``: the overview is fetched separately by
    ``/api/search/unified/ai-overview`` so rendering never waits on it.
    """
    started = time.monotonic()
    request_id = uuid.uuid4().hex[:16]
    query = (req.query or "").strip()[:_UNIFIED_SEARCH_MAX_QUERY]

    cached = _load_visas()
    visa_data = cached.get("visas") or []

    manual_search_fn = _unified_manual_search if (req.includeManualEvidence is not False) else None
    result = _unified_search.run_unified_search(
        query,
        visa_data=visa_data,
        valid_main_codes=set(_VALID_MAIN_CODES),
        manual_search=manual_search_fn,
        limit=max(1, min(int(req.limit or 10), 20)),
    )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    result.update({
        "requestId": request_id,
        "aiOverview": None,
        "aiOverviewStatus": "pending" if query else "not_applicable",
        "sourceCards": _unified_source_cards(result),
        "latency": {"deterministicMs": elapsed_ms},
        "version": _unified_search.UNIFIED_SEARCH_VERSION,
    })
    return result


def _unified_source_cards(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Official-source cards for the result page. Public URLs only, no secrets."""
    cards: List[Dict[str, Any]] = [
        {
            "id": "hikorea",
            "title": "하이코리아 (HiKorea)",
            "url": "https://www.hikorea.go.kr",
            "sourceType": "official_portal",
            "note": "체류·사증 민원의 공식 안내 및 신청 창구입니다.",
        },
        {
            "id": "call1345",
            "title": "외국인종합안내센터 1345",
            "url": "https://www.immigration.go.kr",
            "sourceType": "official_helpline",
            "note": "다국어 상담. 개별 사안의 최종 확인은 이곳에서 받으세요.",
        },
    ]
    if result.get("intent") == _unified_search.INTENT_LEGAL_QUESTION:
        cards.append({
            "id": "law_go_kr",
            "title": "국가법령정보센터 (법제처)",
            "url": "https://www.law.go.kr",
            "sourceType": "official_law",
            "note": "법령 원문은 공식 사이트에서 확인하세요.",
        })
    manual = result.get("manualEvidence") or {}
    if manual.get("reviewPendingCount"):
        cards.append({
            "id": "manual_review_pending",
            "title": "매뉴얼 본문 (검토 전)",
            "url": "",
            "sourceType": "manual_review_pending",
            "note": "검색된 매뉴얼 본문은 아직 사람이 원문과 대조·승인하지 않은 상태입니다. "
                    "참고용으로만 보시고, 확정 내용은 공식 출처에서 확인하세요.",
        })
    return cards


@app.post(
    "/api/search/unified/ai-overview",
    dependencies=[Depends(rate_limit("search_unified_ai", per_minute=10, per_day=200))],
)
async def search_unified_ai_overview(req: UnifiedAiOverviewRequest) -> Any:
    """AI Overview for a unified search result. Optional by construction.

    Failure is a first-class, *quiet* outcome: a provider outage returns
    ``status="unavailable"`` with a friendly reason and no answer text, so the
    frontend hides the overview card and leaves the organic results untouched.

    The model is never allowed to introduce a statute, article, case number or
    visa code that is not already grounded — anything it emits is put through the
    statute-citation guard against the retrieved evidence before it is returned.
    """
    started = time.monotonic()
    request_id = uuid.uuid4().hex[:16]
    query = (req.query or "").strip()[:_UNIFIED_SEARCH_MAX_QUERY]
    lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"

    if not query:
        return {"status": "not_applicable", "requestId": request_id,
                "overview": None, "citationVerification": None}

    providers = _providers_configured()
    if not any(providers.values()):
        return {
            "status": "unavailable",
            "reason": "no_provider_configured",
            "requestId": request_id,
            "overview": None,
            "fallbackAvailable": True,
            "message": ("AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요."
                        if lang == "ko" else
                        "The AI overview is unavailable. Please use the search results "
                        "and official sources below."),
        }

    cached = _load_visas()
    visa_data = cached.get("visas") or []
    deterministic = _unified_search.run_unified_search(
        query, visa_data=visa_data, valid_main_codes=set(_VALID_MAIN_CODES),
        manual_search=_unified_manual_search, limit=8,
    )

    # Evidence the model is allowed to speak from. Anything outside this set is a
    # citation failure by definition.
    evidence_lines: List[str] = []
    for card in deterministic.get("organicResults", []):
        if card.get("code"):
            evidence_lines.append(
                f"- [{card['code']}] {card.get('title', '')}: {card.get('summary', '')[:180]}")
    manual_state = (deterministic.get("manualEvidence") or {}).get("status", "not_queried")

    if not evidence_lines:
        # `blocked` in the design vocabulary: no summary was produced, and the
        # reason is stated rather than left as an empty card.
        return {
            "status": "blocked",
            "reason": ("검색된 근거 0건" if lang == "ko" else "no grounded evidence"),
            "requestId": request_id,
            "overview": None,
            "fallbackAvailable": True,
            "message": ("검색된 근거가 없어 요약을 만들지 않았습니다. 검색어를 바꾸거나 "
                        "공식 출처에서 확인해 주세요." if lang == "ko" else
                        "No grounded evidence was retrieved, so no overview was generated."),
        }

    prompt = _unified_overview_prompt(query, deterministic, evidence_lines, lang)

    def _overview_unavailable(reason: str) -> Dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": reason,
            "requestId": request_id,
            "overview": None,
            "fallbackAvailable": True,
            "message": ("AI 요약을 불러오지 못했습니다. 아래 검색 결과는 정상입니다."
                        if lang == "ko" else
                        "The AI overview could not be loaded. The search results below "
                        "are unaffected."),
        }

    # ``_openrouter_complete_with_candidates`` returns a RESULT DICT, never a
    # (text, meta) tuple. Unpacking it into two names raised ValueError on every
    # call, which the bare ``except Exception`` below swallowed into
    # ``provider_error`` — so this endpoint reported "unavailable" even when the
    # provider answered correctly. Read the documented keys instead.
    try:
        attempt_meta = await _openrouter_complete_with_candidates(prompt)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        reason, _retryable = _classify_openrouter_error(
            detail.get("status", exc.status_code), detail.get("message"), detail.get("error")
        )
        return _overview_unavailable(reason)
    except Exception:
        return _overview_unavailable("provider_error")

    if not attempt_meta.get("ok") or not (attempt_meta.get("answer") or "").strip():
        # Every candidate failed (or all are cooling down). This is the same
        # quiet, organic-results-preserving outcome as a transport failure, but
        # the classified provider reason is reported rather than a generic one.
        return _overview_unavailable(
            str(attempt_meta.get("provider_error_type") or "provider_error")
        )
    text = attempt_meta["answer"]

    # Citation guard: the overview is grounded in visa-data cards, not in fetched
    # statute text, so ANY statute citation it emits is unverifiable here and is
    # marked as such rather than rendered as a confirmed reference.
    verification = _statute_guard.verify_statute_citations(text, [], evidence_available=False)
    safe_text = _statute_guard.strip_failed_statute_citations(text, verification)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return {
        "status": "ok",
        "requestId": request_id,
        "overview": safe_text,
        "citationVerification": {
            "status": verification["status"],
            "unverifiableCount": verification["unverifiable_count"],
            "failureCount": verification["failure_count"],
        },
        "evidenceState": {
            "manual": manual_state,
            "directEvidenceCount": len(evidence_lines),
            "law": "not_queried",
        },
        "sources": _unified_overview_sources(deterministic),
        "evidenceLabel": _unified_evidence_label(deterministic, lang),
        "requiresOfficialConfirmation": True,
        # The result dict names the model that actually answered ``final_model``;
        # there is no "model"/"provider" key on it. Reading the wrong names made
        # both fields silently blank in every successful response.
        "provider": "openrouter",
        "model": attempt_meta.get("final_model") or "",
        "modelFallbackUsed": bool(attempt_meta.get("model_fallback_used")),
        "fallbackAvailable": True,
        "latency": {"totalMs": elapsed_ms},
    }


def _unified_overview_prompt(
    query: str,
    deterministic: Dict[str, Any],
    evidence_lines: List[str],
    lang: str,
) -> str:
    """Prompt shared by the buffered and streaming AI Overview endpoints.

    Shared deliberately: two copies would drift, and the hard rules here are the
    only thing stopping the model from inventing a statute or a visa code.
    """
    language_line = ("Write in natural Korean." if lang == "ko"
                     else "Write in natural English.")
    return (
        "You summarize Korean immigration/status-of-stay search results for a "
        "public information site. You are NOT giving legal advice.\n\n"
        f"User query: {query}\n"
        f"Detected intent: {deterministic.get('intent')}\n"
        f"Retrieved evidence (the ONLY facts you may use):\n"
        + "\n".join(evidence_lines[:8]) + "\n\n"
        "HARD RULES:\n"
        "1. Use ONLY the retrieved evidence above. Do not add requirements, "
        "deadlines, fees or eligibility rules that are not present in it.\n"
        "2. NEVER write a statute name, article number, case number, visa code, "
        "occupation code or industry code that does not appear above.\n"
        "3. Do not state whether the user is eligible or will be approved.\n"
        "4. 2-5 sentences. Then one short line naming the single most useful "
        "next action.\n"
        "5. End by telling the reader to confirm with HiKorea or 1345.\n\n"
        f"{language_line}"
    )


@app.post(
    "/api/search/unified/ai-overview/stream",
    dependencies=[Depends(rate_limit("search_unified_ai", per_minute=10, per_day=200))],
)
async def search_unified_ai_overview_stream(req: UnifiedAiOverviewRequest) -> Any:
    """SSE variant of the AI Overview — emits `streaming` deltas, then `done`.

    Exists so the design's `Streaming` state (Figma UX-03, node 406:92) is a real
    state and not decoration: without a producer the frontend could render it but
    nothing would ever trigger it.

    The citation guard runs on the ACCUMULATED text at the end, never per delta —
    a half-written statute reference would otherwise be judged incomplete and
    wrongly flagged. Until `done` arrives the client shows the text as provisional.
    """
    query = (req.query or "").strip()[:_UNIFIED_SEARCH_MAX_QUERY]
    lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"
    request_id = uuid.uuid4().hex[:16]

    async def event_stream():
        if not query:
            yield _sse("done", {"status": "not_applicable", "requestId": request_id})
            return
        if not _providers_configured().get("openrouter"):
            # Non-streaming providers cannot satisfy this endpoint; the client
            # falls back to the buffered endpoint rather than showing nothing.
            yield _sse("done", {
                "status": "unavailable", "reason": "streaming_not_available",
                "requestId": request_id, "fallbackAvailable": True,
                "message": ("실시간 요약을 사용할 수 없습니다. 일반 요약으로 대체합니다."
                            if lang == "ko" else
                            "Live summary is unavailable; falling back to the buffered summary."),
            })
            return

        cached = _load_visas()
        deterministic = _unified_search.run_unified_search(
            query, visa_data=cached.get("visas") or [],
            valid_main_codes=set(_VALID_MAIN_CODES),
            manual_search=_unified_manual_search, limit=8,
        )
        evidence_lines = [
            f"- [{c['code']}] {c.get('title', '')}: {c.get('summary', '')[:180]}"
            for c in deterministic.get("organicResults", []) if c.get("code")
        ]
        if not evidence_lines:
            yield _sse("done", {
                "status": "blocked",
                "reason": ("검색된 근거 0건" if lang == "ko" else "no grounded evidence"),
                "requestId": request_id, "fallbackAvailable": True,
            })
            return

        prompt = _unified_overview_prompt(query, deterministic, evidence_lines, lang)
        yield _sse("start", {"status": "streaming", "requestId": request_id})

        accumulated = ""
        try:
            candidates = _resolve_openrouter_candidates()
            model = candidates[0] if candidates else OPENROUTER_MODEL
            async for delta in _stream_openrouter_text(prompt, model):
                if not delta:
                    continue
                accumulated += delta
                yield _sse("delta", {"text": delta})
        except Exception:
            yield _sse("done", {
                "status": "unavailable", "reason": "provider_error",
                "requestId": request_id, "fallbackAvailable": True,
                "message": ("AI 요약을 불러오지 못했습니다. 아래 검색 결과는 정상입니다."
                            if lang == "ko" else
                            "The AI overview could not be loaded."),
            })
            return

        verification = _statute_guard.verify_statute_citations(
            accumulated, [], evidence_available=False)
        safe_text = _statute_guard.strip_failed_statute_citations(accumulated, verification)
        yield _sse("done", {
            "status": "ok",
            "requestId": request_id,
            "overview": safe_text,
            "citationVerification": {
                "status": verification["status"],
                "unverifiableCount": verification["unverifiable_count"],
                "failureCount": verification["failure_count"],
            },
            "evidenceState": {
                "manual": (deterministic.get("manualEvidence") or {}).get("status", "not_queried"),
                "directEvidenceCount": len(evidence_lines),
                "law": "not_queried",
            },
            "sources": _unified_overview_sources(deterministic),
            "evidenceLabel": _unified_evidence_label(deterministic, lang),
            "requiresOfficialConfirmation": True,
            "fallbackAvailable": True,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _unified_overview_sources(deterministic: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Source chips for the overview card (Figma UX-03 `SourceChips`).

    A source that could not be retrieved is included with ``unavailable: true``
    rather than omitted — the frontend dims it, so the evidence set never looks
    larger or cleaner than it actually is.
    """
    chips: List[Dict[str, Any]] = []
    for card in deterministic.get("organicResults", []):
        if card.get("kind") == _unified_search.RESULT_MANUAL_CARD:
            page = card.get("page")
            label = card.get("title") or "매뉴얼 본문"
            chips.append({
                "label": f"{label} p.{page}" if page else label,
                "kind": "manual",
                # Review-pending manual text is real evidence but not approved,
                # so it is shown dimmed rather than as a settled source.
                "unavailable": not card.get("usableAsDirectEvidence", False),
            })
        elif card.get("code"):
            chips.append({"label": f"{card['code']} {card.get('title', '')}".strip(),
                          "kind": "structured", "unavailable": False})
    manual = deterministic.get("manualEvidence") or {}
    if manual.get("status") == "index_unavailable":
        chips.append({"label": "매뉴얼 색인", "kind": "manual", "unavailable": True})
    # De-duplicate on label, keep first occurrence.
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for chip in chips:
        if chip["label"] and chip["label"] not in seen:
            seen.add(chip["label"])
            out.append(chip)
    return out[:8]


def _unified_evidence_label(deterministic: Dict[str, Any], lang: str) -> str:
    """One-line evidence tally, mirroring the design's '매뉴얼 직접 근거 N · …' line."""
    manual = deterministic.get("manualEvidence") or {}
    approved = int(manual.get("approvedCount") or 0)
    pending = int(manual.get("reviewPendingCount") or 0)
    structured = sum(1 for c in deterministic.get("organicResults", []) if c.get("code"))
    if lang == "ko":
        parts = [f"구조화 데이터 {structured}건"]
        if approved:
            parts.append(f"매뉴얼 직접 근거 {approved}건")
        if pending:
            parts.append(f"검토 전 매뉴얼 {pending}건")
        parts.append("공식 확인 필요")
        return " · ".join(parts)
    parts = [f"{structured} structured records"]
    if approved:
        parts.append(f"{approved} approved manual")
    if pending:
        parts.append(f"{pending} unreviewed manual")
    parts.append("official confirmation required")
    return " · ".join(parts)


class EmploymentInterpretRequest(BaseModel):
    text: str = ""
    lang: Optional[str] = None


class EnforcementExtractRequest(BaseModel):
    text: str = Field(default="", max_length=3000)
    assessment_date: Optional[date] = Field(default=None, alias="assessmentDate")


class EnforcementAnalyzeRequest(BaseModel):
    case_data: Dict[str, Any] = Field(alias="caseData")


async def _enforcement_ai_provider(prompt: str) -> Dict[str, Any]:
    """Narrow adapter over Visable's existing OpenRouter provider policy."""
    return await _openrouter_complete_with_candidates(prompt, max_tokens=1800)


@app.post(
    "/api/enforcement/extract",
    dependencies=[Depends(rate_limit("enforcement_extract", per_minute=10, per_day=200))],
)
async def enforcement_extract(req: EnforcementExtractRequest) -> Any:
    """Convert a sensitive narrative into non-identifying structured facts."""
    if not (req.text or "").strip():
        raise HTTPException(status_code=422, detail="case text is required")
    provider = _enforcement_ai_provider if OPENROUTER_API_KEY else None
    case = await extract_structured_case(
        req.text,
        provider=provider,
        assessment_date=req.assessment_date,
    )
    return {"schemaVersion": "1", "case": case.public_dict()}


@app.post(
    "/api/enforcement/analyze",
    dependencies=[Depends(rate_limit("enforcement_analyze", per_minute=8, per_day=160))],
)
async def enforcement_analyze(req: EnforcementAnalyzeRequest) -> Any:
    """Calculate the law first, then request a bounded outcome prediction."""
    try:
        case = StructuredCase.model_validate(req.case_data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid structured enforcement case") from exc
    provider = _enforcement_ai_provider if OPENROUTER_API_KEY else None
    analysis = await analyze_enforcement_case(case, prediction_provider=provider)
    return analysis.public_dict()


@app.post(
    "/api/employment/interpret",
    dependencies=[Depends(rate_limit("employment_interpret", per_minute=12, per_day=300))],
)
async def employment_interpret(req: EmploymentInterpretRequest) -> Any:
    """Extract structured job facts from free text for the 취업정보 신고 helper.

    This endpoint NEVER returns a KSCO8 직종 code or a KSIC11 업종 code and never
    decides whether reporting is required. It returns validated *facts* which the
    frontend feeds into the existing deterministic analyzer — the only component
    that may produce a code, because it retrieves codes from the official tables.

    Anything the model emits outside the fixed schema is dropped, and every
    removal is reported in ``warnings`` so the sanitization is auditable.
    """
    text = (req.text or "").strip()[:600]
    lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"

    if not text:
        return {"status": "empty_input", "extraction": _employment_nl.empty_extraction(),
                "analyzerInput": None, "interpretation": "", "warnings": []}

    if not any(_providers_configured().values()):
        # The guided/deterministic flow in the UI is unaffected; only the
        # free-sentence convenience layer is unavailable.
        return {
            "status": "unavailable",
            "reason": "no_provider_configured",
            "extraction": _employment_nl.empty_extraction(),
            "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
            "interpretation": "",
            "warnings": [],
            "fallbackAvailable": True,
        }

    prompt = _employment_nl.build_extraction_prompt(text, lang=lang)

    def _interpret_unavailable(reason: str) -> Dict[str, Any]:
        # The deterministic analyzer is the fallback, so the raw sentence still
        # reaches it: this layer is a convenience, never a gate.
        return {
            "status": "unavailable",
            "reason": reason,
            "extraction": _employment_nl.empty_extraction(),
            "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
            "interpretation": "",
            "warnings": [],
            "fallbackAvailable": True,
        }

    # Same defect as the AI Overview endpoint: the helper returns a RESULT DICT,
    # not a (text, meta) tuple, so this unpack raised ValueError on every call
    # and the bare ``except Exception`` reported a provider failure that had not
    # happened. Employment interpretation never once ran in production.
    try:
        attempt_meta = await _openrouter_complete_with_candidates(prompt)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        reason, _retryable = _classify_openrouter_error(
            detail.get("status", exc.status_code), detail.get("message"), detail.get("error")
        )
        return _interpret_unavailable(reason)
    except Exception:
        return _interpret_unavailable("provider_error")

    if not attempt_meta.get("ok") or not (attempt_meta.get("answer") or "").strip():
        return _interpret_unavailable(
            str(attempt_meta.get("provider_error_type") or "provider_error")
        )
    raw = attempt_meta["answer"]

    try:
        known_codes = {
            str(r.get("code")).strip().upper()
            for r in (_load_visas().get("visas") or [])
            if isinstance(r, dict) and r.get("code")
        }
    except Exception:
        known_codes = set()

    validated = _employment_nl.validate_extraction(raw, allowed_visa_codes=known_codes or None)
    if not validated["ok"]:
        return {
            "status": "extraction_failed",
            "reason": validated["reason"],
            "extraction": validated["data"],
            "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
            "interpretation": "",
            "warnings": validated["warnings"],
            "fallbackAvailable": True,
        }

    data = validated["data"]
    return {
        "status": "ok",
        "extraction": data,
        "analyzerInput": _employment_nl.to_analyzer_input(data, original_text=text),
        "interpretation": _employment_nl.build_interpretation_sentence(data, lang=lang),
        "needsClarification": bool(data.get("needsClarification")),
        "clarificationQuestion": data.get("clarificationQuestion", ""),
        "warnings": validated["warnings"],
        "fallbackAvailable": True,
        "provider": "openrouter",
        "model": attempt_meta.get("final_model") or "",
        "notice": ("직종·업종 코드는 이 단계에서 만들지 않습니다. 아래 후보는 공식 분류표에서 "
                   "검색한 결과이며, 최종 확정은 하이코리아에서 확인하세요."
                   if lang == "ko" else
                   "No classification code is produced at this step. Candidates below are "
                   "retrieved from the official tables; confirm the final code with HiKorea."),
    }


@app.get("/api/search/manual-evidence-state")
async def manual_evidence_state_endpoint() -> Dict[str, Any]:
    """Operator-safe snapshot of the manual approval layer. No secrets, no bodies."""
    summary = _manual_registry.registry_summary()
    return {
        "registryVersion": summary["registry_version"],
        "documentCount": summary["document_count"],
        "familyCount": summary["family_count"],
        "approvalCounts": summary["approval_counts"],
        "indexAvailable": _manual_search.index_available(),
        "note": "Only approval_state='approved' content may back a direct assertion.",
    }


# ---------------------------------------------------------------------------
# Entrypoint helper for local runs
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "paradiso_backend:app",
        host="0.0.0.0",
        port=port,
        reload=bool(os.environ.get("RELOAD")),
    )
