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
#: Korean amounts written in units: "3만5천원", "1억 2천만원", "5만 원", "3,896만 8,428원"
#: (a comma in the tail was cut at "8" and the rest read as 8,428원; held-out v9).
_KRW_COMPOUND_RE = re.compile(r"(?P<amt>(?:\d[\d,.]*\s*(?:억|만|천)\s*)+(?:\d[\d,]*)?)\s*(?:원|won\b)")
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
    # Not the digit of a status code: "D-2 일반대학" is not two days.
    r"(?<![A-Za-z]-)(?<![\d-])(?P<n>\d+)\s*(?P<u>개월|달|주일|주|일|년|days?\b|weeks?\b|months?\b|years?\b|个月|天|周|年|ngày|tuần|tháng|năm)",
    re.IGNORECASE,
)
#: "1월 이내", "6월 이상", "3월간", "1월이 경과": the manuals' older way of writing N months.
#: Only with a duration word after it, so "3월에 접수" (March) is never read as a period.
_MONTH_SPAN_RE = re.compile(r"(?P<n>\d+)\s*월(?=\s*(?:이내|이상|이하|미만|초과|간|동안|이\s*경과|이\s*지나|을\s*초과|를\s*초과|을\s*넘|를\s*넘))")
#: Periods written with Korean number words: "두 달", "석 달", "두 주", "두 해", "열흘",
#: "보름", and Sino-Korean numerals before 개월/년 ("육 개월", "일 년") or before 일
#: ("십오 일", "오 일"). The numeral must start a word, so "한국", "두 번", "세 가지",
#: "해외" are not read.
_NATIVE_COUNT = {"한": 1, "두": 2, "세": 3, "석": 3, "서": 3, "네": 4, "넉": 4, "너": 4, "다섯": 5, "여섯": 6,
                 "일곱": 7, "여덟": 8, "아홉": 9, "열": 10, "열한": 11, "열두": 12}
_PARTICLE = r"(?=$|[^가-힣]|간|일|이|가|을|를|은|는|에|의|도|만|씩|째|후|뒤|전|내|동안|입|마다|부터|까지|넘|미만|정도|쯤|반)"
_NATIVE_PERIOD_RE = re.compile(
    r"(?<![가-힣])(?P<w>열한|열두|다섯|여섯|일곱|여덟|아홉|한|두|세|석|서|네|넉|너|열)\s*"
    r"(?:(?P<m>달)(?!러|력|리|성|라)|(?P<wk>주)" + _PARTICLE + r"|(?P<y>해)" + _PARTICLE + r")"
)
_DAY_WORDS = {"하루": 1, "이틀": 2, "사흘": 3, "나흘": 4, "닷새": 5, "엿새": 6, "이레": 7, "여드레": 8,
              "아흐레": 9, "열흘": 10, "보름": 15}
