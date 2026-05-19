"""Backend service scaffolds for law/public-data grounding."""

from .grounding_config import GroundingConfig, load_grounding_config
from .law_grounding import build_law_grounding_context

__all__ = [
    "GroundingConfig",
    "load_grounding_config",
    "build_law_grounding_context",
]
