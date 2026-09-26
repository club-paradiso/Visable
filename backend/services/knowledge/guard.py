"""Answer Guard: deterministic post-generation checks.

Runs on model text BEFORE it reaches the user. Nothing here asks a model
whether the model was right.

Severity policy
---------------
critical  the generated text is not shown. The caller falls back to the
          deterministic answer (structured facts) or to limited guidance.
high      for deterministic-fact answers the model text is dropped (the
          structured facts remain); for free-form answers it is recorded.
medium / low
          recorded for the operator (quality signal), text is shown.

Facts stay on the data side: the guard compares the text against the
verified facts it was given, it never edits the facts to match the text.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from services.deploy_paths import repo_path
from services.structured_answer import contains_internal_metadata

_REPO_ROOT = Path(__file__).resolve().parents[3]

CRITICAL, HIGH, MEDIUM, LOW = "critical", "high", "medium", "low"

_PROVIDER_RE = re.compile(
    r"openrouter|groq|ollama|nemotron|gemma|nvidia|\bnim\b|llama[\s-]?\d|gpt-?\d|chatgpt|openai|anthropic|"
    r"\bclaude\b|deepseek|qwen|moonshot|kimi|mistral|gemini|inkling|thinkingmachines",
    re.IGNORECASE,
)
_KNOWLEDGE_INTERNAL_RE = re.compile(
    r"fact_id|lineage_id|slot_key|variant_key|proposal_hash|coverage_state|review_state|lifecycle_state|"
    r"retrieval[\s_]confidence|vector\s+distance|conflict_id|eval_(?:case|id)|kf_[0-9a-f]{8}",
    re.IGNORECASE,
)
_UNSAFE_HTML_RE = re.compile(r"<\s*(?:script|iframe|object|embed|style|form|img|svg)\b|javascript:|\bon[a-z]+\s*=\s*[\"']",
                             re.IGNORECASE)
_CERTAINTY_RE = re.compile(
    r"100\s*%|무조건|반드시\s*(?:허가|승인)|확실(?:히|하게)\s*(?:허가|승인)|허가가\s*보장|승인이\s*보장|보장됩니다|"
    r"틀림없이|절대\s*(?:거절|불허)되지|guarantee[sd]?|definitely\s+(?:be\s+)?(?:approved|granted)|"
    r"will\s+(?:certainly|definitely)\s+be|certain(?:ly)?\s+to\s+be\s+approved|no\s+risk",
    re.IGNORECASE,
)
_OFFICIAL_CONFIRMATION_RE = re.compile(
    r"(?:출입국|법무부|관서|하이코리아)(?:에서|이|가)?\s*(?:공식(?:적으로)?\s*)?확인(?:해\s*주었|했|받았|되었)|"
    r"공식\s*확인(?:을\s*)?(?:받|거쳤|완료)|officially\s+confirmed|verified\s+(?:by|with)\s+(?:the\s+)?immigration|"
    r"confirmed\s+(?:by|with)\s+(?:the\s+)?(?:immigration|ministry|hikorea)",
    re.IGNORECASE,
)
_STATUS_CODE_RE = re.compile(r"(?<![A-Z0-9])([A-HKM]-\d{1,2})(?:-[0-9A-Z]{1,3})?(?![A-Z0-9])")
_PAGE_RE = re.compile(r"(?:pp?\.\s*|페이지\s*|쪽\s*)(\d{1,4})|(\d{1,4})\s*(?:쪽|페이지)")
_VISA_PROCEDURE_RE = re.compile(r"사증발급인정서|사증\s*발급\s*신청|visa\s+issuance\s+confirmation|재외공관.*사증", re.I)
_UNIVERSAL_RE = re.compile(r"모든\s*신청자|누구나|반드시|항상|예외\s*없이|all\s+applicants|always|must\s+(?:all|always)", re.I)
_CONDITION_MARKER_RE = re.compile(r"해당|경우|만\s|에\s*한|조건|if\b|only|when|where applicable", re.I)
_HANGUL_RE = re.compile(r"[가-힣]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_WS_RE = re.compile(r"\s+")


@dataclass
class GuardFinding:
    check: str
    severity: str
    detail: str = ""


@dataclass
class GuardResult:
    findings: List[GuardFinding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(f.severity == CRITICAL for f in self.findings)

    @property
    def high(self) -> bool:
        return any(f.severity in (CRITICAL, HIGH) for f in self.findings)

    @property
    def outcome(self) -> str:
        if self.blocked:
            return "blocked"
        if self.high:
            return "high_findings"
        return "passed_with_notes" if self.findings else "passed"

    def to_dict(self) -> Dict[str, Any]:
        return {"outcome": self.outcome, "findings": [asdict(f) for f in self.findings]}


LEAK_CHECKS = frozenset({"provider_model_leak", "internal_metadata_leak"})


def scrub_leaks(text: str) -> str:
    """Drop the lines that name a provider/model or internal machinery.

    Mirrors ``structured_answer.scrub_internal_metadata``: remove the leaking
    line, keep the rest of the answer untouched.
    """
    kept = [line for line in str(text or "").split("\n")
            if not (_PROVIDER_RE.search(line) or _KNOWLEDGE_INTERNAL_RE.search(line)
                    or contains_internal_metadata(line))]
    return "\n".join(kept).strip()


def _norm(text: str) -> str:
    return _WS_RE.sub("", str(text or "")).lower()


@lru_cache(maxsize=1)
def document_vocabulary() -> tuple:
    """Official document names Waymaker knows (doc_master.json)."""
    try:
        data = json.loads(repo_path("doc_master.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return tuple()
    names = []
    for entry in data:
        name = str(entry.get("ko_name") or "").strip()
        base = re.sub(r"\([^)]*\)", "", name).strip()
        if 3 <= len(base) <= 16 and base not in names:
            names.append(base)
    return tuple(names)


def check(
    text: str,
    *,
    language: str = "ko",
    verified_facts: Sequence[Dict[str, Any]] = (),
    coverage_state: str = "",
    status_code: Optional[str] = None,
    user_mentioned_statuses: Iterable[str] = (),
    procedure_family: Optional[str] = "stay",
    cited_pages: Iterable[int] = (),
    summary_only: bool = True,
) -> GuardResult:
    """Evaluate generated ``text`` against the verified evidence boundary.

    ``summary_only``: the model text is a short lead (structured document
    answers) — the omission check is skipped because the facts render
    deterministically next to it.
    """
    result = GuardResult()
    add = result.findings.append
    body = str(text or "")
    if not body.strip():
        return result

    # --- leaks / unsafe rendering (always critical) -----------------------
    if _PROVIDER_RE.search(body):
        add(GuardFinding("provider_model_leak", CRITICAL, _PROVIDER_RE.search(body).group(0)))
    if contains_internal_metadata(body) or _KNOWLEDGE_INTERNAL_RE.search(body):
        add(GuardFinding("internal_metadata_leak", CRITICAL))
    if _UNSAFE_HTML_RE.search(body):
        add(GuardFinding("unsafe_html", CRITICAL))

    verified = [f for f in verified_facts if f.get("property") == "required_document"]
    verified_norm = [_norm(f.get("value_text")) for f in verified]

    # --- unsupported factual claims (document membership) ----------------
    if verified:
        body_norm = _norm(body)
        for name in document_vocabulary():
            n = _norm(name)
            if n in body_norm and not any(n in v or v.split("(")[0] in n for v in verified_norm):
                add(GuardFinding("unsupported_document", CRITICAL, name))
        # Conditional fact promoted to unconditional.
        for fact in verified:
            if fact.get("condition_kind") == "always":
                continue
            label = re.split(r"[(,（]", str(fact.get("value_text") or ""))[0].strip()
            if len(label) < 3:
                continue
            for sentence in re.split(r"(?<=[.!?。])\s+|\n", body):
                if label in sentence and _UNIVERSAL_RE.search(sentence) and not _CONDITION_MARKER_RE.search(sentence):
                    add(GuardFinding("conditional_promoted_to_universal", HIGH, label))
                    break
        if not summary_only:
            for fact, norm in zip(verified, verified_norm):
                label = _norm(re.split(r"[(,（]", str(fact.get("value_text") or ""))[0])
                if label and label not in body_norm:
                    add(GuardFinding("required_fact_omitted", HIGH, fact.get("value_text", "")[:40]))

    # --- certainty / confirmation -----------------------------------------
    if _CERTAINTY_RE.search(body):
        # Approval is the competent office's decision; no source Waymaker holds
        # can support a guarantee, so this is critical whatever the coverage.
        add(GuardFinding("forbidden_certainty", CRITICAL, _CERTAINTY_RE.search(body).group(0)))
    if _OFFICIAL_CONFIRMATION_RE.search(body):
        add(GuardFinding("claims_official_confirmation", HIGH, _OFFICIAL_CONFIRMATION_RE.search(body).group(0)))

    # --- contamination ------------------------------------------------------
    allowed = {status_code} | {c.split("-")[0] + "-" + c.split("-")[1] for c in user_mentioned_statuses if "-" in c}
    if status_code:
        for m in _STATUS_CODE_RE.finditer(body):
            code = m.group(1)
            if code not in allowed:
                add(GuardFinding("wrong_status_family", HIGH, code))
                break
    if procedure_family == "stay" and _VISA_PROCEDURE_RE.search(body):
        add(GuardFinding("wrong_procedure_scope", HIGH, _VISA_PROCEDURE_RE.search(body).group(0)))

    pages = {int(p) for p in cited_pages if p}
    if pages:
        for m in _PAGE_RE.finditer(body):
            num = int(m.group(1) or m.group(2))
            if num not in pages:
                add(GuardFinding("unsupported_citation", HIGH, f"page {num}"))
                break

    # --- language / style -----------------------------------------------------
    lang = (language or "ko").lower()
    hangul, latin = len(_HANGUL_RE.findall(body)), len(_LATIN_RE.findall(body))
    if lang.startswith("ko") and latin > 3 * max(hangul, 1) and latin > 40:
        add(GuardFinding("language_mismatch", MEDIUM, "expected Korean"))
    if lang.startswith("en") and hangul > latin and hangul > 20:
        add(GuardFinding("language_mismatch", MEDIUM, "expected English"))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。다])\s+", body) if len(s.strip()) > 20]
    if sentences and len(sentences) - len(set(sentences)) >= 2:
        add(GuardFinding("duplicated_disclaimer", LOW))
    return result