_DAY_WORD_RE = re.compile(r"(?<![가-힣])(?P<w>" + "|".join(sorted(_DAY_WORDS, key=len, reverse=True)) + r")")
_SINO_DIGIT = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_SINO_PERIOD_RE = re.compile(
    r"(?<![가-힣])(?:(?P<n>(?:[이삼사오육칠팔구]?십)?[일이삼사오육칠팔구]|[이삼사오육칠팔구]?십)\s*(?P<u>개월|년)"
    r"|(?P<n2>[이삼사오육칠팔구]?십[일이삼사오육칠팔구]?)\s*일"
    # A single digit before 일 needs a space ("오 일", never "오일" oil or "삼일절"),
    # and 이/일 are left out: "이 일" (this matter) and "일 일" are ordinary words.
    r"|(?P<n3>[삼사오육칠팔구])\s+일" + _PARTICLE + r")"
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


_COMPOUND_PERIOD_RE = re.compile(r"(?<![A-Za-z]-)(?<![\d-])(\d+)\s*년\s*(\d+)\s*개월")


def _period_claims(text: str) -> List[Claim]:
    claims: List[Claim] = []
    # "4년 10개월" is one period of 58 months, not four years and ten months apart.
    for m in _COMPOUND_PERIOD_RE.finditer(text):
        claims.append(Claim("period", m.group(0), ("period", "month", int(m.group(1)) * 12 + int(m.group(2)))))
    text = _COMPOUND_PERIOD_RE.sub(lambda m: " " * len(m.group(0)), text)
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
        key = ("period", "month", n) if m.group("m") else ("period", "year", n) if m.group("y") else ("period", "day", n * 7)
        claims.append(Claim("period", m.group(0), key))
    for m in _DAY_WORD_RE.finditer(text):
        claims.append(Claim("period", m.group(0), ("period", "day", _DAY_WORDS[m.group("w")])))
    for m in _SINO_PERIOD_RE.finditer(text):
        unit = {"개월": "month", "년": "year"}.get(m.group("u"), "day")
        claims.append(Claim("period", m.group(0), ("period", unit, _sino(m.group("n") or m.group("n2") or m.group("n3")))))
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
        numbers = list(_BARE_AMOUNT_RE.finditer(line))
        row_of_numbers = len(numbers) >= 3   # "소득기준 25,195,752 32,154,216 …": a flattened table row
        for m in numbers:
            before = line[:m.start()] if row_of_numbers else line[max(0, m.start() - 30):m.start()]
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
    # "24개월" for the page's "2년" is the same period (held-out v9 withheld five such answers).
    if claim.kind == "period" and any(t.kind == "period" and _norm_value(*t.key) == _norm_value(*claim.key)
                                      for t in trusted_claims):
        return True
    # A won amount the evidence prints as a bare number ("소득기준 23,595,948" in a
    # table whose header carries the unit). Found on manual_buttons B-10, 2026-10-28.
    if claim.kind == "money" and claim.key[1] == "krw" and claim.key[2] >= 1000:
        return claim.key[2] in _bare_amounts(trusted_text)
    return False


# --- Role check (2026-10-28) -------------------------------------------------
# A value can be in the evidence and still belong to another fact: "신청 후 4일 이내
# 발급, 발급일부터 9일 동안 유효" makes "4일 동안 유효" pass the value check. The role
# check reads, for each period or amount, the role word of its clause (the nearest
# one after the value, since Korean puts the verb last, else the nearest before;
# table cells take their column header) and compares the answer's role with the
# roles the same value has in the approved text. It never withholds: a mismatch
# only marks the answer for a person (smoke_grader counts it as needs_review).
ROLE_WORDS: Dict[str, str] = {
    "validity": r"유효|효력|쓸\s*수\s*있|사용할\s*수\s*있|사용\s*기한|valid",
    "issue": r"발급|교부|발행|내어\s*주|나오|나옵|나온|나와|issue",
    "apply": r"신청|접수|apply|application",
    "submit": r"제출|보완|내야|내면|낸다|내십|submit",
    "stay": r"체류\s*기간|체류할\s*수|체류\s*허가|머무|머물|stay",
    "extend": r"연장|extend",
    "process": r"처리|심사\s*기간|걸린|걸려|걸립|소요|process",
    "report": r"신고|report",
    "wait": r"경과|지나야|지난\s*뒤|지난\s*후|이후에|after",
    "entry": r"재입국|입국|출국|도착|enter|entry|depart",
    "fee": r"수수료|심사료|요금|비용|인지|fee",
    "income": r"소득|연봉|급여|임금|income|salary",
    "deposit": r"예치|잔고|잔액|보증|deposit",
    "fine": r"과태료|벌금|범칙금|fine",
}
_ROLE_RE = {role: re.compile(words, re.IGNORECASE) for role, words in ROLE_WORDS.items()}
#: Roles that answers and manuals use for the same fact ("발급까지 4일 걸린다" is the
#: issuing deadline; "신청" and "제출" of the same papers; a stay permit "유효" for 6개월).
ROLE_FAMILY: Dict[str, str] = {"issue": "issue", "process": "issue",
                               "apply": "file", "submit": "file", "report": "file",
                               "validity": "valid", "stay": "valid", "extend": "valid",
                               "wait": "wait", "entry": "entry", "fee": "fee", "income": "income", "deposit": "deposit", "fine": "fine"}
#: A role word followed by one of these characters is part of a noun, not the fact's role.
_NOUN_SUFFIX = set("증서자일")
_START_POINT_RE = re.compile(r"\s*(?:한|된|하고|되고)?\s*(?:후|뒤|날|때|부터|로부터|이후|직후)")
#: What may stand between a role word and the value it names: "유효기간은 ", "수수료: ", "체류기간 최대 ".
_NAMES_VALUE_RE = re.compile(r"(?:\s*(?:기간|기한|기일|금액|액))?\s*(?:은|는|이|가|도|만)?\s*[:：]?\s*(?:최대|최소|약|총|모두)?\s*")
#: Clause breaks. A comma or point between digits is part of a number ("40,000원", "1.5").
_CLAUSE_SPLIT_RE = re.compile(r"(?<!\d)[.,]|[.,](?!\d)|[\n;·]|(?<=며)\s|(?<=하고)\s|(?<=하되)\s|(?<=이고)\s")


def _roles_in(text: str, at: int, kind: str, lenient: bool = False) -> List[str]:
    """Role(s) of the value at ``at`` in ``text`` (one clause). A role word right before
    the value names it ("체류기간 1년", "수수료는 6만원"); otherwise the nearest role word
    after it (Korean puts the verb last), else the nearest before. ``lenient`` (used for
    answers) also accepts the nearest role word before the value, so an answer is only
    marked when none of its readings fits the evidence. Money roles only for amounts,
    period roles only for periods."""
    allowed = {"fee", "income", "deposit", "fine"} if kind == "money" else set(ROLE_WORDS) - {"fee", "income", "deposit", "fine"}
    after, before, named = [], [], []
    for role in allowed:
        for m in _ROLE_RE[role].finditer(text):
            # 접수증, 신청서, 신청자, 발급일부터, 입국일로부터 name a paper, person or date,
            # not the fact a period belongs to. An amount, though, is named by its paper:
            # "18,000,000원 이상의 잔고증명서" is a deposit.
            if kind != "money" and text[m.end():m.end() + 1] in _NOUN_SUFFIX:
                continue
            # "입국 후 90일", "신청한 날부터", "발급한 뒤": a starting point, not the role.
            if kind != "money" and _START_POINT_RE.match(text, m.end()):
                continue
            if m.start() >= at:
                after.append((m.start() - at, role))
            else:
                before.append((at - m.end(), role))
                if _NAMES_VALUE_RE.fullmatch(text[m.end():at]):
                    named.append((at - m.end(), role))
    if named:
        return [min(named)[1]]
    nearest_before = min(before)[1] if before else None
    roles = [min(after)[1]] if after else ([nearest_before] if nearest_before else [])
    if lenient and nearest_before and nearest_before not in roles:
        roles.append(nearest_before)
    return roles


def _clauses(text: str) -> List[str]:
    """Clauses, with each table row joined to its header so a cell reads its column name."""
    out: List[str] = []
    header: Optional[List[str]] = None
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells is None:
            header = None
            out.extend(c for c in _CLAUSE_SPLIT_RE.split(line) if c.strip())
        elif header is None:
            header = cells
        elif not all(set(c) <= set("-: ") for c in cells):
            for i, cell in enumerate(cells):
                head = header[i] if i < len(header) else ""
                out.append(f"{cells[0]} {head} {cell}")
    return out


def _role_pairs(text: str, lenient: bool = False) -> List[Tuple[Tuple, List[str], str]]:
    """(value key, roles, clause) for every amount and period in the text. A bare number
    in a clause that carries a money role word (a table cell under "수수료(원)", or
    "소득기준은 55,000") is read as won."""
    pairs = []
    for clause in _clauses(text):
        dates, masked = _date_claims(clause)
        money = _money_claims(masked)
        for claim in money + _period_claims(masked):
            at = clause.find(claim.text)
            pairs.append((claim.key, _roles_in(clause, max(at, 0), claim.kind, lenient), clause))
        spans = [(clause.find(c.text), clause.find(c.text) + len(c.text)) for c in money]
        for m in _BARE_AMOUNT_RE.finditer(masked):
            if any(a <= m.start() < b for a, b in spans):
                continue
            roles = _roles_in(clause, m.start(), "money", lenient)
            if roles:
                pairs.append((("money", "krw", _number(m.group("n"))), roles, clause))
    return pairs


def role_mismatches(answer: str, trusted_text: str, fact_families: Optional[Mapping[Tuple, set]] = None) -> List[str]:
    """Answer values whose role differs from every role the same value has in the
    approved text. Values with no role word on either side are left alone."""
    evidence = _role_pairs(trusted_text)
    found = []
    for key, roles, clause in _role_pairs(answer, lenient=True):
        if not roles:
            continue
        evidence_roles = [r for k, rs, _ in evidence if k == key for r in rs]
        unroled = any(k == key and not rs for k, rs, _ in evidence)
        families = {ROLE_FAMILY[r] for r in evidence_roles} | set((fact_families or {}).get(_norm_value(*key), ()))
        if evidence_roles and not unroled and not families & {ROLE_FAMILY[r] for r in roles}:
            found.append(f"{clause.strip()} — 답의 역할 '{'/'.join(roles)}', 근거의 역할 '{'/'.join(sorted(set(evidence_roles)))}'")
    return found


# --- Subject check against approved facts (2026-10-28) ---------------------------
# Facts (APPROVED-FACTS-DESIGN.ko.md) say whose value a number is: (subject, role,
# value) for one page. The caller passes the facts of the trusted pages. An answer is
# marked for review when, for the subject and role it names, the facts hold another
# value AND the answer's value is a fact of a different subject, row or role on those
# pages — the row/household/status mix-up the role check cannot see. Never withholds.
FACT_ROLE_FAMILY: Dict[str, str] = {
    "issue_deadline": "issue", "processing_time": "issue", "filing_deadline": "file", "report_deadline": "file",
    "entry_deadline": "entry", "exit_deadline": "entry", "waiting_period": "wait", "validity": "valid",
    "stay_per_grant": "valid", "stay_cap_total": "valid", "extension_period": "valid", "fee": "fee",
    "income_threshold": "income", "deposit": "deposit", "fine": "fine",
}
_STATUS_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-[0-9A-Z]{1,2})?)(?![0-9])")
_HOUSEHOLD_RE = re.compile(r"(\d+)\s*인\s*가구")

