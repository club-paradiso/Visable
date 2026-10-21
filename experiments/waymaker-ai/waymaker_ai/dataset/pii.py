"""Personal-data screen for dataset examples.

Why: benchmark and training examples must never carry a real person's data.
Waymaker's users are foreign residents, so the identifiers that matter are the
ones an immigration question attracts: 외국인등록번호 and 주민등록번호, passport
numbers, Korean mobile numbers and e-mail addresses. A labelled example that
leaks one of them would travel into every model trained or evaluated on it.

The screen is deliberately conservative and dumb:

* It reports a *kind* and a position, never the matched value, so a report or
  CI log cannot itself become the leak. ``redact`` applies the same scan to
  report text (ids, paths, messages) that echoes an example's own keys.
* Text is NFKC-normalized before scanning, so full-width digits ("９００１０１")
  and a full-width at sign cannot slip past. Positions refer to the normalized
  text.
* Any registration-number shape is flagged, citizen or foreigner. The 7th
  digit (5-8 for foreigners) only decides the label.

  - ``######-#######`` (hyphen or dash between the halves) is always flagged.
    Nothing a legal dataset legitimately carries is written that way.
  - Thirteen bare digits, or the two halves separated only by a space, are
    flagged when the first six digits read as a birth date (YYMMDD with month
    01-12 and day 01-31). Without that check every 행정규칙일련번호 such as
    ``2100000275060`` (version ids and law.go.kr ``admRulSeq`` URLs) would be
    reported, and those ids carry month ``00``.
* A passport number is only recognisable by context, so passport-like tokens
  are flagged when a passport word appears close by.

False positives are acceptable (the author rewrites the example); false
negatives are not. The scanners are small functions over tokens rather than one
large regular expression, so each rule can be read and tested on its own.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterator, List, Optional, Tuple

RESIDENT_REGISTRATION_NUMBER = "resident_registration_number"
ALIEN_REGISTRATION_NUMBER = "alien_registration_number"
PASSPORT_NUMBER = "passport_number"
MOBILE_NUMBER = "mobile_number"
EMAIL_ADDRESS = "email_address"

PII_KINDS: Tuple[str, ...] = (
    RESIDENT_REGISTRATION_NUMBER,
    ALIEN_REGISTRATION_NUMBER,
    PASSPORT_NUMBER,
    MOBILE_NUMBER,
    EMAIL_ADDRESS,
)

#: Words that put a nearby token in passport context (casefolded).
PASSPORT_CONTEXT_WORDS: Tuple[str, ...] = ("여권", "passport", "护照", "護照", "旅券", "パスポート")

#: How far (in characters) a passport word may sit from the token.
PASSPORT_CONTEXT_WINDOW = 30

#: Hex tokens at least this long are hashes (sha256 = 64), not identifiers.
_HASH_TOKEN_MIN_LENGTH = 32

#: Separators accepted between the 6-digit and 7-digit halves of a
#: registration number (after NFKC, so the full-width hyphen is already "-").
_REGISTRATION_SEPARATORS = frozenset({"-", "‐", "‑", "‒", "–", "—"})

#: Longest gap (dash plus surrounding spaces) accepted between the two halves.
_MAX_SEPARATOR_LENGTH = 3

_MOBILE_NUMBER = re.compile(
    r"""
    (?<![0-9])            # not the tail of a longer number
    (?:\+82[\s.-]?|0)     # country code, or the domestic trunk prefix
    1[016789]             # mobile prefixes 010, 011, 016-019
    [\s.-]?[0-9]{3,4}     # exchange
    [\s.-]?[0-9]{4}       # subscriber
    (?![0-9])             # not the head of a longer number
    """,
    re.VERBOSE,
)

_EMAIL_ADDRESS = re.compile(
    r"""
    [A-Za-z0-9._%+-]+     # local part
    @
    [A-Za-z0-9-]+         # first domain label
    (?:\.[A-Za-z0-9-]+)*  # further labels
    \.[A-Za-z]{2,}        # top-level domain
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class PiiFinding:
    kind: str
    start: int   # offsets in the NFKC-normalized text
    end: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def scan_text(text: str) -> List[PiiFinding]:
    """Every personal-data finding in ``text``, ordered by position."""
    normalized = unicodedata.normalize("NFKC", text or "")
    findings = (
        find_registration_numbers(normalized)
        + find_passport_numbers(normalized)
        + find_mobile_numbers(normalized)
        + find_email_addresses(normalized)
    )
    return sorted(set(findings), key=lambda f: (f.start, f.end, f.kind))


def scan_value(value: Any, path: str = "") -> List[Tuple[str, PiiFinding]]:
    """Scan every string (keys included) inside a JSON value; return (path, finding) pairs."""
    results: List[Tuple[str, PiiFinding]] = []
    for where, text in iter_strings(value, path):
        results.extend((where, finding) for finding in scan_text(text))
    return results


def describe(finding: PiiFinding) -> str:
    """A report line that names the kind and position but never the value."""
    return f"{finding.kind} at characters {finding.start}-{finding.end} (value withheld)"


REDACTED = "<withheld>"


def redact(text: str) -> str:
    """``text`` with every finding replaced by ``REDACTED``; unchanged when nothing is found.

    For report strings (paths, ids, messages) that may echo an example's own
    keys or values. The result is NFKC-normalized only when something was
    redacted, because finding offsets refer to the normalized text.
    """
    findings = scan_text(text)
    if not findings:
        return text
    normalized = unicodedata.normalize("NFKC", text or "")
    parts: List[str] = []
    position = 0
    for start, end in _merged_spans(findings):
        parts.append(normalized[position:start])
        parts.append(REDACTED)
        position = end
    parts.append(normalized[position:])
    return "".join(parts)


