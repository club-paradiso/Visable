"""Internal MCP-like law tool layer for Paradiso.

This module is a small, typed, deterministic adapter over the Korean National
Law Information Open API (open.law.go.kr — the ``DRF/lawSearch.do`` /
``DRF/lawService.do`` endpoints). It reflects the operating principles the user
referenced from prior law/MCP discussions WITHOUT shipping a public MCP server
or copying any third-party code:

* **korean-law-mcp principle** — law retrieval is a backend *tool/verifier*
  layer, not free-form LLM reasoning. The LLM receives normalized evidence; it
  never invents API calls or law citations.
* **dot-studio principle** — the workflow is split into explicit stages:
  question → intent/status detection → tool plan → retrieval → normalization →
  evidence pack → answer prompt.
* **korean-privacy-terms principle** — sensitive legal/notice wording is kept
  structured and reusable (see ``answer_quality`` and the evidence pack),
  not scattered as one-off strings.

Hard guarantees:

* The OC / API-key value is NEVER returned in URLs, logs, results, or the
  evidence pack. ``_sanitize_url`` strips it.
* Every public function is deterministic and mock-friendly: the HTTP boundary
  is a single injectable ``transport`` callable, so CI never needs live
  network, OpenRouter, Railway, HiKorea, or data.go.kr access.
* Failures are typed (``LAW_API_*``) and never raise out of the tool layer;
  callers downgrade source confidence instead of crashing.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .grounding_config import GroundingConfig, load_grounding_config
from .law_grounding import should_attempt_law_grounding
from .citation_verifier import (
    build_law_evidence_citation_verification,
    verify_case_decision_citations,
)
from .answer_quality import (
    classify_answer_quality,
    classify_question_type,
    detect_related_statuses,
)
from .legal_analysis import (
    build_generalized_source_plan,
    build_legal_analysis,
    classify_legal_issue_types,
    extract_immigration_facts,
    score_evidence_relevance,
)
from .evidence_ontology import (
    ONTOLOGY_VERSION,
    is_source_family_wired,
    plan_evidence_queries,
    route_source_families,
    source_family_support_status,
    status_family,
)
from .source_grounding import (
    build_official_grounding_context,
    classify_query_for_grounding,
    developer_source_diagnostics,
    normalize_law_source_attempts,
    normalize_manual_source_attempts,
    project_public_source_status,
    render_grounding_context_for_prompt,
)

LAW_TOOL_LAYER_VERSION = "2026-06-law-tools-v5-article-verification"

# ---------------------------------------------------------------------------
# Stable error types (Part B contract). Returned in tool output ``error_type``.
# ---------------------------------------------------------------------------
LAW_API_NOT_CONFIGURED = "law_api_not_configured"
LAW_API_HTTP_ERROR = "law_api_http_error"
LAW_API_TIMEOUT = "law_api_timeout"
LAW_API_BAD_RESPONSE = "law_api_bad_response"
LAW_API_NO_RESULTS = "law_api_no_results"
LAW_API_PARSE_ERROR = "law_api_parse_error"
LAW_API_OFFICIAL_ERROR = "law_api_official_error"

SOURCE_STATUS_RESULTS_FOUND = "results_found"
SOURCE_STATUS_NO_RESULTS = "no_results"
SOURCE_STATUS_OFFICIAL_ERROR = "official_error"
SOURCE_STATUS_HTTP_ERROR = "http_error"
SOURCE_STATUS_TIMEOUT = "timeout"
SOURCE_STATUS_BAD_RESPONSE = "bad_response"
SOURCE_STATUS_PARSE_ERROR = "parse_error"
SOURCE_STATUS_UNSUPPORTED = "unsupported"
SOURCE_STATUS_NOT_CONFIGURED = "not_configured"

_ERROR_TO_SOURCE_STATUS = {
    LAW_API_NOT_CONFIGURED: SOURCE_STATUS_NOT_CONFIGURED,
    LAW_API_HTTP_ERROR: SOURCE_STATUS_HTTP_ERROR,
    LAW_API_TIMEOUT: SOURCE_STATUS_TIMEOUT,
    LAW_API_BAD_RESPONSE: SOURCE_STATUS_BAD_RESPONSE,
    LAW_API_NO_RESULTS: SOURCE_STATUS_NO_RESULTS,
    LAW_API_PARSE_ERROR: SOURCE_STATUS_PARSE_ERROR,
    LAW_API_OFFICIAL_ERROR: SOURCE_STATUS_OFFICIAL_ERROR,
}

# Default DRF endpoints for the National Law Information Open API. These are
# public, fixed endpoints (confirmed by scripts/probe_korean_law_open_api_2026_05.py);
# only the OC value is a secret. A deployment that sets LAW_API_BASE_URL can
# override the host (e.g. to a private proxy) without touching code.
#
# HTTPS by default: cloud egress proxies (e.g. Railway) commonly block plaintext
# outbound HTTP / port 80 — the live smoke "CONNECT tunnel failed (000)" symptom
# and the netdiag REACHABLE_HTTPS / HTTP_PORT_80_BLOCKED diagnoses. www.law.go.kr
# serves the same DRF API over TLS, so defaulting to https lets the real-time law
# lookup actually reach the host from a cloud deploy even when port 80 is blocked.
_DEFAULT_API_HOST = "https://www.law.go.kr"
_SEARCH_PATH = "/DRF/lawSearch.do"
_SERVICE_PATH = "/DRF/lawService.do"

# Conservative request ceiling so a single /api/ask never fans out into a
# burst of law-API calls. The planner keeps the set small; this is a hard cap.
_DEFAULT_MAX_QUERIES = 7
_HARD_MAX_QUERIES = 8
_DEFAULT_DISPLAY = 5

_USER_AGENT = "Paradiso-law-tool-layer/2026.05"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# HTTP boundary (single injectable seam — the ONLY place that touches network)
# ---------------------------------------------------------------------------
@dataclass
class LawHttpResponse:
    """Normalized transport result. ``error_type`` is a transport-level marker
    (``timeout`` / ``http_error`` / ``network``), mapped to ``LAW_API_*`` by the
    tool functions."""

    ok: bool
    status_code: int = 0
    text: str = ""
    error_type: str = ""


# A transport takes a fully-built URL (OC already embedded) plus a timeout and
# returns a LawHttpResponse. Tests inject a fake transport; production uses the
# urllib-based default below. The URL is never logged here.
LawTransport = Callable[[str, float], LawHttpResponse]


def _http_get_once(url: str, timeout: float) -> LawHttpResponse:
    """Single urllib GET (no scheme fallback). The URL is never logged here."""
    import socket
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, application/xml, text/plain, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            status = getattr(resp, "status", None) or getattr(resp, "code", 200) or 200
            return LawHttpResponse(ok=True, status_code=int(status), text=text)
    except urllib.error.HTTPError as exc:
        return LawHttpResponse(ok=False, status_code=int(getattr(exc, "code", 0) or 0),
                               error_type="http_error")
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return LawHttpResponse(ok=False, error_type="timeout")
        return LawHttpResponse(ok=False, error_type="network")
    except (TimeoutError, socket.timeout):
        return LawHttpResponse(ok=False, error_type="timeout")
    except Exception:  # pragma: no cover - defensive: never raise out of transport
        return LawHttpResponse(ok=False, error_type="network")


def _swap_scheme(url: str) -> str:
    if url.startswith("https://"):
        return "http://" + url[len("https://"):]
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def _is_law_host(url: str) -> bool:
    try:
        host = urlsplit(url).netloc.lower()
    except Exception:  # pragma: no cover - defensive
        return False
    return host == "law.go.kr" or host.endswith(".law.go.kr")


def _transport_with_scheme_fallback(url: str, timeout: float, sender: LawTransport) -> LawHttpResponse:
    """Send via ``sender``; on a CONNECTION-level failure for a law.go.kr host,
    retry once with the opposite scheme.

    Rationale: cloud egress (e.g. Railway) can block plaintext http / port 80,
    while the law.go.kr DRF host may not serve every scheme identically. Trying
    one scheme and falling back to the other on a *network* failure makes the
    lookup robust either way. A real HTTP response — including a 403 (the OC /
    calling-IP-allowlist case) — means the host WAS reached, so we never swap
    scheme on it (swapping would not help and would mask the real cause).
    """
    resp = sender(url, timeout)
    if (not resp.ok) and resp.error_type == "network" and _is_law_host(url):
        alt = _swap_scheme(url)
        if alt != url:
            alt_resp = sender(alt, timeout)
            if alt_resp.ok or alt_resp.error_type == "http_error":
                return alt_resp
    return resp


def _default_transport(url: str, timeout: float) -> LawHttpResponse:
    """Real network transport (urllib) with https<->http scheme fallback for the
    law.go.kr host. No third-party dependency; the URL/OC is never logged."""
    return _transport_with_scheme_fallback(url, timeout, _http_get_once)


def _sanitize_url(url: str) -> str:
    """Return ``url`` with the OC / any credential-ish query params removed.

    The real request embeds ``OC=<secret>``; the value surfaced to callers,
    debug output, and the evidence pack must NEVER contain it. Reproducible
    everything-but-the-secret URLs are still useful for operators.
    """
    try:
        parts = urlsplit(url)
    except Exception:  # pragma: no cover - defensive
        return ""
    secret_keys = {"oc", "authorization", "key", "apikey", "api_key", "serviceкey", "servicekey"}
    known_secrets = {
        (load_grounding_config().law_api_oc or "").strip(),
        (load_grounding_config().law_api_key or "").strip(),
    }
    kept = [(k, "[REDACTED]" if v in known_secrets and v else v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
            if k.lower() not in secret_keys]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


# ---------------------------------------------------------------------------
# Typed tool inputs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SearchLawsInput:
    query: str
    target: str = "law"
    response_type: str = "JSON"
    limit: int = _DEFAULT_DISPLAY


@dataclass(frozen=True)
class GetLawDetailInput:
    law_id: str = ""
    law_name: str = ""
    article: str = ""
    response_type: str = "JSON"


@dataclass(frozen=True)
class SearchAdminRulesInput:
    query: str
    limit: int = _DEFAULT_DISPLAY


@dataclass(frozen=True)
class SearchLawTermsInput:
    query: str
    limit: int = _DEFAULT_DISPLAY


@dataclass
class OfficialEvidence:
    source_type: str
    title: str = ""
    law_name: str = ""
    article: str = ""
    case_name: str = ""
    case_number: str = ""
    decision_date: str = ""
    summary: str = ""
    query: str = ""
    source_url: str = ""
    retrieval_status: str = ""
    relevance: str = "background"


@dataclass
class OfficialSourceResult:
    source_family: str
    status: str
    query: str
    normalized_items: List[Dict[str, Any]] = field(default_factory=list)
    response_shape_hint: str = ""
    parser_status: str = ""
    sanitized_source_url: str = ""
    error_type: str = ""
    safe_error_message: str = ""


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def _first(obj: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = obj.get(key)
        if value not in (None, "", []):
            return str(value).strip()
    return None


def _normalize_candidate(obj: Dict[str, Any], source_type: str) -> Optional[Dict[str, Any]]:
    """Map one raw API object to a normalized, secret-free candidate dict."""
    if not isinstance(obj, dict):
        return None
    if source_type == "law_term":
        term = _first(obj, "법령용어명", "용어명", "법령용어", "term", "termName")
        if not term:
            return None
        definition = _first(obj, "법령용어정의", "용어설명", "정의", "definition") or ""
        return {
            "source_type": "law_term",
            "title": term,
            "term": term,
            "law_name": "",
            "article": "",
            "case_name": "",
            "case_number": "",
            "decision_date": "",
            "summary": definition[:700],
            "definition": definition,
            "retrieval_status": "ok",
            "relevance": "background",
        }
    if source_type == "admin_rule":
        name = _first(obj, "행정규칙명", "행정규칙명한글", "admRulNm", "lawName")
        serial = _first(obj, "행정규칙일련번호", "admRulSeq", "MST", "mst")
        rule_id = _first(obj, "행정규칙ID", "admRulId", "ID")
        if not (name or serial or rule_id):
            return None
        title = name or "(행정규칙)"
        return {
            "source_type": "admin_rule",
            "title": title,
            "law_name": title,
            "law_id": rule_id or "",
            "law_serial_no": serial or "",
            "reference": rule_id or serial or "",
            "article": _first(obj, "조문번호", "article") or "",
            "case_name": "",
            "case_number": "",
            "decision_date": _first(obj, "발령일자", "시행일자") or "",
            "summary": _first(obj, "행정규칙요약", "summary", "내용") or "",
            "rule_type": _first(obj, "행정규칙종류", "행정규칙구분명") or "",
            "department": _first(obj, "소관부처명", "담당부처명") or "",
            "retrieval_status": "ok",
            "relevance": "background",
        }
    # Default: a statute / enforcement decree / rule.
    name = _first(obj, "법령명한글", "법령명", "법령명_한글", "lawName")
    serial = _first(obj, "법령일련번호", "MST", "mst")
    law_id = _first(obj, "법령ID", "lawId", "ID")
    if not (name or serial or law_id):
        return None
    law_division = _first(obj, "법령구분명", "법종구분명") or ""
    normalized_type = source_type if source_type in {"statute", "enforcement_decree", "enforcement_rule"} else "statute"
    if "시행령" in (name or law_division):
        normalized_type = "enforcement_decree"
    elif "시행규칙" in (name or law_division):
        normalized_type = "enforcement_rule"
    title = name or "(법령)"
    return {
        "source_type": "law",
        "title": title,
        "law_name": title,
        "law_id": law_id or "",
        "law_serial_no": serial or "",
        "reference": law_id or serial or "",
        "article": _first(obj, "조문번호", "article", "조") or "",
        "case_name": "",
        "case_number": "",
        "decision_date": "",
        "summary": _first(obj, "조문내용", "내용", "summary") or "",
        "law_division": law_division,
        "promulgation_date": _first(obj, "공포일자") or "",
        "enforcement_date": _first(obj, "시행일자") or "",
        "department": _first(obj, "소관부처명") or "",
        "retrieval_status": "ok",
        "relevance": "background",
    }


def _walk_candidates(payload: Any, source_type: str, limit: int) -> List[Dict[str, Any]]:
    """Defensively walk a parsed API payload collecting normalized candidates.

    The DRF JSON shape varies (``{"LawSearch": {"law": [...]}}`` etc.) and
    occasionally returns a single object. Walking tolerates all of these
    without hard-coding one schema.
    """
    found: List[Dict[str, Any]] = []
    seen_refs: set = set()

    def visit(node: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            candidate = _normalize_candidate(node, source_type)
            if candidate is not None:
                key = candidate.get("reference") or candidate.get("term") or candidate.get("law_name")
                if key not in seen_refs:
                    seen_refs.add(key)
                    found.append(candidate)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return found[:limit]


def _shape_hint(text: str) -> str:
    """Small, safe response-shape hint for debug output; never includes body."""
    stripped = (text or "").lstrip("\ufeff\ufeff").strip()
    if not stripped:
        return "empty"
    lower = stripped[:200].lower()
    if lower.startswith("<!doctype html") or lower.startswith("<html") or "<body" in lower:
        return "html"
    if lower.startswith("<?xml") or lower.startswith("<"):
        return "xml"
    if stripped.startswith("["):
        return "json_list"
    if stripped.startswith("{"):
        return "json_object"
    return "text"


def _xml_to_obj(elem: ET.Element) -> Any:
    children = list(elem)
    text = (elem.text or "").strip()
    if not children:
        return text
    out: Dict[str, Any] = {}
    for child in children:
        key = child.tag.split("}", 1)[-1]
        val = _xml_to_obj(child)
        if key in out:
            if not isinstance(out[key], list):
                out[key] = [out[key]]
            out[key].append(val)
        else:
            out[key] = val
    if text:
        out["_text"] = text
    return out


def _safe_text(value: Any, *, limit: int = 160) -> str:
    text = str(value or "").strip()[:limit]
    for secret in (load_grounding_config().law_api_oc, load_grounding_config().law_api_key):
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(OC|LAW_API_OC|LAW_API_KEY|apikey|api_key|servicekey)=([^&\s]+)", r"\1=[REDACTED]", text)
    return text


def _official_error_info(payload: Any) -> Tuple[bool, str, str]:
    """Detect official API error objects and return safe code/message only."""
    success_values = {"00", "0", "success", "ok", "정상"}
    found = False
    code = ""
    message = ""

    def set_code(value: Any) -> None:
        nonlocal code
        if not code and value not in (None, ""):
            code = _safe_text(value, limit=80)

    def set_message(value: Any) -> None:
        nonlocal message
        if not message and value not in (None, ""):
            message = _safe_text(value, limit=180)

    def walk(node: Any) -> bool:
        nonlocal found
        if isinstance(node, dict):
            lowered = {str(k).lower(): v for k, v in node.items()}
            for key, value in lowered.items():
                sval = str(value).strip().lower()
                # A success code (errorCode "0"/"00"/"OK") must NOT be flagged as
                # an official error — otherwise a perfectly good search response
                # carrying errorCode=0 would collapse into official_error and
                # then look like a bad response downstream.
                if key in {"error", "errorcode", "errcode"} and sval and sval not in success_values:
                    found = True; set_code(value)
                if key in {"resultcode", "code"} and sval and sval not in success_values:
                    found = True; set_code(value)
                if key in {"message", "msg", "errmsg", "errormessage"}:
                    set_message(value)
                    if sval and any(w in sval for w in ("error", "오류", "not", "invalid", "fail", "인증", "권한")):
                        found = True
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        return found

    walk(payload)
    return found, code, message


def _contains_official_error(payload: Any) -> bool:
    """Detect official API error objects without exposing message/body."""
    return _official_error_info(payload)[0]


def _xml_root_tag(text: str) -> str:
    try:
        root = ET.fromstring((text or "").strip())
        return root.tag.split("}", 1)[-1]
    except Exception:
        return ""


def inspect_law_api_response_shape(text: str) -> Dict[str, Any]:
    """Safe parser/shape metadata for capture tooling and debug output."""
    payload, error, parser_status, shape = _parse_payload(text or "")
    info = {"response_shape_hint": shape, "parser_status": parser_status, "error_type": error or ""}
    if shape in {"json_object", "json_list"}:
        try:
            obj = json.loads((text or "").strip())
            if isinstance(obj, dict):
                info["json_root_keys"] = list(obj.keys())[:20]
            elif isinstance(obj, list):
                info["list_item_count"] = len(obj)
            official, code, msg = _official_error_info(obj)
            if official:
                info["official_error_code"] = code
                info["official_error_message"] = msg
        except Exception:
            pass
    elif shape == "xml":
        info["xml_root_tag"] = _xml_root_tag(text or "")
        if payload is not None:
            official, code, msg = _official_error_info(payload)
            if official:
                info["official_error_code"] = code
                info["official_error_message"] = msg
    return info


def _parse_payload(text: str) -> Tuple[Optional[Any], Optional[str], str, str]:
    """Parse response as JSON or XML. Returns (payload, error_type, parser_status, shape_hint)."""
    stripped = (text or "").strip()
    shape = _shape_hint(stripped)
    if shape == "empty":
        return None, LAW_API_NO_RESULTS, "empty", shape
    if shape == "html":
        return None, LAW_API_BAD_RESPONSE, "unsupported_html", shape
    if shape in {"json_object", "json_list"}:
        try:
            payload = json.loads(stripped)
        except Exception:
            return None, LAW_API_PARSE_ERROR, "json_parse_error", shape
        if _contains_official_error(payload):
            return payload, LAW_API_OFFICIAL_ERROR, "official_error", shape
        return payload, None, "parsed_json", shape
    if shape == "xml":
        try:
            root = ET.fromstring(stripped)
            payload = {root.tag.split("}", 1)[-1]: _xml_to_obj(root)}
        except Exception:
            return None, LAW_API_PARSE_ERROR, "xml_parse_error", shape
        if _contains_official_error(payload):
            return payload, LAW_API_OFFICIAL_ERROR, "official_error", shape
        return payload, None, "parsed_xml", shape
    return None, LAW_API_BAD_RESPONSE, "unsupported_text", shape


def parse_law_search_response(text: str, *, source_type: str = "law", limit: int = _DEFAULT_DISPLAY) -> Dict[str, Any]:
    payload, error, parser_status, shape = _parse_payload(text)
    results = [] if error else _walk_candidates(payload, source_type, limit)
    if not error and not results:
        error = LAW_API_NO_RESULTS
    return {"payload": payload if error is None else None, "results": results, "error_type": error or "", "parser_status": parser_status, "response_shape_hint": shape}


def parse_law_detail_response(text: str, *, limit: int = 1) -> Dict[str, Any]:
    return parse_law_search_response(text, source_type="law", limit=limit)


def parse_admin_rule_response(text: str, *, limit: int = _DEFAULT_DISPLAY) -> Dict[str, Any]:
    return parse_law_search_response(text, source_type="admin_rule", limit=limit)


# ---------------------------------------------------------------------------
# Request building + execution
# ---------------------------------------------------------------------------
def _api_host(config: GroundingConfig) -> str:
    base = (config.law_api_base_url or "").strip()
    return base.rstrip("/") if base else _DEFAULT_API_HOST


def _build_request_url(config: GroundingConfig, path: str, params: Dict[str, str]) -> str:
    full = {"OC": config.law_api_credential, **params}
    query = urlencode({k: v for k, v in full.items() if v not in (None, "")})
    return f"{_api_host(config)}{path}?{query}"


def _tool_error(tool: str, *, query: str, target: str, error_type: str,
                source_url: str = "", raw_status: int = 0, parser_status: str = "",
                response_shape_hint: str = "", failure_reason: str = "") -> Dict[str, Any]:
    return {
        "tool": tool,
        "status": "error",
        "error_type": error_type,
        "query": query,
        "target": target,
        "source_url": source_url,
        "raw_status": raw_status,
        "parser_status": parser_status,
        "response_shape_hint": response_shape_hint,
        "failure_reason": failure_reason,
        "attempted_targets": [target] if target else [],
        "results": [],
        "result_count": 0,
        "retrieved_at": _now_iso(),
    }


def _execute(
    *,
    tool: str,
    config: GroundingConfig,
    transport: Optional[LawTransport],
    path: str,
    params: Dict[str, str],
    target: str,
    query: str,
    source_type: str,
    limit: int,
    include_payload: bool = False,
) -> Dict[str, Any]:
    """Shared request → transport → normalize pipeline for every tool."""
    if not config.law_api_configured:
        return _tool_error(tool, query=query, target=target, error_type=LAW_API_NOT_CONFIGURED, failure_reason="not_configured")

    url = _build_request_url(config, path, params)
    sanitized = _sanitize_url(url)
    send = transport or _default_transport
    try:
        response = send(url, config.timeout_seconds)
    except Exception:  # pragma: no cover - transport must not raise, but guard
        return _tool_error(tool, query=query, target=target,
                           error_type=LAW_API_BAD_RESPONSE, source_url=sanitized, failure_reason="transport_exception")

    if not response.ok:
        mapping = {
            "timeout": LAW_API_TIMEOUT,
            "http_error": LAW_API_HTTP_ERROR,
            "network": LAW_API_BAD_RESPONSE,
        }
        error_type = mapping.get(response.error_type, LAW_API_BAD_RESPONSE)
        return _tool_error(tool, query=query, target=target, error_type=error_type,
                           source_url=sanitized, raw_status=response.status_code, failure_reason=response.error_type or "transport_error")

    if response.status_code >= 400:
        return _tool_error(tool, query=query, target=target, error_type=LAW_API_HTTP_ERROR,
                           source_url=sanitized, raw_status=response.status_code, failure_reason="http_status")

    parsed = parse_admin_rule_response(response.text, limit=limit) if source_type == "admin_rule" else parse_law_search_response(response.text, source_type=source_type, limit=limit)
    parse_error = parsed.get("error_type")
    if parse_error:
        return _tool_error(
            tool, query=query, target=target, error_type=parse_error,
            source_url=sanitized, raw_status=response.status_code,
            parser_status=parsed.get("parser_status", ""),
            response_shape_hint=parsed.get("response_shape_hint", ""),
            failure_reason="official_api_error" if parse_error == LAW_API_OFFICIAL_ERROR else parsed.get("parser_status", ""),
        )

    payload = parsed.get("payload")
    results = parsed.get("results") or []

    for item in results:
        if isinstance(item, dict) and sanitized:
            item.setdefault("source_url", sanitized)
            item.setdefault("query", query)

    ok_result: Dict[str, Any] = {
        "tool": tool,
        "status": "ok",
        "error_type": "",
        "query": query,
        "target": target,
        "source_url": sanitized,
        "raw_status": response.status_code,
        "parser_status": parsed.get("parser_status", ""),
        "response_shape_hint": parsed.get("response_shape_hint", ""),
        "failure_reason": "",
        "attempted_targets": [target] if target else [],
        "results": results,
        "result_count": len(results),
        "retrieved_at": _now_iso(),
    }
    if include_payload:
        # Only get_law_detail consumes this (for article extraction). It is
        # stripped before returning so a raw payload never reaches the LLM.
        ok_result["_raw_payload"] = payload
    return ok_result


# ---------------------------------------------------------------------------
# Public tools (Part B)
# ---------------------------------------------------------------------------
def _coerce_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return _DEFAULT_DISPLAY
    return max(1, min(value, 50))


def search_laws(
    query: str,
    *,
    target: str = "law",
    response_type: str = "JSON",
    limit: int = _DEFAULT_DISPLAY,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
) -> Dict[str, Any]:
    """Search statutes / enforcement decrees / rules on the Open Law API.

    Builds the request with the OC value internally; returns normalized law
    candidates plus a sanitized (secret-free) ``source_url``. Never raises.
    """
    cfg = config or load_grounding_config()
    q = (query or "").strip()
    if not q:
        return _tool_error("search_laws", query="", target=target, error_type=LAW_API_NO_RESULTS)
    capped = _coerce_limit(limit)
    return _execute(
        tool="search_laws",
        config=cfg,
        transport=transport,
        path=_SEARCH_PATH,
        params={"target": target or "law", "type": response_type or "JSON",
                "query": q, "display": str(capped)},
        target=target or "law",
        query=q,
        source_type="law" if (target or "law") == "law" else "admin_rule",
        limit=capped,
    )


def get_law_detail(
    *,
    law_id: str = "",
    law_name: str = "",
    article: str = "",
    response_type: str = "JSON",
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
) -> Dict[str, Any]:
    """Fetch a normalized law detail (and articles where available).

    Accepts a law id / serial number, or a law name (resolved via a search
    first). The article filter is best-effort.
    """
    cfg = config or load_grounding_config()
    if not cfg.law_api_configured:
        return _tool_error("get_law_detail", query=law_name or law_id, target="law",
                           error_type=LAW_API_NOT_CONFIGURED)

    resolved_id = (law_id or "").strip()
    resolved_name = (law_name or "").strip()
    if not resolved_id and resolved_name:
        search = search_laws(resolved_name, config=cfg, transport=transport, limit=1)
        if search["status"] != "ok":
            return _tool_error("get_law_detail", query=resolved_name, target="law",
                               error_type=search["error_type"])
        top = search["results"][0]
        resolved_id = top.get("law_serial_no") or top.get("law_id") or ""
        resolved_name = top.get("law_name") or resolved_name
    if not resolved_id:
        return _tool_error("get_law_detail", query=resolved_name or law_id, target="law",
                           error_type=LAW_API_NO_RESULTS)

    params: Dict[str, str] = {"target": "law", "type": response_type or "JSON"}
    # The DRF service endpoint accepts MST (serial) or ID; we pass MST when the
    # value looks like a serial, else ID. Both are non-secret references.
    if resolved_id.isdigit():
        params["MST"] = resolved_id
    else:
        params["ID"] = resolved_id

    result = _execute(
        tool="get_law_detail",
        config=cfg,
        transport=transport,
        path=_SERVICE_PATH,
        params=params,
        target="law",
        query=resolved_name or resolved_id,
        source_type="law",
        limit=1,
        include_payload=True,
    )
    if result["status"] == "ok":
        detail = dict(result["results"][0]) if result["results"] else {}
        detail["articles"] = _extract_articles(result, article)
        result["detail"] = detail
    # Strip the raw payload so it never propagates to a caller / the LLM.
    result.pop("_raw_payload", None)
    return result


_ARTICLE_KEYS = ("조문내용", "조문제목", "조문번호", "조문가지번호")


def _article_parts(value: Any, branch_value: Any = "") -> Tuple[Optional[int], Optional[int]]:
    """Normalize Open Law and human article numbers to ``(article, branch)``.

    Open Law detail payloads commonly encode 제21조 as ``002100`` and put the
    가지번호 in a separate field, while user text uses ``제21조`` or
    ``제21조의2``.  Comparing normalized integers prevents a list hit from
    being mistaken for a verified article merely because those encodings look
    different.
    """
    text = str(value or "").strip()
    branch_text = str(branch_value or "").strip()
    human = re.search(r"제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if human:
        article_no = int(human.group(1))
        branch_no = int(human.group(2)) if human.group(2) else None
        return article_no, branch_no
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None, None
    if len(digits) >= 6:
        # DRF 조문번호 uses a zero-padded four-digit article plus two-digit
        # branch marker (e.g. 002100). A separate 조문가지번호 wins when set.
        article_no = int(digits[:4])
        encoded_branch = int(digits[4:6])
        branch_no = encoded_branch or None
    else:
        article_no = int(digits)
        branch_no = None
    branch_digits = re.sub(r"\D", "", branch_text)
    if branch_digits and int(branch_digits):
        branch_no = int(branch_digits)
    return article_no, branch_no


def _extract_articles(result: Dict[str, Any], article_filter: str) -> List[Dict[str, Any]]:
    """Best-effort article normalization from a service response (tolerant)."""
    # The normalized candidate path does not retain raw articles; service
    # payloads vary widely, so we keep this conservative and schema-tolerant.
    raw = result.get("_raw_payload")
    articles: List[Dict[str, Any]] = []
    target_no = (article_filter or "").strip()
    target_parts = _article_parts(target_no) if target_no else (None, None)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if any(k in node for k in _ARTICLE_KEYS):
                no = _first(node, "조문번호") or ""
                branch = _first(node, "조문가지번호") or ""
                title = _first(node, "조문제목") or ""
                text = _first(node, "조문내용") or ""
                parts = _article_parts(no, branch)
                matches = not target_no or parts == target_parts
                if matches:
                    article_no, branch_no = parts
                    label = (
                        f"제{article_no}조" + (f"의{branch_no}" if branch_no else "")
                        if article_no is not None else str(no)
                    )
                    articles.append({
                        "article_no": str(no),
                        "article_label": label,
                        "article_title": title[:200],
                        "text": " ".join(str(text or "").split())[:600],
                    })
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    if raw is not None:
        visit(raw)
    return articles[:10]


def search_admin_rules(
    query: str,
    *,
    limit: int = _DEFAULT_DISPLAY,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
) -> Dict[str, Any]:
    """Search administrative rules (행정규칙) — normalized candidates."""
    cfg = config or load_grounding_config()
    q = (query or "").strip()
    if not q:
        return _tool_error("search_admin_rules", query="", target="admrul",
                           error_type=LAW_API_NO_RESULTS)
    capped = _coerce_limit(limit)
    return _execute(
        tool="search_admin_rules",
        config=cfg,
        transport=transport,
        path=_SEARCH_PATH,
        params={"target": "admrul", "type": "JSON", "query": q, "display": str(capped)},
        target="admrul",
        query=q,
        source_type="admin_rule",
        limit=capped,
    )


def search_law_terms(
    query: str,
    *,
    limit: int = _DEFAULT_DISPLAY,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
) -> Dict[str, Any]:
    """Search legal terms (법령용어). Returns normalized term results where the
    adapter/endpoint supports it; otherwise a graceful ``law_api_no_results``."""
    cfg = config or load_grounding_config()
    q = (query or "").strip()
    if not q:
        return _tool_error("search_law_terms", query="", target="lstrm",
                           error_type=LAW_API_NO_RESULTS)
    capped = _coerce_limit(limit)
    return _execute(
        tool="search_law_terms",
        config=cfg,
        transport=transport,
        path=_SEARCH_PATH,
        params={"target": "lstrm", "type": "JSON", "query": q, "display": str(capped)},
        target="lstrm",
        query=q,
        source_type="law_term",
        limit=capped,
    )




# ---------------------------------------------------------------------------
# Official source-family adapters (typed result contract)
# ---------------------------------------------------------------------------
_TARGET_BY_SOURCE_FAMILY = {
    "statute": "law",
    "enforcement_decree": "law",
    "enforcement_rule": "law",
    "administrative_rule": "admrul",
    "legal_term": "lstrm",
}
_WIRED_SOURCE_FAMILIES = set(_TARGET_BY_SOURCE_FAMILY)
_PRECEDENT_RELATED_FAMILIES = {
    "precedent", "administrative_appeal", "legal_interpretation", "constitutional_decision",
}


def _adapter_status_from_tool_result(result: Dict[str, Any]) -> str:
    if result.get("status") == "ok" and result.get("results"):
        return SOURCE_STATUS_RESULTS_FOUND
    return _ERROR_TO_SOURCE_STATUS.get(result.get("error_type") or LAW_API_NO_RESULTS, SOURCE_STATUS_BAD_RESPONSE)


def _evidence_from_tool_item(item: Dict[str, Any], *, source_family: str, query: str, status: str, source_url: str) -> Dict[str, Any]:
    source_type = source_family if source_family in {
        "enforcement_decree", "enforcement_rule",
        "legal_interpretation", "precedent", "administrative_appeal", "constitutional_decision", "manual",
    } else str(item.get("source_type") or source_family)
    out = {
        "source_type": source_type,
        "title": str(item.get("title") or item.get("law_name") or item.get("term") or item.get("case_name") or "")[:180],
        "law_name": str(item.get("law_name") or "")[:180],
        "article": str(item.get("article") or "")[:80],
        "case_name": str(item.get("case_name") or "")[:180],
        "case_number": str(item.get("case_number") or "")[:80],
        "decision_date": str(item.get("decision_date") or item.get("enforcement_date") or "")[:40],
        "summary": str(item.get("summary") or item.get("definition") or item.get("text") or "")[:700],
        "query": query,
        "source_url": _sanitize_url(source_url or item.get("source_url") or ""),
        "retrieval_status": "ok" if status == SOURCE_STATUS_RESULTS_FOUND else status,
        "relevance": str(item.get("relevance") or "background"),
    }
    for key in ("law_id", "law_serial_no", "reference", "law_division", "rule_type", "department", "term", "definition"):
        if item.get(key) not in (None, ""):
            out[key] = item.get(key)
    return out


def _official_result_from_tool(source_family: str, query: str, tool_result: Dict[str, Any]) -> Dict[str, Any]:
    status = _adapter_status_from_tool_result(tool_result)
    source_url = _sanitize_url(tool_result.get("source_url") or "")
    items = [
        _evidence_from_tool_item(item, source_family=source_family, query=query, status=status, source_url=source_url)
        for item in (tool_result.get("results") or [])
        if isinstance(item, dict)
    ]
    return asdict(OfficialSourceResult(
        source_family=source_family,
        status=status,
        query=query,
        normalized_items=items,
        response_shape_hint=str(tool_result.get("response_shape_hint") or ""),
        parser_status=str(tool_result.get("parser_status") or ""),
        sanitized_source_url=source_url,
        error_type=str(tool_result.get("error_type") or ""),
        safe_error_message=_safe_text(tool_result.get("failure_reason") or tool_result.get("error_type") or ""),
    ))


def _official_result_from_precedent_envelope(source_family: str, query: str, envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge precedent_sources envelopes into the OfficialSourceResult shape."""
    status = str(envelope.get("status") or SOURCE_STATUS_UNSUPPORTED)
    if status == "scaffold_only":
        status = SOURCE_STATUS_UNSUPPORTED
    items: List[Dict[str, Any]] = []
    for item in envelope.get("items") or []:
        if not isinstance(item, dict) or item.get("resultKind") == "unavailable":
            continue
        grade = str(item.get("citationGrade") or "")
        items.append({
            "source_type": source_family,
            "title": str(item.get("title") or item.get("sourceName") or "")[:180],
            "case_name": str(item.get("title") or "")[:180],
            "case_number": str(item.get("caseNumber") or "")[:80],
            "decision_number": str(item.get("decisionNumber") or "")[:80],
            "decision_date": str(item.get("decisionDate") or "")[:40],
            "court_or_agency": str(item.get("courtOrAgency") or "")[:120],
            "summary": str(item.get("holdingSummary") or item.get("snippet") or "")[:700],
            "query": query,
            "source_url": _sanitize_url(item.get("url") or ""),
            "retrieval_status": "ok" if status == SOURCE_STATUS_RESULTS_FOUND else status,
            "relevance": "direct" if grade == "direct" else ("analogical" if grade in {"contextual", "background"} else "background"),
            "result_kind": item.get("resultKind") or "",
            "citation_grade": grade,
        })
    out = asdict(OfficialSourceResult(
        source_family=source_family,
        status=status,
        query=query,
        normalized_items=items,
        response_shape_hint=str(envelope.get("responseShapeHint") or ""),
        parser_status=str(envelope.get("parserStatus") or ""),
        sanitized_source_url=str(envelope.get("sanitizedSourceUrl") or ""),
        error_type=str(envelope.get("errorType") or ""),
        safe_error_message="",
    ))
    out["precedent_evidence_items"] = [
        item for item in (envelope.get("items") or [])
        if isinstance(item, dict)
    ]
    out["public_status"] = envelope.get("publicStatus") or ""
    out["live_adapter_status"] = envelope.get("liveAdapterStatus") or ""
    return out


