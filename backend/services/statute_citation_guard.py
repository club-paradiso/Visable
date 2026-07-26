"""Statute-citation verification against a retrieved evidence pack.

``citation_verifier`` already covers *adjudicative* citations (판례 / 재결 / 헌재결정).
This module covers the other half — 법령 조문 citations — at the granularity the
answer surface actually prints them:

    「출입국관리법」 제19조의4 제2항 제1호 (외국인등록사항 등의 변경신고)
     └ law name   └ article └ branch └ clause └ subclause └ article title

The contract is containment, not plausibility: a citation is ``verified`` only when
the *retrieved evidence pack* actually contains that law and that article. A model
that emits a real-looking article number for a law nobody fetched is producing an
unverifiable citation, and that is reported as such rather than rendered as fact.

Failure taxonomy (never collapsed into one boolean):

* ``verified``               — law + article present in the evidence pack
* ``law_not_in_evidence``    — the cited law was never retrieved
* ``article_not_in_evidence``— the law was retrieved, that article was not
* ``title_mismatch``         — article exists, but the quoted 조문 제목 disagrees
* ``repealed_law_cited``     — cited against a statute the pack marks 폐지
* ``unverifiable``           — no evidence pack at all (lookup failed / disabled)

Pure functions, stdlib only, never raises.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence

STATUTE_CITATION_GUARD_VERSION = "2026-07-statute-citation-guard-v1"

STATUS_VERIFIED = "verified"
STATUS_LAW_NOT_IN_EVIDENCE = "law_not_in_evidence"
STATUS_ARTICLE_NOT_IN_EVIDENCE = "article_not_in_evidence"
STATUS_TITLE_MISMATCH = "title_mismatch"
STATUS_REPEALED_LAW_CITED = "repealed_law_cited"
STATUS_UNVERIFIABLE = "unverifiable"

FAILING_STATUSES = frozenset({
    STATUS_LAW_NOT_IN_EVIDENCE,
    STATUS_ARTICLE_NOT_IN_EVIDENCE,
    STATUS_TITLE_MISMATCH,
    STATUS_REPEALED_LAW_CITED,
})

# 원문자 항 표기(①②③) is as common as 제1항 in Korean statutes and in model output.
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"

_INTERPUNCT_RE = re.compile("[·ㆍ‧•・]")

# A statute name is a Hangul run ending in 법/령/규칙/규정, optionally bracketed by
# 「」/『』, optionally followed by 시행령 / 시행규칙. Multi-word official titles
# ("재외동포의 출입국과 법적 지위에 관한 법률") are matched via the bracket form or by
# allowing internal spaces before the terminal 법률/법.
_LAW_NAME_RE = (
    r"(?:「(?P<bracketed>[^」]{2,60})」|"
    r"(?P<plain>[가-힣]{2,20}(?:\s?[가-힣]{1,20}){0,6}?(?:법률|법|령|규칙|규정)"
    r"(?:\s*시행(?:령|규칙))?))"
)

_ARTICLE_RE = (
    r"제\s*(?P<article>\d+)\s*조"
    r"(?:\s*의\s*(?P<branch>\d+))?"
)

_CLAUSE_RE = (
    r"(?:\s*(?:제\s*(?P<clause>\d+)\s*항|(?P<circled>[" + _CIRCLED + r"])))?"
    r"(?:\s*제\s*(?P<subclause>\d+)\s*호)?"
)

_TITLE_RE = r"(?:\s*\(\s*(?P<title>[^)\n]{1,40})\s*\))?"

_STATUTE_CITATION_RE = re.compile(
    _LAW_NAME_RE + r"\s*" + _ARTICLE_RE + _CLAUSE_RE + _TITLE_RE
)

# A bare "제20조" with no law name in the same sentence is still a citation the
# reader will attribute to whatever law is on screen, so it is captured too — but
# only when a law name appeared earlier in the text (see _carry_forward_law).
_BARE_ARTICLE_RE = re.compile(_ARTICLE_RE + _CLAUSE_RE + _TITLE_RE)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = _INTERPUNCT_RE.sub("", text)
    return re.sub(r"\s+", "", text)


def _article_label(article: Optional[str], branch: Optional[str]) -> str:
    if not article:
        return ""
    return f"제{int(article)}조" + (f"의{int(branch)}" if branch else "")


def _article_key(article: Optional[str], branch: Optional[str]) -> str:
    if not article:
        return ""
    return f"{int(article)}:{int(branch) if branch else 0}"


def _clause_label(clause: Optional[str], circled: Optional[str], subclause: Optional[str]) -> str:
    parts: List[str] = []
    if clause:
        parts.append(f"제{int(clause)}항")
    elif circled:
        parts.append(f"제{_CIRCLED.index(circled) + 1}항")
    if subclause:
        parts.append(f"제{int(subclause)}호")
    return " ".join(parts)


def extract_statute_citations(text: str) -> List[Dict[str, Any]]:
    """Extract statute citations with article / clause / subclause / title parts."""
    source = unicodedata.normalize("NFC", str(text or ""))
    citations: List[Dict[str, Any]] = []
    consumed: List[tuple] = []

    for match in _STATUTE_CITATION_RE.finditer(source):
        law_name = (match.group("bracketed") or match.group("plain") or "").strip()
        if not law_name:
            continue
        citations.append({
            "law_name": law_name,
            "article": _article_label(match.group("article"), match.group("branch")),
            "article_key": _article_key(match.group("article"), match.group("branch")),
            "clause": _clause_label(match.group("clause"), match.group("circled"),
                                    match.group("subclause")),
            "article_title": (match.group("title") or "").strip(),
            "matched_text": match.group(0).strip(),
        })
        consumed.append((match.start(), match.end()))

    # Bare "제N조" references that follow a named law inherit that law, so an
    # unverifiable article cannot hide behind an elided statute name.
    for match in _BARE_ARTICLE_RE.finditer(source):
        if any(start <= match.start() < end for start, end in consumed):
            continue
        carried = _carry_forward_law(citations, match.start(), source)
        if not carried:
            continue
        citations.append({
            "law_name": carried,
            "article": _article_label(match.group("article"), match.group("branch")),
            "article_key": _article_key(match.group("article"), match.group("branch")),
            "clause": _clause_label(match.group("clause"), match.group("circled"),
                                    match.group("subclause")),
            "article_title": (match.group("title") or "").strip(),
            "matched_text": match.group(0).strip(),
            "law_name_inferred": True,
        })

    citations.sort(key=lambda c: source.find(c["matched_text"]))
    return citations


def _carry_forward_law(citations: Sequence[Dict[str, Any]], position: int, source: str) -> str:
    """Most recent explicitly-named law appearing before ``position``."""
    best = ""
    for citation in citations:
        idx = source.find(citation["matched_text"])
        if 0 <= idx < position:
            best = citation["law_name"]
    return best


def index_law_evidence(evidence_items: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a law-name -> {articles, titles, lifecycle} index from an evidence pack.

    Accepts the normalized rows produced by ``law_tools`` (``law_name``,
    ``articles``, ``lifecycle_status``) and tolerates partial shapes.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for item in evidence_items or []:
        if not isinstance(item, dict):
            continue
        law_name = item.get("law_name") or item.get("title") or ""
        if not law_name:
            continue
        key = _normalize(law_name)
        entry = index.setdefault(key, {
            "law_name": law_name,
            "articles": {},
            "lifecycle_status": "",
            "has_article_detail": False,
        })
        lifecycle = item.get("lifecycle_status") or ""
        if lifecycle:
            entry["lifecycle_status"] = lifecycle

        articles = item.get("articles")
        if isinstance(articles, list):
            for article in articles:
                if not isinstance(article, dict):
                    continue
                number = article.get("article_number") or article.get("조문번호") or article.get("article")
                branch = article.get("article_branch") or article.get("조문가지번호") or ""
                article_key = _article_key(_digits(number), _digits(branch))
                if not article_key:
                    continue
                entry["has_article_detail"] = True
                entry["articles"][article_key] = {
                    "title": str(article.get("article_title") or article.get("조문제목") or "").strip(),
                    "text": str(article.get("article_text") or article.get("조문내용") or "").strip(),
                }

        single = item.get("article_or_clause") or item.get("article") or ""
        parsed = re.search(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?", str(single))
        if parsed:
            article_key = _article_key(parsed.group(1), parsed.group(2))
            entry["has_article_detail"] = True
            entry["articles"].setdefault(article_key, {
                "title": str(item.get("article_title") or "").strip(),
                "text": str(item.get("summary") or "").strip(),
            })
    return index


def _digits(value: Any) -> Optional[str]:
    raw = re.sub(r"[^0-9]", "", str(value or ""))
    return raw or None


def _titles_agree(cited: str, official: str) -> bool:
    a, b = _normalize(cited), _normalize(official)
    if not a or not b:
        return True  # nothing to contradict
    return a == b or a in b or b in a


def verify_statute_citations(
    text: str,
    evidence_items: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    evidence_available: Optional[bool] = None,
) -> Dict[str, Any]:
    """Verify every statute citation in ``text`` against the evidence pack.

    ``evidence_available=False`` (a failed or disabled lookup) marks every citation
    ``unverifiable`` rather than ``law_not_in_evidence`` — "we could not check" and
    "we checked and it is not there" are different claims and must not be merged.
    """
    citations = extract_statute_citations(text)
    index = index_law_evidence(evidence_items or [])
    has_evidence = bool(index) if evidence_available is None else bool(evidence_available)

    verified: List[Dict[str, Any]] = []
    for citation in citations:
        result = dict(citation)
        if not has_evidence:
            result["verification_status"] = STATUS_UNVERIFIABLE
            verified.append(result)
            continue

        entry = _lookup_law(index, citation["law_name"])
        if entry is None:
            result["verification_status"] = STATUS_LAW_NOT_IN_EVIDENCE
            verified.append(result)
            continue

        result["matched_law_name"] = entry["law_name"]
        if entry.get("lifecycle_status") == "repealed":
            result["verification_status"] = STATUS_REPEALED_LAW_CITED
            verified.append(result)
            continue

        article_key = citation.get("article_key") or ""
        if not article_key:
            # A law-level reference with no article: verified at law granularity.
            result["verification_status"] = STATUS_VERIFIED
            result["granularity"] = "law"
            verified.append(result)
            continue

        if not entry.get("has_article_detail"):
            # The law was retrieved but article text was never fetched, so the
            # article number is unchecked — not a pass.
            result["verification_status"] = STATUS_ARTICLE_NOT_IN_EVIDENCE
            result["reason"] = "no_article_detail_retrieved"
            verified.append(result)
            continue

        article = entry["articles"].get(article_key)
        if article is None:
            result["verification_status"] = STATUS_ARTICLE_NOT_IN_EVIDENCE
            verified.append(result)
            continue

        if citation.get("article_title") and not _titles_agree(
                citation["article_title"], article.get("title", "")):
            result["verification_status"] = STATUS_TITLE_MISMATCH
            result["official_article_title"] = article.get("title", "")
            verified.append(result)
            continue

        result["verification_status"] = STATUS_VERIFIED
        result["granularity"] = "article"
        result["official_article_title"] = article.get("title", "")
        verified.append(result)

    failures = [c for c in verified if c["verification_status"] in FAILING_STATUSES]
    unverifiable = [c for c in verified if c["verification_status"] == STATUS_UNVERIFIABLE]

    if not verified:
        status = "no_statute_citations"
    elif failures:
        status = "failed"
    elif unverifiable:
        status = "unverifiable"
    else:
        status = "verified"

    return {
        "status": status,
        "citations": verified,
        "failure_count": len(failures),
        "unverifiable_count": len(unverifiable),
        "verified_count": sum(1 for c in verified if c["verification_status"] == STATUS_VERIFIED),
        # Log-safe: identifiers only, no answer text and no credentials.
        "failure_summary": [
            {"law_name": c.get("law_name", ""), "article": c.get("article", ""),
             "status": c["verification_status"]}
            for c in failures
        ],
    }


def _lookup_law(index: Dict[str, Dict[str, Any]], law_name: str) -> Optional[Dict[str, Any]]:
    key = _normalize(law_name)
    if key in index:
        return index[key]
    # Prefix tolerance: "출입국관리법" cited against retrieved "출입국관리법 시행령"
    # must NOT match (different instrument), but a retrieved parent Act does cover
    # a citation written with a spacing variant of its own name.
    for candidate_key, entry in index.items():
        if candidate_key == key:
            return entry
    return None


def strip_failed_statute_citations(text: str, verification: Dict[str, Any]) -> str:
    """Deterministically neutralize citations that failed verification.

    Rather than deleting the sentence (which can invert its meaning), the citation
    token is replaced with an explicit unverified marker, so the reader sees that a
    reference was claimed and could not be confirmed.
    """
    out = str(text or "")
    for citation in verification.get("citations", []):
        if citation.get("verification_status") not in FAILING_STATUSES:
            continue
        token = citation.get("matched_text") or ""
        if token and token in out:
            out = out.replace(token, f"[미확인 인용: {token}]")
    return out


__all__ = [
    "STATUTE_CITATION_GUARD_VERSION",
    "STATUS_VERIFIED", "STATUS_LAW_NOT_IN_EVIDENCE", "STATUS_ARTICLE_NOT_IN_EVIDENCE",
    "STATUS_TITLE_MISMATCH", "STATUS_REPEALED_LAW_CITED", "STATUS_UNVERIFIABLE",
    "FAILING_STATUSES",
    "extract_statute_citations", "index_law_evidence", "verify_statute_citations",
    "strip_failed_statute_citations",
]
