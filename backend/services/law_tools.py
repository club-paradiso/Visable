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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .grounding_config import GroundingConfig, load_grounding_config
from .law_grounding import should_attempt_law_grounding
from .answer_quality import (
    classify_answer_quality,
    classify_question_type,
    detect_related_statuses,
)

LAW_TOOL_LAYER_VERSION = "2026-05-law-tools-v1"

# ---------------------------------------------------------------------------
# Stable error types (Part B contract). Returned in tool output ``error_type``.
# ---------------------------------------------------------------------------
LAW_API_NOT_CONFIGURED = "law_api_not_configured"
LAW_API_HTTP_ERROR = "law_api_http_error"
LAW_API_TIMEOUT = "law_api_timeout"
LAW_API_BAD_RESPONSE = "law_api_bad_response"
LAW_API_NO_RESULTS = "law_api_no_results"
LAW_API_PARSE_ERROR = "law_api_parse_error"

# Default DRF endpoints for the National Law Information Open API. These are
# public, fixed endpoints (confirmed by scripts/probe_korean_law_open_api_2026_05.py);
# only the OC value is a secret. A deployment that sets LAW_API_BASE_URL can
# override the host (e.g. to a private proxy) without touching code.
_DEFAULT_API_HOST = "http://www.law.go.kr"
_SEARCH_PATH = "/DRF/lawSearch.do"
_SERVICE_PATH = "/DRF/lawService.do"

# Conservative request ceiling so a single /api/ask never fans out into a
# burst of law-API calls. The planner keeps the set small; this is a hard cap.
_DEFAULT_MAX_QUERIES = 4
_HARD_MAX_QUERIES = 6
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


