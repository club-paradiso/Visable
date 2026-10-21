"""Teacher policy and the gate every distilled training record must pass.

Why this exists: what Waymaker may do with a model's output depends on the
*serving channel* as much as on the weights licence. The same Nemotron weights
are OpenMDW-licensed when self-hosted and trial-only when reached through
OpenRouter's ``:free`` route (research-notes/training-distill.md §3). A
distillation pipeline that only checks the model name would therefore launder
trial-tier output into training data. This module keeps four things apart:

* ``configs/teacher_policy.json`` is the recorded reading of each provider's
  terms. It is data, edited by a person after legal review, never by code.
* ``is_permitted(provider, model, channel)`` turns that reading into a decision.
  It denies by default: a teacher that no entry names is not a teacher.
* The policy's ``legal_signoff`` block records whether counsel has approved the
  reading (gate G0 in training-distill.md §4.7). A favourable reading of the
  terms is not permission to run; until sign-off is recorded the gate refuses
  every record.
* ``gate_record(record)`` refuses a ``TeacherRecord`` whose teacher is not
  permitted, whose output carries reasoning text instead of structured labels,
  or whose legal conclusions were not verified by the WLIE claim gate *and* by a
  human reviewer. A teacher's conclusion is a candidate label, never gold.

Standard library only, like the rest of ``waymaker_ai``.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import OverallStatus
from waymaker_ai.dataset.tasks import TASK_EXPECTED_KEYS, TASK_SUITE

POLICY_SCHEMA_VERSION = "waymaker-teacher-policy/0.1"
RECORD_SCHEMA_VERSION = "waymaker-teacher-record/0.1"
POLICY_ACCESS_DATE = "2026-10-19"
DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "configs" / "teacher_policy.json"

#: The task brief caps a recorded clause quote at 25 words.
MAX_QUOTE_WORDS = 25

#: The channel whose weights Waymaker serves itself. It is the only channel on
#: which a weights licence (rather than a provider's service terms) decides.
SELF_HOSTED_CHANNEL = "self_hosted"


class OutputUse(str, Enum):
    """What an entry says about training on the teacher's outputs."""

    PERMITTED = "permitted"
    PERMITTED_WITH_CONDITIONS = "permitted_with_conditions"
    NOT_PERMITTED = "not_permitted"
    REQUIRES_LEGAL_REVIEW = "requires_legal_review"


#: Most restrictive first. When several entries match, the first one in this
#: order decides, so an unreviewed channel can never be outvoted by a licence.
_RESTRICTIVENESS: Tuple[OutputUse, ...] = (
    OutputUse.NOT_PERMITTED,
    OutputUse.REQUIRES_LEGAL_REVIEW,
    OutputUse.PERMITTED_WITH_CONDITIONS,
    OutputUse.PERMITTED,
)

#: Waymaker's own model policy (check 3 of the decision rule). Only "accepted"
#: families may be permitted.
WAYMAKER_POLICY_VALUES = frozenset({"accepted", "chinese_routes_only", "not_in_use"})

SIGNOFF_STATES = frozenset({"pending", "approved", "rejected"})

#: Tasks whose expected output is a legal conclusion (a verification status, a
#: candidate version, a decision to withhold). Classification labels are not.
LEGAL_CONCLUSION_TASKS = frozenset({
    task for task, suite in TASK_SUITE.items() if suite in ("legal_verification", "temporal", "abstention")
})

#: Keys that would carry a teacher's reasoning rather than its labels. A record
#: whose output contains any of them, at any depth, is refused.
REASONING_KEYS = frozenset({
    "analysis",
    "chain_of_thought",
    "cot",
    "explanation",
    "internal_monologue",
    "rationale",
    "reasoning",
    "scratchpad",
    "thinking",
    "thought",
    "thoughts",
})

#: Literal markers that reasoning models emit around hidden reasoning.
REASONING_MARKERS: Tuple[str, ...] = ("<think>", "</think>")

HUMAN_REVIEW_STATES = frozenset({"unreviewed", "machine_checked", "human_verified", "disputed"})

