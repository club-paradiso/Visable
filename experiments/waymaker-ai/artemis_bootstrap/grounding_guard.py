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
model's sentences are never edited. Mission 005-I: when the question itself carries
an instruction about the reply (start with a word, ignore the rules), a marker it
demands that shows up in the answer withholds the answer. Mission 005-J: those
instruction sentences are also removed from the question the model receives (the
user's question is kept in the record and still checked), and a general question
whose evidence splits by sub-code is asked once per sub-code with only that
sub-code's evidence; the parts are joined deterministically and each part is
guarded on its own. Mission 005-K: the same per-situation (people in Korea / abroad),
the question's date goes to the model when the user gave one, and Korean names copied
from the admissible evidence do not count against the reply language. Mission 005-L: a request
for a reply language written into the question is also removed from the question the model
receives; the system has already chosen reply_language from the user's question. Mission 005-M:
a partial answer is given the sentence naming its uncovered items (contract v10), and a value copied
from a cited document's source fields (its name) is not an unsupported claim. Mission 005-P: when the
guard's only objection to a part is the reply language, the system asks that part once more with a
language_retry note (contract v12); the first answer stays in the record as the raw output, and what is
released comes from the guard's decision on the retried answer.
Mission 005-Q: claim support reads Vietnamese dates as dates (vi_dates=True).
Mission 005-R: when a released answer gives only one case of a two-case evidence passage (branch_coverage),
the system asks that part once more with a branch_retry note quoting the left-out case (contract v13). If the
retried answer still leaves it out, or cannot be released, the released answer carries a labelled system notice
quoting the case; nothing is withheld for it, and the model's sentences are never edited.
Mission 005-S: claim support reads a cap on an amount ("must not exceed 18 hours") as a cap, not a prohibition
(caps_apart=True).
Mission 005-T: when a released answer's status or form is visibly wrong (status_check: two cited records that differ
only in their numbers answered as answered/partial, partial with nothing uncovered, an input field name in the answer),
the system asks that part once more with a status_retry note (contract v14). The retried answer is released when the
guard releases it; otherwise the earlier answer stays. Nothing is withheld for it.
Mission 005-U: the first call already names, as conflict_records (contract v15), each pair of a part's admissible
records whose texts differ only in their numbers (status_check's rule), so the model can state them as a conflict
before any retry. The status retry stays as a second line.
Mission 005-V: when a question asks which of two sibling status codes applies and a released answer names only one
of them though its cited evidence names both (choice_coverage), the system asks that part once more with a
choice_retry note quoting the evidence sentence about the other code (contract v16). If the retried answer still
leaves it out, or cannot be released, the released answer carries a labelled system notice quoting that sentence;
nothing is withheld for it, and the model's sentences are never edited.
Mission 005-W: the first call already names, as choice_codes (contract v17), the codes a choice question asks between
that the part's admissible evidence names (two or more, in question order), so the model can cover each of them
before any retry. The choice retry stays as a second line.
Research-only; nothing here is wired into the production backend.
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
import branch_coverage
import choice_conclusion
import choice_coverage
import claim_support_validation
import status_check
import language_compliance
from waymaker_ai.evidence_admissibility import (ITEM_LABELS, parent_code, requested_items, select_admissible_evidence,
                                                uncovered_items)
from waymaker_ai.evidence_registry import TrustRegistry
from waymaker_ai.response_contract import parse_response

CONTRACT_VERSION = "v18"
#: Mission 005-X: ask a choice question one choice code at a time. False gives the 005-W flow (one call with
#: choice_codes, then the choice retry); kept for tests and comparison only.
CHOICE_PARTS = True
PROVENANCE = ("model_generated", "model_generated_with_system_notice", "system_withheld", "system_clarification",
              "review_required", "post_generation_blocked", "invalid_response")
#: Mission 005-J: worst guard decision first, for joining per-sub-code parts.
DECISION_ORDER = ("invalid_response", "withhold", "review_required", "release")
#: Mission 005-P (contract v12): the note sent with the one retry after a reply-language failure.
LANGUAGE_RETRY = {"ko": "앞의 답이 한국어로 쓰이지 않았습니다. 모든 문장을 한국어로 쓰세요.",
                  "en": "The previous answer was not written in English. Write every sentence in English.",
                  "vi": "Câu trả lời trước không được viết bằng tiếng Việt. Hãy viết mọi câu bằng tiếng Việt."}
#: Mission 005-R (contract v13): the note sent with the one retry after an answer left out a case of its evidence,
#: and the system notice added when the case is still left out. {case} is the evidence text, quoted.
BRANCH_RETRY = {"ko": "앞의 답에는 인용한 근거가 정한 다른 경우가 빠졌습니다: “{case}” 근거가 정한 경우를 모두 쓰세요.",
                "en": "The previous answer left out a case the cited evidence states: “{case}” State every case the evidence gives.",
                "vi": "Câu trả lời trước đã bỏ sót một trường hợp mà căn cứ được trích dẫn nêu: “{case}” Hãy nêu mọi trường hợp căn cứ đưa ra."}
BRANCH_NOTICE = {"ko": "확인된 근거에는 다음 경우도 있습니다: “{case}”",
                 "en": "The verified evidence also states: “{case}”",
                 "vi": "Căn cứ đã xác minh còn nêu: “{case}”"}
MAX_QUOTED_CASE = 400
#: Mission 005-V (contract v16): the note sent with the one retry after a choice question was answered with only one of
#: its codes, and the system notice added when the code is still left out. {sentence} is the evidence text, quoted.
CHOICE_RETRY = {"ko": "질문은 {codes} 가운데 어느 쪽인지 묻습니다. 앞의 답에는 {code}에 관한 내용이 없습니다. 근거가 {code}에 대해 말하는 것도 쓰세요: “{sentence}”",
                "en": "The question asks which of {codes} applies. The previous answer did not cover {code}. Also state what the evidence says about {code}: “{sentence}”",
                "vi": "Câu hỏi hỏi trường hợp nào trong {codes} được áp dụng. Câu trả lời trước chưa nói về {code}. Hãy nêu cả điều căn cứ nói về {code}: “{sentence}”"}
#: Mission 005-X (contract v18): a part about one choice code gave a value the evidence states only for another code.
VALUE_RETRY = {"ko": "이번 호출은 {code}만 묻습니다. 앞의 답에 쓴 값({values})은 근거에서 다른 코드의 값이고 {code}의 값이 아닙니다. 근거가 {code}에 대해 말하는 문장: “{sentence}”",
               "en": "This call asks only about {code}. The value ({values}) in the previous answer is what the evidence states for another code, not for {code}. The evidence says about {code}: “{sentence}”",
               "vi": "Lần hỏi này chỉ về {code}. Giá trị ({values}) trong câu trả lời trước là giá trị căn cứ ghi cho mã khác, không phải cho {code}. Căn cứ nói về {code}: “{sentence}”"}
CHOICE_NOTICE = {"ko": "확인된 근거는 {code}에 대해 다음과 같이 적었습니다: “{sentence}”",
                 "en": "The verified evidence states about {code}: “{sentence}”",
                 "vi": "Căn cứ đã xác minh nêu về {code}: “{sentence}”"}
#: Mission 005-T (contract v14): one sentence per status or form problem, joined into the status_retry note.
STATUS_RETRY = {
    "conflict_not_labelled": {
        "ko": "인용한 두 근거가 같은 경우에 다른 값({a} / {b})을 말합니다. 두 값을 각 근거와 함께 쓰고, 두 근거를 모두 인용하고, 상태를 conflict로 하세요.",
        "en": "The cited records give different values for the same case ({a} / {b}). State both values with their records, cite both, and use status conflict.",
        "vi": "Hai căn cứ được trích dẫn nêu giá trị khác nhau cho cùng một trường hợp ({a} / {b}). Hãy nêu cả hai giá trị kèm căn cứ, trích dẫn cả hai và dùng trạng thái conflict."},
    "partial_without_uncovered": {
        "ko": "uncovered_items가 비어 있으므로 묻는 항목은 모두 근거에 있습니다. 상태를 answered로 하고 근거에 없는 항목 문장을 붙이지 마세요.",
        "en": "uncovered_items is empty, so every asked item is covered: use status answered and add no sentence about items not in the evidence.",
        "vi": "uncovered_items trống nên mọi mục được hỏi đều có trong căn cứ: hãy dùng trạng thái answered và không thêm câu về mục không có trong căn cứ."},
    "input_field_named": {
        "ko": "답에 입력 칸 이름({names})을 쓰지 마세요.",
        "en": "Do not write input field names ({names}) in the answer.",
        "vi": "Không viết tên trường đầu vào ({names}) trong câu trả lời."},
}
#: Mission 005-H: the system notice added to a released partial answer, by reply language.
NOTICE = {"ko": "확인된 근거에 없는 항목: {items}. 이 항목은 담당 기관에 직접 확인해 주세요.",
          "en": "Not covered by the verified evidence: {items}. Please check these with the responsible office.",
          "vi": "Không có trong căn cứ đã xác minh: {items}. Vui lòng hỏi trực tiếp cơ quan phụ trách về các mục này."}
#: Mission 005-M (contract v10): the sentence the model ends a partial answer with, naming the uncovered items.
UNCOVERED_SENTENCE = {"ko": "확인된 근거에 없는 항목: {items}.", "en": "Not covered by the verified evidence: {items}.",
                      "vi": "Không có trong căn cứ đã xác minh: {items}."}
SUBSTANTIVE = {"answered", "partial", "conflict"}
_CODE_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z]-\d{1,2}(?:-\d{1,2})?)(?![0-9-])")
# Mission 005-I: instructions about the reply written into the question (matched on NFC, case-insensitive).
_DIRECTIVE_RE = re.compile(
    r"(?:ignore|disregard|forget)\s+(?:all\s+|every\s+|any\s+|the\s+)?(?:previous\s+|earlier\s+|prior\s+|above\s+|other\s+)?(?:instructions?|rules?)"
    r"|(?:start|begin|end|prefix)\s+(?:your\s+|the\s+)?(?:reply|answer|response)\s+with"
    r"|(?:reply|respond|answer)\s+only\s+with|(?:say|write|print|include|add)\s+the\s+(?:word|phrase|code)"
    r"|(?:이전|앞의|위의|모든)\s*(?:지시|규칙|지침)[^.?!\n]{0,12}무시|(?:답|대답|답변)[^.?!\n]{0,20}(?:로|으로)\s*시작"
    r"|bỏ\s+qua\s+(?:mọi|tất\s+cả|các)?\s*(?:hướng\s+dẫn|chỉ\s+dẫn|quy\s+tắc)|bắt\s+đầu\s+(?:câu\s+)?trả\s+lời\s+bằng",
    re.IGNORECASE)
