from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .grounding_config import GroundingConfig

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - import guard
    httpx = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


class KoreanLawClient:
    """Audit-mode HTTP client for Korean law grounding (conservative scope)."""

    def __init__(self, config: GroundingConfig):
        self.config = config

    def _result(self, *, status: str, query: str, results: List[Dict[str, Any]] | None = None,
                warnings: List[str] | None = None) -> Dict[str, Any]:
        return {
            "status": status,
            "source_type": "law",
            "query": query,
            "results": results or [],
            "warnings": warnings or [],
            "retrieved_at": _now_iso(),
        }

    def _guard(self, query: str) -> Dict[str, Any] | None:
        q = (query or "").strip()
        if not q:
            return self._result(status="invalid_request", query=query, warnings=["LAW_QUERY_EMPTY"])
        if self.config.mode == "disabled":
            return self._result(status="disabled", query=q, warnings=["LAW_GROUNDING_DISABLED"])
        if not self.config.law_api_key:
            return self._result(status="unavailable", query=q, warnings=["LAW_API_KEY_MISSING"])
        if httpx is None:
            return self._result(status="unavailable", query=q, warnings=["SOURCE_UNAVAILABLE"])
        if not self.config.law_api_base_url:
            return self._result(status="unavailable", query=q, warnings=["SOURCE_UNAVAILABLE"])
        return None

    def _call(self, path: str, query: str, params: Dict[str, str]) -> Dict[str, Any]:
        if not path:
            return self._result(status="unavailable", query=query, warnings=["SOURCE_UNAVAILABLE"])

        url = _join_url(self.config.law_api_base_url, path)
        headers = {"Authorization": f"Bearer {self.config.law_api_key}"}
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.get(url, params=params, headers=headers)
        except TimeoutError:
            return self._result(status="error", query=query, warnings=["LAW_API_TIMEOUT"])
        except Exception:
            return self._result(status="error", query=query, warnings=["SOURCE_UNAVAILABLE"])

        if resp.status_code >= 400:
            return self._result(status="error", query=query, warnings=["LAW_API_HTTP_ERROR"])

        try:
            payload = resp.json()
        except Exception:
            return self._result(status="error", query=query, warnings=["LAW_API_PARSE_ERROR"])

        if isinstance(payload, list):
            results = payload
        elif isinstance(payload, dict):
            items = payload.get("results")
            if isinstance(items, list):
                results = items
            else:
                results = [payload]
        else:
            return self._result(status="error", query=query, warnings=["LAW_API_PARSE_ERROR"])

        return self._result(status="ok", query=query, results=results)

    def search_law(self, query: str) -> Dict[str, Any]:
        guarded = self._guard(query)
        if guarded is not None:
            return guarded
        q = query.strip()
        return self._call(
            self.config.law_api_search_path,
            q,
            {"query": q, "mode": self.config.mode},
        )

    def get_article(self, law_name: str, article: str) -> Dict[str, Any]:
        query = f"{(law_name or '').strip()} {(article or '').strip()}".strip()
        guarded = self._guard(query)
        if guarded is not None:
            return guarded
        return self._call(
            self.config.law_api_article_path,
            query,
            {"law_name": (law_name or "").strip(), "article": (article or "").strip(), "mode": self.config.mode},
        )
