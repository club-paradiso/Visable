#!/usr/bin/env python3
"""Tests for scripts/diff_manual_paragraph_editions.py — the paragraph-anchored
manual diff used for 배포용-HWP editions, which carry no page layer.

Runnable standalone (`python3 scripts/tests/test_diff_manual_paragraph_editions.py`)
or via pytest. Stdlib-only, no network. Verifies:
  * identical inputs report zero change,
  * a changed / inserted / deleted paragraph is detected with the right kind and
    NO false positives on the untouched paragraphs around it,
  * a change is anchored to its nearest preceding 체류자격 heading, and the codes
    reported for it come from that anchor plus the changed text,
  * whitespace-only reflow is not reported as a content change,
  * codes group under their parent (D-2-1 lands under D-2, F-2-7S under F-2),
  * a date like 2026-09-01 is never mistaken for a status code,
  * the extraction-mismatch heuristic fires on a cross-pipeline pair and not on
    a clean same-pipeline pair,
  * the tool never writes to protected data files.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import diff_manual_paragraph_editions as dmp  # noqa: E402

PROTECTED = ["visa_data.json", "doc_master.json", "backend/data/visas.json"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


def _base_lines():
    return [
        "사증발급 안내매뉴얼",
        "유학(D-2)",
        "1. 체류자격 해당자",
        "가. 전문대학 이상의 교육기관에서 정규과정의 교육을 받는 사람",
        "특정활동(E-7)",
        "1. 도입직종",
        "가. 전문인력 67개 직종",
        "나. 준전문인력 10개 직종",
    ]


def _write(tmp: Path, name: str, lines) -> Path:
    p = tmp / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _run(tmp: Path, old_lines, new_lines):
    old_p = _write(tmp, "old.txt", old_lines)
    new_p = _write(tmp, "new.txt", new_lines)
    old = dmp.load(old_p)
    new = dmp.load(new_p)
    hunks = dmp.diff(old, new)
    return old, new, hunks, dmp.by_code(hunks)


def test_identical_inputs_no_change(tmp_path):
    _old, _new, hunks, grouped = _run(tmp_path, _base_lines(), _base_lines())
    assert hunks == [], f"identical inputs must produce no hunks, got {hunks}"
    assert grouped == {}


def test_changed_paragraph_detected_with_anchor_and_codes(tmp_path):
    new_lines = list(_base_lines())
    new_lines[6] = "가. 전문인력 69개 직종"
    _old, _new, hunks, grouped = _run(tmp_path, _base_lines(), new_lines)

    assert len(hunks) == 1, f"exactly one hunk expected, got {len(hunks)}"
    h = hunks[0]
    assert h.kind == "changed"
    assert h.old_lines == ["가. 전문인력 67개 직종"]
    assert h.new_lines == ["가. 전문인력 69개 직종"]
    # Anchored to the nearest preceding code-bearing heading, not the D-2 one.
    assert "E-7" in h.anchor, f"anchor should be the E-7 heading, got {h.anchor!r}"
    assert h.codes == ["E-7"]
    assert set(grouped) == {"E-7"}, f"only E-7 should be flagged, got {set(grouped)}"
    assert grouped["E-7"]["changed"] == 1


def test_insert_and_delete_do_not_shift_following_paragraphs(tmp_path):
    new_lines = list(_base_lines())
    new_lines.insert(7, "나-1. 육성형 해외전문기술인력 특례")
    _old, _new, hunks, grouped = _run(tmp_path, _base_lines(), new_lines)
    assert [h.kind for h in hunks] == ["added"]
    assert hunks[0].new_lines == ["나-1. 육성형 해외전문기술인력 특례"]

    # And the reverse direction is a delete, again with no collateral hunks.
    _old, _new, hunks_del, _g = _run(tmp_path, new_lines, _base_lines())
    assert [h.kind for h in hunks_del] == ["removed"]
    assert hunks_del[0].old_lines == ["나-1. 육성형 해외전문기술인력 특례"]


def test_whitespace_reflow_is_not_a_change(tmp_path):
    new_lines = [f"  {line}   " for line in _base_lines()]
    new_lines[3] = "가.  전문대학 이상의   교육기관에서 정규과정의 교육을 받는 사람"
    _old, _new, hunks, _g = _run(tmp_path, _base_lines(), new_lines)
    assert hunks == [], f"whitespace-only reflow must not be reported, got {hunks}"


def test_subcodes_group_under_parent(tmp_path):
    old_lines = ["유학(D-2)", "가. 학사유학(D-2-2) 대상", "거주(F-2)", "나. 점수제(F-2-7S) 대상"]
    new_lines = ["유학(D-2)", "가. 학사유학(D-2-2) 대상 확대", "거주(F-2)", "나. 점수제(F-2-7S) 대상 확대"]
    _old, _new, _hunks, grouped = _run(tmp_path, old_lines, new_lines)
    assert set(grouped) == {"D-2", "F-2"}, f"expected parent grouping, got {set(grouped)}"
    assert "D-2-2" in grouped["D-2"]["codes"]
    assert "F-2-7S" in grouped["F-2"]["codes"]


def test_date_is_not_mistaken_for_a_status_code(tmp_path):
    old_lines = ["시행일자 2026-07-31 기준", "적용 대상"]
    new_lines = ["시행일자 2026-09-01 기준", "적용 대상"]
    _old, _new, hunks, grouped = _run(tmp_path, old_lines, new_lines)
    assert len(hunks) == 1
    assert hunks[0].codes == [], f"a date must not parse as a code, got {hunks[0].codes}"
    assert grouped == {}


def test_extraction_mismatch_heuristic(tmp_path):
    # Same pipeline, one edit -> well under the threshold.
    new_lines = list(_base_lines())
    new_lines[6] = "가. 전문인력 69개 직종"
    old, new, hunks, _g = _run(tmp_path, _base_lines(), new_lines)
    touched = sum(len(h.old_lines) + len(h.new_lines) for h in hunks)
    ratio = touched / (len(old) + len(new))
    assert ratio <= dmp.MISMATCH_CHANGED_RATIO

    # Wholly different text -> mismatch suspected.
    other = [f"완전히 다른 추출 결과 {i}" for i in range(len(_base_lines()))]
    old2, new2, hunks2, _g2 = _run(tmp_path, _base_lines(), other)
    touched2 = sum(len(h.old_lines) + len(h.new_lines) for h in hunks2)
    ratio2 = touched2 / (len(old2) + len(new2))
    assert ratio2 > dmp.MISMATCH_CHANGED_RATIO


def test_no_protected_file_writes(tmp_path):
    before = {f: _sha(ROOT / f) for f in PROTECTED}
    new_lines = list(_base_lines())
    new_lines[6] = "가. 전문인력 69개 직종"
    old_p = _write(tmp_path, "old.txt", _base_lines())
    new_p = _write(tmp_path, "new.txt", new_lines)
    out_md, out_json = tmp_path / "r.md", tmp_path / "r.json"

    argv = sys.argv
    sys.argv = ["diff_manual_paragraph_editions.py",
                "--old", str(old_p), "--new", str(new_p), "--role", "visa",
                "--out-md", str(out_md), "--out-json", str(out_json)]
    try:
        assert dmp.main() == 0
    finally:
        sys.argv = argv

    assert out_md.exists() and out_json.exists()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["meta"]["review_status"] == "candidates_for_human_review"
    assert payload["affected_status_codes"][0]["parent"] == "E-7"
    after = {f: _sha(ROOT / f) for f in PROTECTED}
    assert before == after, "protected data files must never be written"


def _run_all_standalone() -> int:
    import tempfile
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        with tempfile.TemporaryDirectory() as td:
            try:
                t(Path(td))
                print(f"PASS {t.__name__}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all_standalone())