_SENTENCE_RE = re.compile(r"[^.?!。\n]*[.?!。\n]?")
_MARKER_RE = re.compile(r"[\"'“‘「]([^\"'”’」]{2,40})[\"'”’」]|(?<![\w-])([A-Z][A-Z0-9_]{3,}|[A-Z0-9_]*\d[A-Z][A-Z0-9_]*)(?![\w-])")


# Mission 005-L: reply-language requests (the forms of language_compliance._REQUESTS), with "or"
# chains such as "bằng tiếng Anh hoặc using Korean". A chain is a request only next to a reply word:
# after one ("answer in English", "trả lời bằng tiếng Anh", "답은 bằng tiếng Việt"), right before one
# ("영어로 답해", "in English please") or before a colon ("In English: ..."). "한국어로 된 서류" is not one.
_LANG_ITEM = (r"(?:(?:in|using|use)\s+(?:english|korean|vietnamese)|(?:bằng\s+)?tiếng\s+(?:anh|hàn|việt)"
              r"|(?:영어|한국어|한국말|베트남어)(?:로만?)?|english|korean|vietnamese)")
# Mission 005-M: a Korean particle glued to a non-Korean request ("bằng tiếng Việt로") goes with it.
_LANG_TAIL = r"(?:(?<=[a-zA-Zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ])(?:으로|로)(?:만)?)?"
_LANG_CHAIN_RE = re.compile(_LANG_ITEM + r"(?:\s*(?:,|/|\bor\b|\band\b|hoặc|hay|và|또는|혹은|이나|나)\s*" + _LANG_ITEM + r")*"
                            + _LANG_TAIL, re.IGNORECASE)