def _merged_spans(findings: List[PiiFinding]) -> List[Tuple[int, int]]:
    """Finding spans with overlaps joined (a mobile number inside a passport window, say)."""
    spans: List[Tuple[int, int]] = []
    for finding in findings:   # scan_text sorts by start
        if spans and finding.start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], finding.end))
        else:
            spans.append((finding.start, finding.end))
    return spans


def iter_strings(value: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    """Yield (path, string) for every string value and object key, depth first, sorted keys."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key in sorted(value, key=str):
            child = f"{path}.{key}" if path else str(key)
            yield f"{child}(key)", str(key)
            yield from iter_strings(value[key], child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Registration numbers (주민등록번호 / 외국인등록번호)
# ---------------------------------------------------------------------------
def find_registration_numbers(text: str) -> List[PiiFinding]:
    findings: List[PiiFinding] = []
    runs = _digit_runs(text)
    for index, (start, end) in enumerate(runs):
        if _inside_hash_token(text, start, end):
            continue
        length = end - start
        if length == 13:
            if _reads_as_birth_date(text[start:start + 6]):
                findings.append(PiiFinding(_registration_kind(text[start + 6]), start, end))
            continue
        if length != 6 or index + 1 >= len(runs):
            continue
        next_start, next_end = runs[index + 1]
        if next_end - next_start != 7 or _inside_hash_token(text, next_start, next_end):
            continue
        if _joins_registration_halves(text[end:next_start], text[start:end]):
            findings.append(PiiFinding(_registration_kind(text[next_start]), start, next_end))
    return findings


def _joins_registration_halves(separator: str, first_half: str) -> bool:
    """A dash always joins the halves; a bare space only when the first half reads as a birth date."""
    if len(separator) > _MAX_SEPARATOR_LENGTH:
        return False
    stripped = separator.strip()
    if stripped in _REGISTRATION_SEPARATORS:
        return True
    return stripped == "" and _reads_as_birth_date(first_half)


def _reads_as_birth_date(six_digits: str) -> bool:
    """YYMMDD with a month 01-12 and a day 01-31 (no calendar check: the shape is what matters)."""
    month, day = int(six_digits[2:4]), int(six_digits[4:6])
    return 1 <= month <= 12 and 1 <= day <= 31


def _registration_kind(seventh_digit: str) -> str:
    """Digits 5-8 in the 7th position mark a foreigner's registration number."""
    return ALIEN_REGISTRATION_NUMBER if seventh_digit in "5678" else RESIDENT_REGISTRATION_NUMBER


# ---------------------------------------------------------------------------
# Passport numbers (context dependent)
# ---------------------------------------------------------------------------
def find_passport_numbers(text: str) -> List[PiiFinding]:
    folded = text.casefold()
    findings: List[PiiFinding] = []
    for start, end in _ascii_alnum_runs(text):
        if _looks_like_passport_number(text[start:end]) and _near_passport_word(folded, start, end):
            findings.append(PiiFinding(PASSPORT_NUMBER, start, end))
    return findings


def _looks_like_passport_number(token: str) -> bool:
    """Letter-led tokens with 6+ digits (M12345678, M123A4567), or 9 bare digits."""
    digits = sum(ch.isdigit() for ch in token)
    if token.isdigit():
        return len(token) == 9
    return 7 <= len(token) <= 10 and token[0].isalpha() and digits >= 6


def _near_passport_word(folded: str, start: int, end: int) -> bool:
    window = folded[max(0, start - PASSPORT_CONTEXT_WINDOW): end + PASSPORT_CONTEXT_WINDOW]
    return any(word in window for word in PASSPORT_CONTEXT_WORDS)


# ---------------------------------------------------------------------------
# Mobile numbers and e-mail addresses
# ---------------------------------------------------------------------------
def find_mobile_numbers(text: str) -> List[PiiFinding]:
    return [PiiFinding(MOBILE_NUMBER, m.start(), m.end()) for m in _MOBILE_NUMBER.finditer(text)]


def find_email_addresses(text: str) -> List[PiiFinding]:
    return [PiiFinding(EMAIL_ADDRESS, m.start(), m.end()) for m in _EMAIL_ADDRESS.finditer(text)]


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
def _is_ascii_digit(ch: str) -> bool:
    return "0" <= ch <= "9"


def _is_ascii_alnum(ch: str) -> bool:
    return _is_ascii_digit(ch) or "a" <= ch <= "z" or "A" <= ch <= "Z"


def _runs(text: str, predicate) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start: Optional[int] = None
    for position, ch in enumerate(text):
        if predicate(ch):
            if start is None:
                start = position
        elif start is not None:
            runs.append((start, position))
            start = None
    if start is not None:
        runs.append((start, len(text)))
    return runs


def _digit_runs(text: str) -> List[Tuple[int, int]]:
    return _runs(text, _is_ascii_digit)


def _ascii_alnum_runs(text: str) -> List[Tuple[int, int]]:
    return _runs(text, _is_ascii_alnum)


def _inside_hash_token(text: str, start: int, end: int) -> bool:
    """True when the digits sit inside a long hex token such as a sha256 digest."""
    left = start
    while left > 0 and _is_ascii_alnum(text[left - 1]):
        left -= 1
    right = end
    while right < len(text) and _is_ascii_alnum(text[right]):
        right += 1
    token = text[left:right]
    return len(token) >= _HASH_TOKEN_MIN_LENGTH and all(ch in "0123456789abcdefABCDEF" for ch in token)
