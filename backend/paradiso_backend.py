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
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from services.law_grounding import (
    build_law_grounding_context,
    build_law_search_query,
    law_grounding_preflight,
    should_attempt_law_grounding,
)
from services.grounding_config import load_grounding_config
from services.law_tools import build_law_evidence_pack
from services.legal_analysis import first_sentence_quality_warning
from services.answer_quality import (
    ANSWER_STYLE_VERSION,
    build_answer_directives,
    classify_answer_quality,
)
from services import answer_quality as _answer_quality


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
# variable `openrouter/auto` router. The verified free model id is mirrored
# in backend/.env.example and docs/data/MODEL_PRIORITY_COOLDOWN_OLLAMA_SCAFFOLD_2026_05.md.
# Override per-deploy with the OPENROUTER_MODEL env var if the catalog changes.
_DEFAULT_OPENROUTER_MODEL: str = "qwen/qwen3-next-80b-a3b-instruct:free"
OPENROUTER_MODEL: str = (
    os.environ.get("OPENROUTER_MODEL", "").strip() or _DEFAULT_OPENROUTER_MODEL
)

# Explicit, predictable OpenRouter fallback candidates. When the primary model
# is rate-limited (429) or its upstream is unavailable (503 / "no healthy
# upstream"), Paradiso retries the NEXT OpenRouter candidate rather than
# silently switching providers or surfacing raw provider JSON. Random
# free-model routing (openrouter/auto) is intentionally NOT used — Paradiso
# needs predictable model behaviour and auditable response metadata.
_DEFAULT_OPENROUTER_MODEL_CANDIDATES: List[str] = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k2.6:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

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
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    """Log the active provider/model and law-grounding mode at startup.

    Reports only non-secret descriptors (provider name, public model id,
    feature flags). API keys are never logged.
    """
    llm = _resolve_llm_config()
    law_mode = (os.environ.get("LAW_GROUNDING_MODE") or "disabled").strip().lower()
    logger.info(
        "Paradiso backend startup: llm_provider=%s llm_model=%s groq_fallback_allowed=%s law_grounding_mode=%s",
        llm["provider"],
        llm["model"],
        llm["groq_fallback_allowed"],
        law_mode,
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
    law_grounding_intent_reasons: List[str] = Field(default_factory=list)
    law_search_query: str = ""
    law_grounding_warnings: List[str] = Field(default_factory=list)
    citation_verification: Optional[Dict[str, Any]] = None
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
    answer_style_version: str = ANSWER_STYLE_VERSION
    question_type_detected: str = "general"
    # Structured law/manual evidence pack (Part D). Non-secret: sanitized source
    # URLs only, OC/API-key values never appear. ``law_evidence_pack`` is the
    # full structured object; the flat fields below are convenience projections
    # for the frontend source panel and the smoke harness.
    law_evidence_pack: Optional[Dict[str, Any]] = None
    planned_law_queries: List[str] = Field(default_factory=list)
    law_sources: List[Dict[str, Any]] = Field(default_factory=list)
    law_evidence_count: int = 0
    legal_analysis: Optional[Dict[str, Any]] = None
    legal_analysis_exists: bool = False
    immigration_facts: Dict[str, Any] = Field(default_factory=dict)
    legal_issue_types: List[str] = Field(default_factory=list)
    proposed_activity_type: List[str] = Field(default_factory=list)
    source_plan: Dict[str, Any] = Field(default_factory=dict)
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
    direct_manual_sources: List[Dict[str, Any]] = Field(default_factory=list)
    related_manual_sources: List[Dict[str, Any]] = Field(default_factory=list)
    law_grounding_error: str = ""
    # OpenRouter model-candidate fallback transparency (non-secret). When the
    # primary model is rate-limited / upstream-unavailable, Paradiso retries the
    # next explicit OpenRouter candidate rather than switching providers.
    llm_provider: str = ""
    requested_model: Optional[str] = None
    primary_model: Optional[str] = None
    model_candidates: List[str] = Field(default_factory=list)
    attempted_models: List[str] = Field(default_factory=list)
    final_model: Optional[str] = None
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
    replacement = (
        "F-2-99로 체류자격 변경이 완료되었다면, 부업 여부는 이전 E-7 기준만으로 판단할 사안은 아니고 "
        "현재 F-2-99의 활동범위와 승인 조건을 기준으로 다시 검토해야 합니다. 다만 E-7의 근무처 추가 신고 의무가 "
        "자동으로 계속 적용되는지, 또는 전혀 적용되지 않는지는 개별 승인 조건과 부업의 형태를 확인해야 합니다."
    )
    risky_patterns = [
        r"체류자격이\s*E-7\(특정활동\)에서\s*F-2-99\(거주\)로\s*변경되었다면,?\s*원칙적으로\s*이전\s*자격인\s*E-7에\s*묶여\s*있던\s*근무처\s*변경·추가\s*신고\s*의무는\s*더\s*이상\s*적용되지\s*않습니다\. ?",
        r"원칙적으로\s*이전\s*자격인\s*E-7에\s*묶여\s*있던\s*근무처\s*변경·추가\s*신고\s*의무는\s*더\s*이상\s*적용되지\s*않습니다\. ?",
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
    if OPENROUTER_API_KEY:
        return {
            "provider": "openrouter",
            "model": OPENROUTER_MODEL,
            "configured": True,
            "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
            "warnings": _groq_fallback_warnings("openrouter"),
        }
    if GROQ_API_KEY and ALLOW_GROQ_FALLBACK:
        return {
            "provider": "groq",
            "model": GROQ_MODEL,
            "configured": True,
            "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
            "warnings": _groq_fallback_warnings("groq"),
        }
    return {
        "provider": "none",
        "model": None,
        "configured": False,
        "groq_fallback_allowed": ALLOW_GROQ_FALLBACK,
        "warnings": _groq_fallback_warnings("none"),
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


async def _call_openrouter(prompt: str, model: Optional[str] = None) -> str:
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

    payload = {
        "model": model or OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if SITE_URL:
        headers["HTTP-Referer"] = SITE_URL
    if SITE_TITLE:
        headers["X-Title"] = SITE_TITLE
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
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
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openrouter_bad_response",
                "message": f"Unexpected OpenRouter payload: {exc}",
            },
        )


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
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
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
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "groq_bad_response",
                "message": f"Unexpected Groq payload: {exc}",
            },
        )


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
    # Model not found / unauthorized model -> do not retry blindly.
    if (
        status_int == 404
        or "not found" in msg
        or "no endpoints" in msg
        or "no allowed providers" in msg
        or "unknown model" in msg
    ):
        return "invalid_provider_config", False
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
        "messages": [{"role": "user", "content": prompt}],
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
    if "registration_or_residence_report" in issues:
        return f"{current}의 외국인등록·체류 신고 기한, 신고 사유, 접수 방법을 공식 절차 기준으로 확인해야 합니다."
    if "workplace_change_addition" in issues or "reporting_duty" in issues:
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
    registration = bool(issue_set & {"registration_or_residence_report", "reporting_duty"}) and not study
    status_change = "status_change" in issue_set
    return {"study": study, "work": work, "registration": registration, "status_change": status_change}