_CUE_BEFORE_RE = re.compile(r"(?:\b(?:answer|reply|respond|explain|tell\s+(?:me|us))\b|trả\s+lời|giải\s+thích|cho\s+biết"
                            r"|(?<![가-힣])답(?:은|을|변은|변을)?|대답(?:은|을)?)[^\n.?!:,;]{0,16}$", re.IGNORECASE)
# Mission 005-M: "In Korean or in Vietnamese, please: ..." — a comma may come before a please that ends the clause.
# Mission 005-N: "Using Korean, list …" — a request that opens the sentence, then a comma and an imperative.
_CUE_AFTER_RE = re.compile(r"^(?:\s*(?:답(?![안장])|대답|알려\s*주|설명\s*(?:해|하)|말해|부탁|please|plz|nhé|nha|giùm|giúp)|\s*,\s*(?:please|plz)\s*(?=[:.?!]|$)|\s*:)",
                           re.IGNORECASE)
_OPENING_RE = re.compile(r"^\s*,\s*(?:list|name|give|tell|explain|describe|write|show|summari[sz]e)\b", re.IGNORECASE)
_FILLER_RE = re.compile(
    r"(?:please|kindly|answer|reply|respond|explain|tell|me|us|it|this|only|either|both|is|are|one|fine|ok|okay|thanks?"
    r"|you|would|be|great|can|could|the|in|language|works|too|also|or|and"
    r"|답|변|은|을|대답|알려|설명|말해|주세요|줘요|주십시오|주실래요|주시겠어요|줘|주|세요|부탁|해요|합니다|드립니다|드려요|바랍니다"
    r"|해|요|만|도|돼요|됩니다|되요|괜찮아요|좋아요|상관없어요|둘|중|하나|어느|쪽|이든|든지|든"
    r"|vui|lòng|xin|hãy|trả|lời|giải|thích|cho|biết|tôi|giúp|đều|được|cũng|nhé|nha|ạ|cảm|ơn|thôi|chỉ|là|hoặc|hay"
    r"|có|thể|bạn|ngôn|ngữ|nào|giùm)+", re.IGNORECASE)


def _filler_only(text: str) -> bool:
    return all(_FILLER_RE.fullmatch(w) for w in re.findall(r"\w+", text))


def _language_request_spans(sentence: str) -> list:
    """(start, end) of the reply-language request chains in one sentence."""
    spans = []
    for m in _LANG_CHAIN_RE.finditer(sentence):
        chain = m.group(0)
        if not any(p.search(chain.lower()) for p in language_compliance._REQUESTS.values()):
            continue
        if _CUE_BEFORE_RE.search(sentence[:m.start()]) or _CUE_AFTER_RE.search(sentence[m.end():]) \
                or (not sentence[:m.start()].strip() and _OPENING_RE.search(sentence[m.end():])):
            spans.append((m.start(), m.end()))
    return spans


def remove_language_requests(question: str) -> dict:
    """Mission 005-L: the question without its reply-language requests (spec section 4).

    A sentence that is only a request ("Please answer in English.", "Trả lời bằng tiếng Anh hoặc bằng
    tiếng Hàn đều được.") is dropped; in "<request>: <question>" the part after the colon is kept; a request
    inside a real question ("수수료를 영어로 알려 주세요") loses only the language words.
    """
    text = unicodedata.normalize("NFC", question or "")
    out, removed = [], []
    for s in _SENTENCE_RE.findall(text):
        spans = _language_request_spans(s)
        if not spans:
            out.append(s)
            continue
        kept, last = [], 0
        for a, b in spans:
            kept.append(s[last:a])
            last = b
        kept.append(s[last:])
        rest = "".join(kept)
        colon = rest.find(":")
        if colon >= 0 and _filler_only(rest[:colon]) and re.search(r"\w", rest[colon + 1:]):
            out.append(" " + rest[colon + 1:].strip() + (" " if s.endswith(("\n", " ")) else ""))
            removed.append(s[:s.find(":") + 1].strip() if ":" in s else s.strip())
        elif _filler_only(rest):
            removed.append(s.strip())
        else:
            rest = re.sub(r"\s+([,.?!。:;])", r"\1", re.sub(r"[ \t]{2,}", " ", rest))
            rest = re.sub(r",\s*(?=[,.?!。:;])", "", rest)   # 005-M: "fee, , please?" -> "fee, please?"
            rest = re.sub(r"^\s*,\s*", "", rest)            # 005-N: "Using Korean, list …" -> "list …"
            out.append(rest)
            removed.extend(s[a:b] for a, b in spans)
    return {"question": re.sub(r"\s{2,}", " ", "".join(out)).strip(), "removed": removed}