# --- Reading the subject from a person's own words (2026-10-28, after held-out v9) ---
# People write "결혼이민", "네 식구", "대사관에서 받는 사증", not "F-6", "4인 가구" or the
# AI's row label. Held-out v9 marked 5 of 72 mixed-up answers before this.
#: Status names from 출입국관리법 시행령 별표 1·1의2. Left out because they are also
#: everyday words or name two statuses: 공무(공무원), 연구(연구과정 is D-2-5), 거주,
#: 동반, 기타, 계절근로 (C-4 and E-8).
_STATUS_NAMES: Dict[str, str] = {
    "외교": "A-1", "협정": "A-3", "사증면제": "B-1", "관광통과": "B-2", "일시취재": "C-1", "단기방문": "C-3",
    "단기취업": "C-4", "문화예술": "D-1", "유학": "D-2", "기술연수": "D-3", "일반연수": "D-4", "어학연수": "D-4",
    "취재": "D-5", "종교": "D-6", "주재": "D-7", "기업투자": "D-8", "무역경영": "D-9", "구직": "D-10",
    "교수": "E-1", "회화지도": "E-2", "기술지도": "E-4", "전문직업": "E-5", "예술흥행": "E-6", "특정활동": "E-7",
    "비전문취업": "E-9", "선원취업": "E-10", "방문동거": "F-1", "재외동포": "F-4", "영주": "F-5",
    "결혼이민": "F-6", "관광취업": "H-1", "방문취업": "H-2",
}
_STATUS_NAME_RE = re.compile("|".join(sorted(map(re.escape, _STATUS_NAMES), key=len, reverse=True)))
#: Everyday names people use (held-out v10 W-07 said "결혼비자"). Only names that point
#: to one status: "취업비자" and "관광비자" stand for several and are left out.
_STATUS_COLLOQUIAL = (
    (re.compile(r"결혼\s*비자|배우자\s*비자|결혼이민\s*비자|(?:marriage|spouse)\s+visa", re.IGNORECASE), "F-6"),
    (re.compile(r"유학\s*비자|학생\s*비자|student\s+visa", re.IGNORECASE), "D-2"),
    (re.compile(r"어학\s*(?:연수)?\s*비자|language\s+(?:student|course|study)\s+visa", re.IGNORECASE), "D-4"),
    (re.compile(r"구직\s*비자|job[\s-]*seeker", re.IGNORECASE), "D-10"),
    (re.compile(r"워홀|워킹\s*홀리데이|working\s+holiday", re.IGNORECASE), "H-1"),
    (re.compile(r"영주권|permanent\s+residen", re.IGNORECASE), "F-5"),
    (re.compile(r"동포\s*비자", re.IGNORECASE), "F-4"),
    (re.compile(r"투자\s*비자|investor\s+visa", re.IGNORECASE), "D-8"),
)
_COUNT_WORDS = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
                "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
