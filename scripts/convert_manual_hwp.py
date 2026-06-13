#!/usr/bin/env python3
"""Best-effort HWP -> text conversion for the HiKorea manual sync pipeline.

The HiKorea 사증/체류 자격별 안내 매뉴얼 are distributed as **배포용(distribution)
HWP** files (FileHeader flag 0x4). Their BodyText is a stub and ViewText is
encrypted, so no open-source tool extracts them fully — the committed
docs/data/.../*_hwp_full.txt were produced with human/AI-assisted extraction.

This script therefore runs every available method, keeps each result, and
writes a verification report comparing extraction completeness against the
previously committed text. It NEVER decides on its own that an extraction is
authoritative; it produces artifacts for human review (see
docs/hikorea_manual_sync.md).

Methods (each optional, used only if its tooling is present):
  - olefile  : parse HWPTAG_PARA_TEXT from BodyText/Section* (works for plain
               HWP5; returns ~nothing for distribution docs — that itself is a
               useful signal).
  - soffice  : LibreOffice headless HWP -> PDF, then pdftotext PDF -> txt.
  - hwp5txt  : pyhwp CLI, if installed.

Usage:
  python3 scripts/convert_manual_hwp.py INPUT.hwp --outdir DIR [--compare PREV.txt]

Exit code is always 0 (best-effort); inspect the report for completeness.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

EXT_CONTROLS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}


def _para_text(payload: bytes) -> str:
    n = len(payload) // 2
    arr = struct.unpack_from("<%dH" % n, payload, 0)
    out = []
    i = 0
    while i < n:
        c = arr[i]
        if c in EXT_CONTROLS:
            i += 8
            continue
        if c in (10, 13):
            out.append("\n")
            i += 1
            continue
        if c < 32:
            i += 1
            continue
        out.append(chr(c))
        i += 1
    return "".join(out)


def hwp_flags(path: Path):
    """Return (is_hwp, compressed, distribution) by reading the FileHeader."""
    try:
        import olefile  # noqa: F401
    except Exception:
        return (None, None, None)
    import olefile
    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return (False, None, None)
    try:
        fh = ole.openstream("FileHeader").read()
        sig = fh[:16] == b"HWP Document Fil"  # truncated signature is fine
        flags = struct.unpack_from("<I", fh, 36)[0]
        return (True, bool(flags & 1), bool(flags & 4))
    except Exception:
        return (False, None, None)
    finally:
        ole.close()


def extract_olefile(path: Path) -> str:
    import olefile
    ole = olefile.OleFileIO(str(path))
    try:
        compressed = True
        try:
            fh = ole.openstream("FileHeader").read()
            compressed = bool(struct.unpack_from("<I", fh, 36)[0] & 1)
        except Exception:
            pass
        sects = [e for e in ole.listdir() if len(e) == 2 and e[0] == "BodyText" and e[1].startswith("Section")]
        sects.sort(key=lambda e: int(re.search(r"(\d+)", e[1]).group(1)))
        paras = []
        for e in sects:
            data = ole.openstream(e).read()
            if compressed:
                try:
                    data = zlib.decompress(data, -15)
                except Exception:
                    continue
            i, n = 0, len(data)
            while i + 4 <= n:
                hdr = struct.unpack_from("<I", data, i)[0]
                i += 4
                tag = hdr & 0x3FF
                size = (hdr >> 20) & 0xFFF
                if size == 0xFFF:
                    size = struct.unpack_from("<I", data, i)[0]
                    i += 4
                if i + size > n:
                    break
                payload = data[i:i + size]
                i += size
                if tag == 67:  # HWPTAG_PARA_TEXT
                    paras.append(_para_text(payload))
        return re.sub(r"[ \t]{2,}", " ", "\n".join(paras))
    finally:
        ole.close()


def extract_soffice(path: Path, workdir: Path) -> str:
    """HWP -> PDF (LibreOffice) -> txt (pdftotext)."""
    if not shutil.which("soffice") and not shutil.which("libreoffice"):
        raise RuntimeError("soffice/libreoffice not installed")
    profile = workdir / "lo_profile"
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    subprocess.run(
        [binary, "--headless", "--norestore",
         "-env:UserInstallation=file://%s" % profile,
         "--convert-to", "pdf", "--outdir", str(workdir), str(path)],
        check=True, capture_output=True, timeout=600,
    )
    pdf = workdir / (path.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError("LibreOffice produced no PDF (HWP filter likely failed)")
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext (poppler-utils) not installed")
    txt = workdir / (path.stem + ".txt")
    subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), str(txt)],
                   check=True, capture_output=True, timeout=300)
    return txt.read_text(encoding="utf-8", errors="replace")


def extract_hwp5txt(path: Path, workdir: Path) -> str:
    if not shutil.which("hwp5txt"):
        raise RuntimeError("hwp5txt (pyhwp) not installed")
    out = workdir / (path.stem + ".hwp5.txt")
    subprocess.run(["hwp5txt", "--output", str(out), str(path)],
                   check=True, capture_output=True, timeout=300)
    return out.read_text(encoding="utf-8", errors="replace")


def korean_count(s: str) -> int:
    return sum(1 for c in s if "가" <= c <= "힣")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--compare", type=Path, default=None,
                    help="previously committed txt to gauge extraction completeness")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem
    is_hwp, compressed, distribution = hwp_flags(args.input)

    results = {}  # method -> (text or None, error)
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        for name, fn in (("olefile", lambda: extract_olefile(args.input)),
                         ("soffice_pdftotext", lambda: extract_soffice(args.input, workdir)),
                         ("hwp5txt", lambda: extract_hwp5txt(args.input, workdir))):
            try:
                results[name] = (fn(), None)
            except Exception as e:  # noqa: BLE001 - best-effort by design
                results[name] = (None, str(e))

    # pick the longest successful extraction as the candidate
    best_name, best_text = None, ""
    for name, (text, _err) in results.items():
        if text and len(text) > len(best_text):
            best_name, best_text = name, text

    for name, (text, _err) in results.items():
        if text is not None:
            (args.outdir / f"{stem}.{name}.txt").write_text(text, encoding="utf-8")
    if best_text:
        (args.outdir / f"{stem}.candidate.txt").write_text(best_text, encoding="utf-8")

    prev_len = None
    if args.compare and args.compare.exists():
        prev_len = len(args.compare.read_text(encoding="utf-8", errors="replace"))
    completeness = (len(best_text) / prev_len * 100) if (prev_len and best_text) else None

    lines = [
        f"# HWP extraction report — {args.input.name}",
        "",
        f"- HWP format: {'distribution(배포용)' if distribution else 'standard' if is_hwp else 'unknown/not HWP'}"
        + (" ⚠ open tools cannot fully extract distribution HWP — human/AI-assisted"
           " extraction required before merge." if distribution else ""),
        f"- compressed: {compressed}",
        f"- candidate method: {best_name or 'NONE — all methods failed'}",
        f"- candidate length: {len(best_text)} chars (korean {korean_count(best_text)})",
    ]
    if prev_len is not None:
        lines.append(f"- previous committed txt: {prev_len} chars")
        lines.append(f"- extraction completeness vs previous: "
                     f"{completeness:.1f}%" if completeness is not None else "- completeness: n/a")
        if completeness is not None and completeness < 80:
            lines.append("- ⚠ LOW COMPLETENESS — do not promote this text without a verified re-extraction.")
    lines += ["", "## per-method", "", "| method | chars | korean | status |", "| --- | --- | --- | --- |"]
    for name, (text, err) in results.items():
        if text is not None:
            lines.append(f"| {name} | {len(text)} | {korean_count(text)} | ok |")
        else:
            lines.append(f"| {name} | — | — | {err} |")
    report = "\n".join(lines) + "\n"
    (args.outdir / f"{stem}.extraction_report.md").write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