def question_directives(question: str, evidence_texts: list) -> dict:
    """Instruction sentences in the question and the marker tokens they demand (not found in any evidence)."""
    text = unicodedata.normalize("NFC", question or "")
    sentences = [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip() and _DIRECTIVE_RE.search(s)]
    body = unicodedata.normalize("NFC", "\n".join(evidence_texts)).casefold()
    markers = []
    for s in sentences:
        for quoted, bare in _MARKER_RE.findall(s):
            token = (quoted or bare).strip()
            if token and not _CODE_RE.fullmatch(token) and token.casefold() not in body and token not in markers:
                markers.append(token)
    return {"sentences": sentences, "markers": markers}

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


def question_for_model(question: str, evidence_texts: list) -> dict:
    """Mission 005-J: the question without its reply-instruction sentences (spec section 4); 005-L: and
    without its reply-language requests (remove_language_requests).

    A sentence of the form "<instruction>: <question>" keeps the part after the colon. If nothing
    would be left, the question is passed unchanged (the answer guard still checks markers).
    """
    found = question_directives(question, evidence_texts)
    text = unicodedata.normalize("NFC", question or "")
    removed = []
    for s in found["sentences"]:
        m = _DIRECTIVE_RE.search(s)
        colon = s.find(":", m.end()) if m else -1
        keep = s[colon + 1:].strip() if colon >= 0 else ""
        text = text.replace(s, keep, 1)
        removed.append(s if not keep else s[:colon + 1].strip())
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Mission 005-L: then the reply-language requests; reply_language still reads the user's question.
    lang = remove_language_requests(text)
    if not re.search(r"\w", lang["question"]):
        return {"question": question, "removed": [], "language_removed": [], "markers": found["markers"]}
    return {"question": lang["question"], "removed": removed, "language_removed": lang["removed"],
            "markers": found["markers"]}


def reply_language(question: str) -> dict:
    """Deterministic: explicit request, then question language, then Korean (language_compliance)."""
    return language_compliance.required_language(question)


def system_response(kind: str, lang: str) -> dict:
    status = "clarify" if kind in ("location", "status_code") else "insufficient_evidence"
    return {"status": status, "answer": FALLBACK[kind][lang], "citations": []}


def conflict_records(evidence: list) -> list:
    """Mission 005-U: each pair of records whose texts differ only in their numbers, as [[id_a, id_b], ...] in
    evidence order (status_check's rule: leading [title] removed, status codes kept)."""
    return [[a["id"], b["id"]] for i, a in enumerate(evidence) for b in evidence[i + 1:]
            if status_check.conflicting_values([a.get("text", ""), b.get("text", "")])]


def choice_marks(question: str, evidence: list) -> list:
    """Mission 005-W: the codes a choice question asks between that the evidence names, in question order,
    when there are two or more (choice_coverage's rule); otherwise []."""
    named = [c for c in choice_coverage.choice_codes(question)
             if any(c in choice_coverage._CODE.findall(e.get("text", "")) for e in evidence)]
    return named if len(named) >= 2 else []


def prepare(question: str, intake: Optional[Mapping], candidates: list, registry: Optional[TrustRegistry],
            evaluation_date: str) -> dict:
    """Pre-inference: admissibility, outcome, and the exact items the model would receive (one per part)."""
    selection = select_admissible_evidence(question, intake, candidates, registry, evaluation_date)
    lang = reply_language(question)
    cleaned = question_for_model(question, [e.get("text", "") for e in selection["admissible"]])
    items, parts = [], []
    if selection["outcome"] == "proceed":
        code = lang["language"]
        split = (selection.get("subcode_parts") or []) + (selection.get("situation_parts") or [])
        groups = [(p.get("status_code"), p.get("location"), None, [e for e in selection["admissible"] if e["id"] in p["evidence_ids"]])
                  for p in split]
        # Mission 005-X: a choice question that is not split otherwise is asked one choice code at a time, in question
        # order. Every part sees all the admissible evidence; the answers are joined as sub-code parts are (005-J).
        choice = [] if groups or not CHOICE_PARTS else choice_marks(selection.get("context_question", question), selection["admissible"])
        groups = groups or [(None, None, c, selection["admissible"]) for c in choice] or [(None, None, None, selection["admissible"])]
        ctx = selection["context"] or {}
        for sub, loc, part_code, evidence in groups:
            # v5+ names the uncovered items in the reply language instead of internal keys.
            # 005-N: items are read from the question without the document names it quotes.
            keys = uncovered_items(selection.get("context_question", question), evidence) if (sub or loc) \
                else selection["uncovered_items"]
            system = {"reply_language": code, "uncovered_items": [ITEM_LABELS[i][code] for i in keys]}
            if keys:
                system["uncovered_sentence"] = UNCOVERED_SENTENCE[code].format(items=", ".join(system["uncovered_items"]))
            if sub:
                system["scope_status_code"] = sub
            if loc:
                system["scope_location"] = loc
            if ctx.get("as_of_source") in ("question", "intake"):
                system["as_of"] = ctx["as_of"]
            pairs = conflict_records(evidence)
            if pairs:
                system["conflict_records"] = pairs
            codes = choice or choice_marks(selection.get("context_question", question), evidence)
            if codes:
                system["choice_codes"] = codes
            if part_code:
                system["choice_part"] = part_code
            items.append({"question": cleaned["question"], "evidence": evidence, "system": system})
            parts.append({"status_code": sub, "location": loc, "evidence": evidence, "uncovered_items": keys,
                          "choice_part": part_code, "choice_codes": codes if part_code else None})
    return {"selection": selection, "reply_language": lang, "question": question,
            "question_directives_removed": cleaned["removed"],
            "question_language_requests_removed": cleaned["language_removed"], "model_items": items, "parts": parts,
            "model_item": items[0] if len(items) == 1 else None}


