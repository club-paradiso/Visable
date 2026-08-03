"""Unified search: deterministic intent routing and organic result building.

One input box has to absorb everything a user might type — a code (``D-2-1``,
``E74``), a keyword (``결혼이민``), a situation (``졸업 후 취업``), a full question
(``회사 옮기려면 뭘 해야 하나요``), a statute reference (``출입국관리법 제20조``), a job
description (``카페에서 음료를 만들어요``), or nothing meaningful at all.

Design rules this module exists to enforce:

* **Rules decide, AI only annotates.** Intent classification is deterministic.
  An AI classifier may refine the result later, but exact-code and keyword search
  must work with the AI provider completely down.
* **Organic results never wait for AI.** Everything here is local: visa data,
  the manual index, and the query itself. No LLM call, no outbound HTTP.
* **No invented codes.** A 체류자격 code is only reported when it resolves against
  the loaded visa dataset. A plausible-looking code that is not in the data is
  reported as *unrecognized*, not echoed back as if it existed.
* **Parent/subcode hierarchy is preserved.** ``D-2-1`` resolves to the subcode
  under ``D-2``; it is never flattened into its parent, and a parent match never
  presents subcode-specific rules as universal.

Pure functions plus one dataset-injected entry point. No I/O of its own.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

UNIFIED_SEARCH_VERSION = "2026-07-unified-search-v1"

# --- intents ---------------------------------------------------------------
INTENT_EXACT_VISA_CODE = "exact_visa_code"
INTENT_VISA_KEYWORD = "visa_keyword"
INTENT_VISA_SITUATION = "visa_situation"
INTENT_PROCEDURE_QUESTION = "procedure_question"
INTENT_LEGAL_QUESTION = "legal_question"
INTENT_EMPLOYMENT_REPORTING = "employment_reporting"
INTENT_FEATURE_NAVIGATION = "feature_navigation"
INTENT_UNKNOWN = "unknown"

INTENTS = (
    INTENT_EXACT_VISA_CODE, INTENT_VISA_KEYWORD, INTENT_VISA_SITUATION,
    INTENT_PROCEDURE_QUESTION, INTENT_LEGAL_QUESTION, INTENT_EMPLOYMENT_REPORTING,
    INTENT_FEATURE_NAVIGATION, INTENT_UNKNOWN,
)

MAX_QUERY_LENGTH = 300

# --- result kinds ----------------------------------------------------------
RESULT_STATUS_CARD = "status_card"
RESULT_SUBCODE_CARD = "subcode_card"
RESULT_PROCEDURE_CARD = "procedure_card"
RESULT_LEGAL_CARD = "legal_card"
RESULT_EMPLOYMENT_TOOL = "employment_tool"
RESULT_FEATURE_CARD = "feature_card"
RESULT_MANUAL_CARD = "manual_card"


# ---------------------------------------------------------------------------
# Query normalization
# ---------------------------------------------------------------------------
def normalize_query(raw: str) -> str:
    text = unicodedata.normalize("NFC", str(raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_QUERY_LENGTH]


# A code-shaped token: one letter, digits, optional sub-segments. Deliberately
# permissive at the *shape* level — validity is decided against the dataset, not
# by this regex, so an unknown-but-plausible code is detected and then rejected
# with an explicit reason instead of silently ignored.
_CODE_TOKEN_RE = re.compile(r"\b([A-Za-z])\s*-?\s*(\d{1,2})(?:\s*-?\s*([0-9A-Za-z]{1,3}))?\b")
_NAMED_CODE_RE = re.compile(r"\b(K-?ETA|K-?STAR|REGION-?S)\b", re.IGNORECASE)


def normalize_visa_code(raw: str, valid_main_codes: Set[str]) -> Optional[str]:
    """Normalize a code-shaped string to canonical ``A-N`` / ``A-N-SUB`` form.

    ``valid_main_codes`` disambiguates contiguous input: ``d101`` is ``D-10-1``
    only because ``D-10`` is a known main code, while ``d21`` is ``D-2-1``.
    """
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().upper()
    if not cleaned:
        return None
    if not re.search(r"\d", cleaned):
        return cleaned
    head = re.match(r"^([A-Z])[\s\-]?(\d.*)$", cleaned)
    if not head:
        return cleaned
    letter, body = head.group(1), head.group(2)
    digit_run = re.match(r"^(\d+)(.*)$", body)
    if not digit_run:
        return cleaned
    leading_digits, tail = digit_run.group(1), digit_run.group(2)
    tail = re.sub(r"^[\s\-]+", "", tail)

    main_digits, sub_from_digits = leading_digits, ""
    for prefix_len in range(min(len(leading_digits), 2), 0, -1):
        candidate = f"{letter}-{leading_digits[:prefix_len]}"
        if candidate in valid_main_codes:
            main_digits = leading_digits[:prefix_len]
            sub_from_digits = leading_digits[prefix_len:]
            break

    sub = re.sub(r"[\s\-]+", "-", sub_from_digits + tail).strip("-")
    return f"{letter}-{main_digits}-{sub}" if sub else f"{letter}-{main_digits}"


def split_visa_code(normalized: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """``D-2-1`` -> ``("D-2", "D-2-1")``; ``D-2`` -> ``("D-2", None)``.

    Two segments are a parent code; three or more are a subcode *under* that
    parent. The subcode is never collapsed into the parent.
    """
    if not normalized:
        return None, None
    parts = normalized.split("-")
    if len(parts) >= 3 and parts[1].isdigit():
        return f"{parts[0]}-{parts[1]}", normalized
    return normalized, None


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------
# Contesting a decision is a legal question even though the words also read as
# procedure ("이의신청"). These outrank generic procedure vocabulary; the weak set
# below only wins when no procedure word is present.
_STRONG_LEGAL_SIGNALS = (
    "이의신청", "행정심판", "행정소송", "소송", "판례", "판결", "대법원", "헌법재판소",
    "위헌", "강제퇴거", "출국명령", "불인정", "불허", "취소처분", "처분취소", "구제",
)

_LEGAL_SIGNALS = (
    "법 제", "법률", "시행령", "시행규칙", "결정례", "법령", "조문",
)
_LEGAL_ARTICLE_RE = re.compile(r"제\s*\d+\s*조")
_LEGAL_LAW_NAME_RE = re.compile(r"[가-힣]{2,}(?:법|법률)(?:\s*시행(?:령|규칙))?")
_CASE_NUMBER_RE = re.compile(r"\d{4}\s*(?:두|다|구합|구단|누|헌마|헌바|헌가|도|무)\s*\d+")

_PROCEDURE_SIGNALS = (
    "연장", "변경", "신고", "등록", "재입국", "발급", "신청", "접수", "예약",
    "체류지", "거소", "말소", "허가", "제출", "서류", "수수료", "기한",
    "언제까지", "며칠", "절차", "방법", "어떻게",
)

_EMPLOYMENT_SIGNALS = (
    "취업정보", "직종", "업종", "직종코드", "업종코드", "ksco", "ksic",
    "취업 신고", "취업신고", "근무처", "일자리", "연간소득",
)
# Job-description shapes: "…에서 …해요/합니다", "일해요", "만들어요"
_JOB_DESCRIPTION_RE = re.compile(
    r"(에서\s*.{0,12}(해요|합니다|한다|해|하고\s*있|일해|일합|근무))"
    r"|(일해요|일합니다|근무해요|근무합니다)"
    r"|(만들어요|만듭니다|청소해요|서빙해요|가르쳐요|조립해요|따요|잡아요|번역|편집)"
)

_FEATURE_SIGNALS = {
    "행정사": "agency-directory",
    "행정사무소": "agency-directory",
    "하이코리아 예약": "hikorea-reservation",
    "예약": "hikorea-reservation",
    "서식": "form-helper",
    "신청서": "form-helper",
    "귀화": "nationality-hub",
    "국적": "nationality-hub",
    "면접": "nationality-hub",
    "무비자": "short-stay",
    "단기입국": "short-stay",
}

_KEYWORD_TOPICS = (
    "결혼이민", "유학", "취업", "구직", "동포", "재외동포", "영주", "난민",
    "투자", "주재", "연수", "방문동거", "동반", "관광", "거주", "귀화", "기술",
    "교수", "회화지도", "예술흥행", "선원", "계절근로",
)


def _has_any(text: str, needles: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(n.lower() in lowered for n in needles)


def detect_visa_codes(
    query: str,
    valid_main_codes: Set[str],
    known_codes: Set[str],
) -> Dict[str, Any]:
    """Detect code-shaped tokens and validate them against the dataset.

    Returns recognized codes plus explicitly *unrecognized* ones. A code-shaped
    token that is not in the dataset is never returned as if it existed — that is
    the invented-code failure this function exists to prevent.
    """
    recognized: List[str] = []
    unrecognized: List[str] = []
    seen: Set[str] = set()

    for match in _NAMED_CODE_RE.finditer(query or ""):
        token = match.group(0).upper().replace("-", "")
        canonical = {"KETA": "K-ETA", "KSTAR": "K-STAR", "REGIONS": "REGION-S"}.get(token)
        if canonical and canonical in known_codes and canonical not in seen:
            seen.add(canonical)
            recognized.append(canonical)

    for match in _CODE_TOKEN_RE.finditer(query or ""):
        raw = match.group(0)
        normalized = normalize_visa_code(raw, valid_main_codes)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if normalized in known_codes:
            recognized.append(normalized)
            continue
        parent, _sub = split_visa_code(normalized)
        if parent and parent in known_codes:
            # The parent exists but this subcode does not — surface the parent and
            # say so, rather than pretending the subcode is real.
            recognized.append(parent)
            unrecognized.append(normalized)
        else:
            unrecognized.append(normalized)

    return {"recognized": recognized, "unrecognized": unrecognized}


def classify_intent(query: str, detected: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Deterministic intent classification. Rules win; AI may only refine later.

    Returns the intent plus the signals that produced it, so the UI can render an
    editable interpretation instead of an opaque verdict.
    """
    text = normalize_query(query)
    if not text:
        return {"intent": INTENT_UNKNOWN, "signals": [], "confidence": "none",
                "query": "", "rule": "empty"}

    detected = detected or {"recognized": [], "unrecognized": []}
    signals: List[str] = []

    has_article = bool(_LEGAL_ARTICLE_RE.search(text))
    has_case_number = bool(_CASE_NUMBER_RE.search(text))
    has_law_name = bool(_LEGAL_LAW_NAME_RE.search(text))
    strong_legal = _has_any(text, _STRONG_LEGAL_SIGNALS)
    legal_word = strong_legal or _has_any(text, _LEGAL_SIGNALS)
    employment_word = _has_any(text, _EMPLOYMENT_SIGNALS)
    job_shape = bool(_JOB_DESCRIPTION_RE.search(text))
    procedure_word = _has_any(text, _PROCEDURE_SIGNALS)

    # 1. Statute / case reference is the most specific signal there is.
    if has_case_number or (has_article and has_law_name):
        signals.append("statute_reference" if has_article else "case_number")
        return {"intent": INTENT_LEGAL_QUESTION, "signals": signals,
                "confidence": "high", "query": text, "rule": "explicit_legal_reference"}

    # 2. An exact code with nothing else to interpret.
    recognized = detected.get("recognized") or []
    if recognized:
        signals.append("visa_code")
        bare = re.sub(r"[A-Za-z]\s*-?\s*\d{1,2}(\s*-?\s*[0-9A-Za-z]{1,3})?", "", text)
        bare = re.sub(r"[\s\-]+", "", bare)
        if not bare:
            return {"intent": INTENT_EXACT_VISA_CODE, "signals": signals,
                    "confidence": "high", "query": text, "rule": "code_only"}

    # 3. Employment reporting: explicit vocabulary, or a job-description sentence.
    if employment_word:
        signals.append("employment_vocabulary")
        return {"intent": INTENT_EMPLOYMENT_REPORTING, "signals": signals,
                "confidence": "high", "query": text, "rule": "employment_vocabulary"}
    if job_shape and not recognized:
        signals.append("job_description_shape")
        return {"intent": INTENT_EMPLOYMENT_REPORTING, "signals": signals,
                "confidence": "medium", "query": text, "rule": "job_description"}

    # 4. Legal vocabulary. Dispute vocabulary (이의신청 / 행정심판 / 불허 …) wins even
    #    when a procedure word is also present — contesting a decision is a legal
    #    question first and a procedure second.
    if strong_legal:
        signals.append("dispute_vocabulary")
        return {"intent": INTENT_LEGAL_QUESTION, "signals": signals,
                "confidence": "high", "query": text, "rule": "dispute_vocabulary"}
    if legal_word and not procedure_word:
        signals.append("legal_vocabulary")
        return {"intent": INTENT_LEGAL_QUESTION, "signals": signals,
                "confidence": "medium", "query": text, "rule": "legal_vocabulary"}

    # 5. Feature navigation (a tool, not an answer).
    for needle, feature in _FEATURE_SIGNALS.items():
        if needle in text:
            signals.append(f"feature:{feature}")
            return {"intent": INTENT_FEATURE_NAVIGATION, "signals": signals,
                    "confidence": "medium", "query": text, "rule": "feature_keyword",
                    "feature": feature}

    # 6. Procedure question.
    if procedure_word:
        signals.append("procedure_vocabulary")
        return {"intent": INTENT_PROCEDURE_QUESTION, "signals": signals,
                "confidence": "medium" if len(text) > 4 else "low",
                "query": text, "rule": "procedure_vocabulary"}

    # 7. Topic keyword.
    for topic in _KEYWORD_TOPICS:
        if topic in text:
            signals.append(f"topic:{topic}")
            return {"intent": INTENT_VISA_KEYWORD, "signals": signals,
                    "confidence": "medium", "query": text, "rule": "topic_keyword",
                    "topic": topic}

    # 8. A code plus extra words is a situation about that code.
    if recognized:
        return {"intent": INTENT_VISA_SITUATION, "signals": signals,
                "confidence": "medium", "query": text, "rule": "code_with_context"}

    # 9. A sentence with a verb ending reads as a situation; a bare token does not.
    if len(text) >= 6 and re.search(r"(요|다|까|\?|나요|습니다)\s*$", text):
        signals.append("sentence_shape")
        return {"intent": INTENT_VISA_SITUATION, "signals": signals,
                "confidence": "low", "query": text, "rule": "sentence_shape"}

    return {"intent": INTENT_UNKNOWN, "signals": signals, "confidence": "none",
            "query": text, "rule": "no_signal"}