_COUNT = r"(\d+|다섯|여섯|일곱|여덟|아홉|한|두|세|네|열)"
#: "네 식구", "4인 가족", "가족이 다섯 명", "family of four". A bare "N명" counts only
#: with a family word in the same sentence ("저희 집은 … 여섯 명이에요").
_FAMILY_COUNT_RES = (
    re.compile(rf"(?<![가-힣]){_COUNT}\s*(?:식구|인\s*가족|명\s*가족|인\s*가구)"),
    re.compile(rf"(?:가족|식구|가구원)[^.?!\n]{{0,8}}?(?<![가-힣]){_COUNT}\s*명"),
    re.compile(rf"(?:집|가족|식구)[^.?!\n]{{0,40}}?(?<![가-힣]){_COUNT}\s*명(?:이에요|입니다|이고|인데|이요)"),
    re.compile(r"family of (\d+|two|three|four|five|six|seven|eight)|(\d+)[- ]person household", re.IGNORECASE),
)
#: Words a person uses for a row's wording, mapped to the manual's word.
_ROW_SYNONYMS = (
    (re.compile(r"대사관|영사관|consulate|embassy", re.IGNORECASE), "공관"),
    (re.compile(r"\bexchange\b", re.IGNORECASE), "교환학생"),
    (re.compile(r"\bIndia(?:n)?\b"), "인도"),
    (re.compile(r"\bPh\.?D\b|doctoral", re.IGNORECASE), "박사"),
    (re.compile(r"어학당|language (?:school|course|program)", re.IGNORECASE), "어학연수"),
)
#: Label words that say what the value is, not whose it is.
_ROW_STOP_RE = re.compile(r"^(?:\d+회|부여|체류기간|유효기간|체류허가|기간|상한|사증|허가|신청|수수료|기준|경우|"
                          r"이상|이하|이내|대상|대상자|소득기준|복수사증|단수사증|사증발급)$")


