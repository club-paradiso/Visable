"""Unverified legal-citation guardrail.

Large models will happily emit confident-looking Korean statute citations —
"출입국관리법 제24조 제1항", "시행규칙 제18조의2(별표 1)" — entirely from memory.
When real-time law grounding was NOT verified and the cited article does not
appear in the local manual / official evidence Paradiso actually retrieved, the
answer must not present those numbers as if they were confirmed law.

This module is pure logic (no I/O, no secrets) so it is fully unit-testable and
can run on both the buffered ``/api/ask`` path and inside regression tests. The
streamed path additionally relies on the in-prompt constraint built by
``build_citation_safety_directive`` plus the user-visible status panel.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Statute / decree / rule article references the model might fabricate:
#   제24조, 제24조 제1항, 제18조의2, 제46조제1항제8호 ...
_ARTICLE_RE = re.compile(
    r"제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?"
)
# 별표 references (often cited alongside 시행규칙): 별표 1, 별표 1의2 ...
_ATTACHMENT_RE = re.compile(r"별표\s*\d+(?:\s*의\s*\d+)?")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def detect_legal_article_citations(text: str) -> List[str]:
    """Return the distinct statute/article/별표 citation tokens found in ``text``.

    Tokens are whitespace-normalized (제24조 제1항 -> 제24조제1항) so they compare
    cleanly against evidence text regardless of spacing.
    """
    found: List[str] = []
    for pattern in (_ARTICLE_RE, _ATTACHMENT_RE):
        for match in pattern.finditer(text or ""):
            token = _normalize(match.group(0))
            if token and token not in found:
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
            "so it relies on Paradiso's stored manual/official materials. Specific "
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
) -> Dict[str, Any]:
    """Post-hoc guardrail for a completed answer.

    Returns a dict with the (possibly augmented) ``answer`` plus non-secret
    metadata describing what was detected and what action was taken. When the
    answer cites specific articles, real-time grounding is NOT verified, and the
    citations are not backed by local evidence, a clear notice is prepended so a
    hallucinated citation is never silently presented as official.
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

    if law_grounding_verified:
        meta["law_citation_guard_action"] = "allowed_verified"
        return {"answer": answer, **meta}

    unsupported = [c for c in citations if not citation_supported_by_evidence(c, evidence)]
    if not unsupported:
        # Every cited article is backed by local manual/official evidence.
        meta["law_citation_guard_action"] = "allowed_local_evidence"
        return {"answer": answer, **meta}

    notice = build_unverified_citation_notice(lang)
    meta["unsupported_law_citations"] = unsupported
    meta["unverified_law_citation_detected"] = True
    meta["law_citation_guard_action"] = "notice_prepended"
    guarded = answer if (notice in (answer or "")) else f"⚠️ {notice}\n\n{answer}"
    return {"answer": guarded, **meta}
