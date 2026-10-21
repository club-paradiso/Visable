"""Unverified legal-citation guardrail.

Large models will happily emit confident-looking Korean statute citations —
"출입국관리법 제24조 제1항", "시행규칙 제18조의2(별표 1)" — entirely from memory.
When the cited article does not appear in the local manual / official evidence
Visable actually retrieved, the answer must not present those numbers as if they
were confirmed law. A "verified" grounding state is not enough on its own: it can
come from a law-title search hit, so it authorizes an article number only when
that article of that law was fetched and matched (``article_evidence``).

This module is pure logic (no I/O, no secrets) so it is fully unit-testable and
can run on both the buffered ``/api/ask`` path and inside regression tests. The
streamed path additionally relies on the in-prompt constraint built by
``build_citation_safety_directive`` plus the user-visible status panel.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

# Statute / decree / rule article references the model might fabricate:
#   제24조, 제24조 제1항, 제18조의2, 제46조제1항제8호 ...
_ARTICLE_RE = re.compile(
    r"제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?"
)
# 별표 references (often cited alongside 시행규칙): 별표 1, 별표 1의2 ...
_ATTACHMENT_RE = re.compile(r"별표\s*\d+(?:\s*의\s*\d+)?")
# The part of a token that article-level evidence is keyed by: 제24조제1항 and
# 제24조 both belong to 제24조 (its 항/호 are inside the fetched article text).
_ARTICLE_KEY_RE = re.compile(r"제\d+조(?:의\d+)?|별표\d+(?:의\d+)?")

# One law reference in prose. At each position the alternatives are tried in
# order, so "동법" is a back-reference rather than a law called 동법, and the 시행령
# in "출입국관리법 시행령" belongs to the name instead of standing alone.
_LAW_REFERENCE_RE = re.compile(
    r"""
      (?P<same>같은\s*법|동법)(?P<same_suffix>\s*시행령|\s*시행규칙)?   # 같은 법, 동법 시행령
    | (?P<name>[가-힣]+(?:법률|법))(?P<suffix>\s*시행령|\s*시행규칙)?   # 출입국관리법 (시행규칙)
    | (?P<unnamed>시행령|시행규칙|법률)                                 # 시행령, "…에 관한 법률"
    """,
    re.VERBOSE,
)
# Common words that end in 법 but are not law names.
_NOT_LAW_NAMES = frozenset({
    "방법", "불법", "위법", "적법", "합법", "편법", "용법", "문법", "해법", "수법", "기법", "어법",
})
# A law named in an earlier sentence does not govern a bare article number.
_SENTENCE_END_RE = re.compile(r"[.?!。\n]")
_DECREE_SUFFIXES = ("시행령", "시행규칙")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _citation_occurrences(text: str) -> Iterator[Tuple[int, str]]:
    """``(position, normalized token)`` for every article / 별표 citation."""
    for pattern in (_ARTICLE_RE, _ATTACHMENT_RE):
        for match in pattern.finditer(text or ""):
            token = _normalize(match.group(0))
            if token:
                yield match.start(), token


def _base_act(law_name: str) -> str:
    """출입국관리법시행규칙 -> 출입국관리법 (names are already space-free)."""
    for suffix in _DECREE_SUFFIXES:
        if law_name.endswith(suffix):
            return law_name[: -len(suffix)]
    return law_name


def _law_references(text: str) -> List[Tuple[int, str]]:
    """``(end position, space-free law name)`` for each law the text refers to.

    A reference whose law the text does not name (a bare 시행령, the tail of a
    multi-word title such as "…에 관한 법률", a "같은 법" with nothing before it)
    gets an empty name. It still ends the reach of the law named before it, so a
    later article number is never bound to the wrong law.
    """
    references: List[Tuple[int, str]] = []
    last_named = ""
    for match in _LAW_REFERENCE_RE.finditer(text or ""):
        if match.group("unnamed"):
            name = last_named = ""
        elif match.group("same"):
            suffix = _normalize(match.group("same_suffix") or "")
            name = _base_act(last_named) + suffix if last_named else ""
        elif match.group("name") in _NOT_LAW_NAMES:
            continue
        else:
            name = last_named = _normalize(match.group("name") + (match.group("suffix") or ""))
        references.append((match.end(), name))
    return references


def _governing_law(text: str, references: Sequence[Tuple[int, str]], position: int) -> str:
    """The law a citation at ``position`` belongs to: the nearest law reference
    before it in the same sentence, or ``""`` when there is none or it names no
    law."""
    preceding = [(end, name) for end, name in references if end <= position]
    if not preceding:
        return ""
    end, name = preceding[-1]
    if _SENTENCE_END_RE.search(text[end:position]):
        return ""
    return name


def _article_key(token: str) -> str:
    match = _ARTICLE_KEY_RE.match(_normalize(token))
    return match.group(0) if match else ""


def _fetched_article_keys(article_evidence: Optional[Iterable[Mapping[str, Any]]]) -> Set[Tuple[str, str]]:
    keys: Set[Tuple[str, str]] = set()
    for row in article_evidence or []:
        if not isinstance(row, Mapping) or row.get("article_verification_status") != "verified":
            continue
        law_name = _normalize(str(row.get("law_name") or ""))
        article = _article_key(str(row.get("article") or ""))
        if law_name and article:
            keys.add((law_name, article))
    return keys


def _tokens_backed_by_article_evidence(
    answer: str, article_evidence: Optional[Iterable[Mapping[str, Any]]]
) -> Set[str]:
    """Citation tokens whose every occurrence names a law + article that was
    fetched and matched. A bare "제24조" names no law, so it is never backed."""
    fetched = _fetched_article_keys(article_evidence)
    if not fetched:
        return set()
    references = _law_references(answer)
    backed: Set[str] = set()
    unbacked: Set[str] = set()
    for position, token in _citation_occurrences(answer):
        law_name = _governing_law(answer, references, position)
        if law_name and (law_name, _article_key(token)) in fetched:
            backed.add(token)
        else:
            unbacked.add(token)
    return backed - unbacked


def article_evidence_from_law_pack(pack: Optional[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """Article-level evidence rows from a law evidence pack, for
    ``guard_answer_citations(article_evidence=...)``.

    Only rows that law_grounding fetched from lawService and matched by article
    number carry ``article_verification_status == "verified"``; title-list hits
    never do. /api/ask does not pass these to the guard yet, because the call
    site is in paradiso_backend.py (see research-notes/law-stack-fixes.md).
    """
    pack = pack or {}
    verification = pack.get("citation_verification") or {}
    candidates = [*(pack.get("law_sources") or []), *(verification.get("article_evidence") or [])]
    rows: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for row in candidates:
        if not isinstance(row, Mapping) or row.get("article_verification_status") != "verified":
            continue
        law_name = str(row.get("law_name") or "").strip()
        article = str(row.get("article") or "").strip()
        key = (_normalize(law_name), _normalize(article))
        if not all(key) or key in seen:
            continue
        seen.add(key)
        rows.append({"law_name": law_name, "article": article, "article_verification_status": "verified"})
    return rows


def detect_legal_article_citations(text: str) -> List[str]:
    """Return the distinct statute/article/별표 citation tokens found in ``text``.

    Tokens are whitespace-normalized (제24조 제1항 -> 제24조제1항) so they compare
    cleanly against evidence text regardless of spacing.
    """
    found: List[str] = []
    for _position, token in _citation_occurrences(text):
        if token not in found:
            found.append(token)
    return found


def citation_supported_by_evidence(citation: str, evidence_texts: Iterable[str]) -> bool:
    """True when the (normalized) citation token appears in any evidence text."""
    needle = _normalize(citation)
    if not needle:
        return False
    return any(needle in _normalize(str(ev)) for ev in evidence_texts if ev)


def build_unverified_citation_notice(lang: Optional[str] = None) -> str:
    """The user-facing notice shown when specific citations are unverified."""
    if str(lang or "").lower().startswith("en"):
        return (
            "Real-time legal-source lookup could not be verified for this answer, "
            "so it relies on Visable's stored manual/official materials. Specific "
            "article numbers below are not confirmed — verify them with HiKorea, "
            "1345, or the competent immigration office."
        )
    return (
        "실시간 법령 조회 결과를 확인하지 못해, 아래 답변은 보유 매뉴얼/공식자료 기준입니다. "
        "특정 조문 번호는 확정하지 않습니다. 정확한 조문은 하이코리아·1345·관할 출입국·외국인관서에서 확인하세요."
    )


def build_citation_safety_directive(
    *, status_detail: str, lang: Optional[str] = None
) -> str:
    """Prompt directive forbidding invented citations when law is unverified.

    Injected into the final prompt for EVERY law-intent answer (including the
    streamed path, where post-hoc text repair is not possible).
    """
    verified = str(status_detail or "") == "law_grounding_verified"
    if verified:
        return (
            "[Legal citation safety]\n"
            "- Real-time law grounding for THIS answer is VERIFIED.\n"
            "- You may cite a specific 조문/별표 ONLY if it appears verbatim in the"
            " official evidence provided above; never add article numbers from memory."
        )
    return (
        "[Legal citation safety — strict]\n"
        f"- Real-time law grounding status for THIS answer: {status_detail}.\n"
        "- Do NOT generate statute, decree, rule, article, paragraph, 호, or 별표"
        " numbers from memory (e.g. 출입국관리법 제24조, 시행규칙 제18조의2, 별표 1).\n"
        "- Because the live law citation is NOT verified, explicitly state that the"
        " specific 조문 번호(법적 근거)는 확인되지 않았다 and avoid asserting exact"
        " article numbers.\n"
        "- Explain duties in general terms (예: 근무처 변경허가 또는 변경신고가 필요할"
        " 수 있음) and direct the user to confirm exact provisions via HiKorea / 1345"
        " / 관할 출입국·외국인관서."
    )


def guard_answer_citations(
    answer: str,
    *,
    law_grounding_verified: bool,
    evidence_texts: Optional[Sequence[str]] = None,
    lang: Optional[str] = None,
    article_evidence: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Post-hoc guardrail for a completed answer.

    Returns a dict with the (possibly augmented) ``answer`` plus non-secret
    metadata describing what was detected and what action was taken. When the
    answer cites specific articles that are backed neither by fetched
    article-level evidence nor by local evidence, a clear notice is prepended so
    a hallucinated citation is never silently presented as official.

    ``allowed_verified`` needs ``law_grounding_verified`` AND every cited
    article in ``article_evidence`` (rows with ``article_verification_status ==
    "verified"``) under the law the answer names for it. The flag alone used to
    allow every article number, but it is also set by a law-title search hit
    (audit R2). Callers that pass no ``article_evidence`` get the local-evidence
    check whatever the flag says.
    """
    evidence = list(evidence_texts or [])
    citations = detect_legal_article_citations(answer or "")
    meta: Dict[str, Any] = {
        "law_citations_detected": citations,
        "unsupported_law_citations": [],
        "unverified_law_citation_detected": False,
        "law_citation_guard_action": "none",
    }
    if not citations:
        return {"answer": answer, **meta}

    fetched_tokens = (
        _tokens_backed_by_article_evidence(answer or "", article_evidence)
        if law_grounding_verified else set()
    )
    if fetched_tokens.issuperset(citations):
        meta["law_citation_guard_action"] = "allowed_verified"
        return {"answer": answer, **meta}

    unsupported = [
        c for c in citations
        if c not in fetched_tokens and not citation_supported_by_evidence(c, evidence)
    ]
    if not unsupported:
        # Every cited article is backed by fetched articles or local evidence.
        meta["law_citation_guard_action"] = "allowed_local_evidence"
        return {"answer": answer, **meta}

    notice = build_unverified_citation_notice(lang)
    meta["unsupported_law_citations"] = unsupported
    meta["unverified_law_citation_detected"] = True
    meta["law_citation_guard_action"] = "notice_prepended"
    guarded = answer if (notice in (answer or "")) else f"⚠️ {notice}\n\n{answer}"
    return {"answer": guarded, **meta}
