"""Law Open Data precedent-family source adapter scaffold.

This module scaffolds the *precedent-related* official source families that the
existing law tooling (``law_tools``) does not yet retrieve:

* ``precedent``               — 판례 (court precedent)
* ``administrative_appeal``   — 행정심판례 (administrative appeal decisions)
* ``legal_interpretation``    — 법령해석례 (legal interpretation cases)
* ``constitutional_decision`` — 헌재결정례 (Constitutional Court decisions)

Scope (scaffold-first — see
``docs/data/LAW_OPEN_DATA_PRECEDENT_SOURCE_SCAFFOLD_2026_06.md``):

* A conservative, fixture-driven *normalizer* for each family that maps raw
  Open Law API objects into a single normalized **evidence item** shape, and a
  list-search scaffold for ``precedent`` using the documented
  ``DRF/lawSearch.do?target=prec`` endpoint.
* The two-step precedent design is explicit: list search yields candidate
  cases; a bounded body/detail lookup uses the stable identifiers from the
  list result. The normalizer distinguishes
  ``list_result`` from ``body_result`` so a list-only result is never presented
  as a full-text citation.
* Only ``precedent`` has a confirmed list-search target (``prec``). The other
  three families keep ``None`` targets — they are normalized from fixtures only
  and reported as ``scaffold_only`` / public-safe unavailable, never as fake
  production adapters.

Hard guarantees (shared with ``law_tools``):

* The OC / API-key value is NEVER returned in URLs, results, or logs. URL
  sanitization and the HTTP transport are reused from ``law_tools`` so the
  secret-redaction logic lives in exactly one place.
* Every function is deterministic and mock-friendly: the HTTP boundary is the
  same injectable ``transport`` callable, so CI never needs live network or a
  real ``LAW_API_OC``.
* When ``LAW_API_OC`` is absent the adapter returns a public-safe
  ``not_configured`` / ``unavailable`` envelope; it never raises.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlsplit

from .grounding_config import GroundingConfig, load_grounding_config
from . import law_tools as lt
from .evidence_ontology import (
    is_citation_grade_capable,
    source_family_live_adapter_status,
    source_family_public_unavailable_label,
)

PRECEDENT_SOURCES_VERSION = "2026-06-law-open-data-precedent-v2-detail-safe"

# Confirmed list-search target for court precedent (판례) on lawSearch.do.
# Documented hint (Open Law API guide + community implementation notes); live
# target/body verification remains a follow-up (see the scaffold doc).
PRECEDENT_LIST_TARGET = "prec"

# List-search targets. ``None`` means the official target is NOT confirmed yet
# and we refuse to guess one — the family stays scaffold-only / fixture-driven.
SOURCE_FAMILY_LIST_TARGETS: Dict[str, Optional[str]] = {
    "precedent": PRECEDENT_LIST_TARGET,
    "administrative_appeal": None,
    "legal_interpretation": None,
    "constitutional_decision": None,
}

# Normalized evidence-item enums (kept public for tests / callers).
RESULT_KINDS = ("list_result", "body_result", "fixture", "unavailable")
CITATION_GRADES = ("direct", "contextual", "background", "unavailable")
PUBLIC_STATUSES = ("available", "temporarily_unavailable", "unavailable", "not_relevant")

_PRECEDENT_FAMILIES = frozenset(SOURCE_FAMILY_LIST_TARGETS)


def normalize_law_go_kr_url(value: Any) -> str:
    """Return a safe absolute official URL, or ``""`` for anything else."""
    raw = str(value or "").strip()
    if not raw or any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        return ""
    if raw.startswith("//"):
        return ""
    if raw.startswith("/"):
        parsed = urlsplit(raw)
        decoded_path = unquote(parsed.path or "")
        if parsed.scheme or parsed.netloc or not decoded_path.startswith("/DRF/lawService.do"):
            return ""
        if decoded_path != "/DRF/lawService.do" or ".." in decoded_path.split("/"):
            return ""
        return "https://www.law.go.kr" + raw
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.lower().rstrip(".")
    if not (host == "law.go.kr" or host.endswith(".law.go.kr")):
        return ""
    if parsed.username or parsed.password:
        return ""
    decoded_path = unquote(parsed.path or "")
    if ".." in decoded_path.split("/"):
        return ""
    return raw


def _precedent_identity(item: Dict[str, Any]) -> tuple:
    source_id = re.sub(r"\s+", "", str(item.get("serialNumber") or "")).lower()
    if source_id:
        return ("source_id", source_id)
    return (
        "case",
        re.sub(r"\s+", "", str(item.get("caseNumber") or item.get("decisionNumber") or "")).lower(),
        re.sub(r"\s+", "", str(item.get("courtOrAgency") or item.get("sourceName") or "")).lower(),
        re.sub(r"\D", "", str(item.get("decisionDate") or "")),
    )


def dedupe_precedent_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        primary = _precedent_identity(item)
        case_key = (
            "case",
            re.sub(r"\s+", "", str(item.get("caseNumber") or item.get("decisionNumber") or "")).lower(),
            re.sub(r"\s+", "", str(item.get("courtOrAgency") or item.get("sourceName") or "")).lower(),
            re.sub(r"\D", "", str(item.get("decisionDate") or "")),
        )
        keys = [primary]
        if case_key[1]:
            keys.append(case_key)
        if any(key in seen for key in keys):
            continue
        seen.update(keys)
        out.append(item)
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick(obj: Dict[str, Any], *keys: str) -> str:
    """First non-empty value across the candidate keys, as a stripped string."""
    if not isinstance(obj, dict):
        return ""
    for key in keys:
        value = obj.get(key)
        if value not in (None, "", [], {}):
            return str(value).strip()
    return ""


def _pick_join(obj: Dict[str, Any], keys: tuple, *, max_parts: int = 2, sep: str = " / ") -> str:
    """Join the first ``max_parts`` distinct non-empty values across keys.

    Used for the holding text so that a precedent body's 판시사항 (the issue)
    AND 판결요지 (the holding summary) are both captured as quotable text,
    rather than dropping one of them.
    """
    if not isinstance(obj, dict):
        return ""
    parts: List[str] = []
    for key in keys:
        value = obj.get(key)
        if value in (None, "", [], {}):
            continue
        text = str(value).strip()
        if text and text not in parts:
            parts.append(text)
        if len(parts) >= max_parts:
            break
    return sep.join(parts)


def _clean(value: Any, *, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit]


# ---------------------------------------------------------------------------
# Tolerant field keys per family (Korean official-ish keys + English fallbacks)
# ---------------------------------------------------------------------------
_TITLE_KEYS = ("사건명", "안건명", "제목", "case_name", "caseName", "title")
_CASE_NUMBER_KEYS = ("사건번호", "caseNumber", "case_no", "caseNo")
_DECISION_NUMBER_KEYS = ("재결번호", "결정번호", "의안번호", "안건번호", "decisionNumber", "decision_no")
_SERIAL_KEYS = (
    "판례일련번호", "헌재결정례일련번호", "행정심판례일련번호", "법령해석례일련번호",
    "일련번호", "serialNumber", "serial", "id", "ID",
)
_DATE_KEYS = (
    "선고일자", "종국일자", "재결일자", "회신일자", "의결일자", "결정일자",
    "decisionDate", "date",
)
_COURT_AGENCY_KEYS = (
    "법원명", "의결기관", "처분청", "회신기관명", "회신기관", "해석기관", "재판부",
    "기관명", "courtOrAgency", "court", "agency",
)
_HOLDING_KEYS = ("판시사항", "판결요지", "재결요지", "결정요지", "회답", "holdingSummary", "holding")
_SNIPPET_KEYS = (
    "판례내용", "재결내용", "결정내용", "이유", "질의요지", "본문",
    "summary", "snippet", "text", "내용",
)
_URL_KEYS = ("판례상세링크", "상세링크", "url", "link")
_ISSUE_TAG_KEYS = ("사건종류명", "판결유형", "종국결과", "사건종류", "분야")


# ---------------------------------------------------------------------------
# Citation grading
# ---------------------------------------------------------------------------
def _identity_level(
    family: str,
    *,
    case_number: str,
    decision_number: str,
    serial_number: str,
    court_or_agency: str,
) -> str:
    """How complete the source identity is: 'full' / 'partial' / 'none'.

    A citation needs a stable identifier AND an issuing authority. For
    legal interpretations the issuing body is the core identity and a stable
    serial strengthens it; for precedent / appeal / constitutional families a
    case or decision number plus the court/agency is required.
    """
    has_id = bool(case_number or decision_number or serial_number)
    has_authority = bool(court_or_agency)
    if family == "legal_interpretation":
        if has_authority and has_id:
            return "full"
        return "partial" if has_authority else "none"
    if has_id and has_authority:
        return "full"
    if has_id or has_authority:
        return "partial"
    return "none"


def _derive_citation_grade(
    family: str,
    *,
    result_kind: str,
    case_number: str,
    decision_number: str,
    serial_number: str,
    court_or_agency: str,
    snippet: str,
    holding_summary: str,
) -> str:
    """Citation grade per the precedent-family rules.

    * Unidentified text is NEVER citation-grade (→ background).
    * A list_result with full identity is contextual, not direct.
    * A body_result with full identity AND quotable text is direct.
    * Partial identity downgrades to background.
    """
    if result_kind == "unavailable":
        return "unavailable"
    if not is_citation_grade_capable(family):
        return "background"
    level = _identity_level(
        family,
        case_number=case_number,
        decision_number=decision_number,
        serial_number=serial_number,
        court_or_agency=court_or_agency,
    )
    if level == "none":
        return "background"
    has_body_text = bool(snippet or holding_summary)
    if result_kind == "body_result" and has_body_text and level == "full":
        return "direct"
    if level == "full":
        return "contextual"
    return "background"


def _public_status_for(result_kind: str, grade: str, *, transient: bool = False) -> str:
    if result_kind == "unavailable" or grade == "unavailable":
        return "temporarily_unavailable" if transient else "unavailable"
    return "available"


def build_source_family_evidence_item(
    *,
    source_family: str,
    result_kind: str,
    title: str = "",
    source_name: str = "",
    case_number: str = "",
    decision_number: str = "",
    serial_number: str = "",
    decision_date: str = "",
    court_or_agency: str = "",
    issue_tags: Optional[List[str]] = None,
    url: str = "",
    snippet: str = "",
    holding_summary: str = "",
    internal_status: str = "",
    public_status: str = "",
    transient: bool = False,
    supports: Optional[List[str]] = None,
    limitations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct one normalized precedent-family evidence item.

    The returned dict is public-safe: ``internalStatus`` is the only raw
    diagnostic field and the public projection / answer layers never surface it.
    """
    grade = _derive_citation_grade(
        source_family,
        result_kind=result_kind,
        case_number=case_number,
        decision_number=decision_number,
        serial_number=serial_number,
        court_or_agency=court_or_agency,
        snippet=snippet,
        holding_summary=holding_summary,
    )
    pub = public_status or _public_status_for(result_kind, grade, transient=transient)
    # Only a body result with quotable text is safe to quote verbatim. A list
    # result is a pointer to a case, never a verbatim source.
    quote_safe = bool(result_kind == "body_result" and (snippet or holding_summary))
    item: Dict[str, Any] = {
        "sourceFamily": source_family,
        "resultKind": result_kind,
        "citationGrade": grade,
        "publicStatus": pub,
        "quoteSafe": quote_safe,
    }
    optional = {
        "internalStatus": internal_status,
        "title": _clean(title, limit=200),
        "sourceName": _clean(source_name, limit=200),
        "caseNumber": _clean(case_number, limit=80),
        "decisionNumber": _clean(decision_number, limit=80),
        "serialNumber": _clean(serial_number, limit=80),
        "decisionDate": _clean(decision_date, limit=40),
        "courtOrAgency": _clean(court_or_agency, limit=120),
        "url": normalize_law_go_kr_url(lt._sanitize_url(url)) if url else "",
        "snippet": _clean(snippet, limit=700),
        "holdingSummary": _clean(holding_summary, limit=700),
        "retrievedAt": _now_iso(),
    }
    for key, value in optional.items():
        if value:
            item[key] = value
    if issue_tags:
        item["issueTags"] = [t for t in (str(x).strip() for x in issue_tags) if t][:6]
    if supports:
        item["supports"] = list(supports)
    if limitations:
        item["limitations"] = list(limitations)
    return item


