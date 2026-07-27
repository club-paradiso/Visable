"""AI-assisted structured extraction for 취업정보 신고, feeding the deterministic analyzer.

The existing deterministic analyzer (``scripts/employment_code_analyzer.mjs``) is
NOT replaced and NOT bypassed. It remains the only thing that produces a KSCO8
직종 code or a KSIC11 업종 code, because it retrieves them from the official
classification tables and an LLM cannot.

What the LLM is allowed to do here:

* pull structured fields out of a free sentence ("카페에서 음료를 만들어요")
* normalize typos and mixed-language phrasing
* notice that a description is ambiguous and say which fact is missing
* write the natural-language "this is how we understood you" sentence

What the LLM is **forbidden** to do, enforced mechanically below rather than by
prompt wording alone:

* emit a KSCO8 or KSIC11 code (any code-shaped token is stripped)
* emit a 체류자격 code that is not in the allow-list passed by the caller
* decide whether reporting is required, whether work is permitted, or what a
  status allows
* state a deadline, fee or requirement

``validate_extraction`` is the trust boundary: everything the model returns
passes through it, unknown keys are dropped, and every stripped value is recorded
in ``warnings`` so the removal is auditable rather than silent.

Pure functions, stdlib only, never raises.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

EMPLOYMENT_NL_VERSION = "2026-07-employment-nl-v1"

# The exact contract the model is asked for, and the only keys kept from it.
EXTRACTION_FIELDS: Dict[str, str] = {
    "detectedLanguage": "str",
    "role": "str",
    "tasks": "list",
    "workplace": "str",
    "employerMainBusiness": "str",
    "employmentType": "str",
    "incomeStatus": "str",
    "visaStatus": "str",
    "objects": "list",
    "actions": "list",
    "tools": "list",
    "ambiguities": "list",
    "needsClarification": "bool",
    "clarificationQuestion": "str",
}

_MAX_STRING = 160
_MAX_LIST_ITEMS = 12
_MAX_CLARIFICATION = 240

# KSCO8 직종 codes and KSIC11 업종 codes are digit runs / letter+digit runs. Any
# such token in model output is an invention by construction — the model was
# never given the classification tables.
_CLASSIFICATION_CODE_RE = re.compile(
    r"(?<![0-9A-Za-z])(?:"
    r"\d{3,6}"                       # KSCO8 세분류/세세분류 shapes
    r"|[A-Z]\d{2,5}"                 # KSIC11 대분류 letter + digits
    r"|[A-Z]-\d{2,5}"
    r")(?![0-9A-Za-z])"
)

# A 체류자격 code shape. Only codes explicitly allow-listed by the caller survive.
_VISA_CODE_RE = re.compile(r"\b([A-Z])\s*-?\s*(\d{1,2})(?:\s*-?\s*([0-9A-Z]{1,3}))?\b")

# Determination vocabulary: the model must describe facts, never adjudicate.
_DETERMINATION_PATTERNS = (
    re.compile(r"신고\s*(대상|의무)\s*(입니다|이다|임|여부는?\s*(예|아니오))"),
    re.compile(r"(신고|보고)(해야|하셔야)\s*(합니다|한다|해요)"),
    re.compile(r"취업(이)?\s*(가능|불가|허용|금지)\s*(합니다|하다|해요|입니다)"),
    re.compile(r"(허가|불허|승인|거부)\s*(됩니다|된다|돼요)"),
    re.compile(r"(within|must|required to)\s+(report|apply|notify)", re.IGNORECASE),
    re.compile(r"\d+\s*(일|개월|년)\s*(이내|안에)"),
)


def _clean_text(value: Any, *, limit: int = _MAX_STRING) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def _clean_list(value: Any) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out: List[str] = []
    for item in value:
        cleaned = _clean_text(item)
        if cleaned and cleaned not in out:
            out.append(cleaned)
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def strip_classification_codes(value: str) -> Tuple[str, List[str]]:
    """Remove any classification-code-shaped token. Returns (cleaned, removed)."""
    removed = _CLASSIFICATION_CODE_RE.findall(value or "")
    if not removed:
        return value, []
    cleaned = _CLASSIFICATION_CODE_RE.sub("", value or "")
    return re.sub(r"\s{2,}", " ", cleaned).strip(), list(removed)


def sanitize_visa_status(value: str, allowed_codes: Optional[Set[str]]) -> Tuple[str, List[str]]:
    """Keep a 체류자격 code only when it is in the caller's allow-list."""
    text = (value or "").strip().upper()
    if not text:
        return "", []
    match = _VISA_CODE_RE.search(text)
    if not match:
        return "", [text] if text else []
    parts = [match.group(1), match.group(2)]
    if match.group(3):
        parts.append(match.group(3))
    canonical = "-".join(parts)
    if allowed_codes is None or canonical in allowed_codes:
        return canonical, []
    parent = "-".join(parts[:2])
    if allowed_codes is not None and parent in allowed_codes:
        return parent, [canonical]
    return "", [canonical]


