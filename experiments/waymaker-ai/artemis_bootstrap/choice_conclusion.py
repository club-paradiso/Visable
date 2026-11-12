"""Mission 005-Z: which choice code does an answer say the comparison question asks for?

In the 005-Y run (A05Y-45, "which of N-4-1 and N-4-3 has the lower fee?") the N-4-1 part answered correctly
and the N-4-3 part said N-4-3 is lower; the joined answer contradicted itself and was released. This module
reads, for a comparison question (lower, higher, shorter, longer in ko, en, vi), which code each answer
sentence claims as the one the question asks for:

  - a sentence claims a code when it carries the question's comparison word, no negation, and names the
    code outside a comparison side ("… than X", "X보다", "so với X", "compared to X", "unlike X",
    "X와 달리", "X가 아니라", "không phải X");
  - a sentence that leaves more than one code outside a comparison side, or points to "the other" code,
    claims nothing.

`conflict()` is true when the claims of the parts name two different codes. `against_values()` lists claims
that contradict the values the evidence gives: when each choice code has exactly one number in its own
evidence sentences (choice_coverage.own_sentences), the claimed code must hold the lowest value for
lower/shorter and the highest for higher/longer. Questions that ask which code covers someone ("해당",
"falls under") are left out: two correct parts can each say which group falls under their code. The rule
is lexical and never judges which code applies on its own. No model is called here.
"""
from __future__ import annotations

import re
import unicodedata

import choice_coverage

_SENT = re.compile(r"(?:[^.!?。\n]|(?<=\d)\.(?=\d))+(?:[.!?。]|$)")
#: (question cue, answer cue, direction): "min" for lower/shorter, "max" for higher/longer.
FAMILIES = (
    (r"더\s*낮|더\s*적|저렴|\blower\b|\bless\b|\bcheaper\b|thấp\s+hơn|ít\s+hơn|rẻ\s+hơn",
     r"더\s*낮|더\s*적|적은|낮은|저렴|\blower\b|\bless\b|\bcheaper\b|thấp\s+hơn|ít\s+hơn|rẻ\s+hơn", "min"),
    (r"더\s*높|더\s*많|비싼|\bhigher\b|\bmore\b|cao\s+hơn|nhiều\s+hơn|đắt\s+hơn",
     r"더\s*높|더\s*많|높은|비싼|\bhigher\b|\bmore\b|cao\s+hơn|nhiều\s+hơn|đắt\s+hơn", "max"),
    (r"더\s*짧|빠른|\bshorter\b|\bfaster\b|ngắn\s+hơn|nhanh\s+hơn",
     r"더\s*짧|짧은|빠른|\bshorter\b|\bfaster\b|ngắn\s+hơn|nhanh\s+hơn", "min"),
    (r"더\s*길|\blonger\b|dài\s+hơn|lâu\s+hơn",
     r"더\s*길|긴|\blonger\b|dài\s+hơn|lâu\s+hơn", "max"),
)
_NEG = re.compile(r"\bnot\b|n['’]t\b|\bno\b|không|chưa|않|아니|아닌|아닙|아님|없|못")
#: A sentence that points to "the other" code claims nothing about the code it names.
_OTHER = re.compile(r"\bother\b|(?<!\w)khác(?!\w)|còn\s+lại|(?<!\w)kia(?!\w)|다른|나머지")
#: Inside a sentence, up to the comparison marker: no other status code; a comma or dot only inside a number.
_GAP = r"(?:(?![A-Z]-\d)(?:[^.,;]|(?<=\d)[.,](?=\d)))"


def family(question: str):
    """(answer cue, direction) for a comparison question, or None."""
    q = unicodedata.normalize("NFC", question or "")
    for qcue, acue, direction in FAMILIES:
        if re.search(qcue, q, re.IGNORECASE):
            return acue, direction
    return None


def _comparison_side(sentence: str, code: str) -> bool:
    c = re.escape(code)
    return any(re.search(p, sentence) for p in (
        c + _GAP + r"{0,50}?보다", r"\bthan\s+(?:the\s+)?(?:fictional\s+)?(?:[\w-]+\s+){0,4}?" + c,
        r"compared\s+(?:to|with)\s+(?:[\w-]+\s+){0,4}?" + c, r"\bunlike\s+(?:[\w-]+\s+){0,4}?" + c,
        r"so\s+với\s+(?:[^\s,.]+\s+){0,6}?" + c, c + _GAP + r"{0,20}?(?:와|과)\s*달리",
        r"không\s+phải\s+(?:là\s+)?" + c, c + _GAP + r"{0,15}?(?:이|가)?\s*아니라"))


def claims(question: str, answer: str, codes: list) -> set:
    """The choice codes the answer's sentences claim as the one the comparison question asks for."""
    fam = family(question)
    if not fam:
        return set()
    out = set()
    for sentence in _SENT.findall(unicodedata.normalize("NFC", answer or "")):
        if not re.search(fam[0], sentence, re.IGNORECASE) or _NEG.search(sentence) or _OTHER.search(sentence):
            continue
        named = set(choice_coverage._CODE.findall(sentence))
        main = [c for c in codes if c in named and not _comparison_side(sentence, c)]
        if len(main) == 1:
            out.add(main[0])
    return out


def conflict(question: str, answers: list, codes: list) -> bool:
    """True when the answers (one per choice part) together claim two different codes."""
    return len(set().union(set(), *(claims(question, a, codes) for a in answers))) > 1


def own_values(codes: list, texts: list) -> dict:
    """Each code's single number in its own evidence sentences, or {} when any code has none or several."""
    out = {}
    for code in codes:
        nums = set().union(set(), *(choice_coverage._numbers(s) for s in choice_coverage.own_sentences(code, codes, texts)))
        values = {float(n.replace(",", "")) for n in nums if re.fullmatch(r"\d+(?:,\d+)?", n)}
        if len(values) != 1:
            return {}
        out[code] = values.pop()
    return out


def against_values(question: str, answers: list, codes: list, texts: list) -> list:
    """Claimed codes that do not hold the lowest (lower/shorter) or highest (higher/longer) own value."""
    fam = family(question)
    values = own_values(codes, texts) if fam else {}
    if not values or len(set(values.values())) != len(values):
        return []
    best = (min if fam[1] == "min" else max)(values, key=values.get)
    claimed = set().union(set(), *(claims(question, a, codes) for a in answers))
    return sorted(c for c in claimed if c != best)
