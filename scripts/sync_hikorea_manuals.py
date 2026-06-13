#!/usr/bin/env python3
"""Orchestrate the HiKorea manual sync — detect, stage, convert, propose.

For each manual in data/sources/hikorea_manual_sync.json this script:
  1. Obtains a candidate HWP — from --input id=PATH (manual upload / dispatch),
     or, with --allow-network and a configured download_url, a best-effort
     download (gracefully skipped if the official host blocks CI, e.g. 403).
  2. Computes its sha256 and compares to the committed baseline.
  3. If changed/new, stages the HWP under docs/source-manuals/incoming/ and runs
     scripts/convert_manual_hwp.py to produce best-effort text + an extraction
     report.
  4. Writes a machine summary (build/manual-sync/summary.json) and a PR body
     (build/manual-sync/pr_body.md) for the workflow to open a DRAFT PR.

Safety: this script only writes under docs/source-manuals/incoming/ and
build/manual-sync/. It never edits visa_data.json, doc_master.json, the
committed *_hwp_full.txt, or any production data. Promotion is a human task.

Exit code: 0 always. The workflow reads summary.json ("changed": true/false).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data/sources/hikorea_manual_sync.json"
INCOMING = ROOT / "docs/source-manuals/incoming"
OUTDIR = ROOT / "build/manual-sync"
CONVERT = ROOT / "scripts/convert_manual_hwp.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def best_effort_download(url: str, dest: Path) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Paradiso-manual-sync/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (gov host, opt-in)
            dest.write_bytes(resp.read())
        return True, "downloaded"
    except Exception as e:  # noqa: BLE001 - blocked/403/offline is expected
        return False, f"download skipped: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-network", action="store_true",
                    help="permit best-effort download from configured download_url")
    ap.add_argument("--input", action="append", default=[], metavar="id=PATH",
                    help="manually-provided HWP for a manual id (repeatable)")
    args = ap.parse_args()

    manual_inputs = {}
    for spec in args.input:
        if "=" not in spec:
            print(f"ERROR: --input must be id=PATH, got {spec!r}", file=sys.stderr)
            return 0
        mid, p = spec.split("=", 1)
        manual_inputs[mid.strip()] = Path(p).expanduser()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    INCOMING.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    results = []
    for m in config["manuals"]:
        mid = m["id"]
        entry = {"id": mid, "title": m.get("title_ko"), "status": "unchanged",
                 "detail": "", "report": None}

        with tempfile.TemporaryDirectory() as td:
            candidate = None
            if mid in manual_inputs and manual_inputs[mid].exists():
                candidate = manual_inputs[mid]
                entry["detail"] = f"manual input: {candidate}"
            elif args.allow_network and m.get("download_url"):
                tmp = Path(td) / f"{mid}.hwp"
                ok, msg = best_effort_download(m["download_url"], tmp)
                entry["detail"] = msg
                candidate = tmp if ok else None
            else:
                entry["status"] = "no_source"
                entry["detail"] = ("no manual input and no usable download_url "
                                   "(supply via workflow_dispatch or configure download_url)")
                results.append(entry)
                continue

            if candidate is None:
                entry["status"] = "fetch_failed"
                results.append(entry)
                continue

            new_hash = sha256_file(candidate)
            baseline = m.get("baseline_sha256")
            if new_hash == baseline:
                entry["status"] = "unchanged"
                entry["detail"] += f" · sha256 matches baseline ({new_hash[:12]}…)"
                results.append(entry)
                continue

            # changed / new → stage + convert (no production writes)
            entry["status"] = "changed"
            entry["new_sha256"] = new_hash
            entry["baseline_sha256"] = baseline
            staged = INCOMING / Path(m["hwp_path"]).name
            shutil.copy2(candidate, staged)
            conv_out = OUTDIR / mid
            prev_txt = ROOT / m["txt_path"]
            cmd = [sys.executable, str(CONVERT), str(staged), "--outdir", str(conv_out)]
            if prev_txt.exists():
                cmd += ["--compare", str(prev_txt)]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=900)
                report = conv_out / f"{staged.stem}.extraction_report.md"
                entry["report"] = report.read_text(encoding="utf-8") if report.exists() else None
            except Exception as e:  # noqa: BLE001
                entry["detail"] += f" · conversion error: {e}"
            results.append(entry)

    changed = [r for r in results if r["status"] == "changed"]
    summary = {"changed": bool(changed), "results": results}
    (OUTDIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # PR body
    lines = ["# HiKorea manual sync — review required", "",
             "An updated HiKorea manual was detected. This PR is a **draft for human",
             "review** — it stages the new file and a *best-effort* extraction only.",
             "It does NOT modify any production data.", ""]
    if changed:
        lines.append("## Changed manuals")
        for r in changed:
            lines += [
                f"### {r['title']} (`{r['id']}`)",
                f"- {r.get('detail','')}",
                f"- new sha256: `{r.get('new_sha256','')}`",
                f"- baseline:   `{r.get('baseline_sha256','')}`",
                "",
            ]
            if r.get("report"):
                lines += ["<details><summary>extraction report</summary>", "", r["report"], "</details>", ""]
        lines += [
            "## Reviewer checklist (before merge)",
            "- [ ] Confirm the staged HWP under `docs/source-manuals/incoming/` is the genuine official file.",
            "- [ ] These are 배포용(distribution) HWP — perform a verified (human/AI-assisted) full extraction; do NOT trust the best-effort text.",
            "- [ ] Move the HWP to its canonical `docs/source-manuals/...` path and update the verified `*_hwp_full.txt`.",
            "- [ ] Update `baseline_sha256` in `data/sources/hikorea_manual_sync.json`.",
            "- [ ] Run the data audits and decide, with review, whether any grounding data changes follow.",
        ]
    else:
        lines.append("_No manual changes detected (all sha256 match baseline, or no source was available)._")
    (OUTDIR / "pr_body.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