def _households(text: str) -> set:
    found = {int(h) for h in _HOUSEHOLD_RE.findall(text)}
    for regex in _FAMILY_COUNT_RES:
        for m in regex.finditer(text):
            word = next(g for g in m.groups() if g)
            found.add(int(word) if word.isdigit() else _COUNT_WORDS[word.lower()])
    return found


def _row_tokens(label: str) -> set:
    tokens = set()
    for run in re.findall(r"[가-힣]{2,}", label or ""):
        run = re.sub(r"(?:의|시|등|및)$", "", run)
        if len(run) >= 2 and not _ROW_STOP_RE.match(run):
            tokens.add(run)
    return tokens


def _named_rows(question: str, facts: Sequence[Mapping[str, Any]]) -> set:
    """Row labels whose distinctive words the question uses most. A word is distinctive
    when it is missing from at least one other row of that role family on the page
    ("재입국허가" is not, beside "복수재입국허가"); only the best-matching rows count."""
    said = re.sub(r"\s+", "", question)
    extra = [word for regex, word in _ROW_SYNONYMS if regex.search(question)]
    named = set()
    by_family: Dict[str, List[Mapping[str, Any]]] = {}
    for f in facts:
        if f["subject"]["qualifiers"].get("row_label"):
            by_family.setdefault(FACT_ROLE_FAMILY[f["role"]], []).append(f)
    for group in by_family.values():
        labels = {f["subject"]["qualifiers"]["row_label"] for f in group}
        squeezed = {label: re.sub(r"\s+", "", label) for label in labels}
        scores = {}
        for label in labels:
            score = 0
            for t in _row_tokens(label):
                if all(t in other for other in squeezed.values()):
                    continue
                stem = t[:-1] if len(t) >= 4 else t
                if t in said or stem in said or any(w in t for w in extra):
                    score += 1
            scores[label] = score
        best = max(scores.values(), default=0)
        if best:
            named |= {label for label, score in scores.items() if score == best}
    return named


def _norm_value(kind: str, unit: str, amount: float) -> Tuple:
    if kind == "period" and unit == "year":
        return ("period", "month", amount * 12)
    return (kind, unit, amount)


