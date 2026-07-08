#!/usr/bin/env python3
"""Tests for scripts/diff_manual_versions.py — the structured manual diff.

Runnable standalone (`python3 scripts/tests/test_diff_manual_versions.py`) or
via pytest. Stdlib-only, no network. Verifies:
  * both sections.json schemas load (new `text` and old `paragraphs[]`),
  * a changed / inserted / deleted page is detected with the right codes and
    NO false positives on unchanged pages (page-shift alignment),
  * identical inputs report zero change,
  * the extraction-mismatch heuristic fires on a cross-pipeline pair and not on
    a clean same-pipeline pair,
  * the tool never writes to protected data files.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import diff_manual_versions as dmv  # noqa: E402

PROTECTED = ["visa_data.json", "doc_master.json", "backend/data/visas.json"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


def _page(page, text, codes):
    return {"source_id": "t", "source_file": "t", "page": page, "heading": "",
            "text": text, "status_codes_detected": list(codes),
            "subcodes_detected": [], "domain": "stay"}


def _base_pages():
    return [
        _page(1, "표지", []),
        _page(2, "目次 유학(D-2) 거주(F-2)", ["D-2", "F-2"]),
        _page(3, "유학(D-2) 제출서류 ① 신청서 ② 재학증명서", ["D-2"]),
        _page(4, "거주(F-2) 제출서류 ① 신청서 ② 소득증명", ["F-2"]),
        _page(5, "영주(F-5) 안내", ["F-5"]),
    ]


def _write(tmp: Path, name: str, pages) -> Path:
    p = tmp / name
    p.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return p


def _run(old_path: Path, new_path: Path):
    old = dmv.load_manual(old_path, "old")
    new = dmv.load_manual(new_path, "new")
    changes = dmv.diff_manuals(old, new, max_diff_lines=40)
    _md, jr = dmv.build_report(old, new, old_path, new_path, "stay", changes, 60)
    return jr


def test_identical_inputs_no_change(tmp_path):
    p = _write(tmp_path, "a.json", _base_pages())
    jr = _run(p, p)
    assert jr["summary"]["pages_changed"] == 0
    assert jr["summary"]["pages_added"] == 0
    assert jr["summary"]["pages_removed"] == 0
    assert jr["summary"]["extraction_mismatch_suspected"] is False


def test_change_insert_delete_with_codes(tmp_path):
    old_pages = _base_pages()
    new_pages = copy.deepcopy(old_pages)
    # change page 3 (D-2)
    new_pages[2]["text"] += " ③ 추가서류 재직증명서"
    # delete page 4 (F-2)
    new_pages = [pg for pg in new_pages if pg["page"] != 4]
    # insert a new page 6 (F-6)
    new_pages.append(_page(6, "결혼이민(F-6) 신설", ["F-6"]))

    old_p = _write(tmp_path, "old.json", old_pages)
    new_p = _write(tmp_path, "new.json", new_pages)
    jr = _run(old_p, new_p)

    s = jr["summary"]
    assert s["pages_changed"] == 1, s
    assert s["pages_added"] == 1, s
    assert s["pages_removed"] == 1, s

    kinds = {(c["kind"], c["old_page"], c["new_page"]) for c in jr["page_changes"]}
    assert ("changed", 3, 3) in kinds
    assert ("removed", 4, None) in kinds
    assert ("added", None, 6) in kinds

    affected = {a["code"] for a in jr["affected_codes"]}
    # D-2 (changed page 3), F-2 (deleted page 4), F-6 (inserted page 6)
    assert {"D-2", "F-2", "F-6"} <= affected, affected
    # F-5 page 5 was untouched -> must NOT appear
    assert "F-5" not in affected, affected


def test_old_paragraphs_schema_loads(tmp_path):
    """The older extraction schema (pdf_page + paragraphs[]) must load."""
    old_schema = [
        {"pdf_page": 1, "title": "표지", "paragraphs": [
            {"paragraph_index": 0, "text": "표지", "status_codes_detected": []}]},
        {"pdf_page": 2, "title": "유학", "paragraphs": [
            {"paragraph_index": 0, "text": "유학(D-2)", "status_codes_detected": ["D-2"]},
            {"paragraph_index": 1, "text": "제출서류 신청서", "status_codes_detected": []}],
         "status_codes_detected": ["D-2"]},
    ]
    p = tmp_path / "old_schema.json"
    p.write_text(json.dumps(old_schema, ensure_ascii=False), encoding="utf-8")
    man = dmv.load_manual(p, "old")
    assert man.page_count == 2
    assert man.pages[1].page == 2
    assert "D-2" in man.pages[1].codes
    assert "제출서류" in man.pages[1].text


def test_readable_txt_schema_loads(tmp_path):
    txt = (
        "===== 외국인체류 안내매뉴얼 2026.6 / PDF page 1 of 2 =====\n"
        "표지\n"
        "===== 외국인체류 안내매뉴얼 2026.6 / PDF page 2 of 2 =====\n"
        "유학(D-2) 제출서류\n"
    )
    p = tmp_path / "readable.txt"
    p.write_text(txt, encoding="utf-8")
    man = dmv.load_manual(p, "x")
    assert man.page_count == 2
    assert "D-2" in man.pages[1].codes


def test_extraction_mismatch_heuristic(tmp_path):
    # Same content, but expressed so that every page string differs wildly:
    # simulate a cross-pipeline pair by making the new pages entirely different
    # text on every page while keeping the same count.
    old_pages = [_page(i, f"content page {i} 유학 D-2", ["D-2"]) for i in range(1, 21)]
    new_pages = [_page(i, f"WHOLLY DIFFERENT {i*7} 거주 F-2", ["F-2"]) for i in range(1, 21)]
    old_p = _write(tmp_path, "o.json", old_pages)
    new_p = _write(tmp_path, "n.json", new_pages)
    jr = _run(old_p, new_p)
    assert jr["summary"]["extraction_mismatch_suspected"] is True
    assert jr["summary"]["change_ratio"] > 0.6

    # And a clean pair (one changed page out of 20) must NOT trip it.
    new2 = copy.deepcopy(old_pages)
    new2[5]["text"] += " 추가"
    new2_p = _write(tmp_path, "n2.json", new2)
    jr2 = _run(old_p, new2_p)
    assert jr2["summary"]["extraction_mismatch_suspected"] is False


def test_no_protected_file_writes(tmp_path):
    before = {f: _sha(ROOT / f) for f in PROTECTED}
    old_p = _write(tmp_path, "old.json", _base_pages())
    new_pages = copy.deepcopy(_base_pages())
    new_pages[2]["text"] += " 변경"
    new_p = _write(tmp_path, "new.json", new_pages)
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    rc = dmv.main([
        "--old", str(old_p), "--new", str(new_p), "--role", "stay",
        "--out-md", str(out_md), "--out-json", str(out_json),
    ])
    assert rc == 0
    assert out_md.exists() and out_json.exists()
    after = {f: _sha(ROOT / f) for f in PROTECTED}
    assert before == after, "diff tool must never modify protected data files"


def test_fail_on_change_exit_code(tmp_path):
    old_p = _write(tmp_path, "old.json", _base_pages())
    new_pages = copy.deepcopy(_base_pages())
    new_pages[2]["text"] += " 변경"
    new_p = _write(tmp_path, "new.json", new_pages)
    rc = dmv.main(["--old", str(old_p), "--new", str(new_p), "--role", "stay",
                   "--fail-on-change"])
    assert rc == 2
    # identical -> 0
    rc0 = dmv.main(["--old", str(old_p), "--new", str(old_p), "--role", "stay",
                    "--fail-on-change"])
    assert rc0 == 0


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