# ---------------------------------------------------------------------------
# Per-family item normalizers (raw API object → evidence item)
# ---------------------------------------------------------------------------
def _normalize_family_item(obj: Dict[str, Any], *, source_family: str, result_kind: str) -> Optional[Dict[str, Any]]:
    if not isinstance(obj, dict):
        return None
    title = _pick(obj, *_TITLE_KEYS)
    case_number = _pick(obj, *_CASE_NUMBER_KEYS)
    decision_number = _pick(obj, *_DECISION_NUMBER_KEYS)
    serial_number = _pick(obj, *_SERIAL_KEYS)
    court_or_agency = _pick(obj, *_COURT_AGENCY_KEYS)
    decision_date = _pick(obj, *_DATE_KEYS)
    holding_summary = _pick_join(obj, _HOLDING_KEYS, max_parts=2)
    snippet = _pick(obj, *_SNIPPET_KEYS)
    if result_kind != "body_result":
        # List responses identify candidate cases only. They are never a safe
        # substitute for the official body/holding.
        holding_summary = ""
        snippet = ""
    url = _pick(obj, *_URL_KEYS)
    issue_tag = _pick(obj, *_ISSUE_TAG_KEYS)
    # A candidate must carry at least a title or some identity to be useful.
    if not (title or case_number or decision_number or serial_number):
        return None
    return build_source_family_evidence_item(
        source_family=source_family,
        result_kind=result_kind,
        title=title,
        source_name=court_or_agency or title,
        case_number=case_number,
        decision_number=decision_number,
        serial_number=serial_number,
        decision_date=decision_date,
        court_or_agency=court_or_agency,
        issue_tags=[issue_tag] if issue_tag else None,
        url=url,
        snippet=snippet,
        holding_summary=holding_summary,
        internal_status=f"{result_kind}_normalized",
    )


