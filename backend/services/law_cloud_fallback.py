"""Cloud-safe fallback for Korean Open Law title searches.

law.go.kr can return a syntactically successful ``LawSearch`` envelope with
``totalCnt=0`` for Korean ``query=`` requests from some cloud egress ranges.
The same credential still returns normal data when the Korean query parameter
is omitted.  This module keeps the documented query path as primary and only
falls back after that path returns an empty result.

The fallback uses the documented mobile law-list ``gana`` filter (ASCII only),
fetches bounded pages, and performs conservative title matching locally.  It
never logs or returns the OC value and it never invents a law row.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

_PAGE_SIZE = 100
_MAX_SCAN_PAGES_PER_DIRECTION = 6
_CACHE_TTL_SECONDS = 15 * 60

# Choseong index (U+AC00 Hangul syllable decomposition) -> documented
# mobile ``gana`` dictionary group.
_INITIAL_TO_GANA = (
    "ga", "ga",   # ㄱ ㄲ
    "na",          # ㄴ
    "da", "da",   # ㄷ ㄸ
    "ra",          # ㄹ
    "ma",          # ㅁ
    "ba", "ba",   # ㅂ ㅃ
    "sa", "sa",   # ㅅ ㅆ
    "a",           # ㅇ
    "ja", "ja",   # ㅈ ㅉ
    "cha",         # ㅊ
    "ka",          # ㅋ
    "ta",          # ㅌ
    "pa",          # ㅍ
    "ha",          # ㅎ
)

_CORE_LAW_NAMES = (
    "출입국관리법 시행규칙",
    "출입국관리법 시행령",
    "출입국관리법",
    "국적법 시행규칙",
    "국적법 시행령",
    "국적법",
    "난민법 시행규칙",
    "난민법 시행령",
    "난민법",
    "재외동포의 출입국과 법적 지위에 관한 법률",
)

_PAGE_CACHE: Dict[Tuple[str, str, str, int], Tuple[float, Dict[str, Any]]] = {}


def _compact(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", str(value or "")).lower()


def _seed_for_query(query: str) -> str:
    text = str(query or "").strip()
    for law_name in _CORE_LAW_NAMES:
        if _compact(law_name) in _compact(text):
            return law_name
    # Prefer a whitespace-delimited token that looks like a law title.
    for token in re.split(r"[\s,;:/()\[\]{}]+", text):
        if token.endswith(("법률", "법", "시행령", "시행규칙")) and re.search(r"[가-힣]", token):
            return token
    return text


def _gana_group(query: str) -> str:
    seed = _seed_for_query(query)
    for ch in seed:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            initial = (code - 0xAC00) // 588
            if 0 <= initial < len(_INITIAL_TO_GANA):
                return _INITIAL_TO_GANA[initial]
    return ""


def _title(item: Dict[str, Any]) -> str:
    return str(item.get("law_name") or item.get("title") or "").strip()


def _match_score(item: Dict[str, Any], query: str) -> int:
    title = _compact(_title(item))
    q = _compact(query)
    if not title or not q:
        return 0
    if title == q:
        return 10000 + len(title)
    # A generated legal-grounding query commonly has the exact statute title
    # followed by issue words (e.g. "출입국관리법 체류자격외활동 허가").
    if title in q:
        return 8000 + len(title)
    if q in title and len(q) >= 2:
        return 6000 + len(q)

    seed = _compact(_seed_for_query(query))
    if seed:
        if title == seed:
            return 9500 + len(title)
        if title in seed:
            return 7800 + len(title)
        if seed in title and len(seed) >= 2:
            return 5800 + len(seed)
    return 0


def _total_count(payload: Any) -> Optional[int]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in {"totalcnt", "totalcount", "검색결과개수"}:
                try:
                    return max(0, int(str(value).replace(",", "").strip()))
                except (TypeError, ValueError):
                    pass
        for value in payload.values():
            found = _total_count(value)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _total_count(value)
            if found is not None:
                return found
    return None


def _cache_key(config: Any, gana: str, sort: str, page: int) -> Tuple[str, str, str, int]:
    # Only public/non-secret labels participate in the cache key.
    source = str(getattr(config, "law_api_credential_source", "") or "")
    host = str(getattr(config, "law_api_base_url", "") or "default")
    return (f"{source}:{host}", gana, sort, page)


def _cached_page(
    law_tools: Any,
    *,
    config: Any,
    transport: Any,
    gana: str,
    sort: str,
    page: int,
    query_label: str,
) -> Dict[str, Any]:
    key = _cache_key(config, gana, sort, page)
    now = time.monotonic()
    cached = _PAGE_CACHE.get(key)
    if cached and now - cached[0] <= _CACHE_TTL_SECONDS:
        return cached[1]

    result = law_tools._execute(
        tool="search_laws_cloud_fallback",
        config=config,
        transport=transport,
        path=law_tools._SEARCH_PATH,
        params={
            "target": "law",
            "type": "JSON",
            "display": str(_PAGE_SIZE),
            "page": str(page),
            "sort": sort,
            "gana": gana,
            "mobileYn": "Y",
        },
        target="law",
        query=query_label,
        source_type="law",
        limit=_PAGE_SIZE,
        include_payload=True,
    )
    # Do not cache transport/API failures. A transient outage should heal on the
    # very next request rather than being preserved for 15 minutes.
    if result.get("status") == "ok":
        _PAGE_CACHE[key] = (now, result)
    return result


def _best_matches(rows: Iterable[Dict[str, Any]], query: str, limit: int) -> List[Dict[str, Any]]:
    scored: List[Tuple[int, Dict[str, Any]]] = []
    seen: set = set()
    for item in rows:
        if not isinstance(item, dict):
            continue
        score = _match_score(item, query)
        if score <= 0:
            continue
        key = (
            _compact(_title(item)),
            str(item.get("law_id") or ""),
            str(item.get("law_serial_no") or item.get("reference") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], _compact(_title(pair[1]))))
    return [item for _, item in scored[: max(1, limit)]]


def _dictionary_fallback(
    law_tools: Any,
    *,
    query: str,
    limit: int,
    config: Any,
    transport: Any,
) -> Optional[Dict[str, Any]]:
    gana = _gana_group(query)
    if not gana:
        return None

    collected: List[Dict[str, Any]] = []
    first_success: Optional[Dict[str, Any]] = None
    # Probe both ends first. Exact titles near either edge of a dictionary group
    # are recovered in two calls; deeper pages are scanned only when necessary.
    directions = ("lasc", "ldes")
    totals: Dict[str, Optional[int]] = {"lasc": None, "ldes": None}

    for sort in directions:
        result = _cached_page(
            law_tools, config=config, transport=transport, gana=gana,
            sort=sort, page=1, query_label=query,
        )
        if result.get("status") != "ok":
            continue
        first_success = first_success or result
        rows = result.get("results") or []
        collected.extend(rows)
        totals[sort] = _total_count(result.get("_raw_payload"))
        matches = _best_matches(collected, query, limit)
        if matches and _match_score(matches[0], query) >= 7800:
            return _fallback_result(first_success, matches, query, gana)

    for page in range(2, _MAX_SCAN_PAGES_PER_DIRECTION + 1):
        made_request = False
        for sort in directions:
            total = totals.get(sort)
            if total is not None and (page - 1) * _PAGE_SIZE >= total:
                continue
            made_request = True
            result = _cached_page(
                law_tools, config=config, transport=transport, gana=gana,
                sort=sort, page=page, query_label=query,
            )
            if result.get("status") != "ok":
                continue
            first_success = first_success or result
            collected.extend(result.get("results") or [])
            if totals.get(sort) is None:
                totals[sort] = _total_count(result.get("_raw_payload"))
            matches = _best_matches(collected, query, limit)
            if matches and _match_score(matches[0], query) >= 7800:
                return _fallback_result(first_success, matches, query, gana)
        if not made_request:
            break

    matches = _best_matches(collected, query, limit)
    return _fallback_result(first_success, matches, query, gana) if matches else None


def _fallback_result(
    basis: Optional[Dict[str, Any]],
    matches: List[Dict[str, Any]],
    query: str,
    gana: str,
) -> Dict[str, Any]:
    base = dict(basis or {})
    base.pop("_raw_payload", None)
    source_url = str(base.get("source_url") or "")
    for item in matches:
        if source_url:
            item.setdefault("source_url", source_url)
        item.setdefault("query", query)
    base.update({
        "tool": "search_laws",
        "status": "ok",
        "error_type": "",
        "query": query,
        "target": "law",
        "results": matches,
        "result_count": len(matches),
        "parser_status": "cloud_korean_query_dictionary_fallback",
        "failure_reason": "",
        "fallback_mode": "mobile_gana_local_title_match",
        "fallback_gana": gana,
        "cloud_korean_query_recovered": True,
    })
    return base


def install_cloud_resilient_search(law_tools: Any) -> Callable[..., Dict[str, Any]]:
    """Install an idempotent wrapper around ``law_tools.search_laws``.

    This is intentionally installed from ``services.__init__`` so every normal
    package import (including ``services.law_tools``) sees the same behavior,
    while the large deterministic law-tools module stays untouched.
    """
    current = law_tools.search_laws
    if getattr(current, "_cloud_resilient_search", False):
        return current

    original = current

    def search_laws(
        query: str,
        *,
        target: str = "law",
        response_type: str = "JSON",
        limit: int = 5,
        config: Any = None,
        transport: Any = None,
    ) -> Dict[str, Any]:
        primary = original(
            query,
            target=target,
            response_type=response_type,
            limit=limit,
            config=config,
            transport=transport,
        )
        if str(target or "law") != "law":
            return primary
        if int(primary.get("result_count") or 0) > 0:
            return primary
        q = str(query or "").strip()
        if not q or not re.search(r"[가-힣]", q):
            return primary
        # Only recover the deceptive HTTP-200/empty-search shape. Real transport,
        # auth, parse, or official errors remain explicit and are never hidden.
        error_type = str(primary.get("error_type") or "")
        if error_type not in {"", getattr(law_tools, "LAW_API_NO_RESULTS", "law_api_no_results")}:
            return primary

        cfg = config or law_tools.load_grounding_config()
        fallback = _dictionary_fallback(
            law_tools,
            query=q,
            limit=max(1, min(int(limit or 5), 100)),
            config=cfg,
            transport=transport,
        )
        if fallback:
            fallback["primary_error_type"] = error_type
            fallback["primary_parser_status"] = str(primary.get("parser_status") or "")
            return fallback
        return primary

    setattr(search_laws, "_cloud_resilient_search", True)
    setattr(search_laws, "_cloud_resilient_original", original)
    law_tools.search_laws = search_laws
    return search_laws
