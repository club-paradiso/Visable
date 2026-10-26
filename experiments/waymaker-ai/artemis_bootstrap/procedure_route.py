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


def route(question: str) -> List[Tuple[str, str]]:
    """``[(domain, procedure_label), ...]``; empty when the question names no procedure."""
    has_code = bool(_CODE_RE.search(question or ""))
    scopes = list(_me.procedure_scopes(question, None, has_code))
    if _me._stay_procedure_named(question) and not any(s[0] == SCOPE_STAY for s in scopes):
        scopes.append((SCOPE_STAY, "체류 절차(질문에 명시)"))
    return scopes


def route_gate(case: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str], List[Tuple[str, str]]]:
    """The case with only evidence from the routed manual(s), the ids withheld, and the route."""
    scopes = route(case["question"])
    domains = {d for d, _ in scopes}
    kept = [e for e in case["evidence"] if (e.get("source") or {}).get("domain") in domains]
    withheld = [e["id"] for e in case["evidence"] if e not in kept]
    return {**case, "evidence": kept}, withheld, scopes
