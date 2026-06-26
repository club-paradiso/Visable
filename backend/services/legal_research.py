"""Deterministic legal-research-depth layer for Waymaker by Paradiso.

Turns the Fast / Basic / Pro tiers (formerly answer-*speed* model tiers in
``model_policy``) into research-*depth* modes for the Legal Research feature:

    빠른 확인 / Quick check      -> "fast"
    기본 리서치 / Standard research -> "basic"  (default)
    심층 리서치 / Deep research    -> "pro"

IMPORTANT — what this module IS and IS NOT:
  * It is a DETERMINISTIC source-CHECKING scaffold. It plans retrieval (how many
    law/precedent searches, whether precedents run), derives *issues to verify*
    and *search-term candidates*, labels source strength, flags *things to check*
    (risk flags), lists *missing facts to ask the user*, and structures the
    output by depth — then points to official sources.
  * It does NOT call an LLM, does NOT invent statute/article/precedent numbers,
    does NOT state legal conclusions or eligibility, and does NOT infer facts the
    user did not provide. "Issues" and "risk flags" are framed as items to
    verify against official text, never as the answer.

Everything here is pure/stdlib so it unit-tests fully offline. Live law/precedent
retrieval is layered on top by the endpoint via the existing OC-safe adapters.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

RESEARCH_DEPTHS = ("fast", "basic", "pro")
DEFAULT_DEPTH = "basic"

RESEARCH_MODES = ("qa", "issue_spotting", "memo", "compare", "precedent_explorer")
DEFAULT_MODE_FOR_DEPTH = {"fast": "qa", "basic": "issue_spotting", "pro": "memo"}

# Concepts that are inherently dispute/refusal-heavy: matching one (or matching
# two concepts of any kind) escalates auto-selected depth to deep research.
PRO_CONCEPTS = frozenset({
    "deportation_vs_departure", "naturalization_refusal", "refugee_extension_refusal",
    "e7_occupation", "f4_h2_employment",
})

SOURCE_STRENGTHS = ("direct", "related", "background", "metadata-only")
SOURCE_STRENGTH_LABELS = {
    "ko": {"direct": "직접 근거", "related": "관련 근거", "background": "배경자료", "metadata-only": "원문 확인 필요"},
    "en": {"direct": "Direct source", "related": "Related source", "background": "Background source", "metadata-only": "Check official text"},
}

DEPTH_LABELS = {
    "ko": {"fast": "빠른 확인", "basic": "기본 리서치", "pro": "심층 리서치"},
    "en": {"fast": "Quick check", "basic": "Standard research", "pro": "Deep research"},
}

# Keywords that escalate a question to deep (pro) research. ASCII matched
# case-insensitively; Hangul matched as substrings.
PRO_TRIGGERS = (
    "판례", "불허", "취소소송", "강제퇴거", "출국명령", "난민", "귀화 불허", "행정심판", "소송",
    "appeal", "precedent", "refusal", "denial", "deportation",
)

# Pro loading steps (frontend may show these while a deep research runs).
PRO_LOADING_STEPS_KO = ["쟁점 추출 중", "법령 검색 중", "판례 검색 중", "공식자료 대조 중", "리서치 메모 작성 중"]
PRO_LOADING_STEPS_EN = ["Spotting issues", "Searching laws", "Searching precedents", "Cross-checking official materials", "Drafting research memo"]

# Pro source-card group order (by source type).
PRO_SOURCE_GROUPS = ("law", "subordinate", "precedent", "manual", "paradiso")
PRO_SOURCE_GROUP_LABELS = {
    "ko": {"law": "법령", "subordinate": "시행령·시행규칙", "precedent": "판례", "manual": "출입국 매뉴얼·공식자료", "paradiso": "Paradiso 구조화 데이터"},
    "en": {"law": "Laws", "subordinate": "Decrees & rules", "precedent": "Precedents", "manual": "Immigration manuals & official materials", "paradiso": "Paradiso structured data"},
}

SECTION_HEADINGS = {
    "fast": {
        "ko": ["빠른 요약", "관련 경로", "확인할 근거", "주의"],
        "en": ["Quick summary", "Likely routes", "Sources to check", "Caution"],
    },
    "basic": {
        "ko": ["요약", "주요 쟁점", "관련 법령·자료", "실무상 확인할 부분", "다음 확인사항", "출처", "주의"],
        "en": ["Summary", "Key issues", "Relevant laws & materials", "Points to verify in practice", "Next checks", "Sources", "Caution"],
    },
    "pro": {
        "ko": [
            "리서치 메모", "1. 쟁점", "2. 사실관계에서 중요한 부분", "3. 관련 법령",
            "4. 관련 판례 또는 판례 검색 결과", "5. 출입국 실무상 확인할 자료", "6. 적용 가능성",
            "7. 위험 신호", "8. 부족한 사실관계", "9. 다음 확인사항", "10. 출처", "주의",
        ],
        "en": [
            "Research memo", "1. Issues", "2. Key facts in the situation", "3. Relevant laws",
            "4. Relevant precedents or precedent search results", "5. Immigration practice materials to verify",
            "6. Possible application", "7. Risk flags", "8. Missing facts", "9. Next checks", "10. Sources", "Caution",
        ],
    },
}

DISCLAIMER = {
    "ko": "법령·판례 리서치는 공식 원문 확인을 돕기 위한 정리이며, 변호사·행정사의 법률 자문이나 최종 판단을 대체하지 않습니다. 실제 허가 여부와 처분의 적법성은 관계 기관의 심사와 공식 원문에 따릅니다.",
    "en": "This legal research organizes pointers to official sources. It does not replace legal advice from a qualified professional or any final decision; actual approval and the lawfulness of a disposition follow the competent authority's review and the official text.",
}


def _low(text: Optional[str]) -> str:
    return (text or "").lower()


def normalize_depth(depth: Any) -> str:
    d = str(depth or "").strip().lower()
    return d if d in RESEARCH_DEPTHS else DEFAULT_DEPTH


def normalize_mode(mode: Any) -> str:
    m = str(mode or "").strip().lower()
    return m if m in RESEARCH_MODES else ""


def normalize_locale(locale: Any) -> str:
    loc = str(locale or "").strip().lower()
    if loc == "en":
        return "en"
    return "ko"  # zh gracefully falls back to ko for this deterministic scaffold


def auto_select_depth(question: str) -> str:
    """Pick a depth from the question shape (deterministic).

    * a pro-trigger keyword (판례 / 불허 / 강제퇴거 / appeal / ...) -> pro
    * a long, multi-clause narrative -> pro
    * a very short, simple question -> fast
    * otherwise -> basic
    """
    text = (question or "").strip()
    low = _low(text)
    for kw in PRO_TRIGGERS:
        needle = kw.lower()
        if needle.isascii():
            if needle in low:
                return "pro"
        elif kw in text:
            return "pro"
    # Long / complex narrative -> pro.
    clause_markers = text.count("?") + text.count("？") + text.count(",") + text.count("、") + text.count("그리고") + text.count("동시에")
    if len(text) >= 90 or clause_markers >= 3:
        return "pro"
    # Very short, simple -> fast.
    if len(text) <= 22:
        return "fast"
    return "basic"


# ---------------------------------------------------------------------------
# Concept map — detection keyword -> issue/term/risk/missing-fact scaffolding.
# These are SEARCH-TERM and ISSUE-TO-VERIFY pointers, NOT legal requirements or
# conclusions. Each entry stays cautious ("확인", "쟁점", "검토").
# ---------------------------------------------------------------------------
_CONCEPTS: List[Dict[str, Any]] = [
    {
        "id": "deportation_vs_departure",
        "keywords": ["강제퇴거", "출국명령", "deportation", "departure order"],
        "law_terms": ["출입국관리법 강제퇴거", "출입국관리법 출국명령", "출입국관리법 시행령 강제퇴거 출국명령"],
        "prec_terms": ["강제퇴거명령 취소", "출국명령 취소"],
        "issues_ko": ["강제퇴거명령과 출국명령의 요건·효과 구분", "처분의 근거 조항과 재량 일탈·남용 여부", "불복 절차(행정심판·행정소송)와 기한"],
        "issues_en": ["Distinguishing deportation order vs departure order (grounds/effects)", "Statutory basis of the disposition and discretion abuse", "Challenge routes (administrative appeal/litigation) and deadlines"],
        "risk_ko": ["입국금지·재입국 제한 가능성", "처분 통지·송달일 기준 불복 기한 도과 위험"],
        "risk_en": ["Possible entry ban / re-entry restriction", "Risk of missing the appeal deadline counted from notice/service date"],
        "facts_ko": ["처분의 종류(강제퇴거 vs 출국명령)와 근거 조항", "처분서 송달일", "이의신청·행정심판 청구 여부"],
        "facts_en": ["Which disposition (deportation vs departure) and its statutory basis", "Date the disposition was served", "Whether an objection/appeal has been filed"],
    },
    {
        "id": "naturalization_refusal",
        "keywords": ["귀화", "국적취득", "품행단정", "naturalization"],
        "law_terms": ["국적법 귀화 요건", "국적법 시행령 귀화 품행", "국적법 일반귀화 간이귀화"],
        "prec_terms": ["귀화 불허처분 취소", "품행 단정 귀화"],
        "issues_ko": ["품행 단정 요건의 판단기준", "귀화 요건(거주기간·생계·기본소양 등) 충족 여부", "불허처분의 재량 일탈·남용"],
        "issues_en": ["Standard for the 'good conduct' requirement", "Whether naturalization requirements are met (residence period, livelihood, basic knowledge)", "Discretion abuse in a refusal"],
        "risk_ko": ["전과·출입국 위반 이력이 품행 판단에 미치는 영향", "불허 시 불복 기한"],
        "risk_en": ["Effect of criminal/immigration-violation history on the conduct assessment", "Appeal deadline if refused"],
        "facts_ko": ["귀화 유형(일반·간이·특별)", "전과·과태료·출입국 위반 이력", "거주기간과 체류자격 연속성"],
        "facts_en": ["Naturalization type (general/simplified/special)", "Criminal / fine / immigration-violation history", "Residence period and status continuity"],
    },
    {
        "id": "refugee_extension_refusal",
        "keywords": ["난민", "g-1", "행정소송", "refugee"],
        "law_terms": ["난민법 난민인정", "출입국관리법 시행령 G-1 인도적체류", "난민법 이의신청"],
        "prec_terms": ["난민불인정 취소", "체류기간 연장 불허 취소", "난민 인도적체류"],
        "issues_ko": ["체류기간 연장 불허의 근거와 재량 범위", "난민신청·이의신청·소송 단계별 체류 안정성", "행정소송 대상 적격(처분성)과 제소기간"],
        "issues_en": ["Basis and discretion scope of an extension refusal", "Stay stability across application/objection/litigation stages", "Standing (disposition character) and filing period for litigation"],
        "risk_ko": ["연장 불허로 인한 체류 단절·강제퇴거 위험", "제소기간 도과 위험"],
        "risk_en": ["Risk of stay interruption / deportation from a refusal", "Risk of missing the litigation filing period"],
        "facts_ko": ["현재 단계(1차 심사·이의신청·소송)", "불허 통지일", "G-1 세부 사유(난민신청·인도적체류 등)"],
        "facts_en": ["Current stage (first review / objection / litigation)", "Refusal notice date", "G-1 sub-reason (asylum application / humanitarian stay)"],
    },
    {
        "id": "f6_marriage",
        "keywords": ["f-6", "결혼이민", "혼인", "소득요건", "marriage"],
        "law_terms": ["출입국관리법 결혼이민 체류자격 변경", "결혼이민 소득요건 체류자격", "출입국관리법 시행규칙 결혼이민 초청"],
        "prec_terms": ["결혼이민 체류자격 불허", "혼인의 진정성"],
        "issues_ko": ["혼인의 진정성 판단 자료", "소득요건(초청인 소득) 충족 여부", "체류자격 변경 vs 연장 경로"],
        "issues_en": ["Materials assessing genuineness of the marriage", "Whether the income requirement (sponsor income) is met", "Status-change vs extension route"],
        "risk_ko": ["소득요건 미충족·혼인 단절 시 체류 불안정", "허위 혼인 의심 시 처분 위험"],
        "risk_en": ["Stay instability if income unmet or marriage ends", "Disposition risk if the marriage is suspected to be false"],
        "facts_ko": ["혼인 경위와 동거 여부", "초청인 소득·재정 입증", "자녀 유무"],
        "facts_en": ["How the marriage came about and cohabitation", "Sponsor income / financial proof", "Whether there are children"],
    },
    {
        "id": "d2_to_d10",
        "keywords": ["d-2", "유학", "졸업", "출석률", "d-10", "구직", "student"],
        "law_terms": ["출입국관리법 시행령 유학 D-2 체류자격", "구직 D-10 체류자격 변경", "체류자격 변경허가 D-10"],
        "prec_terms": ["체류자격 변경 불허", "유학 체류자격"],
        "issues_ko": ["졸업·수료 시점과 잔여 체류기간", "출석률·학사경고가 변경 심사에 미치는 영향", "D-10 변경 요건과 구직활동 입증"],
        "issues_en": ["Graduation/completion timing and remaining stay period", "Effect of attendance / academic warning on the change review", "D-10 change requirements and job-search evidence"],
        "risk_ko": ["체류기간 임박 시 변경 신청 시점 도과 위험", "출석률 문제가 성실성 판단에 미치는 영향"],
        "risk_en": ["Risk of missing the change-application window near expiry", "Effect of attendance issues on the sincerity assessment"],
        "facts_ko": ["졸업·수료 예정일", "현재 체류기간 만료일", "출석률·학점 현황"],
        "facts_en": ["Expected graduation/completion date", "Current stay expiry date", "Attendance / GPA status"],
    },
    {
        "id": "e7_occupation",
        "keywords": ["e-7", "특정활동", "직종", "고용 필요성", "학력", "경력"],
        "law_terms": ["출입국관리법 시행령 특정활동 E-7 체류자격", "E-7 직종 고용 학력 경력 요건", "특정활동 체류자격 변경허가"],
        "prec_terms": ["E-7 체류자격 불허", "특정활동 직종 적합성"],
        "issues_ko": ["직종 적합성(고시 직종 해당 여부)", "고용 필요성·대체 인력 검토", "학력·경력 요건 충족 여부"],
        "issues_en": ["Occupation suitability (whether it falls under listed jobs)", "Employment necessity / substitutability review", "Whether education/experience requirements are met"],
        "risk_ko": ["직종 분류 오인 시 불허 위험", "경력 입증 부족"],
        "risk_en": ["Refusal risk if the occupation is misclassified", "Insufficient experience proof"],
        "facts_ko": ["정확한 직종·직무 내용", "학위·전공과 직무 관련성", "경력 연수와 증빙"],
        "facts_en": ["Exact occupation / job duties", "Degree/major relevance to the job", "Years of experience and evidence"],
    },
    {
        "id": "f4_h2_employment",
        "keywords": ["f-4", "재외동포", "단순노무", "사행행위", "h-2", "방문취업"],
        "law_terms": ["재외동포의 출입국과 법적 지위에 관한 법률 취업활동", "F-4 단순노무 취업제한 고시", "출입국관리법 시행령 재외동포 H-2 방문취업"],
        "prec_terms": ["F-4 취업활동 제한", "재외동포 단순노무"],
        "issues_ko": ["F-4 취업활동 제한 범위(단순노무·사행행위 등)", "F-4와 H-2의 취업 가능 범위 비교", "제한 업종 해당 여부 확인"],
        "issues_en": ["Scope of F-4 employment restriction (manual labor, gambling, etc.)", "Comparing permitted employment scope of F-4 vs H-2", "Whether the job falls in a restricted industry"],
        "risk_ko": ["제한 업종 취업 시 체류자격 위반 위험", "업종 분류 해석 차이"],
        "risk_en": ["Status-violation risk if working in a restricted industry", "Differences in industry classification interpretation"],
        "facts_ko": ["구체적 업종·직무", "사업장 업태·종목", "근로 형태(상용·일용 등)"],
        "facts_en": ["Specific industry / job duties", "Employer business type", "Employment form (regular/daily)"],
    },
    {
        "id": "status_change_general",
        "keywords": ["체류자격 변경", "status change"],
        "law_terms": ["출입국관리법 체류자격 변경허가", "출입국관리법 시행령 체류자격 변경"],
        "prec_terms": ["체류자격 변경허가 불허"],
        "issues_ko": ["변경 가능한 체류자격 경로", "변경 요건과 구비서류", "변경 vs 연장 판단"],
        "issues_en": ["Available status-change routes", "Change requirements and documents", "Change vs extension decision"],
        "risk_ko": ["요건 미충족 시 불허", "신청 시점 도과"],
        "risk_en": ["Refusal if requirements are unmet", "Missing the application window"],
        "facts_ko": ["현재 체류자격과 목표 체류자격", "체류기간 만료일"],
        "facts_en": ["Current and target status", "Stay expiry date"],
    },
    {
        "id": "extension_general",
        "keywords": ["체류기간 연장", "연장", "extension"],
        "law_terms": ["출입국관리법 체류기간 연장허가", "출입국관리법 시행령 체류기간 연장"],
        "prec_terms": ["체류기간 연장 불허"],
        "issues_ko": ["연장 요건과 구비서류", "연장 불허 사유와 불복"],
        "issues_en": ["Extension requirements and documents", "Grounds for an extension refusal and how to challenge"],
        "risk_ko": ["만료 전 신청 시점 도과", "연장 불허로 인한 체류 단절"],
        "risk_en": ["Missing the pre-expiry application window", "Stay interruption from an extension refusal"],
        "facts_ko": ["현재 체류자격·세부코드", "체류기간 만료일"],
        "facts_en": ["Current status / sub-code", "Stay expiry date"],
    },
]

_GENERIC_ISSUE = {
    "ko": ["질문과 관련된 체류자격·절차 확인", "근거 법령·시행령·시행규칙 확인", "관할 기관 실무 자료 확인"],
    "en": ["Identify the relevant status/procedure", "Check the governing act/decree/rule", "Check the competent office's practice materials"],
}
_GENERIC_FACTS = {
    "ko": ["현재 체류자격과 세부코드", "체류기간 만료일", "관할 출입국·외국인관서"],
    "en": ["Current status and sub-code", "Stay expiry date", "Competent immigration office"],
}
_GENERIC_NEXT_KO = ["관할 출입국·외국인관서 또는 1345에 사실관계 확인", "HiKorea에서 신청 가능 절차·서류 확인", "처분이 있는 경우 처분서의 근거 법령 확인"]
_GENERIC_NEXT_EN = ["Confirm the facts with the competent office or 1345", "Check available procedures/documents on HiKorea", "If there is a disposition, check its statutory basis on the notice"]


def _match_concepts(question: str, visa_hint: Optional[str]) -> List[Dict[str, Any]]:
    hay = (question or "") + " " + (visa_hint or "")
    low = _low(hay)
    matched: List[Dict[str, Any]] = []
    for concept in _CONCEPTS:
        for kw in concept["keywords"]:
            needle = kw.lower()
            hit = (needle in low) if needle.isascii() else (kw in hay)
            if hit:
                matched.append(concept)
                break
    return matched


def _dedupe(seq: Sequence[str], limit: int) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in seq:
        s = (item or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) >= limit:
            break
    return out


def depth_budget(depth: str) -> Dict[str, Any]:
    """Retrieval budget per depth (guidance range + a conservative hard cap on
    actual API calls so we never hammer the Open Law API)."""
    d = normalize_depth(depth)
    if d == "fast":
        return {"depth": "fast", "lawRange": [1, 3], "lawCap": 2, "precedentRange": [0, 1],
                "precedentDefault": False, "precedentCap": 1}
    if d == "pro":
        return {"depth": "pro", "lawRange": [5, 10], "lawCap": 5, "precedentRange": [1, 4],
                "precedentDefault": True, "precedentCap": 3}
    return {"depth": "basic", "lawRange": [3, 6], "lawCap": 3, "precedentRange": [0, 2],
            "precedentDefault": False, "precedentCap": 2}


# ---------------------------------------------------------------------------
# Fact extraction + query localization (English question -> Korean queries)
# ---------------------------------------------------------------------------
# Korea uses uppercase status codes like F-6, D-2, D-10, E-7, G-1, H-2, plus the
# K-STAR/REGION-S pilots. Match those, not arbitrary letter-number pairs.
_VISA_CODE_RE = re.compile(r"\b([A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?)?)\b")

# English (or romanized) legal phrasing -> Korean Open-Law search anchors. Korean
# law APIs match Korean statutory terms far better than English, so an English
# question still gets Korean queries. Order: most specific phrases first.
_EN_KO_QUERY_TERMS = (
    ("deportation order", ["강제퇴거명령", "출입국관리법 강제퇴거"]),
    ("departure order", ["출국명령", "출입국관리법 출국명령"]),
    ("change of status", ["체류자격 변경", "출입국관리법 체류자격 변경허가"]),
    ("status change", ["체류자격 변경"]),
    ("extension of stay", ["체류기간 연장", "출입국관리법 체류기간 연장허가"]),
    ("good conduct", ["품행 단정", "국적법 귀화 품행"]),
    ("genuine marriage", ["혼인의 진정성", "결혼이민 체류자격"]),
    ("income requirement", ["결혼이민 소득요건"]),
    ("deportation", ["강제퇴거"]),
    ("naturalization", ["국적법 귀화", "귀화 요건"]),
    ("refugee", ["난민법", "난민 인정"]),
    ("marriage", ["결혼이민"]),
    ("graduation", ["유학 졸업 체류자격"]),
    ("student", ["유학 체류자격"]),
    ("extension", ["체류기간 연장"]),
    ("employment", ["취업활동", "고용"]),
    ("permanent resid", ["영주 F-5", "영주자격"]),
    ("appeal", ["행정심판 행정소송"]),
    ("lawsuit", ["행정소송"]),
)

# Procedure-type detection for extracted facts (KO + EN keywords -> a KO label).
_PROCEDURE_KEYWORDS = (
    (("체류자격 변경", "변경허가", "change of status", "status change"), "체류자격 변경허가"),
    (("체류기간 연장", "연장", "extension"), "체류기간 연장허가"),
    (("불허", "취소", "refusal", "denial", "revocation"), "불허·취소 처분 대응"),
    (("강제퇴거", "deportation"), "강제퇴거"),
    (("출국명령", "departure order"), "출국명령"),
    (("귀화", "국적취득", "naturalization"), "귀화"),
    (("거소", "거소신고", "residence registration"), "국내거소신고"),
    (("취업", "고용", "employment"), "취업·고용 활동"),
    (("사증", "비자 발급", "visa issuance"), "사증발급"),
    (("행정심판", "행정소송", "소송", "appeal", "lawsuit", "litigation"), "불복(행정심판·행정소송)"),
)


def english_korean_queries(question: str) -> List[str]:
    """Korean Open-Law search anchors derived from English/romanized phrasing.

    Returns [] for a Korean-only question (the concept map already covers it).
    """
    low = (question or "").lower()
    out: List[str] = []
    for needle, terms in _EN_KO_QUERY_TERMS:
        if needle in low:
            out.extend(terms)
    return out


def extract_facts(question: str, visa_hint: Optional[str] = None) -> Dict[str, Any]:
    """Deterministically extract structured research facts from a question.

    Pure. Used to enrich query generation + the research plan. Never infers facts
    the user did not state — it only surfaces what the text explicitly contains.
    """
    text = (question or "") + " " + (visa_hint or "")
    low = text.lower()
    visa_statuses = _dedupe(_VISA_CODE_RE.findall(text), 8)
    concepts = _match_concepts(question, visa_hint)

    procedure_types: List[str] = []
    for needles, label in _PROCEDURE_KEYWORDS:
        for nd in needles:
            hit = (nd.lower() in low) if nd.isascii() else (nd in text)
            if hit:
                procedure_types.append(label)
                break

    legal_issues: List[str] = []
    factual_risk: List[str] = []
    for c in concepts:
        legal_issues += c["issues_ko"]
        factual_risk += c["risk_ko"]

    likely_needs = ["law", "regulation", "manual", "precedent"] if concepts else ["law", "manual"]

    return {
        "visaStatuses": visa_statuses,
        "procedureTypes": _dedupe(procedure_types, 6),
        "legalIssues": _dedupe(legal_issues, 8),
        "factualRiskSignals": _dedupe(factual_risk, 6),
        "likelySourceNeeds": likely_needs,
    }


# ---------------------------------------------------------------------------
# Source language metadata (official Korean text is never disguised as English)
# ---------------------------------------------------------------------------
def _source_notice(locale_raw: Any) -> str:
    """Per-UI-language notice that an official source is Korean (not machine-translated)."""
    l = str(locale_raw or "").strip().lower()
    if l == "en":
        return "Official source text may be in Korean"
    if l.startswith("zh"):
        return "官方原文可能为韩语"
    return ""  # Korean UI: the original Korean source is shown as-is.


def localize_sources(cards: List[Dict[str, Any]], locale_raw: Any) -> None:
    """Tag each retrieved source card (in place) with honest language metadata.

    law.go.kr text is Korean-only, so we mark ``language='ko'`` and, in a non-KO
    UI, attach a clear ``translationNotice`` — we never fabricate a machine
    translation of the legal text or pretend it is an official English version.
    """
    notice = _source_notice(locale_raw)
    for c in (cards or []):
        if not isinstance(c, dict):
            continue
        c["language"] = "ko"
        c["originalLanguage"] = "ko"
        c["isMachineTranslated"] = False
        if notice:
            c["translationNotice"] = notice


def build_research_plan(
    question: str,
    *,
    depth: Any = None,
    mode: Any = None,
    visa_status_hint: Optional[str] = None,
    include_precedents: Optional[bool] = None,
    include_manuals: Optional[bool] = None,
    locale: Any = "ko",
) -> Dict[str, Any]:
    """Deterministic research plan: chosen depth/mode, issues, and law/precedent
    search-term candidates with a retrieval budget. Pure → unit-testable."""
    q = (question or "").strip()
    requested_depth = normalize_depth(depth) if depth else ""
    concepts = _match_concepts(q, visa_status_hint)
    auto = not requested_depth
    chosen_depth = requested_depth or auto_select_depth(q)
    # Concept-based escalation (auto only): a dispute/refusal-heavy concept, or two
    # or more distinct concepts, signals a complex narrative -> deep research.
    if auto and chosen_depth != "pro":
        concept_ids = {c["id"] for c in concepts}
        if (concept_ids & PRO_CONCEPTS) or len(concept_ids) >= 2:
            chosen_depth = "pro"
    chosen_mode = normalize_mode(mode) or DEFAULT_MODE_FOR_DEPTH[chosen_depth]
    lang = normalize_locale(locale)
    budget = depth_budget(chosen_depth)
    issues_ko: List[str] = []
    issues_en: List[str] = []
    law_terms: List[str] = []
    prec_terms: List[str] = []
    risk_ko: List[str] = []
    risk_en: List[str] = []
    facts_ko: List[str] = []
    facts_en: List[str] = []
    for c in concepts:
        issues_ko += c["issues_ko"]; issues_en += c["issues_en"]
        law_terms += c["law_terms"]; prec_terms += c["prec_terms"]
        risk_ko += c["risk_ko"]; risk_en += c["risk_en"]
        facts_ko += c["facts_ko"]; facts_en += c["facts_en"]

    # English / romanized phrasing -> Korean Open-Law anchors, so an English
    # question still retrieves Korean law text (Korean APIs match Korean terms).
    law_terms += english_korean_queries(q)

    if not concepts:
        # No concept matched — still produce a Korean query + generic issues.
        if not law_terms:
            try:
                from services.law_grounding import build_law_search_query  # local import to avoid cycle
                law_terms = [build_law_search_query(q) or "출입국관리법"]
            except Exception:
                law_terms = ["출입국관리법"]
        issues_ko = _GENERIC_ISSUE["ko"][:]; issues_en = _GENERIC_ISSUE["en"][:]
        facts_ko = _GENERIC_FACTS["ko"][:]; facts_en = _GENERIC_FACTS["en"][:]

    if include_precedents is None:
        run_precedents = budget["precedentDefault"]
    else:
        run_precedents = bool(include_precedents)
    include_manuals_flag = True if include_manuals is None else bool(include_manuals)

    return {
        "question": q,
        "depth": chosen_depth,
        "depthAutoSelected": auto,
        "mode": chosen_mode,
        "locale": lang,
        "localeRaw": str(locale or "ko"),
        "extractedFacts": extract_facts(q, visa_status_hint),
        "budget": budget,
        "lawTerms": _dedupe(law_terms, budget["lawCap"]),
        "precedentTerms": _dedupe(prec_terms or law_terms, budget["precedentCap"]),
        "runPrecedents": run_precedents,
        "includeManuals": include_manuals_flag,
        "matchedConcepts": [c["id"] for c in concepts],
        "issuesKo": _dedupe(issues_ko, 8),
        "issuesEn": _dedupe(issues_en, 8),
        "riskKo": _dedupe(risk_ko, 6),
        "riskEn": _dedupe(risk_en, 6),
        "missingFactsKo": _dedupe(facts_ko, 6),
        "missingFactsEn": _dedupe(facts_en, 6),
    }


def classify_law_strength(card: Dict[str, Any], law_terms: Sequence[str]) -> str:
    title = (card.get("title") or "")
    if any(t and t.split()[0] in title for t in law_terms):
        return "direct" if card.get("snippet") else "related"
    if card.get("snippet"):
        return "related"
    if card.get("sourceUrl"):
        return "background"
    return "metadata-only"


_PREC_GRADE_TO_STRENGTH = {"direct": "direct", "contextual": "related", "background": "background", "unavailable": "metadata-only"}


def classify_precedent_strength(card: Dict[str, Any]) -> str:
    grade = (card.get("citationGrade") or "").strip().lower()
    if grade in _PREC_GRADE_TO_STRENGTH:
        return _PREC_GRADE_TO_STRENGTH[grade]
    # Frontend-normalized precedent cards carry no grade; infer from content.
    if card.get("summary") and card.get("caseNumber"):
        return "related"
    if card.get("caseNumber") or card.get("sourceUrl"):
        return "background"
    return "metadata-only"


def _law_group(card: Dict[str, Any]) -> str:
    t = (card.get("type") or "") + (card.get("title") or "")
    if "시행령" in t or "시행규칙" in t or "decree" in t.lower() or "rule" in t.lower():
        return "subordinate"
    return "law"


def build_research_result(
    plan: Dict[str, Any],
    *,
    law_results: Optional[List[Dict[str, Any]]] = None,
    precedent_results: Optional[List[Dict[str, Any]]] = None,
    paradiso_sources: Optional[List[Dict[str, Any]]] = None,
    retrieval_available: bool = True,
) -> Dict[str, Any]:
    """Assemble the depth-structured, source-grounded research scaffold.

    Pure given the plan + retrieved cards. Adds source-strength labels, groups
    sources by type (pro), and surfaces issues / risk flags / missing facts /
    next checks / limitations — all framed as items to verify, never as legal
    conclusions. No fact is inferred; no citation is fabricated.
    """
    lang = plan.get("locale", "ko")
    depth = plan.get("depth", "basic")
    law_terms = plan.get("lawTerms") or []
    laws = list(law_results or [])
    precs = list(precedent_results or [])
    para = list(paradiso_sources or [])

    strength_labels = SOURCE_STRENGTH_LABELS[lang]
    for c in laws:
        s = classify_law_strength(c, law_terms)
        c["strength"] = s
        c["strengthLabel"] = strength_labels[s]
    for c in precs:
        s = classify_precedent_strength(c)
        c["strength"] = s
        c["strengthLabel"] = strength_labels[s]
    # Honest language metadata: law.go.kr text is Korean; in a non-KO UI attach a
    # clear "official source may be in Korean" notice (never a fake translation).
    locale_raw = plan.get("localeRaw", lang)
    localize_sources(laws, locale_raw)
    localize_sources(precs, locale_raw)

    issues = plan.get("issuesKo") if lang == "ko" else plan.get("issuesEn")
    risks = plan.get("riskKo") if lang == "ko" else plan.get("riskEn")
    missing = plan.get("missingFactsKo") if lang == "ko" else plan.get("missingFactsEn")
    next_checks = _GENERIC_NEXT_KO if lang == "ko" else _GENERIC_NEXT_EN

    limitations = []
    if lang == "ko":
        limitations.append("이 정리는 검색·구조화 결과이며 법적 결론이 아닙니다. 쟁점·위험 신호는 확인 대상입니다.")
        if not retrieval_available:
            limitations.append("법령 검색 서비스(LAW_API_OC)가 설정되지 않아 실시간 원문은 검색하지 못했습니다. 아래 검색어로 공식 자료에서 직접 확인하세요.")
        if depth == "pro":
            limitations.append("판례 검색 결과는 후보이며, 관련성·최신성은 원문에서 직접 확인해야 합니다.")
    else:
        limitations.append("This is a search/structuring result, not a legal conclusion. Issues and risk flags are items to verify.")
        if not retrieval_available:
            limitations.append("The legal search service (LAW_API_OC) is not configured, so live text was not retrieved. Use the search terms below to check official sources directly.")
        if depth == "pro":
            limitations.append("Precedent results are candidates; verify relevance and currency against the official text.")

    pro_groups = None
    if depth == "pro":
        grouped: Dict[str, List[Dict[str, Any]]] = {g: [] for g in PRO_SOURCE_GROUPS}
        for c in laws:
            grouped[_law_group(c)].append(c)
        grouped["precedent"] = precs
        grouped["paradiso"] = para
        labels = PRO_SOURCE_GROUP_LABELS[lang]
        pro_groups = [
            {"group": g, "label": labels[g], "cards": grouped[g]}
            for g in PRO_SOURCE_GROUPS if grouped[g]
        ]

    result: Dict[str, Any] = {
        "ok": True,
        "depth": depth,
        "depthLabel": DEPTH_LABELS[lang][depth],
        "depthAutoSelected": plan.get("depthAutoSelected", False),
        "mode": plan.get("mode"),
        "locale": lang,
        "question": plan.get("question", ""),
        "headings": SECTION_HEADINGS[depth][lang],
        "issues": issues or [],
        "lawSearchTerms": law_terms,
        "precedentSearchTerms": plan.get("precedentTerms") or [],
        "laws": laws,
        "precedents": precs,
        "runPrecedents": plan.get("runPrecedents", False),
        "missingFacts": (missing or []) if depth != "fast" else [],
        "riskFlags": (risks or []) if depth != "fast" else [],
        "nextChecks": next_checks,
        "limitations": limitations,
        "sourceGroups": pro_groups,
        "extractedFacts": plan.get("extractedFacts") or {},
        "sourceLanguageNotice": _source_notice(locale_raw),
        "disclaimer": DISCLAIMER[lang],
        "retrievalAvailable": retrieval_available,
    }
    if depth == "pro":
        result["loadingSteps"] = PRO_LOADING_STEPS_KO if lang == "ko" else PRO_LOADING_STEPS_EN
    return result
