"""Legal evidence service — Korean case law (판례) + administrative decisions (재결례).

This is a dedicated, backend-only retrieval service for *adjudicative* official
evidence (court precedent and administrative-appeal / special-administrative-appeal
decisions) from the 국가법령정보 공동활용 / LAW OPEN DATA APIs (law.go.kr /
open.law.go.kr DRF endpoints). It is intentionally **separate from the
visa/manual retrieval pipeline**: manuals, statutes, and official administrative
guidance remain the PRIMARY source for current visa/stay requirements; case law
and adjudication decisions are **supplementary context only**.

Non-negotiable guarantees:

* Authentication uses the EXISTING ``LAW_API_OC`` env var (via
  ``grounding_config``). No new variable is introduced; the OC value is never
  hardcoded, never returned to the frontend, never logged, and never placed in
  any sanitized URL. All external calls happen here in the backend.
* Every external HTTP call reuses the shared ``law_tools`` transport + URL
  sanitization seam, so OC-redaction logic lives in exactly one place.
* Missing ``LAW_API_OC`` (local/dev/test) degrades gracefully: retrieval returns
  a clear ``not_configured`` / ``unavailable`` status instead of crashing
  Waymaker. Nothing here ever raises out of the public functions.
* Case bodies are NOT sent to the LLM wholesale. The service prefers 판시사항
  (holding issue), 판결요지 (holding summary), 참조조문 (reference statutes), and
  the most relevant reasoning chunks.
* Safety: case law is never used to guarantee approval/recognition/issuance/
  extension/litigation success, and asylum-gaming prompts (false-narrative
  construction, interview coaching, evidence fabrication, fact concealment) are
  detected so the caller can refuse and redirect.

Two-step retrieval (mirrors the documented LAW OPEN DATA design):
    1. 목록 조회  — lawSearch.do?target=<t>  → candidate cases (list grade)
    2. 본문 조회  — lawService.do?target=<t>&ID=<id>  → full parsed body + chunks
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .grounding_config import GroundingConfig, load_grounding_config
from . import law_tools as lt

LEGAL_EVIDENCE_VERSION = "2026-06-legal-evidence-caselaw-v1"

logger = logging.getLogger("paradiso.legal_evidence")


# ---------------------------------------------------------------------------
# Source types + DRF targets
# ---------------------------------------------------------------------------
class LegalEvidenceSourceType:
    """Normalized adjudicative source types (public, stable string enum)."""

    PRECEDENT = "precedent"
    ADMINISTRATIVE_APPEAL = "administrative_appeal"
    SPECIAL_ADMINISTRATIVE_APPEAL = "special_administrative_appeal"


LEGAL_EVIDENCE_SOURCE_TYPES: Tuple[str, ...] = (
    LegalEvidenceSourceType.PRECEDENT,
    LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL,
    LegalEvidenceSourceType.SPECIAL_ADMINISTRATIVE_APPEAL,
)

# DRF ``target`` codes. Only court precedent (prec) is officially confirmed
# (open.law.go.kr precListGuide / precInfoGuide). The administrative-appeal
# targets are NOT publicly confirmed, so we never hardcode an unverified code as
# gospel: they are env-overridable best-effort values that degrade gracefully
# (an unknown target simply returns no parseable results -> "unavailable").
#   * LAW_API_ADMIN_APPEAL_TARGET          (행정심판례)         default "decc"
#   * LAW_API_SPECIAL_ADMIN_APPEAL_TARGET  (특별행정심판재결례)  default unset
_CONFIRMED_PRECEDENT_TARGET = "prec"


def _env(name: str, default: str = "") -> str:
    import os

    return (os.environ.get(name) or "").strip() or default


def _source_target(source_type: str) -> str:
    if source_type == LegalEvidenceSourceType.PRECEDENT:
        return _CONFIRMED_PRECEDENT_TARGET
    if source_type == LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL:
        return _env("LAW_API_ADMIN_APPEAL_TARGET", "decc")
    if source_type == LegalEvidenceSourceType.SPECIAL_ADMINISTRATIVE_APPEAL:
        # No documented default — operator must set it; otherwise unavailable.
        return _env("LAW_API_SPECIAL_ADMIN_APPEAL_TARGET", "")
    return ""


def _target_is_confirmed(source_type: str) -> bool:
    """Whether the DRF target for this source type is officially confirmed."""
    return source_type == LegalEvidenceSourceType.PRECEDENT


# ---------------------------------------------------------------------------
# Normalized types
# ---------------------------------------------------------------------------
@dataclass
class LegalCaseChunk:
    """One quotable evidence chunk from a case body.

    ``chunk_type`` is one of: holding (판시사항), summary (판결요지),
    reference_statutes (참조조문), reference_cases (참조판례), ruling_summary
    (재결요지), order (주문), claim (청구취지), reasoning (이유 / 판례내용 excerpt).
    Full raw bodies are never emitted as a single chunk.
    """

    label: str
    text: str
    chunk_type: str
    relevance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "text": self.text,
            "chunkType": self.chunk_type,
            "relevance": round(float(self.relevance), 4),
        }


@dataclass
class LegalCase:
    """A normalized court precedent or administrative-appeal decision."""

    source_type: str
    source_id: str = ""          # 판례정보일련번호 / decision serial / ID
    case_name: str = ""          # 사건명
    case_number: str = ""        # 사건번호
    court: str = ""              # 법원명 / 재결청
    court_type_code: str = ""    # 법원종류코드
    case_type_name: str = ""     # 사건종류명
    case_type_code: str = ""     # 사건종류코드
    decision_date: str = ""      # 선고일자 / 의결일자
    decision_type: str = ""      # 판결유형 / 선고
    holding: str = ""            # 판시사항
    summary: str = ""            # 판결요지 / 재결요지
    reference_statutes: str = "" # 참조조문 / 관계법령
    reference_cases: str = ""    # 참조판례
    # Administrative-appeal specific.
    disposition_authority: str = ""  # 처분청
    ruling_authority: str = ""       # 재결청
    claim: str = ""                  # 청구취지
    order: str = ""                  # 주문 / 재결주문
    disposition_date: str = ""       # 처분일자
    source_download_url: str = ""    # 원본다운로드URL (sanitized)
    data_reference_datetime: str = ""  # 데이터기준일시
    # Derived / housekeeping.
    chunks: List[LegalCaseChunk] = field(default_factory=list)
    # Bounded reasoning text (판례내용 / 이유) kept ONLY so the orchestrator can
    # re-window query-relevant reasoning chunks. It is private: never emitted by
    # to_public_dict / citations, so the full body never reaches the LLM or UI.
    reasoning_text: str = ""
    url: str = ""                # sanitized detail link
    result_kind: str = "list_result"   # list_result | body_result
    score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    retrieved_at: str = ""

    # ------------------------------------------------------------------
    def citation(self) -> Dict[str, Any]:
        """Compact citation for the answer + UI (never the raw OC or body)."""
        return {
            "case_name": self.case_name,
            "case_number": self.case_number,
            "court_or_tribunal": self.court or self.ruling_authority,
            "decision_date": self.decision_date or self.disposition_date,
            "source_type": self.source_type,
            "retrieved_source_id": self.source_id,
        }

    def to_public_dict(self, *, include_chunks: bool = True) -> Dict[str, Any]:
        """Public, secret-free projection. Excludes any raw full body by default;
        only the holding/summary/reference fields and selected chunks are kept."""
        out: Dict[str, Any] = {
            "sourceType": self.source_type,
            "sourceId": self.source_id,
            "caseName": self.case_name,
            "caseNumber": self.case_number,
            "court": self.court or self.ruling_authority,
            "decisionDate": self.decision_date or self.disposition_date,
            "decisionType": self.decision_type,
            "resultKind": self.result_kind,
            "citation": self.citation(),
            "score": round(float(self.score), 4),
        }
        for key, value in (
            ("caseTypeName", self.case_type_name),
            ("holding", self.holding),
            ("summary", self.summary),
            ("referenceStatutes", self.reference_statutes),
            ("referenceCases", self.reference_cases),
            ("dispositionAuthority", self.disposition_authority),
            ("rulingAuthority", self.ruling_authority),
            ("claim", self.claim),
            ("order", self.order),
            ("url", self.url),
            ("sourceDownloadUrl", self.source_download_url),
            ("dataReferenceDatetime", self.data_reference_datetime),
        ):
            if value:
                out[key] = value
        if include_chunks and self.chunks:
            out["chunks"] = [c.to_dict() for c in self.chunks]
        return out


@dataclass
class LegalEvidenceResult:
    """The outcome of a legal-evidence retrieval for one question."""

    query: str
    source_types: List[str]
    status: str = "not_attempted"   # available|no_results|not_configured|unavailable|disabled|error|safety_refused
    cases: List[LegalCase] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_type: str = ""
    expanded_queries: List[str] = field(default_factory=list)
    safety_refused: bool = False
    retrieved_at: str = ""
    version: str = LEGAL_EVIDENCE_VERSION

    def to_dict(self, *, include_chunks: bool = True) -> Dict[str, Any]:
        return {
            "version": self.version,
            "query": self.query,
            "sourceTypes": list(self.source_types),
            "status": self.status,
            "available": self.status == "available",
            "safetyRefused": self.safety_refused,
            "errorType": self.error_type,
            "warnings": list(dict.fromkeys(self.warnings)),
            "expandedQueries": list(self.expanded_queries),
            "caseCount": len(self.cases),
            "cases": [c.to_public_dict(include_chunks=include_chunks) for c in self.cases],
            "citations": list(self.citations),
            "retrievedAt": self.retrieved_at or _now_iso(),
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Tolerant field extraction (Korean official keys + fallbacks)
# ---------------------------------------------------------------------------
_K = {
    "serial": ("판례정보일련번호", "판례일련번호", "재결례일련번호", "일련번호", "ID", "id", "caseSerial"),
    "case_name": ("사건명", "안건명", "제목", "caseName", "title"),
    "case_number": ("사건번호", "재결례사건번호", "caseNumber", "caseNo"),
    "court": ("법원명", "재결청", "처분청", "courtName", "court"),
    "court_type_code": ("법원종류코드", "courtTypeCode"),
    "case_type_name": ("사건종류명", "caseTypeName"),
    "case_type_code": ("사건종류코드", "caseTypeCode"),
    "decision_date": ("선고일자", "의결일자", "재결일자", "decisionDate"),
    "decision_type": ("판결유형", "선고", "재결구분", "decisionType"),
    "holding": ("판시사항", "holding"),
    "summary": ("판결요지", "재결요지", "결정요지", "summary"),
    "ref_statutes": ("참조조문", "관계법령", "referenceStatutes"),
    "ref_cases": ("참조판례", "referenceCases"),
    "disposition_authority": ("처분청", "dispositionAuthority"),
    "ruling_authority": ("재결청", "rulingAuthority"),
    "claim": ("청구취지", "claim"),
    "order": ("주문", "재결주문", "order"),
    "disposition_date": ("처분일자", "dispositionDate"),
    "resolution_date": ("의결일자", "resolutionDate"),
    "body": ("판례내용", "재결내용", "이유", "내용", "본문", "body"),
    "reasoning": ("이유", "reasoning"),
    "ref_statutes_admin": ("관계법령",),
    "download_url": ("원본다운로드URL", "원문다운로드URL", "downloadUrl"),
    "data_ref_dt": ("데이터기준일시", "dataReferenceDatetime"),
    "detail_link": ("판례상세링크", "상세링크", "url", "link"),
}


def _pick(obj: Dict[str, Any], group: str) -> str:
    if not isinstance(obj, dict):
        return ""
    for key in _K.get(group, ()):  # type: ignore[arg-type]
        value = obj.get(key)
        if value not in (None, "", [], {}):
            return str(value).strip()
    return ""


def _clean(value: Any, *, limit: int = 1200) -> str:
    return " ".join(str(value or "").split())[:limit]


def _identity_keys() -> Tuple[str, ...]:
    return tuple({*_K["serial"], *_K["case_name"], *_K["case_number"]})


def _find_record(payload: Any, *, limit: int = 30) -> List[Dict[str, Any]]:
    """Collect candidate record dicts from a parsed DRF payload (schema-tolerant).

    DRF nests results under family keys (``{"PrecSearch": {"prec": [...]}}``,
    ``{"PrecService": {...}}``, etc.). We collect dicts that carry case identity
    without hardcoding one schema.
    """
    ident = _identity_keys()
    out: List[Dict[str, Any]] = []

    def looks_like_record(node: Dict[str, Any]) -> bool:
        return any(node.get(k) not in (None, "", [], {}) for k in ident)

    def visit(node: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(node, dict):
            has_child_container = any(isinstance(v, (dict, list)) for v in node.values())
            if looks_like_record(node) and not has_child_container:
                out.append(node)
                return
            for value in node.values():
                visit(value)
            if looks_like_record(node) and not out:
                out.append(node)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return out[:limit]


# ---------------------------------------------------------------------------
# Normalization (raw API object -> LegalCase)
# ---------------------------------------------------------------------------
def normalize_case(obj: Dict[str, Any], *, source_type: str, result_kind: str) -> Optional[LegalCase]:
    if not isinstance(obj, dict):
        return None
    case = LegalCase(
        source_type=source_type,
        result_kind=result_kind,
        source_id=_clean(_pick(obj, "serial"), limit=80),
        case_name=_clean(_pick(obj, "case_name"), limit=300),
        case_number=_clean(_pick(obj, "case_number"), limit=120),
        court=_clean(_pick(obj, "court"), limit=160),
        court_type_code=_clean(_pick(obj, "court_type_code"), limit=40),
        case_type_name=_clean(_pick(obj, "case_type_name"), limit=120),
        case_type_code=_clean(_pick(obj, "case_type_code"), limit=40),
        decision_date=_clean(_pick(obj, "decision_date"), limit=40),
        decision_type=_clean(_pick(obj, "decision_type"), limit=80),
        holding=_clean(_pick(obj, "holding"), limit=1600),
        summary=_clean(_pick(obj, "summary"), limit=1600),
        reference_statutes=_clean(_pick(obj, "ref_statutes"), limit=600),
        reference_cases=_clean(_pick(obj, "ref_cases"), limit=600),
        disposition_authority=_clean(_pick(obj, "disposition_authority"), limit=160),
        ruling_authority=_clean(_pick(obj, "ruling_authority"), limit=160),
        claim=_clean(_pick(obj, "claim"), limit=1200),
        order=_clean(_pick(obj, "order"), limit=1200),
        disposition_date=_clean(_pick(obj, "disposition_date"), limit=40),
        data_reference_datetime=_clean(_pick(obj, "data_ref_dt"), limit=60),
        retrieved_at=_now_iso(),
    )
    detail = _pick(obj, "detail_link")
    if detail:
        case.url = lt._sanitize_url(detail)
    download = _pick(obj, "download_url")
    if download:
        case.source_download_url = lt._sanitize_url(download)
    # A usable record needs identity.
    if not (case.case_name or case.case_number or case.source_id):
        return None
    # Body grade: keep a bounded reasoning text (never emitted raw) and build
    # query-agnostic chunks. The orchestrator re-chunks with query awareness.
    if result_kind == "body_result":
        case.reasoning_text = _clean(_pick(obj, "body") or _pick(obj, "reasoning"), limit=4000)
        case.chunks = build_chunks(case)
    return case


# ---------------------------------------------------------------------------
# Chunking — prefer 판시사항 / 판결요지 / 참조조문 + best reasoning excerpts
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.。!?\n])\s+|(?<=다\.)\s+|(?<=음\.)\s+")


def _split_reasoning(text: str, *, max_chunks: int = 6) -> List[str]:
    raw = " ".join(str(text or "").split())
    if not raw:
        return []
    # Split into coarse sentence-ish segments, then regroup to ~280-char windows.
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(raw) if p.strip()]
    windows: List[str] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) + 1 <= 280:
            buf = f"{buf} {part}".strip()
        else:
            if buf:
                windows.append(buf)
            buf = part
        if len(windows) >= max_chunks * 3:
            break
    if buf:
        windows.append(buf)
    return windows


def build_chunks(case: LegalCase, *, query_tokens: Optional[List[str]] = None, max_reasoning: int = 3) -> List[LegalCaseChunk]:
    """Build quotable chunks, preferring holding/summary/reference + top reasoning.

    The full ``case.reasoning_text`` (판례내용 / 이유) is NEVER emitted as one
    chunk; only the most query-relevant reasoning WINDOWS (each ≤ 280 chars,
    capped at ``max_reasoning``) are kept, so the LLM receives a compact,
    citation-anchored excerpt set rather than the whole case body.
    """
    chunks: List[LegalCaseChunk] = []
    if case.holding:
        chunks.append(LegalCaseChunk("판시사항", case.holding[:900], "holding", 1.0))
    if case.summary:
        label = "재결요지" if case.source_type != LegalEvidenceSourceType.PRECEDENT else "판결요지"
        chunks.append(LegalCaseChunk(label, case.summary[:900], "summary", 0.95))
    if case.reference_statutes:
        chunks.append(LegalCaseChunk("참조조문", case.reference_statutes[:500], "reference_statutes", 0.8))
    if case.order:
        chunks.append(LegalCaseChunk("주문", case.order[:500], "order", 0.7))
    if case.claim:
        chunks.append(LegalCaseChunk("청구취지", case.claim[:500], "claim", 0.6))

    body = case.reasoning_text or ""
    if body:
        tokens = [t for t in (query_tokens or []) if t]
        windows = _split_reasoning(body)
        scored: List[Tuple[float, str]] = []
        for w in windows:
            overlap = sum(1 for t in tokens if t and t in w)
            # Light relevance: keyword overlap + brevity bonus.
            scored.append((overlap + (0.1 if len(w) < 220 else 0.0), w))
        scored.sort(key=lambda x: x[0], reverse=True)
        for rel, w in scored[:max_reasoning]:
            chunks.append(LegalCaseChunk("이유(발췌)", w[:300], "reasoning", round(min(0.5, 0.2 + 0.1 * rel), 4)))
    return chunks


# ---------------------------------------------------------------------------
# Query expansion (immigration / visa / stay / refugee / deportation / etc.)
# ---------------------------------------------------------------------------
# Domain anchor -> Korean expansion terms. Used to broaden a thin question into
# statute-anchored case-law queries. Conservative: a question must mention the
# anchor (KO or EN) for the expansion to apply.
_QUERY_EXPANSIONS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("사증발급", "비자발급", "visa issuance", "visa issue"), "출입국관리법 사증발급 거부 처분"),
    (("체류자격 변경", "자격변경", "변경허가", "status change", "change of status",
      "change my status", "change status", "change his status", "change her status"),
     "출입국관리법 체류자격 변경허가 거부"),
    (("체류기간 연장", "연장", "extension", "extend"), "출입국관리법 체류기간 연장 불허가"),
    (("체류자격외활동", "근무처", "취업", "work permission", "work permit", "employment"), "출입국관리법 체류자격외활동 허가 취업활동"),
    (("강제퇴거", "출국명령", "deportation", "removal", "departure order"), "출입국관리법 강제퇴거 출국명령 처분"),
    (("난민", "인도적", "refugee", "asylum", "humanitarian"), "난민법 난민인정 불인정 처분 행정소송"),
    (("외국인등록", "거소신고", "registration"), "출입국관리법 외국인등록 신고의무"),
    (("재입국", "reentry", "re-entry"), "출입국관리법 재입국허가"),
    (("영주", "permanent residence", "F-5"), "출입국관리법 영주자격 요건"),
    (("체류", "stay", "sojourn"), "출입국관리법 체류자격"),
)


def expand_query(question: str, *, issue_concepts: Optional[List[str]] = None, statute_anchors: Optional[List[str]] = None, max_variants: int = 4) -> List[str]:
    """Build a small set of Korean case-law queries from the question.

    Deterministic and network-free. The first variant is the (cleaned) question;
    subsequent variants add statute-anchored, domain-expanded phrasings so a thin
    English question still retrieves Korean adjudicative evidence.
    """
    text = " ".join(str(question or "").split())
    low = text.lower()
    variants: List[str] = []

    def add(v: str) -> None:
        v = " ".join(str(v or "").split())[:240]
        if v and v not in variants:
            variants.append(v)

    if text:
        add(text)
    for concept in issue_concepts or []:
        add(str(concept))
    for anchor in statute_anchors or []:
        add(str(anchor))
    for triggers, expansion in _QUERY_EXPANSIONS:
        if any(t.lower() in low for t in triggers):
            add(expansion)
    if not variants:
        add("출입국관리법 체류자격")
    return variants[:max(1, max_variants)]


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
# Court / tribunal binding weight (higher = more authoritative for context).
_COURT_WEIGHT: Tuple[Tuple[str, float], ...] = (
    ("대법원", 1.0),
    ("헌법재판소", 0.95),
    ("고등법원", 0.7),
    ("고법", 0.7),
    ("지방법원", 0.45),
    ("지법", 0.45),
    ("행정법원", 0.5),
)
_SOURCE_TYPE_WEIGHT: Dict[str, float] = {
    LegalEvidenceSourceType.PRECEDENT: 1.0,
    LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL: 0.85,
    LegalEvidenceSourceType.SPECIAL_ADMINISTRATIVE_APPEAL: 0.8,
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _court_weight(case: LegalCase) -> float:
    name = (case.court or case.ruling_authority or "")
    for token, weight in _COURT_WEIGHT:
        if token in name:
            return weight
    return 0.4


def _recency_score(case: LegalCase) -> float:
    raw = case.decision_date or case.disposition_date or ""
    m = _YEAR_RE.search(raw)
    if not m:
        return 0.0
    try:
        year = int(m.group(0))
    except ValueError:
        return 0.0
    now_year = datetime.now(timezone.utc).year
    age = max(0, now_year - year)
    # 0 (>=25y old) .. 1.0 (this year), linear.
    return max(0.0, min(1.0, 1.0 - age / 25.0))


def _tokenize(text: str) -> List[str]:
    toks = re.split(r"[\s,./·\-—()\[\]{}:;\"']+", str(text or ""))
    return [t for t in toks if t and len(t) >= 2]


def score_case(
    case: LegalCase,
    *,
    query_tokens: List[str],
    issue_concepts: Optional[List[str]] = None,
    statute_refs: Optional[List[str]] = None,
) -> Tuple[float, Dict[str, float]]:
    """Composite relevance score with an auditable breakdown.

    Signals: exact keyword match, statute/reference match, issue-type match,
    court/tribunal weight, recency, source type. Weights are explicit so ranking
    is testable and never random.
    """
    hay = " ".join(
        x for x in (case.case_name, case.holding, case.summary, case.reference_statutes, case.case_type_name) if x
    )
    hay_low = hay.lower()
    q = [t for t in (query_tokens or []) if t]
    keyword_hits = sum(1 for t in q if t.lower() in hay_low)
    keyword = min(1.0, keyword_hits / max(1, len(q))) if q else 0.0

    statute_refs = statute_refs or []
    ref_field = (case.reference_statutes or "").lower()
    statute = 0.0
    if statute_refs:
        statute = min(1.0, sum(1 for s in statute_refs if s and s.lower() in ref_field) / len(statute_refs))

    issue_concepts = issue_concepts or []
    issue = 0.0
    if issue_concepts:
        issue = min(1.0, sum(1 for c in issue_concepts if c and c.lower() in hay_low) / len(issue_concepts))

    court = _court_weight(case)
    recency = _recency_score(case)
    stype = _SOURCE_TYPE_WEIGHT.get(case.source_type, 0.7)

    breakdown = {
        "keyword": round(keyword, 4),
        "statute": round(statute, 4),
        "issue": round(issue, 4),
        "court": round(court, 4),
        "recency": round(recency, 4),
        "source_type": round(stype, 4),
    }
    total = (
        0.34 * keyword
        + 0.18 * statute
        + 0.16 * issue
        + 0.14 * court
        + 0.10 * recency
        + 0.08 * stype
    )
    return round(total, 6), breakdown


def rank_cases(
    cases: List[LegalCase],
    *,
    query: str,
    issue_concepts: Optional[List[str]] = None,
    statute_refs: Optional[List[str]] = None,
) -> List[LegalCase]:
    """Return cases sorted by composite score desc, then decision-date desc."""
    query_tokens = _tokenize(query)
    for c in cases:
        c.score, c.score_breakdown = score_case(
            c, query_tokens=query_tokens, issue_concepts=issue_concepts, statute_refs=statute_refs
        )

    def sort_key(c: LegalCase) -> Tuple[float, str]:
        return (c.score, c.decision_date or c.disposition_date or "")

    return sorted(cases, key=sort_key, reverse=True)


# ---------------------------------------------------------------------------
# Safety — asylum-gaming / deception detection
# ---------------------------------------------------------------------------
_ASYLUM_GAMING_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"난민\s*(으로|로)?\s*(인정|승인)\s*(받|되)\s*(는|을)?\s*(방법|법|전략|팁|요령|노하우)", re.IGNORECASE),
    re.compile(r"(난민|망명|asylum)\s*(인터뷰|면접|interview)\s*(통과|합격|대비|준비|coaching|연습|예상\s*답변)", re.IGNORECASE),
    re.compile(r"(어떤|무슨)\s*(사유|이유|근거|story|story line|스토리|진술)\s*(로|를|을)?\s*(말|주장|claim|진술|꾸미)", re.IGNORECASE),
    re.compile(r"(거짓|허위|fake|false)\s*(진술|서류|증거|사유|사실|story|narrative)", re.IGNORECASE),
    re.compile(r"(사실|facts?)\s*(을|를)?\s*(숨기|감추|은폐|conceal|hide)", re.IGNORECASE),
    re.compile(r"(증거|서류|문서|document|evidence)\s*(를|을)?\s*(위조|조작|fabricat|forge|꾸미)", re.IGNORECASE),
    re.compile(r"how\s+to\s+(get|be|become)\s+(recognized|granted)\s+(as\s+)?(a\s+)?refugee", re.IGNORECASE),
    re.compile(r"(coach|prep(are)?|pass|game|trick)\s+(the\s+)?(asylum|refugee)\s+interview", re.IGNORECASE),
    re.compile(r"what\s+(story|reason|grounds?)\s+should\s+i\s+(tell|claim|say)", re.IGNORECASE),
    re.compile(r"(fabricat|forge|falsif)\w*\s+(evidence|document|story|account)", re.IGNORECASE),
)


def is_asylum_gaming_prompt(text: str) -> bool:
    """True when a prompt seeks asylum/visa *gaming*: false-narrative construction,
    interview coaching, evidence fabrication, fact concealment, or "how to be
    recognized as a refugee" strategy. Neutral procedural questions are NOT flagged.
    """
    t = str(text or "")
    return any(p.search(t) for p in _ASYLUM_GAMING_PATTERNS)


# Public-safe case-law caution (never weakened).
CASE_LAW_CAUTION_KO = "주의: 개별 사건 판단이며 결과를 보장하지 않습니다."
CASE_LAW_CAUTION_EN = "Caution: this is an individual case decision and does not guarantee any outcome."

# Prompt directive injected when case-law evidence is supplied to the LLM.
LEGAL_EVIDENCE_PROMPT_DIRECTIVE = (
    "\n\n[Supplementary case-law / adjudication evidence]\n"
    "- The following 판례/재결례 items are SUPPLEMENTARY context, not the primary "
    "source. Current manuals, statutes, and official administrative guidance remain "
    "authoritative for documents, fees, deadlines, and procedures.\n"
    "- Use them ONLY to explain general legal issues and procedural context. NEVER "
    "use a precedent or decision to guarantee approval, recognition, issuance, "
    "extension, or litigation success.\n"
    "- Each case is an individual, fact-specific decision; surface that limitation. "
    "If the evidence is weak, outdated, lower-court-only, or fact-specific, say so.\n"
    "- Cite only the provided case name / number / court / date / source id. Do NOT "
    "invent cases, numbers, or quotations beyond the provided excerpts.\n"
    "- For refugee/asylum topics, use cases only for neutral legal/procedural "
    "explanation. Never provide asylum strategy, story construction, interview "
    "coaching, evidence fabrication, or fact concealment."
)


# ---------------------------------------------------------------------------
# In-memory TTL cache (search + body), keyed without the OC value
# ---------------------------------------------------------------------------
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Tuple[float, Any]] = {}


def _cache_get(key: str, ttl_seconds: int) -> Optional[Any]:
    if ttl_seconds <= 0:
        return None
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        ts, value = entry
        if (time.monotonic() - ts) > ttl_seconds:
            _CACHE.pop(key, None)
            return None
        return value


def _cache_put(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), value)


def reset_legal_evidence_cache_for_tests() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------
class LawOpenDataClient:
    """Backend-only client for the LAW OPEN DATA adjudication APIs.

    Reads ``LAW_API_OC`` via ``grounding_config`` (never a new var, never
    hardcoded). Adds timeout, retry-with-backoff, response normalization, error
    handling, and caching on top of the shared ``law_tools`` transport seam.
    """

    def __init__(
        self,
        *,
        config: Optional[GroundingConfig] = None,
        transport: Optional[lt.LawTransport] = None,
        max_retries: int = 2,
        backoff_base_seconds: float = 0.5,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.config = config or load_grounding_config()
        self.transport = transport or lt._default_transport
        self.max_retries = max(0, int(max_retries))
        self.backoff_base_seconds = max(0.0, float(backoff_base_seconds))
        self._sleep = sleep or time.sleep

    # -- config validation -------------------------------------------------
    @property
    def is_available(self) -> bool:
        """Whether live retrieval can run: a credential is present AND the mode
        is not 'disabled'. (The /api/ask gate also applies the enabled-without-
        credential rule; this is the service-level guard.)"""
        return bool(self.config.law_api_configured) and self.config.mode != "disabled"

    def config_validation(self) -> Dict[str, Any]:
        """Non-secret startup/config validation result. Warns/disables when the
        OC is missing; NEVER returns the OC value."""
        warnings: List[str] = []
        if not self.config.law_api_configured:
            warnings.append("LAW_API_OC_MISSING_LEGAL_EVIDENCE_DISABLED")
        if self.config.mode == "disabled":
            warnings.append("LAW_GROUNDING_DISABLED")
        return {
            "available": self.is_available,
            "law_api_configured": bool(self.config.law_api_configured),
            "credential_source": self.config.law_api_credential_source,
            "mode": self.config.mode,
            "warnings": warnings,
        }

    # -- low-level request with retry/backoff + cache ----------------------
    def _request(self, path: str, params: Dict[str, str], *, ttl_seconds: Optional[int] = None) -> lt.LawHttpResponse:
        ttl = self.config.cache_ttl_seconds if ttl_seconds is None else ttl_seconds
        # Cache key excludes the OC (it is added inside _build_request_url).
        cache_key = f"{path}?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = _cache_get(cache_key, ttl)
        if cached is not None:
            return cached

        url = lt._build_request_url(self.config, path, params)
        attempts = self.max_retries + 1
        last: Optional[lt.LawHttpResponse] = None
        for attempt in range(attempts):
            try:
                resp = self.transport(url, self.config.timeout_seconds)
            except Exception:  # transport must never raise out; treat as bad response
                resp = lt.LawHttpResponse(ok=False, status_code=0, text="", error_type="network")
            last = resp
            transient = (not resp.ok) and resp.error_type in {"timeout", "network"} or (resp.ok and resp.status_code >= 500)
            if not transient:
                break
            if attempt < attempts - 1:
                # exponential backoff (only between retries; tests inject a no-op sleeper)
                self._sleep(self.backoff_base_seconds * (2 ** attempt))
        assert last is not None
        if last.ok and last.status_code < 400:
            _cache_put(cache_key, last)
        return last

    # -- 목록 조회 (search) -------------------------------------------------
    def search_cases(
        self,
        query: str,
        *,
        source_type: str = LegalEvidenceSourceType.PRECEDENT,
        search: int = 1,
        display: int = 5,
        page: int = 1,
        org: str = "",
        curt: str = "",
        JO: str = "",
        sort: str = "",
        prncYd: str = "",
        nb: str = "",
        datSrcNm: str = "",
        response_type: str = "JSON",
    ) -> Dict[str, Any]:
        """판례/재결례 목록 조회 (lawSearch.do?target=<t>). Returns a normalized
        envelope: ``{status, cases, error_type, warnings, target, sanitized_url}``.
        Never raises."""
        q = (query or "").strip()
        target = _source_target(source_type)
        if not self.config.law_api_configured:
            return self._envelope(source_type, "not_configured", error_type=lt.LAW_API_NOT_CONFIGURED)
        if not target:
            return self._envelope(source_type, "unavailable", error_type="target_not_configured",
                                  warnings=["LEGAL_EVIDENCE_TARGET_NOT_CONFIGURED"])
        if not q:
            return self._envelope(source_type, "no_results", error_type=lt.LAW_API_NO_RESULTS)

        capped = max(1, min(int(display or 5), 20))
        params: Dict[str, str] = {
            "target": target,
            "type": response_type or "JSON",
            "query": q,
            "search": str(search if search in (1, 2) else 1),
            "display": str(capped),
            "page": str(max(1, int(page or 1))),
        }
        for key, value in (("org", org), ("curt", curt), ("JO", JO), ("sort", sort),
                           ("prncYd", prncYd), ("nb", nb), ("datSrcNm", datSrcNm)):
            if value:
                params[key] = str(value)

        resp = self._request(lt._SEARCH_PATH, params)
        return self._normalize_response(resp, source_type=source_type, result_kind="list_result",
                                        query=q, target=target, params=params)

    # -- 본문 조회 (body) ---------------------------------------------------
    def get_case_body(
        self,
        case_id: str,
        *,
        source_type: str = LegalEvidenceSourceType.PRECEDENT,
        response_type: str = "JSON",
    ) -> Optional[LegalCase]:
        """판례/재결례 본문 조회 (lawService.do?target=<t>&ID=<id>). Returns a
        body-grade LegalCase, or None on any failure. Never raises."""
        cid = (case_id or "").strip()
        target = _source_target(source_type)
        if not (self.config.law_api_configured and target and cid):
            return None
        params = {"target": target, "type": response_type or "JSON", "ID": cid}
        resp = self._request(lt._SERVICE_PATH, params)
        if not (resp.ok and resp.status_code < 400):
            return None
        payload, error, _parser, _shape = lt._parse_payload(resp.text)
        if error:
            return None
        records = _find_record(payload)
        if not records:
            return None
        case = normalize_case(records[0], source_type=source_type, result_kind="body_result")
        if case and not case.source_id:
            case.source_id = cid
        return case

    # -- helpers -----------------------------------------------------------
    def _envelope(self, source_type: str, status: str, *, cases: Optional[List[LegalCase]] = None,
                  error_type: str = "", warnings: Optional[List[str]] = None,
                  target: str = "", sanitized_url: str = "") -> Dict[str, Any]:
        return {
            "source_type": source_type,
            "status": status,
            "cases": cases or [],
            "error_type": error_type,
            "warnings": warnings or [],
            "target": target,
            "target_confirmed": _target_is_confirmed(source_type),
            "sanitized_url": sanitized_url,
        }

    def _normalize_response(self, resp: lt.LawHttpResponse, *, source_type: str, result_kind: str,
                            query: str, target: str, params: Dict[str, str]) -> Dict[str, Any]:
        sanitized = lt._sanitize_url(lt._build_request_url(self.config, lt._SEARCH_PATH, params))
        if not resp.ok:
            mapping = {"timeout": lt.LAW_API_TIMEOUT, "http_error": lt.LAW_API_HTTP_ERROR, "network": lt.LAW_API_BAD_RESPONSE}
            etype = mapping.get(resp.error_type, lt.LAW_API_BAD_RESPONSE)
            return self._envelope(source_type, "unavailable", error_type=etype,
                                  warnings=["SOURCE_UNAVAILABLE"], target=target, sanitized_url=sanitized)
        if resp.status_code >= 400:
            return self._envelope(source_type, "unavailable", error_type=lt.LAW_API_HTTP_ERROR,
                                  warnings=["SOURCE_UNAVAILABLE"], target=target, sanitized_url=sanitized)
        payload, error, _parser, _shape = lt._parse_payload(resp.text)
        if error == lt.LAW_API_NO_RESULTS:
            return self._envelope(source_type, "no_results", error_type=error, target=target, sanitized_url=sanitized)
        if error:
            return self._envelope(source_type, "unavailable", error_type=error,
                                  warnings=["SOURCE_UNAVAILABLE"], target=target, sanitized_url=sanitized)
        records = _find_record(payload)
        cases: List[LegalCase] = []
        for obj in records:
            c = normalize_case(obj, source_type=source_type, result_kind=result_kind)
            if c:
                if not c.url and sanitized:
                    c.url = sanitized
                cases.append(c)
        if not cases:
            return self._envelope(source_type, "no_results", target=target, sanitized_url=sanitized)
        return self._envelope(source_type, "available", cases=cases, target=target, sanitized_url=sanitized)


# ---------------------------------------------------------------------------
# Top-level orchestration (search -> rank -> fetch bodies -> chunk)
# ---------------------------------------------------------------------------
def retrieve_legal_evidence(
    question: str,
    *,
    source_types: Optional[List[str]] = None,
    issue_concepts: Optional[List[str]] = None,
    statute_refs: Optional[List[str]] = None,
    search: int = 1,
    max_cases: int = 3,
    fetch_bodies: bool = True,
    config: Optional[GroundingConfig] = None,
    transport: Optional[lt.LawTransport] = None,
    client: Optional[LawOpenDataClient] = None,
) -> LegalEvidenceResult:
    """Retrieve supplementary case-law / adjudication evidence for a question.

    Two-step per source type: list search (ranked) → body fetch for the top
    candidates → chunking. Degrades gracefully (never raises). Returns a
    ``safety_refused`` result for asylum-gaming prompts (no case retrieval).
    """
    q = " ".join(str(question or "").split())
    types = [t for t in (source_types or [LegalEvidenceSourceType.PRECEDENT]) if t in LEGAL_EVIDENCE_SOURCE_TYPES]
    result = LegalEvidenceResult(query=q, source_types=types, retrieved_at=_now_iso())

    # Safety gate first: never retrieve/coach for asylum-gaming prompts.
    if is_asylum_gaming_prompt(q):
        result.status = "safety_refused"
        result.safety_refused = True
        result.warnings.append("ASYLUM_GAMING_PROMPT_REFUSED")
        return result

    cli = client or LawOpenDataClient(config=config, transport=transport)
    if not cli.is_available:
        validation = cli.config_validation()
        result.status = "disabled" if cli.config.mode == "disabled" else "not_configured"
        result.warnings.extend(validation["warnings"])
        result.error_type = lt.LAW_API_NOT_CONFIGURED if not cli.config.law_api_configured else ""
        return result

    queries = expand_query(q, issue_concepts=issue_concepts, statute_anchors=statute_refs)
    result.expanded_queries = list(queries)

    collected: List[LegalCase] = []
    any_unavailable = False
    seen_ids: set = set()
    for source_type in types:
        for qv in queries:
            env = cli.search_cases(qv, source_type=source_type, search=search, display=max(3, max_cases))
            status = env.get("status")
            if status == "available":
                for c in env.get("cases", []):
                    key = (c.source_type, c.source_id or c.case_number or c.case_name)
                    if key in seen_ids:
                        continue
                    seen_ids.add(key)
                    collected.append(c)
                break  # first query variant that yields results is enough per type
            if status in {"unavailable", "error"}:
                any_unavailable = True
                for w in env.get("warnings", []):
                    if w not in result.warnings:
                        result.warnings.append(w)

    if not collected:
        result.status = "unavailable" if any_unavailable else "no_results"
        if any_unavailable and "SOURCE_UNAVAILABLE" not in result.warnings:
            result.warnings.append("SOURCE_UNAVAILABLE")
        return result

    ranked = rank_cases(collected, query=q, issue_concepts=issue_concepts, statute_refs=statute_refs)
    top = ranked[: max(1, int(max_cases))]

    if fetch_bodies:
        query_tokens = _tokenize(q)
        for case in top:
            if case.source_id:
                body = cli.get_case_body(case.source_id, source_type=case.source_type)
                if body:
                    # Preserve the ranking score + merge richer body fields/chunks.
                    body.score = case.score
                    body.score_breakdown = case.score_breakdown
                    if not body.url:
                        body.url = case.url
                    # Re-chunk with query awareness now that we have the body.
                    body.chunks = build_chunks(body, query_tokens=query_tokens) or case.chunks
                    _replace_case(top, case, body)
            if not case.chunks:
                case.chunks = build_chunks(case)

    result.cases = top
    result.citations = [c.citation() for c in top]
    result.status = "available"
    return result


def _replace_case(cases: List[LegalCase], old: LegalCase, new: LegalCase) -> None:
    for i, c in enumerate(cases):
        if c is old:
            cases[i] = new
            return


def legal_evidence_preflight(config: Optional[GroundingConfig] = None) -> Dict[str, Any]:
    """Non-secret readiness report (no external call). Safe for /health & startup."""
    cli = LawOpenDataClient(config=config)
    validation = cli.config_validation()
    return {
        "version": LEGAL_EVIDENCE_VERSION,
        "available": validation["available"],
        "law_api_configured": validation["law_api_configured"],
        "credential_source": validation["credential_source"],
        "mode": validation["mode"],
        "source_types": list(LEGAL_EVIDENCE_SOURCE_TYPES),
        "confirmed_targets": {
            LegalEvidenceSourceType.PRECEDENT: _target_is_confirmed(LegalEvidenceSourceType.PRECEDENT),
            LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL: bool(_source_target(LegalEvidenceSourceType.ADMINISTRATIVE_APPEAL)),
            LegalEvidenceSourceType.SPECIAL_ADMINISTRATIVE_APPEAL: bool(_source_target(LegalEvidenceSourceType.SPECIAL_ADMINISTRATIVE_APPEAL)),
        },
        "warnings": validation["warnings"],
    }