def retrieve_official_source_family(
    source_family: str,
    query: str,
    *,
    limit: int = 3,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
) -> Dict[str, Any]:
    """Retrieve one official source family with explicit adapter status.

    Unsupported families are reported as ``unsupported`` rather than being
    collapsed into LAW_API_BAD_RESPONSE. Returned items are normalized evidence
    only; raw response bodies/payloads are never exposed.
    """
    family = (source_family or "").strip().lower()
    q = (query or "").strip()
    if family not in SOURCE_FAMILIES:
        return asdict(OfficialSourceResult(source_family=family or "unknown", status=SOURCE_STATUS_UNSUPPORTED, query=q, safe_error_message="unsupported_source_family"))
    if family in _PRECEDENT_RELATED_FAMILIES:
        from . import precedent_sources
        if family == "precedent":
            envelope = precedent_sources.search_precedents(q, limit=limit, config=config, transport=transport)
            return _official_result_from_precedent_envelope(family, q, envelope)
        envelope = precedent_sources.normalize_source_family_response(
            family,
            "",
            result_kind="unavailable",
            query=q,
            target=precedent_sources.SOURCE_FAMILY_LIST_TARGETS.get(family),
        )
        envelope["status"] = SOURCE_STATUS_UNSUPPORTED
        envelope["publicStatus"] = "unavailable"
        envelope["errorType"] = ""
        return _official_result_from_precedent_envelope(family, q, envelope)
    if family not in _WIRED_SOURCE_FAMILIES:
        return asdict(OfficialSourceResult(source_family=family, status=SOURCE_STATUS_UNSUPPORTED, query=q, safe_error_message="planned_not_wired"))
    cfg = config or load_grounding_config()
    if not cfg.law_api_configured:
        return asdict(OfficialSourceResult(source_family=family, status=SOURCE_STATUS_NOT_CONFIGURED, query=q, error_type=LAW_API_NOT_CONFIGURED, safe_error_message="not_configured"))
    if not q:
        return asdict(OfficialSourceResult(source_family=family, status=SOURCE_STATUS_NO_RESULTS, query=q, error_type=LAW_API_NO_RESULTS, safe_error_message="empty_query"))
    if family == "administrative_rule":
        tool_result = search_admin_rules(q, limit=limit, config=cfg, transport=transport)
    elif family == "legal_term":
        tool_result = search_law_terms(q, limit=limit, config=cfg, transport=transport)
    else:
        tool_result = search_laws(q, target="law", limit=limit, config=cfg, transport=transport)
    return _official_result_from_tool(family, q, tool_result)


