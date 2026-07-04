"""Read-only MOFA public-data portal client for PreView by Paradiso.

Scope
-----
This module talks to exactly one public-data portal OpenAPI:

    외교부_국가·지역별 재외공관 정보
    https://www.data.go.kr/data/15075354/openapi.do
    http(s)://apis.data.go.kr/1262000/EmbassyService2/getEmbassyList2

It powers the pre-arrival "PreView" mission card. It is intentionally
independent from the existing Visable grounding clients
(public_data_client.py / korean_law_client.py) because the data.go.kr
portal authenticates with a ``serviceKey`` query parameter rather than an
Authorization header — but it follows the same house rules:

- guarded httpx import (module must import without httpx installed)
- environment read at call time, never at import time
- every failure returns a safe JSON envelope; nothing raises to callers
- the service key is NEVER echoed in responses, logs, or error text

Key resolution order (documented product policy):
1. MOFA_EMBASSY_SERVICE_KEY   (service-specific alias)
2. PUBLIC_DATA_SERVICE_KEY    (unified portal key)
3. no key -> safe fallback envelope (frontend renders MVP sample data)
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

try:  # pragma: no cover - exercised implicitly by import
    import httpx
except Exception:  # pragma: no cover - environment without httpx
    httpx = None  # type: ignore[assignment]

DATASET_NAME = "외교부_국가·지역별 재외공관 정보"
DATASET_PROVIDER = "외교부"
DATASET_SOURCE_TYPE = "mofa_public_data_portal_api"
DATASET_PAGE_URL = "https://www.data.go.kr/data/15075354/openapi.do"
DEFAULT_ENDPOINT = "https://apis.data.go.kr/1262000/EmbassyService2/getEmbassyList2"

_KEY_ENV_ORDER: Tuple[str, ...] = (
    "MOFA_EMBASSY_SERVICE_KEY",
    "PUBLIC_DATA_SERVICE_KEY",
)

_DEFAULT_TIMEOUT_SECONDS = 6.0
_MAX_UPSTREAM_BYTES = 2_000_000
_MAX_ITEMS = 20

_ISO2_RE = re.compile(r"^[A-Za-z]{2}$")
# Korean or Latin country names, spaces and a few punctuation marks only.
_COUNTRY_NAME_RE = re.compile(r"^[0-9A-Za-z가-힣 ·().,\-]{1,40}$")
_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

SAFE_MESSAGE_MISSING_KEY_KO = (
    "공공데이터 API 키가 설정되지 않아 MVP 샘플 데이터를 표시해야 합니다."
)
SAFE_MESSAGE_UPSTREAM_KO = (
    "공공데이터 API 응답을 불러오지 못했습니다. MVP 샘플 데이터를 표시하고 "
    "관할 재외공관 공식 원문을 확인해야 합니다."
)
SAFE_MESSAGE_INVALID_QUERY_KO = (
    "국가 코드(ISO 2자리) 또는 국가명을 확인해 주세요."
)


def _now_date() -> str:
    return time.strftime("%Y-%m-%d")


def _source_metadata(evidence_level: str) -> Dict[str, Any]:
    return {
        "provider": DATASET_PROVIDER,
        "datasetName": DATASET_NAME,
        "sourceType": DATASET_SOURCE_TYPE,
        "evidenceLevel": evidence_level,
        "datasetPageUrl": DATASET_PAGE_URL,
        "fetchedAt": _now_date(),
    }


def _fallback_envelope(reason: str, safe_message_ko: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "mode": "fallback_required",
        "reason": reason,
        "safeMessageKo": safe_message_ko,
        "source": _source_metadata("unavailable"),
        "items": [],
    }


def _invalid_query_envelope() -> Dict[str, Any]:
    envelope = _fallback_envelope("invalid_query", SAFE_MESSAGE_INVALID_QUERY_KO)
    envelope["error"] = "invalid_query"
    return envelope


def resolve_service_key() -> Optional[str]:
    """Return the first configured portal key, or None. Never log the value."""
    for env_name in _KEY_ENV_ORDER:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def _prepare_key_for_transport(key: str) -> str:
    """data.go.kr issues percent-encoded keys; decode once so the HTTP client
    does not double-encode (a classic SERVICE_KEY_IS_NOT_REGISTERED cause)."""
    if re.search(r"%[0-9A-Fa-f]{2}", key):
        return unquote(key)
    return key


def _clean_iso2(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip()
    if _ISO2_RE.match(candidate):
        return candidate.upper()
    return None


def _clean_country_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = " ".join(value.strip().split())
    if candidate and _COUNTRY_NAME_RE.match(candidate):
        return candidate
    return None


def _sanitize_text(value: Any, max_len: int = 300) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = _CONTROL_RE.sub(" ", text)
    text = " ".join(text.split())
    if not text:
        return None
    return text[:max_len]


def _sanitize_number(value: Any) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _default_transport(url: str, params: Dict[str, str], timeout: float) -> Tuple[int, str]:
    """Perform the upstream GET. Swappable seam for offline tests
    (tests assign mofa_public_data._default_transport = fake)."""
    if httpx is None:
        raise RuntimeError("httpx_unavailable")
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = client.get(url, params=params)
        return response.status_code, response.text[: _MAX_UPSTREAM_BYTES + 1]


def _extract_records(payload: Any) -> List[Dict[str, Any]]:
    """Accept both observed MOFA envelope shapes defensively:
    flat {"data": [...]} (versioned JSON services) and the classic
    response/body/items/item wrapper."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [rec for rec in data if isinstance(rec, dict)]
    response = payload.get("response")
    if isinstance(response, dict):
        body = response.get("body")
        if isinstance(body, dict):
            items = body.get("items")
            if isinstance(items, dict):
                item = items.get("item")
                if isinstance(item, list):
                    return [rec for rec in item if isinstance(rec, dict)]
                if isinstance(item, dict):
                    return [item]
            if isinstance(items, list):
                return [rec for rec in items if isinstance(rec, dict)]
    items = payload.get("items")
    if isinstance(items, list):
        return [rec for rec in items if isinstance(rec, dict)]
    return []