# Keys the policy file may carry. Anything else is a typo or an unreviewed
# addition, and the loader refuses it rather than ignoring it.
_TOP_LEVEL_KEYS = frozenset({
    "schema_version", "accessed", "status", "source_notes", "default_decision",
    "decision_rule", "quote_policy", "channels", "entries", "legal_signoff",
})
_ENTRY_KEYS = frozenset({
    "id", "provider", "channel", "models", "weights_license", "output_use_for_training",
    "waymaker_policy", "conditions", "clause_ref", "evidence", "notes",
})
_CLAUSE_KEYS = frozenset({"url", "accessed", "section", "quote", "paraphrase"})
_CHANNEL_KEYS = frozenset({"description", "terms_url"})
_SIGNOFF_KEYS = frozenset({"status", "reviewer", "date", "scope", "note"})


class PolicyError(ValueError):
    """The policy file is malformed. Carries every problem found, not just the first."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("invalid teacher policy: " + "; ".join(self.problems))


class RecordError(ValueError):
    """A TeacherRecord dict does not match the record schema."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("invalid teacher record: " + "; ".join(self.problems))


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PolicyCondition:
    id: str
    text: str


@dataclass(frozen=True)
class ClauseRef:
    url: str
    accessed: str
    section: str
    quote: Optional[str]
    paraphrase: str


@dataclass(frozen=True)
class PolicyEntry:
    id: str
    provider: str
    channel: str
    models: Tuple[str, ...]
    weights_license: str
    output_use: OutputUse
    waymaker_policy: str
    conditions: Tuple[PolicyCondition, ...]
    clause_ref: ClauseRef
    notes: str = ""

    def matches(self, provider: str, model: str, channel: str) -> bool:
        if _norm(provider) != _norm(self.provider) or channel != self.channel:
            return False
        return any(_model_matches(pattern, model) for pattern in self.models)


@dataclass(frozen=True)
class LegalSignoff:
    status: str                       # one of SIGNOFF_STATES
    reviewer: Optional[str] = None
    date: Optional[str] = None        # YYYY-MM-DD

    @property
    def approved(self) -> bool:
        return self.status == "approved"


@dataclass(frozen=True)
class TeacherDecision:
    """The outcome of ``is_permitted``. ``permitted`` is False unless an entry allows it.

    ``permitted`` describes the recorded terms only. Whether a distillation run
    may start also depends on the policy's legal sign-off, which ``gate_record``
    checks.
    """

    permitted: bool
    verdict: str                      # an OutputUse value, or "no_entry"
    reasons: Tuple[str, ...]
    conditions: Tuple[PolicyCondition, ...] = ()
    entry_ids: Tuple[str, ...] = ()

    def condition_ids(self) -> Tuple[str, ...]:
        return tuple(c.id for c in self.conditions)


