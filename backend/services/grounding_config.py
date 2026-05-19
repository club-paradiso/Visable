from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

_SUPPORTED_MODES = {"disabled", "audit", "enabled"}
_DEFAULT_TIMEOUT_SECONDS = 8.0
_DEFAULT_CACHE_TTL_SECONDS = 86400


@dataclass(frozen=True)
class GroundingConfig:
    public_data_api_key: str = ""
    law_api_key: str = ""
    mode: str = "disabled"
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    cache_ttl_seconds: int = _DEFAULT_CACHE_TTL_SECONDS
    law_api_base_url: str = ""
    law_api_search_path: str = ""
    law_api_article_path: str = ""
    public_data_base_url: str = ""
    public_data_visa_path: str = ""
    public_data_job_path: str = ""
    warnings: List[str] = field(default_factory=list)


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


def load_grounding_config() -> GroundingConfig:
    warnings: List[str] = []
    mode = (os.environ.get("LAW_GROUNDING_MODE") or "disabled").strip().lower()
    if mode not in _SUPPORTED_MODES:
        warnings.append("LAW_GROUNDING_MODE_INVALID_USING_DISABLED")
        mode = "disabled"

    return GroundingConfig(
        public_data_api_key=(os.environ.get("PUBLIC_DATA_API_KEY") or "").strip(),
        law_api_key=(os.environ.get("LAW_API_KEY") or "").strip(),
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
