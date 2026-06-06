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


# ---------------------------------------------------------------------------
# Case / decision citation verification (precedent-family scaffold)
#
# Statute citations (XX법 제N조) are handled above. This layer verifies
# *adjudicative* citations — court precedent (판례), administrative-appeal
# decisions (재결), Constitutional Court decisions (헌재결정), and legal
# interpretation cases (법령해석례) — against the normalized precedent-family
# evidence items produced by ``precedent_sources``. The contract is strict:
#
#   * A cited case / decision number that maps to no evidence item FAILS
#     (an invented citation), it is never silently accepted.
#   * An adjudicative authority claim with no evidence of that family FAILS
#     (the answer must instead say the direct evidence was not retrieved).
#   * A binding/direct authority claim backed only by *contextual* evidence is
#     an overclaim and FAILS (list-only results are not binding authority).
#   * A direct quotation attributed to a decision must match a ``quoteSafe``
#     snippet/holding; otherwise it is a quote mismatch and FAILS.
#
# Pure procedure mentions ("행정심판을 청구할 수 있습니다") are NOT authority
# claims and never fail. This function never raises.
# ---------------------------------------------------------------------------

# Court / constitutional case numbers: 4-digit year + known classifier + serial.
# Multi-char classifiers are listed before single-char ones so e.g. 2017구합8901
# is read as 구합, not 구. Constitutional classifiers (헌마/헌바/...) are included.
_CASE_NUMBER_RE = re.compile(
    r"(?<![0-9A-Za-z])(?:19|20)\d{2}"
    r"(?:구합|구단|가합|가단|가소|고합|고단|고정|헌마|헌바|헌가|헌라|헌나|헌사|헌아"
    r"|두|다|도|구|누|노|머|므|드|재|초|나|라)"
    r"\d{1,6}"
)
# Generic decision / agenda numbers (행정심판 재결, 법령해석 안건번호 등): only
# extracted when an adjudicative keyword sits in the same answer (attribution),
# so unrelated hyphenated numbers (page 12-34) are not treated as citations.
_DECISION_NUMBER_RE = re.compile(r"(?<![0-9A-Za-z가-힣])\d{2,4}-\d{1,6}(?![0-9])")

_ADJUDICATIVE_KEYWORDS = (
    "판례", "판결", "대법원", "판시", "헌재", "헌법재판소", "위헌", "헌법소원",
    "행정심판", "재결", "행정심판위원회", "법령해석", "유권해석", "결정례",
)

# Authority-claim patterns per family. These mean the answer is *citing a
# decision/holding as authority*, not merely describing the remedy option.
_AUTHORITY_CLAIM_PATTERNS = {
    "precedent": re.compile(
        r"확립된\s*판례|판례에\s*따르면|판례상|대법원[^.\n]{0,30}(?:판시|판결|선고)"
        r"|판시한\s*바|the court held|binding precedent"
    ),
    "constitutional_decision": re.compile(
        r"헌법재판소[^.\n]{0,30}(?:결정|판단|위헌)|헌재[^.\n]{0,20}(?:결정|판단)"
        r"|위헌결정에\s*따르면|헌법소원[^.\n]{0,20}결정"
    ),
    "administrative_appeal": re.compile(
        r"재결례에\s*따르면|행정심판[^.\n]{0,20}재결[^.\n]{0,20}(?:판단|인용|기각)"
        r"|중앙행정심판위원회[^.\n]{0,20}재결"
    ),
    "legal_interpretation": re.compile(
        r"법령해석례에\s*따르면|법제처[^.\n]{0,20}해석[^.\n]{0,20}(?:따르면|의하면)"
        r"|유권해석에\s*따르면"
    ),
}

# Binding/direct wording that contextual-only evidence cannot support.
_BINDING_WORDING_RE = re.compile(
    r"확립된\s*판례|판례상\s*확립|구속력|기속력|확정\s*판결|반드시\s*취소"
    r"|binding\s*precedent|the\s*court\s*held"
)