@dataclass(frozen=True)
class TeacherPolicy:
    schema_version: str
    accessed: str
    entries: Tuple[PolicyEntry, ...]
    channels: Tuple[str, ...]
    signoff: LegalSignoff = LegalSignoff(status="pending")

    def matching_entries(self, provider: str, model: str, channel: str) -> List[PolicyEntry]:
        return [entry for entry in self.entries if entry.matches(provider, model, channel)]

    def entry(self, entry_id: str) -> Optional[PolicyEntry]:
        for candidate in self.entries:
            if candidate.id == entry_id:
                return candidate
        return None

    def is_permitted(self, provider: str, model: str, channel: str) -> TeacherDecision:
        if not provider or not model or not channel:
            return TeacherDecision(False, "no_entry", ("provider, model and channel are all required",))
        if channel not in self.channels:
            return TeacherDecision(False, "no_entry", (f"unknown channel {channel!r}: default deny",))
        if channel == SELF_HOSTED_CHANNEL and ":" in model:
            # "google/gemma-4-31b-it:free" is an API route, not downloadable
            # weights. Calling it self-hosted would launder the route's terms.
            return TeacherDecision(False, "no_entry", (
                f"{model!r} is an API route id (it has a ':' suffix), not a repo id that can be self-hosted",
            ))
        matches = self.matching_entries(provider, model, channel)
        if not matches:
            return TeacherDecision(
                False,
                "no_entry",
                (f"no policy entry covers ({provider}, {model}, {channel}): default deny",),
            )
        decisive = _most_restrictive(matches)
        entry_ids = tuple(entry.id for entry in matches)
        if decisive.output_use is OutputUse.NOT_PERMITTED:
            return TeacherDecision(False, decisive.output_use.value, (
                f"{decisive.id}: outputs may not be used for training ({decisive.clause_ref.section})",
            ), entry_ids=entry_ids)
        if decisive.output_use is OutputUse.REQUIRES_LEGAL_REVIEW:
            return TeacherDecision(False, decisive.output_use.value, (
                f"{decisive.id}: requires legal review before any use as a teacher",
            ), entry_ids=entry_ids)
        conditions = _union_conditions(matches)
        verdict = OutputUse.PERMITTED_WITH_CONDITIONS if conditions else OutputUse.PERMITTED
        return TeacherDecision(True, verdict.value, (
            f"permitted by {', '.join(entry_ids)}",
        ), conditions=conditions, entry_ids=entry_ids)


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _model_matches(pattern: str, model: str) -> bool:
    """Exact id, or a prefix when the pattern ends with '*'. '*' alone matches any model."""
    if pattern.endswith("*"):
        return model.lower().startswith(pattern[:-1].lower())
    return model.lower() == pattern.lower()


def _most_restrictive(entries: Sequence[PolicyEntry]) -> PolicyEntry:
    return min(entries, key=lambda entry: _RESTRICTIVENESS.index(entry.output_use))


def _union_conditions(entries: Sequence[PolicyEntry]) -> Tuple[PolicyCondition, ...]:
    seen: Dict[str, PolicyCondition] = {}
    for entry in entries:
        for condition in entry.conditions:
            seen.setdefault(condition.id, condition)
    return tuple(seen.values())


def load_policy(path: Optional[Path] = None) -> TeacherPolicy:
    policy_path = Path(path) if path else DEFAULT_POLICY_PATH
    try:
        data = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolicyError([f"{policy_path.name} is not valid JSON: {exc}"]) from exc
    return parse_policy(data)


def parse_policy(data: Any) -> TeacherPolicy:
    """Validate a policy dict and build a TeacherPolicy. Raises PolicyError listing every problem."""
    if not isinstance(data, Mapping):
        raise PolicyError(["policy must be a JSON object"])
    problems: List[str] = _unknown_keys(data, _TOP_LEVEL_KEYS, "policy")
    if data.get("schema_version") != POLICY_SCHEMA_VERSION:
        problems.append(f"schema_version must be {POLICY_SCHEMA_VERSION!r}")
    if data.get("accessed") != POLICY_ACCESS_DATE:
        problems.append(f"accessed must be {POLICY_ACCESS_DATE!r}")
    if data.get("default_decision") != "deny":
        problems.append("default_decision must be 'deny'")

    channels = data.get("channels")
    if not isinstance(channels, Mapping) or not channels:
        problems.append("channels must be a non-empty object")
        channels = {}
    for name, channel in channels.items():
        if not isinstance(channel, Mapping):
            problems.append(f"channels.{name} must be an object")
            continue
        problems.extend(_unknown_keys(channel, _CHANNEL_KEYS, f"channels.{name}"))

    signoff, signoff_problems = _parse_signoff(data.get("legal_signoff"))
    problems.extend(signoff_problems)

    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        problems.append("entries must be a non-empty list")
        raw_entries = []
    entries: List[PolicyEntry] = []
    seen_ids: set = set()
    for index, raw in enumerate(raw_entries):
        entry, entry_problems = _parse_entry(raw, index, set(channels))
        problems.extend(entry_problems)
        if entry is None:
            continue
        if entry.id in seen_ids:
            problems.append(f"entries[{index}]: duplicate id {entry.id!r}")
        seen_ids.add(entry.id)
        entries.append(entry)

    if problems:
        raise PolicyError(problems)
    return TeacherPolicy(
        schema_version=str(data["schema_version"]),
        accessed=str(data["accessed"]),
        entries=tuple(entries),
        channels=tuple(sorted(channels)),
        signoff=signoff,
    )


