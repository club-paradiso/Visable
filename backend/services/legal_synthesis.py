"""Optional source-grounded LLM synthesis layer for Waymaker Legal Research.

This sits ON TOP of the deterministic scaffold in ``legal_research.py``. The
deterministic result is always produced first and remains the fallback. Only
after retrieval + ranking + deterministic planning does the endpoint optionally
ask the model to SYNTHESIZE — and only from a compact source packet built from
the already-retrieved sources. The model never answers from the raw question.

Everything here is pure/stdlib (packet build, prompt build, JSON parse, and the
citation/safety validator) so it unit-tests fully offline. The actual provider
call lives in paradiso_backend.py (the existing OpenRouter abstraction) — this
module never opens a network connection or instantiates an LLM client.

Hard safety contract enforced by ``validate_synthesis``:
  * every referenced sourceId must exist in the packet (no phantom sources);
  * no statute/article (제N조 / 별표) appears unless it is present in the packet;
  * no case/decision number appears unless it is present in the packet;
  * no final-advice / approval-guarantee / impersonation phrasing;
  * no raw HTML.
Any failure → the caller falls back to the deterministic result + a warning.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Reuse the repo's existing citation detectors — do NOT reinvent regexes.
from services.law_citation_guard import detect_legal_article_citations, citation_supported_by_evidence
try:
    from services.citation_verifier import _CASE_NUMBER_RE, _DECISION_NUMBER_RE  # type: ignore
except Exception:  # pragma: no cover - defensive: keep validator working if internals move
    _CASE_NUMBER_RE = re.compile(r"(?:19|20)\d{2}(?:구합|구단|가합|가단|두|누|다|도|허|후|드|므|르)\d{1,6}")
    _DECISION_NUMBER_RE = re.compile(r"(?<![0-9A-Za-z가-힣])\d{2,4}-\d{1,6}(?![0-9])")

SYNTHESIS_MODES = ("deterministic", "source_grounded_llm")

# Source packet types.
PACKET_TYPES = ("law", "regulation", "precedent", "manual", "visa_data")

# Forbidden final-advice / guarantee / impersonation phrases (task §5).
# KO matched as exact substrings; EN matched case-insensitively.
FORBIDDEN_KO = (
    "무조건 가능합니다", "확실히 허가됩니다", "승소 가능합니다", "반드시 허가됩니다",
    "출입국청은 반드시", "100% 가능", "법률 자문입니다", "행정사 상담입니다", "변호사 상담입니다",
    "반드시 승인", "무조건 허가", "100퍼센트",
)
FORBIDDEN_EN = (
    "guaranteed approval", "you will win", "must approve", "100% eligible",
    "legal advice", "lawyer consultation", "guaranteed to be approved", "we guarantee",
)

# Spacing-/variant-tolerant patterns (red-team hardening): catch the same
# guarantee/outcome/impersonation intent even with extra spaces or morphological
# variants the fixed lists miss. KO patterns are matched against the
# whitespace-stripped text too (to defeat '반 드시 승인' style mid-token spaces);
# EN patterns use \s+ so multi-space variants still match. Targeted at
# certainty+outcome to keep false positives (which only trigger a safe
# deterministic fallback) low.
FORBIDDEN_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"100\s*%",
    r"무조건",
    r"반드시\s*(승인|허가|가능|승소|인용|발급)",
    r"확실히\s*(승인|허가|가능|인용|발급)",
    r"승소\s*(가능|확실|보장)",
    r"(승인|허가|발급|결과|승소)\s*(?:이|가)?\s*보장",
    r"100\s*%\s*(가능|확실|승인|허가)",
    r"법률\s*자문",
    r"(변호사|행정사)\s*상담",
    r"you\s+will\s+win",
    r"you\s+are\s+(?:fully\s+)?eligible",
    r"we\s+guarantee",
    r"guaranteed",
    r"100\s*%\s*(?:eligible|approv|guaranteed)",
    r"must\s+(?:be\s+)?approv",
    r"legal\s+advice",
    r"lawyer\s+consultation",
))

# Whitespace-tolerant broad case-number pattern (year + 1-3 Hangul case marker +
# >=3 digit serial) to catch fabricated case numbers in formats the repo's
# _CASE_NUMBER_RE marker list does not enumerate (e.g. '2021나5678'). The
# (?!년|월|일) lookahead + 3-digit-minimum serial avoid matching plain dates like
# '2024년 3월'. Residual false positives only trigger a safe deterministic fallback.
_BROAD_CASE_RE = re.compile(r"(?:19|20)\d{2}\s*(?!(?:년|월|일))[가-힣]{1,3}\s*\d{3,6}")
_BRACKET_SID_RE = re.compile(r"\[\s*(s\d+)\s*\]")

VALIDATION_FAILED_MESSAGE = {
    "ko": "AI 리서치 요약을 안전하게 검증하지 못해 기본 리서치 결과를 표시합니다.",
    "en": "Waymaker could not safely validate the AI research synthesis, so it is showing the standard research result instead.",
}

# Expected synthesis JSON keys. The richer "BetterLegalResearchAnswer" shape
# (task §3) is canonical; the normalizer below also accepts the original flatter
# shape (issues / analysis / text / nextDocuments / string riskFlags) additively
# so previously-valid synthesis output keeps validating.
_PLAIN_LIST_FIELDS = ("missingFacts", "nextQuestions", "documentsToCheck", "limitations")
_CONFIDENCE = ("high", "medium", "low")

_HTML_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def _norm_locale(locale: Any) -> str:
    return "en" if str(locale or "").strip().lower() == "en" else "ko"


def _strip_ws(s: Any) -> str:
    return re.sub(r"\s+", "", str(s or ""))


# ---------------------------------------------------------------------------
# Synthesis-mode resolution
# ---------------------------------------------------------------------------
def resolve_synthesis_mode(requested: Any, depth: str, *, provider_configured: bool, has_sources: bool) -> str:
    """Decide the effective synthesis mode (deterministic vs source_grounded_llm).

    * fast  -> always deterministic (lightweight; keeps Fast fast).
    * basic/pro -> source_grounded_llm by default, but ONLY when a provider is
      configured AND sources were retrieved; otherwise deterministic.
    * an explicit ``deterministic`` request always wins.
    """
    req = str(requested or "").strip().lower()
    if req == "deterministic":
        return "deterministic"
    if depth == "fast":
        return "deterministic"
    # basic / pro: default (or explicit source_grounded_llm) — gated on provider + sources.
    if provider_configured and has_sources:
        return "source_grounded_llm"
    return "deterministic"


# ---------------------------------------------------------------------------
# Source packet
# ---------------------------------------------------------------------------
def _law_packet_type(card: Dict[str, Any]) -> str:
    blob = (card.get("type") or "") + (card.get("title") or "")
    if "시행령" in blob or "시행규칙" in blob or "decree" in blob.lower() or "rule" in blob.lower():
        return "regulation"
    return "law"


def build_source_packet(
    question: str,
    *,
    mode: str,
    depth: str,
    locale: str,
    laws: Optional[List[Dict[str, Any]]] = None,
    precedents: Optional[List[Dict[str, Any]]] = None,
    manuals: Optional[List[Dict[str, Any]]] = None,
    paradiso: Optional[List[Dict[str, Any]]] = None,
    max_sources: int = 14,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Build a compact source packet + a {sourceId: source} map from retrieved cards.

    Pure. The packet is the ONLY context the model may synthesize from.
    """
    sources: List[Dict[str, Any]] = []
    used: Dict[str, Dict[str, Any]] = {}
    n = 0

    def add(entry: Dict[str, Any]) -> None:
        nonlocal n
        if len(sources) >= max_sources:
            return
        n += 1
        sid = "s%d" % n
        item = {"sourceId": sid}
        item.update({k: v for k, v in entry.items() if v})
        sources.append(item)
        used[sid] = item

    for c in (laws or []):
        add({
            "type": _law_packet_type(c),
            "strength": c.get("strength") or "background",
            "title": c.get("title") or "",
            "articleNo": c.get("articleNo") or "",
            "articleTitle": c.get("articleTitle") or "",
            "snippet": (c.get("snippet") or "")[:400],
            "sourceUrl": c.get("sourceUrl") or "",
        })
    for c in (precedents or []):
        add({
            "type": "precedent",
            "strength": c.get("strength") or "background",
            "title": c.get("title") or "",
            "court": c.get("court") or "",
            "caseNumber": c.get("caseNumber") or "",
            "decisionDate": c.get("decisionDate") or "",
            "snippet": (c.get("summary") or c.get("snippet") or "")[:400],
            "sourceUrl": c.get("sourceUrl") or "",
        })
    for c in (manuals or []):
        add({
            "type": "manual",
            "strength": c.get("strength") or "background",
            "title": c.get("title") or "",
            "snippet": (c.get("snippet") or "")[:400],
            "sourceUrl": c.get("sourceUrl") or "",
        })
    for c in (paradiso or []):
        add({
            "type": "visa_data",
            "strength": c.get("strength") or "metadata-only",
            "title": c.get("title") or "",
            "snippet": (c.get("note") or c.get("snippet") or "")[:200],
        })

    packet = {
        "question": (question or "").strip(),
        "mode": mode,
        "depth": depth,
        "locale": _norm_locale(locale),
        "sources": sources,
    }
    return packet, used


