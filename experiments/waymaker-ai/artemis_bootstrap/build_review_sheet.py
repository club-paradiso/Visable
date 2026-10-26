"""Bundle the frozen real-manual case sets for human label review.

Why: every real-manual case set was machine-drafted by an agent and graded by
verbatim string checks. Before any of those numbers is quoted as quality, a
person has to confirm each label: is the expected status right, is the
expected string the right fact, is the gold page really the answer. This
writes one JSON file the review page loads: each case with its question,
expectations, the text of every evidence page (deduplicated), and the answer
E4B gave in the run that measured that set, so a reviewer can see where the
string check rejected a correct paraphrase.

Usage, from experiments/waymaker-ai/artemis_bootstrap::

    python build_review_sheet.py --out <dir>/cases.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manual_ledger  # noqa: E402

HERE = Path(__file__).resolve().parent

#: Case set → (Korean name, the run whose answers are shown next to each case).
SETS: Dict[str, tuple] = {
    "manual_oracle_cases.json": ("실제 매뉴얼 첫 측정", "2026-10-26-e4b-it-4bit-m1-8gb-manual-oracle"),
    "manual_routing_cases.json": ("절차별 라우팅", "2026-10-26-e4b-it-4bit-m1-8gb-routing-routed"),
    "manual_clarify_cases.json": ("되묻기(글로 답함)", "2026-10-26-e4b-it-4bit-m1-8gb-clarify-route-clarify"),
    "manual_buttons_cases.json": ("두 버튼 되묻기", "2026-10-26-e4b-it-4bit-m1-8gb-buttons-buttons"),
    "manual_always_ask_cases.json": ("항상 두 버튼", "2026-10-26-e4b-it-4bit-m1-8gb-always-ask-always-ask"),
    "manual_misclick_cases.json": ("잘못 누른 버튼 보완", "2026-10-27-e4b-it-4bit-m1-8gb-misclick-label"),
}
BEHAVIOUR_FIELDS = ("user_choice", "clarification_choice", "clarification_reply", "confirm_choice",
                    "on_label", "procedure_named_in_question")


def build() -> Dict[str, Any]:
    pages: Dict[str, Dict[str, Any]] = {}
    cases: List[Dict[str, Any]] = []
    sets = []
    for fname, (label, run) in SETS.items():
        path = HERE / fname
        raw = json.loads(path.read_text(encoding="utf-8"))
        resolved = manual_ledger.resolve_cases(raw["cases"])
        results = {}
        rec = HERE / "runs" / run / "run_record.json"
        if rec.exists():
            results = {r["case"]: r for r in json.loads(rec.read_text(encoding="utf-8")).get("results", [])}
        sets.append({"file": fname, "label": label, "run": run, "version": raw.get("version"),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "count": len(resolved)})
        for case in resolved:
            for e in case["evidence"]:
                pages.setdefault(e["id"], {"title": e["title"], "text": e["text"], "domain": e["source"]["domain"]})
            r = results.get(case["id"], {})
            parsed = r.get("final_output") or r.get("parsed") or {}
            cases.append({
                "key": f"{fname.removesuffix('_cases.json')}/{case['id']}",
                "set": fname, "id": case["id"], "group": case.get("group"), "purpose": case.get("purpose"),
                "question": case["question"],
                "behaviour": {k: case[k] for k in BEHAVIOUR_FIELDS if k in case},
                "evidence": [e["id"] for e in case["evidence"]],
                "expect": case["expect"],
                "model": {
                    "status": parsed.get("status"), "answer": parsed.get("answer"),
                    "citations": parsed.get("citations"), "outcome": r.get("outcome_checked"),
                    "failures": r.get("failures", []),
                } if r else None,
            })
    return {"version": "artemis-label-review-v1", "sets": sets, "cases": cases, "pages": pages}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", required=True)
    args = p.parse_args()
    data = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"cases": len(data["cases"]), "pages": len(data["pages"]), "bytes": out.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
