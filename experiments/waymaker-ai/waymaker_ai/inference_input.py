"""Explicit, non-recursive projection at every Artemis evidence/prompt boundary.

Evidence bodies remain verbatim, untrusted source material. Review decisions,
answer keys and arbitrary nested metadata are never model input. This is not
an authenticity or legal-approval check; those remain evaluator-side gates.
"""
from collections.abc import Mapping

SOURCE_TEXT_FIELDS = (
    "document_id", "source_id", "version_id", "provision", "effective_date",
    "publication_date", "retrieval_date", "source_url", "official_url",
    "domain", "provenance", "page_locator",
)


def project_evidence(evidence: Mapping) -> dict:
    if not isinstance(evidence, Mapping):
        raise ValueError("Evidence must be an object")
    projected = {}
    for name in ("id", "title", "text"):
        value = evidence.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"Evidence {name} must be text, not a metadata object")
        projected[name] = value
    source = evidence.get("source", {})
    if not isinstance(source, Mapping):
        raise ValueError("Evidence source must be an object")
    projected["source"] = {key: source[key] for key in SOURCE_TEXT_FIELDS
                           if isinstance(source.get(key), str)}
    page = source.get("page")
    if isinstance(page, str) or type(page) is int:
        projected["source"]["page"] = page
    return projected


def project_inference_item(item: Mapping) -> dict:
    question = item.get("question", "")
    if not isinstance(question, str):
        raise ValueError("Question must be text")
    evidence = item.get("evidence", [])
    if not isinstance(evidence, (list, tuple)):
        raise ValueError("Evidence must be a sequence")
    return {"question": question, "evidence": [project_evidence(e) for e in evidence]}
