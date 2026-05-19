from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .grounding_config import GroundingConfig

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


class PublicDataClient:
    """Audit-mode HTTP client for public-data grounding (conservative scope)."""

    def __init__(self, config: GroundingConfig):
        self.config = config

    def _result(self, *, status: str, query: str, results: List[Dict[str, Any]] | None = None,
                warnings: List[str] | None = None) -> Dict[str, Any]:
        return {
            "status": status,
            "source_type": "public_data",
            "query": query,
            "results": results or [],
            "warnings": warnings or [],
            "retrieved_at": _now_iso(),
        }

    def _guard(self, query: str) -> Dict[str, Any] | None:
        q = (query or "").strip()
        if not q:
            return self._result(status="invalid_request", query=query, warnings=["PUBLIC_DATA_QUERY_EMPTY"])
        if self.config.mode == "disabled":
            return self._result(status="disabled", query=q, warnings=["PUBLIC_DATA_GROUNDING_DISABLED"])
        if not self.config.public_data_api_key:
            return self._result(status="unavailable", query=q, warnings=["PUBLIC_DATA_API_KEY_MISSING"])
        if httpx is None or not self.config.public_data_base_url:
            return self._result(status="unavailable", query=q, warnings=["SOURCE_UNAVAILABLE"])
        return None

    def _call(self, query: str, path: str, params: Dict[str, str]) -> Dict[str, Any]:
        if not path:
            return self._result(status="unavailable", query=query, warnings=["SOURCE_UNAVAILABLE"])

        url = _join_url(self.config.public_data_base_url, path)
        headers = {"Authorization": f"Bearer {self.config.public_data_api_key}"}
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.get(url, params=params, headers=headers)
        except TimeoutError:
            return self._result(status="error", query=query, warnings=["PUBLIC_DATA_TIMEOUT"])
        except Exception:
            return self._result(status="error", query=query, warnings=["SOURCE_UNAVAILABLE"])

        if resp.status_code >= 400:
            return self._result(status="error", query=query, warnings=["PUBLIC_DATA_HTTP_ERROR"])
        try:
            payload = resp.json()
        except Exception:
            return self._result(status="error", query=query, warnings=["PUBLIC_DATA_PARSE_ERROR"])

        if isinstance(payload, list):
            results = payload
        elif isinstance(payload, dict):
            results = payload.get("results") if isinstance(payload.get("results"), list) else [payload]
        else:
            return self._result(status="error", query=query, warnings=["PUBLIC_DATA_PARSE_ERROR"])
        return self._result(status="ok", query=query, results=results)

    def fetch_visa_public_data(self, query: str) -> Dict[str, Any]:
        guarded = self._guard(query)
        if guarded is not None:
            return guarded
        q = query.strip()
        return self._call(q, self.config.public_data_visa_path, {"query": q, "domain": "visa"})

    def fetch_job_public_data(self, query: str) -> Dict[str, Any]:
        guarded = self._guard(query)
        if guarded is not None:
            return guarded
        q = query.strip()
        return self._call(q, self.config.public_data_job_path, {"query": q, "domain": "job"})
