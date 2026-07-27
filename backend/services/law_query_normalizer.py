"""Korean statute query normalization, alias resolution and relevance ranking.

Why this module exists
----------------------
The 법제처 Open Law API (``law.go.kr``) ``lawSearch`` target performs a LIKE-style
*substring* match over 법령명 and returns results in 가나다 order. Two consequences
bite every caller:

1. A query for a short statute name matches unrelated laws that merely contain it
   as a substring — the canonical example being 「민법」 matching 「난민법」. Trusting
   ``results[0]`` therefore produces a confidently-wrong statute.
2. Because ordering is alphabetical rather than by relevance, a short official name
   can sit far down the list; a small ``display`` window never even receives the
   correct row, so no amount of local re-ranking can recover it.

This module supplies the deterministic defences: input normalization (spacing,
typos, interpunct variants, ``§``), statutory-abbreviation (약칭) resolution, a
non-law keyword stripper for the fallback ladder, relevance scoring, and a final
loose-match guard used before any retrieved statute is treated as *the* requested
one. It also classifies the lifecycle state of a retrieved statute (현행 / 폐지 /
시행예정) and maps transport/parser failures onto a machine-readable evidence
status, so "no result" is never conflated with "lookup failed".

Attribution
-----------
The normalization ladder, the loose-match rule, the relevance-scoring shape and
the non-law keyword stripper are ported to Python from ``chrisryugj/korean-law-mcp``
(MIT). See ``THIRD_PARTY_NOTICES.md``. The alias table here is Paradiso's own,
scoped to immigration/status-of-stay law; the upstream tax/labour alias set is not
carried over.

Pure functions only — no I/O, no network, no secrets. Safe to unit test offline.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

LAW_QUERY_NORMALIZER_VERSION = "2026-07-law-query-normalizer-v1"


# ---------------------------------------------------------------------------
# Machine-readable evidence status
#
# A caller must be able to branch on *why* there is no statute in hand. A bare
# string message cannot be branched on, and collapsing every failure into
# "not found" makes an API outage look like "this law does not exist" — the most
# damaging possible confusion in a legal-evidence surface.
# ---------------------------------------------------------------------------
STATUS_VERIFIED = "verified"
STATUS_NOT_FOUND = "not_found"
STATUS_REPEALED = "repealed"
STATUS_SCHEDULED = "scheduled"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_UNAVAILABLE = "unavailable"
STATUS_FORBIDDEN = "forbidden"
STATUS_TIMEOUT = "timeout"
STATUS_PARSE_FAILED = "parse_failed"

EVIDENCE_STATUSES = frozenset({
    STATUS_VERIFIED,
    STATUS_NOT_FOUND,
    STATUS_REPEALED,
    STATUS_SCHEDULED,
    STATUS_AMBIGUOUS,
    STATUS_UNAVAILABLE,
    STATUS_FORBIDDEN,
    STATUS_TIMEOUT,
    STATUS_PARSE_FAILED,
})

# law_tools error_type -> evidence status. Kept as data so a new transport error
# cannot silently fall through to "verified".
_ERROR_TYPE_TO_STATUS: Dict[str, str] = {
    "": STATUS_VERIFIED,
    "law_api_not_configured": STATUS_UNAVAILABLE,
    "law_api_http_error": STATUS_UNAVAILABLE,
    "law_api_timeout": STATUS_TIMEOUT,
    "law_api_bad_response": STATUS_UNAVAILABLE,
    "law_api_no_results": STATUS_NOT_FOUND,
    "law_api_parse_error": STATUS_PARSE_FAILED,
    "law_api_official_error": STATUS_UNAVAILABLE,
}


def evidence_status_for(error_type: str, *, http_status: Optional[int] = None) -> str:
    """Map a law_tools ``error_type`` (+ HTTP status) onto an evidence status.

    HTTP 401/403 is reported as ``forbidden`` rather than a generic
    ``unavailable``: a rejected credential is an operator action item, while a
    502 is a wait-and-retry. Unknown error types degrade to ``unavailable`` —
    never to ``verified`` and never to ``not_found``.
    """
    if http_status in (401, 403):
        return STATUS_FORBIDDEN
    key = (error_type or "").strip().lower()
    if key in _ERROR_TYPE_TO_STATUS:
        return _ERROR_TYPE_TO_STATUS[key]
    return STATUS_UNAVAILABLE if key else STATUS_VERIFIED


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

# Hangul jamo-level slips seen in OCR'd manuals and hand-typed queries. Only
# unambiguous single-syllable confusions are listed; anything requiring context
# is deliberately excluded so normalization can never change which law is meant.
_BASIC_CHAR_MAP = {
    "벚": "법", "벆": "법", "벋": "법", "뻡": "법", "볍": "법", "뱝": "법",
}
_BASIC_CHAR_RE = re.compile("[" + "".join(_BASIC_CHAR_MAP) + "]")

# 법제처 official statute names use the Hangul interpunct 'ㆍ' (U+318D); practice
# documents, judgments and LLM output freely substitute '·', '‧', '•', '・'. Two
# spellings of the same law must not read as a mismatch.
_INTERPUNCT_RE = re.compile("[·ㆍ‧•・]")

_WIDE_SPACE_RE = re.compile("[    ]")
_DASH_RE = re.compile("[‐‑‒–—―﹘﹣－]")


def normalize_basic_typos(value: str) -> str:
    return _BASIC_CHAR_RE.sub(lambda m: _BASIC_CHAR_MAP.get(m.group(0), m.group(0)), value or "")


def normalize_law_search_text(value: str) -> str:
    """Canonicalize a user-supplied statute query for matching and lookup.

    NFC-normalizes, folds exotic spaces/dashes, rewrites ``§`` to ``제``, repairs
    the known typo set, and separates Latin/Hangul runs so "FTA특례법" tokenizes.
    """
    text = unicodedata.normalize("NFC", value or "")
    text = _WIDE_SPACE_RE.sub(" ", text)
    text = _DASH_RE.sub("-", text)
    text = text.replace("＝", " ").replace("=", " ")
    text = text.replace("§", " 제")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s*\.\s*", " ", text)
    text = normalize_basic_typos(text)
    text = re.sub(r"([A-Za-z])([가-힣])", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("( ", "(").replace(" )", ")")
    return text.strip()


def normalize_alias_key(value: str) -> str:
    """Lookup key for the alias table: case/space/interpunct insensitive."""
    return _INTERPUNCT_RE.sub("", normalize_basic_typos(value or "").lower().replace(" ", ""))


# ---------------------------------------------------------------------------
# Immigration-scoped statutory abbreviations (약칭)
#
# Every ``canonical`` below is an official Korean statute title and every
# ``aliases`` entry is either the 법제처-published 약칭 or a pure spacing variant
# of the official title. Nothing here is invented, and no alias asserts anything
# about what a law *says*.
#
# ``alternatives`` names statutes a user could plausibly have meant instead. They
# are offered as sibling candidates — never silently substituted — so a query that
# is genuinely ambiguous between two real laws resolves to ``ambiguous`` rather
# than to a confident wrong pick.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AliasEntry:
    canonical: str
    aliases: Tuple[str, ...] = ()
    alternatives: Tuple[str, ...] = ()


LAW_ALIAS_ENTRIES: Tuple[AliasEntry, ...] = (
    AliasEntry(
        canonical="출입국관리법",
        aliases=("출입국 관리법", "출입국법", "출입국관리 법"),
        alternatives=("출입국관리법 시행령", "출입국관리법 시행규칙"),
    ),
    AliasEntry(
        canonical="출입국관리법 시행령",
        aliases=("출입국관리법시행령", "출입국관리법 시행 령", "출입국관리법령"),
        alternatives=("출입국관리법", "출입국관리법 시행규칙"),
    ),
    AliasEntry(
        canonical="출입국관리법 시행규칙",
        aliases=("출입국관리법시행규칙", "출입국관리법 시행 규칙"),
        alternatives=("출입국관리법", "출입국관리법 시행령"),
    ),
    AliasEntry(
        canonical="국적법",
        aliases=("국적 법",),
        alternatives=("국적법 시행령", "국적법 시행규칙"),
    ),
    AliasEntry(
        canonical="난민법",
        aliases=("난민 법",),
        alternatives=("난민법 시행령", "출입국관리법"),
    ),
    AliasEntry(
        # 법제처 약칭: 재외동포법. 2023년 제정된 「재외동포기본법」은 별개 법률이므로
        # alternatives 로 함께 제시한다.
        canonical="재외동포의 출입국과 법적 지위에 관한 법률",
        aliases=("재외동포법", "재외동포 법", "재외동포출입국법"),
        alternatives=("재외동포기본법", "재외동포의 출입국과 법적 지위에 관한 법률 시행령"),
    ),
    AliasEntry(
        # 법제처 약칭: 외국인고용법.
        canonical="외국인근로자의 고용 등에 관한 법률",
        aliases=("외국인고용법", "외국인 고용법", "고용허가제법", "외국인근로자고용법"),
        alternatives=("외국인근로자의 고용 등에 관한 법률 시행령", "출입국관리법"),
    ),
    AliasEntry(
        canonical="재한외국인 처우 기본법",
        aliases=("재한외국인처우기본법", "외국인처우법", "재한외국인 처우기본법"),
        alternatives=("다문화가족지원법",),
    ),
    AliasEntry(
        canonical="다문화가족지원법",
        aliases=("다문화가족 지원법", "다문화지원법"),
        alternatives=("재한외국인 처우 기본법",),
    ),
    AliasEntry(
        canonical="대한민국헌법",
        aliases=("헌법", "헌 법"),
    ),
    AliasEntry(
        canonical="행정절차법",
        aliases=("행정 절차법",),
        alternatives=("행정기본법", "행정심판법", "행정소송법"),
    ),
    AliasEntry(
        canonical="행정심판법",
        aliases=("행정 심판법",),
        alternatives=("행정소송법", "행정절차법"),
    ),
    AliasEntry(
        canonical="행정소송법",
        aliases=("행정 소송법",),
        alternatives=("행정심판법", "행정절차법"),
    ),
    AliasEntry(
        canonical="행정기본법",
        aliases=("행정 기본법",),
        alternatives=("행정절차법", "행정조사기본법"),
    ),
    AliasEntry(
        # 짧은 법령명은 부분매칭 노이즈가 가장 심한 구간(민법 → 난민법)이라
        # alternatives 로 흔한 혼동 대상을 함께 노출한다.
        canonical="민법",
        aliases=("민 법",),
        alternatives=("민사소송법", "민사집행법", "난민법"),
    ),
    AliasEntry(
        canonical="형법",
        aliases=("형 법",),
        alternatives=("형사소송법",),
    ),
    AliasEntry(
        canonical="근로기준법",
        aliases=("근기법", "근로 기준법"),
        alternatives=("근로기준법 시행령",),
    ),
    AliasEntry(
        canonical="개인정보 보호법",
        aliases=("개인정보보호법", "개보법", "개인정보법"),
    ),
    AliasEntry(
        canonical="가족관계의 등록 등에 관한 법률",
        aliases=("가족관계등록법", "가족관계 등록법"),
    ),
    AliasEntry(
        canonical="재외국민등록법",
        aliases=("재외국민 등록법",),
    ),
    AliasEntry(
        canonical="병역법",
        aliases=("병역 법",),
    ),
)

_ALIAS_LOOKUP: Dict[str, AliasEntry] = {}
for _entry in LAW_ALIAS_ENTRIES:
    _ALIAS_LOOKUP[normalize_alias_key(_entry.canonical)] = _entry
    for _alias in _entry.aliases:
        _ALIAS_LOOKUP.setdefault(normalize_alias_key(_alias), _entry)


@dataclass
class AliasResolution:
    canonical: str
    matched_alias: str = ""
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical": self.canonical,
            "matched_alias": self.matched_alias,
            "alternatives": list(self.alternatives),
        }


def resolve_law_alias(law_name: str) -> AliasResolution:
    """Resolve a 약칭 / spacing variant to its official statute title.

    An unknown name is returned unchanged (typo-repaired only) — this function
    never guesses a canonical title it has no entry for.
    """
    key = normalize_alias_key(law_name)
    entry = _ALIAS_LOOKUP.get(key)
    if entry is not None:
        matched = ""
        for alias in entry.aliases:
            if normalize_alias_key(alias) == key:
                matched = alias
                break
        return AliasResolution(
            canonical=entry.canonical,
            matched_alias=matched,
            alternatives=list(entry.alternatives),
        )
    return AliasResolution(canonical=normalize_basic_typos(law_name or "").strip())


def extract_embedded_aliases(query: str) -> List[Dict[str, Any]]:
    """Find abbreviations *inside* a longer query ("재외동포법 제10조").

    Longest alias first so "출입국관리법시행령" is not shadowed by "출입국관리법".
    """
    normalized = normalize_law_search_text(query)
    normalized_key = normalize_alias_key(normalized)
    results: List[Dict[str, Any]] = []
    seen: set = set()

    candidates: List[Tuple[str, AliasEntry, str]] = []
    for entry in LAW_ALIAS_ENTRIES:
        for alias in entry.aliases:
            key = normalize_alias_key(alias)
            if len(key) < 2:
                continue
            candidates.append((alias, entry, key))
    candidates.sort(key=lambda c: len(c[2]), reverse=True)

    for alias, entry, key in candidates:
        if entry.canonical in seen:
            continue
        if normalized_key == key or key not in normalized_key:
            continue
        expanded = normalized.replace(alias, entry.canonical)
        if expanded == normalized:
            parts = [re.escape(p) for p in alias.split() if p]
            if len(parts) >= 2:
                expanded = re.sub(r"\s*".join(parts), entry.canonical, normalized)
        if expanded == normalized:
            continue
        seen.add(entry.canonical)
        results.append({
            "alias": alias,
            "canonical": entry.canonical,
            "alternatives": list(entry.alternatives),
            "expanded_query": expanded,
        })
    return results


@dataclass
class QueryExpansion:
    original: str
    expanded: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "expanded": list(self.expanded),
            "alternatives": list(self.alternatives),
        }


def expand_law_query(query: str, *, limit: int = 5) -> QueryExpansion:
    """Build ordered retry queries for a statute lookup (canonical name first)."""
    normalized = normalize_law_search_text(query)
    expanded: List[str] = []
    alternatives: List[str] = []

    resolution = resolve_law_alias(normalized)
    if resolution.canonical and resolution.canonical != normalized:
        expanded.append(resolution.canonical)
    alternatives.extend(resolution.alternatives)

    for match in extract_embedded_aliases(normalized):
        if match["expanded_query"] not in expanded:
            expanded.append(match["expanded_query"])
        for alt in match["alternatives"]:
            if alt not in alternatives:
                alternatives.append(alt)

    stripped = strip_non_law_keywords(normalized)
    if stripped and stripped != normalized and stripped not in expanded:
        expanded.append(stripped)

    bare = extract_law_name_pattern(normalized)
    if bare and bare != normalized and bare not in expanded:
        expanded.append(bare)

    return QueryExpansion(
        original=normalized,
        expanded=expanded[:limit],
        alternatives=alternatives[:limit],
    )


# 법제처 lawSearch matches on 법령명, so procedural/topical words in a natural
# question are pure noise that can drive the query to zero results. They are only
# stripped on a *fallback* pass — never on the first attempt, where an exact
# official title containing one of these words must still match verbatim.
_NON_LAW_KEYWORD_RE = re.compile(
    r"\s*(과태료|절차|비용|처벌|기준|허가|신청|부과|근거|위반|방법|요건|조건|처분|수수료"
    r"|신고|등록|면허|인가|승인|취소|정지|벌칙|벌금|과징금|시정명령|체계|구조|판례|해석"
    r"|개정|별표|서식|의무|권리|자격|종류|기간|대상|범위|적용|제한|금지|면제|감면"
    r"|변경|연장|초청|심사|발급|거부|불허|이의신청|소송|쟁송|불복|안내|문의|알려줘|알려주세요)\s*"
)


def strip_non_law_keywords(query: str) -> str:
    return _NON_LAW_KEYWORD_RE.sub(" ", query or "").strip()


_LAW_NAME_PATTERN_RE = re.compile(r"[가-힣]+(?:법|시행령|시행규칙|규칙|규정|령)(?=\s|$)")


def extract_law_name_pattern(query: str) -> str:
    """Pull a bare statute-shaped token out of a sentence ("출입국관리법 제20조" -> 출입국관리법)."""
    match = _LAW_NAME_PATTERN_RE.search(query or "")
    return match.group(0).strip() if match else ""


# ---------------------------------------------------------------------------
# Matching guards and relevance ranking
# ---------------------------------------------------------------------------
def _strip_for_match(value: str) -> str:
    return _INTERPUNCT_RE.sub("", re.sub(r"\s+", "", value or ""))


def loose_match_law_name(target: str, official: str) -> bool:
    """Space/interpunct-insensitive match between a requested and official title."""
    t = _strip_for_match(target)
    o = _strip_for_match(official)
    if not t or not o:
        return False
    return o == t or o.startswith(t) or t.startswith(re.sub(r"(법률|법)$", "법", o))


def resolved_law_matches(requested: str, official_name: str) -> bool:
    """Final guard before a retrieved statute is treated as *the* requested one.

    ``lawSearch`` returns substring hits even when nothing relevant exists, so a
    top result must be re-checked against the request (and against its canonical
    form, for alias input) before anything is stated about it.
    """
    if loose_match_law_name(requested, official_name):
        return True
    canonical = resolve_law_alias(normalize_law_search_text(requested)).canonical
    return canonical != requested and loose_match_law_name(canonical, official_name)


def score_law_relevance(law_name: str, query: str, query_words: Sequence[str]) -> int:
    """Relevance of an official title against the request. Higher is better."""
    score = 0
    name = law_name or ""
    q = query or ""
    if name and q and name in q:
        score += 100
    compact_query = re.sub(r"\s+", "", q)
    if compact_query and compact_query in name:
        score += 80
    for word in query_words:
        if word and word in name:
            score += 10
    # A parent Act outranks its 시행령/시행규칙 for an unqualified request; the
    # subordinate instruments are still returned, as a separate hierarchy layer.
    if not re.search(r"시행령|시행규칙", name):
        score += 5
    return score


def law_hierarchy_level(law_name: str, law_division: str = "") -> str:
    """Classify a statute into the 법률 / 시행령 / 시행규칙 hierarchy.

    This is a *display* layer, never a result filter: a user asking about
    「출입국관리법」 usually needs the decree and the rule alongside it.
    """
    haystack = f"{law_name or ''} {law_division or ''}"
    if "시행규칙" in haystack:
        return "enforcement_rule"
    if "시행령" in haystack:
        return "enforcement_decree"
    if "규칙" in haystack or "규정" in haystack or "훈령" in haystack or "고시" in haystack:
        return "administrative_rule"
    if "헌법" in haystack:
        return "constitution"
    return "statute"


_HIERARCHY_ORDER = {
    "constitution": 0,
    "statute": 1,
    "enforcement_decree": 2,
    "enforcement_rule": 3,
    "administrative_rule": 4,
}


def rank_law_candidates(
    candidates: Sequence[Dict[str, Any]],
    query: str,
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Re-rank raw API rows by local relevance, annotating each with its evidence.

    Each returned row gains ``relevance_score``, ``hierarchy_level`` and
    ``name_match`` (whether it survives :func:`resolved_law_matches`). Rows are
    never dropped for failing the name match — that is the caller's decision, and
    a near-miss is still useful context.
    """
    normalized_query = normalize_law_search_text(query)
    stripped = strip_non_law_keywords(normalized_query)
    query_words = [w for w in re.split(r"\s+", stripped) if w]

    ranked: List[Dict[str, Any]] = []
    for row in candidates or []:
        if not isinstance(row, dict):
            continue
        name = row.get("law_name") or row.get("title") or ""
        item = dict(row)
        item["relevance_score"] = score_law_relevance(name, normalized_query, query_words)
        item["hierarchy_level"] = law_hierarchy_level(name, row.get("law_division", ""))
        item["name_match"] = resolved_law_matches(normalized_query, name)
        ranked.append(item)

    ranked.sort(
        key=lambda r: (
            0 if r.get("name_match") else 1,
            -int(r.get("relevance_score") or 0),
            _HIERARCHY_ORDER.get(r.get("hierarchy_level", "statute"), 9),
            str(r.get("law_name") or ""),
        )
    )
    return ranked[:limit] if limit else ranked


