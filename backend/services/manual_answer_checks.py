"""Review flags for a generated answer against the manual excerpts it was given.

Two checks from experiments/waymaker-ai/artemis_bootstrap (trust_gate.py), each
measured on held-out sets written by agents that never saw the code:

* start point: the answer counts a period from a start the excerpt never uses for it
  ("활동을 하려는 시점으로부터 6개월" where the manual says "변경일(사증소지자는 입국일)로부터
  6개월"). Held-out v11: 21 of 30 wrong start points marked; no right answer newly marked.
* permission flip: the answer lifts a limit or allows what the closest excerpt passage
  forbids ("제한 없이 받을 수 있습니다" where the manual says "할 수 없음"), unless that
  passage also grants it. Held-out v12: 9 of 60 flips caught, v13: 11 of 60; no right
  answer marked. Most flips are not caught: this is a review signal, not a guarantee.

Both only add flags to the response metadata. They never change, block or withhold an
answer. Deterministic; no model call. Not a legal judgement.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple

_SENTENCE_RE = re.compile(r"(?<=[다음함됨임])[.。]\s*|\n+|(?<=니다)\s+")
#: Words that name when a period starts: "입국일로부터", "변경일(사증소지자는 입국일)로부터".
_START_WORDS = ("입국", "출국", "변경", "신청", "접수", "허가", "발급", "등록", "졸업", "취득", "결정", "납부",
                "확정", "만료", "계약", "활동", "시점", "도착", "채용", "고용", "선고", "집행", "출생", "혼인")
_FROM_RE = re.compile(r"(?:으로|로)?\s*부터\s*(\d+)\s*(개월|년|일)")


def _sentences(text: str) -> List[str]:
    return [s for s in _SENTENCE_RE.split(text or "") if s.strip()]



# Permission flips. Flips rarely repeat the manual's number; they lift the limit
# ("제한 없이", "관계없이", "넘어서도", "…더라도 인정됩니다") or claim "가능" where the manual
# says "불가/불허/불인정". An answer sentence is compared with the excerpt passage
# closest in content.
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
            # an exception the answer states is not a flip (without this, 20 right answers of
            # the experiment's recorded runs were marked).
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

def review(answer: str, excerpts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """``{"checked", "flags"}`` for one answer and the manual excerpts behind it. Each flag
    is ``{"kind": "start_point" | "permission_flip", "detail": str}``."""
    texts = [str(ex.get("text") or "") for ex in excerpts or [] if ex.get("text")]
    if not answer or not texts:
        return {"checked": False, "flags": []}
    evidence = "\n".join(texts)
    flags = [{"kind": "start_point", "detail": d} for d in start_point_mismatches(answer, evidence)]
    flags += [{"kind": "permission_flip", "detail": d} for d in permission_flips(answer, evidence)]
    return {"checked": True, "flags": flags}