def _fallback_fact_lines_localized(issues: List[str], facts: Dict[str, Any], activities: List[str], *, is_ko: bool) -> List[str]:
    """Issue-aware 'facts to confirm' bullets with natural-language labels.

    Replaces the internal snake_case ``decisive_facts`` list (current_status/
    sub_status, paid_or_credit_bearing, duration/employer_or_school, ...) so the
    user-facing memo never exposes backend field names (Part D / Part E).
    """
    kinds = _fallback_activity_kinds(issues, activities)
    lines: List[str] = []
    if is_ko:
        if kinds["study"]:
            lines.append("학점 인정 여부 또는 학위 과정 관련성")
            lines.append("수업 기간, 주당 시간, 학교 등록 방식")
        if kinds["work"]:
            lines.append("보수 발생 여부와 부업·근로 형태(고용/프리랜서/사업/단순 부수입)")
            lines.append("추가 고용주·사업자등록 여부, 업종·근무시간·계약형태")
        if "post_status_change_residual_duty" in set(issues or []):
            lines.append("이전 체류자격의 승인 조건과 신고 이력이 현재 활동에 남는지")
        if kinds["registration"]:
            lines.append("신고 기산일(입국·자격변경·주소변경 등)과 현재 체류자격 기준 신고 기한")
            lines.append("신고 접수 방법(하이코리아 또는 관할 출입국·외국인청)")
        return list(dict.fromkeys(lines))[:6]
    if kinds["study"]:
        lines.append("whether the course is credit-bearing or degree-related")
        lines.append("the course duration, weekly hours, and how the school registers it")
    if kinds["work"]:
        lines.append("whether it is paid and the work form (employment/freelance/business/incidental)")
        lines.append("any additional employer/business registration, industry, hours, and contract type")
    if "post_status_change_residual_duty" in set(issues or []):
        lines.append("whether the previous status's approval conditions or reporting history still apply")
    if kinds["registration"]:
        lines.append("the event that starts the deadline (entry, status change, address change) and the time limit")
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
        if kinds["registration"]:
            return [
                "한국에 입국한 날짜(입국일)는 언제인지",
                "부여받은 체류기간은 얼마인지",
                "외국인등록 등 신고 기한은 며칠인지",
                "신고를 어디서·어떻게(하이코리아 또는 관할 출입국·외국인청 방문) 하는지",
            ]
        if kinds["status_change"] and facts.get("target_status"):
            target = facts.get("target_status")
            return [
                f"현재 체류자격이 {current}인지, 세부 코드는 무엇인지",
                f"{target}로의 변경 요건을 충족하는지",
                "국내 변경인지, 재외공관 사증 신청인지",
                "남은 체류기간과 변경 신청 시점",
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
    if kinds["registration"]:
        return [
            "your date of entry into Korea",
            "the period of stay you were granted",
            "the alien-registration / reporting deadline in days",
            "where and how to file (HiKorea or the competent immigration office)",
        ]
    if kinds["status_change"] and facts.get("target_status"):
        target = facts.get("target_status")
        return [
            f"whether your current status is {current} and its sub-code",
            f"whether you meet the requirements to change to {target}",
            "whether this is an in-country change or a consular visa application",
            "your remaining period of stay and when you would apply",
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
) -> str:
    """Build a deterministic outage fallback from generalized legal_analysis.

    This deliberately avoids status/activity templates. Study-specific wording
    appears only when legal_analysis actually classified the issue/activity as
    study-related.
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

    practical = str(la.get("practical_posture") or "").strip()
    main_issue = str(la.get("main_issue") or base_meta.get("main_issue") or "").strip()
    if is_ko:
        practical = _korean_practical_fallback(issues, facts, activities, activity_labels)
        main_issue = _korean_main_issue_fallback(issues, facts, activity_labels)
        intro = "AI 모델이 일시적으로 응답하지 않아, Paradiso가 구조화된 법률 분석 메모를 대신 표시합니다."
        lines = [intro, ""]
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
        elif "registration_or_residence_report" in issues:
            status = current or "현재 체류자격"
            lines.append(f"{status} 관련 외국인등록·체류 신고 문제이므로, 학교 등록이 아니라 출입국 체류 신고의 기한·대상·관할을 중심으로 확인해야 합니다.")
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

    intro = "The AI model is temporarily unavailable, so Paradiso is showing a structured legal-analysis preparation note."
    lines = [intro, ""]
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
    elif "registration_or_residence_report" in issues:
        status = current or "the current status"
        lines.append(f"This is an alien-registration/residence-reporting issue for {status}; do not treat the word registration as school enrollment unless the facts say that. ")
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


async def _openrouter_complete_with_candidates(
    prompt: str, requested_model: Optional[str] = None
) -> Dict[str, Any]:
    """Try OpenRouter candidates in order, skipping models in short cooldown.

    Retryable failures (429/503/timeout/temporary upstream unavailability) mark
    that model in an in-memory cooldown map. Later requests skip cooling models.
    If every candidate is cooling down, this function does not hammer any model;
    it returns deterministic metadata so /api/ask can use the preparation-note
    fallback (or an explicitly enabled provider-family/private fallback).
    """
    if requested_model:
        candidates = _dedupe_preserve_order([requested_model, *OPENROUTER_MODEL_CANDIDATES])
    else:
        candidates = list(OPENROUTER_MODEL_CANDIDATES) or [OPENROUTER_MODEL]

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
            answer = await _call_openrouter(prompt, model=model)
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
            if not last_retryable:
                break  # auth/bad-request/model-not-found/safety: stop early
            continue
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
    workplace_ko = ("근무처 변경", "근무처 추가", "근무처 변경신고", "이직", "직장을 바꾸", "직장 변경")
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
    source_date = bundle.get("source_date", "2026.5")
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
        f"[참고 자료] {source_title} ({source_date}) — {issuing_body}{page_label}\n"
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
        f"- 출처를 다음과 같이 명시하십시오: {source_title} ({source_date}), {issuing_body}.\n"
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


def _build_source_confirmed_structured_requirements_block(
    visa_code: Optional[str],
    visa_sub_code: Optional[str] = None,
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
    if _structured_requirements is None or not visa_code:
        return ""
    try:
        entries = _structured_requirements.get_source_confirmed_structured_requirements(
            visa_code
        )
    except Exception:  # pragma: no cover - defensive only
        return ""
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
        "[Source-confirmed structured requirements from 2026-05 official manuals]\n"
        "The items below were locally verified against the official 2026-05"
        " manual at the cited page(s) and are limited to the exact section/"
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
    # Non-secret Open Law API posture. NEVER exposes LAW_API_OC / LAW_API_KEY
    # values — only booleans, the resolved mode, and which env var supplied the
    # credential. Computed live so LAW_API_OC-only deployments report correctly.
    try:
        law_cfg = load_grounding_config()
        law_api_status: Dict[str, Any] = {
            "law_api_configured": law_cfg.law_api_configured,
            "law_api_oc_configured": law_cfg.law_api_oc_configured,
            "law_api_key_fallback_configured": law_cfg.law_api_key_fallback_configured,
            "law_api_credential_source": law_cfg.law_api_credential_source,
        }
    except Exception:  # pragma: no cover - defensive
        law_api_status = {
            "law_api_configured": bool(LAW_API_KEY),
            "law_api_oc_configured": False,
            "law_api_key_fallback_configured": bool(LAW_API_KEY),
            "law_api_credential_source": "LAW_API_KEY" if LAW_API_KEY else "",
        }
    return {
        "status": "ok",
        "service": "paradiso-backend",
        "version": app.version,
        "providers": _providers_configured(),
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
            "provider_family_fallback_allowed": llm["groq_fallback_allowed"],
            "candidate_warnings": candidate_warnings,
            **_openrouter_cooldown_metadata(),
            "ollama_fallback_enabled": ENABLE_OLLAMA_FALLBACK,
            "ollama_model": OLLAMA_MODEL,
            "ollama_configured": bool(ENABLE_OLLAMA_FALLBACK and OLLAMA_BASE_URL),
            "ollama_timeout_seconds": OLLAMA_TIMEOUT_SECONDS,
        },
        "law_grounding_mode": (os.environ.get("LAW_GROUNDING_MODE") or "disabled").strip().lower(),
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


@app.post("/api/ask", response_model=AskResponse)
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
    structured_block = _build_source_confirmed_structured_requirements_block(
        visa_code_detected, visa_sub_code_detected
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
    law_grounding_warnings: List[str] = []
    citation_verification: Optional[Dict[str, Any]] = None
    law_context: Dict[str, Any] = {}
    mode = (os.environ.get("LAW_GROUNDING_MODE") or "disabled").strip().lower()
    intent = should_attempt_law_grounding(prompt)
    if intent.get("should_attempt"):
        law_grounding_intent_reasons = list(intent.get("reasons", []) or [])
        if mode in {"audit", "enabled"}:
            law_context = build_law_grounding_context(prompt)
            law_grounding_attempted = bool(law_context.get("attempted"))
            law_grounding_used = bool(law_context.get("law_grounding_used"))
            law_grounding_warnings = law_context.get("grounding_warnings", []) or []
            citation_verification = law_context.get("citation_verification")
            law_search_query = law_context.get("law_search_query", "") or ""
            law_grounding_status = "used" if law_grounding_used else "unavailable"
            # The normalized law evidence is injected below via the structured
            # evidence pack (a single compact summary), not as a second raw dump.
        else:
            # Intent detected but grounding is disabled: surface the state and
            # the query that WOULD be issued, without making any external call.
            law_grounding_status = "disabled"
            law_search_query = build_law_search_query(prompt, law_grounding_intent_reasons)
            law_grounding_warnings = ["LAW_GROUNDING_DISABLED"]

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
        if mode in {"audit", "enabled"}:
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
            manual_evidence={"direct": grounding_sources, "related": []},
            manual_present=(grounding is not None),
            structured_present=bool(structured_block),
            procedure_variant_present=bool(procedure_variant_block),
            law_context=law_context,
            quality=quality,
        )
    except Exception:  # pragma: no cover - the pack must never break /api/ask
        law_evidence_pack = None

    if law_evidence_pack and law_evidence_pack.get("citation_verification"):
        citation_verification = law_evidence_pack.get("citation_verification")

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
                "Confidence gate: if answer_certainty_level is not direct, missing_direct_authority is true, direct_evidence_count is 0, or law_lookup_error_type is LAW_API_BAD_RESPONSE/SOURCE_UNAVAILABLE, avoid final conclusion verbs. Do not say 신고 의무는 없습니다, 반드시 신고해야 합니다, 허용됩니다, 가능합니다, or 원칙적으로 이전 E-7 의무는 더 이상 적용되지 않습니다 unless direct authority supports it. For E-7→F-2-99 side-job questions, say current F-2-99 status is primary, prior E-7 is related/comparative, and decisive facts are F-2-99 approval conditions plus side activity form/employer/client/industry/hours/compensation.\n"
                "Required framing: use the issue-based template; practical legal posture first; identify current status/activity/issue; explain backend legal_analysis; source basis later; concrete official-confirmation questions fourth; no final administrative determination.\n"
                "Official-confirmation questions:\n" + confirmation_lines
            )

    final_prompt += "\n\n" + build_answer_directives(quality, lang=req.lang)

    llm = _resolve_llm_config()

    base_meta: Dict[str, Any] = dict(
        grounding_used=bool(grounding),
        grounding_sources=grounding_sources,
        procedure_variant_context_used=bool(procedure_variant_block),
        procedure_variant_context_sources=procedure_variant_context_sources,
        visa_code_detected=visa_code_detected,
        visa_sub_code_detected=visa_sub_code_detected,
        task_type_detected=task_type_detected,
        risk_level_detected=risk_level_detected,
        law_grounding_used=law_grounding_used,
        law_grounding_attempted=law_grounding_attempted,
        law_grounding_status=law_grounding_status,
        law_grounding_intent_reasons=law_grounding_intent_reasons,
        law_search_query=law_search_query,
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
        answer_style_version=quality["answer_style_version"],
        question_type_detected=quality["question_type"],
        # Structured law/manual evidence pack (Part D) + convenience fields.
        # Secret-free: source URLs are sanitized and OC/keys never appear.
        law_evidence_pack=law_evidence_pack,
        planned_law_queries=(law_evidence_pack or {}).get("planned_law_queries", []),
        law_sources=(law_evidence_pack or {}).get("law_sources", []),
        law_evidence_count=(law_evidence_pack or {}).get("law_evidence_count", 0),
        legal_analysis=(law_evidence_pack or {}).get("legal_analysis"),
        immigration_facts=(law_evidence_pack or {}).get("immigration_facts", {}),
        legal_issue_types=(law_evidence_pack or {}).get("legal_issue_types", []),
        proposed_activity_type=(law_evidence_pack or {}).get("proposed_activity_type", []),
        source_plan=(law_evidence_pack or {}).get("source_plan", {}),
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
        law_grounding_error=(law_evidence_pack or {}).get("law_grounding_error", ""),
        parser_status=(law_evidence_pack or {}).get("parser_status", ""),
        response_shape_hint=(law_evidence_pack or {}).get("response_shape_hint", ""),
        source_panel_status=((law_evidence_pack or {}).get("citation_verification") or {}).get("status", ""),
        **source_panel_meta,
    )

    if llm["provider"] == "openrouter":
        result = await _openrouter_complete_with_candidates(
            final_prompt, requested_model=req.model
        )
        # Non-secret attempt metadata (model ids + classified error only).
        attempt_meta: Dict[str, Any] = dict(
            llm_provider="openrouter",
            requested_model=result["requested_model"],
            primary_model=result["primary_model"],
            model_candidates=result["model_candidates"],
            attempted_models=result["attempted_models"],
            final_model=result["final_model"],
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
        answer = await _call_groq(final_prompt, model=req.model)
        groq_model = req.model or GROQ_MODEL
        response_meta = dict(base_meta)
        answer = _confidence_gate_answer_text(answer, response_meta)
        response_meta["answer_first_sentence"] = (answer or "").strip().split(".", 1)[0].strip()
        response_meta["first_sentence_quality_warning"] = first_sentence_quality_warning(answer)
        return AskResponse(
            answer=answer,
            provider="groq",
            model=groq_model,
            llm_provider="groq",
            requested_model=req.model,
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


@app.get("/api/debug/law-grounding/preflight")
async def debug_law_grounding_preflight(question: Optional[str] = None) -> Dict[str, Any]:
    """Operator-safe law-grounding readiness preflight (no external call, no secrets).

    Reports the resolved mode, whether the API key / endpoint are configured
    (booleans only), whether a sample question would trigger grounding, the
    statutory query that would be issued, and explicit warning markers
    (LAW_GROUNDING_DISABLED / LAW_GROUNDING_AUDIT_ONLY / LAW_API_KEY_MISSING /
    LAW_API_ENDPOINT_MISSING). Useful even when external calls are disabled.
    """
    return law_grounding_preflight(question or "")


@app.post("/api/debug/law-grounding")
async def debug_law_grounding(req: DebugLawGroundingRequest) -> Dict[str, Any]:
    """Development/debug endpoint only, not a legal-advice production route.

    Always includes a non-secret `preflight` readiness block. When a question
    is supplied, also returns the (mode-gated, non-crashing) grounding context.
    """
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
