from __future__ import annotations

from typing import Any, Dict

from .citation_verifier import extract_korean_legal_citations
from .grounding_config import load_grounding_config
from .korean_law_client import KoreanLawClient


def build_law_grounding_context(question: str) -> Dict[str, Any]:
    config = load_grounding_config()
    law_client = KoreanLawClient(config)
    law_result = law_client.search_law(question)

    if law_result.get("status") == "disabled":
        return {
            "law_grounding_used": False,
            "law_grounding": [],
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    citation_result = extract_korean_legal_citations(question)
    warnings = [*law_result.get("warnings", []), *citation_result.get("warnings", []), *config.warnings]
    return {
        "law_grounding_used": law_result.get("status") == "ok",
        "law_grounding": law_result.get("results", []),
        "grounding_sources": [{"source_type": "law", "status": law_result.get("status")}],
        "citation_extraction": citation_result,
        "grounding_warnings": warnings,
    }