def packet_evidence_texts(packet: Dict[str, Any]) -> List[str]:
    """All strings in the packet that a citation could legitimately come from."""
    texts: List[str] = []
    for s in packet.get("sources", []):
        for key in ("title", "articleNo", "articleTitle", "court", "caseNumber", "snippet"):
            v = s.get(key)
            if v:
                texts.append(str(v))
    return texts


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_JSON_SCHEMA_HINT = (
    '{\n'
    '  "summary": string,\n'
    '  "issueMap": [{"issue": string, "whyItMatters": string, "sourceIds": string[]}],\n'
    '  "sourceBackedRules": [{"rule": string, "sourceIds": string[]}],\n'
    '  "applicationPoints": [{"point": string, "confidence": "high"|"medium"|"low", "sourceIds": string[]}],\n'
    '  "riskFlags": [{"risk": string, "why": string, "sourceIds": string[]}],\n'
    '  "missingFacts": string[],\n'
    '  "nextQuestions": string[],\n'
    '  "documentsToCheck": string[],\n'
    '  "limitations": string[],\n'
    '  "caution": string\n'
    '}'
)


def build_synthesis_prompt(packet: Dict[str, Any], *, depth: str, locale: str) -> str:
    """Build the user prompt. The system prompt (WAYMAKER_SYSTEM_PROMPT) is
    injected separately by the provider layer; this is the source-grounded task."""
    lang = _norm_locale(locale)
    lines: List[str] = []
    for s in packet.get("sources", []):
        meta = " | ".join(filter(None, [
            "[" + s["sourceId"] + "]",
            s.get("type"),
            "strength=" + str(s.get("strength") or ""),
            (s.get("title") or "").strip(),
            ("art " + s["articleNo"]) if s.get("articleNo") else "",
            (s.get("court") or ""),
            (s.get("caseNumber") or ""),
            (s.get("decisionDate") or ""),
        ]))
        snip = (s.get("snippet") or "").replace("\n", " ").strip()
        lines.append(meta + (" :: " + snip if snip else ""))
    source_block = "\n".join(lines) if lines else "(no sources)"

    if lang == "ko":
        rules = (
            "당신은 Waymaker 리걸 리서치의 출처 기반 정리 도구입니다. 아래 '출처 패킷'에 있는 출처만 사용해 "
            "정리하세요.\n"
            "- 패킷에 없는 법령·조문·판례·사건번호를 인용하거나 만들어내지 마세요.\n"
            "- 조문번호·사건번호는 패킷에 실제로 있을 때만 사용하세요.\n"
            "- 출처가 부족하면 부족하다고 말하세요.\n"
            "- 출처로 뒷받침되는 내용(sourceBackedRules)과 사실관계에 비춘 조심스러운 검토(applicationPoints)를 구분하세요.\n"
            "- sourceBackedRules·applicationPoints·issueMap·riskFlags 의 각 항목에는 근거가 된 sourceIds 를 최소 하나 이상 붙이세요.\n"
            "- limitations(한계)는 반드시 한 개 이상 적으세요. nextQuestions 또는 documentsToCheck 로 다음 확인사항을 제시하세요.\n"
            "- 사용자가 주지 않은 사실관계를 지어내지 말고, 모르는 부분은 missingFacts 에 적으세요.\n"
            "- 허가 여부, 승인, 소송 결과, 기관의 최종 판단을 보장하지 마세요.\n"
            "- 변호사·행정사·공무원을 사칭하지 마세요. 법률 자문이 아닙니다.\n"
            "- 모든 sourceIds 는 패킷의 sourceId 중에서만 사용하세요.\n"
        )
        if depth == "pro":
            rules += "- 심층 리서치이므로 쟁점·법령·판례·검토 포인트를 충분히 정리하되, 최종 결론은 내리지 마세요.\n"
        task = "다음 질문에 대해 위 규칙을 지켜 JSON 으로만 답하세요. 다른 텍스트나 코드펜스 없이 JSON 객체 하나만 출력하세요."
        question_label = "질문"
        packet_label = "출처 패킷"
    else:
        rules = (
            "You are the source-grounded synthesis tool of Waymaker Legal Research. Organize ONLY from the "
            "sources in the 'Source packet' below.\n"
            "- Do not cite or invent any statute/article/precedent/case number not in the packet.\n"
            "- Use article/case numbers only when they actually appear in the packet.\n"
            "- If the sources are insufficient, say so.\n"
            "- Separate source-backed rules (sourceBackedRules) from cautious, fact-relative reasoning (applicationPoints).\n"
            "- Attach at least one supporting sourceId to every sourceBackedRules / applicationPoints / issueMap / riskFlags item.\n"
            "- Always include at least one limitations entry, and give next checks via nextQuestions or documentsToCheck.\n"
            "- Do not invent facts the user did not provide; put unknowns in missingFacts.\n"
            "- Never guarantee eligibility, approval, lawsuit outcome, or an agency's final decision.\n"
            "- Do not impersonate a lawyer, administrative agent, or government officer. This is not legal advice.\n"
            "- Every sourceIds value must be one of the packet sourceId values.\n"
        )
        if depth == "pro":
            rules += "- This is deep research: organize issues/laws/precedents/application points thoroughly, but do not reach a final conclusion.\n"
        task = "Answer the question following the rules above, as JSON ONLY. Output exactly one JSON object, with no other text or code fences."
        question_label = "Question"
        packet_label = "Source packet"

    return (
        rules
        + "\n" + task + "\n\n"
        + "Output JSON shape:\n" + _JSON_SCHEMA_HINT + "\n\n"
        + question_label + ": " + (packet.get("question") or "") + "\n\n"
        + packet_label + ":\n" + source_block + "\n"
    )


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
def parse_synthesis_json(text: Any) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from model text (tolerates code fences/prose)."""
    if not isinstance(text, str):
        return None
    s = text.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    else:
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        s = s[start:end + 1]
    try:
        obj = json.loads(s)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_synthesis(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a parsed synthesis object into the canonical rich shape.

    Accepts BOTH the richer ``BetterLegalResearchAnswer`` shape (issueMap /
    applicationPoints / object riskFlags / documentsToCheck / rule) AND the
    original flatter shape (issues / analysis / string riskFlags / nextDocuments /
    text) so older valid output keeps validating. Output is always the rich shape.
    """
    out: Dict[str, Any] = {
        "summary": str(obj.get("summary") or "").strip(),
        "caution": str(obj.get("caution") or "").strip(),
    }

    # issueMap (new) or issues (legacy string[]) -> [{issue, whyItMatters, sourceIds}]
    issue_map: List[Dict[str, Any]] = []
    raw_issue_map = obj.get("issueMap")
    if isinstance(raw_issue_map, list) and raw_issue_map:
        for item in raw_issue_map:
            if isinstance(item, dict):
                issue = str(item.get("issue") or item.get("text") or "").strip()
                if issue:
                    issue_map.append({
                        "issue": issue,
                        "whyItMatters": str(item.get("whyItMatters") or "").strip(),
                        "sourceIds": _as_str_list(item.get("sourceIds")),
                    })
            elif str(item or "").strip():
                issue_map.append({"issue": str(item).strip(), "whyItMatters": "", "sourceIds": []})
    else:
        for s in _as_str_list(obj.get("issues")):
            issue_map.append({"issue": s, "whyItMatters": "", "sourceIds": []})
    out["issueMap"] = issue_map

    # sourceBackedRules: {rule|text, sourceIds}
    rules: List[Dict[str, Any]] = []
    for item in (obj.get("sourceBackedRules") or []):
        if isinstance(item, dict):
            rule = str(item.get("rule") or item.get("text") or "").strip()
            if rule:
                rules.append({"rule": rule, "sourceIds": _as_str_list(item.get("sourceIds"))})
        elif str(item or "").strip():
            rules.append({"rule": str(item).strip(), "sourceIds": []})
    out["sourceBackedRules"] = rules

    # applicationPoints (new) or analysis (legacy) -> [{point, confidence, sourceIds}]
    points: List[Dict[str, Any]] = []
    raw_points = obj.get("applicationPoints")
    if not (isinstance(raw_points, list) and raw_points):
        raw_points = obj.get("analysis")
    for item in (raw_points or []):
        if isinstance(item, dict):
            point = str(item.get("point") or item.get("text") or "").strip()
            if point:
                conf = str(item.get("confidence") or "").strip().lower()
                points.append({
                    "point": point,
                    "confidence": conf if conf in _CONFIDENCE else "low",
                    "sourceIds": _as_str_list(item.get("sourceIds")),
                })
        elif str(item or "").strip():
            points.append({"point": str(item).strip(), "confidence": "low", "sourceIds": []})
    out["applicationPoints"] = points

    # riskFlags: object {risk, why, sourceIds} (new) or plain string (legacy)
    risks: List[Dict[str, Any]] = []
    for item in (obj.get("riskFlags") or []):
        if isinstance(item, dict):
            risk = str(item.get("risk") or item.get("text") or "").strip()
            if risk:
                risks.append({
                    "risk": risk,
                    "why": str(item.get("why") or "").strip(),
                    "sourceIds": _as_str_list(item.get("sourceIds")),
                })
        elif str(item or "").strip():
            risks.append({"risk": str(item).strip(), "why": "", "sourceIds": []})
    out["riskFlags"] = risks

    # plain string lists; documentsToCheck (new) falls back to nextDocuments (legacy)
    out["missingFacts"] = _as_str_list(obj.get("missingFacts"))
    out["nextQuestions"] = _as_str_list(obj.get("nextQuestions"))
    docs = obj.get("documentsToCheck")
    if not (isinstance(docs, list) and docs):
        docs = obj.get("nextDocuments")
    out["documentsToCheck"] = _as_str_list(docs)
    out["limitations"] = _as_str_list(obj.get("limitations"))
    return out


