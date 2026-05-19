from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

from .grounding_config import GroundingConfig


@dataclass
class PublicDataResult:
    status: str
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PublicDataClient:
    """Scaffold-only client for future public-data integration.

    Not wired to /api/ask in phase 1.
    """

    def __init__(self, config: GroundingConfig):
        self.config = config

    def _guard(self, query: str) -> PublicDataResult | None:
        if self.config.mode == "disabled":
            return PublicDataResult(
                status="disabled",
                query=query,
                sources=[],
                warnings=["PUBLIC_DATA_GROUNDING_DISABLED"],
            )
        if not self.config.public_data_api_key:
            return PublicDataResult(
                status="unavailable",
                query=query,
                sources=[],
                warnings=["PUBLIC_DATA_API_KEY_MISSING"],
            )
        return None

    def fetch_visa_public_data(self, query: str) -> Dict[str, Any]:
        guarded = self._guard(query)
        if guarded is not None:
            return guarded.to_dict()
        return PublicDataResult(
            status="not_implemented",
            query=query,
            sources=[],
            warnings=["PUBLIC_DATA_FETCH_NOT_IMPLEMENTED"],
        ).to_dict()

    def fetch_job_public_data(self, query: str) -> Dict[str, Any]:
        return self.fetch_visa_public_data(query)
