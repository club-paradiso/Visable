"""Mission 005-G: the trusted-evidence pipeline around one model call, and the answer guard.

    candidates -> evidence_admissibility.select_admissible_evidence (registry, scope, date)
               -> pre-inference outcome: proceed | system_withheld | system_clarification | review_required
               -> (proceed only) model call with admissible evidence, reply_language, uncovered_items (contract v5)
               -> validate_generated_answer: release | withhold | review_required | invalid_response
               -> released response, labelled with who produced it

Raw model output is kept unchanged next to what the system releases. A system
fallback is never a model success, and the guard never rewrites a wrong answer
into a right one: it either lets the model's answer through or replaces it with a
non-substantive system message. Mission 005-H: a released partial answer that does
not name an uncovered item gets a separate, labelled system notice naming it; the
model's sentences are never edited. Research-only; nothing here is wired into the
production backend.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Mapping, Optional

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import claim_support_validation
import language_compliance
from waymaker_ai.evidence_admissibility import ITEM_LABELS, parent_code, requested_items, select_admissible_evidence
from waymaker_ai.evidence_registry import TrustRegistry
from waymaker_ai.response_contract import parse_response

CONTRACT_VERSION = "v5"
PROVENANCE = ("model_generated", "model_generated_with_system_notice", "system_withheld", "system_clarification",
              "review_required", "post_generation_blocked", "invalid_response")
#: Mission 005-H: the system notice added to a released partial answer, by reply language.
NOTICE = {"ko": "확인된 근거에 없는 항목: {items}. 이 항목은 담당 기관에 직접 확인해 주세요.",
          "en": "Not covered by the verified evidence: {items}. Please check these with the responsible office.",
          "vi": "Không có trong căn cứ đã xác minh: {items}. Vui lòng hỏi trực tiếp cơ quan phụ trách về các mục này."}
SUBSTANTIVE = {"answered", "partial", "conflict"}
_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-\d{1,2})?)(?![0-9-])")

FALLBACK = {
    "withheld": {"ko": "확인된 공식 근거로 답할 수 없어 답변을 보류합니다. 담당 기관에 직접 확인해 주세요.",
                 "en": "This cannot be answered from verified official evidence, so the answer is withheld. Please check with the responsible office.",
                 "vi": "Không thể trả lời dựa trên căn cứ chính thức đã được xác minh nên câu trả lời được tạm giữ. Vui lòng hỏi trực tiếp cơ quan phụ trách."},
    "review": {"ko": "근거의 적용 여부를 사람이 확인해야 해 지금은 답변을 드리지 않습니다.",
               "en": "Whether the evidence applies needs human review, so no answer is given now.",
               "vi": "Cần có người kiểm tra căn cứ có áp dụng hay không, nên hiện chưa đưa ra câu trả lời."},
    "location": {"ko": "답이 국내에 계신지 국외에 계신지에 따라 달라집니다. 지금 어디에 계신지 알려 주세요.",
                 "en": "The answer depends on whether you are in Korea or abroad. Please tell me where you are now.",
                 "vi": "Câu trả lời phụ thuộc vào việc bạn đang ở Hàn Quốc hay ở nước ngoài. Vui lòng cho biết bạn đang ở đâu."},
    "status_code": {"ko": "답이 세부 체류자격에 따라 달라집니다. 지금 가진 체류자격 코드를 알려 주세요.",
                    "en": "The answer depends on your exact status sub-category. Please tell me your current status code.",
                    "vi": "Câu trả lời phụ thuộc vào tư cách lưu trú chi tiết. Vui lòng cho biết mã tư cách hiện tại của bạn."},
    "blocked": {"ko": "생성된 답에 확인되지 않은 내용이 있어 내보내지 않았습니다. 담당 기관에 직접 확인해 주세요.",
                "en": "The generated answer contained unverified content and was not released. Please check with the responsible office.",
                "vi": "Câu trả lời được tạo có nội dung chưa được xác minh nên không được gửi. Vui lòng hỏi trực tiếp cơ quan phụ trách."},
}


def reply_language(question: str) -> dict:
    """Deterministic: explicit request, then question language, then Korean (language_compliance)."""
    return language_compliance.required_language(question)


def system_response(kind: str, lang: str) -> dict:
    status = "clarify" if kind in ("location", "status_code") else "insufficient_evidence"
    return {"status": status, "answer": FALLBACK[kind][lang], "citations": []}


def prepare(question: str, intake: Optional[Mapping], candidates: list, registry: Optional[TrustRegistry],
            evaluation_date: str) -> dict:
    """Pre-inference: admissibility, outcome, and the exact item the model would receive."""
    selection = select_admissible_evidence(question, intake, candidates, registry, evaluation_date)
    lang = reply_language(question)
    model_item = None
    if selection["outcome"] == "proceed":
        # v5 names the uncovered items in the reply language instead of internal keys.
        labels = [ITEM_LABELS[i][lang["language"]] for i in selection["uncovered_items"]]
        model_item = {"question": question, "evidence": selection["admissible"],
                      "system": {"reply_language": lang["language"], "uncovered_items": labels}}
    return {"selection": selection, "reply_language": lang, "model_item": model_item}


def _mentions_item(answer: str, item: str) -> bool:
    from waymaker_ai.evidence_admissibility import ITEM_ASK
    return bool(ITEM_ASK[item].search(unicodedata.normalize("NFC", answer)))


def validate_generated_answer(raw: Optional[str], prepared: Mapping, candidates: list,
                              registry: TrustRegistry) -> dict:
    """The guard decision for one model output (trusted_evidence_spec.md section 5)."""
    selection = prepared["selection"]
    admissible_ids = {e["id"] for e in selection["admissible"]}
    lang = prepared["reply_language"]["language"]
    question = prepared["model_item"]["question"]
    findings = []

    def done(decision):
        return {"decision": decision, "findings": findings}
    try:
        parsed = parse_response(raw, admissible_ids, CONTRACT_VERSION)
    except (TypeError, ValueError) as exc:
        findings.append({"check": "contract", "detail": str(exc)})
        return {**done("invalid_response"), "parsed": None}
    status, answer, cites = parsed["status"], parsed["answer"], set(parsed["citations"])
    admissible_map = {e["id"]: e["id"] in admissible_ids for e in candidates}
    if status in SUBSTANTIVE:
        support = claim_support_validation.check(answer, question, candidates, cites, admissible_map)
        for f in support["findings"]:
            kind = f["kind"]
            if kind in ("value_from_inadmissible", "polarity_reversal", "obligation_negated") or kind.endswith("_mismatch") \
                    or kind in ("unsupported_money", "unsupported_period", "unsupported_date"):
                findings.append({"check": "claim_support", "kind": kind, "detail": f["detail"], "effect": "withhold"})
            elif kind in ("code_not_in_cited_evidence",):
                findings.append({"check": "scope", "kind": kind, "detail": f["detail"], "effect": "review_required"})
        ctx_code = (selection["context"] or {}).get("status_code")
        if ctx_code:
            # Mission 005-H: a code the cited admissible evidence itself names is in scope; sorted for a stable record.
            cited_text = "\n".join(e.get("text", "") for e in selection["admissible"] if e["id"] in cites)
            for code in sorted(set(_CODE_RE.findall(answer)) - set(_CODE_RE.findall(cited_text))):
                if parent_code(code) == parent_code(ctx_code) and code != ctx_code and code != parent_code(code) \
                        and ctx_code != parent_code(ctx_code):
                    findings.append({"check": "scope", "kind": "other_subcategory_in_answer", "detail": code,
                                     "effect": "review_required"})
        missing = [i for i in selection["uncovered_items"] if not _mentions_item(answer, i)]
        if missing and status == "answered":
            findings.append({"check": "partial", "kind": "uncovered_item_not_named", "detail": missing,
                             "effect": "review_required"})
        elif missing and status == "partial":
            findings.append({"check": "partial", "kind": "uncovered_item_not_named", "detail": missing,
                             "effect": "system_notice"})
        asked = requested_items(question)
        if asked and set(asked) <= set(selection["uncovered_items"]):
            # Unreachable when pre-inference withholds such questions; kept as a second line.
            findings.append({"check": "partial", "kind": "no_requested_item_covered", "detail": asked, "effect": "withhold"})
    language = language_compliance.check(question, answer, lang)
    if language["result"] == "fail":
        findings.append({"check": "language", "kind": language["reason"], "detail": lang, "effect": "review_required"})
    effects = {f.get("effect") for f in findings}
    decision = "withhold" if "withhold" in effects else "review_required" if "review_required" in effects else "release"
    notice = None
    if decision == "release" and "system_notice" in effects:
        missing = next(f["detail"] for f in findings if f.get("effect") == "system_notice")
        notice = NOTICE[lang].format(items=", ".join(ITEM_LABELS[i][lang] for i in missing))
    return {**done(decision), "parsed": parsed, "language": language["result"], "system_notice": notice}


def run_case(question: str, intake: Optional[Mapping], candidates: list, registry: Optional[TrustRegistry],
             evaluation_date: str, generate: Callable[[dict], Optional[str]]) -> dict:
    """One question end to end. `generate(model_item)` returns the raw model text; it is called only on proceed."""
    prepared = prepare(question, intake, candidates, registry, evaluation_date)
    sel, lang = prepared["selection"], prepared["reply_language"]["language"]
    record = {"pre_inference": sel["outcome"], "pre_inference_reason": sel["reason"], "context": sel["context"],
              "trust_decisions": sel["decisions"], "admissible_ids": [e["id"] for e in sel["admissible"]],
              "uncovered_items": sel["uncovered_items"], "reply_language": prepared["reply_language"],
              "model_called": False, "raw_output": None, "guard": None}
    if sel["outcome"] == "system_withheld":
        released, provenance = system_response("withheld", lang), "system_withheld"
    elif sel["outcome"] == "review_required":
        released, provenance = system_response("review", lang), "review_required"
    elif sel["outcome"] == "system_clarification":
        released, provenance = system_response(sel["clarify_on"], lang), "system_clarification"
    else:
        raw = generate(prepared["model_item"])
        guard = validate_generated_answer(raw, prepared, candidates, registry)
        record.update(model_called=True, raw_output=raw, guard=guard,
                      model_input_sha256=hashlib.sha256(json.dumps(prepared["model_item"], ensure_ascii=False,
                                                                   sort_keys=True).encode()).hexdigest())
        if guard["decision"] == "release" and guard.get("system_notice"):
            released = {**guard["parsed"], "system_notice": guard["system_notice"]}
            provenance = "model_generated_with_system_notice"
        elif guard["decision"] == "release":
            released, provenance = guard["parsed"], "model_generated"
        elif guard["decision"] == "invalid_response":
            released, provenance = system_response("blocked", lang), "invalid_response"
        elif guard["decision"] == "review_required":
            released, provenance = system_response("review", lang), "review_required"
        else:
            released, provenance = system_response("blocked", lang), "post_generation_blocked"
    record.update(released=released, released_provenance=provenance)
    return record
