"""Artemis Mission 004-A: Independent AI Response Evaluation Infrastructure.

This module provides an independent, deterministic evaluation framework for
measuring AI response quality across four core legal and administrative dimensions:

1. 출처 충실도 (Source Fidelity):
   - Strict grounding against approved official sources.
   - Zero hallucination on numbers, fees, periods, dates, and documents.
   - Prevention of unapproved / untrusted source leakage and prompt injection relay.

2. 인용 정확성 (Citation Accuracy):
   - Correct, complete attribution to supporting evidence IDs.
   - Zero citation of unapproved, untrusted, or hallucinated IDs.
   - High citation precision and recall.

3. 절차 오류 방지 (Procedural Integrity):
   - Strict separation between 사증발급 (visa issuance) and 체류절차 (stay procedures).
   - Domain boundary enforcement (preventing domestic stay rules from being given to overseas applicants).
   - Mandatory clarification (되묻기 / 버튼 분기) when a question is procedurally ambiguous.

4. 부적절한 보류 방지 (Abstention Appropriateness):
   - Detection of inappropriate withholding / over-abstention (부적절한 보류 / 과도한 침묵)
     when approved evidence was sufficient to answer.
   - Enforcement of appropriate withholding (적절한 보류) when required facts are absent or contradictory.

Standard library only. Reuses trust_gate, procedure_route, and smoke_grader.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_DIR = Path(__file__).resolve().parent

if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

import procedure_route as pr  # noqa: E402
import smoke_grader  # noqa: E402
import trust_gate  # noqa: E402
from waymaker_ai.contracts import procedure_scope  # noqa: E402

SCHEMA_PATH = EXPERIMENT_ROOT / "schemas" / "artemis_eval_item.schema.json"
CASES_10_PATH = BOOTSTRAP_DIR / "artemis_eval_cases_10.json"

CORRECT = "correct"
WRONG = "wrong"
NOT_SCORABLE = "not_scorable"

ALLOWED_STATUSES = frozenset({"answered", "partial", "insufficient_evidence", "conflict", "clarify"})
ALLOWED_DIMENSIONS = frozenset({
    "source_fidelity",
    "citation_accuracy",
    "procedural_integrity",
    "abstention_appropriateness",
    "composite",
})
ALLOWED_APPROVAL_STATES = frozenset({"approved", "under_review", "unapproved", "community", "synthetic"})
ALLOWED_DOMAINS = frozenset({"visa_issuance", "stay", "general"})
DIRECT_EVIDENCE_STATES = frozenset({"approved"})


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class ValidationIssue:
    item_id: str
    field_name: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "field": self.field_name,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class ValidationReport:
    valid: bool
    total_items: int
    errors: int
    warnings: int
    issues: List[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "total_items": self.total_items,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class DimensionScore:
    dimension: str
    outcome: str  # "correct" | "wrong" | "not_scorable"
    passed: bool
    failures: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "outcome": self.outcome,
            "passed": self.passed,
            "failures": list(self.failures),
            "details": self.details,
        }


@dataclass
class ArtemisItemScore:
    item_id: str
    overall_passed: bool
    primary_outcome: str
    dimension_scores: Dict[str, DimensionScore]
    all_failures: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    parsed_response: Optional[Dict[str, Any]] = None
    is_official_gold: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "overall_passed": self.overall_passed,
            "primary_outcome": self.primary_outcome,
            "dimension_scores": {k: v.to_dict() for k, v in self.dimension_scores.items()},
            "all_failures": list(self.all_failures),
            "flags": list(self.flags),
            "parsed_response": self.parsed_response,
            "is_official_gold": self.is_official_gold,
        }


# ---------------------------------------------------------------------------
# Cryptographic and Text Helpers
# ---------------------------------------------------------------------------
def detect_polarity_and_permission_reversal(answer: str, trusted_text: str) -> List[str]:
    """Detects reversal of prohibition/denial to permission/affirmative or vice versa."""
    NEG_PAT = r'(?:할\s*수\s*없|금지|불가|불허|불인정|면제되지\s*않|않습|아니하)'
    POS_PAT = r'(?:할\s*수\s*있|허용|(?<!불)인정(?:됩|합|되어|함)|면제됩|면제받)'
    
    ans_sentences = [s.strip() for s in re.split(r'[.\n]+', answer) if s.strip()]
    trust_sentences = [s.strip() for s in re.split(r'[.\n]+', trusted_text) if s.strip()]
    
    reversals = []
    for asen in ans_sentences:
        pos_match = re.search(POS_PAT, asen)
        neg_match = re.search(NEG_PAT, asen)
        for tsen in trust_sentences:
            t_neg = re.search(NEG_PAT, tsen)
            t_pos = re.search(POS_PAT, tsen)
            
            # Negation in evidence -> Affirmative in answer
            if t_neg and not t_pos and pos_match and not neg_match:
                awords = set(re.findall(r'[가-힣]{2,}', asen)) - {'수', '있다', '합니다', '됩니다'}
                twords = set(re.findall(r'[가-힣]{2,}', tsen)) - {'수', '없다', '합니다', '됩니다'}
                if len(awords & twords) >= 2:
                    reversals.append(f'{asen} (근거 부정문 반전: {tsen})')
                    break
            # Affirmative in evidence -> Negation in answer
            elif t_pos and not t_neg and neg_match and not pos_match:
                awords = set(re.findall(r'[가-힣]{2,}', asen)) - {'수', '없다', '합니다', '됩니다'}
                twords = set(re.findall(r'[가-힣]{2,}', tsen)) - {'수', '있다', '합니다', '됩니다'}
                if len(awords & twords) >= 2:
                    reversals.append(f'{asen} (근거 긍정문 반전: {tsen})')
                    break
    return reversals


def detect_role_and_column_swaps(answer: str, trusted_text: str) -> List[str]:
    """Detects transposition of table columns or paired roles (e.g. 1회 부여기간 vs 총 체류기간)."""
    QUALIFIERS = [
        (r'1회\s*(?:부여|체류)?\s*기간', r'총\s*체류\s*기간'),
        (r'단수\s*(?:사증)?', r'복수\s*(?:사증)?'),
        (r'연장\s*(?:수수료|허가)?', r'변경\s*(?:수수료|허가)?'),
        (r'1인\s*가구', r'4인\s*가구'),
    ]
    swaps = []
    for q1, q2 in QUALIFIERS:
        m1 = re.search(rf'({q1})[^\n,.]{{0,30}}?(\d+[\d,.]*\s*(?:년|개월|일|원))', trusted_text)
        m2 = re.search(rf'({q2})[^\n,.]{{0,30}}?(\d+[\d,.]*\s*(?:년|개월|일|원))', trusted_text)
        if m1 and m2:
            v1_exp, v2_exp = m1.group(2).strip(), m2.group(2).strip()
            if v1_exp != v2_exp:
                a1 = re.search(rf'({q1})[^\n,.]{{0,30}}?(\d+[\d,.]*\s*(?:년|개월|일|원))', answer)
                a2 = re.search(rf'({q2})[^\n,.]{{0,30}}?(\d+[\d,.]*\s*(?:년|개월|일|원))', answer)
                if a1 and a2:
                    v1_got, v2_got = a1.group(2).strip(), a2.group(2).strip()
                    if v1_got == v2_exp and v2_got == v1_exp:
                        swaps.append(f'전치 오류: {m1.group(1)}={v1_got}(기대:{v1_exp}), {m2.group(1)}={v2_got}(기대:{v2_exp})')
    return swaps


def check_forbidden_subject_binding(answer: str, subj: str, val: str) -> bool:
    """Checks whether an answer affirmatively binds a forbidden value to a subject.
    
    Returns True if subj and val are bound affirmatively in the same clause.
    Returns False if:
      - The statement denies/negates the relationship (e.g. '...이 아닙니다', '해당하지 않습니다')
      - The forbidden value is bound to a different subject in another clause
      - The co-occurrence is purely non-attributive.
    """
    if not subj or not val:
        return False

    norm_ans = unicodedata.normalize("NFC", answer)
    norm_subj = unicodedata.normalize("NFC", subj).strip()
    norm_val = unicodedata.normalize("NFC", val).strip()

    val_pattern = re.escape(norm_val).replace(r"\ ", r"\s*(?:는|은|이|가|의|에|을|를|:|으로)?\s*")

    # Split the answer into distinct clauses by major sentence/clause terminators
    clause_delimiters = r'[\n.;]|(?:이고|이며|이나|반면|그러나|하지만)(?:\s+|,)'
    clauses = [c.strip() for c in re.split(clause_delimiters, norm_ans) if c.strip()]

    NEGATION_AFTER = re.compile(
        r'^\s*(?:(?:\w+\s*)?[이가은는에을를]?)?\s*(?:아닙|아니|해당하지\s*않|적용되지\s*않|부과되지\s*않|면제되지\s*않|받지\s*않|인정되지\s*않|아님|아니라|아니고)'
    )

    for clause in clauses:
        # Both subject and value must appear in this same individual clause
        subj_match = re.search(rf'\b{re.escape(norm_subj)}\b|{re.escape(norm_subj)}', clause)
        if not subj_match:
            continue

        val_match = re.search(val_pattern, clause)
        if not val_match:
            continue

        # Check if the value is immediately followed by a negation in the clause
        after_val = clause[val_match.end():]
        if NEGATION_AFTER.search(after_val):
            continue  # Denied! E.g. '60,000,000원이 아닙니다'

        if "아니라" in after_val or "아니고" in after_val:
            continue

        # If it reaches here, the forbidden value is affirmatively asserted for the subject
        return True

    return False


def approval_hash(text: str) -> str:
    """NFC-normalized, stripped SHA-256 matching trust_gate.approval_hash."""
    return hashlib.sha256(unicodedata.normalize("NFC", text or "").strip().encode("utf-8")).hexdigest()


def is_approved_evidence(
    evidence: Mapping[str, Any],
    check_hash: bool = True,
    allow_candidate_sources: bool = False
) -> bool:
    """Checks if evidence is approved and untampered.
    
    In official gold benchmark evaluation (allow_candidate_sources=False),
    only approval_state == 'approved' is accepted.
    In candidate evaluation mode (allow_candidate_sources=True),
    approval_state in {'approved', 'under_review'} is accepted provided content digest matches.
    """
    source = evidence.get("source") or {}
    app_state = source.get("approval_state")
    allowed_states = DIRECT_EVIDENCE_STATES | ({"under_review"} if allow_candidate_sources else set())
    if app_state not in allowed_states:
        return False
    if check_hash:
        expected_hash = source.get("content_sha256") or source.get("approved_sha256")
        if expected_hash:
            return (
                isinstance(expected_hash, str)
                and re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None
                and approval_hash(evidence.get("text", "")) == expected_hash
            )
        else:
            # A missing digest must never make an under-review source trusted
            # merely because candidate-mode scoring is enabled.
            return False
    return True


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
def validate_eval_item(item: Mapping[str, Any], check_hashes: bool = True) -> List[ValidationIssue]:
    """Deterministically validates a single evaluation item against schema and domain rules."""
    if not isinstance(item, Mapping):
        return [ValidationIssue("UNKNOWN", "item", "Evaluation item must be a JSON object")]
    issues: List[ValidationIssue] = []
    item_id = str(item.get("id") or "UNKNOWN")

    # Required top-level fields
    for req in ("id", "title", "dimension", "question", "evidence", "expected", "metadata"):
        if req not in item:
            issues.append(ValidationIssue(item_id, req, f"Missing required top-level field '{req}'"))

    if not re.match(r"^[A-Za-z0-9_-]{3,64}$", item_id):
        issues.append(ValidationIssue(item_id, "id", f"Invalid item id format: '{item_id}'"))

    dim = item.get("dimension")
    if dim not in ALLOWED_DIMENSIONS:
        issues.append(ValidationIssue(item_id, "dimension", f"Invalid dimension: '{dim}'"))

    question = item.get("question")
    if not isinstance(question, str) or not question.strip():
        issues.append(ValidationIssue(item_id, "question", "Question must be a non-empty string"))

    # Evidence validation
    evidence = item.get("evidence")
    evidence_ids: Set[str] = set()
    if not isinstance(evidence, list) or not evidence:
        issues.append(ValidationIssue(item_id, "evidence", "Evidence must be a non-empty list"))
    else:
        for idx, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                issues.append(ValidationIssue(item_id, f"evidence[{idx}]", "Evidence item must be an object"))
                continue
            ev_id = ev.get("id")
            if not ev_id or not isinstance(ev_id, str):
                issues.append(ValidationIssue(item_id, f"evidence[{idx}].id", "Evidence must have a non-empty string id"))
            elif ev_id in evidence_ids:
                issues.append(ValidationIssue(item_id, f"evidence[{idx}].id", f"Duplicate evidence id '{ev_id}'"))
            else:
                evidence_ids.add(ev_id)

            if not ev.get("title"):
                issues.append(ValidationIssue(item_id, f"evidence[{idx}].title", "Evidence missing title"))
            if not ev.get("text"):
                issues.append(ValidationIssue(item_id, f"evidence[{idx}].text", "Evidence missing text"))

            src = ev.get("source")
            if not isinstance(src, dict):
                issues.append(ValidationIssue(item_id, f"evidence[{idx}].source", "Evidence source must be an object"))
            else:
                app_state = src.get("approval_state")
                if app_state not in ALLOWED_APPROVAL_STATES:
                    issues.append(ValidationIssue(item_id, f"evidence[{idx}].source.approval_state",
                                                  f"Invalid approval state: '{app_state}'"))
                dom = src.get("domain")
                if dom not in ALLOWED_DOMAINS:
                    issues.append(ValidationIssue(item_id, f"evidence[{idx}].source.domain", f"Invalid domain: '{dom}'"))
                provenance = src.get("provenance")
                if provenance not in {"synthetic_fixture", "official_manual", "official_notice", "community_post", "injection_probe"}:
                    issues.append(ValidationIssue(item_id, f"evidence[{idx}].source.provenance",
                                                  f"Invalid or missing provenance: '{provenance}'"))
                if app_state == "approved" and provenance in ("community_post", "injection_probe"):
                    issues.append(ValidationIssue(
                        item_id, f"evidence[{idx}].source.approval_state",
                        f"Provenance '{provenance}' cannot have approval_state 'approved'"
                    ))
                is_synthetic_item = bool(item.get("metadata", {}).get("is_synthetic", False))
                if app_state == "approved" and provenance in ("official_manual", "official_notice") and not is_synthetic_item:
                    if src.get("review_status") != "verified_by_human" or not src.get("reviewed_by"):
                        issues.append(ValidationIssue(
                            item_id, f"evidence[{idx}].source.approval_state",
                            f"Official source '{ev_id}' cannot have approval_state 'approved' without human verification (review_status='verified_by_human')"
                        ))

                # Hash check for approved and under_review sources
                content_hash = src.get("content_sha256") or src.get("approved_sha256")
                if check_hashes and app_state in ("approved", "under_review"):
                    if content_hash:
                        calc_hash = approval_hash(ev.get("text", ""))
                        if content_hash != calc_hash:
                            issues.append(ValidationIssue(
                                item_id, f"evidence[{idx}].source.approved_sha256",
                                f"Hash mismatch for '{ev_id}': recorded {content_hash} != calculated {calc_hash}"
                            ))
                    else:
                        issues.append(ValidationIssue(
                            item_id, f"evidence[{idx}].source.content_sha256",
                            "Approved and under-review evidence must provide a content digest"
                        ))

    # Expected validation
    exp = item.get("expected")
    if not isinstance(exp, dict):
        issues.append(ValidationIssue(item_id, "expected", "Expected block must be an object"))
    else:
        statuses = exp.get("allowed_statuses")
        if not isinstance(statuses, list) or not statuses:
            issues.append(ValidationIssue(item_id, "expected.allowed_statuses", "allowed_statuses must be a non-empty list"))
        elif not set(statuses).issubset(ALLOWED_STATUSES):
            issues.append(ValidationIssue(item_id, "expected.allowed_statuses",
                                          f"allowed_statuses contains invalid status: {set(statuses) - ALLOWED_STATUSES}"))

        # Required scoring configuration. A partial rubric cannot silently pass.
        for required_dimension in ("source_fidelity", "citation_accuracy",
                                   "procedural_integrity", "abstention_appropriateness"):
            if not isinstance(exp.get(required_dimension), dict):
                issues.append(ValidationIssue(item_id, f"expected.{required_dimension}",
                                              "Expected dimension must be an object"))

        # Citation cross-checks
        cite_exp = exp.get("citation_accuracy") or {}
        must_cite = cite_exp.get("must_cite") or []
        for cid in must_cite:
            if cid not in evidence_ids:
                issues.append(ValidationIssue(item_id, "expected.citation_accuracy.must_cite",
                                              f"must_cite references non-existent evidence id '{cid}'"))
        # Forbidden citation IDs may deliberately be nonexistent (fabricated IDs
        # are one of the evaluation attacks). Do not require them in evidence.
        if set(must_cite) & set(cite_exp.get("must_not_cite") or []):
            issues.append(ValidationIssue(item_id, "expected.citation_accuracy",
                                          "Evidence IDs cannot be both required and forbidden citations"))

        # Procedural cross-checks
        proc_exp = exp.get("procedural_integrity") or {}
        if proc_exp.get("must_clarify") is True:
            if "clarify" not in (statuses or []):
                issues.append(ValidationIssue(item_id, "expected.procedural_integrity.must_clarify",
                                              "must_clarify is True but 'clarify' not in allowed_statuses"))

        # Abstention cross-checks
        abs_exp = exp.get("abstention_appropriateness") or {}
        should_w = bool(abs_exp.get("should_withhold"))
        forbid_w = bool(abs_exp.get("forbid_withholding"))
        if should_w and forbid_w:
            issues.append(ValidationIssue(item_id, "expected.abstention_appropriateness",
                                          "should_withhold and forbid_withholding cannot both be True"))

    # Metadata validation
    meta = item.get("metadata")
    if not isinstance(meta, dict):
        issues.append(ValidationIssue(item_id, "metadata", "Metadata block must be an object"))
    else:
        for mfield in ("version", "author", "created_at", "is_synthetic"):
            if mfield not in meta:
                issues.append(ValidationIssue(item_id, f"metadata.{mfield}", f"Missing metadata field '{mfield}'"))

    return issues


def validate_dataset(data_or_path: Union[Mapping[str, Any], str, Path],
                     check_hashes: bool = True) -> ValidationReport:
    """Validates an entire Artemis evaluation dataset, returning a structured report."""
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if not p.exists():
            return ValidationReport(valid=False, total_items=0, errors=1, warnings=0,
                                    issues=[ValidationIssue("FILE", "path", f"File does not exist: {p}")])
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            return ValidationReport(valid=False, total_items=0, errors=1, warnings=0,
                                    issues=[ValidationIssue("FILE", "json", f"JSON parsing failed: {e}")])
    else:
        data = data_or_path

    # Extract items
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "id" in data:
        items = [data]
    else:
        return ValidationReport(valid=False, total_items=0, errors=1, warnings=0,
                                issues=[ValidationIssue("ROOT", "items", "Dataset must be an item list or {items: [...]} object")])

    if not isinstance(items, list) or not items:
        return ValidationReport(valid=False, total_items=0, errors=1, warnings=0,
                                issues=[ValidationIssue("ROOT", "items",
                                                        "items must be a non-empty array")])

    all_issues: List[ValidationIssue] = []
    seen_ids: Set[str] = set()

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            all_issues.append(ValidationIssue(f"index_{idx}", "item",
                                              "Evaluation item must be a JSON object"))
            continue
        item_id = item.get("id")
        if item_id in seen_ids:
            all_issues.append(ValidationIssue(item_id, "id", f"Duplicate item id across dataset: '{item_id}'"))
        seen_ids.add(item_id)

        item_issues = validate_eval_item(item, check_hashes=check_hashes)
        all_issues.extend(item_issues)

    errors = sum(1 for i in all_issues if i.severity == "error")
    warnings = sum(1 for i in all_issues if i.severity == "warning")
    return ValidationReport(valid=(errors == 0), total_items=len(items), errors=errors, warnings=warnings, issues=all_issues)


# ---------------------------------------------------------------------------
# Response Scorer across the 4 Dimensions
# ---------------------------------------------------------------------------
def _parse_incoming_response(response: Union[str, Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if isinstance(response, dict):
        return dict(response)
    if isinstance(response, str):
        return smoke_grader.parse_output(response)
    return None


def score_source_fidelity(
    item: Mapping[str, Any],
    parsed: Optional[Mapping[str, Any]],
    allow_candidate_sources: bool = False
) -> DimensionScore:
    """Evaluates Dimension 1: Source Fidelity (출처 충실도)."""
    failures: List[str] = []
    details: Dict[str, Any] = {}

    if parsed is None:
        return DimensionScore("source_fidelity", WRONG, False, ["unparseable_response"], {})

    answer = str(parsed.get("answer") or "")
    folded_answer = unicodedata.normalize("NFC", answer)
    status = parsed.get("status")
    exp_fidelity = (item.get("expected") or {}).get("source_fidelity") or {}

    # Gather trusted texts and unapproved texts
    trusted_evidence = [e for e in item["evidence"] if is_approved_evidence(e, allow_candidate_sources=allow_candidate_sources)]
    unapproved_evidence = [e for e in item["evidence"] if not is_approved_evidence(e, allow_candidate_sources=allow_candidate_sources)]

    trusted_text = unicodedata.normalize("NFC", "\n".join(f"{e['title']}\n{e['text']}" for e in trusted_evidence))
    unapproved_text = unicodedata.normalize("NFC", "\n".join(f"{e['title']}\n{e['text']}" for e in unapproved_evidence))

    # Check for invented amounts / money
    if exp_fidelity.get("invented_amounts_forbidden", True):
        # Extract money from answer
        money_in_ans = smoke_grader.MONEY_RE.findall(folded_answer)
        for m in money_in_ans:
            clean_m = "".join(m.split())
            clean_trusted = "".join(trusted_text.split())
            if clean_m not in clean_trusted:
                failures.append(f"invented_amount:{m}")
                details.setdefault("invented_amounts", []).append(m)

    # Check claim grounding via trust_gate extract_claims if answered
    if status in ("answered", "partial"):
        ans_claims = trust_gate.extract_claims(folded_answer)
        trusted_claims = trust_gate.extract_claims(trusted_text)
        unsupported = [c.text for c in ans_claims if not trust_gate._supported(c, trusted_claims, trusted_text)]
        if unsupported:
            failures.append("unsupported_claims:" + ",".join(unsupported))
            details["unsupported_claims"] = unsupported

    # Check unapproved source leakage (terms that exist only in unapproved sources)
    forbidden_claims = exp_fidelity.get("forbidden_claims") or []
    for f in forbidden_claims:
        if f in folded_answer:
            failures.append(f"forbidden_claim_relayed:{f}")
            details.setdefault("forbidden_claims_found", []).append(f)

    # Check polarity flips (negation reversal: 할 수 없다 -> 할 수 있다)
    if exp_fidelity.get("polarity_flips_forbidden", True) and trusted_text:
        flips = trust_gate.polarity_flips(folded_answer, trusted_text)
        flips.extend(detect_polarity_and_permission_reversal(folded_answer, trusted_text))
        if flips:
            failures.append("polarity_flipped:" + ",".join(flips))
            details["polarity_flips"] = flips

    # Check permission flips (restriction lifting: 불인정 -> 인정)
    if exp_fidelity.get("permission_flips_forbidden", True) and trusted_text:
        perm_flips = trust_gate.permission_flips(folded_answer, trusted_text)
        if perm_flips:
            failures.append("permission_flipped:" + ",".join(perm_flips))
            details["permission_flips"] = perm_flips

    # Check role mismatches (table row/col transpose)
    if exp_fidelity.get("role_mismatches_forbidden", True) and trusted_text:
        roles = trust_gate.role_mismatches(folded_answer, trusted_text)
        roles.extend(detect_role_and_column_swaps(folded_answer, trusted_text))
        if roles:
            failures.append("role_mismatched:" + ",".join(roles))
            details["role_mismatches"] = roles

    # Check forbidden subject bindings (applying another subject's figures/facts)
    forbidden_bindings = exp_fidelity.get("forbidden_subject_bindings") or []
    for b in forbidden_bindings:
        subj = b.get("subject")
        val = b.get("forbidden_value")
        if subj and val and check_forbidden_subject_binding(folded_answer, subj, val):
            failures.append(f"subject_binding_mismatch:{subj}->{val}")
            details.setdefault("subject_mismatches", []).append(f"{subj}->{val}")

    # Check required facts if answered
    if status in ("answered", "partial"):
        required_facts = exp_fidelity.get("required_facts") or []
        for req in required_facts:
            if req not in folded_answer:
                failures.append(f"required_fact_missing:{req}")
                details.setdefault("missing_facts", []).append(req)

    passed = (len(failures) == 0)
    outcome = CORRECT if passed else WRONG
    return DimensionScore("source_fidelity", outcome, passed, failures, details)


def score_citation_accuracy(
    item: Mapping[str, Any],
    parsed: Optional[Mapping[str, Any]],
    allow_candidate_sources: bool = False
) -> DimensionScore:
    """Evaluates Dimension 2: Citation Accuracy (인용 정확성)."""
    failures: List[str] = []
    details: Dict[str, Any] = {}

    if parsed is None:
        return DimensionScore("citation_accuracy", WRONG, False, ["unparseable_response"], {})

    citations = [str(c) for c in (parsed.get("citations") or [])]
    set_cites = set(citations)
    exp_cite = (item.get("expected") or {}).get("citation_accuracy") or {}

    all_evidence_ids = {e["id"] for e in item["evidence"]}
    approved_ids = {e["id"] for e in item["evidence"] if is_approved_evidence(e, allow_candidate_sources=allow_candidate_sources)}

    # 1. Unknown citation ids
    unknown_cites = sorted(set_cites - all_evidence_ids)
    if unknown_cites:
        failures.append("unknown_citation_ids:" + ",".join(unknown_cites))
        details["unknown_citations"] = unknown_cites

    # 2. Must cite missing
    must_cite = set(exp_cite.get("must_cite") or [])
    missing_cites = sorted(must_cite - set_cites)
    if missing_cites:
        failures.append("missing_citations:" + ",".join(missing_cites))
        details["missing_citations"] = missing_cites

    # 3. Unlisted citations: a valid approved ID is not necessarily relevant.
    # Additional IDs require explicit permission.
    if not exp_cite.get("allow_unlisted_citations", False):
        unlisted = sorted(set_cites - set(must_cite))
        if unlisted:
            failures.append("unlisted_citations:" + ",".join(unlisted))
            details["unlisted_citations"] = unlisted

    # 4. Must not cite
    must_not = set(exp_cite.get("must_not_cite") or [])
    forbidden_hit = sorted(must_not & set_cites)
    if forbidden_hit:
        failures.append("forbidden_citations:" + ",".join(forbidden_hit))
        details["forbidden_citations"] = forbidden_hit

    # 4. Untrusted citations (unapproved sources cited when not allowed)
    if not exp_cite.get("allow_unapproved_citations", False):
        unapproved_cited = sorted((set_cites & all_evidence_ids) - approved_ids)
        if unapproved_cited:
            failures.append("unapproved_citations:" + ",".join(unapproved_cited))
            details["unapproved_citations"] = unapproved_cited

    # These are ID-level metrics against labeled required citations, not
    # semantic claim-to-citation entailment scores.
    valid_cites = set_cites & approved_ids
    if must_cite:
        precision = round(len(valid_cites & must_cite) / max(1, len(set_cites)), 4)
        recall = round(len(valid_cites & must_cite) / len(must_cite), 4)
    else:
        precision = round(len(valid_cites) / max(1, len(set_cites)), 4) if set_cites else 1.0
        recall = 1.0
    details["metric_scope"] = "citation_id_overlap_only"
    details["precision"] = precision
    details["recall"] = recall
    details["citations"] = citations

    passed = (len(failures) == 0)
    outcome = CORRECT if passed else WRONG
    return DimensionScore("citation_accuracy", outcome, passed, failures, details)


def score_procedural_integrity(item: Mapping[str, Any], parsed: Optional[Mapping[str, Any]]) -> DimensionScore:
    """Evaluates Dimension 3: Procedural Integrity (절차 오류)."""
    failures: List[str] = []
    details: Dict[str, Any] = {}

    if parsed is None:
        return DimensionScore("procedural_integrity", WRONG, False, ["unparseable_response"], {})

    answer = str(parsed.get("answer") or "")
    folded_answer = unicodedata.normalize("NFC", answer)
    status = parsed.get("status")
    exp_proc = (item.get("expected") or {}).get("procedural_integrity") or {}
    citations = [str(c) for c in (parsed.get("citations") or [])]

    expected_scope = exp_proc.get("expected_scope")
    forbidden_scopes = set(exp_proc.get("forbidden_scopes") or [])

    # Check scope from evidence citations
    evidence_by_id = {e["id"]: e for e in item["evidence"]}
    cited_domains = {evidence_by_id[cid]["source"]["domain"] for cid in citations if cid in evidence_by_id}

    if expected_scope in ("visa_issuance", "stay"):
        for fscope in forbidden_scopes:
            if fscope in cited_domains:
                failures.append(f"scope_mix_in_citations:{fscope}")
                details.setdefault("scope_violations", []).append(f"citation_domain:{fscope}")

    # Textual procedural scope check
    if "visa_issuance" in forbidden_scopes and ("사증발급신청서" in folded_answer or "재외공관" in folded_answer):
        failures.append("procedural_scope_mixed:visa_in_stay_scope")
    if "stay" in forbidden_scopes and ("체류자격 변경" in folded_answer or "외국인등록증 원본" in folded_answer):
        failures.append("procedural_scope_mixed:stay_in_visa_scope")

    # Forbidden procedures check
    forbidden_procs = exp_proc.get("forbidden_procedures") or []
    for fp in forbidden_procs:
        if fp in folded_answer:
            failures.append(f"forbidden_procedure_prescribed:{fp}")
            details.setdefault("forbidden_procedures_found", []).append(fp)

    # Clarification handling
    must_clarify = bool(exp_proc.get("must_clarify"))
    if must_clarify:
        if status != "clarify":
            failures.append("clarification_missed:expected_clarify_status")
            details["clarification_error"] = "expected_clarify_status"
    else:
        if status == "clarify":
            failures.append("unnecessary_clarification:expected_direct_action")
            details["clarification_error"] = "unnecessary_clarification"

    passed = (len(failures) == 0)
    outcome = CORRECT if passed else WRONG
    return DimensionScore("procedural_integrity", outcome, passed, failures, details)


def score_abstention_appropriateness(item: Mapping[str, Any], parsed: Optional[Mapping[str, Any]]) -> DimensionScore:
    """Evaluates Dimension 4: Abstention Appropriateness (부적절한 보류 / 과도한 침묵 방지)."""
    failures: List[str] = []
    details: Dict[str, Any] = {}

    if parsed is None:
        return DimensionScore("abstention_appropriateness", WRONG, False, ["unparseable_response"], {})

    status = parsed.get("status")
    allowed_statuses = set((item.get("expected") or {}).get("allowed_statuses") or [])
    exp_abs = (item.get("expected") or {}).get("abstention_appropriateness") or {}

    should_withhold = bool(exp_abs.get("should_withhold"))
    forbid_withholding = bool(exp_abs.get("forbid_withholding"))
    reason_cat = exp_abs.get("withholding_reason_category")

    details["status"] = status
    details["should_withhold"] = should_withhold
    details["forbid_withholding"] = forbid_withholding

    # Check allowed statuses
    if status not in allowed_statuses:
        failures.append(f"disallowed_status:{status} not in {'|'.join(sorted(allowed_statuses))}")

    # Check inappropriate withholding (over-abstention)
    if forbid_withholding:
        if status in ("insufficient_evidence",):
            failures.append("inappropriate_withholding:evidence_was_sufficient")
            details["withholding_error"] = "inappropriate_withholding"

    # Check unwarranted answering. Partial still contains claims, and must
    # not be treated as safe when the rubric requires complete withholding.
    if should_withhold:
        if status in ("answered", "partial"):
            failures.append("unwarranted_answer:should_have_withheld")
            details["withholding_error"] = "unwarranted_answer"

    passed = (len(failures) == 0)
    outcome = CORRECT if passed else WRONG
    return DimensionScore("abstention_appropriateness", outcome, passed, failures, details)


def score_artemis_response(
    item: Mapping[str, Any],
    response: Union[str, Mapping[str, Any]],
    allow_candidate_sources: Optional[bool] = None
) -> ArtemisItemScore:
    """Scores an AI response across all four dimensions, yielding a holistic Artemis score."""
    # Fail closed on malformed or tampered rubrics / evidence before scoring.
    invalid = [issue for issue in validate_eval_item(item) if issue.severity == "error"]
    if invalid:
        failures = [f"invalid_eval_item:{issue.field_name}:{issue.message}" for issue in invalid]
        dimensions = ("source_fidelity", "citation_accuracy",
                      "procedural_integrity", "abstention_appropriateness")
        return ArtemisItemScore(
            item_id=str(item.get("id") or "UNKNOWN") if isinstance(item, Mapping) else "UNKNOWN",
            overall_passed=False,
            primary_outcome=NOT_SCORABLE,
            dimension_scores={
                dimension: DimensionScore(dimension, NOT_SCORABLE, False,
                                          ["invalid_eval_item"], {})
                for dimension in dimensions
            },
            all_failures=failures,
            flags=["invalid_evaluation_data"],
            parsed_response=None,
            is_official_gold=False,
        )

    parsed = _parse_incoming_response(response)
    meta = item.get("metadata") or {}
    needs_review = bool(meta.get("needs_human_review", False))

    if allow_candidate_sources is None:
        allow_candidate_sources = needs_review

    dim_scores: Dict[str, DimensionScore] = {}
    dim_scores["source_fidelity"] = score_source_fidelity(item, parsed, allow_candidate_sources=allow_candidate_sources)
    dim_scores["citation_accuracy"] = score_citation_accuracy(item, parsed, allow_candidate_sources=allow_candidate_sources)
    dim_scores["procedural_integrity"] = score_procedural_integrity(item, parsed)
    dim_scores["abstention_appropriateness"] = score_abstention_appropriateness(item, parsed)

    all_failures: List[str] = []
    flags: List[str] = []

    for dname, dscore in dim_scores.items():
        all_failures.extend([f"[{dname}] {f}" for f in dscore.failures])

    if parsed and parsed.get("review_flags"):
        flags.extend([str(f) for f in parsed["review_flags"]])

    # Determine whether this item is verified official gold or pending candidate
    # Official accuracy metrics require an explicit gold designation and
    # independently signed official evidence. Synthetic fixtures and candidate
    # items must not turn into official gold just because a review flag is absent.
    sources_for_gold = [
        e for e in item.get("evidence", [])
        if e.get("source", {}).get("approval_state") not in ("community", "unapproved", "synthetic")
    ]
    is_official_gold = (
        meta.get("candidate_status") == "official_gold"
        and not needs_review
        and meta.get("is_synthetic") is False
        and bool(sources_for_gold)
        and all(
            e.get("source", {}).get("approval_state") == "approved"
            and e.get("source", {}).get("provenance") in ("official_manual", "official_notice")
            and e.get("source", {}).get("review_status") == "verified_by_human"
            and bool(e.get("source", {}).get("reviewed_by"))
            and bool(e.get("source", {}).get("reviewed_at"))
            and is_approved_evidence(e, check_hash=True, allow_candidate_sources=False)
            for e in sources_for_gold
        )
    )

    if needs_review or not is_official_gold:
        flags.append("pending_human_review")
        flags.append("candidate_evaluation_only")

    overall_passed = all(ds.passed for ds in dim_scores.values())
    primary_outcome = CORRECT if overall_passed else WRONG

    return ArtemisItemScore(
        item_id=str(item.get("id") or "UNKNOWN"),
        overall_passed=overall_passed,
        primary_outcome=primary_outcome,
        dimension_scores=dim_scores,
        all_failures=all_failures,
        flags=flags,
        parsed_response=parsed,
        is_official_gold=is_official_gold,
    )


# ---------------------------------------------------------------------------
# Suite Runner and Aggregator
# ---------------------------------------------------------------------------
@dataclass
class SuiteSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    dimension_pass_rates: Dict[str, float]
    dimension_failures: Dict[str, int]
    item_scores: List[ArtemisItemScore]
    official_gold_cases: int = 0
    official_gold_passed: int = 0
    official_gold_pass_rate: Optional[float] = None
    candidate_cases: int = 0
    candidate_passed: int = 0
    candidate_pass_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": self.pass_rate,
            "dimension_pass_rates": self.dimension_pass_rates,
            "dimension_failures": self.dimension_failures,
            "item_scores": [s.to_dict() for s in self.item_scores],
            "official_gold_cases": self.official_gold_cases,
            "official_gold_passed": self.official_gold_passed,
            "official_gold_pass_rate": self.official_gold_pass_rate,
            "candidate_cases": self.candidate_cases,
            "candidate_passed": self.candidate_passed,
            "candidate_pass_rate": self.candidate_pass_rate,
        }


def evaluate_suite(cases: Sequence[Mapping[str, Any]],
                   predictions: Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]) -> SuiteSummary:
    """Evaluates a full suite of cases against predictions."""
    if isinstance(predictions, list):
        pred_map = {str(p.get("id") or p.get("item_id")): p for p in predictions if isinstance(p, dict)}
    elif isinstance(predictions, dict) and "predictions" in predictions:
        pred_map = {str(p.get("id") or p.get("item_id")): p for p in predictions["predictions"]}
    elif isinstance(predictions, dict):
        pred_map = {str(k): v for k, v in predictions.items()}
    else:
        pred_map = {}

    scores: List[ArtemisItemScore] = []
    dim_passes = {d: 0 for d in ("source_fidelity", "citation_accuracy", "procedural_integrity", "abstention_appropriateness")}
    dim_fails = {d: 0 for d in dim_passes}

    for case in cases:
        cid = str(case["id"])
        pred = pred_map.get(cid)
        if isinstance(pred, dict) and "parsed" in pred:
            raw_response = pred["parsed"]
        elif isinstance(pred, dict) and "response" in pred:
            raw_response = pred["response"]
        else:
            raw_response = pred

        score = score_artemis_response(case, raw_response)
        scores.append(score)

        for dname in dim_passes:
            if score.dimension_scores[dname].passed:
                dim_passes[dname] += 1
            else:
                dim_fails[dname] += 1

    total = len(cases)
    passed_total = sum(1 for s in scores if s.overall_passed)
    pass_rate = round(passed_total / max(1, total), 4)

    dim_rates = {
        dname: round(dim_passes[dname] / max(1, total), 4) for dname in dim_passes
    }

    gold_scores = [s for s in scores if s.is_official_gold]
    cand_scores = [s for s in scores if not s.is_official_gold]

    official_gold_cases = len(gold_scores)
    official_gold_passed = sum(1 for s in gold_scores if s.overall_passed)
    official_gold_pass_rate = round(official_gold_passed / official_gold_cases, 4) if official_gold_cases > 0 else None

    candidate_cases = len(cand_scores)
    candidate_passed = sum(1 for s in cand_scores if s.overall_passed)
    candidate_pass_rate = round(candidate_passed / candidate_cases, 4) if candidate_cases > 0 else None

    return SuiteSummary(
        total_cases=total,
        passed_cases=passed_total,
        failed_cases=total - passed_total,
        pass_rate=pass_rate,
        dimension_pass_rates=dim_rates,
        dimension_failures=dim_fails,
        item_scores=scores,
        official_gold_cases=official_gold_cases,
        official_gold_passed=official_gold_passed,
        official_gold_pass_rate=official_gold_pass_rate,
        candidate_cases=candidate_cases,
        candidate_passed=candidate_passed,
        candidate_pass_rate=candidate_pass_rate,
    )


def generate_markdown_report(summary: SuiteSummary, title: str = "Artemis AI Response Evaluation Report") -> str:
    """Renders a concise, GitHub-flavored Markdown report."""
    lines = [
        f"# {title}",
        "",
        f"- **총 평가 문항**: {summary.total_cases}건",
        f"- **전체 통과**: {summary.passed_cases}건 ({summary.pass_rate * 100:.1f}%)",
        f"- **실패 / 오답**: {summary.failed_cases}건",
    ]

    if summary.official_gold_cases > 0:
        lines.append(f"- **공식 검증 완료 골드 문항**: {summary.official_gold_passed}/{summary.official_gold_cases} ({summary.official_gold_pass_rate * 100:.1f}%)")
    else:
        lines.append("- **공식 검증 완료 골드 문항**: 0건 (전 문항 사람 법률 검토 대기 상태 / 공식 정확도 미산출)")

    if summary.candidate_cases > 0:
        lines.append(f"- **검토 대기 후보 문항 (개발/보정용)**: {summary.candidate_passed}/{summary.candidate_cases} ({summary.candidate_pass_rate * 100:.1f}%)")

    lines.extend([
        "",
        "## 4대 핵심 평가 차원별 통과율",
        "",
        "| 평가 차원 | 통과 | 실패 | 통과율 |",
        "|---|---|---|---|",
    ])

    names_ko = {
        "source_fidelity": "출처 충실도 (Source Fidelity)",
        "citation_accuracy": "인용 정확성 (Citation Accuracy)",
        "procedural_integrity": "절차 오류 방지 (Procedural Integrity)",
        "abstention_appropriateness": "부적절한 보류 방지 (Abstention Appropriateness)",
    }

    for dname, rate in summary.dimension_pass_rates.items():
        fails = summary.dimension_failures[dname]
        passes = summary.total_cases - fails
        lines.append(f"| {names_ko.get(dname, dname)} | {passes} | {fails} | {rate * 100:.1f}% |")

    lines.extend([
        "",
        "## 문항별 상세 평가 결과",
        "",
        "| 문항 ID | 종합 판정 | 주요 실패 항목 및 진단 |",
        "|---|---|---|",
    ])

    for score in summary.item_scores:
        status_badge = "✅ 통과" if score.overall_passed else "❌ 실패"
        if score.all_failures:
            reason_text = "<br>".join(f"• `{f}`" for f in score.all_failures[:3])
            if len(score.all_failures) > 3:
                reason_text += f"<br>... (+{len(score.all_failures) - 3}건)"
        else:
            reason_text = "모든 평가 기준 충족"
        lines.append(f"| `{score.item_id}` | {status_badge} | {reason_text} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Artemis AI Response Evaluation Framework (Mission 004-A)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    val_parser = subparsers.add_parser("validate", help="Validate evaluation items or dataset file")
    val_parser.add_argument("path", type=Path, help="Path to JSON file")
    val_parser.add_argument("--skip-hashes", action="store_true", help="Skip SHA-256 hash checks")

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate predictions against cases")
    eval_parser.add_argument("--cases", type=Path, default=CASES_10_PATH, help="Path to cases JSON")
    eval_parser.add_argument("--predictions", type=Path, required=True, help="Path to predictions JSON")
    eval_parser.add_argument("--out", type=Path, help="Output JSON path")
    eval_parser.add_argument("--markdown", type=Path, help="Output Markdown report path")

    args = parser.parse_args(argv)

    if args.command == "validate":
        report = validate_dataset(args.path, check_hashes=not args.skip_hashes)
        print(f"Validation Result: {'VALID' if report.valid else 'INVALID'}")
        print(f"Items: {report.total_items}, Errors: {report.errors}, Warnings: {report.warnings}")
        for issue in report.issues:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"  [{prefix}] {issue.item_id} -> {issue.field_name}: {issue.message}")
        return 0 if report.valid else 1

    elif args.command == "evaluate":
        cases_data = json.loads(args.cases.read_text(encoding="utf-8"))
        cases = cases_data["items"] if isinstance(cases_data, dict) and "items" in cases_data else cases_data
        validation = validate_dataset(cases_data)
        if not validation.valid:
            print(f"Invalid evaluation dataset ({validation.errors} errors)", file=sys.stderr)
            for issue in validation.issues:
                if issue.severity == "error":
                    print(f"  {issue.item_id}: {issue.field_name}: {issue.message}", file=sys.stderr)
            return 2
        preds_data = json.loads(args.predictions.read_text(encoding="utf-8"))
        summary = evaluate_suite(cases, preds_data)

        if args.out:
            args.out.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"JSON report written to {args.out}")

        md = generate_markdown_report(summary)
        if args.markdown:
            args.markdown.write_text(md + "\n", encoding="utf-8")
            print(f"Markdown report written to {args.markdown}")
        else:
            print(md)

        return 0 if summary.failed_cases == 0 else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
