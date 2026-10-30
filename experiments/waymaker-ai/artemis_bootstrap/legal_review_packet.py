"""Mission 005-F: build and validate the packet a qualified legal reviewer fills in.

The packet holds, per DEV-20 item: question, evidence, the recorded model response,
the existing candidate expected answer, scorer findings and the open legal questions,
plus empty decision fields. It never edits the benchmark. A label can only become
gold through authorized review recorded here and a separate, versioned dataset.

    python3 artemis_bootstrap/legal_review_packet.py build --run-dir runs/mission005e/dev20_contract_v2 --out runs/mission005f/review_packet.json
    python3 artemis_bootstrap/legal_review_packet.py validate runs/mission005f/review_packet.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))

SCHEMA_VERSION = "waymaker-artemis-legal-review/1.0"
STATES = ("not_reviewed", "in_review", "agree", "disagree", "needs_more_information", "escalated")
TRI = (None, "yes", "no", "uncertain")
DECISION_QUESTIONS = (
    "source_authentic", "effective_at_relevant_time", "applies_to_subject_and_procedure",
    "response_preserves_legal_meaning", "candidate_expected_answer_valid", "source_trust_rules_appropriate",
    "evaluator_classification_justified")

#: Analyst notes from the Mission 005-E report. Opinions to check, not findings.
ANALYST_NOTES = {
    "ARTEMIS-004-DEV-002": ["Is a clarification about residence acceptable when the question already says the user lives abroad?"],
    "ARTEMIS-004-DEV-003": ["Is 'D-2-1은 전문학사' a required fact or an optional contrastive explanation?"],
    "ARTEMIS-004-DEV-004": ["Is 'E-7-1은 전문인력' a required fact or an optional contrastive explanation?"],
    "ARTEMIS-004-DEV-006": ["Must the answer state the reason (결핵 고위험국가) for the obligation?"],
    "ARTEMIS-004-DEV-009": ["'금지됩니다' versus the required '할 수 없': same legal meaning?",
                            "Is '청소년유해업소' a necessary element of a correct answer?"],
    "ARTEMIS-004-DEV-011": ["Product language policy answers in the question's language; the rubric's required facts are English. Which governs?"],
    "ARTEMIS-004-DEV-012": ["Rubric facts mix languages (rubric_language_mismatch)."],
    "ARTEMIS-004-DEV-020": ["Should an unverified community post ever be cited, even to rebut it?"],
}


def empty_decision(required_facts: list) -> dict:
    return {"state": "not_reviewed", **{q: None for q in DECISION_QUESTIONS},
            "required_facts_necessary": [{"fact": f, "necessary": None, "note": ""} for f in required_facts],
            "reasoning": "", "legal_authority": [],
            "reviewer": {"name": None, "role": None, "qualification": None, "organization": None},
            "reviewed_at": None, "second_review": None, "disagreement": None}


def build(run_dir: Path) -> dict:
    import score_dev20
    items, dataset_sha = score_dev20.load_dev_items()
    result = score_dev20.score(run_dir)
    diags = {c["case_id"]: c for c in result["cases"]}
    gens = {g["case_id"]: g for g in result["generations"]}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BOOT, capture_output=True, text=True).stdout.strip() or None
    packet_items = []
    for item in items:
        exp = item.get("expected") or {}
        facts = (exp.get("source_fidelity") or {}).get("required_facts") or []
        gen, diag = gens.get(item["id"]) or {}, diags.get(item["id"]) or {}
        packet_items.append({
            "item_id": item["id"], "question": item["question"],
            "evidence": [{"id": e["id"], "title": e.get("title", ""), "text": e.get("text", ""), "source": e.get("source", {})}
                         for e in item["evidence"]],
            "model_response": {"contract_version": gen.get("contract_version", "v1"), "response": gen.get("response"),
                               "raw_output_sha256": gen.get("raw_output_sha256"), "session_id": gen.get("session_id")},
            "candidate_expected_answer": exp,
            "scorer_findings": {"diagnostic_outcome": diag.get("diagnostic_outcome"),
                                "failure_codes": diag.get("failure_codes"), "dimensions": diag.get("dimensions"),
                                "review_annotation": diag.get("review_annotation")},
            "open_legal_questions": ANALYST_NOTES.get(item["id"], []),
            "review": empty_decision(facts), "audit_trail": []})
    return {"schema_version": SCHEMA_VERSION,
            "packet_version": "005-F.1",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "generated_from": {"code_commit": commit, "dataset_sha256": dataset_sha,
                               "run_dir": str(run_dir.relative_to(BOOT)) if run_dir.is_absolute() else str(run_dir),
                               "generations_sha256": result["integrity"]["generations_sha256"]},
            "benchmark_labels_changed": False,
            "gold_promotion_policy": "A candidate label becomes gold only after authorized review recorded in this packet "
                                     "and publication as a separate, versioned dataset. This packet never edits the benchmark.",
            "independent_legal_review": "not_verified",
            "items": packet_items}


def validate(packet: dict) -> list[str]:
    """Problems that would make a filled-in packet unusable or misleading."""
    problems = []
    if packet.get("schema_version") != SCHEMA_VERSION:
        problems.append("wrong schema_version")
    if packet.get("benchmark_labels_changed") is not False:
        problems.append("benchmark_labels_changed must stay false")
    reviewed = 0
    for it in packet.get("items", []):
        rid, rev = it.get("item_id", "?"), it.get("review") or {}
        if rev.get("state") not in STATES:
            problems.append(f"{rid}: unknown state {rev.get('state')!r}")
            continue
        for q in DECISION_QUESTIONS:
            if rev.get(q) not in TRI:
                problems.append(f"{rid}: {q} must be one of yes/no/uncertain/null")
        if rev["state"] != "not_reviewed":
            who = rev.get("reviewer") or {}
            if not who.get("name") or not who.get("qualification"):
                problems.append(f"{rid}: a reviewed item needs reviewer name and qualification")
            if not rev.get("reviewed_at"):
                problems.append(f"{rid}: a reviewed item needs reviewed_at")
            if not it.get("audit_trail"):
                problems.append(f"{rid}: a state change needs an audit_trail entry")
        if rev["state"] in ("agree", "disagree"):
            reviewed += 1
            if not rev.get("reasoning"):
                problems.append(f"{rid}: a decision needs reasoning")
            if rev["state"] == "disagree" and not rev.get("legal_authority"):
                problems.append(f"{rid}: a disagreement needs supporting legal authority")
        second = rev.get("second_review")
        if second and second.get("state") != rev["state"] and not rev.get("disagreement"):
            problems.append(f"{rid}: reviewers disagree; record the disagreement and its resolution")
        for entry in it.get("audit_trail", []):
            if not {"at", "actor", "action", "from_state", "to_state"} <= set(entry):
                problems.append(f"{rid}: incomplete audit_trail entry")
        if "gold" in json.dumps(rev).lower() and "gold" not in json.dumps(it.get("candidate_expected_answer", "")).lower():
            problems.append(f"{rid}: review fields must not declare gold labels")
    if packet.get("independent_legal_review") != "not_verified" and reviewed < len(packet.get("items", [])):
        problems.append("independent_legal_review can leave not_verified only when every item is decided")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--run-dir", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("packet", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        packet = build(BOOT / args.run_dir if not args.run_dir.is_absolute() else args.run_dir)
        out = BOOT / args.out if not args.out.is_absolute() else args.out
        out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"items": len(packet["items"]), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}))
        return 0
    problems = validate(json.loads(args.packet.read_text(encoding="utf-8")))
    print(json.dumps({"problems": problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 8


if __name__ == "__main__":
    raise SystemExit(main())
