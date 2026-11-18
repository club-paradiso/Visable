"""DEV-20 v2: the development split with the rubric decisions from benchmarks/dev20_rubric_review.json applied.

v1 (`artemis_eval_dev_20.json`) stays byte for byte, so every earlier run still re-scores against the
digest the isolation manifest records. v2 is a separate file with its own manifest
(`DEV20_V2_MANIFEST.json`) that pins the v1 digest, the v2 digest and the review file it was built from.

Each decision maps to a rubric change:

  - update: the evidence text is replaced (new evidence id, new content hash, source fields from REWRITTEN)
    and allowed_statuses, required_facts and forbidden_claims come from the decided proposal. Subject
    bindings and procedures that only held for the old text are replaced from REWRITTEN.
  - withhold_correct: the system's withholding is the expected answer (insufficient_evidence; no citation
    or fact is required).
  - accept_conditional: a conditional general answer counts as well as a clarification question.
  - loosen: required_facts come from the decided proposal.

The decisions are Claude's under the owner's delegation, by the rule stated in the review file's
decision_meta. This is rubric hygiene against cited primary text, not legal review. No model is called.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent
BENCHMARKS = BOOT / "benchmarks"
DEV20_V1 = BENCHMARKS / "artemis_eval_dev_20.json"
DEV20_V2 = BENCHMARKS / "artemis_eval_dev_20_v2.json"
REVIEW = BENCHMARKS / "dev20_rubric_review.json"
V2_MANIFEST = BENCHMARKS / "DEV20_V2_MANIFEST.json"
MANUAL = "https://www.hikorea.go.kr"
LAW = "https://www.law.go.kr/법령/"

#: For each `update` decision: which evidence is rewritten, its new id and source fields, and the rubric
#: fields that only held for the old text. Source fields name where the new text was checked.
REWRITTEN = {
    "ARTEMIS-004-DEV-001": dict(
        old="EV-DEV-001-A", new="EV-DEV-001-A2",
        title="체류민원 자격별 안내 매뉴얼(261019) 유학(D-2) 체류자격 변경허가 기본원칙",
        source=dict(provenance="official_manual", domain="stay", document_id="체류민원 자격별 안내 매뉴얼",
                    provision="유학(D-2) 체류자격 변경허가 가. 기본원칙", effective_date="2026-10-19", source_url=MANUAL),
        forbidden_subject_bindings=[],
        procedural=dict(expected_procedure=None, forbidden_procedures=[])),
    "ARTEMIS-004-DEV-005": dict(
        old="EV-DEV-005-A", new="EV-DEV-005-A2",
        title="출입국관리법 시행규칙 제72조 (각종 허가 등에 관한 수수료)",
        source=dict(provenance="official_manual", domain="stay", document_id="출입국관리법 시행규칙",
                    provision="제72조 제6호·제10호", effective_date="2026-10-23", source_url=LAW + "출입국관리법시행규칙"),
        forbidden_subject_bindings=[{"subject": "외국인등록증", "forbidden_value": "30,000원"},
                                    {"subject": "외국인등록증", "forbidden_value": "60,000원"}],
        procedural={}),
    "ARTEMIS-004-DEV-011": dict(
        old="EV-DEV-011-A", new="EV-DEV-011-A2",
        title="Immigration Control Act Article 21(1) and Enforcement Decree Article 26-2(1) (Change or Addition of Workplace)",
        source=dict(provenance="official_manual", domain="stay", document_id="출입국관리법",
                    provision="제21조 제1항, 시행령 제26조의2 제1항", effective_date="2026-10-02",
                    source_url=LAW + "출입국관리법"),
        forbidden_subject_bindings=[],
        procedural=dict(expected_procedure=None)),
    "ARTEMIS-004-DEV-017": dict(
        old="EV-DEV-017-A", new="EV-DEV-017-A2",
        title="체류민원 자격별 안내 매뉴얼(261019) 유학(D-2) 1회 부여 상한과 학위과정별 최대 체류기간 상한",
        source=dict(provenance="official_manual", domain="stay", document_id="체류민원 자격별 안내 매뉴얼",
                    provision="유학(D-2) 체류기간 상한 · 학교 변경 · 체류기간 연장 특례", effective_date="2026-10-19",
                    source_url=MANUAL),
        forbidden_subject_bindings=None,
        procedural={}),
    "ARTEMIS-004-DEV-020": dict(
        old="EV-DEV-020-OFFICIAL", new="EV-DEV-020-OFFICIAL-A2",
        title="통합신청서 양식(사증민원 자격별 안내 매뉴얼 261019)과 출입국관리법 시행규칙 제72조 제10호 (외국인등록증 재발급)",
        source=dict(provenance="official_manual", domain="stay", document_id="출입국관리법 시행규칙",
                    provision="제72조 제10호 · 통합신청서 사진 규격", effective_date="2026-10-23",
                    source_url=LAW + "출입국관리법시행규칙"),
        forbidden_subject_bindings=None,
        procedural={}),
}
WITHHOLD_REASON = "evidence_not_verifiable"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def apply_decision(item: dict, decision: dict) -> dict:
    """One DEV-20 item with one decided rubric change applied. The input is not modified."""
    item = copy.deepcopy(item)
    exp = item["expected"]
    fid, cite = exp["source_fidelity"], exp["citation_accuracy"]
    proc, abst = exp["procedural_integrity"], exp["abstention_appropriateness"]
    option, proposal = decision["option"], decision.get("proposal") or {}
    if option == "update":
        spec = REWRITTEN[item["id"]]
        position = next(n for n, ev in enumerate(item["evidence"]) if ev["id"] == spec["old"])
        old = item["evidence"][position]
        text = proposal["evidence_text"]
        digest = sha256_text(text)
        item["evidence"][position] = {
            "id": spec["new"], "title": spec["title"], "text": text,
            "source": {**old["source"], **spec["source"], "approval_state": "under_review",
                       "approved_sha256": digest, "content_sha256": digest,
                       "review_status": "unreviewed", "reviewed_by": None, "reviewed_at": None},
        }
        exp["allowed_statuses"] = list(proposal["allowed_statuses"])
        fid["required_facts"] = list(proposal["required_facts"])
        fid["forbidden_claims"] = list(proposal["forbidden_claims"])
        if spec["forbidden_subject_bindings"] is not None:
            fid["forbidden_subject_bindings"] = spec["forbidden_subject_bindings"]
        proc.update(spec["procedural"])
        cite["must_cite"] = [spec["new"] if c == spec["old"] else c for c in cite["must_cite"]]
    elif option == "withhold_correct":
        exp["allowed_statuses"] = ["insufficient_evidence"]
        fid["required_facts"] = []
        cite["must_cite"] = []
        proc.update(expected_procedure=None, must_clarify=False)
        abst.update(should_withhold=True, forbid_withholding=False, withholding_reason_category=WITHHOLD_REASON)
    elif option == "accept_conditional":
        exp["allowed_statuses"] = list(proposal["allowed_statuses"])
        fid["required_facts"] = list(proposal["required_facts"])
        fid["forbidden_claims"] = list(proposal["forbidden_claims"])
        proc["must_clarify"] = False
    elif option == "loosen":
        fid["required_facts"] = list(proposal["required_facts"])
    elif option != "keep":
        raise ValueError(f"{item['id']}: no v2 rule for option {option!r}")
    item["metadata"] = {**item["metadata"], "rubric_revision": {
        "dev20_version": "v2", "option": option, "decided_by": decision["decided_by"],
        "decided_at": decision["decided_at"], "review_file": "benchmarks/dev20_rubric_review.json"}}
    return item


def build(v1: dict, review: dict) -> dict:
    if review.get("status") != "decided":
        raise ValueError("the rubric review is not decided")
    decisions = {i["id"]: i["decision"] for i in review["items"]}
    unknown = set(decisions) - {i["id"] for i in v1["items"]}
    if unknown:
        raise ValueError(f"decisions for unknown items: {sorted(unknown)}")
    items = [apply_decision(i, decisions[i["id"]]) if i["id"] in decisions else copy.deepcopy(i) for i in v1["items"]]
    return {"version": v1["version"],
            "description": "Artemis DEV-20 v2: the 20 development cases with the 2026-11-03 rubric decisions applied "
                           "(benchmarks/dev20_rubric_review.json); v1 is artemis_eval_dev_20.json",
            "items": items}


def dump(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def manifest(v1_raw: bytes, v2_raw: bytes, review_raw: bytes, review: dict) -> dict:
    return {"manifest_version": "artemis-dev20-v2-manifest/1.0",
            "dev20_v1_sha256": sha256_bytes(v1_raw), "dev20_v2_sha256": sha256_bytes(v2_raw),
            "rubric_review_sha256": sha256_bytes(review_raw),
            "decided_by": review["decision_meta"]["decided_by"],
            "options": {i["id"]: i["decision"]["option"] for i in review["items"]},
            "note": "Development Candidate Diagnostic set; not Official Gold Accuracy and not legally reviewed."}


def main() -> int:
    v1_raw, review_raw = DEV20_V1.read_bytes(), REVIEW.read_bytes()
    review = json.loads(review_raw)
    v2_raw = dump(build(json.loads(v1_raw), review))
    DEV20_V2.write_bytes(v2_raw)
    V2_MANIFEST.write_bytes(dump(manifest(v1_raw, v2_raw, review_raw, review)))
    print(json.dumps({"dev20_v2_sha256": sha256_bytes(v2_raw)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
