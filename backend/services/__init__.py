"""Backend service scaffolds for law/public-data grounding."""

from .grounding_config import GroundingConfig, load_grounding_config
from .law_grounding import build_law_grounding_context
from .law_tools import (
    build_law_evidence_pack,
    classify_law_question_type,
    get_law_detail,
    plan_law_queries,
    search_admin_rules,
    search_law_terms,
    search_laws,
)

__all__ = [
    "GroundingConfig",
    "load_grounding_config",
    "build_law_grounding_context",
    "build_law_evidence_pack",
    "classify_law_question_type",
    "plan_law_queries",
    "search_laws",
    "search_admin_rules",
    "search_law_terms",
    "get_law_detail",
]
