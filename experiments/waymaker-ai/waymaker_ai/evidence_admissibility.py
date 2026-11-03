"""Mission 005-G: deterministic evidence admissibility and the pre-inference grounding gate.

Sits between retrieval and inference. For each candidate document it decides
admissible / rejected / review_required from the trust registry and the question
context, in the fixed order of trusted_evidence_spec.md section 3, and records why.
Then it decides whether the model is called at all (section 4): with no admissible
evidence the system withholds instead of letting the model guess, and a personal
question whose answer turns on a missing fact gets a system clarification.
Mission 005-H: when the question asks for specific items and the admissible
evidence covers none of them, the system also withholds; the model is not asked to
answer around the gap. Mission 005-J: a general question whose admissible evidence
is split by sub-code is answered one sub-code at a time (subcode_parts). Mission 005-K:
the same for evidence split between people in Korea and people abroad (situation_parts).
Mission 005-N: a candidate's document name written in the question, and a location word that names
an office or a document ("overseas mission handbook"), are not read as the user's location, procedure
or asked items; "how can <several words> apply" asks for the method.

Nothing here reads a document's self-description, a benchmark answer key or an
expected status. The question context is what the user entered (intake) plus what
the question text states; it is not a label.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import unicodedata
from typing import Iterable, Mapping, Optional

from waymaker_ai.evidence_registry import RegistryUnavailable, TrustRegistry, content_sha256

_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-\d{1,2})?)(?![0-9-])")
_LOCATION = {
    # Mission 005-K: "in Korea" only as a word, so "in Korean" (a language request) is not a location.
    "domestic": re.compile(r"국내|한국에\s*(?:있|체류|살)|한국\s*안|in\s+korea\b|inside\s+korea\b|tại\s+hàn\s+quốc|ở\s+hàn\s+quốc|trong\s+nước", re.I),
    "abroad": re.compile(r"국외|해외|외국에\s*(?:있|체류|살)|abroad|outside\s+(?:of\s+)?korea|overseas|ở\s+nước\s+ngoài|ngoài\s+hàn\s+quốc", re.I),
}
# Mission 005-N: a location word followed by (or, in Vietnamese, preceded by) an office or document noun names
# that office or document ("overseas mission handbook", "해외 공관", "cơ quan đại diện ở nước ngoài"), not the user's location.
_NAMED_AFTER = re.compile(r"\s*(?:[\w-]+\s+)?(?:missions?|embass(?:y|ies)|consulates?|offices?|handbooks?|guide(?:line)?s?|manuals?)\b"
                          r"|\s*(?:공관|대사관|영사관|사무소|편람|지침|안내서)", re.I)
_NAMED_BEFORE = re.compile(r"(?:cơ\s+quan(?:\s+đại\s+diện)?|đại\s+sứ\s+quán|lãnh\s+sự\s+quán|văn\s+phòng|sổ\s+tay|hướng\s+dẫn)\s*$", re.I)
_PROCEDURE = {
    "extension": r"연장|extend|extension|gia\s*hạn",
    "change": r"자격\s*변경|체류자격을?\s*(?:바꾸|변경)|change\s+(?:of\s+)?status|status\s+change|thay\s+đổi\s+tư\s+cách|chuyển\s+đổi",
    "issuance": r"사증|비자\s*발급|발급\s*신청|visa\s+issu|issuance|cấp\s+thị\s+thực|xin\s+thị\s+thực",
    "registration": r"외국인\s*등록|alien\s+registration|foreigner\s+registration|đăng\s+ký\s+người\s+nước\s+ngoài",
    "reentry": r"재입국|re-?entry|tái\s+nhập\s+cảnh",
    "workplace": r"근무처|workplace|employer\s+change|nơi\s+làm\s+việc",
    "address": r"체류지|주소|이사|address|change\s+of\s+residence|địa\s+chỉ|chuyển\s+nhà",
    "activity": r"시간제|아르바이트|체류자격\s*외|part-?time|làm\s+thêm",
    "family": r"초청|가족|동반|invite|family|bảo\s+lãnh|gia\s+đình",
}
_PROCEDURE_RE = {k: re.compile(v, re.I) for k, v in _PROCEDURE.items()}
# A personal determination needs a first-person reference AND a request for a decision.
# Mission 005-T: "am I permitted / able" is a request for a decision like "am I allowed" (A05T-35).
_FIRST_PERSON = re.compile(r"제가|저는|저의|제\s|내가|나는|\bI\b|\bI'm\b|\bmy\b|\bme\b|\btôi\b|\bem\b|\bmình\b", re.I)
_DECISION = re.compile(r"할\s*수\s*있|해야\s*(?:하|되|합)|하나요|되나요|대상인가|대상이\s*되|가능한가|가능할까|필요한가|필요하나요|"
                       r"\bcan\s+i\b|\bmay\s+i\b|\bdo\s+i\s+(?:need|have)\b|\bmust\s+i\b|\bam\s+i\s+(?:eligible|allowed|permitted|required|able)\b|"
                       r"\bshould\s+i\b|\bwhere\s+do\s+i\b|có\s+thể|có\s+cần|có\s+phải|phải\s+.*không|được\s+không", re.I)
_DATE_FULL = re.compile(r"(\d{4})\s*(?:년|[.\-/])\s*(\d{1,2})\s*(?:월|[.\-/])\s*(\d{1,2})")
_DATE_MONTH = re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월|tháng\s*(\d{1,2})\s*(?:/|năm)\s*(\d{4})")
#: Items a question can ask for, and the words that show evidence covers them.
ITEMS = {
    # Mission 005-H: "phí" only as a word, so "phía" (side, as in vùng phía Nam) is not a fee.
    # Mission 005-I: "원" only after a number (not 지원, 원본, 직원); fee-free wording also covers the fee.
    "fee": (r"수수료|비용|요금|fee|cost|lệ\s*phí|\bphí\b",
            r"수수료|\d[\d,.]*\s*원|\bwon\b(?!')|krw|fee|lệ\s*phí|무료|면제|free\s+of\s+charge|miễn\s+phí"),
    "processing_time": (r"처리\s*기간|처리기간|걸리|processing\s+(?:time|period)|how\s+long|thời\s+gian\s+xử\s+lý|bao\s+lâu",
                        r"처리\s*기간|처리기간|처리한다|처리됨|processing|xử\s+lý|일\s*이내\s*처리|일\s*안에\s*처리"),
    # Mission 005-J: English document words also cover documents.
    "documents": (r"서류|documents?|papers|giấy\s+tờ|hồ\s+sơ",
                  r"서류|신청서|여권|증명서|확인서|document|giấy|hồ\s+sơ|등록증|사진|\bpassport|\bcertificate|\bapplication\s+form"),
    "deadline": (r"기한|며칠\s*(?:안|이내)|언제까지|deadline|within\s+how|how\s+many\s+days|thời\s+hạn|trong\s+bao\s+nhiêu\s+ngày",
                 r"이내|기한|까지|within|deadline|trong\s+vòng|thời\s+hạn"),
    # Mission 005-I: 장소 / place / địa điểm also ask for the place.
    "place": (r"어디에|어디서|신청처|장소|where|\bplace\b|ở\s+đâu|nơi\s+nộp|địa\s+điểm",
              # Mission 005-I: an agency counts only as a place to go ("…청에", "기관에서"); bare 청 matched 신청.
              r"(?<!신)청(?:에|에서)|기관(?:에|에서)|사무소|출장소|공관|센터|창구|누리집|장소|신청처|office|embassy|consulate|"
              r"counter|cent(?:er|re)|\bmission\b|cơ\s+quan|văn\s+phòng|trung\s+tâm"),
    "method": (r"온라인|방문|방법|how\s+(?:do|can)\s+(?:\S+\s+){1,6}?apply|online|in\s+person|bằng\s+cách|(?<!tư\s)cách\s+nào|phương\s+thức|trực\s+tuyến|trực\s+tiếp",
               r"온라인|방문|누리집|창구|online|visit|in\s+person|trực"),
    "eligibility": (r"자격\s*요건|요건|조건|대상|eligib|requirement|điều\s+kiện|đối\s+tượng", r"요건|조건|대상|이상|이하|eligib|requirement|điều\s+kiện"),
}
ITEM_ASK = {k: re.compile(a, re.I) for k, (a, _) in ITEMS.items()}
ITEM_COVER = {k: re.compile(c, re.I) for k, (_, c) in ITEMS.items()}
#: Mission 005-H: item names in each reply language, for the model input (contract v5)
#: and the system notice on a partial answer.
ITEM_LABELS = {
    "fee": {"ko": "수수료", "en": "fee", "vi": "lệ phí"},
    "processing_time": {"ko": "처리기간", "en": "processing time", "vi": "thời gian xử lý"},
    "documents": {"ko": "제출 서류", "en": "required documents", "vi": "giấy tờ cần nộp"},
    "deadline": {"ko": "신청·신고 기한", "en": "deadline", "vi": "thời hạn"},
    "place": {"ko": "신청 장소", "en": "place of application", "vi": "nơi nộp"},
    "method": {"ko": "신청 방법", "en": "application method", "vi": "cách nộp"},
    "eligibility": {"ko": "자격 요건", "en": "eligibility requirements", "vi": "điều kiện"},
}


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _date(value: Optional[str]) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def parent_code(code: str) -> str:
    parts = code.split("-")
    return "-".join(parts[:2])


def without_document_names(question: str, candidates: Iterable[Mapping]) -> str:
    """Mission 005-N: the question with every candidate document name (source.document_id) it quotes blanked out.

    A name such as "가상 국외체류자 안내(2026년판)" is the document's, not a fact the user gives. Status codes are
    still read from the whole question.
    """
    text = _nfc(question)
    names = {_nfc(e["source"]["document_id"]).strip() for e in candidates
             if isinstance(e.get("source"), Mapping) and isinstance(e["source"].get("document_id"), str)}
    for name in sorted((n for n in names if len(n) >= 4), key=len, reverse=True):
        text = re.sub(re.escape(name), " ", text, flags=re.I)
    return text


def _located(rx: re.Pattern, text: str) -> bool:
    """A location word that is not part of an office or document name (005-N)."""
    return any(not _NAMED_AFTER.match(text, m.end()) and not _NAMED_BEFORE.search(text[:m.start()])
               for m in rx.finditer(text))


def question_context(question: str, intake: Optional[Mapping], registry: Optional[TrustRegistry],
                     evaluation_date: str, context_question: Optional[str] = None) -> dict:
    """User-entered intake, with empty fields filled from the question text (spec section 2).

    005-N: location and procedure are read from `context_question` (the question without quoted document names).
    """
    intake = dict(intake or {})
    text = _nfc(question)
    place_text = _nfc(context_question) if context_question is not None else text
    filled = {}
    codes = list(dict.fromkeys(_CODE_RE.findall(text)))
    subs = [c for c in codes if c != parent_code(c)]
    # The most specific code the question names; two different sub-codes leave only their family.
    found = subs[0] if len(subs) == 1 else (parent_code(subs[0]) if subs else (codes[0] if codes else None))
    status = intake.get("status_code") or found
    if not intake.get("status_code") and found:
        filled["status_code"] = status
    location = intake.get("location")
    if not location:
        hits = [k for k, rx in _LOCATION.items() if _located(rx, place_text)]
        location = hits[0] if len(hits) == 1 else None
        if location:
            filled["location"] = location
    procedure = intake.get("procedure")
    if not procedure:
        hits = [k for k, rx in _PROCEDURE_RE.items() if rx.search(place_text)]
        procedure = hits[0] if len(hits) == 1 else None
        if procedure:
            filled["procedure"] = procedure
    jurisdiction = intake.get("jurisdiction")
    if not jurisdiction and registry is not None:
        hits = [j for j in registry.jurisdictions() if j in text]
        jurisdiction = hits[0] if len(hits) == 1 else None
        if jurisdiction:
            filled["jurisdiction"] = jurisdiction
    qtype = intake.get("question_type")
    if not qtype:
        qtype = "personal" if (_FIRST_PERSON.search(text) and _DECISION.search(text)) else "general"
        filled["question_type"] = qtype
    as_of = intake.get("as_of")
    if not as_of:
        m = _DATE_FULL.search(text)
        if m:
            as_of = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        else:
            m = _DATE_MONTH.search(text)
            if m:
                y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
                as_of = f"{int(y):04d}-{int(mo):02d}-01"
        if as_of:
            filled["as_of"] = as_of
    return {"status_code": status, "procedure": procedure, "jurisdiction": jurisdiction, "location": location,
            "question_type": qtype, "as_of": as_of or evaluation_date, "as_of_source": "intake" if intake.get("as_of")
            else ("question" if as_of else "evaluation_date"), "filled_from_text": filled}


def _scope_decision(record: Mapping, code: Optional[str]) -> Optional[tuple[str, str]]:
    if not code:
        return None
    scope = list(record.get("status_scope") or [])
    parents = list(record.get("all_subcategories_of") or [])
    family = parent_code(code)
    is_sub = code != family
    if is_sub:
        if code in scope or family in parents:
            return None
        same_family = [s for s in scope if parent_code(s) == family]
        if family in scope:
            return "review_required", "parent_scope_unverified"
        if same_family:
            return "rejected", "other_subcategory"
        return "rejected", "other_subject"
    if any(parent_code(s) == family for s in scope) or family in parents:
        return None
    return "rejected", "other_subject"


def decide_one(evidence: Mapping, ctx: Mapping, registry: TrustRegistry) -> dict:
    """The admissibility decision for one document, first failing rule wins (spec section 3)."""
    eid = evidence.get("id")
    record = registry.get(eid)

    def out(decision, reason, rule):
        return {"evidence_id": eid, "decision": decision, "reason": reason, "rule": rule,
                "registry_record_sha256": hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if record else None,
                "content_sha256": content_sha256(evidence.get("text", ""))}
    if record is None:
        return out("rejected", "no_registry_record", 1)
    if record["content_sha256"] != content_sha256(evidence.get("text", "")):
        return out("rejected", "integrity_mismatch", 2)
    result = record["verification"]["result"]
    if result in ("rejected", "unverified"):
        return out("rejected", "verification_rejected" if result == "rejected" else "unverified_source", 3)
    if result == "review_required":
        return out("review_required", "verification_pending", 4)
    if record["authority"] != "official":
        return out("rejected", "non_authoritative_source", 5)
    if record["review_state"] == "rejected":
        return out("rejected", "review_rejected", 6)
    if record["review_state"] == "pending":
        return out("review_required", "review_pending", 7)
    regions = [j for j in record["jurisdiction"] if j != "national"]
    if ctx.get("jurisdiction"):
        if regions and ctx["jurisdiction"] not in regions:
            return out("rejected", "other_jurisdiction", 8)
    elif regions and "national" not in record["jurisdiction"]:
        return out("review_required", "jurisdiction_unspecified", 9)
    scope = _scope_decision(record, ctx.get("status_code"))
    if scope:
        return out(scope[0], scope[1], 10 if scope[0] == "rejected" else 11)
    procs = record["procedures"]
    if ctx.get("procedure") and "any" not in procs and ctx["procedure"] not in procs:
        return out("rejected", "other_procedure", 12)
    who = record["applicant_scope"]
    if ctx.get("location") and "any" not in who and ctx["location"] not in who:
        return out("rejected", "other_applicant_location", 13)
    start, end = _date(record["effective_from"]), _date(record["effective_until"])
    as_of = _date(ctx["as_of"])
    if start is None:
        return out("review_required", "effective_date_unknown", 14)
    if as_of < start:
        return out("rejected", "not_yet_effective", 15)
    if end is not None and as_of >= end:
        return out("rejected", "no_longer_effective", 16)
    successor = registry.get(record["superseded_by"]) if record.get("superseded_by") else None
    if successor and successor["verification"]["result"] == "verified" and _date(successor["effective_from"]) \
            and _date(successor["effective_from"]) <= as_of:
        return out("rejected", "superseded", 17)
    return out("admissible", "admissible", 0)


def requested_items(question: str) -> list[str]:
    text = _nfc(question)
    return [k for k, rx in ITEM_ASK.items() if rx.search(text)]


def uncovered_items(question: str, admissible: Iterable[Mapping]) -> list[str]:
    body = _nfc("\n".join(f"{e.get('title', '')}\n{e.get('text', '')}" for e in admissible))
    return [k for k in requested_items(question) if not ITEM_COVER[k].search(body)]


def _branches(ctx: Mapping, admissible: list, registry: TrustRegistry) -> Optional[str]:
    """The missing fact the admissible evidence splits on, if any (spec section 4)."""
    records = [registry.get(e["id"]) for e in admissible]
    if not ctx.get("location"):
        only = {tuple(sorted(r["applicant_scope"])) for r in records}
        if ("domestic",) in only and ("abroad",) in only:
            return "location"
    code = ctx.get("status_code")
    if not code or code == parent_code(code):
        if any(r.get("all_subcategories_of") for r in records):
            return None
        subs = {tuple(sorted(s for s in r["status_scope"] if s != parent_code(s))) for r in records}
        subs = {s for s in subs if s}
        if len(subs) >= 2 and all(len(s) == 1 for s in subs):
            return "status_code"
    return None


def subcode_parts(question: str, ctx: Mapping, admissible: list, registry: TrustRegistry) -> list:
    """Mission 005-J: one part per sub-code when the evidence for a parent-code or code-less question splits by sub-code.

    Applies only when every admissible record is limited to exactly one sub-code, at least two sub-codes
    occur, and no record is verified for all sub-codes. A sub-code whose evidence covers none of the
    asked items is left out. Fewer than two remaining parts means no split.
    """
    code = ctx.get("status_code")
    if code and code != parent_code(code):
        return []
    records = {e["id"]: registry.get(e["id"]) for e in admissible}
    if any(r.get("all_subcategories_of") for r in records.values()):
        return []
    scope = {}
    for eid, r in records.items():
        subs = [s for s in r["status_scope"] if s != parent_code(s)]
        if len(subs) != 1 or len(r["status_scope"]) != 1:
            return []
        scope.setdefault(subs[0], []).append(eid)
    if len(scope) < 2:
        return []
    asked = requested_items(question)
    parts = []
    for sub in sorted(scope):
        evidence = [e for e in admissible if e["id"] in scope[sub]]
        if asked and set(uncovered_items(question, evidence)) == set(asked):
            continue
        parts.append({"status_code": sub, "evidence_ids": scope[sub]})
    return parts if len(parts) >= 2 else []


def situation_parts(question: str, ctx: Mapping, admissible: list, registry: TrustRegistry) -> list:
    """Mission 005-K: one part per applicant location when the evidence splits between domestic and abroad.

    Applies only when the question gives no location, at least one admissible record is limited to
    domestic applicants and one to applicants abroad. Records for any applicant go into both parts.
    A situation whose evidence covers none of the asked items is left out; fewer than two parts means no split.
    """
    if ctx.get("location"):
        return []
    scopes = {e["id"]: set(registry.get(e["id"])["applicant_scope"]) for e in admissible}
    if not any(s == {"domestic"} for s in scopes.values()) or not any(s == {"abroad"} for s in scopes.values()):
        return []
    asked = requested_items(question)
    parts = []
    for loc in ("domestic", "abroad"):
        ids = [eid for eid, s in scopes.items() if loc in s or "any" in s]
        evidence = [e for e in admissible if e["id"] in ids]
        if asked and set(uncovered_items(question, evidence)) == set(asked):
            continue
        parts.append({"location": loc, "evidence_ids": ids})
    return parts if len(parts) >= 2 else []


def select_admissible_evidence(question: str, intake: Optional[Mapping], candidates: list,
                               registry: Optional[TrustRegistry], evaluation_date: str) -> dict:
    """Decisions for every candidate, the evidence the model may see, and the pre-inference outcome."""
    original = question
    if registry is None:
        decisions = [{"evidence_id": e.get("id"), "decision": "rejected", "reason": "registry_unavailable", "rule": 0,
                      "registry_record_sha256": None, "content_sha256": content_sha256(e.get("text", ""))} for e in candidates]
        return {"outcome": "system_withheld", "reason": "registry_unavailable", "context": None, "decisions": decisions,
                "admissible": [], "uncovered_items": [], "clarify_on": None,
                "input_sha256": hashlib.sha256(json.dumps(candidates, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    # Mission 005-N: context and asked items come from the question without the document names it quotes.
    question = without_document_names(question, candidates)
    ctx = question_context(original, intake, registry, evaluation_date, context_question=question)
    decisions = [decide_one(e, ctx, registry) for e in candidates]
    keep = {d["evidence_id"] for d in decisions if d["decision"] == "admissible"}
    admissible = [e for e in candidates if e.get("id") in keep]
    review = [d for d in decisions if d["decision"] == "review_required"]
    clarify_on, uncovered = None, []
    asked = requested_items(question)
    if not admissible:
        outcome, reason = ("review_required", "only_review_required_evidence") if review else ("system_withheld", "no_admissible_evidence")
    elif asked and set(uncovered_items(question, admissible)) == set(asked):
        # Mission 005-H: nothing the question asks for is in the admissible evidence. The list is kept for audit.
        outcome, reason = "system_withheld", "no_evidence_for_requested_items"
        uncovered = uncovered_items(question, admissible)
    else:
        clarify_on = _branches(ctx, admissible, registry) if ctx["question_type"] == "personal" else None
        if clarify_on:
            outcome, reason = "system_clarification", f"missing_{clarify_on}"
        else:
            outcome, reason = "proceed", "admissible_evidence"
            uncovered = uncovered_items(question, admissible)
    general = outcome == "proceed" and ctx["question_type"] == "general"
    parts = subcode_parts(question, ctx, admissible, registry) if general else []
    situations = situation_parts(question, ctx, admissible, registry) if general and not parts else []
    return {"outcome": outcome, "reason": reason, "context": ctx, "decisions": decisions, "admissible": admissible,
            "uncovered_items": uncovered, "clarify_on": clarify_on, "subcode_parts": parts, "situation_parts": situations,
            "context_question": question,
            "input_sha256": hashlib.sha256(json.dumps(candidates, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}


__all__ = ["RegistryUnavailable", "question_context", "decide_one", "select_admissible_evidence", "requested_items",
           "uncovered_items", "parent_code", "ITEM_LABELS", "subcode_parts", "situation_parts", "without_document_names"]
