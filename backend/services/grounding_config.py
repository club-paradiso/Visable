from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_SUPPORTED_MODES = {"disabled", "audit", "enabled"}
_DEFAULT_TIMEOUT_SECONDS = 8.0
_DEFAULT_CACHE_TTL_SECONDS = 86400
_LAW_OC_ENV_NAMES = ("LAW_API_OC", "LAW_OC", "OPEN_LAW_ID")
_KNOWN_PLACEHOLDER_OC_VALUES = {"paradiso"}
_RAILWAY_RUNTIME_ENV_NAMES = (
    "RAILWAY_PROJECT_ID",
    "RAILWAY_ENVIRONMENT_ID",
    "RAILWAY_SERVICE_ID",
    "RAILWAY_PUBLIC_DOMAIN",
)


@dataclass(frozen=True)
class GroundingConfig:
    public_data_api_key: str = ""
    # LAW_API_KEY is the legacy / backward-compatibility credential. It is kept
    # only as a fallback. Prefer LAW_API_OC for the Open Law API ``OC`` value.
    law_api_key: str = ""
    # LAW_API_OC is the preferred, explicit Open Law API authentication
    # identifier (the ``OC`` query parameter on open.law.go.kr / DRF). It is
    # NEVER exposed in /health, debug output, logs, or sanitized source URLs.
    law_api_oc: str = ""
    # Non-secret name of the env var that supplied law_api_oc. This allows
    # compatibility with common Korean Law MCP aliases without exposing values.
    law_api_oc_source: str = "LAW_API_OC"
    mode: str = "enabled"
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    cache_ttl_seconds: int = _DEFAULT_CACHE_TTL_SECONDS
    law_api_base_url: str = ""
    law_api_search_path: str = ""
    law_api_article_path: str = ""
    public_data_base_url: str = ""
    public_data_visa_path: str = ""
    public_data_job_path: str = ""
    warnings: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Credential resolution (OC-style variables preferred, LAW_API_KEY fallback)
    # ------------------------------------------------------------------
    @property
    def law_api_credential(self) -> str:
        """Effective Open Law API ``OC`` value.

        The normal contract remains OC-first. Railway-specific compatibility is
        resolved in ``load_grounding_config`` before the immutable config is
        constructed, so callers and tests see one deterministic credential.
        """
        return self.law_api_oc or self.law_api_key

    @property
    def law_api_credential_source(self) -> str:
        """Which env var supplied the effective credential (non-secret label)."""
        if self.law_api_oc:
            return self.law_api_oc_source or "LAW_API_OC"
        if self.law_api_key:
            return "LAW_API_KEY"
        return ""

    @property
    def law_api_configured(self) -> bool:
        """True when any supported Open Law API credential is present."""
        return bool(self.law_api_credential)

    @property
    def law_api_oc_configured(self) -> bool:
        """True when an effective OC-style credential is set (non-secret)."""
        return bool(self.law_api_oc)

    @property
    def law_api_key_fallback_configured(self) -> bool:
        """True when the legacy ``LAW_API_KEY`` fallback is set (non-secret)."""
        return bool(self.law_api_key)


def _parse_timeout(raw_value: str | None) -> float:
    if raw_value is None or raw_value.strip() == "":
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw_value)
        return value if value > 0 else _DEFAULT_TIMEOUT_SECONDS
    except (TypeError, ValueError):
        return _DEFAULT_TIMEOUT_SECONDS


def _parse_cache_ttl(raw_value: str | None) -> int:
    if raw_value is None or raw_value.strip() == "":
        return _DEFAULT_CACHE_TTL_SECONDS
    try:
        value = int(raw_value)
        return value if value > 0 else _DEFAULT_CACHE_TTL_SECONDS
    except (TypeError, ValueError):
        return _DEFAULT_CACHE_TTL_SECONDS


def _is_railway_runtime() -> bool:
    """Detect the running Railway service without requiring a user secret.

    Railway injects these system variables into builds/deployments. Requiring a
    platform marker keeps the historical non-Railway OC-first contract intact.
    """
    return any((os.environ.get(name) or "").strip() for name in _RAILWAY_RUNTIME_ENV_NAMES)