def _unknown_keys(raw: Mapping[str, Any], allowed: frozenset, where: str) -> List[str]:
    return [f"{where}: unknown key {key!r}" for key in sorted(set(raw) - allowed)]


def _parse_signoff(raw: Any) -> Tuple[LegalSignoff, List[str]]:
    if not isinstance(raw, Mapping):
        return LegalSignoff(status="pending"), ["legal_signoff must be an object"]
    problems = _unknown_keys(raw, _SIGNOFF_KEYS, "legal_signoff")
    status = raw.get("status")
    if status not in SIGNOFF_STATES:
        problems.append(f"legal_signoff.status must be one of {sorted(SIGNOFF_STATES)}")
        status = "pending"
    if status == "approved":
        if not isinstance(raw.get("reviewer"), str) or not raw.get("reviewer"):
            problems.append("an approved legal_signoff must name the reviewer")
        if not _is_iso_date(raw.get("date")):
            problems.append("an approved legal_signoff must carry its date as YYYY-MM-DD")
    return LegalSignoff(status=status, reviewer=raw.get("reviewer"), date=raw.get("date")), problems


_ENTRY_STRING_FIELDS = ("id", "provider", "channel", "weights_license", "waymaker_policy")


def _parse_entry(raw: Any, index: int, channels: set) -> Tuple[Optional[PolicyEntry], List[str]]:
    where = f"entries[{index}]"
    if not isinstance(raw, Mapping):
        return None, [f"{where}: must be an object"]
    problems: List[str] = []
    for name in _ENTRY_STRING_FIELDS:
        if not isinstance(raw.get(name), str) or not raw.get(name):
            problems.append(f"{where}: {name} must be a non-empty string")
    where = f"entries[{index}] ({raw.get('id')})"
    problems.extend(_unknown_keys(raw, _ENTRY_KEYS, where))
    if not isinstance(raw.get("notes"), str):
        problems.append(f"{where}: notes must be a string (empty is allowed)")

    try:
        output_use: Optional[OutputUse] = OutputUse(raw.get("output_use_for_training"))
    except ValueError:
        problems.append(f"{where}: output_use_for_training must be one of {[u.value for u in OutputUse]}")
        output_use = None

    if raw.get("channel") not in channels:
        problems.append(f"{where}: channel {raw.get('channel')!r} is not declared in channels")
    if raw.get("waymaker_policy") not in WAYMAKER_POLICY_VALUES:
        problems.append(f"{where}: waymaker_policy must be one of {sorted(WAYMAKER_POLICY_VALUES)}")

    models = raw.get("models")
    if not isinstance(models, list) or not models or not all(isinstance(m, str) and m for m in models):
        problems.append(f"{where}: models must be a non-empty list of strings")
        models = []

    conditions, condition_problems = _parse_conditions(raw.get("conditions"), where)
    problems.extend(condition_problems)
    clause_ref, clause_problems = _parse_clause_ref(raw.get("clause_ref"), where)
    problems.extend(clause_problems)

    if output_use is OutputUse.PERMITTED_WITH_CONDITIONS and not conditions:
        problems.append(f"{where}: permitted_with_conditions needs at least one condition")
    if output_use is OutputUse.PERMITTED and conditions:
        problems.append(f"{where}: an entry with conditions must say permitted_with_conditions")
    if output_use in (OutputUse.PERMITTED, OutputUse.PERMITTED_WITH_CONDITIONS) and raw.get("waymaker_policy") != "accepted":
        problems.append(f"{where}: only a family Waymaker's policy accepts may be permitted")

    if problems or output_use is None or clause_ref is None:
        return None, problems
    return PolicyEntry(
        id=raw["id"],
        provider=raw["provider"],
        channel=raw["channel"],
        models=tuple(models),
        weights_license=raw["weights_license"],
        output_use=output_use,
        waymaker_policy=raw["waymaker_policy"],
        conditions=conditions,
        clause_ref=clause_ref,
        notes=raw["notes"],
    ), []


