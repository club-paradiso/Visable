"""Waymaker Trust & Safety guardrail — first-stage deterministic classifier.

This module is the FIRST safety gate for the Paradiso/Waymaker ``/api/ask``
flow. It runs BEFORE any model generation and decides whether a request may
proceed to the normal legal-information pipeline, or must be safely refused.

Design principles
-----------------
1. **Deterministic, rule-based, no LLM.** The initial safety decision must be
   reproducible, auditable, and free of provider latency/availability. An LLM
   is never consulted to make the block/allow decision.

2. **Behavior-focused, never identity-focused.** The classifier looks only at
   what the *current request asks the assistant to do*. It must NOT score risk
   by nationality, race, ethnicity, religion, or visa status, and it must NOT
   label a person as a criminal, false refugee applicant, or violator.

3. **Facilitation, not topic.** Merely mentioning refugees, G-1, asylum, a
   nationality, Jeju, fraud, or crime in a lawful informational context is
   always allowed. A request is only refused when it asks the assistant to
   *produce or enable* concrete wrongdoing (fabricate a claim, forge a
   document, evade enforcement, harm a person, abuse someone's personal data).
   The discriminator is the presence of a *facilitation signal* — an imperative
   "do the wrongdoing for me / tell me how to do the wrongdoing" pattern — not
   the presence of a sensitive keyword.

The module is intentionally dependency-free (standard library only) so it can
be imported and unit-tested without FastAPI/httpx and reused from scripts.

Returned decision (``SafetyDecision.to_dict()``)::

    {
      "action": "allow" | "warn" | "block" | "escalate" | "emergency_review",
      "category": "SAFE_LEGAL_INFO" | "IMMIGRATION_FRAUD_FACILITATION"
                | "DOCUMENT_FRAUD" | "UNAUTHORIZED_WORK_BROKERING"
                | "LAW_ENFORCEMENT_EVASION" | "VIOLENT_CRIME_OR_EXPLOITATION"
                | "PERSONAL_DATA_ABUSE" | "SPAM_OR_SCAM",
      "severity": 0 | 1 | 2 | 3 | 4 | 5,
      "reason": "...",
      "matched_signals": [...]
    }

The matched_signals are short *pattern labels* (never the raw user text), so
they are safe to log for manual review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Pattern, Sequence, Tuple

SAFETY_VERSION = "waymaker-safety-rules-1"

# ---------------------------------------------------------------------------
# Actions / categories / severity
# ---------------------------------------------------------------------------
ACTION_ALLOW = "allow"
ACTION_WARN = "warn"
ACTION_BLOCK = "block"
ACTION_ESCALATE = "escalate"
ACTION_EMERGENCY = "emergency_review"

# Actions that must NOT reach the model (a refusal is returned instead).
BLOCKING_ACTIONS = frozenset({ACTION_BLOCK, ACTION_ESCALATE, ACTION_EMERGENCY})
# Actions that warrant a server-side safety event for manual review.
LOGGED_ACTIONS = frozenset({ACTION_BLOCK, ACTION_ESCALATE, ACTION_EMERGENCY})

CAT_SAFE = "SAFE_LEGAL_INFO"
CAT_IMMIGRATION_FRAUD = "IMMIGRATION_FRAUD_FACILITATION"
CAT_DOCUMENT_FRAUD = "DOCUMENT_FRAUD"
CAT_WORK_BROKERING = "UNAUTHORIZED_WORK_BROKERING"
CAT_LE_EVASION = "LAW_ENFORCEMENT_EVASION"
CAT_VIOLENT = "VIOLENT_CRIME_OR_EXPLOITATION"
CAT_PERSONAL_DATA = "PERSONAL_DATA_ABUSE"
CAT_SPAM_SCAM = "SPAM_OR_SCAM"

# Higher number = more acute. Used to pick the dominant signal when several
# categories match the same request.
_SEVERITY_BY_ACTION = {
    ACTION_ALLOW: 0,
    ACTION_WARN: 1,
    ACTION_BLOCK: 3,
    ACTION_ESCALATE: 4,
    ACTION_EMERGENCY: 5,
}

# Tie-break priority when two signals share the same severity. Acute
# person-safety risks win over paperwork-style risks.
_CATEGORY_PRIORITY = {
    CAT_VIOLENT: 6,
    CAT_PERSONAL_DATA: 5,
    CAT_IMMIGRATION_FRAUD: 4,
    CAT_DOCUMENT_FRAUD: 3,
    CAT_LE_EVASION: 2,
    CAT_WORK_BROKERING: 1,
    CAT_SPAM_SCAM: 0,
}


@dataclass
class SafetyDecision:
    action: str = ACTION_ALLOW
    category: str = CAT_SAFE
    severity: int = 0
    reason: str = "no safety signals matched"
    matched_signals: List[str] = field(default_factory=list)
    # Internal, non-serialized helpers for the calling backend.
    language: str = "ko"

    @property
    def blocked(self) -> bool:
        """True when the request must not reach the model."""
        return self.action in BLOCKING_ACTIONS

    @property
    def should_log(self) -> bool:
        return self.action in LOGGED_ACTIONS

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "category": self.category,
            "severity": self.severity,
            "reason": self.reason,
            "matched_signals": list(self.matched_signals),
        }


@dataclass(frozen=True)
class _Signal:
    category: str
    label: str
    action: str
    severity: int
    regex: Pattern
    # "evasion_only" signals are the only ones eligible for the lawful-intent
    # warn downgrade (see classify_request). Forgery/fabrication/violent/
    # personal-data signals are NEVER downgraded by a "but legally" phrase.
    downgradable: bool = False


def _c(pattern: str) -> Pattern:
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


# ---------------------------------------------------------------------------
# Facilitation signals — each encodes BOTH a wrongdoing object AND a
# "do it / tell me how" intent. Mere informational mentions never match.
# ---------------------------------------------------------------------------
_FACILITATION_SIGNALS: Tuple[_Signal, ...] = (
    # ---- VIOLENT_CRIME_OR_EXPLOITATION (most acute) ----------------------
    _Signal(
        CAT_VIOLENT, "violent.harm_person_method", ACTION_EMERGENCY, 5,
        _c(r"(찾아가|찾아서|찾아내|쫓아가|따라가).{0,30}(해치|죽이|폭행|상해|때리|보복|혼내|없애)"),
    ),
    _Signal(
        CAT_VIOLENT, "violent.harm_intent_method", ACTION_EMERGENCY, 5,
        _c(r"(해치|죽이|폭행|상해|보복|없애버리|없애려).{0,25}(방법|어떻게|싶|려고|려는|할\s*거|하고\s*싶|알려)"),
    ),
    _Signal(
        CAT_VIOLENT, "violent.track_to_harm", ACTION_EMERGENCY, 5,
        _c(r"(해치|죽이|보복|복수|없애).{0,20}(추적|위치|주소|찾아|어디\s*사는)"
           r"|(추적|위치추적|어디\s*사는지|주소).{0,20}(해치|죽이|보복|복수)"),
    ),
    _Signal(
        CAT_VIOLENT, "violent.harm_person_method.en", ACTION_EMERGENCY, 5,
        # A real violence verb must co-occur with a person target. "find/locate/
        # track down" alone are NOT treated as violent (they only matter when a
        # violence verb is also present, which the verb branch below captures).
        _c(r"\b(hurt|kill|attack|harm|beat\s+up|murder|stab|assault|"
           r"get\s+rid\s+of|take\s+revenge\s+on)\b.{0,25}"
           r"\b(him|her|them|someone|that\s+person|my\s+ex|a\s+person|people|my\s+\w+)\b"
           r"|\b(track\s+down|hunt\s+down|stalk)\b.{0,30}\band\b.{0,15}"
           r"\b(hurt|kill|harm|attack|beat|murder)\b"),
    ),
    _Signal(
        CAT_VIOLENT, "exploitation.trafficking", ACTION_ESCALATE, 5,
        _c(r"인신\s*매매|장기\s*매매|성\s*매매.{0,6}(알선|강요|시키)|강제\s*(노동|매춘|성매매|결혼)"
           r"|착취.{0,8}(방법|시키|하는)|감금.{0,8}(방법|시키|하는)"
           r"|미성년.{0,10}(성|착취|매매|알선)"),
    ),
    _Signal(
        CAT_VIOLENT, "exploitation.trafficking.en", ACTION_ESCALATE, 5,
        _c(r"\b(human\s+)?traffick(ing|er|ed)?\b"
           r"|\b(sexually\s+|sexual\s+)?exploit(ing|ation)?\b.{0,18}"
           r"\b(someone|people|workers?|women|children|a\s+minor|minors?|girls?)\b"
           r"|\bforced\s+(labou?r|prostitution|marriage)\b"
           r"|\bhold\b.{0,15}\bcaptive\b"),
    ),
    _Signal(
        CAT_VIOLENT, "violent.stalk_threat", ACTION_ESCALATE, 4,
        _c(r"스토킹.{0,8}(방법|어떻게)|미행.{0,8}(방법|어떻게)|몰래.{0,10}(미행|위치\s*추적|따라다)"
           r"|협박\s*(편지|문구|메시지|메일|방법|하는\s*법)|죽여\s*버리|가만\s*안\s*둬|보복\s*협박"),
    ),
    _Signal(
        CAT_VIOLENT, "violent.stalk_threat.en", ACTION_ESCALATE, 4,
        _c(r"\bhow\s+to\s+stalk\b|\bstalk\s+(him|her|them|someone)\b"
           r"|\b(write|send|make)\b.{0,12}\b(threat|threatening)\b"
           r"|\b(track|follow)\b.{0,12}\b(secretly|without\s+them\s+knowing)\b"),
    ),

    # ---- IMMIGRATION_FRAUD_FACILITATION ---------------------------------
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.fabricate_refugee_claim", ACTION_BLOCK, 3,
        _c(r"(난민|망명|박해|보호\s*신청|난민\s*사유|보호\s*사유).{0,15}"
           r"(지어내|꾸며|만들어|만들어줘|날조|조작|그럴듯하게|가짜로|허위로|거짓으로)"
           r"|(지어내|꾸며|날조|조작|그럴듯하게\s*만들|가짜로\s*만들).{0,15}"
           r"(난민|망명|박해|사유|스토리|사연|이야기|진술)"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.fabricate_refugee_claim.en", ACTION_BLOCK, 3,
        _c(r"\b(fabricate|make\s+up|invent|forge|fake)\b.{0,18}"
           r"\b(refugee|asylum|persecution)\b.{0,12}\b(claim|story|narrative|reason|case|application)\b"
           r"|\b(refugee|asylum)\b.{0,12}\b(story|claim|narrative)\b.{0,12}\b(fabricate|made?\s*up|invent|fake)\b"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.coach_interview_lie", ACTION_BLOCK, 3,
        _c(r"(출입국|이민|비자|난민|영사|공관).{0,12}(면접|인터뷰|심사).{0,15}"
           r"(거짓말|거짓|허위|지어).{0,10}(답변|대답|진술|스크립트|짜|준비)"
           r"|(면접|인터뷰).{0,12}(거짓말|거짓).{0,10}(답변|대답|짜|스크립트)"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.coach_interview_lie.en", ACTION_BLOCK, 3,
        _c(r"\b(lie|lying|false\s+answers?|coach\s+me|script)\b.{0,18}"
           r"\b(immigration|visa|asylum|consular)\b.{0,12}\binterview\b"
           r"|\b(immigration|visa|asylum)\b.{0,12}\binterview\b.{0,18}\b(lie|lying|false\s+answers?)\b"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.overstay_status_abuse", ACTION_BLOCK, 3,
        _c(r"(관광|단기|무비자|방문|여행).{0,6}(비자|입국|체류).{0,22}"
           r"(버티|눌러앉|불법\s*체류|오래\s*(머무|체류|있))"
           r"|버티는\s*(방법|법|꿀팁|팁)|눌러앉는\s*(방법|법)"
           r"|불법\s*체류.{0,10}(방법|버티|팁|들키지)"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.overstay_status_abuse.en", ACTION_BLOCK, 3,
        _c(r"\bhow\s+to\s+overstay\b|\boverstay\b.{0,15}\b(without|undetected|legally\s+impossible)\b"
           r"|\btourist\s+visa\b.{0,25}\b(stay|overstay|never\s+leave|disappear)\b"
           r"|\bsham\b.{0,10}\b(marriage|asylum|claim)\b"),
    ),
    _Signal(
        CAT_IMMIGRATION_FRAUD, "imm.sham_marriage", ACTION_BLOCK, 3,
        _c(r"위장\s*결혼.{0,10}(방법|서류|하는\s*법|꾸|만들)"
           r"|가짜\s*결혼.{0,10}(방법|서류|하는\s*법)"),
    ),

    # ---- DOCUMENT_FRAUD --------------------------------------------------
    _Signal(
        CAT_DOCUMENT_FRAUD, "doc.forge_document", ACTION_BLOCK, 3,
        _c(r"(위조|변조|날조|조작).{0,10}"
           r"(서류|문서|계약서|고용계약|증명서|초청장|진단서|재직증명|졸업증명|통장|잔고|도장|직인|서명|사인|문구|여권|비자)"
           r"|(서류|문서|계약서|고용계약|증명서|초청장|진단서|재직증명|졸업증명|통장|잔고증명|도장|직인)"
           r".{0,10}(위조|변조|날조|조작)"),
    ),
    _Signal(
        CAT_DOCUMENT_FRAUD, "doc.make_fake_document", ACTION_BLOCK, 3,
        # A fake-document NOUN plus an explicit production/request intent. The
        # make/request verb is REQUIRED so informational prose like
        # "허위 서류 제출은 처벌됩니다" (submitting false documents is punishable)
        # or "고용계약서가 가짜인지 확인하는 방법" (how to check if a contract is fake)
        # is NOT flagged — only "make me / write me a fake document" is.
        _c(r"(가짜|허위|위조된|허위의|거짓으로).{0,12}"
           r"(서류|문서|계약서|고용계약서?|재직증명서?|초청장|진단서|졸업증명서?|통장\s*사본|잔고증명서?|증명서|명세서|진술서)"
           r".{0,14}(만들|작성|발급|꾸며|꾸미|제작|준비해|구해|구하|뽑아|써\s*줘|써줘|해\s*줘|해줘|달라|주세요)"
           r"|(고용계약서|재직증명서|초청장|진단서|잔고증명서|통장\s*사본).{0,10}(가짜로|허위로|위조해|위조한|조작해|날조해)"),
    ),
    _Signal(
        CAT_DOCUMENT_FRAUD, "doc.forge_document.en", ACTION_BLOCK, 3,
        # forge/counterfeit/fabricate are themselves production verbs → standalone
        # near a document noun. "fake/forged" need a production/request verb so
        # "what if I submit a fake document" stays informational (allowed).
        _c(r"\b(forge|forging|forged|counterfeit|fabricat(?:e|ing))\b.{0,22}"
           r"\b(document|contract|certificate|invitation|invitation\s+letter|letter|"
           r"statement|bank\s+statement|payslip|passport|visa|stamp|seal|signature|diploma)\b"
           r"|\b(make|create|write|produce|need|get|provide|give|help\s+me\s+(?:make|create|get|write))\b"
           r".{0,18}\b(fake|forged|counterfeit|phony|bogus)\b.{0,12}"
           r"\b(document|contract|certificate|invitation|letter|statement|passport|diploma|payslip)\b"),
    ),

    # ---- LAW_ENFORCEMENT_EVASION (downgradable when "but legally") -------
    _Signal(
        CAT_LE_EVASION, "evasion.avoid_crackdown_work", ACTION_BLOCK, 3,
        _c(r"단속.{0,8}(안\s*걸리|안걸리|피하|벗어|걸리지\s*않|들키지\s*않|면하)"
           r"|(안\s*걸리고|안걸리고|들키지\s*않고|걸리지\s*않고|몰래).{0,12}(일하|취업|근무|체류|머무|숨|돈\s*벌)"),
        downgradable=True,
    ),
    _Signal(
        CAT_LE_EVASION, "evasion.go_dark", ACTION_BLOCK, 3,
        _c(r"잠적하는\s*(방법|법)|잠수\s*타는\s*(방법|법)|불심검문.{0,8}피하"
           r"|추적.{0,6}피하는|출입국.{0,8}(단속|추적).{0,8}피하|강제\s*퇴거.{0,8}(피하|면하)"),
        downgradable=True,
    ),
    _Signal(
        CAT_LE_EVASION, "evasion.en", ACTION_BLOCK, 3,
        _c(r"\b(avoid|evade|dodge|escape|get\s+around|slip\s+past)\b.{0,25}"
           r"\b(immigration|police|enforcement|crackdown|detection|deportation|raid|authorities|checkpoint)\b"
           r"|\bwork\b.{0,12}\bwithout\s+getting\s+caught\b"
           r"|\b(stay|fly)\b.{0,8}\bunder\s+the\s+radar\b"),
        downgradable=True,
    ),

    # ---- UNAUTHORIZED_WORK_BROKERING (brokering => escalate) ------------
    _Signal(
        CAT_WORK_BROKERING, "broker.illegal_work", ACTION_ESCALATE, 4,
        _c(r"(불법|미등록|무허가|불법체류자?).{0,8}(취업|노동|근로|인력).{0,12}(알선|중개|소개|브로커|파견|연결)"
           r"|(여러\s*명|여러명|다수|단체|여럿).{0,12}(취업|일자리|일거리|불법\s*취업).{0,12}(알선|중개|소개|연결)"
           r"|위장\s*취업.{0,8}알선|불법\s*파견.{0,8}(방법|업체)"),
    ),
    _Signal(
        CAT_WORK_BROKERING, "broker.illegal_work.en", ACTION_ESCALATE, 4,
        _c(r"\b(broker|arrange|recruit|place|supply)\b.{0,20}"
           r"\b(illegal|undocumented|unauthori[sz]ed)\b.{0,15}\b(work|workers?|jobs?|labou?r|employment)\b"),
    ),

    # ---- PERSONAL_DATA_ABUSE --------------------------------------------
    _Signal(
        CAT_PERSONAL_DATA, "pii.dig_up_person", ACTION_BLOCK, 3,
        _c(r"(여권\s*번호|외국인\s*등록\s*번호|외국인등록번호|주민\s*등록\s*번호|주민번호|집\s*주소|실제\s*주소|"
           r"전화번호|휴대폰\s*번호|연락처|개인\s*정보|신상\s*정보).{0,15}"
           r"(알아내|알아내줘|찾아내|찾아줘|캐내|캐|빼내|털어|뒷조사|추적|조회해)"
           r"|신상\s*털|신상털기|뒷조사\s*(해|하는\s*방법|방법)"),
    ),
    _Signal(
        CAT_PERSONAL_DATA, "pii.dox.en", ACTION_BLOCK, 3,
        _c(r"\bdox(x)?(ing|ed)?\b"
           r"|\b(find|look\s*up|get|obtain|track\s+down|dig\s+up)\b.{0,20}"
           r"\b(someone'?s|his|her|their|a\s+person'?s)\b.{0,18}"
           r"\b(passport\s+number|home\s+address|real\s+address|phone\s+number|"
           r"alien\s+registration|personal\s+(info|information|data))\b"),
    ),
)

# Escalators bump a block-level paperwork/PII signal to escalate (organized /
# at-scale / for-profit abuse: multiple applicants, selling, in bulk).
_ESCALATOR_SIGNALS: Tuple[Tuple[str, Pattern], ...] = (
    ("scale.multiple_applicants",
     _c(r"여러\s*명|여러명|신청자\s*들|명단|단체로|대량|다수의|여럿|손님들|고객들|업체\s*운영")),
    ("scale.for_sale",
     _c(r"팔아|팔\s*거|판매|장사|돈\s*받고|대행으로\s*돈|수수료\s*받고")),
    ("scale.en",
     _c(r"\b(multiple|several|many|bulk|in\s+bulk|clients?|customers?)\b"
        r"|\bsell(ing)?\b|\bfor\s+(money|profit|a\s+fee)\b")),
)

# Explicit lawful-alternative framing. ONLY downgrades an evasion-only block
# to a warn (e.g. "how can I work legally instead of dodging enforcement?").
# Never downgrades forgery/fabrication/violent/PII/brokering.
_LAWFUL_FRAMING = _c(
    r"합법(적)?(으로|인\s*방법|적인\s*방법|적으로\s*하는)"
    r"|적법(하게|한\s*방법)"
    r"|불법\s*아니|불법\s*없이|법\s*테두리|법적으로\s*문제\s*없"
    r"|\blegal(ly)?\b|\blawful(ly)?\b|\bwithin\s+the\s+law\b|\bproper\s+(visa|way)\b"
)


def detect_language(text: str, lang_hint: Optional[str] = None) -> str:
    """Best-effort language pick for the refusal copy: 'ko' or 'en'.

    Korea-focused platform → default to Korean. An explicit English hint or a
    message with Hangul absent and Latin letters present resolves to English.
    """
    hint = (lang_hint or "").strip().lower()
    if hint.startswith("en"):
        return "en"
    if hint.startswith("ko") or hint.startswith("zh"):
        return "ko"
    if re.search(r"[가-힣]", text or ""):
        return "ko"
    # No Korean characters and at least a few Latin letters → treat as English.
    if re.search(r"[A-Za-z]", text or ""):
        return "en"
    return "ko"


def _iter_prior_user_texts(history: Optional[Sequence]) -> List[str]:
    """Defensively extract prior *user* message texts from a loose history list.

    Accepts strings or dicts ({role, content/text/message}). Never raises.
    """
    out: List[str] = []
    if not history:
        return out
    try:
        for item in history:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                role = str(item.get("role") or item.get("speaker") or "").lower()
                if role and role not in {"user", "human"}:
                    continue
                text = item.get("content") or item.get("text") or item.get("message") or ""
                if isinstance(text, str) and text.strip():
                    out.append(text)
    except Exception:  # pragma: no cover - history is untrusted/optional
        return out
    return out


def classify_request(
    text: str,
    lang: Optional[str] = None,
    history: Optional[Sequence] = None,
) -> SafetyDecision:
    """Classify a single request. Pure, deterministic, never raises.

    ``history`` (optional) is the recent conversation; prior user turns that hit
    the same fraud/forgery family let the classifier recognize *repeated*
    attempts and escalate them for manual review.
    """
    language = detect_language(text or "", lang)
    raw = text or ""

    matches = [s for s in _FACILITATION_SIGNALS if s.regex.search(raw)]
    if not matches:
        return SafetyDecision(
            action=ACTION_ALLOW,
            category=CAT_SAFE,
            severity=0,
            reason="no facilitation signals; treated as lawful information request",
            matched_signals=[],
            language=language,
        )

    # Dominant signal: highest severity, then category priority.
    matches.sort(
        key=lambda s: (_SEVERITY_BY_ACTION[s.action], _CATEGORY_PRIORITY.get(s.category, 0)),
        reverse=True,
    )
    top = matches[0]
    matched_labels = [s.label for s in matches]
    matched_categories = {s.category for s in matches}

    action = top.action
    category = top.category
    severity = top.severity
    reason_bits = [f"matched {top.label}"]

    # Organized / at-scale / for-profit abuse → escalate (paperwork + PII only).
    escalator_hits = [name for name, rx in _ESCALATOR_SIGNALS if rx.search(raw)]
    if (
        action == ACTION_BLOCK
        and category in {CAT_DOCUMENT_FRAUD, CAT_IMMIGRATION_FRAUD, CAT_PERSONAL_DATA, CAT_WORK_BROKERING}
        and escalator_hits
    ):
        action = ACTION_ESCALATE
        severity = max(severity, 4)
        matched_labels.extend(escalator_hits)
        reason_bits.append("organized/at-scale indicators present")

    # Repeated fraud/forgery attempts across the conversation → escalate.
    if action == ACTION_BLOCK and category in {CAT_DOCUMENT_FRAUD, CAT_IMMIGRATION_FRAUD}:
        prior = _iter_prior_user_texts(history)
        repeats = 0
        for prev in prior:
            for s in _FACILITATION_SIGNALS:
                if s.category == category and s.regex.search(prev):
                    repeats += 1
                    break
        if repeats >= 1:
            action = ACTION_ESCALATE
            severity = max(severity, 4)
            matched_labels.append("pattern.repeated_attempt")
            reason_bits.append(f"repeated same-category attempts in session ({repeats})")

    # Lawful-alternative downgrade: ONLY when every matched signal is an
    # evasion-only signal AND the user explicitly asked for the legal route.
    if (
        action == ACTION_BLOCK
        and matched_categories == {CAT_LE_EVASION}
        and all(s.downgradable for s in matches)
        and _LAWFUL_FRAMING.search(raw)
    ):
        action = ACTION_WARN
        severity = 1
        matched_labels.append("framing.lawful_alternative")
        reason_bits.append("explicit lawful-alternative framing → continue with caution")

    return SafetyDecision(
        action=action,
        category=category,
        severity=severity,
        reason="; ".join(reason_bits),
        matched_signals=_dedupe(matched_labels),
        language=language,
    )


def _dedupe(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# Refusal copy (neutral, non-accusatory). KO + EN per the policy.
# ---------------------------------------------------------------------------
REFUSAL_IMMIGRATION_KO = (
    "그 요청은 허위 진술, 허위서류 제출, 체류자격 남용 또는 불법취업을 돕는 내용일 수 있어 답변할 수 없습니다. "
    "합법적인 체류자격, 난민신청 절차, 취업 가능 여부, 피해자 보호 및 공식 상담 경로에 대한 일반 정보는 안내할 수 있습니다."
)
REFUSAL_IMMIGRATION_EN = (
    "I can't help create false statements, fabricated refugee claims, forged documents, unauthorized work "
    "arrangements, or ways to misuse immigration procedures. I can help explain lawful visa options, refugee "
    "procedures, work authorization rules, victim support, and official consultation channels."
)
REFUSAL_VIOLENT_KO = (
    "타인에게 위해를 가하거나 범죄를 실행, 은폐, 추적, 협박하는 방법은 도울 수 없습니다. "
    "누군가 즉시 위험한 상황이라면 112 또는 가까운 경찰서에 신고해야 합니다. "
    "본인이 누군가를 해칠 것 같다면 즉시 그 장소에서 떨어지고 주변 사람이나 긴급기관에 도움을 요청하세요."
)
REFUSAL_VIOLENT_EN = (
    "I can't help with harming someone, committing a crime, hiding a crime, stalking, threats, or exploitation. "
    "If someone is in immediate danger, contact local emergency services. If you feel you may hurt someone, "
    "leave the situation and seek urgent help from people nearby or emergency services."
)

# Safe alternatives shown under "대신 안내할 수 있는 정보 / What I can help with instead".
_ALT_IMMIGRATION_KO = [
    "합법적인 체류자격·비자 종류와 요건",
    "난민신청 절차와 심사 흐름에 대한 일반 정보",
    "취업 가능 여부와 근무처 규정(합법적 범위)",
    "피해자 보호·상담: 1345(외국인종합안내), 1366(여성긴급전화)",
    "공식 상담 경로: HiKorea(hikorea.go.kr), 관할 출입국·외국인관서",
]
_ALT_IMMIGRATION_EN = [
    "Lawful visa/status options and their requirements",
    "General information on the refugee/asylum application process",
    "Whether and how you may work lawfully under a given status",
    "Victim support: 1345 (immigration help line), 1366 (women's helpline)",
    "Official channels: HiKorea (hikorea.go.kr), the competent immigration office",
]
_ALT_VIOLENT_KO = [
    "긴급 위험 시: 112(경찰), 119(구조·구급)",
    "가정폭력·성폭력 피해: 1366(여성긴급전화), 112",
    "이주민 상담: 1345(외국인종합안내센터)",
    "안전 확보 후 가까운 사람이나 전문기관에 도움 요청",
]
_ALT_VIOLENT_EN = [
    "Immediate danger: 112 (police), 119 (rescue/ambulance)",
    "Domestic/sexual violence support: 1366 (women's helpline), 112",
    "Migrant support: 1345 (immigration help line)",
    "Once safe, reach out to someone you trust or a professional service",
]


def refusal_copy(decision: SafetyDecision) -> Tuple[str, List[str]]:
    """Return ``(refusal_text, safe_alternatives)`` for a blocking decision."""
    is_en = decision.language == "en"
    if decision.category == CAT_VIOLENT:
        text = REFUSAL_VIOLENT_EN if is_en else REFUSAL_VIOLENT_KO
        alts = _ALT_VIOLENT_EN if is_en else _ALT_VIOLENT_KO
    else:
        # Immigration/document/work/evasion/PII all share the immigration-style
        # neutral refusal + lawful alternatives.
        text = REFUSAL_IMMIGRATION_EN if is_en else REFUSAL_IMMIGRATION_KO
        alts = _ALT_IMMIGRATION_EN if is_en else _ALT_IMMIGRATION_KO
    return text, list(alts)


def warn_caution(decision: SafetyDecision) -> str:
    """Short neutral caution appended when a request is allowed with a warning."""
    if decision.language == "en":
        return (
            "Note: This is general guidance toward lawful options only. It is not a way to "
            "avoid enforcement. Confirm specifics with 1345 / HiKorea / the competent immigration office."
        )
    return (
        "참고: 아래 안내는 단속 회피가 아니라 합법적인 자격·절차 확보 관점의 일반 정보입니다. "
        "구체적인 사항은 1345 / HiKorea / 관할 출입국·외국인관서에 확인하세요."
    )


# ---------------------------------------------------------------------------
# Post-generation sanity check (defense-in-depth, conservative)
# ---------------------------------------------------------------------------
# A small subset of the most acute facilitation categories. A compliant model
# essentially never emits these; informational answers about penalties/fraud do
# NOT match because the patterns require facilitation specificity, not topic.
_POSTGEN_CATEGORIES = frozenset({CAT_VIOLENT, CAT_DOCUMENT_FRAUD, CAT_IMMIGRATION_FRAUD})


def post_generation_review(answer_text: str) -> Optional[SafetyDecision]:
    """Re-scan a model answer for egregious facilitation content it should
    never produce. Returns a SafetyDecision when the answer must be withheld,
    otherwise None. Never raises.
    """
    try:
        if not answer_text or not answer_text.strip():
            return None
        decision = classify_request(answer_text)
        if (
            decision.action in BLOCKING_ACTIONS
            and decision.category in _POSTGEN_CATEGORIES
            and decision.severity >= 3
        ):
            decision.reason = "post_generation: model output matched a facilitation signal — " + decision.reason
            return decision
    except Exception:  # pragma: no cover - must never break the answer path
        return None
    return None
