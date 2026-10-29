"""Flag instruction-like text inside retrieved source text (spec 07 §2, invariant 5).

Why: retrieved text is data. Official statute text is low-risk, but OCR noise,
quoted material inside decisions, scraped guidance pages and anything a
fixture or cache can be tampered with may contain text written *to the model*
("이전 지시를 무시하고 …", "ignore previous instructions", a fake
``system:`` line, a ``<script>`` tag). Waymaker never acts on such text. This
module only *flags* it, so that the evidence package can mark the item
(``untrusted_instruction_like_text``) and the context builder can quote it as
data. A flag never changes a verification result: no rule in
``verification.py`` reads it.

This is a heuristic and is documented as one. It is a short list of literal
markers, matched after NFC normalization and case folding, plus one rule that
needs an AI addressee and an imperative in the same sentence, and one that
lets an intensifier stand between an instruction noun and "무시" ("이전 지시를
모두 무시하고": the literal "지시를 무시" missed it in the Artemis bootstrap
smoke case D-injection, 2026-10-26). It will miss
paraphrased or obfuscated instructions, and it can flag a source that merely
*discusses* prompt injection. Statute drafting forms are deliberately not
markers: "하여야 한다", "할 것" (list items of 별표), "<개정 2020. 1. 1.>" and
"정보시스템" do not trigger anything on their own.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

UNTRUSTED_FLAG = "untrusted_instruction_like_text"

#: Literal phrases that address an AI or try to override instructions. Each one
#: carries the override itself ("…를 무시", "ignore …"): a bare "이전 지시" or
#: "위의 지시사항" is ordinary administrative prose, "사용자에게 알리지 아니하고"
#: is labour-law prose (사용자 = employer), and "you are now" is ordinary English
#: guidance ("if you are now staying in Korea").
OVERRIDE_PHRASES_EN: Tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore the above",
    "ignore prior instructions",
    "disregard previous instructions",
    "disregard the above",
    "forget your instructions",
    "new instructions:",
    "system prompt",
    "developer message",
    "do not tell the user",
    "reveal your instructions",
)
OVERRIDE_PHRASES_KO: Tuple[str, ...] = (
    "지시를 무시",
    "지시는 무시",
    "지시사항을 무시",
    "지침을 무시",
    "명령을 무시",
    "시스템 프롬프트",
    "프롬프트를 무시",
)

#: The same override with intensifiers in between: "지시를 모두 무시", "지침은 전부
#: 무시". Only these words may stand between the noun's particle and "무시", so
#: prose such as "지시와 무관한 … 무시" or "지시를 이행하지 않고 … 무시" does not
#: match. "명령" is left to the literal list above: "출국명령을 … 무시" is case prose.
INTENSIFIERS_KO: Tuple[str, ...] = ("모두", "전부", "다", "완전히", "일체", "일절", "싹")
OVERRIDE_WITH_INTENSIFIER_KO = re.compile(
    r"(?:지시|지침|프롬프트)(?:사항)?(?:을|를|은|는|도)\s+(?:(?:"
    + "|".join(INTENSIFIERS_KO)
    + r")\s+){1,2}무시"
)

#: An AI addressed directly: Korean forms carry the topic or vocative particle
#: ("AI는", "챗봇아"), so a page that merely mentions an "AI 상담" service does
#: not count. Generic words statutes use ("시스템", "모델", "프로그램") are absent.
AI_ADDRESSEES_KO: Tuple[str, ...] = (
    "ai는", "ai야", "ai에게", "인공지능은", "인공지능아", "인공지능에게", "챗봇은", "챗봇아", "어시스턴트는",
    "언어모델은", "언어 모델은", "llm은", "gpt는", "chatgpt는", "claude는", "클로드는", "너는", "당신은",
)
#: English addressees, matched as whole words.
AI_ADDRESSEES_EN: Tuple[str, ...] = ("ai", "assistant", "language model", "llm", "chatgpt", "gpt", "claude")
#: Imperatives aimed at a reader. "하여야 한다" (a statutory duty) and the
#: polite "하세요" of public guidance pages are deliberately not listed.
IMPERATIVES_KO: Tuple[str, ...] = (
    "하라", "해라", "하십시오", "해줘", "해 줘", "답하라", "답변하라", "출력하라", "무시하라", "따르라",
    "말하지 마", "알리지 마", "말하지 말", "알리지 말",
)
IMPERATIVES_EN: Tuple[str, ...] = (
    "must answer", "must respond", "must say", "must tell", "should answer", "always answer", "never mention",
    "do not mention", "respond only", "answer only",
)

#: Chat-template and role markers (anywhere in the text).
TEMPLATE_MARKERS: Tuple[str, ...] = (
    "<|im_start|>", "<|im_end|>", "<|system|>", "<|user|>", "<|assistant|>", "<|endoftext|>",
    "[inst]", "[/inst]", "<<sys>>", "<</sys>>",
)
#: Role labels that start a line ("system: …"). "사용자:" is deliberately absent:
#: 사용자 is the employer in 외국인고용법, and forms print "사용자: (서명)".
ROLE_LINE_PREFIXES: Tuple[str, ...] = (
    "system:", "assistant:", "user:", "developer:", "시스템:", "어시스턴트:", "### system", "### instruction",
)
#: Fences and delimiters used to fake the end of a context block.
DELIMITER_MARKERS: Tuple[str, ...] = (
    "```", "</context>", "<context>", "</system>", "<system>", "<instructions>", "</instructions>",
    "begin system prompt", "end system prompt", "end of context", "[system]",
)
#: Active HTML. Plain angle brackets ("<개정 …>", "<신설 …>") are statute notation, not HTML.
HTML_MARKERS: Tuple[str, ...] = (
    "<script", "</script", "<iframe", "<object", "<embed", "<style", "<form", "<meta", "<link ",
    "javascript:", "data:text/html", "onerror=", "onload=", "onclick=",
)

SENTENCE_ENDS = ".!?。\n"


@dataclass(frozen=True)
class InjectionFinding:
    kind: str      # override_phrase | ai_imperative | template_marker | role_marker | prompt_delimiter | html
    marker: str
    start: int     # index into the folded text (NFC, case-folded)


def fold(text: str) -> str:
    """NFC + case folding. Same length as the NFC text for the scripts used here."""
    return unicodedata.normalize("NFC", text or "").casefold()


def _find_all(text: str, kind: str, markers: Tuple[str, ...]) -> List[InjectionFinding]:
    found: List[InjectionFinding] = []
    for marker in markers:
        start = text.find(marker)
        if start != -1:
            found.append(InjectionFinding(kind, marker, start))
    return found


def _overrides_with_intensifier(text: str) -> List[InjectionFinding]:
    return [
        InjectionFinding("override_phrase", m.group(0), m.start())
        for m in OVERRIDE_WITH_INTENSIFIER_KO.finditer(text)
    ]


def _role_lines(text: str) -> List[InjectionFinding]:
    found: List[InjectionFinding] = []
    offset = 0
    for line in text.split("\n"):
        stripped = line.lstrip()
        for prefix in ROLE_LINE_PREFIXES:
            if stripped.startswith(prefix):
                found.append(InjectionFinding("role_marker", prefix, offset + len(line) - len(stripped)))
                break
        offset += len(line) + 1
    return found


def _sentences(text: str) -> List[Tuple[int, str]]:
    sentences: List[Tuple[int, str]] = []
    start = 0
    for index, ch in enumerate(text):
        if ch in SENTENCE_ENDS:
            sentences.append((start, text[start:index + 1]))
            start = index + 1
    if start < len(text):
        sentences.append((start, text[start:]))
    return sentences


def _contains_word(sentence: str, word: str) -> bool:
    """ASCII addressees must stand alone ("ai" is not part of "said"); Korean ones are substrings."""
    if not word.isascii():
        return word in sentence
    index = sentence.find(word)
    while index != -1:
        before = sentence[index - 1] if index > 0 else " "
        after = sentence[index + len(word)] if index + len(word) < len(sentence) else " "
        if not (before.isascii() and before.isalnum()) and not (after.isascii() and after.isalnum()):
            return True
        index = sentence.find(word, index + 1)
    return False


def _ai_imperatives(text: str) -> List[InjectionFinding]:
    """A sentence that both addresses an AI and gives it an order."""
    found: List[InjectionFinding] = []
    for start, sentence in _sentences(text):
        for addressees, imperatives in ((AI_ADDRESSEES_KO, IMPERATIVES_KO), (AI_ADDRESSEES_EN, IMPERATIVES_EN)):
            addressee = next((w for w in addressees if _contains_word(sentence, w)), None)
            ending = next((e for e in imperatives if e in sentence), None) if addressee else None
            if addressee and ending:
                found.append(InjectionFinding("ai_imperative", f"{addressee} … {ending}", start))
                break
    return found


def scan(text: str) -> List[InjectionFinding]:
    """Every instruction-like marker in ``text``, in order of position."""
    folded = fold(text)
    findings = (
        _find_all(folded, "override_phrase", OVERRIDE_PHRASES_EN + OVERRIDE_PHRASES_KO)
        + _overrides_with_intensifier(folded)
        + _find_all(folded, "template_marker", TEMPLATE_MARKERS)
        + _find_all(folded, "prompt_delimiter", DELIMITER_MARKERS)
        + _find_all(folded, "html", HTML_MARKERS)
        + _role_lines(folded)
        + _ai_imperatives(folded)
    )
    return sorted(findings, key=lambda f: (f.start, f.kind, f.marker))


def scan_flags(text: str) -> Tuple[str, ...]:
    """``(UNTRUSTED_FLAG, "kind:…", …)`` when anything was found, else ``()``."""
    kinds = sorted({f.kind for f in scan(text)})
    if not kinds:
        return ()
    return (UNTRUSTED_FLAG,) + tuple(f"kind:{kind}" for kind in kinds)


def is_instruction_like(text: str) -> bool:
    return bool(scan(text))


__all__ = [
    "AI_ADDRESSEES_EN",
    "AI_ADDRESSEES_KO",
    "DELIMITER_MARKERS",
    "HTML_MARKERS",
    "IMPERATIVES_EN",
    "IMPERATIVES_KO",
    "INTENSIFIERS_KO",
    "InjectionFinding",
    "OVERRIDE_PHRASES_EN",
    "OVERRIDE_PHRASES_KO",
    "ROLE_LINE_PREFIXES",
    "TEMPLATE_MARKERS",
    "UNTRUSTED_FLAG",
    "fold",
    "is_instruction_like",
    "scan",
    "scan_flags",
]