def retrieve_planned_official_sources(
    source_plan: Dict[str, Any],
    *,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
    limit_per_family: int = 2,
    max_attempts: int = _HARD_MAX_QUERIES,
) -> Dict[str, Any]:
    families = list(source_plan.get("source_types_priority") or [])
    queries = list(source_plan.get("queries") or [])
    results: List[Dict[str, Any]] = []
    normalized: List[Dict[str, Any]] = []
    precedent_evidence_items: List[Dict[str, Any]] = []
    attempts = 0
    for idx, family in enumerate(families):
        if family == "manual":
            continue
        query = queries[min(idx, len(queries) - 1)] if queries else "출입국관리법 체류자격"
        result = retrieve_official_source_family(family, query, limit=limit_per_family, config=config, transport=transport)
        results.append(result)
        attempts += 1
        normalized.extend(result.get("normalized_items") or [])
        precedent_evidence_items.extend(result.get("precedent_evidence_items") or [])
        if attempts >= max(1, min(max_attempts, _HARD_MAX_QUERIES)):
            break
    statuses = {r["source_family"]: r["status"] for r in results}
    return {
        "source_family_results": results,
        "normalized_evidence": normalized,
        "precedent_evidence_items": precedent_evidence_items,
        "source_family_statuses": statuses,
        "source_family_result_counts": {r["source_family"]: len(r.get("normalized_items") or []) for r in results},
        "response_shape_hints": {r["source_family"]: r.get("response_shape_hint", "") for r in results},
        "parser_statuses": {r["source_family"]: r.get("parser_status", "") for r in results},
        "law_error_types": {r["source_family"]: r.get("error_type", "") for r in results},
        "sanitized_source_urls": [r.get("sanitized_source_url", "") for r in results if r.get("sanitized_source_url")],
    }

