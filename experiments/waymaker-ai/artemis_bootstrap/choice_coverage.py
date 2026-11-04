"""Mission 005-V: does an answer to a "which of these codes" question name only one of them?

DEV-20 v2 items 003 ("D-2-1과 D-2-2 중 어느 세부코드로 …") and 004 ("E-7-1과 E-7-4 중 어느 체계에 …")
ask the user to choose between two status codes, and the cited evidence speaks about both. The model
named the right code and dropped what the evidence says about the other (003 in all six recorded runs,
004 in three), while the question asks for the contrast.

A question is a choice when it names two or more status codes and has a choosing word (중 어느·어떤·무엇,
어느 쪽·것·체계·자격, 아니면, 또는, or, which, hay, hoặc, nào). Only sibling codes count: a code and its
own parent (R-4 and R-4-3) are not a choice. A code is missing when the cited evidence names it, the
answer does not, and the answer names another of the question's codes. Codes are compared as written,
so the rule works in every reply language. The rule is lexical: an answer that explains the other code
without writing it gets an unneeded retry. It never judges which code applies to the user. No model is
called here.
"""
from __future__ import annotations

import re
import unicodedata

_CODE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-\d{1,2})?)(?![0-9-])")
CHOICE = re.compile(r"중\s*(?:어느|어떤|무엇|뭐)|어느\s*(?:쪽|것|체계|자격)|아니면|또는|\bor\b|\bwhich\b|\bhay\b|hoặc|nào",
                    re.IGNORECASE)
_TITLE = re.compile(r"^\s*\[[^\]\n]*\]\s*")
_SENTENCE = re.compile(r"[^.!?。]*(?:[.!?。]|$)")


def _parent(code: str) -> str:
    return "-".join(code.split("-")[:2])


def choice_codes(question: str) -> list:
    """The sibling status codes a choice question asks between, in question order, or [] when it is not one."""
    question = unicodedata.normalize("NFC", question or "")
    if not CHOICE.search(question):
        return []
    codes = list(dict.fromkeys(_CODE.findall(question)))
    siblings = [c for c in codes if not any(o != c and (_parent(c) == o or _parent(o) == c) for o in codes)]
    return siblings if len(siblings) >= 2 else []


def sentence_naming(code: str, texts: list) -> str:
    """The first evidence sentence that names the code (a leading [title] left out)."""
    for text in texts:
        body = _TITLE.sub("", unicodedata.normalize("NFC", text or ""), count=1)
        for sentence in _SENTENCE.findall(body):
            if code in _CODE.findall(sentence):
                return sentence.strip()
    return ""


def omitted_choices(question: str, answer: str, cited_texts: list) -> list:
    """Each question code the answer left out though the cited evidence names it:
    [{"code", "codes" (all the question's choice codes, in question order), "named", "sentence"}]."""
    codes = choice_codes(question)
    if not codes:
        return []
    in_answer = set(_CODE.findall(unicodedata.normalize("NFC", answer or "")))
    named = [c for c in codes if c in in_answer]
    if not named:
        return []
    in_evidence = {c for t in cited_texts for c in _CODE.findall(unicodedata.normalize("NFC", t or ""))}
    return [{"code": c, "codes": codes, "named": named, "sentence": sentence_naming(c, cited_texts)}
            for c in codes if c not in in_answer and c in in_evidence]
