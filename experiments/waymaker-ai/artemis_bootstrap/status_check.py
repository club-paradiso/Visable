"""Mission 005-T: an answer whose status or form the system can see is wrong, without any expected answer.

Three habits recorded across earlier runs, each found from the pipeline's own inputs only:

  - conflict_not_labelled: two cited admissible records say the same sentence with different
    numbers (the text matches once its numbers are replaced; status codes such as U-6-1 stay as
    written, so per-sub-code records do not match), and the answer's status is answered or partial.
    The model gave both values but called the status answered in A05M/N-28·29 and A05Q/R/S-28.
  - partial_without_uncovered: status partial while the system's uncovered_items (for that part) is
    empty, so nothing asked is missing (A05P/R/S-60).
  - input_field_named: the answer writes an input field name such as uncovered_sentence (A05K-41,
    A05R/S-60).

The pipeline asks once more with a status_retry note naming the problem (contract v14). Nothing is
withheld for it and the model's sentences are never edited. No model is called here.
"""
from __future__ import annotations

import re
import unicodedata

_TITLE = re.compile(r"^\s*\[[^\]\n]*\]\s*")
_NUM = re.compile(r"\d[\d,.]*")
_CODE = re.compile(r"(?<![A-Za-z0-9-])[A-Z]-\d{1,2}(?:-\d{1,2})?(?![0-9-])")
INPUT_FIELDS = ("uncovered_sentence", "uncovered_items", "reply_language", "scope_status_code", "scope_location",
                "language_retry", "branch_retry", "status_retry")
_FIELD_RE = re.compile(r"\b(?:" + "|".join(INPUT_FIELDS) + r")\b")


def _body(text: str) -> str:
    return _TITLE.sub("", unicodedata.normalize("NFC", text or ""), count=1)


def skeleton(text: str) -> str:
    """The record's sentence with its numbers replaced by '#', status codes kept as written."""
    body = _body(text)
    codes = _CODE.findall(body)
    body = _NUM.sub("#", _CODE.sub("\x00", body))
    for code in codes:
        body = body.replace("\x00", code, 1)
    return " ".join(body.split())


def numbers(text: str) -> list:
    return [n.rstrip(".,").replace(",", "") for n in _NUM.findall(_CODE.sub(" ", _body(text)))]


def conflicting_values(cited_texts: list) -> list:
    """Each pair of cited records that differ only in their numbers: [(numbers_a, numbers_b), ...]."""
    found = []
    for i, a in enumerate(cited_texts):
        for b in cited_texts[i + 1:]:
            if skeleton(a) == skeleton(b) and numbers(a) != numbers(b):
                found.append((numbers(a), numbers(b)))
    return found


def problems(status: str, answer: str, cited_texts: list, uncovered_items: list) -> list:
    """The status and form problems of one answer: [{'kind', 'detail'}], in a fixed order."""
    found = []
    if status in ("answered", "partial"):
        pairs = conflicting_values(cited_texts)
        if pairs:
            found.append({"kind": "conflict_not_labelled", "detail": pairs[0]})
    if status == "partial" and not uncovered_items:
        found.append({"kind": "partial_without_uncovered", "detail": None})
    named = sorted(set(_FIELD_RE.findall(answer or "")))
    if named:
        found.append({"kind": "input_field_named", "detail": named})
    return found