# ---------------------------------------------------------------------------
# Status / question-type detection (richer law taxonomy used for planning)
# ---------------------------------------------------------------------------
# Lookarounds (not \b) so a code is matched even when a Korean particle follows
# directly, e.g. "E-7으로", "D-2인데" — a trailing \b fails before Hangul.
_CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-H])\s*-?\s*(\d{1,2})(?![0-9])", re.IGNORECASE)


def extract_status_codes(text: str) -> List[str]:
    """Return ordered, de-duplicated visa/status codes mentioned in ``text``."""
    codes: List[str] = []
    for match in _CODE_RE.finditer(text or ""):
        code = f"{match.group(1).upper()}-{int(match.group(2))}"
        if code not in codes:
            codes.append(code)
    return codes


def _status_change_pair(text: str, codes: Sequence[str]) -> Tuple[str, str]:
    """Best-effort (source_status, target_status) extraction for changes."""
    source, target = "", ""
    pair = re.search(
        r"([A-H]-?\d{1,2})[^A-H]{0,12}?(?:에서|→|->|to)[^A-H]{0,12}?([A-H]-?\d{1,2})",
        text or "",
        flags=re.IGNORECASE,
    )
    if pair:
        source = _norm_code(pair.group(1))
        target = _norm_code(pair.group(2))
        return source, target
    # "X로/으로 ... 변경/신청/전환" → X is the target.
    tgt = re.search(
        r"([A-H]-?\d{1,2})\s*[가-힣 ]{0,8}?(?:으로|로)\b[가-힣 ]{0,12}?(?:변경|바꾸|전환|신청|진행)",
        text or "",
        flags=re.IGNORECASE,
    )
    if tgt:
        target = _norm_code(tgt.group(1))
    if not target:
        # "X 신청/취득/부여" (applying FOR status X) → X is the target.
        apply = re.search(
            r"([A-H]-?\d{1,2})\s*[가-힣 ]{0,4}?(?:신청|취득|부여|전환)",
            text or "",
            flags=re.IGNORECASE,
        )
        if apply:
            target = _norm_code(apply.group(1))
    if not source and codes:
        for code in codes:
            if code != target:
                source = code
                break
    return source, target


def _norm_code(raw: str) -> str:
    match = _CODE_RE.search(raw or "")
    if not match:
        return (raw or "").upper()
    return f"{match.group(1).upper()}-{int(match.group(2))}"


# Richer law question-type taxonomy (used for planning + the evidence pack).
# Kept SEPARATE from answer_quality.classify_question_type (which feeds the
# HTTP ``question_type_detected`` field and has a stable 6-value contract).
LQ_ACTIVITY_ON_STATUS = "activity_on_status"
LQ_DOCUMENTS_NEEDED = "documents_needed"
LQ_STATUS_CHANGE = "status_change"
LQ_DEADLINE_OR_REPORT = "deadline_or_report"
LQ_HIGH_RISK_EXCEPTION = "high_risk_exception"
LQ_PROCEDURE = "procedure"
LQ_PROCEDURE_OR_CODE_LOOKUP = "procedure_or_code_lookup"
LQ_COMPARISON = "comparison"
LQ_NATIONALITY = "nationality_or_naturalization"
LQ_REFUGEE = "refugee_context"
LQ_GENERAL_LEGAL = "general_legal"
LQ_GENERAL = "general"

# Question types where court precedent (판례) is genuinely informative. Routine
# document/extension/procedure lookups are intentionally excluded so precedent
# retrieval (an extra network call) only fires where case law adds value.
_PRECEDENT_WARRANTED_QUESTION_TYPES = frozenset({
    LQ_ACTIVITY_ON_STATUS,
    LQ_STATUS_CHANGE,
    LQ_HIGH_RISK_EXCEPTION,
    LQ_DEADLINE_OR_REPORT,
    LQ_NATIONALITY,
    LQ_REFUGEE,
})


