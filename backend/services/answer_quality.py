"""General AI answer-quality contract for Paradiso /api/ask.

This module is the single source of truth for *how* Paradiso shapes an answer
once the grounding pipeline has decided *what* sources are available. It is
deliberately deterministic and side-effect free: every function here can be
unit-tested without a live LLM, and the public ``classify_answer_quality``
result is surfaced as non-secret response metadata so the frontend can render
honest source/state chips.

The goals (see docs/data/AI_ANSWER_EXPERIENCE_QUALITY_GATE_2026_05.md):

* Distinguish *source state* (how strongly the answer is grounded) from
  *user intent* (what shape of answer the question calls for), then fold both
  into prompt directives that produce a readable, modern-LLM-style answer.
* Never let related comparison statuses (e.g. D-2 / D-4 for an H-1 study
  question) look like direct source grounding.
* Keep cautions to one place, avoid mixed-language artifacts, and lead with the
  practical answer instead of a wall of warnings.

Nothing here changes provider/model selection — that stays in
``paradiso_backend`` untouched.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

# Bumped whenever the answer contract / prompt directives change in a way the
# frontend or smoke harness should be able to detect. Surfaced as
# ``answer_style_version`` in the response metadata.
ANSWER_STYLE_VERSION = "2026-05-quality-v2-legal-analysis"

# ---------------------------------------------------------------------------
# Answer quality modes (source state)
# ---------------------------------------------------------------------------
SOURCE_CONFIRMED = "source_confirmed"
SOURCE_ASSISTED = "source_assisted"
SOURCE_LIMITED = "source_limited"
SOURCE_UNAVAILABLE = "source_unavailable"
GENERIC_ADVISORY = "generic_advisory"

_VALID_MODES = (
    SOURCE_CONFIRMED,
    SOURCE_ASSISTED,
    SOURCE_LIMITED,
    SOURCE_UNAVAILABLE,
    GENERIC_ADVISORY,
)

# Coarse confidence label per mode. Intentionally not a probability — it only
# tells the UI how much weight to give the answer.
_CONFIDENCE_BY_MODE = {
    SOURCE_CONFIRMED: "high",
    SOURCE_ASSISTED: "moderate",
    SOURCE_LIMITED: "low",
    SOURCE_UNAVAILABLE: "low",
    GENERIC_ADVISORY: "none",
}

# ---------------------------------------------------------------------------
# Question types (user intent) — Part D templates
# ---------------------------------------------------------------------------
Q_ACTIVITY_ON_STATUS = "activity_on_status"      # "Can I do X on status Y?"
Q_DOCUMENTS_NEEDED = "documents_needed"          # "What documents do I need?"
Q_STATUS_CHANGE = "status_change"                # "Can I change from A to B?"
Q_DEADLINE_REPORT = "deadline_report"            # deadline / registration / report
Q_SPECIAL_SITUATION = "special_situation"        # "I have a special situation"
Q_GENERAL = "general"

# ---------------------------------------------------------------------------
# Canonical Korean -> English helper glossary (Part B / Part I).
# These are NON-AUTHORITATIVE helper translations. Official Korean terms stay
# authoritative; the English rendering only aids comprehension in English mode.
# ---------------------------------------------------------------------------
CANONICAL_TERMS = {
    "체류자격": "sojourn status",
    "체류자격외활동": "activities outside the scope of status",
    "체류자격 변경": "change of sojourn status",
    "국내거소신고": "domestic residence report",
    "활동범위": "permitted scope of activities",
    "관광취업": "working holiday / H-1",
}

# Chinese legal fragments that must NOT appear in an English-mode answer
# (Part I terminology guard). These are common simplified/traditional tokens
# that show up in mixed-language artifacts like ``sojourn资格``.
_CJK_LEGAL_FRAGMENTS = (
    "资格", "資格", "签证", "簽證", "滞留", "滯留", "居留",
    "在留", "许可", "許可", "申请", "申請", "签发", "簽發",
)

# Hangul block — used to flag Korean fragments leaking into a Chinese-mode
# answer (we allow Korean *inside parentheses* as an official-term reference).
_HANGUL_RE = re.compile(r"[가-힣]")
_CJK_RE = re.compile(r"[一-鿿]")


# ---------------------------------------------------------------------------
# Language helpers
# ---------------------------------------------------------------------------
def normalize_lang(lang: Optional[str]) -> str:
    """Normalize a request ``lang`` hint to one of ko / en / zh-CN / zh-TW.

    Anything unrecognized maps to ``""`` (answer in the user's language).
    """
    norm = (lang or "").strip().lower().replace("_", "-")
    if norm == "ko":
        return "ko"
    if norm == "en":
        return "en"
    if norm in {"zh", "zh-cn", "zh-hans", "zh-sg"}:
        return "zh-CN"
    if norm in {"zh-tw", "zh-hant", "zh-hk", "zh-mo"}:
        return "zh-TW"
    return ""


def answer_language_instruction(lang: Optional[str]) -> str:
    """One-line answer-language instruction with anti-mixed-language guardrails.

    Replaces the previous ko/en-only helper so Chinese modes are explicit and
    every mode forbids cross-script artifacts (Part I).
    """
    norm = normalize_lang(lang)
    if norm == "ko":
        return (
            "- 한국어로 자연스럽게 답하십시오. 공식 행정·법령 용어는 한국어 원문을 유지하고,"
            " 불필요한 영어 표현은 섞지 마십시오."
        )
    if norm == "en":
        return (
            "- Answer in natural English. Do not insert Chinese characters into English"
            " terms (no artifacts like \"sojourn资格\"). You may keep an official Korean"
            " term in parentheses where it aids clarity, e.g. \"sojourn status (체류자격)\"."
        )
    if norm == "zh-CN":
        return (
            "- 用自然的简体中文回答。术语保持简体中文，不要混入繁体字或英文片段；"
            "如有帮助，可在括号内保留韩文官方术语，例如 \"居留资格(체류자격)\"。"
        )
    if norm == "zh-TW":
        return (
            "- 用自然的繁體中文回答。術語保持繁體中文，不要混入簡體字或英文片段；"
            "如有幫助，可在括號內保留韓文官方術語，例如 \"居留資格(체류자격)\"。"
        )
    return (
        "- Answer in the same language as the user's question, and keep terminology"
        " in that single language (no mixed-script artifacts)."
    )


def glossary_lines(lang: Optional[str]) -> str:
    """English-mode canonical helper glossary block (empty for other modes)."""
    if normalize_lang(lang) != "en":
        return ""
    rows = "\n".join(f"  - {ko} = {en}" for ko, en in CANONICAL_TERMS.items())
    return (
        "[Canonical helper translations — English mode]\n"
        "Use these non-authoritative English renderings for Korean terms when"
        " they appear; keep the Korean term in parentheses where useful:\n"
        f"{rows}"
    )


# ---------------------------------------------------------------------------
# Question-type classification (Part D)
# ---------------------------------------------------------------------------
_DOC_HINTS = (
    "what documents", "which documents", "documents do i need", "required documents",
    "필요한 서류", "구비서류", "제출서류", "서류가 무엇", "서류는", "需要什么材料",
    "需要哪些材料", "需要的材料", "需要什麼文件", "需要哪些文件",
)
_ACTIVITY_HINTS = (
    "can i ", "am i allowed", "may i ", "is it allowed", "able to",
    "할 수 있", "가능한가", "가능할까", "해도 되", "수강", "可以", "能不能", "能否",
)
_DEADLINE_HINTS = (
    "deadline", "due date", "how many days", "grace period", "register", "registration",
    "report", "신고", "기한", "유예", "며칠", "등록", "期限", "几天", "幾天", "申报", "申報",
)
_SPECIAL_HINTS = (
    "my situation", "special situation", "in my case", "what if", "i recently",
    "제 상황", "특수한", "사정이", "경우인데", "我的情况", "我的情況", "特殊情况", "特殊情況",
)
_CHANGE_HINTS = (
    "change from", "change to", "switch from", "switch to", "change status",
    "change of status", "transfer to",
    "바꿀", "바꾸", "변경", "전환", "改成", "转换", "轉換", "更改", "变更", "變更",
)
# "A에서 B로" / "A to B" status-change framing between two visa-like codes.
_A_TO_B_RE = re.compile(
    r"[A-Z]-?\d[\w-]*\s*(?:에서|->|→|to)\s*[A-Z]-?\d", re.IGNORECASE
)


def classify_question_type(prompt: str, task_type: Optional[str]) -> str:
    """Map a question to one of the Part D templates.

    Uses the already-detected ``task_type`` first (authoritative), then falls
    back to light keyword heuristics on the raw prompt. Conservative: when in
    doubt, returns the lowest-commitment template that fits.
    """
    text = (prompt or "").lower()
    raw = prompt or ""
    tt = (task_type or "").lower()

    # A documents question is the most specific intent and wins over everything
    # except an explicit deadline framing handled below.
    if any(h in text for h in _DOC_HINTS):
        return Q_DOCUMENTS_NEEDED

    # Status-change framing: from task detection, change keywords, or an
    # "A -> B" code pattern. This must beat the broad activity heuristic so that
    # "Can I change from A to B?" is not mis-read as an activity question.
    is_workplace = "workplace" in tt
    if (
        ("status_change" in tt)
        or (not is_workplace and "change" in tt)
        or any(h in text for h in _CHANGE_HINTS)
        or _A_TO_B_RE.search(raw)
    ):
        return Q_STATUS_CHANGE

    if any(h in text for h in _DEADLINE_HINTS):
        return Q_DEADLINE_REPORT
    if any(h in text for h in _SPECIAL_HINTS):
        return Q_SPECIAL_SITUATION
    # "Can I do X on status Y" / activity-scope phrasing.
    if any(h in text for h in _ACTIVITY_HINTS):
        return Q_ACTIVITY_ON_STATUS
    return Q_GENERAL


# ---------------------------------------------------------------------------
# Related-status detection (Part F)
# ---------------------------------------------------------------------------
_STUDY_HINTS = (
    "summer semester", "summer course", "seasonal course", "winter semester",
    "take a course", "take courses", "university course", "study", "studying",
    "enroll", "class", "credit",
    "계절학기", "수강", "학기", "대학 강의", "학점", "수업", "공부",
    "暑期", "学期", "學期", "选课", "選課", "修课", "修課", "学习", "學習",
)
_WORK_HOLIDAY_HINTS = (
    "h-1", "h1", "working holiday", "관광취업", "워킹홀리데이", "打工度假",
)


def detect_related_statuses(
    prompt: str,
    visa_code: Optional[str],
    task_type: Optional[str],
) -> List[str]:
    """Return comparison statuses worth verifying — NOT source grounding.

    The canonical case: a study/course question asked from a non-study status
    (e.g. H-1 working holiday) should surface D-2 (degree study) and D-4
    (non-degree / language study) as *related statuses to verify*, never as a
    source that proves the asked-about status permits the activity.
    """
    text = (prompt or "").lower()
    code = (visa_code or "").upper()
    is_study = any(h in text for h in _STUDY_HINTS)
    if not is_study:
        return []
    # If the question is already squarely a study-status question, the manual
    # grounding (if any) covers it; related comparison statuses are only useful
    # when the asker is on a non-study status.
    if code.startswith("D-2") or code.startswith("D-4"):
        return []
    is_non_study_holder = bool(code) and not code.startswith("D-")
    mentions_work_holiday = any(h in text for h in _WORK_HOLIDAY_HINTS)
    if is_non_study_holder or mentions_work_holiday or not code:
        return ["D-2", "D-4"]
    return []


# ---------------------------------------------------------------------------
# Official-confirmation questions (Part D / Part E)
# ---------------------------------------------------------------------------
_H1_STUDY_CONFIRMATION_QUESTIONS = [
    "Is the course credit-bearing?",
    "Is it degree-related?",
    "How many weeks / hours is it?",
    "Is study the main purpose of your stay?",
    "Will you also work under H-1 at the same time?",
    "Does the university require D-2 / D-4 or another status?",
    "Would immigration treat this as activities outside the scope of status (체류자격외활동) or require a change of status?",
]


def official_confirmation_questions(
    question_type: str,
    visa_code: Optional[str],
    prompt: str,
    related_statuses: Sequence[str],
) -> List[str]:
    """Exact questions the user should ask 1345 / HiKorea / immigration office.

    These are deterministic and template-driven so tests can assert their
    presence without depending on LLM wording.
    """
    text = (prompt or "").lower()
    is_study = any(h in text for h in _STUDY_HINTS)

    # Study/activity-scope case. Keep H-1-specific work-history wording only for H-1;
    # otherwise the deterministic fallback would leak unrelated H-1 context into
    # G-1/F-2/E-7 study questions.
    if question_type == Q_ACTIVITY_ON_STATUS and is_study:
        if (visa_code or "").upper().startswith("H-1"):
            return list(_H1_STUDY_CONFIRMATION_QUESTIONS)
        return [
            "Is the course credit-bearing?",
            "Is it degree-related or part of formal enrollment?",
            "Is it audit/non-credit, language training, or a regular university course?",
            "How many weeks / hours is it, and would study become the main purpose of stay?",
            "Does the school require D-2 / D-4 or another status?",
            "Would immigration treat this as activities outside the scope of status (체류자격외활동) or require a change of status?",
        ]

    if question_type == Q_ACTIVITY_ON_STATUS:
        return [
            "Is the activity within the permitted scope of activities (활동범위) for your current status?",
            "Does it count as activities outside the scope of status (체류자격외활동)?",
            "Do you need prior permission or a change of sojourn status (체류자격 변경)?",
            "Is there a reporting duty, and what event starts the clock?",
        ]
    if question_type == Q_STATUS_CHANGE:
        return [
            "What is your current sojourn status (체류자격) and sub-code?",
            "How did you enter Korea (entry route / visa)?",
            "How long is your remaining period of stay?",
            "What is the purpose and intended start date of the new activity?",
            "Are you eligible to change in Korea, or must you re-apply from abroad?",
        ]
    if question_type == Q_DOCUMENTS_NEEDED:
        return [
            "Which exact procedure and sub-code applies to your case?",
            "Are any of the documents conditional on your specific situation?",
            "Does the competent immigration office require anything additional locally?",
        ]
    if question_type == Q_DEADLINE_REPORT:
        return [
            "What exact event starts the deadline (entry, change, address change)?",
            "What is the confirmed time limit for your specific status?",
            "Where and how must the report be filed (HiKorea / in person)?",
        ]
    if question_type == Q_SPECIAL_SITUATION:
        return [
            "What is your current sojourn status (체류자격) and remaining stay?",
            "What changed in your situation, and when?",
            "What outcome are you trying to achieve?",
        ]
    return []


# ---------------------------------------------------------------------------
# Core classification (Part A / Part C)
# ---------------------------------------------------------------------------
def classify_answer_quality(
    *,
    prompt: str,
    visa_code: Optional[str],
    task_type: Optional[str],
    manual_grounding_present: bool,
    structured_requirements_present: bool,
    procedure_variant_present: bool,
    law_grounding_used: bool,
    law_grounding_status: str,
    manual_to_law_fallback_used: bool,
    law_intent: bool,
    provider_configured: bool = True,
) -> Dict[str, Any]:
    """Fold grounding state + user intent into the answer-quality contract.

    Returns a flat, JSON-serializable dict of non-secret metadata fields. The
    precedence below is conservative: a stronger mode is only claimed when the
    corresponding source state is genuinely present.
    """
    question_type = classify_question_type(prompt, task_type)
    related = detect_related_statuses(prompt, visa_code, task_type)

    if manual_grounding_present or structured_requirements_present:
        mode = SOURCE_CONFIRMED
    elif law_grounding_used:
        mode = SOURCE_ASSISTED
    elif procedure_variant_present:
        # Scenario-specific local catalog context: useful, but needs review and
        # is weaker than confirmed manual grounding.
        mode = SOURCE_ASSISTED
    elif manual_to_law_fallback_used or related:
        # Legal/activity-scope context or related comparison statuses exist, but
        # there is no direct source proving the asked-about outcome.
        mode = SOURCE_LIMITED
    elif law_intent or (law_grounding_status in {"unavailable", "disabled"}):
        mode = SOURCE_UNAVAILABLE
    else:
        mode = GENERIC_ADVISORY

    # A substantive immigration question with no source should be framed as
    # honestly source-unavailable, not as a casual generic-advisory reply.
    if mode == GENERIC_ADVISORY and question_type in (
        Q_ACTIVITY_ON_STATUS, Q_STATUS_CHANGE, Q_DOCUMENTS_NEEDED, Q_DEADLINE_REPORT,
    ):
        mode = SOURCE_UNAVAILABLE

    grounded_answer_limited = mode in (
        SOURCE_LIMITED, SOURCE_UNAVAILABLE, GENERIC_ADVISORY,
    )
    requires_official_confirmation = mode != SOURCE_CONFIRMED

    confirmation_qs: List[str] = []
    if requires_official_confirmation:
        confirmation_qs = official_confirmation_questions(
            question_type, visa_code, prompt, related
        )

    return {
        "answer_quality_mode": mode,
        "source_confidence_level": _CONFIDENCE_BY_MODE[mode],
        "requires_official_confirmation": requires_official_confirmation,
        "official_confirmation_questions": confirmation_qs,
        "related_statuses_not_sources": related,
        "grounded_answer_limited": grounded_answer_limited,
        "answer_style_version": ANSWER_STYLE_VERSION,
        "question_type": question_type,
    }


# ---------------------------------------------------------------------------
# Prompt directives (Part A / B / C / D / E / H)
# ---------------------------------------------------------------------------
_MODE_SOURCE_DIRECTIVE = {
    SOURCE_CONFIRMED: (
        "Source state: a verified manual / source-confirmed requirement supports"
        " this answer. Give a clear, practical answer and cite the source briefly."
        " Note that the competent office may add or waive items case by case."
    ),
    SOURCE_ASSISTED: (
        "Source state: there is useful manual or legal context, but official"
        " confirmation is still needed. Separate confirmed facts from"
        " interpretation, and say what still needs to be verified."
    ),
    SOURCE_LIMITED: (
        "Source state: only related or partial information exists; direct source"
        " support for the exact question is incomplete. Lead with the strongest"
        " legally supportable practical posture, then state the source limitation."
        " Do not present related statuses or general legal context as direct"
        " authority for the asked status."
    ),
    SOURCE_UNAVAILABLE: (
        "Source state: verified manual/law grounding is unavailable for this"
        " question. Lead with limited practical preparation/risk posture, then"
        " clearly state the source gap. Do not invent holdings, documents, fees,"
        " deadlines, or final outcomes; provide exact facts/questions for"
        " 1345 / HiKorea / the competent immigration office."
    ),
    GENERIC_ADVISORY: (
        "Source state: general reference only. Keep the answer short, label it as"
        " general information, recommend official confirmation, and avoid long"
        " speculative scenario trees."
    ),
}

_QUESTION_TYPE_DIRECTIVE = {
    Q_ACTIVITY_ON_STATUS: (
        "Question type — \"Can I do X on status Y?\": (1) lead with a direct but"
        " cautious answer; (2) name the main risk (permitted scope of activities,"
        " activities outside the scope of status, change of status, or a reporting"
        " duty); (3) say what information would change the answer; (4) give the"
        " exact questions to ask 1345 / HiKorea / the immigration office;"
        " (5) end with one short source-status note."
    ),
    Q_DOCUMENTS_NEEDED: (
        "Question type — \"What documents do I need?\": if a source-confirmed list"
        " exists, show it clearly and group documents by purpose, marking"
        " conditional ones. Do NOT invent missing documents. If it is not"
        " source-confirmed, say so plainly and give the official-confirmation route."
    ),
    Q_STATUS_CHANGE: (
        "Question type — \"Can I change from A to B?\": do not promise eligibility."
        " Explain the route and its risks, ask for current status, entry route,"
        " remaining stay, and purpose, then give the official confirmation steps."
    ),
    Q_DEADLINE_REPORT: (
        "Question type — deadline / registration / report: give a confirmed"
        " deadline ONLY if it is source-backed; if you rely on a common rule,"
        " label it clearly as a general rule to verify. Explain what event starts"
        " the clock, suggest a calendar reminder, and add an official-confirmation"
        " note."
    ),
    Q_SPECIAL_SITUATION: (
        "Question type — special situation: briefly restate the issue, identify the"
        " 2-4 key variables that drive the outcome, avoid a final answer when facts"
        " are missing, and give the exact next questions plus checklist-style steps."
    ),
    Q_GENERAL: "",
}


def build_answer_directives(
    quality: Dict[str, Any],
    *,
    lang: Optional[str],
) -> str:
    """Assemble the answer-quality prompt block injected into the final prompt.

    This block instructs the model to write a readable, modern-LLM answer that
    matches the source state and question type. It deliberately does NOT force a
    fixed six-section template; it asks for a flexible structure that scales with
    question complexity (Part A).
    """
    mode = quality.get("answer_quality_mode", GENERIC_ADVISORY)
    qtype = quality.get("question_type", Q_GENERAL)
    related = quality.get("related_statuses_not_sources") or []
    confirmation_qs = quality.get("official_confirmation_questions") or []

    parts: List[str] = ["[Answer quality contract]"]

    # General structure (flexible, not a rigid template).
    parts.append(
        "Write like a careful, helpful modern assistant. Structure (adapt to the"
        " question, do not pad):\n"
        "1. Lead with the direct, practical answer in the first one or two sentences.\n"
        "2. Briefly explain why — the key rule or risk, in plain language.\n"
        "3. Say what this means for the user / what would change the answer.\n"
        "4. Give a concrete next step or the exact questions to ask.\n"
        "5. End with ONE short source/verification note.\n"
        "Keep it mobile-readable: short paragraphs, few headings. A short answer"
        " is better for simple questions; only go deep for genuinely complex"
        " scenarios. Tone: calm, concise, not robotic, not legalistic unless"
        " necessary."
    )

    if qtype in {Q_ACTIVITY_ON_STATUS, Q_STATUS_CHANGE, Q_DEADLINE_REPORT, Q_SPECIAL_SITUATION}:
        parts.append(
            "For legal/procedure questions, use these concise sections when useful:"
            " Practical answer; Legal issue; Source-based analysis; What the"
            " sources do not directly answer; Questions to confirm with"
            " 1345/HiKorea/competent office; Source status / basis summary. Do not"
            " force this template on simple source-confirmed document checklists."
        )

    # Anti-patterns (Part B) + warning de-duplication (Part H).
    parts.append(
        "Avoid: starting with a long \"currently known facts\" section; excessive"
        " headings; repeating the same caution in more than one place; vague \"it"
        " may depend\" without saying what it depends on; invented checklists;"
        " legal certainty unless directly source-confirmed; saying \"possible"
        " paths\" when the source state is weak; generic filler; fake precision."
        " State each caution once."
    )

    parts.append(_MODE_SOURCE_DIRECTIVE[mode])

    # Limited / unavailable source state: forbid unsupported certainty wording
    # and require legal-analysis-first framing rather than failure-first prose.
    if mode in (SOURCE_LIMITED, SOURCE_UNAVAILABLE):
        parts.append(
            "Because direct sources are limited, start with the strongest"
            " legally supportable practical posture from the backend-prepared"
            " legal_analysis — NOT with \"Paradiso cannot verify...\","
            " \"Whether you can...\", \"It depends...\", or \"Specific manual"
            " guidance was not found...\". Keep the framing specific to the"
            " extracted immigration_facts, legal_issue_types, proposed_activity_type,"
            " main_issue, sub_issues, decisive_facts, and official-confirmation"
            " questions. Do not reuse study/course wording unless the issue is"
            " study_on_non_study_status or the activity is credit_bearing_study,"
            " formal_enrollment, non_credit_audit, or language_training. Do NOT use"
            " unsupported certainty wording (\"may be permissible\", \"is allowed\","
            " \"you can\", \"no need to\", \"does not require\", \"guaranteed\","
            " \"will be approved\", \"will be denied\", \"automatically\")."
            " official confirmation is required before acting. Do not claim final"
            " eligibility, permission, approval, denial, illegality, or invent"
            " document lists."
        )

    qdir = _QUESTION_TYPE_DIRECTIVE.get(qtype, "")
    if qdir:
        parts.append(qdir)

    if related:
        parts.append(
            "Related statuses to verify (NOT a source that answers the question): "
            + ", ".join(related)
            + ". Present them only as comparison statuses the user may need to"
            " check; never imply they prove what the asked-about status permits,"
            " and never label them as a manual source."
        )

    if confirmation_qs:
        joined = "\n".join(f"  - {q}" for q in confirmation_qs)
        parts.append(
            "Include these exact official-confirmation questions for the user to"
            " ask 1345 / HiKorea / the competent immigration office:\n" + joined
        )

    gloss = glossary_lines(lang)
    if gloss:
        parts.append(gloss)

    parts.append(answer_language_instruction(lang))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Terminology guard (Part I) — used by tests and the smoke harness
# ---------------------------------------------------------------------------
def scan_mixed_language_artifacts(text: str, lang: Optional[str]) -> List[str]:
    """Return a list of mixed-language artifact findings for ``text``.

    English mode: any CJK legal fragment (资格, 签证, 滞留, ...) is an artifact.
    Korean parenthetical terms are allowed because they are official references.

    Chinese modes: Hangul *outside* parentheses is an artifact (inside
    parentheses it is an allowed official-term reference).

    This is intentionally conservative — it is a guard against the observed
    ``sojourn资格`` class of bug, not a full linguistic validator. Returns an
    empty list when ``text`` is clean.
    """
    findings: List[str] = []
    if not text:
        return findings
    norm = normalize_lang(lang)

    if norm == "en":
        for frag in _CJK_LEGAL_FRAGMENTS:
            if frag in text:
                findings.append(frag)
        return findings

    if norm in {"zh-CN", "zh-TW"}:
        # Strip parenthetical content (both ASCII and full-width brackets) so an
        # official Korean term in parentheses is not flagged.
        stripped = re.sub(r"[\(（][^\)）]*[\)）]", "", text)
        if _HANGUL_RE.search(stripped):
            findings.append("hangul_outside_parentheses")
        return findings

    return findings


# ---------------------------------------------------------------------------
# Unsupported-confidence phrase guard (Part N) — used by tests + smoke harness
# ---------------------------------------------------------------------------
# Phrases that over-claim certainty. In a source_limited / source_unavailable
# answer these must be softened to wording like "may be assessed differently,
# but official confirmation is required".
RISKY_CONFIDENCE_PHRASES = (
    "may be permissible",
    "is allowed",
    "you can",
    "no need to",
    "does not require",
    "definitely",
    "guaranteed",
    "will be approved",
    "will be denied",
    "automatically",
    "always",
    "never",
)

SAFER_CONFIDENCE_PHRASES = (
    "may be assessed differently, but official confirmation is required",
    "paradiso cannot confirm from currently verified sources that",
    "check whether this requires permission or a change of sojourn status",
    "confirm with 1345, hikorea, or the competent immigration office",
)

# Modes where over-confident wording is unsafe.
_RISKY_FLAG_MODES = {SOURCE_LIMITED, SOURCE_UNAVAILABLE}


def scan_unsupported_confidence_phrases(text: str, mode: str) -> List[str]:
    """Return risky certainty phrases found in ``text`` for a weak source mode.

    Only flags in ``source_limited`` / ``source_unavailable`` modes — a
    ``source_confirmed`` answer is allowed to be definite. Case-insensitive.
    Returns an empty list when the answer is clean or the mode tolerates
    certainty. Deterministic; safe for tests and the smoke harness.
    """
    if not text or mode not in _RISKY_FLAG_MODES:
        return []
    low = text.lower()
    return [phrase for phrase in RISKY_CONFIDENCE_PHRASES if phrase in low]
