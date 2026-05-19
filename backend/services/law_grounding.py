from __future__ import annotations

import re
from typing import Any, Dict

from .citation_verifier import verify_citations
from .grounding_config import load_grounding_config
from .korean_law_client import KoreanLawClient


_LEGAL_INTENT_PATTERNS = (
    (re.compile(r"근거\s*법령"), "ko_legal_basis"),
    (re.compile(r"법적\s*근거"), "ko_legal_basis"),
    (re.compile(r"출입국관리법"), "ko_immigration_act"),
    (re.compile(r"시행령"), "ko_enforcement_decree"),
    (re.compile(r"시행규칙"), "ko_enforcement_rule"),
    (re.compile(r"제\s*\d+\s*조"), "ko_article_number"),
    (re.compile(r"according to korean law", re.IGNORECASE), "en_korean_law"),
    (re.compile(r"legal basis", re.IGNORECASE), "en_legal_basis"),
    (re.compile(r"\barticle\b", re.IGNORECASE), "en_article"),
    (re.compile(r"immigration act", re.IGNORECASE), "en_immigration_act"),
)


def should_attempt_law_grounding(question: str) -> Dict[str, Any]:
    text = (question or "").strip()
    reasons = [tag for pattern, tag in _LEGAL_INTENT_PATTERNS if pattern.search(text)]
    return {"should_attempt": bool(reasons), "reasons": reasons}


def build_law_grounding_context(question: str) -> Dict[str, Any]:
    intent = should_attempt_law_grounding(question)
    if not intent["should_attempt"]:
        return {
            "attempted": False,
            "intent_reasons": [],
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "extracted_only", "citations": [], "warnings": []},
            "grounding_sources": [],
            "grounding_warnings": [],
        }
    try:
        config = load_grounding_config()
        law_client = KoreanLawClient(config)
        law_result = law_client.search_law(question)
        citation_verification = verify_citations(question, law_client=law_client)
    except Exception:
        return {
            "attempted": True,
            "intent_reasons": intent["reasons"],
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "error", "citations": [], "warnings": ["SOURCE_UNAVAILABLE"]},
            "grounding_sources": [],
            "grounding_warnings": ["SOURCE_UNAVAILABLE"],
        }

    if law_result.get("status") == "disabled":
        return {
            "attempted": False,
            "intent_reasons": intent["reasons"],
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": citation_verification,
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    warnings = [*law_result.get("warnings", []), *citation_verification.get("warnings", []), *config.warnings]
    return {
        "attempted": True,
        "intent_reasons": intent["reasons"],
        "law_grounding_used": law_result.get("status") == "ok",
        "law_grounding": law_result.get("results", []),
        "citation_verification": citation_verification,
        "grounding_sources": [{"source_type": "law", "status": law_result.get("status")}],
        "grounding_warnings": list(dict.fromkeys(warnings)),
    }