def _signal_flags(text: str) -> Dict[str, bool]:
    low = (text or "").lower()
    # Code-based signals use extract_status_codes (lookaround-based) so a code
    # followed by a Korean particle (e.g. "H-1으로") is still detected.
    codes = set(extract_status_codes(text))

    def has(*needles: str) -> bool:
        return any(n.lower() in low for n in needles)

    return {
        "study": has("유학", "수강", "계절학기", "학기", "수업", "강의", "어학", "어학연수", "휴학", "복학",
                     "학점", "인턴", "course", "study", "studying", "class", "semester", "enroll", "lecture"),
        "work_holiday": has("관광취업", "워킹홀리데이", "워홀", "working holiday") or ("H-1" in codes),
        "employment": has("취업", "근무처", "이직", "직장", "아르바이트", "알바", "부업", "side job",
                          "part-time", "part time", "employ", "work", "job", "freelance", "프리랜서", "intern", "인턴", "인턴십"),
        "overseas_korean": has("재외동포", "국적상실", "방문취업", "거소신고", "국내거소") or bool({"F-4", "H-2"} & codes),
        "family": has("결혼", "이혼", "사망", "가정폭력", "별거", "양육", "배우자", "혼인", "생계",
                      "divorce", "marriage", "spouse", "widow", "domestic violence") or ("F-6" in codes),
        "humanitarian": has("인도적", "치료", "소송", "litigation", "medical", "humanitarian") or ("G-1" in codes),
        "refugee": has("난민", "refugee", "asylum"),
        "short_term": has("사증면제", "무비자", "단기", "short-term", "short term", "visa-free", "visa free") or bool({"B-1", "B-2", "C-1", "C-3", "C-4"} & codes),
        "reporting": has("신고", "외국인등록", "등록", "거소신고", "체류지", "여권", "재입국", "report", "register", "registration", "re-entry", "reentry"),
        "reentry": has("재입국", "re-entry", "reentry", "출국했다", "다시 들어"),
        "urgent": has("도과", "지났", "초과체류", "불법체류", "강제퇴거", "출국명령", "범칙금", "과태료", "취소", "벌금",
                      "overstay", "expired", "deport", "penalt", "fine", "cancel"),
        "nationality": has("귀화", "국적", "naturaliz", "nationality", "citizenship"),
        "jobcode": has("직종코드", "직종 코드", "job code", "occupation code", "직업코드"),
        "documents": has("서류", "구비서류", "제출서류", "필요한 서류", "document", "documents", "필요서류", "材料", "文件"),
        "comparison": has("차이", "다른가요", "어떻게 다른", "vs", "비교", "difference", "differ", "compare"),
        "change": has("변경", "바꾸", "전환", "change", "switch", "transfer"),
        "deadline": has("기한", "며칠", "언제까지", "언제", "deadline", "grace period", "how many days", "due"),
        "activity_question": has("할 수 있", "해도 되", "가능", "되나요", "can i", "may i", "am i allowed", "able to", "할수있"),
    }


