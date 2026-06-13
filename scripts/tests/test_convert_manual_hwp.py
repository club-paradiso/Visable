#!/usr/bin/env python3
"""Tests for the HiKorea manual converter backends + benchmark.

Runnable standalone (`python3 scripts/tests/test_convert_manual_hwp.py`) or via
pytest. No network, no optional converters required — the "fake converter" test
synthesises a backend via an env-var command pointing at a temp script.

Covers: missing optional converters, tiny/stub output, fake successful converter
output, blocked/protected HWP classification, benchmark report generation, and
that production guidance data is never modified.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import convert_manual_hwp as cm  # noqa: E402

PROTECTED = [
    "visa_data.json",
    "doc_master.json",
    "backend/data/visas.json",
    "data/jobcode_master.json",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


def test_missing_optional_converter():
    """An unconfigured / absent external backend reports missing, never raises."""
    backend = {"name": "hwp2md_roboco", "url": "u",
               "env": "HWP2MD_ROBOCO_CMD", "default": None}
    os.environ.pop("HWP2MD_ROBOCO_CMD", None)
    with tempfile.TemporaryDirectory() as td:
        rec = cm.run_external(backend, Path(td) / "x.hwp", Path(td))
    assert rec["installed"] is False
    assert "not configured" in rec["error"]

    backend2 = {"name": "kordoc", "url": "u", "env": "KORDOC_CMD",
                "default": "definitely_missing_cmd_xyz {input}"}
    with tempfile.TemporaryDirectory() as td:
        rec2 = cm.run_external(backend2, Path(td) / "x.hwp", Path(td))
    assert rec2["installed"] is False and "missing" in rec2["error"]


def test_tiny_stub_output_classification():
    assert cm.classify("짧은 글", is_distribution=False) == "low_confidence"
    assert cm.classify("", is_distribution=False) == "failed"


def test_blocked_distribution_hwp_classification():
    # A stub or empty extraction from a distribution HWP must be 'blocked'.
    assert cm.classify("x" * 50, is_distribution=True) == "blocked_distribution_hwp"
    assert cm.classify("", is_distribution=True) == "blocked_distribution_hwp"


def test_fake_successful_converter_is_confident():
    """A backend whose command emits a rich manual-like doc → 'confident'."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        fake = tdp / "fake_converter.py"
        # Emit ~25k chars of Korean with headings and visa/stay codes.
        fake.write_text(
            "import sys\n"
            "body = []\n"
            "for i in range(60):\n"
            "    body.append(f'# 제{i+1}장 체류자격 안내')\n"
            "    body.append('대한민국 체류자격 D-2 E-7 F-4 안내 ' * 30)\n"
            "print('\\n'.join(body))\n",
            encoding="utf-8")
        backend = {"name": "kordoc", "url": "u", "env": "KORDOC_CMD",
                   "default": "%s %s {input}" % (sys.executable, fake)}
        rec = cm.run_external(backend, tdp / "in.hwp", tdp)
    assert rec["installed"] is True and rec["exit_code"] == 0
    status = cm.classify(rec["text"], is_distribution=False)
    m = cm.metrics(rec["text"])
    assert status == "confident", (status, m)
    assert m["headings"] >= 10 and m["codes"] >= 10


def test_benchmark_report_generation():
    """convert() writes benchmark.json + the matrix report; honours a fake backend."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        fake = tdp / "fake.py"
        fake.write_text(
            "print(('# 제1장 안내\\n' + '체류자격 D-2 E-7 F-4 ' * 50 + '\\n') * 80)\n",
            encoding="utf-8")
        os.environ["KORDOC_CMD"] = "%s %s {input}" % (sys.executable, fake)
        try:
            dummy = tdp / "dummy.hwp"
            dummy.write_bytes(b"not a real hwp")
            outdir = tdp / "out"
            result = cm.convert(dummy, outdir, compare=None)
        finally:
            os.environ.pop("KORDOC_CMD", None)
        assert (outdir / "dummy.benchmark.json").exists()
        assert (outdir / "dummy.extraction_report.md").exists()
        report = (outdir / "dummy.extraction_report.md").read_text(encoding="utf-8")
        assert "Converter result matrix" in report
        # the fake confident backend should drive the overall classification
        assert result["overall_quality"] == "confident"
        assert result["candidate_backend"] == "kordoc"


def test_production_guidance_data_untouched():
    before = {p: _sha(ROOT / p) for p in PROTECTED}
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        dummy = tdp / "d.hwp"
        dummy.write_bytes(b"x")
        cm.convert(dummy, tdp / "o", compare=None)
    after = {p: _sha(ROOT / p) for p in PROTECTED}
    assert before == after, "production guidance data must not change"


def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests)-failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