def normalize_precedent_list_item(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _normalize_family_item(obj, source_family="precedent", result_kind="list_result")


def normalize_precedent_body_item(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _normalize_family_item(obj, source_family="precedent", result_kind="body_result")


def normalize_administrative_appeal_item(obj: Dict[str, Any], *, result_kind: str = "list_result") -> Optional[Dict[str, Any]]:
    return _normalize_family_item(obj, source_family="administrative_appeal", result_kind=result_kind)


def normalize_legal_interpretation_item(obj: Dict[str, Any], *, result_kind: str = "list_result") -> Optional[Dict[str, Any]]:
    return _normalize_family_item(obj, source_family="legal_interpretation", result_kind=result_kind)


def normalize_constitutional_decision_item(obj: Dict[str, Any], *, result_kind: str = "list_result") -> Optional[Dict[str, Any]]:
    return _normalize_family_item(obj, source_family="constitutional_decision", result_kind=result_kind)


# ---------------------------------------------------------------------------
# Payload walking + response normalization
# ---------------------------------------------------------------------------
def _walk_dicts(payload: Any, limit: int = 50) -> List[Dict[str, Any]]:
    """Collect candidate dict objects from a parsed payload (schema-tolerant).

    The DRF JSON shape nests results under family-specific keys
    (``{"PrecSearch": {"prec": [...]}}`` etc.). We collect the deepest dict
    objects that look like records rather than hard-coding one schema.
    """
    out: List[Dict[str, Any]] = []

    def visit(node: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(node, dict):
            looks_like_record = any(
                node.get(k) not in (None, "", [], {})
                for k in (*_TITLE_KEYS, *_CASE_NUMBER_KEYS, *_DECISION_NUMBER_KEYS, *_SERIAL_KEYS)
            )
            has_child_container = any(isinstance(v, (dict, list)) for v in node.values())
            if looks_like_record and not has_child_container:
                out.append(node)
                return
            for value in node.values():
                visit(value)
            if looks_like_record and not out:
                out.append(node)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return out[:limit]


def _unavailable_item(family: str, *, internal_status: str, transient: bool) -> Dict[str, Any]:
    return build_source_family_evidence_item(
        source_family=family,
        result_kind="unavailable",
        internal_status=internal_status,
        transient=transient,
        limitations=[source_family_public_unavailable_label(family, lang="ko")],
    )


def _envelope(
    *,
    family: str,
    status: str,
    public_status: str,
    result_kind: str,
    query: str,
    items: List[Dict[str, Any]],
    target: Optional[str] = None,
    sanitized_url: str = "",
    response_shape_hint: str = "",
    parser_status: str = "",
    error_type: str = "",
) -> Dict[str, Any]:
    return {
        "sourceFamily": family,
        "liveAdapterStatus": source_family_live_adapter_status(family),
        "target": target if target is not None else (SOURCE_FAMILY_LIST_TARGETS.get(family) or ""),
        "resultKind": result_kind,
        "status": status,
        "publicStatus": public_status,
        "query": query,
        "sanitizedSourceUrl": sanitized_url,
        "responseShapeHint": response_shape_hint,
        "parserStatus": parser_status,
        "errorType": error_type,
        "items": items,
        "itemCount": len(items),
        "retrievedAt": _now_iso(),
        "version": PRECEDENT_SOURCES_VERSION,
    }


def normalize_source_family_response(
    family: str,
    body: str,
    *,
    result_kind: str = "list_result",
    http_status: int = 200,
    query: str = "",
    sanitized_url: str = "",
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize a raw precedent-family response body into an evidence envelope.

    Reuses ``law_tools`` shape/error detection (HTML/empty/official-error all
    map to a public-safe unavailable item) and never echoes the raw body. This
    is the single entry point used by both the live ``search_precedents``
    scaffold and the fixture-based tests.
    """
    fam = (family or "").strip().lower()
    if fam not in _PRECEDENT_FAMILIES:
        return _envelope(
            family=fam or "unknown", status="unsupported", public_status="unavailable",
            result_kind="unavailable", query=query, items=[_unavailable_item(fam or "unknown", internal_status="unsupported_family", transient=False)],
            target=target, sanitized_url=sanitized_url,
        )
    if http_status >= 400:
        return _envelope(
            family=fam, status="http_error", public_status="temporarily_unavailable",
            result_kind="unavailable", query=query,
            items=[_unavailable_item(fam, internal_status="http_error", transient=True)],
            target=target, sanitized_url=sanitized_url, error_type=lt.LAW_API_HTTP_ERROR,
        )

    payload, error, parser_status, shape = lt._parse_payload(body or "")
    if error:
        # Map the typed parser error to a public-safe transient/permanent state.
        transient = error in {lt.LAW_API_OFFICIAL_ERROR, lt.LAW_API_PARSE_ERROR}
        status_map = {
            lt.LAW_API_NO_RESULTS: "no_results",
            lt.LAW_API_BAD_RESPONSE: "bad_response",
            lt.LAW_API_PARSE_ERROR: "parse_error",
            lt.LAW_API_OFFICIAL_ERROR: "official_error",
        }
        status = status_map.get(error, "bad_response")
        if status == "no_results":
            return _envelope(
                family=fam, status="no_results", public_status="unavailable",
                result_kind=result_kind, query=query, items=[],
                target=target, sanitized_url=sanitized_url,
                response_shape_hint=shape, parser_status=parser_status, error_type=error,
            )
        return _envelope(
            family=fam, status=status,
            public_status="temporarily_unavailable" if transient else "unavailable",
            result_kind="unavailable", query=query,
            items=[_unavailable_item(fam, internal_status=status, transient=transient)],
            target=target, sanitized_url=sanitized_url,
            response_shape_hint=shape, parser_status=parser_status, error_type=error,
        )

    raw_items = _walk_dicts(payload)
    items: List[Dict[str, Any]] = []
    for obj in raw_items:
        item = _normalize_family_item(obj, source_family=fam, result_kind=result_kind)
        if item:
            items.append(item)
    if not items:
        return _envelope(
            family=fam, status="no_results", public_status="unavailable",
            result_kind=result_kind, query=query, items=[],
            target=target, sanitized_url=sanitized_url,
            response_shape_hint=shape, parser_status=parser_status,
        )
    items = dedupe_precedent_items(items)
    return _envelope(
        family=fam, status="results_found", public_status="available",
        result_kind=result_kind, query=query, items=items,
        target=target, sanitized_url=sanitized_url,
        response_shape_hint=shape, parser_status=parser_status,
    )


# Convenience wrappers naming the family + result kind explicitly.
def normalize_precedent_list_response(body: str, **kwargs: Any) -> Dict[str, Any]:
    return normalize_source_family_response("precedent", body, result_kind="list_result", **kwargs)


def normalize_precedent_body_response(body: str, **kwargs: Any) -> Dict[str, Any]:
    return normalize_source_family_response("precedent", body, result_kind="body_result", **kwargs)


# ---------------------------------------------------------------------------
# Live list-search scaffold (precedent only — target=prec)
# ---------------------------------------------------------------------------
def search_precedents(
    query: str,
    *,
    limit: int = 3,
    config: Optional[GroundingConfig] = None,
    transport: Optional[lt.LawTransport] = None,
) -> Dict[str, Any]:
    """Scaffold list search for court precedent (판례) via ``target=prec``.

    Returns the normalized evidence envelope. This is the *list-search* half of
    the two-step design — body/detail lookup is a documented follow-up. It is
    deliberately NOT invoked by ``law_tools.retrieve_official_source_family``
    (precedent stays ``unsupported`` there) so this PR never auto-fires an
    unverified live call inside the production answer fan-out; it exists for the
    optional shape-capture path and the follow-up live-wiring PR.

    Never raises; honors the shared OC redaction + transport seam, so it is
    fully mockable and safe without ``LAW_API_OC``.
    """
    fam = "precedent"
    cfg = config or load_grounding_config()
    q = (query or "").strip()
    if not cfg.law_api_configured:
        return _envelope(
            family=fam, status="not_configured", public_status="unavailable",
            result_kind="unavailable", query=q,
            items=[_unavailable_item(fam, internal_status="not_configured", transient=False)],
            error_type=lt.LAW_API_NOT_CONFIGURED,
        )
    if not q:
        return _envelope(
            family=fam, status="no_results", public_status="unavailable",
            result_kind="list_result", query=q, items=[], error_type=lt.LAW_API_NO_RESULTS,
        )
    capped = max(1, min(int(limit or 3), 20))
    params = {"target": PRECEDENT_LIST_TARGET, "type": "JSON", "query": q, "display": str(capped)}
    url = lt._build_request_url(cfg, lt._SEARCH_PATH, params)
    sanitized = lt._sanitize_url(url)
    send = transport or lt._default_transport
    try:
        response = send(url, cfg.timeout_seconds)
    except Exception:  # pragma: no cover - transport must not raise, but guard
        return _envelope(
            family=fam, status="bad_response", public_status="temporarily_unavailable",
            result_kind="unavailable", query=q, sanitized_url=sanitized,
            items=[_unavailable_item(fam, internal_status="transport_exception", transient=True)],
            error_type=lt.LAW_API_BAD_RESPONSE,
        )
    if not response.ok:
        mapping = {
            "timeout": ("timeout", lt.LAW_API_TIMEOUT),
            "http_error": ("http_error", lt.LAW_API_HTTP_ERROR),
            "network": ("bad_response", lt.LAW_API_BAD_RESPONSE),
        }
        status, error_type = mapping.get(response.error_type, ("bad_response", lt.LAW_API_BAD_RESPONSE))
        return _envelope(
            family=fam, status=status, public_status="temporarily_unavailable",
            result_kind="unavailable", query=q, sanitized_url=sanitized,
            items=[_unavailable_item(fam, internal_status=status, transient=True)],
            error_type=error_type,
        )
    return normalize_source_family_response(
        fam, response.text, result_kind="list_result",
        http_status=response.status_code, query=q, sanitized_url=sanitized,
        target=PRECEDENT_LIST_TARGET,
    )


def get_precedent_detail(
    source_id: str,
    *,
    config: Optional[GroundingConfig] = None,
    transport: Optional[lt.LawTransport] = None,
) -> Dict[str, Any]:
    """Fetch one official precedent body by stable source ID.

    Only normalized, bounded fields survive. If the service returns no body,
    callers receive metadata/unavailable state and must not synthesize a
    holding, summary, or quoted text.
    """
    cfg = config or load_grounding_config()
    ident = re.sub(r"[^A-Za-z0-9_-]", "", str(source_id or ""))[:80]
    if not cfg.law_api_configured:
        return _envelope(
            family="precedent", status="not_configured", public_status="unavailable",
            result_kind="unavailable", query=ident,
            items=[_unavailable_item("precedent", internal_status="not_configured", transient=False)],
            error_type=lt.LAW_API_NOT_CONFIGURED,
        )
    if not ident:
        return _envelope(
            family="precedent", status="no_results", public_status="unavailable",
            result_kind="body_result", query="", items=[], error_type=lt.LAW_API_NO_RESULTS,
        )
    params = {"target": PRECEDENT_LIST_TARGET, "type": "JSON", "ID": ident}
    url = lt._build_request_url(cfg, lt._SERVICE_PATH, params)
    sanitized = lt._sanitize_url(url)
    send = transport or lt._default_transport
    try:
        response = send(url, cfg.timeout_seconds)
    except Exception:  # pragma: no cover
        response = lt.LawHttpResponse(ok=False, error_type="network")
    if not response.ok:
        status = "timeout" if response.error_type == "timeout" else "bad_response"
        error_type = lt.LAW_API_TIMEOUT if response.error_type == "timeout" else lt.LAW_API_BAD_RESPONSE
        return _envelope(
            family="precedent", status=status, public_status="temporarily_unavailable",
            result_kind="unavailable", query=ident, sanitized_url=sanitized,
            items=[_unavailable_item("precedent", internal_status=status, transient=True)],
            error_type=error_type,
        )
    return normalize_precedent_body_response(
        response.text,
        http_status=response.status_code,
        query=ident,
        sanitized_url=sanitized,
        target=PRECEDENT_LIST_TARGET,
    )
