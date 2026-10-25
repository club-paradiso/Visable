"""Lossless explicit immigration status tokens and directional transitions.

Syntax recognition does not certify a status or its document requirements.
"""
from __future__ import annotations

import re
from typing import Optional

_SUFFIX = r"(?:[0-9]{1,3}[A-Z]?|[A-Z][0-9]?)"
CODE_TOKEN = rf"[A-HKM](?:-)?\d{{1,2}}(?:-{_SUFFIX})?"
CODE_RE = re.compile(rf"(?<![A-Za-z0-9])({CODE_TOKEN})(?![A-Za-z0-9-])", re.I)
PAIR_RE = re.compile(
    rf"({CODE_TOKEN})\s*(?:에서|부터|→|->|\bto\b|\binto\b|转为|轉為|变更为|変更為|から|\bsang\b|\bна\b|\bв\b)\s*({CODE_TOKEN})",
    re.I,
)


def normalize_explicit(code: str) -> Optional[str]:
    raw = str(code or "").strip().upper()
    if not CODE_RE.fullmatch(raw):
        return None
    match = re.fullmatch(rf"([A-HKM])-?(\d{{1,2}})(?:-({_SUFFIX}))?", raw)
    if not match:
        return None
    # A hyphen fixes the parent segment, including two-digit parents.
    return f"{match.group(1)}-{int(match.group(2))}" + (f"-{match.group(3)}" if match.group(3) else "")


def explicit_codes(text: str) -> list[str]:
    codes: list[str] = []
    for match in CODE_RE.finditer(text or ""):
        code = normalize_explicit(match.group(1))
        if code and code not in codes:
            codes.append(code)
    return codes


def transition_pair(text: str) -> Optional[tuple[str, str]]:
    match = PAIR_RE.search(text or "")
    if match:
        return normalize_explicit(match.group(1)), normalize_explicit(match.group(2))
    codes = explicit_codes(text)
    if len(codes) == 2 and re.search(r"체류자격\s*(?:변경|전환)|change\s+(?:of\s+)?status|switch\s+(?:my\s+)?visa|签证.*(?:换成|改为)|在留資格.*(?:変更|切替)|đổi.*(?:sang|thành)|сменить.*(?:на|статус)", text or "", re.I):
        return codes[0], codes[1]
    return None


def supplemental_task(text: str) -> Optional[str]:
    raw = text or ""
    if re.search(r"사증발급인정서|visa\s+issuance\s+confirmation|certificate\s+for\s+visa\s+issuance|签证签发认定书|査証発給認定書", raw, re.I):
        return "visa_issuance_confirmation"
    if re.search(r"전자사증|전자비자|e-?visa|electronic\s+visa|电子签证|電子査証", raw, re.I):
        return "visa_issuance"
    if re.search(r"재입국(?:허가|신청)?|re-?entry(?:\s+permit)?|再入境|再入国|tái nhập cảnh|повторн(?:ый|ого)\s+въезд", raw, re.I):
        return "reentry"
    if re.search(r"사증\s*(?:발급|신청)|비자\s*발급|visa\s+(?:issuance|application|issue)|签证签发|査証発給", raw, re.I):
        return "visa_issuance"
    if transition_pair(raw) or re.search(r"签证.*(?:换成|改为)|在留資格.*(?:変更|切替)|đổi.*(?:sang|thành)|сменить.*(?:на|статус)", raw, re.I):
        return "status_change"
    return None
