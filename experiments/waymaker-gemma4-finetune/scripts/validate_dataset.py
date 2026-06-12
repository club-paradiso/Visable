#!/usr/bin/env python3
"""Validate Waymaker fine-tuning JSONL dataset files.

Checks per line:
  - valid JSON with a `messages` array
  - roles are exactly system / user / assistant, in that order, with non-empty content
  - user message contains a non-empty [evidence_pack] section with at least one excerpt
Warnings (heuristic, not legal review):
  - unsupported absolute claims in the assistant answer ("무조건 가능합니다" etc.)
  - exact fee amounts in the assistant answer that do not appear in the user message
    (question + evidence_pack)
  - exact periods (N일/주/개월/년) in the assistant answer that do not appear in the
    user message

Exit code 0 if no errors (warnings allowed), 1 otherwise.

Usage:
    python scripts/validate_dataset.py dataset/train.sample.jsonl dataset/eval.sample.jsonl
"""
import json
import re
import sys

REQUIRED_ROLES = ["system", "user", "assistant"]

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

# 50,000원 / 13만원 / 13만 원 ...
FEE_RE = re.compile(r"\d[\d,]*\s*(?:만\s?)?원")
# 30일 / 2주 / 6개월 / 1년 ...
PERIOD_RE = re.compile(r"\d+\s*(?:일|주|개월|년)")

REFUSAL_HINTS = ["확인되지 않습니다", "확인할 수 없습니다", "답변을 유보", "근거가 부족", "추가 근거"]


def evidence_section(user_content: str) -> str:
    idx = user_content.find("[evidence_pack]")
    return "" if idx < 0 else user_content[idx:]


def validate_record(rec, lineno, errors, warnings):
    msgs = rec.get("messages")
    if not isinstance(msgs, list):
        errors.append(f"line {lineno}: missing or non-list `messages`")
        return

    roles = [m.get("role") for m in msgs if isinstance(m, dict)]
    if roles != REQUIRED_ROLES:
        errors.append(f"line {lineno}: roles must be exactly {REQUIRED_ROLES}, got {roles}")
        return

    for m in msgs:
        content = m.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"line {lineno}: empty content for role `{m.get('role')}`")
            return

    user = msgs[1]["content"]
    assistant = msgs[2]["content"]

    ev = evidence_section(user)
    if not ev:
        errors.append(f"line {lineno}: user message has no [evidence_pack] section")
        return
    excerpts = re.findall(r"excerpt:\s*(.+)", ev)
    if not excerpts or all(len(e.strip()) < 10 for e in excerpts):
        errors.append(f"line {lineno}: evidence_pack is empty or has no usable excerpt")
        return

    for pat in OVERCLAIM_PATTERNS:
        if pat in assistant:
            warnings.append(f"line {lineno}: absolute claim `{pat}` in assistant answer")

    # Fees/periods stated by the assistant must already appear in the user message
    # (evidence_pack or the question itself); otherwise they are likely invented.
    for m in FEE_RE.finditer(assistant):
        if m.group(0) not in user:
            warnings.append(
                f"line {lineno}: fee `{m.group(0)}` in assistant answer not found in evidence/question"
            )
    for m in PERIOD_RE.finditer(assistant):
        if m.group(0) not in user:
            warnings.append(
                f"line {lineno}: period `{m.group(0)}` in assistant answer not found in evidence/question"
            )


def validate_file(path):
    errors, warnings = [], []
    n = 0
    refusals = 0
    assistant_lens = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"line {lineno}: invalid JSON ({e})")
                continue
            validate_record(rec, lineno, errors, warnings)
            try:
                a = rec["messages"][2]["content"]
                assistant_lens.append(len(a))
                if any(h in a for h in REFUSAL_HINTS):
                    refusals += 1
            except (KeyError, IndexError, TypeError):
                pass

    print(f"== {path} ==")
    print(f"  examples:                {n}")
    print(f"  errors:                  {len(errors)}")
    print(f"  warnings:                {len(warnings)}")
    if assistant_lens:
        print(f"  avg assistant chars:     {sum(assistant_lens) // len(assistant_lens)}")
    print(f"  answers with defer/uncertainty language: {refusals}/{n}")
    for e in errors:
        print(f"  ERROR   {e}")
    for w in warnings:
        print(f"  WARNING {w}")
    return len(errors)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    total_errors = sum(validate_file(p) for p in argv[1:])
    print(f"\nTotal errors: {total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
