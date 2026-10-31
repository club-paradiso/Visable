"""Mission 005-F: does a reply use the language the contract asks for?

Deterministic and script-based, not a language classifier. It decides the required
language (an explicit request in the question wins, otherwise the question's
language, Korean if unclear) and compares it with the reply's word mix. Korean
terms inside brackets or quotes, status codes and evidence IDs are not counted, so
"residence card (외국인등록증)" in an English reply is not a violation. A mix that is
neither clearly right nor clearly wrong is `unresolved`, never a pass or a fail.

This is a separate metric. It is not folded into the historical four-dimension
diagnostic score.
"""
from __future__ import annotations

import re
import unicodedata

LANGUAGES = ("ko", "en", "vi")
DEFAULT_LANGUAGE = "ko"

_HANGUL = re.compile(r"[가-힣]")
_VI_MARK = re.compile(r"[ăâđêôơưạảãáàặẳẵắằậẩẫấầẹẻẽéèệểễếềịỉĩíìọỏõóòộổỗốồợởỡớờụủũúùựửữứừỳỷỹýỵ]", re.IGNORECASE)
_LATIN = re.compile(r"[A-Za-z]")
# Spans whose Korean is a quoted term, not prose in the wrong language.
_PROTECTED_SPAN = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|「[^」]*」|『[^』]*』|\"[^\"]*\"|“[^”]*”|'[^']*'|‘[^’]*’")
_CODE = re.compile(r"(?<![A-Za-z0-9-])[A-Z]{1,3}-\d+(?:-[0-9A-Z]{1,3})*(?![0-9])|[A-Z0-9]+(?:-[A-Z0-9]+)+")

# Explicit requests for a reply language, matched on NFC lower-cased text.
# Mission 005-H added "using/use <language>" and "한국말로" ("Please answer using Korean").
_REQUESTS = {
    "en": re.compile(r"영어로|in english|(?:using|use) english|bằng tiếng anh|tiếng anh"),
    "vi": re.compile(r"베트남어로|in vietnamese|(?:using|use) vietnamese|bằng tiếng việt|tiếng việt"),
    "ko": re.compile(r"한국어로|한국말로|in korean|(?:using|use) korean|bằng tiếng hàn|tiếng hàn"),
}

# Thresholds on the share of counted words. Between them the result is unresolved.
PASS_SHARE = 0.8
FAIL_SHARE = 0.5
VI_MARK_SHARE = 0.15


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def question_language(question: str) -> str:
    """Script of the question itself: ko, vi, en or unknown."""
    text = _nfc(question)
    words = text.split()
    hangul = sum(1 for w in words if _HANGUL.search(w))
    latin = [w for w in words if _LATIN.search(w) and not _HANGUL.search(w)]
    if not words or (not hangul and not latin):
        return "unknown"
    if hangul >= len(latin):
        return "ko"
    if sum(1 for w in latin if _VI_MARK.search(w)) >= max(1, VI_MARK_SHARE * len(latin)):
        return "vi"
    return "en"


def requested_language(question: str) -> str | None:
    """A language the user explicitly asks for, or None. Two different requests is None."""
    text = _nfc(question).lower()
    found = {lang for lang, pattern in _REQUESTS.items() if pattern.search(text)}
    # "tiếng Việt" inside a Vietnamese question is not a request on its own.
    if found == {"vi"} and not re.search(r"베트남어로|in vietnamese|(?:using|use) vietnamese|bằng tiếng việt|trả lời bằng|answer in", text):
        found = set()
    return found.pop() if len(found) == 1 else None


def required_language(question: str) -> dict:
    explicit = requested_language(question)
    if explicit:
        return {"language": explicit, "basis": "explicit_request"}
    lang = question_language(question)
    if lang == "unknown":
        return {"language": DEFAULT_LANGUAGE, "basis": "default_unknown_question"}
    return {"language": lang, "basis": "question_language"}


def word_mix(answer: str) -> dict:
    """Counted words after removing protected spans, codes and evidence IDs."""
    text = _CODE.sub(" ", _PROTECTED_SPAN.sub(" ", _nfc(answer)))
    words = [w for w in text.split() if _HANGUL.search(w) or _LATIN.search(w)]
    hangul = sum(1 for w in words if _HANGUL.search(w))
    latin = [w for w in words if _LATIN.search(w) and not _HANGUL.search(w)]
    return {"words": len(words), "hangul": hangul, "latin": len(latin),
            "vi_marked": sum(1 for w in latin if _VI_MARK.search(w))}


def check(question: str, answer: str, required_override: str | None = None) -> dict:
    """{'result': pass|fail|unresolved, 'required': ..., 'mix': ..., 'reason': ...}.

    A test case may state the required language itself (required_override); the computed
    requirement is still reported so a disagreement between the two is visible.
    """
    required = required_language(question)
    if required_override:
        if required_override not in LANGUAGES:
            raise ValueError(f"Unsupported language: {required_override}")
        required = {"language": required_override, "basis": "case_specification",
                    "computed": required["language"]}
    mix = word_mix(answer)
    lang, n = required["language"], mix["words"]

    def out(result, reason):
        return {"result": result, "required": required, "mix": mix, "reason": reason}

    if n == 0:
        return out("unresolved", "no_counted_words")
    if n < 3 and 0 < mix["hangul"] < n:
        return out("unresolved", "too_few_counted_words")
    hangul_share = mix["hangul"] / n
    latin_share = mix["latin"] / n
    vi_share = mix["vi_marked"] / mix["latin"] if mix["latin"] else 0.0
    if lang == "ko":
        if hangul_share >= PASS_SHARE:
            return out("pass", "korean_reply")
        if hangul_share < 1 - FAIL_SHARE:
            return out("fail", "reply_not_korean")
        return out("unresolved", "mixed_reply")
    if hangul_share > FAIL_SHARE:
        return out("fail", "reply_in_korean")
    if latin_share < PASS_SHARE:
        return out("unresolved", "mixed_reply")
    if lang == "vi":
        if vi_share >= VI_MARK_SHARE:
            return out("pass", "vietnamese_reply")
        if mix["vi_marked"] == 0:
            return out("fail", "reply_not_vietnamese") if n >= 3 else out("unresolved", "too_few_counted_words")
        return out("unresolved", "few_vietnamese_marks")
    if vi_share >= 2 * VI_MARK_SHARE:
        return out("fail", "reply_in_vietnamese")
    if vi_share == 0:
        return out("pass", "english_reply")
    return out("unresolved", "some_vietnamese_marks")
