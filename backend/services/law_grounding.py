from __future__ import annotations

from typing import Any, Dict

from .citation_verifier import verify_citations
from .grounding_config import load_grounding_config
from .korean_law_client import KoreanLawClient


def build_law_grounding_context(question: str) -> Dict[str, Any]:
    try:
        config = load_grounding_config()
        law_client = KoreanLawClient(config)
        law_result = law_client.search_law(question)
        citation_verification = verify_citations(question, law_client=law_client)
    except Exception:
        return {
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "error", "citations": [], "warnings": ["SOURCE_UNAVAILABLE"]},
            "grounding_sources": [],
            "grounding_warnings": ["SOURCE_UNAVAILABLE"],
        }

    if law_result.get("status") == "disabled":
        return {
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": citation_verification,
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    warnings = [*law_result.get("warnings", []), *citation_verification.get("warnings", []), *config.warnings]
    return {
        "law_grounding_used": law_result.get("status") == "ok",
        "law_grounding": law_result.get("results", []),
        "citation_verification": citation_verification,
        "grounding_sources": [{"source_type": "law", "status": law_result.get("status")}],
        "grounding_warnings": list(dict.fromkeys(warnings)),
    }
