"""Serve a source bundle as law.go.kr DRF responses for the existing-law baseline.

Why a fake *server* and not fake *results*: the existing backend parses DRF
bodies itself (``law_tools._parse_payload``, ``_walk_candidates``,
``_extract_articles``). Handing it pre-parsed results would skip exactly the
code under measurement: an HTML body, an empty body, a ``조문여부 = 전문``
heading unit, the official error envelope the parser does not recognise. So the
bundle is rendered into the response shapes the Open API documents, and every
fault is rendered as the transport event urllib would produce.

The module is standard-library only. The existing-law driver imports it inside
the *backend* interpreter; the runner's tests import it directly. Nothing here
imports backend code.

Shapes follow research-notes/official-api.md §2.1 and the documented
건강가정기본법 ``lawService.do`` sample:

* ``lawSearch.do`` → ``{"LawSearch": {..., "law": [{법령명한글, 법령ID,
  법령일련번호, 공포일자, 시행일자, 법령구분명, 현행연혁코드, ...}]}}``;
* ``lawService.do`` → ``{"법령": {"기본정보": {...}, "조문": {"조문단위": [...]},
  "부칙": {"부칙단위": [...]}, "별표": {"별표단위": [...]}}}``.

Known approximations, also listed in 12-evaluation-methodology.md §6:

* title search is containment of the query in the *current* official title,
  or exact equality with a 약칭; former titles are never searchable;
* an ``ID=`` lookup also accepts a version id, so a synthetic non-numeric
  version id does not create a failure the real API would not have;
* the backend fetches a whole law (``lawService.do``) and filters the cited
  article locally, so an article never travels in the URL. A ``get_provision``
  fault that names a ``provision_key`` is applied to the ``lawService.do``
  request the backend makes *while it looks up that article*: the driver sets
  ``requested_article`` around each ``law_tools.get_law_detail`` call. A fault
  without a ``provision_key`` applies to every detail request for the law. A
  fault whose provision is never requested is never served (and the WLIE
  adapter behaves the same way: a match key the call does not carry never
  matches);
* ``unavailable_budget`` has no transport form; it is rendered as a network
  failure;
* a version whose ``parse_status`` is not ``complete`` is served with only the
  provisions the bundle captured. The server records it (``partial_versions``)
  so the report can say that a missing article there is a fixture gap.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlsplit

from waymaker_ai.contracts import LEGISLATIVE_FAMILIES, SourceFamily, compact, parse_date

SEARCH_PATH = "/DRF/lawSearch.do"
SERVICE_PATH = "/DRF/lawService.do"

#: Transport events. ``body`` is an HTTP 200 with a body; the others are what
#: ``urllib`` raises (HTTPError, a timeout, a connection failure).
EVENT_BODY = "body"
EVENT_HTTP_ERROR = "http_error"
EVENT_TIMEOUT = "timeout"
EVENT_NETWORK = "network"

#: Synthetic maintenance page. Its wording is invented; only its *shape*
#: (an HTML document answering a JSON request) matters to the parser.
HTML_PAGE = (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>evaluation fixture</title></head>"
    "<body><p>synthetic maintenance page served by the evaluation fake</p></body></html>"
)

#: The missing-OC envelope observed live on 2026-10-19 (HTTP 200, no
#: resultCode). research-notes/official-api.md, verification pass V-E.
#: 출처: 법제처 국가법령정보센터 (law.go.kr).
OBSERVED_ERROR_ENVELOPE = json.dumps(
    {"result": "필수입력요소 검증에 실패하였습니다.", "msg": "필수 입력값이 존재하지 않습니다. 요청 URL을 확인해 주세요."},
    ensure_ascii=False,
)

#: Answer for an MST / ID the bundle does not hold: a JSON body with no law
#: record (no 기본정보). The official wording for this case was not captured,
#: so the text is an obviously synthetic stand-in; only the shape matters.
NO_SUCH_LAW_BODY = json.dumps({"Law": "evaluation fixture: no law record for this id"}, ensure_ascii=False)

MALFORMED_JSON_BODY = '{"LawSearch": {"law": [{"법령명한글": "'
MALFORMED_XML_BODY = '<?xml version="1.0" encoding="UTF-8"?><LawSearch><law><법령명한글>'

#: raw_body_kind → (event, HTTP status, body)
BODY_KIND_EVENTS: Dict[str, Tuple[str, int, str]] = {
    "html": (EVENT_BODY, 200, HTML_PAGE),
    "empty": (EVENT_BODY, 200, ""),
    "malformed_json": (EVENT_BODY, 200, MALFORMED_JSON_BODY),
    "malformed_xml": (EVENT_BODY, 200, MALFORMED_XML_BODY),
    "http_429": (EVENT_HTTP_ERROR, 429, ""),
    "http_500": (EVENT_HTTP_ERROR, 500, ""),
    "timeout": (EVENT_TIMEOUT, 0, ""),
    "official_error": (EVENT_BODY, 200, OBSERVED_ERROR_ENVELOPE),
}

#: LookupStatus value → (event, HTTP status, body), used when a fault gives no
#: raw_body_kind. ``not_found`` is handled separately (an authoritative empty
#: answer, not a failure).
STATUS_EVENTS: Dict[str, Tuple[str, int, str]] = {
    "unavailable_network": (EVENT_NETWORK, 0, ""),
    "unavailable_timeout": (EVENT_TIMEOUT, 0, ""),
    "unavailable_auth": (EVENT_BODY, 200, OBSERVED_ERROR_ENVELOPE),
    "unavailable_rate_limited": (EVENT_HTTP_ERROR, 429, ""),
    "unavailable_parse": (EVENT_BODY, 200, HTML_PAGE),
    "unavailable_budget": (EVENT_NETWORK, 0, ""),
    "upstream_error": (EVENT_HTTP_ERROR, 500, ""),
}

_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


@dataclass(frozen=True)
class DrfReply:
    event: str                 # EVENT_*
    status: int                # HTTP status (0 for timeout / network)
    body: str
    operation: str             # "search" | "service" | "other"
    fault: Optional[str] = None  # fault detail when a bundle fault produced this reply


@dataclass
class _Version:
    stable_id: str
    version_id: str
    effective_date: Optional[dt.date]
    record: Mapping[str, Any]

    @property
    def is_repeal(self) -> bool:
        return bool(self.record.get("is_repeal"))


@dataclass
class FakeDrfServer:
    """Answers DRF URLs from one bundle, as of ``reference_date`` (the simulated today)."""

    bundle: Mapping[str, Any]
    reference_date: Optional[dt.date] = None
    #: The article the backend is looking up right now (set by the driver), or None.
    requested_article: Optional[str] = None
    #: stable ids this server answered about (search rows and detail lookups)
    touched: set = field(default_factory=set, init=False)
    #: versions served whose bundle text is not completely parsed: the payload
    #: then holds only the captured provisions, so a missing article in it is
    #: a fixture gap, not evidence that the article does not exist
    partial_versions: set = field(default_factory=set, init=False)
    _identities: Dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False)
    _versions: Dict[str, List[_Version]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for identity in self.bundle.get("identities") or []:
            self._identities[str(identity["stable_id"])] = identity
        for record in self.bundle.get("versions") or []:
            version = _Version(str(record["stable_id"]), str(record["version_id"]),
                               parse_date(record.get("effective_date")), record)
            self._versions.setdefault(version.stable_id, []).append(version)
        for versions in self._versions.values():
            versions.sort(key=_version_order)

    # -- dispatch -----------------------------------------------------------
    def respond(self, url: str) -> DrfReply:
        parts = urlsplit(url)
        params = {key: value for key, value in parse_qsl(parts.query, keep_blank_values=True)}
        if parts.path.endswith(SEARCH_PATH):
            return self._search(params)
        if parts.path.endswith(SERVICE_PATH):
            return self._service(params)
        return DrfReply(EVENT_HTTP_ERROR, 404, "", "other")

    # -- lawSearch.do ---------------------------------------------------------
    def _search(self, params: Mapping[str, str]) -> DrfReply:
        """A title query, or (no query) the 가나다 dictionary listing.

        The backend's cloud fallback (``law_cloud_fallback``) pages the
        dictionary listing (``gana``, ``sort``, ``page``) when a Korean query
        comes back empty, then matches titles locally. Serving that listing is
        what lets the evaluation see its near-title matches.
        """
        query = params.get("query") or ""
        target = params.get("target") or "law"
        if target != "law":
            matches: List[Tuple[Mapping[str, Any], _Version]] = []
        elif query:
            matches = self._title_matches(query)
        else:
            matches = self._dictionary(params.get("gana") or "", params.get("sort") or "lasc")
        fault = self._fault("resolve_title", title=query if query else None,
                            stable_ids=[i["stable_id"] for i, _ in matches])
        if fault is not None:
            if fault.get("status") == "not_found":
                return DrfReply(EVENT_BODY, 200, self._search_body(query, [], 0, 1), "search", _fault_detail(fault))
            return _fault_reply(fault, "search")
        display = _bounded_int(params.get("display"), default=20, low=1, high=100)
        page = _bounded_int(params.get("page"), default=1, low=1, high=10_000)
        rows = matches[(page - 1) * display: page * display]
        self.touched.update(str(identity["stable_id"]) for identity, _ in rows)
        return DrfReply(EVENT_BODY, 200, self._search_body(query, rows, len(matches), page), "search")

    def _current_legislative(self) -> List[Tuple[Mapping[str, Any], _Version]]:
        found = []
        for stable_id in sorted(self._identities):
            identity = self._identities[stable_id]
            if not _is_legislative(identity):
                continue
            current = self.current_version(stable_id)
            if current is None or current.is_repeal:
                continue
            found.append((identity, current))
        # The real list is ordered 가나다 by title, not by relevance.
        found.sort(key=lambda pair: (compact(pair[0].get("official_title") or ""), pair[0]["stable_id"]))
        return found

    def _title_matches(self, query: str) -> List[Tuple[Mapping[str, Any], _Version]]:
        key = compact(query)
        if not key:
            return []
        found = []
        for identity, current in self._current_legislative():
            titles = [compact(t) for t in identity.get("short_titles") or []]
            if key in compact(identity.get("official_title") or "") or key in titles:
                found.append((identity, current))
        return found

    def _dictionary(self, gana: str, sort: str) -> List[Tuple[Mapping[str, Any], _Version]]:
        hidden = self._titles_declared_absent()
        rows = [pair for pair in self._current_legislative()
                if (not gana or gana_group(pair[0].get("official_title") or "") == gana)
                and compact(pair[0].get("official_title") or "") not in hidden]
        return list(reversed(rows)) if sort == "ldes" else rows

    def _titles_declared_absent(self) -> frozenset:
        """Titles a ``not_found`` resolve_title fault removes from the index, listing included."""
        return frozenset(compact(str((f.get("match") or {}).get("title") or ""))
                         for f in self.bundle.get("faults") or []
                         if f.get("operation") == "resolve_title" and f.get("status") == "not_found"
                         and (f.get("match") or {}).get("title"))

    def _search_body(self, query: str, rows: Sequence[Tuple[Mapping[str, Any], _Version]], total: int,
                     page: int) -> str:
        envelope: Dict[str, Any] = {
            "target": "law",
            "키워드": query,
            "section": "lawNm",
            "totalCnt": str(total),
            "page": str(page),
            "resultCode": "00",
            "resultMsg": "success",
        }
        if rows:
            envelope["law"] = [_search_row(index, identity, version) for index, (identity, version) in enumerate(rows, start=1)]
        return json.dumps({"LawSearch": envelope}, ensure_ascii=False)

    # -- lawService.do --------------------------------------------------------
    def _service(self, params: Mapping[str, str]) -> DrfReply:
        version = self._lookup_version(params.get("MST") or "", params.get("ID") or "")
        stable_id = version.stable_id if version else None
        if stable_id:
            self.touched.add(stable_id)
        fault = self._fault("get_provision", stable_ids=[stable_id] if stable_id else [],
                            provision_key=self.requested_article)
        dropped: Optional[str] = None
        if fault is not None:
            if fault.get("status") != "not_found":
                return _fault_reply(fault, "service")
            dropped = str((fault.get("match") or {}).get("provision_key") or "*")
        if version is None:
            return DrfReply(EVENT_BODY, 200, NO_SUCH_LAW_BODY, "service")
        if version.record.get("parse_status") != "complete":
            effective = version.effective_date.isoformat() if version.effective_date else "-"
            self.partial_versions.add(f"{version.stable_id}@{version.version_id}:{effective}")
        body = self.service_payload(version, drop_provision=dropped)
        return DrfReply(EVENT_BODY, 200, json.dumps(body, ensure_ascii=False), "service",
                        _fault_detail(fault) if fault is not None else None)

    def _lookup_version(self, mst: str, law_id: str) -> Optional[_Version]:
        if mst:
            return self._pick(v for vs in self._versions.values() for v in vs if v.version_id == mst)
        if law_id:
            if law_id in self._identities:
                return self.current_version(law_id)
            return self._pick(v for vs in self._versions.values() for v in vs if v.version_id == law_id)
        return None

    def _pick(self, candidates) -> Optional[_Version]:
        """The latest candidate in force on the reference date, else the earliest one."""
        ordered = sorted(candidates, key=_version_order)
        if not ordered:
            return None
        in_force = [v for v in ordered if self._in_force(v)]
        return in_force[-1] if in_force else ordered[0]

    def current_version(self, stable_id: str) -> Optional[_Version]:
        in_force = [v for v in self._versions.get(stable_id, []) if self._in_force(v)]
        return in_force[-1] if in_force else None

    def _in_force(self, version: _Version) -> bool:
        if version.effective_date is None:
            return False
        return self.reference_date is None or version.effective_date <= self.reference_date

    def service_payload(self, version: _Version, *, drop_provision: Optional[str] = None) -> Dict[str, Any]:
        identity = self._identities.get(version.stable_id, {})
        record = version.record
        units = self._units(version, drop_provision)
        payload: Dict[str, Any] = {
            # 기본정보 must come first: the backend's candidate walk stops at the
            # first dict that carries a law name.
            "기본정보": {
                "법령ID": version.stable_id,
                "법령명_한글": identity.get("official_title") or "",
                "법령명약칭": _first_or_empty(identity.get("short_titles")),
                "공포일자": _yyyymmdd(record.get("promulgation_date")),
                "공포번호": _digits(record.get("promulgation_no")),
                "시행일자": _yyyymmdd(record.get("effective_date")),
                "제개정구분": record.get("amendment_type") or "",
                "법종구분": {"content": _division(identity)},
                "소관부처": {"content": identity.get("competent_ministry") or ""},
                "제명변경여부": "N",
            },
            "조문": {"조문단위": units["articles"]},
        }
        if units["addenda"]:
            payload["부칙"] = {"부칙단위": units["addenda"]}
        if units["annexes"]:
            payload["별표"] = {"별표단위": units["annexes"]}
        return {"법령": payload}

    def _units(self, version: _Version, drop_provision: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
        own = [p for p in self.bundle.get("provisions") or [] if _belongs(p, version)]
        if drop_provision == "*":
            own = [p for p in own if p.get("unit_kind") not in ("article", "annex")]
        elif drop_provision:
            own = [p for p in own if compact(str(p.get("provision_key") or "")) != compact(drop_provision)]
        articles: List[Dict[str, Any]] = []
        annexes: List[Dict[str, Any]] = []
        numbers = [_article_number(str(p.get("provision_key") or "")) if p.get("unit_kind") == "article" else None for p in own]
        for index, provision in enumerate(own):
            kind = provision.get("unit_kind") or "article"
            if kind == "article" and numbers[index] is not None:
                articles.append(_article_unit(provision, numbers[index], version))
            elif kind == "heading":
                articles.append(_heading_unit(provision, _nearest_number(numbers, index)))
            elif kind == "annex":
                annexes.append({"별표키": compact(str(provision.get("provision_key") or "")),
                                "별표제목": provision.get("heading") or "",
                                "별표내용": provision.get("text") or ""})
        addenda = [
            {"부칙공포일자": _yyyymmdd(version.record.get("promulgation_date")),
             "부칙공포번호": _digits(version.record.get("promulgation_no")),
             "부칙내용": [[str(a.get("text") or "")]]}
            for a in self.bundle.get("addenda") or [] if _belongs(a, version)
        ]
        return {"articles": articles, "annexes": annexes, "addenda": addenda}

    # -- faults ---------------------------------------------------------------
    def _fault(self, operation: str, *, title: Optional[str] = None, stable_ids: Sequence[Optional[str]] = (),
               provision_key: Optional[str] = None) -> Optional[Mapping[str, Any]]:
        """The first bundle fault for this request. A match key the request does not carry never matches."""
        for fault in self.bundle.get("faults") or []:
            if fault.get("operation") != operation:
                continue
            match = fault.get("match") or {}
            if match.get("title") and not _same(match["title"], title):
                continue
            if match.get("stable_id") and str(match["stable_id"]) not in {str(s) for s in stable_ids if s}:
                continue
            if match.get("provision_key") and not _same(match["provision_key"], provision_key):
                continue
            return fault
        return None

    def unexercised_faults(self) -> List[str]:
        """Faults on laws the backend looked at, on operations it never performs (history, 부칙).

        The backend asks for no version history, no 부칙 on their own and no
        guidance, so a fault scripted for those operations cannot reach it.
        Reported per item only for laws this item touched, so that the note
        explains this item's result rather than repeating the whole bundle.
        """
        found = set()
        for fault in self.bundle.get("faults") or []:
            if fault.get("operation") in ("resolve_title", "get_provision"):
                continue
            stable_id = (fault.get("match") or {}).get("stable_id")
            if stable_id and str(stable_id) in self.touched:
                found.add(f"{fault.get('operation')}:{stable_id}")
        return sorted(found)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
#: 가나다 groups of the 19 Hangul initial consonants (ㄲ, ㄸ, ㅃ, ㅆ, ㅉ share
#: the group of their plain consonant), as the dictionary listing's ``gana``
#: filter uses them.
_GANA_BY_INITIAL = ("ga", "ga", "na", "da", "da", "ra", "ma", "ba", "ba", "sa", "sa", "a",
                    "ja", "ja", "cha", "ka", "ta", "pa", "ha")


def gana_group(title: str) -> str:
    """The 가나다 group of a title's first Hangul syllable, or ""."""
    for ch in title:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            return _GANA_BY_INITIAL[(code - 0xAC00) // 588]
    return ""


def _same(expected: Any, actual: Optional[str]) -> bool:
    return actual is not None and compact(str(expected)) == compact(actual)


def _bounded_int(value: Any, *, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(number, high))


def _version_order(version: _Version) -> Tuple[str, str]:
    return (version.effective_date.isoformat() if version.effective_date else "", version.version_id)


def _belongs(record: Mapping[str, Any], version: _Version) -> bool:
    if str(record.get("stable_id")) != version.stable_id or str(record.get("version_id")) != version.version_id:
        return False
    effective = parse_date(record.get("effective_date"))
    return effective is None or effective == version.effective_date


def _is_legislative(identity: Mapping[str, Any]) -> bool:
    try:
        return SourceFamily(identity.get("family")) in LEGISLATIVE_FAMILIES
    except ValueError:
        return False


def _division(identity: Mapping[str, Any]) -> str:
    family = identity.get("family")
    if family == SourceFamily.STATUTE.value:
        return "법률"
    if family == SourceFamily.ENFORCEMENT_DECREE.value:
        return "대통령령"
    if family == SourceFamily.ENFORCEMENT_RULE.value:
        ministry = str(identity.get("competent_ministry") or "")
        return f"{ministry}령" if ministry.endswith("부") else "부령"
    return ""


def _search_row(index: int, identity: Mapping[str, Any], version: _Version) -> Dict[str, Any]:
    record = version.record
    return {
        "id": str(index),
        "법령일련번호": version.version_id,
        "현행연혁코드": "현행",
        "법령명한글": identity.get("official_title") or "",
        "법령약칭명": _first_or_empty(identity.get("short_titles")),
        "법령ID": version.stable_id,
        "공포일자": _yyyymmdd(record.get("promulgation_date")),
        "공포번호": _digits(record.get("promulgation_no")),
        "제개정구분명": record.get("amendment_type") or "",
        "소관부처명": identity.get("competent_ministry") or "",
        "법령구분명": _division(identity),
        "시행일자": _yyyymmdd(record.get("effective_date")),
        "법령상세링크": f"/DRF/lawService.do?target=law&MST={version.version_id}&type=HTML",
    }


def _article_number(key: str) -> Optional[Tuple[int, int]]:
    """``제73조`` → (73, 0); ``제21조의2`` → (21, 2); anything else → None."""
    text = compact(key)
    if not text.startswith("제"):
        return None
    pos = 1
    while pos < len(text) and text[pos].isdigit():
        pos += 1
    if pos == 1 or pos >= len(text) or text[pos] != "조":
        return None
    article = int(text[1:pos])
    rest = text[pos + 1:]
    if not rest:
        return article, 0
    if rest.startswith("의") and rest[1:].isdigit():
        return article, int(rest[1:])
    return None


def _nearest_number(numbers: Sequence[Optional[Tuple[int, int]]], index: int) -> Tuple[int, int]:
    """A heading unit carries the number of the article that follows it (as the real API does)."""
    for value in list(numbers[index + 1:]) + list(reversed(numbers[:index])):
        if value is not None:
            return value
    return (0, 0)


def _article_unit(provision: Mapping[str, Any], number: Tuple[int, int], version: _Version) -> Dict[str, Any]:
    article, branch = number
    key = str(provision.get("provision_key") or "")
    heading = provision.get("heading") or ""
    text = str(provision.get("text") or "")
    if not compact(text).startswith(compact(key)):
        text = f"{key}({heading}) {text}" if heading else f"{key} {text}"
    effective = (version.record.get("provision_effective_dates") or {}).get(key) or provision.get("effective_date")
    unit: Dict[str, Any] = {
        "조문번호": str(article),
        "조문여부": "조문",
        "조문제목": heading,
        "조문내용": text,
        "조문시행일자": _yyyymmdd(effective),
        "조문키": f"{article:04d}{branch:02d}1",
    }
    if branch:
        unit["조문가지번호"] = str(branch)
    paragraphs = _paragraph_units(provision.get("paragraphs") or {}, provision.get("items") or {})
    if paragraphs is not None:
        unit["항"] = paragraphs
    return unit


def _heading_unit(provision: Mapping[str, Any], number: Tuple[int, int]) -> Dict[str, Any]:
    article, branch = number
    return {
        "조문번호": str(article),
        "조문여부": "전문",
        "조문내용": str(provision.get("text") or provision.get("heading") or ""),
        "조문키": f"{article:04d}{branch:02d}0",
    }


def _paragraph_units(paragraphs: Mapping[str, str], items: Mapping[str, str]) -> Any:
    by_paragraph: Dict[int, List[Dict[str, str]]] = {}
    for key in sorted(items, key=_item_sort_key):
        paragraph, _sep, item = str(key).partition(":")
        by_paragraph.setdefault(_to_int(paragraph), []).append({"호번호": f"{item}.", "호내용": str(items[key])})
    if paragraphs:
        units = []
        for key in sorted(paragraphs, key=_to_int):
            number = _to_int(key)
            unit: Dict[str, Any] = {"항번호": _CIRCLED[number - 1] if 0 < number <= len(_CIRCLED) else str(number),
                                    "항내용": str(paragraphs[key])}
            if by_paragraph.get(number):
                unit["호"] = by_paragraph[number]
            units.append(unit)
        return units
    if by_paragraph.get(0):
        return {"호": by_paragraph[0]}
    return None


def _item_sort_key(key: str) -> Tuple[int, str]:
    paragraph, _sep, item = str(key).partition(":")
    return (_to_int(paragraph), item.zfill(8))


def _to_int(value: Any) -> int:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def _yyyymmdd(value: Any) -> str:
    date = parse_date(value)
    return date.strftime("%Y%m%d") if date else ""


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _first_or_empty(values: Any) -> str:
    return str(values[0]) if values else ""


def _fault_reply(fault: Mapping[str, Any], operation: str) -> DrfReply:
    kind = fault.get("raw_body_kind")
    event, status, body = BODY_KIND_EVENTS.get(kind) if kind in BODY_KIND_EVENTS else STATUS_EVENTS.get(
        str(fault.get("status")), (EVENT_NETWORK, 0, ""))
    return DrfReply(event, status, body, operation, _fault_detail(fault))


def _fault_detail(fault: Mapping[str, Any]) -> str:
    return f"{fault.get('operation')}:{fault.get('status')}:{fault.get('raw_body_kind') or '-'}"