def _default_transport(url: str, timeout: float) -> LawHttpResponse:
    """Real network transport (urllib; no third-party dependency required)."""
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
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
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
        return {
            "term": term,
            "definition": _first(obj, "법령용어정의", "용어설명", "정의", "definition") or "",
            "source_type": "law_term",
            "retrieval_status": "ok",
        }
    if source_type == "admin_rule":
        name = _first(obj, "행정규칙명", "행정규칙명한글", "admRulNm", "lawName")
        serial = _first(obj, "행정규칙일련번호", "admRulSeq", "MST", "mst")
        rule_id = _first(obj, "행정규칙ID", "admRulId", "ID")
        if not (name or serial or rule_id):
            return None
        return {
            "law_name": name or "(행정규칙)",
            "law_id": rule_id or "",
            "law_serial_no": serial or "",
            "reference": rule_id or serial or "",
            "rule_type": _first(obj, "행정규칙종류", "행정규칙구분명") or "",
            "department": _first(obj, "소관부처명", "담당부처명") or "",
            "source_type": "admin_rule",
            "retrieval_status": "ok",
        }
    # Default: a statute / enforcement decree / rule.
    name = _first(obj, "법령명한글", "법령명", "법령명_한글", "lawName")
    serial = _first(obj, "법령일련번호", "MST", "mst")
    law_id = _first(obj, "법령ID", "lawId", "ID")
    if not (name or serial or law_id):
        return None
    return {
        "law_name": name or "(법령)",
        "law_id": law_id or "",
        "law_serial_no": serial or "",
        "reference": law_id or serial or "",
        "law_division": _first(obj, "법령구분명", "법종구분명") or "",
        "promulgation_date": _first(obj, "공포일자") or "",
        "enforcement_date": _first(obj, "시행일자") or "",
        "department": _first(obj, "소관부처명") or "",
        "source_type": "law",
        "retrieval_status": "ok",
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


def _parse_payload(text: str) -> Tuple[Optional[Any], Optional[str]]:
    """Parse a response body as JSON. Returns ``(payload, error_type)``."""
    stripped = (text or "").strip()
    if not stripped:
        return None, LAW_API_BAD_RESPONSE
    try:
        return json.loads(stripped), None
    except Exception:
        return None, LAW_API_PARSE_ERROR


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
                source_url: str = "", raw_status: int = 0) -> Dict[str, Any]:
    return {
        "tool": tool,
        "status": "error",
        "error_type": error_type,
        "query": query,
        "target": target,
        "source_url": source_url,
        "raw_status": raw_status,
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
        return _tool_error(tool, query=query, target=target, error_type=LAW_API_NOT_CONFIGURED)

    url = _build_request_url(config, path, params)
    sanitized = _sanitize_url(url)
    send = transport or _default_transport
    try:
        response = send(url, config.timeout_seconds)
    except Exception:  # pragma: no cover - transport must not raise, but guard
        return _tool_error(tool, query=query, target=target,
                           error_type=LAW_API_BAD_RESPONSE, source_url=sanitized)

    if not response.ok:
        mapping = {
            "timeout": LAW_API_TIMEOUT,
            "http_error": LAW_API_HTTP_ERROR,
            "network": LAW_API_BAD_RESPONSE,
        }
        error_type = mapping.get(response.error_type, LAW_API_BAD_RESPONSE)
        return _tool_error(tool, query=query, target=target, error_type=error_type,
                           source_url=sanitized, raw_status=response.status_code)

    if response.status_code >= 400:
        return _tool_error(tool, query=query, target=target, error_type=LAW_API_HTTP_ERROR,
                           source_url=sanitized, raw_status=response.status_code)

    payload, parse_error = _parse_payload(response.text)
    if parse_error is not None:
        return _tool_error(tool, query=query, target=target, error_type=parse_error,
                           source_url=sanitized, raw_status=response.status_code)

    results = _walk_candidates(payload, source_type, limit)
    if not results:
        return _tool_error(tool, query=query, target=target, error_type=LAW_API_NO_RESULTS,
                           source_url=sanitized, raw_status=response.status_code)

    ok_result: Dict[str, Any] = {
        "tool": tool,
        "status": "ok",
        "error_type": "",
        "query": query,
        "target": target,
        "source_url": sanitized,
        "raw_status": response.status_code,
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


def _extract_articles(result: Dict[str, Any], article_filter: str) -> List[Dict[str, Any]]:
    """Best-effort article normalization from a service response (tolerant)."""
    # The normalized candidate path does not retain raw articles; service
    # payloads vary widely, so we keep this conservative and schema-tolerant.
    raw = result.get("_raw_payload")
    articles: List[Dict[str, Any]] = []
    target_no = (article_filter or "").strip()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if any(k in node for k in _ARTICLE_KEYS):
                no = _first(node, "조문번호", "조문가지번호") or ""
                title = _first(node, "조문제목") or ""
                text = _first(node, "조문내용") or ""
                if not target_no or target_no in no or target_no in title:
                    articles.append({"article_no": no, "article_title": title, "text": text[:600]})
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
                          "part-time", "part time", "employ", "work", "job", "freelance", "프리랜서", "intern"),
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
        "출입국관리법 시행령 유학 어학연수 체류자격외활동 활동범위",
        "유학 시간제취업 인턴십 활동범위 체류자격외활동",
        "체류자격 변경 유학 D-2 D-4",
    ],
    "working_holiday": [
        "출입국관리법 시행령 관광취업 H-1 체류자격 활동범위",
        "관광취업 유학 활동범위 체류자격외활동",
        "H-1 관광취업 체류자격외활동 체류자격 변경",
    ],
    "employment": [
        "취업활동 근무처 변경 근무처 추가 신고",
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

    codes = extract_status_codes(text)
    source_status, target_status = _status_change_pair(text, codes)
    related_statuses = detect_related_statuses(text, visa_code, task_type)

    plan = plan_law_queries(
        text, visa_code=visa_code, task_type=task_type,
        question_type=question_type, max_queries=max_queries,
    )
    planned_queries = plan["queries"]

    # --- Retrieval (single network seam; never required in tests) ----------
    law_sources: List[Dict[str, Any]] = []
    law_queries_attempted: List[str] = []
    law_api_attempted = False
    law_grounding_error = ""
    law_grounding_warnings: List[str] = []
    context_used_hint = False

    if law_context is not None:
        # Reuse already-fetched results (no duplicate live call).
        law_api_attempted = bool(law_context.get("attempted"))
        context_used_hint = bool(law_context.get("law_grounding_used"))
        for candidate in (law_context.get("law_grounding") or []):
            normalized = _normalize_candidate(candidate, "law") if isinstance(candidate, dict) else None
            if normalized:
                law_sources.append(normalized)
        law_queries_attempted = [law_context.get("law_search_query", "")] if law_context.get("law_search_query") else []
        law_grounding_warnings = list(law_context.get("grounding_warnings") or [])
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
                for query in planned_queries:
                    result = search_laws(query, config=cfg, transport=transport, limit=cfg_display(cfg))
                    law_queries_attempted.append(query)
                    if result["status"] == "ok":
                        law_sources.extend(result["results"])
                    elif not law_grounding_error:
                        law_grounding_error = result["error_type"]
                    if len(law_sources) >= _HARD_MAX_QUERIES:
                        break
                # Trim/dedupe normalized law sources for a compact pack.
                law_sources = _dedupe_sources(law_sources)[:_HARD_MAX_QUERIES]
                if not law_sources and not law_grounding_error:
                    law_grounding_error = LAW_API_NO_RESULTS

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

    pack: Dict[str, Any] = {
        "law_tool_layer_version": LAW_TOOL_LAYER_VERSION,
        "question_type": question_type,
        "risk_level": risk_level,
        "visa_code": (visa_code or "").upper() or (codes[0] if codes else None),
        "detected_statuses": codes,
        "source_status": source_status,
        "target_status": target_status,
        # Evidence buckets (kept strictly separate — Part D / evidence discipline)
        "direct_manual_sources": direct_manual_sources,
        "related_manual_sources": related_manual_sources,
        "law_sources": law_sources,
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
        "official_confirmation_questions": list(quality.get("official_confirmation_questions") or []),
        "official_confirmation_questions_localized": localized_confirm,
        "law_evidence_count": len(law_sources),
        "intent_reasons": list(intent.get("reasons") or []),
    }
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
