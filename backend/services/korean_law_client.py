from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

from .grounding_config import GroundingConfig


@dataclass
class LawClientResult:
    status: str
    query: str
    law_grounding: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KoreanLawClient:
    """Scaffold-only client for future Korean law grounding.

    Not wired to /api/ask in phase 1.
    """

    def __init__(self, config: GroundingConfig):
        self.config = config

    def _guard(self, query: str) -> LawClientResult | None:
        if self.config.mode == "disabled":
            return LawClientResult(
                status="disabled",
                query=query,
                law_grounding=[],
                warnings=["LAW_GROUNDING_DISABLED"],
            )
        if not self.config.law_api_key:
            return LawClientResult(
                status="unavailable",
                query=query,
                law_grounding=[],
                warnings=["LAW_API_KEY_MISSING"],
            )
        return None

    def search_law(self, query: str) -> Dict[str, Any]:
        guarded = self._guard(query)
        if guarded is not None:
            return guarded.to_dict()
        return LawClientResult(
            status="not_implemented",
            query=query,
            law_grounding=[],
            warnings=["LAW_SEARCH_NOT_IMPLEMENTED"],
        ).to_dict()

    def get_article(self, law_name: str, article: str) -> Dict[str, Any]:
        return self.search_law(f"{law_name} {article}".strip())
