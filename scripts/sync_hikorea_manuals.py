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
DIFF_TOOL = ROOT / "scripts/diff_manual_versions.py"

# Maps a sync-config manual id to the --role the structured diff expects.
_MANUAL_ROLE = {"visa_manual": "visa", "stay_manual": "stay"}


def _resolve_extract(spec_map: dict, mid: str, config_entry: dict) -> Path | None:
    """Resolve the extracted-text path for one side of the structured diff.

    Preference: an explicit --old-extract/--new-extract mapping wins; otherwise
    fall back to a path declared in the sync config (``sections_path`` preferred
    for its per-page code mapping, else the verified ``txt_path``).
    """
    if mid in spec_map and spec_map[mid].exists():
        return spec_map[mid]
    for key in ("sections_path", "txt_path"):
        rel = config_entry.get(key)
        if rel:
            p = ROOT / rel
            if p.exists():
                return p
    return None


def run_structured_diff(mid: str, old_extract: Path, new_extract: Path) -> dict:
    """Run diff_manual_versions.py for a changed manual; return a compact summary.

    Writes the full Markdown + JSON report under build/manual-sync/<id>.manual-diff.*
    and returns {ok, summary, md_path, affected_codes} for the PR body. Never
    raises — a diff failure degrades to {ok: False, error: ...}.
    """
    role = _MANUAL_ROLE.get(mid, "stay")
    md_path = OUTDIR / f"{mid}.manual-diff.md"
    json_path = OUTDIR / f"{mid}.manual-diff.json"
    cmd = [
        sys.executable, str(DIFF_TOOL),
        "--old", str(old_extract), "--new", str(new_extract),
        "--role", role,
        "--out-md", str(md_path), "--out-json", str(json_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        report = json.loads(json_path.read_text(encoding="utf-8"))
        return {
            "ok": True,
            "summary": report.get("summary", {}),
            "affected_codes": [a["code"] for a in report.get("affected_codes", [])],
            "md_path": str(md_path.relative_to(ROOT)),
            "json_path": str(json_path.relative_to(ROOT)),
        }
    except Exception as e:  # noqa: BLE001 - diff is advisory; never break sync
        return {"ok": False, "error": str(e)}


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
    ap.add_argument("--new-extract", action="append", default=[], metavar="id=PATH",
                    help="verified NEW extracted text (*_sections.json or *_readable.txt) "
                         "for a changed manual; enables the structured diff (repeatable)")
    ap.add_argument("--old-extract", action="append", default=[], metavar="id=PATH",
                    help="override the OLD extracted-text baseline for the structured diff "
                         "(defaults to the config's sections_path/txt_path; repeatable)")
    args = ap.parse_args()

    def _parse_id_paths(specs, flag):
        out = {}
        for spec in specs:
            if "=" not in spec:
                print(f"ERROR: {flag} must be id=PATH, got {spec!r}", file=sys.stderr)
                continue
            mid, p = spec.split("=", 1)
            out[mid.strip()] = Path(p).expanduser()
        return out

    manual_inputs = _parse_id_paths(args.input, "--input")
    new_extracts = _parse_id_paths(args.new_extract, "--new-extract")
    old_extracts = _parse_id_paths(args.old_extract, "--old-extract")

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
                bench = conv_out / f"{staged.stem}.benchmark.json"
                if bench.exists():
                    b = json.loads(bench.read_text(encoding="utf-8"))
                    entry["overall_quality"] = b.get("overall_quality")
                    entry["candidate_backend"] = b.get("candidate_backend")
            except Exception as e:  # noqa: BLE001
                entry["detail"] += f" · conversion error: {e}"

            # Structured diff (advisory review artifact). Runs when a verified
            # NEW extraction is available (maintainer-supplied via --new-extract,
            # since distribution HWP cannot be auto-extracted) and an OLD
            # extraction baseline exists. Never edits production data.
            new_extract = _resolve_extract(new_extracts, mid, m)
            old_extract = _resolve_extract(old_extracts, mid, m)
            # Only treat an explicitly-supplied new extraction as "new"; the
            # config fallbacks are baselines, not the incoming version.
            if mid in new_extracts and new_extract and old_extract:
                entry["structured_diff"] = run_structured_diff(mid, old_extract, new_extract)
            else:
                entry["structured_diff"] = {
                    "ok": False,
                    "error": "no verified new extraction supplied (--new-extract id=PATH); "
                             "structured diff pending human/AI extraction of the distribution HWP",
                }
            results.append(entry)

    changed = [r for r in results if r["status"] == "changed"]
    summary = {"changed": bool(changed), "results": results}
    (OUTDIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # PR body
    lines = ["# HiKorea manual sync — review required", "",
             "An updated HiKorea manual was detected. This PR is a **draft for human",
             "review** — it stages the new file and a *best-effort* extraction only.",
             "It does NOT modify any production data.", ""]
    any_confident = any(r.get("overall_quality") == "confident" for r in changed)
    if changed:
        lines.append("## Changed manuals")
        for r in changed:
            lines += [
                f"### {r['title']} (`{r['id']}`)",
                f"- {r.get('detail','')}",
                f"- extraction classification: **{r.get('overall_quality','unknown')}**"
                f" (candidate backend: {r.get('candidate_backend') or 'none'})",
                f"- new sha256: `{r.get('new_sha256','')}`",
                f"- baseline:   `{r.get('baseline_sha256','')}`",
                "",
            ]
            if r.get("report"):
                lines += ["<details><summary>converter benchmark</summary>", "", r["report"], "</details>", ""]

            sd = r.get("structured_diff") or {}
            if sd.get("ok"):
                s = sd.get("summary", {})
                codes = sd.get("affected_codes", [])
                lines += [
                    "#### 구조적 diff — 영향받는 체류자격",
                    f"- 변경 페이지 **{s.get('pages_changed', 0)}**, 추가 "
                    f"**{s.get('pages_added', 0)}**, 삭제 **{s.get('pages_removed', 0)}** · "
                    f"영향 코드 **{s.get('affected_code_count', 0)}** "
                    f"(상위코드 {s.get('affected_base_code_count', 0)})",
                ]
                if s.get("extraction_mismatch_suspected"):
                    lines.append(
                        "- ⚠️ 변경률이 매우 높습니다 — 두 추출본이 서로 다른 파이프라인으로 "
                        "만들어졌을 수 있습니다(diff가 추출 노이즈에 지배). 같은 방식으로 추출한 "
                        "두 버전을 비교하세요.")
                if codes:
                    preview = ", ".join(codes[:40]) + (f" …(+{len(codes) - 40})" if len(codes) > 40 else "")
                    lines.append(f"- 영향 코드: {preview}")
                lines += [
                    f"- 전체 리포트: `{sd.get('md_path')}` (+ JSON `{sd.get('json_path')}`)",
                    "",
                ]
            elif sd.get("error"):
                lines += [f"#### 구조적 diff: 생략 — {sd['error']}", ""]
        if not any_confident:
            lines += [
                "> **Do not merge as a verified manual text update.** This PR only"
                " detects and stages the upstream file change. A verified text"
                " extraction must be supplied by a maintainer.",
                "",
            ]
        lines += [
            "## Reviewer checklist (before merge)",
            "- [ ] Confirm the staged HWP under `docs/source-manuals/incoming/` is the genuine official file.",
            "- [ ] These are 배포용(distribution) HWP — perform a verified (human/AI-assisted) full extraction; do NOT trust the best-effort text.",
            "- [ ] Review the structured diff (affected 체류자격 above / `build/manual-sync/*.manual-diff.md`) and re-check each affected status record against the manual source.",
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
