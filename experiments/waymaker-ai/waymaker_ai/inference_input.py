"""Explicit, non-recursive projection at every Artemis evidence/prompt boundary.

Evidence bodies remain verbatim, untrusted source material. Review decisions,
answer keys and arbitrary nested metadata are never model input. This is not
an authenticity or legal-approval check; those remain evaluator-side gates.
"""
import re
from collections.abc import Mapping

SOURCE_TEXT_FIELDS = (
    "document_id", "source_id", "version_id", "provision", "effective_date",
    "publication_date", "retrieval_date", "source_url", "official_url",
    "domain", "provenance", "page_locator",
)
# provenance says what kind of source a text is. Benchmark labels such as
# injection_probe or synthetic_fixture describe the test, not the source, and
# would tell the model it is being evaluated, so only real source kinds pass.
SOURCE_PROVENANCE_VALUES = frozenset({"official_manual", "official_notice", "community_post"})
# Mission 005-G: values the trusted-evidence pipeline computes itself and hands to a
# v4/v5 prompt. They come from the system, never from the item's own fields or labels.
# v5 (Mission 005-H) and later send uncovered_items as item names in the reply language; v7 (005-J)
# adds scope_status_code when the system asks one sub-code at a time; v8 (005-K) adds scope_location
# (one applicant situation at a time) and as_of (the date the question is about); v10 (005-M) adds
# uncovered_sentence (the system's sentence naming the uncovered items in the reply language); v12 (005-P)
# adds language_retry (the system's note that the previous answer was not in the reply language); v13 (005-R)
# adds branch_retry (the system's note quoting a case of the cited evidence the previous answer left out); v14
# (005-T) adds status_retry (the system's note naming a status or form problem of the previous answer); v15
# (005-U) adds conflict_records (pairs of evidence IDs whose texts differ only in their numbers); v16 (005-V) adds
# choice_retry (the system's note that a choice question was answered with only one of its codes); v17 (005-W) adds
# choice_codes (the codes a choice question asks between that the evidence names).
SYSTEM_FIELDS = ("reply_language", "uncovered_items", "scope_status_code", "scope_location", "as_of", "uncovered_sentence",
                 "language_retry", "branch_retry", "status_retry", "conflict_records", "choice_retry", "choice_codes")
REPLY_LANGUAGES = frozenset({"ko", "en", "vi"})


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
                           if isinstance(source.get(key), str)
                           and (key != "provenance" or source[key] in SOURCE_PROVENANCE_VALUES)}
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
    projected = {"question": question, "evidence": [project_evidence(e) for e in evidence]}
    system = item.get("system")
    if system is not None:
        if not isinstance(system, Mapping) or set(system) - set(SYSTEM_FIELDS):
            raise ValueError("System fields must be a map of allowlisted pipeline values")
        if system.get("reply_language") not in REPLY_LANGUAGES:
            raise ValueError("System reply_language must be ko, en or vi")
        items = system.get("uncovered_items", [])
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise ValueError("System uncovered_items must be a list of item names")
        projected["system"] = {"reply_language": system["reply_language"], "uncovered_items": list(items)}
        if "scope_status_code" in system:
            if not isinstance(system["scope_status_code"], str) or not re.fullmatch(r"[A-Z]-\d{1,2}-\d{1,2}", system["scope_status_code"]):
                raise ValueError("System scope_status_code must be one status sub-code")
            projected["system"]["scope_status_code"] = system["scope_status_code"]
        if "scope_location" in system:
            if system["scope_location"] not in ("domestic", "abroad"):
                raise ValueError("System scope_location must be domestic or abroad")
            projected["system"]["scope_location"] = system["scope_location"]
        if "as_of" in system:
            if not isinstance(system["as_of"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", system["as_of"]):
                raise ValueError("System as_of must be a YYYY-MM-DD date")
            projected["system"]["as_of"] = system["as_of"]
        if "uncovered_sentence" in system:
            text = system["uncovered_sentence"]
            if not isinstance(text, str) or not text.strip() or len(text) > 300 or "\n" in text:
                raise ValueError("System uncovered_sentence must be one short line")
            projected["system"]["uncovered_sentence"] = text
        if "language_retry" in system:
            text = system["language_retry"]
            if not isinstance(text, str) or not text.strip() or len(text) > 300 or "\n" in text:
                raise ValueError("System language_retry must be one short line")
            projected["system"]["language_retry"] = text
        if "branch_retry" in system:
            text = system["branch_retry"]
            if not isinstance(text, str) or not text.strip() or len(text) > 600 or "\n" in text:
                raise ValueError("System branch_retry must be one line of at most 600 characters")
            projected["system"]["branch_retry"] = text
        if "status_retry" in system:
            text = system["status_retry"]
            if not isinstance(text, str) or not text.strip() or len(text) > 600 or "\n" in text:
                raise ValueError("System status_retry must be one line of at most 600 characters")
            projected["system"]["status_retry"] = text
        if "choice_retry" in system:
            text = system["choice_retry"]
            if not isinstance(text, str) or not text.strip() or len(text) > 600 or "\n" in text:
                raise ValueError("System choice_retry must be one line of at most 600 characters")
            projected["system"]["choice_retry"] = text
        if "conflict_records" in system:
            pairs = system["conflict_records"]
            ids = {e["id"] for e in projected["evidence"]}
            if not isinstance(pairs, list) or not pairs or len(pairs) > 10 or not all(
                    isinstance(p, list) and len(p) == 2 and all(isinstance(i, str) and i in ids for i in p) and p[0] != p[1]
                    for p in pairs):
                raise ValueError("System conflict_records must be pairs of two different evidence IDs of this item")
            projected["system"]["conflict_records"] = [list(p) for p in pairs]
        if "choice_codes" in system:
            codes = system["choice_codes"]
            texts = " ".join(e["text"] for e in projected["evidence"])
            if not isinstance(codes, list) or not 2 <= len(codes) <= 6 or len(set(codes)) != len(codes) or not all(
                    isinstance(c, str) and re.fullmatch(r"[A-Z]-\d{1,2}(?:-\d{1,2})?", c) and c in texts for c in codes):
                raise ValueError("System choice_codes must be two to six different status codes named in this item's evidence")
            projected["system"]["choice_codes"] = list(codes)
    return projected