def _configured_oc_credentials() -> list[tuple[str, str]]:
    configured: list[tuple[str, str]] = []
    for name in _LAW_OC_ENV_NAMES:
        value = (os.environ.get(name) or "").strip()
        if value:
            configured.append((value, name))
    return configured


def _resolve_oc_credential() -> tuple[str, str]:
    configured = _configured_oc_credentials()
    if not configured:
        return "", "LAW_API_OC"

    # Preserve the established OC-first contract everywhere except the live
    # Railway runtime. Historical deployment docs used `paradiso` as an example
    # OC and a recorded live probe returned HTTP 403 for it. If that stale value
    # still exists on Railway, prefer another configured *real* OC alias. If no
    # real OC alias exists, load_grounding_config will fall back to LAW_API_KEY.
    first_value, first_name = configured[0]
    if _is_railway_runtime() and first_value.lower() in _KNOWN_PLACEHOLDER_OC_VALUES:
        for value, name in configured[1:]:
            if value.lower() not in _KNOWN_PLACEHOLDER_OC_VALUES:
                return value, name
    return first_value, first_name


def load_grounding_config() -> GroundingConfig:
    warnings: List[str] = []
    mode = (os.environ.get("LAW_GROUNDING_MODE") or "enabled").strip().lower()
    if mode not in _SUPPORTED_MODES:
        warnings.append("LAW_GROUNDING_MODE_INVALID_USING_DISABLED")
        mode = "disabled"

    law_api_oc, law_api_oc_source = _resolve_oc_credential()
    law_api_key = (os.environ.get("LAW_API_KEY") or "").strip()

    if law_api_oc and law_api_oc_source != "LAW_API_OC":
        warnings.append("LAW_API_OC_ALIAS_USED")

    railway_placeholder = bool(
        _is_railway_runtime()
        and law_api_oc
        and law_api_oc.lower() in _KNOWN_PLACEHOLDER_OC_VALUES
    )
    if railway_placeholder:
        warnings.append("LAW_API_OC_PLACEHOLDER_DETECTED_ON_RAILWAY")
        if law_api_key:
            # Do not mutate process.env or expose either value. The immutable
            # config simply represents the effective credential Railway should
            # use for this process.
            law_api_oc = ""
            law_api_oc_source = "LAW_API_OC"
            warnings.append("LAW_API_OC_PLACEHOLDER_IGNORED_FOR_RAILWAY_KEY_FALLBACK")

    # Non-secret advisory: the deployment is relying on the legacy LAW_API_KEY
    # fallback only. Recommend the explicit registered LAW_API_OC. This marker
    # never contains either value.
    if law_api_key and not law_api_oc:
        warnings.append("LAW_API_OC_RECOMMENDED")

    return GroundingConfig(
        public_data_api_key=(os.environ.get("PUBLIC_DATA_API_KEY") or "").strip(),
        law_api_key=law_api_key,
        law_api_oc=law_api_oc,
        law_api_oc_source=law_api_oc_source,
        mode=mode,
        timeout_seconds=_parse_timeout(os.environ.get("LAW_GROUNDING_TIMEOUT_SECONDS")),
        cache_ttl_seconds=_parse_cache_ttl(os.environ.get("LAW_GROUNDING_CACHE_TTL_SECONDS")),
        law_api_base_url=(os.environ.get("LAW_API_BASE_URL") or "").strip(),
        law_api_search_path=(os.environ.get("LAW_API_SEARCH_PATH") or "").strip(),
        law_api_article_path=(os.environ.get("LAW_API_ARTICLE_PATH") or "").strip(),
        public_data_base_url=(os.environ.get("PUBLIC_DATA_BASE_URL") or "").strip(),
        public_data_visa_path=(os.environ.get("PUBLIC_DATA_VISA_PATH") or "").strip(),
        public_data_job_path=(os.environ.get("PUBLIC_DATA_JOB_PATH") or "").strip(),
        warnings=warnings,
    )