def subject_mismatches(answer: str, question: str, facts: Sequence[Mapping[str, Any]]) -> List[str]:
    if not facts:
        return []
    usable = [f for f in facts if f.get("role") in FACT_ROLE_FAMILY]
    text = f"{question} {answer}"
    codes = set(_STATUS_CODE_RE.findall(text)) | {_STATUS_NAMES[m] for m in _STATUS_NAME_RE.findall(text)} \
        | {code for regex, code in _STATUS_COLLOQUIAL if regex.search(text)}
    # The person says how many they are; an answer that re-counts them ("세 식구(2인 가구)")
    # does not get to change the subject (held-out v13 S-17).
    households = _households(question) or _households(answer)
    rows = {f["subject"]["qualifiers"].get("row_label") for f in usable
            if f["subject"]["qualifiers"].get("row_label") and f["subject"]["qualifiers"]["row_label"] in text}
    rows |= _named_rows(question, usable)
    # An answer clause with no role word ("네 식구면 32,154,216원 이상입니다") takes the
    # role the question asks about.
    money_roles = {"fee", "income", "deposit", "fine"}
    asked = {kind: {ROLE_FAMILY[r] for r in ROLE_WORDS if (r in money_roles) == (kind == "money") and _ROLE_RE[r].search(question)}
             for kind in ("money", "period")}

    def fits(f: Mapping[str, Any]) -> bool:
        s, q = f["subject"], f["subject"].get("qualifiers") or {}
        if codes and s.get("status_code") and not any(
                c in (s["status_code"], s.get("sub_code")) or c.startswith(s["status_code"] + "-") for c in codes):
            return False
        if households and q.get("household_size") is not None and q["household_size"] not in households:
            return False
        # A named general row also names its narrower rows: "체류기간 연장허가" covers
        # "체류기간 연장허가(결혼이민 F-6)", whose 3만원 is right for an F-6 holder (v9 V-01).
        if rows and q.get("row_label") and not any(r in q["row_label"] for r in rows):
            return False
        # "가구원 1인당 5,755,188원" is not a household's threshold, so a per-head fact must
        # be named. "연간" or "1통" only says how the amount is counted; requiring it dropped
        # every F-6 income row when the question said "2인 가구 소득기준" (2026-10-28).
        if q.get("per") and "당" in q["per"] and re.sub(r"\s+", "", q["per"]) not in re.sub(r"\s+", "", text):
            return False
        return True

    def value(f: Mapping[str, Any]) -> Tuple:
        v = f["value"]
        return _norm_value(v["kind"], v["unit"], float(v["amount"]))

    found = []
    pairs = _role_pairs(answer, lenient=True)
    said_values = {_norm_value(*k) for k, _, _ in pairs}
    for key, roles, clause in pairs:
        families = {ROLE_FAMILY[r] for r in roles} or asked.get(key[0], set())
        if not families:
            continue
        mine = _norm_value(*key)
        same = [f for f in usable if FACT_ROLE_FAMILY[f["role"]] in families and fits(f) and value(f)[:2] == mine[:2]]
        # A row for the named status beats the general row: for an F-6 holder the
        # extension fee is the F-6 row's 3만원, not the general 6만원 (held-out v10 W-07).
        if codes and any(f["subject"].get("status_code") for f in same):
            same = [f for f in same if f["subject"].get("status_code")]
        if not same or any(value(f) == mine for f in same):
            continue
        # The answer also gives the right value somewhere ("1년 이후 2년 이내"; "3년이며,
        # 재고용 시 4년 10개월"): the other row is context, not a mix-up. E4B copies
        # neighbouring rows this way; on held-out v10 three such right answers were marked.
        if any(value(f) in said_values for f in same):
            continue
        elsewhere = [f for f in usable if value(f) == mine and f not in same]
        if elsewhere:
            want = "/".join(sorted({str(int(value(f)[2])) for f in same}))
            found.append(f"{clause.strip()} — 같은 대상·역할의 사실 값은 {want}, 답의 값은 다른 대상·행의 사실({elsewhere[0]['fact_id']})")
    return found


# --- Three checks from the fifteen wrong answers of the real-manual sets (2026-10-28) ---
# Q-11 turned "2회를 초과할 수 없음" into "2회를 초과하여 변경할 수 있습니다"; M-04 moved
# "변경일(사증소지자는 입국일)로부터 6개월" to "활동을 하려는 시점으로부터"; N-02 took its
# papers from p105 and cited p103 and p26.
_COUNTED_RE = re.compile(r"(\d+)\s*(회|번|년|개월|일|시간|주|명|만\s*원|원)")
_ABLE_RE = re.compile(r"([가-힣]{2,}?)(?:하여|해서|하는|하게|할|하|해|될|되|받을|을|를|이|가)?\s*(?:할\s*)?수\s*(있|없)")
_SENTENCE_RE = re.compile(r"(?<=[다음함됨임])[.。]\s*|\n+|(?<=니다)\s+")
#: Words that name when a period starts: "입국일로부터", "변경일(사증소지자는 입국일)로부터".
_START_WORDS = ("입국", "출국", "변경", "신청", "접수", "허가", "발급", "등록", "졸업", "취득", "결정", "납부",
                "확정", "만료", "계약", "활동", "시점", "도착", "채용", "고용", "선고", "집행", "출생", "혼인")
_FROM_RE = re.compile(r"(?:으로|로)?\s*부터\s*(\d+)\s*(개월|년|일)")


def _sentences(text: str) -> List[str]:
    return [s for s in _SENTENCE_RE.split(text or "") if s.strip()]


