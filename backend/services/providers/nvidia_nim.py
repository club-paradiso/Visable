"""Fail-closed NVIDIA API Catalog trial scaffold; not wired to /api/ask."""
from __future__ import annotations
import os, re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
PUBLIC_NON_PERSONAL = "public_non_personal"
PERSONAL_OR_SENSITIVE = "personal_or_sensitive"
UNKNOWN = "unknown"
Transport = Callable[[str, Dict[str, str], Dict[str, Any], float], Awaitable[Tuple[int, Any]]]

def _bool(name: str, default=False) -> bool:
    return (os.environ.get(name, str(default)) or "").strip().lower() in {"1", "true", "yes", "on"}

def _num(name: str, default: float) -> float:
    try:
        value = float((os.environ.get(name) or "").strip())
        return value if value > 0 else default
    except ValueError:
        return default

def _modes(raw: str) -> Tuple[str, ...]:
    values = tuple(dict.fromkeys(x.strip().lower() for x in raw.split(",") if x.strip()))
    return values or ("research", "internal_qa")

@dataclass(frozen=True)
class NvidiaNimConfig:
    api_key: str = ""
    enabled: bool = False
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 45.0
    max_tokens: int = 1200
    reasoning_enabled: bool = False
    allowed_modes: Tuple[str, ...] = ("research", "internal_qa")
    personal_data_allowed: bool = False

    @classmethod
    def from_env(cls):
        return cls(
            api_key=(os.environ.get("NVIDIA_API_KEY") or "").strip(),
            enabled=_bool("ENABLE_NVIDIA_NIM_EXPERIMENTAL"),
            base_url=(os.environ.get("NVIDIA_NIM_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/"),
            model=(os.environ.get("NVIDIA_NIM_MODEL") or DEFAULT_MODEL).strip(),
            timeout_seconds=_num("NVIDIA_NIM_TIMEOUT_SECONDS", 45),
            max_tokens=int(_num("NVIDIA_NIM_MAX_TOKENS", 1200)),
            reasoning_enabled=_bool("NVIDIA_NIM_REASONING_ENABLED"),
            allowed_modes=_modes(os.environ.get("NVIDIA_NIM_ALLOWED_MODES") or "research,internal_qa"),
            personal_data_allowed=_bool("NVIDIA_NIM_ALLOW_PERSONAL_DATA"),
        )

class NvidiaNimBlocked(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code; self.public_message = message

class NvidiaNimProvider:
    provider_name = "nvidia_nim"
    def __init__(self, config: Optional[NvidiaNimConfig] = None, *, transport: Optional[Transport] = None):
        self.config = config or NvidiaNimConfig.from_env()
        self._transport = transport or self._post

    @property
    def configured(self): return bool(self.config.api_key)
    @property
    def enabled(self): return self.config.enabled

    def metadata(self):
        return {"provider_name": self.provider_name, "configured": self.configured,
                "enabled": self.enabled, "allowed_modes": list(self.config.allowed_modes),
                "personal_data_allowed": self.config.personal_data_allowed,
                "production_ready": False, "base_url": self.config.base_url,
                "model": self.config.model, "timeout_seconds": self.config.timeout_seconds,
                "max_tokens": self.config.max_tokens, "reasoning_enabled": self.config.reasoning_enabled,
                "wired_to_api_ask": False}

    def health_check(self):
        status = "disabled" if not self.enabled else ("not_configured" if not self.configured else "ready_for_internal_experiment")
        return {**self.metadata(), "status": status, "live_check_performed": False}

    def _guard(self, mode: str, classification: str):
        if not self.enabled: raise NvidiaNimBlocked("nvidia_nim_disabled", "Experimental NVIDIA provider is disabled.")
        if not self.configured: raise NvidiaNimBlocked("nvidia_nim_not_configured", "Experimental NVIDIA provider is not configured.")
        if (mode or "").strip().lower() not in self.config.allowed_modes:
            raise NvidiaNimBlocked("nvidia_nim_mode_not_allowed", "This request mode is not allowed for NVIDIA.")
        if classification not in {PUBLIC_NON_PERSONAL, PERSONAL_OR_SENSITIVE}:
            raise NvidiaNimBlocked("nvidia_nim_data_classification_required", "NVIDIA requires an explicit data classification.")
        if classification == PERSONAL_OR_SENSITIVE and not self.config.personal_data_allowed:
            raise NvidiaNimBlocked("nvidia_nim_personal_data_not_allowed", "Personal or sensitive data is not allowed for NVIDIA.")

    async def chat_completion(self, messages: List[Dict[str, str]], *, request_mode: str, data_classification: str = UNKNOWN) -> str:
        self._guard(request_mode, data_classification)
        payload: Dict[str, Any] = {"model": self.config.model, "messages": messages,
                                  "max_tokens": self.config.max_tokens, "stream": False}
        if self.config.reasoning_enabled:
            payload["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        try:
            status, body = await self._transport(f"{self.config.base_url}/chat/completions", headers, payload, self.config.timeout_seconds)
        except Exception as exc:
            raise NvidiaNimBlocked("nvidia_nim_unavailable", self.sanitize_error(exc)) from None
        if status >= 400:
            raise NvidiaNimBlocked("nvidia_nim_upstream_error", f"NVIDIA experimental endpoint returned status {status}.")
        try: return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            raise NvidiaNimBlocked("nvidia_nim_bad_response", "NVIDIA experimental endpoint returned an unexpected response.") from None

    def sanitize_error(self, error: Any) -> str:
        text = str(error or "NVIDIA experimental provider unavailable.")
        if self.config.api_key: text = text.replace(self.config.api_key, "[REDACTED]")
        text = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", text)
        return text[:240]

    async def _post(self, url, headers, payload, timeout):
        if httpx is None: raise RuntimeError("HTTP client unavailable")
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
        try: body = response.json()
        except ValueError: body = {}
        return response.status_code, body
