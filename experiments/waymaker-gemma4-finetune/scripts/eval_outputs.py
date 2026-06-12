#!/usr/bin/env python3
"""Score model outputs from the Waymaker Gemma-4 fine-tune experiment.

Input: JSONL where each line is one generation result:
    {
      "id": "optional-id",
      "expected_behavior": "answer" | "defer",
      "evidence_pack": "<the evidence text the model was given>",
      "output": "<the model's full answer text>"
    }

Per-record checks (all heuristic string checks, NOT legal review):
  citation   — output contains a `사용한 근거` section
  structure  — all six Korean section headers are present
  defer_ok   — if expected_behavior == "defer", output contains refusal/defer language;
               if "answer", check passes automatically
  no_overclaim — none of the known absolute-claim phrases appear
  no_invented_fee_period — fee amounts (…원) and periods (N일/주/개월/년) in the output
               also appear in evidence_pack (or there are none)
  no_invented_doc_list — heuristic: output does not assert a definitive document list
               ("필요한 서류는 다음과 같습니다" 등) unless the evidence mentions documents

Usage:
    python scripts/eval_outputs.py outputs.jsonl
"""
import json
import re
import sys

SECTION_HEADERS = [
    "1. 요약",
    "2. 근거에서 확인되는 내용",
    "3. 아직 확인이 필요한 내용",
    "4. 주의할 점",
    "5. 다음 단계",
    "6. 사용한 근거",
]

DEFER_PHRASES = [
    "답변을 유보",
    "확인할 수 없습니다",
    "확인되지 않습니다",
    "근거가 부족",
    "추가 근거",
    "근거에 포함되어 있지 않",
]

OVERCLAIM_PATTERNS = [
    "무조건 가능",
    "무조건 됩니다",
    "무조건 허가",
    "반드시 허가",
    "반드시 승인",
    "반드시 가능",
    "100% 가능",
    "100% 승인",
    "확실히 허가",
    "확실히 승인",
    "절대 문제 없",
    "걱정할 필요 없",
]

DOC_LIST_PATTERNS = [
    "필요한 서류는 다음과 같습니다",
    "제출 서류는 다음과 같습니다",
    "준비 서류는 다음과 같습니다",
]

FEE_RE = re.compile(r"\d[\d,]*\s*(?:만\s?)?원")
PERIOD_RE = re.compile(r"\d+\s*(?:일|주|개월|년)")

CHECKS = ["citation", "structure", "defer_ok", "no_overclaim",
          "no_invented_fee_period", "no_invented_doc_list"]


def score_record(rec):
    out = rec.get("output", "") or ""
    evidence = rec.get("evidence_pack", "") or ""
    expected = rec.get("expected_behavior", "answer")

    r = {}
    r["citation"] = "사용한 근거" in out
    r["structure"] = all(h in out for h in SECTION_HEADERS)
    r["defer_ok"] = expected != "defer" or any(p in out for p in DEFER_PHRASES)
    r["no_overclaim"] = not any(p in out for p in OVERCLAIM_PATTERNS)

    invented = [m.group(0) for m in FEE_RE.finditer(out) if m.group(0) not in evidence]
    invented += [m.group(0) for m in PERIOD_RE.finditer(out) if m.group(0) not in evidence]
    r["no_invented_fee_period"] = not invented

    doc_claim = any(p in out for p in DOC_LIST_PATTERNS)
    r["no_invented_doc_list"] = not doc_claim or "서류" in evidence

    return r, invented


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2

    records = []
    with open(argv[1], encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append((lineno, json.loads(line)))
            except json.JSONDecodeError as e:
                print(f"line {lineno}: invalid JSON, skipped ({e})")

    if not records:
        print("No records to score.")
        return 1

    totals = {c: 0 for c in CHECKS}
    print(f"{'id':<20} " + " ".join(f"{c:<22}" for c in CHECKS))
    for lineno, rec in records:
        rid = str(rec.get("id", f"line{lineno}"))[:20]
        r, invented = score_record(rec)
        for c in CHECKS:
            totals[c] += r[c]
        print(f"{rid:<20} " + " ".join(f"{'PASS' if r[c] else 'FAIL':<22}" for c in CHECKS))
        if invented:
            print(f"  {rid}: ungrounded fee/period mentions: {invented}")

    n = len(records)
    print("\n== score report ==")
    for c in CHECKS:
        print(f"  {c:<24} {totals[c]}/{n} ({100 * totals[c] / n:.0f}%)")
    overall = sum(totals.values()) / (n * len(CHECKS))
    print(f"  {'overall':<24} {overall * 100:.0f}%")
    print("\nNote: heuristic string checks only — manual review is still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