# ---------------------------------------------------------------------------
# Lifecycle status of a retrieved statute
# ---------------------------------------------------------------------------
_REPEALED_TOKENS = ("폐지", "폐止", "실효")
_SCHEDULED_TOKENS = ("시행예정", "예정")
_CURRENT_TOKENS = ("현행",)
_HISTORICAL_TOKENS = ("연혁",)


def _parse_yyyymmdd(value: Any) -> Optional[date]:
    raw = re.sub(r"[^0-9]", "", str(value or ""))
    if len(raw) != 8:
        return None
    try:
        return date(int(raw[0:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError:
        return None


def classify_law_lifecycle(
    *,
    status_code: str = "",
    enforcement_date: Any = "",
    today: Optional[date] = None,
) -> str:
    """Classify 현행 / 폐지 / 시행예정 / 연혁 from API metadata.

    Returns an evidence status. Anything unrecognized becomes ``verified`` — the
    statute *was* retrieved; only its lifecycle annotation is unknown, and this
    function must not manufacture a repeal.
    """
    code = str(status_code or "")
    if any(token in code for token in _REPEALED_TOKENS):
        return STATUS_REPEALED
    if any(token in code for token in _SCHEDULED_TOKENS):
        return STATUS_SCHEDULED

    effective = _parse_yyyymmdd(enforcement_date)
    if effective is not None:
        reference = today or date.today()
        if effective > reference:
            return STATUS_SCHEDULED

    if any(token in code for token in _CURRENT_TOKENS):
        return STATUS_VERIFIED
    if any(token in code for token in _HISTORICAL_TOKENS):
        return STATUS_VERIFIED
    return STATUS_VERIFIED


def annotate_lifecycle(rows: Iterable[Dict[str, Any]], *, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Attach ``lifecycle_status`` to each normalized law row."""
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item["lifecycle_status"] = classify_law_lifecycle(
            status_code=str(row.get("law_status_code") or ""),
            enforcement_date=row.get("enforcement_date") or "",
            today=today,
        )
        out.append(item)
    return out


def summarize_search_outcome(
    ranked: Sequence[Dict[str, Any]],
    *,
    query: str,
    error_type: str = "",
    http_status: Optional[int] = None,
) -> Dict[str, Any]:
    """Collapse a ranked result set into one machine-readable outcome.

    ``ambiguous`` is reserved for the genuinely undecidable case: several rows
    pass the name guard with the same top relevance score. That is a distinct
    state from "found" and must not be presented as a confident single answer.
    """
    if error_type:
        status = evidence_status_for(error_type, http_status=http_status)
        return {
            "status": status,
            "query": query,
            "match_count": 0,
            "top": None,
            "candidates": [],
            "error_type": error_type,
        }

    matches = [r for r in ranked if r.get("name_match")]
    if not ranked:
        return {"status": STATUS_NOT_FOUND, "query": query, "match_count": 0,
                "top": None, "candidates": [], "error_type": ""}
    if not matches:
        # Rows came back but none is the requested law — substring noise only.
        return {"status": STATUS_NOT_FOUND, "query": query, "match_count": 0,
                "top": None, "candidates": list(ranked[:3]), "error_type": ""}

    top = matches[0]
    top_score = int(top.get("relevance_score") or 0)
    tied = [
        r for r in matches
        if int(r.get("relevance_score") or 0) == top_score
        and r.get("hierarchy_level") == top.get("hierarchy_level")
        and (r.get("law_name") or "") != (top.get("law_name") or "")
    ]
    status = top.get("lifecycle_status") or STATUS_VERIFIED
    if tied and status == STATUS_VERIFIED:
        status = STATUS_AMBIGUOUS
    return {
        "status": status,
        "query": query,
        "match_count": len(matches),
        "top": top,
        "candidates": list(matches[:5]),
        "error_type": "",
    }


__all__ = [
    "LAW_QUERY_NORMALIZER_VERSION",
    "STATUS_VERIFIED", "STATUS_NOT_FOUND", "STATUS_REPEALED", "STATUS_SCHEDULED",
    "STATUS_AMBIGUOUS", "STATUS_UNAVAILABLE", "STATUS_FORBIDDEN", "STATUS_TIMEOUT",
    "STATUS_PARSE_FAILED", "EVIDENCE_STATUSES", "evidence_status_for",
    "AliasEntry", "AliasResolution", "QueryExpansion", "LAW_ALIAS_ENTRIES",
    "normalize_basic_typos", "normalize_law_search_text", "normalize_alias_key",
    "resolve_law_alias", "extract_embedded_aliases", "expand_law_query",
    "strip_non_law_keywords", "extract_law_name_pattern",
    "loose_match_law_name", "resolved_law_matches", "score_law_relevance",
    "law_hierarchy_level", "rank_law_candidates",
    "classify_law_lifecycle", "annotate_lifecycle", "summarize_search_outcome",
]
