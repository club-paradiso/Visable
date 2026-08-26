"""Backend service scaffolds for law/public-data grounding."""

from .grounding_config import GroundingConfig, load_grounding_config
from .law_grounding import build_law_grounding_context
from . import law_tools as _law_tools
from .law_cloud_fallback import install_cloud_resilient_search

# Install before exporting the package-level function so every normal service
# caller, including the lazy law_grounding module path, sees the same fallback.
install_cloud_resilient_search(_law_tools)

build_law_evidence_pack = _law_tools.build_law_evidence_pack
classify_law_question_type = _law_tools.classify_law_question_type
get_law_detail = _law_tools.get_law_detail
plan_law_queries = _law_tools.plan_law_queries
search_admin_rules = _law_tools.search_admin_rules
search_law_terms = _law_tools.search_law_terms
search_laws = _law_tools.search_laws

from .precedent_sources import (  # noqa: E402
    PRECEDENT_LIST_TARGET,
    normalize_source_family_response,
    search_precedents,
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
    "PRECEDENT_LIST_TARGET",
    "search_precedents",
    "normalize_source_family_response",
]
