"""Record a bounded CUDA inference smoke run, or the precise preflight blocker.

Reproduces the three Colab cases of 2026-10-30: no evidence, one synthetic
source, two conflicting synthetic sources. The synthetic rules are invented
test text, not law. This checks execution and the response contract only;
it is not a legal benchmark and it never sets official gold accuracy.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gemma4_cuda_runtime import PreparedRun
from waymaker_ai import cuda_policy

# 합성 자료만 사용: 실제 법률이나 행정 규칙이 아닙니다.
CASES = [
    ("no_evidence", {"question": "체류기간을 연장하려면 어떤 사항을 확인해야 하나요?", "evidence": []}),
    ("synthetic_citation", {"question": "가상 규칙에서 신청 기한은 언제인가요?", "evidence": [
        {"id": "SYN-1", "text": "가상의 규칙: 신청은 만료일 30일 전까지 해야 한다."}]}),
    ("synthetic_conflict", {"question": "가상 규칙에서 신청 기한은 언제인가요?", "evidence": [
        {"id": "SYN-1", "text": "가상의 규칙: 신청은 만료일 30일 전까지 해야 한다."},
        {"id": "SYN-2", "text": "가상의 규칙: 신청은 만료일 10일 전까지 해야 한다."}]}),
]
EXIT_CODES = {"completed": 0, "generated_but_invalid": 2, "failed": 1, "not_executed": 3}


def main(argv=None, prepared=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, choices=[32, 64, 96, 128], default=96)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--size-only-weights", action="store_true",
                        help="Skip the 16 GB SHA-256; the record is then excluded from metric groups")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("Refusing to overwrite an existing inference record")
    prepared = prepared or PreparedRun(args.cache_dir, verify_weights=not args.size_only_weights)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    record = prepared.run(CASES, args.max_new_tokens, evidence_kind="synthetic")
    record.update(kind="cuda_inference_smoke", started_at=started,
                  finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
    cuda_policy.validate_run_record(record)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["execution_status"], "reason": record.get("not_executed_reason"),
                      "cases": {c["case_id"]: c["execution_status"] for c in record["cases"]}}, ensure_ascii=False))
    return EXIT_CODES[record["execution_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
