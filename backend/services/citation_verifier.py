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

def build_law_evidence_citation_verification(
    law_sources: List[Dict[str, Any]],
    *,
    query: str = "",
    law_error_type: str = "",
    law_api_attempted: bool = False,
) -> Dict[str, Any]:
    """Build user-facing citation verification from normalized law evidence.

    This does not claim article-level legal verification. It wires normalized
    Open Law API evidence into the citation metadata so the UI can distinguish
    verified law evidence, evidence-present-but-not-article-verified, and
    unavailable API states without showing NOT_WIRED to users.
    """
    citations: List[Dict[str, Any]] = []
    for source in law_sources or []:
        if not isinstance(source, dict):
            continue
        law_name = source.get("law_name") or source.get("term") or ""
        if not law_name:
            continue
        article = source.get("article_or_clause") or source.get("article") or source.get("reference") or ""
        citations.append({
            "source_type": source.get("source_type") or "law",
            "law_name": law_name,
            "article_or_clause": article,
            "query": source.get("query") or query or "",
            "retrieval_status": source.get("retrieval_status") or "ok",
            "source_url": source.get("source_url") or "",
            "verification_status": "verified_law_evidence" if source.get("retrieval_status") == "ok" else "law_evidence_present_unverified",
        })
    if citations:
        status = "verified_law_evidence" if any(c["verification_status"] == "verified_law_evidence" for c in citations) else "law_evidence_present_unverified"
        return {"status": status, "citations": citations, "warnings": []}
    if law_error_type == "law_api_not_configured":
        return {"status": "law_api_unavailable", "citations": [], "warnings": ["SOURCE_UNAVAILABLE", law_error_type.upper()]}
    if law_api_attempted or law_error_type:
        warnings = ["SOURCE_UNAVAILABLE"]
        if law_error_type:
            warnings.append(law_error_type.upper())
        return {"status": "law_evidence_unavailable", "citations": [], "warnings": list(dict.fromkeys(warnings))}
    return {"status": "citation_verification_not_applicable", "citations": [], "warnings": []}