def _parse_conditions(raw: Any, where: str) -> Tuple[Tuple[PolicyCondition, ...], List[str]]:
    if not isinstance(raw, list):
        return (), [f"{where}: conditions must be a list"]
    problems: List[str] = []
    conditions: List[PolicyCondition] = []
    for position, item in enumerate(raw):
        if not isinstance(item, Mapping) or not item.get("id") or not item.get("text"):
            problems.append(f"{where}: conditions[{position}] needs a non-empty id and text")
            continue
        conditions.append(PolicyCondition(id=str(item["id"]), text=str(item["text"])))
    return tuple(conditions), problems


def _parse_clause_ref(raw: Any, where: str) -> Tuple[Optional[ClauseRef], List[str]]:
    if not isinstance(raw, Mapping):
        return None, [f"{where}: clause_ref must be an object"]
    problems = _unknown_keys(raw, _CLAUSE_KEYS, f"{where} clause_ref")
    url = raw.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        problems.append(f"{where}: clause_ref.url must be an https URL")
    if raw.get("accessed") != POLICY_ACCESS_DATE:
        problems.append(f"{where}: clause_ref.accessed must be {POLICY_ACCESS_DATE!r}")
    if not isinstance(raw.get("section"), str) or not raw.get("section"):
        problems.append(f"{where}: clause_ref.section must name the clause")
    if "quote" not in raw:
        problems.append(f"{where}: clause_ref.quote must be present (null when the notes recorded no verbatim text)")
    quote = raw.get("quote")
    if quote is not None and (not isinstance(quote, str) or not quote.strip() or len(quote.split()) > MAX_QUOTE_WORDS):
        problems.append(f"{where}: clause_ref.quote must be null or a non-empty string of at most {MAX_QUOTE_WORDS} words")
    paraphrase = raw.get("paraphrase")
    if quote is None and not paraphrase:
        problems.append(f"{where}: clause_ref needs a quote or a paraphrase")
    if problems:
        return None, problems
    return ClauseRef(
        url=url,
        accessed=raw["accessed"],
        section=raw["section"],
        quote=quote,
        paraphrase=str(paraphrase or ""),
    ), []


_DEFAULT_POLICY: Optional[TeacherPolicy] = None


def default_policy() -> TeacherPolicy:
    global _DEFAULT_POLICY
    if _DEFAULT_POLICY is None:
        _DEFAULT_POLICY = load_policy(DEFAULT_POLICY_PATH)
    return _DEFAULT_POLICY


def is_permitted(provider: str, model: str, channel: str, policy: Optional[TeacherPolicy] = None) -> TeacherDecision:
    """Decide whether (provider, model, channel) may serve as a distillation teacher.

    Default deny: an unknown channel, an unlisted model or a missing field is a
    refusal with a reason, never an exception the caller could swallow.
    """
    return (policy or default_policy()).is_permitted(provider, model, channel)


# ---------------------------------------------------------------------------
# Teacher records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TeacherIdentity:
    provider: str
    model: str
    channel: str
    weights_license: str
    revision: Optional[str] = None          # weights SHA; required for self-hosted teachers
    serving_host: Optional[str] = None      # e.g. "self-hosted vLLM on a rented GPU"
    serving_terms_url: Optional[str] = None
    serving_terms_version: Optional[str] = None


@dataclass(frozen=True)
class DeterministicCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class ClaimStatus:
    """One WLIE claim result, as ``ClaimVerification.to_dict()`` summarises it."""

    claim_id: str
    overall: str                       # an OverallStatus value
    highest_verified_layer: int = 0


@dataclass(frozen=True)
class HumanReview:
    status: str                        # one of HUMAN_REVIEW_STATES
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None  # YYYY-MM-DD


