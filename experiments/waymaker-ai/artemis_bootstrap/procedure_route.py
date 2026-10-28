"""Stage 2 routing: decide which manual a question's procedure belongs to, before evidence is chosen.

Why: on the first real-manual run (2026-10-26) E4B answered a 체류자격 변경
question from 사증발급 pages and a 사증발급인정서 question with stay-manual
documents. Mixing the two procedures is a hard rule of this repository, so the
fix is not a prompt: pages from the other manual never reach the model.

The decision is the backend's own (``backend/services/manual_evidence.py``,
imported read-only): ``procedure_scopes`` for 사증발급 wording, 재입국 and a
detected stay task, plus ``_stay_procedure_named`` for stay procedures named in
the question (체류기간, 연장허가, 체류자격 변경, 외국인등록, 근무처 …). The
backend passes a task type detected elsewhere; this experiment has none, so a
named stay procedure stands in for it. A question that names no procedure gets
no manual at all — the backend's "no manual basis" state — and the model sees
no evidence. That over-abstains on implicit wording ("한국에 더 있으려면") and is
measured as such.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))
from services import manual_evidence as _me  # noqa: E402

SCOPE_STAY = _me.SCOPE_STAY      # "stay" — equal to the corpus domain
SCOPE_VISA = _me.SCOPE_VISA      # "visa_issuance"
_CODE_RE = re.compile(r"(?<![A-Za-z0-9])[A-H]\s?-?\s?\d{1,2}", re.IGNORECASE)


# Where the person is (2026-10-28, from the fifteen wrong answers of the real-manual
# sets): "베트남에 살고 있는데 … D-4로 가면 체류기간은" went to the stay manual on the word
# 체류기간 alone, "I'd like to come to Korea as a digital nomad (F-1-D) … what kind of
# visa" on a status code plus "work", and "I came to Korea visa-free … so I can stay"
# went nowhere. These cues live here, in the experiment, not in the backend detector.
_ABROAD_RE = re.compile(
    r"(?<!한국)(?<!국내)(?<!서울)에\s*살고\s*있|해외에\s*(?:있|살)|본국에\s*(?:있|살)"
    r"|한국(?:에|으로)\s*(?:가|오|들어가|들어오)(?:려|고\s*싶|면|게\s*되)"
    r"|\b(?:come|coming|move|moving)\s+to\s+Korea\b|\boverseas\b|\babroad\b",
    re.IGNORECASE)
_IN_KOREA_RE = re.compile(
    # "한국에 있는 교회" is about the church, not the person: only "있어요/있는데/있고…".
    r"(?:한국|국내)에\s*(?:있(?:어|습|는데|고|으)|살고|와\s*있|체류\s*(?:중|하고))|들어와\s*있|입국해서"
    r"|\bI\s+came\s+to\s+Korea\b|\b(?:I'm|I am|we're|we are)\s+(?:in|living in|staying in)\s+Korea\b"
    r"|\balready in Korea\b|\bin Korea now\b",
    re.IGNORECASE)
#: Stay routes taken from words that a visa question uses too.
_WEAK_STAY = {"활동범위", "체류 절차(질문에 명시)"}
_STAY_PERIOD_WORD_RE = re.compile(r"체류\s*기간", re.IGNORECASE)


def _location(question: str) -> str:
    abroad, korea = bool(_ABROAD_RE.search(question or "")), bool(_IN_KOREA_RE.search(question or ""))
    return "abroad" if abroad and not korea else "korea" if korea and not abroad else ""


def route(question: str) -> List[Tuple[str, str]]:
    """``[(domain, procedure_label), ...]``; empty when the question names no procedure."""
    has_code = bool(_CODE_RE.search(question or ""))
    scopes = list(_me.procedure_scopes(question, None, has_code))
    if _me._stay_procedure_named(question) and not any(s[0] == SCOPE_STAY for s in scopes):
        scopes.append((SCOPE_STAY, "체류 절차(질문에 명시)"))
    where = _location(question)
    # A stay route resting only on "체류기간" or on a code plus a work word, for someone
    # who says they live abroad or are coming to Korea, is a visa question.
    named = {m.group(0) for m in _me._STAY_NAMED_RE.finditer(question or "")}
    weak = scopes and all(d == SCOPE_STAY and label in _WEAK_STAY for d, label in scopes) \
        and all(_STAY_PERIOD_WORD_RE.fullmatch(n) for n in named)
    if where == "abroad" and weak:
        return [(SCOPE_VISA, "해외 거주(질문에 명시)")]
    if not scopes and where == "abroad":
        return [(SCOPE_VISA, "해외 거주(질문에 명시)")]
    if not scopes and where == "korea":
        return [(SCOPE_STAY, "국내 체류(질문에 명시)")]
    return scopes


def route_gate(case: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str], List[Tuple[str, str]]]:
    """The case with only evidence from the routed manual(s), the ids withheld, and the route."""
    scopes = route(case["question"])
    domains = {d for d, _ in scopes}
    kept = [e for e in case["evidence"] if (e.get("source") or {}).get("domain") in domains]
    withheld = [e["id"] for e in case["evidence"] if e not in kept]
    return {**case, "evidence": kept}, withheld, scopes


# --- clarify -----------------------------------------------------------------
# Measured on held-out routing cases (2026-10-26): an empty route withheld every
# page and 5 of 24 questions were abstained on silently. A question that names
# no procedure now gets one fixed question back instead (the "clarify" mode of
# the Mission 002 answer contract). The user's reply is appended and routed
# again; the model never sees pages before a route exists.

CLARIFY_ANSWER = (
    "어떤 절차를 물으시는지 먼저 확인할게요. 아래에서 골라 주세요. "
    "'해외에서 비자 받기'는 해외에서 사증(비자)이나 사증발급인정서를 새로 받는 경우이고, "
    "'한국에서 체류 절차'는 한국에 있으면서 체류기간 연장·체류자격 변경·외국인등록·재입국허가·근무처 변경을 하는 경우입니다."
)


#: Two buttons instead of a free-text reply (2026-10-26): on held-out clarify
#: cases the backend detector could not route 4 of 10 natural replies ("사증을
#: 새로 받으려는 거예요", "I need to apply for …"). A pressed button names the
#: manual exactly, so the second turn needs no text understanding at all.
CLARIFY_CHOICES: Dict[str, Tuple[str, str]] = {
    "visa_abroad": (SCOPE_VISA, "해외에서 비자 받기"),
    "stay_in_korea": (SCOPE_STAY, "한국에서 체류 절차"),
}


def clarify_output() -> Dict[str, Any]:
    return {
        "status": "clarify", "answer": CLARIFY_ANSWER, "citations": [],
        "choices": [{"id": k, "label": label} for k, (_, label) in CLARIFY_CHOICES.items()],
    }


def route_choice(choice: str) -> List[Tuple[str, str]]:
    """The route a pressed button stands for; an unknown id routes nowhere."""
    return [CLARIFY_CHOICES[choice]] if choice in CLARIFY_CHOICES else []


def gate_to(case: Mapping[str, Any], scopes: List[Tuple[str, str]]) -> Tuple[Dict[str, Any], List[str]]:
    """Keep only evidence from the given route's manual(s)."""
    domains = {d for d, _ in scopes}
    kept = [e for e in case["evidence"] if (e.get("source") or {}).get("domain") in domains]
    return {**case, "evidence": kept}, [e["id"] for e in case["evidence"] if e not in kept]


