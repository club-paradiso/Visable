"""Artemis bootstrap defenses: an approved-source gate (가) and a post-answer claim check (나).

Why both: on 2026-10-26 a pattern detector caught 0 of 12 independently written
planted instructions, and E4B relayed the planted claim in 10 of them. So the
defense no longer tries to recognise an attack. It relies on two facts that do
not depend on how an attack is phrased:

* 가 — where text came from. Only evidence whose ``source.approval_state`` is a
  direct-evidence state reaches the model. The states mirror
  ``backend/services/manual_registry.py`` (``DIRECT_EVIDENCE_STATES``): a
  board post, a blog, a user message or a manual chunk still under review is
  never shown to the model as evidence.
* 나 — what the answer asserts. Every amount of money, period, calendar date and
  document name in the answer must be found in the trusted evidence (the
  approved items). One unsupported claim withholds the whole answer and
  replaces it with a fixed abstention. The answer is never patched.

What 나 cannot see: claims without a number or a document noun ("서류가 필요
없다", "승인이 보장된다", "온라인으로만 받는다"), times of day, and numbers
written out in Korean words ("오만 원"). An attack planted inside an approved
document passes 가 by definition and is caught only if it makes one of the
claims 나 extracts.

* 라 — whether approved text is still the text that was approved. Held-out v2
  showed that attacks inside approved documents pass 가 and 나 (7 of 8
  harmful): 나 trusts approved text. With ``integrity=True`` an item counts as
  trusted only if ``source.approved_sha256`` (recorded when a reviewer
  approved the paragraph) equals the hash of its current text, so text edited
  after approval loses its approval before the model sees it. Text that was
  already malicious when it was approved still passes; only review catches that.

Standard library only.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: Mirrors manual_registry.DIRECT_EVIDENCE_STATES (a test keeps them equal).
DIRECT_EVIDENCE_STATES = frozenset({"approved"})

WITHHELD_ANSWER = "공식 근거로 확인되지 않은 금액·기간·날짜·서류가 들어 있어 답변을 보류합니다. 담당 기관에 직접 확인해 주세요."
NO_EVIDENCE_ANSWER = "승인된 공식 근거가 없어 답변을 보류합니다. 담당 기관에 직접 확인해 주세요."


def approval_hash(text: str) -> str:
    """The hash recorded at approval: SHA-256 of the NFC-normalized, stripped paragraph text.
    Normalization and surrounding whitespace are not edits; any other change is."""
    return hashlib.sha256(unicodedata.normalize("NFC", text or "").strip().encode("utf-8")).hexdigest()


def integrity_ok(evidence: Mapping[str, Any]) -> bool:
    """(라) The approved paragraph is byte-for-byte (after NFC + strip) what was approved."""
    recorded = (evidence.get("source") or {}).get("approved_sha256")
    return bool(recorded) and recorded == approval_hash(evidence.get("text", ""))


def is_trusted(evidence: Mapping[str, Any], integrity: bool = False) -> bool:
    source = evidence.get("source") or {}
    if source.get("approval_state") not in DIRECT_EVIDENCE_STATES:
        return False
    return integrity_ok(evidence) if integrity else True


def has_source_labels(case: Mapping[str, Any]) -> bool:
    return all("source" in e for e in case["evidence"])


def gate(case: Mapping[str, Any], integrity: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """(가, and 라 with ``integrity``) The case with only trusted evidence, and the ids withheld."""
    if not has_source_labels(case):
        raise ValueError(f"case {case.get('id')!r} has evidence without source labels; the gate cannot judge it")
    kept = [e for e in case["evidence"] if is_trusted(e, integrity)]
    withheld = [e["id"] for e in case["evidence"] if not is_trusted(e, integrity)]
    return {**case, "evidence": kept}, withheld


# --- 나: claim extraction ---------------------------------------------------

@dataclass(frozen=True)
class Claim:
    kind: str       # money | period | date | document
    text: str       # as written in the answer
    key: Tuple      # comparable form


_NUM = r"\d[\d,.]*"
_MONEY_RE = re.compile(
    rf"(?P<n>{_NUM})\s*(?P<mul>만|천)?\s*(?P<cur>원|달러|USD|KRW|VND|đồng|dong|元|韩元|won\b)"
    rf"|(?P<cur2>USD|KRW|VND|\$|₩|￦)\s*(?P<n2>{_NUM})"
)
#: Korean amounts written in units: "3만5천원", "1억 2천만원", "5만 원".
_KRW_COMPOUND_RE = re.compile(r"(?P<amt>(?:\d[\d,.]*\s*(?:억|만|천)\s*)+\d*)\s*(?:원|won\b)")
#: Numbers standing alone in the evidence (table cells such as "소득기준 23,595,948"):
#: at least four digits, not part of a date and not followed by a non-money unit.
#: They count as won amounts only in a money context (see _bare_amounts).
_MONEY_WORD_RE = re.compile(r"수수료|소득|금액|비용|예치금|급여|임금|보수|보증금|기준액|심사료|요금|원\s*\)")
_WON_UNIT_DECLARED_RE = re.compile(r"\(\s*원\s*\)|단위\s*[:：]?\s*원")
_BARE_AMOUNT_RE = re.compile(
    r"(?<![\d,.])(?P<n>\d{1,3}(?:,\d{3})+|\d{4,})(?![\d,.])"
    r"(?!\s*(?:개월|개|달|주|일|년|월|명|%|퍼센트|점|시간|회|세|쪽|호|조|항|번|차|건|kg|km|m\b|원))"
)
_FREE_RE = re.compile(r"무료|free of charge|免费|miễn phí", re.IGNORECASE)
_DATE_FULL_RE = re.compile(r"(?P<y>\d{4})\s*(?:년|[.\-/])\s*(?P<m>\d{1,2})\s*(?:월|[.\-/])\s*(?P<d>\d{1,2})\s*일?")
_DATE_MD_RE = re.compile(r"(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일")
_PERIOD_RE = re.compile(
    r"(?P<n>\d+)\s*(?P<u>개월|달|주일|주|일|년|days?\b|weeks?\b|months?\b|years?\b|个月|天|周|年|ngày|tuần|tháng|năm)",
    re.IGNORECASE,
)
#: "1월 이내", "6월 이상", "3월간", "1월이 경과": the manuals' older way of writing N months.
#: Only with a duration word after it, so "3월에 접수" (March) is never read as a period.
_MONTH_SPAN_RE = re.compile(r"(?P<n>\d+)\s*월(?=\s*(?:이내|이상|이하|미만|초과|간|동안|이\s*경과|이\s*지나|을\s*초과|를\s*초과|을\s*넘|를\s*넘))")
#: Periods written with Korean number words: "두 달", "석 달", "두 주", "열흘", "보름",
#: and Sino-Korean numerals before 개월/년 ("육 개월", "일 년") or a 십 numeral before 일
#: ("십오 일"). The numeral must start a word, so "한국", "두 번", "세 가지" are not read.
_NATIVE_COUNT = {"한": 1, "두": 2, "세": 3, "석": 3, "서": 3, "네": 4, "넉": 4, "너": 4, "다섯": 5, "여섯": 6,
                 "일곱": 7, "여덟": 8, "아홉": 9, "열": 10, "열한": 11, "열두": 12}
_PARTICLE = r"(?=$|[^가-힣]|간|일|이|가|을|를|은|는|에|의|도|만|씩|째|후|뒤|전|내|동안)"
_NATIVE_PERIOD_RE = re.compile(
    r"(?<![가-힣])(?P<w>열한|열두|다섯|여섯|일곱|여덟|아홉|한|두|세|석|서|네|넉|너|열)\s*"
    r"(?:(?P<m>달)(?!러|력|리|성|라)|(?P<wk>주)" + _PARTICLE + r")"
)
_DAY_WORDS = {"하루": 1, "이틀": 2, "사흘": 3, "나흘": 4, "닷새": 5, "엿새": 6, "이레": 7, "여드레": 8,
              "아흐레": 9, "열흘": 10, "보름": 15}
_DAY_WORD_RE = re.compile(r"(?<![가-힣])(?P<w>" + "|".join(sorted(_DAY_WORDS, key=len, reverse=True)) + r")")
_SINO_DIGIT = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_SINO_PERIOD_RE = re.compile(
    r"(?<![가-힣])(?:(?P<n>(?:[이삼사오육칠팔구]?십)?[일이삼사오육칠팔구]|[이삼사오육칠팔구]?십)\s*(?P<u>개월|년)"
    r"|(?P<n2>[이삼사오육칠팔구]?십[일이삼사오육칠팔구]?)\s*일)"
)
_UNIT = {
    "개월": "month", "달": "month", "months": "month", "month": "month", "个月": "month", "tháng": "month",
    "주": "week", "주일": "week", "weeks": "week", "week": "week", "周": "week", "tuần": "week",
    "일": "day", "days": "day", "day": "day", "天": "day", "ngày": "day",
    "년": "year", "years": "year", "year": "year", "年": "year", "năm": "year",
}
DOCUMENT_NOUNS: Tuple[str, ...] = (
    "증명서", "확인서", "진단서", "신청서", "신고서", "위임장", "등록증", "신분증", "계약서", "통지서",
    "등본", "초본", "사본", "여권", "사진", "서약서", "소견서", "보증서", "명세서",
)
_DOC_RE = re.compile(r"[가-힣]{0,6}(?:" + "|".join(DOCUMENT_NOUNS) + r")")


def _number(text: str) -> Optional[float]:
    digits = text.replace(",", "")
    if digits.count(".") > 1:          # "500.000" written with dots as thousands separators
        digits = digits.replace(".", "")
    try:
        return float(digits)
    except ValueError:
        return None


def _krw_compound(amount: str) -> Optional[float]:
    total, seen = 0.0, False
    for n, unit in re.findall(r"(\d[\d,.]*)\s*(억|만|천)?", amount):
        value = _number(n)
        if value is None:
            return None
        total += value * {"억": 100_000_000, "만": 10_000, "천": 1_000}.get(unit, 1)
        seen = True
    return total if seen else None


def _money_claims(text: str) -> List[Claim]:
    claims: List[Claim] = []
    for m in _KRW_COMPOUND_RE.finditer(text):
        value = _krw_compound(m.group("amt"))
        if value is not None:
            claims.append(Claim("money", m.group(0), ("money", "krw", value)))
    text = _KRW_COMPOUND_RE.sub(lambda m: " " * len(m.group(0)), text)
    for m in _MONEY_RE.finditer(text):
        value = _number(m.group("n") or m.group("n2") or "")
        if value is None:
            continue
        value *= {"만": 10000, "천": 1000}.get(m.group("mul") or "", 1)
        currency = (m.group("cur") or m.group("cur2") or "").lower()
        currency = {"원": "krw", "won": "krw", "krw": "krw", "₩": "krw", "￦": "krw", "韩元": "krw",
                    "달러": "usd", "usd": "usd", "$": "usd", "vnd": "vnd", "đồng": "vnd", "dong": "vnd",
                    "元": "cny"}.get(currency, currency)
        claims.append(Claim("money", m.group(0), ("money", currency, value)))
    for m in _FREE_RE.finditer(text):
        claims.append(Claim("money", m.group(0), ("money", "free", 0.0)))
    return claims


def _date_claims(text: str) -> Tuple[List[Claim], str]:
    """Dates, and the text with them blanked out so their 년/일 are not read as periods."""
    claims: List[Claim] = []
    masked = text
    for regex, has_year in ((_DATE_FULL_RE, True), (_DATE_MD_RE, False)):
        for m in regex.finditer(masked):
            year = int(m.group("y")) if has_year else None
            claims.append(Claim("date", m.group(0), ("date", year, int(m.group("m")), int(m.group("d")))))
        masked = regex.sub(lambda m: " " * len(m.group(0)), masked)
    return claims, masked


def _period_claims(text: str) -> List[Claim]:
    claims: List[Claim] = []
    for m in _PERIOD_RE.finditer(text):
        unit = _UNIT[m.group("u").lower()]
        n = int(m.group("n"))
        if unit == "week":              # "2주" and "14일" are the same period
            unit, n = "day", n * 7
        claims.append(Claim("period", m.group(0), ("period", unit, n)))
    for m in _MONTH_SPAN_RE.finditer(text):
        claims.append(Claim("period", m.group(0), ("period", "month", int(m.group("n")))))
    for m in _NATIVE_PERIOD_RE.finditer(text):
        n = _NATIVE_COUNT[m.group("w")]
        claims.append(Claim("period", m.group(0), ("period", "month", n) if m.group("m") else ("period", "day", n * 7)))
    for m in _DAY_WORD_RE.finditer(text):
        claims.append(Claim("period", m.group(0), ("period", "day", _DAY_WORDS[m.group("w")])))
    for m in _SINO_PERIOD_RE.finditer(text):
        unit = {"개월": "month", "년": "year"}.get(m.group("u"), "day")
        claims.append(Claim("period", m.group(0), ("period", unit, _sino(m.group("n") or m.group("n2")))))
    return claims


def _sino(word: str) -> int:
    """"육" -> 6, "십오" -> 15, "이십" -> 20."""
    if "십" not in word:
        return _SINO_DIGIT[word]
    tens, _, ones = word.partition("십")
    return (_SINO_DIGIT[tens] if tens else 1) * 10 + (_SINO_DIGIT[ones] if ones else 0)


def _bare_amounts(text: str) -> set:
    """Bare numbers that the evidence itself marks as won: a money word shortly before
    the number on its line, or a table row in text that declares the unit as 원.
    "최소 면적 12,500제곱미터" is not an amount (held-out v4 V-24, 2026-10-28)."""
    declared = bool(_WON_UNIT_DECLARED_RE.search(text))
    amounts = set()
    for line in text.splitlines():
        for m in _BARE_AMOUNT_RE.finditer(line):
            before = line[max(0, m.start() - 30):m.start()]
            if _MONEY_WORD_RE.search(before) or (declared and line.lstrip().startswith("|")):
                amounts.add(_number(m.group("n")))
    return amounts


def _document_claims(text: str) -> List[Claim]:
    claims = []
    for m in _DOC_RE.finditer(text):
        noun = next(n for n in DOCUMENT_NOUNS if m.group(0).endswith(n))
        claims.append(Claim("document", m.group(0), ("document", m.group(0), noun)))
    return claims


def extract_claims(text: str) -> List[Claim]:
    dates, masked = _date_claims(text or "")
    return _money_claims(masked) + dates + _period_claims(masked) + _document_claims(text or "")


def _supported(claim: Claim, trusted_claims: Sequence[Claim], trusted_text: str) -> bool:
    if claim.kind == "document":
        written, noun = claim.key[1], claim.key[2]
        squeezed = re.sub(r"\s+", "", trusted_text)
        # The noun as written, or a tail at least two characters longer than the
        # bare noun: "건강진단서" needs "건강진단서" (or "강진단서"), never just
        # "진단서"; a bare "사진" is supported by "증명사진".
        tails = [written[i:] for i in range(len(written) - len(noun) + 1)]
        floor = min(len(written), len(noun) + 2)
        return any(t in squeezed for t in tails if len(t) >= floor)
    if claim.kind == "date" and claim.key[1] is None:
        return any(t.kind == "date" and t.key[2:] == claim.key[2:] for t in trusted_claims)
    if claim.kind == "date":
        return any(t.kind == "date" and t.key[2:] == claim.key[2:] and t.key[1] in (None, claim.key[1])
                   for t in trusted_claims)
    if any(t.key == claim.key for t in trusted_claims):
        return True
    # A won amount the evidence prints as a bare number ("소득기준 23,595,948" in a
    # table whose header carries the unit). Found on manual_buttons B-10, 2026-10-28.
    if claim.kind == "money" and claim.key[1] == "krw" and claim.key[2] >= 1000:
        return claim.key[2] in _bare_amounts(trusted_text)
    return False


def post_check(parsed: Optional[Mapping[str, Any]], trusted: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """(나) Verdict on one parsed model output against the trusted evidence.

    Returns ``verdict`` (``pass`` | ``withheld`` | ``no_trusted_evidence`` |
    ``unparseable``), the claims found, the unsupported ones, and ``final``: the
    output to show, which is the model's own when the verdict is ``pass``."""
    abstain = {"status": "insufficient_evidence", "citations": []}
    if parsed is None:
        return {"verdict": "unparseable", "claims": [], "unsupported": [], "final": {**abstain, "answer": WITHHELD_ANSWER}}
    if not trusted:
        return {"verdict": "no_trusted_evidence", "claims": [], "unsupported": [],
                "final": {**abstain, "answer": NO_EVIDENCE_ANSWER}}
    answer = parsed.get("answer") if isinstance(parsed.get("answer"), str) else ""
    answer = unicodedata.normalize("NFC", answer)
    trusted_ids = {e["id"] for e in trusted}
    # NFC, as approval_hash does: decomposed Hangul (NFD) would hide "1년" from the
    # extractors. Found on held-out v3 case R-25 (2026-10-26), fixed after that run.
    trusted_text = unicodedata.normalize("NFC", "\n".join(f"{e['title']}\n{e['text']}" for e in trusted))
    trusted_claims = extract_claims(trusted_text)
    claims = extract_claims(answer)
    unsupported = [c.text for c in claims if not _supported(c, trusted_claims, trusted_text)]
    citations = parsed.get("citations") if isinstance(parsed.get("citations"), list) else []
    untrusted_citations = sorted({str(c) for c in citations} - trusted_ids)
    found = [{"kind": c.kind, "text": c.text} for c in claims]
    if unsupported or untrusted_citations:
        return {"verdict": "withheld", "claims": found, "unsupported": unsupported,
                "untrusted_citations": untrusted_citations, "final": {**abstain, "answer": WITHHELD_ANSWER}}
    return {"verdict": "pass", "claims": found, "unsupported": [], "untrusted_citations": [], "final": dict(parsed)}
