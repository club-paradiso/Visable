"""Mission 005-R: does an answer give only one case of a two-case evidence passage?

DEV-20 v2 item 011: the evidence said holders who meet the notified requirements report a workplace
change within 15 days, and "any other foreigner must obtain permission" first. The model released only
the first case. Nothing in the guard looked at that, because every sentence it wrote was supported.

A passage has two cases when a marker splits it: "; any other …", "; otherwise …", a sentence starting
"Any other …" / "Otherwise …", a sentence starting "다만", a clause starting "그 밖의"/"그 외의", or
"; mọi trường hợp khác …" / "Ngoài ra …" / "trừ trường hợp …". Each side's distinctive words are the
words it has and the other side does not. An answer that carries at least half of one side's
distinctive words and at most 15% of the other side's has left the other case out.

A leading bracketed source title is left out of both sides. The rule is lexical: an answer that
paraphrases one case can escape it, and a paraphrase of both cases can get an unneeded retry and notice.
Deterministic and conservative. It says nothing when the answer is in another language than the
evidence (no shared words to compare), when either side has fewer than three distinctive words, or
when the left-out side names only status codes other than the question's (a "다만 T-5-3 …" exception
does not apply to a T-5-1 question). It never judges which case applies to the user.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

MARKERS = (
    re.compile(r";\s*(?=(?:any|all|every)\s+other\b|otherwise\b)", re.IGNORECASE),
    re.compile(r"(?<=[.!?])\s+(?=(?:any|all|every)\s+other\b|otherwise\b)", re.IGNORECASE),
    re.compile(r"(?<=[.다])\s+(?=다만[,\s])"),
    re.compile(r"(?<=[,.])\s*(?=그\s*(?:밖|외)의\s)"),
    re.compile(r"(?<=[;.])\s*(?=(?:mọi|các)\s+trường\s+hợp\s+khác|ngoài\s+ra\b)", re.IGNORECASE),
    re.compile(r"[,;]?\s+(?=trừ\s+trường\s+hợp)", re.IGNORECASE),
)
MIN_SIDE = 15          # characters on each side of the marker
MIN_DISTINCT = 3       # distinctive words on each side
KEPT, LEFT_OUT = 0.5, 0.15
_STOP = frozenset("the and for with that this who which from into any all every other otherwise must may can shall "
                  "will are was were has have its their there such than then only also case cases person people "
                  "foreigner foreigners holding hold status".split())
_HAN_STOP = frozenset(("다만", "경우", "사람", "외국인", "그밖", "그외"))
_LATIN = re.compile(r"[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ'-]{2,}|\d[\d,]*")
_HANGUL = re.compile(r"[가-힣]{2,}")
_PARTICLE = re.compile(r"(?:으로|에서|에게|까지|부터|이며|이고|이면|하면|은|는|이|가|을|를|의|에|로|과|와|도|만|고|며)$")
_TITLE = re.compile(r"^\s*\[[^\]\n]*\]\s*")
_CODE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-\d{1,2})?)(?![0-9-])")


def words(text: str) -> set:
    """Comparable word stems: Latin and Vietnamese words cut to six letters, Hangul words without a final particle."""
    text = unicodedata.normalize("NFC", text)
    out = set()
    for w in _LATIN.findall(text):
        w = w.lower().replace(",", "")
        if w not in _STOP:
            out.add(w[:6])
    for w in _HANGUL.findall(text):
        w = _PARTICLE.sub("", w)
        if len(w) >= 2 and w not in _HAN_STOP:
            out.add(w[:3])
    return out


def split_cases(text: str) -> Optional[tuple]:
    """The two cases of a passage, or None when no marker splits it into two real sides. A leading
    bracketed source title ("[가상 … 지침] …") is not part of either case."""
    text = _TITLE.sub("", unicodedata.normalize("NFC", text), count=1)
    for marker in MARKERS:
        parts = marker.split(text, maxsplit=1)
        if len(parts) == 2 and len(parts[0].strip()) > MIN_SIDE and len(parts[1].strip()) > MIN_SIDE:
            return parts[0].strip(), parts[1].strip()
    return None


def _parent(code: str) -> str:
    return "-".join(code.split("-")[:2])


def _about_other_code(side: str, context_code: Optional[str]) -> bool:
    codes = set(_CODE.findall(side))
    if not codes or not context_code:
        return False
    return not any(c == context_code or c == _parent(context_code) or _parent(c) == context_code for c in codes)


def omitted_cases(answer: str, evidence_texts: list, context_code: Optional[str] = None) -> list:
    """Each case the answer left out: {"case": the left-out text, "kept": share, "left_out": share}, in evidence order."""
    have = words(answer)
    found = []
    for text in evidence_texts:
        cases = split_cases(text)
        if not cases:
            continue
        a, b = words(cases[0]), words(cases[1])
        only_a, only_b = a - b, b - a
        if len(only_a) < MIN_DISTINCT or len(only_b) < MIN_DISTINCT:
            continue
        share_a, share_b = len(only_a & have) / len(only_a), len(only_b & have) / len(only_b)
        for kept, left, share_kept, share_left in ((cases[0], cases[1], share_a, share_b),
                                                   (cases[1], cases[0], share_b, share_a)):
            if share_kept >= KEPT and share_left <= LEFT_OUT and not _about_other_code(left, context_code):
                found.append({"case": left, "kept": round(share_kept, 2), "left_out": round(share_left, 2)})
    return found
