from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List

_CITATION_PATTERN = re.compile(
    r"(?P<law_name>[가-힣]+법(?:\s시행령)?)\s*제\s*(?P<article>\d+)\s*조"
)


@dataclass
class CitationExtractionResult:
    status: str
    citations: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_korean_legal_citations(text: str) -> Dict[str, Any]:
    citations: List[Dict[str, str]] = []
    for match in _CITATION_PATTERN.finditer(text or ""):
        citations.append(
            {
                "law_name": match.group("law_name"),
                "article": f"제{match.group('article')}조",
                "matched_text": match.group(0),
            }
        )
    return CitationExtractionResult(
        status="extracted_only",
        citations=citations,
        warnings=["CITATION_VERIFICATION_NOT_WIRED"],
    ).to_dict()
