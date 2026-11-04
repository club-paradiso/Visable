"""Service info and health routes: /, /health, /api/health/ai.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict
from fastapi import APIRouter


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get("/")
    async def root() -> Dict[str, Any]:
        """Service-info page for humans who hit the bare backend URL.

        The Visable backend is API-only; the human-facing frontend is
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
            "frontend": pb.FRONTEND_URL or None,
        }


    @router.get("/health")
    async def health() -> Dict[str, Any]:
        llm = pb._resolve_llm_config()
        candidates = pb.OPENROUTER_MODEL_CANDIDATES
        candidate_warnings = pb._validate_model_candidates(candidates)
        if llm.get("groq_fallback_allowed"):
            candidate_warnings = [*candidate_warnings, "PROVIDER_FAMILY_FALLBACK_ENABLED"]
        # Make deploy-time model configuration visible without exposing secrets.
        # Presence is distinct from activity: stale values are ignored unless the
        # independent opt-in flag is enabled.
        _model_env_present = bool((pb.os.environ.get("OPENROUTER_MODEL") or "").strip())
        _candidates_env_present = bool((pb.os.environ.get("OPENROUTER_MODEL_CANDIDATES") or "").strip())
        _model_env_override = pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED and _model_env_present
        _candidates_env_override = pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED and _candidates_env_present
        if _model_env_override and pb.OPENROUTER_MODEL != pb._DEFAULT_OPENROUTER_MODEL:
            candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_ENV_OVERRIDE"]
        if _candidates_env_override and candidates != list(pb._DEFAULT_OPENROUTER_MODEL_CANDIDATES):
            candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE"]
        if _model_env_present and not pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED:
            candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_ENV_OVERRIDE_IGNORED"]
        if _candidates_env_present and not pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED:
            candidate_warnings = [*candidate_warnings, "OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE_IGNORED"]
        # Non-secret Open Law API posture. NEVER exposes LAW_API_OC / LAW_API_KEY
        # values — only booleans, the resolved mode, and which env var supplied the
        # credential. Computed live so LAW_API_OC-only deployments report correctly.
        try:
            law_cfg = pb.load_grounding_config()
            law_mode, law_effective_mode, law_grounding_active = pb._law_grounding_runtime_state(law_cfg)
            law_api_status: Dict[str, Any] = {
                "law_api_configured": law_cfg.law_api_configured,
                "law_api_oc_configured": law_cfg.law_api_oc_configured,
                "law_api_key_fallback_configured": law_cfg.law_api_key_fallback_configured,
                "law_api_credential_source": law_cfg.law_api_credential_source,
            }
        except Exception:  # pragma: no cover - defensive
            law_mode = (pb.os.environ.get("LAW_GROUNDING_MODE") or "enabled").strip().lower()
            law_effective_mode = law_mode if pb.LAW_API_KEY else ("disabled" if law_mode == "enabled" else law_mode)
            law_grounding_active = law_effective_mode in {"audit", "enabled"}
            law_api_status = {
                "law_api_configured": bool(pb.LAW_API_KEY),
                "law_api_oc_configured": False,
                "law_api_key_fallback_configured": bool(pb.LAW_API_KEY),
                "law_api_credential_source": "LAW_API_KEY" if pb.LAW_API_KEY else "",
            }
        provider_status = {
            "openrouter": {"configured": bool(pb.OPENROUTER_API_KEY), "enabled": llm["provider"] == "openrouter"},
            "groq": {"configured": bool(pb.GROQ_API_KEY), "fallback_allowed": pb.ALLOW_GROQ_FALLBACK},
            "law_grounding": {"mode": law_mode, "effective_mode": law_effective_mode},
            "legal_evidence": {"configured": bool(law_api_status["law_api_configured"])},
            "nvidia_nim": pb.NvidiaNimProvider().health_check(),
        }
        return {
            "status": "ok",
            "service": "paradiso-backend",
            "version": pb.app.version,
            # Which commit is actually serving. Lets a post-deploy check wait for
            # its own commit instead of passing against the previous deploy.
            "build": pb._deployed_build_metadata(),
            "providers": pb._providers_configured(),
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
                "primary_model": pb.OPENROUTER_MODEL,
                "model_candidates": candidates,
                # Committed code-policy default + whether an env var is overriding it,
                # so "the answer model did not update after merge" is self-diagnosing:
                # if model_env_override is true and primary_model != code_default_model,
                # a deploy env var (e.g. a stale Railway OPENROUTER_MODEL) is pinning it.
                "code_default_model": pb._DEFAULT_OPENROUTER_MODEL,
                "code_default_model_candidates": list(pb._DEFAULT_OPENROUTER_MODEL_CANDIDATES),
                "model_env_override": _model_env_override or _candidates_env_override,
                "model_env_override_present": _model_env_present or _candidates_env_present,
                "model_env_override_ignored": (
                    (_model_env_present or _candidates_env_present)
                    and not pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED
                ),
                "model_env_overrides_allowed": pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED,
                "provider_family_fallback_allowed": llm["groq_fallback_allowed"],
                "candidate_warnings": candidate_warnings,
                **pb._openrouter_cooldown_metadata(),
                "chain_budget_seconds": pb.OPENROUTER_CHAIN_BUDGET_SECONDS,
                "fallback_reserve_seconds": pb.OPENROUTER_FALLBACK_RESERVE_SECONDS,
                "ollama_fallback_enabled": pb.ENABLE_OLLAMA_FALLBACK,
                "ollama_model": pb.OLLAMA_MODEL,
                "ollama_configured": bool(pb.ENABLE_OLLAMA_FALLBACK and pb.OLLAMA_BASE_URL),
                "ollama_timeout_seconds": pb.OLLAMA_TIMEOUT_SECONDS,
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
            # off / token / open — never the token itself.
            "client_diagnostics_mode": pb._client_diagnostics_mode(),
        }


    @router.get("/api/health/ai")
    async def health_ai() -> Dict[str, Any]:
        """AI readiness — what an operator needs to answer "is the AI actually up?".

        /health answers "is the web server alive?". That is a different question,
        and conflating them is how a deployment can look healthy while every AI
        feature is failing. This endpoint reports readiness per feature.

        It performs NO provider calls: a health probe that costs a completion is a
        health probe nobody runs often enough to be useful, and it would bill the
        account on every check. Everything here is configuration and registry state,
        so it is cheap enough to poll.

        Readiness is NOT proof of a working answer. `liveVerification` says so
        explicitly, and names the smoke script that can actually prove it — so this
        endpoint can never be mistaken for the live check.

        Non-secret by construction: booleans, public model ids, classified states.
        No credential value, no authorization header, no raw provider body.
        """
        runtime = pb._ai_runtime.provider_configuration()
        llm = pb._resolve_llm_config()

        try:
            law_cfg = pb.load_grounding_config()
            law_mode, law_effective_mode, law_active = pb._law_grounding_runtime_state(law_cfg)
            law_configured = law_cfg.law_api_configured
            law_total_budget = law_cfg.total_budget_seconds
        except Exception:  # pragma: no cover - defensive
            law_mode = (pb.os.environ.get("LAW_GROUNDING_MODE") or "enabled").strip().lower()
            law_effective_mode, law_active, law_configured = "unknown", False, bool(pb.LAW_API_KEY)
            law_total_budget = 0.0

        try:
            manual_summary = pb._manual_registry.registry_summary()
            approved_manuals = int(manual_summary["approval_counts"].get("approved", 0))
            composition = pb._manual_search.index_composition()
            index_available = bool(composition.get("available"))
            indexed_direct = int(composition.get("directEvidenceChunks") or 0)
            indexed_total = int(composition.get("totalChunks") or 0)
        except Exception:  # pragma: no cover - defensive
            approved_manuals, index_available = 0, False
            indexed_direct, indexed_total, composition = 0, 0, {}

        # Three separate facts, and only all three together mean approved manual
        # evidence can actually back an answer:
        #   1. an edition is human-approved in the registry,
        #   2. the FTS index is built,
        #   3. that index CONTAINS chunks from the approved edition.
        #
        # (3) is the one an "is the file there?" probe misses. The index can be
        # complete and healthy while holding zero direct-evidence chunks, because
        # the approved editions have extracted full text but no sectioned source
        # for the builder to read. Reporting ready on (1) and (2) alone would be
        # the same class of false green this endpoint exists to prevent.
        manual_ready = bool(approved_manuals) and index_available and indexed_direct > 0
        manual_blocker = ""
        if not approved_manuals:
            manual_blocker = "no manual edition has been human-approved for direct evidence"
        elif not index_available:
            manual_blocker = (
                "approved manual editions exist but no FTS index is present on this "
                "deployment. The builder (scripts/build_manual_search_index.py) lives at "
                "the repository root, which is NOT in the backend build context — the "
                "Railway service sets Root Directory = backend — so it cannot be invoked "
                "during the build. Ship a prebuilt index as "
                "backend/data/manual_search_index.sqlite3, or point "
                "MANUAL_SEARCH_INDEX_PATH at a mounted volume. Searched: "
                + ", ".join(pb._document_labels.display_path(c)
                            for c in pb._manual_search.candidate_index_paths())
            )
        elif indexed_direct == 0:
            manual_blocker = (
                f"the index holds {indexed_total} chunks but 0 from an approved edition. "
                "The approved editions are extracted to full text only; they have no "
                "*_sections.json, and scripts/build_manual_search_index.py SECTION_SOURCES "
                "does not list them. Sectioning an approved manual produces direct legal "
                "evidence and needs the manual-sourcing owner plus a human review pass — "
                "it is not a build-configuration fix."
            )

        provider_ready = bool(pb.OPENROUTER_API_KEY) or bool(pb.GROQ_API_KEY and pb.ALLOW_GROQ_FALLBACK)

        # Privacy-safe deploy truth: report only whether a variable exists. Never
        # return credential values, headers, or raw provider responses.
        def env_present(name: str) -> bool:
            return bool((pb.os.environ.get(name) or "").strip())

        environment_overrides = {
            "provider": {
                "OPENROUTER_API_KEY": env_present("OPENROUTER_API_KEY"),
                "GROQ_API_KEY": env_present("GROQ_API_KEY"),
                "ALLOW_GROQ_FALLBACK": env_present("ALLOW_GROQ_FALLBACK"),
            },
            "model": {
                "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES": env_present("OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES"),
                "OPENROUTER_MODEL": env_present("OPENROUTER_MODEL"),
                "OPENROUTER_MODEL_CANDIDATES": env_present("OPENROUTER_MODEL_CANDIDATES"),
                "OPENROUTER_FAST_MODEL": env_present("OPENROUTER_FAST_MODEL"),
                "OPENROUTER_FAST_MODEL_CANDIDATES": env_present("OPENROUTER_FAST_MODEL_CANDIDATES"),
            },
            "timeouts": {
                "OPENROUTER_TIMEOUT_SECONDS": env_present("OPENROUTER_TIMEOUT_SECONDS"),
                "OPENROUTER_CHAIN_BUDGET_SECONDS": env_present("OPENROUTER_CHAIN_BUDGET_SECONDS"),
                "OPENROUTER_FALLBACK_RESERVE_SECONDS": env_present("OPENROUTER_FALLBACK_RESERVE_SECONDS"),
                "OPENROUTER_MODEL_COOLDOWN_SECONDS": env_present("OPENROUTER_MODEL_COOLDOWN_SECONDS"),
            },
            "law": {
                "LAW_API_OC": env_present("LAW_API_OC"),
                "LAW_OC": env_present("LAW_OC"),
                "OPEN_LAW_ID": env_present("OPEN_LAW_ID"),
                "LAW_API_KEY": env_present("LAW_API_KEY"),
                "LAW_GROUNDING_MODE": env_present("LAW_GROUNDING_MODE"),
                "LAW_GROUNDING_TOTAL_BUDGET_SECONDS": env_present("LAW_GROUNDING_TOTAL_BUDGET_SECONDS"),
            },
            "manual": {
                "MANUAL_SEARCH_INDEX_PATH": env_present("MANUAL_SEARCH_INDEX_PATH"),
            },
        }

        candidate_warnings = pb._validate_model_candidates(pb.OPENROUTER_MODEL_CANDIDATES)
        if (
            pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED
            and env_present("OPENROUTER_MODEL")
            and pb.OPENROUTER_MODEL != pb._DEFAULT_OPENROUTER_MODEL
        ):
            candidate_warnings.append("OPENROUTER_MODEL_ENV_OVERRIDE")
        if (
            pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED
            and env_present("OPENROUTER_MODEL_CANDIDATES")
            and pb.OPENROUTER_MODEL_CANDIDATES != list(pb._DEFAULT_OPENROUTER_MODEL_CANDIDATES)
        ):
            candidate_warnings.append("OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE")
        if not pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED and env_present("OPENROUTER_MODEL"):
            candidate_warnings.append("OPENROUTER_MODEL_ENV_OVERRIDE_IGNORED")
        if not pb.OPENROUTER_MODEL_ENV_OVERRIDES_ALLOWED and env_present("OPENROUTER_MODEL_CANDIDATES"):
            candidate_warnings.append("OPENROUTER_MODEL_CANDIDATES_ENV_OVERRIDE_IGNORED")

        def feature(name: str, ready: bool, *, blocker: str = "",
                    degrades_to: str = "") -> Dict[str, Any]:
            return {"feature": name, "ready": ready, "blocker": blocker,
                    "degradesTo": degrades_to}

        no_provider = "" if provider_ready else "no LLM provider is configured"
        features = [
            feature("waymaker_ask", provider_ready, blocker=no_provider,
                    degrades_to="deterministic source-grounded preparation note"),
            feature("unified_search_ai_overview", provider_ready, blocker=no_provider,
                    degrades_to="deterministic organic search results (always available)"),
            feature("employment_interpret", provider_ready, blocker=no_provider,
                    degrades_to="guided deterministic employment analyzer"),
            feature("nationality_coach", bool(pb.OPENROUTER_API_KEY or pb.GROQ_API_KEY),
                    blocker="" if (pb.OPENROUTER_API_KEY or pb.GROQ_API_KEY) else no_provider,
                    degrades_to="local heuristic practice feedback"),
            feature("legal_research", True,
                    degrades_to="deterministic retrieval without LLM synthesis"),
            feature("enforcement_intelligence", True,
                    degrades_to="deterministic statutory baseline without AI explanation"),
        ]

        return {
            "status": "ok",
            "service": "visable-backend",
            "aiReady": provider_ready,
            "runtimeVersion": runtime["runtime_version"],
            "modelPolicyVersion": runtime["policy_version"],
            "toolLayerVersion": pb._immigration_tools.TOOL_LAYER_VERSION,
            "providers": runtime["providers"],
            "activeProvider": runtime["active_provider"],
            "answerTiers": {
                mode: pb.resolve_answer_mode_models(mode) for mode in ("fast", "basic", "pro")
            },
            "taskRoleModels": runtime["task_roles"],
            "cooldown": {
                **pb._MODEL_COOLDOWNS.metadata(),
                "chainBudgetSeconds": pb.OPENROUTER_CHAIN_BUDGET_SECONDS,
                "fallbackReserveSeconds": pb.OPENROUTER_FALLBACK_RESERVE_SECONDS,
            },
            "environmentOverrides": environment_overrides,
            "grounding": {
                "law": {
                    "configured": law_configured,
                    "mode": law_mode,
                    "effectiveMode": law_effective_mode,
                    "active": law_active,
                    "totalBudgetSeconds": law_total_budget,
                    # Audit posture is a real, deliberate state — not a failure —
                    # but citations retrieved under it are never marked verified.
                    "citationsTrustworthy": law_effective_mode == "enabled" and law_configured,
                },
                "manual": {
                    "approvedEditions": approved_manuals,
                    "indexAvailable": index_available,
                    # What the index actually holds, so "built" is never mistaken
                    # for "approved evidence is searchable".
                    "indexedChunks": indexed_total,
                    "indexedDirectEvidenceChunks": indexed_direct,
                    "indexedByApprovalState": composition.get("byApprovalState", {}),
                    "ready": manual_ready,
                    "blocker": manual_blocker,
                },
                # The document registry is a packaging fact, not a model fact, but
                # it belongs here for the same reason as the index: it is loaded
                # from disk, and a deploy layout that omits it degrades answers
                # silently. Review on #582 found exactly that — the resolver was
                # correct and the file was not in the deploy context, so every
                # document ID reached users unresolved.
                "documentRegistry": pb._document_labels.registry_source(),
            },
            "features": features,
            "tools": pb._immigration_tools.build_registry().describe(),
            "candidateWarnings": candidate_warnings,
            "llmWarnings": llm.get("warnings", []),
            "liveVerification": {
                "performed": False,
                "note": (
                    "This endpoint reports CONFIGURATION readiness only and issues no "
                    "provider call. A configured provider is not a working one. Prove a "
                    "real completion with: python3 scripts/smoke_ai_runtime.py "
                    "--backend-url <url> --require-live"
                ),
            },
        }
    return router