def _upstream_error_code(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    code = payload.get("resultCode")
    if code is None and isinstance(payload.get("response"), dict):
        header = payload["response"].get("header")
        if isinstance(header, dict):
            code = header.get("resultCode")
    if code is None:
        return None
    code_text = str(code).strip()
    if code_text in ("0", "00", "INFO-0", "INFO-00"):
        return None
    return code_text


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Map upstream field names into the stable PreViewMission shape.

    Upstream field names follow the corroborated EmbassyService2 schema
    (country_nm, embassy_kor_nm, emblgbd_addr, tel_no, urgency_tel_no,
    center_tel_no, ...). Unknown/missing fields become None — never guessed.
    """
    return {
        "missionNameKo": _sanitize_text(record.get("embassy_kor_nm")),
        "missionTypeKo": _sanitize_text(record.get("embassy_ty_cd_nm")),
        "missionJurisdictionKo": _sanitize_text(record.get("embassy_manage_ty_cd_nm")),
        "countryNameKo": _sanitize_text(record.get("country_nm")),
        "countryNameEn": _sanitize_text(record.get("country_eng_nm")),
        "countryIso2": _sanitize_text(record.get("country_iso_alp2"), max_len=2),
        "addressKo": _sanitize_text(record.get("emblgbd_addr"), max_len=400),
        "phone": _sanitize_text(record.get("tel_no"), max_len=80),
        "emergencyPhone": _sanitize_text(record.get("urgency_tel_no"), max_len=80),
        "consularCallCenter": _sanitize_text(record.get("center_tel_no"), max_len=80),
        "freePhone": _sanitize_text(record.get("free_tel_no"), max_len=80),
        "latitude": _sanitize_number(record.get("embassy_lat")),
        "longitude": _sanitize_number(record.get("embassy_lng")),
    }


def _matches_query(item: Dict[str, Any], iso2: Optional[str], name: Optional[str]) -> bool:
    if iso2:
        item_iso = (item.get("countryIso2") or "").upper()
        if item_iso:
            return item_iso == iso2
        # No ISO field on the record: fall through to name matching if any.
    if name:
        country = item.get("countryNameKo") or ""
        country_en = (item.get("countryNameEn") or "").lower()
        return name in country or name.lower() in country_en
    # cond[] filter already applied upstream and record carries no ISO field.
    return not iso2


def _endpoint() -> str:
    return os.environ.get("MOFA_EMBASSY_ENDPOINT", "").strip() or DEFAULT_ENDPOINT


def _timeout_seconds() -> float:
    raw = os.environ.get("PREVIEW_MOFA_TIMEOUT_SECONDS", "").strip()
    try:
        value = float(raw) if raw else _DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        value = _DEFAULT_TIMEOUT_SECONDS
    return min(max(value, 1.0), 20.0)


def fetch_mission_directory(
    country_iso2: Optional[str] = None,
    country_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch overseas-mission records for one country.

    Returns a safe JSON envelope in every case; never raises and never
    includes the service key in any field.
    """
    iso2 = _clean_iso2(country_iso2)
    name = _clean_country_name(country_name)
    if (country_iso2 and not iso2) or (country_name and not name):
        return _invalid_query_envelope()
    if not iso2 and not name:
        return _invalid_query_envelope()

    key = resolve_service_key()
    if not key:
        return _fallback_envelope("missing_service_key", SAFE_MESSAGE_MISSING_KEY_KO)

    params: Dict[str, str] = {
        "serviceKey": _prepare_key_for_transport(key),
        "returnType": "JSON",
        "pageNo": "1",
        "numOfRows": "50",
        # Portal docs: cond[country_nm::EQ] accepts Korean country name or
        # ISO 3166-1 alpha-2 code.
        "cond[country_nm::EQ]": iso2 or name or "",
    }

    try:
        status_code, body_text = _default_transport(_endpoint(), params, _timeout_seconds())
    except Exception as exc:  # noqa: BLE001 - convert everything to safe envelope
        if httpx is not None and isinstance(exc, httpx.TimeoutException):
            return _fallback_envelope("upstream_timeout", SAFE_MESSAGE_UPSTREAM_KO)
        return _fallback_envelope("upstream_unreachable", SAFE_MESSAGE_UPSTREAM_KO)

    if status_code != 200:
        return _fallback_envelope(f"upstream_http_{int(status_code)}", SAFE_MESSAGE_UPSTREAM_KO)
    if len(body_text) > _MAX_UPSTREAM_BYTES:
        return _fallback_envelope("upstream_response_too_large", SAFE_MESSAGE_UPSTREAM_KO)

    try:
        payload = json.loads(body_text)
    except (TypeError, ValueError):
        # Auth/quota errors arrive as an XML OpenAPI_ServiceResponse blob.
        if "OpenAPI_ServiceResponse" in body_text or "SERVICE" in body_text[:400]:
            return _fallback_envelope("upstream_service_error", SAFE_MESSAGE_UPSTREAM_KO)
        return _fallback_envelope("upstream_parse_error", SAFE_MESSAGE_UPSTREAM_KO)

    error_code = _upstream_error_code(payload)
    records = _extract_records(payload)
    if not records and error_code:
        return _fallback_envelope("upstream_service_error", SAFE_MESSAGE_UPSTREAM_KO)

    normalized = [_normalize_record(record) for record in records]
    matched = [item for item in normalized if _matches_query(item, iso2, name)]
    items = (matched or [])[:_MAX_ITEMS]

    envelope: Dict[str, Any] = {
        "ok": True,
        "mode": "live_api",
        "source": _source_metadata("source_confirmed"),
        "query": {"country": iso2, "countryName": name},
        "itemCount": len(items),
        "items": items,
    }
    if not items:
        envelope["noteKo"] = (
            "요청한 국가에 대한 재외공관 레코드를 찾지 못했습니다. "
            "관할 재외공관은 외교부 공식 안내에서 확인해 주세요."
        )
    return envelope
