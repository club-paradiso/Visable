#!/usr/bin/env python3
"""Best-effort HWP/HWPX -> text conversion + converter benchmark.

The HiKorea 사증/체류 자격별 안내 매뉴얼 ship as **배포용(distribution) HWP**
(FileHeader flag 0x4): BodyText is a stub and ViewText is encrypted, so no
open-source tool on Linux extracts them fully (kordoc, for example, needs the
Hancom Office COM API on Windows for DRM/distribution docs). The committed
docs/data/.../*_hwp_full.txt were produced by verified human/AI extraction.

This script runs every *available* backend, scores each output, classifies the
overall extraction, and writes a benchmark matrix for human review. It never
decides on its own that an extraction is authoritative (see
docs/hikorea_manual_sync.md).

Backends (each optional; skipped gracefully when missing):
  - olefile             : builtin HWPTAG_PARA_TEXT parse of BodyText/Section*.
  - soffice_pdftotext   : LibreOffice headless HWP->PDF then pdftotext.
  - hwp5txt             : pyhwp CLI.
  - hwp2md_hephaex      : github.com/hephaex/hwp2md (Rust). Cmd via $HWP2MD_HEPHAEX_CMD (default: hwp2md).
  - kordoc              : github.com/chrisryugj/kordoc (Python). Cmd via $KORDOC_CMD (default: kordoc).
  - hwp2md_roboco       : github.com/roboco-io/hwp2md (Go). Cmd via $HWP2MD_ROBOCO_CMD (no default — name collides with hephaex).

Usage:
  python3 scripts/convert_manual_hwp.py INPUT.hwp --outdir DIR [--compare PREV.txt]

Exit code is always 0 (best-effort); inspect the benchmark for confidence.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

EXT_CONTROLS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}

# Quality thresholds (deliberately conservative — never over-claim).
STUB_MAX_CHARS = 2000          # below this = a stub / blocked extraction
CONFIDENT_MIN_CHARS = 20000
CONFIDENT_MIN_KOREAN_RATIO = 0.15
CONFIDENT_MIN_ANCHORS = 10     # headings + manual anchors
CONFIDENT_MIN_CODES = 10

# Visa/stay status codes (A-1 … H-2, with optional sub-code like D-2-1 / F-2-7S).
CODE_RE = re.compile(r"\b[A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?)?\b")
# Markdown headings or Korean manual anchors (제N장/절/관, 별표, 붙임).
ANCHOR_RE = re.compile(r"(?m)^(?:#{1,6}\s+\S|제\s*\d+\s*[장절관]|별표\s*\d|붙임\s*\d)")


# --------------------------------------------------------------------------- #
# HWP inspection + builtin extractors
# --------------------------------------------------------------------------- #
def _para_text(payload: bytes) -> str:
    n = len(payload) // 2
    arr = struct.unpack_from("<%dH" % n, payload, 0)
    out, i = [], 0
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
    """Return (is_hwp, compressed, distribution) from the FileHeader, or Nones."""
    try:
        import olefile
    except Exception:
        return (None, None, None)
    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return (False, None, None)
    try:
        fh = ole.openstream("FileHeader").read()
        flags = struct.unpack_from("<I", fh, 36)[0]
        return (fh[:16] == b"HWP Document Fil", bool(flags & 1), bool(flags & 4))
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
        sects = [e for e in ole.listdir()
                 if len(e) == 2 and e[0] == "BodyText" and e[1].startswith("Section")]
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
                if tag == 67:
                    paras.append(_para_text(payload))
        return re.sub(r"[ \t]{2,}", " ", "\n".join(paras))
    finally:
        ole.close()


def _run_cmd(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def extract_soffice(path: Path, workdir: Path) -> str:
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise RuntimeError("soffice/libreoffice not installed")
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext (poppler-utils) not installed")
    profile = workdir / "lo_profile"
    rc, _o, err = _run_cmd(
        [binary, "--headless", "--norestore",
         "-env:UserInstallation=file://%s" % profile,
         "--convert-to", "pdf", "--outdir", str(workdir), str(path)], 600)
    pdf = workdir / (path.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError("LibreOffice produced no PDF (rc=%s) %s" % (rc, err.strip()[:120]))
    txt = workdir / (path.stem + ".txt")
    _run_cmd(["pdftotext", "-enc", "UTF-8", str(pdf), str(txt)], 300)
    return txt.read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# External CLI backends (optional; detected at runtime, never vendored)
# --------------------------------------------------------------------------- #
# Each: name, url, env var for the command/template, default template (or None).
# A template may contain {input} and {output}; with {output} we read that file,
# otherwise stdout is captured.
EXTERNAL_BACKENDS = [
    {"name": "hwp5txt", "url": "https://github.com/mete0r/pyhwp",
     "env": "HWP5TXT_CMD", "default": "hwp5txt --output {output} {input}"},
    {"name": "hwp2md_hephaex", "url": "https://github.com/hephaex/hwp2md",
     "env": "HWP2MD_HEPHAEX_CMD", "default": "hwp2md {input}"},
    {"name": "kordoc", "url": "https://github.com/chrisryugj/kordoc",
     "env": "KORDOC_CMD", "default": "kordoc {input}"},
    {"name": "hwp2md_roboco", "url": "https://github.com/roboco-io/hwp2md",
     "env": "HWP2MD_ROBOCO_CMD", "default": None},  # no default: collides with hephaex
]


def run_external(backend: dict, path: Path, workdir: Path) -> dict:
    """Run one external backend. Returns a record (never raises)."""
    rec = {"name": backend["name"], "url": backend["url"], "installed": False,
           "command": None, "exit_code": None, "text": None, "error": None}
    template = os.environ.get(backend["env"]) or backend["default"]
    if not template:
        rec["error"] = "not configured (set $%s)" % backend["env"]
        return rec
    out_file = workdir / ("%s.out" % backend["name"])
    cmd_str = template.replace("{input}", shlex.quote(str(path))).replace("{output}", shlex.quote(str(out_file)))
    rec["command"] = cmd_str
    try:
        tokens = shlex.split(cmd_str)
    except Exception as e:
        rec["error"] = "bad command template: %s" % e
        return rec
    base = tokens[0]
    if not (shutil.which(base) or Path(base).exists()):
        rec["error"] = "missing: %r not on PATH" % base
        return rec
    rec["installed"] = True
    try:
        rc, out, err = _run_cmd(tokens, 600)
        rec["exit_code"] = rc
        if "{output}" in template:
            text = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""
        else:
            text = out
        rec["text"] = text
        if rc != 0 and not text.strip():
            rec["error"] = "exit %s: %s" % (rc, err.strip()[:160])
    except subprocess.TimeoutExpired:
        rec["error"] = "timeout"
    except Exception as e:  # noqa: BLE001 - optional backend, never fatal
        rec["error"] = str(e)
    return rec


# --------------------------------------------------------------------------- #
# Scoring + classification
# --------------------------------------------------------------------------- #
def korean_ratio(s: str) -> float:
    if not s:
        return 0.0
    ko = sum(1 for c in s if "가" <= c <= "힣")
    return ko / max(1, len(s))


def metrics(text: str) -> dict:
    text = text or ""
    return {
        "chars": len(text),
        "korean_ratio": round(korean_ratio(text), 3),
        "headings": len(ANCHOR_RE.findall(text)),
        "codes": len(CODE_RE.findall(text)),
    }


def classify(text: str, is_distribution: bool) -> str:
    """confident | low_confidence | blocked_distribution_hwp | failed."""
    if not text or not text.strip():
        return "blocked_distribution_hwp" if is_distribution else "failed"
    m = metrics(text)
    if m["chars"] < STUB_MAX_CHARS:
        return "blocked_distribution_hwp" if is_distribution else "low_confidence"
    if (m["chars"] >= CONFIDENT_MIN_CHARS
            and m["korean_ratio"] >= CONFIDENT_MIN_KOREAN_RATIO
            and (m["headings"] >= CONFIDENT_MIN_ANCHORS or m["codes"] >= CONFIDENT_MIN_CODES)):
        return "confident"
    return "low_confidence"


_RANK = {"confident": 3, "low_confidence": 2, "blocked_distribution_hwp": 1, "failed": 0}


def overall_status(statuses: list[str], is_distribution: bool) -> str:
    if not statuses:
        return "blocked_distribution_hwp" if is_distribution else "failed"
    return max(statuses, key=lambda s: _RANK.get(s, 0))


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def convert(input_path: Path, outdir: Path, compare: Path | None = None) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    is_hwp, compressed, distribution = hwp_flags(input_path)
    distribution = bool(distribution)

    backends = []  # list of records
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        # builtin backends
        #
        # `viewtext_aes` reads the 배포용 path the others cannot: for a
        # distribution HWP the body lives in ViewText, AES-128-ECB encrypted,
        # while every backend below reads the BodyText stub and comes back
        # empty. See scripts/decrypt_hwp_distribution.py for why that is a
        # documented format feature rather than a protection being bypassed.
        # It is still only a *candidate* extraction — nothing here promotes an
        # edition to `approved`.
        def _viewtext_aes() -> str:
            if not distribution:
                raise RuntimeError("not a distribution HWP — other backends apply")
            import decrypt_hwp_distribution as dist
            return dist.extract(input_path)

        for name, fn in (("viewtext_aes", _viewtext_aes),
                         ("olefile", lambda: extract_olefile(input_path)),
                         ("soffice_pdftotext", lambda: extract_soffice(input_path, workdir))):
            rec = {"name": name, "url": "builtin", "installed": True,
                   "command": name, "exit_code": None, "text": None, "error": None}
            try:
                rec["text"] = fn()
            except Exception as e:  # noqa: BLE001
                # Both builtins are always present; only soffice is an external
                # dependency that can genuinely be missing.
                rec["installed"] = name in ("olefile", "viewtext_aes")
                rec["error"] = str(e)
            backends.append(rec)
        # external CLI backends
        for be in EXTERNAL_BACKENDS:
            backends.append(run_external(be, input_path, workdir))

        # score + persist each output
        for rec in backends:
            text = rec.get("text")
            rec["metrics"] = metrics(text) if text else {"chars": 0, "korean_ratio": 0.0, "headings": 0, "codes": 0}
            rec["quality"] = classify(text, distribution) if text is not None else (
                "blocked_distribution_hwp" if distribution else "failed")
            if text:
                p = outdir / f"{stem}.{rec['name']}.txt"
                p.write_text(text, encoding="utf-8")
                rec["output_path"] = str(p)
            else:
                rec["output_path"] = None
            rec.pop("text", None)  # keep the record JSON-light

    # candidate = best non-stub output
    ranked = sorted(backends, key=lambda r: (_RANK.get(r["quality"], 0), r["metrics"]["chars"]), reverse=True)
    candidate = next((r for r in ranked if r["metrics"]["chars"] >= STUB_MAX_CHARS), None)
    overall = overall_status([r["quality"] for r in backends], distribution)

    prev_len = len(compare.read_text(encoding="utf-8", errors="replace")) if (compare and compare.exists()) else None
    completeness = None
    if prev_len and candidate:
        completeness = round(candidate["metrics"]["chars"] / prev_len * 100, 1)

    result = {
        "input": input_path.name,
        "hwp_format": "distribution" if distribution else ("standard" if is_hwp else "unknown"),
        "compressed": compressed,
        "overall_quality": overall,
        "candidate_backend": candidate["name"] if candidate else None,
        "candidate_chars": candidate["metrics"]["chars"] if candidate else 0,
        "previous_chars": prev_len,
        "completeness_pct": completeness,
        "backends": backends,
    }
    (outdir / f"{stem}.benchmark.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / f"{stem}.extraction_report.md").write_text(render_report(result), encoding="utf-8")
    if candidate:
        # copy the best output as the candidate text (never a stub)
        shutil.copy2(candidate["output_path"], outdir / f"{stem}.candidate.txt")
    return result


def render_report(result: dict) -> str:
    dist = result["hwp_format"] == "distribution"
    lines = [
        f"# HWP extraction benchmark — {result['input']}",
        "",
        f"- HWP format: **{result['hwp_format']}**"
        + ("  ⚠ distribution HWP: the body is read via the documented ViewText"
           " AES path (`viewtext_aes`); the BodyText-reading backends below"
           " will always report empty. A high character count here is a"
           " *candidate* extraction only — it is not evidence that the text"
           " matches the source, so human verification against the original is"
           " still required before merge, and nothing here may set"
           " `approved`." if dist else ""),
        f"- overall classification: **{result['overall_quality']}**",
        f"- candidate backend: {result['candidate_backend'] or 'NONE'}"
        f" ({result['candidate_chars']} chars)",
    ]
    if result["previous_chars"] is not None:
        lines.append(f"- previous committed txt: {result['previous_chars']} chars"
                     + (f" · completeness {result['completeness_pct']}%" if result["completeness_pct"] is not None else ""))
    lines += [
        "",
        "## Converter result matrix",
        "",
        "| backend | installed | exit | chars | korean | headings | codes | quality | command / failure |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in result["backends"]:
        m = r["metrics"]
        detail = r.get("error") or r.get("command") or ""
        lines.append(
            f"| {r['name']} | {'yes' if r['installed'] else 'no'} | {r.get('exit_code')} | "
            f"{m['chars']} | {m['korean_ratio']} | {m['headings']} | {m['codes']} | "
            f"{r['quality']} | {str(detail)[:80]} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--compare", type=Path, default=None)
    args = ap.parse_args()
    result = convert(args.input, args.outdir, args.compare)
    sys.stdout.write(render_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
