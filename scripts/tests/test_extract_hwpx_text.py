import json
import subprocess
import sys
import zipfile
from pathlib import Path


def test_extract_hwpx_text_from_synthetic_package(tmp_path: Path) -> None:
    hwpx = tmp_path / "sample.hwpx"
    section = """<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>유학(D-2) 체류기간 연장</hp:t></hp:run></hp:p>
  <hp:p><hp:run><hp:t>한국어 문단과 D-2 코드가 포함됩니다.</hp:t></hp:run></hp:p>
</hs:sec>
"""
    with zipfile.ZipFile(hwpx, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr("Contents/section0.xml", section)

    txt = tmp_path / "out.txt"
    md = tmp_path / "out.md"
    js = tmp_path / "out.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/extract_hwpx_text.py",
            str(hwpx),
            "--txt",
            str(txt),
            "--md",
            str(md),
            "--json",
            str(js),
        ],
        check=True,
    )

    assert "유학(D-2)" in txt.read_text(encoding="utf-8")
    assert md.exists()
    records = json.loads(js.read_text(encoding="utf-8"))
    assert records[0]["status_codes_detected"] == ["D-2"]
    assert records[0]["paragraphs"][0]["status_codes_detected"] == ["D-2"]
