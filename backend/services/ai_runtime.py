"""Visable shared AI runtime — one canonical place for provider semantics.

Why this module exists
----------------------
Visable's AI features grew independently, and each one re-derived its own
answer to the same questions: which provider, which model, what counts as a
retryable failure, how long to wait, what to do when the model returns
nothing. That fragmentation produced real outages — a feature whose provider
routing ignored the deployment's fallback policy, and two endpoints that
misread the completion contract and reported a healthy provider as an outage
for their entire production lifetime.

This module owns the answers so features do not have to:

* :class:`AIErrorType` — the shared provider-failure taxonomy.
* :func:`classify_provider_error` — HTTP status + sanitized message -> taxonomy.
* :class:`ModelCooldownRegistry` — the circuit breaker for a failing model.
* :class:`TaskRole` / :func:`resolve_task_models` — a capability, not a
  hardcoded model string, is what a feature asks for.
* :class:`AIResult` — the completion contract, with a shape that cannot be
  mistaken for a tuple.
* :class:`AIRuntime` — the orchestrator that runs a candidate chain.

Deliberate non-goals
--------------------
This module performs **no** HTTP itself. The provider adapters live where the
transport already lives, and are injected. That keeps this module importable
with no network, no FastAPI, and no secrets, so it is testable offline and
reusable from a future MCP server or CLI.

Secrets are never read, stored, logged, or returned here. The module handles
only public model identifiers, booleans and classified error labels.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from .model_policy import (
    MODEL_POLICY_VERSION,
    resolve_answer_mode_models,
    resolve_model_role_policy,
)

AI_RUNTIME_VERSION = "2026-08-ai-runtime-v1"


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


class AIErrorType(str, Enum):
    """Every way a provider call can fail, named once.

    The distinctions here are the ones that change behaviour. Collapsing any
    two of them produces a real bug: treating a bad API key as a transient
    outage burns the whole candidate chain against a broken account, and
    treating a safety rejection as "provider offline" tells the user something
    false about why they did not get an answer.
    """

    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    INVALID_PROVIDER_CREDENTIALS = "invalid_provider_credentials"
    INVALID_MODEL = "invalid_model"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMITED = "rate_limited"
    PROVIDER_OVERLOADED = "provider_overloaded"
    TIMEOUT = "timeout"
    NETWORK_FAILURE = "network_failure"
    MALFORMED_PROVIDER_RESPONSE = "malformed_provider_response"
    EMPTY_COMPLETION = "empty_completion"
    SAFETY_REJECTION = "safety_rejection"
    INVALID_REQUEST = "invalid_request"
    ALL_CANDIDATES_COOLING_DOWN = "all_candidates_cooling_down"
    UNKNOWN_PROVIDER_ERROR = "unknown_provider_error"


#: Failures that are transient and NOT specific to one model. Retrying the
#: same model later is reasonable, so the model is put on cooldown and the
#: chain advances.
RETRYABLE_ERROR_TYPES = frozenset({
    AIErrorType.RATE_LIMITED,
    AIErrorType.PROVIDER_OVERLOADED,
    AIErrorType.TIMEOUT,
    AIErrorType.NETWORK_FAILURE,
    AIErrorType.EMPTY_COMPLETION,
    AIErrorType.MALFORMED_PROVIDER_RESPONSE,
})

#: Failures tied to ONE model id (unknown slug, or a free model with no
#: capacity). A cooldown would not help, but one bad candidate must never sink
#: an otherwise answerable request — so skip to the next candidate.
PER_MODEL_SKIP_ERROR_TYPES = frozenset({
    AIErrorType.INVALID_MODEL,
    AIErrorType.MODEL_UNAVAILABLE,
})

#: Failures that affect every candidate equally. Stop immediately: iterating
#: the chain against a broken account or a malformed request wastes the user's
#: time and hides the real cause from the operator.
FATAL_ERROR_TYPES = frozenset({
    AIErrorType.PROVIDER_NOT_CONFIGURED,
    AIErrorType.INVALID_PROVIDER_CREDENTIALS,
    AIErrorType.INVALID_REQUEST,
    AIErrorType.SAFETY_REJECTION,
})


def is_retryable(error_type: Any) -> bool:
    return _coerce_error_type(error_type) in RETRYABLE_ERROR_TYPES


def should_skip_model(error_type: Any) -> bool:
    return _coerce_error_type(error_type) in PER_MODEL_SKIP_ERROR_TYPES


def is_fatal(error_type: Any) -> bool:
    return _coerce_error_type(error_type) in FATAL_ERROR_TYPES


#: Public labels the /api/ask contract has always used. The taxonomy above is
#: finer-grained than the wire format, so several entries collapse onto one
#: legacy label. Kept as an explicit map (rather than renaming the wire format)
#: because these strings reach the frontend's error cards and existing clients:
#: widening the taxonomy must not be an API break.
LEGACY_ERROR_LABELS: Dict[AIErrorType, str] = {
    AIErrorType.PROVIDER_NOT_CONFIGURED: "provider_not_configured",
    AIErrorType.INVALID_PROVIDER_CREDENTIALS: "invalid_provider_config",
    AIErrorType.INVALID_MODEL: "model_not_found",
    AIErrorType.MODEL_UNAVAILABLE: "model_not_found",
    AIErrorType.RATE_LIMITED: "rate_limited",
    AIErrorType.PROVIDER_OVERLOADED: "upstream_unavailable",
    AIErrorType.TIMEOUT: "upstream_unavailable",
    AIErrorType.NETWORK_FAILURE: "upstream_unavailable",
    AIErrorType.MALFORMED_PROVIDER_RESPONSE: "invalid_request",
    AIErrorType.EMPTY_COMPLETION: "upstream_unavailable",
    AIErrorType.SAFETY_REJECTION: "policy_or_safety_rejection",
    AIErrorType.INVALID_REQUEST: "invalid_request",
    AIErrorType.ALL_CANDIDATES_COOLING_DOWN: "all_candidates_cooling_down",
    AIErrorType.UNKNOWN_PROVIDER_ERROR: "unknown_provider_error",
}


def legacy_label(error_type: Any) -> str:
    """The wire-format label for a taxonomy entry."""
    coerced = _coerce_error_type(error_type)
    if coerced is None:
        return AIErrorType.UNKNOWN_PROVIDER_ERROR.value
    return LEGACY_ERROR_LABELS.get(coerced, coerced.value)


def _coerce_error_type(value: Any) -> Optional[AIErrorType]:
    if isinstance(value, AIErrorType):
        return value
    try:
        return AIErrorType(str(value or "").strip().lower())
    except ValueError:
        return None


def classify_provider_error(
    status: Optional[int] = None,
    message: Optional[str] = None,
    error_code: Optional[str] = None,
) -> AIErrorType:
    """Map an upstream failure onto the taxonomy. Never sees or returns secrets.

    ``status`` is the upstream HTTP status when known, ``message`` is already
    sanitized provider text, ``error_code`` is Visable's own internal marker
    (e.g. ``openrouter_empty_completion``). All three are optional because
    different transports surface different amounts of detail.
    """
    msg = (message or "").lower()
    code = (error_code or "").strip().lower()
    try:
        status_int = int(status) if status is not None else None
    except (TypeError, ValueError):
        status_int = None

    # Internal markers are the most precise signal available, so they win.
    if code.endswith("_not_configured") or code in {"no_llm_provider_configured", "coach_no_provider"}:
        return AIErrorType.PROVIDER_NOT_CONFIGURED
    if code.endswith("_empty_completion"):
        return AIErrorType.EMPTY_COMPLETION
    if code.endswith("_bad_response") or code.endswith("_unparseable"):
        return AIErrorType.MALFORMED_PROVIDER_RESPONSE
    if code.endswith("_timeout"):
        return AIErrorType.TIMEOUT
    if code.endswith("_network_error"):
        return AIErrorType.NETWORK_FAILURE

    if (
        status_int == 429
        or "rate limit" in msg
        or "rate-limit" in msg
        or "too many requests" in msg
        or "quota" in msg
        or "429" in msg
    ):
        return AIErrorType.RATE_LIMITED

    # Auth is checked BEFORE the generic 5xx bucket: a 403 from an expired key
    # must never be retried across the whole chain as if it were capacity.
    if (
        status_int in (401, 403)
        or "invalid api key" in msg
        or "unauthorized" in msg
        or "no auth credentials" in msg
        or "authentication" in msg
    ):
        return AIErrorType.INVALID_PROVIDER_CREDENTIALS

    if status_int in (502, 503) or "no healthy upstream" in msg or "no instances available" in msg \
            or "overloaded" in msg or "temporarily unavailable" in msg \
            or "service unavailable" in msg or "bad gateway" in msg:
        return AIErrorType.PROVIDER_OVERLOADED
    if status_int == 504 or "timeout" in msg or "timed out" in msg:
        return AIErrorType.TIMEOUT

    if status_int == 404 or "not found" in msg or "unknown model" in msg or "not a valid model" in msg:
        return AIErrorType.INVALID_MODEL
    if "no endpoints" in msg or "no allowed providers" in msg or "no endpoints found" in msg:
        return AIErrorType.MODEL_UNAVAILABLE

    if (
        status_int == 451
        or "moderation" in msg
        or "flagged" in msg
        or "safety" in msg
        or "content policy" in msg
        or "content filter" in msg
    ):
        return AIErrorType.SAFETY_REJECTION

    if status_int == 400 or "bad request" in msg or "invalid request" in msg or "validation" in msg:
        return AIErrorType.INVALID_REQUEST

    if "connect" in msg or "dns" in msg or "network" in msg or "reset by peer" in msg:
        return AIErrorType.NETWORK_FAILURE

    if status_int is not None and status_int >= 500:
        return AIErrorType.PROVIDER_OVERLOADED
    return AIErrorType.UNKNOWN_PROVIDER_ERROR


# ---------------------------------------------------------------------------
# Task roles
# ---------------------------------------------------------------------------


class TaskRole(str, Enum):
    """What a feature needs, expressed as a capability rather than a model id.

    A feature asking for ``TaskRole.FINAL_ANSWER`` keeps working when the
    catalog changes underneath it; a feature that hardcodes a model string does
    not. Scattered model strings are precisely how one deprecated slug used to
    take a whole feature down.
    """

    ROUTER = "router"
    TRANSLATOR = "translator"
    FACT_EXTRACTOR = "fact_extractor"
    FINAL_ANSWER = "final_answer"
    FAST_FINAL_ANSWER = "fast_final_answer"
    LEGAL_SYNTHESIS = "legal_synthesis"
    VERIFIER = "verifier"
    NATIONALITY_COACH = "nationality_coach"
    EMPLOYMENT_INTERPRETER = "employment_interpreter"
    ENFORCEMENT_EXPLAINER = "enforcement_explainer"
    ENFORCEMENT_STRUCTURED = "enforcement_structured"
    SEARCH_OVERVIEW = "search_overview"


def resolve_task_models(role: Any) -> Dict[str, Any]:
    """Resolve a task role to an ordered candidate chain of public model ids.

    Every role resolves through :mod:`services.model_policy`, so the deploy-time
    environment overrides that policy honours apply uniformly instead of only
    to whichever feature happened to read the same env var.
    """
    try:
        task = role if isinstance(role, TaskRole) else TaskRole(str(role or "").strip().lower())
    except ValueError:
        task = TaskRole.FINAL_ANSWER

    policy = resolve_model_role_policy()
    basic = resolve_answer_mode_models("basic")
    fast = resolve_answer_mode_models("fast")

    def chain(*models: Any) -> List[str]:
        out: List[str] = []
        seen = set()
        for item in models:
            for value in (item if isinstance(item, (list, tuple)) else [item]):
                clean = str(value or "").strip()
                if clean and clean not in seen:
                    seen.add(clean)
                    out.append(clean)
        return out

    # Short, cheap tasks lead with a small model and fall back to the basic
    # chain: a structured extraction that cannot run at all is worse for the
    # user than one that runs on a larger model.
    if task in (TaskRole.ROUTER, TaskRole.TRANSLATOR):
        candidates = chain(policy["router_model"], policy["translation_model"], fast["candidates"])
    elif task in (TaskRole.FACT_EXTRACTOR, TaskRole.EMPLOYMENT_INTERPRETER):
        candidates = chain(fast["candidates"], basic["candidates"])
    elif task == TaskRole.VERIFIER:
        candidates = chain(policy["verifier_model"], basic["candidates"])
    elif task == TaskRole.ENFORCEMENT_STRUCTURED:
        # Extraction/prediction already runs behind deterministic legal rules and
        # strict typed validation. Lead with the low-latency structured-output
        # chain; keep the verifier model as the final deep fallback without
        # paying the general 405B Basic-answer primary on every request.
        candidates = chain(fast["candidates"], policy["verifier_model"])
    elif task == TaskRole.FAST_FINAL_ANSWER:
        candidates = chain(fast["candidates"])
    elif task in (TaskRole.SEARCH_OVERVIEW, TaskRole.NATIONALITY_COACH):
        candidates = chain(fast["candidates"], basic["candidates"])
    else:
        # FINAL_ANSWER, LEGAL_SYNTHESIS, ENFORCEMENT_EXPLAINER — the answers a
        # user acts on. These get the full basic chain.
        candidates = chain(basic["candidates"])

    return {
        "task_role": task.value,
        "primary": candidates[0] if candidates else "",
        "candidates": candidates,
        "policy_version": MODEL_POLICY_VERSION,
        "runtime_version": AI_RUNTIME_VERSION,
    }


# ---------------------------------------------------------------------------
# Cooldown / circuit breaker
# ---------------------------------------------------------------------------


class ModelCooldownRegistry:
    """In-memory circuit breaker keyed by public model id.

    A model that just returned 429 will almost certainly return 429 again on
    the next request a second later. Recording the failure lets later requests
    skip it and reach a working candidate immediately, instead of paying the
    same timeout again. In-memory by design: it is a latency optimization, not
    state worth persisting, and a restart clearing it is harmless.
    """

    def __init__(self, cooldown_seconds: float = 300.0) -> None:
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._failed_at: Dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return self.cooldown_seconds > 0

    def mark(self, model: str, now: Optional[float] = None) -> None:
        if not model or not self.enabled:
            return
        self._failed_at[model] = time.time() if now is None else now

    def cooling_down(self, now: Optional[float] = None) -> List[str]:
        if not self.enabled:
            return []
        ts = time.time() if now is None else now
        for model in [m for m, at in self._failed_at.items() if ts - at >= self.cooldown_seconds]:
            self._failed_at.pop(model, None)
        return [m for m, at in self._failed_at.items() if ts - at < self.cooldown_seconds]

    def is_cooling(self, model: str, now: Optional[float] = None) -> bool:
        return model in set(self.cooling_down(now))

    def clear(self) -> None:
        self._failed_at.clear()

    def metadata(self) -> Dict[str, Any]:
        return {
            "cooling_down_models": self.cooling_down(),
            "model_cooldown_seconds": self.cooldown_seconds,
            "cooldown_enabled": self.enabled,
        }


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


@dataclass
class AIResult:
    """The outcome of a completion attempt across a candidate chain.

    Deliberately a dataclass rather than a bare dict. The defect this runtime
    was built after was a caller writing ``text, meta = await complete(...)``
    against a 16-key dict: Python happily unpacked the KEYS and raised
    ValueError, which a broad ``except`` turned into a permanent fake outage.
    A dataclass raises ``TypeError: cannot unpack non-iterable AIResult`` on
    the same mistake — immediate and unmissable.
    """

    ok: bool
    answer: Optional[str] = None
    provider: str = ""
    task_role: str = ""
    primary_model: Optional[str] = None
    final_model: Optional[str] = None
    requested_model: Optional[str] = None
    model_candidates: List[str] = field(default_factory=list)
    attempted_models: List[str] = field(default_factory=list)
    skipped_models_due_to_cooldown: List[str] = field(default_factory=list)
    cooling_down_models: List[str] = field(default_factory=list)
    model_cooldown_seconds: float = 0.0
    cooldown_enabled: bool = False
    model_fallback_used: bool = False
    error_type: Optional[str] = None
    retryable: bool = False
    all_candidates_failed: bool = False
    upstream_statuses: List[int] = field(default_factory=list)
    latency_ms: int = 0

    @property
    def text(self) -> str:
        return self.answer or ""

    def telemetry(self) -> Dict[str, Any]:
        """Privacy-safe observability fields. Never the prompt, never a key."""
        return {
            "task_role": self.task_role,
            "provider": self.provider,
            "selected_model": self.final_model,
            "attempted_models": list(self.attempted_models),
            "fallback_used": self.model_fallback_used,
            "error_type": self.error_type,
            "latency_ms": self.latency_ms,
            "runtime_version": AI_RUNTIME_VERSION,
        }

    def to_legacy_dict(self) -> Dict[str, Any]:
        """The historical `_openrouter_complete_with_candidates` result shape.

        Kept so existing callers and their tests keep working unchanged while
        features migrate one at a time. New code should use the dataclass.
        """
        return {
            "ok": self.ok,
            "answer": self.answer,
            "primary_model": self.primary_model,
            "requested_model": self.requested_model,
            "model_candidates": list(self.model_candidates),
            "attempted_models": list(self.attempted_models),
            "skipped_models_due_to_cooldown": list(self.skipped_models_due_to_cooldown),
            "cooling_down_models": list(self.cooling_down_models),
            "model_cooldown_seconds": self.model_cooldown_seconds,
            "cooldown_enabled": self.cooldown_enabled,
            "final_model": self.final_model,
            "model_fallback_used": self.model_fallback_used,
            "provider_error_type": self.error_type,
            "upstream_statuses": list(self.upstream_statuses),
            "retryable_provider_error": self.retryable,
            "all_candidates_failed": self.all_candidates_failed,
        }

    @classmethod
    def from_legacy_dict(cls, data: Dict[str, Any], *, provider: str = "", task_role: str = "") -> "AIResult":
        data = data if isinstance(data, dict) else {}
        return cls(
            ok=bool(data.get("ok")),
            answer=data.get("answer"),
            provider=provider,
            task_role=task_role,
            primary_model=data.get("primary_model"),
            final_model=data.get("final_model"),
            requested_model=data.get("requested_model"),
            model_candidates=list(data.get("model_candidates") or []),
            attempted_models=list(data.get("attempted_models") or []),
            skipped_models_due_to_cooldown=list(data.get("skipped_models_due_to_cooldown") or []),
            cooling_down_models=list(data.get("cooling_down_models") or []),
            model_cooldown_seconds=float(data.get("model_cooldown_seconds") or 0.0),
            cooldown_enabled=bool(data.get("cooldown_enabled")),
            model_fallback_used=bool(data.get("model_fallback_used")),
            error_type=data.get("provider_error_type"),
            retryable=bool(data.get("retryable_provider_error")),
            all_candidates_failed=bool(data.get("all_candidates_failed")),
            upstream_statuses=list(data.get("upstream_statuses") or []),
        )


class AIError(Exception):
    """A classified provider failure. Carries no secret and no raw body."""

    def __init__(self, error_type: AIErrorType, message: str = "", *, status: Optional[int] = None):
        super().__init__(message or error_type.value)
        self.error_type = error_type
        self.public_message = message or error_type.value
        self.status = status

    def as_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "message": self.public_message,
            "status": self.status,
            "retryable": is_retryable(self.error_type),
        }


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

#: A provider adapter: ``(prompt, model, max_tokens) -> completion text``.
#: It raises ``AIError`` on failure. Injected rather than imported so this
#: module stays free of transport, FastAPI and secrets.
CompletionAdapter = Callable[[str, str, Optional[int]], Awaitable[str]]


class AIRuntime:
    """Runs a task role's candidate chain against one provider adapter.

    The orchestration rules live here once, so every feature gets identical
    behaviour: cooldown-aware candidate selection, retry on transient failure,
    skip on a model-specific failure, stop immediately on an account-wide one.
    """

    def __init__(
        self,
        *,
        adapter: CompletionAdapter,
        provider_name: str = "openrouter",
        cooldowns: Optional[ModelCooldownRegistry] = None,
    ) -> None:
        self._adapter = adapter
        self.provider_name = provider_name
        self.cooldowns = cooldowns or ModelCooldownRegistry()

    async def complete(
        self,
        prompt: str,
        *,
        role: Any = TaskRole.FINAL_ANSWER,
        candidates: Optional[Sequence[str]] = None,
        requested_model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> AIResult:
        plan = resolve_task_models(role)
        # `candidates=[]` means "this deployment resolved no models", which is a
        # configuration failure to report — not an invitation to silently
        # substitute the policy chain. Only an omitted argument (None) does that.
        chain: List[str] = list(plan["candidates"]) if candidates is None else list(candidates)
        if requested_model:
            chain = [requested_model, *[m for m in chain if m != requested_model]]
        if not chain:
            return AIResult(
                ok=False, provider=self.provider_name, task_role=plan["task_role"],
                error_type=AIErrorType.PROVIDER_NOT_CONFIGURED.value,
                all_candidates_failed=True,
            )

        started = time.monotonic()
        cooling = set(self.cooldowns.cooling_down())
        runnable = [m for m in chain if m not in cooling]
        skipped = [m for m in chain if m in cooling]

        base = dict(
            provider=self.provider_name,
            task_role=plan["task_role"],
            primary_model=chain[0],
            requested_model=requested_model,
            model_candidates=chain,
            skipped_models_due_to_cooldown=skipped,
            model_cooldown_seconds=self.cooldowns.cooldown_seconds,
            cooldown_enabled=self.cooldowns.enabled,
        )

        if not runnable:
            # Every candidate is cooling down. Hammering them would add latency
            # and no answer; the caller uses its deterministic fallback.
            return AIResult(
                ok=False,
                error_type=AIErrorType.ALL_CANDIDATES_COOLING_DOWN.value,
                retryable=True, all_candidates_failed=True,
                cooling_down_models=self.cooldowns.cooling_down(),
                latency_ms=int((time.monotonic() - started) * 1000),
                **base,
            )

        attempted: List[str] = []
        statuses: List[int] = []
        last_error: Optional[AIErrorType] = None

        for model in runnable:
            attempted.append(model)
            try:
                answer = await self._adapter(prompt, model, max_tokens)
            except AIError as exc:
                last_error = exc.error_type
                if exc.status is not None:
                    statuses.append(int(exc.status))
                if is_retryable(exc.error_type):
                    self.cooldowns.mark(model)
                    continue
                if should_skip_model(exc.error_type):
                    continue
                break  # account-wide: credentials, bad request, safety
            return AIResult(
                ok=True, answer=answer, final_model=model,
                attempted_models=attempted,
                model_fallback_used=model != chain[0],
                error_type=last_error.value if last_error else None,
                upstream_statuses=statuses,
                cooling_down_models=self.cooldowns.cooling_down(),
                latency_ms=int((time.monotonic() - started) * 1000),
                **base,
            )

        return AIResult(
            ok=False,
            attempted_models=attempted,
            model_fallback_used=len(attempted) > 1 or bool(skipped),
            error_type=(last_error or AIErrorType.UNKNOWN_PROVIDER_ERROR).value,
            retryable=is_retryable(last_error) if last_error else False,
            all_candidates_failed=len(attempted) + len(skipped) == len(chain),
            upstream_statuses=statuses,
            cooling_down_models=self.cooldowns.cooling_down(),
            latency_ms=int((time.monotonic() - started) * 1000),
            **base,
        )


# ---------------------------------------------------------------------------
# Provider configuration (names only — never values)
# ---------------------------------------------------------------------------

#: The only environment variable names that may carry provider credentials.
#: The architecture guard asserts nothing outside the approved adapter modules
#: reads them, so a new feature cannot quietly grow its own provider routing.
PROVIDER_CREDENTIAL_ENV_NAMES = (
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "NVIDIA_API_KEY",
)


def provider_configuration() -> Dict[str, Any]:
    """Non-secret readiness snapshot: which providers *could* answer.

    Returns booleans and public model ids only. This is what /health and the
    AI readiness endpoint report; it never touches a credential value.
    """
    openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))
    groq = bool(os.environ.get("GROQ_API_KEY"))
    groq_fallback = (os.environ.get("ALLOW_GROQ_FALLBACK", "false") or "false").strip().lower() in {
        "1", "true", "yes", "on",
    }
    return {
        "runtime_version": AI_RUNTIME_VERSION,
        "policy_version": MODEL_POLICY_VERSION,
        "providers": {
            "openrouter": {"configured": openrouter},
            "groq": {"configured": groq, "fallback_allowed": groq_fallback},
        },
        "active_provider": (
            "openrouter" if openrouter else ("groq" if (groq and groq_fallback) else "none")
        ),
        "task_roles": {
            role.value: resolve_task_models(role)["candidates"] for role in TaskRole
        },
    }