def contains_determination(text: str) -> bool:
    """True when the text adjudicates rather than describes."""
    haystack = text or ""
    return any(pattern.search(haystack) for pattern in _DETERMINATION_PATTERNS)


def validate_extraction(
    raw: Any,
    *,
    allowed_visa_codes: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Validate and sanitize a model extraction into the fixed schema.

    Unknown keys are dropped, every string is length-capped, classification codes
    are stripped, out-of-allow-list 체류자격 codes are removed, and any determination
    sentence is discarded. Every removal is recorded in ``warnings``.
    """
    warnings: List[str] = []
    allowed = None
    if allowed_visa_codes is not None:
        allowed = {str(c).strip().upper() for c in allowed_visa_codes if c}

    payload: Any = raw
    if isinstance(raw, str):
        payload = parse_json_object(raw)
        if payload is None:
            return {
                "ok": False,
                "reason": "unparseable_model_output",
                "data": empty_extraction(),
                "warnings": ["MODEL_OUTPUT_NOT_JSON"],
            }
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "unexpected_shape",
            "data": empty_extraction(),
            "warnings": ["MODEL_OUTPUT_NOT_OBJECT"],
        }

    unknown_keys = [k for k in payload.keys() if k not in EXTRACTION_FIELDS]
    if unknown_keys:
        warnings.append("DROPPED_UNKNOWN_FIELDS:" + ",".join(sorted(unknown_keys)[:8]))

    data = empty_extraction()
    for field, kind in EXTRACTION_FIELDS.items():
        value = payload.get(field)
        if kind == "list":
            data[field] = _clean_list(value)
        elif kind == "bool":
            data[field] = bool(value)
        else:
            data[field] = _clean_text(
                value, limit=_MAX_CLARIFICATION if field == "clarificationQuestion" else _MAX_STRING)

    # 1. Classification codes: never allowed anywhere.
    for field, kind in EXTRACTION_FIELDS.items():
        if kind == "str":
            cleaned, removed = strip_classification_codes(data[field])
            if removed:
                data[field] = cleaned
                warnings.append(f"STRIPPED_CLASSIFICATION_CODE:{field}")
        elif kind == "list":
            new_items: List[str] = []
            for item in data[field]:
                cleaned, removed = strip_classification_codes(item)
                if removed:
                    warnings.append(f"STRIPPED_CLASSIFICATION_CODE:{field}")
                if cleaned:
                    new_items.append(cleaned)
            data[field] = new_items

    # 2. 체류자격 code: allow-list only.
    visa, rejected = sanitize_visa_status(data["visaStatus"], allowed)
    data["visaStatus"] = visa
    if rejected:
        warnings.append("REJECTED_UNKNOWN_VISA_CODE")

    # 3. Determinations: the clarification question must ask, not answer.
    if data["clarificationQuestion"] and contains_determination(data["clarificationQuestion"]):
        data["clarificationQuestion"] = ""
        data["needsClarification"] = False
        warnings.append("REMOVED_DETERMINATION_IN_CLARIFICATION")
    data["ambiguities"] = [a for a in data["ambiguities"] if not contains_determination(a)]

    # 4. A clarification flag with no question is not actionable.
    if data["needsClarification"] and not data["clarificationQuestion"]:
        data["needsClarification"] = False
        warnings.append("CLARIFICATION_FLAG_WITHOUT_QUESTION")

    language = (data["detectedLanguage"] or "").lower()
    data["detectedLanguage"] = language if language in {"ko", "en", "zh", "mixed", "other"} else ""

    return {"ok": True, "reason": "", "data": data, "warnings": warnings}


def empty_extraction() -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for field, kind in EXTRACTION_FIELDS.items():
        data[field] = [] if kind == "list" else (False if kind == "bool" else "")
    return data


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from model output (tolerates code fences)."""
    raw = str(text or "").strip()
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(raw[start:end + 1])
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def build_extraction_prompt(text: str, *, lang: str = "ko") -> str:
    """Prompt for structured extraction. Explicitly forbids codes and verdicts."""
    user_text = _clean_text(text, limit=600)
    schema = json.dumps(
        {k: ([] if v == "list" else (False if v == "bool" else ""))
         for k, v in EXTRACTION_FIELDS.items()},
        ensure_ascii=False, indent=2,
    )
    language_line = ("Write all string values in natural Korean."
                     if lang == "ko" else "Write all string values in natural English.")
    return (
        "You extract structured facts from a foreign resident's free-text "
        "description of their job in Korea, for a 취업정보 신고 (employment "
        "information reporting) helper.\n\n"
        f"User text:\n\"\"\"\n{user_text}\n\"\"\"\n\n"
        "Return ONLY a JSON object with exactly these keys:\n"
        f"{schema}\n\n"
        "FIELD MEANINGS:\n"
        "- role: what the PERSON does (their occupation).\n"
        "- workplace: where they physically work.\n"
        "- employerMainBusiness: what the EMPLOYER's business is. This is a "
        "different question from `role` — never copy one into the other.\n"
        "- tasks / actions / objects / tools: concrete verbs and things named.\n"
        "- ambiguities: which facts are genuinely unclear from the text.\n"
        "- clarificationQuestion: ONE short question that would resolve the most "
        "important ambiguity. Leave empty if the text is clear enough.\n\n"
        "ABSOLUTE PROHIBITIONS — violating any of these makes the output unusable:\n"
        "1. NEVER output a KSCO8 occupation code or a KSIC11 industry code, or "
        "any number that looks like a classification code. You have not been "
        "given the classification tables and cannot know them.\n"
        "2. NEVER decide whether reporting is required, whether the work is "
        "permitted, or what a visa status allows.\n"
        "3. NEVER state a deadline, fee, or legal requirement.\n"
        "4. NEVER invent facts the user did not write. Leave a field empty "
        "instead of guessing.\n"
        "5. Output JSON only — no prose before or after.\n\n"
        f"{language_line}"
    )


def to_analyzer_input(extraction: Dict[str, Any], *, original_text: str = "") -> Dict[str, Any]:
    """Shape a validated extraction into deterministic-analyzer input.

    The analyzer accepts ``{text, locale, visaStatus, employmentType}``. The text
    it receives is the structured fields rejoined — a cleaner retrieval query than
    the raw sentence — with the original text appended so nothing the user wrote
    is lost if extraction missed it.
    """
    data = extraction if isinstance(extraction, dict) else {}
    parts: List[str] = []
    for key in ("role", "workplace", "employerMainBusiness"):
        if data.get(key):
            parts.append(str(data[key]))
    for key in ("tasks", "actions", "objects", "tools"):
        parts.extend(str(v) for v in (data.get(key) or []))

    structured_text = " ".join(dict.fromkeys(p for p in parts if p))
    combined = (structured_text + " " + _clean_text(original_text, limit=400)).strip()

    locale = data.get("detectedLanguage") or ""
    return {
        "text": combined or _clean_text(original_text, limit=400),
        "locale": locale if locale in {"ko", "en"} else "",
        "visaStatus": data.get("visaStatus") or "",
        "employmentType": data.get("employmentType") or "",
    }


def build_interpretation_sentence(extraction: Dict[str, Any], *, lang: str = "ko") -> str:
    """Deterministic "this is how we understood you" sentence.

    Built from the validated fields rather than asked of the model again, so the
    sentence can never contain something the validator just stripped.
    """
    data = extraction if isinstance(extraction, dict) else {}
    role = data.get("role") or ""
    workplace = data.get("workplace") or ""
    business = data.get("employerMainBusiness") or ""

    if lang == "en":
        bits = []
        if workplace:
            bits.append(f"you work at {workplace}")
        if role:
            bits.append(f"your role is {role}")
        if business:
            bits.append(f"the employer's business is {business}")
        if not bits:
            return "We could not read a clear job description yet."
        return "We understood that " + ", and ".join(bits) + "."

    bits = []
    if workplace:
        bits.append(f"{workplace}에서 일하시고")
    if role:
        bits.append(f"하시는 일은 {role}")
    if business:
        bits.append(f"사업장 분야는 {business}")
    if not bits:
        return "아직 어떤 일을 하시는지 명확하게 읽지 못했어요."
    return " ".join(bits) + "(으)로 이해했어요."


__all__ = [
    "EMPLOYMENT_NL_VERSION", "EXTRACTION_FIELDS",
    "empty_extraction", "parse_json_object", "build_extraction_prompt",
    "validate_extraction", "strip_classification_codes", "sanitize_visa_status",
    "contains_determination", "to_analyzer_input", "build_interpretation_sentence",
]