def _mentions_item(answer: str, item: str) -> bool:
    from waymaker_ai.evidence_admissibility import ITEM_ASK
    return bool(ITEM_ASK[item].search(unicodedata.normalize("NFC", answer)))


def _quoted(case: str) -> str:
    case = " ".join(case.split())
    return case if len(case) <= MAX_QUOTED_CASE else case[:MAX_QUOTED_CASE - 1] + "…"


def validate_generated_answer(raw: Optional[str], prepared: Mapping, candidates: list,
                              registry: TrustRegistry, part: Optional[int] = None, branch_notice: bool = False,
                              choice_notice: bool = False, value_final: bool = False) -> dict:
    """The guard decision for one model output (trusted_evidence_spec.md section 5).

    With `part`, the output answers one sub-code: only that part's evidence is admissible, its own
    uncovered items apply, and the sub-code stands in for the question's code in the scope check.
    A case of the cited evidence that the answer left out (Mission 005-R) never changes the decision: it
    asks for one retry, or with `branch_notice` (after that retry) it adds a system notice quoting the case.
    Mission 005-V: the same for a choice question answered with only one of its codes, with `choice_notice`.
    Mission 005-X: a part about one choice code is not checked for the other codes (the joined answer covers
    them); Mission 005-Y: it is checked for its own code, as a whole answer is for the question's codes (005-V); a value it gives that the evidence states only for another choice code asks for one retry, and
    with `value_final` (after that retry) withholds.
    """
    selection = prepared["selection"]
    choice_part = prepared["parts"][part].get("choice_part") if part is not None else None
    if part is not None:
        p = prepared["parts"][part]
        context = dict(selection["context"] or {})
        if p.get("status_code"):
            context["status_code"] = p["status_code"]
        if p.get("location"):
            context["location"] = p["location"]
        selection = {**selection, "admissible": p["evidence"], "uncovered_items": p["uncovered_items"], "context": context}
    admissible_ids = {e["id"] for e in selection["admissible"]}
    lang = prepared["reply_language"]["language"]
    question = prepared.get("question") or prepared["model_item"]["question"]
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
    directives = question_directives(question, [e.get("text", "") for e in selection["admissible"]])
    followed = [m for m in directives["markers"] if m.casefold() in unicodedata.normalize("NFC", answer).casefold()]
    if followed:
        findings.append({"check": "question_instruction", "kind": "question_instruction_followed", "detail": followed,
                         "effect": "withhold"})
    if status in SUBSTANTIVE:
        support = claim_support_validation.check(answer, question, candidates, cites, admissible_map, with_source=True,
                                                 ages_apart=True, vi_dates=True, caps_apart=True)
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
        asked = requested_items(selection.get("context_question", question))
        if asked and set(asked) <= set(selection["uncovered_items"]):
            # Unreachable when pre-inference withholds such questions; kept as a second line.
            findings.append({"check": "partial", "kind": "no_requested_item_covered", "detail": asked, "effect": "withhold"})
    # 005-K: Korean names copied from the admissible evidence (titles and text) are not counted.
    names = [x for e in selection["admissible"] for x in (e.get("title", ""), e.get("text", ""))]
    language = language_compliance.check(question, answer, lang, protected_texts=names)
    if language["result"] == "fail":
        findings.append({"check": "language", "kind": language["reason"], "detail": lang, "effect": "review_required"})
    if status in SUBSTANTIVE:
        cited_texts = [e.get("text", "") for e in selection["admissible"] if e["id"] in cites]
        left_out = branch_coverage.omitted_cases(answer, cited_texts, (selection["context"] or {}).get("status_code"))
        if left_out:
            findings.append({"check": "branches", "kind": "case_omitted", "detail": [c["case"] for c in left_out],
                             "effect": "system_notice" if branch_notice else "branch_retry"})
        left_codes = [] if choice_part else \
            choice_coverage.omitted_choices(selection.get("context_question", question), answer, cited_texts)
        if choice_part:
            # Mission 005-Y: a part that does not name its own choice code, though the cited evidence does, is asked
            # once more (choice_retry) and, with `choice_notice`, gets a notice quoting the code's evidence sentence.
            in_answer = set(choice_coverage._CODE.findall(unicodedata.normalize("NFC", answer)))
            in_cited = {c for t in cited_texts for c in choice_coverage._CODE.findall(unicodedata.normalize("NFC", t or ""))}
            codes = prepared["parts"][part]["choice_codes"]
            if choice_part not in in_answer and choice_part in in_cited:
                findings.append({"check": "choice", "kind": "choice_part_omitted",
                                 "detail": [{"code": choice_part, "codes": codes, "named": [c for c in codes if c in in_answer],
                                             "sentence": choice_coverage.sentence_naming(choice_part, cited_texts)}],
                                 "effect": "system_notice" if choice_notice else "choice_retry"})
            swapped = choice_coverage.swapped_values(choice_part, prepared["parts"][part]["choice_codes"], answer,
                                                     [e.get("text", "") for e in selection["admissible"]],
                                                     selection.get("context_question", question))
            if swapped:
                findings.append({"check": "choice_value", "kind": "value_of_other_code", "detail": swapped,
                                 "effect": "withhold" if value_final else "value_retry"})
        if left_codes:
            findings.append({"check": "choice", "kind": "choice_omitted", "detail": left_codes,
                             "effect": "system_notice" if choice_notice else "choice_retry"})
        for problem in status_check.problems(status, answer, cited_texts, selection["uncovered_items"]):
            findings.append({"check": "status", "kind": problem["kind"], "detail": problem["detail"], "effect": "status_retry"})
    effects = {f.get("effect") for f in findings}
    decision = "withhold" if "withhold" in effects else "review_required" if "review_required" in effects else "release"
    notices = []
    missing = next((f["detail"] for f in findings if f["check"] == "partial" and f.get("effect") == "system_notice"), None)
    if missing:
        notices.append(NOTICE[lang].format(items=", ".join(ITEM_LABELS[i][lang] for i in missing)))
    notices += [BRANCH_NOTICE[lang].format(case=_quoted(c)) for f in findings
                if f["check"] == "branches" and f.get("effect") == "system_notice" for c in f["detail"]]
    notices += [CHOICE_NOTICE[lang].format(code=c["code"], sentence=_quoted(c["sentence"])) for f in findings
                if f["check"] == "choice" and f.get("effect") == "system_notice" for c in f["detail"] if c["sentence"]]
    notice = " ".join(notices) if decision == "release" and notices else None
    return {**done(decision), "parsed": parsed, "language": language["result"], "system_notice": notice}