def classify_law_question_type(
    question: str,
    visa_code: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify a question into the richer law taxonomy + risk level.

    Deterministic. Returns ``{"question_type", "risk_level", "signals"}``.
    Priority is risk-first so urgent/exception questions are never mislabeled
    as casual activity questions.
    """
    signals = _signal_flags(question)
    tt = (task_type or "").lower()

    # 1. Urgent / overstay / cancellation risk (highest).
    if signals["urgent"] or tt in {"overstay_deadline_risk"}:
        return {"question_type": LQ_HIGH_RISK_EXCEPTION, "risk_level": "high", "signals": signals}

    # 1b. Academic status maintenance (휴학/자퇴/제적) — status-maintenance risk.
    if tt == "academic_status_change" or any(
        w in (question or "") for w in ("휴학", "자퇴", "제적", "정학")
    ):
        return {"question_type": LQ_HIGH_RISK_EXCEPTION, "risk_level": "medium", "signals": signals}

    # 2. Family / marriage exceptions — ONLY for genuine exception circumstances
    # (divorce / death / domestic violence / separation), NOT a routine F-6
    # extension, which stays a documents/extension question.
    _family_exception_words = (
        "이혼", "사망", "가정폭력", "별거", "사별", "divorce", "death", "widow",
        "passed away", "domestic violence",
    )
    if tt == "marriage_divorce_status_change" or any(
        w in (question or "").lower() for w in _family_exception_words
    ):
        return {"question_type": LQ_HIGH_RISK_EXCEPTION, "risk_level": "high", "signals": signals}

    # 3. Refugee context.
    if signals["refugee"]:
        return {"question_type": LQ_REFUGEE, "risk_level": "high", "signals": signals}

    # 4. Nationality / naturalization (unless it is really an F-4 status change).
    if signals["nationality"] and not (signals["overseas_korean"] and signals["change"]):
        if "귀화" in (question or "") or "naturaliz" in (question or "").lower() or (
            signals["nationality"] and not signals["overseas_korean"]
        ):
            return {"question_type": LQ_NATIONALITY, "risk_level": "medium", "signals": signals}

    # 5. Humanitarian / medical / litigation (G-1 etc.).
    if signals["humanitarian"]:
        return {"question_type": LQ_HIGH_RISK_EXCEPTION, "risk_level": "high", "signals": signals}

    # 6. Job/occupation code lookup.
    if signals["jobcode"]:
        return {"question_type": LQ_PROCEDURE_OR_CODE_LOOKUP, "risk_level": "low", "signals": signals}

    # 7. Documents.
    if signals["documents"]:
        return {"question_type": LQ_DOCUMENTS_NEEDED, "risk_level": "low", "signals": signals}

    # 8. Status change.
    codes = extract_status_codes(question)
    if (signals["change"] and (len(codes) >= 1)) or tt in {"status_change"} or (
        re.search(r"[A-H]-?\d{1,2}\s*(?:에서|to|->|→)", question or "", re.IGNORECASE)
    ):
        return {"question_type": LQ_STATUS_CHANGE, "risk_level": "high", "signals": signals}

    # 9. Comparison.
    if signals["comparison"] and len(codes) >= 2:
        return {"question_type": LQ_COMPARISON, "risk_level": "low", "signals": signals}

    # 10. Deadline / reporting.
    if signals["reporting"] or signals["deadline"] or tt in {
        "address_report", "passport_info_report", "workplace_change", "foreigner_registration",
    }:
        return {"question_type": LQ_DEADLINE_OR_REPORT, "risk_level": "medium", "signals": signals}

    # 11. Activity on status.
    if signals["activity_question"] or signals["study"] or signals["employment"] or tt in {
        "activities_outside_status",
    }:
        return {"question_type": LQ_ACTIVITY_ON_STATUS, "risk_level": "medium", "signals": signals}

    # 12. Procedure ("어떤 절차") fallback when a procedure word is present.
    if any(w in (question or "") for w in ("절차", "procedure", "process")):
        return {"question_type": LQ_PROCEDURE, "risk_level": "low", "signals": signals}

    # 13. Otherwise: legal-general if law intent, else general.
    if should_attempt_law_grounding(question).get("should_attempt"):
        return {"question_type": LQ_GENERAL_LEGAL, "risk_level": "low", "signals": signals}
    return {"question_type": LQ_GENERAL, "risk_level": "low", "signals": signals}


# ---------------------------------------------------------------------------
# Query planning (Part C) — deterministic, small, high-signal Korean queries
# ---------------------------------------------------------------------------
_CATEGORY_QUERIES: Dict[str, List[str]] = {
    "activity_scope": [
        "출입국관리법 체류자격외활동 활동범위",
        "체류자격외활동 허가 활동범위 체류자격",
    ],
    "status_change": [
        "출입국관리법 체류자격 변경허가 체류자격 변경",
    ],
    "student_activity": [
        "체류자격 변경 유학 D-2 D-4",
        "유학 체류자격 활동범위",
        "출입국관리법 체류자격 변경허가",
    ],
    "working_holiday": [
        "출입국관리법 시행령 별표 체류자격 관광취업",
        "관광취업 H-1 활동범위",
        "체류자격외활동 허가",
        "출입국관리법 체류자격외활동허가",
    ],
    "employment": [
        "취업활동 인턴십 근무처 변경 근무처 추가 신고",
        "체류자격외활동 특정활동 허가",
        "구직 취업활동 활동범위 체류자격",
    ],
    "overseas_korean": [
        "재외동포 국내거소신고 체류자격 변경",
        "재외동포의 출입국과 법적 지위에 관한 법률 방문취업",
        "국적상실 재외동포 체류자격 활동범위",
    ],
    "family_marriage": [
        "결혼이민 체류기간 연장 체류자격 유지",
        "이혼 사망 가정폭력 양육 생계 체류자격",
    ],
    "humanitarian": [
        "출입국관리법 시행령 기타 G-1 인도적 사유 체류",
        "치료 소송 난민 체류기간 연장 체류자격",
    ],
    "refugee": [
        "난민법 난민신청 G-1 체류자격",
        "난민 인정 체류자격 난민법",
    ],
    "short_term": [
        "사증면제 단기방문 단기취업 활동범위",
        "단기 취업활동 유학 체류자격 활동범위",
    ],
    "reporting_deadline": [
        "외국인등록 체류지 변경 신고의무",
        "근무처 변경 여권 변경 신고",
        "재입국허가 체류기간 신고",
    ],
    "urgent_risk": [
        "체류기간 도과 출국 범칙금 과태료",
        "체류자격 취소 강제퇴거 출국명령 체류기간",
    ],
    "reentry": [
        "출입국관리법 재입국허가 출국 재입국 체류자격",
    ],
    "documents_support": [
        "출입국관리법 시행규칙 체류자격 첨부서류 신청",
    ],
    "nationality": [
        "국적법 귀화 요건 절차",
        "국적법 국적 취득 상실 신고",
    ],
    "general_legal": [
        "출입국관리법 체류자격 활동범위 체류자격외활동",
    ],
}


def _categories_for(question_type: str, signals: Dict[str, bool], visa_code: Optional[str]) -> List[str]:
    """Ordered category selection for the planner (deterministic)."""
    cats: List[str] = []

    def add(*names: str) -> None:
        for name in names:
            if name not in cats:
                cats.append(name)

    if question_type == LQ_HIGH_RISK_EXCEPTION:
        if signals["urgent"]:
            add("urgent_risk")
        if signals["family"]:
            add("family_marriage")
        if signals["humanitarian"]:
            add("humanitarian")
        if signals["refugee"]:
            add("refugee")
        add("status_change", "activity_scope")
    elif question_type == LQ_REFUGEE:
        add("refugee", "humanitarian")
    elif question_type == LQ_NATIONALITY:
        add("nationality")
    elif question_type == LQ_STATUS_CHANGE:
        add("status_change")
        if signals["overseas_korean"]:
            add("overseas_korean")
        if signals["study"]:
            add("student_activity")
        if signals["employment"]:
            add("employment")
        if signals["short_term"]:
            add("short_term")
    elif question_type == LQ_DOCUMENTS_NEEDED:
        # Manual evidence is primary for documents; law is supporting only.
        add("documents_support")
        if signals["change"]:
            add("status_change")
    elif question_type == LQ_DEADLINE_OR_REPORT:
        add("reporting_deadline")
        if signals["overseas_korean"]:
            add("overseas_korean")
        if signals["reentry"]:
            add("reentry")
        if signals["employment"]:
            add("employment")
    elif question_type in (LQ_PROCEDURE, LQ_PROCEDURE_OR_CODE_LOOKUP):
        if signals["reentry"]:
            add("reentry")
        if signals["employment"]:
            add("employment")
        add("status_change", "general_legal")
    elif question_type == LQ_COMPARISON:
        if signals["short_term"]:
            add("short_term")
        add("activity_scope")
    elif question_type == LQ_ACTIVITY_ON_STATUS:
        if signals["work_holiday"]:
            add("working_holiday")
        if signals["study"]:
            add("student_activity")
        if signals["employment"]:
            add("employment")
        if signals["overseas_korean"]:
            add("overseas_korean")
        if signals["short_term"]:
            add("short_term")
        add("activity_scope")
    else:  # general_legal / general
        if signals["reporting"]:
            add("reporting_deadline")
        add("general_legal", "activity_scope")

    if not cats:
        add("general_legal")
    return cats


def plan_law_queries(
    question: str,
    *,
    visa_code: Optional[str] = None,
    task_type: Optional[str] = None,
    question_type: Optional[str] = None,
    max_queries: int = _DEFAULT_MAX_QUERIES,
) -> Dict[str, Any]:
    """Produce a small, deterministic set of high-signal Korean law queries.

    Never issues a network call. The set is intentionally capped (default 3-5)
    so a single answer never fans out into a burst of API requests. Planned
    queries are preserved verbatim in the evidence pack / debug metadata.
    """
    classified = classify_law_question_type(question, visa_code, task_type)
    qtype = question_type or classified["question_type"]
    signals = classified["signals"]
    cap = max(1, min(int(max_queries or _DEFAULT_MAX_QUERIES), _HARD_MAX_QUERIES))

    categories = _categories_for(qtype, signals, visa_code)
    queries: List[str] = []
    used_categories: List[str] = []
    for category in categories:
        if len(queries) >= cap:
            break
        used_categories.append(category)
        for query in _CATEGORY_QUERIES.get(category, []):
            if len(queries) >= cap:
                break
            if query not in queries:
                queries.append(query)

    return {
        "question_type": qtype,
        "risk_level": classified["risk_level"],
        "queries": queries,
        "categories": used_categories,
        "max_queries": cap,
        "visa_code": (visa_code or "").upper() or None,
    }




# ---------------------------------------------------------------------------
# Official source-family planning (legal-analysis guidance engine)
# ---------------------------------------------------------------------------
SOURCE_FAMILIES = (
    "manual",
    "statute",
    "enforcement_decree",
    "enforcement_rule",
    "administrative_rule",
    "legal_interpretation",
    "precedent",
    "administrative_appeal",
    "constitutional_decision",
    "legal_term",
    "intelligent_search",
)
_SUPPORTED_SOURCE_FAMILIES = {
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_term",
}


def _source_families_for(question_type: str, signals: Dict[str, bool]) -> List[str]:
    families: List[str] = []

    def add(*names: str) -> None:
        for name in names:
            if name in SOURCE_FAMILIES and name not in families:
                families.append(name)

    if question_type == LQ_ACTIVITY_ON_STATUS:
        add("statute", "enforcement_decree", "enforcement_rule", "legal_interpretation", "administrative_appeal")
        if signals.get("study"):
            add("legal_term")
    elif question_type == LQ_STATUS_CHANGE:
        add("manual", "statute", "enforcement_decree", "legal_interpretation", "administrative_appeal")
    elif question_type == LQ_DOCUMENTS_NEEDED:
        add("manual", "statute", "enforcement_rule")
    elif question_type == LQ_DEADLINE_OR_REPORT:
        add("statute", "enforcement_decree", "enforcement_rule", "manual", "administrative_rule")
    elif question_type == LQ_HIGH_RISK_EXCEPTION:
        add("statute", "enforcement_decree", "enforcement_rule", "legal_interpretation", "administrative_appeal")
        if signals.get("urgent") or signals.get("family"):
            add("precedent")
    elif question_type in {LQ_NATIONALITY, LQ_REFUGEE}:
        add("statute", "enforcement_decree", "enforcement_rule", "legal_interpretation")
    else:
        add("manual", "statute", "enforcement_decree", "enforcement_rule", "legal_term")
    return families


def plan_source_families(
    question: str,
    *,
    visa_code: Optional[str] = None,
    task_type: Optional[str] = None,
    question_type: Optional[str] = None,
    manual_present: bool = False,
    law_sources: Optional[Sequence[Dict[str, Any]]] = None,
    law_api_attempted: bool = False,
    law_grounding_status: str = "not_attempted",
) -> Dict[str, Any]:
    """Plan and status official source families without requiring all to work.

    The Open Law API tooling currently supports statute-family search through
    target=law, administrative rules through target=admrul, and legal terms
    through target=lstrm.  Other official families are represented as safe
    scaffolding and marked unsupported unless later wired.
    """
    classified = classify_law_question_type(question, visa_code, task_type)
    qtype = question_type or classified["question_type"]
    selected = _source_families_for(qtype, classified["signals"])
    law_sources = list(law_sources or [])
    returned_types = set()
    if law_sources:
        for src in law_sources:
            st = str(src.get("source_type") or src.get("target") or "law").lower()
            if st in {"law", "statute"}:
                returned_types.update({"statute", "enforcement_decree", "enforcement_rule"})
            elif st in {"admin_rule", "admrul", "administrative_rule"}:
                returned_types.add("administrative_rule")
            elif st in {"law_term", "lstrm", "legal_term"}:
                returned_types.add("legal_term")

    statuses: Dict[str, str] = {}
    for family in SOURCE_FAMILIES:
        if family == "manual":
            if manual_present:
                statuses[family] = "results_found"
            elif family in selected:
                statuses[family] = "attempted"
            else:
                statuses[family] = "not_attempted"
            continue
        if family not in selected:
            statuses[family] = "not_attempted"
        elif family not in _SUPPORTED_SOURCE_FAMILIES:
            statuses[family] = "unsupported"
        elif family in returned_types:
            statuses[family] = "results_found"
        elif law_api_attempted:
            statuses[family] = "no_results" if law_grounding_status != "unavailable" else "unavailable"
        else:
            statuses[family] = "attempted"

    attempted = [f for f in selected if statuses.get(f) in {"attempted", "unavailable", "no_results", "results_found", "parse_error"}]
    return {
        "question_type": qtype,
        "statuses": statuses,
        "source_types_priority": selected,
        "source_types_attempted": attempted,
        "source_types_returned": [f for f in SOURCE_FAMILIES if statuses.get(f) == "results_found"],
        "unsupported_source_types": [f for f in selected if statuses.get(f) == "unsupported"],
    }

# ---------------------------------------------------------------------------
# Localized official-confirmation questions (richer than the EN-canonical set
# in answer_quality; used only inside the evidence pack so the HTTP contract
# field stays unchanged).
# ---------------------------------------------------------------------------
_H1_STUDY_CONFIRM = {
    "ko": [
        "학점이 인정되는 과정인가요? (학점 인정)",
        "정규과정 여부가 어떻게 되나요?",
        "수업 기간/시간은 어느 정도인가요?",
        "체류 목적이 학업 중심인가요?",
        "H-1 취업 병행 여부가 있나요?",
        "대학이 D-2 / D-4 등 다른 체류자격을 요구하나요?",
        "체류자격외활동 허가 또는 체류자격 변경이 필요한지 확인이 필요합니다.",
    ],
    "en": [
        "Is the course credit-bearing?",
        "Is it degree-related / part of a regular program?",
        "How many weeks / hours is it?",
        "Is study the main purpose of your stay?",
        "Will you also work under H-1 at the same time?",
        "Does the university require D-2 / D-4 or another status?",
        "Would this require permission for activities outside status or a change of status?",
    ],
}


def localized_official_confirmation_questions(
    question_type: str,
    *,
    lang: str = "ko",
    is_study: bool = False,
    source_status: str = "",
    target_status: str = "",
) -> List[str]:
    """Localized confirmation questions for the evidence pack (ko/en focus)."""
    norm = "en" if (lang or "").lower().startswith("en") else "ko"

    if question_type == LQ_ACTIVITY_ON_STATUS and is_study:
        return list(_H1_STUDY_CONFIRM[norm])

    ko = {
        LQ_ACTIVITY_ON_STATUS: [
            "현재 체류자격의 활동범위 안에 있는 활동인가요?",
            "체류자격외활동에 해당하나요?",
            "사전 허가나 체류자격 변경이 필요한가요?",
            "고용주·근무형태·근무시간·보수 조건은 어떻게 되나요?",
        ],
        LQ_STATUS_CHANGE: [
            f"현재 체류자격({source_status or '현재 자격'})과 세부 코드가 무엇인가요?",
            "어떤 경로(재외공관 사증 / 국내 변경)로 진행하나요?",
            "남은 체류기간은 얼마나 되나요?",
            f"변경하려는 체류자격({target_status or '목표 자격'})의 요건을 충족하나요?",
        ],
        LQ_DOCUMENTS_NEEDED: [
            "정확히 어떤 절차와 세부 코드에 해당하나요?",
            "상황에 따라 조건부로 요구되는 서류가 있나요?",
            "관할 출입국·외국인청에서 추가로 요구하는 서류가 있나요?",
        ],
        LQ_DEADLINE_OR_REPORT: [
            "신고 기한이 시작되는 사건(입국·변경·주소변경 등)은 무엇인가요?",
            "현재 체류자격 기준 정확한 기한은 며칠인가요?",
            "신고는 어디서·어떻게(하이코리아/방문) 하나요?",
        ],
        LQ_HIGH_RISK_EXCEPTION: [
            "현재 체류자격과 남은 체류기간은 어떻게 되나요?",
            "어떤 사정이 언제 발생했나요?",
            "관련 증빙(서류·기록)은 무엇을 준비할 수 있나요?",
            "즉시 1345 또는 관할 출입국·외국인청 확인이 필요합니다.",
        ],
        LQ_PROCEDURE: [
            "현재 체류자격과 등록 상태는 어떻게 되나요?",
            "진행하려는 절차의 정확한 종류는 무엇인가요?",
            "관할 출입국·외국인청에서 요구하는 추가 절차가 있나요?",
        ],
        LQ_PROCEDURE_OR_CODE_LOOKUP: [
            "해당 직종·코드의 정확한 기준은 무엇인가요?",
            "직종 적격 여부는 관할 출입국·외국인청/하이코리아 확인이 필요합니다.",
        ],
        LQ_NATIONALITY: [
            "신청하려는 국적 절차(귀화 등)의 정확한 종류는 무엇인가요?",
            "Paradiso는 체류·거주 중심이며 국적 세부 요건은 확인이 필요합니다.",
        ],
        LQ_REFUGEE: [
            "현재 난민 절차 단계와 체류자격은 어떻게 되나요?",
            "관련 법적 조력 및 관할 기관 확인이 필요합니다.",
        ],
        LQ_COMPARISON: [
            "두 체류자격의 정확한 활동범위 기준은 무엇인가요?",
            "본인 상황에 맞는 자격 여부는 관할 기관 확인이 필요합니다.",
        ],
    }
    en = {
        LQ_ACTIVITY_ON_STATUS: [
            "Is the activity within the permitted scope of activities for your status?",
            "Does it count as activities outside the scope of status?",
            "Do you need prior permission or a change of sojourn status?",
            "What are the employer, work type, hours, and compensation?",
        ],
        LQ_STATUS_CHANGE: [
            "What is your current sojourn status and sub-code?",
            "Which route applies (consular visa vs in-country change)?",
            "How long is your remaining period of stay?",
            "Do you meet the requirements for the target status?",
        ],
        LQ_DOCUMENTS_NEEDED: [
            "Which exact procedure and sub-code applies to your case?",
            "Are any documents conditional on your specific situation?",
            "Does the competent immigration office require anything additional?",
        ],
        LQ_DEADLINE_OR_REPORT: [
            "What event starts the deadline (entry, change, address change)?",
            "What is the confirmed time limit for your status?",
            "Where and how must the report be filed (HiKorea / in person)?",
        ],
        LQ_HIGH_RISK_EXCEPTION: [
            "What is your current status and remaining stay?",
            "What changed in your situation, and when?",
            "What supporting evidence can you prepare?",
            "Confirm urgently with 1345 or the competent immigration office.",
        ],
        LQ_PROCEDURE: [
            "What are your current status and registration state?",
            "What exact procedure are you trying to complete?",
            "Does the competent office require any extra steps?",
        ],
        LQ_PROCEDURE_OR_CODE_LOOKUP: [
            "What is the exact occupation/code standard involved?",
            "Occupation eligibility must be confirmed with HiKorea / the office.",
        ],
        LQ_NATIONALITY: [
            "Which nationality procedure (e.g. naturalization) applies?",
            "Paradiso focuses on residence; nationality specifics need confirmation.",
        ],
        LQ_REFUGEE: [
            "What stage is the refugee process at, and what is your status?",
            "Legal assistance and the competent authority should be confirmed.",
        ],
        LQ_COMPARISON: [
            "What is the exact permitted scope for each status?",
            "Whether either fits your case must be confirmed with the office.",
        ],
    }
    table = en if norm == "en" else ko
    return list(table.get(question_type, []))


# ---------------------------------------------------------------------------
# Manual evidence normalization
# ---------------------------------------------------------------------------
def _normalize_manual_sources(manual_evidence: Optional[Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split provided manual evidence into (direct, related) normalized lists.

    Accepts either a dict ``{"direct": [...], "related": [...]}`` or a flat list
    of backend ``grounding_sources`` (all treated as direct). Never fabricates.
    """
    direct: List[Dict[str, Any]] = []
    related: List[Dict[str, Any]] = []
    if not manual_evidence:
        return direct, related
    if isinstance(manual_evidence, dict):
        direct = list(manual_evidence.get("direct") or [])
        related = list(manual_evidence.get("related") or [])
    elif isinstance(manual_evidence, list):
        direct = list(manual_evidence)
    return direct, related


# ---------------------------------------------------------------------------
# Evidence pack (Part D) — the orchestrated, structured output
# ---------------------------------------------------------------------------
def build_law_evidence_pack(
    question: str,
    *,
    visa_code: Optional[str] = None,
    task_type: Optional[str] = None,
    lang: str = "",
    manual_evidence: Optional[Any] = None,
    manual_present: bool = False,
    structured_present: bool = False,
    procedure_variant_present: bool = False,
    config: Optional[GroundingConfig] = None,
    transport: Optional[LawTransport] = None,
    law_context: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, Any]] = None,
    max_queries: int = _DEFAULT_MAX_QUERIES,
    retrieve: Optional[bool] = None,
) -> Dict[str, Any]:
    """Combine intent → plan → retrieval → normalization → source confidence.

    Returns a flat, JSON-serializable, secret-free pack. It never raises: a law
    API failure downgrades source confidence and records a typed error instead
    of crashing. Raw API payloads are NOT included verbatim; the LLM-facing
    summary is normalized and trimmed.
    """
    cfg = config or load_grounding_config()
    text = (question or "").strip()
    intent = should_attempt_law_grounding(text)
    law_intent = bool(intent.get("should_attempt"))

    classified = classify_law_question_type(text, visa_code, task_type)
    question_type = classified["question_type"]
    risk_level = classified["risk_level"]
    signals = classified["signals"]

    immigration_facts = extract_immigration_facts(text, visa_code=visa_code)
    legal_issue_types = classify_legal_issue_types(text, immigration_facts)
    # Generalized, structured evidence query plan (ontology-driven). Each entry
    # carries its source family, status-role anchor, evidence goal and reason —
    # so the plan is auditable and never a per-visa hardcode (Parts A/B/C).
    evidence_query_plan = plan_evidence_queries(
        immigration_facts, legal_issue_types,
        activity_types=immigration_facts.get("proposed_activities"),
        max_queries=max_queries,
    )
    codes = [c for c in [
        immigration_facts.get("previous_status"),
        immigration_facts.get("current_status"),
        immigration_facts.get("target_status"),
    ] if c]
    for c in extract_status_codes(text):
        if c not in codes:
            codes.append(c)
    source_status = immigration_facts.get("previous_status") or ""
    target_status = immigration_facts.get("target_status") or ""
    if not (source_status or target_status):
        source_status, target_status = _status_change_pair(text, codes)
    related_statuses = detect_related_statuses(text, visa_code, task_type)

    initial_source_plan = build_generalized_source_plan(
        text, immigration_facts, legal_issue_types, max_queries=max_queries,
    )
    legacy_plan = plan_law_queries(
        text, visa_code=visa_code, task_type=task_type,
        question_type=question_type, max_queries=max_queries,
    )
    planned_queries = list(dict.fromkeys([*legacy_plan.get("queries", []), *initial_source_plan.get("queries", [])]))[:max(1, min(max_queries, _HARD_MAX_QUERIES))]

    # --- Retrieval (single network seam; never required in tests) ----------
    law_sources: List[Dict[str, Any]] = []
    law_queries_attempted: List[str] = []
    law_api_attempted = False
    law_grounding_error = ""
    law_grounding_warnings: List[str] = []
    context_used_hint = False
    source_family_retrieval: Dict[str, Any] = {
        "source_family_results": [],
        "normalized_evidence": [],
        "source_family_statuses": {},
        "source_family_result_counts": {},
        "response_shape_hints": {},
        "parser_statuses": {},
        "law_error_types": {},
        "sanitized_source_urls": [],
    }

    if law_context is not None:
        # Reuse already-fetched results (no duplicate live call).
        law_api_attempted = bool(law_context.get("attempted"))
        context_used_hint = bool(law_context.get("law_grounding_used"))
        for candidate in (law_context.get("law_grounding") or []):
            normalized = _normalize_candidate(candidate, "law") if isinstance(candidate, dict) else None
            if normalized:
                law_sources.append(normalized)
        law_queries_attempted = list(law_context.get("law_search_queries") or [])
        if not law_queries_attempted and law_context.get("law_search_query"):
            law_queries_attempted = [law_context.get("law_search_query", "")]
        law_grounding_warnings = list(law_context.get("grounding_warnings") or [])
        law_grounding_error = law_context.get("error_type", "") or law_context.get("law_grounding_error", "") or ""
        # Derive a granular statute-family status from the single reused law call
        # so the source panel / developer diagnostics show a real per-family
        # status (statute: no_results / official_error / bad_response / ...)
        # instead of collapsing everything into one dominant LAW_API_BAD_RESPONSE.
        if law_api_attempted:
            ctx_status = (
                SOURCE_STATUS_RESULTS_FOUND if context_used_hint and law_sources
                else _ERROR_TO_SOURCE_STATUS.get(law_grounding_error or LAW_API_NO_RESULTS, SOURCE_STATUS_NO_RESULTS)
            )
            source_family_retrieval["source_family_statuses"] = {"statute": ctx_status}
            source_family_retrieval["parser_statuses"] = {"statute": law_context.get("parser_status", "")}
            source_family_retrieval["response_shape_hints"] = {"statute": law_context.get("response_shape_hint", "")}
            source_family_retrieval["law_error_types"] = {"statute": law_grounding_error or ""}
            source_family_retrieval["source_family_result_counts"] = {"statute": len(law_sources)}
    else:
        should_retrieve = retrieve if retrieve is not None else (
            law_intent and cfg.mode in {"audit", "enabled"}
        )
        if should_retrieve:
            law_api_attempted = True
            if not cfg.law_api_configured:
                law_grounding_error = LAW_API_NOT_CONFIGURED
                law_grounding_warnings.append("SOURCE_UNAVAILABLE")
            else:
                source_family_retrieval = retrieve_planned_official_sources(
                    initial_source_plan, config=cfg, transport=transport,
                    limit_per_family=max(1, min(cfg_display(cfg), 3)),
                    max_attempts=max_queries,
                )
                law_sources.extend(source_family_retrieval.get("normalized_evidence") or [])
                law_queries_attempted = [
                    r.get("query", "") for r in source_family_retrieval.get("source_family_results", []) if r.get("query")
                ]
                for result in source_family_retrieval.get("source_family_results", []):
                    if result.get("error_type") and not law_grounding_error:
                        law_grounding_error = result.get("error_type")
                # Trim/dedupe normalized law sources for a compact pack.
                law_sources = _dedupe_sources(law_sources)[:_HARD_MAX_QUERIES]
                if not law_sources and not law_grounding_error:
                    law_grounding_error = LAW_API_NO_RESULTS

    # --- Precedent (판례) best-effort retrieval -----------------------------
    # Court precedent is CONTEXTUAL evidence only: list-search results are never
    # presented as verbatim citations (the normalizer grades them accordingly).
    # It is fetched as a separate best-effort step so it never blocks or breaks
    # the statute path — any failure simply leaves the precedent bucket empty.
    # Gated on real legal intent + an enabled mode + a configured credential, and
    # limited to question types where case law genuinely helps. When no credential
    # is present this short-circuits without any network call (no latency cost).
    precedent_warranted = (
        law_intent
        and cfg.mode in {"audit", "enabled"}
        and cfg.law_api_configured
        and question_type in _PRECEDENT_WARRANTED_QUESTION_TYPES
    )
    already_have_precedent = bool(source_family_retrieval.get("precedent_evidence_items"))
    if precedent_warranted and not already_have_precedent and retrieve is not False:
        try:
            prec_query = (
                (law_queries_attempted[0] if law_queries_attempted else "")
                or (planned_queries[0] if planned_queries else text)
            )
            prec_result = retrieve_official_source_family(
                "precedent", prec_query,
                limit=max(1, min(cfg_display(cfg), 3)),
                config=cfg, transport=transport,
            )
            prec_items = prec_result.get("precedent_evidence_items") or []
            if prec_items:
                source_family_retrieval["precedent_evidence_items"] = prec_items
                fam_statuses = dict(source_family_retrieval.get("source_family_statuses") or {})
                fam_statuses["precedent"] = prec_result.get("status", "")
                source_family_retrieval["source_family_statuses"] = fam_statuses
        except Exception:  # pragma: no cover - precedent must never break the pack
            pass

    law_grounding_used = bool(law_sources) or context_used_hint

    # --- Grounding status taxonomy -----------------------------------------
    if not law_intent:
        law_grounding_status = "not_attempted"
    elif cfg.mode == "disabled":
        law_grounding_status = "disabled"
        if "LAW_GROUNDING_DISABLED" not in law_grounding_warnings:
            law_grounding_warnings.append("LAW_GROUNDING_DISABLED")
    elif law_grounding_used:
        law_grounding_status = "used"
    elif law_api_attempted:
        law_grounding_status = "unavailable"
    else:
        law_grounding_status = "not_attempted"

    manual_grounding_status = "present" if (manual_present or structured_present) else "absent"
    direct_manual_sources, related_manual_sources = _normalize_manual_sources(manual_evidence)
    manual_to_law_fallback_used = (
        not (manual_present or structured_present)
        and law_intent
        and cfg.mode in {"audit", "enabled"}
    )

    # --- Source confidence (single source of truth = answer_quality) -------
    if quality is None:
        quality = classify_answer_quality(
            prompt=text,
            visa_code=visa_code,
            task_type=task_type,
            manual_grounding_present=manual_present,
            structured_requirements_present=structured_present,
            procedure_variant_present=procedure_variant_present,
            law_grounding_used=law_grounding_used,
            law_grounding_status=law_grounding_status,
            manual_to_law_fallback_used=manual_to_law_fallback_used,
            law_intent=law_intent,
        )

    is_study = bool(signals.get("study"))
    localized_confirm = localized_official_confirmation_questions(
        question_type, lang=lang or "ko", is_study=is_study,
        source_status=source_status, target_status=target_status,
    )
    source_type_plan = build_generalized_source_plan(
        text,
        immigration_facts,
        legal_issue_types,
        manual_present=(manual_present or structured_present),
        law_sources=law_sources,
        law_api_attempted=law_api_attempted,
        law_grounding_status=law_grounding_status,
        max_queries=max_queries,
    )
    if source_family_retrieval.get("source_family_statuses"):
        merged_statuses = dict(source_type_plan.get("statuses") or {})
        merged_statuses.update(source_family_retrieval.get("source_family_statuses") or {})
        source_type_plan["statuses"] = merged_statuses
        source_type_plan["source_family_statuses"] = merged_statuses
        attempted_families = list(dict.fromkeys([
            *(source_type_plan.get("source_types_attempted") or []),
            *source_family_retrieval.get("source_family_statuses", {}).keys(),
        ]))
        source_type_plan["source_types_attempted"] = attempted_families
        source_type_plan["source_families_attempted"] = attempted_families
        returned_families = [f for f, st in merged_statuses.items() if st == SOURCE_STATUS_RESULTS_FOUND]
        source_type_plan["source_types_returned"] = returned_families
        source_type_plan["source_families_returned"] = returned_families
    legal_analysis = build_legal_analysis(
        question=text,
        question_type=question_type,
        visa_code=immigration_facts.get("current_status") or (visa_code or "").upper() or (codes[0] if codes else None),
        risk_level=risk_level,
        source_type_plan=source_type_plan,
        direct_manual_sources=direct_manual_sources,
        related_manual_sources=related_manual_sources,
        law_sources=law_sources,
        official_confirmation_questions=list(quality.get("official_confirmation_questions") or localized_confirm),
        law_grounding_status=law_grounding_status,
        immigration_facts=immigration_facts,
        legal_issue_types=legal_issue_types,
    )

    pack: Dict[str, Any] = {
        "law_tool_layer_version": LAW_TOOL_LAYER_VERSION,
        "question_type": question_type,
        "risk_level": risk_level,
        "visa_code": immigration_facts.get("current_status") or (visa_code or "").upper() or (codes[0] if codes else None),
        "detected_statuses": codes,
        "source_status": source_status,
        "target_status": target_status,
        "immigration_facts": immigration_facts,
        "legal_issue_types": legal_issue_types,
        "proposed_activity_type": immigration_facts.get("proposed_activities", []),
        # Generalized ontology snapshot + structured query plan (Parts A/B/C).
        "evidence_ontology": {
            "ontology_version": ONTOLOGY_VERSION,
            "status_family": status_family(
                immigration_facts.get("current_parent_status")
                or immigration_facts.get("current_status")
            ),
            "activity_types": immigration_facts.get("proposed_activities", []),
            "legal_issue_types": legal_issue_types,
            "source_families_planned": route_source_families(legal_issue_types),
            "wired_families_planned": [
                f for f in route_source_families(legal_issue_types)
                if is_source_family_wired(f)
            ],
            "unwired_families_planned": [
                f for f in route_source_families(legal_issue_types)
                if not is_source_family_wired(f)
            ],
        },
        "evidence_query_plan": evidence_query_plan,
        "evidence_goal_by_query": [q["evidence_goal"] for q in evidence_query_plan],
        "source_family_support": {
            f: source_family_support_status(f)
            for f in route_source_families(legal_issue_types)
        },
        # Evidence buckets (kept strictly separate — Part D / evidence discipline)
        "direct_manual_sources": direct_manual_sources,
        "related_manual_sources": related_manual_sources,
        "law_sources": law_sources,
        "precedent_evidence_items": source_family_retrieval.get("precedent_evidence_items", []),
        "planned_law_queries": planned_queries,
        "law_queries_attempted": law_queries_attempted,
        "law_api_attempted": law_api_attempted,
        "law_grounding_status": law_grounding_status,
        "law_grounding_error": law_grounding_error,
        "law_grounding_warnings": list(dict.fromkeys(law_grounding_warnings)),
        "manual_grounding_status": manual_grounding_status,
        "manual_to_law_fallback_used": manual_to_law_fallback_used,
        "related_statuses_not_sources": list(quality.get("related_statuses_not_sources") or related_statuses),
        "source_confidence_level": quality.get("source_confidence_level", "none"),
        "answer_quality_mode": quality.get("answer_quality_mode", "generic_advisory"),
        "requires_official_confirmation": bool(quality.get("requires_official_confirmation", True)),
        "official_confirmation_questions": list(quality.get("official_confirmation_questions") or []),
        "official_confirmation_questions_localized": localized_confirm,
        "law_evidence_count": len(law_sources),
        "normalized_evidence_count": len(law_sources),
        "source_family_results": source_family_retrieval.get("source_family_results", []),
        "source_families_planned": source_type_plan.get("source_families_planned") or source_type_plan.get("source_types_priority", []),
        "source_families_attempted": source_type_plan.get("source_families_attempted") or source_type_plan.get("source_types_attempted", []),
        "source_family_statuses": source_type_plan.get("source_family_statuses") or source_type_plan.get("statuses", {}),
        "source_family_result_counts": source_family_retrieval.get("source_family_result_counts", {}),
        "response_shape_hint_by_family": source_family_retrieval.get("response_shape_hints", {}),
        "parser_status_by_family": source_family_retrieval.get("parser_statuses", {}),
        "law_error_type_by_family": source_family_retrieval.get("law_error_types", {}),
        "sanitized_source_urls": source_family_retrieval.get("sanitized_source_urls", []),
        "parser_status": law_context.get("parser_status", "") if law_context else "",
        "response_shape_hint": law_context.get("response_shape_hint", "") if law_context else "",
        "sanitized_source_url": law_context.get("source_url", "") if law_context else (law_sources[0].get("source_url", "") if law_sources else ""),
        "attempted_targets": ["law"] if (law_api_attempted or law_sources) else [],
        "intent_reasons": list(intent.get("reasons") or []),
        "source_type_plan": source_type_plan,
        "source_plan": source_type_plan,
        "source_type_statuses": source_type_plan.get("statuses", {}),
        "source_types_attempted": source_type_plan.get("source_types_attempted", []),
        "source_types_returned": source_type_plan.get("source_types_returned", []),
        "legal_analysis": legal_analysis,
        # Public structured evidence items (compact grounding schema: source_id,
        # source_title, source_type, version_or_date, authority_level, excerpt,
        # page_or_section, url, directness, relevance_reason). Surfaced top-level
        # for the source panel; also present inside legal_analysis.
        "grounding_items": legal_analysis.get("grounding_items", []),
        "analysis_mode": legal_analysis.get("analysis_mode"),
        "main_issue": legal_analysis.get("main_issue"),
        "direct_evidence_count": legal_analysis.get("direct_evidence_count", 0),
        "related_evidence_count": legal_analysis.get("related_evidence_count", 0),
        "analogical_evidence_count": legal_analysis.get("analogical_evidence_count", 0),
        "background_evidence_count": legal_analysis.get("background_evidence_count", 0),
        "missing_direct_authority": legal_analysis.get("missing_direct_authority", True),
        "authority_summary": legal_analysis.get("authority_summary", ""),
    }
    normalized_official_sources = [
        *normalize_manual_source_attempts(
            direct_manual_sources,
            related_manual_sources,
            manual_present=(manual_present or structured_present),
        ),
        *normalize_law_source_attempts(
            law_sources=law_sources,
            source_family_statuses=pack.get("source_family_statuses") or {},
            parser_status_by_family=pack.get("parser_status_by_family") or {},
            law_error_type_by_family=pack.get("law_error_type_by_family") or {},
            source_family_results=pack.get("source_family_results") or [],
        ),
    ]
    query_classification = classify_query_for_grounding(
        text,
        visa_code=visa_code,
        task_type=task_type,
    )
    official_grounding_context = build_official_grounding_context(
        query_classification=query_classification,
        normalized_sources=normalized_official_sources,
        source_plan=source_type_plan,
    )

    pack["query_classification"] = query_classification
    pack["normalized_official_sources"] = normalized_official_sources
    pack["official_grounding_context"] = official_grounding_context
    pack["grounding_context_prompt"] = render_grounding_context_for_prompt(official_grounding_context)
    pack["public_source_status"] = project_public_source_status(
        normalized_official_sources,
        lang=lang or "ko",
    )
    pack["public_official_sources"] = pack["public_source_status"].get("sources", [])
    pack["developer_source_diagnostics"] = developer_source_diagnostics(normalized_official_sources)

    if law_context is not None and isinstance(law_context.get("citation_verification"), dict):
        # Article-level verification is performed during the bounded live
        # fan-out. Preserve that strict result; never replace it with the
        # weaker list-evidence projection below.
        pack["citation_verification"] = law_context["citation_verification"]
    else:
        pack["citation_verification"] = build_law_evidence_citation_verification(
            law_sources,
            query=(law_queries_attempted[0] if law_queries_attempted else ""),
            law_error_type=law_grounding_error,
            law_api_attempted=law_api_attempted,
        )
    pack["case_decision_citation_verification"] = verify_case_decision_citations(
        "",
        evidence_items=pack.get("precedent_evidence_items") or [],
    )
    pack["evidence_summary"] = build_evidence_summary(pack)
    return pack