def polarity_flips(answer: str, trusted_text: str) -> List[str]:
    """Answer sentences that say "…할 수 있다" where the evidence says "…할 수 없다" (or the
    reverse) about the same thing: the same predicate word ("초과") and every counted
    number of the evidence sentence ("3회", "2회") in the answer sentence. Not flagged
    when the evidence also states that predicate the answer's way somewhere."""
    said: Dict[str, set] = {}
    rules = []
    for s in _sentences(trusted_text):
        counted = {(n, re.sub(r"\s+", "", u)) for n, u in _COUNTED_RE.findall(s)}
        for m in _ABLE_RE.finditer(s):
            said.setdefault(m.group(1), set()).add(m.group(2))
            if counted:
                rules.append((m.group(1), m.group(2), counted))
    found = []
    for s in _sentences(answer):
        counted = {(n, re.sub(r"\s+", "", u)) for n, u in _COUNTED_RE.findall(s)}
        for stem, polarity, numbers in rules:
            m = re.search(re.escape(stem) + r"[^.\n]{0,20}?수\s*(있|없)", s)
            if not m or m.group(1) == polarity or m.group(1) in said.get(stem, set()):
                continue
            if numbers <= counted:
                found.append(f"{s.strip()} — 근거는 '{stem} … 수 {polarity}'")
                break
    return found


# Held-out v11 (2026-10-28): polarity_flips caught 0 of 30 flipped answers. Real flips
# rarely repeat the counted number; they lift the limit ("제한 없이", "관계없이", "넘어서도",
# "…더라도 인정됩니다") or claim "가능" where the page says "불가/불허/불인정". This check
# compares an answer sentence with the page sentence closest in content. Review only.
_LIMIT_RE = re.compile(r"수\s*없|불가|불허|불인정|인정하지|아니함|않음|제한|한도|이내|범위\s*내|까지만|만\s*인정|초과할\s*수\s*없")
_LIFT_RE = re.compile(r"제한\s*(?:없이|이\s*없|되지\s*않)|관계\s*없이|상관\s*없이|넘어서도|넘겨서도|넘어\s*(?:한\s*번에\s*)?더"
                      r"|묶이지\s*않|한도\s*없이|그대로\s*인정|계속\s*(?:인정|연장)|(?:더라도|어도|여도|아도)\s*[^.]{0,40}?"
                      r"(?:수\s*있|가능|인정|허용|됩니다)")
_ALLOW_RE = re.compile(r"수\s*있|가능|허용|써도\s*됩|해도\s*됩")
_HARD_NO_RE = re.compile(r"수\s*없|불가|불허|불인정|인정하지|아니함|않음")
_DENY_RE = re.compile(r"없|불가|않|안\s*되|안\s*됩|못|제한됩|불허")
_KEEPS_LIMIT_RE = re.compile(r"이내|까지|범위|한도|만\s|만입|최대|이하로|넘을\s*수\s*없")
_STEM_TAIL_RE = re.compile(r"(?:은|는|이|가|을|를|에|의|로|으로|도|만|까지|부터|에서|이나|이면|하여|해서|하고|합니다|됩니다|입니다)$")


#: Word starts that carry no content ("있습니다", "됩니다", "하지", "중이어도").
_STEM_STOP = {"있습", "있어", "없습", "됩니", "합니", "입니", "하지", "않아", "않습", "중이", "이어", "하여", "해서",
              "경우", "또는", "그리", "이상", "이하", "다만", "또한", "있는", "하는", "되는", "수있"}


def _stems(text: str) -> set:
    out = set()
    for w in re.findall(r"[가-힣]{2,}", text):
        stem = _STEM_TAIL_RE.sub("", w)[:2]
        if len(stem) == 2 and stem not in _STEM_STOP:
            out.add(stem)
    return out


def permission_flips(answer: str, trusted_text: str) -> List[str]:
    lines = [ln for ln in trusted_text.splitlines() if ln.strip()]
    segments = [" ".join(lines[i:i + 2]) for i in range(len(lines))] + _sentences(trusted_text)
    found = []
    for s in _sentences(answer):
        # "41점 이상이어도 … 불인정입니다" keeps the limit: a lift counts only without a "no".
        lifts = bool(_LIFT_RE.search(s)) and not re.search(r"불인정|불허|불가|않습|않아요|안\s*됩|없습니다", s) \
            and not _KEEPS_LIMIT_RE.search(s)
        allows = bool(_ALLOW_RE.search(s)) and not _DENY_RE.search(s) and not _KEEPS_LIMIT_RE.search(s)
        if not (lifts or allows):
            continue
        mine = _stems(s)
        if len(mine) < 3:
            continue
        scored = []
        for seg in segments:
            shared = len(mine & _stems(seg))
            if shared >= 3:
                scored.append((shared / len(mine), seg))
        top = max((sc for sc, _ in scored), default=0.0)
        if top < 0.5:
            continue
        for sc, seg in scored:
            if sc < max(0.5, top - 0.15):
                continue
            # The page grants it somewhere in that passage ("…제한. 단, 결혼이민(F-6)…는 가능"):
            # an exception the answer states is not a flip (20 right answers of recorded runs).
            if re.search(r"가능|허용|할\s*수\s*있|인정(?!하지)", seg):
                continue
            if (lifts and _LIMIT_RE.search(seg)) or (allows and _HARD_NO_RE.search(seg)):
                found.append(f"{s.strip()} — 근거: {seg.strip()[:80]}")
                break
    return found