@dataclass(frozen=True)
class TeacherRecord:
    """One teacher answer kept as a *candidate* label, with its provenance.

    ``output`` holds structured labels only (the task's expected keys). It never
    holds reasoning: no teacher is ever asked for private chain-of-thought, and a
    record that says it was (``reasoning_requested``) is refused.
    """

    record_id: str
    example_id: str
    task: str
    teacher: TeacherIdentity
    request_date: str
    prompt_sha256: str
    output: Mapping[str, Any]
    reasoning_requested: bool
    has_legal_conclusions: bool
    critical: bool
    deterministic_checks: Tuple[DeterministicCheck, ...]
    wlie_claims: Tuple[ClaimStatus, ...]
    human_review: HumanReview
    permitted: bool                    # as recorded at generation time; the gate recomputes it
    acknowledged_condition_ids: Tuple[str, ...] = ()
    evidence_pack_sha256: Optional[str] = None
    schema_version: str = RECORD_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "example_id": self.example_id,
            "task": self.task,
            "teacher": dict(self.teacher.__dict__),
            "request_date": self.request_date,
            "prompt_sha256": self.prompt_sha256,
            "evidence_pack_sha256": self.evidence_pack_sha256,
            "output": dict(self.output),
            "reasoning_requested": self.reasoning_requested,
            "has_legal_conclusions": self.has_legal_conclusions,
            "critical": self.critical,
            "verification": {
                "deterministic_checks": [dict(c.__dict__) for c in self.deterministic_checks],
                "wlie_claims": [dict(c.__dict__) for c in self.wlie_claims],
                "human_review": dict(self.human_review.__dict__),
            },
            "permitted": self.permitted,
            "acknowledged_condition_ids": list(self.acknowledged_condition_ids),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "TeacherRecord":
        return _record_from_dict(data)


