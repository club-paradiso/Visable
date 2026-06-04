#!/usr/bin/env python3
"""Safely capture Open Law API response-shape metadata.

This helper is intentionally metadata-only by default. It uses the same backend
credential precedence as Paradiso (LAW_API_OC preferred, LAW_API_KEY fallback),
redacts credential-like values, and never prints raw response bodies.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.grounding_config import load_grounding_config  # noqa: E402
from services.law_tools import _sanitize_url, inspect_law_api_response_shape  # noqa: E402

DEFAULT_HOST = "http://www.law.go.kr"
SEARCH_PATH = "/DRF/lawSearch.do"
FAMILY_TARGETS = {
    "statute": "law",
    "enforcement_decree": "law",
    "enforcement_rule": "law",
    "administrative_rule": "admrul",
    "legal_term": "lstrm",
    "legal_interpretation": None,
    "precedent": None,
    "administrative_appeal": None,
}
FAMILY_QUERY_HINTS = {
    "statute": "출입국관리법 체류자격",
    "enforcement_decree": "출입국관리법 시행령 체류자격 별표",
    "enforcement_rule": "출입국관리법 시행규칙 체류자격 신고",
    "administrative_rule": "체류자격외활동 근무처 변경 행정규칙",
    "legal_term": "체류자격",
    "legal_interpretation": "체류자격외활동 법령해석",
    "precedent": "출입국관리 체류자격 판례",
    "administrative_appeal": "체류자격외활동 행정심판",
}


def _redact(obj: Any, secrets: set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _redact(v, secrets) for k, v in obj.items() if k.lower() not in {"oc", "law_api_oc", "law_api_key", "apikey", "api_key", "servicekey"}}
    if isinstance(obj, list):
        return [_redact(v, secrets) for v in obj]
    text = str(obj) if obj is not None else ""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(OC|LAW_API_OC|LAW_API_KEY|apikey|api_key|servicekey)=([^&\s]+)", r"\1=[REDACTED]", text)
    return text


def _build_url(credential: str, family: str, query: str, display: int) -> str:
    target = FAMILY_TARGETS[family]
    if not target:
        return ""
    params = {"OC": credential, "target": target, "type": "JSON", "query": query, "display": str(display)}
    return f"{DEFAULT_HOST}{SEARCH_PATH}?{urllib.parse.urlencode(params)}"


def capture(family: str, query: str, display: int, timeout: float) -> Dict[str, Any]:
    cfg = load_grounding_config()
    secrets = {cfg.law_api_oc, cfg.law_api_key, cfg.law_api_credential}
    if family not in FAMILY_TARGETS:
        raise ValueError(f"Unsupported family argument: {family}")
    if not FAMILY_TARGETS[family]:
        return {
            "source_family": family,
            "status": "unsupported",
            "query": query,
            "sanitized_url": "",
            "response_shape_hint": "unknown",
            "parser_status": "planned_not_wired",
        }
    if not cfg.law_api_configured:
        return {
            "source_family": family,
            "status": "not_configured",
            "query": query,
            "sanitized_url": "",
            "response_shape_hint": "unknown",
            "parser_status": "not_configured",
        }
    url = _build_url(cfg.law_api_credential, family, query, display)
    sanitized_url = _sanitize_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Paradiso-law-shape-capture/2026.05"})
    status = 0
    content_type = ""
    encoding = ""
    text = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200) or 200)
            content_type = resp.headers.get("content-type", "")
            encoding = resp.headers.get_content_charset() or ""
            text = resp.read(200000).decode(encoding or "utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        content_type = getattr(exc, "headers", {}).get("content-type", "") if getattr(exc, "headers", None) else ""
        text = exc.read(200000).decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
    except Exception as exc:
        return {
            "source_family": family,
            "status": "transport_error",
            "query": query,
            "sanitized_url": sanitized_url,
            "safe_error_message": _redact(str(type(exc).__name__), secrets),
            "response_shape_hint": "unknown",
            "parser_status": "transport_error",
        }
    shape = inspect_law_api_response_shape(_redact(text, secrets))
    return {
        "source_family": family,
        "status": "captured",
        "query": query,
        "http_status": status,
        "content_type": _redact(content_type, secrets),
        "encoding": encoding,
        "sanitized_url": sanitized_url,
        **shape,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Capture sanitized Open Law API response-shape metadata; never prints OC/API keys.")
    ap.add_argument("--family", choices=sorted(FAMILY_TARGETS), default="statute", help="official source family to sample")
    ap.add_argument("--query", default="", help="sample query; defaults to a family-specific immigration-law query")
    ap.add_argument("--display", type=int, default=3, help="Open Law API display count (metadata only)")
    ap.add_argument("--timeout", type=float, default=8.0, help="HTTP timeout seconds")
    ap.add_argument("--write-fixture", action="store_true", help="write sanitized metadata fixture under backend/tests/fixtures/law_api_shapes/")
    args = ap.parse_args()
    query = args.query or FAMILY_QUERY_HINTS[args.family]
    meta = capture(args.family, query, max(1, min(args.display, 10)), args.timeout)
    print(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True))
    if args.write_fixture:
        out_dir = REPO_ROOT / "backend" / "tests" / "fixtures" / "law_api_shapes"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{args.family}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