def _collect_text(syn: Dict[str, Any]) -> str:
    parts: List[str] = [syn.get("summary", ""), syn.get("caution", "")]
    for item in syn.get("issueMap", []):
        parts.append(item.get("issue", ""))
        parts.append(item.get("whyItMatters", ""))
    for item in syn.get("sourceBackedRules", []):
        parts.append(item.get("rule", ""))
    for item in syn.get("applicationPoints", []):
        parts.append(item.get("point", ""))
    for item in syn.get("riskFlags", []):
        parts.append(item.get("risk", ""))
        parts.append(item.get("why", ""))
    for f in _PLAIN_LIST_FIELDS:
        parts.extend(syn.get(f, []))
    return "\n".join(p for p in parts if p)


def _referenced_source_ids(syn: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for field in ("issueMap", "sourceBackedRules", "applicationPoints", "riskFlags"):
        for item in syn.get(field, []):
            ids.extend(item.get("sourceIds", []))
    return ids


def validate_synthesis(
    obj: Any,
    *,
    packet: Dict[str, Any],
    locale: str = "ko",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate a parsed synthesis object against the packet + safety rules.

    Returns (ok, reason, cleaned). On failure cleaned is None and the caller
    falls back to the deterministic result with the localized warning.
    """
    if not isinstance(obj, dict):
        return False, "not_an_object", None
    syn = _normalize_synthesis(obj)

    used_ids = {s.get("sourceId") for s in packet.get("sources", [])}
    evidence = packet_evidence_texts(packet)
    text = _collect_text(syn)

    # 1. Every referenced sourceId must exist in the packet — both the structured
    #    references (rules/analysis) AND any "[sN]" tokens written inline anywhere
    #    (so a phantom source can't be implied in prose either).
    for sid in _referenced_source_ids(syn) + _BRACKET_SID_RE.findall(text):
        if sid not in used_ids:
            return False, "unsupported_source_id:%s" % sid, None

    # 2. No raw HTML.
    if _HTML_TAG_RE.search(text):
        return False, "raw_html", None

    # 3. No fabricated statute/article citation (must appear in the packet).
    for art in detect_legal_article_citations(text):
        if not citation_supported_by_evidence(art, evidence):
            return False, "fabricated_article:%s" % art, None

    # 4. No fabricated case/decision number (must appear in the packet). Use the
    #    repo's precise detectors PLUS a broad, whitespace-tolerant case pattern
    #    so a fabricated number in an unusual marker/spacing still gets checked.
    ev_blob = " ".join(evidence)
    ev_compact = _strip_ws(ev_blob)
    for case in _CASE_NUMBER_RE.findall(text):
        if case not in ev_blob:
            return False, "fabricated_case:%s" % case, None
    for dec in _DECISION_NUMBER_RE.findall(text):
        if dec not in ev_blob:
            return False, "fabricated_decision:%s" % dec, None
    for case in _BROAD_CASE_RE.findall(text):
        if _strip_ws(case) not in ev_compact:
            return False, "fabricated_case:%s" % _strip_ws(case), None

    # 5. No forbidden final-advice / guarantee / impersonation language. Matched
    #    on both the raw text and a whitespace-stripped copy (to defeat spacing
    #    evasion like '반 드시 승인'), plus spacing-/variant-tolerant patterns.
    low = text.lower()
    compact = _strip_ws(text)
    compact_low = compact.lower()
    for phrase in FORBIDDEN_EN:
        if phrase.lower() in low:
            return False, "forbidden_phrase:%s" % phrase, None
    for phrase in FORBIDDEN_KO:
        if phrase in text or _strip_ws(phrase) in compact:
            return False, "forbidden_phrase:%s" % phrase, None
    for pat in FORBIDDEN_PATTERNS:
        if pat.search(text) or pat.search(compact) or pat.search(compact_low):
            return False, "forbidden_pattern:%s" % pat.pattern, None

    # 6. Quality rubric (task §3). Citation fabrication and guarantee/advice
    #    language are already rejected above; these checks cover structural answer
    #    quality so a thin or unsourced AI summary falls back to the deterministic
    #    result instead of being shown. (Inventing user facts is mitigated by the
    #    prompt + missingFacts framing; fabricated citations are caught above.)
    refs = _referenced_source_ids(syn) + _BRACKET_SID_RE.findall(text)
    if not refs:
        return False, "quality:no_sources_cited", None
    if not syn.get("summary"):
        return False, "quality:no_summary", None
    if not syn.get("limitations"):
        return False, "quality:no_limitations", None
    depth = str(packet.get("depth") or "").strip().lower()
    if depth == "pro" and not (syn.get("nextQuestions") or syn.get("documentsToCheck")):
        return False, "quality:no_next_checks", None

    return True, "ok", syn