# Quoted spans (Korean + ASCII quotation styles).
_QUOTE_RE = re.compile(r"[\"“”]([^\"“”]{6,300})[\"“”]|「([^」]{6,300})」|『([^』]{6,300})』")

_FAILING_STATUSES = frozenset({
    "unverified_fabricated", "overclaimed_contextual",
    "unsupported_authority_claim", "quote_mismatch",
})


def _norm_identifier(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower()


def _index_evidence_items(evidence_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Index normalized precedent-family evidence items for matching."""
    by_identifier: Dict[str, Dict[str, Any]] = {}
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    quote_safe_texts: List[str] = []
    for item in evidence_items or []:
        if not isinstance(item, dict):
            continue
        family = str(item.get("sourceFamily") or item.get("source_family") or "")
        by_family.setdefault(family, []).append(item)
        for key in ("caseNumber", "decisionNumber", "serialNumber",
                    "case_number", "decision_number", "serial_number"):
            ident = _norm_identifier(item.get(key) or "")
            if ident:
                by_identifier.setdefault(ident, item)
        if item.get("quoteSafe"):
            for tkey in ("snippet", "holdingSummary", "holding_summary"):
                text = re.sub(r"\s+", " ", str(item.get(tkey) or "")).strip()
                if text:
                    quote_safe_texts.append(text)
    return {
        "by_identifier": by_identifier,
        "by_family": by_family,
        "quote_safe_texts": quote_safe_texts,
    }


def extract_case_decision_citations(text: str) -> Dict[str, Any]:
    """Extract adjudicative citation signals from answer text (no verification).

    Returns case/decision numbers, attributed authority claims (by family), and
    quoted spans. Decision numbers are only reported when the text also carries
    an adjudicative keyword (attribution guard).
    """
    body = text or ""
    has_adjudicative_kw = any(kw in body for kw in _ADJUDICATIVE_KEYWORDS)
    case_numbers = list(dict.fromkeys(m.group(0) for m in _CASE_NUMBER_RE.finditer(body)))
    decision_numbers: List[str] = []
    if has_adjudicative_kw:
        decision_numbers = [
            n for n in dict.fromkeys(m.group(0) for m in _DECISION_NUMBER_RE.finditer(body))
            if n not in case_numbers
        ]
    authority_claims = [
        family for family, pattern in _AUTHORITY_CLAIM_PATTERNS.items()
        if pattern.search(body)
    ]
    quotes: List[str] = []
    for match in _QUOTE_RE.finditer(body):
        span = next((g for g in match.groups() if g), "")
        if span:
            quotes.append(span.strip())
    return {
        "caseNumbers": case_numbers,
        "decisionNumbers": decision_numbers,
        "authorityClaims": authority_claims,
        "quotes": quotes,
        "hasBindingWording": bool(_BINDING_WORDING_RE.search(body)),
    }


def verify_case_decision_citations(
    text: str,
    evidence_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Verify adjudicative (case/decision) citations against evidence items.

    ``evidence_items`` are normalized precedent-family items (see
    ``precedent_sources.build_source_family_evidence_item``). When it is
    ``None`` the function runs in extract-only mode (never fails) so callers
    without an evidence pack get a benign result. When it is a list (even empty)
    citations are verified and invented ones fail.
    """
    extracted = extract_case_decision_citations(text)
    base = {
        "extracted": extracted,
        "citations": [],
        "quotes": [],
        "warnings": [],
    }
    no_signal = not (
        extracted["caseNumbers"] or extracted["decisionNumbers"]
        or extracted["authorityClaims"] or extracted["quotes"]
    )
    if evidence_items is None:
        base["status"] = "extracted_only" if not no_signal else "no_citations"
        return base
    if no_signal:
        base["status"] = "no_citations"
        return base

    index = _index_evidence_items(evidence_items)
    by_identifier = index["by_identifier"]
    by_family = index["by_family"]
    quote_safe_texts = index["quote_safe_texts"]

    citations: List[Dict[str, Any]] = []

    def family_evidence(family: str) -> List[Dict[str, Any]]:
        return [
            it for it in by_family.get(family, [])
            if str(it.get("citationGrade") or "") != "unavailable"
        ]

    # 1) Concrete case / decision numbers must map to an evidence item.
    for kind, numbers in (("case_number", extracted["caseNumbers"]),
                          ("decision_number", extracted["decisionNumbers"])):
        for num in numbers:
            item = by_identifier.get(_norm_identifier(num))
            if item is None:
                citations.append({
                    "raw": num, "kind": kind, "identifier": num,
                    "family": "", "verification_status": "unverified_fabricated",
                    "notes": "cited case/decision number has no matching evidence item",
                })
                continue
            grade = str(item.get("citationGrade") or "")
            overclaim = extracted["hasBindingWording"] and grade != "direct"
            citations.append({
                "raw": num, "kind": kind, "identifier": num,
                "family": str(item.get("sourceFamily") or ""),
                "verification_status": "overclaimed_contextual" if overclaim else (
                    "verified" if grade == "direct" else "verified_contextual"
                ),
                "matchedCitationGrade": grade,
                "notes": "binding wording over contextual evidence" if overclaim else "",
            })

    # 2) Authority claims by family must have evidence of that family.
    for family in extracted["authorityClaims"]:
        fam_items = family_evidence(family)
        if not fam_items:
            citations.append({
                "raw": family, "kind": "authority_claim", "family": family,
                "verification_status": "unsupported_authority_claim",
                "notes": "adjudicative authority claimed without retrieved evidence",
            })
            continue
        best_grade = "direct" if any(str(i.get("citationGrade")) == "direct" for i in fam_items) else "contextual"
        overclaim = extracted["hasBindingWording"] and best_grade != "direct"
        citations.append({
            "raw": family, "kind": "authority_claim", "family": family,
            "verification_status": "overclaimed_contextual" if overclaim else "verified",
            "matchedCitationGrade": best_grade,
            "notes": "binding wording over contextual-only evidence" if overclaim else "",
        })

    # 3) Direct quotations attributed to decisions must match quoteSafe text.
    quote_results: List[Dict[str, Any]] = []
    adjudicative_context = bool(extracted["authorityClaims"] or extracted["caseNumbers"] or extracted["decisionNumbers"])
    for quote in extracted["quotes"]:
        norm_q = re.sub(r"\s+", " ", quote).strip()
        matched = any(norm_q in safe for safe in quote_safe_texts)
        if matched:
            quote_results.append({"text": quote, "verification_status": "quote_verified"})
        elif adjudicative_context:
            quote_results.append({
                "text": quote, "verification_status": "quote_mismatch",
                "notes": "quoted holding does not match any quoteSafe snippet",
            })
        else:
            quote_results.append({"text": quote, "verification_status": "quote_unattributed"})

    failed = [c for c in citations if c["verification_status"] in _FAILING_STATUSES]
    failed += [q for q in quote_results if q["verification_status"] in _FAILING_STATUSES]
    warnings: List[str] = []
    if any(c["verification_status"] == "unverified_fabricated" for c in citations):
        warnings.append("FABRICATED_CASE_CITATION")
    if any(c["verification_status"] == "unsupported_authority_claim" for c in citations):
        warnings.append("UNSUPPORTED_ADJUDICATIVE_AUTHORITY")
    if any(c["verification_status"] == "overclaimed_contextual" for c in citations):
        warnings.append("CONTEXTUAL_EVIDENCE_OVERCLAIMED")
    if any(q["verification_status"] == "quote_mismatch" for q in quote_results):
        warnings.append("QUOTE_MISMATCH")

    base.update({
        "status": "failed" if failed else "verified",
        "citations": citations,
        "quotes": quote_results,
        "warnings": warnings,
    })
    return base