def hash_prompt(messages: Sequence[Mapping[str, Any]]) -> str:
    """Stable sha256 of a chat prompt (canonical JSON), for the record's prompt_sha256."""
    canonical = json.dumps(list(messages), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_lower_hex(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)


def _is_sha256(value: Any) -> bool:
    return _is_lower_hex(value, 64)


def is_pinned_revision(value: Any) -> bool:
    """A Hugging Face commit SHA: 40 lowercase hex characters."""
    return _is_lower_hex(value, 40)


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _record_from_dict(data: Any) -> TeacherRecord:
    if not isinstance(data, Mapping):
        raise RecordError(["record must be an object"])
    problems: List[str] = []
    if data.get("schema_version", RECORD_SCHEMA_VERSION) != RECORD_SCHEMA_VERSION:
        problems.append(f"schema_version must be {RECORD_SCHEMA_VERSION!r}")
    for name in ("record_id", "example_id", "task", "request_date", "prompt_sha256"):
        if not isinstance(data.get(name), str) or not data.get(name):
            problems.append(f"{name} must be a non-empty string")
    if data.get("task") not in TASK_EXPECTED_KEYS:
        problems.append(f"task {data.get('task')!r} is not a benchmark task")
    if not _is_iso_date(data.get("request_date")):
        problems.append("request_date must be YYYY-MM-DD")
    if not _is_sha256(data.get("prompt_sha256")):
        problems.append("prompt_sha256 must be 64 lowercase hex characters")
    evidence_hash = data.get("evidence_pack_sha256")
    if evidence_hash is not None and not _is_sha256(evidence_hash):
        problems.append("evidence_pack_sha256 must be null or 64 lowercase hex characters")
    if not isinstance(data.get("output"), Mapping):
        problems.append("output must be an object of structured labels")
    for name in ("reasoning_requested", "has_legal_conclusions", "critical", "permitted"):
        if not isinstance(data.get(name), bool):
            problems.append(f"{name} must be true or false")

    teacher_raw = data.get("teacher")
    if not isinstance(teacher_raw, Mapping):
        problems.append("teacher must be an object")
        teacher_raw = {}
    for name in ("provider", "model", "channel", "weights_license"):
        if not isinstance(teacher_raw.get(name), str) or not teacher_raw.get(name):
            problems.append(f"teacher.{name} must be a non-empty string")

    verification = data.get("verification")
    if not isinstance(verification, Mapping):
        problems.append("verification must be an object")
        verification = {}
    checks = verification.get("deterministic_checks", [])
    claims = verification.get("wlie_claims", [])
    review = verification.get("human_review")
    if not isinstance(checks, list) or not all(
        isinstance(c, Mapping) and c.get("name") and isinstance(c.get("passed"), bool) for c in checks
    ):
        problems.append("verification.deterministic_checks must be a list of {name, passed}")
        checks = []
    if not isinstance(claims, list) or not all(
        isinstance(c, Mapping) and c.get("claim_id") and "overall" in c for c in claims
    ):
        problems.append("verification.wlie_claims must be a list of {claim_id, overall}")
        claims = []
    valid_overall = {status.value for status in OverallStatus}
    for claim in claims:
        if claim.get("overall") not in valid_overall:
            problems.append(f"wlie claim {claim.get('claim_id')!r}: overall must be an OverallStatus value")
        layer = claim.get("highest_verified_layer", 0)
        if not isinstance(layer, int) or isinstance(layer, bool) or not 0 <= layer <= 7:
            problems.append(f"wlie claim {claim.get('claim_id')!r}: highest_verified_layer must be an integer 0-7")
    if not isinstance(review, Mapping) or review.get("status") not in HUMAN_REVIEW_STATES:
        problems.append(f"verification.human_review.status must be one of {sorted(HUMAN_REVIEW_STATES)}")
        review = {"status": "unreviewed"}
    acknowledged = data.get("acknowledged_condition_ids", [])
    if not isinstance(acknowledged, list) or not all(isinstance(a, str) for a in acknowledged):
        problems.append("acknowledged_condition_ids must be a list of strings")
        acknowledged = []

    if problems:
        raise RecordError(problems)
    return TeacherRecord(
        record_id=data["record_id"],
        example_id=data["example_id"],
        task=data["task"],
        teacher=TeacherIdentity(
            provider=teacher_raw["provider"],
            model=teacher_raw["model"],
            channel=teacher_raw["channel"],
            weights_license=teacher_raw["weights_license"],
            revision=teacher_raw.get("revision"),
            serving_host=teacher_raw.get("serving_host"),
            serving_terms_url=teacher_raw.get("serving_terms_url"),
            serving_terms_version=teacher_raw.get("serving_terms_version"),
        ),
        request_date=data["request_date"],
        prompt_sha256=data["prompt_sha256"],
        evidence_pack_sha256=evidence_hash,
        output=dict(data["output"]),
        reasoning_requested=data["reasoning_requested"],
        has_legal_conclusions=data["has_legal_conclusions"],
        critical=data["critical"],
        deterministic_checks=tuple(
            DeterministicCheck(name=str(c["name"]), passed=c["passed"], detail=str(c.get("detail", ""))) for c in checks
        ),
        wlie_claims=tuple(
            ClaimStatus(
                claim_id=str(c["claim_id"]),
                overall=str(c["overall"]),
                highest_verified_layer=c.get("highest_verified_layer", 0),
            )
            for c in claims
        ),
        human_review=HumanReview(
            status=review["status"],
            reviewer=review.get("reviewer"),
            reviewed_at=review.get("reviewed_at"),
        ),
        permitted=data["permitted"],
        acknowledged_condition_ids=tuple(acknowledged),
    )


def load_teacher_records(path: Path) -> List[TeacherRecord]:
    """Read a JSONL ledger of TeacherRecords. A malformed line is an error, not a skip."""
    records: List[TeacherRecord] = []
    problems: List[str] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(TeacherRecord.from_dict(json.loads(line)))
        except (json.JSONDecodeError, RecordError) as exc:
            problems.append(f"line {number}: {exc}")
    if problems:
        raise RecordError(problems)
    return records


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GateResult:
    accepted: bool
    reasons: Tuple[str, ...] = ()
    conditions: Tuple[PolicyCondition, ...] = field(default_factory=tuple)


def find_reasoning(value: Any, path: str = "output") -> List[str]:
    """Paths inside ``value`` that look like reasoning rather than labels."""
    found: List[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key).strip().lower() in REASONING_KEYS:
                found.append(child)
            found.extend(find_reasoning(item, child))
    elif isinstance(value, (list, tuple)):
        for position, item in enumerate(value):
            found.extend(find_reasoning(item, f"{path}[{position}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in REASONING_MARKERS):
            found.append(path)
    return found


def _label_problems(record: TeacherRecord) -> List[str]:
    required, optional = TASK_EXPECTED_KEYS[record.task]
    keys = set(record.output)
    problems: List[str] = []
    missing = sorted(required - keys)
    extra = sorted(keys - required - optional)
    if missing:
        problems.append(f"output lacks required {record.task} keys {missing}")
    if extra:
        problems.append(f"output has keys outside the {record.task} label schema {extra}")
    return problems


def _verification_problems(record: TeacherRecord) -> List[str]:
    problems: List[str] = []
    if not record.deterministic_checks:
        problems.append("no deterministic checks were recorded")
    failed = [check.name for check in record.deterministic_checks if not check.passed]
    if failed:
        problems.append(f"deterministic checks failed: {failed}")

    needs_legal_verification = record.has_legal_conclusions or record.task in LEGAL_CONCLUSION_TASKS
    if record.task in LEGAL_CONCLUSION_TASKS and not record.has_legal_conclusions:
        problems.append(f"task {record.task} carries legal conclusions; has_legal_conclusions cannot be false")
    if needs_legal_verification:
        if record.evidence_pack_sha256 is None:
            problems.append("a legal conclusion needs the hash of the evidence pack it was drawn from")
        if not record.wlie_claims:
            problems.append("legal conclusions were not run through the WLIE claim gate")
        unverified = [c.claim_id for c in record.wlie_claims if c.overall != OverallStatus.VERIFIED.value]
        if unverified:
            problems.append(f"WLIE did not verify claims {unverified}")

    review = record.human_review
    if needs_legal_verification or record.critical:
        if review.status != "human_verified":
            problems.append(f"human review is {review.status!r}; legal or critical labels need 'human_verified'")
        elif not review.reviewer or not _is_iso_date(review.reviewed_at):
            problems.append("human review must name the reviewer and the review date")
    elif review.status not in ("machine_checked", "human_verified"):
        problems.append(f"human review is {review.status!r}; at least 'machine_checked' is required")
    return problems


def gate_record(record: TeacherRecord, policy: Optional[TeacherPolicy] = None) -> GateResult:
    """Accept a teacher record as a training target only if every check passes.

    The stored ``permitted`` flag is never trusted on its own: the decision is
    recomputed from the current policy, so a channel that was later found to be
    trial-only invalidates records generated through it. Every reason is
    collected, so one pass over a ledger shows everything that must be fixed.
    """
    active = policy or default_policy()
    reasons: List[str] = []
    if not active.signoff.approved:
        reasons.append(
            f"teacher policy legal_signoff is {active.signoff.status!r}: no record is accepted before counsel "
            "approves the policy (gate G0, training-distill.md §4.7)"
        )
    teacher = record.teacher
    decision = active.is_permitted(teacher.provider, teacher.model, teacher.channel)
    if not decision.permitted:
        reasons.extend(decision.reasons)
    if not record.permitted:
        reasons.append("the record itself says its teacher was not permitted at generation time")
    missing_conditions = [cid for cid in decision.condition_ids() if cid not in record.acknowledged_condition_ids]
    if decision.permitted and missing_conditions:
        reasons.append(f"policy conditions not acknowledged: {missing_conditions}")
    if teacher.channel == SELF_HOSTED_CHANNEL and not is_pinned_revision(teacher.revision):
        reasons.append("a self-hosted teacher must record its 40-character weights revision SHA")

    if record.reasoning_requested:
        reasons.append("the teacher was asked for reasoning; only final structured labels are allowed")
    reasoning_paths = find_reasoning(record.output)
    if reasoning_paths:
        reasons.append(f"output carries reasoning text at {reasoning_paths}")
    reasons.extend(_label_problems(record))
    reasons.extend(_verification_problems(record))

    return GateResult(accepted=not reasons, reasons=tuple(reasons), conditions=decision.conditions)


def gate_records(records: Iterable[TeacherRecord], policy: Optional[TeacherPolicy] = None) -> Dict[str, GateResult]:
    return {record.record_id: gate_record(record, policy) for record in records}