def _starts_before(text: str) -> Dict[Tuple[str, str], set]:
    out: Dict[Tuple[str, str], set] = {}
    for m in _FROM_RE.finditer(text):
        window = text[max(0, m.start() - 30):m.start()]
        window = window[window.rfind("\n") + 1:] if "\n" in window[-20:] else window
        words = {w for w in _START_WORDS if w in window}
        if words:
            out.setdefault((m.group(1), m.group(2)), set()).update(words)
    return out


def start_point_mismatches(answer: str, trusted_text: str) -> List[str]:
    """A period the answer counts from a start ("…시점으로부터 6개월") that the evidence
    never uses for that period, while the evidence names another start for it."""
    evidence = _starts_before(trusted_text)
    found = []
    for value, words in _starts_before(answer).items():
        if value in evidence and not words & evidence[value]:
            found.append(f"{value[0]}{value[1]}의 기산점 {'/'.join(sorted(words))} — 근거의 기산점 {'/'.join(sorted(evidence[value]))}")
    return found


def missing_citations(answer: str, trusted: Sequence[Mapping[str, Any]], cited: Sequence[str]) -> List[str]:
    """Trusted pages that alone support a claim of the answer (a paper, an amount, a
    period) while no cited page does: they belong in the citations."""
    pages = [(e["id"], unicodedata.normalize("NFC", f"{e['title']}\n{e['text']}")) for e in trusted]
    page_claims = {pid: extract_claims(text) for pid, text in pages}
    add: List[str] = []
    for claim in extract_claims(answer):
        backers = [pid for pid, text in pages if _supported(claim, page_claims[pid], text)]
        if backers and not set(backers) & set(cited) and backers[0] not in add:
            add.append(backers[0])
    return add


def post_check(parsed: Optional[Mapping[str, Any]], trusted: Sequence[Mapping[str, Any]],
               facts: Optional[Sequence[Mapping[str, Any]]] = None, question: str = "") -> Dict[str, Any]:
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
    final = dict(parsed)
    page_facts = [f for f in (facts or []) if f["source"]["page_id"] in trusted_ids]
    fact_families: Dict[Tuple, set] = {}
    for f in page_facts:
        if f.get("role") in FACT_ROLE_FAMILY:
            v = f["value"]
            fact_families.setdefault(_norm_value(v["kind"], v["unit"], float(v["amount"])), set()).add(FACT_ROLE_FAMILY[f["role"]])
    flips = polarity_flips(answer, trusted_text)
    if flips:
        # "할 수 없다" turned into "할 수 있다" about the same counted rule is a harmful
        # answer, not a style question: withheld like an unsupported value.
        return {"verdict": "withheld", "claims": found, "unsupported": [], "untrusted_citations": [],
                "polarity_flips": flips, "final": {**abstain, "answer": WITHHELD_ANSWER}}
    added = missing_citations(answer, trusted, [str(c) for c in citations])
    if added:
        final["citations"] = list(citations) + added
    roles = role_mismatches(answer, trusted_text, fact_families)
    subjects = subject_mismatches(answer, question, page_facts)
    starts = start_point_mismatches(answer, trusted_text)
    lifted = permission_flips(answer, trusted_text)
    flags = [f"role_mismatch: {r}" for r in roles] + [f"subject_mismatch: {m}" for m in subjects] + \
        [f"start_point_mismatch: {s}" for s in starts] + [f"permission_flip: {p}" for p in lifted]
    if flags:
        final["review_flags"] = flags
    return {"verdict": "pass", "claims": found, "unsupported": [], "untrusted_citations": [],
            "role_mismatches": roles, "subject_mismatches": subjects, "start_point_mismatches": starts,
            "permission_flips": lifted,
            "citations_added": added, "final": final}
