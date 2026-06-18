#!/usr/bin/env python3
"""Diff the checked-in visa_data.json against the regenerated output (Phase 3 / Script 4).

Read-only by default. Conservative: warns loudly rather than assuming a change
is safe. Used as a safety gate to prove the authoring refactor introduces no
runtime-visible change.

Reports:
  * record count / missing codes / new codes
  * changed subcode counts
  * changed `available` flags under procedures
  * removed runtime-critical fields
  * changed document IDs (in procedures.requiredDocs)
  * changed source-manual references / review flags
  * runtime-visible summary changes (content)
  * authoring-side summary cleanup (removed from authoring / compat-only /
    moved to audit / hidden from UI) — sourced from summary_cleanup_audit.json

Usage:
  python3 scripts/visa/diff_visa_data.py            # diff regenerated vs on-disk visa_data.json
  python3 scripts/visa/diff_visa_data.py --git      # diff regenerated vs git HEAD:visa_data.json
  python3 scripts/visa/diff_visa_data.py --write-temp PATH   # also write regenerated output to PATH
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _visa_pipeline_common as C  # noqa: E402

RUNTIME_CRITICAL = (
    "code", "name", "cat", "period", "procedures", "newReq", "newReqDocs",
    "extReq", "extReqDocs", "initialReqDocs", "extensionReqDocs", "changeReqDocs",
    "documents_initial", "documents_registration", "documents_extension",
    "subCodes", "faq", "feeInfo", "sourceManualStatus", "manualRefs", "searchAliases",
)


def _by_code(records):
    out = {}
    for r in records:
        out.setdefault(r.get("code"), []).append(r)
    return out


def _proc_summaries(rec):
    out = {}
    for nm, pv in (rec.get("procedures") or {}).items():
        if isinstance(pv, dict) and "summary" in pv:
            out[nm] = pv["summary"]
    return out


def _proc_available(rec):
    return {nm: pv.get("available") for nm, pv in (rec.get("procedures") or {}).items()
            if isinstance(pv, dict)}


def _doc_ids(rec):
    out = set()

    def walk(x):
        if isinstance(x, str) and x.startswith("doc_"):
            out.add(x)
        elif isinstance(x, list):
            [walk(i) for i in x]
        elif isinstance(x, dict):
            [walk(v) for v in x.values()]

    for pv in (rec.get("procedures") or {}).values():
        if isinstance(pv, dict):
            walk(pv.get("requiredDocs"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--git", action="store_true",
                    help="compare against git HEAD:visa_data.json instead of the working file")
    ap.add_argument("--write-temp", type=str, default=None,
                    help="write regenerated output to this path for audit comparison")
    args = ap.parse_args()

    from build_visa_data import build_records
    regenerated = build_records()
    rendered = C.dump_visa_json(regenerated)

    if args.write_temp:
        Path(args.write_temp).write_text(rendered, encoding="utf-8")
        print(f"[diff] wrote regenerated output to {args.write_temp}")

    if args.git:
        raw = subprocess.run(["git", "show", "HEAD:visa_data.json"],
                             capture_output=True, text=True, cwd=C.REPO_ROOT)
        if raw.returncode != 0:
            print("[diff] ERROR: could not read git HEAD:visa_data.json", file=sys.stderr)
            return 2
        baseline = json.loads(raw.stdout)
        baseline_label = "git HEAD:visa_data.json"
    else:
        baseline = C.load_json(C.VISA_DATA)
        baseline_label = "visa_data.json (working tree)"

    findings: list[str] = []
    base_codes = [r.get("code") for r in baseline]
    new_codes = [r.get("code") for r in regenerated]

    if len(baseline) != len(regenerated):
        findings.append(f"RECORD COUNT changed: {len(baseline)} -> {len(regenerated)}")
    missing = set(base_codes) - set(new_codes)
    added = set(new_codes) - set(base_codes)
    if missing:
        findings.append(f"MISSING codes (in baseline, not regenerated): {sorted(missing)}")
    if added:
        findings.append(f"NEW codes (in regenerated, not baseline): {sorted(added)}")

    bmap, nmap = _by_code(baseline), _by_code(regenerated)
    for code in base_codes:
        if code not in nmap:
            continue
        b = bmap[code][0]
        n = nmap[code][0]
        # removed runtime-critical fields
        removed = [f for f in RUNTIME_CRITICAL if f in b and f not in n]
        if removed:
            findings.append(f"[{code}] removed runtime-critical field(s): {removed}")
        # subcode counts
        if len(b.get("subCodes") or []) != len(n.get("subCodes") or []):
            findings.append(f"[{code}] subCodes count {len(b.get('subCodes') or [])} -> "
                            f"{len(n.get('subCodes') or [])}")
        # available flags
        if _proc_available(b) != _proc_available(n):
            findings.append(f"[{code}] procedure 'available' flags changed")
        # doc ids
        if _doc_ids(b) != _doc_ids(n):
            findings.append(f"[{code}] requiredDocs doc IDs changed: "
                            f"{sorted(_doc_ids(b) ^ _doc_ids(n))}")
        # source manual / review flags
        if b.get("sourceManualStatus") != n.get("sourceManualStatus"):
            findings.append(f"[{code}] sourceManualStatus changed")
        if json.dumps(b.get("manualRefs"), ensure_ascii=False, sort_keys=True) != \
                json.dumps(n.get("manualRefs"), ensure_ascii=False, sort_keys=True):
            findings.append(f"[{code}] top-level manualRefs changed")
        # runtime-visible summary content
        bs, ns = _proc_summaries(b), _proc_summaries(n)
        for nm in set(bs) | set(ns):
            if bs.get(nm) != ns.get(nm):
                findings.append(f"[{code}:{nm}] RUNTIME-VISIBLE summary content changed")

    # ---- authoring-side cleanup report (informational) ----
    print("=" * 72)
    print(f"DIFF: regenerated output vs {baseline_label}")
    print("=" * 72)
    print(f"records: baseline={len(baseline)} regenerated={len(regenerated)}")

    audit_path = C.AUDIT_DIR / "summary_cleanup_audit.json"
    if audit_path.exists():
        counts = C.load_json(audit_path).get("_meta", {}).get("counts", {})
        print("\nAuthoring summary cleanup (does NOT affect generated runtime output):")
        print(f"  total summaries scanned : {counts.get('total')}")
        print(f"  kept in authoring       : {counts.get('kept')}")
        print(f"  removed from authoring  : {counts.get('removedFromAuthoring')}")
        print(f"  preserved compat-only   : {counts.get('compatOnly')}")
        print(f"  moved to audit/excerpt  : {counts.get('movedToAudit')}")
        print(f"  needs human review      : {counts.get('needsHumanReview')}")
        print(f"  by quality              : {counts.get('byQuality')}")

    print("\nGenerated-vs-baseline runtime comparison:")
    if not findings:
        print("  OK — regenerated output is byte/structure identical to the baseline. "
              "No runtime-visible change.")
        return 0
    print(f"  !! {len(findings)} potential runtime-visible change(s) detected:")
    for f in findings:
        print(f"   - {f}")
    print("\n[diff] WARNING: differences found. Review carefully before committing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
