"""Fine procedure identity, independent of status and legal eligibility.

Uses B2's repository-owned 16-procedure catalog and object/action vocabulary.
Object × action composition distinguishes a card from a passport and a report
from an extension. The only taxonomy conversion is fine -> coarse. Missing or
ambiguous information stays absent. No benchmark, network or model is read.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .status_code_parser import transition_pair

FINE_TO_COARSE = {
    "visa_issuance": "visa_issuance",
    "visa_issuance_confirmation": "visa_issuance_confirmation",
    "electronic_visa": None,
    "status_grant": "status_grant",
    "status_change": "status_change",
    "extension": "extension",
    "registration": "registration",
    "card_reissue": None,
    "activities_outside_status": "activities_outside_status",
    "part_time_work": None,
    "workplace_change": "workplace_change",
    "workplace_report": None,
    "reentry": "reentry",
    "residence_report": "address_report",
    "registration_info_report": "reporting_duty",
    "program_condition_change": None,
}


@dataclass(frozen=True)
class ProcedureDecision:
    fine: Optional[str] = None
    candidates: tuple[str, ...] = ()
    reason: str = "no_procedure"

    @property
    def coarse(self) -> Optional[str]:
        return FINE_TO_COARSE.get(self.fine)


@lru_cache(maxsize=1)
def vocabulary() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "data/procedure_classifier_lexicon.json").read_text())


def _has(text: str, terms) -> bool:
    return any(term.lower() in text for term in terms)


def classify_procedure(question: str) -> ProcedureDecision:
    text = str(question or "").strip().lower()
    if not text:
        return ProcedureDecision()
    data = vocabulary()
    objects = {name for name, terms in data["objects"].items() if _has(text, terms)}
    actions_text = text
    for term in sorted({term.lower() for terms in data["objects"].values() for term in terms}, key=lambda t: (-len(t), t)):
        actions_text = actions_text.replace(term, " ")
    actions = {name for name, terms in data["actions"].items() if _has(actions_text, terms)}

    def decide(fine, reason):
        return ProcedureDecision(fine, (fine,), reason)

    # Explicit specialized procedures outrank generic "registration", "change",
    # or "renewal" words inside their names. This list contains taxonomy, not codes.
    specialized = {
        "visa_issuance_confirmation", "electronic_visa", "program_condition_change",
        "workplace_report", "part_time_work", "activities_outside_status", "reentry",
        "status_grant",
    }
    hits = [(len(k), p["id"]) for p in data["procedures"] for k in p["keywords"] if k.lower() in text]
    specific = sorted(((n,p) for n,p in hits if p in specialized), reverse=True)
    if specific:
        return decide(specific[0][1], "explicit_specialized_procedure")

    # Supplemental language expressions are procedure-level, never tied to a code.
    if re.search(r"査証発給認定書|签证签发认定书|visa\s+issuance\s+confirmation|certificate\s+for\s+visa\s+issuance", text, re.I):
        return decide("visa_issuance_confirmation", "explicit_confirmation")
    if re.search(r"再入境|再入国|tái nhập cảnh|повторн(?:ый|ого)\s+въезд", text, re.I):
        return decide("reentry", "explicit_reentry")
    if "registration_info" in objects:
        return decide("registration_info_report", "registration_information")
    if "passport" in objects:
        # A passport is issued/renewed by a passport authority, not by Korean
        # immigration. "renewed passport" and "new passport" in the shared
        # vocabulary are NOT evidence that a change report was requested.
        embassy_only = bool(re.search(r"대사관|영사관|embassy|consulat|공관", text, re.I))
        immigration_filing = bool(re.search(
            r"여권.{0,25}(?:정보\s*(?:변경|신고)|변경\s*신고|신고)"
            r"|(?:신고|통보|등록사항\s*변경).{0,25}여권"
            r"|\b(?:report|notify|declare|update|file)\b.{0,55}\bpassport\b"
            r"|\bpassport\b.{0,55}\b(?:report|notification|filing|update)\b",
            text, re.I,
        ))
        passport_service = bool(re.search(
            r"여권\s*(?:갱신|연장|재발급|발급|교체)"
            r"|\bpassport\b.{0,20}\b(?:renew\w*|reissu\w*|replac\w*|extend\w*)\b"
            r"|\b(?:renew\w*|reissu\w*|replac\w*|extend\w*)\b.{0,22}\bpassport\b",
            text, re.I,
        ))
        if immigration_filing and not (embassy_only and not re.search(r"출입국|immigration", text, re.I)):
            return decide("registration_info_report", "passport_information_report")
        if passport_service:
            return ProcedureDecision(reason="passport_service_not_immigration")
    # "First ever card" is an initial registration even if informal wording
    # such as "new card" also appears in the reissue vocabulary.
    first_card = bool(re.search(
        r"외국인등록증.{0,15}(?:처음|최초)|(?:처음|최초|첫\s*번째).{0,20}(?:외국인등록증|등록증|거소증)"
        r"|\b(?:first\s*(?:time|ever)|initial|never\s+had)\b.{0,45}\b(?:card|arc)\b"
        r"|\b(?:card|arc)\b.{0,45}\b(?:first\s*(?:time|ever)|initial)\b",
        text, re.I,
    ))
    lost_card = bool(re.search(r"분실|잃어버|잃었|lost|replac|reissu|훼손|damaged", text, re.I))
    if "card" in objects and first_card and not lost_card:
        return decide("registration", "first_card_registration")
    if "card" in objects and "reissue" in actions:
        # "new card" alone does not reveal first registration vs replacement.
        if not lost_card and not re.search(r"재발급|분실|re-?issu|replac|again|다시", text, re.I):
            return ProcedureDecision(candidates=("card_reissue", "registration"), reason="card_action_missing")
        return decide("card_reissue", "card_reissue")
    if "card" in objects and "register" in actions:
        return decide("registration", "first_card_registration")
    if "card" in objects and not actions.intersection({"register", "change", "extend"}):
        return ProcedureDecision(candidates=("card_reissue", "registration"), reason="card_action_missing")
    if "address" in objects and not ("residence_proof" in objects and not actions.intersection({"move", "change"})):
        if actions.intersection({"change", "move"}) or "extend" not in actions:
            return decide("residence_report", "address_report")
    if objects.intersection({"school", "name"}) and "change" in actions:
        return decide("registration_info_report", "registered_information_change")
    if "extend" in actions:
        return decide("extension", "stay_extension")
    if re.search(r"продлить|продление", text, re.I):
        return decide("extension", "stay_extension_ru")
    if transition_pair(question):
        return decide("status_change", "directional_transition")
    if re.search(r"(?:회사|직장|일자리|근무지)\s*(?:을|를|이|가)?\s*(?:옮기|옮길|옮겨|바꾸|바꿔|변경)|\b(?:change|changing|switch)\s+(?:my\s+)?(?:job|employer|company)\b|换工作|换雇主|chuyển\s+(?:nơi\s+làm\s+việc|công\s+việc)", text, re.I):
        return decide("workplace_change", "workplace_move")
    if hits:
        fine = sorted(hits, key=lambda h: (-h[0], h[1]))[0][1]
        if fine == "registration" and "card" in objects and "register" not in actions:
            return ProcedureDecision(candidates=("card_reissue", "registration"), reason="card_action_missing")
        # "lost" alone never implies a lost residence card.
        if fine == "card_reissue" and "card" not in objects and not re.search(r"재발급|re-?issu", text):
            return ProcedureDecision(reason="reissue_object_missing")
        return decide(fine, "catalog_keyword")
    return ProcedureDecision()