def cfg_display(config: GroundingConfig) -> int:
    # Small fixed page size; the planner already limits total queries.
    return _DEFAULT_DISPLAY


def _dedupe_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for source in sources:
        key = source.get("reference") or source.get("law_name") or source.get("term")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(source)
    return out


def build_evidence_summary(pack: Dict[str, Any]) -> str:
    """Compact, normalized, trimmed evidence summary for the answer prompt.

    Deliberately small — the final prompt must receive a summary, never a raw
    API dump. Contains no secrets and no sanitized-out URLs.
    """
    lines: List[str] = []
    lines.append(f"Question type: {pack.get('question_type')} (risk: {pack.get('risk_level')}).")
    lines.append(
        f"Source state: manual={pack.get('manual_grounding_status')}, "
        f"law={pack.get('law_grounding_status')}, "
        f"confidence={pack.get('source_confidence_level')}, "
        f"answer mode={pack.get('answer_quality_mode')}."
    )
    if pack.get("grounding_context_prompt"):
        lines.append("Generalized source-grounding context:")
        lines.append(pack.get("grounding_context_prompt"))
    legal_analysis = pack.get("legal_analysis") or {}
    if legal_analysis:
        lines.append("Legal analysis object (backend-prepared; do not invent beyond it):")
        lines.append(f"  - practical posture: {legal_analysis.get('practical_posture')}")
        lines.append(f"  - main issue: {legal_analysis.get('main_issue')}")
        lines.append(f"  - authority: {legal_analysis.get('authority_summary')}")
    law_sources = pack.get("law_sources") or []
    if law_sources:
        lines.append("Normalized law evidence (context only — not a document checklist):")
        for source in law_sources[:3]:
            name = source.get("law_name") or source.get("term") or "(law)"
            extra = source.get("law_division") or source.get("rule_type") or ""
            lines.append(f"  - {name} {extra}".rstrip())
    elif pack.get("law_api_attempted"):
        lines.append("Law evidence: attempted but unavailable for this question.")
    related = pack.get("related_statuses_not_sources") or []
    if related:
        lines.append(
            "Related statuses to verify (NOT direct sources for the asked status): "
            + ", ".join(related)
        )
    return "\n".join(lines)
