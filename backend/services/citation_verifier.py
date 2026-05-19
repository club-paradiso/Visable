from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

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


def verify_citations(text: str, law_client: Optional[Any] = None) -> Dict[str, Any]:
    extracted = extract_korean_legal_citations(text)
    items = extracted.get("citations", [])
    normalized = [
        {
            "raw": item.get("matched_text", ""),
            "law_name": item.get("law_name", ""),
            "article": item.get("article", ""),
            "verification_status": "not_verified",
            "source_type": "law",
            "warnings": [],
        }
        for item in items
    ]
    if law_client is None:
        return {
            "status": "extracted_only",
            "citations": normalized,
            "warnings": ["CITATION_VERIFICATION_NOT_WIRED"],
        }

    if getattr(getattr(law_client, "config", None), "mode", "disabled") == "disabled":
        for item in normalized:
            item["warnings"].append("LAW_GROUNDING_DISABLED")
        return {"status": "disabled", "citations": normalized, "warnings": ["LAW_GROUNDING_DISABLED"]}

    overall_warnings: List[str] = []
    saw_error = False
    saw_unavailable = False
    for item in normalized:
        try:
            result = law_client.get_article(item["law_name"], item["article"])
        except Exception:
            item["verification_status"] = "error"
            item["warnings"].append("SOURCE_UNAVAILABLE")
            overall_warnings.append("SOURCE_UNAVAILABLE")
            saw_error = True
            continue
        status = result.get("status")
        warnings = result.get("warnings", [])
        item["warnings"].extend(warnings)
        if status == "ok" and result.get("results"):
            item["verification_status"] = "verified"
        elif status == "ok":
            item["verification_status"] = "not_found"
        elif status == "unavailable":
            item["verification_status"] = "unavailable"
            saw_unavailable = True
        elif status == "error":
            item["verification_status"] = "error"
            saw_error = True
        else:
            item["verification_status"] = "not_verified"
        overall_warnings.extend(warnings)

    dedup_warnings = list(dict.fromkeys(overall_warnings))
    if saw_error:
        status = "error"
    elif saw_unavailable:
        status = "unavailable"
    else:
        status = "ok"
    return {"status": status, "citations": normalized, "warnings": dedup_warnings}