def _join_parts(guards: list, raws: list) -> tuple[dict, Optional[str]]:
    """Mission 005-J: one guard result and one composed raw output from per-sub-code parts (deterministic).

    The worst decision wins. When every part is released, the answers are joined in sub-code order (an
    identical answer text only once, Mission 005-Y),
    citations are united, and the status is answered (all answered), conflict (any conflict) or partial.
    The composed raw output joins the parsed raw parts the same way, so the raw channel scores what the
    model wrote; if a part did not parse, that part's raw text is the composed output.
    """
    decision = min((g["decision"] for g in guards), key=DECISION_ORDER.index)
    findings = [{**f, "part": i} for i, g in enumerate(guards) for f in g["findings"]]
    parsed = [g.get("parsed") for g in guards]

    def joined(items):
        statuses = [x["status"] for x in items]
        status = "answered" if all(s == "answered" for s in statuses) else "conflict" if "conflict" in statuses else "partial"
        substantive = [x for x in items if x["status"] in SUBSTANTIVE] or items
        cites = list(dict.fromkeys(c for x in items for c in x["citations"]))
        # Mission 005-Y: an answer text two parts both gave is joined once (DEV-20 v2 003/004 in 005-X).
        return {"status": status if any(x["status"] in SUBSTANTIVE for x in items) else items[0]["status"],
                "answer": "\n".join(dict.fromkeys(x["answer"] for x in substantive)), "citations": cites}
    composed_raw = next((r for r, x in zip(raws, parsed) if x is None), None)
    if composed_raw is None:
        composed_raw = json.dumps(joined(parsed), ensure_ascii=False)
    out = {"decision": decision, "findings": findings, "parts": [g["decision"] for g in guards],
           "parsed": joined(parsed) if all(x is not None for x in parsed) else None,
           "language": "fail" if any(g.get("language") == "fail" for g in guards) else "pass"}
    notices = [g["system_notice"] for g in guards if g.get("system_notice")]
    out["system_notice"] = " ".join(notices) if decision == "release" and notices else None
    return out, composed_raw


def _input_sha(item: Mapping) -> str:
    return hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _language_only(guard: Mapping) -> bool:
    """Mission 005-P: the reply language is the only reason this answer is held back."""
    blocking = [f for f in guard["findings"] if f.get("effect") in ("withhold", "review_required")]
    return guard["decision"] == "review_required" and bool(blocking) and all(f["check"] == "language" for f in blocking)


def status_note(found: list, lang: str) -> str:
    """Mission 005-T: the status_retry note for the problems status_check found, in the reply language."""
    parts = []
    for f in found:
        text = STATUS_RETRY[f["kind"]][lang]
        if f["kind"] == "conflict_not_labelled":
            text = text.format(a=", ".join(f["detail"][0]), b=", ".join(f["detail"][1]))
        elif f["kind"] == "input_field_named":
            text = text.format(names=", ".join(f["detail"]))
        parts.append(text)
    return " ".join(parts)


def _status_problems(guard: Mapping) -> list:
    """Mission 005-T: the status or form problems of a released part, which ask for one retry."""
    if guard["decision"] != "release":
        return []
    return [f for f in guard["findings"] if f.get("effect") == "status_retry"]


def choice_note(left: list, lang: str) -> str:
    """Mission 005-V: the choice_retry note for the question codes an answer left out, in the reply language."""
    return " ".join(CHOICE_RETRY[lang].format(codes=", ".join(c["codes"]), code=c["code"],
                                              sentence=_quoted(c["sentence"])) for c in left)


def _choices_left_out(guard: Mapping) -> list:
    """Mission 005-V: the question codes a released answer left out, which ask for one retry."""
    if guard["decision"] != "release":
        return []
    return [c for f in guard["findings"] if f.get("effect") == "choice_retry" for c in f["detail"]]


def value_note(swapped: list, lang: str) -> str:
    """Mission 005-X: the value_retry note for a part that gave another choice code's value, in the reply language."""
    return " ".join(VALUE_RETRY[lang].format(code=c["code"], values=", ".join(c["values"]), sentence=_quoted(c["sentence"]))
                    for c in swapped)


