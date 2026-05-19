from __future__ import annotations

import re
from typing import Any, Dict, List

from .citation_verifier import verify_citations
from .grounding_config import load_grounding_config
from .korean_law_client import KoreanLawClient


_INTENT_PATTERNS = [
    ("근거 법령", re.compile(r"근거\s*법령", re.IGNORECASE)),
    ("법적 근거", re.compile(r"법적\s*근거", re.IGNORECASE)),
    ("출입국관리법", re.compile(r"출입국관리법", re.IGNORECASE)),
    ("시행령", re.compile(r"시행령", re.IGNORECASE)),
    ("시행규칙", re.compile(r"시행규칙", re.IGNORECASE)),
    ("제n조", re.compile(r"제\s*\d+\s*조", re.IGNORECASE)),
    ("according to korean law", re.compile(r"according\s+to\s+korean\s+law", re.IGNORECASE)),
    ("legal basis", re.compile(r"legal\s+basis", re.IGNORECASE)),
    ("article", re.compile(r"\barticle\b", re.IGNORECASE)),
    ("immigration act", re.compile(r"immigration\s+act", re.IGNORECASE)),
]


def should_attempt_law_grounding(question: str) -> Dict[str, Any]:
    text = (question or "").strip()
    if not text:
        return {"should_attempt": False, "reasons": []}

    reasons: List[str] = [label for label, pattern in _INTENT_PATTERNS if pattern.search(text)]
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

    config = load_grounding_config()
    if config.mode == "disabled":
        return {
            "attempted": False,
            "intent_reasons": intent["reasons"],
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "extracted_only", "citations": [], "warnings": []},
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    try:
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
