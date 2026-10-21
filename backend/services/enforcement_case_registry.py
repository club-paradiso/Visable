"""Independent, privacy-safe multi-subject enforcement case registry.

Keeps an administrative notice, confirmed payment, court fine and review result
as distinct observations. This is *not* the legacy prediction ground-truth
contract: no registry event is automatically promoted into model evaluation.
No code from third-party law MCP implementations is used.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit
import re

REGISTRY_SCHEMA_VERSION = "1.0.0"
SUBJECT_ROLES = frozenset({"FOREIGN_NATIONAL", "EMPLOYER", "BUSINESS_ENTITY", "OTHER", "UNKNOWN"})
OBSERVATION_TYPES = frozenset({
    "PENALTY_NOTICE", "PENALTY_PAYMENT_CONFIRMED", "COURT_FINE",
    "DEPARTURE_ORDER", "DEPORTATION", "STAY_RESTRICTION",
    "APPEAL_DISMISSED", "APPEAL_REJECTED", "APPEAL_ACCEPTED",
})
MONETARY_OBSERVATIONS = frozenset({"PENALTY_NOTICE", "PENALTY_PAYMENT_CONFIRMED", "COURT_FINE"})
STAGES_BY_TYPE = {
    "PENALTY_NOTICE": {"NOTIFIED"},
    "PENALTY_PAYMENT_CONFIRMED": {"PAID"},
    "COURT_FINE": {"SENTENCED", "FINAL"},
    "DEPARTURE_ORDER": {"ORDERED", "FINAL"},
    "DEPORTATION": {"ORDERED", "FINAL"},
    "STAY_RESTRICTION": {"ORDERED", "FINAL"},
    "APPEAL_DISMISSED": {"DECIDED", "FINAL"},
    "APPEAL_REJECTED": {"DECIDED", "FINAL"},
    "APPEAL_ACCEPTED": {"DECIDED", "FINAL"},
}
VERIFICATION_STATES = frozenset({"STAGED", "INDEPENDENTLY_REVIEWED"})
SOURCE_STATES = frozenset({"STAGED", "SOURCE_VERIFIED"})
SOURCE_TYPES = frozenset({
    "OFFICIAL_ADMINISTRATIVE_DECISION", "COURT_DECISION", "VERIFIED_ADMINISTRATIVE_RECORD",
})
_ID = re.compile(r"^(?:case|src|subject|obs)_[0-9a-f]{24}$")
_SENSITIVE_KEYS = frozenset({
    "rawText", "text", "narrative", "name", "fullName", "birthDate", "dateOfBirth",
    "passportNumber", "alienRegistrationNumber", "registrationNumber", "email",
    "address", "phone", "phoneNumber", "workplaceName", "modelOutput",
    "predictionOutput", "nationality", "gender", "dateOfBirth",
})
_ROOT_FIELDS = {"schemaVersion", "datasetVersion", "jurisdiction", "sources", "cases"}
_SOURCE_FIELDS = {"sourceId", "sourceType", "authority", "publicUrl", "publicationDate", "reviewStatus"}
_CASE_FIELDS = {"caseId", "sourceIds", "subjects"}
_SUBJECT_FIELDS = {"subjectId", "role", "statusOfStay", "violationCode", "violationArticle", "observations"}
_OBSERVATION_FIELDS = {"observationId", "type", "stage", "amountKrw", "decisionDate",
                       "sourceIds", "reviewStatus", "independentFromPrediction", "sourcePage"}
_OFFICIAL_HOSTS = {"law.go.kr", "scourt.go.kr", "moj.go.kr", "simpan.go.kr", "ccourt.go.kr"}


class CaseRegistryError(ValueError):
    """The registry rejected ungrounded, identifying or contradictory data."""


def _object(value: Any, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise CaseRegistryError(f"{where} must be an object")
    if set(value) - keys:
        raise CaseRegistryError(f"unsupported fields in {where}: {sorted(set(value) - keys)}")
    return value


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseRegistryError(f"missing or invalid {where}")
    return value.strip()


def _id(value: Any, prefix: str, where: str) -> str:
    value = _string(value, where)
    if not _ID.fullmatch(value) or not value.startswith(prefix + "_"):
        raise CaseRegistryError(f"{where} must be a de-identified {prefix} token")
    return value


def _date(value: Any, where: str) -> str:
    value = _string(value, where)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("noncanonical")
    except ValueError as exc:
        raise CaseRegistryError(f"invalid {where}") from exc
    return value


def _official_url(value: Any) -> str:
    raw = _string(value, "source.publicUrl")
    parsed = urlsplit(raw)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
        raise CaseRegistryError("source.publicUrl must be an uncredentialed https URL")
    try:
        ip_address(host)
        raise CaseRegistryError("source.publicUrl may not use an IP address")
    except ValueError:
        pass
    if not any(host == base or host.endswith("." + base) for base in _OFFICIAL_HOSTS):
        raise CaseRegistryError("source.publicUrl must be from an approved official source host")
    if any(name in (parsed.query or "").lower() for name in ("oc=", "apikey=", "access_token=", "key=")):
        raise CaseRegistryError("source.publicUrl must not expose API credentials")
    return raw


def _no_identifiers(value: Any, where: str = "registry") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SENSITIVE_KEYS:
                raise CaseRegistryError(f"identifying or unapproved field in {where}: {key}")
            _no_identifiers(child, where + "." + key)
    elif isinstance(value, list):
        for child in value:
            _no_identifiers(child, where)


def _source_ids(values: Any, valid_ids: set[str], where: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise CaseRegistryError(f"{where} must be a nonempty sourceId list")
    result = [_id(v, "src", where) for v in values]
    if len(result) != len(set(result)) or set(result) - valid_ids:
        raise CaseRegistryError(f"duplicate or unknown official source in {where}")
    return result


def validate_case_registry(dataset: Any) -> dict:
    """Strict offline validation only. SOURCE_VERIFIED still requires actual review."""
    _no_identifiers(dataset)
    root = _object(dataset, _ROOT_FIELDS, "registry")
    if root.get("schemaVersion") != REGISTRY_SCHEMA_VERSION or root.get("jurisdiction") != "KR":
        raise CaseRegistryError("unsupported registry version or jurisdiction")
    _string(root.get("datasetVersion"), "datasetVersion")
    sources = root.get("sources")
    cases = root.get("cases")
    if not isinstance(sources, list) or not isinstance(cases, list):
        raise CaseRegistryError("sources and cases must be arrays")
    source_state: dict[str, str] = {}
    for source in sources:
        row = _object(source, _SOURCE_FIELDS, "source")
        sid = _id(row.get("sourceId"), "src", "sourceId")
        if sid in source_state:
            raise CaseRegistryError("duplicate sourceId")
        if row.get("sourceType") not in SOURCE_TYPES:
            raise CaseRegistryError("unrecognized official source type")
        _string(row.get("authority"), "authority")
        _official_url(row.get("publicUrl"))
        _date(row.get("publicationDate"), "publicationDate")
        if row.get("reviewStatus") not in SOURCE_STATES:
            raise CaseRegistryError("source reviewStatus is invalid")
        source_state[sid] = row["reviewStatus"]

    seen_cases: set[str] = set()
    seen_subjects: set[str] = set()
    seen_observations: set[str] = set()
    for case in cases:
        row = _object(case, _CASE_FIELDS, "case")
        cid = _id(row.get("caseId"), "case", "caseId")
        if cid in seen_cases:
            raise CaseRegistryError("duplicate caseId")
        seen_cases.add(cid)
        case_sources = set(_source_ids(row.get("sourceIds"), set(source_state), "case.sourceIds"))
        subjects = row.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            raise CaseRegistryError("case requires at least one subject")
        for subject in subjects:
            person = _object(subject, _SUBJECT_FIELDS, "subject")
            sid = _id(person.get("subjectId"), "subject", "subjectId")
            if sid in seen_subjects:
                raise CaseRegistryError("duplicate subjectId")
            seen_subjects.add(sid)
            if person.get("role") not in SUBJECT_ROLES:
                raise CaseRegistryError("subject role is invalid")
            for key in ("statusOfStay", "violationCode", "violationArticle"):
                if person.get(key) is not None and (not isinstance(person[key], str) or len(person[key]) > 100):
                    raise CaseRegistryError(f"invalid subject.{key}")
            observations = person.get("observations")
            if not isinstance(observations, list):
                raise CaseRegistryError("subject.observations must be an array")
            for observation in observations:
                event = _object(observation, _OBSERVATION_FIELDS, "observation")
                oid = _id(event.get("observationId"), "obs", "observationId")
                if oid in seen_observations:
                    raise CaseRegistryError("duplicate observationId")
                seen_observations.add(oid)
                kind, stage = event.get("type"), event.get("stage")
                if kind not in OBSERVATION_TYPES or stage not in STAGES_BY_TYPE[kind]:
                    raise CaseRegistryError("invalid observation type/stage pairing")
                amount = event.get("amountKrw")
                if kind in MONETARY_OBSERVATIONS:
                    if type(amount) is not int or amount < 0:
                        raise CaseRegistryError("monetary outcome requires a confirmed nonnegative amount")
                elif amount is not None:
                    raise CaseRegistryError("nonmonetary outcome may not inherit another subject's fine")
                _date(event.get("decisionDate"), "observation.decisionDate")
                linked = set(_source_ids(event.get("sourceIds"), case_sources, "observation.sourceIds"))
                if event.get("reviewStatus") not in VERIFICATION_STATES:
                    raise CaseRegistryError("unknown observation review status")
                if event.get("independentFromPrediction") not in (True, False):
                    raise CaseRegistryError("independentFromPrediction must be boolean")
                if event.get("sourcePage") is not None and (
                    type(event["sourcePage"]) is not int or event["sourcePage"] < 1
                ):
                    raise CaseRegistryError("sourcePage must be a positive page number")
                if event["reviewStatus"] == "INDEPENDENTLY_REVIEWED":
                    if not event["independentFromPrediction"] or any(
                        source_state[source_id] != "SOURCE_VERIFIED" for source_id in linked
                    ):
                        raise CaseRegistryError("independent review requires verified source and prediction independence")
    return deepcopy(root)


def reviewed_observations(dataset: Any, *, role: str, observation_type: str) -> list[dict]:
    """Select specific verified target labels without mixing subject roles or outcome stages."""
    if role not in SUBJECT_ROLES or role == "UNKNOWN" or observation_type not in OBSERVATION_TYPES:
        raise CaseRegistryError("explicit known role and target observation type are required")
    registry = validate_case_registry(dataset)
    selected = []
    for case in registry["cases"]:
        for subject in case["subjects"]:
            if subject["role"] != role:
                continue
            for obs in subject["observations"]:
                if obs["type"] == observation_type and obs["reviewStatus"] == "INDEPENDENTLY_REVIEWED":
                    selected.append({
                        "caseId": case["caseId"], "subjectId": subject["subjectId"],
                        "subjectRole": role, "observationType": observation_type,
                        "observedAmountKrw": obs.get("amountKrw"),
                        "decisionDate": obs["decisionDate"], "sourceIds": list(obs["sourceIds"]),
                    })
    return selected