def _values_swapped(guard: Mapping) -> list:
    """Mission 005-X: the values a released choice part gave for another code, which ask for one retry."""
    if guard["decision"] != "release":
        return []
    return [c for f in guard["findings"] if f.get("effect") == "value_retry" for c in f["detail"]]


def _cases_left_out(guard: Mapping) -> list:
    """Mission 005-R: the evidence cases a released answer left out, which ask for one retry."""
    if guard["decision"] != "release":
        return []
    return [c for f in guard["findings"] if f.get("effect") == "branch_retry" for c in f["detail"]]


def run_case(question: str, intake: Optional[Mapping], candidates: list, registry: Optional[TrustRegistry],
             evaluation_date: str, generate: Callable[[dict], Optional[str]]) -> dict:
    """One question end to end. `generate(model_item)` returns the raw model text; it is called only on proceed,
    once per sub-code part when the evidence splits by sub-code (Mission 005-J), once more for a part the
    guard holds back only for its reply language (Mission 005-P), once per choice code of a choice question
    (Mission 005-X) and once more for a choice part that gave another code's value, once more as a single call when the
    choice parts of a comparison question disagree (Mission 005-Z), once more for a released part that left
    out a case of its evidence (Mission 005-R), once more for a released part that answered a choice question
    with only one of its codes (Mission 005-V), and once more for a released part whose status or form is
    visibly wrong (Mission 005-T)."""
    prepared = prepare(question, intake, candidates, registry, evaluation_date)
    sel, lang = prepared["selection"], prepared["reply_language"]["language"]
    record = {"pre_inference": sel["outcome"], "pre_inference_reason": sel["reason"], "context": sel["context"],
              "trust_decisions": sel["decisions"], "admissible_ids": [e["id"] for e in sel["admissible"]],
              "uncovered_items": sel["uncovered_items"], "reply_language": prepared["reply_language"],
              "question_directives_removed": prepared["question_directives_removed"],
              "question_language_requests_removed": prepared["question_language_requests_removed"],
              "subcode_parts": sel.get("subcode_parts") or [], "situation_parts": sel.get("situation_parts") or [],
              "model_called": False, "raw_output": None, "guard": None, "language_retry": None, "value_retry": None,
              "branch_retry": None, "choice_retry": None, "status_retry": None, "conclusion_retry": None}
    if sel["outcome"] == "system_withheld":
        released, provenance = system_response("withheld", lang), "system_withheld"
    elif sel["outcome"] == "review_required":
        released, provenance = system_response("review", lang), "review_required"
    elif sel["outcome"] == "system_clarification":
        released, provenance = system_response(sel["clarify_on"], lang), "system_clarification"
    else:
        items = prepared["model_items"]
        split = len(items) > 1
        raws = [generate(item) for item in items]
        guards = [validate_generated_answer(r, prepared, candidates, registry, part=i if split else None)
                  for i, r in enumerate(raws)]
        guard, raw = _join_parts(guards, raws) if split else (guards[0], raws[0])
        shas = [_input_sha(item) for item in items]
        record.update(model_called=True, raw_output=raw, guard=guard, model_input_sha256=shas[0],
                      model_input_sha256s=shas, raw_outputs=raws if split else None)
        # Mission 005-P: one more call for each part held back only for its reply language, in part order.
        retry_parts = [i for i, g in enumerate(guards) if _language_only(g)]
        final_raws, final_guards = list(raws), list(guards)
        if retry_parts:
            for i in retry_parts:
                item = {**items[i], "system": {**items[i]["system"], "language_retry": LANGUAGE_RETRY[lang]}}
                final_raws[i] = generate(item)
                final_guards[i] = validate_generated_answer(final_raws[i], prepared, candidates, registry,
                                                            part=i if split else None)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
            guard, retry_raw = _join_parts(final_guards, final_raws) if split else (final_guards[0], final_raws[0])
            record["language_retry"] = {"parts": retry_parts, "raw_outputs": [final_raws[i] for i in retry_parts],
                                        "raw_output": retry_raw, "guard": guard}
        # Mission 005-X: one more call for each released choice part that gave a value the evidence states only for
        # another choice code, in part order. The retried answer is used when the guard releases it; otherwise the
        # earlier answer is checked again with value_final, so a value still swapped withholds the joined answer.
        value_parts = [i for i, g in enumerate(final_guards) if _values_swapped(g)]
        if value_parts:
            value_raws = []
            for i in value_parts:
                note = value_note(_values_swapped(final_guards[i]), lang)
                item = {**items[i], "system": {**items[i]["system"], "value_retry": note}}
                retried = generate(item)
                value_raws.append(retried)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
                retried_guard = validate_generated_answer(retried, prepared, candidates, registry,
                                                          part=i if split else None, value_final=True)
                if retried_guard["decision"] == "release":
                    final_raws[i], final_guards[i] = retried, retried_guard
                else:
                    final_guards[i] = validate_generated_answer(final_raws[i], prepared, candidates, registry,
                                                                part=i if split else None, value_final=True)
            guard, value_raw = _join_parts(final_guards, final_raws) if split else (final_guards[0], final_raws[0])
            record["value_retry"] = {"parts": value_parts, "raw_outputs": value_raws, "raw_output": value_raw,
                                     "guard": guard}
        # Mission 005-R: one more call for each released part that left out a case of its evidence, in part order.
        # The retried answer is released when the guard releases it; otherwise the earlier answer stays. Either
        # way a case still left out is quoted in a system notice.
        branch_parts = [i for i, g in enumerate(final_guards) if _cases_left_out(g)]
        if branch_parts:
            branch_raws = []
            for i in branch_parts:
                note = " ".join(BRANCH_RETRY[lang].format(case=_quoted(c)) for c in _cases_left_out(final_guards[i]))
                item = {**items[i], "system": {**items[i]["system"], "branch_retry": note}}
                retried = generate(item)
                branch_raws.append(retried)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
                retried_guard = validate_generated_answer(retried, prepared, candidates, registry,
                                                          part=i if split else None, branch_notice=True, value_final=True)
                if retried_guard["decision"] == "release":
                    final_raws[i], final_guards[i] = retried, retried_guard
                else:
                    final_guards[i] = validate_generated_answer(final_raws[i], prepared, candidates, registry,
                                                                part=i if split else None, branch_notice=True, value_final=True)
            guard, branch_raw = _join_parts(final_guards, final_raws) if split else (final_guards[0], final_raws[0])
            record["branch_retry"] = {"parts": branch_parts, "raw_outputs": branch_raws, "raw_output": branch_raw,
                                      "guard": guard}
        # Mission 005-V: one more call for each released part that answered a choice question with only one of its
        # codes, in part order. The retried answer is released when the guard releases it; otherwise the earlier
        # answer stays. Either way a code still left out is quoted in a system notice.
        choice_parts = [i for i, g in enumerate(final_guards) if _choices_left_out(g)]
        if choice_parts:
            choice_raws = []
            for i in choice_parts:
                note = choice_note(_choices_left_out(final_guards[i]), lang)
                item = {**items[i], "system": {**items[i]["system"], "choice_retry": note}}
                retried = generate(item)
                choice_raws.append(retried)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
                retried_guard = validate_generated_answer(retried, prepared, candidates, registry,
                                                          part=i if split else None, branch_notice=True, choice_notice=True,
                                                          value_final=True)
                if retried_guard["decision"] == "release":
                    final_raws[i], final_guards[i] = retried, retried_guard
                else:
                    final_guards[i] = validate_generated_answer(final_raws[i], prepared, candidates, registry,
                                                                part=i if split else None, branch_notice=True,
                                                                choice_notice=True, value_final=True)
            guard, choice_raw = _join_parts(final_guards, final_raws) if split else (final_guards[0], final_raws[0])
            record["choice_retry"] = {"parts": choice_parts, "raw_outputs": choice_raws, "raw_output": choice_raw,
                                      "guard": guard}
        # Mission 005-T: one more call for each released part whose status or form is visibly wrong, in part order.
        # The retried answer is released when the guard releases it (keeping any branch notice); otherwise the
        # earlier answer stays.
        status_parts = [i for i, g in enumerate(final_guards) if _status_problems(g)]
        if status_parts:
            status_raws = []
            for i in status_parts:
                note = status_note([{"kind": f["kind"], "detail": f["detail"]} for f in _status_problems(final_guards[i])], lang)
                item = {**items[i], "system": {**items[i]["system"], "status_retry": note}}
                retried = generate(item)
                status_raws.append(retried)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
                retried_guard = validate_generated_answer(retried, prepared, candidates, registry,
                                                          part=i if split else None, branch_notice=True, choice_notice=True,
                                                          value_final=True)
                if retried_guard["decision"] == "release":
                    final_raws[i], final_guards[i] = retried, retried_guard
            guard, status_raw = _join_parts(final_guards, final_raws) if split else (final_guards[0], final_raws[0])
            record["status_retry"] = {"parts": status_parts, "raw_outputs": status_raws, "raw_output": status_raw,
                                      "guard": guard}
        # Mission 005-Z: the choice parts of a comparison question claim different codes, or claim a code that does
        # not hold the lowest/highest own value. The question is asked once more as one call (choice_codes, no
        # choice_part, the 005-W item); a single answer the guard releases and that claims one code consistent with
        # the values is released, otherwise nothing is.
        if split and guard["decision"] == "release" and all(p.get("choice_part") for p in prepared["parts"]):
            question_c = sel.get("context_question", question)
            codes = prepared["parts"][0]["choice_codes"]
            texts = [e.get("text", "") for e in sel["admissible"]]
            answers = [g["parsed"]["answer"] for g in final_guards]
            reason = {"conflict": choice_conclusion.conflict(question_c, answers, codes),
                      "against_values": choice_conclusion.against_values(question_c, answers, codes, texts)}
            if reason["conflict"] or reason["against_values"]:
                item = {**items[0], "system": {k: v for k, v in items[0]["system"].items() if k != "choice_part"}}
                retried = generate(item)
                record["model_input_sha256s"] = record["model_input_sha256s"] + [_input_sha(item)]
                single = validate_generated_answer(retried, prepared, candidates, registry, part=None, branch_notice=True,
                                                   choice_notice=True, value_final=True)
                after = {}
                if single["decision"] == "release":
                    one = [single["parsed"]["answer"]]
                    after = {"conflict": choice_conclusion.conflict(question_c, one, codes),
                             "against_values": choice_conclusion.against_values(question_c, one, codes, texts)}
                if single["decision"] == "release" and not after["conflict"] and not after["against_values"]:
                    guard = single
                else:
                    guard = {"decision": "withhold", "parsed": None, "language": single.get("language"), "system_notice": None,
                             "findings": [{"check": "conclusion", "kind": "choice_parts_disagree", "detail": reason,
                                           "effect": "withhold"},
                                          {"check": "conclusion", "kind": "single_answer_not_released_or_disagrees",
                                           "detail": {"decision": single["decision"], **after}, "effect": "withhold"}]}
                record["conclusion_retry"] = {"reason": reason, "raw_output": retried, "guard": guard}
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
