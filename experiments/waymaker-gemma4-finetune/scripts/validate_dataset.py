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
  - assistant answer missing any of the six required Korean section headers
  - assistant answer missing the non-legal-advice disclaimer

Status/visa codes (e.g. "G-1", "D-10") are stripped before the fee/period scan so a
phrase like "G-1 일반" is not misread as the period "1 일".

The summary also reports how many answers carry the full six-section structure and
which status codes the file covers (useful for confirming golden-eval coverage of
D-2 / F-4 / G-1-5 / E-7 / D-10 / F-2 / F-6).

Exit code 0 if no errors (warnings allowed), 1 otherwise.

Usage:
    python scripts/validate_dataset.py dataset/train.sample.jsonl dataset/eval.sample.jsonl
"""
import json
import re
import sys

REQUIRED_ROLES = ["system", "user", "assistant"]

# Six-section Korean answer structure required by the Waymaker behavior contract
# (kept in sync with scripts/eval_outputs.py).
SECTION_HEADERS = [
    "1. 요약",
    "2. 근거에서 확인되는 내용",
    "3. 아직 확인이 필요한 내용",
    "4. 주의할 점",
    "5. 다음 단계",
    "6. 사용한 근거",
]

DISCLAIMER_HINT = "법률 자문이 아닙니다"

# Visa/status codes such as D-2, D-10, F-2-7, G-1-5, F-5-T.
CODE_RE = re.compile(r"\b[A-H]-\d{1,2}(?:-(?:\d+[A-Z]?|T))?\b")

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
    # Strip status/visa codes first so "G-1 일반" is not misread as the period "1 일".
    assistant_codeless = CODE_RE.sub(" ", assistant)
    user_codeless = CODE_RE.sub(" ", user)
    for m in FEE_RE.finditer(assistant_codeless):
        if m.group(0) not in user_codeless:
            warnings.append(
                f"line {lineno}: fee `{m.group(0)}` in assistant answer not found in evidence/question"
            )
    for m in PERIOD_RE.finditer(assistant_codeless):
        if m.group(0) not in user_codeless:
            warnings.append(
                f"line {lineno}: period `{m.group(0)}` in assistant answer not found in evidence/question"
            )

    # The Waymaker answer contract requires the six-section structure and a
    # non-legal-advice disclaimer (heuristic string checks, not legal review).
    for header in SECTION_HEADERS:
        if header not in assistant:
            warnings.append(f"line {lineno}: assistant answer missing section header `{header}`")
    if DISCLAIMER_HINT not in assistant:
        warnings.append(f"line {lineno}: assistant answer missing non-legal-advice disclaimer")


def validate_file(path):
    errors, warnings = [], []
    n = 0
    refusals = 0
    structured = 0
    assistant_lens = []
    codes_seen = set()
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
                if all(h in a for h in SECTION_HEADERS):
                    structured += 1
                codes_seen.update(CODE_RE.findall(rec["messages"][1]["content"]))
            except (KeyError, IndexError, TypeError):
                pass

    print(f"== {path} ==")
    print(f"  examples:                {n}")
    print(f"  errors:                  {len(errors)}")
    print(f"  warnings:                {len(warnings)}")
    if assistant_lens:
        print(f"  avg assistant chars:     {sum(assistant_lens) // len(assistant_lens)}")
    print(f"  answers with defer/uncertainty language: {refusals}/{n}")
    print(f"  answers with full 6-section structure:   {structured}/{n}")
    print(f"  status codes covered:    {', '.join(sorted(codes_seen)) or '(none)'}")
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
