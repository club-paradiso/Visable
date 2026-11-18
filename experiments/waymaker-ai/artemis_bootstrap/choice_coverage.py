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

Mission 005-X asks about one choice code at a time (choice_part) and joins the answers. A part could
then attach the question's value to the wrong code. swapped_values() finds a number in a part's answer
that the evidence states only in another choice code's own sentence (a sentence naming that code and
no other choice code) and not in this code's own sentences. An answer sentence that names another choice
code is left out: it is a contrast about that code. A value the question quotes counts only when the
answer states none of this code's own values. Status codes are left out of the numbers
and thousands separators are ignored (46,000 = 46.000 = 46000). A value written in words is not seen.
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


_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# 005-X: a sentence does not end at a dot between digits (46.000), unlike _SENTENCE used for notices.
_SENTENCE_X = re.compile(r"(?:[^.!?。]|(?<=\d)\.(?=\d))+(?:[.!?。]|$)")


def _written(text: str) -> dict:
    """Each number of a text (status codes left out) by its value without thousands separators, as first written."""
    text = _CODE.sub(" ", unicodedata.normalize("NFC", text or ""))
    out = {}
    for n in _NUMBER.findall(text):
        out.setdefault(re.sub(r"[.,]", "", n) if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", n) else n, n)
    return out


def _numbers(text: str) -> set:
    """The numbers of a text with its status codes left out; thousands separators are ignored."""
    return set(_written(text))


def own_sentences(code: str, codes: list, texts: list) -> list:
    """The evidence sentences that name the code and no other of the choice codes (a leading [title] left out)."""
    others = [c for c in codes if c != code]
    out = []
    for text in texts:
        body = _TITLE.sub("", unicodedata.normalize("NFC", text or ""), count=1)
        for sentence in _SENTENCE_X.findall(body):
            named = set(_CODE.findall(sentence))
            if code in named and not named & set(others):
                out.append(sentence.strip())
    return out


def swapped_values(code: str, codes: list, answer: str, texts: list, question: str = "") -> list:
    """Mission 005-X: numbers in an answer about `code` that the evidence states only for another choice code.

    [{"code", "values" (as the answer writes them), "sentence" (this code's first own sentence)}] or [] when nothing is swapped
    or when the code has no own sentence (one sentence naming every code, as DEV-20 v2 003)."""
    mine = own_sentences(code, codes, texts)
    if not mine:
        return []
    own = set().union(*(_numbers(s) for s in mine))
    other = set().union(*(_numbers(s) for c in codes if c != code for s in own_sentences(c, codes, texts)))
    # An answer sentence that names another choice code is about that code (a contrast), not this one.
    others = set(codes) - {code}
    about = [x for x in _SENTENCE_X.findall(unicodedata.normalize("NFC", answer or "")) if not set(_CODE.findall(x)) & others]
    written = {}
    for x in about:
        for k, v in _written(x).items():
            written.setdefault(k, v)
    swapped = (set(written) & other) - own
    # A value the question itself quotes ("which one pays 46,000 won?") is a contrast when the answer also states
    # this code's own value ("not 46,000 but 19,000"); it counts only when the answer gives no own value.
    if set(written) & own:
        swapped -= _numbers(question)
    swapped = sorted(swapped)
    return [{"code": code, "values": [written[v] for v in swapped], "sentence": mine[0]}] if swapped else []