def with_reply(question: str, reply: str) -> str:
    """The question as routed and shown to the model after the user answers the clarifying question."""
    return f"{question}\n(확인 질문에 대한 답) {reply}"


# --- mis-click guards ----------------------------------------------------------
# Measured 2026-10-26: with the two buttons always shown, the one harmful answer
# was a user's own mis-click (in Korea, pressed "해외에서 비자 받기"). Two guards:
# the detector cross-checks the pressed button and asks once when it confidently
# disagrees, and every answer names the manual it came from with a one-tap switch.

def other_choice(choice: str) -> str:
    return next(k for k in CLARIFY_CHOICES if k != choice)


def cross_check(question: str, choice: str) -> Dict[str, Any]:
    """``{"disagrees": bool, ...}``: True only when the detector routes the question to
    exactly one manual and it is not the pressed button's. An empty or two-manual
    route never overrides the user."""
    detected = {d for d, _ in route(question)}
    pressed = CLARIFY_CHOICES[choice][0]
    return {"detected": sorted(detected), "pressed": pressed,
            "disagrees": len(detected) == 1 and pressed not in detected}


def confirm_output(choice: str) -> Dict[str, Any]:
    """Asked once when the cross-check disagrees with the pressed button."""
    pressed, other = CLARIFY_CHOICES[choice][1], CLARIFY_CHOICES[other_choice(choice)][1]
    return {
        "status": "clarify",
        "answer": f"'{pressed}'를 고르셨는데, 질문 내용은 '{other}'에 더 가까워 보여요. 어느 쪽으로 안내할까요?",
        "citations": [],
        "choices": [{"id": k, "label": label} for k, (_, label) in CLARIFY_CHOICES.items()],
    }


def label_answer(output: Mapping[str, Any], choice: str) -> Dict[str, Any]:
    """The answer with the manual it came from and a one-tap switch to the other button."""
    other = other_choice(choice)
    return {**output,
            "basis": {"id": choice, "label": f"{CLARIFY_CHOICES[choice][1]} 기준 안내"},
            "switch": {"id": other, "label": f"'{CLARIFY_CHOICES[other][1]}'로 다시 보기"}}