# ---------------------------------------------------------------------------
# Organic result building
# ---------------------------------------------------------------------------
def _subcodes(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("subCodes", "subcodes", "sub_codes", "details"):
        value = record.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    return []


def build_visa_index(visa_data: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index parent codes *and* nested subcodes by canonical code.

    Subcodes live inside each parent's ``subCodes`` array in ``visa_data.json``.
    They are indexed as first-class entries — with a ``_parentCode`` back-pointer —
    so a search for ``D-2-1`` resolves to the subcode itself and is never answered
    with the parent's universal text.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for record in visa_data or []:
        if not isinstance(record, dict) or not record.get("code"):
            continue
        code = str(record["code"]).strip().upper()
        entry = dict(record)
        entry["_isSubcode"] = False
        entry["_parentCode"] = None
        index[code] = entry
        for sub in _subcodes(record):
            sub_code = str(sub.get("code") or "").strip().upper()
            if not sub_code or sub_code in index:
                continue
            sub_entry = dict(sub)
            sub_entry["_isSubcode"] = True
            sub_entry["_parentCode"] = code
            index[sub_code] = sub_entry
    return index


# Parent records use `name` + `newReq`; subcode records use `name` + `addReq`.
_LABEL_KEYS = ("name", "nameKo", "name_ko", "title", "koreanName")
_SUMMARY_KEYS = ("addReq", "newReq", "summary", "overview", "description", "descKo")


def _record_label(record: Dict[str, Any]) -> str:
    for key in _LABEL_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(record.get("code") or "")


def _record_summary(record: Dict[str, Any]) -> str:
    for key in _SUMMARY_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:220]
    return ""


def _keyword_score(record: Dict[str, Any], tokens: Sequence[str]) -> int:
    if not tokens:
        return 0
    haystack = " ".join(str(record.get(k) or "") for k in
                        ("code", "name", "nameKo", "title", "cat", "newReq", "addReq",
                         "summary", "overview", "description", "keywords", "tags")).lower()
    return sum(12 for token in tokens if token and token.lower() in haystack)


def build_organic_results(
    query: str,
    *,
    visa_data: Sequence[Dict[str, Any]],
    intent: Dict[str, Any],
    detected: Dict[str, Any],
    manual_hits: Optional[Dict[str, Any]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Build deterministic result cards. Local data only — never blocks on AI."""
    text = normalize_query(query)
    index = build_visa_index(visa_data)
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    # 1. Exact code matches first, parent and subcode kept distinct.
    for code in detected.get("recognized") or []:
        record = index.get(code)
        if record is None or code in seen:
            continue
        seen.add(code)
        parent, sub = split_visa_code(code)
        results.append({
            "kind": RESULT_SUBCODE_CARD if sub else RESULT_STATUS_CARD,
            "code": code,
            "parentCode": parent if sub else None,
            "title": _record_label(record),
            "summary": _record_summary(record),
            "matchReason": "exact_code",
            "score": 1000,
        })
        # A subcode result also offers its parent, clearly labelled as the parent
        # — never merged into one card that would read as universal rules.
        if sub and parent and parent in index and parent not in seen:
            seen.add(parent)
            results.append({
                "kind": RESULT_STATUS_CARD,
                "code": parent,
                "parentCode": None,
                "title": _record_label(index[parent]),
                "summary": _record_summary(index[parent]),
                "matchReason": "parent_of_exact_code",
                "score": 900,
            })

    # 2. Subcode label matches ("E-7-4" typed as "숙련기능인력").
    tokens = [t for t in re.split(r"\s+", text) if len(t) >= 2]
    if intent.get("intent") != INTENT_EXACT_VISA_CODE:
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for code, record in index.items():
            if code in seen:
                continue
            score = _keyword_score(record, tokens)
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("code"))))
        for score, record in scored[: max(0, limit - len(results))]:
            code = str(record.get("code"))
            if code in seen:
                continue
            seen.add(code)
            parent, sub = split_visa_code(code)
            results.append({
                "kind": RESULT_SUBCODE_CARD if sub else RESULT_STATUS_CARD,
                "code": code,
                "parentCode": parent if sub else None,
                "title": _record_label(record),
                "summary": _record_summary(record),
                "matchReason": "keyword",
                "score": score,
            })

    # 3. Intent-specific tool cards.
    intent_name = intent.get("intent")
    if intent_name == INTENT_EMPLOYMENT_REPORTING:
        results.insert(0, {
            "kind": RESULT_EMPLOYMENT_TOOL,
            "toolId": "employment-reporting",
            "title": "취업정보 신고 직종·업종 코드 찾기",
            "summary": "하시는 일과 사업장 분야를 적으면 KSCO8 직종 후보와 KSIC11 업종 후보를 "
                       "각각 나눠서 찾아드립니다. 최종 확정은 하이코리아에서 확인하세요.",
            "matchReason": "intent",
            "score": 1100,
        })
    elif intent_name == INTENT_LEGAL_QUESTION:
        results.insert(0, {
            "kind": RESULT_LEGAL_CARD,
            "toolId": "legal-research",
            "title": "법령·판례 기준으로 분석",
            "summary": "법제처 공식 법령과 판례를 검색해 근거 상태와 확인이 필요한 사실을 정리합니다.",
            "matchReason": "intent",
            "score": 1100,
        })
    elif intent_name == INTENT_FEATURE_NAVIGATION and intent.get("feature"):
        results.insert(0, {
            "kind": RESULT_FEATURE_CARD,
            "toolId": intent["feature"],
            "title": _FEATURE_TITLES.get(intent["feature"], intent["feature"]),
            "summary": "",
            "matchReason": "intent",
            "score": 1100,
        })

    # 4. Manual chunks, always carrying their approval state.
    for hit in (manual_hits or {}).get("needs_review", [])[:3]:
        results.append({
            "kind": RESULT_MANUAL_CARD,
            "title": hit.get("heading") or "매뉴얼 본문",
            "summary": hit.get("excerpt", ""),
            "sourceId": hit.get("source_id", ""),
            "page": hit.get("page", 0),
            "approvalState": hit.get("approval_state", ""),
            "usableAsDirectEvidence": False,
            "matchReason": "manual_index",
            "score": 300,
        })
    for hit in (manual_hits or {}).get("approved", [])[:3]:
        results.append({
            "kind": RESULT_MANUAL_CARD,
            "title": hit.get("heading") or "매뉴얼 본문",
            "summary": hit.get("excerpt", ""),
            "sourceId": hit.get("source_id", ""),
            "page": hit.get("page", 0),
            "approvalState": hit.get("approval_state", ""),
            "usableAsDirectEvidence": True,
            "matchReason": "manual_index",
            "score": 700,
        })

    results.sort(key=lambda r: -int(r.get("score") or 0))
    return results[:limit]


_FEATURE_TITLES = {
    "agency-directory": "행정사 사무소 찾기",
    "hikorea-reservation": "하이코리아 방문예약 도우미",
    "form-helper": "신청 서식 작성 도우미",
    "nationality-hub": "국적·귀화 안내",
    "short-stay": "국적별 단기입국 경로 확인",
}


# Suggestion row types, mirroring the `Search / Suggestion Row` design
# component (UX-03, node 400:12). `recent_query` is rendered by the frontend
# from client-side history; the backend never emits it, because the backend
# does not — and should not — keep a record of what anyone searched for.
SUGGEST_VISA_CODE = "visa_code"
SUGGEST_VISA_STATUS = "visa_status"
SUGGEST_PROCEDURE = "procedure"
SUGGEST_LEGAL_SOURCE = "legal_source"
SUGGEST_EMPLOYMENT_TOOL = "employment_tool"
SUGGEST_RECENT_QUERY = "recent_query"
SUGGEST_CORRECTION = "correction"

SUGGESTION_TYPES = (
    SUGGEST_VISA_CODE, SUGGEST_VISA_STATUS, SUGGEST_PROCEDURE,
    SUGGEST_LEGAL_SOURCE, SUGGEST_EMPLOYMENT_TOOL, SUGGEST_RECENT_QUERY,
    SUGGEST_CORRECTION,
)

# Category chip copy. Fixed strings — a suggestion never carries a generated
# label, so there is nothing here a model could have invented.
_SUGGEST_BADGES = {
    SUGGEST_VISA_CODE: "체류자격",
    SUGGEST_VISA_STATUS: "체류자격",
    SUGGEST_PROCEDURE: "절차",
    SUGGEST_LEGAL_SOURCE: "법령 출처",
    SUGGEST_EMPLOYMENT_TOOL: "취업 도구",
    SUGGEST_RECENT_QUERY: "최근 검색",
    SUGGEST_CORRECTION: "추천 검색어",
}


def _suggestion_row(
    kind: str,
    query: str,
    label: str,
    sublabel: str = "",
) -> Dict[str, Any]:
    return {
        "type": kind,
        "query": query,
        "label": label,
        "sublabel": sublabel,
        "badge": _SUGGEST_BADGES.get(kind, ""),
    }


def build_suggestion_rows(
    query: str,
    intent: Dict[str, Any],
    detected: Dict[str, Any],
    index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Typed next-query suggestions.

    Every row is derived from the query, the intent rules, or the loaded visa
    dataset. Nothing is generated: a secondary line only appears when the visa
    record actually carries a name, and a correction row only appears when the
    corrected code is present in the dataset. A code-shaped token we do not
    have never becomes a suggestion — that would turn "we don't have this" into
    "here it is".
    """
    index = index or {}
    rows: List[Dict[str, Any]] = []
    recognized = detected.get("recognized") or []
    unrecognized = detected.get("unrecognized") or []

    # A code-shaped token that did not resolve, next to a code that did, means
    # the input was degraded to a parent (D-2-99 -> D-2). Saying so is the whole
    # point of the Correction row: it names what was typed and what we do have.
    if unrecognized and recognized:
        typed = unrecognized[0]
        target = recognized[0]
        rows.append(_suggestion_row(
            SUGGEST_CORRECTION, target,
            f"혹시 “{target}” 을(를) 찾으셨나요?",
            f"입력하신 “{typed}” 은(는) 보유한 체류자격 목록에 없습니다",
        ))

    if recognized:
        code = recognized[0]
        record = index.get(code) or {}
        name = _record_label(record) if record else ""
        # `_record_label` falls back to the code itself; a label identical to
        # the code carries no information, so it is not shown as a subtitle.
        sub = name if name and name != code else ""
        is_sub = bool(record.get("_isSubcode"))
        if is_sub:
            # A subcode always names its parent, so the row can never be read
            # as a standalone top-level 체류자격 (CLAUDE.md code hierarchy).
            parent = record.get("_parentCode") or ""
            parent_name = _record_label(index.get(parent) or {}) if parent else ""
            if parent and parent_name and parent_name != parent:
                detail = f"{parent} · {parent_name}의 세부 체류자격"
            elif parent:
                detail = f"{parent}의 세부 체류자격"
            else:
                detail = "세부 체류자격"
        else:
            detail = "체류자격 개요"
        rows.append(_suggestion_row(
            SUGGEST_VISA_STATUS if is_sub else SUGGEST_VISA_CODE,
            code, code if not sub else f"{code} · {sub}", detail,
        ))
        for action, hint in (
            ("체류기간 연장", "연장 신청 요건과 제출 서류"),
            ("필요 서류", "신청 유형별 제출 서류"),
            ("자격변경", "다른 체류자격으로 변경하는 절차"),
        ):
            rows.append(_suggestion_row(
                SUGGEST_PROCEDURE, f"{code} {action}", f"{code} {action}", hint,
            ))

    intent_name = intent.get("intent")
    if intent_name == INTENT_EMPLOYMENT_REPORTING:
        rows.append(_suggestion_row(
            SUGGEST_EMPLOYMENT_TOOL, "취업정보 신고 직종 코드",
            "취업정보 신고 직종 코드", "직종(KSCO) 코드 찾기",
        ))
        rows.append(_suggestion_row(
            SUGGEST_EMPLOYMENT_TOOL, "근무처 변경 신고 기한",
            "근무처 변경 신고 기한", "신고 대상과 기한 확인",
        ))
    elif intent_name == INTENT_LEGAL_QUESTION:
        rows.append(_suggestion_row(
            SUGGEST_LEGAL_SOURCE, "출입국관리법 제20조",
            "출입국관리법 제20조", "법령 원문으로 확인",
        ))
        rows.append(_suggestion_row(
            SUGGEST_PROCEDURE, "체류자격 외 활동 허가",
            "체류자격 외 활동 허가", "허가 요건과 절차",
        ))
    elif intent_name == INTENT_UNKNOWN:
        rows.append(_suggestion_row(
            SUGGEST_PROCEDURE, "체류기간 연장", "체류기간 연장", "연장 신청 절차",
        ))
        rows.append(_suggestion_row(
            SUGGEST_PROCEDURE, "체류지 변경 신고", "체류지 변경 신고", "주소 변경 신고 절차",
        ))
        for code in ("D-2", "F-6"):
            record = index.get(code) or {}
            name = _record_label(record) if record else ""
            sub = name if name and name != code else ""
            rows.append(_suggestion_row(
                SUGGEST_VISA_CODE, code, code if not sub else f"{code} · {sub}",
                "체류자격 개요",
            ))

    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = row["query"]
        if key and key not in seen:
            seen.add(key)
            out.append(row)
    return out[:6]


def build_suggestions(
    query: str,
    intent: Dict[str, Any],
    detected: Dict[str, Any],
    index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    """Next-query suggestions as plain strings.

    Kept for callers that only need the query text. Derived from
    :func:`build_suggestion_rows` so the two can never drift apart.
    """
    return [row["query"] for row in build_suggestion_rows(query, intent, detected, index)]


def build_interpretation(
    query: str,
    intent: Dict[str, Any],
    detected: Dict[str, Any],
) -> Dict[str, Any]:
    """The editable "this is how we read your question" block."""
    return {
        "query": normalize_query(query),
        "intent": intent.get("intent"),
        "intentRule": intent.get("rule"),
        "confidence": intent.get("confidence"),
        "signals": intent.get("signals", []),
        "recognizedVisaCodes": detected.get("recognized", []),
        # Named explicitly so the UI can say "we do not have this code" instead of
        # rendering it as a real status.
        "unrecognizedCodeLikeTokens": detected.get("unrecognized", []),
        "editable": True,
    }


def run_unified_search(
    query: str,
    *,
    visa_data: Sequence[Dict[str, Any]],
    valid_main_codes: Set[str],
    manual_search: Optional[Callable[[str], Dict[str, Any]]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Full deterministic pass: normalize -> detect -> classify -> build results.

    ``manual_search`` is injected so this function stays pure and offline-testable;
    a failure inside it degrades to "no manual hits", never to an exception.
    """
    text = normalize_query(query)
    # Subcodes must be in the known set, otherwise a valid "D-2-1" would be
    # reported as an unrecognized token.
    visa_index = build_visa_index(visa_data)
    known_codes = set(visa_index.keys())

    detected = detect_visa_codes(text, valid_main_codes, known_codes)
    intent = classify_intent(text, detected)

    manual_hits: Dict[str, Any] = {}
    if manual_search is not None and text:
        try:
            manual_hits = manual_search(text) or {}
        except Exception:
            manual_hits = {}

    organic = build_organic_results(
        text, visa_data=visa_data, intent=intent, detected=detected,
        manual_hits=manual_hits, limit=limit,
    )
    suggestion_rows = build_suggestion_rows(text, intent, detected, visa_index)

    return {
        "query": text,
        "intent": intent.get("intent"),
        "detectedVisaCodes": detected.get("recognized", []),
        "interpretation": build_interpretation(text, intent, detected),
        "organicResults": organic,
        # Both shapes ship: `suggestionRows` drives the typed Suggestion Row UI,
        # `suggestions` stays a plain string list for existing callers.
        "suggestionRows": suggestion_rows,
        "suggestions": [row["query"] for row in suggestion_rows],
        "manualEvidence": {
            "status": manual_hits.get("status", "not_queried"),
            "approvedCount": len(manual_hits.get("approved", []) or []),
            "reviewPendingCount": len(manual_hits.get("needs_review", []) or []),
        },
        # Organic results are always available with the AI provider down; the
        # frontend must render them before any overview arrives.
        "fallbackAvailable": True,
        "resultCount": len(organic),
    }


__all__ = [
    "UNIFIED_SEARCH_VERSION", "INTENTS", "MAX_QUERY_LENGTH",
    "INTENT_EXACT_VISA_CODE", "INTENT_VISA_KEYWORD", "INTENT_VISA_SITUATION",
    "INTENT_PROCEDURE_QUESTION", "INTENT_LEGAL_QUESTION",
    "INTENT_EMPLOYMENT_REPORTING", "INTENT_FEATURE_NAVIGATION", "INTENT_UNKNOWN",
    "RESULT_STATUS_CARD", "RESULT_SUBCODE_CARD", "RESULT_PROCEDURE_CARD",
    "RESULT_LEGAL_CARD", "RESULT_EMPLOYMENT_TOOL", "RESULT_FEATURE_CARD",
    "RESULT_MANUAL_CARD",
    "normalize_query", "normalize_visa_code", "split_visa_code",
    "detect_visa_codes", "classify_intent", "build_organic_results",
    "build_suggestions", "build_suggestion_rows", "build_interpretation",
    "run_unified_search",
    "SUGGESTION_TYPES", "SUGGEST_VISA_CODE", "SUGGEST_VISA_STATUS",
    "SUGGEST_PROCEDURE", "SUGGEST_LEGAL_SOURCE", "SUGGEST_EMPLOYMENT_TOOL",
    "SUGGEST_RECENT_QUERY", "SUGGEST_CORRECTION",
]
